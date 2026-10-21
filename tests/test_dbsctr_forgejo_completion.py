"""Offline local completion using real Git and synthetic transport/approval.

The fixture registers through the real typed Initiative CLI handler. Its fetch
and approval are synthetic; no credentials, provider network, or real consent
are established by these tests.
"""

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import test_dbsctrctl as harness
from test_dbsctr_forgejo_identity import IDENTITY, manifest, write_manifest


@pytest.fixture
def cycle(monkeypatch, request, capsys):
    fixture = harness.DbsctrctlTest()
    fixture.setUp()
    request.addfinalizer(fixture.tearDown)
    loader = importlib.machinery.SourceFileLoader("forgejo_completion_under_test", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    authority = write_manifest(fixture.repo, manifest())
    authority_relative = authority.relative_to(fixture.repo)
    core.git(fixture.repo, "add", str(authority))
    core.git(fixture.repo, "commit", "-m", "fixture authority")
    base = core.git(fixture.repo, "rev-parse", "HEAD").stdout.strip()
    url = IDENTITY["origin"] + "/" + IDENTITY["repository"] + ".git"
    core.git(fixture.repo, "remote", "add", "origin", url)
    core.git(fixture.repo, "update-ref", "refs/remotes/origin/main", base)
    fixture.prepare_native_checkout()
    root = fixture.repo
    core.git(root, "branch", "--set-upstream-to", "origin/main")
    monkeypatch.chdir(root)
    monkeypatch.setattr(core, "root_dir", lambda: root)
    monkeypatch.setattr(core, "fetch_forgejo_branch", lambda *_args, **_kwargs: base)
    plan = fixture.plan_path()
    receipt = core.initiative_receipt(root / authority_relative, "local", root)
    argv = [
        "begin", "--cycle-id", "cycle-1", "--context", "test", "--risk", "critical",
        "--delivery-intent", "local", "--plan", str(plan), "--base-branch", "main",
        "--forge-provider", "forgejo", "--forge-origin", IDENTITY["origin"],
        "--forge-repository", IDENTITY["repository"], "--forge-account", "fixture-user",
        "--initiative-manifest", "docs/initiatives/forgejo-identity/MANIFEST.json",
        "--initiative-slice", "local", "--initiative-digest", receipt["manifest_digest"],
        "--expected-plan-digest", core.hashlib.sha256(plan.read_bytes()).hexdigest(),
        "--expected-repository-json", json.dumps(IDENTITY), "--approval", "agent-confirmed",
    ]
    args = core.parser().parse_args([*argv, "--preflight"])
    core.command_begin(args)
    preview = json.loads(capsys.readouterr().out)
    args.preflight = False
    args.expected_launch_digest = preview["launch_digest"]
    core.command_begin(args)
    capsys.readouterr()
    path = fixture.record_path()
    assert json.loads(path.read_text())["schema_version"] == 6
    original_git = core.git

    def local_git(target, *arguments, **kwargs):
        assert not any(value in {"fetch", "push", "ls-remote"} for value in arguments), arguments
        return original_git(target, *arguments, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Local completion invoked a provider, delivery, or telemetry entry point")

    monkeypatch.setattr(core, "git", local_git)
    for name in ("fetch_forgejo_branch", "github_environment", "fetch_github_branch",
                 "push_github_branch", "github_remote_head", "deliver_draft_pr",
                 "sync_source_checkout", "workflow_flush", "workflow_operation_start",
                 "workflow_operation_finish"):
        monkeypatch.setattr(core, name, forbidden)

    def invoke(*arguments):
        monkeypatch.setattr(core.sys, "argv", ["dbsctrctl", *arguments])
        return core.main()

    return SimpleNamespace(core=core, fixture=fixture, root=root, path=path,
                           base=base, invoke=invoke, forbidden=forbidden, begin_argv=argv)


def test_resume_refuses_new_comparison_base_even_with_fresh_preflight(cycle, monkeypatch, capsys):
    core, root = cycle.core, cycle.root
    monkeypatch.setattr(core, "fetch_forgejo_branch", lambda *_args, **_kwargs: cycle.base)
    args = core.parser().parse_args([*cycle.begin_argv, "--resume-existing", "--preflight"])
    core.command_begin(args)
    args.preflight = False
    args.expected_launch_digest = json.loads(capsys.readouterr().out)["launch_digest"]
    before = cycle.path.read_bytes()
    core.command_begin(args)
    assert json.loads(capsys.readouterr().out)["resumed"] is True
    assert cycle.path.read_bytes() == before

    advanced = core.git(root, "commit-tree", f"{cycle.base}^{{tree}}", "-p", cycle.base,
                        "-m", "synthetic comparison-base advance").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", advanced)
    monkeypatch.setattr(core, "fetch_forgejo_branch", lambda *_args, **_kwargs: advanced)
    args.preflight = True
    core.command_begin(args)
    preview = json.loads(capsys.readouterr().out)
    assert preview["plan"]["base_head"] == advanced
    args.preflight = False
    args.expected_launch_digest = preview["launch_digest"]
    pointer = core.resolved_active_path(root, bindings=False)
    pointer_before = pointer.read_bytes()
    with pytest.raises(RuntimeError, match="existing Initiative cycle"):
        core.command_begin(args)
    assert cycle.path.read_bytes() == before
    assert pointer.read_bytes() == pointer_before


def evidence(cycle, gate, *, paths=(), code=0):
    argv = ["record-evidence", gate, "--authority", "fixture"]
    for path in paths:
        argv.extend(["--path", path])
    cycle.core.command_record_evidence(cycle.core.parser().parse_args([
        *argv, "--", sys.executable, "-c", f"raise SystemExit({code})",
    ]))


@pytest.fixture
def ready(cycle, capsys):
    core, root = cycle.core, cycle.root
    (root / "tracked.txt").write_text("cycle source\n")
    (root / "docs/specs/test/CHANGELOG.md").write_text("Completed fixture change.\n")
    paths = ["tracked.txt", "docs/specs/test/CHANGELOG.md"]
    evidence(cycle, "domain", paths=paths)
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "fixture cycle", "--gates", "domain", "--paths", *paths,
    ]))
    for artifact, result in (("README", "unchanged"), ("BACKLOG", "unchanged"), ("CHANGELOG", "changed")):
        args = ["review-artifact", artifact, "--result", result, "--reason", "fixture review"]
        if result == "changed":
            args.extend(["--path", "docs/specs/test/CHANGELOG.md"])
        core.command_review(core.parser().parse_args(args))
    for gate in core.GATES:
        if gate not in {"domain", "release"}:
            evidence(cycle, gate)
    capsys.readouterr()
    return cycle


