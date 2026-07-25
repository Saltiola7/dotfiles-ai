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
        "digest": "c" * 64,
        "query": {
            "after": None,
            "archive_only": False,
            "before": None,
            "context": None,
            "cycle_id": None,
            "method_revision": None,
            "project_digest": None,
            "reviewed_status": None,
            "state": None,
        },
        "session_ids": [],
    }


def history_candidate(helper) -> dict:
    return {
        "schema_version": 1,
        "session_id": "session-1",
        "snapshot": 10,
        "session_ceiling": 9,
        "part_ceiling": 8,
        "database_digest": "a" * 64,
        "project_digest": "d" * 64,
        "context": "dotfiles_ai_distribution",
        "completed_at": "2026-07-24T10:00:00Z",
        "reviewed_status": "unreviewed",
        "correlation_quality": "exact",
        "cycles": [{"cycle_id": "DAI-007", "state": "active"}],
        "aggregates": {key: 0 for key in helper.AGGREGATE_KEYS},
        "telemetry": {
            "approval_count": 0,
            "attribution_status": "exact",
            "availability": {key: "available" for key in helper.AVAILABILITY_KEYS},
            "cost_total": 0,
            "delegation_count": 0,
            "error_classes": {},
            "model_families": ["gpt"],
            "retry_count": 0,
            "token_total": 0,
        },
        "method_revision": "3.27",
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
        assert "sudo -n true" in template
        assert "sandbox user retains noninteractive sudo" in template
    assert "configparser.ConfigParser" in (ROOT / "private_dot_config/dotfiles-ai/lima/mgm.yaml.tmpl").read_text()


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
    assert result["source_state"] is None
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


def test_federation_rejects_malformed_scalar_values() -> None:
    helper = load_helper()
    candidate = history_candidate(helper)
    assert helper._valid_candidate(candidate)
    assert helper._valid_candidate({**candidate, "method_revision": "unavailable"})
    for key, value in (
        ("context", "/etc/passwd"),
        ("context", "person@example.com"),
        ("context", "password=private"),
        ("database_digest", "not-a-digest"),
        ("session_id", "bad/session"),
        ("snapshot", True),
        ("snapshot", 1.5),
    ):
        malformed = json.loads(json.dumps(candidate))
        malformed[key] = value
        assert not helper._valid_candidate(malformed)

    for path, value in (
        (("query", "context"), "/etc/passwd"),
        (("query", "context"), "person@example.com"),
        (("query", "context"), "secret=value"),
        (("database_digest",), "bad"),
        (("session_ids",), ["bad/session"]),
        (("snapshot",), True),
        (("snapshot",), 1.5),
    ):
        page = history_page()
        target = page
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        with pytest.raises(ValueError):
            helper._source_page("host", json.dumps(page), 5, 0)


def test_command_stops_oversized_output(tmp_path: Path) -> None:
    helper = load_helper()
    noisy = tmp_path / "noisy"
    noisy.write_text("#!/bin/sh\ndd if=/dev/zero bs=300000 count=1 2>/dev/null\n")
    noisy.chmod(0o755)
    with pytest.raises(RuntimeError, match="output exceeded"):
        helper.command([str(noisy)])


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


def test_federation_binds_filters_to_continuation_and_manifest(tmp_path: Path) -> None:
    helper = load_helper()
    calls = []
    filters = {key: (False if key == "archive_only" else None) for key in helper.QUERY_KEYS}
    filters["context"] = "dotfiles_ai_distribution"

    def execute(argv, **_kwargs):
        calls.append(argv)
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "opencode-personal", "status": "Running"},
                {"name": "opencode-mgm", "status": "Running"},
            ])
        page = history_page()
        page["query"] = filters
        page["continuation"] = 5
        return json.dumps(page)

    first = helper.federated_review(config(tmp_path), 5, 0, execute=execute, filters=filters)
    assert all("--context" in call for call in calls if "review-history" in call)
    assert len(first["manifest_digest"]) == 64
    changed = {**filters, "context": "other_context"}
    with pytest.raises(ValueError, match="source state"):
        helper.federated_review(config(tmp_path), 5, 0, first["source_state"], execute=execute, filters=changed)


def test_federation_rejects_changed_continuation_identity(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "opencode-personal", "status": "Running"},
                {"name": "opencode-mgm", "status": "Running"},
            ])
        cursor = int(argv[argv.index("--cursor") + 1])
        page = {**history_page(), "cursor": cursor, "continuation": 5 if cursor == 0 else None}
        if cursor == 5:
            page["snapshot"] = 11
        return json.dumps(page)

    first = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    second = helper.federated_review(config(tmp_path), 5, 5, first["source_state"], execute=execute)
    assert all(source["availability"] == "invalid_output" for source in second["sources"])
    assert second["source_state"] is None


def test_unavailable_source_has_no_continuation_state(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([{"name": "opencode-mgm", "status": "Running"}])
        return json.dumps(history_page())

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert result["sources"][1]["availability"] == "missing_instance"
    assert result["source_state"] is None


def test_sources_page_independently_until_all_complete(tmp_path: Path) -> None:
    helper = load_helper()
    calls = []

    def execute(argv, **_kwargs):
        calls.append(argv)
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "opencode-personal", "status": "Running"},
                {"name": "opencode-mgm", "status": "Running"},
            ])
        source = "host" if argv[0] == "dbsctrctl" else argv[2].removeprefix("opencode-")
        cursor = int(argv[argv.index("--cursor") + 1])
        continuations = {"host": {0: None}, "personal": {0: 5, 5: None}, "mgm": {0: 5, 5: 10, 10: None}}
        return json.dumps({**history_page(), "cursor": cursor, "continuation": continuations[source][cursor]})

    first = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    second = helper.federated_review(config(tmp_path), 5, 0, first["source_state"], execute=execute)
    third = helper.federated_review(config(tmp_path), 5, 0, second["source_state"], execute=execute)
    assert [source["availability"] for source in second["sources"]] == ["complete", "available", "available"]
    assert [source["availability"] for source in third["sources"]] == ["complete", "complete", "available"]
    assert third["source_state"] is None
    assert sum(call[0] == "dbsctrctl" for call in calls) == 1


def test_status_reports_sparse_allocation(tmp_path: Path) -> None:
    helper = load_helper()
    instance = tmp_path / "opencode-personal"
    instance.mkdir()
    (instance / "disk").write_bytes(b"allocated")

    def execute(_argv, **_kwargs):
        return json.dumps([{"name": "opencode-personal", "status": "Running"}])

    result = helper.status_report(config(tmp_path), execute=execute, lima_root=tmp_path)
    assert result["host_free_bytes"] > 0
    assert result["clients"]["personal"]["running"] is True
    assert result["clients"]["personal"]["allocated_bytes"] > 0
    assert result["clients"]["mgm"]["allocated_bytes"] is None


def test_general_controller_exposes_no_handoff_command() -> None:
    body = SCRIPT.read_text()
    assert 'add_parser("handoff")' not in body
    assert "launch_handoff" not in body


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
