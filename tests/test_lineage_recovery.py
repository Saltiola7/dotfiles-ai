"""Audited omitted-history recovery uses disposable Git and no provider calls."""

import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest
import test_dbsctrctl as harness
from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture, git


REASON = "PRIVATE_REASON_SENTINEL"
RESULT_FIELDS = {"schema_version", "cycle_id", "status", "state_digest", "reasons", "next_action"}


def record(path):
    return json.loads(path.read_text())


def evidence(core, gate, *, paths=(), code=0):
    argv = ["record-evidence", gate, "--authority", "synthetic-recovery-fixture"]
    for path in paths:
        argv += ["--path", path]
    args = core.parser().parse_args([*argv, "--", sys.executable, "-c", f"raise SystemExit({code})"])
    args.func(args)


def document(target, name, text="Reviewed synthetic documentation.\n"):
    relative = f"docs/operations/{name}.md"
    path = target / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return relative


def omitted_document(target, name):
    relative = document(target, name)
    git(target, "add", relative)
    git(target, "commit", "-m", f"Synthetic omitted {name}")
    return git(target, "rev-parse", "HEAD").strip()


def gate_document(core, target, name):
    relative = document(target, name)
    evidence(core, "domain", paths=(relative,))
    args = core.parser().parse_args(["gate-commit", "--message", f"Synthetic recorded {name}",
                                    "--gates", "domain", "--paths", relative])
    args.func(args)
    return git(target, "rev-parse", "HEAD").strip()


@pytest.fixture
def recovery(initiative, fixture, capsys):
    core, target, path, begin, _, _ = initiative
    core.command_begin(core.parser().parse_args([*begin, "--approval", "agent-confirmed"]))
    # Registration is genuine and local. The following fixture-only identity
    # substitution exercises GitHub-shaped admission without any live fetch/API.
    baseline = git(target, "rev-parse", "HEAD").strip()
    git(target, "update-ref", "refs/remotes/origin/base", baseline)
    git(target, "branch", "--set-upstream-to", "origin/base")
    before = record(path)
    before["delivery_intent"] = "draft_pr"
    before["git"]["upstream"] = "origin/base"
    before["git"]["remote"] = {"name": "origin", "push_url": "https://github.com/example/test.git"}
    before["delivery"] = {
        "upstream": "origin/base", "remote": "origin", "branch": "task", "base_branch": "base",
        "base_head": baseline,
        "github": {"host": "github.com", "account": "synthetic-operator", "repository": "example/test"},
        "lock_id": core.delivery_lock_id("https://github.com/example/test.git", remote_branch="task"),
    }
    core.private_json(path, before, strict=True)
    gate_document(core, target, "recorded-first")
    missing = [omitted_document(target, "first-gap")]
    accepted_file = document(fixture.repo, "accepted-source")
    git(fixture.repo, "add", accepted_file)
    git(fixture.repo, "commit", "-m", "Synthetic accepted source")
    accepted = git(fixture.repo, "rev-parse", "HEAD").strip()
    git(target, "update-ref", "refs/remotes/origin/base", accepted)
    git(target, "merge", "--no-ff", accepted, "-m", "Synthetic omitted accepted-base merge")
    merge = git(target, "rev-parse", "HEAD").strip()
    missing += [merge, omitted_document(target, "second-gap")]
    gate_document(core, target, "recorded-later")
    missing.append(omitted_document(target, "third-gap"))
    # Preserve a real red result, then demonstrate that recovery must not erase
    # its envelope even after ordinary passing replacement evidence exists.
    evidence(core, "contract", code=1)
    failed_id = record(path)["gates"]["contract"]["evidence"]
    for gate in core.GATES[:7]:
        evidence(core, gate)
    evidence(core, "operate", code=1)
    capsys.readouterr()
    argv = ["lineage-recover", "--cycle-id", "cycle-1", "--accepted-base", accepted,
            "--reason", REASON, "--json"]
    return {"core": core, "target": target, "path": path, "argv": argv, "accepted": accepted,
            "missing": missing, "merge": merge, "failed_id": failed_id, "fixture": fixture}


