"""Closed unprivileged Cargo stages appended to the qualified harness.

Inputs and compiler closure are reverified by the caller. This module authenticates
registry archives and their extracted files before offline compilation. Failed
attempts remain in place; no retry, deletion, fallback compiler or new cap exists.
"""
import contextlib
import gzip
import re
import tomllib

FULL_VERSION = '0.1.7+dotfiles-ai.child-unix-deny.2'
FULL_REGISTRY = 'registry+https://github.com/rust-lang/crates.io-index'
FULL_CACHE_LIMIT = 512*1024**2
FULL_EXPANDED_LIMIT = 2*1024**3
FULL_CRATE_LIMIT = 64*1024**2
FULL_CRATE_EXPANDED_LIMIT = 128*1024**2
FULL_ENTRIES = 200000
FULL_SOURCE_CONFIG = b'''# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

[env]
# z3-sys bindgen needs the z3 include path. On some distros (e.g. RHEL/Fedora)
# the header lives in /usr/include/z3/ rather than /usr/include/. The extra -I
# is harmless on systems where the path doesn't exist.
BINDGEN_EXTRA_CLANG_ARGS = "-I/usr/include/z3"
'''
FULL_LIBRARIES = frozenset(('libc.so.6','libm.so.6','libpthread.so.0','libdl.so.2',
                           'librt.so.1','libstdc++.so.6','libgcc_s.so.1','libz.so.1'))


def full_cargo_settings(payload):
    remaining()
    value=payload['full_manifest']
    expected={'home':'full-cargo-1','target':'full-target-1','source':'full-source-1',
        'auto_clean_frequency':'never','incremental':'0','release_debug':'0',
        'aws_lc_sys_use_system':'0','aws_lc_sys_cmake_builder':'0','locked':True,'offline_compile':True}
    if (value['schema_version']!=1 or value['experimental_version']!=FULL_VERSION
            or value['cargo']!=expected or value['limits']['jobs']!=2
            or value['limits']['store_bytes']!=8*1024**3):
        raise RuntimeError('full_cargo_selection')
    return value


def full_cargo_meta(path, *, directory=False):
    remaining()
    path=Path(path)
    try: parts=path.relative_to(WORK).parts
    except ValueError: raise RuntimeError('full_cargo_path') from None
    if any(part in ('','.', '..') for part in parts): raise RuntimeError('full_cargo_path')
    root=WORK.lstat();current=WORK;info=root
    for index,part in enumerate(parts):
        current/=part;info=current.lstat()
        is_dir=index<len(parts)-1 or directory
        if (info.st_dev!=root.st_dev or info.st_uid!=os.getuid() or info.st_gid!=os.getgid()
                or info.st_mode&0o022 or not (stat.S_ISDIR(info.st_mode) if is_dir else stat.S_ISREG(info.st_mode))
                or (not is_dir and info.st_nlink!=1)):
            raise RuntimeError('full_cargo_file_identity')
    return info


def full_cargo_identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)


@contextlib.contextmanager
def full_cargo_open(path, maximum):
    info=full_cargo_meta(path)
    if not 0<=info.st_size<=maximum: raise RuntimeError('full_cargo_file_budget')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    try:
        if full_cargo_identity(os.fstat(fd))!=full_cargo_identity(info):
            raise RuntimeError('full_cargo_file_changed')
        with os.fdopen(fd,'rb',closefd=False) as stream:
            yield stream
        if (full_cargo_identity(os.fstat(fd))!=full_cargo_identity(info)
                or full_cargo_identity(full_cargo_meta(path))!=full_cargo_identity(info)):
            raise RuntimeError('full_cargo_file_changed')
    finally: os.close(fd)


def full_cargo_read(path, maximum):
    with full_cargo_open(path,maximum) as stream:
        remaining();data=stream.read(maximum+1);remaining()
    if len(data)>maximum: raise RuntimeError('full_cargo_file_budget')
    return data


def full_cargo_digest(path, maximum):
    value=hashlib.sha256()
    with full_cargo_open(path,maximum) as stream:
        while True:
            remaining();block=stream.read(1024*1024)
            if not block: break
            value.update(block)
    return value.hexdigest()


