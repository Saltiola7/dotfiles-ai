"""Bounded CI accepts only complete, matching, genuinely attempted partitions.

Synthetic receipts exercise reconciliation, not native execution qualification.
The hosted run remains the authority for actual test execution and timing.
"""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def core():
    spec = importlib.util.spec_from_file_location("ci_shard_under_test", ROOT / "tests/ci_shard.py")
    assert spec is not None and spec.loader is not None, "CI helper must have an executable module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def artifact(root, identity, shard):
    return root / f"pytest-{identity['python_version']}-{identity['worktrunk_version']}-{shard}"


def write_manifest(root, identity, manifest):
    target = artifact(root, identity, manifest["shard"]) / "manifest.json"
    target.write_text(json.dumps(manifest), encoding="utf-8")


def write_junit(root, identity, manifest):
    skipped = {
        report["nodeid"] for report in manifest["reports"] if report["outcome"] == "skipped"
    }
    suites = ET.Element("testsuites")
    suite = ET.SubElement(suites, "testsuite", name="pytest", tests=str(len(manifest["selected"])),
                          errors="0", failures="0", skipped=str(len(skipped)))
    for nodeid in manifest["selected"]:
        case = ET.SubElement(suite, "testcase", classname="synthetic", name=nodeid)
        properties = ET.SubElement(case, "properties")
        ET.SubElement(properties, "property", name="ci_nodeid", value=nodeid)
        if nodeid in skipped:
            ET.SubElement(case, "skipped", message="Existing synthetic skip")
    ET.ElementTree(suites).write(artifact(root, identity, manifest["shard"]) / "junit.xml",
                                encoding="utf-8", xml_declaration=True)


@pytest.fixture
def receipts(tmp_path, core):
    identity = {
        "repository": "example/project", "commit": "a" * 40, "tree": "b" * 40,
        "run_id": "123456", "attempt": "1", "python_version": "3.14",
        "worktrunk_version": "0.81.0",
        "authority": {"tests/ci_shard.py": "c" * 64, ".github/workflows/test.yml": "d" * 64},
    }
    nodes = [
        "tests/test_initiative_authority_amendment.py::test_existing_setup_skip",
        "tests/test_lineage_recovery.py::test_existing_call_skip",
        "tests/test_lineage_recovery.py::test_literal_parameter[<tag>::雪]",
        *[f"tests/test_sample_{index}.py::test_passes[value-{index}]" for index in range(12)],
    ]
    manifests = []
    for shard in range(4):
        selected = [node for node in nodes if core.partition(node) == shard]
        assert selected, "Synthetic collection must exercise every worker"
        reports = []
        for node in selected:
            reports.append({"nodeid": node, "when": "setup", "outcome": "skipped" if node == nodes[0] else "passed"})
            if node != nodes[0]:
                reports.append({"nodeid": node, "when": "call", "outcome": "skipped" if node == nodes[1] else "passed"})
            reports.append({"nodeid": node, "when": "teardown", "outcome": "passed"})
        manifest = {
            "schema_version": 1, "identity": copy.deepcopy(identity), "shard": shard,
            "collected": list(nodes), "selected": selected, "reports": reports,
            "collection_reports": [], "collection_complete": True,
            "exit_code": 0, "python_full": "3.14.10",
        }
        artifact(tmp_path, identity, shard).mkdir()
        write_manifest(tmp_path, identity, manifest)
        write_junit(tmp_path, identity, manifest)
        manifests.append(manifest)
    return tmp_path, identity, manifests, nodes


def test_module_assignment_preserves_affinity_and_reserved_heavy_modules(core):
    for suffix in ("test_one", "TestCase::test_two[one::two]", "test_unicode[雪]"):
        assert core.partition(f"tests/test_initiative_authority_amendment.py::{suffix}") == 0
        assert core.partition(f"tests/test_lineage_recovery.py::{suffix}") == 1
    allocations = {
        core.partition(f"tests/test_sample_{index}.py::test_one") for index in range(30)
    }
    assert allocations == {2, 3}
    for index in range(30):
        module = f"tests/test_sample_{index}.py"
        assert core.partition(module + "::test_one") == core.partition(module + "::TestCase::test_two[雪]")


@pytest.mark.parametrize("nodeid", ["", "/tmp/tests/test_x.py::test_x", "../tests/test_x.py::test_x", "tests/../test_x.py::test_x"])
def test_partition_refuses_unsafe_or_empty_node_ids(core, nodeid):
    with pytest.raises(ValueError):
        core.partition(nodeid)


