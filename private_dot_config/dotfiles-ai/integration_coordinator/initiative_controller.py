"""Persist exact Initiative dispatch and reconcile through trusted observation ports."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import AbstractContextManager, closing, contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

from . import core
from .lifecycle import canonical


def _identifier(value: str) -> None:
    core._require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is not None,
                  "initiative_execution_identifier")


@dataclass(frozen=True, slots=True)
class Target:
    origin: str
    repository: str
    target_ref: str

    def __post_init__(self) -> None:
        core._require(isinstance(self.origin, str) and len(self.origin) <= 256
                      and re.fullmatch(r"https://[a-z0-9.-]+(?::[1-9][0-9]{0,4})?", self.origin) is not None,
                      "initiative_execution_origin")
        try:
            port = urlsplit(self.origin).port
        except ValueError:
            raise core.Invalid("initiative_execution_origin") from None
        core._require(port != 443, "initiative_execution_origin")
        core._repository(self.repository)
        core._require(isinstance(self.target_ref, str) and self.target_ref.startswith("refs/heads/"),
                      "initiative_execution_ref")
        core._branch(self.target_ref.removeprefix("refs/heads/"))


@dataclass(frozen=True, slots=True)
class Slice:
    slice_id: str
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.slice_id)
        core._tuple(self.depends_on, str, 256)
        core._require(self.slice_id not in self.depends_on and len(set(self.depends_on)) == len(self.depends_on),
                      "initiative_execution_dependencies")
        for dependency in self.depends_on:
            _identifier(dependency)


@dataclass(frozen=True, slots=True)
class Approval:
    """A trusted port's assessment of an immutable grant and its current authority."""

    grant_id: str
    target: Target
    controller_digest: str
    writer_digest: str
    slices: tuple[Slice, ...]
    mutation_stop: str | None = None

    def __post_init__(self) -> None:
        for value in (self.grant_id, self.controller_digest, self.writer_digest):
            core._digest(value)
        core._require(type(self.target) is Target, "initiative_execution_target")
        core._tuple(self.slices, Slice, 256, minimum=1)
        core._require(len({item.slice_id for item in self.slices}) == len(self.slices),
                      "initiative_execution_slice_duplicates")
        if self.mutation_stop is not None:
            _identifier(self.mutation_stop)


@dataclass(frozen=True, slots=True)
class Launch:
    launch_digest: str
    base_head: str
    checkout: str
    cycle_id: str
    agent: str

    def __post_init__(self) -> None:
        core._digest(self.launch_digest)
        core._oid(self.base_head)
        core._require(isinstance(self.checkout, str) and 0 < len(self.checkout) <= 4096
                      and all(ord(char) >= 32 and ord(char) != 127 for char in self.checkout),
                      "initiative_execution_checkout")
        path = Path(self.checkout)
        core._require(path.is_absolute() and path.as_posix() == self.checkout and ".." not in path.parts,
                      "initiative_execution_checkout")
        _identifier(self.cycle_id)
        _identifier(self.agent)


def _activation_id(grant_id: str, controller_digest: str, writer_digest: str, slice_id: str,
                   target: Target, launch: Launch, managed: bool) -> str:
    return sha256(canonical({
        "kind": "initiative_activation", "schema_version": 1, "grant": grant_id,
        "controller": controller_digest, "writer": writer_digest, "slice": slice_id,
        "target": asdict(target), "launch": asdict(launch),
        **({"managed_registration": True} if managed else {}),
    })).hexdigest()


