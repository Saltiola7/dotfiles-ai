"""Bounded private records and completed-request evidence remain replayable."""

import hashlib
import json
from pathlib import Path

import pytest

from test_continuous_validation import (
    ADAPTER, comparison_observation, configured, git, private_json, request, runner, worktree,
)


def sized_record(size, character="x"):
    """Construct a JSON value of an independently calculated on-disk size."""
    overhead = len(json.dumps({"value": ""}, sort_keys=True,
                              separators=(",", ":"), ensure_ascii=True).encode()) + 1
    unit_size = len(json.dumps(character, ensure_ascii=True).encode()) - 2
    units, remainder = divmod(size - overhead, unit_size)
    return {"value": character * units + "x" * remainder}


def journal_path(value, payload):
    return Path(value["state_dir"]) / "requests" / (payload["request_id"] + ".json")


def observation_path(value, observation):
    return Path(value["state_dir"]) / "observations" / (observation["id"] + ".json")


def refuse_execution(monkeypatch):
    from continuous_validation import feedback

    def unexpected(*args, **kwargs):
        pytest.fail("a retained request must not execute adapters or feedback again")

    monkeypatch.setattr(runner, "adapter_call", unexpected)
    monkeypatch.setattr(feedback, "deliver", unexpected)


def assert_unavailable_query(result):
    assert result["schema_version"] == 1
    assert result["status"] == "unavailable"
    assert result["new_execution"] is False
    assert result["observations"] == []
    assert result["advisory"] is True


def completed_reference_journal(path, value, payload, result):
    """Build the specified private format independently from its writer."""
    patterns = ["**", value["adapter"]]
    references = []
    for observation in result["observations"]:
        references.append({
            **{name: observation[name] for name in (
                "id", "request_id", "snapshot_id", "generation", "check_id")},
            "sha256": hashlib.sha256(runner.canonical(observation)).hexdigest(),
        })
    return {
        "schema_version": 1, "storage_version": 2, "kind": "completed",
        "request_digest": runner.digest(payload),
        "enrollment_digest": runner.digest(runner.read_private(path)),
        "patterns": patterns,
        "head": git(Path(value["worktree"]), "rev-parse", "HEAD"),
        "files_digest": runner.digest(runner.inventory(Path(value["worktree"]), patterns)),
        "result": {name: item for name, item in result.items() if name != "observations"},
        "observation_refs": references,
        "observation_order_digest": runner.read_private(
            journal_path(value, payload))["observation_order_digest"],
    }


@pytest.mark.parametrize("character", ["x", "é"])
def test_private_write_includes_newline_in_exact_bound_and_preserves_rejected_replacement(
        tmp_path, monkeypatch, character):
    monkeypatch.setattr(runner, "MAX_PRIVATE_RECORD", 256)
    path = tmp_path / "private" / "record.json"
    exact = sized_record(256, character)
    runner.write_private(path, exact)
    before = path.read_bytes()
    assert len(before) == 256
    assert before.endswith(b"\n")
    assert runner.read_private(path) == exact
    assert path.stat().st_mode & 0o077 == 0

    overflow = sized_record(257, character)
    with pytest.raises(runner.ValidationError):
        runner.write_private(path, overflow)
    assert path.read_bytes() == before
    assert runner.read_private(path) == exact
    assert sorted(item.name for item in path.parent.iterdir()) == ["record.json"]


def test_private_write_refuses_nan_without_replacing_readable_record(tmp_path):
    path = tmp_path / "private" / "record.json"
    runner.write_private(path, {"retained": True})
    before = path.read_bytes()
    with pytest.raises(runner.ValidationError, match="non_json_value"):
        runner.write_private(path, {"value": float("nan")})
    assert path.read_bytes() == before
    assert sorted(item.name for item in path.parent.iterdir()) == ["record.json"]


def test_complete_observation_bound_includes_trailing_newline(tmp_path):
    observation = comparison_observation(tmp_path, runtime={"fixture_padding": ""})
    overhead = len(json.dumps(observation, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=True).encode()) + 1
    observation["runtime"]["fixture_padding"] = "x" * (runner.MAX_JSON - overhead)
    assert len(runner.canonical(observation)) + 1 == runner.MAX_JSON
    assert runner.validate_observation(observation) == observation
    observation["runtime"]["fixture_padding"] += "x"
    with pytest.raises(runner.ValidationError):
        runner.validate_observation(observation)


