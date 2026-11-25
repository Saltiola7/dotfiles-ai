"""Managed owner: lifecycle-requested validation stays advisory, enrolled and content-bound."""

import hashlib
import importlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import uuid

import pytest

from test_continuous_validation import ADAPTER, git, private_json, worktree  # noqa: F401 - shared fixtures


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_dbsctrctl"
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from continuous_validation import runner


UNSET = object()


@pytest.fixture
def owner(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "default_state_root", lambda: tmp_path / "state-root")
    return importlib.import_module("continuous_validation.cli")


@pytest.fixture
def enrolled(worktree, tmp_path, monkeypatch):
    """One checkpoint-enabled enrollment explicitly bound to the exact worktree and cycle."""
    monkeypatch.setattr(runner, "default_state_root", lambda: tmp_path / "state-root")
    monkeypatch.setattr(runner, "cycle_open", lambda _: True)
    monkeypatch.setattr(runner, "budget_root", lambda: tmp_path / "shared-admission")
    monkeypatch.setattr(runner, "pressure", lambda _: False)
    adapter = worktree / ".ci/adapter.py"
    adapter.parent.mkdir()
    adapter.write_text(ADAPTER)
    git(worktree, "add", ".ci/adapter.py")
    git(worktree, "commit", "-m", "owner fixture adapter")
    state = tmp_path / "state"
    value = {
        "schema_version": 1, "enabled": True, "mode": "shadow", "checkpoints_enabled": True,
        "worktree": str(worktree), "adapter": ".ci/adapter.py",
        "adapter_digest": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        "adapter_python": sys.executable, "adapter_config": {},
        "repository_id": runner.repository_id(worktree),
        "session_id": str(uuid.uuid4()), "cycle_id": "owner-cycle",
        "base": git(worktree, "rev-parse", "HEAD"), "state_dir": str(state), "feedback_enabled": False,
    }
    path = private_json(tmp_path / "enrollment.json", value)
    importlib.import_module("continuous_validation.checkpoints").register(path, value)
    policy = private_json(tmp_path / "continuous-validation-policy.json", {"enabled": True})
    return {"enrollment": path, "value": value, "worktree": worktree, "state": state, "policy": policy,
            "cycle": "owner-cycle"}


def action(owner, enrolled, name, cycle=None, policy=UNSET, **extra):
    """Call the owner exactly as the lifecycle helper does."""
    return owner.managed_action(
        name, worktree=enrolled["worktree"], cycle=cycle or enrolled["cycle"],
        policy_path=enrolled["policy"] if policy is UNSET else policy,
        feedback_target=None, gate=None, purpose=None, expected_ids=[], head=None, checkpoint_id=None,
        lifecycle_path=SCRIPT, automatic=False, **extra)


def write_enrollment(enrolled, **changes):
    private_json(enrolled["enrollment"], {**enrolled["value"], **changes})


def unavailable(code):
    return {"schema_version": 1, "status": "unavailable", "error_code": code, "observations": [], "advisory": True}


def routed(status):
    return {"schema_version": 1, "status": status, "error_code": "owner_action_unsupported", "advisory": True}


@pytest.mark.parametrize("policy", [None, {"enabled": False}, {"enabled": "true"}])
def test_inert_policy_disables_every_action_without_state(owner, enrolled, tmp_path, policy):
    path = private_json(tmp_path / "policy.json", policy) if policy is not None else None
    for name in ("validate", "applicability", "enroll", "checkpoint", "opt-out"):
        assert action(owner, enrolled, name, policy=path, snapshot_id="a" * 64) == {"status": "disabled", "advisory": True}
    assert not enrolled["state"].exists()


