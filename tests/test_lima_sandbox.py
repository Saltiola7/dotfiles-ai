import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_opencode-vm"


def load_helper():
    loader = importlib.machinery.SourceFileLoader("opencode_vm", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def config(tmp_path: Path) -> dict:
    return {
        "schema_version": 1,
        "source": "https://github.com/Saltiola7/dotfiles-ai.git",
        "clients": {
            "personal": {
                "instance": "opencode-personal",
                "root": str(tmp_path / "github"),
                "protected_repo": "",
            },
            "mgm": {
                "instance": "opencode-mgm",
                "root": str(tmp_path / "MGM/git"),
                "protected_repo": str(tmp_path / "MGM/reference/seo-code-analysis"),
            },
        },
    }


def history_page() -> dict:
    return {
        "schema_version": 1,
        "snapshot": 10,
        "session_ceiling": 9,
        "part_ceiling": 8,
        "database_digest": "a" * 64,
        "exclusion_digest": "b" * 64,
        "limit": 5,
        "cursor": 0,
        "continuation": None,
        "candidates": [],
    }


def test_fedora_templates_pin_runtime_and_sparse_disk() -> None:
    for client in ("personal", "mgm"):
        template = (ROOT / f"private_dot_config/dotfiles-ai/lima/{client}.yaml.tmpl").read_text()
        assert "template:fedora-44" in template
        assert 'vmType: "vz"' in template
        assert 'arch: "aarch64"' in template
        assert 'disk: "{{ .dotfiles_ai.sandbox.disk_gib }}GiB"' in template
        assert "opencode-linux-arm64.tar.gz" in template
        assert "eba87efba3976d533a24cca0316f8ef375b5f8e797c0a95c25ee919700b7ba35" in template
        assert "herdr-linux-aarch64" in template
        assert "32e763a1499a6b694b1d708e4f062b743be1da9f34fcfa4d212d6db6fe09a8b9" in template


def test_client_paths_are_explicit_and_non_overlapping(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    for path in (
        tmp_path / "github",
        tmp_path / "MGM/git",
        tmp_path / "MGM/reference/seo-code-analysis",
    ):
        path.mkdir(parents=True)
    helper.validate_config(values)

    values["clients"]["mgm"]["protected_repo"] = str(tmp_path / "MGM/git/seo-code-analysis")
    with pytest.raises(ValueError, match="overlap"):
        helper.validate_config(values)


def test_federation_namespaces_sources_and_restores_stopped_instances(tmp_path: Path) -> None:
    helper = load_helper()
    calls = []
    running = {"opencode-personal": False, "opencode-mgm": True}

    def execute(argv, **_kwargs):
        calls.append(argv)
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": name, "status": "Running" if state else "Stopped"}
                for name, state in running.items()
            ])
        if argv[:2] == ["limactl", "start"]:
            running[argv[2]] = True
            return ""
        if argv[:2] == ["limactl", "stop"]:
            running[argv[2]] = False
            return ""
        if argv[:2] == ["limactl", "shell"]:
            return json.dumps(history_page())
        if argv[:2] == ["dbsctrctl", "review-history"]:
            return json.dumps(history_page())
        raise AssertionError(argv)

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert [source["source_id"] for source in result["sources"]] == ["host", "personal", "mgm"]
    assert all(source["availability"] == "available" for source in result["sources"])
    assert len(result["manifest_digest"]) == 64
    assert running == {"opencode-personal": False, "opencode-mgm": True}
    assert ["limactl", "start", "opencode-personal"] in calls
    assert ["limactl", "stop", "opencode-personal"] in calls
    assert ["limactl", "stop", "opencode-mgm"] not in calls


def test_federation_rejects_unsafe_remote_output(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "opencode-personal", "status": "Running"},
                {"name": "opencode-mgm", "status": "Running"},
            ])
        if argv[:2] == ["dbsctrctl", "review-history"]:
            return json.dumps(history_page())
        return json.dumps({**history_page(), "leak": "/Users/private/key"})

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert result["sources"][1] == {
        "source_id": "personal",
        "availability": "invalid_output",
    }


def test_federation_continuation_reuses_each_source_identity(tmp_path: Path) -> None:
    helper = load_helper()
    calls = []

    def execute(argv, **_kwargs):
        calls.append(argv)
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "opencode-personal", "status": "Running"},
                {"name": "opencode-mgm", "status": "Running"},
            ])
        return json.dumps({**history_page(), "continuation": 5})

    first = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    helper.federated_review(config(tmp_path), 5, 5, first["source_state"], execute=execute)
    continuation = [call for call in calls if "review-history" in call][-1]
    assert continuation[continuation.index("--snapshot") + 1] == "10"
    assert continuation[continuation.index("--database-digest") + 1] == "a" * 64


def test_handoff_requires_explicit_proceed_and_sanitized_paths(tmp_path: Path) -> None:
    helper = load_helper()
    report = {
        "schema_version": 1,
        "worker_id": "dbsctr-12345678",
        "proceed": True,
        "target": "personal",
        "risk": "elevated",
        "summary": "Implement the approved sandbox improvement",
        "paths": ["dot_local/bin/executable_opencode-vm"],
        "validation": ["pytest tests/test_lima_sandbox.py"],
    }
    assert helper.validate_handoff(report) == report

    with pytest.raises(ValueError, match="proceed"):
        helper.validate_handoff({**report, "proceed": False})
    with pytest.raises(ValueError, match="repository-relative"):
        helper.validate_handoff({**report, "paths": ["/absolute/secret"]})


def test_submodule_manifest_is_stable_and_relative(tmp_path: Path) -> None:
    helper = load_helper()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitmodules").write_text(
        '[submodule "one"]\n\tpath = modules/one\n\turl = https://example.invalid/one\n'
        '[submodule "two"]\n\tpath = modules/two\n\turl = https://example.invalid/two\n'
    )
    assert helper.submodule_paths(repo) == ["modules/one", "modules/two"]

    (repo / ".gitmodules").write_text('[submodule "bad"]\n\tpath = ../escape\n')
    with pytest.raises(ValueError, match="submodule path"):
        helper.submodule_paths(repo)


def test_shortcuts_attach_to_existing_vm_herdr() -> None:
    assert "opencode-vm herdr personal" in (ROOT / "dot_local/bin/executable_herdr-personal").read_text()
    assert "opencode-vm herdr mgm" in (ROOT / "dot_local/bin/executable_herdr-mgm").read_text()
