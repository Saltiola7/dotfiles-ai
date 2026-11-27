"""Assess Forgejo commit statuses against caller-qualified execution evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal, Protocol

from . import core as c
from . import forgejo
from . import forgejo_status
from . import initiative_ci
from . import runtime as r


CheckState = Literal["waiting", "queued", "running", "stale", "unavailable", "failed", "passed"]


@dataclass(frozen=True, slots=True, repr=False)
class RequiredCheck:
    context: str
    creator_id: int
    producer_digest: str
    definition_digest: str

    def __post_init__(self) -> None:
        forgejo_status._context(self.context)
        forgejo_status._creator_id(self.creator_id)
        c._digest(self.producer_digest)
        c._digest(self.definition_digest)


@dataclass(frozen=True, slots=True, repr=False)
class CheckPlan:
    binding: forgejo.Binding
    target_ref: str
    policy_digest: str
    checks: tuple[RequiredCheck, ...]

    def __post_init__(self) -> None:
        c._require(type(self.binding) is forgejo.Binding, "forgejo_check_binding_invalid")
        forgejo._branch(self.target_ref)
        c._digest(self.policy_digest)
        c._tuple(self.checks, RequiredCheck, 512, 1)
        c._require(len({check.context for check in self.checks}) == len(self.checks),
                   "forgejo_check_context_ambiguous")


@dataclass(frozen=True, slots=True, repr=False)
class Subject:
    binding: forgejo.Binding
    target_ref: str
    pull_number: int
    candidate: r.Candidate

    def __post_init__(self) -> None:
        c._require(type(self.binding) is forgejo.Binding, "forgejo_check_binding_invalid")
        forgejo._branch(self.target_ref)
        c._integer(self.pull_number)
        c._require(type(self.candidate) is r.Candidate, "forgejo_check_candidate_invalid")


@dataclass(frozen=True, slots=True, repr=False)
class ExecutionReceipt:
    subject: Subject
    context: str
    status_id: int
    producer_digest: str
    invocation: r.Invocation
    executed: bool
    conclusion: str
    completed_at: datetime | None = None
    provider: str = "forgejo"


@dataclass(frozen=True, slots=True, repr=False)
class Execution:
    subject: Subject
    context: str
    producer_digest: str
    invocation: r.Invocation
    phase: str
    receipts: tuple[ExecutionReceipt, ...] = ()
    started_at: datetime | None = None


class ReceiptReader(Protocol):
    """The delivery owner supplies authenticated current execution and receipts."""

    def current_execution(self, subject: Subject, check: RequiredCheck) -> Execution | None: ...


@dataclass(frozen=True, slots=True, repr=False)
class CheckAssessment:
    context: str
    state: CheckState
    reason: str
    native_state: str | None = None
    status_id: int | None = None
    run_id: int | None = None
    attempt: int | None = None
    diagnostic_url: str | None = None
    created_at: datetime | None = None
    elapsed_seconds: int | None = None
    receipt: ExecutionReceipt | None = None
    progress_at: datetime | None = None


@dataclass(frozen=True, slots=True, repr=False)
class Assessment:
    subject: Subject
    state: CheckState
    reason: str
    checks: tuple[CheckAssessment, ...]
    observed_at: datetime | None
    problem_context: str | None = None


_FAILURE_STATES = ("failure", "error")
_STATE_ORDER: tuple[CheckState, ...] = ("failed", "stale", "unavailable", "running", "queued", "waiting", "passed")


def _utc(value: datetime | None) -> datetime | None:
    try:
        if isinstance(value, datetime) and value.utcoffset() is not None:
            return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        pass
    return None


def _elapsed(since: datetime | None, now: datetime) -> int | None:
    timestamp = _utc(since)
    return int((now - timestamp).total_seconds()) if timestamp is not None and timestamp <= now else None


def _assess_check(subject: Subject, check: RequiredCheck, status: forgejo_status.Status | None,
                  reader: ReceiptReader | None, now: datetime) -> CheckAssessment:
    result = CheckAssessment(check.context, "waiting", "required_status_missing")
    if status is None:
        return result
    result = replace(result, native_state=status.state, status_id=status.id, diagnostic_url=status.diagnostic_url,
                     created_at=status.created_at, elapsed_seconds=_elapsed(status.created_at, now))
    if status.creator_id != check.creator_id:
        return replace(result, state="unavailable", reason="native_creator_mismatch")
    if status.state not in ("pending", "success", *_FAILURE_STATES):
        return replace(result, state="unavailable", reason="native_status_not_qualifying")

    try:
        execution = reader.current_execution(subject, check) if reader is not None else None
    except (OSError, c.Invalid, c.Conflict, c.Unavailable, c.Ambiguous):
        return replace(result, state="unavailable", reason="execution_reader_unavailable")
    if execution is None:
        state: CheckState = "waiting" if status.state == "pending" else "unavailable"
        reason = "native_status_pending" if state == "waiting" else "execution_receipt_missing"
        return replace(result, state=state, reason=reason)
    if type(execution) is not Execution or execution.context != check.context or (
            execution.producer_digest != check.producer_digest or type(execution.invocation) is not r.Invocation):
        return replace(result, state="unavailable", reason="execution_identity_mismatch")
    if execution.subject != subject or execution.invocation.workflow_digest != check.definition_digest:
        return replace(result, state="stale", reason="execution_candidate_or_definition_changed")
    result = replace(result, run_id=execution.invocation.run_id, attempt=execution.invocation.attempt)
    if execution.phase in ("queued", "running"):
        if execution.receipts != ():
            return replace(result, state="unavailable", reason="execution_phase_conflict")
        phase: CheckState = "queued" if execution.phase == "queued" else "running"
        elapsed = _elapsed(execution.started_at, now)
        return replace(result, state=phase, reason="execution_" + phase, elapsed_seconds=elapsed,
                       progress_at=_utc(execution.started_at) if elapsed is not None else None)
    if execution.phase != "completed" or type(execution.receipts) is not tuple:
        return replace(result, state="unavailable", reason="execution_phase_unavailable")
    if status.state == "pending":
        return replace(result, reason="native_status_pending")
    if len(execution.receipts) != 1:
        reason = "execution_receipt_ambiguous" if execution.receipts else "execution_receipt_missing"
        return replace(result, state="unavailable", reason=reason)
    receipt = execution.receipts[0]
    if (type(receipt) is not ExecutionReceipt or receipt.provider != "forgejo" or receipt.context != check.context
            or receipt.producer_digest != check.producer_digest or type(receipt.status_id) is not int):
        return replace(result, state="unavailable", reason="execution_receipt_identity_mismatch")
    if receipt.subject != subject or receipt.status_id != status.id or receipt.invocation != execution.invocation:
        return replace(result, state="stale", reason="execution_receipt_subject_or_attempt_changed")
    started, completed = _utc(execution.started_at), _utc(receipt.completed_at)
    if ((execution.started_at is not None and (started is None or started > now))
            or (receipt.completed_at is not None and (completed is None or completed > now))
            or (started is not None and completed is not None and completed < started)):
        return replace(result, state="unavailable", reason="execution_receipt_time_invalid")
    if receipt.executed is not True or receipt.conclusion not in ("success", *_FAILURE_STATES):
        return replace(result, state="unavailable", reason="required_work_unproved")
    if status.state == receipt.conclusion == "success":
        return replace(result, state="passed", reason="required_check_passed", receipt=receipt)
    if status.state in _FAILURE_STATES and receipt.conclusion in _FAILURE_STATES:
        return replace(result, state="failed", reason="required_check_failed", receipt=receipt)
    return replace(result, state="unavailable", reason="native_and_receipt_outcomes_conflict")


def assess_ci(subject: Subject, plan: CheckPlan, transport: forgejo.Transport,
              reader: ReceiptReader | None, *, observed_at: datetime) -> Assessment:
    """Read the exact tested object's statuses and assess independently verified attempts."""
    now = _utc(observed_at)
    if now is None:
        raise c.Invalid("forgejo_observation_time_invalid")
    candidate = subject.candidate
    if (subject.binding != plan.binding or subject.target_ref != plan.target_ref
            or candidate.plan_digest != c.identity(plan) or candidate.policy_digest != plan.policy_digest
            or transport.binding != subject.binding):
        return Assessment(subject, "stale", "forgejo_check_plan_mismatch", (), None)

    try:
        statuses = forgejo_status.read_statuses(subject.binding, candidate.tested_oid, transport)
    except (OSError, c.Invalid, c.Conflict, c.Unavailable, c.Ambiguous):
        return Assessment(subject, "unavailable", "forgejo_statuses_unavailable", (), None)
    required = {check.context for check in plan.checks}
    latest: dict[str, forgejo_status.Status] = {}
    for status in statuses:
        prior = latest.get(status.context)
        if status.context in required and (prior is None or status.id > prior.id):
            latest[status.context] = status
    checks = tuple(_assess_check(subject, check, latest.get(check.context), reader, now) for check in plan.checks)
    leading = min(checks, key=lambda check: _STATE_ORDER.index(check.state))
    if leading.state == "passed":
        return Assessment(subject, "passed", "required_checks_passed", checks, now)
    return Assessment(subject, leading.state, leading.reason, checks, now, leading.context)



