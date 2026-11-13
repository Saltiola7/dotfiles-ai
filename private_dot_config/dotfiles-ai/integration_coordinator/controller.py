"""Default-off hosted orchestration over the single version-two ledger engine.

The entry point is deliberately lazy: disabled configuration reads no event,
credential, environment identity, Git object or provider. Live authority requires
native hosted identity, the reviewed policy and the separately delegated mutator.
"""
from __future__ import annotations

from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Protocol, TypeAlias
import urllib.parse

from . import core as c
from . import github as g
from . import runtime as r

DISPATCH_LIMIT = 48 * 1024
POLICY_LIMIT = 128 * 1024
MAX_STEPS = 16


def _hash(value: object) -> str:
    return hashlib.sha256(c._canonical(value)).hexdigest()


def native_guard_digest(target_digest: str, control_digest: str) -> str:
    return g.native_guard_digest(target_digest, control_digest)


@dataclass(frozen=True, slots=True)
class HostedConfig:
    enabled: bool = False
    enrollment: g.Enrollment | None = None
    check_plan: g.CheckPlan | None = None
    workflow_id: int | None = None
    workflow_path: str | None = None
    workflow_blob_oid: str | None = None
    shared_source_pin: str | None = None
    shared_source_repository: str | None = None
    job_name: str | None = None
    requester_ids: tuple[int, ...] = ()
    schema_version: int = 2

    def __post_init__(self) -> None:
        c._require(type(self.schema_version) is int and self.schema_version == 2, "hosted_schema")
        c._require(type(self.enabled) is bool, "hosted_enabled")
        if not self.enabled:
            c._require(self.enrollment is None and self.check_plan is None and self.workflow_id is None
                       and self.workflow_path is None and self.workflow_blob_oid is None
                       and self.shared_source_pin is None and self.shared_source_repository is None
                       and self.job_name is None and not self.requester_ids,
                       "disabled_hosted_fields")
            return
        c._require(type(self.enrollment) is g.Enrollment and self.enrollment.enabled, "hosted_enrollment")
        c._require(type(self.check_plan) is g.CheckPlan, "hosted_check_plan")
        c._integer(self.workflow_id)
        c._require(isinstance(self.workflow_path, str) and re.fullmatch(
            r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml", self.workflow_path) is not None, "hosted_workflow")
        c._oid(self.workflow_blob_oid)
        c._oid(self.shared_source_pin)
        c._repository(self.shared_source_repository)
        c._require(isinstance(self.job_name, str) and 0 < len(self.job_name) <= 128
                   and all(32 <= ord(char) < 127 for char in self.job_name), "hosted_job")
        c._tuple(self.requester_ids, int, 128, 1)
        c._require(len(set(self.requester_ids)) == len(self.requester_ids), "hosted_requesters")
        for user in self.requester_ids:
            c._integer(user)
        assert self.enrollment is not None
        c._digest(self.enrollment.native_guard_digest)


def _config_data(config: HostedConfig) -> dict[str, object]:
    if not config.enabled:
        return {"schema_version": 2, "enabled": False}
    assert config.enrollment is not None and config.check_plan is not None
    return {"schema_version": 2, "enabled": True,
            "enrollment": {"schema_version": 2, **asdict(config.enrollment)},
            "check_plan": {"schema_version": 1, **asdict(config.check_plan)},
            "workflow_id": config.workflow_id, "workflow_path": config.workflow_path,
            "workflow_blob_oid": config.workflow_blob_oid, "shared_source_pin": config.shared_source_pin,
            "shared_source_repository": config.shared_source_repository, "job_name": config.job_name,
            "requester_ids": config.requester_ids}


def policy_identity(config: HostedConfig) -> str:
    """One policy identity; omit only its own enrollment.policy_digest field."""
    if not config.enabled:
        raise c.Unavailable("disabled_policy_has_no_live_identity")
    data = _config_data(config)
    enrollment = data["enrollment"]
    assert isinstance(enrollment, dict)
    enrollment.pop("policy_digest")
    return _hash(data)


def _policy_identity(config: HostedConfig) -> None:
    assert config.enrollment is not None
    if config.enrollment.policy_digest != policy_identity(config):
        raise c.Invalid("hosted_policy_identity")


def parse_config(raw: bytes) -> HostedConfig:
    data = g._object(g.decode_json(raw, POLICY_LIMIT))
    if data.get("enabled") is False:
        if set(data) != {"schema_version", "enabled"}:
            raise c.Invalid("disabled_hosted_fields")
        return HostedConfig(schema_version=g._integer(data["schema_version"]))
    names = {"schema_version", "enabled", "enrollment", "check_plan", "workflow_id", "workflow_path",
             "workflow_blob_oid", "shared_source_pin", "shared_source_repository", "job_name", "requester_ids",
             }
    if set(data) != names or data.get("enabled") is not True:
        raise c.Invalid("hosted_config_fields")
    config = HostedConfig(True, g.parse_enrollment(data["enrollment"]), g.parse_check_plan(data["check_plan"]),
        g._integer(data["workflow_id"]), g._text(data["workflow_path"], 256), g._oid(data["workflow_blob_oid"]),
        g._oid(data["shared_source_pin"]), g._text(data["shared_source_repository"], 201), g._text(data["job_name"], 128),
        tuple(g._integer(value) for value in g._array(data["requester_ids"], 128)),
        g._integer(data["schema_version"]))
    _policy_identity(config)
    return config


@dataclass(frozen=True, slots=True)
class HostContext:
    repository: str
    run_id: int
    attempt: int
    event_name: str
    ref: str
    workflow_sha: str
    implementation_ref: str
    implementation_repository: str

    def __post_init__(self) -> None:
        c._repository(self.repository)
        c._integer(self.run_id)
        c._integer(self.attempt)
        c._require(self.event_name in {"workflow_dispatch", "workflow_run", "schedule"}, "host_event")
        c._oid(self.workflow_sha)
        c._oid(self.implementation_ref)
        c._repository(self.implementation_repository)
        c._require(isinstance(self.ref, str) and len(self.ref) <= 300, "host_ref")


@dataclass(frozen=True, slots=True)
class VerifiedHost:
    invocation: r.Invocation
    actor_id: int
    event_name: str
    receipt_digest: str

    def __post_init__(self) -> None:
        c._require(type(self.invocation) is r.Invocation)
        c._integer(self.actor_id)
        c._require(self.event_name in {"workflow_dispatch", "workflow_run", "schedule"})
        c._digest(self.receipt_digest)


@dataclass(frozen=True, slots=True)
class OperatorAuthority:
    """Qualified local port result, not accepted from hosted/caller JSON."""
    invocation: r.OperatorInvocation
    receipt_digest: str
    expected_handle: str
    expected_generation: int

    def __post_init__(self) -> None:
        c._require(type(self.invocation) is r.OperatorInvocation)
        c._digest(self.receipt_digest)
        c._handle(self.expected_handle)
        c._integer(self.expected_generation)


Authority: TypeAlias = VerifiedHost | OperatorAuthority


class QuiescencePort(Protocol):
    def quiescent(self, invocation: r.InvocationIdentity) -> bool: ...


class HostPort(Protocol):
    def verify(self, config: HostedConfig, context: HostContext) -> VerifiedHost: ...
    def quiescent(self, invocation: r.InvocationIdentity) -> bool: ...


class NativeHost:
    """GET-only hosted provenance before the mutator credential is accessed."""

    def __init__(self, transport: g.Transport) -> None:
        self.transport = transport
        self._config: HostedConfig | None = None

    @classmethod
    def for_reconciliation(cls, transport: g.Transport, config: HostedConfig) -> QuiescencePort:
        """Read historical native custody without claiming a current hosted job."""
        if not config.enabled:
            raise c.Unavailable("coordinator_disabled")
        _policy_identity(config)
        reader = cls(transport)
        reader._config = config
        return reader

    def _get(self, repository: str, path: str) -> dict[str, object]:
        try:
            return g._object(self.transport.request("GET", f"repos/{repository}/{path}"))
        except g.ApiFailure:
            raise c.Unavailable("host_native_identity_unavailable") from None

    def _workflow(self, config: HostedConfig, run: dict[str, object]) -> str:
        assert config.enrollment is not None and config.workflow_path is not None
        sha = g._oid(run.get("head_sha"))
        if (run.get("workflow_id") != config.workflow_id or run.get("path") != config.workflow_path
                or run.get("head_branch") != config.enrollment.default_branch
                or g._object(run.get("repository")).get("id") != config.enrollment.repository_id
                or g._object(run.get("repository")).get("full_name") != config.enrollment.repository):
            raise c.Unavailable("host_native_workflow_unbound")
        blob = self._get(config.enrollment.repository,
                         f"contents/{config.workflow_path}?ref={urllib.parse.quote(sha, safe='')}")
        if blob.get("type") != "file" or blob.get("sha") != config.workflow_blob_oid:
            raise c.Unavailable("host_workflow_source_unqualified")
        return _hash({"repository": config.enrollment.repository, "workflow_id": config.workflow_id,
                      "path": config.workflow_path, "blob": config.workflow_blob_oid,
                      "implementation_repository": config.shared_source_repository, "implementation_ref": config.shared_source_pin})

    def _jobs(self, config: HostedConfig, run_id: int, attempt: int) -> list[dict[str, object]]:
        assert config.enrollment is not None
        value = self._get(config.enrollment.repository, f"actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page=1")
        jobs = [g._object(item) for item in g._array(value.get("jobs"), 100)]
        if type(value.get("total_count")) is not int or value["total_count"] != len(jobs):
            raise c.Unavailable("host_job_inventory_unavailable")
        return jobs

    @staticmethod
    def _invocation(run_id: int, attempt: int, job_id: int) -> str:
        return _hash({"run_id": run_id, "attempt": attempt, "job_id": job_id})

    def verify(self, config: HostedConfig, context: HostContext) -> VerifiedHost:
        if not config.enabled or config.enrollment is None:
            raise c.Unavailable("coordinator_disabled")
        enrollment = config.enrollment
        if (context.repository != enrollment.repository or context.ref != f"refs/heads/{enrollment.default_branch}"
                or context.implementation_ref != config.shared_source_pin
                or context.implementation_repository != config.shared_source_repository):
            raise c.Unavailable("host_context_unqualified")
        run = self._get(enrollment.repository, f"actions/runs/{context.run_id}")
        if (run.get("id") != context.run_id or run.get("run_attempt") != context.attempt
                or run.get("event") != context.event_name or run.get("head_sha") != context.workflow_sha
                or run.get("status") != "in_progress"):
            raise c.Unavailable("host_run_unqualified")
        workflow_digest = self._workflow(config, run)
        actor = g._integer(g._object(run.get("actor")).get("id"))
        triggering = g._integer(g._object(run.get("triggering_actor")).get("id"))
        if context.event_name == "workflow_dispatch" and (actor not in config.requester_ids or triggering not in config.requester_ids):
            raise c.Unavailable("host_requester_not_enrolled")
        jobs = [job for job in self._jobs(config, context.run_id, context.attempt) if job.get("name") == config.job_name]
        if len(jobs) != 1:
            raise c.Unavailable("host_job_ambiguous")
        job = jobs[0]
        labels = g._array(job.get("labels"), 64)
        if (job.get("run_id") != context.run_id or job.get("run_attempt") != context.attempt
                or job.get("status") != "in_progress" or job.get("runner_group_name") != "GitHub Actions"
                or "self-hosted" in labels):
            raise c.Unavailable("host_job_unqualified")
        invocation = r.Invocation(context.run_id, context.attempt,
            self._invocation(context.run_id, context.attempt, g._integer(job.get("id"))), workflow_digest)
        self._config = config
        return VerifiedHost(invocation, actor, context.event_name, _hash({"run": run, "job": job, "workflow": workflow_digest}))

    def quiescent(self, invocation: r.InvocationIdentity) -> bool:
        if not isinstance(invocation, r.Invocation):
            raise c.Unavailable("operator_custody_requires_local_proof")
        config = self._config
        if config is None or config.enrollment is None:
            raise c.Unavailable("host_identity_not_qualified")
        run = self._get(config.enrollment.repository, f"actions/runs/{invocation.run_id}/attempts/{invocation.attempt}")
        if (run.get("id") != invocation.run_id or run.get("run_attempt") != invocation.attempt
                or self._workflow(config, run) != invocation.workflow_digest):
            raise c.Unavailable("host_prior_invocation_unbound")
        jobs = [job for job in self._jobs(config, invocation.run_id, invocation.attempt)
                if self._invocation(invocation.run_id, invocation.attempt, g._integer(job.get("id"))) == invocation.invocation_id]
        if len(jobs) != 1 or jobs[0].get("name") != config.job_name:
            raise c.Unavailable("host_prior_job_unbound")
        return run.get("status") == "completed" and jobs[0].get("status") == "completed"


class Adapter(Protocol):
    @property
    def enrollment(self) -> g.Enrollment: ...
    @property
    def plan(self) -> g.CheckPlan | None: ...
    def observe_policy(self) -> g.TargetGuards: ...
    def observe_control(self) -> str: ...
    def read_control(self, lookup_handles: tuple[str, ...] = ()) -> tuple[str, dict[str, bytes]]: ...
    def append(self, request: r.AppendRequest) -> str: ...
    def observe_pr(self, number: int) -> g.PullFacts: ...
    def get(self, path: str) -> object: ...
    def projection(self, source: r.SourceSeries, head: str, base: str) -> r.Projection: ...
    def candidate(self, ticket: r.Ticket, generation: int, projection: r.Projection) -> r.Candidate: ...
    def qualify(self, candidate: r.Candidate, pr_number: int) -> c.Qualification: ...
    def refresh(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult: ...
    def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery: ...
    def reconcile(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult | r.Delivery | r.NoEffect: ...


@dataclass(frozen=True, slots=True)
class Report:
    status: str
    handle: str | None = None
    control_head: str | None = None
    detail: str | None = None


def _policy(adapter: Adapter, config: HostedConfig) -> None:
    if adapter.enrollment != config.enrollment or adapter.plan != config.check_plan:
        raise c.Unavailable("host_adapter_configuration_changed")
    target = adapter.observe_policy()
    assert config.enrollment is not None
    if target.digest != config.enrollment.native_guard_digest:
        raise c.Unavailable("native_policy_changed")


def _read(adapter: Adapter, config: HostedConfig, handles: tuple[str, ...] = ()) -> tuple[str, r.RuntimeSnapshot]:
    _policy(adapter, config)
    head, records = adapter.read_control(handles)
    state = r.load_snapshot(records)
    assert config.enrollment is not None
    enrollment = config.enrollment
    if (state.target.repository, state.target.default_branch, state.target.root_oid, state.target.policy_digest) != (
            enrollment.repository, enrollment.default_branch, enrollment.root_oid, enrollment.policy_digest):
        raise c.Unavailable("native_ledger_authority_changed")
    return head, state


def _operation(host: Authority, state: r.RuntimeSnapshot, kind: str, handle: str | None) -> str:
    return _hash({"invocation": asdict(host.invocation), "prior": state.target.last_operation,
                  "generation": state.target.generation, "kind": kind, "handle": handle})


def _persist(adapter: Adapter, config: HostedConfig, host: Authority, head: str,
             before: r.RuntimeSnapshot, after: r.RuntimeSnapshot, kind: str, handle: str | None) -> str:
    _policy(adapter, config)
    assert config.enrollment is not None
    return adapter.append(r.build_append(before, after, head, config.enrollment.control_branch,
                                         _operation(host, before, kind, handle)))


def _dispatch(raw: bytes, config: HostedConfig, host: VerifiedHost) -> tuple[r.Ticket, r.Obligation, c.Admission]:
    if type(raw) is not bytes or len(raw) > DISPATCH_LIMIT:
        raise c.Invalid("dispatch_envelope_size")
    body = g._object(g.decode_json(raw, DISPATCH_LIMIT))
    if set(body) != {"schema_version", "policy_digest", "ticket", "obligation"} or type(body["schema_version"]) is not int or body["schema_version"] != 2:
        raise c.Invalid("dispatch_envelope_fields")
    assert config.enrollment is not None
    c._digest(body["policy_digest"])
    if body["policy_digest"] != config.enrollment.policy_digest:
        raise c.Unavailable("dispatch_policy_changed")
    ticket = r.decode("ticket", c._canonical(body["ticket"]))
    obligation = r.decode("obligation", c._canonical(body["obligation"]))
    assert isinstance(ticket, r.Ticket) and isinstance(obligation, r.Obligation)
    assert config.enrollment is not None
    if ticket.delivery_mode == "admin" and not config.enrollment.review_exception:
        raise c.Unavailable("task_admin_not_enrolled")
    if (ticket.source.repository != config.enrollment.repository
            or ticket.requester_digest != r.requester_digest(config.enrollment.repository, host.actor_id)):
        raise c.Unavailable("dispatch_requester_binding")
    admission = c.Admission(c.identity(ticket.source), ticket.requester_digest, config.enrollment.policy_digest,
        _hash({"host": host.receipt_digest, "source": c.identity(ticket.source), "descriptor": _hash(body)}))
    return ticket, obligation, admission


def _outcome(state: r.RuntimeSnapshot, ticket: r.Ticket, proof: r.RefreshResult | r.Delivery | r.NoEffect) -> r.RuntimeSnapshot:
    if isinstance(proof, r.RefreshResult):
        return r.record_projection(state, ticket.handle, ticket.generation, proof)
    if isinstance(proof, r.Delivery):
        return r.record_delivery(state, ticket.handle, ticket.generation, proof)
    if isinstance(proof, r.NoEffect):
        return r.resolve_no_effect(state, ticket.handle, ticket.generation, proof)
    raise c.Invalid("native_outcome_type")


def _repair_admission(adapter: Adapter, config: HostedConfig, host: VerifiedHost, head: str,
                      state: r.RuntimeSnapshot, ticket: r.Ticket, expected: r.Obligation,
                      admission: c.Admission) -> tuple[str, r.RuntimeSnapshot]:
    predecessor = ticket.predecessor
    assert predecessor is not None
    actual = state.obligation(ticket.obligation_handle)
    if expected.handle != actual.handle or expected.grant_digest != actual.grant_digest:
        raise c.Conflict("repair_root_grant_changed")
    authorization = ticket.source.authority_digest
    if actual.current_ticket != predecessor:
        # Only the identical accepted successor is an idempotent retry. The
        # immutable original request never overwrites the newer current index.
        result = r.supersede(state, ticket.obligation_handle, predecessor, ticket, admission, authorization)
        return head, result
    old = state.ticket(predecessor)
    if (old.state != r.State.REPAIR_PENDING or old.reservation is not None
            or old.requester_digest != ticket.requester_digest or expected.current_ticket != predecessor):
        raise c.Conflict("repair_predecessor_changed")
    observations = {(actual.repair_count, actual.revision_count, actual.repair_owner)}
    if actual.repair_owner == authorization and actual.repair_count > 0:
        observations.add((actual.repair_count - 1, actual.revision_count, None))
    # An incoming index is an expected observation, not a counter assignment.
    # Accept either our reserved snapshot or its exact preceding unreserved one.
    # Archive links may advance independently; current/grant/counters may not.
    if (expected.repair_count, expected.revision_count, expected.repair_owner) not in observations:
        raise c.Conflict("repair_counter_observation_changed")
    owned = r.reserve_repair(state, ticket.obligation_handle, predecessor, authorization)
    if owned != state:
        head = _persist(adapter, config, host, head, state, owned, "repair_owner", ticket.handle)
    head, state = _read(adapter, config, (ticket.handle, predecessor, ticket.obligation_handle))
    successor = r.supersede(state, ticket.obligation_handle, predecessor, ticket, admission, authorization)
    if successor != state:
        head = _persist(adapter, config, host, head, state, successor, "supersede", ticket.handle)
    return head, successor


def run(config: HostedConfig, context_loader: Callable[[], HostContext], host_factory: Callable[[], HostPort],
        adapter_factory: Callable[[], Adapter], dispatch_loader: Callable[[], bytes] | None = None) -> Report:
    if not config.enabled:
        return Report("disabled")
    _policy_identity(config)
    context = context_loader()
    host_port = host_factory()
    host = host_port.verify(config, context)
    incoming: tuple[r.Ticket, r.Obligation, c.Admission] | None = None
    if host.event_name == "workflow_dispatch":
        if dispatch_loader is None:
            raise c.Unavailable("dispatch_input_unavailable")
        raw = dispatch_loader()
        if raw:
            incoming = _dispatch(raw, config, host)
    adapter = adapter_factory()  # Explicit delegated credential is accessed only after host/source preflight.
    handles = () if incoming is None else tuple(dict.fromkeys((incoming[0].handle, incoming[1].handle,
        *((incoming[0].predecessor,) if incoming[0].predecessor is not None else ()))))
    head, state = _read(adapter, config, handles)
    if incoming is not None:
        # Recover a crash after supersession before consuming the reserved repair
        # headroom. This moves only terminal metadata; source/outcomes stay intact.
        for _ in range(MAX_STEPS):
            terminal = next((value for value in state.tickets if value.state in r.TERMINAL), None)
            if terminal is None:
                break
            archived = r.archive(state, terminal.handle)
            _persist(adapter, config, host, head, state, archived, "admission_archive", terminal.handle)
            head, state = _read(adapter, config, handles)
        ticket, obligation, admission = incoming
        # A verified archived duplicate remains idempotent even though its PR is closed.
        existing = next((value for value in (*state.tickets, *(entry.ticket for entry in state.archives))
                         if value.handle == ticket.handle), None)
        if existing is None:
            pr = adapter.observe_pr(ticket.source.pr_number)
            assert config.enrollment is not None
            if (pr.merged or pr.head != ticket.current_head or pr.base_ref != config.enrollment.default_branch
                    or pr.head_ref in {config.enrollment.default_branch, "main", "master", config.enrollment.control_branch}):
                raise c.Unavailable("dispatch_source_changed")
        if ticket.predecessor is None:
            admitted = r.admit_authenticated(state, ticket, obligation, admission)
            if admitted != state:
                head = _persist(adapter, config, host, head, state, admitted, "admit", ticket.handle)
        else:
            head, admitted = _repair_admission(adapter, config, host, head, state, ticket, obligation, admission)
        if existing is not None and existing.state == r.State.DELIVERED:
            return Report("delivered", ticket.handle, head)
    return advance(config, host, host_port, adapter, handles)


def advance(config: HostedConfig, host: Authority, host_port: QuiescencePort, adapter: Adapter,
            handles: tuple[str, ...] = ()) -> Report:
    """Same guarded scheduler for qualified hosted or qualified local authority.

    This is an injected-port API, not JSON authentication. Local operator code must
    prove requester/scope/private-process custody before constructing its authority.
    """
    if not config.enabled:
        return Report("disabled")
    _policy_identity(config)
    if isinstance(host, OperatorAuthority):
        assert config.enrollment is not None
        if (host.invocation.requester_id not in config.enrollment.mutator_user_ids
                or host.invocation.requester_id not in config.requester_ids):
            raise c.Unavailable("operator_requester_not_enrolled")
    head: str | None = None
    generation_fence = host.expected_generation if isinstance(host, OperatorAuthority) else None
    first_view = True
    def commit(head: str, before: r.RuntimeSnapshot, after: r.RuntimeSnapshot,
               kind: str, handle: str | None) -> str:
        nonlocal generation_fence
        result = _persist(adapter, config, host, head, before, after, kind, handle)
        if isinstance(host, OperatorAuthority):
            generation_fence = after.target.generation
        return result
    def block(head: str, state: r.RuntimeSnapshot, ticket: r.Ticket,
              failure_digest: str, detail: str) -> Report:
        if ticket.state == r.State.QUEUED:
            after = r.park_queued(state, ticket.handle, failure_digest)
        else:
            after = r.record_failure(state, ticket.handle, ticket.generation, failure_digest)
        updated = commit(head, state, after, "source_block", ticket.handle)
        return Report("repair_pending", ticket.handle, updated, detail)
    # Each iteration rereads the pinned native view and effective policy. Provider
    # concurrency is merely an optimization; native expected-head CAS owns state.
    for _ in range(MAX_STEPS):
        head, state = _read(adapter, config, handles)
        if isinstance(host, OperatorAuthority):
            if state.target.generation != generation_fence or (first_view and state.target.active != host.expected_handle):
                raise c.Conflict("operator_fence_changed")
            subject = state.lookup_ticket(host.expected_handle)
            if state.target.active != host.expected_handle and subject.state not in r.TERMINAL:
                raise c.Conflict("operator_subject_changed")
            terminal = subject if subject.state in r.TERMINAL else None
        else:
            terminal = next((ticket for ticket in state.tickets if ticket.state in r.TERMINAL), None)
        first_view = False
        if terminal is not None:
            after = r.archive(state, terminal.handle)
            head = commit(head, state, after, "archive", terminal.handle)
            if terminal.state == r.State.DELIVERED:
                return Report("delivered", terminal.handle, head)
            if isinstance(host, OperatorAuthority):
                return Report(terminal.state.value, terminal.handle, head)
            continue
        if state.target.active is None:
            if isinstance(host, OperatorAuthority):
                raise c.Conflict("operator_subject_not_active")
            if not state.target.queue:
                return Report("idle", control_head=head)
            ticket = state.ticket(state.target.queue[0])
            try:
                pr = adapter.observe_pr(ticket.source.pr_number)
            except g.SourceChanged as changed:
                return block(head, state, ticket, changed.failure_digest, "native_source_not_admissible")
            if pr.merged or pr.head != ticket.current_head:
                detail = "native_delivery_requires_reconciliation" if pr.merged else "native_source_changed_without_projection"
                failure = _hash({"kind": detail, "ticket": c.identity(ticket), "native": asdict(pr)})
                return block(head, state, ticket, failure, detail)
            assert config.check_plan is not None
            after = r.claim(state, ticket.handle, pr.base, config.check_plan.digest)
            commit(head, state, after, "claim", ticket.handle)
            continue
        ticket = state.ticket(state.target.active)
        reservation = ticket.reservation
        if reservation is not None:
            try:
                proof = adapter.reconcile(ticket, reservation)  # Read-only even while an old worker may exist.
                exhausted = isinstance(proof, r.Delivery) or (
                    isinstance(proof, r.RefreshResult) and proof.projection.head != reservation.expected_head)
                if not exhausted and not host_port.quiescent(reservation.invocation):
                    return Report("uncertain", ticket.handle, head, "prior_worker_not_quiescent")
                after = _outcome(state, ticket, proof)
            except (c.Ambiguous, c.Unavailable):
                return Report("uncertain", ticket.handle, head, "native_effect_unresolved")
            commit(head, state, after, "reconcile", ticket.handle)
            continue
        try:
            pr = adapter.observe_pr(ticket.source.pr_number)
        except g.SourceChanged as changed:
            return block(head, state, ticket, changed.failure_digest, "native_source_not_admissible")
        if pr.head != ticket.current_head:
            failure = _hash({"kind": "native_source_changed_without_projection", "ticket": c.identity(ticket),
                             "native_head": pr.head, "native_base": pr.base})
            after = r.record_failure(state, ticket.handle, ticket.generation, failure)
            head = commit(head, state, after, "source_changed", ticket.handle)
            return Report("repair_pending", ticket.handle, head, "native_source_changed_without_projection")
        if pr.merged:
            failure = _hash({"kind": "native_delivery_requires_reconciliation", "ticket": c.identity(ticket), "native": asdict(pr)})
            return block(head, state, ticket, failure, "native_delivery_requires_reconciliation")
        if (pr.base != ticket.base or ticket.candidate is not None
                and not pr.merged and pr.merge_oid != ticket.candidate.tested_oid):
            assert config.check_plan is not None
            after = r.invalidate(state, ticket.handle, ticket.generation, pr.base, config.check_plan.digest)
            commit(head, state, after, "invalidate", ticket.handle)
            continue
        if ticket.state == r.State.AWAITING_OPERATOR:
            return Report("awaiting_operator", ticket.handle, head)
        kind: str | None = None
        qualification: c.Qualification | None = None
        if ticket.state == r.State.PREPARING:
            comparison = g._object(adapter.get(f"compare/{pr.base}...{pr.head}"))
            comparison_base = g._oid(g._object(comparison.get("merge_base_commit")).get("sha"))
            if comparison_base != pr.base:
                if not ticket.guarded_refresh:
                    failure = _hash({"kind": "task_refresh_not_authorized", "ticket": c.identity(ticket),
                                     "native_head": pr.head, "native_base": pr.base})
                    after = r.record_failure(state, ticket.handle, ticket.generation, failure)
                    head = commit(head, state, after, "permission_block", ticket.handle)
                    return Report("repair_pending", ticket.handle, head, "task_refresh_not_authorized")
                kind = "refresh"
            elif ticket.projection is None or ticket.projection.base != pr.base:
                try:
                    projection = adapter.projection(ticket.source, pr.head, pr.base)
                except g.SourceChanged as changed:
                    return block(head, state, ticket, changed.failure_digest, "native_source_not_admissible")
                after = r.bind_projection(state, ticket.handle, ticket.generation, projection)
                commit(head, state, after, "bind_projection", ticket.handle)
                continue
            else:
                try:
                    candidate = adapter.candidate(ticket, ticket.generation, ticket.projection)
                except g.SourceChanged as changed:
                    return block(head, state, ticket, changed.failure_digest, "native_source_not_admissible")
                after = r.bind_candidate(state, ticket.handle, ticket.generation, candidate)
                commit(head, state, after, "candidate", ticket.handle)
                continue
        elif ticket.state == r.State.QUALIFYING:
            assert ticket.candidate is not None
            try:
                qualification = adapter.qualify(ticket.candidate, ticket.source.pr_number)
            except g.SourceChanged as changed:
                return block(head, state, ticket, changed.failure_digest, "native_source_not_admissible")
            except g.FailedChecks as failure:
                after = r.record_failure(state, ticket.handle, ticket.generation, failure.failure_digest)
                head = commit(head, state, after, "failure", ticket.handle)
                return Report("repair_pending", ticket.handle, head)
            except c.Unavailable:
                return Report("waiting", ticket.handle, head, "native_checks_not_qualified")
            kind = "merge"
        else:
            raise c.Unavailable("active_state_not_qualified")
        assert kind is not None
        operation_id = _operation(host, state, kind, ticket.handle)
        retained = _hash({"source_head": ticket.source.head, "current_head": ticket.current_head}) if kind == "refresh" else None
        after = r.reserve_native(state, ticket.handle, ticket.generation, kind, operation_id, host.invocation,
                                 qualification=qualification, retention_digest=retained)
        commit(head, state, after, "reserve", ticket.handle)
        # Reobserve the persisted reservation and invocation before the native call.
        head, fenced = _read(adapter, config, handles)
        current = fenced.ticket(ticket.handle)
        expected = after.ticket(ticket.handle).reservation
        if (fenced.target.active != ticket.handle or fenced.target.generation != ticket.generation
                or current.reservation != expected or expected is None or expected.invocation != host.invocation):
            raise c.Conflict("worker_fence_changed")
        try:
            proof = adapter.refresh(current, expected) if kind == "refresh" else adapter.merge(current, expected)
            result = _outcome(fenced, current, proof)
        except g.NativeRejection as rejection:
            no_effect = r.NoEffect(expected.operation_id, expected.invocation, expected.subject_digest, rejection.receipt_digest)
            try:
                fresh = adapter.observe_pr(current.source.pr_number)
            except (c.Invalid, c.Conflict, c.Unavailable):
                fresh = None
            if (fresh is not None and not fresh.merged and fresh.head == current.current_head
                    and (fresh.base != current.base or current.candidate is not None
                         and fresh.merge_oid != current.candidate.tested_oid)):
                assert config.check_plan is not None
                result = r.reprepare_no_effect(fenced, current.handle, current.generation, no_effect,
                                              fresh.base, config.check_plan.digest)
                commit(head, fenced, result, "native_rejection_reprepare", ticket.handle)
                continue
            result = r.record_rejection(fenced, current.handle, current.generation, no_effect)
            head = commit(head, fenced, result, "native_rejection", ticket.handle)
            return Report("repair_pending", ticket.handle, head, "native_mutation_rejected")
        except (c.Ambiguous, c.Unavailable, c.Invalid, c.Conflict):
            result = r.mark_uncertain(fenced, current.handle, current.generation, expected.operation_id)
            head = commit(head, fenced, result, "uncertain", ticket.handle)
            return Report("uncertain", ticket.handle, head, "native_effect_requires_reconciliation")
        commit(head, fenced, result, "native_outcome", ticket.handle)
    return Report("waiting", control_head=head, detail="bounded_advance_yield")


def _regular_bytes(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise c.Invalid("host_file_not_regular")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise c.Invalid("host_file_size")
    return raw


def _context() -> HostContext:
    def required(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise c.Unavailable("host_environment_missing")
        return value
    if required("GITHUB_SERVER_URL") != "https://github.com" or required("GITHUB_API_URL") != "https://api.github.com":
        raise c.Unavailable("host_provider_unsupported")
    run_id, attempt = required("GITHUB_RUN_ID"), required("GITHUB_RUN_ATTEMPT")
    if re.fullmatch(r"[1-9][0-9]{0,15}", run_id) is None or re.fullmatch(r"[1-9][0-9]{0,15}", attempt) is None:
        raise c.Invalid("host_environment_integer")
    return HostContext(required("GITHUB_REPOSITORY"), int(run_id), int(attempt), required("GITHUB_EVENT_NAME"),
        required("GITHUB_REF"), required("GITHUB_WORKFLOW_SHA"), required("DBSCTR_COORDINATOR_IMPLEMENTATION_REF"),
        required("DBSCTR_COORDINATOR_IMPLEMENTATION_REPOSITORY"))


def _workspace_policy_path(policy_path: Path) -> str:
    workspace_name = os.environ.get("GITHUB_WORKSPACE")
    if not workspace_name:
        raise c.Unavailable("host_workspace_missing")
    try:
        workspace = Path(workspace_name).absolute()
        candidate = policy_path.absolute()
        if (workspace != workspace.resolve(strict=True) or not workspace.is_dir()
                or candidate != candidate.resolve(strict=True) or not candidate.is_file()):
            raise c.Invalid("host_policy_path_unqualified")
        relative = candidate.relative_to(workspace).as_posix()
    except (OSError, ValueError):
        raise c.Invalid("host_policy_path_unqualified") from None
    g._member(relative)
    if not relative.endswith(".json") or any(part in {".git", ".dbsctr"} for part in Path(relative).parts):
        raise c.Invalid("host_policy_path_unqualified")
    return relative


def hosted_main(policy_path: Path) -> int:
    """Fixed credential and native-context bridge for the reviewed hosted action."""
    try:
        config = parse_config(_regular_bytes(policy_path, POLICY_LIMIT))
        if not config.enabled:
            print(json.dumps(asdict(Report("disabled")), sort_keys=True))
            return 0
        # Importing the port is not Git startup; even this import follows disabled.
        from .gitproof import GitMirror, ProofPort
        with ExitStack() as stack:
            def host_factory() -> HostPort:
                token = os.environ.get("GITHUB_TOKEN")
                if not token:
                    raise c.Unavailable("host_read_token_missing")
                return NativeHost(g.HttpTransport(token))
            def adapter_factory() -> Adapter:
                token = os.environ.get("DBSCTR_COORDINATOR_TOKEN")
                if not token:
                    raise c.Unavailable("host_mutator_delegation_missing")
                assert config.enrollment is not None and config.check_plan is not None
                policy_relative = _workspace_policy_path(policy_path)
                mirror = stack.enter_context(GitMirror(config.enrollment.repository, token))
                return g.GitHub(g.HttpTransport(token), config.enrollment, ProofPort(mirror.supply), config.check_plan,
                                policy_path=policy_relative)
            def dispatch_loader() -> bytes:
                event_path = os.environ.get("GITHUB_EVENT_PATH")
                if not event_path:
                    raise c.Unavailable("host_event_missing")
                event = g._object(g.decode_json(_regular_bytes(Path(event_path), POLICY_LIMIT), POLICY_LIMIT))
                inputs = g._object(event.get("inputs"))
                if set(inputs) != {"request"} or not isinstance(inputs["request"], str):
                    raise c.Invalid("host_dispatch_inputs")
                raw = inputs["request"].encode("utf-8")
                if len(raw) > DISPATCH_LIMIT:
                    raise c.Invalid("dispatch_envelope_size")
                return raw
            report = run(config, _context, host_factory, adapter_factory, dispatch_loader)
        print(json.dumps(asdict(report), sort_keys=True))
        return 0
    except (c.Invalid, c.Conflict, c.Unavailable, c.Ambiguous):
        print(json.dumps(asdict(Report("blocked", detail="hosted_authority_or_state_unavailable")), sort_keys=True))
        return 78
    except (OSError, UnicodeError, ValueError):
        print(json.dumps(asdict(Report("blocked", detail="invalid_hosted_input")), sort_keys=True))
        return 78
