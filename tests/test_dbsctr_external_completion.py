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
    assert spec is not None
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    core.git(fixture.repo, "branch", "-m", "main")
    initiative = getattr(request, "param", None) == "initiative"
    if initiative:
        manifest = harness.initiative_manifest()
        manifest["coordinator_repository"] = REPOSITORY
        manifest["contexts"][0]["repository"] = REPOSITORY
        authority = fixture.write_initiative(manifest)
        core.git(fixture.repo, "add", str(authority.relative_to(fixture.repo)))
        core.git(fixture.repo, "commit", "-m", "Synthetic Initiative authority")
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
    plan_path = fixture.plan_path("draft_pr")
    if getattr(request, "param", None) == "source-only":
        plan = json.loads(plan_path.read_text())
        for gate in ("deploy", "operate"):
            plan["gates"][gate] = {"applicability": "not_applicable", "reason": "Source-only synthetic delivery."}
        plan_path.write_text(json.dumps(plan))
    argv = [
        "begin" if initiative else "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
        "--delivery-intent", "draft_pr", "--plan", str(plan_path),
        "--base-branch", "main", "--github-account", ACCOUNT,
        "--github-repository", REPOSITORY,
    ]
    if initiative:
        # Real registration and digests; transport and consent are fixture-only.
        # This cannot establish production authorization or native actor identity.
        monkeypatch.setattr(core, "github_environment", lambda _account: {
            **os.environ, "GH_TOKEN": "synthetic-token-never-print",
        })
        receipt = core.initiative_receipt(root / "docs/initiatives/test/MANIFEST.json", "slice-a", root)
        argv.extend([
            "--initiative-manifest", "docs/initiatives/test/MANIFEST.json",
            "--initiative-slice", "slice-a", "--initiative-digest", receipt["manifest_digest"],
            "--expected-repository", REPOSITORY,
            "--expected-plan-digest", core.hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "--approval", "agent-confirmed",
        ])
        core.command_begin(core.parser().parse_args([*argv, "--preflight"]))
        preview = json.loads(capsys.readouterr().out)
        core.command_begin(core.parser().parse_args([
            *argv, "--expected-launch-digest", preview["launch_digest"],
        ]))
        record = json.loads(fixture.record_path().read_text())
        assert record["schema_version"] == 5
        assert record["execution"]["mode"] == "native_workspace"
        assert record["initiative"]["manifest_digest"] == receipt["manifest_digest"]
        assert record["initiative_approval"]["method"] == "agent_confirmed"
    else:
        core.command_start(core.parser().parse_args(argv))

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
        if gate != "domain" and core.load(root)[1]["gates"][gate]["applicability"] == "required":
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


def exact_tree_merge(ready):
    merge = ready.core.git(ready.root, "commit-tree", ready.tree,
                           "-p", ready.base, "-p", ready.head,
                           "-m", "Exact-tree merge of retained head").stdout.strip()
    ready.merge = merge
    ready.native.pull["merge_commit_sha"] = merge
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", merge)
    return merge


def test_exact_tree_two_parent_merge_records_native_provenance(ready, capsys):
    merge = exact_tree_merge(ready)
    before = json.loads(ready.path.read_text())
    assert ready.invoke(*arguments(ready)) == 0
    result = json.loads(capsys.readouterr().out)
    record = ready.core.read_cycle_record(ready.root, ready.path)
    assert result == record["external_completion"]
    assert result["status"] == "delivered_external" and result["proof"] == "exact_tree"
    assert result["head"] == ready.head and result["tree"] == ready.tree
    assert result["merge"] == merge and result["merge_parent"] == ready.base
    assert result["target_head"] == merge
    assert result["recorded_commits"] == [entry["id"] for entry in before["commits"]]
    assert record["state"] == "completed"
    assert not ready.core.resolved_active_path(ready.root, bindings=False).exists()


def test_two_parent_merge_with_changed_tree_is_rejected(ready, capsys):
    wrong_tree = ready.core.git(ready.root, "rev-parse", f"{ready.base}^{{tree}}").stdout.strip()
    wrong = ready.core.git(ready.root, "commit-tree", wrong_tree,
                           "-p", ready.base, "-p", ready.head,
                           "-m", "Reconciliation merge, not exact tree").stdout.strip()
    ready.merge = wrong
    ready.native.pull["merge_commit_sha"] = wrong
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", wrong)
    assert_rejected(ready, capsys)


def test_two_parent_merge_with_rewritten_head_parent_is_rejected(ready, capsys):
    rewritten = ready.core.git(ready.root, "commit-tree", ready.tree, "-p", ready.base,
                               "-m", "Rewritten same-tree head").stdout.strip()
    wrong = ready.core.git(ready.root, "commit-tree", ready.tree,
                           "-p", ready.base, "-p", rewritten,
                           "-m", "Merge of rewritten head").stdout.strip()
    ready.merge = wrong
    ready.native.pull["merge_commit_sha"] = wrong
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", wrong)
    assert_rejected(ready, capsys)


def test_two_parent_merge_with_unrelated_first_parent_is_rejected(ready, capsys):
    unrelated = ready.core.git(ready.root, "commit-tree", ready.tree,
                               "-m", "Unrelated base history").stdout.strip()
    wrong = ready.core.git(ready.root, "commit-tree", ready.tree,
                           "-p", unrelated, "-p", ready.head,
                           "-m", "Merge outside base lineage").stdout.strip()
    ready.merge = wrong
    ready.native.pull["merge_commit_sha"] = wrong
    ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", wrong)
    assert_rejected(ready, capsys)


