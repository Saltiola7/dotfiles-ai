"""Use one retained Initiative view for the displayed tally and its JSON."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, initiative_authority, initiative_ci as ci, lifecycle
from integration_coordinator import initiative_controller as controller, initiative_status as status


NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)
NOW_SECONDS = int(NOW.timestamp())
POLICY = ci.Policy(60, 15, 60, 300)
REPOSITORY = {"provider": "forgejo", "origin": "https://forge.example", "repository": "org/project"}


def digest(number: int) -> str:
    return f"{number:064x}"


def oid(number: int) -> str:
    return f"{number:040x}"


@pytest.fixture
def approved():
    snapshot = {
        "schema_version": 1, "initiative_id": "example",
        "manifest_path": "docs/initiatives/example/MANIFEST.json", "source_commit": oid(1),
        "selected": ["first", "second", "separate"],
        "slices": {
            name: {"scope_digest": digest(index), "depends_on": dependencies, "repository": REPOSITORY, "clear": True}
            for index, (name, dependencies) in enumerate([
                ("first", ["historical"]), ("second", ["first"]), ("separate", []), ("historical", []),
            ], 10)
        },
    }
    binding = {"repository": REPOSITORY, "target_ref": "refs/heads/main", "root_oid": oid(2),
               "controller_digest": digest(3), "writer_digest": digest(4), "policy_digest": digest(5),
               "enrollment_digest": digest(6), "qualification_digest": digest(7)}
    proposal = initiative_authority.grant_proposal(
        snapshot, binding=binding, operator_id="private-operator",
        approved_at="2026-01-01T00:00:00Z", expires_at="2026-01-03T00:00:00Z",
        allowed_operations=("launch", "admit", "merge"), repair_limit=0,
    )
    return proposal, snapshot


def grant_with_policy(proposal: dict, repair_limit: int = 0):
    repair_policy = {"class_qualifications": {"infrastructure_retry": digest(8)}, "writable_paths": {}}
    return {**proposal, "schema_version": 2, "ci_policy": asdict(POLICY), "repair_limit": repair_limit,
            "repair_policy": repair_policy if repair_limit else None,
            "allowed_operations": proposal["allowed_operations"] + (["repair"] if repair_limit else [])}


def execution(proposal: dict, name: str, state: str, reason: str | None = None) -> controller.Execution:
    grant = lifecycle.digest({"schema_version": 1, "kind": "initiative_grant", "value": proposal})
    target = controller.Target(REPOSITORY["origin"], REPOSITORY["repository"], "refs/heads/main")
    approval = controller.Approval(grant, target, digest(3), digest(4), (controller.Slice(name),))
    launch = controller.Launch(digest(9), oid(3), "/private/data/checkout", "PRIVATE-CYCLE-ID", "build")
    activation = controller.Activation.from_launch(approval, name, launch)
    admission = (controller.Admission(activation.activation_id, target, "a" * 32, "b" * 32, digest(15))
                 if state in {"admitted", "delivered"} else None)
    delivery = (controller.Delivery(activation.activation_id, target, "a" * 32, "b" * 32, oid(4), digest(16))
                if state == "delivered" else None)
    return controller.Execution(activation, state, admission, delivery, reason)


def project(proposal: dict, snapshot: dict, executions: dict, **facts) -> dict:
    return status.project(proposal, snapshot, executions, now=NOW, verified_dependencies={"historical"}, **facts)


def test_historical_progress_and_blocked_prerequisite_keep_the_denominator(approved):
    proposal, snapshot = approved
    rows = {
        "first": execution(proposal, "first", "stopped", "initiative_execution_material_drift"),
        "separate": execution(proposal, "separate", "delivered"),
    }
    summary = project(proposal, snapshot, rows)
    first, second, separate = summary["slices"]
    assert [row["state"] for row in summary["slices"]] == ["discovery_reopened", "waiting_on_dependencies", "delivered"]
    assert first["dependencies"] == {"historical": "delivered"}
    assert second["dependencies"] == {"first": "blocked"}
    assert second["reason"] == "prerequisite_blocked"
    assert separate["last_verified_age_seconds"] is None
    assert summary["schema_version"] == 1
    assert summary["selected_total"] == sum(summary["state_counts"].values()) == 3
    assert summary["delivered_total"] == 1
    assert summary["repair"] == {"limit": 0, "used": 0, "remaining": 0}
    text = status.render_text(summary)
    assert "1/3 delivered" in text and "first  discovery reopened" in text and "second  waiting on dependencies" in text
    encoded = text + json.dumps(summary)
    for item in ("private-operator", "PRIVATE-CYCLE-ID", "/private/data", rows["first"].activation.session_id,
                 rows["first"].activation.activation_id):
        assert item not in encoded


def test_no_legacy_dependency_claim_without_retained_proof(approved):
    proposal, snapshot = approved
    report = status.project(proposal, snapshot, {}, now=NOW)
    assert [row["state"] for row in report["slices"]] == ["waiting_on_dependencies", "waiting_on_dependencies", "ready"]
    assert report["slices"][0]["dependencies"] == {"historical": "waiting"}


def test_revocation_preserves_delivered_history_and_stops_new_work(approved):
    proposal, snapshot = approved
    summary = project(proposal, snapshot, {"first": execution(proposal, "first", "delivered")}, revoked=True)
    assert summary["delivered_total"] == 1
    assert [row["reason"] for row in summary["slices"]] == ["protected_delivery_verified", "grant_revoked", "grant_revoked"]


def telemetry(state="queued", *, diagnostic_url=None, check="Tests / linux", read_outcome="verified"):
    candidate = ci.Candidate(1, oid(3), oid(4), oid(4), digest(18))
    observation = ci.Observation(
        candidate, state, "arbitrary_private_diagnostic", NOW_SECONDS - 5,
        read_outcome=read_outcome, check=check, run_id=21, attempt=1,
        native_progress_at=NOW_SECONDS - 70 if state == "queued" else None,
        diagnostic_url=diagnostic_url, failure_digest=digest(20) if state == "failed" else None,
    )
    return ci.advance(None, observation, POLICY)


def test_running_diagnostic_does_not_change_primary_waiting_state(approved):
    proposal, snapshot = approved
    proposal = grant_with_policy(proposal)
    summary = project(proposal, snapshot, {"first": execution(proposal, "first", "admitted")},
                      ci={"first": telemetry(diagnostic_url="https://forge.example/org/project/actions/runs/21")})
    first = summary["slices"][0]
    assert first["state"] == "awaiting_ci_or_integration" and first["diagnostic"] == "stalled"
    assert first["candidate"] == {"head": oid(4), "base": oid(3), "tested": oid(4)}
    assert first["required_ci"] == "queued" and first["attempt"] == 1
    assert first["last_verified_age_seconds"] == 5
    assert first["last_progress_at"] == NOW_SECONDS - 70 and first["last_read_at"] == NOW_SECONDS - 5
    assert first["stalled_since"] == first["last_progress_at"]
    assert first["next_recheck_at"] == NOW_SECONDS + 10
    assert first["run_url"] == "https://forge.example/org/project/actions/runs/21"
    assert first["owner"] is None and first["queue_position"] is None
    text = status.render_text(summary)
    assert "(stalled)" in text and "evidence age 5 s" in text and "Run  https://forge.example/" in text
    assert "arbitrary_private_diagnostic" not in text + json.dumps(first)


@pytest.mark.parametrize(("state", "read_outcome", "reason", "primary"), [
    ("unavailable", "unavailable", "required_ci_unavailable", "awaiting_ci_or_integration"),
    ("unavailable", "untrusted", "required_ci_untrusted", "awaiting_ci_or_integration"),
    ("missing", "verified", "required_ci_missing", "awaiting_ci_or_integration"),
    ("stale", "stale", "required_ci_stale", "reconciling"),
    ("passed", "verified", "required_ci_passed", "awaiting_ci_or_integration"),
    ("failed", "verified", "required_ci_failed", "reconciling"),
])
def test_ci_outcomes_distinguish_failure_drift_outage_and_missing(approved, state, read_outcome, reason, primary):
    proposal, snapshot = approved
    proposal = grant_with_policy(proposal, repair_limit=1)
    admitted = execution(proposal, "first", "admitted")
    row = project(proposal, snapshot, {"first": admitted},
                  ci={"first": telemetry(state, read_outcome=read_outcome)})["slices"][0]
    assert (row["reason"], row["state"], row["diagnostic"]) == (reason, primary, None)


def test_executed_repair_budget_and_retained_report_use_one_view(approved):
    proposal, snapshot = approved
    proposal = grant_with_policy(proposal, repair_limit=1)
    admitted = execution(proposal, "first", "admitted")
    retained = controller.Report("reconciling", "first", admitted.activation.activation_id,
                                 "initiative_repair_effect_unresolved")
    summary = project(proposal, snapshot, {"first": admitted}, repair_used=1,
                      ci={"first": telemetry("failed")}, reports={"first": retained})
    first = summary["slices"][0]
    assert (first["state"], first["reason"], first["next_action"]) == (
        "reconciling", "repair_effect_unresolved", "reconcile_effect")
    assert summary["repair"] == {"limit": 1, "used": 1, "remaining": 0}
    spent = project(proposal, snapshot, {"first": admitted}, repair_used=1,
                    ci={"first": telemetry("failed")})["slices"][0]
    assert (spent["state"], spent["reason"]) == ("blocked", "repair_limit_used")


@pytest.mark.parametrize("url", [
    "https://foreign.example/org/project/pulls/7",
    "https://forge.example/org/other/pulls/7",
    "https://forge.example/org/project/private/path-name",
])
def test_projection_removes_non_allowlisted_links_and_untrusted_strings(approved, url):
    proposal, snapshot = approved
    row = project(proposal, snapshot, {"first": execution(proposal, "first", "admitted")},
                  ci={"first": telemetry(diagnostic_url=url, check="ghp_diagnostic-private")})["slices"][0]
    assert row["pull_url"] is None and row["run_url"] is None and row["check"] is None


def test_projection_refuses_wrong_activation_and_unbound_policy(approved):
    proposal, snapshot = approved
    first = execution(proposal, "first", "admitted")
    wrong_id = digest(19)
    with pytest.raises(core.Invalid, match="initiative_tally_report_unbound"):
        project(proposal, snapshot, {"first": first},
                reports={"first": controller.Report("blocked", "first", wrong_id, "untrusted-private-reason")})
    with pytest.raises(core.Invalid, match="initiative_tally_ci_policy_unbound"):
        project(proposal, snapshot, {"first": first}, policy=POLICY)
    with pytest.raises(core.Invalid, match="initiative_tally_execution_unbound"):
        project(proposal, snapshot, {"first": replace(first, activation=execution(proposal, "second", "reserved").activation)})


def test_positive_reports_and_global_block_keep_receipted_delivery(approved):
    proposal, snapshot = approved
    first = execution(proposal, "first", "delivered")
    summary = status.project(proposal, snapshot, {"first": first}, now=NOW, verified_dependencies={"historical"},
                             reports={"first": controller.Report("delivered", "first", first.activation.activation_id),
                                      "": controller.Report("blocked", reason="arbitrary_private_diagnostic")})
    assert [(row["state"], row["reason"]) for row in summary["slices"]] == [
        ("delivered", "protected_delivery_verified"),
        ("blocked", "controller_blocked"),
        ("blocked", "controller_blocked"),
    ]
    assert "arbitrary_private_diagnostic" not in json.dumps(summary)


def test_stale_queued_evidence_is_not_a_current_stall(approved):
    proposal, snapshot = approved
    proposal = grant_with_policy(proposal)
    observed = telemetry()
    future = datetime.fromtimestamp(observed.next_recheck_at + 1, timezone.utc)
    report = status.project(proposal, snapshot, {"first": execution(proposal, "first", "admitted")},
                            now=future, ci={"first": observed}, verified_dependencies={"historical"})
    assert report["slices"][0]["diagnostic"] is None
    assert report["slices"][0]["last_verified_age_seconds"] > POLICY.recheck_seconds



def test_native_failure_without_independent_evidence_remains_a_wait(approved):
    proposal, snapshot = approved
    admitted = execution(proposal, "first", "admitted")
    observed = telemetry("unavailable", read_outcome="untrusted")
    native_red = replace(observed, observation=replace(observed.observation, native_state="failure"))
    row = project(proposal, snapshot, {"first": admitted}, ci={"first": native_red})["slices"][0]
    assert (row["state"], row["reason"], row["next_action"]) == (
        "awaiting_ci_or_integration", "native_failure_unproved", "verify_producer")



def test_retention_excludes_expired_telemetry_and_its_action_only(approved):
    proposal, snapshot = approved
    proposal = grant_with_policy(proposal, repair_limit=1)
    admitted = execution(proposal, "first", "admitted")
    retained = telemetry("failed", diagnostic_url="https://forge.example/org/project/pulls/7")
    at_expiry = retained.observation.read_at + POLICY.retention_seconds
    prior = status.project(
        proposal, snapshot, {"first": admitted}, now=datetime.fromtimestamp(at_expiry - 1, timezone.utc),
        ci={"first": retained}, verified_dependencies={"historical"},
    )["slices"][0]
    assert prior["state"] == "reconciling" and prior["reason"] == "required_ci_failed"
    assert prior["pull_url"] is not None and prior["check"] == "Tests / linux"

    no_failure_proof = controller.Report("admitted", "first", admitted.activation.activation_id,
                                         "initiative_repair_failure_unproved")
    actual = status.project(
        proposal, snapshot, {"first": admitted}, now=datetime.fromtimestamp(at_expiry, timezone.utc),
        ci={"first": retained}, verified_dependencies={"historical"}, reports={"first": no_failure_proof},
    )
    row = actual["slices"][0]
    assert (row["state"], row["reason"], row["next_action"]) == (
        "awaiting_ci_or_integration", "admitted", "observe_integration")
    for key in ("required_ci", "check", "candidate", "next_recheck_at", "last_verified_age_seconds", "pull_url"):
        assert row[key] is None
    assert "Tests / linux" not in status.render_text(actual)
    assert retained.observation.failure_digest == digest(20)

    unresolved = replace(no_failure_proof, state="reconciling", reason="initiative_repair_effect_unresolved")
    unclosed = status.project(
        proposal, snapshot, {"first": admitted}, now=datetime.fromtimestamp(at_expiry, timezone.utc),
        ci={"first": retained}, verified_dependencies={"historical"}, repair_used=1, reports={"first": unresolved},
    )
    assert unclosed["slices"][0]["reason"] == "repair_effect_unresolved"
    assert unclosed["repair"] == {"limit": 1, "used": 1, "remaining": 0}
