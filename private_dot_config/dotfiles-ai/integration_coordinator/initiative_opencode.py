"""Bound OpenCode v2 session and queue writer for approved Initiative activations."""

from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
import http.client
import json
import re
import time
from typing import Protocol
from urllib.parse import urlsplit

from . import core
from .initiative_controller import Activation, NativeDispatch, NativeRelease, NativeSession


_MAX_RESPONSE = 2 * 1024 * 1024
_MAX_RECORDS = 4096
_SECONDS = 5.0
_SESSION_ID = r"ses_[A-Za-z0-9]{1,80}"
_MESSAGE_ID = r"msg_[A-Za-z0-9]{1,80}"
_SESSION_ROUTE = rf"/api/session/{_SESSION_ID}"
_LOG_ROUTE = rf"/api/experimental/session/{_SESSION_ID}/log\?follow=false"
_ACTIVE_ROUTE = "/api/session/active"
_INBOX_ROUTE = _SESSION_ROUTE + "/inbox"


@dataclass(frozen=True, slots=True)
class Qualification:
    origin: str
    pid: int
    version: str
    writer_digest: str

    def __post_init__(self) -> None:
        _endpoint(self.origin)
        core._integer(self.pid)
        core._require(isinstance(self.version, str)
                      and re.fullmatch(r"2\.[0-9]{1,5}\.[0-9]{1,5}", self.version) is not None,
                      "opencode_writer_version")
        core._digest(self.writer_digest)


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    value: object


class Transport(Protocol):
    def qualification(self) -> Qualification: ...

    def request(self, method: str, path: str, payload: dict[str, object] | None = None) -> Response: ...


def _endpoint(origin: str) -> tuple[str, int]:
    core._require(isinstance(origin, str), "opencode_loopback_origin")
    try:
        parsed = urlsplit(origin)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        raise core.Invalid("opencode_loopback_origin") from None
    expected_host = "[::1]" if host == "::1" else "127.0.0.1"
    if (host not in {"127.0.0.1", "::1"} or port is None or port == 0
            or origin != f"http://{expected_host}:{port}"):
        raise core.Invalid("opencode_loopback_origin")
    return host, port


def _json(raw: bytes | str) -> object:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(_: str) -> object:
        raise ValueError("invalid JSON constant")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)


def _event_stream(raw: bytes) -> list[object]:
    body = raw.decode("utf-8").replace("\r\n", "\n")
    if not body.endswith("\n\n") or "\r" in body:
        raise ValueError("incomplete event stream")
    records = []
    for frame in body.removesuffix("\n\n").split("\n\n"):
        fields = frame.splitlines()
        data = [line.removeprefix("data:").removeprefix(" ") for line in fields if line.startswith("data:")]
        if any(not line.startswith(("data:", "event:", "id:", "retry:", ":")) for line in fields):
            raise ValueError("malformed event stream")
        if data:
            records.append(_json("\n".join(data)))
            if len(records) > _MAX_RECORDS:
                raise ValueError("event stream too large")
    return records


