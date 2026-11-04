"""Synthetic source admission tests; no network, compiler, VM or kernel proof."""
import ast
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import time
from types import ModuleType

import pytest


BASE = Path(__file__).parent / 'fixtures/openshell_runtime'
NETWORK = 'crates/openshell-sandbox/src/network_broker.rs'
NETWORK_OLD = b'''                let header = libc::msghdr {
                    msg_name: native.as_ptr().cast_mut().cast(),
                    msg_namelen: native.len(),
                    msg_iov: &raw mut iov,
                    msg_iovlen: 1,
                    msg_control: control.as_mut_ptr().cast(),
                    msg_controllen: control.len(),
                    msg_flags: 0,
                };'''
NETWORK_NEW = b'''                // SAFETY: msghdr contains only integer and pointer fields;
                // zero initialization also initializes target-specific padding.
                let mut header: libc::msghdr = unsafe { std::mem::zeroed() };
                header.msg_name = native.as_ptr().cast_mut().cast();
                header.msg_namelen = native.len();
                header.msg_iov = &raw mut iov;
                header.msg_iovlen = 1;
                header.msg_control = control.as_mut_ptr().cast();
                header.msg_controllen = control
                    .len()
                    .try_into()
                    .expect("control length fits target ABI");
                header.msg_flags = 0;'''


@pytest.fixture
def source():
    path = BASE / 'guest_full_source.py'
    assert path.is_file(), 'Full source helper absent: intended red'
    module = ModuleType('full_source_test')
    exec(compile((BASE / 'guest_harness.py').read_text() + '\n' + path.read_text(), str(path), 'exec'), module.__dict__)
    return module


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def object_id(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def tree_fixture(files):
    """Build a tiny independent Git object fixture, including ordering collision."""
    entries = {}
    for path, (mode, body) in files.items():
        entries[path] = {'path': path, 'mode': mode, 'type': 'blob', 'size': len(body), 'sha': object_id('blob', body)}
        for parent in Path(path).parents:
            if str(parent) != '.': entries.setdefault(str(parent), {'path': str(parent), 'mode': '040000', 'type': 'tree'})
    directories = sorted([p for p, v in entries.items() if v['type'] == 'tree'], key=lambda x: x.count('/'), reverse=True) + ['']
    for directory in directories:
        children = [v for p, v in entries.items() if str(Path(p).parent).replace('.', '', 1) == directory] if not directory else [v for p, v in entries.items() if str(Path(p).parent) == directory]
        children.sort(key=lambda v: Path(v['path']).name.encode() + (b'/' if v['type'] == 'tree' else b'\0'))
        body = b''.join((v['mode'].lstrip('0') + ' ' + Path(v['path']).name).encode() + b'\0' + bytes.fromhex(v['sha']) for v in children)
        digest = object_id('tree', body)
        if directory: entries[directory]['sha'] = digest
        else: root = digest
    return {'sha': root, 'truncated': False, 'tree': list(entries.values())}


def archive_fixture(files, root, extra=()):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT, pax_headers={'comment': 'source fixture'}) as archive:
        for path, (mode, body) in [*files.items(), *extra]:
            member = tarfile.TarInfo(root + '/' + path)
            if mode == '120000':
                member.type = tarfile.SYMTYPE; member.linkname = body.decode(); member.mode = 0o777
                archive.addfile(member)
            elif mode == 'fifo':
                member.type = tarfile.FIFOTYPE; archive.addfile(member)
            else:
                member.mode = 0o775 if mode == '100755' else 0o664
                member.size = len(body); archive.addfile(member, io.BytesIO(body))
    return gzip.compress(stream.getvalue())