def test_exact_tree_two_parent_merge_preserves_imported_source_history(cycle, monkeypatch, capsys):
    core, root = cycle.core, cycle.root
    branch = core.branch(root)
    core.git(root, "checkout", "-q", "-b", "auxiliary")
    (root / "auxiliary.txt").write_text("Imported ancestry\n")
    core.git(root, "add", "auxiliary.txt")
    core.git(root, "commit", "-q", "-m", "Imported auxiliary change")
    auxiliary = core.git(root, "rev-parse", "HEAD").stdout.strip()
    core.git(root, "checkout", "-q", branch)
    core.git(root, "merge", "--no-commit", "--no-ff", "auxiliary")
    (root / "tracked.txt").write_text("Python 3.14 candidate\n")
    (root / "docs/specs/test/CHANGELOG.md").write_text("Completed fixture change.\n")
    core.git(root, "add", "tracked.txt", "docs/specs/test/CHANGELOG.md", "auxiliary.txt")
    paths = ["tracked.txt", "docs/specs/test/CHANGELOG.md", "auxiliary.txt"]
    record_evidence(cycle, "domain", paths=paths)
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "fixture candidate importing ancestry",
        "--gates", "domain", "--paths", *paths,
    ]))
    for artifact, result in (("README", "unchanged"), ("BACKLOG", "unchanged"), ("CHANGELOG", "changed")):
        arguments_review = ["review-artifact", artifact, "--result", result, "--reason", "fixture review"]
        if result == "changed":
            arguments_review.extend(["--path", "docs/specs/test/CHANGELOG.md"])
        core.command_review(core.parser().parse_args(arguments_review))
    for gate in core.GATES:
        if gate not in {"domain", "release"}:
            record_evidence(cycle, gate)
    cycle.head = core.git(root, "rev-parse", "HEAD").stdout.strip()
    cycle.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    imported = core.git(root, "show", "-s", "--format=%P", cycle.head).stdout.split()
    assert imported == [core.git(root, "rev-parse", f"{cycle.head}^1").stdout.strip(), auxiliary]
    cycle.merge = core.git(root, "commit-tree", cycle.tree, "-p", cycle.base, "-p", cycle.head,
                           "-m", "External exact-tree merge PR #17").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", cycle.merge)
    cycle.native = NativeGitHub(core, root, cycle.base, cycle.head, cycle.merge)
    monkeypatch.setattr(core, "github_environment", cycle.native.environment)
    monkeypatch.setattr(core, "github_json", cycle.native.json)
    capsys.readouterr()
    assert cycle.invoke(*arguments(cycle)) == 0
    result = json.loads(capsys.readouterr().out)
    record = core.read_cycle_record(root, cycle.path)
    assert result == record["external_completion"]
    assert result["merge_parent"] == cycle.base
    assert result["recorded_commits"] == [cycle.head]
    assert record["state"] == "completed"
    assert core.git(root, "merge-base", "--is-ancestor", auxiliary,
                    f"refs/remotes/origin/main", check=False).returncode == 0


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


@pytest.mark.parametrize("advance_target", [False, True])
def test_interrupted_pointer_removal_retries_durable_completion_without_rewriting(ready, monkeypatch, capsys, advance_target):
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
    if advance_target:
        later_tree = rebased_tree(ready, ready.head, extra="Unrelated later target work\n")
        later = ready.core.git(ready.root, "commit-tree", later_tree, "-p", ready.merge,
                               "-m", "Later unrelated target change").stdout.strip()
        ready.core.git(ready.root, "update-ref", "refs/remotes/origin/main", later)
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


@pytest.mark.parametrize("cycle", [None, "source-only"], indirect=True)
def test_authenticated_environment_cannot_redirect_git_repository(ready, monkeypatch, capsys, request):
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
    extra = []
    if request.node.callspec.params["cycle"] == "source-only":
        from test_completion_segments import segments
        selector, original_read = segments(ready)
        extra = ["--delivery-segment", selector]
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
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, *extra)) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["head"] == ready.head
    # Reconciliation consumes retained local objects without fetching; the
    # original standalone route must still qualify its authenticated fetch.
    assert observed == ({"native-proof"} if extra else {"fetch", "native-proof"})
    assert core.git(other, "rev-parse", "HEAD").stdout.strip() == ready.base
    assert core.LOCAL_COMPLETION_GIT.get() is None


@pytest.mark.parametrize("failure", [False, True])
def test_final_target_pin_restores_caller_context(cycle, monkeypatch, failure):
    core, root = cycle.core, cycle.root
    record = core.load(root)[1]
    target = "a" * 40
    calls = []

    def native_read(_root, _env, _endpoint):
        selected = core.LOCAL_COMPLETION_GIT.get()
        assert selected is not None
        assert set(core.GIT_REPOSITORY_REDIRECTS).isdisjoint(selected)
        calls.append("read")
        if failure:
            raise RuntimeError("synthetic native read unavailable")
        return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": target}}

    monkeypatch.setattr(core, "external_github", native_read)
    outer = {"GIT_DIR": "synthetic-caller-must-not-redirect"}
    token = core.LOCAL_COMPLETION_GIT.set(outer)
    try:
        if failure:
            with pytest.raises(RuntimeError, match="synthetic native read unavailable"):
                core.require_completion_target_pin(root, record, {}, target)
        else:
            core.require_completion_target_pin(root, record, {}, target)
        assert core.LOCAL_COMPLETION_GIT.get() is outer
        assert calls == ["read"]
    finally:
        core.LOCAL_COMPLETION_GIT.reset(token)


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


def rebased_tree(cycle, source, *, extra="unrelated base work\n", phase=None):
    """Construct the integration tree independently of the replay verifier."""
    core, root = cycle.core, cycle.root
    index = Path(cycle.fixture.temp.name) / "rebased-fixture-index"
    env = {**core.GIT_REPOSITORY_ENV, "GIT_INDEX_FILE": str(index)}
    core.git(root, "read-tree", source, env=env)
    contents = {"unrelated.txt": extra}
    if phase is not None:
        contents["phase.py"] = phase
    for name, content in contents.items():
        blob_file = Path(cycle.fixture.temp.name) / "rebased-fixture-blob"
        blob_file.write_text(content)
        blob = core.git(root, "hash-object", "-w", str(blob_file)).stdout.strip()
        core.git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{name}", env=env)
    return core.git(root, "write-tree", env=env).stdout.strip()


