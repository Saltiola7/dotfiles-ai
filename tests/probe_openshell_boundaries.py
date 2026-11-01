"""Fixed synthetic metadata and native control observations; no lifecycle mutation."""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import time

import probe_openshell_runtime as runtime


_TARGETS = ("config", "object", "ref", "hook", "sibling_index", "lifecycle")
_VERSIONS = Path(__file__).parent / "fixtures/openshell_runtime/versions.json"


def _receipts(root: Path) -> tuple[dict, dict]:
    boundary = runtime.decode_object(runtime.private_file(root / "boundaries.json"))
    artifact = runtime.decode_object(runtime.private_file(root / "runtime-artifact.json"))
    if (set(boundary) != {"schema_version", "metadata_targets"}
            or type(boundary["schema_version"]) is not int or boundary["schema_version"] != 1
            or not isinstance(boundary["metadata_targets"], dict)
            or set(boundary["metadata_targets"]) != set(_TARGETS)):
        raise runtime.Refusal("invalid_boundaries_receipt")
    for value in boundary["metadata_targets"].values():
        if (not isinstance(value, str) or not value or len(value) > 256
                or PurePosixPath(value).is_absolute() or str(PurePosixPath(value)) != value
                or any(part in (".", "..") for part in value.split("/"))
                or any(ord(char) < 32 for char in value)):
            raise runtime.Refusal("invalid_boundaries_receipt")
    if (set(artifact) != {"schema_version", "runtime_binary_sha256", "workload_image_id"}
            or type(artifact["schema_version"]) is not int or artifact["schema_version"] != 1
            or not isinstance(artifact["runtime_binary_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", artifact["runtime_binary_sha256"]) is None
            or not isinstance(artifact["workload_image_id"], str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["workload_image_id"]) is None):
        raise runtime.Refusal("invalid_runtime_artifact")
    return boundary["metadata_targets"], artifact


def _host_targets(root: Path, common: Path, targets: dict, env: dict, deadline: float) -> dict:
    def git(directory, *args):
        result = runtime.run_command(["/usr/bin/git", "-C", str(directory), *args], cwd=root,
                                     env=env, timeout=runtime._remaining(deadline), limit=65536)
        if result.returncode:
            raise runtime.Refusal("metadata_role_unavailable")
        return result.stdout.rstrip(b"\n").decode("utf-8")
    if (targets["config"] != "config" or targets["hook"] != "hooks/openshell-qualification"
            or targets["lifecycle"] != "openshell-qualification/lifecycle"
            or re.fullmatch(r"objects/[0-9a-f]{2}/[0-9a-f]{38}", targets["object"]) is None
            or not targets["ref"].startswith("refs/heads/")
            or re.fullmatch(r"worktrees/[A-Za-z0-9_.-]+/index", targets["sibling_index"]) is None):
        raise runtime.Refusal("metadata_role_unavailable")
    found = {}
    for name, relative in targets.items():
        path = common / relative
        if path.resolve(strict=True) != path:
            raise runtime.Refusal("metadata_role_unavailable")
        found[name] = runtime._regular_identity(path, 64 * 1024 * 1024)
    oid = targets["object"].removeprefix("objects/").replace("/", "")
    if git(root / "fixture/main", "cat-file", "-t", oid) not in {"commit", "tree", "blob", "tag"}:
        raise runtime.Refusal("metadata_role_unavailable")
    git(root / "fixture/main", "check-ref-format", targets["ref"])
    git(root / "fixture/main", "show-ref", "--verify", targets["ref"])
    sibling = root / "fixture/sibling"
    admin = common / targets["sibling_index"]
    if (git(sibling, "rev-parse", "--path-format=absolute", "--git-dir") != str(admin.parent)
            or git(sibling, "rev-parse", "--path-format=absolute", "--git-common-dir") != str(common)):
        raise runtime.Refusal("metadata_role_unavailable")
    inventory = git(root / "fixture/main", "worktree", "list", "--porcelain", "-z")
    if sum(record.split("\0", 1)[0] == "worktree " + str(sibling) for record in inventory.split("\0\0")) != 1:
        raise runtime.Refusal("metadata_role_unavailable")
    return found


def _alias_admission(root: Path) -> list[dict]:
    runtime._metadata_snapshot(root / "fixture/task")
    checks = []
    for kind, reason in (("symlink", "fixture_alias"), ("hardlink", "unsafe_fixture_file")):
        directory = root / "input/alias-specimens" / kind
        path = directory / "alias"
        before = path.lstat()
        if (not directory.is_dir() or directory.resolve(strict=True) != directory
                or before.st_uid != os.getuid()
                or (kind == "symlink" and not stat.S_ISLNK(before.st_mode))
                or (kind == "hardlink" and (not stat.S_ISREG(before.st_mode) or before.st_nlink != 2))):
            raise runtime.Refusal("alias_specimen_unavailable")
        try:
            runtime._metadata_snapshot(directory)
        except runtime.Refusal as error:
            if str(error) != reason:
                raise runtime.Refusal("alias_specimen_unavailable") from None
        else:
            raise runtime.Refusal("alias_admission_failed")
        if path.lstat() != before:
            raise runtime.Refusal("protected_state_changed")
        checks.append({"operation": "admission_" + kind, "status": "passed", "refusal": reason})
    return checks


# This observer runs under the guest's existing rootless Podman user namespace.
# It only inspects the selected running processes, and opens existing transports
# without sending administrative messages or reading credential contents.
_UNSHARE_OBSERVER = r'''import hashlib,json,os,pathlib,socket,stat,sys
purpose = 'boundary_namespace_observation'
data=json.loads(sys.argv[1]);pid=data['pid'];supervisor=data['supervisor_pid']
def read(path,limit=65536):
    with open(path,'rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError()
    return raw
def ticks(p):return int(read('/proc/'+str(p)+'/stat').rsplit(b')',1)[1].split()[19])
def inode(path):
    info=os.lstat(path)
    return {'device':info.st_dev,'inode':info.st_ino}
def connect_unix(path):
    # Native volume paths can exceed sockaddr_un.sun_path. The single-threaded
    # observer connects by basename while holding and verifying its directory.
    path=pathlib.Path(path);parent=path.parent
    if not path.is_absolute() or parent.resolve(strict=True)!=parent:raise ValueError()
    info=os.lstat(path)
    if not stat.S_ISSOCK(info.st_mode):raise ValueError()
    def same_socket(other):
        return (stat.S_ISSOCK(other.st_mode) and
                (other.st_dev,other.st_ino,other.st_mode,other.st_uid,other.st_gid)==
                (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid))
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    original=os.open('.',flags)
    try:
        directory=os.open(parent,flags)
        try:
            held=os.fstat(directory);named=parent.lstat()
            if (held.st_dev,held.st_ino)!=(named.st_dev,named.st_ino):raise ValueError()
            if not same_socket(os.stat(path.name,dir_fd=directory,follow_symlinks=False)):raise ValueError()
            os.fchdir(directory)
            try:
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
                    stream.settimeout(2);stream.connect(path.name)
                if not same_socket(os.stat(path.name,dir_fd=directory,follow_symlinks=False)):raise ValueError()
                named=parent.lstat()
                if (held.st_dev,held.st_ino)!=(named.st_dev,named.st_ino):raise ValueError()
                return {'device':info.st_dev,'inode':info.st_ino}
            finally:os.fchdir(original)
        finally:os.close(directory)
    finally:os.close(original)
try:
    before=ticks(pid)
    binary=hashlib.sha256(read('/proc/'+str(pid)+'/exe',134217728)).hexdigest()
    namespace=os.readlink('/proc/'+str(pid)+'/ns/user')
    if namespace==data['host_namespace']:raise ValueError()
    control_base=pathlib.Path(data['control_source'])
    if control_base.resolve(strict=True)!=control_base:raise ValueError()
    candidates=[];pending=[(control_base,0)];seen=0
    while pending:
        parent,depth=pending.pop()
        for entry in parent.iterdir():
            seen+=1
            if seen>64:raise ValueError()
            info=entry.lstat()
            if stat.S_ISSOCK(info.st_mode):candidates.append(entry)
            elif stat.S_ISDIR(info.st_mode) and depth<2:pending.append((entry,depth+1))
            elif stat.S_ISLNK(info.st_mode):raise ValueError()
    if len(candidates)!=1:raise ValueError()
    control=candidates[0]
    control_value={'path':data['control_target']+'/'+control.relative_to(control_base).as_posix(),**connect_unix(str(control))}
    podman={'path':data['podman_path'],**connect_unix(data['podman_path'])}
    state=[]
    for name,path,p in [('bootstrap','/.openshell/channel/sandbox/bootstrap.json',pid),
                        ('supervisor_auth','/.openshell/supervisor/auth.json',supervisor)]:
        native='/proc/'+str(p)+'/root'+path
        try:
            info=os.lstat(native)
            if not stat.S_ISREG(info.st_mode):raise ValueError()
            fd=os.open(native,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK);os.close(fd)
            state.append({'name':name,'path':path,'present':True,**inode(native)})
        except FileNotFoundError:state.append({'name':name,'path':path,'present':False})
    if ticks(pid)!=before:raise ValueError()
    print(json.dumps({'runtime_binary_sha256':binary,'namespace':namespace,'runtime_start_ticks':before,
                      'control':control_value,'podman':podman,'state':state}))
except (OSError,ValueError,IndexError,KeyError,UnicodeError):
    print(json.dumps({'error':'native_boundary_unavailable'}))
'''


_NATIVE_OBSERVER = r'''import ipaddress,json,os,pathlib,re,socket,stat,subprocess,sys,tomllib
purpose = 'boundary_native_observation'
cid,sandbox,pid,home,uid,pins,inner=sys.argv[1:];pid=int(pid);uid=int(uid);gid=os.getgid();pins=json.loads(pins)
def read(path,limit=65536):
    with open(path,'rb') as stream:data=stream.read(limit+1)
    if len(data)>limit:raise ValueError()
    return data
def command(args,limit=1048576):
    result=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,timeout=10)
    if result.returncode or len(result.stdout)+len(result.stderr)>limit:raise ValueError()
    return result.stdout
def obj(args):return json.loads(command(args))
def inspect(identity):
    values=obj(['/usr/bin/podman','inspect','--type','container',identity])
    if len(values)!=1 or values[0]['Id']!=identity:raise ValueError()
    return values[0]
def fullid(value):return value if value.startswith('sha256:') else 'sha256:'+value
def mapping(kind,owner):
    rows=[list(map(int,line.split())) for line in read('/proc/'+str(pid)+'/'+kind+'_map',4096).splitlines()]
    if not rows or any(len(row)!=3 or row[0]<0 or row[1]<=0 or row[2]<=0 for row in rows):raise ValueError()
    if not any(a<=1000<a+n and b+(1000-a)==owner for a,b,n in rows):raise ValueError()
    return rows
try:
    if gid<=0:raise ValueError()
    info=obj(['/usr/bin/podman','info','--format','json'])
    if info['host']['security']['rootless'] is not True or info['host']['cgroupVersion']!='v2':raise ValueError()
    all_workloads=command(['/usr/bin/podman','ps','-a','--filter','label=openshell.ai/isolation-role=sandbox','--no-trunc','--format','{{.ID}}']).decode().split()
    if all_workloads!=[cid]:raise ValueError()
    selected=inspect(cid);labels=selected['Config']['Labels'];state=selected['State']
    if (labels.get('openshell.managed')!='true' or labels.get('openshell.ai/sandbox-id')!=sandbox
        or state.get('Running') is not True or state.get('Paused') is not False or state['Pid']!=pid
        or selected['HostConfig']['Privileged'] is not False):raise ValueError()
    supervisors=command(['/usr/bin/podman','ps','--filter','label=openshell.ai/isolation-role=supervisor',
        '--filter','label=openshell.ai/sandbox-id='+sandbox,'--no-trunc','--format','{{.ID}}']).decode().split()
    if len(supervisors)!=1 or re.fullmatch('[0-9a-f]{64}',supervisors[0]) is None:raise ValueError()
    supervisor=inspect(supervisors[0])
    if supervisor['HostConfig']['Privileged'] is not False or supervisor['State']['Running'] is not True:raise ValueError()
    images={}
    for name in ('sandbox_runtime','supervisor'):
        pin=pins[name];image=obj(['/usr/bin/podman','image','inspect',pin['repository']+'@'+pin['manifest_digest']])
        if len(image)!=1:raise ValueError()
        image=image[0]
        if (fullid(image['Id'])!=pin['config_digest'] or image.get('Digest')!=pin['manifest_digest']
            or image['Architecture']!='arm64' or image['Os']!='linux'):raise ValueError()
        images[name]={'id':fullid(image['Id']),'digest':image['Digest'],'architecture':image['Architecture'],'os':image['Os']}
    if fullid(supervisor['Image'])!=pins['supervisor']['config_digest']:raise ValueError()
    proc_status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in read('/proc/'+str(pid)+'/status').decode().splitlines() if ':' in line}
    if any(int(proc_status[key],16)!=0 for key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')) or proc_status['NoNewPrivs']!='1':raise ValueError()
    if any(int(value)!=uid for value in proc_status['Uid'].split()):raise ValueError()
    if any(int(value)!=gid for value in proc_status['Gid'].split()):raise ValueError()
    uid_map,gid_map=mapping('uid',uid),mapping('gid',gid)
    groups=read('/proc/'+str(pid)+'/cgroup',4096).decode().splitlines()
    if len(groups)!=1 or not groups[0].startswith('0::/') or '..' in groups[0].split('/'):raise ValueError()
    cgroup=pathlib.Path('/sys/fs/cgroup'+groups[0][3:]).resolve(strict=True)
    if not cgroup.is_relative_to('/sys/fs/cgroup'):raise ValueError()
    cpu=list(map(int,read(cgroup/'cpu.max',128).split()))
    resources={'cgroup':str(cgroup),'cpu_quota':cpu[0],'cpu_period':cpu[1],
               'memory_max':int(read(cgroup/'memory.max',128)),'pids_max':int(read(cgroup/'pids.max',128))}
    mounts=[value for value in selected['Mounts'] if value['Destination']=='/.openshell/channel/control']
    if len(mounts)!=1 or not mounts[0]['Source'].startswith('/'):raise ValueError()
    gateway_pid=int(command(['/usr/bin/systemctl','--user','show','openshell-gateway.service','--property=MainPID','--value'],128))
    if gateway_pid<=0:raise ValueError()
    gateway_start=int(read('/proc/'+str(gateway_pid)+'/stat').rsplit(b')',1)[1].split()[19])
    if os.stat('/proc/'+str(gateway_pid)).st_uid!=uid:raise ValueError()
    config=tomllib.loads(read(home+'/.config/openshell/gateway.toml').decode())
    address,port=config['openshell']['gateway']['bind_address'].rsplit(':',1);port=int(port)
    if str(ipaddress.IPv4Address(address))!=address or not ipaddress.IPv4Address(address).is_loopback or not 0<port<65536:raise ValueError()
    owned=set()
    for fd in pathlib.Path('/proc/'+str(gateway_pid)+'/fd').iterdir():
        try:link=os.readlink(fd)
        except FileNotFoundError:continue
        match=re.fullmatch(r'socket:\[([0-9]+)\]',link)
        if match:owned.add(int(match[1]))
    listening=[]
    for row in read('/proc/'+str(gateway_pid)+'/net/tcp').decode().splitlines()[1:]:
        fields=row.split();ip,p=fields[1].split(':')
        if fields[3]=='0A' and socket.inet_ntoa(bytes.fromhex(ip)[::-1])==address and int(p,16)==port and int(fields[9]) in owned:listening.append(int(fields[9]))
    if len(listening)!=1:raise ValueError()
    with socket.create_connection((address,port),timeout=2):pass
    args={'pid':pid,'supervisor_pid':supervisor['State']['Pid'],'host_namespace':os.readlink('/proc/self/ns/user'),
          'control_source':mounts[0]['Source'],'control_target':mounts[0]['Destination'],
          'podman_path':'/run/user/'+str(uid)+'/podman/podman.sock'}
    observed=obj(['/usr/bin/podman','unshare','/usr/bin/python3','-I','-B','-c',inner,json.dumps(args)])
    if 'error' in observed:raise ValueError()
    if inspect(cid)['State']['Pid']!=pid:raise ValueError()
    observed.update({'workload_image_id':fullid(selected['Image']),'uid_map':uid_map,'gid_map':gid_map,'resources':resources,
       'images':images,'rootless':info['host']['security']['rootless'],'privileged':selected['HostConfig']['Privileged'],
       'capabilities':{key:int(proc_status[key],16) for key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')},
       'no_new_privileges':proc_status['NoNewPrivs']=='1','uid':list(map(int,proc_status['Uid'].split())),
       'guest_gid':gid,'gid':list(map(int,proc_status['Gid'].split())),
       'gateway':{'address':address,'port':port,'pid':gateway_pid,'start_ticks':gateway_start,'inode':listening[0]}})
    print(json.dumps(observed,sort_keys=True))
except (OSError,ValueError,IndexError,KeyError,TypeError,UnicodeError,subprocess.SubprocessError):
    print(json.dumps({'error':'native_boundary_unavailable'}))
'''


def _validate_native_observation(value: dict, artifact: dict, uid: int) -> dict:
    if (set(value) != {"runtime_binary_sha256", "workload_image_id", "namespace", "runtime_start_ticks",
                      "uid_map", "gid_map", "gateway", "control", "podman", "state", "resources", "images",
                      "rootless", "privileged", "capabilities", "no_new_privileges", "uid", "guest_gid", "gid"}
            or value["runtime_binary_sha256"] != artifact["runtime_binary_sha256"]
            or value["workload_image_id"] != artifact["workload_image_id"]
            or not isinstance(value["namespace"], str)
            or re.fullmatch(r"user:\[[0-9]+\]", value["namespace"]) is None
            or type(value["runtime_start_ticks"]) is not int or value["runtime_start_ticks"] <= 0):
        raise runtime.Refusal("native_boundary_unavailable")
    capabilities = value["capabilities"]
    if (value["rootless"] is not True or value["privileged"] is not False or value["no_new_privileges"] is not True
            or not isinstance(value["uid"], list) or len(value["uid"]) != 4
            or any(type(item) is not int or item != uid for item in value["uid"])
            or type(value["guest_gid"]) is not int or value["guest_gid"] <= 0
            or not isinstance(value["gid"], list) or len(value["gid"]) != 4
            or any(type(item) is not int or item != value["guest_gid"] for item in value["gid"])
            or not isinstance(capabilities, dict) or set(capabilities) != {"CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"}
            or any(type(item) is not int or item != 0 for item in capabilities.values())):
        raise runtime.Refusal("native_boundary_unavailable")
    pins = runtime.decode_object(_VERSIONS.read_bytes())["images"]
    expected_images = {name: {"id": pins[name]["config_digest"], "digest": pins[name]["manifest_digest"],
                             "architecture": "arm64", "os": "linux"} for name in ("sandbox_runtime", "supervisor")}
    if value["images"] != expected_images:
        raise runtime.Refusal("native_boundary_unavailable")
    for name in ("uid_map", "gid_map"):
        rows = value[name]
        owner = uid if name == "uid_map" else value["guest_gid"]
        if (not isinstance(rows, list) or not 0 < len(rows) <= 16
                or any(not isinstance(row, list) or len(row) != 3 or any(type(x) is not int for x in row)
                       or row[0] < 0 or row[1] <= 0 or row[2] <= 0 for row in rows)
                or not any(a <= 1000 < a + n and b + 1000 - a == owner for a, b, n in rows)):
            raise runtime.Refusal("native_boundary_unavailable")
    gateway = value["gateway"]
    if (not isinstance(gateway, dict) or set(gateway) != {"address", "port", "pid", "start_ticks", "inode"}
            or gateway["address"] != "127.0.0.1" or gateway["port"] != 17670
            or any(type(gateway[key]) is not int or gateway[key] <= 0 for key in ("port", "pid", "start_ticks", "inode"))):
        raise runtime.Refusal("native_boundary_unavailable")
    for name in ("control", "podman"):
        surface = value[name]
        if (not isinstance(surface, dict) or set(surface) != {"path", "device", "inode"}
                or any(type(surface[key]) is not int or surface[key] < (1 if key == "inode" else 0)
                       for key in ("device", "inode")) or not isinstance(surface["path"], str)
                or str(PurePosixPath(surface["path"])) != surface["path"] or ".." in surface["path"].split("/")
                or (name == "control" and not surface["path"].startswith("/.openshell/channel/control/"))
                or (name == "podman" and surface["path"] != f"/run/user/{uid}/podman/podman.sock")):
            raise runtime.Refusal("native_boundary_unavailable")
    states = value["state"]
    expected_paths = {"bootstrap": "/.openshell/channel/sandbox/bootstrap.json",
                      "supervisor_auth": "/.openshell/supervisor/auth.json"}
    if not isinstance(states, list) or len(states) != 2:
        raise runtime.Refusal("native_boundary_unavailable")
    seen = set()
    for item in states:
        if (not isinstance(item, dict) or item.get("name") not in expected_paths
                or item["name"] in seen or item.get("path") != expected_paths[item["name"]]
                or type(item.get("present")) is not bool
                or set(item) != {"name", "path", "present"} | ({"device", "inode"} if item["present"] else set())):
            raise runtime.Refusal("native_boundary_unavailable")
        if item["present"] and any(type(item[key]) is not int or item[key] < (1 if key == "inode" else 0)
                                   for key in ("device", "inode")):
            raise runtime.Refusal("native_boundary_unavailable")
        seen.add(item["name"])
    resources = value["resources"]
    if (not isinstance(resources, dict) or set(resources) != {"cgroup", "cpu_quota", "cpu_period", "memory_max", "pids_max"}
            or not isinstance(resources["cgroup"], str) or not resources["cgroup"].startswith("/sys/fs/cgroup/")
            or ".." in resources["cgroup"].split("/")
            or any(type(resources[key]) is not int or resources[key] <= 0
                   for key in ("cpu_quota", "cpu_period", "memory_max", "pids_max"))
            or resources["cpu_quota"] > 2 * resources["cpu_period"]
            or resources["memory_max"] > 2147483648 or resources["pids_max"] > 256):
        raise runtime.Refusal("native_boundary_unavailable")
    return value


def _native_observation(controller, generation: tuple, artifact: dict, deadline: float) -> dict:
    pins = runtime.decode_object(_VERSIONS.read_bytes())["images"]
    value = runtime.decode_object(controller.guest([
        "/usr/bin/python3", "-I", "-B", "-c", _NATIVE_OBSERVER, generation[3], generation[0],
        str(generation[4]), controller.guest_home, str(controller.guest_uid), json.dumps(pins),
        _UNSHARE_OBSERVER], deadline).stdout)
    return _validate_native_observation(value, artifact, controller.guest_uid)


def _program(operation: str, target=None) -> str:
    return "operation = " + repr(operation) + "\ntarget = " + repr(target) + "\n" + r'''import errno,json,os,socket,urllib.error,urllib.request
result={'schema_version':1,'operation':operation,'outcome':'unavailable','errno':0}
phase='setup'
try:
    if operation=='startup_execution':
        with open('/proc/self/status') as stream:status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in stream if ':' in line}
        result={'schema_version':1,'operation':operation,'outcome':'executed','uid':os.getuid(),'gid':os.getgid(),
                'capabilities_zero':all(int(status[key],16)==0 for key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')),
                'no_new_privileges':status['NoNewPrivs']=='1','binary':os.readlink('/proc/self/exe')}
    elif operation.startswith('policy_'):
        method,path,body=('GET','/v1/policy/current',None) if operation=='policy_current' else ('POST','/v1/proposals',b'{}')
        request=urllib.request.Request('http://policy.local'+path,data=body,method=method,headers={'Content-Type':'application/json'})
        try:response=urllib.request.urlopen(request,timeout=3)
        except urllib.error.HTTPError as error:response=error
        with response:
            raw=response.read(4097)
            if len(raw)>4096:raise ValueError()
            value=json.loads(raw)
            result={'schema_version':1,'operation':operation,'outcome':'disabled','status':response.status,'error':value.get('error')}
    elif operation in ('parent_rename','parent_replace'):
        if not os.path.isdir('/work'):raise ValueError()
        if operation=='parent_rename':
            destination='/openshell-qualification-parent-replacement'
            if os.path.lexists(destination):raise ValueError()
            phase='target';os.rename('/work',destination)
        else:
            source='/scratch/.openshell-boundary-parent'
            os.mkdir(source,0o700)
            phase='target';os.replace(source,'/work')
        result.update(outcome='accessible')
    elif operation in ('gateway','podman','control'):
        family=socket.AF_INET if operation=='gateway' else socket.AF_UNIX
        with socket.socket(family,socket.SOCK_STREAM) as stream:
            stream.settimeout(3);phase='target';stream.connect(tuple(target) if operation=='gateway' else target)
        result.update(outcome='accessible')
    else:
        flags=os.O_RDONLY if operation.startswith('state_') else os.O_WRONLY
        phase='target';fd=os.open(target,flags|os.O_NOFOLLOW|os.O_NONBLOCK);os.close(fd)
        result.update(outcome='accessible')
except OSError as error:
    result.update(outcome='denied' if phase=='target' else 'unavailable',errno=error.errno or 0)
except (ValueError,KeyError,TypeError,urllib.error.URLError):pass
print(json.dumps(result,sort_keys=True))
'''


def _execute(controller, operation: str, target, deadline: float) -> dict:
    result = controller.guest(["/usr/bin/openshell", "sandbox", "exec", "--name", controller.sandbox_name,
                               "--workdir", "/work", "--no-tty", "--no-login-shell", "--timeout", "50", "--",
                               "/usr/local/bin/python3.13", "-I", "-B", "-c", _program(operation, target)], deadline)
    if len(result.stdout) > 4096:
        raise runtime.Refusal("invalid_probe_output")
    return runtime.decode_object(result.stdout)


def _validate_result(value: dict, operation: str) -> None:
    if value.get("outcome") == "accessible":
        raise runtime.Refusal("boundary_accessible")
    if operation == "startup_execution":
        expected = {"schema_version": 1, "operation": operation, "outcome": "executed", "uid": 1000, "gid": 1000,
                    "capabilities_zero": True, "no_new_privileges": True, "binary": "/usr/local/bin/python3.13"}
        if json.dumps(value, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise runtime.Refusal("startup_execution_unavailable")
        return
    if operation.startswith("policy_"):
        if (value != {"schema_version": 1, "operation": operation, "outcome": "disabled", "status": 404,
                      "error": "feature_disabled"} or type(value.get("schema_version")) is not int
                or type(value.get("status")) is not int):
            raise runtime.Refusal("policy_disabled_unavailable")
        return
    # These observations originate on Linux aarch64, independently of the
    # controller host's errno table (macOS uses different connection numbers).
    allowed = {1, 2, 13, 30}  # EPERM, ENOENT, EACCES, EROFS
    if operation.startswith("parent_"):
        allowed = {1, 13, 16, 18, 30}  # EPERM, EACCES, EBUSY, EXDEV, EROFS
    elif operation in ("gateway", "podman", "control"):
        allowed = {1, 2, 13, 101, 111}  # EPERM, ENOENT, EACCES, ENETUNREACH, ECONNREFUSED
    if (set(value) != {"schema_version", "operation", "outcome", "errno"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["operation"] != operation or value["outcome"] != "denied"
            or type(value["errno"]) is not int or value["errno"] not in allowed):
        raise runtime.Refusal("boundary_denial_unavailable")


def protected_boundaries_probe(selection: runtime.Selection) -> dict:
    report = {"schema_version": 1, "probe": "boundaries", "status": "unavailable", "reason": None,
              "runtime_qualification": "not_run", "checks": [], "retained": False,
              "generation_sha256": None, "truncation": {"transport_output": False, "limit_bytes": None},
              "startup_attestation": {"kind": "source_backed_inference", "status": "not_run",
                                      "unexported_audit_fields": "unobserved"}}
    admitted = False
    try:
        runtime.validate_root(selection)
        admitted = True
        deadline = runtime._prepared_deadline(selection.root)
        generation, report["generation_sha256"] = runtime._validate_generation(selection.root)
        guard = runtime._validate_guard(selection.root)
        targets, artifact = _receipts(selection.root)
        runtime._check_pointer_evidence(selection.root, 256 * 1024, 32)
        controller = runtime._PointerController(selection, deadline)
        common, pointer = runtime._host_git_fixture(selection.root, controller.env, deadline)
        _host_targets(selection.root, common, targets, controller.env, min(deadline, time.monotonic() + 60))
        report["checks"].extend(_alias_admission(selection.root))
        protected = runtime._metadata_snapshot(common)
        task = selection.root / "fixture/task"
        task_identity = task.lstat()
        if not stat.S_ISDIR(task_identity.st_mode) or task.resolve(strict=True) != task:
            raise runtime.Refusal("fixture_membership")
        native = None

        def unchanged(step):
            try:
                runtime.validate_root(selection)
                current = task.lstat()
                if (runtime._guard_snapshot(pointer) != guard or runtime._metadata_snapshot(common) != protected
                        or (current.st_dev, current.st_ino, current.st_mode, current.st_uid)
                        != (task_identity.st_dev, task_identity.st_ino, task_identity.st_mode, task_identity.st_uid)):
                    raise runtime.Refusal("protected_state_changed")
                runtime._host_git_fixture(selection.root, controller.env, step)
                _host_targets(selection.root, common, targets, controller.env, step)
            except (OSError, runtime.Refusal):
                raise runtime.Refusal("protected_state_changed") from None

        def checked(operation, target=None):
            nonlocal native
            step = min(deadline, time.monotonic() + 60)
            runtime._remaining(step)
            unchanged(step)
            if controller.identity(step) != generation:
                raise runtime.Refusal("sandbox_identity")
            observation = _native_observation(controller, generation, artifact, step)
            if native is None:
                native = observation
                report["native_observation"] = observation
            elif observation != native:
                raise runtime.Refusal("native_boundary_identity")
            try:
                value = _execute(controller, operation, target, step)
                _validate_result(value, operation)
            except runtime.Refusal as error:
                runtime._record_truncation(report, error)
                raise
            finally:
                host_error = None
                try:
                    unchanged(step)
                except runtime.Refusal as error:
                    host_error = error
                try:
                    if controller.identity(step) != generation:
                        raise runtime.Refusal("sandbox_identity")
                    if _native_observation(controller, generation, artifact, step) != native:
                        raise runtime.Refusal("native_boundary_identity")
                finally:
                    if host_error is not None:
                        raise host_error
            report["checks"].append({"operation": operation, "status": "passed"})
            runtime._write_pointer_evidence(selection.root, report)

        checked("startup_execution")
        report["startup_attestation"].update(status="passed", runtime_binary_sha256=artifact["runtime_binary_sha256"],
                                             workload_image_id=artifact["workload_image_id"])
        for name in _TARGETS:
            checked("metadata_" + name, str(common / targets[name]))
        for operation in ("parent_rename", "parent_replace"):
            checked(operation)
        checked("gateway", [native["gateway"]["address"], native["gateway"]["port"]])
        for operation in ("podman", "control"):
            checked(operation, native[operation]["path"])
        for operation in ("policy_current", "policy_proposals"):
            checked(operation)
        for item in native["state"]:
            if item["present"]:
                checked("state_" + item["name"], item["path"])
            else:
                report["checks"].append({"operation": "state_" + item["name"], "status": "unavailable", "reason": "absent"})
        report["status"] = "passed"
    except runtime.Refusal as error:
        report["reason"] = str(error)
        runtime._record_truncation(report, error)
        if str(error) in {"protected_state_changed", "boundary_accessible", "alias_admission_failed"}:
            report["status"] = "failed"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        report["reason"] = "boundary_observation_unavailable"
    if admitted:
        try:
            report["retained"] = True
            runtime._write_pointer_evidence(selection.root, report)
        except (OSError, runtime.Refusal):
            report["retained"] = False
            if report["status"] != "failed":
                report["status"], report["reason"] = "unavailable", "evidence_retention_failed"
    return report
