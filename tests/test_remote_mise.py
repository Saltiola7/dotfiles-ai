"""Global remote toolchain ownership stays separate from uv and project locks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest
from test_remote_personalisation import ROOT, foundation, render
from test_prefect_mcp_runtime import launcher, layout, fake_install


def test_remote_global_mise_declares_only_optional_pinned_python():
    path = 'private_dot_config/mise/config.toml.tmpl'
    disabled = tomllib.loads(render(path))
    enabled = tomllib.loads(render(path, options={'prefect_mcp': {'enabled': True}}))
    assert disabled['tools'] == {}
    assert enabled['tools'] == {'python': '3.13.18'}
    assert enabled['env']['UV_PYTHON_DOWNLOADS'] == 'never'
    assert enabled['settings']['python']['compile'] is False


def test_remote_global_mise_lock_matches_official_release_and_config():
    path = 'private_dot_config/mise/mise.lock.tmpl'
    assert 'tools' not in tomllib.loads(render(path))
    locked = tomllib.loads(render(path, options={'prefect_mcp': {'enabled': True}}))
    python = locked['tools']['python'][0]
    assert python['version'] == '3.13.18'
    assert python['backend'] == 'core:python'
    asset = python['platforms.linux-x64']
    assert asset['checksum'] == 'sha256:df15fe60d3ff55bf9dcf25824b5572756bb8816ff93865a273d3301d7066a8b7'
    assert '/20261026/cpython-3.13.18+20261026-x86_64-unknown-linux-gnu-' in asset['url']
    assert asset['provenance'] == 'github-attestations'


@pytest.mark.parametrize('remote', [False, True])
def test_global_mise_targets_are_remote_only(remote):
    data = tomllib.loads((ROOT / '.chezmoidata.toml').read_text())
    data['chezmoi'] = {'os': 'linux', 'arch': 'amd64'}
    data['dotfiles_ai']['remote_user_environment']['enabled'] = remote
    result = subprocess.run(['chezmoi', '-S', str(ROOT), '--config', '/dev/null',
        '--config-format', 'toml', '--override-data', json.dumps(data), 'managed'],
        text=True, capture_output=True, check=True)
    managed = set(result.stdout.splitlines())
    assert ('.config/mise/config.toml' in managed) is remote
    assert ('.config/mise/mise.lock' in managed) is remote
    assert ('.bashrc.d/00-dotfiles-ai-mise.sh' in managed) is remote


def test_uv_bootstrap_no_longer_requires_host_python_before_mise():
    bootstrap = render('run_after_install-02-remote-tools.sh.tmpl',
                       options={'prefect_mcp': {'enabled': True}})
    assert 'uv_version=' in bootstrap
    assert 'python find' not in bootstrap
    hook = render('run_after_install-03-remote-mise.sh.tmpl',
                  options={'prefect_mcp': {'enabled': True}})
    assert 'install --locked' in hook
    assert 'uv sync' not in hook and 'uv python install' not in hook
    assert 'python' in hook and '3.13.18' in hook


def test_remote_shims_reach_shell_and_prefect_install_paths():
    common = render('dot_common_profile.tmpl')
    installer = render('run_onchange_after_install-prefect-mcp.sh.tmpl',
                       options={'prefect_mcp': {'enabled': True}})
    for script in (common, installer):
        assert '$HOME/.local/share/mise/shims' in script
        assert 'UV_PYTHON_DOWNLOADS=never' in script
    assert '"$HOME/.local/bin/mise" activate bash' in render('dot_bashrc.d/00-dotfiles-ai-mise.sh.tmpl')
    assert 'mise/shims' not in render('dot_common_profile.tmpl', remote=False)


@pytest.mark.parametrize('status', [0, 37])
def test_mise_hook_uses_native_locked_installer_and_propagates_failure(tmp_path, status):
    home = tmp_path / 'home'
    binary = home / '.local/bin'
    config = home / '.config/mise'
    binary.mkdir(parents=True)
    config.mkdir(parents=True)
    (config / 'config.toml').write_text('[tools]\n')
    (config / 'mise.lock').write_text('lockfile_version = 3\n')
    log = tmp_path / 'calls.json'
    mise = binary / 'mise'
    mise.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$CALLS"\n' + f'exit {status}\n')
    mise.chmod(0o755)
    install_context(binary)
    script = render('run_after_install-03-remote-mise.sh.tmpl')
    result = subprocess.run(['/bin/bash'], input=script, text=True, capture_output=True,
        env={**os.environ, 'HOME': str(home), 'CALLS': str(log), 'PATH': '/usr/bin:/bin'})
    assert result.returncode == status
    assert 'install --locked' in log.read_text()
    assert str(home) in log.read_text()


def test_disabled_host_mise_hook_has_no_effects(tmp_path):
    script = render('run_after_install-03-remote-mise.sh.tmpl', remote=False)
    result = subprocess.run(['/bin/bash'], input=script, text=True, capture_output=True,
        env={'HOME': str(tmp_path), 'PATH': '/unavailable'})
    assert result.returncode == 0
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('fault', ['symlink', 'writable', 'hardlink'])
def test_mise_hook_refuses_unsafe_config_before_native_execution(tmp_path, fault):
    home = tmp_path / 'home'
    config = home / '.config/mise'
    binary = home / '.local/bin'
    config.mkdir(parents=True)
    binary.mkdir(parents=True)
    path = config / 'config.toml'
    path.write_text('[tools]\n')
    (config / 'mise.lock').write_text('lockfile_version = 3\n')
    if fault == 'symlink':
        original = tmp_path / 'outside.toml'
        path.rename(original)
        path.symlink_to(original)
    elif fault == 'writable':
        path.chmod(0o666)
    else:
        (config / 'linked.toml').hardlink_to(path)
    marker = tmp_path / 'executed'
    mise = binary / 'mise'
    mise.write_text('#!/bin/sh\ntouch "$MARKER"\n')
    mise.chmod(0o755)
    install_context(binary)
    result = subprocess.run(['/bin/bash'], input=render('run_after_install-03-remote-mise.sh.tmpl'),
        text=True, capture_output=True, env={**os.environ, 'HOME': str(home),
            'PATH': '/usr/bin:/bin', 'MARKER': str(marker)})
    assert result.returncode != 0
    assert 'unsafe' in result.stderr
    assert not marker.exists()


@pytest.mark.parametrize('version', ['3.13.18', '3.13.17'])
def test_enabled_mise_hook_requires_the_exact_python_pin(tmp_path, version):
    home = tmp_path / 'home'
    config = home / '.config/mise'
    binary = home / '.local/bin'
    config.mkdir(parents=True)
    binary.mkdir(parents=True)
    (home / '.local/share/mise/installs/python/3.13.18').mkdir(parents=True)
    (config / 'config.toml').write_text('[tools]\npython = "3.13.18"\n')
    (config / 'mise.lock').write_text('lockfile_version = 3\n')
    mise = binary / 'mise'
    mise.write_text('#!/bin/sh\nif [ "$3" = exec ]; then echo ' + version + '; fi\n')
    mise.chmod(0o755)
    install_context(binary)
    result = subprocess.run(['/bin/bash'], input=render('run_after_install-03-remote-mise.sh.tmpl',
        options={'prefect_mcp': {'enabled': True}}), text=True, capture_output=True,
        env={**os.environ, 'HOME': str(home), 'PATH': '/usr/bin:/bin'})
    assert result.returncode == (0 if version == '3.13.18' else 1)


@pytest.mark.parametrize('fault', ['', 'version', 'outside'])
def test_foundation_qualifies_mise_interpreter_path_and_version(tmp_path, monkeypatch, fault):
    import hashlib
    core = foundation(tmp_path, monkeypatch, '[data.dotfiles_ai.prefect_mcp]\nenabled = true\n')
    data = core.configuration()
    binary = core.HOME / '.local/bin'
    binary.mkdir(parents=True)
    for name, key in [('mise', 'mise_sha256'), ('gh', 'gh_binary_sha256'), ('uv', 'uv_binary_sha256')]:
        path = binary / name
        path.write_bytes(b'fixture')
        path.chmod(0o755)
        data['remote_user_environment'][key] = hashlib.sha256(path.read_bytes()).hexdigest()
    install_context(binary)
    install = core.HOME / '.local/share/mise/installs/python/3.13.18'
    interpreter = install / 'bin/python3.13'
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b'fixture-python')
    interpreter.chmod(0o755)
    selected = interpreter if fault != 'outside' else Path('/usr/bin/python3')
    def command(*args, **kwargs):
        if args[0] == str(binary / 'remote-mise'):
            assert args[:4] == (str(binary / 'remote-mise'), 'exec', '--', str(binary / 'uv'))
            assert '--no-python-downloads' in args
            return subprocess.CompletedProcess(args, 0, stdout=str(selected))
        assert args[0] == str(interpreter)
        return subprocess.CompletedProcess(args, 0, stdout='3.13.17' if fault == 'version' else '3.13.18')
    monkeypatch.setattr(core, 'command', command)
    if fault:
        with pytest.raises(RuntimeError, match='Python'):
            core.validate_tool_integrity(data)
    else:
        core.validate_tool_integrity(data)


def test_remote_python_pin_changes_adapter_generation_identity(launcher, layout):
    before = launcher.input_identity(layout.base)[0]
    (layout.base / '.python-version').write_text('3.13.18\n')
    assert launcher.input_identity(layout.base)[0] != before


def test_adding_remote_pin_migrates_without_deleting_old_generation(launcher, layout, fake_install, monkeypatch):
    launcher.install(layout)
    previous, _ = launcher.resolve_runtime(layout)
    (layout.base / '.python-version').write_text('3.13.18\n')
    selected = layout.home / '.local/share/mise/installs/python/3.13.18/bin/python3.13'
    selected.parent.mkdir(parents=True)
    selected.write_bytes(b'fixture-python')
    selected.chmod(0o755)
    import hashlib
    identity = {'path': str(selected), 'version': [3, 13, 18],
                'sha256': hashlib.sha256(selected.read_bytes()).hexdigest()}
    monkeypatch.setattr(launcher, 'python_identity', lambda _: identity)
    original = launcher.run_command
    def run(argv, **kwargs):
        result = original(argv, **kwargs)
        if argv[1:3] == ['python', 'find']:
            return str(selected).encode()
        if 'sync' in argv:
            python = Path(kwargs['cwd']) / '.venv/bin/python'
            python.unlink()
            python.symlink_to(selected)
        return result
    monkeypatch.setattr(launcher, 'run_command', run)
    launcher.install(layout)
    current, _ = launcher.resolve_runtime(layout)
    assert previous != current
    assert (previous / '.complete.json').exists()
    assert (current / '.python-version').read_text() == '3.13.18\n'
    assert json.loads((current / '.complete.json').read_text())['python']['version'] == [3, 13, 18]
    assert sum('sync' in call[0] for call in fake_install) == 2


def test_remote_generation_refuses_an_interpreter_with_the_wrong_patch(launcher, layout, fake_install):
    (layout.base / '.python-version').write_text('3.13.18\n')
    with pytest.raises(launcher.Unavailable, match='interpreter_pin_mismatch'):
        launcher.install(layout)


def install_context(binary):
    path = binary / 'remote-mise'
    path.write_bytes((ROOT / 'dot_local/bin/executable_remote-mise').read_bytes())
    path.chmod(0o755)


@pytest.mark.parametrize('status', [0, 23])
def test_optional_smoke_diagnostics_preserve_failure(tmp_path, status):
    smoke = (ROOT / 'tests/remote_user_environment_smoke.sh').read_text()
    diagnostic = smoke.split('# BEGIN optional-apply diagnostics\n', 1)[1].split(
        '# END optional-apply diagnostics', 1)[0]
    helper = tmp_path / 'foundation'
    helper.write_text('import subprocess\n'
        'def command(*args, **kwargs):\n'
        f'    return subprocess.run(["/bin/sh", "-c", "echo fixture-out; echo fixture-error >&2; exit {status}"],'
        ' check=True, text=True, capture_output=True)\n'
        'def main():\n'
        '    try: command()\n'
        '    except subprocess.CalledProcessError: raise SystemExit(1)\n')
    result = subprocess.run([sys.executable, '-', '0' * 40, str(helper)], input=diagnostic,
                            text=True, capture_output=True)
    assert result.returncode == (0 if status == 0 else 1)
    if status:
        assert 'fixture-out' in result.stderr
        assert 'fixture-error' in result.stderr
    else:
        assert result.stderr == ''


def test_optional_smoke_checks_python_in_user_shell_before_interference():
    smoke = (ROOT / 'tests/remote_user_environment_smoke.sh').read_text()
    assert 'command -v python3.13' in smoke
    assert '$(python3.13 --version)' in smoke
    assert 'Python 3.13.18' in smoke
    assert smoke.index('command -v python3.13') < smoke.index('# Deliberately invalid extra configs')


def normalization_script():
    hook = render('run_after_install-03-remote-mise.sh.tmpl',
                  options={'prefect_mcp': {'enabled': True}})
    return hook.split('# BEGIN Python install permissions\n', 1)[1].split(
        '# END Python install permissions', 1)[0]


def test_native_python_archive_permissions_are_hardened_without_byte_changes(tmp_path):
    home = tmp_path / 'home'
    install = home / '.local/share/mise/installs/python/3.13.18'
    (install / 'bin').mkdir(parents=True)
    (install / 'lib').mkdir()
    interpreter = install / 'bin/python3.13'
    interpreter.write_bytes(b'locked-interpreter')
    interpreter.chmod(0o775)
    library = install / 'lib/module.py'
    library.write_bytes(b'locked-library')
    library.chmod(0o664)
    (install / 'lib').chmod(0o775)
    outside = tmp_path / 'outside'
    outside.mkdir()
    external = outside / 'unchanged'
    external.write_bytes(b'outside-install')
    external.chmod(0o666)
    (install / 'bin/python3').symlink_to('python3.13')
    (install / 'linked-dir').symlink_to(outside, target_is_directory=True)
    (install / 'linked-file').symlink_to(external)
    for _ in range(2):
        subprocess.run([sys.executable, '-', str(home), str(install)], input=normalization_script(),
                       text=True, check=True)
    assert interpreter.stat().st_mode & 0o777 == 0o755
    assert library.stat().st_mode & 0o777 == 0o644
    assert (install / 'lib').stat().st_mode & 0o777 == 0o755
    assert interpreter.read_bytes() == b'locked-interpreter'
    assert library.read_bytes() == b'locked-library'
    assert external.stat().st_mode & 0o777 == 0o666
    assert (install / 'bin/python3').is_symlink()


@pytest.mark.parametrize('fault', ['symlink-parent', 'hardlink', 'special', 'wrong-root'])
def test_python_permission_normalization_refuses_unsafe_inputs(tmp_path, fault):
    home = tmp_path / 'home'
    install = home / '.local/share/mise/installs/python/3.13.18'
    install.mkdir(parents=True)
    marker = install / 'unchanged'
    marker.write_bytes(b'preserve')
    marker.chmod(0o664)
    if fault == 'symlink-parent':
        actual = tmp_path / 'actual'
        install.parent.rename(actual)
        install.parent.symlink_to(actual, target_is_directory=True)
    elif fault == 'hardlink':
        (install / 'alias').hardlink_to(marker)
    elif fault == 'special':
        os.mkfifo(install / 'pipe')
    else:
        install = install.parent
    result = subprocess.run([sys.executable, '-', str(home), str(install)],
                            input=normalization_script(), text=True, capture_output=True)
    assert result.returncode != 0
    assert marker.stat().st_mode & 0o777 == 0o664


@pytest.mark.parametrize('fault', ['home-symlink', 'ancestor-replacement', 'owner', 'privilege',
                                  'writable-ancestor', 'entry-bound', 'walk-error', 'file-replacement'])
def test_python_permission_normalization_security_guards(tmp_path, fault):
    home = tmp_path / 'home'
    install = home / '.local/share/mise/installs/python/3.13.18'
    install.mkdir(parents=True)
    marker = install / 'unchanged'
    marker.write_bytes(b'preserve')
    marker.chmod(0o664)
    script = normalization_script()
    prelude = ''
    expected_mode = 0o664
    if fault == 'home-symlink':
        alias = tmp_path / 'alias'
        alias.symlink_to(tmp_path, target_is_directory=True)
        home = alias / 'home'
        install = home / '.local/share/mise/installs/python/3.13.18'
    elif fault == 'ancestor-replacement':
        moved = tmp_path / 'original-python'
        outside = tmp_path / 'outside'
        outside.mkdir()
        prelude = ('import os\noriginal_open = os.open\n'
            'def injected_open(path, flags, *args, **kwargs):\n'
            '    if path == "python" and "dir_fd" in kwargs:\n'
            f'        os.rename({str(install.parent)!r}, {str(moved)!r})\n'
            f'        os.symlink({str(outside)!r}, {str(install.parent)!r})\n'
            '    return original_open(path, flags, *args, **kwargs)\n'
            'os.open = injected_open\n')
        marker = moved / '3.13.18/unchanged'
    elif fault == 'owner':
        prelude = ('import os\noriginal_stat = os.stat\n'
            'def injected_stat(path, *args, **kwargs):\n'
            '    result = original_stat(path, *args, **kwargs)\n'
            '    if path == "unchanged":\n'
            '        values = list(result); values[4] = os.getuid() + 1\n'
            '        return os.stat_result(values)\n'
            '    return result\n'
            'os.stat = injected_stat\n')
    elif fault == 'privilege':
        marker.chmod(0o4664)
        expected_mode = 0o4664
    elif fault == 'writable-ancestor':
        (home / '.local').chmod(0o775)
    elif fault == 'entry-bound':
        script = script.replace('count > 50000', 'count > 0')
    elif fault == 'walk-error':
        prelude = ('import os\n'
            'def injected_walk(*args, **kwargs):\n'
            '    kwargs["onerror"](PermissionError("fixture traversal failure"))\n'
            'os.fwalk = injected_walk\n')
    else:
        alias = tmp_path / 'replacement-alias'
        prelude = ('import os\noriginal_open = os.open\n'
            'def injected_open(path, flags, *args, **kwargs):\n'
            '    if path == "unchanged":\n'
            f'        os.link({str(marker)!r}, {str(alias)!r})\n'
            '    return original_open(path, flags, *args, **kwargs)\n'
            'os.open = injected_open\n')
    result = subprocess.run([sys.executable, '-', str(home), str(install)],
                            input=prelude + script, text=True, capture_output=True)
    assert result.returncode != 0
    assert marker.stat().st_mode & 0o7777 == expected_mode
    assert marker.read_bytes() == b'preserve'


@pytest.mark.parametrize('operation', ['install', 'exec'])
def test_remote_context_isolates_project_fragments_and_ambient_overrides(tmp_path, operation):
    home = tmp_path / 'home'
    config = home / '.config/mise'
    binary = home / '.local/bin'
    config.mkdir(parents=True)
    binary.mkdir(parents=True)
    (config / 'config.toml').write_text('[tools]\n')
    (config / 'mise.lock').write_text('lockfile_version = 3\n')
    (config / 'conf.d').mkdir()
    for path in (home / 'mise.toml', config / 'config.local.toml', config / 'config.override.toml',
                 config / 'conf.d/extra.toml', home / '.miserc.toml', home / '.miserc.local.toml'):
        path.write_text('invalid = [\n')
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'mise.toml').write_text('[tools]\npython = "3.13.17"\n')
    output = tmp_path / 'observed.json'
    mise = binary / 'mise'
    mise.write_text(f'#!{sys.executable}\nimport json,os,sys\n'
        f'open({str(output)!r},"w").write(json.dumps({{"argv":sys.argv[1:],"cwd":os.getcwd(),'
        '"env":{k:v for k,v in os.environ.items() if k.startswith(("MISE_","UV_"))}}))\n')
    mise.chmod(0o755)
    arguments = ['install', '--locked'] if operation == 'install' else ['exec', '--', 'python', '--version']
    subprocess.run([sys.executable, str(ROOT / 'dot_local/bin/executable_remote-mise'), *arguments],
        cwd=project, env={**os.environ, 'HOME': str(home), 'MISE_ENV': 'unreviewed',
            'MISE_PYTHON_COMPILE': 'true', 'UV_PYTHON': '/unreviewed/python'}, check=True)
    observed = json.loads(output.read_text())
    assert observed['cwd'] == str(home)
    assert observed['argv'] == ['--cd', str(home), *arguments]
    for key in ('MISE_GLOBAL_CONFIG_FILE', 'MISE_SYSTEM_CONFIG_FILE', 'MISE_OVERRIDE_CONFIG_FILENAMES'):
        assert observed['env'][key] == str(config / 'config.toml')
    assert 'MISE_ENV' not in observed['env']
    assert 'MISE_PYTHON_COMPILE' not in observed['env']
    assert 'UV_PYTHON' not in observed['env']
    assert observed['env']['UV_PYTHON_DOWNLOADS'] == 'never'
    assert observed['env']['UV_PYTHON_PREFERENCE'] == 'only-system'
    assert observed['env']['MISE_CEILING_PATHS'] == str(home)
    assert observed['env']['MISE_SYSTEM_CONFIG_DIR'] == str(config)
    if operation == 'exec':
        assert observed['env']['MISE_EXEC_AUTO_INSTALL'] == '0'
        assert observed['env']['MISE_AUTO_INSTALL'] == '0'


@pytest.mark.parametrize('name', ['miserc.toml', 'miserc.local.toml'])
@pytest.mark.parametrize('content', ['env = ["unreviewed"]\n', 'invalid = [\n'])
def test_global_rc_is_refused_before_native_loading(tmp_path, name, content):
    home = tmp_path / 'home'
    config = home / '.config/mise'
    binary = home / '.local/bin'
    config.mkdir(parents=True)
    binary.mkdir(parents=True)
    (config / 'config.toml').write_text('[tools]\n')
    (config / 'mise.lock').write_text('lockfile_version = 3\n')
    (config / name).write_text(content)
    sentinel = tmp_path / 'native-ran'
    mise = binary / 'mise'
    mise.write_text(f'#!/bin/sh\ntouch "{sentinel}"\n')
    mise.chmod(0o755)
    result = subprocess.run([sys.executable, str(ROOT / 'dot_local/bin/executable_remote-mise'), 'install', '--locked'],
        env={**os.environ, 'HOME': str(home)}, capture_output=True, text=True)
    assert result.returncode != 0
    assert not sentinel.exists()
    assert (config / name).read_text() == content
