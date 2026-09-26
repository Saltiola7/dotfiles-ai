"""Synthetic routing/transaction regressions; not native qualification evidence."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import copy

import pytest

BIN = Path(__file__).parents[1] / "dot_local/bin"


@pytest.fixture
def manager():
    return runpy.run_path(str(BIN / "executable_codex-requalify"), run_name="test_requalification")


def test_only_exact_selected_hook_pair_changes(manager):
    old = {"producer": {"path": "/private/producer"}, "conversation_id": "root-1"}
    command = "/usr/bin/python3 /private/producer hook --conversation root-1"
    before = {"hooks": {event: [{"matcher": matcher, "hooks": [
        {"type": "command", "command": command, "timeout": 15}]}]
        for event, matcher in (("PreToolUse", "^(Bash|apply_patch|Edit|Write|mcp__.*)$"),
                               ("PostToolUse", "^Bash$"))}}
    before["hooks"]["Stop"] = [{"hooks": [{"command": "unrelated"}]}]
    raw = json.dumps(before).encode()
    after = json.loads(manager["fixture_hooks"](raw, old, Path("/fixture/producer")))
    assert json.loads(raw) == before
    assert after["hooks"]["Stop"] == before["hooks"]["Stop"]
    for event in ("PreToolUse", "PostToolUse"):
        assert after["hooks"][event][0]["matcher"] == before["hooks"][event][0]["matcher"]
        assert "root-1" in after["hooks"][event][0]["hooks"][0]["command"]
        assert "/fixture/producer" in after["hooks"][event][0]["hooks"][0]["command"]
    before["hooks"]["PreToolUse"].append(before["hooks"]["PreToolUse"][0])
    with pytest.raises(ValueError):
        manager["fixture_hooks"](json.dumps(before).encode(), old, Path("/fixture/producer"))


def test_hook_compare_exchange_preserves_preimages_and_refuses_drift(manager, tmp_path):
    hooks = tmp_path / "hooks.json"
    hooks.write_bytes(b"before")
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    manager["replace_hooks"](hooks, b"before", b"fixture", evidence, "install")
    assert hooks.read_bytes() == b"fixture"
    receipt = json.loads((evidence / "install.intent.json").read_text())
    assert Path(receipt["exchange"]).read_bytes() == b"before"
    hooks.write_bytes(b"concurrent edit")
    with pytest.raises(ValueError, match="drift"):
        manager["replace_hooks"](hooks, b"fixture", b"before", evidence, "restore")
    assert hooks.read_bytes() == b"concurrent edit"


def test_racing_edit_is_retained_not_overwritten(manager, tmp_path, monkeypatch):
    hooks = tmp_path / "hooks.json"
    hooks.write_bytes(b"before")
    swap = manager["exchange_files"]
    def race(left, right):
        right.write_bytes(b"racing edit")
        swap(left, right)
    monkeypatch.setitem(manager["replace_hooks"].__globals__, "exchange_files", race)
    with pytest.raises(ValueError, match="drift"):
        manager["replace_hooks"](hooks, b"before", b"fixture", tmp_path, "install")
    receipt = json.loads((tmp_path / "install.intent.json").read_text())
    assert Path(receipt["exchange"]).read_bytes() == b"racing edit"
    assert not (tmp_path / "install.complete.json").exists()


def test_fixed_route_never_falls_back_to_production(tmp_path, monkeypatch):
    api = runpy.run_path(str(BIN / "executable_codex-continuation"))
    parent = tmp_path / ".local/state/dbsctr/codex"
    parent.mkdir(parents=True, mode=0o700)
    (parent / "qualification").mkdir(mode=0o700)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with pytest.raises(api["NativeIdentityError"]):
        api["configured_deployment"]()
    assert not (parent / "native").exists()


def test_broken_qualification_link_fails_closed(tmp_path, monkeypatch):
    api = runpy.run_path(str(BIN / "executable_codex-continuation"))
    parent = tmp_path / ".local/state/dbsctr/codex"
    parent.mkdir(parents=True, mode=0o700)
    (parent / "qualification").symlink_to(tmp_path / "absent")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with pytest.raises((api["NativeIdentityError"], OSError)):
        api["configured_deployment"]()


@pytest.fixture
def route(tmp_path, monkeypatch):
    api = runpy.run_path(str(BIN / "executable_codex-continuation"))
    parent = tmp_path / ".local/state/dbsctr/codex"
    parent.mkdir(parents=True, mode=0o700)
    qualification = tmp_path / "external-fixture"
    qualification.mkdir(mode=0o700)
    (parent / "qualification").symlink_to(qualification)
    hooks = tmp_path / "hooks.json"
    hooks.write_bytes(b"installed hooks")
    hooks.chmod(0o644)  # Existing public-readable native config is not a journal.
    production = {"conversation_id": "root-1", "conversation_home": str(tmp_path),
                  "native_home": str(tmp_path), "native_executable": {"path": "/native", "sha256": "a" * 64},
                  "producer": {"path": "/production/producer"}, "core": {"path": "/production/core"},
                  "target": {"common_git_dir": "/production/.git"}}
    candidate = copy.deepcopy(production)
    candidate["native_executable"]["sha256"] = "b" * 64
    candidate["target"]["common_git_dir"] = "/fixture/.git"
    candidate["producer"]["path"] = str(qualification / "executable_codex-continuation")
    candidate["core"]["path"] = str(qualification / "executable_dbsctrctl")
    def save(path, value):
        path.write_text(json.dumps(value))
        path.chmod(0o600)
    save(parent / "selected.json", production)
    after = hashlib.sha256(hooks.read_bytes()).hexdigest()
    save(qualification / "route.json", {"schema_version": 1,
         "production_sha256": hashlib.sha256((parent / "selected.json").read_bytes()).hexdigest(),
         "deployment_digest": api["canonical_digest"](candidate), "hooks_after_sha256": after})
    save(qualification / "install.complete.json", {"after_sha256": after})
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    namespace = api["configured_deployment"].__globals__
    monkeypatch.setitem(namespace, "__file__", str(qualification / "executable_codex-continuation"))
    monkeypatch.setitem(namespace, "load_deployment", lambda path: candidate)
    monkeypatch.setitem(namespace, "pinned_file", lambda value: None)
    return api, parent, qualification, candidate, hooks


def test_qualified_route_selects_only_fixed_fixture_journal(route):
    api, parent, qualification, candidate, hooks = route
    path, actual = api["configured_deployment"]()
    assert path == qualification / "selected.json"
    assert actual == candidate
    assert api["configured_store"](path).path == qualification / "native/native.sqlite3"
    assert not (parent / "native").exists()


@pytest.mark.parametrize("fault", ["hooks", "production", "receipt", "restored", "other_conversation", "same_repository", "same_pin"])
def test_qualification_refuses_drift_or_missing_install_evidence(route, fault):
    api, parent, qualification, candidate, hooks = route
    if fault == "hooks":
        hooks.write_bytes(b"other edit")
    elif fault == "production":
        (parent / "selected.json").write_text("{}")
    elif fault == "receipt":
        (qualification / "install.complete.json").unlink()
    elif fault == "restored":
        (qualification / "restored.json").write_text("{}")
    else:
        if fault == "other_conversation":
            candidate["conversation_id"] = "other-root"
        elif fault == "same_repository":
            candidate["target"]["common_git_dir"] = "/production/.git"
        else:
            candidate["native_executable"]["sha256"] = "a" * 64
        value = json.loads((qualification / "route.json").read_text())
        value["deployment_digest"] = api["canonical_digest"](candidate)
        (qualification / "route.json").write_text(json.dumps(value))
    with pytest.raises((api["NativeIdentityError"], OSError)):
        api["configured_deployment"]()


def test_production_producer_refuses_while_lane_exists(route, monkeypatch):
    api, parent, qualification, candidate, hooks = route
    monkeypatch.setitem(api["configured_deployment"].__globals__, "__file__", "/production/producer")
    with pytest.raises(api["NativeIdentityError"], match="qualification_active"):
        api["configured_deployment"]()


@pytest.mark.parametrize("interruption", ["before_exchange", "after_exchange"])
def test_interrupted_restore_recovers_exact_images_only(manager, route, monkeypatch, interruption):
    api, parent, qualification, candidate, hooks = route
    production_before = (parent / "selected.json").read_bytes()
    hooks_before, hooks_after = b"original hooks", hooks.read_bytes()
    for name, raw in (("production.before.json", production_before), ("hooks.before.json", hooks_before),
                      ("hooks.fixture.json", hooks_after)):
        (qualification / name).write_bytes(raw)
        (qualification / name).chmod(0o600)
    route_path = qualification / "route.json"
    value = json.loads(route_path.read_text())
    value["hooks_before_sha256"] = hashlib.sha256(hooks_before).hexdigest()
    route_path.write_text(json.dumps(value))
    namespace = manager["change_route"].__globals__
    monkeypatch.setitem(namespace, "load_api", lambda _: api)
    original = namespace["exchange_files" if interruption == "before_exchange" else "json_new"]
    def interrupt(*arguments):
        if interruption == "before_exchange" or arguments[0].name == "restore.complete.json":
            raise InterruptedError("test interruption")
        return original(*arguments)
    key = "exchange_files" if interruption == "before_exchange" else "json_new"
    monkeypatch.setitem(namespace, key, interrupt)
    with pytest.raises(InterruptedError):
        manager["change_route"]("restore", parent, parent / "qualification")
    assert not (qualification / "restored.json").exists()
    monkeypatch.setitem(namespace, key, original)
    manager["change_route"]("recover", parent, parent / "qualification")
    assert hooks.read_bytes() == hooks_before
    assert (qualification / "restored.json").exists()
    assert (parent / "selected.json").read_bytes() == production_before


@pytest.mark.parametrize("link", ["symlink", "hardlink"])
def test_unsafe_hook_path_refuses_without_modifying_target(manager, tmp_path, link):
    target = tmp_path / "target"
    target.write_bytes(b"preserve")
    hooks = tmp_path / "hooks.json"
    if link == "symlink":
        hooks.symlink_to(target)
    else:
        os.link(target, hooks)
    with pytest.raises(ValueError, match="unsafe_file"):
        manager["replace_hooks"](hooks, b"preserve", b"changed", tmp_path, "install")
    assert target.read_bytes() == b"preserve"
