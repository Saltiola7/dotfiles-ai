"""Runtime-v2 state contracts; synthetic facts never establish native authority."""
from dataclasses import asdict, replace
import base64
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core as c
from integration_coordinator import runtime as r


def oid(n: int) -> str:
    return f"{n:040x}"


def digest(n: int) -> str:
    return f"{n:064x}"


def handle(n: int) -> str:
    return f"{n:032x}"


def source(n: int = 1) -> r.SourceSeries:
    entries = (r.SourceEntry(oid(n * 10 + 1), "phase", ("domain", "behavior")),
               r.SourceEntry(oid(n * 10 + 2), "discovery_import"),
               r.SourceEntry(oid(n * 10 + 3), "wrapper"),
               r.SourceEntry(oid(n * 10 + 4), "phase", ("test_driven_implementation",)))
    return r.SourceSeries("example/repo", n, oid(900), entries[-1].oid, entries, digest(n))


def requested(n: int = 1, obligation: str | None = None, predecessor: str | None = None) -> r.Ticket:
    return r.Ticket(handle(n), obligation or handle(n + 100), source(n), digest(3), predecessor, guarded_refresh=True)


def empty() -> r.RuntimeSnapshot:
    return r.RuntimeSnapshot(r.Target("example/repo", "main", oid(999), digest(2)), (), ())


def admission(ticket: r.Ticket) -> c.Admission:
    return c.Admission(c.identity(ticket.source), ticket.requester_digest, digest(2), digest(4))


def queued(count: int = 1) -> r.RuntimeSnapshot:
    state = empty()
    for n in range(1, count + 1):
        ticket = requested(n)
        obligation = r.Obligation(ticket.obligation_handle, ticket.handle, digest(6))
        state = r.admit_authenticated(state, ticket, obligation, admission(ticket))
    return state


def projection(ticket: r.Ticket, n: int = 0) -> r.Projection:
    pairs = tuple(c.CommitPair(entry.oid, entry.oid if n == 0 else oid(n + i))
                  for i, entry in enumerate(ticket.source.entries))
    return r.Projection(c.identity(ticket.source), oid(900), pairs[-1].landed, pairs, digest(5))


def preparing(count: int = 1) -> r.RuntimeSnapshot:
    return r.claim(queued(count), handle(1), oid(900), digest(7))


def qualified(count: int = 1) -> r.RuntimeSnapshot:
    state = preparing(count)
    state = r.bind_projection(state, handle(1), state.target.generation, projection(state.ticket(handle(1))))
    ticket = state.ticket(handle(1))
    assert ticket.projection is not None
    candidate = r.Candidate(ticket.generation, c.identity(ticket.source), c.identity(ticket.projection),
                            ticket.projection.head, oid(900), oid(901),
                            (oid(900), ticket.projection.head), oid(902), digest(7), digest(2))
    return r.bind_candidate(state, handle(1), state.target.generation, candidate)


def invocation(n: int = 1) -> r.Invocation:
    return r.Invocation(1000 + n, n, handle(600 + n), digest(88))


def qualification(state: r.RuntimeSnapshot) -> c.Qualification:
    candidate = state.ticket(handle(1)).candidate
    assert candidate is not None
    evidence = c.Evidence("check", 7, 8, 1, candidate.tested_oid, digest(8))
    return c.Qualification(c.identity(candidate), candidate.plan_digest,
                           candidate.policy_digest, digest(9), (evidence,))


def test_interleaved_source_keeps_original_phase_order_and_closed_encoding() -> None:
    value = source()
    assert value.entries[0].gates == ("domain", "behavior")
    assert value.entries[1].gates == ()
    assert [entry.kind for entry in value.entries] == ["phase", "discovery_import", "wrapper", "phase"]
    assert r.decode("source", r.encode(value)) == value
    body = asdict(value)
    body["extra"] = "untrusted"
    with pytest.raises(c.Invalid):
        r.decode("source", json.dumps(body).encode())
    for entries in ((value.entries[0], value.entries[0]), ()):
        with pytest.raises(c.Invalid):
            replace(value, entries=entries)


def test_atomic_authenticated_admission_is_fifo_idempotent_and_not_caller_identity() -> None:
    state = queued(12)
    assert state.target.queue == tuple(handle(n) for n in range(1, 13))
    assert all(ticket.state == r.State.QUEUED for ticket in state.tickets)
    first = requested()
    assert r.admit_authenticated(state, first, r.Obligation(first.obligation_handle, first.handle, digest(6)), admission(first)) == state
    with pytest.raises(c.Conflict):
        r.admit_authenticated(empty(), first, r.Obligation(first.obligation_handle, first.handle, digest(6)),
                              replace(admission(first), requester_digest=digest(99)))
    assert empty().target.queue == ()


