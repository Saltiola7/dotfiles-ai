"""Authenticated musl unwind prerequisite inside the capped unprivileged build.

APK hashes are measured after authentication, not invented advance pins. The
existing OpenSSL authenticates apk.static's detached SHA256 signature before any
execution. That exact verifier then checks both complete APKs offline. Nothing is
installed into the guest OS; the caller scopes the new library to Rust processes.
Sources: aports a53adea12086d36717300ea195ede9ad75f98e1f/main/apk-tools/APKBUILD;
aports fbf60319be3bbaf6dd32ef55cc6fb7189e05c266/main/alpine-keys;
apk-tools v2.14.12/src/{app_verify.c,database.c,apk.c}. Source tests are not native proof.
"""
import io as unwind_io
import zlib as unwind_zlib
import re as unwind_re

unwind_artifacts = (
    {'name': 'apk-tools-static-2.14.12-r0.apk', 'bytes': 2436399,
     'url': 'https://dl-cdn.alpinelinux.org/alpine/v3.22/main/aarch64/apk-tools-static-2.14.12-r0.apk'},
    {'name': 'libgcc-14.2.0-r6.apk', 'bytes': 67013,
     'url': 'https://dl-cdn.alpinelinux.org/alpine/v3.22/main/aarch64/libgcc-14.2.0-r6.apk'},
    {'name': 'alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub', 'bytes': 800,
     'url': 'https://raw.githubusercontent.com/alpinelinux/aports/fbf60319be3bbaf6dd32ef55cc6fb7189e05c266/main/alpine-keys/alpine-devel%40lists.alpinelinux.org-616ae350.rsa.pub',
     'sha256': 'd11f6b21c61b4274e182eb888883a8ba8acdbf820dcc7a6d82a7d9fc2fd2836d'},
)
unwind_packages = (
    {'pkgname': 'apk-tools-static', 'pkgver': '2.14.12-r0', 'arch': 'aarch64',
     'origin': 'apk-tools', 'commit': 'a53adea12086d36717300ea195ede9ad75f98e1f', 'depend': []},
    {'pkgname': 'libgcc', 'pkgver': '14.2.0-r6', 'arch': 'aarch64',
     'origin': 'gcc', 'commit': 'fbf60319be3bbaf6dd32ef55cc6fb7189e05c266',
     'depend': ['so:libc.musl-aarch64.so.1']},
)
# Upstream v2.14.12 Make.rules resets FULL_VERSION after config.mk.
# The binary omits the package revision; signed PKGINFO retains it.
unwind_version = b'apk-tools 2.14.12, compiled for aarch64.\n'
unwind_signature = 'sbin/apk.static.SIGN.RSA.sha256.alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub'
unwind_expansion_limit = 32 * 1024**2


def unwind_regular(path, size):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
            or info.st_mode & 0o022 or info.st_size != size or path.resolve() != path
            or info.st_dev != WORK.stat().st_dev):
        raise RuntimeError('unwind_file_identity')


def unwind_checked(item):
    path = WORK / 'downloads' / item['name']
    unwind_regular(path, item['bytes'])
    if 'sha256' in item and digest(path) != item['sha256']:
        raise RuntimeError('unwind_key_digest')
    return path


class unwind_NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('unwind_download_redirect')


def unwind_download():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), unwind_NoRedirect())
    for item in unwind_artifacts:
        target = WORK / 'downloads' / item['name']
        if target.exists() or target.is_symlink():
            unwind_checked(item)
            continue
        partial = target.with_name(target.name + '.partial')
        with partial.open('xb') as output:
            with opener.open(item['url'], timeout=remaining(20)) as response:
                if response.status != 200 or response.url != item['url']:
                    raise RuntimeError('unwind_download_transport')
                count = 0
                while True:
                    remaining()
                    chunk = response.read1(min(65536, item['bytes'] + 1 - count))
                    if not chunk: break
                    count += len(chunk)
                    if count > item['bytes']: raise RuntimeError('unwind_download_size')
                    output.write(chunk)
            output.flush(); os.fsync(output.fileno())
        if count != item['bytes'] or ('sha256' in item and digest(partial) != item['sha256']):
            raise RuntimeError('unwind_download_identity')
        os.link(partial, target, follow_symlinks=False)
        partial.unlink()
        unwind_checked(item)
    return {'downloaded_artifacts': 3, 'authenticated_archives': 0}


