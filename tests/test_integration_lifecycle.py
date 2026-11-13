"""Private local custody is immutable; data never claims native admission."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from types import FunctionType, ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import lifecycle as l, runtime as r, core as c
from integration_coordinator.client import Status, VerifiedOutcome
from integration_coordinator.gitproof import GitObjects, ProofPort
from test_integration_gitproof import objects, series as git_series, commit as git_commit
from test_dbsctr_external_completion import cycle, ready, record_evidence, rebased_tree, NUMBER, REPOSITORY, ACCOUNT


def birth() -> dict[str, object]:
    return {"cycle_id": "cycle-1", "launch_digest": "d" * 64, "record_digest": "a" * 64, "policy_digest": "b" * 64,
            "enrollment_digest": "c" * 64, "remote_repository": "fixture/project",
            "target_ref": "refs/heads/main", "control_ref": "refs/heads/control",
            "guarded_refresh": False, "delivery_mode": "ordinary"}


def test_private_custody_is_idempotent_immutable_and_read_only_when_absent(tmp_path: Path) -> None:
    common = tmp_path / "common"; common.mkdir()
    store = l.Custody(common)
    assert not store.directory.exists()
    with pytest.raises(FileNotFoundError):
        store.read("birth", "0" * 64)
    assert not store.directory.exists()
    digest = store.write("birth", birth())
    path = store.object_path(digest)
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.stat().st_nlink == 1
    assert store.read("birth", digest) == birth()
    original = path.read_bytes()
    assert store.write("birth", birth()) == digest
    assert path.read_bytes() == original
    assert hashlib.sha256(original).hexdigest() == digest
    assert json.loads(original)["schema_version"] == 1


@pytest.mark.parametrize("problem", ["symlink", "hardlink", "public", "changed", "oversize"])
def test_custody_refuses_replaced_or_unbounded_objects(tmp_path: Path, problem: str) -> None:
    common = tmp_path / "common"; common.mkdir()
    store = l.Custody(common); digest = store.write("birth", birth())
    path = store.object_path(digest)
    if problem == "symlink":
        other = path.with_suffix(".other"); path.rename(other); path.symlink_to(other)
    elif problem == "hardlink":
        os.link(path, path.with_suffix(".other"))
    elif problem == "public":
        path.chmod(0o644)
    elif problem == "changed":
        path.write_bytes(b"{}")
    else:
        path.write_bytes(b"x" * (l.MAX_PRIVATE_BYTES + 1))
    with pytest.raises((ValueError, OSError)):
        store.read("birth", digest)


@pytest.mark.parametrize("change", [{"unexpected": False}, {"guarded_refresh": 1},
                                    {"record_digest": "x"}, {"target_ref": "refs/heads/control"}])
def test_birth_records_are_closed_and_typed(tmp_path: Path, change: dict[str, object]) -> None:
    common = tmp_path / "common"; common.mkdir(); store = l.Custody(common)
    with pytest.raises(ValueError):
        store.write("birth", birth() | change)
    assert not store.directory.exists()


def test_approval_v2_requires_actual_private_authorization_chain(tmp_path: Path) -> None:
    common = tmp_path / "common"; common.mkdir(); store = l.Custody(common)
    approval = {"schema_version": 2, "method": "integration_grant", "launch_digest": "a" * 64,
                "authorization_digest": "b" * 64, "authorized_at": "2026-11-13T00:00:00Z"}
    with pytest.raises(FileNotFoundError):
        store.verify_approval(approval, "child")


def test_custody_rejects_symlinked_common_or_directory(tmp_path: Path) -> None:
    common = tmp_path / "common"; common.mkdir()
    linked = tmp_path / "linked"; linked.symlink_to(common, target_is_directory=True)
    with pytest.raises(ValueError):
        l.Custody(linked)
    store = l.Custody(common)
    (common / "dbsctr").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        store.write("birth", birth())


def replayed_fixture(ready: SimpleNamespace, source_head: str, base_parent: str,
                     extra: str, message: str) -> tuple[str, str]:
    core, root = ready.core, ready.root
    base = core.git(root, "commit-tree", rebased_tree(ready, base_parent, extra=extra), "-p", base_parent,
                    "-m", message).stdout.strip()
    author = core.git(root, "show", "-s", "--format=%an%x00%ae%x00%aI", source_head).stdout.rstrip("\n").split("\0")
    original_message = core.git(root, "show", "-s", "--format=%B", source_head).stdout.rstrip("\n")
    env = {**core.GIT_REPOSITORY_ENV, "GIT_AUTHOR_NAME": author[0], "GIT_AUTHOR_EMAIL": author[1], "GIT_AUTHOR_DATE": author[2]}
    head = core.git(root, "commit-tree", rebased_tree(ready, source_head, extra=extra), "-p", base,
                    "-m", original_message, env=env).stdout.strip()
    return base, head


@pytest.mark.parametrize("cycle", ["initiative"], indirect=True)
@pytest.mark.parametrize("pre_adopt_rebase", [False, True])
def test_completed_source_uses_actual_recorded_final_head_without_rewriting_record(
        ready: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], pre_adopt_rebase: bool) -> None:
    core, root = ready.core, ready.root
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.base)
    monkeypatch.setattr(core, "push_github_branch", lambda *_args: None)
    monkeypatch.setattr(core, "github_remote_head", lambda *_args: (ready.head, "unused"))
    monkeypatch.setattr(core, "deliver_draft_pr", lambda *_args: {
        "number": NUMBER, "url": f"https://github.com/{REPOSITORY}/pull/{NUMBER}", "draft": True})
    core.command_final_push(core.parser().parse_args(["final-push"]))
    capsys.readouterr()
    record = core.read_cycle_record(root, ready.path, historical=True)
    assert record["state"] == "completed"
    assert record["commits"][-1]["id"] == ready.head
    assert "published_feature_head" not in record["delivery"]
    original = ready.path.read_bytes()
    ready.native.pull.update(state="open", merged=False, draft=True)
    original_native = ready.native.json
    def native_actor(*args: object) -> object:
        arguments = list(args)
        if isinstance(arguments[0], Path) and arguments[0].resolve() == ready.native.root.resolve():
            arguments[0] = ready.native.root
        result = original_native(*arguments)
        return {**result, "id": 123} if isinstance(result, dict) and result.get("login") else result
    monkeypatch.setattr(core, "github_json", native_actor)
    monkeypatch.setattr(core, "integration_policy_snapshot", lambda _root: {
        "policy_digest": "b" * 64, "enrollment_digest": "c" * 64,
        "delivery": {"mode": "ordinary", "role": "operator"},
        "coordinator": {"remote_repository": REPOSITORY, "target_ref": "refs/heads/main",
                        "control_ref": "refs/heads/control", "guarded_refresh": False, "policy_digest": "f" * 64}})
    native_published = ready.head
    if pre_adopt_rebase:
        adoption_base, native_published = replayed_fixture(ready, ready.head, ready.base, "Before adoption\n", "Pre-adoption base")
        core.git(root, "update-ref", "refs/remotes/origin/main", adoption_base)
        ready.native.pull["head"]["sha"] = native_published
        ready.native.pull["base"]["sha"] = adoption_base
    produced = core.integration_source_snapshot(root, "cycle-1", NUMBER, ready.head, adopt=True, mode="admin")
    assert produced["status"] == "unadmitted"
    assert produced["source"]["head"] == native_published
    assert produced["request"]["ticket"]["projection"] is None
    assert set(produced["request"]) == {"schema_version", "policy_digest", "ticket", "obligation"}
    assert produced["request"]["policy_digest"] == "f" * 64
    assert produced["request"]["ticket"]["requester_digest"] == produced["requester_digest"]
    assert ready.path.read_bytes() == original
    assert core.integration_source_snapshot(root, "cycle-1", NUMBER, ready.head, adopt=True, mode="admin") == produced
    with pytest.raises(RuntimeError):
        core.integration_source_snapshot(root, "cycle-1", NUMBER, ready.base, adopt=True)
    assert ready.path.read_bytes() == original

    # Real follow-up preflight and begin, with synthetic read-only native transport.
    feature = core.branch(root)
    source = r.decode("source", l.canonical(produced["source"]))
    ticket = r.decode("ticket", l.canonical(produced["request"]["ticket"]))
    remote_obligation = r.decode("obligation", l.canonical(produced["request"]["obligation"]))
    assert isinstance(source, r.SourceSeries) and isinstance(ticket, r.Ticket)
    assert isinstance(remote_obligation, r.Obligation) and ticket.delivery_mode == "admin"
    new_base, refreshed = replayed_fixture(ready, source.head, source.base, "After admission\n", "Unrelated base change")
    assert refreshed != ready.head
    core.git(root, "update-ref", "refs/remotes/origin/main", new_base)
    core.git(root, "update-ref", "refs/remotes/origin/" + feature, refreshed)
    ready.native.pull.update(state="open", merged=False, draft=True)
    ready.native.pull["head"]["sha"] = refreshed
    ready.native.pull["base"]["sha"] = new_base
    projection = ProofPort(lambda _ids: GitObjects(root)).prove_refresh(source, refreshed, new_base)
    failed = replace(ticket, state=r.State.REPAIR_PENDING, sequence=1, generation=1, base=new_base,
                     plan_digest="b" * 64, projection=projection, failure_digest="d" * 64, admission_digest="e" * 64)
    qualified = core.integration_capture_projection(root, produced["grant_digest"], Status(new_base, failed, remote_obligation))
    core.git(root, "branch", "--set-upstream-to", "origin/" + feature)
    aligned = core.integration_align_repair_checkout(root, produced["grant_digest"], qualified)
    assert aligned["head"] == refreshed
    manifest = root / "docs/initiatives/test/MANIFEST.json"
    receipt = core.initiative_receipt(manifest, "slice-a", root)
    plan = ready.fixture.plan_path("draft_pr")
    argv = ["begin", "--cycle-id", "child-1", "--context", "test", "--risk", "routine",
        "--delivery-intent", "draft_pr", "--base-branch", "main", "--plan", str(plan),
        "--github-account", ACCOUNT, "--github-repository", REPOSITORY, "--follow-up-pr", str(NUMBER),
        "--initiative-manifest", "docs/initiatives/test/MANIFEST.json", "--initiative-slice", "slice-a",
        "--initiative-digest", receipt["manifest_digest"], "--expected-repository", REPOSITORY,
        "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest()]
    preflight = core.parser().parse_args([*argv, "--preflight"])
    statement = "Trusted agent scope assessment: routine correction within the original approved behavior, risk and authority."
    inherited = core.integration_prepare_child(preflight, produced["grant_digest"], statement,
        predecessor_ticket=failed.handle, qualified_projection_digest=qualified)
    assert inherited["fresh_human_confirmation"] is False
    core.command_integration_prepare_child(core.parser().parse_args(["integration-prepare-child",
        "--grant-digest", produced["grant_digest"], "--predecessor-ticket", failed.handle,
        "--qualified-projection-digest", qualified, "--assessment", statement, "--", *argv[1:], "--preflight"]))
    assert json.loads(capsys.readouterr().out) == inherited
    assert core.integration_prepare_child(preflight, produced["grant_digest"], statement,
        predecessor_ticket=failed.handle, qualified_projection_digest=qualified) == inherited
    live = [*argv, "--expected-launch-digest", inherited["launch_digest"],
            "--integration-authorization", inherited["authorization_digest"]]
    class NoInput(io.StringIO):
        def readline(self, size: int = -1) -> str:
            raise AssertionError("inherited authority must not synthesize human confirmation")
    monkeypatch.setattr(core.sys, "stdin", NoInput())
    monkeypatch.setattr(core, "github_remote_head", lambda *_args: (ready.native.pull["head"]["sha"], "unused"))
    core.command_begin(core.parser().parse_args(live))
    child_path = core.cycle_dir(root) / "cycles/child-1.json"
    child = core.read_cycle_record(root, child_path)
    assert child["schema_version"] == 5
    assert child["initiative_approval"]["method"] == "integration_grant"
    assert child["initiative_approval"]["schema_version"] == 2
    assert "confirmed_at" not in child["initiative_approval"]
    assert all(g["result"] == "pending" for g in child["gates"].values() if g["applicability"] == "required")
    assert child["execution"]["attribution"]["status"] == "unavailable"
    assert ready.path.read_bytes() == original
    assert l.Custody(core.common_git_dir(root).resolve()).linked("birth", "child-1")["delivery_mode"] == "admin"
    (root / "tracked.txt").write_text("Routine repair\n")
    (root / "docs/specs/test/CHANGELOG.md").write_text("Routine repair completed.\n")
    changed = ["tracked.txt", "docs/specs/test/CHANGELOG.md"]
    record_evidence(ready, "domain", paths=changed)
    core.command_gate_commit(core.parser().parse_args(["gate-commit", "--message", "Repair phase", "--gates", "domain", "--paths", *changed]))
    for artifact, result in (("README", "unchanged"), ("BACKLOG", "unchanged"), ("CHANGELOG", "changed")):
        review = ["review-artifact", artifact, "--result", result, "--reason", "repair fixture"]
        if result == "changed": review += ["--path", "docs/specs/test/CHANGELOG.md"]
        core.command_review(core.parser().parse_args(review))
    for gate in core.GATES:
        if gate not in {"domain", "release"}: record_evidence(ready, gate)
    child_head = core.git(root, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setattr(core, "github_remote_head", lambda *_args: (ready.native.pull["head"]["sha"], "unused"))
    def push_child(*_args: object) -> None:
        ready.native.pull["head"]["sha"] = child_head
    monkeypatch.setattr(core, "push_github_branch", push_child)
    core.command_final_push(core.parser().parse_args(["final-push"]))
    capsys.readouterr()
    core.git(root, "update-ref", "refs/remotes/origin/" + feature, child_head)
    completed_child = child_path.read_bytes()
    replacement = core.integration_source_snapshot(root, "child-1", NUMBER, child_head)
    assert replacement["grant_digest"] == produced["grant_digest"]
    assert replacement["obligation_handle"] == produced["obligation_handle"]
    assert replacement["ticket_handle"] != produced["ticket_handle"]
    assert replacement["request"]["ticket"]["predecessor"] == produced["ticket_handle"]
    assert replacement["request"]["obligation"] == produced["request"]["obligation"]
    assert [entry["oid"] for entry in replacement["source"]["entries"]] == [refreshed, child_head]
    chain = l.revision_chain(l.Custody(core.common_git_dir(root).resolve()), replacement["ticket_handle"], GitObjects(root),
        lambda cycle_id, record_digest: core.integration_record_entries(root, cycle_id, record_digest))
    assert c.CommitPair(ready.head, refreshed) in chain.aliases
    assert c.CommitPair(native_published, refreshed) in chain.aliases
    assert c.CommitPair(child_head, child_head) in chain.aliases
    assert ready.path.read_bytes() == original and child_path.read_bytes() == completed_child
    next_ticket = r.decode("ticket", l.canonical(replacement["request"]["ticket"]))
    assert isinstance(next_ticket, r.Ticket)
    identity_projection = ProofPort(lambda _ids: GitObjects(root)).prove_refresh(next_ticket.source, child_head, new_base)
    failed_again = replace(next_ticket, state=r.State.REPAIR_PENDING, sequence=2, generation=2,
        base=new_base, plan_digest="b" * 64, projection=identity_projection, failure_digest="d" * 64, admission_digest="e" * 64)
    next_obligation = replace(remote_obligation, current_ticket=failed_again.handle, repair_count=1, revision_count=2)
    next_projection = core.integration_capture_projection(root, produced["grant_digest"], Status(new_base, failed_again, next_obligation))
    next_argv = list(argv); next_argv[next_argv.index("--cycle-id") + 1] = "child-2"
    next_authorization = core.integration_prepare_child(core.parser().parse_args([*next_argv, "--preflight"]),
        produced["grant_digest"], statement, predecessor_ticket=failed_again.handle, qualified_projection_digest=next_projection)
    assert next_authorization["authorization_digest"] != inherited["authorization_digest"]
    store = l.Custody(core.common_git_dir(root).resolve())
    # The gateway reuses the exact immutable outbox, rather than regenerating
    # the original producer against the now-aligned checkout.
    submitted: list[dict[str, object]] = []
    class ObservedClient:
        def submit(self, request: dict[str, object]) -> dict[str, object]:
            submitted.append(request)
            return {"status": "unadmitted", "dispatch": "accepted"}
        def status(self, ticket_handle: str, obligation_handle: str) -> Status:
            assert ticket_handle == produced["ticket_handle"] and obligation_handle == remote_obligation.handle
            return Status(new_base, failed_again, next_obligation)
    @contextmanager
    def selected_client(*args: object):
        yield ObservedClient()
    monkeypatch.setattr(core, "root_dir", lambda: root)
    monkeypatch.setattr(core, "integration_native_client", selected_client)
    core.command_integration_gateway(core.parser().parse_args(["integration-submit", "--cycle-id", "cycle-1"]))
    assert submitted == []
    assert json.loads(capsys.readouterr().out)["status"] == "repair_pending"
    core.command_integration_gateway(core.parser().parse_args(["integration-status", "--cycle-id", "cycle-1"]))
    assert json.loads(capsys.readouterr().out)["ticket_handle"] == failed_again.handle
    selected = core.integration_policy_snapshot(root)
    root_record = core.read_cycle_record(root, ready.path, historical=True)
    root_packet = store.linked("outbox", "cycle-1")
    binding = core.integration_operator_binding(root, selected, root_record, original, store, root_packet)
    assert binding.obligation_handle == produced["obligation_handle"]
    assert binding.original_task_digest == store.read("obligation", produced["obligation_digest"])["original_task_digest"]
    with pytest.raises(RuntimeError, match="operator_role"):
        core.integration_operator_binding(root, {**selected, "delivery": {"role": "integrator"}},
            root_record, original, store, root_packet)
    store.revoke(produced["grant_digest"], "e" * 64, "2026-11-13T00:00:00Z")
    assert core.read_cycle_record(root, child_path)["initiative_approval"]["method"] == "integration_grant"
    with pytest.raises(RuntimeError, match="revoked|changed"):
        core.command_begin(core.parser().parse_args([*next_argv, "--expected-launch-digest", next_authorization["launch_digest"],
            "--integration-authorization", next_authorization["authorization_digest"]]))
    assert not (core.cycle_dir(root) / "cycles/child-2.json").exists()
    assert child_path.read_bytes() == completed_child and ready.path.read_bytes() == original

    # A native verified delivery is re-proved against every immutable root and
    # child record. It is valid to finish an already dispatched grant after its
    # local future-repair authorization is revoked.
    projection = identity_projection
    candidate = r.Candidate(2, c.identity(next_ticket.source), c.identity(projection), child_head, new_base,
        child_head, (new_base, child_head), GitObjects(root).tree(child_head), "b" * 64, "f" * 64)
    qualification = c.Qualification(c.identity(candidate), "b" * 64, "f" * 64, "a" * 64,
        (c.Evidence("check", 1, 1, 1, child_head, "a" * 64),))
    delivery = r.Delivery("9" * 32, r.Invocation(1, 1, "8" * 32, "a" * 64), c.identity(candidate),
        c.identity(projection), NUMBER, child_head, tuple(c.CommitPair(p.landed, p.landed) for p in projection.mapping), "d" * 64)
    delivered = replace(failed_again, state=r.State.DELIVERED, candidate=candidate, qualification=qualification,
        delivery=delivery, failure_digest=None)
    verified = VerifiedOutcome(new_base, delivered, next_obligation, r.original_to_landed(delivered), child_head,
        new_base, child_head, "2026-11-13T00:00:00Z", "b" * 64)
    read_entries = lambda cycle_id, record_digest: core.integration_record_entries(root, cycle_id, record_digest)
    outcome_id = l.accept_verified_outcome(store, verified, GitObjects(root), read_entries, "2026-11-13T01:00:00Z")
    outcome = store.read("outcome", outcome_id)
    assert store.linked("outcome", "cycle-1") == store.linked("outcome", "child-1") == outcome
    mapping = outcome["mapping"]
    assert isinstance(mapping, list)
    assert {"original": ready.head, "landed": refreshed} in mapping
    assert {"original": child_head, "landed": child_head} in mapping
    retained, pairs = l.verify_outcome(store, outcome_id, GitObjects(root), read_entries)
    assert retained == outcome and c.CommitPair(ready.head, refreshed) in pairs
    accepted = core.integration_retirement_outcome(root, core.read_cycle_record(root, ready.path, historical=True))
    assert accepted is not None and accepted[1][ready.head] == refreshed
    primary = core.primary_worktree(root)
    core.git(primary, "branch", "--set-upstream-to", "origin/main", "main")
    core.git(primary, "merge", "--ff-only", child_head)
    pull = {"number": NUMBER, "url": f"https://github.com/{REPOSITORY}/pull/{NUMBER}", "repository": REPOSITORY,
        "state": "MERGED", "baseRefName": "main", "headRefName": feature, "headRefOid": child_head,
        "mergeCommit": {"oid": child_head}, "mergedAt": verified.merged_at}
    native_merged = {**ready.native.pull, "state": "closed", "merged": True, "merged_at": verified.merged_at}
    observation = {"repository": REPOSITORY, "repository_after": REPOSITORY, "remote": "origin", "default": "main",
        "default_after": "main", "head": child_head, "head_after": child_head, "fetched_head": child_head,
        "pull_requests": {str(NUMBER): pull},
        "commit_pull_requests": {p.landed: [native_merged] for p in pairs}}
    originals = [core.read_cycle_record(root, ready.path, historical=True), core.read_cycle_record(root, child_path, historical=True)]
    assert core.removal_default_predicates(root, originals, observation) == []
    pull["headRefOid"] = ready.head
    assert "pr_delivery_unverified" in core.removal_default_predicates(root, originals, observation)
    assert root.is_dir() and ready.path.read_bytes() == original and child_path.read_bytes() == completed_child
    assert l.accept_verified_outcome(store, verified, GitObjects(root), read_entries, "2026-11-13T02:00:00Z") == outcome_id
    with pytest.raises(ValueError):
        l.accept_verified_outcome(store, replace(verified, mapping=verified.mapping[1:]), GitObjects(root), read_entries,
            "2026-11-13T02:00:00Z")
    assert ready.path.read_bytes() == original and child_path.read_bytes() == completed_child


def helper() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader("integration_lifecycle_helper", str(ROOT / "dot_local/bin/executable_dbsctrctl"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    result = importlib.util.module_from_spec(spec)
    loader.exec_module(result)
    return result


def test_inherited_begin_flag_cannot_also_claim_fresh_confirmation() -> None:
    core = helper()
    argv = ["begin", "--cycle-id", "child", "--context", "test", "--risk", "routine",
            "--delivery-intent", "draft_pr", "--plan", "/not-opened.json",
            "--integration-authorization", "a" * 64]
    assert core.parser().parse_args(argv).integration_authorization == "a" * 64
    for mode in ("interactive", "agent-confirmed"):
        with pytest.raises(SystemExit):
            core.parser().parse_args([*argv, "--approval", mode])


@pytest.mark.parametrize("outer,nested", [(False, True), (True, False), (False, False)])
def test_disabled_policy_never_starts_validator_owner_or_credentials(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outer: bool, nested: bool) -> None:
    core = helper()
    common = tmp_path / ".git"; common.mkdir()
    config = tmp_path / "config"; policy = config / "dotfiles-ai/workflow-policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"repositories": [{"repository": str(tmp_path),
        "delivery": {"schema_version": 2, "enabled": outer, "coordinator": {"enabled": nested}}}]}))
    policy.chmod(0o600)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    monkeypatch.setattr(core, "common_git_dir", lambda _root: common)
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("disabled policy started an authority adapter")
    for name in ("_preservation_policy_snapshot", "integration_lifecycle_owner", "github_environment"):
        monkeypatch.setattr(core, name, forbidden)
    assert core.integration_policy_snapshot(tmp_path) is None
    assert not (common / "dbsctr/integration").exists()


def test_revision_composer_preserves_all_prior_kinds_gates_and_appends_child(objects: Path) -> None:
    base, first, second, refreshed_base, one, two = git_series(objects)
    prior = r.SourceSeries("fixture/project", 1, base, second,
        (r.SourceEntry(first, "phase", ("domain", "behavior")), r.SourceEntry(second, "discovery_import")), "a" * 64)
    projection = ProofPort(lambda _ids: GitObjects(objects)).prove_refresh(prior, two, refreshed_base)
    child = git_commit(objects, {"a": "one\n", "b": "two\n", "c": "other\n", "d": "repair\n"}, two, "repair phase")
    composed = l.compose_source(GitObjects(objects), prior, projection,
        (r.SourceEntry(child, "phase", ("test_driven_implementation",)),), "c" * 64)
    assert composed.base == refreshed_base and composed.head == child
    assert composed.entries == (r.SourceEntry(one, "phase", ("domain", "behavior")),
        r.SourceEntry(two, "discovery_import"), r.SourceEntry(child, "phase", ("test_driven_implementation",)))
    with pytest.raises(ValueError):
        l.compose_source(GitObjects(objects), prior, projection,
            (r.SourceEntry(one, "phase", ("domain",)),), "c" * 64)


def test_projection_cannot_relabel_drop_or_reorder_original_phases(objects: Path) -> None:
    base, first, second, refreshed_base, one, two = git_series(objects)
    prior = r.SourceSeries("fixture/project", 1, base, second,
        (r.SourceEntry(first, "phase", ("domain",)), r.SourceEntry(second, "phase", ("behavior",))), "a" * 64)
    malformed = r.Projection(c.identity(prior), refreshed_base, two,
        (c.CommitPair(second, one), c.CommitPair(first, two)), "b" * 64)
    with pytest.raises(ValueError):
        l.qualify_projection(GitObjects(objects), prior, malformed)


@pytest.mark.parametrize("action,extra", [("submit", []), ("adopt", ["--pr", "3"]), ("status", []),
    ("reconcile", []), ("operator-resume", ["--handle", "a" * 32, "--expected-generation", "1"]),
    ("prepare-child", ["--grant-digest", "a" * 64, "--predecessor-ticket", "b" * 32,
        "--qualified-projection-digest", "c" * 64, "--assessment", "Mechanical scope unchanged"])])
def test_gateway_disabled_never_starts_client_or_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str], action: str, extra: list[str]) -> None:
    core = helper()
    monkeypatch.setattr(core, "root_dir", lambda: tmp_path)
    monkeypatch.setattr(core, "integration_policy_snapshot", lambda _root: None)
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("disabled gateway started authority")
    monkeypatch.setattr(core, "integration_lifecycle_owner", forbidden)
    monkeypatch.setattr(core, "github_environment", forbidden)
    cycle_args = [] if action == "prepare-child" else ["--cycle-id", "cycle-1"]
    args = core.parser().parse_args(["integration-" + action, *cycle_args, *extra])
    args.func(args)
    assert json.loads(capsys.readouterr().out)["status"] == "disabled_local"

@pytest.mark.parametrize("mode,expected", [("ordinary", False), ("admin", False), ("pr", False), ("draft_pr", True), ("off", True)])
def test_enrolled_publication_mode_selects_ready_without_affecting_legacy(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, expected: bool) -> None:
    core = helper()
    record = {"cycle_id": "cycle-1", "delivery": {"github": {"account": "human", "repository": "owner/repo"},
        "branch": "feature", "base_branch": "main"}}
    monkeypatch.setattr(core, "integration_publication_mode", lambda *_args: mode)
    monkeypatch.setattr(core, "validate_follow_up", lambda *_args: None)
    pull = {"number": 3, "url": "https://github.com/owner/repo/pull/3", "isDraft": expected,
        "state": "OPEN", "baseRefName": "main", "headRefName": "feature", "headRepositoryOwner": {"login": "owner"}}
    monkeypatch.setattr(core, "github_json", lambda *_args: [pull])
    assert core.deliver_draft_pr(tmp_path, record, {"GH_TOKEN": "fixture"})["draft"] is expected


def test_ready_transition_rejects_changed_native_head(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    core = helper()
    record = {"delivery": {"github": {"account": "human", "repository": "owner/repo"},
        "branch": "feature", "base_branch": "main"}}
    calls: list[tuple[object, ...]] = []
    observations = iter([({"observed_base": "a" * 40}, {"draft": True, "node_id": "PR_fixture"}),
                         ({"observed_base": "a" * 40}, {"draft": False, "node_id": "PR_fixture"})])
    def observe(*args: object):
        before, pull = next(observations)
        if calls:
            raise RuntimeError("follow-up published head changed")
        return before, pull
    monkeypatch.setattr(core, "observe_follow_up", observe)
    monkeypatch.setattr(core, "github_json", lambda *args: calls.append(args) or {})
    with pytest.raises(RuntimeError, match="head changed"):
        core.integration_ready_pull(tmp_path, record, {}, 3, "b" * 40)
    assert len(calls) == 1

@pytest.mark.parametrize("cycle", ["initiative"], indirect=True)
@pytest.mark.parametrize("mode", ["admin", "pr", "draft_pr"])
def test_birth_enrolled_final_publish_is_linear_ready_and_dispatches_only_merge_modes(
        ready: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], mode: str) -> None:
    core, root = ready.core, ready.root
    policy = {"policy_digest": "b" * 64, "enrollment_digest": "c" * 64,
        "delivery": {"mode": "ordinary", "role": "operator"},
        "coordinator": {"remote_repository": REPOSITORY, "target_ref": "refs/heads/main",
            "control_ref": "refs/heads/control", "guarded_refresh": True, "policy_digest": "f" * 64}}
    monkeypatch.setattr(core, "integration_policy_snapshot", lambda _root: policy)
    record = core.read_cycle_record(root, ready.path)
    core.integration_birth_enrollment(root, record, mode)
    target = ready.base
    if mode == "admin":
        # The current default advances without changing the owned phase IDs.
        target = core.git(root, "commit-tree", rebased_tree(ready, ready.base), "-p", ready.base,
                          "-m", "Unrelated default advance").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", target)
    ready.native.pull.update(state="open", merged=False, draft=True, node_id="PR_fixture")
    ready.native.pull["base"]["sha"] = target
    mutations: list[str] = []
    original_native = ready.native.json
    def native(*args: object) -> object:
        arguments = list(args)
        if isinstance(arguments[0], Path): arguments[0] = ready.native.root
        if "graphql" in arguments:
            assert "markPullRequestReadyForReview" in " ".join(str(a) for a in arguments)
            mutations.append("ready")
            ready.native.pull["draft"] = False
            return {"data": {}}
        if arguments[2:4] == ["pr", "list"]:
            return [{"number": NUMBER, "url": ready.native.pull["html_url"], "isDraft": ready.native.pull["draft"],
                "state": "OPEN", "baseRefName": "main", "headRefName": core.branch(root),
                "headRepositoryOwner": {"login": REPOSITORY.split("/")[0]}}]
        value = original_native(*arguments)
        return {**value, "id": 123} if isinstance(value, dict) and value.get("login") else value
    monkeypatch.setattr(core, "github_json", native)
    # The external-completion fixture intentionally forbids this operation.
    # Restore the actual paired source function against this fixture's native
    # boundary, rather than replacing the behavior under test.
    paired = helper()
    monkeypatch.setattr(core, "deliver_draft_pr", FunctionType(paired.deliver_draft_pr.__code__, core.__dict__,
        name="deliver_draft_pr", argdefs=(None,)))
    monkeypatch.setattr(core, "push_github_branch", lambda *_args: None)
    monkeypatch.setattr(core, "github_remote_head", lambda *_args: (ready.head, "unused"))
    core.command_final_push(core.parser().parse_args(["final-push"]))
    capsys.readouterr()
    completed = ready.path.read_bytes()
    assert core.git(root, "rev-parse", "HEAD").stdout.strip() == ready.head
    final = core.read_cycle_record(root, ready.path, historical=True)
    assert final["state"] == "completed" and final["delivery"]["pull_request"]["draft"] is (mode == "draft_pr")
    assert mutations == ([] if mode == "draft_pr" else ["ready"])
    dispatched: list[dict[str, object]] = []
    class NativeClient:
        def status(self, *_args: object) -> None:
            return None
        def submit(self, request: dict[str, object]) -> dict[str, object]:
            dispatched.append(request)
            assert ready.native.pull["draft"] is False
            return {"status": "unadmitted", "dispatch": "accepted"}
    @contextmanager
    def selected_client(*_args: object):
        yield NativeClient()
    monkeypatch.setattr(core, "integration_native_client", selected_client)
    core.command_integration_gateway(core.parser().parse_args(["integration-submit", "--cycle-id", "cycle-1"]))
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == ("unadmitted" if mode == "admin" else "source_only")
    assert len(dispatched) == (1 if mode == "admin" else 0)
    if dispatched:
        requested = r.decode("ticket", l.canonical(dispatched[0]["ticket"]))
        assert isinstance(requested, r.Ticket)
        assert requested.source.entries == (r.SourceEntry(ready.head, "phase", ("domain",)),)
    assert ready.path.read_bytes() == completed

@pytest.mark.parametrize("mode,ready", [("pr", True), ("draft_pr", False), ("off", False), (None, False)])
def test_selected_pr_followup_readies_exact_head_and_legacy_preserves_draft(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str | None, ready: bool) -> None:
    core = helper()
    record = {"delivery": {"github": {"account": "human", "repository": "owner/repo"},
        "branch": "feature", "base_branch": "main"}}
    monkeypatch.setattr(core, "integration_publication_mode", lambda *_args: mode)
    monkeypatch.setattr(core, "validate_follow_up", lambda *_args: {"number": 3})
    monkeypatch.setattr(core, "git", lambda *_args: SimpleNamespace(stdout="b" * 40))
    pull = {"number": 3, "html_url": "https://github.com/owner/repo/pull/3", "draft": True, "node_id": "PR_fixture"}
    calls: list[object] = []
    def observe(*args: object):
        assert args[-1] == "b" * 40
        return {"observed_base": "a" * 40}, dict(pull)
    def mutation(*args: object) -> dict[str, object]:
        calls.append(args)
        pull["draft"] = False
        return {}
    monkeypatch.setattr(core, "observe_follow_up", observe)
    monkeypatch.setattr(core, "github_json", mutation)
    result = core.deliver_draft_pr(tmp_path, record, {"GH_TOKEN": "fixture"})
    assert result["draft"] is (not ready)
    assert len(calls) == int(ready)

@pytest.mark.parametrize("problem", ["missing", "broken_link"])
def test_source_generation_never_falls_back_to_installed_decoy(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str) -> None:
    core = helper()
    source = tmp_path / "source/dot_local/bin/executable_dbsctrctl"
    source.parent.mkdir(parents=True); source.write_text("")
    package = tmp_path / "source/private_dot_config/dotfiles-ai/integration_coordinator"
    if problem == "broken_link":
        package.mkdir(parents=True)
        (package / "lifecycle.py").symlink_to(package / "missing.py")
    home = tmp_path / "home"
    decoy = home / ".config/dotfiles-ai/integration_coordinator"
    decoy.mkdir(parents=True)
    marker = tmp_path / "decoy-loaded"
    for name in ("__init__.py", "core.py"):
        (decoy / name).write_text("")
    (decoy / "lifecycle.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('loaded')\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(core, "__file__", str(source))
    for name in tuple(sys.modules):
        if name == "integration_coordinator" or name.startswith("integration_coordinator."):
            monkeypatch.delitem(sys.modules, name)
    with pytest.raises(RuntimeError, match="integration_owner_unavailable"):
        core.integration_lifecycle_owner()
    assert not marker.exists()