@pytest.fixture
def rebased(cycle, monkeypatch, capsys, request):
    core, root = cycle.core, cycle.root
    sources = []
    phases = (
        ("domain", {"tracked.txt": "Domain work\n", "docs/specs/test/CHANGELOG.md": "Rebased phase history.\n"}),
        ("behavior", {"phase.py": "def phase():\n    return 1\n"}),
        ("spec", {"phase.py": "def phase():\n    return 2\n"}),
    )
    attribute = getattr(request, "param", None)
    if attribute is not None:
        assert attribute in {"merge", "filter"}
        phases[0][1][".gitattributes"] = f"*.py {attribute}=fixture\n"
    for gate, changes in phases:
        for name, content in changes.items():
            (root / name).write_text(content)
        record_evidence(cycle, gate, paths=list(changes))
        core.command_gate_commit(core.parser().parse_args([
            "gate-commit", "--message", f"[{gate}] fixture phase", "--gates", gate,
            "--paths", *changes,
        ]))
        sources.append(core.git(root, "rev-parse", "HEAD").stdout.strip())
    for artifact, result in (("README", "unchanged"), ("BACKLOG", "unchanged"), ("CHANGELOG", "changed")):
        review = ["review-artifact", artifact, "--result", result, "--reason", "fixture review"]
        if result == "changed":
            review.extend(["--path", "docs/specs/test/CHANGELOG.md"])
        core.command_review(core.parser().parse_args(review))
    for gate in core.GATES:
        if gate not in {"domain", "behavior", "spec", "release"}:
            record_evidence(cycle, gate)
    cycle.sources = sources
    cycle.head = sources[-1]
    cycle.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    base_tree = rebased_tree(cycle, cycle.base)
    cycle.landed_base = core.git(root, "commit-tree", base_tree, "-p", cycle.base,
                                 "-m", "Independent base change").stdout.strip()
    parent = cycle.landed_base
    cycle.landed = []
    for source, (gate, _) in zip(sources, phases):
        tree = rebased_tree(cycle, source)
        parent = core.git(root, "commit-tree", tree, "-p", parent,
                          "-m", f"[{gate}] fixture phase").stdout.strip()
        cycle.landed.append(parent)
    cycle.merge = parent
    core.git(root, "update-ref", "refs/remotes/origin/main", cycle.merge)
    cycle.native = NativeGitHub(core, root, cycle.landed_base, cycle.head, cycle.merge)
    cycle.default_branch = "main"
    cycle.introductions = {oid: [copy.deepcopy(cycle.native.pull)] for oid in cycle.landed}
    original_read = cycle.native.json

    def native_read(root, env, *arguments):
        if arguments[-1] == f"repos/{REPOSITORY}":
            cycle.native.calls.append(arguments)
            return {"full_name": REPOSITORY, "default_branch": cycle.default_branch}
        prefix, suffix = f"repos/{REPOSITORY}/commits/", "/pulls?per_page=2"
        if arguments[-1].startswith(prefix) and arguments[-1].endswith(suffix):
            cycle.native.calls.append(arguments)
            oid = arguments[-1][len(prefix):-len(suffix)]
            return copy.deepcopy(cycle.introductions.get(oid, []))
        return original_read(root, env, *arguments)

    monkeypatch.setattr(core, "github_environment", cycle.native.environment)
    monkeypatch.setattr(core, "github_json", native_read)
    capsys.readouterr()
    return cycle


def rebase_arguments(cycle, *extra):
    return (*arguments(cycle), "--proof", "rebased_commits", *extra)


def reject_rebased(cycle, capsys):
    before = snapshot(cycle)
    assert cycle.invoke(*rebase_arguments(cycle)) == 1
    output = capsys.readouterr()
    assert "dbsctrctl:" in output.err
    assert "synthetic-token-never-print" not in output.out + output.err
    assert snapshot(cycle) == before


def replace_rebased_result(cycle, tree, parent):
    cycle.merge = cycle.core.git(cycle.root, "commit-tree", tree, "-p", parent,
                                  "-m", "Altered integration result").stdout.strip()
    cycle.native.pull["merge_commit_sha"] = cycle.merge
    cycle.core.git(cycle.root, "update-ref", "refs/remotes/origin/main", cycle.merge)


def test_rebased_phases_preserve_original_evidence_and_landed_attribution(rebased, capsys):
    before = json.loads(rebased.path.read_text())
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    receipt = json.loads(capsys.readouterr().out)
    record = rebased.core.read_cycle_record(rebased.root, rebased.path)
    assert receipt == record["external_completion"]
    assert receipt["schema_version"] == 2
    assert receipt["proof"] == "rebased_commits"
    assert receipt["landed_base"] == rebased.landed_base
    assert receipt["commit_mapping"] == [
        {"original": source, "landed": landed}
        for source, landed in zip(rebased.sources, rebased.landed)
    ]
    assert all(source != landed for source, landed in zip(rebased.sources, rebased.landed))
    assert receipt["head"] == rebased.head
    assert receipt["tree"] == rebased.tree
    assert receipt["merge"] == rebased.merge
    assert receipt["source_retention_ref"] == "refs/dbsctr/evidence/cycle-1"
    assert rebased.core.git(rebased.root, "rev-parse", receipt["source_retention_ref"]).stdout.strip() == rebased.head
    assert rebased.core.git(rebased.root, "rev-parse", f"{rebased.merge}^{{tree}}").stdout.strip() != rebased.tree
    for field in ("git", "worktree", "commits", "gates", "evidence", "artifact_reviews"):
        assert record[field] == before[field]
    assert not rebased.core.resolved_active_path(rebased.root, bindings=False).exists()


def test_rebased_preview_has_no_completion_or_retention_ref_side_effects(rebased, capsys):
    before = snapshot(rebased)
    assert rebased.invoke(*rebase_arguments(rebased, "--preview")) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["proof"] == "rebased_commits"
    assert snapshot(rebased) == before


def test_rebased_retry_preserves_original_receipt_after_later_target_advance(rebased, capsys):
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    receipt = json.loads(capsys.readouterr().out)
    saved = rebased.path.read_bytes()
    later = rebased.core.git(rebased.root, "commit-tree", f"{rebased.merge}^{{tree}}",
                              "-p", rebased.merge, "-m", "Later target advance").stdout.strip()
    rebased.core.git(rebased.root, "update-ref", "refs/remotes/origin/main", later)
    assert rebased.invoke(*rebase_arguments(rebased, "--cycle-id", "cycle-1")) == 0
    assert json.loads(capsys.readouterr().out) == receipt
    assert rebased.path.read_bytes() == saved


