"""Opt-in, credential-free storage preparation and patched-module kernel proof.

These test-only operations do not install an agent launcher or enable sessions.
Every native operation reuses the qualified exact-worker admission and shutdown.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import textwrap

import probe_openshell_guest_inventory as guest
import probe_openshell_storage_boot as boot
import probe_openshell_storage_create as create
from probe_openshell_storage import Refusal


FIXTURES=Path(__file__).parent/'fixtures/openshell_runtime'
PATCHED_SHA='259e77596f3f70ee28bdd8672f4747f3462f4c727b609e92d782cf749782ccb3'
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


def prepare_script(controller: str) -> str:
    return _observed_script(controller,'print(json.dumps(prepare(),sort_keys=True),flush=True)\n')


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


def kernel_script(controller: str, builder: str, payload: dict, seconds: int, *, runtime: str) -> str:
    return _observed_script(controller+"\n"+runtime,f'''
_builder_source = {builder!r}
_payload = {payload!r}
_operation_end = time.monotonic() + {seconds!r}
_stages = {{}}
with mounted_store(deadline=_operation_end):
    _runtime = install_runtime()
    print(json.dumps({{'stage':'runtime','result':_runtime}}),file=sys.stderr,flush=True)
    for _operation, _network, _maximum in [('download', True, 420), ('setup', False, 300), ('fetch', True, 240), ('test', False, 480)]:
        _seconds = min(_maximum, int(_operation_end-time.monotonic()-65))
        if _seconds <= 0:
            raise RuntimeError('kernel_preparation_deadline')
        _script = _builder_source + '\\nstage(' + repr(_operation) + ',' + repr(_payload) + ',' + repr(_seconds-5) + ')\\n'
        _observed = run_unit(_script, network=_network, seconds=_seconds)
        _stages[_operation] = json.loads(_observed['stdout'])
        print(json.dumps({{'stage':_operation,'finished':True}}),file=sys.stderr,flush=True)
print(json.dumps({{'status':'kernel_tested','runtime':_runtime,'stages':_stages,'session_enabled':False,'full_runtime_qualified':False}}),flush=True)
''')


def qualify(selection: create.CreateSelection, operation: str) -> BuildObservation:
    if operation not in {'prepare','kernel'}: raise Refusal('build_operation')
    # Capture reviewed source before any VM start. The body is fixed per
    # operation; neither selection JSON nor CLI accepts commands or scripts.
    controller=read_source(FIXTURES/'guest_build_storage.py').decode()
    builder=read_source(FIXTURES/'guest_harness.py').decode() if operation=='kernel' else ''
    runtime=read_source(FIXTURES/'guest_runtime.py').decode() if operation=='kernel' else ''
    def inspect(selected, anchor, deadline):
        observed=guest._inspect_guest(selected,anchor,deadline)
        if operation=='prepare' and observed.free_bytes<12*1024**3: raise Refusal('guest_build_reserve')
        if operation=='prepare': script=prepare_script(controller)
        else:
            bundle=load_bundle(selected.storage.cache_path/'_tmp')
            seconds=int(create._remaining(deadline,1200))-15
            if seconds<120: raise Refusal('build_deadline')
            script=kernel_script(controller,builder,bundle.payload,seconds,runtime=runtime)
        argv=[str(anchor.sources[0].identity.path),'shell','--tty=false','--start=false',
              '--workdir','/','q','--','/usr/bin/sudo','-n','/usr/bin/python3','-I','-c',script]
        raw=create._command(selected,argv,deadline,'guest_build',450 if operation=='prepare' else 1250)
        result=create._json(raw)
        if operation=='prepare': parse_prepared(result)
        if operation=='kernel':
            if (result.get('status')!='kernel_tested' or result.get('session_enabled') is not False
                    or result.get('full_runtime_qualified') is not False or set(result.get('stages',{}))!={'download','setup','fetch','test'}):
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
        result['controller_sha256']=hashlib.sha256(controller.encode()).hexdigest()
        return result
    lifecycle,result=boot._qualify_with_inspection(selection,inspect,qualification_seconds=900 if operation=='prepare' else 1800)
    return BuildObservation(operation,lifecycle,result)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',required=True,type=Path)
    parser.add_argument('--operation',required=True,choices=('prepare','kernel'))
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
