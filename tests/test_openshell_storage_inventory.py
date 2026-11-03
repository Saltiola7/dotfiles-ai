"""Mounted inventory counts retained state without granting allocation."""
from __future__ import annotations

from dataclasses import replace
from contextlib import contextmanager
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def inventory():
    path = Path(__file__).with_name("probe_openshell_storage_inventory.py")
    assert path.is_file(), "Mount-aware inventory absent: expected red-first failure"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("openshell_inventory_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


def private(path, data=b"preserved\n"):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(0o600)


def owned_run(root, index):
    path = root / "qualification" / f"openshell-q-{index:012x}"
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    private(path / "owner.json", json.dumps({"schema_version": 1, "run_id": path.name}).encode())
    return path


@pytest.fixture
def mounted(inventory, tmp_path, monkeypatch):
    native = inventory.native
    root = tmp_path.resolve() / "openshell"
    root.mkdir(mode=0o700)
    run = owned_run(root, 1)
    image = run / "runtime.raw"
    private(image)
    with image.open("r+b") as stream:
        stream.truncate(24 * 1024**3)
    info = image.stat()
    selection = native.NativeStorageSelection(
        "pilot", root, run, image, info.st_dev, info.st_ino,
        "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222",
        "33333333-3333-4333-8333-333333333333")
    for path in native._paths(selection):
        if path != image:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.chmod(0o700)
    for name in ("_xdg", "_tmp"):
        (selection.cache_path / name).mkdir(mode=0o700)
    capacity = selection.image_bytes - 40960
    volumes = [native.Volume(selection.runtime_uuid, "disk41s1", 0, 0, 32768),
               native.Volume(selection.cache_uuid, "disk41s2", selection.cache_bytes, 0, 16384)]
    snapshot = native.NativeSnapshot(
        native.Attachment(str(image), os.getuid(), 0o600, True, selection.image_bytes,
                          "disk40", "disk40s1", "disk41", ("disk41s1", "disk41s2")),
        native.Container(selection.container_uuid, "disk41", "disk40s1",
                         "44444444-4444-4444-8444-444444444444", capacity, capacity,
                         capacity - 131072, *volumes),
        native.Mount(selection.runtime_uuid, "disk41s1", "disk41", "disk40s1",
                     str(selection.runtime_path), True, capacity),
        native.Mount(selection.cache_uuid, "disk41s2", "disk41", "disk40s1",
                     str(selection.cache_path), True, capacity))
    calls = []

    def device(path):
        if path == selection.cache_path or selection.cache_path in path.parents:
            return 9002
        if path == selection.runtime_path or selection.runtime_path in path.parents:
            return 9001
        return info.st_dev

    def observe(value, **kwargs):
        calls.append(value)
        records = tuple(replace(item, device=device(item.path)) for item in native._observe_paths(value, **kwargs))
        return native.NativeStorageObservation(os.getuid(), records, records, snapshot, snapshot, 64 * 1024**3)

    original_stat = inventory._stat

    def mounted_stat(fd, name=None):
        observed = original_stat(fd, name)
        candidates = [root, *root.rglob("*")]
        matches = [path for path in candidates if path.lstat().st_ino == observed.st_ino]
        virtual_device = device(matches[0]) if matches else observed.st_dev
        attrs = {key: getattr(observed, key) for key in dir(observed) if key.startswith("st_")}
        return SimpleNamespace(**(attrs | {"st_dev": virtual_device}))

    monkeypatch.setattr(native, "collect_native_storage", observe)
    monkeypatch.setattr(inventory, "_stat", mounted_stat)
    return selection, calls


def test_zero_workers_with_live_mounts_verifies_inventory_only(inventory, mounted):
    selection, calls = mounted
    observed = inventory.collect_native_inventory(selection)
    report = inventory.validate_native_inventory(selection, observed)
    assert report.inventory_verified and report.blockers == ()
    assert report.allocation_enabled is False and report.admitted is False
    assert report.running_worker_qualification == report.disk_format_qualification == "not_run"
    assert observed.workers == () and len(calls) == 2
    assert observed.image_allocated_bytes == selection.image_path.stat().st_blocks * 512
    assert observed.runtime_used_bytes == 131072 and observed.cache_used_bytes == 16384


def test_mounted_content_is_not_counted_again_as_host_allocation(inventory, mounted):
    selection, _ = mounted
    before = inventory.collect_native_inventory(selection)
    private(selection.home_path / "payload", b"x" * 65536)
    private(selection.cache_path / "download/payload", b"y" * 65536)
    after = inventory.collect_native_inventory(selection)
    assert after.image_allocated_bytes == before.image_allocated_bytes
    assert after.external_allocated_bytes == before.external_allocated_bytes


def test_partial_and_stopped_workers_count_across_all_runs(inventory, mounted):
    selection, _ = mounted
    (selection.runtime_path / "q").mkdir()
    other = owned_run(selection.pilot_root, 2)
    private(other / "lima/q/lima.yaml", b"vmType: vz\n")
    private(other / "lima/q/disk")
    observed = inventory.collect_native_inventory(selection)
    assert len(observed.workers) == 2
    assert sorted(worker.has_config for worker in observed.workers) == [False, True]
    assert "retained_vm_limit" in inventory.validate_native_inventory(selection, observed).blockers


def test_only_exact_controller_config_network_directories_are_excluded(inventory, mounted):
    selection, _ = mounted
    for name in ("_config", "_networks", "controller"):
        (selection.runtime_path / name).mkdir()
    observed = inventory.collect_native_inventory(selection)
    assert [worker.name for worker in observed.workers] == ["controller"]


@pytest.mark.parametrize("name", ["_disk", "_disks", "_templates", "_hidden", ".hidden", "_controller-old"])
def test_unexpected_reserved_worker_state_refuses(inventory, mounted, name):
    selection, _ = mounted
    (selection.runtime_path / name).mkdir()
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


@pytest.mark.parametrize("name", ["q", "_config", "_networks"])
def test_non_directory_worker_or_exclusion_refuses(inventory, mounted, name):
    selection, _ = mounted
    private(selection.runtime_path / name)
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


@pytest.mark.parametrize("name", ["disk", "image", "basedisk", "diffdisk"])
def test_all_partial_disk_candidates_enforce_logical_ceiling(inventory, mounted, name):
    selection, _ = mounted
    path = selection.runtime_path / "q" / name
    private(path)
    with path.open("r+b") as stream:
        stream.truncate(20 * 1024**3 + 1)
    observed = inventory.collect_native_inventory(selection)
    assert observed.maximum_vm_disk_logical_bytes == 20 * 1024**3 + 1
    assert "virtual_disk_limit" in inventory.validate_native_inventory(selection, observed).blockers
    assert observed.workers[0].disks[0].path == path


def test_external_evidence_is_counted_conservatively(inventory, mounted):
    selection, _ = mounted
    base = inventory.collect_native_inventory(selection).external_allocated_bytes
    private(selection.run_root / "evidence/retained", b"e" * 65536)
    observed = inventory.collect_native_inventory(selection)
    assert observed.external_allocated_bytes >= base + 65536
    report = inventory.validate_native_inventory(selection, replace(observed, external_allocated_bytes=1024**3 + 1))
    assert "external_retention_limit" in report.blockers


@pytest.mark.parametrize("relative", ["controller/cache", "controller/tmp", "controller/Library/Caches/lima"])
@pytest.mark.parametrize("retained", ["file", "empty_directory"])
def test_historical_cache_and_temp_content_refuses_without_cleanup(inventory, mounted, relative, retained):
    selection, _ = mounted
    run = owned_run(selection.pilot_root, 2)
    path = run / relative / "retained"
    if retained == "file":
        private(path, b"keep this evidence")
    else:
        path.mkdir(mode=0o700, parents=True)
    before = path.lstat()
    with pytest.raises(inventory.Refusal, match="cache_route_retained"):
        inventory.collect_native_inventory(selection)
    assert path.lstat().st_ino == before.st_ino
    if retained == "file":
        assert path.read_bytes() == b"keep this evidence"


@pytest.mark.parametrize("name", ["cache", "tmp"])
def test_selected_unused_home_cache_and_temp_must_be_empty(inventory, mounted, name):
    selection, _ = mounted
    path = selection.home_path / name / "retained"
    private(path)
    with pytest.raises(inventory.Refusal, match="cache_route_retained"):
        inventory.collect_native_inventory(selection)
    assert path.read_bytes() == b"preserved\n"


def test_empty_historical_routes_and_active_quota_contents_are_allowed(inventory, mounted):
    selection, _ = mounted
    run = owned_run(selection.pilot_root, 2)
    for relative in ("controller/cache", "controller/tmp", "controller/Library/Caches/lima"):
        (run / relative).mkdir(mode=0o700, parents=True)
    private(selection.cache_path / "_xdg/retained", b"bounded cache")
    private(selection.cache_path / "_tmp/retained", b"bounded temporary data")
    observed = inventory.collect_native_inventory(selection)
    assert inventory.validate_native_inventory(selection, observed).inventory_verified


@pytest.mark.parametrize("kind", ["missing", "alias", "public", "wrong_device"])
def test_quota_child_routes_must_exist_privately_on_cache_device(inventory, mounted, monkeypatch, kind):
    selection, _ = mounted
    path = selection.cache_path / "_tmp"
    if kind == "missing":
        path.rmdir()
    elif kind == "alias":
        path.rmdir()
        path.symlink_to(selection.home_path / "tmp")
    elif kind == "public":
        path.chmod(0o755)
    else:
        original = inventory._stat

        def wrong(fd, name=None):
            result = original(fd, name)
            if result.st_ino == path.stat().st_ino:
                result.st_dev = 9001
            return result

        monkeypatch.setattr(inventory, "_stat", wrong)
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


def test_other_backing_image_refuses_even_when_sparse_and_unmounted(inventory, mounted):
    selection, _ = mounted
    other = owned_run(selection.pilot_root, 2)
    private(other / "runtime.raw")
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


def test_undeclared_runtime_disk_image_refuses(inventory, mounted):
    selection, _ = mounted
    private(selection.runtime_path / "q/extra.raw")
    with pytest.raises(inventory.Refusal, match="additional_image"):
        inventory.collect_native_inventory(selection)


def test_non_directory_lima_home_in_another_run_refuses(inventory, mounted):
    selection, _ = mounted
    other = owned_run(selection.pilot_root, 2)
    private(other / "lima")
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "socket", "fifo"])
def test_runtime_aliases_and_special_files_never_opened(inventory, mounted, kind):
    selection, _ = mounted
    path = selection.runtime_path / "q/disk"
    private(path)
    if kind == "symlink":
        path.unlink()
        path.symlink_to(selection.run_root / "owner.json")
    elif kind == "hardlink":
        os.link(path, path.with_name("alias"))
    elif kind == "fifo":
        path.unlink()
        os.mkfifo(path)
    else:
        path.unlink()
        # Use a short path: macOS AF_UNIX paths have a small native length bound.
        sock = socket.socket(socket.AF_UNIX)
        previous = Path.cwd()
        try:
            os.chdir(path.parent)
            sock.bind("ha.sock")
        finally:
            os.chdir(previous)
            sock.close()
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


