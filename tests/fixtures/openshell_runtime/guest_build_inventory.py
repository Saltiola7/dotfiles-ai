"""Metadata-only inventory inside the already verified mounted build store.

Two bounded descriptor walks require unchanged identities and allocation. No
regular file or symlink is opened, and no symlink target is read. Logical bytes
count regular files and symlink lengths; allocated bytes include directories.
Exclusive bytes are an estimate for an entire top-level tree, not deletion
authority or a guarantee of recovered filesystem space. Unknown names remain
visible. The caller verifies unmount and worker shutdown after this returns.
"""
INVENTORY_MAX_ENTRIES = 200000
INVENTORY_MAX_DEPTH = 32
INVENTORY_MAX_ROOTS = 128
INVENTORY_ROOT_UID = INVENTORY_ROOT_GID = 0
INVENTORY_WORK_UID = INVENTORY_WORK_GID = 65534
INVENTORY_KNOWN = frozenset(('home', 'tmp', 'cargo', 'rustup', 'cache', 'target', 'downloads',
    'toolchain', 'toolchain-unwind-1', 'harness', 'unwind-bootstrap-1', 'resume-original-child_seccomp.rs',
    'unpack-0', 'unpack-1', 'unpack-2', 'unpack-unwind-1-0', 'unpack-unwind-1-1', 'unpack-unwind-1-2'))


def inventory_kind(mode):
    if stat.S_ISDIR(mode): return 'directory'
    if stat.S_ISREG(mode): return 'file'
    if stat.S_ISLNK(mode): return 'symlink'
    raise Refusal('inventory_special_file')


def inventory_snapshot(info):
    value = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
             info.st_nlink, info.st_size, info.st_blocks, info.st_mtime_ns, info.st_ctime_ns)
    if (any(type(number) is not int for number in value)
            or any(not 0 <= number < 2**64 for number in value[:8])
            or not 0 <= value[2] <= 0xffff or value[5] < 1
            or any(not -2**63 <= number < 2**63 for number in value[8:])):
        raise Refusal('inventory_metadata')
    inventory_kind(value[2])
    return value


def inventory_scan(work_fd, device):
    """Return path-relative metadata, checking directories before and after use."""
    _remaining(_work_end)
    root = inventory_snapshot(os.fstat(work_fd))
    if root[0] != device or inventory_kind(root[2]) != 'directory':
        raise Refusal('inventory_work_identity')
    nodes = {(): root}; directory_inodes = {(root[0], root[1])}

    def walk(fd, parts, depth):
        _remaining(_work_end)
        if depth > INVENTORY_MAX_DEPTH: raise Refusal('inventory_depth')
        before = inventory_snapshot(os.fstat(fd))
        if before != nodes[parts]: raise Refusal('inventory_changed')
        top_count = 0
        with os.scandir(fd) as entries:
            for entry in entries:
                _remaining(_work_end)
                if len(nodes) >= INVENTORY_MAX_ENTRIES: raise Refusal('inventory_entry_budget')
                if not parts:
                    top_count += 1
                    if top_count > INVENTORY_MAX_ROOTS: raise Refusal('inventory_top_budget')
                if entry.name in {'.', '..'} or '/' in entry.name or '\0' in entry.name:
                    raise Refusal('inventory_name')
                child_parts = parts + (entry.name,)
                info = inventory_snapshot(os.stat(entry.name, dir_fd=fd, follow_symlinks=False))
                if info[0] != device: raise Refusal('inventory_filesystem')
                if child_parts in nodes: raise Refusal('inventory_alias')
                nodes[child_parts] = info
                if inventory_kind(info[2]) == 'directory':
                    key = info[:2]
                    if key in directory_inodes: raise Refusal('inventory_directory_alias')
                    directory_inodes.add(key)
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                    try: walk(child, child_parts, depth+1)
                    finally: os.close(child)
                    if inventory_snapshot(os.stat(entry.name, dir_fd=fd, follow_symlinks=False)) != info:
                        raise Refusal('inventory_changed')
        if inventory_snapshot(os.fstat(fd)) != before: raise Refusal('inventory_changed')
        _remaining(_work_end)

    walk(work_fd, (), 0)
    return nodes


def inventory_space(fd):
    space = os.fstatvfs(fd)
    values = (space.f_blocks, space.f_frsize, space.f_bfree, space.f_bavail)
    if (any(type(value) is not int for value in values) or not 0 < values[1]
            or not 0 <= values[3] <= values[2] <= values[0]
            or not 0 < values[0]*values[1] < 2**63):
        raise Refusal('inventory_capacity')
    return (values[0]*values[1], values[2]*values[1], values[3]*values[1])