def test_claim_owns_one_slot_before_refresh_and_candidate_binding_requires_projection() -> None:
    state = preparing(2)
    assert state.ticket(handle(1)).state == r.State.PREPARING
    with pytest.raises(c.Conflict):
        r.claim(state, handle(2), oid(900), digest(7))
    with pytest.raises(c.Conflict):
        r.bind_projection(state, handle(1), 1, projection(state.ticket(handle(1)), 100))


def test_refresh_reservation_retains_original_objects_and_fences_unknown_worker() -> None:
    before = preparing(2)
    reserved = r.reserve_native(before, handle(1), 1, "refresh", handle(501), invocation(), retention_digest=digest(30))
    append = r.build_append(before, reserved, oid(1000), "integration-control", handle(701))
    assert append.parents == (oid(1000), source().head)
    assert append.deletions == ()
    with pytest.raises(c.Unavailable):
        append.graphql()
    unknown = r.mark_uncertain(reserved, handle(1), 1, handle(501))
    for action in (lambda: r.record_failure(unknown, handle(1), 1, digest(90)),
                   lambda: r.claim(unknown, handle(2), oid(900), digest(7)),
                   lambda: r.reserve_native(unknown, handle(1), 1, "refresh", handle(502), invocation(2), retention_digest=digest(30))):
        with pytest.raises(c.Conflict):
            action()
    reservation = reserved.ticket(handle(1)).reservation
    assert reservation is not None
    proof = r.RefreshResult(handle(501), invocation(2), reservation.subject_digest,
                            projection(reserved.ticket(handle(1)), 100), digest(91))
    with pytest.raises(c.Conflict):
        r.record_projection(unknown, handle(1), 1, proof)
    fixed = r.record_projection(unknown, handle(1), 1, replace(proof, invocation=invocation()))
    assert fixed.target.active == handle(1)
    assert fixed.target.generation == 2
    assert fixed.ticket(handle(1)).source == source()
    refreshed = fixed.ticket(handle(1)).projection
    assert refreshed is not None and refreshed.head == oid(103)
    assert fixed.ticket(handle(1)).reservation is None
    with pytest.raises(c.Conflict):
        r.record_failure(fixed, handle(1), 1, digest(90))


def test_no_effect_requires_exact_native_invocation_and_preserves_slot() -> None:
    reserved = r.reserve_native(preparing(), handle(1), 1, "refresh", handle(501), invocation(), retention_digest=digest(30))
    reservation = reserved.ticket(handle(1)).reservation
    assert reservation is not None
    proof = r.NoEffect(handle(501), invocation(), reservation.subject_digest, digest(92))
    with pytest.raises(c.Conflict):
        r.resolve_no_effect(reserved, handle(1), 1, replace(proof, invocation=invocation(2)))
    result = r.resolve_no_effect(reserved, handle(1), 1, proof)
    assert result.target.active == handle(1)
    assert result.ticket(handle(1)).reservation is None
    with pytest.raises(c.Conflict):
        r.reserve_native(result, handle(1), 1, "refresh", handle(501), invocation(), retention_digest=digest(30))


def test_delivery_requires_fresh_qualification_and_maps_every_original_entry() -> None:
    before = qualified(2)
    with pytest.raises(c.Conflict):
        r.reserve_native(before, handle(1), 1, "merge", handle(501), invocation(),
                         qualification=replace(qualification(before), policy_digest=digest(99)))
    state = r.reserve_native(before, handle(1), 1, "merge", handle(501), invocation(), qualification=qualification(before))
    ticket = state.ticket(handle(1))
    assert ticket.candidate is not None and ticket.projection is not None
    mapping = tuple(c.CommitPair(pair.landed, oid(100 + n)) for n, pair in enumerate(ticket.projection.mapping))
    proof = r.Delivery(handle(501), invocation(), c.identity(ticket.candidate), c.identity(ticket.projection),
                       1, oid(103), mapping, digest(93))
    with pytest.raises((c.Invalid, c.Conflict)):
        r.record_delivery(state, handle(1), 1, replace(proof, mapping=mapping[1:]))
    result = r.record_delivery(state, handle(1), 1, proof)
    assert result.target.active is None
    assert result.target.queue == (handle(2),)
    assert result.ticket(handle(1)).state == r.State.DELIVERED
    assert r.original_to_landed(result.ticket(handle(1))) == tuple(
        c.CommitPair(entry.oid, oid(100 + n)) for n, entry in enumerate(source().entries))


