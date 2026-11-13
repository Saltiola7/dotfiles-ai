"""Data-only Git replay, sharing the delivered rebased-completion proof rules.

No checkout, hooks, credential lookup, forge mutation or caller-selected executable.
An explicit delegated mirror may fetch same-repository object data.
Native adapters establish repository/PR/producer identity separately. A proof of
the same patch series alone cannot establish which PR introduced landed commits.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
import base64
import os
from pathlib import Path
import signal
import subprocess
import tempfile

from . import core
from . import runtime

MAX_OUTPUT = 32 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class Proof:
    base: str
    head: str
    tree: str
    pairs: tuple[core.CommitPair, ...]


class GitObjects:
    """Inspect an already populated object repository under a closed environment."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve(strict=True)

    def _result(self, args: tuple[str, ...], *, negative: bool = False) -> tuple[int, bytes]:
        env = {key: os.environ[key] for key in ("PATH", "TMPDIR", "LANG") if key in os.environ}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                   GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0",
                   GIT_TERMINAL_PROMPT="0", GIT_ATTR_NOSYSTEM="1", LC_ALL="C")
        try:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                result = subprocess.run(
                    ["git", "--no-replace-objects", "-c", "core.hooksPath=" + os.devnull,
                     "-c", "core.attributesFile=" + os.devnull, "-c", "core.fsmonitor=false",
                     "-c", "protocol.allow=never", "-C", str(self.path), *args],
                    env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=errors, timeout=60,
                )
                if (result.returncode not in ((0, 1) if negative else (0,))
                        or output.tell() > MAX_OUTPUT or errors.tell() > MAX_OUTPUT):
                    raise core.Invalid("git_proof_refused")
                output.seek(0)
                return result.returncode, output.read(MAX_OUTPUT + 1)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise core.Unavailable("git_proof_unavailable") from error

    def read(self, *args: str) -> str:
        _, raw = self._result(args)
        try:
            return raw.decode("utf-8", errors="strict").rstrip("\n")
        except UnicodeError as error:
            raise core.Invalid("git_proof_encoding") from error

    def ancestor(self, before: str, after: str) -> bool:
        core._oid(before)
        core._oid(after)
        if self.read("rev-parse", "--is-shallow-repository") != "false":
            raise core.Invalid("git_proof_shallow")
        code, _ = self._result(("merge-base", "--is-ancestor", before, after), negative=True)
        return code == 0

    def excludes_root(self, root: str, sources: tuple[str, ...]) -> bool:
        core._oid(root)
        core._oids(sources, 1024, 1)
        self.safety()
        return all(not self.ancestor(root, source) for source in sources)

    def safety(self) -> None:
        grafts = Path(self.read("rev-parse", "--git-path", "info/grafts"))
        if (grafts if grafts.is_absolute() else self.path / grafts).exists():
            raise core.Invalid("git_proof_grafts")
        for item in self.read("config", "--local", "--list", "-z").split("\0"):
            key = item.split("\n", 1)[0].casefold()
            if key.startswith("filter.") or key.startswith("merge.") and key.endswith(".driver"):
                raise core.Invalid("git_proof_driver")
        if self.read("for-each-ref", "--format=%(refname)", "refs/replace"):
            raise core.Invalid("git_proof_replace")

    def tree(self, commit: str) -> str:
        core._oid(commit)
        value = self.read("rev-parse", commit + "^{tree}")
        core._oid(value)
        return value

    def attribution(self, commit: str) -> bytes:
        core._oid(commit)
        return self._result(("show", "-s", "--format=%an%x00%ae%x00%aI%x00%B", commit))[1]

    def safe_tree(self, tree: str) -> None:
        core._oid(tree)
        for item in self.read("ls-tree", "-r", "-z", tree).split("\0"):
            if not item:
                continue
            metadata, name = item.split("\t", 1)
            if metadata.startswith("160000 "):
                raise core.Invalid("git_proof_submodule")
            if name.rsplit("/", 1)[-1] == ".gitattributes":
                for line in self.read("cat-file", "blob", metadata.split()[2]).splitlines():
                    if line.lstrip().startswith("#"):
                        continue
                    if any(word.lstrip("-!").split("=", 1)[0]
                           in {"merge", "filter", "working-tree-encoding"}
                           for word in line.split()[1:]):
                        raise core.Invalid("git_proof_attributes")


def prove_series(objects: GitObjects, source_base: str, sources: tuple[str, ...],
                 head: str, expected_base: str) -> Proof:
    """Replay each original delta and check author/message plus the exact new base.

    This is the conservative single-parent, nonempty route already qualified by
    rebased-completion. Unsupported wrappers retain the task; no phase is dropped.
    """
    core._oids(sources, 1024, 1)
    for value in (source_base, head, expected_base):
        core._oid(value)
    if len({len(value) for value in (source_base, head, expected_base, *sources)}) != 1:
        raise core.Invalid("mixed_oid_formats")
    objects.safety()
    actual = objects.read("rev-list", "--first-parent", "--reverse", "--max-count=1025",
                          source_base + ".." + sources[-1]).splitlines()
    if tuple(actual) != sources or not objects.ancestor(source_base, expected_base):
        raise core.Invalid("git_proof_source_range")
    destinations = objects.read("rev-list", "--first-parent", "--max-count=" + str(len(sources)),
                                head).splitlines()[::-1]
    if len(destinations) != len(sources):
        raise core.Invalid("git_proof_landed_range")
    prior_source, prior_result = source_base, expected_base
    pairs: list[core.CommitPair] = []
    checked: set[str] = set()
    for source, destination in zip(sources, destinations, strict=True):
        source_fields = objects.read("show", "-s", "--format=%T %P", source).split()
        result_fields = objects.read("show", "-s", "--format=%T %P", destination).split()
        if (len(source_fields) != 2 or source_fields[1] != prior_source
                or len(result_fields) != 2 or result_fields[1] != prior_result):
            raise core.Invalid("git_proof_parent_order")
        source_tree, result_tree = source_fields[0], result_fields[0]
        if source_tree == objects.tree(prior_source):
            raise core.Invalid("git_proof_empty_phase")
        if objects.attribution(source) != objects.attribution(destination):
            raise core.Invalid("git_proof_attribution")
        for revision in (source, prior_source, destination, prior_result):
            tree = objects.tree(revision)
            if tree not in checked:
                objects.safe_tree(tree)
                checked.add(tree)
        replay = objects.read("merge-tree", "--write-tree", "--merge-base=" + prior_source,
                              prior_result, source).splitlines()
        if replay != [result_tree]:
            raise core.Invalid("git_proof_delta")
        pairs.append(core.CommitPair(source, destination))
        prior_source, prior_result = source, destination
    return Proof(expected_base, head, objects.tree(head), tuple(pairs))


