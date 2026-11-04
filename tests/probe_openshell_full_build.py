"""Closed full-build operations inside the existing optional capped guest.

No normal agent configuration, credentials, runtime activation, or new storage
backend is part of this test-only interface.
"""
from __future__ import annotations

import hashlib
import json
import re

import probe_openshell_guest_build as build
import probe_openshell_guest_inventory as guest
import probe_openshell_storage_boot as boot
import probe_openshell_storage_create as create


OPERATIONS=('full-prepare','full-source-reprepare','full-fetch','full-test')
NETWORK_TEST_ORIGINAL_SHA256='4de840d02dc34a63102e9deece321d0f4253f67fe226475778c7f71292d9c899'
NETWORK_TEST_SHA256='3a3112b39af2499bc30603f5655d7425b6b265a3a69af9234ccf24805645ea84'
STAGES={
    'full-prepare':(('rust-verify','rust',False,240),
                    ('compiler-download','compiler',True,300),
                    ('compiler-prepare','compiler',False,300),
                    ('compiler-probe','compiler',False,120),
                    ('source-prepare','source',True,300)),
    'full-source-reprepare':(('rust-verify','rust',False,240),
                             ('compiler-verify','compiler',False,240),
                             ('source-reprepare','source',False,300)),
    'full-fetch':(('rust-verify','rust',False,240),
                  ('compiler-verify','compiler',False,240),
                  ('source-verify','source',False,120),
                  ('cargo-fetch','cargo',True,1000)),
    'full-test':(('rust-verify','rust',False,240),
                 ('compiler-verify','compiler',False,240),
                 ('source-verify','source',False,120),
                 ('cargo-verify','cargo',False,240),
                 ('cargo-test','cargo',False,1400),
                 ('source-final','source',False,120)),
}
STAGE_BODIES={
    'rust-verify': """
_unwind, _library = unwind_verify()
if digest(WORK/TOOLCHAIN/'lib/libgcc_s.so.1') != hashlib.sha256(_library).hexdigest():
    raise RuntimeError('full_rust_unwind_identity')
_files=resume_rust(_stage_payload)
_version,_=command([str(WORK/TOOLCHAIN/'bin/rustc'),'-vV'],environment=environment())
if (b'release: 1.95.0\\n' not in _version or ('host: '+HOST+'\\n').encode() not in _version
        or _stage_payload['toolchain']['commit'].encode() not in _version):
    raise RuntimeError('full_rust_identity')
_result={'status':'rust_verified','files':_files,'unwind':_unwind,'rustc':_version.decode()}
""",
    'compiler-download': '_result=full_compiler_download(_stage_payload)\n',
    'compiler-prepare': '_result=full_compiler_prepare(_stage_payload)\n',
    'compiler-verify': '_result=full_compiler_verify(_stage_payload)\n',
    'compiler-probe': '_result=full_compiler_probe(_stage_payload)\n',
    'source-prepare': '_result=full_source_prepare(_stage_payload,int(remaining(1200)))\n',
    'source-reprepare': '_result=full_source_reprepare(_stage_payload,int(remaining(1200)))\n',
    'source-verify': '_result=full_source_verify(_stage_payload,int(remaining(1200)))\n',
    'source-final': '_result=full_source_verify(_stage_payload,int(remaining(1200)))\n',
    'cargo-fetch': '_result=full_cargo_fetch(_stage_payload)\n',
    'cargo-verify': '_result=full_cargo_verify(_stage_payload)\n',
    'cargo-test': '_result=full_cargo_test(_stage_payload)\n',
}
DEFAULT_STAGE={'rust':'rust-verify','compiler':'compiler-verify',
               'source':'source-verify','cargo':'cargo-verify'}


