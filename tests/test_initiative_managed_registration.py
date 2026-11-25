"""Synthetic transport and crash tests for the managed Build handoff."""

from contextlib import contextmanager
from dataclasses import replace

import pytest

from test_integration_initiative_controller import Authority, Provider, Writer, core, digest, ic
from test_integration_initiative_opencode import APPROVAL, LAUNCH, ScriptedTransport, native


class HeldWriter(Writer):
    def __init__(self, store):
        super().__init__(store)
        self.release_calls = []
        self.release_receipt = None
        self.release_locked = False
        self.premature = False
        self.lose_release = False

    def observe_dispatch(self, activation):
        if self.premature:
            raise core.Conflict("fixture_unexpected_early_execution")
        return super().observe_dispatch(activation)

    def observe_release(self, activation):
        return self.release_receipt

    def release(self, activation):
        assert self.release_locked
        assert self.store.history(activation.activation_id)[-1].state == "release_claimed"
        assert not self.release_calls
        self.release_calls.append(activation)
        self.release_receipt = ic.NativeRelease(activation.session_id, activation.message_id,
                                                activation.activation_id, False)
        if self.lose_release:
            raise core.Ambiguous("fixture_lost_release_reply")
        return self.release_receipt


class Registration:
    def __init__(self, writer):
        self.writer = writer
        self.calls = []
        self.receipt = None
        self.lost = False
        self.revoked = False

    def register(self, activation, controller):
        assert controller.authorize_begin(activation.grant_id, activation.activation_id,
            activation.session_id, activation.launch.launch_digest) == activation
        assert not self.calls
        self.calls.append(activation)
        self.receipt = ic.RegistrationReceipt(activation.activation_id, activation.launch.cycle_id,
                                             activation.launch.launch_digest, digest(22))
        if self.lost:
            raise core.Ambiguous("fixture_lost_registration_reply")

    def observed(self, activation):
        return self.receipt

    @contextmanager
    def require_release(self, activation):
        if self.revoked:
            raise core.Unavailable("fixture_grant_revoked")
        self.writer.release_locked = True
        try:
            yield self.receipt
        finally:
            self.writer.release_locked = False


@pytest.fixture
def managed(tmp_path):
    private = tmp_path / "state"
    private.mkdir(mode=0o700)
    database = private / "controller.sqlite"
    store = ic.ExecutionStore(database)
    authority, writer, provider = Authority(tmp_path), HeldWriter(store), Provider()
    registration = Registration(writer)
    controller = ic.InitiativeController(store, authority, writer, provider, registration=registration)
    return database, authority, writer, provider, registration, controller


def test_hold_before_begin_and_release_only_after_exact_persisted_registration(managed):
    _, authority, writer, provider, registration, run = managed
    grant = digest(1)
    assert run.advance(grant).state == "session_ready"
    active, = writer.created
    assert run.advance(grant).state == "held"
    with pytest.raises(core.Conflict):
        run.authorize_begin(grant, active.activation_id, active.session_id, active.launch.launch_digest)
    assert writer.release_calls == registration.calls == []
    assert run.advance(grant).state == "registered"
    assert run.store.history(active.activation_id)[-1].receipt_digest == digest(22)
    authority.drift.add("first")  # The clean-launch preflight no longer applies.
    assert run.advance(grant).state == "release_accepted"
    assert not writer.release_locked
    assert run.advance(grant).state == "release_accepted"
    writer.release_receipt = ic.NativeRelease(active.session_id, active.message_id, active.activation_id, True)
    assert run.advance(grant).state == "dispatched"
    assert registration.calls == writer.release_calls == [active]
    provider.admit(active)
    assert run.advance(grant).state == "admitted"


def test_restart_only_observes_claimed_registration_and_release(managed):
    database, authority, writer, provider, registration, run = managed
    grant = digest(1)
    run.advance(grant)
    assert run.advance(grant).state == "held"
    registration.lost = True
    assert run.advance(grant).state == "uncertain"
    restarted = ic.InitiativeController(ic.ExecutionStore(database), authority, writer, provider,
                                       registration=registration)
    assert restarted.advance(grant).state == "registered"
    writer.lose_release = True
    assert restarted.advance(grant).state == "uncertain"
    receipt = writer.release_receipt
    writer.release_receipt = None
    assert restarted.advance(grant).state == "uncertain"
    writer.release_receipt = receipt
    assert restarted.advance(grant).state == "release_accepted"
    assert len(registration.calls) == len(writer.release_calls) == 1


def test_managed_and_legacy_compositions_cannot_swap_a_persisted_claim(managed):
    database, authority, writer, provider, registration, run = managed
    grant = digest(1)
    assert run.advance(grant).state == "session_ready"
    resumed_without_registrar = ic.InitiativeController(ic.ExecutionStore(database), authority, writer, provider)
    result = resumed_without_registrar.advance(grant)
    assert (result.state, result.reason) == ("uncertain", "initiative_execution_mode_changed")
    assert not writer.prompted and not registration.calls


