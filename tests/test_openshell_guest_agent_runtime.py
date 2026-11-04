"""Closed agent probes retain negative observations without granting activation."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from types import ModuleType
from types import SimpleNamespace

import pytest


BASE=Path(__file__).parent/'fixtures/openshell_runtime'


@pytest.fixture
def runtime(tmp_path,monkeypatch):
    helper=BASE/'guest_agent_runtime.py'
    assert helper.is_file(),'bounded agent runtime absent: intended red'
    module=ModuleType('agent_runtime_test')
    exec(compile((BASE/'guest_harness.py').read_text()+'\n'+helper.read_text(),str(helper),'exec'),module.__dict__)
    monkeypatch.setattr(module,'WORK',tmp_path)
    monkeypatch.setattr(module,'DEADLINE',time.monotonic()+60)
    monkeypatch.setattr(module,'agent_platform',lambda:None)
    return module


@pytest.mark.parametrize('case',['','codex-version','codex-version-patched-extra','opencode-rg-unknown',None,1])
def test_unselected_case_refuses_before_paths(runtime,case):
    with pytest.raises(RuntimeError,match='agent_case_selection'):runtime.agent_selection(case)


def test_case_preparation_is_exclusive_and_equivalent(runtime):
    result=runtime.agent_cases_prepare({})
    assert result['cases']==list(runtime.AGENT_CASES) and len(result['cases'])==21
    assert result['session_enabled'] is result['compatibility_qualified'] is False
    for case in runtime.AGENT_CASES:
        root=runtime.WORK/'agent-cases-1'/case
        assert (root/'codex/config.toml').read_bytes()==runtime.AGENT_CODEX_CONFIG
        assert (root/'config/opencode/.gitignore').read_bytes()==runtime.AGENT_GITIGNORE
        assert (root/'workspace/sentinel.txt').exists()==case.startswith('opencode-rg-')
        assert all((root/name).stat().st_mode&0o777==0o700 for name in runtime.AGENT_DIRS)
    with pytest.raises(RuntimeError,match='agent_cases_retained'):runtime.agent_cases_prepare({})


@pytest.mark.parametrize('change',['extra','config','symlink','mode'])
def test_case_freshness_refuses_unselected_state(runtime,change):
    runtime.agent_cases_prepare({});case=runtime.AGENT_CASES[0]
    root=runtime.WORK/'agent-cases-1'/case
    if change=='extra':(root/'home/auth.json').write_text('synthetic forbidden state')
    elif change=='config':(root/'codex/config.toml').write_text('changed')
    elif change=='symlink':(root/'workspace').rmdir();(root/'workspace').symlink_to(root/'home')
    else:(root/'home').chmod(0o755)
    with pytest.raises(RuntimeError,match='agent_case_freshness'):runtime.agent_fresh_case(case)


def test_stdio_exchange_requires_exact_identity(runtime):
    protocol=runtime.AgentProtocol('/private/codex')
    response={'id':1,'result':{'userAgent':'codex/0.164.0','codexHome':'/private/codex',
                             'platformFamily':'unix','platformOs':'linux'}}
    raw=json.dumps(response).encode()+b'\n'
    assert protocol.feed(raw[:12]) is False
    assert protocol.feed(raw[12:]) is True
    assert protocol.initialized is True
    protocol.finish()
    with pytest.raises(RuntimeError,match='agent_protocol'):protocol.feed(raw)


@pytest.mark.parametrize('response',[
    {'id':2,'result':{}},{'id':True,'result':{}},{'id':1,'error':{}},
    {'id':1,'method':'approval','params':{}},
    {'id':1,'result':{'userAgent':'x','codexHome':'/other','platformFamily':'unix','platformOs':'linux'}},
    {'id':1,'result':{'userAgent':'x','codexHome':'/private/codex','platformFamily':'unix','platformOs':'macos'}},
])
def test_stdio_rejects_responses_or_requests_without_authorizing(runtime,response):
    protocol=runtime.AgentProtocol('/private/codex')
    with pytest.raises(RuntimeError,match='agent_protocol'):protocol.feed(json.dumps(response).encode()+b'\n')


IDENTITY={'userAgent':'x','codexHome':'/private/codex','platformFamily':'unix','platformOs':'linux'}


def test_stdio_accepts_observed_notification_timestamp_after_initialize(runtime):
    protocol=runtime.AgentProtocol('/private/codex')
    lines=[{'id':1,'result':IDENTITY},
           {'method':'configWarning','params':{'summary':'x','details':None},'emittedAtMs':1793771401861},
           {'method':'bare'}]
    assert protocol.feed(b''.join(json.dumps(line).encode()+b'\n' for line in lines)) is True
    protocol.finish()


@pytest.mark.parametrize('extra',[
    {'emittedAtMs':True},{'emittedAtMs':-1},{'emittedAtMs':2**53+1},{'emittedAtMs':1.5},
    {'emittedAtMs':'1'},{'emittedAtMs':None},{'unknown':1},{'jsonrpc':'2.0'},
])
def test_stdio_rejects_bad_notification_timestamp_or_unknown_fields(runtime,extra):
    protocol=runtime.AgentProtocol('/private/codex')
    with pytest.raises(RuntimeError,match='agent_protocol_notification'):
        protocol.feed(json.dumps({'method':'configWarning',**extra}).encode()+b'\n')


def test_stdio_timestamp_never_turns_a_request_or_response_into_a_notification(runtime):
    for value in ({'id':1,'method':'x','emittedAtMs':1},{'id':1,'result':IDENTITY,'emittedAtMs':1}):
        with pytest.raises(RuntimeError,match='agent_protocol_response'):
            runtime.AgentProtocol('/private/codex').feed(json.dumps(value).encode()+b'\n')


@pytest.mark.parametrize('raw',[b'not json\n',b'{}\n',b'x'*65537])
def test_stdio_rejects_malformed_or_overlong_lines(runtime,raw):
    with pytest.raises(RuntimeError,match='agent_protocol'):runtime.AgentProtocol('/x').feed(raw)


def proof(mode=2):
    records=[(1,mode,222,350,1,0,111,0),(2,mode,0,333,int(mode!=0),0,0,0),
             (6,mode,13,1,7,1,0,0),(3,mode,int(mode==2),int(mode==2),0,0,0,0),
             (4,mode,0,333,0,0,0,0),(5,mode,1,0,0,0,0,0)]
    return b''.join(struct.pack('<4sBBH6i',b'OAC1',event,selected,0,*values)
                    for event,selected,*values in records)


def test_proof_binds_install_kernel_and_child_exit(runtime):
    result=runtime.agent_proof(proof(),'patched',222)
    assert result['exit_code']==1 and result['signal'] is None
    assert result['observation']=='exited' and len(result['records'])==6


@pytest.mark.parametrize('change',['mode','short','extra','order','reserved','kernel','parent','dumpable','fd'])
def test_proof_refuses_forged_incomplete_or_reordered_records(runtime,change):
    raw=bytearray(proof())
    if change=='mode':raw[5]=1
    elif change=='short':raw.pop()
    elif change=='extra':raw.extend(raw[-32:])
    elif change=='order':raw[32:64],raw[64:96]=raw[64:96],raw[32:64]
    elif change=='reserved':raw[6]=1
    elif change=='kernel':struct.pack_into('<i',raw,3*32+8,0)
    elif change=='parent':struct.pack_into('<i',raw,8,999)
    elif change=='dumpable':struct.pack_into('<i',raw,20,1)
    else:struct.pack_into('<i',raw,2*32+12,0)
    with pytest.raises(RuntimeError,match='agent_proof'):runtime.agent_proof(bytes(raw),'patched',222)


def test_negative_login_is_expected_but_other_nonzero_is_not(runtime):
    assert runtime.agent_expectation('codex-empty-login',1,None,b'',b'Not logged in\n',False)
    assert not runtime.agent_expectation('codex-version',1,None,b'',b'EPERM',False)
    assert not runtime.agent_expectation('codex-stdio',0,None,b'',b'',False)


def test_runtime_source_and_fixture_fit_existing_caps():
    assert (BASE/'guest_agent_runtime.py').stat().st_size<=32768
    assert (BASE/'agentcheck/main.rs').stat().st_size<=10240
    import tomllib
    lock=tomllib.loads((BASE/'agentcheck/Cargo.lock').read_text())
    assert {entry['name'] for entry in lock['package']}=={'libc','openshell-agent-filter-probe'}
    assert len(lock['package'])==2


FAKE_LAUNCHER=r'''
import fcntl, json, os, stat, struct, sys, time
assert stat.S_ISFIFO(os.fstat(3).st_mode)
assert fcntl.fcntl(3, fcntl.F_GETFL)&os.O_ACCMODE == os.O_WRONLY
assert os.get_inheritable(3)
os.set_inheritable(3, False); os.closerange(4, 256)
scenario, probe, mode_name = sys.argv[1:]
mode = ('unfiltered','upstream','patched').index(mode_name)
pid = os.getpid()
def record(event, values):
    os.write(3, struct.pack('<4sBBH6i',b'OAC1',event,mode,0,*values))
record(1,[pid,350 if mode else 0,1,0,os.getppid(),0])
record(2,[0,pid+1,int(mode!=0),0,0,0])
record(6,[13,1,7,1,0,0])
record(3,[int(mode==2),int(mode==2),0,0,0,0])
record(4,[0,pid+1,0,0,0,0])
if scenario == 'handshake':
    request=json.loads(sys.stdin.buffer.readline())
    assert request['method']=='initialize' and request['params']['capabilities']['explicitGatewayOauth'] is True
    result={'userAgent':'codex/0.164.0','codexHome':os.environ['CODEX_HOME'],'platformFamily':'unix','platformOs':'linux'}
    print(json.dumps({'id':1,'result':result}),flush=True)
    assert json.loads(sys.stdin.buffer.readline())=={'method':'initialized'}
    assert sys.stdin.buffer.read()==b''
elif scenario == 'negative':
    os.write(2,b'Operation not permitted (os error 1)\n')
elif scenario == 'malformed':
    os.write(1,b'{"id":1,"method":"approval"}\n');time.sleep(10)
elif scenario == 'timeout':
    time.sleep(10)
elif scenario == 'output':
    os.write(1,b'x'*(1024*1024+1))
elif scenario == 'badproof':
    os.write(3,b'bad!'+bytes(28))
record(5,[1 if scenario=='negative' else 0,0,0,0,0,0])
'''


@pytest.mark.parametrize('scenario,expected',[
    ('handshake','exited'),('negative','exited'),('malformed','protocol_error'),
    ('timeout','timeout'),('output','output_limit'),('badproof','proof_error'),
])
def test_real_process_transport_is_bounded_and_retains_negative_results(tmp_path,scenario,expected):
    # The isolated parent deliberately holds FD3; the real child bootstrap may
    # replace only its own FD3. The synthetic fixture makes no filter claim.
    launcher=tmp_path/'fake-launcher.py';launcher.write_text(FAKE_LAUNCHER);launcher.chmod(0o500)
    driver=r'''
import fcntl, json, os, subprocess, sys, time
from pathlib import Path
from types import ModuleType
base, root, launcher, scenario = map(str,sys.argv[1:])
module=ModuleType('driver_under_test')
source=(Path(base)/'guest_harness.py').read_text()+'\n'+(Path(base)/'guest_agent_runtime.py').read_text()
exec(compile(source,'bounded-driver','exec'),module.__dict__)
module.WORK=Path(root);module.DEADLINE=time.monotonic()+20;module.agent_platform=lambda:None
module.agent_cases_prepare({})
if not hasattr(os,'pipe2'):
    def pipe2(flags):
        read,write=os.pipe();os.set_inheritable(read,False);os.set_inheritable(write,False)
        return read,write
    module.os.pipe2=pipe2
original=subprocess.Popen
def popen(argv,**kwargs):
    assert argv[:3]==['/usr/bin/python3','-I','-c']
    assert len(kwargs['pass_fds'])==2 and 3 not in kwargs['pass_fds']
    assert kwargs['pass_fds']==tuple(map(int,argv[4:6]))
    assert kwargs['close_fds'] is True and kwargs['start_new_session'] is True
    assert 'executable' not in kwargs and 'preexec_fn' not in kwargs and not kwargs.get('shell')
    # Execute the actual trusted bootstrap, substituting only its final exec
    # with the synthetic Python fixture; /proc is unavailable on macOS.
    prefix=("import os,sys\nnative_exec=os.execve\n"
        "def synthetic_exec(path,args,env):\n"
        " assert path=='/proc/self/fd/'+sys.argv[2]\n"
        " assert args==['openshell-agent-filter-probe',*sys.argv[3:]]\n"
        " return native_exec(sys.executable,[sys.executable,'-I',"+repr(launcher)+","+repr(scenario)+",*args[1:]],env)\n"
        "os.execve=synthetic_exec\n")
    return original([sys.executable,'-I','-c',prefix+argv[3],*argv[4:]],**kwargs)
module.subprocess.Popen=popen
if scenario=='timeout':
    remaining=module.remaining
    module.remaining=lambda maximum=60:min(remaining(maximum),.2)
case=('codex-stdio' if scenario in ('handshake','negative','malformed') else 'codex-help')+'-patched'
preserved=os.open(Path(root)/'parent-descriptor',os.O_RDWR|os.O_CREAT|os.O_CLOEXEC,0o600)
assert preserved==3
os.write(preserved,b'parent descriptor must remain untouched');os.lseek(preserved,7,os.SEEK_SET)
before=(os.fstat(3),fcntl.fcntl(3,fcntl.F_GETFD),fcntl.fcntl(3,fcntl.F_GETFL),os.lseek(3,0,os.SEEK_CUR))
with module.agent_proof_pipe() as channel:
    fd=os.open(launcher,os.O_RDONLY)
    try:result=module.agent_observe(fd,case,channel)
    finally:os.close(fd)
after=(os.fstat(3),fcntl.fcntl(3,fcntl.F_GETFD),fcntl.fcntl(3,fcntl.F_GETFL),os.lseek(3,0,os.SEEK_CUR))
assert before==after
os.lseek(3,0,os.SEEK_SET);assert os.read(3,128)==b'parent descriptor must remain untouched';os.close(3)
print(json.dumps(result))
'''
    result=subprocess.run([sys.executable,'-I','-c',driver,str(BASE),str(tmp_path),str(launcher),scenario],
                          capture_output=True,timeout=12,check=True)
    observed=json.loads(result.stdout)
    assert observed['observation']==expected
    assert observed['expectation_met']==(scenario=='handshake')
    assert len(observed['stdout_tail'].encode())<=8192 and len(observed['stderr_tail'].encode())<=8192
    assert observed['stdout_bytes']+observed['stderr_bytes']<=1024*1024
    if scenario=='handshake':
        assert observed['initialize_result']['platformOs']=='linux' and observed['stdin_bytes']<1024
        assert observed['termination_requested'] is False and observed['wrapper_returncode']==0
    if scenario=='negative':
        assert observed['exit_code']==1 and 'Operation not permitted' in observed['stderr_tail']
    if scenario in ('timeout','malformed'):
        assert observed['termination_requested'] is True and observed['wrapper_returncode']<0


def test_invalid_utf8_diagnostics_stay_within_encoded_report_bound(runtime):
    assert len(runtime.agent_tail(b'\xff'*20000).encode())<=8192


def test_proof_pipe_closes_only_owned_ends_and_preserves_parent_three(runtime,monkeypatch):
    closed=[];fake=SimpleNamespace(**vars(os))
    fake.pipe2=lambda flags:(7,8)
    fake.open=lambda *a,**kw:pytest.fail('opened descriptor to reserve FD3')
    fake.dup2=lambda *a,**kw:pytest.fail('replaced a parent descriptor')
    fake.close=closed.append
    monkeypatch.setattr(runtime,'os',fake)
    with runtime.agent_proof_pipe() as (reader,writer,release):
        assert (reader,writer)==(7,8)
        release();release()
    assert closed==[8,7]


@pytest.mark.parametrize('fixture,channel',[(3,(4,5)),(0,(4,5)),(5,(4,5)),(8,(0,5)),(8,(4,4))])
def test_launch_descriptor_numbers_refuse_before_process(runtime,monkeypatch,fixture,channel):
    monkeypatch.setattr(runtime.subprocess,'Popen',lambda *a,**kw:pytest.fail('invalid descriptor launch'))
    with pytest.raises(RuntimeError,match='agent_launch_descriptors'):
        runtime.agent_observe(fixture,'codex-version-unfiltered',(*channel,lambda:None))


@pytest.mark.parametrize('status',['agent_fixture_built','agent_fixture_verified','other'])
def test_case_accepts_only_fresh_build_or_verification(runtime,monkeypatch,status):
    for name in ('agent_platform','agent_capacity','agent_nondumpable'):
        monkeypatch.setattr(runtime,name,lambda:None)
    monkeypatch.setattr(runtime,'agent_case_view',lambda case:None)
    def reached():raise RuntimeError('reached_owned_pipe')
    monkeypatch.setattr(runtime,'agent_proof_pipe',reached)
    built={'status':status,'static_arm64':True,'schema_version':1,'generation':1,**runtime.AGENT_FLAGS,
           'binary_layout':{'link_count':1,'companion':None},'binary_bytes':1,'binary_sha256':'a'*64}
    assets={'status':'agent_assets_verified','schema_version':1,'generation':1,**runtime.AGENT_FLAGS,
            'assets':{'codex':{'files':{'bin/codex':{},'codex-path/rg':{}}}}}
    expected='agent_prior_proof' if status=='other' else 'reached_owned_pipe'
    with pytest.raises(RuntimeError,match=expected):
        runtime.agent_case({'agent_build_report':built,'agent_assets_report':assets},'codex-version-unfiltered')


@pytest.mark.parametrize('failure',[None,'shared_temp','writable_asset','false_readonly','readonly_case'])
def test_case_mount_proof_checks_aliases_and_actual_write_results(runtime,monkeypatch,failure):
    runtime.agent_cases_prepare({});case=runtime.AGENT_CASES[0]
    base=runtime.WORK/'agent-cases-1'/case
    for name in ('agent-assets-1','full-source-2','full-cargo-1','full-target-1','tmp'):
        (runtime.WORK/name).mkdir(mode=0o700)
    real_path=Path;real_open=os.open
    aliases={'/tmp':runtime.WORK/'tmp' if failure=='shared_temp' else base/'tmp','/var/tmp':base/'tmp'}
    monkeypatch.setattr(runtime,'Path',lambda value:real_path(aliases.get(str(value),value)))
    def readonly(path):
        path=real_path(path)
        if failure=='readonly_case' and path==base:return True
        if failure=='writable_asset' and path==runtime.WORK/'agent-assets-1':return False
        return path!=base and base not in path.parents or path==base/'config'
    monkeypatch.setattr(runtime.os,'statvfs',lambda path:SimpleNamespace(f_flag=os.ST_RDONLY if readonly(path) else 0))
    attempts=[]
    def open_probe(path,*args,**kwargs):
        path=real_path(path);attempts.append(path)
        if readonly(path.parent) and not (failure=='false_readonly' and path.parent==runtime.WORK):
            raise OSError(30,'read-only test view')
        return real_open(path,*args,**kwargs)
    monkeypatch.setattr(runtime.os,'open',open_probe)
    if failure:
        with pytest.raises(RuntimeError,match='agent_(temp_alias|readonly_view|writable_view)'):
            runtime.agent_case_view(case)
    else:
        assert runtime.agent_case_view(case)==base
        assert any(path.parent==runtime.WORK/'agent-assets-1' for path in attempts)
        assert sum(path.parent==base/'tmp' for path in attempts)==2
    assert not any(runtime.WORK.rglob('.openshell-agent-write-probe'))


def test_asset_descriptor_hash_mode_and_cleanup(runtime,monkeypatch):
    path=runtime.WORK/'asset';path.write_bytes(b'synthetic asset');path.chmod(0o500)
    expected={'bytes':len(b'synthetic asset'),'sha256':hashlib.sha256(b'synthetic asset').hexdigest(),'mode':0o500}
    with runtime.agent_binary(path,expected) as fd:
        observed_fd=fd
        os.lseek(fd,0,os.SEEK_SET)
        assert os.read(fd,100)==b'synthetic asset'
    with pytest.raises(OSError):os.fstat(observed_fd)
    with pytest.raises(RuntimeError,match='agent_binary_identity'):
        with runtime.agent_binary(path,expected|{'sha256':'f'*64}):pytest.fail('wrong bytes accepted')
    with pytest.raises(RuntimeError,match='agent_binary_identity'):
        with runtime.agent_binary(path,expected|{'mode':0o700}):pytest.fail('wrong mode accepted')


def test_state_budget_counts_other_cases_without_following_links(runtime,monkeypatch):
    runtime.agent_cases_prepare({})
    root=runtime.WORK/'agent-cases-1'
    (root/runtime.AGENT_CASES[-1]/'cache/retained').write_bytes(b'x'*8192)
    monkeypatch.setattr(runtime,'AGENT_STATE_LIMIT',100)
    with pytest.raises(RuntimeError,match='agent_state_bound'):runtime.agent_state_bytes()


@pytest.fixture
def descriptors(runtime, monkeypatch):
    import fcntl
    import stat
    events = []; closed = []; state = {0: False, 1: True, 2: True, 3: True}; owned = 0
    def fstat(fd):
        events.append(('stat', fd))
        if not state.get(fd, False): raise OSError(9, 'closed')
        return SimpleNamespace(st_mode=stat.S_IFCHR|0o666 if fd == owned else stat.S_IFIFO|0o600,
                               st_rdev=os.makedev(1, 3) if fd == owned else 0)
    def control(fd, operation):
        events.append(('fcntl', fd, operation))
        if not state.get(fd, False): raise OSError(9, 'closed')
        return fcntl.FD_CLOEXEC if operation == fcntl.F_GETFD else os.O_RDONLY
    def opened(path, flags):
        events.append(('open', path, flags)); state[owned] = True
        return owned
    def close(fd):
        events.append(('close', fd)); closed.append(fd); state[fd] = False
    fake_os = SimpleNamespace(**vars(os)); fake_os.fstat=fstat; fake_os.open=opened; fake_os.close=close
    fake_fcntl = SimpleNamespace(**vars(fcntl)); fake_fcntl.fcntl=control
    monkeypatch.setattr(runtime, 'os', fake_os)
    monkeypatch.setattr(runtime, 'fcntl', fake_fcntl, raising=False)
    monkeypatch.setattr(runtime, 'agent_platform', lambda: events.append(('platform',)))
    monkeypatch.setattr(runtime, 'agent_capacity', lambda: events.append(('capacity',)))
    monkeypatch.setattr(runtime, 'agent_case_view', lambda case: events.append(('view', case)))
    monkeypatch.setattr(runtime, 'agent_proof_pipe', lambda: pytest.fail('proof pipe opened'))
    monkeypatch.setattr(runtime, 'command', lambda *a, **kw: pytest.fail('process executed'))
    return runtime, events, closed, state


def test_descriptor_inspection_records_without_repair_or_launch(descriptors):
    module, events, closed, state = descriptors
    result = module.agent_descriptor_inspect()
    assert set(result) == {'schema_version', 'generation', 'status', 'before', 'after_validation',
                          'after_close', 'reserved_fd', 'reserved_null', *module.AGENT_FLAGS}
    assert result['schema_version'] == result['generation'] == 1
    assert result['status'] == 'agent_descriptors_observed'
    assert result['reserved_fd'] == 0 and result['reserved_null'] is True
    assert all(result[key] is False for key in module.AGENT_FLAGS)
    assert result['before'] == result['after_validation'] == result['after_close']
    assert result['before'][0] == {'fd':0, 'errno':9, 'mode':None, 'rdev':None, 'fd_flags':None, 'status_flags':None}
    for fd, item in enumerate(result['before'][1:], 1):
        assert item == {'fd':fd, 'errno':0, 'mode':0o10600, 'rdev':0, 'fd_flags':1, 'status_flags':0}
    platform = events.index(('platform',)); view = events.index(('view', 'codex-version-unfiltered'))
    opening = events.index(('open', '/dev/null', os.O_RDONLY|os.O_CLOEXEC))
    assert events[:platform][-1][0] == 'fcntl' and platform < view < opening
    assert sum(event[0] == 'open' for event in events) == 1
    assert closed == [0] and state == {0:False, 1:True, 2:True, 3:True}


@pytest.mark.parametrize('failure', ['metadata', 'flags', 'platform', 'capacity', 'view', 'open', 'null', 'deadline'])
def test_descriptor_inspection_fails_without_touching_unowned_descriptors(descriptors, monkeypatch, failure):
    module, events, closed, state = descriptors
    def refused(*args): raise OSError(5, 'synthetic error')
    if failure == 'metadata': monkeypatch.setattr(module.os, 'fstat', refused)
    elif failure == 'flags': monkeypatch.setattr(module.fcntl, 'fcntl', refused)
    elif failure in ('platform', 'capacity', 'view'):
        monkeypatch.setattr(module, 'agent_'+('case_view' if failure == 'view' else failure), refused)
    elif failure == 'open': monkeypatch.setattr(module.os, 'open', refused)
    elif failure == 'null':
        original = module.os.fstat
        def wrong(fd):
            result = original(fd)
            if fd == 0: result.st_rdev = os.makedev(1, 5)
            return result
        monkeypatch.setattr(module.os, 'fstat', wrong)
    else: monkeypatch.setattr(module, 'DEADLINE', 0)
    with pytest.raises((RuntimeError, OSError)): module.agent_descriptor_inspect()
    assert closed == ([0] if failure == 'null' else [])
    assert state[1] is state[2] is state[3] is True


@pytest.mark.parametrize('failure',['read_pipe','regular_writer','non_executable','fd_collision','fixture_three','probe','mode'])
def test_child_bootstrap_refuses_wrong_descriptors_or_selection(runtime,tmp_path,failure):
    fixture=tmp_path/'not-executed';fixture.write_bytes(b'not an executable image');fixture.chmod(0o500)
    reader,writer=os.pipe();held=os.open(fixture,os.O_RDONLY)
    try:
        selected_writer=reader if failure=='read_pipe' else held if failure=='regular_writer' else writer
        selected_fixture=writer if failure=='fd_collision' else 3 if failure=='fixture_three' else held
        if failure=='non_executable':fixture.chmod(0o400)
        probe='arbitrary-command' if failure=='probe' else 'codex-version'
        mode='other' if failure=='mode' else 'unfiltered'
        result=subprocess.run([sys.executable,'-I','-c',runtime.AGENT_BOOTSTRAP,str(selected_writer),
                               str(selected_fixture),probe,mode],pass_fds=(reader,writer,held),
                              capture_output=True,timeout=5)
        assert result.returncode==125 and result.stdout==result.stderr==b''
        assert os.fstat(held).st_size==len(b'not an executable image')
        os.set_blocking(reader,False)
        with pytest.raises(BlockingIOError):os.read(reader,1)
    finally:
        for fd in (reader,writer,held):os.close(fd)
