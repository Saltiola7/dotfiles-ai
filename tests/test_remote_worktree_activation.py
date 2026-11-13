"""INT-074: only explicit default-home apply may initialize activation."""
import json
import ast
import os
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_worktrunk_native_policy import policy, storage_home
from test_remote_personalisation import ROOT, render, foundation


@pytest.fixture
def activation(policy, storage_home, monkeypatch):
    home = storage_home
    root = home / '.local/state/worktrees'
    root.mkdir(parents=True)
    config = home / '.config'
    (config / 'dotfiles-ai').mkdir(parents=True)
    value = policy.resolve({'schema_version': 1, 'root': str(root)}, home)
    value.update(source_commit='a' * 40)
    value['policy_digest'] = policy.digest(value)
    monkeypatch.setattr(policy.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.80.0')
    monkeypatch.setattr(policy, 'mount_identity', lambda *a, **kw: ('fixture-home', '/'))
    return home, config, value


def test_initial_apply_publishes_private_single_link_and_preserves_reapply(policy, activation):
    home, config, value = activation
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    policy.initialize_default_home(value, home, config)
    info = target.lstat()
    assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
    assert info.st_uid == os.getuid()
    before = target.read_bytes()
    assert json.loads(before) == policy.snapshot(value, home)
    policy.initialize_default_home(value, home, config)
    assert target.read_bytes() == before
    assert target.stat().st_ino == info.st_ino


@pytest.mark.parametrize('kind', ['symlink', 'dangling', 'hardlink', 'malformed', 'public', 'stale'])
def test_existing_activation_is_never_repaired_or_overwritten(policy, activation, kind):
    home, config, value = activation
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    other = config / 'dotfiles-ai/retained'
    other.write_text('retained')
    if kind in {'symlink', 'dangling'}:
        target.symlink_to(other if kind == 'symlink' else home / 'missing')
    else:
        saved = policy.snapshot(value, home)
        saved['worktrunk_version'] = 'wt v0.0.0' if kind == 'stale' else saved['worktrunk_version']
        target.write_text('{' if kind == 'malformed' else json.dumps(saved))
        target.chmod(0o644 if kind == 'public' else 0o600)
        if kind == 'hardlink':
            os.link(target, home / 'retained-hardlink')
    before = target.lstat()
    content = os.readlink(target) if stat.S_ISLNK(before.st_mode) else target.read_bytes()
    with pytest.raises((ValueError, OSError)):
        policy.initialize_default_home(value, home, config)
    after = target.lstat()
    # A read may update atime. Preserve every identity/write-related field,
    # including nanosecond timestamps, without treating access as a repair.
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
              'st_size', 'st_mtime_ns', 'st_ctime_ns')
    assert {name: getattr(after, name) for name in fields} == {
        name: getattr(before, name) for name in fields}
    assert (os.readlink(target) if stat.S_ISLNK(after.st_mode) else target.read_bytes()) == content
    assert other.read_text() == 'retained'


@pytest.mark.parametrize('change', ['root', 'mount', 'platform', 'version', 'policy', 'unproven_source'])
def test_unapproved_location_or_changed_binding_refuses(policy, activation, monkeypatch, change):
    home, config, value = activation
    if change in {'version', 'policy', 'unproven_source'}:
        policy.initialize_default_home(value, home, config)
    if change == 'root':
        value['root'] = str(home / 'Worktrees')
        value['policy_digest'] = policy.digest(value)
    elif change == 'mount':
        monkeypatch.setattr(policy, 'mount_identity', lambda path, **kw:
            ('other', str(path)) if path != home else ('fixture-home', '/'))
    elif change == 'platform':
        monkeypatch.setattr(policy.platform, 'system', lambda: 'Darwin')
    elif change == 'version':
        monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.81.0')
    elif change == 'policy':
        value['naming']['task'] = 'changed'
        value['policy_digest'] = policy.digest(value)
    else:
        # A legacy full hash without its deployed policy preimage is not proof.
        target = config / 'dotfiles-ai/workflow-policy.activation.json'
        saved = policy.snapshot(value, home)
        saved.pop('semantic_digest', None)
        saved.update(schema_version=1, policy_digest=value['policy_digest'])
        target.write_text(json.dumps(saved))
        target.chmod(0o600)
        value['source_commit'] = 'b' * 40
        value['policy_digest'] = policy.digest(value)
    with pytest.raises(ValueError):
        policy.initialize_default_home(value, home, config)


