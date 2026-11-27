"""Project approved Initiative progress from one retained read without provider access."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime, timezone
import re

from . import core, initiative_ci, initiative_controller as controller, lifecycle


_STATES = (
    "waiting_on_dependencies", "ready", "implementing", "awaiting_ci_or_integration",
    "reconciling", "delivered", "blocked", "discovery_reopened", "cancelled",
)
_WAITING_CI = frozenset({"pending", "queued", "running", "missing", "unavailable"})
_RETAINED_REPORTS = frozenset({"blocked", "discovery_reopened", "waiting", "target_busy", "uncertain",
                               "reconciling"})
_CHECK_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._()/+:-]{0,127}")
_NATIVE_FAILURES = frozenset({"error", "failure", "failed", "cancelled", "timed_out", "action_required",
                             "startup_failure", "stale"})
_SAFE_LINK_PATH = {"github": "pull", "forgejo": "pulls"}

_REASONS = {
    "protected_delivery_verified": "Protected delivery is verified in the retained journal.",
    "prerequisite_waiting": "An approved prerequisite is awaiting verified delivery.",
    "prerequisite_blocked": "An approved prerequisite needs attention.",
    "grant_revoked": "The Initiative grant has been revoked.",
    "grant_expired": "The Initiative grant has expired.",
    "grant_not_yet_active": "The Initiative grant is awaiting its effective time.",
    "material_scope_changed": "Material scope requires reviewed Discovery.",
    "execution_stopped": "The recorded execution is stopped.",
    "execution_cancelled": "The recorded execution is cancelled and its effects are settled.",
    "launch_eligible": "The recorded prerequisites allow the next exact launch.",
    "build_active": "The activation is progressing through the approved Build workflow.",
    "admitted": "The source is admitted and awaiting verified integration evidence.",
    "required_ci_pending": "The required check is pending.",
    "required_ci_queued": "The required check is queued.",
    "required_ci_running": "The required check is running.",
    "required_ci_missing": "A required check or its execution evidence is missing.",
    "required_ci_unavailable": "The provider evidence read is unavailable.",
    "required_ci_untrusted": "The retained CI observation lacks required producer or execution authority.",
    "native_failure_unproved": "The forge reports a failure without qualified execution evidence.",
    "required_ci_passed": "Required CI passed for the retained candidate.",
    "required_ci_failed": "A required check conclusively failed for the retained candidate.",
    "required_ci_stale": "The retained CI evidence needs refresh for the current candidate.",
    "repair_limit_used": "The grant has no available repair attempt.",
    "controller_blocked": "The controller recorded an unresolved blocker.",
    "target_slot_busy": "The current target slot has an active owner.",
    "controller_uncertain": "The controller could not verify the latest effect.",
    "repair_unapproved": "The source or infrastructure correction is outside the recorded grant.",
    "repair_capability_unavailable": "The enrolled target lacks the qualified recovery capability.",
    "repair_correction_unproved": "The proposed correction lacks the required verification.",
    "repair_failure_unproved": "The retained failure evidence does not authorize a repair.",
    "repair_effect_unresolved": "The reserved repair has an unresolved effect.",
    "repair_effect_verified": "The repair effect is verified and needs current required CI.",
    "protected_step_unverified": "The last protected integration action lacks verified readback.",
    "qualification_changed": "The enrolled target or runtime qualification has changed.",
}

_ACTIONS = {
    "none": "No action needed.",
    "wait_for_prerequisite": "Wait for a verified prerequisite delivery.",
    "resolve_prerequisite": "Review the held prerequisite and its recovery action.",
    "review_authority": "Review exact authority before a new mutation. Read back any unsettled effect.",
    "review_discovery": "Review the affected material scope in Discovery.",
    "review_execution": "Review the stopped execution and its retained evidence.",
    "await_launch": "Await the controller's exact launch.",
    "await_build": "Await the Build result and admission receipt.",
    "observe_integration": "Await verified integration evidence.",
    "await_ci": "Await progress or the enrolled recheck.",
    "investigate_missing_ci": "Check the required context and its qualified execution producer.",
    "restore_observation": "Restore the authoritative provider observation.",
    "verify_producer": "Verify the enrolled producer, definition and current attempt.",
    "await_protected_merge": "Await checked protection and verified inclusion.",
    "review_repair": "Review the qualified recovery evidence under the current grant.",
    "refresh_candidate": "Reobserve the exact candidate and its current required checks.",
    "reconcile_effect": "Read back the unresolved effect while preserving its fence.",
    "review_repair_authority": "Review an exact grant with a qualified available repair, or resolve the failure separately.",
}


_REPORT_REASONS = {
    "initiative_repair_unapproved": ("repair_unapproved", "review_repair_authority"),
    "initiative_repair_capability_unavailable": ("repair_capability_unavailable", "review_repair_authority"),
    "initiative_repair_budget_spent": ("repair_limit_used", "review_repair_authority"),
    "initiative_repair_correction_unproved": ("repair_correction_unproved", "review_repair"),
    "initiative_repair_failure_unproved": ("repair_failure_unproved", "verify_producer"),
    "initiative_repair_effect_unresolved": ("repair_effect_unresolved", "reconcile_effect"),
    "initiative_repair_effect_verified": ("repair_effect_verified", "await_ci"),
    "initiative_protected_step_unverified": ("protected_step_unverified", "reconcile_effect"),
    "initiative_qualification_changed": ("qualification_changed", "review_authority"),
}


def _elapsed(start: datetime | None, end: datetime) -> int | None:
    return None if start is None or start > end else int((end - start).total_seconds())


def _allowed_link(value: str | None, target: controller.Target, route: str) -> str | None:
    prefix = f"{target.origin}/{target.repository}/{route}"
    if isinstance(value, str) and len(value) <= 2048 and re.fullmatch(
            rf"{re.escape(prefix)}/[1-9][0-9]{{0,19}}", value):
        return value
    return None


def _check_label(value: str | None) -> str | None:
    if isinstance(value, str) and _CHECK_LABEL.fullmatch(value) and not (
        "//" in value or ".." in value or re.search(r"(?:gh[pousr]_|[0-9a-f]{32})", value, flags=re.I)
    ):
        return value
    return None


def _authority_stop(proposal: dict, now: datetime, revoked: bool) -> str | None:
    if revoked:
        return "grant_revoked"
    if now >= lifecycle.initiative_time(proposal["expires_at"]):
        return "grant_expired"
    if now < lifecycle.initiative_time(proposal["approved_at"]):
        return "grant_not_yet_active"
    return None


def _primary(
    execution: controller.Execution | None, dependency_states: Collection[str], clear: bool,
    authority_stop: str | None, report: controller.Report | None, ci: initiative_ci.Telemetry | None,
    repair_remaining: int,
) -> tuple[str, str, str]:
    if execution is not None and execution.delivery is not None:
        return "delivered", "protected_delivery_verified", "none"
    if (not clear or execution is not None and execution.reason == "initiative_execution_material_drift"
            or report is not None and report.state == "discovery_reopened"):
        return "discovery_reopened", "material_scope_changed", "review_discovery"
    if execution is not None and execution.state == "stopped":
        if execution.reason == "initiative_execution_cancelled":
            return "cancelled", "execution_cancelled", "none"
        return "blocked", "execution_stopped", "review_execution"
    if "blocked" in dependency_states:
        return "waiting_on_dependencies", "prerequisite_blocked", "resolve_prerequisite"
    if "waiting" in dependency_states:
        return "waiting_on_dependencies", "prerequisite_waiting", "wait_for_prerequisite"
    if authority_stop is not None:
        return "blocked", authority_stop, "review_authority"
    if report is not None:
        if report.state == "blocked":
            reason, action = _REPORT_REASONS.get(report.reason, ("controller_blocked", "review_execution"))
            return "blocked", reason, action
        if report.state == "waiting":
            return "waiting_on_dependencies", "prerequisite_waiting", "wait_for_prerequisite"
        if report.state == "target_busy":
            return "ready", "target_slot_busy", "await_launch"
        if report.state in {"uncertain", "reconciling"}:
            reason, action = _REPORT_REASONS.get(report.reason, ("controller_uncertain", "reconcile_effect"))
            return "reconciling", reason, action
        if report.state == "admitted" and report.reason == "initiative_repair_failure_unproved":
            return "awaiting_ci_or_integration", "repair_failure_unproved", "verify_producer"
    if execution is None:
        return "ready", "launch_eligible", "await_launch"
    if execution.admission is None:
        return "implementing", "build_active", "await_build"
    if ci is None:
        return "awaiting_ci_or_integration", "admitted", "observe_integration"
    ci_state = ci.observation.state
    if ci.observation.read_outcome == "untrusted":
        reason = "native_failure_unproved" if ci.observation.native_state in _NATIVE_FAILURES else "required_ci_untrusted"
        return "awaiting_ci_or_integration", reason, "verify_producer"
    if ci_state == "failed":
        if repair_remaining == 0:
            return "blocked", "repair_limit_used", "review_repair_authority"
        return "reconciling", "required_ci_failed", "review_repair"
    if ci_state == "stale":
        return "reconciling", "required_ci_stale", "refresh_candidate"
    action = {
        "pending": "await_ci",
        "queued": "await_ci",
        "running": "await_ci",
        "missing": "investigate_missing_ci",
        "unavailable": "restore_observation",
        "passed": "await_protected_merge",
    }[ci_state]
    return "awaiting_ci_or_integration", f"required_ci_{ci_state}", action


def _ci_view(ci: initiative_ci.Telemetry | None, policy: initiative_ci.Policy | None, now: int,
             state: str, target: controller.Target, provider: str) -> dict[str, object]:
    if ci is None:
        return dict.fromkeys(("candidate", "check", "attempt", "required_ci", "last_verified_age_seconds",
                              "last_verified_at", "last_progress_at", "next_recheck_at", "read_outcome",
                              "last_read_at", "queue_position", "owner", "diagnostic", "stalled_since",
                              "pull_url", "run_url"))
    seen = ci.observation
    candidate = seen.candidate
    stalled = (initiative_ci.stall(ci, policy, now)
               if policy is not None and state == "awaiting_ci_or_integration" and seen.state in _WAITING_CI else None)
    return {
        "candidate": (None if candidate is None else
                      {"head": candidate.head, "base": candidate.base, "tested": candidate.tested_oid}),
        "check": _check_label(seen.check),
        "attempt": seen.attempt,
        "required_ci": seen.state,
        "last_verified_age_seconds": (
            None if ci.last_success_at is None or ci.last_success_at > now else now - ci.last_success_at
        ),
        "last_verified_at": ci.last_success_at,
        "last_read_at": seen.read_at,
        "last_progress_at": ci.last_progress_at,
        "next_recheck_at": ci.next_recheck_at,
        "read_outcome": seen.read_outcome,
        "queue_position": None,
        "owner": None,
        "diagnostic": "stalled" if stalled is not None else None,
        "stalled_since": stalled.since if stalled is not None else None,
        "pull_url": _allowed_link(seen.diagnostic_url, target, _SAFE_LINK_PATH[provider]),
        "run_url": _allowed_link(seen.diagnostic_url, target, "actions/runs"),
    }


def project(
    proposal: dict, snapshot: dict, executions: Mapping[str, controller.Execution], *, now: datetime,
    repair_used: int = 0, verified_dependencies: Collection[str] = (),
    ci: Mapping[str, initiative_ci.Telemetry] | None = None, policy: initiative_ci.Policy | None = None,
    reports: Mapping[str, controller.Report] | None = None, revoked: bool = False,
) -> dict:
    """Join typed observations from one retained read. This projection has no effect ports."""
    lifecycle.validate("initiative_grant", proposal)
    lifecycle.validate("initiative_snapshot", snapshot)
    snapshot_digest = lifecycle.digest({"schema_version": 1, "kind": "initiative_snapshot", "value": snapshot})
    core._require(snapshot_digest == proposal["snapshot_digest"], "initiative_tally_snapshot_unbound")
    grant_id = lifecycle.digest({"schema_version": 1, "kind": "initiative_grant", "value": proposal})
    binding = lifecycle.initiative_binding(proposal["binding"])
    repository = lifecycle.initiative_repository(binding["repository"])
    target = controller.Target(lifecycle.text(repository["origin"]), lifecycle.text(repository["repository"]),
                               lifecycle.text(binding["target_ref"]))
    provider = lifecycle.text(repository["provider"])
    core._require(isinstance(now, datetime) and now.utcoffset() is not None and isinstance(revoked, bool),
                  "initiative_tally_input")
    limit = proposal["repair_limit"]
    core._integer(repair_used, minimum=0)
    core._require(repair_used <= limit, "initiative_tally_repair_budget")
    raw_policy = proposal.get("ci_policy")
    enrolled_policy = None if raw_policy is None else lifecycle.initiative_ci_policy(raw_policy)
    core._require(policy is None or policy == enrolled_policy, "initiative_tally_ci_policy_unbound")
    policy = enrolled_policy
    remaining = limit - repair_used
    telemetry = {} if ci is None else ci
    outcomes = {} if reports is None else reports
    now_seconds = int(now.timestamp())
    selected, scopes = snapshot["selected"], snapshot["slices"]
    selected_keys = set(selected)
    external_delivery = set(verified_dependencies)
    core._require(set(executions) <= selected_keys and set(telemetry) <= set(executions)
                  and set(outcomes) <= selected_keys | {""}
                  and external_delivery <= scopes.keys() - selected_keys, "initiative_tally_slice_unbound")
    for key, row in executions.items():
        core._require(type(row) is controller.Execution and row.state != "superseded", "initiative_tally_execution")
        activation = row.activation
        core._require((activation.slice_id, activation.grant_id, activation.target,
                      activation.controller_digest, activation.writer_digest) == (
                      key, grant_id, target, binding["controller_digest"], binding["writer_digest"]),
                      "initiative_tally_execution_unbound")
    for key, view in telemetry.items():
        core._require(type(view) is initiative_ci.Telemetry, "initiative_tally_ci_unbound")
    expired = {
        key for key, view in telemetry.items()
        if policy is not None and initiative_ci.diagnostic_expired(view, policy, now_seconds)
    }
    telemetry = {
        key: view for key, view in telemetry.items()
        if key not in expired and executions[key].admission is not None
    }
    for key, report in outcomes.items():
        row = executions.get(key)
        core._require(type(report) is controller.Report and report.slice_id == (key or None)
                      and (report.activation_id is None
                           or row is not None and report.activation_id == row.activation.activation_id),
                      "initiative_tally_report_unbound")
    retained = {
        key: report for key, report in outcomes.items()
        if report.state in _RETAINED_REPORTS
        or (key not in expired and report.state == "admitted"
            and report.reason == "initiative_repair_failure_unproved")
    }
    general = retained.get("")
    if general is not None and general.state not in {"blocked", "uncertain"}:
        general = None

    authority_stop = _authority_stop(proposal, now, revoked)
    counts = dict.fromkeys(_STATES, 0)
    states: dict[str, str] = {}
    slices: list[dict] = []

    def state_of(key: str) -> str:
        if key in states:
            return states[key]
        if key in external_delivery:
            return "delivered"
        if key not in selected_keys:
            return "blocked" if not scopes[key]["clear"] else "waiting"
        _, state, reason, _ = status_of(key)
        states[key] = "delivered" if state == "delivered" else (
            "blocked" if state in {"blocked", "cancelled", "discovery_reopened"} or reason == "prerequisite_blocked"
            else "waiting")
        return states[key]

    def status_of(key: str) -> tuple[dict[str, str], str, str, str]:
        scope = scopes[key]
        dependencies = {dep: state_of(dep) for dep in scope["depends_on"]}
        state, reason, action = _primary(executions.get(key), dependencies.values(), scope["clear"], authority_stop,
                                        retained.get(key, general), telemetry.get(key), remaining)
        return dependencies, state, reason, action

    for key in selected:
        dependencies, state, reason, action = status_of(key)
        counts[state] += 1
        slices.append({
            "slice_id": key,
            "dependencies": dependencies,
            "state": state,
            "reason": reason,
            "next_action": action,
            **_ci_view(telemetry.get(key), policy, now_seconds, state, target, provider),
        })
    return {
        "schema_version": 1,
        "initiative_id": snapshot["initiative_id"],
        "selected_total": len(selected),
        "delivered_total": counts["delivered"],
        "state_counts": counts,
        "repair": {"limit": limit, "used": repair_used, "remaining": remaining},
        "elapsed_seconds": _elapsed(lifecycle.initiative_time(proposal["approved_at"]), now),
        "slices": slices,
    }


def _utc_label(stamp: int) -> str:
    try:
        return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return "unavailable"


def render_text(report: dict) -> str:
    """Describe the same versioned projection in the terminal."""
    budget = report["repair"]
    rows = [
        f"{report['initiative_id']}  {report['delivered_total']}/{report['selected_total']} delivered",
        f"Repair budget  {budget['used']} used, {budget['remaining']} remaining of {budget['limit']}",
    ]
    states = ", ".join(f"{count} {state.replace('_', ' ')}" for state, count in report["state_counts"].items() if count)
    rows.append(f"States  {states}")
    if report["elapsed_seconds"] is not None:
        rows.append(f"Since approval  {report['elapsed_seconds']} s")
    for row in report["slices"]:
        state = row["state"].replace("_", " ")
        suffix = " (stalled)" if row["diagnostic"] == "stalled" else ""
        rows.extend([f"{row['slice_id']}  {state}{suffix}", _REASONS[row["reason"]], _ACTIONS[row["next_action"]]])
        if row["dependencies"]:
            dependencies = ", ".join(f"{key} {state}" for key, state in row["dependencies"].items())
            rows.append(f"Prerequisites  {dependencies}")
        if row["candidate"] is not None:
            candidate = row["candidate"]
            rows.append(f"Candidate  head {candidate['head']}, base {candidate['base']}, tested {candidate['tested']}")
        if row["required_ci"] is not None:
            check = row["check"] or "check unavailable"
            attempt = row["attempt"] if row["attempt"] is not None else "unavailable"
            age = row["last_verified_age_seconds"]
            age_label = "unavailable" if age is None else f"{age} s"
            rows.append(f"CI  {check}, {row['required_ci']}, attempt {attempt}, evidence age {age_label}")
        for label, key in (("Last native progress", "last_progress_at"), ("Latest read time", "last_read_at"),
                           ("Next recheck", "next_recheck_at"), ("Stalled since", "stalled_since")):
            if row[key] is not None:
                rows.append(f"{label}  {_utc_label(row[key])}")
        for label, key in (("Latest read", "read_outcome"), ("Queue position", "queue_position"),
                           ("Pull request", "pull_url"), ("Run", "run_url")):
            if row[key] is not None:
                rows.append(f"{label}  {row[key]}")
    return "\n".join(rows)
