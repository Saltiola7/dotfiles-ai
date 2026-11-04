"""Closed host orchestration must never turn build metadata into command authority."""
from __future__ import annotations

import importlib.util
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import sys
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest


HOST_BINDING='d'*64


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
    script=build.kernel_script('', 'def stage(*args): pass', {'files':{}}, 1000,runtime='def install_runtime(): return {}',host_binding_sha256=HOST_BINDING)
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
    exec(build.kernel_script('', 'def stage(*args): pass', {}, 1000,runtime='def install_runtime(): return {}',host_binding_sha256=HOST_BINDING),namespace)
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
    exec(build.kernel_script('', 'def stage(*args): pass', {}, 1000,runtime=runtime,host_binding_sha256=HOST_BINDING),namespace)
    assert calls==['runtime','stage','stage','stage','stage']


@pytest.mark.parametrize('resume', [False, True])
def test_complete_guest_program_fits_linux_argument_and_unit_limits(build,tmp_path,resume):
    import shlex
    bundle=build.load_bundle(tmp_path)
    controller=build.read_source(build.FIXTURES/'guest_build_storage.py').decode()
    builder=build.read_source(build.FIXTURES/'guest_harness.py').decode()+'\n'+build.read_source(build.FIXTURES/'guest_unwind.py').decode()
    if resume: builder+='\n'+build.read_source(build.FIXTURES/'guest_resume.py').decode()
    runtime=build.read_source(build.FIXTURES/'guest_runtime.py').decode()
    script=build.kernel_script(controller,builder,bundle.payload,1100,runtime=runtime,resume=resume,host_binding_sha256=HOST_BINDING)
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
                                 runtime='def install_runtime(): return {}',host_binding_sha256=HOST_BINDING), namespace)
    records = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert records[-1] == {'stage': 'setup', 'finished': True, 'result': {'proof': 2}}


def test_resume_has_only_offline_stages(build):
    script=build.kernel_script('', 'def stage(*args): pass', {}, 1000,
                               runtime='def install_runtime(): return {}', resume=True,host_binding_sha256=HOST_BINDING)
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


def inventory_report():
    return {'schema_version':1,'status':'inventoried','image_bytes':8*1024**3,
            'store_capacity_bytes':7*1024**3,'store_free_bytes':4*1024**3,
            'store_available_bytes':4*1024**3,'root_free_bytes':12*1024**3,
            'work':'/var/lib/dotfiles-ai-openshell-build/store/work',
            'totals':{'entry_count':1,'unique_inode_count':1,
            'logical_bytes':0,'allocated_bytes':4096,'shared_allocated_bytes':0,
            'hardlink_entries':0,'symlink_entries':0,'work_root_allocated_bytes':4096},
            'entries':[],'build_enabled':False,'session_enabled':False,'unmounted_verified':True}


@pytest.mark.parametrize('change',['none','cap','available','used','enabled','unknown','unmounted','count'])
def test_build_inventory_report_cannot_grant_build_or_hide_missing_proof(build,change):
    report=inventory_report()
    if change=='cap': report['image_bytes']+=1
    elif change=='available': report['store_available_bytes']=report['store_free_bytes']+1
    elif change=='used': report['totals']['shared_allocated_bytes']=4097
    elif change=='enabled': report['build_enabled']=True
    elif change=='unknown': report['extra']='ignored'
    elif change=='unmounted': report['unmounted_verified']=False
    elif change=='count': report['totals']['entry_count']=200001
    if change=='none': assert build.parse_inventory(report)==report
    else:
        with pytest.raises(build.Refusal): build.parse_inventory(report)


def test_inventory_always_unmounts_and_never_invokes_builder(build,capsys):
    calls=[]
    @contextmanager
    def mounted_store(**kwargs):
        calls.append('mount')
        try: yield None
        finally: calls.append('unmount')
    ns={'json':json,'time':time,'sys':sys,'mounted_store':mounted_store,'Refusal':build.Refusal,
        'build_inventory':lambda:inventory_report()}
    exec(build.inventory_script('', '',300,host_binding_sha256=HOST_BINDING),ns)
    assert calls==['mount','unmount']
    assert json.loads(capsys.readouterr().out)['unmounted_verified'] is True
    calls.clear()
    def fail():
        error=build.Refusal('inventory_failed');error.stdout=error.stderr=b''
        raise error
    ns['build_inventory']=fail
    with pytest.raises(build.Refusal): exec(build.inventory_script('', '',300,host_binding_sha256=HOST_BINDING),ns)
    assert calls==['mount','unmount']


def test_complete_inventory_program_is_bounded_and_valid(build):
    program=build.inventory_script(build.read_source(build.FIXTURES/'guest_build_storage.py').decode(),
                                   build.read_source(build.FIXTURES/'guest_build_inventory.py').decode(),300,host_binding_sha256=HOST_BINDING)
    compile(program,'closed-inventory','exec')
    assert len(build.encode_program(program).encode())<64*1024


