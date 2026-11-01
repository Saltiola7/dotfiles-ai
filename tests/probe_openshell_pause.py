"""Bounded, credential-free whole-container pause observations; never installed."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

import probe_openshell_runtime as runtime
import probe_openshell_network as network


ROLES = ("parent", "child", "background")


def _require_prerequisites(root: Path, digest: str) -> None:
    required = {"immutable_git_pointer", "containment", "network"}
    seen = set()
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
            seen.add(value["probe"])
    if seen != required:
        raise runtime.Refusal("missing_prerequisite")


def _validate_native_snapshot(value: dict, expected: tuple, paused: bool) -> dict:
    keys = {"container_id", "container_pid", "container_started_at", "paused", "frozen",
            "cgroup", "cpu_usage_usec", "members"}
    if (not isinstance(value, dict) or set(value) != keys
            or value["container_id"] != expected[3] or type(value["container_pid"]) is not int
            or value["container_pid"] != expected[4] or value["container_started_at"] != expected[5]
            or value["paused"] is not paused or value["frozen"] is not paused
            or type(value["cpu_usage_usec"]) is not int or value["cpu_usage_usec"] < 0
            or not isinstance(value["cgroup"], str) or not value["cgroup"].startswith("/sys/fs/cgroup/")
            or any(part in {"", ".", ".."} for part in value["cgroup"].split("/")[1:])
            or not isinstance(value["members"], list) or not 1 <= len(value["members"]) <= 1024):
        raise runtime.Refusal("pause_violation")
    pids, inner = set(), set()
    for member in value["members"]:
        if (not isinstance(member, dict) or set(member) != {"pid", "start_ticks", "inner_pid"}
                or any(type(member[key]) is not int or member[key] <= 0 for key in member)
                or member["pid"] in pids or member["inner_pid"] in inner):
            raise runtime.Refusal("pause_violation")
        pids.add(member["pid"])
        inner.add(member["inner_pid"])
    if expected[4] not in pids or not any(row["pid"] == expected[4] and row["inner_pid"] == 1 for row in value["members"]):
        raise runtime.Refusal("pause_violation")
    return value


def _role_file(path: Path) -> bytes:
    try:
        return runtime.private_file(path, 4096)
    except FileNotFoundError:
        raise
    except OSError:
        raise runtime.Refusal("invalid_role") from None


def _role_snapshot(root: Path, session: str) -> dict:
    directory = root / "fixture/task/.openshell-pause"
    runtime.private_directory(directory)
    found = {}
    for role in ROLES:
        value = runtime.decode_object(_role_file(directory / f"{role}.json"))
        if (set(value) != {"schema_version", "role", "pid", "start_ticks", "session", "counter", "inflight", "held", "error"}
                or type(value["schema_version"]) is not int or value["schema_version"] != 1
                or value["role"] != role or value["session"] != session
                or any(type(value[key]) is not int or value[key] <= 0 for key in ("pid", "start_ticks"))
                or type(value["counter"]) is not int or not 0 <= value["counter"] <= 55
                or any(type(value[key]) is not bool for key in ("inflight", "held", "error"))):
            raise runtime.Refusal("invalid_role")
        if value["error"]:
            raise runtime.Refusal("pause_fixture_error")
        raw = _role_file(directory / f"{role}.txt")
        expected = "".join(f"{session}:{role}:{counter}\n" for counter in range(value["counter"] + 1)).encode()
        if raw != expected:
            raise runtime.Refusal("role_snapshot_unsettled")
        found[role] = {"state": value, "source_sha256": hashlib.sha256(raw).hexdigest()}
    if len({row["state"]["pid"] for row in found.values()}) != 3:
        raise runtime.Refusal("invalid_role")
    return found


def _wait_until(predicate, deadline: float):
    while True:
        if time.monotonic() >= deadline:
            raise runtime.Refusal("pause_timeout")
        try:
            value = predicate()
        except FileNotFoundError:
            value = None
        except runtime.Refusal as error:
            if str(error) != "role_snapshot_unsettled":
                raise
            value = None
        if value:
            return value
        time.sleep(min(0.1, max(0, deadline - time.monotonic())))


def _fixture_program(session: str, address: str) -> str:
    if re.fullmatch(r"[0-9a-f]{32}", session) is None:
        raise runtime.Refusal("invalid_pause_session")
    return """import http.client,json,os,signal,time