def test_unimplemented_actions_never_enroll_queue_or_change_state(owner, enrolled):
    assert action(owner, enrolled, "enroll") == routed("not_enrolled")
    assert action(owner, enrolled, "checkpoint") == routed("legacy_enrolled")
    assert action(owner, enrolled, "checkpoint", cycle="other-cycle") == routed("not_enrolled")
    for name in ("opt-out", "resume", "validate-everything"):
        assert action(owner, enrolled, name) == unavailable("owner_action_unsupported")
    assert not enrolled["state"].exists()


def test_validate_returns_one_reference_per_executed_observation(owner, enrolled):
    result = action(owner, enrolled, "validate")
    assert result["status"] == "completed" and result["new_execution"] is True and result["advisory"] is True
    assert result["pending_checks"] == [] and result["selection_complete"] is True
    assert [(item["check_id"], item["status"], item["executed"]) for item in result["observations"]] == [
        ("quick", "passed", True), ("slow", "passed", True)]
    assert all(item["snapshot_id"] == result["snapshot_id"] and item["failed_test_ids"] == [] for item in result["observations"])
    assert sorted(path.stem for path in (enrolled["state"] / "observations").glob("*.json")) == sorted(
        item["id"] for item in result["observations"])
    json.dumps(result)  # The lifecycle helper prints this value as JSON.


def test_validate_is_inactive_without_a_bound_enabled_enrollment(owner, enrolled):
    other = action(owner, enrolled, "validate", cycle="other-cycle")
    assert other == unavailable("enrollment_inactive")
    write_enrollment(enrolled, enabled=False)
    assert action(owner, enrolled, "validate") == unavailable("enrollment_inactive")
    write_enrollment(enrolled, checkpoints_enabled=False)
    assert action(owner, enrolled, "validate") == unavailable("enrollment_inactive")
    assert not enrolled["state"].exists()


def test_validate_refuses_a_closed_task_and_a_changed_adapter(owner, enrolled, monkeypatch):
    monkeypatch.setattr(runner, "cycle_open", lambda _: False)
    assert action(owner, enrolled, "validate") == unavailable("enrolled_task_closed")
    monkeypatch.setattr(runner, "cycle_open", lambda _: True)
    (enrolled["worktree"] / ".ci/adapter.py").write_text("# replaced after enrollment\n")
    assert action(owner, enrolled, "validate") == unavailable("adapter_identity_changed")
    assert not enrolled["state"].exists()


def test_named_checks_narrow_validate_and_unknown_names_are_refused(owner, enrolled):
    narrowed = action(owner, enrolled, "validate", check_ids=["slow"])
    assert narrowed["status"] == "completed" and narrowed["selection_complete"] is False
    assert [item["check_id"] for item in narrowed["observations"]] == ["slow"]
    unknown_check = action(owner, enrolled, "validate", check_ids=["missing"])
    assert {name: value for name, value in unknown_check.items() if name != "request_id"} == unavailable("invalid_selection")
    for named in ("slow", ["quick", "quick"], ["../escape"], [7]):
        assert action(owner, enrolled, "validate", check_ids=named) == unavailable("invalid_checks")


def test_validate_honours_an_explicit_request_id(owner, enrolled):
    first = action(owner, enrolled, "validate", request_id="retry")
    replay = action(owner, enrolled, "validate", request_id="retry")
    assert replay["new_execution"] is False and replay["status"] == "completed"
    assert [item["id"] for item in replay["observations"]] == [item["id"] for item in first["observations"]]


def test_validate_never_opts_into_feedback(owner, enrolled, monkeypatch):
    feedback = importlib.import_module("continuous_validation.feedback")
    seen = []
    monkeypatch.setattr(feedback, "deliver", lambda enrollment, *args, **options: seen.append(enrollment["feedback_enabled"])
                        or {"status": "disabled", "reason": "fixture"})
    (enrolled["worktree"] / "source.py").write_text("fail = True\n")
    result = action(owner, enrolled, "validate")
    assert result["status"] == "completed"
    assert [item["status"] for item in result["observations"]] == ["failed", "failed"]
    assert seen and set(seen) == {False}