@pytest.fixture
def admitted_host(build):
    native=build.create.native
    pilot=Path('/Volumes/ext/state/openshell')
    run=pilot/'qualification/openshell-q-123456abcdef'
    storage=native.NativeStorageSelection('pilot',pilot,run,run/'runtime.raw',11,101,
        '11111111-1111-1111-1111-111111111111','22222222-2222-2222-2222-222222222222',
        '33333333-3333-3333-3333-333333333333')
    selected=build.create.CreateSelection(storage,'a'*64,'b'*64,build.create.RECIPE_SHA256)
    disk=native.FileIdentity(storage.runtime_path/'q/disk',22,301,0o100600,501,1,20*1024**3,4096)
    worker=build.create.inventory.RetainedWorker(run.name,'q',22,201,True,(disk,))
    config=build.create.FileEvidence(replace(disk,path=storage.runtime_path/'q/lima.yaml',inode=302),1,2,'c'*64)
    anchor=build.boot._Anchors(None,worker,config,build.create.FileEvidence(disk,3,4,None),())
    return selected,anchor


def test_host_binding_has_exact_canonical_domain_and_identity_record(build,admitted_host):
    selected,anchor=admitted_host
    storage=selected.storage
    record={'schema_version':1,'storage':{
        'profile':'pilot','pilot_root':str(storage.pilot_root),'run_root':str(storage.run_root),
        'image_path':str(storage.image_path),'image_device':11,'image_inode':101,
        'container_uuid':storage.container_uuid,'runtime_uuid':storage.runtime_uuid,'cache_uuid':storage.cache_uuid},
        'worker':{'run_id':storage.run_root.name,'name':'q','path':str(storage.runtime_path/'q'),
                  'volume_uuid':storage.runtime_uuid,'inode':201},
        'disk':{'path':str(storage.runtime_path/'q/disk'),'volume_uuid':storage.runtime_uuid,
                'inode':301,'mode':0o100600,'uid':501,'links':1}}
    canonical=json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    expected=hashlib.sha256(b'dotfiles-ai.openshell.build-store-host-binding.v1\0'+canonical).hexdigest()
    assert build.host_binding_sha256(selected,anchor)==expected


def test_host_binding_ignores_usage_transient_devices_and_source_evidence(build,admitted_host):
    selected,anchor=admitted_host
    original=build.host_binding_sha256(selected,anchor)
    disk=replace(anchor.disk,identity=replace(anchor.disk.identity,device=900,size=123,allocated=8192),
                 modified_ns=700,changed_ns=800,sha256='e'*64)
    changed=replace(anchor,disk=disk,worker=replace(anchor.worker,device=900,disks=(disk.identity,)),
                    config=replace(anchor.config,sha256='f'*64),sources=(object(),),inventory=object())
    assert build.host_binding_sha256(replace(selected,lima_sha256='1'*64,qemu_sha256='2'*64),changed)==original


@pytest.mark.parametrize('field', ['image_device','image_inode','container_uuid','runtime_uuid','cache_uuid',
                                  'worker_inode','disk_inode','disk_mode','disk_uid','disk_links'])
def test_host_binding_changes_with_each_persistent_identity(build,admitted_host,field):
    selected,anchor=admitted_host
    original=build.host_binding_sha256(selected,anchor)
    if field in {'image_device','image_inode'}:
        selected=replace(selected,storage=replace(selected.storage,**{field:getattr(selected.storage,field)+1}))
    elif field.endswith('_uuid'):
        selected=replace(selected,storage=replace(selected.storage,**{field:'44444444-4444-4444-4444-444444444444'}))
    elif field=='worker_inode':anchor=replace(anchor,worker=replace(anchor.worker,inode=202))
    else:
        name=field.removeprefix('disk_')
        disk=replace(anchor.disk.identity,**{name:getattr(anchor.disk.identity,name)+1})
        anchor=replace(anchor,disk=replace(anchor.disk,identity=disk),worker=replace(anchor.worker,disks=(disk,)))
    assert build.host_binding_sha256(selected,anchor)!=original


def bound_report():
    return {'schema_version':1,'status':'storage_bound','host_binding_sha256':HOST_BINDING,
            'legacy_receipt_sha256':'e'*64,'binding_sha256':'f'*64,'image_bytes':8*1024**3,
            'unmounted_verified':True,'session_enabled':False,'historical_outer_identity_verified':False}


@pytest.mark.parametrize('change',['none','unknown','missing','schema_bool','host','legacy_hash','binding_hash',
                                  'size','unmounted','enabled','historical'])
