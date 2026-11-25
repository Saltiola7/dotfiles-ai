"""INT-074: only explicit default-home apply may initialize activation."""
import json
import ast
import os
import shutil
import stat
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_worktrunk_native_policy import generation_source, git, policy, render_generation, storage_home
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


WORKSTATION_EXAMPLES = ('config.omarchy.example.toml', 'config.omarchy-try.example.toml')
POLICY_DOCUMENT = '.config/dotfiles-ai/workflow-policy.json'
ACTIVATION_HOOK = 'zz-remote-worktree-activation.sh'
ACTIVATION_FILE = '.config/dotfiles-ai/workflow-policy.activation.json'
HELPER = '"$HOME/.local/bin/workflow-policy" '
# System, remote-user flag, workstation flag, arguments the hook hands the helper.
FLAG_TABLE = [
    ('linux', False, False, None),
    ('linux', False, True, 'initialize-default-home --default-home-root-only'),
    ('linux', True, False, 'initialize-default-home'),
    ('linux', True, True, 'initialize-default-home'),
    ('darwin', False, True, None),
    ('darwin', True, False, 'initialize-default-home'),
]


def chezmoi_data(system, remote, workstation, example=None):
    data = tomllib.loads((ROOT / '.chezmoidata.toml').read_text())
    data['chezmoi'] = {'os': system, 'arch': 'amd64'}
    data['dotfiles_ai']['remote_user_environment']['enabled'] = remote
    data['dotfiles_ai']['linux_workstation']['enabled'] = workstation
    if example is not None:
        data['dotfiles_ai'].update(tomllib.loads((ROOT / example).read_text())['data']['dotfiles_ai'])
    return data


def chezmoi_output(data, *arguments, template=None):
    return subprocess.run(['chezmoi', '-S', str(ROOT), '--config', '/dev/null',
        '--config-format', 'toml', '--override-data', json.dumps(data), *arguments],
        input=template, text=True, capture_output=True, check=True).stdout


def activation_hook(data, home, calls):
    """Run the rendered hook against a helper that only records its arguments."""
    helper = home / '.local/bin/workflow-policy'
    helper.parent.mkdir(parents=True)
    helper.write_text('#!/bin/sh\nprintf \'%s\\n\' "$*" >"$CALLS"\n')
    helper.chmod(0o755)
    script = chezmoi_output(data, 'execute-template',
        template=(ROOT / 'run_after_zz-remote-worktree-activation.sh.tmpl').read_text())
    subprocess.run(['bash', '-n'], input=script, text=True, check=True)
    return subprocess.run(['/bin/bash'], input=script, text=True, capture_output=True, timeout=5,
                          env={'HOME': str(home), 'PATH': '/unavailable', 'CALLS': str(calls)})


@pytest.mark.parametrize('system,remote,workstation,arguments', FLAG_TABLE)
def test_policy_document_and_activation_hook_are_reached_together(tmp_path, system, remote,
                                                                   workstation, arguments):
    data = chezmoi_data(system, remote, workstation)
    managed = set(chezmoi_output(data, 'managed').splitlines())
    # Linux ignores the document without either flag; macOS never did, and the
    # workstation flag changes nothing there.
    assert (POLICY_DOCUMENT in managed) is (arguments is not None or system == 'darwin')
    assert (ACTIVATION_HOOK in managed) is (arguments is not None)
    assert ACTIVATION_FILE not in managed
    calls = tmp_path / 'calls'
    result = activation_hook(data, tmp_path / 'home', calls)
    assert result.returncode == 0, result.stderr
    if arguments is None:
        assert not calls.exists()
    else:
        # The remote user environment is unchanged; only a workstation asks
        # the helper to leave another root alone.
        assert calls.read_text().splitlines() == [arguments]


