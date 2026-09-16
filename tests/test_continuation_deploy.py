import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def helper():
    loader = importlib.machinery.SourceFileLoader(
        "continuation_deploy", str(ROOT / "dot_local/bin/executable_opencode-continuation-deploy")
    )
    specification = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(specification)
    loader.exec_module(module)
    return module


def test_config_projection_preserves_unrelated_values():
    module = helper()
    before = {"provider": {"private": {"value": "unchanged"}}, "permission": {"edit": "deny"}}
    after = {**before, "references": {"dbsctr-worktrees": {"path": "/fixture/worktrees"}},
             "permission": {**before["permission"], "dbsctr_preflight": "allow"}}
    assert module.allowed_config_delta(before, after)
    assert not module.allowed_config_delta(before, {**after, "provider": {}})
    assert not module.allowed_config_delta(before, {**after, "permission": {"edit": "allow"}})


def test_deployment_targets_are_explicit_and_ordered():
    module = helper()
    paths = list(module.TARGETS)
    assert len(paths) == 11
    assert paths[-1] == ".config/opencode/opencode.json"
    assert paths.index(".config/opencode/tools/dbsctr.ts") < paths.index(".config/opencode/plugins/continuation.ts")
    assert all(not name.endswith(".sh") for name in paths)


def test_atomic_restore_preserves_bytes_modes_and_refuses_links(tmp_path):
    module = helper()
    target = tmp_path / "target"
    module.atomic_file(target, b"original", 0o600)
    assert target.read_bytes() == b"original"
    assert target.stat().st_mode & 0o777 == 0o600
    other = tmp_path / "other"
    other.write_text("untouched")
    target.unlink()
    target.symlink_to(other)
    with pytest.raises(RuntimeError, match="unsafe_target"):
        module.atomic_file(target, b"replacement", 0o600)
    assert other.read_text() == "untouched"


def test_rollback_refuses_later_drift(tmp_path):
    module = helper()
    home, backup = tmp_path / "home", tmp_path / "backup"
    home.mkdir()
    backup.mkdir(mode=0o700)
    name = ".config/opencode/opencode.json"
    target = home / name
    target.parent.mkdir(parents=True)
    target.write_bytes(b"later edit")
    (backup / "0").write_bytes(b"prior")
    receipt = {"schema_version": 1, "source_commit": "a" * 40, "state": "applied", "targets": {
        name: {"before": module.digest(b"prior"), "after": module.digest(b"installed"),
               "mode": 0o600, "after_mode": 0o600, "backup": "0"}}}
    module.save_receipt(backup / "receipt.json", receipt)
    with pytest.raises(RuntimeError, match="rollback_drift"):
        module.rollback(home, backup)
    assert target.read_bytes() == b"later edit"


def test_rollback_restores_exact_prior_target(tmp_path):
    module = helper()
    home, backup = tmp_path / "home", tmp_path / "backup"
    home.mkdir()
    backup.mkdir(mode=0o700)
    name = ".config/opencode/opencode.json"
    module.atomic_file(home / name, b"installed", 0o600)
    module.atomic_file(backup / "0", b"prior", 0o600)
    module.save_receipt(backup / "receipt.json", {
        "schema_version": 1, "source_commit": "a" * 40, "state": "applied", "targets": {
            name: {"before": module.digest(b"prior"), "after": module.digest(b"installed"),
                   "mode": 0o600, "after_mode": 0o600, "backup": "0"}}})
    assert module.rollback(home, backup)["state"] == "rolled_back"
    assert (home / name).read_bytes() == b"prior"


