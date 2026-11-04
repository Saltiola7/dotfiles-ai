"""Opt-in, credential-free storage preparation and patched-module kernel proof.

These test-only operations do not install an agent launcher or enable sessions.
Every native operation reuses the qualified exact-worker admission and shutdown.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import tempfile
import textwrap
import zlib

import probe_openshell_guest_inventory as guest
import probe_openshell_storage_boot as boot
import probe_openshell_storage_create as create
from probe_openshell_storage import Refusal


FIXTURES=Path(__file__).parent/'fixtures/openshell_runtime'
PATCHED_SHA='57a91bdc412ceb124da0b409f841420de35b692b07db0e806cd888c3ab7a3bb1'
UPSTREAM='5d25211b25a8fc887e8d5c606d57d6ab22f1d76c'


@dataclass(frozen=True)
class Bundle:
    payload: dict
    source_hashes: dict[str,str]


@dataclass(frozen=True)
class BuildObservation:
    operation: str
    lifecycle: boot.BootObservation
    result: dict
    session_enabled: bool = False


def host_binding_sha256(selection: create.CreateSelection, anchor: boot._Anchors) -> str:
    """Project persistent identities from fresh admission; never admit an operation."""
    if type(selection) is not create.CreateSelection or type(anchor) is not boot._Anchors:
        raise Refusal('build_host_binding')
    storage=selection.storage
    storage_record={name:getattr(storage,name) for name in (
        'profile','pilot_root','run_root','image_path','image_device','image_inode',
        'container_uuid','runtime_uuid','cache_uuid')}
    for name in ('pilot_root','run_root','image_path'):
        storage_record[name]=str(storage_record[name])
    worker=anchor.worker;disk=anchor.disk.identity
    record={'schema_version':1,'storage':storage_record,
        'worker':{'run_id':worker.run_id,'name':worker.name,'path':str(storage.runtime_path/worker.name),
                  'volume_uuid':storage.runtime_uuid,'inode':worker.inode},
        'disk':{'path':str(disk.path),'volume_uuid':storage.runtime_uuid,
                **{name:getattr(disk,name) for name in ('inode','mode','uid','links')}}}
    canonical=json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    return hashlib.sha256(b'dotfiles-ai.openshell.build-store-host-binding.v1\0'+canonical).hexdigest()


def _binding_digest(value: str) -> bool:
    return type(value) is str and re.fullmatch(r'[a-f0-9]{64}',value) is not None


def read_source(path: Path) -> bytes:
    return create._file(path,512*1024)[1]


def load_bundle(temporary_parent: Path) -> Bundle:
    """Apply only the verified single-file patch in bounded controller cache."""
    manifest_raw=read_source(FIXTURES/'harness/manifest.json')
    manifest=create._json(manifest_raw)
    generated=manifest['generated_source'];toolchain=manifest['toolchain']
    if (generated['upstream_commit']!=UPSTREAM or generated['patched_sha256']!=PATCHED_SHA
            or toolchain['version']!='1.95.0' or toolchain['host']!='aarch64-unknown-linux-musl'):
        raise Refusal('build_source_selection')
    files={};hashes={'harness/manifest.json':hashlib.sha256(manifest_raw).hexdigest()}
    if {item['path'] for item in manifest['fixture_files']}!={'Cargo.toml','Cargo.lock','src/lib.rs'}:
        raise Refusal('build_source_set')
    for item in manifest['fixture_files']:
        raw=read_source(FIXTURES/'harness'/item['path']);digest=hashlib.sha256(raw).hexdigest()
        if digest!=item['sha256'] or len(raw)!=item['size_bytes']: raise Refusal('build_source_identity')
        files[item['path']]=raw.decode();hashes['harness/'+item['path']]=digest
    preimage=read_source(FIXTURES/'patches/upstream/child_seccomp.rs')
    patch=read_source(FIXTURES/'patches/child-unix-sockets.patch')
    if (hashlib.sha256(preimage).hexdigest()!=generated['preimage_sha256']
            or hashlib.sha256(patch).hexdigest()!=generated['patch_sha256']
            or generated['patch_target']!='crates/openshell-sandbox/src/linux/child_seccomp.rs'):
        raise Refusal('build_patch_identity')
    with tempfile.TemporaryDirectory(prefix='kernel-source-',dir=temporary_parent) as name:
        root=Path(name);target=root/generated['patch_target'];target.parent.mkdir(parents=True)
        target.write_bytes(preimage);patch_path=root/'source.patch';patch_path.write_bytes(patch)
        result=create._run_bounded_command(['/usr/bin/git','apply','--whitespace=error-all',str(patch_path)],
            cwd=root,env={'PATH':'/usr/bin:/bin','HOME':str(root),'GIT_CONFIG_NOSYSTEM':'1','LC_ALL':'C'},
            timeout=10,limit=1024*1024)
        if result.returncode: raise Refusal('build_patch_application')
        patched=target.read_bytes()
    if hashlib.sha256(patched).hexdigest()!=PATCHED_SHA: raise Refusal('build_patch_result')
    files['src/linux/child_seccomp.rs']=patched.decode()
    hashes['patches/child-unix-sockets.patch']=hashlib.sha256(patch).hexdigest()
    artifacts=[{'archive':a['filename'],'bytes':a['size_bytes'],'url':a['url'],'sha256':a['sha256']}
               for a in toolchain['archives']]
    expected={f'{part}-1.95.0-aarch64-unknown-linux-musl.tar.xz' for part in ('cargo','rustc','rust-std')}
    if len(artifacts)!=3 or {a['archive'] for a in artifacts}!=expected: raise Refusal('build_toolchain_set')
    payload={'toolchain':{'version':toolchain['version'],'host':toolchain['host'],
                         'commit':toolchain['source_commit'],'artifacts':artifacts},
             'files':files,'patched_sha256':PATCHED_SHA}
    if len(json.dumps(payload).encode())>128*1024: raise Refusal('build_payload_limit')
    return Bundle(payload,hashes)


def _observed_script(controller: str, body: str) -> str:
    """Preserve bounded diagnostics in the private native runner on refusal."""
    return controller + '\ntry:\n' + textwrap.indent(body, '    ') + """