def _native_id(prefix: str, identifier: str) -> str:
    return prefix + sha256((prefix + identifier).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Activation:
    activation_id: str
    grant_id: str
    writer_digest: str
    controller_digest: str
    slice_id: str
    target: Target
    launch: Launch
    session_id: str
    message_id: str
    managed: bool = False

    def __post_init__(self) -> None:
        for value in (self.grant_id, self.controller_digest, self.writer_digest):
            core._digest(value)
        _identifier(self.slice_id)
        core._require(type(self.target) is Target and type(self.launch) is Launch and type(self.managed) is bool,
                      "initiative_execution_subject")
        identifier = _activation_id(self.grant_id, self.controller_digest, self.writer_digest,
                                    self.slice_id, self.target, self.launch, self.managed)
        core._require((self.activation_id, self.session_id, self.message_id)
                      == (identifier, _native_id("ses_", identifier), _native_id("msg_", identifier)),
                      "initiative_execution_identity")

    @classmethod
    def from_launch(cls, approval: Approval, slice_id: str, launch: Launch, *, managed: bool = False) -> Activation:
        identifier = _activation_id(approval.grant_id, approval.controller_digest, approval.writer_digest,
                                    slice_id, approval.target, launch, managed)
        return cls(identifier, approval.grant_id, approval.writer_digest, approval.controller_digest, slice_id,
                   approval.target, launch, _native_id("ses_", identifier), _native_id("msg_", identifier), managed)


@dataclass(frozen=True, slots=True)
class NativeSession:
    session_id: str
    checkout: str
    agent: str


@dataclass(frozen=True, slots=True)
class NativeDispatch:
    session_id: str
    message_id: str
    activation_id: str


@dataclass(frozen=True, slots=True)
class NativeRelease:
    session_id: str
    message_id: str
    activation_id: str
    delivered: bool


@dataclass(frozen=True, slots=True)
class RegistrationReceipt:
    activation_id: str
    cycle_id: str
    launch_digest: str
    receipt_digest: str

    def __post_init__(self) -> None:
        for value in (self.activation_id, self.launch_digest, self.receipt_digest):
            core._digest(value)
        _identifier(self.cycle_id)


@dataclass(frozen=True, slots=True)
class Admission:
    activation_id: str
    target: Target
    ticket_handle: str
    obligation_handle: str
    receipt_digest: str

    def __post_init__(self) -> None:
        core._digest(self.activation_id)
        core._require(type(self.target) is Target, "initiative_execution_target")
        core._handle(self.ticket_handle)
        core._handle(self.obligation_handle)
        core._digest(self.receipt_digest)


@dataclass(frozen=True, slots=True)
class Delivery:
    """Verified protection and current target inclusion for the original admission."""

    activation_id: str
    target: Target
    ticket_handle: str
    obligation_handle: str
    merge_oid: str
    receipt_digest: str

    def __post_init__(self) -> None:
        core._digest(self.activation_id)
        core._require(type(self.target) is Target, "initiative_execution_target")
        core._handle(self.ticket_handle)
        core._handle(self.obligation_handle)
        core._oid(self.merge_oid)
        core._digest(self.receipt_digest)


class Authority(Protocol):
    def approval(self, grant_id: str) -> Approval: ...
    def preflight(self, approval: Approval, slice_id: str) -> Launch | None:
        """Recheck scope and dependency closure; None means material drift."""
        ...
    def dependency_delivered(self, approval: Approval, slice_id: str) -> bool:
        """Prove current inclusion for an approved dependency outside the selected set."""
        ...


class Writer(Protocol):
    def observe_session(self, activation: Activation) -> NativeSession | None: ...
    def create_session(self, activation: Activation) -> NativeSession: ...
    def observe_dispatch(self, activation: Activation) -> NativeDispatch | None: ...
    def dispatch(self, activation: Activation) -> NativeDispatch: ...


@runtime_checkable
class ManagedWriter(Writer, Protocol):
    def observe_release(self, activation: Activation) -> NativeRelease | None: ...
    def release(self, activation: Activation) -> NativeRelease: ...


class Registration(Protocol):
    def register(self, activation: Activation, controller: InitiativeController) -> None: ...
    def observed(self, activation: Activation) -> RegistrationReceipt | None: ...
    def require_release(self, activation: Activation) -> AbstractContextManager[RegistrationReceipt]:
        """Hold live grant and registration authority through one native release."""
        ...


class Provider(Protocol):
    def observe_admission(self, activation: Activation) -> Admission | None: ...
    def observe_delivery(self, activation: Activation, admission: Admission) -> Delivery | None: ...


@dataclass(frozen=True, slots=True)
class Execution:
    activation: Activation
    state: str
    admission: Admission | None
    delivery: Delivery | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Event:
    state: str
    receipt_digest: str | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Report:
    state: str
    slice_id: str | None = None
    activation_id: str | None = None
    reason: str | None = None


_TRANSITIONS = {
    "reserved": ("session_claimed", "stopped", "superseded"),
    "session_claimed": ("session_ready",),
    "session_ready": ("dispatch_claimed", "stopped"),
    "dispatch_claimed": ("held", "dispatched"),
    "held": ("registration_claimed",),
    "registration_claimed": ("registered",),
    "registered": ("release_claimed",),
    "release_claimed": ("release_accepted",),
    "release_accepted": ("dispatched",),
    "dispatched": ("admitted",),
    "admitted": ("delivered",),
}
_MANAGED_STATES = frozenset({"held", "registration_claimed", "registered", "release_claimed", "release_accepted"})
_TERMINAL = ("delivered", "stopped", "superseded")
_OBSERVATION_ERRORS = (core.Ambiguous, core.Unavailable, core.Conflict, core.Invalid, OSError)


def _target_key(target: Target) -> str:
    return core.identity(Target(target.origin, target.repository.lower(), target.target_ref))


def _load_target(fields: dict[str, str]) -> Target:
    return Target(**fields)


def _load_proof(kind: type[Admission] | type[Delivery], raw: bytes | None) -> Admission | Delivery | None:
    if raw is None:
        return None
    fields = json.loads(raw)
    fields["target"] = _load_target(fields["target"])
    return kind(**fields)


class ExecutionStore:
    """A private, transactionally updated cursor over an append-only dispatch history."""

    def __init__(self, path: Path, *, initialize: bool = True) -> None:
        self.path = Path(path)
        parent = self.path.parent
        core._require(self.path.is_absolute() and self.path == self.path.resolve()
                      and parent.stat().st_uid == os.getuid() and stat.S_IMODE(parent.stat().st_mode) == 0o700,
                      "initiative_execution_private_directory")
        if initialize:
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
            with self._connect(write=True) as database:
                database.executescript("""
                    CREATE TABLE IF NOT EXISTS activation (
                        id TEXT PRIMARY KEY, target TEXT NOT NULL, grant_id TEXT NOT NULL, slice_id TEXT NOT NULL,
                        payload BLOB NOT NULL, state TEXT NOT NULL, admission BLOB, delivery BLOB, reason TEXT
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS active_target ON activation(target)
                    WHERE state NOT IN ('delivered', 'stopped', 'superseded');
                    CREATE UNIQUE INDEX IF NOT EXISTS retained_slice ON activation(grant_id, slice_id)
                    WHERE state != 'superseded';
                    CREATE TABLE IF NOT EXISTS event (
                        seq INTEGER PRIMARY KEY, activation_id TEXT NOT NULL REFERENCES activation(id),
                        state TEXT NOT NULL, receipt_digest TEXT, reason TEXT
                    );
                """)
        else:
            self._check_file()

    def _check_file(self) -> None:
        info = self.path.lstat()
        core._require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                      and stat.S_IMODE(info.st_mode) == 0o600, "initiative_execution_private_file")

    @contextmanager
    def _connect(self, *, write: bool = False) -> Generator[sqlite3.Connection, None, None]:
        self._check_file()
        mode = "rw" if write else "ro"
        with closing(sqlite3.connect(f"{self.path.as_uri()}?mode={mode}", uri=True, timeout=5)) as database:
            database.row_factory = sqlite3.Row
            database.execute("PRAGMA foreign_keys = ON")
            if write:
                database.execute("PRAGMA synchronous = FULL")
                database.execute("BEGIN IMMEDIATE")
            with database:
                yield database

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> Execution | None:
        if row is None:
            return None
        data = json.loads(row["payload"])
        data["target"] = _load_target(data["target"])
        data["launch"] = Launch(**data["launch"])
        activation = Activation(**data)
        state = row["state"]
        reason = row["reason"]
        admission = _load_proof(Admission, row["admission"])
        delivery = _load_proof(Delivery, row["delivery"])
        core._require((row["id"], row["target"], row["grant_id"], row["slice_id"]) == (
            activation.activation_id, _target_key(activation.target), activation.grant_id, activation.slice_id)
            and state in (*_TRANSITIONS, *_TERMINAL)
            and (activation.managed or state not in _MANAGED_STATES)
            and (type(reason) is str) == (state in {"stopped", "superseded"})
            and (type(admission) is Admission) == (state in {"admitted", "delivered"})
            and (type(delivery) is Delivery) == (state == "delivered"), "initiative_execution_record")
        if isinstance(admission, Admission) and not _admission_matches(activation, admission):
            raise core.Invalid("initiative_execution_admission")
        if isinstance(delivery, Delivery) and isinstance(admission, Admission) and not _delivery_matches(admission, delivery):
            raise core.Invalid("initiative_execution_delivery")
        return Execution(activation, state, admission if isinstance(admission, Admission) else None,
                         delivery if isinstance(delivery, Delivery) else None, reason)

    def execution(self, grant_id: str, slice_id: str) -> Execution | None:
        with self._connect() as database:
            row = database.execute("""
                SELECT * FROM activation WHERE grant_id=? AND slice_id=? AND state != 'superseded'
            """, (grant_id, slice_id)).fetchone()
        return self._decode(row)

    def activation(self, activation_id: str) -> Execution | None:
        with self._connect() as database:
            row = database.execute("SELECT * FROM activation WHERE id=?", (activation_id,)).fetchone()
        return self._decode(row)

    def delivered(self, target: Target, slice_id: str) -> tuple[Execution, ...]:
        """Read a bounded set of recent local delivery receipts for prerequisite verification."""
        _identifier(slice_id)
        with self._connect() as database:
            rows = database.execute("""
                SELECT * FROM activation WHERE target=? AND slice_id=? AND state='delivered'
                ORDER BY rowid DESC LIMIT 64
            """, (_target_key(target), slice_id)).fetchall()
        return tuple(execution for row in rows if (execution := self._decode(row)) is not None)

    def active(self, grant_id: str) -> Execution | None:
        with self._connect() as database:
            rows = database.execute("""
                SELECT * FROM activation WHERE grant_id=?
                AND state NOT IN ('delivered', 'stopped', 'superseded') LIMIT 2
            """, (grant_id,)).fetchall()
        core._require(len(rows) <= 1, "initiative_execution_grant_has_multiple_activations")
        return self._decode(rows[0] if rows else None)

    def history(self, activation_id: str) -> tuple[Event, ...]:
        with self._connect() as database:
            rows = database.execute("SELECT state, receipt_digest, reason FROM event WHERE activation_id=? ORDER BY seq",
                                    (activation_id,)).fetchall()
        return tuple(Event(row["state"], row["receipt_digest"], row["reason"]) for row in rows)

    def _reserve(self, activation: Activation) -> bool:
        with self._connect(write=True) as database:
            busy = database.execute("""
                SELECT 1 FROM activation WHERE id=?
                OR (target=? AND state NOT IN ('delivered', 'stopped', 'superseded'))
                OR (grant_id=? AND ((slice_id=? AND state != 'superseded')
                    OR state NOT IN ('delivered', 'stopped', 'superseded')))
            """, (activation.activation_id, _target_key(activation.target),
                  activation.grant_id, activation.slice_id)).fetchone()
            if busy is not None:
                return False
            database.execute("""
                INSERT INTO activation (id, target, grant_id, slice_id, payload, state) VALUES (?, ?, ?, ?, ?, 'reserved')
            """, (activation.activation_id, _target_key(activation.target), activation.grant_id,
                  activation.slice_id, canonical(asdict(activation))))
            database.execute("INSERT INTO event (activation_id, state) VALUES (?, 'reserved')", (activation.activation_id,))
        return True

    def _append(self, execution: Execution, state: str, proof: Admission | Delivery | RegistrationReceipt | None = None, *,
                reason: str | None = None) -> bool:
        core._require(state in _TRANSITIONS.get(execution.state, ())
                      and (execution.activation.managed or state not in _MANAGED_STATES)
                      and (execution.state != "dispatch_claimed"
                           or (state == "held") == execution.activation.managed)
                      and (type(proof) is Admission) == (state == "admitted")
                      and (type(proof) is Delivery) == (state == "delivered")
                      and (type(proof) is RegistrationReceipt) == (state == "registered")
                      and (type(reason) is str) == (state in {"stopped", "superseded"}),
                      "initiative_execution_transition")
        with self._connect(write=True) as database:
            updated = database.execute("""
                UPDATE activation SET state=?, admission=COALESCE(?, admission), delivery=COALESCE(?, delivery), reason=?
                WHERE id=? AND state=?
            """, (state, canonical(asdict(proof)) if isinstance(proof, Admission) else None,
                  canonical(asdict(proof)) if isinstance(proof, Delivery) else None,
                  reason, execution.activation.activation_id, execution.state))
            if updated.rowcount != 1:
                return False
            database.execute("INSERT INTO event (activation_id, state, receipt_digest, reason) VALUES (?, ?, ?, ?)",
                             (execution.activation.activation_id, state,
                              proof.receipt_digest if proof is not None else None, reason))
        return True


