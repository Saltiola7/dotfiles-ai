"""Completion reconciliation contracts using disposable repositories only."""

import json
import runpy
import subprocess
import sys

import pytest
import test_dbsctrctl as harness


@pytest.fixture
def deletion(request):
    fixture = harness.DbsctrctlTest()
    fixture.setUp()
    request.addfinalizer(fixture.tearDown)
    fixture.start()
    return fixture


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True).stdout.strip()


@pytest.mark.parametrize("staged", [False, True])
@pytest.mark.parametrize("rename", [False, True])
def test_tracked_absence_is_stage_order_independent(deletion, staged, rename):
    root = deletion.repo
    original = git(root, "rev-parse", "HEAD:tracked.txt")
    (root / "tracked.txt").unlink()
    paths = ["tracked.txt"]
    if rename:
        (root / "renamed.txt").write_text("renamed fixture\n")
        paths.append("renamed.txt")
    if staged:
        git(root, "add", "--", *paths)
    deletion.record_gate("domain", paths=paths)
    before = json.loads(deletion.record_path().read_text())
    item = before["evidence"]["items"][before["gates"]["domain"]["evidence"]]
    assert item["paths"]["tracked.txt"] is None
    assert item["absences"] == {"tracked.txt": {"mode": "100644", "blob": original}}
    harness.run(root, "gate-commit", "--message", "record tracked absence", "--gates", "domain",
                "--paths", *paths)
    after = json.loads(deletion.record_path().read_text())
    assert after["commits"][-1]["gates"] == ["domain"]
    assert "tracked.txt" not in git(root, "ls-files").splitlines()
    assert after["evidence"]["items"][item["id"]]["absences"] == item["absences"]
    assert harness.run(root, "check", "gates", ok=False).returncode != 0


@pytest.mark.parametrize("name", ["never-tracked.txt", ".env", "../escape.txt"])
def test_absence_does_not_admit_unknown_or_unsafe_paths(deletion, name):
    before = deletion.record_path().read_bytes()
    result = harness.run(deletion.repo, "record-evidence", "domain", "--authority", "fixture",
                         "--path", name, "--", "python3", "-c", "raise SystemExit(0)", ok=False)
    assert result.returncode != 0
    assert deletion.record_path().read_bytes() == before


@pytest.mark.parametrize("tamper", ["blob", "mode", "unknown-path"])
def test_tracked_absence_predecessor_tamper_cannot_be_committed(deletion, tamper):
    root = deletion.repo
    (root / "tracked.txt").unlink()
    deletion.record_gate("domain", paths=["tracked.txt"])
    path = deletion.record_path()
    record = json.loads(path.read_text())
    item = record["evidence"]["items"][record["gates"]["domain"]["evidence"]]
    if tamper == "unknown-path":
        item["paths"]["never-tracked.txt"] = None
        item["absences"]["never-tracked.txt"] = dict(item["absences"]["tracked.txt"])
    else:
        item["absences"]["tracked.txt"][tamper] = "f" * 40 if tamper == "blob" else "100755"
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    head, index = git(root, "rev-parse", "HEAD"), git(root, "write-tree")
    result = harness.run(root, "gate-commit", "--message", "reject forged predecessor", "--gates", "domain",
                         "--paths", "tracked.txt", ok=False)
    assert result.returncode != 0
    assert "predecessor" in result.stderr
    assert path.read_bytes() == before
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "write-tree") == index
    assert not (root / "tracked.txt").exists()


