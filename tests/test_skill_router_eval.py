"""Offline contracts for explicitly invoked native skill-routing qualification."""

import copy
import json
import sys
import shutil
from types import SimpleNamespace
from collections import Counter, defaultdict
from pathlib import Path

import pytest

import skill_router_eval as evaluation


FIXTURES = Path(__file__).parent / "fixtures/skill_router"


def suite():
    cases = evaluation.load_cases(FIXTURES / "cases.json")
    oracle = evaluation.load_oracle(FIXTURES / "oracle.json", cases)
    return cases, oracle


def final_output():
    return {
        "assessment": "Task ownership and cleanup need a bounded assessment.",
        "proposed_changes": ["Preserve the caller cancellation boundary."],
        "validation": ["Use existing project tests on supported runtimes."],
        "limitations": ["No runtime or external target was exercised."],
    }


@pytest.fixture
def guidance(tmp_path):
    root = tmp_path / "guidance with spaces"
    skill = root / "async-python-patterns"
    skill.mkdir(parents=True)
    entry = skill / "SKILL.md"
    entry.write_text(
        "---\nname: async-python-patterns\ndescription: Review owned concurrent work.\n---\n\n"
        "# Async task ownership\n\n"
        "## Method\n\n"
        "Cancel sibling tasks when this operation fails, then await their completion.\n"
        "Keep the shared session alive until every owned task has been drained.\n"
    )
    resource = skill / "references/cancellation.md"
    resource.parent.mkdir()
    resource.write_text(
        "# Cancellation details\n\n"
        "Caller cancellation must propagate after owned child tasks have completed cleanup.\n"
        "Keep cleanup failures visible rather than reporting successful completion.\n"
    )
    return root, entry, resource


def native_events(entry, *, output=None, exit_code=0, usage=None, command=None):
    if usage is None:
        usage = {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20}
    return [
        {"type": "thread.started", "thread_id": "synthetic-native-thread"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {
            "id": "command-1", "type": "command_execution", "status": "completed",
            "command": command or f"cat '{entry}'",
            "aggregated_output": entry.read_text() if output is None else output,
            "exit_code": exit_code,
        }},
        {"type": "item.completed", "item": {
            "id": "answer-1", "type": "agent_message", "text": json.dumps(final_output()),
        }},
        {"type": "turn.completed", "usage": usage},
    ]


def test_frozen_population_has_balanced_pairs_and_complete_denominator():
    cases, oracle = suite()
    plan = evaluation.build_plan(cases)
    assert len(cases["cases"]) == len(oracle["cases"]) == 14
    assert len(plan) == 46
    development = [row["arm"] for row in plan if row["split"] == "development"]
    assert development == ["baseline"] * 4 + ["candidate"] * 4
    assert Counter(row["split"] for row in plan) == {
        "development": 8, "heldout": 32, "navigation": 4, "omission": 2,
    }
    pairs = defaultdict(list)
    for row in plan:
        pairs[row["case_id"], row["repetition"]].append(row)
    assert all({row["arm"] for row in pair} == {"baseline", "candidate"} for pair in pairs.values())
    for case in cases["cases"]:
        if case["split"] in {"heldout", "navigation"}:
            first = [row["arm"] for row in pairs[case["id"], 1]]
            second = [row["arm"] for row in pairs[case["id"], 2]]
            assert first == list(reversed(second)), "repeated pairs must balance arm order"


def test_oracle_is_separate_and_rootless_optional_policy_is_predeclared():
    cases, oracle = suite()
    assert oracle["amendment"]["model_outcomes_observed"] is False
    changed = oracle["cases"][oracle["amendment"]["case_id"]]
    assert changed["required_tracked_skills"] == ["podman-quadlet"]
    assert changed["allowed_additional_tracked_skills"] == ["linux-host-diagnostics"]
    for index, case in enumerate(cases["cases"]):
        assert set(case["input"]) == {"request", "files", "execution_scope"}, index
        rendered = json.dumps(case["input"])
        assert "required_tracked_skills" not in rendered, index
        assert "forbidden_tracked_skills" not in rendered, index
        assert "decision_checks" not in rendered, index
        assert not any(name in rendered for name in cases["tracked_skills"]), index
    schema = json.loads((FIXTURES / "output.schema.json").read_text())
    assert set(schema["required"]) == set(schema["properties"]) == set(final_output())
    assert schema["additionalProperties"] is False
    assert "selected_skills" not in schema["properties"]


