"""Offline provenance, resource closure, and bounded Python skill delivery."""

import hashlib
import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import pytest

from test_opencode_control_plane import DATA, ROOT


SKILLS = ROOT / "dot_agents/skills"
INVENTORY = SKILLS / "dbsctr/references/python-specialists"
LOCK = INVENTORY / "sources.lock.json"
NAMES = {
    "modern-python",
    "python-design-patterns",
    "python-performance-optimization",
    "property-based-testing",
}
DBSCTR_FILES = (
    "dbsctr/modules/python.md",
    "dbsctr/references/python-specialists.md",
    "dbsctr/references/specialist-selection.md",
    "dbsctr/scripts/resolve_specialist.py",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    assert root.is_dir() and not root.is_symlink(), f"missing or linked bundle: {root}"
    result = {}
    for path in root.rglob("*"):
        assert not path.is_symlink(), f"linked resource: {path}"
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
        else:
            assert path.is_dir(), f"unsupported resource: {path}"
    return result


def portable_path(value):
    path = PurePosixPath(value)
    assert value and not path.is_absolute() and ".." not in path.parts
    assert str(path) == value
    return path


def read_lock():
    lock = json.loads(LOCK.read_text())
    assert lock["schema_version"] == 1
    packages = lock["packages"]
    assert len(packages) == len(NAMES)
    assert {package["name"] for package in packages} == NAMES
    return packages


def assert_bundles(skills_root, packages):
    for package in packages:
        assert inventory(skills_root / package["name"]) == package["files"], package["name"]


def copy_selected(skills_root):
    for name in NAMES:
        shutil.copytree(SKILLS / name, skills_root / name)
    for relative in DBSCTR_FILES:
        target = skills_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILLS / relative, target)
    shutil.copytree(INVENTORY, skills_root / "dbsctr/references/python-specialists")


def test_complete_bundles_have_immutable_source_identity_and_attribution():
    packages = read_lock()
    for package in packages:
        assert package["state"] == "vendored"
        assert re.fullmatch(r"[0-9a-f]{40}", package["commit"])
        assert package["upstream_url"].startswith("https://github.com/")
        portable_path(package["upstream_path"])
        assert package["license"] in {"MIT", "CC-BY-SA-4.0"}
        assert package["changes"].strip()
        assert {"SKILL.md", "LICENSE.upstream"} <= package["upstream_files"].keys()
        assert package["upstream_files"].keys() == package["git_blobs"].keys()
        assert package["upstream_files"].keys() <= package["files"].keys()
        assert "UPSTREAM.md" in package["files"]
        for field, width in (("upstream_files", 64), ("files", 64), ("git_blobs", 40), ("patches", 64)):
            for relative, value in package[field].items():
                portable_path(relative)
                assert re.fullmatch(rf"[0-9a-f]{{{width}}}", value)
        upstream = (SKILLS / package["name"] / "UPSTREAM.md").read_text()
        assert package["commit"] in upstream
        assert package["upstream_url"] in upstream
    assert_bundles(SKILLS, packages)


def test_selected_typing_migration_preserves_diagnostics_and_full_scope():
    source = (SKILLS / "modern-python/references/migration-checklist.md").read_text()
    for block in re.findall(r"```toml\n(.*?)```", source, flags=re.DOTALL):
        rules = tomllib.loads(block).get("tool", {}).get("ty", {}).get("rules", {})
        assert "ignore" not in rules.values(), "migration must not disable diagnostic classes"
    normalized = " ".join(source.split())
    for contract in (
        "independent inventory", "conflict census", "actual exit status",
        "required typing gate", "Narrow suppressions",
    ):
        assert contract in normalized
    assert not re.search(r"ty check[^\n]*\|\s*grep", source)


@pytest.mark.parametrize("mutation", ["missing", "changed", "extra", "linked"])
def test_complete_inventory_detects_resource_drift(tmp_path, mutation):
    package = read_lock()[0]
    target = tmp_path / package["name"]
    shutil.copytree(SKILLS / package["name"], target)
    assert_bundles(tmp_path, [package])
    relative = next(path for path in package["files"] if "/" in path)
    resource = target / relative
    if mutation == "missing":
        resource.unlink()
    elif mutation == "changed":
        resource.write_bytes(resource.read_bytes() + b"\nchanged\n")
    elif mutation == "extra":
        (target / "unrecorded-resource.md").write_text("unexpected")
    else:
        resource.unlink()
        resource.symlink_to(SKILLS / package["name"] / relative)
    with pytest.raises(AssertionError):
        assert_bundles(tmp_path, [package])


