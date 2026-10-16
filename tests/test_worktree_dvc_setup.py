"""Bootstrap is config-only; validation cannot migrate configuration or data."""
import importlib.machinery
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home/.config"))
    source = Path(__file__).parents[1] / "dot_local/bin/executable_worktree-dvc-setup"
    loader = importlib.machinery.SourceFileLoader("worktree_dvc_setup", str(source))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    root, primary, cache = (tmp_path / name for name in ("task", "primary", "cache"))
    root.mkdir()
    primary.mkdir()
    (root / ".dvc").mkdir()
    calls = []
    effective = {"cache": root / ".dvc/cache", "type": "reflink"}

    def run(args, cwd):
        calls.append(args)
        if args == ["dvc", "data", "status", "--json"]:
            return "{}"
        if args[:2] == ["git", "worktree"]:
            return f"worktree {primary}\0\0worktree {root}\0\0"
        if args == ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"]:
            return str(primary / ".git")
        if args == ["dvc", "cache", "dir"]:
            return str(effective["cache"])
        if args == ["dvc", "config", "cache.type"]:
            return effective["type"]
        if args[:4] == ["dvc", "config", "--local", "cache.type"]:
            effective["type"] = args[4]
        if args[:4] == ["dvc", "cache", "dir", "--local"]:
            effective["cache"] = Path(args[4])
        return ""

    monkeypatch.setattr(module, "run", run)
    return module, root, primary, cache, calls, effective


def test_bootstrap_does_not_materialize_or_create_cache(setup):
    module, root, _, cache, calls, _ = setup
    module.configure(root, cache)
    assert [command for command in calls if "--local" in command] == [
        ["dvc", "config", "--local", "cache.type", "reflink"],
        ["dvc", "cache", "dir", "--local", str(cache)]]
    assert not cache.exists()
    assert not (root / "data").exists()


@pytest.mark.parametrize("held", ["primary", "internal_cache", "private_cache", "conflicting_config",
                                  "copy_fallback", "symlink", "hardlink", "cache_file"])
def test_unsafe_bootstrap_refuses_before_config_writes(setup, held):
    module, root, primary, cache, calls, _ = setup
    if held == "primary":
        (primary / ".dvc").mkdir()
        root = primary
    elif held == "internal_cache":
        cache = primary / "cache"
    elif held == "private_cache":
        private = root / ".dvc/cache"
        private.mkdir()
        (private / "data").write_bytes(b"retain me")
    elif held == "conflicting_config":
        (root / ".dvc/config.local").write_text("[cache]\n dir = elsewhere\n")
    elif held == "copy_fallback":
        (root / ".dvc/config.local").write_text('[cache]\n type = "reflink,copy"\n')
    elif held == "symlink":
        (root / ".dvc/config.local").symlink_to(primary / "config")
    elif held == "hardlink":
        original = primary / "config"
        original.write_text("[cache]\n type = reflink\n")
        (root / ".dvc/config.local").hardlink_to(original)
    else:
        cache.write_bytes(b"retain me")
    with pytest.raises(ValueError):
        module.configure(root, cache)
    assert not any("--local" in command for command in calls)


def test_check_uses_explicit_local_selection_and_never_writes(setup):
    module, root, _, cache, calls, effective = setup
    local = root / ".dvc/config.local"
    local.write_text(f"[cache]\n dir = {cache}\n type = reflink\n")
    before = local.read_bytes()
    effective["cache"] = cache
    module.configure(root, None, check=True)
    assert local.read_bytes() == before
    assert not any("--local" in command for command in calls)


@pytest.mark.parametrize("problem", ["missing", "copy_override", "cache_override"])
def test_check_refuses_unconfigured_or_overridden_cache(setup, problem):
    module, root, _, cache, calls, effective = setup
    if problem != "missing":
        (root / ".dvc/config.local").write_text(f"[cache]\n dir = {cache}\n type = reflink\n")
        effective["cache"] = cache if problem == "copy_override" else root / ".dvc/cache"
        effective["type"] = "reflink,copy" if problem == "copy_override" else "reflink"
    with pytest.raises(ValueError):
        module.configure(root, None, check=True)
    assert not any("--local" in command for command in calls)


