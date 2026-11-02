"""Storage admission protects the host before any future runtime allocation."""
from __future__ import annotations

from dataclasses import replace
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def storage():
    path = Path(__file__).with_name("probe_openshell_storage.py")
    assert path.is_file(), "Storage admission implementation absent: expected red-first failure"
    spec = importlib.util.spec_from_file_location("openshell_storage_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def store(tmp_path):
    root = tmp_path.resolve() / "openshell"
    root.mkdir(mode=0o700)
    return root


def private(path: Path, data: bytes = b"preserved\n") -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(0o600)


def run_root(root: Path, index: int = 1) -> Path:
    run = root / "qualification" / f"openshell-q-{index:012x}"
    run.mkdir(mode=0o700, parents=True)
    private(run / "owner.json", json.dumps({"schema_version": 1, "run_id": run.name}).encode())
    return run


def ample(inventory, storage):
    return replace(inventory, free_bytes=64 * storage.GIB)


def test_inspection_never_creates_missing_store(storage, tmp_path):
    missing = tmp_path.resolve() / "not-created"
    with pytest.raises(storage.Refusal, match="storage_unavailable"):
        storage.inspect_storage(missing)
    assert not missing.exists()


def test_retired_fixtures_and_small_aliases_are_preserved(storage, store):
    run = run_root(store)
    private(run / "evidence/failure.json", b'{"status":"failed"}')
    private(run / "input/alias-specimens/sentinel")
    alias = run / "input/alias-specimens/symlink/alias"
    alias.parent.mkdir()
    alias.symlink_to("../sentinel")
    hardlink = run / "input/alias-specimens/hardlink/alias"
    hardlink.parent.mkdir()
    os.link(run / "input/alias-specimens/sentinel", hardlink)
    before = {str(p.relative_to(store)): p.lstat() for p in store.rglob("*")}
    inventory = storage.inspect_storage(store)
    assert inventory.retained_vm_count == 0
    assert inventory.symlink_count == 1
    assert inventory.allocated_bytes > 0
    assert set(before) == {str(p.relative_to(store)) for p in store.rglob("*")}
    assert (run / "evidence/failure.json").read_bytes() == b'{"status":"failed"}'
    for relative, original in before.items():
        after = (store / relative).lstat()
        assert (after.st_ino, after.st_mtime_ns) == (original.st_ino, original.st_mtime_ns)


def test_sparse_logical_size_never_becomes_allocation_credit(storage, store):
    run = run_root(store)
    disk = run / "lima/q/disk"
    private(disk)
    with disk.open("r+b") as stream:
        stream.truncate(20 * storage.GIB)
    inventory = storage.inspect_storage(store)
    assert inventory.logical_bytes >= 20 * storage.GIB
    assert inventory.allocated_bytes < inventory.logical_bytes
    report = storage.admit_storage(ample(inventory, storage))
    assert report.required_free_bytes == 46 * storage.GIB
    assert report.admitted is False
    assert "storage_enforcement_unqualified" in report.blockers


def test_stopped_and_partial_workers_both_count(storage, store):
    for index in (1, 2):
        run = run_root(store, index)
        (run / "lima/q").mkdir(parents=True)
    inventory = storage.inspect_storage(store)
    assert inventory.retained_vm_count == 2
    assert "retained_vm_limit" in storage.admit_storage(ample(inventory, storage)).blockers


def test_native_lima_cache_counted_even_when_xdg_cache_empty(storage, store):
    run = run_root(store)
    private(run / "controller/Library/Caches/lima/download/original", b"x" * 65536)
    private(run / "controller/Library/Caches/lima/download/imgconv/raw", b"y" * 65536)
    (run / "controller/cache").mkdir()
    inventory = storage.inspect_storage(store)
    assert inventory.lima_cache_allocated_bytes >= 131072
    assert inventory.other_cache_allocated_bytes == 0
    over = replace(ample(inventory, storage), lima_cache_allocated_bytes=2 * storage.GIB + 1)
    assert "cache_limit" in storage.admit_storage(over).blockers


@pytest.mark.parametrize("field,value,reason", [
    ("free_bytes", 12 * 1024**3, "host_free_space"),
    ("free_bytes", 46 * 1024**3 - 1, "host_free_space"),
    ("runtime_allocated_bytes", 24 * 1024**3 + 1, "runtime_storage_limit"),
    ("external_allocated_bytes", 1024**3 + 1, "external_retention_limit"),
    ("maximum_vm_disk_logical_bytes", 20 * 1024**3 + 1, "virtual_disk_limit"),
])
def test_each_resource_limit_refuses(storage, store, field, value, reason):
    inventory = replace(ample(storage.inspect_storage(store), storage), **{field: value})
    assert reason in storage.admit_storage(inventory).blockers


def test_all_blockers_reported_and_no_claimed_native_quota_pass(storage, store):
    private(store / "quota.json", b'{"quota_verified":true,"native_enforcement":true}')
    inventory = replace(storage.inspect_storage(store), free_bytes=0, retained_vm_count=2,
                        lima_cache_allocated_bytes=3 * storage.GIB,
                        external_allocated_bytes=2 * storage.GIB)
    report = storage.admit_storage(inventory)
    assert set(report.blockers) == {"host_free_space", "retained_vm_limit", "cache_limit",
                                   "external_retention_limit", "storage_enforcement_unqualified"}
    assert report.admitted is False
    assert storage.admit_storage(ample(inventory, storage)).admitted is False


@pytest.mark.parametrize("kind", ["root_symlink", "cache_symlink", "foreign_hardlink", "public_root"])
def test_unsafe_storage_alias_or_ownership_refuses(storage, store, tmp_path, kind):
    selected = store
    if kind == "root_symlink":
        selected = tmp_path.resolve() / "alias"
        selected.symlink_to(store, target_is_directory=True)
    elif kind == "public_root":
        store.chmod(0o755)
    else:
        run = run_root(store)
        outside = tmp_path.resolve() / "outside"
        private(outside, b"do not read or change")
        if kind == "cache_symlink":
            target = run / "controller/Library/Caches/lima"
            target.parent.mkdir(parents=True)
            target.symlink_to(outside)
        else:
            os.link(outside, run / "foreign-link")
    with pytest.raises(storage.Refusal):
        storage.inspect_storage(selected)


@pytest.mark.parametrize("marker", [b'{"schema_version":1,"run_id":"wrong"}', b'{}',
                                     b'{"schema_version":1,"schema_version":1,"run_id":"x"}'])
def test_unowned_run_refuses(storage, store, marker):
    run = run_root(store)
    private(run / "owner.json", marker)
    with pytest.raises(storage.Refusal, match="storage_owner"):
        storage.inspect_storage(store)


def test_unavailable_accounting_and_bounded_inventory_refuse(storage, store, monkeypatch):
    private(store / "one")
    monkeypatch.setattr(storage, "MAX_ENTRIES", 0)
    with pytest.raises(storage.Refusal, match="storage_inventory_limit"):
        storage.inspect_storage(store)


def test_deep_inventory_refuses_without_following_more_directories(storage, store, monkeypatch):
    (store / "first/second").mkdir(parents=True)
    monkeypatch.setattr(storage, "MAX_DEPTH", 1)
    with pytest.raises(storage.Refusal, match="storage_inventory_limit"):
        storage.inspect_storage(store)


def test_root_handle_closed_when_acquisition_validation_fails(storage, store, monkeypatch):
    original_open, original_fstat = os.open, os.fstat
    opened = []

    def tracked_open(*args, **kwargs):
        fd = original_open(*args, **kwargs)
        opened.append(fd)
        return fd

    monkeypatch.setattr(storage.os, "open", tracked_open)
    monkeypatch.setattr(storage.os, "fstat", lambda fd: (_ for _ in ()).throw(OSError("unavailable")))
    with pytest.raises(storage.Refusal, match="storage_unavailable"):
        storage.inspect_storage(store)
    assert len(opened) == 1
    with pytest.raises(OSError):
        original_fstat(opened[0])


def test_marker_handle_closed_when_stream_acquisition_fails(storage, store, monkeypatch):
    run_root(store)
    original_open = os.open
    opened = []

    def tracked_open(*args, **kwargs):
        fd = original_open(*args, **kwargs)
        opened.append(fd)
        return fd

    monkeypatch.setattr(storage.os, "open", tracked_open)
    monkeypatch.setattr(storage.os, "fdopen", lambda *args: (_ for _ in ()).throw(OSError("unavailable")))
    with pytest.raises(storage.Refusal, match="storage_owner"):
        storage.inspect_storage(store)
    assert len(opened) >= 4
    for fd in opened:
        with pytest.raises(OSError):
            os.fstat(fd)


@pytest.mark.parametrize("available", [-1, None, True])
def test_unavailable_free_space_is_not_admitted(storage, store, monkeypatch, available):
    monkeypatch.setattr(storage.os, "fstatvfs", lambda fd: SimpleNamespace(f_bavail=available, f_frsize=4096))
    with pytest.raises(storage.Refusal, match="storage_accounting"):
        storage.inspect_storage(store)


def test_missing_allocated_block_accounting_refuses(storage, store, monkeypatch):
    info = store.stat()
    entry = SimpleNamespace(name="file", stat=lambda **kwargs: SimpleNamespace(
        st_uid=info.st_uid, st_dev=info.st_dev, st_size=1))

    class Entries:
        def __enter__(self):
            return iter([entry])

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(storage.os, "scandir", lambda fd: Entries())
    with pytest.raises(storage.Refusal, match="storage_accounting"):
        storage.inspect_storage(store)


def test_foreign_owner_refuses(storage, store, monkeypatch):
    owner = os.getuid()
    monkeypatch.setattr(storage.os, "getuid", lambda: owner + 1)
    with pytest.raises(storage.Refusal, match="storage_owner"):
        storage.inspect_storage(store)


def test_sufficient_space_still_refuses_without_native_enforcement(storage, store, monkeypatch):
    inventory = ample(storage.inspect_storage(store), storage)
    monkeypatch.setattr(storage, "_inspect_fd", lambda *args: inventory)
    with pytest.raises(storage.Refusal, match="^storage_enforcement_unqualified$"):
        with storage.allocation_guard(store):
            pytest.fail("caller should never reach a VM operation")


def test_lock_contention_and_refusal_release_without_writes(storage, store):
    fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(storage.Refusal, match="storage_busy"):
            with storage.allocation_guard(store):
                pytest.fail("allocation was admitted")
    finally:
        os.close(fd)
    with pytest.raises(storage.Refusal):
        with storage.allocation_guard(store):
            pytest.fail("unqualified storage was admitted")
    fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)
    assert list(store.iterdir()) == []


def test_invalid_accounting_is_not_zero_usage(storage, store):
    for value in (True, -1, "unknown", None):
        with pytest.raises(storage.Refusal, match="storage_accounting"):
            storage.admit_storage(replace(storage.inspect_storage(store), allocated_bytes=value))


def test_cli_reports_refusal_without_mutation(storage, store):
    script = Path(__file__).with_name("probe_openshell_storage.py")
    result = subprocess.run([sys.executable, str(script), "--root", str(store)], capture_output=True,
                            text=True, timeout=15, check=False)
    assert result.returncode == 1
    value = json.loads(result.stdout)
    assert value["status"] == "refused"
    assert value["hard_limits"] == "unqualified"
    assert "storage_enforcement_unqualified" in value["blockers"]
    assert str(store) not in result.stdout
    assert list(store.iterdir()) == []
