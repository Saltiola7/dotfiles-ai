"""Portable security toolkit integrity and isolated chezmoi delivery."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from test_opencode_control_plane import DATA, ROOT

SKILLS = ROOT / "dot_agents/skills"
TOOLKIT = SKILLS / "security-toolkit"
LOCK = TOOLKIT / "references/sources.lock.json"


def files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def verify(root):
    return subprocess.run([sys.executable, str(TOOLKIT / "scripts/verify_bundle.py"),
                           "--skills-root", str(root)], capture_output=True, text=True)


def test_source_inventory_is_pinned_and_matches_complete_bundles():
    lock = json.loads(LOCK.read_text())
    assert lock["schema_version"] == 1
    assert {p["name"] for p in lock["packages"]} == {
        "security-audit", "variant-analysis", "gha-security-review", "codeguard", "secret-serialization"}
    for package in lock["packages"]:
        assert package["state"] == "vendored"
        assert len(bytes.fromhex(package["commit"])) == 20
        assert len(bytes.fromhex(package["archive_sha256"])) == 32
        assert package["license"] and package["upstream_url"].startswith("https://github.com/")
        assert files(SKILLS / package["name"]) == package["files"]
        assert (SKILLS / package["name"] / "LICENSE.upstream").is_file()
        assert (SKILLS / package["name"] / "UPSTREAM.md").is_file()
    assert verify(SKILLS).returncode == 0
    for pending in lock["not_vendored"]:
        assert pending["reason"]
        assert pending["state"] != "vendored"


def test_integrity_check_refuses_changed_extra_and_symlinked_files(tmp_path):
    import shutil
    lock = json.loads(LOCK.read_text())
    for package in lock["packages"]:
        shutil.copytree(SKILLS / package["name"], tmp_path / package["name"])
    assert verify(tmp_path).returncode == 0
    target = tmp_path / "variant-analysis/SKILL.md"
    before = target.read_bytes()
    target.write_bytes(before + b"\nchanged\n")
    assert verify(tmp_path).returncode != 0
    target.write_bytes(before)
    extra = target.parent / "unexpected.txt"
    extra.write_text("extra")
    assert verify(tmp_path).returncode != 0
    extra.unlink()
    target.unlink()
    target.symlink_to(SKILLS / "variant-analysis/SKILL.md")
    assert verify(tmp_path).returncode != 0


def test_isolated_delivery_is_complete_and_idempotent(tmp_path):
    lock = json.loads(LOCK.read_text())
    names = [p["name"] for p in lock["packages"]] + ["security-toolkit"]
    targets = [str(tmp_path / ".agents/skills" / name) for name in names]
    base = ["chezmoi", "-S", str(ROOT), "-D", str(tmp_path), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(DATA),
            "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"),
            "--exclude", "scripts"]
    for _ in range(2):
        subprocess.run([*base, "apply", "--parent-dirs", *targets], check=True, capture_output=True)
        for name in names:
            assert files(tmp_path / ".agents/skills" / name) == files(SKILLS / name)
    assert subprocess.run([*base, "diff", "--recursive", *targets], check=True, capture_output=True).stdout == b""
    assert verify(tmp_path / ".agents/skills").returncode == 0


def test_local_patches_reconstruct_original_selected_files(tmp_path):
    import shutil
    lock = json.loads(LOCK.read_text())
    for package in lock["packages"]:
        target = tmp_path / package["name"]
        shutil.copytree(SKILLS / package["name"], target)
        for relative, digest in package["patches"].items():
            patch = TOOLKIT / relative
            assert hashlib.sha256(patch.read_bytes()).hexdigest() == digest
            subprocess.run(["patch", "--batch", "-R", "-p1", "-i", str(patch)],
                           cwd=target, check=True, capture_output=True)
        for relative in package["selected_files"]:
            assert hashlib.sha256((target / relative).read_bytes()).hexdigest() == package["upstream_files"][relative]


def load_local_tools():
    import importlib.util
    specification = importlib.util.spec_from_file_location("local_security_tools", TOOLKIT / "scripts/local_tools.py")
    module = importlib.util.module_from_spec(specification)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        specification.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def test_runtime_profile_disables_subscriptions_and_locks_dependencies():
    module = load_local_tools()
    profile = module.load_profile()
    assert all(not entry["enabled"] for entry in profile["subscription_integrations"].values())
    assert profile["osv_database"]["installed"] is False
    tool = next(t for t in profile["tools"] if t["name"] == "semgrep")
    assert hashlib.sha256((module.DATA / tool["requirements"]).read_bytes()).hexdigest() == tool["requirements_sha256"]
    assert {t["name"] for t in profile["tools"]} == {"semgrep", "gitleaks", "osv-scanner"}


def test_runtime_archive_rejects_links_and_traversal(tmp_path):
    import io
    import tarfile
    import pytest
    module = load_local_tools()
    for bad_name, link in [("../outside", False), ("linked", True)]:
        archive = tmp_path / "release.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            member = tarfile.TarInfo("gitleaks")
            member.size = 2
            bundle.addfile(member, io.BytesIO(b"ok"))
            bad = tarfile.TarInfo(bad_name)
            if link:
                bad.type = tarfile.SYMTYPE
                bad.linkname = "/outside"
            bundle.addfile(bad)
        with pytest.raises(ValueError, match="unsafe release archive"):
            module.check_archive(archive, "gitleaks")
    assert not (tmp_path.parent / "outside").exists()


def test_runtime_smoke_is_version_only_and_uses_empty_environment(tmp_path, monkeypatch):
    module = load_local_tools()
    calls = []
    monkeypatch.setenv("SEMGREP_APP_TOKEN", "synthetic-token-not-for-child")
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="1.182.1\n", stderr="")
    monkeypatch.setattr(module.subprocess, "run", run)
    module.smoke({"name": "semgrep", "kind": "python", "version": "1.182.1"}, tmp_path)
    argv, kwargs = calls[0]
    assert argv[1:] == ["--version", "--disable-version-check", "--metrics=off"]
    assert "SEMGREP_APP_TOKEN" not in kwargs["env"]
    assert kwargs["env"]["SEMGREP_SEND_METRICS"] == "off"
    assert kwargs["env"]["HOME"] != str(Path.home())
    assert kwargs["cwd"] == kwargs["env"]["HOME"]


def test_runtime_existing_incomplete_generation_is_preserved(tmp_path):
    import pytest
    module = load_local_tools()
    tool = next(t for t in module.load_profile()["tools"] if t["name"] == "gitleaks")
    generation = module.generation_for(tool, tmp_path)
    generation.mkdir(parents=True)
    original = generation / "user-content"
    original.write_text("preserve")
    with pytest.raises(ValueError, match="incomplete generation"):
        module.install(tool, tmp_path, tmp_path / "downloads")
    assert original.read_text() == "preserve"


def test_runtime_refuses_linked_ancestor_and_cached_release(tmp_path):
    import pytest
    module = load_local_tools()
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="unsafe runtime directory"):
        module.real_directory(linked / "child")
    assert not (outside / "child").exists()
    tool = next(t for t in module.load_profile()["tools"] if t["name"] == "gitleaks")
    cache = tmp_path / "cache"
    cache.mkdir()
    original = tmp_path / "original"
    original.write_bytes(b"fixture")
    (cache / tool["asset"]["name"]).symlink_to(original)
    with pytest.raises(ValueError, match="unsafe runtime file"):
        module.install(tool, tmp_path / "runtime", cache)


def test_runtime_complete_inventory_prevents_changed_core_execution(tmp_path, monkeypatch):
    import pytest
    module = load_local_tools()
    tool = next(t for t in module.load_profile()["tools"] if t["name"] == "semgrep")
    generation = module.generation_for(tool, tmp_path)
    executable = module.binary_path(tool, generation)
    executable.parent.mkdir(parents=True)
    executable.write_text("fixture entrypoint")
    core = generation / "venv/semgrep-core"
    core.write_text("fixture core")
    record = {"tool": tool, "entrypoint_sha256": module.digest(executable), "files": module.inventory(generation)}
    marker = generation / "installed.json"
    marker.write_text(json.dumps(record))
    calls = []
    monkeypatch.setattr(module, "preflight", lambda _: {})
    monkeypatch.setattr(module, "smoke", lambda *args: calls.append("version"))
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: pytest.fail("unexpected installer operation"))
    module.install(tool, tmp_path, tmp_path / "cache")
    assert calls == ["version"]
    core.write_text("modified core")
    with pytest.raises(ValueError, match="generation drift"):
        module.install(tool, tmp_path, tmp_path / "cache")
    assert calls == ["version"]
    marker.write_text("[]")
    with pytest.raises(ValueError, match="invalid installed record"):
        module.verify_generation(tool, generation)


def test_runtime_smoke_exit_status_does_not_pass_missing_tools(tmp_path, monkeypatch):
    module = load_local_tools()
    monkeypatch.setattr(sys, "argv", ["local_tools.py", "status", "--root", str(tmp_path)])
    assert module.main() == 0
    monkeypatch.setattr(sys, "argv", ["local_tools.py", "status", "--smoke", "--root", str(tmp_path)])
    assert module.main() == 1


def test_runtime_directory_permissions_and_hardlinks_are_rejected(tmp_path):
    import os
    import pytest
    module = load_local_tools()
    tool = next(t for t in module.load_profile()["tools"] if t["name"] == "semgrep")
    generation = module.generation_for(tool, tmp_path)
    executable = module.binary_path(tool, generation)
    executable.parent.mkdir(parents=True)
    executable.write_text("fixture")
    marker = generation / "installed.json"
    marker.write_text(json.dumps({"tool": tool, "entrypoint_sha256": module.digest(executable), "files": module.inventory(generation)}))
    executable.parent.chmod(0o777)
    with pytest.raises(ValueError, match="unsafe runtime directory"):
        module.verify_generation(tool, generation)
    executable.parent.chmod(0o755)
    os.link(executable, generation / "linked-copy")
    with pytest.raises(ValueError, match="unsafe runtime file"):
        module.verify_generation(tool, generation)


def test_uv_empty_lock_is_private_and_linked_lock_is_preserved(tmp_path):
    import os
    import pytest
    module = load_local_tools()
    lock = tmp_path / ".lock"
    lock.touch()
    lock.chmod(0o666)
    module.secure_uv_lock(lock)
    assert lock.stat().st_mode & 0o777 == 0o600
    os.link(lock, tmp_path / "other-link")
    with pytest.raises(ValueError, match="unexpected uv environment lock"):
        module.secure_uv_lock(lock)
    assert lock.stat().st_nlink == 2


def database_fixture(module, tmp_path, monkeypatch):
    import base64
    import zipfile
    data = tmp_path / "source"
    data.mkdir()
    archive = tmp_path / "advisories.zip"
    payload = b'{"id":"OSV-TEST-1","modified":"2026-10-28T00:00:00Z"}'
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as stream:
        stream.writestr("OSV-TEST-1.json", payload)
    content = archive.read_bytes()
    pin = {"schema_version": 1, "ecosystem": "PyPI", "generation": "1",
           "url": "https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip?generation=1",
           "compressed_bytes": len(content), "expanded_bytes": len(payload), "entries": 1,
           "sha256": hashlib.sha256(content).hexdigest(),
           "md5_base64": base64.b64encode(hashlib.md5(content).digest()).decode(),
           "upstream_updated_at": "2026-10-28T00:00:00Z",
           "max_compressed_bytes": 64 * 1024 * 1024, "max_expanded_bytes": 256 * 1024 * 1024}
    (data / "osv-database.lock.json").write_text(json.dumps(pin))
    monkeypatch.setattr(module, "DATA", data)
    return archive, pin


def test_pypi_database_provision_is_bounded_idempotent_and_scan_free(tmp_path, monkeypatch):
    module = load_local_tools()
    archive, pin = database_fixture(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected external command")))
    root = tmp_path / "runtime"
    module.provision_osv_database(root, archive)
    first = module.osv_database_status({}, root)
    assert first["installed"] is True and first["ecosystems"] == ["PyPI"]
    assert first["scan_validated"] is False
    target = root / "cache/osv/osv-scanner/PyPI/all.zip"
    assert target.read_bytes() == archive.read_bytes()
    module.provision_osv_database(root, archive)
    assert target.read_bytes() == archive.read_bytes()
    assert list(target.parent.iterdir()) == [target]


def test_pypi_database_refuses_drift_and_size_caps(tmp_path, monkeypatch):
    import pytest
    module = load_local_tools()
    archive, pin = database_fixture(module, tmp_path, monkeypatch)
    pin["max_expanded_bytes"] = 1
    (module.DATA / "osv-database.lock.json").write_text(json.dumps(pin))
    with pytest.raises(ValueError, match="database size"):
        module.provision_osv_database(tmp_path / "runtime", archive)
    pin["max_expanded_bytes"] = 256 * 1024 * 1024
    (module.DATA / "osv-database.lock.json").write_text(json.dumps(pin))
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="database.*mismatch"):
        module.provision_osv_database(tmp_path / "runtime", archive)
    assert not (tmp_path / "runtime/cache/osv/osv-scanner/PyPI/all.zip").exists()


def test_pypi_database_preserves_existing_cache_and_rejects_links(tmp_path, monkeypatch):
    import pytest
    module = load_local_tools()
    archive, pin = database_fixture(module, tmp_path, monkeypatch)
    root = tmp_path / "runtime"
    target = root / "cache/osv/osv-scanner/PyPI/all.zip"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"keep existing snapshot")
    with pytest.raises(ValueError, match="database.*mismatch"):
        module.provision_osv_database(root, archive)
    assert target.read_bytes() == b"keep existing snapshot"
    target.unlink()
    target.symlink_to(archive)
    with pytest.raises(ValueError, match="unsafe runtime file"):
        module.provision_osv_database(root, archive)
    assert target.is_symlink()


def test_pypi_download_uses_bounded_credential_free_curl(tmp_path, monkeypatch):
    module = load_local_tools()
    archive, pin = database_fixture(module, tmp_path, monkeypatch)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/synthetic/not-for-child")
    calls = []
    def download(argv, **kwargs):
        calls.append((argv, kwargs))
        Path(argv[argv.index("--output") + 1]).write_bytes(archive.read_bytes())
        return subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(module.subprocess, "run", download)
    module.provision_osv_database(tmp_path / "runtime")
    argv, options = calls[0]
    assert argv[:2] == ["/usr/bin/curl", "--disable"]
    assert argv[-1] == pin["url"]
    assert argv[argv.index("--max-filesize") + 1] == str(64 * 1024 * 1024)
    assert options["timeout"] == 125
    assert set(options["env"]) == {"PATH", "HOME"}
