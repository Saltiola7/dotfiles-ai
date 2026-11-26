"""Completion at verified merge for cycles whose approved plan binds that contract.

Real Git and the real helper; only the GitHub transport is synthetic, as in the
external completion tests. Identities are public examples. Nothing here
establishes production authentication, consent, CI or deployment acceptance.
"""

import contextlib
import dataclasses
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core as coordinator  # noqa: E402
from integration_coordinator import lifecycle, runtime  # noqa: E402
from integration_coordinator.client import Status, VerifiedOutcome  # noqa: E402
from integration_coordinator.gitproof import GitObjects, ProofPort  # noqa: E402

import test_dbsctrctl as harness
import test_dbsctr_external_completion as external
import test_post_delivery_receipts as post
from test_dbsctr_external_completion import NUMBER, cycle, ready, snapshot  # noqa: F401 - shared fixtures
from test_post_delivery_receipts import URL, delivered, real  # noqa: F401 - shared legacy fixture


CONTRACT = {"schema_version": 1, "contract": "verified_merge"}
MANIFEST = "docs/initiatives/test/MANIFEST.json"
FROZEN = ("commits", "gates", "evidence", "artifact_reviews", "git", "worktree", "initiative",
          "initiative_approval", "initiative_amendments", "initiative_authority_checkpoints",
          "engineering_profile", "applicability_plan", "completion_contract", "publication")


def amend(ws, capsys):
    """Amend the approved Initiative authority; Build imports its closure in the Gate Commit."""
    core, source = ws.core, ws.primary
    manifest = source / MANIFEST
    value = json.loads(manifest.read_text())
    value["title"] += " amended authority"
    # A same-repository amendment freezes every slice artifact at its authority blob.
    value["slices"][0]["artifacts"] = ["docs/specs/test/BACKLOG.md"]
    manifest.write_text(json.dumps(value))
    real("add", MANIFEST, cwd=source)
    real("commit", "-m", "Amended Discovery authority", cwd=source)
    receipt = core.initiative_receipt(manifest, "slice-a", source)
    argv = ["initiative-amend", "--cycle-id", "cycle-1", "--initiative-manifest", MANIFEST,
            "--initiative-slice", "slice-a", "--initiative-source", str(source),
            "--initiative-digest", receipt["manifest_digest"], "--plan", str(ws.plan),
            "--expected-plan-digest", hashlib.sha256(ws.plan.read_bytes()).hexdigest(),
            "--reason", "fixture amendment", "--json"]
    core.command_initiative_amend(core.parser().parse_args([*argv, "--preflight"]))
    digest = json.loads(capsys.readouterr().out)["state_digest"]
    core.command_initiative_amend(core.parser().parse_args(
        [*argv, "--expected-launch-digest", digest, "--approval", "agent-confirmed"]))
    assert json.loads(capsys.readouterr().out)["status"] == "applied"
    (ws.root / MANIFEST).write_bytes(manifest.read_bytes())


bound = pytest.mark.parametrize("cycle", ["merge"], indirect=True)


@pytest.fixture
def published(cycle, monkeypatch, capsys):
    """An amended Initiative cycle published under the contract; its checkout slot is free."""
    ws = post.transport(cycle, monkeypatch, capsys)
    ws.plan = Path(ws.fixture.temp.name) / "plan.json"
    amend(ws, capsys)
    post.prepare(ws, deferred=(), extra=(MANIFEST,))
    assert ws.invoke("final-push") == 0
    ws.report = ws.capsys.readouterr().out
    record = json.loads(ws.path.read_text())
    assert record["state"] == "awaiting_merge" and "completed_at" not in record
    assert record["completion_contract"] == CONTRACT
    assert not ws.core.resolved_active_path(ws.root, bindings=False).exists()
    ws.publication = record["publication"]
    return ws


@pytest.fixture
def waiting(published):
    """The published cycle waits while a second cycle owns its checkout."""
    ws = published
    real("switch", "-c", "cycle-2-branch", "refs/remotes/origin/main", cwd=ws.root)
    plan = ws.plan.with_name("plan-2.json")
    plan.write_text(json.dumps({key: value for key, value in json.loads(ws.plan.read_text()).items()
                                if key != "completion"}))
    ws.core.command_start(ws.core.parser().parse_args([
        "start", "--cycle-id", "cycle-2", "--context", "test", "--risk", "routine",
        "--delivery-intent", "draft_pr", "--plan", str(plan), "--base-branch", "main",
        "--github-account", external.ACCOUNT, "--github-repository", external.REPOSITORY]))
    ws.capsys.readouterr()
    ws.second = ws.core.cycle_dir(ws.root) / "cycles" / "cycle-2.json"
    ws.pointer = ws.core.resolved_active_path(ws.root, bindings=False)
    assert ws.pointer.read_bytes().strip() == b"cycle-2"
    return ws


