"""Pause qualification with real host observations and simulated native transport."""
from __future__ import annotations

import ast
import builtins
import copy
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from types import SimpleNamespace

import pytest

import test_openshell_runtime as support


owned_root = support.owned_root
pointer_fixture = support.pointer_fixture
guarded_pointer_fixture = support.guarded_pointer_fixture
IDENTITY = tuple(support.GENERATION_IDENTITY.values())
ROLES = ("parent", "child", "background")
ROLE_IDS = {"parent": (2201, 21, 10001), "child": (2202, 22, 10002), "background": (2203, 23, 10003)}
SESSION = "ab" * 16
ADDRESS = "192.168.127.2"
LISTENER_SOURCE = Path(__file__).parent / "fixtures/openshell_runtime/network_listener.py"


def load_module(name, path):
    assert path.is_file(), f"Required pause implementation is absent: {path.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pause():
    sys.modules["probe_openshell_runtime"] = support.probe
    load_module("probe_openshell_network", Path(__file__).with_name("probe_openshell_network.py"))
    return load_module("openshell_pause_under_test", Path(__file__).with_name("probe_openshell_pause.py"))


def write_private(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)


@pytest.fixture
def pause_fixture(guarded_pointer_fixture):
    root, env, guard, observed = guarded_pointer_fixture
    write_private(root / "network.json", {"schema_version": 1, "address": ADDRESS,
                  "listener_pid": 2345, "listener_start_ticks": 4567,
                  "listener_source_sha256": hashlib.sha256(LISTENER_SOURCE.read_bytes()).hexdigest()})
    for index, name in enumerate(("immutable_git_pointer", "containment", "network"), start=1):
        write_private(root / "evidence" / f"pointer-{index:032x}.json", {
            "schema_version": 1, "probe": name, "status": "passed", "reason": None,
            "checks": [], "retained": True, "runtime_qualification": "not_run",
            "generation_sha256": support.generation_digest(),
            "truncation": {"transport_output": False, "limit_bytes": None}})
    return root, env, guard, observed


def state(role, session=SESSION, counter=1, held=False, inflight=False):
    _, inner, ticks = ROLE_IDS[role]
    return {"schema_version": 1, "role": role, "pid": inner, "start_ticks": ticks,
            "session": session, "counter": counter, "held": held, "inflight": inflight, "error": False}


def source_history(value):
    return "".join(f"{value['session']}:{value['role']}:{counter}\n"
                   for counter in range(value["counter"] + 1)).encode()


def write_roles(root, values):
    directory = root / "fixture/task/.openshell-pause"
    directory.mkdir(mode=0o700, exist_ok=True)
    for role, value in values.items():
        write_private(directory / f"{role}.json", value)
        source = directory / f"{role}.txt"
        source.write_bytes(source_history(value))
        source.chmod(0o600)


def native_snapshot(paused=False):
    return {"container_id": IDENTITY[3], "container_pid": IDENTITY[4],
            "container_started_at": IDENTITY[5], "paused": paused, "frozen": paused,
            "cgroup": "/sys/fs/cgroup/user.slice/qualification.scope", "cpu_usage_usec": 1000,
            "members": [{"pid": 1234, "start_ticks": 9000, "inner_pid": 1},
                        *[{"pid": guest, "start_ticks": ticks, "inner_pid": inner}
                          for guest, inner, ticks in ROLE_IDS.values()]]}


@pytest.mark.parametrize("paused", [False, True])
def test_native_snapshot_binds_guest_and_namespace_process_identities(pause, paused):
    value = native_snapshot(paused)
    assert pause._validate_native_snapshot(value, IDENTITY, paused) == value
    assert value["members"][1]["pid"] != value["members"][1]["inner_pid"]


