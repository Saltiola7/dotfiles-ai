"""Closed host orchestration must never turn build metadata into command authority."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest


@pytest.fixture(scope='module')
def build():
    path=Path(__file__).with_name('probe_openshell_guest_build.py')
    assert path.exists(), 'closed guest build runner absent: intended red evidence'
    sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location('guest_build_under_test',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


def test_bundle_is_exact_source_and_toolchain(build,tmp_path):
    bundle=build.load_bundle(tmp_path)
    assert bundle.payload['toolchain']['host']=='aarch64-unknown-linux-musl'
    assert set(bundle.payload['files'])=={'Cargo.toml','Cargo.lock','src/lib.rs','src/linux/child_seccomp.rs'}
    assert len(bundle.payload['toolchain']['artifacts'])==3
    assert bundle.payload['patched_sha256']=='57a91bdc412ceb124da0b409f841420de35b692b07db0e806cd888c3ab7a3bb1'


@pytest.mark.parametrize('operation',['command','build-all','activate','start',''])
def test_unknown_operation_cannot_start_worker(build,monkeypatch,operation):
    monkeypatch.setattr(build.boot,'_qualify_with_inspection',lambda *a,**k:pytest.fail('started'))
    with pytest.raises(build.Refusal): build.qualify(None,operation)


def test_fixed_script_has_no_arbitrary_root_cli(build):
    script=build.prepare_script('def prepare(): return {"prepared": True}\n')
    assert 'sudo' not in script and 'sys.argv' not in script
    compile(script,'fixed-prepare','exec')


@pytest.mark.parametrize('change',['none','size','fixture','written','boolean','enabled','unknown'])
def test_prepare_report_must_prove_exact_limits(build,change):
    value={'schema_version':1,'status':'prepared','image_bytes':8*1024**3,'fixture_bytes':64*1024**2,
           'fixture_written_bytes':60*1024**2,'escape_verified':True,'enospc_verified':True,
           'unmounted_verified':True,'work':'/var/lib/dotfiles-ai-openshell-build/store/work','allocation_enabled':False}
    if change=='size': value['image_bytes']+=1
    elif change=='fixture': value['fixture_bytes']=128*1024**2
    elif change=='written': value['fixture_written_bytes']=66*1024**2
    elif change=='boolean': value['enospc_verified']=1
    elif change=='enabled': value['allocation_enabled']=True
    elif change=='unknown': value['command']='x'
    if change=='none': assert build.parse_prepared(value)==value
    else:
        with pytest.raises(build.Refusal): build.parse_prepared(value)


def test_kernel_script_keeps_four_fixed_stages_and_offline_test(build):
    script=build.kernel_script('', 'def stage(*args): pass', {'files':{}}, 1000,runtime='def install_runtime(): return {}')
    compile(script,'fixed-kernel','exec')
    assert "('download', True" in script and "('fetch', True" in script
    assert "('setup', False" in script and "('test', False" in script
    assert 'mounted_store' in script


def test_kernel_script_composes_valid_unprivileged_stage_source(build):
    calls=[]
    @contextmanager
    def mounted_store(**kwargs): yield None
    def run_unit(script,**kwargs):
        compile(script,'generated-unprivileged-stage','exec')
        calls.append(kwargs['network'])
        return {'stdout':b'{}'}
    namespace={'time':time,'sys':sys,'json':json,'mounted_store':mounted_store,'run_unit':run_unit}
    exec(build.kernel_script('', 'def stage(*args): pass', {}, 1000,runtime='def install_runtime(): return {}'),namespace)
    assert calls==[True,False,True,False]


def test_cli_rejects_command_override(build,monkeypatch):
    monkeypatch.setattr(sys,'argv',['runner','--selection','unused','--command','x'])
    with pytest.raises(SystemExit) as caught: build.main()
    assert caught.value.code==2


def test_prepare_failure_retains_bounded_private_diagnostics(build, capsys):
    controller='''
class Refusal(Exception):
    stdout = b"bounded compiler output"
    stderr = b"bounded compiler error"
def prepare():
    raise Refusal("unit_failed")
'''
    with pytest.raises(Exception,match='unit_failed'):
        exec(build.prepare_script(controller),{'sys':sys,'json':json})
    captured=capsys.readouterr()
    assert 'bounded compiler output' in captured.err
    assert 'bounded compiler error' in captured.err
    assert captured.out==''


def test_kernel_admits_runtime_before_unprivileged_stages(build):
    calls=[]
    @contextmanager
    def mounted_store(**kwargs): yield None
    def run_unit(script,**kwargs):
        calls.append('stage')
        return {'stdout':b'{}'}
    runtime="def install_runtime():\n    calls.append('runtime')\n    return {'status':'runtime_ready','installed_bytes':945234}\n"
    namespace={'time':time,'sys':sys,'json':json,'calls':calls,'mounted_store':mounted_store,'run_unit':run_unit}
    exec(build.kernel_script('', 'def stage(*args): pass', {}, 1000,runtime=runtime),namespace)
    assert calls==['runtime','stage','stage','stage','stage']


@pytest.mark.parametrize('resume', [False, True])
def test_complete_guest_program_fits_linux_argument_and_unit_limits(build,tmp_path,resume):
    import shlex
    bundle=build.load_bundle(tmp_path)
    controller=build.read_source(build.FIXTURES/'guest_build_storage.py').decode()
    builder=build.read_source(build.FIXTURES/'guest_harness.py').decode()+'\n'+build.read_source(build.FIXTURES/'guest_unwind.py').decode()
    if resume: builder+='\n'+build.read_source(build.FIXTURES/'guest_resume.py').decode()
    runtime=build.read_source(build.FIXTURES/'guest_runtime.py').decode()
    script=build.kernel_script(controller,builder,bundle.payload,1100,runtime=runtime,resume=resume)
    compile(script,'closed-native-kernel','exec')
    command=shlex.join(['/usr/bin/sudo','-n','/usr/bin/python3','-I','-c',build.encode_program(script)])
    assert len(command.encode())<64*1024
    unit=builder+'\n'+build.payload_source(bundle.payload)+'\nstage("download",_stage_payload,420)\n'
    compile(unit,'closed-unprivileged-stage','exec')
    assert len(unit.encode())<=65536


def test_guest_transport_roundtrips_reviewed_source_before_execution(build):
    source="proof = 'exact source'\n"
    wire=build.encode_program(source)
    namespace={}
    exec(wire,namespace)
    assert namespace['proof']=='exact source'
    assert len(wire.encode())<65536


def test_guest_transport_rejects_modified_identity_before_execution(build):
    import hashlib
    source="proof = 'must not execute'\n"
    wire=build.encode_program(source).replace(hashlib.sha256(source.encode()).hexdigest(),'0'*64)
    namespace={}
    with pytest.raises(RuntimeError,match='guest_program_identity'):
        exec(wire,namespace)
    assert 'proof' not in namespace


def test_guest_transport_rejects_trailing_compressed_data(build):
    import base64,re
    wire=build.encode_program("proof = 'must not execute'\n")
    encoded=re.search(r"b64decode\('([^']+)'\)",wire).group(1)
    changed=base64.b64encode(base64.b64decode(encoded)+b'trailing').decode()
    namespace={}
    with pytest.raises(RuntimeError,match='guest_program_identity'):
        exec(wire.replace(encoded,changed),namespace)
    assert 'proof' not in namespace


def test_guest_transport_bounds_expanded_source_before_vm(build):
    with pytest.raises(build.Refusal,match='guest_program_bound'):
        build.encode_program('x'*(256*1024+1))


def test_completed_stage_results_survive_later_failure(build, capsys):
    @contextmanager
    def mounted_store(**kwargs): yield None
    count = 0
    def run_unit(script, **kwargs):
        nonlocal count
        count += 1
        if count == 3: raise RuntimeError('later stage failed')
        return {'stdout': json.dumps({'proof': count}).encode()}
    namespace = {'time': time, 'sys': sys, 'json': json,
                 'mounted_store': mounted_store, 'run_unit': run_unit, 'Refusal': build.Refusal}
    with pytest.raises(RuntimeError, match='later stage failed'):
        exec(build.kernel_script('', 'def stage(*args): pass', {}, 1000,
                                 runtime='def install_runtime(): return {}'), namespace)
    records = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert records[-1] == {'stage': 'setup', 'finished': True, 'result': {'proof': 2}}


def test_resume_has_only_offline_stages(build):
    script=build.kernel_script('', 'def stage(*args): pass', {}, 1000,
                               runtime='def install_runtime(): return {}', resume=True)
    assert "('resume', False" in script and "('test', False" in script
    assert "('download', True" not in script and "('fetch', True" not in script


def test_payload_transport_is_bounded_authenticated_data(build):
    payload={'example':'value', 'code':'raise RuntimeError("not executed")'}
    namespace={'json':json,'hashlib':__import__('hashlib')}
    exec(build.payload_source(payload),namespace)
    assert namespace['_stage_payload']==payload
    source=build.payload_source(payload)
    import re
    tampered=re.sub(r"hexdigest\(\)!='[a-f0-9]{64}'", "hexdigest()!='"+'0'*64+"'",source)
    with pytest.raises(RuntimeError,match='build_payload_identity'):
        exec(tampered,{'json':json,'hashlib':__import__('hashlib')})
    with pytest.raises(build.Refusal): build.payload_source({'oversized':'x'*(128*1024)})
