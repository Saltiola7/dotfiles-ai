"""Recoverable reconciliation of captured source records into a private vault.

The caller owns provider reads, YAML parsing/rendering, and exporter validation.
This standard-library core never contacts a provider or imports source content.
"""

from __future__ import annotations

import base64
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Callable, Iterable, Iterator
import unicodedata
import uuid


class SyncFailure(RuntimeError):
    """A content-free reconciliation failure category."""


Reader = Callable[[bytes], dict]
Renderer = Callable[[dict], bytes]
Validator = Callable[[Path], list[str] | None]
_MISSING = object()
_IDENTITY = frozenset({"schema_version", "entity_type", "id", "source_system", "source_id"})


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _copy(value: object):
    return json.loads(_json_bytes(value))


def _same(left: object, right: object) -> bool:
    if left is _MISSING or right is _MISSING:
        return left is right
    return type(left) is type(right) and left == right


def _path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise SyncFailure("invalid_path")
    path = PurePosixPath(value)
    if (path.is_absolute() or value != path.as_posix() or ".." in path.parts
            or path.parts[0] not in {"Records", "Knowledge"} or len(path.parts) < 2
            or path.suffix != ".md"):
        raise SyncFailure("invalid_path")
    return value


def _check_path_aliases(paths: Iterable[str]) -> None:
    """Reject names that could select the same file on a supported filesystem."""
    seen = {}
    for path in paths:
        key = unicodedata.normalize("NFC", unicodedata.normalize("NFC", path).casefold())
        previous = seen.setdefault(key, path)
        if previous != path:
            raise SyncFailure("invalid_duplicate")


def _flat(metadata: object) -> None:
    if not isinstance(metadata, dict):
        raise SyncFailure("invalid_metadata")
    for key, value in metadata.items():
        if not isinstance(key, str) or not key or "\x00" in key:
            raise SyncFailure("invalid_metadata")
        if value is None or type(value) in (str, int, bool):
            continue
        if type(value) is float and math.isfinite(value):
            continue
        if isinstance(value, list) and all(type(item) is str for item in value):
            continue
        raise SyncFailure("invalid_metadata")
    required = {"schema_version", "entity_type", "id", "title", "source_system", "source_id"}
    if not required.issubset(metadata) or type(metadata["schema_version"]) is not int or metadata["schema_version"] != 1:
        raise SyncFailure("invalid_metadata")
    for key in ("id", "entity_type", "title", "source_system"):
        if not isinstance(metadata[key], str) or not metadata[key] or "\x00" in metadata[key]:
            raise SyncFailure("invalid_metadata")
    if metadata["source_id"] is not None and not isinstance(metadata["source_id"], str):
        raise SyncFailure("invalid_metadata")


def _record(value: object, source: str | None = None) -> dict:
    if not isinstance(value, dict) or set(value) != {"path", "metadata", "body"}:
        raise SyncFailure("invalid_record")
    _path(value["path"])
    _flat(value["metadata"])
    if not isinstance(value["body"], str):
        raise SyncFailure("invalid_record")
    if source is not None and (value["metadata"]["source_system"] != source
                               or not value["metadata"]["source_id"]):
        raise SyncFailure("invalid_source")
    return _copy(value)


