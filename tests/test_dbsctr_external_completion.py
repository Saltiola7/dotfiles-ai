"""External squash completion with real Git and synthetic native GitHub reads.

Only the GitHub transport is synthetic. These tests do not establish production
authentication, consent, CI, or deployment acceptance. Git trees, ancestry,
linked-worktree identity, gates, and evidence are exercised by the real helper.
"""

import copy
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import test_dbsctrctl as harness


ACCOUNT = "example-user"
REPOSITORY = "example-org/dotfiles-ai"
ORIGIN = f"https://github.com/{REPOSITORY}.git"
NUMBER = 17
MERGED_AT = "2026-07-12T12:00:00Z"


class NativeGitHub:
    """Fail closed on any unexpected GitHub call or remote write."""

    def __init__(self, core, root, base, head, merge):
        self.core = core
        self.root = root
        self.actor = ACCOUNT
        self.auth_error = False
        self.calls = []
        self.commit_override = None
        self.pull = {
            "number": NUMBER,
            "html_url": f"https://github.com/{REPOSITORY}/pull/{NUMBER}",
            "state": "closed",
            "draft": False,
            "merged": True,
            "merged_at": MERGED_AT,
            "merge_commit_sha": merge,
            "base": {"ref": "main", "sha": base, "repo": {"full_name": REPOSITORY}},
            "head": {
                "ref": core.branch(root), "sha": head,
                "repo": {"full_name": REPOSITORY},
            },
        }

    def environment(self, account):
        assert account == ACCOUNT
        if self.auth_error:
            raise RuntimeError("GitHub account is not authenticated: example-user")
        return {**os.environ, "GH_TOKEN": "synthetic-token-never-print"}

    def json(self, root, env, *arguments):
        assert root == self.root
        assert env["GH_TOKEN"] == "synthetic-token-never-print"
        self.calls.append(arguments)
        assert arguments[0] == "api", arguments
        assert "--hostname" in arguments and arguments[arguments.index("--hostname") + 1] == "github.com"
        assert not any(value in {"POST", "PATCH", "PUT", "DELETE"} for value in arguments)
        endpoint = next((value.lstrip("/") for value in arguments[1:]
                         if value == "user" or value.lstrip("/").startswith("repos/")), None)
        if endpoint == "user":
            return {"login": self.actor}
        if endpoint == f"repos/{REPOSITORY}/pulls/{NUMBER}":
            return copy.deepcopy(self.pull)
        if endpoint == f"repos/{REPOSITORY}/git/ref/heads/main":
            target = self.core.git(self.root, "rev-parse", "refs/remotes/origin/main").stdout.strip()
            return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": target}}
        prefix = f"repos/{REPOSITORY}/git/commits/"
        if endpoint and endpoint.startswith(prefix):
            commit = endpoint.removeprefix(prefix)
            tree = self.core.git(self.root, "rev-parse", f"{commit}^{{tree}}").stdout.strip()
            parents = self.core.git(self.root, "show", "-s", "--format=%P", commit).stdout.split()
            value = {"sha": commit, "tree": {"sha": tree},
                     "parents": [{"sha": parent} for parent in parents]}
            return {**value, **(self.commit_override or {})}
        raise AssertionError(f"Unexpected native GitHub read: {arguments!r}")


