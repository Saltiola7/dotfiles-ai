"""Fixed credential-free cases, appended to the existing bounded guest harness.

Neither payload data nor output selects a command, path, environment or PID.
Successful observations never authorize a normal agent session or activation.
"""
import ctypes
import errno
import fcntl
import re
import sys
from contextlib import contextmanager


AGENT_PROBES=('codex-version','codex-help','codex-empty-login','codex-stdio',
              'opencode-version','opencode-help','opencode-rg')
AGENT_MODES=('unfiltered','upstream','patched')
AGENT_CASES=tuple(probe+'-'+mode for probe in AGENT_PROBES for mode in AGENT_MODES)
AGENT_DIRS=('home','codex','config','config/opencode','data','state','cache','tmp',
            'workspace','logs','cargo','rustup','target')
AGENT_CODEX_CONFIG=b'''cli_auth_credentials_store = "file"
check_for_update_on_startup = false
[analytics]
enabled = false
[feedback]
enabled = false
[otel]
exporter = "none"
trace_exporter = "none"
metrics_exporter = "none"
'''
AGENT_GITIGNORE=b'node_modules\npackage.json\npackage-lock.json\nbun.lock\n.gitignore\n'
AGENT_SENTINEL=b'openshell optional agent comparison\n'
AGENT_INITIALIZE=(json.dumps({'id':1,'method':'initialize','params':{
    'clientInfo':{'name':'dotfiles_ai_openshell_probe','title':'dotfiles-ai OpenShell probe','version':'1'},
    'capabilities':{'explicitGatewayOauth':True,'experimentalApi':False,'requestAttestation':False}}},
    separators=(',',':'))+'\n').encode()
AGENT_INITIALIZED=b'{"method":"initialized"}\n'
AGENT_FLAGS={'session_enabled':False,'full_runtime_qualified':False,'compatibility_qualified':False}
AGENT_STATE_LIMIT=128*1024**2
AGENT_RESERVE=256*1024**2
AGENT_RECORD=struct.Struct('<4sBBH6i')

# Only this fresh child owns FD3. Error exit bypasses Python cleanup after dup2.
AGENT_BOOTSTRAP=r"""
import fcntl, os, stat, sys
try:
    if len(sys.argv)!=5:raise ValueError()
    writer,fixture=int(sys.argv[1]),int(sys.argv[2]);probe,mode=sys.argv[3:]
    if writer<3 or fixture<=3 or writer==fixture:raise ValueError()
    if probe not in ('codex-version','codex-help','codex-empty-login','codex-stdio',
                     'opencode-version','opencode-help','opencode-rg'):raise ValueError()
    if mode not in ('unfiltered','upstream','patched'):raise ValueError()
    pipe=os.fstat(writer);binary=os.fstat(fixture)
    if not stat.S_ISFIFO(pipe.st_mode) or fcntl.fcntl(writer,fcntl.F_GETFL)&os.O_ACCMODE!=os.O_WRONLY:
        raise ValueError()
    if not stat.S_ISREG(binary.st_mode) or not binary.st_mode&stat.S_IXUSR or binary.st_size<=0:
        raise ValueError()
    os.dup2(writer,3,inheritable=True);os.set_inheritable(3,True)
    if writer!=3:os.close(writer)
    os.execve('/proc/self/fd/'+str(fixture),['openshell-agent-filter-probe',probe,mode],os.environ)
except BaseException:
    os._exit(125)
"""


def agent_platform():
    if sys.platform!='linux' or os.uname().machine!='aarch64' or os.getuid()!=65534 or os.getgid()!=65534:
        raise RuntimeError('agent_platform')


def agent_selection(case):
    if type(case) is not str or case not in AGENT_CASES:raise RuntimeError('agent_case_selection')
    return case.rsplit('-',1)


def agent_capacity():
    remaining()
    info=os.statvfs(WORK)
    if info.f_bavail*info.f_frsize<AGENT_RESERVE:raise RuntimeError('agent_capacity')


