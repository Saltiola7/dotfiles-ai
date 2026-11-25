"""Crash and replay tests for the durable Initiative implementation controller."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sys
from threading import Event

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, initiative_controller as ic


def digest(value: int) -> str:
    return f"{value:064x}"


def oid(value: int) -> str:
    return f"{value:040x}"


class Authority:
    target = ic.Target("https://forge.example", "example/project", "refs/heads/main")

    def __init__(self, worktree: Path) -> None:
        self.worktree = worktree
        self.mutation_stop: str | None = None
        self.drift: set[str] = set()

    def approval(self, grant_id: str) -> ic.Approval:
        slices = (ic.Slice("first"), ic.Slice("next", ("first",)))
        if grant_id == digest(2):
            slices = (ic.Slice("separate"),)
        return ic.Approval(grant_id, self.target, digest(3), digest(4), slices, self.mutation_stop)

    def preflight(self, approval: ic.Approval, slice_id: str) -> ic.Launch | None:
        if slice_id in self.drift:
            return None
        path = self.worktree / slice_id
        return ic.Launch(digest(8 if slice_id == "first" else 9), oid(10), str(path), slice_id, "build")

    def dependency_delivered(self, approval: ic.Approval, slice_id: str) -> bool:
        return False


class Writer:
    def __init__(self, store: ic.ExecutionStore) -> None:
        self.store = store
        self.sessions: dict[str, ic.NativeSession] = {}
        self.messages: dict[str, ic.NativeDispatch] = {}
        self.created: list[ic.Activation] = []
        self.prompted: list[ic.Activation] = []
        self.lost_create = False
        self.lost_dispatch = False
        self.hide_sessions = False
        self.hide_dispatches = False

    def observe_session(self, activation: ic.Activation) -> ic.NativeSession | None:
        return None if self.hide_sessions else self.sessions.get(activation.session_id)

    def create_session(self, activation: ic.Activation) -> ic.NativeSession:
        assert self.store.history(activation.activation_id)[-1].state == "session_claimed"
        assert activation.session_id not in self.sessions
        self.created.append(activation)
        session = ic.NativeSession(activation.session_id, activation.launch.checkout, activation.launch.agent)
        self.sessions[activation.session_id] = session
        if self.lost_create:
            raise core.Ambiguous("fixture_lost_create_reply")
        return session

    def observe_dispatch(self, activation: ic.Activation) -> ic.NativeDispatch | None:
        return None if self.hide_dispatches else self.messages.get(activation.message_id)

    def dispatch(self, activation: ic.Activation) -> ic.NativeDispatch:
        assert self.store.history(activation.activation_id)[-1].state == "dispatch_claimed"
        assert activation.message_id not in self.messages
        self.prompted.append(activation)
        message = ic.NativeDispatch(activation.session_id, activation.message_id, activation.activation_id)
        self.messages[activation.message_id] = message
        if self.lost_dispatch:
            raise core.Ambiguous("fixture_lost_dispatch_reply")
        return message


class Provider:
    def __init__(self) -> None:
        self.admissions: dict[str, ic.Admission] = {}
        self.deliveries: dict[str, ic.Delivery] = {}

    def observe_admission(self, activation: ic.Activation) -> ic.Admission | None:
        return self.admissions.get(activation.activation_id)

    def observe_delivery(self, activation: ic.Activation, admission: ic.Admission) -> ic.Delivery | None:
        return self.deliveries.get(activation.activation_id)

    def admit(self, activation: ic.Activation) -> ic.Admission:
        proof = ic.Admission(activation.activation_id, activation.target, "e" * 32, "f" * 32, digest(12))
        self.admissions[activation.activation_id] = proof
        return proof

    def land(self, admission: ic.Admission) -> ic.Delivery:
        proof = ic.Delivery(admission.activation_id, admission.target, admission.ticket_handle,
                            admission.obligation_handle, oid(14), digest(13))
        self.deliveries[admission.activation_id] = proof
        return proof


@pytest.fixture
def setup(tmp_path: Path) -> tuple[Path, Authority, Writer, Provider, ic.InitiativeController]:
    private = tmp_path / "state"
    private.mkdir(mode=0o700)
    database = private / "controller.sqlite"
    store = ic.ExecutionStore(database)
    authority, writer, provider = Authority(tmp_path), Writer(store), Provider()
    return database, authority, writer, provider, ic.InitiativeController(store, authority, writer, provider)


def test_restarts_reuse_exact_launch_and_wait_for_native_delivery(setup) -> None:
    database, authority, writer, provider, run = setup
    grant = digest(1)
    assert run.advance(grant).state == "session_ready"
    restarted = ic.InitiativeController(ic.ExecutionStore(database), authority, writer, provider)
    assert restarted.advance(grant).state == "dispatched"
    active, = writer.created
    assert writer.prompted == [active]
    assert restarted.authorize_begin(grant, active.activation_id, active.session_id, active.launch.launch_digest) == active
    assert restarted.advance(grant).state == "dispatched"

    admission = provider.admit(active)
    assert restarted.advance(grant).state == "admitted"
    assert restarted.advance(grant).state == "admitted"
    assert writer.created == [active]
    provider.land(admission)
    assert restarted.advance(grant).state == "delivered"

    result = restarted.advance(grant)
    assert result.state == "session_ready" and result.slice_id == "next"
    assert [event.state for event in restarted.store.history(active.activation_id)] == [
        "reserved", "session_claimed", "session_ready", "dispatch_claimed", "dispatched", "admitted", "delivered",
    ]
    assert restarted.store.history(active.activation_id)[-1].receipt_digest == digest(13)
    assert database.stat().st_mode & 0o777 == 0o600


def test_lost_create_and_prompt_only_reconcile_exact_native_ids(setup) -> None:
    database, authority, writer, provider, run = setup
    grant = digest(1)
    writer.lost_create = True
    assert run.advance(grant).state == "uncertain"
    active, = writer.created
    writer.hide_sessions = True
    reopened = ic.InitiativeController(ic.ExecutionStore(database), authority, writer, provider)
    assert reopened.advance(grant).state == "uncertain"
    assert reopened.advance(digest(2)).state == "target_busy"
    assert writer.created == [active] and not writer.prompted
    writer.hide_sessions = False
    assert reopened.advance(grant).state == "session_ready"

    writer.lost_dispatch = True
    assert reopened.advance(grant).state == "uncertain"
    writer.hide_dispatches = True
    assert reopened.advance(grant).state == "uncertain"
    with pytest.raises(core.Unavailable):
        reopened.authorize_begin(grant, active.activation_id, active.session_id, active.launch.launch_digest)
    writer.hide_dispatches = False
    assert reopened.advance(grant).state == "dispatched"
    assert writer.prompted == [active]


def test_revocation_preserves_native_readback_and_prevents_a_new_prompt(setup) -> None:
    _, authority, writer, _, run = setup
    grant = digest(1)
    writer.lost_create = True
    assert run.advance(grant).state == "uncertain"
    authority.mutation_stop = "revoked"
    assert run.advance(grant).state == "session_ready"
    assert run.advance(grant).state == "blocked"
    assert not writer.prompted


def test_material_drift_narrows_to_affected_dependency_branch(setup) -> None:
    _, authority, writer, _, run = setup
    grant = digest(1)
    original = authority.approval
    authority.approval = lambda grant_id: replace(
        original(grant_id), slices=(*original(grant_id).slices, ic.Slice("independent")))
    authority.drift.add("first")
    result = run.advance(grant)
    assert result.state == "session_ready" and result.slice_id == "independent"
    assert [activation.slice_id for activation in writer.created] == ["independent"]


def test_mismatched_native_readback_and_delivery_cannot_release_the_target(setup) -> None:
    _, _, writer, provider, run = setup
    grant = digest(1)
    writer.lost_create = True
    assert run.advance(grant).state == "uncertain"
    active, = writer.created
    exact = writer.sessions[active.session_id]
    writer.sessions[active.session_id] = replace(exact, checkout="/wrong-checkout")
    assert run.advance(grant).state == "uncertain"
    assert not writer.prompted
    writer.sessions[active.session_id] = exact
    assert run.advance(grant).state == "session_ready"
    assert run.advance(grant).state == "dispatched"
    admission = provider.admit(active)
    assert run.advance(grant).state == "admitted"
    delivery = provider.land(admission)
    provider.deliveries[active.activation_id] = replace(delivery, obligation_handle="a" * 32)
    assert run.advance(grant).state == "uncertain"
    assert run.advance(digest(2)).state == "target_busy"


def test_dispatched_worker_begin_requires_exact_reserved_subject_and_fresh_scope(setup) -> None:
    _, authority, writer, _, run = setup
    grant = digest(1)
    run.advance(grant)
    active, = writer.created
    with pytest.raises(core.Conflict):
        run.authorize_begin(grant, active.activation_id, active.session_id, active.launch.launch_digest)
    run.advance(grant)
    for identifier, session, launch in (
        (digest(99), active.session_id, active.launch.launch_digest),
        (active.activation_id, "ses_other", active.launch.launch_digest),
        (active.activation_id, active.session_id, digest(99)),
    ):
        with pytest.raises(core.Conflict):
            run.authorize_begin(grant, identifier, session, launch)
    authority.drift.add("first")
    with pytest.raises(core.Unavailable):
        run.authorize_begin(grant, active.activation_id, active.session_id, active.launch.launch_digest)


def test_two_workers_cannot_dispatch_a_second_write_while_first_call_is_in_flight(setup) -> None:
    database, authority, writer, provider, run = setup
    grant = digest(1)
    started, finish = Event(), Event()
    original = writer.create_session

    def held_create(activation: ic.Activation) -> ic.NativeSession:
        started.set()
        assert finish.wait(5)
        return original(activation)

    writer.create_session = held_create
    competing = ic.InitiativeController(ic.ExecutionStore(database), authority, writer, provider)
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(run.advance, grant)
        try:
            assert started.wait(5)
            assert competing.advance(grant).state == "uncertain"
            assert competing.advance(digest(2)).state == "target_busy"
            assert not writer.created and not writer.prompted
        finally:
            finish.set()
        assert pending.result(timeout=5).state == "session_ready"
    assert len(writer.created) == 1


def test_existing_native_absence_does_not_release_a_crashed_claim(setup) -> None:
    database, authority, writer, provider, run = setup
    grant = digest(1)

    def stop_after_persisting_claim(activation: ic.Activation) -> ic.NativeSession:
        assert run.store.history(activation.activation_id)[-1].state == "session_claimed"
        raise KeyboardInterrupt

    writer.create_session = stop_after_persisting_claim
    with pytest.raises(KeyboardInterrupt):
        run.advance(grant)
    reopened = ic.InitiativeController(ic.ExecutionStore(database), authority, writer, provider)
    assert reopened.advance(grant).state == "uncertain"
    assert reopened.advance(digest(2)).state == "target_busy"
    assert not writer.created and not writer.prompted


def test_advance_reprepares_fresh_base_before_first_native_claim_and_keeps_history(setup) -> None:
    database, authority, writer, provider, run = setup
    grant = digest(1)
    original_preflight = authority.preflight
    count = 0

    def changed_preflight(approval: ic.Approval, slice_id: str) -> ic.Launch:
        nonlocal count
        count += 1
        launch = original_preflight(approval, slice_id)
        assert launch is not None
        return launch if count == 1 else replace(launch, launch_digest=digest(40), base_head=oid(40))

    authority.preflight = changed_preflight
    outdated = run.advance(grant)
    assert outdated.state == "reprepare"
    assert outdated.activation_id is not None
    assert not writer.created and not writer.prompted
    assert [event.state for event in run.store.history(outdated.activation_id)] == ["reserved", "superseded"]

    reopened = ic.InitiativeController(ic.ExecutionStore(database), authority, writer, provider)
    current = reopened.advance(grant)
    assert current.state == "session_ready" and current.slice_id == "first"
    assert current.activation_id != outdated.activation_id
    expired = reopened.store.activation(outdated.activation_id)
    assert expired is not None and expired.state == "superseded" and expired.activation.launch.base_head == oid(10)
    assert writer.created[0].launch.base_head == oid(40)


def test_prerequisite_native_inclusion_must_still_hold_before_dispatch_and_begin(setup) -> None:
    _, _, writer, provider, run = setup
    grant = digest(1)
    assert run.advance(grant).state == "session_ready"
    assert run.advance(grant).state == "dispatched"
    first, = writer.created
    admission = provider.admit(first)
    assert run.advance(grant).state == "admitted"
    delivery = provider.land(admission)
    assert run.advance(grant).state == "delivered"
    assert run.advance(grant).slice_id == "next"
    second = writer.created[1]
    provider.deliveries.clear()
    assert run.advance(grant).state == "waiting"
    assert writer.prompted == [first]
    provider.deliveries[first.activation_id] = delivery
    assert run.advance(grant).state == "dispatched"
    provider.deliveries.clear()
    with pytest.raises(core.Unavailable, match="initiative_execution_dependency_unproved"):
        run.authorize_begin(grant, second.activation_id, second.session_id, second.launch.launch_digest)


def test_repository_name_case_alias_does_not_bypass_target_fence(setup) -> None:
    _, authority, writer, _, run = setup
    assert run.advance(digest(1)).state == "session_ready"
    authority.target = replace(authority.target, repository="Example/Project")
    assert run.advance(digest(2)).state == "target_busy"
    assert len(writer.created) == 1
