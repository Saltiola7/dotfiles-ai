"""Hosted orchestration fixtures use injected native facts, never credentials."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys
from typing import Never

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core as c
from integration_coordinator import runtime as r
from integration_coordinator import github as g
from integration_coordinator import controller as h


def oid(n: int) -> str:
    return f"{n:040x}"


def digest(n: int) -> str:
    return f"{n:064x}"


def handle(n: int) -> str:
    return f"{n:032x}"


def plan() -> g.CheckPlan:
    receipt = g.ReceiptBinding("proof-{attempt}", "result.json", (
        g.IdentityField(("tested",), "tested_oid"), g.IdentityField(("run",), "run_id"),
        g.IdentityField(("attempt",), "attempt")))
    return g.CheckPlan((g.Producer(g.CheckBinding("test", 7, 8, ".github/workflows/test.yml", "pull_request"), digest(8), receipt),))


def config() -> h.HostedConfig:
    enrollment = g.Enrollment("example/repo", 1, "main", "control", oid(999), digest(2), (5,), (), True,
                              native_guard_digest=h.native_guard_digest(digest(43), digest(44)))
    proposed = h.HostedConfig(enabled=True, enrollment=enrollment,
        check_plan=plan(), workflow_id=80, workflow_path=".github/workflows/coordinate.yml", workflow_blob_oid=oid(700),
        shared_source_pin=oid(701), shared_source_repository="example/shared", job_name="coordinate", requester_ids=(5,))
    return replace(proposed, enrollment=replace(enrollment, policy_digest=h.policy_identity(proposed)))


def policy_digest() -> str:
    enrollment = config().enrollment
    assert enrollment is not None
    return enrollment.policy_digest


def context() -> h.HostContext:
    return h.HostContext("example/repo", 1000, 1, "workflow_dispatch", "refs/heads/main", oid(500), oid(701), "example/shared")


def requested() -> r.Ticket:
    source = r.SourceSeries("example/repo", 1, oid(900), oid(14),
        (r.SourceEntry(oid(11), "phase", ("domain", "behavior")), r.SourceEntry(oid(14), "phase", ("test_driven_implementation",))), digest(1))
    return r.Ticket(handle(1), handle(101), source, r.requester_digest("example/repo", 5), guarded_refresh=True)


def envelope() -> bytes:
    ticket = requested()
    return json.dumps({"schema_version": 2, "policy_digest": policy_digest(), "ticket": asdict(ticket),
                       "obligation": asdict(r.Obligation(ticket.obligation_handle, ticket.handle, digest(6)))}).encode()


class FakeHost:
    def __init__(self) -> None:
        self.stopped = False
        self.verified = 0

    def verify(self, config: h.HostedConfig, context: h.HostContext) -> h.VerifiedHost:
        self.verified += 1
        return h.VerifiedHost(r.Invocation(1000, 1, handle(600), digest(88)), 5, context.event_name, digest(90))

    def quiescent(self, invocation: r.InvocationIdentity) -> bool:
        return self.stopped


class FakeAdapter:
    def __init__(self) -> None:
        enrollment = config().enrollment
        assert enrollment is not None
        self.enrollment = enrollment
        self.plan = plan()
        self.state = r.RuntimeSnapshot(r.Target("example/repo", "main", oid(999), self.enrollment.policy_digest), (), ())
        self.tip = oid(10000)
        self.head = oid(14)
        self.merged = False
        self.landed = oid(503)
        self.tested = oid(901)
        self.qualified_oids: list[str] = []
        self.writes: list[r.AppendRequest] = []
        self.refreshes = 0
        self.merges = 0
        self.fail = False
        self.pending = False
        self.stale_base = False
        self.unknown = False
        self.bad_rules = False

    def observe_policy(self) -> g.TargetGuards:
        return g.TargetGuards((g.CheckRequirement("test", 7),), False, h.native_guard_digest(digest(99 if self.bad_rules else 43), digest(44)))

    def observe_control(self) -> str:
        return digest(44)

    def read_control(self, lookup_handles: tuple[str, ...] = ()) -> tuple[str, dict[str, bytes]]:
        rows = {"integration/v2/target.json": r.encode(self.state.target)}
        rows.update({f"integration/v2/tickets/{v.handle}.json": r.encode(v) for v in self.state.tickets})
        rows.update({f"integration/v2/obligations/{v.handle}.json": r.encode(v) for v in self.state.obligations})
        rows.update({f"integration/v2/archive/tickets/{v.ticket.handle}.json": r.encode(v) for v in self.state.archives})
        return self.tip, rows

    def append(self, request: r.AppendRequest) -> str:
        assert request.expected_head == self.tip
        self.writes.append(request)
        self.state = request.state
        self.tip = oid(int(self.tip, 16) + 1)
        return self.tip

    def observe_pr(self, number: int) -> g.PullFacts:
        return g.PullFacts(number, "PR_node", self.head, oid(900), "task", "main", self.landed if self.merged else self.tested,
                           self.merged, "2026-01-01T00:00:00Z" if self.merged else None)

    def get(self, path: str) -> object:
        if path.startswith("compare/"):
            return {"merge_base_commit": {"sha": oid(899) if self.stale_base else oid(900)}}
        raise AssertionError(path)

    def projection(self, source: r.SourceSeries, head: str, base: str) -> r.Projection:
        mapped = tuple(c.CommitPair(entry.oid, entry.oid if head == source.head else oid(100 + n)) for n, entry in enumerate(source.entries))
        return r.Projection(c.identity(source), base, head, mapped, digest(5))

    def candidate(self, ticket: r.Ticket, generation: int, projection: r.Projection) -> r.Candidate:
        return r.Candidate(generation, c.identity(ticket.source), c.identity(projection), projection.head, projection.base,
                           self.tested, (projection.base, projection.head), oid(902), self.plan.digest, self.enrollment.policy_digest)

    def qualify(self, candidate: r.Candidate, pr_number: int) -> c.Qualification:
        self.qualified_oids.append(candidate.tested_oid)
        if candidate.tested_oid != self.tested:
            raise c.Unavailable("native_candidate_changed")
        if self.fail:
            raise g.FailedChecks(digest(91))
        if self.pending:
            raise c.Unavailable("native_pending")
        return c.Qualification(c.identity(candidate), candidate.plan_digest, candidate.policy_digest, digest(92),
                               (c.Evidence("check", 7, 8, 1, candidate.tested_oid, digest(8)),))

    def refresh(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult:
        self.refreshes += 1
        if self.unknown:
            raise c.Ambiguous("native_unknown")
        self.head = oid(101)
        self.stale_base = False
        return r.RefreshResult(reservation.operation_id, reservation.invocation, reservation.subject_digest,
                               self.projection(ticket.source, self.head, oid(900)), digest(93))

    def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
        self.merges += 1
        assert ticket.candidate is not None and ticket.projection is not None
        self.merged = True
        mapping = tuple(c.CommitPair(pair.landed, oid(502 + n)) for n, pair in enumerate(ticket.projection.mapping))
        self.landed = mapping[-1].landed
        return r.Delivery(reservation.operation_id, reservation.invocation, c.identity(ticket.candidate),
            c.identity(ticket.projection), 1, self.landed, mapping, digest(94))

    def reconcile(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult | r.Delivery | r.NoEffect:
        raise c.Ambiguous("native_request_not_proved_terminal")


def run(adapter: FakeAdapter, host: FakeHost | None = None, raw: bytes | None = None) -> h.Report:
    chosen = host or FakeHost()
    return h.run(config(), context, lambda: chosen, lambda: adapter, lambda: envelope() if raw is None else raw)


def test_disabled_returns_before_context_input_credentials_git_or_provider() -> None:
    def forbidden() -> Never:
        raise AssertionError("disabled startup touched a port")
    assert h.run(h.parse_config(b'{"schema_version":2,"enabled":false}'), forbidden, forbidden, forbidden, forbidden).status == "disabled"
    with pytest.raises(c.Invalid):
        h.parse_config(b'{"schema_version":2,"enabled":false,"credential":"ignored"}')


def test_dispatch_completes_one_proved_delivery_and_archives_before_owner_ack() -> None:
    adapter = FakeAdapter()
    report = run(adapter)
    assert report.status == "delivered"
    assert adapter.merges == 1 and adapter.refreshes == 0
    assert adapter.state.target.retained_count == 0
    assert adapter.state.lookup_ticket(handle(1)).state == r.State.DELIVERED
    assert any(len(request.parents) > 1 for request in adapter.writes)
    # A lost caller response retries against the terminal archive without another merge.
    assert run(adapter).status in {"delivered", "idle"}
    assert adapter.merges == 1


def test_forged_requester_and_oversize_descriptor_never_admit_or_mutate() -> None:
    for raw in (b"x" * (48 * 1024 + 1), envelope().replace(r.requester_digest("example/repo", 5).encode(), digest(99).encode())):
        adapter = FakeAdapter()
        with pytest.raises((c.Invalid, c.Conflict, c.Unavailable)):
            run(adapter, raw=raw)
        assert adapter.writes == [] and adapter.merges == adapter.refreshes == 0


def test_native_policy_drift_blocks_before_any_cas_or_native_effect() -> None:
    adapter = FakeAdapter()
    adapter.bad_rules = True
    with pytest.raises(c.Unavailable):
        run(adapter)
    assert adapter.writes == []


def test_pending_checks_wait_but_terminal_current_ci_failure_returns_to_original_owner() -> None:
    pending = FakeAdapter()
    pending.pending = True
    assert run(pending).status == "waiting"
    assert pending.state.target.active == handle(1)
    failed = FakeAdapter()
    failed.fail = True
    assert run(failed).status == "repair_pending"
    assert failed.state.ticket(handle(1)).failure_digest == digest(91)
    assert failed.state.target.active is None and failed.merges == 0


def test_unknown_refresh_preserves_slot_and_does_not_retry_without_quiescence() -> None:
    adapter = FakeAdapter()
    adapter.stale_base = adapter.unknown = True
    host = FakeHost()
    assert run(adapter, host).status == "uncertain"
    assert adapter.refreshes == 1
    assert adapter.state.ticket(handle(1)).reservation is not None
    assert run(adapter, host).status == "uncertain"
    assert adapter.refreshes == 1
    host.stopped = True
    assert run(adapter, host).status == "uncertain"
    assert adapter.refreshes == 1 and adapter.state.target.active == handle(1)


class NativeFacts:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.run: dict[str, object] = {"id": 1000, "run_attempt": 1, "event": "workflow_dispatch",
            "head_sha": oid(500), "status": "in_progress", "workflow_id": 80,
            "path": ".github/workflows/coordinate.yml", "head_branch": "main",
            "repository": {"id": 1, "full_name": "example/repo"}, "actor": {"id": 5}, "triggering_actor": {"id": 5}}
        self.job: dict[str, object] = {"id": 99, "name": "coordinate", "run_id": 1000, "run_attempt": 1,
            "status": "in_progress", "runner_group_name": "GitHub Actions", "labels": ["ubuntu-latest"]}
        self.blob = oid(700)

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        assert method == "GET" and body is None
        self.calls.append(path)
        if "/jobs?" in path:
            return {"total_count": 1, "jobs": [self.job]}
        if "/contents/" in path:
            return {"type": "file", "sha": self.blob}
        if "/actions/runs/" in path:
            return self.run
        raise AssertionError(path)

    def archive(self, path: str) -> bytes:
        raise AssertionError("host identity never reads artifacts")


def test_native_host_binds_actor_rerunner_job_and_source_but_allows_main_to_advance() -> None:
    facts = NativeFacts()
    port = h.NativeHost(facts)
    first = port.verify(config(), context())
    assert first.actor_id == 5
    assert first.invocation.run_id == 1000
    assert first.invocation.invocation_id == hashlib.sha256(c._canonical({"run_id": 1000, "attempt": 1, "job_id": 99})).hexdigest()
    # The reviewed blob/pinned implementation remain fixed while unrelated main commits land.
    facts.run["head_sha"] = oid(501)
    assert port.verify(config(), replace(context(), workflow_sha=oid(501))).actor_id == 5
    facts.run["status"] = facts.job["status"] = "completed"
    assert port.quiescent(first.invocation)
    with pytest.raises(c.Unavailable):
        port.quiescent(r.OperatorInvocation(5, handle(800), digest(81), digest(82)))


@pytest.mark.parametrize("change", ["actor", "rerunner", "branch", "workflow_blob", "attempt", "self_hosted", "implementation"])
def test_unqualified_host_never_reads_dispatch_or_starts_mutator(change: str) -> None:
    facts = NativeFacts()
    ctx = context()
    if change == "actor": facts.run["actor"] = {"id": 9}
    elif change == "rerunner": facts.run["triggering_actor"] = {"id": 9}
    elif change == "branch": facts.run["head_branch"] = "untrusted-task"
    elif change == "workflow_blob": facts.blob = oid(999)
    elif change == "attempt": facts.run["run_attempt"] = 2
    elif change == "self_hosted": facts.job["labels"] = ["self-hosted"]
    elif change == "implementation": ctx = replace(ctx, implementation_ref=oid(999))
    def forbidden() -> Never:
        raise AssertionError("unqualified host accessed write credential or dispatch input")
    with pytest.raises(c.Unavailable):
        h.run(config(), lambda: ctx, lambda: h.NativeHost(facts), forbidden, forbidden)


def test_other_native_wakeups_cannot_admit_from_dispatch_data() -> None:
    adapter = FakeAdapter()
    def forbidden() -> Never:
        raise AssertionError("callback consumed a new-source descriptor")
    result = h.run(config(), lambda: replace(context(), event_name="workflow_run"), FakeHost, lambda: adapter, forbidden)
    assert result.status == "idle" and adapter.writes == []


def test_single_policy_identity_omits_only_its_own_digest_and_parser_never_repairs_it() -> None:
    value = config()
    assert value.enrollment is not None and value.check_plan is not None
    changed_self = replace(value, enrollment=replace(value.enrollment, policy_digest=digest(99)))
    assert h.policy_identity(changed_self) == h.policy_identity(value)
    assert h.policy_identity(replace(value, workflow_blob_oid=oid(999))) != h.policy_identity(value)
    wire = {"schema_version": 2, "enabled": True, "enrollment": {"schema_version": 2, **asdict(value.enrollment)},
            "check_plan": {"schema_version": 1, **asdict(value.check_plan)}, "workflow_id": value.workflow_id,
            "workflow_path": value.workflow_path, "workflow_blob_oid": value.workflow_blob_oid,
            "shared_source_pin": value.shared_source_pin, "shared_source_repository": value.shared_source_repository,
            "job_name": value.job_name, "requester_ids": value.requester_ids}
    assert h.parse_config(json.dumps(wire).encode()) == value
    wire["workflow_blob_oid"] = oid(999)
    with pytest.raises(c.Invalid):
        h.parse_config(json.dumps(wire).encode())


def test_hosted_main_disabled_ignores_missing_native_context_and_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text('{"schema_version":2,"enabled":false}')
    def forbidden(*args: object, **kwargs: object) -> Never:
        raise AssertionError("disabled entry started host or credentials")
    monkeypatch.setattr(h, "_context", forbidden)
    monkeypatch.setattr(h.g, "HttpTransport", forbidden)
    assert h.hosted_main(policy) == 0


def test_operator_uses_same_scheduler_without_claiming_native_run_identity() -> None:
    adapter = FakeAdapter()
    adapter.pending = True
    assert run(adapter).status == "waiting"
    adapter.pending = False
    authority = h.OperatorAuthority(r.OperatorInvocation(5, handle(800), digest(81), digest(82)), digest(83), handle(1), 1)
    result = h.advance(config(), authority, FakeHost(), adapter)
    assert result.status == "delivered" and adapter.merges == 1
    delivery = adapter.state.lookup_ticket(handle(1)).delivery
    assert delivery is not None and isinstance(delivery.invocation, r.OperatorInvocation)


def test_no_effect_cannot_retry_until_original_worker_is_proved_quiescent() -> None:
    class NoEffectAdapter(FakeAdapter):
        def reconcile(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.NoEffect:
            return r.NoEffect(reservation.operation_id, reservation.invocation, reservation.subject_digest, digest(95))
    adapter = NoEffectAdapter()
    adapter.stale_base = adapter.unknown = True
    host = FakeHost()
    assert run(adapter, host).status == "uncertain" and adapter.refreshes == 1
    assert run(adapter, host).status == "uncertain" and adapter.refreshes == 1
    host.stopped = True
    assert run(adapter, host).status == "uncertain" and adapter.refreshes == 2


def test_proved_native_head_change_exhausts_old_refresh_guard_without_guessing_no_effect() -> None:
    class AppliedAdapter(FakeAdapter):
        def reconcile(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult:
            return r.RefreshResult(reservation.operation_id, reservation.invocation, reservation.subject_digest,
                self.projection(ticket.source, self.head, oid(900)), digest(96))
    adapter = AppliedAdapter()
    adapter.stale_base = adapter.unknown = True
    host = FakeHost()
    assert run(adapter, host).status == "uncertain"
    adapter.head, adapter.stale_base, adapter.unknown = oid(101), False, False
    assert not host.stopped
    assert run(adapter, host).status == "delivered"
    assert adapter.refreshes == 1 and adapter.merges == 1


def test_unenrolled_operator_cannot_enter_the_shared_mutation_path() -> None:
    adapter = FakeAdapter()
    adapter.pending = True
    assert run(adapter).status == "waiting"
    authority = h.OperatorAuthority(r.OperatorInvocation(9, handle(800), digest(81), digest(82)), digest(83), handle(1), 1)
    adapter.pending = False
    before = len(adapter.writes)
    with pytest.raises(c.Unavailable):
        h.advance(config(), authority, FakeHost(), adapter)
    assert len(adapter.writes) == before and adapter.merges == 0


def repair_envelope(adapter: FakeAdapter) -> bytes:
    old = adapter.state.ticket(handle(1))
    entries = (*old.source.entries, r.SourceEntry(oid(15), "phase", ("refactor",)))
    source = replace(old.source, entries=entries, head=oid(15), authority_digest=digest(70))
    child = r.Ticket(handle(3), old.obligation_handle, source, old.requester_digest, old.handle,
                     delivery_mode=old.delivery_mode, guarded_refresh=old.guarded_refresh)
    return json.dumps({"schema_version": 2, "policy_digest": policy_digest(), "ticket": asdict(child),
                       "obligation": asdict(adapter.state.obligation(old.obligation_handle))}).encode()


def test_authenticated_repair_dispatch_supersedes_and_retains_original_obligation() -> None:
    adapter = FakeAdapter()
    adapter.fail = True
    assert run(adapter).status == "repair_pending"
    raw = repair_envelope(adapter)
    adapter.fail = False
    adapter.head = oid(15)
    assert run(adapter, raw=raw).status == "delivered"
    obligation = adapter.state.obligation(handle(101))
    assert obligation.current_ticket == handle(3) and obligation.repair_count == 1 and obligation.revision_count == 2
    assert adapter.state.lookup_ticket(handle(1)).state == r.State.SUPERSEDED
    assert adapter.state.lookup_ticket(handle(3)).state == r.State.DELIVERED
    assert run(adapter, raw=raw).status == "delivered"
    assert adapter.merges == 1


def test_lost_repair_owner_cas_response_resumes_same_successor_without_counter_reset() -> None:
    class Interrupted(FakeAdapter):
        stop = True
        def append(self, request: r.AppendRequest) -> str:
            result = super().append(request)
            if request.state.action is not None and request.state.action.kind == "repair_owner" and self.stop:
                self.stop = False
                raise c.Ambiguous("lost_admission_response")
            return result
    adapter = Interrupted()
    adapter.fail = True
    assert run(adapter).status == "repair_pending"
    raw = repair_envelope(adapter)
    adapter.fail = False
    adapter.head = oid(15)
    with pytest.raises(c.Ambiguous):
        run(adapter, raw=raw)
    assert adapter.state.obligation(handle(101)).repair_count == 1
    # A resumed producer may observe our already-reserved owner, while the old
    # durable outbox still contains the preceding unreserved index observation.
    observed = repair_envelope(adapter)
    assert run(adapter, raw=observed).status == "delivered"
    assert run(adapter, raw=raw).status == "delivered"
    assert adapter.state.obligation(handle(101)).repair_count == 1


def test_missing_or_obsolete_dispatch_policy_cannot_inherit_current_enrollment() -> None:
    for missing in (True, False):
        body = json.loads(envelope())
        if missing:
            body.pop("policy_digest")
        else:
            body["policy_digest"] = digest(99)
        adapter = FakeAdapter()
        with pytest.raises((c.Invalid, c.Unavailable)):
            run(adapter, raw=json.dumps(body).encode())
        assert adapter.writes == [] and adapter.merges == 0


def test_task_without_guarded_refresh_waits_without_rewriting_its_branch() -> None:
    adapter = FakeAdapter()
    adapter.stale_base = True
    raw = json.loads(envelope())
    raw["ticket"]["guarded_refresh"] = False
    result = run(adapter, raw=json.dumps(raw).encode())
    assert result.status == "repair_pending" and result.detail == "task_refresh_not_authorized"
    assert adapter.refreshes == adapter.merges == 0
    assert adapter.state.ticket(handle(1)).reservation is None and adapter.state.target.active is None


def test_task_admin_delivery_cannot_inherit_unenrolled_global_authority() -> None:
    adapter = FakeAdapter()
    raw = json.loads(envelope())
    raw["ticket"]["delivery_mode"] = "admin"
    with pytest.raises(c.Unavailable):
        run(adapter, raw=json.dumps(raw).encode())
    assert adapter.writes == [] and adapter.merges == adapter.refreshes == 0


def test_operator_exact_subject_and_generation_never_select_another_task() -> None:
    adapter = FakeAdapter()
    adapter.pending = True
    assert run(adapter).status == "waiting"
    authority = h.OperatorAuthority(r.OperatorInvocation(5, handle(800), digest(81), digest(82)), digest(83), handle(1), 1)
    count = len(adapter.writes)
    for bad in (replace(authority, expected_handle=handle(2)), replace(authority, expected_generation=2)):
        with pytest.raises(c.Conflict):
            h.advance(config(), bad, FakeHost(), adapter)
    assert len(adapter.writes) == count and adapter.merges == 0


def test_regenerated_synthetic_commit_rebuilds_generation_without_cross_sha_receipts() -> None:
    adapter = FakeAdapter()
    adapter.pending = True
    assert run(adapter).status == "waiting"
    candidate = adapter.state.ticket(handle(1)).candidate
    assert candidate is not None and candidate.tested_oid == oid(901)
    adapter.tested = oid(903)
    adapter.pending = False
    assert run(adapter).status == "delivered"
    delivered = adapter.state.lookup_ticket(handle(1))
    assert delivered.candidate is not None and delivered.candidate.tested_oid == oid(903)
    assert delivered.generation == 2
    assert adapter.qualified_oids == [oid(901), oid(903)]


def test_definite_unchanged_native_rejection_is_durable_and_never_retried_by_wakeups() -> None:
    class Rejected(FakeAdapter):
        def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
            self.merges += 1
            raise g.NativeRejection(digest(97))
    adapter = Rejected()
    assert run(adapter).status == "repair_pending"
    blocked = adapter.state.ticket(handle(1))
    assert blocked.state == r.State.REPAIR_PENDING and blocked.reservation is None
    assert len(blocked.reconciliations) == 1 and blocked.failure_digest is not None
    assert adapter.state.target.active is None
    assert run(adapter).status == "idle"
    assert adapter.merges == 1


def test_definite_rejection_with_new_tested_input_reprepares_without_coding_repair() -> None:
    class Changed(FakeAdapter):
        def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
            if self.merges == 0:
                self.merges += 1
                self.tested = oid(903)
                raise g.NativeRejection(digest(98))
            return super().merge(ticket, reservation)
    adapter = Changed()
    assert run(adapter).status == "delivered"
    delivered = adapter.state.lookup_ticket(handle(1))
    assert delivered.generation == 2 and delivered.failure_digest is None
    assert len(delivered.reconciliations) == 1
    assert adapter.qualified_oids == [oid(901), oid(903)]
    assert adapter.merges == 2


def test_lost_atomic_rejection_response_cannot_leave_a_retryable_reservation_gap() -> None:
    class LostResponse(FakeAdapter):
        stop = True
        def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
            self.merges += 1
            raise g.NativeRejection(digest(97))
        def append(self, request: r.AppendRequest) -> str:
            result = super().append(request)
            if request.state.action is not None and request.state.action.kind == "native_rejected" and self.stop:
                self.stop = False
                assert request.before.ticket(handle(1)).reservation is not None
                assert request.state.ticket(handle(1)).state == r.State.REPAIR_PENDING
                raise c.Ambiguous("lost_final_rejection_response")
            return result
    adapter = LostResponse()
    with pytest.raises(c.Ambiguous):
        run(adapter)
    blocked = adapter.state.ticket(handle(1))
    assert blocked.state == r.State.REPAIR_PENDING and blocked.reservation is None
    assert blocked.failure_digest == digest(97) and len(blocked.reconciliations) == 1
    assert run(adapter).status == "idle"
    assert adapter.merges == 1


def test_full_capacity_crash_after_supersede_archives_before_another_repair_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r, "MAX_TICKETS", 3)
    class TwoRoots(FakeAdapter):
        stop = True
        heads: dict[int, str]
        def observe_pr(self, number: int) -> g.PullFacts:
            return replace(super().observe_pr(number), head=getattr(self, "heads", {}).get(number, self.head))
        def append(self, request: r.AppendRequest) -> str:
            result = super().append(request)
            if request.state.action is not None and request.state.action.kind == "supersede" and self.stop:
                self.stop = False
                raise c.Ambiguous("lost_supersession_response")
            return result
    adapter = TwoRoots()
    adapter.fail = True
    assert run(adapter).status == "repair_pending"
    other_source = r.SourceSeries("example/repo", 2, oid(900), oid(24), (
        r.SourceEntry(oid(21), "phase", ("domain",)), r.SourceEntry(oid(24), "phase", ("test_driven_implementation",))), digest(2))
    other = r.Ticket(handle(2), handle(102), other_source, requested().requester_digest, guarded_refresh=True)
    state = r.admit_authenticated(adapter.state, other, r.Obligation(handle(102), handle(2), digest(6)),
        c.Admission(c.identity(other_source), other.requester_digest, policy_digest(), digest(4)))
    state = r.claim(state, handle(2), oid(900), adapter.plan.digest)
    adapter.state = r.record_failure(state, handle(2), state.target.generation, digest(96))
    first = repair_envelope(adapter)
    adapter.fail = False
    adapter.heads = {1: oid(15), 2: oid(35)}
    with pytest.raises(c.Ambiguous):
        run(adapter, raw=first)
    assert adapter.state.target.retained_count == 3
    source2 = replace(other_source, entries=(*other_source.entries, r.SourceEntry(oid(35), "phase", ("refactor",))),
                      head=oid(35), authority_digest=digest(74))
    child2 = r.Ticket(handle(4), handle(102), source2, other.requester_digest, handle(2), guarded_refresh=True)
    second = json.dumps({"schema_version": 2, "policy_digest": policy_digest(), "ticket": asdict(child2),
                        "obligation": asdict(adapter.state.obligation(handle(102)))}).encode()
    adapter.pending = True
    assert run(adapter, raw=second).status == "waiting"
    assert adapter.state.target.retained_count == 2
    assert adapter.state.obligation(handle(101)).current_ticket == handle(3)
    assert adapter.state.obligation(handle(102)).current_ticket == handle(4)
    assert adapter.state.obligation(handle(101)).repair_count == adapter.state.obligation(handle(102)).repair_count == 1


@pytest.mark.parametrize("reason", ["permission", "head_changed"])
def test_definite_unreserved_task_block_does_not_starve_unrelated_ready_work(reason: str) -> None:
    class TwoPulls(FakeAdapter):
        first_head = oid(14)
        def observe_pr(self, number: int) -> g.PullFacts:
            return replace(super().observe_pr(number), head=self.first_head if number == 1 else oid(24))
        def get(self, path: str) -> object:
            if path.startswith("compare/"):
                return {"merge_base_commit": {"sha": oid(899) if reason == "permission" and path.endswith(oid(14)) else oid(900)}}
            return super().get(path)
        def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
            self.merges += 1
            assert ticket.candidate is not None and ticket.projection is not None
            mapping = tuple(c.CommitPair(pair.landed, oid(502 + n)) for n, pair in enumerate(ticket.projection.mapping))
            return r.Delivery(reservation.operation_id, reservation.invocation, c.identity(ticket.candidate),
                c.identity(ticket.projection), ticket.source.pr_number, mapping[-1].landed, mapping, digest(94))
    adapter = TwoPulls()
    first = replace(requested(), guarded_refresh=False) if reason == "permission" else requested()
    state = r.admit_authenticated(adapter.state, first, r.Obligation(first.obligation_handle, first.handle, digest(6)),
        c.Admission(c.identity(first.source), first.requester_digest, policy_digest(), digest(4)))
    other_source = r.SourceSeries("example/repo", 2, oid(900), oid(24), (
        r.SourceEntry(oid(21), "phase", ("domain",)), r.SourceEntry(oid(24), "phase", ("test_driven_implementation",))), digest(2))
    other = r.Ticket(handle(2), handle(102), other_source, first.requester_digest, guarded_refresh=True)
    state = r.admit_authenticated(state, other, r.Obligation(handle(102), handle(2), digest(6)),
        c.Admission(c.identity(other_source), other.requester_digest, policy_digest(), digest(4)))
    adapter.state = state
    if reason == "head_changed":
        adapter.pending = True
        assert h.run(config(), lambda: replace(context(), event_name="schedule"), FakeHost, lambda: adapter).status == "waiting"
        adapter.first_head = oid(15)
        adapter.pending = False
    blocked = h.run(config(), lambda: replace(context(), event_name="schedule"), FakeHost, lambda: adapter)
    assert blocked.status == "repair_pending" and adapter.state.target.active is None
    assert adapter.state.ticket(handle(1)).source == first.source and adapter.state.ticket(handle(1)).reservation is None
    progressed = h.run(config(), lambda: replace(context(), event_name="schedule"), FakeHost, lambda: adapter)
    assert progressed.status == "delivered" and progressed.handle == handle(2)
    assert adapter.state.ticket(handle(1)).state == r.State.REPAIR_PENDING


def test_unqualified_compare_metadata_cannot_trigger_a_refresh_or_release_custody() -> None:
    class MissingComparison(FakeAdapter):
        def get(self, path: str) -> object:
            return {"merge_base_commit": {}}
    adapter = MissingComparison()
    with pytest.raises((c.Invalid, c.Unavailable)):
        run(adapter)
    assert adapter.refreshes == adapter.merges == 0
    assert adapter.state.target.active == handle(1)
    assert adapter.state.ticket(handle(1)).reservation is None


def test_readonly_historical_quiescence_has_no_fabricated_current_host_context(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = NativeFacts()
    prior = h.NativeHost(facts).verify(config(), context()).invocation
    facts.calls.clear()
    def forbidden(*args: object, **kwargs: object) -> Never:
        raise AssertionError("historical reader fabricated a current hosted run")
    monkeypatch.setattr(h.NativeHost, "verify", forbidden)
    port = h.NativeHost.for_reconciliation(facts, config())
    assert facts.calls == []
    facts.run["status"] = facts.job["status"] = "completed"
    assert port.quiescent(prior)
    assert any("/attempts/1" in path for path in facts.calls)
    with pytest.raises(c.Unavailable):
        h.NativeHost.for_reconciliation(facts, h.HostedConfig())
    enrolled = config().enrollment
    assert enrolled is not None
    with pytest.raises(c.Invalid):
        h.NativeHost.for_reconciliation(facts, replace(config(), enrollment=replace(enrolled, policy_digest=digest(99))))


@pytest.mark.parametrize("reason", ["draft", "closed", "merged", "head_changed"])
def test_positive_queued_source_block_parks_without_claiming_and_next_task_progresses(reason: str) -> None:
    class QueuedSource(FakeAdapter):
        def observe_pr(self, number: int) -> g.PullFacts:
            native = replace(super().observe_pr(number), head=oid(14) if number == 1 else oid(24))
            if number == 1:
                if reason in {"draft", "closed"}:
                    raise g.SourceChanged(digest(98))
                if reason == "merged":
                    return replace(native, merged=True, merged_at="2026-01-01T00:00:00Z", merge_oid=oid(503))
                return replace(native, head=oid(15))
            return native
        def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
            assert ticket.candidate is not None and ticket.projection is not None
            mapping = tuple(c.CommitPair(pair.landed, oid(502 + n)) for n, pair in enumerate(ticket.projection.mapping))
            self.merges += 1
            return r.Delivery(reservation.operation_id, reservation.invocation, c.identity(ticket.candidate),
                c.identity(ticket.projection), ticket.source.pr_number, mapping[-1].landed, mapping, digest(94))
    adapter = QueuedSource()
    first = requested()
    state = r.admit_authenticated(adapter.state, first, r.Obligation(first.obligation_handle, first.handle, digest(6)),
        c.Admission(c.identity(first.source), first.requester_digest, policy_digest(), digest(4)))
    source2 = r.SourceSeries("example/repo", 2, oid(900), oid(24), (
        r.SourceEntry(oid(21), "phase", ("domain",)), r.SourceEntry(oid(24), "phase", ("test_driven_implementation",))), digest(2))
    second = r.Ticket(handle(2), handle(102), source2, first.requester_digest, guarded_refresh=True)
    adapter.state = r.admit_authenticated(state, second, r.Obligation(handle(102), handle(2), digest(6)),
        c.Admission(c.identity(source2), second.requester_digest, policy_digest(), digest(4)))
    result = h.run(config(), lambda: replace(context(), event_name="schedule"), FakeHost, lambda: adapter)
    assert result.status == "repair_pending" and adapter.state.target.active is None
    parked = adapter.state.ticket(handle(1))
    assert parked.state == r.State.REPAIR_PENDING and parked.generation == 0 and parked.candidate is None
    assert adapter.refreshes == adapter.merges == 0
    assert h.run(config(), lambda: replace(context(), event_name="schedule"), FakeHost, lambda: adapter).handle == handle(2)
    assert adapter.merges == 1


def test_hosted_policy_binding_is_a_regular_workspace_relative_json_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    policy = workspace / ".github" / "policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text('{}')
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))
    assert h._workspace_policy_path(policy) == ".github/policy.json"
    outside = tmp_path / "outside.json"
    outside.write_text('{}')
    with pytest.raises(c.Invalid):
        h._workspace_policy_path(outside)
    linked = workspace / "alias.json"
    linked.symlink_to(policy)
    with pytest.raises(c.Invalid):
        h._workspace_policy_path(linked)


def validation_envelope(adapter: FakeAdapter, correction: int = 75) -> bytes:
    old = adapter.state.ticket(handle(1))
    assert old.failure_digest is not None
    request = r.ValidationRepair(old.handle, old.generation, old.failure_digest, digest(correction))
    return json.dumps({"schema_version": 2, "policy_digest": policy_digest(), "ticket": asdict(request),
        "obligation": asdict(adapter.state.obligation(old.obligation_handle))}).encode()


def test_validation_repair_requires_fresh_checks_without_code_or_phase_changes() -> None:
    adapter = FakeAdapter()
    adapter.fail = True
    assert run(adapter).status == "repair_pending"
    old = adapter.state.ticket(handle(1))
    raw = validation_envelope(adapter)
    request = r.decode("validation_repair", c._canonical(json.loads(raw)["ticket"]))
    assert isinstance(request, r.ValidationRepair)
    adapter.fail = False
    assert run(adapter, raw=raw).status == "delivered"
    current = adapter.state.lookup_ticket(r.validation_repair_handle(request))
    assert current.source == old.source and current.projection == old.projection
    assert current.predecessor == old.handle and current.state == r.State.DELIVERED
    assert adapter.state.lookup_ticket(old.handle).state == r.State.SUPERSEDED
    assert adapter.refreshes == 0 and adapter.merges == 1
    assert adapter.qualified_oids == [oid(901), oid(901)]
    obligation = adapter.state.obligation(old.obligation_handle)
    assert obligation.grant_digest == digest(6)
    assert (obligation.repair_count, obligation.revision_count) == (1, 2)
    # Lost dispatcher acknowledgement is an immutable archived lookup, even
    # though the source PR is now closed; it cannot produce another merge.
    assert run(adapter, raw=raw).status == "delivered"
    assert adapter.merges == 1
    assert adapter.state.obligation(old.obligation_handle) == obligation


def test_validation_repair_native_sender_binding_precedes_any_archive_cas() -> None:
    adapter = FakeAdapter()
    adapter.fail = True
    assert run(adapter).status == "repair_pending"
    raw = validation_envelope(adapter)
    other = replace(requested(), handle=handle(2), obligation_handle=handle(102),
                    source=replace(requested().source, pr_number=2))
    receipt = c.Admission(c.identity(other.source), other.requester_digest, policy_digest(), digest(80))
    adapter.state = r.admit_authenticated(adapter.state, other, r.Obligation(handle(102), handle(2), digest(6)), receipt)
    adapter.state = r.reject_queued(adapter.state, other.handle, digest(81))
    class AnotherNativeSender(FakeHost):
        def verify(self, config: h.HostedConfig, context: h.HostContext) -> h.VerifiedHost:
            return replace(super().verify(config, context), actor_id=6)
    before = len(adapter.writes)
    with pytest.raises(c.Unavailable, match="requester"):
        run(adapter, AnotherNativeSender(), raw)
    assert len(adapter.writes) == before and adapter.merges == adapter.refreshes == 0
    assert adapter.state.ticket(other.handle).state == r.State.REJECTED


def test_validation_repair_lost_atomic_cas_response_does_not_duplicate_or_reset_counters() -> None:
    class LostResponse(FakeAdapter):
        stop = True
        def append(self, request: r.AppendRequest) -> str:
            result = super().append(request)
            if request.state.action is not None and request.state.action.kind == "validation_repair" and self.stop:
                self.stop = False
                raise c.Ambiguous("lost_validation_repair_response")
            return result
    adapter = LostResponse()
    adapter.fail = True
    assert run(adapter).status == "repair_pending"
    raw = validation_envelope(adapter)
    adapter.fail = False
    with pytest.raises(c.Ambiguous):
        run(adapter, raw=raw)
    assert adapter.state.obligation(handle(101)).repair_count == 1
    assert run(adapter, raw=raw).status == "delivered"
    assert adapter.state.obligation(handle(101)).repair_count == 1
    assert adapter.merges == 1


def test_validation_repair_archived_duplicate_does_not_resurrect_after_newer_child() -> None:
    class PinnedLookups(FakeAdapter):
        def __init__(self) -> None:
            super().__init__()
            self.cold: dict[str, r.Archive] = {}
        def append(self, request: r.AppendRequest) -> str:
            # Native additive Git writes retain unloaded lifetime archives.
            for row in (*self.state.archives, *request.state.archives):
                self.cold[row.ticket.handle] = row
            return super().append(request)
        def read_control(self, lookup_handles: tuple[str, ...] = ()) -> tuple[str, dict[str, bytes]]:
            head, files = super().read_control(lookup_handles)
            required = {ticket.obligation_handle for ticket in self.state.tickets}
            required.update(self.cold[handle].ticket.obligation_handle for handle in lookup_handles if handle in self.cold)
            current = {row.current_ticket for row in self.state.obligations if row.handle in required}
            requested = set(lookup_handles) | current
            files.update({"integration/v2/archive/tickets/" + handle + ".json": r.encode(self.cold[handle])
                          for handle in requested if handle in self.cold})
            selected = {"integration/v2/archive/tickets/" + handle + ".json" for handle in requested}
            return head, {path: raw for path, raw in files.items()
                          if not path.startswith("integration/v2/archive/") or path in selected}
    adapter = PinnedLookups()
    adapter.fail = True
    assert run(adapter).status == "repair_pending"
    raw = validation_envelope(adapter)
    request = r.decode("validation_repair", c._canonical(json.loads(raw)["ticket"]))
    assert isinstance(request, r.ValidationRepair)
    successor_handle = r.validation_repair_handle(request)
    adapter.fail = False
    adapter.pending = True
    assert run(adapter, raw=raw).status == "waiting"
    adapter.pending = False
    adapter.fail = True
    assert run(adapter, raw=raw).status == "repair_pending"
    successor = adapter.state.ticket(successor_handle)
    changed_source = replace(successor.source, entries=(*successor.source.entries,
        r.SourceEntry(oid(15), "phase", ("refactor",))), head=oid(15), authority_digest=digest(70))
    child = r.Ticket(handle(3), successor.obligation_handle, changed_source, successor.requester_digest,
        predecessor=successor.handle, delivery_mode=successor.delivery_mode, guarded_refresh=successor.guarded_refresh)
    child_raw = json.dumps({"schema_version": 2, "policy_digest": policy_digest(), "ticket": asdict(child),
        "obligation": asdict(adapter.state.obligation(child.obligation_handle))}).encode()
    adapter.fail = False
    adapter.head = oid(15)
    assert run(adapter, raw=child_raw).status == "delivered"
    index = adapter.state.obligation(child.obligation_handle)
    assert (index.current_ticket, index.repair_count, index.revision_count) == (child.handle, 2, 3)
    assert adapter.state.tickets == ()
    before = len(adapter.writes)
    report = run(adapter, raw=raw)
    assert report.status == "accepted" and report.handle == successor.handle
    assert len(adapter.writes) == before and adapter.merges == 1
    assert adapter.state.obligation(child.obligation_handle) == index