@pytest.fixture
def cycle(monkeypatch, request, capsys):
    fixture = harness.DbsctrctlTest()
    fixture.setUp()
    request.addfinalizer(fixture.tearDown)
    state = Path(fixture.temp.name) / "private-state"
    monkeypatch.setenv("DBSCTR_STATE_ROOT", str(state))
    for name in harness.STATE_ENVIRONMENT - {"DBSCTR_STATE_ROOT"}:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("GIT_NO_REPLACE_OBJECTS", raising=False)
    loader = importlib.machinery.SourceFileLoader("external_completion_under_test", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    core.git(fixture.repo, "branch", "-m", "main")
    base = core.git(fixture.repo, "rev-parse", "HEAD").stdout.strip()
    core.git(fixture.repo, "remote", "add", "origin", ORIGIN)
    core.git(fixture.repo, "update-ref", "refs/remotes/origin/main", base)
    fixture.prepare_native_checkout()
    root = fixture.repo
    core.git(root, "branch", "--set-upstream-to", "origin/main")
    monkeypatch.chdir(root)
    monkeypatch.setattr(core, "root_dir", lambda: root)
    original_git = core.git

    def git_at_transport(target, *arguments, **kwargs):
        if arguments[0] == "fetch":
            # All needed objects and refs already exist in this isolated repository.
            return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")
        if arguments[0] == "ls-remote" and "--get-url" not in arguments:
            # Retained PR head remains authoritative after feature branch deletion.
            return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")
        assert arguments[0] not in {"push", "reset", "clean"}, arguments
        if arguments[0] in {"branch", "worktree"}:
            assert not any(value in {"-d", "-D", "delete", "remove", "prune"} for value in arguments)
        return original_git(target, *arguments, **kwargs)

    monkeypatch.setattr(core, "git", git_at_transport)
    args = core.parser().parse_args([
        "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
        "--delivery-intent", "draft_pr", "--plan", str(fixture.plan_path("draft_pr")),
        "--base-branch", "main", "--github-account", ACCOUNT,
        "--github-repository", REPOSITORY,
    ])
    core.command_start(args)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("External completion invoked a delivery or cleanup operation")

    for name in ("push_github_branch", "deliver_draft_pr", "sync_source_checkout", "workflow_flush"):
        monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr(core, "workflow_operation_start", lambda *_args: None)
    monkeypatch.setattr(core, "workflow_operation_finish", lambda *_args: None)

    def invoke(*arguments):
        monkeypatch.setattr(core.sys, "argv", ["dbsctrctl", *arguments])
        return core.main()

    capsys.readouterr()
    return SimpleNamespace(core=core, fixture=fixture, root=root, path=fixture.record_path(),
                           base=base, invoke=invoke)


def record_evidence(cycle, gate, *, paths=(), code=0):
    arguments = ["record-evidence", gate, "--authority", "fixture"]
    for path in paths:
        arguments.extend(["--path", path])
    cycle.core.command_record_evidence(cycle.core.parser().parse_args([
        *arguments, "--", sys.executable, "-c", f"raise SystemExit({code})",
    ]))


@pytest.fixture
def ready(cycle, monkeypatch, capsys):
    core, root = cycle.core, cycle.root
    (root / "tracked.txt").write_text("Python 3.14 candidate\n")
    (root / "docs/specs/test/CHANGELOG.md").write_text("Completed fixture change.\n")
    paths = ["tracked.txt", "docs/specs/test/CHANGELOG.md"]
    record_evidence(cycle, "domain", paths=paths)
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "fixture candidate", "--gates", "domain", "--paths", *paths,
    ]))
    for artifact, result in (("README", "unchanged"), ("BACKLOG", "unchanged"), ("CHANGELOG", "changed")):
        arguments = ["review-artifact", artifact, "--result", result, "--reason", "fixture review"]
        if result == "changed":
            arguments.extend(["--path", "docs/specs/test/CHANGELOG.md"])
        core.command_review(core.parser().parse_args(arguments))
    for gate in core.GATES:
        if gate not in {"domain", "release"}:
            record_evidence(cycle, gate)
    cycle.head = core.git(root, "rev-parse", "HEAD").stdout.strip()
    cycle.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    cycle.merge = core.git(root, "commit-tree", cycle.tree, "-p", cycle.base,
                           "-m", "External squash PR #17").stdout.strip()
    assert cycle.head != cycle.merge
    core.git(root, "update-ref", "refs/remotes/origin/main", cycle.merge)
    cycle.native = NativeGitHub(core, root, cycle.base, cycle.head, cycle.merge)
    monkeypatch.setattr(core, "github_environment", cycle.native.environment)
    monkeypatch.setattr(core, "github_json", cycle.native.json)
    capsys.readouterr()
    return cycle


def arguments(cycle, *extra):
    return ("complete-external", "--pr-number", str(NUMBER),
            "--expected-head", cycle.head, "--expected-merge", cycle.merge, *extra)


def snapshot(cycle):
    core, root = cycle.core, cycle.root
    pointer = core.resolved_active_path(root, bindings=False)
    return {
        "record": cycle.path.read_bytes(),
        "pointer": pointer.read_bytes() if pointer.exists() else None,
        "head": core.git(root, "rev-parse", "HEAD").stdout,
        "branch": core.branch(root),
        "refs": core.git(root, "show-ref").stdout,
        "index": core.git(root, "write-tree").stdout,
        "status": core.git(root, "status", "--porcelain").stdout,
    }


def assert_rejected(cycle, capsys, *extra):
    before = snapshot(cycle)
    assert cycle.invoke(*arguments(cycle, *extra)) == 1
    output = capsys.readouterr()
    assert "dbsctrctl:" in output.err
    assert "synthetic-token-never-print" not in output.out + output.err
    assert snapshot(cycle) == before


