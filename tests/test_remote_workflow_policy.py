"""Remote policy rendering and original F03 storage identity constraints."""
import json
import subprocess
import tomllib

import pytest
from test_remote_personalisation import ROOT
from test_worktrunk_native_policy import policy, storage_home


def test_remote_profile_manages_policy_but_never_activation():
    data = {'chezmoi': {'os': 'linux', 'arch': 'amd64'},
            'dotfiles_ai': {'remote_user_environment': {'enabled': True}}}
    result = subprocess.run(['chezmoi', '-S', str(ROOT), '--config', '/dev/null',
        '--config-format', 'toml', '--override-data', json.dumps(data), 'managed'],
        text=True, capture_output=True, check=True)
    managed = set(result.stdout.splitlines())
    assert '.config/dotfiles-ai/workflow-policy.json' in managed
    assert '.config/dotfiles-ai/workflow-policy.activation.json' not in managed


@pytest.mark.parametrize('uuid', ['linux-volume', None])
def test_remote_home_root_uses_findmnt_identity(policy, storage_home, monkeypatch, uuid):
    root = storage_home / '.local/state/worktrees'
    root.mkdir(parents=True)
    value = policy.resolve({'schema_version': 1, 'root': str(root)}, storage_home)
    value['source_commit'] = 'a' * 40
    value['policy_digest'] = policy.digest(value)
    monkeypatch.setattr(policy.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.80.0')
    calls = []
    def run(*args, **kwargs):
        calls.append(args)
        assert args == ('findmnt', '--json', '--output', 'UUID,TARGET', '--target', str(root))
        return json.dumps({'filesystems': [{'uuid': uuid, 'target': '/'}]}).encode()
    monkeypatch.setattr(policy, 'run', run)
    saved = policy.snapshot(value, storage_home)
    selected = next(item for item in saved['roots'] if item['canonical_path'] == str(root))
    assert selected == {'canonical_path': str(root), 'kind': 'owned_home',
                        'filesystem_uuid': uuid, 'mountpoint': '/'}
    assert calls
    policy.verify_snapshot(value, saved, storage_home)
    selected['mountpoint'] = '/changed'
    with pytest.raises(ValueError):
        policy.verify_snapshot(value, saved, storage_home)


def test_missing_linux_uuid_still_refuses_external_root(policy, storage_home, monkeypatch):
    root = storage_home.parent / 'external'
    root.mkdir()
    value = policy.resolve({'schema_version': 1, 'root': str(root)}, storage_home)
    value['source_commit'] = 'a' * 40
    value['policy_digest'] = policy.digest(value)
    monkeypatch.setattr(policy.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.80.0')
    monkeypatch.setattr(policy, 'run', lambda *args, **kwargs:
        json.dumps({'filesystems': [{'uuid': None, 'target': '/'}]}).encode())
    with pytest.raises(ValueError):
        policy.snapshot(value, storage_home)


@pytest.mark.parametrize('raw', [b'{', b'{"filesystems":[]}',
    b'{"filesystems":[{"uuid":"","target":"/"}]}',
    b'{"filesystems":[{"uuid":null,"target":"relative"}]}'])
def test_remote_home_does_not_hide_findmnt_failure(policy, storage_home, monkeypatch, raw):
    root = storage_home / '.local/state/worktrees'
    root.mkdir(parents=True)
    value = policy.resolve({'schema_version': 1, 'root': str(root)}, storage_home)
    value.update(source_commit='a' * 40)
    value['policy_digest'] = policy.digest(value)
    monkeypatch.setattr(policy.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.80.0')
    monkeypatch.setattr(policy, 'run', lambda *args, **kwargs: raw)
    with pytest.raises(ValueError):
        policy.snapshot(value, storage_home)


def test_remote_activation_instructions_and_smoke_preserve_owner_boundary():
    instructions = (ROOT / 'docs/specs/dotfiles_ai_distribution/features/remote-worktrunk-policy.md').read_text()
    assert 'RRW-007E successor' in instructions
    assert 'Other configured roots retain mandatory UUID identity' in instructions
    smoke = (ROOT / 'tests/remote_user_environment_smoke.sh').read_text()
    assert 'remote Worktrunk default apply activation qualification passed' in smoke
    assert 'install -m 0600 "$proposal"' not in smoke
    workflow = (ROOT / '.github/workflows/rhel-remote-user.yml').read_text()
    assert 'util-linux' in workflow
    assert '"tests/test_remote_workflow_policy.py"' in workflow
    example = (ROOT / 'config.remote-user.example.toml').read_text()
    assert 'Existing/stale activation still requires owner review' in example
    assert tomllib.loads(example)['data']['dotfiles_ai']['workspaces'] == {
        'schema_version': 1, 'root': '/home/you/.local/state/worktrees'}
    assert 'cat >>"$HOME/.config/dotfiles-ai/chezmoi.toml"' not in smoke
