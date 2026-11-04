"""Fixed unprivileged harness stages; executed only in the capped guest service.

No command-line script or arbitrary artifact URL is accepted. The host assembles
the source-bound payload; guest root never executes downloaded project code.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import stat
import struct
import subprocess
import tarfile
import time
import urllib.request


WORK = Path('/var/lib/dotfiles-ai-openshell-build/store/work')
TOOLCHAIN = 'toolchain-unwind-1'
TARGET = 'target'
HOST = 'aarch64-unknown-linux-musl'
DEADLINE = 0.0
OUTPUT_LIMIT = 1024 * 1024
SENTINEL = 'openshell-child-unix-denial-checked'


def remaining(maximum=60):
    value = DEADLINE - time.monotonic()
    if value <= 0:
        raise RuntimeError('harness_deadline')
    return min(value, maximum)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024*1024):
            value.update(chunk)
    return value.hexdigest()


def command(argv, *, cwd=None, maximum=120, environment=None, umask=-1):
    if type(umask) is not int or umask not in (-1,0o066):
        raise RuntimeError('harness_command_umask')
    end = time.monotonic() + remaining(maximum)
    output, error = bytearray(), bytearray()
    process = subprocess.Popen(argv, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                               umask=umask)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, output)
            selector.register(process.stderr, selectors.EVENT_READ, error)
            while selector.get_map():
                wait = min(remaining(), end-time.monotonic())
                if wait <= 0: raise RuntimeError('harness_command_timeout')
                for key, _ in selector.select(wait):
                    chunk = os.read(key.fd, min(65536, OUTPUT_LIMIT+1-len(output)-len(error)))
                    if chunk: key.data.extend(chunk)
                    else: selector.unregister(key.fileobj)
                    if len(output)+len(error)>OUTPUT_LIMIT: raise RuntimeError('harness_output_limit')
            process.wait(timeout=max(.001,min(remaining(),end-time.monotonic())))
    finally:
        try:
            if process.poll() is None:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait(timeout=2)
        finally:
            process.stdout.close(); process.stderr.close()
    if process.returncode:
        # These fixed tool diagnostics contain no credentials; retain bounded
        # failure output for the native evidence, never declare a partial pass.
        print(error.decode(errors='replace')[-32768:], flush=True)
        print(output.decode(errors='replace')[-32768:], flush=True)
        raise RuntimeError('harness_command_failed')
    return bytes(output), bytes(error)


def archive_members(tar, root, maximum):
    total = 0
    names = set()
    selected = []
    for member in tar:
        name = PurePosixPath(member.name)
        if (name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] != root
                or len(member.name) > 512 or member.name in names
                or not (member.isfile() or member.isdir() or member.issym() or member.islnk())):
            raise RuntimeError('harness_archive_path')
        if member.issym() or member.islnk():
            target = PurePosixPath(member.linkname)
            if target.is_absolute(): raise RuntimeError('harness_archive_link')
            parts = list(name.parent.parts if member.issym() else ())
            for part in target.parts:
                if part == '..':
                    if len(parts) <= 1: raise RuntimeError('harness_archive_link')
                    parts.pop()
                elif part != '.': parts.append(part)
            if not parts or parts[0] != root: raise RuntimeError('harness_archive_link')
        total += member.size
        if total > maximum or len(selected) >= 30000: raise RuntimeError('harness_archive_budget')
        names.add(member.name); selected.append(member)
    return selected, total


def extract_archive(source, destination, root, *, maximum):
    with tarfile.open(source, 'r:xz') as tar:
        members, total = archive_members(tar, root, maximum)
        destination.mkdir(mode=0o700)
        tar.extractall(destination, members=members, filter='data')
        return total


def verify_static_arm64(path):
    with path.open('rb') as stream:
        head = stream.read(64)
        if len(head)!=64 or head[:7]!=b'\x7fELF\x02\x01\x01': raise RuntimeError('harness_elf')
        values=struct.unpack_from('<HHIQQQIHHHHHH',head,16)
        kind,machine,version,_,phoff,_,_,ehsize,phsize,phnum,_,_,_=values
        if (kind not in (2,3) or machine!=183 or version!=1 or ehsize!=64
                or phsize!=56 or not 0<phnum<=128 or phoff<64 or phoff>1024*1024):
            raise RuntimeError('harness_elf')
        stream.seek(phoff)
        dynamic=[]
        file_size=os.fstat(stream.fileno()).st_size
        for _ in range(phnum):
            header=stream.read(phsize)
            if len(header)!=phsize or struct.unpack_from('<I',header)[0]==3:
                raise RuntimeError('harness_dynamic_or_invalid_elf')
            fields=struct.unpack('<IIQQQQQQ',header)
            if fields[0]==2:
                offset,size=fields[2],fields[5]
                if dynamic or not 0<size<=65536 or size%16 or offset+size>file_size:
                    raise RuntimeError('harness_dynamic_or_invalid_elf')
                dynamic.append((offset,size))
        # Dependency-free static PIE may contain PT_DYNAMIC relocations. Reject
        # DT_NEEDED even without an interpreter; require bounded DT_NULL ending.
        for offset,size in dynamic:
            stream.seek(offset)
            for _ in range(size//16):
                tag,_=struct.unpack('<qQ',stream.read(16))
                if tag==1: raise RuntimeError('harness_dynamic_or_invalid_elf')
                if tag==0: break
            else: raise RuntimeError('harness_dynamic_or_invalid_elf')
    return digest(path)


def environment(*, rust=True):
    prefix=WORK/TOOLCHAIN
    result = {'PATH':str(prefix/'bin')+':/usr/bin:/bin','LC_ALL':'C',
            'HOME':str(WORK/'home'),'CARGO_HOME':str(WORK/'cargo'),
            'RUSTUP_HOME':str(WORK/'rustup'),'XDG_CACHE_HOME':str(WORK/'cache'),
            'TMPDIR':str(WORK/'tmp'),'CARGO_TARGET_DIR':str(WORK/TARGET),
            'CARGO_INCREMENTAL':'0','CARGO_BUILD_JOBS':'2','CARGO_TERM_COLOR':'never',
            'RUSTC':str(prefix/'bin/rustc'),'RUSTDOC':str(prefix/'bin/rustdoc'),
            'RUSTFLAGS':f'-C linker={prefix}/lib/rustlib/{HOST}/bin/rust-lld -C linker-flavor=ld.lld -C link-self-contained=yes'}
    if rust:
        result['LD_LIBRARY_PATH']=str(prefix/'lib')
    return result


def validate_context():
    if os.getuid()!=65534 or os.getgid()!=65534 or os.uname().machine!='aarch64':
        raise RuntimeError('harness_identity')
    if not all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (1,2)):
        raise RuntimeError('harness_log_route')
    device=WORK.stat().st_dev
    for path in (WORK,Path('/tmp'),Path('/var/tmp')):
        if path.stat().st_dev!=device: raise RuntimeError('harness_temp_route')
    for name in ('home','cargo','rustup','cache','tmp','downloads','target'):
        path=WORK/name
        if path.exists() and (path.is_symlink() or not path.is_dir()): raise RuntimeError('harness_directory')
        path.mkdir(mode=0o700,exist_ok=True)
        if path.stat().st_dev!=device: raise RuntimeError('harness_cache_route')


def download(item):
    name=item['archive'];url=item['url']
    if (Path(name).name!=name or url!='https://static.rust-lang.org/dist/2026-04-16/'+name
            or not name.endswith('-1.95.0-'+HOST+'.tar.xz')
            or not 0<item['bytes']<=128*1024**2):
        raise RuntimeError('harness_artifact')
    target=WORK/'downloads'/name
    if target.exists():
        if target.is_symlink() or target.stat().st_size!=item['bytes'] or digest(target)!=item['sha256']:
            raise RuntimeError('harness_retained_artifact')
        return
    partial=target.with_suffix('.partial')
    value=hashlib.sha256();count=0
    with partial.open('xb') as output:
        with urllib.request.urlopen(url, timeout=remaining(30)) as response:
            if response.url.split(':',1)[0]!='https': raise RuntimeError('harness_download_transport')
            while True:
                remaining()
                chunk=response.read(min(1024*1024,item['bytes']+1-count))
                if not chunk: break
                count+=len(chunk)
                if count>item['bytes']: raise RuntimeError('harness_download_budget')
                output.write(chunk);value.update(chunk)
        output.flush();os.fsync(output.fileno())
    if count!=item['bytes'] or value.hexdigest()!=item['sha256']: raise RuntimeError('harness_download_digest')
    partial.rename(target)


def setup(payload):
    artifacts=payload['toolchain']['artifacts']
    total=0
    for item in artifacts:
        path=WORK/'downloads'/item['archive']
        if path.is_symlink() or path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
            raise RuntimeError('harness_artifact_identity')
        with tarfile.open(path,'r:xz') as tar:
            _,size=archive_members(tar,item['archive'].removesuffix('.tar.xz'),2*1024**3)
            total+=size
    if total>2*1024**3 or os.statvfs(WORK).f_bavail*os.statvfs(WORK).f_frsize<2*total+512*1024**2:
        raise RuntimeError('harness_expansion_admission')
    prefix=WORK/TOOLCHAIN
    if prefix.exists(): raise RuntimeError('harness_toolchain_already_present')
    unwind=unwind_install(prefix)
    for index,item in enumerate(artifacts):
        root=item['archive'].removesuffix('.tar.xz')
        unpack=WORK/f'unpack-unwind-1-{index}'
        extract_archive(WORK/'downloads'/item['archive'],unpack,root,maximum=2*1024**3)
        command(['/usr/bin/bash',str(unpack/root/'install.sh'),f'--prefix={prefix}',
                 f'--sysconfdir={prefix}/etc',f'--datadir={prefix}/share',f'--docdir={prefix}/share/doc/rust',
                 f'--bindir={prefix}/bin',f'--libdir={prefix}/lib',f'--mandir={prefix}/share/man','--disable-ldconfig'],
                cwd=unpack/root,maximum=120,environment=environment(rust=False))
    env=environment()
    output,_=command([str(prefix/'bin/rustc'),'-vV'],environment=env)
    if (b'release: 1.95.0\n' not in output or ('host: '+HOST+'\n').encode() not in output
            or payload['toolchain']['commit'].encode() not in output): raise RuntimeError('harness_rustc_identity')
    linker=prefix/'lib/rustlib'/HOST/'bin/rust-lld'
    if not linker.is_file(): raise RuntimeError('harness_linker_missing')
    source=WORK/'harness';source.mkdir(mode=0o700)
    expected={'Cargo.toml','Cargo.lock','src/lib.rs','src/linux/child_seccomp.rs'}
    if set(payload['files'])!=expected: raise RuntimeError('harness_source_set')
    for name,content in payload['files'].items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as stream: stream.write(content)
    if digest(source/'src/linux/child_seccomp.rs')!=payload['patched_sha256']:
        raise RuntimeError('harness_patch_identity')
    return {'expanded_archive_bytes':total,'rustc':output.decode(),'linker_sha256':digest(linker),'unwind':unwind}


def execute_tests(payload):
    source=WORK/'harness';env=environment();cargo=str(WORK/TOOLCHAIN/'bin/cargo')
    for name,content in payload['files'].items():
        if (source/name).read_text()!=content: raise RuntimeError('harness_source_changed')
    lock_before=digest(source/'Cargo.lock')
    raw,_=command([cargo,'test','--release','--locked','--offline','--lib','--no-run','--message-format=json'],
                  cwd=source,maximum=600,environment=env)
    executables=[]
    for line in raw.splitlines():
        item=json.loads(line)
        if item.get('reason')=='compiler-artifact' and item.get('executable'):
            executables.append(Path(item['executable']))
    if len(executables)!=1 or not executables[0].resolve().is_relative_to((WORK/TARGET).resolve()):
        raise RuntimeError('harness_test_binary')
    binary=executables[0];binary_hash=verify_static_arm64(binary)
    output,error=command([str(binary),'--test-threads=1','--nocapture'],cwd=source,maximum=180,environment=env)
    if b'test result: ok.' not in output:
        raise RuntimeError('harness_test_proof')
    # The upstream-style parent test captures its child's stdout. Run the exact
    # filtered child once separately to retain the required native sentinel,
    # after the complete suite has exercised its unaffected-parent control.
    filtered,filtered_error=command([
        str(binary),'--exact',
        'linux::child_seccomp::tests::filter_denies_unix_creation_only_in_workload_children',
        '--test-threads=1','--nocapture'],cwd=source,maximum=60,
        environment=env|{'OPENSHELL_CHILD_UNIX_DENIAL_PROBE':'filtered'})
    if SENTINEL.encode() not in filtered or b'test result: ok.' not in filtered:
        raise RuntimeError('harness_filtered_test_proof')
    if digest(source/'Cargo.lock')!=lock_before: raise RuntimeError('harness_lock_changed')
    return {'binary_sha256':binary_hash,'binary':str(binary),'static_arm64':True,
            'patched_source_sha256':digest(source/'src/linux/child_seccomp.rs'),
            'lock_sha256':lock_before,'test_stdout':output.decode(),'test_stderr':error.decode(),
            'filtered_stdout':filtered.decode(),'filtered_stderr':filtered_error.decode(),
            'kernel_only':True,'full_runtime_qualified':False,'session_enabled':False}


def stage(operation, payload, seconds, *, resume_run=False):
    global DEADLINE, TARGET
    allowed = {'resume','test'} if resume_run is True else {'download','setup','fetch','test'}
    if type(resume_run) is not bool or operation not in allowed or not 0<seconds<=1200:
        raise RuntimeError('harness_operation')
    DEADLINE=time.monotonic()+seconds
    TARGET='target/resume-1' if resume_run else 'target'
    validate_context()
    if payload['toolchain']['host']!=HOST or payload['toolchain']['version']!='1.95.0':
        raise RuntimeError('harness_toolchain_selection')
    if operation=='download':
        for item in payload['toolchain']['artifacts']: download(item)
        result={'verified_archives':len(payload['toolchain']['artifacts']),'unwind':unwind_download()}
    elif operation=='setup': result=setup(payload)
    elif operation=='resume': result=resume(payload)
    elif operation=='fetch':
        source=WORK/'harness';before=digest(source/'Cargo.lock')
        command([str(WORK/TOOLCHAIN/'bin/cargo'),'fetch','--locked'],cwd=source,maximum=300,environment=environment())
        if digest(source/'Cargo.lock')!=before: raise RuntimeError('harness_lock_changed')
        result={'locked_fetch':True}
    else: result=execute_tests(payload)
    remaining()
    print(json.dumps({'stage':operation,'result':result},sort_keys=True),flush=True)