def test_complete_local_cli_records_exact_source_without_delivery(ready, capsys):
    core, root = ready.core, ready.root
    before = json.loads(ready.path.read_text())
    assert ready.invoke("complete-local") == 0
    result = json.loads(capsys.readouterr().out)
    record = core.read_cycle_record(root, ready.path)
    completion = record["local_completion"]
    assert result == {"status": "locally_validated", **completion}
    assert record["state"] == "completed"
    assert completion["repository"] == IDENTITY
    assert completion["base_head"] == ready.base
    assert completion["head"] == core.git(root, "rev-parse", "HEAD").stdout.strip()
    assert completion["tree"] == core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    assert completion["recorded_commits"] == [entry["id"] for entry in before["commits"]]
    assert completion["manual_delivery"] == {"status": "pending"}
    assert record["source_sync"] == {"status": "not_applicable", "reason": "local_only_completion"}
    assert not core.resolved_active_path(root, bindings=False).exists()
    assert core.git(root, "rev-parse", "origin/main").stdout.strip() == ready.base
    assert root.is_dir()


@pytest.mark.parametrize("problem", ["receipt_extra", "receipt_missing", "profile_path", "review_extra", "evidence_shape"])
def test_malformed_nested_local_record_refuses_mutation(cycle, capsys, problem):
    record = json.loads(cycle.path.read_text())
    if problem == "receipt_extra":
        record["initiative"]["unexpected"] = "untrusted"
    elif problem == "receipt_missing":
        record["initiative"].pop("initiative_id")
    elif problem == "profile_path":
        record["engineering_profile"]["path"] = "docs/specs/../../outside.md"
        record["applicability_plan"]["profile"] = "docs/specs/../../outside.md"
    elif problem == "review_extra":
        record["artifact_reviews"]["README"]["unexpected"] = "untrusted"
    else:
        record["evidence"]["items"]["ev-" + "a" * 32] = {"result": "passed"}
    cycle.path.write_text(json.dumps(record))
    before = cycle.path.read_bytes()
    assert cycle.invoke("set-gate", "domain", "--result", "pending") == 1
    assert cycle.path.read_bytes() == before
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("problem", ["pending", "failed", "dirty", "extra_commit", "profile", "changelog", "sidecar", "unbound_head"])
def test_completion_refuses_bad_source_or_evidence_without_mutation(ready, capsys, problem):
    core, root = ready.core, ready.root
    record = json.loads(ready.path.read_text())
    if problem in {"pending", "failed"}:
        record["gates"]["operate"]["result"] = problem
    elif problem == "dirty":
        (root / "tracked.txt").write_text("retain dirty source\n")
    elif problem == "extra_commit":
        core.git(root, "commit", "--allow-empty", "-m", "unrecorded")
    elif problem == "profile":
        record["engineering_profile"]["blob"] = "a" * 40
    elif problem == "changelog":
        record["artifact_reviews"]["CHANGELOG"] = {"result": "unchanged", "reason": "fixture", "reviewed_at": core.now()}
    else:
        item = record["evidence"]["items"][record["gates"]["operate"]["evidence"]]
        if problem == "sidecar":
            item["content"] = {"status": "sidecar", "path": "evidence/cycle-1/" + "a" * 64,
                               "sha256": "a" * 64, "byte_count": 4}
        else:
            item["head"] = ready.base
    ready.path.write_text(json.dumps(record))
    before = ready.path.read_bytes()
    pointer = core.resolved_active_path(root, bindings=False)
    pointer_before = pointer.read_bytes()
    assert ready.invoke("complete-local") == 1
    assert capsys.readouterr().out == ""
    assert ready.path.read_bytes() == before
    assert pointer.read_bytes() == pointer_before