def test_two_repairs_archive_unique_predecessors_and_keep_one_obligation() -> None:
    state = r.record_failure(qualified(2), handle(1), 1, digest(99))
    obligation_handle = requested().obligation_handle
    for revision in (3, 4):
        old = state.obligation(obligation_handle).current_ticket
        state = r.reserve_repair(state, obligation_handle, old, digest(700 + revision))
        replacement = requested(revision, obligation_handle, old)
        # A repair stays on its original PR, with a new immutable source revision.
        replacement = replace(replacement, source=replace(replacement.source, pr_number=1))
        state = r.supersede(state, obligation_handle, old, replacement, admission(replacement), digest(700 + revision))
        assert r.supersede(state, obligation_handle, old, replacement, admission(replacement), digest(700 + revision)) == state
        with pytest.raises(c.Conflict):
            r.supersede(state, obligation_handle, old, replace(replacement, handle=handle(50 + revision)), admission(replacement), digest(700 + revision))
        state = r.archive(state, old)
        assert state.obligation(obligation_handle).repair_count == revision - 2
        assert state.obligation(obligation_handle).current_ticket == handle(revision)
        assert state.lookup_ticket(old).state == r.State.SUPERSEDED
        assert state.target.queue[-1] == handle(revision)
        if revision == 3:
            # Let unrelated FIFO work finish, then observe a second real repair failure.
            state = r.reject_queued(state, handle(2), digest(94))
            state = r.claim(state, handle(3), oid(900), digest(7))
            state = r.record_failure(state, handle(3), state.target.generation, digest(95))
    assert state.obligation(obligation_handle).revision_count == 3
    assert len(state.archives) == 2


def test_archive_is_atomic_and_releases_working_capacity_without_owner_ack() -> None:
    state = r.reject_queued(queued(), handle(1), digest(90))
    archived = r.archive(state, handle(1))
    assert archived.target.retained_count == 0
    assert archived.tickets == ()
    assert archived.lookup_ticket(handle(1)).state == r.State.REJECTED
    assert r.archive(archived, handle(1)) == archived
    request = r.build_append(state, archived, oid(1000), "integration-control", handle(701))
    assert request.deletions == (f"integration/v2/tickets/{handle(1)}.json",)
    paths = {path for path, _ in request.additions}
    assert f"integration/v2/archive/tickets/{handle(1)}.json" in paths
    assert f"integration/v2/obligations/{requested().obligation_handle}.json" in paths
    assert r.admit_authenticated(archived, requested(), r.Obligation(requested().obligation_handle, handle(1), digest(6)), admission(requested())) == archived
    with pytest.raises(c.Conflict):
        r.archive(queued(), handle(1))


def test_append_replays_whole_transition_and_cannot_hide_writes_or_reset_authority() -> None:
    before = empty()
    after = queued()
    request = r.build_append(before, after, oid(1000), "integration-control", handle(701))
    assert len(request.additions) == 3
    assert request.parents == (oid(1000),)
    assert request.graphql()["expectedHeadOid"] == oid(1000)
    for path, encoded in request.additions:
        body = json.loads(base64.b64decode(encoded))
        assert isinstance(body, dict) and path.startswith("integration/v2/")
    with pytest.raises(c.Conflict):
        r.build_append(before, replace(after, target=replace(after.target, next_sequence=99)), oid(1000), "integration-control", handle(702))
    with pytest.raises(c.Conflict):
        r.build_append(before, replace(after, target=replace(after.target, root_oid=oid(99))), oid(1000), "integration-control", handle(702))


def test_v1_wire_is_unchanged_and_cannot_gain_v2_live_authority() -> None:
    legacy = c.SourceSeries("example/repo", 1, oid(2), (oid(1), oid(2)), (), digest(1))
    encoded = c.encode(legacy)
    assert c.decode("source", encoded) == legacy
    assert json.loads(encoded)["schema_version"] == 1
    with pytest.raises(c.Invalid):
        r.decode("source", encoded)


