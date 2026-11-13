"""Version-two extension of the coordinator ledger engine.

These records and pure transitions prove structural custody only. Authenticated
admission, native replay, policy and actual side effects belong to qualified ports.
Version-one records and their codecs remain in :mod:`core` without reinterpretation.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, fields, is_dataclass, replace
from enum import StrEnum
import json
import hashlib
from collections.abc import Mapping
from typing import TypeAlias

from . import core as c

Invalid = c.Invalid
Conflict = c.Conflict
Unavailable = c.Unavailable
Ambiguous = c.Ambiguous
identity = c.identity
MAX_TICKETS = c.MAX_TICKETS
MAX_ARCHIVE_CONTEXT = 32


def requester_digest(repository: str, requester_id: int) -> str:
    """Stable native identity binding; never proof of private validation by itself."""
    c._repository(repository)
    c._integer(requester_id)
    return hashlib.sha256(c._canonical({"repository": repository, "requester_id": requester_id})).hexdigest()


def _version(value: object) -> None:
    c._require(type(value) is int and value == 2, "unsupported_version")


@dataclass(frozen=True, slots=True)
class SourceEntry:
    oid: str
    kind: str
    gates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        c._oid(self.oid)
        c._require(self.kind in {"phase", "discovery_import", "wrapper"}, "source_kind")
        c._tuple(self.gates, str, 11)
        known = {"domain", "behavior", "spec", "contract", "test_driven_implementation", "refactor",
                 "review_integrate", "release", "deploy", "operate", "maintain_retire"}
        c._require(len(set(self.gates)) == len(self.gates) and set(self.gates) <= known, "source_gates")
        c._require((self.kind == "phase") == bool(self.gates), "source_gates")


@dataclass(frozen=True, slots=True)
class SourceSeries:
    repository: str
    pr_number: int
    base: str
    head: str
    entries: tuple[SourceEntry, ...]
    authority_digest: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._repository(self.repository)
        c._integer(self.pr_number)
        c._oid(self.base)
        c._oid(self.head)
        c._digest(self.authority_digest)
        c._tuple(self.entries, SourceEntry, 1024, 1)
        c._oids(tuple(entry.oid for entry in self.entries), 1024, 1)
        c._require(self.head == self.entries[-1].oid and self.base not in {entry.oid for entry in self.entries}, "source_interval")
        c._require(all(len(entry.oid) == len(self.base) == len(self.head) for entry in self.entries), "mixed_oid_formats")
        c._require(any(entry.kind == "phase" for entry in self.entries), "source_phase_missing")
        c._size(self)


@dataclass(frozen=True, slots=True)
class Projection:
    source_digest: str
    base: str
    head: str
    mapping: tuple[c.CommitPair, ...]
    receipt_digest: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._digest(self.source_digest)
        c._digest(self.receipt_digest)
        c._oid(self.base)
        c._oid(self.head)
        c._tuple(self.mapping, c.CommitPair, 1024, 1)
        c._oids(tuple(pair.original for pair in self.mapping), 1024, 1)
        c._oids(tuple(pair.landed for pair in self.mapping), 1024, 1)
        c._require(self.head == self.mapping[-1].landed and self.base not in {pair.landed for pair in self.mapping}
                   and all(len(pair.original) == len(self.head) == len(self.base) for pair in self.mapping),
                   "projection_interval")
        c._size(self)


def _projection(source: SourceSeries, value: Projection) -> None:
    c._require(type(value) is Projection and value.source_digest == identity(source)
               and tuple(pair.original for pair in value.mapping) == tuple(entry.oid for entry in source.entries),
               "projection_binding")


@dataclass(frozen=True, slots=True)
class Candidate:
    generation: int
    source_digest: str
    projection_digest: str
    head: str
    base: str
    tested_oid: str
    tested_parents: tuple[str, ...]
    tree: str
    plan_digest: str
    policy_digest: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._digest(self.projection_digest)
        # Share v1's supported object formats and candidate/check primitives.
        c.Candidate(self.generation, self.source_digest, self.head, self.base, self.tested_oid,
                    self.tested_parents, self.tree, self.plan_digest, self.policy_digest)
        c._size(self)


@dataclass(frozen=True, slots=True)
class Invocation:
    run_id: int
    attempt: int
    invocation_id: str
    workflow_digest: str

    def __post_init__(self) -> None:
        c._integer(self.run_id)
        c._integer(self.attempt)
        c._handle(self.invocation_id)
        c._digest(self.workflow_digest)


@dataclass(frozen=True, slots=True)
class OperatorInvocation:
    requester_id: int
    invocation_id: str
    custody_digest: str
    scope_digest: str
    kind: str = "operator"
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._require(self.kind == "operator", "operator_kind")
        c._integer(self.requester_id)
        c._handle(self.invocation_id)
        c._digest(self.custody_digest)
        c._digest(self.scope_digest)


InvocationIdentity: TypeAlias = Invocation | OperatorInvocation


@dataclass(frozen=True, slots=True)
class NativeReservation:
    kind: str
    operation_id: str
    invocation: InvocationIdentity
    generation: int
    subject_digest: str
    expected_head: str
    expected_base: str
    retention_digest: str | None = None
    uncertain: bool = False
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._require(self.kind in {"refresh", "merge"}, "mutation_kind")
        c._handle(self.operation_id)
        c._require(type(self.invocation) in {Invocation, OperatorInvocation}, "native_invocation")
        c._integer(self.generation)
        c._digest(self.subject_digest)
        c._oid(self.expected_head)
        c._oid(self.expected_base)
        c._require(len(self.expected_head) == len(self.expected_base), "mixed_oid_formats")
        c._require(type(self.uncertain) is bool, "invalid_uncertainty")
        if self.kind == "refresh":
            c._digest(self.retention_digest)
        else:
            c._require(self.retention_digest is None, "merge_retention")


@dataclass(frozen=True, slots=True)
class RefreshResult:
    operation_id: str
    invocation: InvocationIdentity
    subject_digest: str
    projection: Projection
    receipt_digest: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._handle(self.operation_id)
        c._require(type(self.invocation) in {Invocation, OperatorInvocation} and type(self.projection) is Projection)
        c._digest(self.subject_digest)
        c._digest(self.receipt_digest)
        c._size(self)


@dataclass(frozen=True, slots=True)
class NoEffect:
    operation_id: str
    invocation: InvocationIdentity
    subject_digest: str
    receipt_digest: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._handle(self.operation_id)
        c._require(type(self.invocation) in {Invocation, OperatorInvocation})
        c._digest(self.subject_digest)
        c._digest(self.receipt_digest)


@dataclass(frozen=True, slots=True)
class Delivery:
    operation_id: str
    invocation: InvocationIdentity
    candidate_digest: str
    projection_digest: str
    pr_number: int
    merge_oid: str
    mapping: tuple[c.CommitPair, ...]
    receipt_digest: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._handle(self.operation_id)
        c._require(type(self.invocation) in {Invocation, OperatorInvocation})
        for value in (self.candidate_digest, self.projection_digest, self.receipt_digest):
            c._digest(value)
        c._integer(self.pr_number)
        c._oid(self.merge_oid)
        c._tuple(self.mapping, c.CommitPair, 1024, 1)
        c._oids(tuple(pair.original for pair in self.mapping), 1024, 1)
        c._oids(tuple(pair.landed for pair in self.mapping), 1024, 1)
        c._require(self.merge_oid == self.mapping[-1].landed
                   and all(len(pair.landed) == len(self.merge_oid) for pair in self.mapping), "delivery_interval")
        c._size(self)


class State(StrEnum):
    REQUESTED = "requested"  # Transient producer value; never persisted before admission.
    QUEUED = "queued"
    PREPARING = "preparing"
    QUALIFYING = "qualifying"
    AWAITING_OPERATOR = "awaiting_operator"
    MUTATION_UNCERTAIN = "mutation_uncertain"
    REPAIR_PENDING = "repair_pending"
    DELIVERED = "delivered"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


TERMINAL = frozenset({State.DELIVERED, State.REJECTED, State.SUPERSEDED})
ACTIVE = frozenset({State.PREPARING, State.QUALIFYING, State.AWAITING_OPERATOR, State.MUTATION_UNCERTAIN})


@dataclass(frozen=True, slots=True)
class Ticket:
    handle: str
    obligation_handle: str
    source: SourceSeries
    requester_digest: str
    predecessor: str | None = None
    state: State = State.REQUESTED
    sequence: int | None = None
    generation: int = 0
    base: str | None = None
    plan_digest: str | None = None
    projection: Projection | None = None
    candidate: Candidate | None = None
    qualification: c.Qualification | None = None
    reservation: NativeReservation | None = None
    delivery: Delivery | None = None
    failure_digest: str | None = None
    admission_digest: str | None = None
    repair_authorization_digest: str | None = None
    reconciliations: tuple[NoEffect, ...] = ()
    refresh_results: tuple[RefreshResult, ...] = ()
    delivery_mode: str = "ordinary"
    guarded_refresh: bool = False
    schema_version: int = 2

    @property
    def current_head(self) -> str:
        return self.projection.head if self.projection is not None else self.source.head

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._handle(self.handle)
        c._handle(self.obligation_handle)
        c._require(type(self.source) is SourceSeries and type(self.state) is State)
        c._digest(self.requester_digest)
        c._require(self.delivery_mode in {"ordinary", "admin"} and type(self.guarded_refresh) is bool,
                   "task_delivery_permission")
        if self.predecessor is not None:
            c._handle(self.predecessor)
            c._require(self.predecessor != self.handle, "revision_cycle")
        for value in (self.plan_digest, self.failure_digest, self.admission_digest, self.repair_authorization_digest):
            if value is not None:
                c._digest(value)
        c._integer(self.generation, 0)
        if self.sequence is not None:
            c._integer(self.sequence)
        if self.base is not None:
            c._oid(self.base)
            c._require(len(self.base) == len(self.source.head), "mixed_oid_formats")
        if self.projection is not None:
            _projection(self.source, self.projection)
        c._tuple(self.reconciliations, NoEffect, 512)
        c._tuple(self.refresh_results, RefreshResult, 512)
        operations = [proof.operation_id for proof in (*self.reconciliations, *self.refresh_results)]
        c._require(len(set(operations)) == len(operations), "operation_reused")
        for result in self.refresh_results:
            _projection(self.source, result.projection)
        if self.candidate is not None:
            c._require(type(self.candidate) is Candidate and self.projection is not None)
            assert self.projection is not None
            c._require(self.candidate.generation == self.generation
                       and self.candidate.source_digest == identity(self.source)
                       and self.candidate.projection_digest == identity(self.projection)
                       and self.candidate.head == self.projection.head
                       and self.candidate.base == self.base == self.projection.base
                       and self.candidate.plan_digest == self.plan_digest, "candidate_binding")
        if self.qualification is not None:
            c._require(type(self.qualification) is c.Qualification and self.candidate is not None)
            assert self.candidate is not None
            c._require(self.qualification.candidate_digest == identity(self.candidate)
                       and self.qualification.plan_digest == self.candidate.plan_digest
                       and self.qualification.policy_digest == self.candidate.policy_digest
                       and all(item.subject_oid in {self.candidate.head, self.candidate.tested_oid}
                               for item in self.qualification.evidence), "qualification_binding")
        if self.reservation is not None:
            c._require(type(self.reservation) is NativeReservation
                       and self.reservation.generation == self.generation
                       and self.reservation.expected_head == self.current_head
                       and self.reservation.expected_base == self.base
                       and self.reservation.operation_id not in operations, "reservation_binding")
            c._require(self.reservation.uncertain == (self.state == State.MUTATION_UNCERTAIN), "uncertain_binding")
            c._require(self.state in {State.PREPARING, State.QUALIFYING, State.MUTATION_UNCERTAIN})
            if self.reservation.kind == "merge":
                c._require(self.candidate is not None and self.qualification is not None
                           and self.reservation.subject_digest == identity(self.candidate), "merge_binding")
            else:
                c._require(self.candidate is None and self.qualification is None, "refresh_binding")
        if self.delivery is not None:
            c._require(type(self.delivery) is Delivery and self.candidate is not None
                       and self.qualification is not None and self.projection is not None)
            assert self.candidate is not None and self.projection is not None
            c._require(self.delivery.candidate_digest == identity(self.candidate)
                       and self.delivery.projection_digest == identity(self.projection)
                       and self.delivery.pr_number == self.source.pr_number
                       and tuple(pair.original for pair in self.delivery.mapping)
                       == tuple(pair.landed for pair in self.projection.mapping), "delivery_binding")
        c._require((self.delivery is not None) == (self.state == State.DELIVERED), "delivery_state")
        if self.state == State.REQUESTED:
            c._require(self.sequence is None and self.generation == 0 and self.base is None
                       and self.plan_digest is None and self.candidate is None and self.qualification is None
                       and self.reservation is None and self.admission_digest is None
                       and self.failure_digest is None and self.projection is None
                       and self.repair_authorization_digest is None and not operations, "unadmitted_state")
        else:
            c._require(self.sequence is not None and self.admission_digest is not None, "admitted_state")
        if self.state in ACTIVE:
            c._require(self.generation > 0 and self.base is not None and self.plan_digest is not None)
        if self.state == State.QUEUED:
            c._require(self.candidate is None and self.qualification is None and self.reservation is None)
        if self.state == State.PREPARING:
            c._require(self.candidate is None and self.qualification is None)
        if self.state == State.QUALIFYING:
            c._require(self.candidate is not None)
        if self.state == State.MUTATION_UNCERTAIN:
            c._require(self.reservation is not None)
        if self.state not in ACTIVE and self.state != State.DELIVERED:
            c._require(self.reservation is None and self.qualification is None)
        if self.state in {State.REPAIR_PENDING, State.REJECTED}:
            c._require(self.failure_digest is not None)
        c._size(self)


@dataclass(frozen=True, slots=True)
class Obligation:
    handle: str
    current_ticket: str
    grant_digest: str
    repair_count: int = 0
    revision_count: int = 1
    repair_owner: str | None = None
    archive_ticket: str | None = None
    archive_tip: str | None = None
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._handle(self.handle)
        c._handle(self.current_ticket)
        c._digest(self.grant_digest)
        c._integer(self.repair_count, 0)
        c._integer(self.revision_count)
        c._require(self.revision_count <= self.repair_count + 1, "repair_accounting")
        if self.repair_owner is not None:
            c._digest(self.repair_owner)
            c._require(self.repair_count > 0, "repair_accounting")
        c._require((self.archive_ticket is None) == (self.archive_tip is None), "archive_pointer")
        if self.archive_ticket is not None:
            c._handle(self.archive_ticket)
            c._digest(self.archive_tip)
        c._size(self)


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
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c.Target(self.repository, self.default_branch, self.root_oid, self.policy_digest,
                 self.generation, self.next_sequence, self.queue, self.active,
                 self.retained_count, self.last_operation)
        c._require(self.retained_count <= MAX_TICKETS, "ticket_count_limit")
        c._size(self, c.TARGET_LIMIT)


@dataclass(frozen=True, slots=True)
class Archive:
    ticket: Ticket
    previous_ticket: str | None = None
    previous_digest: str | None = None
    schema_version: int = 2

    def __post_init__(self) -> None:
        _version(self.schema_version)
        c._require(type(self.ticket) is Ticket and self.ticket.state in TERMINAL
                   and self.ticket.reservation is None, "archive_state")
        c._require((self.previous_ticket is None) == (self.previous_digest is None), "archive_pointer")
        if self.previous_ticket is not None:
            c._handle(self.previous_ticket)
            c._digest(self.previous_digest)
            c._require(self.previous_ticket != self.ticket.handle, "archive_cycle")
        c._size(self)


@dataclass(frozen=True, slots=True)
class _Action:
    kind: str
    args: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    target: Target
    tickets: tuple[Ticket, ...]
    obligations: tuple[Obligation, ...]
    archives: tuple[Archive, ...] = ()
    action: _Action | None = None

    def __post_init__(self) -> None:
        c._require(type(self.target) is Target)
        c._tuple(self.tickets, Ticket, MAX_TICKETS)
        c._tuple(self.obligations, Obligation, MAX_TICKETS + MAX_ARCHIVE_CONTEXT)
        c._tuple(self.archives, Archive, MAX_ARCHIVE_CONTEXT)
        ticket_index = {ticket.handle: ticket for ticket in self.tickets}
        obligations = {entry.handle: entry for entry in self.obligations}
        archive_index = {entry.ticket.handle: entry for entry in self.archives}
        c._require(len(ticket_index) == len(self.tickets) and len(obligations) == len(self.obligations)
                   and len(archive_index) == len(self.archives) and not ticket_index.keys() & archive_index.keys(),
                   "duplicate_runtime_identity")
        c._require(self.target.retained_count == len(self.tickets), "ticket_inventory")
        c._require(all(ticket.source.repository == self.target.repository
                       and ticket.state != State.REQUESTED and ticket.obligation_handle in obligations
                       for ticket in self.tickets), "runtime_binding")
        for ticket in self.tickets:
            obligation = obligations[ticket.obligation_handle]
            if ticket.state != State.SUPERSEDED:
                c._require(obligation.current_ticket == ticket.handle, "obligation_current")
        c._require(set(self.target.queue) == {ticket.handle for ticket in self.tickets if ticket.state == State.QUEUED},
                   "queue_inventory")
        c._require(all(handle in ticket_index for handle in self.target.queue), "queue_inventory")
        c._require(self.target.queue == tuple(ticket.handle for ticket in sorted(
            (value for value in self.tickets if value.state == State.QUEUED), key=lambda value: value.sequence or 0)),
            "fifo_inventory")
        for obligation in self.obligations:
            if obligation.repair_owner is not None:
                current = ticket_index.get(obligation.current_ticket)
                c._require(current is not None and current.state == State.REPAIR_PENDING, "repair_owner_binding")
        active = [ticket for ticket in self.tickets if ticket.state in ACTIVE]
        c._require(len(active) <= 1 and (active[0].handle if active else None) == self.target.active, "active_inventory")
        if active:
            current = active[0]
            c._require(current.generation == self.target.generation, "active_generation")
            if current.candidate is not None:
                c._require(current.candidate.policy_digest == self.target.policy_digest, "active_policy")
            if current.reservation is not None and current.reservation.kind == "refresh":
                c._require(current.reservation.subject_digest == _refresh_subject(current, self.target.policy_digest),
                           "refresh_subject")
        sequences = [ticket.sequence for ticket in self.tickets]
        c._require(len(set(sequences)) == len(sequences)
                   and all(value is not None and value < self.target.next_sequence for value in sequences), "sequence_inventory")
        current_prs = [ticket.source.pr_number for ticket in self.tickets if ticket.state not in TERMINAL]
        c._require(len(set(current_prs)) == len(current_prs), "duplicate_active_pr")
        if self.action is not None:
            c._require(type(self.action) is _Action, "runtime_action")

    def ticket(self, handle: str) -> Ticket:
        for ticket in self.tickets:
            if ticket.handle == handle:
                return ticket
        raise Conflict("ticket_missing")

    def lookup_ticket(self, handle: str) -> Ticket:
        for ticket in self.tickets:
            if ticket.handle == handle:
                return ticket
        for entry in self.archives:
            if entry.ticket.handle == handle:
                return entry.ticket
        raise Conflict("ticket_lookup_required")

    def obligation(self, handle: str) -> Obligation:
        for entry in self.obligations:
            if entry.handle == handle:
                return entry
        raise Conflict("obligation_missing")


def working_view(state: RuntimeSnapshot) -> RuntimeSnapshot:
    """Drop read-cache context only; never a persistence transition or deletion.

    Native readers fetch requested terminal indexes/archives directly at the same
    pinned tip. They need not load all lifetime obligations into working memory.
    """
    needed = {ticket.obligation_handle for ticket in state.tickets}
    return RuntimeSnapshot(state.target, state.tickets,
                           tuple(entry for entry in state.obligations if entry.handle in needed))


def _changed(state: RuntimeSnapshot, kind: str, args: tuple[object, ...], *,
             ticket: Ticket | None = None, target: Target | None = None,
             obligation: Obligation | None = None) -> RuntimeSnapshot:
    tickets = state.tickets
    if ticket is not None:
        tickets = tuple(ticket if value.handle == ticket.handle else value for value in tickets)
    obligations = state.obligations
    if obligation is not None:
        obligations = tuple(obligation if value.handle == obligation.handle else value for value in obligations)
    return RuntimeSnapshot(target or state.target, tickets, obligations, state.archives, _Action(kind, args))


def _admission(state: RuntimeSnapshot, ticket: Ticket, admission: c.Admission) -> None:
    if (type(admission) is not c.Admission or (admission.source_digest, admission.requester_digest, admission.policy_digest)
            != (identity(ticket.source), ticket.requester_digest, state.target.policy_digest)):
        raise Conflict("admission_binding")


def admit_authenticated(state: RuntimeSnapshot, ticket: Ticket, obligation: Obligation,
                        admission: c.Admission) -> RuntimeSnapshot:
    """One replayable request+admission CAS; an authenticated port supplies facts."""
    c._require(type(ticket) is Ticket and type(obligation) is Obligation)
    _admission(state, ticket, admission)
    if ticket.state != State.REQUESTED or ticket.predecessor is not None:
        raise Conflict("new_request_state")
    for value in (*state.tickets, *(entry.ticket for entry in state.archives)):
        if value.handle == ticket.handle:
            if (value.source, value.requester_digest, value.obligation_handle, value.delivery_mode, value.guarded_refresh) != (
                    ticket.source, ticket.requester_digest, ticket.obligation_handle, ticket.delivery_mode, ticket.guarded_refresh):
                raise Conflict("request_identity_changed")
            current = state.obligation(ticket.obligation_handle)
            if current.grant_digest != obligation.grant_digest:
                raise Conflict("grant_changed")
            return state
    if any(entry.handle == obligation.handle for entry in state.obligations):
        raise Conflict("obligation_exists_or_lookup_required")
    if (obligation.handle != ticket.obligation_handle or obligation.current_ticket != ticket.handle
            or obligation.repair_count != 0 or obligation.revision_count != 1
            or obligation.repair_owner is not None or obligation.archive_tip is not None):
        raise Conflict("obligation_binding")
    # Keep one working slot for a repair successor until its superseded
    # predecessor is archived. Roots cannot consume this recovery headroom.
    if len(state.tickets) >= MAX_TICKETS - 1 or len(state.target.queue) >= c.MAX_QUEUE:
        raise Conflict("working_capacity")
    admitted = replace(ticket, state=State.QUEUED, sequence=state.target.next_sequence,
                       admission_digest=admission.receipt_digest)
    target = replace(state.target, retained_count=state.target.retained_count + 1,
                     next_sequence=state.target.next_sequence + 1, queue=(*state.target.queue, ticket.handle))
    return RuntimeSnapshot(target, (*state.tickets, admitted), (*state.obligations, obligation),
                           state.archives, _Action("admit", (ticket, obligation, admission)))


def _active(state: RuntimeSnapshot, handle: str, generation: int) -> Ticket:
    c._integer(generation)
    ticket = state.ticket(handle)
    if state.target.active != handle or state.target.generation != generation or ticket.generation != generation:
        raise Conflict("stale_generation")
    return ticket


def _unreserved(ticket: Ticket) -> None:
    if ticket.reservation is not None:
        raise Conflict("mutation_unresolved")


def claim(state: RuntimeSnapshot, handle: str, base: str, plan_digest: str) -> RuntimeSnapshot:
    ticket = state.ticket(handle)
    if state.target.active is not None or not state.target.queue or state.target.queue[0] != handle or ticket.state != State.QUEUED:
        raise Conflict("claim_binding")
    generation = state.target.generation + 1
    return _changed(state, "claim", (handle, base, plan_digest),
        ticket=replace(ticket, state=State.PREPARING, generation=generation, base=base,
                       plan_digest=plan_digest, candidate=None, qualification=None),
        target=replace(state.target, generation=generation, active=handle, queue=state.target.queue[1:]))


def bind_projection(state: RuntimeSnapshot, handle: str, generation: int, projection: Projection) -> RuntimeSnapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    _projection(ticket.source, projection)
    if ticket.state != State.PREPARING or projection.head != ticket.current_head or projection.base != ticket.base:
        raise Conflict("projection_requires_refresh")
    return _changed(state, "bind_projection", (handle, generation, projection), ticket=replace(ticket, projection=projection))


def bind_candidate(state: RuntimeSnapshot, handle: str, generation: int, candidate: Candidate) -> RuntimeSnapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    if (ticket.state not in {State.PREPARING, State.AWAITING_OPERATOR} or ticket.projection is None
            or candidate.generation != generation or candidate.source_digest != identity(ticket.source)
            or candidate.projection_digest != identity(ticket.projection) or candidate.head != ticket.current_head
            or candidate.base != ticket.base or candidate.policy_digest != state.target.policy_digest):
        raise Conflict("candidate_binding")
    return _changed(state, "bind_candidate", (handle, generation, candidate),
                    ticket=replace(ticket, state=State.QUALIFYING, candidate=candidate, plan_digest=candidate.plan_digest))


@dataclass(frozen=True, slots=True)
class _RefreshSubject:
    source_digest: str
    projection_digest: str | None
    head: str
    base: str | None
    plan_digest: str | None
    policy_digest: str
    generation: int


def _refresh_subject(ticket: Ticket, policy_digest: str) -> str:
    return identity(_RefreshSubject(identity(ticket.source), identity(ticket.projection) if ticket.projection else None,
                                    ticket.current_head, ticket.base, ticket.plan_digest, policy_digest, ticket.generation))


def _outcome_capacity(ticket: Ticket) -> None:
    """Reserve headroom for all effect/reconciliation envelopes before a call."""
    body = asdict(ticket)
    pairs = [{"original": entry.oid, "landed": "f" * len(entry.oid)} for entry in ticket.source.entries]
    projection = {"schema_version": 2, "source_digest": identity(ticket.source), "base": ticket.base,
                  "head": "f" * len(ticket.source.head), "mapping": pairs, "receipt_digest": "f" * 64}
    assert ticket.reservation is not None
    refresh = {"schema_version": 2, "operation_id": ticket.reservation.operation_id,
               "invocation": asdict(ticket.reservation.invocation), "subject_digest": ticket.reservation.subject_digest,
               "projection": projection, "receipt_digest": "f" * 64}
    no_effect = {key: value for key, value in refresh.items() if key != "projection"}
    delivery = {"schema_version": 2, "operation_id": ticket.reservation.operation_id,
                "invocation": asdict(ticket.reservation.invocation), "candidate_digest": "f" * 64,
                "projection_digest": "f" * 64, "pr_number": ticket.source.pr_number,
                "merge_oid": "f" * len(ticket.source.head), "mapping": pairs, "receipt_digest": "f" * 64}
    possibilities = [{**body, "reconciliations": [*body["reconciliations"], no_effect]},
                     {**body, "projection": projection, "refresh_results": [*body["refresh_results"], refresh]},
                     {**body, "delivery": delivery}]
    if any(len(c._canonical(value)) > c.RECORD_LIMIT for value in possibilities):
        raise Conflict("outcome_capacity")


def reserve_native(state: RuntimeSnapshot, handle: str, generation: int, kind: str, operation_id: str,
                   invocation: InvocationIdentity, *, qualification: c.Qualification | None = None,
                   retention_digest: str | None = None) -> RuntimeSnapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    if any(value.operation_id == operation_id for value in (*ticket.reconciliations, *ticket.refresh_results)):
        raise Conflict("operation_id_reused")
    if len(ticket.reconciliations) >= 512 or len(ticket.refresh_results) >= 512:
        raise Conflict("native_history_capacity")
    if kind == "refresh":
        if (ticket.state != State.PREPARING or qualification is not None or retention_digest is None
                or not ticket.guarded_refresh):
            raise Conflict("refresh_binding")
        subject = _refresh_subject(ticket, state.target.policy_digest)
    elif kind == "merge":
        if ticket.state not in {State.QUALIFYING, State.AWAITING_OPERATOR} or ticket.candidate is None or qualification is None:
            raise Conflict("merge_binding")
        if (qualification.candidate_digest != identity(ticket.candidate) or qualification.plan_digest != ticket.plan_digest
                or qualification.policy_digest != state.target.policy_digest):
            raise Conflict("qualification_stale")
        subject = identity(ticket.candidate)
    else:
        raise Invalid("mutation_kind")
    assert ticket.base is not None
    reservation = NativeReservation(kind, operation_id, invocation, generation, subject, ticket.current_head,
                                    ticket.base, retention_digest)
    updated = replace(ticket, qualification=qualification, reservation=reservation,
                      state=State.PREPARING if kind == "refresh" else State.QUALIFYING)
    _outcome_capacity(updated)
    return _changed(state, "reserve_native", (handle, generation, kind, operation_id, invocation, qualification, retention_digest),
                    ticket=updated)


def mark_uncertain(state: RuntimeSnapshot, handle: str, generation: int, operation_id: str) -> RuntimeSnapshot:
    ticket = _active(state, handle, generation)
    if ticket.reservation is None or ticket.reservation.operation_id != operation_id:
        raise Conflict("reservation_binding")
    return _changed(state, "uncertain", (handle, generation, operation_id),
                    ticket=replace(ticket, state=State.MUTATION_UNCERTAIN, reservation=replace(ticket.reservation, uncertain=True)))


def _reserved(state: RuntimeSnapshot, handle: str, generation: int, operation_id: str,
              invocation: InvocationIdentity, subject: str) -> tuple[Ticket, NativeReservation]:
    ticket = _active(state, handle, generation)
    reservation = ticket.reservation
    if reservation is None or (reservation.operation_id, reservation.invocation, reservation.subject_digest) != (
            operation_id, invocation, subject):
        raise Conflict("reconciliation_binding")
    return ticket, reservation


def resolve_no_effect(state: RuntimeSnapshot, handle: str, generation: int, proof: NoEffect) -> RuntimeSnapshot:
    c._require(type(proof) is NoEffect)
    ticket, reservation = _reserved(state, handle, generation, proof.operation_id, proof.invocation, proof.subject_digest)
    return _changed(state, "no_effect", (handle, generation, proof), ticket=replace(ticket,
        state=State.PREPARING if reservation.kind == "refresh" else State.QUALIFYING,
        reservation=None, qualification=None, reconciliations=(*ticket.reconciliations, proof)))


def record_rejection(state: RuntimeSnapshot, handle: str, generation: int, proof: NoEffect) -> RuntimeSnapshot:
    """Atomically retain definite no-effect proof and release to a stable blocker.

    No replayable intermediate state may clear the reservation while allowing an
    unchanged rejected operation to be attempted again after a worker crash.
    """
    resolved = resolve_no_effect(state, handle, generation, proof)
    failed = record_failure(resolved, handle, generation, proof.receipt_digest)
    return replace(failed, action=_Action("native_rejected", (handle, generation, proof)))


def reprepare_no_effect(state: RuntimeSnapshot, handle: str, generation: int, proof: NoEffect,
                       base: str, plan_digest: str) -> RuntimeSnapshot:
    """Resolve a definite rejection and invalidate newly observed inputs in one CAS."""
    resolved = resolve_no_effect(state, handle, generation, proof)
    prepared = invalidate(resolved, handle, generation, base, plan_digest)
    return replace(prepared, action=_Action("no_effect_reprepare", (handle, generation, proof, base, plan_digest)))


def record_projection(state: RuntimeSnapshot, handle: str, generation: int, proof: RefreshResult) -> RuntimeSnapshot:
    c._require(type(proof) is RefreshResult)
    ticket, reservation = _reserved(state, handle, generation, proof.operation_id, proof.invocation, proof.subject_digest)
    if reservation.kind != "refresh":
        raise Conflict("refresh_binding")
    _projection(ticket.source, proof.projection)
    next_generation = state.target.generation + 1
    return _changed(state, "projection", (handle, generation, proof), ticket=replace(ticket, state=State.PREPARING,
        generation=next_generation, base=proof.projection.base, projection=proof.projection,
        candidate=None, qualification=None, reservation=None, refresh_results=(*ticket.refresh_results, proof)),
        target=replace(state.target, generation=next_generation))


def invalidate(state: RuntimeSnapshot, handle: str, generation: int, base: str, plan_digest: str) -> RuntimeSnapshot:
    """Reprepare changed approved inputs without releasing the logical slot.

    Enrollment/policy authority is unchanged. Unknown policy drift is an adapter
    blocker, never an instruction to manufacture a new grant or accept new rules.
    """
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    next_generation = state.target.generation + 1
    return _changed(state, "invalidate", (handle, generation, base, plan_digest),
        ticket=replace(ticket, state=State.PREPARING, generation=next_generation, base=base,
                       plan_digest=plan_digest, candidate=None, qualification=None),
        target=replace(state.target, generation=next_generation))


def record_failure(state: RuntimeSnapshot, handle: str, generation: int, failure_digest: str) -> RuntimeSnapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    return _changed(state, "failure", (handle, generation, failure_digest),
        ticket=replace(ticket, state=State.REPAIR_PENDING, qualification=None, failure_digest=failure_digest),
        target=replace(state.target, active=None))


def wait_for_operator(state: RuntimeSnapshot, handle: str, generation: int) -> RuntimeSnapshot:
    ticket = _active(state, handle, generation)
    _unreserved(ticket)
    return _changed(state, "operator", (handle, generation),
                    ticket=replace(ticket, state=State.AWAITING_OPERATOR, qualification=None))


def record_delivery(state: RuntimeSnapshot, handle: str, generation: int, proof: Delivery) -> RuntimeSnapshot:
    c._require(type(proof) is Delivery)
    ticket, reservation = _reserved(state, handle, generation, proof.operation_id, proof.invocation, proof.candidate_digest)
    if reservation.kind != "merge":
        raise Conflict("merge_binding")
    return _changed(state, "delivery", (handle, generation, proof),
                    ticket=replace(ticket, state=State.DELIVERED, delivery=proof, reservation=None),
                    target=replace(state.target, active=None))


def original_to_landed(ticket: Ticket) -> tuple[c.CommitPair, ...]:
    if ticket.delivery is None or ticket.projection is None:
        raise Conflict("delivery_missing")
    return tuple(c.CommitPair(before.original, after.landed)
                 for before, after in zip(ticket.projection.mapping, ticket.delivery.mapping, strict=True))


def park_queued(state: RuntimeSnapshot, handle: str, failure_digest: str) -> RuntimeSnapshot:
    """Retain an admitted source/obligation without claiming or holding the slot."""
    ticket = state.ticket(handle)
    if ticket.state != State.QUEUED:
        raise Conflict("parking_state")
    _unreserved(ticket)
    return _changed(state, "park_queued", (handle, failure_digest),
        ticket=replace(ticket, state=State.REPAIR_PENDING, failure_digest=failure_digest),
        target=replace(state.target, queue=tuple(value for value in state.target.queue if value != handle)))


def reject_queued(state: RuntimeSnapshot, handle: str, failure_digest: str) -> RuntimeSnapshot:
    ticket = state.ticket(handle)
    if ticket.state != State.QUEUED:
        raise Conflict("rejection_state")
    return _changed(state, "reject", (handle, failure_digest),
                    ticket=replace(ticket, state=State.REJECTED, failure_digest=failure_digest),
                    target=replace(state.target, queue=tuple(value for value in state.target.queue if value != handle)))


def reserve_repair(state: RuntimeSnapshot, obligation_handle: str, expected_current_ticket: str,
                   authorization_digest: str) -> RuntimeSnapshot:
    c._digest(authorization_digest)
    obligation = state.obligation(obligation_handle)
    if obligation.current_ticket != expected_current_ticket or state.ticket(expected_current_ticket).state != State.REPAIR_PENDING:
        raise Conflict("repair_predecessor")
    if obligation.repair_owner is not None:
        if obligation.repair_owner == authorization_digest:
            return state
        raise Conflict("repair_owner_exists")
    return _changed(state, "repair_owner", (obligation_handle, expected_current_ticket, authorization_digest),
        obligation=replace(obligation, repair_owner=authorization_digest, repair_count=obligation.repair_count + 1))


def supersede(state: RuntimeSnapshot, obligation_handle: str, expected_current_ticket: str, replacement: Ticket,
              admission: c.Admission, authorization_digest: str) -> RuntimeSnapshot:
    obligation = state.obligation(obligation_handle)
    _admission(state, replacement, admission)
    if obligation.current_ticket != expected_current_ticket:
        current = state.lookup_ticket(obligation.current_ticket)
        if (current.handle == replacement.handle and current.predecessor == expected_current_ticket
                and current.source == replacement.source and current.requester_digest == replacement.requester_digest
                and current.repair_authorization_digest == authorization_digest
                and current.delivery_mode == replacement.delivery_mode and current.guarded_refresh == replacement.guarded_refresh):
            return state
        raise Conflict("repair_predecessor")
    old = state.ticket(expected_current_ticket)
    if (old.state != State.REPAIR_PENDING or obligation.repair_owner != authorization_digest
            or replacement.state != State.REQUESTED or replacement.predecessor != old.handle
            or replacement.obligation_handle != obligation.handle
            or replacement.source.repository != old.source.repository or replacement.source.pr_number != old.source.pr_number
            or replacement.requester_digest != old.requester_digest
            or replacement.delivery_mode != old.delivery_mode or replacement.guarded_refresh != old.guarded_refresh
            or any(value.handle == replacement.handle for value in state.tickets)
            or any(value.ticket.handle == replacement.handle for value in state.archives)):
        raise Conflict("supersession_binding")
    if len(state.tickets) >= MAX_TICKETS or len(state.target.queue) >= c.MAX_QUEUE:
        raise Conflict("working_capacity")
    successor = replace(replacement, state=State.QUEUED, sequence=state.target.next_sequence,
                        admission_digest=admission.receipt_digest, repair_authorization_digest=authorization_digest)
    retired = replace(old, state=State.SUPERSEDED)
    tickets = tuple(retired if value.handle == old.handle else value for value in state.tickets)
    next_obligation = replace(obligation, current_ticket=successor.handle, repair_owner=None,
                              revision_count=obligation.revision_count + 1)
    return RuntimeSnapshot(replace(state.target, queue=(*state.target.queue, successor.handle),
        next_sequence=state.target.next_sequence + 1, retained_count=state.target.retained_count + 1),
        (*tickets, successor), tuple(next_obligation if value.handle == obligation.handle else value for value in state.obligations),
        state.archives, _Action("supersede", (obligation_handle, expected_current_ticket, replacement, admission, authorization_digest)))


def archive(state: RuntimeSnapshot, handle: str) -> RuntimeSnapshot:
    try:
        ticket = state.ticket(handle)
    except Conflict:
        state.lookup_ticket(handle)  # A pinned native lookup is required for idempotence.
        return state
    if ticket.state not in TERMINAL or ticket.reservation is not None or state.target.active == handle or handle in state.target.queue:
        raise Conflict("archive_state")
    if len(state.archives) >= MAX_ARCHIVE_CONTEXT:
        raise Conflict("archive_context_full")
    obligation = state.obligation(ticket.obligation_handle)
    entry = Archive(ticket, obligation.archive_ticket, obligation.archive_tip)
    next_obligation = replace(obligation, archive_ticket=handle, archive_tip=identity(entry))
    return RuntimeSnapshot(replace(state.target, retained_count=state.target.retained_count - 1),
        tuple(value for value in state.tickets if value.handle != handle),
        tuple(next_obligation if value.handle == obligation.handle else value for value in state.obligations),
        (*state.archives, entry), _Action("archive", (handle,)))


def _argument[T](args: tuple[object, ...], index: int, cls: type[T]) -> T:
    value = args[index]
    if type(value) is not cls:
        raise Conflict("transition_shape")
    assert isinstance(value, cls)
    return value


def _optional_argument[T](args: tuple[object, ...], index: int, cls: type[T]) -> T | None:
    return None if args[index] is None else _argument(args, index, cls)


def _invocation_argument(args: tuple[object, ...], index: int) -> InvocationIdentity:
    value = args[index]
    if isinstance(value, (Invocation, OperatorInvocation)):
        return value
    raise Conflict("transition_shape")


def _replay(before: RuntimeSnapshot, action: _Action) -> RuntimeSnapshot:
    a = action.args
    kind = action.kind
    if kind == "admit":
        c._require(len(a) == 3, "transition_shape")
        return admit_authenticated(before, _argument(a, 0, Ticket), _argument(a, 1, Obligation), _argument(a, 2, c.Admission))
    if kind == "claim":
        c._require(len(a) == 3, "transition_shape")
        return claim(before, _argument(a, 0, str), _argument(a, 1, str), _argument(a, 2, str))
    if kind == "bind_projection":
        c._require(len(a) == 3, "transition_shape")
        return bind_projection(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, Projection))
    if kind == "bind_candidate":
        c._require(len(a) == 3, "transition_shape")
        return bind_candidate(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, Candidate))
    if kind == "reserve_native":
        c._require(len(a) == 7, "transition_shape")
        return reserve_native(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, str),
            _argument(a, 3, str), _invocation_argument(a, 4), qualification=_optional_argument(a, 5, c.Qualification),
            retention_digest=_optional_argument(a, 6, str))
    if kind == "uncertain":
        c._require(len(a) == 3, "transition_shape")
        return mark_uncertain(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, str))
    if kind == "no_effect":
        c._require(len(a) == 3, "transition_shape")
        return resolve_no_effect(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, NoEffect))
    if kind == "native_rejected":
        c._require(len(a) == 3, "transition_shape")
        return record_rejection(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, NoEffect))
    if kind == "no_effect_reprepare":
        c._require(len(a) == 5, "transition_shape")
        return reprepare_no_effect(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, NoEffect),
                                   _argument(a, 3, str), _argument(a, 4, str))
    if kind == "projection":
        c._require(len(a) == 3, "transition_shape")
        return record_projection(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, RefreshResult))
    if kind == "invalidate":
        c._require(len(a) == 4, "transition_shape")
        return invalidate(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, str), _argument(a, 3, str))
    if kind == "failure":
        c._require(len(a) == 3, "transition_shape")
        return record_failure(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, str))
    if kind == "operator":
        c._require(len(a) == 2, "transition_shape")
        return wait_for_operator(before, _argument(a, 0, str), _argument(a, 1, int))
    if kind == "delivery":
        c._require(len(a) == 3, "transition_shape")
        return record_delivery(before, _argument(a, 0, str), _argument(a, 1, int), _argument(a, 2, Delivery))
    if kind == "park_queued":
        c._require(len(a) == 2, "transition_shape")
        return park_queued(before, _argument(a, 0, str), _argument(a, 1, str))
    if kind == "reject":
        c._require(len(a) == 2, "transition_shape")
        return reject_queued(before, _argument(a, 0, str), _argument(a, 1, str))
    if kind == "repair_owner":
        c._require(len(a) == 3, "transition_shape")
        return reserve_repair(before, _argument(a, 0, str), _argument(a, 1, str), _argument(a, 2, str))
    if kind == "supersede":
        c._require(len(a) == 5, "transition_shape")
        return supersede(before, _argument(a, 0, str), _argument(a, 1, str), _argument(a, 2, Ticket),
                         _argument(a, 3, c.Admission), _argument(a, 4, str))
    if kind == "archive":
        c._require(len(a) == 1, "transition_shape")
        return archive(before, _argument(a, 0, str))
    raise Conflict("transition_unsupported")


Record: TypeAlias = SourceSeries | Projection | Candidate | Ticket | Target | Obligation | Archive
RECORDS = (SourceSeries, Projection, Candidate, Ticket, Target, Obligation, Archive)


def encode(value: Record) -> bytes:
    c._require(type(value) in RECORDS, "record_type")
    raw = c._canonical(asdict(value))
    c._require(len(raw) <= (c.TARGET_LIMIT if type(value) is Target else c.RECORD_LIMIT), "record_size_limit")
    return raw


@dataclass(frozen=True, slots=True)
class AppendRequest:
    expected_head: str
    control_branch: str
    operation_id: str
    state: RuntimeSnapshot
    before: RuntimeSnapshot

    def __post_init__(self) -> None:
        c._oid(self.expected_head)
        c._branch(self.control_branch)
        c._handle(self.operation_id)
        if (self.control_branch in {self.state.target.default_branch, "main", "master"}
                or len(self.expected_head) != len(self.before.target.root_oid)
                or self.operation_id == self.before.target.last_operation
                or self.state.target.last_operation != self.operation_id):
            raise Conflict("append_binding")
        for name in ("repository", "default_branch", "root_oid", "policy_digest"):
            if getattr(self.before.target, name) != getattr(self.state.target, name):
                raise Conflict("target_authority_changed")
        if self.state.action is None:
            raise Conflict("transition_required")
        proposed = replace(self.state, target=replace(self.state.target, last_operation=self.before.target.last_operation))
        try:
            replayed = _replay(self.before, self.state.action)
        except (TypeError, IndexError, AttributeError):
            raise Conflict("transition_shape") from None
        if replayed != proposed:
            raise Conflict("transition_changed")

    @property
    def parents(self) -> tuple[str, ...]:
        heads: tuple[str, ...] = ()
        for ticket in self.state.tickets:
            old = next((value for value in self.before.tickets if value.handle == ticket.handle), None)
            if ticket.reservation is not None and (
                    old is None or old.reservation is None):
                heads = tuple(dict.fromkeys((ticket.source.head, ticket.current_head)))
        c._require(self.expected_head not in heads and all(len(head) == len(self.expected_head) for head in heads), "retention_parents")
        return (self.expected_head, *heads)

    @property
    def additions(self) -> tuple[tuple[str, str], ...]:
        updates: list[tuple[str, Record]] = [("integration/v2/target.json", self.state.target)]
        previous_tickets = {value.handle: value for value in self.before.tickets}
        previous_obligations = {value.handle: value for value in self.before.obligations}
        previous_archives = {value.ticket.handle: value for value in self.before.archives}
        updates.extend((f"integration/v2/tickets/{value.handle}.json", value) for value in self.state.tickets
                       if previous_tickets.get(value.handle) != value)
        updates.extend((f"integration/v2/obligations/{value.handle}.json", value) for value in self.state.obligations
                       if previous_obligations.get(value.handle) != value)
        updates.extend((f"integration/v2/archive/tickets/{value.ticket.handle}.json", value) for value in self.state.archives
                       if previous_archives.get(value.ticket.handle) != value)
        return tuple((path, base64.b64encode(encode(value)).decode("ascii")) for path, value in updates)

    @property
    def deletions(self) -> tuple[str, ...]:
        current = {value.handle for value in self.state.tickets}
        return tuple(f"integration/v2/tickets/{value.handle}.json" for value in self.before.tickets if value.handle not in current)

    def graphql(self) -> dict[str, object]:
        if len(self.parents) != 1:
            raise Unavailable("retention_requires_native_git_data")
        return {"branch": {"repositoryNameWithOwner": self.state.target.repository, "branchName": self.control_branch},
                "expectedHeadOid": self.expected_head, "message": {"headline": "chore(integration): append state"},
                "fileChanges": {"additions": [{"path": path, "contents": content} for path, content in self.additions],
                                "deletions": [{"path": path} for path in self.deletions]},
                "clientMutationId": self.operation_id}


def build_append(before: RuntimeSnapshot, after: RuntimeSnapshot, expected_head: str,
                 control_branch: str, operation_id: str) -> AppendRequest:
    if before.target.last_operation != after.target.last_operation:
        raise Conflict("append_history_changed")
    return AppendRequest(expected_head, control_branch, operation_id,
                         replace(after, target=replace(after.target, last_operation=operation_id)), before)


# Closed recursive codecs. No class name, callable or path is loaded from JSON.
def _obj(value: object, cls: type) -> dict[str, object]:
    if not is_dataclass(cls):
        raise Invalid("record_type")
    return c._object(value, " ".join(field.name for field in fields(cls)))


def _array(value: object) -> tuple[object, ...]:
    c._require(type(value) is list, "record_array")
    assert isinstance(value, list)
    return tuple(value)


def _entry(value: object) -> SourceEntry:
    v = _obj(value, SourceEntry)
    return SourceEntry(c._text(v["oid"]), c._text(v["kind"]), tuple(c._text(item) for item in _array(v["gates"])))


def _pairs(value: object) -> tuple[c.CommitPair, ...]:
    result = []
    for item in _array(value):
        pair = c._object(item, "original landed")
        result.append(c.CommitPair(c._text(pair["original"]), c._text(pair["landed"])))
    return tuple(result)


def _source(value: object) -> SourceSeries:
    v = _obj(value, SourceSeries)
    return SourceSeries(c._text(v["repository"]), c._int(v["pr_number"]), c._text(v["base"]), c._text(v["head"]),
                        tuple(_entry(item) for item in _array(v["entries"])), c._text(v["authority_digest"]), c._int(v["schema_version"]))


def _projection_record(value: object) -> Projection:
    v = _obj(value, Projection)
    return Projection(c._text(v["source_digest"]), c._text(v["base"]), c._text(v["head"]), _pairs(v["mapping"]),
                      c._text(v["receipt_digest"]), c._int(v["schema_version"]))


def _candidate(value: object) -> Candidate:
    v = _obj(value, Candidate)
    return Candidate(c._int(v["generation"]), c._text(v["source_digest"]), c._text(v["projection_digest"]),
                     c._text(v["head"]), c._text(v["base"]), c._text(v["tested_oid"]),
                     tuple(c._text(item) for item in _array(v["tested_parents"])), c._text(v["tree"]),
                     c._text(v["plan_digest"]), c._text(v["policy_digest"]), c._int(v["schema_version"]))


def _invocation(value: object) -> InvocationIdentity:
    if isinstance(value, dict) and value.get("kind") == "operator":
        v = _obj(value, OperatorInvocation)
        return OperatorInvocation(c._int(v["requester_id"]), c._text(v["invocation_id"]),
            c._text(v["custody_digest"]), c._text(v["scope_digest"]), c._text(v["kind"]), c._int(v["schema_version"]))
    v = _obj(value, Invocation)
    return Invocation(c._int(v["run_id"]), c._int(v["attempt"]), c._text(v["invocation_id"]), c._text(v["workflow_digest"]))


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise Invalid("record_boolean")
    return value


def _reservation(value: object) -> NativeReservation:
    v = _obj(value, NativeReservation)
    return NativeReservation(c._text(v["kind"]), c._text(v["operation_id"]), _invocation(v["invocation"]), c._int(v["generation"]),
        c._text(v["subject_digest"]), c._text(v["expected_head"]), c._text(v["expected_base"]),
        None if v["retention_digest"] is None else c._text(v["retention_digest"]), _boolean(v["uncertain"]), c._int(v["schema_version"]))


def _no_effect(value: object) -> NoEffect:
    v = _obj(value, NoEffect)
    return NoEffect(c._text(v["operation_id"]), _invocation(v["invocation"]), c._text(v["subject_digest"]),
                    c._text(v["receipt_digest"]), c._int(v["schema_version"]))


def _refresh(value: object) -> RefreshResult:
    v = _obj(value, RefreshResult)
    return RefreshResult(c._text(v["operation_id"]), _invocation(v["invocation"]), c._text(v["subject_digest"]),
                         _projection_record(v["projection"]), c._text(v["receipt_digest"]), c._int(v["schema_version"]))


def _delivery(value: object) -> Delivery:
    v = _obj(value, Delivery)
    return Delivery(c._text(v["operation_id"]), _invocation(v["invocation"]), c._text(v["candidate_digest"]),
                    c._text(v["projection_digest"]), c._int(v["pr_number"]), c._text(v["merge_oid"]),
                    _pairs(v["mapping"]), c._text(v["receipt_digest"]), c._int(v["schema_version"]))


def _ticket(value: object) -> Ticket:
    v = _obj(value, Ticket)
    return Ticket(c._text(v["handle"]), c._text(v["obligation_handle"]), _source(v["source"]), c._text(v["requester_digest"]),
        None if v["predecessor"] is None else c._text(v["predecessor"]), State(c._text(v["state"])),
        None if v["sequence"] is None else c._int(v["sequence"]), c._int(v["generation"]),
        None if v["base"] is None else c._text(v["base"]), None if v["plan_digest"] is None else c._text(v["plan_digest"]),
        None if v["projection"] is None else _projection_record(v["projection"]),
        None if v["candidate"] is None else _candidate(v["candidate"]),
        None if v["qualification"] is None else c._qualification(v["qualification"]),
        None if v["reservation"] is None else _reservation(v["reservation"]),
        None if v["delivery"] is None else _delivery(v["delivery"]),
        None if v["failure_digest"] is None else c._text(v["failure_digest"]),
        None if v["admission_digest"] is None else c._text(v["admission_digest"]),
        None if v["repair_authorization_digest"] is None else c._text(v["repair_authorization_digest"]),
        tuple(_no_effect(item) for item in _array(v["reconciliations"])),
        tuple(_refresh(item) for item in _array(v["refresh_results"])), c._text(v["delivery_mode"]),
        _boolean(v["guarded_refresh"]), c._int(v["schema_version"]))


def _target(value: object) -> Target:
    v = _obj(value, Target)
    return Target(c._text(v["repository"]), c._text(v["default_branch"]), c._text(v["root_oid"]), c._text(v["policy_digest"]),
        c._int(v["generation"]), c._int(v["next_sequence"]), tuple(c._text(item) for item in _array(v["queue"])),
        None if v["active"] is None else c._text(v["active"]), c._int(v["retained_count"]),
        None if v["last_operation"] is None else c._text(v["last_operation"]), c._int(v["schema_version"]))


def _obligation(value: object) -> Obligation:
    v = _obj(value, Obligation)
    return Obligation(c._text(v["handle"]), c._text(v["current_ticket"]), c._text(v["grant_digest"]),
        c._int(v["repair_count"]), c._int(v["revision_count"]), None if v["repair_owner"] is None else c._text(v["repair_owner"]),
        None if v["archive_ticket"] is None else c._text(v["archive_ticket"]),
        None if v["archive_tip"] is None else c._text(v["archive_tip"]), c._int(v["schema_version"]))


def _archive(value: object) -> Archive:
    v = _obj(value, Archive)
    return Archive(_ticket(v["ticket"]), None if v["previous_ticket"] is None else c._text(v["previous_ticket"]),
                   None if v["previous_digest"] is None else c._text(v["previous_digest"]), c._int(v["schema_version"]))


def decode(kind: str, raw: bytes) -> Record:
    decoders = {"source": _source, "projection": _projection_record, "candidate": _candidate, "ticket": _ticket,
                "target": _target, "obligation": _obligation, "archive": _archive}
    if kind not in decoders or type(raw) is not bytes or len(raw) > (c.TARGET_LIMIT if kind == "target" else c.RECORD_LIMIT):
        raise Invalid("record_boundary")
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in items:
            if key in result:
                raise Invalid("duplicate_json_key")
            result[key] = item
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(Invalid("invalid_json_number")))
        return decoders[kind](value)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        if isinstance(error, Invalid):
            raise
        raise Invalid("invalid_record") from None


def load_snapshot(records: Mapping[str, bytes]) -> RuntimeSnapshot:
    """Decode a bounded pinned-tip working view and explicitly requested history.

    The native reader owns repository/root/rules and same-tip proof. It must load
    all working tickets, their obligation indexes, plus bounded requested terminal
    context. It must not enumerate every lifetime archive on ordinary advancement.
    Other enrollment data is validated separately and is not passed to this codec.
    """
    if not isinstance(records, Mapping) or "integration/v2/target.json" not in records:
        raise Invalid("target_missing")
    target: Target | None = None
    tickets: list[Ticket] = []
    obligations: list[Obligation] = []
    archives: list[Archive] = []
    if len(records) > MAX_TICKETS * 2 + MAX_ARCHIVE_CONTEXT * 2 + 1:
        raise Invalid("view_count_limit")
    for path, raw in records.items():
        if type(path) is not str or type(raw) is not bytes:
            raise Invalid("record_boundary")
        if path == "integration/v2/target.json":
            value = decode("target", raw)
            assert isinstance(value, Target)
            target = value
        elif path.startswith("integration/v2/tickets/"):
            value = decode("ticket", raw)
            assert isinstance(value, Ticket)
            if path != f"integration/v2/tickets/{value.handle}.json":
                raise Invalid("ticket_path_identity")
            tickets.append(value)
        elif path.startswith("integration/v2/obligations/"):
            value = decode("obligation", raw)
            assert isinstance(value, Obligation)
            if path != f"integration/v2/obligations/{value.handle}.json":
                raise Invalid("obligation_path_identity")
            obligations.append(value)
        elif path.startswith("integration/v2/archive/tickets/"):
            value = decode("archive", raw)
            assert isinstance(value, Archive)
            if path != f"integration/v2/archive/tickets/{value.ticket.handle}.json":
                raise Invalid("archive_path_identity")
            archives.append(value)
        else:
            raise Invalid("unknown_ledger_path")
    assert target is not None
    view = RuntimeSnapshot(target, tuple(tickets), tuple(obligations), tuple(archives))
    for entry in view.archives:
        obligation = view.obligation(entry.ticket.obligation_handle)
        if entry.ticket.handle == obligation.archive_ticket and identity(entry) != obligation.archive_tip:
            raise Invalid("archive_digest")
        previous = next((item for item in view.archives if item.ticket.handle == entry.previous_ticket), None)
        if previous is not None and (identity(previous) != entry.previous_digest
                                     or previous.ticket.obligation_handle != entry.ticket.obligation_handle):
            raise Invalid("archive_link")
    for obligation in view.obligations:
        try:
            current = view.lookup_ticket(obligation.current_ticket)
        except Conflict:
            raise Invalid("current_ticket_missing") from None
        if current.obligation_handle != obligation.handle or current.state == State.SUPERSEDED:
            raise Invalid("obligation_current")
    return view
