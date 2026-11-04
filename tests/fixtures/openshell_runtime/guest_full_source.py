"""Fixed complete-source admission for the optional OpenShell build.

Appended after guest_harness.py. Downloads and all writes stay in the selected
work filesystem. Verification is offline and read-only. Source tests do not
establish native compilation or runtime containment.
"""
import io as full_source_io
import re as full_source_re
import tomllib as full_source_toml
import zlib as full_source_zlib

full_source_commit = '5d25211b25a8fc887e8d5c606d57d6ab22f1d76c'
full_source_tree_sha1 = '053850cd069ba0f770d8296eae6be36d6cf52da7'
full_source_version = '0.1.7+dotfiles-ai.child-unix-deny.2'
full_source_child = 'crates/openshell-sandbox/src/linux/child_seccomp.rs'
full_source_child_before = '14c06d0d2c33a56b9a075f469a16436b92cc101186ef19a00a4f1ab84871fa0f'
full_source_child_after = '57a91bdc412ceb124da0b409f841420de35b692b07db0e806cd888c3ab7a3bb1'
full_source_link = '.claude/skills'
full_source_link_target = '../.agents/skills/'
full_source_end = 0.0
full_source_contract = {
    "metadata_url": "https://api.github.com/repos/NVIDIA/OpenShell/git/trees/053850cd069ba0f770d8296eae6be36d6cf52da7?recursive=1",
    "archive_url": "https://codeload.github.com/NVIDIA/OpenShell/tar.gz/5d25211b25a8fc887e8d5c606d57d6ab22f1d76c",
    "entries": 2685,
    "blobs": 2196,
    "blob_bytes": 42874582,
    "metadata_limit": 1048576,
    "compressed_limit": 33554432,
    "expanded_limit": 67108864,
    "members_limit": 4096,
    "original_manifest_sha256": "776988371f2df32a67bee004b1d4221e1190d77bb961b4ad91aab35c882fc0e0",
    "derived_manifest_sha256": "34e54d9334e5938d4ce0ccbb52f2b028fdb685d60242db0421409c4fcc446c55",
    "original_lock_sha256": "819e04aa814edfa23da5fbafa85d3000f58f981a3fcd94162c3f7af128809e7f",
    "derived_lock_sha256": "90fd65d3e8220fc912b27d29c3943aaf23d8ce4fd37810dc6c3fc34e686552ae",
    "local_packages": 39,
    "external_packages": 830
}
full_source_local_names = (
    'openshell-binary-identity',
    'openshell-bootstrap',
    'openshell-cli',
    'openshell-conformance',
    'openshell-core',
    'openshell-crypto',
    'openshell-driver-db-credstore',
    'openshell-driver-docker',
    'openshell-driver-kubernetes',
    'openshell-driver-kubernetes-secrets',
    'openshell-driver-mxc',
    'openshell-driver-podman',
    'openshell-driver-vault',
    'openshell-driver-vm',
    'openshell-extension-core',
    'openshell-gateway',
    'openshell-gateway-interceptors',
    'openshell-isolation-interface',
    'openshell-ocsf',
    'openshell-ocsf-validate',
    'openshell-otel',
    'openshell-otel-test-support',
    'openshell-policy',
    'openshell-policy-schema',
    'openshell-prover',
    'openshell-prover-cli',
    'openshell-providers',
    'openshell-sandbox',
    'openshell-sandbox-backend',
    'openshell-sdk',
    'openshell-server',
    'openshell-supervisor',
    'openshell-supervisor-control',
    'openshell-supervisor-middleware',
    'openshell-supervisor-middleware-builtins',
    'openshell-supervisor-network',
    'openshell-supervisor-process',
    'openshell-tui',
    'openshell-vfio',
)


def full_source_fail(reason):
    raise RuntimeError('full_source_' + reason)


def full_source_remaining(maximum=30):
    left = full_source_end - time.monotonic()
    if left <= 0:
        full_source_fail('deadline')
    return min(left, maximum)


