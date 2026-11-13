"""Retained task alignment mutates disposable Git worktrees only."""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import alignment as a
from integration_coordinator import core as c, runtime as r


def git(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


class MemoryJournal:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], bytes] = {}
        self.interrupt: str | None = None

    def read(self, operation_digest: str, phase: str) -> bytes | None:
        return self.rows.get((operation_digest, phase))

    def write(self, operation_digest: str, phase: str, payload: bytes) -> None:
        event = a.decode_event(payload)
        assert event.operation_digest == operation_digest and event.phase == phase
        if self.interrupt == phase:
            raise OSError("injected journal interruption")
        old = self.rows.setdefault((operation_digest, phase), payload)
        assert old == payload


@pytest.fixture
def task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]:
    for key in tuple(os.environ):
        if key.startswith("GIT_"): monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Fixture")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "fixture@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Fixture")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "fixture@example.invalid")
    path = tmp_path / "task"
    path.mkdir()
    git(path, "init", "--initial-branch=task")
    (path / "a").write_text("zero\n")
    git(path, "add", "a"); git(path, "commit", "-m", "base")
    original_base = git(path, "rev-parse", "HEAD")
    (path / "a").write_text("one\n")
    git(path, "add", "a"); git(path, "commit", "-m", "phase")
    old = git(path, "rev-parse", "HEAD")
    git(path, "checkout", "-b", "remote", original_base)
    (path / "b").write_text("base advance\n")
    git(path, "add", "b"); git(path, "commit", "-m", "other task")
    new_base = git(path, "rev-parse", "HEAD")
    (path / "a").write_text("one\n")
    git(path, "add", "a"); git(path, "commit", "-m", "phase")
    new = git(path, "rev-parse", "HEAD")
    git(path, "checkout", "task")
    reference = "refs/dbsctr/evidence/fixture"
    git(path, "update-ref", reference, old)
    context = a.AlignmentContext(path.resolve(), (path / ".git").resolve(), "task", "trunk", "control", "a" * 64)
    projection = r.Projection("b" * 64, new_base, new, (c.CommitPair(old, new),), "c" * 64)
    return context, old, projection, (a.RetainedRef(reference, old),)


