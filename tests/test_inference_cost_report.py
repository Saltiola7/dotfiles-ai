import json
import sqlite3
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"


def run(*args, ok=True):
    result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], text=True, capture_output=True)
    assert (result.returncode == 0) is ok, result.stderr
    return result


def database(path, supported=True):
    connection = sqlite3.connect(path)
    if not supported:
        connection.execute("create table session (id text primary key, title text)")
    else:
        connection.executescript("""
            create table session (
                id text primary key, parent_id text, project_id text, time_created integer,
                title text, directory text, metadata text, model text, cost real not null,
                tokens_input integer not null, tokens_output integer not null,
                tokens_reasoning integer not null, tokens_cache_read integer not null,
                tokens_cache_write integer not null
            );
        """)
        sentinel = "PROHIBITED /Users/private prompt response"
        rows = [
            ("one", None, "project", 1784073600000, sentinel, sentinel, sentinel,
             json.dumps({"id": "gpt-test", "providerID": "openai", "variant": "medium"}),
             1.25, 100, 20, 5, 40, 0),
            ("two", None, "project", 1784073601000, sentinel, sentinel, sentinel,
             json.dumps({"id": "gpt-test", "providerID": "openai", "variant": "low"}),
             0, 300, 40, 10, 0, 20),
            ("three", None, "project", 1784073602000, sentinel, sentinel, sentinel,
             "malformed", 0, 10, 0, 0, 0, 0),
            ("four", None, "project", 1784073603000, sentinel, sentinel, sentinel,
             "malformed", 0, 1, 0, 0, 0, 0),
        ]
        connection.executemany("insert into session values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    connection.commit()
    connection.close()


def test_inference_cost_report_reconciles_and_excludes_content(tmp_path):
    source = tmp_path / "opencode.db"
    database(source)
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({
        "schema_version": 1,
        "sessions": {"two": "alpha", "three": "beta"},
    }))
    state = tmp_path / "state"
    history = state / "reviews/history"
    history.mkdir(parents=True)
    (history / "one.json").write_text(json.dumps({
        "schema_version": 1, "session_id": "one", "completed_at": "1784073600000",
        "method_revision": "3.27", "context": "alpha", "project_digest": "unavailable",
        "cycles": [], "aggregates": {}, "reviewed_status": "reviewed",
        "correlation_quality": "exact",
    }))
    (history / "three.json").write_text(json.dumps({
        "schema_version": 1, "session_id": "three", "completed_at": "1784073602000",
        "method_revision": "3.27", "context": "gamma", "project_digest": "unavailable",
        "cycles": [], "aggregates": {}, "reviewed_status": "reviewed",
        "correlation_quality": "exact",
    }))
    for path in (state / "reviews", history):
        path.chmod(0o700)
    (history / "one.json").chmod(0o600)
    (history / "three.json").chmod(0o600)
    rates = tmp_path / "rates.json"
    rates.write_text(json.dumps({
        "schema_version": 1,
        "currency": "USD",
        "retrieved_at": "2026-07-30",
        "entries": [{
            "provider": "openai", "model": "gpt-test",
            "effective_from": 1784070000000, "effective_to": None,
            "max_input_tokens": None,
            "source": "https://example.invalid/pricing",
            "usd_per_million_tokens": {
                "input": "5", "output": "30", "reasoning": "30",
                "cache_read": "0.5", "cache_write": "6.25",
            },
        }],
    }))
    output = tmp_path / "report"

    dry_run = json.loads(run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", mapping, "--state-root", state, "--rate-card", rates, "--dry-run",
    ).stdout)
    assert dry_run["planned_session_count"] == 4
    assert not output.exists()

    run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", mapping, "--state-root", state, "--rate-card", rates,
    )
    report = json.loads((output / "inference-cost-report.json").read_text())
    alpha = next(item for item in report["contexts"] if item["bounded_context"] == "alpha")
    ambiguous = next(item for item in report["contexts"] if item["bounded_context"] == "MULTI_CONTEXT")
    unknown = next(item for item in report["contexts"] if item["bounded_context"] == "UNKNOWN")
    assert alpha["session_count"] == 2
    assert alpha["input_tokens"] == 400
    assert alpha["actual_cost_usd"] == 1.25
    assert alpha["actual_cost_coverage"] == 0.308411
    assert alpha["estimated_cost_usd"] == 0.004395
    assert alpha["estimated_cost_coverage"] == 1.0
    assert alpha["tokens_per_session_stats"] == {
        "min": 165, "p25": 165, "mean": 267.5, "median": 267.5,
        "p75": 370, "p95": 370, "max": 370, "population_standard_deviation": 102.5,
    }
    assert alpha["models"][0]["provider"] == "openai"
    assert ambiguous["estimated_cost_usd"] is None
    assert unknown["session_count"] == 1
    assert report["totals"]["session_count"] == 4
    assert len(report["source_snapshot"]["attribution_digest"]) == 64
    persisted = "".join(path.read_text() for path in output.iterdir())
    assert "PROHIBITED" not in persisted
    assert "/Users/private" not in persisted
    assert "\"one\"" not in persisted


def test_inference_cost_report_fails_before_replacing_outputs(tmp_path):
    source = tmp_path / "unsupported.db"
    database(source, supported=False)
    output = tmp_path / "report"
    output.mkdir()
    prior = output / "inference-cost-report.json"
    prior.write_text("prior\n")
    result = run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--rate-card", Path(__file__).parents[1] / "private_dot_config/opencode/inference-cost-rates.json",
        ok=False,
    )
    assert "missing required metadata columns" in result.stderr
    assert prior.read_text() == "prior\n"
