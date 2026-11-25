"""Compare retained validation evidence offline; never decide whether to run a check."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import itertools
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from xml.parsers import expat


MIB = 1024 * 1024
NOTE_BYTES = 4 * MIB
PARTITION_BYTES = 32 * MIB  # same per-file budget as the required verifier
MAX_JOBS = 64
MAX_PARTITIONS = 16
MAX_ITEMS = 100_000
CHECKS = {
    "dotfiles.syntax", "dotfiles.instructions", "dotfiles.adapter",
    "dotfiles.lifecycle", "dotfiles.full", "dotfiles.portable",
}
EARLY = "Check publication and instruction contracts"
VERIFY = "Verify complete lane coverage"
WORKER = r"Full suite \((3\.(?:12|13|14|15)), partition ([0-3])\)"
SUMMARY = r"test \((3\.(?:12|13|14|15))\)"
ARTIFACT = r"pytest-(3\.(?:12|13|14|15))-(0\.(?:80|81)\.0)-([0-3])"
NON_PR_EVENTS = ("push", "schedule", "workflow_dispatch")


def matches(pattern, value):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def oid(value):
    return value if matches(r"[0-9a-f]{40}", value) else None


def digest(value):
    return matches(r"[0-9a-f]{64}", value)


def identifier(value):
    return matches(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value)


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def timestamp(value):
    if matches(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)", value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON value")
    return result


def open_directory(root, *children):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(root, flags)
    try:
        for name in children:
            child = os.open(name, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
    except OSError:
        os.close(descriptor)
        raise
    return descriptor


def read_bounded(root, relative, limit):
    *parents, name = relative.split("/")
    directory = open_directory(root, *parents)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError("unsafe or oversized input")
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("oversized input")
    return content


def read_json(root, relative, limit):
    raw = read_bounded(root, relative, limit)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                       parse_float=finite_float, parse_constant=finite_float)
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value, raw


def optional_json(root, relative, limit):
    try:
        return read_json(root, relative, limit)[0]
    except (OSError, ValueError, RecursionError):
        return None


def bounded_projection(value):
    # The exporter admits owner-projected summaries of at most 8192 bytes.
    return isinstance(value, dict) and len(json.dumps(value, ensure_ascii=True)) <= 8192


def versioned(value, version, kind):
    return (isinstance(value, dict) and type(value.get("schema_version")) is int
            and value["schema_version"] == version and value.get("kind") == kind)


def load_note(root):
    try:
        note, raw = read_json(root, "note.json", NOTE_BYTES)
        adapter, selection, executions = (note.get(key) for key in ("adapter", "selection", "executions"))
        if (not versioned(note, 1, "dbsctr-validation-manifest")
                or set(note) != {"schema_version", "kind", "head", "base", "exported_at",
                                 "adapter", "selection", "executions"}
                or not oid(note["head"]) or not oid(note["base"]) or not timestamp(note["exported_at"])
                or not isinstance(adapter, dict) or set(adapter) != {"id", "digest"}
                or not identifier(adapter["id"]) or not digest(adapter["digest"])
                or not isinstance(selection, dict) or set(selection) != {"basis", "checks"}
                or selection["basis"] not in ("affected", "broad", "full")
                or not isinstance(selection["checks"], list) or len(selection["checks"]) > 128
                or not isinstance(executions, list) or len(executions) > 4096):
            raise ValueError("invalid manifest envelope")
        checks = set()
        for check in selection["checks"]:
            if (not isinstance(check, dict) or set(check) != {"id", "test_identity"}
                    or not identifier(check["id"]) or check["id"] in checks
                    or not bounded_projection(check["test_identity"])):
                raise ValueError("invalid selected check")
            checks.add(check["id"])
        ids = set()
        for item in executions:
            if (not isinstance(item, dict) or set(item) != {
                    "id", "check_id", "result", "snapshot_id", "head", "lane", "test_identity",
                    "elapsed_seconds", "referenced_by",
                } or not identifier(item["id"]) or item["id"] in ids
                or not identifier(item["check_id"]) or item["check_id"] not in checks
                or item["result"] not in ("passed", "failed", "interrupted", "unavailable")
                or not digest(item["snapshot_id"]) or not oid(item["head"])
                or not bounded_projection(item["lane"]) or not bounded_projection(item["test_identity"])
                or type(item["elapsed_seconds"]) not in (int, float)
                or not 0 <= item["elapsed_seconds"] <= 86400
                or not isinstance(item["referenced_by"], list) or len(item["referenced_by"]) > 128
                or not all(map(identifier, item["referenced_by"]))):
                raise ValueError("invalid execution claim")
            ids.add(item["id"])
        return note, "present", hashlib.sha256(raw).hexdigest()
    except FileNotFoundError:
        return None, "manifest_unavailable", None
    except (OSError, ValueError, RecursionError):
        return None, "manifest_malformed", None


def whole_group(receipt, hosted):
    """Match the producer's complete summary to an independently verified hosted group."""
    if not isinstance(hosted, dict):
        return False
    size = hosted.get("case_count")
    outcomes = receipt.get("outcomes")
    return (versioned(receipt, 1, "pytest-junit-v1")
            and receipt.get("encoding") == hosted.get("encoding") == "pytest-nodeid-or-sha256-v1"
            and receipt.get("scope") == "completed" and receipt.get("complete") is True
            and integer(size, 1, 10_000)
            and integer(receipt.get("case_count"), size, size)
            and integer(receipt.get("reported_count"), size, size)
            and integer(receipt.get("omitted_count"), 0, 0)
            and integer(receipt.get("opaque_count"), 0, size)
            and digest(receipt.get("ids_digest")) and receipt["ids_digest"] == hosted.get("ids_digest")
            and isinstance(outcomes, dict) and set(outcomes) == {"passed", "skipped", "failed", "error"}
            and integer(outcomes["passed"], size, size)
            and all(integer(outcomes[key], 0, 0) for key in ("skipped", "failed", "error"))
            and receipt.get("failed_test_ids") == [])


