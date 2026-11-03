"""Native storage inspection binds live identities without enabling allocation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def native():
    path = Path(__file__).with_name("probe_openshell_storage_native.py")
    assert path.is_file(), "Native storage inspector absent: expected red-first failure"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("openshell_native_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


@pytest.fixture
def fixture(native, tmp_path, monkeypatch):
    root = tmp_path.resolve() / "openshell"
    run = root / "storage-qualification/openshell-s-000000000001"
    runtime = run / "runtime"
    home = runtime / "controller"
    cache = home / "Library/Caches/lima"
    for directory in (root, run.parent, run, runtime, home, home / "Library",
                      home / "Library/Caches", cache,
                      *(home / name for name in ("tmp", "config", "data", "state", "cache"))):
        directory.mkdir(mode=0o700)
    image = run / "quota-test.raw"
    with image.open("wb") as stream:
        stream.truncate(768 * 1024**2)
    image.chmod(0o600)
    info = image.stat()
    selected = {
        "schema_version": 1, "profile": "mechanism", "pilot_root": str(root),
        "run_root": str(run), "image_path": str(image),
        "image_device": info.st_dev, "image_inode": info.st_ino,
        "container_uuid": "11111111-1111-4111-8111-111111111111",
        "runtime_uuid": "22222222-2222-4222-8222-222222222222",
        "cache_uuid": "33333333-3333-4333-8333-333333333333",
    }
    selection = native.parse_selection(json.dumps(selected).encode())
    capacity = 768 * 1024**2 - 40960
    attachment = {
        "image-path": str(image), "image-type": "read/write disk image",
        "image-encrypted": False, "owner-uid": os.getuid(), "owner-mode": 0o600,
        "writeable": True, "blockcount": 768 * 1024**2 // 512, "blocksize": 512,
        "system-entities": [
            {"content-hint": "GUID_partition_scheme", "dev-entry": "/dev/disk40"},
            {"content-hint": "7C3457EF-0000-11AA-AA11-00306543ECAC", "dev-entry": "/dev/disk40s1"},
            {"content-hint": "EF57347C-0000-11AA-AA11-00306543ECAC", "dev-entry": "/dev/disk41"},
            {"content-hint": "41504653-0000-11AA-AA11-00306543ECAC", "dev-entry": "/dev/disk41s1"},
            {"content-hint": "41504653-0000-11AA-AA11-00306543ECAC", "dev-entry": "/dev/disk41s2"},
        ],
    }
    container = {
        "APFSContainerUUID": selected["container_uuid"], "ContainerReference": "disk41",
        "CapacityCeiling": capacity, "CapacityFree": capacity - 65536,
        "DesignatedPhysicalStore": "disk40s1",
        "PhysicalStores": [{"DeviceIdentifier": "disk40s1", "Size": capacity,
                            "DiskUUID": "44444444-4444-4444-8444-444444444444"}],
        "Volumes": [
            {"APFSVolumeUUID": selected["runtime_uuid"], "DeviceIdentifier": "disk41s1",
             "CapacityQuota": 0, "CapacityReserve": 0, "CapacityInUse": 20480},
            {"APFSVolumeUUID": selected["cache_uuid"], "DeviceIdentifier": "disk41s2",
             "CapacityQuota": 32 * 1024**2, "CapacityReserve": 0, "CapacityInUse": 20480},
        ],
    }

    def mount(path, uuid, device):
        return {"MountPoint": str(path), "VolumeUUID": uuid, "DeviceIdentifier": device,
                "DeviceNode": "/dev/" + device, "APFSContainerReference": "disk41",
                "APFSPhysicalStores": [{"APFSPhysicalStore": "disk40s1"}],
                "FilesystemType": "apfs", "WritableVolume": True, "APFSContainerSize": capacity}

    responses = {
        "attachment": {"images": [attachment]}, "apfs": {"Containers": [container]},
        "runtime": mount(runtime, selected["runtime_uuid"], "disk41s1"),
        "cache": mount(cache, selected["cache_uuid"], "disk41s2"),
    }
    calls = []

    def command(argv, **kwargs):
        calls.append((argv, kwargs))
        assert kwargs["timeout"] <= 15 and kwargs["limit"] <= 1024**2
        assert set(kwargs["env"]) <= {"PATH", "LC_ALL", "HOME"}
        assert kwargs["cwd"] == run
        if argv == ["/usr/bin/hdiutil", "info", "-plist"]:
            key = "attachment"
        elif argv == ["/usr/sbin/diskutil", "apfs", "list", "-plist", "disk41"]:
            key = "apfs"
        elif argv == ["/usr/sbin/diskutil", "info", "-plist", str(runtime)]:
            key = "runtime"
        elif argv == ["/usr/sbin/diskutil", "info", "-plist", str(cache)]:
            key = "cache"
        else:
            pytest.fail("Unexpected native command")
        return native.CommandResult(0, plistlib.dumps(responses[key]), b"")

    original = native._observe_paths

    def paths(value, **kwargs):
        observed = original(value, **kwargs)
        return tuple(replace(item, device=9002 if item.path == cache else 9001)
                     if item.path == runtime or runtime in item.path.parents else item
                     for item in observed)

    monkeypatch.setattr(native, "run_command", command)
    monkeypatch.setattr(native, "_observe_paths", paths)
    monkeypatch.setattr(native, "_host_free", lambda path, **kwargs: 64 * 1024**3)
    return selection, selected, responses, calls


def test_live_binding_verified_but_never_enables_allocation(native, fixture):
    selection, _, _, calls = fixture
    report = native.validate_native_storage(selection, native.collect_native_storage(selection), "inspect")
    assert report.topology_verified and report.blockers == ()
    assert not report.allocation_enabled and not report.admitted
    assert report.required_free_bytes == 46 * 1024**3
    assert len(calls) == 8


@pytest.mark.parametrize("operation", ["create", "start", "workload_exec", "clone", "resize", "", True, {}])
def test_inspector_cannot_admit_operations(native, fixture, operation):
    selection, _, _, _ = fixture
    result = native.validate_native_storage(selection, native.collect_native_storage(selection), operation)
    assert not result.admitted and not result.allocation_enabled
    assert "unsupported_operation" in result.blockers


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("profile", "custom"), ("image_inode", True),
    ("image_device", -1), ("cache_uuid", "not-a-uuid"), ("runtime_uuid", "33333333-3333-4333-8333-333333333333"),
    ("pilot_root", "/private/../tmp"), ("run_root", "/tmp/elsewhere"),
    ("image_path", "/tmp/elsewhere.raw"), ("native_command", ["touch", "/tmp/escape"]),
    ("quota_verified", True), ("allocation_enabled", True),
])
def test_selection_is_closed_and_canonical(native, fixture, field, value):
    _, selected, _, _ = fixture
    selected[field] = value
    with pytest.raises(native.Refusal):
        native.parse_selection(json.dumps(selected).encode())


def test_duplicate_selection_fields_refuse(native, fixture):
    _, selected, _, _ = fixture
    raw = json.dumps(selected)[:-1] + ', "profile":"mechanism"}'
    with pytest.raises(native.Refusal):
        native.parse_selection(raw.encode())


def test_nonencodable_selection_path_refuses_before_filesystem_access(native, fixture):
    _, selected, _, calls = fixture
    old_root = selected["pilot_root"]
    for name in ("pilot_root", "run_root", "image_path"):
        selected[name] = selected[name].replace(old_root, old_root + "\ud800")
    with pytest.raises(native.Refusal):
        native.parse_selection(json.dumps(selected).encode())
    assert not calls


@pytest.mark.parametrize("change", [
    "duplicate_attachment", "shadow", "wrong_image_capacity", "readonly_image", "foreign_owner",
    "foreign_store", "extra_store", "wrong_container", "wrong_volume", "quota_zero", "quota_large",
    "quota_missing", "quota_boolean", "cache_unmounted", "cache_readonly", "cache_foreign_device",
    "escaped_mount", "foreign_mount_store", "native_device_argument", "extra_volume", "unknown_entity",
])
def test_contradictory_native_observation_refuses(native, fixture, change):
    selection, _, responses, _ = fixture
    image = responses["attachment"]["images"][0]
    container = responses["apfs"]["Containers"][0]
    cache = responses["cache"]
    if change == "duplicate_attachment":
        responses["attachment"]["images"].append(deepcopy(image))
    elif change == "shadow":
        image["shadow-path"] = "/private/synthetic.shadow"
    elif change == "wrong_image_capacity":
        image["blockcount"] += 1
    elif change == "readonly_image":
        image["writeable"] = False
    elif change == "foreign_owner":
        image["owner-uid"] += 1
    elif change == "foreign_store":
        container["PhysicalStores"][0]["DeviceIdentifier"] = "disk99s1"
    elif change == "extra_store":
        container["PhysicalStores"].append(deepcopy(container["PhysicalStores"][0]))
    elif change == "wrong_container":
        container["APFSContainerUUID"] = selection.cache_uuid
    elif change == "wrong_volume":
        cache["VolumeUUID"] = selection.runtime_uuid
    elif change.startswith("quota_"):
        volume = container["Volumes"][1]
        if change == "quota_missing":
            del volume["CapacityQuota"]
        else:
            volume["CapacityQuota"] = {"quota_zero": 0, "quota_large": 2 * 1024**3,
                                       "quota_boolean": True}[change]
    elif change == "cache_unmounted":
        cache["MountPoint"] = ""
    elif change == "cache_readonly":
        cache["WritableVolume"] = False
    elif change == "cache_foreign_device":
        cache["DeviceIdentifier"] = "disk99s1"
    elif change == "escaped_mount":
        cache["MountPoint"] = "/private/synthetic"
    elif change == "foreign_mount_store":
        cache["APFSPhysicalStores"][0]["APFSPhysicalStore"] = "disk99s1"
    elif change == "native_device_argument":
        image["system-entities"][2]["dev-entry"] = "/dev/--unsafe"
    elif change == "extra_volume":
        container["Volumes"].append(deepcopy(container["Volumes"][1]))
    elif change == "unknown_entity":
        image["system-entities"][1]["content-hint"] = "unknown-format"
    try:
        observation = native.collect_native_storage(selection)
    except native.Refusal:
        return
    assert not native.validate_native_storage(selection, observation, "inspect").topology_verified


@pytest.mark.parametrize("kind", ["image_replaced", "image_hardlink", "image_symlink", "public_image", "home_symlink"])
def test_filesystem_aliases_refuse_before_native_calls(native, fixture, kind):
    selection, _, _, calls = fixture
    if kind == "image_replaced":
        selection.image_path.unlink()
        selection.image_path.write_bytes(b"replacement")
        selection.image_path.chmod(0o600)
    elif kind == "image_hardlink":
        os.link(selection.image_path, selection.run_root / "second-link")
    elif kind == "image_symlink":
        original = selection.run_root / "original.raw"
        selection.image_path.rename(original)
        selection.image_path.symlink_to(original)
    elif kind == "public_image":
        selection.image_path.chmod(0o644)
    else:
        original = selection.home_path.with_name("original")
        selection.home_path.rename(original)
        selection.home_path.symlink_to(original)
    with pytest.raises(native.Refusal):
        native.collect_native_storage(selection)
    assert not calls


def test_missing_cache_mount_cannot_fall_back_to_runtime_device(native, fixture, monkeypatch):
    selection, _, _, _ = fixture
    original = native._observe_paths
    monkeypatch.setattr(native, "_observe_paths", lambda value, **kwargs: tuple(
        replace(item, device=9001) if item.path == selection.cache_path else item
        for item in original(value, **kwargs)))
    result = native.validate_native_storage(selection, native.collect_native_storage(selection), "inspect")
    assert not result.topology_verified


def test_path_replacement_during_collection_refuses(native, fixture, monkeypatch):
    selection, _, _, _ = fixture
    original = native._observe_paths
    count = 0

    def changed(value, **kwargs):
        nonlocal count
        count += 1
        return tuple(replace(item, inode=item.inode + 1)
                     if count > 1 and item.path == selection.cache_path else item
                     for item in original(value, **kwargs))

    monkeypatch.setattr(native, "_observe_paths", changed)
    observation = native.collect_native_storage(selection)
    assert "storage_identity" in native.validate_native_storage(selection, observation, "inspect").blockers


def test_host_reserve_uses_parent_filesystem(native, fixture, monkeypatch):
    selection, _, _, _ = fixture
    seen = []

    def free(path, **kwargs):
        seen.append(path)
        return 46 * 1024**3 - 1

    monkeypatch.setattr(native, "_host_free", free)
    observation = native.collect_native_storage(selection)
    report = native.validate_native_storage(selection, observation, "inspect")
    assert seen and all(path == selection.pilot_root for path in seen)
    assert report.blockers == ("host_free_space",)
    assert not report.topology_verified


@pytest.mark.parametrize("failure", ["timeout", "output_limit", "nonzero", "malformed", "duplicate_plist"])
def test_native_failures_are_path_free_and_bounded(native, fixture, monkeypatch, failure):
    selection, _, _, _ = fixture

    def fail(*args, **kwargs):
        if failure in {"timeout", "output_limit"}:
            raise native.CommandRefusal(failure)
        if failure == "nonzero":
            return native.CommandResult(1, b"private-path", b"private-secret")
        if failure == "duplicate_plist":
            raw = b'<?xml version="1.0"?><plist version="1.0"><dict><key>images</key><array/><key>images</key><array/></dict></plist>'
        else:
            raw = b"private malformed output"
        return native.CommandResult(0, raw, b"")

    monkeypatch.setattr(native, "run_command", fail)
    with pytest.raises(native.Refusal) as error:
        native.collect_native_storage(selection)
    assert "private" not in str(error.value) and "/" not in str(error.value)


def test_observation_is_typed_and_not_a_stored_success_receipt(native, fixture):
    selection, _, _, _ = fixture
    report = native.validate_native_storage(selection, {"topology_verified": True}, "inspect")
    assert not report.topology_verified and not report.allocation_enabled


def test_device_names_and_paths_normalize_without_options(native):
    assert native.normalize_device("disk40s1") == "disk40s1"
    assert native.normalize_device("/dev/disk40s1") == "disk40s1"
    for value in ("/tmp/disk40", "--help", "disk40/../disk1", "disk40;touch", True, "disk-1"):
        with pytest.raises(native.Refusal):
            native.normalize_device(value)


def test_pilot_profile_validates_exact_capacity_and_cache_topology(native, fixture):
    mechanism, selected, _, _ = fixture
    original = native.collect_native_storage(mechanism)
    run = mechanism.pilot_root / "qualification/openshell-q-000000000002"
    selected.update(profile="pilot", run_root=str(run), image_path=str(run / "runtime.raw"))
    pilot = native.parse_selection(json.dumps(selected).encode())
    assert pilot.image_bytes == 24 * 1024**3 and pilot.cache_bytes == 2 * 1024**3
    assert pilot.home_path == run / "lima/_controller"
    assert pilot.cache_path == pilot.home_path / "Library/Caches/lima"
    capacity = pilot.image_bytes - 40960
    old = original.native_before
    snapshot = replace(old,
                       attachment=replace(old.attachment, image_path=str(pilot.image_path), image_bytes=pilot.image_bytes),
                       container=replace(old.container, capacity=capacity, physical_size=capacity,
                                         free=capacity - 65536, cache=replace(old.container.cache, quota=pilot.cache_bytes)),
                       runtime=replace(old.runtime, mountpoint=str(pilot.runtime_path), capacity=capacity),
                       cache=replace(old.cache, mountpoint=str(pilot.cache_path), capacity=capacity))
    mapping = dict(zip(native._paths(mechanism), native._paths(pilot), strict=True))
    identities = tuple(replace(item, path=mapping[item.path],
                               size=pilot.image_bytes if item.path == mechanism.image_path else item.size)
                       for item in original.before)
    observation = replace(original, before=identities, after=identities, native_before=snapshot, native_after=snapshot)
    report = native.validate_native_storage(pilot, observation, "inspect")
    assert report.topology_verified and not report.allocation_enabled
    assert report.inventory_qualification == "not_run"
    wrong_cache = replace(snapshot, container=replace(snapshot.container,
                          cache=replace(snapshot.container.cache, quota=32 * 1024**2)))
    assert not native.validate_native_storage(pilot, replace(observation, native_after=wrong_cache), "inspect").topology_verified


def test_changed_native_identity_refuses_even_when_each_snapshot_valid(native, fixture):
    selection, _, _, _ = fixture
    observation = native.collect_native_storage(selection)
    snapshot = observation.native_after
    changed = replace(snapshot, container=replace(snapshot.container,
                      physical_uuid="55555555-5555-4555-8555-555555555555"))
    report = native.validate_native_storage(selection, replace(observation, native_after=changed), "inspect")
    assert report.blockers == ("native_changed",)


def test_collection_never_executes_malformed_native_device(native, fixture):
    selection, _, responses, calls = fixture
    responses["attachment"]["images"][0]["system-entities"][2]["dev-entry"] = "/dev/--help"
    with pytest.raises(native.Refusal):
        native.collect_native_storage(selection)
    assert [call[0] for call in calls] == [["/usr/bin/hdiutil", "info", "-plist"]]


def test_reconstructed_selection_with_invalid_field_refuses_cleanly(native, fixture):
    selection, _, _, calls = fixture
    for invalid in (replace(selection, image_inode=object()), replace(selection, profile={"x"}),
                    replace(selection, image_path="/tmp/image.raw")):
        with pytest.raises(native.Refusal):
            native.collect_native_storage(invalid)
    assert not calls


@pytest.mark.parametrize("change", ["boolean_free", "bad_snapshot", "bad_image", "bad_volume", "bad_path"])
def test_malformed_typed_observation_is_refused(native, fixture, change):
    selection, _, _, _ = fixture
    observation = native.collect_native_storage(selection)
    if change == "boolean_free":
        observation = replace(observation, free_bytes=True)
    elif change == "bad_snapshot":
        observation = replace(observation, native_before={})
    elif change == "bad_image":
        observation = replace(observation, native_before=replace(observation.native_before, attachment={}))
    elif change == "bad_volume":
        snapshot = observation.native_before
        observation = replace(observation, native_before=replace(snapshot, container=replace(snapshot.container, cache={})))
    else:
        observation = replace(observation, before=(*observation.before[:-1], {}))
    assert not native.validate_native_storage(selection, observation, "inspect").topology_verified


def test_cli_only_accepts_inspect_operation(native, tmp_path):
    outcome = subprocess.run([sys.executable, native.__file__, "--selection", str(tmp_path / "missing.json"),
                              "--operation", "start"], capture_output=True, timeout=5)
    assert outcome.returncode == 2
    assert b"invalid choice" in outcome.stderr


def test_expired_deadline_refuses_before_native_or_filesystem_collection(native, fixture, monkeypatch):
    selection, _, _, calls = fixture
    monkeypatch.setattr(native, "time", SimpleNamespace(monotonic=lambda: 100.0), raising=False)

    def forbidden(*args, **kwargs):
        pytest.fail("Expired collection reached filesystem inspection")

    monkeypatch.setattr(native, "_observe_paths", forbidden)
    with pytest.raises(native.Refusal, match="storage_deadline"):
        native.collect_native_storage(selection, deadline=100.0)
    assert not calls


@pytest.mark.parametrize("deadline", [True, 100, float("nan"), float("inf"), float("-inf"), "100"])
def test_deadline_requires_finite_float(native, fixture, deadline):
    selection, _, _, calls = fixture
    with pytest.raises(native.Refusal, match="invalid_deadline"):
        native.collect_native_storage(selection, deadline=deadline)
    assert not calls


@pytest.mark.parametrize("deadline,first,last", [(103.5, 3.5, 1.75), (1000.0, 10.0, 10.0)])
def test_native_query_timeouts_share_remaining_deadline(native, fixture, monkeypatch, deadline, first, last):
    selection, _, _, calls = fixture
    clock = [100.0]
    monkeypatch.setattr(native, "time", SimpleNamespace(monotonic=lambda: clock[0]), raising=False)
    original = native.run_command

    def timed(*args, **kwargs):
        result = original(*args, **kwargs)
        clock[0] += 0.25
        return result

    monkeypatch.setattr(native, "run_command", timed)
    observation = native.collect_native_storage(selection, deadline=deadline)
    assert native.validate_native_storage(selection, observation, "inspect").topology_verified
    assert calls[0][1]["timeout"] == first and calls[-1][1]["timeout"] == last


@pytest.mark.parametrize("expire_on", [1, 8])
def test_expiry_during_native_query_sequence_never_returns_success(native, fixture, monkeypatch, expire_on):
    selection, _, _, calls = fixture
    clock = [100.0]
    monkeypatch.setattr(native, "time", SimpleNamespace(monotonic=lambda: clock[0]), raising=False)
    original = native.run_command

    def timed(*args, **kwargs):
        result = original(*args, **kwargs)
        if len(calls) == expire_on:
            clock[0] = 101.0
        return result

    monkeypatch.setattr(native, "run_command", timed)
    with pytest.raises(native.Refusal, match="storage_deadline"):
        native.collect_native_storage(selection, deadline=101.0)
    assert len(calls) == expire_on


def test_path_observation_checks_deadline_between_filesystem_steps(native, fixture, monkeypatch):
    selection, _, _, _ = fixture
    clock = [100.0]
    seen = []
    monkeypatch.setattr(native, "time", SimpleNamespace(monotonic=lambda: clock[0]), raising=False)
    original = Path.lstat

    def expires(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        seen.append(path)
        clock[0] = 101.0
        return result

    monkeypatch.setattr(Path, "lstat", expires)
    with pytest.raises(native.Refusal, match="storage_deadline"):
        native._observe_paths(selection, deadline=101.0)
    assert seen == [selection.pilot_root]


@pytest.mark.parametrize("mode", [2**32, 2**63 - 1])
def test_large_stat_mode_refuses_without_overflow(native, fixture, mode):
    selection, _, _, _ = fixture
    observed = native.collect_native_storage(selection)
    records = (replace(observed.before[0], mode=mode), *observed.before[1:])
    report = native.validate_native_storage(selection, replace(observed, before=records, after=records), "inspect")
    assert not report.topology_verified


def test_running_native_validation_allows_only_mutable_usage(native, fixture):
    selection, _, _, _ = fixture
    observed = native.collect_native_storage(selection)
    after = tuple(replace(item, allocated=item.allocated + 4096,
                          size=item.size + 16 if stat.S_ISDIR(item.mode) else item.size)
                  for item in observed.after)
    snapshot = observed.native_after
    changed = replace(snapshot, container=replace(snapshot.container, free=snapshot.container.free - 8192,
                      runtime=replace(snapshot.container.runtime, in_use=snapshot.container.runtime.in_use + 4096),
                      cache=replace(snapshot.container.cache, in_use=snapshot.container.cache.in_use + 4096)))
    observed = replace(observed, after=after, native_after=changed)
    assert not native.validate_native_storage(selection, observed, "inspect").topology_verified
    report = native.validate_running_native_storage(selection, observed)
    assert report.topology_verified and not report.allocation_enabled
    assert observed.native_after.container.cache.in_use > observed.native_before.container.cache.in_use


@pytest.mark.parametrize("change", ["image_inode", "image_length", "directory_owner", "directory_mode", "directory_links",
                                    "store_uuid", "quota", "mountpoint"])
def test_running_native_validation_preserves_stable_binding(native, fixture, change):
    selection, _, _, _ = fixture
    observed = native.collect_native_storage(selection)
    if change.startswith("image_") or change.startswith("directory_"):
        index = next(index for index, item in enumerate(observed.after)
                     if item.path == (selection.image_path if change.startswith("image_") else selection.home_path))
        item = observed.after[index]
        field = {"image_inode": "inode", "image_length": "size", "directory_owner": "uid",
                 "directory_mode": "mode", "directory_links": "links"}[change]
        after = (*observed.after[:index], replace(item, **{field: getattr(item, field) + 1}), *observed.after[index + 1:])
        observed = replace(observed, after=after)
    else:
        snapshot = observed.native_after
        if change == "store_uuid":
            snapshot = replace(snapshot, container=replace(snapshot.container, physical_uuid="55555555-5555-4555-8555-555555555555"))
        elif change == "quota":
            snapshot = replace(snapshot, container=replace(snapshot.container, cache=replace(snapshot.container.cache, quota=0)))
        else:
            snapshot = replace(snapshot, cache=replace(snapshot.cache, mountpoint="/private/not-the-cache"))
        observed = replace(observed, native_after=snapshot)
    assert not native.validate_running_native_storage(selection, observed).topology_verified


def test_running_native_collection_uses_existing_bounded_queries(native, fixture, monkeypatch):
    selection, _, _, calls = fixture
    monkeypatch.setattr(native, "time", SimpleNamespace(monotonic=lambda: 100.0))
    observed = native.collect_running_native_storage(selection, deadline=102.0)
    assert native.validate_running_native_storage(selection, observed).topology_verified
    assert len(calls) == 8 and all(kwargs["timeout"] == 2.0 for _, kwargs in calls)


def test_running_native_identity_can_preserve_safe_stop_under_usage_pressure(native, fixture):
    selection, _, _, _ = fixture
    observed = native.collect_native_storage(selection)
    snapshot = observed.native_before
    snapshot = replace(snapshot, container=replace(snapshot.container,
                       cache=replace(snapshot.container.cache, in_use=selection.cache_bytes + 1)))
    pressure = replace(observed, free_bytes=1, native_before=snapshot, native_after=snapshot)
    assert not native.validate_running_native_storage(selection, pressure).topology_verified
    assert native.validate_running_native_storage_identity(selection, pressure).topology_verified
    native.assert_same_running_binding(observed, pressure)
    bad_quota = replace(snapshot, container=replace(snapshot.container,
                        cache=replace(snapshot.container.cache, quota=selection.cache_bytes + 1)))
    changed = replace(pressure, native_before=bad_quota, native_after=bad_quota)
    assert not native.validate_running_native_storage_identity(selection, changed).topology_verified
    with pytest.raises(native.Refusal, match="storage_changed"):
        native.assert_same_running_binding(observed, changed)