def elsewhere(ws, monkeypatch, name="observer"):
    """Another checkout of the same repository, with no cycle of its own."""
    other = Path(ws.fixture.temp.name) / name
    real("worktree", "add", "-b", name, str(other), "refs/remotes/origin/main", cwd=ws.root)
    real("branch", "--set-upstream-to=origin/main", cwd=other)
    monkeypatch.chdir(other)
    monkeypatch.setattr(ws.core, "root_dir", lambda: other)
    # The synthetic provider reads the same shared refs and objects through this checkout.
    ws.native.root = other
    return other


def state(ws, other):
    """Bytes that no preview, observation or status read may change."""
    return {"original": snapshot(ws), "other": snapshot(
        type("View", (), {"core": ws.core, "root": other, "path": ws.path})())}


def observe(ws, *extra, cycle_id="cycle-1"):
    return ["complete-external", "--cycle-id", cycle_id, "--pr-number", str(NUMBER),
            "--expected-head", ws.pr_head, "--expected-merge", ws.merge, *extra]


def preview(ws, other, *extra, cycle_id="cycle-1"):
    before = state(ws, other)
    assert ws.invoke(*observe(ws, *extra, cycle_id=cycle_id), "--preview") == 0, ws.capsys.readouterr().err
    report = json.loads(ws.capsys.readouterr().out)
    assert state(ws, other) == before
    return report


def append(ws, other, digest, *extra, cycle_id="cycle-1"):
    argv = observe(ws, "--expected-receipt-digest", digest, "--approval", "agent-confirmed", *extra,
                   cycle_id=cycle_id)
    assert ws.invoke(*argv) == 0, ws.capsys.readouterr().err
    return json.loads(ws.capsys.readouterr().out)


def refused(ws, other, *extra):
    """A read-only preview that refuses: no record, receipt, ref, index or pointer changes."""
    before = state(ws, other)
    names = receipt_names(ws)
    assert ws.invoke(*observe(ws, *extra), "--preview") == 1
    output = ws.capsys.readouterr()
    assert "dbsctrctl:" in output.err and "Traceback" not in output.err
    assert "synthetic-token-never-print" not in output.out + output.err
    assert state(ws, other) == before and receipt_names(ws) == names
    return output.err


def receipt_names(ws):
    directory = ws.core.cycle_dir(ws.root) / "evidence" / "cycle-1" / "post-delivery"
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.iterdir() if not path.name.startswith("tmp"))


def status(ws):
    """An offline read: any provider call fails the test."""
    original = ws.core.github_environment
    ws.core.github_environment = lambda _account: pytest.fail("status reached a provider")
    try:
        argv = ["status", "--cycle-id", "cycle-1", "--json"]
        assert ws.invoke(*argv) == 0, ws.capsys.readouterr().err
        report = json.loads(ws.capsys.readouterr().out)
    finally:
        ws.core.github_environment = original
    assert receipt_names(ws) == [f"{item['sequence']:04d}-{item['digest']}.json"
                                 for item in report["observations"]]
    return report


@bound
def test_published_amended_cycle_frees_its_slot_and_completes_by_id_from_another_checkout(
        waiting, monkeypatch):
    ws = waiting
    frozen = json.loads(ws.path.read_text())
    second, pointer = ws.second.read_bytes(), ws.pointer.read_bytes()
    assert "awaiting_merge" in ws.report and ws.publication["head"] == frozen["commits"][-1]["id"]
    post.land(ws)
    other = elsewhere(ws, monkeypatch)

    report = preview(ws, other)
    assert report["schema_version"] == 2 and report["mode"] == "preview"
    assert report["binding"]["kind"] == "publication" and report["binding"]["digest"] == ws.publication["digest"]
    assert report["binding"]["recorded_commits"] == [entry["id"] for entry in frozen["commits"]]
    assert report["native"]["status"] == "merged" and report["native"]["merge"] == ws.merge
    assert report["delivery"]["status"] == "verified" and report["completion"] == {"status": "ready"}
    assert len(report["receipt_digest"]) == 64
    stored = status(ws)
    assert stored["state"] == "awaiting_merge" and stored["latest_observation"] is None
    assert stored["published_at"] == ws.publication["published_at"] and stored["completed_at"] is None

    receipt = append(ws, other, report["receipt_digest"])
    assert receipt["mode"] == "recorded" and receipt["cycle_state"] == "completed"
    record = json.loads(ws.path.read_text())
    for name in FROZEN:
        assert record[name] == frozen[name], name
    assert record["state"] == "completed" and record["completed_at"] == receipt["observed_at"]
    assert record["publication"]["published_at"] < record["completed_at"]
    assert record["merge_completion"]["publication_digest"] == ws.publication["digest"]
    assert record["merge_completion"]["observation_digest"] == receipt["digest"]
    assert "external_completion" not in record
    assert ws.second.read_bytes() == second and ws.pointer.read_bytes() == pointer

    again = append(ws, other, report["receipt_digest"])
    assert again["mode"] == "already_recorded" and again["cycle_state"] == "completed"
    assert {key: again[key] for key in receipt if key != "mode"} == {
        key: value for key, value in receipt.items() if key != "mode"}
    assert ws.path.read_bytes() == json.dumps(record).encode() or json.loads(ws.path.read_text()) == record
    stored = status(ws)
    assert stored["state"] == "completed" and stored["merged_at"] == external.MERGED_AT
    assert stored["latest_observation"]["digest"] == receipt["digest"]
    assert stored["completed_at"] == record["completed_at"] != stored["merged_at"]


