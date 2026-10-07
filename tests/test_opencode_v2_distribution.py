"""One-time V2 generation boundaries; synthetic artifacts, no live state."""
import base64
import copy
import hashlib
import io
import json
import os
import sys
import tarfile

import pytest

from test_opencode_distribution import fake_binary, load_updater, release_payload


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    helper = load_updater()
    root, binary = tmp_path / "package", tmp_path / "bin/opencode"
    root.mkdir(mode=0o700)
    binary.parent.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    fake_binary(binary, "opencode v2.0.22")
    package = {"name": "@opencode/cli-darwin-arm64", "version": "2.0.22",
               "os": ["darwin"], "cpu": ["arm64"]}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, body in (("package/package.json", json.dumps(package).encode()),
                           ("package/bin/opencode", binary.read_bytes())):
            member = tarfile.TarInfo(name)
            member.size = len(body)
            archive.addfile(member, io.BytesIO(body))
    data = stream.getvalue()
    artifact = {"package": package["name"], "version": "2.0.22",
                "url": "https://registry.npmjs.org/@opencode/cli-darwin-arm64/-/cli-darwin-arm64-2.0.22.tgz",
                "integrity": "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode(),
                "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    lock = {"schema_version": 2, "channel": "stable", "release": "2.0.22",
            "platform": "darwin-aarch64", "binary_sha256": helper.file_digest(binary),
            "artifact": artifact, "validator_revision": "opencode-v2-validator-1",
            "admission": None, "previous": None}
    return helper, root, binary, lock, data, package


def test_v2_lock_is_recognized_without_v1_revalidation(fixture, monkeypatch):
    helper, root, binary, lock, *_ = fixture
    helper.atomic_json(root / "release-lock.json", lock)
    monkeypatch.setattr(helper, "validate_binary", lambda *_: pytest.fail("V1 validator called"))
    assert helper.read_lock(root) == lock
    assert helper.upgrade_validator_lock(root, binary, lock) == lock
    assert not helper.healthy(lock, binary), "unadmitted V2 must not launch"


@pytest.mark.parametrize("field,value", [
    ("schema_version", 3), ("release", "1.18.31"), ("binary_sha256", "bad"),
    ("platform", "linux-aarch64"), ("validator_revision", "opencode-release-validator-5"),
    ("admission", True),
])
def test_malformed_v2_lock_is_preserved_and_rejected(fixture, field, value):
    helper, root, _, lock, *_ = fixture
    lock[field] = value
    helper.atomic_json(root / "release-lock.json", lock)
    before = (root / "release-lock.json").read_bytes()
    with pytest.raises(helper.UpdateError):
        helper.read_lock(root)
    assert (root / "release-lock.json").read_bytes() == before


def test_v2_archive_checks_provenance_and_member_boundaries(fixture, tmp_path):
    helper, _, _, lock, data, _ = fixture
    archive = tmp_path / "archive.tgz"
    archive.write_bytes(data)
    helper.extract_v2(archive, tmp_path / "candidate", lock["artifact"], lock["platform"])
    assert helper.file_digest(tmp_path / "candidate") == lock["binary_sha256"]
    broken = copy.deepcopy(lock["artifact"])
    broken["integrity"] = "sha512-" + base64.b64encode(b"x" * 64).decode()
    with pytest.raises(helper.UpdateError):
        helper.extract_v2(archive, tmp_path / "bad", broken, lock["platform"])
    assert not (tmp_path / "bad").exists()


def test_v2_interruption_blocks_automatic_v1_recovery(fixture, monkeypatch):
    helper, root, binary, _, *_ = fixture
    helper.atomic_json(root / "v2-transition.json", {"phase": "prepared"})
    monkeypatch.setattr(helper, "rollback", lambda *_: pytest.fail("V1 rollback called"))
    with pytest.raises(helper.UpdateError):
        helper.recover(root, binary)
    assert (root / "v2-transition.json").exists()


