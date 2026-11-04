"""Pinned private agent packages; authentication and inspection never execute them.

Appended to the capped guest harness. Only the two source-defined artifacts and
fixed private roots are admitted. Partial downloads/extractions remain on failure.
"""
import contextlib as agent_assets_contextlib
import urllib.parse as agent_assets_parse
import zlib as agent_assets_zlib


agent_assets_contract = {
    'schema_version': 1, 'generation': 1,
    'assets': {
        'codex': {'version': '0.164.0',
            'url': 'https://github.com/openai/codex/releases/download/rust-v0.164.0/codex-package-aarch64-unknown-linux-musl.tar.gz',
            'archive': 'codex-package-aarch64-unknown-linux-musl.tar.gz', 'bytes': 152400557,
            'sha256': '5918add6c7e9cf1e14a9af1b4c0f4bf1d24a43903faac26df5dc4c019ea91bd5', 'expanded_limit': 1073741824},
        'opencode': {'version': '1.18.25',
            'url': 'https://github.com/anomalyco/opencode/releases/download/v1.18.25/opencode-linux-arm64.tar.gz',
            'archive': 'opencode-linux-arm64.tar.gz', 'bytes': 60345335,
            'sha256': '35ef77897425e41b5183a2c21ac4fb1d4d944d82a94e3c920f57b5490af11ac5', 'expanded_limit': 536870912},
    },
}
agent_assets_codex_metadata = {'layoutVersion': 1, 'version': '0.164.0',
    'target': 'aarch64-unknown-linux-musl', 'variant': 'codex', 'entrypoint': 'bin/codex',
    'resourcesDir': 'codex-resources', 'pathDir': 'codex-path'}
agent_assets_files = {
    'codex': {'codex-package.json': 0o400, 'bin/codex': 0o500, 'bin/codex-code-mode-host': 0o500,
              'codex-resources/bwrap': 0o500, 'codex-path/rg': 0o500},
    'opencode': {'opencode': 0o500},
}
agent_assets_directories = {'codex': {'bin', 'codex-resources', 'codex-path'}, 'opencode': set()}
agent_assets_voice_sha256 = '478394bae952fff452aa79788abe07f3b2a44b1439c88b91da2919250cde7780'


def agent_assets_fail(reason):
    raise RuntimeError('agent_assets_'+reason)


def agent_assets_selection(payload):
    remaining()
    try:
        value = payload['agent_manifest']
        if (type(value) is not dict or type(value.get('schema_version')) is not int
                or type(value.get('generation')) is not int or value != agent_assets_contract
                or any(type(item.get(field)) is not int for item in value['assets'].values()
                       for field in ('bytes', 'expanded_limit'))):
            agent_assets_fail('selection')
    except (KeyError, TypeError, AttributeError):
        agent_assets_fail('selection')
    agent_assets_voice_selection(payload, value)
    return value


def agent_assets_voice_selection(payload, selected):
    try:
        value = payload['voice_omissions']
        if (type(value) is not dict or set(value) != {'schema_version', 'archive_sha256', 'entries'}
                or type(value['schema_version']) is not int or value['schema_version'] != 1
                or value['archive_sha256'] != selected['assets']['codex']['sha256']
                or type(value['entries']) is not dict or len(value['entries']) != 43):
            agent_assets_fail('voice_selection')
        for path, item in value['entries'].items():
            if (type(path) is not str or len(path) > 200 or type(item) is not dict
                    or set(item) != {'kind', 'bytes', 'mode'} or item['kind'] not in ('file', 'directory')
                    or type(item['bytes']) is not int or not 0 <= item['bytes'] <= selected['assets']['codex']['expanded_limit']
                    or type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777):
                agent_assets_fail('voice_selection')
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        if hashlib.sha256(raw).hexdigest() != agent_assets_voice_sha256:
            agent_assets_fail('voice_selection')
    except (KeyError, TypeError, ValueError, UnicodeError):
        agent_assets_fail('voice_selection')
    return value['entries']


def agent_assets_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def agent_assets_owned(info, *, directory=False, mode=None):
    if (not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or info.st_dev != WORK.lstat().st_dev or info.st_uid != os.getuid() or info.st_gid != os.getgid()
            or info.st_mode & 0o7022 or (not directory and info.st_nlink != 1)
            or (mode is not None and stat.S_IMODE(info.st_mode) != mode)):
        agent_assets_fail('file_identity')