@pytest.mark.parametrize("violation", [
    "wrong_container", "wrong_container_pid", "wrong_start", "not_frozen", "boolean_cpu",
    "negative_cpu", "path_escape", "duplicate_pid", "duplicate_inner_pid", "missing_container",
    "boolean_start", "wrong_container_inner", "unknown_field",
])
def test_native_snapshot_refuses_ambiguous_or_unfrozen_observation(pause, violation):
    value = native_snapshot(True)
    if violation == "wrong_container":
        value["container_id"] = "ef" * 32
    elif violation == "wrong_container_pid":
        value["container_pid"] = 5678
    elif violation == "wrong_start":
        value["container_started_at"] = "replacement"
    elif violation == "not_frozen":
        value["frozen"] = False
    elif violation == "boolean_cpu":
        value["cpu_usage_usec"] = True
    elif violation == "negative_cpu":
        value["cpu_usage_usec"] = -1
    elif violation == "path_escape":
        value["cgroup"] = "/sys/fs/cgroup/../unrelated"
    elif violation == "duplicate_pid":
        value["members"][2]["pid"] = value["members"][1]["pid"]
    elif violation == "duplicate_inner_pid":
        value["members"][2]["inner_pid"] = value["members"][1]["inner_pid"]
    elif violation == "missing_container":
        value["members"].pop(0)
    elif violation == "boolean_start":
        value["members"][1]["start_ticks"] = True
    elif violation == "wrong_container_inner":
        value["members"][0]["inner_pid"] = 99
    else:
        value["extra"] = "private native marker"
    with pytest.raises(support.probe.Refusal):
        pause._validate_native_snapshot(value, IDENTITY, True)


def test_role_snapshot_verifies_exact_acknowledged_source_history(pause_fixture, pause):
    root, _, _, _ = pause_fixture
    values = {role: state(role, counter=2) for role in ROLES}
    write_roles(root, values)
    result = pause._role_snapshot(root, SESSION)
    assert set(result) == set(ROLES)
    for role in ROLES:
        assert result[role] == {"state": values[role],
                                "source_sha256": hashlib.sha256(source_history(values[role])).hexdigest()}


@pytest.mark.parametrize("violation", [
    "missing_role", "wrong_session", "boolean_counter", "counter_limit", "wrong_role",
    "zero_start", "source_mismatch", "lost_history", "hardlink", "source_alias", "unsafe_state",
])
def test_role_snapshot_rejects_unverified_or_substituted_host_evidence(pause_fixture, pause, violation):
    root, _, _, _ = pause_fixture
    values = {role: state(role, counter=2) for role in ROLES}
    if violation == "wrong_session":
        values["child"]["session"] = "cd" * 16
    elif violation == "boolean_counter":
        values["child"]["counter"] = True
    elif violation == "counter_limit":
        values["child"]["counter"] = 56
    elif violation == "wrong_role":
        values["child"]["role"] = "parent"
    elif violation == "zero_start":
        values["child"]["start_ticks"] = 0
    write_roles(root, values)
    directory = root / "fixture/task/.openshell-pause"
    source = directory / "child.txt"
    if violation == "missing_role":
        (directory / "child.json").unlink()
    elif violation == "source_mismatch":
        source.write_bytes(b"private wrong bytes")
    elif violation == "lost_history":
        source.write_bytes(f"{SESSION}:child:2\n".encode())
    elif violation == "hardlink":
        os.link(source, directory / "other-source")
    elif violation == "source_alias":
        source.unlink()
        source.symlink_to(directory / "parent.txt")
    elif violation == "unsafe_state":
        (directory / "child.json").chmod(0o644)
    with pytest.raises((support.probe.Refusal, FileNotFoundError)):
        pause._role_snapshot(root, SESSION)


@pytest.mark.parametrize("violation", [
    "missing_pointer", "missing_containment", "missing_network", "wrong_generation", "not_retained",
    "same_generation_failed", "same_generation_unavailable", "unsafe_receipt", "boolean_schema",
])
def test_pause_prerequisites_require_all_retained_same_generation_passes(pause_fixture, pause, violation):
    root, _, _, _ = pause_fixture
    paths = sorted((root / "evidence").glob("pointer-*.json"))
    if violation.startswith("missing_"):
        paths[{"missing_pointer": 0, "missing_containment": 1, "missing_network": 2}[violation]].unlink()
    else:
        value = json.loads(paths[2].read_text())
        if violation == "wrong_generation":
            value["generation_sha256"] = "ef" * 32
        elif violation == "not_retained":
            value["retained"] = False
        elif violation.startswith("same_generation_"):
            value.update(status="failed" if violation.endswith("failed") else "unavailable", reason="observed_failure")
            write_private(root / "evidence" / ("pointer-" + "f" * 32 + ".json"), value)
        elif violation == "boolean_schema":
            value["schema_version"] = True
        if not violation.startswith("same_generation_"):
            write_private(paths[2], value)
        if violation == "unsafe_receipt":
            paths[2].chmod(0o644)
    with pytest.raises(support.probe.Refusal):
        pause._require_prerequisites(root, support.generation_digest())


