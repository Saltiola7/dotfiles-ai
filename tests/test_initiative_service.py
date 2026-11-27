"""The managed service confirms exact private scope and resumes the same journal."""
from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import (
    core, initiative_authority as authority, initiative_ci as ci, initiative_controller as controller,
    initiative_repair as repair, initiative_service as service, lifecycle as l,
)
from test_initiative_managed_registration import HeldWriter, Registration
from test_integration_initiative_authority import APPROVED_AT, EXPIRES, binding, manifest, oid, selected_snapshot
from test_integration_initiative_controller import Provider, Writer


@pytest.fixture
def managed(tmp_path):
    custody = l.Custody(tmp_path)
    custody.directory.mkdir(mode=0o700, parents=True)
    checkout = tmp_path / "authority"
    checkout.mkdir()
    recipe_path = custody.directory / "initiative-runtime.json"
    recipe = {
        "schema_version": 1, "authority_checkout": str(checkout),
        "manifest_path": "docs/initiatives/test-initiative/MANIFEST.json", "github_account": "fixture",
        "writer_agent": "build", "slices": {
            "independent": {"branch": "dbsctr/cycle-1", "cycle_id": "cycle-1", "context": "fixture",
                            "risk": "critical", "plan_path": "docs/initiatives/test-initiative/plan.json",
                            "plan_digest": "7" * 64},
        },
    }
    recipe_path.write_text(json.dumps(recipe))
    recipe_path.chmod(0o600)
    journal = custody.directory / "initiative-execution.sqlite"
    value = {"manifest": manifest(), "binding": binding(), "now": APPROVED_AT}
    provider = Provider()

    def launch(runtime, grant_id, slice_id):
        assert len(grant_id) == 64 and slice_id == "independent"
        return controller.Launch("8" * 64, oid("base"), str(checkout), "cycle-1", "build")

    writer = lambda store: Writer(store)

    def build(writer_factory=writer, *, registration=None, protected_tick=None, ci_reader=None, repair_route=None):
        return service.InitiativeService(
            custody, committed_scope=lambda recipe, selected: selected_snapshot(value["manifest"], selected=selected),
            live_binding=lambda recipe: value["binding"], preflight=launch,
            prior_delivery=lambda recipe, approval, slice_id, scope: False, writer=writer_factory, provider=provider,
            registration=registration, clock=lambda: value["now"], protected_tick=protected_tick,
            ci_reader=ci_reader, repair_route=repair_route,
        )

    return custody, recipe_path, recipe, journal, value, build


def preview(manager, **selection):
    return manager.preview(("independent",), operator_id="operator-1", expires_at=EXPIRES, **selection)