def manifest() -> dict:
    value=create._json(build.read_source(build.FIXTURES/'fullbuild/manifest.json'))
    limits={'required_free_before_prepare':4*1024**3,'required_free_before_fetch':3*1024**3,
            'required_free_before_build':2*1024**3,'reserve_bytes':256*1024**2,
            'store_bytes':8*1024**3,'jobs':2,'memory_bytes':6*1024**3,
            'swap_bytes':0,'tasks':512,'lifecycle_seconds':1800,'cleanup_seconds':60}
    if (value.get('schema_version')!=1 or value.get('upstream_commit')!=build.UPSTREAM
            or value.get('upstream_tree_sha1')!='053850cd069ba0f770d8296eae6be36d6cf52da7'
            or value.get('experimental_version')!='0.1.7+dotfiles-ai.child-unix-deny.2'
            or value.get('limits')!=limits
            or value.get('source',{}).get('network_test_original_sha256')!=NETWORK_TEST_ORIGINAL_SHA256
            or value.get('source',{}).get('network_test_sha256')!=NETWORK_TEST_SHA256
            or value.get('cargo')!={'home':'full-cargo-1','target':'full-target-1','source':'full-source-2',
                'auto_clean_frequency':'never','incremental':'0','release_debug':'0',
                'aws_lc_sys_use_system':'0','aws_lc_sys_cmake_builder':'0','locked':True,'offline_compile':True}
            or len(value.get('c_toolchain',{}).get('packages',[]))!=15
            or value['c_toolchain'].get('compressed_bytes')!=59383318
            or value['c_toolchain'].get('expanded_limit')!=256*1024**2):
        raise build.Refusal('full_build_selection')
    return value


def load_bundle(parent) -> build.Bundle:
    base=build.load_bundle(parent)
    selected=manifest()
    raw=build.read_source(build.FIXTURES/'fullbuild/manifest.json')
    return build.Bundle(base.payload|{'full_manifest':selected},
                        base.source_hashes|{'fullbuild/manifest.json':hashlib.sha256(raw).hexdigest()})


def required_sources(operation: str) -> tuple[str,...]:
    if operation not in OPERATIONS: raise build.Refusal('full_build_operation')
    return tuple(dict.fromkeys(stage[1] for stage in STAGES[operation]))


def capture_sources(operation: str) -> dict[str,str]:
    files={'rust':('guest_unwind.py','guest_resume.py'),
           'compiler':('guest_unwind.py','guest_full_compiler.py'),
           'source':('guest_full_source.py',),'cargo':('guest_full_cargo.py',)}
    base=build.read_source(build.FIXTURES/'guest_harness.py').decode()
    return {key:base+'\n'+'\n'.join(build.read_source(build.FIXTURES/name).decode() for name in files[key])
            for key in required_sources(operation)}


def unit_tail(stage: str, seconds: int) -> str:
    selected=DEFAULT_STAGE.get(stage,stage)
    if selected not in STAGE_BODIES or type(seconds) is not int or not 1<=seconds<=1495:
        raise build.Refusal('full_build_stage')
    return (f'\nDEADLINE=time.monotonic()+{seconds!r}\nvalidate_context()\n'
            +STAGE_BODIES[selected]
            +"\nremaining()\nprint(json.dumps(_result,sort_keys=True),flush=True)\n")


def unit_source(source: str, payload: dict, stage: str, seconds: int) -> str:
    unit=source+'\n'+build.payload_source(stage_payload(payload,stage))+unit_tail(stage,seconds)
    if len(unit.encode())>65536: raise build.Refusal('full_build_unit_bound')
    return unit


def stage_payload(payload: dict, stage: str) -> dict:
    """Carry only each reviewed helper's required data, within the same cap."""
    key=stage.split('-',1)[0]
    if key=='rust': return {'toolchain':payload['toolchain']}
    result={'full_manifest':payload['full_manifest']}
    if key in {'source','cargo'}: result['patched_sha256']=payload['patched_sha256']
    if key=='source':
        result['files']={'src/linux/child_seccomp.rs':payload['files']['src/linux/child_seccomp.rs']}
    return result


