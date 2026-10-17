"""Managed user hooks guard native Worktrunk; no custom allocator participates."""
import os
import importlib.machinery
import importlib.util
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tomllib

import pytest
from test_worktrunk_registration import fixture, git


ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "private_dot_config/worktrunk/config.toml.tmpl"


@pytest.fixture
def policy():
    path = ROOT / "dot_local/bin/executable_workflow-policy"
    loader = importlib.machinery.SourceFileLoader("workflow_policy", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def storage_home(tmp_path):
    home = tmp_path.resolve() / "home"
    (home / "Worktrees").mkdir(parents=True)
    (home / ".cache/dotfiles-ai/dvc").mkdir(parents=True)
    return home


@pytest.fixture
def generation_source(tmp_path):
    source = tmp_path.resolve() / "source"
    source.mkdir()
    for relative in ("dot_local/bin/executable_workflow-policy", ".chezmoitemplates/workflow-policy.tmpl",
                     "private_dot_config/worktrunk/config.toml.tmpl",
                     "private_dot_config/dotfiles-ai/private_workflow-policy.json.tmpl"):
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    git(source, "init")
    git(source, "add", ".")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
    return source


def render_generation(source, home, template, options=None):
    data = {"chezmoi": {"homeDir": str(home)}, "dotfiles_ai": {}}
    if options is not None:
        data["dotfiles_ai"]["workspaces"] = options
    result = subprocess.run(["chezmoi", "-S", str(source), "--config", "/dev/null", "--config-format", "toml", "--override-data",
                           json.dumps(data), "execute-template"], input=template, text=True,
                          capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_policy_defaults_are_not_legacy_state_roots(policy, storage_home):
    value = policy.resolve(None, storage_home)
    assert value["root"] == str(storage_home / "Worktrees")
    assert value["cache_root"] == str(storage_home / ".cache/dotfiles-ai/dvc")
    assert value["repositories"] == []
    assert value["naming"] == dict(task="dbsctr", discovery="discovery", integration="integration")


@pytest.mark.skipif(not shutil.which("wt"), reason="native policy qualification tool unavailable")
def test_pr_review_uses_actual_disposable_validator_without_requiring_activation_for_birth(
        fixture, policy, storage_home, generation_source, monkeypatch):
    home = storage_home
    helper = home / ".local/bin/workflow-policy"
    helper.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "dot_local/bin/executable_workflow-policy", helper)
    helper.chmod(0o700)
    config = home / ".config/worktrunk/config.toml"
    config.parent.mkdir(parents=True)
    options = {"schema_version": 1, "repositories": [{"repository": str(fixture.repo.resolve()),
               "delivery": {"schema_version": 1}}]}
    config.write_text(render_generation(generation_source, home, CONFIG.read_text(), options))
    path = home / ".config/dotfiles-ai/workflow-policy.json"
    path.parent.mkdir(parents=True)
    path.write_text(render_generation(generation_source, home,
        (ROOT / "private_dot_config/dotfiles-ai/private_workflow-policy.json.tmpl").read_text(), options))
    path.chmod(0o600)
    loader = importlib.machinery.SourceFileLoader("pr_review_native", str(ROOT / "dot_local/bin/executable_dbsctrctl"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "DVC_", "DBSCTR_", "WORKTRUNK_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               WORKTRUNK_CONFIG_PATH=str(config), WORKTRUNK_SYSTEM_CONFIG_PATH=str(home / "no-system-config"))
    monkeypatch.setattr(core, "INSPECT_ENV", env)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    before = git(fixture.repo, "worktree", "list", "--porcelain")
    assert core.pr_review_birth_policy(fixture.repo) is None
    assert core.birth_policy_snapshot(fixture.repo, core.preservation_policy_snapshot) is None
    with pytest.raises(RuntimeError):
        core.pr_review_policy_snapshot(fixture.repo)
    activation = path.with_name("workflow-policy.activation.json")
    activation.write_text(json.dumps(policy.snapshot(json.loads(path.read_text()), home)))
    activation.chmod(0o600)
    selected = core.pr_review_policy_snapshot(fixture.repo)
    assert not selected["delivery"]["enabled"]
    assert core.pr_review_birth_policy(fixture.repo) == selected
    assert git(fixture.repo, "worktree", "list", "--porcelain") == before
    linked = home / "Worktrees/linked"
    git(fixture.repo, "worktree", "add", "-b", "linked", str(linked))
    assert core.pr_review_policy_snapshot(linked) == selected
    original = path.read_bytes()
    changed = json.loads(original)
    changed["repositories"] = []
    changed["policy_digest"] = core.pr_review_digest({k: v for k, v in changed.items() if k != "policy_digest"})
    path.write_text(json.dumps(changed))
    assert core.pr_review_birth_policy(fixture.repo) is None  # Activation no longer matches.
    activation.write_text(json.dumps(policy.snapshot(changed, home)))
    config.write_text("")  # Replace only this fixture's generated project selector.
    config.write_text(render_generation(generation_source, home, CONFIG.read_text(), {"schema_version": 1}))
    # An absent exact repository entry stays disabled; no global delivery fallback.
    assert core.pr_review_policy_snapshot(linked)["delivery"]["enabled"] is False


@pytest.mark.parametrize("value", [{}, {"schema_version": True}, {"schema_version": 2},
    {"schema_version": 1, "automatic_remove": True}, {"schema_version": 1, "root": ""},
    {"schema_version": 1, "root": "$HOME/tasks"}, {"schema_version": 1, "root": "/a/../b"},
    {"schema_version": 1, "naming": {"task": "Bad prefix"}},
    {"schema_version": 1, "repositories": "wrong"}])
def test_policy_rejects_invalid_schema_without_writes(policy, storage_home, value):
    before = sorted(str(p) for p in storage_home.rglob("*"))
    with pytest.raises(ValueError):
        policy.resolve(value, storage_home)
    assert sorted(str(p) for p in storage_home.rglob("*")) == before


def test_exact_repository_override_and_full_cache_identity(policy, storage_home, fixture):
    value = policy.resolve({"schema_version": 1, "repositories": [{
        "repository": str(fixture.repo.resolve()), "naming": {"task": "task"}}]}, storage_home)
    selected = policy.effective(value, fixture.repo)
    common = Path(git(fixture.repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).resolve()
    assert selected["cache"] == str(storage_home / ".cache/dotfiles-ai/dvc" /
                                   hashlib.sha256(str(common).encode()).hexdigest())
    assert selected["naming"]["task"] == "task"
    assert selected["naming"]["discovery"] == "discovery"
    with pytest.raises(ValueError):
        policy.resolve({"schema_version": 1, "repositories": [
            {"repository": str(fixture.repo.resolve())},
            {"repository": str(fixture.repo.resolve())}]}, storage_home)


def test_existing_registered_children_allow_rerender_and_share_cache(policy, storage_home, fixture):
    linked = storage_home / "Worktrees/registered-task"
    git(fixture.repo, "worktree", "add", "-b", "registered-task", str(linked))
    value = policy.resolve({"schema_version": 1, "repositories": [
        {"repository": str(fixture.repo.resolve())}]}, storage_home)
    assert policy.effective(value, linked) == policy.effective(value, fixture.repo)
    nested = linked / "nested-root"
    nested.mkdir()
    with pytest.raises(ValueError):
        policy.resolve({"schema_version": 1, "root": str(nested), "repositories": [
            {"repository": str(fixture.repo.resolve())}]}, storage_home)


def test_storage_refuses_nested_or_symlink_roots(policy, storage_home, fixture):
    nested = fixture.repo / "tasks"
    nested.mkdir()
    linked = storage_home / "linked"
    linked.symlink_to(storage_home / "Worktrees", target_is_directory=True)
    for root in (str(nested), str(linked), str(storage_home / "missing-external")):
        with pytest.raises(ValueError):
            policy.resolve({"schema_version": 1, "root": root,
                            "repositories": [{"repository": str(fixture.repo.resolve())}]}, storage_home)


def test_storage_refuses_replaceable_ancestor_even_when_leaf_is_owned(policy, storage_home):
    unsafe = storage_home.parent / "unsafe"
    leaf = unsafe / "owned"
    leaf.mkdir(parents=True)
    unsafe.chmod(0o777)
    try:
        with pytest.raises(ValueError):
            policy.resolve({"schema_version": 1, "root": str(leaf)}, storage_home)
    finally:
        unsafe.chmod(0o700)


@pytest.mark.parametrize("version", [None, True, 2, "1"])
def test_preservation_requires_exact_schema_version(policy, version):
    value = {"automatic_remove": False}
    if version is not None:
        value["schema_version"] = version
    with pytest.raises(ValueError):
        policy.consent("preservation", value)
    policy.consent("preservation", {"schema_version": 1, "automatic_remove": False})


def test_native_config_preserves_unrelated_values_and_safety(policy, storage_home):
    value = policy.resolve(None, storage_home)
    previous = {"list": {"full": True}, "pre-switch": {"user": "true"},
                "remove": {"delete-branch": True}, "commit": {"stage": "all", "generation": {"command": "true"}}}
    native = policy.native_config(value, storage_home, previous)
    assert native["worktree-path"] == str(storage_home / "Worktrees") + "/{{ repo }}-{{ repo_path | hash }}/{{ branch | sanitize }}"
    assert native["list"]["full"] is True and native["pre-switch"]["user"] == "true"
    assert native["commit"]["generation"] == {"command": "true"}
    assert native["remove"]["delete-branch"] is False
    assert native["pre-remove"]["preservation"] == "exec dbsctrctl workspace-remove-check --json"
    assert "workflow-policy" in native["pre-switch"]["workflow-storage"]
    assert "pre-start" not in native and "post-start" not in native


def test_mount_replacement_and_partial_generation_refuse(policy, storage_home, monkeypatch):
    value = policy.resolve(None, storage_home)
    external = storage_home.parent / "external"
    external.mkdir()
    value["root"] = str(external)
    value["source_commit"] = "a" * 40
    value["policy_digest"] = policy.digest(value)
    monkeypatch.setattr(policy, "mount_identity", lambda path: ("uuid-one", "/mounted"))
    snapshot = policy.snapshot(value, storage_home)
    policy.verify_snapshot(value, snapshot, storage_home)
    monkeypatch.setattr(policy, "mount_identity", lambda path: ("uuid-two", "/mounted"))
    with pytest.raises(ValueError):
        policy.verify_snapshot(value, snapshot, storage_home)
    snapshot["policy_digest"] = "b" * 64
    with pytest.raises(ValueError):
        policy.verify_snapshot(value, snapshot, storage_home)


def test_native_selector_conflict_refuses_whole_generation(policy, storage_home, fixture):
    other = fixture.repo.parent / "clone"
    subprocess.run(["git", "clone", str(fixture.repo), str(other)], check=True, capture_output=True)
    git(fixture.repo, "remote", "add", "origin", "https://example.invalid/team/repository.git")
    git(other, "remote", "set-url", "origin", "https://example.invalid/team/repository.git")
    different = storage_home.parent / "other-tasks"
    different.mkdir()
    with pytest.raises(ValueError):
        policy.resolve({"schema_version": 1, "repositories": [
            {"repository": str(fixture.repo.resolve())},
            {"repository": str(other.resolve()), "root": str(different)}]}, storage_home)


def test_mount_parsers_use_uuid_and_mountpoint_not_device_name(policy):
    assert policy.parse_mount("darwin", policy.plistlib.dumps({
        "VolumeUUID": "UUID", "MountPoint": "/volume"})) == ("UUID", "/volume")
    assert policy.parse_mount("linux", json.dumps({"filesystems": [
        {"uuid": "UUID", "target": "/volume"}]}).encode()) == ("UUID", "/volume")
    for system, output in (("darwin", policy.plistlib.dumps({"DeviceIdentifier": "disk1"})),
                           ("linux", b'{"filesystems":[{"uuid":null,"target":"/"}]}')):
        with pytest.raises(ValueError):
            policy.parse_mount(system, output)


def test_private_render_binds_clean_source_and_rejects_dirty_or_invalid_input(generation_source, storage_home):
    template = (ROOT / "private_dot_config/dotfiles-ai/private_workflow-policy.json.tmpl").read_text()
    value = json.loads(render_generation(generation_source, storage_home, template))
    assert value["source_commit"] == git(generation_source, "rev-parse", "HEAD").strip()
    assert len(value["policy_digest"]) == 64
    with pytest.raises(AssertionError, match="invalid_or_unavailable"):
        render_generation(generation_source, storage_home, template, {"schema_version": True})
    (generation_source / "uncommitted").write_text("not a release")
    with pytest.raises(AssertionError, match="invalid_or_unavailable"):
        render_generation(generation_source, storage_home, template)


def test_private_template_has_real_chezmoi_private_attribute(generation_source, storage_home):
    data = {"chezmoi": {"homeDir": str(storage_home)}, "dotfiles_ai": {}}
    dump = subprocess.run(["chezmoi", "-S", str(generation_source), "--config", "/dev/null", "--config-format", "toml",
                           "--override-data", json.dumps(data), "dump", "--format=json"],
                          capture_output=True, text=True, timeout=20)
    assert dump.returncode == 0, dump.stderr
    entries = json.loads(dump.stdout)
    target = next(value for name, value in entries.items() if name.endswith("/workflow-policy.json"))
    assert target["perm"] == 0o600


@pytest.mark.parametrize("hook", ["true", [{"user": "true"}]])
def test_native_config_preserves_non_table_hook_forms_idempotently(policy, storage_home, hook):
    value = policy.resolve(None, storage_home)
    native = policy.native_config(value, storage_home, {"pre-switch": hook})
    assert native["pre-switch"][1:] == ([{"user-preserved": hook}] if isinstance(hook, str) else hook)
    assert policy.native_config(value, storage_home, native) == native


def test_string_hook_roundtrips_through_real_toml(generation_source, storage_home):
    local = storage_home / ".config/worktrunk/config.toml"
    local.parent.mkdir(parents=True)
    local.write_text('pre-switch = "true"\n')
    native = tomllib.loads(render_generation(generation_source, storage_home, CONFIG.read_text()))
    assert native["pre-switch"][1] == {"user-preserved": "true"}


@pytest.mark.parametrize("kind, value", [("delivery", {"schema_version": 1, "enabled": "yes"}),
    ("preservation", {"automatic_remove": "true"}), ("feedback", {"schema_version": 1, "external_enabled": True}),
    ("delivery", {"schema_version": 1, "targets": ["refs/heads/main*?"]}),
    ("feedback", {"schema_version": 1, "unknown": True})])
def test_exact_consent_declarations_do_not_accept_misspelled_or_untyped_switches(policy, kind, value):
    with pytest.raises((ValueError, subprocess.SubprocessError)):
        policy.consent(kind, value)


def test_managed_policy_keeps_branches_and_uses_blocking_user_hook(generation_source, storage_home):
    value = tomllib.loads(render_generation(generation_source, storage_home, CONFIG.read_text()))
    assert value["worktree-path"] == str(storage_home / "Worktrees") + "/{{ repo }}-{{ repo_path | hash }}/{{ branch | sanitize }}"
    assert value["remove"]["delete-branch"] is False
    assert value["pre-remove"]["preservation"] == "exec dbsctrctl workspace-remove-check --json"
    assert "post-start" not in value and "pre-start" not in value
    assert value["commit"]["stage"] == "none"


@pytest.mark.skipif(not shutil.which("wt") or not shutil.which("lsof"), reason="native Worktrunk/process authority unavailable")
def test_native_user_hook_blocks_forced_dirty_removal_then_preserves_branch(fixture, policy, storage_home, generation_source):
    base = fixture.repo.parent
    home, tools = storage_home, base / "bin"
    tools.mkdir()
    shim = tools / "dbsctrctl"
    shim.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} "
                    f"{shlex.quote(str(ROOT / 'dot_local/bin/executable_dbsctrctl'))} \"$@\"\n")
    shim.chmod(0o755)
    helper = home / ".local/bin/workflow-policy"
    helper.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "dot_local/bin/executable_workflow-policy", helper)
    helper.chmod(0o755)
    config = home / ".config/worktrunk/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(render_generation(generation_source, home, CONFIG.read_text()))
    policy_path = home / ".config/dotfiles-ai/workflow-policy.json"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(render_generation(generation_source, home,
        (ROOT / "private_dot_config/dotfiles-ai/private_workflow-policy.json.tmpl").read_text()))
    policy_path.chmod(0o600)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GIT_", "DVC_", "DBSCTR_", "WORKTRUNK_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), XDG_CACHE_HOME=str(home / "cache"),
               XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"),
               PATH=f"{tools}:{os.environ['PATH']}", WORKTRUNK_CONFIG_PATH=str(config),
               WORKTRUNK_SYSTEM_CONFIG_PATH=str(base / "no-system-config"))

    def wt(*argv, ok=True):
        value = subprocess.run([shutil.which("wt"), *argv], cwd=fixture.repo, env=env,
                               text=True, capture_output=True, timeout=90)
        assert (value.returncode == 0) is ok, value.stderr + value.stdout
        return value

    # Missing activation must fail in native pre-switch before branch/directory writes.
    before = git(fixture.repo, "worktree", "list", "--porcelain")
    refused = wt("switch", "--create", "task", "--no-cd", "--yes", ok=False)
    assert "invalid_or_unavailable" in refused.stderr + refused.stdout
    assert git(fixture.repo, "worktree", "list", "--porcelain") == before
    wt("switch", "master", "--no-cd", "--yes")
    assert not subprocess.run(["git", "show-ref", "--verify", "refs/heads/task"], cwd=fixture.repo,
                              capture_output=True).returncode == 0
    activation = policy_path.with_name("workflow-policy.activation.json")
    activation.write_text(json.dumps(policy.snapshot(json.loads(policy_path.read_text()), home)))
    activation.chmod(0o600)
    for path, damaged in ((policy_path, '{"schema_version":2}'),
                          (config, config.read_text().replace(str(home / "Worktrees"), str(base / "bypass")))):
        original_bytes = path.read_bytes()
        path.write_text(damaged)
        try:
            wt("switch", "--create", "task", "--no-cd", "--yes", ok=False)
            assert git(fixture.repo, "worktree", "list", "--porcelain") == before
        finally:
            path.write_bytes(original_bytes)
    alternate = base / "alternate.toml"
    shutil.copyfile(config, alternate)
    for key, value in (("WORKTRUNK_CONFIG_PATH", str(alternate)),
                       ("WORKTRUNK_WORKTREE_PATH", str(base / "bypass"))):
        original = env.get(key)
        env[key] = value
        wt("switch", "--create", "task", "--no-cd", "--yes", ok=False)
        assert git(fixture.repo, "worktree", "list", "--porcelain") == before
        if original is None:
            del env[key]
        else:
            env[key] = original
    wt("switch", "--create", "task", "--no-cd", "--yes")
    members = git(fixture.repo, "worktree", "list", "--porcelain").splitlines()
    target = next(Path(line.removeprefix("worktree ")) for line in members
                  if line.startswith("worktree ") and Path(line.removeprefix("worktree ")) != fixture.repo.resolve())
    assert target.is_relative_to(home / "Worktrees")
    assert target.is_dir()
    wt("switch", "--create", "collision/a", "--no-cd", "--yes")
    collision = next(p for p in target.parent.iterdir() if p.name == "collision-a")
    wt("switch", "--create", "collision-a", "--no-cd", "--yes", ok=False)
    assert collision.is_dir() and git(collision, "branch", "--show-current").strip() == "collision/a"
    (target / "tracked.txt").write_text("disposable dirty fixture\n")
    refused = wt("remove", "task", "--force", "--yes", ok=False)
    assert "dirty_worktree" in refused.stdout + refused.stderr
    assert (target / "tracked.txt").read_text() == "disposable dirty fixture\n"
    git(target, "restore", "tracked.txt")
    outcome = subprocess.run([shutil.which("wt"), "remove", "task", "--yes"], cwd=fixture.repo,
                             env=env, text=True, capture_output=True, timeout=90)
    if outcome.returncode:
        # Real process visibility may time out on a busy host: unknown must retain.
        assert "process_inventory_unavailable" in outcome.stdout + outcome.stderr
        assert target.exists()
    else:
        assert not target.exists()
    assert git(fixture.repo, "branch", "--show-current").strip() == "master"
    git(fixture.repo, "show-ref", "--verify", "refs/heads/task")