def test_every_gate_commit_attribution_survives_imports_without_invented_gates() -> None:
    record = source()
    assert r.decode("source", r.encode(record)) == record
    with pytest.raises(c.Invalid):
        r.SourceEntry(oid(20), "phase", ())
    with pytest.raises(c.Invalid):
        r.SourceEntry(oid(20), "wrapper", ("domain",))
    with pytest.raises(c.Invalid):
        r.SourceEntry(oid(20), "phase", ("caller_says_green",))
    with pytest.raises(c.Invalid):
        r.SourceEntry(oid(20), "phase", ("domain", "domain"))


def test_merge_append_preserves_original_and_distinct_refreshed_objects() -> None:
    state = preparing()
    state = r.reserve_native(state, handle(1), 1, "refresh", handle(501), invocation(), retention_digest=digest(30))
    reserved = state.ticket(handle(1)).reservation
    assert reserved is not None
    state = r.record_projection(state, handle(1), 1, r.RefreshResult(handle(501), invocation(), reserved.subject_digest,
                                projection(state.ticket(handle(1)), 100), digest(31)))
    ticket = state.ticket(handle(1))
    assert ticket.projection is not None
    value = r.Candidate(2, c.identity(ticket.source), c.identity(ticket.projection), ticket.current_head,
                        oid(900), oid(901), (oid(900), ticket.current_head), oid(902), digest(7), digest(2))
    state = r.bind_candidate(state, handle(1), 2, value)
    after = r.reserve_native(state, handle(1), 2, "merge", handle(502), invocation(2), qualification=qualification(state))
    request = r.build_append(state, after, oid(1000), "integration-control", handle(703))
    assert request.parents == (oid(1000), source().head, oid(103))
    # A native adapter must additionally prove neither source parent contains the ledger root.
    with pytest.raises(c.Unavailable):
        request.graphql()


def test_closed_codec_roundtrips_native_reservations_checks_and_archival() -> None:
    state = r.reserve_native(qualified(), handle(1), 1, "merge", handle(501), invocation(), qualification=qualification(qualified()))
    unknown = r.mark_uncertain(state, handle(1), 1, handle(501))
    for view in (queued(), preparing(), qualified(), state, unknown):
        ticket = view.ticket(handle(1))
        assert r.decode("ticket", r.encode(ticket)) == ticket
        assert r.decode("target", r.encode(view.target)) == view.target
        assert r.decode("obligation", r.encode(view.obligation(ticket.obligation_handle))) == view.obligation(ticket.obligation_handle)
    for raw in (b'{"schema_version":2,"schema_version":2}', b'NaN', b'[]', b'{}', b'\xff'):
        with pytest.raises(c.Invalid):
            r.decode("ticket", raw)
    body = asdict(unknown.ticket(handle(1)))
    body["reservation"]["uncertain"] = 1
    with pytest.raises(c.Invalid):
        r.decode("ticket", json.dumps(body).encode())


def test_complete_append_write_sets_load_at_one_tip_and_reject_missing_or_aliased_rows() -> None:
    state = queued()
    request = r.build_append(empty(), state, oid(1000), "integration-control", handle(701))
    records = {path: base64.b64decode(value) for path, value in request.additions}
    view = r.load_snapshot(records)
    assert view.target == request.state.target
    assert view.ticket(handle(1)) == state.ticket(handle(1))
    with pytest.raises((c.Invalid, c.Conflict)):
        r.load_snapshot({key: value for key, value in records.items() if "/tickets/" not in key})
    wrong = dict(records)
    wrong[f"integration/v2/tickets/{handle(99)}.json"] = wrong.pop(f"integration/v2/tickets/{handle(1)}.json")
    with pytest.raises(c.Invalid):
        r.load_snapshot(wrong)
    denied = r.reject_queued(view, handle(1), digest(50))
    request2 = r.build_append(view, denied, oid(1001), "integration-control", handle(702))
    records.update({path: base64.b64decode(value) for path, value in request2.additions})
    denied = r.load_snapshot(records)
    request3 = r.build_append(denied, r.archive(denied, handle(1)), oid(1002), "integration-control", handle(703))
    records.update({path: base64.b64decode(value) for path, value in request3.additions})
    for path in request3.deletions:
        records.pop(path)
    terminal = r.load_snapshot(records)
    assert terminal.lookup_ticket(handle(1)).state == r.State.REJECTED
    assert terminal.target.retained_count == 0
    corrupted = dict(records)
    row = json.loads(corrupted[f"integration/v2/obligations/{requested().obligation_handle}.json"])
    row["archive_tip"] = digest(99)
    corrupted[f"integration/v2/obligations/{requested().obligation_handle}.json"] = json.dumps(row).encode()
    with pytest.raises(c.Invalid):
        r.load_snapshot(corrupted)


