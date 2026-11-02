#!/usr/bin/env python3
"""Opt-in synthetic CLI measurements; never execute input evidence as code."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import sys
import time
import uuid


SIBLING = Path(__file__).resolve().with_name("performance_evidence.py")
if ("performance_evidence" not in sys.modules
        or Path(sys.modules["performance_evidence"].__file__).resolve() != SIBLING):
    _spec = importlib.util.spec_from_file_location("performance_evidence", SIBLING)
    _evidence = importlib.util.module_from_spec(_spec)
    sys.modules["performance_evidence"] = _evidence
    _spec.loader.exec_module(_evidence)
evidence = sys.modules["performance_evidence"]
EvidenceError = evidence.EvidenceError

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures/cli_workloads.json"
STREAM_LIMIT = 1024 * 1024
PROFILE_LIMIT = 16 * 1024 * 1024
SCRATCH_LIMIT = 1024 * 1024 * 1024
TOTAL_SECONDS = 600
CHILD_SECONDS = 10
ALLOWED_GIT = frozenset({
    "rev-parse", "rev-list", "symbolic-ref", "worktree", "status", "show",
    "cat-file", "log", "diff", "config", "ls-files",
})
SYSTEM_LFS_FILTERS = {
    b"filter.lfs.clean": b"git-lfs clean -- %f",
    b"filter.lfs.smudge": b"git-lfs smudge -- %f",
    b"filter.lfs.process": b"git-lfs filter-process",
    b"filter.lfs.required": b"true",
}

"""Bounded process-group ownership for the synthetic benchmark coordinator.

The coordinator must serialize invocations and must not reap unrelated children
inside this measurement window. CPU is cumulative reaped-child CPU under that
ownership contract; it is not controller CPU or a whole-host measurement.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time
from typing import Literal

try:
    import resource
except ImportError:
    resource = None


MAX_PROCESS_STREAM = 1024 * 1024
MAX_PROFILE_BYTES = 16 * 1024 * 1024


ProcessStatus = Literal[
    "completed", "timed_out", "cancelled", "output_overflow",
    "start_failed", "cleanup_uncertain",
]


@dataclass(frozen=True)
class ProcessResult:
    status: ProcessStatus
    returncode: int | None
    stdout: bytes
    stderr: bytes
    wall_ns: int
    cpu_ns: int | None
    cleanup_complete: bool


def _process_cpu() -> float | None:
    if resource is None:
        return None
    try:
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        total = usage.ru_utime + usage.ru_stime
    except (AttributeError, OSError, ValueError):
        return None
    return total if math.isfinite(total) and total >= 0 else None


def _group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        # Permission or inspection failure is uncertainty, never proof of exit.
        return True
    return True


def _signal_group(pgid: int, number: int) -> bool:
    try:
        os.killpg(pgid, number)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return True


def _reap_group(process: subprocess.Popen[bytes]) -> bool:
    """Terminate any surviving owned group, reap its leader, then verify absence.

    Non-child descendants are reaped by their operating-system parent. A group
    that remains observable, including unreaped descendants, stays uncertain.
    The caller must retain scratch and stop scheduling on a false result.
    """
    pgid = process.pid
    try:
        process.poll()
        if _group_exists(pgid):
            if not _signal_group(pgid, signal.SIGTERM):
                return False
            deadline = time.monotonic() + 0.2
            while time.monotonic() < deadline:
                process.poll()
                if not _group_exists(pgid):
                    break
                time.sleep(0.01)
            if _group_exists(pgid) and not _signal_group(pgid, signal.SIGKILL):
                return False
        process.wait(timeout=0.5)
        deadline = time.monotonic() + 0.5
        while _group_exists(pgid) and time.monotonic() < deadline:
            time.sleep(0.01)
        return process.returncode is not None and not _group_exists(pgid)
    except (OSError, ChildProcessError, subprocess.TimeoutExpired):
        return False


