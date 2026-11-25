"""Fixture-only checks for the qualified OpenCode v2 writer adapter."""
from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, initiative_controller as controller, initiative_opencode as native


CHECKOUT = "/fixture/qualified/checkout"
AGENT = "build-gpt"
DIGEST = "a" * 64
SERVICE = "http://127.0.0.1:43822"
VERSION = "2.3.2"
TARGET = controller.Target("https://forge.example.invalid", "example/fixture", "refs/heads/main")
APPROVAL = controller.Approval("b" * 64, TARGET, "c" * 64, DIGEST, (controller.Slice("fixture"),))
LAUNCH = controller.Launch("d" * 64, "e" * 40, CHECKOUT, "fixture-cycle", AGENT)
ACTIVATION = controller.Activation.from_launch(APPROVAL, "fixture", LAUNCH)
SID, MID, AID = ACTIVATION.session_id, ACTIVATION.message_id, ACTIVATION.activation_id
SESSION = f"/api/session/{SID}"
LOG = f"/api/experimental/session/{SID}/log?follow=false"
TEXT = f"Continue the approved DBSCTR Initiative activation {AID}. Resolve its exact launch and scope from the private coordinator."
META = {"dbsctrInitiativeActivation": AID}


@pytest.fixture
def activation():
    return ACTIVATION


def session(**changes):
    return native.Response(200, {"data": {"id": SID, "agent": AGENT,
        "location": {"directory": CHECKOUT}, **changes}})


def inbox(**changes):
    return {"type": "user", "delivery": "queue", "payload": {"text": TEXT, "metadata": META}, **changes}


def event(kind, seq, **fields):
    return {"id": f"evt_fixture{seq}", "type": kind, "created": 100 + seq,
            "durable": {"aggregateID": SID, "seq": seq, "version": 1},
            "data": {"sessionID": SID, "inboxID": MID, **fields}}


def synced(seq=None):
    return {"type": "log.synced", "aggregateID": SID, **({} if seq is None else {"seq": seq})}


class ScriptedTransport:
    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls = []
        self.witness = native.Qualification(SERVICE, 4100, VERSION, DIGEST)

    def qualification(self):
        return self.witness

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        assert self.steps, f"unexpected request: {method} {path}"
        expected_method, expected_path, response = self.steps.pop(0)
        assert (method, path) == (expected_method, expected_path)
        if isinstance(response, Exception):
            raise response
        return response


def writer(transport):
    return native.OpenCodeWriter(native.Qualification(SERVICE, 4100, VERSION, DIGEST), transport)


def test_writer_qualification_binds_native_service_process():
    service = native.Qualification(SERVICE, 4100, VERSION, DIGEST)
    assert service != replace(service, pid=4101)


def test_numeric_loopback_transport_allows_only_the_exact_release_route(monkeypatch):
    calls = []

    class EmptyResponse:
        status = 204

        def read1(self, _size):
            return b""

    class Connection:
        def __init__(self, host, port, *, timeout):
            assert (host, port) == ("127.0.0.1", 43822)
            assert timeout > 0

        def request(self, method, path, *, body, headers):
            calls.append((method, path, json.loads(body)))
            assert headers["Authorization"].startswith("Basic ")

        def getresponse(self):
            return EmptyResponse()

        def close(self):
            pass

    monkeypatch.setattr(native.http.client, "HTTPConnection", Connection)
    transport = native.LoopbackTransport(native.Qualification(SERVICE, 4100, VERSION, DIGEST), "fixture-only")
    path = f"{SESSION}/inbox/{MID}"
    assert transport.request("PATCH", path, {"delivery": "steer"}) == native.Response(204, None)
    with pytest.raises(core.Invalid):
        transport.request("PATCH", SESSION + "/inbox/invalid", {"delivery": "steer"})
    assert calls == [("PATCH", path, {"delivery": "steer"})]


@pytest.mark.parametrize("change", [{"pid": 4211}, {"version": "2.3.3"}, {"writer_digest": "b" * 64}])
def test_witness_drift_blocks_all_native_requests(activation, change):
    transport = ScriptedTransport()
    transport.witness = replace(transport.witness, **change)
    with pytest.raises((core.Conflict, core.Unavailable)):
        writer(transport).create_session(activation)
    assert transport.calls == []


def test_activation_is_bound_to_the_qualified_writer_before_transport(activation):
    other = controller.Activation.from_launch(replace(APPROVAL, writer_digest="9" * 64), "fixture", LAUNCH)
    transport = ScriptedTransport()
    with pytest.raises(core.Conflict, match="opencode_writer_activation_drift"):
        writer(transport).create_session(other)
    assert transport.calls == []