def stage_fixture(fixture, monkeypatch):
    helper, root, binary, lock, data, _ = fixture
    fake_binary(binary)
    old = helper.generation(helper.validate_release(release_payload()), "darwin-aarch64", helper.file_digest(binary))
    old["previous"] = None
    helper.atomic_json(root / "release-lock.json", old)
    monkeypatch.setattr(helper, "download_v2", lambda artifact, destination, platform: destination.write_bytes(data))
    current = hashlib.sha256((root / "release-lock.json").read_bytes()).hexdigest()
    staged = helper.stage_v2({"release": lock["release"], "artifact": lock["artifact"]}, root, binary)
    assert helper.read_lock(root) == old
    return {"candidate_digest": helper.v2_identity(staged), "current_sha256": current}, old


def admission_fixture(helper, root, candidate_digest):
    def store(directory, value):
        directory.mkdir(exist_ok=True, mode=0o700)
        raw = helper.canonical(value)
        digest = hashlib.sha256(raw).hexdigest()
        path = directory / (digest + ".json")
        path.write_bytes(raw)
        path.chmod(0o400)
        return digest
    manifest = {"schema_version": 1, "candidate_digest": candidate_digest}
    for kind in ("configuration", "service", "data", "recovery", "reconciliation"):
        manifest[kind] = store(root / "v2-evidence", {
            "kind": kind, "candidate_digest": candidate_digest, "result": "passed",
            "fixture": "synthetic workflow evidence only, not live admission",
        })
    return {"candidate_digest": candidate_digest,
            "manifest_sha256": store(root / "v2-admissions", manifest)}


def test_stage_activate_admit_and_held_update_preserve_both_generations(fixture, monkeypatch):
    helper, root, binary, *_ = fixture
    request, old = stage_fixture(fixture, monkeypatch)
    prior_binary, prior_lock = binary.read_bytes(), (root / "release-lock.json").read_bytes()
    activated = helper.activate_v2(request, root, binary)
    assert activated["previous"] == {key: value for key, value in old.items() if key != "previous"}
    assert not helper.healthy(activated, binary)
    with pytest.raises(helper.UpdateError):
        helper.exec_managed(["--session", "synthetic"])
    with pytest.raises(helper.UpdateError):
        helper.admit_v2({"candidate_digest": request["candidate_digest"], "manifest_sha256": "a" * 64}, root, binary)
    assert (root / "v2-transition.json").exists()
    directory = root / json.loads((root / "v2-candidate.json").read_text())["directory"]
    assert (directory / "previous-opencode").read_bytes() == prior_binary
    assert (directory / "previous-lock.json").read_bytes() == prior_lock
    admitted = helper.admit_v2(admission_fixture(helper, root, request["candidate_digest"]), root, binary)
    assert helper.healthy(admitted, binary)
    assert not (root / "v2-transition.json").exists()
    for name in ("fetch_release", "sandbox_config", "recover_host", "validate_binary"):
        monkeypatch.setattr(helper, name, lambda *_: pytest.fail("V1 path reached"))
    assert helper.host_update() == 0
    assert helper.local_update() == 0
    assert helper.read_lock(root) == admitted
    class Executed(Exception):
        pass
    def execute(executable, arguments, environment):
        assert executable == binary and arguments == [str(binary), "--session", "synthetic"]
        raise Executed
    monkeypatch.setattr(helper.os, "execve", execute)
    with pytest.raises(Executed):
        helper.exec_managed(["--session", "synthetic"])
    binary.write_text("tampered")
    assert not helper.healthy(admitted, binary)
    assert helper.local_update() == 1


@pytest.mark.parametrize("failure", ["stale_preimage", "after_backup"])
def test_activation_failure_never_discards_preimages(fixture, monkeypatch, failure):
    helper, root, binary, *_ = fixture
    request, _ = stage_fixture(fixture, monkeypatch)
    before = binary.read_bytes(), (root / "release-lock.json").read_bytes()
    if failure == "stale_preimage":
        request["current_sha256"] = "a" * 64
        with pytest.raises(helper.UpdateError):
            helper.activate_v2(request, root, binary)
        assert not (root / "v2-transition.json").exists()
    else:
        replace = helper.os.replace
        def interrupted(source, destination):
            if destination == binary:
                raise OSError("synthetic interrupted activation")
            return replace(source, destination)
        monkeypatch.setattr(helper.os, "replace", interrupted)
        with pytest.raises(OSError):
            helper.activate_v2(request, root, binary)
        with pytest.raises(helper.UpdateError):
            helper.host_update()
        assert json.loads((root / "v2-transition.json").read_text())["phase"] == "backed_up"
    assert (binary.read_bytes(), (root / "release-lock.json").read_bytes()) == before