def test_external_squash_records_native_provenance_without_redelivery(ready, capsys):
    before = json.loads(ready.path.read_text())
    assert ready.invoke(*arguments(ready)) == 0
    result = json.loads(capsys.readouterr().out)
    record = ready.core.read_cycle_record(ready.root, ready.path)
    completion = record["external_completion"]
    assert result == completion
    assert completion["schema_version"] == 1
    assert completion["status"] == "delivered_external"
    assert completion["cycle_id"] == "cycle-1"
    assert completion["repository"] == {
        "host": "github.com", "repository": REPOSITORY, "account": ACCOUNT,
    }
    assert completion["pull_request"] == {
        "number": NUMBER, "url": f"https://github.com/{REPOSITORY}/pull/{NUMBER}",
    }
    assert completion["head"] == ready.head
    assert completion["tree"] == ready.tree
    assert completion["merge"] == ready.merge
    assert completion["merge_parent"] == ready.base
    assert completion["target_branch"] == "main"
    assert completion["target_head"] == ready.merge
    assert completion["merged_at"] == MERGED_AT
    assert completion["verified_at"]
    assert completion["recorded_commits"] == [entry["id"] for entry in before["commits"]]
    assert record["state"] == "completed"
    for name in ("commits", "gates", "evidence", "artifact_reviews", "git", "worktree"):
        assert record[name] == before[name]
    assert not ready.core.resolved_active_path(ready.root, bindings=False).exists()
    assert ready.core.git(ready.root, "rev-parse", "HEAD").stdout.strip() == ready.head
    assert ready.root.is_dir()
    assert ready.native.calls


def test_preview_verifies_merge_without_changing_record_pointer_or_source(ready, capsys):
    before = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--preview")) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["head"] == ready.head
    assert result["merge"] == ready.merge
    assert snapshot(ready) == before
    assert ready.native.calls


def test_enterprise_managed_username_is_verified_by_native_identity(ready, monkeypatch, capsys):
    account = "fixture_user"
    record = json.loads(ready.path.read_text())
    record["delivery"]["github"]["account"] = account
    ready.path.write_text(json.dumps(record))
    ready.native.actor = account

    def selected_environment(selected):
        assert selected == account
        return ready.native.environment(ACCOUNT)

    monkeypatch.setattr(ready.core, "github_environment", selected_environment)
    assert ready.invoke(*arguments(ready)) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["repository"]["account"] == account


def test_verified_merge_may_be_ancestor_of_later_target_tip(ready, capsys):
    later = ready.core.git(ready.root, "commit-tree", ready.tree, "-p", ready.merge,
                            "-m", "Later target commit").stdout.strip()
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", later)
    assert ready.invoke(*arguments(ready)) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["merge"] == ready.merge
    assert result["target_head"] == later


@pytest.mark.parametrize("failure", ["missing-account", "wrong-actor"])
def test_authentication_failure_preserves_canonical_state(ready, capsys, failure):
    if failure == "missing-account":
        ready.native.auth_error = True
    else:
        ready.native.actor = "other-account"
    assert_rejected(ready, capsys)


@pytest.mark.parametrize("field,value", [
    ("state", "open"), ("merged", False), ("merged_at", None),
    ("number", 18), ("merge_commit_sha", "f" * 40),
    ("html_url", "https://github.com/other/repo/pull/17"),
])
def test_wrong_native_pull_request_preserves_canonical_state(ready, capsys, field, value):
    ready.native.pull[field] = value
    assert_rejected(ready, capsys)


@pytest.mark.parametrize("side,field,value", [
    ("head", "sha", "f" * 40), ("head", "ref", "other-feature"),
    ("head", "repo", {"full_name": "example-org/other-repository"}),
    ("base", "ref", "develop"),
    ("base", "repo", {"full_name": "other-org/dotfiles-ai"}),
])
def test_wrong_native_repository_or_ref_preserves_canonical_state(ready, capsys, side, field, value):
    ready.native.pull[side][field] = value
    assert_rejected(ready, capsys)


@pytest.mark.parametrize("field", ["sha", "tree", "parents"])
def test_native_merge_object_must_match_real_git_object(ready, capsys, field):
    ready.native.commit_override = {
        field: {"sha": "f" * 40} if field == "tree" else
        [{"sha": "f" * 40}] if field == "parents" else "f" * 40,
    }
    assert_rejected(ready, capsys)


