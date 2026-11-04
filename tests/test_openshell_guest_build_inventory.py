"""Read-only mounted-store inventory, with synthetic files and mount metadata."""
import os
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def inventory(tmp_path, monkeypatch):
    base = Path(__file__).parent / 'fixtures/openshell_runtime'
    path = base / 'guest_build_inventory.py'
    assert path.is_file(), 'mounted-store inventory absent: intended red'
    module = ModuleType('guest_inventory_test')
    sys.modules[module.__name__] = module
    exec(compile((base / 'guest_build_storage.py').read_text() + '\n' + path.read_text(), str(path), 'exec'), module.__dict__)
    root = tmp_path / 'root'; root.mkdir(mode=0o711); root.chmod(0o711)
    mount = root / 'store'; mount.mkdir(mode=0o755); mount.chmod(0o755)
    work = mount / 'work'; work.mkdir(mode=0o700)
    monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(module, 'WORK', work)
    monkeypatch.setattr(module, 'INVENTORY_ROOT_UID', os.getuid())
    monkeypatch.setattr(module, 'INVENTORY_WORK_UID', os.getuid())
    monkeypatch.setattr(module, 'INVENTORY_ROOT_GID', os.getgid())
    monkeypatch.setattr(module, 'INVENTORY_WORK_GID', os.getgid())
    module._active = module.Store(root, root/'image.raw', mount, work, 'fixture', '/dev/loop9', 42, (), module.IMAGE_BYTES)
    module._work_end = time.monotonic() + 30
    space = SimpleNamespace(f_blocks=2**21, f_frsize=4096, f_bfree=2**20, f_bavail=2**20-1)
    monkeypatch.setattr(module.os, 'fstatvfs', lambda fd: space)
    return module, work