def test_completed_retry_is_immutable_and_revalidates_evidence(ready, capsys):
    assert ready.invoke("complete-local") == 0
    first = json.loads(capsys.readouterr().out)
    before = ready.path.read_bytes()
    assert ready.invoke("complete-local", "--cycle-id", "cycle-1") == 0
    assert json.loads(capsys.readouterr().out) == first
    assert ready.path.read_bytes() == before
    record = json.loads(before)
    record["evidence"]["items"][record["gates"]["operate"]["evidence"]]["head"] = ready.base
    ready.path.write_text(json.dumps(record))
    assert ready.invoke("complete-local", "--cycle-id", "cycle-1") == 1
    assert capsys.readouterr().out == ""


def test_retry_refuses_source_drift_and_never_removes_foreign_pointer(ready, capsys):
    assert ready.invoke("complete-local") == 0
    capsys.readouterr()
    record = json.loads(ready.path.read_text())
    pointer = ready.core.cycle_dir(ready.root) / "worktrees" / record["worktree"]["id"] / "active"
    pointer.write_text("other-cycle\n")
    assert ready.invoke("complete-local", "--cycle-id", "cycle-1") == 0
    capsys.readouterr()
    assert pointer.read_text() == "other-cycle\n"
    ready.core.git(ready.root, "commit", "--allow-empty", "-m", "later source")
    before = ready.path.read_bytes()
    assert ready.invoke("complete-local", "--cycle-id", "cycle-1") == 1
    assert ready.path.read_bytes() == before
    assert pointer.read_text() == "other-cycle\n"


def test_crash_after_completion_save_can_retry_matching_pointer(ready, monkeypatch, capsys):
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    original = Path.unlink

    def interrupted(path, *args, **kwargs):
        if path == pointer:
            raise OSError("fixture interruption")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupted)
        assert ready.invoke("complete-local") == 1
    capsys.readouterr()
    before = ready.path.read_bytes()
    assert json.loads(before)["state"] == "completed"
    assert pointer.exists()
    assert ready.invoke("complete-local") == 0
    capsys.readouterr()
    assert ready.path.read_bytes() == before
    assert not pointer.exists()


