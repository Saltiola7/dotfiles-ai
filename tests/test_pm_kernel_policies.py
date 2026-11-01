import builtins
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import example, given, settings, strategies as st


ROOT = Path(__file__).resolve().parents[1]
PMCTL = ROOT / "dot_local/bin/executable_pmctl"


def load_pmctl() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader("pmctl_policy_properties", str(PMCTL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


pm = load_pmctl()
PROPERTY = settings(max_examples=100, derandomize=True, database=None,
                    deadline=None, print_blob=True, suppress_health_check=())
SAFE_TEXT = st.text(alphabet="azAZ09 é界🙂", min_size=1, max_size=64)
TEXT = st.text(max_size=512)
KEYS = st.from_regex(r"[a-z][a-z0-9_]{0,15}", fullmatch=True)

# These reviewed examples stand independently of the production allowlists.
SOURCE_CASES: list[tuple[str, dict[str, object], str]] = [
    ("cycle_record", {"cycle_id": "cycle-1", "context": "example", "state": "completed",
                      "risk": "routine", "delivery_intent": "local", "method_revision": "3",
                      "schema_version": 4, "gates": {}}, "cycle_id"),
    ("review_report", {"report_id": "review-1", "decision": "accept", "findings": []}, "report_id"),
    ("history_capture", {"capture_id": "capture-1", "manifest_digest": "abc", "members": []}, "capture_id"),
    ("history_telemetry", {"cycle_id": "cycle-1", "metrics": {}, "availability": "available"}, "cycle_id"),
    ("benchmark", {"benchmark_id": "bench-1", "result": "pass", "metrics": {}}, "benchmark_id"),
    ("provider_evaluation", {"report_id": "provider-1", "manifest_digest": "abc",
                             "rubric": {"name": "quality", "version": "1", "digest": "abc"},
                             "members": [], "findings": [], "recommendations": []}, "report_id"),
    ("phase_profile", {"cycle_id": "cycle-1", "phase_profile": {}, "availability": "available"}, "cycle_id"),
    ("execution_dag", {"cycle_id": "cycle-1", "nodes": [], "result": "pass"}, "cycle_id"),
    ("improvement", {"worker_id": "worker-1", "opportunity_id": "opportunity-1",
                     "priority": "P2", "state": "open", "summary": "Synthetic example"}, "worker_id"),
]


def envelope(payload: dict[str, object], availability: str = "available") -> dict[str, object]:
    return {"schema_version": 1, "source_id": "source-1", "source_authority": "dbsctr",
            "availability": availability, "payload": payload}


def rejects(action: Callable[[], object], message: str) -> None:
    with pytest.raises(RuntimeError) as caught:
        action()
    assert str(caught.value) == message


@PROPERTY
@given(text=TEXT)
@example(text="true")
@example(text="1")
@example(text="\ud800")
def test_quoted_scalar_roundtrip(text: str) -> None:
    parsed = pm.scalar(json.dumps(text))
    assert type(parsed) is str and parsed == text


@PROPERTY
@given(number=st.integers(min_value=-10**12, max_value=10**12))
def test_integer_scalar_preserves_value_and_type(number: int) -> None:
    parsed = pm.scalar(f" {number} ")
    assert type(parsed) is int and parsed == number


@pytest.mark.parametrize(("raw", "expected"), [
    ("null", None), ("~", None), ("true", True), ("false", False), ("[]", []),
    ("-0", 0), ("0.5", 0.5), ("-12.25", -12.25), ("1٢", 12),
    ("+1", "+1"), ("01", "01"), ("1e2", "1e2"), (".5", ".5"),
    ("'", ""), ("'a", ""), ("'abc", "ab"), ("'a''b'", "a'b"),
    ("'true'", "true"), ("a: b", "a: b"),
])
def test_scalar_characterized_edges(raw: str, expected: object) -> None:
    parsed = pm.scalar(raw)
    assert type(parsed) is type(expected) and parsed == expected


@pytest.mark.parametrize("raw", ["", "{}", "[1]", "&a", "*a", "!x", "|", ">"])
def test_scalar_rejection_text(raw: str) -> None:
    rejects(lambda: pm.scalar(raw), "unsupported YAML scalar")


def test_invalid_double_quote_error_is_characterized() -> None:
    rejects(lambda: pm.scalar('"'),
            "invalid quoted scalar: Unterminated string starting at: line 1 column 1 (char 0)")


@PROPERTY
@given(values=st.dictionaries(KEYS, TEXT, max_size=16),
       body=st.lists(SAFE_TEXT, max_size=8), newline=st.sampled_from(["\n", "\r\n", "\r"]))
def test_frontmatter_preserves_generated_values_and_body(
    values: dict[str, str], body: list[str], newline: str,
) -> None:
    document = newline.join(["---", *(f"{key}: {json.dumps(value)}" for key, value in values.items()),
                             "---", "", "", *body])
    parsed, actual_body = pm.frontmatter(document)
    assert parsed == values and all(type(value) is str for value in parsed.values())
    assert actual_body == "\n".join(body)


@PROPERTY
@given(items=st.lists(TEXT, min_size=1, max_size=16))
def test_block_list_preserves_quoted_members(items: list[str]) -> None:
    document = "---\nitems:\n" + "".join(f"  - {json.dumps(item)}\n" for item in items) + "---\n"
    parsed, body = pm.frontmatter(document)
    assert parsed == {"items": items} and body == ""


def test_frontmatter_preserves_nested_empty_list() -> None:
    assert pm.frontmatter("---\nitems:\n  - []\n---\n") == ({"items": [[]]}, "")


@pytest.mark.parametrize(("document", "message"), [
    ("", "ticket frontmatter is missing"), (" ---\n---", "ticket frontmatter is missing"),
    ("---\na: x", "ticket frontmatter is unterminated"),
    ("---\na: x\na: y\n---", "duplicate or invalid YAML key"),
    ("---\nA: x\n---", "duplicate or invalid YAML key"),
    ("---\na : x\n---", "duplicate or invalid YAML key"),
    ("---\n# comment\n---", "unsupported YAML structure"),
    ("---\n a: x\n---", "unsupported YAML structure"),
    ("---\na:\n---", "empty block collection is unsupported; use []"),
    ("---\na:\n  - x\n    - y\n---", "unsupported YAML structure"),
])
def test_frontmatter_rejection_text(document: str, message: str) -> None:
    rejects(lambda: pm.frontmatter(document), message)


@pytest.mark.parametrize("newline", ["\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"])
def test_frontmatter_unicode_line_boundaries(newline: str) -> None:
    assert pm.frontmatter(newline.join(["---", "a: true", "---", "", "body", ""])) == ({"a": True}, "body")


@pytest.mark.parametrize(("source", "baseline", "string_field"), SOURCE_CASES)
@PROPERTY
@given(text=SAFE_TEXT)
def test_all_source_contracts_preserve_input(
    source: str, baseline: dict[str, object], string_field: str, text: str,
) -> None:
    payload = copy.deepcopy(baseline)
    payload[string_field] = text
    value = envelope(payload)
    before = copy.deepcopy(value)
    assert pm.safe_envelope(value) is None
    assert pm.validate_envelope_contract(source, value) is None
    assert value == before and value["payload"] is payload


@pytest.mark.parametrize(("source", "baseline", "string_field"), SOURCE_CASES)
def test_each_source_missing_extra_and_wrong_required_type(
    source: str, baseline: dict[str, object], string_field: str,
) -> None:
    for payload in ({key: item for key, item in baseline.items() if key != string_field},
                    {**baseline, "unknown": "x"}):
        rejects(lambda: pm.validate_envelope_contract(source, envelope(payload)),
                "envelope payload does not match its versioned source contract")
    rejects(lambda: pm.validate_envelope_contract(source, envelope({**baseline, string_field: 1})),
            "envelope payload has an invalid field type")


@pytest.mark.parametrize("source", [case[0] for case in SOURCE_CASES])
@pytest.mark.parametrize(("reason", "accepted"), [("", False), ("é" * 1023 + "x", True), ("é" * 1024, True), ("é" * 1024 + "x", False)])
def test_unavailable_reason_byte_bounds(source: str, reason: str, accepted: bool) -> None:
    value = envelope({"reason": reason}, "unavailable")
    pm.safe_envelope(value)
    if accepted:
        assert pm.validate_envelope_contract(source, value) is None
    else:
        rejects(lambda: pm.validate_envelope_contract(source, value),
                "unavailable envelope must contain one bounded reason")


@pytest.mark.parametrize(("source_id", "accepted"), [("", False), ("é" * 127 + "x", True), ("é" * 128, True), ("é" * 128 + "x", False)])
def test_source_id_byte_bounds(source_id: str, accepted: bool) -> None:
    value = {**envelope({}), "source_id": source_id}
    if accepted:
        assert pm.safe_envelope(value) is None
    else:
        rejects(lambda: pm.safe_envelope(value), "envelope contract is incomplete")


@PROPERTY
@given(path=st.lists(st.booleans(), max_size=2), siblings=st.lists(SAFE_TEXT, max_size=7),
       forbidden=st.sampled_from(["token", "PASSWORD", "api_key", "command_arguments", "prompt"]))
def test_forbidden_fields_reject_at_generated_depth(path: list[bool], siblings: list[str], forbidden: str) -> None:
    child: object = {forbidden: "synthetic"}
    for use_list in path:
        child = [*siblings, child] if use_list else {"child": child, "siblings": siblings}
    value = envelope({"nested": child})
    before = copy.deepcopy(value)
    rejects(lambda: pm.safe_envelope(value), "envelope contains a forbidden field")
    assert value == before


@pytest.mark.parametrize("unsafe", ["op://synthetic/vault", "-----BEGIN PRIVATE KEY-----",
                                   "Bearer synthetic", "/home/synthetic/file", "synthetic@example.invalid"])
def test_unsafe_strings_precede_top_level_shape(unsafe: str) -> None:
    rejects(lambda: pm.safe_envelope([{"nested": [unsafe]}]), "envelope contains unsafe content")
    rejects(lambda: pm.safe_envelope({"token": unsafe}), "envelope contains a forbidden field")


@pytest.mark.parametrize(("key", "value", "message"), [
    ("gates", {"unknown": {}}, "envelope gates contain an unknown gate"),
    ("gates", {"domain": {"extra": "x"}}, "envelope gate contract is invalid"),
    ("gates", {"domain": {"result": True}}, "envelope gate field type is invalid"),
    ("gates", {"domain": {"exception": {"extra": "x"}}}, "envelope gate exception is invalid"),
    ("gates", {"domain": {"exception": {"owner": 1}}}, "envelope gate exception is invalid"),
    ("metrics", {"elapsed_ms": True}, "envelope metrics contract is invalid"),
    ("metrics", {"elapsed_ms": -1}, "envelope metrics contract is invalid"),
    ("metrics", {"unknown": 1}, "envelope metrics contract is invalid"),
    ("rubric", {"name": "x", "version": "1"}, "envelope rubric contract is invalid"),
    ("harness_identity", {}, "envelope harness identity is invalid"),
    ("members", [{"position": True}], "envelope members contract is invalid"),
    ("members", [{"extra": "x"}], "envelope members contract is invalid"),
    ("nodes", [{"id": "a", "depends_on": [1], "operation": "x", "result": "pass"}], "envelope DAG node contract is invalid"),
    ("phase_profile", {"phase_count": True}, "envelope phase profile is invalid"),
    ("phase_profile", {"critical_path": [1]}, "envelope phase profile is invalid"),
    ("findings", [""], "envelope prose list is invalid"),
    ("summary", "", "envelope scalar is invalid"),
])
def test_nested_field_rejection_text(key: str, value: object, message: str) -> None:
    rejects(lambda: pm.validate_envelope_field(key, value), message)


@PROPERTY
@given(number=st.one_of(st.integers(min_value=0, max_value=10**12),
                        st.floats(min_value=0, allow_nan=False, allow_infinity=False)), text=SAFE_TEXT)
def test_nested_valid_fields(number: int | float, text: str) -> None:
    fields: dict[str, object] = {
        "gates": {"domain": {"applicability": text, "result": text, "reason": text,
                              "evidence": text, "owner": text,
                              "exception": {"disposition": text, "rationale": text, "owner": text,
                                            "approved_at": text, "expires_at": text}}},
        "metrics": {"elapsed_ms": number}, "rubric": {"name": text, "version": text, "digest": text},
        "harness_identity": dict.fromkeys(["provider_id", "model_id", "agent_id", "role", "core_revision", "overlay_revision"], text),
        "members": [{"id": text, "position": 1}],
        "nodes": [{"id": text, "depends_on": [text], "operation": text, "result": text}],
        "phase_profile": {"critical_path": [text], "phase_count": 1, "elapsed_ms": text}, "findings": [text],
    }
    before = copy.deepcopy(fields)
    for key, value in fields.items():
        assert pm.validate_envelope_field(key, value) is None
    assert fields == before


@pytest.mark.parametrize("key", ["members", "nodes", "findings"])
@pytest.mark.parametrize("count", [499, 500, 501])
def test_collection_limits(key: str, count: int) -> None:
    item: object = {} if key == "members" else {"id": "a", "depends_on": [], "operation": "x", "result": "pass"} if key == "nodes" else "x"
    if count <= 500:
        assert pm.validate_envelope_field(key, [item] * count) is None
    else:
        message = {"members": "envelope members contract is invalid", "nodes": "envelope DAG node contract is invalid",
                   "findings": "envelope prose list is invalid"}[key]
        rejects(lambda: pm.validate_envelope_field(key, [item] * count), message)


@pytest.mark.parametrize("key", ["summary", "findings"])
@pytest.mark.parametrize("text", ["é" * 1023 + "x", "é" * 1024, "é" * 1024 + "x"])
def test_scalar_and_prose_byte_limits(key: str, text: str) -> None:
    value: object = [text] if key == "findings" else text
    if len(text.encode()) <= 2048:
        assert pm.validate_envelope_field(key, value) is None
    else:
        rejects(lambda: pm.validate_envelope_field(key, value),
                "envelope prose list is invalid" if key == "findings" else "envelope scalar is invalid")


def test_incidental_errors_and_numeric_distinctions_stay_visible() -> None:
    rejects(lambda: pm.safe_envelope({**envelope({}), "schema_version": True}), "envelope contract is incomplete")
    with pytest.raises(TypeError, match="unhashable type: 'list'"):
        pm.safe_envelope({**envelope({}), "availability": []})
    with pytest.raises(UnicodeEncodeError):
        pm.safe_envelope({**envelope({}), "source_id": "\ud800"})
    for number in (float("nan"), float("inf"), -0.0):
        assert pm.validate_envelope_field("metrics", {"elapsed_ms": number}) is None
    assert pm.validate_envelope_field("metrics", {"token_total": 1}) is None
    rejects(lambda: pm.safe_envelope(envelope({"metrics": {"token_total": 1}})), "envelope contains a forbidden field")


def test_top_level_versions_optional_fields_and_unavailable_shape() -> None:
    value = envelope(copy.deepcopy(SOURCE_CASES[0][1]))
    rejects(lambda: pm.safe_envelope({**value, "extra": 1}), "envelope contract is incomplete")
    rejects(lambda: pm.safe_envelope({**value, "source_authority": "other"}), "envelope contract is incomplete")
    rejects(lambda: pm.validate_envelope_contract("cycle_record", {**value, "schema_version": 2}),
            "unsupported sanitized envelope schema version")
    payload = copy.deepcopy(SOURCE_CASES[0][1])
    assert pm.validate_envelope_contract("cycle_record", envelope({**payload, "metrics": {}})) is None
    rejects(lambda: pm.validate_envelope_contract("cycle_record", envelope({**payload, "created_at": True})),
            "envelope payload has an invalid optional field type")
    rejects(lambda: pm.validate_envelope_contract("cycle_record", envelope({**payload, "created_at": ""})),
            "envelope scalar is invalid")
    unavailable_payloads: list[dict[str, object]] = [{}, {"reason": True}, {"reason": "x", "extra": "x"}]
    for unavailable in unavailable_payloads:
        rejects(lambda: pm.validate_envelope_contract("cycle_record", envelope(unavailable, "unavailable")),
                "unavailable envelope must contain one bounded reason")


def test_safety_preserves_non_json_values_without_claiming_source_validity() -> None:
    payload: dict[str, object] = {"nested": (b"synthetic",), "bytes": b"synthetic"}
    value = envelope(payload)
    assert pm.safe_envelope(value) is None and value["payload"] is payload
    rejects(lambda: pm.validate_envelope_contract("cycle_record", value),
            "envelope payload does not match its versioned source contract")


def test_legacy_source_validator_does_not_add_safety_or_source_selection() -> None:
    payload = copy.deepcopy(SOURCE_CASES[0][1])
    payload["metrics"] = {"token_total": 1}
    # The direct legacy helper checks the selected payload, not the safety envelope.
    value = {"schema_version": True, "availability": "available", "payload": payload}
    assert pm.validate_envelope_contract("cycle_record", value) is None
    unavailable = envelope({"reason": "No eligible source"}, "unavailable")
    assert pm.validate_envelope_contract("unknown", unavailable) is None
    with pytest.raises(KeyError, match="unknown"):
        pm.validate_envelope_contract("unknown", envelope(payload))


def test_boundary_parser_and_legacy_adapter_agree_with_expected_values() -> None:
    parsed = pm.parse_frontmatter("---\na: true\nitems:\n  - '1'\nempty: []\nnested:\n  - []\n---\n\nbody\n")
    assert type(parsed) is pm.ParsedFrontmatter
    assert parsed.values == {"a": True, "items": ["1"], "empty": [], "nested": [[]]}
    assert parsed.body == "body"
    assert type(pm.frontmatter("---\n---")) is tuple


@pytest.mark.parametrize(("source", "baseline", "string_field"), SOURCE_CASES)
def test_boundary_approval_retains_original_objects(source: str, baseline: dict[str, object], string_field: str) -> None:
    payload = copy.deepcopy(baseline)
    value = envelope(payload)
    before = copy.deepcopy(value)
    safety = pm.approve_envelope_safety(value)
    approved = pm.approve_envelope(source, value)
    assert safety.value is value and approved.value is value and approved.source == source
    assert type(safety) is pm.SafetyApprovedEnvelope and type(approved) is pm.SourceApprovedEnvelope
    assert type(safety.schema_version) is int and safety.schema_version == 1
    assert safety.source_id == "source-1" and safety.payload is payload
    assert type(approved.envelope) is pm.SafetyApprovedEnvelope
    assert approved.envelope.value is value and approved.envelope.payload is payload
    assert approved.envelope.schema_version == 1 and approved.envelope.source_id == "source-1"
    assert value["payload"] is payload and value == before
    unavailable = envelope({"reason": "No eligible source"}, "unavailable")
    assert pm.approve_envelope(source, unavailable).value is unavailable
    rejects(lambda: pm.approve_envelope(source, envelope({**baseline, string_field: True})),
            "envelope payload has an invalid field type")


def test_boundary_exact_type_checks_see_original_subclasses() -> None:
    class DictChild(dict[str, object]):
        pass
    payload = copy.deepcopy(SOURCE_CASES[0][1])
    original_gates = DictChild()
    payload["gates"] = original_gates
    value = envelope(payload)
    assert pm.approve_envelope_safety(value).value is value and payload["gates"] is original_gates
    rejects(lambda: pm.approve_envelope("cycle_record", value), "envelope payload has an invalid field type")


def test_boundary_proof_captures_checked_subclass_fields() -> None:
    class ChangingFields(dict[str, object]):
        def __init__(self) -> None:
            super().__init__(envelope({}))
            self.reads: dict[str, int] = {}

        def __getitem__(self, key: str) -> object:
            self.reads[key] = self.reads.get(key, 0) + 1
            if key == "schema_version" and self.reads[key] > 1:
                return "unchecked"
            if key == "source_id" and self.reads[key] > 2:
                return 0
            if key == "payload" and self.reads[key] > 1:
                return "unchecked"
            return super().__getitem__(key)

    value = ChangingFields()
    approved = pm.approve_envelope_safety(value)
    assert approved.value is value
    assert type(approved.schema_version) is int and approved.schema_version == 1
    assert type(approved.source_id) is str and approved.source_id == "source-1"
    assert approved.payload is dict.__getitem__(value, "payload")
    assert value.reads == {"schema_version": 1, "source_authority": 1,
                           "availability": 1, "source_id": 2, "payload": 1}
    assert pm.safe_envelope(ChangingFields()) is None


def test_boundary_safety_rejects_before_contract_and_does_not_mutate() -> None:
    value = envelope({"token": "synthetic"})
    before = copy.deepcopy(value)
    rejects(lambda: pm.approve_envelope_safety(value), "envelope contains a forbidden field")
    rejects(lambda: pm.approve_envelope("cycle_record", value), "envelope contains a forbidden field")
    assert value == before
    rejects(lambda: pm.approve_envelope_safety({}), "envelope contract is incomplete")
    rejects(lambda: pm.approve_envelope("unknown", value), "unsupported sanitized envelope source")


def test_boundary_pure_calls_perform_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("pure policy attempted I/O")
    for name in ("open",):
        monkeypatch.setattr(builtins, name, forbidden)
    for name in ("open", "read_bytes", "read_text", "write_bytes", "write_text"):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(pm.subprocess, "run", forbidden)
    monkeypatch.setattr(pm.os, "open", forbidden)
    pm.scalar("true")
    pm.parse_frontmatter("---\na: true\n---")
    value = envelope({"reason": "No source"}, "unavailable")
    pm.approve_envelope_safety(value)
    pm.approve_envelope("cycle_record", value)


def project(tmp_path: Path, raw: bytes, source: str = "cycle_record") -> tuple[subprocess.CompletedProcess[str], Path]:
    input_path, capture, adapter = tmp_path / "envelope.json", tmp_path / "captured.sql", tmp_path / "psql"
    input_path.write_bytes(raw)
    adapter.write_text('#!/bin/sh\ncat > "$0.sql"\n')
    adapter.chmod(0o755)
    capture = adapter.with_suffix(".sql")
    completed = subprocess.run(["python3", str(PMCTL), "project", "--source", source,
                                "--input", str(input_path), "--psql", str(adapter), "--json"],
                               text=True, capture_output=True, timeout=30)
    return completed, capture


def test_projection_preserves_raw_digest_and_canonical_payload(tmp_path: Path) -> None:
    value = envelope({"reason": "Synthetic reason"}, "unavailable")
    raw_values = [json.dumps(value).encode(), json.dumps(value, indent=2).encode()]
    digests = []
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    for raw in raw_values:
        completed, capture = project(tmp_path, raw)
        assert completed.returncode == 0 and completed.stderr == ""
        result = json.loads(completed.stdout)
        assert completed.stdout == json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        assert result["digest"] == hashlib.sha256(raw).hexdigest()
        assert canonical in capture.read_text() and "ON CONFLICT DO NOTHING" in capture.read_text()
        digests.append(result["digest"])
    assert digests[0] != digests[1]


@pytest.mark.parametrize(("raw", "source", "message"), [
    (b"x" * (1024 * 1024 + 1), "unknown", "envelope exceeds 1 MiB"),
    (b"{}", "unknown", "unsupported sanitized envelope source"),
    (b'{"token":"x"}', "cycle_record", "envelope contains a forbidden field"),
    (b"{}", "cycle_record", "envelope contract is incomplete"),
    (json.dumps(envelope({})).encode(), "cycle_record", "envelope payload does not match its versioned source contract"),
], ids=["oversized", "unknown-source", "forbidden-field", "incomplete-envelope", "invalid-source-payload"])
def test_projection_rejection_precedes_adapter(tmp_path: Path, raw: bytes, source: str, message: str) -> None:
    completed, capture = project(tmp_path, raw, source)
    assert completed.returncode == 1 and completed.stdout == "" and completed.stderr == f"pmctl: {message}\n"
    assert not capture.exists()


def test_projection_json_decode_precedes_source_check(tmp_path: Path) -> None:
    completed, capture = project(tmp_path, b"{", "unknown")
    assert completed.returncode == 1 and completed.stdout == ""
    assert completed.stderr == 'pmctl: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)\n'
    assert not capture.exists()