class Clock:
    def __init__(self):
        self.now = time.monotonic()
        self.transport = None

    def sleep(self, seconds):
        assert 0 <= seconds <= 1
        self.now += seconds
        if self.transport:
            self.transport.advance(seconds)


class PauseTransport:
    """Independent native/listener views plus genuine host state and source files."""

    def __init__(self, root, env, pause, clock, observed):
        self.root, self.env, self.pause_module, self.clock = root, env, pause, clock
        self.observed = observed
        self.guest_home, self.guest_uid = "/home/fixture", 1000
        self.prepared = {"sandbox_id": IDENTITY[0], "container_id": IDENTITY[3]}
        self.sandbox_name = root.name.removeprefix("openshell-")
        self.paused = False
        self.launched = False
        self.resumed = False
        self.session = None
        self.roles = {}
        self.records = []
        self.controls = []
        self.observations = []
        self.deadlines = []
        self.cpu = 1000
        self.accumulated = 0
        self.fault = None

    def bounded(self, deadline):
        assert 0 < deadline - self.clock.now <= 60
        self.deadlines.append(deadline)

    def identity(self, deadline):
        self.bounded(deadline)
        assert not self.paused, "ordinary running identity must not observe a frozen workload"
        if self.resumed and self.fault == "resume_generation":
            return ("replacement", *IDENTITY[1:])
        return IDENTITY

    def append_arrival(self, role):
        self.records.append({"schema_version": 1, "token": f"pause-{self.session}-{role}",
                             "port": 18080, "method": "GET", "path": "/probe", "accepted": True})

    def launch(self, session, address, deadline):
        self.bounded(deadline)
        assert re.fullmatch(r"[a-f0-9]{32}", session) and address == ADDRESS
        assert not self.launched
        self.launched, self.session = True, session
        self.roles = {role: state(role, session, counter=0) for role in ROLES}
        write_roles(self.root, self.roles)
        for role in ROLES:
            self.append_arrival(role)
        return {"schema_version": 1, "session": session, "started": True}

    def advance(self, seconds):
        if not self.launched:
            return
        if self.paused:
            if self.fault == "frozen_counter":
                self.roles["background"]["counter"] += 1
                write_roles(self.root, self.roles)
            elif self.fault == "frozen_cpu":
                self.cpu += 1
            elif self.fault == "frozen_arrival":
                self.records.append({"schema_version": 1, "token": "unrelated-arrival",
                                     "port": 18080, "method": "GET", "path": "/probe", "accepted": True})
            return
        held = (self.root / "fixture/task/.openshell-pause/hold").exists()
        if held:
            for role, value in self.roles.items():
                value["held"] = not (self.fault in {"hold_inflight", "guard_hold_timeout"} and role == "background")
                value["inflight"] = not value["held"]
            if self.fault == "guard_hold_timeout":
                self.observed["flags"] = 0
            write_roles(self.root, self.roles)
            return
        self.accumulated += seconds
        if self.accumulated < 0.999:
            return
        self.accumulated = 0
        self.cpu += 100
        for role, value in self.roles.items():
            value["held"], value["inflight"] = False, False
            if self.resumed and self.fault == "resume_counter" and role == "background":
                continue
            value["counter"] += 1
            if not (self.resumed and self.fault == "resume_arrival" and role == "background"):
                self.append_arrival(role)
        if self.resumed and self.fault in {"resume_pid", "resume_start", "resume_session"}:
            key, value = {"resume_pid": ("pid", 99), "resume_start": ("start_ticks", 99999),
                          "resume_session": ("session", "cd" * 16)}[self.fault]
            self.roles["background"][key] = value
        write_roles(self.root, self.roles)

    def snapshot(self, deadline, paused):
        self.bounded(deadline)
        assert paused is self.paused
        value = native_snapshot(paused)
        value["cpu_usage_usec"] = self.cpu
        if paused and self.fault == "not_frozen":
            value["frozen"] = False
        if paused and self.fault == "frozen_members" and any(entry[1] for entry in self.observations):
            value["members"].append({"pid": 2300, "inner_pid": 30, "start_ticks": 12345})
        self.observations.append((self.clock.now, paused, copy.deepcopy(value)))
        return self.pause_module._validate_native_snapshot(value, IDENTITY, paused)

    def pause(self, deadline):
        self.bounded(deadline)
        assert all(value["held"] and not value["inflight"] for value in self.roles.values())
        hold = self.root / "fixture/task/.openshell-pause/hold"
        assert hold.read_bytes() == b"hold\n" and stat.S_IMODE(hold.stat().st_mode) == 0o600
        self.controls.append(("pause", IDENTITY[3]))
        self.paused = True

    def unpause(self, deadline):
        self.bounded(deadline)
        assert self.paused
        self.controls.append(("unpause", IDENTITY[3]))
        self.paused, self.resumed = False, True

    def gateway(self, deadline):
        self.bounded(deadline)
        assert self.paused
        self.controls.append(("gateway", IDENTITY[0]))
        if self.fault in {"gateway_error", "guard_and_gateway_error"}:
            if self.fault == "guard_and_gateway_error":
                self.observed["flags"] = 0
            raise support.probe.Refusal("gateway_unavailable")
        return True

    def guest(self, argv, deadline):
        self.bounded(deadline)
        program = argv[argv.index("-c") + 1]
        constants = {}
        for node in ast.parse(program).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                try:
                    constants[node.targets[0].id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
        assert constants.get("purpose") == "listener_observation"
        raw = b"".join((json.dumps(row) + "\n").encode() for row in self.records)
        value = {"address": ADDRESS, "pid": 2345, "start_ticks": 4567, "uid": 1000,
                 "source_sha256": hashlib.sha256(LISTENER_SOURCE.read_bytes()).hexdigest(),
                 "socket_inodes": {"18080": 101, "18081": 102},
                 "record_identity": {"device": 1, "inode": 300, "uid": 1000,
                                     "mode": stat.S_IFREG | 0o600, "link_count": 1},
                 "record_size": len(raw), "records": copy.deepcopy(self.records)}
        return support.probe.CommandResult(0, json.dumps(value).encode(), b"")


def install_transport(pause_fixture, pause, monkeypatch):
    root, env, _, observed = pause_fixture
    clock = Clock()
    transport = PauseTransport(root, env, pause, clock, observed)
    clock.transport = transport
    monkeypatch.setattr(pause.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(pause.time, "sleep", clock.sleep)
    monkeypatch.setattr(pause, "_PauseController", lambda selection, deadline: transport)
    return transport, clock


def test_pause_requires_independent_freeze_gateway_and_every_role_resume(pause_fixture, pause, monkeypatch):
    root, _, _, _ = pause_fixture
    transport, clock = install_transport(pause_fixture, pause, monkeypatch)
    started = clock.now
    result = pause.pause_resume_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "passed" and result["probe"] == "pause_resume"
    assert result["generation_sha256"] == support.generation_digest()
    assert result["runtime_qualification"] == "not_run" and result["retained"] is True
    assert result["workload_state"] == "running"
    assert [command for command, _ in transport.controls] == ["pause", "gateway", "unpause"]
    frozen = [item for item in transport.observations if item[1]]
    assert len(frozen) >= 2 and frozen[-1][0] - frozen[0][0] >= 1
    assert frozen[0][2] == frozen[-1][2]
    assert 0 < clock.now - started <= 60
    assert all(value["counter"] >= 2 for value in transport.roles.values())
    assert all(any(row["token"] == f"pause-{transport.session}-{role}" for row in transport.records) for role in ROLES)
    assert {check["operation"] for check in result["checks"]} == {"progress", "pause", "gateway", "resume"}
    assert any(json.loads(path.read_text()) == result for path in (root / "evidence").glob("pointer-*.json"))


@pytest.mark.parametrize("fault", ["not_frozen", "frozen_counter", "frozen_cpu", "frozen_members", "frozen_arrival", "gateway_error"])
def test_failed_frozen_observation_never_automatically_unpauses(pause_fixture, pause, monkeypatch, fault):
    root, _, _, _ = pause_fixture
    transport, _ = install_transport(pause_fixture, pause, monkeypatch)
    transport.fault = fault
    result = pause.pause_resume_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] != "passed" and result["runtime_qualification"] == "not_run"
    assert transport.paused and result["workload_state"] == "paused"
    assert not any(command == "unpause" for command, _ in transport.controls)
    assert result["retained"] is True


def test_requests_must_drain_before_pause(pause_fixture, pause, monkeypatch):
    root, _, _, _ = pause_fixture
    transport, clock = install_transport(pause_fixture, pause, monkeypatch)
    transport.fault = "hold_inflight"
    started = clock.now
    result = pause.pause_resume_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "pause_timeout"
    assert transport.controls == [] and not transport.paused
    assert clock.now - started <= 60


@pytest.mark.parametrize("fault", ["resume_pid", "resume_start", "resume_session", "resume_generation", "resume_counter", "resume_arrival"])
def test_resume_requires_same_identities_and_progress_from_every_role(pause_fixture, pause, monkeypatch, fault):
    root, _, _, _ = pause_fixture
    transport, _ = install_transport(pause_fixture, pause, monkeypatch)
    transport.fault = fault
    result = pause.pause_resume_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] != "passed" and result["runtime_qualification"] == "not_run"
    assert transport.resumed
    assert [command for command, _ in transport.controls].count("unpause") == 1