@pytest.mark.parametrize("hazard", ["duplicate", "traversal", "symlink", "wrong_package", "hook"])
def test_unsafe_archive_never_extracts_an_executable(fixture, tmp_path, hazard):
    helper, _, binary, lock, _, package = fixture
    archive = tmp_path / "unsafe.tgz"
    if hazard == "wrong_package":
        package["name"] = "untrusted"
    if hazard == "hook":
        package["scripts"] = {"postinstall": "untrusted"}
    with tarfile.open(archive, "w:gz") as bundle:
        for name, body in (("package/package.json", json.dumps(package).encode()),
                           ("package/bin/opencode", binary.read_bytes())):
            member = tarfile.TarInfo("../escaped" if hazard == "traversal" and name.endswith("opencode") else name)
            member.size = len(body)
            if hazard == "symlink" and name.endswith("opencode"):
                member.type, member.linkname = tarfile.SYMTYPE, "../../escaped"
                member.size = 0
            bundle.addfile(member, io.BytesIO(body))
            if hazard == "duplicate":
                bundle.addfile(member, io.BytesIO(body))
    data = archive.read_bytes()
    artifact = {**lock["artifact"], "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "integrity": "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()}
    with pytest.raises(helper.UpdateError):
        helper.extract_v2(archive, tmp_path / "unsafe-executable", artifact, lock["platform"])
    assert not (tmp_path / "unsafe-executable").exists()


def test_missing_or_changed_evidence_cannot_admit(fixture, monkeypatch):
    helper, root, binary, *_ = fixture
    request, _ = stage_fixture(fixture, monkeypatch)
    helper.activate_v2(request, root, binary)
    admission = admission_fixture(helper, root, request["candidate_digest"])
    evidence = next((root / "v2-evidence").iterdir())
    evidence.chmod(0o600)
    evidence.write_text("changed")
    evidence.chmod(0o400)
    with pytest.raises(helper.UpdateError):
        helper.admit_v2(admission, root, binary)
    assert helper.read_lock(root)["admission"] is None
    assert (root / "v2-transition.json").exists()


def test_stage_cli_consumes_bounded_request_without_activation(fixture, monkeypatch, capsys):
    helper, root, binary, lock, data, _ = fixture
    monkeypatch.setattr(helper, "download_v2", lambda artifact, destination, platform: destination.write_bytes(data))
    request = {"release": lock["release"], "artifact": lock["artifact"]}
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(request).encode())))
    before = binary.read_bytes()
    assert helper.main(["stage-v2"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"schema_version": 1, "status": "staged", "release": "2.0.22", "target_count": 1, "reason": "none"}
    assert binary.read_bytes() == before and not (root / "release-lock.json").exists()
    assert (root / "v2-candidate.json").exists()


@pytest.mark.skipif(os.environ.get("OPENCODE_V2_STAGING_SMOKE") != "1",
                    reason="official native artifact staging not selected")
def test_official_native_v2_staging_is_isolated(tmp_path, monkeypatch):
    helper = load_updater()
    assert helper.platform_id() == "darwin-aarch64"
    root = tmp_path / "package"
    root.mkdir(mode=0o700)
    binary = tmp_path / "never-installed"
    artifact = {
        "package": "@opencode/cli-darwin-arm64", "version": "2.0.22",
        "url": "https://registry.npmjs.org/@opencode/cli-darwin-arm64/-/cli-darwin-arm64-2.0.22.tgz",
        "integrity": "sha512-NNg1VCCTWSfLlNKpRb4RA6IE7H67ZBLBYmfIWjP3CxR9NPtdROQFCL8lpPf+Tz2Qje4Bb27sQOLWanYyNT/9dQ==",
        "sha256": "16f5f5851e0fcf86dc38c98042bc50e5f167319a9973897c9487f17b2e810117",
        "size": 77796777,
    }
    monkeypatch.setenv("HOME", str(tmp_path))
    staged = helper.stage_v2({"release": "2.0.22", "artifact": artifact}, root, binary)
    assert staged["binary_sha256"] == "af29b0b1b0291dbf2471c66c89d2e055b6afa9c41a950e052fa609c3295e2a75"
    assert staged["admission"] is None
    assert not binary.exists() and not (root / "release-lock.json").exists()
