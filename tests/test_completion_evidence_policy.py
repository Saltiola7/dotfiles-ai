"""Trusted plan policy validation; pure contracts require no provider or checkout."""

import copy
import importlib.machinery
import importlib.util

import pytest
from hypothesis import given, settings, strategies as st
import test_dbsctrctl as harness


@pytest.fixture(scope="module")
def core():
    loader = importlib.machinery.SourceFileLoader("evidence_policy_under_test", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def policy():
    return {
        "schema_version": 1,
        "requirements": {
            "EXAMPLE-001": {"revision": "1", "depends_on": [], "gates": ["contract"]},
            "EXAMPLE-002": {"revision": "1", "depends_on": ["EXAMPLE-001"], "gates": ["test_driven_implementation"]},
        },
        "gates": {
            "contract": {
                "authority": "project-contract", "argv": ["python3", "scripts/check.py"],
                "inputs": ["src", "scripts/check.py"], "environment": ["PROJECT_TEST_MODE"],
                "toolchain_paths": ["uv.lock"], "scope_complete": True,
            },
            "test_driven_implementation": {
                "authority": "project-tests", "argv": ["python3", "scripts/test.py"],
                "inputs": ["src", "tests"], "environment": [],
                "toolchain_paths": [], "scope_complete": True,
            },
        },
    }


def gates(core):
    return {name: {"applicability": "required"} for name in core.GATES}


def test_exact_approved_policy_is_deterministic_without_mutation(core):
    selected = policy()
    before = copy.deepcopy(selected)
    assert core.validate_evidence_policy(selected, gates(core), ["EXAMPLE-001", "EXAMPLE-002"]) == selected
    assert selected == before


@pytest.mark.parametrize("problem", [
    "unknown_version", "boolean_version", "unknown_field", "missing_requirement", "extra_requirement",
    "empty_revision", "missing_revision", "unknown_dependency", "duplicate_dependency", "cycle",
    "unknown_gate", "unmapped_requirement", "duplicate_gate", "nonrequired_gate", "incomplete_scope",
    "empty_inputs", "duplicate_inputs", "absolute_input", "traversal_input", "pathspec_input",
    "glob_input", "secret_input", "invalid_environment", "duplicate_environment", "empty_argv",
    "nul_argument", "secret_argument", "unknown_declaration_field", "runtime_without_policy",
    "zero_freshness", "boolean_freshness", "unbounded_probe", "unknown_runtime_field", "null_authority",
    "unsupported_encoding",
])
def test_invalid_policy_never_becomes_reuse_authority(core, problem):
    value = policy()
    app = gates(core)
    requirement = value["requirements"]["EXAMPLE-001"]
    declaration = value["gates"]["contract"]
    if problem == "unknown_version":
        value["schema_version"] = 2
    elif problem == "boolean_version":
        value["schema_version"] = True
    elif problem == "unknown_field":
        value["implicit_approval"] = True
    elif problem == "missing_requirement":
        del value["requirements"]["EXAMPLE-002"]
    elif problem == "extra_requirement":
        value["requirements"]["EXAMPLE-003"] = copy.deepcopy(requirement)
    elif problem == "empty_revision":
        requirement["revision"] = ""
    elif problem == "missing_revision":
        del requirement["revision"]
    elif problem == "unknown_dependency":
        requirement["depends_on"] = ["EXAMPLE-999"]
    elif problem == "duplicate_dependency":
        value["requirements"]["EXAMPLE-002"]["depends_on"] *= 2
    elif problem == "cycle":
        requirement["depends_on"] = ["EXAMPLE-002"]
    elif problem == "unknown_gate":
        requirement["gates"] = ["invented_gate"]
    elif problem == "unmapped_requirement":
        requirement["gates"] = []
    elif problem == "duplicate_gate":
        requirement["gates"] *= 2
    elif problem == "nonrequired_gate":
        app["contract"] = {"applicability": "not_applicable"}
    elif problem == "incomplete_scope":
        declaration["scope_complete"] = False
    elif problem == "empty_inputs":
        declaration["inputs"] = []
    elif problem == "duplicate_inputs":
        declaration["inputs"] *= 2
    elif problem in {"absolute_input", "traversal_input", "pathspec_input", "glob_input", "secret_input"}:
        declaration["inputs"] = [{
            "absolute_input": "/private/source", "traversal_input": "src/../outside", "pathspec_input": ":(top)src",
            "glob_input": "src/**", "secret_input": ".env",
        }[problem]]
    elif problem == "invalid_environment":
        declaration["environment"] = ["invalid=name"]
    elif problem == "duplicate_environment":
        declaration["environment"] *= 2
    elif problem == "empty_argv":
        declaration["argv"] = []
    elif problem == "nul_argument":
        declaration["argv"] = ["python3", "bad\0argument"]
    elif problem == "secret_argument":
        declaration["argv"] = ["python3", "op://private/item/value"]
    elif problem == "unknown_declaration_field":
        declaration["trust_me"] = True
    elif problem == "null_authority":
        declaration["authority"] = None
    elif problem == "unsupported_encoding":
        declaration["authority"] = "invalid-\ud800"
    else:
        declaration["runtime"] = {"probe_argv": ["python3", "scripts/probe.py"],
                                  "probe_timeout_seconds": 20, "max_age_seconds": 3600}
        if problem == "runtime_without_policy":
            value["gates"]["deploy"] = {key: item for key, item in declaration.items() if key != "runtime"}
        elif problem == "zero_freshness":
            declaration["runtime"]["max_age_seconds"] = 0
        elif problem == "boolean_freshness":
            declaration["runtime"]["max_age_seconds"] = True
        elif problem == "unbounded_probe":
            declaration["runtime"]["probe_timeout_seconds"] = 61
        else:
            declaration["runtime"]["trust_me"] = True
    before = copy.deepcopy(value)
    with pytest.raises(RuntimeError):
        core.validate_evidence_policy(value, app, ["EXAMPLE-001", "EXAMPLE-002"])
    assert value == before


def test_gate_local_projection_ignores_unrelated_policy_but_not_prerequisites(core):
    original = policy()
    digest = core.evidence_gate_policy_digest(original, "contract")
    unrelated = copy.deepcopy(original)
    unrelated["requirements"]["EXAMPLE-002"]["revision"] = "2"
    unrelated["gates"]["test_driven_implementation"]["inputs"].append("other")
    assert core.evidence_gate_policy_digest(unrelated, "contract") == digest
    affected = copy.deepcopy(original)
    affected["requirements"]["EXAMPLE-001"]["revision"] = "2"
    assert core.evidence_gate_policy_digest(affected, "contract") != digest
    assert core.evidence_gate_policy_digest(affected, "test_driven_implementation") != core.evidence_gate_policy_digest(
        original, "test_driven_implementation")


@settings(max_examples=24, deadline=None)
@given(st.permutations(["src", "scripts/check.py", "tests"]), st.integers(min_value=1, max_value=10_000))
def test_set_order_and_unrelated_semantic_revisions_cannot_invalidate_gate(core, inputs, revision):
    original = policy()
    original["gates"]["contract"]["inputs"] = ["src", "scripts/check.py", "tests"]
    changed = copy.deepcopy(original)
    changed["gates"]["contract"]["inputs"] = list(inputs)
    changed["requirements"]["EXAMPLE-002"]["revision"] = str(revision)
    assert core.evidence_gate_policy_digest(changed, "contract") == core.evidence_gate_policy_digest(original, "contract")
