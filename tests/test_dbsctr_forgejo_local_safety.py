"""Completion and persistence boundaries with disposable offline repositories."""

import json
import os
from pathlib import Path

import pytest

from test_dbsctr_forgejo_completion import cycle, ready  # noqa: F401


@pytest.mark.parametrize("reason", ["", "   "])
def test_invalid_review_input_does_not_damage_record(cycle, capsys, reason):
    before = cycle.path.read_bytes()
    assert cycle.invoke("review-artifact", "README", "--result", "unchanged", "--reason", reason) == 1
    assert cycle.path.read_bytes() == before
    assert capsys.readouterr().out == ""
    cycle.core.read_cycle_record(cycle.root, cycle.path)


def test_completion_never_executes_configured_fsmonitor(ready, capsys):
    marker = ready.root.parent / "fsmonitor-ran"
    hook = ready.root.parent / "fsmonitor"
    hook.write_text(f'#!/bin/sh\nprintf called >> "{marker}"\n')
    hook.chmod(0o700)
    ready.core.git(ready.root, "config", "core.fsmonitor", str(hook))
    assert ready.invoke("complete-local") == 0
    assert not marker.exists()
    assert json.loads(capsys.readouterr().out)["status"] == "locally_validated"


def test_completion_refuses_external_filters_without_running_them(ready, capsys):
    marker = ready.root.parent / "filter-ran"
    hook = ready.root.parent / "clean-filter"
    hook.write_text(f'#!/bin/sh\nprintf called >> "{marker}"\ncat\n')
    hook.chmod(0o700)
    ready.core.git(ready.root, "config", "filter.fixture.clean", str(hook))
    info = ready.core.common_git_dir(ready.root) / "info/attributes"
    info.parent.mkdir(exist_ok=True)
    info.write_text("tracked.txt filter=fixture\n")
    os.utime(ready.root / "tracked.txt", None)
    before = ready.path.read_bytes()
    assert ready.invoke("complete-local") == 1
    assert not marker.exists()
    assert ready.path.read_bytes() == before
    assert capsys.readouterr().out == ""


def test_completion_refuses_profile_filter_before_running_it(ready, capsys):
    profile = json.loads(ready.path.read_text())["engineering_profile"]["path"]
    marker = ready.root.parent / "profile-filter-ran"
    hook = ready.root.parent / "profile-clean-filter"
    hook.write_text(f'#!/bin/sh\nprintf called >> "{marker}"\ncat\n')
    hook.chmod(0o700)
    ready.core.git(ready.root, "config", "filter.fixture.clean", str(hook))
    attributes = ready.core.common_git_dir(ready.root) / "info/attributes"
    attributes.parent.mkdir(exist_ok=True)
    attributes.write_text(f"{profile} filter=fixture\n")
    target = ready.root / profile
    stamp = target.stat()
    os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000_000))
    before = ready.path.read_bytes()

    assert ready.invoke("complete-local") == 1
    assert not marker.exists()
    assert ready.path.read_bytes() == before
    assert capsys.readouterr().out == ""


def test_local_filter_scan_preserves_carriage_return_in_gitlink_path(cycle):
    core, root = cycle.core, cycle.root
    child = root / "child\rrepository"
    child.mkdir()
    core.git(child, "init", "-b", "main")
    core.git(child, "config", "user.name", "Fixture")
    core.git(child, "config", "user.email", "fixture@example.invalid")
    (child / "tracked.txt").write_text("fixture\n")
    (child / ".gitattributes").write_text("tracked.txt filter=fixture\n")
    core.git(child, "add", ".")
    core.git(child, "commit", "-m", "fixture child")
    core.git(root, "add", "--", child.name)
    core.git(root, "commit", "-m", "fixture gitlink")
    with core.local_completion_git_context():
        assert core.status_paths(root) == []

    marker = root.parent / "child-filter-ran"
    hook = root.parent / "child-clean-filter"
    hook.write_text(f'#!/bin/sh\nprintf called >> "{marker}"\ncat\n')
    hook.chmod(0o700)
    core.git(child, "config", "filter.fixture.clean", str(hook))
    tracked = child / "tracked.txt"
    stamp = tracked.stat()
    os.utime(tracked, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000_000))

    with core.local_completion_git_context():
        with pytest.raises(RuntimeError, match="executable Git filters"):
            core.status_paths(root)
    assert not marker.exists()


def test_local_filter_scan_rejects_redirected_submodule_worktree(cycle):
    core, root = cycle.core, cycle.root
    child = root / "child"
    external = root.parent / "redirected-child"
    nested = external / "nested"
    child.mkdir()
    nested.mkdir(parents=True)
    for repository in (child, nested):
        core.git(repository, "init", "-b", "main")
        core.git(repository, "config", "user.name", "Fixture")
        core.git(repository, "config", "user.email", "fixture@example.invalid")
    (nested / "tracked.txt").write_text("fixture\n")
    (nested / ".gitattributes").write_text("tracked.txt filter=fixture\n")
    core.git(nested, "add", ".")
    core.git(nested, "commit", "-m", "fixture nested")
    core.git(child, "config", "core.worktree", str(external))
    (external / "child.txt").write_text("fixture child\n")
    core.git(child, "add", "--all")
    core.git(child, "commit", "-m", "fixture redirected child")
    core.git(root, "add", "--", child.name)
    core.git(root, "commit", "-m", "fixture outer")
    effective = core.inspect_git_bytes(child, "rev-parse", "--show-toplevel")
    assert Path(os.fsdecode(effective.removesuffix(b"\n"))).resolve() == external.resolve()

    marker = root.parent / "redirected-filter-ran"
    hook = root.parent / "redirected-clean-filter"
    hook.write_text(f'#!/bin/sh\nprintf called >> "{marker}"\ncat\n')
    hook.chmod(0o700)
    core.git(nested, "config", "filter.fixture.clean", str(hook))
    tracked = nested / "tracked.txt"
    stamp = tracked.stat()
    os.utime(tracked, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000_000))

    with core.local_completion_git_context():
        with pytest.raises(RuntimeError, match="worktree"):
            core.status_paths(root)
    assert not marker.exists()