def test_binding_report_is_closed_and_matches_fresh_host(build,change):
    report=bound_report()
    if change=='unknown':report['override']=True
    elif change=='missing':report.pop('binding_sha256')
    elif change=='schema_bool':report['schema_version']=True
    elif change=='host':report['host_binding_sha256']='a'*64
    elif change=='legacy_hash':report['legacy_receipt_sha256']='F'*64
    elif change=='binding_hash':report['binding_sha256']=''
    elif change=='size':report['image_bytes']+=1
    elif change=='unmounted':report['unmounted_verified']=False
    elif change=='enabled':report['session_enabled']=True
    elif change=='historical':report['historical_outer_identity_verified']=True
    if change=='none':assert build.parse_bound(report,HOST_BINDING)==report
    else:
        with pytest.raises(build.Refusal):build.parse_bound(report,HOST_BINDING)


def test_binding_script_calls_only_fixed_unmounted_binding(build,capsys):
    calls=[]
    def record_stable_binding(**kwargs):
        calls.append(kwargs)
        return bound_report()
    namespace={'json':json,'sys':sys,'time':time,'Refusal':build.Refusal,
        'record_stable_binding':record_stable_binding,
        'mounted_store':lambda **k:pytest.fail('mounted'),'run_unit':lambda *a,**k:pytest.fail('service')}
    exec(build.binding_script('',300,host_binding_sha256=HOST_BINDING),namespace)
    assert len(calls)==1 and calls[0]['host_binding_sha256']==HOST_BINDING
    assert time.monotonic()<calls[0]['deadline']<=time.monotonic()+300
    assert json.loads(capsys.readouterr().out)==bound_report()


@pytest.mark.parametrize('operation',['inventory','kernel','kernel-resume'])
def test_mounted_operations_receive_fresh_binding(build,operation,capsys):
    calls=[]
    @contextmanager
    def mounted_store(**kwargs):
        calls.append(kwargs)
        yield None
    namespace={'json':json,'sys':sys,'time':time,'mounted_store':mounted_store,'Refusal':build.Refusal,
        'build_inventory':inventory_report,'run_unit':lambda *a,**k:{'stdout':b'{}'}}
    if operation=='inventory':script=build.inventory_script('','',300,host_binding_sha256=HOST_BINDING)
    else:script=build.kernel_script('','',{},1000,runtime='def install_runtime(**kwargs): return {}',
                                   resume=operation=='kernel-resume',host_binding_sha256=HOST_BINDING)
    exec(script,namespace)
    assert len(calls)==1 and calls[0]['host_binding_sha256']==HOST_BINDING


@pytest.mark.parametrize('operation',['inventory','bind-storage'])
def test_binding_computed_only_inside_admitted_inspection(build,admitted_host,monkeypatch,operation):
    selected,anchor=admitted_host;entered=[];commands=[]
    def digest(selection,observed):
        assert entered==['admitted'] and selection is selected and observed is anchor
        return HOST_BINDING
    monkeypatch.setattr(build,'host_binding_sha256',digest)
    monkeypatch.setattr(build.guest,'_inspect_guest',lambda *a:SimpleNamespace(free_bytes=16*1024**3))
    monkeypatch.setattr(build,'read_source',lambda path:b'')
    anchor=replace(anchor,sources=(SimpleNamespace(identity=SimpleNamespace(path=Path('/fixed/limactl'))),))
    def lifecycle(selection,inspect,**kwargs):
        entered.append('admitted')
        assert kwargs['qualification_seconds']==900
        return SimpleNamespace(stopped_verified=True),inspect(selected,anchor,time.monotonic()+500)
    def command(selection,argv,deadline,phase,maximum):
        commands.append(argv)
        assert '--start=false' in argv and '--' in argv
        return json.dumps(bound_report() if operation=='bind-storage' else inventory_report()).encode()
    monkeypatch.setattr(build.boot,'_qualify_with_inspection',lifecycle)
    monkeypatch.setattr(build.create,'_command',command)
    observed=build.qualify(selected,operation)
    assert len(commands)==1 and observed.lifecycle.stopped_verified is True
    assert observed.result['session_enabled'] is False


def test_bind_cli_accepts_only_selection_and_closed_operation(build,monkeypatch,capsys):
    monkeypatch.setattr(sys,'argv',['runner','--selection','unused','--operation','bind-storage'])
    monkeypatch.setattr(build.create,'private_file',lambda path:b'')
    monkeypatch.setattr(build.create,'parse_selection',lambda raw:None)
    monkeypatch.setattr(build,'qualify',lambda selected,op:SimpleNamespace(
        result=bound_report(),lifecycle=SimpleNamespace(stopped_verified=True)))
    assert build.main()==0
    assert json.loads(capsys.readouterr().out)['operation']=='bind-storage'


@pytest.mark.parametrize('override',['--host-binding-sha256','--guest-path','--uuid','--receipt'])
def test_bind_cli_refuses_identity_overrides_before_admission(build,monkeypatch,override):
    monkeypatch.setattr(sys,'argv',['runner','--selection','unused','--operation','bind-storage',override,'untrusted'])
    monkeypatch.setattr(build.create,'private_file',lambda path:pytest.fail('selection read'))
    monkeypatch.setattr(build,'qualify',lambda *a:pytest.fail('boot'))
    with pytest.raises(SystemExit) as caught:build.main()
    assert caught.value.code==2