def run_owned(
    argv: Sequence[str],
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
    *,
    input_data: bytes | None = None,
    stream_limit: int = MAX_PROCESS_STREAM,
    cancelled: Callable[[], bool] | None = None,
    watch_limit: tuple[Path, int] | None = None,
) -> ProcessResult:
    """Execute one argv under a deadline and drain stdin/stdout/stderr together.

    Expected process outcomes return structured dispositions. Invalid caller
    arguments raise ValueError before launch. Unexpected caller exceptions still
    trigger owned cleanup before propagating. This is process-group ownership,
    not an OS sandbox or a guarantee about a child that deliberately escapes its
    assigned process group; only the reviewed fixed benchmark commands belong here.
    """
    if (
        os.name != "posix" or not hasattr(os, "killpg")
        or isinstance(argv, (str, bytes)) or not 1 <= len(argv) <= 128
        or not argv[0] or any(not isinstance(arg, str) or "\0" in arg for arg in argv)
        or sum(len(arg) for arg in argv) > 65536
        or type(timeout) not in (int, float) or not math.isfinite(timeout)
        or not 0 < timeout <= 10
        or type(stream_limit) is not int or not 1 <= stream_limit <= MAX_PROCESS_STREAM
        or input_data is not None and (not isinstance(input_data, bytes)
                                      or len(input_data) > MAX_PROCESS_STREAM)
        or any(not isinstance(key, str) or not isinstance(value, str)
               or "\0" in key or "\0" in value or "=" in key
               for key, value in env.items())
    ):
        raise ValueError("invalid_process_arguments")
    if watch_limit is not None:
        if (
            not isinstance(watch_limit, tuple) or len(watch_limit) != 2
            or not isinstance(watch_limit[0], Path)
            or type(watch_limit[1]) is not int
            or not 1 <= watch_limit[1] <= MAX_PROFILE_BYTES
        ):
            raise ValueError("invalid_profile_bound")

    started = time.monotonic_ns()
    deadline = time.monotonic() + float(timeout)
    cpu_before = _process_cpu()
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    status: ProcessStatus = "completed"
    cleanup_complete = True

    def close_stream(stream) -> None:
        if selector is not None:
            try:
                selector.unregister(stream)
            except (KeyError, ValueError):
                pass
        stream.close()

    def profile_exceeded() -> bool:
        if watch_limit is None:
            return False
        path, limit = watch_limit
        try:
            item = path.lstat()
        except FileNotFoundError:
            return False
        return (not stat.S_ISREG(item.st_mode) or item.st_nlink != 1
                or item.st_size > limit)

    try:
        if cancelled is not None and cancelled():
            status = "cancelled"
        elif profile_exceeded():
            status = "output_overflow"
        else:
            selector = selectors.DefaultSelector()
            process = subprocess.Popen(
                list(argv), cwd=cwd, env=dict(env), stdin=(subprocess.PIPE
                    if input_data is not None else subprocess.DEVNULL),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True, shell=False, bufsize=0, umask=0o077,
            )
            for stream, channel in ((process.stdout, "stdout"),
                                    (process.stderr, "stderr")):
                assert stream is not None
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, channel)
            pending = memoryview(input_data or b"")
            input_offset = 0
            if process.stdin is not None:
                if pending:
                    os.set_blocking(process.stdin.fileno(), False)
                    selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
                else:
                    close_stream(process.stdin)
            while True:
                if cancelled is not None and cancelled():
                    status = "cancelled"
                    break
                if profile_exceeded():
                    status = "output_overflow"
                    break
                if process.poll() is not None and not selector.get_map():
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    status = "timed_out"
                    break
                if not selector.get_map():
                    time.sleep(min(0.01, remaining))
                    continue
                for key, _ in selector.select(min(0.05, remaining)):
                    if key.data == "stdin":
                        try:
                            wrote = os.write(key.fd, pending[input_offset:input_offset + 65536])
                        except BlockingIOError:
                            continue
                        except BrokenPipeError:
                            close_stream(key.fileobj)
                            continue
                        input_offset += wrote
                        if input_offset == len(pending):
                            close_stream(key.fileobj)
                    else:
                        buffer = buffers[key.data]
                        try:
                            block = os.read(key.fd, min(65536, stream_limit - len(buffer) + 1))
                        except BlockingIOError:
                            continue
                        if not block:
                            close_stream(key.fileobj)
                            continue
                        room = stream_limit - len(buffer)
                        buffer.extend(block[:room])
                        if len(block) > room:
                            status = "output_overflow"
                            break
                if status == "output_overflow":
                    break
    except KeyboardInterrupt:
        status = "cancelled"
    except OSError:
        status = "start_failed"
    finally:
        if process is not None:
            cleanup_complete = _reap_group(process)
        if selector is not None:
            try:
                selector.close()
            except OSError:
                cleanup_complete = False
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    try:
                        stream.close()
                    except OSError:
                        cleanup_complete = False

    cpu_after = _process_cpu()
    cpu_ns = None
    if process is not None and cleanup_complete and cpu_before is not None and cpu_after is not None:
        delta = cpu_after - cpu_before
        if math.isfinite(delta) and delta >= 0:
            cpu_ns = int(delta * 1_000_000_000)
    return ProcessResult(
        status if cleanup_complete else "cleanup_uncertain",
        None if process is None else process.returncode,
        bytes(buffers["stdout"]), bytes(buffers["stderr"]),
        time.monotonic_ns() - started, cpu_ns, cleanup_complete,
    )



class BenchmarkError(ValueError):
    """A bounded public failure class with no raw command or path content."""


class CleanupUncertain(BenchmarkError):
    """Owned work could not be proven terminated; retain its scratch."""


@dataclass
class RunControl:
    cancelled: bool = False
    cleanup_known: bool = True

    def admit(self) -> None:
        if not self.cleanup_known:
            raise CleanupUncertain("cleanup_uncertain")
        if self.cancelled:
            raise BenchmarkError("cancelled")


