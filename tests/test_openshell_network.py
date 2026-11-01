"""Network qualification contracts using fake guest transport and local sockets."""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
import copy
import errno
import hashlib
import http.client
import importlib.util
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import socket
import stat
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

import test_openshell_runtime as support


owned_root = support.owned_root
pointer_fixture = support.pointer_fixture
guarded_pointer_fixture = support.guarded_pointer_fixture
DIGEST = support.DIGEST
ADDRESS = "192.168.127.2"
BODY = b"openshell-network-probe\n"
LISTENER_PATH = Path(__file__).parent / "fixtures/openshell_runtime/network_listener.py"
IDENTITY = ("ab123456-1234-4234-8234-123456789abc", "fixture-main", 1700000000000,
            "cd" * 32, 1234, "2026-11-01T00:00:00Z", "ab" * 32, 1, 1, 1, 1)
IDENTITY_FIELDS = ("sandbox_id", "main_process_instance_id", "main_process_started_at_ms",
                   "container_id", "pid", "container_started_at", "policy_hash",
                   "policy_version", "config_revision", "provider_env_revision", "current_policy_version")


def load_module(name: str, path: Path):
    assert path.is_file(), f"Required network implementation is absent: {path.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def network():
    sys.modules["probe_openshell_runtime"] = support.probe
    return load_module("openshell_network_under_test", Path(__file__).with_name("probe_openshell_network.py"))


@pytest.fixture(scope="module")
def listener():
    return load_module("openshell_network_listener_under_test", LISTENER_PATH)


def write_private(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)


@pytest.fixture
def network_fixture(guarded_pointer_fixture, network):
    root, env, guard, observed = guarded_pointer_fixture
    write_private(root / "generation.json", {"schema_version": 1, "identity": dict(zip(IDENTITY_FIELDS, IDENTITY))})
    write_private(root / "network.json", {
        "schema_version": 1, "address": ADDRESS, "listener_pid": 2345, "listener_start_ticks": 4567,
        "listener_source_sha256": hashlib.sha256(LISTENER_PATH.read_bytes()).hexdigest(),
    })
    return root, env, guard, observed


def constants(program: str) -> dict:
    values = {}
    for node in ast.parse(program).body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name):
                values[target.id] = value
            elif isinstance(target, ast.Tuple):
                values.update({entry.id: part for entry, part in zip(target.elts, value)})
    return values


def arrival(token: str, port: int = 18080, method: str = "GET", path: str = "/probe") -> dict:
    return {"schema_version": 1, "token": token, "port": port, "method": method,
            "path": path, "accepted": method == "GET" and path == "/probe"}


class NetworkTransport:
    """Only the native transport is simulated; qualification decisions stay real."""

    def __init__(self, root: Path, env: dict, network):
        self.root, self.env, self.network = root, env, network
        self.guest_home, self.guest_uid = "/home/fixture", 1000
        self.sandbox_name = root.name.removeprefix("openshell-")
        self.generation = IDENTITY
        self.executions = []
        self.controls = []
        self.records = []
        self.action = None
        self.observation_action = None
        self.policy = network.expected_policy(ADDRESS)
        self.failed = False
        self.post_failure_identities = 0
        self.deadlines = []

    def identity(self, deadline):
        self.deadlines.append(deadline)
        assert 0 < deadline - time.monotonic() <= 60
        if self.failed:
            self.post_failure_identities += 1
        return self.generation

    def guest(self, argv, deadline):
        assert 0 < deadline - time.monotonic() <= 60
        if argv[0] == "/usr/bin/openshell":
            if argv[1:3] == ["sandbox", "exec"]:
                assert argv[argv.index("--") + 1] == "/usr/local/bin/python3.13"
                value = self.execute(argv[argv.index("-c") + 1], deadline)
                return support.probe.CommandResult(0, json.dumps(value).encode(), b"")
            assert argv[1:3] == ["policy", "get"] and "--full" in argv and "--base" not in argv
            value = {"scope": "sandbox", "sandbox": self.sandbox_name, "version": 1,
                     "active_version": 1, "hash": IDENTITY[6], "status": "effective",
                     "config_revision": 1, "policy_source": "sandbox", "policy": self.policy}
        else:
            data = constants(argv[argv.index("-c") + 1])
            if data["purpose"] == "listener_control":
                token, port = argv[-2], int(argv[-1])
                self.controls.append((token, port))
                self.records.append(arrival(token, port))
                value = {"schema_version": 1, "status": 200,
                         "response_sha256": hashlib.sha256(BODY).hexdigest()}
            else:
                assert data["purpose"] == "listener_observation"
                raw = b"".join((json.dumps(row) + "\n").encode() for row in self.records)
                value = {"address": ADDRESS, "pid": 2345, "start_ticks": 4567, "uid": 1000,
                         "source_sha256": hashlib.sha256(LISTENER_PATH.read_bytes()).hexdigest(),
                         "socket_inodes": {"18080": 101, "18081": 102},
                         "record_identity": {"device": 1, "inode": 300, "uid": 1000,
                                             "mode": stat.S_IFREG | 0o600, "link_count": 1},
                         "record_size": len(raw), "records": copy.deepcopy(self.records)}
                if self.observation_action:
                    value = self.observation_action(value)
        return support.probe.CommandResult(0, json.dumps(value).encode(), b"")

    def execute(self, program, deadline):
        assert 0 < deadline - time.monotonic() <= 60
        data = constants(program)
        operation, token = data["operation"], data["token"]
        self.executions.append(operation)
        result = {"schema_version": 1, "operation": operation,
                  "outcome": "allowed" if operation == "allowed" else "denied",
                  "errno": 0, "status": 200 if operation == "allowed" else 403,
                  "response_sha256": hashlib.sha256(BODY).hexdigest() if operation == "allowed" else "",
                  "binary": "/usr/local/bin/python3.13"}
        if operation == "allowed":
            self.records.append(arrival(token))
        if self.action:
            return self.action(operation, token, result)
        return result