@bound
def test_accepted_base_refresh_completes_and_an_absent_pointer_stays_absent(published, monkeypatch):
    ws = published
    other = elsewhere(ws, monkeypatch)
    post.advance_base(ws)
    post.refresh(ws)
    report = preview(ws, other)
    assert report["delivery"]["status"] == "verified" and report["delivery"]["proof"] == "base_refresh"
    assert report["delivery"]["recorded_commits"][-1] == ws.pr_head
    receipt = append(ws, other, report["receipt_digest"])
    assert receipt["cycle_state"] == "completed"
    record = json.loads(ws.path.read_text())
    assert record["merge_completion"]["proof"] == "base_refresh" and record["merge_completion"]["head"] == ws.pr_head
    assert not ws.core.resolved_active_path(ws.root, bindings=False).exists()
    assert not ws.core.resolved_active_path(other, bindings=False).exists()


@bound
def test_substantive_head_records_the_merge_without_completing(published, monkeypatch):
    ws = published
    other = elsewhere(ws, monkeypatch)
    post.land(ws, pr_head=post.edit(ws, "Later unqualified edit\n"))
    report = preview(ws, other)
    assert report["native"]["status"] == "merged" and report["native"]["merge"] == ws.merge
    assert report["delivery"] == {"status": "unverified", "proof": None, "reason": "head_changed_beyond_base_refresh",
                                  "head": None, "recorded_commits": None}
    assert report["completion"] == {"status": "pending", "reason": "head_changed_beyond_base_refresh"}
    receipt = append(ws, other, report["receipt_digest"])
    assert receipt["mode"] == "recorded" and receipt["cycle_state"] == "awaiting_merge"
    record = json.loads(ws.path.read_text())
    assert record["state"] == "awaiting_merge" and "completed_at" not in record and "merge_completion" not in record
    stored = status(ws)
    assert stored["state"] == "awaiting_merge" and stored["merged_at"] == external.MERGED_AT
    assert stored["latest_observation"]["delivery"]["status"] == "unverified" and stored["completed_at"] is None


@bound
def test_unmerged_mismatched_and_unavailable_observations_leave_no_record(published, monkeypatch):
    ws = published
    other = elsewhere(ws, monkeypatch)
    post.land(ws)
    native = ws.native
    native.pull["merged"] = False
    assert "closed without merging" in refused(ws, other)
    native.pull.update(merged=True, state="open")
    assert "pull request is not closed" in refused(ws, other)
    native.pull["state"] = "closed"
    for pin in ("--expected-merge", "--expected-head"):
        assert "pins are not the pull request head and merge" in refused(ws, other, pin, "0" * 40)
    native.pull["base"]["repo"]["full_name"] = "example-org/another"
    assert "pull request repository, branch or identity does not match" in refused(ws, other)
    native.pull["base"]["repo"]["full_name"] = external.REPOSITORY
    native.auth_error = True
    assert "not authenticated" in refused(ws, other)
    native.auth_error = False
    # The merge object must be in the independently fetched protected target, not merely retained.
    real("update-ref", "refs/remotes/origin/main", ws.base, cwd=ws.root)
    assert "not included in the independently fetched protected target" in refused(ws, other)


@bound
def test_frozen_publication_refuses_writers_and_an_interrupted_release_retries_exactly(published, monkeypatch):
    ws = published
    calls = []
    monkeypatch.setattr(ws.core, "deliver_draft_pr", lambda *a, **k: calls.append("deliver"))
    monkeypatch.setattr(ws.core, "push_github_branch", lambda *a, **k: calls.append("push"))
    pointer = ws.core.active_path(ws.root)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text("cycle-1\n")  # a publication interrupted before it released its own pointer
    frozen = ws.path.read_bytes()
    for command in (["record-evidence", "domain", "--authority", "fixture", "--", "true"],
                    ["gate-commit", "--message", "late", "--gates", "domain", "--paths", "tracked.txt"],
                    ["set-gate", "domain", "--result", "passed"], ["reconcile-target", "--mode", "preview", "--json"]):
        assert ws.invoke(*command) == 1
        assert "dbsctrctl:" in ws.capsys.readouterr().err, command
    assert pointer.read_bytes() == b"cycle-1\n" and ws.path.read_bytes() == frozen
    assert ws.invoke("final-push") == 0
    assert "awaiting_merge" in ws.capsys.readouterr().out and calls == []
    assert not pointer.exists() and ws.path.read_bytes() == frozen
    assert ws.invoke("status", "--json") == 0 and ws.capsys.readouterr().out == "null\n"


