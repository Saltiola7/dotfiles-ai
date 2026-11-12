"""Published-feature follow-up through real Git and synthetic native transport.

Fixture consent and GitHub observations do not authenticate a production actor.
"""
import copy
import json
import sys
from types import SimpleNamespace

import pytest
import test_dbsctrctl as fixtures
from test_initiative_local_launch import launch


@pytest.fixture
def followup(launch, monkeypatch):
    core, fixture, args = launch
    root = fixture.native_task
    branch = core.branch(root)
    original = core.git(root, "rev-parse", "HEAD").stdout.strip()
    (root / "tracked.txt").write_text("Published feature.\n")
    core.git(root, "commit", "-am", "Published feature")
    core.git(root, "push", "-u", "origin", branch)
    published = core.git(root, "rev-parse", "HEAD").stdout.strip()
    published_head = {"ref": branch, "sha": published, "repo": {"full_name": "example/test"}}
    pull = {
        "number": 17, "state": "open", "draft": False,
        "html_url": "https://github.com/example/test/pull/17",
        "head": published_head,
        # Deliberately stale: current native default must be observed separately.
        "base": {"ref": "main", "sha": "0" * 40, "repo": {"full_name": "example/test"}},
    }
    remote = core.git(root, "remote", "get-url", "origin").stdout.strip()

    def remote_head(_root, url, ref, _env):
        return core.git(root, "ls-remote", "--heads", url, ref).stdout.split()

    def native(_root, _env, endpoint):
        if endpoint == "user":
            return {"login": "example"}
        if endpoint == "repos/example/test/pulls/17":
            return copy.deepcopy(pull)
        if endpoint == "repos/example/test/git/ref/heads/main":
            sha = remote_head(root, remote, "refs/heads/main", {})[0]
            return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": sha}}
        raise AssertionError("Unexpected native read: " + endpoint)

    def push(_root, url, selected, _env):
        assert selected == branch
        core.git(root, "push", url, f"HEAD:{selected}")
        published_head["sha"] = core.git(root, "rev-parse", "HEAD").stdout.strip()

    monkeypatch.setattr(core, "github_remote_head", remote_head)
    monkeypatch.setattr(core, "external_github", native)
    monkeypatch.setattr(core, "push_github_branch", push)
    args.follow_up_pr = 17
    return SimpleNamespace(core=core, fixture=fixture, args=args, root=root,
                           pull=pull, original=original, published=published)


def register(case, capsys):
    case.args.preflight = True
    case.core.command_begin(case.args)
    preview = json.loads(capsys.readouterr().out)
    case.args.expected_launch_digest = preview["launch_digest"]
    case.args.preflight = False
    case.args.approval = "agent-confirmed"
    case.core.command_begin(case.args)
    capsys.readouterr()
    return case.core.load(case.root)


def advance_default(case):
    core, source = case.core, case.fixture.repo
    current = core.branch(source)
    core.git(source, "switch", "main")
    (source / "accepted.txt").write_text("Accepted default.\n")
    core.git(source, "add", "accepted.txt")
    core.git(source, "commit", "-m", "Accepted default")
    core.git(source, "push", "origin", "main")
    core.git(source, "switch", current)
    return core.git(source, "rev-parse", "main").stdout.strip()


def qualify(case, selectors):
    """Disposable synthetic gate executions, never production qualification."""
    for gate in fixtures.GATES:
        if gate == "release":
            continue
        argv = ["record-evidence", gate, "--authority", "fixture-follow-up"]
        for path in selectors:
            argv += ["--path", path]
        fixtures.run(case.root, *argv, "--", sys.executable, "-c", "print('passed')")


