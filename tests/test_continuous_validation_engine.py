"""Local bootstrap cannot adopt or mutate unrelated Lima workers."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "private_dot_config/dotfiles-ai/continuous_validation/local_engine.py"
TEMPLATE = SOURCE.parent / "engine/lima.yaml"


@pytest.fixture
def engine():
    spec = importlib.util.spec_from_file_location("continuous_validation_engine", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_requires_explicit_shadow_opt_in_before_any_work(engine, tmp_path, monkeypatch):
    for name in ("_host_capability", "_inventory", "_install_cli", "_command"):
        monkeypatch.setattr(engine, name, lambda *_a, **_k: pytest.fail("disabled setup performed work"))
    state = tmp_path / "state"
    result = engine.setup(state, tmp_path / "lima")
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["shadow_opt_in_required"]
    assert not state.exists()


def test_plan_declares_bounded_isolated_worker_without_mutations(engine, monkeypatch):
    monkeypatch.setattr(engine, "_command", lambda *_a, **_k: pytest.fail("plan executed a command"))
    result = engine.plan()
    assert result["resources"] == {"cpus": 2, "memory_gib": 4, "disk_gib": 40}
    assert result["mounts"] == [] and result["ssh_agent_forwarding"] is False
    assert result["dagger_version"] == "0.21.10"
    assert result["engine_transport"] == "private_unix_socket"


def test_template_has_no_host_mounts_or_automatically_forwarded_ports():
    source = TEMPLATE.read_text()
    assert "mounts: []" in source
    assert "forwardAgent: false" in source and "loadDotSSHPubKeys: false" in source
    assert 'memory: "4GiB"' in source and "cpus: 2" in source
    assert "containerd:" in source and "system: false" in source and "user: false" in source
    assert "guestSocket:" in source and "hostSocket:" in source
    assert "ignore: true" in source
    assert "--privileged" in source and "--addr unix:///run/dagger/engine.sock" in source
    assert "@sha256:" in source and "digest: sha256:" in source


@pytest.fixture
def fake_setup(engine, tmp_path, monkeypatch):
    state = tmp_path / "state"
    lima = tmp_path / "lima"
    lima.mkdir()
    rows = {"unrelated-agent": {"name": "unrelated-agent", "status": "Running"}}
    calls = []
    monkeypatch.setattr(engine, "_host_capability", lambda: {"lima_version": "2.2.1"})
    monkeypatch.setattr(engine, "_inventory", lambda *_: dict(rows))
    monkeypatch.setattr(engine, "_install_cli", lambda *_: {"cli": str(state / "bin/dagger"), "cli_sha256": "a" * 64})
    monkeypatch.setattr(engine, "_prepare_sdk", lambda *_: None)
    monkeypatch.setattr(engine, "_probe_worker", lambda *_: {"python_version": "3.13.7", "uv_version": "0.9.2", "podman_version": "5.7.0"})

    def command(argv, **kwargs):
        calls.append(argv)
        if "create" in argv:
            directory = lima / engine.INSTANCE
            directory.mkdir()
            (directory / "lima.yaml").write_bytes(TEMPLATE.read_bytes())
            rows[engine.INSTANCE] = {
                "name": engine.INSTANCE, "status": "Stopped", "dir": str(directory),
                "arch": "aarch64", "vmType": "vz", "cpus": 2,
                "memory": 4 * 1024**3, "disk": 40 * 1024**3,
                "config": {"mounts": [], "ssh": {"forwardAgent": False, "loadDotSSHPubKeys": False}},
            }
        elif "start" in argv:
            rows[engine.INSTANCE]["status"] = "Running"
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(engine, "_command", command)
    return state, lima, rows, calls


def test_existing_unowned_name_refuses_before_install_or_vm_changes(engine, fake_setup, monkeypatch):
    state, lima, rows, calls = fake_setup
    rows[engine.INSTANCE] = {"name": engine.INSTANCE, "status": "Running"}
    monkeypatch.setattr(engine, "_install_cli", lambda *_: pytest.fail("unowned VM must refuse before download"))
    result = engine.setup(state, lima, enable_shadow=True)
    assert result["diagnostic_codes"] == ["local_engine_ownership_unavailable"]
    assert calls == []


def test_new_worker_is_named_stamped_and_does_not_mutate_other_workers(engine, fake_setup):
    state, lima, rows, calls = fake_setup
    result = engine.setup(state, lima, enable_shadow=True)
    assert result["status"] == "ready", result
    assert rows["unrelated-agent"]["status"] == "Running"
    assert not any("stop" in call or "delete" in call for call in calls)
    create = next(call for call in calls if "create" in call)
    assert "--name=" + engine.INSTANCE in create and "--mount-none" in create
    assert (state / "ownership.json").stat().st_mode & 0o777 == 0o600
    config = result["backend_configuration"]
    assert config["engine"].startswith("unix://")
    assert config["cli_sha256"] == "a" * 64
    assert config["python_version"] == "3.13.7"
    assert config["image"].rsplit("@", 1)[1].startswith("sha256:")


def test_repeat_setup_reuses_only_exact_owned_worker(engine, fake_setup):
    state, lima, _, calls = fake_setup
    assert engine.setup(state, lima, enable_shadow=True)["status"] == "ready"
    calls.clear()
    assert engine.setup(state, lima, enable_shadow=True)["status"] == "ready"
    assert not any("create" in call or "start" in call for call in calls)


@pytest.mark.parametrize("change", ["template", "resources", "mounts", "owner"])
def test_existing_worker_drift_refuses_without_mutation(engine, fake_setup, change):
    state, lima, rows, calls = fake_setup
    assert engine.setup(state, lima, enable_shadow=True)["status"] == "ready"
    calls.clear()
    if change == "template":
        (lima / engine.INSTANCE / "lima.yaml").write_text("changed")
    elif change == "resources":
        rows[engine.INSTANCE]["cpus"] = 8
    elif change == "mounts":
        rows[engine.INSTANCE]["config"]["mounts"] = [{"location": "/private-data"}]
    else:
        record = json.loads((state / "ownership.json").read_text())
        record["owner"] = "different-owner"
        (state / "ownership.json").write_text(json.dumps(record))
    result = engine.setup(state, lima, enable_shadow=True)
    assert result["status"] == "unavailable"
    assert calls == []


def test_download_checksum_failure_does_not_install_or_execute(engine, tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "_download", lambda *_: b"tampered archive")
    monkeypatch.setattr(engine, "_command", lambda *_a, **_k: pytest.fail("unverified asset executed"))
    with pytest.raises(Exception, match="checksum"):
        engine._install_cli(tmp_path)
    assert not (tmp_path / "bin/dagger").exists()


def test_installed_cli_probe_cannot_use_host_registry_or_cloud_auth(engine, tmp_path, monkeypatch):
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir(mode=0o700)
    binary = binary_dir / "dagger"
    binary.write_bytes(b"fixture pinned binary; execution mocked")
    binary.chmod(0o700)
    engine._write_private(tmp_path / "cli.json", {
        "archive_sha256": engine.CLI_ARCHIVE_SHA256, "binary_sha256": engine._digest(binary),
    })
    monkeypatch.setenv("DAGGER_CLOUD_TOKEN", "PRIVATE_TOKEN")
    monkeypatch.setenv("DOCKER_AUTH_CONFIG", "PRIVATE_AUTH")
    previous = dict(engine.os.environ)
    def command(_argv, **kwargs):
        environment = kwargs["env"]
        assert environment["DO_NOT_TRACK"] == "1"
        assert "DAGGER_CLOUD_TOKEN" not in environment and "DOCKER_AUTH_CONFIG" not in environment
        assert Path(environment["XDG_CONFIG_HOME"]).is_dir()
        assert json.loads((Path(environment["DOCKER_CONFIG"]) / "config.json").read_text()) == {"auths": {}}
        return SimpleNamespace(stdout="dagger v0.21.10", returncode=0)
    monkeypatch.setattr(engine, "_command", command)
    assert engine._install_cli(tmp_path)["cli"] == str(binary)
    assert dict(engine.os.environ) == previous


def test_bootstrap_sdk_identity_probe_uses_private_cli_auth_boundary(engine, tmp_path, monkeypatch):
    worker = tmp_path / "worker"
    (worker / "sock").mkdir(parents=True)
    (worker / "sock/cvs-dagger.sock").touch()
    monkeypatch.setattr(engine.Path, "is_socket", lambda _path: True)
    monkeypatch.setenv("DAGGER_CLOUD_TOKEN", "PRIVATE_TOKEN")
    monkeypatch.setenv("DOCKER_AUTH_CONFIG", "PRIVATE_AUTH")
    cli = {"cli": "/fixture/dagger", "cli_sha256": "a" * 64}
    def command(argv, **kwargs):
        if "inspect" in argv:
            digest = engine.ENGINE_IMAGE.split("@", 1)[1]
            result = [{"Config": {"Image": engine.ENGINE_IMAGE}, "ImageName": engine.ENGINE_IMAGE,
                       "ImageDigest": digest, "State": {"Running": True}}]
        elif "run" in argv:
            result = {"python_version": "3.14.0", "uv_version": "0.9.2", "git_version": "git version 2.39.5"}
        elif "--version" in argv:
            return SimpleNamespace(stdout="podman version 5.7.0", returncode=0)
        else:
            environment = kwargs["env"]
            assert environment["DO_NOT_TRACK"] == "1"
            assert "DAGGER_CLOUD_TOKEN" not in environment and "DOCKER_AUTH_CONFIG" not in environment
            assert environment["_EXPERIMENTAL_DAGGER_CLI_BIN"] == cli["cli"]
            assert environment["_EXPERIMENTAL_DAGGER_RUNNER_HOST"].startswith("unix://")
            assert not list(Path(environment["XDG_CONFIG_HOME"]).iterdir())
            result = {"version": "v0.21.10", "platform": "linux/arm64"}
        return SimpleNamespace(stdout=json.dumps(result), returncode=0)
    monkeypatch.setattr(engine, "_command", command)
    assert engine._probe_worker(tmp_path / "lima", {"dir": str(worker)}, cli, tmp_path)["python_version"] == "3.14.0"


@pytest.mark.parametrize("encoding", ["null", "omitted"])
def test_lima_serialized_zero_mounts_mean_no_host_mounts(engine, fake_setup, monkeypatch, encoding):
    state, lima, rows, _ = fake_setup
    original = engine._command
    def command(argv, **kwargs):
        result = original(argv, **kwargs)
        if "create" in argv:
            if encoding == "null":
                rows[engine.INSTANCE]["config"]["mounts"] = None
            else:
                rows[engine.INSTANCE]["config"].pop("mounts")
        return result
    monkeypatch.setattr(engine, "_command", command)
    assert engine.setup(state, lima, enable_shadow=True)["status"] == "ready"


@pytest.mark.parametrize("same_configuration", [True, False])
def test_interrupted_creation_recovers_only_canonically_matching_configuration(engine, fake_setup, monkeypatch, same_configuration):
    state, lima, rows, calls = fake_setup
    assert engine.setup(state, lima, enable_shadow=True)["status"] == "ready"
    record_path = state / "ownership.json"
    record = json.loads(record_path.read_text())
    record["status"] = "creating"
    record.pop("instance_config_sha256")
    record_path.write_text(json.dumps(record))
    rows[engine.INSTANCE]["status"] = "Stopped"
    calls.clear()
    def canonical(path, *_args):
        return {"configuration": "approved" if path == engine.TEMPLATE or same_configuration else "changed"}
    monkeypatch.setattr(engine, "_canonical_configuration", canonical, raising=False)
    result = engine.setup(state, lima, enable_shadow=True)
    if same_configuration:
        assert result["status"] == "ready"
        assert json.loads(record_path.read_text())["instance_config_sha256"]
        assert not any("create" in call for call in calls)
    else:
        assert result["status"] == "unavailable"
        assert not any("create" in call or "start" in call for call in calls)


@pytest.mark.parametrize("normalized", [True, False])
def test_podman_reference_normalization_preserves_exact_manifest_identity(engine, normalized):
    digest = engine.ENGINE_IMAGE.split("@", 1)[1]
    reference = "registry.dagger.io/engine@" + digest if normalized else engine.ENGINE_IMAGE
    value = [{"Config": {"Image": reference}, "ImageName": reference,
              "ImageDigest": digest, "State": {"Running": True}}]
    engine._validate_container(value)


@pytest.mark.parametrize("problem", ["digest", "repository", "stopped"])
def test_container_identity_drift_cannot_pass_engine_probe(engine, problem):
    digest = engine.ENGINE_IMAGE.split("@", 1)[1]
    reference = "registry.dagger.io/engine@" + digest
    value = [{"Config": {"Image": reference}, "ImageName": reference,
              "ImageDigest": digest, "State": {"Running": True}}]
    if problem == "digest":
        value[0]["ImageDigest"] = "sha256:" + "0" * 64
    elif problem == "repository":
        value[0]["Config"]["Image"] = "registry.invalid/other@" + digest
    else:
        value[0]["State"]["Running"] = False
    with pytest.raises(engine.EngineError, match="container_mismatch"):
        engine._validate_container(value)