def full_cargo_configs():
    """Only the authenticated upstream config may affect Cargo resolution."""
    source=WORK/'full-source-1'
    allowed=source/'.cargo/config.toml'
    if full_cargo_read(allowed,16384)!=FULL_SOURCE_CONFIG:
        raise RuntimeError('full_cargo_config')
    for base in (source,*source.parents):
        for name in ('config','config.toml','credentials','credentials.toml'):
            path=base/'.cargo'/name
            if path!=allowed and os.path.lexists(path): raise RuntimeError('full_cargo_config')
    home=WORK/'full-cargo-1'
    for name in ('config','config.toml','credentials','credentials.toml','.gitconfig','.netrc'):
        if os.path.lexists(home/name): raise RuntimeError('full_cargo_config')


def full_cargo_environment(*, offline=False):
    env=environment()
    env.update({'HOME':str(WORK/'full-cargo-1'),'CARGO_HOME':str(WORK/'full-cargo-1'),
        'CARGO_TARGET_DIR':str(WORK/'full-target-1'),'CARGO_CACHE_AUTO_CLEAN_FREQUENCY':'never',
        'CARGO_PROFILE_RELEASE_DEBUG':'0','CARGO_PROFILE_TEST_DEBUG':'0','CARGO_NET_RETRY':'0',
        'GIT_DIR':'/nonexistent',
        'CARGO_HTTP_TIMEOUT':'30','CARGO_REGISTRIES_CRATES_IO_PROTOCOL':'sparse',
        'AWS_LC_SYS_USE_SYSTEM':'0','AWS_LC_SYS_CMAKE_BUILDER':'0',
        'CC':str(WORK/'full-c-wrappers-1/cc'),'AR':str(WORK/'full-c-wrappers-1/ar'),
        'AS':str(WORK/'full-c-wrappers-1/as')})
    for target in ('aarch64_unknown_linux_musl','aarch64-unknown-linux-musl'):
        env['CC_'+target]=env['CC'];env['AR_'+target]=env['AR']
    env['HOST_CC']=env['TARGET_CC']=env['CC'];env['HOST_AR']=env['TARGET_AR']=env['AR']
    if offline: env['CARGO_NET_OFFLINE']='true'
    return env


def full_cargo_lock(payload):
    manifest=full_cargo_settings(payload)
    raw=full_cargo_read(WORK/'full-source-1/Cargo.lock',1024*1024)
    if hashlib.sha256(raw).hexdigest()!=manifest['source']['derived_lock_sha256']:
        raise RuntimeError('full_cargo_lock')
    try: packages=tomllib.loads(raw.decode())['package']
    except (ValueError,KeyError,UnicodeError): raise RuntimeError('full_cargo_lock') from None
    if type(packages) is not list or not 1<=len(packages)<=1024: raise RuntimeError('full_cargo_lock')
    expected={};local=0
    for package in packages:
        if (type(package) is not dict or type(package.get('name')) is not str
                or re.fullmatch(r'[A-Za-z0-9_-]{1,128}',package['name']) is None
                or type(package.get('version')) is not str
                or re.fullmatch(r'[0-9][A-Za-z0-9.+_-]{0,127}',package['version']) is None):
            raise RuntimeError('full_cargo_lock')
        if 'source' not in package:
            if package['version']!=FULL_VERSION or 'checksum' in package: raise RuntimeError('full_cargo_lock')
            local+=1;continue
        name=package['name']+'-'+package['version'];checksum=package.get('checksum')
        if (package['source']!=FULL_REGISTRY or name in expected or type(checksum) is not str
                or re.fullmatch(r'[0-9a-f]{64}',checksum) is None): raise RuntimeError('full_cargo_lock')
        expected[name]=checksum
    if len(expected)!=manifest['source']['external_packages'] or local!=manifest['source']['local_packages']:
        raise RuntimeError('full_cargo_lock')
    return expected


def full_cargo_tree(root):
    """Bounded metadata walk, without following links or changing cache files."""
    full_cargo_meta(root,directory=True);found={};pending=[(root,0)]
    while pending:
        directory,depth=pending.pop();remaining()
        if depth>32: raise RuntimeError('full_cargo_tree_budget')
        with os.scandir(directory) as entries:
            for entry in entries:
                remaining()
                if len(found)>=FULL_ENTRIES: raise RuntimeError('full_cargo_tree_budget')
                path=directory/entry.name;info=entry.stat(follow_symlinks=False)
                is_dir=stat.S_ISDIR(info.st_mode)
                full_cargo_meta(path,directory=is_dir)
                relative=path.relative_to(root).as_posix()
                found[relative]=('directory' if is_dir else 'file',info.st_size,info.st_mode)
                if is_dir: pending.append((path,depth+1))
    return found