def commit_and_close(case, selectors):
    qualify(case, selectors)
    case.core.git(case.root, "add", "--", *selectors)
    fixtures.run(case.root, "gate-commit", "--message", "Reviewed follow-up",
                 "--gates", *[gate for gate in fixtures.GATES if gate != "release"],
                 "--paths", *selectors)
    for name in ("README", "BACKLOG"):
        fixtures.run(case.root, "review-artifact", name, "--result", "unchanged", "--reason", "Verified")
    fixtures.run(case.root, "review-artifact", "CHANGELOG", "--result", "changed",
                 "--reason", "Recorded", "--path", "docs/specs/test/CHANGELOG.md")


def test_followup_selector_is_only_on_begin(followup):
    core, fixture = followup.core, followup.fixture
    parsed = core.parser().parse_args([*fixture.launch_argv, "--follow-up-pr", "17"])
    assert parsed.follow_up_pr == 17
    with pytest.raises(SystemExit):
        core.parser().parse_args(["start", "--follow-up-pr", "17"])


@pytest.mark.parametrize("draft", [False, True])
def test_followup_import_preserves_published_prefix_and_existing_pr(followup, capsys, draft):
    case = followup
    case.pull["draft"] = draft
    path, record = register(case, capsys)
    binding = record["delivery"]["follow_up"]
    assert binding == {"schema_version": 1, "number": 17, "published_head": case.published,
                       "observed_base": case.original}
    imported = record["discovery_import"]
    assert imported["base_head"] == case.published
    assert record["git"]["head"] == imported["commit"]
    assert record["commits"] == []
    assert record["delivery"]["published_feature_head"] == case.published
    assert case.pull["head"]["sha"] == case.published
    assert all(g["result"] == "pending" for g in record["gates"].values()
               if g["applicability"] == "required")
    case.core.verify_discovery_import(case.root, record)
    assert case.core.read_cycle_record(case.root, path, historical=True) == record


@pytest.mark.parametrize("diverged", [False, True])
def test_followup_completes_with_contained_or_reconciled_default(followup, capsys, diverged):
    case = followup
    expected_base = advance_default(case) if diverged else case.original
    _, record = register(case, capsys)
    case.core.command_reconcile_target(SimpleNamespace(mode="prepare", json=True))
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == ("prepared" if diverged else "integrated")
    changelog = "docs/specs/test/CHANGELOG.md"
    (case.root / changelog).write_text("Qualified follow-up.\n")
    selectors = sorted({changelog, *result["staged_paths"]})
    commit_and_close(case, selectors)
    path, record = case.core.load(case.root)
    case.core.finish_push(case.root, path, record)
    assert record["state"] == "completed"
    assert record["delivery"]["pull_request"]["number"] == 17
    assert record["delivery"]["pull_request"]["draft"] is False
    assert case.core.git(case.root, "rev-parse", "origin/main").stdout.strip() == expected_base
    assert case.pull["head"]["sha"] == case.core.git(case.root, "rev-parse", "HEAD").stdout.strip()
    assert len(record["commits"]) == 1


def test_ordinary_registration_still_refuses_published_feature(followup):
    case = followup
    case.args.follow_up_pr = None
    case.args.preflight = True
    with pytest.raises(RuntimeError, match="approved base"):
        case.core.command_begin(case.args)
    assert not case.core.resolved_active_path(case.root).exists()


@pytest.mark.parametrize("change", ["closed", "fork", "target", "head", "number", "draft_type"])
def test_followup_refuses_native_identity_drift_before_registration(followup, change):
    case = followup
    if change == "closed":
        case.pull["state"] = "closed"
    elif change == "fork":
        case.pull["head"]["repo"]["full_name"] = "other/test"
    elif change == "target":
        case.pull["base"]["ref"] = "other"
    elif change == "head":
        case.pull["head"]["sha"] = case.original
    elif change == "number":
        case.pull["number"] = 18
    else:
        case.pull["draft"] = "false"
    before = case.core.git(case.root, "rev-parse", "HEAD").stdout
    case.args.preflight = True
    with pytest.raises(RuntimeError, match="follow-up"):
        case.core.command_begin(case.args)
    assert case.core.git(case.root, "rev-parse", "HEAD").stdout == before
    assert not case.core.resolved_active_path(case.root).exists()