def classify(note, status, head, base, check, *, source=None, hosted_group=None, lane=None):
    """Admit only independently verified source, group and lane facts, never note assertions."""
    if note is None:
        return "must_run", status
    if head is not None and note["head"] != head:
        return "must_run", "head_mismatch"
    if base is not None and note["base"] != base:
        return "must_run", "base_advanced"
    if not any(item["id"] == check for item in note["selection"]["checks"]):
        return "must_run", "not_selected_locally"
    receipts = [item for item in note["executions"] if item["check_id"] == check]
    if not receipts:
        return "must_run", "no_receipt"
    passing = [item for item in receipts if item["result"] == "passed"]
    if not passing:
        return "must_run", "receipt_failed"
    if source == "changed":
        return "must_run", "source_changed"
    if head is None or base is None or source != "equivalent":
        return "must_run", "source_unverified"
    if not any(item["head"] == head and whole_group(item["test_identity"], hosted_group)
               for item in passing):
        return "must_run", "test_identity_unverified"
    if lane == "match":
        return "would_reuse", None
    return "would_reuse_if_lane_equivalent", "lane_mismatch" if lane == "mismatch" else "lane_unverified"


def repetition(early, partitions):
    """Inputs are complete lists of (verified source/runtime, executed identities)."""
    if early is None or partitions is None:
        return {"identities": None, "extra_executions": None}
    early_counts = Counter((key, node) for key, nodes in early for node in nodes)
    partition_counts = Counter((key, node) for key, nodes in partitions for node in nodes)
    repeated = [number + partition_counts[key] - 1 for key, number in early_counts.items()
                if number + partition_counts[key] > 1]
    return {"identities": len(repeated), "extra_executions": sum(repeated)}


def elapsed(start, finish):
    if start is None or finish is None or finish < start:
        return None
    return (finish - start).total_seconds()


def interval(record):
    return timestamp(record.get("started_at")), timestamp(record.get("completed_at"))


def step(job, name):
    steps = job.get("steps")
    if isinstance(steps, list) and len(steps) <= 128:
        found = [item for item in steps if isinstance(item, dict) and item.get("name") == name]
        if len(found) == 1:
            return found[0]
    return {}


