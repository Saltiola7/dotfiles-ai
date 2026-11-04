"""Explicit offline reuse of authenticated inputs; no installer or network fallback.

Appended to the fixed harness and unwind verifier. All mutation remains inside
the existing work filesystem: preserve one old source, publish its reviewed
replacement, and create one fresh target directory. Source checks are not native
qualification. The caller owns the deadline and isolated service lifecycle.
"""
import re as resume_re
import tomllib as resume_toml

RESUME_OLD_SHA = '259e77596f3f70ee28bdd8672f4747f3462f4c727b609e92d782cf749782ccb3'
RESUME_LIMIT = 2 * 1024**3


def resume_fail(reason, path=''):
    raise RuntimeError('resume_' + reason + ':' + str(path)[:512])


def resume_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def resume_owned(info, path, *, directory=False):
    if (info.st_uid != os.getuid() or info.st_gid != os.getgid()
            or info.st_dev != WORK.lstat().st_dev or info.st_mode & 0o022
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        resume_fail('identity', path)


def resume_open(path, *, directory=False):
    remaining()
    try:
        parts = path.relative_to(WORK).parts
        if '..' in parts or path != WORK.joinpath(*parts) or WORK.resolve() != WORK:
            resume_fail('path', path)
        fd = os.open(WORK, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            resume_owned(os.fstat(fd), WORK, directory=True)
            for index, part in enumerate(parts):
                isdir = index < len(parts)-1 or directory
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                child = os.open(part, flags | (os.O_DIRECTORY if isdir else 0), dir_fd=fd)
                os.close(fd); fd = child
                resume_owned(os.fstat(fd), path, directory=isdir)
            return fd
        except BaseException:
            os.close(fd); raise
    except OSError:
        resume_fail('open', path)


def resume_read(path, limit, expected=None):
    fd = resume_open(path)
    try:
        before = os.fstat(fd)
        if before.st_size > limit or (expected is not None and before.st_size != expected):
            resume_fail('size', path)
        data = bytearray()
        while True:
            remaining(); chunk = os.read(fd, min(65536, limit+1-len(data)))
            if not chunk: break
            data.extend(chunk)
            if len(data) > limit: resume_fail('size', path)
        if resume_identity(before) != resume_identity(os.fstat(fd)) or len(data) != before.st_size:
            resume_fail('changed', path)
        return bytes(data)
    finally: os.close(fd)


def resume_compare(path, stream, size, mode=None):
    fd = resume_open(path)
    try:
        before = os.fstat(fd)
        if before.st_size != size or (mode is not None and before.st_mode & 0o111 != mode & 0o111):
            resume_fail('size_mode', path)
        count = 0; value = hashlib.sha256()
        while count < size:
            remaining(); wanted = min(65536, size-count)
            actual = os.read(fd, wanted); expected = stream.read(wanted)
            if len(actual) != wanted or actual != expected: resume_fail('content', path)
            count += wanted; value.update(expected)
        if resume_identity(before) != resume_identity(os.fstat(fd)):
            resume_fail('changed', path)
        return value.hexdigest()
    finally: os.close(fd)


def resume_hash(path, limit, expected=None):
    fd = resume_open(path)
    try:
        before = os.fstat(fd)
        if before.st_size > limit or (expected is not None and before.st_size != expected):
            resume_fail('size', path)
        value = hashlib.sha256(); count = 0
        while True:
            remaining(); chunk = os.read(fd, 65536)
            if not chunk: break
            value.update(chunk); count += len(chunk)
            if count > limit: resume_fail('size', path)
        if count != before.st_size or resume_identity(before) != resume_identity(os.fstat(fd)):
            resume_fail('changed', path)
        return value.hexdigest()
    finally: os.close(fd)


def resume_tree(root):
    leaves = {}; directories = {''}; pending = [root]; count = 0
    while pending:
        remaining(); path = pending.pop(); fd = resume_open(path, directory=True)
        try:
            with os.scandir(fd) as entries:
                for entry in entries:
                    remaining(); count += 1
                    if count > 30000: resume_fail('entry_budget', root)
                    child = path / entry.name; key = str(child.relative_to(root))
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        resume_owned(info, child, directory=True)
                        directories.add(key); pending.append(child)
                    elif stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode): leaves[key] = info
                    else: resume_fail('file_type', child)
        finally: os.close(fd)
    return leaves, directories


def resume_parents(names):
    return {''} | {str(parent) for name in names for parent in PurePosixPath(name).parents if str(parent) != '.'}


def resume_exact_tree(root, names, extras=(), directories=()):
    leaves, dirs = resume_tree(root)
    if set(leaves) - set(names) - set(extras) or set(names) - set(leaves):
        resume_fail('tree_entries', root)
    permitted = set(names) | set(directories) | (set(leaves) & set(extras))
    if dirs - resume_parents(permitted) - set(directories):
        resume_fail('tree_directories', root)
    return leaves


def resume_rust(payload):
    prefix = WORK / TOOLCHAIN; names = set(); links = {}; total = 0; directories = set()
    parts = {'cargo', 'rustc', 'rust-std'}
    items = payload['toolchain']['artifacts']
    expected = {f'{part}-1.95.0-{HOST}.tar.xz' for part in parts}
    if len(items) != 3 or {item['archive'] for item in items} != expected:
        resume_fail('archive_set')
    for item in items:
        path = WORK / 'downloads' / item['archive']
        if resume_hash(path, 128*1024**2, item['bytes']) != item['sha256']:
            resume_fail('archive_digest', path)
        root = item['archive'].removesuffix('.tar.xz')
        component = next(part for part in parts if root.startswith(part+'-1.95.0-'))
        if component == 'rust-std': component += '-' + HOST
        seen = set()
        with tarfile.open(path, 'r:xz') as tar:
            for member in tar:
                remaining(); name = PurePosixPath(member.name)
                if (len(seen) >= 30000 or member.name in seen or name.is_absolute()
                        or '..' in name.parts or not name.parts or name.parts[0] != root
                        or len(member.name) > 512 or not (member.isfile() or member.isdir() or member.issym())):
                    resume_fail('archive_member', member.name)
                seen.add(member.name); total += member.size
                if total > RESUME_LIMIT: resume_fail('archive_expansion')
                if len(name.parts) < 3 or name.parts[1] != component or name.parts[2] not in {'bin', 'lib'}:
                    continue
                relative = str(PurePosixPath(*name.parts[2:]))
                if member.isdir(): directories.add(relative); continue
                if relative in names: resume_fail('archive_duplicate', relative)
                names.add(relative); installed = prefix / relative
                if member.issym():
                    links[relative] = member.linkname
                    info = installed.lstat()
                    if (not stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or info.st_gid != os.getgid()
                            or info.st_dev != WORK.lstat().st_dev or os.readlink(installed) != member.linkname):
                        resume_fail('link', installed)
                else:
                    with tar.extractfile(member) as stream: resume_compare(installed, stream, member.size, member.mode)
    for name, target in links.items():
        if PurePosixPath(target).is_absolute(): resume_fail('link_escape', name)
        installed = prefix / name
        resolved = installed.resolve()
        if not resolved.is_relative_to(prefix) or str(resolved.relative_to(prefix)) not in names:
            resume_fail('link_escape', name)
        fd = resume_open(resolved); os.close(fd)
    metadata = {'lib/rustlib/' + name for name in ('components', 'rust-installer-version', 'uninstall.sh',
                'install.log', 'manifest-cargo', 'manifest-rustc', 'manifest-rust-std-'+HOST)}
    names.add('lib/libgcc_s.so.1')
    for directory in ('bin', 'lib'):
        selected = {name[len(directory)+1:] for name in names if name.startswith(directory+'/')}
        extra = {name[len(directory)+1:] for name in metadata if name.startswith(directory+'/')}
        declared = {name[len(directory)+1:] for name in directories if name.startswith(directory+'/')}
        leaves = resume_exact_tree(prefix / directory, selected, extra, declared)
        for name in set(leaves) & extra: resume_read(prefix / directory / name, 1024*1024)
    return len(names)


def resume_cargo(payload):
    for ancestor in (WORK/'harness', WORK, WORK/'home', *WORK.parents):
        for suffix in ('config', 'config.toml'):
            if os.path.lexists(ancestor / '.cargo' / suffix): resume_fail('cargo_config', ancestor)
    for suffix in ('config', 'config.toml', 'credentials', 'credentials.toml'):
        if os.path.lexists(WORK / 'cargo' / suffix): resume_fail('cargo_config', suffix)
    records = resume_toml.loads(payload['files']['Cargo.lock'])['package']; packages = {}
    for record in records:
        if 'source' not in record: continue
        if (record['source'] != 'registry+https://github.com/rust-lang/crates.io-index'
                or resume_re.fullmatch('[A-Za-z0-9_-]+', record['name']) is None
                or resume_re.fullmatch('[A-Za-z0-9_.+-]+', record['version']) is None
                or resume_re.fullmatch('[a-f0-9]{64}', record['checksum']) is None): resume_fail('cargo_lock')
        name = record['name']+'-'+record['version']
        if name in packages or len(packages) >= 32: resume_fail('cargo_lock')
        packages[name] = record['checksum']
    base = WORK / 'cargo/registry'; cache = base/'cache'; fd = resume_open(cache, directory=True)
    try:
        with os.scandir(fd) as entries:
            selected = next(entries, None)
            if (selected is None or next(entries, None) is not None
                    or resume_re.fullmatch('index.crates.io-[a-f0-9]{16}', selected.name) is None): resume_fail('cargo_registry')
            registry = selected.name
    finally: os.close(fd)
    resume_exact_tree(cache/registry, {name+'.crate' for name in packages})
    fd = resume_open(base/'src', directory=True)
    try:
        with os.scandir(fd) as entries:
            selected = next(entries, None)
            if selected is None or selected.name != registry or next(entries, None) is not None:
                resume_fail('cargo_source_registry')
    finally: os.close(fd)
    source = base/'src'/registry
    leaves, dirs = resume_tree(source)
    if ({name.split('/')[0] for name in leaves} != set(packages)
            or {name.split('/')[0] for name in dirs if name} != set(packages)):
        resume_fail('cargo_source_set')
    total = 0
    for name, expected in packages.items():
        path = cache/registry/(name+'.crate')
        if resume_hash(path, 32*1024**2) != expected: resume_fail('crate_digest', name)
        names = set(); seen = set(); directories = set(); file_hashes = {}
        with tarfile.open(path, 'r:gz') as tar:
            for member in tar:
                remaining(); entry = PurePosixPath(member.name)
                if (len(seen) >= 30000 or member.name in seen or entry.is_absolute() or '..' in entry.parts
                        or len(entry.parts) < 1 or entry.parts[0] != name or len(member.name) > 512
                        or not (member.isfile() or member.isdir())): resume_fail('crate_member', member.name)
                seen.add(member.name); total += member.size
                if total > 256*1024**2: resume_fail('crate_expansion')
                relative = str(PurePosixPath(*entry.parts[1:]))
                if member.isdir():
                    if relative != '.': directories.add(relative)
                    continue
                names.add(relative)
                with tar.extractfile(member) as stream:
                    file_hashes[relative] = resume_compare(source/name/relative, stream, member.size)
        entries = resume_exact_tree(source/name, names, {'.cargo-ok', '.cargo-checksum.json'}, directories)
        if '.cargo-ok' in entries and '.cargo-ok' not in names:
            if resume_read(source/name/'.cargo-ok', 128).strip() not in (b'', b'{"v":1}'): resume_fail('cargo_marker', name)
        if '.cargo-checksum.json' in entries and '.cargo-checksum.json' not in names:
            value = json.loads(resume_read(source/name/'.cargo-checksum.json', 2*1024**2))
            if (set(value) != {'files', 'package'} or value['package'] != expected
                    or type(value['files']) is not dict or value['files'] not in ({}, file_hashes)):
                resume_fail('cargo_checksum', name)
    return len(packages)


def resume_write(path, raw, mode):
    parent = resume_open(path.parent, directory=True)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw); stream.flush(); os.fsync(fd)
        finally: os.close(fd)
    finally: os.close(parent)


