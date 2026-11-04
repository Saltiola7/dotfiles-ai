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
import json, os, struct, sys, time
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
    # An isolated Python process guarantees FD3 is initially free. Its synthetic
    # fixture exercises the driver transport; it makes no native filter claim.
    launcher=tmp_path/'fake-launcher.py';launcher.write_text(FAKE_LAUNCHER)
    driver=r'''
import json, os, subprocess, sys, time
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
    assert argv[0]=='openshell-agent-filter-probe'
    assert kwargs['pass_fds'][0]==3 and len(kwargs['pass_fds'])==2
    assert kwargs.pop('executable')=='/proc/self/fd/'+str(kwargs['pass_fds'][1])
    assert kwargs['close_fds'] is True and kwargs['start_new_session'] is True
    return original([sys.executable,'-I',launcher,scenario,*argv[1:]],**kwargs)
module.subprocess.Popen=popen
if scenario=='timeout':
    remaining=module.remaining
    module.remaining=lambda maximum=60:min(remaining(maximum),.2)
case=('codex-stdio' if scenario in ('handshake','negative','malformed') else 'codex-help')+'-patched'
with module.agent_proof_pipe() as channel:
    fd=os.open(launcher,os.O_RDONLY)
    try:result=module.agent_observe(fd,case,channel)
    finally:os.close(fd)
assert not os.path.exists('/proc/self/fd/3') if sys.platform=='linux' else True
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


def test_proof_pipe_collision_preserves_existing_descriptor(runtime,monkeypatch):
    closed=[]
    monkeypatch.setattr(runtime.os,'open',lambda *a,**k:17)
    monkeypatch.setattr(runtime.os,'close',closed.append)
    with pytest.raises(RuntimeError,match='agent_proof_fd_collision'):
        with runtime.agent_proof_pipe():pytest.fail('overwrote occupied FD3')
    assert closed==[17]


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