def test_rebased_ref_collision_preserves_original_owner(rebased, capsys):
    ref = "refs/dbsctr/evidence/cycle-1"
    rebased.core.git(rebased.root, "update-ref", ref, rebased.base)
    reject_rebased(rebased, capsys)


def test_rebased_existing_matching_retention_ref_recovers_after_interruption(rebased, capsys):
    ref = "refs/dbsctr/evidence/cycle-1"
    rebased.core.git(rebased.root, "update-ref", ref, rebased.head)
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    assert json.loads(capsys.readouterr().out)["source_retention_ref"] == ref


def test_rebased_completed_ref_drift_is_not_silently_repaired(rebased, capsys):
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    capsys.readouterr()
    rebased.core.git(rebased.root, "update-ref", "refs/dbsctr/evidence/cycle-1", rebased.base)
    before = snapshot(rebased)
    assert rebased.invoke(*rebase_arguments(rebased, "--cycle-id", "cycle-1")) == 1
    capsys.readouterr()
    assert snapshot(rebased) == before


def test_rebased_intermediate_branch_is_not_ultimate_delivery(rebased, capsys):
    rebased.default_branch = "production"
    reject_rebased(rebased, capsys)


@pytest.mark.parametrize("problem", ["squash", "drop", "edit", "whitespace", "reorder"])
def test_rebased_non_corresponding_phase_history_is_retained(rebased, capsys, problem):
    core, root = rebased.core, rebased.root
    if problem == "squash":
        tree, parent = rebased_tree(rebased, rebased.head), rebased.landed_base
    elif problem == "drop":
        tree, parent = rebased_tree(rebased, rebased.head), rebased.landed[0]
    elif problem in {"edit", "whitespace"}:
        phase = "def phase():\n    return 3\n" if problem == "edit" else "def phase():\n\treturn 2\n"
        tree, parent = rebased_tree(rebased, rebased.head, phase=phase), rebased.landed[1]
    else:
        # The same final tree does not prove the intermediate phases survived.
        first = core.git(root, "commit-tree", rebased_tree(rebased, rebased.sources[0]),
                         "-p", rebased.landed_base, "-m", "Domain phase").stdout.strip()
        middle = core.git(root, "commit-tree", rebased_tree(rebased, rebased.sources[2]),
                          "-p", first, "-m", "Final behavior introduced early").stdout.strip()
        tree, parent = rebased_tree(rebased, rebased.head), middle
    replace_rebased_result(rebased, tree, parent)
    reject_rebased(rebased, capsys)


def test_rebased_pending_gate_cannot_be_closed_by_merged_pr(rebased, capsys):
    record = json.loads(rebased.path.read_text())
    record["gates"]["maintain_retire"]["result"] = "pending"
    record["gates"]["maintain_retire"].pop("evidence", None)
    rebased.path.write_text(json.dumps(record))
    reject_rebased(rebased, capsys)


@pytest.mark.parametrize("problem", ["dirty", "native-parent", "native-head"])
def test_rebased_changed_source_or_native_identity_is_retained(rebased, capsys, problem):
    if problem == "dirty":
        (rebased.root / "tracked.txt").write_text("Uncommitted retained work\n")
    elif problem == "native-parent":
        rebased.native.commit_override = {"parents": [{"sha": rebased.base}]}
    else:
        rebased.native.pull["head"]["sha"] = rebased.base
    reject_rebased(rebased, capsys)


@pytest.mark.parametrize("shape", ["empty", "merge"])
def test_rebased_non_linear_or_empty_source_is_not_partially_attributed(rebased, capsys, shape):
    core, root = rebased.core, rebased.root
    source_args = ["commit-tree", rebased.tree, "-p", rebased.head]
    if shape == "merge":
        source_args[1] = rebased_tree(rebased, rebased.head)
        source_args.extend(["-p", rebased.landed_base])
    source = core.git(root, *source_args, "-m", f"Recorded {shape} source commit").stdout.strip()
    core.git(root, "update-ref", "refs/heads/" + core.branch(root), source, rebased.head)
    core.git(root, "read-tree", "--reset", "-u", source)
    record = json.loads(rebased.path.read_text())
    record["commits"].append({"id": source, "gates": []})
    rebased.path.write_text(json.dumps(record))
    rebased.head = source
    rebased.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    rebased.native.pull["head"]["sha"] = source
    for gate in core.GATES:
        if gate != "release":
            record_evidence(rebased, gate)
    # Count and terminal contents are still consistent; the unsupported source
    # shape itself must not receive a fabricated correspondence.
    replace_rebased_result(rebased, rebased_tree(rebased, source), rebased.landed[-1])
    capsys.readouterr()
    reject_rebased(rebased, capsys)


def test_rebased_interrupted_pointer_removal_keeps_receipt_and_source_ref(rebased, monkeypatch, capsys):
    core, root = rebased.core, rebased.root
    pointer = core.resolved_active_path(root, bindings=False)
    original_unlink = Path.unlink

    def interrupted(path, *args, **kwargs):
        if path == pointer:
            raise OSError("fixture interruption")
        return original_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupted)
        assert rebased.invoke(*rebase_arguments(rebased)) == 1
    assert "fixture interruption" in capsys.readouterr().err
    durable = rebased.path.read_bytes()
    receipt = json.loads(durable)["external_completion"]
    assert receipt["proof"] == "rebased_commits"
    assert core.git(root, "rev-parse", receipt["source_retention_ref"]).stdout.strip() == rebased.head
    assert pointer.exists()
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    assert json.loads(capsys.readouterr().out) == receipt
    assert rebased.path.read_bytes() == durable
    assert not pointer.exists()


