"""Native execution metadata does not rewrite historical identity or gate evidence."""
import copy
import importlib.machinery
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def core():
    path = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
    loader = importlib.machinery.SourceFileLoader("native_workspace_records", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def record(origin="registered", schema=5):
    before = "a" * 64
    return {"schema_version": schema, "cycle_id": "cycle-1",
            "runtime": {"historical": "retained"}, "gates": {"test_driven_implementation": {"result": "failed"}},
            "execution": {"schema_version": 1, "mode": "native_workspace", "origin": origin,
                "attribution": {"status": "unavailable", "reason": "native_identity_not_collected"},
                "adoption": None if origin == "registered" else {
                    "before_sha256": before, "state_digest": "b" * 64,
                    "record_backup": f"dbsctr/migrations/cycle-1.{before}.native-before.json"}}}


def test_legacy_record_is_not_implicitly_native(core):
    assert core.native_workspace_execution({"schema_version": 5}) is False


@pytest.mark.parametrize("schema", [3, 4, 5])
def test_adopted_metadata_preserves_history_and_failed_gates(core, schema):
    value = record("adopted", schema)
    before = copy.deepcopy(value)
    assert core.native_workspace_execution(value) is True
    assert value == before


def test_registered_metadata_has_no_fabricated_attribution(core):
    assert core.native_workspace_execution(record()) is True


@pytest.mark.parametrize("case", ["unknown_version", "invalid_origin", "false_identity", "missing_backup",
                                  "foreign_backup", "traversal", "invalid_digest", "extra_field", "legacy_registration"])
def test_invalid_execution_metadata_refuses(core, case):
    value = record("adopted")
    execution = value["execution"]
    if case == "unknown_version":
        execution["schema_version"] = 2
    elif case == "invalid_origin":
        execution["origin"] = "imported"
    elif case == "false_identity":
        execution["attribution"] = {"status": "available", "session_id": "borrowed"}
    elif case == "missing_backup":
        execution["adoption"] = None
    elif case == "foreign_backup":
        execution["adoption"]["record_backup"] = execution["adoption"]["record_backup"].replace("cycle-1", "cycle-2")
    elif case == "traversal":
        execution["adoption"]["record_backup"] = "../outside.json"
    elif case == "invalid_digest":
        execution["adoption"]["before_sha256"] = "not-a-digest"
    elif case == "extra_field":
        execution["writer"] = "self"
    else:
        value = record("registered", 3)
    with pytest.raises(RuntimeError, match="native workspace execution"):
        core.native_workspace_execution(value)
