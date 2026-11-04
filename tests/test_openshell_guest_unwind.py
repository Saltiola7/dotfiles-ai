"""Offline trust-order and bounded parsing checks; no native APK execution."""
import ast
import gzip
import hashlib
import io
from pathlib import Path
import struct
import sys
import tarfile
import time
from types import ModuleType

import pytest


@pytest.fixture
def unwind():
    base = Path(__file__).parent / 'fixtures/openshell_runtime'
    path = base / 'guest_unwind.py'
    assert path.is_file(), 'Fixed unwind helper not implemented'
    module = ModuleType('guest_unwind_test')
    sys.modules[module.__name__] = module
    exec(compile((base / 'guest_harness.py').read_text() + '\n' + path.read_text(), str(path), 'exec'), module.__dict__)
    module.unwind_source = path.read_text()
    return module


def test_fixed_artifacts_and_no_fabricated_apk_hash(unwind):
    assert [(p['name'], p['bytes']) for p in unwind.unwind_artifacts] == [
        ('apk-tools-static-2.14.12-r0.apk', 2436399), ('libgcc-14.2.0-r6.apk', 67013),
        ('alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub', 800)]
    assert all('sha256' not in p for p in unwind.unwind_artifacts[:2])
    assert unwind.unwind_artifacts[2]['sha256'] == 'd11f6b21c61b4274e182eb888883a8ba8acdbf820dcc7a6d82a7d9fc2fd2836d'
    assert unwind.unwind_version == b'apk-tools 2.14.12-r0, compiled for aarch64.\n'
    assert 'RSA.sha256.' in unwind.unwind_signature


def test_appended_helper_has_no_entrypoint_and_stays_small(unwind):
    tree = ast.parse(unwind.unwind_source)
    assert len(unwind.unwind_source.encode()) <= 16 * 1024
    assert not any(isinstance(n, ast.ImportFrom) and n.module == '__future__' for n in tree.body)
    assert not any(isinstance(n, (ast.If, ast.For, ast.While)) for n in tree.body)
    assert not any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) for n in tree.body)
    assert all(n.name.startswith('unwind_') for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)))


