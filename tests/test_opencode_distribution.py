import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import zipfile

import pytest


ROOT = Path(__file__).parents[1]
UPDATER = ROOT / "dot_local/bin/executable_opencode-update-all"


def load_updater():
    loader = importlib.machinery.SourceFileLoader("opencode_update", str(UPDATER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def release_payload(version="1.18.29"):
    assets = []
    for name in (
        "opencode-darwin-arm64.zip",
        "opencode-linux-arm64.tar.gz",
        "opencode-linux-x64.tar.gz",
    ):
        assets.append({
            "name": name,
            "size": 6,
            "digest": "sha256:" + "a" * 64,
            "browser_download_url":
                f"https://github.com/anomalyco/opencode/releases/download/v{version}/{name}",
        })
    return {"name": f"v{version}", "tag_name": f"v{version}", "draft": False,
            "prerelease": False, "assets": assets}


def fake_binary(path: Path, version="1.18.29", valid=True, tool_valid=True, minimal=False):
    config = ({"agent": {"build": {}, "plan": {}} if minimal else {"build": {}, "build-rnd": {}, "plan": {}},
               "permission": {"dbsctr_status": "allow", "dbsctr_begin": "deny",
                              "dks_context": "allow", "dbsctr_attach": "deny",
                              "dbsctr_reconcile": "deny", "dbsctr_phase_span": "deny",
                              "dbsctr_execution_benchmark": "deny", "dbsctr_execution_dag": "deny",
                               "dbsctr_improvement_claim": "allow",
                               "dbsctr_improvement_update": "allow"}} if valid else {})
    tool = {} if not tool_valid else {"dbsctr_status": {}}
    path.write_text(
        "#!/bin/sh\n"
        f"case \"$1\" in --version) printf '{version}\\n';; --help) printf 'help\\n' >&2;; "
        "agent) printf 'build primary\\nbuild-rnd primary\\nplan primary\\n';; "
        "session) printf 'opencode session list\\n' >&2;; "
        f"debug) if [ \"$2\" = agent ]; then printf '%s\\n' "
        f"'{json.dumps({'name': 'build', 'tools': tool})}'; else "
        f"printf '%s\\n' '{json.dumps(config)}'; fi;; esac\n"
    )
    path.chmod(0o700)


def test_release_metadata_accepts_official_name_and_complete_assets() -> None:
    helper = load_updater()
    value = helper.validate_release(release_payload())

    assert value["release"] == "1.18.29"
    assert set(value["assets"]) == {"darwin-aarch64", "linux-aarch64", "linux-x86_64"}
    broken = release_payload()
    broken["assets"].pop()
    with pytest.raises(helper.UpdateError):
        helper.validate_release(broken)
    with pytest.raises(helper.UpdateError):
        helper.validate_release({**release_payload(), "tag_name": "1.18.29"})
    with pytest.raises(helper.UpdateError, match="metadata_unavailable"):
        helper.MetadataRedirectHandler().redirect_request(None, None, 302, "", {}, "https://example.com")


def test_extract_accepts_one_regular_zip_or_tar_member(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    archive = tmp_path / "candidate"
    destination = tmp_path / "opencode"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("opencode", b"zip")
    helper.extract(archive, destination, "opencode")
    assert destination.read_bytes() == b"zip"

    archive.unlink()
    destination.unlink()
    with tarfile.open(archive, "w:gz") as bundle:
        info = tarfile.TarInfo("opencode")
        info.size = 3
        bundle.addfile(info, io.BytesIO(b"tar"))
    helper.extract(archive, destination, "opencode")
    assert destination.read_bytes() == b"tar"

    class Encrypted:
        filename = "opencode"
        file_size = 3

    class Bundle:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def infolist(self):
            return [Encrypted()]

        def open(self, _member):
            raise RuntimeError("encrypted")

    monkeypatch.setattr(helper.zipfile, "is_zipfile", lambda _path: True)
    monkeypatch.setattr(helper.zipfile, "ZipFile", lambda _path: Bundle())
    with pytest.raises(helper.UpdateError):
        helper.extract(archive, destination, "opencode")


def test_semantic_validator_requires_managed_roles_and_permissions(tmp_path: Path) -> None:
    helper = load_updater()
    binary = tmp_path / "opencode"
    fake_binary(binary)
    helper.validate_binary(binary, "1.18.29")

    fake_binary(binary, valid=False)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")

    fake_binary(binary, tool_valid=False)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")

    fake_binary(binary, minimal=True)
    helper.validate_binary(binary, "1.18.29")

    helper = load_updater()
    helper.run = lambda *_args, **_kwargs: b"\xff"
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")


def test_stage_lock_binds_binary_and_activates(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    monkeypatch.setattr(helper, "download", lambda _asset, path: path.write_bytes(b"archive"))
    monkeypatch.setattr(helper, "extract", lambda _archive, path, _member: fake_binary(path))
    candidate = helper.validate_release(release_payload())

    assert helper.stage(candidate) == "staged"
    lock = json.loads((root / "candidate-lock.json").read_text())
    assert lock["binary_sha256"] == hashlib.sha256(
        (root / "candidate-opencode").read_bytes()).hexdigest()
    assert helper.activate() == "updated"
    assert helper.healthy(helper.read_lock())
    assert stat.S_IMODE(binary.stat().st_mode) == 0o700


def test_same_release_asset_mutation_is_rejected(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    candidate = helper.validate_release(release_payload())
    lock = helper.generation(candidate, "darwin-aarch64", "b" * 64)
    lock["previous"] = None
    helper.atomic_json(root / "release-lock.json", lock)
    mutated = json.loads(json.dumps(candidate))
    mutated["assets"]["darwin-aarch64"]["sha256"] = "c" * 64

    with pytest.raises(helper.UpdateError, match="candidate_invalid"):
        helper.stage(mutated, root, binary)


def test_validator_revision_retries_rejection_and_upgrades_live_lock(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    fake_binary(binary)
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    candidate = helper.validate_release(release_payload())
    old_revision = "opencode-release-validator-1"
    helper.atomic_json(root / "rejected-candidate.json", {
        "schema_version": 1, "release": candidate["release"],
        "candidate_digest": hashlib.sha256(helper.canonical(candidate)).hexdigest(),
        "validator_revision": old_revision, "reason": "validation_failed",
    })
    assert helper.rejected_candidate(candidate, root) is False

    lock = helper.generation(candidate, "darwin-aarch64", helper.file_digest(binary))
    lock["validator_revision"] = old_revision
    lock["previous"] = None
    helper.atomic_json(root / "release-lock.json", lock)
    old_lock = helper.read_lock(root)
    assert helper.healthy(old_lock, binary) is False
    upgraded = helper.upgrade_validator_lock(root, binary, old_lock)
    assert upgraded["validator_revision"] == helper.VALIDATOR_REVISION
    assert helper.read_lock(root)["validator_revision"] == helper.VALIDATOR_REVISION


def test_legacy_guest_is_verified_before_migration_marker(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    assert helper.LEGACY_LINUX_AARCH64_BINARY_SHA256 == (
        "896c9c9b1942d4d74576868af24bbcbfa3f267d7eeb17aa6b8dff70810800084"
    )
    root = tmp_path / "state"
    root.mkdir(mode=0o700)
    legacy = tmp_path / "legacy-opencode"
    fake_binary(legacy, helper.LEGACY_RELEASE)
    legacy.chmod(0o755)
    monkeypatch.setattr(helper, "LEGACY_ROOT", str(legacy))
    monkeypatch.setattr(helper, "LEGACY_LINUX_AARCH64_BINARY_SHA256", helper.file_digest(legacy))
    helper.validate_legacy(legacy, os.getuid())
    monkeypatch.setattr(helper, "validate_legacy", lambda _path: None)
    monkeypatch.setattr(helper, "platform_id", lambda: "linux-aarch64")
    monkeypatch.setattr(helper, "binary_path", lambda: tmp_path / "missing")

    helper.verify_legacy(root)

    marker = json.loads((root / "legacy-migration.json").read_text())
    assert marker == {"schema_version": 1, "release": helper.LEGACY_RELEASE,
                      "binary_sha256": helper.LEGACY_LINUX_AARCH64_BINARY_SHA256}


def test_host_update_stages_every_guest_before_activation(tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    candidate = helper.validate_release(release_payload())
    calls = []
    monkeypatch.setattr(helper, "fetch_release", lambda: candidate)
    monkeypatch.setattr(helper, "read_lock", lambda *_args: None)
    health = iter((False, True))
    monkeypatch.setattr(helper, "healthy", lambda *_args: next(health))
    monkeypatch.setattr(helper, "rejected_candidate", lambda *_args: False)
    monkeypatch.setattr(helper, "sandbox_config", lambda: ["workspace-a", "workspace-b"])

    def stage(candidate, root, _binary, target_count, targets_digest):
        calls.append("stage-host")
        lock = helper.generation(candidate, "darwin-aarch64", "b" * 64,
                                 target_count, targets_digest)
        lock["previous"] = None
        helper.atomic_json(root / "candidate-lock.json", lock)
        return "staged"

    stages = {}

    def guest(action, workspace, candidate=None, **_kwargs):
        calls.append(f"{action}-{workspace}")
        if action == "stage":
            stages[workspace] = stages.get(workspace, 0) + 1
            return "staged" if stages[workspace] == 1 else "current"
        return "current"

    monkeypatch.setattr(helper, "stage", stage)
    monkeypatch.setattr(helper, "guest_call", guest)
    monkeypatch.setattr(helper, "activate", lambda *_args, **_kwargs:
                        calls.append("activate-host") or "updated")

    assert helper.host_update() == 0
    assert calls[:5] == ["stage-host", "stage-workspace-a", "stage-workspace-b",
                         "activate-workspace-a", "activate-workspace-b"]
    assert calls.index("activate-host") > calls.index("activate-workspace-b")
    assert json.loads(capsys.readouterr().out)["target_count"] == 3


def test_exec_managed_recovers_and_execs_verified_path(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    fake_binary(binary)
    candidate = helper.validate_release(release_payload())
    lock = helper.generation(candidate, helper.platform_id(), helper.file_digest(binary))
    lock["previous"] = None
    helper.atomic_json(root / "release-lock.json", lock)
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    monkeypatch.setattr(helper, "recover_host", lambda *_args: None)
    called = {}

    class ExecCalled(Exception):
        pass

    def execute(path, argv, environment):
        called.update(path=path, argv=argv, environment=environment)
        raise ExecCalled

    monkeypatch.setattr(helper.os, "execve", execute)
    with pytest.raises(ExecCalled):
        helper.exec_managed(["--version"])
    assert called["path"] == binary
    assert called["argv"] == [str(binary), "--version"]

    binary.write_text("tampered")
    binary.chmod(0o700)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.exec_managed(["--version"])