@pytest.fixture
def retained(source, tmp_path, monkeypatch):
    work = tmp_path / 'work'; work.mkdir(mode=0o700)
    monkeypatch.setattr(source, 'WORK', work)
    monkeypatch.setattr(source, 'DEADLINE', time.monotonic() + 60)
    version = '0.1.7+dotfiles-ai.child-unix-deny.2'
    manifest = b'[workspace]\nmembers=["crates/*"]\n[workspace.package]\nversion = "0.0.0"\n'
    lock = (b'version = 4\n\n[[package]]\nname = "openshell-sandbox"\nversion = "0.0.0"\n\n'
            b'[[package]]\nname = "external"\nversion = "0.0.0"\nsource = "registry+https://github.com/rust-lang/crates.io-index"\nchecksum = "' + b'a'*64 + b'"\n')
    child = 'crates/openshell-sandbox/src/linux/child_seccomp.rs'
    network = b'// production remains unchanged\n#[cfg(test)]\nmod tests {\n'+NETWORK_OLD+b'\n}\n'
    files = {'Cargo.toml': ('100644', manifest), 'Cargo.lock': ('100644', lock), child: ('100644', b'old child\n'),
             NETWORK: ('100644', network),
             'crates/openshell-sandbox/Cargo.toml': ('100644', b'[package]\nname="openshell-sandbox"\nversion.workspace=true\n'),
             '.claude/skills': ('120000', b'../.agents/skills/'), '.agents/skills/README': ('100644', b'fixture\n'),
             'foo.bar': ('100644', b'first'), 'foo/run': ('100755', b'#!/bin/sh\nexit 0\n')}
    metadata = tree_fixture(files)
    contract = copy.deepcopy(source.full_source_contract)
    contract.update(entries=len(metadata['tree']), blobs=len(files), blob_bytes=sum(len(v[1]) for v in files.values()),
                    original_manifest_sha256=sha(manifest), derived_manifest_sha256=sha(manifest.replace(b'0.0.0', version.encode())),
                    original_lock_sha256=sha(lock), derived_lock_sha256=sha(lock.replace(b'version = "0.0.0"', ('version = "'+version+'"').encode(), 1)),
                    local_packages=1, external_packages=1,
                    network_test_original_sha256=sha(network),
                    network_test_sha256=sha(network.replace(NETWORK_OLD, NETWORK_NEW)))
    monkeypatch.setattr(source, 'full_source_contract', contract)
    monkeypatch.setattr(source, 'full_source_tree_sha1', metadata['sha'])
    monkeypatch.setattr(source, 'full_source_local_names', ('openshell-sandbox',))
    monkeypatch.setattr(source, 'full_source_child_before', sha(b'old child\n'))
    monkeypatch.setattr(source, 'full_source_child_after', sha(b'new child\n'))
    payload = {'full_manifest': {'schema_version': 1, 'upstream_commit': source.full_source_commit,
                'upstream_tree_sha1': metadata['sha'], 'experimental_version': version, 'source': contract,
                'cargo': {'source': 'full-source-2'}}, 'files': {'src/linux/child_seccomp.rs': 'new child\n'}, 'patched_sha256': sha(b'new child\n')}
    inputs = work / 'full-source-inputs-1'; inputs.mkdir(mode=0o700)
    (inputs / 'tree.json').write_bytes(json.dumps(metadata).encode())
    (inputs / 'source.tar.gz').write_bytes(archive_fixture(files, 'OpenShell-'+source.full_source_commit))
    monkeypatch.setattr(source.urllib.request, 'build_opener', lambda *a: pytest.fail('unexpected network'))
    return source, work, inputs, payload, files, metadata


def test_contract_matches_committed_manifest(source):
    manifest = json.loads((BASE / 'fullbuild/manifest.json').read_text())
    assert source.full_source_contract == manifest['source']
    assert source.full_source_tree_sha1 == manifest['upstream_tree_sha1']
    assert len(source.full_source_local_names) == 39