def test_malformed_config_diagnostic_does_not_echo_contents(setup):
    module, root, _, cache, _, _ = setup
    (root / ".dvc/config.local").write_text("PRIVATE_TEST_SENTINEL\n")
    with pytest.raises(ValueError) as error:
        module.configure(root, cache)
    assert "PRIVATE_TEST_SENTINEL" not in str(error.value)


@pytest.mark.parametrize("problem", ["cache_alias", "parent_alias", "mutable_alias", "cross_device"])
def test_cache_identity_and_mutable_state_refuse_before_configuration(setup, monkeypatch, problem):
    module, root, primary, cache, calls, _ = setup
    if problem == "cache_alias":
        cache.symlink_to(primary, target_is_directory=True)
    elif problem == "parent_alias":
        alias = cache.parent / "alias"
        alias.symlink_to(primary, target_is_directory=True)
        cache = alias / "cache"
    elif problem == "mutable_alias":
        (root / ".dvc/tmp").symlink_to(primary, target_is_directory=True)
    else:
        original = module.device
        monkeypatch.setattr(module, "device", lambda path: original(path) + (path != root))
    with pytest.raises(ValueError):
        module.configure(root, cache)
    assert not any("--local" in command for command in calls)


def test_unsupported_reflink_refuses_without_copy_fallback(setup, monkeypatch):
    module, root, _, cache, calls, _ = setup
    def unavailable(*_):
        raise ValueError("reflink_unavailable")
    monkeypatch.setattr(module, "qualify_reflink", unavailable)
    with pytest.raises(ValueError, match="reflink_unavailable"):
        module.configure(root, cache)
    assert not cache.exists()
    assert not any("--local" in command for command in calls)


def test_check_rejects_configured_alias_before_resolving_it(setup):
    module, root, _, cache, calls, effective = setup
    cache.mkdir()
    alias = cache.parent / "cache-alias"
    alias.symlink_to(cache, target_is_directory=True)
    (root / ".dvc/config.local").write_text(f"[cache]\n dir = {alias}\n type = reflink\n")
    effective["cache"] = cache
    with pytest.raises(ValueError):
        module.configure(root, None, check=True)
    assert not any("--local" in command for command in calls)


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_nested_mutable_alias_blocks_bootstrap(setup, kind):
    module, root, primary, cache, calls, _ = setup
    shared = primary / "lock"
    shared.write_bytes(b"preserve shared state")
    local = root / ".dvc/tmp/lock"
    local.parent.mkdir()
    if kind == "symlink":
        local.symlink_to(shared)
    else:
        local.hardlink_to(shared)
    with pytest.raises(ValueError):
        module.configure(root, cache)
    assert shared.read_bytes() == b"preserve shared state"
    assert not any("--local" in command for command in calls)


@pytest.mark.parametrize("name", [".", "config.local", "tmp", "tmp/state", "tmp/nested"])
def test_writable_configuration_or_mutable_state_refuses_before_writes(setup, name):
    module, root, _, cache, calls, _ = setup
    path = root / ".dvc" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if name in {".", "tmp", "tmp/nested"}:
        path.mkdir(exist_ok=True)
        path.chmod(0o777)
    else:
        path.write_text("[cache]\n type = reflink\n" if name == "config.local" else "state")
        path.chmod(0o666)
    with pytest.raises(ValueError):
        module.configure(root, cache)
    assert not any("--local" in command for command in calls)


def test_dirty_outputs_block_redirection_even_without_old_cache(setup, monkeypatch):
    module, root, _, cache, calls, _ = setup
    native = module.run
    def dirty(args, cwd):
        if args == ["dvc", "data", "status", "--json"]:
            return '{"uncommitted":{"modified":["result.txt"]}}'
        return native(args, cwd)
    monkeypatch.setattr(module, "run", dirty)
    (root / "result.txt").write_bytes(b"unique result")
    with pytest.raises(ValueError):
        module.configure(root, cache)
    assert (root / "result.txt").read_bytes() == b"unique result"
    assert not any("--local" in command for command in calls)


@pytest.mark.parametrize("status", [{"uncommitted": {"deleted": "missing"}},
    {"not_in_cache": ["result.txt"]}, {"unchanged": "result.txt"},
    {"not_in_cache": "missing"}, {"untracked": {}}, {"committed": []}])
