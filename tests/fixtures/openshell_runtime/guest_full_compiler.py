"""Private, signed C prerequisite for the fixed capped OpenShell experiment.

Appended to guest_harness and guest_unwind, never a public command interface.
No package scripts or system installation. Reauthenticate complete APKs before
publishing or verifying their bounded private prefix. Native compatibility is a
separate compile/archive/static-link/run proof; source tests cannot establish it.
"""
import posixpath as full_compiler_posix
import shlex as full_compiler_shlex

FULL_COMPILER_MANIFEST_SHA = '930a9840bce91cd99374be33d683b089e03bebfed89dc4cc85b97e7c95522171'
FULL_COMPILER_TRIPLE = 'aarch64-alpine-linux-musl'
FULL_COMPILER_GCC = '14.2.0'
FULL_COMPILER_SENTINEL = 'openshell-private-c-static-checked'


def full_compiler_fail(reason, detail=''):
    raise RuntimeError('full_compiler_'+reason+':'+str(detail)[:512])


def full_compiler_config(payload):
    cfg = payload['full_manifest']['c_toolchain']
    raw = json.dumps(cfg, sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(raw).hexdigest() != FULL_COMPILER_MANIFEST_SHA:
        full_compiler_fail('manifest')
    return cfg


def full_compiler_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def full_compiler_open(path, directory=False):
    remaining()
    if not path.is_relative_to(WORK) or '..' in path.parts or WORK.resolve() != WORK:
        full_compiler_fail('path', path)
    fd = os.open(WORK, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = path.relative_to(WORK).parts
        for index, part in enumerate(parts):
            parent = os.fstat(fd)
            if (parent.st_uid != os.getuid() or parent.st_gid != os.getgid()
                    or parent.st_mode & 0o022 or parent.st_dev != WORK.lstat().st_dev):
                full_compiler_fail('parent', path)
            isdir = index < len(parts)-1 or directory
            child = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                            (os.O_DIRECTORY if isdir else 0), dir_fd=fd)
            os.close(fd); fd = child
        info = os.fstat(fd)
        if (info.st_uid != os.getuid() or info.st_gid != os.getgid() or info.st_mode & 0o022
                or info.st_dev != WORK.lstat().st_dev
                or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
                or (not directory and info.st_nlink != 1)):
            full_compiler_fail('identity', path)
        return fd
    except BaseException:
        os.close(fd); raise


def full_compiler_read(path, limit, size=None):
    fd = full_compiler_open(path)
    try:
        before = os.fstat(fd)
        if before.st_size > limit or (size is not None and before.st_size != size):
            full_compiler_fail('size', path)
        raw = bytearray()
        while True:
            remaining(); chunk = os.read(fd, min(65536, limit+1-len(raw)))
            if not chunk: break
            raw.extend(chunk)
            if len(raw) > limit: full_compiler_fail('size', path)
        if len(raw) != before.st_size or full_compiler_identity(os.fstat(fd)) != full_compiler_identity(before):
            full_compiler_fail('changed', path)
        return bytes(raw)
    finally: os.close(fd)


def full_compiler_mkdir(path):
    if not os.path.lexists(path):
        fd = full_compiler_open(path.parent, True)
        try: os.mkdir(path.name, 0o700, dir_fd=fd)
        finally: os.close(fd)
    fd = full_compiler_open(path, True)
    try:
        if stat.S_IMODE(os.fstat(fd).st_mode) != 0o700: full_compiler_fail('directory_mode', path)
    finally: os.close(fd)


def full_compiler_save(path, raw, mode):
    if os.path.lexists(path):
        if full_compiler_read(path, len(raw)+1) != raw or stat.S_IMODE(path.lstat().st_mode) != mode:
            full_compiler_fail('retained_file', path)
        return
    parent = full_compiler_open(path.parent, True)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw); stream.flush(); os.fsync(fd)
            os.fchmod(fd, mode)
        finally: os.close(fd)
    finally: os.close(parent)