def pending_deletion_merge(root):
    """Resolve modify/delete as deleted; a second path exists only at the merge base."""
    branch = git(root, "branch", "--show-current")
    (root / "base-only.txt").write_text("both branches delete this\n")
    git(root, "add", "base-only.txt")
    git(root, "commit", "-m", "common predecessor")
    base = git(root, "rev-parse", "HEAD")
    git(root, "switch", "-c", "target")
    git(root, "rm", "base-only.txt")
    (root / "tracked.txt").write_text("target version\n")
    git(root, "commit", "-am", "target modifies tracked file")
    git(root, "switch", branch)
    git(root, "rm", "tracked.txt", "base-only.txt")
    git(root, "commit", "-m", "branch deletes both files")
    conflict = subprocess.run(["git", "merge", "--no-ff", "--no-commit", "target"], cwd=root, capture_output=True)
    assert conflict.returncode == 1
    assert git(root, "ls-files", "-u", "--", "tracked.txt")
    git(root, "rm", "tracked.txt")
    return git(root, "rev-parse", "MERGE_HEAD"), base


def domain_evidence(deletion):
    record = json.loads(deletion.record_path().read_text())
    return record["evidence"]["items"][record["gates"]["domain"]["evidence"]]


@pytest.fixture(scope="module")
def verify_absences():
    return runpy.run_path(str(harness.SCRIPT))["verify_evidence_absences"]


def assert_recording_refused(deletion, name, reason):
    before = deletion.record_path().read_bytes()
    result = harness.run(deletion.repo, "record-evidence", "domain", "--authority", "fixture",
                         "--path", name, "--", sys.executable, "-c", "pass", ok=False)
    assert reason in result.stderr
    assert deletion.record_path().read_bytes() == before


def test_merge_absence_is_pinned_to_its_source_but_not_staged(deletion, verify_absences):
    root = deletion.repo
    merge_head, base = pending_deletion_merge(root)
    sources = {"tracked.txt": merge_head, "base-only.txt": base}
    assert git(root, "ls-files", "--", *sources) == ""
    assert git(root, "ls-tree", "HEAD", "--", *sources) == ""
    assert not any((root / name).exists() for name in sources)
    deletion.record_gate("domain", paths=sources)
    item = domain_evidence(deletion)
    assert item["paths"] == dict.fromkeys(sources)
    assert item["absence_sources"] == sources
    assert item["absence_merge_head"] == merge_head
    assert item["absences"] == {
        name: {"mode": "100644", "blob": git(root, "rev-parse", f"{revision}:{name}")}
        for name, revision in sources.items()
    }

    before = deletion.record_path().read_bytes()
    head, index = git(root, "rev-parse", "HEAD"), git(root, "write-tree")
    result = harness.run(root, "gate-commit", "--message", "not in the staged diff", "--gates", "domain",
                         "--paths", *sources, ok=False)
    assert "staged paths differ" in result.stderr
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "write-tree") == index
    assert deletion.record_path().read_bytes() == before
    git(root, "commit", "-m", "finish fixture merge")
    assert git(root, "show", "-s", "--format=%P", "HEAD").split() == [head, merge_head]
    # Re-read the persisted proof after MERGE_HEAD has gone away.
    item = domain_evidence(deletion)
    verify_absences(root, item)
    commit = git(root, "rev-parse", "HEAD")
    verify_absences(root, {**item, "commit": commit})
    with pytest.raises(RuntimeError):
        verify_absences(root, {**item, "commit": head})


def test_absence_needs_an_exact_path_in_an_actual_merge(deletion, verify_absences):
    root = deletion.repo
    pending_deletion_merge(root)
    deletion.record_gate("domain", paths=["tracked.txt"])
    item = domain_evidence(deletion)
    verify_absences(root, item)
    assert_recording_refused(deletion, "never-tracked.txt", "path does not exist")
    git(root, "merge", "--abort")
    # An old branch, even one named like a pseudoref, is not a pending merge.
    git(root, "branch", "MERGE_HEAD", "target")
    assert_recording_refused(deletion, "tracked.txt", "path does not exist")
    with pytest.raises(RuntimeError, match="merge"):
        verify_absences(root, item)
    result = harness.run(root, "set-gate", "domain", "--result", "passed", "--evidence", item["id"], ok=False)
    assert "merge" in result.stderr
    result = harness.run(root, "record-evidence", "behavior", "--authority", "fixture", "--", sys.executable,
                         "-c", "pass", ok=False)
    assert "merge" in result.stderr


