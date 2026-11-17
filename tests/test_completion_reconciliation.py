"""Completion reconciliation contracts using disposable repositories only."""

import json
import subprocess
from pathlib import Path

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


def merge_target_modify(deletion):
    """Branch deletes tracked.txt, target modifies it, merge resolves to delete."""
    root = deletion.repo
    base = git(root, "branch", "--show-current")
    git(root, "checkout", "-b", "target")
    (root / "tracked.txt").write_text("target modifies\n")
    git(root, "add", "tracked.txt")
    git(root, "commit", "-m", "target: modify tracked.txt")
    git(root, "checkout", base)
    git(root, "rm", "-q", "tracked.txt")
    git(root, "commit", "-m", "branch: delete tracked.txt")
    subprocess.run(["git", "merge", "--no-ff", "--no-commit", "target"], cwd=root, capture_output=True)
    subprocess.run(["git", "rm", "-q", "tracked.txt"], cwd=root, capture_output=True)
    return git(root, "rev-parse", "MERGE_HEAD")


def test_merge_deletion_absent_from_head_is_evidenced_from_the_merge(deletion):
    """A reconcile merge in progress pins deletions the branch already dropped from HEAD."""
    root = deletion.repo
    merge_head = merge_target_modify(deletion)
    target_blob = git(root, "rev-parse", f"{merge_head}:tracked.txt")
    deletion.record_gate("domain", paths=["tracked.txt"])
    record = json.loads(deletion.record_path().read_text())
    item = record["evidence"]["items"][record["gates"]["domain"]["evidence"]]
    assert item["paths"] == {"tracked.txt": None}
    assert item["absences"] == {"tracked.txt": {"mode": "100644", "blob": target_blob}}
    assert item["absence_sources"] == {"tracked.txt": merge_head}
    # Verification stays stable while the merge is still in progress.
    assert harness.run(root, "status", "--json").returncode == 0
    # The staged-paths-equality rule still governs what may be committed: this
    # deletion is not part of the staged diff, so gate-commit refuses it.
    before = deletion.record_path().read_bytes()
    head = git(root, "rev-parse", "HEAD")
    result = harness.run(root, "gate-commit", "--message", "not staged by this merge", "--gates", "domain",
                         "--paths", "tracked.txt", ok=False)
    assert result.returncode != 0
    assert "staged paths" in result.stderr
    assert deletion.record_path().read_bytes() == before
    assert git(root, "rev-parse", "HEAD") == head


@pytest.mark.parametrize("vanished", ["never-tracked.txt", "tracked.txt"])
def test_merge_deletion_unknown_to_the_merge_is_still_refused(deletion, vanished):
    """Paths absent from disk, index, HEAD and every merge tree stay refused."""
    root = deletion.repo
    if vanished == "tracked.txt":
        # Dropped on the branch with no merge in progress and no other tree to pin it.
        git(root, "rm", "-q", "tracked.txt")
        git(root, "commit", "-m", "branch: delete tracked.txt")
    else:
        merge_target_modify(deletion)  # a merge is in progress; the path is unknown to it
    before = deletion.record_path().read_bytes()
    result = harness.run(root, "record-evidence", "domain", "--authority", "fixture",
                         "--path", vanished, "--", "python3", "-c", "raise SystemExit(0)", ok=False)
    assert result.returncode != 0
    assert "path does not exist" in result.stderr
    assert deletion.record_path().read_bytes() == before


def test_merge_staged_deletion_commits_as_a_merge(deletion):
    """A deletion staged by the merge itself (present at HEAD) commits with two parents."""
    root = deletion.repo
    original = git(root, "rev-parse", "HEAD:tracked.txt")
    base = git(root, "branch", "--show-current")
    git(root, "checkout", "-b", "target")
    git(root, "rm", "-q", "tracked.txt")
    (root / "README.md").write_text("target change\n")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "target: delete tracked.txt, touch README")
    git(root, "checkout", base)
    git(root, "merge", "--no-ff", "--no-commit", "target")
    deletion.record_gate("domain", paths=["README.md", "tracked.txt"])
    record = json.loads(deletion.record_path().read_text())
    item = record["evidence"]["items"][record["gates"]["domain"]["evidence"]]
    assert item["paths"] == {"README.md": item["paths"]["README.md"], "tracked.txt": None}
    assert item["absences"] == {"tracked.txt": {"mode": "100644", "blob": original}}
    assert "absence_sources" not in item
    harness.run(root, "gate-commit", "--message", "commit merge deletion", "--gates", "domain",
                "--paths", "README.md", "tracked.txt")
    assert len(git(root, "show", "-s", "--format=%P", "HEAD").split()) == 2
    assert "tracked.txt" not in git(root, "ls-files").splitlines()
    # MERGE_HEAD is gone after the commit; pinned absences still verify.
    assert not (Path(root) / ".git" / "MERGE_HEAD").exists()
    result = harness.run(root, "check", "gates", ok=False)
    assert "predecessor" not in result.stderr


def test_own_dbsctr_artifacts_are_admissible_evidence_paths(deletion):
    """The repo-root .dbsctr/ prefix is the tool's own evidence artifact area."""
    root = deletion.repo
    (root / ".gitignore").write_text(".dbsctr/\nignored-area/\n")
    artifact = root / ".dbsctr" / "witness.json"
    artifact.parent.mkdir()
    artifact.write_text('{"witness": true}\n')
    deletion.record_gate("domain", paths=[".dbsctr/witness.json"])
    record = json.loads(deletion.record_path().read_text())
    item = record["evidence"]["items"][record["gates"]["domain"]["evidence"]]
    assert item["paths"] == {".dbsctr/witness.json": item["paths"][".dbsctr/witness.json"]}
    assert item["paths"][".dbsctr/witness.json"] is not None
    # Committed evidence stays staged-only: gate-commit refuses the artifact path
    # through the staged-paths rule, not through the ignored-path refusal.
    result = harness.run(root, "gate-commit", "--message", "own artifact", "--gates", "domain",
                         "--paths", ".dbsctr/witness.json", ok=False)
    assert result.returncode != 0
    assert "path is ignored" not in result.stderr


def test_other_ignored_evidence_paths_stay_refused(deletion):
    """Every ignored location outside the tool's own artifact area keeps its refusal."""
    root = deletion.repo
    (root / ".gitignore").write_text(".dbsctr/\nignored-area/\n")
    (root / "ignored-area").mkdir()
    (root / "ignored-area" / "notes.txt").write_text("notes\n")
    before = deletion.record_path().read_bytes()
    result = harness.run(root, "record-evidence", "domain", "--authority", "fixture",
                         "--path", "ignored-area/notes.txt", "--", "python3", "-c", "raise SystemExit(0)",
                         ok=False)
    assert result.returncode != 0
    assert "path is ignored" in result.stderr
    assert deletion.record_path().read_bytes() == before
