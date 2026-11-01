"""Fixed synthetic network observations; not a launcher or policy editor."""
from __future__ import annotations

import hashlib
import ipaddress
import json
from pathlib import Path
import re
import stat
import time
import uuid

import probe_openshell_runtime as runtime


BODY = b"openshell-network-probe\n"
BODY_SHA256 = hashlib.sha256(BODY).hexdigest()
LISTENER_SOURCE = Path(__file__).parent / "fixtures/openshell_runtime/network_listener.py"
OPERATIONS = ("allowed", "denied_method", "denied_path", "denied_proxy", "denied_clear", "denied_socket")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")


def _address(value: object) -> str:
    try:
        if not isinstance(value, str):
            raise ValueError()
        address = ipaddress.IPv4Address(value)
        if str(address) != value or not any(address in ipaddress.IPv4Network(network) for network in
                                            ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")):
            raise ValueError()
    except ValueError:
        raise runtime.Refusal("invalid_network_receipt") from None
    return value


def _validate_network_receipt(root: Path) -> dict:
    value = runtime.decode_object(runtime.private_file(root / "network.json"))
    if (set(value) != {"schema_version", "address", "listener_pid", "listener_start_ticks", "listener_source_sha256"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or any(type(value[key]) is not int or value[key] <= 0
                   for key in ("listener_pid", "listener_start_ticks"))
            or not isinstance(value["listener_source_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", value["listener_source_sha256"]) is None):
        raise runtime.Refusal("invalid_network_receipt")
    _address(value["address"])
    if runtime._regular_identity(LISTENER_SOURCE, 1024 * 1024)[-1] != value["listener_source_sha256"]:
        raise runtime.Refusal("invalid_network_receipt")
    return value


def expected_policy(address: str) -> dict:
    """Exact authored policy, including explicit non-writable runtime baselines."""
    _address(address)
    return {
        "version": 1,
        "filesystem_policy": {
            "include_workdir": False,
            "read_only": ["/usr", "/bin", "/lib", "/etc", "/proc", "/dev/urandom",
                          "/app", "/var/log", "/tmp", "/dev/null"],
            "read_write": ["/work", "/scratch"],
        },
        "landlock": {"compatibility": "hard_requirement"},
        "process": {"run_as_user": "sandbox", "run_as_group": "sandbox"},
        "network_policies": {"qualification_probe": {
            "name": "qualification_probe",
            "endpoints": [{"host": address, "port": 18080, "allowed_ips": [address + "/32"],
                           "protocol": "rest", "enforcement": "enforce",
                           "rules": [{"allow": {"method": "GET", "path": "/probe"}}]}],
            "binaries": [{"path": "/usr/local/bin/python3.13"}],
        }},
    }


def _check_policy(controller, receipt: dict, generation: tuple, deadline: float) -> None:
    value = runtime.decode_object(controller.guest(
        ["/usr/bin/openshell", "policy", "get", controller.sandbox_name, "--full", "-o", "json"], deadline).stdout)
    expected = {"scope": "sandbox", "sandbox": controller.sandbox_name, "version": generation[7],
                "active_version": generation[10], "hash": generation[6], "status": "effective",
                "config_revision": generation[8], "policy_source": "sandbox",
                "policy": expected_policy(receipt["address"])}
    # Equality covers provider/global additions as well as the authored rule.
    # Do not coerce booleans into revision integers.
    if (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            != json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False)):
        raise runtime.Refusal("network_policy_mismatch")


_OBSERVATION_PROGRAM = r'''import fcntl,hashlib,json,os,pathlib,re,socket,stat,struct,sys
purpose = 'listener_observation'
pid,start,address,source,record_directory,uid,source_sha=sys.argv[1:]
pid,start,uid=int(pid),int(start),int(uid)
def read(path,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):raise ValueError()
        raw=stream.read(limit+1)
        after=os.fstat(stream.fileno())
    if len(raw)>limit or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError()
    return raw,before
def ticks():
    data,_=read('/proc/'+str(pid)+'/stat',16384)
    return int(data.rsplit(b')',1)[1].split()[19])
def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError()
        result[key]=value
    return result
try:
    if ticks()!=start or os.stat('/proc/'+str(pid)).st_uid!=uid:raise ValueError()
    status,_=read('/proc/'+str(pid)+'/status',65536)
    ids=next(line.split()[1:] for line in status.splitlines() if line.startswith(b'Uid:'))
    if any(int(value)!=uid for value in ids):raise ValueError()
    addresses=[]
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as stream:
        for _,name in socket.if_nameindex():
            try:
                result=fcntl.ioctl(stream.fileno(),0x8915,struct.pack('256s',name.encode()[:15]))
                addresses.append(socket.inet_ntoa(result[20:24]))
            except OSError:pass
    if address not in addresses:raise ValueError()
    body,source_info=read(source,1048576)
    if source_info.st_uid!=uid or source_info.st_nlink!=1 or hashlib.sha256(body).hexdigest()!=source_sha:raise ValueError()
    command,_=read('/proc/'+str(pid)+'/cmdline',16384)
    if command.split(b'\0').count(os.fsencode(source))!=1:raise ValueError()
    if os.path.realpath('/proc/'+str(pid)+'/exe')!=os.path.realpath('/usr/bin/python3'):raise ValueError()
    record=pathlib.Path(record_directory)
    for directory in (record.parent,record):
        info=directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=uid or stat.S_IMODE(info.st_mode)!=0o700 or directory.resolve()!=directory:raise ValueError()
    data,record_info=read(record/'events.jsonl',65536)
    if record_info.st_uid!=uid or record_info.st_nlink!=1 or stat.S_IMODE(record_info.st_mode)!=0o600:raise ValueError()
    if data and not data.endswith(b'\n'):raise ValueError()
    records=[json.loads(line,object_pairs_hook=unique) for line in data.splitlines()]
    if len(records)>256:raise ValueError()
    descriptors=list(pathlib.Path('/proc/'+str(pid)+'/fd').iterdir())
    if len(descriptors)>256:raise ValueError()
    sockets=set();record_open=False
    for entry in descriptors:
        target=os.readlink(entry)
        match=re.fullmatch(r'socket:\[(\d+)\]',target)
        if match:sockets.add(int(match[1]))
        if target==str(record/'events.jsonl'):record_open=True
    if not record_open:raise ValueError()
    expected=socket.inet_aton(address)[::-1].hex().upper()
    found={}
    for table in ('tcp','tcp6'):
        raw,_=read('/proc/'+str(pid)+'/net/'+table,262144)
        for line in raw.decode().splitlines()[1:]:
            fields=line.split()
            if len(fields)<10 or fields[3]!='0A' or int(fields[9]) not in sockets:continue
            host,port=fields[1].split(':');port=int(port,16)
            if table!='tcp' or host!=expected or port not in (18080,18081) or str(port) in found:raise ValueError()
            found[str(port)]=int(fields[9])
    if set(found)!={'18080','18081'} or ticks()!=start:raise ValueError()
    value={'address':address,'pid':pid,'start_ticks':start,'uid':uid,'source_sha256':source_sha,
           'socket_inodes':found,'record_identity':{'device':record_info.st_dev,'inode':record_info.st_ino,
           'uid':record_info.st_uid,'mode':record_info.st_mode,'link_count':record_info.st_nlink},
           'record_size':len(data),'records':records}
    print(json.dumps(value,sort_keys=True))
except (OSError,ValueError,TypeError,KeyError,IndexError,StopIteration,UnicodeError):
    print(json.dumps({'error':'listener_observation_unavailable'}))
'''


def _validate_listener_observation(value: dict, receipt: dict, uid: int) -> dict:
    if (set(value) != {"address", "pid", "start_ticks", "uid", "source_sha256", "socket_inodes",
                      "record_identity", "record_size", "records"}
            or value["address"] != receipt["address"] or value["pid"] != receipt["listener_pid"]
            or value["start_ticks"] != receipt["listener_start_ticks"] or value["uid"] != uid
            or value["source_sha256"] != receipt["listener_source_sha256"]
            or any(type(value[key]) is not int or value[key] <= 0 for key in ("pid", "start_ticks", "uid"))
            or type(value["record_size"]) is not int or not 0 <= value["record_size"] <= 65536
            or not isinstance(value["socket_inodes"], dict) or set(value["socket_inodes"]) != {"18080", "18081"}
            or any(type(item) is not int or item <= 0 for item in value["socket_inodes"].values())
            or len(set(value["socket_inodes"].values())) != 2
            or not isinstance(value["record_identity"], dict)
            or set(value["record_identity"]) != {"device", "inode", "uid", "mode", "link_count"}
            or not isinstance(value["records"], list) or len(value["records"]) > 256):
        raise runtime.Refusal("listener_observation_unavailable")
    info = value["record_identity"]
    if (any(type(item) is not int for item in info.values()) or info["device"] < 0 or info["inode"] <= 0
            or info["uid"] != uid or info["link_count"] != 1
            or not stat.S_ISREG(info["mode"]) or stat.S_IMODE(info["mode"]) != 0o600):
        raise runtime.Refusal("listener_observation_unavailable")
    for row in value["records"]:
        if (not isinstance(row, dict) or set(row) != {"schema_version", "token", "port", "method", "path", "accepted"}
                or type(row["schema_version"]) is not int or row["schema_version"] != 1
                or not isinstance(row["token"], str) or (row["token"] != "" and _TOKEN.fullmatch(row["token"]) is None)
                or type(row["port"]) is not int or row["port"] not in (18080, 18081)
                or row["method"] not in {"GET", "POST", "HEAD", "OPTIONS", "CONNECT", "OTHER"}
                or row["path"] not in {"/probe", "other"} or type(row["accepted"]) is not bool):
            raise runtime.Refusal("listener_observation_unavailable")
    return value


def listener_observation(controller, receipt: dict, deadline: float) -> dict:
    """Read the selected listener's native identity and append-only bounded records."""
    directory = controller.guest_home + "/openshell-qualification/network-records"
    result = controller.guest(["/usr/bin/python3", "-I", "-B", "-c", _OBSERVATION_PROGRAM,
                               str(receipt["listener_pid"]), str(receipt["listener_start_ticks"]),
                               receipt["address"], str(controller.root / "input/network_listener.py"),
                               directory, str(controller.guest_uid), receipt["listener_source_sha256"]], deadline)
    return _validate_listener_observation(runtime.decode_object(result.stdout), receipt, controller.guest_uid)


_CONTROL_PROGRAM = r'''import hashlib,http.client,json,sys
purpose = 'listener_control'
address,token,port=sys.argv[1:]
connection=http.client.HTTPConnection(address,int(port),timeout=3)
try:
    connection.request('GET','/probe',headers={'X-Qualification-Case':token,'Connection':'close'})
    response=connection.getresponse();body=response.read(4097)
    if len(body)>4096:raise ValueError()
    print(json.dumps({'schema_version':1,'status':response.status,'response_sha256':hashlib.sha256(body).hexdigest()}))
finally:connection.close()
'''


def _controller_request(controller, address: str, token: str, port: int, deadline: float) -> None:
    result = controller.guest(["/usr/bin/python3", "-I", "-B", "-c", _CONTROL_PROGRAM,
                               address, token, str(port)], deadline)
    value = runtime.decode_object(result.stdout)
    if (value != {"schema_version": 1, "status": 200, "response_sha256": BODY_SHA256}
            or type(value.get("schema_version")) is not int or type(value.get("status")) is not int):
        raise runtime.Refusal("listener_positive_control")


def _network_program(operation: str, address: str, token: str) -> str:
    if operation not in OPERATIONS or _TOKEN.fullmatch(token) is None:
        raise runtime.Refusal("invalid_probe")
    _address(address)
    return "import errno,hashlib,http.client,json,os,socket,urllib.error,urllib.request\noperation,address,token=%r\n" % (
        (operation, address, token),) + r'''
port=18081 if operation in ('denied_proxy','denied_clear','denied_socket') else 18080
method='POST' if operation=='denied_method' else 'GET'
path='/denied' if operation=='denied_path' else '/probe'
out={'schema_version':1,'operation':operation,'outcome':'unavailable','errno':0,'status':0,'response_sha256':'',
     'binary':os.readlink('/proc/self/exe')}
if out['binary']!='/usr/local/bin/python3.13':
    print(json.dumps(out,sort_keys=True));raise SystemExit(0)
if operation in ('denied_clear','denied_socket'):
    for key in list(os.environ):
        if key.lower() in ('http_proxy','https_proxy','all_proxy','no_proxy'):os.environ.pop(key,None)
try:
    if operation=='denied_socket':
        with socket.create_connection((address,port),timeout=3) as stream:
            stream.settimeout(3)
            stream.sendall(('GET /probe HTTP/1.1\r\nHost: '+address+':'+str(port)+'\r\nX-Qualification-Case: '+token+'\r\nConnection: close\r\n\r\n').encode())
            response=http.client.HTTPResponse(stream);response.begin();body=response.read(8193);status=response.status
    else:
        request=urllib.request.Request('http://'+address+':'+str(port)+path,method=method,
            headers={'X-Qualification-Case':token,'Connection':'close'})
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({})) if operation=='denied_clear' else urllib.request.build_opener()
        try:
            with opener.open(request,timeout=3) as response:body=response.read(8193);status=response.status
        except urllib.error.HTTPError as error:
            body=error.read(8193);status=error.code;error.close()
    if len(body)>8192:raise ValueError()
    out['status']=status
    if status==200:
        out['outcome']='allowed';out['response_sha256']=hashlib.sha256(body).hexdigest()
    elif status==403:
        denial=json.loads(body)
        permitted={'policy_denied','ssrf_denied'} if port==18081 else {'policy_denied'}
        if isinstance(denial,dict) and isinstance(denial.get('error'),str) and denial['error'] in permitted:out['outcome']='denied'
except (OSError,urllib.error.URLError) as error:
    cause=error.reason if isinstance(error,urllib.error.URLError) else error
    code=getattr(cause,'errno',None)
    if type(code) is int:
        out['errno']=code
        if code in (errno.EACCES,errno.EPERM):out['outcome']='denied'
except (ValueError,http.client.HTTPException):pass
print(json.dumps(out,sort_keys=True))
'''


def _validate_result(value: dict, operation: str) -> None:
    if (not isinstance(value, dict) or set(value) != {"schema_version", "operation", "outcome", "errno", "status", "response_sha256", "binary"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["operation"] != operation or type(value["errno"]) is not int
            or type(value["status"]) is not int or not isinstance(value["response_sha256"], str)
            or value["binary"] != "/usr/local/bin/python3.13"):
        raise runtime.Refusal("invalid_probe_output")
    if operation == "allowed":
        if value != {"schema_version": 1, "operation": operation, "outcome": "allowed", "errno": 0,
                     "status": 200, "response_sha256": BODY_SHA256, "binary": "/usr/local/bin/python3.13"}:
            raise runtime.Refusal("network_positive_control")
    elif value["outcome"] == "allowed":
        raise runtime.Refusal("network_boundary")
    elif not (value["outcome"] == "denied" and value["response_sha256"] == ""
              and ((value["status"] == 403 and value["errno"] == 0)
                   or (value["status"] == 0 and value["errno"] in (1, 13)))):
        raise runtime.Refusal("network_denial_unavailable")


def _execute(controller, program: str, deadline: float) -> dict:
    """Use the policy's exact executable, independently of the workload PATH."""
    result = controller.guest(["/usr/bin/openshell", "sandbox", "exec", "--name", controller.sandbox_name,
                               "--workdir", "/work", "--no-tty", "--no-login-shell", "--timeout", "50", "--",
                               "/usr/local/bin/python3.13", "-I", "-B", "-c", program], deadline)
    if len(result.stdout) > 4096:
        raise runtime.Refusal("invalid_probe_output")
    return runtime.decode_object(result.stdout)


def network_probe(selection: runtime.Selection) -> dict:
    report = {"schema_version": 1, "probe": "network", "status": "unavailable", "reason": None,
              "runtime_qualification": "not_run", "checks": [], "retained": False,
              "generation_sha256": None, "truncation": {"transport_output": False, "limit_bytes": None}}
    admitted = False
    try:
        runtime.validate_root(selection)
        admitted = True
        deadline = runtime._prepared_deadline(selection.root)
        generation, report["generation_sha256"] = runtime._validate_generation(selection.root)
        guard = runtime._validate_guard(selection.root)
        receipt = _validate_network_receipt(selection.root)
        runtime._check_pointer_evidence(selection.root, 256 * 1024, 16)
        controller = runtime._PointerController(selection, deadline)
        common, pointer = runtime._host_git_fixture(selection.root, controller.env, deadline)
        protected = runtime._metadata_snapshot(common)
        previous = None

        def unchanged():
            try:
                runtime.validate_root(selection)
                if runtime._guard_snapshot(pointer) != guard or runtime._metadata_snapshot(common) != protected:
                    raise runtime.Refusal("protected_state_changed")
            except (OSError, runtime.Refusal):
                raise runtime.Refusal("protected_state_changed") from None

        def checked(call):
            runtime._remaining(deadline)
            step = min(deadline, time.monotonic() + 60)
            unchanged()
            if controller.identity(step) != generation:
                raise runtime.Refusal("sandbox_identity")
            try:
                return call(step)
            except runtime.Refusal as error:
                runtime._record_truncation(report, error)
                raise
            finally:
                guard_error = None
                try:
                    unchanged()
                except runtime.Refusal as error:
                    guard_error = error
                try:
                    if controller.identity(step) != generation:
                        raise runtime.Refusal("sandbox_identity")
                finally:
                    if guard_error is not None:
                        raise guard_error

        def observe(step):
            nonlocal previous
            value = listener_observation(controller, receipt, step)
            if previous is not None:
                if (any(value[key] != previous[key] for key in ("address", "pid", "start_ticks", "uid",
                                                               "source_sha256", "socket_inodes", "record_identity"))
                        or value["record_size"] < previous["record_size"]
                        or value["records"][:len(previous["records"])] != previous["records"]):
                    raise runtime.Refusal("listener_identity")
            previous = value
            return value

        def attempt(step, operation, port=None):
            before = observe(step)
            token = "network-" + uuid.uuid4().hex
            result = None
            try:
                if operation == "control":
                    _controller_request(controller, receipt["address"], token, port, step)
                else:
                    result = _execute(controller, _network_program(operation, receipt["address"], token), step)
            except runtime.Refusal as error:
                runtime._record_truncation(report, error)
                raise
            finally:
                after = observe(step)
                delta = after["records"][len(before["records"]):]
                matches = [row for row in delta if row["token"] == token]
                if operation not in ("control", "allowed") and matches:
                    raise runtime.Refusal("network_boundary")
                if operation in ("control", "allowed"):
                    expected = {"schema_version": 1, "token": token, "port": port or 18080,
                                "method": "GET", "path": "/probe", "accepted": True}
                    if matches != [expected]:
                        raise runtime.Refusal("listener_positive_control")
                if len(delta) != len(matches):
                    raise runtime.Refusal("listener_unexpected_arrival")
            if operation != "control":
                _validate_result(result, operation)

        checked(lambda step: _check_policy(controller, receipt, generation, step))
        checked(observe)
        if previous["records"]:
            raise runtime.Refusal("listener_preexisting_arrivals")
        for port in (18080, 18081):
            checked(lambda step, port=port: attempt(step, "control", port))
        for operation in OPERATIONS:
            checked(lambda step, operation=operation: attempt(step, operation))
            report["checks"].append({"operation": operation, "status": "passed"})
            runtime._write_pointer_evidence(selection.root, report)
        for port in (18080, 18081):
            checked(lambda step, port=port: attempt(step, "control", port))
        checked(lambda step: _check_policy(controller, receipt, generation, step))
        report["status"] = "passed"
    except runtime.Refusal as error:
        report["reason"] = str(error)
        runtime._record_truncation(report, error)
        if str(error) in {"protected_state_changed", "network_boundary", "network_policy_mismatch"}:
            report["status"] = "failed"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        report["reason"] = "network_observation_unavailable"
    if admitted:
        try:
            report["retained"] = True
            runtime._write_pointer_evidence(selection.root, report)
        except (OSError, runtime.Refusal):
            report["retained"] = False
            if report["status"] != "failed":
                report["status"], report["reason"] = "unavailable", "evidence_retention_failed"
    return report