@pytest.mark.parametrize("mutation", ["duplicate-id", "escaped-file", "absolute-file", "oracle-in-input"])
def test_invalid_case_population_is_rejected(tmp_path, mutation):
    cases = json.loads((FIXTURES / "cases.json").read_text())
    if mutation == "duplicate-id":
        cases["cases"][1]["id"] = cases["cases"][0]["id"]
    elif mutation == "escaped-file":
        cases["cases"][0]["input"]["files"] = {"../oracle.json": "outside fixture"}
    elif mutation == "absolute-file":
        cases["cases"][0]["input"]["files"] = {"/tmp/oracle.json": "outside fixture"}
    else:
        cases["cases"][0]["input"]["oracle"] = {"expected": "not model input"}
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(cases))
    with pytest.raises(ValueError):
        evaluation.load_cases(path)


def test_actual_successful_method_content_and_usage_are_observed(guidance):
    root, entry, resource = guidance
    result = evaluation.parse_events(native_events(entry), root)
    assert result["status"] == "complete"
    assert result["usage"] == {
        "input_tokens": 100, "cached_input_tokens": 40,
        "output_tokens": 20, "reasoning_output_tokens": None,
    }
    assert result["final_output"] == final_output()
    assert any(row["skill"] == "async-python-patterns" and row["extent"] == "full" for row in result["reads"])
    excerpt = evaluation.parse_events(native_events(resource), root)
    assert any(row["skill"] == "async-python-patterns" for row in excerpt["reads"])


@pytest.mark.parametrize("kind", ["mention", "metadata", "failed-command", "not-completed"])
def test_path_claims_and_failed_reads_are_not_method_loading(guidance, kind):
    root, entry, _ = guidance
    events = native_events(entry)
    command = events[2]["item"]
    if kind == "mention":
        command["command"] = f"printf '%s' '{entry}'"
        command["aggregated_output"] = str(entry)
    elif kind == "metadata":
        command["aggregated_output"] = "---".join(entry.read_text().split("---")[:2]) + "---\n"
    elif kind == "failed-command":
        command["exit_code"] = 1
    else:
        events[2]["type"] = "item.started"
    result = evaluation.parse_events(events, root)
    assert result["reads"] == []


@pytest.mark.parametrize("value", [True, -1, "100", 1.5])
def test_invalid_usage_cannot_be_coerced_to_a_success(guidance, value):
    root, entry, _ = guidance
    usage = {"input_tokens": value, "cached_input_tokens": 0, "output_tokens": 20}
    with pytest.raises(ValueError):
        evaluation.parse_events(native_events(entry, usage=usage), root)


def test_missing_usage_and_terminal_failure_remain_unavailable_or_failed(guidance):
    root, entry, _ = guidance
    events = native_events(entry, usage={"input_tokens": 100, "output_tokens": 20})
    missing = evaluation.parse_events(events, root)
    assert missing["usage"]["cached_input_tokens"] is None
    assert missing["status"] == "unavailable"
    failed = evaluation.parse_events(native_events(entry), root, returncode=23)
    assert failed["status"] != "complete"
    unfinished = evaluation.parse_events(native_events(entry)[:-1], root)
    assert unfinished["status"] != "complete"


def test_answer_skill_claim_cannot_replace_a_method_read(guidance):
    root, entry, _ = guidance
    events = native_events(entry, output="Only unrelated command output.\n")
    result = final_output()
    result["assessment"] = "I used async-python-patterns."
    events[3]["item"]["text"] = json.dumps(result)
    observation = evaluation.parse_events(events, root)
    scored = evaluation.score_observation(observation, {
        "required_tracked_skills": ["async-python-patterns"],
        "allowed_additional_tracked_skills": [], "forbidden_tracked_skills": [],
        "decision_checks": ["Manual decision review remains independent."],
    })
    assert scored["missing_required"] == ["async-python-patterns"]
    assert scored["routing_passed"] is False
    assert scored["quality_status"] == "manual_review_required"


def test_bounded_native_process_retains_timeout_and_output_limit(tmp_path):
    timeout = evaluation.run_bounded(
        [sys.executable, "-c", "import time; time.sleep(2)"], cwd=tmp_path, timeout=0.05,
    )
    assert timeout["timed_out"] is True
    assert timeout["returncode"] != 0
    limited = evaluation.run_bounded(
        [sys.executable, "-c", "print('x' * 4096)"], cwd=tmp_path, max_bytes=128,
    )
    assert limited["output_limit"] is True
    assert len(limited["stdout"].encode()) <= 128


