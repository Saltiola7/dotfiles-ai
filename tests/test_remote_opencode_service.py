"""Boot service owns the native shared process, not a second watchdog."""
import configparser
import os
import subprocess
import json
import tomllib
import importlib.util
import ast

import pytest
from test_remote_personalisation import ROOT, render


def test_remote_unit_uses_native_foreground_loopback_service():
    unit = configparser.ConfigParser(interpolation=None, strict=False)
    unit.read(ROOT / 'private_dot_config/systemd/user/opencode-shared.service')
    assert unit['Install']['WantedBy'] == 'default.target'
    assert unit['Service']['ExecStart'] == '%h/.local/bin/opencode serve --service --hostname 127.0.0.1 --port 0'
    assert unit['Service']['Restart'] == 'on-failure'
    assert 'service start' not in unit['Service']['ExecStart']


@pytest.mark.parametrize('state', ['unit-active', 'unit-unhealthy', 'native-active', 'stopped',
                                  'stopped-success', 'start-fails'])
def test_remote_service_reapply_preserves_healthy_processes(tmp_path, state):
    home = tmp_path / 'home'
    binary = home / '.local/bin'
    binary.mkdir(parents=True)
    log = tmp_path / 'calls'
    started = tmp_path / 'started'
    systemctl = binary / 'systemctl'
    systemctl.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$CALLS"\n'
        'case "$2" in\n'
        'is-active) [ "$STATE" = unit-active ] || [ "$STATE" = unit-unhealthy ];;\n'
        'start) [ "$STATE" != start-fails ] || exit 23; [ "$STATE" = unit-unhealthy ] || touch "$STARTED";;\n'
        '*) exit 0;;\nesac\n')
    systemctl.chmod(0o755)
    opencode = binary / 'opencode'
    opencode.write_text('#!/bin/sh\nif [ "$*" = "service status" ]; then\n'
        '  if [ "$STATE" = stopped-success ] && [ ! -f "$STARTED" ]; then echo stopped; exit 0; fi\n'
        '  [ "$STATE" = native-active ] || [ "$STATE" = unit-active ] || '
        '[ "$STATE" = unit-unhealthy ] || [ -f "$STARTED" ] || exit 1\n'
        '  echo http://127.0.0.1:12345\n'
        'elif [ "$*" = "api --server http://127.0.0.1:12345 get /api/info" ]; then\n'
        '  [ "$STATE" != unit-unhealthy ] || exit 1\n'
        '  [ "$OPENCODE_PASSWORD" = fixture-service-password ] || exit 99\n'
        '  echo \'{"pid":12345,"version":"2.0.99"}\'\n'
        'else exit 99; fi\n')
    opencode.chmod(0o755)
    registration = home / '.local/state/opencode/service.json'
    registration.parent.mkdir(parents=True)
    registration.write_text(json.dumps({'pid': 12345, 'url': 'http://127.0.0.1:12345',
                                        'password': 'fixture-service-password'}))
    registration.chmod(0o600)
    sleep = binary / 'sleep'
    sleep.write_text('#!/bin/sh\nexit 0\n')
    sleep.chmod(0o755)
    result = subprocess.run(['/bin/bash'], text=True, capture_output=True,
        input=render('run_after_install-04-remote-opencode-service.sh.tmpl'),
        env={**os.environ, 'HOME': str(home), 'PATH': str(binary) + ':/usr/bin:/bin',
             'STATE': state, 'CALLS': str(log), 'STARTED': str(started)})
    expected = 23 if state == 'start-fails' else 75 if state == 'unit-unhealthy' else 0
    assert result.returncode == expected, result.stderr
    calls = log.read_text().splitlines()
    assert '--user daemon-reload' in calls
    assert '--user enable opencode-shared.service' in calls
    assert not any('restart' in call or 'stop ' in call for call in calls)
    assert ('--user start opencode-shared.service' in calls) is (
        state in {'stopped', 'stopped-success', 'start-fails', 'unit-unhealthy'})


def test_nonremote_service_hook_has_no_effects(tmp_path):
    result = subprocess.run(['/bin/bash'], text=True, capture_output=True,
        input=render('run_after_install-04-remote-opencode-service.sh.tmpl', remote=False),
        env={'HOME': str(tmp_path), 'PATH': '/unavailable'})
    assert result.returncode == 0
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('remote', [False, True])
def test_remote_unit_and_hook_target_selection(remote):
    data = tomllib.loads((ROOT / '.chezmoidata.toml').read_text())
    data['chezmoi'] = {'os': 'linux', 'arch': 'amd64'}
    data['dotfiles_ai']['remote_user_environment']['enabled'] = remote
    result = subprocess.run(['chezmoi', '-S', str(ROOT), '--config', '/dev/null',
        '--config-format', 'toml', '--override-data', json.dumps(data), 'managed'],
        text=True, capture_output=True, check=True)
    targets = set(result.stdout.splitlines())
    assert ('.config/systemd/user/opencode-shared.service' in targets) is remote
    assert ('install-04-remote-opencode-service.sh' in targets) is remote


