"""Completion reconciliation contracts using disposable repositories only."""

import json
import subprocess

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