def test_completed_merge_absence_requires_the_actual_result(deletion, verify_absences):
    root = deletion.repo
    target, _ = pending_deletion_merge(root)
    deletion.record_gate("domain", paths=["tracked.txt"])
    item = domain_evidence(deletion)
    # A different valid resolution keeps the file in the resulting merge.
    git(root, "restore", "--source", target, "--staged", "--worktree", "--", "tracked.txt")
    git(root, "commit", "-m", "retain fixture file")
    merge = git(root, "rev-parse", "HEAD")
    git(root, "rm", "tracked.txt")
    git(root, "commit", "-m", "later deletion is not the merge resolution")
    for evidence in (item, {**item, "commit": merge}):
        with pytest.raises(RuntimeError, match="merge"):
            verify_absences(root, evidence)


def test_merge_credit_requires_ancestry_and_the_current_pending_target(deletion, verify_absences):
    root = deletion.repo
    target, _ = pending_deletion_merge(root)
    deletion.record_gate("domain", paths=["tracked.txt"])
    item = domain_evidence(deletion)
    git(root, "commit", "-m", "finish fixture merge")
    merge = git(root, "rev-parse", "HEAD")
    git(root, "commit", "--allow-empty", "-m", "descendant")
    for evidence in (item, {**item, "commit": merge}):
        verify_absences(root, evidence)

    git(root, "switch", "-c", "later-target", target)
    git(root, "commit", "--allow-empty", "-m", "different target identity")
    git(root, "switch", "-c", "again", item["head"])
    conflict = subprocess.run(["git", "merge", "--no-commit", "--no-ff", "later-target"], cwd=root, capture_output=True)
    assert conflict.returncode == 1
    git(root, "rm", "tracked.txt")
    for evidence in (item, {**item, "commit": merge}):
        with pytest.raises(RuntimeError, match="merge"):
            verify_absences(root, evidence)


@pytest.mark.parametrize("impossible", ["tracked.txt", "docs/specs/test/README.md"])
def test_mixed_impossible_gate_paths_preserve_existing_staging(deletion, impossible):
    root = deletion.repo
    if impossible == "tracked.txt":
        pending_deletion_merge(root)
    (root / "candidate.txt").write_text("working change\n")
    (root / "staged.txt").write_text("already staged\n")
    git(root, "add", "--", "staged.txt")
    (root / "staged.txt").write_text("later unstaged edit\n")
    names = ["candidate.txt", "staged.txt", impossible]
    deletion.record_gate("domain", paths=names)
    before = deletion.record_path().read_bytes()
    index = git(root, "write-tree")
    head = git(root, "rev-parse", "HEAD")
    result = harness.run(root, "gate-commit", "--message", "impossible pathset", "--gates", "domain", "--paths",
                         *names, ok=False)
    assert "staged paths differ" in result.stderr
    assert git(root, "write-tree") == index
    assert git(root, "rev-parse", "HEAD") == head
    assert deletion.record_path().read_bytes() == before