def test_service_contract_reserves_lingering_and_rollout_for_host_owner():
    feature = (ROOT / 'docs/specs/dotfiles_ai_distribution/features/remote-opencode-service.md').read_text()
    assert 'Fork A owns host user declaration' in feature
    assert 'Ordinary UBI smoke uses' in feature
    assert 'stubbed pass cannot replace' in feature
    assert 'No automatic service restart' in feature
    assert '## Visual Evidence' in feature and '**Text Equivalent:**' in feature
    assert 'OpenCode after remote boot (RRW-F01)' in (ROOT / 'docs/UPDATES.md').read_text()


def test_boot_proof_is_native_isolated_and_ubi10():
    directory = ROOT / 'tests/remote_opencode_systemd'
    container = (directory / 'Containerfile').read_text()
    assert 'FROM registry.access.redhat.com/ubi10/ubi' in container
    assert 'systemd' in container and 'python3 ' in container
    assert container.index('systemctl unmask systemd-logind.service') < container.index(
        'systemctl add-wants multi-user.target systemd-logind.service dbus.socket')
    assert '\nCOPY . ' not in container
    workflow = (ROOT / '.github/workflows/remote-opencode-service.yml').read_text()
    assert 'persist-credentials: false' in workflow
    assert 'contents: read' in workflow
    assert 'pull_request_target' not in workflow
    assert '--cgroupns=private' in workflow
    assert 'docker restart' in workflow
    assert '/sys/fs/cgroup:/sys/fs/cgroup' not in workflow
    boot = (directory / 'boot-smoke.sh').read_text()
    assert 'loginctl enable-linger fixture' in boot
    assert 'setpriv --reuid' in boot
    assert 'Sessions --value' in boot
    assert 'opencode service start' not in boot


def native_fixture():
    path = ROOT / 'tests/remote_opencode_systemd/verify-user.py'
    spec = importlib.util.spec_from_file_location('f01_fixture', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_boot_fixture_preserves_failure_without_exposing_child_output(tmp_path, monkeypatch):
    fixture = native_fixture()
    monkeypatch.setattr(fixture, 'HOME', tmp_path)
    with pytest.raises(fixture.QualificationFailure) as error:
        fixture.run('/bin/sh', '-c', 'echo fixture-private-output; echo fixture-private-error >&2; exit 23')
    assert error.value.status == 23
    assert 'fixture-private' not in str(error.value)
    assert fixture.failure_reason(error.value) == 'native-tool-exit-23'
    assert 'fixture-private' not in fixture.failure_reason(RuntimeError('fixture-private-error'))


def test_boot_invariant_labels_are_source_literals():
    tree = ast.parse((ROOT / 'tests/remote_opencode_systemd/verify-user.py').read_text())
    for call in ast.walk(tree):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'require':
            assert isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str)


def test_boot_readiness_retains_only_sanitized_last_reason(monkeypatch):
    fixture = native_fixture()
    ticks = iter([0, 0, 61])
    monkeypatch.setattr(fixture.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(fixture.time, 'sleep', lambda _: None)
    def inspect():
        raise fixture.InvariantFailure('service registration mismatch')
    monkeypatch.setattr(fixture, 'inspect', inspect)
    with pytest.raises(fixture.InvariantFailure) as error:
        fixture.ready()
    assert fixture.failure_reason(error.value) == 'bounded readiness: service registration mismatch'


def test_boot_readiness_retries_native_command_failures(monkeypatch):
    fixture = native_fixture()
    calls = []
    def inspect():
        calls.append(None)
        if len(calls) == 1:
            raise fixture.QualificationFailure(1)
        return 12345, 'http://127.0.0.1:12345'
    monkeypatch.setattr(fixture, 'inspect', inspect)
    monkeypatch.setattr(fixture.time, 'sleep', lambda _: None)
    assert fixture.ready() == (12345, 'http://127.0.0.1:12345')
    assert len(calls) == 2


@pytest.mark.parametrize('state,inode,address,port,expected', [
    ('01', '42', '0100007F', '3039', True),
    ('0A', '42', '0100007F', '3039', False),
    ('01', '43', '0100007F', '3039', False),
    ('01', '42', '00000000', '3039', False),
    ('01', '42', '0100007F', '3038', False),
])
def test_tui_witness_requires_client_owned_established_service_socket(
        tmp_path, monkeypatch, state, inode, address, port, expected):
    fixture = native_fixture()
    descriptors = tmp_path / '12345/fd'
    descriptors.mkdir(parents=True)
    (descriptors / '7').symlink_to('socket:[42]')
    net = tmp_path / 'net'
    net.mkdir()
    (net / 'tcp').write_text('header\n' +
        f'0: 0100007F:C000 {address}:{port} {state} 0:0 00:0 0 1000 0 {inode}\n')
    (net / 'tcp6').write_text('header\n')
    monkeypatch.setattr(fixture, 'Path', lambda value: tmp_path / value.removeprefix('/proc/'))
    assert fixture.connected(12345, 12345) is expected
