"""Retain exact Initiative CI observations and compute bounded read schedules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Literal
from urllib.parse import urlsplit

from . import core as c
from . import runtime as r


State = Literal["missing", "pending", "queued", "running", "unavailable", "stale", "failed", "passed"]
ReadOutcome = Literal["verified", "unavailable", "stale", "untrusted"]

_WAITING = frozenset(("queued", "running"))
_VERIFIED = frozenset(("missing", "pending", "queued", "running", "failed", "passed"))
_UNVERIFIED = {"unavailable": "unavailable", "stale": "stale", "untrusted": "unavailable"}
_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}")


def _time(value: int) -> None:
    c._require(type(value) is int and 0 <= value <= c.MAX_INTEGER, "initiative_ci_time_invalid")


def _optional_time(value: int | None, until: int) -> None:
    if value is not None:
        _time(value)
        c._require(value <= until, "initiative_ci_time_invalid")


def _safe_url(value: str) -> bool:
    if (type(value) is not str or not 1 <= len(value) <= 512 or not value.isascii()
            or any(ord(ch) <= 32 or ord(ch) == 127 for ch in value)
            or any(ch in value for ch in "\\%") or not value.startswith("https://")):
        return False
    try:
        url = urlsplit(value)
        return (url.hostname is not None and url.username is None and url.password is None
                and url.path.startswith("/") and not url.query and not url.fragment
                and not any(part in ("", ".", "..") for part in url.path[1:].split("/")))
    except ValueError:
        return False


@dataclass(frozen=True, slots=True)
class Policy:
    no_progress_seconds: int
    recheck_seconds: int
    max_unavailable_backoff_seconds: int
    retention_seconds: int

    def __post_init__(self) -> None:
        for value in (self.no_progress_seconds, self.recheck_seconds,
                      self.max_unavailable_backoff_seconds, self.retention_seconds):
            c._integer(value)
        c._require(self.recheck_seconds <= self.max_unavailable_backoff_seconds,
                   "initiative_ci_backoff_below_cadence")


@dataclass(frozen=True, slots=True)
class Candidate:
    generation: int
    base: str
    head: str
    tested_oid: str
    digest: str

    def __post_init__(self) -> None:
        c._integer(self.generation)
        for oid in (self.base, self.head, self.tested_oid):
            c._oid(oid)
        c._require(len(self.base) == len(self.head) == len(self.tested_oid),
                   "initiative_ci_candidate_format")
        c._digest(self.digest)

    @classmethod
    def exact(cls, candidate: r.Candidate) -> Candidate:
        c._require(type(candidate) is r.Candidate, "initiative_ci_candidate_unbound")
        return cls(candidate.generation, candidate.base, candidate.head, candidate.tested_oid, c.identity(candidate))


@dataclass(frozen=True, slots=True)
class Observation:
    candidate: Candidate | None
    state: State
    reason: str
    read_at: int
    read_outcome: ReadOutcome = "verified"
    check: str | None = None
    run_id: int | None = None
    attempt: int | None = None
    native_progress_at: int | None = None
    diagnostic_url: str | None = None
    failure_digest: str | None = None
    native_state: str | None = None

    def __post_init__(self) -> None:
        c._require(type(self.candidate) is Candidate or (
            self.candidate is None and self.state == self.read_outcome == "unavailable"
            and all(value is None for value in (self.check, self.run_id, self.attempt, self.native_progress_at,
                                                self.diagnostic_url, self.failure_digest, self.native_state))),
            "initiative_ci_candidate_unbound")
        c._require(type(self.read_outcome) is str and type(self.state) is str
                   and ((self.read_outcome == "verified" and self.state in _VERIFIED)
                        or _UNVERIFIED.get(self.read_outcome) == self.state),
                   "initiative_ci_read_outcome_invalid")
        c._require(type(self.reason) is str and _CODE.fullmatch(self.reason) is not None,
                   "initiative_ci_reason_invalid")
        _time(self.read_at)
        for value in (self.check, self.native_state):
            c._require(value is None or (type(value) is str and 0 < len(value) <= 512 and value.isprintable()),
                       "initiative_ci_check_diagnostic_invalid")
        for value in (self.run_id, self.attempt):
            if value is not None:
                c._integer(value)
        c._require(self.attempt is None or self.run_id is not None, "initiative_ci_attempt_unbound")
        _optional_time(self.native_progress_at, self.read_at)
        c._require(self.native_progress_at is None or self.read_outcome == "verified",
                   "initiative_ci_progress_unverified")
        c._require(self.diagnostic_url is None or _safe_url(self.diagnostic_url),
                   "initiative_ci_diagnostic_url_invalid")
        if self.failure_digest is not None:
            c._digest(self.failure_digest)
            c._require(self.state == "failed" and self.read_outcome == "verified"
                       and self.check is not None and self.attempt is not None,
                       "initiative_ci_failure_unproved")


@dataclass(frozen=True, slots=True)
class Telemetry:
    observation: Observation
    last_success_at: int | None
    last_progress_at: int | None
    progress_since: int | None
    unavailable_reads: int
    next_recheck_at: int

    def __post_init__(self) -> None:
        c._require(type(self.observation) is Observation, "initiative_ci_observation_unbound")
        for value in (self.last_success_at, self.last_progress_at, self.progress_since):
            _optional_time(value, self.observation.read_at)
        _time(self.unavailable_reads)
        _time(self.next_recheck_at)
        c._require(self.next_recheck_at > self.observation.read_at, "initiative_ci_recheck_invalid")
        c._require(self.progress_since is None or self.observation.state in _WAITING,
                   "initiative_ci_progress_unverified")
        c._require((self.unavailable_reads > 0) == (self.observation.read_outcome == "unavailable"),
                   "initiative_ci_unavailable_reads_invalid")
        c._require(self.observation.read_outcome != "verified" or self.last_success_at == self.observation.read_at,
                   "initiative_ci_last_success_invalid")

    def to_record(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls, raw: object) -> Telemetry:
        try:
            if isinstance(raw, (str, bytes)):
                raw = json.loads(raw, object_pairs_hook=_unique)
            if type(raw) is not dict:
                raise c.Invalid("initiative_ci_telemetry_invalid")
            fields = dict(raw)
            observation = dict(fields.pop("observation"))
            subject = observation.pop("candidate")
            candidate = Candidate(**subject) if subject is not None else None
            return cls(Observation(candidate, **observation), **fields)
        except c.Invalid:
            raise
        except (KeyError, TypeError, ValueError):
            raise c.Invalid("initiative_ci_telemetry_invalid") from None


@dataclass(frozen=True, slots=True)
class Stall:
    state: Literal["queued", "running"]
    since: int
    last_progress_at: int | None
    next_recheck_at: int


def _unique(pairs: list[tuple[str, object]]) -> dict:
    value = dict(pairs)
    c._require(len(value) == len(pairs), "initiative_ci_telemetry_duplicate")
    return value


def _key(observation: Observation) -> tuple[State, str | None, int | None, int | None]:
    return observation.state, observation.check, observation.run_id, observation.attempt


def _interval(policy: Policy, failures: int) -> int:
    ceiling = policy.max_unavailable_backoff_seconds
    shift = min(max(failures - 1, 0), ceiling.bit_length())
    return min(policy.recheck_seconds << shift, ceiling)


def advance(previous: Telemetry | None, observation: Observation, policy: Policy) -> Telemetry:
    """Update read and progress times while keeping candidate generations independent."""
    if previous is not None:
        if observation.read_at < previous.observation.read_at:
            raise c.Conflict("initiative_ci_observation_out_of_order")
        if observation == previous.observation:
            return previous
        if previous.observation.candidate != observation.candidate:
            previous = None

    last_success = previous.last_success_at if previous else None
    last_progress = previous.last_progress_at if previous else None
    progress_since = None
    if observation.read_outcome == "verified":
        last_success = observation.read_at
        native = observation.native_progress_at
        prior = previous.observation if previous else None
        same_run = prior is not None and _key(prior) == _key(observation)
        if observation.state in _WAITING:
            if same_run and previous is not None and previous.progress_since is not None:
                progress_since = previous.progress_since
                if native is not None and (last_progress is None or native > last_progress):
                    progress_since = native
            else:
                progress_since = native if native is not None else observation.read_at
        if native is not None and (last_progress is None or native > last_progress):
            last_progress = native

    failures = 0
    if observation.read_outcome == "unavailable":
        failures = 1 + (previous.unavailable_reads if previous else 0)
    interval = _interval(policy, failures)
    return Telemetry(observation, last_success, last_progress, progress_since,
                     failures, observation.read_at + interval)


def unavailable(previous: Telemetry | None, now: int, reason: str) -> Observation:
    """Report a read outage without inventing a candidate or retaining failure authority."""
    candidate = previous.observation.candidate if previous is not None else None
    return Observation(candidate, "unavailable", reason, now, "unavailable")


def due(previous: Telemetry | None, now: int, *, wakeup: bool = False) -> bool:
    _time(now)
    return previous is None or wakeup or now >= previous.next_recheck_at


def stall(telemetry: Telemetry, policy: Policy, now: int) -> Stall | None:
    """Diagnose no progress only from a fresh, exact queued or running observation."""
    _time(now)
    observed, since = telemetry.observation, telemetry.progress_since
    state = observed.state
    if (state in ("queued", "running") and observed.read_outcome == "verified"
            and observed.read_at <= now <= telemetry.next_recheck_at and since is not None
            and observed.read_at - since >= policy.no_progress_seconds):
        return Stall(state, since, telemetry.last_progress_at, telemetry.next_recheck_at)
    return None


def diagnostic_expired(telemetry: Telemetry, policy: Policy, now: int) -> bool:
    """Retention applies to telemetry, independently of failure or delivery custody."""
    _time(now)
    return now - telemetry.observation.read_at >= policy.retention_seconds
