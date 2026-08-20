import hashlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
PMCTL = ROOT / "dot_local/bin/executable_pmctl"


def run(root, *args, check=True):
    return subprocess.run(["python3", str(PMCTL), *args, "--root", str(root), "--json"],
                          text=True, capture_output=True, check=check)


def test_jira_adf_text_preserves_structure():
    loader = importlib.machinery.SourceFileLoader("pmctl_module", str(PMCTL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    adf = {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "First"}]},
        {"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Second"}]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Third"}]}]},
        ]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "Line"}, {"type": "hardBreak"}, {"type": "text", "text": "break"},
        ]},
    ]}
    assert module.jira_description_text(adf) == "First\n\n- Second\n- Third\n\nLine\nbreak"


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
        "publication_id": "test-rollup", "target": {"mode": "create"},
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

    acli = tmp_path / "acli"
    log = tmp_path / "acli.log"
    description = tmp_path / "description.log"
    label = "pmk-" + hashlib.sha256(b"test-rollup").hexdigest()[:16]
    acli.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with pathlib.Path(os.environ["ACLI_LOG"]).open("a") as stream:
    stream.write(json.dumps(args) + "\\n")
if "search" in args:
    print("[]")
elif "create" in args:
    path = args[args.index("--description-file") + 1]
    pathlib.Path(os.environ["ACLI_DESCRIPTION"]).write_text(pathlib.Path(path).read_text())
    if os.environ.get("ACLI_FAIL"):
        print("not-json")
    else:
        print(json.dumps({"key": "TEST-1"}))
elif "edit" in args:
    print(json.dumps({"key": "TEST-1"}))
elif "view" in args:
    fields = {
        "project": {"key": "TEST"}, "issuetype": {"name": "Story"},
        "summary": "One sprint outcome", "description": "Complete standalone context",
        "labels": [os.environ["ACLI_LABEL"]]
    }
    if os.environ.get("ACLI_OMIT"):
        fields.pop("description")
    print(json.dumps({"key": "TEST-1", "fields": fields}))
else:
    raise SystemExit(2)
