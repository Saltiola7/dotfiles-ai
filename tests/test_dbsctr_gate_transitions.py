"""Finite policy cases for admitted gate replacement, without CLI or storage I/O.

These synthetic policy records do not qualify record admission or persistence.
Expected transitions come from the PY-02 contract table, not production predicates.
"""

import copy
import importlib.machinery
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
GATE_ORDER = (
    "domain", "behavior", "spec", "contract", "test_driven_implementation",
    "refactor", "review_integrate", "release", "deploy", "operate", "maintain_retire",
)
LATER_SUCCESSES = {
    "domain": ("behavior", "spec", "refactor", "review_integrate"),
    "refactor": ("review_integrate",),
    "maintain_retire": (),
}
REOPENING_OUTCOMES = ("pending", "failed", "unavailable")
FAILURE_OUTCOMES = ("failed", "unavailable")
PRIOR_CASES = [
    pytest.param("pending", None, (), FAILURE_OUTCOMES, (), id="pending"),
    pytest.param("passed", None, REOPENING_OUTCOMES, FAILURE_OUTCOMES, (), id="passed"),
    pytest.param("failed", None, (), (), ("passed",), id="failed"),
    pytest.param("unavailable", None, (), (), ("passed",), id="unavailable"),
    pytest.param("failed", "deferred", REOPENING_OUTCOMES, (), ("passed",), id="failed-deferred"),
    pytest.param("failed", "accepted_risk", REOPENING_OUTCOMES, (), ("passed",), id="failed-accepted"),
    pytest.param("unavailable", "deferred", REOPENING_OUTCOMES, (), ("passed",), id="unavailable-deferred"),
    pytest.param("unavailable", "accepted_risk", REOPENING_OUTCOMES, (), ("passed",), id="unavailable-accepted"),
]


@pytest.fixture(scope="module")
def core():
    loader = importlib.machinery.SourceFileLoader("gate_policy_under_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    assert module.GATES == GATE_ORDER
    return module


@pytest.fixture
def isolated_policy(core, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Gate-result policy invoked an I/O or admission boundary")

    for name in ("root_dir", "git", "load", "save", "atomic_json", "evidence_lock",
                 "write_sidecar", "require_current_profile", "amendment_fresh_evidence"):
        monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr(core, "open", forbidden, raising=False)
    monkeypatch.setattr(core, "subprocess", SimpleNamespace(
        run=forbidden, Popen=forbidden, check_output=forbidden,
    ))
    return core


def approved_exception(kind):
    return {"kind": kind, "rationale": "Synthetic policy case", "owner": "test",
            "review_condition": "next test", "approved_at": "2026-10-31T00:00:00Z"}


def policy_record(schema, selected, prior_result, exception_kind, missing_metrics):
    gates, history = {}, {}
    for index, name in enumerate(GATE_ORDER):
        result, kind = "passed", None
        if index > GATE_ORDER.index(selected):
            if name in {"contract", "operate"}:
                result, kind = "failed", "deferred"
            elif name in {"test_driven_implementation", "maintain_retire"}:
                result, kind = "unavailable", "accepted_risk"
            elif name == "deploy":
                result = "pending"
            elif name == "release":
                gates[name] = {"applicability": "not_applicable", "result": "not_run",
                               "reason": "Synthetic source-only case"}
                continue
        if name == selected:
            result, kind = prior_result, exception_kind
        gate = {"applicability": "required", "result": result}
        identifier = f"ev-{index:032x}"
        history[identifier] = {"id": identifier, "gate": name, "retained": ["original"]}
        if result != "pending":
            gate["evidence"] = identifier
        if kind is not None:
            gate["exception"] = approved_exception(kind)
        gates[name] = gate
    record = {"gates": gates, "evidence": {"version": 1, "items": history},
              "commits": [{"id": "a" * 40, "gates": ["domain"]}],
              "artifact_reviews": {"README": {"result": "unchanged"}},
              "unrelated": {"nested": ["preserve"]}}
    if schema is not None:
        record["schema_version"] = schema
    if not missing_metrics:
        record["metrics"] = {"gate_failure_count": 5, "gate_reopen_count": 11,
                             "remediation_round_count": 7, "unrelated_count": 13}
    return record


@pytest.mark.parametrize("schema", [None, 1, 2, 3, 4, 5, 6],
                         ids=["schema-less", "schema-1", "schema-2", "schema-3",
                              "schema-4", "schema-5", "schema-6"])
@pytest.mark.parametrize("selected", ["domain", "refactor", "maintain_retire"])
@pytest.mark.parametrize("prior_result,exception_kind,reopen_on,failure_on,remediation_on", PRIOR_CASES)
@pytest.mark.parametrize("outcome", ["pending", "passed", "failed", "unavailable"])
@pytest.mark.parametrize("supply_evidence", [False, True], ids=["default-evidence", "new-evidence"])
@pytest.mark.parametrize("missing_metrics", [False, True], ids=["existing-metrics", "default-metrics"])
def test_gate_result_matches_contract_and_is_idempotent(
        isolated_policy, schema, selected, prior_result, exception_kind,
        reopen_on, failure_on, remediation_on, outcome, supply_evidence, missing_metrics):
    record = policy_record(schema, selected, prior_result, exception_kind, missing_metrics)
    expected = copy.deepcopy(record)
    selected_expected = expected["gates"][selected]
    selected_expected["result"] = outcome
    selected_expected.pop("exception", None)
    if supply_evidence:
        selected_expected["evidence"] = "ev-new"
    elif outcome == "pending":
        selected_expected.pop("evidence", None)

    reopened = LATER_SUCCESSES[selected] if schema is not None and outcome in reopen_on else ()
    for name in reopened:
        expected["gates"][name] = {"applicability": "required", "result": "pending"}
    counters = expected.setdefault("metrics", {
        "gate_failure_count": 0, "gate_reopen_count": 0, "remediation_round_count": 0,
    })
    counters["gate_reopen_count"] += len(reopened)
    counters["gate_failure_count"] += int(outcome in failure_on)
    counters["remediation_round_count"] += int(outcome in remediation_on)

    if supply_evidence:
        isolated_policy.apply_gate_result(record, selected, outcome, "ev-new")
    else:
        isolated_policy.apply_gate_result(record, selected, outcome)
    assert record == expected

    # Repeating the same result cannot count another failure, repair, or reopening.
    # Explicit None also characterizes the omitted evidence argument's default.
    isolated_policy.apply_gate_result(record, selected, outcome, "ev-new" if supply_evidence else None)
    assert record == expected