def test_rebased_evidence_ref_keeps_original_commits_after_feature_refs_and_gc(rebased, capsys):
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    receipt = json.loads(capsys.readouterr().out)
    core = rebased.core
    mirror = Path(rebased.fixture.temp.name) / "retention-proof.git"
    core.git(rebased.root, "clone", "--mirror", "--no-local",
             str(core.common_git_dir(rebased.root)), str(mirror))
    refs = core.git(mirror, "for-each-ref", "--format=%(refname)").stdout.splitlines()
    for ref in refs:
        if ref != receipt["source_retention_ref"]:
            core.git(mirror, "update-ref", "-d", ref)
    core.git(mirror, "reflog", "expire", "--expire=now", "--all")
    core.git(mirror, "gc", "--prune=now")
    assert core.git(mirror, "for-each-ref", "--format=%(refname)").stdout.splitlines() == [receipt["source_retention_ref"]]
    for original in rebased.sources:
        assert core.git(mirror, "cat-file", "-t", original).stdout.strip() == "commit"


def test_rebased_phase_already_introduced_by_prior_pr_is_not_attributed_again(rebased, capsys):
    # Walking three commits backwards and replaying all three deltas still
    # matches perfectly. The first one was introduced by an earlier PR, though;
    # this current PR only adds the last two, so it did not preserve all phases.
    rebased.native.pull["base"]["sha"] = rebased.landed[0]
    for oid in rebased.landed:
        rebased.introductions[oid] = [copy.deepcopy(rebased.native.pull)]
    older = copy.deepcopy(rebased.native.pull)
    older.update(number=NUMBER - 1, html_url=f"https://github.com/{REPOSITORY}/pull/{NUMBER - 1}",
                 merged_at="2026-07-11T12:00:00Z")
    rebased.introductions[rebased.landed[0]] = [older]
    reject_rebased(rebased, capsys)


@pytest.mark.parametrize("membership", ["absent", "ambiguous", "foreign"])
def test_rebased_landed_commit_requires_one_native_introducing_pr(rebased, capsys, membership):
    current = copy.deepcopy(rebased.native.pull)
    if membership == "absent":
        introductions = []
    elif membership == "ambiguous":
        introductions = [current, copy.deepcopy(current)]
    else:
        current["base"]["repo"]["full_name"] = "another-owner/another-repository"
        introductions = [current]
    rebased.introductions[rebased.landed[1]] = introductions
    reject_rebased(rebased, capsys)


@pytest.mark.parametrize("changed", ["source", "record", "pointer"])
def test_rebased_change_during_source_ref_creation_is_never_overwritten(rebased, monkeypatch, capsys, changed):
    core, root = rebased.core, rebased.root
    pointer = core.resolved_active_path(root, bindings=False)
    before_record, before_pointer = rebased.path.read_bytes(), pointer.read_bytes()
    original_git = core.lineage_git
    external_record = None
    mutations = 0

    def ref_write(target, *args):
        nonlocal external_record, mutations
        result = original_git(target, *args)
        if args[:3] == ("update-ref", "--no-deref", "refs/dbsctr/evidence/cycle-1"):
            mutations += 1
            if changed == "source":
                (root / "tracked.txt").write_text("Concurrent uncommitted source edit\n")
            elif changed == "record":
                record = json.loads(rebased.path.read_text())
                record["metrics"]["remediation_round_count"] += 1
                external_record = json.dumps(record).encode()
                rebased.path.write_bytes(external_record)
            else:
                pointer.write_text("other-cycle\n")
        return result

    monkeypatch.setattr(core, "lineage_git", ref_write)
    assert rebased.invoke(*rebase_arguments(rebased)) == 1
    assert "dbsctrctl:" in capsys.readouterr().err
    assert mutations == 1
    assert rebased.path.read_bytes() == (external_record if changed == "record" else before_record)
    assert pointer.read_bytes() == (b"other-cycle\n" if changed == "pointer" else before_pointer)
    assert json.loads(rebased.path.read_text())["state"] != "completed"
    if changed == "source":
        assert (root / "tracked.txt").read_text() == "Concurrent uncommitted source edit\n"
    # Keeping this orphan is safe; completing over the competing state is not.
    assert core.git(root, "rev-parse", "refs/dbsctr/evidence/cycle-1").stdout.strip() == rebased.head


@pytest.mark.parametrize("state", ["completed", "finalizing"])
def test_rebased_native_dispatch_allows_handler_owned_completion_states(rebased, monkeypatch, capsys, state):
    core, root = rebased.core, rebased.root
    pointer = core.resolved_active_path(root, bindings=False)
    if state == "completed":
        assert rebased.invoke(*rebase_arguments(rebased)) == 0
        capsys.readouterr()
        before = rebased.path.read_bytes()
        assert not pointer.exists()
    else:
        record = json.loads(rebased.path.read_text())
        record["state"] = "finalizing"
        rebased.path.write_text(json.dumps(record))
        before = None
    monkeypatch.setattr(core, "local_dispatch_selection", lambda args: (
        root, pointer, rebased.path, core.read_cycle_record(root, rebased.path, historical=True)))
    extra = ("--cycle-id", "cycle-1") if state == "completed" else ()
    assert rebased.invoke(*rebase_arguments(rebased, *extra)) == 0
    assert json.loads(capsys.readouterr().out)["proof"] == "rebased_commits"
    assert json.loads(rebased.path.read_text())["state"] == "completed"
    assert not pointer.exists()
    if before is not None:
        assert rebased.path.read_bytes() == before


def test_rebased_native_dispatch_preserves_pending_lineage_guard(rebased, monkeypatch, capsys):
    core, root = rebased.core, rebased.root
    pointer = core.resolved_active_path(root, bindings=False)
    monkeypatch.setattr(core, "local_dispatch_selection", lambda args: (
        root, pointer, rebased.path, core.read_cycle_record(root, rebased.path, historical=True)))
    called = []

    def pending(target, record):
        assert target == root and record["cycle_id"] == "cycle-1"
        called.append(True)
        raise RuntimeError("prepared lineage recovery requires reconciliation")

    monkeypatch.setattr(core, "lineage_pending_guard", pending)
    before = snapshot(rebased)
    assert rebased.invoke(*rebase_arguments(rebased)) == 1
    assert "prepared lineage recovery requires reconciliation" in capsys.readouterr().err
    assert called == [True]
    assert snapshot(rebased) == before
    assert rebased.native.calls == []