def agent_assets_open(path, *, directory=False, mode=None):
    remaining(); fd = None
    try:
        parts = path.relative_to(WORK).parts
        if WORK.resolve() != WORK or any(part in ('', '.', '..') for part in parts):
            agent_assets_fail('path')
        fd = os.open(WORK, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        agent_assets_owned(os.fstat(fd), directory=True, mode=0o700)
        for index, part in enumerate(parts):
            remaining(); isdir = index < len(parts)-1 or directory
            child = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
                            | (os.O_DIRECTORY if isdir else 0), dir_fd=fd)
            os.close(fd); fd = child
            agent_assets_owned(os.fstat(fd), directory=isdir, mode=0o700 if isdir else mode)
        if agent_assets_identity(os.fstat(fd)) != agent_assets_identity(path.lstat()):
            agent_assets_fail('path_changed')
        result = fd; fd = None
        return result
    except (OSError, ValueError):
        agent_assets_fail('open')
    finally:
        if fd is not None: os.close(fd)


@agent_assets_contextlib.contextmanager
def agent_assets_hold(path, *, directory=False, mode=None):
    fd = agent_assets_open(path, directory=directory, mode=mode)
    try:
        before = agent_assets_identity(os.fstat(fd))
        yield fd
        remaining()
        if before != agent_assets_identity(os.fstat(fd)) or before != agent_assets_identity(path.lstat()):
            agent_assets_fail('file_changed')
    except OSError:
        agent_assets_fail('file_io')
    finally:
        os.close(fd)


def agent_assets_hash(fd, size):
    if os.fstat(fd).st_size != size: agent_assets_fail('length')
    value = hashlib.sha256(); offset = 0
    while offset < size:
        remaining(); block = os.pread(fd, min(65536, size-offset), offset)
        if not block: agent_assets_fail('short_read')
        value.update(block); offset += len(block)
    remaining()
    return value.hexdigest()


def agent_assets_mkdir(path):
    parent = agent_assets_open(path.parent, directory=True)
    try:
        remaining(); os.mkdir(path.name, 0o700, dir_fd=parent); os.fsync(parent)
    except OSError:
        agent_assets_fail('directory_publish')
    finally:
        os.close(parent)


def agent_assets_inputs(*, create=False):
    path = WORK/'agent-assets-inputs-1'
    if create and not os.path.lexists(path): agent_assets_mkdir(path)
    allowed = {item['archive'] for item in agent_assets_contract['assets'].values()}
    with agent_assets_hold(path, directory=True) as fd:
        with os.scandir(fd) as entries:
            for count, entry in enumerate(entries):
                remaining()
                if count >= 2 or entry.name not in allowed: agent_assets_fail('input_entries')
                agent_assets_owned(entry.stat(follow_symlinks=False), mode=0o600)
    return path


def agent_assets_url(url):
    try:
        parsed = agent_assets_parse.urlsplit(url)
        return (type(url) is str and len(url) <= 8192 and parsed.scheme == 'https'
                and parsed.hostname == 'release-assets.githubusercontent.com' and parsed.port in (None, 443)
                and parsed.username is None and parsed.password is None and not parsed.fragment
                and parsed.path.startswith('/'))
    except (ValueError, TypeError):
        return False


class agent_assets_Redirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, original):
        super().__init__(); self.current = original; self.count = 0

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        remaining()
        if (request.full_url != self.current or request.get_method() != 'GET' or self.count >= 2
                or code not in (301, 302, 303, 307, 308) or not agent_assets_url(newurl)):
            agent_assets_fail('redirect')
        self.count += 1; self.current = newurl
        return urllib.request.Request(newurl, headers={'User-Agent': 'dotfiles-ai-openshell-agent-assets'})


