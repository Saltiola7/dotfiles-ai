"""Fence one native Initiative repair across the approved slice set."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Protocol

from . import core, initiative_ci as ci, initiative_controller as controller
from .initiative_evidence import Evidence, Reservation
from .initiative_authority import initiative_effect_lock
from .lifecycle import Custody, digest

if TYPE_CHECKING:
    from .initiative_service import RuntimeRecipe


SOURCE = "source_fix"
INFRASTRUCTURE = "infrastructure_retry"
CLASSES = (SOURCE, INFRASTRUCTURE)

_FINAL_REFUSALS = frozenset({
    "initiative_grant_inactive", "initiative_grant_revoked", "initiative_qualification_changed",
    "initiative_material_changed", "initiative_repair_paths_unapproved", "initiative_repair_candidate_changed",
    "initiative_repair_qualification_changed",
})


@dataclass(frozen=True, slots=True)
class Failure:
    """Authenticated current failed predecessor, with its independently bound CI proof."""

    obligation: str
    predecessor: str
    candidate: ci.Candidate
    receipt_digest: str
    producer_digest: str
    definition_digest: str
    invocation_digest: str
    attempt: int

    def __post_init__(self) -> None:
        for value in (self.obligation, self.predecessor):
            core._handle(value)
        for value in (self.receipt_digest, self.producer_digest, self.definition_digest, self.invocation_digest):
            core._digest(value)
        core._require(type(self.candidate) is ci.Candidate and type(self.attempt) is int and self.attempt >= 1,
                      "initiative_repair_failure_invalid")

    def matches(self, observation: ci.Observation) -> bool:
        return (observation.state, observation.read_outcome, observation.candidate,
                observation.failure_digest, observation.attempt) == (
                    "failed", "verified", self.candidate, self.receipt_digest, self.attempt)


@dataclass(frozen=True, slots=True)
class Correction:
    """Proof of an exact writable change or a verified infrastructure correction."""

    kind: str
    proof_digest: str
    writable_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        core._digest(self.proof_digest)
        core._tuple(self.writable_paths, str, 256)
        core._require(self.kind in CLASSES and bool(self.writable_paths) == (self.kind == SOURCE)
                      and len(self.writable_paths) == len(set(self.writable_paths)),
                      "initiative_repair_correction_invalid")


@dataclass(frozen=True, slots=True)
class Request:
    grant_id: str
    activation_id: str
    slice_id: str
    failure: Failure
    correction: Correction
    qualification_digest: str

    def __post_init__(self) -> None:
        for value in (self.grant_id, self.activation_id, self.qualification_digest):
            core._digest(value)
        controller._identifier(self.slice_id)
        core._require(type(self.failure) is Failure and type(self.correction) is Correction,
                      "initiative_repair_request_invalid")

    @classmethod
    def load(cls, value: dict) -> Request:
        fields = dict(value)
        failure = dict(fields.pop("failure"))
        failure["candidate"] = ci.Candidate(**failure["candidate"])
        correction = dict(fields.pop("correction"))
        correction["writable_paths"] = tuple(correction["writable_paths"])
        return cls(failure=Failure(**failure), correction=Correction(**correction), **fields)


class Route(Protocol):
    """A provider's enrolled repair implementation, independent from diagnostic red labels."""

    def qualifications(self, recipe: RuntimeRecipe, snapshot: dict) -> dict[str, str]:
        """Present live fingerprints for the qualified classes on this exact target."""
        ...

    def failure(self, activation: controller.Activation, admission: controller.Admission,
                observation: ci.Observation) -> Failure | None:
        """Verify the current exact failed predecessor, native run and independent evidence."""
        ...

    def correction(self, activation: controller.Activation, failure: Failure,
                   approved_classes: frozenset[str]) -> Correction | None:
        """Read-only proof; raise initiative_repair_correction_ambiguous for unclear changes."""
        ...

    def verify(self, activation: controller.Activation, request: Request) -> bool:
        """Verify the current fence. False proves change. Unavailable evidence raises."""
        ...

    def submit(self, activation: controller.Activation, request: Request) -> str | None:
        """Apply the inherited repair or same-source retry with a native exact-subject fence."""
        ...

    def reconcile(self, activation: controller.Activation, request: Request) -> str | None:
        """Read verified native outcome. Unknown leaves the effect claim in place."""
        ...