def step_duration(job, name):
    start, end = interval(step(job, name))
    job_start, job_end = interval(job)
    if (start is not None and job_start is not None and start < job_start
            or end is not None and job_end is not None and end > job_end):
        return None
    return elapsed(start, end)


def range_seconds(values):
    if not values or None in values:
        return {"min": None, "max": None}
    return {"min": min(values), "max": max(values)}


def read_jobs(root, run, unavailable):
    envelope = optional_json(root, "jobs.json", 4 * MIB)
    jobs = envelope.get("jobs") if envelope is not None else None
    if (not isinstance(jobs, list) or not 0 < len(jobs) <= MAX_JOBS
            or type(envelope.get("total_count")) is not int or envelope["total_count"] != len(jobs)
            or not integer(run.get("id"), 1, 10**20 - 1)
            or not integer(run.get("run_attempt"), 1, 999999)
            or any(not isinstance(job, dict) or type(job.get("run_id")) is not int
                   or job["run_id"] != run["id"] or type(job.get("run_attempt")) is not int
                   or job["run_attempt"] != run["run_attempt"] for job in jobs)):
        unavailable.add("jobs")
        return {}, {}
    workers, summaries = {}, {}
    for job in jobs:
        name = job.get("name")
        if matches(WORKER, name):
            python, shard = re.fullmatch(WORKER, name).groups()
            key, target = (python, int(shard)), workers
        elif matches(SUMMARY, name):
            key, target = re.fullmatch(SUMMARY, name)[1], summaries
        else:
            continue
        if key in target:
            unavailable.add("jobs")
            return {}, {}
        target[key] = job
    return workers, summaries


def timings(run, workers, summaries, unavailable):
    lanes = {python for python, _ in workers} | summaries.keys()
    complete = bool(lanes) and set(workers) == {(python, i) for python in lanes for i in range(4)}
    worker_values = list(workers.values()) if complete else []
    worker_spans = [interval(job) for job in worker_values]
    workers_end = [end for start, end in worker_spans if elapsed(start, end) is not None]
    summary_spans = [interval(job) for job in summaries.values()] if summaries.keys() == lanes else []
    tail = None
    if (workers_end and len(workers_end) == len(worker_spans) and summary_spans
            and all(elapsed(start, end) is not None and start >= max(workers_end)
                    for start, end in summary_spans)):
        tail = elapsed(max(workers_end), max(end for _, end in summary_spans))
    verify_values = [step_duration(job, VERIFY) for job in summaries.values()]
    values = {
        "queue_seconds": elapsed(timestamp(run.get("created_at")), timestamp(run.get("run_started_at"))),
        "worker_seconds": range_seconds([elapsed(*span) for span in worker_spans]),
        "early_step_seconds": range_seconds([step_duration(job, EARLY) for job in worker_values]),
        "summary_tail_seconds": tail,
        "verification_seconds": (verify_values[0] if len(verify_values) == 1 else None),
    }
    unavailable.update(key for key, value in values.items()
                       if value is None or isinstance(value, dict) and None in value.values())
    return values


def nodeids(items):
    if not isinstance(items, list) or not 0 < len(items) <= MAX_ITEMS:
        raise ValueError("invalid test population")
    for node in items:
        if (not isinstance(node, str) or not node or len(node) > 4 * MIB
                or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in node)):
            raise ValueError("invalid test identity")
        module = node.split("::", 1)[0]
        path = PurePosixPath(module)
        if (not module.startswith("tests/") or not module.endswith(".py")
                or "\\" in module or ".." in path.parts or str(path) != module):
            raise ValueError("invalid test module")
    if len(set(items)) != len(items):
        raise ValueError("duplicate test identities")
    return items


def partition_for(node):
    module = node.split("::", 1)[0]
    if module == "tests/test_initiative_authority_amendment.py":
        return 0
    if module == "tests/test_lineage_recovery.py":
        return 1
    return 2 + hashlib.sha256(module.encode()).digest()[-1] % 2