def initiative_observation(assessment: Assessment, *, read_at: int) -> initiative_ci.Observation:
    """Project existing qualified checks without widening merge or repair evidence."""
    candidate = initiative_ci.Candidate.exact(assessment.subject.candidate)
    check = next((row for row in assessment.checks if row.context == assessment.problem_context), None)
    if check is None:
        if assessment.state == "passed":
            return initiative_ci.Observation(candidate, "passed", assessment.reason, read_at)
        if assessment.state == "stale":
            return initiative_ci.Observation(candidate, "stale", assessment.reason, read_at, "stale")
        return initiative_ci.Observation(candidate, "unavailable", assessment.reason, read_at, "unavailable")

    context = check.context if check.context.isprintable() else None
    link = forgejo_status._diagnostic_url(check.diagnostic_url, assessment.subject.binding)
    if link is not None and len(link) > 512:
        link = None
    native = check.native_state
    if assessment.state == "failed":
        receipt = check.receipt
        if (receipt is None or receipt.subject != assessment.subject or receipt.context != check.context
                or receipt.provider != "forgejo" or receipt.status_id != check.status_id
                or receipt.executed is not True or receipt.conclusion not in _FAILURE_STATES
                or check.native_state not in _FAILURE_STATES
                or (receipt.invocation.run_id, receipt.invocation.attempt) != (check.run_id, check.attempt)
                or context is None):
            return initiative_ci.Observation(candidate, "unavailable", "required_failure_unproved",
                                             read_at, "untrusted", check=context, native_state=native)
        evidence = {"kind": "forgejo_initiative_failure", "subject": c.identity(receipt.subject),
                    "context": receipt.context, "status_id": receipt.status_id,
                    "producer": receipt.producer_digest, "invocation": c.identity(receipt.invocation),
                    "conclusion": receipt.conclusion,
                    "completed_at": receipt.completed_at.isoformat() if receipt.completed_at else None}
        failure = sha256(c._canonical(evidence)).hexdigest()
        return initiative_ci.Observation(candidate, "failed", assessment.reason, read_at, check=context,
                                         run_id=check.run_id, attempt=check.attempt, diagnostic_url=link,
                                         failure_digest=failure, native_state=native)
    if assessment.state == "stale":
        return initiative_ci.Observation(candidate, "stale", assessment.reason, read_at, "stale",
                                         check=context, native_state=native)
    if assessment.state == "unavailable":
        outcome: initiative_ci.ReadOutcome = ("unavailable" if assessment.reason == "execution_reader_unavailable"
                                               else "untrusted")
        return initiative_ci.Observation(candidate, "unavailable", assessment.reason, read_at, outcome,
                                         check=context, native_state=native)

    if assessment.state == "waiting":
        state: initiative_ci.State = "missing" if check.status_id is None else "pending"
    else:
        state = assessment.state
    progress_at = int(check.progress_at.timestamp()) if check.progress_at is not None else None
    if progress_at is not None and not 0 <= progress_at <= read_at:
        progress_at = None
    return initiative_ci.Observation(candidate, state, assessment.reason, read_at, check=context,
                                     run_id=check.run_id, attempt=check.attempt, native_progress_at=progress_at,
                                     diagnostic_url=link, native_state=native)