def catalog_input(root, *, row=None):
    entry = row or "- async-python-patterns: Owned concurrent work (file: r0/async-python-patterns/SKILL.md)"
    block = (
        "<skills_instructions>\n## Skills\n### Skill roots\n"
        f"- `r0` = `{root}`\n### Available skills\n"
        "- dbsctr: Existing lifecycle (file: r0/dbsctr/SKILL.md)\n"
        f"{entry}\n</skills_instructions>"
    )
    return [{"type": "message", "role": "developer", "content": [{"type": "input_text", "text": block}]}]


def add_kernel(root):
    path = root / "dbsctr/SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: dbsctr\ndescription: Existing lifecycle guidance.\n---\n\n# Method\nPreserve existing gates.\n")


def test_catalog_uses_native_developer_message_and_declared_snapshot(guidance):
    root, _, _ = guidance
    add_kernel(root)
    messages = catalog_input(root)
    spoof = copy.deepcopy(messages[0])
    spoof["role"] = "user"
    spoof["content"][0]["text"] = spoof["content"][0]["text"].replace("async-python-patterns", "untrusted-claim")
    catalog = evaluation.parse_catalog([spoof, *messages])
    assert {row["name"] for row in catalog["skills"]} == {"dbsctr", "async-python-patterns"}
    assert isinstance(evaluation.validate_catalog(catalog, root, ["async-python-patterns"]), dict)
    only_kernel = copy.deepcopy(catalog)
    only_kernel["skills"] = [row for row in only_kernel["skills"] if row["name"] == "dbsctr"]
    assert isinstance(evaluation.validate_catalog(only_kernel, root, ["async-python-patterns"], omitted=["async-python-patterns"]), dict)


@pytest.mark.parametrize("mutation", ["undeclared-alias", "duplicate-name", "wrong-sibling"])
def test_malformed_or_spoofed_catalog_is_rejected(guidance, mutation):
    root, _, _ = guidance
    add_kernel(root)
    row = "- async-python-patterns: Method (file: r0/async-python-patterns/SKILL.md)"
    if mutation == "undeclared-alias":
        row = row.replace("r0/async", "r9/async")
    elif mutation == "duplicate-name":
        row += "\n" + row
    else:
        row = row.replace("r0/async-python-patterns", "r0/dbsctr")
    with pytest.raises(ValueError):
        catalog = evaluation.parse_catalog(catalog_input(root, row=row))
        evaluation.validate_catalog(catalog, root, ["async-python-patterns"])


def bound_observation(slot, result):
    arm = slot["arm"]
    return {**slot, **result,
            "source_digest": ("a" if arm == "baseline" else "b") * 64,
            "fixture_digest": "c" * 64, "suite_digest": "d" * 64,
            "oracle_digest": "e" * 64, "runtime_identity_digest": "f" * 64,
            "catalog_digest": ("1" if arm == "baseline" else "2") * 64,
            "ambient_catalog_digest": "3" * 64,
            "client_version": "synthetic-native-client", "model": "configured-model",
            "provider": "configured-provider"}


def test_aggregate_preserves_missing_failed_and_mismatched_attempts(guidance):
    root, entry, _ = guidance
    cases, _ = suite()
    full_plan = evaluation.build_plan(cases)
    selected = next(row for row in full_plan if row["split"] == "heldout")
    plan = [row for row in full_plan if row["case_id"] == selected["case_id"] and row["repetition"] == selected["repetition"]]
    first = bound_observation(plan[0], evaluation.parse_events(native_events(entry), root))
    missing = evaluation.aggregate(plan, [first])
    assert missing["planned"] == 2 and missing["observed"] == 1 and missing["missing"] == 1
    with pytest.raises(ValueError):
        evaluation.aggregate(plan, [first, first])
    second = bound_observation(plan[1], evaluation.parse_events(native_events(entry), root, returncode=23))
    failed = evaluation.aggregate(plan, [first, second])
    assert failed["failed"] == 1 and failed["complete"] == 1
    drifted = copy.deepcopy(second)
    drifted["fixture_digest"] = "4" * 64
    with pytest.raises(ValueError):
        evaluation.aggregate(plan, [first, drifted])