def full_cargo_crate(archive, root, checksum):
    if full_cargo_digest(archive,FULL_CRATE_LIMIT)!=checksum: raise RuntimeError('full_cargo_archive_checksum')
    expected={};directories=set();expanded=0;decompressed=0;count=0
    class Reader:
        def __init__(self,stream):self.stream=stream
        def read(self,size=-1):
            nonlocal decompressed
            remaining()
            if size<0: size=65536
            block=self.stream.read(min(size,FULL_CRATE_EXPANDED_LIMIT+1-decompressed))
            decompressed+=len(block)
            if decompressed>FULL_CRATE_EXPANDED_LIMIT: raise RuntimeError('full_cargo_archive_budget')
            return block
    with full_cargo_open(archive,FULL_CRATE_LIMIT) as stream, gzip.GzipFile(fileobj=stream) as compressed:
        reader=Reader(compressed)
        with tarfile.open(fileobj=reader,mode='r|') as tar:
            for member in tar:
                remaining();count+=1;path=PurePosixPath(member.name)
                if (count>30000 or len(member.name)>1024 or path.is_absolute() or '..' in path.parts
                        or not path.parts or path.parts[0]!=root.name or str(path)!=member.name.rstrip('/')
                        or not (member.isdir() or member.isfile()) or member.size<0
                        or member.mode&0o6000): raise RuntimeError('full_cargo_archive_path')
                relative=PurePosixPath(*path.parts[1:]).as_posix()
                if relative=='.':
                    if not member.isdir(): raise RuntimeError('full_cargo_archive_path')
                    continue
                if relative in expected or relative in directories: raise RuntimeError('full_cargo_archive_duplicate')
                for parent in PurePosixPath(relative).parents:
                    if str(parent)!='.':directories.add(str(parent))
                if member.isdir():directories.add(relative);continue
                expanded+=member.size
                if expanded>FULL_CRATE_EXPANDED_LIMIT: raise RuntimeError('full_cargo_archive_budget')
                value=hashlib.sha256();size=0
                extracted=tar.extractfile(member)
                if extracted is None: raise RuntimeError('full_cargo_archive_file')
                with extracted:
                    while True:
                        remaining();block=extracted.read(1024*1024)
                        if not block:break
                        size+=len(block);value.update(block)
                if size!=member.size: raise RuntimeError('full_cargo_archive_file')
                expected[relative]=(size,value.hexdigest(),bool(member.mode&0o111))
        while reader.read(65536):pass
    actual=full_cargo_tree(root)
    extra=set(actual)-set(expected)-directories
    if not extra<= {'.cargo-ok','.cargo-checksum.json'}: raise RuntimeError('full_cargo_extracted_extra')
    if set(expected)-set(actual) or directories-set(actual): raise RuntimeError('full_cargo_extracted_missing')
    for name,(size,checksum_value,executable) in expected.items():
        kind,actual_size,mode=actual[name]
        if (kind!='file' or actual_size!=size or bool(mode&0o111)!=executable
                or full_cargo_digest(root/name,FULL_CRATE_EXPANDED_LIMIT)!=checksum_value):
            raise RuntimeError('full_cargo_extracted_checksum')
    if any(actual[name][0]!='directory' for name in directories): raise RuntimeError('full_cargo_extracted_type')
    for name in extra:
        raw=full_cargo_read(root/name,1024*1024)
        if name=='.cargo-ok':
            if raw not in (b'',b'{"v":1}',b'{"v":1}\n'): raise RuntimeError('full_cargo_marker')
        else:
            marker=json.loads(raw)
            if (type(marker) is not dict or set(marker)!={'files','package'} or marker['package']!=checksum
                    or type(marker['files']) is not dict
                    or any(name not in expected or digest_value!=expected[name][1] for name,digest_value in marker['files'].items())):
                raise RuntimeError('full_cargo_marker')
    return expanded