@pytest.mark.parametrize("setting", ["merge.fixture.driver", "filter.fixture.clean"])
def test_rebased_configured_executable_transform_is_refused_without_execution(rebased, capsys, setting):
    marker = Path(rebased.fixture.temp.name) / "transform-executed"
    rebased.core.git(rebased.root, "config", "--local", setting, f"touch '{marker}'")
    reject_rebased(rebased, capsys)
    assert not marker.exists()


@pytest.mark.parametrize("rebased", ["merge", "filter"], indirect=True)
def test_rebased_declared_transform_attributes_are_refused(rebased, capsys):
    reject_rebased(rebased, capsys)


def test_rebased_grafts_are_refused(rebased, capsys):
    core, root = rebased.core, rebased.root
    graft = Path(core.git(root, "rev-parse", "--git-path", "info/grafts").stdout.strip())
    graft = graft if graft.is_absolute() else root / graft
    graft.parent.mkdir(parents=True, exist_ok=True)
    graft.write_text(rebased.head + " " + rebased.base + "\n")
    reject_rebased(rebased, capsys)


@pytest.mark.parametrize("field", ["head", "merge_parent"])
def test_rebased_malformed_receipt_object_identity_fails_closed(rebased, capsys, field):
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    capsys.readouterr()
    record = json.loads(rebased.path.read_text())
    record["external_completion"][field] = [rebased.head]
    rebased.path.write_text(json.dumps(record))
    before = snapshot(rebased)
    rebased.native.calls.clear()
    assert rebased.invoke(*rebase_arguments(rebased, "--cycle-id", "cycle-1")) == 1
    assert "invalid external completion" in capsys.readouterr().err
    assert snapshot(rebased) == before
    assert rebased.native.calls == []



@pytest.mark.parametrize("field", ["head", "merge_parent"])
def test_rebased_correspondence_relationships_are_validated_on_record_read(rebased, capsys, field):
    assert rebased.invoke(*rebase_arguments(rebased)) == 0
    capsys.readouterr()
    record = json.loads(rebased.path.read_text())
    record["external_completion"][field] = rebased.sources[0] if field == "head" else rebased.base
    rebased.path.write_text(json.dumps(record))
    before = snapshot(rebased)
    rebased.native.calls.clear()
    assert rebased.invoke(*rebase_arguments(rebased, "--cycle-id", "cycle-1")) == 1
    assert "invalid rebased completion correspondence" in capsys.readouterr().err
    assert snapshot(rebased) == before
    assert rebased.native.calls == []



@pytest.mark.parametrize("changed", ["drift", "missing"])
def test_rebased_retention_changed_during_final_source_check_blocks_completion(rebased, monkeypatch, capsys, changed):
    core, root = rebased.core, rebased.root
    pointer = core.resolved_active_path(root, bindings=False)
    before_record, before_pointer = rebased.path.read_bytes(), pointer.read_bytes()
    original_source = core.external_source
    calls = 0

    def inspect_source(*args):
        nonlocal calls
        result = original_source(*args)
        calls += 1
        if calls == 2:
            ref = "refs/dbsctr/evidence/cycle-1"
            if changed == "missing":
                core.git(root, "update-ref", "-d", ref)
            else:
                core.git(root, "update-ref", ref, rebased.base)
        return result

    monkeypatch.setattr(core, "external_source", inspect_source)
    assert rebased.invoke(*rebase_arguments(rebased)) == 1
    assert "source retention ref" in capsys.readouterr().err
    assert calls == 2
    assert rebased.path.read_bytes() == before_record
    assert pointer.read_bytes() == before_pointer