def validate_bundle(bundle: dict) -> dict:
    """Validate and copy a complete captured source scope without executing it."""
    if (not isinstance(bundle, dict) or type(bundle.get("schema_version")) is not int
            or bundle["schema_version"] != 1 or bundle.get("complete") is not True
            or not isinstance(bundle.get("source_system"), str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]*", bundle["source_system"])
            or not isinstance(bundle.get("scope"), str) or not bundle["scope"]
            or not isinstance(bundle.get("records"), list) or not bundle["records"]):
        raise SyncFailure("invalid_bundle")
    try:
        timestamp = datetime.fromisoformat(bundle["captured_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError
    except (KeyError, AttributeError, TypeError, ValueError):
        raise SyncFailure("invalid_bundle") from None
    records = [_record(value, bundle["source_system"]) for value in bundle["records"]]
    identities = [value["metadata"]["id"] for value in records]
    paths = [value["path"] for value in records]
    _check_path_aliases(paths)
    source_ids = [(value["metadata"]["entity_type"], value["metadata"]["source_id"]) for value in records]
    if len(set(identities)) != len(records) or len(set(paths)) != len(records) or len(set(source_ids)) != len(records):
        raise SyncFailure("invalid_duplicate")
    return {"schema_version": 1, "source_system": bundle["source_system"],
            "scope": bundle["scope"], "captured_at": bundle["captured_at"],
            "complete": True, "records": records}


def merge_record(base: dict, local: dict, remote: dict) -> tuple[dict, list[str]]:
    """Merge each metadata property and the Markdown body independently."""
    base, local, remote = (_record(value) for value in (base, local, remote))
    merged = {"path": base["path"], "metadata": {}, "body": local["body"]}
    conflicts = []
    if base["path"] != local["path"] or base["path"] != remote["path"]:
        conflicts.append("path")
    for key in sorted(set(base["metadata"]) | set(local["metadata"]) | set(remote["metadata"])):
        before, here, incoming = (value["metadata"].get(key, _MISSING) for value in (base, local, remote))
        if key in _IDENTITY and (not _same(here, before) or not _same(incoming, before)):
            conflicts.append(key)
            chosen = here
        elif _same(here, incoming):
            chosen = here
        elif _same(here, before):
            chosen = incoming
        elif _same(incoming, before):
            chosen = here
        else:
            conflicts.append(key)
            chosen = here
        if chosen is not _MISSING:
            merged["metadata"][key] = chosen
    before, here, incoming = (value["body"] for value in (base, local, remote))
    if here == incoming or incoming == before:
        merged["body"] = here
    elif here == before:
        merged["body"] = incoming
    else:
        conflicts.append("body")
    return merged, conflicts


def _safe_path(vault: Path, name: str) -> Path:
    path = vault / _path(name)
    current = vault
    if vault.is_symlink() or not vault.is_dir():
        raise SyncFailure("unsafe_vault")
    for part in PurePosixPath(name).parts:
        current = current / part
        if current.is_symlink():
            raise SyncFailure("unsafe_path")
    if not path.resolve().is_relative_to(vault.resolve()):
        raise SyncFailure("unsafe_path")
    return path


def _scan(vault: Path) -> dict[str, bytes]:
    files = {}
    for name in ("Records", "Knowledge"):
        root = vault / name
        if root.is_symlink() or not root.is_dir():
            raise SyncFailure("unsafe_vault")
        def failed(_error):
            raise SyncFailure("unreadable_vault")
        for directory, dirs, names in os.walk(root, followlinks=False, onerror=failed):
            for child in [*dirs, *names]:
                if (Path(directory) / child).is_symlink():
                    raise SyncFailure("unsafe_path")
            for filename in names:
                path = Path(directory) / filename
                if path.suffix == ".md":
                    relative = path.relative_to(vault).as_posix()
                    files[relative] = _safe_path(vault, relative).read_bytes()
    _check_path_aliases(files)
    return files


@dataclass(frozen=True)
class Plan:
    """Read-only reconciliation result; source contents are hidden from repr."""

    vault_digest: str
    baseline_digest: str
    writes: dict[str, dict] = field(repr=False)
    before: dict[str, bytes | None] = field(repr=False)
    conflicts: list[dict]
    retained: list[str]
    baseline: dict = field(repr=False)
    files: dict[str, bytes] = field(repr=False)

    def summary(self) -> dict:
        return {"written": len(self.writes), "retained": len(self.retained),
                "conflicts": len(self.conflicts), "records": len(self.baseline["records"])}


def plan_sync(vault: Path, bundle: dict, baseline: dict | None, reader: Reader) -> Plan:
    """Plan a complete scope pull against its previous remote representation."""
    vault = Path(vault)
    incoming = validate_bundle(bundle)
    original = validate_bundle(baseline) if baseline is not None else None
    if original is not None and any(incoming[key] != original[key] for key in ("source_system", "scope")):
        raise SyncFailure("source_mismatch")
    files = _scan(vault)
    _check_path_aliases([*files, *(value["path"] for value in incoming["records"])])
    local_by_id = {}
    local_by_path = {}
    for path, data in files.items():
        try:
            parsed = reader(data)
            value = _record({"path": path, "metadata": parsed["metadata"], "body": parsed["body"]})
        except Exception:
            raise SyncFailure("invalid_local_record") from None
        identity = value["metadata"]["id"]
        if identity in local_by_id:
            raise SyncFailure("invalid_local_duplicate")
        local_by_id[identity] = value
        local_by_path[path] = value
    bases = {value["metadata"]["id"]: value for value in original["records"]} if original else {}
    remotes = {value["metadata"]["id"]: value for value in incoming["records"]}
    writes, before, conflicts, retained = {}, {}, [], []
    for identity, base in bases.items():
        local = local_by_id.get(identity)
        if local is None:
            conflicts.append({"path": base["path"], "key": "id", "reason": "local_deleted"})
        elif local["path"] != base["path"]:
            conflicts.append({"path": base["path"], "key": "path", "reason": "identity_reassigned"})
        if identity not in remotes:
            retained.append(base["path"])
            if local is not None:
                for key in _IDENTITY:
                    if not _same(local["metadata"].get(key, _MISSING), base["metadata"].get(key, _MISSING)):
                        conflicts.append({"path": base["path"], "key": key, "reason": "identity_reassigned"})
    for identity, remote in remotes.items():
        path = remote["path"]
        _safe_path(vault, path)
        base = bases.get(identity)
        local = local_by_id.get(identity)
        if base is None:
            if local is not None or path in files or (vault / path).exists():
                conflicts.append({"path": path, "key": "id", "reason": "first_pull_collision"})
                continue
            merged = remote
        elif local is None:
            continue
        else:
            merged, keys = merge_record(base, local, remote)
            if keys:
                conflicts.extend({"path": path, "key": key, "reason": "concurrent_change"} for key in keys)
                continue
            occupant = local_by_path.get(path)
            if occupant is not None and occupant["metadata"]["id"] != identity:
                conflicts.append({"path": path, "key": "path", "reason": "path_collision"})
                continue
        if local is None or _json_bytes(local) != _json_bytes(merged):
            writes[path] = merged
            before[path] = files.get(path)
    accepted = dict(bases)
    accepted.update(remotes)
    next_baseline = {**incoming, "records": sorted(accepted.values(), key=lambda value: value["path"])}
    return Plan(_digest(str(vault.resolve())), _digest(original), writes, before, conflicts,
                sorted(retained), next_baseline, files)


def _private(path: Path) -> None:
    if path.is_symlink():
        raise SyncFailure("unsafe_state")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as handle:
            os.chmod(temporary, 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _read_baseline(path: Path) -> tuple[dict | None, bytes | None]:
    if path.is_symlink():
        raise SyncFailure("unsafe_state")
    if not path.exists():
        return None, None
    try:
        data = path.read_bytes()
        return validate_bundle(json.loads(data)), data
    except (OSError, ValueError, TypeError):
        raise SyncFailure("invalid_baseline") from None


@contextlib.contextmanager
def _lock(path: Path) -> Iterator[None]:
    _private(path.parent)
    if path.is_symlink():
        raise SyncFailure("unsafe_state")
    with path.open("a") as handle:
        os.chmod(path, 0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SyncFailure("busy") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _encoded(data: bytes | None) -> str | None:
    return base64.b64encode(data).decode("ascii") if data is not None else None


def _decoded(value: object) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SyncFailure("invalid_journal")
    try:
        return base64.b64decode(value, validate=True)
    except ValueError:
        raise SyncFailure("invalid_journal") from None


def _journal_path(state_root: Path) -> Path:
    return state_root / "sync-journal.json"


def _journal(state_root: Path) -> dict | None:
    path = _journal_path(state_root)
    if path.is_symlink():
        raise SyncFailure("unsafe_state")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_bytes())
        if (not isinstance(data, dict) or data.get("schema_version") != 1
                or data.get("status") not in {"prepared", "accepted"}):
            raise ValueError
        return data
    except (OSError, ValueError, TypeError):
        raise SyncFailure("invalid_journal") from None


def _state_paths(vault: Path, baseline_path: Path, state_root: Path) -> None:
    if (state_root.resolve().is_relative_to(vault.resolve())
            or baseline_path.resolve().is_relative_to(vault.resolve())
            or vault.resolve().is_relative_to(state_root.resolve())):
        raise SyncFailure("unsafe_state")
    _private(state_root)
    _private(baseline_path.parent)
    if baseline_path.is_symlink():
        raise SyncFailure("unsafe_state")


def seed_baseline(bundle: dict, baseline_path: Path) -> dict:
    """Explicitly seed the original remote representation, never current notes."""
    accepted = validate_bundle(bundle)
    baseline_path = Path(baseline_path)
    _private(baseline_path.parent)
    temporary = baseline_path.with_name(baseline_path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        _atomic_bytes(temporary, _json_bytes(accepted))
        os.link(temporary, baseline_path)
        directory = os.open(baseline_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except FileExistsError:
        raise SyncFailure("baseline_exists") from None
    finally:
        temporary.unlink(missing_ok=True)
    return {"seeded": True, "records": len(accepted["records"])}


def apply_sync(vault: Path, plan: Plan, baseline_path: Path, state_root: Path,
               renderer: Renderer, validator: Validator) -> dict:
    """Validate a complete staged vault, then journal and apply the entire batch."""
    vault, baseline_path, state_root = map(Path, (vault, baseline_path, state_root))
    if plan.conflicts:
        raise SyncFailure("conflicts")
    if _digest(str(vault.resolve())) != plan.vault_digest:
        raise SyncFailure("stale_plan")
    _state_paths(vault, baseline_path, state_root)
    with _lock(state_root / "importer.lock"), _lock(state_root / "publisher.lock"):
        pending = _journal(state_root)
        if pending is not None and pending["status"] == "prepared":
            raise SyncFailure("pending_recovery")
        baseline, baseline_bytes = _read_baseline(baseline_path)
        if _digest(baseline) != plan.baseline_digest:
            raise SyncFailure("stale_baseline")
        if _scan(vault) != plan.files:
            raise SyncFailure("stale_plan")
        accepted = validate_bundle(plan.baseline)
        rendered = {}
        for path, record in plan.writes.items():
            if path != record["path"] or plan.before.get(path) != plan.files.get(path):
                raise SyncFailure("invalid_plan")
            _record(record, accepted["source_system"])
            value = renderer(record)
            if not isinstance(value, bytes):
                raise SyncFailure("invalid_render")
            rendered[path] = value
        with tempfile.TemporaryDirectory(prefix="obsidian-sync-", dir=state_root) as directory:
            stage = Path(directory)
            for name in ("Records", "Knowledge"):
                (stage / name).mkdir()
            expected_files = {**plan.files, **rendered}
            for path, data in expected_files.items():
                target = stage / _path(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if _scan(stage) != expected_files:
                raise SyncFailure("invalid_stage")
            try:
                findings = validator(stage)
                if findings:
                    raise SyncFailure("validation_failed")
            except Exception:
                raise SyncFailure("validation_failed") from None
            if _scan(stage) != expected_files:
                raise SyncFailure("invalid_stage")
        if _scan(vault) != plan.files:
            raise SyncFailure("stale_plan")
        if _read_baseline(baseline_path)[1] != baseline_bytes:
            raise SyncFailure("stale_baseline")
        new_baseline = _json_bytes(accepted)
        if baseline_bytes is not None:
            _atomic_bytes(baseline_path.with_name(baseline_path.name + ".previous"), baseline_bytes)
        journal = {
            "schema_version": 1, "status": "prepared", "vault_digest": plan.vault_digest,
            "baseline_path_digest": _digest(str(baseline_path.resolve())),
            "baseline_old": _encoded(baseline_bytes), "baseline_new": _encoded(new_baseline),
            "files": {path: hashlib.sha256(data).hexdigest() for path, data in plan.files.items()},
            "writes": [{"path": path, "old": _encoded(plan.before[path]), "new": _encoded(data)}
                       for path, data in sorted(rendered.items())],
        }
        _atomic_bytes(_journal_path(state_root), _json_bytes(journal))
        return _finish(vault, baseline_path, state_root, journal, recovered=False)


def _finish(vault: Path, baseline_path: Path, state_root: Path, journal: dict,
            *, recovered: bool) -> dict:
    if (journal.get("vault_digest") != _digest(str(vault.resolve()))
            or journal.get("baseline_path_digest") != _digest(str(baseline_path.resolve()))):
        raise SyncFailure("invalid_journal")
    try:
        writes = journal["writes"]
        files = journal["files"]
        if not isinstance(writes, list) or not isinstance(files, dict):
            raise SyncFailure("invalid_journal")
        decoded = {}
        for entry in writes:
            path = _path(entry["path"])
            if path in decoded:
                raise SyncFailure("invalid_journal")
            old, new = _decoded(entry["old"]), _decoded(entry["new"])
            if new is None:
                raise SyncFailure("invalid_journal")
            decoded[path] = (old, new)
        for path, digest in files.items():
            _path(path)
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise SyncFailure("invalid_journal")
        _check_path_aliases([*files, *decoded])
        for path, (old, _new) in decoded.items():
            if ((old is None and path in files)
                    or (old is not None and hashlib.sha256(old).hexdigest() != files.get(path))):
                raise SyncFailure("invalid_journal")
        baseline_old, baseline_new = _decoded(journal["baseline_old"]), _decoded(journal["baseline_new"])
        accepted = validate_bundle(json.loads(baseline_new))
        if baseline_old is not None:
            previous = validate_bundle(json.loads(baseline_old))
            if any(previous[key] != accepted[key] for key in ("source_system", "scope")):
                raise SyncFailure("invalid_journal")
    except (KeyError, TypeError, ValueError):
        raise SyncFailure("invalid_journal") from None
    live = _scan(vault)
    if set(live) != set(files) | {path for path in decoded if path in live}:
        raise SyncFailure("recovery_conflict")
    for path, digest in files.items():
        if path not in decoded and (path not in live or hashlib.sha256(live[path]).hexdigest() != digest):
            raise SyncFailure("recovery_conflict")
    for path, (old, new) in decoded.items():
        _safe_path(vault, path)
        if live.get(path) not in (old, new):
            raise SyncFailure("recovery_conflict")
    current_baseline = _read_baseline(baseline_path)[1]
    if current_baseline not in (baseline_old, baseline_new):
        raise SyncFailure("recovery_conflict")
    for path, (old, new) in decoded.items():
        target = _safe_path(vault, path)
        current = target.read_bytes() if target.exists() else None
        if current not in (old, new):
            raise SyncFailure("recovery_conflict")
        if current != new:
            _atomic_bytes(target, new)
    final = _scan(vault)
    expected = {**live, **{path: new for path, (_, new) in decoded.items()}}
    if final != expected or _read_baseline(baseline_path)[1] not in (baseline_old, baseline_new):
        raise SyncFailure("recovery_conflict")
    _atomic_bytes(baseline_path, baseline_new)
    journal["status"] = "accepted"
    _atomic_bytes(_journal_path(state_root), _json_bytes(journal))
    return {"written": len(decoded), "records": len(accepted["records"]), "recovered": recovered}


def recover(vault: Path, baseline_path: Path, state_root: Path) -> dict:
    """Finish a pending journal only while every live byte still matches it."""
    vault, baseline_path, state_root = map(Path, (vault, baseline_path, state_root))
    _state_paths(vault, baseline_path, state_root)
    with _lock(state_root / "importer.lock"), _lock(state_root / "publisher.lock"):
        journal = _journal(state_root)
        if journal is None or journal["status"] == "accepted":
            return {"recovered": False, "written": 0}
        return _finish(vault, baseline_path, state_root, journal, recovered=True)