@pytest.mark.parametrize("completed", [False, True])
def test_final_push_refuses_before_any_lock_or_completed_fast_path(ready, monkeypatch, capsys, completed):
    if completed:
        assert ready.invoke("complete-local") == 0
        capsys.readouterr()
        record = json.loads(ready.path.read_text())
        pointer = ready.core.cycle_dir(ready.root) / "worktrees" / record["worktree"]["id"] / "active"
        pointer.write_text("cycle-1\n")
    before = ready.path.read_bytes()
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    monkeypatch.setattr(ready.core, "target_lock", ready.forbidden)
    monkeypatch.setattr(ready.core, "evidence_lock", ready.forbidden)
    assert ready.invoke("final-push") == 1
    assert "local-only" in capsys.readouterr().err
    assert ready.path.read_bytes() == before and pointer.exists()
    with pytest.raises(RuntimeError, match="local-only"):
        ready.core.finish_push(ready.root, ready.path, json.loads(before))


def test_reconcile_target_refuses_without_transport_or_locks(ready, monkeypatch, capsys):
    monkeypatch.setattr(ready.core, "evidence_lock", ready.forbidden)
    before = ready.path.read_bytes()
    assert ready.invoke("reconcile-target", "--mode", "preview", "--json") == 1
    assert "local-only" in capsys.readouterr().err
    assert ready.path.read_bytes() == before


def test_explicit_id_cannot_complete_an_active_record(cycle, capsys):
    before = cycle.path.read_bytes()
    assert cycle.invoke("complete-local", "--cycle-id", "cycle-1") == 1
    assert "completed" in capsys.readouterr().err
    assert cycle.path.read_bytes() == before


def test_all_cli_mutators_share_local_completion_admission(cycle, capsys):
    core = cycle.core
    with core.evidence_lock(cycle.root, "local-mutation-cycle-1"):
        before = cycle.path.read_bytes()
        assert cycle.invoke("set-gate", "domain", "--result", "pending") == 1
        assert "busy" in capsys.readouterr().err
        assert cycle.path.read_bytes() == before
        assert cycle.invoke("status", "--json") == 0
        assert json.loads(capsys.readouterr().out)["state"] == "active"


def test_source_change_before_atomic_save_preserves_active_record(ready, monkeypatch, capsys):
    original = ready.core.status_paths
    checks = 0

    def changed(root):
        nonlocal checks
        checks += 1
        if checks == 2:
            (root / "tracked.txt").write_text("manual source change\n")
        return original(root)

    monkeypatch.setattr(ready.core, "status_paths", changed)
    before = ready.path.read_bytes()
    assert ready.invoke("complete-local") == 1
    assert "changed during completion" in capsys.readouterr().err
    assert ready.path.read_bytes() == before
    assert ready.core.resolved_active_path(ready.root, bindings=False).exists()


def test_record_change_during_validation_is_not_overwritten(ready, monkeypatch, capsys):
    original = ready.core.local_completion_source

    def changed(root, record):
        result = original(root, record)
        current = json.loads(ready.path.read_text())
        current["metrics"]["gate_reopen_count"] += 1
        ready.path.write_text(json.dumps(current))
        return result

    monkeypatch.setattr(ready.core, "local_completion_source", changed)
    assert ready.invoke("complete-local") == 1
    assert "record changed" in capsys.readouterr().err
    assert json.loads(ready.path.read_text())["state"] == "active"
    assert ready.core.resolved_active_path(ready.root, bindings=False).exists()


@pytest.mark.parametrize("problem", ["gate", "artifact", "identity"])
def test_reader_rejects_forged_completed_state(ready, capsys, problem):
    assert ready.invoke("complete-local") == 0
    capsys.readouterr()
    record = json.loads(ready.path.read_text())
    if problem == "gate":
        record["gates"]["operate"]["result"] = "pending"
    elif problem == "artifact":
        record["artifact_reviews"]["README"]["reviewed_at"] = None
    else:
        record["local_completion"]["repository"]["origin"] = "https://other.example.invalid"
    ready.path.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match="local-only"):
        ready.core.read_cycle_record(ready.root, ready.path)


@pytest.mark.parametrize("strict", [False, True])
def test_removal_retains_completed_unpublished_cycle(ready, monkeypatch, capsys, strict):
    assert ready.invoke("complete-local") == 0
    capsys.readouterr()
    monkeypatch.setattr(ready.core, "removal_run", ready.forbidden)
    if strict:
        monkeypatch.setenv("DBSCTR_REMOVAL_FD", "not-a-reservation")
        result = ready.core.workspace_remove_check(ready.root)
    else:
        result = ready.core.legacy_workspace_remove_check(ready.root)
    assert result["eligible"] is False
    assert "unpublished_local_completion" in result["reasons"]
    assert ready.root.is_dir()
