"""Synthetic source reconciliation behavior; no provider or vault data required."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE = Path(__file__).resolve().parents[1] / "dot_local/share/pm-kernel/obsidian_sync.py"
spec = importlib.util.spec_from_file_location("obsidian_sync_test", MODULE)
sync = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sync
spec.loader.exec_module(sync)


def record(identity="source-1", title="Original", body="Body", **properties):
    return {
        "path": f"Records/entity=issue/{identity}.md",
        "metadata": {
            "schema_version": 1,
            "entity_type": "issue",
            "id": identity,
            "title": title,
            "source_system": "linear",
            "source_id": identity,
            "source_url": None,
            **properties,
        },
        "body": body,
    }


def bundle(*records, scope="linear:workspace"):
    return {
        "schema_version": 1,
        "source_system": "linear",
        "scope": scope,
        "captured_at": "2026-10-27T00:00:00Z",
        "complete": True,
        "records": list(records),
    }


def reader(data):
    return json.loads(data)


def renderer(value):
    return (json.dumps({k: value[k] for k in ("metadata", "body")}, sort_keys=True) + "\n").encode()


def write(vault, value):
    path = vault / value["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(renderer(value))


@pytest.fixture
def paths(tmp_path):
    vault = tmp_path / "vault"
    for name in ("Records", "Knowledge"):
        (vault / name).mkdir(parents=True)
    state = tmp_path / "state"
    return vault, state / "linear-baseline.json", state


def apply(paths, incoming, baseline=None, validator=lambda _: []):
    vault, baseline_path, state = paths
    plan = sync.plan_sync(vault, incoming, baseline, reader)
    result = sync.apply_sync(vault, plan, baseline_path, state, renderer, validator)
    return plan, result


def test_first_pull_retains_local_notes_and_repeat_is_noop(paths):
    vault, baseline_path, _ = paths
    local = record("local-1", source_system="local", source_id=None)
    write(vault, local)
    incoming = bundle(record())
    plan, result = apply(paths, incoming)
    assert len(plan.writes) == 1 and result["written"] == 1
    assert reader((vault / local["path"]).read_bytes())["metadata"]["source_system"] == "local"
    baseline = json.loads(baseline_path.read_text())
    plan, result = apply(paths, incoming, baseline)
    assert not plan.writes and result["written"] == 0


def test_threeway_independent_changes_and_equal_changes_converge():
    base = record(priority=3)
    local = record(title="Local title", priority=3)
    remote = record(priority=2)
    merged, conflicts = sync.merge_record(base, local, remote)
    assert conflicts == []
    assert merged["metadata"]["title"] == "Local title"
    assert merged["metadata"]["priority"] == 2
    same = record(title="Same", priority=3)
    assert sync.merge_record(base, same, same)[1] == []


def test_threeway_missing_property_and_body_conflict():
    base = record(priority=3)
    local = record(body="Local body", priority=3)
    remote = record(body="Remote body")
    merged, conflicts = sync.merge_record(base, local, remote)
    assert conflicts == ["body"]
    assert "priority" not in merged["metadata"]


def test_threeway_preserves_property_types():
    base = record(custom=1)
    local = record(custom=True)
    remote = record(custom=2)
    assert sync.merge_record(base, local, remote)[1] == ["custom"]


def test_conflict_stops_entire_batch_and_reports_keys_only(paths):
    vault, baseline_path, _ = paths
    original = bundle(record(), record("source-2"))
    apply(paths, original)
    baseline = json.loads(baseline_path.read_text())
    write(vault, record(body="Private local prose"))
    incoming = bundle(record(body="Private remote prose"), record("source-2", title="Remote"))
    plan = sync.plan_sync(vault, incoming, baseline, reader)
    assert plan.conflicts[0]["key"] == "body"
    assert "Private" not in json.dumps(plan.summary())
    before = {p: p.read_bytes() for p in vault.rglob("*.md")}
    with pytest.raises(sync.SyncFailure, match="conflicts"):
        sync.apply_sync(vault, plan, baseline_path, paths[2], renderer, lambda _: [])
    assert before == {p: p.read_bytes() for p in vault.rglob("*.md")}


def test_local_only_changes_survive_and_remote_omissions_retained(paths):
    vault, baseline_path, _ = paths
    original = bundle(record(), record("source-2"))
    apply(paths, original)
    baseline = json.loads(baseline_path.read_text())
    local = record(title="Local title", custom="Local property")
    write(vault, local)
    plan, _ = apply(paths, bundle(record()), baseline)
    assert plan.retained == ["Records/entity=issue/source-2.md"]
    assert reader((vault / local["path"]).read_bytes())["metadata"]["custom"] == "Local property"
    assert len(json.loads(baseline_path.read_text())["records"]) == 2


def test_locally_deleted_baseline_record_is_conflict(paths):
    vault, baseline_path, _ = paths
    original = bundle(record(), record("source-2"))
    apply(paths, original)
    baseline = json.loads(baseline_path.read_text())
    (vault / record()["path"]).unlink()
    plan = sync.plan_sync(vault, bundle(record("source-2")), baseline, reader)
    assert any(c["reason"] == "local_deleted" for c in plan.conflicts)


def test_source_identity_and_path_cannot_be_reassigned(paths):
    vault, baseline_path, _ = paths
    original = bundle(record())
    apply(paths, original)
    baseline = json.loads(baseline_path.read_text())
    changed = record(source_id="different")
    assert sync.plan_sync(vault, bundle(changed), baseline, reader).conflicts
    moved = record()
    moved["path"] = "Records/entity=issue/moved.md"
    assert sync.plan_sync(vault, bundle(moved), baseline, reader).conflicts


def test_full_vault_identity_collision_rejected(paths):
    vault, _, _ = paths
    local = record(source_system="local", source_id=None)
    local["path"] = "Knowledge/local.md"
    write(vault, local)
    assert sync.plan_sync(vault, bundle(record()), None, reader).conflicts


@pytest.mark.parametrize("path", ["../escape.md", "/absolute.md", "Views/record.md", "Records/../escape.md", "Records/a.txt", "Records//a.md", "Records/a\\b.md"])
def test_unsafe_bundle_paths_rejected(paths, path):
    value = record()
    value["path"] = path
    with pytest.raises(sync.SyncFailure, match="invalid"):
        sync.plan_sync(paths[0], bundle(value), None, reader)


@pytest.mark.parametrize("mutate", [
    lambda b: b.update(complete=False),
    lambda b: b.update(records=[]),
    lambda b: b.update(captured_at="yesterday"),
    lambda b: b["records"].append(b["records"][0]),
    lambda b: b["records"][0]["metadata"].update(nested={"bad": True}),
    lambda b: b["records"][0]["metadata"].update(values=[{"bad": True}]),
    lambda b: b["records"][0]["metadata"].update(source_system="jira"),
])
def test_malformed_bundle_rejected(paths, mutate):
    incoming = bundle(record())
    mutate(incoming)
    with pytest.raises(sync.SyncFailure, match="invalid"):
        sync.plan_sync(paths[0], incoming, None, reader)


def test_baseline_scope_mismatch_rejected(paths):
    apply(paths, bundle(record()))
    baseline = json.loads(paths[1].read_text())
    with pytest.raises(sync.SyncFailure, match="source_mismatch"):
        sync.plan_sync(paths[0], bundle(record(), scope="other"), baseline, reader)


def test_symlink_in_canonical_tree_rejected(paths, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (paths[0] / "Records/linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(sync.SyncFailure, match="unsafe"):
        sync.plan_sync(paths[0], bundle(record()), None, reader)


def test_invalid_staged_vault_leaves_source_and_baseline_unchanged(paths):
    before = list(paths[0].rglob("*.md"))
    with pytest.raises(sync.SyncFailure, match="validation_failed"):
        apply(paths, bundle(record()), validator=lambda _: ["Invalid foreign key"])
    assert list(paths[0].rglob("*.md")) == before
    assert not paths[1].exists()


def test_stage_omits_generated_symlink_and_preserves_full_records(paths, tmp_path):
    vault, _, _ = paths
    write(vault, record("local-1", source_system="local", source_id=None))
    (vault / "Data").symlink_to(tmp_path / "nonexistent", target_is_directory=True)

    def validate(stage):
        assert len(list(stage.rglob("*.md"))) == 2
        assert not (stage / "Data").exists()
        return []

    apply(paths, bundle(record()), validator=validate)


def test_unrelated_note_edit_after_plan_blocks_apply(paths):
    vault, baseline_path, state = paths
    local = record("local-1", source_system="local", source_id=None)
    write(vault, local)
    plan = sync.plan_sync(vault, bundle(record()), None, reader)
    write(vault, record("local-1", title="New edit", source_system="local", source_id=None))
    with pytest.raises(sync.SyncFailure, match="stale_plan"):
        sync.apply_sync(vault, plan, baseline_path, state, renderer, lambda _: [])
    assert not (vault / record()["path"]).exists()


def test_live_edit_during_staged_validation_blocks_apply(paths):
    vault, baseline_path, _ = paths
    local = record("local-1", source_system="local", source_id=None)
    write(vault, local)

    def validator(_stage):
        local["body"] = "Intervening edit"
        write(vault, local)
        return []

    with pytest.raises(sync.SyncFailure, match="stale_plan"):
        apply(paths, bundle(record()), validator=validator)
    assert not baseline_path.exists()
    assert not (vault / record()["path"]).exists()


def test_concurrent_baseline_change_blocks_apply(paths):
    vault, baseline_path, state = paths
    incoming = bundle(record())
    plan = sync.plan_sync(vault, incoming, None, reader)
    sync.seed_baseline(incoming, baseline_path)
    with pytest.raises(sync.SyncFailure, match="stale_baseline"):
        sync.apply_sync(vault, plan, baseline_path, state, renderer, lambda _: [])


def test_seed_create_only_and_never_reads_current_notes(paths):
    incoming = bundle(record())
    sync.seed_baseline(incoming, paths[1])
    assert json.loads(paths[1].read_text())["records"] == incoming["records"]
    with pytest.raises(sync.SyncFailure, match="baseline_exists"):
        sync.seed_baseline(incoming, paths[1])
    assert list(paths[0].rglob("*.md")) == []


def test_interrupted_apply_recovers_remaining_writes(paths, monkeypatch):
    vault, baseline_path, state = paths
    original = sync._atomic_bytes
    count = 0

    def interrupt(path, data):
        nonlocal count
        if path.is_relative_to(vault):
            count += 1
            if count == 2:
                raise OSError("simulated interruption")
        return original(path, data)

    monkeypatch.setattr(sync, "_atomic_bytes", interrupt)
    with pytest.raises(OSError, match="simulated"):
        apply(paths, bundle(record(), record("source-2")))
    assert not baseline_path.exists()
    monkeypatch.setattr(sync, "_atomic_bytes", original)
    result = sync.recover(vault, baseline_path, state)
    assert result["recovered"] is True
    assert len(list(vault.rglob("*.md"))) == 2
    assert len(json.loads(baseline_path.read_text())["records"]) == 2


def test_recovery_refuses_newer_edit_without_overwriting(paths, monkeypatch):
    vault, baseline_path, state = paths
    original = sync._atomic_bytes
    count = 0

    def interrupt(path, data):
        nonlocal count
        if path.is_relative_to(vault):
            count += 1
            if count == 2:
                raise OSError("simulated interruption")
        return original(path, data)

    monkeypatch.setattr(sync, "_atomic_bytes", interrupt)
    with pytest.raises(OSError):
        apply(paths, bundle(record(), record("source-2")))
    monkeypatch.setattr(sync, "_atomic_bytes", original)
    newer = record(title="Newer local edit")
    write(vault, newer)
    before = (vault / newer["path"]).read_bytes()
    with pytest.raises(sync.SyncFailure, match="recovery_conflict"):
        sync.recover(vault, baseline_path, state)
    assert (vault / newer["path"]).read_bytes() == before
    assert not baseline_path.exists()


def test_existing_publisher_lock_blocks_import(paths):
    import fcntl

    vault, baseline_path, state = paths
    state.mkdir()
    plan = sync.plan_sync(vault, bundle(record()), None, reader)
    with (state / "publisher.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(sync.SyncFailure, match="busy"):
            sync.apply_sync(vault, plan, baseline_path, state, renderer, lambda _: [])
    assert not baseline_path.exists()


def test_invalid_journal_path_never_writes_outside_vault(paths):
    vault, baseline_path, state = paths
    state.mkdir()
    journal = {
        "schema_version": 1, "status": "prepared",
        "vault_digest": sync._digest(str(vault.resolve())),
        "baseline_path_digest": sync._digest(str(baseline_path.resolve())),
        "files": {},
        "writes": [{"path": "../outside.md", "old": None, "new": "bmV3"}],
        "baseline_old": None,
        "baseline_new": sync._encoded(sync._json_bytes(bundle(record()))),
    }
    (state / "sync-journal.json").write_text(json.dumps(journal))
    with pytest.raises(sync.SyncFailure, match="invalid_path"):
        sync.recover(vault, baseline_path, state)
    assert not (vault.parent / "outside.md").exists()