def test_existing_synthetic_fixture_aliases_are_counted_without_following(inventory, mounted):
    selection, _ = mounted
    path = selection.run_root / "fixture/input"
    private(path)
    os.link(path, path.with_name("hardlink"))
    path.with_name("symlink").symlink_to("/never-open-this-target")
    observed = inventory.collect_native_inventory(selection)
    assert observed.fixture_alias_count == 3


def test_each_run_requires_closed_owner_marker(inventory, mounted):
    selection, _ = mounted
    other = owned_run(selection.pilot_root, 2)
    private(other / "owner.json", b'{"schema_version":1,"run_id":"wrong"}')
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


def test_qualification_finder_metadata_is_counted_without_opening_or_parsing(inventory, mounted, monkeypatch):
    selection, _ = mounted
    before = inventory.collect_native_inventory(selection)
    metadata = selection.pilot_root / "qualification/.DS_Store"
    private(metadata, b"\xffnot-json" * 8192)
    # The metadata allowance is exactly 64 KiB, independent of its contents.
    with metadata.open("r+b") as stream:
        stream.truncate(64 * 1024)
    opened = []
    original = os.open

    def record(path, *args, **kwargs):
        if Path(path).name == ".DS_Store":
            opened.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(inventory.os, "open", record)
    observed = inventory.collect_native_inventory(selection)
    assert inventory.validate_native_inventory(selection, observed).inventory_verified
    assert observed.workers == () and not opened
    assert observed.external_allocated_bytes >= before.external_allocated_bytes + metadata.stat().st_blocks * 512
    assert metadata.read_bytes().startswith(b"\xffnot-json")