def test_safe_oversized_legacy_journal_is_recovery_required_without_execution(
        configured, monkeypatch):
    path, value = configured
    payload = {**request(path), "request_id": "oversized-retained-query"}
    runner.private_dir(Path(value["state_dir"]))
    record = journal_path(value, payload)
    private_json(record, {"legacy": True})
    # The unread body deliberately makes no validity claim. Size alone must not
    # allow an existing ID to become new work or authorize journal replacement.
    record.write_bytes(b" " * (runner.MAX_PRIVATE_RECORD + 1))
    before = hashlib.sha256(record.read_bytes()).hexdigest()
    original_read_text = Path.read_text

    def read_text(candidate, *args, **kwargs):
        if candidate == record:
            pytest.fail("oversized journal body must not be loaded")
        return original_read_text(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    refuse_execution(monkeypatch)
    result = runner.run_request(payload)
    assert_unavailable_query(result)
    assert result["error_code"] == "request_journal_recovery_required"
    assert hashlib.sha256(record.read_bytes()).hexdigest() == before
    assert not (Path(value["state_dir"]) / "observations").exists()


def install_large_adapter(path, value):
    source = ADAPTER.replace(
        "[check('quick','cheap'),check('slow','expensive')]",
        "[check('large-%02d'%i,'cheap') for i in range(10)]",
    ).replace(
        "else ['quick','slow']",
        "else ['large-%02d'%i for i in range(10)]",
    ).replace(
        "'runtime':{'python':platform.python_version()}",
        "'runtime':{'python':platform.python_version(),'fixture_padding':'x'*900000}",
    )
    adapter = Path(value["worktree"]) / value["adapter"]
    adapter.write_text(source)
    private_json(path, {**value, "adapter_digest": hashlib.sha256(source.encode()).hexdigest()})


def test_ten_large_observations_replay_from_bounded_journal_without_execution(
        configured, monkeypatch):
    path, value = configured
    install_large_adapter(path, value)
    payload = {**request(path, "checkpoint"), "request_id": "large-completed-query"}
    first = runner.run_request(payload)
    assert first["status"] == "passed"
    assert len(first["observations"]) == 10
    for observation in first["observations"]:
        assert runner.validate_observation(observation) == observation
        assert len(runner.canonical(observation)) + 1 <= runner.MAX_JSON
        assert runner.read_private(observation_path(value, observation)) == observation
    assert sum(len(runner.canonical(item)) + 1 for item in first["observations"]) > runner.MAX_PRIVATE_RECORD

    record = journal_path(value, payload)
    stored_bytes = record.read_bytes()
    assert len(stored_bytes) <= runner.MAX_PRIVATE_RECORD
    stored = json.loads(stored_bytes)
    assert type(stored.get("storage_version")) is int
    assert "fixture_padding" not in stored_bytes.decode()
    for metadata in Path(value["state_dir"]).glob("snapshot-*.json"):
        metadata.unlink()
    before_files = {str(item.relative_to(value["state_dir"]))
                    for item in Path(value["state_dir"]).rglob("*")}
    refuse_execution(monkeypatch)
    second = runner.run_request(payload)
    assert second == {**first, "coalesced_with": payload["request_id"], "new_execution": False}
    assert record.read_bytes() == stored_bytes
    assert {str(item.relative_to(value["state_dir"]))
            for item in Path(value["state_dir"]).rglob("*")} == before_files


def test_readable_legacy_inline_journal_replays_without_rewriting(configured, monkeypatch):
    path, value = configured
    payload = {**request(path, "checkpoint"), "request_id": "legacy-completed-query"}
    first = runner.run_request(payload)
    assert first["status"] == "passed"
    patterns = ["**", value["adapter"]]
    legacy = {
        "schema_version": 1,
        "request_digest": runner.digest(payload),
        "enrollment_digest": runner.digest(runner.read_private(path)),
        "patterns": patterns,
        "files": runner.inventory(Path(value["worktree"]), patterns),
        "head": git(Path(value["worktree"]), "rev-parse", "HEAD"),
        "result": first,
    }
    record = private_json(journal_path(value, payload), legacy)
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    second = runner.run_request(payload)
    assert second == {**first, "coalesced_with": payload["request_id"], "new_execution": False}
    assert record.read_bytes() == before


def test_unknown_private_journal_version_is_unavailable_without_rewriting(configured, monkeypatch):
    path, value = configured
    payload = {**request(path, "checkpoint"), "request_id": "unknown-storage-query"}
    assert runner.run_request(payload)["status"] == "passed"
    record = journal_path(value, payload)
    stored = runner.read_private(record)
    stored["storage_version"] = 999
    private_json(record, stored)
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    result = runner.run_request(payload)
    assert_unavailable_query(result)
    assert record.read_bytes() == before


def test_independently_encoded_reference_journal_replays(configured, monkeypatch):
    path, value = configured
    payload = {**request(path, "checkpoint"), "request_id": "reference-format-query"}
    first = runner.run_request(payload)
    assert first["status"] == "passed"
    stored = completed_reference_journal(path, value, payload, first)
    record = private_json(journal_path(value, payload), stored)
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    result = runner.run_request(payload)
    assert result == {**first, "coalesced_with": payload["request_id"], "new_execution": False}
    assert record.read_bytes() == before


@pytest.mark.parametrize("corruption", [
    "duplicate", "reordered", "digest", "request_id", "snapshot_id",
    "generation", "check_id", "summary",
])
def test_replay_refuses_malformed_reference_identity_order_or_summary(
        configured, monkeypatch, corruption):
    path, value = configured
    payload = {**request(path, "checkpoint"), "request_id": "damaged-reference-query"}
    first = runner.run_request(payload)
    assert first["status"] == "passed"
    stored = completed_reference_journal(path, value, payload, first)
    reference = stored["observation_refs"][0]
    if corruption == "duplicate":
        stored["observation_refs"][1] = dict(reference)
    elif corruption == "reordered":
        stored["observation_refs"].reverse()
    elif corruption == "digest":
        reference["sha256"] = "0" * 64
    elif corruption == "request_id":
        reference["request_id"] = "other-request"
    elif corruption == "snapshot_id":
        reference["snapshot_id"] = "0" * 64
    elif corruption == "generation":
        reference["generation"] += 1
    elif corruption == "check_id":
        reference["check_id"] = "other-check"
    else:
        stored["result"]["status"] = "unsupported-result"
    record = private_json(journal_path(value, payload), stored)
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    result = runner.run_request(payload)
    assert_unavailable_query(result)
    assert record.read_bytes() == before


@pytest.mark.parametrize("corruption", ["missing", "changed", "swapped", "mode", "symlink", "hardlink"])
def test_replay_refuses_missing_changed_or_unsafe_observation_evidence(
        configured, monkeypatch, corruption):
    path, value = configured
    payload = {**request(path, "checkpoint"), "request_id": "damaged-completed-query"}
    first = runner.run_request(payload)
    assert first["status"] == "passed"
    left, right = [observation_path(value, item) for item in first["observations"]]
    if corruption == "missing":
        left.unlink()
    elif corruption == "changed":
        changed = runner.read_private(left)
        changed["runtime"]["fixture_change"] = "retained identity was modified"
        private_json(left, changed)
    elif corruption == "swapped":
        left_bytes, right_bytes = left.read_bytes(), right.read_bytes()
        left.write_bytes(right_bytes)
        right.write_bytes(left_bytes)
    elif corruption == "mode":
        left.chmod(0o644)
    elif corruption == "symlink":
        left.unlink()
        left.symlink_to(right)
    else:
        (left.parent / "same-inode.json").hardlink_to(left)
    record = journal_path(value, payload)
    before = record.read_bytes()
    before_names = sorted(item.name for item in left.parent.iterdir())
    refuse_execution(monkeypatch)
    second = runner.run_request(payload)
    assert_unavailable_query(second)
    assert record.read_bytes() == before
    assert sorted(item.name for item in left.parent.iterdir()) == before_names


def test_oversized_feedback_preserves_durable_observation_and_replay(configured, monkeypatch):
    from continuous_validation import feedback

    path, value = configured
    (Path(value["worktree"]) / "source.py").write_text("fail = True\n")
    payload = {**request(path), "request_id": "feedback-overflow-query"}
    delivered = []

    def deliver(enrollment, observation, **kwargs):
        durable = runner.read_private(observation_path(value, observation))
        assert runner.validate_observation(durable) == durable
        delivered.append(durable)
        return {"status": "accepted", "fixture_padding": "x" * runner.MAX_JSON}

    monkeypatch.setattr(feedback, "deliver", deliver)
    first = runner.run_request(payload)
    assert first["status"] == "failed"
    assert len(delivered) == 1
    assert first["observations"] == delivered
    assert "feedback" not in first["observations"][0]
    assert runner.read_private(observation_path(value, delivered[0])) == delivered[0]
    refuse_execution(monkeypatch)
    second = runner.run_request(payload)
    assert second["new_execution"] is False
    assert second["observations"] == delivered