def test_failure_and_supersession_each_require_their_own_replayable_cas() -> None:
    before = qualified()
    failed = r.record_failure(before, handle(1), 1, digest(99))
    assert r.build_append(before, failed, oid(1000), "integration-control", handle(701)).state.ticket(handle(1)).state == r.State.REPAIR_PENDING
    owner = r.reserve_repair(failed, requested().obligation_handle, handle(1), digest(700))
    assert r.reserve_repair(owner, requested().obligation_handle, handle(1), digest(700)) == owner
    with pytest.raises(c.Conflict):
        r.reserve_repair(owner, requested().obligation_handle, handle(1), digest(701))
    r.build_append(failed, owner, oid(1001), "integration-control", handle(702))
    replacement = replace(requested(3, requested().obligation_handle, handle(1)), source=replace(source(3), pr_number=1))
    successor = r.supersede(owner, requested().obligation_handle, handle(1), replacement, admission(replacement), digest(700))
    request = r.build_append(owner, successor, oid(1002), "integration-control", handle(703))
    assert len(request.additions) == 4  # Target, predecessor, successor and stable obligation.
    with pytest.raises(c.Conflict):
        r.build_append(before, successor, oid(1000), "integration-control", handle(704))


def test_working_capacity_is_not_a_lifetime_delivery_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r, "MAX_TICKETS", 2)
    state = empty()
    for n in range(1, 7):
        ticket = requested(n)
        state = r.admit_authenticated(state, ticket, r.Obligation(ticket.obligation_handle, ticket.handle, digest(6)), admission(ticket))
        state = r.archive(r.reject_queued(state, ticket.handle, digest(90)), ticket.handle)
        # Pinned archive rows remain remote; the next working read need not cache lifetime rows.
        state = r.working_view(state)
    assert state.target.retained_count == 0
    assert state.target.next_sequence == 7


def test_loaded_active_state_rejects_wrong_policy_and_refresh_subject() -> None:
    state = qualified()
    candidate = state.ticket(handle(1)).candidate
    assert candidate is not None
    ticket = replace(state.ticket(handle(1)), candidate=replace(candidate, policy_digest=digest(98)))
    with pytest.raises(c.Invalid):
        replace(state, tickets=(ticket,))
    refresh = r.reserve_native(preparing(), handle(1), 1, "refresh", handle(501), invocation(), retention_digest=digest(30))
    ticket = refresh.ticket(handle(1))
    assert ticket.reservation is not None
    wrong = replace(ticket, reservation=replace(ticket.reservation, subject_digest=digest(99)))
    with pytest.raises(c.Invalid):
        replace(refresh, tickets=(wrong,))


def test_loaded_fifo_cannot_be_reordered_and_repair_owner_cannot_attach_to_unfailed_work() -> None:
    state = queued(2)
    with pytest.raises(c.Invalid):
        replace(state, target=replace(state.target, queue=tuple(reversed(state.target.queue))))
    current = state.obligations[0]
    with pytest.raises(c.Invalid):
        replace(state, obligations=(replace(current, repair_owner=digest(90)), state.obligations[1]))
    with pytest.raises(c.Invalid):
        replace(current, revision_count=3, repair_count=0)


def test_new_base_reprepares_same_slot_with_fresh_generation_and_preserved_projection() -> None:
    before = qualified(2)
    after = r.invalidate(before, handle(1), 1, oid(950), digest(70))
    assert after.target.active == handle(1) and after.target.queue == (handle(2),)
    assert after.target.generation == 2
    ticket = after.ticket(handle(1))
    assert ticket.source == before.ticket(handle(1)).source
    assert ticket.projection == before.ticket(handle(1)).projection
    assert ticket.candidate is None and ticket.qualification is None
    assert ticket.state == r.State.PREPARING and ticket.base == oid(950)
    assert r.build_append(before, after, oid(1000), "integration-control", handle(701)).state.target.generation == 2
    with pytest.raises(c.Conflict):
        r.record_failure(after, handle(1), 1, digest(90))
    reserved = r.reserve_native(before, handle(1), 1, "merge", handle(501), invocation(), qualification=qualification(before))
    with pytest.raises(c.Conflict):
        r.invalidate(reserved, handle(1), 1, oid(950), digest(70))
    assert r.requester_digest("example/repo", 5) != r.requester_digest("example/repo", 6)
    with pytest.raises(c.Invalid):
        r.requester_digest("example/repo", True)