def test_create_uses_bound_id_directory_agent_and_independent_readback(activation):
    transport = ScriptedTransport(("POST", "/api/session", session()), ("GET", SESSION, session()))
    result = writer(transport).create_session(activation)
    assert (result.session_id, result.checkout, result.agent) == (SID, CHECKOUT, AGENT)
    assert transport.calls == [
        ("POST", "/api/session", {"id": SID, "agent": AGENT, "location": {"directory": CHECKOUT}}),
        ("GET", SESSION, None),
    ]


@pytest.mark.parametrize("changed", [{"id": "ses_foreign"}, {"location": {"directory": "/wrong"}},
                                      {"agent": "plan"}, {"parentID": "ses_parent"}, {"subpath": "nested"}])
def test_create_acknowledgement_cannot_replace_exact_native_readback(activation, changed):
    transport = ScriptedTransport(("POST", "/api/session", session()), ("GET", SESSION, session(**changed)))
    with pytest.raises(core.Ambiguous):
        writer(transport).create_session(activation)
    assert [method for method, _, _ in transport.calls] == ["POST", "GET"]


def test_only_exact_tagged_native_session_absence_is_observed(activation):
    record = native.Response(404, {"_tag": "SessionNotFoundError", "sessionID": SID, "message": "missing"})
    transport = ScriptedTransport(("GET", SESSION, record))
    assert writer(transport).observe_session(activation) is None
    for malformed in (native.Response(404, {}), native.Response(404, {"_tag": "SessionNotFoundError",
        "sessionID": "ses_foreign"}), native.Response(500, {}), TimeoutError()):
        transport = ScriptedTransport(("GET", SESSION, malformed))
        with pytest.raises((core.Ambiguous, core.Unavailable)):
            writer(transport).observe_session(activation)
        assert len(transport.calls) == 1


def test_dispatch_admits_one_fixed_native_queue_prompt(activation):
    transport = ScriptedTransport(("GET", SESSION, session()), ("POST", SESSION + "/prompt",
        native.Response(200, {"data": {"id": MID, "sessionID": SID, **inbox()}})))
    result = writer(transport).dispatch(activation)
    assert (result.session_id, result.message_id, result.activation_id) == (SID, MID, AID)
    assert transport.calls[-1] == ("POST", SESSION + "/prompt", {
        "id": MID, "text": TEXT, "metadata": META, "delivery": "queue", "resume": True,
    })


@pytest.mark.parametrize("change", [{"id": "msg_foreign"}, {"sessionID": "ses_foreign"},
                                     {"delivery": "steer"}, {"payload": {"text": "modified", "metadata": META}}])
def test_dispatch_ack_mismatch_remains_ambiguous_without_second_post(activation, change):
    record = {"id": MID, "sessionID": SID, **inbox(), **change}
    transport = ScriptedTransport(("GET", SESSION, session()),
                                  ("POST", SESSION + "/prompt", native.Response(200, {"data": record})))
    with pytest.raises(core.Ambiguous):
        writer(transport).dispatch(activation)
    assert [method for method, _, _ in transport.calls] == ["GET", "POST"]


def test_lost_dispatch_response_can_be_reconciled_from_exact_durable_events(activation):
    created = event("session.created", 0)
    tool = event("session.tool.success", 7)
    tool["durable"]["version"] = 2
    events = [created, event("session.inbox.enqueued", 2, item=inbox()),
              event("session.inbox.delivered", 3), tool, synced(10)]
    transport = ScriptedTransport(("GET", SESSION, session()),
        ("POST", SESSION + "/prompt", TimeoutError()), ("GET", SESSION, session()),
        ("GET", LOG, native.Response(200, events)))
    adapter = writer(transport)
    with pytest.raises(core.Ambiguous):
        adapter.dispatch(activation)
    result = adapter.observe_dispatch(activation)
    assert (result.session_id, result.message_id, result.activation_id) == (SID, MID, AID)
    assert [method for method, _, _ in transport.calls] == ["GET", "POST", "GET", "GET"]


@pytest.mark.parametrize("case", ["truncated", "duplicate", "cancelled", "delivery", "scope", "wrong_body",
                                  "stale_watermark", "unknown_inbox_version"])
