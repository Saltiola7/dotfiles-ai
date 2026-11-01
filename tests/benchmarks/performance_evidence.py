"""Closed, bounded evidence for explicitly invoked synthetic benchmarks.

Validation establishes shape and internal consistency. It does not authenticate
serialized source identities, cohort claims, host identity or provenance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from typing import TypedDict, cast


MAX_FILES = 32
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_CELLS = 256
MAX_ATTEMPTS = 10_000
MAX_METRICS = 32
STATUSES = frozenset({
    "measured", "partial", "failed", "unavailable", "timed_out", "cancelled",
    "not_attempted",
})
QUALIFIED = frozenset({"measured", "partial"})
TOKEN = re.compile(r"[a-z][a-z0-9_]{0,63}")
VALUE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}")
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")

Number = int | float


class EvidenceError(ValueError):
    """A path-free failure of the benchmark evidence contract."""


def _check_deadline(deadline: float | None) -> None:
    if deadline is None:
        return
    if type(deadline) not in {int, float} or type(deadline) is float and not math.isfinite(deadline):
        raise EvidenceError("invalid_analysis_deadline")
    if time.monotonic() >= deadline:
        raise EvidenceError("analysis_budget_exhausted")


class SourceIdentity(TypedDict):
    commit: str
    tree: str
    tool_commit: str
    lock_sha256: str
    workload_sha256: str
    clean: bool


class EnvironmentIdentity(TypedDict):
    python: str
    python_sha256: str
    git_version: str
    git_sha256: str
    os: str
    os_version: str
    architecture: str
    cpu_count: int
    execution_cohort: str


class MetricDescriptor(TypedDict):
    unit: str
    scope: str
    required: bool


class Cell(TypedDict):
    surface: str
    workload: str
    dimensions: dict[str, int | str]
    fixture_sha256: str
    instrumentation: str
    cache: str
    metrics: dict[str, MetricDescriptor]


class Attempt(TypedDict):
    sequence: int
    warmup: bool
    status: str
    reason: str | None
    compatible: bool
    returncode: int | None
    metrics: dict[str, Number | None]
    unavailable: dict[str, str]
    output_sha256: str | None


class MetricSummary(TypedDict):
    n: int
    mean: int | None
    p50: Number | None
    p90: Number | None


class Coverage(TypedDict):
    planned: int
    warmups: int
    attempted: int
    measured: int
    partial: int
    failed: int
    unavailable: int
    timed_out: int
    cancelled: int
    not_attempted: int
    complete: bool


class Record(TypedDict):
    schema_version: int
    source: SourceIdentity
    environment: EnvironmentIdentity
    cell: Cell
    attempts: list[Attempt]
    coverage: Coverage
    summary: dict[str, MetricSummary]


def canonical(value: object) -> bytes:
    """Encode finite JSON deterministically; never include input in errors."""
    try:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        raise EvidenceError("invalid_json_value") from None


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _closed(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise EvidenceError("invalid_fields")
    return cast(dict[str, object], value)


def _matches(value: object, expression: re.Pattern[str]) -> bool:
    return isinstance(value, str) and expression.fullmatch(value) is not None


def _integer(value: object, minimum: int = 0, maximum: int = 2**63 - 1) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _number(value: object) -> bool:
    return ((type(value) is int and value >= 0)
            or (type(value) is float and math.isfinite(value) and value >= 0))


def _source(value: object) -> SourceIdentity:
    item = _closed(value, {
        "commit", "tree", "tool_commit", "lock_sha256", "workload_sha256", "clean",
    })
    if (any(not _matches(item[k], GIT_ID) for k in ("commit", "tree", "tool_commit"))
            or any(not _matches(item[k], SHA256) for k in ("lock_sha256", "workload_sha256"))
            or item["clean"] is not True):
        raise EvidenceError("invalid_source_identity")
    return cast(SourceIdentity, item)


def _environment(value: object) -> EnvironmentIdentity:
    item = _closed(value, {
        "python", "python_sha256", "git_version", "git_sha256", "os", "os_version",
        "architecture", "cpu_count", "execution_cohort",
    })
    version = (re.fullmatch(r"3\.([0-9]{1,2})\.([0-9]{1,5})", item["python"])
               if isinstance(item["python"], str) else None)
    if (not version or int(version[1]) < 12
            or any(not _matches(item[k], SHA256) for k in ("python_sha256", "git_sha256"))
            or not isinstance(item["git_version"], str)
            or re.fullmatch(r"git version [A-Za-z0-9 .()+_-]{1,96}", item["git_version"]) is None
            or any(not _matches(item[k], VALUE_TOKEN) for k in ("os", "os_version", "architecture"))
            or not _integer(item["cpu_count"], 1, 65536)
            or not isinstance(item["execution_cohort"], str)
            or re.fullmatch(r"[0-9a-f]{32}", item["execution_cohort"]) is None):
        raise EvidenceError("invalid_environment_identity")
    return cast(EnvironmentIdentity, item)


def _cell(value: object) -> Cell:
    item = _closed(value, {
        "surface", "workload", "dimensions", "fixture_sha256", "instrumentation",
        "cache", "metrics",
    })
    if (not isinstance(item["surface"], str) or item["surface"] not in {"cli", "ci", "snapshot"}
            or not _matches(item["workload"], TOKEN)
            or not _matches(item["fixture_sha256"], SHA256)
            or not _matches(item["instrumentation"], TOKEN)
            or not _matches(item["cache"], TOKEN)):
        raise EvidenceError("invalid_cell_identity")
    dimensions = item["dimensions"]
    if type(dimensions) is not dict or len(dimensions) > 32:
        raise EvidenceError("invalid_dimensions")
    for key, child in dimensions.items():
        if not _matches(key, TOKEN) or not (_integer(child) or _matches(child, VALUE_TOKEN)):
            raise EvidenceError("invalid_dimensions")
    metrics = item["metrics"]
    if type(metrics) is not dict or not 1 <= len(metrics) <= MAX_METRICS:
        raise EvidenceError("invalid_metric_descriptors")
    required = False
    for key, child in metrics.items():
        descriptor = _closed(child, {"unit", "scope", "required"})
        if (not _matches(key, TOKEN) or not isinstance(descriptor["unit"], str)
                or descriptor["unit"] not in {"ns", "bytes", "count"}
                or not _matches(descriptor["scope"], TOKEN)
                or type(descriptor["required"]) is not bool):
            raise EvidenceError("invalid_metric_descriptors")
        required |= descriptor["required"]
    if not required:
        raise EvidenceError("missing_required_metric")
    return cast(Cell, item)


def _attempts(value: object, cell: Cell, *, deadline: float | None = None) -> list[Attempt]:
    _check_deadline(deadline)
    if type(value) is not list or not 1 <= len(value) <= MAX_ATTEMPTS:
        raise EvidenceError("invalid_attempt_population")
    warmup_finished = False
    warmups = 0
    for sequence, child in enumerate(value):
        _check_deadline(deadline)
        item = _closed(child, {
            "sequence", "warmup", "status", "reason", "compatible", "returncode",
            "metrics", "unavailable", "output_sha256",
        })
        if (not _integer(item["sequence"]) or item["sequence"] != sequence
                or type(item["warmup"]) is not bool
                or type(item["compatible"]) is not bool
                or not isinstance(item["status"], str) or item["status"] not in STATUSES
                or item["reason"] is not None and not _matches(item["reason"], TOKEN)
                or item["returncode"] is not None and not _integer(item["returncode"], -(2**31), 2**31 - 1)
                or item["output_sha256"] is not None and not _matches(item["output_sha256"], SHA256)):
            raise EvidenceError("invalid_attempt")
        if item["warmup"]:
            warmups += 1
            if warmup_finished or warmups > 1:
                raise EvidenceError("invalid_warmup_order")
        else:
            warmup_finished = True
        values = item["metrics"]
        missing = item["unavailable"]
        if (type(values) is not dict or set(values) != set(cell["metrics"])
                or type(missing) is not dict
                or any(v is not None and not _number(v) for v in values.values())):
            raise EvidenceError("invalid_attempt_metrics")
        absent = {name for name, metric in values.items() if metric is None}
        if set(missing) != absent or any(not _matches(reason, TOKEN) for reason in missing.values()):
            raise EvidenceError("invalid_unavailable_metrics")
        status = item["status"]
        if status in QUALIFIED:
            if (item["compatible"] is not True or item["returncode"] != 0
                    or item["output_sha256"] is None
                    or status == "measured" and absent
                    or status == "partial" and (not absent or len(absent) == len(values))):
                raise EvidenceError("invalid_qualified_attempt")
        elif item["compatible"] is not False or item["reason"] is None:
            raise EvidenceError("invalid_failed_attempt")
        if status == "not_attempted" and (
                item["returncode"] is not None or item["output_sha256"] is not None
                or len(absent) != len(values)):
            raise EvidenceError("invalid_not_attempted")
    if cell["surface"] in {"cli", "snapshot"} and warmups != 1:
        raise EvidenceError("missing_warmup")
    _check_deadline(deadline)
    return cast(list[Attempt], value)


def summarize(values: Sequence[Number], *, deadline: float | None = None) -> MetricSummary:
    """Nearest-rank percentiles with exact floor mean, excluding no values."""
    _check_deadline(deadline)
    for value in values:
        _check_deadline(deadline)
        if not _number(value):
            raise EvidenceError("invalid_metric_values")
    ordered = sorted(values)
    _check_deadline(deadline)
    count = len(ordered)
    if not count:
        return {"n": 0, "mean": None, "p50": None, "p90": None}
    total = Fraction()
    for value in ordered:
        _check_deadline(deadline)
        total += Fraction(value)
    mean = total / count
    _check_deadline(deadline)
    return {
        "n": count, "mean": mean.numerator // mean.denominator,
        "p50": ordered[(count - 1) // 2], "p90": ordered[(9 * count + 9) // 10 - 1],
    }


def _derived(
    cell: Cell, attempts: list[Attempt], planned: object, *, deadline: float | None = None,
) -> tuple[Coverage, dict[str, MetricSummary]]:
    _check_deadline(deadline)
    if not _integer(planned, 1, MAX_ATTEMPTS):
        raise EvidenceError("invalid_planned_population")
    recorded: list[Attempt] = []
    counts = {status: 0 for status in STATUSES}
    required = {name for name, item in cell["metrics"].items() if item["required"]}
    complete = True
    for item in attempts:
        _check_deadline(deadline)
        if not item["warmup"]:
            recorded.append(item)
            counts[item["status"]] += 1
        complete &= (
            item["status"] in QUALIFIED and item["compatible"]
            and all(item["metrics"][name] is not None for name in required)
        )
    if len(recorded) != planned:
        raise EvidenceError("planned_population_mismatch")
    coverage = cast(Coverage, {
        "planned": planned, "warmups": len(attempts) - len(recorded),
        "attempted": len(recorded) - counts["not_attempted"],
        **counts, "complete": complete,
    })
    summary = {}
    for name in cell["metrics"]:
        _check_deadline(deadline)
        values: list[Number] = []
        for item in recorded:
            _check_deadline(deadline)
            value = item["metrics"][name]
            if item["status"] in QUALIFIED and item["compatible"] and value is not None:
                values.append(value)
        summary[name] = summarize(values, deadline=deadline)
    _check_deadline(deadline)
    return coverage, summary


def _parts(
    record: dict[str, object], *, deadline: float | None = None,
) -> tuple[Cell, list[Attempt]]:
    _check_deadline(deadline)
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise EvidenceError("unsupported_schema")
    _source(record["source"])
    _environment(record["environment"])
    cell = _cell(record["cell"])
    return cell, _attempts(record["attempts"], cell, deadline=deadline)


def build_record(
    source: Mapping[str, object], environment: Mapping[str, object],
    cell: Mapping[str, object], attempts: Sequence[Mapping[str, object]], planned: int,
) -> Record:
    """Build a detached record from bounded, validated observations."""
    if not 1 <= len(attempts) <= MAX_ATTEMPTS:
        raise EvidenceError("invalid_attempt_population")
    candidate: dict[str, object] = {
        "schema_version": 1, "source": dict(source), "environment": dict(environment),
        "cell": dict(cell), "attempts": list(attempts),
    }
    selected, rows = _parts(candidate)
    candidate["coverage"], candidate["summary"] = _derived(selected, rows, planned)
    return validate_record(candidate)


def validate_record(record: object, *, deadline: float | None = None) -> Record:
    """Validate closed shape and exact reductions without authenticating input."""
    _check_deadline(deadline)
    candidate = _closed(record, {
        "schema_version", "source", "environment", "cell", "attempts", "coverage", "summary",
    })
    cell, attempts = _parts(candidate, deadline=deadline)
    coverage = candidate["coverage"]
    if type(coverage) is not dict or "planned" not in coverage:
        raise EvidenceError("invalid_coverage")
    expected_coverage, expected_summary = _derived(
        cell, attempts, coverage["planned"], deadline=deadline,
    )
    reductions_match = (
        canonical(coverage) == canonical(expected_coverage)
        and canonical(candidate["summary"]) == canonical(expected_summary)
    )
    _check_deadline(deadline)
    if not reductions_match:
        raise EvidenceError("inconsistent_reductions")
    serialized = canonical(candidate)
    _check_deadline(deadline)
    if len(serialized) + 1 > MAX_FILE_BYTES:
        raise EvidenceError("record_byte_limit")
    _check_deadline(deadline)
    detached = copy.deepcopy(cast(Record, candidate))
    _check_deadline(deadline)
    return detached


def _absolute(path: Path) -> Path:
    if ".." in Path(path).parts:
        raise EvidenceError("unsafe_path")
    return Path(os.path.abspath(path))


def _safe_directory(item: os.stat_result, *, private: bool = False) -> None:
    sticky = item.st_uid == 0 and bool(item.st_mode & stat.S_ISVTX)
    if (not stat.S_ISDIR(item.st_mode) or item.st_uid not in {0, os.getuid()}
            or item.st_mode & 0o022 and not sticky
            or private and (item.st_uid != os.getuid() or item.st_mode & 0o077)):
        raise EvidenceError("unsafe_directory")


def _directory_fd(
    path: Path, *, create: bool = False, private: bool = False,
    deadline: float | None = None,
) -> int:
    """Return an owned descriptor after checking every ancestor without links."""
    _check_deadline(deadline)
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        _safe_directory(os.fstat(descriptor))
        for part in _absolute(path).parts[1:]:
            _check_deadline(deadline)
            try:
                child = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o700, dir_fd=descriptor)
                child = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            try:
                _safe_directory(os.fstat(child))
            except BaseException:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
        _safe_directory(os.fstat(descriptor), private=private)
        _check_deadline(deadline)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def create_private_output(path: Path, source: Path | None = None) -> Path:
    """Create one fresh owner-private output directory outside source."""
    path = _absolute(path)
    if source is not None:
        try:
            selected = Path(source).resolve(strict=True)
            proposed = path.resolve(strict=False)
            if not selected.is_dir():
                raise EvidenceError("invalid_source_scope")
            if proposed.is_relative_to(selected) or selected.is_relative_to(proposed):
                raise EvidenceError("output_aliases_source")
        except (OSError, RuntimeError):
            raise EvidenceError("invalid_source_scope") from None
    parent = None
    child = None
    try:
        parent = _directory_fd(path.parent, create=True)
        os.mkdir(path.name, 0o700, dir_fd=parent)
        child = os.open(
            path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        _safe_directory(os.fstat(child), private=True)
        return path
    except (OSError, ValueError):
        raise EvidenceError("unsafe_output_directory") from None
    finally:
        if child is not None:
            os.close(child)
        if parent is not None:
            os.close(parent)


def write_private_json(directory: Path, name: str, value: object) -> Path:
    """Write a new bounded private JSON file; an existing file is never replaced."""
    if not isinstance(name, str) or re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,127}\.json", name) is None:
        raise EvidenceError("unsafe_output_name")
    raw = canonical(value) + b"\n"
    if len(raw) > MAX_FILE_BYTES:
        raise EvidenceError("record_byte_limit")
    parent = None
    descriptor = None
    try:
        parent = _directory_fd(Path(directory), private=True)
        descriptor = os.open(
            name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600, dir_fd=parent,
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return _absolute(Path(directory)) / name
    except OSError:
        raise EvidenceError("private_write_failed") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)


def _private_file(item: os.stat_result) -> None:
    if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid()
            or item.st_nlink != 1 or item.st_mode & 0o077
            or not item.st_mode & stat.S_IRUSR
            or item.st_size > MAX_FILE_BYTES):
        raise EvidenceError("unsafe_private_record")


def _stamp(item: os.stat_result) -> tuple[int, ...]:
    return (
        item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns,
        item.st_mode, item.st_uid, item.st_nlink,
    )


def _read_private(path: Path, remaining: int, *, deadline: float | None = None) -> bytes:
    parent = None
    descriptor = None
    try:
        _check_deadline(deadline)
        parent = _directory_fd(path.parent, deadline=deadline)
        descriptor = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            dir_fd=parent,
        )
        before = os.fstat(descriptor)
        _private_file(before)
        _check_deadline(deadline)
        if before.st_size > remaining:
            raise EvidenceError("aggregate_byte_limit")
        limit = min(MAX_FILE_BYTES, remaining)
        chunks: list[bytes] = []
        size = 0
        while True:
            _check_deadline(deadline)
            block = os.read(descriptor, min(1024 * 1024, limit + 1 - size))
            _check_deadline(deadline)
            if not block:
                break
            chunks.append(block)
            size += len(block)
            if size > limit:
                raise EvidenceError("record_byte_limit" if limit == MAX_FILE_BYTES else "aggregate_byte_limit")
        if size != before.st_size or _stamp(before) != _stamp(os.fstat(descriptor)):
            raise EvidenceError("record_changed_during_read")
        _check_deadline(deadline)
        return b"".join(chunks)
    except OSError:
        raise EvidenceError("private_read_failed") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)


def _unique_keys(
    pairs: list[tuple[str, object]], *, deadline: float | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _check_deadline(deadline)
        if key in result:
            raise EvidenceError("duplicate_json_key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> object:
    raise EvidenceError("nonfinite_json_number")


def read_records(paths: Sequence[Path], *, deadline: float | None = None) -> list[Record]:
    """Read bounded explicit files, keeping each unauthenticated record separate."""
    _check_deadline(deadline)
    if not 1 <= len(paths) <= min(MAX_FILES, MAX_CELLS):
        raise EvidenceError("record_population_limit")
    records: list[Record] = []
    seen: set[str] = set()
    total = 0
    for supplied in paths:
        _check_deadline(deadline)
        path = _absolute(Path(supplied))
        raw = _read_private(path, MAX_TOTAL_BYTES - total, deadline=deadline)
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise EvidenceError("aggregate_byte_limit")
        try:
            _check_deadline(deadline)
            value = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=lambda pairs: _unique_keys(pairs, deadline=deadline),
                parse_constant=_invalid_constant,
            )
            _check_deadline(deadline)
        except EvidenceError:
            raise
        except (ValueError, UnicodeError, RecursionError):
            raise EvidenceError("invalid_record_json") from None
        record = validate_record(value, deadline=deadline)
        identity = digest(record)
        _check_deadline(deadline)
        if identity in seen:
            raise EvidenceError("duplicate_record")
        seen.add(identity)
        records.append(record)
    _check_deadline(deadline)
    return records
