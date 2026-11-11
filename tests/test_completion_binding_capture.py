"""Input capture invariants use real temporary files/Git, never live runtimes."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_completion_evidence_policy import core


@pytest.fixture
def source(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("value = 1\n")
    (tmp_path / "uv.lock").write_text("fixture-lock\n")
    (tmp_path / ".gitignore").write_text("ignored/\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=tmp_path, check=True)
    return tmp_path


def declaration():
    return {"authority": "fixture", "argv": [sys.executable, "-c", "print('passed')"],
            "inputs": ["src"], "environment": ["PROJECT_MODE"],
            "toolchain_paths": ["uv.lock"], "scope_complete": True}


KEY = {"key_id": "a" * 32, "key": b"k" * 32}


def test_capture_ignores_unrelated_files_but_detects_new_input_population(core, source):
    before = core.evidence_binding_snapshot(source, declaration(), KEY)
    (source / "unrelated.txt").write_text("outside declared inputs\n")
    assert core.evidence_binding_snapshot(source, declaration(), KEY) == before
    (source / "src/added.py").write_text("added = True\n")
    assert core.evidence_binding_snapshot(source, declaration(), KEY) != before


@pytest.mark.parametrize("change", ["blob", "mode", "environment", "ignore", "toolchain"])
def test_relevant_input_change_breaks_equivalence(core, source, monkeypatch, change):
    monkeypatch.delenv("PROJECT_MODE", raising=False)
    before = core.evidence_binding_snapshot(source, declaration(), KEY)
    if change == "blob":
        (source / "src/main.py").write_text("value = 2\n")
    elif change == "mode":
        (source / "src/main.py").chmod(0o755)
    elif change == "environment":
        monkeypatch.setenv("PROJECT_MODE", "")
    elif change == "ignore":
        (source / ".gitignore").write_text("ignored/\nnew-ignore/\n")
    else:
        (source / "uv.lock").write_text("changed-lock\n")
    assert core.evidence_binding_snapshot(source, declaration(), KEY) != before


@pytest.mark.parametrize("kind", ["symlink_file", "symlink_parent", "special_file", "secret", "ignored"])
def test_unsafe_dependency_capture_is_unavailable(core, source, kind):
    selected = declaration()
    if kind == "symlink_file":
        (source / "src/link.py").symlink_to("main.py")
    elif kind == "symlink_parent":
        (source / "alias").symlink_to("src", target_is_directory=True)
        selected["inputs"] = ["alias/main.py"]
    elif kind == "special_file":
        os.mkfifo(source / "src/fifo")
    elif kind == "secret":
        (source / "src/.env").write_text("not-a-real-secret\n")
        selected["inputs"] = ["src/.env"]
    else:
        (source / "ignored").mkdir()
        (source / "ignored/data.txt").write_text("ignored\n")
        selected["inputs"] = ["ignored"]
    with pytest.raises(RuntimeError):
        core.evidence_binding_snapshot(source, selected, KEY)


def test_tracked_absence_keeps_predecessor_identity_after_staging(core, source):
    selected = declaration()
    selected["inputs"] = ["src/main.py"]
    (source / "src/main.py").unlink()
    before = core.evidence_binding_snapshot(source, selected, KEY)
    subprocess.run(["git", "add", "src/main.py"], cwd=source, check=True)
    assert core.evidence_binding_snapshot(source, selected, KEY) == before
    item = before["inputs"][0]
    assert item["mode"] is None and item["sha256"] is None and item["predecessor"]["mode"] == "100644"


def test_environment_fingerprints_are_keyed_and_do_not_retain_values(core, source, monkeypatch):
    sentinel = "PRIVATE_ENVIRONMENT_SENTINEL"
    monkeypatch.setenv("PROJECT_MODE", sentinel)
    first = core.evidence_binding_snapshot(source, declaration(), KEY)
    second = core.evidence_binding_snapshot(source, declaration(), {"key_id": "b" * 32, "key": b"b" * 32})
    assert first["environment"]["values_hmac"] != second["environment"]["values_hmac"]
    assert sentinel not in repr(first)


def test_toolchain_symlink_cannot_select_secret_target(core, source):
    (source / ".env").write_text("synthetic-private-value\n")
    (source / "tool-config").symlink_to(".env")
    selected = declaration()
    selected["toolchain_paths"] = ["tool-config"]
    with pytest.raises(RuntimeError, match="secret paths"):
        core.evidence_binding_snapshot(source, selected, KEY)


def test_environment_unsupported_encoding_is_unavailable(core, source, monkeypatch):
    monkeypatch.setenv("PROJECT_MODE", "unsupported-\udcff")
    with pytest.raises(RuntimeError, match="capture unavailable"):
        core.evidence_binding_snapshot(source, declaration(), KEY)


def test_absence_stays_equivalent_after_unrelated_history_and_gate_commit(core, source):
    baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    (source / "notes.txt").write_text("unrelated\n")
    subprocess.run(["git", "add", "notes.txt"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "unrelated"], cwd=source, check=True)
    selected = declaration()
    selected["inputs"] = ["src/main.py"]
    (source / "src/main.py").unlink()
    before = core.evidence_binding_snapshot(source, selected, KEY, baseline=baseline)
    subprocess.run(["git", "add", "src/main.py"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "delete validated file"], cwd=source, check=True)
    assert core.evidence_binding_snapshot(source, selected, KEY, baseline=baseline) == before