""")
    acli.chmod(0o755)
    env = {**os.environ, "HOME": str(tmp_path), "ACLI_LOG": str(log),
           "ACLI_DESCRIPTION": str(description), "ACLI_LABEL": label}
    receipt_root = tmp_path / ".local/state/pm-kernel/jira"
    live = subprocess.run([
        "python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", digest, "--confirm", digest,
        "--adapter", "acli", "--project", "TEST", "--issue-type", "Story",
        "--acli", str(acli), "--json",
    ], check=True, text=True, capture_output=True, env=env)
    assert json.loads(live.stdout)["jira_key"] == "TEST-1"
    assert description.read_text() == "Complete standalone context"
    assert "Complete standalone context" not in log.read_text()
    receipt = json.loads((receipt_root / "test-rollup.json").read_text())
    assert receipt["status"] == "succeeded" and receipt["jira_key"] == "TEST-1"

    psql = tmp_path / "psql"
    sql = tmp_path / "publication.sql"
    psql.write_text(f"#!/bin/sh\ncat > {sql}\n")
    psql.chmod(0o755)
    projected = subprocess.run([
        "python3", str(PMCTL), "jira", "project-receipt", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", digest,
        "--psql", str(psql), "--json",
    ], check=True, text=True, capture_output=True, env=env)
    projection = json.loads(projected.stdout)
    assert projection["jira_key"] == "TEST-1"
    assert projection["references"] == [
        {"ticket_id": member["id"], "reference": "test-rollup"}
        for member in members
    ]
    assert "context.jira_publications" in sql.read_text()
    assert sql.read_text().count("context.jira_publication_members") == 3

    payload = json.loads(manifest.read_text())
    payload["target"] = {"mode": "update", "key": "TEST-1"}
    manifest.write_text(json.dumps(payload))
    update_digest = json.loads(subprocess.run([
        "python3", str(PMCTL), "jira", "preview", "--root", str(tmp_path),
        "--manifest", str(manifest), "--json",
    ], check=True, text=True, capture_output=True).stdout)["preview_digest"]
    updated = subprocess.run([
        "python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", update_digest, "--confirm", update_digest,
        "--adapter", "acli", "--project", "TEST", "--issue-type", "Story",
        "--acli", str(acli), "--json",
    ], check=True, text=True, capture_output=True, env=env)
    assert json.loads(updated.stdout)["jira_key"] == "TEST-1"
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert any("edit" in call for call in calls)
    search = next(call for call in calls if "search" in call)
    assert search[search.index("--fields") + 1] == "key,issuetype,summary,description,labels"
    assert not any(argument.startswith(("--customfield", "--sprint", "--points"))
                   for call in calls for argument in call)
    edit_count = sum("edit" in call for call in calls)
    repeated = subprocess.run([
        "python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", update_digest, "--confirm", update_digest,
        "--adapter", "acli", "--project", "TEST", "--issue-type", "Story",
        "--acli", str(acli), "--json",
    ], text=True, capture_output=True, env=env)
    assert repeated.returncode == 1
    assert sum("edit" in json.loads(line) for line in log.read_text().splitlines()) == edit_count

    payload["publication_id"] = "missing-field-rollup"
    payload["target"] = {"mode": "create"}
    manifest.write_text(json.dumps(payload))
    missing_digest = json.loads(subprocess.run([
        "python3", str(PMCTL), "jira", "preview", "--root", str(tmp_path),
        "--manifest", str(manifest), "--json",
    ], check=True, text=True, capture_output=True).stdout)["preview_digest"]
    missing_env = {**env, "ACLI_OMIT": "1",
                   "ACLI_LABEL": "pmk-" + hashlib.sha256(b"missing-field-rollup").hexdigest()[:16]}
    missing = subprocess.run([
        "python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", missing_digest, "--confirm", missing_digest,
        "--adapter", "acli", "--project", "TEST", "--issue-type", "Story",
        "--acli", str(acli), "--json",
    ], text=True, capture_output=True, env=missing_env)
    assert missing.returncode == 1
    assert json.loads((receipt_root / "missing-field-rollup.json").read_text())["status"] == "unknown"


def test_jira_acli_unknown_result_blocks_retry(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path, "| EX-1 | First | high | pending | - | code | docs | no | Needed | S | pytest |\n")
    ticket = json.loads(run(tmp_path, "migrate-backlogs", "--apply").stdout)["tickets"][0]
    path = tmp_path / ticket["path"]
    path.write_text(path.read_text().replace('state: "intake"', 'state: "ready"'))
    subprocess.run(["git", "add", "docs/tickets"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "tickets"], cwd=tmp_path, check=True, capture_output=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True,
                            text=True, capture_output=True).stdout.strip()
    blob = subprocess.run(["git", "rev-parse", f"HEAD:{ticket['path']}"], cwd=tmp_path,
                          check=True, text=True, capture_output=True).stdout.strip()
    manifest = tmp_path / "jira.json"
    manifest.write_text(json.dumps({
        "publication_id": "unknown-rollup", "target": {"mode": "create"},
        "project": "TEST", "issue_type": "Story", "summary": "Unknown outcome",
        "description": "Complete context", "source_tickets": [
            {"id": ticket["id"], "path": ticket["path"], "commit": commit, "blob": blob},
        ],
    }))
    digest = json.loads(subprocess.run([
        "python3", str(PMCTL), "jira", "preview", "--root", str(tmp_path),
        "--manifest", str(manifest), "--json",
    ], check=True, text=True, capture_output=True).stdout)["preview_digest"]
    acli = tmp_path / "acli"
    log = tmp_path / "log"
    acli.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {log}\ncase \"$*\" in *search*) printf '[]\\n';; *create*) printf 'not-json\\n';; esac\n")
    acli.chmod(0o755)
    command = [
        "python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", digest, "--confirm", digest,
        "--adapter", "acli", "--project", "TEST", "--issue-type", "Story",
        "--acli", str(acli), "--json",
    ]
    env = {**os.environ, "HOME": str(tmp_path)}
    assert subprocess.run(command, text=True, capture_output=True, env=env).returncode == 1
    first = log.read_text().count("create")
    receipt_root = tmp_path / ".local/state/pm-kernel/jira"
    assert json.loads((receipt_root / "unknown-rollup.json").read_text())["status"] == "unknown"
    assert subprocess.run(command, text=True, capture_output=True, env=env).returncode == 1
    assert log.read_text().count("create") == first
    reconciled = subprocess.run([
        "python3", str(PMCTL), "jira", "reconcile", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", digest, "--project", "TEST",
        "--issue-type", "Story", "--acli", str(acli),
        "--json",
    ], check=True, text=True, capture_output=True, env=env)
    assert json.loads(reconciled.stdout)["result"] == "not_found"


def test_jira_acli_create_is_locked_by_publication(tmp_path):
    init_git(tmp_path)
    backlog(tmp_path, "| EX-1 | First | high | pending | - | code | docs | no | Needed | S | pytest |\n")
    ticket = json.loads(run(tmp_path, "migrate-backlogs", "--apply").stdout)["tickets"][0]
    path = tmp_path / ticket["path"]
    path.write_text(path.read_text().replace('state: "intake"', 'state: "ready"'))
    subprocess.run(["git", "add", "docs/tickets"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "tickets"], cwd=tmp_path, check=True, capture_output=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True,
                            text=True, capture_output=True).stdout.strip()
    blob = subprocess.run(["git", "rev-parse", f"HEAD:{ticket['path']}"], cwd=tmp_path, check=True,
                          text=True, capture_output=True).stdout.strip()
    manifest = tmp_path / "jira.json"
    manifest.write_text(json.dumps({
        "publication_id": "concurrent-rollup", "target": {"mode": "create"},
        "project": "TEST", "issue_type": "Story", "summary": "Concurrent outcome",
        "description": "Complete context", "source_tickets": [
            {"id": ticket["id"], "path": ticket["path"], "commit": commit, "blob": blob},
        ],
    }))
    digest = json.loads(subprocess.run([
        "python3", str(PMCTL), "jira", "preview", "--root", str(tmp_path),
        "--manifest", str(manifest), "--json",
    ], check=True, text=True, capture_output=True).stdout)["preview_digest"]
    acli = tmp_path / "acli"
    log = tmp_path / "create.log"
    label = "pmk-" + hashlib.sha256(b"concurrent-rollup").hexdigest()[:16]
    acli.write_text(f"""#!/usr/bin/env python3
