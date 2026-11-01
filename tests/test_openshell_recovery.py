"""Controlled recovery contracts; no service, worker or host flag operations."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time

import pytest

import test_openshell_runtime as support


owned_root = support.owned_root
pointer_fixture = support.pointer_fixture
guarded_pointer_fixture = support.guarded_pointer_fixture
IDENTITY = tuple(support.GENERATION_IDENTITY.values())
TEXT = b"openshell recovery checkpoint\n"
BINARY = bytes(range(256))
STORAGE = b"openshell storage object\n"
UNACKNOWLEDGED = b"openshell unacknowledged marker\n"
BOOT_BEFORE = "11111111-1111-4111-8111-111111111111"
BOOT_AFTER = "22222222-2222-4222-8222-222222222222"
PREREQUISITES = ("immutable_git_pointer", "containment", "boundaries", "network", "pause_resume")


@pytest.fixture(scope="module")
def recovery():
    sys.modules["probe_openshell_runtime"] = support.probe
    path = Path(__file__).with_name("probe_openshell_recovery.py")
    assert path.is_file(), "Required recovery implementation is absent"
    spec = importlib.util.spec_from_file_location("openshell_recovery_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_private(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)


@pytest.fixture
def recovery_fixture(guarded_pointer_fixture):
    root, env, guard, observed = guarded_pointer_fixture
    (root / "lima/q").mkdir(mode=0o700)
    worker_config = root / "lima/q/lima.yaml"
    worker_config.write_bytes(b"cpus: 4\nmemory: 8GiB\n")
    worker_config.chmod(0o600)
    write_private(root / "worker-config.json", {"schema_version": 1,
                  "sha256": hashlib.sha256(worker_config.read_bytes()).hexdigest()})
    for index, name in enumerate(PREREQUISITES, start=1):
        write_private(root / "evidence" / f"pointer-{index:032x}.json", {
            "schema_version": 1, "probe": name, "status": "passed", "reason": None,
            "checks": [], "retained": True, "runtime_qualification": "not_run",
            "generation_sha256": support.generation_digest(),
            "truncation": {"transport_output": False, "limit_bytes": None}})
    return root, env, guard, observed


def gateway_state(active=True):
    return {"unit": "openshell-gateway.service", "active": active,
            "pid": 3001 if active else 0, "start_ticks": 20001 if active else 0,
            "configuration_sha256": "ef" * 32}


def worker_state(running=True, boot_id=BOOT_BEFORE):
    return {"boot_id": boot_id, "container_id": IDENTITY[3], "running": running,
            "pid": IDENTITY[4] if running else 0, "start_ticks": 10001 if running else 0}


@pytest.mark.parametrize("active", [False, True])
def test_gateway_native_state_requires_exact_owned_unit(recovery, active):
    value = gateway_state(active)
    assert recovery._validate_gateway_state(value, active) == value


@pytest.mark.parametrize("change", [
    {"unit": "unrelated.service"}, {"active": 1}, {"pid": True}, {"start_ticks": True},
    {"pid": 0}, {"configuration_sha256": "EF" * 32}, {"unexpected": "private native value"},
])
def test_gateway_native_state_rejects_invalid_identity(recovery, change):
    with pytest.raises(support.probe.Refusal):
        recovery._validate_gateway_state(gateway_state() | change, True)


def test_inactive_gateway_requires_zero_process_identity(recovery):
    with pytest.raises(support.probe.Refusal):
        recovery._validate_gateway_state(gateway_state(False) | {"pid": 3001}, False)


@pytest.mark.parametrize("running", [False, True])
def test_worker_native_state_preserves_boot_identity_and_container(recovery, running):
    value = worker_state(running)
    assert recovery._validate_worker_state(value, IDENTITY[3]) == value


@pytest.mark.parametrize("change", [
    {"boot_id": "not-a-boot-uuid"}, {"container_id": "ab" * 32}, {"running": 1},
    {"pid": True}, {"pid": 0}, {"start_ticks": True}, {"start_ticks": 0},
    {"unexpected": "private native value"},
])
def test_worker_native_state_rejects_ambiguous_identity(recovery, change):
    with pytest.raises(support.probe.Refusal):
        recovery._validate_worker_state(worker_state() | change, IDENTITY[3])


def create_checkpoints(root):
    directory = root / "fixture/task/.openshell-recovery"
    directory.mkdir(mode=0o700)
    for name, content in (("text", TEXT), ("binary", BINARY), ("storage", STORAGE)):
        path = directory / name
        path.write_bytes(content)
        path.chmod(0o600)
    return directory


@pytest.mark.parametrize("unacknowledged", ["present", "absent", "changed"])
def test_checkpoint_observation_does_not_promote_unacknowledged_marker(
        recovery_fixture, recovery, unacknowledged):
    root, _, _, _ = recovery_fixture
    directory = create_checkpoints(root)
    baseline = recovery._checkpoint_snapshot(root)
    assert set(baseline) == {"text", "binary"}
    if unacknowledged != "absent":
        path = directory / "unacknowledged"
        path.write_bytes(UNACKNOWLEDGED if unacknowledged == "present" else b"changed unacknowledged bytes")
        path.chmod(0o600)
    assert recovery._verify_checkpoints(root, baseline) == {
        "acknowledged": "preserved", "unacknowledged": unacknowledged}


@pytest.mark.parametrize("violation", ["wrong_bytes", "same_bytes_new_inode", "hardlink", "alias", "unsafe_mode"])
def test_acknowledged_checkpoint_identity_cannot_be_substituted(recovery_fixture, recovery, violation):
    root, _, _, _ = recovery_fixture
    directory = create_checkpoints(root)
    baseline = recovery._checkpoint_snapshot(root)
    path = directory / "text"
    if violation == "wrong_bytes":
        path.write_bytes(b"lost acknowledged content")
    elif violation == "same_bytes_new_inode":
        new = directory / "replacement"
        new.write_bytes(TEXT)
        new.chmod(0o600)
        new.replace(path)
    elif violation == "hardlink":
        os.link(path, directory / "other-link")
    elif violation == "alias":
        path.unlink()
        path.symlink_to(directory / "binary")
    else:
        path.chmod(0o644)
    with pytest.raises((support.probe.Refusal, OSError)):
        recovery._verify_checkpoints(root, baseline)


class Clock:
    def __init__(self):
        self.now = time.monotonic()

    def sleep(self, seconds):
        assert 0 <= seconds <= 1
        self.now += seconds


class RecoveryTransport:
    """Native control is simulated; checkpoint bytes and storage modes are real."""

    def __init__(self, root, env, clock, observed):
        self.root, self.env, self.clock, self.observed = root, env, clock, observed
        self.guest_home, self.guest_uid = "/home/fixture", 1000
        self.prepared = {"sandbox_id": IDENTITY[0], "container_id": IDENTITY[3]}
        self.gateway = gateway_state()
        self.worker = worker_state()
        self.vm_stopped = False
        self.restarted = False
        self.calls = []
        self.deadlines = []
        self.case_delay = 0
        self.fault = None

    def bounded(self, operation, deadline):
        assert 0 < deadline - self.clock.now <= 60
        self.calls.append(operation)
        self.deadlines.append((operation, self.clock.now, deadline))

    def delay(self, deadline):
        remaining = deadline - self.clock.now
        if self.case_delay >= remaining:
            self.clock.now += remaining
            raise support.probe.Refusal("timeout")
        self.clock.now += self.case_delay

    def identity(self, deadline):
        self.bounded("identity", deadline)
        assert self.gateway["active"] and not self.vm_stopped
        assert not self.restarted, "worker restart must use its dedicated observer, never ordinary resume identity"
        if self.fault == "gateway_generation" and self.gateway["pid"] != 3001:
            return (*IDENTITY[:4], 5678, *IDENTITY[5:])
        return IDENTITY

    def execute(self, program, deadline):
        assignment = next(node for node in ast.parse(program).body
                          if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple))
        operation, _ = ast.literal_eval(assignment.value)
        self.bounded(operation, deadline)
        assert operation in {"checkpoint_create", "unacknowledged_create", "storage_open"}
        directory = self.root / "fixture/task/.openshell-recovery"
        if operation == "checkpoint_create":
            create_checkpoints(self.root)
            return {"schema_version": 1, "operation": operation, "outcome": "succeeded"}
        if operation == "unacknowledged_create":
            path = directory / "unacknowledged"
            path.write_bytes(UNACKNOWLEDGED)
            path.chmod(0o600)
            return {"schema_version": 1, "operation": operation, "outcome": "succeeded"}
        path = directory / "storage"
        denied = stat.S_IMODE(path.stat().st_mode) == 0
        if denied:
            self.delay(deadline)
            if self.fault in {"storage_timeout", "guard_storage_timeout"}:
                if self.fault == "guard_storage_timeout":
                    self.observed["flags"] = 0
                raise support.probe.Refusal("timeout")
            if self.fault == "storage_replacement":
                path.rename(directory / "retained-original-storage")
                path.write_bytes(b"replacement storage")
                path.chmod(0o600)
            if self.fault == "storage_allowed":
                return {"schema_version": 1, "operation": operation, "outcome": "read", "errno": 0,
                        "sha256": hashlib.sha256(STORAGE).hexdigest()}
            return {"schema_version": 1, "operation": operation, "outcome": "denied",
                    "errno": 30 if self.fault == "storage_wrong_denial" else 13, "sha256": None}
        return {"schema_version": 1, "operation": operation, "outcome": "read", "errno": 0,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def gateway_state(self, deadline):
        self.bounded("gateway_state", deadline)
        assert not self.vm_stopped
        return copy.deepcopy(self.gateway)

    def gateway_stop(self, deadline):
        self.bounded("gateway_stop", deadline)
        self.gateway = gateway_state(False)
        if self.fault == "gateway_stop_unobserved":
            self.gateway = gateway_state(True)

    def gateway_start(self, deadline):
        self.bounded("gateway_start", deadline)
        assert not self.gateway["active"]
        self.delay(deadline)
        self.gateway = gateway_state(True) | {"pid": 3002, "start_ticks": 20002}
        if self.fault == "gateway_configuration":
            self.gateway["configuration_sha256"] = "ab" * 32
        elif self.fault == "gateway_checkpoint_loss":
            (self.root / "fixture/task/.openshell-recovery/text").write_bytes(b"lost checkpoint")
        elif self.fault == "guard_gateway_error":
            self.observed["flags"] = 0
            raise support.probe.Refusal("timeout")

    def worker_state(self, deadline):
        self.bounded("worker_state", deadline)
        assert not self.vm_stopped
        return copy.deepcopy(self.worker)

    def worker_stop(self, deadline):
        self.bounded("worker_stop", deadline)
        self.vm_stopped = True
        if self.fault == "drop_unacknowledged":
            (self.root / "fixture/task/.openshell-recovery/unacknowledged").unlink()
        elif self.fault == "configuration_after_stop":
            (self.root / "lima/q/lima.yaml").write_bytes(b"changed worker configuration\n")

    def worker_stopped(self, deadline):
        self.bounded("worker_stopped", deadline)
        return self.vm_stopped and self.fault != "worker_stop_unobserved"

    def worker_start(self, deadline):
        self.bounded("worker_start", deadline)
        assert self.vm_stopped
        self.delay(deadline)
        self.vm_stopped, self.restarted = False, True
        boot = BOOT_BEFORE if self.fault == "unchanged_boot" else BOOT_AFTER
        self.worker = worker_state(False, boot)
        if self.fault == "worker_checkpoint_loss":
            (self.root / "fixture/task/.openshell-recovery/binary").write_bytes(b"lost checkpoint")
        elif self.fault == "configuration_after_restart":
            (self.root / "lima/q/lima.yaml").write_bytes(b"changed worker configuration\n")


def install_transport(recovery_fixture, recovery, monkeypatch):
    root, env, _, observed = recovery_fixture
    clock = Clock()
    transport = RecoveryTransport(root, env, clock, observed)
    monkeypatch.setattr(recovery.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(recovery.time, "sleep", clock.sleep)
    monkeypatch.setattr(recovery, "_RecoveryController", lambda selection, deadline: transport)
    return transport, clock


@pytest.mark.parametrize("missing", PREREQUISITES)
def test_recovery_requires_every_prior_same_generation_pass_before_native_effects(
        recovery_fixture, recovery, monkeypatch, missing):
    root, _, _, _ = recovery_fixture
    for path in (root / "evidence").glob("pointer-*.json"):
        if json.loads(path.read_text())["probe"] == missing:
            path.unlink()
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("native")
        raise AssertionError("recovery prerequisites must be verified before native control")

    monkeypatch.setattr(recovery, "_RecoveryController", forbidden)
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "unavailable" and calls == []


@pytest.mark.parametrize("change", [{"generation_sha256": "ef" * 32}, {"retained": False},
                                    {"status": "failed", "reason": "observed_failure"}])
def test_recovery_cannot_adopt_incomplete_or_other_generation_evidence(
        recovery_fixture, recovery, monkeypatch, change):
    root, _, _, _ = recovery_fixture
    path = root / "evidence" / f"pointer-{5:032x}.json"
    write_private(path, json.loads(path.read_text()) | change)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("native")
        raise AssertionError("invalid previous evidence must stop before native control")

    monkeypatch.setattr(recovery, "_RecoveryController", forbidden)
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "unavailable" and calls == []


@pytest.mark.parametrize("violation", ["missing", "boolean_schema", "unknown_field", "wrong_hash", "unsafe_receipt", "changed_configuration", "configuration_alias"])
def test_worker_configuration_is_bound_before_any_native_effect(recovery_fixture, recovery, monkeypatch, violation):
    root, _, _, _ = recovery_fixture
    receipt = root / "worker-config.json"
    value = json.loads(receipt.read_text())
    if violation == "missing":
        receipt.unlink()
    else:
        if violation == "boolean_schema":
            value["schema_version"] = True
        elif violation == "unknown_field":
            value["extra"] = "private configuration marker"
        elif violation == "wrong_hash":
            value["sha256"] = "ab" * 32
        write_private(receipt, value)
    configuration = root / "lima/q/lima.yaml"
    if violation == "unsafe_receipt":
        receipt.chmod(0o644)
    elif violation == "changed_configuration":
        configuration.write_bytes(b"changed worker configuration\n")
    elif violation == "configuration_alias":
        configuration.rename(root / "original-lima.yaml")
        configuration.symlink_to(root / "original-lima.yaml")
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("native")
        raise AssertionError("unknown worker configuration must stop before native control")

    monkeypatch.setattr(recovery, "_RecoveryController", forbidden)
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "unavailable" and calls == []


@pytest.mark.parametrize("drop_unacknowledged", [False, True])
def test_recovery_preserves_acknowledged_work_without_claiming_physical_durability(
        recovery_fixture, recovery, monkeypatch, drop_unacknowledged):
    root, _, _, _ = recovery_fixture
    transport, _ = install_transport(recovery_fixture, recovery, monkeypatch)
    if drop_unacknowledged:
        transport.fault = "drop_unacknowledged"
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "passed" and result["probe"] == "recovery"
    assert result["recovery_kind"] == "worker_restart" and result["worker_state"] == "restarted"
    assert result["unacknowledged_state"] == ("absent" if drop_unacknowledged else "present")
    assert result["physical_storage_loss"] == result["abrupt_host_power_loss"] == "not_run"
    assert result["runtime_qualification"] == "not_run" and result["generation_sha256"] == support.generation_digest()
    assert result["retained"] is True
    assert {row["operation"] for row in result["checks"]} == {
        "checkpoint", "gateway_interruption", "storage_permission_denial", "worker_restart"}
    assert transport.calls.index("gateway_stop") < transport.calls.index("gateway_start")
    assert transport.calls.index("worker_stop") < transport.calls.index("worker_start")
    assert not any("resume" in call or "create_workload" in call for call in transport.calls)
    assert (root / "fixture/task/.openshell-recovery/text").read_bytes() == TEXT
    assert (root / "fixture/task/.openshell-recovery/binary").read_bytes() == BINARY
    assert any(json.loads(path.read_text()) == result for path in (root / "evidence").glob("pointer-*.json"))


@pytest.mark.parametrize("fault", ["gateway_stop_unobserved", "gateway_generation", "gateway_configuration", "gateway_checkpoint_loss"])
def test_failed_gateway_case_stops_later_recovery_cases(recovery_fixture, recovery, monkeypatch, fault):
    root, _, _, _ = recovery_fixture
    transport, _ = install_transport(recovery_fixture, recovery, monkeypatch)
    transport.fault = fault
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] != "passed" and result["runtime_qualification"] == "not_run"
    assert "storage_open" not in transport.calls and "worker_stop" not in transport.calls
    if fault == "gateway_stop_unobserved":
        assert "gateway_start" not in transport.calls


@pytest.mark.parametrize("fault", ["worker_stop_unobserved", "unchanged_boot", "worker_checkpoint_loss",
                                   "configuration_after_stop", "configuration_after_restart"])
def test_worker_case_requires_observed_stop_restart_and_checkpoint_preservation(recovery_fixture, recovery, monkeypatch, fault):
    root, _, _, _ = recovery_fixture
    transport, _ = install_transport(recovery_fixture, recovery, monkeypatch)
    transport.fault = fault
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] != "passed" and result["runtime_qualification"] == "not_run"
    if fault in {"worker_stop_unobserved", "configuration_after_stop"}:
        assert "worker_start" not in transport.calls
    if fault == "unchanged_boot":
        assert result.get("recovery_kind") != "worker_restart"
    assert result.get("recovery_kind") != "resume"


def test_storage_denial_restores_only_recorded_mode_after_verified_denial(recovery_fixture, recovery):
    root, env, _, observed = recovery_fixture
    directory = create_checkpoints(root)
    transport = RecoveryTransport(root, env, Clock(), observed)
    checks = []
    recovery._storage_case(root, transport, transport.clock.now + 60, lambda: checks.append("host"))
    assert stat.S_IMODE((directory / "storage").stat().st_mode) == 0o600
    assert (directory / "storage").read_bytes() == STORAGE
    assert transport.calls == ["storage_open", "storage_open"] and checks


@pytest.mark.parametrize("fault", ["storage_timeout", "storage_allowed", "storage_wrong_denial", "storage_replacement"])
def test_storage_unexpected_outcome_never_silently_repairs_permission(recovery_fixture, recovery, monkeypatch, fault):
    root, env, _, observed = recovery_fixture
    directory = create_checkpoints(root)
    transport = RecoveryTransport(root, env, Clock(), observed)
    transport.fault = fault
    native_fchmod = os.fchmod
    modes = []

    def fchmod(fd, mode):
        modes.append(mode)
        native_fchmod(fd, mode)

    monkeypatch.setattr(recovery.os, "fchmod", fchmod)
    checks = []
    with pytest.raises(support.probe.Refusal):
        recovery._storage_case(root, transport, transport.clock.now + 60, lambda: checks.append("host"))
    assert modes == [0] and checks
    original = directory / ("retained-original-storage" if fault == "storage_replacement" else "storage")
    assert stat.S_IMODE(original.stat().st_mode) == 0
    if fault == "storage_replacement":
        assert (directory / "storage").read_bytes() == b"replacement storage"
        assert stat.S_IMODE((directory / "storage").stat().st_mode) == 0o600


@pytest.mark.parametrize("fault", ["guard_gateway_error", "guard_storage_timeout"])
def test_recovery_host_guard_failure_survives_transport_errors(recovery_fixture, recovery, monkeypatch, fault):
    root, _, _, observed = recovery_fixture
    transport, _ = install_transport(recovery_fixture, recovery, monkeypatch)
    transport.fault = fault
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert observed["flags"] == 0 and "worker_stop" not in transport.calls
    assert result["retained"] is True


def test_recovery_cases_each_have_sixty_seconds_without_resetting_original_window(recovery_fixture, recovery, monkeypatch):
    root, _, _, _ = recovery_fixture
    transport, clock = install_transport(recovery_fixture, recovery, monkeypatch)
    transport.case_delay = 30
    started = clock.now
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "passed"
    assert 60 < clock.now - started <= 180
    assert all(0 < deadline - called <= 60 for _, called, deadline in transport.deadlines)


def test_recovery_cannot_extend_expiring_original_experiment(recovery_fixture, recovery, monkeypatch):
    root, _, _, _ = recovery_fixture
    stamp = time.time() - 855
    os.utime(root / "prepared.json", (stamp, stamp))
    transport, clock = install_transport(recovery_fixture, recovery, monkeypatch)
    transport.case_delay = 30
    started = clock.now
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "unavailable"
    assert 0 < clock.now - started <= 45
    assert "worker_stop" not in transport.calls
    assert max(deadline for _, _, deadline in transport.deadlines) - started <= 45


@pytest.mark.parametrize("failure", ["gateway_host", "checkpoint_identity", "storage_host"])
def test_transport_truncation_survives_later_host_or_identity_failure(
        recovery_fixture, recovery, monkeypatch, failure):
    root, _, _, observed = recovery_fixture
    transport, _ = install_transport(recovery_fixture, recovery, monkeypatch)
    identity_changed = False
    original_identity, original_execute = transport.identity, transport.execute
    original_gateway_start = transport.gateway_start

    def identity(deadline):
        value = original_identity(deadline)
        return (*value[:4], 5678, *value[5:]) if identity_changed else value

    def execute(program, deadline):
        nonlocal identity_changed
        result = original_execute(program, deadline)
        if failure == "checkpoint_identity" and result["operation"] == "checkpoint_create":
            identity_changed = True
            raise support.probe.Refusal("output_limit", output_limit_bytes=1234)
        if failure == "storage_host" and result.get("outcome") == "denied":
            observed["flags"] = 0
            raise support.probe.Refusal("output_limit", output_limit_bytes=1234)
        return result

    def gateway_start(deadline):
        original_gateway_start(deadline)
        if failure == "gateway_host":
            observed["flags"] = 0
            raise support.probe.Refusal("output_limit", output_limit_bytes=1234)

    transport.identity, transport.execute, transport.gateway_start = identity, execute, gateway_start
    result = recovery.recovery_probe(support.probe.Selection(root, support.DIGEST))
    assert result["truncation"] == {"transport_output": True, "limit_bytes": 1234}
    assert result["reason"] == ("sandbox_identity" if failure == "checkpoint_identity" else "protected_state_changed")
    assert result["status"] == ("unavailable" if failure == "checkpoint_identity" else "failed")
    assert result["retained"] is True and "worker_stop" not in transport.calls
    if failure == "storage_host":
        assert stat.S_IMODE((root / "fixture/task/.openshell-recovery/storage").stat().st_mode) == 0