def stage_script(controller: str, runtime: str, inventory: str, source: str,
                 payload: dict, operation: str, stage: str, seconds: int, *, host_binding_sha256: str) -> str:
    """One fixed stage per bounded transport, within the same worker lifecycle."""
    if operation not in OPERATIONS:
        raise build.Refusal('full_build_operation')
    if not build._binding_digest(host_binding_sha256): raise build.Refusal('build_binding_input')
    selected=[item for item in STAGES[operation] if item[0]==stage]
    if len(selected)!=1 or type(seconds) is not int or not 90<=seconds<=1600:
        raise build.Refusal('full_build_stage')
    _,key,network,maximum=selected[0]
    first=stage==STAGES[operation][0][0]
    unit=unit_source(source,payload,stage,min(maximum,seconds-70)-5)
    threshold=payload['full_manifest']['limits'][{
        'full-prepare':'required_free_before_prepare','full-fetch':'required_free_before_fetch',
        'full-source-reprepare':'required_free_before_build',
        'full-test':'required_free_before_build'}[operation]] if first else 0
    body=f'''
_operation_end=time.monotonic()+{seconds!r}
with mounted_store(deadline=_operation_end,host_binding_sha256={host_binding_sha256!r}):
    _before=build_inventory()
    if _before['store_available_bytes'] < {threshold!r}:
        raise RuntimeError('full_build_capacity')
    _runtime=install_runtime(existing_only=True) if {first!r} else None
    _seconds=min({maximum!r},int(_operation_end-time.monotonic()-65))
    if _seconds<10:
        raise RuntimeError('full_build_deadline')
    _observed=run_unit({unit!r},network={network!r},seconds=_seconds)
    _result=json.loads(_observed['stdout'])
    _after=build_inventory()
print(json.dumps({{'status':'full_stage_completed','operation':{operation!r},'stage':{stage!r},
    'result':_result,'runtime':_runtime,'inventory_before':_before,'inventory_after':_after,
    'unmounted_verified':True,'session_enabled':False,'full_runtime_qualified':False}}),flush=True)
'''
    return build._observed_script(controller+'\n'+(runtime if first else '')+'\n'+inventory,body)


def parse_stage(value: dict, operation: str, stage: str) -> dict:
    keys={'status','operation','stage','result','runtime','inventory_before','inventory_after',
          'unmounted_verified','session_enabled','full_runtime_qualified'}
    first=stage==STAGES[operation][0][0]
    if (type(value) is not dict or set(value)!=keys or value['status']!='full_stage_completed'
            or value['operation']!=operation or value['stage']!=stage
            or value['unmounted_verified'] is not True or value['session_enabled'] is not False
            or value['full_runtime_qualified'] is not False or type(value['result']) is not dict
            or not value['result'] or (not first and value['runtime'] is not None)):
        raise build.Refusal('full_build_stage_report')
    if first and (type(value['runtime']) is not dict or value['runtime'].get('status')!='runtime_ready'
                  or value['runtime'].get('installed_bytes')!=945234):
        raise build.Refusal('full_build_stage_runtime')
    for key in ('inventory_before','inventory_after'):
        build.parse_inventory(value[key]|{'unmounted_verified':True})
    return value


def parse_result(value: dict, operation: str) -> dict:
    keys={'status','operation','runtime','stages','inventory_before','inventory_after',
          'unmounted_verified','session_enabled','full_runtime_qualified'}
    if (type(value) is not dict or set(value)!=keys or value['status']!='full_operation_completed'
            or value['operation']!=operation or value['unmounted_verified'] is not True
            or value['session_enabled'] is not False or value['full_runtime_qualified'] is not False
            or value['runtime'].get('status')!='runtime_ready'
            or value['runtime'].get('installed_bytes')!=945234
            or set(value['stages'])!={stage[0] for stage in STAGES[operation]}
            or any(type(result) is not dict or not result for result in value['stages'].values())):
        raise build.Refusal('full_build_report')
    for key in ('inventory_before','inventory_after'):
        # Completion is emitted only after the context verified teardown. These
        # inventories themselves were taken while the same store was mounted.
        build.parse_inventory(value[key]|{'unmounted_verified':True})
    parse_stages(value['stages'],operation)
    return value