def test_simultaneous_initializers_retain_one_complete_snapshot(policy, activation):
    home, config, value = activation
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(lambda _: policy.initialize_default_home(value, home, config), range(8)))
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    assert json.loads(target.read_bytes()) == policy.snapshot(value, home)
    assert target.stat().st_nlink == 1
    assert not list(target.parent.glob('.activation-*.tmp'))


def test_snapshot_never_creates_activation(policy, activation):
    home, config, value = activation
    before = set(config.rglob('*'))
    policy.snapshot(value, home)
    assert set(config.rglob('*')) == before


def test_unavailable_identity_never_publishes(policy, activation, monkeypatch):
    home, config, value = activation
    def unavailable(*args, **kwargs):
        raise ValueError('unavailable')
    monkeypatch.setattr(policy, 'mount_identity', unavailable)
    with pytest.raises(ValueError):
        policy.initialize_default_home(value, home, config)
    assert not os.path.lexists(config / 'dotfiles-ai/workflow-policy.activation.json')


def test_disabled_hook_has_no_effects(tmp_path):
    result = subprocess.run(['/bin/bash'], text=True, capture_output=True,
        input=render('run_after_zz-remote-worktree-activation.sh.tmpl', remote=False),
        env={'HOME': str(tmp_path), 'PATH': '/unavailable'}, timeout=5)
    assert result.returncode == 0
    assert not list(tmp_path.iterdir())
    assert 'initialize-default-home' in render('run_after_zz-remote-worktree-activation.sh.tmpl')


def test_activation_runs_after_installers_and_updaters():
    def target(path):
        return path.name.removeprefix('run_').removeprefix('onchange_').removeprefix('after_').removesuffix('.tmpl')
    hook = ROOT / 'run_after_zz-remote-worktree-activation.sh.tmpl'
    activation_name = target(hook)
    for path in ROOT.glob('run_*after_*.sh.tmpl'):
        if path != hook:
            assert target(path) < activation_name, path.name


def test_ubi_qualifies_automatic_default_not_manual_activation():
    smoke = (ROOT / 'tests/remote_user_environment_smoke.sh').read_text()
    assert 'remote Worktrunk default apply activation qualification passed' in smoke
    assert 'install -m 0600 "$proposal"' not in smoke
    assert 'review_fixture_generation' not in smoke
    assert 'assert_activation_retained' in smoke


def test_fresh_foundation_provisions_default_cache_before_snapshot(tmp_path, monkeypatch):
    core = foundation(tmp_path, monkeypatch)
    cache = core.HOME / '.cache/dotfiles-ai/dvc'
    assert not cache.exists()
    root = core.HOME / '.local/state/worktrees'
    core.provision_workspace_directories({'workspaces': {'schema_version': 1, 'root': str(root)}})
    assert cache.is_dir() and root.is_dir()
    assert stat.S_IMODE(cache.stat().st_mode) == 0o700


def test_publication_failure_retains_no_partial_activation(policy, activation, monkeypatch):
    home, config, value = activation
    def fail_link(*args, **kwargs):
        raise OSError('fixture publication failure')
    monkeypatch.setattr(policy.os, 'link', fail_link)
    with pytest.raises(OSError):
        policy.initialize_default_home(value, home, config)
    assert not os.path.lexists(config / 'dotfiles-ai/workflow-policy.activation.json')
    assert not list((config / 'dotfiles-ai').glob('.activation-*.tmp'))


def test_no_replace_publication_preserves_noncooperating_winner(policy, activation, monkeypatch):
    home, config, value = activation
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    original = policy.os.link
    def competing_link(*args, **kwargs):
        target.write_text('retained winner')
        target.chmod(0o600)
        return original(*args, **kwargs)
    monkeypatch.setattr(policy.os, 'link', competing_link)
    with pytest.raises(FileExistsError):
        policy.initialize_default_home(value, home, config)
    assert target.read_text() == 'retained winner'
    assert target.stat().st_nlink == 1
    assert not list(target.parent.glob('.activation-*.tmp'))


