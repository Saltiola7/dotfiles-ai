"""The managed service confirms exact private scope and resumes the same journal."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import (
    core, initiative_authority as authority, initiative_controller as controller, initiative_service as service, lifecycle as l,
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

    def build(writer_factory=writer, *, registration=None, protected_tick=None):
        return service.InitiativeService(
            custody, committed_scope=lambda recipe, selected: selected_snapshot(value["manifest"], selected=selected),
            live_binding=lambda recipe: value["binding"], preflight=launch,
            prior_delivery=lambda recipe, approval, slice_id, scope: False, writer=writer_factory, provider=provider,
            registration=registration, clock=lambda: value["now"], protected_tick=protected_tick,
        )

    return custody, recipe_path, recipe, journal, value, build


def preview(manager):
    return manager.preview(("independent",), operator_id="operator-1", expires_at=EXPIRES)


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