def tar_bytes(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as tar:
        for name, data, kind in entries:
            member = tarfile.TarInfo(name)
            if kind == 'file':
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
            else:
                member.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.FIFOTYPE
                member.linkname = data.decode()
                tar.addfile(member)
    return stream.getvalue()


@pytest.mark.parametrize('kind', ['traversal', 'absolute', 'symlink', 'fifo', 'duplicate', 'expansion'])
def test_apk_parser_refuses_paths_links_duplicates_and_expansion(unwind, tmp_path, monkeypatch, kind):
    entries = [('.PKGINFO', b'pkgname = libgcc\n', 'file')]
    if kind == 'traversal': entries.append(('../escape', b'x', 'file'))
    elif kind == 'absolute': entries.append(('/escape', b'x', 'file'))
    elif kind in {'symlink', 'fifo'}: entries.append(('usr/lib/libgcc_s.so.1', b'/elsewhere', kind))
    elif kind == 'duplicate': entries += entries
    path = tmp_path / 'package.apk'
    path.write_bytes(gzip.compress(tar_bytes(entries)))
    monkeypatch.setattr(unwind, 'remaining', lambda *a: 10)
    if kind == 'expansion': monkeypatch.setattr(unwind, 'unwind_expansion_limit', 128)
    with pytest.raises(RuntimeError, match='unwind_'):
        unwind.unwind_members(path)
    assert not (tmp_path / 'escape').exists()


def test_apk_parser_handles_concatenated_gzip_streams(unwind, tmp_path, monkeypatch):
    path = tmp_path / 'package.apk'
    path.write_bytes(gzip.compress(tar_bytes([('.SIGN.RSA.key', b'signature', 'file')])) +
                     gzip.compress(tar_bytes([('.PKGINFO', b'metadata', 'file')])) +
                     gzip.compress(tar_bytes([('usr/lib/libgcc_s.so.1', b'library', 'file')])))
    monkeypatch.setattr(unwind, 'remaining', lambda *a: 10)
    values = unwind.unwind_members(path)
    assert values['.PKGINFO'] == b'metadata'
    assert values['usr/lib/libgcc_s.so.1'] == b'library'


def pkginfo(package):
    value = {**package, 'datahash': 'a' * 64}
    deps = value.pop('depend')
    return (''.join(f'{k} = {v}\n' for k, v in value.items()) +
            ''.join(f'depend = {value}\n' for value in deps)).encode()


@pytest.mark.parametrize('kind', ['version', 'arch', 'origin', 'commit', 'duplicate', 'dependency', 'datahash'])
def test_signed_package_metadata_requires_exact_identity(unwind, kind):
    expected = unwind.unwind_packages[1]
    raw = pkginfo(expected)
    unwind.unwind_metadata(raw, expected)
    if kind in {'version', 'arch', 'origin', 'commit'}:
        field = 'pkgver' if kind == 'version' else kind
        raw = raw.replace(f'{field} = {expected[field]}'.encode(), f'{field} = changed'.encode())
    elif kind == 'duplicate': raw += b'pkgname = libgcc\n'
    elif kind == 'dependency': raw += b'depend = foreign-runtime\n'
    else: raw = raw.replace(b'a' * 64, b'bad')
    with pytest.raises(RuntimeError, match='unwind_metadata'):
        unwind.unwind_metadata(raw, expected)


def library_elf(needed=b'libc.musl-aarch64.so.1', machine=183, rpath=False):
    strings = b'\0' + needed + b'\0libgcc_s.so.1\0'
    tags = [(5, 512), (10, len(strings)), (1, 1), (14, len(needed) + 2)]
    if rpath: tags.append((29, 1))
    tags.append((0, 0))
    data = bytearray(512 + len(strings))
    data[:16] = b'\x7fELF\x02\x01\x01' + b'\0' * 9
    struct.pack_into('<HHIQQQIHHHHHH', data, 16, 3, machine, 1, 0, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, 0, 0, 0, len(data), len(data), 4096)
    struct.pack_into('<IIQQQQQQ', data, 120, 2, 4, 256, 256, 0, len(tags) * 16, len(tags) * 16, 8)
    for i, tag in enumerate(tags): struct.pack_into('<qQ', data, 256 + i * 16, *tag)
    data[512:] = strings
    return bytes(data)


@pytest.mark.parametrize('kind', ['valid', 'glibc', 'machine', 'rpath', 'truncated'])
def test_library_must_be_arm64_musl_only_without_search_path(unwind, kind):
    raw = library_elf(needed=b'libc.so.6' if kind == 'glibc' else b'libc.musl-aarch64.so.1',
                      machine=62 if kind == 'machine' else 183, rpath=kind == 'rpath')
    if kind == 'truncated': raw = raw[:70]
    if kind == 'valid': unwind.unwind_library(raw)
    else:
        with pytest.raises(RuntimeError, match='unwind_elf'):
            unwind.unwind_library(raw)


@pytest.fixture
def installable(unwind, tmp_path, monkeypatch):
    monkeypatch.setattr(unwind, 'WORK', tmp_path)
    monkeypatch.setattr(unwind, 'DEADLINE', time.monotonic() + 30)
    (tmp_path / 'downloads').mkdir()
    prefix = tmp_path / 'toolchain-unwind-1'
    raw = library_elf()
    for item in unwind.unwind_artifacts: (tmp_path / 'downloads' / item['name']).write_bytes(b'fixture')
    monkeypatch.setattr(unwind, 'unwind_checked', lambda item: tmp_path / 'downloads' / item['name'])
    monkeypatch.setattr(unwind, 'verify_static_arm64', lambda path: 'static-sha')
    monkeypatch.setattr(unwind, 'unwind_openssl', lambda: None)
    def members(path):
        if path.name.startswith('apk-tools-static'):
            return {'sbin/apk.static': b'authenticated executable', unwind.unwind_signature: bytes(512),
                    '.PKGINFO': pkginfo(unwind.unwind_packages[0])}
        return {'.PKGINFO': pkginfo(unwind.unwind_packages[1]), 'usr/lib/libgcc_s.so.1': raw}
    monkeypatch.setattr(unwind, 'unwind_members', members)
    calls = []
    def command(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[0] == '/usr/bin/openssl': return b'Verified OK\n', b''
        if '--version' in argv: return unwind.unwind_version, b''
        return b'packages verified\n', b''
    monkeypatch.setattr(unwind, 'command', command)
    return unwind, prefix, calls, raw


def test_signature_version_offline_verification_precede_library_write(installable):
    unwind, prefix, calls, raw = installable
    report = unwind.unwind_install(prefix)
    assert calls[0][0][:3] == ['/usr/bin/openssl', 'dgst', '-sha256']
    assert '--version' in calls[1][0]
    verify = calls[2][0]
    assert {'--no-network', '--no-cache', '--keys-dir', '--root', 'verify'} <= set(verify)
    assert '--allow-untrusted' not in verify
    assert verify[verify.index('--keys-dir') + 1] == 'keys'
    assert verify[verify.index('--repositories-file') + 1] == '/dev/null'
    assert (prefix / 'lib/libgcc_s.so.1').read_bytes() == raw
    assert report['library_sha256'] == hashlib.sha256(raw).hexdigest()
    assert report['authenticated_archives'] == 2
    assert all('LD_LIBRARY_PATH' not in kw['environment'] for _, kw in calls)


@pytest.mark.parametrize('failure', ['signature', 'version', 'apk'])
def test_failed_verification_never_installs_library(installable, monkeypatch, failure):
    unwind, prefix, calls, _ = installable
    def command(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[0] == '/usr/bin/openssl':
            if failure == 'signature': raise RuntimeError('signature rejected')
            return b'Verified OK\n', b''
        if '--version' in argv:
            return (b'changed version\n' if failure == 'version' else unwind.unwind_version), b''
        raise RuntimeError('APK rejected')
    monkeypatch.setattr(unwind, 'command', command)
    with pytest.raises(RuntimeError): unwind.unwind_install(prefix)
    assert not prefix.exists()
    if failure == 'signature': assert len(calls) == 1


def test_unknown_or_existing_prefix_refuses_without_execution(installable, monkeypatch):
    unwind, prefix, calls, _ = installable
    with pytest.raises(RuntimeError, match='unwind_prefix'): unwind.unwind_install(prefix.parent / 'toolchain')
    (prefix / 'lib').mkdir(parents=True)
    (prefix / 'lib/libgcc_s.so.1').write_bytes(b'preserve')
    with pytest.raises(RuntimeError, match='unwind_prefix'): unwind.unwind_install(prefix)
    assert (prefix / 'lib/libgcc_s.so.1').read_bytes() == b'preserve'
    assert calls == []


@pytest.mark.parametrize('kind', ['valid', 'short', 'oversize', 'key_digest', 'redirect'])
def test_download_bounds_and_key_hash_before_promotion(unwind, tmp_path, monkeypatch, kind):
    expected = b'verified key'
    body = {'short': expected[:-1], 'oversize': expected + b'x', 'key_digest': b'x' * len(expected)}.get(kind, expected)
    item = dict(unwind.unwind_artifacts[2], bytes=len(expected), sha256=hashlib.sha256(expected).hexdigest())
    class Response(io.BytesIO):
        status = 200
        url = 'https://elsewhere.invalid' if kind == 'redirect' else item['url']
    class Opener:
        def open(self, *a, **k): return Response(body)
    monkeypatch.setattr(unwind, 'WORK', tmp_path)
    monkeypatch.setattr(unwind, 'DEADLINE', time.monotonic() + 10)
    monkeypatch.setattr(unwind, 'unwind_artifacts', (item,))
    monkeypatch.setattr(unwind.urllib.request, 'build_opener', lambda *a: Opener())
    (tmp_path / 'downloads').mkdir()
    target = tmp_path / 'downloads' / item['name']
    if kind == 'valid':
        report = unwind.unwind_download()
        assert target.read_bytes() == expected and report['authenticated_archives'] == 0
    else:
        with pytest.raises(RuntimeError, match='unwind_download_'): unwind.unwind_download()
        assert not target.exists()
        assert target.with_name(target.name + '.partial').exists()


def test_exact_bootstrap_cache_reauthenticates_and_changed_file_refuses(installable, monkeypatch):
    unwind, prefix, calls, _ = installable
    original = unwind.command
    def failed_verify(argv, **kwargs):
        if 'verify' in argv: raise RuntimeError('native APK rejection')
        return original(argv, **kwargs)
    monkeypatch.setattr(unwind, 'command', failed_verify)
    with pytest.raises(RuntimeError): unwind.unwind_install(prefix)
    assert not prefix.exists()
    monkeypatch.setattr(unwind, 'command', original)
    calls.clear()
    unwind.unwind_install(prefix)
    assert calls[0][0][0] == '/usr/bin/openssl'
    binary = prefix.parent / 'unwind-bootstrap-1/apk.static'
    binary.chmod(0o700)
    binary.write_bytes(b'changed')
    with pytest.raises(RuntimeError, match='unwind_'):
        unwind.unwind_save(binary, b'authenticated executable', 0o500)


def test_authenticated_archives_cannot_change_before_publication(installable, monkeypatch):
    unwind, prefix, calls, _ = installable
    original = unwind.command
    def change_archive(argv, **kwargs):
        result = original(argv, **kwargs)
        if 'verify' in argv:
            (prefix.parent / 'downloads' / unwind.unwind_artifacts[1]['name']).write_bytes(b'changed after verify')
        return result
    monkeypatch.setattr(unwind, 'command', change_archive)
    with pytest.raises(RuntimeError, match='unwind_artifact_changed'): unwind.unwind_install(prefix)
    assert not prefix.exists()