def test_followup_rejects_default_advance_after_approval(followup, capsys):
    case = followup
    case.args.preflight = True
    case.core.command_begin(case.args)
    case.args.expected_launch_digest = json.loads(capsys.readouterr().out)["launch_digest"]
    advance_default(case)
    case.args.preflight = False
    case.args.approval = "agent-confirmed"
    with pytest.raises(RuntimeError, match="launch plan changed"):
        case.core.command_begin(case.args)
    assert not case.core.resolved_active_path(case.root).exists()


def test_followup_binding_rejects_tampered_published_prefix(followup, capsys):
    case = followup
    path, record = register(case, capsys)
    record["delivery"]["follow_up"]["published_head"] = case.original
    path.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match="follow-up"):
        case.core.read_cycle_record(case.root, path, historical=True)


def test_followup_empty_prefix_requires_exact_registered_head(followup, capsys):
    case = followup
    advance_default(case)
    _, record = register(case, capsys)
    branch = case.core.branch(case.root)
    # Only synthetic fixture refs: CAS a detached, known branch to model drift.
    case.core.git(case.root, "switch", "--detach", case.original)
    case.core.git(case.root, "update-ref", f"refs/heads/{branch}", case.original, record["git"]["head"])
    case.core.git(case.root, "switch", branch)
    assert not case.core.git(case.root, "status", "--porcelain").stdout
    with pytest.raises(RuntimeError, match="follow-up.*baseline"):
        case.core.command_reconcile_target(SimpleNamespace(mode="prepare", json=True))
    assert case.core.git(case.root, "rev-parse", "HEAD").stdout.strip() == case.original
    assert case.core.git(case.root, "rev-parse", "--verify", "-q", "MERGE_HEAD", check=False).returncode


@pytest.mark.parametrize("change", ["closed", "retargeted", "actor"])
def test_followup_rechecks_native_identity_after_import(followup, capsys, monkeypatch, change):
    case = followup
    original_git = case.core.git
    original_native = case.core.external_github
    imported = []

    def native(root, env, endpoint):
        if change == "actor" and imported and endpoint == "user":
            return {"login": "other-user"}
        return original_native(root, env, endpoint)

    def git(root, *args, **kwargs):
        result = original_git(root, *args, **kwargs)
        if args == ("commit", "-m", "docs(discovery): import approved slice authority"):
            imported.append(True)
            if change == "closed":
                case.pull["state"] = "closed"
            elif change == "retargeted":
                case.pull["base"]["ref"] = "other"
        return result

    monkeypatch.setattr(case.core, "git", git)
    monkeypatch.setattr(case.core, "external_github", native)
    with pytest.raises(RuntimeError, match="follow-up"):
        register(case, capsys)
    assert imported == [True]
    assert not case.core.resolved_active_path(case.root).exists()
    assert not (case.core.cycle_dir(case.root) / "cycles" / "local-1.json").exists()


def test_followup_without_import_uses_exact_published_baseline(followup, capsys):
    case = followup
    authority = case.core.git(case.fixture.repo, "rev-parse", "HEAD").stdout.strip()
    case.core.git(case.root, "merge", "--no-ff", authority, "-m", "Published authority")
    case.core.git(case.root, "push", "origin", case.core.branch(case.root))
    case.published = case.core.git(case.root, "rev-parse", "HEAD").stdout.strip()
    case.pull["head"]["sha"] = case.published
    _, record = register(case, capsys)
    assert "discovery_import" not in record
    assert record["git"]["head"] == record["delivery"]["published_feature_head"] == case.published
    assert record["commits"] == []