def junit_population(raw):
    """Read only explicit pytest properties, not JUnit names or arbitrary output."""
    stack = []
    identities = set()
    unidentified, suite_count, elements = 0, 0, 0
    current = None

    def bad(*_):
        raise ValueError("invalid JUnit structure")

    def start(tag, attrs):
        nonlocal current, elements, suite_count
        stack.append(tag)
        elements += 1
        if elements > 1_000_000 or len(stack) > 32 or len(attrs) > 32:
            bad()
        if len(stack) == 1 and tag != "testsuites":
            bad()
        if tag == "testsuite":
            suite_count += 1
            if stack != ["testsuites", "testsuite"] or suite_count != 1:
                bad()
        if tag == "testcase":
            if stack != ["testsuites", "testsuite", "testcase"]:
                bad()
            current = None
        if (tag == "property" and stack == ["testsuites", "testsuite", "testcase", "properties", "property"]
                and attrs.get("name") == "ci_nodeid"):
            if current is not None or not attrs.get("value"):
                bad()
            current = attrs["value"]

    def end(tag):
        nonlocal unidentified
        if tag == "testcase":
            if current is None:
                unidentified += 1
            elif current in identities:
                bad()
            else:
                identities.add(current)
            if len(identities) + unidentified > MAX_ITEMS:
                bad()
        stack.pop()

    parser = expat.ParserCreate(encoding="UTF-8")
    parser.StartDoctypeDeclHandler = bad
    parser.ExternalEntityRefHandler = bad
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(raw, True)
    if suite_count != 1:
        bad()
    return identities, unidentified


def partition_group(root, name, run, tested):
    value, _ = read_json(root, f"partitions/{name}/manifest.json", PARTITION_BYTES)
    identity = value.get("identity")
    python, worktrunk, shard = re.fullmatch(ARTIFACT, name).groups()
    repository = run.get("repository")
    if (not integer(value.get("schema_version"), 2, 2) or not isinstance(identity, dict)
            or not isinstance(repository, dict) or not isinstance(repository.get("full_name"), str)
            or not integer(run.get("id"), 1, 10**20 - 1) or not integer(run.get("run_attempt"), 1, 999999)
            or not oid(identity.get("commit")) or tested is not None and identity["commit"] != tested
            or (identity.get("repository"), identity.get("run_id"),
                              identity.get("attempt"), identity.get("python_version"),
                              identity.get("worktrunk_version")) != (
                                  repository["full_name"], str(run["id"]), str(run["run_attempt"]),
                                  python, worktrunk)
            or not oid(identity.get("tree")) or not integer(value.get("shard"), int(shard), int(shard))
            or not matches(re.escape(python) + r"\.[0-9]{1,3}", value.get("python_full"))
            or value.get("collection_complete") is not True):
        raise ValueError("unrelated or incomplete partition")
    authority = identity.get("authority")
    if (not isinstance(authority, dict) or set(authority) != {"tests/ci_shard.py", ".github/workflows/test.yml"}
            or not all(map(digest, authority.values()))):
        raise ValueError("invalid partition authority")
    collected, selected = nodeids(value.get("collected")), nodeids(value.get("selected"))
    if selected != [node for node in collected if partition_for(node) == int(shard)]:
        raise ValueError("partition selection does not match collection")
    # A manifest retains the selected group even if the worker did not finish
    # executing it. JUnit must independently account for the complete group
    # before its execution identities could be used.
    try:
        junit_ids, unidentified = junit_population(read_bounded(root, f"partitions/{name}/junit.xml",
                                                                PARTITION_BYTES))
        collectors = value.get("collection_reports")
        reconciled = (junit_ids == set(selected) and isinstance(collectors, list)
                      and len(collectors) == unidentified)
    except (OSError, ValueError, expat.ExpatError):
        reconciled = False
    return (python, int(shard)), (value["python_full"], worktrunk), reconciled