def test_complete_union_preserves_existing_setup_and_call_skips(core, receipts):
    root, expected, _, nodes = receipts
    result = core.verify(root, expected, "success")
    assert result["selected"] == len(nodes)
    assert result["passed"] == len(nodes) - 2
    assert result["skipped"] == 2


@pytest.mark.parametrize("workers_result", ["failure", "cancelled", "skipped", "pending", ""])
def test_native_worker_failure_blocks_even_complete_receipts(core, receipts, workers_result):
    root, expected, _, _ = receipts
    with pytest.raises(ValueError):
        core.verify(root, expected, workers_result)


@pytest.mark.parametrize("field,value", [
    ("repository", "example/other"), ("commit", "e" * 40), ("tree", "f" * 40),
    ("run_id", "123455"), ("attempt", "2"), ("python_version", "3.13"),
    ("worktrunk_version", "0.80.0"),
    ("authority", {"tests/ci_shard.py": "0" * 64, ".github/workflows/test.yml": "d" * 64}),
])
def test_stale_or_wrong_lane_identity_refuses(core, receipts, field, value):
    root, expected, manifests, _ = receipts
    manifests[0]["identity"][field] = value
    write_manifest(root, expected, manifests[0])
    with pytest.raises(ValueError):
        core.verify(root, expected, "success")


@pytest.mark.parametrize("change", ["missing_worker", "extra_worker", "extra_file", "malformed_json", "duplicate_json_key", "manifest_link", "junit_link"])
def test_incomplete_or_unsafe_artifact_set_refuses(core, receipts, tmp_path, change):
    root, expected, _, _ = receipts
    directory = artifact(root, expected, 0)
    if change == "missing_worker":
        (directory / "manifest.json").unlink()
    elif change == "extra_worker":
        (root / "pytest-3.14-0.81.0-4").mkdir()
    elif change == "extra_file":
        (directory / "unexplained.json").write_text("{}")
    elif change == "malformed_json":
        (directory / "manifest.json").write_text("{broken")
    elif change == "duplicate_json_key":
        path = directory / "manifest.json"
        path.write_text(path.read_text().replace('"schema_version": 1', '"schema_version": 0, "schema_version": 1'))
    else:
        path = directory / ("manifest.json" if change == "manifest_link" else "junit.xml")
        outside = tmp_path.parent / (tmp_path.name + "-retained-preimage")
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
    with pytest.raises(ValueError):
        core.verify(root, expected, "success")


@pytest.mark.parametrize("field,value", [
    ("schema_version", 2), ("schema_version", True), ("shard", True),
    ("collection_complete", False), ("collection_complete", 1),
    ("exit_code", 1), ("exit_code", True), ("python_full", "3.13.16"),
    ("python_full", "3.14.11"),
    ("unrecognized", "ignored fields must not qualify"),
])
def test_receipt_requires_exact_schema_and_terminal_success(core, receipts, field, value):
    root, expected, manifests, _ = receipts
    manifests[0][field] = value
    # Keep the artifact's trusted name unchanged even when its claimed shard changes.
    (artifact(root, expected, 0) / "manifest.json").write_text(json.dumps(manifests[0]))
    with pytest.raises(ValueError):
        core.verify(root, expected, "success")


@pytest.mark.parametrize("change", ["different_universe", "duplicate_collected", "duplicate_selected", "omitted_execution", "duplicate_phase", "failed_setup", "failed_teardown", "missing_teardown", "foreign_report"])
def test_population_and_observed_phase_corruption_refuses(core, receipts, change):
    root, expected, manifests, nodes = receipts
    manifest = manifests[1]
    if change == "different_universe":
        manifest["collected"] = manifest["collected"][:-1]
    elif change == "duplicate_collected":
        manifest["collected"].append(nodes[0])
    elif change == "duplicate_selected":
        manifest["selected"].append(manifest["selected"][0])
    elif change == "omitted_execution":
        omitted = manifest["selected"][0]
        manifest["reports"] = [report for report in manifest["reports"] if report["nodeid"] != omitted]
    elif change == "duplicate_phase":
        manifest["reports"].append(copy.deepcopy(manifest["reports"][0]))
    elif change in {"failed_setup", "failed_teardown"}:
        when = change.removeprefix("failed_")
        next(report for report in manifest["reports"] if report["when"] == when)["outcome"] = "failed"
    elif change == "missing_teardown":
        manifest["reports"].pop()
    else:
        manifest["reports"].append({"nodeid": nodes[0], "when": "call", "outcome": "passed"})
    write_manifest(root, expected, manifest)
    with pytest.raises(ValueError):
        core.verify(root, expected, "success")