def full_cargo_cache(payload):
    expected=full_cargo_lock(payload);full_cargo_configs()
    home=WORK/'full-cargo-1';tree=full_cargo_tree(home)
    allowed={'registry','.package-cache','.package-cache-mutate','.global-cache','.global-cache-wal','.global-cache-shm'}
    if {name.split('/')[0] for name in tree}-allowed: raise RuntimeError('full_cargo_cache_shape')
    registry=home/'registry';cache=registry/'cache';sources=registry/'src';index=registry/'index'
    for path in (cache,sources,index):full_cargo_meta(path,directory=True)
    registry_ids={item.name for item in cache.iterdir()}
    if len(registry_ids)!=1 or any(re.fullmatch(r'index\.crates\.io-[0-9a-f]{16}',value) is None for value in registry_ids):
        raise RuntimeError('full_cargo_registry')
    registry_id=next(iter(registry_ids))
    if ({item.name for item in sources.iterdir()}!=registry_ids or {item.name for item in index.iterdir()}!=registry_ids):
        raise RuntimeError('full_cargo_registry')
    config=json.loads(full_cargo_read(index/registry_id/'config.json',4096))
    if config!={'dl':'https://static.crates.io/crates','api':'https://crates.io'}: raise RuntimeError('full_cargo_registry')
    archives=sorted((cache/registry_id).iterdir());names=set();compressed=expanded=0;transcript=[]
    if not 1<=len(archives)<=len(expected): raise RuntimeError('full_cargo_cache_shape')
    for archive in archives:
        remaining();name=archive.name.removesuffix('.crate')
        if archive.name!=name+'.crate' or name not in expected or name in names: raise RuntimeError('full_cargo_cache_shape')
        names.add(name);compressed+=full_cargo_meta(archive).st_size
        if compressed>FULL_CACHE_LIMIT:raise RuntimeError('full_cargo_cache_budget')
        expanded+=full_cargo_crate(archive,sources/registry_id/name,expected[name])
        if expanded>FULL_EXPANDED_LIMIT:raise RuntimeError('full_cargo_cache_budget')
        transcript.append(name+' '+expected[name])
    if {item.name for item in (sources/registry_id).iterdir()}!=names:raise RuntimeError('full_cargo_cache_shape')
    return {'crates':len(names),'locked_registry_records':len(expected),'compressed_bytes':compressed,'expanded_bytes':expanded,
            'cache_sha256':hashlib.sha256('\n'.join(transcript).encode()).hexdigest()}


def full_cargo_fetch(payload):
    full_cargo_lock(payload);full_cargo_configs()
    home=WORK/'full-cargo-1'
    if os.path.lexists(home):raise RuntimeError('full_cargo_retained')
    home.mkdir(mode=0o700)
    command([str(WORK/TOOLCHAIN/'bin/cargo'),'fetch','--locked','--target',HOST],
            cwd=WORK/'full-source-1',maximum=900,environment=full_cargo_environment())
    result=full_cargo_cache(payload)
    return {'status':'full_cargo_fetched','locked_fetch':True,**result,
            'session_enabled':False,'full_runtime_qualified':False}


