"""Immutable offline records and transitions, never native merge authority.

Qualified future adapters own authentication, actual native evidence, persistence
and mutation. Constructing these objects is not a substitute for those checks.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, is_dataclass, replace
from enum import StrEnum
import hashlib
import json
import re
from typing import Protocol, TypeAlias

MAX_INTEGER = 2**53 - 1
RECORD_LIMIT = 128 * 1024
TARGET_LIMIT = 64 * 1024
MAX_QUEUE = 256
MAX_TICKETS = 4096


class Invalid(ValueError):
    """Fixed structural diagnostic, with no untrusted payload in its message."""


class Conflict(RuntimeError):
    """Known rejected transition/CAS; distinct from an uncertain remote effect."""


class Unavailable(RuntimeError):
    """A required live authority is not supplied by this source slice."""


class Ambiguous(RuntimeError):
    """A later adapter must reconcile an unknown native effect before retry."""


def _require(condition: bool, code: str = "invalid_record") -> None:
    if not condition:
        raise Invalid(code)


def _integer(value: object, minimum: int = 1) -> None:
    _require(type(value) is int and minimum <= value <= MAX_INTEGER, "invalid_integer")


def _hex(value: object, lengths: tuple[int, ...]) -> None:
    _require(isinstance(value, str) and len(value) in lengths
             and re.fullmatch(r"[0-9a-f]+", value) is not None, "invalid_identity")


def _oid(value: object) -> None:
    _hex(value, (40, 64))
    _require(isinstance(value, str) and set(value) != {"0"}, "invalid_oid")


def _digest(value: object) -> None:
    _hex(value, (64,))


def _handle(value: object) -> None:
    _hex(value, tuple(range(16, 65)))


def _repository(value: object) -> None:
    _require(isinstance(value, str) and re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value
    ) is not None, "invalid_repository")


def _branch(value: object) -> None:
    _require(isinstance(value, str), "invalid_branch")
    assert isinstance(value, str)
    _require(0 < len(value) <= 256 and value != "@" and not value.startswith("refs/")
             and not value.endswith(("/", "."))
             and not any(char.isspace() or ord(char) < 33 or ord(char) > 126
                         or char in '~^:?*[\\' for char in value)
             and not any(term in value for term in ("..", "@{", "//"))
             and all(part and not part.startswith(".") and not part.endswith(".lock")
                     for part in value.split("/")), "invalid_branch")


def _tuple(value: object, item_type: type, limit: int, minimum: int = 0) -> None:
    _require(type(value) is tuple and minimum <= len(value) <= limit
             and all(type(item) is item_type for item in value), "invalid_population")


def _oids(value: tuple[str, ...], limit: int, minimum: int = 0) -> None:
    _tuple(value, str, limit, minimum)
    for item in value:
        _oid(item)
    _require(len(set(value)) == len(value), "duplicate_oid")
    _require(len({len(item) for item in value}) <= 1, "mixed_oid_formats")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def _data(value: object) -> dict[str, object]:
    if not is_dataclass(value) or isinstance(value, type):
        raise Invalid("invalid_record")
    return asdict(value)


def _size(value: object, limit: int = RECORD_LIMIT) -> None:
    _require(len(_canonical(_data(value))) <= limit, "record_size_limit")


def _version(value: object) -> None:
    _require(type(value) is int and value == 1, "unsupported_version")


@dataclass(frozen=True, slots=True)
class SourceSeries:
    repository: str
    pr_number: int
    head: str
    phase_commits: tuple[str, ...]
    wrappers: tuple[str, ...]
    authority_digest: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _repository(self.repository)
        _integer(self.pr_number)
        _oid(self.head)
        _digest(self.authority_digest)
        _oids(self.phase_commits, 1024, 1)
        _oids(self.wrappers, 1024)
        _require(not set(self.phase_commits).intersection(self.wrappers), "wrapper_overlaps_phase")
        _require(len(self.phase_commits) + len(self.wrappers) <= 1024, "source_count_limit")
        _require(all(len(oid) == len(self.head) for oid in (*self.phase_commits, *self.wrappers)),
                 "mixed_oid_formats")
        _require(self.head == (self.wrappers or self.phase_commits)[-1], "source_head_unbound")
        _size(self)


@dataclass(frozen=True, slots=True)
class Candidate:
    generation: int
    source_digest: str
    head: str
    base: str
    tested_oid: str
    tested_parents: tuple[str, ...]
    tree: str
    plan_digest: str
    policy_digest: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _integer(self.generation)
        for value in (self.source_digest, self.plan_digest, self.policy_digest):
            _digest(value)
        for value in (self.head, self.base, self.tested_oid, self.tree):
            _oid(value)
        _oids(self.tested_parents, 2, 1)
        _require(len({len(v) for v in (self.head, self.base, self.tested_oid, self.tree,
                                      *self.tested_parents)}) == 1, "mixed_oid_formats")
        _size(self)


@dataclass(frozen=True, slots=True)
class Evidence:
    kind: str
    app_id: int
    native_id: int
    attempt: int
    subject_oid: str
    producer_digest: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _require(self.kind in {"check", "scan"}, "invalid_evidence_kind")
        for value in (self.app_id, self.native_id, self.attempt):
            _integer(value)
        _oid(self.subject_oid)
        _digest(self.producer_digest)


@dataclass(frozen=True, slots=True)
class Qualification:
    candidate_digest: str
    plan_digest: str
    policy_digest: str
    native_guard_digest: str
    evidence: tuple[Evidence, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for value in (self.candidate_digest, self.plan_digest, self.policy_digest, self.native_guard_digest):
            _digest(value)
        _tuple(self.evidence, Evidence, 512, 1)
        _require(len(set(self.evidence)) == len(self.evidence), "duplicate_evidence")
        _size(self)


@dataclass(frozen=True, slots=True)
class Admission:
    source_digest: str
    requester_digest: str
    policy_digest: str
    receipt_digest: str

    def __post_init__(self) -> None:
        for value in (self.source_digest, self.requester_digest, self.policy_digest, self.receipt_digest):
            _digest(value)


@dataclass(frozen=True, slots=True)
class Reservation:
    operation_id: str
    invocation_id: str
    generation: int
    candidate_digest: str
    uncertain: bool = False
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _handle(self.operation_id)
        _handle(self.invocation_id)
        _integer(self.generation)
        _digest(self.candidate_digest)
        _require(type(self.uncertain) is bool, "invalid_uncertainty")


@dataclass(frozen=True, slots=True)
class NoEffect:
    operation_id: str
    invocation_id: str
    candidate_digest: str
    receipt_digest: str

    def __post_init__(self) -> None:
        _handle(self.operation_id)
        _handle(self.invocation_id)
        _digest(self.candidate_digest)
        _digest(self.receipt_digest)


@dataclass(frozen=True, slots=True)
class CommitPair:
    original: str
    landed: str

    def __post_init__(self) -> None:
        _oid(self.original)
        _oid(self.landed)
        _require(len(self.original) == len(self.landed), "mixed_oid_formats")


@dataclass(frozen=True, slots=True)
class Delivery:
    candidate_digest: str
    pr_number: int
    merge_oid: str
    phase_map: tuple[CommitPair, ...]
    receipt_digest: str
    operation_id: str
    invocation_id: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _handle(self.operation_id)
        _handle(self.invocation_id)
        _digest(self.candidate_digest)
        _digest(self.receipt_digest)
        _integer(self.pr_number)
        _oid(self.merge_oid)
        _tuple(self.phase_map, CommitPair, 1024, 1)
        _require(len({p.original for p in self.phase_map}) == len(self.phase_map)
                 and len({p.landed for p in self.phase_map}) == len(self.phase_map), "duplicate_mapping")
        _require(all(len(p.landed) == len(self.merge_oid) for p in self.phase_map), "mixed_oid_formats")
        _size(self)


class State(StrEnum):
    REQUESTED = "requested"
    QUEUED = "queued"
    QUALIFYING = "qualifying"
    AWAITING_OPERATOR = "awaiting_operator"
    MERGE_UNCERTAIN = "merge_uncertain"
    REPAIR_PENDING = "repair_pending"
    DELIVERED = "delivered"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class Ticket:
    handle: str
    source: SourceSeries
    requester_digest: str
    state: State = State.REQUESTED
    sequence: int | None = None
    generation: int = 0
    candidate: Candidate | None = None
    qualification: Qualification | None = None
    reservation: Reservation | None = None
    delivery: Delivery | None = None
    failure_digest: str | None = None
    admission_digest: str | None = None
    reconciliations: tuple[NoEffect, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _handle(self.handle)
        _require(type(self.source) is SourceSeries and type(self.state) is State)
        _digest(self.requester_digest)
        _integer(self.generation, 0)
        if self.sequence is not None:
            _integer(self.sequence)
        if self.failure_digest is not None:
            _digest(self.failure_digest)
        if self.admission_digest is not None:
            _digest(self.admission_digest)
        _tuple(self.reconciliations, NoEffect, 512)
        _require(len({r.operation_id for r in self.reconciliations}) == len(self.reconciliations),
                 "duplicate_reconciliation")
        if self.candidate is not None:
            _require(type(self.candidate) is Candidate)
            _require(self.candidate.source_digest == identity(self.source)
                     and self.candidate.head == self.source.head
                     and self.candidate.generation == self.generation, "candidate_binding")
        if self.qualification is not None:
            _require(type(self.qualification) is Qualification and self.candidate is not None)
            assert self.candidate is not None
            _require(self.qualification.candidate_digest == identity(self.candidate)
                     and self.qualification.plan_digest == self.candidate.plan_digest
                     and self.qualification.policy_digest == self.candidate.policy_digest
                     and all(e.subject_oid in {self.candidate.head, self.candidate.tested_oid}
                             for e in self.qualification.evidence), "qualification_binding")
        if self.reservation is not None:
            _require(type(self.reservation) is Reservation and self.candidate is not None
                     and self.qualification is not None)
            assert self.candidate is not None
            _require(all(r.operation_id != self.reservation.operation_id for r in self.reconciliations),
                     "reservation_reused")
            _require(self.reservation.generation == self.generation
                     and self.reservation.candidate_digest == identity(self.candidate), "reservation_binding")
        if self.delivery is not None:
            _require(type(self.delivery) is Delivery and self.candidate is not None
                     and self.qualification is not None)
            assert self.candidate is not None
            _require(all(r.operation_id != self.delivery.operation_id for r in self.reconciliations),
                     "delivery_operation_reused")
            _require(self.delivery.candidate_digest == identity(self.candidate)
                     and self.delivery.pr_number == self.source.pr_number
                     and tuple(p.original for p in self.delivery.phase_map) == self.source.phase_commits
                     and len(self.delivery.merge_oid) == len(self.source.head), "delivery_binding")
        if self.state in {State.REQUESTED, State.REJECTED}:
            _require(self.sequence is None and self.generation == 0 and self.candidate is None
                     and self.admission_digest is None and not self.reconciliations)
        else:
            _require(self.sequence is not None and self.admission_digest is not None)
        if self.state == State.REQUESTED:
            _require(self.failure_digest is None)
        if self.state == State.QUEUED:
            _require(self.candidate is None)
        if self.state in {State.QUALIFYING, State.AWAITING_OPERATOR, State.MERGE_UNCERTAIN, State.DELIVERED}:
            _require(self.candidate is not None)
        if self.state == State.REPAIR_PENDING:
            _require(self.failure_digest is not None)
        if self.state == State.REJECTED:
            _require(self.failure_digest is not None)
        _require((self.delivery is not None) == (self.state == State.DELIVERED))
        if self.reservation is not None:
            _require(self.state in {State.QUALIFYING, State.MERGE_UNCERTAIN})
            _require(self.reservation.uncertain == (self.state == State.MERGE_UNCERTAIN))
        if self.state == State.MERGE_UNCERTAIN:
            _require(self.reservation is not None)
        if self.state not in {State.QUALIFYING, State.MERGE_UNCERTAIN, State.DELIVERED}:
            _require(self.qualification is None and self.reservation is None)
        _size(self)


@dataclass(frozen=True, slots=True)
class Target:
    repository: str
    default_branch: str
    root_oid: str
    policy_digest: str
    generation: int = 0
    next_sequence: int = 1
    queue: tuple[str, ...] = ()
    active: str | None = None
    retained_count: int = 0
    last_operation: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _repository(self.repository)
        _branch(self.default_branch)
        _oid(self.root_oid)
        _digest(self.policy_digest)
        _integer(self.generation, 0)
        _integer(self.next_sequence)
        _integer(self.retained_count, 0)
        _require(self.retained_count <= MAX_TICKETS, "ticket_count_limit")
        _tuple(self.queue, str, MAX_QUEUE)
        for item in self.queue:
            _handle(item)
        _require(len(set(self.queue)) == len(self.queue), "duplicate_queue_handle")
        if self.active is not None:
            _handle(self.active)
            _require(self.active not in self.queue and self.generation > 0)
        if self.last_operation is not None:
            _handle(self.last_operation)
        _size(self, TARGET_LIMIT)


Record: TypeAlias = SourceSeries | Candidate | Ticket | Target


def encode(value: Record) -> bytes:
    _require(type(value) in {SourceSeries, Candidate, Ticket, Target})
    result = _canonical(asdict(value))
    _require(len(result) <= (TARGET_LIMIT if isinstance(value, Target) else RECORD_LIMIT), "record_size_limit")
    return result


def identity(value: object) -> str:
    """Content identity only; never authentication or native check authority."""
    return hashlib.sha256(_canonical(_data(value))).hexdigest()


@dataclass(frozen=True, slots=True)
class Snapshot:
    target: Target
    tickets: tuple[Ticket, ...]

    def __post_init__(self) -> None:
        _require(type(self.target) is Target)
        _tuple(self.tickets, Ticket, MAX_TICKETS)
        index = {t.handle: t for t in self.tickets}
        _require(len(index) == len(self.tickets) == self.target.retained_count, "ticket_inventory")
        _require(all(t.source.repository == self.target.repository
                     and len(t.source.head) == len(self.target.root_oid)
                     and t.generation <= self.target.generation for t in self.tickets), "target_binding")
        queued = tuple(t.handle for t in sorted(
            (t for t in self.tickets if t.state == State.QUEUED), key=lambda t: t.sequence or 0))
        _require(queued == self.target.queue, "queue_inventory")
        active = [t for t in self.tickets if t.state in {
            State.QUALIFYING, State.AWAITING_OPERATOR, State.MERGE_UNCERTAIN}]
        _require(len(active) <= 1 and (active[0].handle if active else None) == self.target.active,
                 "active_inventory")
        if active:
            _require(active[0].generation == self.target.generation
                     and active[0].candidate is not None
                     and active[0].candidate.policy_digest == self.target.policy_digest, "active_binding")
        sequences = [t.sequence for t in self.tickets if t.sequence is not None]
        _require(len(set(sequences)) == len(sequences)
                 and all(v < self.target.next_sequence for v in sequences), "sequence_inventory")
        pending = [t.source.pr_number for t in self.tickets if t.state in {
            State.REQUESTED, State.QUEUED, State.QUALIFYING, State.AWAITING_OPERATOR, State.MERGE_UNCERTAIN}]
        _require(len(set(pending)) == len(pending), "duplicate_active_pr")

    def ticket(self, handle: str) -> Ticket:
        for ticket in self.tickets:
            if ticket.handle == handle:
                return ticket
        raise Conflict("ticket_missing")


def _replace_ticket(state: Snapshot, ticket: Ticket, target: Target | None = None) -> Snapshot:
    return Snapshot(target or state.target,
                    tuple(ticket if prior.handle == ticket.handle else prior for prior in state.tickets))


def request(state: Snapshot, ticket: Ticket) -> Snapshot:
    if ticket.state != State.REQUESTED:
        raise Conflict("request_state")
    existing = next((prior for prior in state.tickets if prior.handle == ticket.handle), None)
    if existing is not None:
        if (existing.source, existing.requester_digest) != (ticket.source, ticket.requester_digest):
            raise Conflict("request_identity_changed")
        return state
    if len(state.tickets) >= MAX_TICKETS:
        raise Conflict("ticket_capacity")
    return Snapshot(replace(state.target, retained_count=state.target.retained_count + 1),
                    (*state.tickets, ticket))


def admit(state: Snapshot, handle: str, binding: Admission) -> Snapshot:
    _require(type(binding) is Admission)
    ticket = state.ticket(handle)
    if (binding.source_digest, binding.requester_digest, binding.policy_digest) != (
            identity(ticket.source), ticket.requester_digest, state.target.policy_digest):
        raise Conflict("admission_binding")
    if ticket.state != State.REQUESTED:
        if ticket.sequence is not None:
            return state
        raise Conflict("admission_state")
    if len(state.target.queue) >= MAX_QUEUE:
        raise Conflict("queue_capacity")
    target = replace(state.target, next_sequence=state.target.next_sequence + 1,
                     queue=(*state.target.queue, handle))
    return _replace_ticket(state, replace(ticket, state=State.QUEUED,
                           sequence=state.target.next_sequence, admission_digest=binding.receipt_digest), target)


def claim(state: Snapshot, handle: str, candidate: Candidate) -> Snapshot:
    ticket = state.ticket(handle)
    if (state.target.active is not None or not state.target.queue or state.target.queue[0] != handle
            or ticket.state != State.QUEUED or candidate.generation != state.target.generation + 1
            or candidate.source_digest != identity(ticket.source) or candidate.head != ticket.source.head
            or candidate.policy_digest != state.target.policy_digest):
        raise Conflict("claim_binding")
    return _replace_ticket(state, replace(ticket, state=State.QUALIFYING,
        generation=candidate.generation, candidate=candidate), replace(state.target,
        generation=candidate.generation, active=handle, queue=state.target.queue[1:]))


def _active(state: Snapshot, handle: str, generation: int) -> Ticket:
    _integer(generation)
    ticket = state.ticket(handle)
    if state.target.active != handle or state.target.generation != generation or ticket.generation != generation:
        raise Conflict("stale_generation")
    return ticket


def _unreserved(ticket: Ticket) -> None:
    if ticket.reservation is not None:
        raise Conflict("mutation_unresolved")


def wait_for_operator(state: Snapshot, handle: str, generation: int) -> Snapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    return _replace_ticket(state, replace(ticket, state=State.AWAITING_OPERATOR, qualification=None))


def invalidate(state: Snapshot, handle: str, generation: int) -> Snapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    if len(state.target.queue) >= MAX_QUEUE:
        raise Conflict("queue_capacity")
    all_queued = [state.ticket(h) for h in state.target.queue] + [ticket]
    queue = tuple(t.handle for t in sorted(all_queued, key=lambda t: t.sequence or 0))
    return _replace_ticket(state, replace(ticket, state=State.QUEUED, candidate=None, qualification=None),
                           replace(state.target, active=None, queue=queue))


def record_failure(state: Snapshot, handle: str, generation: int, failure_digest: str) -> Snapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    return _replace_ticket(state, replace(ticket, state=State.REPAIR_PENDING,
                           failure_digest=failure_digest, qualification=None), replace(state.target, active=None))


def reserve_merge(state: Snapshot, handle: str, generation: int, qualification: Qualification,
                  operation_id: str, invocation_id: str) -> Snapshot:
    _require(type(qualification) is Qualification)
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    assert ticket.candidate is not None
    if (qualification.candidate_digest != identity(ticket.candidate)
            or qualification.plan_digest != ticket.candidate.plan_digest
            or qualification.policy_digest != state.target.policy_digest):
        raise Conflict("qualification_stale")
    if any(receipt.operation_id == operation_id for receipt in ticket.reconciliations):
        raise Conflict("operation_id_reused")
    if len(ticket.reconciliations) >= 512:
        raise Conflict("reconciliation_capacity")
    reservation = Reservation(operation_id, invocation_id, generation, identity(ticket.candidate))
    try:
        reserved = replace(ticket, state=State.QUALIFYING, qualification=qualification, reservation=reservation)
        _check_outcome_capacity(reserved)
    except Invalid as error:
        if str(error) == "record_size_limit":
            raise Conflict("outcome_capacity") from None
        raise
    return _replace_ticket(state, reserved)


def _check_outcome_capacity(ticket: Ticket) -> None:
    """Reserve byte headroom, not fabricated receipts or native proof.

    Zero-filled fixed-width envelopes are never decoded, stored or admitted.
    All variable-length outcome fields are already bound by the source/reservation.
    """
    assert ticket.reservation is not None and ticket.candidate is not None
    reservation = ticket.reservation
    body = _data(ticket)
    uncertain_reservation = _data(replace(reservation, uncertain=True))
    uncertain = {**body, "state": State.MERGE_UNCERTAIN, "reservation": uncertain_reservation}
    delivery = {
        "schema_version": 1, "candidate_digest": identity(ticket.candidate),
        "pr_number": ticket.source.pr_number, "merge_oid": "0" * len(ticket.source.head),
        "phase_map": [{"original": old, "landed": "0" * len(old)} for old in ticket.source.phase_commits],
        "receipt_digest": "0" * 64,
        "operation_id": reservation.operation_id, "invocation_id": reservation.invocation_id,
    }
    delivered = {**body, "state": State.DELIVERED, "reservation": None, "delivery": delivery}
    no_effect = {"operation_id": reservation.operation_id, "invocation_id": reservation.invocation_id,
                 "candidate_digest": identity(ticket.candidate), "receipt_digest": "0" * 64}
    reconciled = {**body, "state": State.QUALIFYING, "reservation": None, "qualification": None,
                  "reconciliations": [*(_data(receipt) for receipt in ticket.reconciliations), no_effect]}
    if any(len(_canonical(outcome)) > RECORD_LIMIT for outcome in (uncertain, delivered, reconciled)):
        raise Conflict("outcome_capacity")


def mark_uncertain(state: Snapshot, handle: str, generation: int, operation_id: str) -> Snapshot:
    ticket = _active(state, handle, generation)
    if ticket.reservation is None or ticket.reservation.operation_id != operation_id:
        raise Conflict("reservation_binding")
    return _replace_ticket(state, replace(ticket, state=State.MERGE_UNCERTAIN,
                           reservation=replace(ticket.reservation, uncertain=True)))


def resolve_no_effect(state: Snapshot, handle: str, generation: int, proof: NoEffect) -> Snapshot:
    _require(type(proof) is NoEffect)
    ticket = _active(state, handle, generation)
    reservation = ticket.reservation
    if reservation is None or (reservation.operation_id, reservation.invocation_id, reservation.candidate_digest) != (
            proof.operation_id, proof.invocation_id, proof.candidate_digest):
        raise Conflict("reconciliation_binding")
    return _replace_ticket(state, replace(ticket, state=State.QUALIFYING,
                           reservation=None, qualification=None,
                           reconciliations=(*ticket.reconciliations, proof)))


def record_delivery(state: Snapshot, handle: str, generation: int, proof: Delivery) -> Snapshot:
    _require(type(proof) is Delivery)
    ticket = _active(state, handle, generation)
    if ticket.reservation is None or ticket.candidate is None or (
            proof.candidate_digest != identity(ticket.candidate) or proof.pr_number != ticket.source.pr_number
            or proof.operation_id != ticket.reservation.operation_id
            or proof.invocation_id != ticket.reservation.invocation_id
            or tuple(p.original for p in proof.phase_map) != ticket.source.phase_commits):
        raise Conflict("delivery_binding")
    return _replace_ticket(state, replace(ticket, state=State.DELIVERED, delivery=proof,
                           reservation=None), replace(state.target, active=None))


def reject(state: Snapshot, handle: str, failure_digest: str) -> Snapshot:
    ticket = state.ticket(handle)
    if ticket.state != State.REQUESTED:
        raise Conflict("rejection_state")
    return _replace_ticket(state, replace(ticket, state=State.REJECTED, failure_digest=failure_digest))


def _check_transition(before: Snapshot, after: Snapshot) -> None:
    """Replay one legal transition; arbitrary valid snapshots cannot drop custody."""
    prior = {ticket.handle: ticket for ticket in before.tickets}
    current = {ticket.handle: ticket for ticket in after.tickets}
    if not prior.keys() <= current.keys():
        raise Conflict("ticket_deletion")
    changed = [ticket for ticket in after.tickets if prior.get(ticket.handle) != ticket]
    if len(changed) != 1:
        raise Conflict("one_transition_required")
    new = changed[0]
    old = prior.get(new.handle)
    expected: Snapshot
    if old is None:
        expected = request(before, new)
    elif old.state == State.REQUESTED and new.state == State.QUEUED and new.admission_digest is not None:
        expected = admit(before, old.handle, Admission(identity(old.source), old.requester_digest,
                         before.target.policy_digest, new.admission_digest))
    elif old.state == State.REQUESTED and new.state == State.REJECTED and new.failure_digest is not None:
        expected = reject(before, old.handle, new.failure_digest)
    elif old.state == State.QUEUED and new.state == State.QUALIFYING and new.candidate is not None:
        expected = claim(before, old.handle, new.candidate)
    elif old.reservation is not None:
        if new.state == State.DELIVERED and new.delivery is not None:
            expected = record_delivery(before, old.handle, old.generation, new.delivery)
        elif new.reservation is None and len(new.reconciliations) == len(old.reconciliations) + 1:
            expected = resolve_no_effect(before, old.handle, old.generation, new.reconciliations[-1])
        elif new.state == State.MERGE_UNCERTAIN:
            expected = mark_uncertain(before, old.handle, old.generation, old.reservation.operation_id)
        else:
            raise Conflict("mutation_unresolved")
    elif new.reservation is not None and new.qualification is not None:
        expected = reserve_merge(before, old.handle, old.generation, new.qualification,
                                 new.reservation.operation_id, new.reservation.invocation_id)
    elif new.state == State.AWAITING_OPERATOR:
        expected = wait_for_operator(before, old.handle, old.generation)
    elif new.state == State.QUEUED:
        expected = invalidate(before, old.handle, old.generation)
    elif new.state == State.REPAIR_PENDING and new.failure_digest is not None:
        expected = record_failure(before, old.handle, old.generation, new.failure_digest)
    else:
        raise Conflict("transition_unsupported")
    if expected != after:
        raise Conflict("transition_changed")


@dataclass(frozen=True, slots=True)
class AppendRequest:
    expected_head: str
    control_branch: str
    operation_id: str
    state: Snapshot
    before: Snapshot

    def __post_init__(self) -> None:
        _oid(self.expected_head)
        _branch(self.control_branch)
        _handle(self.operation_id)
        _require(type(self.before) is Snapshot and type(self.state) is Snapshot)
        if (self.control_branch == self.state.target.default_branch
                or len(self.expected_head) != len(self.before.target.root_oid)
                or self.operation_id == self.before.target.last_operation
                or self.state.target.last_operation != self.operation_id):
            raise Conflict("append_binding")
        for field in ("repository", "default_branch", "root_oid", "policy_digest"):
            if getattr(self.before.target, field) != getattr(self.state.target, field):
                raise Conflict("target_authority_changed")
        uncommitted = replace(self.state, target=replace(self.state.target,
                              last_operation=self.before.target.last_operation))
        _check_transition(self.before, uncommitted)

    @property
    def additions(self) -> tuple[tuple[str, str], ...]:
        # Derived from the complete validated transition; callers cannot omit writes.
        prior = {ticket.handle: ticket for ticket in self.before.tickets}
        updates: list[tuple[str, Record]] = [("integration/v1/target.json", self.state.target)]
        updates.extend((f"integration/v1/tickets/{t.handle}.json", t)
                       for t in self.state.tickets if prior.get(t.handle) != t)
        return tuple((path, base64.b64encode(encode(value)).decode("ascii"))
                     for path, value in updates)

    def graphql(self) -> dict[str, object]:
        return {"branch": {"repositoryNameWithOwner": self.state.target.repository,
                           "branchName": self.control_branch},
                "expectedHeadOid": self.expected_head,
                "message": {"headline": "chore(integration): append state"},
                "fileChanges": {"additions": [{"path": path, "contents": content}
                                              for path, content in self.additions]},
                "clientMutationId": self.operation_id}


def build_append(before: Snapshot, after: Snapshot, expected_head: str,
                 control_branch: str, operation_id: str) -> AppendRequest:
    if before.target.last_operation != after.target.last_operation:
        raise Conflict("append_history_changed")
    committed = replace(after, target=replace(after.target, last_operation=operation_id))
    return AppendRequest(expected_head, control_branch, operation_id, committed, before)


class IntegrationPorts(Protocol):
    """Later enrolled trusted adapters; no implementation or JSON loader here."""

    def read(self) -> tuple[str, Snapshot]: ...
    def authorize(self, ticket: Ticket) -> Admission: ...
    def qualify(self, candidate: Candidate) -> Qualification: ...
    def append(self, request: AppendRequest) -> str: ...
    def merge(self, candidate: Candidate, reservation: Reservation) -> Delivery: ...
    def reconcile(self, candidate: Candidate, reservation: Reservation) -> Delivery | NoEffect: ...


def unavailable_operation() -> None:
    raise Unavailable("live_adapters_unavailable")


# JSON is a structural boundary. Every accepted member is validated recursively.
def _object(value: object, fields: str) -> dict[str, object]:
    _require(type(value) is dict, "record_fields")
    assert isinstance(value, dict)
    _require(set(value) == set(fields.split()), "record_fields")
    return {key: member for key, member in value.items() if isinstance(key, str)}


def _text(value: object) -> str:
    _require(type(value) is str, "invalid_text")
    assert isinstance(value, str)
    return value


def _int(value: object) -> int:
    _require(type(value) is int, "invalid_integer")
    assert isinstance(value, int)
    return value


def _array(value: object, limit: int = 1024) -> tuple[object, ...]:
    _require(type(value) is list, "invalid_population")
    assert isinstance(value, list)
    _require(len(value) <= limit, "population_limit")
    return tuple(value)


def _source(value: object) -> SourceSeries:
    v = _object(value, "repository pr_number head phase_commits wrappers authority_digest schema_version")
    return SourceSeries(_text(v["repository"]), _int(v["pr_number"]), _text(v["head"]),
        tuple(_text(x) for x in _array(v["phase_commits"])), tuple(_text(x) for x in _array(v["wrappers"])),
        _text(v["authority_digest"]), _int(v["schema_version"]))


def _candidate(value: object) -> Candidate:
    v = _object(value, "generation source_digest head base tested_oid tested_parents tree plan_digest policy_digest schema_version")
    return Candidate(_int(v["generation"]), _text(v["source_digest"]), _text(v["head"]), _text(v["base"]),
        _text(v["tested_oid"]), tuple(_text(x) for x in _array(v["tested_parents"], 2)), _text(v["tree"]),
        _text(v["plan_digest"]), _text(v["policy_digest"]), _int(v["schema_version"]))


def _evidence(value: object) -> Evidence:
    v = _object(value, "kind app_id native_id attempt subject_oid producer_digest schema_version")
    return Evidence(_text(v["kind"]), _int(v["app_id"]), _int(v["native_id"]), _int(v["attempt"]),
                    _text(v["subject_oid"]), _text(v["producer_digest"]), _int(v["schema_version"]))


def _qualification(value: object) -> Qualification:
    v = _object(value, "candidate_digest plan_digest policy_digest native_guard_digest evidence schema_version")
    return Qualification(_text(v["candidate_digest"]), _text(v["plan_digest"]), _text(v["policy_digest"]),
        _text(v["native_guard_digest"]), tuple(_evidence(x) for x in _array(v["evidence"], 512)), _int(v["schema_version"]))


def _reservation(value: object) -> Reservation:
    v = _object(value, "operation_id invocation_id generation candidate_digest uncertain schema_version")
    _require(type(v["uncertain"]) is bool)
    return Reservation(_text(v["operation_id"]), _text(v["invocation_id"]), _int(v["generation"]),
                       _text(v["candidate_digest"]), v["uncertain"] is True, _int(v["schema_version"]))


def _delivery(value: object) -> Delivery:
    v = _object(value, "candidate_digest pr_number merge_oid phase_map receipt_digest operation_id invocation_id schema_version")
    pairs = [_object(x, "original landed") for x in _array(v["phase_map"])]
    return Delivery(_text(v["candidate_digest"]), _int(v["pr_number"]), _text(v["merge_oid"]),
        tuple(CommitPair(_text(x["original"]), _text(x["landed"])) for x in pairs),
        _text(v["receipt_digest"]), _text(v["operation_id"]), _text(v["invocation_id"]),
        _int(v["schema_version"]))


def _no_effect(value: object) -> NoEffect:
    v = _object(value, "operation_id invocation_id candidate_digest receipt_digest")
    return NoEffect(_text(v["operation_id"]), _text(v["invocation_id"]),
                    _text(v["candidate_digest"]), _text(v["receipt_digest"]))


def _ticket(value: object) -> Ticket:
    v = _object(value, "handle source requester_digest state sequence generation candidate qualification reservation delivery failure_digest admission_digest reconciliations schema_version")
    return Ticket(handle=_text(v["handle"]), source=_source(v["source"]),
        requester_digest=_text(v["requester_digest"]), state=State(_text(v["state"])),
        sequence=None if v["sequence"] is None else _int(v["sequence"]), generation=_int(v["generation"]),
        candidate=None if v["candidate"] is None else _candidate(v["candidate"]),
        qualification=None if v["qualification"] is None else _qualification(v["qualification"]),
        reservation=None if v["reservation"] is None else _reservation(v["reservation"]),
        delivery=None if v["delivery"] is None else _delivery(v["delivery"]),
        failure_digest=None if v["failure_digest"] is None else _text(v["failure_digest"]),
        admission_digest=None if v["admission_digest"] is None else _text(v["admission_digest"]),
        reconciliations=tuple(_no_effect(item) for item in _array(v["reconciliations"], 512)),
        schema_version=_int(v["schema_version"]))


def _target(value: object) -> Target:
    v = _object(value, "repository default_branch root_oid policy_digest generation next_sequence queue active retained_count last_operation schema_version")
    return Target(_text(v["repository"]), _text(v["default_branch"]), _text(v["root_oid"]), _text(v["policy_digest"]),
        _int(v["generation"]), _int(v["next_sequence"]), tuple(_text(x) for x in _array(v["queue"], MAX_QUEUE)),
        None if v["active"] is None else _text(v["active"]), _int(v["retained_count"]),
        None if v["last_operation"] is None else _text(v["last_operation"]), _int(v["schema_version"]))


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("duplicate_json_key")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise Invalid("nonfinite_json")


def decode(kind: str, raw: bytes) -> Record:
    limit = TARGET_LIMIT if kind == "target" else RECORD_LIMIT
    _require(type(raw) is bytes and len(raw) <= limit, "record_size_limit")
    try:
        value: object = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
        result: Record
        if kind == "source":
            result = _source(value)
        elif kind == "candidate":
            result = _candidate(value)
        elif kind == "ticket":
            result = _ticket(value)
        elif kind == "target":
            result = _target(value)
        else:
            raise Invalid("record_kind")
        encode(result)
        return result
    except Invalid:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise Invalid("invalid_json_record") from None