@bound
def test_changed_frozen_sections_are_refused_by_every_reader(published):
    ws = published
    frozen = ws.path.read_bytes()
    for name, change in (("gates", lambda record: record["gates"]["operate"].update(evidence=None)),
                         ("commits", lambda record: record["commits"].pop()),
                         ("evidence", lambda record: record["evidence"]["items"].clear()),
                         ("delivery", lambda record: record["delivery"].update(base_branch="release")),
                         ("initiative_amendments", lambda record: record["initiative_amendments"].clear()),
                         ("artifact_reviews", lambda record: record["artifact_reviews"]["README"].update(result="changed"))):
        tampered = json.loads(frozen)
        change(tampered)
        ws.path.write_text(json.dumps(tampered))
        assert ws.invoke("status", "--cycle-id", "cycle-1", "--json") == 1, name
        # A section validator may refuse first; either way the changed record never reads as current.
        assert "dbsctrctl:" in ws.capsys.readouterr().err, name
        ws.path.write_bytes(frozen)
    assert ws.invoke("status", "--cycle-id", "cycle-1", "--json") == 0


@bound
def test_interrupted_completion_is_finished_only_by_the_identical_retry(waiting, monkeypatch):
    ws = waiting
    post.land(ws)
    other = elsewhere(ws, monkeypatch)
    report = preview(ws, other)
    awaiting = ws.path.read_bytes()
    receipt = append(ws, other, report["receipt_digest"])
    completed = ws.path.read_bytes()
    ws.path.write_bytes(awaiting)  # the receipt was durable; the state save was interrupted
    again = append(ws, other, report["receipt_digest"])
    assert again["mode"] == "already_recorded" and again["cycle_state"] == "completed"
    assert {key: again[key] for key in receipt if key != "mode"} == {
        key: value for key, value in receipt.items() if key != "mode"}
    assert ws.path.read_bytes() == completed and len(receipt_names(ws)) == 1


legacy = pytest.mark.parametrize("cycle", [None], indirect=True)


@legacy
def test_historical_final_push_record_gains_an_observation_and_never_changes(delivered, monkeypatch):
    ws = delivered
    record = post.deliver(ws)
    historical = ws.path.read_bytes()
    post.land(ws)
    other = elsewhere(ws, monkeypatch)
    report = preview(ws, other)
    assert report["binding"]["kind"] == "historical_record"
    assert report["binding"]["record_sha256"] == hashlib.sha256(historical).hexdigest()
    assert report["completion"] == {"status": "already_completed", "route": "final_push"}
    assert [item["gate"] for item in report["conditions"]] == list(post.DEFERRED)
    receipt = append(ws, other, report["receipt_digest"])
    assert receipt["mode"] == "recorded" and receipt["cycle_state"] == "completed"
    assert ws.path.read_bytes() == historical
    stored = status(ws)
    assert stored["state"] == "completed" and stored["publication"] is None
    assert stored["completion_contract"] is None and stored["merge_completion"] is None
    assert stored["published_at"] == record["completed_at"] and stored["merged_at"] == external.MERGED_AT
    assert ws.invoke("status", "--post-delivery", "--cycle-id", "cycle-1", "--json") == 0
    version_one = json.loads(ws.capsys.readouterr().out)
    assert version_one["receipts"] == [] and version_one["latest"] is None
    assert [item["digest"] for item in version_one["observations"]] == [receipt["digest"]]


def test_plan_completion_is_refused_outside_github_draft_pr():
    fixture = harness.DbsctrctlTest()
    fixture.setUp()
    try:
        fixture.prepare_native_checkout()
        plan = fixture.plan_path("local")
        for completion, message in ((CONTRACT, "plan completion must be verified_merge on a GitHub draft_pr plan"),
                                    ({"schema_version": 1, "contract": "publication"}, "plan completion must be verified_merge on a GitHub draft_pr plan"),
                                    (True, "plan completion must be verified_merge on a GitHub draft_pr plan")):
            plan.write_text(json.dumps({**json.loads(plan.read_text()), "completion": completion}))
            result = harness.run(fixture.repo, "start", "--cycle-id", "cycle-1", "--context", "test", "--risk",
                                 "routine", "--delivery-intent", "local", "--plan", str(plan),
                                 "--base-branch", "main", ok=False)
            assert result.returncode == 1 and message in result.stderr, completion
        assert not (fixture.git_common / "dbsctr/cycles/cycle-1.json").exists()
    finally:
        fixture.tearDown()


