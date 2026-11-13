"""Retained coordinator custody never imports foreign documents into Build Git."""
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import test_dbsctrctl as harness
from test_initiative_authority_amendment import (
    amendment, apply_amendment, evidence, git_snapshot, preview, private_file,
)
from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture, git, task


def reader():
    loader = importlib.machinery.SourceFileLoader("historical_profile_reader", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    return core


@pytest.fixture
def cross(fixture):
    root = fixture.repo
    git(root, "remote", "add", "origin", "https://github.com/example/test.git")
    remote = root.parent / "remote.git"
    git(root, "init", "--bare", str(remote))
    git(root, "remote", "add", "upstream", str(remote))
    git(root, "push", "upstream", "HEAD:refs/heads/base")
    source = root.parent / "coordinator"
    git(root, "clone", "--no-hardlinks", str(root), str(source))
    git(source, "config", "user.email", "fixture@example.invalid")
    git(source, "config", "user.name", "Fixture")
    git(source, "remote", "set-url", "origin", "https://github.com/example/coordinator.git")
    manifest = source / "docs/initiatives/test/MANIFEST.json"
    manifest.parent.mkdir(parents=True)
    value = harness.initiative_manifest()
    value["coordinator_repository"] = "example/coordinator"
    manifest.write_text(json.dumps(value))
    git(source, "add", "docs")
    git(source, "commit", "-m", "Initial coordinator authority")
    target = task(fixture)
    git(target, "branch", "--set-upstream-to", "upstream/base")
    plan = fixture.plan_path()

    def digest():
        return json.loads(harness.run(source, "initiative-check", "--manifest",
            str(manifest), "--json").stdout)["manifest_digest"]

    begin = ["begin", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
        "--delivery-intent", "local", "--base-branch", "protected", "--plan", str(plan),
        "--initiative-manifest", "docs/initiatives/test/MANIFEST.json",
        "--initiative-slice", "slice-a", "--initiative-source", str(source),
        "--initiative-digest", digest(), "--expected-repository", "example/test",
        "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest()]
    launch = json.loads(harness.run(target, *begin, "--preflight").stdout)["launch_digest"]
    harness.run(target, *begin, "--expected-launch-digest", launch, "--approval", "agent-confirmed")
    harness.run(target, "record-evidence", "contract", "--authority", "fixture", "--",
                "python3", "-c", "raise SystemExit(1)")
    foreign = source / "docs/specs/test/EXPANSION.md"
    foreign.write_text("Additional coordinator-owned contract.\n")
    value["statements"][0]["artifacts"].append("docs/specs/test/EXPANSION.md")
    manifest.write_text(json.dumps(value))
    git(source, "add", "docs")
    git(source, "commit", "-m", "Expanded coordinator authority")
    argv = ["initiative-amend", "--cycle-id", "cycle-1",
        "--initiative-manifest", "docs/initiatives/test/MANIFEST.json",
        "--initiative-slice", "slice-a", "--initiative-source", str(source),
        "--initiative-digest", digest(), "--plan", str(plan),
        "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest(),
        "--reason", "PRIVATE_REASON_SENTINEL", "--json"]
    return SimpleNamespace(amendment=(target, fixture.record_path(), argv), source=source,
                           manifest=manifest, foreign=foreign)


def test_cross_repository_preflight_apply_replay_and_local_checkpoint(cross):
    target, path, _ = cross.amendment
    before, checkout = json.loads(path.read_text()), git_snapshot(target)
    digest = preview(cross.amendment)
    assert json.loads(path.read_text()) == before
    _, replay = apply_amendment(cross.amendment)
    record = json.loads(path.read_text())
    entry = record["initiative_amendments"][-1]
    assert entry["schema_version"] == 2
    envelope = json.loads(private_file(target, entry["envelope_locator"]).read_text())
    assert envelope["plan"]["schema_version"] == 2
    assert envelope["plan"]["authority"]["repository"] == "example/coordinator"
    assert [p["path"] for p in envelope["plan"]["closure"]] == [before["engineering_profile"]["path"]]
    for key in ("initiative", "initiative_approval", "git", "commits", "evidence"):
        assert record.get(key) == before.get(key)
    assert all(g["result"] == "pending" for g in record["gates"].values()
               if g["applicability"] == "required")
    assert git_snapshot(target) == checkout
    assert not (target / cross.foreign.relative_to(cross.source)).exists()

    assert json.loads(harness.run(target, *replay).stdout)["status"] == "already_applied"
    (target / "tracked.txt").write_text("Build-only implementation change\n")
    evidence(target, paths=["tracked.txt"])
    harness.run(target, "gate-commit", "--message", "Build checkpoint", "--gates", "domain",
                "--paths", "tracked.txt")
    status = json.loads(harness.run(target, "status", "--json").stdout)
    assert status["gates"]["domain"]["result"] == "passed"
    record = json.loads(path.read_text())
    assert record["initiative_authority_checkpoints"][-1]["launch_digest"] == digest
    assert not (target / cross.foreign.relative_to(cross.source)).exists()

def test_historical_profile_uses_approved_source_not_inventory_checkout(cross):
    target, path, _ = cross.amendment
    apply_amendment(cross.amendment)
    original = path.read_bytes()
    observer = target.parent / "profile-observer"
    git(target, "worktree", "add", "-b", "profile-observer", str(observer), "HEAD")
    relative = json.loads(path.read_text())["engineering_profile"]["path"]
    profile = observer / relative
    profile.write_text(profile.read_text() + "\nIndependent later profile revision.\n")
    git(observer, "add", relative)
    git(observer, "commit", "-m", "Later profile revision")
    assert reader().read_cycle_record(observer, path, historical=True)["cycle_id"] == "cycle-1"
    assert path.read_bytes() == original


def test_historical_profile_rejects_moving_missing_or_wrong_source(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    relative = "docs/specs/test/PROFILE.md"
    profile = tmp_path / relative
    profile.parent.mkdir(parents=True)
    profile.write_text("Original profile\n")
    git(tmp_path, "add", relative)
    git(tmp_path, "commit", "-m", "Original profile")
    revision = git(tmp_path, "rev-parse", "HEAD").strip()
    blob = git(tmp_path, "rev-parse", "HEAD:" + relative).strip()
    profile.write_text("Later profile\n")
    git(tmp_path, "add", relative)
    git(tmp_path, "commit", "-m", "Later profile")
    core = reader()
    assert core.amendment_local_profile(tmp_path, relative, blob, revision) == [
        {"path": relative, "mode": "100644", "blob": blob}]
    with pytest.raises(RuntimeError, match="profile changed"):
        core.amendment_local_profile(tmp_path, relative, blob)
    for invalid in ("HEAD", "main", "--all", "", False):
        with pytest.raises(RuntimeError, match="revision is invalid"):
            core.amendment_local_profile(tmp_path, relative, blob, invalid)
    with pytest.raises(RuntimeError):
        core.amendment_local_profile(tmp_path, relative, blob, "f" * 40)
    with pytest.raises(RuntimeError, match="profile changed"):
        core.amendment_local_profile(tmp_path, relative, "e" * 40, revision)



@pytest.mark.parametrize("change", ["head", "origin", "document", "index", "missing"])
def test_cross_repository_authority_loss_or_drift_blocks_read_and_apply(cross, change):
    target, path, argv = cross.amendment
    _, replay = apply_amendment(cross.amendment)
    if change == "head":
        git(cross.source, "commit", "--allow-empty", "-m", "Changed authority HEAD")
    elif change == "origin":
        git(cross.source, "remote", "set-url", "origin", "https://github.com/foreign/control.git")
    elif change in {"document", "index"}:
        cross.foreign.write_text("Changed authority\n")
        if change == "index":
            git(cross.source, "add", str(cross.foreign.relative_to(cross.source)))
    else:
        cross.source.rename(cross.source.with_name("retained-but-unavailable"))
    before, checkout = path.read_bytes(), git_snapshot(target)
    assert harness.run(target, "status", "--json", ok=False).returncode != 0
    assert harness.run(target, *replay, ok=False).returncode != 0
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout


def test_cross_repository_stale_preflight_preserves_canonical_state(cross):
    target, path, argv = cross.amendment
    digest = preview(cross.amendment)
    git(cross.source, "commit", "--allow-empty", "-m", "Intervening authority change")
    before, checkout = path.read_bytes(), git_snapshot(target)
    result = harness.run(target, *argv, "--expected-launch-digest", digest,
                         "--approval", "agent-confirmed", ok=False)
    assert json.loads(result.stdout)["status"] == "blocked"
    assert path.read_bytes() == before and git_snapshot(target) == checkout


def test_independent_same_repository_clone_cannot_select_external_route(amendment, fixture):
    target, path, argv = amendment
    clone = fixture.repo.parent / "independent-same-repository"
    git(fixture.repo, "clone", "--no-hardlinks", str(fixture.repo), str(clone))
    git(clone, "remote", "set-url", "origin", "https://github.com/example/test.git")
    argv = list(argv)
    argv[argv.index("--initiative-source") + 1] = str(clone)
    before, checkout = path.read_bytes(), git_snapshot(target)
    result = harness.run(target, *argv, "--preflight", ok=False)
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "blocked"
    assert path.read_bytes() == before and git_snapshot(target) == checkout


@pytest.mark.parametrize("replacement", ["checkout", "git_directory"])
def test_retained_native_custody_replacement_at_same_path_is_rejected(cross, replacement):
    target, path, _ = cross.amendment
    apply_amendment(cross.amendment)
    before, checkout = path.read_bytes(), git_snapshot(target)
    if replacement == "checkout":
        retained = cross.source.with_name("original-native-checkout")
        cross.source.rename(retained)
        git(retained, "clone", "--no-hardlinks", str(retained), str(cross.source))
        git(cross.source, "remote", "set-url", "origin", "https://github.com/example/coordinator.git")
    else:
        original = cross.source / ".git"
        retained = cross.source.with_name("original-git-directory")
        original.rename(retained)
        shutil.copytree(retained, original)
    result = harness.run(target, "status", "--json", ok=False)
    assert result.returncode != 0
    assert path.read_bytes() == before and git_snapshot(target) == checkout