def snapshot(recovery):
    target = recovery["target"]
    common = Path(git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    objects = {str(p.relative_to(common / "objects")): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (common / "objects").rglob("*") if p.is_file()}
    return (git(target, "rev-parse", "HEAD"), git(target, "show-ref"),
            git(target, "ls-files", "--stage", "-z"), git(target, "status", "--porcelain=v1"), objects)


def result_body(result, status, digest=None):
    body = json.loads(result.stdout)
    assert set(body) == RESULT_FIELDS
    assert body["schema_version"] == 1 and body["cycle_id"] == "cycle-1"
    assert body["status"] == status
    if digest is not None:
        assert body["state_digest"] == digest
    public = result.stdout + result.stderr
    assert REASON not in public
    assert "PRIVATE_EXCEPTION_SENTINEL" not in public
    assert not any(part in public for part in ("/Volumes/", "/private/", "/tmp/"))
    return body


def preview(recovery):
    result = harness.run(recovery["target"], *recovery["argv"], "--preflight")
    body = result_body(result, "preflight")
    digest = body["state_digest"]
    assert isinstance(digest, str) and len(digest) == 64 and set(digest) <= set("0123456789abcdef")
    return digest


def apply_arguments(recovery, digest):
    return [*recovery["argv"], "--expected-launch-digest", digest, "--approval", "agent-confirmed"]


def apply(recovery):
    digest = preview(recovery)
    argv = apply_arguments(recovery, digest)
    result_body(harness.run(recovery["target"], *argv), "applied", digest)
    return digest, argv


def custody(recovery, name):
    common = Path(git(recovery["target"], "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    found = list((common / "dbsctr/evidence/cycle-1").rglob(name))
    assert len(found) == 1, f"Expected one recovery {name}"
    return found[0]


def test_preflight_deterministic_private_and_no_git_mutation(recovery):
    original, checkout = recovery["path"].read_bytes(), snapshot(recovery)
    assert preview(recovery) == preview(recovery)
    assert recovery["path"].read_bytes() == original
    assert snapshot(recovery) == checkout
    plan = custody(recovery, "plan.json")
    assert REASON in plan.read_text()
    assert plan.stat().st_mode & 0o777 == 0o600


def test_four_gap_apply_preserves_evidence_and_grants_no_gate_credit(recovery):
    before, checkout = record(recovery["path"]), snapshot(recovery)
    digest, argv = apply(recovery)
    after = record(recovery["path"])
    lineage = git(recovery["target"], "rev-list", "--first-parent", "--reverse",
                  f"{before['git']['head']}..HEAD").splitlines()
    assert [item["id"] for item in after["commits"]] == lineage
    for item in before["commits"]:
        assert item in after["commits"]
    assert [item for item in after["commits"] if item["id"] in recovery["missing"]] == [
        {"id": oid, "gates": []} for oid in recovery["missing"]]
    for key in ("git", "worktree", "delivery", "initiative", "initiative_approval", "discovery_import", "evidence"):
        assert after.get(key) == before.get(key)
    assert after["gates"]["review_integrate"] == {"applicability": "required", "result": "pending"}
    for gate in before["gates"]:
        if gate != "review_integrate":
            assert after["gates"][gate] == before["gates"][gate]
    assert after["evidence"]["items"][recovery["failed_id"]]["result"] == "failed"
    assert after["lineage_recovery"]["schema_version"] == 1
    assert snapshot(recovery) == checkout
    original = recovery["path"].read_bytes()
    result_body(harness.run(recovery["target"], *argv), "already_applied", digest)
    assert recovery["path"].read_bytes() == original
    status = harness.run(recovery["target"], "status", "--json")
    assert REASON not in status.stdout and str(custody(recovery, "before.json")) not in status.stdout
    assert harness.run(recovery["target"], "check", "gates", ok=False).returncode != 0


@pytest.mark.parametrize("change", ["reason", "head", "record", "base", "profile", "dirty", "push_url", "upstream"])
def test_stale_approval_preserves_state(recovery, change):
    digest = preview(recovery)
    argv = apply_arguments(recovery, digest)
    target, path = recovery["target"], recovery["path"]
    if change == "reason":
        argv[argv.index("--reason") + 1] += " changed"
    elif change == "head":
        omitted_document(target, "after-approval")
    elif change == "record":
        value = record(path)
        value["metrics"]["gate_failure_count"] += 1
        recovery["core"].private_json(path, value, strict=True)
    elif change == "base":
        git(target, "update-ref", "refs/remotes/origin/base", recovery["accepted"] + "^")
    elif change == "profile":
        (target / "docs/specs/test/README.md").write_text("Changed profile.\n")
        git(target, "add", "docs/specs/test/README.md")
        git(target, "commit", "-m", "Changed profile")
    elif change == "dirty":
        (target / "tracked.txt").write_text("Preserve unrelated operator work.\n")
    elif change == "push_url":
        git(target, "remote", "set-url", "--push", "origin", "https://github.com/example/other.git")
    else:
        git(target, "config", "branch.task.merge", "refs/heads/other")
    before, checkout = path.read_bytes(), snapshot(recovery)
    result = harness.run(target, *argv, ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert path.read_bytes() == before and snapshot(recovery) == checkout


@pytest.mark.parametrize("kind", ["code", "outside_docs", "executable", "symlink", "empty", "wrong_merge_tree"])
def test_unreviewable_omissions_refuse_without_mutation(recovery, kind):
    target = recovery["target"]
    if kind == "wrong_merge_tree":
        # Make a real two-parent commit with an extra overlay absent from either
        # parent's clean merge; this must not be laundered as accepted source.
        before = git(target, "rev-parse", "HEAD").strip()
        document(target, "unexplained-merge-overlay")
        git(target, "add", "docs/operations/unexplained-merge-overlay.md")
        tree = git(target, "write-tree").strip()
        overlay = git(target, "commit-tree", tree, "-p", before, "-p", recovery["accepted"],
                      "-m", "Synthetic wrong merge tree").strip()
        git(target, "reset", "--hard", overlay)
    elif kind == "empty":
        git(target, "commit", "--allow-empty", "-m", "Unexplained empty omission")
    else:
        relative = "code.py" if kind == "code" else "outside.md" if kind == "outside_docs" else "docs/operations/unsafe.md"
        selected = target / relative
        if kind == "symlink":
            selected.symlink_to("../../tracked.txt")
        else:
            selected.write_text("print('unreviewed')\n" if kind == "code" else "Synthetic unsafe document.\n")
            if kind == "executable":
                selected.chmod(0o755)
        git(target, "add", relative)
        git(target, "commit", "-m", "Unreviewable synthetic omission")
    before, checkout = recovery["path"].read_bytes(), snapshot(recovery)
    result = harness.run(target, *recovery["argv"], "--preflight", ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert recovery["path"].read_bytes() == before and snapshot(recovery) == checkout


@pytest.mark.parametrize("change", ["ordinary", "adopted", "schema6", "completed", "amended", "duplicate", "reordered"])
def test_unsupported_record_and_corrupt_lineage_refuse(recovery, change):
    value = record(recovery["path"])
    if change == "ordinary":
        value["initiative"] = None
    elif change == "adopted":
        value["execution"]["origin"] = "adopted"
    elif change == "schema6":
        value["schema_version"] = 6
    elif change == "completed":
        value["state"] = "completed"
    elif change == "amended":
        value["initiative_amendments"] = [{"synthetic": "unsupported"}]
    elif change == "duplicate":
        value["commits"].append(dict(value["commits"][0]))
    else:
        value["commits"].reverse()
    recovery["path"].write_text(json.dumps(value))
    original = recovery["path"].read_bytes()
    result = harness.run(recovery["target"], *recovery["argv"], "--preflight", ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert recovery["path"].read_bytes() == original


@pytest.mark.parametrize("lock", ["cycle", "target"])
def test_competing_native_writer_refuses(recovery, lock):
    core, target = recovery["core"], recovery["target"]
    before = recovery["path"].read_bytes()
    if lock == "cycle":
        context = core.evidence_lock(target, "local-mutation-cycle-1", timeout=1)
    else:
        context = core.target_lock(target, record(recovery["path"]))
    with context:
        result = harness.run(target, *recovery["argv"], "--preflight", ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert recovery["path"].read_bytes() == before


@pytest.mark.parametrize("corruption", ["changed", "missing", "symlink", "hardlink", "permissions"])
def test_corrupt_private_custody_blocks_all_readers(recovery, tmp_path, corruption):
    apply(recovery)
    owned = custody(recovery, "before.json")
    if corruption == "changed":
        owned.write_bytes(owned.read_bytes() + b"\n")
    elif corruption == "missing":
        owned.unlink()
    elif corruption == "permissions":
        owned.chmod(0o644)
    else:
        outside = tmp_path / "private-evidence"
        outside.write_bytes(owned.read_bytes())
        outside.chmod(0o600)
        owned.unlink()
        if corruption == "symlink":
            owned.symlink_to(outside)
        else:
            os.link(outside, owned)
    original = recovery["path"].read_bytes()
    assert harness.run(recovery["target"], "status", "--json", ok=False).returncode != 0
    assert recovery["path"].read_bytes() == original


@pytest.mark.parametrize("when", ["before_replace", "after_replace"])
def test_atomic_interruption_retries_without_losing_original_evidence(recovery, monkeypatch, capsys, when):
    core, path = recovery["core"], recovery["path"]
    digest = preview(recovery)
    argv = apply_arguments(recovery, digest)
    original = path.read_bytes()
    replace = core.private_json

    def interrupted(destination, value, **kwargs):
        if Path(destination) == path:
            if when == "after_replace":
                replace(destination, value, **kwargs)
            raise OSError("PRIVATE_EXCEPTION_SENTINEL")
        return replace(destination, value, **kwargs)

    monkeypatch.setattr(core, "private_json", interrupted)
    args = core.parser().parse_args(argv)
    with pytest.raises(SystemExit) as error:
        args.func(args)
    assert error.value.code == 75
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "recovery_required" and REASON not in json.dumps(body)
    assert "PRIVATE_EXCEPTION_SENTINEL" not in json.dumps(body)
    if when == "before_replace":
        assert path.read_bytes() == original
        denied = harness.run(recovery["target"], "set-gate", "review_integrate", "--result", "pending", ok=False)
        assert denied.returncode != 0 and path.read_bytes() == original
    envelope = custody(recovery, "envelope.json").read_bytes()
    monkeypatch.setattr(core, "private_json", replace)
    result = harness.run(recovery["target"], *argv)
    result_body(result, "already_applied" if when == "after_replace" else "applied", digest)
    assert custody(recovery, "before.json").read_bytes() == original
    assert custody(recovery, "envelope.json").read_bytes() == envelope
    assert record(path)["evidence"]["items"][recovery["failed_id"]]["result"] == "failed"


def test_normal_progress_retains_recovered_prefix_and_rejects_old_replay(recovery):
    _, argv = apply(recovery)
    original = record(recovery["path"])
    gate_document(recovery["core"], recovery["target"], "after-recovery")
    progressed = recovery["path"].read_bytes()
    current = record(recovery["path"])
    assert current["commits"][:len(original["commits"])] == original["commits"]
    harness.run(recovery["target"], "status", "--json")
    result = harness.run(recovery["target"], *argv, ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert recovery["path"].read_bytes() == progressed


def test_historical_read_validates_custody_without_current_head(recovery):
    apply(recovery)
    # Detached unrelated HEAD is a read-only historical-reader fixture, not a
    # supported mutation route. The private record still describes its source.
    git(recovery["target"], "switch", "--detach", recovery["accepted"])
    core = recovery["core"]
    historical = core.read_cycle_record(recovery["target"], recovery["path"], historical=True)
    assert historical["lineage_recovery"]["schema_version"] == 1
    assert historical["evidence"]["items"][recovery["failed_id"]]["result"] == "failed"


def test_old_review_cannot_dispose_reopened_gate(recovery):
    old = record(recovery["path"])
    old_id = old["gates"]["review_integrate"]["evidence"]
    apply(recovery)
    original = recovery["path"].read_bytes()
    result = harness.run(recovery["target"], "set-gate", "review_integrate", "--result", "passed",
                         "--evidence", old_id, ok=False)
    assert result.returncode == 1
    assert recovery["path"].read_bytes() == original
    evidence(recovery["core"], "review_integrate")
    current = record(recovery["path"])
    assert current["gates"]["review_integrate"]["result"] == "passed"
    assert current["gates"]["review_integrate"]["evidence"] != old_id
    assert current["evidence"]["items"][old_id] == old["evidence"]["items"][old_id]


@pytest.mark.parametrize("corruption", ["missing", "replacement_hash"])
def test_corrupt_durable_outcome_remains_actionable(recovery, corruption):
    _, argv = apply(recovery)
    outcome = custody(recovery, "outcome.json")
    if corruption == "missing":
        outcome.unlink()
    else:
        value = json.loads(outcome.read_text())
        value["replacement_sha256"] = "0" * 64
        outcome.write_text(json.dumps(value))
    original = recovery["path"].read_bytes()
    assert harness.run(recovery["target"], "status", "--json", ok=False).returncode != 0
    result = harness.run(recovery["target"], *argv, ok=False)
    assert result.returncode == 75
    result_body(result, "recovery_required")
    assert recovery["path"].read_bytes() == original


def test_failed_operating_evidence_still_blocks_final_push_before_credentials(recovery, monkeypatch):
    apply(recovery)
    core = recovery["core"]
    for name in ("README", "BACKLOG", "CHANGELOG"):
        args = core.parser().parse_args(["review-artifact", name, "--result", "unchanged",
                                        "--reason", "Synthetic unchanged artifact qualification"])
        args.func(args)

    def forbidden_credentials(*_args, **_kwargs):
        raise AssertionError("Final Push must reject incomplete gates before credential access")

    monkeypatch.setattr(core, "github_environment", forbidden_credentials)
    original = recovery["path"].read_bytes()
    with pytest.raises(RuntimeError, match="gate|operate|review"):
        core.command_final_push(core.parser().parse_args(["final-push"]))
    assert recovery["path"].read_bytes() == original


@pytest.mark.parametrize("change", ["push_url", "upstream", "base"])
def test_applied_replay_rechecks_delivery_authority(recovery, change):
    _, argv = apply(recovery)
    target = recovery["target"]
    if change == "push_url":
        git(target, "remote", "set-url", "--push", "origin", "https://github.com/example/other.git")
    elif change == "upstream":
        git(target, "config", "branch.task.merge", "refs/heads/other")
    else:
        git(target, "update-ref", "refs/remotes/origin/base", recovery["accepted"] + "^")
    original, checkout = recovery["path"].read_bytes(), snapshot(recovery)
    result = harness.run(target, *argv, ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert recovery["path"].read_bytes() == original and snapshot(recovery) == checkout


@pytest.mark.parametrize("artifact", ["envelope.json", "before.json", "outcome.json"])
@pytest.mark.parametrize("interruption", ["before_publish", "after_publish", "directory_fsync"])
def test_immutable_publication_interruptions_replay_exactly(
        recovery, monkeypatch, capsys, artifact, interruption):
    core, path = recovery["core"], recovery["path"]
    digest = preview(recovery)
    argv = apply_arguments(recovery, digest)
    original = path.read_bytes()
    replace, sync = core.os.replace, core.fsync_directory
    state = {"published": False, "staging": None, "injected": False}

    def interrupted_replace(source, destination):
        destination = Path(destination)
        selected = destination.name == artifact and destination.parent.name == digest
        if selected:
            state["staging"] = Path(source)
            if interruption == "before_publish":
                state["injected"] = True
                raise OSError("PRIVATE_EXCEPTION_SENTINEL")
        result = replace(source, destination)
        if selected:
            state["published"] = True
            if interruption == "after_publish":
                state["injected"] = True
                raise OSError("PRIVATE_EXCEPTION_SENTINEL")
        return result

    def interrupted_fsync(directory):
        if interruption == "directory_fsync" and state["published"] and not state["injected"]:
            state["injected"] = True
            raise OSError("PRIVATE_EXCEPTION_SENTINEL")
        return sync(directory)

    monkeypatch.setattr(core.os, "replace", interrupted_replace)
    monkeypatch.setattr(core, "fsync_directory", interrupted_fsync)
    monkeypatch.setattr(core, "now", lambda: "2026-11-03T01:02:03Z")
    args = core.parser().parse_args(argv)
    with pytest.raises(SystemExit) as failed:
        args.func(args)
    assert failed.value.code == 75 and state["injected"]
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "recovery_required"
    assert REASON not in json.dumps(body) and "PRIVATE_EXCEPTION_SENTINEL" not in json.dumps(body)
    assert path.read_bytes() == original
    common = core.cycle_dir(recovery["target"])
    leaves = list((common / "evidence/cycle-1/lineage-recovery").rglob("*"))
    leaves += list((common / "lineage-recovery-staging").glob("*"))
    for leaf in leaves:
        if leaf.is_file():
            assert not leaf.is_symlink() and leaf.stat().st_nlink == 1
            assert leaf.stat().st_mode & 0o777 == 0o600
    staged = state["staging"]
    if interruption == "before_publish":
        assert staged is not None and staged.exists(), "Interrupted private staging must be retained"
        retained_staging = staged.read_bytes()
    envelopes = list((common / "evidence/cycle-1/lineage-recovery").rglob("envelope.json"))
    approved = envelopes[0].read_bytes() if envelopes else None
    monkeypatch.setattr(core.os, "replace", replace)
    monkeypatch.setattr(core, "fsync_directory", sync)
    monkeypatch.setattr(core, "now", lambda: "2026-11-03T04:05:06Z")
    args.func(args)
    assert json.loads(capsys.readouterr().out)["status"] == "applied"
    assert custody(recovery, "before.json").read_bytes() == original
    if approved is not None:
        assert custody(recovery, "envelope.json").read_bytes() == approved
        assert record(path)["lineage_recovery"]["approved_at"] == "2026-11-03T01:02:03Z"
    if interruption == "before_publish":
        assert staged.read_bytes() == retained_staging
    applied = path.read_bytes()
    args.func(args)
    assert json.loads(capsys.readouterr().out)["status"] == "already_applied"
    assert path.read_bytes() == applied


@pytest.fixture
def git_boundary(fixture, monkeypatch):
    loader = importlib.machinery.SourceFileLoader("lineage_git_boundary", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    monkeypatch.chdir(fixture.repo)
    return core, fixture.repo


def merge_branches(root, *, conflict=False):
    shared = document(root, "shared", "Base content.\n")
    (root / ".gitattributes").write_text(f"{shared} merge=sentinel\n")
    git(root, "add", ".gitattributes", shared)
    git(root, "commit", "-m", "Synthetic merge boundary")
    baseline = git(root, "rev-parse", "HEAD").strip()
    git(root, "switch", "-c", "accepted")
    if conflict:
        (root / shared).write_text("Accepted conflicting content.\n")
        relative = shared
    else:
        relative = document(root, "accepted")
    git(root, "add", relative)
    git(root, "commit", "-m", "Synthetic accepted branch")
    accepted = git(root, "rev-parse", "HEAD").strip()
    git(root, "switch", "-c", "owned", baseline)
    if conflict:
        (root / shared).write_text("Owned conflicting content.\n")
        relative = shared
    else:
        relative = document(root, "owned")
    git(root, "add", relative)
    git(root, "commit", "-m", "Synthetic recorded branch")
    first = git(root, "rev-parse", "HEAD").strip()
    return baseline, first, accepted


@pytest.mark.parametrize("wrong_tree", [False, True])
def test_single_omitted_merge_proves_exact_native_tree(git_boundary, wrong_tree):
    core, root = git_boundary
    baseline, first, accepted = merge_branches(root)
    git(root, "merge", "--no-ff", accepted, "-m", "Synthetic sole missing merge")
    head = git(root, "rev-parse", "HEAD").strip()
    if wrong_tree:
        relative = document(root, "unexplained-overlay")
        git(root, "add", relative)
        tree = git(root, "write-tree").strip()
        head = git(root, "commit-tree", tree, "-p", first, "-p", accepted,
                   "-m", "Synthetic sole wrong merge").strip()
    before = {"git": {"head": baseline}, "commits": [{"id": first, "gates": ["domain"]}]}
    with core.local_completion_git_context():
        if wrong_tree:
            with pytest.raises(RuntimeError, match="exact selected accepted base"):
                core.lineage_history(root, before, head, accepted, accepted)
        else:
            restored, proofs = core.lineage_history(root, before, head, accepted, accepted)
            assert restored == [*before["commits"], {"id": head, "gates": []}]
            assert len(proofs) == 1 and proofs[0]["kind"] == "accepted_base_merge"


def test_missing_promisor_blob_never_fetches_or_rehydrates(git_boundary, tmp_path, monkeypatch):
    core, root = git_boundary
    oid = git(root, "rev-parse", "HEAD:tracked.txt").strip()
    objects = root / ".git/objects"
    missing = objects / oid[:2] / oid[2:]
    assert missing.is_file()
    marker = tmp_path / "FETCH_EXECUTED"
    transport = tmp_path / "forbidden-transport"
    transport.write_text(f"#!/bin/sh\nprintf attempted > '{marker}'\nexit 1\n")
    transport.chmod(0o700)
    git(root, "config", "extensions.partialClone", "origin")
    git(root, "config", "remote.origin.url", f"ext::{transport}")
    git(root, "config", "remote.origin.promisor", "true")
    git(root, "config", "remote.origin.partialclonefilter", "blob:none")
    git(root, "config", "protocol.ext.allow", "always")
    missing.unlink()
    popen = core.subprocess.Popen
    calls = []

    def observed_popen(argv, **kwargs):
        calls.append(argv)
        assert argv[:2] != ["git", "fetch"]
        assert kwargs["env"]["GIT_NO_LAZY_FETCH"] == "1"
        assert kwargs["env"]["GIT_ALLOW_PROTOCOL"] == ""
        return popen(argv, **kwargs)

    monkeypatch.setattr(core.subprocess, "Popen", observed_popen)
    with core.local_completion_git_context(), pytest.raises(RuntimeError, match="unavailable"):
        core.lineage_git(root, "cat-file", "-p", oid)
    assert calls and not missing.exists() and not marker.exists()


def test_local_global_merge_driver_and_fsmonitor_are_never_executed(git_boundary, tmp_path, monkeypatch):
    core, root = git_boundary
    _, first, accepted = merge_branches(root, conflict=True)
    marker = tmp_path / "CONFIGURED_COMMAND_EXECUTED"
    command = tmp_path / "configured-command"
    command.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\nexit 1\n")
    command.chmod(0o700)
    global_config = tmp_path / "global-gitconfig"
    for config in (None, global_config):
        prefix = [] if config is None else ["--file", str(config)]
        git(root, "config", *prefix, "merge.sentinel.driver", str(command))
        git(root, "config", *prefix, "core.fsmonitor", str(command))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    with core.local_completion_git_context():
        assert core.status_paths(root) == []
        with pytest.raises(RuntimeError):
            core.lineage_merge_tree(root, first, accepted)
    assert not marker.exists()


@pytest.mark.parametrize("applied", [False, True])
def test_unknown_retained_custody_is_actionable_and_never_removed(recovery, applied):
    if applied:
        _, argv = apply(recovery)
    else:
        preview(recovery)
        argv = [*recovery["argv"], "--preflight"]
    unknown = custody(recovery, "plan.json").parent / "unrecognized-retained-evidence"
    unknown.write_bytes(b"Preserve this unexplained private artifact.\n")
    unknown.chmod(0o600)
    before = recovery["path"].read_bytes()
    result = harness.run(recovery["target"], *argv, ok=False)
    assert result.returncode == 75
    result_body(result, "recovery_required")
    assert unknown.read_bytes() == b"Preserve this unexplained private artifact.\n"
    assert recovery["path"].read_bytes() == before
    if applied:
        assert harness.run(recovery["target"], "status", "--json", ok=False).returncode != 0


def test_missing_historical_document_blob_blocks_recovery_path(recovery):
    target = recovery["target"]
    relative = "docs/operations/first-gap.md"
    historical = git(target, "rev-parse", f"{recovery['missing'][0]}:{relative}").strip()
    (target / relative).write_text("A different current document keeps the old blob historical only.\n")
    git(target, "add", relative)
    git(target, "commit", "-m", "Synthetic later documentation")
    current = git(target, "rev-parse", f"HEAD:{relative}").strip()
    assert current != historical
    common = Path(git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    missing = common / "objects" / historical[:2] / historical[2:]
    assert missing.is_file()
    missing.unlink()  # Only a disposable synthetic fixture's historical object.
    assert git(target, "status", "--porcelain") == ""
    before, checkout = recovery["path"].read_bytes(), snapshot(recovery)
    result = harness.run(target, *recovery["argv"], "--preflight", ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert recovery["path"].read_bytes() == before and snapshot(recovery) == checkout
    assert not missing.exists()


@pytest.mark.parametrize("mode", ["preflight", "apply"])
def test_oversized_serialized_outcome_refuses_before_approval_publication(recovery, monkeypatch, capsys, mode):
    core, path = recovery["core"], recovery["path"]
    value = record(path)
    # A real field containing escapable text makes the nested serialized outcome
    # larger than its original record; the plan and envelope stay small.
    value["artifact_reviews"]["README"] = {
        "result": "unchanged", "reason": '"\\' * 20000, "path": None,
        "reviewed_at": "2026-01-01T00:00:00Z",
    }
    core.private_json(path, value, strict=True)
    digest = preview(recovery)
    before = path.read_bytes()
    plan = custody(recovery, "plan.json")
    limit = len(before) + 2048
    assert plan.stat().st_size < limit
    monkeypatch.setattr(core, "LINEAGE_CUSTODY_CAP", limit)
    argv = [*recovery["argv"], "--preflight"] if mode == "preflight" else apply_arguments(recovery, digest)
    args = core.parser().parse_args(argv)
    with pytest.raises(SystemExit) as error:
        args.func(args)
    assert error.value.code == 1
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "blocked" and REASON not in json.dumps(body)
    assert path.read_bytes() == before
    assert {p.name for p in plan.parent.iterdir()} == {"plan.json"}


def test_plan_capacity_refuses_new_plan_without_blocking_ordinary_work(recovery):
    digest = preview(recovery)
    parent = custody(recovery, "plan.json").parent.parent
    candidates = (f"{n:064x}" for n in range(65))
    for candidate in candidates:
        if candidate != digest and len(list(parent.iterdir())) < 64:
            (parent / candidate).mkdir(mode=0o700)
    assert len(list(parent.iterdir())) == 64
    before = recovery["path"].read_bytes()
    argv = list(recovery["argv"])
    argv[argv.index("--reason") + 1] += " another plan"
    result = harness.run(recovery["target"], *argv, "--preflight", ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert len(list(parent.iterdir())) == 64 and recovery["path"].read_bytes() == before
    harness.run(recovery["target"], "set-gate", "review_integrate", "--result", "pending")


@pytest.mark.parametrize("outcome", ["failed", "unavailable"])
def test_recovered_prerequisite_rerun_requires_ordered_fresh_evidence(recovery, outcome):
    """Recovery custody survives ordinary invalidation and ordered remediation."""
    _, replay = apply(recovery)
    core, target, path = recovery["core"], recovery["target"], recovery["path"]
    evidence(core, "review_integrate")
    for gate in core.GATES[core.GATES.index("review_integrate") + 1:]:
        if record(path)["gates"][gate]["applicability"] == "required":
            evidence(core, gate)
    qualified = record(path)
    required_tail = [gate for gate in core.GATES[1:]
                     if qualified["gates"][gate]["applicability"] == "required"]
    assert all(qualified["gates"][gate]["result"] == "passed" for gate in required_tail)
    old_tail_ids = {gate: qualified["gates"][gate]["evidence"] for gate in required_tail}
    retained = {name: custody(recovery, name).read_bytes()
                for name in ("plan.json", "before.json", "envelope.json", "outcome.json")}
    if outcome == "failed":
        evidence(core, "domain", code=1)
    else:
        args = core.parser().parse_args([
            "record-evidence", "domain", "--authority", "synthetic-unavailable-command",
            "--", str(target / "missing-synthetic-evidence-executable"),
        ])
        args.func(args)
    reopened = record(path)
    assert reopened["gates"]["domain"]["result"] == outcome
    rejected_id = reopened["gates"]["domain"]["evidence"]
    assert all(reopened["gates"][gate]["result"] == "pending" for gate in required_tail)
    assert all("evidence" not in reopened["gates"][gate]
               and "exception" not in reopened["gates"][gate] for gate in required_tail)
    assert reopened["commits"] == qualified["commits"]
    assert reopened["lineage_recovery"] == qualified["lineage_recovery"]
    assert all(reopened["evidence"]["items"][key] == value
               for key, value in qualified["evidence"]["items"].items())
    assert core.read_cycle_record(target, path, historical=True)["gates"]["domain"]["result"] == outcome
    harness.run(target, "status", "--json")

    evidence(core, "domain")
    remediated = record(path)
    assert remediated["gates"]["domain"]["result"] == "passed"
    assert all(remediated["gates"][gate]["result"] == "pending" for gate in required_tail)
    assert remediated["evidence"]["items"][rejected_id]["result"] == outcome
    for gate in required_tail:
        evidence(core, gate)
    fresh = record(path)
    assert all(fresh["gates"][gate]["result"] == "passed" for gate in required_tail)
    assert all(fresh["gates"][gate]["evidence"] != old_tail_ids[gate] for gate in required_tail)
    assert fresh["commits"] == qualified["commits"]
    assert fresh["lineage_recovery"] == qualified["lineage_recovery"]
    assert all(fresh["evidence"]["items"][key] == value
               for key, value in qualified["evidence"]["items"].items())
    assert fresh["evidence"]["items"][rejected_id]["result"] == outcome
    assert {name: custody(recovery, name).read_bytes() for name in retained} == retained
    core.read_cycle_record(target, path, historical=True)
    harness.run(target, "status", "--json")
    before_replay = path.read_bytes()
    result = harness.run(target, *replay, ok=False)
    assert result.returncode == 1
    result_body(result, "blocked")
    assert path.read_bytes() == before_replay