class ProofPort:
    """Reprove all links from data-only objects, rather than trusting a receipt."""

    def __init__(self, supply: Callable[[tuple[str, ...]], GitObjects]) -> None:
        self._supply = supply

    def prove_refresh(self, source: runtime.SourceSeries, head: str, base: str) -> runtime.Projection:
        ids = tuple(dict.fromkeys((source.base, source.head, head, base)))
        proof = prove_series(self._supply(ids), source.base,
                             tuple(entry.oid for entry in source.entries), head, base)
        return runtime.Projection(core.identity(source), base, head, proof.pairs, core.identity(proof))

    def prove_delivery(self, source: runtime.SourceSeries, projection: runtime.Projection,
                       merge_oid: str) -> tuple[core.CommitPair, ...]:
        verified = self.prove_refresh(source, projection.head, projection.base)
        if projection != verified:
            raise core.Invalid("git_proof_projection_changed")
        ids = tuple(dict.fromkeys((projection.base, projection.head, merge_oid)))
        proof = prove_series(self._supply(ids), projection.base,
                             tuple(pair.landed for pair in projection.mapping), merge_oid, projection.base)
        return proof.pairs

    def excludes_root(self, root: str, heads: tuple[str, ...]) -> bool:
        ids = tuple(dict.fromkeys((root, *heads)))
        return self._supply(ids).excludes_root(root, heads)


class GitMirror:
    """One ephemeral object store; fetches exact same-repository OIDs only.

    No remote/configuration or authentication is taken from a task checkout.
    The delegated token exists only in the child environment; it is never placed
    in argv, on disk, in a record or in diagnostic output. No branch is created.
    """

    __slots__ = ("_repository", "_token", "_temporary", "_path", "_known", "_width")

    def __init__(self, repository: str, token: str) -> None:
        core._repository(repository)
        if not token or any(ord(char) < 33 or ord(char) == 127 for char in token):
            raise core.Invalid("git_mirror_credential")
        self._repository = repository
        self._token = token
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self._path: Path | None = None
        self._known: set[str] = set()
        self._width: int | None = None

    def __repr__(self) -> str:
        return "GitMirror(<data-only>)"

    def __enter__(self) -> GitMirror:
        self._temporary = tempfile.TemporaryDirectory(prefix="dbsctr-git-proof-")
        self._path = Path(self._temporary.name) / "objects.git"
        return self

    def __exit__(self, *_error: object) -> None:
        self._token = ""
        if self._temporary is not None:
            self._temporary.cleanup()
        self._path = None

    def _run(self, *args: str, authenticated: bool = False) -> None:
        env = {key: os.environ[key] for key in ("PATH", "TMPDIR", "LANG") if key in os.environ}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                   GIT_NO_REPLACE_OBJECTS="1", GIT_ATTR_NOSYSTEM="1", LC_ALL="C")
        if authenticated:
            header = base64.b64encode(("x-access-token:" + self._token).encode()).decode()
            env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.https://github.com/.extraHeader",
                       GIT_CONFIG_VALUE_0="AUTHORIZATION: basic " + header)
        try:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                process = subprocess.Popen(
                    ["git", "--no-replace-objects", "-c", "core.hooksPath=" + os.devnull,
                     "-c", "core.attributesFile=" + os.devnull, "-c", "core.fsmonitor=false",
                     "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
                     "-c", "fetch.fsckObjects=true", *args], env=env, stdin=subprocess.DEVNULL,
                    stdout=output, stderr=errors, start_new_session=True,
                )
                try:
                    process.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    raise core.Unavailable("git_mirror_timeout") from None
                if process.returncode or output.tell() > MAX_OUTPUT or errors.tell() > MAX_OUTPUT:
                    raise core.Unavailable("git_mirror_unavailable")
        except (OSError, subprocess.TimeoutExpired):
            raise core.Unavailable("git_mirror_unavailable") from None

    def supply(self, oids: tuple[str, ...]) -> GitObjects:
        core._oids(oids, 1024, 1)
        if self._path is None or len({len(oid) for oid in oids}) != 1:
            raise core.Invalid("git_mirror_scope")
        width = len(oids[0])
        if self._width is None:
            self._width = width
            self._run("init", "--bare", "--template=", "--object-format=" + ("sha1" if width == 40 else "sha256"),
                      str(self._path))
        if width != self._width:
            raise core.Invalid("mixed_oid_formats")
        missing = tuple(oid for oid in oids if oid not in self._known)
        if missing:
            self._run("-C", str(self._path), "fetch", "--no-tags", "--no-write-fetch-head",
                      "https://github.com/" + self._repository + ".git", *missing, authenticated=True)
            self._known.update(missing)
        return GitObjects(self._path)
