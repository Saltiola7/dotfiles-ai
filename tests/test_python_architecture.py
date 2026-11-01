"""Architecture guidance provenance, mode resources and portable composition."""

import hashlib
import json
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

from test_opencode_control_plane import DATA, ROOT
from test_python_specialists import assert_bundles, digest, inventory, markdown_destinations, portable_path
from test_python_audit import BUNDLES

SKILLS = ROOT / "dot_agents/skills"
SOURCES = SKILLS / "dbsctr/references/architecture-sources"
VENDORED = {"architecture-patterns", "python-project-structure"}
ARCHITECTURE = VENDORED | {"python-architecture-fitness"}


def packages():
    lock = json.loads((SOURCES / "sources.lock.json").read_text())
    assert lock["schema_version"] == 1
    assert {p["name"] for p in lock["packages"]} == VENDORED
    return lock["packages"]


def test_complete_architecture_bundles_reconstruct_original_resources(tmp_path):
    for package in packages():
        assert package["state"] == "vendored" and package["license"] == "MIT"
        assert len(package["commit"]) == 40 and int(package["commit"], 16)
        assert {"SKILL.md", "LICENSE.upstream"} <= package["upstream_files"].keys()
        assert package["upstream_files"].keys() == package["git_blobs"].keys()
        assert package["upstream_files"].keys() <= package["files"].keys()
        assert package["modes"].keys() == package["installed_modes"].keys() == package["files"].keys()
        assert_bundles(SKILLS, [package])
        target = tmp_path / package["name"]
        shutil.copytree(SKILLS / package["name"], target)
        patches = []
        for relative, expected in package["patches"].items():
            patch = SOURCES / portable_path(relative)
            assert digest(patch.read_bytes()) == expected
            patches.append(patch)
        for patch in reversed(patches):
            subprocess.run(["patch", "--batch", "--fuzz=0", "-R", "-p1", "-i", str(patch)], cwd=target, check=True, capture_output=True)
        for relative, expected in package["upstream_files"].items():
            body = (target / portable_path(relative)).read_bytes()
            assert digest(body) == expected
            assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == package["git_blobs"][relative]
        for patch in patches:
            subprocess.run(["patch", "--batch", "--fuzz=0", "--forward", "-p1", "-i", str(patch)], cwd=target, check=True, capture_output=True)
        assert_bundles(tmp_path, [package])


def test_architecture_mode_exposes_techniques_and_declared_evidence_contract():
    module = (SKILLS / "dbsctr/modules/python.md").read_text()
    methods = (SKILLS / "dbsctr/references/python-specialists.md").read_text()
    audit = (SKILLS / "python-audit/SKILL.md").read_text()
    focus = (SKILLS / "python-audit/references/architecture.md").read_text()
    report = (SKILLS / "python-audit/references/report.md").read_text()
    for name in ARCHITECTURE:
        assert f"`{name}`" in module and name in methods and name in audit
        assert (SKILLS / name / "agents/openai.yaml").is_file()
    for body in (audit, focus, report):
        assert "architecture" in body.lower()
    assert "references/architecture.md" in audit
    assert "architecture-sources/sources.lock.json" in methods
    assert "--architecture" not in audit  # Prompt scope is not an invented CLI.


def test_architecture_and_audit_projection_is_closed_bounded_and_idempotent(tmp_path):
    destination = tmp_path / "destination"
    live = destination / ".agents/skills"
    sentinel = live / "unrelated/local.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("Preserve local edits.\n")
    names = BUNDLES | ARCHITECTURE | {"dbsctr"}
    targets = [live / name for name in sorted(names)]
    command = ["chezmoi", "-S", str(ROOT), "-D", str(destination), "--config", "/dev/null", "--config-format", "toml",
               "--override-data", json.dumps(DATA), "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"), "--exclude", "scripts"]
    for _ in range(2):
        subprocess.run([*command, "apply", "--parent-dirs", *map(str, targets)], check=True, capture_output=True)
        for name in names:
            assert inventory(live / name) == inventory(SKILLS / name), name
        assert sentinel.read_text() == "Preserve local edits.\n"
    for name in ARCHITECTURE | {"python-audit"}:
        for document in (live / name).rglob("*.md"):
            for link in markdown_destinations(document.read_text()):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (document.parent / unquote(parsed.path)).resolve()
                assert target.is_relative_to(live) and target.exists(), (document, link)
    for package in packages():
        for relative, mode in package["installed_modes"].items():
            assert bool((live / package["name"] / relative).stat().st_mode & 0o111) == (mode == "100755")
    assert subprocess.run([*command, "diff", "--recursive", *map(str, targets)], check=True, capture_output=True).stdout == b""
    expected = {sentinel.relative_to(destination)}
    for target in targets:
        expected.update(p.relative_to(destination) for p in target.rglob("*") if p.is_file())
    assert {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()} == expected
