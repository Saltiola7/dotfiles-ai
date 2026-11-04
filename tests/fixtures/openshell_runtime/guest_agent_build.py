"""Prepare the closed comparison fixture, then build it offline in a separate unit.

The caller revalidates Rust/compiler inputs and applies the existing storage,
time and service limits. No agent executes here and no qualification is inferred.
"""
import tomllib

agent_build_before = '14c06d0d2c33a56b9a075f469a16436b92cc101186ef19a00a4f1ab84871fa0f'
agent_build_after = '57a91bdc412ceb124da0b409f841420de35b692b07db0e806cd888c3ab7a3bb1'
agent_build_libc = '3eaf3ede3fee6db1a4c2ee091bf8a8b4dccdc6d17f656fb07896ee72867612f2'
agent_build_child = 'crates/openshell-sandbox/src/linux/child_seccomp.rs'
agent_build_names = ('Cargo.toml', 'Cargo.lock', 'src/main.rs',
                     'src/upstream_child_seccomp.rs', 'src/patched_child_seccomp.rs')


def agent_build_fail(reason):
    raise RuntimeError('agent_build_' + reason)


def agent_build_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def agent_build_open(path, *, directory=False):
    """Return an owned descriptor after a no-follow walk from the fixed work root."""
    remaining()
    try: parts = path.relative_to(WORK).parts
    except ValueError: agent_build_fail('path')
    if '..' in parts or WORK.resolve() != WORK: agent_build_fail('path')
    fd = None
    try:
        fd = os.open(WORK, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY | os.O_CLOEXEC)
        device = os.fstat(fd).st_dev
        for index, part in enumerate((None, *parts)):
            isdir = index < len(parts) or directory
            if part is not None:
                child = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
                                | (os.O_DIRECTORY if isdir else 0), dir_fd=fd)
                os.close(fd); fd = child
            info = os.fstat(fd)
            if (info.st_dev != device or info.st_uid != os.getuid() or info.st_gid != os.getgid()
                    or info.st_mode & 0o7022
                    or not (stat.S_ISDIR(info.st_mode) if isdir else stat.S_ISREG(info.st_mode))
                    or (not isdir and info.st_nlink != 1)):
                agent_build_fail('identity')
        result = fd; fd = None
        return result
    except OSError: agent_build_fail('open')
    finally:
        if fd is not None: os.close(fd)


def agent_build_read(path, limit):
    fd = agent_build_open(path)
    try:
        before = agent_build_identity(os.fstat(fd))
        if not 0 < before[6] <= limit: agent_build_fail('read_size')
        raw = bytearray()
        while len(raw) < before[6]:
            remaining(); block = os.read(fd, min(65536, before[6]-len(raw)))
            if not block: agent_build_fail('short_read')
            raw.extend(block)
        if (agent_build_identity(os.fstat(fd)) != before
                or agent_build_identity(path.lstat()) != before): agent_build_fail('read_changed')
        return bytes(raw)
    finally: os.close(fd)


def agent_build_files(payload):
    """The source-bound transport carries exactly one local package and libc."""
    try:
        files = payload['fixture_files']
        if type(files) is not dict or set(files) != set(agent_build_names[:3]): agent_build_fail('files')
        if any(type(raw) is not str or not 0 < len(raw.encode()) <= (10240 if name == 'src/main.rs' else 4096)
               for name, raw in files.items()): agent_build_fail('files')
        manifest = tomllib.loads(files['Cargo.toml']); lock = tomllib.loads(files['Cargo.lock'])
        expected = {'package': {'name': 'openshell-agent-filter-probe', 'version': '0.1.0', 'edition': '2024'},
                    'dependencies': {'libc': '=0.2.189'}}
        if manifest != expected: agent_build_fail('manifest')
        packages = [{'name': 'libc', 'version': '0.2.189',
                     'source': 'registry+https://github.com/rust-lang/crates.io-index', 'checksum': agent_build_libc},
                    {'name': 'openshell-agent-filter-probe', 'version': '0.1.0', 'dependencies': ['libc']}]
        if lock != {'version': 4, 'package': packages}: agent_build_fail('lock')
        return {name: raw.encode() for name, raw in files.items()}
    except (KeyError, TypeError, ValueError, UnicodeError): agent_build_fail('files')


