"""Synthetic fixture assembly/build admission; no native compiler or kernel proof."""
import ast
import hashlib
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from test_openshell_guest_full_source import retained, source  # noqa: F401
from test_openshell_guest_full_cargo import elf

BASE = Path(__file__).parent / 'fixtures/openshell_runtime'
LIBC = '3eaf3ede3fee6db1a4c2ee091bf8a8b4dccdc6d17f656fb07896ee72867612f2'
FILES = {'Cargo.toml', 'Cargo.lock', 'src/main.rs',
         'src/upstream_child_seccomp.rs', 'src/patched_child_seccomp.rs'}


def fixture_files():
    return {
        'Cargo.toml': '[package]\nname="openshell-agent-filter-probe"\nversion="0.1.0"\nedition="2024"\n[dependencies]\nlibc="=0.2.189"\n',
        'Cargo.lock': 'version = 4\n[[package]]\nname="libc"\nversion="0.2.189"\nsource="registry+https://github.com/rust-lang/crates.io-index"\nchecksum="'+LIBC+'"\n[[package]]\nname="openshell-agent-filter-probe"\nversion="0.1.0"\ndependencies=["libc"]\n',
        'src/main.rs': 'fn main() {}\n',
    }


@pytest.fixture
def build(retained, monkeypatch):
    module, work, inputs, payload, files, metadata = retained
    helper = BASE/'guest_agent_build.py'
    assert helper.is_file(), 'agent builder absent: intended red'
    exec(compile(helper.read_text(), str(helper), 'exec'), module.__dict__)
    module.full_source_prepare(payload, 30)
    monkeypatch.setattr(module, 'agent_build_before', module.full_source_child_before)
    monkeypatch.setattr(module, 'agent_build_after', module.full_source_child_after)
    return module, work, inputs, {'full_manifest': payload['full_manifest'], 'fixture_files': fixture_files()}


def test_prepare_reauthenticates_original_and_derived_source(build):
    module, work, _, payload = build
    report = module.agent_build_prepare(payload)
    root = work/'agent-fixture-1'
    assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == FILES
    assert (root/'src/upstream_child_seccomp.rs').read_bytes() == b'old child\n'
    assert (root/'src/patched_child_seccomp.rs').read_bytes() == b'new child\n'
    assert report == {'schema_version': 1, 'generation': 1, 'status': 'agent_fixture_prepared',
        'source_sha256': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in FILES},
        'session_enabled': False, 'full_runtime_qualified': False, 'compatibility_qualified': False}
    assert all((root/name).stat().st_mode & 0o777 == 0o400 for name in FILES)
    with pytest.raises(RuntimeError, match='agent_build_'): module.agent_build_prepare(payload)


@pytest.mark.parametrize('bad', ['tree', 'archive', 'derived', 'original'])
def test_source_corruption_refuses_before_fresh_fixture(build, bad):
    module, work, inputs, payload = build
    path = {'tree': inputs/'tree.json', 'archive': inputs/'source.tar.gz',
        'derived': work/'full-source-2/crates/openshell-sandbox/src/linux/child_seccomp.rs',
        'original': work/'full-source-2/foo.bar'}[bad]
    path.write_bytes(b'tampered')
    with pytest.raises((RuntimeError, ValueError)): module.agent_build_prepare(payload)
    assert not (work/'agent-fixture-1').exists()


@pytest.mark.parametrize('bad', ['extra', 'path', 'main_size', 'dependency', 'lock_checksum', 'buildscript', 'empty'])
def test_closed_fixture_payload_refuses_before_publication(build, bad):
    module, work, _, payload = build
    files = payload['fixture_files']
    if bad == 'extra': files['build.rs'] = 'fn main() {}'
    elif bad == 'path': files['../Cargo.toml'] = files.pop('Cargo.toml')
    elif bad == 'main_size': files['src/main.rs'] = 'x'*(10*1024+1)
    elif bad == 'dependency': files['Cargo.toml'] += 'socket2="0.6"\n'
    elif bad == 'lock_checksum': files['Cargo.lock'] = files['Cargo.lock'].replace(LIBC, '0'*64)
    elif bad == 'buildscript': files['Cargo.toml'] = files['Cargo.toml'].replace('edition="2024"', 'edition="2024"\nbuild="build.rs"')
    else: files['src/main.rs'] = ''
    with pytest.raises(RuntimeError, match='agent_build_'): module.agent_build_prepare(payload)
    assert not (work/'agent-fixture-1').exists()