def inventory_usage(nodes):
    objects = {}; roots = {}
    for parts, info in nodes.items():
        _remaining(_work_end)
        kind = inventory_kind(info[2]); name = parts[0] if parts else None
        key = info[:2]
        if key not in objects:
            objects[key] = {'identity': info, 'kind': kind, 'roots': set(), 'paths': 0}
        item = objects[key]
        if item['identity'] != info: raise Refusal('inventory_changed')
        item['roots'].add(name); item['paths'] += 1
        if name is None: continue
        if name not in roots:
            top = nodes[(name,)]
            roots[name] = {'name': name, 'kind': inventory_kind(top[2]), 'known': name in INVENTORY_KNOWN,
                'device': top[0], 'inode': top[1], 'uid': top[3], 'gid': top[4], 'mode': top[2], 'nlink': top[5],
                'entry_count': 0, 'unique_inode_count': 0, 'logical_bytes': 0, 'allocated_bytes': 0,
                'exclusive_allocated_bytes': 0, 'shared_allocated_bytes': 0, 'hardlink_entries': 0, 'symlink_entries': 0}
        row = roots[name]; row['entry_count'] += 1
        row['symlink_entries'] += kind == 'symlink'
        row['hardlink_entries'] += kind != 'directory' and info[5] > 1
    totals = {'entry_count': len(nodes), 'unique_inode_count': len(objects), 'logical_bytes': 0,
        'allocated_bytes': 0, 'shared_allocated_bytes': 0, 'hardlink_entries': 0, 'symlink_entries': 0,
        'work_root_allocated_bytes': nodes[()][7]*512}
    for item in objects.values():
        _remaining(_work_end)
        info = item['identity']; kind = item['kind']; count = item['paths']; owners = item['roots']
        if kind != 'directory' and count > info[5]: raise Refusal('inventory_link_count')
        allocated = info[7]*512; logical = info[6] if kind != 'directory' else 0
        shared = len(owners) > 1 or (kind != 'directory' and count != info[5])
        totals['allocated_bytes'] += allocated; totals['logical_bytes'] += logical
        if shared: totals['shared_allocated_bytes'] += allocated
        if kind == 'symlink': totals['symlink_entries'] += count
        if kind != 'directory' and info[5] > 1: totals['hardlink_entries'] += count
        for name in owners - {None}:
            row = roots[name]; row['unique_inode_count'] += 1
            row['allocated_bytes'] += allocated; row['logical_bytes'] += logical
            row['shared_allocated_bytes' if shared else 'exclusive_allocated_bytes'] += allocated
    return [roots[name] for name in sorted(roots)], totals


def build_inventory():
    """Inspect only the active fixed store; no path or operation arguments."""
    _remaining(_work_end)
    if (type(_active) is not Store or _active.root != ROOT or _active.mount != ROOT/'store'
            or _active.work != WORK or WORK != ROOT/'store/work' or _active.size != IMAGE_BYTES):
        raise Refusal('inventory_active_store')
    root_fd = mount_fd = work_fd = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        root_fd = os.open(ROOT, flags)
        root = inventory_snapshot(os.fstat(root_fd))
        if (root[3:5] != (INVENTORY_ROOT_UID, INVENTORY_ROOT_GID)
                or stat.S_IMODE(root[2]) != 0o711): raise Refusal('inventory_root_identity')
        mount_fd = os.open('store', flags, dir_fd=root_fd)
        mount = inventory_snapshot(os.fstat(mount_fd))
        if (mount[3:5] != (INVENTORY_ROOT_UID, INVENTORY_ROOT_GID)
                or stat.S_IMODE(mount[2]) != 0o755): raise Refusal('inventory_mount_identity')
        work_fd = os.open('work', flags, dir_fd=mount_fd)
        work = inventory_snapshot(os.fstat(work_fd))
        if (work[0] != mount[0] or work[3:5] != (INVENTORY_WORK_UID, INVENTORY_WORK_GID)
                or stat.S_IMODE(work[2]) != 0o700): raise Refusal('inventory_work_identity')
        before = inventory_space(mount_fd)
        if not IMAGE_BYTES*3//4 < before[0] <= IMAGE_BYTES: raise Refusal('inventory_capacity')
        nodes = inventory_scan(work_fd, mount[0])
        again = inventory_scan(work_fd, mount[0])
        if nodes != again or inventory_space(mount_fd) != before: raise Refusal('inventory_changed')
        for fd, name, expected in ((root_fd, 'store', mount), (mount_fd, 'work', work)):
            if inventory_snapshot(os.stat(name, dir_fd=fd, follow_symlinks=False)) != expected:
                raise Refusal('inventory_changed')
        if inventory_snapshot(os.fstat(root_fd)) != root: raise Refusal('inventory_changed')
        entries, totals = inventory_usage(nodes)
        root_free = inventory_space(root_fd)[2]
        _remaining(_work_end)
        return {'schema_version': 1, 'status': 'inventoried', 'image_bytes': IMAGE_BYTES,
            'store_capacity_bytes': before[0], 'store_free_bytes': before[1], 'store_available_bytes': before[2],
            'root_free_bytes': root_free, 'work': str(WORK), 'entries': entries, 'totals': totals,
            'build_enabled': False, 'session_enabled': False}
    except OSError:
        raise Refusal('inventory_observation') from None
    finally:
        for fd in (work_fd, mount_fd, root_fd):
            if fd is not None: os.close(fd)