def test_host_guard_failure_wins_over_error_while_paused(pause_fixture, pause, monkeypatch):
    root, _, _, observed = pause_fixture
    transport, _ = install_transport(pause_fixture, pause, monkeypatch)
    transport.fault = "guard_and_gateway_error"
    result = pause.pause_resume_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert observed["flags"] == 0 and transport.paused
    assert not any(command == "unpause" for command, _ in transport.controls)


def test_pause_uses_remaining_experiment_window_instead_of_new_sixty_seconds(pause_fixture, pause, monkeypatch):
    root, _, _, _ = pause_fixture
    stamp = time.time() - 870
    os.utime(root / "prepared.json", (stamp, stamp))
    transport, clock = install_transport(pause_fixture, pause, monkeypatch)
    transport.fault = "hold_inflight"
    started = clock.now
    result = pause.pause_resume_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "pause_timeout"
    assert 0 < clock.now - started <= 30
    assert max(transport.deadlines) - started <= 30
    assert not transport.controls


def test_host_guard_is_observed_after_hold_wait_times_out(pause_fixture, pause, monkeypatch):
    root, _, _, observed = pause_fixture
    transport, _ = install_transport(pause_fixture, pause, monkeypatch)
    transport.fault = "guard_hold_timeout"
    result = pause.pause_resume_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert observed["flags"] == 0 and transport.controls == []
    assert result["retained"] is True