@pytest.mark.parametrize('bad', ['extra', 'symlink', 'hardlink', 'tamper', 'config', 'parent_config', 'workspace'])
def test_compile_rejects_changed_source_before_cargo(build, monkeypatch, bad):
    module, work, _, payload = build
    payload['agent_build_report'] = module.agent_build_prepare(payload)
    payload.pop('fixture_files')
    root = work/'agent-fixture-1'
    if bad == 'extra': (root/'extra').write_text('x')
    elif bad == 'symlink':
        (root/'src/main.rs').unlink(); (root/'src/main.rs').symlink_to(work/'outside')
    elif bad == 'hardlink': os.link(root/'src/main.rs', work/'outside')
    elif bad == 'tamper': (root/'src/main.rs').chmod(0o600); (root/'src/main.rs').write_text('tampered')
    elif bad == 'config': (root/'.cargo').mkdir(); (root/'.cargo/config.toml').write_text('[build]\n')
    elif bad == 'workspace': (work/'Cargo.toml').write_text('[workspace]\n')
    else: (work/'.cargo').mkdir(); (work/'.cargo/config.toml').write_text('[build]\n')
    monkeypatch.setattr(module, 'command', lambda *a, **kw: pytest.fail('Cargo ran for invalid input'))
    monkeypatch.setattr(module, 'full_cargo_cache', lambda p: pytest.fail('cache touched before source admission'), raising=False)
    with pytest.raises(RuntimeError, match='agent_build_'): module.agent_build_compile(payload)


def test_appended_helper_has_no_main_or_effects_and_fits_source_cap():
    path = BASE/'guest_agent_build.py'
    assert path.is_file(), 'agent builder absent: intended red'
    raw = path.read_bytes(); assert len(raw) <= 32*1024
    tree = ast.parse(raw)
    assert not any(isinstance(n, ast.ImportFrom) and n.module == '__future__' for n in tree.body)
    assert not any(isinstance(n, (ast.If, ast.With, ast.For, ast.While)) for n in tree.body)


@pytest.fixture
def compile_build(build, monkeypatch):
    module, work, inputs, payload = build
    payload['agent_build_report'] = module.agent_build_prepare(payload)
    payload.pop('fixture_files')
    for name in ('guest_cargo_artifact.py', 'guest_full_cargo.py'):
        exec(compile((BASE/name).read_text(), str(BASE/name), 'exec'), module.__dict__)
    (work/'full-target-1/release/deps').mkdir(parents=True)
    events = []
    monkeypatch.setattr(module, 'full_cargo_cache', lambda p: events.append('cache_authenticated'))
    monkeypatch.setattr(module, 'full_cargo_environment', lambda **kw: {'CARGO_NET_OFFLINE': str(kw['offline'])})
    def compile_fake(argv, **kwargs):
        events.append(('compile', argv, kwargs))
        binary = work/'full-target-1/release/openshell-agent-filter-probe'
        binary.write_bytes(elf()); binary.chmod(0o500)
        os.link(binary, binary.parent/'deps/openshell_agent_filter_probe-0123456789abcdef')
        return b'', b''
    monkeypatch.setattr(module, 'command', compile_fake)
    def static_fd(path):
        assert str(path).startswith('/proc/self/fd/')
        fd = int(path.name)
        assert stat.S_ISREG(os.fstat(fd).st_mode)
        return hashlib.sha256(os.pread(fd, 1024, 0)).hexdigest()
    monkeypatch.setattr(module, 'verify_static_arm64', static_fd)
    return module, work, payload, events


def test_offline_compile_uses_retained_cache_and_holds_exact_probe(compile_build):
    module, work, payload, events = compile_build
    result = module.agent_build_compile(payload)
    assert events[0] == 'cache_authenticated'
    _, argv, options = events[1]
    assert argv == [str(work/module.TOOLCHAIN/'bin/cargo'), 'build', '--release', '--locked', '--offline',
                    '--bin', 'openshell-agent-filter-probe', '--message-format=human']
    assert options == {'cwd': work/'agent-fixture-1', 'maximum': 300, 'environment': {'CARGO_NET_OFFLINE': 'True'}}
    assert result == {**payload['agent_build_report'], 'status': 'agent_fixture_built',
        'binary_sha256': hashlib.sha256(elf()).hexdigest(), 'binary_bytes': len(elf()), 'static_arm64': True,
        'binary_layout': {'link_count': 2, 'companion': 'openshell_agent_filter_probe-0123456789abcdef'}}
    with pytest.raises(RuntimeError, match='agent_build_binary_exists'): module.agent_build_compile(payload)