def agent_metadata(path, *, directory=False, links=1):
    path=Path(path)
    try:parts=path.relative_to(WORK).parts
    except ValueError:raise RuntimeError('agent_path') from None
    root=WORK.lstat();current=WORK
    for index,part in enumerate(parts):
        if part in ('','.','..'):raise RuntimeError('agent_path')
        current/=part;info=current.lstat()
        is_directory=directory or index<len(parts)-1
        if (info.st_dev!=root.st_dev or info.st_uid!=os.getuid() or info.st_gid!=os.getgid()
                or info.st_mode&0o022 or not (stat.S_ISDIR(info.st_mode) if is_directory else stat.S_ISREG(info.st_mode))
                or (not is_directory and info.st_nlink!=links)):
            raise RuntimeError('agent_path_identity')
    return info if parts else root


def agent_initial(case):
    probe,_=agent_selection(case)
    files={'codex/config.toml':AGENT_CODEX_CONFIG,'config/opencode/.gitignore':AGENT_GITIGNORE}
    if probe=='opencode-rg':files['workspace/sentinel.txt']=AGENT_SENTINEL
    return files


def agent_state_bytes():
    """Bound metadata traversal and allocation without reading agent-created data."""
    root=WORK/'agent-cases-1';device=WORK.stat().st_dev
    pending=[(root,0)];total=0;count=0
    while pending:
        path,depth=pending.pop();remaining()
        info=path.lstat();count+=1
        if count>20000 or depth>32 or info.st_dev!=device:raise RuntimeError('agent_state_bound')
        total+=max(info.st_size,info.st_blocks*512)
        if total>AGENT_STATE_LIMIT:raise RuntimeError('agent_state_bound')
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as entries:
                for entry in entries:
                    if len(pending)+count>20000:raise RuntimeError('agent_state_bound')
                    pending.append((Path(entry.path),depth+1))
    return total