def test_prepare_changes_only_four_files_and_verify_is_readonly(retained):
    source, work, _, payload, files, _ = retained
    report = source.full_source_prepare(payload, 30)
    root = work / 'full-source-2'
    assert report['source_verified'] and report['changed_files'] == 4
    assert report['source_generation'] == 2 and report['source'] == str(root)
    assert report['network_test_original_sha256'] == sha(files[NETWORK][1])
    assert report['network_test_sha256'] == sha(files[NETWORK][1].replace(NETWORK_OLD, NETWORK_NEW))
    assert report['upstream_commit'] == source.full_source_commit
    assert report['session_enabled'] is False and report['full_runtime_qualified'] is False
    changed = []
    for name, (mode, raw) in files.items():
        path = root/name
        if mode == '120000': assert os.readlink(path) == raw.decode()
        else:
            if path.read_bytes() != raw: changed.append(name)
            assert path.stat().st_mode & 0o777 == (0o755 if mode == '100755' else 0o644)
    assert set(changed) == {'Cargo.toml', 'Cargo.lock', 'crates/openshell-sandbox/src/linux/child_seccomp.rs', NETWORK}
    assert (root/NETWORK).read_bytes().split(b'#[cfg(test)]')[0] == files[NETWORK][1].split(b'#[cfg(test)]')[0]
    before = {p: p.lstat().st_mtime_ns for p in root.rglob('*')}
    assert source.full_source_verify(payload, 30)['source_verified']
    assert before == {p: p.lstat().st_mtime_ns for p in root.rglob('*')}


@pytest.mark.parametrize('kind', ['root', 'blob', 'subtree', 'duplicate', 'missing', 'truncated', 'parent', 'mode', 'size_bool', 'traversal', 'gitlink'])
def test_tree_metadata_corruption_refuses_before_source_publication(retained, kind):
    source, work, inputs, payload, _, metadata = retained
    if kind == 'root': metadata['sha'] = '0'*40
    elif kind == 'blob': next(x for x in metadata['tree'] if x['type']=='blob')['sha'] = '0'*40
    elif kind == 'subtree': next(x for x in metadata['tree'] if x['type']=='tree')['sha'] = '0'*40
    elif kind == 'duplicate': metadata['tree'].append(metadata['tree'][0])
    elif kind == 'missing': metadata['tree'].pop()
    elif kind == 'truncated': metadata['truncated'] = True
    elif kind == 'parent': next(x for x in metadata['tree'] if x['type']=='blob')['path'] = 'absent/file'
    elif kind == 'mode': metadata['tree'][0]['mode'] = '100600'
    elif kind == 'size_bool': next(x for x in metadata['tree'] if x['type']=='blob')['size'] = True
    elif kind == 'traversal': metadata['tree'][0]['path'] = '../escape'
    else: metadata['tree'][0].update(type='commit', mode='160000')
    (inputs/'tree.json').write_text(json.dumps(metadata))
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_prepare(payload, 30)
    assert not (work/'full-source-2').exists()


@pytest.mark.parametrize('kind', ['changed', 'missing', 'duplicate', 'traversal', 'absolute', 'fifo', 'escape_link', 'extra', 'gzip_tail', 'truncated', 'expansion'])
def test_archive_corruption_refuses_before_source_publication(retained, kind, monkeypatch):
    source, work, inputs, payload, files, _ = retained
    files = copy.deepcopy(files); extras = []
    if kind == 'changed': files['foo.bar'] = ('100644', b'changed')
    elif kind == 'missing': files.pop('foo.bar')
    elif kind == 'duplicate': extras = [('foo.bar', files['foo.bar'])]
    elif kind == 'traversal': extras = [('../escape', ('100644', b'escape'))]
    elif kind == 'absolute': extras = [('/escape', ('100644', b'escape'))]
    elif kind == 'fifo': extras = [('fifo', ('fifo', b''))]
    elif kind == 'escape_link': files['.claude/skills'] = ('120000', b'../../../outside')
    elif kind == 'extra': extras = [('unknown', ('100644', b'unknown'))]
    raw = archive_fixture(files, 'OpenShell-'+source.full_source_commit, extras)
    if kind == 'gzip_tail': raw += gzip.compress(b'unexpected')
    elif kind == 'truncated': raw = raw[:-5]
    elif kind == 'expansion':
        monkeypatch.setitem(source.full_source_contract, 'expanded_limit', 1024)
        payload['full_manifest']['source']['expanded_limit'] = 1024
    (inputs/'source.tar.gz').write_bytes(raw)
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_prepare(payload, 30)
    assert not (work/'full-source-2').exists()


