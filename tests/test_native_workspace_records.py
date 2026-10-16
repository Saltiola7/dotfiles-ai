"""Native execution metadata does not rewrite historical identity or gate evidence."""
import copy
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

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


@pytest.fixture
def inventory_repo(core, tmp_path, monkeypatch):
    root = tmp_path / "PRIVATE_REPOSITORY_SENTINEL"
    root.mkdir()
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                              text=True, check=True).stdout.strip()
    git("init", "-b", "main")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    (root / "tracked").write_text("fixture\n")
    git("add", "tracked")
    git("commit", "-m", "fixture")
    linked = tmp_path / "PRIVATE_WORKTREE_SENTINEL"
    git("worktree", "add", "-b", "PRIVATE_BRANCH_SENTINEL", str(linked))
    value = record()
    value.update(state="active", runtime={"adapters": {}}, worktree={
        "id": core.worktree_id(linked), "created_by_dbsctr": False,
        "git_dir": str(core.git_dir(linked).relative_to(root / ".git")),
        "locator": {"root": "cycle_worktree", "path": "."},
        "branch": "PRIVATE_BRANCH_SENTINEL"})
    records = root / ".git/dbsctr/cycles"
    records.mkdir(parents=True)
    (records / "cycle-1.json").write_text(json.dumps(value))
    monkeypatch.chdir(root)
    return root, linked, records, git


def metadata(core, root, capsys, **overrides):
    args = SimpleNamespace(**{**dict(json=True, now=False, all=False, metadata_only=True,
                                    repository=[], cursor=None), **overrides})
    core.command_worktree_list(args)
    projected = json.loads(capsys.readouterr().out)
    report = json.loads((root / ".git/dbsctr/inventory" /
                         (projected["report_id"] + ".json")).read_text())
    return projected, report


def test_metadata_includes_native_and_unmapped_without_size_or_cleanup(core, inventory_repo,
                                                                      monkeypatch, capsys):
    root, linked, records, _ = inventory_repo
    monkeypatch.setattr(core, "root_dir", lambda: root)
    def forbidden(*args, **kwargs):
        raise AssertionError("metadata must not scan data or assess deletion")
    monkeypatch.setattr(core, "worktree_bytes", forbidden)
    monkeypatch.setattr(core, "workspace_remove_check", forbidden)
    projected, report = metadata(core, root, capsys)
    assert report["schema_version"] == projected["schema_version"] == 1
    assert report["coverage"]["status"] == "complete"
    assert len(report["items"]) == 2
    item = next(x for x in report["items"] if x["path"] == str(linked))
    assert item["cycles"] == {"status": "known", "records": [{"id": "cycle-1", "state": "active"}]}
    assert item["disposition"] == "retained_active"
    assert all(x["disposition"].startswith("retained_") and "size" not in x for x in report["items"])
    assert all(e["status"] == "unknown" for e in item["evidence"].values())
    assert projected["continuation"] is None
    assert not any(s in json.dumps(projected) for s in (
        "PRIVATE_", str(root), str(linked), "cycle-1"))
    report_path = root / ".git/dbsctr/inventory" / (projected["report_id"] + ".json")
    assert report_path.stat().st_mode & 0o777 == 0o600
    assert report_path.parent.stat().st_mode & 0o777 == 0o700


def test_invalid_record_is_partial_unavailable_not_empty_or_completed(core, inventory_repo,
                                                                    monkeypatch, capsys):
    root, _, records, _ = inventory_repo
    monkeypatch.setattr(core, "root_dir", lambda: root)
    (records / "broken.json").write_text('{"schema_version":5,"schema_version":5}')
    projected, report = metadata(core, root, capsys)
    assert report["coverage"]["status"] == "partial"
    assert "cycle_records_unavailable" in report["coverage"]["reasons"]
    assert all(x["cycles"]["status"] == "unavailable" for x in report["items"])
    assert all(x["disposition"] == "retained_unknown" for x in report["items"])
    assert "broken" not in json.dumps(projected)