@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("preview", [False, True], ids=["retry", "preview"])
def test_native_initiative_external_completion_and_completed_retry(ready, capsys, preview):
    assert ready.invoke(*arguments(ready)) == 0
    receipt = json.loads(capsys.readouterr().out)
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    assert not pointer.exists()
    before = snapshot(ready)
    native_reads = len(ready.native.calls)
    extra = ["--cycle-id", "cycle-1", *(["--preview"] if preview else [])]
    assert ready.invoke(*arguments(ready, *extra)) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == receipt
    assert snapshot(ready) == before
    assert len(ready.native.calls) > native_reads


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
def test_native_initiative_recovers_interrupted_pointer_cleanup(ready, monkeypatch, capsys):
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    original = Path.unlink

    def interrupted(path, *args, **kwargs):
        if path == pointer:
            raise OSError("Synthetic Initiative pointer interruption")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupted)
        assert ready.invoke(*arguments(ready)) == 1
    assert "Synthetic Initiative pointer interruption" in capsys.readouterr().err
    before = ready.path.read_bytes()
    receipt = json.loads(before)["external_completion"]
    assert pointer.read_text() == "cycle-1\n"
    assert ready.invoke(*arguments(ready, "--cycle-id", "cycle-1")) == 0
    assert json.loads(capsys.readouterr().out) == receipt
    assert ready.path.read_bytes() == before
    assert not pointer.exists()


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
def test_native_initiative_retry_preserves_foreign_pointer(ready, capsys):
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    pointer.write_text("foreign-cycle\n")
    native_reads = len(ready.native.calls)
    assert_rejected(ready, capsys, "--cycle-id", "cycle-1")
    assert pointer.read_text() == "foreign-cycle\n"
    assert len(ready.native.calls) == native_reads


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
def test_native_initiative_retry_rejects_misnamed_completed_record(ready, capsys):
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    completed = ready.path.read_bytes()
    copied = ready.path.with_name("other-completed-cycle.json")
    copied.write_bytes(completed)
    copied.chmod(0o600)
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    assert not pointer.exists()
    native_reads = len(ready.native.calls)

    assert_rejected(ready, capsys, "--cycle-id", copied.stem)

    assert ready.path.read_bytes() == completed
    assert copied.read_bytes() == completed
    assert not pointer.exists()
    assert len(ready.native.calls) == native_reads


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("completed", [False, True], ids=["initial", "completed-retry"])
def test_native_initiative_completion_respects_shared_mutation_lease(ready, capsys, completed):
    import fcntl

    if completed:
        assert ready.invoke(*arguments(ready)) == 0
        capsys.readouterr()
    lock = ready.core.cycle_dir(ready.root) / "locks/evidence-local-mutation-cycle-1.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    before = snapshot(ready)
    native_reads = len(ready.native.calls)
    with lock.open("a+") as stream:
        lock.chmod(0o600)
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        extra = ["--cycle-id", "cycle-1"] if completed else []
        assert ready.invoke(*arguments(ready, *extra)) == 1
        assert "busy" in capsys.readouterr().err
    assert snapshot(ready) == before
    assert len(ready.native.calls) == native_reads


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
def test_native_initiative_holds_mutation_lease_during_native_verification(ready, monkeypatch, capsys):
    core = ready.core
    original = ready.native.json
    attempted = False
    inner_status = None
    before = json.loads(ready.path.read_text())["artifact_reviews"]

    def native_read(target, env, *args):
        nonlocal attempted, inner_status
        if "user" in args and not attempted:
            attempted = True
            with monkeypatch.context() as patch:
                patch.setattr(core.sys, "argv", [
                    "dbsctrctl", "review-artifact", "README", "--result", "unchanged",
                    "--reason", "Concurrent synthetic writer",
                ])
                inner_status = core.main()
        return original(target, env, *args)

    monkeypatch.setattr(core, "github_json", native_read)
    assert ready.invoke(*arguments(ready)) == 0
    output = capsys.readouterr()
    assert attempted and inner_status == 1
    assert "busy" in output.err
    assert json.loads(output.out)["status"] == "delivered_external"
    assert json.loads(ready.path.read_text())["artifact_reviews"] == before


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("command", ["review-artifact", "record-evidence"])
def test_native_initiative_completed_generic_mutators_remain_blocked(ready, monkeypatch, capsys, command):
    assert ready.invoke(*arguments(ready)) == 0
    capsys.readouterr()
    pointer = ready.core.resolved_active_path(ready.root, bindings=False)
    pointer.write_text("cycle-1\n")
    before = snapshot(ready)

    original_popen = ready.core.subprocess.Popen

    def no_evidence_process(program, *args, **kwargs):
        if program == [sys.executable, "-c", "print('passed')"]:
            raise AssertionError("Completed generic mutator launched an evidence process")
        return original_popen(program, *args, **kwargs)

    monkeypatch.setattr(ready.core.subprocess, "Popen", no_evidence_process)
    argv = ([command, "README", "--result", "unchanged", "--reason", "Synthetic rewrite"]
            if command == "review-artifact" else
            [command, "domain", "--authority", "fixture", "--", sys.executable, "-c", "print('passed')"])
    assert ready.invoke(*argv) == 1
    assert "completed" in capsys.readouterr().err
    assert snapshot(ready) == before


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("failure", ["native", "evidence-lock", "target-lock"])
def test_native_initiative_failure_releases_owned_mutation_lease(ready, capsys, failure):
    import contextlib
    import fcntl

    locks = ready.core.cycle_dir(ready.root) / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    record = json.loads(ready.path.read_text())
    name = ("evidence-cycle-1.lock" if failure == "evidence-lock"
            else f"{record['delivery']['lock_id']}.lock")
    with contextlib.ExitStack() as stack:
        if failure == "native":
            ready.native.actor = "wrong-synthetic-account"
        else:
            stream = stack.enter_context((locks / name).open("a+"))
            (locks / name).chmod(0o600)
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert_rejected(ready, capsys)
    lease = locks / "evidence-local-mutation-cycle-1.lock"
    with lease.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ready.native.actor = ACCOUNT
    assert ready.invoke(*arguments(ready)) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "delivered_external"


@pytest.fixture
def retained_lineage_plan(ready, capsys):
    """Create actual recovery custody, then restore an otherwise eligible source.

    The retained plan becomes stale after restoration, but an approved transaction
    still requires reconciliation. Restoring this disposable checkout prevents an
    unrelated unrecorded-commit error from hiding a missing custody admission check.
    """
    core, root = ready.core, ready.root
    original = snapshot(ready)
    relative = "docs/specs/test/CHANGELOG.md"
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.base, ready.merge)
    with (root / relative).open("a") as stream:
        stream.write("Synthetic omitted documentation for recovery custody.\n")
    core.git(root, "add", relative)
    core.git(root, "commit", "-m", "Synthetic omitted documentation")
    omitted = core.git(root, "rev-parse", "HEAD").stdout.strip()
    argv = ["lineage-recover", "--cycle-id", "cycle-1", "--accepted-base", ready.base,
            "--reason", "PRIVATE_RECOVERY_REASON_SENTINEL", "--json"]
    assert ready.invoke(*argv, "--preflight") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "preflight"
    digest = result["state_digest"]
    directory = core.lineage_location(root, "cycle-1", digest, "plan.json").parent
    assert {path.name for path in directory.iterdir()} == {"plan.json"}

    def restore_source():
        core.git(root, "restore", "--source", ready.head, "--staged", "--worktree", "--", relative)
        core.git(root, "update-ref", "HEAD", ready.head, omitted)
        core.git(root, "update-ref", "refs/remotes/origin/main", ready.merge, ready.base)
        assert snapshot(ready) == original

    ready.lineage = SimpleNamespace(argv=argv, digest=digest, directory=directory,
                                    restore_source=restore_source)
    return ready


def lineage_custody_snapshot(cycle):
    directory = cycle.lineage.directory
    return {str(path.relative_to(directory)): (path.stat().st_mode, path.read_bytes())
            for path in directory.iterdir()}