@pytest.mark.parametrize("number", [0, -1, True, 2**53])
def test_followup_rejects_invalid_selector_without_native_access(followup, monkeypatch, number):
    case = followup
    case.args.follow_up_pr = number
    case.args.preflight = True

    def forbidden(*_args):
        raise AssertionError("Invalid selector reached native access")

    monkeypatch.setattr(case.core, "external_github", forbidden)
    with pytest.raises(RuntimeError, match="follow-up"):
        case.core.command_begin(case.args)
    assert not case.core.resolved_active_path(case.root).exists()


def test_followup_rejects_unknown_ahead_commit(followup):
    case = followup
    (case.root / "tracked.txt").write_text("Unpublished change.\n")
    case.core.git(case.root, "commit", "-am", "Unknown ahead")
    before = case.core.git(case.root, "rev-parse", "HEAD").stdout
    case.args.preflight = True
    with pytest.raises(RuntimeError, match="approved base"):
        case.core.command_begin(case.args)
    assert case.core.git(case.root, "rev-parse", "HEAD").stdout == before
    assert not case.core.resolved_active_path(case.root).exists()


def test_followup_refuses_unavailable_native_evidence(followup, monkeypatch):
    case = followup
    case.args.preflight = True

    def unavailable(*_args):
        raise RuntimeError("Synthetic native evidence unavailable")

    monkeypatch.setattr(case.core, "external_github", unavailable)
    with pytest.raises(RuntimeError, match="unavailable"):
        case.core.command_begin(case.args)
    assert not case.core.resolved_active_path(case.root).exists()


def test_followup_late_default_advance_blocks_push(followup, capsys):
    case = followup
    register(case, capsys)
    path = "docs/specs/test/CHANGELOG.md"
    (case.root / path).write_text("Follow-up qualified before default advance.\n")
    commit_and_close(case, [path])
    advance_default(case)
    record_path, record = case.core.load(case.root)
    with pytest.raises(RuntimeError, match="protected base advanced without reconciliation"):
        case.core.finish_push(case.root, record_path, record)
    assert case.pull["head"]["sha"] == case.published


def test_followup_closed_pr_blocks_push_without_replacement(followup, capsys, monkeypatch):
    case = followup
    register(case, capsys)
    path = "docs/specs/test/CHANGELOG.md"
    (case.root / path).write_text("Follow-up qualified before PR closure.\n")
    commit_and_close(case, [path])
    case.pull["state"] = "closed"

    def forbidden(*_args):
        raise AssertionError("Closed selected PR triggered PR discovery or creation")

    monkeypatch.setattr(case.core, "github_json", forbidden)
    record_path, record = case.core.load(case.root)
    with pytest.raises(RuntimeError, match="follow-up"):
        case.core.finish_push(case.root, record_path, record)
    assert case.pull["head"]["sha"] == case.published


def test_followup_uncertain_push_retry_observes_existing_tip_without_repush(followup, capsys, monkeypatch):
    case = followup
    register(case, capsys)
    changelog = "docs/specs/test/CHANGELOG.md"
    (case.root / changelog).write_text("Retryable follow-up.\n")
    commit_and_close(case, [changelog])
    actual_push = case.core.push_github_branch
    pushes = []

    def interrupted(*args):
        actual_push(*args)
        pushes.append(True)
        if len(pushes) == 1:
            raise RuntimeError("Synthetic interruption after successful remote push")

    monkeypatch.setattr(case.core, "push_github_branch", interrupted)
    record_path, record = case.core.load(case.root)
    with pytest.raises(RuntimeError, match="Synthetic interruption"):
        case.core.finish_push(case.root, record_path, record)
    head = case.core.git(case.root, "rev-parse", "HEAD").stdout
    _, record = case.core.load(case.root)
    assert record["state"] == "finalizing"
    case.core.finish_push(case.root, record_path, record)
    assert record["state"] == "completed"
    assert record["delivery"]["pull_request"]["number"] == 17
    assert case.core.git(case.root, "rev-parse", "HEAD").stdout == head
    assert pushes == [True]


