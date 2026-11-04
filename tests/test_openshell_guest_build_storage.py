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


@pytest.mark.parametrize("probe", ["codex-version", "codex-help", "codex-empty-login", "codex-stdio",
                                   "opencode-version", "opencode-help", "opencode-rg"])
@pytest.mark.parametrize("mode", ["unfiltered", "upstream", "patched"])
def test_agent_profile_has_only_one_writable_case_and_temp_aliases(storage, probe, mode):
    case = f"{probe}-{mode}"
    root = storage.WORK / "agent-cases-1" / case
    properties = storage._properties(False, 60, agent_case=case)
    assert f"ReadOnlyPaths={storage.WORK} {root}/config" in properties
    assert f"ReadWritePaths={root}" in properties
    assert f"BindPaths={storage.WORK}:{storage.WORK}:norbind {root}/tmp:/tmp:norbind {root}/tmp:/var/tmp:norbind" in properties
    assert f"WorkingDirectory={root}/workspace" in properties
    assert "PrivateNetwork=yes" in properties and "UMask=0077" in properties
    assert "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX" in properties
    assert not any(str(storage.WORK / "tmp") in value for value in properties)
    ordinary = storage._properties(False, 60)
    changed = {value.split("=", 1)[0] for value in set(properties) ^ set(ordinary)}
    assert changed == {"ReadOnlyPaths", "ReadWritePaths", "BindPaths", "WorkingDirectory"}


@pytest.mark.parametrize("case", [True, 1, "", "../codex-version-patched", "codex-version", "codex-version-unix", "opencode-rg-patched/child"])
def test_agent_profile_rejects_unselected_identity_before_native_effects(storage, monkeypatch, case):
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    monkeypatch.setattr(storage, "_verify", lambda *a, **k: pytest.fail("unselected case reached native verification"))
    with pytest.raises(storage.Refusal, match="unit_contract"):
        storage.run_unit("print('fixed')", agent_case=case)


@pytest.mark.parametrize("network,library_tests", [(True, False), (False, True), (True, True)])
def test_agent_profile_cannot_enable_network_or_library_exceptions(storage, network, library_tests):
    with pytest.raises(storage.Refusal, match="unit_contract"):
        storage._properties(network, 60, library_tests=library_tests, agent_case="codex-version-patched")