def test_complete_union_cannot_launder_wrong_partition_assignment(core, receipts):
    root, expected, manifests, _ = receipts
    source, destination = manifests[0], manifests[1]
    moved = source["selected"].pop()
    destination["selected"].append(moved)
    moved_reports = [report for report in source["reports"] if report["nodeid"] == moved]
    source["reports"] = [report for report in source["reports"] if report["nodeid"] != moved]
    destination["reports"].extend(moved_reports)
    for manifest in (source, destination):
        write_manifest(root, expected, manifest)
        write_junit(root, expected, manifest)
    with pytest.raises(ValueError):
        core.verify(root, expected, "success")


@pytest.mark.parametrize("change", ["failure", "error", "missing_id", "duplicate_id", "wrong_id", "lost_skip", "invented_skip", "invalid_xml"])
def test_junit_must_match_exact_attempts_and_skips(core, receipts, change):
    root, expected, _, _ = receipts
    path = artifact(root, expected, 1) / "junit.xml"
    document = ET.parse(path)
    case = document.find(".//testcase")
    assert case is not None, "Synthetic JUnit must contain a testcase to corrupt"
    properties = case.find("properties")
    assert properties is not None, "Synthetic testcase must carry identity properties"
    prop = properties.find("property")
    assert prop is not None, "Synthetic testcase must carry its exact node ID"
    nodeid = prop.get("value")
    assert nodeid is not None, "Synthetic node ID property must have a value"
    if change in {"failure", "error"}:
        ET.SubElement(case, change, message="Real failure cannot be hidden by exit code")
    elif change == "missing_id":
        case.remove(properties)
    elif change == "duplicate_id":
        ET.SubElement(properties, "property", name="ci_nodeid", value=nodeid)
    elif change == "wrong_id":
        prop.set("value", "tests/test_foreign.py::test_unknown")
    elif change == "lost_skip":
        skipped = case.find("skipped")
        assert skipped is not None, "Synthetic skipped testcase must contain its skipped outcome"
        case.remove(skipped)
    elif change == "invented_skip":
        ET.SubElement(document.findall(".//testcase")[1], "skipped", message="Unobserved skip")
    else:
        path.write_text("<broken")
    if change != "invalid_xml":
        document.write(path, encoding="utf-8", xml_declaration=True)
    with pytest.raises(ValueError):
        core.verify(root, expected, "success")


def collection_skip_evidence(root, expected, manifests):
    """Create the same ordinary module-level skip each real worker would report."""
    nodeid = "tests/test_optional.py"
    for manifest in manifests:
        manifest["collection_reports"] = [{"nodeid": nodeid, "outcome": "skipped"}]
        write_manifest(root, expected, manifest)
        path = artifact(root, expected, manifest["shard"]) / "junit.xml"
        document = ET.parse(path)
        suite = document.find("testsuite")
        assert suite is not None, "Synthetic JUnit must contain its testsuite"
        tests = suite.get("tests")
        skipped = suite.get("skipped")
        assert tests is not None and tests.isdecimal(), "Synthetic suite must contain a numeric test count"
        assert skipped is not None and skipped.isdecimal(), "Synthetic suite must contain a numeric skip count"
        suite.set("tests", str(int(tests) + 1))
        suite.set("skipped", str(int(skipped) + 1))
        case = ET.SubElement(suite, "testcase", classname="", name="tests.test_optional")
        ET.SubElement(case, "skipped", message="collection skipped")
        document.write(path, encoding="utf-8", xml_declaration=True)


def test_collection_skip_is_preserved_separately_from_executed_items(core, receipts):
    root, expected, manifests, nodes = receipts
    collection_skip_evidence(root, expected, manifests)
    assert core.verify(root, expected, "success") == {
        "selected": len(nodes), "passed": len(nodes) - 2, "skipped": 2, "collection_skipped": 1,
    }


