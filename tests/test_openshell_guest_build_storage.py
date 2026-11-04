"""Source-only checks for the closed Linux guest storage controller."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def storage():
    path = Path(__file__).parent / "fixtures/openshell_runtime/guest_build_storage.py"
    assert path.is_file(), "Guest build storage controller not implemented"
    spec = importlib.util.spec_from_file_location("guest_build_storage_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fixed_caps_and_paths(storage):
    assert storage.ROOT == Path("/var/lib/dotfiles-ai-openshell-build")
    assert storage.WORK == storage.ROOT / "store/work"
    assert storage.IMAGE_BYTES == 8 * 1024**3
    assert storage.FIXTURE_BYTES == 64 * 1024**2
    assert storage.REQUIRED_FREE == 12 * 1024**3
    assert storage.PREPARE_SECONDS == 420
    assert storage.CLEANUP_RESERVE >= 60


@pytest.mark.parametrize("network", [False, True])
def test_unit_properties_confine_writes_and_do_not_use_journal(storage, network):
    properties = storage._properties(network, 120)
    expected = {"User=65534", "Group=65534", "ProtectSystem=strict", "ProtectHome=yes",
                "PrivateDevices=yes", "PrivatePIDs=yes", "PrivateTmp=no", "BindLogSockets=no",
                "NoNewPrivileges=yes", "CapabilityBoundingSet=", "AmbientCapabilities=",
                "RestrictNamespaces=yes", "ProtectKernelTunables=yes", "ProtectControlGroups=yes",
                "CPUQuota=200%", "MemoryMax=6G", "MemorySwapMax=0", "TasksMax=512",
                "LimitCORE=0", "KillMode=control-group", "Restart=no", "Type=exec"}
    assert expected <= set(properties)
    assert f"PrivateNetwork={'no' if network else 'yes'}" in properties
    temporary = next(item for item in properties if item.startswith("TemporaryFileSystem="))
    hidden = next(item for item in properties if item.startswith("InaccessiblePaths="))
    assert "/var:ro" in temporary
    assert ("/run:ro" in temporary) is network
    assert ("/run" in hidden) is (not network)
    assert all(path in hidden for path in ("/dev/shm", "/opt", "/srv", "/mnt", "/media", "/boot"))
    assert not any("journal" in item.lower() for item in properties)
    assert any(item.startswith("BindPaths=") and ":/tmp:norbind" in item and ":/var/tmp:norbind" in item
               for item in properties)
    families = next(item for item in properties if item.startswith("RestrictAddressFamilies="))
    assert ("AF_UNIX" in families) is (not network)
    assert "AF_INET" in families


@pytest.mark.parametrize("seconds", [True, 0, -1, 1501, 1.5])
def test_invalid_unit_duration_refuses(storage, seconds):
    with pytest.raises(storage.Refusal):
        storage._properties(False, seconds)


def test_run_unit_requires_active_owned_mount(storage):
    with pytest.raises(storage.Refusal, match="store_not_mounted"):
        storage.run_unit("print('unavailable')")


@pytest.mark.parametrize("raw", [b"", b"not json", b'{"schema_version":1,"schema_version":1}', b"[]"])
def test_receipt_malformed_data_refuses(storage, raw):
    with pytest.raises(storage.Refusal):
        storage._parse_receipt(raw)


def test_mount_parser_binds_exact_ext4_source_and_options(storage):
    raw = f"44 22 7:5 / {storage.ROOT}/store rw,nosuid,nodev - ext4 /dev/loop5 rw\n".encode()
    assert storage._mount_record(raw, storage.ROOT / "store", "/dev/loop5", 44, 7, 5)["mount_id"] == 44
    for changed in [raw.replace(b"nosuid,", b""), raw.replace(b"ext4", b"btrfs"), raw.replace(b"loop5", b"loop6"), raw + raw]:
        with pytest.raises(storage.Refusal):
            storage._mount_record(changed, storage.ROOT / "store", "/dev/loop5", 44, 7, 5)


def test_expired_deadline_refuses_before_command(storage, monkeypatch):
    monkeypatch.setattr(storage.time, "monotonic", lambda: 10.0)
    monkeypatch.setattr(storage.subprocess, "Popen", lambda *a, **k: pytest.fail("expired command executed"))
    with pytest.raises(storage.Refusal, match="deadline"):
        storage._command(["/usr/bin/true"], 10.0)


def test_prepare_refuses_existing_partial_root_without_native_commands(storage, tmp_path, monkeypatch):
    root = tmp_path / "partial"
    root.mkdir()
    monkeypatch.setattr(storage, "ROOT", root)
    monkeypatch.setattr(storage.os, "geteuid", lambda: 0)
    monkeypatch.setattr(storage.sys, "platform", "linux")
    monkeypatch.setattr(storage, "_command", lambda *a, **k: pytest.fail("partial state adopted"))
    with pytest.raises(storage.Refusal, match="retained_state"):
        storage.prepare()


def test_main_accepts_no_caller_script_or_path(storage):
    import ast
    tree = ast.parse(Path(storage.__file__).read_text())
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"add_argument", "parse_args"} for node in ast.walk(tree))
    assert '__name__ == "__main__"' not in Path(storage.__file__).read_text()


def test_fixed_probe_independently_checks_cgroup_caps_and_inherited_descriptors(storage):
    for required in ("cpu.max", "memory.max", "memory.swap.max", "pids.max", "/proc/self/fd"):
        assert required in storage._PROBE


@pytest.mark.parametrize("failed", [False, True])
def test_unit_always_stops_exact_service_and_preserves_byte_streams(storage, monkeypatch, failed):
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    monkeypatch.setattr(storage.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(storage, "_verify", lambda *a, **k: None)
    monkeypatch.setattr(storage, "_visible_system", lambda *a: None)
    calls = []
    stopped = []
    def command(argv, deadline, **kwargs):
        calls.append((argv, deadline))
        if argv[0].endswith("systemd-run") and failed:
            raise storage.Refusal("command_output_limit")
        return {"returncode": 0, "stdout": b"result", "stderr": b""}
    monkeypatch.setattr(storage, "_command", command)
    monkeypatch.setattr(storage, "_unit_stopped", lambda *args: stopped.append(args))
    if failed:
        with pytest.raises(storage.Refusal, match="command_output_limit"):
            storage.run_unit("print('source defined')", seconds=20)
    else:
        assert storage.run_unit("print('source defined')", seconds=20)["stdout"] == b"result"
    started = calls[0][0]
    unit = next(item.removeprefix("--unit=") for item in started if item.startswith("--unit="))
    assert "--pipe" in started and "--wait" in started
    assert calls[-1] == (["/usr/bin/systemctl", "stop", unit], 200.0)
    assert stopped == [(unit, 200.0)]
    assert started[started.index("--") + 1:started.index("--") + 3] == ["/usr/bin/env", "-i"]


@pytest.mark.parametrize("raw", [b"ActiveState=active\nSubState=running\nControlGroup=/system.slice/x.service\n",
                                 b"ActiveState=inactive\nSubState=dead\nControlGroup=/unexpected\n",
                                 b"ActiveState=inactive\nSubState=dead\n"])
def test_shutdown_requires_stopped_state_and_closed_cgroup(storage, monkeypatch, raw):
    monkeypatch.setattr(storage, "_command", lambda *a, **k: {"stdout": raw})
    with pytest.raises(storage.Refusal, match="unit_shutdown_unverified"):
        storage._unit_stopped("x.service", 100.0)


def test_metadata_read_handles_short_reads_and_bounds_stream(storage, tmp_path, monkeypatch):
    path = tmp_path / "metadata"
    path.write_bytes(b"abcdef")
    original = storage.os.read
    monkeypatch.setattr(storage.os, "read", lambda fd, size: original(fd, min(size, 2)))
    assert storage._read(path, 6) == b"abcdef"
    with pytest.raises(storage.Refusal, match="metadata_limit"):
        storage._read(path, 5)


def test_unit_failure_retains_bounded_private_diagnostics(storage, monkeypatch):
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    monkeypatch.setattr(storage.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(storage, "_verify", lambda *a, **k: None)
    monkeypatch.setattr(storage, "_visible_system", lambda *a: None)
    monkeypatch.setattr(storage, "_unit_stopped", lambda *a: None)
    monkeypatch.setattr(storage, "_command", lambda *a, **k: {"returncode": 2, "stdout": b"bounded output", "stderr": b"failure"})
    with pytest.raises(storage.Refusal, match="unit_failed") as caught:
        storage.run_unit("raise SystemExit(2)")
    assert caught.value.stdout == b"bounded output" and caught.value.stderr == b"failure"
    assert caught.value.returncode == 2


@pytest.mark.parametrize("mode,uid", [(0o140777, 0), (0o040777, 0), (0o100666, 0), (0o040755, 65534), (0o010600, 0)])
def test_visible_system_entries_reject_socket_or_mutable_and_special_objects(storage, mode, uid):
    with pytest.raises(storage.Refusal):
        storage._safe_system_entry(SimpleNamespace(st_mode=mode, st_uid=uid))


@pytest.mark.parametrize("mode", [0o040755, 0o100644, 0o120777])
def test_visible_system_entries_allow_only_immutable_root_owned_types(storage, mode):
    storage._safe_system_entry(SimpleNamespace(st_mode=mode, st_uid=0))


def pending(storage, phase="fixture"):
    return {"schema_version": 1, "phase": phase, "uuid": "11111111-1111-4111-8111-111111111111",
            "image_identity": [1, 2, 0o100600, 0, 0, 1, storage.FIXTURE_BYTES if phase == "fixture" else storage.IMAGE_BYTES],
            "fill_inode": 123 if phase == "fixture" else 0,
            "fixture_written_bytes": 0 if phase == "fixture" else 123456}


@pytest.mark.parametrize("phase", ["fixture", "image"])
def test_pending_record_is_comparison_only_and_closed(storage, phase):
    import json
    value = pending(storage, phase)
    assert storage._parse_pending(json.dumps(value).encode()) == value
    for key, bad in [("phase", "unknown"), ("fill_inode", True), ("schema_version", True), ("fixture_written_bytes", -1)]:
        changed = dict(value, **{key: bad})
        with pytest.raises(storage.Refusal):
            storage._parse_pending(json.dumps(changed).encode())
    with pytest.raises(storage.Refusal):
        storage._parse_pending(json.dumps(dict(value, skip_binding=True)).encode())


@pytest.mark.parametrize("change", [{"st_ino": 88}, {"st_uid": 0}, {"st_mode": 0o120600}, {"st_nlink": 2},
                                   {"st_dev": 8}, {"st_size": 64 * 1024**2 + 1}])
def test_fixture_fill_reset_refuses_changed_or_unknown_content(storage, change):
    info = {"st_ino": 123, "st_uid": 65534, "st_gid": 65534, "st_mode": 0o100600,
            "st_nlink": 1, "st_dev": 7, "st_size": 12345}
    with pytest.raises(storage.Refusal):
        storage._validate_fill(SimpleNamespace(**(info | change)), 123, 7)


def test_probe_has_negative_socket_control_outside_var(storage):
    assert '"other_pathname"' in storage._PROBE
    assert storage.OTHER_SOCKET == Path("/opt/.dotfiles-ai-openshell-build-probe.sock")


def test_probe_failed_listener_retires_only_fresh_known_fixture(storage, tmp_path, monkeypatch):
    root = tmp_path / "owned"
    root.mkdir()
    unknown = tmp_path / "unknown.sock"
    unknown.write_bytes(b"preserve")
    monkeypatch.setattr(storage, "ROOT", root)
    monkeypatch.setattr(storage, "OTHER_SOCKET", unknown)
    monkeypatch.setattr(storage.os, "chown", lambda *a: None)
    with pytest.raises(storage.Refusal, match="probe_listener_unavailable"):
        storage._probe(fill=False, deadline=100.0)
    assert unknown.read_bytes() == b"preserve"
    assert not (root / "outside-writable").exists()


@pytest.mark.parametrize("phase", [[], {}, True, None])
def test_pending_malformed_phase_refuses_structurally(storage, phase):
    import json
    with pytest.raises(storage.Refusal):
        storage._parse_pending(json.dumps(pending(storage) | {"phase": phase}).encode())


def test_full_size_pending_resume_never_formats_or_recreates_image(storage, tmp_path, monkeypatch):
    from contextlib import contextmanager
    import json
    import os
    root = tmp_path / "retained"
    root.mkdir()
    (root / "store").mkdir()
    image = root / "image.raw"
    image.write_bytes(b"preserve exact retained image")
    value = pending(storage, "image")
    (root / "pending.json").write_text(json.dumps(value))
    original_stat = Path.stat
    def parent_stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if path == tmp_path:
            values = list(result)
            values[4] = 0
            return os.stat_result(values)
        return result
    monkeypatch.setattr(Path, "stat", parent_stat)
    monkeypatch.setattr(storage, "ROOT", root)
    monkeypatch.setattr(storage.os, "geteuid", lambda: 0)
    monkeypatch.setattr(storage.sys, "platform", "linux")
    monkeypatch.setattr(storage.os, "statvfs", lambda *a: SimpleNamespace(f_bavail=32 * 1024**3, f_frsize=1))
    monkeypatch.setattr(storage, "_root", lambda: os.open(root, os.O_RDONLY))
    monkeypatch.setattr(storage, "_private", lambda *a, **k: tuple(value["image_identity"]))
    monkeypatch.setattr(storage, "_make_image", lambda *a, **k: pytest.fail("retained image reformatted"))
    monkeypatch.setattr(storage, "_command", lambda *a, **k: pytest.fail("unmocked native effect"))
    bindings = []
    @contextmanager
    def mounted(*args, **kwargs):
        bindings.append(args)
        yield SimpleNamespace()
    monkeypatch.setattr(storage, "_mounted", mounted)
    monkeypatch.setattr(storage, "_probe", lambda **kwargs: {"written_bytes": 0})
    report = storage.prepare()
    assert report["status"] == "prepared" and report["fixture_written_bytes"] == value["fixture_written_bytes"]
    assert bindings[0][:4] == (image, storage.IMAGE_BYTES, value["uuid"], tuple(value["image_identity"]))
    assert image.read_bytes() == b"preserve exact retained image"
    assert not (root / "pending.json").exists()
    assert storage._parse_receipt((root / "receipt.json").read_bytes())["fixture_verified"] is True