def test_same_tree_commit_outside_target_history_is_not_delivery(ready, capsys):
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", ready.base)
    assert_rejected(ready, capsys)


def test_squash_with_different_tree_is_rejected(ready, capsys):
    wrong_tree = ready.core.git(ready.root, "rev-parse", f"{ready.base}^{{tree}}").stdout.strip()
    wrong = ready.core.git(ready.root, "commit-tree", wrong_tree, "-p", ready.base,
                           "-m", "Wrong squash contents").stdout.strip()
    ready.merge = wrong
    ready.native.pull["merge_commit_sha"] = wrong
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", wrong)
    assert_rejected(ready, capsys)


def test_two_parent_merge_is_not_accepted_as_external_squash(ready, capsys):
    wrong = ready.core.git(ready.root, "commit-tree", ready.tree,
                           "-p", ready.base, "-p", ready.head, "-m", "Merge, not squash").stdout.strip()
    ready.merge = wrong
    ready.native.pull["merge_commit_sha"] = wrong
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", wrong)
    assert_rejected(ready, capsys)


def test_matching_tree_with_unrelated_squash_parent_is_rejected(ready, capsys):
    unrelated = ready.core.git(ready.root, "commit-tree", ready.tree,
                               "-m", "Unrelated history").stdout.strip()
    wrong = ready.core.git(ready.root, "commit-tree", ready.tree, "-p", unrelated,
                           "-m", "Squash outside original base lineage").stdout.strip()
    ready.merge = wrong
    ready.native.pull["merge_commit_sha"] = wrong
    ready.native.pull["base"]["sha"] = unrelated
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", wrong)
    assert_rejected(ready, capsys)


def test_git_replace_cannot_forge_target_ancestry(ready, capsys):
    unrelated = ready.core.git(ready.root, "commit-tree", ready.tree,
                               "-m", "Unrelated target history").stdout.strip()
    replacement = ready.core.git(ready.root, "commit-tree", ready.tree, "-p", ready.merge,
                                 "-m", "Forged target ancestry").stdout.strip()
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", unrelated)
    ready.core.git(ready.root, "replace", unrelated, replacement)
    # Ordinary Git sees this forged relationship. Completion must use physical objects.
    assert ready.core.git(ready.root, "merge-base", "--is-ancestor", ready.merge, unrelated,
                          check=False).returncode == 0
    assert_rejected(ready, capsys)


def refresh_squash(cycle, parent):
    core, root = cycle.core, cycle.root
    cycle.head = core.git(root, "rev-parse", "HEAD").stdout.strip()
    cycle.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    cycle.merge = core.git(root, "commit-tree", cycle.tree, "-p", parent,
                           "-m", "Synthetic external squash").stdout.strip()
    cycle.native.pull["head"]["sha"] = cycle.head
    cycle.native.pull["base"]["sha"] = parent
    cycle.native.pull["merge_commit_sha"] = cycle.merge
    core.git(root, "update-ref", "refs/remotes/origin/main", cycle.merge)


def reconcile_source(cycle):
    core, root = cycle.core, cycle.root
    primary = Path(cycle.fixture.temp.name) / "repo"
    (primary / "upstream.txt").write_text("Synthetic upstream change\n")
    core.git(primary, "add", "upstream.txt")
    core.git(primary, "commit", "-m", "Synthetic base advance")
    advanced = core.git(primary, "rev-parse", "HEAD").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", advanced)
    core.command_reconcile_target(core.parser().parse_args([
        "reconcile-target", "--mode", "prepare", "--json",
    ]))
    record_evidence(cycle, "domain", paths=["upstream.txt"])
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "Reconcile synthetic base", "--gates", "domain",
        "--paths", "upstream.txt",
    ]))
    for gate in core.GATES:
        if gate not in {"domain", "release"}:
            record_evidence(cycle, gate)
    return advanced


def test_recorded_first_parent_reconciliation_accepts_shared_base_history(ready, capsys):
    advanced = reconcile_source(ready)
    refresh_squash(ready, advanced)
    recorded = [entry["id"] for entry in json.loads(ready.path.read_text())["commits"]]
    first_parent = ready.core.git(ready.root, "rev-list", "--first-parent", "--reverse",
                                  f"{ready.base}..HEAD").stdout.splitlines()
    full_history = ready.core.git(ready.root, "rev-list", f"{ready.base}..HEAD").stdout.splitlines()
    assert first_parent == recorded
    assert advanced in full_history and advanced not in recorded
    capsys.readouterr()
    assert ready.invoke(*arguments(ready)) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["merge_parent"] == advanced
    assert result["recorded_commits"] == recorded