def isolated_environment(directory: Path, git: Path) -> dict[str, str]:
    directory = directory.resolve()
    children = ("home", "config", "state", "data", "cache", "tmp", "empty-hooks")
    for name in children:
        (directory / name).mkdir(parents=True, exist_ok=True, mode=0o700)
    return {
        "PATH": str(git.parent) + os.pathsep + "/usr/bin:/bin",
        "HOME": str(directory / "home"),
        "XDG_CONFIG_HOME": str(directory / "config"),
        "XDG_STATE_HOME": str(directory / "state"),
        "XDG_DATA_HOME": str(directory / "data"),
        "XDG_CACHE_HOME": str(directory / "cache"),
        "TMPDIR": str(directory / "tmp"),
        "LANG": "C", "LC_ALL": "C", "TERM": "dumb", "NO_COLOR": "1",
        "COLUMNS": "100", "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "file", "GCM_INTERACTIVE": "Never",
    }


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _remaining(deadline: float) -> float:
    # Reserve bounded TERM/KILL/reap time inside the global/child budget.
    remaining = deadline - time.monotonic() - 1.3
    if remaining <= 0:
        raise BenchmarkError("budget_exhausted")
    return min(CHILD_SECONDS - 1.3, remaining)


def git_call(
    git: Path, cwd: Path, env: Mapping[str, str], deadline: float,
    *arguments: str, input_data: bytes | None = None, control: RunControl | None = None,
) -> bytes:
    if control is not None:
        control.admit()
    result = run_owned(
        [str(git), "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
         *arguments], cwd, env, _remaining(deadline), input_data=input_data,
        cancelled=(lambda: control.cancelled) if control else None,
    )
    if not result.cleanup_complete:
        if control is not None:
            control.cleanup_known = False
        raise CleanupUncertain("cleanup_uncertain")
    if control is not None:
        control.admit()
    if result.status != "completed" or result.returncode:
        raise BenchmarkError("git_unavailable")
    return result.stdout


def fixture_manifest(nodes: int) -> dict[str, object]:
    if type(nodes) is not int or nodes not in (10, 100):
        raise BenchmarkError("invalid_fixture")
    slices = [{
        "id": f"node-{i:03}", "context": "synthetic", "state": "captured",
        "requirements": ["INT-001"], "depends_on": [f"node-{i-1:03}"] if i else [],
        "artifacts": [], "execution_owner": "build", "release_group": "synthetic",
    } for i in range(nodes)]
    return {
        "schema_version": 1, "id": "synthetic-benchmark", "title": "Synthetic benchmark",
        "state": "captured", "coordinator_repository": "example/synthetic",
        "statements": [{
            "id": "INT-001", "kind": "requirement", "text": "Validate synthetic input.",
            "disposition": "open", "artifacts": ["README.md"],
        }],
        "contexts": [{
            "id": "synthetic", "repository": "example/synthetic",
            "status": "captured", "depends_on": [],
        }],
        "slices": slices,
        "release_groups": [{
            "id": "synthetic", "members": [row["id"] for row in slices],
            "state": "planning",
        }],
    }


def create_fixture(
    root: Path, commits: int, git: Path, env: Mapping[str, str], deadline: float,
    control: RunControl | None = None,
) -> tuple[Path, str]:
    """Create independent metadata, never a worktree, clone or real Cycle Record."""
    root.mkdir(mode=0o700)
    templates = root.parent / "empty-templates"
    templates.mkdir(exist_ok=True, mode=0o700)
    git_call(git, root, env, deadline, "init", "--initial-branch=main",
             "--template=" + str(templates), control=control)
    settings = {
        "user.name": "Synthetic Benchmark", "user.email": "benchmark@example.invalid",
        "core.hooksPath": str(templates), "core.fsmonitor": "false",
        "core.untrackedCache": "false", "commit.gpgSign": "false",
        "tag.gpgSign": "false", "credential.helper": "",
        "maintenance.auto": "false", "gc.auto": "0",
    }
    for key, value in settings.items():
        git_call(git, root, env, deadline, "config", "--local", key, value, control=control)
    (root / "README.md").write_bytes(b"Synthetic benchmark input.\n")
    for nodes in (10, 100):
        (root / f"manifest-{nodes}.json").write_bytes(evidence.canonical(fixture_manifest(nodes)) + b"\n")
    # Attribute filters can execute during add, so qualify before staging input.
    qualify_git(git, root, env, deadline, control)
    git_call(git, root, env, deadline, "add", "README.md", "manifest-10.json", "manifest-100.json", control=control)
    tree = git_call(git, root, env, deadline, "write-tree", control=control).decode().strip()
    previous = None
    for i in range(commits):
        commit_env = {
            **env, "GIT_AUTHOR_DATE": f"{946684800+i} +0000",
            "GIT_COMMITTER_DATE": f"{946684800+i} +0000",
        }
        args = ["commit-tree", tree]
        if previous:
            args.extend(["-p", previous])
        previous = git_call(
            git, root, commit_env, deadline, *args,
            input_data=f"synthetic {i}\n".encode(), control=control,
        ).decode().strip()
    git_call(git, root, env, deadline, "update-ref", "refs/heads/main", previous, control=control)
    git_call(git, root, env, deadline, "reset", "--mixed", "HEAD", control=control)
    return root, evidence.digest({
        "commits": commits, "manifests": [fixture_manifest(10), fixture_manifest(100)],
        "readme": "Synthetic benchmark input.\n",
    })