def _session_matches(activation: Activation, session: object) -> bool:
    return type(session) is NativeSession and session == NativeSession(
        activation.session_id, activation.launch.checkout, activation.launch.agent)


def _dispatch_matches(activation: Activation, dispatch: object) -> bool:
    return type(dispatch) is NativeDispatch and dispatch == NativeDispatch(
        activation.session_id, activation.message_id, activation.activation_id)


def _release_matches(activation: Activation, release: NativeRelease | None) -> bool:
    return type(release) is NativeRelease and type(release.delivered) is bool and (
        release.session_id, release.message_id, release.activation_id
    ) == (activation.session_id, activation.message_id, activation.activation_id)


def _registration_matches(activation: Activation, receipt: RegistrationReceipt | None) -> bool:
    return type(receipt) is RegistrationReceipt and (receipt.activation_id, receipt.cycle_id, receipt.launch_digest) == (
        activation.activation_id, activation.launch.cycle_id, activation.launch.launch_digest)


def _admission_matches(activation: Activation, admission: Admission) -> bool:
    return type(admission) is Admission and (admission.activation_id, admission.target) == (
        activation.activation_id, activation.target)


def _delivery_matches(admission: Admission, delivery: Delivery) -> bool:
    return type(delivery) is Delivery and (
        delivery.activation_id, delivery.target, delivery.ticket_handle, delivery.obligation_handle
    ) == (admission.activation_id, admission.target, admission.ticket_handle, admission.obligation_handle)