def partition_groups(root, run, tested, workers, unavailable):
    groups = {}
    try:
        descriptor = open_directory(root, "partitions")
        try:
            with os.scandir(descriptor) as entries:
                names = [entry.name for entry in itertools.islice(entries, MAX_PARTITIONS + 1)]
        finally:
            os.close(descriptor)
    except OSError:
        names = []
    if len(names) > MAX_PARTITIONS:
        unavailable.add("partitions")
        return groups
    for name in sorted(names):
        if not matches(ARTIFACT, name):
            unavailable.add("partitions")
            continue
        try:
            key, lane, reconciled = partition_group(root, name, run, tested)
        except (OSError, ValueError, RecursionError):
            unavailable.add("partitions")
            continue
        if key in groups:
            unavailable.add("partitions")
            return {}
        groups[key] = lane
        if not reconciled:
            unavailable.add("partition_junit")
    lanes = {python for python, _ in groups.keys() | workers.keys()}
    if not groups or set(groups) != {(python, i) for python in lanes for i in range(4)}:
        unavailable.add("partitions")
    return groups


def affected_checks(root, base, tested, unavailable):
    result = optional_json(root, "affected/result.json", 4 * MIB)
    if (not versioned(result, 1, "dotfiles-validation-run")
            or result.get("adapter_id") != "dotfiles.continuous-validation"
            or tested is None or base is None or result.get("head") != tested or result.get("base") != base
            or not isinstance(result.get("executed"), list) or len(result["executed"]) > len(CHECKS)):
        unavailable.add("affected")
        return []
    checks = []
    seen = set()
    for item in result["executed"]:
        if (not isinstance(item, dict) or not isinstance(item.get("check_id"), str)
                or item["check_id"] not in CHECKS or item["check_id"] in seen
                or item.get("status") not in ("passed", "failed", "unavailable", "interrupted")):
            unavailable.add("affected")
            return []
        seen.add(item["check_id"])
        if item["status"] in ("passed", "failed"):
            checks.append(item["check_id"])
    not_executed = result.get("not_executed", [])
    if not isinstance(not_executed, list) or len(not_executed) > len(CHECKS):
        unavailable.add("affected")
        return []
    budget_exhausted = False
    for item in not_executed:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or item["id"] not in CHECKS or item["id"] in seen
                or item.get("reason") not in ("dagger_lane", "checkpoint_required", "budget_exhausted")):
            unavailable.add("affected")
            return []
        seen.add(item["id"])
        budget_exhausted |= item["reason"] == "budget_exhausted"
    if budget_exhausted:
        unavailable.add("affected_budget_exhausted")
    return checks


def lane_projection(lane):
    return {
        name: lane[name] for name, pattern in (
            ("os", r"linux|darwin|windows"), ("architecture", r"amd64|arm64|x86_64|aarch64"),
            ("python", r"3\.[0-9]{1,2}(?:\.[0-9]{1,3})?"),
        ) if matches(pattern, lane.get(name))
    }


def local_lane(note):
    # Fixed fields only; never copy note-supplied keys or opaque strings.
    projections = [lane_projection(receipt["lane"]) for receipt in note["executions"]] if note else []
    return projections[0] if projections and all(lane == projections[0] for lane in projections) else {}


def affected_lane(root, unavailable):
    value = optional_json(root, "affected/runtime.json", 8192) or {}
    projected = lane_projection(value)
    tools = value.get("tools")
    if (len(projected) != 3 or not isinstance(tools, dict)
            or not matches(r"uv [0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?: \([0-9a-f]{7,40} \d{4}-\d\d-\d\d\))?",
                           tools.get("uv"))):
        unavailable.add("affected_runtime")
        return {}
    return {**projected, "tools": {"uv": tools["uv"].split()[1]}}