def test_mismatched_registration_receipt_cannot_release_native_execution(managed):
    _, _, writer, _, registration, run = managed
    grant = digest(1)
    run.advance(grant)
    run.advance(grant)
    assert run.advance(grant).state == "registered"
    registration.receipt = replace(registration.receipt, receipt_digest=digest(88))
    assert run.advance(grant).state == "uncertain"
    assert not writer.release_calls


@pytest.mark.parametrize("revoke", (False, True))
def test_premature_execution_or_revocation_prevents_next_managed_mutation(managed, revoke):
    _, _, writer, _, registration, run = managed
    grant = digest(1)
    run.advance(grant)
    assert run.advance(grant).state == "held"
    if revoke:
        assert run.advance(grant).state == "registered"
        registration.revoked = True
    else:
        writer.premature = True
    assert run.advance(grant).state == "uncertain"
    assert writer.release_calls == []
    assert len(registration.calls) == int(revoke)


def _native_case(*, early=False, released=False):
    activation = ic.Activation.from_launch(APPROVAL, "fixture", LAUNCH, managed=True)
    sid, mid, aid = activation.session_id, activation.message_id, activation.activation_id
    session_path = f"/api/session/{sid}"
    log_path = f"/api/experimental/session/{sid}/log?follow=false"
    session = native.Response(200, {"data": {"id": sid, "agent": LAUNCH.agent,
                                            "location": {"directory": LAUNCH.checkout}}})
    body = {"type": "user", "delivery": "queue", "payload": {
        "text": f"Continue the approved DBSCTR Initiative activation {aid}. "
                "Resolve its exact launch and scope from the private coordinator.",
        "metadata": {"dbsctrInitiativeActivation": aid},
    }}
    prompt = {"id": mid, "sessionID": sid, **body}

    def event(kind, seq, **fields):
        return {"type": kind, "durable": {"aggregateID": sid, "seq": seq, "version": 1},
                "data": {"sessionID": sid, "inboxID": mid, **fields}}

    events = [event("session.inbox.enqueued", 1, item=body)]
    if released:
        events.append(event("session.inbox.delivery.changed", 2, delivery="steer"))
    if early or released:
        events.append(event("session.inbox.delivered", len(events) + 1))
    events.append({"type": "log.synced", "aggregateID": sid, "seq": len(events)})
    log = native.Response(200, events)
    return activation, session_path, log_path, session, prompt, log


def test_managed_opencode_queues_without_resume_and_refuses_delivery_before_registration():
    activation, path, log_path, session, prompt, log = _native_case(early=True)
    transport = ScriptedTransport(("GET", path, session), ("POST", path + "/prompt", native.Response(200, {"data": prompt})),
                                  ("GET", path, session), ("GET", log_path, log))
    writer = native.OpenCodeWriter(transport.witness, transport, managed=True)
    with pytest.raises(core.Ambiguous):
        writer.dispatch(activation)
    assert transport.calls[1][-1]["resume"] is False
    assert [method for method, _, _ in transport.calls].count("POST") == 1


def test_managed_writer_reconciles_native_release_and_delivery_read_only():
    activation, path, log_path, session, _, log = _native_case(released=True)
    transport = ScriptedTransport(("GET", path, session), ("GET", log_path, log))
    writer = native.OpenCodeWriter(transport.witness, transport, managed=True)
    assert writer.observe_release(activation) == ic.NativeRelease(
        activation.session_id, activation.message_id, activation.activation_id, True)
    assert all(method == "GET" for method, _, _ in transport.calls)


def test_managed_writer_uses_exact_native_queue_transition_once():
    activation, path, log_path, session, prompt, parked_log = _native_case()
    *_, released_log = _native_case(released=True)
    inbox_path = path + "/inbox"
    release_path = inbox_path + "/" + activation.message_id
    transport = ScriptedTransport(
        ("GET", path, session),
        ("GET", log_path, parked_log),
        ("GET", inbox_path, native.Response(200, {"data": [prompt]})),
        ("GET", "/api/session/active", native.Response(200, {"data": {}})),
        ("PATCH", release_path, native.Response(204, None)),
        ("GET", path, session),
        ("GET", log_path, released_log),
    )
    writer = native.OpenCodeWriter(transport.witness, transport, managed=True)
    assert writer.release(activation) == ic.NativeRelease(
        activation.session_id, activation.message_id, activation.activation_id, True)
    assert [call for call in transport.calls if call[0] != "GET"] == [
        ("PATCH", release_path, {"delivery": "steer"}),
    ]