except Refusal as _failure:
    for _stream in (_failure.stdout, _failure.stderr):
        if _stream:
            print(_stream[-65536:].decode(errors='replace'),file=sys.stderr,flush=True)
    raise
"""


def encode_program(script: str) -> str:
    """Transport only the fixed assembled program within Linux argument limits."""
    if type(script) is not str:
        raise Refusal('guest_program_bound')
    raw=script.encode()
    if not 0<len(raw)<=256*1024:
        raise Refusal('guest_program_bound')
    encoded=base64.b64encode(zlib.compress(raw,9)).decode('ascii')
    if len(encoded)>60*1024:
        raise Refusal('guest_transport_bound')
    expected=hashlib.sha256(raw).hexdigest()
    return f"""import base64 as _guest_b64, zlib as _guest_zlib, hashlib as _guest_hash
_guest_decoder=_guest_zlib.decompressobj()
_guest_program=_guest_decoder.decompress(_guest_b64.b64decode('{encoded}'),{len(raw)+1})
if (len(_guest_program)!={len(raw)} or not _guest_decoder.eof or _guest_decoder.unused_data or _guest_decoder.unconsumed_tail or _guest_hash.sha256(_guest_program).hexdigest()!='{expected}'):
    raise RuntimeError('guest_program_identity')
