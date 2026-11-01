"""Fixed retained recovery observations; never installed or run implicitly."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

import probe_openshell_runtime as runtime

TEXT = b"openshell recovery checkpoint\n"
BINARY = bytes(range(256))
STORAGE = b"openshell storage object\n"
UNACKNOWLEDGED = b"openshell unacknowledged marker\n"


def _validate_worker_config(root: Path) -> tuple:
    receipt = runtime.decode_object(runtime.private_file(root / "worker-config.json"))
    if (set(receipt) != {"schema_version", "sha256"}
            or type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1
            or not isinstance(receipt["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]) is None):
        raise runtime.Refusal("worker_configuration")
    runtime.private_directory(root / "lima/q")
    observed = runtime._regular_identity(root / "lima/q/lima.yaml", 1024 * 1024)
    if observed[-1] != receipt["sha256"] or stat.S_IMODE(observed[2]) & 0o022:
        raise runtime.Refusal("worker_configuration")
    return observed


def _require_prerequisites(root: Path, digest: str) -> None:
    required = {"immutable_git_pointer", "containment", "boundaries", "network", "pause_resume"}
    found = set()
    runtime._check_pointer_evidence(root, 256 * 1024, 16)
    for path in (root / "evidence").iterdir():
        if re.fullmatch(r"pointer-[0-9a-f]{32}\.json", path.name) is None:
            continue
        value = runtime.decode_object(runtime.private_file(path))
        if value.get("generation_sha256") != digest:
            continue
        if (type(value.get("schema_version")) is not int or value["schema_version"] != 1
                or value.get("runtime_qualification") != "not_run"):
            raise runtime.Refusal("invalid_prerequisite")
        if value.get("status") == "failed" or (value.get("status") == "unavailable" and value.get("reason") is not None):
            raise runtime.Refusal("failed_prerequisite")
        if value.get("probe") in required and value.get("status") == "passed" and value.get("retained") is True:
            found.add(value["probe"])
    if found != required:
        raise runtime.Refusal("missing_prerequisite")


def _validate_gateway_state(value: dict, active: bool) -> dict:
    if (not isinstance(value, dict) or set(value) != {"unit", "active", "pid", "start_ticks", "configuration_sha256"}
            or value["unit"] != "openshell-gateway.service" or value["active"] is not active
            or any(type(value[key]) is not int for key in ("pid", "start_ticks"))
            or (active and (value["pid"] <= 0 or value["start_ticks"] <= 0))
            or (not active and (value["pid"] != 0 or value["start_ticks"] != 0))
            or not isinstance(value["configuration_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", value["configuration_sha256"]) is None):
        raise runtime.Refusal("gateway_identity")
    return value


def _validate_worker_state(value: dict, expected_container_id: str) -> dict:
    if (not isinstance(value, dict) or set(value) != {"boot_id", "container_id", "pid", "start_ticks", "running"}
            or value["container_id"] != expected_container_id or type(value["running"]) is not bool
            or any(type(value[key]) is not int for key in ("pid", "start_ticks"))
            or (value["running"] and (value["pid"] <= 0 or value["start_ticks"] <= 0))
            or (not value["running"] and (value["pid"] != 0 or value["start_ticks"] != 0))):
        raise runtime.Refusal("worker_identity")
    try:
        if str(uuid.UUID(value["boot_id"])) != value["boot_id"]:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise runtime.Refusal("worker_identity") from None
    return value


def _checkpoint_snapshot(root: Path) -> dict:
    directory = root / "fixture/task/.openshell-recovery"
    runtime.private_directory(directory)
    result = {}
    for name, content in (("text", TEXT), ("binary", BINARY)):
        identity = runtime._regular_identity(directory / name, 4096)
        if (stat.S_IMODE(identity[2]) != 0o600 or identity[3] != len(content)
                or identity[-1] != hashlib.sha256(content).hexdigest()):
            raise runtime.Refusal("checkpoint_changed")
        result[name] = identity
    return result


def _verify_checkpoints(root: Path, baseline: dict) -> dict:
    if _checkpoint_snapshot(root) != baseline:
        raise runtime.Refusal("checkpoint_changed")
    try:
        marker = runtime.private_file(root / "fixture/task/.openshell-recovery/unacknowledged", 4096)
    except FileNotFoundError:
        state = "absent"
    else:
        state = "present" if marker == UNACKNOWLEDGED else "changed"
    return {"acknowledged": "preserved", "unacknowledged": state}


def _recovery_program(operation: str) -> str:
    if operation not in {"checkpoint_create", "unacknowledged_create", "storage_open"}:
        raise runtime.Refusal("invalid_recovery_operation")
    return """import hashlib,json,os