def test_recorded_secondary_parent_must_belong_to_actual_squash_base(ready, capsys):
    advanced = reconcile_source(ready)
    refresh_squash(ready, ready.base)
    assert ready.core.git(ready.root, "merge-base", "--is-ancestor", advanced, ready.base,
                          check=False).returncode != 0
    capsys.readouterr()
    assert_rejected(ready, capsys)


def test_git_replace_cannot_hide_unrecorded_source_commit(ready, capsys):
    core, root = ready.core, ready.root
    original_head = ready.head
    core.git(root, "commit", "--allow-empty", "-m", "Unrecorded source commit")
    (root / "tracked.txt").write_text("Later qualified source\n")
    record_evidence(ready, "domain", paths=["tracked.txt"])
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "Later recorded source", "--gates", "domain",
        "--paths", "tracked.txt",
    ]))
    for gate in core.GATES:
        if gate not in {"domain", "release"}:
            record_evidence(ready, gate)
    refresh_squash(ready, ready.base)
    replacement = core.git(root, "commit-tree", ready.tree, "-p", original_head,
                            "-m", "Hide unrecorded source parent").stdout.strip()
    core.git(root, "replace", ready.head, replacement)
    recorded = [entry["id"] for entry in json.loads(ready.path.read_text())["commits"]]
    assert core.git(root, "rev-list", "--first-parent", "--reverse",
                    f"{ready.base}..HEAD").stdout.splitlines() == recorded
    capsys.readouterr()
    assert_rejected(ready, capsys)


def test_pending_required_gates_cannot_be_closed_by_external_merge(ready, capsys):
    record_evidence(ready, "domain", code=1)
    capsys.readouterr()
    assert_rejected(ready, capsys)


def test_new_source_head_does_not_reuse_old_gate_evidence(ready, capsys):
    ready.core.git(ready.root, "commit", "--allow-empty", "-m", "Unqualified later source")
    ready.head = ready.core.git(ready.root, "rev-parse", "HEAD").stdout.strip()
    ready.native.pull["head"]["sha"] = ready.head
    assert_rejected(ready, capsys)


@pytest.mark.parametrize("pin", ["head", "merge"])
def test_explicit_expected_object_must_match_native_provenance(ready, capsys, pin):
    setattr(ready, pin, "f" * 40)
    assert_rejected(ready, capsys)


def test_dirty_source_is_preserved_and_not_completed(ready, capsys):
    (ready.root / "tracked.txt").write_text("Uncommitted operator work\n")
    assert_rejected(ready, capsys)


def test_explicit_cycle_id_cannot_select_an_active_cycle(ready, capsys):
    assert_rejected(ready, capsys, "--cycle-id", "cycle-1")


def test_completed_retry_is_idempotent_and_reverifies_native_delivery(ready, capsys):
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    before = snapshot(ready)
    calls = len(ready.native.calls)
    assert ready.invoke(*arguments(ready, "--cycle-id", "cycle-1")) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == json.loads(ready.path.read_text())["external_completion"]
    assert snapshot(ready) == before
    assert len(ready.native.calls) > calls


def test_completed_retry_rejects_different_merge_and_retains_foreign_pointer(ready, capsys):
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    pointer.write_text("other-cycle\n")
    ready.merge = "f" * 40
    assert_rejected(ready, capsys, "--cycle-id", "cycle-1")
    assert pointer.read_text() == "other-cycle\n"


def test_final_push_cannot_redeliver_externally_completed_cycle(ready, capsys):
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    pointer.write_text("cycle-1\n")
    before = ready.path.read_bytes()
    assert ready.invoke("final-push") in {0, 1}
    output = capsys.readouterr()
    assert ready.path.read_bytes() == before
    assert "synthetic-token-never-print" not in output.out + output.err


def test_source_change_during_final_dvc_observation_is_preserved_and_rejected(ready, monkeypatch, capsys):
    core, root = ready.core, ready.root
    pointer = core.resolved_active_path(root, bindings=False)
    before_record, before_pointer = ready.path.read_bytes(), pointer.read_bytes()
    original = core.require_completion_dvc
    calls = 0

    def observe(*args):
        nonlocal calls
        calls += 1
        original(*args)
        if calls == 2:
            (root / "tracked.txt").write_text("Operator edit during final data observation\n")

    monkeypatch.setattr(core, "require_completion_dvc", observe)
    assert ready.invoke(*arguments(ready)) == 1
    output = capsys.readouterr()
    assert calls == 2
    assert "dbsctrctl:" in output.err
    assert ready.path.read_bytes() == before_record
    assert pointer.read_bytes() == before_pointer
    assert (root / "tracked.txt").read_text() == "Operator edit during final data observation\n"
    assert core.git(root, "rev-parse", "HEAD").stdout.strip() == ready.head