def agent_build_report(files, status='agent_fixture_prepared'):
    return {'schema_version': 1, 'generation': 1, 'status': status,
            'source_sha256': {name: hashlib.sha256(files[name]).hexdigest() for name in agent_build_names},
            'session_enabled': False, 'full_runtime_qualified': False, 'compatibility_qualified': False}


def agent_build_scan(files):
    root = WORK/'agent-fixture-1'
    for directory, expected in ((root, {'Cargo.toml', 'Cargo.lock', 'src'}),
                                (root/'src', {Path(name).name for name in agent_build_names[2:]})):
        fd = agent_build_open(directory, directory=True)
        try:
            if stat.S_IMODE(os.fstat(fd).st_mode) != 0o700: agent_build_fail('directory_mode')
            with os.scandir(fd) as entries:
                found = set()
                for entry in entries:
                    if entry.name not in expected or entry.name in found: agent_build_fail('entries')
                    found.add(entry.name)
            if found != expected: agent_build_fail('entries')
        finally: os.close(fd)
    for name, raw in files.items():
        path = root/name
        if stat.S_IMODE(path.lstat().st_mode) != 0o400 or agent_build_read(path, 128*1024) != raw:
            agent_build_fail('source_changed')


def agent_build_prepare(payload):
    files = agent_build_files(payload)
    patched = agent_build_read(WORK/'full-source-2'/agent_build_child, 128*1024)
    if hashlib.sha256(patched).hexdigest() != agent_build_after: agent_build_fail('patched_source')
    local = {'full_manifest': payload['full_manifest'], 'patched_sha256': agent_build_after,
             'files': {'src/linux/child_seccomp.rs': patched.decode()}}
    full_source_start(local, min(300, max(1, int(remaining(300)))))
    inputs = WORK/'full-source-inputs-1'
    fd = full_source_open(inputs, directory=True)
    try:
        with os.scandir(fd) as entries:
            found = set()
            for item in entries:
                if item.name not in {'tree.json', 'source.tar.gz'} or item.name in found: agent_build_fail('inputs')
                found.add(item.name)
            if found != {'tree.json', 'source.tar.gz'}: agent_build_fail('inputs')
    finally: os.close(fd)
    entries = full_source_tree(full_source_read(inputs/'tree.json', full_source_contract['metadata_limit']))
    original = full_source_archive(full_source_read(inputs/'source.tar.gz', full_source_contract['compressed_limit']), entries)
    upstream = original[agent_build_child]
    if hashlib.sha256(upstream).hexdigest() != agent_build_before: agent_build_fail('upstream_source')
    derived = full_source_network_transform(full_source_transform(original, patched))
    full_source_scan(WORK/'full-source-2', entries, derived)
    files.update({'src/upstream_child_seccomp.rs': upstream, 'src/patched_child_seccomp.rs': patched})
    root = WORK/'agent-fixture-1'; fd = agent_build_open(WORK, directory=True)
    try:
        os.mkdir(root.name, 0o700, dir_fd=fd); os.fsync(fd)
    except OSError: agent_build_fail('generation_exists_or_publish_failed')
    finally: os.close(fd)
    full_source_mkdir(root/'src')
    for name in agent_build_names: full_source_write(root/name, files[name], 0o400)
    agent_build_scan(files)
    full_source_scan(WORK/'full-source-2', entries, derived)
    return agent_build_report(files)


