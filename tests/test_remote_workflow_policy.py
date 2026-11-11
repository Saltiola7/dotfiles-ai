"""Remote policy rendering and original F03 storage identity constraints."""
import json
import copy
import os
import subprocess
import tomllib

import pytest
from test_remote_personalisation import ROOT
from test_worktrunk_native_policy import policy, storage_home


def render_policy(policy, home, monkeypatch, previous, *, options=None, commit='b' * 40):
    """Synthetic clean source: exercise the real renderer, not native commands."""
    from pathlib import Path
    helper = Path(policy.__file__).read_bytes()
    def run(*args, **kwargs):
        if args[1] == 'status':
            return b''
        if args[1] == 'rev-parse':
            return commit.encode()
        assert args[1] == 'show'
        return helper
    monkeypatch.setattr(policy, 'run', run)
    return policy.render(home, home, options, {}, previous_policy=previous)['policy']


def test_legacy_bridge_is_bounded_transitive_and_fixed_point(policy, storage_home, monkeypatch):
    old = policy.resolve(None, storage_home)
    old['source_commit'] = 'a' * 40
    old['policy_digest'] = policy.digest(old)
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.80.0')
    saved = policy.snapshot(old, storage_home)
    saved.pop('semantic_digest', None)
    saved.update(schema_version=1, policy_digest=old['policy_digest'])
    previous = old
    for commit in ('b' * 40, 'c' * 40, 'a' * 40):
        fresh = render_policy(policy, storage_home, monkeypatch, previous, commit=commit)
        assert fresh['activation_binding'] == {
            'schema_version': 1, 'semantic_digest': policy.semantic_digest(old),
            'legacy_policy_digest': old['policy_digest']}
        assert fresh['policy_digest'] == policy.digest(fresh)
        assert fresh['source_commit'] == commit
        policy.verify_snapshot(fresh, saved, storage_home)
        assert render_policy(policy, storage_home, monkeypatch, fresh, commit=commit) == fresh
        previous = fresh


@pytest.mark.parametrize('change', ['root', 'naming', 'preservation', 'delivery', 'feedback'])
@pytest.mark.parametrize('upgraded', [False, True])
def test_effective_changes_drop_legacy_anchor(policy, storage_home, monkeypatch, change, upgraded):
    options = {'schema_version': 1}
    old = policy.resolve(options, storage_home)
    old.update(source_commit='a' * 40)
    old['policy_digest'] = policy.digest(old)
    if change == 'root':
        root = storage_home / 'other'
        root.mkdir()
        options['root'] = str(root)
    elif change == 'naming':
        options['naming'] = {'task': 'other'}
    else:
        # Consent is nested in exact repository overrides, not a global fallback.
        repository = storage_home.parent / 'repository'
        repository.mkdir()
        key, before, after = {'preservation': ('automatic_remove', False, True),
                              'delivery': ('remote', 'origin', 'other'),
                              'feedback': ('destination', 'fixture/old', 'fixture/new')}[change]
        old['repositories'] = [{'repository': str(repository), change: {'schema_version': 1, key: before}}]
        options['repositories'] = [{'repository': str(repository), change: {'schema_version': 1, key: after}}]
        old['policy_digest'] = policy.digest(old)
        monkeypatch.setattr(policy, 'repository', lambda path: (path / '.git', [path], 'fixture'))
    previous = old
    if upgraded:
        previous = render_policy(policy, storage_home, monkeypatch, old, options=policy.semantic(old))
        assert previous['activation_binding']['legacy_policy_digest'] == old['policy_digest']
    fresh = render_policy(policy, storage_home, monkeypatch, previous, options=options)
    assert 'legacy_policy_digest' not in fresh['activation_binding']
    assert policy.semantic_digest(fresh) != policy.semantic_digest(old)
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.80.0')
    monkeypatch.setattr(policy, 'mount_identity', lambda *a, **kw: ('fixture', '/'))
    saved = policy.snapshot(old, storage_home)
    saved.pop('semantic_digest')
    saved.update(schema_version=1, policy_digest=old['policy_digest'])
    with pytest.raises(ValueError):
        policy.verify_snapshot(fresh, saved, storage_home)


@pytest.mark.parametrize('binding', [None, {}, {'schema_version': True},
    {'schema_version': 2, 'semantic_digest': 'a' * 64},
    {'schema_version': 1, 'semantic_digest': True},
    {'schema_version': 1, 'semantic_digest': 'a' * 64},
    {'schema_version': 1, 'semantic_digest': 'a' * 64, 'legacy_policy_digest': []},
    {'schema_version': 1, 'semantic_digest': 'a' * 64, 'extra': 1}])
def test_binding_is_validated_even_with_recomputed_full_digest(policy, storage_home, binding):
    value = policy.resolve(None, storage_home)
    value.update(source_commit='a' * 40, activation_binding=copy.deepcopy(binding))
    if isinstance(binding, dict) and ('legacy_policy_digest' in binding or 'extra' in binding):
        value['activation_binding']['semantic_digest'] = policy.semantic_digest(value)
    value['policy_digest'] = policy.digest(value)
    with pytest.raises(ValueError):
        policy.validate_document(value, storage_home)


def test_absent_preimage_cannot_infer_legacy_anchor(policy, storage_home, monkeypatch):
    fresh = render_policy(policy, storage_home, monkeypatch, None)
    assert set(fresh['activation_binding']) == {'schema_version', 'semantic_digest'}
    assert render_policy(policy, storage_home, monkeypatch, fresh) == fresh


@pytest.mark.parametrize('kind', ['malformed', 'duplicate', 'public', 'symlink', 'dangling', 'hardlink', 'oversize',
                                  'integrity', 'normalized'])
def test_prior_policy_read_fails_closed(policy, storage_home, kind):
    config = storage_home / 'custom-config'
    directory = config / 'dotfiles-ai'
    directory.mkdir(parents=True)
    path = directory / 'workflow-policy.json'
    if kind in {'symlink', 'dangling'}:
        other = directory / 'other'
        if kind == 'symlink':
            other.write_text('{}')
        path.symlink_to(other)
    else:
        path.write_text('{"schema_version":1,"schema_version":1}' if kind == 'duplicate'
                        else 'x' * (256 * 1024 + 1) if kind == 'oversize' else '{')
        if kind in {'integrity', 'normalized'}:
            value = policy.resolve(None, storage_home)
            value.update(source_commit='a' * 40)
            value['policy_digest'] = policy.digest(value)
            value['root'] += '/'
            if kind == 'normalized':
                value['policy_digest'] = policy.digest(value)
            path.write_text(json.dumps(value))
        path.chmod(0o644 if kind == 'public' else 0o600)
        if kind == 'hardlink':
            os.link(path, directory / 'other')
    with pytest.raises((ValueError, OSError)):
        policy.previous_policy(config, storage_home)


def test_binding_metadata_and_source_remain_in_full_integrity_digest(policy, storage_home, monkeypatch):
    value = render_policy(policy, storage_home, monkeypatch, None)
    original = value['policy_digest']
    value['source_commit'] = 'c' * 40
    assert policy.digest(value) != original
    with pytest.raises(ValueError):
        policy.validate_document(value, storage_home)
    value['policy_digest'] = policy.digest(value)
    value['activation_binding']['legacy_policy_digest'] = 'd' * 64
    with pytest.raises(ValueError):
        policy.validate_document(value, storage_home)


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