def test_non_authoritative_durable_log_cannot_confirm_or_clear_dispatch(activation, case):
    initial = event("session.inbox.enqueued", 1, item=inbox())
    events = [initial, synced(1)]
    if case == "truncated":
        events.pop()
    elif case == "duplicate":
        events = [initial, event("session.inbox.enqueued", 2, item=inbox()), synced(2)]
    elif case == "cancelled":
        events = [initial, event("session.inbox.cancelled", 2), synced(2)]
    elif case == "delivery":
        events = [initial, event("session.inbox.delivery.changed", 2, delivery="steer"), synced(2)]
    elif case == "scope":
        initial["durable"]["aggregateID"] = "ses_foreign"
    elif case == "stale_watermark":
        events[-1]["seq"] = 0
    elif case == "unknown_inbox_version":
        initial["durable"]["version"] = 2
    else:
        initial["data"]["item"] = inbox(payload={"text": TEXT + " extra", "metadata": META})
    transport = ScriptedTransport(("GET", SESSION, session()), ("GET", LOG, native.Response(200, events)))
    with pytest.raises((core.Ambiguous, core.Unavailable)):
        writer(transport).observe_dispatch(activation)
    assert all(method == "GET" for method, _, _ in transport.calls)


def test_synced_empty_log_is_only_an_absence_observation(activation):
    transport = ScriptedTransport(("GET", SESSION, session()), ("GET", LOG, native.Response(200, [synced()])))
    assert writer(transport).observe_dispatch(activation) is None


def test_loopback_transport_checks_real_metadata_and_does_not_follow_redirects(monkeypatch):
    witnesses = []
    class FakeConnection:
        def __init__(self, host, port, *, timeout):
            assert (host, port) == ("127.0.0.1", 43822)
        def request(self, method, path, *, body=None, headers):
            assert headers["Authorization"].startswith("Basic ")
            witnesses.append((method, path))
        def getresponse(self):
            if witnesses[-1][1] == "/api/info":
                raw = json.dumps({"pid": 4100, "version": VERSION}).encode()
                return FakeHTTP(200, raw, "application/json")
            return FakeHTTP(302, b"", "application/json")
        def close(self):
            pass
    monkeypatch.setattr(native.http.client, "HTTPConnection", FakeConnection)
    expected = native.Qualification(SERVICE, 4100, VERSION, DIGEST)
    transport = native.LoopbackTransport(expected, "synthetic-fixture-password")
    assert transport.qualification() == expected
    assert transport.request("GET", SESSION).status == 302
    with pytest.raises(core.Invalid):
        transport.request("GET", "https://outside.example.invalid/")
    assert witnesses == [("GET", "/api/info"), ("GET", SESSION)]


@pytest.mark.parametrize("wrong_info", [{"pid": 4101}, {"version": "2.3.3"}])
def test_loopback_live_metadata_drift_fails_before_session_route(monkeypatch, wrong_info):
    class FakeConnection:
        def __init__(self, host, port, *, timeout):
            pass
        def request(self, method, path, *, body=None, headers):
            assert (method, path) == ("GET", "/api/info")
        def getresponse(self):
            info = {"pid": 4100, "version": VERSION, **wrong_info}
            return FakeHTTP(200, json.dumps(info).encode(), "application/json")
        def close(self):
            pass
    monkeypatch.setattr(native.http.client, "HTTPConnection", FakeConnection)
    transport = native.LoopbackTransport(native.Qualification(SERVICE, 4100, VERSION, DIGEST), "fixture")
    with pytest.raises(core.Unavailable, match="opencode_service_binding_changed"):
        writer(transport).create_session(ACTIVATION)


@pytest.mark.parametrize("complete", [True, False])
def test_loopback_reads_bounded_finite_native_sse(complete, monkeypatch):
    records = [event("session.inbox.enqueued", 2, item=inbox()), synced(3)]
    frames = "".join(f"event: message\r\ndata: {json.dumps(record)}\r\n\r\n" for record in records)
    if not complete:
        frames = frames.removesuffix("\r\n")

    class FakeConnection:
        def __init__(self, host, port, *, timeout):
            pass
        def request(self, method, path, *, body=None, headers):
            assert (method, path, headers["Accept"]) == ("GET", LOG, "text/event-stream")
        def getresponse(self):
            return FakeHTTP(200, frames.encode(), "text/event-stream; charset=utf-8")
        def close(self):
            pass
    monkeypatch.setattr(native.http.client, "HTTPConnection", FakeConnection)
    transport = native.LoopbackTransport(native.Qualification(SERVICE, 4100, VERSION, DIGEST), "fixture")
    if not complete:
        with pytest.raises(core.Unavailable):
            transport.request("GET", LOG)
    else:
        assert transport.request("GET", LOG) == native.Response(200, records)


class FakeHTTP:
    def __init__(self, status, raw, content_type):
        self.status, self.raw, self.content_type = status, raw, content_type
    def read1(self, size):
        part, self.raw = self.raw[:size], self.raw[size:]
        return part
    def getheader(self, key, default=None):
        return self.content_type if key == "Content-Type" else default
