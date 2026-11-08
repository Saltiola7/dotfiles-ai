"""Source-only installer tests: no native core execution or network access."""
import ast
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'dot_local/bin/executable_remote-herdr-core'


@pytest.fixture
def core():
    loader = importlib.machinery.SourceFileLoader('remote_herdr_core', str(SOURCE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def archive(payload=b'not executable; never run', names=None):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as tar:
        for name in names or ['herdr-core', 'LICENSE', 'THIRD-PARTY-NOTICES']:
            member = tarfile.TarInfo(name)
            data = payload if name == 'herdr-core' else b'notice'
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    return stream.getvalue()


@pytest.fixture
def fixture(tmp_path, core, monkeypatch):
    home = tmp_path / 'home'
    home.mkdir(mode=0o700)
    config = home / '.config/dotfiles-ai'
    config.mkdir(parents=True)
    payload = b'not executable; never run'
    packed = archive(payload)
    pins = dict(version='0.1.18',
                archive_url='https://releases.herdr.dev/core/0.1.18/herdr-core-linux-x86_64.tar.gz',
                archive_sha256=hashlib.sha256(packed).hexdigest(),
                binary_sha256=hashlib.sha256(payload).hexdigest())
    (config / 'herdr-core.json').write_text(json.dumps(pins))
    calls = []
    def download(url):
        calls.append(url)
        return packed
    monkeypatch.setattr(core, 'download', download)
    return home, pins, payload, calls


def test_install_check_and_adopt_without_replacement(core, fixture, monkeypatch):
    home, _, payload, calls = fixture
    core.run(home, 'install')
    binary = home / '.local/bin/herdr-core'
    assert binary.read_bytes() == payload
    assert binary.stat().st_mode & 0o777 == 0o755
    assert os.readlink(binary.parent / 'hc') == 'herdr-core'
    inode = binary.stat().st_ino
    monkeypatch.setattr(core, 'download', lambda _: pytest.fail('unexpected download'))
    core.run(home, 'check')
    core.run(home, 'install')
    assert binary.stat().st_ino == inode
    assert len(calls) == 1


def test_unmanaged_matching_bytes_adopted(core, fixture, monkeypatch):
    home, _, payload, _ = fixture
    binary = home / '.local/bin/herdr-core'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(payload)
    binary.chmod(0o755)
    inode = binary.stat().st_ino
    monkeypatch.setattr(core, 'download', lambda _: pytest.fail('unexpected download'))
    core.run(home, 'install')
    assert binary.stat().st_ino == inode


@pytest.mark.parametrize('alias', ['file', 'dangling', 'directory'])
def test_alias_preserved(core, fixture, alias):
    home, *_ = fixture
    target = home / '.local/bin/hc'
    target.parent.mkdir(parents=True)
    if alias == 'file':
        target.write_bytes(b'keep')
    elif alias == 'dangling':
        target.symlink_to('absent')
    else:
        target.mkdir()
    inode = target.lstat().st_ino
    core.run(home, 'install')
    assert target.lstat().st_ino == inode


@pytest.mark.parametrize('failure', ['archive_hash', 'binary_hash', 'members', 'symlink', 'oversize'])
def test_failed_validation_preserves_drift(core, fixture, monkeypatch, failure):
    home, pins, _, _ = fixture
    binary = home / '.local/bin/herdr-core'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'old private value')
    binary.chmod(0o755)
    packed = archive()
    if failure == 'archive_hash':
        pins['archive_sha256'] = '0' * 64
    elif failure == 'binary_hash':
        pins['binary_sha256'] = '0' * 64
    elif failure == 'members':
        packed = archive(names=['herdr-core', '../escape', 'LICENSE'])
    elif failure == 'symlink':
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as tar:
            member = tarfile.TarInfo('herdr-core')
            member.type = tarfile.SYMTYPE
            member.linkname = '/private'
            tar.addfile(member)
        packed = stream.getvalue()
    else:
        monkeypatch.setattr(core, 'MAX_ARCHIVE', 1)
    if failure != 'archive_hash':
        pins['archive_sha256'] = hashlib.sha256(packed).hexdigest()
    (home / '.config/dotfiles-ai/herdr-core.json').write_text(json.dumps(pins))
    monkeypatch.setattr(core, 'download', lambda _: packed)
    with pytest.raises((ValueError, OSError)):
        core.run(home, 'install')
    assert binary.read_bytes() == b'old private value'
    assert not (binary.parent / 'hc').exists()


def test_check_drift_never_changes_anything(core, fixture):
    home, _, _, calls = fixture
    with pytest.raises(ValueError):
        core.run(home, 'check')
    assert not (home / '.local').exists()
    core.run(home, 'install')
    binary = home / '.local/bin/herdr-core'
    binary.write_bytes(b'drift')
    inode = binary.stat().st_ino
    with pytest.raises(ValueError):
        core.run(home, 'check')
    assert binary.read_bytes() == b'drift'
    assert binary.stat().st_ino == inode
    assert len(calls) == 1


@pytest.mark.parametrize('unsafe', ['symlink', 'hardlink', 'writable', 'directory'])
def test_unsafe_binary_preserved(core, fixture, unsafe):
    home, *_ = fixture
    binary = home / '.local/bin/herdr-core'
    binary.parent.mkdir(parents=True)
    other = home / 'other'
    other.write_bytes(b'keep')
    if unsafe == 'symlink':
        binary.symlink_to(other)
    elif unsafe == 'hardlink':
        os.link(other, binary)
    elif unsafe == 'directory':
        binary.mkdir()
    else:
        binary.write_bytes(b'keep')
        binary.chmod(0o777)
    inode = binary.lstat().st_ino
    with pytest.raises((ValueError, OSError)):
        core.run(home, 'install')
    assert binary.lstat().st_ino == inode
    assert other.read_bytes() == b'keep'


def test_core_and_installer_lock_contention(core, fixture):
    home, *_ = fixture
    core.run(home, 'install')
    binary = home / '.local/bin/herdr-core'
    binary.write_bytes(b'drift')
    native = home / '.local/share/herdr/sessions/example/core.lock'
    native.parent.mkdir(parents=True)
    native.touch(mode=0o600)
    with native.open('rb') as held:
        core.fcntl.flock(held, core.fcntl.LOCK_EX | core.fcntl.LOCK_NB)
        with pytest.raises((ValueError, OSError)):
            core.run(home, 'install')
    assert binary.read_bytes() == b'drift'
    lock = home / '.local/state/dotfiles-ai/herdr-core/install.lock'
    with lock.open('rb') as held:
        core.fcntl.flock(held, core.fcntl.LOCK_EX | core.fcntl.LOCK_NB)
        with pytest.raises((ValueError, OSError)):
            core.run(home, 'install')
    core.run(home, 'install')
    core.run(home, 'check')


@pytest.mark.parametrize('entry', ['config_link', 'parent_link', 'state_link', 'lock_link', 'lock_hardlink'])
def test_unsafe_inputs_never_followed(core, fixture, entry):
    home, *_ = fixture
    config = home / '.config/dotfiles-ai/herdr-core.json'
    if entry == 'config_link':
        other = home / 'pins'
        config.rename(other)
        config.symlink_to(other)
    elif entry == 'parent_link':
        other = home / 'bin'
        other.mkdir()
        (home / '.local').mkdir()
        (home / '.local/bin').symlink_to(other, target_is_directory=True)
    else:
        state = home / '.local/state/dotfiles-ai/herdr-core'
        state.parent.mkdir(parents=True)
        other = home / 'other'
        if entry == 'state_link':
            other.mkdir()
            state.symlink_to(other, target_is_directory=True)
        else:
            state.mkdir(mode=0o700)
            other.write_bytes(b'keep')
            if entry == 'lock_link':
                (state / 'install.lock').symlink_to(other)
            else:
                os.link(other, state / 'install.lock')
    with pytest.raises((OSError, ValueError)):
        core.run(home, 'install')
    assert not (home / '.local/bin/herdr-core').exists()


def test_foreign_ownership_refused(core, fixture, monkeypatch):
    home, *_ = fixture
    monkeypatch.setattr(core.os, 'getuid', lambda: -1)
    with pytest.raises(ValueError):
        core.run(home, 'install')


def test_lock_scan_symlink_refused_and_injectable(core, fixture):
    home, *_ = fixture
    core.run(home, 'install')
    binary = home / '.local/bin/herdr-core'
    binary.write_bytes(b'drift')
    state = home / '.local/share/herdr'
    state.mkdir(parents=True)
    (state / 'sessions').symlink_to(home)
    with pytest.raises((OSError, ValueError)):
        core.run(home, 'install')
    assert binary.read_bytes() == b'drift'
    with core.ExitStack() as stack:
        fd = core.keep(stack, os.open(home, os.O_RDONLY))
        core.core_locks(stack, fd, roots=('missing-fixture-state',))
        with pytest.raises(ValueError):
            core.core_locks(stack, fd, roots=('../outside',))


def test_mode_drift_and_atomic_failure(core, fixture, monkeypatch):
    home, _, payload, _ = fixture
    core.run(home, 'install')
    binary = home / '.local/bin/herdr-core'
    binary.chmod(0o644)
    with pytest.raises(ValueError):
        core.run(home, 'check')
    monkeypatch.setattr(core.os, 'replace', lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))
    with pytest.raises(OSError):
        core.run(home, 'install')
    assert binary.read_bytes() == payload
    assert binary.stat().st_mode & 0o777 == 0o644
    assert sorted(path.name for path in binary.parent.iterdir()) == ['hc', 'herdr-core']