@pytest.mark.parametrize("kind", ["directory", "symlink", "hardlink", "oversized", "foreign_owner", "other_basename"])
def test_qualification_finder_metadata_exception_is_narrow(inventory, mounted, monkeypatch, kind):
    selection, _ = mounted
    metadata = selection.pilot_root / "qualification/.DS_Store"
    if kind == "directory":
        metadata.mkdir()
    elif kind == "symlink":
        metadata.symlink_to(selection.run_root / "owner.json")
    elif kind == "hardlink":
        os.link(selection.run_root / "owner.json", metadata)
    elif kind == "oversized":
        private(metadata, b"x" * (64 * 1024 + 1))
    elif kind == "other_basename":
        private(metadata.with_name(".ds_store"))
    else:
        private(metadata)
        original = inventory._stat

        def foreign(fd, name=None):
            result = original(fd, name)
            if name == ".DS_Store":
                result.st_uid += 1
            return result

        monkeypatch.setattr(inventory, "_stat", foreign)
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)


def test_failed_collection_releases_exclusive_root_lock(inventory, mounted):
    selection, _ = mounted
    (selection.cache_path / "_xdg").rmdir()
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(selection)
    fd = os.open(selection.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)


def test_lock_contention_refuses_before_native_collection(inventory, mounted):
    selection, calls = mounted
    fd = os.open(selection.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(inventory.Refusal, match="storage_busy"):
            inventory.collect_native_inventory(selection)
    finally:
        os.close(fd)
    assert not calls


def test_missing_store_is_never_created(inventory, mounted):
    selection, calls = mounted
    absent = selection.pilot_root / "absent"
    run = absent / "qualification" / selection.run_root.name
    with pytest.raises(inventory.Refusal):
        inventory.collect_native_inventory(replace(selection, pilot_root=absent, run_root=run,
                                                  image_path=run / "runtime.raw"))
    assert not absent.exists() and not calls


def test_receipt_cannot_override_inventory(inventory, mounted):
    selection, _ = mounted
    report = inventory.validate_native_inventory(selection, {"inventory_verified": True})
    assert not report.inventory_verified and not report.allocation_enabled


def test_unexpected_mount_crossing_refuses(inventory, mounted, monkeypatch):
    selection, _ = mounted
    path = selection.run_root / "evidence"
    path.mkdir()
    original = inventory._stat

    def extra_mount(fd, name=None):
        result = original(fd, name)
        if result.st_ino == path.stat().st_ino:
            result.st_dev = 9900
        return result

    monkeypatch.setattr(inventory, "_stat", extra_mount)
    with pytest.raises(inventory.Refusal, match="storage_mount_unqualified"):
        inventory.collect_native_inventory(selection)


def test_native_failure_before_scan_is_not_a_passing_receipt(inventory, mounted, monkeypatch):
    selection, _ = mounted

    def failed(value, **kwargs):
        raise inventory.Refusal("native_timeout")

    monkeypatch.setattr(inventory.native, "collect_native_storage", failed)
    with pytest.raises(inventory.Refusal, match="native_timeout"):
        inventory.collect_native_inventory(selection)


def test_binding_change_after_scan_refuses(inventory, mounted, monkeypatch):
    selection, _ = mounted
    original = inventory.native.collect_native_storage
    count = 0

    def changed(value, **kwargs):
        nonlocal count
        count += 1
        result = original(value, **kwargs)
        if count == 2:
            snapshot = result.native_before
            snapshot = replace(snapshot, container=replace(snapshot.container, free=snapshot.container.free - 4096))
            result = replace(result, native_before=snapshot, native_after=snapshot)
        return result

    monkeypatch.setattr(inventory.native, "collect_native_storage", changed)
    with pytest.raises(inventory.Refusal, match="storage_changed"):
        inventory.collect_native_inventory(selection)


def test_entry_change_between_scans_refuses(inventory, mounted, monkeypatch):
    selection, _ = mounted
    original = inventory._scan
    count = 0

    def changed(*args, **kwargs):
        nonlocal count
        result = original(*args, **kwargs)
        count += 1
        if count == 1:
            private(selection.run_root / "evidence/late-entry")
        return result

    monkeypatch.setattr(inventory, "_scan", changed)
    with pytest.raises(inventory.Refusal, match="storage_changed"):
        inventory.collect_native_inventory(selection)


@pytest.mark.parametrize("limit,value", [("MAX_ENTRIES", 3), ("MAX_DEPTH", 2)])
def test_traversal_limits_refuse(inventory, mounted, monkeypatch, limit, value):
    selection, _ = mounted
    monkeypatch.setattr(inventory, limit, value)
    with pytest.raises(inventory.Refusal, match="storage_inventory_limit"):
        inventory.collect_native_inventory(selection)


def test_large_directory_iteration_stops_at_entry_budget(inventory, mounted, monkeypatch):
    selection, _ = mounted
    original = inventory.os.scandir
    yielded = []

    @contextmanager
    def entries():
        def generate():
            for index in range(100):
                yielded.append(index)
                yield SimpleNamespace(name=f"unobserved-{index}")
        yield generate()

    def large_scan(path):
        if type(path) is int and os.fstat(path).st_ino == selection.pilot_root.stat().st_ino:
            return entries()
        return original(path)

    monkeypatch.setattr(inventory, "MAX_ENTRIES", 3)
    monkeypatch.setattr(inventory.os, "scandir", large_scan)
    with pytest.raises(inventory.Refusal, match="storage_inventory_limit"):
        inventory.collect_native_inventory(selection)
    # One extra entry establishes overflow; the remainder is never materialized.
    assert len(yielded) == 4


def test_borrowed_descriptor_must_identify_selected_root_and_remains_open(inventory, mounted, tmp_path):
    selection, calls = mounted
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    fd = os.open(other, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(inventory.Refusal):
            inventory._collect_locked(selection, fd)
        assert os.fstat(fd).st_ino == other.stat().st_ino
    finally:
        os.close(fd)
    assert not calls


def test_borrowed_root_lock_is_not_reacquired_or_closed(inventory, mounted):
    selection, _ = mounted
    fd = os.open(selection.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        observed = inventory._collect_locked(selection, fd)
        assert inventory.validate_native_inventory(selection, observed).inventory_verified
        assert os.fstat(fd).st_ino == selection.pilot_root.stat().st_ino
    finally:
        os.close(fd)


@pytest.mark.parametrize("change", ["boolean_counter", "duplicate_worker", "disk_mode", "worker_disk_tuple", "wrong_maximum", "invented_socket"])
def test_malformed_inventory_refuses_cleanly(inventory, mounted, change):
    selection, _ = mounted
    private(selection.runtime_path / "q/disk")
    observed = inventory.collect_native_inventory(selection)
    worker = observed.workers[0]
    if change == "boolean_counter":
        observed = replace(observed, entry_count=True)
    elif change == "duplicate_worker":
        observed = replace(observed, workers=(worker, worker))
    elif change == "disk_mode":
        observed = replace(observed, workers=(replace(worker, disks=(replace(worker.disks[0], mode="regular"),)),))
    elif change == "worker_disk_tuple":
        observed = replace(observed, workers=(replace(worker, disks={}),))
    elif change == "wrong_maximum":
        observed = replace(observed, maximum_vm_disk_logical_bytes=0)
    else:
        observed = replace(observed, socket_count=1)
    report = inventory.validate_native_inventory(selection, observed)
    assert not report.inventory_verified and not report.allocation_enabled


def test_cli_missing_selection_emits_path_free_refusal(inventory, tmp_path):
    result = subprocess.run([sys.executable, inventory.__file__, "--selection", str(tmp_path / "private-missing.json")],
                            capture_output=True, timeout=5)
    report = json.loads(result.stdout)
    assert result.returncode == 1 and report["allocation_enabled"] is False
    assert report["blockers"] == ["selection_unavailable"]
    assert b"private-missing" not in result.stdout


def test_expired_inventory_deadline_refuses_before_opening_root(inventory, mounted, monkeypatch):
    selection, calls = mounted
    monkeypatch.setattr(inventory.native, "time", SimpleNamespace(monotonic=lambda: 100.0), raising=False)

    def forbidden(*args, **kwargs):
        pytest.fail("Expired inventory opened root")

    monkeypatch.setattr(inventory.legacy, "_open_root", forbidden)
    with pytest.raises(inventory.Refusal, match="storage_deadline"):
        inventory.collect_native_inventory(selection, deadline=100.0)
    assert not calls


def test_inventory_passes_same_deadline_to_both_native_collections(inventory, mounted, monkeypatch):
    selection, _ = mounted
    monkeypatch.setattr(inventory.native, "time", SimpleNamespace(monotonic=lambda: 100.0), raising=False)
    original = inventory.native.collect_native_storage
    deadlines = []

    def capture(value, **kwargs):
        deadlines.append(kwargs["deadline"])
        return original(value, **kwargs)

    monkeypatch.setattr(inventory.native, "collect_native_storage", capture)
    observed = inventory.collect_native_inventory(selection, deadline=110.0)
    assert inventory.validate_native_inventory(selection, observed).inventory_verified
    assert deadlines == [110.0, 110.0]


def test_inventory_scan_deadline_refuses_and_releases_lock(inventory, mounted, monkeypatch):
    selection, calls = mounted
    clock = [100.0]
    monkeypatch.setattr(inventory.native, "time", SimpleNamespace(monotonic=lambda: clock[0]), raising=False)
    original = inventory._stat

    def expire(fd, name=None):
        result = original(fd, name)
        if name is not None:
            clock[0] = 101.0
        return result

    monkeypatch.setattr(inventory, "_stat", expire)
    with pytest.raises(inventory.Refusal, match="storage_deadline"):
        inventory.collect_native_inventory(selection, deadline=101.0)
    assert len(calls) == 1
    fd = os.open(selection.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)


def test_inventory_rejects_native_result_returned_after_deadline(inventory, mounted, monkeypatch):
    selection, calls = mounted
    clock = [100.0]
    monkeypatch.setattr(inventory.native, "time", SimpleNamespace(monotonic=lambda: clock[0]), raising=False)
    original = inventory.native.collect_native_storage

    def late(value, **kwargs):
        result = original(value, **kwargs)
        if len(calls) == 2:
            clock[0] = 101.0
        return result

    monkeypatch.setattr(inventory.native, "collect_native_storage", late)
    with pytest.raises(inventory.Refusal, match="storage_deadline"):
        inventory.collect_native_inventory(selection, deadline=101.0)


@pytest.mark.parametrize("mode", [2**32, 2**63 - 1])
def test_large_disk_mode_refuses_without_overflow(inventory, mounted, mode):
    selection, _ = mounted
    private(selection.runtime_path / "q/disk")
    observed = inventory.collect_native_inventory(selection)
    worker = observed.workers[0]
    worker = replace(worker, disks=(replace(worker.disks[0], mode=mode),))
    report = inventory.validate_native_inventory(selection, replace(observed, workers=(worker,)))
    assert not report.inventory_verified


def running_worker(selection):
    private(selection.runtime_path / "q/disk")
    private(selection.runtime_path / "q/lima.yaml", b"source-bound configuration")


def collect_running(inventory, selection, **kwargs):
    fd = os.open(selection.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return inventory.collect_running_inventory_locked(selection, fd, **kwargs)
    finally:
        os.close(fd)


def socket_file(path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    sock = socket.socket(socket.AF_UNIX)
    previous = Path.cwd()
    try:
        os.chdir(path.parent)
        sock.bind(path.name)
    finally:
        os.chdir(previous)
        sock.close()


def test_running_inventory_allows_exact_owned_socket_metadata_only(inventory, mounted, monkeypatch):
    selection, _ = mounted
    running_worker(selection)
    for name in ("ha.sock", "default_ep.sock", "default_fd.sock", "ssh.sock"):
        socket_file(selection.runtime_path / "q" / name)
    opened = []
    original = os.open

    def track(path, *args, **kwargs):
        if Path(path).suffix == ".sock":
            opened.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(inventory.os, "open", track)
    with pytest.raises(inventory.Refusal, match="inventory_socket_unqualified"):
        inventory.collect_native_inventory(selection)
    observed = collect_running(inventory, selection)
    assert observed.socket_count == 4 and not opened
    report = inventory.validate_running_inventory(selection, observed)
    assert report.inventory_verified and not report.allocation_enabled


@pytest.mark.parametrize("relative", ["q/unknown.sock", "other/ha.sock", "_controller/ha.sock", "q/nested/ha.sock"])
def test_running_inventory_refuses_other_socket_locations(inventory, mounted, relative):
    selection, _ = mounted
    running_worker(selection)
    socket_file(selection.runtime_path / relative)
    with pytest.raises(inventory.Refusal, match="inventory_socket_unqualified"):
        collect_running(inventory, selection)


@pytest.mark.parametrize("running", [True, False])
def test_running_inventory_preserves_maximum_allocation_while_logs_grow(inventory, mounted, monkeypatch, running):
    selection, _ = mounted
    running_worker(selection)
    log = selection.runtime_path / "q/ha.stdout.log"
    private(log)
    original = inventory._scan
    scans = []

    def grow(*args, **kwargs):
        observed = original(*args, **kwargs)
        scans.append(observed)
        if len(scans) == 1:
            with log.open("ab") as stream:
                stream.write(b"growing log\n" * 1024)
        return observed

    monkeypatch.setattr(inventory, "_scan", grow)
    if not running:
        with pytest.raises(inventory.Refusal, match="storage_changed"):
            inventory.collect_native_inventory(selection)
        return
    observed = collect_running(inventory, selection)
    assert inventory.validate_running_inventory(selection, observed).inventory_verified
    assert observed.external_allocated_bytes == max(scan.external for scan in scans)
    assert next(item.size for item in scans[1].entries if item.path == log) > next(
        item.size for item in scans[0].entries if item.path == log)


@pytest.mark.parametrize("change", ["disk_growth", "config_growth", "disk_replacement", "worker_replacement", "new_worker", "new_entry"])
def test_running_inventory_refuses_anchor_and_entry_changes(inventory, mounted, monkeypatch, change):
    selection, _ = mounted
    running_worker(selection)
    original = inventory._scan
    count = 0

    def mutate(*args, **kwargs):
        nonlocal count
        result = original(*args, **kwargs)
        count += 1
        if count == 1:
            if change in {"disk_growth", "config_growth"}:
                name = "disk" if change == "disk_growth" else "lima.yaml"
                with (selection.runtime_path / "q" / name).open("ab") as stream:
                    stream.write(b"unexpected growth")
            elif change == "disk_replacement":
                disk = selection.runtime_path / "q/disk"
                replacement = disk.with_name("replacement")
                private(replacement, disk.read_bytes())
                replacement.replace(disk)
            elif change == "worker_replacement":
                worker = selection.runtime_path / "q"
                worker.rename(worker.with_name("old-worker"))
                running_worker(selection)
            elif change == "new_worker":
                (selection.runtime_path / "other").mkdir()
            else:
                private(selection.runtime_path / "q/new-log")
        return result

    monkeypatch.setattr(inventory, "_scan", mutate)
    with pytest.raises(inventory.Refusal):
        collect_running(inventory, selection)


def test_running_inventory_requires_exact_existing_selected_worker(inventory, mounted):
    selection, _ = mounted
    with pytest.raises(inventory.Refusal, match="worker_identity"):
        collect_running(inventory, selection)


def test_running_inventory_propagates_deadline(inventory, mounted, monkeypatch):
    selection, _ = mounted
    running_worker(selection)
    monkeypatch.setattr(inventory.native, "time", SimpleNamespace(monotonic=lambda: 100.0))
    with pytest.raises(inventory.Refusal, match="storage_deadline"):
        collect_running(inventory, selection, deadline=100.0)


@pytest.mark.parametrize("pressure,reason", [("host", "host_free_space"), ("cache", "native_binding"),
                                            ("external", "external_retention_limit")])
def test_running_identity_observation_survives_budget_pressure_for_safe_stop(inventory, mounted, monkeypatch, pressure, reason):
    selection, _ = mounted
    running_worker(selection)
    original = inventory.native.collect_native_storage

    def pressured(value, **kwargs):
        observed = original(value, **kwargs)
        if pressure == "host":
            observed = replace(observed, free_bytes=1)
        elif pressure == "cache":
            snapshot = observed.native_before
            snapshot = replace(snapshot, container=replace(snapshot.container,
                               cache=replace(snapshot.container.cache, in_use=selection.cache_bytes + 4096)))
            observed = replace(observed, native_before=snapshot, native_after=snapshot)
        return observed

    monkeypatch.setattr(inventory.native, "collect_native_storage", pressured)
    if pressure == "external":
        evidence = selection.run_root / "evidence/retained"
        private(evidence)
        original_stat = inventory._stat

        def allocated(fd, name=None):
            result = original_stat(fd, name)
            if result.st_ino == evidence.stat().st_ino:
                result.st_blocks = 1024**3 // 512 + 1
            return result

        monkeypatch.setattr(inventory, "_stat", allocated)
    observed = collect_running(inventory, selection)
    assert reason in inventory.validate_running_inventory(selection, observed).blockers
    assert inventory.validate_running_inventory_identity(selection, observed).inventory_verified
    assert not inventory.validate_running_inventory_identity(selection, observed).allocation_enabled


@pytest.mark.parametrize("observation_name", ["native_before", "native_after"])
@pytest.mark.parametrize("snapshot_name", ["native_before", "native_after"])
def test_running_admission_rejects_impossible_native_usage_but_preserves_recovery_identity(
        inventory, mounted, observation_name, snapshot_name):
    selection, _ = mounted
    running_worker(selection)
    observed = collect_running(inventory, selection)
    observation = getattr(observed, observation_name)
    snapshot = getattr(observation, snapshot_name)
    snapshot = replace(snapshot, container=replace(snapshot.container,
                       runtime=replace(snapshot.container.runtime, in_use=snapshot.container.capacity + 1)))
    observation = replace(observation, **{snapshot_name: snapshot})
    observed = replace(observed, **{observation_name: observation})

    report = inventory.validate_running_inventory(selection, observed)
    assert not report.inventory_verified
    assert report.blockers == ("native_binding",)
    assert inventory.validate_running_inventory_identity(selection, observed).inventory_verified


def test_running_usage_uses_minimum_host_free_and_maximum_native_allocation(inventory, mounted, monkeypatch):
    selection, _ = mounted
    running_worker(selection)
    original = inventory.native.collect_native_storage
    records = []

    def changed(value, **kwargs):
        observed = original(value, **kwargs)
        if records:
            paths = tuple(replace(item, allocated=item.allocated + 4096)
                          if item.path == selection.image_path else item for item in observed.before)
            snapshot = observed.native_before
            snapshot = replace(snapshot, container=replace(snapshot.container, free=snapshot.container.free - 8192,
                               cache=replace(snapshot.container.cache, in_use=snapshot.container.cache.in_use + 4096)))
            observed = replace(observed, before=paths, after=paths, native_before=snapshot, native_after=snapshot,
                               free_bytes=observed.free_bytes - 16384)
        records.append(observed)
        return observed

    monkeypatch.setattr(inventory.native, "collect_native_storage", changed)
    observed = collect_running(inventory, selection)
    assert inventory.validate_running_inventory(selection, observed).inventory_verified
    assert observed.free_bytes == records[-1].free_bytes
    assert observed.image_allocated_bytes == next(item.allocated for item in records[-1].after
                                                 if item.path == selection.image_path)
    assert observed.cache_used_bytes == records[-1].native_after.container.cache.in_use
    assert observed.runtime_used_bytes == records[-1].native_after.container.capacity - records[-1].native_after.container.free


def test_running_external_accounting_retains_each_entry_maximum(inventory, mounted, monkeypatch):
    selection, _ = mounted
    running_worker(selection)
    first_path = selection.run_root / "evidence/first"
    second_path = selection.run_root / "evidence/second"
    private(first_path)
    private(second_path)
    original = inventory._scan
    scans = []

    def swapped(*args, **kwargs):
        scan = original(*args, **kwargs)
        selected = first_path if not scans else second_path
        entries = tuple(replace(item, allocated=item.allocated + 8192) if item.path == selected else item for item in scan.entries)
        scan = replace(scan, entries=entries, external=scan.external + 8192)
        scans.append(scan)
        return scan

    monkeypatch.setattr(inventory, "_scan", swapped)
    observed = collect_running(inventory, selection)
    assert observed.external_allocated_bytes == scans[0].external + 8192