def test_snapshot_copies_complete_guidance_outside_source(tmp_path, guidance):
    original, _, _ = guidance
    add_kernel(original)
    source = tmp_path / "source"
    selected = source / "dot_agents/skills"
    shutil.copytree(original, selected)
    cache = selected / "dbsctr/__pycache__/generated.cpython-313.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"generated interpreter cache, not managed guidance")
    snapshot = tmp_path / "private-snapshot"
    manifest = evaluation.prepare_snapshot(source, snapshot, ["async-python-patterns"])
    assert set(manifest["files"]) == {
        "dbsctr/SKILL.md", "async-python-patterns/SKILL.md",
        "async-python-patterns/references/cancellation.md",
    }
    for relative in manifest["files"]:
        assert (snapshot / "skills" / relative).read_bytes() == (selected / relative).read_bytes()
    with pytest.raises(ValueError):
        evaluation.prepare_snapshot(source, source / "nested-snapshot", ["async-python-patterns"])


@pytest.mark.parametrize("mutation", ["missing-field", "self-reported-selection"])
def test_malformed_final_assessment_cannot_complete(guidance, mutation):
    root, entry, _ = guidance
    events = native_events(entry)
    output = final_output()
    if mutation == "missing-field":
        del output["limitations"]
    else:
        output["selected_skills"] = ["async-python-patterns"]
    events[3]["item"]["text"] = json.dumps(output)
    with pytest.raises(ValueError):
        evaluation.parse_events(events, root)