def applicability(owner, enrolled, snapshot_id, **extra):
    result = action(owner, enrolled, "applicability", snapshot_id=snapshot_id, **extra)
    return {name: value for name, value in result.items() if name != "schema_version"}


def test_applicability_tracks_content_not_the_request(owner, enrolled):
    worktree = enrolled["worktree"]
    first = action(owner, enrolled, "validate")
    snapshot = first["snapshot_id"]
    current = {"applicable": True, "reason": "current", "changed_paths": [], "head_advanced": False, "generation_current": True}
    assert applicability(owner, enrolled, snapshot) == current
    # A head that advances without a content change leaves the captured content current.
    git(worktree, "commit", "--allow-empty", "-m", "advance without content")
    assert applicability(owner, enrolled, snapshot) == {**current, "head_advanced": True}
    (worktree / "source.py").write_text("value = 2\n")
    assert applicability(owner, enrolled, snapshot) == {
        "applicable": False, "reason": "source_changed", "changed_paths": ["source.py"], "changed_paths_complete": True}
    # A newer generation on other content does not by itself retire the receipt.
    second = action(owner, enrolled, "validate")
    assert applicability(owner, enrolled, snapshot)["applicable"] is False
    (worktree / "source.py").write_text("value = 1\n")
    assert applicability(owner, enrolled, snapshot) == {**current, "head_advanced": True, "generation_current": False}
    # The newer receipt described the edited content, so the same restore makes that one stale.
    assert applicability(owner, enrolled, second["snapshot_id"]) == {
        "applicable": False, "reason": "source_changed", "changed_paths": ["source.py"], "changed_paths_complete": True}


def test_applicability_fails_closed_for_unknown_snapshots_and_inactive_enrollments(owner, enrolled):
    unknown = {"applicable": False, "reason": "snapshot_unknown", "changed_paths": []}
    for snapshot_id in ("a" * 64, None, "not-a-digest", "A" * 64):
        assert applicability(owner, enrolled, snapshot_id) == unknown
    first = action(owner, enrolled, "validate")
    assert applicability(owner, enrolled, "a" * 64) == unknown
    inactive = {"applicable": False, "reason": "enrollment_inactive", "changed_paths": []}
    assert applicability(owner, enrolled, first["snapshot_id"], cycle="other-cycle") == inactive
    write_enrollment(enrolled, enabled=False)
    assert applicability(owner, enrolled, first["snapshot_id"]) == inactive


def test_applicability_fails_closed_when_the_generation_record_is_unreadable(owner, enrolled):
    first = action(owner, enrolled, "validate")
    tokens = list(enrolled["state"].glob("current-*.json"))
    assert len(tokens) == 1
    tokens[0].write_text("{not json")
    assert applicability(owner, enrolled, first["snapshot_id"]) == {
        "applicable": False, "reason": "generation_changed", "changed_paths": [], "error_code": "invalid_json"}


@pytest.fixture
def core():
    loader = importlib.machinery.SourceFileLoader("managed_owner_helper_fixture", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None, "Lifecycle helper must have an executable module spec"
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_helper_seam_keeps_the_legacy_checkpoint_route(core, tmp_path, monkeypatch, capsys):
    home = tmp_path.resolve()
    monkeypatch.setattr(core.Path, "home", classmethod(lambda cls: home))
    policy = home / ".config/dotfiles-ai/continuous-validation-policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"enabled": True}))
    policy.chmod(0o600)
    event = {"worktree": tmp_path / "task", "cycle": "new", "head": "a" * 40, "gates": ["domain"]}
    assert core.managed_validation_action("checkpoint", event) == routed("not_enrolled")
    assert core.managed_validation_action("enroll", {**event, "automatic": True}) == routed("not_enrolled")
    core.optional_shadow_checkpoint(event)
    assert capsys.readouterr().err == ""
    assert not (home / ".local").exists()