def install_transport(monkeypatch, network_fixture, network):
    root, env, _, _ = network_fixture
    transport = NetworkTransport(root, env, network)
    monkeypatch.setattr(network.runtime, "_PointerController", lambda selection, deadline: transport)
    return transport


@pytest.mark.parametrize("change", [
    {"schema_version": True}, {"address": "127.0.0.1"}, {"address": "8.8.8.8"},
    {"address": "169.254.1.2"}, {"address": "100.64.0.1"}, {"address": "192.168.127.002"},
    {"address": "192.168.127.2/32"}, {"listener_pid": True}, {"listener_pid": 0},
    {"listener_start_ticks": -1}, {"listener_source_sha256": "00" * 32}, {"port": 80},
])
def test_invalid_network_receipt_has_no_native_effects(network_fixture, network, monkeypatch, change):
    root, _, _, _ = network_fixture
    path = root / "network.json"
    write_private(path, json.loads(path.read_text()) | change)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("native")
        raise AssertionError("invalid network receipt reached a native interface")

    monkeypatch.setattr(network.runtime, "_PointerController", forbidden)
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["runtime_qualification"] == "not_run"
    assert calls == []


def test_allowed_and_denied_results_require_independent_listener_records(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "passed" and result["retained"] is True
    assert result["runtime_qualification"] == "not_run"
    assert set(transport.executions) == {"allowed", "denied_method", "denied_path", "denied_proxy",
                                         "denied_clear", "denied_socket"}
    assert [port for _, port in transport.controls] == [18080, 18081, 18080, 18081]
    assert len(result["generation_sha256"]) == 64


@pytest.mark.parametrize("broadening", ["provider", "method", "address", "filesystem", "boolean_version"])
def test_complete_effective_policy_must_equal_frozen_policy(network_fixture, network, monkeypatch, broadening):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)
    if broadening == "provider":
        transport.policy["network_policies"]["_provider_unexpected"] = {"endpoints": [{"host": "example.invalid", "port": 443}]}
    elif broadening == "boolean_version":
        transport.policy["version"] = True
    elif broadening == "filesystem":
        transport.policy["filesystem_policy"]["read_write"].append("/tmp")
    else:
        endpoint = transport.policy["network_policies"]["qualification_probe"]["endpoints"][0]
        if broadening == "method":
            endpoint["rules"][0]["allow"]["method"] = "*"
        else:
            endpoint["allowed_ips"] = ["192.168.0.0/16"]
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] != "passed" and transport.executions == [] and transport.controls == []