def test_agent_unit_validates_case_and_relocates_every_write_environment(storage, monkeypatch):
    case = "opencode-rg-patched"
    root = storage.WORK / "agent-cases-1" / case
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    monkeypatch.setattr(storage.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(storage, "_verify", lambda *a, **k: None)
    monkeypatch.setattr(storage, "_visible_system", lambda *a: None)
    checked = []
    monkeypatch.setattr(storage, "_validate_agent_case", lambda selected: checked.append(selected), raising=False)
    monkeypatch.setattr(storage, "_unit_stopped", lambda *a: None)
    calls = []
    def command(argv, deadline, **kwargs):
        calls.append(argv)
        return {"returncode": 0, "stdout": b"fixed", "stderr": b""}
    monkeypatch.setattr(storage, "_command", command)
    assert storage.run_unit("print('fixed')", agent_case=case)["stdout"] == b"fixed"
    assert checked == [case, case]
    for key, relative in {"HOME": "home", "CODEX_HOME": "codex", "CARGO_HOME": "cargo",
                          "RUSTUP_HOME": "rustup", "TMPDIR": "tmp", "XDG_CONFIG_HOME": "config",
                          "XDG_CACHE_HOME": "cache", "XDG_DATA_HOME": "data", "XDG_STATE_HOME": "state",
                          "CARGO_TARGET_DIR": "target"}.items():
        assert f"--setenv={key}={root / relative}" in calls[0]
        assert f"{key}={root / relative}" in calls[0]


@pytest.mark.parametrize("corrupt", [None, "symlink", "missing", "mode", "owner"])
def test_agent_case_validation_uses_real_nofollow_directories(storage, tmp_path, monkeypatch, corrupt):
    import os
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    cases = work / "agent-cases-1"
    cases.mkdir(mode=0o700)
    root = cases / "opencode-rg-patched"
    root.mkdir(mode=0o700)
    for name in ("home", "codex", "config", "config/opencode", "data", "state", "cache",
                 "tmp", "workspace", "logs", "cargo", "rustup", "target"):
        (root / name).mkdir(mode=0o700)
    if corrupt in {"missing", "symlink"}:
        (root / "tmp").rmdir()
        if corrupt == "symlink":
            (root / "tmp").symlink_to(root / "home", target_is_directory=True)
    elif corrupt == "mode":
        (root / "config").chmod(0o777)
    original = os.fstat
    def fstat(fd):
        values = list(original(fd))
        values[4] = 0 if corrupt == "owner" else 65534
        values[5] = 65534
        return os.stat_result(values)
    monkeypatch.setattr(storage.os, "fstat", fstat)
    monkeypatch.setattr(storage, "WORK", work)
    monkeypatch.setattr(storage, "_remaining", lambda deadline: 10.0)
    if corrupt:
        with pytest.raises(storage.Refusal, match="agent_case_identity"):
            storage._validate_agent_case("opencode-rg-patched")
    else:
        storage._validate_agent_case("opencode-rg-patched")


@pytest.fixture
def binding_env(storage, tmp_path, monkeypatch):
    """Real tiny files; mock Linux root/Btrfs observations, never native effects."""
    import json
    import os
    root = tmp_path.resolve() / "retained"
    root.mkdir(mode=0o711)
    (root / "store").mkdir(mode=0o700)
    image = root / "image.raw"
    image.write_bytes(b"unchanged capped image fixture")
    image.chmod(0o600)
    info = image.lstat()
    identity = [54, info.st_ino, info.st_mode, 0, 0, 1, storage.IMAGE_BYTES]
    receipt = {"schema_version": 1, "uuid": "01234567-1234-4234-8234-0123456789ab",
               "image_identity": identity, "fixture_verified": True}
    receipt_raw = json.dumps(receipt).encode()
    (root / "receipt.json").write_bytes(receipt_raw)
    (root / "receipt.json").chmod(0o600)
    state = {"device": 52, "mount_id": 53, "tree_id": 256,
             "fsid": bytes.fromhex("11" * 16), "subvolume_uuid": bytes.fromhex("22" * 16),
             "inner_uuid": receipt["uuid"], "fds": {}, "commands": [], "mount_calls": []}
    original_open, original_close, original_fstat = os.open, os.close, os.fstat
    original_stat, original_lstat = Path.stat, Path.lstat
    original_read = storage._read
    def adjusted(info, path):
        if path is not None and (path == root.parent or path.is_relative_to(root)):
            fields = list(info)
            fields[2], fields[4], fields[5] = state["device"], 0, 0
            if storage.stat.S_ISDIR(info.st_mode):
                fields[3] = 1  # Linux Btrfs directories do not count regular child files as links.
            if path == image:
                fields[6] = storage.IMAGE_BYTES
            return os.stat_result(fields)
        return info
    def opened(path, flags, *args, **kwargs):
        fd = original_open(path, flags, *args, **kwargs)
        selected = Path(os.fsdecode(path))
        if selected.is_absolute() and (selected == root.parent or selected.is_relative_to(root)):
            state["fds"][fd] = selected
        return fd
    def closed(fd):
        state["fds"].pop(fd, None)
        original_close(fd)
    monkeypatch.setattr(storage.os, "open", opened)
    monkeypatch.setattr(storage.os, "close", closed)
    monkeypatch.setattr(storage.os, "fstat", lambda fd: adjusted(original_fstat(fd), state["fds"].get(fd)))
    monkeypatch.setattr(Path, "stat", lambda path, *a, **k: adjusted(original_stat(path, *a, **k), path))
    monkeypatch.setattr(Path, "lstat", lambda path, *a, **k: adjusted(original_lstat(path, *a, **k), path))
    monkeypatch.setattr(storage, "ROOT", root)
    monkeypatch.setattr(storage.os, "geteuid", lambda: 0)
    monkeypatch.setattr(storage.sys, "platform", "linux")
    def read(path, limit=65536):
        if str(path).startswith("/proc/self/fdinfo/"):
            fd = int(path.name)
            return f"mnt_id: {state['mount_id']}\nino: {os.fstat(fd).st_ino}\n".encode()
        return original_read(path, limit)
    monkeypatch.setattr(storage, "_read", read)
    monkeypatch.setattr(storage, "_mounts", lambda: f"{state['mount_id']} 1 0:35 /var / rw - btrfs /dev/vda3 rw\n".encode())
    monkeypatch.setattr(storage, "_is_mounted", lambda mount: state.get("mounted", False))
    monkeypatch.setattr(storage, "_associated", lambda image, deadline: state.get("loops", []))
    def ioctl(fd, request, buffer):
        assert fd in state["fds"] and not any(buffer)
        if state.get("ioctl_error"):
            raise OSError("unsupported native ioctl")
        size = {0x8400941f: 1024, 0x81f8943c: 504}[request]
        assert len(buffer) == size
        result = bytearray(size)
        if request == 0x8400941f:
            result[16:32] = state["fsid"]
        else:
            storage.struct.pack_into("=Q", result, 0, state["tree_id"])
            result[296:312] = state["subvolume_uuid"]
            if state.get("conflict") and state["fds"][fd].name == "receipt.json":
                result[296] ^= 1
        return bytes(result[:-1] if state.get("short_ioctl") else result)
    monkeypatch.setattr(storage.fcntl, "ioctl", ioctl)
    def command(argv, deadline, **kwargs):
        assert argv[:4] == ["/usr/sbin/blkid", "-p", "-s", argv[3]]
        assert argv[3] in {"TYPE", "UUID"} and argv[4:6] == ["-o", "value"]
        assert argv[6].startswith(f"/proc/{os.getpid()}/fd/")
        fd = int(argv[6].rsplit("/", 1)[1])
        assert state["fds"][fd] == image
        state["commands"].append(argv)
        value = "ext4" if argv[3] == "TYPE" else state["inner_uuid"]
        if argv[3] == "UUID" and state.get("after_blkid"):
            state["after_blkid"]()
        return {"returncode": 0, "stdout": (value + "\n").encode(), "stderr": b""}
    monkeypatch.setattr(storage, "_command", command)
    from contextlib import contextmanager
    @contextmanager
    def mounted(*args, **kwargs):
        state["mount_calls"].append(args)
        yield "verified store"
    monkeypatch.setattr(storage, "_mounted", mounted)
    state.update(root=root, image=image, receipt=receipt, receipt_raw=receipt_raw, host="a" * 64)
    yield state
    assert not state["fds"], "owned binding descriptors leaked"


def bind(storage, env):
    return storage.record_stable_binding(host_binding_sha256=env["host"], deadline=storage.time.monotonic() + 180.0)


def test_explicit_binding_preserves_legacy_and_reuses_after_device_renumber(storage, binding_env):
    import hashlib
    import json
    env = binding_env
    result = bind(storage, env)
    raw = (env["root"] / "binding.json").read_bytes()
    saved = json.loads(raw)
    assert result == {"schema_version": 1, "status": "storage_bound", "host_binding_sha256": env["host"],
        "legacy_receipt_sha256": hashlib.sha256(env["receipt_raw"]).hexdigest(),
        "binding_sha256": hashlib.sha256(raw).hexdigest(), "image_bytes": storage.IMAGE_BYTES,
        "unmounted_verified": True, "session_enabled": False, "historical_outer_identity_verified": False}
    assert saved["image_identity"] == env["receipt"]["image_identity"][1:]
    assert saved["btrfs"]["tree_id"] == 256 and len(raw) <= 8192
    assert env["mount_calls"] == []
    assert (env["root"] / "receipt.json").read_bytes() == env["receipt_raw"]
    env["device"], env["mount_id"] = 61, 91
    with storage.mounted_store(host_binding_sha256=env["host"]) as value:
        assert value == "verified store"
    assert env["mount_calls"][0][3][0] == 61
    assert (env["root"] / "binding.json").read_bytes() == raw
    assert env["image"].read_bytes() == b"unchanged capped image fixture"


@pytest.mark.parametrize("index", range(1, 7))
def test_binding_rejects_every_changed_non_device_legacy_field(storage, binding_env, index):
    import json
    env = binding_env
    env["receipt"]["image_identity"][index] += 1
    (env["root"] / "receipt.json").write_text(json.dumps(env["receipt"]))
    with pytest.raises(storage.Refusal):
        bind(storage, env)
    assert not (env["root"] / "binding.json").exists() and not env["mount_calls"]


@pytest.mark.parametrize("failure", ["host", "receipt", "fsid", "subvolume", "tree", "inner", "zero_fsid",
    "zero_subvolume", "zero_tree", "ioctl", "short_ioctl", "conflict", "loop", "mounted"])
def test_binding_native_and_stable_mismatches_refuse(storage, binding_env, failure):
    env = binding_env
    if failure in {"host", "receipt", "fsid", "subvolume", "tree"}:
        bind(storage, env)
    if failure == "host": env["host"] = "b" * 64
    elif failure == "receipt": (env["root"] / "receipt.json").write_bytes(env["receipt_raw"] + b" ")
    elif failure == "fsid": env["fsid"] = b"3" * 16
    elif failure == "subvolume": env["subvolume_uuid"] = b"4" * 16
    elif failure == "tree": env["tree_id"] += 1
    elif failure == "inner": env["inner_uuid"] = "11111111-1111-4111-8111-111111111111"
    elif failure == "zero_fsid": env["fsid"] = bytes(16)
    elif failure == "zero_subvolume": env["subvolume_uuid"] = bytes(16)
    elif failure == "zero_tree": env["tree_id"] = 0
    elif failure == "ioctl": env["ioctl_error"] = True
    elif failure == "short_ioctl": env["short_ioctl"] = True
    elif failure == "conflict": env["conflict"] = True
    elif failure == "loop": env["loops"] = ["/dev/loop7"]
    else: env["mounted"] = True
    with pytest.raises(storage.Refusal):
        if failure in {"host", "receipt", "fsid", "subvolume", "tree"}:
            with storage.mounted_store(host_binding_sha256=env["host"]):
                pytest.fail("accepted changed stable binding")
        else:
            bind(storage, env)
    assert not env["mount_calls"]


@pytest.mark.parametrize("mutation", ["partial", "duplicate", "unknown", "boolean", "missing_host", "oversize"])
def test_present_sidecar_never_falls_back_to_matching_legacy(storage, binding_env, mutation):
    import json
    env = binding_env
    bind(storage, env)
    path = env["root"] / "binding.json"
    raw = path.read_bytes()
    env["device"] = env["receipt"]["image_identity"][0]
    if mutation == "partial": path.write_bytes(b'{"schema_version":')
    elif mutation == "duplicate": path.write_bytes(b'{"schema_version":1,' + raw[1:])
    elif mutation == "unknown": path.write_text(json.dumps(json.loads(raw) | {"unexpected": 1}))
    elif mutation == "boolean": path.write_text(json.dumps(json.loads(raw) | {"schema_version": True}))
    elif mutation == "oversize": path.write_bytes(b" " * 8193)
    retained = path.read_bytes()
    with pytest.raises(storage.Refusal):
        with storage.mounted_store(host_binding_sha256=None if mutation == "missing_host" else env["host"]):
            pytest.fail("legacy fallback with sidecar present")
    assert path.read_bytes() == retained and not env["mount_calls"]


@pytest.mark.parametrize("change", ["device", "mount", "path"])
def test_binding_rechecks_descriptors_and_mounts_before_publication(storage, binding_env, change):
    env = binding_env
    def changed():
        if change == "device": env["device"] += 1
        elif change == "mount": env["mount_id"] += 1
        else:
            env["image"].rename(env["root"] / "original-image")
            env["image"].write_bytes(b"replacement")
            env["image"].chmod(0o600)
    env["after_blkid"] = changed
    with pytest.raises(storage.Refusal):
        bind(storage, env)
    assert not (env["root"] / "binding.json").exists()


def test_binding_existing_or_sync_failure_preserves_sidecar(storage, binding_env, monkeypatch):
    env = binding_env
    original_sync = storage.os.fsync
    def sync(fd):
        if env["fds"].get(fd) == env["root"] / "binding.json":
            raise OSError("injected fsync failure")
        original_sync(fd)
    monkeypatch.setattr(storage.os, "fsync", sync)
    with pytest.raises(storage.Refusal):
        bind(storage, env)
    path = env["root"] / "binding.json"
    assert path.exists()
    raw = path.read_bytes()
    monkeypatch.setattr(storage.os, "fsync", original_sync)
    with pytest.raises(storage.Refusal):
        bind(storage, env)
    assert path.read_bytes() == raw


def test_binding_partial_descriptor_acquisition_closes_owned_fds(storage, binding_env, monkeypatch):
    env = binding_env
    original = storage.os.open
    def opened(path, *args, **kwargs):
        if Path(path) == env["image"]:
            raise OSError("injected open failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(storage.os, "open", opened)
    with pytest.raises(storage.Refusal):
        bind(storage, env)
    assert not env["fds"] and not (env["root"] / "binding.json").exists()


@pytest.mark.parametrize("mutation", ["extra_entry", "replace_sidecar"])
def test_binding_publication_checks_exact_created_file_and_root_entries(storage, binding_env, monkeypatch, mutation):
    env = binding_env
    original = storage.os.fsync
    def sync(fd):
        original(fd)
        if env["fds"].get(fd) == env["root"]:
            path = env["root"] / "binding.json"
            if mutation == "extra_entry":
                (env["root"] / "unexpected").write_bytes(b"retain")
            else:
                data = path.read_bytes()
                path.unlink()
                path.write_bytes(data)
                path.chmod(0o600)
    monkeypatch.setattr(storage.os, "fsync", sync)
    with pytest.raises(storage.Refusal):
        bind(storage, env)
    assert (env["root"] / "binding.json").exists()
    assert (env["root"] / "receipt.json").read_bytes() == env["receipt_raw"]


def test_dangling_sidecar_refuses_both_binding_and_legacy_fallback(storage, binding_env):
    env = binding_env
    (env["root"] / "binding.json").symlink_to("missing")
    env["device"] = 54
    with pytest.raises(storage.Refusal):
        bind(storage, env)
    with pytest.raises(storage.Refusal):
        with storage.mounted_store(host_binding_sha256=env["host"]):
            pytest.fail("followed dangling sidecar")
    assert (env["root"] / "binding.json").is_symlink() and not env["mount_calls"]


def test_bound_body_failure_preserves_diagnostics_and_releases_descriptors(storage, binding_env, monkeypatch):
    from contextlib import contextmanager
    env = binding_env
    bind(storage, env)
    cleanup = []
    @contextmanager
    def mounted(*args, **kwargs):
        try:
            yield "store"
        finally:
            cleanup.append("exact mounted helper cleanup")
    monkeypatch.setattr(storage, "_mounted", mounted)
    with pytest.raises(storage.Refusal, match="^body_failed$") as caught:
        with storage.mounted_store(host_binding_sha256=env["host"]):
            raise storage.Refusal("body_failed", stderr=b"bounded original diagnostics")
    assert caught.value.stderr == b"bounded original diagnostics"
    assert cleanup == ["exact mounted helper cleanup"] and not env["fds"]


@pytest.mark.parametrize("mount_failure", [None, "read", "limit"])
def test_retained_image_mismatch_reports_identity_without_mounting(storage, tmp_path, monkeypatch, mount_failure):
    import json
    import os
    root = tmp_path / "retained"
    root.mkdir()
    (root / "store").mkdir()
    (root / "image.raw").write_bytes(b"retained image")
    recorded = (54, 413, 0o100600, 0, 0, 1, storage.IMAGE_BYTES)
    observed = (52, *recorded[1:])
    receipt = {"schema_version": 1, "uuid": "01234567-1234-1234-1234-0123456789ab",
               "image_identity": list(recorded), "fixture_verified": True}
    receipt_bytes = json.dumps(receipt).encode()
    (root / "receipt.json").write_bytes(receipt_bytes)
    monkeypatch.setattr(storage, "ROOT", root)
    monkeypatch.setattr(storage, "_root", lambda: os.open(root, os.O_RDONLY | os.O_DIRECTORY))
    monkeypatch.setattr(storage, "_private", lambda *args, **kwargs: observed)
    monkeypatch.setattr(storage, "_mounted", lambda *args, **kwargs: pytest.fail("mounted changed image"))
    def mounts():
        if mount_failure == "read": raise OSError("private arbitrary native text")
        if mount_failure == "limit": raise storage.Refusal("metadata_limit")
        return (f"72 1 0:35 /root / rw - btrfs /dev/vda3 rw\n"
                f"53 72 0:35 /var {root.parent} rw - btrfs /dev/vda3 rw\n"
                "99 72 0:99 / /unrelated rw - tmpfs tmpfs rw\n").encode()
    monkeypatch.setattr(storage, "_mounts", mounts)
    with pytest.raises(storage.Refusal, match="^image_changed$") as error:
        with storage.mounted_store():
            pytest.fail("admitted changed image")
    report = json.loads(error.value.stderr)
    assert report["reason"] == "image_changed"
    assert report["fields"] == ["device", "inode", "mode", "uid", "gid", "links", "size"]
    assert report["recorded"] == list(recorded) and report["observed"] == list(observed)
    assert len(error.value.stderr) <= 8192
    assert b"private arbitrary native text" not in error.value.stderr
    if mount_failure:
        assert report["mount_status"] == "unavailable" and report["mounts"] == []
    else:
        assert report["mount_status"] == "observed"
        assert {row["mount_point"] for row in report["mounts"]} == {"/", str(root.parent)}
        assert all(row["filesystem_type"] == "btrfs" for row in report["mounts"])
    assert (root / "receipt.json").read_bytes() == receipt_bytes
    assert (root / "image.raw").read_bytes() == b"retained image"
    assert storage._end is None and storage._work_end is None


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
    assert "AF_NETLINK" not in families and "UMask=0077" in properties


def test_library_context_adds_only_private_netlink_family(storage):
    ordinary = storage._properties(False, 120)
    tests = storage._properties(False, 120, library_tests=True)
    assert len(tests) == len(ordinary)
    differences = [(before, after) for before, after in zip(ordinary, tests) if before != after]
    assert differences == [("RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX",
                            "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX AF_NETLINK")]
    assert "UMask=0077" in tests and "PrivateNetwork=yes" in tests


@pytest.mark.parametrize("network,library_tests", [(True, True), (False, None), (False, 1), (False, "true"), (False, [])])
def test_invalid_library_context_refuses_before_any_effect(storage, monkeypatch, network, library_tests):
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    for name in ("_verify", "_visible_system", "_resolver", "_command"):
        monkeypatch.setattr(storage, name, lambda *a, **k: pytest.fail("effect before contract refusal"))
    with pytest.raises(storage.Refusal, match="unit_contract"):
        storage._properties(network, 120, library_tests=library_tests)
    with pytest.raises(storage.Refusal, match="unit_contract"):
        storage.run_unit("print('fixed source')", network=network, library_tests=library_tests)


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
@pytest.mark.parametrize("library_tests", [False, True])
def test_unit_always_stops_exact_service_and_preserves_byte_streams(storage, monkeypatch, failed, library_tests):
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
            storage.run_unit("print('source defined')", seconds=20, library_tests=library_tests)
    else:
        assert storage.run_unit("print('source defined')", seconds=20, library_tests=library_tests)["stdout"] == b"result"
    started = calls[0][0]
    unit = next(item.removeprefix("--unit=") for item in started if item.startswith("--unit="))
    assert "--pipe" in started and "--wait" in started
    families = next(item for item in started if item.startswith("--property=RestrictAddressFamilies="))
    assert ("AF_NETLINK" in families) is library_tests
    assert "--property=UMask=0077" in started and "--property=PrivateNetwork=yes" in started
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


def test_fedora_afs_root_is_admitted_only_with_explicit_mask(storage, monkeypatch):
    from contextlib import nullcontext
    info = SimpleNamespace(st_mode=0o040555, st_uid=0)
    entry = SimpleNamespace(name="afs", stat=lambda **kwargs: info)
    monkeypatch.setattr(storage, "_remaining", lambda *args: 1.0)
    monkeypatch.setattr(storage, "_mounts", lambda: b"")
    monkeypatch.setattr(storage.os, "scandir", lambda path: nullcontext(iter([entry] if path == "/" else [])))
    monkeypatch.setattr(storage.os, "open", lambda *args: 11)
    monkeypatch.setattr(storage.os, "close", lambda *args: None)
    monkeypatch.setattr(storage.os, "fstat", lambda *args: info)
    monkeypatch.setattr(Path, "lstat", lambda *args: info)
    storage._visible_system(100.0)
    for network in (False, True):
        hidden = next(item for item in storage._properties(network, 30) if item.startswith("InaccessiblePaths="))
        assert "-/afs" in hidden.split()


def test_visible_system_refusal_retains_only_bounded_entry_metadata(storage):
    import json
    info = SimpleNamespace(st_mode=0o100666, st_uid=123, st_gid=456)
    with pytest.raises(storage.Refusal) as caught:
        storage._safe_system_entry(info, path=Path("/usr/example"))
    assert str(caught.value) == "visible_system_mutable_or_socket"
    assert json.loads(caught.value.stderr) == {"path": "/usr/example", "uid": 123, "gid": 456, "mode": "0o100666"}
    assert len(caught.value.stderr) <= 4096


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


UNIT = "dotfiles-ai-openshell-build-" + "a" * 32 + ".service"


@pytest.mark.parametrize("load,active,sub", [("not-found", "inactive", "dead"), ("loaded", "inactive", "dead"),
                                           ("loaded", "failed", "failed")])
def test_unit_shutdown_accepts_only_proved_stopped_state_with_absent_exact_cgroup(storage, monkeypatch, load, active, sub):
    calls = []
    def command(argv, deadline, **kwargs):
        calls.append((argv, kwargs))
        return {"returncode": 0, "stdout": f"LoadState={load}\nActiveState={active}\nSubState={sub}\nControlGroup=\n".encode(), "stderr": b""}
    monkeypatch.setattr(storage, "_command", command)
    def absent(path):
        assert str(path) == f"/sys/fs/cgroup/system.slice/{UNIT}"
        raise FileNotFoundError
    monkeypatch.setattr(Path, "lstat", absent)
    storage._unit_stopped(UNIT, 100.0)
    assert calls[0][1]["check"] is False
    assert "LoadState" in calls[0][0][-1]


@pytest.mark.parametrize("returncode,present", [(1, False), (4, False), (0, True)])
def test_not_found_unit_never_waives_query_failure_or_retained_cgroup(storage, monkeypatch, returncode, present):
    monkeypatch.setattr(storage, "_command", lambda *a, **k: {"returncode": returncode, "stdout":
        b"LoadState=not-found\nActiveState=inactive\nSubState=dead\nControlGroup=\n", "stderr": b""})
    def observed(path):
        if present:
            return SimpleNamespace(st_mode=0o040755, st_uid=0)
        raise FileNotFoundError
    monkeypatch.setattr(Path, "lstat", observed)
    with pytest.raises(storage.Refusal, match="unit_shutdown_unverified"):
        storage._unit_stopped(UNIT, 100.0)


@pytest.mark.parametrize("shutdown_verified", [True, False])
def test_launch_failure_diagnostics_survive_stop_failure(storage, monkeypatch, shutdown_verified):
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    monkeypatch.setattr(storage.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(storage, "_verify", lambda *a, **k: None)
    monkeypatch.setattr(storage, "_visible_system", lambda *a: None)
    def command(argv, deadline, **kwargs):
        if argv[0].endswith("systemd-run"):
            return {"returncode": 17, "stdout": b"launch output", "stderr": b"original launch failure"}
        if kwargs.get("check", True):
            raise storage.Refusal("native_command_failed", stderr=b"unit not loaded")
        return {"returncode": 5, "stdout": b"", "stderr": b"unit not loaded"}
    monkeypatch.setattr(storage, "_command", command)
    def stopped(*args):
        if not shutdown_verified:
            raise storage.Refusal("unit_shutdown_unverified", stderr=b"state unavailable")
    monkeypatch.setattr(storage, "_unit_stopped", stopped)
    with pytest.raises(storage.Refusal) as caught:
        storage.run_unit("raise SystemExit(17)")
    assert str(caught.value) == ("unit_failed" if shutdown_verified else "unit_shutdown_unverified")
    assert caught.value.stdout == b"launch output"
    assert b"original launch failure" in caught.value.stderr
    assert caught.value.returncode == 17


@pytest.mark.parametrize("uid,gid", [(0, 0), (193, 193)])
def test_resolver_descriptor_accepts_only_known_root_or_resolve_principal(storage, uid, gid):
    info = SimpleNamespace(st_mode=0o100644, st_uid=uid, st_gid=gid, st_nlink=1, st_size=936)
    storage._validate_resolver_info(info, {(0, 0), (193, 193)})


@pytest.mark.parametrize("change", [{"st_uid": 65534}, {"st_gid": 65534}, {"st_mode": 0o100666},
                                   {"st_mode": 0o120644}, {"st_nlink": 2}, {"st_size": 65537}, {"st_size": 0}])
def test_resolver_descriptor_rejects_unsafe_metadata(storage, change):
    info = dict(st_mode=0o100644, st_uid=193, st_gid=193, st_nlink=1, st_size=936)
    with pytest.raises(storage.Refusal, match="resolver_identity"):
        storage._validate_resolver_info(SimpleNamespace(**(info | change)), {(0, 0), (193, 193)})


@pytest.mark.parametrize("raw", [b"nameserver 127.0.0.53\noptions edns0 trust-ad\nsearch .\n",
                                 b"# controlled DNS data\nnameserver 192.168.5.2\n"])
def test_resolver_snapshot_accepts_bounded_dns_data(storage, raw):
    storage._validate_resolver_data(raw)


@pytest.mark.parametrize("raw", [b"", b"nameserver hostname.example\n", b"nameserver 127.0.0.53\0\n",
                                 b"include /run/other\n", b"options edns0\n"])
def test_resolver_snapshot_refuses_non_dns_or_empty_input(storage, raw):
    with pytest.raises(storage.Refusal, match="resolver_data"):
        storage._validate_resolver_data(raw)


def test_network_unit_binds_only_private_snapshot_to_selected_dns_file(storage):
    snapshot = storage.ROOT / "store/runtime-config" / ("resolver-" + "a" * 32 + ".conf")
    target = Path("/run/systemd/resolve/stub-resolv.conf")
    resolver = storage.Resolver(snapshot, target, (1, 2))
    properties = storage._properties(True, 30, resolver=resolver)
    assert f"BindReadOnlyPaths={snapshot}:{target}:norbind" in properties
    assert "TemporaryFileSystem=/var:ro /run:ro" in properties
    assert not any(item == f"BindReadOnlyPaths={target}:{target}:norbind" for item in properties)
    with pytest.raises(storage.Refusal):
        storage._properties(False, 30, resolver=resolver)


@pytest.mark.parametrize("replace_source", [False, True])
def test_resolver_source_reads_one_bound_descriptor_and_refuses_replacement(storage, tmp_path, monkeypatch, replace_source):
    import os
    source = tmp_path / "dns"
    link = tmp_path / "resolv.conf"
    raw = b"nameserver 127.0.0.53\n"
    source.write_bytes(raw)
    source.chmod(0o644)
    link.symlink_to(source)
    original_lstat, original_fstat, original_read = Path.lstat, os.fstat, os.read
    def root_info(info):
        values = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
        return SimpleNamespace(**(values | {"st_uid": 0, "st_gid": 0}))
    monkeypatch.setattr(Path, "lstat", lambda path, *a, **k: root_info(original_lstat(path, *a, **k)))
    monkeypatch.setattr(storage.os, "fstat", lambda fd: root_info(original_fstat(fd)))
    monkeypatch.setattr(storage, "Path", lambda value: link if value == "/etc/resolv.conf" else Path(value))
    monkeypatch.setattr(storage, "_RESOLVER_TARGETS", {source})
    monkeypatch.setattr(storage, "_remaining", lambda *a: 1.0)
    descriptors = []
    def opened(target, principals):
        assert target == source and principals == {(0, 0)}
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        descriptors.append(fd)
        return fd
    monkeypatch.setattr(storage, "_open_resolver", opened)
    reads = 0
    def read(fd, size):
        nonlocal reads
        value = original_read(fd, min(size, 3))
        reads += 1
        if reads == 1 and replace_source:
            replacement = source.with_name("replacement")
            replacement.write_bytes(raw)
            replacement.chmod(0o644)
            replacement.replace(source)
        return value
    monkeypatch.setattr(storage.os, "read", read)
    if replace_source:
        with pytest.raises(storage.Refusal, match="resolver_changed"):
            storage._resolver_source(100.0)
    else:
        assert storage._resolver_source(100.0) == (source, raw)
        assert reads > 1
    with pytest.raises(OSError):
        original_fstat(descriptors[0])


@pytest.mark.parametrize("verified", [True, False])
def test_network_snapshot_retirement_waits_for_independent_unit_shutdown(storage, monkeypatch, verified):
    resolver = storage.Resolver(storage.ROOT / "store/runtime-config" / ("resolver-" + "a" * 32 + ".conf"),
                                Path("/run/systemd/resolve/stub-resolv.conf"), (1, 2))
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    monkeypatch.setattr(storage.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(storage, "_verify", lambda *a: None)
    monkeypatch.setattr(storage, "_visible_system", lambda *a: None)
    monkeypatch.setattr(storage, "_resolver", lambda *a: resolver)
    monkeypatch.setattr(storage, "_command", lambda *a, **k: {"returncode": 0, "stdout": b"ok", "stderr": b""})
    retired = []
    monkeypatch.setattr(storage, "_retire_resolver", lambda value: retired.append(value))
    def stopped(*args):
        if not verified:
            raise storage.Refusal("unit_shutdown_unverified")
    monkeypatch.setattr(storage, "_unit_stopped", stopped)
    if verified:
        assert storage.run_unit("print('fixed download stage')", network=True)["stdout"] == b"ok"
    else:
        with pytest.raises(storage.Refusal, match="unit_shutdown_unverified"):
            storage.run_unit("print('fixed download stage')", network=True)
    assert retired == ([resolver] if verified else [])


def test_resolver_retirement_failure_preserves_original_unit_diagnostics(storage, monkeypatch):
    resolver = storage.Resolver(storage.ROOT / "store/runtime-config" / ("resolver-" + "a" * 32 + ".conf"),
                                Path("/run/systemd/resolve/stub-resolv.conf"), (1, 2))
    monkeypatch.setattr(storage, "_active", SimpleNamespace())
    monkeypatch.setattr(storage, "_end", 200.0)
    monkeypatch.setattr(storage, "_work_end", 140.0)
    monkeypatch.setattr(storage.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(storage, "_verify", lambda *a: None)
    monkeypatch.setattr(storage, "_visible_system", lambda *a: None)
    monkeypatch.setattr(storage, "_resolver", lambda *a: resolver)
    monkeypatch.setattr(storage, "_unit_stopped", lambda *a: None)
    def command(argv, *args, **kwargs):
        return {"returncode": 17, "stdout": b"original output", "stderr": b"original failure"} if argv[0].endswith("systemd-run") else {"returncode": 0, "stdout": b"", "stderr": b""}
    monkeypatch.setattr(storage, "_command", command)
    def retirement(value):
        raise storage.Refusal("resolver_retirement_identity")
    monkeypatch.setattr(storage, "_retire_resolver", retirement)
    with pytest.raises(storage.Refusal, match="resolver_retirement_identity") as caught:
        storage.run_unit("raise SystemExit(17)", network=True)
    assert caught.value.stdout == b"original output"
    assert b"original failure" in caught.value.stderr
    assert caught.value.returncode == 17


@pytest.mark.parametrize("failure", ["lstat", "unlink"])
def test_resolver_retirement_normalizes_raw_filesystem_errors(storage, monkeypatch, failure):
    import errno
    info = SimpleNamespace(st_dev=1, st_ino=2, st_mode=0o100444, st_uid=0, st_gid=0,
                           st_nlink=1, st_size=20, st_mtime_ns=3, st_ctime_ns=4)
    resolver = storage.Resolver(Path("/owned/resolver.conf"), Path("/run/systemd/resolve/stub-resolv.conf"),
                                storage._resolver_identity(info))
    def unavailable(*args):
        raise OSError(errno.EIO, "private filesystem details")
    monkeypatch.setattr(Path, "lstat", unavailable if failure == "lstat" else lambda *a: info)
    monkeypatch.setattr(Path, "unlink", unavailable)
    with pytest.raises(storage.Refusal, match="^resolver_retirement_identity$") as caught:
        storage._retire_resolver(resolver)
    assert b"private filesystem details" not in caught.value.stderr
