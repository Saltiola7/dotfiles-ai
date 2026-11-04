"""Full compilation preserves the closed, bounded optional worker lifecycle."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest


HOST_BINDING='d'*64


@pytest.fixture(scope='module')
def full():
    path=Path(__file__).with_name('probe_openshell_full_build.py')
    assert path.exists(), 'closed full build orchestration absent: intended red'
    sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location('full_build_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


def dummy_payload(full):
    return {'full_manifest':full.manifest(),'toolchain':{},'patched_sha256':'0'*64,
            'files':{'src/linux/child_seccomp.rs':''}}


def test_selected_manifest_preserves_native_limits(full,tmp_path):
    bundle=full.load_bundle(tmp_path)
    value=bundle.payload['full_manifest']
    assert value['limits']['store_bytes']==8*1024**3
    assert value['limits']['memory_bytes']==6*1024**3
    assert value['limits']['jobs']==2
    assert value['limits']['lifecycle_seconds']==1800
    assert value['experimental_version']=='0.1.7+dotfiles-ai.child-unix-deny.2'
    assert len(value['c_toolchain']['packages'])==15
    assert value['cargo']['source']=='full-source-2'


@pytest.mark.parametrize('operation',['full-prepare','full-source-reprepare'])
def test_public_runner_dispatches_full_operation_without_legacy_boot(full,monkeypatch,operation):
    sentinel=object()
    # Import the runner's canonical lazy import target, preserving existing
    # module tests that load it under an isolated fixture identity.
    import probe_openshell_full_build as canonical
    monkeypatch.setattr(canonical,'qualify',lambda selected,operation:sentinel)
    assert full.build.qualify(None,operation) is sentinel


@pytest.mark.parametrize('operation',['activate','start','full','full-prune','full-resume',''])
def test_unknown_full_operation_refuses_before_boot(full,monkeypatch,operation):
    monkeypatch.setattr(full.boot,'_qualify_with_inspection',lambda *a,**k:pytest.fail('boot'))
    with pytest.raises(full.build.Refusal): full.qualify(None,operation)


@pytest.mark.parametrize('operation,networks,library_tests',[
    ('full-prepare',[False,True,False,False,True],[False,False,False,False,False]),
    ('full-source-reprepare',[False,False,False],[False,False,False]),
    ('full-fetch',[False,False,False,True],[False,False,False,False]),
    ('full-test',[False,False,False,False,False,False],[False,False,False,False,True,False]),
])
def test_full_operations_separate_network_and_execution(full,operation,networks,library_tests,capsys):
    calls=[]
    @contextmanager
    def mounted_store(**kwargs): yield None
    def run_unit(script,**kwargs):
        compile(script,'bounded-full-stage','exec')
        calls.append((kwargs['network'],kwargs['library_tests']))
        return {'stdout':json.dumps({'status':'verified'}).encode()}
    namespace={'time':time,'sys':sys,'json':json,'mounted_store':mounted_store,
               'run_unit':run_unit,'Refusal':full.build.Refusal,
               'build_inventory':lambda:{'store_available_bytes':5*1024**3},
               'install_runtime':lambda **k:{'status':'runtime_ready','installed_bytes':945234}}
    for stage,_,_,maximum in full.STAGES[operation]:
        script=full.stage_script('', '', '', '', dummy_payload(full),operation,stage,maximum+100,host_binding_sha256=HOST_BINDING)
        exec(script,namespace)
    assert calls==list(zip(networks,library_tests,strict=True))
    report=json.loads(capsys.readouterr().out.splitlines()[-1])
    assert report['unmounted_verified'] is True
    assert report['session_enabled'] is False
    assert report['full_runtime_qualified'] is False


@pytest.mark.parametrize('operation,threshold',[
    ('full-prepare',4*1024**3),('full-source-reprepare',2*1024**3),
    ('full-fetch',3*1024**3),('full-test',2*1024**3)])
def test_low_capacity_stops_before_inputs_or_service(full,operation,threshold):
    @contextmanager
    def mounted_store(**kwargs): yield None
    namespace={'time':time,'sys':sys,'json':json,'mounted_store':mounted_store,
               'run_unit':lambda *a,**k:pytest.fail('service'),
               'install_runtime':lambda **k:pytest.fail('runtime'),
               'Refusal':full.build.Refusal,
               'build_inventory':lambda:{'store_available_bytes':threshold-1}}
    with pytest.raises(RuntimeError,match='full_build_capacity'):
        exec(full.stage_script('','','','',dummy_payload(full),operation,'rust-verify',340,host_binding_sha256=HOST_BINDING),namespace)


def test_every_full_program_fits_existing_transport_and_service_bounds(full,tmp_path):
    bundle=full.load_bundle(tmp_path)
    for operation in full.OPERATIONS:
        sources=full.capture_sources(operation)
        controller=full.build.read_source(full.build.FIXTURES/'guest_build_storage.py').decode()
        runtime=full.build.read_source(full.build.FIXTURES/'guest_runtime.py').decode()
        inventory=full.build.read_source(full.build.FIXTURES/'guest_build_inventory.py').decode()
        for stage,key,_,maximum in full.STAGES[operation]:
            script=full.stage_script(controller,runtime,inventory,sources[key],bundle.payload,operation,stage,maximum+100,host_binding_sha256=HOST_BINDING)
            compile(script,'full-native-operation','exec')
            full.build.encode_program(script)
            unit=full.unit_source(sources[key],bundle.payload,stage,maximum-5)
            compile(unit,'full-unprivileged-stage','exec')
            assert len(unit.encode())<=65536


def test_failed_stage_retains_prior_diagnostics_and_exits_mount(full,capsys):
    ended=[];calls=[]
    @contextmanager
    def mounted_store(**kwargs):
        try: yield None
        finally: ended.append(True)
    def run_unit(script,**kwargs):
        calls.append(True)
        if len(calls)==2: raise RuntimeError('input refused')
        return {'stdout':b'{"status":"verified"}'}
    namespace={'time':time,'sys':sys,'json':json,'mounted_store':mounted_store,
               'run_unit':run_unit,'Refusal':full.build.Refusal,
               'build_inventory':lambda:{'store_available_bytes':5*1024**3},
               'install_runtime':lambda **k:{'status':'runtime_ready'}}
    with pytest.raises(RuntimeError,match='input refused'):
        for stage,_,_,maximum in full.STAGES['full-prepare']:
            exec(full.stage_script('','','','',dummy_payload(full),'full-prepare',stage,maximum+100,host_binding_sha256=HOST_BINDING),namespace)
    captured=capsys.readouterr()
    assert ended==[True,True] and 'rust-verify' in captured.out and 'compiler-download' not in captured.out


@pytest.fixture
def stage_report(full):
    value=full.manifest();sha='a'*64
    compiler={'status':'compiler_verified','package_count':15,'authenticated_packages':15,
              'compiler_tree_sha256':sha,'expanded_bytes':100,
              'archive_sha256':{p['archive']:sha for p in value['c_toolchain']['packages']},
              'omitted_gdb_entries':{stem+suffix:{'kind':'file' if suffix=='.so.0.0.0' else 'symlink','sha256':sha}
                  for stem in ('usr/lib/libcc1',
                      'usr/lib/gcc/aarch64-alpine-linux-musl/14.2.0/plugin/libcc1plugin',
                      'usr/lib/gcc/aarch64-alpine-linux-musl/14.2.0/plugin/libcp1plugin')
                  for suffix in ('.so','.so.0','.so.0.0.0')}}
    source={'source_verified':True,'changed_files':4,'source_blobs':2196,'source_generation':2,
            'source':'/var/lib/dotfiles-ai-openshell-build/store/work/full-source-2',
            'network_test_original_sha256':'4de840d02dc34a63102e9deece321d0f4253f67fe226475778c7f71292d9c899',
            'network_test_sha256':'3a3112b39af2499bc30603f5655d7425b6b265a3a69af9234ccf24805645ea84',
            'upstream_commit':value['upstream_commit'],'upstream_tree_sha1':value['upstream_tree_sha1'],
            'experimental_version':value['experimental_version'],'patched_source_sha256':full.build.PATCHED_SHA,
            'derived_manifest_sha256':value['source']['derived_manifest_sha256'],
            'derived_lock_sha256':value['source']['derived_lock_sha256'],
            'archive_sha256':sha,'metadata_sha256':sha,'session_enabled':False,'full_runtime_qualified':False}
    tested={'status':'full_cargo_tested','static_arm64':True,
            'experimental_version':value['experimental_version'],'patched_source_sha256':full.build.PATCHED_SHA,
            'derived_lock_sha256':value['source']['derived_lock_sha256'],
            'binary_sha256':sha,'test_binary_sha256':sha,
            'binary_layout':{'link_count':1,'companion':None},
            'filtered_stdout':'openshell-child-unix-denial-checked',
            'session_enabled':False,'full_runtime_qualified':False}
    return {'rust-verify':{'status':'rust_verified','files':105,'rustc':'release: 1.95.0\n'},
            'compiler-verify':compiler,'source-verify':source,
            'cargo-verify':{'status':'full_cargo_verified','locked_registry_records':830,'crates':700,
                'compressed_bytes':100,'expanded_bytes':200,'cache_sha256':sha,
                'protoc':{'version':'31.1','binary_sha256':sha},
                'session_enabled':False,'full_runtime_qualified':False},
            'cargo-test':tested,'source-final':dict(source)}


def test_host_accepts_complete_selected_build_proof(full,stage_report):
    full.parse_stages(stage_report,'full-test')


def test_offline_reprepare_requires_rust_compiler_and_source_proof(full,stage_report):
    assert full.STAGES['full-source-reprepare']==(
        ('rust-verify','rust',False,240),('compiler-verify','compiler',False,240),
        ('source-reprepare','source',False,300))
    report={name:stage_report[name] for name in ('rust-verify','compiler-verify')}
    report['source-reprepare']=stage_report['source-verify']
    full.parse_stages(report,'full-source-reprepare')
    report['source-reprepare']['source_generation']=1
    with pytest.raises(full.build.Refusal,match='full_build_source_proof'):
        full.parse_stages(report,'full-source-reprepare')


@pytest.mark.parametrize('key,value',[
    ('source_generation',None),('source_generation',1),('source_generation',2.0),
    ('source_generation',True),('changed_files',3),('changed_files',4.0),
    ('source',None),('source','/var/lib/dotfiles-ai-openshell-build/store/work/full-source-1'),
    ('source','/foreign/full-source-2'),
    ('network_test_original_sha256',None),('network_test_original_sha256','a'*64),
    ('network_test_sha256',None),('network_test_sha256','a'*64),
])
def test_host_requires_exact_source_generation_and_fourth_file(full,stage_report,key,value):
    # Keep initial and final reports equal so equality alone cannot validate
    # the generation, source location, or reviewed fourth-file identities.
    for name in ('source-verify','source-final'):stage_report[name][key]=value
    with pytest.raises(full.build.Refusal,match='full_build_source_proof'):
        full.parse_stages(stage_report,'full-test')


@pytest.mark.parametrize('layout',[
    {'link_count':1,'companion':None},
    {'link_count':2,'companion':'openshell_sandbox-0123456789abcdef'},
])
def test_host_accepts_only_observed_singleton_or_exact_cargo_companion(full,stage_report,layout):
    stage_report['cargo-test']['binary_layout']=layout
    full.parse_stages(stage_report,'full-test')


@pytest.mark.parametrize('layout',[
    None,[],{},
    {'link_count':1},
    {'companion':None},
    {'link_count':1,'companion':None,'verified':True},
    {'link_count':True,'companion':None},
    {'link_count':1.0,'companion':None},
    {'link_count':'1','companion':None},
    {'link_count':0,'companion':None},
    {'link_count':3,'companion':'openshell_sandbox-0123456789abcdef'},
    {'link_count':1,'companion':'openshell_sandbox-0123456789abcdef'},
    {'link_count':2,'companion':None},
    {'link_count':2,'companion':False},
    {'link_count':2,'companion':'openshell_sandbox-0123456789ABCDEF'},
    {'link_count':2,'companion':'openshell_sandbox-01234567'},
    {'link_count':2,'companion':'openshell_sandbox-0123456789abcdef0'},
    {'link_count':2,'companion':'openshell-sandbox-0123456789abcdef'},
    {'link_count':2,'companion':'../openshell_sandbox-0123456789abcdef'},
    {'link_count':2,'companion':'/release/deps/openshell_sandbox-0123456789abcdef'},
    {'link_count':2,'companion':'openshell_sandbox-0123456789abcdef\n'},
])
def test_host_refuses_missing_ambiguous_or_unselected_binary_layout(full,stage_report,layout):
    stage_report['cargo-test']['binary_layout']=layout
    with pytest.raises(full.build.Refusal):full.parse_stages(stage_report,'full-test')


def test_host_requires_binary_layout_in_cargo_result(full,stage_report):
    stage_report['cargo-test'].pop('binary_layout')
    with pytest.raises(full.build.Refusal):full.parse_stages(stage_report,'full-test')


def test_host_admits_only_verified_prefix_before_next_stage(full,stage_report):
    for size in range(1,len(stage_report)+1):
        prefix=dict(list(stage_report.items())[:size])
        full.parse_stages(prefix,'full-test',complete=False)
        prefix[next(reversed(prefix))]={}
        with pytest.raises(full.build.Refusal): full.parse_stages(prefix,'full-test',complete=False)


def test_host_refuses_skipped_prerequisite(full,stage_report):
    stage_report.pop('source-verify')
    with pytest.raises(full.build.Refusal): full.parse_stages(stage_report,'full-test',complete=False)


@pytest.mark.parametrize('change',['missing','extra','kind','hash','fields'])
def test_host_requires_exact_authenticated_gdb_omission(full,stage_report,change):
    entries=stage_report['compiler-verify']['omitted_gdb_entries']
    if change=='missing':entries.pop('usr/lib/libcc1.so')
    elif change=='extra':entries['usr/bin/gcc']={'kind':'file','sha256':'a'*64}
    elif change=='kind':entries['usr/lib/libcc1.so']['kind']='file'
    elif change=='hash':entries['usr/lib/libcc1.so']['sha256']='invalid'
    elif change=='fields':entries['usr/lib/libcc1.so']['target']='unselected'
    with pytest.raises(full.build.Refusal):full.parse_stages(stage_report,'full-test')


@pytest.mark.parametrize('stage,key,value',[
    ('rust-verify','files',0),('compiler-verify','authenticated_packages',0),
    ('compiler-verify','expanded_bytes',257*1024**2),('source-verify','source_verified',False),
    ('compiler-verify','archive_sha256',{str(i):'a'*64 for i in range(15)}),
    ('source-verify','derived_lock_sha256','b'*64),('source-verify','upstream_commit','b'*40),
    ('cargo-test','static_arm64',False),('cargo-test','filtered_stdout',''),
    ('cargo-test','experimental_version','0.1.7'),('cargo-test','session_enabled',True),
    ('cargo-test','full_runtime_qualified',True),('cargo-test','patched_source_sha256','b'*64),
    ('cargo-verify','locked_registry_records',829),('cargo-verify','cache_sha256',''),
    ('cargo-verify','expanded_bytes',2*1024**3+1),('source-final','metadata_sha256','b'*64),
])
def test_host_rejects_incomplete_or_wrong_proof(full,stage_report,stage,key,value):
    stage_report[stage][key]=value
    with pytest.raises(full.build.Refusal): full.parse_stages(stage_report,'full-test')


@pytest.mark.parametrize('operation',['full-prepare','full-source-reprepare','full-fetch','full-test'])
def test_every_full_stage_receives_same_fresh_host_binding(full,operation,capsys):
    bindings=[]
    @contextmanager
    def mounted_store(**kwargs):
        bindings.append(kwargs['host_binding_sha256'])
        yield None
    namespace={'time':time,'sys':sys,'json':json,'mounted_store':mounted_store,
               'run_unit':lambda *a,**k:{'stdout':b'{"status":"verified"}'},'Refusal':full.build.Refusal,
               'build_inventory':lambda:{'store_available_bytes':5*1024**3},
               'install_runtime':lambda **k:{'status':'runtime_ready'}}
    for stage,_,_,maximum in full.STAGES[operation]:
        script=full.stage_script('','','','',dummy_payload(full),operation,stage,maximum+100,
                                 host_binding_sha256=HOST_BINDING)
        exec(script,namespace)
    assert bindings==[HOST_BINDING]*len(full.STAGES[operation])


@pytest.mark.parametrize('operation',['full-prepare','full-source-reprepare','full-fetch','full-test'])
def test_full_lifecycle_computes_binding_after_admission_before_each_stage(full,monkeypatch,operation):
    selected=SimpleNamespace(storage=SimpleNamespace(cache_path=Path('/private/controller-cache')))
    anchor=SimpleNamespace(sources=(SimpleNamespace(identity=SimpleNamespace(path=Path('/fixed/limactl'))),))
    admitted=[];digests=[];scripts=[]
    def lifecycle(selection,inspect,**kwargs):
        assert selection is selected and kwargs['qualification_seconds']==1800
        admitted.append(True)
        return SimpleNamespace(stopped_verified=True),inspect(selected,anchor,time.monotonic()+1700)
    def digest(selection,observed):
        assert admitted==[True] and selection is selected and observed is anchor
        digests.append(True)
        return HOST_BINDING
    def script(controller,runtime,inventory,source,payload,op,stage,seconds,**kwargs):
        assert digests==[True] and op==operation and kwargs=={'host_binding_sha256':HOST_BINDING}
        scripts.append(stage)
        return 'pass\n'
    monkeypatch.setattr(full.boot,'_qualify_with_inspection',lifecycle)
    monkeypatch.setattr(full.guest,'_inspect_guest',lambda *a:None)
    monkeypatch.setattr(full.build,'host_binding_sha256',digest)
    monkeypatch.setattr(full.build,'read_source',lambda path:b'')
    monkeypatch.setattr(full,'capture_sources',lambda op:{key:'' for key in full.required_sources(op)})
    monkeypatch.setattr(full,'load_bundle',lambda parent:full.build.Bundle({},{}))
    monkeypatch.setattr(full,'stage_script',script)
    monkeypatch.setattr(full.create,'_command',lambda *a:b'{}')
    monkeypatch.setattr(full,'parse_stage',lambda result,op,stage:{
        'result':{'status':'verified'},'inventory_before':{},'inventory_after':{},'runtime':{}})
    monkeypatch.setattr(full,'parse_stages',lambda *a,**k:None)
    monkeypatch.setattr(full,'parse_result',lambda result,op:result)
    observed=full.qualify(selected,operation)
    assert digests==[True] and scripts==[item[0] for item in full.STAGES[operation]]
    assert observed.lifecycle.stopped_verified is True
    assert observed.session_enabled is False