@pytest.mark.parametrize("operation", ["allowed", "denied_method", "denied_path", "denied_socket"])
def test_guest_claim_cannot_override_trusted_listener_arrival(network_fixture, network, monkeypatch, operation):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)

    def contradict(name, token, result):
        if name == operation:
            if name == "allowed":
                transport.records.pop()
            else:
                transport.records.append(arrival(token, 18081 if name == "denied_socket" else 18080))
        return result

    transport.action = contradict
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] != "passed" and transport.executions[-1] == operation
    if operation != "allowed":
        assert result["status"] == "failed"


@pytest.mark.parametrize("field,value", [("pid", 9999), ("start_ticks", 9999), ("uid", 0),
                                         ("socket_inodes", {"18080": 101}),
                                         ("source_sha256", "00" * 32), ("record_size", 65537)])
def test_native_listener_identity_and_bounds_are_required(network_fixture, network, monkeypatch, field, value):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)
    transport.observation_action = lambda observation: observation | {field: value}
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] != "passed" and transport.executions == [] and transport.controls == []


@pytest.mark.parametrize("failure", ["timeout", "malformed"])
def test_guard_is_observed_after_failed_workload_transport(network_fixture, network, monkeypatch, failure):
    root, _, _, observed = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)

    def fail(operation, token, result):
        observed["flags"] = 0
        transport.failed = True
        if failure == "timeout":
            raise network.runtime.Refusal("timeout")
        return {"private": "untrusted body must not escape"}

    transport.action = fail
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert result["retained"] is True and len(transport.executions) == 1
    assert "untrusted body" not in json.dumps(result)


def test_identity_is_observed_after_transport_error(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)

    def fail(operation, token, result):
        transport.failed = True
        transport.generation = (*IDENTITY[:6], "fe" * 32, *IDENTITY[7:])
        raise network.runtime.Refusal("timeout")

    transport.action = fail
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert transport.post_failure_identities > 0
    assert result["status"] != "passed" and result["reason"] == "sandbox_identity"
    assert len(transport.executions) == 1


@pytest.mark.parametrize("age", [-1, 901])
def test_network_does_not_start_a_fresh_experiment_window(network_fixture, network, monkeypatch, age):
    root, _, _, _ = network_fixture
    timestamp = time.time() - age
    os.utime(root / "prepared.json", (timestamp, timestamp))
    transport = install_transport(monkeypatch, network_fixture, network)
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "experiment_deadline"
    assert transport.executions == [] and transport.controls == []


@pytest.mark.parametrize("violation", ["duplicate", "permissions", "symlink"])
def test_network_receipt_requires_one_private_regular_object(network_fixture, network, monkeypatch, violation):
    root, _, _, _ = network_fixture
    path = root / "network.json"
    if violation == "duplicate":
        path.write_text(path.read_text()[:-1] + ',"schema_version":1}')
    elif violation == "permissions":
        path.chmod(0o644)
    else:
        path.rename(root / "network-original.json")
        path.symlink_to(root / "network-original.json")
    transport = install_transport(monkeypatch, network_fixture, network)
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and transport.executions == [] and transport.controls == []


def test_changed_generation_is_refused_before_any_native_request(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)
    transport.generation = (*IDENTITY[:6], "fe" * 32, *IDENTITY[7:])
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "sandbox_identity"
    assert transport.executions == [] and transport.controls == []


def test_previous_listener_traffic_is_not_adopted_as_fresh_qualification(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)
    transport.records.append(arrival("previous-run"))
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and transport.executions == [] and transport.controls == []


def test_listener_log_replacement_stops_before_next_request(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)

    def replace(value):
        if transport.controls:
            value["record_identity"]["inode"] += 1
        return value

    transport.observation_action = replace
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "listener_identity"
    assert len(transport.controls) == 1 and transport.executions == []