def full_protoc_elf(path):
    """Inspect ARM64 ELF program/dynamic headers without executing the artifact."""
    with full_cargo_open(path,32*1024**2) as stream:
        size=os.fstat(stream.fileno()).st_size;head=stream.read(64)
        if len(head)!=64 or head[:7]!=b'\x7fELF\x02\x01\x01': raise RuntimeError('full_cargo_protoc_elf')
        kind,machine,version,_,phoff,_,_,ehsize,phsize,phnum,_,_,_=struct.unpack_from('<HHIQQQIHHHHHH',head,16)
        if (kind not in (2,3) or machine!=183 or version!=1 or ehsize!=64 or phsize!=56
                or not 1<=phnum<=128 or not 64<=phoff<=1024*1024 or phoff+phnum*56>size):
            raise RuntimeError('full_cargo_protoc_elf')
        stream.seek(phoff);headers=[struct.unpack('<IIQQQQQQ',stream.read(56)) for _ in range(phnum)]
        interpreter=None;dynamic=[];loads=[]
        for h in headers:
            if h[2]+h[5]>size:raise RuntimeError('full_cargo_protoc_elf')
            if h[0]==1:loads.append(h)
            elif h[0]==3:
                if interpreter is not None or not 1<=h[5]<=256:raise RuntimeError('full_cargo_protoc_elf')
                stream.seek(h[2]);raw=stream.read(h[5])
                if raw!=b'/lib/ld-linux-aarch64.so.1\0':raise RuntimeError('full_cargo_protoc_interpreter')
                interpreter=raw[:-1].decode()
            elif h[0]==2:
                if dynamic or not 0<h[5]<=65536 or h[5]%16:raise RuntimeError('full_cargo_protoc_elf')
                stream.seek(h[2]);dynamic=[struct.unpack('<qQ',stream.read(16)) for _ in range(h[5]//16)]
        needed=[];strings={};offsets=[];terminated=not dynamic
        for tag,value in dynamic:
            if tag==0:terminated=True;break
            if tag==1:offsets.append(value)
            if tag in (5,10):
                if tag in strings:raise RuntimeError('full_cargo_protoc_elf')
                strings[tag]=value
            if tag in (15,29):raise RuntimeError('full_cargo_protoc_search_path')
        if not terminated:raise RuntimeError('full_cargo_protoc_elf')
        if offsets:
            if set(strings)!={5,10} or not 0<strings[10]<=1024*1024:raise RuntimeError('full_cargo_protoc_elf')
            mappings=[h[2]+strings[5]-h[3] for h in loads if h[3]<=strings[5] and strings[5]+strings[10]<=h[3]+h[5]]
            if len(mappings)!=1:raise RuntimeError('full_cargo_protoc_elf')
            stream.seek(mappings[0]);raw=stream.read(strings[10])
            for offset in offsets:
                end=raw.find(b'\0',offset)
                if not 0<=offset<end:raise RuntimeError('full_cargo_protoc_elf')
                try:name=raw[offset:end].decode('ascii')
                except UnicodeError:raise RuntimeError('full_cargo_protoc_elf') from None
                if name not in FULL_LIBRARIES or name in needed:raise RuntimeError('full_cargo_protoc_dependency')
                needed.append(name)
        if needed and interpreter is None:raise RuntimeError('full_cargo_protoc_interpreter')
    return {'interpreter':interpreter,'needed':sorted(needed)}


def full_protoc(payload):
    selected=full_cargo_settings(payload)['protoc']
    name='protoc-bin-vendored-linux-aarch_64-3.2.0'
    if (selected['crate']+'-'+selected['version']!=name or selected['upstream_version']!='31.1'
            or selected['checksum']!='c350df4d49b5b9e3ca79f7e646fde2377b199e13cfa87320308397e1f37e1a4c'):
        raise RuntimeError('full_cargo_protoc_selection')
    root=WORK/'full-cargo-1/registry/src'
    matches=[path/name for path in root.iterdir() if (path/name).is_dir()]
    if len(matches)!=1:raise RuntimeError('full_cargo_protoc_missing')
    prefix=matches[0];binary=prefix/'bin/protoc';include=prefix/'include'
    full_cargo_meta(include,directory=True);details=full_protoc_elf(binary)
    clean=environment(rust=False);clean['HOME']=str(WORK/'full-cargo-1')
    if details['interpreter'] is not None:
        loader=Path(details['interpreter']);canonical=loader.resolve(strict=True);info=canonical.stat()
        if (not canonical.is_relative_to('/usr/lib64') or info.st_uid!=0 or info.st_mode&0o022
                or not stat.S_ISREG(info.st_mode)):raise RuntimeError('full_cargo_protoc_loader')
        raw,_=command([str(loader),'--list',str(binary)],maximum=15,environment=clean)
        observed=set()
        for line in raw.decode('ascii').splitlines():
            value=line.strip()
            if value.startswith('linux-vdso.so.1 ') or value.startswith(str(loader)+' '):continue
            match=re.fullmatch(r'([A-Za-z0-9_.+-]+) => (/[^ ]+) \(0x[0-9a-f]+\)',value)
            if not match or match[1] not in FULL_LIBRARIES:raise RuntimeError('full_cargo_protoc_dependency')
            dependency=Path(match[2]).resolve(strict=True);info=dependency.stat()
            if (not dependency.is_relative_to('/usr/lib64') or info.st_uid!=0 or info.st_mode&0o022
                    or not stat.S_ISREG(info.st_mode)):raise RuntimeError('full_cargo_protoc_dependency')
            observed.add(match[1])
        if not set(details['needed'])<=observed:raise RuntimeError('full_cargo_protoc_dependency')
    output,_=command([str(binary),'--version'],maximum=15,environment=clean)
    if output!=b'libprotoc 31.1\n':raise RuntimeError('full_cargo_protoc_version')
    wrapper=WORK/'full-protoc-1'
    body=('#!/usr/bin/python3 -I\nimport os, sys\nos.execve('+repr(str(binary))+', ['+repr(str(binary))+', *sys.argv[1:]], '+repr(clean)+')\n').encode()
    if os.path.lexists(wrapper):
        if full_cargo_read(wrapper,8192)!=body or stat.S_IMODE(wrapper.stat().st_mode)!=0o500:
            raise RuntimeError('full_cargo_protoc_wrapper')
    else:
        with wrapper.open('xb') as stream:stream.write(body)
        wrapper.chmod(0o500)
    return {'binary_sha256':full_cargo_digest(binary,32*1024**2),'version':'31.1',**details,
            'wrapper':str(wrapper),'include':str(include)}


def full_cargo_verify(payload):
    result=full_cargo_cache(payload);protoc=full_protoc(payload)
    return {'status':'full_cargo_verified',**result,'protoc':protoc,
            'session_enabled':False,'full_runtime_qualified':False}


def full_test_executable(raw):
    matches=[]
    for line in raw.decode('utf-8').splitlines():
        if 'Executable unittests' not in line:continue
        match=re.fullmatch(r'\s*Executable unittests src/lib\.rs \(([^\n]+)\)',line)
        if not match:raise RuntimeError('full_cargo_test_binary')
        path=Path(match[1])
        if not path.is_absolute():path=WORK/'full-source-1'/path
        if (path.parent!=WORK/'full-target-1/release/deps'
                or re.fullmatch(r'openshell_sandbox-[0-9a-f]{8,64}',path.name) is None):
            raise RuntimeError('full_cargo_test_binary')
        full_cargo_meta(path);matches.append(path)
    if len(matches)!=1:raise RuntimeError('full_cargo_test_binary')
    return matches[0]


def full_cargo_test(payload):
    manifest=full_cargo_settings(payload);full_cargo_lock(payload);full_cargo_configs()
    source=WORK/'full-source-1';lock=manifest['source']['derived_lock_sha256']
    patched=source/'crates/openshell-sandbox/src/linux/child_seccomp.rs'
    if full_cargo_digest(patched,128*1024)!=payload['patched_sha256']:raise RuntimeError('full_cargo_source_changed')
    protoc=full_protoc(payload);env=full_cargo_environment(offline=True)
    env.update({'PROTOC':protoc['wrapper'],'PROTOC_INCLUDE':protoc['include']})
    cargo=str(WORK/TOOLCHAIN/'bin/cargo')
    # Native musl host and target are identical. With an explicit --target,
    # Cargo withholds RUSTFLAGS from host build scripts, losing the bundled
    # linker. Keep the native build so host and target both receive these flags.
    flags=['--release','--locked','--offline','-p','openshell-sandbox','--message-format=human']
    command([cargo,'build',*flags,'--bin','openshell-sandbox'],cwd=source,maximum=1200,environment=env)
    binary=WORK/'full-target-1/release/openshell-sandbox'
    full_cargo_meta(binary);binary_hash=verify_static_arm64(binary)
    version,_=command([str(binary),'--version'],cwd=source,maximum=15,environment=env)
    if version.decode().strip()!='openshell-sandbox '+FULL_VERSION:raise RuntimeError('full_cargo_binary_version')
    out,err=command([cargo,'test',*flags,'--lib','--no-run'],cwd=source,maximum=1200,environment=env)
    test=full_test_executable(out+b'\n'+err);test_hash=verify_static_arm64(test)
    output,error=command([str(test),'--test-threads=1','--nocapture'],cwd=source,maximum=180,environment=env)
    if re.search(rb'test result: ok\. [1-9][0-9]* passed; 0 failed;',output) is None:
        raise RuntimeError('full_cargo_test_proof')
    filtered,filtered_error=command([str(test),'--exact',
        'linux::child_seccomp::tests::filter_denies_unix_creation_only_in_workload_children',
        '--test-threads=1','--nocapture'],cwd=source,maximum=60,
        environment=env|{'OPENSHELL_CHILD_UNIX_DENIAL_PROBE':'filtered'})
    if SENTINEL.encode() not in filtered or b'test result: ok. 1 passed; 0 failed;' not in filtered:
        raise RuntimeError('full_cargo_filtered_proof')
    full_cargo_lock(payload)
    if full_cargo_digest(patched,128*1024)!=payload['patched_sha256']:raise RuntimeError('full_cargo_source_changed')
    return {'status':'full_cargo_tested','static_arm64':True,'experimental_version':FULL_VERSION,
        'binary':str(binary),'binary_sha256':binary_hash,'test_binary_sha256':test_hash,
        'patched_source_sha256':payload['patched_sha256'],'derived_lock_sha256':lock,
        'test_stdout':output[-32768:].decode(),'test_stderr':error[-32768:].decode(),
        'filtered_stdout':filtered[-32768:].decode(),'filtered_stderr':filtered_error[-32768:].decode(),
        'session_enabled':False,'full_runtime_qualified':False}