def agent_assets_download_one(inputs, item):
    target = inputs/item['archive']
    if os.path.lexists(target):
        with agent_assets_hold(target, mode=0o600) as fd:
            if agent_assets_hash(fd, item['bytes']) != item['sha256']: agent_assets_fail('retained_digest')
        return
    parent = agent_assets_open(inputs, directory=True); fd = None
    partial = target.name+'.partial'
    try:
        remaining()
        fd = os.open(partial, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), agent_assets_Redirect(item['url']))
        request = urllib.request.Request(item['url'], headers={'User-Agent': 'dotfiles-ai-openshell-agent-assets'})
        value = hashlib.sha256(); count = 0
        with opener.open(request, timeout=remaining(20)) as response:
            if response.status != 200 or (response.url != item['url'] and not agent_assets_url(response.url)):
                agent_assets_fail('transport')
            while True:
                remaining(); chunk = response.read1(min(65536, item['bytes']+1-count))
                if not chunk: break
                count += len(chunk)
                if count > item['bytes']: agent_assets_fail('download_size')
                value.update(chunk); offset = 0
                while offset < len(chunk):
                    remaining(); written = os.write(fd, chunk[offset:])
                    if written <= 0: agent_assets_fail('write')
                    offset += written
        if count != item['bytes'] or value.hexdigest() != item['sha256']: agent_assets_fail('download_digest')
        os.fsync(fd)
        if (agent_assets_hash(fd, item['bytes']) != item['sha256']
                or agent_assets_identity(os.fstat(fd)) != agent_assets_identity(os.stat(partial, dir_fd=parent, follow_symlinks=False))):
            agent_assets_fail('download_changed')
        remaining(); os.link(partial, target.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.unlink(partial, dir_fd=parent); os.fsync(parent)
        agent_assets_owned(os.fstat(fd), mode=0o600)
        if agent_assets_identity(os.fstat(fd)) != agent_assets_identity(target.lstat()):
            agent_assets_fail('download_changed')
    except OSError:
        agent_assets_fail('download_io')
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


class agent_assets_Gzip:
    """One gzip member, bounded actual expansion and constant streaming buffer."""
    def __init__(self, fd, limit):
        os.lseek(fd, 0, os.SEEK_SET)
        self.fd = fd; self.limit = limit; self.count = 0
        self.decoder = agent_assets_zlib.decompressobj(31); self.pending = b''; self.done = False

    def read(self, size):
        if size < 0: agent_assets_fail('unbounded_read')
        size = min(size, 65536)
        if self.done or size == 0: return b''
        result = bytearray()
        while len(result) < size and not self.done:
            remaining()
            if not self.pending:
                self.pending = os.read(self.fd, 65536)
                if not self.pending: agent_assets_fail('gzip_truncated')
            block = self.decoder.decompress(self.pending, size-len(result))
            self.pending = self.decoder.unconsumed_tail
            self.count += len(block)
            if self.count > self.limit: agent_assets_fail('expanded_limit')
            result.extend(block)
            if self.decoder.eof:
                if self.decoder.unused_data or self.pending or os.read(self.fd, 1): agent_assets_fail('gzip_trailing')
                self.done = True
        return bytes(result)


def agent_assets_json(raw):
    if not 0 < len(raw) <= 8192: agent_assets_fail('metadata_size')
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: agent_assets_fail('metadata_duplicate')
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        if (type(value) is not dict or type(value.get('layoutVersion')) is not int
                or value != agent_assets_codex_metadata): agent_assets_fail('metadata')
    except (ValueError, UnicodeError):
        agent_assets_fail('metadata')
    return value


def agent_assets_elf(raw):
    if len(raw) < 64 or raw[:7] != b'\x7fELF\x02\x01\x01': agent_assets_fail('elf')
    values = struct.unpack_from('<HHIQQQIHHHHHH', raw, 16)
    kind, machine, version, _, phoff, _, _, ehsize, phsize, phnum, _, _, _ = values
    if (kind not in (2, 3) or machine != 183 or version != 1 or ehsize != 64 or phsize != 56
            or not 0 < phnum <= 128 or phoff < 64 or phoff+phnum*56 > len(raw)):
        agent_assets_fail('elf_header')
    loads = []; dynamic = None; interpreter = None
    for number in range(phnum):
        remaining(); tag, _, offset, address, _, length, memory, _ = struct.unpack_from('<IIQQQQQQ', raw, phoff+number*56)
        if offset+length > len(raw) or (tag == 1 and length > memory): agent_assets_fail('elf_segment')
        if tag == 1: loads.append((offset, address, length))
        elif tag == 2:
            if dynamic is not None or not 0 < length <= 1024**2 or length % 16: agent_assets_fail('elf_dynamic')
            dynamic = (offset, length)
        elif tag == 3:
            if interpreter is not None or not 1 < length <= 4096: agent_assets_fail('elf_interpreter')
            value = raw[offset:offset+length]
            if value[-1:] != b'\0' or b'\0' in value[:-1]: agent_assets_fail('elf_interpreter')
            try: interpreter = value[:-1].decode('ascii')
            except UnicodeError: agent_assets_fail('elf_interpreter')
            if interpreter not in ('/lib/ld-linux-aarch64.so.1', '/lib/ld-musl-aarch64.so.1'):
                agent_assets_fail('elf_interpreter')
    if not loads: agent_assets_fail('elf_load')
    needed = []; fields = {}
    if dynamic is not None:
        offset, length = dynamic
        for cursor in range(offset, offset+length, 16):
            remaining(); tag, value = struct.unpack_from('<qQ', raw, cursor)
            if tag == 0: break
            if tag == 1:
                needed.append(value)
                if len(needed) > 64: agent_assets_fail('elf_needed')
            elif tag in (5, 10):
                if tag in fields: agent_assets_fail('elf_strings')
                fields[tag] = value
            elif tag in (15, 29, 0x6ffffefb, 0x6ffffefc, 0x7fffffff, 0x7ffffffd):
                agent_assets_fail('elf_search_path')
        else: agent_assets_fail('elf_dynamic_ending')
    names = []
    if needed:
        if set(fields) != {5, 10} or not 0 < fields[10] <= len(raw): agent_assets_fail('elf_strings')
        matches = [(offset+fields[5]-address, length-(fields[5]-address)) for offset,address,length in loads
                   if address <= fields[5] and fields[5]+fields[10] <= address+length]
        if len(matches) != 1: agent_assets_fail('elf_strings')
        start, _ = matches[0]
        for offset in needed:
            if offset >= fields[10]: agent_assets_fail('elf_needed')
            value = raw[start+offset:start+min(fields[10], offset+256)]
            value, marker, _ = value.partition(b'\0')
            if not marker or not value or any(byte not in b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.+-' for byte in value):
                agent_assets_fail('elf_needed')
            name = value.decode('ascii')
            if name in names or name in ('.', '..'): agent_assets_fail('elf_needed')
            names.append(name)
    return {'machine': machine, 'kind': kind, 'interpreter': interpreter, 'needed': names}


def agent_assets_header_inventory(fd, item):
    """Diagnostic metadata only; no member extraction or admission fallback."""
    result = {'status': 'complete', 'entries': []}
    try:
        stream = agent_assets_Gzip(fd, item['expanded_limit'])
        with tarfile.open(fileobj=stream, mode='r|') as archive:
            for index, member in enumerate(archive):
                remaining()
                if index >= 160:
                    result.update(status='limited', error='entry_limit'); break
                row = {'index': index, 'name_repr': repr(member.name)[:160],
                       'type_repr': repr(member.type)[:32], 'mode': oct(member.mode)[:32], 'bytes': member.size}
                candidate = dict(result, entries=result['entries']+[row])
                if len(json.dumps(candidate, sort_keys=True, separators=(',', ':')).encode()) > 20*1024:
                    result.update(status='limited', error='byte_limit'); break
                result['entries'].append(row)
            else:
                while True:
                    remaining(); tail = archive.fileobj.read(65536)
                    if not tail: break
                    if any(tail): agent_assets_fail('tar_trailing')
                if not stream.done: agent_assets_fail('gzip_truncated')
    except RuntimeError as error:
        category = 'deadline' if str(error) == 'harness_deadline' else (
            'expansion_limit' if str(error) == 'agent_assets_expanded_limit' else 'scan_refused')
        result.update(status='incomplete', error=category)
    except OSError:
        result.update(status='incomplete', error='io')
    except (ValueError, tarfile.TarError, agent_assets_zlib.error, EOFError):
        result.update(status='incomplete', error='archive')
    return result


def agent_assets_scan(fd, name, item, *, omissions=None, write=None, expected=None):
    if omissions is None:
        if name == 'codex': agent_assets_fail('voice_selection')
        omissions = {}
    stream = agent_assets_Gzip(fd, item['expanded_limit']); seen = set(); files = {}; total = omitted_total = 0
    omitted = {}; required = set(agent_assets_files[name]) | agent_assets_directories[name] | set(omissions)
    try:
        with tarfile.open(fileobj=stream, mode='r|') as archive:
            for count, member in enumerate(archive):
                remaining(); path = member.name
                if count >= 10000 or path in seen or path not in required or member.mode & 0o7000:
                    detail = {'asset': name, 'index': count, 'name_repr': repr(path)[:160],
                              'type_repr': repr(member.type)[:32], 'mode': oct(member.mode)[:32],
                              'duplicate': path in seen, 'unknown': path not in required}
                    detail['inventory'] = agent_assets_header_inventory(fd, item)
                    agent_assets_fail('archive_member:'+json.dumps(detail, sort_keys=True, separators=(',', ':')))
                seen.add(path)
                if path in omissions:
                    chosen = omissions[path]
                    if member.mode != chosen['mode'] or member.size != chosen['bytes']:
                        agent_assets_fail('voice_header')
                    digest = None
                    if chosen['kind'] == 'directory':
                        if not member.isdir() or member.size: agent_assets_fail('voice_directory')
                    else:
                        if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or member.sparse is not None:
                            agent_assets_fail('voice_file')
                        omitted_total += member.size
                        if total+omitted_total > item['expanded_limit']: agent_assets_fail('expanded_limit')
                        hashed = hashlib.sha256(); left = member.size
                        with archive.extractfile(member) as source:
                            while left:
                                remaining(); block = source.read(min(65536, left))
                                if not block or len(block) > left: agent_assets_fail('archive_short')
                                hashed.update(block); left -= len(block)
                        digest = hashed.hexdigest()
                    omitted[path] = dict(chosen, sha256=digest)
                    if expected is not None and omitted[path] != expected['omitted_entries'][path]:
                        agent_assets_fail('archive_changed')
                    continue
                if path in agent_assets_directories[name]:
                    if not member.isdir() or member.size: agent_assets_fail('archive_directory')
                    continue
                mode = agent_assets_files[name][path]
                if (member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or member.sparse is not None
                        or not 0 < member.size <= item['expanded_limit']
                        or bool(member.mode & 0o111) != (mode == 0o500)):
                    agent_assets_fail('archive_file')
                if path == 'codex-package.json' and member.size > 8192: agent_assets_fail('metadata_size')
                total += member.size
                if total+omitted_total > item['expanded_limit']: agent_assets_fail('expanded_limit')
                with archive.extractfile(member) as source:
                    raw = source.read(member.size+1)
                remaining()
                if len(raw) != member.size: agent_assets_fail('archive_short')
                record = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': mode,
                          'elf': agent_assets_elf(raw) if mode == 0o500 else None}
                if mode == 0o400: agent_assets_json(raw)
                if expected is not None and record != expected['files'][path]: agent_assets_fail('archive_changed')
                files[path] = record
                if write is not None: write(path, raw, mode)
                del raw
            # Tar's first zero header is not permission to ignore hidden data.
            while True:
                remaining(); tail = archive.fileobj.read(65536)
                if not tail: break
                if any(tail): agent_assets_fail('tar_trailing')
        if seen != required or not stream.done: agent_assets_fail('archive_missing')
    except (OSError, ValueError, tarfile.TarError, agent_assets_zlib.error, EOFError):
        agent_assets_fail('archive_parse')
    return {'version': item['version'], 'archive_bytes': item['bytes'], 'archive_sha256': item['sha256'],
            'expanded_bytes': total, 'files': files,
            'package_scope': 'probe_subset_without_voice' if name == 'codex' else 'complete',
            'omitted_entries': omitted}


def agent_assets_write(path, raw, mode):
    parent = agent_assets_open(path.parent, directory=True); fd = None
    try:
        remaining(); fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode, dir_fd=parent)
        offset = 0
        while offset < len(raw):
            remaining(); written = os.write(fd, raw[offset:offset+65536])
            if written <= 0: agent_assets_fail('write')
            offset += written
        os.fchmod(fd, mode); os.fsync(fd); os.fsync(parent)
        agent_assets_owned(os.fstat(fd), mode=mode)
        if agent_assets_identity(os.fstat(fd)) != agent_assets_identity(path.lstat()): agent_assets_fail('write_changed')
    except OSError:
        agent_assets_fail('write_io')
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def agent_assets_tree(report):
    root = WORK/'agent-assets-1'; directories = {root, root/'codex', root/'opencode'}; files = {}
    for name, item in report['assets'].items():
        directories.update(root/name/part for part in agent_assets_directories[name])
        files.update({root/name/path: record for path, record in item['files'].items()})
    found = {root}; pending = [root]
    while pending:
        remaining(); path = pending.pop()
        with agent_assets_hold(path, directory=True) as fd:
            with os.scandir(fd) as entries:
                for count, entry in enumerate(entries):
                    remaining(); selected = path/entry.name
                    if count >= 10000 or selected in found: agent_assets_fail('retained_entries')
                    found.add(selected)
                    if selected in directories:
                        agent_assets_owned(entry.stat(follow_symlinks=False), directory=True, mode=0o700)
                        pending.append(selected)
                    elif selected in files:
                        expected = files[selected]
                        with agent_assets_hold(selected, mode=expected['mode']) as member:
                            if agent_assets_hash(member, expected['bytes']) != expected['sha256']:
                                agent_assets_fail('retained_content')
                    else: agent_assets_fail('retained_entries')
    if found != directories | set(files): agent_assets_fail('retained_missing')