def test_operator_invocation_is_truthful_and_cannot_be_replaced_by_native_run_identity() -> None:
    operator = r.OperatorInvocation(5, handle(800), digest(81), digest(82))
    state = r.reserve_native(preparing(), handle(1), 1, "refresh", handle(501), operator, retention_digest=digest(30))
    ticket = state.ticket(handle(1))
    assert ticket.reservation is not None
    assert r.decode("ticket", r.encode(ticket)) == ticket
    proof = r.NoEffect(handle(501), invocation(), ticket.reservation.subject_digest, digest(92))
    with pytest.raises(c.Conflict):
        r.resolve_no_effect(state, handle(1), 1, proof)
    result = r.resolve_no_effect(state, handle(1), 1, replace(proof, invocation=operator))
    assert result.target.active == handle(1)
    assert "run_id" not in asdict(operator)


def test_repair_cannot_change_the_original_requester_identity() -> None:
    state = r.record_failure(qualified(), handle(1), 1, digest(99))
    state = r.reserve_repair(state, requested().obligation_handle, handle(1), digest(700))
    replacement = replace(requested(3, requested().obligation_handle, handle(1)),
        source=replace(source(3), pr_number=1), requester_digest=digest(99))
    with pytest.raises(c.Conflict):
        r.supersede(state, requested().obligation_handle, handle(1), replacement, admission(replacement), digest(700))


def test_task_permissions_are_immutable_and_refresh_defaults_to_no_authority() -> None:
    denied = replace(preparing().ticket(handle(1)), guarded_refresh=False)
    state = replace(preparing(), tickets=(denied,))
    with pytest.raises(c.Conflict):
        r.reserve_native(state, handle(1), 1, "refresh", handle(501), invocation(), retention_digest=digest(30))
    duplicate = replace(requested(), guarded_refresh=False)
    with pytest.raises(c.Conflict):
        r.admit_authenticated(queued(), duplicate, r.Obligation(duplicate.obligation_handle, duplicate.handle, digest(6)), admission(duplicate))
    failed = r.record_failure(qualified(), handle(1), 1, digest(99))
    owned = r.reserve_repair(failed, requested().obligation_handle, handle(1), digest(700))
    replacement = replace(requested(3, requested().obligation_handle, handle(1)), source=replace(source(3), pr_number=1), delivery_mode="admin")
    with pytest.raises(c.Conflict):
        r.supersede(owned, replacement.obligation_handle, handle(1), replacement, admission(replacement), digest(700))


def test_unadmitted_source_cannot_carry_a_claimed_projection_or_child_authorization() -> None:
    ticket = requested()
    with pytest.raises(c.Invalid):
        replace(ticket, projection=projection(ticket))
    with pytest.raises(c.Invalid):
        replace(ticket, repair_authorization_digest=digest(99))


def test_reserved_repair_headroom_keeps_saturated_failed_roots_recoverable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r, "MAX_TICKETS", 3)
    state = r.record_failure(qualified(2), handle(1), 1, digest(90))
    state = r.claim(state, handle(2), oid(900), digest(7))
    state = r.record_failure(state, handle(2), 2, digest(91))
    third = requested(3)
    with pytest.raises(c.Conflict):
        r.admit_authenticated(state, third, r.Obligation(third.obligation_handle, third.handle, digest(6)), admission(third))
    state = r.reserve_repair(state, requested().obligation_handle, handle(1), digest(70))
    old = state.ticket(handle(1))
    repaired_source = replace(old.source, entries=(*old.source.entries, r.SourceEntry(oid(45), "phase", ("refactor",))), head=oid(45))
    replacement = r.Ticket(handle(4), old.obligation_handle, repaired_source, old.requester_digest, old.handle,
                           delivery_mode=old.delivery_mode, guarded_refresh=old.guarded_refresh)
    state = r.supersede(state, old.obligation_handle, old.handle, replacement, admission(replacement), digest(70))
    assert state.target.retained_count == 3
    state = r.archive(state, old.handle)
    assert state.target.retained_count == 2
    state = r.claim(state, replacement.handle, oid(900), digest(7))
    assert state.target.active == replacement.handle
    assert state.obligation(old.obligation_handle).repair_count == 1