import json, pathlib, sys, time
args = sys.argv[1:]
if "search" in args:
    print("[]")
elif "create" in args:
    with pathlib.Path({str(log)!r}).open("a") as stream: stream.write("create\\n")
    time.sleep(0.2)
    print(json.dumps({{"key": "TEST-1"}}))
elif "view" in args:
    print(json.dumps({{"key": "TEST-1", "fields": {{"project": {{"key": "TEST"}},
        "issuetype": {{"name": "Story"}}, "summary": "Concurrent outcome",
        "description": "Complete context", "labels": [{label!r}]}}}}))
else:
    raise SystemExit(2)
""")
    acli.chmod(0o755)
    command = [
        "python3", str(PMCTL), "jira", "publish", "--root", str(tmp_path),
        "--manifest", str(manifest), "--preview-digest", digest, "--confirm", digest,
        "--adapter", "acli", "--project", "TEST", "--issue-type", "Story",
        "--acli", str(acli), "--json",
    ]
    env = {**os.environ, "HOME": str(tmp_path)}
    processes = [subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                 for _ in range(2)]
    results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]
    assert sorted(result[2] for result in results) == [0, 1]
    assert log.read_text().splitlines() == ["create"]
    overridden = subprocess.run([*command, "--receipt-root", str(tmp_path / "other")],
                                text=True, capture_output=True, env=env)
    assert overridden.returncode == 2


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

    envelope.write_text(json.dumps({"schema_version": 1, "source_id": "cycle-missing",
                                    "source_authority": "dbsctr", "availability": "unavailable",
                                    "payload": {"reason": "No eligible sanitized source"}}))
    unavailable = subprocess.run(["python3", str(PMCTL), "project", "--source", "cycle_record",
                                  "--input", str(envelope), "--psql", str(psql), "--json"],
                                 check=True, text=True, capture_output=True)
    assert json.loads(unavailable.stdout)["availability"] == "unavailable"
    assert "'unavailable'" in capture.read_text()


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
    assert '"body":"## Outcome' in capture.read_text()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True,
                          text=True, capture_output=True).stdout.strip()
    assert json.loads(projected.stdout)["commit"] == head
    assert f"'tickets','{head}',1" in capture.read_text()
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
        {"key": "T-1", "summary": "First # [unsafe]", "status": "Done", "parent": "EP-1",
         "description": "![remote](https://invalid/image)", "url": "https://jira.invalid/T-1"},
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
    assert "First \\# \\[unsafe\\]" in report and "![remote]" not in report
    assert Path(result["path"]).stat().st_mode & 0o777 == 0o600
    assert Path(result["path"]).parent.stat().st_mode & 0o777 == 0o700

    default_path = subprocess.run(["python3", str(PMCTL), "sprint-review", "--input", str(issues),
                                   "--title", "Default path", "--json"], cwd=tmp_path,
                                  check=True, text=True, capture_output=True)
    default_report = tmp_path / json.loads(default_path.stdout)["path"]
    assert default_report.is_file() and default_report.stat().st_mode & 0o777 == 0o600

    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    shared_path = subprocess.run(["python3", str(PMCTL), "sprint-review", "--input", str(issues),
                                  "--title", "Shared root", "--output-root", str(shared), "--json"],
                                 check=True, text=True, capture_output=True)
    shared_report = Path(json.loads(shared_path.stdout)["path"])
    assert shared.stat().st_mode & 0o777 == 0o755
    assert shared_report.parent.stat().st_mode & 0o777 == 0o700


def test_sprint_review_rejects_non_done_work(tmp_path):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps([{"key": "T-1", "summary": "Still open", "status": "In Progress",
                                   "parent": "", "description": "Not complete", "url": ""}]))
    denied = subprocess.run(["python3", str(PMCTL), "sprint-review", "--input", str(issues),
                             "--title", "Sprint", "--output-root", str(tmp_path / "reports"), "--json"],
                            text=True, capture_output=True)
    assert denied.returncode == 1

    issues.write_text(json.dumps([{"key": [], "summary": "Bad", "status": "Done",
                                   "parent": "", "description": "Bad", "url": ""}]))
    malformed = subprocess.run(["python3", str(PMCTL), "sprint-review", "--input", str(issues),
                                "--title", "Sprint", "--output-root", str(tmp_path / "reports"), "--json"],
                               text=True, capture_output=True)
    assert malformed.returncode == 1 and "Traceback" not in malformed.stderr

    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    issues.write_text("[]")
    escaped = subprocess.run(["python3", str(PMCTL), "sprint-review", "--input", str(issues),
                              "--title", "Sprint", "--output-root", str(linked / "reports"), "--json"],
                             text=True, capture_output=True)
    assert escaped.returncode == 1
    assert not list(outside.rglob("sprint_review_*.md"))


def test_sprint_review_reads_digest_confirmed_bounded_jql(tmp_path):
    acli = tmp_path / "acli"
    log = tmp_path / "acli.log"
    acli.write_text(f"""#!/usr/bin/env python3