def _configuration_rows(raw: bytes) -> list[tuple[bytes, bytes, bytes]]:
    fields = raw.split(b"\0")
    if fields[-1] != b"" or len(fields) % 2 != 1:
        raise BenchmarkError("git_configuration_unqualified")
    return [(scope, row.partition(b"\n")[0], row.partition(b"\n")[2])
            for scope, row in zip(fields[::2], fields[1::2])]


def _qualify_filter_definitions(
    rows: Sequence[tuple[bytes, bytes, bytes]], *, system_reason: str, other_reason: str,
) -> None:
    """Recognize only the complete standard system LFS definitions, once each."""
    seen = set()
    for scope, key, value in rows:
        if not key.startswith(b"filter."):
            continue
        reason = system_reason if scope == b"system" else other_reason
        if (scope != b"system" or key not in SYSTEM_LFS_FILTERS
                or value != SYSTEM_LFS_FILTERS[key] or key in seen):
            raise BenchmarkError(reason)
        seen.add(key)
    if seen and seen != SYSTEM_LFS_FILTERS.keys():
        raise BenchmarkError(system_reason)


def _qualify_path_filters(
    root: Path, git: Path, env: Mapping[str, str], deadline: float,
    control: RunControl | None, reason: str,
) -> None:
    """Resolve effective attributes without executing filters or recursing submodules."""
    staged = git_call(git, root, env, deadline, "ls-files", "--stage", "-z", control=control)
    if any(row.startswith(b"160000 ") for row in staged.split(b"\0")):
        raise BenchmarkError("submodules_unqualified")
    raw = git_call(git, root, env, deadline, "ls-files", "--cached", "--others",
                   "--exclude-standard", "-z", control=control)
    if not raw:
        return
    if not raw.endswith(b"\0"):
        raise BenchmarkError(reason)
    paths = raw.split(b"\0")[:-1]
    attributes = git_call(git, root, env, deadline, "check-attr", "-z", "--stdin",
                          "filter", input_data=raw, control=control)
    fields = attributes.split(b"\0")
    if fields[-1] != b"" or len(fields) != 3 * len(paths) + 1:
        raise BenchmarkError(reason)
    for index, path in enumerate(paths):
        offset = index * 3
        if (fields[offset:offset + 2] != [path, b"filter"]
                or fields[offset + 2] not in (b"unspecified", b"unset")):
            raise BenchmarkError(reason)


def qualify_git(git: Path, fixture: Path, env: Mapping[str, str], deadline: float,
                control: RunControl | None = None) -> str:
    """Qualify native configuration, including the helper's stripped-env behavior."""
    if control is not None:
        control.admit()
    result = run_owned([str(git), "config", "--show-scope", "-z", "--list"],
                       fixture, env, _remaining(deadline),
                       cancelled=(lambda: control.cancelled) if control else None)
    if not result.cleanup_complete:
        if control is not None:
            control.cleanup_known = False
        raise CleanupUncertain("cleanup_uncertain")
    if control is not None:
        control.admit()
    if result.status != "completed" or result.returncode:
        raise BenchmarkError("git_configuration_unqualified")
    rows = _configuration_rows(result.stdout)
    _qualify_filter_definitions(rows, system_reason="git_system_configuration_unqualified",
                                other_reason="git_filters_unqualified")
    local_helpers = []
    qualified_rows = []
    for scope, key, value in rows:
        if scope == b"system" and key != b"credential.helper" and key not in SYSTEM_LFS_FILTERS:
            raise BenchmarkError("git_system_configuration_unqualified")
        if scope not in (b"local", b"system"):
            raise BenchmarkError("git_configuration_unqualified")
        if scope == b"local" and key == b"credential.helper":
            local_helpers.append(value)
        if scope == b"local" and key == b"core.hookspath":
            expected = fixture.parent / "empty-templates"
            if value != os.fsencode(expected) or expected.is_symlink() or any(expected.iterdir()):
                raise BenchmarkError("git_hooks_unqualified")
            value = b"owned_empty_hooks"
        qualified_rows.append([scope.decode(), key.decode(), hashlib.sha256(value).hexdigest()])
    # An empty local credential helper resets preceding system helpers. No selected
    # workload uses transport. Standard LFS definitions additionally require fresh
    # proof that no path selects a filter; all other system keys are refused.
    if local_helpers != [b""]:
        raise BenchmarkError("git_credentials_unqualified")
    _qualify_path_filters(fixture, git, env, deadline, control, "git_filters_unqualified")
    return evidence.digest(qualified_rows)


def qualify_source_config(root: Path, git: Path, env: Mapping[str, str], deadline: float,
                          control: RunControl | None = None) -> None:
    configuration = git_call(git, root, env, deadline, "config", "--show-scope", "--includes",
                             "-z", "--list", control=control)
    rows = _configuration_rows(configuration)
    _qualify_filter_definitions(rows, system_reason="source_filters_unqualified",
                                other_reason="source_filters_unqualified")
    for _, key, _ in rows:
        if key.lower().startswith(b"core.attributesfile"):
            raise BenchmarkError("source_filters_unqualified")
    _qualify_path_filters(root, git, env, deadline, control, "source_filters_unqualified")