def _report(activation: Activation, state: str, reason: str | None = None) -> Report:
    return Report(state, activation.slice_id, activation.activation_id, reason)


class InitiativeController:
    def __init__(self, store: ExecutionStore, authority: Authority, writer: Writer, provider: Provider, *,
                 registration: Registration | None = None) -> None:
        self.store, self.authority, self.writer, self.provider = store, authority, writer, provider
        self.registration = registration
        self.managed_writer = writer if registration is not None and isinstance(writer, ManagedWriter) else None
        if registration is not None and self.managed_writer is None:
            raise core.Unavailable("initiative_managed_writer_unavailable")

    def _approval(self, grant_id: str) -> Approval:
        approval = self.authority.approval(grant_id)
        if type(approval) is not Approval or approval.grant_id != grant_id:
            raise core.Conflict("initiative_execution_approval_changed")
        return approval

    def _authorize_dependencies(self, activation: Activation) -> Approval:
        approval = self._approval(activation.grant_id)
        if approval.mutation_stop is not None:
            raise core.Unavailable("initiative_execution_authority_stopped")
        item = next((item for item in approval.slices if item.slice_id == activation.slice_id), None)
        if item is None or (approval.target, approval.controller_digest, approval.writer_digest) != (
                activation.target, activation.controller_digest, activation.writer_digest
        ):
            raise core.Conflict("initiative_execution_authority_changed")
        selected = {item.slice_id for item in approval.slices}
        if not all(self._dependency_delivered(approval, selected, dependency) for dependency in item.depends_on):
            raise core.Unavailable("initiative_execution_dependency_unproved")
        return approval

    def _authorize(self, activation: Activation) -> None:
        approval = self._authorize_dependencies(activation)
        launch = self.authority.preflight(approval, activation.slice_id)
        if launch is None:
            raise core.Unavailable("initiative_execution_material_drift")
        if type(launch) is not Launch or activation.launch != launch:
            raise core.Unavailable("initiative_execution_preflight_changed")

    def authorize_begin(self, grant_id: str, activation_id: str, session_id: str, launch_digest: str) -> Activation:
        """Read-only proof that this exact session may begin the reserved slice now."""
        execution = self.store.activation(activation_id)
        if execution is None:
            raise core.Conflict("initiative_execution_begin_unreserved")
        activation = execution.activation
        allowed = {"registration_claimed"} if activation.managed else {"dispatch_claimed", "dispatched"}
        if execution.state not in allowed or activation.managed != (self.registration is not None):
            raise core.Conflict("initiative_execution_begin_unreserved")
        if (grant_id, session_id, launch_digest) != (activation.grant_id, activation.session_id, activation.launch.launch_digest):
            raise core.Conflict("initiative_execution_begin_subject_changed")
        if not _session_matches(activation, self.writer.observe_session(activation)) or not _dispatch_matches(
                activation, self.writer.observe_dispatch(activation)):
            raise core.Unavailable("initiative_execution_begin_dispatch_unproved")
        self._authorize(activation)
        return activation

    def _dependency_delivered(self, approval: Approval, selected: set[str], dependency: str) -> bool:
        if dependency not in selected:
            return self.authority.dependency_delivered(approval, dependency) is True
        previous = self.store.execution(approval.grant_id, dependency)
        if previous is None or previous.delivery is None or previous.admission is None:
            return False
        observed = self.provider.observe_delivery(previous.activation, previous.admission)
        return (observed is not None and _delivery_matches(previous.admission, observed)
                and observed.merge_oid == previous.delivery.merge_oid)

    def _record(self, execution: Execution, state: str, proof: Admission | Delivery | RegistrationReceipt | None = None) -> Report:
        if not self.store._append(execution, state, proof):
            return _report(execution.activation, "uncertain", "execution_changed")
        return _report(execution.activation, state)

    def _mutate(self, execution: Execution) -> Report:
        activation = execution.activation
        session = self.writer.observe_session(activation)
        creating = execution.state == "reserved"
        if creating and session is not None:
            return _report(activation, "uncertain", "unexpected_existing_session")
        if not creating and not _session_matches(activation, session):
            return _report(activation, "uncertain", "native_session_unproved")
        try:
            self._authorize(activation)
        except core.Unavailable as error:
            reason = str(error)
            if reason == "initiative_execution_dependency_unproved":
                return _report(activation, "waiting", reason)
            if reason not in {"initiative_execution_authority_stopped", "initiative_execution_material_drift",
                              "initiative_execution_preflight_changed"}:
                raise
            if creating and reason == "initiative_execution_preflight_changed":
                next_state, result = "superseded", "reprepare"
            elif reason == "initiative_execution_material_drift":
                next_state, result = "stopped", "discovery_reopened"
            else:
                next_state, result = "stopped", "blocked"
            if self.store._append(execution, next_state, reason=reason):
                return _report(activation, result, reason)
            return _report(activation, "uncertain", "execution_changed")
        claimed_state = "session_claimed" if creating else "dispatch_claimed"
        if not self.store._append(execution, claimed_state):
            return _report(activation, "uncertain", "execution_changed")
        claimed = Execution(activation, claimed_state, None, None)
        self._authorize(activation)
        if creating:
            if _session_matches(activation, self.writer.create_session(activation)):
                return self._record(claimed, "session_ready")
        elif _dispatch_matches(activation, self.writer.dispatch(activation)):
            return self._record(claimed, "held" if activation.managed else "dispatched")
        return _report(activation, "uncertain", "native_response_unproved")

    def _managed_registration(self, execution: Execution, registrar: Registration) -> Report:
        activation = execution.activation
        if not _dispatch_matches(activation, self.writer.observe_dispatch(activation)):
            raise core.Unavailable("initiative_managed_prompt_not_parked")
        if execution.state == "held":
            self._authorize(activation)
            if not self.store._append(execution, "registration_claimed"):
                return _report(activation, "uncertain", "execution_changed")
            execution = Execution(activation, "registration_claimed", None, None)
            registrar.register(activation, self)
        receipt = registrar.observed(activation)
        if not _registration_matches(activation, receipt) or not _dispatch_matches(
                activation, self.writer.observe_dispatch(activation)):
            raise core.Unavailable("initiative_managed_registration_unproved")
        return self._record(execution, "registered", receipt)

    def _managed_release(self, execution: Execution, registrar: Registration, writer: ManagedWriter) -> Report:
        activation = execution.activation
        if execution.state == "registered":
            events = self.store.history(activation.activation_id)
            with registrar.require_release(activation) as receipt:
                self._authorize_dependencies(activation)
                if (not _registration_matches(activation, receipt) or not events
                        or events[-1] != Event("registered", receipt.receipt_digest)
                        or not _dispatch_matches(activation, writer.observe_dispatch(activation))):
                    raise core.Unavailable("initiative_managed_release_unproved")
                if not self.store._append(execution, "release_claimed"):
                    return _report(activation, "uncertain", "execution_changed")
                execution = Execution(activation, "release_claimed", None, None)
                observed = writer.release(activation)
        else:
            observed = writer.observe_release(activation)
        if observed is None or not _release_matches(activation, observed):
            raise core.Unavailable("initiative_managed_release_unproved")
        if execution.state == "release_claimed":
            return self._record(execution, "release_accepted")
        if observed.delivered:
            return self._record(execution, "dispatched")
        return _report(activation, "release_accepted")

    def _advance_active(self, execution: Execution) -> Report:
        activation, state = execution.activation, execution.state
        if activation.managed != (self.registration is not None):
            return _report(activation, "uncertain", "initiative_execution_mode_changed")
        try:
            if state in {"reserved", "session_ready"}:
                return self._mutate(execution)
            if state == "session_claimed":
                if _session_matches(activation, self.writer.observe_session(activation)):
                    return self._record(execution, "session_ready")
            elif state == "dispatch_claimed":
                if _dispatch_matches(activation, self.writer.observe_dispatch(activation)):
                    return self._record(execution, "held" if activation.managed else "dispatched")
            elif self.registration is not None and state in {"held", "registration_claimed"}:
                return self._managed_registration(execution, self.registration)
            elif self.registration is not None and self.managed_writer is not None and state in _MANAGED_STATES:
                return self._managed_release(execution, self.registration, self.managed_writer)
            elif state == "dispatched":
                admission = self.provider.observe_admission(activation)
                if admission is None:
                    return _report(activation, state)
                if _admission_matches(activation, admission):
                    return self._record(execution, "admitted", admission)
            elif state == "admitted" and execution.admission is not None:
                delivery = self.provider.observe_delivery(activation, execution.admission)
                if delivery is None:
                    return _report(activation, state)
                if _delivery_matches(execution.admission, delivery):
                    return self._record(execution, "delivered", delivery)
        except _OBSERVATION_ERRORS:
            pass
        return _report(activation, "uncertain", "native_observation_unproved")

    def advance(self, grant_id: str) -> Report:
        """Reconcile or make one native mutation for an approved Initiative."""
        core._digest(grant_id)
        existing = self.store.active(grant_id)
        if existing is not None:
            return self._advance_active(existing)
        try:
            approval = self._approval(grant_id)
            if approval.mutation_stop is not None:
                return Report("blocked", reason=approval.mutation_stop)
            selected = {item.slice_id for item in approval.slices}
            all_delivered = True
            stopped: Report | None = None
            for item in approval.slices:
                previous = self.store.execution(grant_id, item.slice_id)
                if previous is not None:
                    all_delivered &= previous.state == "delivered"
                    if previous.reason is not None and stopped is None:
                        stopped = _report(
                            previous.activation,
                            "discovery_reopened" if previous.reason == "initiative_execution_material_drift" else "blocked",
                            previous.reason,
                        )
                    continue
                all_delivered = False
                if not all(self._dependency_delivered(approval, selected, dependency) for dependency in item.depends_on):
                    continue
                launch = self.authority.preflight(approval, item.slice_id)
                if launch is None:
                    stopped = stopped or Report("discovery_reopened", item.slice_id,
                                                reason="initiative_execution_material_drift")
                    continue
                activation = Activation.from_launch(approval, item.slice_id, launch, managed=self.registration is not None)
                if not self.store._reserve(activation):
                    return _report(activation, "target_busy", "execution_slot_owned")
                return self._advance_active(Execution(activation, "reserved", None, None))
        except _OBSERVATION_ERRORS:
            return Report("blocked", reason="initiative_execution_authority_unavailable")
        return stopped or Report("complete" if all_delivered else "waiting")