import json, os, pathlib, sys
pathlib.Path({str(log)!r}).write_text(json.dumps(sys.argv[1:]))
print(json.dumps({{"issues": [{{"key": "TEST-2", "fields": {{
    "summary": "Delivered", "status": {{"name": os.environ.get("ACLI_STATUS", "Done")}},
    "parent": {{"key": "TEST-1"}}, "description": "Shipped"
}}}}]}}))
""")
    acli.chmod(0o755)
    jql = 'project = "TEST" AND status = "Done"'
    digest = hashlib.sha256(jql.encode()).hexdigest()
    completed = subprocess.run([
        "python3", str(PMCTL), "sprint-review", "--jql", jql,
        "--confirm-jql-digest", digest, "--project", "TEST", "--acli", str(acli),
        "--title", "Sprint 2", "--output-root", str(tmp_path / "reports"), "--json",
    ], check=True, text=True, capture_output=True)
    result = json.loads(completed.stdout)
    report = Path(result["path"]).read_text()
    arguments = json.loads(log.read_text())
    assert arguments[:3] == ["jira", "workitem", "search"]
    assert arguments[arguments.index("--fields") + 1] == "key,summary,status,description"
    assert arguments[arguments.index("--limit") + 1] == "200"
    assert not {"create", "edit"} & set(arguments)
    assert result["jql_digest"] == digest and result["issue_keys"] == ["TEST-2"]
    assert f"JQL SHA-256: `{digest}`" in report and "TEST-2" in report

    sprint_jql = '''project = TEST
AND status = Closed
AND "cf[10010]" = 41762
AND "cf[10010]" NOT IN openSprints()
AND "cf[10010]" NOT IN futureSprints()
ORDER BY created DESC'''
    sprint_digest = hashlib.sha256(sprint_jql.encode()).hexdigest()
    sprint = subprocess.run([
        "python3", str(PMCTL), "sprint-review", "--jql", sprint_jql,
        "--confirm-jql-digest", sprint_digest, "--project", "TEST", "--done-status", "Closed",
        "--acli", str(acli), "--title", "Closed Sprint", "--output-root", str(tmp_path / "reports"), "--json",
    ], check=True, text=True, capture_output=True, env={**os.environ, "ACLI_STATUS": "Closed"})
    assert json.loads(sprint.stdout)["jql_digest"] == sprint_digest

    before = log.read_text()
    invalid = [
        'project = "OTHER" AND status = "Done"',
        'project != "TEST" AND status = "Done"',
        'summary ~ "project = TEST" AND project = "OTHER" AND status = "Done"',
        'project = "TEST" AND project = "TEST" AND status = "Done"',
        'project = "TEST" AND summary ~ "work"',
    ]
    for query in invalid:
        denied = subprocess.run([
            "python3", str(PMCTL), "sprint-review", "--jql", query,
            "--confirm-jql-digest", hashlib.sha256(query.encode()).hexdigest(),
            "--project", "TEST", "--acli", str(acli), "--title", "Denied",
            "--output-root", str(tmp_path / "reports"), "--json",
        ], text=True, capture_output=True)
        assert denied.returncode == 1
        assert log.read_text() == before

    broad = subprocess.run([
        "python3", str(PMCTL), "sprint-review", "--jql", jql,
        "--confirm-jql-digest", digest, "--project", "TEST", "--done-status", "Closed",
        "--acli", str(acli), "--title", "Denied", "--output-root", str(tmp_path / "reports"), "--json",
    ], text=True, capture_output=True)
    assert broad.returncode == 1 and log.read_text() == before

    other_jql = 'project = "OTHER" AND status = "Done"'
    cross_project = subprocess.run([
        "python3", str(PMCTL), "sprint-review", "--jql", other_jql,
        "--confirm-jql-digest", hashlib.sha256(other_jql.encode()).hexdigest(),
        "--project", "OTHER", "--acli", str(acli), "--title", "Denied",
        "--output-root", str(tmp_path / "reports"), "--json",
    ], text=True, capture_output=True)
    assert cross_project.returncode == 1
