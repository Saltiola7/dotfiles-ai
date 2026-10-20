"""Native DVC 3 metadata qualifies data preservation without pulling or deletion."""
import importlib.machinery
import importlib.util
import os
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from test_managed_dvc import WRAPPER, provision_native_runtime


@pytest.fixture
def preservation_native(tmp_path, monkeypatch):
    repo, home, remote, cache = (tmp_path / name for name in ("repo", "home", "remote", "cache"))
    for path in (repo, home, remote):
        path.mkdir(mode=0o700)
    provision_native_runtime(home)
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "DVC_", "DBSCTR_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), XDG_CACHE_HOME=str(home / "cache"),
               XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"), DVC_NO_ANALYTICS="1")
    def run(*argv):
        if argv[0] == "dvc":
            argv = [sys.executable, "-I", str(WRAPPER), *argv[1:]]
        result = subprocess.run(argv, cwd=repo, env=env, check=True, text=True, capture_output=True, timeout=30)
        return result.stdout
    run("git", "init", "-b", "main")
    run("git", "config", "user.name", "Fixture")
    run("git", "config", "user.email", "fixture@example.invalid")
    run("dvc", "init")
    run("dvc", "remote", "add", "-d", "backup", str(remote))
    run("dvc", "cache", "dir", "--local", str(cache))
    run("dvc", "config", "--local", "cache.type", "reflink")
    source = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
    loader = importlib.machinery.SourceFileLoader("native_preservation", str(source))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    monkeypatch.setattr(core, "INSPECT_ENV", {**env, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1"})
    return core, repo, remote, cache, run


def declared_record(core, repo, run, target, monkeypatch):
    (repo / "outputs.json").write_text(json.dumps({"schema_version": 1, "targets": [target]}))
    run("git", "add", ".")
    run("git", "commit", "-m", "declared synthetic output")
    head = run("git", "rev-parse", "HEAD").strip()
    declaration_digest, _ = core.preservation_declaration(repo, head, "outputs.json")
    _, destination_digest = core.preservation_destination(repo, "backup")
    policy = {"schema_version": 1, "policy_digest": "a" * 64,
              "repository": str(core.common_git_dir(repo).resolve()), "consent": {"schema_version": 1, "uploads": [{
        "declaration_path": "outputs.json", "declaration_sha256": declaration_digest,
        "remote": "backup", "destination_sha256": destination_digest}]}}
    # Synthetic trusted-policy adapter; native backend/status/upload remain real.
    monkeypatch.setattr(core, "preservation_policy_snapshot", lambda root: policy)
    record = {"cycle_id": "fixture", "preservation_policy": policy}
    directory = core.cycle_dir(repo) / "cycles"
    core.managed_directory(repo, directory, create=True)
    return record, directory / "fixture.json", head


def test_native_file_upload_is_targeted_bound_and_independently_requeried(preservation_native, monkeypatch):
    core, repo, remote, _, run = preservation_native
    (repo / "result.txt").write_bytes(b"synthetic file\n")
    run("dvc", "add", "result.txt")
    record, path, head = declared_record(core, repo, run, "result.txt.dvc", monkeypatch)
    args = SimpleNamespace(declaration="outputs.json", remote="backup", upload=False)
    with pytest.raises(RuntimeError, match="remote_objects_not_verified"):
        core.record_declared_dvc_preservation(repo, path, record, args)
    assert "dvc_push" not in record and not list(remote.rglob("*.dir"))
    args.upload = True
    core.record_declared_dvc_preservation(repo, path, record, args)
    manifest_path = core.cycle_dir(repo) / record["dvc_preservation"]["path"]
    assert manifest_path.stat().st_mode & 0o777 == 0o600
    value = json.loads(manifest_path.read_text())
    assert value["head"] == head and value["upload"]["status"] == "succeeded"
    assert value["verification"]["status"] == "verified"
    assert core.verified_preservation_outputs(repo, [record], [repo / "result.txt"])
    # Ask DVC for the exact synthetic remote object URL; never guess cache paths.
    object_path = Path(run("dvc", "get", ".", "result.txt", "--show-url").strip())
    assert object_path.is_relative_to(remote) and object_path.is_file()
    object_path.unlink()
    assert not core.verified_preservation_outputs(repo, [record], [repo / "result.txt"])
    assert (repo / "result.txt").read_bytes() == b"synthetic file\n"


@pytest.mark.parametrize("when", ["during_push", "before_verification"])
def test_upload_attempt_state_survives_interruption(preservation_native, monkeypatch, when):
    core, repo, _, _, run = preservation_native
    (repo / "result.txt").write_bytes(b"synthetic interruption fixture\n")
    run("dvc", "add", "result.txt")
    record, path, _ = declared_record(core, repo, run, "result.txt.dvc", monkeypatch)
    native = core.removal_run
    def interrupted_push(root, argv, **kw):
        if argv[:2] == ["dvc", "push"]:
            raise KeyboardInterrupt("synthetic interruption during push")
        return native(root, argv, **kw)
    def interrupted_verification(*a):
        raise KeyboardInterrupt("synthetic interruption after successful push")
    if when == "during_push":
        monkeypatch.setattr(core, "removal_run", interrupted_push)
    else:
        monkeypatch.setattr(core, "preservation_remote_observation", interrupted_verification)
    with pytest.raises(KeyboardInterrupt):
        core.record_declared_dvc_preservation(repo, path, record,
            SimpleNamespace(declaration="outputs.json", remote="backup", upload=True))
    attempts = list((core.cycle_dir(repo) / "preservation/fixture").glob("*.json"))
    assert len(attempts) == 1
    outcome = json.loads(attempts[0].read_text())["upload"]["status"]
    assert outcome == ("started" if when == "during_push" else "succeeded")


def test_unavailable_directory_fsync_blocks_before_native_upload(preservation_native, monkeypatch):
    core, repo, _, _, run = preservation_native
    (repo / "result.txt").write_bytes(b"synthetic durability fixture\n")
    run("dvc", "add", "result.txt")
    record, path, _ = declared_record(core, repo, run, "result.txt.dvc", monkeypatch)
    native = core.removal_run
    def unavailable(directory):
        raise OSError("synthetic directory fsync unavailable")
    def forbid_push(root, argv, **kw):
        assert argv[:2] != ["dvc", "push"], "upload cannot precede durable attempt confirmation"
        return native(root, argv, **kw)
    monkeypatch.setattr(core, "fsync_directory", unavailable)
    monkeypatch.setattr(core, "removal_run", forbid_push)
    with pytest.raises(RuntimeError, match="durability"):
        core.record_declared_dvc_preservation(repo, path, record,
            SimpleNamespace(declaration="outputs.json", remote="backup", upload=True))


@pytest.mark.parametrize("section", ["upload", "verification"])
def test_unknown_nested_manifest_fields_retain_without_native_query(preservation_native, monkeypatch, section):
    core, repo, _, _, run = preservation_native
    (repo / "result.txt").write_bytes(b"synthetic strict-schema fixture\n")
    run("dvc", "add", "result.txt")
    record, path, _ = declared_record(core, repo, run, "result.txt.dvc", monkeypatch)
    core.record_declared_dvc_preservation(repo, path, record,
        SimpleNamespace(declaration="outputs.json", remote="backup", upload=True))
    manifest_path = core.cycle_dir(repo) / record["dvc_preservation"]["path"]
    value = json.loads(manifest_path.read_text())
    value[section]["unknown"] = True
    value.pop("manifest_digest")
    value["manifest_digest"] = core.continuation_digest(value)
    record["dvc_preservation"]["digest"] = value["manifest_digest"]
    core.private_json(manifest_path, value)
    monkeypatch.setattr(core, "preservation_policy_snapshot", lambda root: pytest.fail("schema must reject before query"))
    assert not core.verified_preservation_outputs(repo, [record], [repo / "result.txt"])


@pytest.mark.parametrize("cold", [False, True])
def test_native_directory_member_absence_never_passes_even_with_present_dir_object(preservation_native, monkeypatch, cold):
    core, repo, remote, cache, run = preservation_native
    (repo / "dataset").mkdir()
    (repo / "dataset/item.txt").write_bytes(b"synthetic directory member\n")
    run("dvc", "add", "dataset")
    record, path, _ = declared_record(core, repo, run, "dataset.dvc", monkeypatch)
    run("dvc", "push", "-r", "backup", "dataset.dvc")
    directory_object = Path(run("dvc", "get", ".", "dataset", "--show-url").strip())
    member = Path(run("dvc", "get", ".", "dataset/item.txt", "--show-url").strip())
    assert directory_object.is_relative_to(remote) and directory_object.is_file()
    assert member.is_relative_to(remote) and member.is_file()
    member.unlink()
    if cold:
        run("dvc", "cache", "dir", "--local", str(cache.parent / "cold-cache"))
    assert directory_object.exists() and not member.exists()
    with pytest.raises(RuntimeError, match="remote_directory_closure_unverified"):
        core.record_declared_dvc_preservation(repo, path, record,
            SimpleNamespace(declaration="outputs.json", remote="backup", upload=False))
    value = json.loads((core.cycle_dir(repo) / record["dvc_preservation"]["path"]).read_text())
    assert value["verification"]["status"] == "unavailable"
    assert "remote_directory_closure_unverified" in value["verification"]["reasons"]
    assert (repo / "dataset/item.txt").read_bytes() == b"synthetic directory member\n"


def test_native_removal_checks_absent_unchanged_modified_and_ignored_data(tmp_path, monkeypatch):
    repo, home, cache, task = (tmp_path / name for name in ("repo", "home", "cache", "task"))
    repo.mkdir()
    home.mkdir()
    provision_native_runtime(home)
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "DVC_", "DBSCTR_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), XDG_CACHE_HOME=str(home / "cache"),
               XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"), DVC_NO_ANALYTICS="1")

    def run(*argv, cwd=repo):
        if argv[0] == "dvc":
            argv = [sys.executable, "-I", str(WRAPPER), *argv[1:]]
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
    native_removal = core.removal_run
    with monkeypatch.context() as unavailable:
        def command_failure(root, argv, **kwargs):
            if argv[0] == "dvc":
                raise core.DVCCommandUnavailable("dvc_command_unavailable")
            return native_removal(root, argv, **kwargs)
        unavailable.setattr(core, "removal_run", command_failure)
        retained = core.workspace_remove_check(task)
        assert "dvc_command_unavailable" in retained["reasons"]
        assert "data_disposition_required" not in retained["reasons"]
        assert retained["eligible"] is False
    run("dvc", "checkout", "dataset.dvc", cwd=task)
    cached = {path: path.read_bytes() for path in cache.rglob("*") if path.is_file()}
    retained = core.workspace_remove_check(task)
    assert retained["eligible"] is False
    assert "remote_directory_closure_unverified" in retained["reasons"]
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