def full_compiler_download(payload):
    cfg = full_compiler_config(payload); root = WORK/'full-c-downloads-1'
    if os.statvfs(WORK).f_bavail*os.statvfs(WORK).f_frsize < cfg['compressed_bytes']+cfg['expanded_limit']+256*1024**2:
        full_compiler_fail('admission')
    full_compiler_mkdir(root)
    allowed = {item['archive'] for item in cfg['packages']}
    with os.scandir(root) as values:
        for count, entry in enumerate(values, 1):
            if count > 15 or entry.name not in allowed: full_compiler_fail('download_retained', entry.name)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), unwind_NoRedirect())
    for item in cfg['packages']:
        remaining(); path = root/item['archive']
        if os.path.lexists(path):
            full_compiler_read(path, item['bytes'], item['bytes']); continue
        partial = path.with_name(path.name+'.partial')
        with partial.open('xb') as stream:
            with opener.open(item['url'], timeout=remaining(20)) as response:
                if response.status != 200 or response.url != item['url']: full_compiler_fail('download_transport')
                count = 0
                while True:
                    remaining(); chunk = response.read1(min(65536, item['bytes']+1-count))
                    if not chunk: break
                    count += len(chunk)
                    if count > item['bytes']: full_compiler_fail('download_size', item['archive'])
                    stream.write(chunk)
            stream.flush(); os.fsync(stream.fileno())
        if count != item['bytes']: full_compiler_fail('download_size', item['archive'])
        os.link(partial, path, follow_symlinks=False); partial.unlink()
        full_compiler_read(path, item['bytes'], item['bytes'])
    return {'status':'compiler_downloaded', 'package_count':15, 'compressed_bytes':cfg['compressed_bytes'],
            'authenticated_packages':0}


def full_compiler_metadata(fields, item, versions):
    expected = {key:item[key] for key in ('pkgname','pkgver','arch','origin')}
    expected['commit'] = item['source_commit']
    if any(fields.get(key) != [value] for key,value in expected.items()): full_compiler_fail('metadata', item['archive'])
    if len(fields.get('datahash',[])) != 1 or unwind_re.fullmatch('[a-f0-9]{64}',fields['datahash'][0]) is None:
        full_compiler_fail('metadata', 'datahash')
    deps = {}
    for value in fields.get('depend',[]):
        name = value
        if '=' in value:
            name,version = value.split('=',1)
            if name not in versions or version != versions[name]:
                full_compiler_fail('metadata',item['archive']+': dependency '+value)
        if any(token in name for token in '<>~!') or (name in deps and deps[name] != value):
            full_compiler_fail('metadata',item['archive']+': conflicting dependency '+value)
        deps[name] = value
    if sorted(deps) != sorted(item['dependencies_expected']):
        full_compiler_fail('metadata',item['archive']+': dependency set '+repr(sorted(deps)))


def full_compiler_parse(compressed, item, versions, limit):
    expanded = bytearray(); streams = 0
    while compressed:
        remaining(); streams += 1
        if streams > 3: full_compiler_fail('streams')
        decoder = unwind_zlib.decompressobj(31)
        expanded.extend(decoder.decompress(compressed, limit+1-len(expanded)))
        if len(expanded)>limit or not decoder.eof: full_compiler_fail('expansion')
        compressed = decoder.unused_data
    result = {}; seen = set(); metadata = None
    with tarfile.open(fileobj=unwind_io.BytesIO(expanded), mode='r:', ignore_zeros=True) as archive:
        for member in archive:
            remaining(); name = member.name.rstrip('/') if member.isdir() else member.name
            parts = PurePosixPath(name)
            if (len(seen)>=20000 or name in seen or len(name)>512 or len(parts.parts)>32
                    or not name or name.startswith('/') or any(p in ('','..','.') for p in name.split('/'))
                    or member.mode & 0o7000
                    or not (member.isfile() or member.isdir() or member.issym() or member.islnk())):
                full_compiler_fail('member',name)
            seen.add(name)
            if name.startswith('.'):
                accepted = {'.PKGINFO','.pre-install','.post-install','.pre-upgrade','.post-upgrade','.pre-deinstall',
                            '.post-deinstall','.trigger','.SIGN.RSA.'+unwind_artifacts[2]['name'],
                            '.SIGN.RSA256.'+unwind_artifacts[2]['name']}
                if name not in accepted or not member.isfile() or member.size>65536: full_compiler_fail('control',name)
                if name=='.PKGINFO':
                    fields = {}
                    for line in archive.extractfile(member).read(65537).decode('utf-8').splitlines():
                        if not line or line.startswith('#'): continue
                        if ' = ' not in line: full_compiler_fail('metadata',name)
                        key,value=line.split(' = ',1);fields.setdefault(key,[]).append(value)
                    full_compiler_metadata(fields,item,versions); metadata=fields
                continue
            if name=='usr/bin/ldd': continue
            if member.isdir(): result[name]=('directory',0o700,None)
            elif member.isfile():
                raw=archive.extractfile(member).read(limit+1)
                if len(raw)!=member.size or len(raw)>limit: full_compiler_fail('expansion',name)
                result[name]=('file',0o500 if member.mode & 0o111 else 0o400,raw)
            else:
                target=member.linkname
                # The pinned native GCC APKBUILD publishes this one absolute
                # plugin alias. Relocate only its exact signed spelling.
                if (item['pkgname']=='gcc' and member.issym() and name=='usr/lib/bfd-plugins/liblto_plugin.so'
                        and target=='//usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/liblto_plugin.so'):
                    target='../../libexec/gcc/aarch64-alpine-linux-musl/14.2.0/liblto_plugin.so'
                if not target or target.startswith('/') or len(target)>512 or '\0' in target:
                    full_compiler_fail('link',name)
                result[name]=('symlink' if member.issym() else 'hardlink',0o777,target)
    if metadata is None: full_compiler_fail('metadata','missing PKGINFO')
    return result,len(expanded)


