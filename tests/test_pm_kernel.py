import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
PMCTL = ROOT / "dot_local/bin/executable_pmctl"


def run(root, *args, check=True):
    return subprocess.run(["python3", str(PMCTL), *args, "--root", str(root), "--json"],
                          text=True, capture_output=True, check=check)


def backlog(root, active="", completed=""):
    path = root / "docs/specs/example/BACKLOG.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Backlog\n\n## Active\n\n"
        "| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n" + active +
        "\n## Completed\n\n| id | outcome | completed | commit |\n|---|---|---|---|\n" + completed
    )
    subprocess.run(["git", "add", str(path.relative_to(root))], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "backlog"], cwd=root, check=True, capture_output=True)
    return path


def init_git(root):
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    marker = root / "README.md"
    marker.write_text("test\n")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)


def test_migration_dry_run_is_deterministic_and_complete(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path,
            "| EX-1 | Refine work | high | pending | - | code | docs | no | Needed | S | pytest |\n",
            "| EX-0 | Shipped work | 2026-01-01 | `abcdef0` |\n")
    first = json.loads(run(tmp_path, "migrate-backlogs").stdout)
    second = json.loads(run(tmp_path, "migrate-backlogs").stdout)
    assert first == second
    assert [item["id"] for item in first["tickets"]] == ["EX-0", "EX-1"]
    assert not (tmp_path / "docs/tickets").exists()


def test_migration_apply_is_idempotent_and_preserves_source(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path, "| EX-1 | Refine work | high | in_progress | - | code | docs | yes | Needed | M | pytest |\n")
    applied = json.loads(run(tmp_path, "migrate-backlogs", "--apply").stdout)
    path = tmp_path / applied["tickets"][0]["path"]
    original = path.read_text()
    assert "migration:" in original and '"effort": "M"' in original
    run(tmp_path, "migrate-backlogs", "--apply")
    assert path.read_text() == original
    checked = json.loads(run(tmp_path, "tickets", "check").stdout)
    assert checked["findings"] == []


def test_ticket_check_rejects_duplicate_yaml_and_wrong_identity(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path, "| EX-1 | Refine work | high | pending | - | code | docs | no | Needed | S | pytest |\n")
    result = json.loads(run(tmp_path, "migrate-backlogs", "--apply").stdout)
    path = tmp_path / result["tickets"][0]["path"]
    path.write_text(path.read_text().replace("title:", "title: duplicate\ntitle:", 1))
    failed = run(tmp_path, "tickets", "check", check=False)
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["findings"][0]["code"] == "invalid_ticket_yaml"


def test_migration_refuses_all_outputs_before_destination_conflict(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path, "| EX-1 | Refine work | high | pending | - | code | docs | no | Needed | S | pytest |\n")
    target = tmp_path / "docs/tickets/context=example/EX-1-refine-work.md"
    target.parent.mkdir(parents=True)
    target.write_text("foreign\n")
    failed = run(tmp_path, "migrate-backlogs", "--apply", check=False)
    assert failed.returncode == 1
    assert "destination conflict" in failed.stderr
    assert target.read_text() == "foreign\n"


def test_jira_rollup_requires_exact_preview_confirmation(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path, "| EX-1 | First | high | pending | - | code | docs | no | Needed | S | pytest |\n"
                      "| EX-2 | Second | high | pending | EX-1 | code | docs | no | Needed | S | pytest |\n")
    migrated = json.loads(run(tmp_path, "migrate-backlogs", "--apply").stdout)
    for ticket in migrated["tickets"]:
        path = tmp_path / ticket["path"]
        path.write_text(path.read_text().replace('state: "intake"', 'state: "ready"'))
    subprocess.run(["git", "add", "docs/tickets"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "tickets"], cwd=tmp_path, check=True, capture_output=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True,
                            text=True, capture_output=True).stdout.strip()
    members = []
    for ticket in migrated["tickets"]:
        blob = subprocess.run(["git", "rev-parse", f"HEAD:{ticket['path']}"], cwd=tmp_path,
                              check=True, text=True, capture_output=True).stdout.strip()
        members.append({"id": ticket["id"], "path": ticket["path"], "commit": commit, "blob": blob})
    manifest = tmp_path / "jira.json"
    manifest.write_text(json.dumps({
        "project": "TEST", "issue_type": "Story", "summary": "One sprint outcome",
        "description": "Complete standalone context", "source_tickets": members,
    }))
    preview = subprocess.run(["python3", str(PMCTL), "jira", "preview", "--root", str(tmp_path),
                              "--manifest", str(manifest), "--json"],
                             check=True, text=True, capture_output=True)
    digest = json.loads(preview.stdout)["preview_digest"]
    denied = subprocess.run(["python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path), "--manifest", str(manifest),
                             "--preview-digest", digest, "--confirm", "wrong", "--json"],
                            text=True, capture_output=True)
    assert denied.returncode == 1
    accepted = subprocess.run(["python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path), "--manifest", str(manifest),
                               "--preview-digest", digest, "--confirm", digest, "--json"],
                              check=True, text=True, capture_output=True)
    assert json.loads(accepted.stdout)["result"] == "simulated"
    assert json.loads(accepted.stdout)["written"] is False