def parse_stages(stages: dict, operation: str, *, complete: bool = True) -> None:
    """Validate each completed prefix before any dependent command may start."""
    if type(stages) is not dict or operation not in OPERATIONS or not stages:
        raise build.Refusal('full_build_stages')
    ordered=[stage[0] for stage in STAGES[operation]]
    expected=ordered if complete else ordered[:len(stages)]
    if list(stages)!=expected: raise build.Refusal('full_build_stages')
    selected=manifest()
    def sha(value): return type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None
    for stage,result in stages.items():
        if type(result) is not dict: raise build.Refusal('full_build_stage_proof')
        if stage=='rust-verify':
            if (result.get('status')!='rust_verified' or type(result.get('files')) is not int
                    or result['files']<100 or 'release: 1.95.0\n' not in result.get('rustc','')):
                raise build.Refusal('full_build_rust_proof')
        elif stage=='compiler-download':
            if (result.get('status')!='compiler_downloaded' or result.get('package_count')!=15
                    or result.get('compressed_bytes')!=59383318 or result.get('authenticated_packages')!=0):
                raise build.Refusal('full_build_download_proof')
        elif stage in {'compiler-prepare','compiler-verify'}:
            if (result.get('status')!=('compiler_prepared' if stage=='compiler-prepare' else 'compiler_verified')
                    or result.get('package_count')!=15 or result.get('authenticated_packages')!=15
                    or not sha(result.get('compiler_tree_sha256'))
                    or type(result.get('expanded_bytes')) is not int or not 0<result['expanded_bytes']<=256*1024**2
                    or type(result.get('archive_sha256')) is not dict
                    or set(result['archive_sha256'])!={p['archive'] for p in selected['c_toolchain']['packages']}
                    or not all(sha(v) for v in result['archive_sha256'].values())):
                raise build.Refusal('full_build_compiler_proof')
            omitted=result.get('omitted_gdb_entries')
            expected={stem+suffix:('file' if suffix=='.so.0.0.0' else 'symlink')
                for stem in ('usr/lib/libcc1',
                    'usr/lib/gcc/aarch64-alpine-linux-musl/14.2.0/plugin/libcc1plugin',
                    'usr/lib/gcc/aarch64-alpine-linux-musl/14.2.0/plugin/libcp1plugin')
                for suffix in ('.so','.so.0','.so.0.0.0')}
            if (type(omitted) is not dict or set(omitted)!=set(expected)
                    or any(type(value) is not dict or set(value)!={'kind','sha256'}
                           or value['kind']!=expected[name] or not sha(value['sha256'])
                           for name,value in omitted.items())):
                raise build.Refusal('full_build_compiler_omissions')
        elif stage=='compiler-probe':
            if (result.get('status')!='compiler_probed' or result.get('static_arm64') is not True
                    or result.get('sentinel')!='openshell-private-c-static-checked'
                    or result.get('search_paths_verified') is not True or result.get('link_inputs_verified') is not True
                    or result.get('compiler_tree_sha256')!=stages['compiler-prepare']['compiler_tree_sha256']):
                raise build.Refusal('full_build_c_probe')
        elif stage in {'source-prepare','source-reprepare','source-verify','source-final'}:
            if (result.get('source_verified') is not True
                    or type(result.get('changed_files')) is not int or result['changed_files']!=4
                    or type(result.get('source_generation')) is not int or result['source_generation']!=2
                    or result.get('source')!='/var/lib/dotfiles-ai-openshell-build/store/work/full-source-2'
                    or result.get('network_test_original_sha256')!=NETWORK_TEST_ORIGINAL_SHA256
                    or result.get('network_test_sha256')!=NETWORK_TEST_SHA256
                    or result.get('source_blobs')!=2196 or result.get('upstream_commit')!=build.UPSTREAM
                    or result.get('upstream_tree_sha1')!=selected['upstream_tree_sha1']
                    or result.get('experimental_version')!=selected['experimental_version']
                    or result.get('patched_source_sha256')!=build.PATCHED_SHA
                    or result.get('derived_manifest_sha256')!=selected['source']['derived_manifest_sha256']
                    or result.get('derived_lock_sha256')!=selected['source']['derived_lock_sha256']
                    or not sha(result.get('archive_sha256')) or not sha(result.get('metadata_sha256'))
                    or result.get('session_enabled') is not False or result.get('full_runtime_qualified') is not False):
                raise build.Refusal('full_build_source_proof')
            if stage=='source-final' and result!=stages['source-verify']:
                raise build.Refusal('full_build_source_changed')
        elif stage in {'cargo-fetch','cargo-verify'}:
            if (result.get('status')!=('full_cargo_fetched' if stage=='cargo-fetch' else 'full_cargo_verified')
                    or (stage=='cargo-fetch' and result.get('locked_fetch') is not True)
                    or result.get('locked_registry_records')!=830
                    or type(result.get('crates')) is not int or not 1<=result['crates']<=830
                    or type(result.get('compressed_bytes')) is not int or not 0<result['compressed_bytes']<=512*1024**2
                    or type(result.get('expanded_bytes')) is not int or not 0<result['expanded_bytes']<=2*1024**3
                    or not sha(result.get('cache_sha256')) or result.get('session_enabled') is not False
                    or result.get('full_runtime_qualified') is not False):
                raise build.Refusal('full_build_cache_proof')
            if stage=='cargo-verify':
                protoc=result.get('protoc',{})
                if protoc.get('version')!='31.1' or not sha(protoc.get('binary_sha256')):
                    raise build.Refusal('full_build_protoc_proof')
        elif stage=='cargo-test':
            layout=result.get('binary_layout')
            if (type(layout) is not dict or set(layout)!={'link_count','companion'}
                    or type(layout['link_count']) is not int or layout['link_count'] not in (1,2)
                    or (layout['link_count']==1 and layout['companion'] is not None)
                    or (layout['link_count']==2 and (type(layout['companion']) is not str
                        or re.fullmatch(r'openshell_sandbox-[a-f0-9]{16}',layout['companion']) is None))):
                raise build.Refusal('full_build_binary_layout')
            if (result.get('status')!='full_cargo_tested' or result.get('static_arm64') is not True
                    or result.get('experimental_version')!=selected['experimental_version']
                    or result.get('patched_source_sha256')!=build.PATCHED_SHA
                    or result.get('derived_lock_sha256')!=selected['source']['derived_lock_sha256']
                    or not sha(result.get('binary_sha256')) or not sha(result.get('test_binary_sha256'))
                    or 'openshell-child-unix-denial-checked' not in result.get('filtered_stdout','')
                    or result.get('full_runtime_qualified') is not False or result.get('session_enabled') is not False):
                raise build.Refusal('full_build_test_proof')


