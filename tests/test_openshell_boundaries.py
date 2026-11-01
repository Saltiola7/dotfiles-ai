"""Protected-boundary decisions with native local Git and simulated guest transport."""
from __future__ import annotations

import ast
import builtins
from contextlib import redirect_stdout
import copy
import errno
import importlib.util
import json
from io import BytesIO, StringIO
import os
from pathlib import Path
import subprocess
import socket
import sys
import time
from types import SimpleNamespace

import pytest

import test_openshell_runtime as support

owned_root = support.owned_root
pointer_fixture = support.pointer_fixture
guarded_pointer_fixture = support.guarded_pointer_fixture


@pytest.fixture(scope="module")
def boundaries():
    sys.modules["probe_openshell_runtime"] = support.probe
    path = Path(__file__).with_name("probe_openshell_boundaries.py")
    assert path.is_file(), "Boundary implementation absent: expected red-first failure"
    spec = importlib.util.spec_from_file_location("openshell_boundaries_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def private(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)


@pytest.fixture
def boundary_fixture(guarded_pointer_fixture):
    root, env, guard, observed = guarded_pointer_fixture
    main = root / "fixture/main"
    common = main / ".git"
    def git(*args):
        return subprocess.run(["/usr/bin/git", "-C", str(main), *args], cwd=root,
                              env=env, check=True, capture_output=True, timeout=10).stdout.decode().strip()
    git("worktree", "add", "--quiet", "--detach", str(root / "fixture/sibling"), "HEAD")
    oid = git("rev-parse", "HEAD")
    (common / "hooks/openshell-qualification").write_text("nonfunctional hook sentinel\n")
    (common / "openshell-qualification").mkdir()
    (common / "openshell-qualification/lifecycle").write_text("nonfunctional lifecycle sentinel\n")
    targets = {"config": "config", "object": "objects/" + oid[:2] + "/" + oid[2:],
               "ref": "refs/heads/main", "hook": "hooks/openshell-qualification",
               "sibling_index": "worktrees/sibling/index", "lifecycle": "openshell-qualification/lifecycle"}
    private(root / "boundaries.json", {"schema_version": 1, "metadata_targets": targets})
    private(root / "runtime-artifact.json", {"schema_version": 1,
            "runtime_binary_sha256": "12" * 32, "workload_image_id": "sha256:" + "34" * 32})
    specimens = root / "input/alias-specimens"
    for kind in ("symlink", "hardlink"):
        (specimens / kind).mkdir(parents=True)
    source = specimens / "target"
    source.write_text("nonfunctional alias sentinel\n")
    (specimens / "symlink/alias").symlink_to(source)
    os.link(source, specimens / "hardlink/alias")
    return root, env, guard, observed, targets


class Transport:
    def __init__(self, fixture):
        self.root, self.env, _, _, _ = fixture
        self.guest_home, self.guest_uid = "/home/fixture", 1000
        self.sandbox_name = self.root.name.removeprefix("openshell-")
        self.calls, self.identities = [], 0
        self.generation = tuple(support.GENERATION_IDENTITY.values())
        self.action = None

    def identity(self, deadline):
        assert 0 < deadline - time.monotonic() <= 60
        self.identities += 1
        return self.generation

    def guest(self, argv, deadline):
        assert argv[0] == "/usr/bin/openshell" and argv[1:3] == ["sandbox", "exec"]
        assert argv[argv.index("--") + 1] == "/usr/local/bin/python3.13"
        data = {}
        for node in ast.parse(argv[argv.index("-c") + 1]).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                try:
                    data[node.targets[0].id] = ast.literal_eval(node.value)
                except (TypeError, ValueError):
                    pass
        operation = data["operation"]
        self.calls.append(operation)
        result = {"schema_version": 1, "operation": operation, "outcome": "denied", "errno": 13}
        if operation == "startup_execution":
            result = {"schema_version": 1, "operation": operation, "outcome": "executed",
                      "uid": 1000, "gid": 1000, "capabilities_zero": True, "no_new_privileges": True,
                      "binary": "/usr/local/bin/python3.13"}
        elif operation.startswith("policy_"):
            result = {"schema_version": 1, "operation": operation, "outcome": "disabled",
                      "status": 404, "error": "feature_disabled"}
        if self.action:
            result = self.action(operation, result)
        return support.probe.CommandResult(0, json.dumps(result).encode(), b"")


def native_observation(uid=1000, gid=1000):
    pins = json.loads((Path(__file__).parent / "fixtures/openshell_runtime/versions.json").read_text())["images"]
    return {"runtime_binary_sha256": "12" * 32, "workload_image_id": "sha256:" + "34" * 32,
            "gateway": {"address": "127.0.0.1", "port": 17670, "pid": 88, "start_ticks": 99, "inode": 11},
            "control": {"path": "/.openshell/channel/control/control.sock", "device": 1, "inode": 12},
            "podman": {"path": f"/run/user/{uid}/podman/podman.sock", "device": 1, "inode": 13},
            "state": [{"name": "bootstrap", "path": "/.openshell/channel/sandbox/bootstrap.json", "present": True,
                       "device": 1, "inode": 14},
                      {"name": "supervisor_auth", "path": "/.openshell/supervisor/auth.json", "present": False}],
            "namespace": "user:[123]", "uid_map": [[0, 100000, 1000], [1000, uid, 1]],
            "gid_map": [[0, 100000, 1000], [1000, gid, 1]], "runtime_start_ticks": 55,
            "resources": {"cgroup": "/sys/fs/cgroup/fixture", "cpu_quota": 200000, "cpu_period": 100000,
                          "memory_max": 2147483648, "pids_max": 256},
            "rootless": True, "privileged": False, "no_new_privileges": True, "uid": [uid] * 4,
            "guest_gid": gid, "gid": [gid] * 4,
            "capabilities": {name: 0 for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")},
            "images": {name: {"id": pins[name]["config_digest"], "digest": pins[name]["manifest_digest"],
                              "architecture": "arm64", "os": "linux"} for name in ("sandbox_runtime", "supervisor")}}


def install(monkeypatch, boundaries, fixture):
    transport = Transport(fixture)
    monkeypatch.setattr(boundaries.runtime, "_PointerController", lambda *args: transport)
    monkeypatch.setattr(boundaries, "_native_observation", lambda *args: copy.deepcopy(native_observation()))
    return transport


def test_complete_checks_remain_partial_qualification(boundary_fixture, boundaries, monkeypatch):
    transport = install(monkeypatch, boundaries, boundary_fixture)
    report = boundaries.protected_boundaries_probe(support.probe.Selection(boundary_fixture[0], support.DIGEST))
    assert report["status"] == "passed" and report["retained"] is True
    assert report["runtime_qualification"] == "not_run"
    assert report["startup_attestation"]["kind"] == "source_backed_inference"
    assert report["startup_attestation"]["unexported_audit_fields"] == "unobserved"
    assert report["native_observation"] == native_observation()
    assert set("metadata_" + key for key in boundary_fixture[4]) <= set(transport.calls)
    assert {"parent_rename", "parent_replace", "gateway", "podman", "control", "policy_current", "policy_proposals"} <= set(transport.calls)
    assert "capability-probe" not in repr(transport.calls)


@pytest.mark.parametrize("change", [{"schema_version": True}, {"extra": 1}, {"metadata_targets": {}}])
def test_receipt_refused_before_native_calls(boundary_fixture, boundaries, monkeypatch, change):
    root = boundary_fixture[0]
    private(root / "boundaries.json", json.loads((root / "boundaries.json").read_text()) | change)
    monkeypatch.setattr(boundaries.runtime, "_PointerController", lambda *args: pytest.fail("native effect"))
    assert boundaries.protected_boundaries_probe(support.probe.Selection(root, support.DIGEST))["status"] == "unavailable"


@pytest.mark.parametrize("target,value", [("config", "../config"), ("object", "config"),
                                         ("ref", "refs/heads/absent"), ("sibling_index", "worktrees/task/index")])
def test_native_target_role_is_required(boundary_fixture, boundaries, monkeypatch, target, value):
    root = boundary_fixture[0]
    receipt = json.loads((root / "boundaries.json").read_text())
    receipt["metadata_targets"][target] = value
    private(root / "boundaries.json", receipt)
    transport = install(monkeypatch, boundaries, boundary_fixture)
    assert boundaries.protected_boundaries_probe(support.probe.Selection(root, support.DIGEST))["status"] == "unavailable"
    assert transport.calls == []


@pytest.mark.parametrize("operation", ["metadata_config", "metadata_object", "parent_rename", "gateway", "control", "state_bootstrap"])
def test_successful_access_fails_and_stops(boundary_fixture, boundaries, monkeypatch, operation):
    transport = install(monkeypatch, boundaries, boundary_fixture)
    transport.action = lambda name, value: value | {"outcome": "accessible", "errno": 0} if name == operation else value
    result = boundaries.protected_boundaries_probe(support.probe.Selection(boundary_fixture[0], support.DIGEST))
    assert result["status"] == "failed" and transport.calls[-1] == operation


@pytest.mark.parametrize("error", [22, 20, 21, 2, 110])
def test_invalid_parent_operation_does_not_prove_denial(boundary_fixture, boundaries, monkeypatch, error):
    transport = install(monkeypatch, boundaries, boundary_fixture)
    transport.action = lambda name, value: value | {"errno": error} if name == "parent_rename" else value
    result = boundaries.protected_boundaries_probe(support.probe.Selection(boundary_fixture[0], support.DIGEST))
    assert result["status"] == "unavailable" and transport.calls[-1] == "parent_rename"


def test_host_change_overrides_guest_denial_and_transport_error(boundary_fixture, boundaries, monkeypatch):
    root, _, _, observed, _ = boundary_fixture
    transport = install(monkeypatch, boundaries, boundary_fixture)
    def mutate(operation, result):
        if operation == "metadata_config":
            observed["flags"] = 0
            raise support.probe.Refusal("output_limit", output_limit_bytes=1234)
        return result
    transport.action = mutate
    result = boundaries.protected_boundaries_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert result["truncation"] == {"transport_output": True, "limit_bytes": 1234}
    assert transport.identities >= 2


@pytest.mark.parametrize("value", [{"status": 404, "error": "not_found"}, {"status": 403, "error": "feature_disabled"}])
def test_policy_disabled_requires_exact_response(boundary_fixture, boundaries, monkeypatch, value):
    transport = install(monkeypatch, boundaries, boundary_fixture)
    transport.action = lambda name, result: result | value if name == "policy_current" else result
    result = boundaries.protected_boundaries_probe(support.probe.Selection(boundary_fixture[0], support.DIGEST))
    assert result["status"] != "passed" and transport.calls[-1] == "policy_current"


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_missing_alias_specimen_cannot_count_as_refusal(boundary_fixture, boundaries, monkeypatch, kind):
    root = boundary_fixture[0]
    (root / "input/alias-specimens" / kind / "alias").unlink()
    transport = install(monkeypatch, boundaries, boundary_fixture)
    result = boundaries.protected_boundaries_probe(support.probe.Selection(root, support.DIGEST))
    assert result["status"] == "unavailable" and not transport.calls


def test_changed_native_surface_stops_before_next_operation(boundary_fixture, boundaries, monkeypatch):
    transport = install(monkeypatch, boundaries, boundary_fixture)
    def observe(*args):
        value = native_observation()
        if transport.calls:
            value["control"]["inode"] += 1
        return value
    monkeypatch.setattr(boundaries, "_native_observation", observe)
    result = boundaries.protected_boundaries_probe(support.probe.Selection(boundary_fixture[0], support.DIGEST))
    assert result["status"] != "passed" and len(transport.calls) == 1


@pytest.mark.parametrize("field,value", [
    ("runtime_binary_sha256", "00" * 32), ("workload_image_id", "sha256:" + "00" * 32),
    ("namespace", ""), ("runtime_start_ticks", True), ("uid_map", [[0, 0, 65536]]),
    ("gid_map", [[0, 100000, 65536]]), ("gateway", {"address": "127.0.0.1", "port": 17670}),
    ("control", {"path": "/invented.sock", "device": 1, "inode": 1}),
    ("podman", {"path": "/run/user/0/podman/podman.sock", "device": 1, "inode": 1}),
    ("state", []), ("resources", {"cpu_quota": -1}),
    ("rootless", False), ("privileged", True), ("no_new_privileges", False),
    ("uid", [0] * 4), ("capabilities", {}), ("images", {}),
    ("guest_gid", 0), ("guest_gid", True), ("gid", [503] * 4),
])
def test_native_observation_requires_exact_positive_identity(boundaries, field, value):
    receipt = {"runtime_binary_sha256": "12" * 32, "workload_image_id": "sha256:" + "34" * 32}
    observation = native_observation()
    observation[field] = value
    with pytest.raises(support.probe.Refusal, match="native_boundary_unavailable"):
        boundaries._validate_native_observation(observation, receipt, 1000)


def test_native_resource_limits_and_control_socket_identity_are_retained(boundaries):
    receipt = {"runtime_binary_sha256": "12" * 32, "workload_image_id": "sha256:" + "34" * 32}
    observed = native_observation()
    assert boundaries._validate_native_observation(observed, receipt, 1000) == observed
    observed["resources"]["pids_max"] = 257
    with pytest.raises(support.probe.Refusal):
        boundaries._validate_native_observation(observed, receipt, 1000)


@pytest.mark.parametrize("change", [{"schema_version": True}, {"runtime_binary_sha256": "aa"},
                                    {"workload_image_id": "mutable:tag"}, {"extra": 1}])
def test_artifact_receipt_refused_before_native_calls(boundary_fixture, boundaries, monkeypatch, change):
    root = boundary_fixture[0]
    path = root / "runtime-artifact.json"
    private(path, json.loads(path.read_text()) | change)
    monkeypatch.setattr(boundaries.runtime, "_PointerController", lambda *args: pytest.fail("native effect"))
    assert boundaries.protected_boundaries_probe(support.probe.Selection(root, support.DIGEST))["status"] == "unavailable"


def test_expired_budget_refuses_before_native_calls(boundary_fixture, boundaries, monkeypatch):
    root = boundary_fixture[0]
    os.utime(root / "prepared.json", (time.time() - 901, time.time() - 901))
    monkeypatch.setattr(boundaries.runtime, "_PointerController", lambda *args: pytest.fail("native effect"))
    assert boundaries.protected_boundaries_probe(support.probe.Selection(root, support.DIGEST))["status"] == "unavailable"


def run_workload_program(boundaries, operation, fake_os, target="/native/common/config"):
    original = builtins.__import__
    def imports(name, *args, **kwargs):
        return fake_os if name == "os" else original(name, *args, **kwargs)
    output = StringIO()
    with redirect_stdout(output):
        exec(boundaries._program(operation, target), {"__builtins__": dict(vars(builtins), __import__=imports)})
    return json.loads(output.getvalue())


@pytest.mark.parametrize("operation,flags", [("metadata_config", os.O_WRONLY), ("state_bootstrap", os.O_RDONLY)])
def test_generated_file_attempt_uses_actual_open_without_read_or_write(boundaries, operation, flags):
    calls = []
    def denied(path, actual_flags):
        calls.append((path, actual_flags))
        raise PermissionError(errno.EACCES, "synthetic")
    fake = SimpleNamespace(O_RDONLY=os.O_RDONLY, O_WRONLY=os.O_WRONLY, O_NOFOLLOW=os.O_NOFOLLOW,
                           O_NONBLOCK=os.O_NONBLOCK, open=denied)
    result = run_workload_program(boundaries, operation, fake)
    assert result["outcome"] == "denied" and result["errno"] == errno.EACCES
    assert calls == [("/native/common/config", flags | os.O_NOFOLLOW | os.O_NONBLOCK)]


def test_generated_writable_open_success_fails_without_modifying_bytes(boundaries):
    calls = []
    fake = SimpleNamespace(O_RDONLY=os.O_RDONLY, O_WRONLY=os.O_WRONLY, O_NOFOLLOW=os.O_NOFOLLOW,
                           O_NONBLOCK=os.O_NONBLOCK, open=lambda *args: 42, close=lambda fd: calls.append(fd))
    result = run_workload_program(boundaries, "metadata_config", fake)
    assert calls == [42]
    with pytest.raises(support.probe.Refusal, match="boundary_accessible"):
        boundaries._validate_result(result, "metadata_config")


@pytest.mark.parametrize("operation", ["parent_rename", "parent_replace"])
def test_generated_parent_attempt_reaches_valid_target_and_distinguishes_setup(boundaries, operation):
    calls = []
    def reject(*args):
        calls.append(args)
        raise OSError(errno.EBUSY, "synthetic mount boundary")
    fake = SimpleNamespace(path=SimpleNamespace(isdir=lambda path: True, lexists=lambda path: False),
                           mkdir=lambda *args: None, rename=reject, replace=reject)
    result = run_workload_program(boundaries, operation, fake)
    assert result["outcome"] == "denied" and result["errno"] == errno.EBUSY and len(calls) == 1
    boundaries._validate_result(result, operation)
    if operation == "parent_replace":
        fake.mkdir = reject
        result = run_workload_program(boundaries, operation, fake)
        assert result["outcome"] == "unavailable"


def test_parent_symlink_substitution_cannot_preserve_apparent_directory_identity(boundary_fixture, boundaries, monkeypatch):
    root = boundary_fixture[0]
    transport = install(monkeypatch, boundaries, boundary_fixture)
    def substitute(operation, result):
        if operation == "metadata_config":
            task = root / "fixture/task"
            moved = root / "fixture/substituted-task"
            task.rename(moved)
            task.symlink_to(moved, target_is_directory=True)
        return result
    transport.action = substitute
    report = boundaries.protected_boundaries_probe(support.probe.Selection(root, support.DIGEST))
    assert report["status"] == "failed" and report["reason"] == "protected_state_changed"
    assert transport.calls[-1] == "metadata_config"


def run_native_observer(boundaries, violation=None, uid=1000, gid=1000):
    """Execute the native observer itself with fixed process/Podman interfaces."""
    baseline = native_observation(uid, gid)
    pins = json.loads((Path(__file__).parent / "fixtures/openshell_runtime/versions.json").read_text())["images"]
    cid, supervisor_id = "cd" * 32, "ef" * 32
    sandbox_id = support.GENERATION_IDENTITY["sandbox_id"]
    calls = []
    workload = {"Id": cid, "Config": {"Labels": {"openshell.managed": "true", "openshell.ai/sandbox-id": sandbox_id}},
                "State": {"Running": True, "Paused": False, "Pid": 1234}, "HostConfig": {"Privileged": False},
                "Mounts": [{"Destination": "/.openshell/channel/control", "Source": "/native/control"}],
                "Image": baseline["workload_image_id"]}
    supervisor = {"Id": supervisor_id, "HostConfig": {"Privileged": False}, "State": {"Running": True, "Pid": 2345},
                  "Image": pins["supervisor"]["config_digest"]}
    info = {"host": {"security": {"rootless": violation != "rootful"}, "cgroupVersion": "v2"}}
    cap = "1" if violation == "capability" else "0"
    files = {"/proc/1234/status": ("Uid:\t" + " ".join([str(uid)] * 4) + "\nGid:\t" +
                                  " ".join([str(gid)] * 4) + "\nNoNewPrivs:\t1\n" +
                                  "".join(key + ":\t" + cap + "\n" for key in baseline["capabilities"])).encode(),
             "/proc/1234/uid_map": f"0 100000 1000\n1000 {uid} 1\n".encode(),
             "/proc/1234/gid_map": f"0 100000 1000\n1000 {gid} 1\n".encode(),
             "/proc/1234/cgroup": b"0::/fixture\n", "/sys/fs/cgroup/fixture/cpu.max": b"200000 100000\n",
             "/sys/fs/cgroup/fixture/memory.max": b"2147483648\n", "/sys/fs/cgroup/fixture/pids.max": b"256\n",
             "/proc/88/stat": ("88 (gateway) " + " ".join(["0"] * 19 + ["99"])).encode(),
             "/proc/88/net/tcp": ("header\n0: 0100007F:" + format(17670, "04X") + " 00000000:0000 0A 0 0 0 0 0 11\n").encode(),
             "/home/fixture/.config/openshell/gateway.toml": b'[openshell.gateway]\nbind_address="127.0.0.1:17670"\n'}
    if violation == "host_root_mapping":
        files["/proc/1234/uid_map"] = b"0 0 65536\n"
    if violation == "wrong_group_mapping":
        files["/proc/1234/gid_map"] = f"0 100000 1000\n1000 {uid} 1\n".encode()
    if violation == "wrong_group_status":
        files["/proc/1234/status"] = files["/proc/1234/status"].replace(
            ("Gid:\t" + " ".join([str(gid)] * 4)).encode(), b"Gid:\t0 0 0 0")
    def command(args, **kwargs):
        calls.append(args)
        if args[1:2] == ["info"]:
            value = info
        elif args[1:2] == ["ps"]:
            return SimpleNamespace(returncode=0, stdout=(supervisor_id if any("=supervisor" in x for x in args) else cid).encode(), stderr=b"")
        elif args[1:2] == ["inspect"]:
            value = [workload if args[-1] == cid else supervisor]
        elif args[1:3] == ["image", "inspect"]:
            name = "supervisor" if "supervisor@" in args[-1] else "sandbox_runtime"
            pin = pins[name]
            value = [{"Id": pin["config_digest"], "Digest": pin["manifest_digest"], "Architecture": "arm64", "Os": "linux"}]
            if violation == "mutable_image":
                value[0]["Id"] = "00" * 32
        elif args[0] == "/usr/bin/systemctl":
            return SimpleNamespace(returncode=0, stdout=b"88\n", stderr=b"")
        elif args[1:2] == ["unshare"]:
            value = {key: baseline[key] for key in ("runtime_binary_sha256", "namespace", "runtime_start_ticks", "control", "podman", "state")}
        else:
            raise AssertionError(args)
        return SimpleNamespace(returncode=0, stdout=json.dumps(value).encode(), stderr=b"")
    class NativePath:
        def __init__(self, value): self.value = str(value)
        def __str__(self): return self.value
        def __truediv__(self, name): return NativePath(self.value + "/" + name)
        def resolve(self, strict=False): return self
        def is_relative_to(self, parent): return self.value.startswith(parent + "/")
        def iterdir(self): return [NativePath(self.value + "/7")]
    def link(path):
        if str(path) == "/proc/self/ns/user": return "user:[999]"
        return "socket:[999]" if violation == "unowned_gateway" else "socket:[11]"
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    fake_modules = {
        "sys": SimpleNamespace(argv=["probe", cid, sandbox_id, "1234", "/home/fixture", str(uid), json.dumps(pins), boundaries._UNSHARE_OBSERVER]),
        "os": SimpleNamespace(readlink=link, stat=lambda path: SimpleNamespace(st_uid=uid), getgid=lambda: gid),
        "pathlib": SimpleNamespace(Path=NativePath),
        "socket": SimpleNamespace(inet_ntoa=socket.inet_ntoa, create_connection=lambda *args, **kwargs: Connection()),
        "subprocess": SimpleNamespace(run=command, DEVNULL=subprocess.DEVNULL, SubprocessError=subprocess.SubprocessError),
    }
    original_import = builtins.__import__
    def imports(name, *args, **kwargs): return fake_modules.get(name) or original_import(name, *args, **kwargs)
    def read(path, mode): return BytesIO(files[str(path)])
    output = StringIO()
    with redirect_stdout(output):
        exec(boundaries._NATIVE_OBSERVER, {"__builtins__": dict(vars(builtins), __import__=imports, open=read)})
    return json.loads(output.getvalue()), calls


def test_actual_native_observer_binds_process_socket_and_image_observations(boundaries):
    value, calls = run_native_observer(boundaries)
    receipt = {"runtime_binary_sha256": "12" * 32, "workload_image_id": "sha256:" + "34" * 32}
    assert boundaries._validate_native_observation(value, receipt, 1000) == native_observation()
    assert len([argv for argv in calls if argv[1:2] == ["unshare"]]) == 1
    assert not any("capability-probe" in argv for argv in calls)


@pytest.mark.parametrize("violation", ["rootful", "capability", "host_root_mapping", "mutable_image", "unowned_gateway"])
def test_actual_native_observer_refuses_unqualified_positive_controls(boundaries, violation):
    value, calls = run_native_observer(boundaries, violation)
    assert value == {"error": "native_boundary_unavailable"}
    assert not any(argv[1:2] == ["unshare"] for argv in calls)


def test_native_observer_independent_user_and_group_ids(boundaries):
    value, _ = run_native_observer(boundaries, uid=503, gid=1000)
    assert value == native_observation(uid=503, gid=1000)


def test_native_validator_independent_user_and_group_ids(boundaries):
    receipt = {"runtime_binary_sha256": "12" * 32, "workload_image_id": "sha256:" + "34" * 32}
    value = native_observation(uid=503, gid=1000)
    assert boundaries._validate_native_observation(value, receipt, 503) == value


@pytest.mark.parametrize("violation", ["wrong_group_mapping", "wrong_group_status"])
def test_independent_group_identity_must_match_native_owner(boundaries, violation):
    value, _ = run_native_observer(boundaries, violation, uid=503, gid=1000)
    assert value == {"error": "native_boundary_unavailable"}


@pytest.mark.parametrize("operation", ["gateway", "podman", "control"])
@pytest.mark.parametrize("linux_errno", [111, 101])
def test_linux_connection_denial_numbers_are_host_independent(boundaries, operation, linux_errno):
    boundaries._validate_result({"schema_version": 1, "operation": operation, "outcome": "denied",
                                 "errno": linux_errno}, operation)


@pytest.mark.parametrize("macos_errno", [61, 51])
def test_macos_connection_numbers_do_not_qualify_linux_denials(boundaries, macos_errno):
    with pytest.raises(support.probe.Refusal, match="boundary_denial_unavailable"):
        boundaries._validate_result({"schema_version": 1, "operation": "gateway", "outcome": "denied",
                                     "errno": macos_errno}, "gateway")