def full_compiler_graph(entries):
    if len(entries)>20000:full_compiler_fail('member_budget')
    result=dict(entries)
    for name in list(result):
        for parent in PurePosixPath(name).parents:
            if str(parent)=='.': continue
            key=str(parent)
            if key in result and result[key][0]!='directory': full_compiler_fail('ancestor',key)
            result[key]=('directory',0o700,None)
    def resolve(name, seen):
        if name not in result or name in seen or len(seen)>32: full_compiler_fail('link_graph',name)
        kind,_,value=result[name]
        if kind not in {'symlink','hardlink'}: return name
        target=full_compiler_posix.normpath(full_compiler_posix.join(full_compiler_posix.dirname(name),value)
                                          if kind=='symlink' else value)
        if target.startswith('/') or target=='..' or target.startswith('../'): full_compiler_fail('link_escape',name)
        return resolve(target,seen|{name})
    for name,entry in list(result.items()):
        if entry[0] in {'symlink','hardlink'}:
            target=resolve(name,set())
            if name=='usr/lib/bfd-plugins/liblto_plugin.so' and result[target][0]!='file':
                full_compiler_fail('lto_target',name)
            if entry[0]=='hardlink':
                if result[target][0]!='file': full_compiler_fail('hardlink',name)
                result[name]=result[target]
    return result


def full_compiler_tree(root):
    result={};pending=[root]
    while pending:
        remaining();path=pending.pop();fd=full_compiler_open(path,True)
        try:
            before=full_compiler_identity(os.fstat(fd))
            with os.scandir(fd) as entries:
                for entry in entries:
                    remaining()
                    if len(result)>=20000: full_compiler_fail('tree_budget')
                    child=path/entry.name;name=str(child.relative_to(root))
                    if len(child.relative_to(root).parts)>32:full_compiler_fail('tree_depth',name)
                    info=os.stat(entry.name,dir_fd=fd,follow_symlinks=False)
                    if (info.st_uid!=os.getuid() or info.st_gid!=os.getgid() or info.st_dev!=WORK.lstat().st_dev):
                        full_compiler_fail('tree_identity',name)
                    if stat.S_ISDIR(info.st_mode):
                        if stat.S_IMODE(info.st_mode)!=0o700:full_compiler_fail('tree_mode',name)
                        result[name]=('directory',0o700,None);pending.append(child)
                    elif stat.S_ISREG(info.st_mode):
                        if info.st_nlink!=1 or info.st_mode & 0o022:full_compiler_fail('tree_identity',name)
                        result[name]=('file',stat.S_IMODE(info.st_mode),info.st_size)
                    elif stat.S_ISLNK(info.st_mode) and info.st_nlink==1:
                        result[name]=('symlink',0o777,os.readlink(entry.name,dir_fd=fd))
                    else:full_compiler_fail('tree_type',name)
            if full_compiler_identity(os.fstat(fd))!=before:full_compiler_fail('tree_changed',path)
        finally:os.close(fd)
    return result