def test_merge_absence_rejects_invalid_source_bindings(deletion, verify_absences):
    root = deletion.repo
    target, base = pending_deletion_merge(root)
    present = "docs/specs/test/README.md"
    deletion.record_gate("domain", paths=["tracked.txt", present])
    item = domain_evidence(deletion)
    for sources in (None, [], {}, {"tracked.txt": "target"}, {"tracked.txt": "f" * len(target)},
                    {"tracked.txt": git(root, "rev-parse", "target^{tree}")},
                    {"tracked.txt": target, present: target}, {"tracked.txt": target, "unknown": base}):
        with pytest.raises(RuntimeError):
            verify_absences(root, {**item, "absence_sources": sources})
    # Both trees contain tracked.txt. Rewriting both source and blob to the
    # merge base cannot supersede the predecessor actually carried by target.
    base_blob = git(root, "rev-parse", f"{base}:tracked.txt")
    base_pin = {"tracked.txt": {"mode": "100644", "blob": base_blob}}
    with pytest.raises(RuntimeError):
        verify_absences(root, {**item, "absence_sources": {"tracked.txt": base}, "absences": base_pin})
    for key in ("absences", "absence_sources", "absence_merge_head"):
        with pytest.raises(RuntimeError):
            verify_absences(root, {field: value for field, value in item.items() if field != key})
    # An old HEAD-tracked deletion can be read without the additive fields;
    # a path that never existed at that HEAD cannot receive the same credit.
    old_shape = {key: value for key, value in item.items()
                 if key not in {"absences", "absence_sources", "absence_merge_head"}}
    with pytest.raises(RuntimeError, match="predecessor"):
        verify_absences(root, old_shape)
    verify_absences(root, {**old_shape, "head": base, "paths": {"tracked.txt": None}})
    with pytest.raises(RuntimeError):
        verify_absences(root, {**item, "paths": {"unknown": None}, "absence_sources": {"unknown": target},
                               "absences": {"unknown": item["absences"]["tracked.txt"]}})
    # Even a coherent pair of pins may not replace the actual active merge.
    path = deletion.record_path()
    record = json.loads(path.read_text())
    record["evidence"]["items"][item["id"]].update(
        absence_merge_head=base, absence_sources={"tracked.txt": base}, absences=base_pin)
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    index = git(root, "write-tree")
    result = harness.run(root, "gate-commit", "--message", "reject wrong merge", "--gates", "domain",
                         "--paths", "tracked.txt", present, ok=False)
    assert "predecessor" in result.stderr
    assert path.read_bytes() == before
    assert git(root, "write-tree") == index


def test_merge_staged_head_deletion_still_commits(deletion, verify_absences):
    root = deletion.repo
    head = git(root, "rev-parse", "HEAD")
    branch = git(root, "branch", "--show-current")
    git(root, "switch", "-c", "target")
    git(root, "rm", "tracked.txt")
    git(root, "commit", "-m", "target deletes tracked file")
    target = git(root, "rev-parse", "HEAD")
    git(root, "switch", branch)
    git(root, "merge", "--no-ff", "--no-commit", "target")
    deletion.record_gate("domain", paths=["tracked.txt"])
    harness.run(root, "gate-commit", "--message", "record merge", "--gates", "domain", "--paths", "tracked.txt")
    assert git(root, "show", "-s", "--format=%P", "HEAD").split() == [head, target]
    item = domain_evidence(deletion)
    original = git(root, "rev-parse", f"{head}:tracked.txt")
    assert item["absences"] == {"tracked.txt": {"mode": "100644", "blob": original}}
    assert not {"absence_sources", "absence_merge_head"} & item.keys()
    verify_absences(root, item)


def test_root_dbsctr_regular_artifact_is_recorded_but_not_staged(deletion):
    root = deletion.repo
    (root / ".gitignore").write_text("/.dbsctr/\n")
    name = ".dbsctr/validation/witness.json"
    artifact = root / name
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"checked": true}\n')
    expected = git(root, "hash-object", "--", name)
    deletion.record_gate("domain", paths=[name])
    item = domain_evidence(deletion)
    assert item["paths"] == {name: expected}
    assert "absences" not in item
    before = deletion.record_path().read_bytes()
    head, index = git(root, "rev-parse", "HEAD"), git(root, "write-tree")
    result = harness.run(root, "gate-commit", "--message", "local witness", "--gates", "domain",
                         "--paths", name, ok=False)
    assert "staged paths differ" in result.stderr
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "write-tree") == index
    assert deletion.record_path().read_bytes() == before
    # Force-staging an ignored local file does not make it HEAD-tracked.
    git(root, "add", "-f", "--", name)
    index = git(root, "write-tree")
    harness.run(root, "gate-commit", "--message", "force-staged witness", "--gates", "domain", "--paths", name,
                ok=False)
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "write-tree") == index
    assert deletion.record_path().read_bytes() == before


