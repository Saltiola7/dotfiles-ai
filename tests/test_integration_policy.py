"""Versioned repository delivery consent never infers live coordinator authority."""
import copy
import json
from pathlib import Path
import subprocess

import pytest
from test_worktrunk_native_policy import policy, storage_home


TARGET = "refs/heads/main"
CONTROL = "refs/heads/integration-control"


def coordinator(**changes):
    value = {
        "schema_version": 1, "enabled": True, "protocol_version": 2,
        "strategy": "rebase", "remote_repository": "fixture/project",
        "target_ref": TARGET, "control_ref": CONTROL,
        "policy_path": ".github/integration-policy.json", "policy_digest": "a" * 64,
        "guarded_refresh": False,
    }
    value.update(changes)
    return value


def delivery(**changes):
    value = {
        "schema_version": 2, "enabled": False, "mode": "ordinary", "role": "integrator",
        "remote": "origin", "targets": [TARGET], "mapping_path": "docs/delivery.json",
        "allow_unrelated_pending": False, "delete_remote_branch": False,
    }
    value.update(changes)
    return value


@pytest.fixture
def repository_options(policy, storage_home, monkeypatch):
    primary = storage_home.parent / "repository"
    primary.mkdir()
    monkeypatch.setattr(policy, "repository", lambda p: (p / ".git", [p], "fixture"))
    return {"schema_version": 1, "repositories": [{"repository": str(primary)}]}


def test_schema1_delivery_resolves_verbatim(policy, storage_home, repository_options):
    legacy = delivery(schema_version=1, enabled=True, mode="admin", role="operator")
    repository_options["repositories"][0]["delivery"] = legacy
    expected = copy.deepcopy(legacy)
    resolved = policy.resolve(repository_options, storage_home)
    assert resolved["repositories"][0]["delivery"] == expected
    assert legacy == expected
    with pytest.raises(ValueError):
        policy.consent("delivery", {**legacy, "coordinator": coordinator()})


def test_schema2_does_not_materialize_coordinator_or_enablement(
        policy, storage_home, repository_options):
    repository_options["repositories"][0]["delivery"] = {"schema_version": 2}
    selected = policy.resolve(repository_options, storage_home)["repositories"][0]["delivery"]
    assert selected == {"schema_version": 2}
    assert not selected.get("enabled", False)
    assert "coordinator" not in selected


@pytest.mark.parametrize("extra", [{}, {"enabled": False}, {"guarded_refresh": False},
                                  {"strategy": "rebase"}])
def test_disabled_nested_policy_can_be_minimal_and_is_not_rewritten(
        policy, storage_home, repository_options, extra):
    nested = {"schema_version": 1, "protocol_version": 2, **extra}
    value = delivery(coordinator=nested)
    repository_options["repositories"][0]["delivery"] = value
    expected = copy.deepcopy(value)
    selected = policy.resolve(repository_options, storage_home)["repositories"][0]["delivery"]
    assert selected == expected
    assert value == expected
    assert not selected["coordinator"].get("enabled", False)


@pytest.mark.parametrize("outer_enabled", [False, True])
def test_complete_binding_preserves_staged_and_enabled_outer_consent(
        policy, storage_home, repository_options, outer_enabled):
    value = delivery(enabled=outer_enabled, coordinator=coordinator())
    repository_options["repositories"][0]["delivery"] = value
    selected = policy.resolve(repository_options, storage_home)["repositories"][0]["delivery"]
    assert selected == value
    assert selected["enabled"] is outer_enabled
    # Parsing validates declarations; the consumer requires BOTH live switches.
    assert selected["coordinator"]["enabled"] is True


def test_enabled_binding_can_omit_rebase_default(policy):
    nested = coordinator()
    nested.pop("strategy")
    policy.consent("delivery", delivery(coordinator=nested))
    assert "strategy" not in nested


@pytest.mark.parametrize("field", ["remote_repository", "target_ref", "control_ref",
                                   "policy_path", "policy_digest"])
def test_enabled_coordinator_requires_every_binding(policy, field):
    nested = coordinator()
    nested.pop(field)
    with pytest.raises(ValueError):
        policy.consent("delivery", delivery(coordinator=nested))


@pytest.mark.parametrize("changes", [
    {"schema_version": True}, {"schema_version": 2}, {"protocol_version": True},
    {"protocol_version": 1}, {"enabled": 1}, {"guarded_refresh": "yes"},
    {"strategy": "squash"}, {"remote_repository": "https://example.invalid/fixture/project"},
    {"remote_repository": "fixture/project/extra"}, {"remote_repository": "fixture/../project"},
    {"target_ref": "refs/remotes/origin/main"}, {"target_ref": "refs/heads/other"},
    {"target_ref": "refs/heads/main*"}, {"control_ref": TARGET},
    {"control_ref": "refs/heads/control..branch"}, {"policy_digest": "A" * 64},
    {"policy_digest": "a" * 63}, {"policy_digest": True},
    {"policy_path": "../policy.json"}, {"policy_path": "/policy.json"},
    {"policy_path": ".dbsctr/policy.json"}, {"policy_path": "policy.py"},
    {"policy_path": "policy\n.json"}, {"unknown": False},
])
@pytest.mark.parametrize("enabled", [False, True])
def test_supplied_coordinator_fields_fail_closed_even_when_disabled(policy, changes, enabled):
    with pytest.raises((ValueError, subprocess.SubprocessError)):
        policy.consent("delivery", delivery(coordinator=coordinator(**{"enabled": enabled, **changes})))


@pytest.mark.parametrize("kind", ["preservation", "feedback"])
def test_schema2_extension_is_delivery_only(policy, kind):
    with pytest.raises(ValueError):
        policy.consent(kind, {"schema_version": 2})


def test_generated_v2_policy_roundtrips_and_binds_activation_changes(
        policy, storage_home, repository_options, monkeypatch):
    repository_options["repositories"][0]["delivery"] = delivery(coordinator=coordinator())
    native_run = policy.run
    helper = Path(policy.__file__).read_bytes()
    commit = ["b" * 40]

    def selected_source(*args, **kwargs):
        if args[:2] == ("git", "status"):
            return b""
        if args[:2] == ("git", "rev-parse"):
            return commit[0].encode()
        if args[:2] == ("git", "show"):
            return helper
        return native_run(*args, **kwargs)

    monkeypatch.setattr(policy, "run", selected_source)
    monkeypatch.setattr(policy, "worktrunk_version", lambda: "wt v0.80.0")
    old = policy.render(storage_home, storage_home, repository_options, {})["policy"]
    decoded = json.loads(json.dumps(old), object_pairs_hook=policy.unique)
    policy.validate_document(decoded, storage_home)
    assert decoded == old
    saved = policy.snapshot(old, storage_home)

    commit[0] = "c" * 40
    fresh = policy.render(storage_home, storage_home, repository_options, {},
                          previous_policy=old)["policy"]
    policy.verify_snapshot(fresh, saved, storage_home)
    assert fresh["activation_binding"] == old["activation_binding"]

    repository_options["repositories"][0]["delivery"]["coordinator"]["policy_digest"] = "d" * 64
    changed = policy.render(storage_home, storage_home, repository_options, {},
                            previous_policy=fresh)["policy"]
    assert changed["activation_binding"]["semantic_digest"] != fresh["activation_binding"]["semantic_digest"]
    assert "legacy_policy_digest" not in changed["activation_binding"]
    with pytest.raises(ValueError):
        policy.verify_snapshot(changed, saved, storage_home)