def assert_lineage_blocks_external(cycle, monkeypatch, capsys, preview, message):
    """Check actual custody admission under the shared lease, not a mocked guard."""
    import fcntl

    core, root = cycle.core, cycle.root
    before = snapshot(cycle)
    custody = lineage_custody_snapshot(cycle)
    native_reads = len(cycle.native.calls)
    lease = core.cycle_dir(root) / "locks/evidence-local-mutation-cycle-1.lock"
    original_custody = core.lineage_custody
    original_environment = core.github_environment
    custody_reads, credential_reads = [], []

    def observe_custody(target, identifier):
        assert target.resolve() == root.resolve() and identifier == "cycle-1"
        with lease.open("r+") as stream:
            with pytest.raises(BlockingIOError):
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        custody_reads.append(identifier)
        return original_custody(target, identifier)

    def observe_credentials(account):
        credential_reads.append(account)
        return original_environment(account)

    monkeypatch.setattr(core, "lineage_custody", observe_custody)
    monkeypatch.setattr(core, "github_environment", observe_credentials)
    assert cycle.invoke(*arguments(cycle, *(["--preview"] if preview else []))) == 1
    output = capsys.readouterr()
    assert message in output.err
    assert "PRIVATE_RECOVERY_REASON_SENTINEL" not in output.out + output.err
    assert "PRIVATE_RECOVERY_INTERRUPTION_SENTINEL" not in output.out + output.err
    assert "synthetic-token-never-print" not in output.out + output.err
    assert custody_reads and not credential_reads
    assert len(cycle.native.calls) == native_reads
    assert snapshot(cycle) == before
    assert lineage_custody_snapshot(cycle) == custody
    with lease.open("r+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("preview", [False, True], ids=["initial", "preview"])
def test_native_initiative_pending_lineage_blocks_external_before_native_reads(
        retained_lineage_plan, monkeypatch, capsys, preview):
    ready = retained_lineage_plan
    core = ready.core
    original = ready.path.read_bytes()
    replace = core.private_json
    interrupted = False

    def interrupt_replacement(destination, value, **kwargs):
        nonlocal interrupted
        if Path(destination) == ready.path:
            interrupted = True
            raise OSError("PRIVATE_RECOVERY_INTERRUPTION_SENTINEL")
        return replace(destination, value, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(core, "private_json", interrupt_replacement)
        with pytest.raises(SystemExit) as error:
            ready.invoke(*ready.lineage.argv, "--expected-launch-digest", ready.lineage.digest,
                         "--approval", "agent-confirmed")
        assert error.value.code == 75
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "recovery_required" and interrupted
    assert ready.path.read_bytes() == original
    assert {path.name for path in ready.lineage.directory.iterdir()} == {
        "plan.json", "envelope.json", "before.json", "outcome.json",
    }
    assert (ready.lineage.directory / "before.json").read_bytes() == original
    envelope = json.loads((ready.lineage.directory / "envelope.json").read_text())
    assert envelope["approval_method"] == "agent_confirmed"
    assert envelope["plan"]["head"] != ready.head
    ready.lineage.restore_source()

    assert_lineage_blocks_external(ready, monkeypatch, capsys, preview,
                                  "prepared lineage recovery requires reconciliation")


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("preview", [False, True], ids=["initial", "preview"])
def test_native_initiative_unknown_lineage_custody_blocks_external_before_native_reads(
        retained_lineage_plan, monkeypatch, capsys, preview):
    ready = retained_lineage_plan
    unknown = ready.lineage.directory / "unrecognized-retained-evidence"
    unknown.write_bytes(b"Preserve this unexplained private artifact.\n")
    unknown.chmod(0o600)
    ready.lineage.restore_source()

    assert_lineage_blocks_external(ready, monkeypatch, capsys, preview,
                                  "lineage recovery custody requires reconciliation")


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("preview", [False, True], ids=["initial", "preview"])
def test_native_initiative_plan_only_lineage_custody_allows_external_completion(
        retained_lineage_plan, capsys, preview):
    ready = retained_lineage_plan
    ready.lineage.restore_source()
    custody = lineage_custody_snapshot(ready)
    before = snapshot(ready)

    assert ready.invoke(*arguments(ready, *(["--preview"] if preview else []))) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "delivered_external"
    assert ready.native.calls
    assert lineage_custody_snapshot(ready) == custody
    if preview:
        assert snapshot(ready) == before
    else:
        assert json.loads(ready.path.read_text())["state"] == "completed"


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True, ids=["native-initiative"])
@pytest.mark.parametrize("drift", ["delivery", "worktree", "execution", "completed-predicate"])
def test_native_initiative_revalidates_admission_after_evidence_lock(
        ready, monkeypatch, capsys, drift):
    """A valid record drift before the locked reread must precede credentials."""
    import contextlib

    core = ready.core
    if drift == "completed-predicate":
        assert ready.invoke(*arguments(ready)) == 0
        capsys.readouterr()
    original_lock = core.evidence_lock
    observed = {"injected": False, "credentials": [], "snapshot": None}
    native_reads = len(ready.native.calls)

    @contextlib.contextmanager
    def changed_after_lock(target, identifier, *args, **kwargs):
        with original_lock(target, identifier, *args, **kwargs):
            if identifier == "cycle-1" and not observed["injected"]:
                changed = json.loads(ready.path.read_text())
                if drift == "delivery":
                    changed["delivery"]["github"]["account"] = "other-synthetic-user"
                elif drift == "worktree":
                    changed["worktree"]["created_by_dbsctr"] = not changed["worktree"]["created_by_dbsctr"]
                elif drift == "execution":
                    changed.pop("execution")
                else:
                    changed["state"] = "finalizing"
                    for name in ("external_completion", "completed_at", "source_sync"):
                        changed.pop(name, None)
                ready.path.write_text(json.dumps(changed))
                # Real validation admits this historical record; schema failure
                # must not masquerade as the handler's binding revalidation.
                assert core.read_cycle_record(ready.root, ready.path, historical=True) == changed
                observed["injected"] = True
                observed["snapshot"] = snapshot(ready)
            yield

    def observed_environment(account):
        observed["credentials"].append(account)
        raise AssertionError("Credential read preceded locked admission revalidation")

    monkeypatch.setattr(core, "evidence_lock", changed_after_lock)
    monkeypatch.setattr(core, "github_environment", observed_environment)
    extra = ["--cycle-id", "cycle-1"] if drift == "completed-predicate" else []
    assert ready.invoke(*arguments(ready, *extra)) == 1
    output = capsys.readouterr()
    assert observed["injected"]
    expected = ("explicit cycle ID requires an already externally completed record"
                if drift == "completed-predicate" else "binding changed")
    assert expected in output.err
    assert not observed["credentials"]
    assert len(ready.native.calls) == native_reads
    assert snapshot(ready) == observed["snapshot"]
    assert "synthetic-token-never-print" not in output.out + output.err
