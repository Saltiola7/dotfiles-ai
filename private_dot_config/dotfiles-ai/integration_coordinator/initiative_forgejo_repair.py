"""Use the enrolled Forgejo CI producer for a fenced same-source retry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Protocol

from . import core, forgejo_ci as ci, initiative_authority as authority, initiative_ci as telemetry
from . import initiative_controller as controller, initiative_forgejo as forgejo, initiative_repair as repair
from . import lifecycle, runtime

if TYPE_CHECKING:
    from .initiative_service import RuntimeRecipe

_OUTCOME_FIELDS = frozenset({
    "schema_version", "request_digest", "candidate", "subject_digest", "context", "status_id",
    "producer_digest", "conclusion", "completed_at", "predecessor", "successor",
})
_INVOCATION_FIELDS = frozenset({"run_id", "attempt", "invocation_id", "workflow_digest"})
_FAILED = frozenset({"failure", "error"})


class RetryPorts(Protocol):
    def retry_qualification(self) -> str | None: ...

    def retry_correction(self, activation: controller.Activation, failure: repair.Failure) -> str | None: ...

    def retry_verify(self, activation: controller.Activation, request: repair.Request) -> bool: ...

    def retry_submit(self, activation: controller.Activation, request: repair.Request,
                     expires_at: str) -> dict | None: ...

    def retry_readback(self, activation: controller.Activation, request: repair.Request) -> dict | None: ...


def _invocation(raw: object) -> runtime.Invocation:
    fields = lifecycle.object_value(raw)
    if fields.keys() != _INVOCATION_FIELDS:
        raise core.Invalid("initiative_forgejo_retry_invocation_invalid")
    run_id, attempt = fields["run_id"], fields["attempt"]
    if type(run_id) is not int or type(attempt) is not int:
        raise core.Invalid("initiative_forgejo_retry_invocation_invalid")
    return runtime.Invocation(run_id, attempt, lifecycle.text(fields["invocation_id"]),
                              lifecycle.text(fields["workflow_digest"]))


class ForgejoRetry:
    """A single qualified infrastructure retry, behind the shared Recovery owner."""

    def __init__(self, custody: lifecycle.Custody, delivery: forgejo.FixtureDelivery,
                 ports: RetryPorts, clock: Callable[[], str]) -> None:
        self.custody, self.delivery, self.ports, self.clock = custody, delivery, ports, clock
        fixture = delivery.fixture
        self.target = controller.Target(fixture.binding.origin, fixture.binding.repository, fixture.target_ref)

    def qualifications(self, recipe: RuntimeRecipe, snapshot: dict) -> dict[str, str]:
        if recipe.forgejo != self.delivery.fixture or recipe.repair_policy is None:
            return {}
        expected = recipe.repair_policy["class_qualifications"].get(repair.INFRASTRUCTURE)
        if expected is None or any(snapshot["slices"][key]["repository"] != self.delivery.fixture.repository
                                   for key in snapshot["selected"]):
            return {}
        if self.ports.retry_qualification() != expected:
            return {}
        core._digest(expected)
        return {repair.INFRASTRUCTURE: expected}

    def _assessment(self, activation: controller.Activation, admission: controller.Admission,
                    now: datetime) -> ci.Assessment | None:
        core._require(activation.managed and activation.target == self.target
                      and (admission.activation_id, admission.target) == (activation.activation_id, self.target),
                      "initiative_forgejo_retry_admission_changed")
        assessment = self.delivery.retry_assessment(activation, admission, observed_at=now)
        if assessment is None:
            return None
        subject = assessment.subject
        fixture = self.delivery.fixture
        core._require(subject.binding == fixture.binding and subject.target_ref == fixture.target_ref
                      and subject.candidate.plan_digest == core.identity(fixture.plan)
                      and subject.candidate.policy_digest == fixture.plan.policy_digest
                      and subject.candidate.tested_oid == subject.candidate.head,
                      "initiative_forgejo_retry_subject_changed")
        return assessment

    def _failure(self, admission: controller.Admission, assessment: ci.Assessment,
                 row: ci.CheckAssessment, read_at: int) -> repair.Failure | None:
        receipt = row.receipt
        if row.state != "failed" or receipt is None:
            return None
        check = next((item for item in self.delivery.fixture.plan.checks if item.context == row.context), None)
        if (check is None or receipt.producer_digest != check.producer_digest
                or receipt.invocation.workflow_digest != check.definition_digest):
            return None
        proof = ci.initiative_observation(replace(assessment, state="failed", problem_context=row.context),
                                          read_at=read_at)
        if proof.failure_digest is None or proof.candidate is None:
            return None
        return repair.Failure(admission.obligation_handle, admission.ticket_handle, proof.candidate,
                              proof.failure_digest, check.producer_digest, check.definition_digest,
                              core.identity(receipt.invocation), receipt.invocation.attempt)

    def failure(self, activation: controller.Activation, admission: controller.Admission,
                observation: telemetry.Observation) -> repair.Failure | None:
        if observation.state != "failed" or observation.read_outcome != "verified":
            return None
        now = lifecycle.initiative_time(self.clock())
        assessment = self._assessment(activation, admission, now)
        if assessment is None:
            return None
        for row in assessment.checks:
            if row.context != observation.check:
                continue
            proof = self._failure(admission, assessment, row, int(now.timestamp()))
            if proof is not None and proof.matches(observation):
                return proof
        return None

    def correction(self, activation: controller.Activation, failure: repair.Failure,
                   approved_classes: frozenset[str]) -> repair.Correction | None:
        if repair.INFRASTRUCTURE not in approved_classes or not activation.managed or activation.target != self.target:
            return None
        proof = self.ports.retry_correction(activation, failure)
        return None if proof is None else repair.Correction(repair.INFRASTRUCTURE, proof)

    def _grant(self, activation: controller.Activation, request: repair.Request) -> dict:
        fixture = self.delivery.fixture
        core._require(activation.managed and activation.target == self.target
                      and (request.grant_id, request.activation_id, request.slice_id)
                      == (activation.grant_id, activation.activation_id, activation.slice_id)
                      and request.correction.kind == repair.INFRASTRUCTURE and not request.correction.writable_paths,
                      "initiative_forgejo_retry_request_unbound")
        proposal, snapshot = authority.read_grant(self.custody, activation.grant_id)
        binding = proposal["binding"]
        core._require(proposal["schema_version"] == 2 and proposal["repair_limit"] == 1
                      and "repair" in proposal["allowed_operations"] and activation.slice_id in snapshot["selected"]
                      and binding["repository"] == fixture.repository and binding["target_ref"] == fixture.target_ref
                      and binding["root_oid"] == fixture.root_oid and binding["policy_digest"] == fixture.plan.policy_digest
                      and binding["enrollment_digest"] == fixture.digest
                      and binding["controller_digest"] == activation.controller_digest
                      and binding["writer_digest"] == activation.writer_digest,
                      "initiative_forgejo_retry_grant_unbound")
        authority._require_repair(proposal, activation.slice_id, 1, request.correction.kind,
                                  request.qualification_digest, request.correction.writable_paths)
        return proposal

    def _active(self, request: repair.Request, proposal: dict) -> str:
        now = lifecycle.initiative_time(self.clock())
        if self.custody.optional_link("initiative_revocation", request.grant_id) is not None:
            raise core.Unavailable("initiative_grant_revoked")
        expires_at = lifecycle.timestamp(proposal["expires_at"])
        if not lifecycle.initiative_time(proposal["approved_at"]) <= now < lifecycle.initiative_time(expires_at):
            raise core.Unavailable("initiative_grant_inactive")
        return expires_at

    def verify(self, activation: controller.Activation, request: repair.Request) -> bool:
        self._active(request, self._grant(activation, request))
        admission = self.delivery.observe_admission(activation)
        if admission is None:
            raise core.Unavailable("initiative_forgejo_retry_admission_unavailable")
        if (admission.obligation_handle, admission.ticket_handle) != (
                request.failure.obligation, request.failure.predecessor):
            return False
        now = lifecycle.initiative_time(self.clock())
        assessment = self._assessment(activation, admission, now)
        if assessment is None or assessment.observed_at is None:
            raise core.Unavailable("initiative_forgejo_retry_predecessor_unavailable")
        if telemetry.Candidate.exact(assessment.subject.candidate) != request.failure.candidate:
            return False
        if any(self._failure(admission, assessment, row, int(now.timestamp())) == request.failure
               for row in assessment.checks):
            return self.ports.retry_verify(activation, request)
        if assessment.state in {"unavailable", "stale", "waiting"} or any(
                row.state in {"unavailable", "stale", "waiting"} for row in assessment.checks):
            raise core.Unavailable("initiative_forgejo_retry_predecessor_unavailable")
        return False

    def _require_claim(self, request: repair.Request) -> None:
        from .initiative_evidence import Evidence
        from .initiative_service import open_execution

        retained = Evidence(open_execution(self.custody)).reservation(request.grant_id)
        if retained is None or retained.request != request or retained.state != "claimed":
            raise core.Conflict("initiative_forgejo_retry_claim_unbound")

    def submit(self, activation: controller.Activation, request: repair.Request) -> str | None:
        proposal = self._grant(activation, request)
        self._require_claim(request)
        expires_at = self._active(request, proposal)
        outcome = self.ports.retry_submit(activation, request, expires_at)
        return self._outcome(activation, request, outcome)

    def reconcile(self, activation: controller.Activation, request: repair.Request) -> str | None:
        self._grant(activation, request)
        self._require_claim(request)
        outcome = self.ports.retry_readback(activation, request)
        return self._outcome(activation, request, outcome)

    def _outcome(self, activation: controller.Activation, request: repair.Request,
                 raw: dict | None) -> str | None:
        if raw is None:
            return None
        fields = lifecycle.object_value(raw)
        failure = request.failure
        core._require(fields.keys() == _OUTCOME_FIELDS and type(fields["schema_version"]) is int
                      and fields["schema_version"] == 1 and fields["request_digest"] == core.identity(request)
                      and lifecycle.canonical(fields["candidate"]) == lifecycle.canonical(asdict(failure.candidate)),
                      "initiative_forgejo_retry_outcome_unbound")
        predecessor, successor = _invocation(fields["predecessor"]), _invocation(fields["successor"])
        context = lifecycle.text(fields["context"], 512)
        check = next((entry for entry in self.delivery.fixture.plan.checks if entry.context == context), None)
        status_id = fields["status_id"]
        if type(status_id) is not int:
            raise core.Invalid("initiative_forgejo_retry_outcome_status_invalid")
        core._integer(status_id)
        core._digest(fields["subject_digest"])
        core._require(check is not None and fields["producer_digest"] == check.producer_digest == failure.producer_digest
                      and predecessor.workflow_digest == successor.workflow_digest == check.definition_digest
                      == failure.definition_digest and core.identity(predecessor) == failure.invocation_digest
                      and predecessor.attempt == failure.attempt and successor.attempt == predecessor.attempt + 1
                      and successor.run_id == predecessor.run_id and successor.invocation_id != predecessor.invocation_id
                      and lifecycle.text(fields["conclusion"]) in _FAILED,
                      "initiative_forgejo_retry_outcome_identity_changed")
        completed = fields["completed_at"]
        if completed is not None:
            core._require(datetime.fromisoformat(lifecycle.text(completed)).utcoffset() is not None,
                          "initiative_forgejo_retry_outcome_time_invalid")
        failure_digest = sha256(core._canonical({
            "kind": "forgejo_initiative_failure", "subject": fields["subject_digest"], "context": context,
            "status_id": status_id, "producer": failure.producer_digest, "invocation": core.identity(predecessor),
            "conclusion": fields["conclusion"], "completed_at": completed,
        })).hexdigest()
        core._require(failure_digest == failure.receipt_digest, "initiative_forgejo_retry_predecessor_changed")
        admission = self.delivery.observe_admission(activation)
        if admission is None or (admission.obligation_handle, admission.ticket_handle) != (
                failure.obligation, failure.predecessor):
            return None
        assessment = self._assessment(activation, admission, lifecycle.initiative_time(self.clock()))
        if assessment is None or core.identity(assessment.subject) != fields["subject_digest"]:
            return None
        assert check is not None
        actual = next((row for row in assessment.checks if row.context == check.context), None)
        if (actual is None or actual.state not in {"queued", "running", "passed", "failed"}
                or (actual.run_id, actual.attempt) != (successor.run_id, successor.attempt)
                or type(actual.status_id) is not int or actual.status_id <= status_id):
            return None
        execution = self.delivery.ports.current_execution(assessment.subject, check)
        if (type(execution) is not ci.Execution or execution.phase not in {"queued", "running", "completed"}
                or (execution.subject, execution.context, execution.producer_digest, execution.invocation)
                != (assessment.subject, check.context, check.producer_digest, successor)):
            return None
        return lifecycle.digest(fields)
