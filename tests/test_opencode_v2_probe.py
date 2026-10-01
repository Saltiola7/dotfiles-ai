"""Behavioral checks for isolated, partial V2 CLI evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

import probe_opencode_v2 as probe


def candidate(tmp_path: Path, behavior: str = "") -> Path:
    binary = tmp_path / "candidate"
    binary.write_text(f"#!{sys.executable}\n" + '''
import os, sys, time
from pathlib import Path
args = sys.argv[1:]
assert not any(key in os.environ for key in (
    "OPENAI_API_KEY", "OPENCODE_DB", "OPENCODE_SERVER", "HERDR_ENV", "NODE_OPTIONS"))
assert Path.cwd() in Path(os.environ["HOME"]).parents
''' + behavior + '''
if args == ["--version"]:
    print("opencode v2.0.21")
elif args == ["--help"]:
    print("--standalone --server --auto --session, -s")
elif args == ["debug", "--help"]:
    print("agents config paths")
elif args == ["session", "--help"]:
    print("list export import")
elif args == ["service", "--help"]:
    print("start stop restart status")
elif args == ["debug", "paths", "db"]:
    print(Path(os.environ["XDG_DATA_HOME"]) / "opencode/opencode.db")
else:
    raise AssertionError("unapproved command")
''')
    binary.chmod(0o700)
    return binary


def invoke(binary: Path, root: Path, **overrides):
    values = {"binary": binary, "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
              "expected_version": "2.0.21", "scratch": root}
    return probe.probe(**(values | overrides))


def test_surface_success_is_isolated_and_not_migration_readiness(tmp_path, monkeypatch):
    for key in ("OPENAI_API_KEY", "OPENCODE_DB", "OPENCODE_SERVER", "HERDR_ENV", "NODE_OPTIONS"):
        monkeypatch.setenv(key, "private-parent-secret")
    result = invoke(candidate(tmp_path), tmp_path)
    assert result["status"] == "passed"
    assert set(result["checks"].values()) == {"passed"}
    assert all(result[key] == "unavailable" for key in ("continuation", "migration", "deployment"))
    assert str(tmp_path) not in json.dumps(result)
    assert not list(tmp_path.glob("opencode-v2-*"))


@pytest.mark.parametrize(("behavior", "reason"), [
    ('print("private-child-secret"); sys.exit(9)\n', "command_failed"),
    ('if args == ["--version"]: print("opencode v1.18.34"); sys.exit()\n', "version_mismatch"),
    ('if args == ["--help"]: print("--standalone not--server --auto --session"); sys.exit()\n', "help_contract"),
    ('if args == ["debug", "paths", "db"]: print("/private/wrong.db"); sys.exit()\n', "database_path"),
    ('if args == ["--version"]: Path(__file__).write_text(Path(__file__).read_text() + "\\n")\n', "candidate_mismatch"),
    ('if args == ["debug", "paths", "db"]:\n'
     '    p = Path(os.environ["XDG_DATA_HOME"]) / "opencode/opencode.db"\n'
     '    p.parent.mkdir(); p.touch()\n', "database_path"),
])
def test_contract_failures_are_sanitized(tmp_path, behavior, reason):
    result = invoke(candidate(tmp_path, behavior), tmp_path)
    assert result["status"] == "failed" and result["reason"] == reason
    assert "private-child-secret" not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)


def test_input_rejection_never_executes_candidate(tmp_path):
    marker = tmp_path / "executed"
    binary = candidate(tmp_path, f"Path({str(marker)!r}).touch()\n")
    assert invoke(binary, tmp_path, sha256="0" * 64)["reason"] == "candidate_mismatch"
    link = tmp_path / "link"
    link.symlink_to(binary)
    assert invoke(link, tmp_path)["reason"] == "invalid_input"
    assert invoke(binary, tmp_path, expected_version="2.0.21-beta")["candidate"] is None
    assert invoke(binary, tmp_path, scratch=tmp_path / "missing")["reason"] == "invalid_input"
    assert not marker.exists()


def test_unsafe_scratch_is_rejected(tmp_path):
    binary = candidate(tmp_path)
    scratch = tmp_path / "unsafe"
    scratch.mkdir(mode=0o777)
    scratch.chmod(0o777)
    assert invoke(binary, scratch)["reason"] == "invalid_input"
    link = tmp_path / "scratch-link"
    link.symlink_to(tmp_path)
    assert invoke(binary, link)["reason"] == "invalid_input"


@pytest.mark.parametrize(("behavior", "reason"), [
    ("time.sleep(5)\n", "timeout"),
    ('os.write(1, b"x" * 140000)\n', "output_limit"),
    ('os.write(2, b"x" * 140000)\n', "output_limit"),
    ('os.write(1, b"x" * 70000); os.write(2, b"x" * 70000)\n', "output_limit"),
])
def test_resource_bounds(tmp_path, monkeypatch, behavior, reason):
    monkeypatch.setattr(probe, "TIMEOUT_SECONDS", 0.2)
    result = invoke(candidate(tmp_path, behavior), tmp_path)
    assert result["reason"] == reason
    assert result["checks"]["root_help"] == "not_run"
    assert not list(tmp_path.glob("opencode-v2-*"))


def test_malformed_cli_does_not_echo_arguments():
    result = subprocess.run([sys.executable, str(Path(probe.__file__)),
                             "--unknown-private-secret"], capture_output=True, text=True)
    assert result.returncode == 1 and result.stderr == ""
    value = json.loads(result.stdout)
    assert value["reason"] == "invalid_input" and value["candidate"] is None
    assert "private-secret" not in result.stdout


def test_fifo_candidate_cannot_block_input_validation(tmp_path):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    result = subprocess.run([sys.executable, str(Path(probe.__file__)),
                             "--binary", str(fifo), "--sha256", "0" * 64,
                             "--expected-version", "2.0.21", "--scratch", str(tmp_path)],
                            capture_output=True, text=True, timeout=2)
    assert result.returncode == 1
    assert json.loads(result.stdout)["reason"] == "invalid_input"


def test_timeout_stops_owned_descendants(tmp_path, monkeypatch):
    marker = tmp_path / "survived"
    action = f"import time; from pathlib import Path; time.sleep(.8); Path({str(marker)!r}).touch()"
    behavior = f"import subprocess\nsubprocess.Popen([sys.executable, '-c', {action!r}])\ntime.sleep(5)\n"
    monkeypatch.setattr(probe, "TIMEOUT_SECONDS", 0.2)
    assert invoke(candidate(tmp_path, behavior), tmp_path)["reason"] == "timeout"
    time.sleep(1.2)
    assert not marker.exists()


def test_cleanup_refuses_substituted_root(tmp_path):
    victim = tmp_path / "victim"
    victim.mkdir()
    marker = victim / "keep"
    marker.write_text("keep")
    behavior = ("root = Path.cwd()\nroot.rename(root.with_suffix('.saved'))\n"
                f"root.symlink_to({str(victim)!r}, target_is_directory=True)\n")
    result = invoke(candidate(tmp_path, behavior), tmp_path)
    assert result["status"] == "failed" and result["reason"] == "cleanup_failed"
    assert marker.read_text() == "keep"
