"""Execute and reconcile complete pytest lanes without extending job deadlines."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import NamedTuple
import xml.etree.ElementTree as ET

import pytest


PARTITIONS = 4
MAX_BYTES = 32 * 1024 * 1024
MAX_NODEID = 4 * 1024 * 1024
MAX_SUBTESTS = 100_000
AUTHORITIES = ("tests/ci_shard.py", ".github/workflows/test.yml")
IDENTITY_FIELDS = {
    "repository", "commit", "tree", "run_id", "attempt", "python_version",
    "worktrunk_version", "authority",
}
RECEIPT_FIELDS = {
    "schema_version", "identity", "shard", "collected", "selected", "reports",
    "collection_complete", "collection_reports", "exit_code", "python_full", "subtests",
}


class ExecutionCounts(NamedTuple):
    passed: int
    skipped: set[str]
    junit_skips: dict[str, int]
    junit_tests: int
    subtests_passed: int
    subtests_skipped: int


def partition(nodeid: str) -> int:
    """Keep module fixtures together and isolate the two measured heavy modules."""
    identifiers([nodeid])
    module = nodeid.split("::", 1)[0]
    if module == "tests/test_initiative_authority_amendment.py":
        return 0
    if module == "tests/test_lineage_recovery.py":
        return 1
    return 2 + int.from_bytes(hashlib.sha256(module.encode()).digest(), "big") % 2


def identifiers(value: object) -> list[str]:
    if not isinstance(value, list) or not 0 < len(value) <= 100_000:
        raise ValueError("invalid or empty test population")
    for nodeid in value:
        if (not isinstance(nodeid, str) or not 0 < len(nodeid) <= MAX_NODEID
                or any(ord(c) < 32 for c in nodeid)):
            raise ValueError("invalid test identifier")
        module = nodeid.split("::", 1)[0]
        path = PurePosixPath(module)
        if (not module.startswith("tests/") or not module.endswith(".py")
                or "\\" in module or ".." in path.parts or path.as_posix() != module):
            raise ValueError("invalid test module")
    if len(set(value)) != len(value):
        raise ValueError("duplicate test identifier")
    return value


def read_bounded(path: Path) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise ValueError("evidence file cannot be safely opened") from error
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError("unsafe or oversized evidence file")
        content = stream.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("oversized evidence file")
    return content


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    value: dict = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON field")
        value[key] = item
    return value


def check_identity(value: dict) -> None:
    if not isinstance(value, dict) or set(value) != IDENTITY_FIELDS:
        raise ValueError("invalid identity fields")
    patterns = {
        "repository": r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        "commit": r"[0-9a-f]{40}", "tree": r"[0-9a-f]{40}",
        "run_id": r"[1-9][0-9]{0,19}", "attempt": r"[1-9][0-9]{0,5}",
        "python_version": r"3\.(12|13|14)", "worktrunk_version": r"0\.(80|81)\.0",
    }
    for name, pattern in patterns.items():
        if not isinstance(value[name], str) or not re.fullmatch(pattern, value[name]):
            raise ValueError("invalid execution identity")
    authority = value["authority"]
    if (not isinstance(authority, dict) or set(authority) != set(AUTHORITIES)
            or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)
                   for v in authority.values())):
        raise ValueError("invalid source authority")


def execution_counts(receipt: dict, selected: list[str]) -> ExecutionCounts:
    reports = receipt["reports"]
    if not isinstance(reports, list) or len(reports) > 3 * len(selected):
        raise ValueError("invalid execution reports")
    phases: dict[str, dict[str, str]] = {nodeid: {} for nodeid in selected}
    for report in reports:
        if (not isinstance(report, dict) or set(report) != {"nodeid", "when", "outcome"}
                or not isinstance(report["nodeid"], str) or report["nodeid"] not in phases
                or report["when"] not in ("setup", "call", "teardown")
                or report["outcome"] not in ("passed", "skipped")):
            raise ValueError("failed or invalid test phase")
        node = phases[report["nodeid"]]
        if report["when"] in node:
            raise ValueError("duplicate test phase")
        node[report["when"]] = report["outcome"]
    skipped = set()
    for nodeid, node in phases.items():
        expected = {"setup", "teardown"} if node.get("setup") == "skipped" else {
            "setup", "call", "teardown",
        }
        if set(node) != expected:
            raise ValueError("incomplete test execution")
        if "skipped" in node.values():
            skipped.add(nodeid)
    children = receipt["subtests"]
    if not isinstance(children, list) or len(children) > MAX_SUBTESTS:
        raise ValueError("invalid subtest population")
    occurrences: dict[str, int] = {}
    junit_skips = {nodeid: sum(value == "skipped" for value in node.values())
                   for nodeid, node in phases.items()}
    children_passed = children_skipped = 0
    for child in children:
        if (not isinstance(child, dict) or set(child) != {"nodeid", "index", "outcome"}
                or not isinstance(child["nodeid"], str) or child["nodeid"] not in phases
                or type(child["index"]) is not int
                or child["index"] != occurrences.get(child["nodeid"], 0) + 1
                or child["outcome"] not in ("passed", "skipped")
                or phases[child["nodeid"]].get("setup") != "passed"):
            raise ValueError("failed or invalid subtest occurrence")
        nodeid = child["nodeid"]
        occurrences[nodeid] = child["index"]
        if child["outcome"] == "skipped":
            children_skipped += 1
            junit_skips[nodeid] += 1
        else:
            children_passed += 1
    junit_tests = (sum(node.get("call") == "passed" for node in phases.values())
                   + sum(junit_skips.values()) + children_passed)
    return ExecutionCounts(len(selected) - len(skipped), skipped, junit_skips, junit_tests,
                           children_passed, children_skipped)


def collection_skips(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > 100_000:
        raise ValueError("invalid collection reports")
    skipped = []
    for report in value:
        if (not isinstance(report, dict) or set(report) != {"nodeid", "outcome"}
                or report["outcome"] != "skipped"):
            raise ValueError("failed or invalid collection report")
        identifiers([report["nodeid"]])
        if "::" in report["nodeid"]:
            raise ValueError("unsupported skipped collector identity")
        skipped.append(report["nodeid"])
    if len(set(skipped)) != len(skipped):
        raise ValueError("duplicate collection skip")
    return skipped


def check_junit(path: Path, selected: list[str], skip_counts: dict[str, int],
                collectors: list[str], test_count: int) -> None:
    content = read_bounded(path)
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("unsafe JUnit declaration")
    try:
        tree = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError("invalid JUnit") from error
    if tree.tag != "testsuites" or tree.findall(".//failure") or tree.findall(".//error"):
        raise ValueError("failed JUnit")
    suites = tree.findall("testsuite")
    if len(suites) != 1 or list(tree) != suites or suites[0].findall(".//testsuite"):
        raise ValueError("unexpected JUnit suite structure")
    expected_counts = {
        "tests": test_count + len(collectors),
        "skipped": sum(skip_counts.values()) + len(collectors), "errors": 0, "failures": 0,
    }
    for name, expected in expected_counts.items():
        value = suites[0].get(name)
        if (not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]{0,5}", value)
                or int(value) != expected):
            raise ValueError("JUnit event counter mismatch")
    nodeids = []
    collector_ids = []
    for case in tree.findall(".//testcase"):
        properties = [p.get("value") for p in case.findall("./properties/property")
                      if p.get("name") == "ci_nodeid"]
        if not properties:
            # Pytest emits no user properties for module-level collection skips.
            # Their simple module paths have an explicit, unambiguous mapping.
            matches = [nodeid for nodeid in collectors
                       if case.get("classname") == ""
                       and case.get("name") == nodeid.replace("/", ".").removesuffix(".py")]
            skips = case.findall("skipped")
            if len(matches) != 1 or len(skips) != 1 or skips[0].get("message") != "collection skipped":
                raise ValueError("unidentified JUnit collection outcome")
            collector_ids.extend(matches)
            continue
        if len(properties) != 1 or not isinstance(properties[0], str):
            raise ValueError("JUnit lacks exact item identity")
        if len(case.findall("skipped")) != skip_counts.get(properties[0], 0):
            raise ValueError("JUnit skip outcome mismatch")
        nodeids.extend(properties)
    if len(nodeids) != len(selected) or set(nodeids) != set(selected):
        raise ValueError("JUnit population mismatch")
    if len(collector_ids) != len(collectors) or set(collector_ids) != set(collectors):
        raise ValueError("JUnit collection skip mismatch")


def verify(root: Path, expected: dict, workers_result: str) -> dict:
    """Fail closed on native job failures or incomplete/unrelated evidence."""
    check_identity(expected)
    if workers_result != "success":
        raise ValueError("native worker jobs did not all succeed")
    names = {f"pytest-{expected['python_version']}-{expected['worktrunk_version']}-{s}"
             for s in range(PARTITIONS)}
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != names:
        raise ValueError("missing or unexpected partition evidence")
    universe = None
    full_runtime = None
    skipped_collectors = None
    covered: set[str] = set()
    passed = skipped = subtests_passed = subtests_skipped = 0
    for shard in range(PARTITIONS):
        directory = root / f"pytest-{expected['python_version']}-{expected['worktrunk_version']}-{shard}"
        if (directory.is_symlink() or not directory.is_dir()
                or {p.name for p in directory.iterdir()} != {"manifest.json", "junit.xml"}):
            raise ValueError("unsafe or unexpected partition files")
        receipt = json.loads(read_bounded(directory / "manifest.json"), object_pairs_hook=unique_object)
        if (not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS
                or type(receipt["schema_version"]) is not int or receipt["schema_version"] != 2
                or type(receipt["shard"]) is not int or receipt["shard"] != shard
                or receipt["identity"] != expected or receipt["collection_complete"] is not True
                or type(receipt["exit_code"]) is not int or receipt["exit_code"] != 0
                or not isinstance(receipt["python_full"], str)
                or not re.fullmatch(re.escape(expected["python_version"]) + r"\.[0-9]+", receipt["python_full"])):
            raise ValueError("stale, nonterminal or invalid partition receipt")
        collectors = collection_skips(receipt["collection_reports"])
        if full_runtime is None:
            full_runtime = receipt["python_full"]
            skipped_collectors = collectors
        if receipt["python_full"] != full_runtime or collectors != skipped_collectors:
            raise ValueError("workers disagree about runtime or collection outcomes")
        collected = identifiers(receipt["collected"])
        selected = identifiers(receipt["selected"])
        if universe is None:
            universe = collected
        if collected != universe:
            raise ValueError("workers disagree about full collection")
        if selected != [nodeid for nodeid in collected if partition(nodeid) == shard]:
            raise ValueError("partition assignment mismatch")
        if covered.intersection(selected):
            raise ValueError("overlapping partition execution")
        covered.update(selected)
        counts = execution_counts(receipt, selected)
        if set(collectors).intersection(node.split("::", 1)[0] for node in collected):
            raise ValueError("skipped collector also contains executable items")
        check_junit(directory / "junit.xml", selected, counts.junit_skips, collectors,
                    counts.junit_tests)
        passed += counts.passed
        skipped += len(counts.skipped)
        subtests_passed += counts.subtests_passed
        subtests_skipped += counts.subtests_skipped
    if covered != set(universe or []):
        raise ValueError("incomplete full-suite coverage")
    return {"selected": len(covered), "passed": passed, "skipped": skipped,
            "collection_skipped": len(skipped_collectors or []),
            "subtests_passed": subtests_passed, "subtests_skipped": subtests_skipped}


class PartitionPlugin:
    def __init__(self, shard: int, modules: set[str]):
        self.shard = shard
        self.modules = modules
        self.visited: set[str] = set()
        self.collection_reports: list[dict[str, str]] = []
        self.collected: list[str] = []
        self.selected: list[str] = []
        self.reports: list[dict[str, str]] = []
        self.subtests: list[dict[str, str | int]] = []
        self.subtest_counts: dict[str, int] = {}
        self.complete = False

    def pytest_configure(self, config):
        selectors = ("keyword", "markexpr", "deselect", "ignore", "ignore_glob",
                     "collectonly", "lf", "ff", "stepwise", "stepwise_skip", "pyargs")
        if (config.args != ["tests"] or config.getini("python_files") != ["test_*.py", "*_test.py"]
                or any(getattr(config.option, key, None) for key in selectors)):
            raise pytest.UsageError("full-suite invocation must not select or exclude tests")

    def pytest_collectreport(self, report):
        if report.nodeid in self.modules:
            self.visited.add(report.nodeid)
        if not report.passed:
            self.collection_reports.append({"nodeid": report.nodeid, "outcome": report.outcome})

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_collection_modifyitems(self, config, items):
        self.collected = identifiers([item.nodeid for item in items])
        outcome = yield
        outcome.get_result()
        if [item.nodeid for item in items] != self.collected:
            raise pytest.UsageError("full-suite collection was filtered or rewritten")
        if not {node.split("::", 1)[0] for node in self.collected}.issubset(self.modules):
            raise pytest.UsageError("collected test module is outside the source inventory")
        selected, deselected = [], []
        for item in items:
            if any(name == "ci_nodeid" for name, _ in item.user_properties):
                raise pytest.UsageError("reserved CI item identity already exists")
            item.user_properties.append(("ci_nodeid", item.nodeid))
            (selected if partition(item.nodeid) == self.shard else deselected).append(item)
        self.selected = [item.nodeid for item in selected]
        identifiers(self.selected)
        items[:] = selected
        config.hook.pytest_deselected(items=deselected)

    def pytest_collection_finish(self, session):
        if self.visited != self.modules or [item.nodeid for item in session.items] != self.selected:
            raise pytest.UsageError("partition changed after selection")
        self.complete = True

    def pytest_runtest_logreport(self, report):
        if isinstance(report, pytest.SubtestReport):
            if report.when != "call" or len(self.subtests) >= MAX_SUBTESTS:
                raise pytest.UsageError("invalid or oversized native subtest population")
            index = self.subtest_counts.get(report.nodeid, 0) + 1
            self.subtest_counts[report.nodeid] = index
            self.subtests.append({"nodeid": report.nodeid, "index": index,
                                  "outcome": report.outcome})
            return
        self.reports.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome})


def checkout_identity(args: argparse.Namespace) -> dict:
    def git(*arguments):
        return subprocess.check_output(["git", *arguments], text=True, timeout=30).strip()

    value = {name: getattr(args, name) for name in IDENTITY_FIELDS - {"tree", "authority"}}
    value["tree"] = git("rev-parse", "HEAD^{tree}")
    value["authority"] = {p: hashlib.sha256(read_bounded(Path(p))).hexdigest() for p in AUTHORITIES}
    check_identity(value)
    if git("rev-parse", "HEAD") != value["commit"]:
        raise ValueError("checkout does not match workflow source")
    subprocess.run(["git", "diff", "--exit-code", "--quiet", "HEAD", "--"],
                   check=True, timeout=30)
    return value


def run(args: argparse.Namespace, identity: dict) -> int:
    if f"{sys.version_info.major}.{sys.version_info.minor}" != args.python_version:
        raise ValueError("actual Python runtime differs from selected lane")
    version = subprocess.check_output(["wt", "--version"], text=True, timeout=30).strip()
    if version != f"wt v{args.worktrunk_version}":
        raise ValueError("actual Worktrunk differs from selected lane")
    if os.environ.get("PYTEST_ADDOPTS") or os.environ.get("PYTEST_PLUGINS"):
        raise ValueError("ambient pytest selection/plugins are forbidden")
    args.output.mkdir(parents=True, exist_ok=False)
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", "tests"], timeout=30)
    modules = {os.fsdecode(p) for p in tracked.split(b"\0") if p and any(
        fnmatch.fnmatchcase(Path(os.fsdecode(p)).name, pattern)
        for pattern in ("test_*.py", "*_test.py")
    )}
    if not modules:
        raise ValueError("tracked full-suite module inventory is empty")
    plugin = PartitionPlugin(args.shard, modules)
    result = int(pytest.main([
        "--maxfail=1", "--durations=25", "-ra", f"--junitxml={args.output / 'junit.xml'}",
    ], plugins=[plugin]))
    if checkout_identity(args) != identity:
        raise ValueError("source identity changed during execution")
    receipt = {
        "schema_version": 2, "identity": identity, "shard": args.shard,
        "collected": plugin.collected, "selected": plugin.selected, "reports": plugin.reports,
        "collection_complete": plugin.complete, "exit_code": result,
        "collection_reports": plugin.collection_reports,
        "subtests": plugin.subtests,
        "python_full": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
    payload = json.dumps(receipt, sort_keys=True).encode()
    if len(payload) > MAX_BYTES:
        raise ValueError("partition receipt exceeds evidence budget")
    (args.output / "manifest.json").write_bytes(payload + b"\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "verify"))
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--worktrunk-version", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard", type=int, choices=range(PARTITIONS))
    parser.add_argument("--workers-result")
    args = parser.parse_args(argv)
    try:
        identity = checkout_identity(args)
        if args.mode == "run":
            if args.shard is None or args.workers_result is not None:
                raise ValueError("run requires one partition and no aggregate result")
            return run(args, identity)
        if args.shard is not None:
            raise ValueError("verify does not select a partition")
        print(json.dumps(verify(args.output, identity, args.workers_result), sort_keys=True))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"CI evidence rejected: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