def test_workstation_flag_unlocks_no_remote_user_target():
    remote_only = {'.config/dotfiles-ai/herdr-core.json', '.config/dotfiles-ai/herdr-runtime.json',
                   '.local/bin/remote-herdr', '.local/bin/remote-user-foundation',
                   'install-02-remote-tools.sh', 'install-03-remote-mise.sh',
                   'install-04-remote-opencode-service.sh', '.config/mise/config.toml'}
    remote = set(chezmoi_output(chezmoi_data('linux', True, False), 'managed').splitlines())
    workstation = set(chezmoi_output(chezmoi_data('linux', False, True), 'managed').splitlines())
    assert remote_only <= remote
    assert remote_only.isdisjoint(workstation)


def test_rendered_hook_text():
    remote = ('#!/bin/bash\nset -euo pipefail\n'
              'exec "$HOME/.local/bin/workflow-policy" initialize-default-home\n')
    hook = 'run_after_zz-remote-worktree-activation.sh.tmpl'
    # Byte-identical to the previous generation: the remote user environment
    # neither gains a script nor re-runs an altered one.
    assert render(hook) == remote
    assert render(hook, remote=False) == '#!/bin/bash\nset -euo pipefail\nexit 0\n'
    assert render(hook, remote=False, options={'linux_workstation': {'enabled': True}}) == (
        '#!/bin/bash\nset -euo pipefail\n'
        '# Another root stays with its owner: nothing is attempted or read for it.\n'
        'exec "$HOME/.local/bin/workflow-policy" initialize-default-home \\\n'
        '    --default-home-root-only\n')


def test_default_home_root_requires_exactly_the_default_root(policy, activation):
    home, _, value = activation
    default, other = str(home / '.local/state/worktrees'), str(home / 'Worktrees')
    assert value['root'] == default and policy.default_home_root(value, home)
    assert not policy.default_home_root({**value, 'root': other}, home)
    override = {'repository': '/example/repository', 'root': other}
    assert not policy.default_home_root({**value, 'repositories': [override]}, home)
    within = {'repository': '/example/repository', 'root': default}
    assert policy.default_home_root({**value, 'repositories': [within]}, home)


@pytest.mark.parametrize('example', WORKSTATION_EXAMPLES)
def test_shipped_workstation_configuration_reaches_the_worktree_policy(tmp_path, example):
    data = chezmoi_data('linux', False, False, example)
    managed = set(chezmoi_output(data, 'managed').splitlines())
    assert {POLICY_DOCUMENT, ACTIVATION_HOOK} <= managed
    assert ACTIVATION_FILE not in managed
    calls = tmp_path / 'calls'
    result = activation_hook(data, tmp_path / 'home', calls)
    assert result.returncode == 0, result.stderr
    assert calls.read_text().splitlines() == ['initialize-default-home --default-home-root-only']


def render_shipped_document(generation_source, home, config, workspaces):
    path = config / 'dotfiles-ai/workflow-policy.json'
    document = ROOT / 'private_dot_config/dotfiles-ai/private_workflow-policy.json.tmpl'
    path.write_text(render_generation(generation_source, home, document.read_text(), workspaces))
    path.chmod(0o600)
    return json.loads(path.read_text())


@pytest.mark.parametrize('example', WORKSTATION_EXAMPLES)
def test_shipped_workstation_root_renders_the_document_and_activates_once(
        policy, activation, generation_source, monkeypatch, example):
    home, config, _ = activation
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.83.0')
    shipped = tomllib.loads((ROOT / example).read_text())['data']['dotfiles_ai']['workspaces']
    value = render_shipped_document(generation_source, home, config, shipped)
    assert value['root'] == str(home / '.local/state/worktrees')
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    policy.initialize_default_home(value, home, config)
    first = target.read_bytes()
    assert json.loads(first) == policy.snapshot(value, home)
    assert json.loads(first)['worktrunk_version'] == 'wt v0.83.0'
    policy.initialize_default_home(value, home, config)
    assert target.read_bytes() == first