@dataclass(frozen=True)
class SourceSnapshot:
    root: Path
    helper: Path
    commit: str
    tree: str
    lock_sha256: str
    helper_sha256: str

    @classmethod
    def observe(cls, path: Path, git: Path, env: Mapping[str, str], deadline: float,
                control: RunControl | None = None):
        root = path.resolve(strict=True)
        top = git_call(git, root, env, deadline, "rev-parse", "--show-toplevel", control=control).decode().strip()
        if Path(top).resolve() != root:
            raise BenchmarkError("source_must_be_repository_root")
        qualify_source_config(root, git, env, deadline, control)
        if git_call(git, root, env, deadline, "status", "--porcelain=v1", "--untracked-files=all", control=control):
            raise BenchmarkError("source_not_clean")
        helper = root / "dot_local/bin/executable_dbsctrctl"
        lock = root / "uv.lock"
        for selected in (helper, lock):
            current = root
            for part in selected.relative_to(root).parts:
                current /= part
                if current.is_symlink():
                    raise BenchmarkError("source_alias")
            if not selected.is_file():
                raise BenchmarkError("source_unavailable")
        return cls(
            root, helper,
            git_call(git, root, env, deadline, "rev-parse", "HEAD", control=control).decode().strip(),
            git_call(git, root, env, deadline, "rev-parse", "HEAD^{tree}", control=control).decode().strip(),
            file_digest(lock), file_digest(helper),
        )

    def verify(self, git: Path, env: Mapping[str, str], deadline: float,
               control: RunControl | None = None) -> None:
        if self != self.observe(self.root, git, env, deadline, control):
            raise BenchmarkError("source_changed")


@dataclass(frozen=True)
class LaunchProof:
    paths: tuple[Path, ...]
    identities: tuple[tuple[str, str], ...]

    @classmethod
    def observe(cls, paths: Sequence[Path]):
        selected = tuple(paths)
        identities = tuple((str(path.resolve(strict=True)), file_digest(path.resolve(strict=True)))
                           for path in selected)
        return cls(selected, identities)

    def verify(self) -> None:
        try:
            changed = self != self.observe(self.paths)
        except OSError:
            changed = True
        if changed:
            raise BenchmarkError("launch_identity_changed")


def fixture_content_digest(root: Path) -> str:
    contents = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise BenchmarkError("fixture_alias")
        if path.is_file():
            contents.append([path.relative_to(root).as_posix(), file_digest(path)])
    return evidence.digest(contents)


@dataclass(frozen=True)
class FixtureProof:
    root: Path
    metadata_digest: str
    head: str
    tree: str
    count: int
    inputs: tuple[tuple[str, str], ...]

    @classmethod
    def observe(cls, root: Path, git: Path, env: Mapping[str, str], deadline: float,
                control: RunControl | None = None):
        if not (root / ".git").is_dir() or (root / ".git").is_symlink():
            raise BenchmarkError("fixture_not_standalone")
        if (root / ".git/dbsctr").exists():
            raise BenchmarkError("fixture_state_changed")
        raw = git_call(git, root, env, deadline, "rev-parse", "HEAD", "HEAD^{tree}", control=control).decode().splitlines()
        count = int(git_call(git, root, env, deadline, "rev-list", "--count", "HEAD", control=control))
        inputs = tuple((name, file_digest(root / name)) for name in
                       ("README.md", "manifest-10.json", "manifest-100.json"))
        return cls(root, fixture_content_digest(root), raw[0], raw[1], count, inputs)

    def verify(self, git: Path, env: Mapping[str, str], deadline: float,
               control: RunControl | None = None) -> None:
        # Pure file proof precedes any Git command so altered configuration cannot
        # become executable proof work. The final attempt is checked as well.
        if fixture_content_digest(self.root) != self.metadata_digest:
            raise BenchmarkError("fixture_changed")
        if self != self.observe(self.root, git, env, deadline, control):
            raise BenchmarkError("fixture_changed")

    def identity(self, generator: str) -> str:
        return evidence.digest({"generator": generator, "head": self.head,
                                "tree": self.tree, "count": self.count, "inputs": self.inputs})


COUNT_LAUNCHER = r"""
import json, os, pathlib, runpy, sys
helper, target, *arguments = sys.argv[1:]
counts = {}
allowed = {"rev-parse","rev-list","symbolic-ref","worktree","status","show","cat-file","log","diff","config","ls-files"}
def observe(event, values):
    if event == "subprocess.Popen":
        executable, argv, *_ = values
        if pathlib.Path(os.fsdecode(executable)).name != "git":
            raise RuntimeError("unexpected_child")
        operation = argv[1] if len(argv) > 1 else ""
        if operation not in allowed:
            raise RuntimeError("unexpected_git_operation")
        counts[operation] = counts.get(operation, 0) + 1
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise RuntimeError("network_forbidden")
sys.addaudithook(observe)
sys.argv = [helper, *arguments]
try:
    runpy.run_path(helper, run_name="__main__")
finally:
    with open(target, "x", encoding="utf-8") as stream:
        json.dump(counts, stream, sort_keys=True)
"""


