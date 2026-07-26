import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_sandbox-vm"


def load_helper():
    loader = importlib.machinery.SourceFileLoader("opencode_vm", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def config(tmp_path: Path) -> dict:
    return {
        "schema_version": 2,
        "enabled": True,
        "source": "https://github.com/example/dotfiles-ai.git",
        "template": str(tmp_path / "workspace.yaml"),
        "build_workspace": "workspace1",
        "resources": {"cpus": 4, "memory_gib": 8, "disk_gib": 60},
        "guest": {
            "bedrock_region": "us-west-2", "bedrock_profile": "", "default_model": "provider/model",
            "small_model": "provider/small", "theme": "default",
        },
        "workspaces": [
            {
                "name": "workspace1", "instance": "workspace1-sandbox", "federate": True,
                "mounts": [{
                    "host": str(tmp_path / "projects"), "guest": "/workspace/projects", "writable": True,
                    "protect_git_submodules": False, "reference_name": "", "reference_description": "", "reference_subpath": "",
                }],
            },
            {
                "name": "workspace2", "instance": "workspace2-sandbox", "federate": True,
                "mounts": [{
                    "host": str(tmp_path / "reference"), "guest": "/workspace/reference", "writable": True,
                    "protect_git_submodules": True, "reference_name": "project-reference",
                    "reference_description": "Project reference.", "reference_subpath": "",
                }],
            },
        ],
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
    template = (ROOT / "private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl").read_text()
    assert "template:_images/fedora-44" in template
    assert "template:fedora-44" not in template
    assert 'vmType: "vz"' in template
    assert 'arch: "aarch64"' in template
    assert 'disk: "{{ .dotfiles_ai.sandbox.disk_gib }}GiB"' in template
    assert "opencode-linux-arm64.tar.gz" in template
    assert "/usr/local/libexec/opencode --auto" in template
    assert "configparser.ConfigParser" in template
    assert "opencode-real" not in template
    assert "chmod 0750 /usr/bin/sudo" in template
    assert "sandbox user can execute sudo" in template
    assert "$6 ~ /\\.guest$/" in template
    assert template.count("grep -c .)\" -eq 1") == 2
    assert "opencode-sandbox-ready.service" in template
    assert "After=lima-guestagent.service" in template
    assert "rm -f /run/opencode-sandbox-ready" in template
    assert "touch /run/opencode-sandbox-ready" in template


def test_guest_identity_requires_exactly_one_generated_home() -> None:
    script = r'''agent_user="$(awk -F: '$6 ~ /\.guest$/ {print $1}')"
test -n "$agent_user"
test "$(printf '%s\n' "$agent_user" | grep -c .)" -eq 1'''
    one = "agent:x:503:1000::/home/agent.guest:/bin/bash\n"
    multiple = one + "other:x:504:1001::/home/other.guest:/bin/bash\n"
    assert subprocess.run(["sh", "-c", script], input=one, text=True).returncode == 0
    assert subprocess.run(["sh", "-c", script], input="", text=True).returncode != 0
    assert subprocess.run(["sh", "-c", script], input=multiple, text=True).returncode != 0


def test_workspace_paths_are_explicit_and_non_overlapping(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    for path in (tmp_path / "projects", tmp_path / "reference"):
        path.mkdir(parents=True)
    helper.validate_config(values)

    values["workspaces"][0]["mounts"].append({
        **values["workspaces"][0]["mounts"][0],
        "host": str(tmp_path / "projects/nested"),
        "guest": "/workspace/nested",
    })
    with pytest.raises(ValueError, match="overlap"):
        helper.validate_config(values)

    values = config(tmp_path)
    values["workspaces"][0]["mounts"][0]["guest"] = "/workspace/../escape"
    with pytest.raises(ValueError, match="mount path"):
        helper.validate_config(values)

    values = config(tmp_path)
    values["workspaces"][0]["mounts"][0].update({
        "reference_name": "project-reference", "reference_description": "Duplicate.",
    })
    with pytest.raises(ValueError, match="reference"):
        helper.validate_config(values)


def test_workspace_renderer_maps_access_and_protection(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    template = (ROOT / "private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl").read_text()
    template = (template.replace("{{ .dotfiles_ai.sandbox.cpus }}", "4")
                .replace("{{ .dotfiles_ai.sandbox.memory_gib }}", "8")
                .replace("{{ .dotfiles_ai.sandbox.disk_gib }}", "60"))
    rendered = helper.render_workspace(values, values["workspaces"][1], template)
    assert 'location: "' + str(tmp_path / "reference") + '"' in rendered
    assert 'mountPoint: "/workspace/reference"' in rendered
    assert "writable: true" in rendered
    assert '"protect_git_submodules":true' in rendered
    assert "@@" not in rendered
    path = tmp_path / "rendered.yaml"
    path.write_text(rendered)
    subprocess.run(["limactl", "validate", str(path)], check=True, capture_output=True, text=True)


def test_federation_namespaces_sources_and_restores_stopped_instances(tmp_path: Path) -> None:
    helper = load_helper()
    calls = []
    running = {"workspace1-sandbox": False, "workspace2-sandbox": True}

    def execute(argv, **kwargs):
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
            assert kwargs["timeout"] == 120
            return json.dumps(history_page())
        raise AssertionError(argv)

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert [source["source_id"] for source in result["sources"]] == ["host", "workspace1", "workspace2"]
    assert all(source["availability"] == "available" for source in result["sources"])
    assert len(result["manifest_digest"]) == 64
    assert result["source_state"] is None
    assert running == {"workspace1-sandbox": False, "workspace2-sandbox": True}
    assert ["limactl", "start", "workspace1-sandbox"] in calls
    assert ["limactl", "stop", "workspace1-sandbox"] in calls
    assert ["limactl", "stop", "workspace2-sandbox"] not in calls


def test_stop_failure_discards_source_continuation_state(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Stopped"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        if argv[:3] == ["limactl", "stop", "workspace1-sandbox"]:
            raise RuntimeError("stop failed")
        if argv[:2] == ["limactl", "start"]:
            return ""
        return json.dumps({**history_page(), "continuation": 5})

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert result["sources"][1] == {"source_id": "workspace1", "availability": "state_restore_failed"}
    assert result["source_state"] is None


def test_federation_rejects_unsafe_remote_output(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        if argv[:2] == ["dbsctrctl", "review-history"]:
            return json.dumps(history_page())
        return json.dumps({**history_page(), "leak": "/Users/private/key"})

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert result["sources"][1] == {
        "source_id": "workspace1",
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

    for count in (True, 1.5):
        malformed = json.loads(json.dumps(candidate))
        malformed["telemetry"]["error_classes"] = {"tool_error": count}
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
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
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
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
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
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
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
            return json.dumps([{"name": "workspace2-sandbox", "status": "Running"}])
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
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        source = "host" if argv[0] == "dbsctrctl" else argv[2].removesuffix("-sandbox")
        cursor = int(argv[argv.index("--cursor") + 1])
        continuations = {"host": {0: None}, "workspace1": {0: 5, 5: None}, "workspace2": {0: 5, 5: 10, 10: None}}
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
    instance = tmp_path / "workspace1-sandbox"
    instance.mkdir()
    (instance / "disk").write_bytes(b"allocated")

    def execute(_argv, **_kwargs):
        return json.dumps([{"name": "workspace1-sandbox", "status": "Running"}])

    result = helper.status_report(config(tmp_path), execute=execute, lima_root=tmp_path)
    assert result["host_free_bytes"] > 0
    assert result["workspaces"]["workspace1"]["running"] is True
    assert result["workspaces"]["workspace1"]["allocated_bytes"] > 0
    assert result["workspaces"]["workspace2"]["allocated_bytes"] is None


def test_general_controller_exposes_no_handoff_command() -> None:
    body = SCRIPT.read_text()
    assert 'add_parser("handoff")' not in body
    assert "launch_handoff" not in body
    assert '"render", "validate", "shell"' in body
    assert '["limactl", "validate", rendered.name]' in body


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


def test_controller_shell_resolves_workspace_instances() -> None:
    body = SCRIPT.read_text()
    assert 'os.environ.get("LIMA_TERM", "xterm-256color")' in body
    assert '["limactl", "shell", workspace["instance"]' in body
    assert not (ROOT / "dot_local/bin/executable_lmsh").exists()