def full_compiler_publish(root, entries, create=False):
    if not os.path.lexists(root):
        if not create:full_compiler_fail('tree_missing',root)
        full_compiler_mkdir(root)
    actual=full_compiler_tree(root)
    if set(actual)-set(entries) or (not create and set(actual)!=set(entries)):full_compiler_fail('tree_entries',root)
    for name,value in actual.items():
        expected=entries[name]
        if value[:2]!=expected[:2]:full_compiler_fail('tree_mode_type',name)
        if value[0]=='file':
            if value[2]!=len(expected[2]) or full_compiler_read(root/name,len(expected[2])+1)!=expected[2]:
                full_compiler_fail('tree_content',name)
        elif value[2]!=expected[2]:full_compiler_fail('tree_link',name)
    for name in sorted(set(entries)-set(actual),key=lambda x:(len(PurePosixPath(x).parts),x)):
        kind,mode,value=entries[name]
        if kind=='directory':full_compiler_mkdir(root/name)
    for name,(kind,mode,value) in entries.items():
        if name in actual or kind=='directory':continue
        if kind=='file':full_compiler_save(root/name,value,mode)
    for name,(kind,mode,value) in entries.items():
        if name in actual or kind!='symlink':continue
        parent=full_compiler_open((root/name).parent,True)
        try:os.symlink(value,(root/name).name,dir_fd=parent)
        finally:os.close(parent)
    if set(full_compiler_tree(root))!=set(entries):full_compiler_fail('tree_changed',root)


def full_compiler_elf(raw, member=''):
    if len(raw)<64 or raw[:7]!=b'\x7fELF\x02\x01\x01':full_compiler_fail('elf')
    kind,machine,version,_,offset,_,_,size,phsize,count,_,_,_=struct.unpack_from('<HHIQQQIHHHHHH',raw,16)
    if kind not in (1,2,3) or machine!=183 or version!=1 or size!=64:full_compiler_fail('elf')
    if kind==1 and count==0:return {'kind':kind,'needed':[],'interpreter':None}
    if phsize!=56 or not 0<count<=128 or offset<64 or offset+count*56>len(raw):full_compiler_fail('elf')
    loads=[];dynamic=[];interpreter=None
    for index in range(count):
        tag,_,start,address,_,length,memsize,_=struct.unpack_from('<IIQQQQQQ',raw,offset+index*56)
        if start+length>len(raw) or length>memsize:full_compiler_fail('elf')
        if tag==1:loads.append((start,address,length))
        if tag==2:dynamic.append((start,length))
        if tag==3:
            if interpreter is not None or not 1<length<=256:full_compiler_fail('elf')
            interpreter=raw[start:start+length]
            if interpreter!=b'/lib/ld-musl-aarch64.so.1\0':full_compiler_fail('elf_interpreter')
    if len(dynamic)>1:full_compiler_fail('elf')
    tags={}
    for start,length in dynamic:
        if not 0<length<=65536 or length%16:full_compiler_fail('elf')
        for at in range(start,start+length,16):
            tag,value=struct.unpack_from('<qQ',raw,at)
            if tag==0:break
            tags.setdefault(tag,[]).append(value)
        else:full_compiler_fail('elf')
    needed=[]
    blocked=next((tag for tag in (15,29,0x6ffffefb,0x6ffffefc) if tag in tags),None)
    label=str(member)[:192]+(f' tag={blocked:#x}' if blocked else '')
    if tags.get(1) or blocked:
        if len(tags.get(5,[]))!=1 or len(tags.get(10,[]))!=1 or len(tags.get(1,[]))>64:
            full_compiler_fail('elf',label+' invalid string table')
        address,length=tags[5][0],tags[10][0]
        matches=[start+address-virtual for start,virtual,size in loads if virtual<=address and address+length<=virtual+size]
        if len(matches)!=1 or not 0<length<=len(raw):
            full_compiler_fail('elf_string_table',f'{label} mappings={len(matches)} bytes={length} file_bytes={len(raw)}')
        strings=raw[matches[0]:matches[0]+length]
        if blocked:
            at=tags[blocked][0]
            end=strings.find(b'\0',at,min(at+257,len(strings))) if at<len(strings) else -1
            value=repr(strings[at:end]) if end>=0 else f'<invalid offset={at} or unterminated>'
            full_compiler_fail('elf_search_path',f'{label} value={value}')
        for at in tags.get(1,[]):
            if at>=len(strings) or b'\0' not in strings[at:]:full_compiler_fail('elf')
            name=strings[at:].split(b'\0',1)[0].decode('ascii')
            if not name or '/' in name or name in needed:full_compiler_fail('elf_needed')
            needed.append(name)
    return {'kind':kind,'needed':needed,'interpreter':interpreter}


