"""Native DVC 3 metadata qualifies data preservation without pulling or deletion."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("dvc") is None, reason="native DVC authority is unavailable")
def test_native_removal_checks_absent_unchanged_modified_and_ignored_data(tmp_path, monkeypatch):
    repo, home, cache, task = (tmp_path / name for name in ("repo", "home", "cache", "task"))
    repo.mkdir()
    home.mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "DVC_", "DBSCTR_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), XDG_CACHE_HOME=str(home / "cache"),
               XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"), DVC_NO_ANALYTICS="1")

    def run(*argv, cwd=repo):
        return subprocess.run(argv, cwd=cwd, env=env, check=True, text=True, capture_output=True, timeout=30).stdout

    run("git", "init", "-b", "main")
    run("dvc", "init")
    with (repo / ".dvcignore").open("a") as stream:
        stream.write("\ndataset/*.tmp\n")
    run("dvc", "cache", "dir", "--local", str(cache))
    (repo / "dataset").mkdir()
    (repo / "dataset/item.txt").write_text("fixture\n")
    run("dvc", "add", "dataset")
    run("git", "add", ".")
    run("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@invalid", "commit", "-m", "fixture")
    run("git", "worktree", "add", "-b", "task", str(task))
    run("dvc", "cache", "dir", "--local", str(cache), cwd=task)
    run("dvc", "config", "--local", "cache.type", "reflink", cwd=task)
    source = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
    loader = importlib.machinery.SourceFileLoader("native_dvc_removal", str(source))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    monkeypatch.setattr(core, "INSPECT_ENV", {**env, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1"})
    monkeypatch.setattr(core, "workspace_processes", lambda _root: [])
    before = run("git", "worktree", "list", "--porcelain")
    assert core.workspace_remove_check(task)["eligible"] is True
    assert not (task / "dataset").exists()
    run("dvc", "checkout", "dataset.dvc", cwd=task)
    cached = {path: path.read_bytes() for path in cache.rglob("*") if path.is_file()}
    assert core.workspace_remove_check(task)["eligible"] is True
    (task / "dataset/item.txt").write_text("modified\n")
    assert "data_disposition_required" in core.workspace_remove_check(task)["reasons"]
    assert (task / "dataset/item.txt").read_text() == "modified\n"
    assert {path: path.read_bytes() for path in cached} == cached
    assert run("git", "worktree", "list", "--porcelain") == before
    run("dvc", "checkout", "--force", "dataset.dvc", cwd=task)
    (task / "notes.tmp").write_text("unique ignored data\n")
    with (repo / ".git/info/exclude").open("a") as stream:
        stream.write("\nnotes.tmp\n")
    assert "data_disposition_required" in core.workspace_remove_check(task)["reasons"]
    assert (task / "notes.tmp").read_text() == "unique ignored data\n"
    (task / "notes.tmp").unlink()
    (task / "dataset/hidden.tmp").write_text("not versioned by DVC\n")
    assert "data_disposition_required" in core.workspace_remove_check(task)["reasons"]
    assert (task / "dataset/hidden.tmp").read_text() == "not versioned by DVC\n"