def test_native_execution_requires_explicit_opt_in_before_access(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("unapproved native invocation or fixture access")
    monkeypatch.setattr(evaluation, "run_bounded", forbidden)
    monkeypatch.setattr(evaluation, "load_cases", forbidden)
    with pytest.raises(ValueError, match="--allow-native"):
        evaluation.run_one(SimpleNamespace(allow_native=False))


def test_shared_project_boundaries_do_not_attribute_another_method(guidance):
    root, entry, _ = guidance
    common = (
        "The current primary owns lifecycle decisions and existing approval boundaries.\n"
        "Project policy selects the runtime, dependencies and acceptance authorities.\n"
    )
    entry.write_text(entry.read_text().replace("## Method\n\n", "## Project boundaries\n\n" + common + "\n## Method\n\n"))
    other = root / "python-design-patterns/SKILL.md"
    other.parent.mkdir()
    other.write_text(
        "---\nname: python-design-patterns\ndescription: Assess component responsibilities.\n---\n\n"
        "# Component responsibilities\n\n## Project boundaries\n\n" + common +
        "\n## Method\n\n"
        "Separate business decisions from concrete transport and filesystem access.\n"
        "Keep dependency direction explicit without introducing an unnecessary hierarchy.\n"
    )
    command = f"cat '{entry}'; rg 'unmatched text' '{other}'; true"
    result = evaluation.parse_events(native_events(entry, command=command), root)
    assert {row["skill"] for row in result["reads"]} == {"async-python-patterns"}


def test_native_raw_output_cannot_target_public_source(monkeypatch, tmp_path):
    case = {"id": "synthetic-private-output", "split": "development", "input": {
        "request": "Assess synthetic source only.", "files": {}, "execution_scope": "Read only.",
    }}
    slot = {"case_id": case["id"], "arm": "baseline", "repetition": 1, "order": 1, "split": "development"}
    cases = {"tracked_skills": ["async-python-patterns"], "cases": [case]}
    monkeypatch.setattr(evaluation, "load_cases", lambda *args: cases)
    monkeypatch.setattr(evaluation, "load_oracle", lambda *args: {"cases": {case["id"]: {}}})
    monkeypatch.setattr(evaluation, "build_plan", lambda *args: [slot])
    monkeypatch.setattr(evaluation, "verify_snapshot", lambda *args: {"tracked_skills": cases["tracked_skills"], "source_digest": "a" * 64})
    monkeypatch.setattr(evaluation, "_identity", lambda *args: {"client_version": "synthetic", "model": "configured", "provider": "configured"})
    def forbidden(*args, **kwargs):
        pytest.fail("raw capture attempted a public-source write or native invocation")
    monkeypatch.setattr(evaluation, "run_bounded", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    public_output = Path(evaluation.__file__).resolve().parents[1] / "tests/prohibited-native-capture"
    args = SimpleNamespace(
        allow_native=True, cases="not-opened", oracle="not-opened", case_id=case["id"],
        arm="baseline", repetition=1, order=1, snapshot=tmp_path / "snapshot",
        identity="not-opened", output=public_output,
    )
    with pytest.raises(ValueError, match="private|source"):
        evaluation.run_one(args)


def test_timeout_terminates_owned_descendants_after_parent_exit(monkeypatch, tmp_path):
    import os
    import signal
    original_popen = evaluation.subprocess.Popen
    original_killpg = os.killpg
    owned_groups, signals = set(), []
    def start_owned(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        assert kwargs["start_new_session"] is True
        owned_groups.add(process.pid)
        return process
    def terminate_owned(group, sig):
        assert group in owned_groups, "never signal an unrelated process group"
        signals.append((group, sig))
        return original_killpg(group, sig)
    monkeypatch.setattr(evaluation.subprocess, "Popen", start_owned)
    monkeypatch.setattr(evaluation.os, "killpg", terminate_owned)
    child = None
    try:
        code = (
            "import subprocess,sys; "
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(3)']); "
            "print(p.pid,flush=True)"
        )
        result = evaluation.run_bounded([sys.executable, "-c", code], cwd=tmp_path, timeout=0.5)
        child = int(result["stdout"].strip())
        assert result["returncode"] == 0, "exercise an exited parent with live descendant pipes"
        assert result["timed_out"] is True
        assert any(sig == signal.SIGKILL for _, sig in signals), "owned descendants outlived the bounded call"
    finally:
        if child is not None:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_known_native_web_search_duplicate_ids_remain_unscored_opaque_values(guidance):
    root, entry, _ = guidance
    opaque = "exec-12345678-1234-1234-1234-123456789abc"
    raw = '\n'.join([
        json.dumps(native_events(entry)[0]),
        '{"type":"item.started","item":{"id":"item_6","type":"web_search",'
        '"id":"' + opaque + '","query":"synthetic public reference","action":{"type":"search"}}}',
        '{"type":"item.completed","item":{"id":"item_6","type":"web_search",'
        '"id":"' + opaque + '","query":"synthetic public reference",'
        '"action":{"type":"open_page","url":"https://example.test"},"results":[]}}',
        *[json.dumps(event) for event in native_events(entry)[1:]],
    ])
    events = evaluation.decode_native_events(raw)
    web = [event["item"] for event in events if event.get("item", {}).get("type") == "web_search"]
    assert len(web) == 2
    assert all("id" not in item and item["opaque_ids"] == ["item_6", opaque] for item in web)
    result = evaluation.parse_events(events, root)
    assert result["status"] == "complete"
    assert result["usage"]["input_tokens"] == 100
    assert len(result["serialization_warnings"]) == 2
    assert all(row["code"] == "native_web_search_duplicate_id" for row in result["serialization_warnings"])
    assert {row["skill"] for row in result["reads"]} == {"async-python-patterns"}


@pytest.mark.parametrize("raw", [
    '{"type":"turn.completed","usage":{"input_tokens":1,"input_tokens":2}}',
    '{"type":"item.completed","item":{"id":"item_1","type":"command_execution","id":"other"}}',
    '{"type":"item.completed","item":{"id":"item_1","type":"web_search",'
    '"id":"exec-12345678-1234-1234-1234-123456789abc","query":"a","query":"b","action":{},"results":[]}}',
    '{"type":"item.completed","item":{"id":"item_1","type":"web_search",'
    '"id":"exec-12345678-1234-1234-1234-123456789abc","query":"a","action":{"type":"a","type":"b"},"results":[]}}',
    '{"type":"item.completed","item":{"id":"item_1","type":"web_search",'
    '"id":"exec-12345678-1234-1234-1234-123456789abc","id":"third","query":"a","action":{},"results":[]}}',
])
def test_native_decoder_does_not_weaken_other_duplicate_boundaries(raw):
    with pytest.raises(ValueError):
        evaluation.decode_native_events(raw)
    with pytest.raises(ValueError):
        json.loads('{"field":1,"field":2}', object_pairs_hook=evaluation._pairs)


def test_nonfatal_native_hook_diagnostic_is_retained_with_successful_usage(guidance):
    root, entry, _ = guidance
    events = native_events(entry)
    message = "clamping SessionEnd hook timeout to 3s in /synthetic/native/config.toml"
    events.insert(1, {"type": "item.completed", "item": {
        "id": "item_warning", "type": "error", "message": message,
    }})
    result = evaluation.parse_events(events, root)
    assert result["status"] == "complete"
    assert result["usage"]["cached_input_tokens"] == 40
    assert result["item_diagnostics"] == [{
        "item_type": "error", "item_id": "item_warning", "message": message,
    }]