def native_controller(pause_fixture, pause):
    root, _, _, _ = pause_fixture
    controller = object.__new__(pause._PauseController)
    controller.root = root
    controller.prepared = {"sandbox_id": IDENTITY[0], "container_id": IDENTITY[3]}
    controller.sandbox_name = root.name.removeprefix("openshell-")
    return controller


@pytest.mark.parametrize("violation", ["policy_version", "config_revision", "provider_env_revision", "current_policy_version", "admission_not_object"])
def test_gateway_native_observation_rejects_malformed_identity(pause_fixture, pause, violation):
    controller = native_controller(pause_fixture, pause)
    value = {"id": IDENTITY[0], "name": controller.sandbox_name,
             "main_process_instance_id": IDENTITY[1], "main_process_started_at_ms": IDENTITY[2],
             "current_policy_version": 1, "configuration_admission": {
                 "state": "accepted", "policy_hash": IDENTITY[6], "policy_version": 1,
                 "config_revision": 1, "provider_env_revision": 1}}
    if violation == "current_policy_version":
        value["current_policy_version"] = True
    elif violation == "admission_not_object":
        value["configuration_admission"] = []
    else:
        value["configuration_admission"][violation] = True
    controller.guest = lambda argv, deadline: support.probe.CommandResult(0, json.dumps(value).encode(), b"")
    with pytest.raises(support.probe.Refusal, match="^sandbox_identity$"):
        controller.gateway(time.monotonic() + 60)