def test_another_workstation_root_renders_the_document_and_activates_nothing(
        policy, activation, generation_source, monkeypatch):
    home, config, _ = activation
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.83.0')
    value = render_shipped_document(generation_source, home, config,
                                    {'schema_version': 1, 'root': '~/Worktrees'})
    assert value['root'] == str(home / 'Worktrees')
    with pytest.raises(ValueError):
        policy.initialize_default_home(value, home, config)
    assert not os.path.lexists(config / 'dotfiles-ai/workflow-policy.activation.json')
    assert not list((config / 'dotfiles-ai').glob('.activation-*.tmp'))


def test_shipped_workstation_root_must_exist_before_the_first_apply(storage_home, generation_source):
    # Rendering is read-only. First-run workstation setup provisions the root
    # before it asks chezmoi to render this document.
    document = ROOT / 'private_dot_config/dotfiles-ai/private_workflow-policy.json.tmpl'
    shipped = {'schema_version': 1, 'root': '~/.local/state/worktrees'}
    with pytest.raises(AssertionError, match='invalid_or_unavailable'):
        render_generation(generation_source, storage_home, document.read_text(), shipped)
    (storage_home / '.local/state/worktrees').mkdir(parents=True)
    value = json.loads(render_generation(generation_source, storage_home, document.read_text(), shipped))
    assert value['root'] == str(storage_home / '.local/state/worktrees')


@pytest.mark.parametrize('activated', ['wt v0.80.0', 'wt v0.81.0', 'wt v0.83.0'])
@pytest.mark.parametrize('installed', ['wt v0.80.0', 'wt v0.81.0', 'wt v0.83.0'])
def test_existing_activation_is_verified_and_kept_whatever_its_version(
        policy, activation, monkeypatch, activated, installed):
    home, config, value = activation
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: activated)
    policy.initialize_default_home(value, home, config)
    before, inode = target.read_bytes(), target.stat().st_ino
    assert json.loads(before)['worktrunk_version'] == activated
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: installed)
    if installed != activated:
        # The installed version differs from the activation: refused until reviewed.
        with pytest.raises(ValueError):
            policy.initialize_default_home(value, home, config)
    else:
        policy.initialize_default_home(value, home, config)
    assert target.read_bytes() == before and target.stat().st_ino == inode


def test_reactivation_after_removal_binds_the_installed_version(policy, activation, monkeypatch):
    home, config, value = activation
    target = config / 'dotfiles-ai/workflow-policy.activation.json'
    policy.initialize_default_home(value, home, config)
    assert json.loads(target.read_text())['worktrunk_version'] == 'wt v0.80.0'
    monkeypatch.setattr(policy, 'worktrunk_version', lambda: 'wt v0.83.0')
    stale = target.read_bytes()
    with pytest.raises(ValueError):
        policy.initialize_default_home(value, home, config)
    assert target.read_bytes() == stale
    target.unlink()
    policy.initialize_default_home(value, home, config)
    saved = json.loads(target.read_text())
    assert saved['worktrunk_version'] == 'wt v0.83.0' and saved == policy.snapshot(value, home)


native_linux = pytest.mark.skipif(sys.platform != 'linux' or not shutil.which('findmnt'),
                                  reason='activation reads native Linux mount identity')


def shipped_data():
    return chezmoi_data('linux', False, False, WORKSTATION_EXAMPLES[0])