def test_clean_alignment_retains_originals_and_ignored_private_files(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    ignored = context.checkout / ".private"
    (context.common_git_dir / "info/exclude").write_text(".private\n")
    ignored.write_text("private evidence\n")
    journal = MemoryJournal()
    receipt = a.align(context, old, projection, refs, journal)
    assert receipt.status == "aligned" and receipt.new_head == projection.head
    assert git(context.checkout, "symbolic-ref", "HEAD") == "refs/heads/task"
    assert git(context.checkout, "rev-parse", "HEAD") == projection.head
    assert git(context.checkout, "rev-parse", refs[0].ref) == old
    assert ignored.read_text() == "private evidence\n"
    assert [phase for _, phase in journal.rows] == list(a.PHASES)
    assert a.align(context, old, projection, refs, journal) == receipt


def test_ignored_collision_refuses_without_destroying_private_bytes(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    (context.common_git_dir / "info/exclude").write_text("b\n")
    (context.checkout / "b").write_text("private collision\n")
    with pytest.raises(a.AlignmentPending): a.align(context, old, projection, refs, MemoryJournal())
    assert (context.checkout / "b").read_text() == "private collision\n"
    assert git(context.checkout, "rev-parse", "refs/heads/task") == old


@pytest.mark.parametrize("kind", ["tracked", "untracked"])
def test_local_drift_stops_before_journal_or_checkout(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], kind: str) -> None:
    context, old, projection, refs = task
    changed = context.checkout / ("a" if kind == "tracked" else "untracked")
    changed.write_text("local work\n")
    journal = MemoryJournal()
    with pytest.raises(c.Conflict): a.align(context, old, projection, refs, journal)
    assert not journal.rows and changed.read_text() == "local work\n"
    assert git(context.checkout, "rev-parse", "HEAD") == old


def test_stale_branch_ref_is_never_overwritten(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    git(context.checkout, "update-ref", "refs/heads/task", projection.base, old)
    journal = MemoryJournal()
    with pytest.raises(c.Conflict): a.align(context, old, projection, refs, journal)
    assert not journal.rows
    assert git(context.checkout, "rev-parse", "refs/heads/task") == projection.base


def test_interruption_after_detach_resumes_from_private_journal(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    journal = MemoryJournal(); journal.interrupt = "detached"
    with pytest.raises(a.AlignmentPending): a.align(context, old, projection, refs, journal)
    assert git(context.checkout, "rev-parse", "HEAD") == projection.head
    assert git(context.checkout, "rev-parse", "refs/heads/task") == old
    journal.interrupt = None
    result = a.align(context, old, projection, refs, journal)
    assert result.status == "aligned" and git(context.checkout, "symbolic-ref", "HEAD") == "refs/heads/task"
    assert git(context.checkout, "rev-parse", refs[0].ref) == old


@pytest.mark.parametrize("branch", ["main", "master", "trunk", "control"])
def test_target_and_control_refs_are_excluded(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], branch: str) -> None:
    context, _, _, _ = task
    with pytest.raises(c.Invalid): replace(context, branch=branch)


def test_post_checkout_hooks_are_preserved(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], tmp_path: Path) -> None:
    context, old, projection, refs = task
    marker = tmp_path / "hook-count"
    hooks = tmp_path / "hooks"; hooks.mkdir()
    hook = hooks / "post-checkout"
    hook.write_text("#!/bin/sh\nprintf 'called\\n' >> " + shlex.quote(str(marker)) + "\n")
    hook.chmod(0o700)
    git(context.checkout, "config", "core.hooksPath", str(hooks))
    a.align(context, old, projection, refs, MemoryJournal())
    assert marker.read_text().splitlines() == ["called", "called"]


def test_missing_original_retention_ref_refuses_before_checkout(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    git(context.checkout, "update-ref", "-d", refs[0].ref, old)
    journal = MemoryJournal()
    with pytest.raises(c.Conflict): a.align(context, old, projection, refs, journal)
    assert not journal.rows and git(context.checkout, "rev-parse", "HEAD") == old


def test_already_aligned_is_observation_without_invented_journal(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    git(context.checkout, "checkout", "--detach", projection.head)
    git(context.checkout, "update-ref", "refs/heads/task", projection.head, old)
    git(context.checkout, "checkout", "task")
    journal = MemoryJournal()
    assert a.align(context, old, projection, refs, journal).status == "already_aligned"
    assert not journal.rows


@pytest.mark.parametrize("phase", ["ref_updated", "attached"])
def test_missing_success_event_recovers_each_completed_physical_stage(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], phase: str) -> None:
    context, old, projection, refs = task
    journal = MemoryJournal(); journal.interrupt = phase
    with pytest.raises(a.AlignmentPending): a.align(context, old, projection, refs, journal)
    assert git(context.checkout, "rev-parse", "refs/heads/task") == projection.head
    journal.interrupt = None
    assert a.align(context, old, projection, refs, journal).status == "aligned"
    assert git(context.checkout, "rev-parse", refs[0].ref) == old


def test_failed_configured_hook_is_not_waived_by_recovery(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], tmp_path: Path) -> None:
    context, old, projection, refs = task
    marker = tmp_path / "hook-failed"
    hooks = tmp_path / "hooks"; hooks.mkdir()
    hook = hooks / "post-checkout"
    hook.write_text("#!/bin/sh\nprintf 'failed\\n' >> " + shlex.quote(str(marker)) + "\nexit 1\n")
    hook.chmod(0o700)
    git(context.checkout, "config", "core.hooksPath", str(hooks))
    journal = MemoryJournal()
    for _ in range(2):
        with pytest.raises(a.AlignmentPending): a.align(context, old, projection, refs, journal)
    assert marker.read_text().splitlines() == ["failed", "failed"]
    assert [phase for _, phase in journal.rows] == ["prepared"]
    assert git(context.checkout, "rev-parse", "refs/heads/task") == old
    hook.write_text("#!/bin/sh\nexit 0\n")
    assert a.align(context, old, projection, refs, journal).status == "aligned"


class DriftJournal(MemoryJournal):
    def __init__(self, context: a.AlignmentContext, old: str, replacement: str) -> None:
        super().__init__(); self.context = context; self.old = old; self.replacement = replacement

    def write(self, operation_digest: str, phase: str, payload: bytes) -> None:
        super().write(operation_digest, phase, payload)
        if phase == "detached":
            git(self.context.checkout, "update-ref", "refs/heads/task", self.replacement, self.old)


def test_branch_cas_refuses_drift_after_detached_stage(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    journal = DriftJournal(context, old, projection.base)
    with pytest.raises(a.AlignmentPending): a.align(context, old, projection, refs, journal)
    assert git(context.checkout, "rev-parse", "refs/heads/task") == projection.base
    assert git(context.checkout, "rev-parse", "HEAD") == projection.head
    assert git(context.checkout, "rev-parse", refs[0].ref) == old


def test_linked_worktree_uses_exact_shared_gitdir_without_touching_primary(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], tmp_path: Path) -> None:
    context, old, projection, refs = task
    primary = context.checkout
    git(primary, "checkout", "remote")
    linked = tmp_path / "linked"
    git(primary, "worktree", "add", str(linked), "task")
    context = replace(context, checkout=linked.resolve())
    assert a.align(context, old, projection, refs, MemoryJournal()).status == "aligned"
    assert git(primary, "symbolic-ref", "HEAD") == "refs/heads/remote"
    assert git(primary, "rev-parse", "HEAD") == projection.head
    assert git(primary, "status", "--porcelain") == ""


def test_journal_bytes_carry_no_private_paths_and_reject_duplicate_or_out_of_order_events(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    journal = MemoryJournal()
    a.align(context, old, projection, refs, journal)
    for raw in journal.rows.values():
        assert str(context.checkout).encode() not in raw and refs[0].ref.encode() not in raw
    first = next(iter(journal.rows.values()))
    duplicated = first[:-1] + b',"schema_version":1}'
    with pytest.raises(c.Invalid): a.decode_event(duplicated)
    operation = next(iter(journal.rows))[0]
    del journal.rows[(operation, "detached")]
    with pytest.raises(c.Conflict): a.align(context, old, projection, refs, journal)


def test_local_replace_ref_cannot_relabel_checkout_tree_as_qualified_remote_commit(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]]) -> None:
    context, old, projection, refs = task
    git(context.checkout, "replace", projection.head, old)
    journal = MemoryJournal()
    with pytest.raises(c.Conflict, match="alignment_local_replacements"):
        a.align(context, old, projection, refs, journal)
    assert not journal.rows and git(context.checkout, "rev-parse", "HEAD") == old


@pytest.mark.parametrize("mechanism", ["grafts", "partial_clone"])
def test_unsupported_local_history_or_lazy_fetch_configuration_refuses_before_staging(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], mechanism: str) -> None:
    context, old, projection, refs = task
    if mechanism == "grafts":
        (context.common_git_dir / "info/grafts").write_text(old + "\n")
    else:
        git(context.checkout, "config", "extensions.partialClone", "origin")
    journal = MemoryJournal()
    with pytest.raises(c.Conflict, match="alignment_local_history_configuration"):
        a.align(context, old, projection, refs, journal)
    assert not journal.rows


def test_alternate_replace_namespace_from_environment_cannot_spoof_alignment(task: tuple[a.AlignmentContext, str, r.Projection, tuple[a.RetainedRef, ...]], monkeypatch: pytest.MonkeyPatch) -> None:
    context, old, projection, refs = task
    git(context.checkout, "update-ref", "refs/alternate-replace/" + projection.head, old)
    monkeypatch.setenv("GIT_REPLACE_REF_BASE", "refs/alternate-replace/")
    journal = MemoryJournal()
    with pytest.raises(c.Conflict, match="alignment_local_history_configuration"):
        a.align(context, old, projection, refs, journal)
    assert not journal.rows
