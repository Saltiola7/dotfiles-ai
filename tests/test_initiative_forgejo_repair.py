"""Exercise Forgejo retry against exact native evidence and the real Recovery journal."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from test_initiative_forgejo import Fixture, fixture_document
from integration_coordinator import core, forgejo_ci, initiative_ci, lifecycle, runtime
from integration_coordinator import initiative_authority as authority, initiative_controller as controller
from integration_coordinator import initiative_forgejo as forgejo, initiative_repair as recovery
from integration_coordinator.initiative_evidence import Evidence
from integration_coordinator.initiative_forgejo_repair import ForgejoRetry
from integration_coordinator.initiative_service import open_execution


NOW = "2026-01-02T11:01:00Z"
EXPIRES = "2026-01-02T11:10:00Z"
POLICY = initiative_ci.Policy(60, 5, 60, 600)
QUALIFY = "1" * 64
CORRECTED = "2" * 64


class Producer:
    def __init__(self, subject, check):
        self.subject = subject
        self.check = check
        self.predecessor = runtime.Invocation(subject.pull_number, 1, "3" * 32, check.definition_digest)
        done = datetime(2026, 1, 2, 11, tzinfo=UTC)
        self.old_receipt = forgejo_ci.ExecutionReceipt(subject, check.context, 41, check.producer_digest,
                                                       self.predecessor, True, "failure", done)
        self.successor = replace(self.predecessor, attempt=2, invocation_id="4" * 32)
        self.row = self.assessment_row(self.old_receipt, "failed")
        self.native_execution = self.execution(self.old_receipt)
        self.qualification = QUALIFY
        self.correction = CORRECTED
        self.verified = True
        self.response = None
        self.submit_calls = []
        self.readback_calls = []
        self.verify_calls = []
        self.lose_reply = False

    def assessment_row(self, receipt, state):
        return forgejo_ci.CheckAssessment(self.check.context, state, "required_check_" + state,
                                         native_state=receipt.conclusion, status_id=receipt.status_id,
                                         run_id=receipt.invocation.run_id, attempt=receipt.invocation.attempt,
                                         receipt=receipt)

    def execution(self, receipt):
        return forgejo_ci.Execution(self.subject, self.check.context, self.check.producer_digest,
                                    receipt.invocation, "completed", (receipt,))

    def assess(self, activation, admission, *, observed_at):
        assert admission.activation_id == activation.activation_id
        return forgejo_ci.Assessment(self.subject, self.row.state, self.row.reason, (self.row,), observed_at,
                                     self.row.context if self.row.state != "passed" else None)

    def retry_qualification(self):
        return self.qualification

    def retry_correction(self, activation, failure):
        return self.correction

    def retry_verify(self, activation, request):
        self.verify_calls.append((activation, request))
        return self.verified

    def retry_submit(self, activation, request, expires_at):
        self.submit_calls.append((activation, request, expires_at))
        if self.lose_reply:
            raise core.Ambiguous("fixture_reply_lost")
        return self.response

    def retry_readback(self, activation, request):
        self.readback_calls.append((activation, request))
        return self.response

    def current_execution(self, subject, check):
        assert (subject, check) == (self.subject, self.check)
        return self.native_execution

    def publish(self):
        receipt = replace(self.old_receipt, status_id=42, invocation=self.successor, conclusion="success")
        self.row = self.assessment_row(receipt, "passed")
        self.native_execution = self.execution(receipt)

    def outcome(self, request):
        original = self.old_receipt
        return {
            "schema_version": 1, "request_digest": core.identity(request), "candidate": asdict(request.failure.candidate),
            "subject_digest": core.identity(self.subject), "context": original.context, "status_id": original.status_id,
            "producer_digest": original.producer_digest, "conclusion": original.conclusion,
            "completed_at": original.completed_at.isoformat(), "predecessor": asdict(self.predecessor),
            "successor": asdict(self.successor),
        }


@pytest.fixture
def route(tmp_path, monkeypatch):
    common = tmp_path / ".git"
    common.mkdir()
    custody = lifecycle.Custody(common)
    native = Fixture()
    fixture = forgejo.parse_fixture(fixture_document(native))
    subject = native.intent.subject
    producer = Producer(subject, fixture.plan.checks[0])
    target = controller.Target(fixture.binding.origin, fixture.binding.repository, fixture.target_ref)
    snapshot = {
        "schema_version": 1, "initiative_id": "forgejo-retry-test", "source_commit": fixture.root_oid,
        "manifest_path": "docs/initiatives/forgejo-retry-test/MANIFEST.json",
        "selected": ["first", "second"],
        "slices": {
            "first": {"scope_digest": "5" * 64, "depends_on": [], "repository": fixture.repository, "clear": True},
            "second": {"scope_digest": "6" * 64, "depends_on": ["first"], "repository": fixture.repository, "clear": True},
        },
    }
    binding = {
        "repository": fixture.repository, "target_ref": fixture.target_ref, "root_oid": fixture.root_oid,
        "enrollment_digest": fixture.digest, "policy_digest": fixture.plan.policy_digest,
        "controller_digest": "7" * 64, "writer_digest": "8" * 64, "qualification_digest": "9" * 64,
    }
    enrolled = {"class_qualifications": {recovery.INFRASTRUCTURE: QUALIFY}, "writable_paths": {}}
    proposal = authority.grant_proposal(
        snapshot, binding=binding, operator_id="forgejo-actor-1", approved_at="2026-01-02T10:00:00Z", expires_at=EXPIRES,
        allowed_operations=("launch", "admit", "merge", "repair"), repair_limit=1, ci_policy=POLICY, repair_policy=enrolled,
    )
    grant = authority.store_grant(custody, snapshot, proposal, expected_approval_digest=lifecycle.digest(proposal))
    approval = controller.Approval(grant, target, binding["controller_digest"], binding["writer_digest"],
                                   (controller.Slice("first"), controller.Slice("second", ("first",))))
    launch = controller.Launch("a" * 64, subject.candidate.base, str(tmp_path), "RETRY-A", "build")
    activation = controller.Activation.from_launch(approval, "first", launch, managed=True)
    admission = controller.Admission(activation.activation_id, target, "b" * 32, "c" * 32, "d" * 64)
    registration = controller.RegistrationReceipt(activation.activation_id, launch.cycle_id, launch.launch_digest,
                                                   "e" * 64)
    store = open_execution(custody, create=True)
    assert store._reserve(activation)
    for state in ("session_claimed", "session_ready", "dispatch_claimed", "held", "registration_claimed",
                  "registered", "release_claimed", "release_accepted", "dispatched", "admitted"):
        prior = store.execution(grant, activation.slice_id)
        proof = {"registered": registration, "admitted": admission}.get(state)
        assert store._append(prior, state, proof)
    evidence = Evidence(store)
    evidence.initialize()
    execution = store.execution(grant, activation.slice_id)

    def forbidden(*args):
        pytest.fail("retry used a writer or an unrelated authority")

    delivery = forgejo.FixtureDelivery(custody, fixture, producer, forbidden, forbidden)
    monkeypatch.setattr(delivery, "retry_assessment", producer.assess)
    monkeypatch.setattr(delivery, "observe_admission", lambda activation: admission)
    clock = {"now": NOW}
    actual = ForgejoRetry(custody, delivery, producer, lambda: clock["now"])
    assessment = producer.assess(activation, admission, observed_at=lifecycle.initiative_time(NOW))
    observation = forgejo_ci.initiative_observation(assessment, read_at=int(assessment.observed_at.timestamp()))
    assert observation.state == "failed"
    failure = actual.failure(activation, admission, observation)
    assert failure and failure.matches(observation)
    repair = actual.correction(activation, failure, frozenset({recovery.INFRASTRUCTURE}))
    assert repair
    request = recovery.Request(grant, activation.activation_id, activation.slice_id, failure, repair, QUALIFY)
    producer.response = producer.outcome(request)
    evidence.observe(activation, None, initiative_ci.advance(None, observation, POLICY))
    return SimpleNamespace(
        actual=actual, evidence=evidence, execution=execution, activation=activation, admission=admission,
        observation=observation, request=request, producer=producer, proposal=proposal,
        recipe=SimpleNamespace(forgejo=fixture, repair_policy=enrolled), snapshot=snapshot, clock=clock,
    )


def claim(route):
    assert route.evidence.reserve(route.request)
    route.evidence.claim(route.request)


def test_qualifies_only_explicitly_enrolled_exact_infrastructure_route(route):
    assert route.actual.qualifications(route.recipe, route.snapshot) == {recovery.INFRASTRUCTURE: QUALIFY}
    assert route.actual.correction(route.activation, route.request.failure, frozenset({recovery.SOURCE})) is None
    route.producer.qualification = "f" * 64
    assert route.actual.qualifications(route.recipe, route.snapshot) == {}
    assert route.actual.failure(route.activation, route.admission,
                                replace(route.observation, failure_digest="f" * 64)) is None


def test_effect_requires_a_claim_and_live_original_grant(route):
    assert route.actual.verify(route.activation, route.request)
    with pytest.raises(core.Conflict, match="initiative_forgejo_retry_claim_unbound"):
        route.actual.submit(route.activation, route.request)
    claim(route)
    route.clock["now"] = EXPIRES
    with pytest.raises(core.Unavailable, match="initiative_grant_inactive"):
        route.actual.submit(route.activation, route.request)
    assert route.producer.submit_calls == []


def test_recovery_reconciles_lost_submit_after_expiry_without_another_effect(route):
    owner = recovery.Recovery(route.actual.custody, route.evidence, route.actual, lambda *_args: None)
    route.producer.lose_reply = True
    with pytest.raises(core.Ambiguous, match="fixture_reply_lost"):
        owner.advance(route.execution, route.observation, route.proposal)
    assert route.evidence.reservation(route.request.grant_id).state == "claimed"
    assert route.producer.submit_calls == [(route.activation, route.request, EXPIRES)]
    route.clock["now"] = EXPIRES
    pending = owner.advance(route.execution, route.observation, route.proposal)
    assert pending.reason == "initiative_repair_effect_unresolved"
    route.producer.publish()
    done = owner.advance(route.execution, route.observation, route.proposal)
    assert done.reason == "initiative_repair_effect_verified"
    assert route.evidence.reservation(route.request.grant_id).state == "settled"
    assert route.evidence.snapshot(route.request.grant_id).repair_used == 1
    assert len(route.producer.submit_calls) == 1
    assert len(route.producer.readback_calls) == 2


def test_revocation_closes_submit_but_permits_exact_readback(route):
    claim(route)
    authority.revoke_grant(route.actual.custody, route.request.grant_id, reason_digest="f" * 64, revoked_at=NOW)
    with pytest.raises(core.Unavailable, match="initiative_grant_revoked"):
        route.actual.submit(route.activation, route.request)
    route.producer.publish()
    assert route.actual.reconcile(route.activation, route.request) == lifecycle.digest(route.producer.response)
    assert not route.producer.submit_calls
    assert route.producer.readback_calls == [(route.activation, route.request)]


@pytest.mark.parametrize("change", ["candidate", "producer", "request", "definition", "attempt", "context", "status"])
def test_readback_rejects_rebound_or_stale_producer_receipts(route, change):
    claim(route)
    route.producer.publish()
    response = route.producer.response
    if change == "candidate":
        response["candidate"]["head"] = "d" * 40
    elif change == "producer":
        response["producer_digest"] = "d" * 64
    elif change == "request":
        response["request_digest"] = "d" * 64
    elif change == "definition":
        response["successor"]["workflow_digest"] = "d" * 64
    elif change == "attempt":
        response["successor"]["attempt"] += 1
    elif change == "context":
        response["context"] = "Other required check"
    else:
        response["status_id"] += 1
    with pytest.raises((core.Invalid, core.Conflict), match="initiative_forgejo_retry_"):
        route.actual.reconcile(route.activation, route.request)
    assert not route.producer.submit_calls


def test_new_native_status_and_independent_invocation_are_both_required(route):
    claim(route)
    route.producer.publish()
    successor = route.producer.native_execution
    assert successor.invocation == route.producer.successor
    route.producer.row = replace(route.producer.row, status_id=route.producer.old_receipt.status_id)
    assert route.actual.reconcile(route.activation, route.request) is None
    route.producer.row = replace(route.producer.row, status_id=42)
    route.producer.native_execution = replace(successor, invocation=replace(successor.invocation, invocation_id="a" * 32))
    assert route.actual.reconcile(route.activation, route.request) is None
    route.producer.native_execution = successor
    assert route.actual.reconcile(route.activation, route.request) == lifecycle.digest(route.producer.response)


def test_known_predecessor_change_stops_even_if_producer_offers_a_retry(route):
    route.producer.publish()
    assert route.actual.verify(route.activation, route.request) is False
    assert not route.producer.verify_calls
    assert not route.producer.submit_calls