@pytest.mark.parametrize('kind', ['changed', 'extra', 'missing', 'mode', 'symlink', 'hardlink', 'foreign_device'])
def test_retained_source_drift_refuses_without_repair(retained, kind, monkeypatch):
    source, work, _, payload, _, _ = retained
    source.full_source_prepare(payload, 30); path = work/'full-source-2/foo.bar'
    if kind == 'changed': path.write_bytes(b'changed')
    elif kind == 'extra': (path.parent/'extra').write_bytes(b'extra')
    elif kind == 'missing': path.unlink()
    elif kind == 'mode': path.chmod(0o666)
    elif kind == 'symlink': path.unlink(); path.symlink_to(work/'outside')
    elif kind == 'hardlink': os.link(path, work/'alias')
    else:
        original = source.full_source_owned
        def reject(info, selected, **kwargs):
            if str(selected).endswith('foo.bar'): raise RuntimeError('full_source_mount')
            return original(info, selected, **kwargs)
        monkeypatch.setattr(source, 'full_source_owned', reject)
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_verify(payload, 30)


def test_explicit_prepare_completes_missing_exact_files_but_never_overwrites(retained):
    source, work, _, payload, _, _ = retained
    source.full_source_prepare(payload, 30)
    path = work/'full-source-2/foo.bar'; inode = path.stat().st_ino
    other = work/'full-source-2/foo/run'; other.unlink()
    source.full_source_prepare(payload, 30)
    assert path.stat().st_ino == inode and other.is_file()
    path.write_bytes(b'unknown')
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_prepare(payload, 30)
    assert path.read_bytes() == b'unknown'


@pytest.mark.parametrize('kind', ['url', 'limit', 'patch', 'seconds', 'deadline', 'duplicate_json', 'input_symlink'])
def test_contract_deadline_and_input_identity_reject_before_mutation(retained, kind, monkeypatch):
    source, work, inputs, payload, _, _ = retained
    seconds = 30
    if kind == 'url': payload['full_manifest']['source'] = dict(payload['full_manifest']['source'], archive_url='https://elsewhere/')
    elif kind == 'limit': payload['full_manifest']['source'] = dict(payload['full_manifest']['source'], compressed_limit=2**40)
    elif kind == 'patch': payload['files']['src/linux/child_seccomp.rs'] = 'different'
    elif kind == 'seconds': seconds = True
    elif kind == 'deadline': monkeypatch.setattr(source, 'DEADLINE', time.monotonic()-1)
    elif kind == 'duplicate_json': (inputs/'tree.json').write_bytes(b'{"tree":[],"tree":[]}')
    else:
        (inputs/'tree.json').unlink(); (inputs/'tree.json').symlink_to(work/'outside')
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_prepare(payload, seconds)
    assert not (work/'full-source-2').exists()


def test_helper_composes_without_entrypoint_or_global_name_collisions(source):
    raw = (BASE/'guest_full_source.py').read_text(); module = ast.parse(raw)
    assert len(raw.encode()) <= 32*1024
    assert all(n.name.startswith('full_source_') for n in module.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)))
    assert not any(isinstance(n, ast.ImportFrom) and n.module == '__future__' for n in module.body)
    assert not any(isinstance(n, (ast.If, ast.For, ast.While)) for n in module.body)