def agent_assets_flags(status):
    return {'schema_version': 1, 'generation': 1, 'status': status, 'session_enabled': False,
            'full_runtime_qualified': False, 'compatibility_qualified': False}


def agent_assets_download(payload):
    selected = agent_assets_selection(payload); inputs = agent_assets_inputs(create=True)
    for name in ('codex', 'opencode'): agent_assets_download_one(inputs, selected['assets'][name])
    agent_assets_inputs()
    for item in selected['assets'].values():
        with agent_assets_hold(inputs/item['archive'], mode=0o600) as fd:
            if agent_assets_hash(fd, item['bytes']) != item['sha256']: agent_assets_fail('download_changed')
    remaining()
    return agent_assets_flags('agent_assets_downloaded') | {'archives': {
        name: {'bytes': item['bytes'], 'sha256': item['sha256']} for name, item in selected['assets'].items()}}


def agent_assets_admit(payload, *, prepare):
    selected = agent_assets_selection(payload); inputs = agent_assets_inputs(); observed = {}; descriptors = {}; identities = {}
    with agent_assets_contextlib.ExitStack() as owned:
        for name in ('codex', 'opencode'):
            item = selected['assets'][name]
            fd = owned.enter_context(agent_assets_hold(inputs/item['archive'], mode=0o600))
            descriptors[name] = fd
            identities[name] = agent_assets_identity(os.fstat(fd))
            if agent_assets_hash(fd, item['bytes']) != item['sha256']: agent_assets_fail('digest')
            observed[name] = agent_assets_scan(fd, name, item,
                omissions=payload['voice_omissions']['entries'] if name == 'codex' else {})
        report = agent_assets_flags('agent_assets_verified') | {
            'prefixes': {name: str(WORK/'agent-assets-1'/name) for name in observed},
            'assets': observed, 'codex_metadata': dict(agent_assets_codex_metadata)}
        root = WORK/'agent-assets-1'
        for name, fd in descriptors.items():
            remaining(); path = inputs/selected['assets'][name]['archive']
            if (identities[name] != agent_assets_identity(os.fstat(fd))
                    or identities[name] != agent_assets_identity(path.lstat())):
                agent_assets_fail('archive_changed')
        if prepare and not os.path.lexists(root):
            agent_assets_mkdir(root)
            for name in ('codex', 'opencode'):
                prefix = root/name; agent_assets_mkdir(prefix)
                for path in sorted(agent_assets_directories[name]): agent_assets_mkdir(prefix/path)
                agent_assets_scan(descriptors[name], name, selected['assets'][name],
                                  write=lambda path, raw, mode: agent_assets_write(prefix/path, raw, mode),
                                  omissions=payload['voice_omissions']['entries'] if name == 'codex' else {},
                                  expected=observed[name])
        agent_assets_tree(report)
    remaining()
    return report


def agent_assets_prepare(payload):
    return agent_assets_admit(payload, prepare=True)


def agent_assets_verify(payload):
    return agent_assets_admit(payload, prepare=False)