def test_network_uses_only_remaining_preparation_budget(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    timestamp = time.time() - 870
    os.utime(root / "prepared.json", (timestamp, timestamp))
    transport = install_transport(monkeypatch, network_fixture, network)
    before = time.monotonic()
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "passed"
    assert transport.deadlines and max(transport.deadlines) - before <= 30


def test_failing_listener_positive_control_prevents_workload_probes(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)
    original = transport.guest

    def fail(argv, deadline):
        result = original(argv, deadline)
        if "-c" in argv and constants(argv[argv.index("-c") + 1])["purpose"] == "listener_control":
            return support.probe.CommandResult(0, b'{"schema_version":1,"status":404,"response_sha256":""}', b"")
        return result

    transport.guest = fail
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and transport.executions == []
    assert len(transport.controls) == 1


@pytest.mark.parametrize("outcome,code,status", [("unavailable", 0, 0), ("unavailable", 111, 0),
                                                ("denied", 0, 404), ("denied", 110, 0)])
def test_timeout_refusal_eof_and_fixture_errors_do_not_prove_denial(
        network_fixture, network, monkeypatch, outcome, code, status):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)
    transport.action = lambda op, token, value: value if op == "allowed" else value | {
        "outcome": outcome, "errno": code, "status": status}
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and transport.executions == ["allowed", "denied_method"]


def test_trusted_denied_arrival_still_fails_after_transport_exception(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)

    def arrive_then_fail(operation, token, value):
        if operation == "denied_method":
            transport.records.append(arrival(token, method="POST"))
            raise network.runtime.Refusal("timeout")
        return value

    transport.action = arrive_then_fail
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "network_boundary"
    assert transport.executions == ["allowed", "denied_method"]


def test_network_preserves_truncation_even_when_final_observation_overrides_error(network_fixture, network, monkeypatch):
    root, _, _, observed = network_fixture
    transport = install_transport(monkeypatch, network_fixture, network)

    def overflow(operation, token, value):
        observed["flags"] = 0
        raise network.runtime.Refusal("output_limit", output_limit_bytes=4096)

    transport.action = overflow
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert result["truncation"] == {"transport_output": True, "limit_bytes": 4096}
    assert len(transport.executions) == 1


def test_network_reserves_evidence_capacity_before_native_effects(network_fixture, network, monkeypatch):
    root, _, _, _ = network_fixture
    path = root / "evidence/previous.json"
    with path.open("wb") as stream:
        stream.truncate(10 * 1024 * 1024 - 128 * 1024)
    path.chmod(0o600)
    transport = install_transport(monkeypatch, network_fixture, network)
    result = network.network_probe(network.runtime.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "evidence_limit"
    assert transport.executions == [] and transport.controls == []
    assert path.stat().st_size == 10 * 1024 * 1024 - 128 * 1024


@pytest.mark.parametrize("operation", ["denied_proxy", "denied_clear", "denied_socket"])
def test_fixed_guest_program_really_uses_proxy_free_routes_when_required(network, monkeypatch, operation):
    environment = {"http_proxy": "http://synthetic.invalid", "HTTPS_PROXY": "http://synthetic.invalid",
                   "ALL_PROXY": "http://synthetic.invalid", "NO_PROXY": "*", "KEEP": "present"}
    monkeypatch.setattr(os, "environ", environment)
    original_readlink = os.readlink
    monkeypatch.setattr(os, "readlink", lambda path, *args, **kwargs: "/usr/local/bin/python3.13"
                        if path == "/proc/self/exe" else original_readlink(path, *args, **kwargs))
    calls = []

    class DeniedOpener:
        def open(self, request, timeout):
            calls.append(("http", request.full_url, timeout))
            raise urllib.error.URLError(PermissionError(errno.EACCES, "synthetic denial"))

    def opener(*handlers):
        calls.append(("opener", handlers))
        return DeniedOpener()

    def direct(address, timeout):
        calls.append(("socket", address, timeout))
        raise PermissionError(errno.EACCES, "synthetic denial")

    monkeypatch.setattr(urllib.request, "build_opener", opener)
    monkeypatch.setattr(socket, "create_connection", direct)
    output = StringIO()
    with redirect_stdout(output):
        exec(compile(network._network_program(operation, ADDRESS, "network-unit"), "<fixed-network-program>", "exec"), {})
    result = json.loads(output.getvalue())
    assert result["outcome"] == "denied" and result["errno"] == errno.EACCES
    if operation == "denied_proxy":
        assert environment["http_proxy"] == "http://synthetic.invalid" and calls[0] == ("opener", ())
    else:
        assert environment == {"KEEP": "present"}
        if operation == "denied_clear":
            assert len(calls[0][1]) == 1 and calls[0][1][0].proxies == {}
        else:
            assert calls == [("socket", (ADDRESS, 18081), 3)]


@pytest.mark.parametrize("operation,body,expected", [
    ("denied_method", b'{"error":"policy_denied"}', "denied"),
    ("denied_path", b'{"error":"policy_denied","layer":"l7"}', "denied"),
    ("denied_clear", b'{"error":"ssrf_denied"}', "denied"),
    ("denied_method", b'{"error":"ssrf_denied"}', "unavailable"),
    ("denied_method", b'policy_denied but not JSON', "unavailable"),
    ("denied_method", b'{"error":"other","detail":"policy_denied"}', "unavailable"),
    ("denied_method", b'{"error":["policy_denied"]}', "unavailable"),
])
def test_guest_program_accepts_only_source_verified_policy_denial_body(
        network, monkeypatch, operation, body, expected):
    original_readlink = os.readlink
    monkeypatch.setattr(os, "readlink", lambda path, *args, **kwargs: "/usr/local/bin/python3.13"
                        if path == "/proc/self/exe" else original_readlink(path, *args, **kwargs))
    monkeypatch.setattr(os, "environ", {})

    class Opener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(body))

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    output = StringIO()
    with redirect_stdout(output):
        exec(compile(network._network_program(operation, ADDRESS, "network-unit"), "<fixed-network-program>", "exec"), {})
    assert json.loads(output.getvalue())["outcome"] == expected