def full_source_start(payload, seconds):
    global full_source_end
    if type(seconds) is not int or not 1 <= seconds <= 1500:
        full_source_fail('seconds')
    full_source_end = min(time.monotonic() + seconds, DEADLINE)
    full_source_remaining()
    try:
        manifest = payload['full_manifest']
        patched = payload['files']['src/linux/child_seccomp.rs']
        if (type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
                or manifest['upstream_commit'] != full_source_commit
                or manifest['upstream_tree_sha1'] != full_source_tree_sha1
                or manifest['experimental_version'] != full_source_version
                or manifest['source'] != full_source_contract
                or manifest['cargo']['source'] != 'full-source-1'
                or type(patched) is not str or len(patched.encode()) > 128*1024
                or payload['patched_sha256'] != full_source_child_after
                or hashlib.sha256(patched.encode()).hexdigest() != full_source_child_after):
            full_source_fail('contract')
        return patched.encode()
    except (KeyError, TypeError, UnicodeError):
        full_source_fail('contract')


def full_source_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def full_source_owned(info, path, *, directory=False, symlink=False):
    valid = stat.S_ISDIR(info.st_mode) if directory else (
        stat.S_ISLNK(info.st_mode) if symlink else stat.S_ISREG(info.st_mode))
    if (not valid or info.st_dev != WORK.lstat().st_dev
            or info.st_uid != os.getuid() or info.st_gid != os.getgid()
            or (not directory and info.st_nlink != 1)
            or (not symlink and info.st_mode & 0o7022)):
        full_source_fail('file_identity')


def full_source_open(path, *, directory=False):
    full_source_remaining()
    try:
        parts = path.relative_to(WORK).parts
        if '..' in parts or path != WORK.joinpath(*parts) or WORK.resolve() != WORK:
            full_source_fail('path')
        fd = os.open(WORK, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            full_source_owned(os.fstat(fd), WORK, directory=True)
            for index, part in enumerate(parts):
                isdir = index < len(parts)-1 or directory
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                child = os.open(part, flags | (os.O_DIRECTORY if isdir else 0), dir_fd=fd)
                os.close(fd); fd = child
                full_source_owned(os.fstat(fd), path, directory=isdir)
            return fd
        except BaseException:
            os.close(fd)
            raise
    except OSError:
        full_source_fail('open')


def full_source_read(path, limit):
    fd = full_source_open(path)
    try:
        before = os.fstat(fd)
        if before.st_size > limit:
            full_source_fail('read_size')
        raw = bytearray()
        while True:
            full_source_remaining()
            chunk = os.read(fd, min(65536, limit+1-len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > limit:
                full_source_fail('read_size')
        if (len(raw) != before.st_size or full_source_identity(before) != full_source_identity(os.fstat(fd))
                or full_source_identity(before) != full_source_identity(path.lstat())):
            full_source_fail('read_changed')
        return bytes(raw)
    except OSError:
        full_source_fail('read')
    finally:
        os.close(fd)


def full_source_mkdir(path):
    parent = full_source_open(path.parent, directory=True)
    try:
        try:
            os.mkdir(path.name, 0o700, dir_fd=parent)
        except FileExistsError:
            pass
        fd = full_source_open(path, directory=True)
        os.close(fd)
    except OSError:
        full_source_fail('mkdir')
    finally:
        os.close(parent)


def full_source_write(path, raw, mode):
    parent = full_source_open(path.parent, directory=True)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw); stream.flush(); os.fchmod(fd, mode); os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(parent)
    except OSError:
        full_source_fail('write')
    finally:
        os.close(parent)


class full_source_NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        full_source_fail('redirect')


def full_source_fetch(path, url, limit):
    if os.path.lexists(path):
        full_source_read(path, limit)
        return
    partial = path.with_name(path.name + '.partial')
    parent = full_source_open(path.parent, directory=True)
    try:
        fd = os.open(partial.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), full_source_NoRedirect())
            request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json'})
            with os.fdopen(fd, 'wb', closefd=False) as output:
                with opener.open(request, timeout=full_source_remaining(20)) as response:
                    if response.status != 200 or response.url != url:
                        full_source_fail('transport')
                    count = 0
                    while True:
                        full_source_remaining()
                        chunk = response.read1(min(65536, limit+1-count))
                        if not chunk:
                            break
                        count += len(chunk)
                        if count > limit:
                            full_source_fail('download_size')
                        output.write(chunk)
                output.flush(); os.fsync(fd)
        finally:
            os.close(fd)
        full_source_remaining()
        os.link(partial.name, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.unlink(partial.name, dir_fd=parent)
        os.fsync(parent)
    except OSError:
        full_source_fail('download')
    finally:
        os.close(parent)


def full_source_json_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            full_source_fail('duplicate_json')
        value[key] = item
    return value


def full_source_path(name):
    if (type(name) is not str or not name or len(name.encode()) > 512 or '\0' in name
            or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))
            or len(name.split('/')) > 32):
        full_source_fail('entry_path')
    return name