@pytest.fixture
def shipped_host(tmp_path, generation_source):
    """A real explicit apply of the shipped workstation configuration.

    The clean source carries the policy, the helper and the activation hook;
    the fresh home already holds the two owned directories; a scripted `wt`
    reports whichever version the test says is installed. `tools` comes first
    on PATH, so a test may script another native command there as well.
    """
    home = tmp_path.resolve() / 'home'
    for relative in ('.local/state/worktrees', '.cache/dotfiles-ai/dvc'):
        (home / relative).mkdir(parents=True)
    hook = 'run_after_zz-remote-worktree-activation.sh.tmpl'
    shutil.copyfile(ROOT / hook, generation_source / hook)
    git(generation_source, 'add', '.')
    git(generation_source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-m', 'activation hook')
    tools = tmp_path / 'bin'
    tools.mkdir()
    (tools / 'wt').write_text('#!/bin/sh\ncat "$REPORTED"\n')
    (tools / 'wt').chmod(0o755)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('GIT_', 'WORKTRUNK_', 'XDG_'))}
    environment.update(HOME=str(home), PATH=f"{tools}:{os.environ['PATH']}",
                       REPORTED=str(tools / 'reported'))

    def apply(data):
        return subprocess.run(
            ['chezmoi', '-S', str(generation_source), '--config', '/dev/null',
             '--config-format', 'toml', '--override-data', json.dumps(data),
             '--cache', str(tmp_path / 'cache'), '--persistent-state', str(tmp_path / 'state.boltdb'),
             'apply'], env=environment, text=True, capture_output=True, timeout=120)

    return home, tools, apply


def another_root_data():
    data = shipped_data()
    data['dotfiles_ai']['workspaces'] = {'schema_version': 1, 'root': '~/Worktrees'}
    return data


@native_linux
def test_explicit_apply_of_the_shipped_configuration_activates_once(shipped_host):
    home, tools, apply = shipped_host
    (tools / 'reported').write_text('wt v0.83.0\n')
    document = home / '.config/dotfiles-ai/workflow-policy.json'
    activation = home / '.config/dotfiles-ai/workflow-policy.activation.json'
    root = str(home / '.local/state/worktrees')
    written = None
    for _ in range(2):
        result = apply(shipped_data())
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(document.read_text())['root'] == root
        assert stat.S_IMODE(document.stat().st_mode) == 0o600
        native = tomllib.loads((home / '.config/worktrunk/config.toml').read_text())
        assert native['worktree-path'].startswith(root + '/')
        saved = activation.read_bytes()
        assert json.loads(saved)['worktrunk_version'] == 'wt v0.83.0'
        assert stat.S_IMODE(activation.stat().st_mode) == 0o600
        # A second explicit apply changes neither the document nor the activation.
        if written is not None:
            assert (document.read_bytes(), saved) == written
        written = document.read_bytes(), saved


@native_linux
def test_another_root_is_left_with_its_owner_and_the_apply_succeeds(shipped_host):
    home, tools, apply = shipped_host
    (tools / 'reported').write_text('wt v0.83.0\n')
    (home / 'Worktrees').mkdir()
    (home / '.config').mkdir(mode=0o700)
    policy = home / '.config/dotfiles-ai'
    policy.mkdir()
    # Whatever the owner installed for that root is neither read nor changed.
    activation = policy / 'workflow-policy.activation.json'
    activation.write_text('{"owner":"made"}\n')
    activation.chmod(0o600)
    for _ in range(2):
        result = apply(another_root_data())
        assert result.returncode == 0, result.stdout + result.stderr
        document = policy / 'workflow-policy.json'
        assert json.loads(document.read_text())['root'] == str(home / 'Worktrees')
        assert activation.read_text() == '{"owner":"made"}\n'
        assert sorted(path.name for path in policy.iterdir()) == ['workflow-policy.activation.json',
                                                                  'workflow-policy.json']


@native_linux
def test_default_root_on_another_mount_is_still_refused(shipped_host):
    home, tools, apply = shipped_host
    (tools / 'reported').write_text('wt v0.83.0\n')
    # The default path now reports another mount than the home.
    (tools / 'findmnt').write_text(
        '#!/bin/sh\n[ "$5" = "$HOME/.local/state/worktrees" ] && target=/elsewhere || target=/\n'
        'printf \'{"filesystems":[{"uuid":null,"target":"%s"}]}\\n\' "$target"\n')
    (tools / 'findmnt').chmod(0o755)
    result = apply(shipped_data())
    assert result.returncode != 0
    assert 'activation stage home-identity' in result.stdout + result.stderr
    assert not os.path.lexists(home / '.config/dotfiles-ai/workflow-policy.activation.json')