def file(path, data=b'data'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_parent_mode_matches_existing_controller_contract(inventory, monkeypatch):
    module, _ = inventory
    real = Path.lstat
    def root_owner(path):
        info = real(path)
        if path == module.ROOT:
            values = list(info); values[4] = values[5] = 0
            return os.stat_result(values)
        return info
    monkeypatch.setattr(Path, 'lstat', root_owner)
    accepted = module._private(module.ROOT, directory=True)
    assert module.stat.S_IMODE(accepted[2]) == 0o711
    assert module.build_inventory()['status'] == 'inventoried'


def test_reports_real_metadata_unknown_names_and_exact_closed_shape(inventory):
    module, work = inventory
    value = file(work/'downloads/item', b'hello')
    file(work/'unexpected', b'unknown')
    report = module.build_inventory()
    assert set(report) == {'schema_version', 'status', 'image_bytes', 'store_capacity_bytes', 'store_free_bytes',
        'store_available_bytes', 'root_free_bytes', 'work', 'entries', 'totals', 'build_enabled', 'session_enabled'}
    assert report['schema_version'] == 1 and report['status'] == 'inventoried'
    assert report['image_bytes'] == 8*1024**3
    assert report['build_enabled'] is False and report['session_enabled'] is False
    rows = {entry['name']: entry for entry in report['entries']}
    assert rows['downloads']['kind'] == 'directory' and rows['downloads']['known'] is True
    assert rows['unexpected']['kind'] == 'file' and rows['unexpected']['known'] is False
    assert rows['downloads']['logical_bytes'] == 5
    assert rows['downloads']['allocated_bytes'] >= value.stat().st_blocks*512
    assert sum(row['entry_count'] for row in rows.values())+1 == report['totals']['entry_count']
    assert report['store_available_bytes'] < report['store_free_bytes'] <= report['store_capacity_bytes']


def test_sparse_file_reports_logical_and_allocated_separately(inventory):
    module, work = inventory
    with (work/'sparse').open('wb') as stream: stream.truncate(1024**2)
    row = module.build_inventory()['entries'][0]
    assert row['logical_bytes'] == 1024**2
    assert row['allocated_bytes'] < row['logical_bytes']


def test_cross_root_hardlinks_are_globally_deduplicated_not_reclaimable(inventory):
    module, work = inventory
    original = file(work/'a/item', b'x'*8192); (work/'b').mkdir()
    os.link(original, work/'b/alias')
    report = module.build_inventory(); a, b = report['entries']
    blocks = original.stat().st_blocks*512
    assert a['shared_allocated_bytes'] == blocks == b['shared_allocated_bytes']
    assert report['totals']['shared_allocated_bytes'] == blocks
    assert report['totals']['logical_bytes'] == 8192
    assert report['totals']['hardlink_entries'] == 2
    assert report['totals']['unique_inode_count'] == report['totals']['entry_count']-1


def test_all_hardlinks_inside_one_top_root_are_exclusive(inventory):
    module, work = inventory
    path = file(work/'a/item', b'x'*8192); os.link(path, work/'a/alias')
    row = module.build_inventory()['entries'][0]
    assert row['shared_allocated_bytes'] == 0
    assert row['exclusive_allocated_bytes'] == row['allocated_bytes']
    assert row['hardlink_entries'] == 2


def test_link_outside_work_is_not_claimed_reclaimable(inventory):
    module, work = inventory
    path = file(work/'item', b'x'*8192); os.link(path, work.parent/'retained-outside')
    row = module.build_inventory()['entries'][0]
    assert row['shared_allocated_bytes'] == row['allocated_bytes'] > 0
    assert row['exclusive_allocated_bytes'] == 0


def test_symlinks_are_metadata_only_and_no_file_contents_opened(inventory, monkeypatch):
    module, work = inventory
    outside = file(work.parent/'outside/secret', b'not-read')
    (work/'alias').symlink_to(outside.parent, target_is_directory=True)
    real = module.os.open
    def directories_only(path, flags, *args, **kwargs):
        assert flags & os.O_DIRECTORY, 'inventory attempted a file content open'
        return real(path, flags, *args, **kwargs)
    monkeypatch.setattr(module.os, 'open', directories_only)
    row = module.build_inventory()['entries'][0]
    assert row['kind'] == 'symlink' and row['entry_count'] == 1 and row['symlink_entries'] == 1


def test_fifo_refuses_without_open(inventory):
    module, work = inventory
    os.mkfifo(work/'fifo')
    with pytest.raises(module.Refusal, match='inventory_'): module.build_inventory()


@pytest.mark.parametrize('limit', ['entries', 'depth', 'roots'])
def test_scan_budgets_fail_closed(inventory, monkeypatch, limit):
    module, work = inventory
    file(work/'a/b/c'); file(work/'second')
    name = {'entries':'INVENTORY_MAX_ENTRIES', 'depth':'INVENTORY_MAX_DEPTH', 'roots':'INVENTORY_MAX_ROOTS'}[limit]
    monkeypatch.setattr(module, name, 1)
    with pytest.raises(module.Refusal, match='inventory_'): module.build_inventory()


def test_entry_budget_stops_directory_iterator_without_collecting_every_name(inventory, monkeypatch):
    module, work = inventory
    for index in range(10): file(work / str(index))
    monkeypatch.setattr(module, 'INVENTORY_MAX_ENTRIES', 4)
    real = module.os.scandir; yielded = []
    class Observed:
        def __init__(self, fd): self.iterator = real(fd)
        def __enter__(self): return self
        def __exit__(self, *args): self.iterator.close()
        def __iter__(self): return self
        def __next__(self):
            value = next(self.iterator); yielded.append(value.name); return value
    monkeypatch.setattr(module.os, 'scandir', Observed)
    with pytest.raises(module.Refusal, match='inventory_entry_budget'): module.build_inventory()
    assert len(yielded) == 4


def test_different_device_entry_refuses_before_descent(inventory, monkeypatch):
    module, work = inventory
    file(work / 'foreign/data'); real = module.os.stat
    def changed(path, *args, **kwargs):
        info = real(path, *args, **kwargs)
        if path == 'foreign':
            values = {name: getattr(info, name) for name in ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid',
                       'st_nlink', 'st_size', 'st_blocks', 'st_mtime_ns', 'st_ctime_ns')}
            values['st_dev'] += 1
            return SimpleNamespace(**values)
        return info
    monkeypatch.setattr(module.os, 'stat', changed)
    with pytest.raises(module.Refusal, match='inventory_filesystem'): module.build_inventory()


def test_changed_file_between_scans_refuses(inventory, monkeypatch):
    module, work = inventory
    path = file(work/'data')
    original = module.inventory_scan; calls = []
    def changed(*args, **kwargs):
        result = original(*args, **kwargs); calls.append(1)
        if len(calls) == 1: path.write_bytes(b'changed')
        return result
    monkeypatch.setattr(module, 'inventory_scan', changed)
    with pytest.raises(module.Refusal, match='inventory_changed'): module.build_inventory()


def test_no_active_mount_refuses(inventory):
    module, _ = inventory; module._active = None
    with pytest.raises(module.Refusal, match='inventory_'): module.build_inventory()


def test_deadline_expiry_during_walk_refuses(inventory, monkeypatch):
    module, work = inventory
    file(work/'a/item'); calls = []
    original = module._remaining
    def remaining(*args, **kwargs):
        calls.append(1)
        if len(calls) > 5: raise module.Refusal('deadline')
        return original(*args, **kwargs)
    monkeypatch.setattr(module, '_remaining', remaining)
    with pytest.raises(module.Refusal, match='deadline'): module.build_inventory()


def test_invalid_capacity_refuses(inventory, monkeypatch):
    module, _ = inventory
    monkeypatch.setattr(module.os, 'fstatvfs', lambda fd: SimpleNamespace(f_blocks=2**22, f_frsize=4096, f_bfree=1, f_bavail=1))
    with pytest.raises(module.Refusal, match='inventory_capacity'): module.build_inventory()