@pytest.mark.parametrize('kind', ['valid', 'overflow', 'redirect', 'status', 'interrupted'])
def test_fixed_download_is_bounded_and_preserves_failed_partial(retained, monkeypatch, kind):
    source, work, inputs, payload, _, _ = retained
    path = inputs/'tree.json'; raw = path.read_bytes(); path.unlink()
    archive = inputs/'source.tar.gz'; archive_before = archive.read_bytes()
    if kind == 'overflow':
        monkeypatch.setitem(source.full_source_contract, 'metadata_limit', len(raw)-1)
    class Response(io.BytesIO):
        status = 503 if kind == 'status' else 200
        url = 'https://elsewhere/' if kind == 'redirect' else source.full_source_contract['metadata_url']
        def read1(self, count):
            if kind == 'interrupted': raise OSError('transport interrupted')
            return self.read(count)
    class Opener:
        def open(self, request, *, timeout):
            assert request.full_url == source.full_source_contract['metadata_url']
            assert 0 < timeout <= 20
            return Response(raw)
    monkeypatch.setattr(source.urllib.request, 'build_opener', lambda *handlers: Opener())
    if kind == 'valid':
        assert source.full_source_prepare(payload, 30)['source_verified']
        assert path.read_bytes() == raw and not path.with_suffix('.json.partial').exists()
    else:
        with pytest.raises(RuntimeError, match='full_source_'): source.full_source_prepare(payload, 30)
        assert not path.exists() and (inputs/'tree.json.partial').is_file()
        assert not (work/'full-source-2').exists()
    assert archive.read_bytes() == archive_before


def test_bad_metadata_prevents_archive_download(retained, monkeypatch):
    source, _, inputs, payload, _, _ = retained
    (inputs/'tree.json').write_bytes(b'{}'); (inputs/'source.tar.gz').unlink()
    with pytest.raises(RuntimeError, match='full_source_tree_'):
        source.full_source_prepare(payload, 30)


def test_failure_does_not_automatically_retry_or_erase_partial(retained):
    source, work, inputs, payload, _, _ = retained
    (inputs/'tree.json.partial').write_bytes(b'preserved evidence')
    with pytest.raises(RuntimeError, match='full_source_input_entries'):
        source.full_source_prepare(payload, 30)
    assert (inputs/'tree.json.partial').read_bytes() == b'preserved evidence'
    assert not (work/'full-source-2').exists()


def legacy_generation(retained):
    source, work, _, payload, files, _ = retained
    root = work/'full-source-1'; root.mkdir(mode=0o700)
    for name, (mode, raw) in files.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
        if mode == '120000': path.symlink_to(raw.decode()); continue
        if name == 'Cargo.toml': raw = raw.replace(b'0.0.0', source.full_source_version.encode())
        elif name == 'Cargo.lock': raw = raw.replace(b'version = "0.0.0"', ('version = "'+source.full_source_version+'"').encode(), 1)
        elif name == source.full_source_child: raw = payload['files']['src/linux/child_seccomp.rs'].encode()
        path.write_bytes(raw); path.chmod(0o755 if mode == '100755' else 0o644)
    return root


def test_reprepare_is_offline_exclusive_and_preserves_generation_one(retained, monkeypatch):
    source, work, _, payload, files, _ = retained; old = legacy_generation(retained)
    before = {p: source.full_source_identity(p.lstat()) for p in old.rglob('*')}
    monkeypatch.setattr(source, 'full_source_fetch', lambda *a: pytest.fail('offline repair fetched input'))
    report = source.full_source_reprepare(payload, 30)
    assert report == source.full_source_verify(payload, 30)
    assert report['source_generation'] == 2 and report['changed_files'] == 4
    assert before == {p: source.full_source_identity(p.lstat()) for p in old.rglob('*')}
    new = work/'full-source-2'
    changed = []
    for name, (mode, _) in files.items():
        if mode == '120000': assert os.readlink(old/name) == os.readlink(new/name)
        elif (old/name).read_bytes() != (new/name).read_bytes(): changed.append(name)
    assert changed == [NETWORK]
    assert (old/NETWORK).read_bytes() == files[NETWORK][1]
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_reprepare(payload, 30)