def test_uncached_present_outputs_and_untyped_status_never_redirect_cache(setup, monkeypatch, status):
    module, root, _, cache, calls, _ = setup
    native = module.run
    def observed(args, cwd):
        return json.dumps(status) if args == ["dvc", "data", "status", "--json"] else native(args, cwd)
    monkeypatch.setattr(module, "run", observed)
    (root / "result.txt").write_bytes(b"retain uncached result")
    with pytest.raises(ValueError):
        module.configure(root, cache)
    assert (root / "result.txt").read_bytes() == b"retain uncached result"
    assert not any("--local" in command for command in calls)


def test_bootstrap_checks_effective_selection_after_writes(setup, monkeypatch):
    module, root, _, cache, _, _ = setup
    native = module.run
    def overridden(args, cwd):
        result = native(args, cwd)
        return "reflink,copy" if args == ["dvc", "config", "cache.type"] else result
    monkeypatch.setattr(module, "run", overridden)
    with pytest.raises(ValueError, match="effective"):
        module.configure(root, cache)


def test_activated_policy_selects_only_the_full_repository_cache_namespace(setup, monkeypatch):
    module, root, primary, cache, calls, _ = setup
    home = Path(os.environ["HOME"])
    policy = home / ".config/dotfiles-ai/workflow-policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"repositories": [{"repository": str(primary)}], "cache_root": str(cache)}))
    policy.chmod(0o600)
    helper = home / ".local/bin/workflow-policy"
    helper.parent.mkdir(parents=True)
    helper.write_text("synthetic validator adapter")
    helper.chmod(0o700)
    original = module.run
    def native(args, cwd):
        return '{"status":"passed"}' if args == [str(helper), "check"] else original(args, cwd)
    monkeypatch.setattr(module, "run", native)
    expected = cache / hashlib.sha256(str((primary / ".git").resolve()).encode()).hexdigest()
    assert module.policy_cache(root) == expected
    with pytest.raises(ValueError, match="namespace"):
        module.configure(root, cache)
    assert not any("--local" in command for command in calls)
    module.configure(root, expected)
    assert ["dvc", "cache", "dir", "--local", str(expected)] in calls


@pytest.mark.skipif(shutil.which("dvc") is None, reason="native DVC authority is unavailable")
def test_native_dvc_code_only_bootstrap_and_targeted_reflink(tmp_path):
    primary, task, cache, home = (tmp_path / name for name in ("primary", "task", "shared cache", "home"))
    primary.mkdir()
    home.mkdir()
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GIT_", "DVC_", "DBSCTR_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), XDG_CACHE_HOME=str(home / "cache"),
               XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"), DVC_NO_ANALYTICS="1")

    def run(cwd, *argv, check=True):
        return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, check=check, timeout=60)

    run(primary, "git", "init", "-b", "main")
    run(primary, "dvc", "init")
    run(primary, "dvc", "cache", "dir", "--local", str(cache))
    run(primary, "dvc", "config", "--local", "cache.type", "reflink")
    data = b"versioned fixture\n" * 4096
    (primary / "data.txt").write_bytes(data)
    run(primary, "dvc", "add", "data.txt")
    cached = [path for path in cache.rglob("*") if path.is_file() and path.read_bytes() == data]
    assert len(cached) == 1
    run(primary, "git", "add", ".")
    run(primary, "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@invalid",
        "commit", "-m", "fixture")
    run(primary, "git", "worktree", "add", "-b", "task", str(task))
    script = str(Path(__file__).parents[1] / "dot_local/bin/executable_worktree-dvc-setup")
    run(task, sys.executable, script, "--cache", str(cache))
    before = (task / ".dvc/config.local").read_bytes()
    run(task, sys.executable, script, "--check")
    assert (task / ".dvc/config.local").read_bytes() == before
    assert not (task / "data.txt").exists()
    assert not (task / ".dvc/cache").exists()
    run(task, "dvc", "checkout", "data.txt.dvc")
    assert (task / "data.txt").read_bytes() == data
    assert (task / "data.txt").stat().st_ino != (primary / "data.txt").stat().st_ino
    (task / "data.txt").write_bytes(b"independent edit\n")
    assert (primary / "data.txt").read_bytes() == data
    assert cached[0].read_bytes() == data
    assert (task / ".dvc").stat().st_ino != (primary / ".dvc").stat().st_ino
    assert run(primary, "git", "branch", "--show-current").stdout.strip() == "main"