class LoopbackTransport:
    """Authenticated, bounded HTTP to one already-qualified local service."""

    def __init__(self, approved: Qualification, password: str) -> None:
        self._approved = approved
        self._host, self._port = _endpoint(approved.origin)
        core._require(isinstance(password, str) and 0 < len(password) <= 4096,
                      "opencode_loopback_credential")
        self._credential = "Basic " + b64encode(("opencode:" + password).encode()).decode("ascii")

    def qualification(self) -> Qualification:
        response = self.request("GET", "/api/info")
        info = response.value
        if (response.status != 200 or not isinstance(info, dict)
                or type(info.get("pid")) is not int or info["pid"] != self._approved.pid
                or info.get("version") != self._approved.version):
            raise core.Unavailable("opencode_service_binding_changed")
        return self._approved

    def request(self, method: str, path: str, payload: dict[str, object] | None = None) -> Response:
        is_log = re.fullmatch(_LOG_ROUTE, path) is not None
        if method == "GET":
            core._require(payload is None and (path in {"/api/info", _ACTIVE_ROUTE} or is_log
                          or re.fullmatch(_SESSION_ROUTE, path) is not None
                          or re.fullmatch(_INBOX_ROUTE, path) is not None), "opencode_writer_route")
        elif method == "PATCH":
            core._require(payload == {"delivery": "steer"}
                          and re.fullmatch(_INBOX_ROUTE + "/" + _MESSAGE_ID, path) is not None,
                          "opencode_writer_route")
        else:
            core._require(method == "POST" and isinstance(payload, dict) and (path == "/api/session"
                          or re.fullmatch(_SESSION_ROUTE + "/prompt", path) is not None), "opencode_writer_route")
        headers = {"Authorization": self._credential, "Accept": "text/event-stream" if is_log else "application/json"}
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8")
            core._require(len(body) <= 8192, "opencode_writer_body")
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(self._host, self._port, timeout=_SECONDS)
        deadline = time.monotonic() + _SECONDS
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            data = bytearray()
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError("native response deadline")
                chunk = response.read1(min(65536, _MAX_RESPONSE + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > _MAX_RESPONSE:
                    raise ValueError("native response too large")
            if not data:
                return Response(response.status, None)
            media_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            if is_log and response.status == 200:
                if media_type != "text/event-stream":
                    raise ValueError("unexpected native stream type")
                return Response(response.status, _event_stream(bytes(data)))
            if media_type != "application/json":
                raise ValueError("unexpected native response type")
            return Response(response.status, _json(bytes(data)))
        except (OSError, http.client.HTTPException, ValueError, RecursionError):
            raise core.Unavailable("opencode_native_response_unavailable") from None
        finally:
            connection.close()


def _data(response: Response) -> dict[str, object]:
    if response.status != 200 or not isinstance(response.value, dict):
        raise core.Unavailable("opencode_native_response_unavailable")
    data = response.value.get("data")
    if not isinstance(data, dict):
        raise core.Unavailable("opencode_native_response_unavailable")
    return data


def _session(data: dict[str, object], activation: Activation) -> NativeSession:
    checkout, agent = activation.launch.checkout, activation.launch.agent
    location = data.get("location")
    if (data.get("id") != activation.session_id or data.get("agent") != agent
            or not isinstance(location, dict) or location.get("directory") != checkout
            or data.get("parentID") is not None or location.get("subpath") not in (None, "")
            or data.get("subpath") not in (None, "")):
        raise core.Ambiguous("opencode_session_identity_unconfirmed")
    lifetime = data.get("time")
    if isinstance(lifetime, dict) and lifetime.get("archived") is not None:
        raise core.Ambiguous("opencode_session_archived")
    return NativeSession(activation.session_id, checkout, agent)


def _prompt(activation: Activation) -> tuple[str, dict[str, str]]:
    text = (f"Continue the approved DBSCTR Initiative activation {activation.activation_id}. "
            "Resolve its exact launch and scope from the private coordinator.")
    return text, {"dbsctrInitiativeActivation": activation.activation_id}


def _matches_prompt(item: object, activation: Activation) -> bool:
    if not isinstance(item, dict) or item.get("type") != "user" or item.get("delivery") != "queue":
        return False
    payload = item.get("payload")
    text, metadata = _prompt(activation)
    return (isinstance(payload, dict) and payload.get("text") == text and payload.get("metadata") == metadata
            and all(payload.get(key) in (None, []) for key in ("files", "agents", "skills")))


@dataclass(frozen=True, slots=True)
class _PromptTrace:
    enqueued: bool
    released: bool
    delivered: bool


def _log_trace(response: Response, activation: Activation) -> _PromptTrace:
    records = response.value
    if response.status != 200 or not isinstance(records, list) or not 1 <= len(records) <= _MAX_RECORDS:
        raise core.Unavailable("opencode_dispatch_log_unavailable")
    last_seq = None
    enqueued = released = delivered = False
    for record in records[:-1]:
        if not isinstance(record, dict) or not isinstance(record.get("type"), str):
            raise core.Ambiguous("opencode_dispatch_log_unconfirmed")
        kind, durable, data = record["type"], record.get("durable"), record.get("data")
        if (not kind.startswith("session.") or not isinstance(durable, dict)
                or durable.get("aggregateID") != activation.session_id
                or type(durable.get("version")) is not int or durable["version"] < 1
                or type(durable.get("seq")) is not int or durable["seq"] < 0
                or (last_seq is not None and durable["seq"] <= last_seq)
                or not isinstance(data, dict) or data.get("sessionID") != activation.session_id):
            raise core.Ambiguous("opencode_dispatch_log_unconfirmed")
        last_seq = durable["seq"]
        if activation.managed and not released and kind == "session.execution.started":
            raise core.Ambiguous("opencode_dispatch_executed_before_release")
        if not kind.startswith("session.inbox."):
            continue
        if durable["version"] != 1 or not isinstance(data.get("inboxID"), str):
            raise core.Ambiguous("opencode_dispatch_log_unconfirmed")
        if data["inboxID"] != activation.message_id:
            if activation.managed and not released:
                raise core.Ambiguous("opencode_dispatch_session_not_exclusive")
            continue
        if kind == "session.inbox.enqueued" and not enqueued and _matches_prompt(data.get("item"), activation):
            enqueued = True
        elif (activation.managed and kind == "session.inbox.delivery.changed"
                and enqueued and not released and not delivered and data.get("delivery") == "steer"):
            released = True
        elif kind == "session.inbox.delivered" and enqueued and not delivered and (released or not activation.managed):
            delivered = True
        else:
            raise core.Ambiguous("opencode_dispatch_log_unconfirmed")
    watermark = records[-1]
    if (not isinstance(watermark, dict) or watermark.get("type") != "log.synced"
            or watermark.get("aggregateID") != activation.session_id):
        raise core.Ambiguous("opencode_dispatch_log_unconfirmed")
    # Other durable buses share sequence positions with the session log.
    limit = watermark.get("seq")
    if ("seq" in watermark and (type(limit) is not int or limit < 0)
            or last_seq is not None and (limit is None or limit < last_seq)):
        raise core.Ambiguous("opencode_dispatch_log_unconfirmed")
    return _PromptTrace(enqueued, released, delivered)


class OpenCodeWriter:
    """Verify native identity and queue evidence for the controller's exact activation."""

    def __init__(self, approved: Qualification, transport: Transport, *, managed: bool = False) -> None:
        core._require(type(approved) is Qualification and type(managed) is bool
                      and (not managed or approved.version == "2.3.2"), "opencode_writer_version_unqualified")
        self._approved = approved
        self._transport = transport
        self._managed = managed

    def _check(self, activation: Activation) -> None:
        core._require(type(activation) is Activation, "opencode_writer_activation_unqualified")
        if activation.writer_digest != self._approved.writer_digest or activation.managed != self._managed:
            raise core.Conflict("opencode_writer_activation_drift")
        try:
            witness = self._transport.qualification()
        except OSError:
            raise core.Unavailable("opencode_service_binding_unavailable") from None
        if witness != self._approved:
            raise core.Conflict("opencode_service_binding_changed")

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None) -> Response:
        try:
            response = self._transport.request(method, path, payload)
        except OSError:
            raise core.Unavailable("opencode_native_response_unavailable") from None
        if type(response) is not Response:
            raise core.Unavailable("opencode_native_response_unavailable")
        return response

    def observe_session(self, activation: Activation) -> NativeSession | None:
        self._check(activation)
        response = self._request("GET", f"/api/session/{activation.session_id}")
        native = response.value
        if (response.status == 404 and isinstance(native, dict) and native.get("_tag") == "SessionNotFoundError"
                and native.get("sessionID") == activation.session_id and isinstance(native.get("message"), str)):
            return None
        return _session(_data(response), activation)

    def create_session(self, activation: Activation) -> NativeSession:
        self._check(activation)
        payload: dict[str, object] = {
            "id": activation.session_id,
            "agent": activation.launch.agent,
            "location": {"directory": activation.launch.checkout},
        }
        try:
            _session(_data(self._request("POST", "/api/session", payload)), activation)
            confirmed = self.observe_session(activation)
            if confirmed is None:
                raise core.Ambiguous("opencode_session_identity_unconfirmed")
            return confirmed
        except (core.Ambiguous, core.Conflict, core.Invalid, core.Unavailable):
            raise core.Ambiguous("opencode_session_create_unconfirmed") from None

    def _observe_log(self, activation: Activation) -> _PromptTrace:
        if self.observe_session(activation) is None:
            raise core.Unavailable("opencode_dispatch_session_unavailable")
        path = f"/api/experimental/session/{activation.session_id}/log?follow=false"
        return _log_trace(self._request("GET", path), activation)

    def _require_parked(self, activation: Activation) -> None:
        queue = self._request("GET", f"/api/session/{activation.session_id}/inbox")
        data = queue.value.get("data") if queue.status == 200 and isinstance(queue.value, dict) else None
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise core.Ambiguous("opencode_dispatch_inbox_unproved")
        item = data[0]
        if (item.get("id") != activation.message_id or item.get("sessionID") != activation.session_id
                or not _matches_prompt(item, activation)):
            raise core.Ambiguous("opencode_dispatch_inbox_unproved")
        active = _data(self._request("GET", _ACTIVE_ROUTE))
        if activation.session_id in active:
            raise core.Ambiguous("opencode_dispatch_executed_before_release")

    def observe_dispatch(self, activation: Activation) -> NativeDispatch | None:
        trace = self._observe_log(activation)
        if not trace.enqueued:
            return None
        if self._managed:
            if trace.released or trace.delivered:
                raise core.Ambiguous("opencode_dispatch_executed_before_release")
            self._require_parked(activation)
        return NativeDispatch(activation.session_id, activation.message_id, activation.activation_id)

    def dispatch(self, activation: Activation) -> NativeDispatch:
        if self.observe_session(activation) is None:
            raise core.Unavailable("opencode_dispatch_session_unavailable")
        text, metadata = _prompt(activation)
        payload: dict[str, object] = {
            "id": activation.message_id,
            "text": text,
            "metadata": metadata,
            "delivery": "queue",
            "resume": not self._managed,
        }
        path = f"/api/session/{activation.session_id}/prompt"
        try:
            admission = _data(self._request("POST", path, payload))
            if (admission.get("id") != activation.message_id or admission.get("sessionID") != activation.session_id
                    or not _matches_prompt(admission, activation)):
                raise core.Ambiguous("opencode_dispatch_identity_unconfirmed")
            if self._managed:
                parked = self.observe_dispatch(activation)
                if parked is None:
                    raise core.Ambiguous("opencode_dispatch_inbox_unproved")
                return parked
            return NativeDispatch(activation.session_id, activation.message_id, activation.activation_id)
        except (core.Ambiguous, core.Conflict, core.Invalid, core.Unavailable):
            raise core.Ambiguous("opencode_dispatch_unconfirmed") from None

    def observe_release(self, activation: Activation) -> NativeRelease | None:
        if not self._managed:
            raise core.Unavailable("opencode_managed_release_unavailable")
        trace = self._observe_log(activation)
        if not trace.released:
            return None
        return NativeRelease(activation.session_id, activation.message_id, activation.activation_id, trace.delivered)

    def release(self, activation: Activation) -> NativeRelease:
        if not self._managed or self.observe_dispatch(activation) is None:
            raise core.Unavailable("opencode_managed_release_unavailable")
        path = f"/api/session/{activation.session_id}/inbox/{activation.message_id}"
        try:
            response = self._request("PATCH", path, {"delivery": "steer"})
            if response.status != 204 or response.value is not None:
                raise core.Ambiguous("opencode_release_response_unconfirmed")
            observed = self.observe_release(activation)
            if observed is None:
                raise core.Ambiguous("opencode_release_response_unconfirmed")
            return observed
        except (core.Ambiguous, core.Conflict, core.Invalid, core.Unavailable):
            raise core.Ambiguous("opencode_release_unconfirmed") from None