def test_local_adaptations_round_trip_to_original_git_blobs(tmp_path):
    for package in read_lock():
        target = tmp_path / package["name"]
        shutil.copytree(SKILLS / package["name"], target)
        patches = []
        for relative, expected in package["patches"].items():
            patch = INVENTORY / relative
            assert digest(patch.read_bytes()) == expected
            patches.append(patch)
        for patch in reversed(patches):
            subprocess.run(["patch", "--batch", "--fuzz=0", "-R", "-p1", "-i", str(patch)],
                           cwd=target, check=True, capture_output=True)
        for relative, expected in package["upstream_files"].items():
            data = (target / relative).read_bytes()
            assert digest(data) == expected, f"upstream bytes: {package['name']}/{relative}"
            git_object = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            assert hashlib.sha1(git_object).hexdigest() == package["git_blobs"][relative]
        for patch in patches:
            subprocess.run(["patch", "--batch", "--fuzz=0", "--forward", "-p1", "-i", str(patch)],
                           cwd=target, check=True, capture_output=True)
        assert_bundles(tmp_path, [package])


def markdown_destinations(body):
    lines = []
    fence = None
    for line in body.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        if fence is None:
            lines.append(line)
    prose = re.sub(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", "", "\n".join(lines), flags=re.DOTALL)
    inline = r"\[[^\]\n]*\]\(\s*(?:<([^>]+)>|([^\s)]+))"
    definition = r"^ {0,3}\[[^\]\n]+\]:\s*(?:<([^>]+)>|([^\s]+))"
    for match in re.finditer(f"(?:{inline})|(?:{definition})", prose, re.MULTILINE):
        yield next(value for value in match.groups() if value is not None)


def test_resource_link_scanner_distinguishes_inline_code_from_links():
    body = '''[`actual label`](actual.md)
`rebind[TargetType](value)`
``code with `inner` and [not a link](example)``
```python
[also code](missing.py)
```
[reference]: reference.md
'''
    assert list(markdown_destinations(body)) == ["actual.md", "reference.md"]


def test_local_resource_links_resolve_with_only_selected_bundles(tmp_path):
    copy_selected(tmp_path)
    documents = [path for name in NAMES for path in (tmp_path / name).rglob("*.md")]
    documents.extend(tmp_path / relative for relative in DBSCTR_FILES)
    for document in documents:
        for destination in markdown_destinations(document.read_text()):
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to(tmp_path), f"nonportable link: {document}: {destination}"
            assert target.exists(), f"missing resource: {document}: {destination}"


def test_python_module_exposes_specialist_routes_and_separate_reference():
    module = (SKILLS / "dbsctr/modules/python.md").read_text()
    guide = (SKILLS / "dbsctr/references/python-specialists.md").read_text()
    assert "references/python-specialists.md" in module
    assert "references/python.md" in module
    for name in NAMES:
        assert f"`{name}`" in module
        assert not any(f"`{name}`" in line for line in guide.splitlines() if line.startswith("|"))
    assert "../modules/python.md#conditional-controls" in guide
    assert "references/specialist-selection.md" in module
    assert "python-specialists/sources.lock.json" in guide


def test_exact_target_delivery_preserves_unrelated_state_and_is_idempotent(tmp_path):
    packages = read_lock()
    destination = tmp_path / "destination"
    skill_root = destination / ".agents/skills"
    unrelated = skill_root / "unrelated/local.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("Keep this local skill unchanged.\n")
    targets = [skill_root / name for name in sorted(NAMES)]
    targets.extend(skill_root / relative for relative in DBSCTR_FILES)
    targets.append(skill_root / "dbsctr/references/python-specialists")
    base = ["chezmoi", "-S", str(ROOT), "-D", str(destination), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(DATA),
            "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"),
            "--exclude", "scripts"]
    for _ in range(2):
        subprocess.run([*base, "apply", "--parent-dirs", *map(str, targets)],
                       check=True, capture_output=True)
        assert_bundles(skill_root, packages)
        for relative in DBSCTR_FILES:
            assert (skill_root / relative).read_bytes() == (SKILLS / relative).read_bytes()
        assert inventory(skill_root / "dbsctr/references/python-specialists") == inventory(INVENTORY)
        assert unrelated.read_text() == "Keep this local skill unchanged.\n"
    expected = {Path(".agents/skills/unrelated/local.md")}
    for target in targets:
        if target.is_file():
            expected.add(target.relative_to(destination))
        else:
            expected.update(path.relative_to(destination) for path in target.rglob("*") if path.is_file())
    assert {path.relative_to(destination) for path in destination.rglob("*") if path.is_file()} == expected
    result = subprocess.run([*base, "diff", "--recursive", *map(str, targets)],
                            check=True, capture_output=True)
    assert result.stdout == b""