def qualify(selection: create.CreateSelection, operation: str) -> build.BuildObservation:
    if operation not in OPERATIONS: raise build.Refusal('full_build_operation')
    controller=build.read_source(build.FIXTURES/'guest_build_storage.py').decode()
    runtime=build.read_source(build.FIXTURES/'guest_runtime.py').decode()
    inventory=build.read_source(build.FIXTURES/'guest_build_inventory.py').decode()
    sources=capture_sources(operation)
    # Capturing local fixture inputs is read-only. The source patch's bounded
    # temporary application remains in the already admitted controller cache.
    def inspect(selected,anchor,deadline):
        guest._inspect_guest(selected,anchor,deadline)
        binding=build.host_binding_sha256(selected,anchor)
        bundle=load_bundle(selected.storage.cache_path/'_tmp')
        stages={};programs={};before=after=runtime_result=None
        for stage,key,network,maximum in STAGES[operation]:
            seconds=min(maximum+100,1600,int(create._remaining(deadline,1700))-15)
            script=stage_script(controller,runtime,inventory,sources[key],bundle.payload,operation,stage,seconds,
                                host_binding_sha256=binding)
            wire=build.encode_program(script)
            argv=[str(anchor.sources[0].identity.path),'shell','--tty=false','--start=false',
                  '--workdir','/','q','--','/usr/bin/sudo','-n','/usr/bin/python3','-I','-c',wire]
            raw=create._command(selected,argv,deadline,'guest_full_build',seconds+30)
            observed=parse_stage(create._json(raw),operation,stage)
            stages[stage]=observed['result'];programs[stage]=hashlib.sha256(script.encode()).hexdigest()
            parse_stages(stages,operation,complete=False)
            if before is None:
                before=observed['inventory_before'];runtime_result=observed['runtime']
            after=observed['inventory_after']
        result=parse_result({'status':'full_operation_completed','operation':operation,
            'runtime':runtime_result,'stages':stages,'inventory_before':before,'inventory_after':after,
            'unmounted_verified':True,'session_enabled':False,'full_runtime_qualified':False},operation)
        result['source_hashes']=bundle.source_hashes|{
            name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()}
        result['program_sha256']=programs
        result['controller_sha256']=hashlib.sha256(controller.encode()).hexdigest()
        return result
    lifecycle,result=boot._qualify_with_inspection(selection,inspect,qualification_seconds=1800)
    return build.BuildObservation(operation,lifecycle,result)