@bound
@pytest.mark.usefixtures("cycle")
def test_coordinator_binds_the_frozen_publication_and_completes_once_on_its_verified_outcome(
        ready, monkeypatch, capsys):
    core, root, native = ready.core, ready.root, ready.native
    ready.capsys = capsys
    real_json = native.json

    def identified(*args):
        value = real_json(*args)
        return {**value, "id": 123} if isinstance(value, dict) and value.get("login") else value

    monkeypatch.setattr(core, "github_json", identified)
    monkeypatch.setattr(core, "integration_policy_snapshot", lambda _root: {
        "policy_digest": "b" * 64, "enrollment_digest": "c" * 64, "delivery": {"mode": "ordinary", "role": "operator"},
        "coordinator": {"remote_repository": external.REPOSITORY, "target_ref": "refs/heads/main",
                        "control_ref": "refs/heads/control", "guarded_refresh": False, "policy_digest": "f" * 64}})
    monkeypatch.setattr(core, "push_github_branch", lambda *_args: None)
    monkeypatch.setattr(core, "github_remote_head", lambda *_args: (ready.head, "unused"))
    monkeypatch.setattr(core, "deliver_draft_pr", lambda *_args, **_kwargs: {
        "number": NUMBER, "url": URL, "draft": True, "state": "OPEN", "verified_at": core.now()})
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.base)  # the default has not advanced
    core.command_final_push(core.parser().parse_args(["final-push"]))
    capsys.readouterr()
    published = ready.path.read_bytes()
    publication = json.loads(published)["publication"]
    assert json.loads(published)["state"] == "awaiting_merge"

    # The coordinator accepts the frozen publication before any completion exists.
    native.pull.update(state="open", merged=False, merged_at=None, draft=True)
    native.pull["head"]["sha"] = ready.head
    produced = core.integration_source_snapshot(root, "cycle-1", NUMBER, ready.head, adopt=True, mode="admin")
    assert produced["status"] == "unadmitted" and ready.path.read_bytes() == published
    store = lifecycle.Custody(core.common_git_dir(root).resolve())
    assert store.linked("grant", "cycle-1")["record_digest"] == publication["digest"]
    packet = store.linked("outbox", "cycle-1")
    request = packet["request"]
    assert isinstance(request, dict)
    ticket = runtime.decode("ticket", lifecycle.canonical(request["ticket"]))
    obligation = runtime.decode("obligation", lifecycle.canonical(request["obligation"]))
    assert isinstance(ticket, runtime.Ticket) and isinstance(obligation, runtime.Obligation)

    # A ticket alone proves nothing; only the coordinator's verified native outcome completes.
    assert json.loads(ready.path.read_text())["state"] == "awaiting_merge"
    projection = ProofPort(lambda _ids: GitObjects(root)).prove_refresh(ticket.source, ready.head, ready.base)
    candidate = runtime.Candidate(1, coordinator.identity(ticket.source), coordinator.identity(projection),
        ready.head, ready.base, ready.head, (ready.base, ready.head), GitObjects(root).tree(ready.head),
        "b" * 64, "f" * 64)
    qualification = coordinator.Qualification(coordinator.identity(candidate), "b" * 64, "f" * 64, "a" * 64,
        (coordinator.Evidence("check", 1, 1, 1, ready.head, "a" * 64),))
    delivery = runtime.Delivery("9" * 32, runtime.Invocation(1, 1, "8" * 32, "a" * 64), coordinator.identity(candidate),
        coordinator.identity(projection), NUMBER, ready.head,
        tuple(coordinator.CommitPair(pair.landed, pair.landed) for pair in projection.mapping), "d" * 64)
    delivered = dataclasses.replace(ticket, state=runtime.State.DELIVERED, sequence=1, generation=1,
        base=ready.base, plan_digest="b" * 64, projection=projection, admission_digest="e" * 64,
        candidate=candidate, qualification=qualification, delivery=delivery, failure_digest=None)
    assert isinstance(delivered, runtime.Ticket)
    verified = VerifiedOutcome(ready.base, delivered, obligation, runtime.original_to_landed(delivered), ready.head,
                               ready.base, ready.head, "2026-11-13T00:00:00Z", "b" * 64)

    class Delivered:
        def status(self, ticket_handle, obligation_handle):
            assert (ticket_handle, obligation_handle) == (produced["ticket_handle"], produced["obligation_handle"])
            return Status(ready.base, delivered, obligation)

        def verify_delivered(self, ticket_handle, obligation_handle):
            return verified

    @contextlib.contextmanager
    def client(*_args, **_kwargs):
        yield Delivered()

    monkeypatch.setattr(core, "integration_native_client", client)
    reconcile = ["integration-reconcile", "--cycle-id", "cycle-1"]
    core.command_integration_gateway(core.parser().parse_args(reconcile))
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "delivered" and result["records_unchanged"] is False
    assert result["completed_cycles"] == ["cycle-1"]
    record = json.loads(ready.path.read_text())
    assert record["state"] == "completed" and record["merge_completion"]["route"] == "coordinator"
    assert record["merge_completion"]["outcome_digest"] == result["outcome_digest"]
    assert record["merge_completion"]["publication_digest"] == publication["digest"]
    for name in FROZEN:
        if name in json.loads(published):
            assert record[name] == json.loads(published)[name], name
    completed = ready.path.read_bytes()
    core.command_integration_gateway(core.parser().parse_args(reconcile))  # the duplicate callback
    again = json.loads(capsys.readouterr().out)
    assert again["outcome_digest"] == result["outcome_digest"] and again["records_unchanged"] is True
    assert again["completed_cycles"] == [] and ready.path.read_bytes() == completed
    core.integration_record_entries(root, "cycle-1", publication["digest"])  # the ticket still binds
    stored = status(ready)
    assert stored["state"] == "completed" and stored["observations"] == []
    assert stored["merged_at"] == "2026-11-13T00:00:00Z" and stored["published_at"] == publication["published_at"]