@pytest.mark.parametrize("changed", ["record", "pointer"])
def test_concurrent_canonical_change_during_native_recheck_is_not_overwritten(ready, monkeypatch, capsys, changed):
    core, root = ready.core, ready.root
    pointer = core.resolved_active_path(root, bindings=False)
    before_record, before_pointer = ready.path.read_bytes(), pointer.read_bytes()
    original = ready.native.json
    pulls = 0
    external_record = None

    def native_read(target, env, *args):
        nonlocal pulls, external_record
        result = original(target, env, *args)
        if f"repos/{REPOSITORY}/pulls/{NUMBER}" in args:
            pulls += 1
            if pulls == 2:
                if changed == "record":
                    record = json.loads(ready.path.read_text())
                    record["metrics"]["remediation_round_count"] += 1
                    external_record = json.dumps(record).encode()
                    ready.path.write_bytes(external_record)
                else:
                    pointer.write_text("other-cycle\n")
        return result

    monkeypatch.setattr(core, "github_json", native_read)
    assert ready.invoke(*arguments(ready)) == 1
    assert "dbsctrctl:" in capsys.readouterr().err
    assert pulls == 2
    assert ready.path.read_bytes() == (external_record if changed == "record" else before_record)
    assert pointer.read_bytes() == (b"other-cycle\n" if changed == "pointer" else before_pointer)
    assert core.git(root, "rev-parse", "HEAD").stdout.strip() == ready.head


@pytest.mark.parametrize("kind", ["target", "evidence"])
def test_contended_completion_lock_preserves_state_before_native_reads(ready, capsys, kind):
    import fcntl

    record = json.loads(ready.path.read_text())
    name = (f"{record['delivery']['lock_id']}.lock" if kind == "target"
            else f"evidence-{record['cycle_id']}.lock")
    path = ready.core.cycle_dir(ready.root) / "locks" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert_rejected(ready, capsys)
    assert ready.native.calls == []


@pytest.mark.parametrize("case", ["missing", "incomplete", "invalid-time", "pending"])
def test_missing_or_invalid_exception_cannot_dispose_required_gate(ready, capsys, case):
    record_evidence(ready, "maintain_retire", code=1)
    capsys.readouterr()
    record = json.loads(ready.path.read_text())
    gate = record["gates"]["maintain_retire"]
    exception = {
        "kind": "accepted_risk", "rationale": "Synthetic retained risk",
        "owner": "fixture-operator", "review_condition": "Review fixture acceptance",
        "approved_at": "2026-07-12T11:00:00Z",
    }
    if case == "incomplete":
        exception.pop("owner")
    elif case == "invalid-time":
        exception["approved_at"] = "invalid-time"
    elif case == "pending":
        gate["result"] = "pending"
        gate.pop("evidence", None)
    if case != "missing":
        gate["exception"] = exception
    ready.path.write_text(json.dumps(record))
    assert_rejected(ready, capsys)


@pytest.mark.parametrize("matching", [True, False])
def test_existing_draft_delivery_receipt_is_preserved_or_conflict_rejected(ready, capsys, matching):
    record = json.loads(ready.path.read_text())
    draft = {
        "number": NUMBER if matching else NUMBER + 1,
        "url": f"https://github.com/{REPOSITORY}/pull/{NUMBER if matching else NUMBER + 1}",
        "draft": True, "state": "OPEN", "verified_at": "2026-07-12T11:00:00Z",
    }
    record["delivery"]["pull_request"] = draft
    ready.path.write_text(json.dumps(record))
    if not matching:
        assert_rejected(ready, capsys)
        return
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    completed = json.loads(ready.path.read_text())
    assert completed["delivery"]["pull_request"] == draft
    assert completed["external_completion"]["pull_request"] == {
        "number": NUMBER, "url": draft["url"],
    }


