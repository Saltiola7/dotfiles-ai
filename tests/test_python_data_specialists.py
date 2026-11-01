"""Pinned Python/data guidance, closed composition and bounded projection."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

from test_opencode_control_plane import DATA, ROOT
from test_python_specialists import NAMES, assert_bundles, digest, inventory, markdown_destinations, portable_path


SKILLS = ROOT / "dot_agents/skills"
SOURCES = SKILLS / "dbsctr/references/python-data-sources"
PYTHON = {"python-testing-patterns", "python-type-safety", "python-resilience",
          "python-resource-management", "python-observability"}
ENGINES = {"duckdb-query", "duckdb-read-file", "duckdb-attach-db", "duckdb-docs",
           "clickhouse-best-practices", "clickhouse-architecture-advisor"}
DATABRICKS = {"databricks-core", "databricks-pipelines", "databricks-jobs", "databricks-dabs",
              "databricks-unity-catalog", "databricks-dbsql", "databricks-python-sdk",
              "databricks-spark-structured-streaming"}
AUTHORED = {"python-database-boundaries", "database-audit"}
SHARED = ("dbsctr/modules/python.md", "dbsctr/modules/data.md",
          "dbsctr/references/python-specialists.md", "dbsctr/references/database-specialists.md",
          "python-audit/SKILL.md", "python-audit/references/report.md", "python-audit/agents/openai.yaml")


def packages():
    result = []
    for group, names in (("python", PYTHON), ("engines", ENGINES), ("databricks", DATABRICKS)):
        root = SOURCES / group
        lock = json.loads((root / "sources.lock.json").read_text())
        assert lock["schema_version"] == 1
        assert {p["name"] for p in lock["packages"]} == names
        result.extend((root, package) for package in lock["packages"])
    return result


def test_selected_complete_bundles_have_immutable_resources_and_licenses():
    for _, package in packages():
        assert package["state"] == "vendored"
        assert len(package["commit"]) == 40 and int(package["commit"], 16)
        assert package["upstream_url"].startswith("https://github.com/")
        portable_path(package["upstream_path"])
        assert {"SKILL.md", "LICENSE.upstream"} <= package["upstream_files"].keys()
        assert package["upstream_files"].keys() == package["git_blobs"].keys()
        assert package["upstream_files"].keys() <= package["files"].keys()
        assert {"UPSTREAM.md", "agents/openai.yaml"} <= package["files"].keys()
        assert package["modes"].keys() == package["installed_modes"].keys() == package["files"].keys()
        assert set(package["modes"].values()) <= {"100644", "100755"}
        assert set(package["installed_modes"].values()) <= {"100644", "100755"}
        attribution = (SKILLS / package["name"] / "UPSTREAM.md").read_text()
        assert package["commit"] in attribution and package["upstream_url"] in attribution
        assert package["changes"].strip() and package["license"].strip()
        for relative, mode in package["modes"].items():
            path = SKILLS / package["name"] / portable_path(relative)
            assert bool(path.stat().st_mode & 0o111) == (mode == "100755"), path
        if package["license"] in {"Apache-2.0", "LicenseRef-Databricks"}:
            for relative, original in package["upstream_files"].items():
                if package["files"][relative] != original:
                    modified = (SKILLS / package["name"] / relative).read_text()
                    assert "modified by dotfiles-ai" in modified.lower(), (package["name"], relative)
        assert_bundles(SKILLS, [package])


def test_reviewed_adaptations_round_trip_original_blobs(tmp_path):
    for provenance, package in packages():
        destination = tmp_path / package["name"]
        shutil.copytree(SKILLS / package["name"], destination)
        patches = []
        for relative, expected in package["patches"].items():
            patch = provenance / portable_path(relative)
            assert digest(patch.read_bytes()) == expected
            patches.append(patch)
        for patch in reversed(patches):
            subprocess.run(["patch", "--batch", "--fuzz=0", "-R", "-p1", "-i", str(patch)],
                           cwd=destination, check=True, capture_output=True)
        for relative, expected in package["upstream_files"].items():
            body = (destination / portable_path(relative)).read_bytes()
            assert digest(body) == expected, (package["name"], relative)
            assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == package["git_blobs"][relative]
        for patch in patches:
            subprocess.run(["patch", "--batch", "--fuzz=0", "--forward", "-p1", "-i", str(patch)],
                           cwd=destination, check=True, capture_output=True)
        assert_bundles(tmp_path, [package])


def test_layered_routes_and_audit_dependencies_are_available():
    python = (SKILLS / "dbsctr/modules/python.md").read_text()
    guide = (SKILLS / "dbsctr/references/python-specialists.md").read_text()
    audit = (SKILLS / "python-audit/SKILL.md").read_text()
    data = (SKILLS / "dbsctr/modules/data.md").read_text()
    engines = (SKILLS / "dbsctr/references/database-specialists.md").read_text()
    for name in PYTHON | {"python-database-boundaries"}:
        assert f"`{name}`" in python
        assert name in guide and name in audit
    assert "database-specialists.md" in data
    for name in ENGINES | DATABRICKS | AUTHORED:
        assert name in engines
    for name in AUTHORED:
        body = (SKILLS / name / "SKILL.md").read_text()
        assert f"name: {name}\n" in body
        assert (SKILLS / name / "agents/openai.yaml").is_file()
    for relative in SHARED:
        assert (SKILLS / relative).is_file()


def test_complete_skill_tree_has_closed_resources_and_exact_projection(tmp_path):
    # Use the complete declared skill population: cross-layer audit links must
    # work in a clean projection, without plugin caches or undeclared host files.
    destination = tmp_path / "destination"
    live = destination / ".agents/skills"
    sentinel = live / "unrelated/keep.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("Preserve independent local edits.\n")
    command = ["chezmoi", "-S", str(ROOT), "-D", str(destination), "--config", "/dev/null",
               "--config-format", "toml", "--override-data", json.dumps(DATA),
               "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"),
               "--exclude", "scripts"]
    names = PYTHON | ENGINES | DATABRICKS | AUTHORED | NAMES | {"python-process-parallelism", "python-data-contracts", "python-arrow-interchange", "python-mutation-testing", "python-durable-jobs",
        "python-audit", "dbsctr", "qa", "async-python-patterns", "python-modernization-review",
        "architecture-patterns", "python-project-structure", "python-architecture-fitness",
        "pydantic", "polars", "typer", "fastapi", "atheris", "secure-python-release-pipeline", "port-to-free-threaded-python"}
    targets = [live / name for name in sorted(names)]
    for _ in range(2):
        subprocess.run([*command, "apply", "--parent-dirs", *map(str, targets)], check=True, capture_output=True)
        for name in names:
            # Chezmoi's executable_ source prefix maps to executable target names.
            expected = {str(Path(*[part.removeprefix("executable_") for part in Path(p).parts])): h
                        for p, h in inventory(SKILLS / name).items()}
            assert inventory(live / name) == expected, name
        assert sentinel.read_text() == "Preserve independent local edits.\n"
    for _, package in packages():
        for name, mode in package["installed_modes"].items():
            rendered = Path(*[part.removeprefix("executable_") for part in Path(name).parts])
            assert bool((live / package["name"] / rendered).stat().st_mode & 0o111) == (mode == "100755")
    for name in PYTHON | ENGINES | DATABRICKS | AUTHORED | {"python-audit"}:
        for document in (live / name).rglob("*.md"):
            for link in markdown_destinations(document.read_text()):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (document.parent / unquote(parsed.path)).resolve()
                assert target.is_relative_to(live), (document, link)
                assert target.exists(), (document, link)
    assert subprocess.run([*command, "diff", "--recursive", *map(str, targets)],
                          check=True, capture_output=True).stdout == b""
    expected_paths = {sentinel.relative_to(destination)}
    for target in targets:
        expected_paths.update(p.relative_to(destination) for p in target.rglob("*") if p.is_file())
    assert {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()} == expected_paths