@pytest.fixture
def local_listener(tmp_path, listener):
    path = tmp_path / "events.jsonl"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND, 0o600)
    server = listener.ListenerServer(("127.0.0.1", 0), fd)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield server, path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        os.close(fd)
        assert not thread.is_alive()


def request(server, method="GET", path="/probe", headers=None):
    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    try:
        connection.request(method, path, headers={"X-Qualification-Case": "network-unit"} | (headers or {}))
        response = connection.getresponse()
        return response.status, response.read(4096)
    finally:
        connection.close()


def test_listener_serves_fixed_bytes_and_records_actual_arrival(local_listener):
    server, path = local_listener
    assert request(server) == (200, BODY)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["token"] == "network-unit" and rows[0]["accepted"] is True
    assert path.stat().st_mode & 0o777 == 0o600


def test_raw_socket_program_sends_real_http_to_unit_listener_only(network, local_listener, monkeypatch):
    server, records = local_listener
    original_connection, original_readlink = socket.create_connection, os.readlink
    monkeypatch.setattr(os, "environ", {"HTTP_PROXY": "http://must-not-use.invalid"})
    monkeypatch.setattr(os, "readlink", lambda path, *args, **kwargs: "/usr/local/bin/python3.13"
                        if path == "/proc/self/exe" else original_readlink(path, *args, **kwargs))

    def local_only(address, timeout):
        assert address == (ADDRESS, 18081)
        return original_connection(server.server_address, timeout=timeout)

    monkeypatch.setattr(socket, "create_connection", local_only)
    output = StringIO()
    with redirect_stdout(output):
        exec(compile(network._network_program("denied_socket", ADDRESS, "network-unit"), "<fixed-network-program>", "exec"), {})
    result = json.loads(output.getvalue())
    assert result["outcome"] == "allowed" and result["response_sha256"] == hashlib.sha256(BODY).hexdigest()
    assert json.loads(records.read_text())["token"] == "network-unit"
    with pytest.raises(network.runtime.Refusal, match="^network_boundary$"):
        network._validate_result(result, "denied_socket")


@pytest.mark.parametrize("method,path,headers", [
    ("POST", "/probe", {}), ("GET", "/other", {}), ("GET", "/probe?secret=private", {}),
    ("GET", "/probe", {"Upgrade": "websocket", "Connection": "Upgrade"}),
    ("GET", "/../../etc/passwd", {}),
])
def test_listener_rejects_other_requests_without_logging_untrusted_values(local_listener, method, path, headers):
    server, records = local_listener
    status, body = request(server, method, path, headers)
    assert status != 200 and body != BODY
    raw = records.read_text()
    assert "secret=private" not in raw and "/etc/passwd" not in raw
    assert json.loads(raw)["accepted"] is False


def test_listener_records_are_bounded_and_never_overwritten(local_listener):
    server, path = local_listener
    request(server)
    prefix = path.read_bytes()
    server.writer.max_records = 1
    try:
        request(server, headers={"X-Qualification-Case": "second"})
    except (ConnectionError, http.client.HTTPException, TimeoutError, OSError):
        pass
    assert path.read_bytes() == prefix
    assert server.failed is True