def test_artifact_exception_rejects_aliases_directories_and_secrets(deletion, tmp_path):
    root = deletion.repo
    (root / ".gitignore").write_text(".dbsctr/\n/.dbsctr-other/\n")
    area = root / ".dbsctr"
    area.mkdir()
    (tmp_path / "outside.txt").write_text("outside\n")
    (area / "leaf").symlink_to(tmp_path / "outside.txt")
    (area / "parent").symlink_to(tmp_path, target_is_directory=True)
    (area / "directory").mkdir()
    (area / ".env").write_text("fixture\n")
    for name in (".dbsctr/leaf", ".dbsctr/parent/outside.txt", ".dbsctr/directory", ".dbsctr/missing", ".dbsctr"):
        assert_recording_refused(deletion, name, "artifact")
    assert_recording_refused(deletion, ".dbsctr/../tracked.txt", "repo-relative")
    assert_recording_refused(deletion, ".dbsctr/.env", "possible secret path")
    for name in ("nested/.dbsctr/witness.txt", ".dbsctr-other/witness.txt"):
        (root / name).parent.mkdir(parents=True)
        (root / name).write_text("ordinary ignored file\n")
        assert_recording_refused(deletion, name, "path is ignored")
    area.rename(root / "local-files")
    area.symlink_to(tmp_path, target_is_directory=True)
    assert_recording_refused(deletion, ".dbsctr/outside.txt", "artifact")
    area.unlink()
    area.write_text("a file, not the artifact directory\n")
    assert_recording_refused(deletion, ".dbsctr", "artifact")


def test_historical_tracked_artifact_deletion_retains_its_head_binding(deletion, verify_absences):
    root = deletion.repo
    name = ".dbsctr/previous.txt"
    (root / ".dbsctr").mkdir()
    (root / name).write_text("historically tracked\n")
    (root / ".gitignore").write_text("/.dbsctr/\n")
    git(root, "add", "-f", "--", name, ".gitignore")
    git(root, "commit", "-m", "previously tracked file in ignored area")
    blob = git(root, "rev-parse", f"HEAD:{name}")
    git(root, "rm", "--", name)
    deletion.record_gate("domain", paths=[name])
    harness.run(root, "gate-commit", "--message", "retire tracked file", "--gates", "domain", "--paths", name)
    item = domain_evidence(deletion)
    assert item["paths"] == {name: None}
    assert item["absences"] == {name: {"mode": "100644", "blob": blob}}
    assert not {"absence_sources", "absence_merge_head"} & item.keys()
    verify_absences(root, item)


def test_local_artifact_hash_is_of_literal_bytes(deletion):
    root = deletion.repo
    name = ".dbsctr/witness.txt"
    (root / ".dbsctr").mkdir()
    (root / ".gitignore").write_text("/.dbsctr/\n")
    (root / ".gitattributes").write_text("*.txt text eol=lf\n")
    (root / name).write_bytes(b"line one\r\nline two\r\n")
    literal = git(root, "hash-object", "--no-filters", "--", name)
    assert literal != git(root, "hash-object", "--path", name, "--", name)
    deletion.record_gate("domain", paths=[name])
    assert domain_evidence(deletion)["paths"] == {name: literal}


def test_gate_commit_uses_literal_stage_zero_filename(deletion):
    root = deletion.repo
    name = "2:minutes.txt"
    (root / name).write_text("meeting minutes\n")
    deletion.record_gate("domain", paths=[name])
    harness.run(root, "gate-commit", "--message", "fixture filename", "--gates", "domain", "--paths", name)
    assert git(root, "show", f"HEAD:{name}") == "meeting minutes"
