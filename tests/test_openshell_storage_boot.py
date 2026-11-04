"""Closed boot qualification: fake every native effect and preserve failed state."""
from __future__ import annotations

from dataclasses import replace
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from test_openshell_storage_create import creator, prepared
from test_openshell_storage_inventory import inventory, mounted, private, owned_run


@pytest.fixture(scope="module")
def booter():
    path = Path(__file__).with_name("probe_openshell_storage_boot.py")
    assert path.exists(), "Boot runner absent: expected red-first failure"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("openshell_boot_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


def test_boot_requires_separate_closed_runner(booter):
    assert booter.QUALIFICATION_SECONDS == 900
    assert booter.SHUTDOWN_RESERVE >= 90


@pytest.fixture
def stopped(booter, creator, inventory, prepared, monkeypatch):
    selection, outputs, calls, original = prepared
    creator.create_worker(selection)
    calls.clear()
    monkeypatch.setattr(booter, "create", creator)
    monkeypatch.setattr(booter, "inventory", inventory)
    monkeypatch.setattr(inventory.native, "collect_running_native_storage", inventory.native.collect_native_storage)
    state = {"live": False, "start_error": None, "stop_error": None, "after_start": None,
             "after_stop": None, "before_start": None, "process_stamp": "Tue Nov 3 12:00:00 2026"}

    def command(argv, **kwargs):
        if argv[1] in {"start", "stop"}:
            calls.append((argv, kwargs))
            lock = os.open(selection.storage.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(lock)
            assert kwargs["limit"] == 1024**2 and 0 < kwargs["timeout"] <= 600
            assert kwargs["env"] == creator._environment(selection)
            if argv[1] == "start":
                assert argv == [str(creator.LIMA.resolve()), "start", "--tty=false", "--timeout", "10m", "q"]
                state["live"] = True
                outputs["lima"].update(status="Running", hostAgentPID=34567, driverPID=34567)
                for name in ("ha.pid", "vz.pid"):
                    private(selection.storage.runtime_path / "q" / name, b"34567\n")
                if state["after_start"]:
                    state["after_start"]()
                if state["start_error"]:
                    raise creator.CommandRefusal(state["start_error"])
            else:
                assert argv == [str(creator.LIMA.resolve()), "stop", "--tty=false", "q"]
                if state["stop_error"]:
                    raise creator.CommandRefusal(state["stop_error"])
                state["live"] = False
                outputs["lima"].update(status="Stopped", hostAgentPID=0, driverPID=0)
                for name in ("ha.pid", "vz.pid"):
                    (selection.storage.runtime_path / "q" / name).unlink(missing_ok=True)
                if state["after_stop"]:
                    state["after_stop"]()
            return creator.CommandResult(0, b"", b"")
        if argv[0] == "/bin/ps":
            calls.append((argv, kwargs))
            assert argv[:5] == ["/bin/ps", "-ww", "-p", "34567", "-o"]
            if argv[-1] == "pid=,uid=,lstart=":
                raw = f"34567 {os.getuid()} {state["process_stamp"]}\n".encode()
            elif argv[-1] == "comm=":
                raw = (str(creator.LIMA.resolve()) + "\n").encode()
            else:
                path = creator.LIMA.resolve()
                raw = (f"{path} hostagent --pidfile {selection.storage.runtime_path}/q/ha.pid "
                       f"--socket {selection.storage.runtime_path}/q/ha.sock --guestagent "
                       f"{path.parent.parent}/share/lima/lima-guestagent.Linux-aarch64.gz q\n").encode()
            return creator.CommandResult(0, raw, b"")
        result = original(argv, **kwargs)
        if argv[1] == "info" and state["before_start"]:
            callback, state["before_start"] = state["before_start"], None
            callback()
        return result

    monkeypatch.setattr(creator, "_run_bounded_command", command)
    monkeypatch.setattr(booter, "_pid_alive", lambda pid: state["live"])
    return selection, outputs, calls, state


def effects(calls):
    return [argv[1] for argv, _ in calls if argv[1] in {"start", "stop", "create"}]


def test_one_start_then_stop_with_equal_vz_pids(booter, stopped):
    selection, _, calls, state = stopped
    result = booter.qualify_boot(selection)
    assert result.running_observed and result.stopped_verified
    assert result.host_agent_pid == result.driver_pid == 34567
    assert result.worker_status == "Stopped" and result.session_enabled is False
    assert effects(calls) == ["start", "stop"] and not state["live"]
    assert [argv[1] for argv, _ in calls].count("info") == 2


@pytest.mark.parametrize("error", ["timeout", "output_limit", "launch_failed"])
def test_start_error_still_stops_and_preserves_failure(booter, stopped, error):
    selection, _, calls, state = stopped
    state["start_error"] = error
    with pytest.raises(booter.BootRefusal) as caught:
        booter.qualify_boot(selection)
    assert caught.value.start_requested and caught.value.stop_requested
    assert caught.value.stopped_verified and not caught.value.shutdown_uncertain
    assert str(caught.value).startswith("start_")
    assert effects(calls) == ["start", "stop"] and not state["live"]
    assert (selection.storage.runtime_path / "q/disk").exists()


@pytest.mark.parametrize("error", ["timeout", "output_limit", "launch_failed"])
def test_stop_error_remains_uncertain_and_never_forces_or_retries(booter, stopped, error):
    selection, _, calls, state = stopped
    state["stop_error"] = error
    with pytest.raises(booter.BootRefusal) as caught:
        booter.qualify_boot(selection)
    assert caught.value.shutdown_uncertain and not caught.value.stopped_verified
    assert caught.value.stop_requested
    assert effects(calls) == ["start", "stop"] and state["live"]
    assert all("--force" not in argv for argv, _ in calls)


@pytest.mark.parametrize("change", ["missing", "partial", "second", "autostart", "override", "input", "binary", "format", "running"])
def test_admission_failure_never_starts_or_stops(booter, stopped, change):
    selection, outputs, calls, _ = stopped
    storage = selection.storage
    if change == "missing":
        for path in (storage.runtime_path / "q").iterdir(): path.unlink()
        (storage.runtime_path / "q").rmdir()
    elif change == "partial": (storage.runtime_path / "q/lima.yaml").unlink()
    elif change == "second": private(storage.runtime_path / "other/lima.yaml")
    elif change == "autostart": private(storage.home_path / "Library/LaunchAgents/io.lima-vm.autostart.q.plist")
    elif change == "override": private(storage.runtime_path / "_config/override.yaml")
    elif change == "input": private(storage.run_root / "input/lima.yaml", b"changed")
    elif change == "binary": selection = replace(selection, lima_sha256="0" * 64)
    elif change == "format": outputs["apple"]["Image Format"] = "ASIF"
    else: outputs["lima"].update(status="Running", hostAgentPID=34567, driverPID=34567)
    with pytest.raises(booter.BootRefusal) as caught: booter.qualify_boot(selection)
    assert not caught.value.start_requested and not caught.value.stop_requested
    assert effects(calls) == []


@pytest.mark.parametrize("change", ["worker", "disk", "config", "binary", "home"])
def test_replaced_identity_prevents_stopping_replacement(booter, creator, stopped, change):
    selection, _, calls, state = stopped
    storage = selection.storage
    def mutate():
        if change == "worker":
            (storage.runtime_path / "q").rename(storage.runtime_path / "saved-q")
            private(storage.runtime_path / "q/lima.yaml", creator.RECIPE.read_bytes())
        elif change == "disk":
            path = storage.runtime_path / "q/disk"
            path.rename(path.with_name("saved-disk"))
            private(path)
            with path.open("r+b") as stream: stream.truncate(creator.DISK_BYTES)
        elif change == "config": private(storage.runtime_path / "q/lima.yaml", b"changed")
        elif change == "binary": creator.LIMA.write_bytes(b"replaced")
        else:
            storage.home_path.rename(storage.runtime_path / "_saved-controller")
            storage.home_path.mkdir(mode=0o700)
    state["after_start"] = mutate
    with pytest.raises(booter.BootRefusal) as caught: booter.qualify_boot(selection)
    assert caught.value.shutdown_uncertain and not caught.value.stop_requested
    assert effects(calls) == ["start"] and state["live"]


def test_live_pid_after_stopped_status_is_not_confirmed_shutdown(booter, stopped, monkeypatch):
    selection, _, calls, _ = stopped
    monkeypatch.setattr(booter, "_pid_alive", lambda pid: True)
    with pytest.raises(booter.BootRefusal) as caught: booter.qualify_boot(selection)
    assert caught.value.shutdown_uncertain and not caught.value.stopped_verified
    assert effects(calls) == ["start", "stop"]


def test_low_budget_during_running_does_not_block_identity_safe_stop(booter, inventory, stopped, monkeypatch):
    selection, _, calls, state = stopped
    original = inventory.validate_running_inventory
    def low(selection, observation):
        report = original(selection, observation)
        return inventory.StorageAdmission(("host_free_space",)) if state["live"] else report
    monkeypatch.setattr(inventory, "validate_running_inventory", low)
    with pytest.raises(booter.BootRefusal, match="host_free_space") as caught: booter.qualify_boot(selection)
    assert caught.value.stopped_verified and not caught.value.shutdown_uncertain
    assert effects(calls) == ["start", "stop"]


def test_prestart_drift_after_disk_probe_is_rechecked(booter, stopped):
    selection, _, calls, state = stopped
    state["before_start"] = lambda: private(selection.storage.runtime_path / "_config/default.yaml")
    with pytest.raises(booter.BootRefusal): booter.qualify_boot(selection)
    assert effects(calls) == []


def test_lock_released_after_shutdown_failure(booter, stopped):
    selection, _, _, state = stopped
    state["stop_error"] = "timeout"
    with pytest.raises(booter.BootRefusal): booter.qualify_boot(selection)
    fd = os.open(selection.storage.pilot_root, os.O_RDONLY | os.O_DIRECTORY)
    try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally: os.close(fd)


def test_cli_refuses_unbounded_operations(booter, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["boot", "--selection", "/unused", "--operation", "start"])
    with pytest.raises(SystemExit) as caught: booter.main()
    assert caught.value.code == 2


def test_live_disk_timestamp_changes_still_allow_exact_stop(booter, stopped, monkeypatch):
    from types import SimpleNamespace
    selection, _, calls, state = stopped
    inode = (selection.storage.runtime_path / "q/disk").stat().st_ino
    original = os.fstat
    tick = 0
    def writing(fd):
        nonlocal tick
        info = original(fd)
        if info.st_ino == inode and state["live"]:
            tick += 1
            attrs = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
            return SimpleNamespace(**(attrs | {"st_mtime_ns": info.st_mtime_ns + tick,
                                               "st_ctime_ns": info.st_ctime_ns + tick}))
        return info
    monkeypatch.setattr(os, "fstat", writing)
    result = booter.qualify_boot(selection)
    assert result.stopped_verified and effects(calls) == ["start", "stop"]


@pytest.mark.parametrize("change", ["pidfile", "pidreuse", "zero_live"])
def test_process_change_after_running_observation_cannot_signal_replacement(booter, stopped, monkeypatch, change):
    selection, outputs, calls, state = stopped
    original = booter._processes
    mutated = False
    def changing(*args, **kwargs):
        nonlocal mutated
        observed = original(*args, **kwargs)
        if observed.pids[0] and not mutated:
            mutated = True
            if change == "pidfile":
                path = selection.storage.runtime_path / "q/ha.pid"
                path.rename(path.with_name("old-ha.pid"))
                private(path, b"34567\n")
            elif change == "pidreuse":
                state["process_stamp"] = "Tue Nov 3 12:00:01 2026"
            else:
                outputs["lima"].update(status="Stopped", hostAgentPID=0, driverPID=0)
                for name in ("ha.pid", "vz.pid"):
                    (selection.storage.runtime_path / "q" / name).unlink()
        return observed
    monkeypatch.setattr(booter, "_processes", changing)
    with pytest.raises(booter.BootRefusal) as caught: booter.qualify_boot(selection)
    assert caught.value.shutdown_uncertain and not caught.value.stop_requested
    assert effects(calls) == ["start"]


@pytest.mark.parametrize("field,raw", [
    ("pid=,uid=,lstart=", b"1 0 Tue Nov 3 12:00:00 2026\n"),
    ("pid=,uid=,lstart=", b"34567 503 invalid\n"),
    ("comm=", b"/bin/sleep\n"),
    ("args=", b"unrelated process --pidfile q/ha.pid\n"),
])
def test_unrelated_process_metadata_is_not_stop_authority(booter, creator, stopped, monkeypatch, field, raw):
    selection, _, calls, _ = stopped
    original = creator._run_bounded_command
    def changed(argv, **kwargs):
        result = original(argv, **kwargs)
        if argv[0] == "/bin/ps" and argv[-1] == field:
            return creator.CommandResult(0, raw, b"")
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", changed)
    with pytest.raises(booter.BootRefusal) as caught: booter.qualify_boot(selection)
    assert caught.value.shutdown_uncertain and not caught.value.stop_requested
    assert effects(calls) == ["start"]


def test_start_timeout_preserves_shutdown_and_verification_budget(booter, stopped, monkeypatch):
    selection, _, calls, state = stopped
    clock = [10000.0]
    monkeypatch.setattr(booter.time, "monotonic", lambda: clock[0])
    state["after_start"] = lambda: clock.__setitem__(0, clock[0] + 600)
    state["start_error"] = "timeout"
    state["after_stop"] = lambda: clock.__setitem__(0, clock[0] + 190)
    with pytest.raises(booter.BootRefusal) as caught: booter.qualify_boot(selection)
    assert caught.value.stopped_verified and not caught.value.shutdown_uncertain
    start = next(kwargs for argv, kwargs in calls if argv[1] == "start")
    stop = next(kwargs for argv, kwargs in calls if argv[1] == "stop")
    assert start["timeout"] <= 600 and stop["timeout"] == 190
    assert 10900 - clock[0] >= 90


def test_failed_stop_can_independently_confirm_process_exit(booter, creator, stopped, monkeypatch):
    selection, _, calls, _ = stopped
    original = creator._run_bounded_command
    def stopping(argv, **kwargs):
        result = original(argv, **kwargs)
        if argv[1] == "stop":
            raise creator.CommandRefusal("timeout")
        return result
    monkeypatch.setattr(creator, "_run_bounded_command", stopping)
    with pytest.raises(booter.BootRefusal, match="stop_timeout") as caught: booter.qualify_boot(selection)
    assert caught.value.stopped_verified and not caught.value.shutdown_uncertain
    assert effects(calls) == ["start", "stop"]


def test_post_stop_disk_failure_preserves_positive_shutdown_fact(booter, stopped):
    selection, outputs, calls, state = stopped
    state["after_stop"] = lambda: outputs["apple"].__setitem__("Image Format", "ASIF")
    with pytest.raises(booter.BootRefusal, match="disk_format") as caught: booter.qualify_boot(selection)
    assert caught.value.stopped_verified and not caught.value.shutdown_uncertain
    assert effects(calls) == ["start", "stop"]


def test_slow_cleanup_identity_checks_cannot_consume_stop_reserve(booter, stopped, monkeypatch):
    selection, _, calls, state = stopped
    clock = [10000.0]
    monkeypatch.setattr(booter.time, "monotonic", lambda: clock[0])
    state["after_start"] = lambda: clock.__setitem__(0, clock[0] + 600)
    state["start_error"] = "timeout"
    original = booter._guard
    slowed = False
    def slow(*args, **kwargs):
        nonlocal slowed
        if kwargs.get("identity_only") and not slowed:
            slowed = True
            clock[0] += 51
        return original(*args, **kwargs)
    monkeypatch.setattr(booter, "_guard", slow)
    with pytest.raises(booter.BootRefusal) as caught: booter.qualify_boot(selection)
    assert caught.value.shutdown_uncertain and not caught.value.stop_requested
    assert effects(calls) == ["start"] and state["live"]


@pytest.mark.parametrize("seconds", [True, 0, 901, 1801, 3600])
def test_private_qualification_refuses_unselected_budget(booter, stopped, seconds):
    selection, *_ = stopped
    with pytest.raises(booter.BootRefusal, match="qualification_budget") as error:
        booter._qualify_with_inspection(selection, qualification_seconds=seconds)
    assert not error.value.start_requested


def test_build_qualification_keeps_shutdown_reserve(booter, stopped, monkeypatch):
    selection, *_ = stopped
    def admit(selection, fd, deadline):
        assert 1490 < deadline - booter.time.monotonic() <= 1500
        raise booter.Refusal("admission_probe_only")
    monkeypatch.setattr(booter, "_admit", admit)
    with pytest.raises(booter.BootRefusal, match="admission_probe_only") as error:
        booter._qualify_with_inspection(selection, qualification_seconds=1800)
    assert not error.value.start_requested