def test_bounded_payload_and_duplicate_members(core, fixture, monkeypatch):
    home, pins, _, _ = fixture
    packed = archive(names=['herdr-core', 'LICENSE', 'LICENSE'])
    pins['archive_sha256'] = hashlib.sha256(packed).hexdigest()
    (home / '.config/dotfiles-ai/herdr-core.json').write_text(json.dumps(pins))
    monkeypatch.setattr(core, 'download', lambda _: packed)
    with pytest.raises(ValueError):
        core.run(home, 'install')
    monkeypatch.setattr(core, 'MAX_TAR', 1)
    with pytest.raises(ValueError):
        core.run(home, 'install')


def test_sanitized_cli_errors_and_no_native_execution(core, fixture, monkeypatch, capsys):
    home, *_ = fixture
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setattr(core, 'download', lambda _: (_ for _ in ()).throw(ValueError('PRIVATE')))
    assert core.main(['install']) == 1
    output = capsys.readouterr()
    assert not output.out
    assert 'PRIVATE' not in output.err and str(home) not in output.err
    assert len(output.err) < 150
    assert core.main(['status']) == 2
    source = SOURCE.read_text()
    calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
             and node.func.value.id == 'subprocess']
    assert len(calls) == 1 and isinstance(calls[0].func, ast.Attribute) and calls[0].func.attr == 'run'
    assert isinstance(calls[0].args[0], ast.List) and isinstance(calls[0].args[0].elts[0], ast.Constant)
    assert calls[0].args[0].elts[0].value == 'curl'
    assert 'os.exec' not in source
    assert '.extractall(' not in source


