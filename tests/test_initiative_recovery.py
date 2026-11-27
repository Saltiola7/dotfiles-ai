"""Verify grant-wide repair reservations across processes, candidates and effects."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from test_integration_initiative_controller import setup, digest, oid
from integration_coordinator import core, initiative_ci as ci, initiative_controller as controller
from integration_coordinator import initiative_repair as repair
from integration_coordinator.initiative_evidence import Evidence
from integration_coordinator.lifecycle import Custody


POLICY = ci.Policy(300, 5, 60, 3600)


def admitted(run, writer, provider):
    grant = digest(1)
    assert run.advance(grant).state == "session_ready"
    assert run.advance(grant).state == "dispatched"
    activation = writer.created[-1]
    provider.admit(activation)
    assert run.advance(grant).state == "admitted"
    execution = run.store.execution(grant, activation.slice_id)
    assert execution is not None and execution.admission is not None
    return execution


def subject(execution, *, generation=4, kind=repair.SOURCE):
    activation, admission = execution.activation, execution.admission
    candidate = ci.Candidate(generation, oid(10), oid(11), oid(12), digest(13))
    observation = ci.Observation(candidate, "failed", "required_ci_failed", 1000, check="Required CI",
                                 run_id=41, attempt=2, failure_digest=digest(14))
    failure = repair.Failure(admission.obligation_handle, admission.ticket_handle, candidate, digest(14),
                             digest(15), digest(16), digest(17), 2)
    paths = ("src/component.py",) if kind == repair.SOURCE else ()
    correction = repair.Correction(kind, digest(18), paths)
    request = repair.Request(activation.grant_id, activation.activation_id, activation.slice_id,
                             failure, correction, digest(19))
    return observation, request


def record(evidence, execution, observed):
    activation = execution.activation
    previous = evidence.telemetry(activation.activation_id)
    evidence.observe(activation, previous, ci.advance(previous, observed, POLICY))


class NativeRepair:
    def __init__(self, request, evidence):
        self.request, self.evidence = request, evidence
        self.current = True
        self.lost_reply = False
        self.effect = []
        self.outcome = None

    def failure(self, activation, admission, observation):
        return self.request.failure

    def correction(self, activation, failure, approved_classes):
        assert self.request.correction.kind in approved_classes
        return self.request.correction

    def verify(self, activation, request):
        assert request == self.request
        return self.current

    def submit(self, activation, request):
        assert self.evidence.reservation(activation.grant_id).state == "claimed"
        self.effect.append(request)
        self.outcome = digest(99)
        if self.lost_reply:
            raise core.Ambiguous("fixture_lost_reply")
        return self.outcome

    def reconcile(self, activation, request):
        return self.outcome


def proposal(request):
    return {"repair_limit": 1, "repair_policy": {
        "class_qualifications": {request.correction.kind: request.qualification_digest},
        "writable_paths": {request.slice_id: list(request.correction.writable_paths)}
        if request.correction.writable_paths else {},
    }}


@pytest.mark.parametrize("kind", [repair.SOURCE, repair.INFRASTRUCTURE])
def test_shared_attempt_survives_lost_acknowledgement_and_restart(setup, kind):
    database, _, writer, provider, run = setup
    execution = admitted(run, writer, provider)
    evidence = Evidence(run.store)
    evidence.initialize()
    observed, request = subject(execution, kind=kind)
    record(evidence, execution, observed)
    route = NativeRepair(request, evidence)
    route.lost_reply = True
    custody = Custody(database.parent)
    authorize = lambda activation, reservation: None
    recovery = repair.Recovery(custody, evidence, route, authorize)
    with pytest.raises(core.Ambiguous, match="fixture_lost_reply"):
        recovery.advance(execution, observed, proposal(request))
    assert evidence.reservation(request.grant_id).state == "claimed"
    assert evidence.snapshot(request.grant_id).repair_used == 1
    provider.land(execution.admission)
    assert run.advance(request.grant_id).state == "uncertain"
    assert run.store.active(request.grant_id) == execution

    def expired(activation, reservation):
        pytest.fail("Readback of a claimed effect consulted mutation authority")

    restarted = Evidence(controller.ExecutionStore(database, initialize=False))
    result = repair.Recovery(custody, restarted, route, expired).advance(execution, observed, proposal(request))
    assert result.state == "reconciling" and result.reason == "initiative_repair_effect_verified"
    assert restarted.reservation(request.grant_id).state == "settled"
    assert route.effect == [request]
    spent = recovery.advance(execution, observed, proposal(request))
    assert spent.state == "blocked" and spent.reason == "initiative_repair_budget_spent"
    assert route.effect == [request]

    provider.land(execution.admission)
    assert run.advance(request.grant_id).state == "delivered"
    dependent = admitted(run, writer, provider)
    second, other_request = subject(dependent, generation=5, kind=kind)
    record(restarted, dependent, second)
    with pytest.raises(core.Conflict, match="initiative_repair_budget_spent"):
        restarted.reserve(other_request)
    assert restarted.snapshot(request.grant_id).repair_used == 1


def test_transaction_has_one_winner_for_conflicting_repair_classes(setup):
    database, _, writer, provider, run = setup
    execution = admitted(run, writer, provider)
    evidence = Evidence(run.store)
    evidence.initialize()
    observed, source = subject(execution)
    _, retry = subject(execution, kind=repair.INFRASTRUCTURE)
    record(evidence, execution, observed)

    def reserve(request):
        journal = Evidence(controller.ExecutionStore(database, initialize=False))
        try:
            return journal.reserve(request)
        except core.Conflict as error:
            assert str(error) == "initiative_repair_budget_spent"
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, (source, retry)))
    assert sum(results) == 1
    winner = source if results[0] else retry
    assert evidence.reservation(winner.grant_id).request == winner
    assert evidence.reserve(winner) is False


@pytest.mark.parametrize("change", ["stale", "wrong_attempt", "untrusted", "wrong_subject", "zero", "expired"])
def test_wrong_or_unauthorized_ci_evidence_cannot_spend_attempt(setup, change):
    database, _, writer, provider, run = setup
    execution = admitted(run, writer, provider)
    evidence = Evidence(run.store)
    evidence.initialize()
    observed, request = subject(execution)
    if change == "wrong_attempt":
        observed = replace(observed, attempt=1)
    if change == "wrong_subject":
        observed = replace(observed, candidate=replace(observed.candidate, head=oid(100)))
    if change in {"stale", "untrusted"}:
        outcome = "stale" if change == "stale" else "untrusted"
        state = "stale" if outcome == "stale" else "unavailable"
        observed = ci.Observation(observed.candidate, state, "required_evidence_unproved", 1000, outcome)
    record(evidence, execution, observed)
    route = NativeRepair(request, evidence)
    approved = proposal(request) if change != "zero" else {"repair_limit": 0}

    def guard(*_args):
        raise ValueError("initiative_grant_inactive")

    recover = repair.Recovery(Custody(database.parent), evidence, route, guard)
    if change == "expired":
        with pytest.raises(ValueError, match="initiative_grant_inactive"):
            recover.advance(execution, observed, approved)
    else:
        result = recover.advance(execution, observed, approved)
        assert result is None or result.state in {"admitted", "blocked"}
    assert evidence.snapshot(request.grant_id).repair_used == 0
    assert not route.effect


def test_reserved_repair_with_changed_candidate_spends_allowance_without_mutation(setup):
    database, _, writer, provider, run = setup
    execution = admitted(run, writer, provider)
    evidence = Evidence(run.store)
    evidence.initialize()
    observed, request = subject(execution)
    record(evidence, execution, observed)
    assert evidence.reserve(request)  # Controller stops before claiming the native effect.
    route = NativeRepair(request, evidence)
    replacement = replace(observed.candidate, generation=observed.candidate.generation + 1)
    current = ci.Observation(replacement, "queued", "required_ci_queued", 1010)
    record(evidence, execution, current)
    recover = repair.Recovery(Custody(database.parent), evidence, route, lambda *_args: None)
    with pytest.raises(core.Conflict, match="initiative_repair_predecessor_changed"):
        recover.advance(execution, current, proposal(request))
    assert evidence.reservation(request.grant_id).state == "reserved"
    assert evidence.snapshot(request.grant_id).repair_used == 1
    assert not route.effect


def test_expiring_after_reservation_uses_no_native_mutation(setup):
    database, _, writer, provider, run = setup
    execution = admitted(run, writer, provider)
    evidence = Evidence(run.store)
    evidence.initialize()
    observed, request = subject(execution)
    record(evidence, execution, observed)
    route = NativeRepair(request, evidence)

    def guard(*_args):
        if evidence.reservation(request.grant_id) is not None:
            raise ValueError("initiative_grant_inactive")

    recover = repair.Recovery(Custody(database.parent), evidence, route, guard)
    with pytest.raises(ValueError, match="initiative_grant_inactive"):
        recover.advance(execution, observed, proposal(request))
    assert evidence.reservation(request.grant_id).state == "settled"
    assert evidence.snapshot(request.grant_id).repair_used == 1
    assert not route.effect

    provider.land(execution.admission)
    assert run.advance(request.grant_id).state == "delivered"
