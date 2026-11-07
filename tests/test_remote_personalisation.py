"""RRW-007A remote flags and shared shell/tool ownership, offline unless CI smoke."""
import importlib.machinery
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tomllib

import pytest

ROOT = Path(__file__).parents[1]


def render(path, *, remote=True, options=None):
    data = tomllib.loads((ROOT / '.chezmoidata.toml').read_text())
    data['chezmoi'] = {'os': 'linux', 'arch': 'amd64'}
    data['dotfiles_ai']['remote_user_environment']['enabled'] = remote
    for name, values in (options or {}).items():
        data['dotfiles_ai'].setdefault(name, {}).update(values)
    return subprocess.run(['chezmoi', '-S', str(ROOT), '--config', '/dev/null',
        '--config-format', 'toml', '--override-data', json.dumps(data), 'execute-template'],
        input=(ROOT / path).read_text(), text=True, capture_output=True, check=True).stdout


def foundation(tmp_path, monkeypatch, config=''):
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.delenv('DOTFILES_AI_SOURCE', raising=False)
    monkeypatch.delenv('DOTFILES_AI_CONFIG', raising=False)
    loader = importlib.machinery.SourceFileLoader('personal_foundation',
        str(ROOT / 'dot_local/bin/executable_remote-user-foundation'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.SOURCE.mkdir(parents=True)
    (module.SOURCE / '.chezmoidata.toml').write_bytes((ROOT / '.chezmoidata.toml').read_bytes())
    module.CONFIG.parent.mkdir(parents=True)
    module.CONFIG.write_text(config)
    module.CONFIG.chmod(0o600)
    return module


@pytest.mark.parametrize('flag', ['onepassword', 'prefect_mcp', 'pm_kernel', 'jfrog_cli', 'history_projection'])
def test_foundation_accepts_supported_user_flags(tmp_path, monkeypatch, flag):
    core = foundation(tmp_path, monkeypatch, f'[data.dotfiles_ai.{flag}]\nenabled = true\n')
    assert core.configuration()[flag]['enabled'] is True


@pytest.mark.parametrize('flag', ['knowledge_store', 'hermes', 'rnd'])
def test_foundation_rejects_unavailable_remote_features(tmp_path, monkeypatch, flag):
    core = foundation(tmp_path, monkeypatch, f'[data.dotfiles_ai.{flag}]\nenabled = true\n')
    with pytest.raises(RuntimeError, match='unavailable'):
        core.configuration()


def test_remote_tools_are_pinned_and_checksum_verified():
    script = render('run_after_install-02-remote-tools.sh.tmpl')
    assert 'latest' not in script
    for needle in ('sha256sum -c', 'mise_version="2026.11.2"',
                   'gh_version="2.103.3"', 'b768184570b12536'):
        assert needle in script
    subprocess.run(['bash', '-n'], input=script, text=True, check=True)
    disabled = render('run_after_install-02-remote-tools.sh.tmpl', remote=False)
    result = subprocess.run(['/bin/bash'], input=disabled, text=True,
        env={'PATH': '/unavailable'}, capture_output=True)
    assert result.returncode == 0


def test_remote_archive_extraction_preserves_installing_user_ownership():
    script = render('run_after_install-02-remote-tools.sh.tmpl',
                    options={'prefect_mcp': {'enabled': True}})
    extracts = [line.strip() for line in script.splitlines() if line.strip().startswith('tar ')]
    assert len(extracts) == 2
    assert all('--no-same-owner' in line for line in extracts)


@pytest.mark.parametrize('fault', ['', 'mise', 'gh', 'uv'])
def test_remote_installer_checksums_and_no_download_reapply(tmp_path, fault):
    home = tmp_path / 'home'
    binary = home / '.local/bin'
    binary.mkdir(parents=True)
    tools = {'mise': b'#!/bin/sh\necho mise-2026.11.2\n',
             'gh': b'#!/bin/sh\necho gh-2.103.3\n',
             'uv': b'#!/bin/sh\necho uv-0.13.6\n'}
    for name in tools:
        path = binary / name
        path.write_bytes(b'#!/bin/sh\necho previous\n')
        path.chmod(0o755)
    archive = tmp_path / 'gh.tar.gz'
    with tarfile.open(archive, 'w:gz') as stream:
        item = tarfile.TarInfo('gh_2.103.3_linux_amd64/bin/gh')
        item.size = len(tools['gh'])
        item.mode = 0o755
        item.uid = 12345
        item.gid = 12345
        item.uname = 'upstream-runner'
        item.gname = 'upstream-runner'
        stream.addfile(item, io.BytesIO(tools['gh']))
    mise = tmp_path / 'mise'
    mise.write_bytes(tools['mise'])
    uv_archive = tmp_path / 'uv.tar.gz'
    with tarfile.open(uv_archive, 'w:gz') as stream:
        item = tarfile.TarInfo('uv-x86_64-unknown-linux-musl/uv')
        item.size = len(tools['uv'])
        item.mode = 0o755
        item.uid = 12345
        item.gid = 12345
        item.uname = 'upstream-runner'
        item.gname = 'upstream-runner'
        stream.addfile(item, io.BytesIO(tools['uv']))
    options = {'remote_user_environment': {
        'mise_sha256': hashlib.sha256(tools['mise']).hexdigest(),
        'gh_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'gh_binary_sha256': hashlib.sha256(tools['gh']).hexdigest(),
        'uv_archive_sha256': hashlib.sha256(uv_archive.read_bytes()).hexdigest(),
        'uv_binary_sha256': hashlib.sha256(tools['uv']).hexdigest(),
    }, 'prefect_mcp': {'enabled': True}}
    script = tmp_path / 'install.sh'
    script.write_text(render('run_after_install-02-remote-tools.sh.tmpl', options=options))
    fake = tmp_path / 'fake'
    fake.mkdir()
    uname = fake / 'uname'
    uname.write_text('#!/bin/sh\nif [ "$1" = -s ]; then echo Linux; else echo x86_64; fi\n')
    uname.chmod(0o755)
    calls = tmp_path / 'curl-calls'
    curl = fake / 'curl'
    curl.write_text(f'#!{sys.executable}\nimport pathlib, shutil, sys\n'
        f'pathlib.Path({str(calls)!r}).touch()\n'
        'url = next(a for a in sys.argv if a.startswith("https://"))\n'
        'output = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])\n'
        'name = "mise" if "/jdx/mise/" in url else "uv" if "/astral-sh/uv/" in url else "gh"\n'
        f'fault = {fault!r}\n'
        'if name == fault: output.write_bytes(b"wrong checksum")\n'
        f'else: shutil.copyfile({{"mise": {str(mise)!r}, "gh": {str(archive)!r}, "uv": {str(uv_archive)!r}}}[name], output)\n')
    curl.chmod(0o755)
    checksum = fake / 'sha256sum'
    checksum.write_text(f'#!{sys.executable}\nimport hashlib, pathlib, sys\n'
        'expected, name = sys.stdin.read().strip().split(None, 1)\n'
        'try: observed = hashlib.sha256(pathlib.Path(name.strip()).read_bytes()).hexdigest()\n'
        'except OSError: raise SystemExit(1)\n'
        'raise SystemExit(0 if observed == expected else 1)\n')
    checksum.chmod(0o755)
    environment = {**os.environ, 'HOME': str(home), 'PATH': f'{fake}:/usr/bin:/bin'}
    before = (binary / fault).read_bytes() if fault in tools else None
    result = subprocess.run(['/bin/bash', str(script)], env=environment, capture_output=True)
    if fault:
        assert result.returncode != 0
        assert (binary / fault).read_bytes() == before
    else:
        assert result.returncode == 0, result.stderr
        for name, content in tools.items():
            assert (binary / name).read_bytes() == content
            assert (binary / name).stat().st_uid == os.getuid()
        calls.unlink()
        repeated = subprocess.run(['/bin/bash', str(script)], env=environment, capture_output=True)
        assert repeated.returncode == 0, repeated.stderr
        assert not calls.exists()
        for name, content in tools.items():
            (binary / name).write_bytes(b'#!/bin/sh\nexit 42\n')
            repaired = subprocess.run(['/bin/bash', str(script)], env=environment, capture_output=True)
            assert repaired.returncode == 0, repaired.stderr
            assert (binary / name).read_bytes() == content


def test_remote_herdr_skill_and_integration_are_selected():
    script = render('run_onchange_after_install-herdr-skill.sh.tmpl')
    assert 'herdr integration install opencode' in script or '"$HERDR" integration install opencode' in script
    assert 'exit 0' not in script.split('HERDR=', 1)[0]
    config = tomllib.loads(render('private_dot_config/herdr/config.toml.tmpl'))
    assert config['session']['resume_agents_on_restore'] is True


@pytest.mark.parametrize('kind', ['binary_symlink', 'binary_directory', 'parent_symlink'])
def test_remote_installer_refuses_unsafe_targets(tmp_path, kind):
    home = tmp_path / 'home'
    binary = home / '.local/bin'
    binary.mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'mise'
    sentinel.write_text('preserve')
    if kind == 'binary_symlink':
        (binary / 'mise').symlink_to(sentinel)
    elif kind == 'binary_directory':
        (binary / 'mise').mkdir()
    else:
        binary.rmdir()
        binary.parent.rmdir()
        (home / '.local').symlink_to(outside, target_is_directory=True)
    fake = tmp_path / 'fake'
    fake.mkdir()
    (fake / 'uname').write_text('#!/bin/sh\nif [ "$1" = -s ]; then echo Linux; else echo x86_64; fi\n')
    (fake / 'uname').chmod(0o755)
    result = subprocess.run(['/bin/bash'],
        input=render('run_after_install-02-remote-tools.sh.tmpl'), text=True,
        env={**os.environ, 'HOME': str(home), 'PATH': f'{fake}:/usr/bin:/bin'},
        capture_output=True)
    assert result.returncode != 0
    assert 'unsafe' in result.stderr
    assert sentinel.read_text() == 'preserve'


def test_prefect_dependency_keeps_existing_runtime_owner():
    script = render('run_after_install-02-remote-tools.sh.tmpl',
                    options={'prefect_mcp': {'enabled': True}})
    assert 'uv_version="0.13.6"' in script
    assert 'python find' not in script
    assert 'install --locked' in render('run_after_install-03-remote-mise.sh.tmpl',
                                      options={'prefect_mcp': {'enabled': True}})
    assert 'uv sync' not in script
    disabled = render('run_after_install-02-remote-tools.sh.tmpl')
    assert 'uv_version=' not in disabled


def test_supported_flag_handoff_is_machine_readable():
    result = subprocess.run([str(ROOT / 'dot_local/bin/executable_remote-user-foundation'),
        'supported-flags'], text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == {
        'onepassword': 'dotfiles_ai.onepassword.enabled',
        'prefect_mcp': 'dotfiles_ai.prefect_mcp.enabled',
        'pm_kernel': 'dotfiles_ai.pm_kernel.enabled',
        'jfrog_cli': 'dotfiles_ai.jfrog_cli.enabled',
        'history_projection': 'dotfiles_ai.history_projection.enabled',
        'opencode.vertex_project': 'dotfiles_ai.opencode.vertex_project',
    }


@pytest.mark.parametrize('value', ['"true"', '1', '[]'])
def test_flag_types_are_not_silently_coerced(tmp_path, monkeypatch, value):
    core = foundation(tmp_path, monkeypatch, f'[data.dotfiles_ai.prefect_mcp]\nenabled = {value}\n')
    with pytest.raises(RuntimeError, match='flag is invalid'):
        core.configuration()


def test_local_data_cannot_override_release_checksums(tmp_path, monkeypatch):
    core = foundation(tmp_path, monkeypatch,
        '[data.dotfiles_ai.remote_user_environment]\nmise_sha256 = "unverified"\n')
    with pytest.raises(RuntimeError, match='pins cannot be overridden'):
        core.configuration()


@pytest.mark.parametrize('config', [
    'data = false\n',
    '[data.dotfiles_ai]\nopencode = false\n',
    '[data.dotfiles_ai]\nworkspaces = false\n',
    '[data.dotfiles_ai.workspaces]\nschema_version = true\n',
    '[data.dotfiles_ai.workspaces]\nroot = 1\n',
    '[data.dotfiles_ai.workspaces]\nroot = "relative/worktrees"\n',
    '[data.dotfiles_ai.workspaces]\nroot = "/outside/worktrees"\n',
])
def test_malformed_configuration_is_rejected_before_apply(tmp_path, monkeypatch, config):
    core = foundation(tmp_path, monkeypatch, config)
    with pytest.raises(RuntimeError, match='foundation'):
        core.configuration()


def test_worktree_root_precondition_preserves_existing_policy(tmp_path, monkeypatch):
    core = foundation(tmp_path, monkeypatch)
    root = core.HOME / '.local/state/custom-worktrees'
    core.CONFIG.write_text('[data.dotfiles_ai.workspaces]\nschema_version = 1\n'
                           f'root = "{root}"\n')
    assert core.configuration()['workspaces']['root'] == str(root)
    assert not root.exists()
    root.parent.mkdir(parents=True)
    root.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(RuntimeError, match='foundation path is unsafe'):
        core.configuration()


def test_apply_records_failure_until_tool_bytes_are_verified(tmp_path, monkeypatch):
    core = foundation(tmp_path, monkeypatch)
    data = core.configuration()
    binaries = core.HOME / '.local/bin'
    binaries.mkdir(parents=True)
    content = b'#!/bin/sh\nexit 0\n'
    for key in ('mise_sha256', 'gh_binary_sha256'):
        data['remote_user_environment'][key] = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(core, 'configuration', lambda: data)
    revision = 'a' * 40
    monkeypatch.setattr(core, 'git', lambda *args, **kwargs:
        subprocess.CompletedProcess(args, 0, stdout=revision if args == ('rev-parse', revision) else ''))
    monkeypatch.setattr(core, 'command', lambda *args, **kwargs:
        subprocess.CompletedProcess(args, 0, stdout=''))
    with pytest.raises(SystemExit, match='foundation apply failed'):
        core.apply(revision)
    assert core.read_state()['state'] == 'failed_retryable'
    for name in ('mise', 'gh'):
        (binaries / name).write_bytes(content)
        (binaries / name).chmod(0o755)
    core.apply(revision)
    assert core.read_state()['state'] == 'foundation_ready'
    assert core.read_state()['attempt'] == 2


@pytest.mark.parametrize('flag', ['knowledge_store', 'hermes', 'rnd'])
def test_direct_render_rejects_unavailable_features_before_apply(flag):
    with pytest.raises(subprocess.CalledProcessError):
        render('.chezmoiignore', options={flag: {'enabled': True}})


def test_prefect_remote_managed_closure_contains_runtime_and_config():
    data = tomllib.loads((ROOT / '.chezmoidata.toml').read_text())
    data['chezmoi'] = {'os': 'linux', 'arch': 'amd64'}
    data['dotfiles_ai']['remote_user_environment']['enabled'] = True
    data['dotfiles_ai']['prefect_mcp']['enabled'] = True
    result = subprocess.run(['chezmoi', '-S', str(ROOT), '--config', '/dev/null',
        '--config-format', 'toml', '--override-data', json.dumps(data), 'managed'],
        text=True, capture_output=True, check=True)
    managed = set(result.stdout.splitlines())
    assert '.config/dotfiles-ai/prefect-mcp.toml' in managed
    assert '.config/dotfiles-ai/runtime/prefect-mcp/pyproject.toml' in managed
    assert '.config/dotfiles-ai/runtime/prefect-mcp/uv.lock' in managed
    assert '.config/dotfiles-ai/runtime/prefect-mcp/server.py' in managed
    assert '.config/dotfiles-ai/knowledge/embedding-space.json' not in managed
    assert not any(path.startswith('.config/dotfiles-ai/runtime/dvc/') for path in managed)


@pytest.mark.parametrize('tool', ['mise', 'gh'])
def test_integrity_detects_remote_tool_tampering(tmp_path, monkeypatch, tool):
    core = foundation(tmp_path, monkeypatch)
    data = core.configuration()
    binaries = core.HOME / '.local/bin'
    binaries.mkdir(parents=True)
    for name in ('codex', 'gcloud', 'op', 'opencode', 'remote-agent-readiness', 'herdr', 'wt', 'mise', 'gh'):
        path = binaries / name
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o755)
    data['remote_user_environment']['mise_sha256'] = hashlib.sha256((binaries / 'mise').read_bytes()).hexdigest()
    data['remote_user_environment']['gh_binary_sha256'] = hashlib.sha256((binaries / 'gh').read_bytes()).hexdigest()
    monkeypatch.setattr(core, 'configuration', lambda: data)
    revision = 'a' * 40
    monkeypatch.setattr(core, 'git', lambda *args, **kwargs:
        subprocess.CompletedProcess(args, 0, stdout=revision if args == ('rev-parse', 'HEAD') else ''))
    config = core.HOME / '.config/opencode/opencode.json'
    config.parent.mkdir(parents=True)
    config.write_text('{}')
    def command(*args, **kwargs):
        output = ' R install-02-remote-tools.sh\n R install-03-remote-mise.sh\n R install-04-remote-opencode-service.sh\n R update-codex.sh\n R update-opencode.sh\n'
        if '--version' in args:
            output = {'codex': 'codex-cli 0.151.0', 'herdr': 'herdr 0.9.5',
                      'wt': 'wt v0.80.0', 'opencode': 'opencode v2.2.5'}[Path(args[0]).name]
        return subprocess.CompletedProcess(args, 0, stdout=output)
    monkeypatch.setattr(core, 'command', command)
    state = {'state': 'foundation_ready', 'revision': revision,
             'desired_revision': revision, 'managed_targets': []}
    assert core.validate_integrity(state) == binaries / 'remote-agent-readiness'
    (binaries / tool).write_text('#!/bin/sh\nexit 42\n')
    with pytest.raises(RuntimeError, match='remote tool integrity changed'):
        core.validate_integrity(state)


def test_shell_dropins_do_not_transfer_bashrc_ownership(tmp_path):
    script = (ROOT / 'dot_bashrc').read_text()
    home = tmp_path / 'home'
    snippets = home / '.bashrc.d'
    snippets.mkdir(parents=True)
    (snippets / '10-custom.sh').write_text('export RRW_DROPIN=loaded\n')
    result = subprocess.run(['bash', '-ic', 'source "$1"; printf "%s" "$RRW_DROPIN"',
        'bash', str(ROOT / 'dot_bashrc')], env={**os.environ, 'HOME': str(home),
        'PATH': '/usr/bin:/bin'}, text=True, capture_output=True)
    assert result.returncode == 0
    assert result.stdout.endswith('loaded')
    assert '.bashrc.d' in script