@pytest.mark.parametrize('failure', ['growth', 'reserve', 'hash', 'source', 'compile'])
def test_compile_failures_preserve_outputs_without_qualification(compile_build, monkeypatch, failure):
    module, work, payload, events = compile_build
    if failure == 'growth':
        sizes = iter([(0, 0), (64*1024**2+1, 0)])
        monkeypatch.setattr(module, 'agent_build_usage', lambda: next(sizes))
    elif failure == 'reserve':
        monkeypatch.setattr(module.os, 'statvfs', lambda p: SimpleNamespace(f_bavail=1, f_frsize=4096))
    elif failure == 'hash': monkeypatch.setattr(module, 'verify_static_arm64', lambda p: '0'*64)
    else:
        old_command = module.command
        def fail_command(*args, **kwargs):
            output = old_command(*args, **kwargs)
            if failure == 'compile': raise RuntimeError('compiler failed')
            path = work/'agent-fixture-1/src/main.rs'; path.chmod(0o600); path.write_text('changed')
            return output
        monkeypatch.setattr(module, 'command', fail_command)
    with pytest.raises(RuntimeError): module.agent_build_compile(payload)
    assert (work/'agent-fixture-1').exists()
    assert (work/'full-target-1/release/openshell-agent-filter-probe').exists()
    assert sum(isinstance(event, tuple) for event in events) == 1


def test_preparation_report_tampering_refuses_before_cache(compile_build, monkeypatch):
    module, _, payload, _ = compile_build
    payload['agent_build_report']['source_sha256']['src/main.rs'] = '0'*64
    monkeypatch.setattr(module, 'full_cargo_cache', lambda p: pytest.fail('cache touched before source proof'))
    with pytest.raises(RuntimeError, match='agent_build_preparation_report'): module.agent_build_compile(payload)


def test_compile_refuses_retransmitted_files_instead_of_selecting_a_fallback(compile_build, monkeypatch):
    module, _, payload, _ = compile_build
    payload['fixture_files'] = fixture_files()
    monkeypatch.setattr(module, 'full_cargo_cache', lambda p: pytest.fail('cache touched for unselected compile input'))
    with pytest.raises(RuntimeError, match='agent_build_compile_input'): module.agent_build_compile(payload)


@pytest.mark.parametrize(('key', 'value'), [('schema_version', True), ('generation', True),
    ('session_enabled', 0), ('full_runtime_qualified', 0), ('compatibility_qualified', 0)])
def test_preparation_report_rejects_boolean_integer_aliases(compile_build, monkeypatch, key, value):
    module, _, payload, _ = compile_build
    payload['agent_build_report'][key] = value
    monkeypatch.setattr(module, 'full_cargo_cache', lambda p: pytest.fail('cache touched for malformed report'))
    with pytest.raises(RuntimeError, match='agent_build_preparation_report'): module.agent_build_compile(payload)


def test_usage_counts_hardlinks_once_and_rejects_symlink(compile_build):
    module, work, _, _ = compile_build
    target = work/'full-target-1'
    path = target/'first'; path.write_bytes(b'x'*1024)
    os.link(path, target/'second')
    assert module.agent_build_usage()[0] == 1024
    (target/'outside').symlink_to(work)
    with pytest.raises(RuntimeError, match='agent_build_target_identity'): module.agent_build_usage()


def test_committed_fixture_has_only_the_selected_dependency(build):
    module, _, _, _ = build
    payload = {'fixture_files': {name: (BASE/'agentcheck'/('main.rs' if name == 'src/main.rs' else name)).read_text()
                                 for name in ('Cargo.toml', 'Cargo.lock', 'src/main.rs')}}
    assert set(module.agent_build_files(payload)) == set(FILES)-{'src/upstream_child_seccomp.rs', 'src/patched_child_seccomp.rs'}
