"""Bootstrap is config-only; validation cannot migrate configuration or data."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def setup(tmp_path, monkeypatch):
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
        if args[:2] == ["git", "worktree"]:
            return f"worktree {primary}\0\0worktree {root}\0\0"
        if args == ["dvc", "cache", "dir"]:
            return str(effective["cache"])
        if args == ["dvc", "config", "cache.type"]:
            return effective["type"]
        return ""

    monkeypatch.setattr(module, "run", run)
    return module, root, primary, cache, calls, effective


def test_bootstrap_does_not_materialize_or_create_cache(setup):
    module, root, _, cache, calls, _ = setup
    module.configure(root, cache)
    assert calls[-2:] == [["dvc", "config", "--local", "cache.type", "reflink"],
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
