"""Read-only guest inventory must retain the qualified boot/stop boundary."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from test_openshell_storage_boot import booter, stopped, effects
from test_openshell_storage_create import creator, prepared
from test_openshell_storage_inventory import inventory, mounted, private, owned_run


@pytest.fixture(scope="module")
def guest():
    path = Path(__file__).with_name("probe_openshell_guest_inventory.py")
    assert path.exists(), "Guest inventory absent: expected red-first failure"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("openshell_guest_inventory_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


def observation(guest):
    return {
        "schema_version": 1, "os": "Linux", "arch": "aarch64", "kernel": "6.19.1-1.fc44.aarch64",
        "release": {"id": "fedora", "version_id": "44"}, "uid": 1000,
        "filesystems": [
            {"path": p, "device": 253, "inode": n, "mode": 0o40755,
             "filesystem_type": "btrfs", "bytes_total": 19 * 1024**3,
             "bytes_free": 17 * 1024**3, "bytes_available": 16 * 1024**3,
             "block_size": 4096}
            for p, n in [("/", 256), ("/var/lib", 280)]
        ],
        "tools": {path: path in {"/usr/bin/python3", "/usr/bin/rpm"} for path in guest.TOOLS},
        "packages": [{"name": name, "installed": False, "version": None, "arch": None}
                     for name in guest.PACKAGES],
    }


def test_missing_tools_are_observation_not_build_authority(guest):
    result = guest.parse_inventory(json.dumps(observation(guest)).encode())
    assert result.free_bytes == 16 * 1024**3
    assert result.build_enabled is False
    assert "gcc" in result.missing_packages


@pytest.mark.parametrize("change", [
    "unknown", "duplicate", "bool_uid", "root_uid", "host_os", "wrong_arch", "wrong_release",
    "unknown_filesystem", "alias_mode", "foreign_device", "too_large", "free_over_total",
    "available_over_free", "invalid_block", "duplicate_path", "tool_command", "tool_integer",
    "unknown_package", "duplicate_package", "missing_with_version", "installed_without_version",
    "foreign_package_arch", "control_character", "oversized",
])
def test_closed_guest_inventory_refuses_invalid_facts(guest, change):
    value = observation(guest)
    if change == "unknown": value["command"] = "anything"
    elif change == "bool_uid": value["uid"] = True
    elif change == "root_uid": value["uid"] = 0
    elif change == "host_os": value["os"] = "Darwin"
    elif change == "wrong_arch": value["arch"] = "x86_64"
    elif change == "wrong_release": value["release"]["version_id"] = "45"
    elif change == "unknown_filesystem": value["filesystems"][0]["filesystem_type"] = "nfs"
    elif change == "alias_mode": value["filesystems"][1]["mode"] = 0o120777
    elif change == "foreign_device": value["filesystems"][1]["device"] = 254
    elif change == "too_large": value["filesystems"][0]["bytes_total"] = 21 * 1024**3
    elif change == "free_over_total": value["filesystems"][0]["bytes_free"] = 21 * 1024**3
    elif change == "available_over_free": value["filesystems"][0]["bytes_available"] = 18 * 1024**3
    elif change == "invalid_block": value["filesystems"][0]["block_size"] = 3
    elif change == "duplicate_path": value["filesystems"][1]["path"] = "/"
    elif change == "tool_command": value["tools"]["/bin/sh -c anything"] = True
    elif change == "tool_integer": value["tools"][guest.TOOLS[0]] = 1
    elif change == "unknown_package": value["packages"][0]["name"] = "unknown"
    elif change == "duplicate_package": value["packages"][1] = copy.deepcopy(value["packages"][0])
    elif change == "missing_with_version": value["packages"][0]["version"] = "1.0"
    elif change == "installed_without_version": value["packages"][0]["installed"] = True
    elif change == "foreign_package_arch": value["packages"][0].update(installed=True, version="1.0", arch="x86_64")
    elif change == "control_character": value["kernel"] = "kernel\nextra"
    raw = json.dumps(value).encode()
    if change == "duplicate": raw = raw.replace(b'"uid": 1000', b'"uid": 1000, "uid": 1000')
    if change == "oversized": raw = b" " * (guest.REPORT_LIMIT + 1)
    with pytest.raises(guest.Refusal): guest.parse_inventory(raw)


@pytest.fixture
def inspect_guest(guest, booter, creator, stopped, monkeypatch):
    selection, outputs, calls, state = stopped
    monkeypatch.setattr(guest, "boot", booter)
    monkeypatch.setattr(guest, "create", creator)
    original = creator._run_bounded_command
    response = {"raw": json.dumps(observation(guest)).encode(), "error": None, "after": None}

    def run(argv, **kwargs):
        if len(argv) > 1 and argv[1] == "shell":
            calls.append((argv, kwargs))
            assert state["live"]
            assert argv == [str(creator.LIMA.resolve()), "shell", "--tty=false", "--start=false",
                            "--workdir", "/", "q", "--", "/usr/bin/python3", "-I", "-c", guest.GUEST_SCRIPT]
            assert kwargs["env"] == creator._environment(selection)
            assert 0 < kwargs["timeout"] <= 30 and kwargs["limit"] == 1024**2
            if response["after"]: response["after"]()
            if response["error"]: raise creator.CommandRefusal(response["error"])
            return creator.CommandResult(0, response["raw"], b"")
        return original(argv, **kwargs)
    monkeypatch.setattr(creator, "_run_bounded_command", run)
    return selection, calls, state, response


def test_fixed_guest_inspection_between_start_and_verified_stop(guest, inspect_guest):
    selection, calls, state, _ = inspect_guest
    result = guest.qualify_guest_inventory(selection)
    assert result.lifecycle.stopped_verified and result.guest.build_enabled is False
    assert result.script_sha256 == hashlib.sha256(guest.GUEST_SCRIPT.encode()).hexdigest()
    assert effects(calls) == ["start", "stop"] and not state["live"]
    operations = [argv[1] for argv, _ in calls]
    assert operations.index("start") < operations.index("shell") < operations.index("stop")
    assert operations.count("shell") == 1


@pytest.mark.parametrize("failure", ["timeout", "output_limit", "schema"])
def test_guest_failure_still_verifies_shutdown(guest, booter, inspect_guest, failure):
    selection, calls, _, response = inspect_guest
    if failure == "schema": response["raw"] = b'{"arbitrary": true}'
    else: response["error"] = failure
    with pytest.raises(booter.BootRefusal) as caught: guest.qualify_guest_inventory(selection)
    assert caught.value.stopped_verified and not caught.value.shutdown_uncertain
    assert effects(calls) == ["start", "stop"]


def test_guest_process_replacement_never_stops_replacement(guest, booter, inspect_guest):
    selection, calls, state, response = inspect_guest
    response["after"] = lambda: state.__setitem__("process_stamp", "Tue Nov 3 12:00:01 2026")
    with pytest.raises(booter.BootRefusal) as caught: guest.qualify_guest_inventory(selection)
    assert caught.value.shutdown_uncertain and not caught.value.stop_requested
    assert effects(calls) == ["start"]


def test_cli_does_not_accept_build_or_arbitrary_commands(guest, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["guest", "--selection", "/unused", "--command", "anything"])
    with pytest.raises(SystemExit) as caught: guest.main()
    assert caught.value.code == 2


def script_namespace(guest):
    namespace = {"__name__": "inventory_test"}
    exec(compile(guest.GUEST_SCRIPT, "fixed-guest-inventory", "exec"), namespace)
    return namespace


def test_guest_reads_bound_regular_files_and_release_descriptors(guest, tmp_path):
    namespace = script_namespace(guest)
    file = tmp_path / "release"
    file.write_bytes(b"12345")
    assert namespace["read_file"](str(file), 5) == "12345"
    with pytest.raises(RuntimeError, match="guest_file_limit"):
        namespace["read_file"](str(file), 4)
    link = tmp_path / "alias"
    link.symlink_to(file)
    with pytest.raises(OSError): namespace["read_file"](str(link), 10)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(RuntimeError, match="guest_file_type"):
        namespace["read_file"](str(fifo), 10)


def test_expired_guest_deadline_never_spawns_query(guest):
    namespace = script_namespace(guest)
    namespace["DEADLINE"] = time.monotonic() - 1
    def forbidden(*args, **kwargs):
        raise AssertionError("expired inspection spawned a process")
    namespace["subprocess"] = SimpleNamespace(Popen=forbidden, DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE)
    with pytest.raises(RuntimeError, match="guest_deadline"):
        namespace["query"]("python3")


@pytest.mark.parametrize("kind", ["installed", "missing", "query_error", "overflow", "timeout"])
def test_guest_package_queries_are_bounded_owned_children(guest, kind):
    namespace = script_namespace(guest)
    children = []
    package = "python3"
    snippets = {
        "installed": "import sys;sys.stdout.write('python3\\t3.14.0-1.fc44\\taarch64\\n')",
        "missing": "import sys;sys.stdout.write('package python3 is not installed\\n');sys.exit(1)",
        "query_error": "import sys;sys.stderr.write('database unavailable');sys.exit(1)",
        "overflow": "import sys;sys.stdout.write('x'*8193)",
        "timeout": "import time;time.sleep(10)",
    }
    def spawn(args, **kwargs):
        assert args == ["/usr/bin/rpm", "-q", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\n", package]
        assert kwargs["env"] == {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "HOME": "/nonexistent"}
        assert kwargs["start_new_session"] is True
        child = subprocess.Popen([sys.executable, "-I", "-c", snippets[kind]], **kwargs)
        children.append(child)
        return child
    namespace["subprocess"] = SimpleNamespace(Popen=spawn, DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE)
    if kind == "timeout": namespace["DEADLINE"] = time.monotonic() + 0.1
    if kind in {"installed", "missing"}:
        result = namespace["query"](package)
        assert result["installed"] == (kind == "installed")
    else:
        with pytest.raises(RuntimeError): namespace["query"](package)
    assert children and all(p.poll() is not None and p.stdout.closed and p.stderr.closed for p in children)