def unwind_members(path):
    with path.open('rb') as stream: compressed = stream.read(3 * 1024**2 + 1)
    if len(compressed) > 3 * 1024**2: raise RuntimeError('unwind_archive_budget')
    expanded = bytearray(); streams = 0
    while compressed:
        remaining(); streams += 1
        if streams > 3: raise RuntimeError('unwind_archive_streams')
        decoder = unwind_zlib.decompressobj(31)
        expanded.extend(decoder.decompress(compressed, unwind_expansion_limit + 1 - len(expanded)))
        if len(expanded) > unwind_expansion_limit or not decoder.eof:
            raise RuntimeError('unwind_archive_budget')
        compressed = decoder.unused_data
    selected = {}; names = set()
    limits = {'sbin/apk.static': 16 * 1024**2, unwind_signature: 512,
              '.PKGINFO': 16384, 'usr/lib/libgcc_s.so.1': 1024**2}
    with tarfile.open(fileobj=unwind_io.BytesIO(expanded), mode='r:', ignore_zeros=True) as tar:
        for member in tar:
            remaining(); name = PurePosixPath(member.name)
            if (len(names) >= 128 or len(member.name) > 512 or name.is_absolute() or '..' in name.parts
                    or member.name in names or not (member.isfile() or member.isdir())):
                raise RuntimeError('unwind_archive_path')
            names.add(member.name)
            if member.name in limits:
                if not member.isfile() or not 0 < member.size <= limits[member.name]:
                    raise RuntimeError('unwind_archive_member')
                selected[member.name] = tar.extractfile(member).read(limits[member.name] + 1)
                if len(selected[member.name]) != member.size: raise RuntimeError('unwind_archive_member')
    return selected


def unwind_metadata(raw, expected):
    fields = {}
    for line in raw.decode('utf-8').splitlines():
        if not line or line.startswith('#'): continue
        if ' = ' not in line: raise RuntimeError('unwind_metadata')
        key, value = line.split(' = ', 1)
        fields.setdefault(key, []).append(value)
    for key, value in expected.items():
        if fields.get(key, []) != (value if key == 'depend' else [value]):
            raise RuntimeError('unwind_metadata')
    if len(fields.get('datahash', [])) != 1 or unwind_re.fullmatch('[0-9a-f]{64}', fields['datahash'][0]) is None:
        raise RuntimeError('unwind_metadata')


def unwind_library(raw):
    if len(raw) < 64 or raw[:7] != b'\x7fELF\x02\x01\x01': raise RuntimeError('unwind_elf')
    kind, machine, version, _, offset, _, _, size, phsize, count, _, _, _ = struct.unpack_from('<HHIQQQIHHHHHH', raw, 16)
    if (kind != 3 or machine != 183 or version != 1 or size != 64 or phsize != 56
            or not 0 < count <= 128 or offset < 64 or offset + count * 56 > len(raw)):
        raise RuntimeError('unwind_elf')
    loads = []; dynamic = []
    for index in range(count):
        tag, _, start, virtual, _, length, _, _ = struct.unpack_from('<IIQQQQQQ', raw, offset + index * 56)
        if start + length > len(raw) or tag == 3: raise RuntimeError('unwind_elf')
        if tag == 1: loads.append((start, virtual, length))
        if tag == 2: dynamic.append((start, length))
    if len(dynamic) != 1 or not 0 < dynamic[0][1] <= 65536 or dynamic[0][1] % 16:
        raise RuntimeError('unwind_elf')
    tags = {}
    for pos in range(dynamic[0][0], sum(dynamic[0]), 16):
        key, value = struct.unpack_from('<qQ', raw, pos)
        if key == 0: break
        if key in (15, 29): raise RuntimeError('unwind_elf')
        tags.setdefault(key, []).append(value)
    else: raise RuntimeError('unwind_elf')
    if any(len(tags.get(key, [])) != 1 for key in (5, 10, 1, 14)):
        raise RuntimeError('unwind_elf')
    address, length = tags[5][0], tags[10][0]
    matches = [start + address - virtual for start, virtual, size in loads
               if virtual <= address and address + length <= virtual + size]
    if len(matches) != 1 or not 0 < length <= 65536: raise RuntimeError('unwind_elf')
    strings = raw[matches[0]:matches[0] + length]
    for key, expected in ((1, b'libc.musl-aarch64.so.1'), (14, b'libgcc_s.so.1')):
        at = tags[key][0]
        if at >= len(strings) or b'\0' not in strings[at:] or strings[at:].split(b'\0', 1)[0] != expected:
            raise RuntimeError('unwind_elf')


