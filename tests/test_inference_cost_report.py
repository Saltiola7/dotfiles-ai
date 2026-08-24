import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
RATE_CARD = Path(__file__).parents[1] / "private_dot_config/opencode/inference-cost-rates.json"


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
                id text primary key, parent_id text, project_id text, time_created integer, time_updated integer,
                title text, directory text, metadata text, model text, cost real not null,
                tokens_input integer not null, tokens_output integer not null,
                tokens_reasoning integer not null, tokens_cache_read integer not null,
                tokens_cache_write integer not null
            );
            create table message (
                id text primary key, session_id text not null, time_created integer not null,
                time_updated integer not null, data text not null
            );
            create table part (
                id text primary key, message_id text not null, session_id text not null,
                time_created integer not null, time_updated integer not null, data text not null
            );
        """)
        sentinel = "PROHIBITED /Users/private prompt response"
        rows = [
            ("one", None, "project", 1784073600000, 1784073600000, sentinel, sentinel, sentinel,
             json.dumps({"id": "gpt-test", "providerID": "openai", "variant": "medium"}),
             1.25, 100, 20, 5, 40, 0),
            ("two", None, "project", 1784073601000, 1784073601000, sentinel, sentinel, sentinel,
             json.dumps({"id": "gpt-test", "providerID": "openai", "variant": "low"}),
             0, 300, 40, 10, 0, 20),
            ("three", None, "project", 1784073602000, 1784073602000, sentinel, sentinel, sentinel,
             "malformed", 0, 10, 0, 0, 0, 0),
            ("four", None, "project", 1784073603000, 1784073603000, sentinel, sentinel, sentinel,
             "malformed", 0, 1, 0, 0, 0, 0),
            ("boundary", None, "project", 1784073602000, 1784073603000, sentinel, sentinel, sentinel,
             json.dumps({"id": "gpt-boundary", "providerID": "openai"}), 0, 1, 0, 0, 0, 0),
        ]
        connection.executemany("insert into session values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        for session_id, _, _, created, updated, _, _, _, raw_model, cost, *tokens in rows:
            try:
                model = json.loads(raw_model)
            except json.JSONDecodeError:
                model = {}
            message_id = f"message-{session_id}"
            connection.execute("insert into message values (?,?,?,?,?)", (
                message_id, session_id, created, updated,
                json.dumps({"role": "assistant", "providerID": model.get("providerID"),
                            "modelID": model.get("id"), "variant": model.get("variant", "default"),
                            "secret": sentinel}),
            ))
            part_tokens = list(tokens)
            if session_id == "four":
                part_tokens[0] = 2
                part_tokens[1] = -1
            connection.execute("insert into part values (?,?,?,?,?,?)", (
                f"part-{session_id}", message_id, session_id, created, updated,
                json.dumps({"type": "step-finish", "cost": cost,
                            "tokens": {"input": part_tokens[0], "output": part_tokens[1],
                                       "reasoning": part_tokens[2],
                                       "cache": {"read": part_tokens[3], "write": part_tokens[4]}},
                            "secret": sentinel}),
            ))
    connection.commit()
    connection.close()


def test_managed_fast_rates_are_exact_and_effective_dated():
    card = json.loads(RATE_CARD.read_text())
    entries = {(entry["provider"], entry["model"]): entry for entry in card["entries"]}
    expected = {
        "gpt-5.6-sol-fast": {"input": "10", "output": "60", "reasoning": "60", "cache_read": "1", "cache_write": "12.5"},
        "gpt-5.6-terra-fast": {"input": "4", "output": "24", "reasoning": "24", "cache_read": "0.4", "cache_write": "5"},
        "gpt-5.6-luna-fast": {"input": "0.4", "output": "2.4", "reasoning": "2.4", "cache_read": "0.04", "cache_write": "0.5"},
    }

    for model, rates in expected.items():
        entry = entries[("openai", model)]
        assert entry["effective_from"] == 1787443200000
        assert entry["effective_to"] is None
        assert entry["max_input_tokens"] == 272000
        assert entry["usd_per_million_tokens"] == rates


def test_managed_fast_rates_resolve_only_for_exact_effective_identities(tmp_path):
    source = tmp_path / "opencode.db"
    database(source)
    connection = sqlite3.connect(source)
    connection.executescript("delete from part; delete from message; delete from session;")
    boundary = 1787443200000
    models = (
        ("sol", "gpt-5.6-sol-fast", boundary, boundary, 0.1435),
        ("terra", "gpt-5.6-terra-fast", boundary, boundary, 0.0574),
        ("luna", "gpt-5.6-luna-fast", boundary, boundary, 0.00574),
        ("near", "gpt-5.6-sol-fast-preview", boundary, boundary, None),
        ("early", "gpt-5.6-sol-fast", boundary - 1, boundary, None),
    )
    for session_id, model, created, updated, _ in models:
        connection.execute("insert into session values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            session_id, None, "project", created, updated, "PROHIBITED", "PROHIBITED", "PROHIBITED",
            json.dumps({"id": model, "providerID": "openai"}), 0, 1000, 1000, 1000, 1000, 1000,
        ))
        connection.execute("insert into message values (?,?,?,?,?)", (
            f"message-{session_id}", session_id, created, updated,
            json.dumps({"role": "assistant", "providerID": "openai", "modelID": model,
                        "variant": session_id}),
        ))
        connection.execute("insert into part values (?,?,?,?,?,?)", (
            f"part-{session_id}", f"message-{session_id}", session_id, created, updated,
            json.dumps({"type": "step-finish", "cost": 0, "tokens": {
                "input": 1000, "output": 1000, "reasoning": 1000,
                "cache": {"read": 1000, "write": 1000},
            }}),
        ))
    connection.commit()
    connection.close()

    output = tmp_path / "report"
    run("inference-cost-report", "--opencode-db", source, "--output-dir", output, "--rate-card", RATE_CARD)
    report = json.loads((output / "inference-cost-report.json").read_text())
    context = report["contexts"][0]
    resolved = {(item["model"], item["variant"]): item["estimated_cost_usd"]
                for item in context["models"]}
    assert resolved == {
        ("gpt-5.6-luna-fast", "luna"): 0.00574,
        ("gpt-5.6-sol-fast", "sol"): 0.1435,
        ("gpt-5.6-sol-fast", "early"): None,
        ("gpt-5.6-sol-fast-preview", "near"): None,
        ("gpt-5.6-terra-fast", "terra"): 0.0574,
    }
    assert context["estimated_cost_coverage"] == 0.6
    assert len(report["rate_card"]["used_entries"]) == 3


def test_inference_cost_report_reconciles_and_excludes_content(tmp_path):
    source = tmp_path / "opencode.db"
    database(source)
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({
        "schema_version": 1,
        "sessions": {"two": "alpha", "three": "beta", "boundary": "boundary"},
    }))
    state = tmp_path / "state"
    history = state / "reviews/history"
    history.mkdir(parents=True)
    (history / "one.json").write_text(json.dumps({
        "schema_version": 1, "session_id": "one", "completed_at": "1784073600000",
        "method_revision": "3.27", "context": "alpha", "project_digest": "unavailable",
        "cycles": [{"cycle_id": "cycle-alpha", "state": "completed", "context": "alpha",
                    "started_at": 1784073599000, "ended_at": 1784073600500}],
        "aggregates": {}, "reviewed_status": "reviewed",
        "correlation_quality": "exact",
    }))
    (history / "three.json").write_text(json.dumps({
        "schema_version": 1, "session_id": "three", "completed_at": "1784073602000",
        "method_revision": "3.27", "context": "gamma", "project_digest": "unavailable",
        "cycles": [{"cycle_id": "cycle-gamma", "state": "completed", "context": "gamma",
                    "started_at": 1784073601500, "ended_at": 1784073602500}],
        "aggregates": {}, "reviewed_status": "reviewed",
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
        }, {
            "provider": "openai", "model": "gpt-boundary",
            "effective_from": 1784070000000, "effective_to": 1784073602500,
            "max_input_tokens": None, "source": "https://example.invalid/boundary",
            "usd_per_million_tokens": {
                "input": "1", "output": "1", "reasoning": "1",
                "cache_read": "1", "cache_write": "1",
            },
        }],
    }))
    output = tmp_path / "report"

    dry_run = json.loads(run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", mapping, "--state-root", state, "--rate-card", rates, "--dry-run",
    ).stdout)
    assert dry_run["planned_session_count"] == 5
    assert dry_run["planned_usage_count"] == 5
    assert dry_run["unreconciled_session_count"] == 1
    assert not output.exists()

    run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", mapping, "--state-root", state, "--rate-card", rates,
    )
    report = json.loads((output / "inference-cost-report.json").read_text())
    alpha = next(item for item in report["contexts"] if item["bounded_context"] == "alpha")
    ambiguous = next(item for item in report["contexts"] if item["bounded_context"] == "MULTI_CONTEXT")
    unknown = next(item for item in report["contexts"] if item["bounded_context"] == "UNKNOWN")
    boundary = next(item for item in report["contexts"] if item["bounded_context"] == "boundary")
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
    assert alpha["models"][0]["rate_entry_ids"]
    assert alpha["attribution_confidence"] == {"HIGH": 1, "MEDIUM": 1, "UNAVAILABLE": 0}
    assert alpha["attribution_sources"]["DBSCTR_HISTORY"] == 1
    assert ambiguous["estimated_cost_usd"] is None
    assert ambiguous["attribution_sources"]["CONFLICT"] == 1
    assert unknown["session_count"] == 1
    assert unknown["tokens_per_session_stats"]["population_standard_deviation"] == 0
    assert boundary["estimated_cost_usd"] is None
    assert report["totals"]["session_count"] == 5
    assert report["schema_version"] == 2
    assert report["totals"]["reconciled_session_count"] == 4
    assert report["totals"]["unreconciled_session_count"] == 1
    assert report["totals"]["reconciliation_coverage"] == 0.998172
    assert report["source_snapshot"]["part_ceiling"] == 5
    assert report["source_snapshot"]["message_ceiling"] == 5
    assert report["source_snapshot"]["capabilities"]["adapter"] == "opencode_step_finish_v2"
    assert len(report["rate_card"]["used_entries"]) == 1
    assert len(report["source_snapshot"]["attribution_digest"]) == 64
    persisted = "".join(path.read_text() for path in output.iterdir())
    assert "PROHIBITED" not in persisted
    assert "/Users/private" not in persisted
    assert "\"one\"" not in persisted
    assert "Actual coverage" in (output / "inference-cost-report.md").read_text()
    assert "Reconciliation coverage" in (output / "inference-cost-report.md").read_text()

    first_report = (output / "inference-cost-report.json").read_text()
    backup = output.parent / ".report-backup"
    shutil.copytree(output, backup)
    run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", mapping, "--state-root", state, "--rate-card", rates,
    )
    assert not backup.exists()
    assert (output / "inference-cost-report.json").read_text() == first_report

    output.rename(backup)
    run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", mapping, "--state-root", state, "--rate-card", rates,
    )
    assert output.is_dir() and not backup.exists()
    assert (output / "inference-cost-report.json").read_text() == first_report

    shutil.copytree(output, backup)
    (output / "inference-cost-report.json").write_text("corrupt\n")
    run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", mapping, "--state-root", state, "--rate-card", rates,
    )
    assert not backup.exists()
    assert (output / "inference-cost-report.json").read_text() == first_report


def test_inference_cost_report_fails_before_replacing_outputs(tmp_path):
    source = tmp_path / "unsupported.db"
    database(source, supported=False)
    output = tmp_path / "report"
    output.mkdir()
    prior = output / "inference-cost-report.json"
    prior.write_text("prior\n")
    missing_mapping = tmp_path / "secret-mapping-name.json"
    private_error = run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--mapping", missing_mapping,
        "--rate-card", Path(__file__).parents[1] / "private_dot_config/opencode/inference-cost-rates.json",
        ok=False,
    )
    assert str(missing_mapping) not in private_error.stderr
    unsafe_rates = tmp_path / "unsafe-rates.json"
    value = json.loads((Path(__file__).parents[1] / "private_dot_config/opencode/inference-cost-rates.json").read_text())
    value["entries"][0]["source"] = "https://secret@example.invalid/pricing?token=private"
    unsafe_rates.write_text(json.dumps(value))
    unsafe = run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--rate-card", unsafe_rates, ok=False,
    )
    assert "secret" not in unsafe.stderr and "token" not in unsafe.stderr
    result = run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--rate-card", Path(__file__).parents[1] / "private_dot_config/opencode/inference-cost-rates.json",
        ok=False,
    )
    assert "missing required metadata columns" in result.stderr
    assert prior.read_text() == "prior\n"

    aliases = tmp_path / "aliases.db"
    connection = sqlite3.connect(aliases)
    connection.execute("create table session (id text, timecreated integer, timeupdated integer, model text, "
                       "cost real, tokensinput integer, tokensoutput integer, tokensreasoning integer, "
                       "tokenscacheread integer, tokenscachewrite integer)")
    connection.close()
    alias_result = run(
        "inference-cost-report", "--opencode-db", aliases, "--output-dir", output,
        "--rate-card", Path(__file__).parents[1] / "private_dot_config/opencode/inference-cost-rates.json",
        ok=False,
    )
    assert "missing required metadata columns" in alias_result.stderr


def test_inference_cost_report_splits_one_session_by_context_interval(tmp_path):
    source = tmp_path / "opencode.db"
    database(source)
    connection = sqlite3.connect(source)
    connection.execute("delete from part")
    connection.execute("delete from message")
    connection.execute("delete from session")
    base = 1784073600000
    connection.execute("insert into session values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        "shared", None, "project", base, base + 5000, "PROHIBITED", "PROHIBITED", "PROHIBITED",
        None, 10, 100, 0, 0, 0, 0,
    ))
    for index, (offset, cost, tokens) in enumerate(((500, 1, 10), (1500, 2, 20),
                                                    (2500, 3, 30), (3500, 4, 40))):
        message_id = f"message-{index}"
        connection.execute("insert into message values (?,?,?,?,?)", (
            message_id, "shared", base + offset, base + offset,
            json.dumps({"role": "assistant", "providerID": "openai", "modelID": "gpt-test"}),
        ))
        connection.execute("insert into part values (?,?,?,?,?,?)", (
            f"part-{index}", message_id, "shared", base + offset, base + offset,
            json.dumps({"type": "step-finish", "cost": cost,
                        "tokens": {"input": tokens, "output": 0, "reasoning": 0,
                                   "cache": {"read": 0, "write": 0}}}),
        ))
    connection.commit()
    connection.close()
    state = tmp_path / "state"
    history = state / "reviews/history"
    history.mkdir(parents=True)
    (history / "shared.json").write_text(json.dumps({
        "schema_version": 1, "session_id": "shared", "completed_at": str(base + 5000),
        "method_revision": "3.27", "context": "unavailable", "project_digest": "unavailable",
        "cycles": [
            {"cycle_id": "alpha-cycle", "state": "completed", "context": "alpha",
             "started_at": base, "ended_at": base + 1000},
            {"cycle_id": "beta-cycle", "state": "completed", "context": "beta",
             "started_at": base + 1000, "ended_at": base + 3000},
            {"cycle_id": "gamma-cycle", "state": "completed", "context": "gamma",
             "started_at": base + 2000, "ended_at": base + 3000},
            {"cycle_id": "old-cycle", "state": "abandoned", "context": "old",
             "started_at": base + 3000, "ended_at": None},
        ],
        "aggregates": {}, "reviewed_status": "reviewed", "correlation_quality": "ambiguous",
    }))
    for path in (state / "reviews", history):
        path.chmod(0o700)
    (history / "shared.json").chmod(0o600)
    rates = tmp_path / "rates.json"
    rates.write_text(json.dumps({"schema_version": 1, "currency": "USD",
                                 "retrieved_at": "2026-07-30", "entries": []}))
    output = tmp_path / "report"

    run("inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--state-root", state, "--rate-card", rates)
    report = json.loads((output / "inference-cost-report.json").read_text())
    contexts = {item["bounded_context"]: item for item in report["contexts"]}
    assert contexts["alpha"]["input_tokens"] == 10
    assert contexts["beta"]["input_tokens"] == 20
    assert contexts["MULTI_CONTEXT"]["input_tokens"] == 30
    assert contexts["UNKNOWN"]["input_tokens"] == 40
    assert report["totals"]["session_count"] == 1
    assert report["totals"]["usage_count"] == 4


def test_inference_cost_report_rejects_orphaned_canonical_part(tmp_path):
    source = tmp_path / "opencode.db"
    database(source)
    connection = sqlite3.connect(source)
    connection.execute("delete from message where id='message-one'")
    connection.commit()
    connection.close()
    output = tmp_path / "report"
    result = run(
        "inference-cost-report", "--opencode-db", source, "--output-dir", output,
        "--rate-card", Path(__file__).parents[1] / "private_dot_config/opencode/inference-cost-rates.json",
        ok=False,
    )
    assert "canonical usage metadata contains invalid values" in result.stderr
    assert not output.exists()