def test_metadata_correlation_preserves_native_branch_drift_and_legacy_record(core, inventory_repo,
                                                                          monkeypatch, capsys):
    root, linked, records, git = inventory_repo
    monkeypatch.setattr(core, "root_dir", lambda: root)
    value = json.loads((records / "cycle-1.json").read_text())
    legacy = {**value, "cycle_id": "legacy-1", "schema_version": 3}
    legacy.pop("execution")
    legacy["worktree"] = {"path": str(linked), "id": core.legacy_worktree_id(linked),
                          "branch": "PRIVATE_BRANCH_SENTINEL", "created_by_dbsctr": True}
    (records / "legacy-1.json").write_text(json.dumps(legacy))
    subprocess.run(["git", "branch", "-m", "changed"], cwd=linked, check=True)
    _, report = metadata(core, root, capsys)
    item = next(x for x in report["items"] if x["path"] == str(linked))
    assert {x["id"] for x in item["cycles"]["records"]} == {"cycle-1", "legacy-1"}
    assert "branch_changed" in item["reasons"]
    assert item["disposition"] != "eligible"


def test_metadata_repository_seed_errors_are_path_free_and_explicit(core, inventory_repo,
                                                                 monkeypatch, capsys):
    root, _, _, _ = inventory_repo
    monkeypatch.setattr(core, "root_dir", lambda: root)
    args = SimpleNamespace(json=True, now=False, all=False, metadata_only=True,
                           repository=[str(root / "PRIVATE_MISSING")], cursor=None)
    core.command_worktree_list(args)
    projected = json.loads(capsys.readouterr().out)
    assert projected["coverage"]["status"] == "unavailable"
    assert "PRIVATE" not in json.dumps(projected)


def test_metadata_pages_bind_sources_and_resume_without_path_tokens(core, inventory_repo,
                                                                 monkeypatch, capsys):
    root, _, _, _ = inventory_repo
    monkeypatch.setattr(core, "root_dir", lambda: root)
    snapshot = core.inventory_repository(root)
    sample = snapshot["members"][0]
    snapshot["members"] = [{**sample, "worktree": str(root.parent / str(n))} for n in range(105)]
    monkeypatch.setattr(core, "inventory_repository", lambda seed: snapshot)
    def item(repository, fields, records, unavailable):
        return {"path": fields["worktree"], "repository_id": "a" * 64,
                "worktree_id": core.continuation_digest(fields), "membership": "unknown",
                "disposition": "retained_unknown", "reasons": ["preservation_not_checked"]}
    monkeypatch.setattr(core, "inventory_item", item)
    first, report = metadata(core, root, capsys)
    assert len(first["items"]) == 100 and report["coverage"]["status"] == "partial"
    assert len(first["continuation"]) == 32 and "PRIVATE" not in first["continuation"]
    second, report = metadata(core, root, capsys, cursor=first["continuation"])
    assert len(second["items"]) == 5 and second["continuation"] is None
    assert not {x["worktree_id"] for x in first["items"]} & {x["worktree_id"] for x in second["items"]}
    snapshot["digest"] = "changed"
    with pytest.raises(RuntimeError, match="inventory_unavailable"):
        metadata(core, root, capsys, cursor=first["continuation"])
    assert capsys.readouterr().out == ""


def test_metadata_timeout_remains_partial_and_restores_timer(core, inventory_repo, monkeypatch, capsys):
    root, _, _, _ = inventory_repo
    monkeypatch.setattr(core, "root_dir", lambda: root)
    snapshot = core.inventory_repository(root)
    monkeypatch.setattr(core, "inventory_repository", lambda seed: snapshot)
    def slow(repository):
        with core.inventory_budget(0.01):
            time.sleep(1)
    monkeypatch.setattr(core, "inventory_cycles", slow)
    before = core.signal.getsignal(core.signal.SIGALRM)
    started = time.monotonic()
    _, report = metadata(core, root, capsys)
    assert time.monotonic() - started < 0.5
    assert report["coverage"]["status"] == "partial"
    assert "repository_metadata_unavailable" in report["coverage"]["reasons"]
    assert report["continuation"] is not None
    assert report["coverage"]["repositories_completed"] == 0
    assert core.signal.getitimer(core.signal.ITIMER_REAL)[0] == 0
    assert core.signal.getsignal(core.signal.SIGALRM) == before