def test_park_queued_keeps_another_tasks_unknown_mutation_and_original_obligation() -> None:
    state = r.reserve_native(qualified(2), handle(1), 1, "merge", handle(501), invocation(), qualification=qualification(qualified(2)))
    state = r.mark_uncertain(state, handle(1), 1, handle(501))
    parked = r.park_queued(state, handle(2), digest(98))
    assert parked.target.active == handle(1) and parked.target.queue == ()
    assert parked.ticket(handle(1)).reservation == state.ticket(handle(1)).reservation
    assert parked.ticket(handle(2)).state == r.State.REPAIR_PENDING and parked.ticket(handle(2)).generation == 0
    assert parked.obligation(requested(2).obligation_handle) == state.obligation(requested(2).obligation_handle)
    assert r.build_append(state, parked, oid(1000), "control", handle(701)).deletions == ()


def validation_request(state: r.RuntimeSnapshot, correction: int = 99) -> "r.ValidationRepair":
    ticket = state.ticket(handle(1))
    assert ticket.failure_digest is not None
    return r.ValidationRepair(ticket.handle, ticket.generation, ticket.failure_digest, digest(correction))


def test_validation_repair_copies_only_server_source_projection_and_queues_after_other_work() -> None:
    before = r.record_failure(qualified(2), handle(1), 1, digest(90))
    old = before.ticket(handle(1))
    request = validation_request(before)
    expected = before.obligation(old.obligation_handle)
    after = r.validation_repair(before, request, expected, admission(old))
    successor = after.ticket(r.validation_repair_handle(request))
    assert successor.handle != old.handle and successor.predecessor == old.handle
    assert successor.source == old.source and successor.projection == old.projection
    assert successor.state == r.State.QUEUED and successor.generation == 0
    assert successor.candidate is successor.qualification is successor.reservation is None
    assert successor.failure_digest is None
    assert (successor.delivery_mode, successor.guarded_refresh) == (old.delivery_mode, old.guarded_refresh)
    assert after.target.queue == (handle(2), successor.handle)
    assert after.ticket(old.handle).state == r.State.SUPERSEDED
    assert after.obligation(old.obligation_handle).repair_count == 1
    assert after.obligation(old.obligation_handle).revision_count == 2
    append = r.build_append(before, after, oid(1000), "control", handle(700))
    assert {path for path, _ in append.additions} == {
        "integration/v2/target.json", "integration/v2/tickets/" + old.handle + ".json",
        "integration/v2/tickets/" + successor.handle + ".json",
        "integration/v2/obligations/" + old.obligation_handle + ".json"}
    forged = replace(after, tickets=tuple(replace(ticket, projection=projection(old, 100))
        if ticket.handle == successor.handle else ticket for ticket in after.tickets))
    with pytest.raises(c.Conflict):
        r.build_append(before, forged, oid(1000), "control", handle(700))


def test_validation_repair_duplicate_survives_archives_and_newer_code_repair_without_reset() -> None:
    before = r.record_failure(qualified(), handle(1), 1, digest(90))
    request = validation_request(before)
    old = before.ticket(handle(1))
    expected = before.obligation(old.obligation_handle)
    state = r.validation_repair(before, request, expected, admission(old))
    successor_handle = r.validation_repair_handle(request)
    state = r.archive(state, old.handle)
    state = r.claim(state, successor_handle, oid(900), digest(7))
    state = r.record_failure(state, successor_handle, state.target.generation, digest(91))
    successor = state.ticket(successor_handle)
    child_source = replace(old.source, entries=(*old.source.entries, r.SourceEntry(oid(15), "phase", ("refactor",))),
                           head=oid(15), authority_digest=digest(71))
    child = r.Ticket(handle(3), old.obligation_handle, child_source, old.requester_digest, successor.handle,
                     delivery_mode=old.delivery_mode, guarded_refresh=old.guarded_refresh)
    state = r.reserve_repair(state, old.obligation_handle, successor.handle, digest(71))
    state = r.supersede(state, old.obligation_handle, successor.handle, child, admission(child), digest(71))
    state = r.archive(state, successor.handle)
    # Both predecessor revisions are cold: their immutable pinned-tip archives
    # are lookup context, while the current working pointer belongs to the child.
    cold = r.working_view(state)
    observed = r.RuntimeSnapshot(cold.target, cold.tickets, cold.obligations, state.archives)
    assert r.validation_repair(observed, request, expected, admission(old)) == observed
    assert observed.obligation(old.obligation_handle).current_ticket == child.handle
    assert (observed.obligation(old.obligation_handle).repair_count,
            observed.obligation(old.obligation_handle).revision_count) == (2, 3)
    with pytest.raises(c.Conflict):
        r.validation_repair(observed, replace(request, correction_digest=digest(98)), expected, admission(old))