@pytest.mark.parametrize("change", ["collector_mismatch", "missing_junit", "duplicate_junit", "wrong_message", "wrong_module", "collector_failure"])
def test_collection_skip_requires_matching_collector_and_junit_evidence(core, receipts, change):
    root, expected, manifests, _ = receipts
    collection_skip_evidence(root, expected, manifests)
    manifest = manifests[0]
    path = artifact(root, expected, 0) / "junit.xml"
    document = ET.parse(path)
    suite = document.find("testsuite")
    assert suite is not None, "Synthetic JUnit must contain its testsuite"
    case = suite.findall("testcase")[-1]
    if change == "collector_mismatch":
        manifest["collection_reports"] = []
    elif change == "missing_junit":
        suite.remove(case)
    elif change == "duplicate_junit":
        suite.append(copy.deepcopy(case))
    elif change == "wrong_message":
        skipped = case.find("skipped")
        assert skipped is not None, "Synthetic collection skip must contain its skipped outcome"
        skipped.set("message", "This is not a collection skip")
    elif change == "wrong_module":
        case.set("name", "tests.test_unobserved")
    else:
        manifest["collection_reports"][0]["outcome"] = "failed"
    write_manifest(root, expected, manifest)
    document.write(path, encoding="utf-8", xml_declaration=True)
    with pytest.raises(ValueError):
        core.verify(root, expected, "success")


