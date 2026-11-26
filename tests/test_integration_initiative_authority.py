"""Initiative authority survives progress and fences unapproved mutations."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, initiative_authority as authority, initiative_controller as controller, lifecycle as l
from test_integration_initiative_controller import Provider, Writer


REPOSITORY = {"provider": "github", "origin": "https://github.com", "repository": "fixture/project"}
APPROVED_AT = "2026-11-24T19:00:00Z"
NOW = "2026-11-24T19:05:00Z"
EXPIRES = "2026-11-24T20:00:00Z"
SELECTED = ("first", "second", "independent")


def oid(value: str) -> str:
    return hashlib.sha1(value.encode(), usedforsecurity=False).hexdigest()


def binding() -> dict:
    return {"repository": REPOSITORY.copy(), "root_oid": oid("root"), "target_ref": "refs/heads/main",
            "policy_digest": "1" * 64, "enrollment_digest": "2" * 64, "controller_digest": "3" * 64,
            "writer_digest": "4" * 64, "qualification_digest": "5" * 64}


def manifest() -> dict:
    ids = ("predecessor", *SELECTED)
    statements = [{"id": f"INT-{i:03d}", "kind": "requirement", "text": name,
                   "disposition": "delivered" if not i else "ready",
                   "artifacts": [f"docs/requirements/{name}.md"]} for i, name in enumerate(ids)]
    slices = [{"id": name, "context": "fixture", "state": state, "execution_owner": "build",
               "requirements": [statement["id"]], "depends_on": dependencies,
               "artifacts": [f"docs/slices/{name}/ACCEPTANCE.md"], "release_group": "fixture-release"}
              for (name, state, dependencies), statement in zip(
                  (("predecessor", "delivered", []), ("first", "ready", ["predecessor"]),
                   ("second", "discovering", ["first"]), ("independent", "ready", [])),
                  statements, strict=True)]
    return {"schema_version": 2, "id": "test-initiative", "title": "Fixture Initiative", "state": "ready",
            "coordinator_repository": REPOSITORY.copy(), "statements": statements,
            "contexts": [{"id": "fixture", "repository": REPOSITORY.copy(), "status": "ready", "depends_on": []}],
            "slices": slices, "release_groups": [{"id": "fixture-release", "members": list(ids), "state": "ready"}]}


def selected_snapshot(value: dict | None = None, *, selected: tuple[str, ...] = SELECTED,
                      blobs=None, commit: str = "approved") -> dict:
    return authority.material_snapshot(manifest() if value is None else value, selected,
                                       oid if blobs is None else blobs, commit=oid(commit))


def proposal(snapshot: dict, **overrides) -> dict:
    inputs = {"binding": binding(), "operator_id": "operator-1", "approved_at": APPROVED_AT,
              "expires_at": EXPIRES, "allowed_operations": ("launch", "admit", "merge"), "repair_limit": 0}
    return authority.grant_proposal(snapshot, **(inputs | overrides))


@pytest.fixture
def approved(tmp_path):
    custody = l.Custody(tmp_path)
    snapshot = selected_snapshot()
    grant = proposal(snapshot)
    identity = authority.store_grant(custody, snapshot, grant, expected_approval_digest=l.digest(grant))
    return custody, snapshot, grant, identity


def require(approved, **overrides):
    custody, snapshot, _, identity = approved
    inputs = {"binding": binding(), "current": snapshot, "slice_id": "first", "operation": "launch", "now": NOW}
    return authority.require_grant(custody, identity, **(inputs | overrides))


def test_progress_and_new_commit_preserve_material_hashes():
    approved = selected_snapshot()
    progressed = manifest()
    progressed["state"] = "building"
    progressed["contexts"][0]["status"] = "building"
    progressed["release_groups"][0]["state"] = "building"
    progressed["slices"][1].update(state="delivered", tickets=["integration-ticket"])
    progressed["slices"][2]["state"] = "ready"
    progressed["statements"][1]["disposition"] = "delivered"
    current = selected_snapshot(progressed, commit="new-main")
    assert approved["source_commit"] != current["source_commit"]
    assert all(authority.same_material(approved, current, name) for name in SELECTED)
    assert current["slices"]["second"]["depends_on"] == ["first"]
    assert "predecessor" in current["slices"] and "predecessor" not in current["selected"]


def test_blocked_progress_does_not_modify_approval_and_defer_withdraws_scope():
    approved = selected_snapshot()
    value = manifest()
    value["slices"][1]["state"] = "blocked"
    assert authority.same_material(approved, selected_snapshot(value), "first")
    value["slices"][1]["state"] = "deferred"
    assert not authority.same_material(approved, selected_snapshot(value), "first")
    assert not authority.same_material(approved, selected_snapshot(value), "second")


@pytest.mark.parametrize("change", ("text", "unresolved", "rewired", "owner", "artifact", "absent"))
def test_drift_reopens_affected_dependency_closure_only(change):
    approved = selected_snapshot()
    changed = manifest()
    artifact = "docs/requirements/predecessor.md"

    def blobs(path: str) -> str:
        if path == artifact and change == "absent":
            raise FileNotFoundError(path)
        return oid(path + " edited" if path == artifact and change == "artifact" else path)

    if change == "text":
        changed["statements"][0]["text"] += " changed"
    if change == "unresolved":
        changed["statements"][0]["disposition"] = "blocked"
    if change == "rewired":
        changed["slices"][1]["depends_on"] = []
    if change == "owner":
        changed["slices"][0]["execution_owner"] = "discovery"
    current = selected_snapshot(changed, blobs=blobs, commit="changed")
    assert not authority.same_material(approved, current, "first")
    assert not authority.same_material(approved, current, "second")
    assert authority.same_material(approved, current, "independent")


def test_release_group_and_target_are_material():
    original = selected_snapshot()
    current = manifest()
    current["contexts"][0]["repository"]["repository"] = "fixture/other"
    assert not authority.same_material(original, selected_snapshot(current), "first")
    current = manifest()
    current["release_groups"][0]["members"].remove("independent")
    current["release_groups"].append({"id": "other-group", "members": ["independent"], "state": "ready"})
    current["slices"][-1]["release_group"] = "other-group"
    assert not authority.same_material(original, selected_snapshot(current), "second")


def test_identical_manifest_at_another_path_is_not_approved():
    original = selected_snapshot()
    current = authority.material_snapshot(manifest(), SELECTED, oid, commit=oid("approved"),
                                          manifest_path="docs/initiatives/other/MANIFEST.json")
    assert not authority.same_material(original, current, "first")


def test_private_approval_round_trip_and_exact_confirmation(approved):
    custody, snapshot, grant, identity = approved
    restarted = l.Custody(custody.common)
    assert authority.read_grant(restarted, identity) == (grant, snapshot)
    assert restarted.object_path(identity).stat().st_mode & 0o777 == 0o600
    assert require(approved) == grant
    assert authority.store_grant(restarted, snapshot, grant, expected_approval_digest=l.digest(grant)) == identity
    with pytest.raises(ValueError):
        authority.store_grant(restarted, snapshot, grant, expected_approval_digest="0" * 64)
    modified = grant | {"operator_id": "another-operator"}
    with pytest.raises(ValueError):
        authority.store_grant(restarted, snapshot, modified, expected_approval_digest=l.digest(grant))


@pytest.mark.parametrize("field", ("repository", "root_oid", "target_ref", "policy_digest", "enrollment_digest",
                                  "controller_digest", "writer_digest", "qualification_digest"))
def test_requires_exact_enrollment_and_writer_binding(approved, field):
    observed = binding()
    if field == "repository":
        observed[field]["repository"] = "fixture/other"
    elif field == "target_ref":
        observed[field] = "refs/heads/other"
    elif field == "root_oid":
        observed[field] = oid("other root")
    else:
        observed[field] = "0" * 64
    with pytest.raises(ValueError):
        require(approved, binding=observed)


@pytest.mark.parametrize("overrides", ({"now": EXPIRES}, {"now": "2026-11-24T18:59:59Z"},
                                       {"slice_id": "predecessor"}, {"operation": "repair"}))
def test_grant_refuses_expiry_future_approval_unselected_slice_and_operation(approved, overrides):
    with pytest.raises(ValueError):
        require(approved, **overrides)


def test_grant_observes_drift_and_revocation_after_restart(approved):
    custody, _, grant, identity = approved
    value = manifest()
    value["statements"][0]["text"] += " changed"
    current = selected_snapshot(value)
    with pytest.raises(ValueError):
        require(approved, current=current, slice_id="second")
    current_independent = selected_snapshot(value, selected=("independent",))
    assert require(approved, current=current_independent, slice_id="independent") == grant
    authority.revoke_grant(custody, identity, reason_digest="7" * 64, revoked_at=NOW)
    restarted = (l.Custody(custody.common), *approved[1:])
    with pytest.raises(ValueError):
        require(restarted)
    with pytest.raises(ValueError):
        authority.revoke_grant(custody, identity, reason_digest="8" * 64, revoked_at=NOW)


def test_custody_rejects_wrong_repository_and_changed_snapshot(approved):
    custody, snapshot, grant, _ = approved
    wrong = deepcopy(snapshot)
    wrong["slices"]["first"]["scope_digest"] = "0" * 64
    with pytest.raises(ValueError):
        authority.store_grant(custody, wrong, grant, expected_approval_digest=l.digest(grant))
    other = binding()
    other["repository"]["repository"] = "fixture/other"
    with pytest.raises(ValueError):
        proposal(snapshot, binding=other)


def test_a_repair_must_fit_the_approved_attempt_limit(approved):
    custody, snapshot, _, _ = approved
    grant = proposal(snapshot, allowed_operations=("launch", "admit", "merge", "repair"), repair_limit=1)
    identity = authority.store_grant(custody, snapshot, grant, expected_approval_digest=l.digest(grant))
    with_repair = (custody, snapshot, grant, identity)
    with pytest.raises(ValueError):
        require(with_repair, operation="repair")
    with pytest.raises(ValueError):
        require(with_repair, operation="repair", repair_attempt=2)
    assert require(with_repair, operation="repair", repair_attempt=1) == grant


def test_custody_rejects_unclosed_or_cyclic_snapshot(approved):
    custody, snapshot, _, _ = approved
    broken = deepcopy(snapshot)
    broken["slices"].pop("predecessor")
    with pytest.raises(ValueError):
        custody.write("initiative_snapshot", broken)
    cyclic = deepcopy(snapshot)
    cyclic["slices"]["predecessor"]["depends_on"] = ["second"]
    with pytest.raises(ValueError):
        custody.write("initiative_snapshot", cyclic)


def test_begin_receipt_is_closed_and_reads_exact_private_evidence(tmp_path):
    custody = l.Custody(tmp_path)
    receipt = {"grant_digest": "1" * 64, "activation_digest": "2" * 64, "launch_digest": "3" * 64,
               "cycle_id": "cycle-1", "session_digest": "4" * 64, "authorized_at": APPROVED_AT}
    identity = custody.write("initiative_begin", receipt)
    assert custody.read("initiative_begin", identity) == receipt
    with pytest.raises(ValueError):
        custody.write("initiative_begin", receipt | {"session_digest": "caller-session"})
    with pytest.raises(ValueError):
        custody.write("initiative_begin", receipt | {"extra": "unexpected"})
    with pytest.raises(ValueError):
        custody.read("authorization", identity)


def test_controller_authority_checks_current_scope_and_preserves_prior_reads(approved):
    custody, snapshot, _, identity = approved
    current = manifest()
    current["statements"][0]["text"] += " changed"
    observations = {"binding": binding(), "now": NOW}
    launch = controller.Launch("6" * 64, oid("base"), "/tmp/checkout", "cycle-1", "build")
    calls = []

    def preflight(slice_id):
        calls.append(slice_id)
        return launch

    adapter = authority.CustodyAuthority(
        custody, current_binding=lambda: observations["binding"],
        current_scope=lambda slice_id: selected_snapshot(current, selected=(slice_id,)),
        plan=preflight, prior_delivery=lambda review, slice_id, scope: (
            review.grant_id == identity and slice_id == "predecessor" and scope == snapshot["slices"][slice_id]),
        clock=lambda: observations["now"],
    )
    review = adapter.approval(identity)
    assert review.target == controller.Target("https://github.com", "fixture/project", "refs/heads/main")
    assert tuple(item.slice_id for item in review.slices) == SELECTED
    assert review.mutation_stop is None
    assert adapter.preflight(review, "second") is None
    assert adapter.preflight(review, "independent") == launch
    assert calls == ["independent"]
    assert adapter.dependency_delivered(review, "predecessor") is True
    assert adapter.dependency_delivered(review, "first") is False
    assert adapter.dependency_delivered(review, "unapproved") is False
    database = custody.directory / "initiative.sqlite"
    store = controller.ExecutionStore(database)
    writer = Writer(store)
    runtime = controller.InitiativeController(store, adapter, writer, Provider())
    outcome = runtime.advance(identity)
    assert (outcome.state, outcome.slice_id) == ("session_ready", "independent")
    assert [activation.slice_id for activation in writer.created] == ["independent"]
    assert set(calls) == {"independent"}
    observations["binding"] = binding() | {"qualification_digest": "0" * 64}
    held = adapter.approval(identity)
    assert held.mutation_stop is not None
    assert adapter.dependency_delivered(held, "predecessor") is True
    with pytest.raises(core.Unavailable):
        adapter.preflight(review, "independent")