exec(compile(_guest_program,'<closed-openshell-guest-program>','exec'))
"""


def prepare_script(controller: str) -> str:
    return _observed_script(controller,'print(json.dumps(prepare(),sort_keys=True),flush=True)\n')


def binding_script(controller: str, seconds: int, *, host_binding_sha256: str) -> str:
    if not _binding_digest(host_binding_sha256) or type(seconds) is not int or not 1<=seconds<=300:
        raise Refusal('build_binding_input')
    return _observed_script(controller,f'''
_binding = record_stable_binding(host_binding_sha256={host_binding_sha256!r},
                                 deadline=time.monotonic()+{seconds!r})
print(json.dumps(_binding,sort_keys=True),flush=True)
''')


def parse_bound(result: dict, expected_host_binding: str) -> dict:
    keys={'schema_version','status','host_binding_sha256','legacy_receipt_sha256','binding_sha256',
          'image_bytes','unmounted_verified','session_enabled','historical_outer_identity_verified'}
    if (type(result) is not dict or set(result)!=keys
            or type(result['schema_version']) is not int or result['schema_version']!=1
            or result['status']!='storage_bound' or not _binding_digest(expected_host_binding)
            or result['host_binding_sha256']!=expected_host_binding
            or not all(_binding_digest(result[name]) for name in
                       ('host_binding_sha256','legacy_receipt_sha256','binding_sha256'))
            or type(result['image_bytes']) is not int or result['image_bytes']!=8*1024**3
            or result['unmounted_verified'] is not True or result['session_enabled'] is not False
            or result['historical_outer_identity_verified'] is not False):
        raise Refusal('build_binding_report')
    return result


def inventory_script(controller: str, inventory: str, seconds: int, *, host_binding_sha256: str) -> str:
    if not _binding_digest(host_binding_sha256): raise Refusal('build_binding_input')
    return _observed_script(controller+'\n'+inventory,f'''
with mounted_store(deadline=time.monotonic()+{seconds!r},host_binding_sha256={host_binding_sha256!r}):
    _inventory = build_inventory()
_inventory['unmounted_verified'] = True
print(json.dumps(_inventory,sort_keys=True),flush=True)
''')


def parse_inventory(result: dict) -> dict:
    counts={'entry_count','unique_inode_count','logical_bytes','allocated_bytes',
            'shared_allocated_bytes','hardlink_entries','symlink_entries'}
    keys={'schema_version','status','image_bytes','store_capacity_bytes','store_free_bytes',
          'store_available_bytes','root_free_bytes','work','entries','totals','build_enabled',
          'session_enabled','unmounted_verified'}
    def numbers(value,names):
        return all(type(value.get(key)) is int and 0<=value[key]<2**63 for key in names)
    if (type(result) is not dict or set(result)!=keys
            or type(result['schema_version']) is not int or result['schema_version']!=1
            or result['status']!='inventoried' or result['image_bytes']!=8*1024**3
            or not numbers(result,{'image_bytes','store_capacity_bytes','store_free_bytes','store_available_bytes','root_free_bytes'})
            or not 6*1024**3<result['store_capacity_bytes']<=result['image_bytes']
            or not 0<=result['store_available_bytes']<=result['store_free_bytes']<=result['store_capacity_bytes']
            or result['work']!='/var/lib/dotfiles-ai-openshell-build/store/work'
            or result['build_enabled'] is not False or result['session_enabled'] is not False
            or result['unmounted_verified'] is not True):
        raise Refusal('build_inventory_report')
    totals=result['totals'];entries=result['entries']
    if (type(totals) is not dict or set(totals)!=counts|{'work_root_allocated_bytes'}
            or not numbers(totals,set(totals)) or not 1<=totals['unique_inode_count']<=totals['entry_count']<=200000
            or not totals['work_root_allocated_bytes']<=totals['allocated_bytes']<=result['image_bytes']
            or totals['shared_allocated_bytes']>totals['allocated_bytes']
            or type(entries) is not list or len(entries)>128):
        raise Refusal('build_inventory_report')
    names=set();entry_count=1
    fields=counts|{'name','kind','known','device','inode','uid','gid','mode','nlink','exclusive_allocated_bytes'}
    for entry in entries:
        if (type(entry) is not dict or set(entry)!=fields
                or not numbers(entry,fields-{'name','kind','known'})
                or type(entry['name']) is not str or not 0<len(entry['name'])<=255
                or entry['name'] in {'.','..'} or '/' in entry['name'] or '\0' in entry['name']
                or entry['name'] in names or entry['kind'] not in {'directory','file','symlink'}
                or type(entry['known']) is not bool or entry['nlink']<1 or entry['inode']<1
                or entry['mode']&0o170000!={'directory':0o040000,'file':0o100000,'symlink':0o120000}[entry['kind']]
                or not 1<=entry['unique_inode_count']<=entry['entry_count']<=200000
                or entry['allocated_bytes']>result['image_bytes']
                or entry['exclusive_allocated_bytes']+entry['shared_allocated_bytes']!=entry['allocated_bytes']):
            raise Refusal('build_inventory_report')
        names.add(entry['name']);entry_count+=entry['entry_count']
    if entry_count!=totals['entry_count']:
        raise Refusal('build_inventory_report')
    return result


def parse_prepared(result: dict) -> dict:
    keys={'schema_version','status','image_bytes','fixture_bytes','fixture_written_bytes',
          'escape_verified','enospc_verified','unmounted_verified','work','allocation_enabled'}
    if (type(result) is not dict or set(result)!=keys
            or type(result['schema_version']) is not int or result['schema_version']!=1
            or result['status']!='prepared' or type(result['image_bytes']) is not int or result['image_bytes']!=8*1024**3
            or type(result['fixture_bytes']) is not int or result['fixture_bytes']!=64*1024**2
            or type(result['fixture_written_bytes']) is not int or not 0<result['fixture_written_bytes']<=65*1024**2
            or any(result[key] is not True for key in ('escape_verified','enospc_verified','unmounted_verified'))
            or result['allocation_enabled'] is not False
            or result['work']!='/var/lib/dotfiles-ai-openshell-build/store/work'):
        raise Refusal('build_storage_report')
    return result


def payload_source(payload: dict) -> str:
    """Carry bounded reviewed JSON as data, preserving the unit source ceiling."""
    raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    if not 0<len(raw)<=128*1024:
        raise Refusal('build_payload_limit')
    encoded=base64.b64encode(zlib.compress(raw,9)).decode('ascii')
    expected=hashlib.sha256(raw).hexdigest()
    return f"""import base64 as _payload_b64, zlib as _payload_zlib