def test_followup_preserves_completed_prior_cycle_bytes(followup, capsys):
    case = followup
    register(case, capsys)
    changelog = "docs/specs/test/CHANGELOG.md"
    # Real retained failure and replacement executions in a disposable prior cycle.
    fixtures.run(case.root, "record-evidence", "domain", "--authority", "fixture-red",
                 "--", sys.executable, "-c", "raise SystemExit(1)")
    (case.root / changelog).write_text("Completed prior cycle.\n")
    commit_and_close(case, [changelog])
    prior_path, prior = case.core.load(case.root)
    case.core.finish_push(case.root, prior_path, prior)
    original_bytes = prior_path.read_bytes()
    capsys.readouterr()
    case.args.cycle_id = "local-2"
    case.published = case.pull["head"]["sha"]
    # Renew the synthetic Discovery authority against the newly published source;
    # stale changelog bytes must still trigger the ordinary import conflict guard.
    case.core.git(case.fixture.repo, "merge", "--no-ff", case.published,
                  "-m", "Reconcile authority before second follow-up")
    _, next_record = register(case, capsys)
    assert prior_path.read_bytes() == original_bytes
    assert next_record["cycle_id"] == "local-2"
    assert next_record["commits"] == []
    assert all(g["result"] == "pending" for g in next_record["gates"].values()
               if g["applicability"] == "required")


def test_followup_rejects_arbitrary_second_parent_despite_fresh_gates(followup, capsys):
    case = followup
    source = case.fixture.repo
    authority_branch = case.core.branch(source)
    case.core.git(source, "switch", "-c", "unrelated-fixture", case.original)
    (source / "unrelated.txt").write_text("Not accepted default history.\n")
    case.core.git(source, "add", "unrelated.txt")
    case.core.git(source, "commit", "-m", "Unapproved fixture history")
    foreign = case.core.git(source, "rev-parse", "HEAD").stdout.strip()
    case.core.git(source, "switch", authority_branch)
    register(case, capsys)
    case.core.git(case.root, "merge", "--no-commit", "--no-ff", foreign)
    changelog = "docs/specs/test/CHANGELOG.md"
    (case.root / changelog).write_text("Fresh gates cannot approve arbitrary incoming history.\n")
    commit_and_close(case, [changelog, "unrelated.txt"])
    path, record = case.core.load(case.root)
    with pytest.raises(RuntimeError, match="unapproved ancestry"):
        case.core.finish_push(case.root, path, record)
    assert case.pull["head"]["sha"] == case.published


def test_followup_cannot_replace_active_occupancy(followup, capsys):
    case = followup
    path, _ = register(case, capsys)
    before = path.read_bytes()
    case.args.cycle_id = "other-cycle"
    case.args.preflight = True
    with pytest.raises(RuntimeError, match="active|occupied|already"):
        case.core.command_begin(case.args)
    assert path.read_bytes() == before
    assert not (path.parent / "other-cycle.json").exists()


def test_followup_historical_read_is_offline_and_immutable(followup, capsys, monkeypatch):
    case = followup
    path, record = register(case, capsys)
    before = path.read_bytes()

    def forbidden(*_args):
        raise AssertionError("Historical binding read reached live credentials or API")

    for name in ("external_github", "github_environment", "github_json"):
        monkeypatch.setattr(case.core, name, forbidden)
    assert case.core.read_cycle_record(case.root, path, historical=True) == record
    assert path.read_bytes() == before


@pytest.mark.parametrize("change", ["unknown", "version", "boolean_number", "baseline"])
def test_followup_read_rejects_malformed_binding(followup, capsys, change):
    case = followup
    path, record = register(case, capsys)
    binding = record["delivery"]["follow_up"]
    if change == "unknown":
        binding["unknown"] = True
    elif change == "version":
        binding["schema_version"] = 2
    elif change == "boolean_number":
        binding["number"] = True
    else:
        record["git"]["head"] = case.published
    path.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match="follow-up"):
        case.core.read_cycle_record(case.root, path, historical=True)