def test_failed_apply_rolls_back_only_owned_targets(tmp_path, monkeypatch, capsys):
    module = helper()
    home, source = tmp_path / "home", tmp_path / "source"
    home.mkdir()
    source.mkdir()
    names = [".local/bin/dbsctrctl", ".config/opencode/opencode.json"]
    targets = {}
    for index, name in enumerate(names):
        module.atomic_file(home / name, b"prior", 0o600)
        targets[name] = {"before": module.digest(b"prior"), "after": module.digest(b"installed"),
                         "mode": 0o600, "after_mode": 0o600, "backup": str(index)}
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(module, "preview", lambda *_args: (
        {"schema_version": 1, "source_commit": "a" * 40, "state": "preview", "targets": targets},
        {name: b"prior" for name in names}))
    monkeypatch.setattr(module, "source_identity", lambda _source: "a" * 40)
    calls = []

    def execute(argv, **_kwargs):
        calls.append(argv)
        if len(calls) == 2:
            raise RuntimeError("command_failed")
        assert "--exclude" in argv and "scripts" in argv
        module.atomic_file(Path(argv[-1]), b"installed", 0o600)
        return b""

    monkeypatch.setattr(module, "execute", execute)
    monkeypatch.setattr(sys, "argv", ["deploy", "apply", "--source", str(source)])
    with pytest.raises(SystemExit):
        module.main()
    assert json.loads(capsys.readouterr().out)["reason"] == "apply_failed_rolled_back"
    assert all((home / name).read_bytes() == b"prior" for name in names)


def test_preview_refuses_unknown_static_target(tmp_path, monkeypatch):
    module = helper()
    home = tmp_path / "home"
    module.atomic_file(home / ".local/bin/dbsctrctl", b"operator edit", 0o755)
    monkeypatch.setattr(module, "source_identity", lambda _source: "a" * 40)
    monkeypatch.setattr(module, "known_blobs", lambda _source: {name: [] for name in module.TARGETS})

    def execute(argv, **_kwargs):
        if "managed" in argv:
            return b".local/bin/dbsctrctl\n.config/opencode/opencode.json\n"
        if "cat" in argv:
            return b"new source"
        return b"b" * 40 + b"\n"

    monkeypatch.setattr(module, "execute", execute)
    with pytest.raises(RuntimeError, match="unrecognized_local_edit"):
        module.preview(tmp_path, tmp_path / "config", home)
    assert (home / ".local/bin/dbsctrctl").read_bytes() == b"operator edit"


def test_apply_creates_missing_parent_without_reconciling_existing_dirs(tmp_path, monkeypatch, capsys):
    module = helper()
    home, source = tmp_path / "home", tmp_path / "source"
    home.mkdir()
    source.mkdir()
    name = ".local/share/opencode-continuation/native_probe.py"
    target = {"before": None, "after": module.digest(b"new"), "mode": None, "after_mode": 0o644, "backup": "0"}
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(module, "source_identity", lambda _source: "a" * 40)
    monkeypatch.setattr(module, "preview", lambda *_args: (
        {"schema_version": 1, "source_commit": "a" * 40, "state": "preview", "targets": {name: target}},
        {name: None}))

    def execute(argv, **_kwargs):
        destination = Path(argv[-1])
        assert destination.parent.is_dir()
        destination.write_bytes(b"new")
        destination.chmod(0o644)
        return b""

    monkeypatch.setattr(module, "execute", execute)
    monkeypatch.setattr(sys, "argv", ["deploy", "apply", "--source", str(source)])
    module.main()
    assert json.loads(capsys.readouterr().out)["state"] == "applied"


def test_field_projection_preserves_guest_drift_and_is_idempotent():
    module = helper()
    before = {"provider": {"local": {"value": "retain"}}, "permission": {"edit": "deny"},
              "agent": {"build": {"permission": {"task": "ask"}}}}
    desired = {"provider": {"local": {"value": "unrelated change"}}}
    for path in module.CONFIG_FIELDS:
        parent = desired
        for key in path[:-1]:
            parent = parent.setdefault(key, {})
        parent[path[-1]] = {"path": "/fixture/worktrees"} if path[0] == "references" else "ask"
    result = module.project_config(json.dumps(before).encode(), json.dumps(desired).encode())
    value = json.loads(result)
    assert value["provider"] == before["provider"]
    assert value["permission"]["edit"] == "deny"
    assert value["agent"]["build"]["permission"]["task"] == "ask"
    assert module.allowed_config_delta(before, value)
    assert module.project_config(result, json.dumps(desired).encode()) == result