def full_compiler_resolve(entries,name):
    seen=set()
    while name in entries and entries[name][0]=='symlink':
        if name in seen or len(seen)>32:full_compiler_fail('link_graph',name)
        seen.add(name);name=full_compiler_posix.normpath(full_compiler_posix.join(full_compiler_posix.dirname(name),entries[name][2]))
    if name not in entries or entries[name][0]!='file':full_compiler_fail('required_file',name)
    return name


def full_compiler_closure(entries):
    gcc='usr/lib/gcc/'+FULL_COMPILER_TRIPLE+'/'+FULL_COMPILER_GCC
    libexec='usr/libexec/gcc/'+FULL_COMPILER_TRIPLE+'/'+FULL_COMPILER_GCC
    required=['usr/bin/gcc','usr/bin/as','usr/bin/ar','usr/bin/ld','lib/ld-musl-aarch64.so.1',
              libexec+'/cc1',libexec+'/collect2',gcc+'/include/stddef.h',gcc+'/libgcc.a',
              'usr/include/stdio.h','usr/lib/libc.a','usr/lib/crt1.o','usr/lib/crti.o','usr/lib/crtn.o']
    for name in required:full_compiler_resolve(entries,name)
    for name,(kind,_,raw) in entries.items():
        remaining()
        if kind!='file' or not raw.startswith(b'\x7fELF'):continue
        for needed in full_compiler_elf(raw,name)['needed']:
            found=[directory+'/'+needed for directory in ('lib','usr/lib',gcc) if directory+'/'+needed in entries]
            if not found:full_compiler_fail('missing_dependency',name+':'+needed)
            target=full_compiler_resolve(entries,found[0])
            if not entries[target][2].startswith(b'\x7fELF'):full_compiler_fail('dependency_elf',target)


def full_compiler_inputs(payload):
    cfg=full_compiler_config(payload);unwind_verify()
    allowed={item['archive'] for item in cfg['packages']};found=set()
    fd=full_compiler_open(WORK/'full-c-downloads-1',True)
    try:
        with os.scandir(fd) as values:
            for entry in values:
                remaining()
                if entry.name not in allowed or len(found)>=len(allowed):full_compiler_fail('download_retained',entry.name)
                found.add(entry.name)
    finally:os.close(fd)
    if found!=allowed:full_compiler_fail('download_retained','missing APK')
    paths=[];hashes={}
    for item in cfg['packages']:
        path=WORK/'full-c-downloads-1'/item['archive']
        raw=full_compiler_read(path,item['bytes'],item['bytes'])
        paths.append(path);hashes[item['archive']]=hashlib.sha256(raw).hexdigest()
    root=WORK/'unwind-bootstrap-1/root';binary=WORK/'unwind-bootstrap-1/apk.static'
    env={'PATH':'/usr/bin:/bin','LC_ALL':'C','HOME':str(WORK/'home'),'TMPDIR':str(WORK/'tmp')}
    command([str(binary),'--root',str(root),'--keys-dir','keys','--repositories-file','/dev/null',
             '--no-network','--no-cache','verify',*(str(path) for path in paths)],environment=env,maximum=120)
    entries={};expanded=0;versions={item['pkgname']:item['pkgver'] for item in cfg['packages']}
    for path,item in zip(paths,cfg['packages']):
        raw=full_compiler_read(path,item['bytes'],item['bytes'])
        if hashlib.sha256(raw).hexdigest()!=hashes[item['archive']]:full_compiler_fail('artifact_changed',path)
        values,size=full_compiler_parse(raw,item,versions,cfg['expanded_limit']-expanded);expanded+=size
        for name,value in values.items():
            if name in entries and entries[name]!=value:full_compiler_fail('package_collision',name)
            entries[name]=value
    entries=full_compiler_graph(entries)
    if sum(len(raw) for kind,_,raw in entries.values() if kind=='file')>cfg['expanded_limit']:
        full_compiler_fail('expansion','materialized files')
    full_compiler_closure(entries)
    return cfg,entries,hashes,expanded