session,address=%r,%r
base='/work/.openshell-pause'
finish=time.monotonic()+55
os.mkdir(base,0o700)
def state_write(role,value):
    temporary=base+'/'+role+'.tmp'
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(json.dumps(value,sort_keys=True).encode());stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,base+'/'+role+'.json')
def role_loop(role):
    remaining=finish-time.monotonic()
    if remaining<=0:os._exit(0)
    signal.signal(signal.SIGALRM,signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL,remaining)
    with open('/proc/self/stat') as stream:raw=stream.read(4096)
    ticks=int(raw[raw.rfind(')')+2:].split()[19])
    value={'schema_version':1,'role':role,'pid':os.getpid(),'start_ticks':ticks,'session':session,
           'counter':0,'inflight':False,'held':False,'error':False}
    source=base+'/'+role+'.txt'
    fd=os.open(source,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.write(fd,(session+':'+role+':0\\n').encode());os.fsync(fd);os.close(fd)
    state_write(role,value)
    next_request=time.monotonic()
    try:
        while time.monotonic()<finish:
            if os.path.exists(base+'/hold'):
                if not value['held']:
                    value['held']=True;state_write(role,value)
                time.sleep(min(0.05,max(0,finish-time.monotonic())));continue
            if value['held']:
                value['held']=False;state_write(role,value)
            if time.monotonic()<next_request:
                time.sleep(min(0.05,max(0,min(next_request,finish)-time.monotonic())));continue
            next_request=time.monotonic()+1
            value['inflight']=True;state_write(role,value)
            remaining=finish-time.monotonic()
            if remaining<=0:os._exit(0)
            connection=http.client.HTTPConnection(address,18080,timeout=min(1,remaining))
            try:
                connection.request('GET','/probe',headers={'X-Qualification-Case':'pause-'+session+'-'+role})
                response=connection.getresponse()
                if response.status!=200 or response.read(128)!=b'openshell-network-probe\\n':raise RuntimeError()
            finally:connection.close()
            value['counter']+=1
            fd=os.open(source,os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
            os.write(fd,(session+':'+role+':'+str(value['counter'])+'\\n').encode());os.fsync(fd);os.close(fd)
            value['inflight']=False;state_write(role,value)
    except Exception:
        value['inflight']=False;value['error']=True;state_write(role,value)
    os._exit(0)
child=os.fork()
if child==0:
    os.setsid()
    null=os.open('/dev/null',os.O_RDONLY)
    for descriptor in (0,1,2):os.dup2(null,descriptor)
    descriptors=os.listdir('/proc/self/fd')
    if len(descriptors)>256:os._exit(1)
    for descriptor in descriptors:
        if int(descriptor)>2:
            try:os.close(int(descriptor))
            except OSError:pass
    child=os.fork()
    if child==0:role_loop('child')
    background=os.fork()
    if background==0:
        os.setsid();role_loop('background')
    role_loop('parent')
print(json.dumps({'schema_version':1,'session':session,'started':True}))
""" % (session, address)


class _PauseController(runtime._PointerController):
    def launch(self, session: str, address: str, deadline: float) -> dict:
        return self.execute(_fixture_program(session, address), deadline)

    def pause(self, deadline: float) -> None:
        self.guest(["/usr/bin/podman", "pause", self.prepared["container_id"]], deadline)

    def unpause(self, deadline: float) -> None:
        self.guest(["/usr/bin/podman", "unpause", self.prepared["container_id"]], deadline)

    def gateway(self, deadline: float) -> bool:
        expected, _ = runtime._validate_generation(self.root)
        result = self.guest(["/usr/bin/openshell", "sandbox", "get", self.sandbox_name, "-o", "json"], deadline)
        value = runtime.decode_object(result.stdout)
        admission = value.get("configuration_admission", {})
        if (not isinstance(admission, dict)
                or any(type(admission.get(key)) is not int or admission[key] <= 0
                       for key in ("policy_version", "config_revision", "provider_env_revision"))
                or any(type(value.get(key)) is not int or value[key] <= 0
                       for key in ("main_process_started_at_ms", "current_policy_version"))):
            raise runtime.Refusal("sandbox_identity")
        observed = (value.get("id"), value.get("main_process_instance_id"), value.get("main_process_started_at_ms"),
                    admission.get("policy_hash"), admission.get("policy_version"), admission.get("config_revision"),
                    admission.get("provider_env_revision"), value.get("current_policy_version"))
        if (value.get("name") != self.sandbox_name or admission.get("state") != "accepted"
                or observed != (*expected[:3], *expected[6:])):
            raise runtime.Refusal("sandbox_identity")
        return True

    def snapshot(self, deadline: float, paused: bool) -> dict:
        expected, _ = runtime._validate_generation(self.root)
        result = self.guest(["/usr/bin/podman", "inspect", "--type", "container", self.prepared["container_id"]], deadline)
        try:
            items = json.loads(result.stdout)
            if not isinstance(items, list) or len(items) != 1:
                raise ValueError
            item = items[0]
            state, labels = item["State"], item["Config"]["Labels"]
            if (item["Id"] != expected[3] or state["Running"] is not True or state["Paused"] is not paused
                    or state["Pid"] != expected[4] or state["StartedAt"] != expected[5]
                    or labels.get("openshell.managed") != "true"
                    or labels.get("openshell.ai/isolation-role") != "sandbox"
                    or labels.get("openshell.ai/sandbox-id") != expected[0]):
                raise ValueError
        except (ValueError, TypeError, KeyError, AttributeError):
            raise runtime.Refusal("pause_violation") from None
        program = """import json,os,pathlib,sys
pid=int(sys.argv[1])
def read(path,limit=65536):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:data=stream.read(limit+1)
    if len(data)>limit:raise ValueError()
    return data.decode()
try:
    groups=read('/proc/'+str(pid)+'/cgroup',4096).splitlines()
    if len(groups)!=1 or not groups[0].startswith('0::/') or '..' in groups[0].split('/'):raise ValueError()
    base=pathlib.Path('/sys/fs/cgroup'+groups[0][3:]).resolve(strict=True)
    if not base.is_relative_to('/sys/fs/cgroup'):raise ValueError()
    events=dict(line.split() for line in read(base/'cgroup.events').splitlines())
    if events.get('frozen') not in ('0','1'):raise ValueError()
    cpu=dict(line.split() for line in read(base/'cpu.stat').splitlines())
    pending=[base];pids=set();count=0
    while pending:
        directory=pending.pop();count+=1
        if count>128:raise ValueError()
        pids.update(map(int,read(directory/'cgroup.procs').split()))
        if len(pids)>1024:raise ValueError()
        for entry in directory.iterdir():
            if entry.is_dir() and not entry.is_symlink():pending.append(entry)
            if len(pending)>128:raise ValueError()
    members=[]
    for member in sorted(pids):
        raw=read('/proc/'+str(member)+'/stat',4096)
        ticks=int(raw[raw.rfind(')')+2:].split()[19])
        namespace=[line.split()[1:] for line in read('/proc/'+str(member)+'/status').splitlines() if line.startswith('NSpid:')]
        if len(namespace)!=1 or not namespace[0]:raise ValueError()
        members.append({'pid':member,'start_ticks':ticks,'inner_pid':int(namespace[0][-1])})
    print(json.dumps({'cgroup':str(base),'cpu_usage_usec':int(cpu['usage_usec']),'frozen':events['frozen']=='1','members':members}))
except (OSError,ValueError,KeyError,IndexError,UnicodeError):print(json.dumps({'error':'native_snapshot_unavailable'}))
"""
        observed = runtime.decode_object(self.guest(["/usr/bin/python3", "-I", "-B", "-c", program, str(expected[4])], deadline).stdout)
        if "error" in observed:
            raise runtime.Refusal("native_snapshot_unavailable")
        observed.update(container_id=item["Id"], container_pid=state["Pid"],
                        container_started_at=state["StartedAt"], paused=state["Paused"])
        return _validate_native_snapshot(observed, expected, paused)


def _members(snapshot: dict) -> tuple:
    return tuple(sorted((row["pid"], row["start_ticks"], row["inner_pid"]) for row in snapshot["members"]))


def _bind_roles(roles: dict, snapshot: dict) -> None:
    members = {(row["inner_pid"], row["start_ticks"]) for row in snapshot["members"]}
    if any((row["state"]["pid"], row["state"]["start_ticks"]) not in members for row in roles.values()):
        raise runtime.Refusal("resume_identity")


def pause_resume_probe(selection: runtime.Selection) -> dict:
    report = {"schema_version": 1, "probe": "pause_resume", "status": "unavailable", "reason": None,
              "checks": [], "runtime_qualification": "not_run", "generation_sha256": None,
              "truncation": {"transport_output": False, "limit_bytes": None}, "retained": False,
              "workload_state": "unknown"}
    admitted, final_guard = False, None
    try:
        runtime.validate_root(selection)
        deadline = min(runtime._prepared_deadline(selection.root), time.monotonic() + 60)
        expected, report["generation_sha256"] = runtime._validate_generation(selection.root)
        guard = runtime._validate_guard(selection.root)
        _require_prerequisites(selection.root, report["generation_sha256"])
        receipt = network._validate_network_receipt(selection.root)
        directory = selection.root / "fixture/task/.openshell-pause"
        if os.path.lexists(directory):
            raise runtime.Refusal("probe_collision")
        admitted = True
        controller = _PauseController(selection, deadline)
        common, pointer = runtime._host_git_fixture(selection.root, controller.env, deadline)
        protected = runtime._metadata_snapshot(common)

        def unchanged():
            try:
                runtime.validate_root(selection)
                if runtime._guard_snapshot(pointer) != guard or runtime._metadata_snapshot(common) != protected:
                    raise runtime.Refusal("protected_state_changed")
            except (OSError, runtime.Refusal):
                raise runtime.Refusal("protected_state_changed") from None

        final_guard = unchanged

        def checked(call, ordinary=True):
            if time.monotonic() >= deadline:
                raise runtime.Refusal("pause_timeout")
            unchanged()
            if ordinary and controller.identity(deadline) != expected:
                raise runtime.Refusal("sandbox_identity")
            try:
                return call()
            finally:
                unchanged()
                if ordinary and controller.identity(deadline) != expected:
                    raise runtime.Refusal("sandbox_identity")

        prior_listener = None

        def listener(ordinary=True):
            nonlocal prior_listener
            value = checked(lambda: network.listener_observation(controller, receipt, deadline), ordinary)
            if prior_listener is not None:
                for key in ("address", "pid", "start_ticks", "uid", "source_sha256", "socket_inodes", "record_identity"):
                    if value[key] != prior_listener[key]:
                        raise runtime.Refusal("listener_identity")
                if value["records"][:len(prior_listener["records"])] != prior_listener["records"] or value["record_size"] < prior_listener["record_size"]:
                    raise runtime.Refusal("listener_identity")
            prior_listener = value
            return value

        session = uuid.uuid4().hex
        initial_listener = listener()
        result = checked(lambda: controller.launch(session, receipt["address"], deadline))
        if (set(result) != {"schema_version", "session", "started"} or type(result["schema_version"]) is not int
                or result != {"schema_version": 1, "session": session, "started": True}):
            raise runtime.Refusal("pause_fixture_error")
        report["workload_state"] = "running"

        def counts(observation):
            return {role: sum(row["token"] == f"pause-{session}-{role}" and row["port"] == 18080
                              and row["method"] == "GET" and row["path"] == "/probe" and row["accepted"] is True
                              for row in observation["records"]) for role in ROLES}

        def progress(after=None):
            roles = _role_snapshot(selection.root, session)
            arrivals = listener()
            observed = counts(arrivals)
            for role in ROLES:
                value = roles[role]["state"]
                if after is not None:
                    original = after[0][role]["state"]
                    if any(value[key] != original[key] for key in ("pid", "start_ticks", "session")):
                        raise runtime.Refusal("resume_identity")
                    if value["counter"] <= original["counter"] or observed[role] <= counts(after[1])[role]:
                        return None
                elif value["counter"] < 1 or observed[role] <= counts(initial_listener)[role]:
                    return None
            return roles, arrivals

        first = _wait_until(progress, deadline)
        _wait_until(lambda: progress(first), deadline)
        report["checks"].append({"operation": "progress", "status": "passed"})
        hold = directory / "hold"
        fd = os.open(hold, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(b"hold\n"); stream.flush(); os.fsync(stream.fileno())

        def held():
            roles = _role_snapshot(selection.root, session)
            return roles if all(row["state"]["held"] and not row["state"]["inflight"] for row in roles.values()) else None

        held_roles = _wait_until(held, deadline)
        before = checked(lambda: controller.snapshot(deadline, False))
        _validate_native_snapshot(before, expected, False)
        _bind_roles(held_roles, before)
        held_listener = listener()
        report["workload_state"] = "unknown"
        checked(lambda: controller.pause(deadline), ordinary=False)
        report["workload_state"] = "paused"
        frozen_first = checked(lambda: controller.snapshot(deadline, True), ordinary=False)
        _validate_native_snapshot(frozen_first, expected, True)
        if _members(frozen_first) != _members(before) or frozen_first["cgroup"] != before["cgroup"]:
            raise runtime.Refusal("pause_violation")
        hold.unlink()
        frozen_roles = _role_snapshot(selection.root, session)
        frozen_listener = listener(False)
        if frozen_roles != held_roles or frozen_listener["records"] != held_listener["records"]:
            raise runtime.Refusal("pause_violation")
        if checked(lambda: controller.gateway(deadline), ordinary=False) is not True:
            raise runtime.Refusal("gateway_unavailable")
        report["checks"].append({"operation": "gateway", "status": "passed"})
        if deadline - time.monotonic() <= 1:
            raise runtime.Refusal("pause_timeout")
        time.sleep(1)
        frozen_second = checked(lambda: controller.snapshot(deadline, True), ordinary=False)
        _validate_native_snapshot(frozen_second, expected, True)
        if (frozen_second != frozen_first or _role_snapshot(selection.root, session) != frozen_roles
                or listener(False)["records"] != frozen_listener["records"]):
            raise runtime.Refusal("pause_violation")
        report["checks"].append({"operation": "pause", "status": "passed"})
        report["workload_state"] = "unknown"
        checked(lambda: controller.unpause(deadline), ordinary=False)
        report["workload_state"] = "running"
        resumed = _wait_until(lambda: progress((frozen_roles, frozen_listener)), deadline)
        after = checked(lambda: controller.snapshot(deadline, False))
        _validate_native_snapshot(after, expected, False)
        _bind_roles(resumed[0], after)
        if _members(after) != _members(before) or after["cgroup"] != before["cgroup"]:
            raise runtime.Refusal("resume_identity")
        report["checks"].append({"operation": "resume", "status": "passed"})
        report["status"] = "passed"
    except runtime.Refusal as error:
        runtime._record_truncation(report, error)
        report["reason"] = str(error)
        if str(error) in {"protected_state_changed", "pause_violation", "resume_identity"}:
            report["status"] = "failed"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        report["reason"] = "pause_observation_unavailable"
    if final_guard is not None:
        try:
            final_guard()
        except runtime.Refusal:
            report["status"], report["reason"] = "failed", "protected_state_changed"
    if admitted:
        try:
            report["retained"] = True
            runtime._write_pointer_evidence(selection.root, report)
        except (OSError, runtime.Refusal):
            report["retained"] = False
            if report["status"] != "failed":
                report["status"], report["reason"] = "unavailable", "evidence_retention_failed"
    return report