def unwind_dir(path, allowed):
    if not path.exists(): path.mkdir(mode=0o700)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700
            or path.resolve() != path or info.st_dev != WORK.stat().st_dev):
        raise RuntimeError('unwind_directory')
    with os.scandir(path) as entries:
        for count, entry in enumerate(entries, 1):
            if count > len(allowed) or entry.name not in allowed: raise RuntimeError('unwind_retained_state')


def unwind_save(path, raw, mode):
    if not path.exists() and not path.is_symlink():
        with path.open('xb') as stream: stream.write(raw)
        path.chmod(mode)
    unwind_regular(path, len(raw))
    if stat.S_IMODE(path.lstat().st_mode) != mode or path.read_bytes() != raw:
        raise RuntimeError('unwind_retained_state')


def unwind_openssl():
    info = Path('/usr/bin/openssl').lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid or info.st_gid or info.st_mode & 0o022:
        raise RuntimeError('unwind_openssl_identity')


def unwind_verify():
    """Authenticate retained support without changing an installed prefix."""
    paths = [unwind_checked(item) for item in unwind_artifacts]
    hashes = [digest(path) for path in paths]
    parts = unwind_members(paths[0])
    executable, signature = parts['sbin/apk.static'], parts[unwind_signature]
    if len(signature) != 512: raise RuntimeError('unwind_signature')
    cache = WORK / 'unwind-bootstrap-1'; root = cache / 'root'; keys = root / 'keys'
    unwind_dir(cache, {'apk.static', 'signature', 'root'})
    unwind_dir(root, {'keys'}); unwind_dir(keys, {unwind_artifacts[2]['name']})
    binary = cache / 'apk.static'; key = keys / unwind_artifacts[2]['name']; sig = cache / 'signature'
    unwind_save(binary, executable, 0o500); unwind_save(sig, signature, 0o400)
    unwind_save(key, paths[2].read_bytes(), 0o400)
    verify_static_arm64(binary); unwind_openssl()
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': str(WORK / 'home'), 'TMPDIR': str(WORK / 'tmp')}
    result, error = command(['/usr/bin/openssl', 'dgst', '-sha256', '-verify', str(key), '-signature', str(sig), str(binary)],
                            environment=env, maximum=30)
    if result != b'Verified OK\n' or error: raise RuntimeError('unwind_signature')
    result, error = command([str(binary), '--version'], environment=env, maximum=10)
    if result != unwind_version or error:
        print(json.dumps({'unwind_version_stdout': result[:512].decode(errors='replace'),
                          'unwind_version_stderr': error[:512].decode(errors='replace')}), flush=True)
        raise RuntimeError('unwind_verifier_version')
    command([str(binary), '--root', str(root), '--keys-dir', 'keys', '--repositories-file', '/dev/null',
             '--no-network', '--no-cache', 'verify', str(paths[0]), str(paths[1])], environment=env, maximum=60)
    library = unwind_members(paths[1])
    unwind_metadata(parts['.PKGINFO'], unwind_packages[0]); unwind_metadata(library['.PKGINFO'], unwind_packages[1])
    raw = library['usr/lib/libgcc_s.so.1']; unwind_library(raw)
    if [digest(path) for path in paths] != hashes: raise RuntimeError('unwind_artifact_changed')
    remaining()
    return {'authenticated_archives': 2, 'library_sha256': hashlib.sha256(raw).hexdigest(),
            'library_bytes': len(raw), 'library': str(WORK / 'toolchain-unwind-1/lib/libgcc_s.so.1'),
            'archive_sha256': dict(zip((item['name'] for item in unwind_artifacts), hashes)),
            'verifier_sha256': hashlib.sha256(executable).hexdigest()}, raw


def unwind_install(prefix):
    if prefix != WORK / 'toolchain-unwind-1' or prefix.exists() or prefix.is_symlink():
        raise RuntimeError('unwind_prefix')
    report, raw = unwind_verify()
    prefix.mkdir(mode=0o700); (prefix / 'lib').mkdir(mode=0o700)
    unwind_save(prefix / 'lib/libgcc_s.so.1', raw, 0o444)
    return report