def full_compiler_wrappers():
    prefix=WORK/'full-c-toolchain-1';gcc=prefix/'usr/lib/gcc'/FULL_COMPILER_TRIPLE/FULL_COMPILER_GCC
    libexec=prefix/'usr/libexec/gcc'/FULL_COMPILER_TRIPLE/FULL_COMPILER_GCC
    libraries=str(prefix/'lib')+':'+str(prefix/'usr/lib')+':'+str(gcc)
    env=['PATH='+str(prefix/'usr/bin'),'LC_ALL=C','HOME='+str(WORK/'home'),'TMPDIR='+str(WORK/'tmp'),
         'LD_LIBRARY_PATH='+libraries,'GCC_EXEC_PREFIX='+str(prefix/'usr/lib/gcc')+'/',
         'COMPILER_PATH='+str(libexec)+':'+str(prefix/'usr/bin'),'LIBRARY_PATH='+str(gcc)+':'+str(prefix/'usr/lib')+':'+str(prefix/'lib')]
    common=['/usr/bin/env','-i',*env,str(prefix/'lib/ld-musl-aarch64.so.1'),'--library-path',libraries]
    result={}
    for tool in ('cc','as','ar'):
        argv=[*common,str(prefix/'usr/bin'/('gcc' if tool=='cc' else tool))]
        if tool=='cc':argv += ['--sysroot='+str(prefix),'-B'+str(libexec)+'/', '-B'+str(gcc)+'/',
            '-B'+str(prefix/'usr/bin')+'/', '-nostdinc','-isystem',str(gcc/'include'),'-isystem',str(prefix/'usr/include'),
            '-L'+str(gcc),'-L'+str(prefix/'usr/lib'),'-L'+str(prefix/'lib')]
        result[tool]=('#!/bin/sh\nexec '+full_compiler_shlex.join(argv)+' "$@"\n').encode()
    return result


def full_compiler_ready(payload, create):
    cfg,entries,hashes,expanded=full_compiler_inputs(payload)
    published=sum(len(raw) for kind,_,raw in entries.values() if kind=='file')
    if create and os.statvfs(WORK).f_bavail*os.statvfs(WORK).f_frsize<max(expanded,published)+256*1024**2:
        full_compiler_fail('admission')
    prefix=WORK/'full-c-toolchain-1';full_compiler_publish(prefix,entries,create)
    wrappers=full_compiler_wrappers();wrapper_root=WORK/'full-c-wrappers-1'
    full_compiler_publish(wrapper_root,{name:('file',0o500,raw) for name,raw in wrappers.items()},create)
    identity=[(name,kind,mode,hashlib.sha256(raw).hexdigest() if kind=='file' else raw)
              for name,(kind,mode,raw) in sorted(entries.items())]
    remaining()
    return {'status':'compiler_prepared' if create else 'compiler_verified','package_count':15,'authenticated_packages':15,
        'archive_sha256':hashes,'expanded_bytes':expanded,'file_count':sum(value[0]=='file' for value in entries.values()),
        'prefix':str(prefix),'compiler_tree_sha256':hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest(),
        'wrappers':{name:str(wrapper_root/name) for name in wrappers},
        'wrapper_sha256':{name:hashlib.sha256(raw).hexdigest() for name,raw in wrappers.items()}}


def full_compiler_prepare(payload):
    return full_compiler_ready(payload,True)


def full_compiler_verify(payload):
    return full_compiler_ready(payload,False)


