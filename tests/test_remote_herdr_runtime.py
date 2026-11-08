"""RRW-007F selection and foundation boundaries; no live runtime access."""
import hashlib
import json
from pathlib import Path
import subprocess
import runpy
import sys
import tomllib

import pytest
from test_remote_personalisation import ROOT, foundation, render


@pytest.mark.parametrize('runtime', ['tui', 'herdr-core'])
def test_explicit_remote_selection_gates_native_tui_resume(runtime):
    data = tomllib.loads(render('private_dot_config/herdr/config.toml.tmpl', options={'herdr': {'runtime': runtime}}))
    assert data['session']['resume_agents_on_restore'] is (runtime == 'tui')


def test_unknown_selection_refuses_render_and_foundation(tmp_path, monkeypatch):
    with pytest.raises(subprocess.CalledProcessError):
        render('private_dot_config/herdr/config.toml.tmpl', options={'herdr': {'runtime': 'unknown'}})
    core = foundation(tmp_path, monkeypatch, '[data.dotfiles_ai.herdr]\nruntime="unknown"\n')
    with pytest.raises(RuntimeError):
        core.configuration()


def test_core_pin_is_reviewed_source_not_local_override(tmp_path, monkeypatch):
    core = foundation(tmp_path, monkeypatch, '[data.dotfiles_ai.herdr_core]\nversion="99.0.0"\n')
    with pytest.raises(RuntimeError):
        core.configuration()
    pins = tomllib.loads((ROOT / '.chezmoidata.toml').read_text())['dotfiles_ai']['herdr_core']
    assert pins['version'] == '0.1.18'
    assert pins['archive_sha256'] == '5b2f97cb4b2a9d7a6b2cc5942628203ed9fbb7cc0c2b4b09ad8a6f5648e246b7'
    assert pins['binary_sha256'] == 'baa9d208d6400556a6e379152455fe1301e0e1acdbc114ff60b79d64425179cf'


def test_core_installer_hook_is_remote_only(tmp_path):
    path = 'run_onchange_after_install-00z-remote-herdr-core.sh.tmpl'
    result = subprocess.run(['/bin/bash'], input=render(path, remote=False), text=True,
        capture_output=True, env={'HOME': str(tmp_path), 'PATH': '/unavailable'}, timeout=5)
    assert result.returncode == 0 and not list(tmp_path.iterdir())
    assert 'remote-herdr-core" install' in render(path)


def test_core_runtime_changes_do_not_modify_bootstrap():
    assert hashlib.sha256((ROOT / 'dot_local/bin/executable_remote-user-bootstrap').read_bytes()).hexdigest() == (
        '89da48232d9352a2eee2dd953fa29d42b7e358a4c2490a59e45cee899d4af666')


def test_foundation_integrity_checks_core_without_executing_drift(tmp_path, monkeypatch):
    core = foundation(tmp_path, monkeypatch)
    binary = core.HOME / '.local/bin/herdr-core'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'controlled pinned payload; never execute')
    binary.chmod(0o755)
    data = {'herdr_core': {'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}}
    core.validate_tool_integrity(data)
    binary.write_bytes(b'owner or app changed binary')
    with pytest.raises(RuntimeError):
        core.validate_tool_integrity(data)
    assert binary.read_bytes() == b'owner or app changed binary'


@pytest.mark.parametrize('operation', [[], ['--capture'], ['--watch'], ['--pace-start', 'must-not-run']])
def test_core_selection_disables_legacy_restore_before_runtime_access(tmp_path, monkeypatch, operation):
    config = tmp_path / '.config/herdr/config.toml'
    config.parent.mkdir(parents=True)
    config.write_text('[session]\nresume_agents_on_restore=false\n')
    config.chmod(0o600)
    monkeypatch.setenv('HOME', str(tmp_path))
    path = ROOT / 'dot_local/bin/executable_herdr-opencode-restore'
    script = runpy.run_path(str(path))
    monkeypatch.setattr(sys, 'argv', [str(path), *operation])
    assert script['main']() == (78 if operation[:1] == ['--pace-start'] else 0)


def test_runtime_units_preserve_native_core_and_shared_backend_ownership():
    service = render('private_dot_config/systemd/user/remote-herdr-restore.service.tmpl')
    timer = render('private_dot_config/systemd/user/remote-herdr-restore.timer.tmpl')
    tui = render('private_dot_config/systemd/user/remote-herdr-tui.service.tmpl')
    assert 'ExecStart=%h/.local/bin/remote-herdr restore' in service
    assert 'OnBootSec=' in timer and 'OnUnitInactiveSec=' in timer
    assert 'ExecStart=%h/.local/bin/remote-herdr exec-tui' in tui
    assert '[Install]' not in tui and 'Restart=' not in tui
    assert 'ExecStop=' not in service and 'ExecStop=' not in tui
    assert 'herdr-core serve' not in service + timer + tui
    pins = json.loads(render('private_dot_config/dotfiles-ai/herdr-runtime.json.tmpl'))
    assert pins['tui_version'] == '0.9.5' and len(pins['tui_sha256']) == 64
    assert pins['core_version'] == '0.1.18' and len(pins['core_sha256']) == 64


def test_runtime_activation_is_remote_only_and_does_not_restart(tmp_path):
    path = 'run_after_install-05-remote-herdr-runtime.sh.tmpl'
    result = subprocess.run(['/bin/bash'], input=render(path, remote=False), text=True,
        capture_output=True, env={'HOME': str(tmp_path), 'PATH': '/unavailable'}, timeout=5)
    assert result.returncode == 0
    script = render(path)
    assert 'enable --now remote-herdr-restore.timer' in script
    commands = '\n'.join(line for line in script.splitlines() if not line.lstrip().startswith('#'))
    assert ' restart ' not in commands and ' stop ' not in commands


@pytest.mark.parametrize('remote', [True, False])
def test_effective_managed_files_include_pins_only_for_remote(remote):
    data = {'chezmoi': {'os': 'linux', 'arch': 'amd64'}, 'dotfiles_ai': {
        'remote_user_environment': {'enabled': remote},
        'linux_workstation': {'enabled': not remote},
        'herdr': {'host_enabled': False, 'launchagent': False}}}
    result = subprocess.run(['chezmoi', '-S', str(ROOT), '--config', '/dev/null',
        '--config-format', 'toml', '--override-data', json.dumps(data), 'managed'],
        capture_output=True, text=True, check=True)
    managed = set(result.stdout.splitlines())
    for path in ('.config/dotfiles-ai/herdr-core.json', '.config/dotfiles-ai/herdr-runtime.json',
                 '.local/bin/remote-herdr', '.local/bin/remote-herdr-core',
                 '.local/share/dotfiles-ai/remote-herdr/controller.py',
                 '.config/systemd/user/remote-herdr-restore.timer'):
        assert (path in managed) is remote