def test_temporary_name_collision_never_unlinks_unowned_entry(policy, activation, monkeypatch):
    home, config, value = activation
    collision = config / 'dotfiles-ai/.activation-collision.tmp'
    collision.write_text('unowned retained entry')
    before = collision.lstat()
    monkeypatch.setattr(policy.secrets, 'token_hex', lambda _: 'collision')
    with pytest.raises(FileExistsError):
        policy.initialize_default_home(value, home, config)
    assert collision.read_text() == 'unowned retained entry'
    assert collision.lstat() == before


def test_activation_contract_and_updates_cover_writing_boundary():
    relative = 'docs/specs/dotfiles_ai_distribution/features/remote-worktree-activation.md'
    feature = (ROOT / relative).read_text()
    for text in ('initialize-default-home', 'semantic identity', 'never write',
                 '## Visual Evidence', '**Text Equivalent:**', 'mode 0600', 'single-link'):
        assert text in feature
    for path in ('docs/UPDATES.md', 'docs/specs/dotfiles_ai_distribution/README.md',
                 'docs/specs/dotfiles_ai_distribution/CHANGELOG.md'):
        assert 'activation' in (ROOT / path).read_text().lower()


def test_activation_progress_labels_are_literal_not_private_values():
    tree = ast.parse((ROOT / 'dot_local/bin/executable_workflow-policy').read_text())
    initialize = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == 'initialize_default_home')
    labels = []
    for node in ast.walk(initialize):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
            assert len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
            labels.append(node.args[0].value)
    assert 'workflow-policy: activation stage home-identity' in labels
    assert 'workflow-policy: activation stage publish' in labels


def legacy_snapshot(policy, value, home):
    saved = policy.snapshot(value, home)
    saved.pop('semantic_digest', None)
    saved.update(schema_version=1, policy_digest=value['policy_digest'])
    return saved


def test_new_activation_uses_semantics_not_source_commit(policy, activation):
    home, config, value = activation
    policy.initialize_default_home(value, home, config)
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    before, inode = target.read_bytes(), target.stat().st_ino
    saved = json.loads(before)
    assert saved['schema_version'] == 2
    assert saved['semantic_digest'] == policy.semantic_digest(value)
    assert 'policy_digest' not in saved
    value['source_commit'] = 'b' * 40
    value['policy_digest'] = policy.digest(value)
    policy.initialize_default_home(value, home, config)
    assert target.read_bytes() == before and target.stat().st_ino == inode


def test_legacy_file_survives_deployed_bridge_and_multiple_bumps(policy, activation, monkeypatch):
    from test_remote_workflow_policy import render_policy
    home, config, value = activation
    path = config / 'dotfiles-ai/workflow-policy.json'
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    target.write_text(json.dumps(legacy_snapshot(policy, value, home)))
    target.chmod(0o600)
    before, inode = target.read_bytes(), target.stat().st_ino
    for commit in ('b' * 40, 'c' * 40, 'a' * 40):
        value = render_policy(policy, home, monkeypatch, policy.previous_policy(config, home),
                              options={'schema_version': 1, 'root': str(home / '.local/state/worktrees')},
                              commit=commit)
        path.write_text(json.dumps(value))
        policy.initialize_default_home(value, home, config)
        assert target.read_bytes() == before and target.stat().st_ino == inode


@pytest.mark.parametrize('change', ['schema_bool', 'extra', 'root_extra', 'root_kind',
                                  'uuid_bool', 'version_type', 'digest_type'])
@pytest.mark.parametrize('legacy', [False, True])
def test_snapshot_rejects_noncanonical_shapes(policy, activation, change, legacy):
    home, _, value = activation
    saved = legacy_snapshot(policy, value, home) if legacy else policy.snapshot(value, home)
    if change == 'schema_bool':
        saved['schema_version'] = True
    elif change == 'extra':
        saved['extra'] = None
    elif change == 'root_extra':
        saved['roots'][0]['extra'] = None
    elif change == 'root_kind':
        saved['roots'][0]['kind'] = 1
    elif change == 'uuid_bool':
        saved['roots'][0]['filesystem_uuid'] = False
    elif change == 'version_type':
        saved['worktrunk_version'] = 80
    else:
        saved['policy_digest' if legacy else 'semantic_digest'] = True
    with pytest.raises(ValueError):
        policy.verify_snapshot(value, saved, home)