def full_source_object(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def full_source_tree(raw):
    try:
        data = json.loads(raw, object_pairs_hook=full_source_json_pairs)
        if (type(data) is not dict or data.get('sha') != full_source_tree_sha1
                or data.get('truncated') is not False or type(data.get('tree')) is not list
                or len(data['tree']) != full_source_contract['entries']):
            full_source_fail('tree_shape')
        entries = {}; children = {'': []}; total = 0; blobs = 0
        for item in data['tree']:
            full_source_remaining()
            name = full_source_path(item['path'])
            mode = item['mode']; kind = item['type']; digest = item['sha']
            if (name in entries or type(digest) is not str
                    or full_source_re.fullmatch('[0-9a-f]{40}', digest) is None
                    or (mode, kind) not in {('040000', 'tree'), ('100644', 'blob'),
                                           ('100755', 'blob'), ('120000', 'blob')}):
                full_source_fail('tree_entry')
            if kind == 'blob':
                if type(item.get('size')) is not int or not 0 <= item['size'] <= full_source_contract['expanded_limit']:
                    full_source_fail('tree_size')
                total += item['size']; blobs += 1
                if mode == '120000' and name != full_source_link:
                    full_source_fail('tree_link')
            else:
                children[name] = []
            entries[name] = item
        if blobs != full_source_contract['blobs'] or total != full_source_contract['blob_bytes']:
            full_source_fail('tree_count')
        if entries.get(full_source_link, {}).get('mode') != '120000':
            full_source_fail('tree_link')
        for name, item in entries.items():
            parent = name.rpartition('/')[0]
            if parent not in children:
                full_source_fail('tree_parent')
            children[parent].append(item)
        for directory in sorted(children, key=lambda n: (n.count('/'), len(n)), reverse=True):
            full_source_remaining()
            values = sorted(children[directory], key=lambda v: v['path'].rsplit('/', 1)[-1].encode()
                            + (b'/' if v['type'] == 'tree' else b'\0'))
            body = b''.join((v['mode'].lstrip('0') + ' ' + v['path'].rsplit('/', 1)[-1]).encode()
                            + b'\0' + bytes.fromhex(v['sha']) for v in values)
            expected = entries[directory]['sha'] if directory else full_source_tree_sha1
            if full_source_object('tree', body) != expected:
                full_source_fail('tree_digest')
        return entries
    except (ValueError, TypeError, KeyError, UnicodeError):
        full_source_fail('tree_parse')


def full_source_archive(raw, entries):
    full_source_remaining()
    try:
        decoder = full_source_zlib.decompressobj(31)
        expanded = decoder.decompress(raw, full_source_contract['expanded_limit']+1)
        if (len(expanded) > full_source_contract['expanded_limit'] or not decoder.eof
                or decoder.unconsumed_tail or decoder.unused_data):
            full_source_fail('archive_expansion')
        root = 'OpenShell-' + full_source_commit
        seen = set(); files = {}; directories = set(); count = 0
        with tarfile.open(fileobj=full_source_io.BytesIO(expanded), mode='r:') as archive:
            for member in archive:
                full_source_remaining(); count += 1
                if count > full_source_contract['members_limit']:
                    full_source_fail('archive_members')
                name = member.name
                if member.isdir():
                    name = name.removesuffix('/')
                if name == root:
                    if not member.isdir() or '' in seen:
                        full_source_fail('archive_root')
                    seen.add(''); continue
                if not name.startswith(root + '/'):
                    full_source_fail('archive_root')
                relative = full_source_path(name[len(root)+1:])
                if relative in seen or relative not in entries:
                    full_source_fail('archive_entries')
                seen.add(relative); item = entries[relative]
                if member.mode & 0o7000:
                    full_source_fail('archive_mode')
                if member.isdir():
                    if item['mode'] != '040000':
                        full_source_fail('archive_type')
                    directories.add(relative); continue
                if member.issym():
                    if (item['mode'] != '120000' or relative != full_source_link
                            or member.linkname != full_source_link_target):
                        full_source_fail('archive_link')
                    body = member.linkname.encode()
                elif member.isfile():
                    if (item['mode'] not in ('100644', '100755') or member.size != item['size']
                            or bool(member.mode & 0o111) != (item['mode'] == '100755')):
                        full_source_fail('archive_mode')
                    with archive.extractfile(member) as stream:
                        body = stream.read(item['size']+1)
                else:
                    full_source_fail('archive_type')
                if len(body) != item['size'] or full_source_object('blob', body) != item['sha']:
                    full_source_fail('archive_blob')
                files[relative] = body
            # Reject a hidden second tar or non-padding data after the first EOF.
            if any(expanded[archive.offset:]):
                full_source_fail('archive_trailing')
        expected_files = {n for n, v in entries.items() if v['type'] == 'blob'}
        if set(files) != expected_files:
            full_source_fail('archive_missing')
        # Tar may omit explicit directory entries; validated parents are still
        # exactly the authenticated tree and are created by this helper.
        return files
    except (ValueError, KeyError, UnicodeError, OSError, tarfile.TarError, full_source_zlib.error):
        full_source_fail('archive_parse')


def full_source_transform(files, patched):
    value = dict(files)
    for name, key in (('Cargo.toml', 'original_manifest_sha256'), ('Cargo.lock', 'original_lock_sha256')):
        if hashlib.sha256(value[name]).hexdigest() != full_source_contract[key]:
            full_source_fail('original_digest')
    if hashlib.sha256(value[full_source_child]).hexdigest() != full_source_child_before:
        full_source_fail('child_preimage')
    try:
        manifest = value['Cargo.toml'].decode()
        original = full_source_toml.loads(manifest)
        if original['workspace']['package']['version'] != '0.0.0' or manifest.count('version = "0.0.0"') != 1:
            full_source_fail('manifest_version')
        value['Cargo.toml'] = manifest.replace('version = "0.0.0"', 'version = "'+full_source_version+'"', 1).encode()
        lock = value['Cargo.lock'].decode()
        before = full_source_toml.loads(lock)
        blocks = lock.split('[[package]]'); changed = []; local = []; external = 0
        for block in blocks[1:]:
            record = full_source_toml.loads(block)
            if 'source' not in record:
                local.append(record['name'])
                if record['version'] != '0.0.0' or block.count('version = "0.0.0"') != 1:
                    full_source_fail('lock_version')
                block = block.replace('version = "0.0.0"', 'version = "'+full_source_version+'"', 1)
            else:
                if record['source'] != 'registry+https://github.com/rust-lang/crates.io-index':
                    full_source_fail('lock_source')
                external += 1
            changed.append(block)
        if (tuple(local) != full_source_local_names or len(local) != full_source_contract['local_packages']
                or external != full_source_contract['external_packages']):
            full_source_fail('lock_set')
        new = blocks[0] + '[[package]]' + '[[package]]'.join(changed)
        after = full_source_toml.loads(new)
        for old, fresh, block, updated in zip(before['package'], after['package'], blocks[1:], changed, strict=True):
            if 'source' in old:
                if old != fresh or block != updated:
                    full_source_fail('external_changed')
            elif fresh != dict(old, version=full_source_version):
                full_source_fail('local_changed')
        value['Cargo.lock'] = new.encode(); value[full_source_child] = patched
    except (ValueError, TypeError, KeyError, UnicodeError):
        full_source_fail('transform_parse')
    for name, key in (('Cargo.toml', 'derived_manifest_sha256'), ('Cargo.lock', 'derived_lock_sha256')):
        if hashlib.sha256(value[name]).hexdigest() != full_source_contract[key]:
            full_source_fail('derived_digest')
    return value


def full_source_scan(root, entries, files, *, partial=False):
    found = set(); pending = [root]
    while pending:
        full_source_remaining(); path = pending.pop(); fd = full_source_open(path, directory=True)
        try:
            before = full_source_identity(os.fstat(fd))
            with os.scandir(fd) as children:
                for child in children:
                    full_source_remaining()
                    name = str((path/child.name).relative_to(root))
                    if name not in entries or name in found:
                        full_source_fail('retained_entries')
                    found.add(name); item = entries[name]; info = child.stat(follow_symlinks=False)
                    full_source_owned(info, path/child.name, directory=item['type']=='tree', symlink=item['mode']=='120000')
                    if item['type'] == 'tree':
                        pending.append(path/child.name)
                    elif item['mode'] == '120000':
                        if os.readlink(child.name, dir_fd=fd) != full_source_link_target:
                            full_source_fail('retained_link')
                    else:
                        mode = 0o755 if item['mode']=='100755' else 0o644
                        if info.st_mode & 0o7777 != mode or full_source_read(path/child.name, len(files[name])) != files[name]:
                            full_source_fail('retained_content')
            if before != full_source_identity(os.fstat(fd)):
                full_source_fail('directory_changed')
        except OSError:
            full_source_fail('retained_read')
        finally:
            os.close(fd)
    if not partial and found != set(entries):
        full_source_fail('retained_missing')
    return found


def full_source_inputs(payload, seconds, *, prepare):
    patched = full_source_start(payload, seconds)
    inputs = WORK/'full-source-inputs-1'
    if prepare:
        full_source_mkdir(inputs)
    fd = full_source_open(inputs, directory=True)
    try:
        with os.scandir(fd) as children:
            if any(child.name not in {'tree.json', 'source.tar.gz'} for child in children):
                full_source_fail('input_entries')
    finally:
        os.close(fd)
    contract = full_source_contract
    if prepare:
        full_source_fetch(inputs/'tree.json', contract['metadata_url'], contract['metadata_limit'])
    metadata = full_source_read(inputs/'tree.json', contract['metadata_limit'])
    entries = full_source_tree(metadata)
    if prepare:
        full_source_fetch(inputs/'source.tar.gz', contract['archive_url'], contract['compressed_limit'])
    archive = full_source_read(inputs/'source.tar.gz', contract['compressed_limit'])
    files = full_source_archive(archive, entries)
    files = full_source_transform(files, patched)
    return entries, files, {'metadata_sha256': hashlib.sha256(metadata).hexdigest(),
                           'archive_sha256': hashlib.sha256(archive).hexdigest(), 'archive_bytes': len(archive)}


def full_source_report(report):
    return dict(report, source_verified=True, changed_files=3, source=str(WORK/'full-source-1'),
                upstream_commit=full_source_commit, session_enabled=False, full_runtime_qualified=False,
                upstream_tree_sha1=full_source_tree_sha1, experimental_version=full_source_version,
                source_blobs=full_source_contract['blobs'], patched_source_sha256=full_source_child_after,
                derived_manifest_sha256=full_source_contract['derived_manifest_sha256'],
                derived_lock_sha256=full_source_contract['derived_lock_sha256'])


def full_source_prepare(payload, seconds):
    entries, files, report = full_source_inputs(payload, seconds, prepare=True)
    root = WORK/'full-source-1'
    if os.path.lexists(root):
        found = full_source_scan(root, entries, files, partial=True)
    else:
        found = set()
    full_source_mkdir(root)
    for name in sorted((n for n, v in entries.items() if v['type']=='tree'), key=lambda n: (n.count('/'), n)):
        full_source_mkdir(root/name)
    for name, raw in files.items():
        full_source_remaining()
        if name in found or name == full_source_link:
            continue
        full_source_write(root/name, raw, 0o755 if entries[name]['mode']=='100755' else 0o644)
    if full_source_link not in found:
        parent = full_source_open((root/full_source_link).parent, directory=True)
        try:
            os.symlink(full_source_link_target, 'skills', dir_fd=parent); os.fsync(parent)
        except OSError:
            full_source_fail('link_publish')
        finally:
            os.close(parent)
    full_source_scan(root, entries, files)
    return full_source_report(report)


def full_source_verify(payload, seconds):
    entries, files, report = full_source_inputs(payload, seconds, prepare=False)
    full_source_scan(WORK/'full-source-1', entries, files)
    return full_source_report(report)
