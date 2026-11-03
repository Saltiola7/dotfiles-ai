"""Create-only storage admission; every native process is replaced by a boundary fake."""
from __future__ import annotations

from dataclasses import replace
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import sys

import pytest

from test_openshell_storage_inventory import inventory, mounted, private, owned_run


@pytest.fixture(scope="module")
def creator():
    path = Path(__file__).with_name("probe_openshell_storage_create.py")
    assert path.exists(), "Create-only runner absent: expected red-first failure"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("openshell_create_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


@pytest.fixture
def prepared(creator, inventory, mounted, monkeypatch, tmp_path):
    storage, _ = mounted
    monkeypatch.setattr(creator, "inventory", inventory)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name in ("limactl", "qemu-img"):
        target = binaries / name
        target.write_bytes(b"trusted executable " + name.encode())
        target.chmod(0o755)
        monkeypatch.setattr(creator, "LIMA" if name == "limactl" else "QEMU", target)
    recipe = creator.RECIPE.read_bytes()
    private(storage.run_root / "input/lima.yaml", recipe)
    selection = creator.CreateSelection(storage, hashlib.sha256(creator.LIMA.read_bytes()).hexdigest(),
                                         hashlib.sha256(creator.QEMU.read_bytes()).hexdigest(),
                                         hashlib.sha256(recipe).hexdigest())
    disk = storage.runtime_path / "q/disk"
    config = {
        "os": "Linux", "vmType": "vz", "arch": "aarch64", "cpus": 4, "memory": "8GiB", "disk": "20GiB",
        "vmOpts": {"vz": {"diskImageFormat": "raw", "rosetta": {"enabled": False, "binfmt": False}}},
        "images": [{"location": creator.IMAGE_URL, "arch": "aarch64", "digest": creator.IMAGE_DIGEST}],
        "mountType": "virtiofs", "mounts": [], "additionalDisks": [],
        "containerd": {"system": False, "user": False},
        "ssh": {"loadDotSSHPubKeys": False, "forwardAgent": False, "forwardX11": False},
        "propagateProxyEnv": False,
        "portForwards": [{"guestIP": "0.0.0.0", "proto": "any", "ignore": True}],
        "provision": [{"mode": "system", "script": creator.PROVISION}],
    }
    lima = {"name": "q", "dir": str(disk.parent), "status": "Stopped", "vmType": "vz", "arch": "aarch64",
            "limaVersion": "2.2.1", "disk": 20 * 1024**3, "cpus": 4, "memory": 8 * 1024**3, "config": config}
    apple = {"Image Format": "RAW", "Size Info": {"Total Bytes": 20 * 1024**3},
             "Encryption Info": {"Is Encrypted": 0}}
    child = {"children": [], "virtual-size": 20 * 1024**3, "filename": str(disk), "format": "file",
             "actual-size": 0, "format-specific": {"type": "file", "data": {}}, "dirty-flag": False}
    qemu = {"children": [{"name": "file", "info": child}], "virtual-size": 20 * 1024**3,
            "filename": str(disk), "format": "raw", "actual-size": 0, "dirty-flag": False}
    outputs = {"lima": lima, "apple": apple, "qemu": qemu}
    calls = []

    def command(argv, **kwargs):
        calls.append((argv, kwargs))
        lock = os.open(storage.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(lock)
        assert kwargs["cwd"] == storage.run_root
        assert kwargs["env"]["HOME"] == str(storage.home_path)
        assert kwargs["env"]["TMPDIR"] == str(storage.cache_path / "_tmp")
        assert kwargs["env"]["XDG_CACHE_HOME"] == str(storage.cache_path / "_xdg")
        assert kwargs["limit"] == 1024**2 and 0 < kwargs["timeout"] <= 1800
        if argv == [str(creator.LIMA.resolve()), "--version"]:
            return creator.CommandResult(0, b"limactl version 2.2.1\n", b"")
        if argv == [str(creator.QEMU.resolve()), "--version"]:
            return creator.CommandResult(0, b"qemu-img version 11.1.2\nCopyright QEMU\n", b"")
        if argv == [str(creator.LIMA.resolve()), "create", "--tty=false", "--name=q", str(storage.run_root / "input/lima.yaml")]:
            private(disk.parent / "lima.yaml", recipe)
            (disk.parent / "lima.yaml").chmod(0o644)
            private(disk)
            with disk.open("r+b") as stream:
                stream.truncate(20 * 1024**3)
            disk.chmod(0o644)
            outputs["qemu"]["actual-size"] = disk.stat().st_blocks * 512
            if outputs["qemu"].get("children"):
                outputs["qemu"]["children"][0]["info"]["actual-size"] = disk.stat().st_blocks * 512
            return creator.CommandResult(0, b"", b"")
        if argv == [str(creator.LIMA.resolve()), "list", "q", "--json"]:
            return creator.CommandResult(0, json.dumps(outputs["lima"]).encode(), b"")
        if argv == ["/usr/sbin/diskutil", "image", "info", "--plist", str(disk)]:
            return creator.CommandResult(0, plistlib.dumps(outputs["apple"]), b"")
        if argv == [str(creator.QEMU.resolve()), "info", "--output=json", str(disk)]:
            return creator.CommandResult(0, json.dumps(outputs["qemu"]).encode(), b"")
        pytest.fail("Unexpected command: " + repr(argv))

    monkeypatch.setattr(creator, "_run_bounded_command", command)
    return selection, outputs, calls, command


def test_create_returns_facts_without_boot_or_enabling_start(creator, prepared):
    selection, _, calls, _ = prepared
    result = creator.create_worker(selection)
    assert result.name == "q" and result.status == "Stopped"
    assert result.disk_format == "RAW" and result.virtual_bytes == 20 * 1024**3
    assert result.start_enabled is False and result.vm_start_requested is False
    assert [call[0][1] for call in calls] == ["--version", "--version", "create", "list", "image", "info"]
    with pytest.raises(creator.Refusal, match="start_unqualified"):
        creator.start_worker(selection)
    assert len(calls) == 6


@pytest.mark.parametrize("change", ["partial", "foreign", "override", "default", "base", "input", "binary", "cache"])
def test_refusal_precedes_create(creator, inventory, prepared, change):
    selection, _, calls, _ = prepared
    storage = selection.storage
    if change == "partial":
        (storage.runtime_path / "q").mkdir()
    elif change == "foreign":
        other = owned_run(storage.pilot_root, 2)
        private(other / "lima/q/lima.yaml")
    elif change in {"override", "default", "base"}:
        private(storage.runtime_path / "_config" / (change + ".yaml"), b"disk: 90GiB")
    elif change == "input":
        private(storage.run_root / "input/lima.yaml", b"disk: 90GiB")
    elif change == "binary":
        selection = replace(selection, lima_sha256="0" * 64)
    else:
        private(storage.home_path / "tmp/leak")
    with pytest.raises(creator.Refusal):
        creator.create_worker(selection)
    assert not calls


@pytest.mark.parametrize("which,field,value", [
    ("apple", "Image Format", "ASIF"), ("apple", "Image Format", "QCOW2"),
    ("lima", "status", "Running"), ("lima", "hostAgentPID", 1), ("lima", "errors", ["private"]),
    ("qemu", "format", "qcow2"), ("qemu", "backing-filename", "/private/backing"),
    ("qemu", "children", []), ("qemu", "virtual-size", 20 * 1024**3 + 512),
])
def test_postcheck_failures_retain_worker_without_start(creator, prepared, which, field, value):
    selection, outputs, calls, _ = prepared
    outputs[which][field] = value
    with pytest.raises(creator.Refusal):
        creator.create_worker(selection)
    assert (selection.storage.runtime_path / "q/disk").exists()
    assert all("start" not in argv for argv, _ in calls)


@pytest.mark.parametrize("change", ["os", "disk", "additional", "host_hook", "mount", "raw", "encrypted"])
def test_effective_configuration_and_encryption_are_independent_proofs(creator, prepared, change):
    selection, outputs, _, _ = prepared
    config = outputs["lima"]["config"]
    if change == "os": config["os"] = "Darwin"
    elif change == "disk": config["disk"] = "40GiB"
    elif change == "additional": config["additionalDisks"] = [{"name": "extra"}]
    elif change == "host_hook": config["provision"].append({"mode": "host", "script": "false"})
    elif change == "mount": config["mounts"] = [{"location": "/Users"}]
    elif change == "raw": config["vmOpts"]["vz"]["diskImageFormat"] = "asif"
    else: outputs["apple"]["Encryption Info"]["Is Encrypted"] = False
    with pytest.raises(creator.Refusal): creator.create_worker(selection)


def test_failure_and_contention_release_lock_without_retry(creator, prepared, monkeypatch):
    selection, _, calls, command = prepared
    def fail(argv, **kwargs):
        result = command(argv, **kwargs)
        if argv[1] == "create": raise creator.CommandRefusal("timeout")
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", fail)
    with pytest.raises(creator.Refusal, match="create_timeout"):
        creator.create_worker(selection)
    assert len(calls) == 3 and (selection.storage.runtime_path / "q").exists()
    fd = os.open(selection.storage.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(creator.Refusal, match="storage_busy"):
            creator.create_worker(selection)
    finally: os.close(fd)
    assert len(calls) == 3


def test_selection_is_closed_and_cannot_select_commands_or_receipts(creator, prepared):
    selection, _, calls, _ = prepared
    encoded = creator.selection_json(selection)
    assert creator.parse_selection(encoded) == selection
    raw = json.loads(encoded)
    for field in ("command", "env", "allocation_enabled", "topology_verified", "operation"):
        with pytest.raises(creator.Refusal):
            creator.parse_selection(json.dumps(raw | {field: True}).encode())
    with pytest.raises(creator.Refusal): creator.parse_selection(encoded[:-1] + b',"schema_version":1}')
    with pytest.raises(creator.Refusal): creator.parse_selection(json.dumps(raw | {"qemu_sha256": True}).encode())
    assert not calls


@pytest.mark.parametrize("which", ["lima", "qemu"])
def test_wrong_actual_version_refuses_before_create(creator, prepared, monkeypatch, which):
    selection, _, calls, command = prepared
    def changed(argv, **kwargs):
        result = command(argv, **kwargs)
        binary = creator.LIMA if which == "lima" else creator.QEMU
        if argv == [str(binary.resolve()), "--version"]:
            return creator.CommandResult(0, b"unexpected version\n", b"")
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", changed)
    with pytest.raises(creator.Refusal, match=which + "_version"):
        creator.create_worker(selection)
    assert all("create" not in argv for argv, _ in calls)


@pytest.mark.parametrize("change", ["global_config", "input", "binary", "worker"])
def test_drift_during_version_checks_cannot_reach_create(creator, prepared, monkeypatch, change):
    selection, _, calls, command = prepared
    def changed(argv, **kwargs):
        result = command(argv, **kwargs)
        if argv == [str(creator.QEMU.resolve()), "--version"]:
            if change == "global_config":
                private(selection.storage.runtime_path / "_config/override.yaml", b"os: Darwin")
            elif change == "input":
                private(selection.storage.run_root / "input/lima.yaml", b"os: Darwin")
            elif change == "binary":
                creator.LIMA.write_bytes(b"changed executable")
            else:
                (selection.storage.runtime_path / "q").mkdir()
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", changed)
    with pytest.raises(creator.Refusal): creator.create_worker(selection)
    assert all("create" not in argv for argv, _ in calls)


@pytest.mark.parametrize("stage", ["list", "image", "info"])
@pytest.mark.parametrize("failure", ["malformed", "nonzero", "timeout", "output_limit"])
def test_native_failures_are_path_free_and_never_retry(creator, prepared, monkeypatch, stage, failure):
    selection, _, calls, command = prepared
    def changed(argv, **kwargs):
        result = command(argv, **kwargs)
        if argv[1] == stage:
            if failure in {"timeout", "output_limit"}:
                raise creator.CommandRefusal(failure)
            return creator.CommandResult(1 if failure == "nonzero" else 0, b"private sensitive data", b"private path")
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", changed)
    with pytest.raises(creator.Refusal) as error: creator.create_worker(selection)
    assert "private" not in str(error.value) and "/" not in str(error.value)
    assert sum(argv[1] == "create" for argv, _ in calls) == 1
    assert (selection.storage.runtime_path / "q/disk").exists()


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "oversize", "changed_during_info"])
def test_actual_disk_alias_or_change_refuses(creator, prepared, monkeypatch, kind):
    selection, _, _, command = prepared
    disk = selection.storage.runtime_path / "q/disk"
    def changed(argv, **kwargs):
        result = command(argv, **kwargs)
        if argv[1] == "create":
            if kind == "symlink":
                disk.rename(disk.with_name("other"))
                disk.symlink_to("other")
            elif kind == "hardlink": os.link(disk, disk.with_name("alias"))
            elif kind == "oversize":
                with disk.open("r+b") as stream: stream.truncate(creator.DISK_BYTES + 512)
        if argv[1] == "info" and kind == "changed_during_info":
            with disk.open("r+b") as stream: stream.write(b"changed")
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", changed)
    with pytest.raises(creator.Refusal): creator.create_worker(selection)
    assert disk.parent.exists()


def test_shared_deadline_bounds_command_budget_and_stops_expired_preparation(creator, prepared, monkeypatch):
    selection, _, calls, command = prepared
    clock = [100.0]
    monkeypatch.setattr(creator.time, "monotonic", lambda: clock[0])
    def changed(argv, **kwargs):
        result = command(argv, **kwargs)
        if argv == [str(creator.QEMU.resolve()), "--version"]:
            clock[0] = 100.0 + creator.PREPARATION_SECONDS
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", changed)
    with pytest.raises(creator.Refusal, match="preparation_timeout"):
        creator.create_worker(selection)
    assert all("create" not in argv for argv, _ in calls)


def test_cli_cannot_select_start_or_arbitrary_command(creator, tmp_path):
    import subprocess
    for operation in ("start", "resize", "shell"):
        result = subprocess.run([sys.executable, creator.__file__, "--selection", str(tmp_path / "absent"),
                                 "--operation", operation], capture_output=True, timeout=5)
        assert result.returncode == 2 and b"invalid choice" in result.stderr
    result = subprocess.run([sys.executable, creator.__file__, "--selection", str(tmp_path / "absent")],
                            capture_output=True, timeout=5)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["blockers"] == ["selection_unavailable"]
    assert report["vm_start_requested"] is False and report["start_enabled"] is False
    assert str(tmp_path).encode() not in result.stdout