def resume(payload):
    remaining(); target = WORK/'target/resume-1'
    if os.path.lexists(target): resume_fail('target_present', target)
    fd = resume_open(target.parent, directory=True); os.close(fd)
    files = payload['files']; subject = 'src/linux/child_seccomp.rs'; source = WORK/'harness'
    if set(files) != {'Cargo.toml', 'Cargo.lock', 'src/lib.rs', subject}: resume_fail('source_set')
    resume_exact_tree(source, files)
    for name, text in files.items():
        raw = resume_read(source/name, 128*1024)
        if name != subject and raw != text.encode(): resume_fail('source_content', name)
    old = resume_read(source/subject, 128*1024); old_hash = hashlib.sha256(old).hexdigest()
    new = files[subject].encode(); new_hash = hashlib.sha256(new).hexdigest()
    backup = WORK/'resume-original-child_seccomp.rs'; temporary = source/'src/linux/.child_seccomp.resume.tmp'
    if new_hash != payload['patched_sha256'] or old_hash not in {RESUME_OLD_SHA, new_hash}:
        resume_fail('source_identity')
    if os.path.lexists(temporary): resume_fail('source_partial', temporary)
    saved = os.path.lexists(backup)
    if saved and hashlib.sha256(resume_read(backup, 128*1024)).hexdigest() != RESUME_OLD_SHA:
        resume_fail('source_backup')
    if old_hash == new_hash and not saved: resume_fail('source_backup_missing')
    inputs = resume_rust(payload)
    proof, library = unwind_verify()
    if resume_read(WORK/TOOLCHAIN/'lib/libgcc_s.so.1', 1024**2) != library: resume_fail('unwind_content')
    packages = resume_cargo(payload)
    remaining()
    if old_hash != new_hash:
        if not saved: resume_write(backup, old, 0o400)
        resume_write(temporary, new, 0o600)
        if resume_read(source/subject, 128*1024) != old: resume_fail('source_changed')
        parent = resume_open(temporary.parent, directory=True)
        try: os.replace(temporary.name, 'child_seccomp.rs', src_dir_fd=parent, dst_dir_fd=parent); os.fsync(parent)
        finally: os.close(parent)
    parent = resume_open(target.parent, directory=True)
    try: os.mkdir(target.name, 0o700, dir_fd=parent)
    finally: os.close(parent)
    remaining()
    return {'offline_reuse_verified': True, 'verified_toolchain_inputs': inputs,
            'verified_cached_packages': packages, 'unwind': proof, 'old_source_sha256': RESUME_OLD_SHA,
            'patched_source_sha256': new_hash, 'target': str(target)}