@bound
def test_linked_follow_up_publication_accounts_for_the_original_cycle(published, monkeypatch, capsys):
    ws = published
    core, root = ws.core, ws.root
    tip = ws.publication["head"]
    original = json.loads(ws.path.read_text())
    # A review correction is a separately admitted follow-up on the same open pull request.
    real("update-ref", "refs/remotes/origin/cycle-worktree", tip, cwd=root)
    real("branch", "--set-upstream-to=origin/cycle-worktree", cwd=root)
    ws.native.pull.update(state="open", merged=False, merged_at=None, merge_commit_sha=None, draft=True)
    ws.native.pull["head"]["sha"] = tip
    receipt = core.initiative_receipt(ws.primary / MANIFEST, "slice-a", ws.primary)
    argv = ["begin", "--cycle-id", "cycle-3", "--context", "test", "--risk", "routine",
            "--delivery-intent", "draft_pr", "--plan", str(ws.plan), "--base-branch", "main",
            "--github-account", external.ACCOUNT, "--github-repository", external.REPOSITORY,
            "--follow-up-pr", str(NUMBER), "--initiative-manifest", MANIFEST, "--initiative-slice", "slice-a",
            "--initiative-digest", receipt["manifest_digest"], "--expected-repository", external.REPOSITORY,
            "--expected-plan-digest", hashlib.sha256(ws.plan.read_bytes()).hexdigest()]
    core.command_begin(core.parser().parse_args([*argv, "--preflight"]))
    launch = json.loads(capsys.readouterr().out)["launch_digest"]
    core.command_begin(core.parser().parse_args(
        [*argv, "--expected-launch-digest", launch, "--approval", "agent-confirmed"]))
    capsys.readouterr()
    follow = core.cycle_dir(root) / "cycles" / "cycle-3.json"
    (root / "tracked.txt").write_text("Follow-up correction\n")
    (root / "docs/specs/test/CHANGELOG.md").write_text("Follow-up correction.\n")
    paths = ["tracked.txt", "docs/specs/test/CHANGELOG.md"]
    for gate in post.required_gates(ws):
        post.evidence(ws, gate, paths=paths)
    core.command_gate_commit(core.parser().parse_args(
        ["gate-commit", "--message", "follow-up", "--gates", *post.required_gates(ws), "--paths", *paths]))
    post.reviews(ws)
    ws.native.pull["head"]["sha"] = real("rev-parse", "HEAD", cwd=root)
    assert ws.invoke("final-push") == 0
    capsys.readouterr()
    follower = json.loads(follow.read_text())
    assert follower["state"] == "awaiting_merge"
    assert follower["delivery"]["follow_up"]["published_head"] == tip
    ws.pr_head = follower["publication"]["head"]
    post.land(ws, pr_head=ws.pr_head, tree=real("rev-parse", f"{ws.pr_head}^{{tree}}", cwd=root))
    ws.native.pull.update(state="closed", merged=True, merged_at=external.MERGED_AT)
    other = elsewhere(ws, monkeypatch)

    # The original cycle is delivered only because every later commit is that linked follow-up's recorded source.
    report = preview(ws, other)
    assert report["delivery"]["status"] == "verified" and report["delivery"]["proof"] == "follow_up_extension"
    assert report["delivery"]["recorded_commits"] == [entry["id"] for entry in original["commits"]] + [
        entry["id"] for entry in follower["commits"]]
    receipt = append(ws, other, report["receipt_digest"])
    assert receipt["cycle_state"] == "completed"
    assert json.loads(ws.path.read_text())["merge_completion"]["proof"] == "follow_up_extension"
    own = preview(ws, other, cycle_id="cycle-3")
    assert own["delivery"]["proof"] == "unchanged_head"
    assert append(ws, other, own["receipt_digest"], cycle_id="cycle-3")["cycle_state"] == "completed"
    assert status(ws)["state"] == status(ws)["state"] == "completed"