def agent_build_retained(payload):
    if 'fixture_files' in payload: agent_build_fail('compile_input')
    try:
        selected = {name: agent_build_read(WORK/'agent-fixture-1'/name,
                    10240 if name == 'src/main.rs' else 4096).decode() for name in agent_build_names[:3]}
    except UnicodeError: agent_build_fail('files')
    files = agent_build_files({'fixture_files': selected})
    for name, expected in zip(agent_build_names[3:], (agent_build_before, agent_build_after)):
        raw = agent_build_read(WORK/'agent-fixture-1'/name, 128*1024)
        if hashlib.sha256(raw).hexdigest() != expected: agent_build_fail('module_hash')
        files[name] = raw
    report = payload.get('agent_build_report')
    if (type(report) is not dict or type(report.get('schema_version')) is not int
            or type(report.get('generation')) is not int
            or any(report.get(key) is not False for key in
                   ('session_enabled', 'full_runtime_qualified', 'compatibility_qualified'))
            or report != agent_build_report(files)): agent_build_fail('preparation_report')
    agent_build_scan(files)
    root = WORK/'agent-fixture-1'
    for base in (root, *root.parents):
        if base != root and os.path.lexists(base/'Cargo.toml'): agent_build_fail('cargo_workspace')
        for name in ('config', 'config.toml', 'credentials', 'credentials.toml'):
            if os.path.lexists(base/'.cargo'/name): agent_build_fail('cargo_config')
    return files


def agent_build_usage():
    """Measure target growth once per inode; this is a rejection cap, not a quota."""
    root = WORK/'full-target-1'; pending = [(root, 0)]; seen = set(); logical = allocated = count = 0
    device = WORK.stat().st_dev
    while pending:
        directory, depth = pending.pop(); remaining()
        if depth > 32: agent_build_fail('target_budget')
        fd = agent_build_open(directory, directory=True)
        try:
            with os.scandir(fd) as entries:
                for entry in entries:
                    count += 1; remaining()
                    if count > 200000: agent_build_fail('target_budget')
                    info = entry.stat(follow_symlinks=False)
                    if info.st_dev != device or info.st_uid != os.getuid() or info.st_gid != os.getgid():
                        agent_build_fail('target_identity')
                    if stat.S_ISDIR(info.st_mode): pending.append((directory/entry.name, depth+1))
                    elif stat.S_ISREG(info.st_mode):
                        key = (info.st_dev, info.st_ino)
                        if key not in seen:
                            seen.add(key); logical += info.st_size; allocated += info.st_blocks*512
                    else: agent_build_fail('target_identity')
        finally: os.close(fd)
    return logical, allocated


def agent_build_compile(payload):
    files = agent_build_retained(payload)
    full_cargo_cache(payload)
    source = WORK/'agent-fixture-1'; binary = WORK/'full-target-1/release/openshell-agent-filter-probe'
    if os.path.lexists(binary): agent_build_fail('binary_exists')
    before = agent_build_usage()
    cargo = str(WORK/TOOLCHAIN/'bin/cargo')
    command([cargo, 'build', '--release', '--locked', '--offline', '--bin', 'openshell-agent-filter-probe',
             '--message-format=human'], cwd=source, maximum=300, environment=full_cargo_environment(offline=True))
    after = agent_build_usage(); space = os.statvfs(WORK)
    if (any(end-start > 64*1024**2 for start, end in zip(before, after))
            or space.f_bavail*space.f_frsize < 256*1024**2): agent_build_fail('growth_or_reserve')
    agent_build_retained(payload)
    with full_cargo_runtime_artifact('agent-probe') as (fd, layout):
        value = full_cargo_runtime_digest(fd, 'agent-probe'); size = os.fstat(fd).st_size
        if size > 64*1024**2: agent_build_fail('binary_size')
        if verify_static_arm64(Path(f'/proc/self/fd/{fd}')) != value: agent_build_fail('static_hash_changed')
        if full_cargo_runtime_digest(fd, 'agent-probe') != value: agent_build_fail('binary_changed')
    return dict(agent_build_report(files, 'agent_fixture_built'), binary_sha256=value,
                binary_bytes=size, binary_layout=layout, static_arm64=True)
