"""Guarded ordinary Forgejo v15 merges for a caller-qualified native path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from . import core as c
from . import forgejo
from . import forgejo_ci as ci
from . import runtime as r


@dataclass(frozen=True, slots=True, repr=False)
class MergeTarget:
    binding: forgejo.Binding
    target_ref: str
    actor_id: int
    guard_digest: str
    dispatcher_digest: str


@dataclass(frozen=True, slots=True, repr=False)
class MergeIntent:
    target: MergeTarget
    subject: ci.Subject
    source_ref: str
    projection: r.Projection
    pull_request_id: int


@dataclass(frozen=True, slots=True, repr=False)
class GuardGrant:
    repository_id: int
    ref: str
    base: str
    head: str
    tested_tree: str
    actor_id: int
    pull_request_id: int
    expires_at: int
    synthetic: bool = True
    schema_version: int = 1


@dataclass(frozen=True, slots=True, repr=False)
class MergePreconditions:
    target: MergeTarget
    policy_digest: str
    reviewer_id: int
    reviewed_head: str
    grant: GuardGrant


@dataclass(frozen=True, slots=True, repr=False)
class RawCommit:
    oid: str
    parents: tuple[str, ...]
    tree: str


class Objects(Protocol):
    """Read authenticated refs and raw Git objects with no replacement or grafts."""

    def ref(self, binding: forgejo.Binding, ref: str) -> str: ...
    def commit(self, binding: forgejo.Binding, oid: str) -> RawCommit: ...
    def is_ancestor(self, binding: forgejo.Binding, ancestor: str, descendant: str) -> bool: ...


class Authority(Protocol):
    """Independent policy, guard and persisted reservation authority.

    Preconditions require live binding of the ordinary transport principal,
    effective native protection and review, functioning generated dispatcher,
    installed guard and its scope, and the immutable operator-owned grant.
    Unknown or unsupported observations must raise or return no preconditions.
    """

    def verify_reservation(self, intent: MergeIntent, reservation: r.NativeReservation) -> None:
        """Check the persisted current reservation and exact intent, including the PR ID."""
        ...

    def observe_preconditions(self, intent: MergeIntent,
                              reservation: r.NativeReservation) -> MergePreconditions | None: ...

    def claim_submission(self, intent: MergeIntent, reservation: r.NativeReservation) -> None:
        """Atomically persist the ordered submission claim once before any native POST."""
        ...


@dataclass(frozen=True, slots=True, repr=False)
class VerifiedMerge:
    target: MergeTarget
    pull_number: int
    pull_request_id: int
    operation_id: str
    invocation: r.InvocationIdentity
    candidate_digest: str
    projection_digest: str
    merge_oid: str
    target_oid: str
    parents: tuple[str, str]
    tree: str

    @property
    def receipt_digest(self) -> str:
        return c.identity(self)


@dataclass(frozen=True, slots=True, repr=False)
class _Pull:
    head: str
    base: str
    author_id: int
    open: bool
    merged: bool
    draft: bool
    mergeable: bool
    merge_oid: str | None
    merger_id: int | None
    merger_login: str | None


def _validate(intent: MergeIntent, reservation: r.NativeReservation, transport: forgejo.Transport) -> None:
    c._require(type(intent) is MergeIntent and type(intent.target) is MergeTarget
               and type(intent.subject) is ci.Subject and type(intent.projection) is r.Projection
               and type(reservation) is r.NativeReservation, "forgejo_merge_intent_invalid")
    target, subject, projection = intent.target, intent.subject, intent.projection
    candidate = subject.candidate
    forgejo._validate_binding(target.binding, transport)
    c._integer(target.actor_id)
    c._integer(intent.pull_request_id)
    c._digest(target.guard_digest)
    c._digest(target.dispatcher_digest)
    if (target.binding != subject.binding or target.target_ref != subject.target_ref
            or forgejo._branch(intent.source_ref) == forgejo._branch(target.target_ref)
            or candidate.projection_digest != c.identity(projection)
            or (projection.base, projection.head) != (candidate.base, candidate.head)
            or projection.source_digest != candidate.source_digest or candidate.tested_oid != candidate.head
            or candidate.base == candidate.head):
        raise c.Conflict("forgejo_merge_subject_unbound")
    if (reservation.kind != "merge" or reservation.subject_digest != c.identity(candidate)
            or reservation.generation != candidate.generation
            or (reservation.expected_base, reservation.expected_head) != (candidate.base, candidate.head)):
        raise c.Conflict("forgejo_merge_reservation_unbound")


def _pull_path(intent: MergeIntent) -> str:
    return f"/api/v1/repos/{intent.target.binding.repository}/pulls/{intent.subject.pull_number}"


def _pull(intent: MergeIntent, transport: forgejo.Transport) -> _Pull:
    binding = intent.target.binding
    row = forgejo._object(forgejo._get(transport, _pull_path(intent)).value)
    c._integer(row.get("id"))
    if forgejo._number(row) != intent.subject.pull_number or row["id"] != intent.pull_request_id:
        raise c.Conflict("forgejo_merge_pull_identity_unbound")
    head, base = forgejo._object(row.get("head")), forgejo._object(row.get("base"))
    if (not forgejo._same_repository(head, binding) or not forgejo._same_repository(base, binding)
            or head.get("ref") != forgejo._branch(intent.source_ref)
            or base.get("ref") != forgejo._branch(intent.target.target_ref)):
        raise c.Conflict("forgejo_merge_pull_scope_unbound")
    commit_ids = (head.get("sha"), base.get("sha"))
    for value in commit_ids:
        c._oid(value)
    c._require(type(row.get("draft")) is bool and type(row.get("mergeable")) is bool,
               "forgejo_merge_readiness_invalid")
    opened = forgejo._open(row)
    author = forgejo._object(row.get("user")).get("id")
    c._integer(author)
    merge_oid = merger_id = merger_login = None
    if row["merged"]:
        merge_oid = row.get("merge_commit_sha")
        merger = forgejo._object(row.get("merged_by"))
        merger_id, merger_login = merger.get("id"), merger.get("login")
        c._oid(merge_oid)
        c._integer(merger_id)
        c._require(isinstance(merger_login, str), "forgejo_merge_actor_invalid")
    return _Pull(head["sha"], base["sha"], author, opened, row["merged"], row["draft"], row["mergeable"],
                 merge_oid, merger_id, merger_login)


def _raw(objects: Objects, binding: forgejo.Binding, oid: str) -> RawCommit:
    result = objects.commit(binding, oid)
    c._require(type(result) is RawCommit and result.oid == oid, "forgejo_raw_commit_unbound")
    c._oids(result.parents, 64)
    c._oid(result.tree)
    c._require(all(len(item) == len(oid) for item in (*result.parents, result.tree)), "mixed_oid_formats")
    return result


def _projection(intent: MergeIntent, objects: Objects) -> None:
    candidate, binding = intent.subject.candidate, intent.target.binding
    previous = candidate.base
    for pair in intent.projection.mapping[:-1]:
        commit = _raw(objects, binding, pair.landed)
        if commit.parents != (previous,):
            raise c.Conflict("forgejo_merge_projection_unbound")
        previous = commit.oid
    commit = _raw(objects, binding, candidate.head)
    if (commit.parents != (previous,) or commit.tree != candidate.tree
            or commit.parents != candidate.tested_parents):
        raise c.Conflict("forgejo_merge_tested_object_unbound")


def _ready(intent: MergeIntent, transport: forgejo.Transport, objects: Objects) -> _Pull:
    candidate, target = intent.subject.candidate, intent.target
    native = _pull(intent, transport)
    if (not native.open or native.draft or not native.mergeable
            or (native.base, native.head) != (candidate.base, candidate.head)
            or objects.ref(target.binding, intent.source_ref) != candidate.head
            or objects.ref(target.binding, target.target_ref) != candidate.base):
        raise c.Conflict("forgejo_merge_native_candidate_changed")
    return native


def _approve(intent: MergeIntent, candidate: r.Candidate, native: _Pull,
             preconditions: MergePreconditions | None, producer_ids: set[int], now: datetime) -> None:
    if type(preconditions) is not MergePreconditions or type(preconditions.grant) is not GuardGrant:
        raise c.Unavailable("forgejo_guarded_merge_preconditions_unavailable")
    target, grant = intent.target, preconditions.grant
    c._integer(preconditions.reviewer_id)
    c._integer(grant.expires_at)
    expected = GuardGrant(target.binding.repository_id, target.target_ref, candidate.base, candidate.head,
                          candidate.tree, target.actor_id, intent.pull_request_id, grant.expires_at)
    if (preconditions.target != target or preconditions.policy_digest != candidate.policy_digest
            or preconditions.reviewed_head != candidate.head
            or preconditions.reviewer_id in {native.author_id, target.actor_id, *producer_ids}
            or type(grant.schema_version) is not int or grant.synthetic is not True
            or any(type(value) is not int for value in (grant.repository_id, grant.actor_id, grant.pull_request_id))
            or grant != expected or grant.expires_at <= int(now.timestamp())):
        raise c.Conflict("forgejo_guarded_merge_preconditions_changed")


def _merged_oid(intent: MergeIntent, transport: forgejo.Transport) -> str:
    native = _pull(intent, transport)
    if (not native.merged or native.merge_oid is None or native.merger_id != intent.target.actor_id
            or native.merger_login != intent.target.binding.api_account):
        raise c.Ambiguous("forgejo_merge_not_observed")
    return native.merge_oid


def _prove(intent: MergeIntent, reservation: r.NativeReservation, transport: forgejo.Transport,
           objects: Objects, authority: Authority) -> VerifiedMerge:
    candidate, target = intent.subject.candidate, intent.target
    try:
        authority.verify_reservation(intent, reservation)
        merge_oid = _merged_oid(intent, transport)
        _projection(intent, objects)
        commit = _raw(objects, target.binding, merge_oid)
        parents = (candidate.base, candidate.head)
        current = objects.ref(target.binding, target.target_ref)
        c._oid(current)
        if (commit.parents != parents or commit.tree != candidate.tree
                or len(current) != len(candidate.head)
                or objects.is_ancestor(target.binding, commit.oid, current) is not True
                or _merged_oid(intent, transport) != merge_oid):
            raise c.Ambiguous("forgejo_merge_delivery_unproved")
        authority.verify_reservation(intent, reservation)
    except (OSError, c.Invalid, c.Conflict, c.Unavailable, c.Ambiguous):
        raise c.Ambiguous("forgejo_merge_outcome_uncertain") from None
    return VerifiedMerge(target, intent.subject.pull_number, intent.pull_request_id, reservation.operation_id,
                         reservation.invocation, c.identity(candidate), candidate.projection_digest, commit.oid,
                         current, parents, commit.tree)


def merge(intent: MergeIntent, reservation: r.NativeReservation, plan: ci.CheckPlan, transport: forgejo.Transport,
          objects: Objects, authority: Authority, reader: ci.ReceiptReader) -> VerifiedMerge:
    """Submit once, with independently verified authority and observed native readiness."""
    _validate(intent, reservation, transport)
    c._require(type(plan) is ci.CheckPlan, "forgejo_check_plan_invalid")
    if reservation.uncertain:
        raise c.Ambiguous("forgejo_prior_merge_unresolved")
    try:
        authority.verify_reservation(intent, reservation)
        _projection(intent, objects)
        native = _ready(intent, transport, objects)
        preconditions = authority.observe_preconditions(intent, reservation)
        if _ready(intent, transport, objects) != native:
            raise c.Conflict("forgejo_merge_native_candidate_changed")
        assessment = ci.assess_ci(intent.subject, plan, transport, reader, observed_at=datetime.now(timezone.utc))
        producer_ids = {check.creator_id for check in plan.checks}
        if assessment.state != "passed" or intent.target.actor_id in producer_ids:
            raise c.Unavailable("forgejo_merge_ci_unqualified")
        _approve(intent, intent.subject.candidate, native, preconditions, producer_ids, datetime.now(timezone.utc))
    except OSError:
        raise c.Unavailable("forgejo_merge_preflight_unavailable") from None
    try:
        authority.claim_submission(intent, reservation)
    except OSError:
        raise c.Ambiguous("forgejo_merge_submission_claim_uncertain") from None
    body = {
        "Do": "merge",
        "head_commit_id": reservation.expected_head,
        "force_merge": False,
        "merge_when_checks_succeed": False,
        "delete_branch_after_merge": False,
    }
    try:
        response = transport.request("POST", _pull_path(intent) + "/merge", body)
    except (OSError, c.Invalid, c.Conflict, c.Unavailable, c.Ambiguous):
        raise c.Ambiguous("forgejo_merge_outcome_uncertain") from None
    if type(response) is not forgejo.Response or type(response.status) is not int or response.status != 200:
        raise c.Ambiguous("forgejo_merge_outcome_uncertain")
    return _prove(intent, reservation, transport, objects, authority)


def reconcile(intent: MergeIntent, reservation: r.NativeReservation, transport: forgejo.Transport,
              objects: Objects, authority: Authority) -> VerifiedMerge:
    """Reconcile only by native readback. An unmerged observation cannot release a claim."""
    _validate(intent, reservation, transport)
    return _prove(intent, reservation, transport, objects, authority)