def test_template_pin_keys_are_json_quoted():
    source = (ROOT / 'private_dot_config/dotfiles-ai/herdr-core.json.tmpl').read_text()
    for key in ('version', 'archive_url', 'archive_sha256', 'binary_sha256'):
        assert '{{ .dotfiles_ai.herdr_core.' + key + ' | toJson }}' in source


def test_download_is_bounded_and_redirects_refused(core, monkeypatch):
    def transport(argv, **kwargs):
        assert argv[:4] == ['curl', '--proto', '=https', '--tlsv1.2']
        assert '-L' not in argv and '--location' not in argv
        assert argv[argv.index('--max-filesize') + 1] == '4'
        assert kwargs == {'capture_output': True, 'check': True, 'timeout': 100}
        return core.subprocess.CompletedProcess(argv, 0, stdout=b'12345')
    monkeypatch.setattr(core.subprocess, 'run', transport)
    monkeypatch.setattr(core, 'MAX_ARCHIVE', 4)
    with pytest.raises(ValueError):
        core.download('synthetic-fixture-only')


def test_quiescence_precedes_download(core, fixture, monkeypatch):
    home, *_ = fixture
    core.run(home, 'install')
    binary = home / '.local/bin/herdr-core'
    binary.write_bytes(b'drift')
    native = home / '.local/state/herdr-core/sessions/core.lock'
    native.parent.mkdir(parents=True)
    native.touch(mode=0o600)
    monkeypatch.setattr(core, 'download', lambda _: pytest.fail('busy core must not download'))
    with native.open('rb') as held:
        core.fcntl.flock(held, core.fcntl.LOCK_EX | core.fcntl.LOCK_NB)
        with pytest.raises(OSError):
            core.run(home, 'install')


def test_state_traversal_is_bounded(core, fixture):
    home, *_ = fixture
    state = home / 'fixture-state'
    state.mkdir()
    for _ in range(14):
        state /= 'child'
        state.mkdir()
    with core.ExitStack() as stack:
        fd = core.keep(stack, os.open(home, os.O_RDONLY))
        with pytest.raises(ValueError):
            core.core_locks(stack, fd, roots=('fixture-state',))