def agent_cases_prepare(payload):
    agent_platform();agent_capacity()
    root=WORK/'agent-cases-1'
    if os.path.lexists(root):raise RuntimeError('agent_cases_retained')
    root.mkdir(mode=0o700)
    for case in AGENT_CASES:
        agent_capacity();base=root/case;base.mkdir(mode=0o700)
        for name in AGENT_DIRS:(base/name).mkdir(mode=0o700)
        for name,data in agent_initial(case).items():
            fd=os.open(base/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(data)
        agent_fresh_case(case)
    return {'schema_version':1,'generation':1,'status':'agent_cases_prepared','cases':list(AGENT_CASES),
            'initial_sha256':{'codex_config':hashlib.sha256(AGENT_CODEX_CONFIG).hexdigest(),
                'opencode_gitignore':hashlib.sha256(AGENT_GITIGNORE).hexdigest(),
                'sentinel':hashlib.sha256(AGENT_SENTINEL).hexdigest()},
            'case_state_bytes':agent_state_bytes(),**AGENT_FLAGS}


def agent_fresh_case(case):
    agent_selection(case);base=WORK/'agent-cases-1'/case;files=agent_initial(case)
    try:
        for path in (WORK/'agent-cases-1',base,*(base/name for name in AGENT_DIRS)):
            if stat.S_IMODE(agent_metadata(path,directory=True).st_mode)!=0o700:
                raise RuntimeError('agent_case_freshness')
        observed=set();pending=[base]
        while pending:
            parent=pending.pop()
            with os.scandir(parent) as entries:
                for entry in entries:
                    path=Path(entry.path);name=str(path.relative_to(base));observed.add(name)
                    if len(observed)>len(AGENT_DIRS)+len(files):raise RuntimeError('agent_case_freshness')
                    if name in AGENT_DIRS:pending.append(path)
                    elif name in files:
                        info=agent_metadata(path)
                        if info.st_size!=len(files[name]) or stat.S_IMODE(info.st_mode)!=0o600:
                            raise RuntimeError('agent_case_freshness')
                        with path.open('rb') as stream:
                            if stream.read(len(files[name])+1)!=files[name]:raise RuntimeError('agent_case_freshness')
                    else:raise RuntimeError('agent_case_freshness')
        if observed!=set(AGENT_DIRS)|set(files):raise RuntimeError('agent_case_freshness')
    except (OSError,RuntimeError) as error:
        raise RuntimeError('agent_case_freshness') from error
    return base


def agent_case_view(case):
    """Prove nested mount policy and temp aliases before any agent execution."""
    base=agent_fresh_case(case);temp=base/'tmp';expected=temp.stat()
    for alias in (Path('/tmp'),Path('/var/tmp')):
        info=alias.stat()
        if (info.st_dev,info.st_ino)!=(expected.st_dev,expected.st_ino):raise RuntimeError('agent_temp_alias')
    readonly=[WORK,WORK/'agent-assets-1',WORK/'full-source-2',WORK/'full-cargo-1',WORK/'full-target-1',base/'config']
    readonly.extend(WORK/'agent-cases-1'/other for other in AGENT_CASES if other!=case)
    for directory in readonly:
        agent_metadata(directory,directory=True)
        if not os.statvfs(directory).f_flag&os.ST_RDONLY:raise RuntimeError('agent_readonly_view')
        probe=directory/'.openshell-agent-write-probe'
        try:fd=os.open(probe,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        except OSError as error:
            if error.errno not in (errno.EROFS,errno.EACCES,errno.EPERM):raise RuntimeError('agent_readonly_view') from error
        else:
            os.close(fd);probe.unlink();raise RuntimeError('agent_readonly_view')
    for directory in (base,Path('/tmp'),Path('/var/tmp')):
        if os.statvfs(directory).f_flag&os.ST_RDONLY:raise RuntimeError('agent_writable_view')
        probe=directory/'.openshell-agent-write-probe'
        fd=os.open(probe,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:os.write(fd,b'case-only')
        finally:os.close(fd);probe.unlink()
    return base



def agent_descriptor_snapshot():
    """Observe fixed descriptor metadata without opening or reading a file."""
    records=[]
    for fd in range(4):
        remaining()
        try:
            info=os.fstat(fd)
            fd_flags=fcntl.fcntl(fd,fcntl.F_GETFD)
            status_flags=fcntl.fcntl(fd,fcntl.F_GETFL)
        except OSError as error:
            if error.errno!=errno.EBADF:raise RuntimeError('agent_descriptor_metadata') from error
            records.append({'fd':fd,'errno':errno.EBADF,'mode':None,'rdev':None,
                            'fd_flags':None,'status_flags':None})
        else:
            records.append({'fd':fd,'errno':0,'mode':info.st_mode,'rdev':info.st_rdev,
                            'fd_flags':fd_flags,'status_flags':status_flags})
    return records


def agent_descriptor_inspect():
    """Diagnose reservation only; never repair a descriptor or execute an agent."""
    before=agent_descriptor_snapshot()
    agent_platform();agent_capacity();agent_case_view('codex-version-unfiltered')
    validated=agent_descriptor_snapshot()
    remaining()
    try:
        reserved=os.open('/dev/null',os.O_RDONLY|os.O_CLOEXEC)
        try:
            remaining();info=os.fstat(reserved)
            if not stat.S_ISCHR(info.st_mode) or (os.major(info.st_rdev),os.minor(info.st_rdev))!=(1,3):
                raise RuntimeError('agent_descriptor_null')
        finally:os.close(reserved)
    except OSError as error:
        raise RuntimeError('agent_descriptor_reservation') from error
    after=agent_descriptor_snapshot()
    return {'schema_version':1,'generation':1,'status':'agent_descriptors_observed',
            'before':before,'after_validation':validated,'after_close':after,
            'reserved_fd':reserved,'reserved_null':True,**AGENT_FLAGS}


def agent_nondumpable():
    libc=ctypes.CDLL(None,use_errno=True)
    prctl=libc.prctl
    prctl.argtypes=[ctypes.c_int,*([ctypes.c_ulong]*4)];prctl.restype=ctypes.c_int
    if prctl(4,0,0,0,0)!=0 or prctl(3,0,0,0,0)!=0:raise RuntimeError('agent_parent_dumpable')


def agent_json(raw):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('duplicate key')
            value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))


class AgentProtocol:
    def __init__(self,codex_home):
        self.codex_home=codex_home;self.buffer=bytearray();self.initialized=False;self.result=None

    def feed(self,chunk):
        previous=self.initialized;self.buffer.extend(chunk)
        while b'\n' in self.buffer:
            raw,_,tail=self.buffer.partition(b'\n');self.buffer=bytearray(tail)
            if len(raw)>65536:raise RuntimeError('agent_protocol_line')
            try:value=agent_json(raw)
            except (ValueError,UnicodeError):raise RuntimeError('agent_protocol_json') from None
            if type(value) is not dict:raise RuntimeError('agent_protocol_shape')
            if 'id' in value:
                if (set(value)!={'id','result'} or type(value['id']) is not int or value['id']!=1
                        or self.initialized or type(value['result']) is not dict):
                    raise RuntimeError('agent_protocol_response')
                result=value['result']
                if (set(result)!={'userAgent','codexHome','platformFamily','platformOs'}
                        or type(result['userAgent']) is not str or not 0<len(result['userAgent'].encode())<=1024
                        or result['codexHome']!=self.codex_home or result['platformFamily']!='unix'
                        or result['platformOs']!='linux'):
                    raise RuntimeError('agent_protocol_identity')
                self.initialized=True
                self.result=result
            elif (not set(value)<={'method','params'} or type(value.get('method')) is not str
                    or not value['method'] or len(value['method'])>256):
                raise RuntimeError('agent_protocol_notification')
        if len(self.buffer)>65536:raise RuntimeError('agent_protocol_line')
        return self.initialized and not previous

    def finish(self):
        if self.buffer:raise RuntimeError('agent_protocol_truncated')


def agent_proof(raw,mode,parent_pid):
    if type(raw) is not bytes or len(raw)>4096 or not raw or len(raw)%32:
        raise RuntimeError('agent_proof_length')
    records=[];selected=AGENT_MODES.index(mode)
    for offset in range(0,len(raw),32):
        magic,event,observed,reserved,*values=AGENT_RECORD.unpack_from(raw,offset)
        if magic!=b'OAC1' or observed!=selected or reserved or event not in (1,2,3,4,5,6):
            raise RuntimeError('agent_proof_record')
        records.append([event,*values])
    events=[row[0] for row in records];success=[1,2,6,3,4,5]
    if events!=success and events not in ([1,2,4],[1,2,6,3,4]):
        raise RuntimeError('agent_proof_order')
    prepared=records[0][1:]
    if (prepared[0]!=parent_pid or parent_pid<=0 or prepared[2:4]!=[1,0]
            or prepared[4]<=0 or prepared[5]!=0
            or (prepared[1]!=0 if selected==0 else not 1<=prepared[1]<=4096)):
        raise RuntimeError('agent_proof_parent')
    installed=records[1][1:]
    if (installed[1]<=0 or installed[1]==parent_pid or installed[2:]!=[int(selected!=0),0,0,0]
            or not 0<=installed[0]<=4095):
        raise RuntimeError('agent_proof_install')
    by_event={row[0]:row[1:] for row in records}
    if 6 in by_event:
        guard=by_event[6]
        if guard[0] not in (errno.EACCES,errno.EPERM) or guard[1:]!=[1,7,1,0,0]:
            raise RuntimeError('agent_proof_descriptor')
    if 3 in by_event and by_event[3]!=[errno.EPERM if selected==2 else 0]*2+[0,0,0,0]:
        raise RuntimeError('agent_proof_kernel')
    spawn=by_event[4]
    if spawn[2:]!=[0,0,0,0] or not 0<=spawn[0]<=4095:raise RuntimeError('agent_proof_exec')
    if events!=success:
        if spawn[0]==0 or spawn[1]!=0:raise RuntimeError('agent_proof_exec')
        if (events==[1,2,4] and (installed[0]==0 or spawn[0]!=installed[0])):
            raise RuntimeError('agent_proof_install')
        if events==[1,2,6,3,4] and installed[0]!=0:raise RuntimeError('agent_proof_install')
        observation='filter_install_error' if installed[0] else 'launch_error'
        return {'records':records,'exit_code':None,'signal':None,'observation':observation}
    if installed[0] or spawn[:2]!=[0,installed[1]]:raise RuntimeError('agent_proof_exec')
    code,signal_number,core,*reserved=by_event[5]
    if (reserved!=[0,0,0] or core not in (0,1)
            or not ((0<=code<=255 and signal_number==0 and core==0) or (code==-1 and 1<=signal_number<=64))):
        raise RuntimeError('agent_proof_wait')
    return {'records':records,'exit_code':code if signal_number==0 else None,
            'signal':signal_number or None,'observation':'exited'}


def agent_expectation(probe,code,signal_number,output,error,initialized):
    if signal_number is not None:return False
    if probe=='codex-empty-login':return code==1 and output==b'' and error.strip()==b'Not logged in'
    if code!=0:return False
    if probe=='codex-version':return output.strip()==b'codex-cli 0.164.0'
    if probe=='opencode-version':return output.strip()==b'1.18.25'
    if probe=='opencode-rg':return output==b'sentinel.txt\n'
    if probe=='codex-stdio':return initialized
    if probe in ('codex-help','opencode-help'):return bool(output.strip())
    raise RuntimeError('agent_case_selection')


@contextmanager
def agent_proof_pipe():
    """Own anonymous pipe ends; never reserve or replace the parent's FD3."""
    reader=writer=None
    def release():
        nonlocal writer
        if writer is not None:os.close(writer);writer=None
    try:
        remaining();reader,writer=os.pipe2(os.O_CLOEXEC)
        if reader<3 or writer<3 or reader==writer:raise RuntimeError('agent_launch_descriptors')
        yield reader,writer,release
    finally:
        for fd in (writer,reader):
            if fd is not None:
                try:os.close(fd)
                except OSError as error:
                    if error.errno!=errno.EBADF:raise


def agent_file_digest(fd):
    value=hashlib.sha256();os.lseek(fd,0,os.SEEK_SET)
    while True:
        remaining();chunk=os.read(fd,1024*1024)
        if not chunk:break
        value.update(chunk)
    return value.hexdigest()


@contextmanager
def agent_binary(path,expected,*,links=1):
    info=agent_metadata(path,links=links)
    if (not info.st_mode&0o100 or not 0<info.st_size<=1024**3 or type(expected) is not dict
            or info.st_size!=expected.get('bytes') or stat.S_IMODE(info.st_mode)!=expected.get('mode')
            or type(expected.get('sha256')) is not str):
        raise RuntimeError('agent_binary_identity')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    def identity(item):return (item.st_dev,item.st_ino,item.st_mode,item.st_uid,item.st_gid,item.st_nlink,
                               item.st_size,item.st_mtime_ns,item.st_ctime_ns)
    try:
        if identity(os.fstat(fd))!=identity(info) or agent_file_digest(fd)!=expected['sha256']:
            raise RuntimeError('agent_binary_identity')
        yield fd
        if identity(os.fstat(fd))!=identity(info) or identity(Path(path).lstat())!=identity(info):
            raise RuntimeError('agent_binary_changed')
    finally:os.close(fd)


def agent_environment(base):
    env={'PATH':'/usr/bin:/bin','LC_ALL':'C','LANG':'C','TERM':'dumb','NO_COLOR':'1'}
    for key,directory in (('HOME','home'),('CODEX_HOME','codex'),('XDG_CONFIG_HOME','config'),
            ('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state'),('XDG_CACHE_HOME','cache'),
            ('TMPDIR','tmp'),('CARGO_HOME','cargo'),('RUSTUP_HOME','rustup'),('CARGO_TARGET_DIR','target')):
        env[key]=str(base/directory)
    return env


def agent_tail(raw):
    return bytes(raw[-8192:]).decode(errors='replace').encode()[-8192:].decode(errors='ignore')


def agent_observe(fixture_fd,case,channel):
    reader,writer,release_writer=channel
    if (any(type(fd) is not int or fd<3 for fd in (reader,writer,fixture_fd))
            or fixture_fd==3 or len({reader,writer,fixture_fd})!=3):
        raise RuntimeError('agent_launch_descriptors')
    probe,mode=agent_selection(case);base=WORK/'agent-cases-1'/case
    protocol=AgentProtocol(str(base/'codex')) if probe=='codex-stdio' else None
    end=time.monotonic()+remaining(60 if protocol else 30)
    initialize_end=min(end,time.monotonic()+10)
    process=None;output=bytearray();error=bytearray();proof=bytearray();reason='exited'
    input_bytes=0;terminated=False;proof_result=None
    try:
        process=subprocess.Popen(['/usr/bin/python3','-I','-c',AGENT_BOOTSTRAP,str(writer),str(fixture_fd),probe,mode],
            cwd=base/'workspace',env=agent_environment(base),
            stdin=subprocess.PIPE if protocol else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            close_fds=True,pass_fds=(writer,fixture_fd),start_new_session=True)
        release_writer()
        pending=bytearray(AGENT_INITIALIZE if protocol else b'')
        with selectors.DefaultSelector() as selector:
            for stream,label in ((process.stdout,'stdout'),(process.stderr,'stderr'),(reader,'proof')):
                selector.register(stream,selectors.EVENT_READ,label)
            if protocol:
                os.set_blocking(process.stdin.fileno(),False)
                selector.register(process.stdin,selectors.EVENT_WRITE,'stdin')
            while selector.get_map():
                remaining();wait=min(end-time.monotonic(),1.0)
                if protocol and not protocol.initialized and process.poll() is None:
                    wait=min(wait,initialize_end-time.monotonic())
                if wait<=0:reason='timeout';break
                for key,_ in selector.select(wait):
                    if key.data=='stdin':
                        try:written=os.write(key.fd,pending)
                        except BrokenPipeError:
                            selector.unregister(key.fileobj);key.fileobj.close();continue
                        except BlockingIOError:continue
                        input_bytes+=written;del pending[:written]
                        if input_bytes>1024:raise RuntimeError('agent_stdin_bound')
                        if not pending:
                            selector.unregister(key.fileobj)
                            if protocol.initialized:key.fileobj.close()
                        continue
                    limit=4096 if key.data=='proof' else OUTPUT_LIMIT
                    current=len(proof) if key.data=='proof' else len(output)+len(error)
                    chunk=os.read(key.fd,min(65536,limit+1-current))
                    if not chunk:
                        selector.unregister(key.fileobj);continue
                    destination={'stdout':output,'stderr':error,'proof':proof}[key.data]
                    destination.extend(chunk[:max(0,limit-current)])
                    if len(chunk)>limit-current:
                        reason='proof_error' if key.data=='proof' else 'output_limit';break
                    if len(proof)>4096:reason='proof_error';break
                    if len(output)+len(error)>OUTPUT_LIMIT:reason='output_limit';break
                    if key.data=='stdout' and protocol:
                        try:ready=protocol.feed(chunk)
                        except RuntimeError:reason='protocol_error';break
                        if ready and process.stdin is not None and not process.stdin.closed:
                            pending.extend(AGENT_INITIALIZED)
                            selector.register(process.stdin,selectors.EVENT_WRITE,'stdin')
                if reason!='exited':break
            if reason=='exited':
                try:process.wait(timeout=max(.001,min(remaining(),end-time.monotonic())))
                except subprocess.TimeoutExpired:reason='timeout'
                if protocol:
                    try:protocol.finish()
                    except RuntimeError:reason='protocol_error'
    finally:
        if process is not None:
            if process.stdin is not None and not process.stdin.closed:process.stdin.close()
            # Check/kill the whole initial process group even if its leader
            # already exited. Root's unit/cgroup stop covers escaped groups.
            try:os.killpg(process.pid,0)
            except ProcessLookupError:pass
            else:
                terminated=True
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            if process.poll() is None:process.wait(timeout=2)
            process.stdout.close();process.stderr.close()
    if process is None:raise RuntimeError('agent_fixture_launch')
    try:proof_result=agent_proof(bytes(proof),mode,process.pid)
    except RuntimeError:
        if reason=='exited':reason='proof_error'
        proof_result={'records':[],'exit_code':None,'signal':None,'observation':'proof_error'}
    if reason=='exited':
        reason=proof_result['observation']
        if process.returncode!=0:reason='proof_error'
    return {'proof_records':proof_result['records'],'observation':reason,
            'exit_code':proof_result['exit_code'],'signal':proof_result['signal'],
            'wrapper_returncode':process.returncode,'termination_requested':terminated,
            'expectation_met':reason=='exited' and not terminated and agent_expectation(probe,
                proof_result['exit_code'],proof_result['signal'],bytes(output),bytes(error),bool(protocol and protocol.initialized))
                and (not protocol or input_bytes==len(AGENT_INITIALIZE)+len(AGENT_INITIALIZED)),
            'initialized':bool(protocol and protocol.initialized),'initialize_result':protocol.result if protocol else None,
            'stdin_bytes':input_bytes,
            'stdout_bytes':len(output),'stderr_bytes':len(error),
            'stdout_tail':agent_tail(output),'stderr_tail':agent_tail(error)}


def agent_case(payload,case):
    probe,mode=agent_selection(case);agent_platform();agent_capacity();agent_case_view(case)
    agent_nondumpable()
    built=payload['agent_build_report'];assets=payload['agent_assets_report']
    if (built.get('status') not in ('agent_fixture_built','agent_fixture_verified') or built.get('static_arm64') is not True
            or assets.get('status')!='agent_assets_verified'
            or any(report.get('schema_version')!=1 or report.get('generation')!=1 for report in (built,assets))
            or any(report.get(key) is not False for report in (built,assets) for key in AGENT_FLAGS)):
        raise RuntimeError('agent_prior_proof')
    layout=built.get('binary_layout')
    if (type(layout) is not dict or set(layout)!={'link_count','companion'}
            or type(layout['link_count']) is not int or layout['link_count'] not in (1,2)
            or (layout['link_count']==1 and layout['companion'] is not None)
            or (layout['link_count']==2 and (type(layout['companion']) is not str
                or re.fullmatch('openshell_agent_filter_probe-[0-9a-f]{16}',layout['companion']) is None))):
        raise RuntimeError('agent_fixture_layout')
    fixture_expected={'bytes':built['binary_bytes'],'sha256':built['binary_sha256']}
    agent='codex' if probe.startswith('codex-') else 'opencode'
    relative='bin/codex' if agent=='codex' else 'opencode'
    executable=assets['assets'][agent]['files'][relative]
    rg=assets['assets']['codex']['files']['codex-path/rg']
    with agent_proof_pipe() as channel:
        with full_cargo_runtime_artifact('agent-probe') as (fixture_fd,observed_layout):
            if (observed_layout!=layout or os.fstat(fixture_fd).st_size!=fixture_expected['bytes']
                    or full_cargo_runtime_digest(fixture_fd,'agent-probe')!=fixture_expected['sha256']):
                raise RuntimeError('agent_fixture_identity')
            with agent_binary(WORK/'agent-assets-1'/agent/relative,executable):
                with agent_binary(WORK/'agent-assets-1/codex/codex-path/rg',rg):
                    result=agent_observe(fixture_fd,case,channel)
    agent_capacity();state=agent_state_bytes()
    return {'schema_version':1,'generation':1,'status':'agent_case_observed','case':case,'probe':probe,'mode':mode,
            'fixture_binary_sha256':built['binary_sha256'],'executable_sha256':executable['sha256'],
            'rg_sha256':rg['sha256'],'case_state_bytes':state,'python_nondumpable':True,
            **result,**AGENT_FLAGS}