@bound
def test_deleted_feature_ref_leaves_the_retained_source_verifiable(waiting, monkeypatch):
    ws = waiting
    retained = real("for-each-ref", "--format=%(refname) %(objectname)", "refs/dbsctr/evidence/cycle-1",
                    cwd=ws.root).split()
    assert retained == ["refs/dbsctr/evidence/cycle-1", ws.publication["head"]]
    post.land(ws)
    real("update-ref", "-d", "refs/heads/cycle-worktree", cwd=ws.root)
    other = elsewhere(ws, monkeypatch)
    report = preview(ws, other)
    assert report["delivery"]["proof"] == "unchanged_head" and report["completion"] == {"status": "ready"}
    assert append(ws, other, report["receipt_digest"])["cycle_state"] == "completed"


@bound
def test_awaiting_publication_retains_its_checkout_until_the_merge_is_verified(waiting, monkeypatch):
    ws = waiting
    monkeypatch.setattr(ws.core, "workspace_processes", lambda root: set())
    code, out = post.removal_check(ws)
    reasons = json.loads(out)["reasons"]
    assert code == 1 and json.loads(out)["eligible"] is False and "cycle_awaiting_merge" in reasons
    assert ws.invoke("worktree-list", "--json") == 0
    # The waiting cycle is still a readable record: inventory coverage stays complete.
    assert json.loads(ws.capsys.readouterr().out)["coverage"]["reasons"] == []
    post.land(ws)
    other = elsewhere(ws, monkeypatch)
    assert append(ws, other, preview(ws, other)["receipt_digest"])["cycle_state"] == "completed"
    code, out = post.removal_check(ws)
    assert code == 1 and "cycle_awaiting_merge" not in json.loads(out)["reasons"]


@bound
def test_a_held_writer_lock_refuses_the_observation_and_changes_nothing(published, monkeypatch):
    ws = published
    post.land(ws)
    other = elsewhere(ws, monkeypatch)
    with contextlib.ExitStack() as stack:
        stack.enter_context(ws.core.evidence_lock(ws.root, "cycle-1"))
        before = state(ws, other)
        assert ws.invoke(*observe(ws), "--preview") == 1
        assert "dbsctrctl:" in ws.capsys.readouterr().err and state(ws, other) == before
        assert receipt_names(ws) == []
    assert preview(ws, other)["completion"] == {"status": "ready"}


@legacy
def test_historical_record_with_an_undisposed_gate_is_refused(delivered, monkeypatch):
    ws = delivered
    post.deliver(ws)
    post.land(ws)
    post.write_record(ws, lambda record: ws.core.apply_gate_result(record, "operate", "pending"))
    other = elsewhere(ws, monkeypatch)
    before = ws.path.read_bytes()
    assert ws.invoke(*observe(ws), "--preview") == 1
    assert "unpassed gate without a valid approved exception" in ws.capsys.readouterr().err
    assert ws.path.read_bytes() == before and receipt_names(ws) == []


from test_initiative_local_launch import launch  # noqa: E402, F401 - shared GitHub Initiative fixture


@pytest.fixture
def enrolled(launch, capsys):
    """A contract cycle whose approved plan also enrolls an evidence policy."""
    helper, fixture, _ = launch
    plan = fixture.plan_path("draft_pr")
    value = json.loads(plan.read_text())
    manifest = fixture.repo / "docs/initiatives/test/MANIFEST.json"
    receipt = helper.initiative_receipt(manifest, "slice-a", fixture.repo)
    value["completion"] = CONTRACT
    value["evidence_policy"] = {"schema_version": 1,
        "requirements": {name: {"revision": "1", "depends_on": [], "gates": ["domain"]}
                         for name in receipt["requirements"]},
        "gates": {"domain": {"authority": "fixture", "argv": [sys.executable, "-c", "print('passed')"],
                             "inputs": ["tracked.txt"], "environment": [], "toolchain_paths": [],
                             "scope_complete": True}}}
    plan.write_text(json.dumps(value))
    argv = fixture.launch_argv
    argv[argv.index("--expected-plan-digest") + 1] = hashlib.sha256(plan.read_bytes()).hexdigest()
    helper.command_begin(helper.parser().parse_args([*argv, "--preflight"]))
    digest = json.loads(capsys.readouterr().out)["launch_digest"]
    helper.command_begin(helper.parser().parse_args(
        [*argv, "--expected-launch-digest", digest, "--approval", "agent-confirmed"]))
    capsys.readouterr()
    return helper, fixture