@pytest.fixture
def native_checkout(tmp_path):
    """Real pytest, Git and installed Worktrunk; only the test population is synthetic."""
    binary = shutil.which("wt")
    if binary is None:
        pytest.skip("Native Worktrunk is unavailable")
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in {"PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH"}
    }
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    version = subprocess.run([binary, "--version"], env=environment, capture_output=True,
                             text=True, check=True, timeout=30).stdout.strip()
    assert version in {"wt v0.80.0", "wt v0.81.0"}, "Installed Worktrunk must match a declared CI lane"
    repository = tmp_path / "source"
    (repository / "tests").mkdir(parents=True)
    (repository / ".github/workflows").mkdir(parents=True)
    shutil.copyfile(ROOT / "tests/ci_shard.py", repository / "tests/ci_shard.py")
    shutil.copyfile(ROOT / ".github/workflows/test.yml", repository / ".github/workflows/test.yml")
    (repository / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    (repository / "tests/test_initiative_authority_amendment.py").write_text(
        'import pytest\n\n'
        'def test_pass():\n    assert 2 + 2 == 4\n\n'
        '@pytest.mark.skip(reason="Existing setup skip")\n'
        'def test_setup_skip():\n    raise AssertionError("must remain skipped")\n'
    )
    (repository / "tests/test_lineage_recovery.py").write_text(
        'import pytest\n\n'
        'def test_pass():\n    assert "native".upper() == "NATIVE"\n\n'
        'def test_call_skip():\n    pytest.skip("Existing call skip")\n\n'
        '@pytest.mark.xfail(strict=True, reason="Existing expected failure")\n'
        'def test_xfail():\n    assert False\n'
    )
    for index in range(8):
        (repository / f"tests/test_sample_{index}.py").write_text(
            f'def test_pass():\n    assert {index} == {index}\n'
        )
    (repository / "tests/test_optional_dependency.py").write_text(
        'import pytest\n'
        'pytest.importorskip("ci_shard_deliberately_absent_dependency_e763f9")\n'
    )

    def git(*arguments):
        return subprocess.run(["git", *arguments], cwd=repository, env=environment,
                              capture_output=True, text=True, check=True, timeout=30).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Synthetic CI")
    git("config", "user.email", "synthetic@example.invalid")
    git("config", "commit.gpgsign", "false")

    def commit():
        git("add", ".")
        git("commit", "-m", "Synthetic CI execution authority")
        return git("rev-parse", "HEAD")

    commit()
    output = tmp_path / "evidence"

    def invoke(mode, *, shard=None, workers_result=None):
        arguments = [
            sys.executable, str(repository / "tests/ci_shard.py"), mode,
            "--repository", "example/project", "--commit", git("rev-parse", "HEAD"),
            "--python-version", f"{sys.version_info.major}.{sys.version_info.minor}",
            "--worktrunk-version", version.removeprefix("wt v"),
            "--run-id", "987654", "--attempt", "1",
        ]
        if shard is None:
            target = output
        else:
            target = output / f"pytest-{sys.version_info.major}.{sys.version_info.minor}-{version.removeprefix('wt v')}-{shard}"
            arguments += ["--shard", str(shard)]
        arguments += ["--output", str(target)]
        if workers_result is not None:
            arguments += ["--workers-result", workers_result]
        completed = subprocess.run(arguments, cwd=repository, env=environment,
                                   capture_output=True, text=True, timeout=45)
        return completed, target

    return repository, commit, invoke, output


def test_native_execution_all_partitions_and_cli_verification(native_checkout):
    repository, _, invoke, _ = native_checkout
    populations = []
    attempted = []
    for shard in range(4):
        result, output = invoke("run", shard=shard)
        assert result.returncode == 0, result.stdout + result.stderr
        receipt = json.loads((output / "manifest.json").read_text())
        assert receipt["collection_complete"] is True and receipt["exit_code"] == result.returncode
        assert receipt["identity"]["python_version"] == f"{sys.version_info.major}.{sys.version_info.minor}"
        assert receipt["python_full"] == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        populations.append(receipt["collected"])
        attempted.extend(receipt["selected"])
    assert all(population == populations[0] for population in populations)
    assert len(attempted) == len(set(attempted)) == 13
    assert set(attempted) == set(populations[0])
    verified, _ = invoke("verify", workers_result="success")
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert json.loads(verified.stdout) == {
        "selected": 13, "passed": 10, "skipped": 3, "collection_skipped": 1,
    }
    assert (repository / "tests/test_lineage_recovery.py").is_file()


@pytest.mark.parametrize("failure", ["assertion", "collection"])
def test_native_test_or_collection_failure_never_qualifies(native_checkout, failure):
    repository, commit, invoke, _ = native_checkout
    target = repository / "tests/test_initiative_authority_amendment.py"
    target.write_text('def test_failure():\n    assert False\n' if failure == "assertion" else 'def test_broken(\n')
    commit()
    results = []
    for shard in range(4):
        result, output = invoke("run", shard=shard)
        results.append(result.returncode)
        receipt = json.loads((output / "manifest.json").read_text())
        assert receipt["exit_code"] == result.returncode
    assert results[0] != 0
    # Even an incorrect provider-success claim cannot launder actual red receipts.
    verified, _ = invoke("verify", workers_result="success")
    assert verified.returncode != 0


@pytest.mark.parametrize("selection", ['-k test_pass', '--ignore=tests/test_sample_0.py'])
def test_native_common_config_filter_is_rejected(native_checkout, selection):
    repository, commit, invoke, _ = native_checkout
    (repository / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n' + f'addopts = "{selection}"\n'
    )
    commit()
    result, output = invoke("run", shard=0)
    assert result.returncode != 0
    receipt = json.loads((output / "manifest.json").read_text())
    assert receipt["exit_code"] == result.returncode and receipt["collection_complete"] is False
    assert "must not select or exclude tests" in result.stdout + result.stderr


def test_native_collection_hook_cannot_remove_common_population(native_checkout):
    repository, commit, invoke, _ = native_checkout
    (repository / "tests/conftest.py").write_text(
        'def pytest_collection_modifyitems(items):\n    items.pop()\n'
    )
    commit()
    result, output = invoke("run", shard=0)
    assert result.returncode != 0
    receipt = json.loads((output / "manifest.json").read_text())
    assert receipt["exit_code"] == result.returncode and receipt["collection_complete"] is False
    assert "filtered or rewritten" in result.stdout + result.stderr


def test_native_ignore_hook_cannot_remove_module_before_item_collection(native_checkout):
    repository, commit, invoke, _ = native_checkout
    (repository / "tests/conftest.py").write_text(
        'def pytest_ignore_collect(collection_path, config):\n'
        '    return collection_path.name == "test_sample_0.py"\n'
    )
    commit()
    result, output = invoke("run", shard=0)
    assert result.returncode != 0
    receipt = json.loads((output / "manifest.json").read_text())
    assert receipt["exit_code"] == result.returncode and receipt["collection_complete"] is False


def test_native_zero_exit_with_partial_execution_is_rejected(native_checkout):
    repository, commit, invoke, _ = native_checkout
    (repository / "tests/conftest.py").write_text(
        'import pytest\n\n'
        '@pytest.hookimpl(tryfirst=True)\n'
        'def pytest_runtestloop(session):\n'
        '    for item in session.items[:1]:\n'
        '        item.ihook.pytest_runtest_protocol(item=item, nextitem=None)\n'
        '    pytest.exit("Synthetic incomplete execution", returncode=0)\n'
    )
    commit()
    for shard in range(4):
        result, output = invoke("run", shard=shard)
        assert result.returncode == 0, result.stdout + result.stderr
        receipt = json.loads((output / "manifest.json").read_text())
        assert receipt["collection_complete"] is True and receipt["exit_code"] == 0
        if shard == 0:
            assert len(receipt["selected"]) == 2
            assert len({report["nodeid"] for report in receipt["reports"]}) == 1
    verified, _ = invoke("verify", workers_result="success")
    assert verified.returncode != 0