def test_metadata_does_not_follow_record_or_report_symlinks(core, inventory_repo, monkeypatch, capsys):
    root, _, records, _ = inventory_repo
    monkeypatch.setattr(core, "root_dir", lambda: root)
    outside = root.parent / "PRIVATE_OUTSIDE"
    outside.write_text("PRIVATE_SENTINEL")
    (records / "linked.json").symlink_to(outside)
    projected, _ = metadata(core, root, capsys)
    assert projected["coverage"]["status"] == "unavailable"
    assert "PRIVATE" not in json.dumps(projected)
    (records / "linked.json").unlink()
    report_directory = root / ".git/dbsctr/inventory"
    (report_directory / ("a" * 32 + ".json")).symlink_to(outside)
    with pytest.raises(RuntimeError, match="inventory_unavailable"):
        metadata(core, root, capsys, cursor="a" * 32)
    assert outside.read_text() == "PRIVATE_SENTINEL"


def test_metadata_policy_sources_are_owned_hints_not_action_authority(core, inventory_repo,
                                                                  monkeypatch, capsys):
    root, _, _, _ = inventory_repo
    config = root.parent / "config"
    policy = config / "dotfiles-ai/workflow-policy.json"
    policy.parent.mkdir(parents=True)
    value = {"schema_version": 1, "source_commit": "a" * 40,
             "root": str(root.parent / "unused"),
             "repositories": [{"repository": str(root), "preservation": {"automatic_remove": True}}]}
    value["policy_digest"] = core.continuation_digest(value)
    policy.write_text(json.dumps(value))
    policy.chmod(0o600)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    monkeypatch.setenv("DBSCTR_WORKTREE_ROOT", str(root.parent / "missing"))
    monkeypatch.setattr(core, "root_dir", lambda: root)
    projected, report = metadata(core, root, capsys, all=True)
    assert len(projected["items"]) == 2
    assert all(x["disposition"] != "eligible" for x in projected["items"])
    policy.chmod(0o644)
    _, report = metadata(core, root, capsys, all=True)
    assert report["coverage"]["status"] == "partial"
    assert "policy_sources_unavailable" in report["coverage"]["reasons"]


@pytest.mark.parametrize("value", [None, [], "wrong"])
def test_metadata_malformed_worktree_is_unavailable(core, inventory_repo, monkeypatch, capsys, value):
    root, _, records, _ = inventory_repo
    document = json.loads((records / "cycle-1.json").read_text())
    document.pop("execution")
    document["worktree"] = value
    (records / "cycle-1.json").write_text(json.dumps(document))
    _, report = metadata(core, root, capsys)
    assert report["coverage"]["status"] == "partial"
    assert "cycle_records_unavailable" in report["coverage"]["reasons"]


def test_metadata_rejects_intermediate_lifecycle_symlink(core, inventory_repo, capsys):
    root, _, records, _ = inventory_repo
    moved = root.parent / "PRIVATE_EXTERNAL_STORE"
    (root / ".git/dbsctr").rename(moved)
    (root / ".git/dbsctr").symlink_to(moved, target_is_directory=True)
    with pytest.raises(RuntimeError, match="inventory_unavailable"):
        metadata(core, root, capsys)
    assert capsys.readouterr().out == ""
    assert not (moved / "inventory").exists()