def report_records(paths: Sequence[Path], *, deadline: float | None = None) -> dict[str, object]:
    """Offline inputs remain separate; a matching asserted token proves no host."""
    deadline = time.monotonic() + 60 if deadline is None else deadline
    records = evidence.read_records(paths, deadline=deadline)
    summaries = []
    for record in records:
        if time.monotonic() >= deadline:
            raise EvidenceError("analysis_budget_exhausted")
        summaries.append({
            "source": record["source"], "environment": record["environment"],
            "cell": record["cell"], "coverage": record["coverage"],
            "summary": record["summary"], "evidence_sha256": evidence.digest(record),
        })
    return {
        "schema_version": 1, "input_authenticity": "unverified",
        "aggregated_across_inputs": False, "records": summaries,
    }


def _oracle(case: Mapping[str, object], stdout: bytes, config: dict, runtime: str) -> bool:
    if case["id"] == "help":
        return hashlib.sha256(stdout).hexdigest() == config["runtime_help"][runtime]["stdout_sha256"]
    if case["id"] == "status_empty":
        return stdout == b"null\n"
    nodes = int(case["nodes"])
    expected = {
        "schema_version": 1, "initiative_id": "synthetic-benchmark",
        "manifest_digest": evidence.digest(fixture_manifest(nodes)),
        "counts": {"contexts": 1, "statements": 1, "slices": nodes, "release_groups": 1},
        "ready_slices": [], "state": "captured",
    }
    # Object semantics are the contract; exact canonical bytes are checked too.
    return stdout == evidence.canonical(expected) + b"\n"


def _descriptor(mode: str) -> dict[str, dict[str, object]]:
    if mode == "git_count":
        return {"git_launches": {"unit": "count", "scope": "python_direct_subprocess", "required": True}}
    if mode == "profile":
        return {"profile_bytes": {"unit": "bytes", "scope": "cprofile_output", "required": True}}
    return {
        "wall_ns": {"unit": "ns", "scope": "whole_process", "required": True},
        "cpu_ns": {"unit": "ns", "scope": "owned_children", "required": False},
    }


def _empty_attempt(sequence: int, status: str, reason: str, descriptors: Mapping) -> dict:
    return {
        "sequence": sequence, "warmup": sequence == 0, "status": status,
        "reason": reason, "compatible": False, "returncode": None,
        "metrics": {key: None for key in descriptors},
        "unavailable": {key: reason for key in descriptors}, "output_sha256": None,
    }


def _scratch_size(directory: Path) -> int:
    total = 0
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise BenchmarkError("scratch_alias")
        if path.is_file():
            total += path.stat().st_size
            if total > SCRATCH_LIMIT:
                raise BenchmarkError("scratch_limit")
    return total


def _load_fixture() -> dict:
    if FIXTURE_PATH.is_symlink() or FIXTURE_PATH.stat().st_size > STREAM_LIMIT:
        raise BenchmarkError("fixture_unavailable")
    with FIXTURE_PATH.open("rb") as stream:
        raw = stream.read(STREAM_LIMIT + 1)
    if len(raw) > STREAM_LIMIT:
        raise BenchmarkError("fixture_unavailable")
    config = json.loads(raw)
    if (set(config) != {"schema_version", "helper_sha256", "columns", "runtime_help", "histories", "cases"}
            or config["schema_version"] != 1 or config["columns"] != 100
            or config["histories"] != [1, 100]
            or config["cases"] != [{"id": "help", "nodes": 0}, {"id": "status_empty", "nodes": 0},
                                   {"id": "initiative_10", "nodes": 10}, {"id": "initiative_100", "nodes": 100}]):
        raise BenchmarkError("fixture_unavailable")
    return config


def finish_attempt(row: dict, control: RunControl, proof: Callable[[], None]) -> str | None:
    """Commit observation eligibility only after fresh proof and cancellation checks."""
    try:
        control.admit()
        proof()
        control.admit()
        return None
    except BenchmarkError as error:
        if isinstance(error, CleanupUncertain):
            control.cleanup_known = False
        reason = str(error)
        row.update(status="cancelled" if reason == "cancelled" else "failed",
                   reason=reason, compatible=False)
        row["metrics"] = {name: None for name in row["metrics"]}
        row["unavailable"] = {name: reason for name in row["metrics"]}
        return reason