def test_projection_rejects_secrets_and_uses_psql_stdin(tmp_path):
    envelope = tmp_path / "envelope.json"
    envelope.write_text(json.dumps({"schema_version": 1, "source_id": "cycle-1",
                                    "source_authority": "dbsctr", "availability": "available",
                                    "payload": {"cycle_id": "cycle-1", "context": "example",
                                                "state": "completed", "risk": "routine",
                                                "delivery_intent": "local", "method_revision": "3.27",
                                                "schema_version": 4, "gates": {}}}))
    psql = tmp_path / "psql"
    capture = tmp_path / "sql"
    psql.write_text(f"#!/bin/sh\ncat > {capture}\n")
    psql.chmod(0o755)
    projected = subprocess.run(["python3", str(PMCTL), "project", "--source", "cycle_record",
                                "--input", str(envelope), "--psql", str(psql), "--json"],
                               check=True, text=True, capture_output=True)
    assert json.loads(projected.stdout)["source_id"] == "cycle-1"
    assert "ON CONFLICT DO NOTHING" in capture.read_text()
    envelope.write_text(json.dumps({"schema_version": 1, "source_id": "cycle-1",
                                    "source_authority": "dbsctr", "availability": "available",
                                    "payload": {"token": "private"}}))
    denied = subprocess.run(["python3", str(PMCTL), "project", "--source", "cycle_record",
                             "--input", str(envelope), "--psql", str(psql), "--json"],
                            text=True, capture_output=True)
    assert denied.returncode == 1


def test_ticket_projection_requires_committed_tree_and_records_revisions(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path, "| EX-1 | Refine | high | pending | - | code | docs | no | Needed | S | pytest |\n")
    migrated = json.loads(run(tmp_path, "migrate-backlogs", "--apply").stdout)
    subprocess.run(["git", "add", "docs/tickets"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "tickets"], cwd=tmp_path, check=True, capture_output=True)
    psql = tmp_path / "psql"
    capture = tmp_path / "ticket-sql"
    psql.write_text(f"#!/bin/sh\ncat > {capture}\n")
    psql.chmod(0o755)
    projected = subprocess.run(["python3", str(PMCTL), "project-tickets", "--root", str(tmp_path),
                                "--psql", str(psql), "--json"], check=True, text=True, capture_output=True)
    assert json.loads(projected.stdout)["projected"] == 1
    assert "context.ticket_revisions" in capture.read_text()
    ticket = tmp_path / migrated["tickets"][0]["path"]
    ticket.write_text(ticket.read_text().replace('title: "Refine"', 'title: "Dirty"'))
    denied = subprocess.run(["python3", str(PMCTL), "project-tickets", "--root", str(tmp_path),
                             "--psql", str(psql), "--json"], text=True, capture_output=True)
    assert denied.returncode == 1 and "clean committed ticket tree" in denied.stderr


def test_sprint_review_preserves_every_issue_once_and_goals(tmp_path):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps([
        {"key": "T-2", "summary": "Second", "status": "Done", "parent": "EP-1",
         "description": "Delivered second", "url": "https://jira.invalid/T-2"},
        {"key": "T-1", "summary": "First", "status": "Done", "parent": "EP-1",
         "description": "Delivered first", "url": "https://jira.invalid/T-1"},
    ]))
    completed = subprocess.run(["python3", str(PMCTL), "sprint-review", "--input", str(issues),
                                "--title", "Sprint 1", "--sprint-goal", "Goal supplied",
                                "--output-root", str(tmp_path / "reports"), "--json"],
                               check=True, text=True, capture_output=True)
    result = json.loads(completed.stdout)
    report = Path(result["path"]).read_text()
    assert result["issues"] == 2
    assert report.count("- [T-1]") == 1 and report.count("- [T-2]") == 1
    assert "Goal supplied" in report and "## Product Goal\n\nNot provided" in report
    assert "report_type=sprint_review" in result["path"] and "snapshot_date=" in result["path"]


def test_sprint_review_rejects_non_done_work(tmp_path):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps([{"key": "T-1", "summary": "Still open", "status": "In Progress",
                                   "parent": "", "description": "Not complete", "url": ""}]))
    denied = subprocess.run(["python3", str(PMCTL), "sprint-review", "--input", str(issues),
                             "--title", "Sprint", "--output-root", str(tmp_path / "reports"), "--json"],
                            text=True, capture_output=True)
    assert denied.returncode == 1