def test_metadata_correlation_never_uses_unbounded_git(core, inventory_repo, monkeypatch, capsys):
    root, linked, records, _ = inventory_repo
    legacy = json.loads((records / "cycle-1.json").read_text())
    legacy.pop("execution")
    legacy.update(cycle_id="portable-1", schema_version=4)
    (records / "portable-1.json").write_text(json.dumps(legacy))
    def forbidden(*args, **kwargs):
        raise AssertionError("unbounded Git must not enter inventory")
    monkeypatch.setattr(core, "git", forbidden)
    _, report = metadata(core, root, capsys)
    assert report["coverage"]["status"] == "complete"
    item = next(x for x in report["items"] if x["path"] == str(linked))
    assert {r["id"] for r in item["cycles"]["records"]} == {"cycle-1", "portable-1"}


def test_metadata_never_enumerates_admin_symlinked_store(core, inventory_repo, capsys):
    root, linked, _, _ = inventory_repo
    admin = core.git_dir(linked)
    outside = root.parent / "PRIVATE_EXTERNAL_STORE"
    (outside / "cycles").mkdir(parents=True)
    (outside / "cycles/private.json").write_text("PRIVATE_SENTINEL")
    (admin / "dbsctr").symlink_to(outside, target_is_directory=True)
    projected, _ = metadata(core, root, capsys)
    assert projected["coverage"]["status"] == "unavailable"
    assert "PRIVATE" not in json.dumps(projected)
    assert (outside / "cycles/private.json").read_text() == "PRIVATE_SENTINEL"


def test_metadata_repository_limit_is_resumable_not_truncated(core, inventory_repo, monkeypatch, capsys):
    root, _, _, _ = inventory_repo
    registry = root.parent / "registry"
    parent = registry / "repositories"
    for number in range(256):
        child = parent / str(number)
        child.mkdir(parents=True)
        (child / ".git").write_text("fixture")
    monkeypatch.setenv("DBSCTR_WORKTREE_ROOT", str(registry))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(root.parent / "missing-config"))
    def repository(seed):
        return {"root": str(seed), "common": str(seed / ".git"), "members": [],
                "files": [], "digest": core.continuation_digest(str(seed))}
    monkeypatch.setattr(core, "inventory_repository", repository)
    first, report = metadata(core, root, capsys, all=True)
    assert report["coverage"]["repositories_seen"] == 256
    assert "repository_limit" in report["coverage"]["reasons"]
    assert len(report["seeds"]) == 257 and first["continuation"] is not None
    _, resumed = metadata(core, root, capsys, all=True, cursor=first["continuation"])
    assert resumed["coverage"]["repositories_seen"] == 1
    assert resumed["coverage"]["status"] == "complete"
    assert resumed["continuation"] is None


def test_metadata_record_read_budget_propagates_timeout(core, tmp_path, monkeypatch):
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record()))
    original = Path.open
    def slow(target, *args, **kwargs):
        if target == path:
            time.sleep(1)
        return original(target, *args, **kwargs)
    monkeypatch.setattr(Path, "open", slow)
    with pytest.raises(TimeoutError), core.inventory_budget(0.01):
        core.read_cycle_record(tmp_path, path, historical=True, max_bytes=1024)


def test_metadata_repository_collection_timeout_resumes(core, inventory_repo, monkeypatch, capsys):
    root, _, _, _ = inventory_repo
    original = core.inventory_repository
    def timeout(seed):
        raise TimeoutError("inventory_timeout")
    monkeypatch.setattr(core, "inventory_repository", timeout)
    first, report = metadata(core, root, capsys)
    assert report["coverage"]["status"] == "unavailable"
    assert first["continuation"] is not None and report["next_position"] == [0, 0]
    monkeypatch.setattr(core, "inventory_repository", original)
    _, resumed = metadata(core, root, capsys, cursor=first["continuation"])
    assert resumed["coverage"]["status"] == "complete"
    assert len(resumed["items"]) == 2 and resumed["continuation"] is None