@pytest.mark.parametrize('kind', ['directory', 'file', 'dangling_symlink', 'changed', 'missing', 'extra', 'alias', 'archive', 'metadata'])
def test_reprepare_refuses_existing_destination_or_changed_inputs_before_publication(retained, kind, monkeypatch):
    source, work, inputs, payload, _, _ = retained; old = legacy_generation(retained)
    new = work/'full-source-2'
    if kind == 'directory': new.mkdir()
    elif kind == 'file': new.write_bytes(b'preserved')
    elif kind == 'dangling_symlink': new.symlink_to(work/'absent')
    elif kind == 'changed': (old/'foo.bar').write_bytes(b'changed')
    elif kind == 'missing': (old/'foo.bar').unlink()
    elif kind == 'extra': (old/'unknown').write_bytes(b'unknown')
    elif kind == 'alias': os.link(old/'foo.bar', work/'alias')
    elif kind == 'archive': (inputs/'source.tar.gz').write_bytes(b'changed')
    else: (inputs/'tree.json').unlink()
    existed = os.path.lexists(new)
    monkeypatch.setattr(source, 'full_source_write', lambda *a: pytest.fail('published before validation'))
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_reprepare(payload, 30)
    assert os.path.lexists(new) == existed


def test_reprepare_retains_partial_and_does_not_adopt_it(retained, monkeypatch):
    source, work, _, payload, _, _ = retained; legacy_generation(retained)
    write = source.full_source_write; calls = []
    def fail_after_one(path, raw, mode):
        if calls: raise RuntimeError('full_source_synthetic_failure')
        write(path, raw, mode); calls.append(path)
    monkeypatch.setattr(source, 'full_source_write', fail_after_one)
    with pytest.raises(RuntimeError, match='synthetic_failure'): source.full_source_reprepare(payload, 30)
    before = calls[0].read_bytes()
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_reprepare(payload, 30)
    assert len(calls) == 1 and calls[0].read_bytes() == before


def test_reprepare_rechecks_legacy_source_after_publication(retained, monkeypatch):
    source, work, _, payload, _, _ = retained; old = legacy_generation(retained)
    write = source.full_source_write
    def mutate_old(path, raw, mode):
        write(path, raw, mode); (old/'foo.bar').write_bytes(b'other')
    monkeypatch.setattr(source, 'full_source_write', mutate_old)
    with pytest.raises(RuntimeError, match='full_source_retained_content'): source.full_source_reprepare(payload, 30)
    assert (work/'full-source-2').is_dir() and (old/'foo.bar').read_bytes() == b'other'


@pytest.mark.parametrize('kind', ['preimage', 'derived_hash', 'missing_block', 'duplicate_block', 'production_block', 'duplicate_boundary'])
def test_network_transform_requires_exact_test_scope_and_hashes(retained, kind):
    source, _, _, payload, files, _ = retained
    source.full_source_start(payload, 30)
    raw = files[NETWORK][1]
    if kind == 'preimage': raw += b'changed'
    elif kind == 'derived_hash': source.full_source_contract['network_test_sha256'] = '0'*64
    else:
        if kind == 'missing_block': raw = raw.replace(NETWORK_OLD, b'missing')
        elif kind == 'duplicate_block': raw += NETWORK_OLD
        elif kind == 'production_block': raw = NETWORK_OLD+b'\n#[cfg(test)]\nmod tests {\n}\n'
        else: raw += b'#[cfg(test)]\nmod tests {}'
        source.full_source_contract['network_test_original_sha256'] = sha(raw)
        source.full_source_contract['network_test_sha256'] = sha(raw.replace(NETWORK_OLD, NETWORK_NEW, 1))
    with pytest.raises(RuntimeError, match='full_source_'): source.full_source_network_transform({NETWORK: raw})
