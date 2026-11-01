"""Complete conditional Python stack guidance, provenance and isolated delivery."""

import hashlib
import json
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

from test_opencode_control_plane import DATA, ROOT
from test_python_audit import BUNDLES
from test_python_specialists import inventory, markdown_destinations, portable_path

SKILLS = ROOT / "dot_agents/skills"
SOURCES = SKILLS / "dbsctr/references/python-expansion-sources"
NAMES = {"pydantic", "polars", "typer", "fastapi", "atheris", "secure-python-release-pipeline", "port-to-free-threaded-python"}


def digest(body):
    return hashlib.sha256(body).hexdigest()


def packages():
    fragments = sorted(SOURCES.glob("*/sources.lock.json"))
    assert {p.parent.name for p in fragments} == {"frameworks", "data-testing", "runtime"}
    result = []
    for fragment in fragments:
        lock = json.loads(fragment.read_text())
        assert lock["schema_version"] == 1
        result.extend((fragment.parent, p) for p in lock["packages"])
    assert len(result) == len(NAMES) and {p["name"] for _, p in result} == NAMES
    return result


def test_complete_stack_bundles_reconstruct_original_bytes_and_identity(tmp_path):
    for owner, p in packages():
        assert p["state"] == "vendored"
        assert p["license"] == ("CC-BY-SA-4.0" if p["name"] == "atheris" else "Apache-2.0" if p["name"] in {"secure-python-release-pipeline", "port-to-free-threaded-python"} else "MIT")
        assert len(p["commit"]) == 40 and int(p["commit"], 16)
        originals = p["upstream_files"]
        assert {"SKILL.md", "LICENSE.upstream"} <= originals.keys()
        assert originals.keys() == p["git_blobs"].keys() == p["upstream_modes"].keys() == p["upstream_paths"].keys()
        assert originals.keys() <= p["files"].keys()
        assert p["files"].keys() == p["modes"].keys() == p["installed_modes"].keys()
        assert inventory(SKILLS / p["name"]) == p["files"]
        for path in p["upstream_paths"].values():
            portable_path(path)
        target = tmp_path / p["name"]
        shutil.copytree(SKILLS / p["name"], target)
        patches = []
        for relative, expected in p["patches"].items():
            patch = owner / portable_path(relative)
            assert digest(patch.read_bytes()) == expected
            patches.append(patch)
        for patch in reversed(patches):
            subprocess.run(["patch", "--batch", "--fuzz=0", "-R", "-p1", "-i", str(patch)], cwd=target, check=True, capture_output=True)
        for relative, expected in originals.items():
            body = (target / portable_path(relative)).read_bytes()
            assert digest(body) == expected
            assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == p["git_blobs"][relative]
        for patch in patches:
            subprocess.run(["patch", "--batch", "--fuzz=0", "--forward", "-p1", "-i", str(patch)], cwd=target, check=True, capture_output=True)
        assert inventory(target) == p["files"]


def test_stack_guidance_has_explicit_conditional_owners():
    module = (SKILLS / "dbsctr/modules/python.md").read_text()
    data = (SKILLS / "dbsctr/modules/data.md").read_text()
    methods = (SKILLS / "dbsctr/references/python-stack-specialists.md").read_text()
    audit = (SKILLS / "python-audit/SKILL.md").read_text()
    assessment = (SKILLS / "python-audit/references/stack-specialists.md").read_text()
    for name in NAMES:
        assert f"`{name}`" in module and name in methods and name in assessment
        assert (SKILLS / name / "agents/openai.yaml").is_file()
    assert "`polars`" in data and "references/stack-specialists.md" in audit


def test_stack_projection_is_complete_bounded_and_idempotent(tmp_path):
    destination = tmp_path / "destination"
    live = destination / ".agents/skills"
    sentinel = live / "unrelated/local.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("Preserve local state.\n")
    names = BUNDLES | NAMES | {"dbsctr"}
    targets = [live / name for name in sorted(names)]
    command = ["chezmoi", "-S", str(ROOT), "-D", str(destination), "--config", "/dev/null", "--config-format", "toml", "--override-data", json.dumps(DATA), "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"), "--exclude", "scripts"]
    for _ in range(2):
        subprocess.run([*command, "apply", "--parent-dirs", *map(str, targets)], check=True, capture_output=True)
        for name in names:
            assert inventory(live / name) == inventory(SKILLS / name), name
        assert sentinel.read_text() == "Preserve local state.\n"
    for name in NAMES | {"python-audit"}:
        for document in (live / name).rglob("*.md"):
            for link in markdown_destinations(document.read_text()):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (document.parent / unquote(parsed.path)).resolve()
                assert target.is_relative_to(live) and target.exists(), (document, link)
    for _, package in packages():
        for relative, mode in package["installed_modes"].items():
            assert bool((live / package["name"] / relative).stat().st_mode & 0o111) == (mode == "100755")
    assert subprocess.run([*command, "diff", "--recursive", *map(str, targets)], check=True, capture_output=True).stdout == b""
    expected = {sentinel.relative_to(destination)}
    for target in targets:
        expected.update(p.relative_to(destination) for p in target.rglob("*") if p.is_file())
    assert {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()} == expected