@pytest.mark.parametrize("change", ["generation", "failure", "counter", "owner", "requester", "unproved"])
def test_validation_repair_refuses_stale_or_competing_authority(change: str) -> None:
    before = r.record_failure(qualified(), handle(1), 1, digest(90))
    old = before.ticket(handle(1))
    request = validation_request(before)
    expected = before.obligation(old.obligation_handle)
    attestation = admission(old)
    if change == "generation":
        request = replace(request, expected_generation=2)
    elif change == "failure":
        request = replace(request, failure_digest=digest(91))
    elif change == "counter":
        expected = replace(expected, repair_count=1)
    elif change == "owner":
        before = r.reserve_repair(before, old.obligation_handle, old.handle, digest(70))
        expected = before.obligation(old.obligation_handle)
    elif change == "requester":
        attestation = replace(attestation, requester_digest=digest(99))
    else:
        before = r.record_failure(preparing(), handle(1), 1, digest(90))
    with pytest.raises(c.Conflict):
        r.validation_repair(before, request, expected, attestation)


def test_validation_repair_request_has_closed_codec_and_cannot_smuggle_projection() -> None:
    before = r.record_failure(qualified(), handle(1), 1, digest(90))
    request = validation_request(before)
    assert r.decode("validation_repair", r.encode(request)) == request
    for extra in ({"projection": asdict(projection(before.ticket(handle(1))))},
                  {"source": asdict(source())}, {"delivery_mode": "admin"}, {"kind": "ticket"},
                  {"expected_generation": True}):
        with pytest.raises(c.Invalid):
            r.decode("validation_repair", json.dumps({**asdict(request), **extra}).encode())


def test_validation_repair_uses_reserved_headroom_without_taking_other_native_custody(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r, "MAX_TICKETS", 3)
    state = r.record_failure(qualified(2), handle(1), 1, digest(90))
    old = state.ticket(handle(1))
    request = validation_request(state)
    other = requested(3)
    with pytest.raises(c.Conflict, match="working_capacity"):
        r.admit_authenticated(state, other, r.Obligation(other.obligation_handle, other.handle, digest(6)), admission(other))
    state = r.claim(state, handle(2), oid(900), digest(7))
    reservation = r.reserve_native(state, handle(2), state.target.generation, "refresh", handle(501), invocation(),
                                   retention_digest=digest(30))
    uncertain = r.mark_uncertain(reservation, handle(2), reservation.target.generation, handle(501))
    expected = uncertain.obligation(old.obligation_handle)
    after = r.validation_repair(uncertain, request, expected, admission(old))
    assert len(after.tickets) == 3 and after.target.active == handle(2)
    assert after.ticket(handle(2)) == uncertain.ticket(handle(2))
    assert after.target.queue == (r.validation_repair_handle(request),)
    after = r.archive(after, old.handle)
    assert len(after.tickets) == 2 and after.ticket(handle(2)).reservation is not None


def test_validation_repair_never_clears_unknown_reservation_or_imposes_lifetime_count_cap() -> None:
    state = qualified()
    reserved = r.reserve_native(state, handle(1), 1, "merge", handle(501), invocation(), qualification=qualification(state))
    unknown = r.mark_uncertain(reserved, handle(1), 1, handle(501))
    old = unknown.ticket(handle(1))
    request = r.ValidationRepair(old.handle, 1, digest(90), digest(99))
    with pytest.raises(c.Conflict):
        r.validation_repair(unknown, request, unknown.obligation(old.obligation_handle), admission(old))
    assert unknown.target.active == old.handle and unknown.ticket(old.handle).reservation is not None
    failed = r.record_failure(qualified(), handle(1), 1, digest(90))
    index = replace(failed.obligation(old.obligation_handle), repair_count=10000, revision_count=10001)
    failed = replace(failed, obligations=(index,))
    after = r.validation_repair(failed, validation_request(failed), index, admission(failed.ticket(handle(1))))
    assert (after.obligation(old.obligation_handle).repair_count, after.obligation(old.obligation_handle).revision_count) == (10001, 10002)
