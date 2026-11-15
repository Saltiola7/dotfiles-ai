"""Align one retained local task after the lifecycle owner qualifies a projection.

The caller owns private task/Gitdir admission and the repository mutation lock.
A Projection is structural data: this module never authenticates one from JSON.
It never fetches, resets, forces a checkout, changes lifecycle records or removes
source refs. Configured user hooks run normally. An interrupted checkout may run
its post-checkout hook again before a missing success event can be acknowledged.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from typing import Protocol

from . import core as c
from . import runtime as r

PHASES = ("prepared", "detached", "ref_updated", "attached")
MAX_OUTPUT = 1024 * 1024


def _hash(value: object) -> str:
    return hashlib.sha256(c._canonical(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class AlignmentContext:
    checkout: Path
    common_git_dir: Path
    branch: str
    default_branch: str
    control_branch: str
    scope_digest: str

    def __post_init__(self) -> None:
        for path in (self.checkout, self.common_git_dir):
            if not isinstance(path, Path) or not path.is_absolute() or any(ord(ch) < 32 for ch in str(path)):
                raise c.Invalid("alignment_context_path")
        for branch in (self.branch, self.default_branch, self.control_branch): c._branch(branch)
        c._digest(self.scope_digest)
        if self.branch.startswith("-") or self.branch in {"main", "master", self.default_branch, self.control_branch}:
            raise c.Invalid("alignment_protected_branch")


@dataclass(frozen=True, slots=True)
class RetainedRef:
    ref: str
    oid: str

    def __post_init__(self) -> None:
        if not isinstance(self.ref, str) or not self.ref.startswith("refs/dbsctr/"):
            raise c.Invalid("alignment_retention_namespace")
        c._branch(self.ref[len("refs/"):]); c._oid(self.oid)


@dataclass(frozen=True, slots=True)
class JournalEvent:
    operation_digest: str
    scope_digest: str
    plan_digest: str
    phase: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        for value in (self.operation_digest, self.scope_digest, self.plan_digest): c._digest(value)
        if self.phase not in PHASES or type(self.schema_version) is not int or self.schema_version != 1:
            raise c.Invalid("alignment_journal_event")


class JournalPort(Protocol):
    """Owner-private immutable create-or-identical bytes, durably fsynced."""
    def read(self, operation_digest: str, phase: str) -> bytes | None: ...
    def write(self, operation_digest: str, phase: str, payload: bytes) -> None: ...


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result: raise c.Invalid("alignment_journal_duplicate")
        result[key] = value
    return result


def decode_event(raw: bytes) -> JournalEvent:
    if type(raw) is not bytes or len(raw) > 2048: raise c.Invalid("alignment_journal_limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
        row = c._object(value, "operation_digest scope_digest plan_digest phase schema_version")
        return JournalEvent(c._text(row["operation_digest"]), c._text(row["scope_digest"]),
            c._text(row["plan_digest"]), c._text(row["phase"]), c._int(row["schema_version"]))
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        if isinstance(error, c.Invalid): raise
        raise c.Invalid("alignment_journal_invalid") from None


@dataclass(frozen=True, slots=True)
class AlignmentReceipt:
    status: str
    operation_digest: str
    scope_digest: str
    branch: str
    old_head: str
    new_head: str
    tree_oid: str
    projection_digest: str
    retention_digest: str
    schema_version: int = 1


class AlignmentPending(c.Conflict):
    """Physical state is retained; resume with the same private operation input."""
    def __init__(self, operation_digest: str, phase: str, reason: str) -> None:
        self.operation_digest = operation_digest
        self.phase = phase
        self.reason = reason
        super().__init__(reason)


class _Git:
    def __init__(self, path: Path) -> None:
        self.path = path

    def run(self, *args: str, data: bytes | None = None, negative: bool = False) -> tuple[int, bytes]:
        # Force -C to select the physical task, while preserving actual configured
        # hooks and the user's ordinary Git configuration for local operations.
        env = dict(os.environ)
        for name in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                     "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
            env.pop(name, None)
        env["GIT_TERMINAL_PROMPT"] = "0"
        try:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                process = subprocess.Popen(["git", "--no-optional-locks", "-C", str(self.path), *args],
                    env=env, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                    stdout=output, stderr=errors, start_new_session=True)
                try:
                    process.communicate(input=data, timeout=120)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.communicate(timeout=5)
                    raise c.Unavailable("alignment_git_timeout") from None
                if output.tell() > MAX_OUTPUT or errors.tell() > MAX_OUTPUT:
                    raise c.Unavailable("alignment_git_output_limit")
                code = process.returncode
                if code not in ((0, 1) if negative else (0,)):
                    raise c.Conflict("alignment_git_refused")
                output.seek(0)
                return code, output.read(MAX_OUTPUT + 1)
        except OSError:
            raise c.Unavailable("alignment_git_unavailable") from None

    def read(self, *args: str) -> str:
        try:
            return self.run(*args)[1].decode("utf-8", errors="strict").rstrip("\n")
        except UnicodeError:
            raise c.Invalid("alignment_git_encoding") from None

    def ref(self, name: str) -> str:
        if self.run("symbolic-ref", "--quiet", name, negative=True)[0] == 0:
            raise c.Conflict("alignment_symbolic_ref")
        value = self.read("show-ref", "--verify", "--hash", name)
        c._oid(value)
        return value

    def state(self) -> tuple[str | None, str]:
        code, raw = self.run("symbolic-ref", "--quiet", "HEAD", negative=True)
        try:
            branch = None if code else raw.decode("utf-8").rstrip("\n")
        except UnicodeError:
            raise c.Invalid("alignment_git_encoding") from None
        head = self.read("rev-parse", "--verify", "HEAD^{commit}"); c._oid(head)
        return branch, head


def _binding(git: _Git, context: AlignmentContext) -> str:
    if any(name in os.environ for name in ("GIT_GRAFT_FILE", "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE")):
        raise c.Conflict("alignment_local_history_configuration")
    top = Path(git.read("rev-parse", "--path-format=absolute", "--show-toplevel")).resolve(strict=True)
    common = Path(git.read("rev-parse", "--path-format=absolute", "--git-common-dir")).resolve(strict=True)
    gitdir = Path(git.read("rev-parse", "--path-format=absolute", "--git-dir")).resolve(strict=True)
    if top != context.checkout.resolve(strict=True) or common != context.common_git_dir.resolve(strict=True):
        raise c.Conflict("alignment_gitdir_changed")
    if git.read("rev-parse", "--is-shallow-repository") != "false":
        raise c.Conflict("alignment_shallow_repository")
    if git.read("for-each-ref", "--format=%(refname)", "refs/replace"):
        raise c.Conflict("alignment_local_replacements")
    grafts = Path(git.read("rev-parse", "--path-format=absolute", "--git-path", "info/grafts"))
    if (grafts.exists() or grafts.is_symlink()
            or git.run("config", "--get", "extensions.partialClone", negative=True)[0] == 0
            or git.run("config", "--get-regexp", r"^remote\..*\.promisor$", negative=True)[0] == 0):
        raise c.Conflict("alignment_local_history_configuration")
    return _hash({"checkout": str(top), "common_git_dir": str(common), "gitdir": str(gitdir)})


def _clean(git: _Git) -> None:
    if git.run("status", "--porcelain=v1", "-z", "--untracked-files=all")[1]:
        raise c.Conflict("alignment_local_drift")


def _exclusive(git: _Git, context: AlignmentContext) -> None:
    raw = git.run("worktree", "list", "--porcelain", "-z")[1]
    try:
        for block in raw.decode("utf-8").split("\0\0"):
            values = dict(line.split(" ", 1) for line in block.split("\0") if " " in line)
            if values.get("branch") == "refs/heads/" + context.branch:
                path = values.get("worktree")
                if path is None or Path(path).resolve(strict=True) != context.checkout.resolve(strict=True):
                    raise c.Conflict("alignment_branch_used_elsewhere")
    except (UnicodeError, ValueError, OSError):
        raise c.Conflict("alignment_worktree_inventory") from None


def _retained(git: _Git, expected_head: str, projection: r.Projection, refs: tuple[RetainedRef, ...]) -> str:
    c._tuple(refs, RetainedRef, 64, 1)
    if len({row.ref for row in refs}) != len(refs): raise c.Invalid("alignment_duplicate_retention_ref")
    for row in refs:
        if git.ref(row.ref) != row.oid: raise c.Conflict("alignment_retention_changed")
    # One bounded revision query proves every original and the former checkout
    # remain reachable from the independently owned evidence refs.
    needed = tuple(dict.fromkeys((expected_head, *(pair.original for pair in projection.mapping))))
    data = ("\n".join((*needed, *("^" + row.oid for row in refs))) + "\n").encode()
    if git.run("rev-list", "--max-count=1", "--stdin", data=data)[1]:
        raise c.Conflict("alignment_originals_not_retained")
    return _hash(tuple((row.ref, row.oid) for row in refs))


def align(context: AlignmentContext, expected_head: str, projection: r.Projection,
          retained_refs: tuple[RetainedRef, ...], journal: JournalPort) -> AlignmentReceipt:
    """Apply/recover one qualified projection under the caller's task lock.

    Neither journal rows nor current HEAD authenticate the supplied projection.
    That admission remains owned by the lifecycle helper and its native replay.
    """
    if type(context) is not AlignmentContext or type(projection) is not r.Projection:
        raise c.Invalid("alignment_input_type")
    c._oid(expected_head)
    if len(expected_head) != len(projection.head): raise c.Invalid("alignment_oid_format")
    git = _Git(context.checkout)
    physical = _binding(git, context)
    _clean(git); _exclusive(git, context)
    retention = _retained(git, expected_head, projection, retained_refs)
    if git.read("rev-parse", "--verify", projection.head + "^{commit}") != projection.head:
        raise c.Conflict("alignment_new_commit_missing")
    tree = git.read("rev-parse", projection.head + "^{tree}"); c._oid(tree)
    plan = _hash({"scope": context.scope_digest, "physical": physical, "branch": context.branch,
        "expected_head": expected_head, "projection": c.identity(projection), "retention": retention})
    operation = _hash({"kind": "retained_checkout_alignment", "plan": plan})
    branch_ref = "refs/heads/" + context.branch
    completed: set[str] = set()
    for phase in PHASES:
        try:
            raw = journal.read(operation, phase)
            if raw is not None:
                event = decode_event(raw)
                if event != JournalEvent(operation, context.scope_digest, plan, phase):
                    raise c.Conflict("alignment_journal_binding")
                if any(prior not in completed for prior in PHASES[:PHASES.index(phase)]):
                    raise c.Conflict("alignment_journal_order")
                completed.add(phase)
        except (OSError, ValueError, c.Invalid) as error:
            raise AlignmentPending(operation, phase, "alignment_journal_unavailable") from error

    def verify() -> tuple[str | None, str, str]:
        if _binding(git, context) != physical: raise c.Conflict("alignment_gitdir_changed")
        _clean(git); _exclusive(git, context)
        if _retained(git, expected_head, projection, retained_refs) != retention:
            raise c.Conflict("alignment_retention_changed")
        branch, head = git.state()
        return branch, head, git.ref(branch_ref)

    def event(phase: str) -> None:
        record = JournalEvent(operation, context.scope_digest, plan, phase)
        try:
            journal.write(operation, phase, c._canonical(asdict(record)))
        except (OSError, ValueError, c.Invalid) as error:
            raise AlignmentPending(operation, phase, "alignment_journal_unavailable") from error
        completed.add(phase)

    def receipt(status: str) -> AlignmentReceipt:
        return AlignmentReceipt(status, operation, context.scope_digest, context.branch, expected_head,
            projection.head, tree, c.identity(projection), retention)

    state = verify()
    desired = (branch_ref, projection.head, projection.head)
    if not completed and state == desired: return receipt("already_aligned")
    if "attached" in completed:
        if state != desired: raise AlignmentPending(operation, "attached", "alignment_completed_state_drift")
        return receipt("aligned")
    if not completed:
        if state != (branch_ref, expected_head, expected_head): raise c.Conflict("alignment_old_head_changed")
        event("prepared")
    try:
        if "detached" not in completed:
            state = verify()
            if state not in {(branch_ref, expected_head, expected_head), (None, projection.head, expected_head)}:
                raise c.Conflict("alignment_detach_state_drift")
            # Reissue on recovery if the previous checkout has no success event,
            # so a failed or interrupted configured hook is never silently waived.
            git.run("checkout", "--detach", "--no-overwrite-ignore", projection.head)
            if verify() != (None, projection.head, expected_head): raise c.Conflict("alignment_detach_state_drift")
            event("detached")
        if "ref_updated" not in completed:
            state = verify()
            if state not in {(None, projection.head, expected_head), (None, projection.head, projection.head)}:
                raise c.Conflict("alignment_ref_state_drift")
            if state[2] == expected_head:
                git.run("update-ref", "--no-deref", "-m", "dbsctr: align retained task", branch_ref, projection.head, expected_head)
            if verify() != (None, projection.head, projection.head): raise c.Conflict("alignment_ref_state_drift")
            event("ref_updated")
        state = verify()
        if state not in {(None, projection.head, projection.head), desired}:
            raise c.Conflict("alignment_attach_state_drift")
        git.run("checkout", "--no-overwrite-ignore", context.branch)
        if verify() != desired: raise c.Conflict("alignment_attach_state_drift")
        event("attached")
    except AlignmentPending:
        raise
    except (c.Conflict, c.Unavailable, OSError) as error:
        raise AlignmentPending(operation, next((phase for phase in PHASES if phase not in completed), "attached"),
                               "alignment_requires_reconciliation") from error
    return receipt("aligned")