_payload_decoder=_payload_zlib.decompressobj()
_payload_raw=_payload_decoder.decompress(_payload_b64.b64decode('{encoded}'),{len(raw)+1})
if (len(_payload_raw)!={len(raw)} or not _payload_decoder.eof or _payload_decoder.unused_data or _payload_decoder.unconsumed_tail or hashlib.sha256(_payload_raw).hexdigest()!='{expected}'):
    raise RuntimeError('build_payload_identity')
_stage_payload=json.loads(_payload_raw)
"""


def kernel_script(controller: str, builder: str, payload: dict, seconds: int, *, runtime: str,
                  host_binding_sha256: str, resume: bool = False) -> str:
    if not _binding_digest(host_binding_sha256): raise Refusal('build_binding_input')
    builder+='\n'+payload_source(payload)
    stages=[('resume',False,300),('test',False,480)] if resume else [
        ('download',True,420),('setup',False,300),('fetch',True,240),('test',False,480)]
    return _observed_script(controller+"\n"+runtime,f'''
_builder_source = {builder!r}
_operation_end = time.monotonic() + {seconds!r}
_stages = {{}}
with mounted_store(deadline=_operation_end,host_binding_sha256={host_binding_sha256!r}):
    _runtime = install_runtime(existing_only=True) if {resume!r} else install_runtime()
    print(json.dumps({{'stage':'runtime','result':_runtime}}),file=sys.stderr,flush=True)
    for _operation, _network, _maximum in {stages!r}:
        _seconds = min(_maximum, int(_operation_end-time.monotonic()-65))
        if _seconds <= 0:
            raise RuntimeError('kernel_preparation_deadline')
        _script = _builder_source + '\\nstage(' + repr(_operation) + ',_stage_payload,' + repr(_seconds-5) + ',resume_run={resume!r})\\n'
        _observed = run_unit(_script, network=_network, seconds=_seconds)
        _stages[_operation] = json.loads(_observed['stdout'])
        print(json.dumps({{'stage':_operation,'finished':True,'result':_stages[_operation]}}),file=sys.stderr,flush=True)
print(json.dumps({{'status':'kernel_tested','runtime':_runtime,'stages':_stages,'session_enabled':False,'full_runtime_qualified':False}}),flush=True)
''')


def qualify(selection: create.CreateSelection, operation: str) -> BuildObservation:
    if operation in {'full-prepare','full-fetch','full-test'}:
        import probe_openshell_full_build as full
        return full.qualify(selection,operation)
    if operation not in {'prepare','bind-storage','inventory','kernel','kernel-resume'}: raise Refusal('build_operation')
    # Capture reviewed source before any VM start. The body is fixed per
    # operation; neither selection JSON nor CLI accepts commands or scripts.
    controller=read_source(FIXTURES/'guest_build_storage.py').decode()
    kernel=operation in {'kernel','kernel-resume'}
    inventory=read_source(FIXTURES/'guest_build_inventory.py').decode() if operation=='inventory' else ''
    builder=read_source(FIXTURES/'guest_harness.py').decode() if kernel else ''
    runtime=read_source(FIXTURES/'guest_runtime.py').decode() if kernel else ''
    unwind=read_source(FIXTURES/'guest_unwind.py').decode() if kernel else ''
    resume_source=read_source(FIXTURES/'guest_resume.py').decode() if operation=='kernel-resume' else ''
    if kernel: builder+='\n'+unwind+'\n'+resume_source
    def inspect(selected, anchor, deadline):
        observed=guest._inspect_guest(selected,anchor,deadline)
        if operation=='prepare' and observed.free_bytes<12*1024**3: raise Refusal('guest_build_reserve')
        binding=host_binding_sha256(selected,anchor) if operation!='prepare' else None
        if operation=='prepare': script=prepare_script(controller)
        elif operation=='bind-storage':
            script=binding_script(controller,min(300,int(create._remaining(deadline,360))-15),host_binding_sha256=binding)
        elif operation=='inventory':
            script=inventory_script(controller,inventory,min(300,int(create._remaining(deadline,360))-15),
                                    host_binding_sha256=binding)
        else:
            bundle=load_bundle(selected.storage.cache_path/'_tmp')
            seconds=int(create._remaining(deadline,1200))-15
            if seconds<120: raise Refusal('build_deadline')
            script=kernel_script(controller,builder,bundle.payload,seconds,runtime=runtime,
                                 host_binding_sha256=binding,resume=operation=='kernel-resume')
        program_sha256=hashlib.sha256(script.encode()).hexdigest()
        wire=encode_program(script)
        argv=[str(anchor.sources[0].identity.path),'shell','--tty=false','--start=false',
              '--workdir','/','q','--','/usr/bin/sudo','-n','/usr/bin/python3','-I','-c',wire]
        raw=create._command(selected,argv,deadline,'guest_build',1250 if kernel else 450)
        result=create._json(raw)
        if operation=='prepare': parse_prepared(result)
        elif operation=='bind-storage': parse_bound(result,binding)
        elif operation=='inventory':
            parse_inventory(result)
            result['inventory_sha256']=hashlib.sha256(inventory.encode()).hexdigest()
        if kernel:
            expected_stages={'resume','test'} if operation=='kernel-resume' else {'download','setup','fetch','test'}
            if (result.get('status')!='kernel_tested' or result.get('session_enabled') is not False
                    or result.get('full_runtime_qualified') is not False or set(result.get('stages',{}))!=expected_stages):
                raise Refusal('kernel_report')
            if (result.get('runtime',{}).get('status')!='runtime_ready'
                    or result['runtime'].get('installed_bytes')!=945234):
                raise Refusal('kernel_runtime')
            test=result['stages']['test']['result']
            if (test.get('static_arm64') is not True or test.get('patched_source_sha256')!=PATCHED_SHA
                    or test.get('kernel_only') is not True or test.get('full_runtime_qualified') is not False
                    or 'openshell-child-unix-denial-checked' not in test.get('filtered_stdout','')):
                raise Refusal('kernel_proof')
            result['source_hashes']=bundle.source_hashes
            result['builder_sha256']=hashlib.sha256(builder.encode()).hexdigest()
            result['runtime_sha256']=hashlib.sha256(runtime.encode()).hexdigest()
            result['unwind_sha256']=hashlib.sha256(unwind.encode()).hexdigest()
            if resume_source: result['resume_sha256']=hashlib.sha256(resume_source.encode()).hexdigest()
        result['program_sha256']=program_sha256
        result['controller_sha256']=hashlib.sha256(controller.encode()).hexdigest()
        return result
    lifecycle,result=boot._qualify_with_inspection(selection,inspect,qualification_seconds=1800 if kernel else 900)
    return BuildObservation(operation,lifecycle,result)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',required=True,type=Path)
    parser.add_argument('--operation',required=True,choices=('prepare','bind-storage','inventory','kernel','kernel-resume',
                                                           'full-prepare','full-fetch','full-test'))
    args=parser.parse_args()
    try:
        selected=create.parse_selection(create.private_file(args.selection))
        observed=qualify(selected,args.operation)
        report={'status':'guest_build_stopped','operation':args.operation,'result':observed.result,
                'stopped_verified':observed.lifecycle.stopped_verified,'shutdown_uncertain':False,
                'session_enabled':False,'full_runtime_qualified':False}
    except boot.BootRefusal as error:
        report={'status':'refused','blockers':[str(error)],'vm_start_requested':error.start_requested,
                'stop_requested':error.stop_requested,'stopped_verified':error.stopped_verified,
                'shutdown_uncertain':error.shutdown_uncertain,'session_enabled':False}
    except (Refusal,OSError,ValueError,KeyError,create.CommandRefusal):
        report={'status':'refused','blockers':['build_selection'],'vm_start_requested':False,
                'shutdown_uncertain':False,'session_enabled':False}
    print(json.dumps(report,sort_keys=True))
    return 0 if report['status']=='guest_build_stopped' else 1


if __name__=='__main__':
    raise SystemExit(main())
