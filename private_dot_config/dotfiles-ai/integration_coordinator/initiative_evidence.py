"""Keep Initiative diagnostics and one repair reservation in the existing journal."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from sqlite3 import Connection
from typing import TYPE_CHECKING

from . import core, initiative_ci as ci, initiative_controller as controller
from .lifecycle import canonical

if TYPE_CHECKING:
    from .initiative_repair import Request


@dataclass(frozen=True, slots=True)
class View:
    executions: dict[str, controller.Execution]
    reports: dict[str, controller.Report]
    telemetry: dict[str, ci.Telemetry]
    verified_dependencies: frozenset[str]
    repair_used: int


@dataclass(frozen=True, slots=True)
class Reservation:
    request: Request
    state: str


class Evidence:
    def __init__(self, journal: controller.ExecutionStore) -> None:
        self.journal = journal

    def initialize(self) -> None:
        """Add the evidence tables during write-side Resume. Status never migrates."""
        with self.journal._connect(write=True) as database:
            database.execute("""
                CREATE TABLE IF NOT EXISTS initiative_progress (
                    grant_id TEXT NOT NULL, slice_id TEXT NOT NULL,
                    activation_id TEXT, state TEXT NOT NULL, reason TEXT,
                    PRIMARY KEY (grant_id, slice_id)
                )
            """)
            database.execute("""
                CREATE TABLE IF NOT EXISTS initiative_ci (
                    activation_id TEXT PRIMARY KEY REFERENCES activation(id), payload BLOB NOT NULL
                )
            """)
            database.execute("""
                CREATE TABLE IF NOT EXISTS initiative_dependency (
                    grant_id TEXT NOT NULL, slice_id TEXT NOT NULL, proved INTEGER NOT NULL,
                    PRIMARY KEY (grant_id, slice_id)
                )
            """)
            database.execute("""
                CREATE TABLE IF NOT EXISTS initiative_repair (
                    grant_id TEXT PRIMARY KEY,
                    activation_id TEXT NOT NULL REFERENCES activation(id), request BLOB NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('reserved', 'claimed', 'settled')),
                    outcome BLOB
                )
            """)

    def report(self, grant_id: str, report: controller.Report) -> None:
        with self.journal._connect(write=True) as database:
            if report.slice_id is not None:
                database.execute("DELETE FROM initiative_progress WHERE grant_id=? AND slice_id=''", (grant_id,))
            activation_id = None if report.state == "target_busy" else report.activation_id
            database.execute("""
                INSERT INTO initiative_progress (grant_id, slice_id, activation_id, state, reason)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(grant_id, slice_id) DO UPDATE SET
                activation_id=excluded.activation_id, state=excluded.state, reason=excluded.reason
            """, (grant_id, report.slice_id or "", activation_id, report.state, report.reason))

    def dependency(self, grant_id: str, slice_id: str, proved: bool) -> bool:
        with self.journal._connect(write=True) as database:
            database.execute("""
                INSERT INTO initiative_dependency VALUES (?, ?, ?) ON CONFLICT(grant_id, slice_id)
                DO UPDATE SET proved=excluded.proved
            """, (grant_id, slice_id, proved))
        return proved

    @staticmethod
    def _ci(database: Connection, activation_id: str) -> ci.Telemetry | None:
        row = database.execute("SELECT payload FROM initiative_ci WHERE activation_id=?", (activation_id,)).fetchone()
        return None if row is None else ci.Telemetry.load(row["payload"])

    def telemetry(self, activation_id: str) -> ci.Telemetry | None:
        with self.journal._connect() as database:
            return self._ci(database, activation_id)

    def observe(self, activation: controller.Activation, previous: ci.Telemetry | None,
                observed: ci.Telemetry) -> ci.Telemetry:
        with self.journal._connect(write=True) as database:
            current = self._ci(database, activation.activation_id)
            if current != previous and current is not None:
                return current
            database.execute("""
                INSERT INTO initiative_ci VALUES (?, ?) ON CONFLICT(activation_id)
                DO UPDATE SET payload=excluded.payload
            """, (activation.activation_id, canonical(asdict(observed))))
        return observed

    def snapshot(self, grant_id: str) -> View:
        core._digest(grant_id)
        with self.journal._connect() as database:
            database.execute("BEGIN")
            tables = {row["name"] for row in database.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
            executions = {
                execution.activation.slice_id: execution for row in database.execute(
                    "SELECT * FROM activation WHERE grant_id=? AND state <> 'superseded'", (grant_id,))
                if (execution := self.journal._decode(row)) is not None
            }
            reports = {}
            if "initiative_progress" in tables:
                for row in database.execute("SELECT * FROM initiative_progress WHERE grant_id=?", (grant_id,)):
                    identifier = row["slice_id"]
                    execution = executions.get(identifier)
                    if row["activation_id"] is None or (
                            execution is not None and execution.activation.activation_id == row["activation_id"]):
                        reports[identifier] = controller.Report(row["state"], identifier or None,
                                                                row["activation_id"], row["reason"])
            telemetry = {}
            if "initiative_ci" in tables:
                telemetry = {key: value for key, execution in executions.items()
                             if (value := self._ci(database, execution.activation.activation_id)) is not None}
            dependencies = frozenset()
            if "initiative_dependency" in tables:
                dependencies = frozenset(row["slice_id"] for row in database.execute(
                    "SELECT slice_id FROM initiative_dependency WHERE grant_id=? AND proved=1", (grant_id,)))
            used = int("initiative_repair" in tables and database.execute(
                "SELECT 1 FROM initiative_repair WHERE grant_id=?", (grant_id,)).fetchone() is not None)
            return View(executions, reports, telemetry, dependencies, used)

    @staticmethod
    def _reservation(database: Connection, grant_id: str) -> Reservation | None:
        from .initiative_repair import Request

        row = database.execute("SELECT * FROM initiative_repair WHERE grant_id=?", (grant_id,)).fetchone()
        if row is None:
            return None
        request = Request.load(json.loads(row["request"]))
        core._require((request.grant_id, request.activation_id) == (grant_id, row["activation_id"]),
                      "initiative_repair_reservation_changed")
        return Reservation(request, row["state"])

    def reservation(self, grant_id: str) -> Reservation | None:
        with self.journal._connect() as database:
            return self._reservation(database, grant_id)

    def _failed_admission(self, database: Connection, request: Request) -> None:
        execution = self.journal._decode(database.execute(
            "SELECT * FROM activation WHERE id=?", (request.activation_id,)).fetchone())
        telemetry = self._ci(database, request.activation_id)
        if (execution is None or execution.state != "admitted" or execution.admission is None
                or (execution.activation.grant_id, execution.activation.slice_id,
                    execution.admission.obligation_handle, execution.admission.ticket_handle)
                != (request.grant_id, request.slice_id, request.failure.obligation, request.failure.predecessor)
                or telemetry is None or not request.failure.matches(telemetry.observation)):
            raise core.Conflict("initiative_repair_predecessor_changed")

    def reserve(self, request: Request) -> bool:
        with self.journal._connect(write=True) as database:
            retained = self._reservation(database, request.grant_id)
            if retained is not None:
                if retained.request != request:
                    raise core.Conflict("initiative_repair_budget_spent")
                return False
            self._failed_admission(database, request)
            database.execute("INSERT INTO initiative_repair VALUES (?, ?, ?, 'reserved', NULL)",
                             (request.grant_id, request.activation_id, canonical(asdict(request))))
        return True

    def claim(self, request: Request) -> None:
        with self.journal._connect(write=True) as database:
            self._failed_admission(database, request)
            result = database.execute("""
                UPDATE initiative_repair SET state='claimed'
                WHERE grant_id=? AND request=? AND state='reserved'
            """, (request.grant_id, canonical(asdict(request))))
            if result.rowcount != 1:
                raise core.Conflict("initiative_repair_effect_claimed")

    def settle(self, request: Request, outcome: str, *, submitted: bool = True) -> None:
        core._digest(outcome)
        expected = "claimed" if submitted else "reserved"
        with self.journal._connect(write=True) as database:
            result = database.execute("""
                UPDATE initiative_repair SET state='settled', outcome=?
                WHERE grant_id=? AND request=? AND state=?
            """, (outcome, request.grant_id, canonical(asdict(request)), expected))
            if result.rowcount != 1:
                retained = database.execute(
                    "SELECT request, state, outcome FROM initiative_repair WHERE grant_id=?",
                    (request.grant_id,)).fetchone()
                if retained is None or tuple(retained) != (canonical(asdict(request)), "settled", outcome):
                    raise core.Conflict("initiative_repair_outcome_changed")