def test_enrolled_evidence_policy_freezes_its_applicability_with_the_publication(enrolled, capsys, monkeypatch):
    helper, fixture = enrolled
    root = fixture.native_task
    path, _ = helper.load(root)
    program = [sys.executable, "-c", "print('passed')"]
    changelog = "docs/specs/test/CHANGELOG.md"
    (root / changelog).write_text("Synthetic source completion.\n")
    (root / "tracked.txt").write_text("Synthetic source candidate.\n")
    helper.command_record_evidence(helper.parser().parse_args([
        "record-evidence", "domain", "--authority", "fixture", "--path", "tracked.txt",
        "--path", changelog, "--", *program]))
    helper.command_gate_commit(helper.parser().parse_args([
        "gate-commit", "--message", "fixture candidate", "--gates", "domain",
        "--paths", "tracked.txt", changelog]))
    _, record = helper.load(root)
    for name in helper.GATES:  # gate order is a predecessor chain
        if name != "domain" and record["gates"][name]["applicability"] == "required":
            helper.command_record_evidence(helper.parser().parse_args(
                ["record-evidence", name, "--authority", "fixture", "--", *program]))
    for name in ("README", "BACKLOG", "CHANGELOG"):
        review = ["review-artifact", name, "--result", "changed" if name == "CHANGELOG" else "unchanged",
                  "--reason", "Fixture review."]
        helper.command_review(helper.parser().parse_args([*review, *(["--path", changelog] if name == "CHANGELOG" else [])]))
    monkeypatch.setattr(helper, "github_remote_head", lambda *_args: (
        helper.git(root, "rev-parse", "HEAD").stdout.strip(), "refs/heads/fixture"))
    monkeypatch.setattr(helper, "deliver_draft_pr", lambda *_args, **_kwargs: {
        "number": 1, "url": "https://github.com/example/test/pull/1", "draft": True, "state": "OPEN",
        "verified_at": helper.now()})
    path, record = helper.load(root)
    helper.finish_push(root, path, record)
    capsys.readouterr()

    # Publication froze the source applicability with the source it validated; nothing is completed yet.
    published = helper.read_cycle_record(root, path, historical=True)
    publication = published["publication"]
    assert published["state"] == "awaiting_merge" and "completed_at" not in published
    frozen = helper.amendment_json(root, helper.reconciliation_location(
        root, "local-1", published["completion_reconciliation"]["digest"], "plan.json"))
    assert frozen["route"] == "final_push" and frozen["verified_at"] == publication["published_at"]
    assert all(item["disposition"] == "retained" for item in frozen["evidence_dispositions"].values())
    assert helper.effective_evidence_policy(published)["gates"]["domain"]["authority"] == "fixture"

    # Completing later keeps that custody valid: it binds the frozen sections, not the completion fields.
    head, base = published["commits"][-1]["id"], published["git"]["head"]
    receipt = {"digest": "c" * 64, "observed_at": helper.now(),
               "binding": helper.merge_observation_binding(published, path.read_bytes()),
               "completion": {"status": "ready"},
               "native": {"pull_request": {key: publication["pull_request"][key] for key in ("number", "url")},
                          "head": head, "merge": "a" * 40, "merge_parent": base, "target_branch": "main",
                          "target_head": "b" * 40, "merged_at": external.MERGED_AT},
               "delivery": {"proof": "unchanged_head",
                            "recorded_commits": [entry["id"] for entry in published["commits"]]}}
    assert helper.complete_publication(root, path, receipt) == {"cycle_state": "completed"}
    completed = helper.read_cycle_record(root, path, historical=True)
    assert completed["state"] == "completed" and completed["completed_at"] == receipt["observed_at"]
    assert completed["merge_completion"]["publication_digest"] == publication["digest"]
    assert completed["completion_reconciliation"] == published["completion_reconciliation"]
    # A frozen section still cannot change after completion.
    tampered = {**completed, "gates": {**completed["gates"],
                                       "domain": {**completed["gates"]["domain"], "evidence": None}}}
    path.write_text(json.dumps(tampered))
    with pytest.raises(RuntimeError, match="publication snapshot changed"):
        helper.read_cycle_record(root, path, historical=True)
    path.write_text(json.dumps(completed))
    assert helper.read_cycle_record(root, path, historical=True) == completed