operation,spelling=%r
base='/work/.openshell-recovery'
if operation=='checkpoint_create':
    os.mkdir(base,0o700)
    for name,data in (('text',%r),('binary',bytes(range(256))),('storage',%r)):
        fd=os.open(base+'/'+name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            if os.write(fd,data)!=len(data):raise RuntimeError()
            os.fsync(fd)
        finally:os.close(fd)
    fd=os.open(base,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
    result={'schema_version':1,'operation':operation,'outcome':'succeeded'}
elif operation=='unacknowledged_create':
    fd=os.open(base+'/unacknowledged',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        data=%r
        if os.write(fd,data)!=len(data):raise RuntimeError()
    finally:os.close(fd)
    result={'schema_version':1,'operation':operation,'outcome':'succeeded'}
else:
    try:fd=os.open(base+'/storage',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except OSError as error:
        result={'schema_version':1,'operation':operation,'outcome':'denied','errno':error.errno,'sha256':None}
    else:
        try:data=os.read(fd,4097)
        finally:os.close(fd)
        result={'schema_version':1,'operation':operation,'outcome':'read','errno':0,'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps(result,sort_keys=True))
""" % ((operation, "storage" if operation == "storage_open" else ""), TEXT, STORAGE, UNACKNOWLEDGED)


def _storage_result(value: dict, denied: bool) -> None:
    if (not isinstance(value, dict) or set(value) != {"schema_version", "operation", "outcome", "errno", "sha256"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["operation"] != "storage_open" or type(value["errno"]) is not int):
        raise runtime.Refusal("invalid_recovery_output")
    if denied:
        if value["outcome"] != "denied" or value["errno"] not in {1, 13} or value["sha256"] is not None:
            raise runtime.Refusal("storage_denial_unobserved")
    elif value["outcome"] != "read" or value["errno"] != 0 or value["sha256"] != hashlib.sha256(STORAGE).hexdigest():
        raise runtime.Refusal("storage_recovery_unobserved")


def _storage_case(root: Path, controller, deadline: float, check_host) -> None:
    path = root / "fixture/task/.openshell-recovery/storage"
    before = runtime._regular_identity(path, 4096)
    if stat.S_IMODE(before[2]) != 0o600 or before[-1] != hashlib.sha256(STORAGE).hexdigest():
        raise runtime.Refusal("storage_identity")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        def same_object(mode):
            held, named = os.fstat(fd), path.lstat()
            for info in (held, named):
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                        or (info.st_dev, info.st_ino) != before[:2] or stat.S_IMODE(info.st_mode) != mode
                        or info.st_size != before[3] or info.st_mtime_ns != before[4]):
                    raise runtime.Refusal("storage_identity")
        same_object(0o600)
        check_host()
        runtime._remaining(deadline)
        os.fchmod(fd, 0)
        try:
            _storage_result(controller.execute(_recovery_program("storage_open"), deadline), True)
        finally:
            check_host()
        same_object(0)
        runtime._remaining(deadline)
        os.fchmod(fd, stat.S_IMODE(before[2]))
        same_object(0o600)
        try:
            _storage_result(controller.execute(_recovery_program("storage_open"), deadline), False)
        finally:
            check_host()
        if runtime._regular_identity(path, 4096) != before:
            raise runtime.Refusal("storage_identity")
    finally:
        os.close(fd)


class _RecoveryController(runtime._PointerController):
    def __init__(self, selection: runtime.Selection, deadline: float):
        super().__init__(selection, min(deadline, time.monotonic() + 60))
        self.deadline = deadline

    def gateway_state(self, deadline: float) -> dict:
        program = """import hashlib,json,os,pathlib,stat,subprocess
unit='openshell-gateway.service'
keys=('Id','LoadState','ActiveState','SubState','MainPID','FragmentPath','DropInPaths')
p=subprocess.run(['/usr/bin/systemctl','--user','show',unit,*['--property='+key for key in keys]],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
assert len(p.stdout)<=16384
v=dict(line.split('=',1) for line in p.stdout.decode().splitlines())
assert set(v)==set(keys) and v['Id']==unit and v['LoadState']=='loaded'
assert (v['ActiveState'],v['SubState']) in {('active','running'),('inactive','dead')}
active=v['ActiveState']=='active';pid=int(v['MainPID']);ticks=0
if active:
    assert pid>0 and os.stat('/proc/'+str(pid)).st_uid==os.getuid()
    raw=pathlib.Path('/proc/'+str(pid)+'/stat').read_text();ticks=int(raw[raw.rfind(')')+2:].split()[19])
else:assert pid==0
files=[v['FragmentPath'],*v['DropInPaths'].split(),os.environ['HOME']+'/.config/openshell/gateway.toml',os.environ['HOME']+'/.config/openshell/gateway.env']
assert len(files)<=19 and len(set(files))==len(files)
digest=hashlib.sha256()
for name in files:
    assert name.startswith('/') and '\\x00' not in name
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_uid in {0,os.getuid()} and before.st_nlink==1 and not before.st_mode&0o022 and before.st_size<=1048576
        data=os.read(fd,1048577);after=os.fstat(fd)
        assert len(data)==before.st_size and (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
    finally:os.close(fd)
    digest.update(name.encode()+b'\\0'+hashlib.sha256(data).digest())
print(json.dumps({'unit':unit,'active':active,'pid':pid,'start_ticks':ticks,'configuration_sha256':digest.hexdigest()}))
"""
        return runtime.decode_object(self.guest(["/usr/bin/python3", "-I", "-B", "-c", program], deadline).stdout)

    def gateway_stop(self, deadline: float) -> None:
        self.guest(["/usr/bin/systemctl", "--user", "stop", "openshell-gateway.service"], deadline)

    def gateway_start(self, deadline: float) -> None:
        self.guest(["/usr/bin/systemctl", "--user", "start", "openshell-gateway.service"], deadline)
        while True:
            try:
                runtime.decode_object(self.guest(["/usr/bin/openshell", "status", "-o", "json"], deadline).stdout)
                return
            except runtime.Refusal as error:
                if str(error) != "native_command_failed":
                    raise
            time.sleep(min(0.2, runtime._remaining(deadline)))

    def worker_state(self, deadline: float) -> dict:
        program = """import json,pathlib,subprocess
cid,sid=%r,%r
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
p=subprocess.run(['/usr/bin/podman','inspect','--type','container',cid],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
assert len(p.stdout)<=1048576
rows=json.loads(p.stdout);assert isinstance(rows,list) and len(rows)==1
v=rows[0];s=v['State'];labels=v['Config']['Labels']
assert v['Id']==cid and labels.get('openshell.ai/sandbox-id')==sid and labels.get('openshell.managed')=='true' and labels.get('openshell.ai/isolation-role')=='sandbox'
assert type(s['Running']) is bool and s.get('Paused') is False
running=s['Running'];pid=s['Pid'];assert type(pid) is int
a=0
if running:
    assert pid>0
    raw=pathlib.Path('/proc/'+str(pid)+'/stat').read_text();a=int(raw[raw.rfind(')')+2:].split()[19])
else:assert pid==0
print(json.dumps({'boot_id':boot,'container_id':cid,'pid':pid,'start_ticks':a,'running':running}))
""" % (self.prepared["container_id"], self.prepared["sandbox_id"])
        return runtime.decode_object(self.guest(["/usr/bin/python3", "-I", "-B", "-c", program], deadline).stdout)

    def _host_command(self, args: list[str], deadline: float) -> runtime.CommandResult:
        runtime.validate_root(runtime.Selection(self.root, self.binary_identity[-1]))
        _validate_worker_config(self.root)
        if runtime._regular_identity(self.binary, 256 * 1024 * 1024) != self.binary_identity:
            raise runtime.Refusal("lima_identity")
        result = runtime.run_command([str(self.binary), *args], cwd=self.root, env=self.env,
                                     timeout=runtime._remaining(min(deadline, self.deadline)), limit=1024 * 1024)
        if result.returncode:
            raise runtime.Refusal("native_command_failed")
        return result

    def _worker_status(self, deadline: float) -> str:
        form = '{"name":{{json .Name}},"status":{{json .Status}},"dir":{{json .Dir}}}'
        value = runtime.decode_object(self._host_command(["list", "--format", form, "q"], deadline).stdout)
        if (set(value) != {"name", "status", "dir"} or value["name"] != "q"
                or value["dir"] != str(self.root / "lima/q") or value["status"] not in {"Running", "Stopped"}):
            raise runtime.Refusal("worker_identity")
        return value["status"]

    def worker_stop(self, deadline: float) -> None:
        if self._worker_status(deadline) != "Running":
            raise runtime.Refusal("worker_identity")
        self._host_command(["stop", "q"], deadline)

    def worker_stopped(self, deadline: float) -> bool:
        return self._worker_status(deadline) == "Stopped"

    def worker_start(self, deadline: float) -> None:
        if self._worker_status(deadline) != "Stopped":
            raise runtime.Refusal("worker_identity")
        self._host_command(["start", "--tty=false", "--timeout", "45s", "q"], deadline)
        if self._worker_status(deadline) != "Running":
            raise runtime.Refusal("worker_identity")


def recovery_probe(selection: runtime.Selection) -> dict:
    report = {"schema_version": 1, "probe": "recovery", "status": "unavailable", "reason": None,
              "checks": [], "runtime_qualification": "not_run", "generation_sha256": None,
              "truncation": {"transport_output": False, "limit_bytes": None}, "retained": False,
              "worker_state": "unknown", "recovery_kind": None, "acknowledged_state": "unknown",
              "unacknowledged_state": "unknown", "physical_storage_loss": "not_run",
              "abrupt_host_power_loss": "not_run"}
    admitted, final_host = False, None
    try:
        root = selection.root
        runtime.validate_root(selection)
        experiment_deadline = runtime._prepared_deadline(root)
        expected, report["generation_sha256"] = runtime._validate_generation(root)
        guard = runtime._validate_guard(root)
        _validate_worker_config(root)
        _require_prerequisites(root, report["generation_sha256"])
        if os.path.lexists(root / "fixture/task/.openshell-recovery"):
            raise runtime.Refusal("probe_collision")
        admitted = True
        controller = _RecoveryController(selection, experiment_deadline)
        deadline = min(experiment_deadline, time.monotonic() + 60)
        common, pointer = runtime._host_git_fixture(root, controller.env, deadline)
        protected = runtime._metadata_snapshot(common)
        checkpoints, evidence = None, None

        def host_check():
            try:
                runtime.validate_root(selection)
                if runtime._guard_snapshot(pointer) != guard or runtime._metadata_snapshot(common) != protected:
                    raise runtime.Refusal("protected_state_changed")
            except (OSError, runtime.Refusal):
                raise runtime.Refusal("protected_state_changed") from None
            if checkpoints is not None:
                try:
                    observed = _verify_checkpoints(root, checkpoints)
                except (OSError, runtime.Refusal):
                    raise runtime.Refusal("checkpoint_changed") from None
                report["acknowledged_state"], report["unacknowledged_state"] = observed["acknowledged"], observed["unacknowledged"]
            if evidence is not None:
                for name, original in evidence.items():
                    try:
                        if runtime._regular_identity(root / "evidence" / name, 10 * 1024 * 1024) != original:
                            raise runtime.Refusal("evidence_changed")
                    except (OSError, runtime.Refusal):
                        raise runtime.Refusal("evidence_changed") from None

        final_host = host_check

        def checked(call, ordinary=True):
            runtime._remaining(deadline)
            host_check()
            if ordinary and controller.identity(deadline) != expected:
                raise runtime.Refusal("sandbox_identity")
            try:
                return call()
            finally:
                host_check()
                if ordinary:
                    runtime._remaining(deadline)
                    if controller.identity(deadline) != expected:
                        raise runtime.Refusal("sandbox_identity")

        for operation in ("checkpoint_create", "unacknowledged_create"):
            value = checked(lambda: controller.execute(_recovery_program(operation), deadline))
            if (type(value.get("schema_version")) is not int
                    or value != {"schema_version": 1, "operation": operation, "outcome": "succeeded"}):
                raise runtime.Refusal("invalid_recovery_output")
            if operation == "checkpoint_create":
                checkpoints = _checkpoint_snapshot(root)
        host_check()
        report["checks"].append({"operation": "checkpoint", "status": "passed", "durability": "fsync_acknowledged"})

        deadline = min(experiment_deadline, time.monotonic() + 60)
        before_worker = _validate_worker_state(checked(lambda: controller.worker_state(deadline)), expected[3])
        if before_worker["running"] is not True or before_worker["pid"] != expected[4]:
            raise runtime.Refusal("worker_identity")
        report["worker_state"] = "running"
        before_gateway = _validate_gateway_state(checked(lambda: controller.gateway_state(deadline)), True)
        checked(lambda: controller.gateway_stop(deadline), False)
        inactive = _validate_gateway_state(checked(lambda: controller.gateway_state(deadline), False), False)
        if inactive["configuration_sha256"] != before_gateway["configuration_sha256"]:
            raise runtime.Refusal("gateway_identity")
        checked(lambda: controller.gateway_start(deadline), False)
        after_gateway = _validate_gateway_state(checked(lambda: controller.gateway_state(deadline)), True)
        if (after_gateway["configuration_sha256"] != before_gateway["configuration_sha256"]
                or (after_gateway["pid"], after_gateway["start_ticks"]) == (before_gateway["pid"], before_gateway["start_ticks"])):
            raise runtime.Refusal("gateway_identity")
        report["checks"].append({"operation": "gateway_interruption", "status": "passed"})

        deadline = min(experiment_deadline, time.monotonic() + 60)
        checked(lambda: _storage_case(root, controller, deadline, host_check))
        report["checks"].append({"operation": "storage_permission_denial", "status": "passed", "scope": "synthetic_object_permission"})

        deadline = min(experiment_deadline, time.monotonic() + 60)
        before_worker = _validate_worker_state(checked(lambda: controller.worker_state(deadline)), expected[3])
        _validate_worker_config(root)
        runtime._check_pointer_evidence(root, 256 * 1024, 16)
        evidence = {path.name: runtime._regular_identity(path, 10 * 1024 * 1024) for path in (root / "evidence").iterdir()}
        report["worker_state"] = "unknown"
        checked(lambda: controller.worker_stop(deadline), False)
        if checked(lambda: controller.worker_stopped(deadline), False) is not True:
            raise runtime.Refusal("worker_stop_unobserved")
        report["worker_state"] = "stopped"
        _validate_worker_config(root)
        checked(lambda: controller.worker_start(deadline), False)
        _validate_worker_config(root)
        after_worker = _validate_worker_state(checked(lambda: controller.worker_state(deadline), False), expected[3])
        if after_worker["boot_id"] == before_worker["boot_id"]:
            raise runtime.Refusal("worker_restart_unobserved")
        report["worker_state"], report["recovery_kind"] = "restarted", "worker_restart"
        report["checks"].append({"operation": "worker_restart", "status": "passed",
                                 "workload_running": after_worker["running"],
                                 "before": before_worker, "after": after_worker})
        report["status"] = "passed"
    except runtime.Refusal as error:
        runtime._record_truncation(report, error)
        report["reason"] = str(error)
        if str(error) in {"protected_state_changed", "checkpoint_changed", "evidence_changed", "storage_denial_unobserved"}:
            report["status"] = "failed"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        report["reason"] = "recovery_observation_unavailable"
    if final_host is not None:
        try:
            final_host()
        except runtime.Refusal as error:
            report["status"], report["reason"] = "failed", str(error)
    if admitted:
        try:
            report["retained"] = True
            runtime._write_pointer_evidence(selection.root, report)
        except (OSError, runtime.Refusal):
            report["retained"] = False
            if report["status"] != "failed":
                report["status"], report["reason"] = "unavailable", "evidence_retention_failed"
    return report