def test_interrupted_pointer_removal_retries_durable_completion_without_rewriting(ready, monkeypatch, capsys):
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    original = Path.unlink

    def interrupted(path, *args, **kwargs):
        if path == pointer:
            raise OSError("fixture interruption")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupted)
        assert ready.invoke(*arguments(ready)) == 1
    assert "fixture interruption" in capsys.readouterr().err
    durable = ready.path.read_bytes()
    record = json.loads(durable)
    assert record["state"] == "completed"
    assert record["external_completion"]["merge"] == ready.merge
    assert pointer.read_text() == "cycle-1\n"
    assert ready.invoke(*arguments(ready, "--cycle-id", "cycle-1")) == 0
    assert json.loads(capsys.readouterr().out) == record["external_completion"]
    assert ready.path.read_bytes() == durable
    assert not pointer.exists()


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("merge", "f" * 64), ("merged_at", "invalid-time"),
    ("recorded_commits", []), ("status", "pending"), ("unexpected", "value"),
    ("pull_request", {"number": True, "url": f"https://github.com/{REPOSITORY}/pull/{NUMBER}"}),
])
def test_malformed_completed_receipt_is_rejected_on_read_and_retry(ready, capsys, field, value):
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    record = json.loads(ready.path.read_text())
    record["external_completion"][field] = value
    ready.path.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match="external completion"):
        ready.core.read_cycle_record(ready.root, ready.path, historical=True)
    assert_rejected(ready, capsys, "--cycle-id", "cycle-1")


def test_native_parent_list_cannot_hide_malformed_extra_entry(ready, capsys):
    ready.native.commit_override = {"parents": [{"sha": ready.base}, None]}
    assert_rejected(ready, capsys)


def test_native_canonical_repository_casing_preserves_recorded_identity(ready, capsys):
    canonical_repository = "Example-Org/Dotfiles-AI"
    canonical_url = f"https://github.com/{canonical_repository}/pull/{NUMBER}"
    ready.native.actor = ACCOUNT.upper()
    ready.native.pull["html_url"] = canonical_url
    for side in ("head", "base"):
        ready.native.pull[side]["repo"]["full_name"] = canonical_repository
    record = json.loads(ready.path.read_text())
    draft = {"number": NUMBER, "url": canonical_url, "draft": True,
             "state": "OPEN", "verified_at": "2026-07-12T11:00:00Z"}
    record["delivery"]["pull_request"] = draft
    ready.path.write_text(json.dumps(record))
    assert ready.invoke(*arguments(ready)) == 0
    receipt = json.loads(capsys.readouterr().out)
    completed = json.loads(ready.path.read_text())
    assert receipt["repository"] == record["delivery"]["github"]
    assert receipt["pull_request"]["url"] == f"https://github.com/{REPOSITORY}/pull/{NUMBER}"
    assert completed["delivery"]["pull_request"] == draft


def test_authenticated_environment_cannot_redirect_git_repository(ready, monkeypatch, capsys):
    core, root = ready.core, ready.root
    other = Path(ready.fixture.temp.name) / "repo"
    redirects = {
        "GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other),
        "GIT_COMMON_DIR": str(other / ".git"), "GIT_INDEX_FILE": str(other / ".git/index"),
        "GIT_OBJECT_DIRECTORY": str(other / ".git/objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(other / ".git/objects"),
        "GIT_NAMESPACE": "other-repository", "GIT_CEILING_DIRECTORIES": str(root.parent),
        "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
    }
    original_environment = ready.native.environment
    original_fetch = core.fetch_github_branch
    original_read = ready.native.json
    observed = set()

    def environment(account):
        return {**original_environment(account), **redirects}

    def safe_context(env):
        assert redirects.keys().isdisjoint(env)
        selected = core.LOCAL_COMPLETION_GIT.get()
        assert selected is not None
        assert redirects.keys().isdisjoint(selected)
        assert core.git(root, "rev-parse", "HEAD").stdout.strip() == ready.head

    def fetch(target, remote, url, branch, env):
        safe_context(env)
        observed.add("fetch")
        return original_fetch(target, remote, url, branch, env)

    def native_read(target, env, *args):
        safe_context(env)
        observed.add("native-proof")
        return original_read(target, env, *args)

    monkeypatch.setattr(core, "github_environment", environment)
    monkeypatch.setattr(core, "fetch_github_branch", fetch)
    monkeypatch.setattr(core, "github_json", native_read)
    assert ready.invoke(*arguments(ready)) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["head"] == ready.head
    assert observed == {"fetch", "native-proof"}
    assert core.git(other, "rev-parse", "HEAD").stdout.strip() == ready.base


@pytest.mark.parametrize("outcome", ["missing-push", "dirty-data"])
def test_changed_dvc_artifacts_require_clean_data_and_paired_push_evidence(ready, monkeypatch, capsys, outcome):
    core, root = ready.core, ready.root
    (root / ".dvc").mkdir()
    (root / ".dvc/config").write_text("[core]\n")
    (root / "data.dvc").write_text("outs:\n- path: data\n")
    paths = [".dvc/config", "data.dvc"]
    record_evidence(ready, "domain", paths=paths)
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "Record synthetic data change", "--gates", "domain",
        "--paths", *paths,
    ]))
    for gate in core.GATES:
        if gate not in {"domain", "release"}:
            record_evidence(ready, gate)
    refresh_squash(ready, ready.base)
    if outcome == "dirty-data":
        core.command_record_dvc_push(core.parser().parse_args([
            "record-dvc-push", "--head", ready.head, "--evidence", "Synthetic approved paired upload",
        ]))
    capsys.readouterr()
    original_run = core.subprocess.run
    calls = []

    def run(program, *args, **kwargs):
        if program[0] == "dvc":
            assert program == ["dvc", "status", "data.dvc"]
            assert kwargs["cwd"] == root
            calls.append(program)
            output = ("changed data.dvc\n" if outcome == "dirty-data"
                      else "Data and pipelines are up to date.\n")
            return subprocess.CompletedProcess(program, 0, stdout=output, stderr="")
        return original_run(program, *args, **kwargs)

    monkeypatch.setattr(core.subprocess, "run", run)
    before = snapshot(ready)
    assert ready.invoke(*arguments(ready)) == 1
    output = capsys.readouterr()
    expected = ("dvc status reports changed or missing data" if outcome == "dirty-data"
                else "separately approved `dvc push` evidence")
    assert expected in output.err
    assert calls == [["dvc", "status", "data.dvc"]]
    assert snapshot(ready) == before
    assert ready.native.calls == []


