"""Opt-in native skill-routing qualification; ordinary pytest never calls a model.

Raw prompts/events and identities belong in private cycle evidence. Observed
returned content is read evidence, not OS file-access or semantic attestation.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tarfile
import time
from collections import Counter
from pathlib import Path, PurePosixPath


SPLITS = {"development": 1, "heldout": 2, "navigation": 2, "omission": 1}
USAGE = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
BINDINGS = ("fixture_digest", "suite_digest", "oracle_digest", "runtime_identity_digest",
            "ambient_catalog_digest", "client_version", "model", "provider")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class _NativeObject(list):
    """Keep native object pairs until their exact event context is known."""


def decode_native_events(text):
    """Decode native JSONL, preserving one known unscored web-search quirk.

    Codex 0.164 can serialize both its item ID and web execution ID as `id`.
    Neither is selected as authority. Every other duplicate remains invalid.
    """
    if not isinstance(text, str):
        raise ValueError("native JSONL must be text")

    def convert(value, path, event_type, warnings):
        if isinstance(value, _NativeObject):
            counts = Counter(key for key, _ in value)
            duplicate = {key for key, count in counts.items() if count > 1}
            if not path and "decoder_warnings" in counts:
                raise ValueError("native event conflicts with decoder metadata")
            if duplicate:
                fields = {key: item for key, item in value if key != "id"}
                ids = [item for key, item in value if key == "id"]
                expected = {"id", "type", "query", "action"}
                if event_type == "item.completed":
                    expected.add("results")
                known = (path == ("item",) and event_type in {"item.started", "item.completed"}
                         and duplicate == {"id"} and counts["id"] == 2
                         and set(counts) == expected and fields.get("type") == "web_search"
                         and all(isinstance(item, str) for item in ids)
                         and re.fullmatch(r"item_[0-9]+", ids[0])
                         and re.fullmatch(r"exec-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", ids[1]))
                if not known:
                    raise ValueError("duplicate native JSON key outside known web-search serialization")
                result = {key: convert(item, path + (key,), event_type, warnings)
                          for key, item in value if key != "id"}
                if not isinstance(result["query"], str) or not isinstance(result["action"], dict):
                    raise ValueError("unsupported native web-search shape")
                if event_type == "item.completed" and not isinstance(result["results"], list):
                    raise ValueError("unsupported native web-search results")
                result["opaque_ids"] = ids
                warnings.append({"code": "native_web_search_duplicate_id", "opaque_ids": ids})
                return result
            return {key: convert(item, path + (key,), event_type, warnings) for key, item in value}
        if isinstance(value, list):
            return [convert(item, path + (index,), event_type, warnings) for index, item in enumerate(value)]
        return value

    events = []
    for line in text.splitlines():
        if not line.strip():
            continue
        raw = json.loads(line, object_pairs_hook=_NativeObject)
        if not isinstance(raw, _NativeObject):
            raise ValueError("native event must be an object")
        types = [value for key, value in raw if key == "type"]
        if len(types) != 1 or not isinstance(types[0], str):
            raise ValueError("native event requires one type")
        warnings = []
        event = convert(raw, (), types[0], warnings)
        if warnings:
            event["decoder_warnings"] = warnings
        events.append(event)
    return events


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=_pairs)


def relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("invalid portable path")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(p in {"", ".", ".."} for p in path.parts):
        raise ValueError("unsafe portable path")
    return path


def _names(value):
    if not isinstance(value, list) or any(not isinstance(n, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,127}", n) for n in value):
        raise ValueError("invalid skill names")
    if len(value) != len(set(value)):
        raise ValueError("duplicate skill name")
    return set(value)


def load_cases(path):
    value = read_json(path)
    if set(value) != {"schema_version", "suite_id", "tracked_skills", "cases"} or type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("unsupported case manifest")
    tracked = _names(value["tracked_skills"])
    if not tracked or not isinstance(value["suite_id"], str) or not value["suite_id"]:
        raise ValueError("invalid suite identity")
    if not isinstance(value["cases"], list):
        raise ValueError("invalid case population")
    ids = set()
    for case in value["cases"]:
        if not isinstance(case, dict) or not {"id", "split", "input"} <= case.keys() or set(case) - {"id", "split", "input", "registration"}:
            raise ValueError("invalid case")
        if not isinstance(case["id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,127}", case["id"]) or case["id"] in ids:
            raise ValueError("invalid or duplicate case identity")
        ids.add(case["id"])
        if case["split"] not in SPLITS:
            raise ValueError("unknown split")
        packet = case["input"]
        if not isinstance(packet, dict) or set(packet) != {"request", "files", "execution_scope"}:
            raise ValueError("input contains non-task fields")
        for key in ("request", "execution_scope"):
            if not isinstance(packet[key], str) or not 1 <= len(packet[key].encode()) <= 16384:
                raise ValueError("invalid task text")
        if not isinstance(packet["files"], dict) or len(packet["files"]) > 64:
            raise ValueError("invalid task files")
        for name, text in packet["files"].items():
            relative_path(name)
            if not isinstance(text, str) or len(text.encode()) > 131072:
                raise ValueError("invalid task file")
        if any(name in json.dumps(packet) for name in tracked):
            raise ValueError("implicit packet includes a tracked skill name")
        registration = case.get("registration", {"omit": []})
        if not isinstance(registration, dict) or set(registration) != {"omit"} or not _names(registration["omit"]) <= tracked:
            raise ValueError("invalid native registration")
        if registration["omit"] and case["split"] != "omission":
            raise ValueError("omission outside its declared control")
    if Counter(c["split"] for c in value["cases"]) != {"development": 4, "heldout": 8, "navigation": 1, "omission": 1}:
        raise ValueError("case population differs from the fixed protocol")
    return value


def load_oracle(path, cases):
    value = read_json(path)
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1 or value.get("suite_id") != cases["suite_id"]:
        raise ValueError("oracle identity mismatch")
    if not isinstance(value.get("cases"), dict) or set(value["cases"]) != {c["id"] for c in cases["cases"]}:
        raise ValueError("oracle case population mismatch")
    tracked = set(cases["tracked_skills"])
    for row in value["cases"].values():
        groups = [_names(row[k]) for k in ("required_tracked_skills", "allowed_additional_tracked_skills", "forbidden_tracked_skills")]
        if any(not group <= tracked for group in groups) or any(groups[i] & groups[j] for i in range(3) for j in range(i)):
            raise ValueError("invalid oracle skill partition")
        if not isinstance(row.get("decision_checks"), list) or any(not isinstance(x, str) or not x for x in row["decision_checks"]):
            raise ValueError("invalid decision rubric")
    return value


def build_plan(cases):
    plan = []
    def add(case, arm, repetition):
        plan.append({"case_id": case["id"], "split": case["split"], "arm": arm,
                     "repetition": repetition, "order": len(plan) + 1})
    development = [c for c in cases["cases"] if c["split"] == "development"]
    for arm in ("baseline", "candidate"):
        for case in development:
            add(case, arm, 1)
    for split in ("heldout", "navigation", "omission"):
        for index, case in enumerate(c for c in cases["cases"] if c["split"] == split):
            for repetition in range(1, SPLITS[split] + 1):
                arms = ("baseline", "candidate") if (index + repetition) % 2 else ("candidate", "baseline")
                for arm in arms:
                    add(case, arm, repetition)
    if len(plan) != 46:
        raise ValueError("native call budget mismatch")
    return plan


def parse_catalog(prompt_input):
    if not isinstance(prompt_input, list):
        raise ValueError("native prompt input must be a list")
    blocks = []
    for item in prompt_input:
        if isinstance(item, dict) and item.get("role") == "developer":
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "input_text":
                    text = part.get("text", "")
                    if isinstance(text, str) and text.startswith("<skills_instructions>\n") and text.endswith("</skills_instructions>"):
                        blocks.append(text)
    if len(blocks) != 1:
        raise ValueError("unsupported native skills block")
    text = blocks[0]
    if text.count("### Skill roots\n") != 1 or text.count("### Available skills\n") != 1:
        raise ValueError("unsupported native catalog sections")
    roots_text, entries = text.split("### Skill roots\n", 1)[1].split("### Available skills\n", 1)
    roots = {}
    for line in roots_text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"- `(r[0-9]+)` = `([^`]+)`", line)
        if not match or match[1] in roots or not Path(match[2]).is_absolute():
            raise ValueError("invalid or duplicate native alias")
        roots[match[1]] = match[2]
    skills = []
    for line in entries.removesuffix("</skills_instructions>").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"- (.+?): (.*) \(file: (r[0-9]+)/(.+)\)", line)
        if not match or match[3] not in roots:
            raise ValueError("unsupported native skill entry")
        child = relative_path(match[4])
        skills.append({"name": match[1], "description": match[2], "path": match[3] + "/" + str(child),
                       "resolved_path": str((Path(roots[match[3]]) / child).resolve())})
    return {"roots": roots, "skills": skills}


def validate_catalog(catalog, skills_root, tracked_names, *, omitted=()):
    root = Path(skills_root).resolve()
    expected = set(tracked_names) | {"dbsctr"}
    omitted = set(omitted)
    if not omitted <= expected:
        raise ValueError("unknown omitted skill")
    found = {}
    for row in catalog["skills"]:
        if row["name"] not in expected:
            continue
        name = row["name"]
        if name in found or name in omitted:
            raise ValueError("duplicate or intentionally unregistered tracked revision")
        path = root / name / "SKILL.md"
        if not path.is_file() or Path(row["resolved_path"]) != path.resolve():
            raise ValueError("tracked catalog revision differs from snapshot")
        found[name] = row
    if set(found) != expected - omitted:
        raise ValueError("tracked native catalog is incomplete")
    return {**catalog, "tracked": found, "digest": digest(encoded(catalog))}


def _final(value):
    if not isinstance(value, dict) or set(value) != {"assessment", "proposed_changes", "validation", "limitations"}:
        raise ValueError("invalid native final output")
    if not isinstance(value["assessment"], str):
        raise ValueError("invalid assessment")
    for key in ("proposed_changes", "validation", "limitations"):
        if not isinstance(value[key], list) or any(not isinstance(x, str) for x in value[key]):
            raise ValueError("invalid final output list")
    return value


def _read_candidates(root):
    for path in sorted(Path(root).rglob("*.md")):
        relative = path.relative_to(root)
        if len(relative.parts) < 2 or path.name in {"UPSTREAM.md", "LICENSE.upstream"} or "specialist-sources" in relative.parts or "python-specialists" in relative.parts:
            continue
        text = path.read_text()
        body = text.split("---", 2)[2] if text.startswith("---\n") and len(text.split("---", 2)) == 3 else text
        lines = [line.strip() for line in body.splitlines() if len(line.strip()) >= 32 and not line.lstrip().startswith("#")]
        yield path, relative, text, lines


def parse_events(events, skills_root, *, returncode=0):
    if not isinstance(events, list) or any(not isinstance(e, dict) or not isinstance(e.get("type"), str) for e in events):
        raise ValueError("invalid native event sequence")
    terminals = [e for e in events if e["type"] == "turn.completed"]
    if len(terminals) > 1:
        raise ValueError("multiple completed turns in one fresh assessment")
    usage = {key: None for key in USAGE}
    if terminals:
        raw_usage = terminals[0].get("usage")
        if raw_usage is not None and not isinstance(raw_usage, dict):
            raise ValueError("invalid native usage object")
        for key in USAGE:
            value = (raw_usage or {}).get(key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("invalid native usage integer")
            usage[key] = value
    reads, commands, answers, errors = [], set(), [], []
    serialization_warnings, item_diagnostics = [], []
    candidates = list(_read_candidates(Path(skills_root)))
    # Shared project boundaries are not evidence for each method mentioned in a
    # batch command. Count a distinct adjacent pair once per candidate file.
    pair_files = Counter(pair for _, _, _, lines in candidates
                         for pair in set(zip(lines, lines[1:])) if pair[0] != pair[1])
    for event in events:
        warnings = event.get("decoder_warnings", [])
        if not isinstance(warnings, list) or any(not isinstance(row, dict) for row in warnings):
            raise ValueError("invalid native decoder diagnostics")
        serialization_warnings.extend(warnings)
        if event["type"] in {"error", "turn.failed"}:
            errors.append(event["type"])
        if event["type"] not in {"item.started", "item.completed"}:
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            raise ValueError("invalid native item")
        if item.get("type") in {"error", "warning"} and event["type"] == "item.completed":
            if not isinstance(item.get("message"), str):
                raise ValueError("invalid native item diagnostic")
            item_diagnostics.append({"item_type": item["type"], "item_id": item.get("id"),
                                     "message": item["message"]})
        if item.get("type") == "agent_message" and event["type"] == "item.completed":
            if not isinstance(item.get("text"), str):
                raise ValueError("invalid native answer")
            answers.append(item["text"])
        if item.get("type") != "command_execution":
            continue
        if not isinstance(item.get("id"), str) or not isinstance(item.get("command"), str):
            raise ValueError("invalid native command item")
        commands.add(item["id"])
        code = item.get("exit_code")
        if code is not None and type(code) is not int:
            raise ValueError("invalid command exit status")
        if event["type"] != "item.completed" or code != 0 or item.get("status") != "completed":
            continue
        output = item.get("aggregated_output")
        if not isinstance(output, str):
            raise ValueError("missing completed command output")
        normalized = re.sub(r"(?m)^\s*[0-9]+[:|\t]\s?", "", output)
        for path, relative, text, lines in candidates:
            full = text.strip() in normalized and bool(text.strip())
            intent = (relative.parts[0] in item["command"] and path.name in item["command"])
            excerpt = intent and any(pair_files[(a, b)] == 1 and a in normalized and b in normalized
                                     for a, b in zip(lines, lines[1:]) if a != b)
            if full or excerpt:
                reads.append({"skill": relative.parts[0], "path": relative.as_posix(),
                              "extent": "full" if full else "excerpt", "item_id": item["id"],
                              "source_sha256": digest(path.read_bytes())})
    failed = returncode != 0 or any(e["type"] == "turn.failed" for e in events)
    output = None
    if answers and terminals and not failed:
        output = _final(json.loads(answers[-1], object_pairs_hook=_pairs))
    elif terminals and not failed:
        raise ValueError("completed native turn has no final assessment")
    status = "failed" if failed else "complete" if terminals and output is not None and all(usage[k] is not None for k in USAGE[:3]) else "unavailable"
    return {"status": status, "usage": usage, "reads": reads, "final_output": output,
            "command_count": len(commands), "errors": errors,
            "serialization_warnings": serialization_warnings, "item_diagnostics": item_diagnostics,
            "measurement_limit": "Returned content is not OS file-access attestation or proof of instruction compliance. Excerpts require a line pair unique among snapshot method files; shared boundaries alone do not qualify. Native totals do not attribute individual skills or qualify nested model usage."}


def score_observation(observation, oracle_case):
    required = set(oracle_case["required_tracked_skills"])
    allowed = set(oracle_case["allowed_additional_tracked_skills"])
    forbidden = set(oracle_case["forbidden_tracked_skills"])
    loaded = {r["skill"] for r in observation["reads"]} - {"dbsctr"}
    missing, unexpected = required - loaded, (loaded - required - allowed) | (loaded & forbidden)
    return {"loaded": sorted(loaded), "missing_required": sorted(missing),
            "unexpected_loaded": sorted(unexpected),
            "routing_passed": not missing and not unexpected if observation["status"] == "complete" else None,
            "quality_status": "manual_review_required"}


def run_bounded(argv, *, cwd, stdin="", timeout=180, max_bytes=2097152, stdout_path=None, stderr_path=None):
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) for a in argv) or timeout <= 0 or type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("invalid bounded command")
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    assert process.stdin and process.stdout and process.stderr
    process.stdin.write(stdin.encode())
    process.stdin.close()
    reader = selectors.DefaultSelector()
    for stream in (process.stdout, process.stderr):
        os.set_blocking(stream.fileno(), False)
        reader.register(stream, selectors.EVENT_READ)
    captured = {process.stdout: bytearray(), process.stderr: bytearray()}
    timed_out = output_limit = False
    termination_error = None
    try:
        while reader.get_map():
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                timed_out = True
                break
            for key, _ in reader.select(min(remaining, 0.1)):
                data = os.read(key.fd, 65536)
                if not data:
                    reader.unregister(key.fileobj)
                    continue
                capacity = max_bytes - sum(len(v) for v in captured.values())
                captured[key.fileobj].extend(data[:capacity])
                if len(data) > capacity:
                    output_limit = True
                    break
            if output_limit:
                break
        # The owned group can still hold pipes after its leader has exited.
        # A reaped parent must not suppress termination of those descendants.
        if timed_out or output_limit:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                termination_error = "permission_denied"
                if process.poll() is None:
                    raise
        remaining = max(0.01, timeout - (time.monotonic() - started))
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    finally:
        reader.close()
        process.stdout.close()
        process.stderr.close()
    raw_stdout, raw_stderr = bytes(captured[process.stdout]), bytes(captured[process.stderr])
    for path, data in ((stdout_path, raw_stdout), (stderr_path, raw_stderr)):
        if path is not None:
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stream:
                stream.write(data)
    encoding_error = False
    try:
        raw_stdout.decode("utf-8")
        raw_stderr.decode("utf-8")
    except UnicodeDecodeError:
        encoding_error = True
    return {"returncode": process.returncode, "timed_out": timed_out, "output_limit": output_limit,
            "stdout": raw_stdout.decode(errors="replace"), "stderr": raw_stderr.decode(errors="replace"),
            "stdout_sha256": digest(raw_stdout), "stderr_sha256": digest(raw_stderr),
            "encoding_error": encoding_error, "termination_error": termination_error,
            "elapsed_ms": round((time.monotonic() - started) * 1000)}


def _private_json(path, value):
    path = Path(path)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def _inventory(root):
    files, modes = {}, {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink inside source snapshot")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            files[relative] = digest(path.read_bytes())
            modes[relative] = "100755" if path.stat().st_mode & 0o111 else "100644"
    return {"files": files, "modes": modes}


def prepare_snapshot(source, destination, tracked_names, *, git_ref=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.is_relative_to(source):
        raise ValueError("private snapshot must be outside its source")
    names = sorted(set(tracked_names) | {"dbsctr"})
    _names(names)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    skills = destination / "skills"
    skills.mkdir(mode=0o700)
    origin = {"kind": "tree"}
    if git_ref is not None:
        commit = subprocess.check_output(["git", "rev-parse", "--verify", git_ref + "^{commit}"], cwd=source, text=True).strip()
        archive = subprocess.check_output(["git", "archive", commit, *["dot_agents/skills/" + n for n in names]], cwd=source)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar.getmembers():
                if member.isdir() and member.name.rstrip("/") in {"dot_agents", "dot_agents/skills"}:
                    continue
                path = PurePosixPath(member.name)
                if not member.name.startswith("dot_agents/skills/") or any(p == ".." for p in path.parts):
                    raise ValueError("unsafe guidance archive member")
                child = PurePosixPath(*path.parts[2:])
                target = skills / child
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    data = tar.extractfile(member)
                    assert data is not None
                    target.write_bytes(data.read())
                    target.chmod(0o755 if member.mode & 0o111 else 0o644)
                else:
                    raise ValueError("unsupported guidance archive entry")
        origin = {"kind": "git", "commit": commit}
    else:
        for name in names:
            path = source / "dot_agents/skills" / name
            _inventory(path)
            shutil.copytree(path, skills / name)
    for name in names:
        if not (skills / name / "SKILL.md").is_file():
            raise ValueError("snapshot is missing an entrypoint")
    inventory = _inventory(skills)
    manifest = {"schema_version": 1, "tracked_skills": sorted(set(tracked_names)),
                "origin": origin, **inventory, "source_digest": digest(encoded(inventory))}
    _private_json(destination / "snapshot.json", manifest)
    return manifest


def verify_snapshot(snapshot):
    snapshot = Path(snapshot)
    manifest = read_json(snapshot / "snapshot.json")
    inventory = _inventory(snapshot / "skills")
    if inventory != {k: manifest[k] for k in ("files", "modes")} or digest(encoded(inventory)) != manifest["source_digest"]:
        raise ValueError("guidance snapshot changed")
    return manifest


def aggregate(plan, observations):
    slots = {(p["case_id"], p["arm"], p["repetition"], p["order"]): p for p in plan}
    if len(slots) != len(plan) or len(plan) > 46:
        raise ValueError("invalid planned denominator")
    seen, arm_sources, shared = {}, {}, {}
    for row in observations:
        key = (row["case_id"], row["arm"], row["repetition"], row["order"])
        if key not in slots or key in seen or row.get("split") != slots[key]["split"]:
            raise ValueError("unknown or duplicate observation")
        for field in BINDINGS:
            if field not in row or row[field] is None:
                raise ValueError("missing observation identity")
        pair = (row["case_id"], row["repetition"])
        identity = tuple(row[k] for k in BINDINGS)
        if pair in shared and shared[pair] != identity:
            raise ValueError("paired observation identity changed")
        shared[pair] = identity
        if row["arm"] in arm_sources and arm_sources[row["arm"]] != row["source_digest"]:
            raise ValueError("arm snapshot changed")
        arm_sources[row["arm"]] = row["source_digest"]
        seen[key] = row
    totals = {}
    for arm in ("baseline", "candidate"):
        rows = [r for r in observations if r["arm"] == arm]
        totals[arm] = {key: {"available": sum(r["usage"].get(key) is not None for r in rows),
                             "sum": sum(r["usage"][key] for r in rows if r["usage"].get(key) is not None) if any(r["usage"].get(key) is not None for r in rows) else None}
                       for key in USAGE}
    counts = Counter(row["status"] for row in observations)
    return {"planned": len(plan), "observed": len(observations), "complete": counts["complete"],
            "failed": counts["failed"], "unavailable": counts["unavailable"],
            "missing": len(slots) - len(seen),
            "missing_slots": [p for key, p in slots.items() if key not in seen], "usage_by_arm": totals,
            "paired": [{"case_id": case, "repetition": repetition,
                        **{arm: next((r for r in observations if r["case_id"] == case and r["repetition"] == repetition and r["arm"] == arm), None) for arm in ("baseline", "candidate")}}
                       for case, repetition in dict.fromkeys((p["case_id"], p["repetition"]) for p in plan)],
            "quality_status": "manual_review_required"}


def _identity(path):
    value = read_json(path)
    for key in ("client_version", "model", "provider", "provenance"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise ValueError("missing observed native identity")
    if not isinstance(value.get("files"), dict) or not value["files"]:
        raise ValueError("native identity must bind observed files")
    for name, expected in value["files"].items():
        if not Path(name).is_absolute() or digest(Path(name).read_bytes()) != expected:
            raise ValueError("native configuration or executable identity changed")
    return value


def run_one(args):
    if not args.allow_native:
        raise ValueError("native execution requires explicit --allow-native")
    output = Path(args.output).resolve()
    source_checkout = Path(__file__).resolve().parents[1]
    if output.is_relative_to(source_checkout):
        git_owner = source_checkout / ".git"
        real_git_owner = (git_owner.is_dir() and not git_owner.is_symlink()
                          and git_owner.stat().st_uid == os.getuid()
                          and (git_owner / "HEAD").is_file() and (git_owner / "objects").is_dir())
        if not real_git_owner or not output.is_relative_to(git_owner.resolve()):
            raise ValueError("native output must use private evidence outside public source")
    evaluator_sha256 = digest(Path(__file__).read_bytes())
    cases = load_cases(args.cases)
    oracle = load_oracle(args.oracle, cases)
    slot = next((p for p in build_plan(cases) if all(p[k] == getattr(args, k) for k in ("case_id", "arm", "repetition", "order"))), None)
    if slot is None:
        raise ValueError("run is outside the fixed native plan")
    case = next(c for c in cases["cases"] if c["id"] == args.case_id)
    snapshot = Path(args.snapshot).resolve()
    manifest = verify_snapshot(snapshot)
    if set(manifest["tracked_skills"]) != set(cases["tracked_skills"]):
        raise ValueError("snapshot and fixture tracked skills differ")
    identity = _identity(args.identity)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    fixture = output / "fixture"
    fixture.mkdir(mode=0o700)
    for name, text in case["input"]["files"].items():
        target = fixture / relative_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    registration = fixture / ".agents/skills"
    registration.mkdir(parents=True, exist_ok=True)
    omitted = case.get("registration", {}).get("omit", [])
    for name in sorted(set(cases["tracked_skills"]) | {"dbsctr"}):
        if name not in omitted:
            (registration / name).symlink_to(snapshot / "skills" / name, target_is_directory=True)
    exclusions = [{"path": str((Path(args.installed_skills) / name / "SKILL.md").absolute()), "enabled": False}
                  for name in sorted(set(cases["tracked_skills"]) | {"dbsctr"})]
    # JSON strings are TOML-compatible strings inside this invocation-only array.
    override = "skills.config=[" + ",".join('{path=' + json.dumps(x["path"]) + ',enabled=false}' for x in exclusions) + "]"
    common = [args.codex, "-C", str(fixture), "-a", "never", "-c", override]
    observation = {**slot, "evaluator_sha256": evaluator_sha256, "source_digest": manifest["source_digest"],
                   "fixture_digest": digest(encoded(case["input"])), "suite_digest": digest(Path(args.cases).read_bytes()),
                   "oracle_digest": digest(Path(args.oracle).read_bytes()), "runtime_identity_digest": digest(encoded(identity)),
                   **{k: identity[k] for k in ("client_version", "model", "provider")},
                   "identity_limit": "Observed native configuration and executable files, not actor authentication or remote backend attestation."}
    preflight = run_bounded([*common, "debug", "prompt-input", "Catalog inspection only. Do not perform work."],
                            cwd=fixture, timeout=30, max_bytes=args.max_bytes,
                            stdout_path=output / "native-prompt-input.json", stderr_path=output / "preflight.stderr")
    _private_json(output / "preflight-process.json", preflight)
    if preflight["returncode"] or preflight["timed_out"] or preflight["output_limit"] or preflight["encoding_error"]:
        raise ValueError("native catalog preflight failed; no model call started")
    catalog = validate_catalog(parse_catalog(json.loads(preflight["stdout"], object_pairs_hook=_pairs)),
                               snapshot / "skills", cases["tracked_skills"], omitted=omitted)
    _private_json(output / "catalog.json", catalog)
    observation["catalog_digest"] = catalog["digest"]
    ambient = [r for r in catalog["skills"] if r["name"] not in set(cases["tracked_skills"]) | {"dbsctr"}]
    observation["ambient_catalog_digest"] = digest(encoded(ambient))
    version = run_bounded([args.codex, "--version"], cwd=fixture, timeout=30, max_bytes=8192)
    if version["returncode"] or version["stdout"].strip() != identity["client_version"]:
        raise ValueError("native client version changed")
    request = case["input"]["execution_scope"] + "\n\n" + case["input"]["request"]
    command = [*common, "exec", "--json", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check",
               "--output-schema", str(Path(args.schema).resolve()), "-"]
    _private_json(output / "invocation.json", {"evaluator_sha256": evaluator_sha256,
                                               "argv": command, "stdin_sha256": digest(request.encode()),
                                               "schema_sha256": digest(Path(args.schema).read_bytes()), "identity": identity})
    result = run_bounded(command, cwd=fixture, stdin=request, timeout=args.timeout, max_bytes=args.max_bytes,
                         stdout_path=output / "native-events.jsonl", stderr_path=output / "native.stderr")
    _private_json(output / "native-process.json", result)
    observation["elapsed_ms"] = result["elapsed_ms"]
    observation["raw_events_digest"] = result["stdout_sha256"]
    try:
        events = decode_native_events(result["stdout"])
        parsed = parse_events(events, snapshot / "skills", returncode=result["returncode"])
        if result["timed_out"] or result["output_limit"] or result["encoding_error"]:
            parsed["status"] = "failed"
            parsed["errors"].append("timeout" if result["timed_out"] else "output_limit" if result["output_limit"] else "invalid_encoding")
        observation.update(parsed)
    except (ValueError, KeyError, TypeError) as error:
        observation.update(status="failed", usage={k: None for k in USAGE}, reads=[], final_output=None,
                           command_count=None, errors=["invalid_native_capture:" + type(error).__name__])
    try:
        verify_snapshot(snapshot)
        if _identity(args.identity) != identity:
            raise ValueError("native identity changed")
    except (ValueError, OSError):
        observation["status"] = "failed"
        observation["errors"].append("identity_changed")
    observation["score"] = score_observation(observation, oracle["cases"][args.case_id])
    _private_json(output / "observation.json", observation)
    print(json.dumps({"case_id": args.case_id, "arm": args.arm, "order": args.order,
                      "status": observation["status"], "usage": observation["usage"],
                      "routing_passed": observation["score"]["routing_passed"]}))
    return 0 if observation["status"] == "complete" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--source", required=True)
    prepare.add_argument("--ref")
    prepare.add_argument("--snapshot", required=True)
    prepare.add_argument("--cases", required=True)
    run = sub.add_parser("run-one")
    for name in ("snapshot", "cases", "oracle", "schema", "identity", "output", "case-id", "arm"):
        run.add_argument("--" + name, required=True)
    run.add_argument("--repetition", type=int, required=True)
    run.add_argument("--order", type=int, required=True)
    run.add_argument("--codex", default="codex")
    run.add_argument("--installed-skills", default=str(Path.home() / ".agents/skills"))
    run.add_argument("--timeout", type=float, default=240)
    run.add_argument("--max-bytes", type=int, default=2097152)
    run.add_argument("--allow-native", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            cases = load_cases(args.cases)
            manifest = prepare_snapshot(args.source, args.snapshot, cases["tracked_skills"], git_ref=args.ref)
            print(json.dumps({"source_digest": manifest["source_digest"], "files": len(manifest["files"])}))
            return 0
        return run_one(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, "skill-router evaluation failed: " + type(error).__name__ + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