class Recovery:
    """Reserve before dispatch and never submit a claimed request a second time."""

    def __init__(self, custody: Custody, evidence: Evidence, route: Route | None,
                 authorize: Callable[[controller.Activation, Request], None]) -> None:
        self.custody, self.evidence, self.route, self.authorize = custody, evidence, route, authorize

    @staticmethod
    def _report(activation: controller.Activation, state: str, reason: str) -> controller.Report:
        return controller.Report(state, activation.slice_id, activation.activation_id, reason)

    def advance(self, execution: controller.Execution, observation: ci.Observation | None, proposal: dict
                ) -> controller.Report | None:
        activation, admission = execution.activation, execution.admission
        if admission is None:
            return None
        retained = self.evidence.reservation(activation.grant_id)
        if retained is not None and retained.request.activation_id == activation.activation_id:
            if retained.state != "settled":
                return self._continue(activation, retained)
        if observation is None or observation.state != "failed" or observation.read_outcome != "verified":
            return None
        if retained is not None:
            return self._report(activation, "blocked", "initiative_repair_budget_spent")
        policy = proposal.get("repair_policy")
        if proposal["repair_limit"] == 0 or policy is None:
            return self._report(activation, "blocked", "initiative_repair_unapproved")
        if self.route is None:
            return self._report(activation, "blocked", "initiative_repair_capability_unavailable")
        if observation.failure_digest is None:
            return self._report(activation, "admitted", "initiative_repair_failure_unproved")
        failure = self.route.failure(activation, admission, observation)
        if failure is None or not failure.matches(observation) or (
                failure.obligation, failure.predecessor) != (admission.obligation_handle, admission.ticket_handle):
            return self._report(activation, "admitted", "initiative_repair_failure_unproved")
        classes = policy["class_qualifications"]
        correction = self.route.correction(activation, failure, frozenset(classes))
        if correction is None or correction.kind not in classes:
            return self._report(activation, "blocked", "initiative_repair_correction_unproved")
        request = Request(activation.grant_id, activation.activation_id, activation.slice_id, failure, correction,
                          classes[correction.kind])
        with initiative_effect_lock(self.custody, activation.grant_id):
            self._require_current(activation, request)
            self.evidence.reserve(request)
            return self._submit(activation, request)

    def _require_current(self, activation: controller.Activation, request: Request) -> None:
        if self.route is None or self.route.verify(activation, request) is not True:
            raise core.Unavailable("initiative_repair_candidate_changed")
        self.authorize(activation, request)

    def _submit(self, activation: controller.Activation, request: Request) -> controller.Report:
        try:
            self._require_current(activation, request)
            self.evidence.claim(request)
        except (core.Unavailable, core.Conflict, ValueError) as error:
            if str(error) in _FINAL_REFUSALS:
                self._settle_before_submission(request, str(error), claimed=False)
            raise
        try:
            self.authorize(activation, request)
        except (core.Unavailable, core.Conflict, OSError, ValueError) as error:
            reason = str(error) if str(error) in _FINAL_REFUSALS else "initiative_repair_authority_unavailable"
            self._settle_before_submission(request, reason, claimed=True)
            raise
        assert self.route is not None
        return self._record(activation, request, self.route.submit(activation, request))

    def _settle_before_submission(self, request: Request, reason: str, *, claimed: bool) -> None:
        outcome = digest({"kind": "unsubmitted_repair", "request": asdict(request), "reason": reason})
        self.evidence.settle(request, outcome, submitted=claimed)

    def _continue(self, activation: controller.Activation, retained: Reservation) -> controller.Report:
        if self.route is None:
            return self._report(activation, "blocked", "initiative_repair_capability_unavailable")
        request = retained.request
        if retained.state == "claimed":
            return self._record(activation, request, self.route.reconcile(activation, request))
        with initiative_effect_lock(self.custody, activation.grant_id):
            fresh = self.evidence.reservation(activation.grant_id)
            if fresh != retained:
                return self._report(activation, "reconciling", "initiative_repair_reservation_changed")
            return self._submit(activation, request)

    def _record(self, activation: controller.Activation, request: Request, outcome: str | None) -> controller.Report:
        if outcome is None:
            return self._report(activation, "reconciling", "initiative_repair_effect_unresolved")
        self.evidence.settle(request, outcome)
        return self._report(activation, "reconciling", "initiative_repair_effect_verified")
