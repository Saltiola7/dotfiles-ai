"""Offline reuse proofs, using synthetic archives and no native execution."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
from types import ModuleType

import pytest


@pytest.fixture
def reuse():
    base = Path(__file__).parent / 'fixtures/openshell_runtime'
    path = base / 'guest_resume.py'
    assert path.is_file(), 'closed resume implementation absent: intended red'
    module = ModuleType('guest_resume_test')
    exec(compile((base / 'guest_harness.py').read_text() + '\n' + path.read_text(), str(path), 'exec'), module.__dict__)
    return module


def archive(path, entries, mode='w:xz'):
    with tarfile.open(path, mode) as tar:
        for name, body in entries.items():
            item = tarfile.TarInfo(name)
            item.mode = 0o755 if '/bin/' in name else 0o644
            if body is None:
                item.type = tarfile.DIRTYPE
                tar.addfile(item)
                continue
            item.size = len(body)
            tar.addfile(item, io.BytesIO(body))


def put(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


@pytest.fixture
def retained(reuse, tmp_path, monkeypatch):
    work = tmp_path / 'work'; work.mkdir(mode=0o700)
    monkeypatch.setattr(reuse, 'WORK', work)
    monkeypatch.setattr(reuse, 'DEADLINE', time.monotonic() + 30)
    (work / 'target').mkdir()
    prefix = work / 'toolchain-unwind-1'
    paths = {
        'cargo': {'bin/cargo': b'cargo'},
        'rustc': {'bin/rustc': b'rustc', 'bin/rustdoc': b'rustdoc', 'lib/librustc_driver.so': b'compiler-library',
                  'lib/rustlib/' + reuse.HOST + '/bin/rust-lld': b'linker'},
        'rust-std': {'lib/rustlib/' + reuse.HOST + '/lib/libstd.rlib': b'standard-library'},
    }
    items = []
    for part, entries in paths.items():
        root = f'{part}-1.95.0-{reuse.HOST}'
        component = 'rust-std-' + reuse.HOST if part == 'rust-std' else part
        path = work / 'downloads' / (root + '.tar.xz'); path.parent.mkdir(exist_ok=True)
        archive(path, {root + '/' + component + '/' + name: raw for name, raw in entries.items()})
        items.append({'archive': path.name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for name, raw in entries.items(): put(prefix / name, raw, 0o755 if '/bin/' in '/' + name else 0o644)
    put(prefix / 'lib/libgcc_s.so.1', b'unwind', 0o444)
    put(prefix / 'lib/rustlib/components', ('cargo\nrustc\nrust-std-' + reuse.HOST + '\n').encode())
    monkeypatch.setattr(reuse, 'unwind_verify', lambda: ({'authenticated_archives': 2}, b'unwind'), raising=False)
    name = 'tiny-1.0.0'; registry = 'index.crates.io-1949cf8c6b5b557f'
    crate = work / 'cargo/registry/cache' / registry / (name + '.crate')
    crate.parent.mkdir(parents=True)
    archive(crate, {name + '/Cargo.toml': b'[package]\nname="tiny"\n', name + '/src/lib.rs': b'pub fn tiny() {}\n'}, 'w:gz')
    digest = hashlib.sha256(crate.read_bytes()).hexdigest()
    src = work / 'cargo/registry/src' / registry / name
    put(src / 'Cargo.toml', b'[package]\nname="tiny"\n'); put(src / 'src/lib.rs', b'pub fn tiny() {}\n')
    put(src / '.cargo-ok', b'{"v":1}')
    lock = ('version=4\n[[package]]\nname="tiny"\nversion="1.0.0"\n'
            'source="registry+https://github.com/rust-lang/crates.io-index"\nchecksum="' + digest + '"\n')
    files = {'Cargo.toml': '[package]\n', 'Cargo.lock': lock, 'src/lib.rs': 'mod linux;\n',
             'src/linux/child_seccomp.rs': 'new portability fix\n'}
    old = b'old patched source\n'
    monkeypatch.setattr(reuse, 'RESUME_OLD_SHA', hashlib.sha256(old).hexdigest())
    for name, content in files.items(): put(work / 'harness' / name, content.encode())
    put(work / 'harness/src/linux/child_seccomp.rs', old)
    payload = {'files': files, 'toolchain': {'artifacts': items},
               'patched_sha256': hashlib.sha256(files['src/linux/child_seccomp.rs'].encode()).hexdigest()}
    return reuse, work, prefix, src, payload, old


def test_complete_reuse_preserves_old_source_and_tools(retained):
    reuse, work, prefix, _, payload, old = retained
    before = (prefix / 'bin/rustc').stat()
    report = reuse.resume(payload)
    assert (prefix / 'bin/rustc').stat().st_ino == before.st_ino
    assert (work / 'resume-original-child_seccomp.rs').read_bytes() == old
    assert (work / 'harness/src/linux/child_seccomp.rs').read_text() == payload['files']['src/linux/child_seccomp.rs']
    assert (work / 'target/resume-1').is_dir()
    assert report['offline_reuse_verified'] is True


@pytest.mark.parametrize('change', ['compiler', 'driver', 'stdlib', 'unwind', 'extra_library', 'archive', 'crate_archive', 'crate_source', 'extra_source', 'config', 'source', 'source_link', 'tool_link', 'tool_hardlink', 'group_write', 'existing_target'])
def test_changed_or_escaped_inputs_refuse_before_source_update(retained, change):
    reuse, work, prefix, src, payload, old = retained
    selected = {
        'compiler': prefix / 'bin/rustc', 'driver': prefix / 'lib/librustc_driver.so',
        'stdlib': prefix / ('lib/rustlib/' + reuse.HOST + '/lib/libstd.rlib'),
        'unwind': prefix / 'lib/libgcc_s.so.1', 'crate_source': src / 'src/lib.rs',
        'source': work / 'harness/Cargo.toml',
    }
    if change in selected:
        selected[change].chmod(0o644)
        selected[change].write_bytes(b'changed')
    elif change == 'extra_library': put(prefix / 'lib/extra.so', b'unknown')
    elif change == 'archive': (work / 'downloads' / payload['toolchain']['artifacts'][0]['archive']).write_bytes(b'changed')
    elif change == 'crate_archive': next((work / 'cargo/registry/cache').glob('*/*.crate')).write_bytes(b'changed')
    elif change == 'extra_source': put(src / 'build.rs', b'fn main() {}')
    elif change == 'config': put(work / 'cargo/config.toml', b'[build]\nrustc="elsewhere"')
    elif change in {'tool_link', 'source_link'}:
        path = prefix / 'bin/rustc' if change == 'tool_link' else work / 'harness/Cargo.toml'
        raw = path.read_bytes(); path.unlink(); put(work / 'elsewhere', raw); path.symlink_to(work / 'elsewhere')
    elif change == 'tool_hardlink': reuse.os.link(prefix / 'bin/rustc', work / 'alias')
    elif change == 'group_write': (prefix / 'bin/rustc').chmod(0o775)
    elif change == 'existing_target': (work / 'target/resume-1').mkdir()
    with pytest.raises(RuntimeError, match='resume_'):
        reuse.resume(payload)
    assert (work / 'harness/src/linux/child_seccomp.rs').read_bytes() == old
    assert not (work / 'resume-original-child_seccomp.rs').exists()


def test_deadline_expiry_precedes_reads_or_writes(retained, monkeypatch):
    reuse, work, _, _, payload, old = retained
    monkeypatch.setattr(reuse, 'DEADLINE', time.monotonic() - 1)
    with pytest.raises(RuntimeError, match='deadline'): reuse.resume(payload)
    assert (work / 'harness/src/linux/child_seccomp.rs').read_bytes() == old


@pytest.mark.parametrize('extra', ['empty_package', 'alternate_registry'])
def test_unknown_source_namespace_refuses(retained, extra):
    reuse, work, _, src, payload, old = retained
    path = src.parent / 'unknown-1.0.0' if extra == 'empty_package' else src.parent.parent / 'index.crates.io-aaaaaaaaaaaaaaaa'
    path.mkdir()
    with pytest.raises(RuntimeError, match='resume_cargo_'): reuse.resume(payload)
    assert (work / 'harness/src/linux/child_seccomp.rs').read_bytes() == old


def test_preserved_source_allows_only_exact_explicit_recovery(retained):
    reuse, work, _, _, payload, old = retained
    put(work / 'resume-original-child_seccomp.rs', old, 0o400)
    reuse.resume(payload)
    assert (work / 'resume-original-child_seccomp.rs').read_bytes() == old


def test_authenticated_empty_tool_directory_is_allowed(retained):
    reuse, work, prefix, _, payload, _ = retained
    item = payload['toolchain']['artifacts'][0]; root = item['archive'].removesuffix('.tar.xz')
    path = work / 'downloads' / item['archive']
    archive(path, {root+'/cargo/bin/cargo': b'cargo', root+'/cargo/lib/empty': None})
    item.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (prefix / 'lib/empty').mkdir()
    assert reuse.resume(payload)['offline_reuse_verified']


def test_changed_generated_cargo_file_checksum_map_refuses(retained):
    reuse, _, _, src, payload, _ = retained
    expected = reuse.resume_toml.loads(payload['files']['Cargo.lock'])['package'][0]['checksum']
    put(src / '.cargo-checksum.json', json.dumps({'package': expected, 'files': {'src/lib.rs': '0'*64}}).encode())
    with pytest.raises(RuntimeError, match='resume_cargo_checksum'): reuse.resume(payload)


@pytest.mark.parametrize('change', ['changed_backup', 'metadata_symlink', 'unverified_new_source'])
def test_unknown_preservation_or_installer_metadata_refuses(retained, change):
    reuse, work, prefix, _, payload, old = retained
    if change == 'changed_backup': put(work / 'resume-original-child_seccomp.rs', b'unknown')
    elif change == 'metadata_symlink':
        path = prefix / 'lib/rustlib/components'; path.unlink(); path.symlink_to(work / 'elsewhere')
    else: put(work / 'harness/src/linux/child_seccomp.rs', payload['files']['src/linux/child_seccomp.rs'].encode())
    with pytest.raises(RuntimeError, match='resume_'): reuse.resume(payload)
    assert not (work / 'target/resume-1').exists()


def test_source_module_has_no_entrypoint_or_network(tmp_path):
    path = Path(__file__).parent / 'fixtures/openshell_runtime/guest_resume.py'
    assert path.is_file(), 'closed resume implementation absent: intended red'
    source = path.read_text()
    assert len(source.encode()) <= 18 * 1024
    assert '__main__' not in source and 'urlopen' not in source
