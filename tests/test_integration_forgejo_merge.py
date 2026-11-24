"""Protected Forgejo merge contracts over fixture-only ports."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, forgejo, forgejo_ci, forgejo_merge as m, runtime


ORIGIN = "https://forge.example.invalid:8443"
REPOSITORY = "fixture/reference"
PULL = f"/api/v1/repos/{REPOSITORY}/pulls/7"
REPOSITORY_ID = 42
PULL_ID = 101
ACTOR = 73
AUTHOR = 71
REVIEWER = 72
TARGET = "refs/heads/main"
SOURCE = "refs/heads/topic"
BASE = "a" * 40
PREVIOUS = "b" * 40
HEAD = "c" * 40
MERGED = "d" * 40
TREE = "e" * 40
SUCCESSOR = "f" * 40
NEW_SOURCE = "4" * 40
STATUS_ID = 81


class Objects:
    def __init__(self, binding):
        self.binding = binding
        self.refs = {TARGET: BASE, SOURCE: HEAD}
        self.commits = {
            BASE: m.RawCommit(BASE, (), "1" * 40),
            PREVIOUS: m.RawCommit(PREVIOUS, (BASE,), "2" * 40),
            HEAD: m.RawCommit(HEAD, (PREVIOUS,), TREE),
            MERGED: m.RawCommit(MERGED, (BASE, HEAD), TREE),
            SUCCESSOR: m.RawCommit(SUCCESSOR, (MERGED,), "3" * 40),
            NEW_SOURCE: m.RawCommit(NEW_SOURCE, (HEAD,), "5" * 40),
        }

    def ref(self, binding, ref):
        assert binding == self.binding
        return self.refs[ref]

    def commit(self, binding, oid):
        assert binding == self.binding
        if oid not in self.commits:
            raise core.Unavailable("fixture object missing")
        return self.commits[oid]

    def is_ancestor(self, binding, ancestor, descendant):
        if ancestor == descendant:
            return True
        return any(self.is_ancestor(binding, ancestor, parent)
                   for parent in self.commit(binding, descendant).parents)


class Authority:
    def __init__(self, preconditions):
        self.preconditions = preconditions
        self.claimed = None
        self.reject_fence = False

    def verify_reservation(self, intent, reservation):
        if self.reject_fence:
            raise core.Conflict("fixture reservation not current")

    def observe_preconditions(self, intent, reservation):
        return self.preconditions

    def claim_submission(self, intent, reservation):
        if self.claimed is not None:
            raise core.Conflict("fixture submission already claimed")
        self.claimed = (intent, reservation)


class Reader:
    def __init__(self, execution):
        self.execution = execution

    def current_execution(self, subject, check):
        return self.execution


class Transport:
    def __init__(self, binding, objects, authority, now, creator_id):
        self.binding = binding
        self.objects = objects
        self.authority = authority
        self.now = now
        self.creator_id = creator_id
        self.calls = []
        self.open_changes = {}
        self.merged_changes = {}
        self.landed = False
        self.mode = "success"
        self.status = "success"

    def pull(self):
        repo = {"id": REPOSITORY_ID, "full_name": REPOSITORY}
        row = {
            "id": PULL_ID, "number": 7, "html_url": f"{ORIGIN}/{REPOSITORY}/pulls/7",
            "state": "closed" if self.landed else "open",
            "draft": False, "title": "Exercise fixture merge", "merged": self.landed,
            "mergeable": not self.landed,
            "head": {"ref": "topic", "sha": self.objects.refs[SOURCE], "repo": dict(repo)},
            "base": {"ref": "main", "sha": self.objects.refs[TARGET], "repo": dict(repo)},
            "user": {"id": AUTHOR},
            "merge_commit_sha": MERGED if self.landed else None,
            "merged_at": self.now.isoformat() if self.landed else None,
            "merged_by": {"id": ACTOR, "login": self.binding.api_account} if self.landed else None,
        }
        return {**row, **(self.merged_changes if self.landed else self.open_changes)}

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if (method, path) == ("GET", PULL):
            return forgejo.Response(200, self.pull())
        if (method, path) == ("GET", f"/api/v1/repos/{REPOSITORY}/statuses/{HEAD}?page=1&limit=50"):
            return forgejo.Response(200, [{"id": STATUS_ID, "status": self.status,
                "context": "fixture/required", "creator": {"id": self.creator_id},
                "created_at": self.now.isoformat()}], {"X-Total-Count": "1"})
        assert (method, path) == ("POST", f"{PULL}/merge")
        assert self.authority.claimed is not None
        if self.mode in {"success", "lost_after_effect", "reported_without_target"}:
            self.landed = True
        if self.mode in {"success", "lost_after_effect"}:
            self.objects.refs[TARGET] = MERGED
        if self.mode in {"lost_after_effect", "unknown"}:
            raise TimeoutError("fixture lost response")
        return forgejo.Response(200, None)

    @property
    def writes(self):
        return [call for call in self.calls if call[0] == "POST"]


class Fixture:
    def __init__(self, creator_id=61):
        now = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=10)
        binding = forgejo.Binding(ORIGIN, REPOSITORY, REPOSITORY_ID, "git-actor", "merge-actor")
        check = forgejo_ci.RequiredCheck("fixture/required", creator_id, "7" * 64, "8" * 64)
        self.plan = forgejo_ci.CheckPlan(binding, TARGET, "9" * 64, (check,))
        projection = runtime.Projection("1" * 64, BASE, HEAD,
            (core.CommitPair(PREVIOUS, PREVIOUS), core.CommitPair(HEAD, HEAD)), "2" * 64)
        candidate = runtime.Candidate(3, projection.source_digest, core.identity(projection), HEAD, BASE,
            HEAD, (PREVIOUS,), TREE, core.identity(self.plan), self.plan.policy_digest)
        subject = forgejo_ci.Subject(binding, TARGET, 7, candidate)
        target = m.MergeTarget(binding, TARGET, ACTOR, "3" * 64, "4" * 64)
        self.intent = m.MergeIntent(target, subject, SOURCE, projection, PULL_ID)
        grant = m.GuardGrant(REPOSITORY_ID, TARGET, BASE, HEAD, TREE, ACTOR, PULL_ID,
            int((now + timedelta(hours=1)).timestamp()))
        self.authority = Authority(m.MergePreconditions(target, self.plan.policy_digest, REVIEWER, HEAD, grant))
        self.objects = Objects(binding)
        self.transport = Transport(binding, self.objects, self.authority, now, creator_id)
        invocation = runtime.Invocation(100, 2, "5" * 32, check.definition_digest)
        self.reservation = runtime.NativeReservation("merge", "6" * 32, invocation,
            candidate.generation, core.identity(candidate), HEAD, BASE)
        receipt = forgejo_ci.ExecutionReceipt(subject, check.context, STATUS_ID, check.producer_digest,
            invocation, True, "success", completed_at=now)
        self.reader = Reader(forgejo_ci.Execution(subject, check.context, check.producer_digest,
            invocation, "completed", (receipt,), started_at=now - timedelta(seconds=5)))

    def submit(self):
        return m.merge(self.intent, self.reservation, self.plan, self.transport,
                       self.objects, self.authority, self.reader)

    def reconcile(self):
        uncertain = replace(self.reservation, uncertain=True)
        return m.reconcile(self.intent, uncertain, self.transport, self.objects, self.authority)


def test_fixture_guard_grant_defaults_to_the_approved_synthetic_schema():
    grant = m.GuardGrant(42, "refs/heads/main", "a" * 40, "b" * 40, "c" * 40, 73, 101, 4_000_000_000)
    assert grant.synthetic is True
    assert grant.schema_version == 1


def test_one_ordinary_expected_head_merge_returns_raw_fixture_proof():
    fixture = Fixture()

    result = fixture.submit()

    assert isinstance(result, m.VerifiedMerge)
    assert (result.merge_oid, result.target_oid) == (MERGED, MERGED)
    assert result.projection_digest == core.identity(fixture.intent.projection)
    assert len(result.receipt_digest) == 64
    assert len(fixture.transport.writes) == 1
    _, path, body = fixture.transport.writes[0]
    assert path == f"{PULL}/merge"
    assert (body["Do"], body["head_commit_id"]) == ("merge", HEAD)
    assert body.get("merge_when_checks_succeed", False) is False
    assert not body.get("delete_branch_after_merge")
    assert fixture.authority.claimed == (fixture.intent, fixture.reservation)


@pytest.mark.parametrize("problem", [
    "reservation", "generation", "base", "head", "pr_id", "draft", "not_mergeable", "missing_guard",
    "guard_digest", "dispatcher_digest", "guard_pr_id", "guard_actor", "guard_tree",
    "guard_expired", "policy", "reviewer", "reviewed_head", "no_ci_receipt", "red_status",
    "reviewer_ci_creator", "merge_actor_ci_creator", "unbound_raw_chain",
])
def test_unapproved_or_stale_effect_has_no_submission(problem):
    fixture = Fixture(creator_id=ACTOR) if problem == "merge_actor_ci_creator" else Fixture()
    current = fixture.authority.preconditions
    if problem == "reservation":
        fixture.authority.reject_fence = True
    elif problem == "generation":
        fixture.reservation = replace(fixture.reservation, generation=4)
    elif problem == "base":
        fixture.objects.refs[TARGET] = SUCCESSOR
    elif problem == "head":
        fixture.objects.refs[SOURCE] = PREVIOUS
        row = fixture.transport.pull()["head"]
        fixture.transport.open_changes["head"] = {**row, "sha": PREVIOUS}
    elif problem == "pr_id":
        fixture.transport.open_changes["id"] = 102
    elif problem == "draft":
        fixture.transport.open_changes["draft"] = True
    elif problem == "not_mergeable":
        fixture.transport.open_changes["mergeable"] = False
    elif problem == "missing_guard":
        current = None
    elif problem == "guard_digest":
        current = replace(current, target=replace(current.target, guard_digest="9" * 64))
    elif problem == "dispatcher_digest":
        current = replace(current, target=replace(current.target, dispatcher_digest="9" * 64))
    elif problem == "guard_pr_id":
        current = replace(current, grant=replace(current.grant, pull_request_id=7))
    elif problem == "guard_actor":
        current = replace(current, grant=replace(current.grant, actor_id=AUTHOR))
    elif problem == "guard_tree":
        current = replace(current, grant=replace(current.grant, tested_tree="9" * 40))
    elif problem == "guard_expired":
        current = replace(current, grant=replace(current.grant, expires_at=1))
    elif problem == "policy":
        current = replace(current, policy_digest="0" * 64)
    elif problem == "reviewer":
        current = replace(current, reviewer_id=AUTHOR)
    elif problem == "reviewer_ci_creator":
        current = replace(current, reviewer_id=fixture.plan.checks[0].creator_id)
    elif problem == "reviewed_head":
        current = replace(current, reviewed_head=PREVIOUS)
    elif problem == "no_ci_receipt":
        fixture.reader.execution = None
    elif problem == "red_status":
        fixture.transport.status = "failure"
    elif problem == "unbound_raw_chain":
        fixture.objects.commits[PREVIOUS] = replace(fixture.objects.commits[PREVIOUS], parents=())
    fixture.authority.preconditions = current

    with pytest.raises((core.Invalid, core.Conflict, core.Unavailable)):
        fixture.submit()
    assert fixture.transport.writes == []
    assert fixture.authority.claimed is None


def test_ci_superseded_during_precondition_read_cannot_authorize_post(monkeypatch):
    fixture = Fixture()
    current = fixture.authority.preconditions

    def observe_preconditions(_intent, _reservation):
        fixture.transport.status = "failure"
        execution = fixture.reader.execution
        receipt = replace(execution.receipts[0], conclusion="failure")
        fixture.reader.execution = replace(execution, receipts=(receipt,))
        return current

    monkeypatch.setattr(fixture.authority, "observe_preconditions", observe_preconditions)
    with pytest.raises(core.Unavailable):
        fixture.submit()
    assert fixture.transport.writes == []
    assert fixture.authority.claimed is None


def test_lost_claim_acknowledgement_remains_ambiguous_without_native_post(monkeypatch):
    fixture = Fixture()
    claim = fixture.authority.claim_submission

    def persist_then_lose_ack(intent, reservation):
        claim(intent, reservation)
        raise OSError("fixture claim acknowledgement lost")

    monkeypatch.setattr(fixture.authority, "claim_submission", persist_then_lose_ack)
    with pytest.raises(core.Ambiguous):
        fixture.submit()
    assert fixture.authority.claimed == (fixture.intent, fixture.reservation)
    with pytest.raises(core.Ambiguous):
        fixture.reconcile()
    assert fixture.transport.writes == []


@pytest.mark.parametrize("problem", ["parents", "tree", "actor", "pr", "missing_object", "missing_merge", "target"])
def test_native_success_without_complete_raw_delivery_proof_is_uncertain(problem):
    fixture = Fixture()
    if problem == "parents":
        fixture.objects.commits[MERGED] = replace(fixture.objects.commits[MERGED], parents=(HEAD, BASE))
    elif problem == "tree":
        fixture.objects.commits[MERGED] = replace(fixture.objects.commits[MERGED], tree="9" * 40)
    elif problem == "actor":
        fixture.transport.merged_changes["merged_by"] = {"id": AUTHOR, "login": "different-actor"}
    elif problem == "pr":
        fixture.transport.merged_changes["id"] = 102
    elif problem == "missing_object":
        del fixture.objects.commits[MERGED]
    elif problem == "missing_merge":
        fixture.transport.merged_changes["merge_commit_sha"] = None
    else:
        fixture.transport.mode = "reported_without_target"

    with pytest.raises(core.Ambiguous):
        fixture.submit()
    if problem == "pr":
        fixture.authority.preconditions = None
        with pytest.raises(core.Ambiguous):
            fixture.reconcile()
    assert len(fixture.transport.writes) == 1


def test_lost_reply_reconciles_read_only_after_both_branches_advance():
    fixture = Fixture()
    fixture.transport.mode = "lost_after_effect"
    with pytest.raises(core.Ambiguous):
        fixture.submit()
    fixture.objects.refs[SOURCE] = NEW_SOURCE
    fixture.objects.refs[TARGET] = SUCCESSOR
    fixture.authority.preconditions = None

    result = fixture.reconcile()

    assert (result.merge_oid, result.target_oid) == (MERGED, SUCCESSOR)
    assert len(fixture.transport.writes) == 1


def test_lost_reply_with_unchanged_ref_remains_uncertain_and_cannot_post_twice():
    fixture = Fixture()
    fixture.transport.mode = "unknown"
    with pytest.raises(core.Ambiguous):
        fixture.submit()
    assert fixture.objects.ref(fixture.intent.target.binding, TARGET) == BASE
    with pytest.raises(core.Ambiguous):
        fixture.reconcile()
    with pytest.raises((core.Conflict, core.Ambiguous)):
        fixture.submit()
    assert len(fixture.transport.writes) == 1


def test_uncertain_prior_reservation_cannot_submit_a_native_write():
    fixture = Fixture()
    fixture.reservation = replace(fixture.reservation, uncertain=True)
    for _ in range(2):
        with pytest.raises((core.Conflict, core.Ambiguous)):
            fixture.submit()
    assert fixture.transport.writes == []
    assert fixture.authority.claimed is None