def compare(root):
    unavailable = set()
    run = optional_json(root, "run.json", MIB) or {}
    if run.get("event") in NON_PR_EVENTS and integer(run.get("id"), 1, 10**20 - 1):
        return None
    if run.get("event") != "pull_request" or not integer(run.get("id"), 1, 10**20 - 1):
        unavailable.add("run")
    source = optional_json(root, "source.json", 4096) or {}
    head, base, tested = (oid(source.get(key)) for key in ("head", "base", "tested_oid"))
    if tested is not None and tested in (head, base):
        tested = None
    if not all((head, base, tested)):
        unavailable.add("source")
    note, status, manifest_digest = load_note(root)
    if note is None:
        unavailable.add(status)
    workers, summaries = read_jobs(root, run, unavailable)
    partitions = partition_groups(root, run, tested, workers, unavailable)
    groups = Counter(affected_checks(root, base, tested, unavailable))
    affected = affected_lane(root, unavailable) if "affected" not in unavailable else {}
    groups["dotfiles.full"] += len(partitions)
    groups["dotfiles.instructions"] += sum(step(job, EARLY).get("conclusion") in ("success", "failure")
                                          for job in workers.values())
    checks = []
    for check, count in sorted(groups.items()):
        if count == 0:
            continue
        selected = note is not None and any(item["id"] == check for item in note["selection"]["checks"])
        # The v1 export only names an opaque snapshot. It cannot bind a
        # receipt's tested content to the hosted commit or its Git tree.
        disposition, reason = classify(note, status, head, base, check)
        checks.append({"id": check, "selected_locally": selected,
                       "would_reuse": count if disposition == "would_reuse" else 0,
                       "would_reuse_if_lane_equivalent": count if disposition == "would_reuse_if_lane_equivalent" else 0,
                       "must_run": [{"reason": reason, "count": count}] if disposition == "must_run" else []})
        if reason == "source_unverified":
            unavailable.add("receipt_source_equivalence")
    hosted_lanes = set(partitions.values())
    hosted = {}
    if len(hosted_lanes) == 1:
        python, worktrunk = hosted_lanes.pop()
        hosted = {"python": python, "tools": {"worktrunk": worktrunk}}
    if affected:
        # Affected is a separate execution lane, not metadata for the workers.
        hosted["affected"] = affected
    unavailable.update(("early_step_execution_identities", "complete_lane_identity"))
    return {
        "schema_version": 1, "kind": "validation-shadow-report",
        "head": head, "base": base, "tested_oid": tested,
        "manifest": {"status": status, "digest": manifest_digest},
        "lane": {"local": local_lane(note), "hosted": hosted, "retained": False},
        "checks": checks, "repeated_early_selection": repetition(None, None),
        "timing": timings(run, workers, summaries, unavailable),
        "unavailable": sorted(unavailable),
    }


def markdown(report):
    lines = ["# Validation shadow", "", "Report only. The required `test` workflow remains authoritative.",
             "", f"Manifest: `{report['manifest']['status']}`", ""]
    lines.extend(f"- {label}: `{report[key] or 'unavailable'}`" for label, key in (
        ("PR head", "head"), ("Tested base", "base"), ("Tested revision", "tested_oid"),
    ))
    lines += ["", "## Checks", "", "| Check | Selected locally | Would reuse | If lane equivalent | Must run |",
              "|---|---|---:|---:|---|"]
    for check in report["checks"]:
        reasons = ", ".join(f"`{item['reason']}`: {item['count']}" for item in check["must_run"]) or "—"
        lines.append(f"| `{check['id']}` | {'yes' if check['selected_locally'] else 'no'} | "
                     f"{check['would_reuse']} | {check['would_reuse_if_lane_equivalent']} | {reasons} |")
    if not report["checks"]:
        lines += ["", "No hosted test groups were retained."]

    def number(value):
        return "unavailable" if value is None else f"{value:g}"

    lines += ["", "## Timing (seconds)", ""]
    for key, value in report["timing"].items():
        measurement = (f"{number(value['min'])} to {number(value['max'])}"
                       if isinstance(value, dict) and value["min"] is not None else
                       number(None if isinstance(value, dict) else value))
        lines.append(f"- {key.replace('_', ' ')}: {measurement}")
    lines += ["", "## Repeated early selection", ""]
    lines.extend(f"- {key.replace('_', ' ')}: {number(value)}"
                 for key, value in report["repeated_early_selection"].items())
    lines += ["", "## Unavailable", ""]
    lines.extend(f"- `{key}`" for key in report["unavailable"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compare",))
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    report = compare(args.input_dir)
    if report is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        directory = open_directory(args.output_dir)
        try:
            for name, text in (
                ("validation-shadow.json", json.dumps(report, indent=2, allow_nan=False) + "\n"),
                ("validation-shadow.md", markdown(report)),
            ):
                descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=directory)
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    stream.write(text)
        finally:
            os.close(directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