def full_compiler_probe(payload):
    smoke=WORK/'full-c-smoke-1'
    if os.path.lexists(smoke):full_compiler_fail('smoke_present')
    report=full_compiler_verify(payload);prefix=WORK/'full-c-toolchain-1';full_compiler_mkdir(smoke)
    sources={'lib.c':b'#include <stdint.h>\nint openshell_c_value(void) { return (int)(uint32_t)42; }\n',
             'main.c':b'#include <stdio.h>\nint openshell_c_value(void);\nint main(void) { if (openshell_c_value()!=42) return 1; puts("openshell-private-c-static-checked"); return 0; }\n'}
    for name,raw in sources.items():full_compiler_save(smoke/name,raw,0o400)
    env={'PATH':'/usr/bin:/bin','LC_ALL':'C','HOME':str(WORK/'home'),'TMPDIR':str(WORK/'tmp')}
    cc=report['wrappers']['cc'];ar=report['wrappers']['ar']
    for flag in ('-print-prog-name=cc1','-print-prog-name=as','-print-prog-name=ld','-print-prog-name=collect2',
                 '-print-file-name=crt1.o','-print-file-name=crti.o','-print-file-name=crtn.o','-print-file-name=libc.a','-print-file-name=libgcc.a'):
        output,_=command([cc,flag],environment=env,maximum=20)
        path=Path(output.decode().strip())
        if not path.is_absolute() or not path.resolve().is_relative_to(prefix):full_compiler_fail('search_path',flag)
        fd=full_compiler_open(path.resolve());os.close(fd)
    _,error=command([cc,'-E','-v',str(smoke/'lib.c')],environment=env,maximum=30)
    text=error.decode();start='#include <...> search starts here:';end='End of search list.'
    if text.count(start)!=1 or text.count(end)!=1:full_compiler_fail('include_search')
    paths=text.split(start,1)[1].split(end,1)[0].splitlines()
    if not paths or any(not Path(path.strip()).resolve().is_relative_to(prefix) for path in paths if path.strip()):
        full_compiler_fail('include_search')
    command([cc,'-O2','-fno-ident','-c',str(smoke/'lib.c'),'-o',str(smoke/'lib.o')],environment=env,maximum=60)
    obj=full_compiler_read(smoke/'lib.o',1024**2)
    if full_compiler_elf(obj)['kind']!=1:full_compiler_fail('object')
    command([ar,'rcsD',str(smoke/'libproof.a'),str(smoke/'lib.o')],environment=env,maximum=30)
    archive=full_compiler_read(smoke/'libproof.a',2*1024**2)
    if not archive.startswith(b'!<arch>\n'):full_compiler_fail('archive')
    at=8;members=[]
    while at<len(archive):
        if at+60>len(archive) or archive[at+58:at+60]!=b'`\n' or len(members)>8:full_compiler_fail('archive')
        name=archive[at:at+16].decode().strip();size=int(archive[at+48:at+58]);body=archive[at+60:at+60+size]
        if size<0 or len(body)!=size:full_compiler_fail('archive')
        if name not in ('/','//'):members.append((name.rstrip('/'),body))
        at+=60+size+(size%2)
    if members!=[('lib.o',obj)]:full_compiler_fail('archive_members')
    output,error=command([cc,'-static','-O2',str(smoke/'main.c'),str(smoke/'libproof.a'),'-Wl,-t','-o',str(smoke/'proof')],
                         environment=env,maximum=60)
    trace=output.decode().splitlines()
    if not trace:full_compiler_fail('link_trace')
    for line in trace:
        path=Path(line.strip())
        if not path.is_absolute() or not any(path.resolve().is_relative_to(root) for root in (prefix,smoke,WORK/'tmp')):
            full_compiler_fail('link_input',line)
    verify_static_arm64(smoke/'proof')
    output,error=command([str(smoke/'proof')],environment=env,maximum=10)
    if output!=(FULL_COMPILER_SENTINEL+'\n').encode() or error:full_compiler_fail('smoke_result')
    hashes={name:hashlib.sha256(full_compiler_read(smoke/name,2*1024**2)).hexdigest()
            for name in (*sources,'lib.o','libproof.a','proof')}
    remaining()
    return {'status':'compiler_probed','compiler_tree_sha256':report['compiler_tree_sha256'],'static_arm64':True,
        'sentinel':FULL_COMPILER_SENTINEL,'smoke_sha256':hashes,'search_paths_verified':True,'link_inputs_verified':True}