@pytest.mark.parametrize("change", ("mode", "symlink", "secret", "plan_path", "agent", "duplicate_key"))
def test_recipe_is_fixed_private_closed_and_safe(managed, change):
    custody, path, recipe, _, _, _ = managed
    assert service.read_recipe(custody).writer_agent == "build"
    if change == "mode":
        path.chmod(0o644)
    elif change == "symlink":
        other = path.with_suffix(".other")
        path.rename(other)
        path.symlink_to(other)
    elif change == "duplicate_key":
        path.write_text(json.dumps(recipe).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
    else:
        if change == "secret":
            recipe["password"] = "never-store"
        elif change == "plan_path":
            recipe["slices"]["independent"]["plan_path"] = "../outside.json"
        else:
            recipe["writer_agent"] = "plan"
        path.write_text(json.dumps(recipe))
    with pytest.raises((ValueError, OSError)):
        service.read_recipe(custody)


def test_preview_has_no_side_effect_and_exact_confirmation_persists_journal_and_grant(managed):
    custody, _, _, journal, _, build = managed
    manager = build()
    proposal = preview(manager)
    assert proposal.confirmation == "START test-initiative " + proposal.approval_digest
    assert proposal.review["approval_digest"] == proposal.approval_digest
    assert [entry["slice_id"] for entry in proposal.review["slice_plans"]] == ["independent"]
    assert not journal.exists()
    assert not custody.object_path(proposal.grant_digest).exists()
    with pytest.raises(ValueError):
        manager.confirm(proposal, "START test-initiative")
    assert not journal.exists()
    original = custody.write

    def verify_write(kind, value):
        assert journal.exists() and journal.stat().st_mode & 0o777 == 0o600
        return original(kind, value)

    custody.write = verify_write
    assert manager.confirm(proposal, proposal.confirmation) == proposal.grant_digest
    assert manager.confirm(proposal, proposal.confirmation) == proposal.grant_digest
    assert custody.object_path(proposal.grant_digest).exists()


@pytest.mark.parametrize("change", ("native", "material", "recipe", "expired"))
def test_confirm_rechecks_same_plan_binding_and_time_before_writes(managed, change):
    _, path, recipe, journal, value, build = managed
    manager = build()
    proposal = preview(manager)
    if change == "native":
        value["binding"]["qualification_digest"] = "0" * 64
    elif change == "material":
        value["manifest"]["statements"][-1]["text"] += " changed scope"
    elif change == "recipe":
        recipe["slices"]["independent"]["plan_digest"] = "0" * 64
        path.write_text(json.dumps(recipe))
    else:
        value["now"] = EXPIRES
    with pytest.raises(ValueError):
        manager.confirm(proposal, proposal.confirmation)
    assert not journal.exists()


def test_resume_reopens_existing_journal_and_reuses_exact_native_activation(managed):
    _, _, _, journal, _, build = managed
    writer = Writer(None)

    def reopen(store):
        writer.store = store
        return writer

    manager = build(reopen)
    proposal = preview(manager)
    grant = manager.confirm(proposal, proposal.confirmation)
    assert manager.resume(grant).state == "session_ready"
    restarted = build(reopen)
    assert restarted.resume(grant).state == "dispatched"
    assert len(writer.created) == len(writer.prompted) == 1
    assert writer.created[0] == writer.prompted[0]
    restarted.resume(grant)
    assert len(writer.created) == len(writer.prompted) == 1
    journal.unlink()
    with pytest.raises(FileNotFoundError):
        restarted.resume(grant)
    assert not journal.exists()


def test_confirmation_cannot_recreate_lost_or_replaced_execution_journal(managed):
    _, _, _, journal, _, build = managed
    manager = build()
    proposal = preview(manager)
    grant = manager.confirm(proposal, proposal.confirmation)
    original = journal.with_suffix(".original")
    journal.rename(original)
    with pytest.raises(FileNotFoundError):
        manager.confirm(proposal, proposal.confirmation)
    assert not journal.exists()
    controller.ExecutionStore(journal)
    with pytest.raises(core.Unavailable, match="initiative_execution_journal_changed"):
        manager.resume(grant)


def test_resume_with_changed_recipe_cannot_create_session(managed):
    _, path, recipe, _, _, build = managed
    writer = Writer(None)
    manager = build(lambda store: writer)
    proposal = preview(manager)
    grant = manager.confirm(proposal, proposal.confirmation)
    recipe["github_account"] = "unapproved"
    path.write_text(json.dumps(recipe))
    assert manager.resume(grant).state == "blocked"
    assert not writer.created


def test_effect_lock_is_shared_and_exclusive_for_same_grant(managed):
    custody, _, _, _, _, build = managed
    manager = build()
    proposal = preview(manager)
    grant = manager.confirm(proposal, proposal.confirmation)
    with authority.initiative_effect_lock(custody, grant):
        with pytest.raises(core.Unavailable, match="initiative_effect_lock_busy"):
            with authority.initiative_effect_lock(l.Custody(custody.common), grant, timeout=0):
                pytest.fail("a second effect acquired the same lock")
        with authority.initiative_effect_lock(custody, "8" * 64, timeout=0):
            assert authority.read_grant(custody, grant)[0] == proposal.proposal


def test_protected_callback_waits_for_identical_durable_released_activation(managed):
    _, _, _, _, _, build = managed
    writer = HeldWriter(None)
    registration = Registration(writer)
    effects = []

    def reopen(store):
        writer.store = store
        return writer

    manager = build(reopen, registration=registration, protected_tick=lambda recipe, activation: effects.append(activation))
    proposal = preview(manager)
    grant = manager.confirm(proposal, proposal.confirmation)
    for state in ("session_ready", "held", "registered", "release_accepted"):
        assert manager.resume(grant).state == state
        assert effects == []
    activation, = writer.created
    writer.release_receipt = controller.NativeRelease(activation.session_id, activation.message_id,
                                                      activation.activation_id, True)
    assert manager.resume(grant).state == "dispatched"
    assert effects == registration.calls == writer.release_calls == [activation]



CI_POLICY = ci.Policy(no_progress_seconds=30, recheck_seconds=15, max_unavailable_backoff_seconds=60,
                      retention_seconds=1_800)
SOURCE_ROUTE = "a" * 64
INFRASTRUCTURE_ROUTE = "b" * 64


def enroll_ci(path, recipe, repair_policy=None):
    recipe.update(schema_version=4, ci_policy=asdict(CI_POLICY), repair_policy=repair_policy)
    path.write_text(json.dumps(recipe))


class QualifiedRoutes:
    def __init__(self, qualified):
        self.qualified = qualified

    def qualifications(self, recipe, snapshot):
        assert recipe.ci_policy == CI_POLICY
        assert snapshot["selected"] == ["independent"]
        return self.qualified.copy()


def unexpected_effect(*args, **kwargs):
    pytest.fail("This operation must use private read-only evidence")


def test_v4_explicit_zero_preserves_ci_policy_and_rejects_unqualified_default(managed):
    custody, path, recipe, journal, _, build = managed
    enroll_ci(path, recipe)
    with pytest.raises(ValueError, match="initiative_ci_capability_unavailable"):
        preview(build(), repair_classes=("none",))
    manager = build(ci_reader=unexpected_effect)
    with pytest.raises(ValueError, match=f"initiative_repair_capability_unavailable:{repair.SOURCE}"):
        preview(manager)
    assert not journal.exists()
    reviewed = preview(manager, repair_classes=("none",))
    assert reviewed.recipe.ci_policy == CI_POLICY
    assert reviewed.review["proposal"]["ci_policy"] == asdict(CI_POLICY)
    assert reviewed.proposal["repair_limit"] == 0 and reviewed.proposal["repair_policy"] is None
    assert reviewed.proposal["allowed_operations"] == ["launch", "admit", "merge"]
    assert manager.confirm(reviewed, reviewed.confirmation) == reviewed.grant_digest
    assert authority.read_grant(custody, reviewed.grant_digest)[0] == reviewed.proposal


def test_v4_only_qualified_selected_routes_are_in_review_and_rechecked_on_confirmation(managed):
    custody, path, recipe, journal, _, build = managed
    enrolled = {
        "class_qualifications": {repair.SOURCE: SOURCE_ROUTE, repair.INFRASTRUCTURE: INFRASTRUCTURE_ROUTE},
        "writable_paths": {"first": ["code/outside.py"], "independent": ["code/selected.py"]},
    }
    enroll_ci(path, recipe, enrolled)
    routes = QualifiedRoutes({repair.SOURCE: SOURCE_ROUTE})
    manager = build(ci_reader=unexpected_effect, repair_route=routes)
    with pytest.raises(ValueError, match=f"initiative_repair_capability_unavailable:{repair.INFRASTRUCTURE}"):
        preview(manager)
    selected = preview(manager, repair_classes=(repair.SOURCE,))
    assert selected.proposal["repair_limit"] == 1
    assert selected.review["proposal"]["repair_policy"] == {
        "class_qualifications": {repair.SOURCE: SOURCE_ROUTE}, "writable_paths": {"independent": ["code/selected.py"]},
    }
    routes.qualified[repair.SOURCE] = "0" * 64
    with pytest.raises(ValueError, match=f"initiative_repair_capability_unavailable:{repair.SOURCE}"):
        manager.confirm(selected, selected.confirmation)
    assert not journal.exists()
    routes.qualified[repair.SOURCE] = SOURCE_ROUTE
    routes.qualified[repair.INFRASTRUCTURE] = INFRASTRUCTURE_ROUTE
    full = preview(manager)
    assert full.proposal["repair_limit"] == 1
    assert full.proposal["repair_policy"]["class_qualifications"] == enrolled["class_qualifications"]
    assert full.grant_digest != selected.grant_digest
    assert manager.confirm(selected, selected.confirmation) == selected.grant_digest
    assert authority.read_grant(custody, selected.grant_digest)[0] == selected.proposal


@pytest.mark.parametrize("v4", (False, True))
def test_status_uses_existing_anchor_and_grant_without_writes_or_native_capabilities(managed, monkeypatch, v4):
    custody, path, recipe, journal, value, build = managed
    if v4:
        enroll_ci(path, recipe, {"class_qualifications": {repair.INFRASTRUCTURE: INFRASTRUCTURE_ROUTE},
                                 "writable_paths": {}})
        routes = QualifiedRoutes({repair.INFRASTRUCTURE: INFRASTRUCTURE_ROUTE})
        manager = build(ci_reader=unexpected_effect, repair_route=routes)
        reviewed = preview(manager, repair_classes=(repair.INFRASTRUCTURE,))
    else:
        manager = build()
        reviewed = preview(manager)
    grant = manager.confirm(reviewed, reviewed.confirmation)
    execution_store = service.open_execution(custody)
    proposal_binding = reviewed.proposal["binding"]
    repository = proposal_binding["repository"]
    approval = controller.Approval(
        grant, controller.Target(repository["origin"], repository["repository"], proposal_binding["target_ref"]),
        proposal_binding["controller_digest"], proposal_binding["writer_digest"], (controller.Slice("independent"),),
    )
    activation = controller.Activation.from_launch(
        approval, "independent", manager.preflight(reviewed.recipe, grant, "independent"), managed=False,
    )
    assert execution_store._reserve(activation)
    with execution_store._connect() as database:
        tables = {row["name"] for row in database.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
    assert tables == {"activation", "event"}
    path.unlink()
    before = {file: (file.read_bytes(), file.stat().st_mtime_ns, file.stat().st_ino)
              for file in custody.directory.rglob("*") if file.is_file()}
    assert journal in before
    connect = controller.ExecutionStore._connect

    def read_connect(instance, *, write=False):
        assert not write
        return connect(instance, write=write)

    monkeypatch.setattr(controller.ExecutionStore, "_connect", read_connect)
    monkeypatch.setattr(service, "read_recipe", unexpected_effect)
    monkeypatch.setattr(service.InitiativeService, "resume", unexpected_effect)
    monkeypatch.setattr(l.Custody, "_write", unexpected_effect)
    monkeypatch.setattr(Provider, "observe_admission", unexpected_effect)
    monkeypatch.setattr(Provider, "observe_delivery", unexpected_effect)
    monkeypatch.setattr(Writer, "create_session", unexpected_effect)
    observer = l.Custody(custody.common)
    status = service.read_status(observer, grant, clock=lambda: value["now"])
    assert status["selected_total"] == 1 and status["delivered_total"] == 0
    assert status["repair"] == {"limit": int(v4), "used": 0, "remaining": int(v4)}
    row, = status["slices"]
    assert row["slice_id"] == "independent" and row["state"] == "implementing" and row["required_ci"] is None
    assert {file: (file.read_bytes(), file.stat().st_mtime_ns, file.stat().st_ino)
            for file in custody.directory.rglob("*") if file.is_file()} == before

    journal.rename(journal.with_suffix(".original"))
    with pytest.raises(FileNotFoundError):
        service.read_status(observer, grant, clock=lambda: value["now"])
    assert not journal.exists()
    journal.write_bytes(before[journal][0])
    journal.chmod(0o600)
    with pytest.raises(core.Unavailable, match="initiative_execution_journal_changed"):
        service.read_status(observer, grant, clock=lambda: value["now"])


def test_v4_recheck_waits_for_cadence_and_accepts_native_wakeup(managed):
    custody, path, recipe, _, value, build = managed
    enroll_ci(path, recipe)
    writer = HeldWriter(None)
    registration = Registration(writer)
    reader_calls = []
    protected_effects = []
    candidate = ci.Candidate(1, oid("base"), oid("head"), oid("tested"), "8" * 64)

    def reopen(store):
        writer.store = store
        return writer

    def observe(activation, admission, now):
        assert admission.activation_id == activation.activation_id
        reader_calls.append(now)
        return ci.Observation(candidate, "queued", "provider_queue", now, check="required")

    manager = build(reopen, registration=registration, ci_reader=observe,
                    protected_tick=lambda recipe, activation: protected_effects.append(activation))
    reviewed = preview(manager, repair_classes=("none",))
    grant = manager.confirm(reviewed, reviewed.confirmation)
    for expected in ("session_ready", "held", "registered", "release_accepted"):
        assert manager.resume(grant).state == expected
    activation, = writer.created
    writer.release_receipt = controller.NativeRelease(activation.session_id, activation.message_id,
                                                      activation.activation_id, True)
    assert manager.resume(grant).state == "dispatched"
    manager.provider.admit(activation)
    start = l.initiative_time(APPROVED_AT)

    def tick(seconds, *, wakeup=False):
        moment = start + timedelta(seconds=seconds)
        value["now"] = moment.isoformat()
        report = manager.resume(grant, wakeup=wakeup)
        return report, int(moment.timestamp())

    first, base = tick(0)
    assert first.state == "admitted" and first.next_recheck_at == base + 15
    assert reader_calls == [base]
    effects = protected_effects.copy()
    assert tick(5)[0].next_recheck_at == base + 15
    assert reader_calls == [base] and protected_effects == effects
    assert tick(5, wakeup=True)[0].next_recheck_at == base + 20
    assert reader_calls == [base, base + 5]
    tick(19)
    assert reader_calls == [base, base + 5]
    assert tick(20)[0].next_recheck_at == base + 35
    assert tick(35)[0].next_recheck_at == base + 50
    assert reader_calls == [base, base + 5, base + 20, base + 35]
    row, = service.read_status(l.Custody(custody.common), grant, clock=lambda: value["now"])["slices"]
    assert row["required_ci"] == "queued" and row["diagnostic"] == "stalled"
    assert row["stalled_since"] == base and row["next_recheck_at"] == base + 50