def benchmark_cli(source_root: Path, output: Path, *, smoke: bool = False, profile: bool = False) -> int:
    git_selected = shutil.which("git")
    if not git_selected:
        raise BenchmarkError("git_unavailable")
    git = Path(git_selected).resolve(strict=True)
    runtime = ".".join(map(str, sys.version_info[:2]))
    config = _load_fixture()
    if runtime not in config["runtime_help"]:
        raise BenchmarkError("runtime_oracle_unavailable")
    config_digest = evidence.digest(config)
    output = evidence.create_private_output(output, source_root.resolve())
    scratch = output / "scratch"
    scratch.mkdir(mode=0o700)
    env = isolated_environment(scratch, git)
    deadline = time.monotonic() + TOTAL_SECONDS
    control = RunControl()
    def cancel(_signum, _frame):
        control.cancelled = True
    previous = {sig: signal.signal(sig, cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    cleanup_known = True
    exit_code = 0
    try:
        fixtures = {}
        for commits in config["histories"]:
            fixtures[commits] = create_fixture(scratch / f"git-{commits}", commits, git, env, deadline, control)
        qualification = qualify_git(git, fixtures[1][0], env, deadline, control)
        source = SourceSnapshot.observe(source_root, git, env, deadline, control)
        if source.helper_sha256 != config["helper_sha256"]:
            raise BenchmarkError("helper_oracle_unavailable")
        tool_root = Path(__file__).resolve().parents[2]
        tool_commit = git_call(git, tool_root, env, deadline, "rev-parse", "HEAD", control=control).decode().strip()
        qualify_source_config(tool_root, git, env, deadline, control)
        if git_call(git, tool_root, env, deadline, "status", "--porcelain=v1",
                    "--untracked-files=all", "--", "tests/benchmarks", control=control):
            raise BenchmarkError("tool_source_not_clean")
        config_digest = evidence.digest({
            "fixture": config, "tool_commit": tool_commit,
            "tool_files": {name: file_digest(Path(__file__).with_name(name))
                           for name in ("python_performance.py", "performance_evidence.py")},
        })
        environment = {
            "python": platform.python_version(), "python_sha256": file_digest(Path(sys.executable).resolve()),
            "git_version": git_call(git, fixtures[1][0], env, deadline, "--version", control=control).decode().strip(),
            "git_sha256": file_digest(git), "os": platform.system(),
            "os_version": platform.release(), "architecture": platform.machine(),
            "cpu_count": os.cpu_count() or 1, "execution_cohort": uuid.uuid4().hex,
        }
        launch_proof = LaunchProof.observe([
            Path(sys.executable), git, Path(__file__), SIBLING, FIXTURE_PATH,
        ])
        fixture_proofs = {commits: FixtureProof.observe(fixture[0], git, env, deadline, control)
                          for commits, fixture in fixtures.items()}
        source_identity = {
            "commit": source.commit, "tree": source.tree, "tool_commit": tool_commit,
            "lock_sha256": source.lock_sha256, "workload_sha256": config_digest, "clean": True,
        }
        modes = ("timing", "git_count", "profile") if profile else ("timing", "git_count")
        planned = 1 if smoke else 10
        manifest = []
        stopped = None
        for mode in modes:
            for commits in config["histories"]:
                fixture, fixture_digest = fixtures[commits]
                for case in config["cases"]:
                    descriptors = _descriptor(mode)
                    attempts = []
                    for sequence in range(planned + 1):
                        if control.cancelled or stopped or time.monotonic() >= deadline:
                            reason = stopped or ("cancelled" if control.cancelled else "budget_exhausted")
                            attempts.append(_empty_attempt(sequence, "not_attempted", reason, descriptors))
                            exit_code = 75 if exit_code == 0 else exit_code
                            continue
                        try:
                            control.admit()
                            launch_proof.verify()
                            fixture_proofs[commits].verify(git, env, deadline, control)
                            source.verify(git, env, deadline, control)
                            if qualify_git(git, fixture, env, deadline, control) != qualification:
                                raise BenchmarkError("git_configuration_changed")
                            if (fixture / ".git/dbsctr").exists():
                                raise BenchmarkError("fixture_state_changed")
                            reservation = 2 * STREAM_LIMIT + (PROFILE_LIMIT if mode == "profile" else 0)
                            if _scratch_size(output) + reservation > SCRATCH_LIMIT:
                                raise BenchmarkError("scratch_limit")
                        except BenchmarkError as error:
                            cleanup_known &= not isinstance(error, CleanupUncertain)
                            stopped = str(error)
                            attempts.append(_empty_attempt(sequence, "not_attempted", stopped, descriptors))
                            exit_code = 75 if exit_code == 0 else exit_code
                            continue
                        arguments = (["--help"] if case["id"] == "help" else
                                     ["status", "--json"] if case["id"] == "status_empty" else
                                     ["initiative-check", "--manifest", f"manifest-{case['nodes']}.json", "--json"])
                        label = f"{mode}-{commits}-{case['id']}-{sequence}"
                        profiles = output / "profiles"
                        if mode == "profile":
                            profiles.mkdir(exist_ok=True, mode=0o700)
                        detail = (profiles if mode == "profile" else scratch) / (
                            label + (".json" if mode == "git_count" else ".pstats"))
                        child = [sys.executable, "-I", "-S", "-B"]
                        if mode == "git_count":
                            child += ["-c", COUNT_LAUNCHER, str(source.helper), str(detail), *arguments]
                        elif mode == "profile":
                            child += ["-m", "cProfile", "-o", str(detail), str(source.helper), *arguments]
                        else:
                            child += [str(source.helper), *arguments]
                        result = run_owned(
                            child, fixture, env, _remaining(deadline),
                            cancelled=lambda: control.cancelled,
                            watch_limit=(detail, PROFILE_LIMIT) if mode == "profile" else None,
                        )
                        cleanup_known &= result.cleanup_complete
                        control.cleanup_known &= result.cleanup_complete
                        compatible = (result.status == "completed" and result.returncode == 0
                                      and not result.stderr and _oracle(case, result.stdout, config, runtime))
                        values = {name: None for name in descriptors}
                        if compatible:
                            if mode == "timing":
                                values.update(wall_ns=result.wall_ns, cpu_ns=result.cpu_ns)
                            elif mode == "git_count":
                                with detail.open("rb") as counter:
                                    raw = counter.read(STREAM_LIMIT + 1)
                                counts = json.loads(raw) if len(raw) <= STREAM_LIMIT else None
                                if (type(counts) is not dict or set(counts) - ALLOWED_GIT
                                        or any(type(value) is not int or value < 0 for value in counts.values())):
                                    compatible = False
                                else:
                                    values["git_launches"] = sum(counts.values())
                            elif detail.is_file() and detail.stat().st_size <= PROFILE_LIMIT:
                                values["profile_bytes"] = detail.stat().st_size
                            else:
                                compatible = False
                        status = ("partial" if any(value is None for value in values.values()) else "measured") if compatible else (
                            result.status if result.status in {"timed_out", "cancelled"} else "failed")
                        reason = None if compatible else (
                            result.status if result.status != "completed" else "output_mismatch")
                        row = {
                            "sequence": sequence, "warmup": sequence == 0, "status": status,
                            "reason": reason, "compatible": compatible, "returncode": result.returncode,
                            "metrics": values,
                            "unavailable": {name: "unqualified_process_cpu" if name == "cpu_ns" and compatible else (reason or "metric_unavailable")
                                            for name, value in values.items() if value is None},
                            "output_sha256": hashlib.sha256(result.stdout).hexdigest(),
                        }
                        attempts.append(row)
                        raw_directory = output / "raw"
                        raw_directory.mkdir(exist_ok=True, mode=0o700)
                        for stream, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
                            path = raw_directory / f"{label}.{stream}"
                            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                            with os.fdopen(descriptor, "wb") as target:
                                target.write(raw)
                        def post_proof():
                            launch_proof.verify()
                            fixture_proofs[commits].verify(git, env, deadline, control)
                            source.verify(git, env, deadline, control)
                        rejected = finish_attempt(row, control, post_proof)
                        if rejected:
                            stopped = rejected
                            cleanup_known &= control.cleanup_known
                            compatible = False
                        if not cleanup_known:
                            stopped = "cleanup_uncertain"
                        elif result.status in {"timed_out", "cancelled", "output_overflow"}:
                            stopped = result.status
                        if not compatible:
                            exit_code = (75 if exit_code == 0 else exit_code) if row["status"] == "cancelled" else 1
                    cell = {
                        "surface": "cli", "workload": case["id"],
                        "dimensions": {"history_commits": commits, "cohort": "smoke" if smoke else "full",
                                       "git_configuration": qualification},
                        "fixture_sha256": fixture_proofs[commits].identity(fixture_digest), "instrumentation": mode,
                        "cache": "fresh_process_uncontrolled_filesystem", "metrics": descriptors,
                    }
                    record = evidence.build_record(source_identity, environment, cell, attempts, planned)
                    name = f"{mode}-{commits}-{case['id']}.json"
                    evidence.write_private_json(output, name, record)
                    manifest.append(name)
        if control.cancelled and exit_code == 0:
            exit_code = 75
        evidence.write_private_json(output, "index.json", {
            "schema_version": 1, "records": manifest, "cohort": "smoke" if smoke else "full",
            "status": "complete" if exit_code == 0 else "partial",
        })
        return exit_code
    except CleanupUncertain:
        cleanup_known = False
        evidence.write_private_json(output, "error.json", {
            "schema_version": 1, "status": "unavailable", "reason": "cleanup_uncertain",
        })
        raise
    except BenchmarkError as error:
        evidence.write_private_json(output, "error.json", {
            "schema_version": 1, "status": "unavailable", "reason": str(error),
        })
        raise
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if cleanup_known and control.cleanup_known:
            shutil.rmtree(scratch)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cli = commands.add_parser("cli", help="run bounded synthetic CLI cohorts")
    cli.add_argument("--source-tree", required=True, type=Path)
    cli.add_argument("--output", required=True, type=Path)
    cli.add_argument("--smoke", action="store_true")
    cli.add_argument("--profile", action="store_true")
    report = commands.add_parser("report", help="validate private evidence without execution")
    report.add_argument("--input", required=True, action="append", type=Path)
    report.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "cli":
            result = benchmark_cli(args.source_tree, args.output, smoke=args.smoke, profile=args.profile)
        else:
            started = time.monotonic()
            value = report_records(args.input, deadline=started + 60)
            if time.monotonic() - started > 60:
                raise BenchmarkError("report_budget_exhausted")
            directory = evidence.create_private_output(args.output)
            evidence.write_private_json(directory, "report.json", value)
            result = 0
        print(json.dumps({"status": "complete" if result == 0 else "partial", "exit_code": result}))
        return result
    except (EvidenceError, BenchmarkError) as error:
        print(json.dumps({"status": "unavailable", "reason": str(error)}))
        return 75 if isinstance(error, BenchmarkError) or str(error) == "analysis_budget_exhausted" else 2
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"status": "unavailable", "reason": "input_or_capability_unavailable"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