def test_valid_approved_exception_preserves_failed_gate_and_accepts_delivery(ready, capsys):
    core = ready.core
    record_evidence(ready, "maintain_retire", code=1)
    core.command_approve_exception(core.parser().parse_args([
        "approve-exception", "maintain_retire", "--kind", "accepted_risk",
        "--rationale", "Synthetic retained maintenance risk", "--owner", "fixture-operator",
        "--review-condition", "Review synthetic follow-up before next release",
    ]))
    before = json.loads(ready.path.read_text())
    capsys.readouterr()
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    completed = json.loads(ready.path.read_text())
    assert completed["state"] == "completed"
    assert completed["gates"]["maintain_retire"]["result"] == "failed"
    assert completed["gates"] == before["gates"]
    assert completed["evidence"] == before["evidence"]


@pytest.mark.parametrize("schema", [3, 4])
def test_adopted_older_cycle_retains_schema_history_and_adoption_backup(ready, monkeypatch, capsys, schema):
    from test_workspace_adoption import Operator

    core, root = ready.core, ready.root
    if schema == 3:
        ready.fixture.make_schema3_fixture("cycle-1", root)
    else:
        record = json.loads(ready.path.read_text())
        record["schema_version"] = 4
        record.pop("execution")
        record["worktree"].pop("git_dir")
        ready.path.write_text(json.dumps(record))
    legacy_bytes = ready.path.read_bytes()
    legacy = json.loads(legacy_bytes)
    core.command_workspace_adopt(core.parser().parse_args([
        "workspace-adopt", "--cycle-id", "cycle-1", "--preview", "--json",
    ]))
    preview = json.loads(capsys.readouterr().out)
    confirmation = f"ADOPT cycle-1 {preview['state_digest']}\n"
    with monkeypatch.context() as patch:
        patch.setattr(core.sys, "stdin", Operator(confirmation))
        core.command_workspace_adopt(core.parser().parse_args([
            "workspace-adopt", "--cycle-id", "cycle-1", "--expected-state", preview["state_digest"],
        ]))
    adopted = json.loads(ready.path.read_text())
    backup = core.common_git_dir(root) / adopted["execution"]["adoption"]["record_backup"]
    assert backup.read_bytes() == legacy_bytes
    capsys.readouterr()
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    completed = core.read_cycle_record(root, ready.path, historical=True)
    assert completed["state"] == "completed"
    assert completed["schema_version"] == schema
    assert completed["execution"] == adopted["execution"]
    for name in ("commits", "gates", "evidence", "artifact_reviews"):
        assert completed[name] == legacy[name]
    assert backup.read_bytes() == legacy_bytes
