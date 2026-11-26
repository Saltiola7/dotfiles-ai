"""Read-only Discovery projection for a selected same-repository slice."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from functools import cache
from pathlib import Path, PurePosixPath
import posixpath
import re

from .gitproof import GitObjects


_OID = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")
_PATH = re.compile(r"docs/(?:[A-Za-z0-9_+-][A-Za-z0-9._+-]*/)*[A-Za-z0-9_+-][A-Za-z0-9._+-]*")
_LINK = re.compile(r"""\]\(\s*(?:<([^>\n]*)>|([^\s)]*))(?:\s+["'][^"'\n]*["'])?\s*\)""")
_DEFINITION = re.compile(r"^ {0,3}\[[^]\n]+\]:\s*(?:<([^>\n]+)>|(\S+))", re.M)


def _references(text: str) -> Iterator[str]:
    """Follow Markdown links and reference definitions, never fenced examples."""
    lines = []
    fence = ""
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            if marker and marker[1].startswith(fence) and not line[marker.end():].strip():
                fence = ""
        elif marker:
            fence = marker[1]
        elif not line.startswith(("    ", "\t")):
            lines.append(line)
    body = re.sub(r"(`+)([^\n]*?)\1", "", "\n".join(lines))
    if "](" in _LINK.sub("", body):
        raise ValueError("ambiguous documentation link")
    definitions = {}
    for definition in _DEFINITION.finditer(body):
        label = definition[0].split("]:", 1)[0].strip()[1:].strip().casefold()
        if label in definitions:
            raise ValueError("ambiguous documentation reference definition")
        definitions[label] = definition[1] or definition[2]
    body = _DEFINITION.sub("", body)
    targets = [match[1] or match[2] or "" for match in _LINK.finditer(body)]
    for use in re.finditer(r"\[([^]\n]+)\]\[([^]\n]*)\]", body):
        label = (use[2] or use[1]).strip().casefold()
        if label not in definitions:
            raise ValueError("missing documentation reference definition")
        targets.append(definitions[label])
    shortcuts = re.sub(r"\[[^]\n]+\]\[[^]\n]*\]|\[[^]\n]*\]\([^)\n]*\)", "", body)
    for use in re.finditer(r"\[([^]\n]+)\]", shortcuts):
        label = use[1].strip().casefold()
        if label in definitions:
            targets.append(definitions[label])
    for target in targets:
        if not target or target.startswith(("#", "https://", "http://", "mailto:")):
            continue
        target = target.partition("#")[0]
        if not re.fullmatch(r"[A-Za-z0-9._+/-]+", target) or target.startswith("/"):
            raise ValueError("ambiguous documentation link")
        yield target


def project_artifacts(repository: Path, *, base_head: str, source_commit: str,
                      declared: Iterable[str], forbidden: Iterable[str] = ()) -> list[dict[str, str]]:
    """Return initiative_import_plan's sorted changed {path,blob,mode} records.

    Caller authenticates the common repository, supplies exact receipt roots
    (including the manifest, committed plan and profile), and excludes deferred
    and exclusively sibling-owned documents. JSON is data, not link authority.
    Relative links resolve at the referring file, never by basename search.
    """
    git = GitObjects(repository)
    for oid in (base_head, source_commit):
        if not _OID.fullmatch(oid) or git.read("cat-file", "-t", oid) != "commit":
            raise ValueError("immutable Discovery commits required")
    ancestors = git.read("merge-base", "--all", base_head, source_commit).splitlines()
    if len(ancestors) != 1 or not _OID.fullmatch(ancestors[0]):
        raise ValueError("unique Discovery merge base required")

    @cache
    def entry(commit: str, path: str) -> tuple[str, str, str] | None:
        raw = git.read("--literal-pathspecs", "ls-tree", "-z", commit, "--", path)
        if not raw:
            return None
        fields, _, name = raw.partition("\t")
        mode, kind, oid = fields.split()
        if name != path + "\0" or not _OID.fullmatch(oid):
            raise ValueError("ambiguous Discovery tree entry")
        return mode, kind, oid

    roots, denied = set(declared), set(forbidden)
    namespaces = {posixpath.dirname(path) + "/" for path in roots}
    pending = set(roots)
    seen: set[str] = set()
    result = []
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        if len(seen) > 512 or not _PATH.fullmatch(name) or name in denied:
            raise ValueError(f"unavailable slice document: {name}")
        desired = entry(source_commit, name)
        if not desired or desired[:2] != ("100644", "blob"):
            raise ValueError(f"missing or irregular slice document: {name}")
        current = entry(base_head, name)
        if current != desired:
            if name not in roots and (not name.endswith((".md", ".json"))
                                      or not any(name.startswith(prefix) for prefix in namespaces)):
                raise ValueError(f"dependency outside slice documentation scope: {name}")
            if current != entry(ancestors[0], name):
                raise ValueError(f"slice document conflicts with protected base: {name}")
            for parent in PurePosixPath(name).parents:
                if parent != PurePosixPath("."):
                    ancestor = entry(base_head, str(parent))
                    if ancestor and ancestor[:2] != ("040000", "tree"):
                        raise ValueError("Discovery import parent is not a Git directory")
            result.append({"path": name, "blob": desired[2], "mode": desired[0]})
        # An unchanged transitive target is already supplied by the protected
        # tree; its incidental links cannot confer new publication authority.
        if name.endswith(".md") and (name in roots or current != desired):
            if int(git.read("cat-file", "-s", desired[2])) > 1024 * 1024:
                raise ValueError("slice document too large")
            for ref in _references(git.read("cat-file", "blob", desired[2])):
                pending.add(posixpath.normpath(posixpath.join(posixpath.dirname(name), ref)))
    return sorted(result, key=lambda item: item["path"])