@pytest.mark.parametrize("kernel_available", [False, True])
def test_frozen_native_parser_separates_kernel_gap_from_observed_violation(pause_fixture, pause, kernel_available):
    controller = native_controller(pause_fixture, pause)
    expected = native_snapshot(True)
    item = {"Id": IDENTITY[3], "State": {"Running": True, "Paused": True,
             "Pid": IDENTITY[4], "StartedAt": IDENTITY[5]}, "Config": {"Labels": {
                 "openshell.managed": "true", "openshell.ai/isolation-role": "sandbox",
                 "openshell.ai/sandbox-id": IDENTITY[0]}}}
    kernel = {key: expected[key] for key in ("cgroup", "cpu_usage_usec", "frozen", "members")}
    calls = []

    def guest(argv, deadline):
        calls.append(argv)
        if argv[0] == "/usr/bin/podman":
            assert argv == ["/usr/bin/podman", "inspect", "--type", "container", IDENTITY[3]]
            value = [item]
        else:
            assert "-c" in argv and argv[-1] == str(IDENTITY[4])
            value = kernel if kernel_available else {"error": "native_snapshot_unavailable"}
        return support.probe.CommandResult(0, json.dumps(value).encode(), b"")

    def forbidden(deadline):
        raise AssertionError("the frozen observer must not require ordinary running identity")

    controller.guest, controller.identity = guest, forbidden
    if kernel_available:
        assert controller.snapshot(time.monotonic() + 60, True) == expected
    else:
        with pytest.raises(support.probe.Refusal, match="^native_snapshot_unavailable$"):
            controller.snapshot(time.monotonic() + 60, True)
    assert len(calls) == 2


def test_generated_roles_arm_their_own_remaining_lifetime_before_blocking_io(pause):
    """Intercept every fork, signal and I/O call while exercising actual role code."""
    events = []
    clock = SimpleNamespace(now=100.0)

    class StopBeforeIO(BaseException):
        pass

    def open_file(path, *args, **kwargs):
        assert path == "/proc/self/stat"
        events.append(("first_io", path))
        raise StopBeforeIO

    def set_handler(number, handler):
        assert number == 14 and handler == 0
        events.append(("handler", number))

    def set_timer(kind, delay):
        assert kind == 0
        events.append(("timer", delay))

    def mkdir(path, mode):
        assert path == "/work/.openshell-pause" and mode == 0o700

    fake_os = SimpleNamespace(mkdir=mkdir, fork=lambda: 1234)
    modules = {"http.client": SimpleNamespace(client=SimpleNamespace()), "json": json, "os": fake_os,
               "time": SimpleNamespace(monotonic=lambda: clock.now),
               "signal": SimpleNamespace(SIGALRM=14, SIG_DFL=0, ITIMER_REAL=0,
                                          signal=set_handler, setitimer=set_timer)}

    def isolated_import(name, *args, **kwargs):
        assert name in modules, "unexpected import must not reach the host"
        return modules[name]

    namespace = {"__builtins__": vars(builtins) | {"__import__": isolated_import, "open": open_file}}
    output = StringIO()
    with redirect_stdout(output):
        exec(compile(pause._fixture_program(SESSION, ADDRESS), "<fixed-pause-fixture>", "exec"), namespace)
    assert json.loads(output.getvalue()) == {"schema_version": 1, "session": SESSION, "started": True}
    assert events == []  # A timer only in the launching parent would not survive fork.
    clock.now = 107.0
    for role in ROLES:
        events.clear()
        with pytest.raises(StopBeforeIO):
            namespace["role_loop"](role)
        assert [kind for kind, _ in events] == ["handler", "timer", "first_io"]
        assert 0 < events[1][1] <= 48.0  # Seven seconds elapsed from the shared 55-second lifetime.