@native_linux
@pytest.mark.parametrize('damage', ['installed_version', 'malformed'])
def test_apply_reports_a_failed_verification_and_keeps_the_activation(shipped_host, damage):
    home, tools, apply = shipped_host
    activation = home / '.config/dotfiles-ai/workflow-policy.activation.json'
    (tools / 'reported').write_text('wt v0.80.0\n')
    assert apply(shipped_data()).returncode == 0
    if damage == 'installed_version':
        (tools / 'reported').write_text('wt v0.83.0\n')  # The installer replaced the binary.
    else:
        activation.write_text('{}')
    before, inode = activation.read_bytes(), activation.stat().st_ino
    result = apply(shipped_data())
    assert result.returncode != 0
    assert 'invalid_or_unavailable' in result.stdout + result.stderr
    assert activation.read_bytes() == before and activation.stat().st_ino == inode


@native_linux
def test_upgrade_backs_up_reactivates_once_and_rolls_back(shipped_host):
    home, tools, apply = shipped_host
    reported = tools / 'reported'
    policy = home / '.config/dotfiles-ai'
    activation, document = policy / 'workflow-policy.activation.json', policy / 'workflow-policy.json'
    reported.write_text('wt v0.80.0\n')
    assert apply(shipped_data()).returncode == 0
    rollback = home.parent / 'rollback'
    rollback.mkdir()
    for live, name in ((reported, 'version'), (activation, 'activation.json'), (document, 'document.json')):
        shutil.copy2(live, rollback / name)
        assert (rollback / name).read_bytes() == live.read_bytes()
        assert stat.S_IMODE((rollback / name).stat().st_mode) == stat.S_IMODE(live.stat().st_mode)
    # The fixture's wt reports its selected version from this file.
    reported.write_text('wt v0.83.0\n')
    # Remove the old activation, then apply once: its activation stage
    # re-activates, and a further apply changes nothing.
    activation.unlink()
    activated = apply(shipped_data())
    assert activated.returncode == 0, activated.stdout + activated.stderr
    rebound = activation.read_bytes()
    assert json.loads(rebound)['worktrunk_version'] == 'wt v0.83.0'
    assert apply(shipped_data()).returncode == 0
    assert activation.read_bytes() == rebound
    # Rollback: restore the old binary and both files; the workstation verifies
    # again as before the upgrade.
    shutil.copy2(rollback / 'version', reported)
    shutil.copy2(rollback / 'activation.json', activation)
    shutil.copy2(rollback / 'document.json', document)
    restored = apply(shipped_data())
    assert restored.returncode == 0, restored.stdout + restored.stderr
    assert activation.read_bytes() == (rollback / 'activation.json').read_bytes()
    assert document.read_bytes() == (rollback / 'document.json').read_bytes()


def test_fresh_home_installs_the_setup_command_before_the_policy_directories_exist(tmp_path):
    # The first documented step of the Try Omarchy flow. Only the requested
    # target is rendered, so the setup command can be installed before the
    # declared root exists and can provision it ahead of its own full apply.
    home = tmp_path / 'home'
    (home / '.local/bin').mkdir(parents=True)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('GIT_', 'WORKTRUNK_', 'XDG_'))}
    environment.update(HOME=str(home))
    result = subprocess.run(
        ['chezmoi', '-S', str(ROOT), '--config', '/dev/null', '--config-format', 'toml',
         '--override-data', json.dumps(shipped_data()), '--cache', str(tmp_path / 'cache'),
         '--persistent-state', str(tmp_path / 'state.boltdb'), 'apply', '--exclude', 'scripts',
         str(home / '.local/bin/dotfiles-ai-omarchy-setup')],
        env=environment, text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / '.local/bin/dotfiles-ai-omarchy-setup').is_file()
    assert sorted(path.relative_to(home).as_posix() for path in home.rglob('*')) == [
        '.local', '.local/bin', '.local/bin/dotfiles-ai-omarchy-setup']
