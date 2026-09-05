import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import tomllib
from unittest import mock

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
    (tmp_path / "state/lima").mkdir(parents=True, exist_ok=True)
    return {
        "schema_version": 9,
        "enabled": True,
        "source": "https://github.com/example/dotfiles-ai.git",
        "template": str(tmp_path / "workspace.yaml"),
        "build_workspace": "workspace1",
        "atuin_workspace": "",
        "pm_kernel": {
            "enabled": False, "workspace": "", "postgres_enabled": False,
            "postgres_image": "", "knowledge_postgres_enabled": False,
        },
        "state_root": str(tmp_path / "state"),
        "codex": {"channel": "stable"},
        "lima_home": str(tmp_path / "state/lima"),
        "tailscale": {"enabled": False, "ssh": False},
        "onepassword": {
            "enabled": True, "account": "example", "user_uuid": "USERUUID",
            "keychain_service": "op-service-account-token",
        },
        "resources": {"cpus": 4, "memory_gib": 8, "disk_gib": 60},
        "guest": {
            "default_model": "provider/model",
            "small_model": "provider/small", "theme": "catppuccin",
            "atuin_sync_address": "https://atuin.example.com", "hermes_enabled": True,
            "rnd_backend": "native",
            "rnd_runtime": "opencode",
            "vertex_project": "vertex-project", "vertex_location": "global",
            "vertex_account": "developer@example.com",
        },
        "workspaces": [
            {
                "name": "workspace1", "instance": "workspace1-sandbox", "shell_alias": "workspace1sh", "federate": True,
                "runtime": "codex",
                "mounts": [{
                    "host": str(tmp_path / "projects"), "guest": "/workspace/projects", "writable": True,
                    "protect_git_submodules": False, "reference_name": "", "reference_description": "", "reference_subpath": "",
                }],
            },
            {
                "name": "workspace2", "instance": "workspace2-sandbox", "shell_alias": "workspace2sh", "federate": True,
                "runtime": "",
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
        "capture_id": "d" * 24,
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
        "review_session": True,
        "correlation_quality": "exact",
        "cycles": [{"cycle_id": "DAI-007", "state": "active",
                    "context": "dotfiles_ai_distribution", "started_at": 1784900000000,
                    "ended_at": None}],
        "aggregates": {key: 0 for key in helper.AGGREGATE_KEYS},
        "telemetry": {
            "schema_version": 2,
            "approval_count": 0,
            "attribution_status": "exact",
            "availability": {key: "available" for key in helper.AVAILABILITY_KEYS},
            "cost_total": 0,
            "delegation_count": 0,
            "error_classes": {},
            "model_families": ["gpt"],
            "retry_count": 0,
            "token_total": 0,
            "provider_ids": ["openai"],
            "model_ids": ["gpt-5.6-sol"],
            "agent_ids": ["build-gpt"],
            "session_relation": "primary",
            "core_revisions": ["3.29"],
            "overlay_revisions": ["openai-2026-07-26"],
            "gate_failure_count": 0,
            "gate_reopen_count": 0,
            "remediation_round_count": 0,
        },
        "method_revision": "3.27",
    }


def lens_summary() -> dict:
    telemetry = {"page_count": 1, "session_count": 1, "review_session_count": 0,
                 "excluded_review_session_count": 0, "unattributed_session_count": 0}
    metric_names = {"approval_count", "candidate_count", "child_count", "cost_total",
                    "cycle_abandoned_count", "cycle_active_count", "cycle_blocked_count",
                    "cycle_completed_count", "cycle_count", "cycle_unknown_count", "delegation_count",
                    "elapsed_ms", "gate_failure_count", "gate_reopen_count", "provider_error_count",
                    "remediation_round_count", "retry_count", "token_total", "tool_call_count",
                    "tool_count", "tool_error_count"}
    metrics = {name: {"available_count": 1, "unavailable_count": 0,
                      "total": 0, "minimum": 0, "maximum": 0} for name in metric_names}
    metrics["cycle_count"].update(total=1, minimum=1, maximum=1)
    evidence_metrics = {name: 0 for name in metric_names}
    evidence_metrics["cycle_count"] = 1
    return {
        "schema_version": 1, "capture_id": "d" * 24, "lens": "performance_cost", "scope": "exclude",
        "snapshot": 10, "session_ceiling": 9, "part_ceiling": 8,
        "database_digest": "a" * 64, "exclusion_digest": "b" * 64,
        "query": history_page()["query"], "member_count": 1, "members_digest": "e" * 64,
        "telemetry": telemetry,
        "categories": {"cycle_state": {"active": 1}, "risk": {"unavailable": 1},
                       "delivery_intent": {"unavailable": 1}, "correlation_quality": {"exact": 1},
                       "reviewed_status": {"unreviewed": 1}, "session_relation": {"primary": 1}},
        "metrics": metrics,
        "evidence": [{"session_id": "session-1", "context": "dotfiles_ai_distribution",
                      "completed_at": "1784900000000", "correlation_quality": "exact",
                      "cycles": [{"cycle_id": "DAI-007", "state": "active"}],
                      "metrics": evidence_metrics, "signal_score": [1, 0, 0, 0]}],
    }


def capture_descriptor() -> dict:
    return {"schema_version": 1, "capture_id": "d" * 24, "created_at": int(time.time() * 1000),
            "query": history_page()["query"], "snapshot": 10, "session_ceiling": 9,
            "part_ceiling": 8, "database_digest": "a" * 64, "page_size": 25,
            "page_count": 1, "member_count": 1}


def test_fedora_templates_pin_runtime_and_sparse_disk(tmp_path: Path) -> None:
    helper = load_helper()
    assert helper.OPENCODE_VERSION == "1.18.25"
    assert helper.OPENCODE_SHA256 == "35ef77897425e41b5183a2c21ac4fb1d4d944d82a94e3c920f57b5490af11ac5"
    template = (ROOT / "private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl").read_text()
    rendered = helper.render_workspace(config(tmp_path), config(tmp_path)["workspaces"][0], template)
    assert "template:_images/fedora-44" in template
    assert "template:fedora-44" not in template
    assert 'vmType: "vz"' in template
    assert 'arch: "aarch64"' in template
    assert 'disk: "{{ .dotfiles_ai.sandbox.disk_gib }}GiB"' in template
    packages = template.split("dnf install -y", 1)[1].splitlines()[0].split()
    assert "podman" in packages
    assert "make" in packages
    assert f"/v{helper.OPENCODE_VERSION}/opencode-linux-arm64.tar.gz" in rendered
    assert helper.OPENCODE_SHA256 in rendered
    assert helper.OPENCODE_PROVISION_MARKER in rendered
    assert "/usr/local/libexec/opencode --auto" in template
    assert "configparser.ConfigParser" in template
    assert "opencode-real" not in template
    assert "chmod 4755 /usr/bin/sudo" in template
    assert "NOPASSWD: /usr/bin/cat /mnt/lima-cidata/param.env" in template
    assert "sandbox user has general sudo" in template
    assert "$6 ~ /\\.guest$/" in template
    assert template.count("grep -c .)\" -eq 1") == 2
    assert "opencode-sandbox-ready.service" in template
    assert "After=lima-guestagent.service" in template
    assert "rm -f /run/opencode-sandbox-ready" in template
    assert "touch /run/opencode-sandbox-ready" in template


def test_guest_config_sets_shared_visual_theme(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["workspaces"][0]["hermes_projects"] = True
    values["workspaces"][0]["hermes_backlog_roots"] = ["/workspace/projects/project-a"]
    rendered = helper.guest_config(values, values["workspaces"][0])
    parsed = tomllib.loads(rendered)

    assert parsed["data"]["machine_type"] == "guest"
    assert parsed["data"]["dotfiles_ai"]["opencode"]["theme"] == "catppuccin"
    assert parsed["data"]["dotfiles_ai"]["herdr"]["theme"] == "catppuccin"
    assert parsed["data"]["dotfiles_ai"]["atuin"]["sync_address"] == "https://atuin.example.com"
    assert parsed["data"]["dotfiles_ai"]["atuin"]["server_enabled"] is False
    assert parsed["data"]["dotfiles_ai"]["hermes"] == {
        "enabled": True, "executable": "~/.local/bin/hermes", "profile": "workspace1",
        "provider": "openai-codex", "backlog_roots": ["/workspace/projects/project-a"],
        "project_profiles": True,
    }
    assert parsed["data"]["dotfiles_ai"]["rnd"]["backend"] == "native"
    assert parsed["data"]["dotfiles_ai"]["rnd"]["runtime"] == "opencode"
    assert parsed["data"]["dotfiles_ai"]["codex"] == values["codex"]
    assert parsed["data"]["dotfiles_ai"]["sandbox"]["workspaces"][0]["runtime"] == "codex"
    assert parsed["data"]["dotfiles_ai"]["onepassword"] == {
        "enabled": True, "account": "example", "user_uuid": "USERUUID",
        "keychain_service": "op-service-account-token",
    }
    assert parsed["data"]["dotfiles_ai"]["opencode"]["vertex_project"] == "vertex-project"
    assert parsed["data"]["dotfiles_ai"]["opencode"]["vertex_account"] == "developer@example.com"
    assert parsed["data"]["dotfiles_ai"]["opencode"]["vertex_credentials"].endswith(
        "/.config/dotfiles-ai/gcloud-vertex/application_default_credentials.json"
    )

    values["workspaces"][0]["hermes_backlog_roots"] = ["/outside"]
    with pytest.raises(ValueError, match="Hermes backlog roots"):
        helper.validate_config(values)


def test_runtime_selector_migrates_and_resolves_without_worker_activation(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)

    assert helper.resolve_runtime(values, values["workspaces"][0]) == "codex"
    assert helper.resolve_runtime(values, values["workspaces"][1]) == "opencode"
    values["guest"]["rnd_runtime"] = "codex"
    assert helper.resolve_runtime(values, values["workspaces"][1]) == "codex"

    legacy = config(tmp_path)
    legacy["schema_version"] = 7
    legacy.pop("codex")
    legacy["guest"].pop("rnd_runtime")
    for workspace in legacy["workspaces"]:
        workspace.pop("runtime")
    helper.validate_config(legacy)
    assert legacy["schema_version"] == 9
    assert legacy["codex"] == {"channel": "stable"}
    assert legacy["guest"]["rnd_runtime"] == "opencode"
    assert all(workspace["runtime"] == "" for workspace in legacy["workspaces"])

    values = config(tmp_path)
    values["workspaces"][0]["runtime"] = "invalid"
    with pytest.raises(ValueError, match="workspace runtime"):
        helper.validate_config(values)


def test_update_refreshes_guest_config_before_apply(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["guest"]["hermes_enabled"] = True
    values["workspaces"][0]["hermes_projects"] = True
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[-2:] == ["printenv", "HOME"]:
            return "/home/agent.guest"
        return "true" if "podman" in argv else ""

    helper.update_workspace(values, values["workspaces"][0], execute=execute)

    assert calls[1][0][-4:] == ["podman", "info", "--format", "{{.Host.Security.Rootless}}"]
    assert [call[0][4] for call in calls[2:]] == ["sh", "git", "chezmoi", "sh"]
    rendered = tomllib.loads(calls[2][1]["input_data"].decode().replace("__GUEST_HOME__", "/home/agent.guest"))
    assert rendered["data"]["dotfiles_ai"]["hermes"]["enabled"] is True
    assert rendered["data"]["dotfiles_ai"]["hermes"]["project_profiles"] is True
    assert calls[3][0][-2:] == ["pull", "--ff-only"]
    assert calls[4][0][-1] == "apply"


def test_update_rejects_rootful_podman_before_guest_mutation(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    calls = []

    def execute(argv, **kwargs):
        calls.append(argv)
        return "/home/agent.guest" if argv[-2:] == ["printenv", "HOME"] else "false"

    with pytest.raises(RuntimeError, match="rootless Podman"):
        helper.update_workspace(values, values["workspaces"][0], execute=execute)

    assert len(calls) == 2


def test_codex_transaction_preserves_guest_state_and_forwards_private_request(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    workspace = values["workspaces"][0]
    running = False
    calls = []
    raw = json.dumps({"schema_version": 1, "release": "0.153.3"}).encode()

    def execute(argv, **kwargs):
        nonlocal running
        calls.append((argv, kwargs))
        if argv == ["limactl", "list", "--json"]:
            return json.dumps({"name": workspace["instance"],
                               "status": "Running" if running else "Stopped"})
        if argv[:2] == ["limactl", "start"]:
            running = True
            return ""
        if argv[:2] == ["limactl", "stop"]:
            running = False
            return ""
        if argv[:2] == ["limactl", "shell"]:
            if argv[-1] == "install-codex-updater":
                assert b"api.github.com/repos/openai/codex/releases/latest" in kwargs["input_data"]
                return ""
            assert kwargs["input_data"] == raw
            assert argv[-1].endswith("guest-stage")
            assert 'CODEX_HOME="$HOME/.local/state/dotfiles-ai/codex"' in argv[-1]
            return '{"status":"staged"}'
        raise AssertionError(argv)

    assert helper.codex_transaction(values, workspace, "stage", raw, execute) == \
        '{"status":"staged"}'
    assert running is False
    shell_scripts = [call[0][-1] for call in calls if call[0][:2] == ["limactl", "shell"]]
    assert shell_scripts[-1].endswith("guest-stage")


def test_update_can_apply_exact_temporary_source_without_changing_guest_checkout(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"archive")
    revision = "a" * 40
    monkeypatch.setenv("DOTFILES_AI_DEPLOY_SOURCE", str(tmp_path / "source"))
    monkeypatch.setattr(helper, "deployment_archive", lambda _source: (archive, revision))
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[-2:] == ["printenv", "HOME"]:
            return "/home/agent.guest"
        return "true" if "podman" in argv else ""

    helper.update_workspace(values, values["workspaces"][0], execute=execute)

    argv = [call[0] for call in calls]
    assert ["limactl", "copy", str(archive),
            f"workspace1-sandbox:/tmp/dotfiles-ai-{revision}.tar.gz"] in argv
    deployment = next(call for call in argv if "deploy-codex" in call)
    assert deployment[-3:] == [f"/tmp/dotfiles-ai-{revision}.tar.gz", revision, "full"]
    assert '"$HOME/.local/bin/codex-archive"' in deployment[-5]
    assert "apply --force" in deployment[-5]
    assert '"$HOME/.local/bin/dbsctrctl"' in deployment[-5]
    assert '"$HOME/.config/dotfiles-ai/codex-managed"' in deployment[-5]
    assert not any("pull" in call for call in argv)
    assert not archive.exists()


def test_update_can_deploy_only_exact_lifecycle_helper(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"archive")
    revision = "b" * 40
    monkeypatch.setenv("DOTFILES_AI_DEPLOY_SOURCE", str(tmp_path / "source"))
    monkeypatch.setenv("DOTFILES_AI_DEPLOY_HELPER_ONLY", "1")
    monkeypatch.setattr(helper, "deployment_archive", lambda _source: (archive, revision))
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[-2:] == ["printenv", "HOME"]:
            return "/home/agent.guest"
        return "true" if "podman" in argv else ""

    helper.update_workspace(values, values["workspaces"][0], execute=execute)

    argv = [call[0] for call in calls]
    deployment = next(call for call in argv if "deploy-codex" in call)
    assert deployment[-1] == "lifecycle"
    assert "apply --force" in deployment[-5]
    assert '"$HOME/.local/bin/dbsctrctl"' in deployment[-5]
    assert not any(call is not deployment and "codex-install" in call[-1] for call in argv)
    assert not archive.exists()


def test_update_can_bootstrap_only_rolling_codex_helpers(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"archive")
    monkeypatch.setenv("DOTFILES_AI_DEPLOY_SOURCE", str(tmp_path / "source"))
    monkeypatch.setenv("DOTFILES_AI_DEPLOY_CODEX_ROLLING", "1")
    monkeypatch.setattr(helper, "deployment_archive", lambda _source: (archive, "b" * 40))
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[-2:] == ["printenv", "HOME"]:
            return "/home/agent.guest"
        return "true" if "podman" in argv else ""

    helper.update_workspace(values, values["workspaces"][0], execute=execute)

    deployment = next(call[0] for call in calls if "deploy-codex" in call[0])
    assert deployment[-1] == "rolling"
    rolling = deployment[-5].split('if [ "$3" = rolling ]; then', 1)[1].split("exit 0", 1)[0]
    assert '"$HOME/.local/bin/codex-update-all"' in rolling
    assert '"$HOME/.config/dotfiles-ai/codex-managed"' not in rolling


def test_install_opencode_repairs_guest_and_restores_stopped_state(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    calls = []
    state = {"running": False, "provision": []}

    def execute(argv, **kwargs):
        calls.append(argv)
        if argv == ["limactl", "list", "--json"]:
            return json.dumps({"name": "workspace1-sandbox",
                               "status": "Running" if state["running"] else "Stopped",
                               "config": {"provision": state["provision"]}})
        if argv[:2] == ["limactl", "start"]:
            state["running"] = True
        elif argv[:2] == ["limactl", "stop"]:
            state["running"] = False
        elif argv[:2] == ["limactl", "edit"]:
            state["provision"] = [helper.OPENCODE_PROVISION]
        elif argv[-1:] == [helper.OPENCODE_PROBE]:
            return "missing"
        elif argv[-1:] == [helper.OPENCODE_VERIFY]:
            return helper.OPENCODE_VERSION
        return ""

    helper.install_opencode(values, values["workspaces"][0], execute=execute)

    assert ["limactl", "edit", "--yes", "--set", helper.OPENCODE_PROVISION_RULE,
            "workspace1-sandbox"] in calls
    assert state["running"] is False
    assert "sudo" not in " ".join(part for call in calls for part in call)


def test_update_all_preserves_mixed_states_and_reports_exact_parity(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    states = {"workspace1-sandbox": True, "workspace2-sandbox": False}
    installed = []
    updated = []

    def execute(argv, **kwargs):
        if argv == [helper.HOST_OPENCODE, "--version"]:
            return helper.OPENCODE_VERSION
        if argv == [helper.HOST_CODEX, "--version"]:
            return f"codex-cli {helper.CODEX_VERSION}"
        if argv == ["limactl", "list", "--json"]:
            return "\n".join(json.dumps({"name": name, "status": "Running" if running else "Stopped",
                                           "config": {}}) for name, running in states.items())
        if argv[:2] in (["limactl", "start"], ["limactl", "stop"]):
            states[argv[2]] = argv[1] == "start"
            return ""
        if argv[:4] == ["limactl", "shell", argv[2], "--"] and "codex" in argv[-1]:
            return f"codex-cli {helper.CODEX_VERSION}"
        if argv[:4] == ["limactl", "shell", argv[2], "--"]:
            return helper.OPENCODE_VERSION
        raise AssertionError(argv)

    def installer(config, workspace, execute):
        installed.append(workspace["name"])

    def updater(config, workspace, execute):
        assert states[workspace["instance"]]
        updated.append(workspace["name"])

    def snapshotter(workspace, execute):
        return workspace["name"]

    def restorer(workspace, token, execute):
        assert token == workspace["name"]

    def discarder(workspace, token, execute):
        assert token == workspace["name"]

    result = helper.update_all_workspaces(
        values, execute=execute, installer=installer, updater=updater,
        snapshotter=snapshotter, restorer=restorer, discarder=discarder)

    assert installed == updated == ["workspace1", "workspace2"]
    assert states == {"workspace1-sandbox": True, "workspace2-sandbox": False}
    assert result == {
        "host": helper.OPENCODE_VERSION,
        "workspaces": {"workspace1": helper.OPENCODE_VERSION,
                       "workspace2": helper.OPENCODE_VERSION},
        "codex": {"host": helper.CODEX_VERSION,
                  "workspaces": {"workspace1": helper.CODEX_VERSION,
                                 "workspace2": helper.CODEX_VERSION}},
    }

    def stale_host(argv, **kwargs):
        return "1.18.21" if argv == [helper.HOST_OPENCODE, "--version"] else execute(argv, **kwargs)

    with pytest.raises(RuntimeError, match="host OpenCode version mismatch"):
        helper.update_all_workspaces(
            values, execute=stale_host, installer=installer, updater=updater,
            snapshotter=snapshotter, restorer=restorer, discarder=discarder)

    installed.clear()
    updated.clear()
    monkeypatch.setattr(helper, "update_workspace", updater)
    helper.update_all_workspaces(
        values, execute=execute, installer=installer, snapshotter=snapshotter,
        restorer=restorer, discarder=discarder)
    assert installed == ["workspace1", "workspace2"]
    assert updated == ["workspace1", "workspace2"]


def test_update_all_rolls_back_prior_guests_when_second_guest_fails(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    states = {"workspace1-sandbox": True, "workspace2-sandbox": False}
    restored = []
    discarded = []

    def execute(argv, **kwargs):
        if argv == [helper.HOST_OPENCODE, "--version"]:
            return helper.OPENCODE_VERSION
        if argv == [helper.HOST_CODEX, "--version"]:
            return f"codex-cli {helper.CODEX_VERSION}"
        if argv == ["limactl", "list", "--json"]:
            return "\n".join(json.dumps({"name": name, "status": "Running" if running else "Stopped",
                                            "config": {}}) for name, running in states.items())
        if argv[:2] in (["limactl", "start"], ["limactl", "stop"]):
            states[argv[2]] = argv[1] == "start"
            return ""
        if argv[:4] == ["limactl", "shell", argv[2], "--"] and "codex" in argv[-1]:
            return f"codex-cli {helper.CODEX_VERSION}"
        if argv[:4] == ["limactl", "shell", argv[2], "--"]:
            return helper.OPENCODE_VERSION
        raise AssertionError(argv)

    def installer(config, workspace, execute):
        pass

    def updater(config, workspace, execute):
        if workspace["name"] == "workspace2":
            raise RuntimeError("second guest failed")

    def snapshotter(workspace, execute):
        return workspace["name"]

    def restorer(workspace, token, execute):
        restored.append((workspace["name"], token))

    def discarder(workspace, token, execute):
        discarded.append((workspace["name"], token))

    with pytest.raises(RuntimeError, match="second guest failed"):
        helper.update_all_workspaces(
            values, execute=execute, installer=installer, updater=updater,
            snapshotter=snapshotter, restorer=restorer, discarder=discarder)

    assert restored == [("workspace2", "workspace2"), ("workspace1", "workspace1")]
    assert discarded == []
    assert states == {"workspace1-sandbox": True, "workspace2-sandbox": False}


def test_parity_restores_stopped_guest_and_rejects_stale_version(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    workspace = values["workspaces"][0]
    running = False
    guest = helper.OPENCODE_VERSION

    def execute(argv, **_kwargs):
        nonlocal running
        if argv == [helper.HOST_OPENCODE, "--version"]:
            return helper.OPENCODE_VERSION
        if argv[:2] == ["limactl", "list"]:
            return json.dumps({"name": workspace["instance"], "status": "Running" if running else "Stopped"})
        if argv[:2] in (["limactl", "start"], ["limactl", "stop"]):
            running = argv[1] == "start"
            return ""
        if argv[:2] == ["limactl", "shell"]:
            return guest
        raise AssertionError(argv)

    assert helper.verify_opencode_parity(values, workspace, execute) == {
        "host": helper.OPENCODE_VERSION, "guest": helper.OPENCODE_VERSION,
        "instance": workspace["instance"]}
    assert not running
    guest = "1.18.21"
    with pytest.raises(RuntimeError, match="workspace1 OpenCode version mismatch"):
        helper.verify_opencode_parity(values, workspace, execute)
    assert not running


def test_codex_version_parity_restores_stopped_guest_and_rejects_stale_version(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    workspace = values["workspaces"][0]
    running = False
    guest = f"codex-cli {helper.CODEX_VERSION}"

    def execute(argv, **_kwargs):
        nonlocal running
        if argv == [helper.HOST_CODEX, "--version"]:
            return f"codex-cli {helper.CODEX_VERSION}"
        if argv[:2] == ["limactl", "list"]:
            return json.dumps({"name": workspace["instance"], "status": "Running" if running else "Stopped"})
        if argv[:2] in (["limactl", "start"], ["limactl", "stop"]):
            running = argv[1] == "start"
            return ""
        if argv[:2] == ["limactl", "shell"]:
            return guest
        raise AssertionError(argv)

    assert helper.verify_codex_version_parity(values, workspace, execute) == {
        "host": helper.CODEX_VERSION, "guest": helper.CODEX_VERSION,
        "instance": workspace["instance"]}
    assert not running
    guest = "codex-cli 0.150.0"
    with pytest.raises(RuntimeError, match="workspace1 Codex version mismatch"):
        helper.verify_codex_version_parity(values, workspace, execute)
    assert not running


def test_install_make_reprovisions_existing_guest_without_widening_sudo(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    calls = []
    state = {"running": True, "provision": []}

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv == ["limactl", "list", "--json"]:
            return json.dumps({"name": "workspace1-sandbox",
                               "status": "Running" if state["running"] else "Stopped",
                               "config": {"provision": state["provision"]}})
        if argv[:2] == ["limactl", "stop"]:
            state["running"] = False
        elif argv[:2] == ["limactl", "start"]:
            state["running"] = True
        elif argv[-1:] == [helper.MAKE_PROBE]:
            return "missing"
        elif argv[-1:] == [helper.MAKE_VERIFY]:
            return "GNU Make 4.4.1"
        return ""

    helper.install_make(values, values["workspaces"][0], execute=execute)

    argv = [call[0] for call in calls]
    assert ["limactl", "edit", "--yes", "--set", helper.MAKE_PROVISION_RULE, "workspace1-sandbox"] in argv
    assert ["limactl", "shell", "workspace1-sandbox", "--", "sh", "-ceu", helper.MAKE_VERIFY] in argv
    assert state["running"] is True
    assert "sudo" not in " ".join(part for call, _ in calls for part in call)


def test_install_make_preserves_stopped_guest_state_when_already_available(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    calls = []
    state = {"running": False}

    def execute(argv, **kwargs):
        calls.append(argv)
        if argv == ["limactl", "list", "--json"]:
            return json.dumps({"name": "workspace1-sandbox",
                               "status": "Running" if state["running"] else "Stopped", "config": {}})
        if argv[:2] == ["limactl", "start"]:
            state["running"] = True
        elif argv[:2] == ["limactl", "stop"]:
            state["running"] = False
        elif argv[-1:] == [helper.MAKE_PROBE]:
            return "present"
        return ""

    helper.install_make(values, values["workspaces"][0], execute=execute)

    assert state["running"] is False
    assert not any(call[:2] == ["limactl", "edit"] for call in calls)


def test_install_make_reuses_owned_provision_after_partial_failure(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    calls = []
    state = {"running": True}

    def execute(argv, **kwargs):
        calls.append(argv)
        if argv == ["limactl", "list", "--json"]:
            return json.dumps({"name": "workspace1-sandbox",
                               "status": "Running" if state["running"] else "Stopped",
                               "config": {"provision": [helper.MAKE_PROVISION]}})
        if argv[:2] == ["limactl", "start"]:
            state["running"] = True
        elif argv[:2] == ["limactl", "stop"]:
            state["running"] = False
        elif argv[-1:] == [helper.MAKE_PROBE]:
            return "missing"
        return "GNU Make 4.4.1" if argv[-1:] == [helper.MAKE_VERIFY] else ""

    helper.install_make(values, values["workspaces"][0], execute=execute)

    assert not any(call[:2] == ["limactl", "edit"] for call in calls)
    assert state["running"] is True


def test_install_make_restores_stopped_state_after_timed_out_provision_start(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    state = {"running": False, "starts": 0}

    def execute(argv, **kwargs):
        if argv == ["limactl", "list", "--json"]:
            return json.dumps({"name": "workspace1-sandbox",
                               "status": "Running" if state["running"] else "Stopped",
                               "config": {"provision": []}})
        if argv[:2] == ["limactl", "start"]:
            state["starts"] += 1
            state["running"] = True
            if state["starts"] == 2:
                raise RuntimeError("start timed out after the VM reached running")
        elif argv[:2] == ["limactl", "stop"]:
            state["running"] = False
        elif argv[-1:] == [helper.MAKE_PROBE]:
            return "missing"
        return ""

    with pytest.raises(RuntimeError, match="start timed out"):
        helper.install_make(values, values["workspaces"][0], execute=execute)

    assert state["running"] is False


def test_install_make_restores_stopped_state_after_timed_out_probe_start(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    state = {"running": False}

    def execute(argv, **kwargs):
        if argv == ["limactl", "list", "--json"]:
            return json.dumps({"name": "workspace1-sandbox",
                               "status": "Running" if state["running"] else "Stopped",
                               "config": {"provision": []}})
        if argv[:2] == ["limactl", "start"]:
            state["running"] = True
            raise RuntimeError("probe start timed out after the VM reached running")
        if argv[:2] == ["limactl", "stop"]:
            state["running"] = False
        return ""

    with pytest.raises(RuntimeError, match="probe start timed out"):
        helper.install_make(values, values["workspaces"][0], execute=execute)

    assert state["running"] is False


def test_old_schema_is_normalized_for_ordered_host_migration(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["schema_version"] = 4
    del values["onepassword"]
    for key in ("vertex_project", "vertex_location", "vertex_account"):
        del values["guest"][key]

    helper.validate_config(values)

    assert values["schema_version"] == 9
    assert values["onepassword"]["enabled"] is False
    assert values["guest"]["vertex_location"] == "global"
    assert values["pm_kernel"]["enabled"] is False
    assert values["pm_kernel"]["knowledge_postgres_enabled"] is False


def test_guest_config_rejects_insecure_atuin_sync_address(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["guest"]["atuin_sync_address"] = "http://atuin.example.com"

    with pytest.raises(ValueError, match="invalid guest Atuin sync address"):
        helper.validate_config(values)


def test_atuin_server_selects_one_workspace_and_private_forward(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["atuin_workspace"] = "workspace1"
    template = (ROOT / "private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl").read_text()
    template = (template.replace("{{ .dotfiles_ai.sandbox.cpus }}", "4")
                .replace("{{ .dotfiles_ai.sandbox.memory_gib }}", "8")
                .replace("{{ .dotfiles_ai.sandbox.disk_gib }}", "60"))

    helper.validate_config(values)
    personal = helper.render_workspace(values, values["workspaces"][0], template)
    client = helper.render_workspace(values, values["workspaces"][1], template)
    personal_config = tomllib.loads(helper.guest_config(values, values["workspaces"][0]))
    client_config = tomllib.loads(helper.guest_config(values, values["workspaces"][1]))

    assert 'hostIP: "127.0.0.1"' in personal
    assert 'guestIP: "127.0.0.1"' in personal
    assert "hostPort: 8889" in personal
    assert "guestPort: 8888" in personal
    assert "hostPort: 8889" not in client
    assert personal_config["data"]["dotfiles_ai"]["atuin"]["server_enabled"] is True
    assert client_config["data"]["dotfiles_ai"]["atuin"]["server_enabled"] is False

    values["atuin_workspace"] = "missing"
    with pytest.raises(ValueError, match="Atuin workspace"):
        helper.validate_config(values)

    values["atuin_workspace"] = "workspace1"
    values["state_root"] = ""
    with pytest.raises(ValueError, match="guarded Lima home"):
        helper.validate_config(values)

    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "state/escaped"
    link.symlink_to(outside, target_is_directory=True)
    values["state_root"] = str(tmp_path / "state")
    values["lima_home"] = str(link)
    with pytest.raises(ValueError, match="guarded Lima home"):
        helper.validate_config(values)


def test_tailscale_config_is_exact_and_default_off(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    helper.validate_config(values)

    values["tailscale"]["auth_key"] = "must-not-render"
    with pytest.raises(ValueError, match="invalid Tailscale settings"):
        helper.validate_config(values)


def test_missing_tailscale_config_inherits_disabled_defaults(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    del values["tailscale"]

    helper.validate_config(values)
    assert values["tailscale"] == {"enabled": False, "ssh": False}


def test_tailscale_enrollment_installs_then_streams_one_key(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["tailscale"] = {"enabled": True, "ssh": True}
    key = b"tskey-auth-" + b"x" * 32
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        return ""

    helper.tailscale_enroll(values, values["workspaces"][0], io.BytesIO(key + b"\n"), execute=execute)

    install, enroll = calls
    assert install[0][:6] == ["limactl", "shell", "workspace1-sandbox", "--", "sh", "-ceu"]
    assert "tailscale_1.98.9_arm64.tgz" in install[0][-1]
    assert "fa554ee808d7d07ee8e3ebbc0215ea087157e2a0abbf408e6e18ea7532554db6" in install[0][-1]
    assert "--tun=userspace-networking" in install[0][-1]
    assert "--retry 3 --retry-all-errors --connect-timeout 10 --max-time 120" in install[0][-1]
    assert ".tailscale.new" in install[0][-1]
    assert 'mv -f "$HOME/.local/bin/.tailscaled.new"' in install[0][-1]
    assert "systemctl --user restart" in install[0][-1]
    assert "Linger" in install[0][-1]
    assert "sudo" not in install[0][-1]
    assert enroll[0][:6] == ["limactl", "shell", "workspace1-sandbox", "--", "sh", "-ceu"]
    assert "--auth-key=file:/dev/stdin" in enroll[0][-1]
    assert "--ssh" in enroll[0][-1]
    assert enroll[1]["input_data"] == key + b"\n"
    assert all(key.decode() not in " ".join(argv) for argv, _ in calls)

    helper.tailscale_enroll(values, values["workspaces"][0], io.BytesIO(key), execute=execute)
    assert calls[2][0][-1] == install[0][-1]


def test_tailscale_enrollment_leaves_ssh_off_when_disabled(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["tailscale"] = {"enabled": True, "ssh": False}
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        return ""

    helper.tailscale_enroll(
        values, values["workspaces"][0], io.BytesIO(b"tskey-auth-" + b"x" * 32),
        execute=execute,
    )

    assert "--auth-key=file:/dev/stdin" in calls[-1][0][-1]
    assert "--ssh" not in calls[-1][0][-1]


@pytest.mark.parametrize("key", [b"", b"not-an-auth-key", b"tskey-auth-" + b"x" * 1014])
def test_tailscale_enrollment_rejects_bad_key_before_changes(tmp_path: Path, key: bytes) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["tailscale"] = {"enabled": True, "ssh": True}
    calls = []

    with pytest.raises(ValueError, match="invalid Tailscale auth key"):
        helper.tailscale_enroll(values, values["workspaces"][0], io.BytesIO(key), execute=lambda *args, **kwargs: calls.append((args, kwargs)))
    assert calls == []


def test_tailscale_enrollment_requires_explicit_opt_in(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)

    with pytest.raises(ValueError, match="Tailscale is disabled"):
        helper.tailscale_enroll(values, values["workspaces"][0], io.BytesIO(b"tskey-auth-" + b"x" * 32))


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


def test_lima_home_is_optional_absolute_machine_data(tmp_path: Path, capsys) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["lima_home"] = "relative/lima"
    with pytest.raises(ValueError, match="Lima home"):
        helper.validate_config(values)

    values["lima_home"] = str(tmp_path / "lima")
    helper.load_config = lambda: values
    with mock.patch.dict(os.environ, {}, clear=True):
        helper.main(["build-workspace"], "sandbox-vm")
        assert os.environ["LIMA_HOME"] == values["lima_home"]
    assert capsys.readouterr().out.strip() == "workspace1"

    values["lima_home"] = ""
    with mock.patch.dict(os.environ, {"LIMA_HOME": "/inherited"}, clear=True):
        helper.main(["build-workspace"], "sandbox-vm")
        assert os.environ["LIMA_HOME"] == "/inherited"


def test_workspace_aliases_are_unique_and_cannot_shadow_controller(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["workspaces"][1]["shell_alias"] = "workspace1sh"
    with pytest.raises(ValueError, match="alias"):
        helper.validate_config(values)

    values = config(tmp_path)
    values["workspaces"][0]["shell_alias"] = "sandbox-vm"
    with pytest.raises(ValueError, match="alias"):
        helper.validate_config(values)


def test_alias_invocation_enters_workspace_and_preserves_arguments(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    invoked = []
    monkeypatch.setattr(helper, "load_config", lambda: values)
    monkeypatch.setattr(helper, "service_token", lambda *_args, **_kwargs: "ops_test")
    monkeypatch.setattr(helper.os, "execvpe", lambda file, argv, env: invoked.append((file, argv, env)))

    helper.main(["--", "pwd"], invocation="workspace1sh")

    assert invoked[0][0:2] == (
        "limactl", ["limactl", "shell", "--preserve-env", "workspace1-sandbox", "pwd"])
    assert invoked[0][2]["TERM"] == os.environ.get("LIMA_TERM", "xterm-256color")
    assert invoked[0][2]["OP_SERVICE_ACCOUNT_TOKEN"] == "ops_test"
    assert "AWS_SECRET_ACCESS_KEY" not in invoked[0][2]


def test_service_token_is_validated_without_entering_argv(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        return "ops_test" if argv[0] == "/usr/bin/security" else ""

    assert helper.service_token(values, execute=execute) == "ops_test"
    assert calls[0][0] == [
        "/usr/bin/security", "find-generic-password", "-s",
        "op-service-account-token", "-a", "example", "-w",
    ]
    assert calls[1][0] == ["op", "vault", "list"]
    assert calls[1][1]["environment"]["OP_SERVICE_ACCOUNT_TOKEN"] == "ops_test"
    assert all("ops_test" not in argv for argv, _ in calls)


def test_controller_starts_and_stops_only_configured_workspace(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    calls = []
    locks = []
    running = False
    monkeypatch.setattr(helper, "load_config", lambda: values)
    def execute(argv, timeout=30, input_data=None):
        nonlocal running
        calls.append((argv, timeout))
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([{"name": "workspace1-sandbox", "status": "Running" if running else "Stopped"}])
        running = argv[1] == "start"
        return ""
    monkeypatch.setattr(helper, "command", execute)
    class Lock:
        def __enter__(self):
            locks.append("enter")

        def __exit__(self, *_args):
            locks.append("exit")
    monkeypatch.setattr(helper, "_instance_lock", lambda root, instance: Lock())

    helper.main(["start", "workspace1"], invocation="sandbox-vm")
    helper.main(["start", "workspace1"], invocation="sandbox-vm")
    helper.main(["stop", "workspace1"], invocation="sandbox-vm")
    helper.main(["stop", "workspace1"], invocation="sandbox-vm")

    assert calls == [
        (["limactl", "list", "--json"], 30),
        (["limactl", "start", "workspace1-sandbox"], 120),
        (["limactl", "list", "--json"], 30),
        (["limactl", "list", "--json"], 30),
        (["limactl", "stop", "workspace1-sandbox"], 120),
        (["limactl", "list", "--json"], 30),
    ]
    assert locks == ["enter", "exit"] * 4


def test_configure_atuin_restarts_selected_existing_workspace(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["atuin_workspace"] = "workspace1"
    calls = []

    def execute(argv, timeout=30, input_data=None):
        calls.append((argv, timeout))
        if argv[:2] == ["limactl", "list"]:
            return "\n".join(json.dumps(row) for row in [
                {"name": "workspace1-sandbox", "status": "Running", "config": {}},
                {"name": "workspace2-sandbox", "status": "Stopped", "config": {}},
            ])
        return ""

    monkeypatch.setattr(helper, "_instance_lock", lambda *_args: mock.MagicMock())

    helper.configure_atuin(values, execute=execute, state_path=tmp_path / "atuin-workspace")

    assert calls[1] == (["limactl", "stop", "workspace1-sandbox"], 120)
    assert calls[2][0][:5] == ["limactl", "edit", "--yes", "--set", helper.atuin_port_rule([])]
    assert calls[2][0][-1] == "workspace1-sandbox"
    assert calls[3] == (["limactl", "start", "workspace1-sandbox"], 120)


def test_configure_atuin_requires_old_forward_removal(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["atuin_workspace"] = "workspace2"
    state = tmp_path / "atuin-workspace"
    state.write_text("workspace1\n")

    with pytest.raises(ValueError, match="remove the prior"):
        helper.configure_atuin(values, execute=lambda *_args, **_kwargs: "", state_path=state)

    calls = []
    other = {"guestPort": 3000, "hostPort": 3000, "hostIP": "127.0.0.1"}
    def execute(argv, **_kwargs):
        calls.append(argv)
        if argv[-2:] == ["printenv", "HOME"]:
            return "/home/agent.guest"
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([{
                "name": "workspace1-sandbox", "status": "Stopped",
                "config": {"portForwards": [other, helper.ATUIN_PORT_FORWARD | {"proto": "tcp"}]},
            }])
        if "podman" in argv:
            return "true"
        return ""
    helper.configure_atuin(
        values,
        remove=True,
        execute=execute,
        state_path=state,
    )
    edit = next(argv for argv in calls if argv[:2] == ["limactl", "edit"])
    assert edit[4] == helper.atuin_port_rule([other, helper.ATUIN_PORT_FORWARD | {"proto": "tcp"}], remove=True)
    assert json.loads(edit[4].split("=", 1)[1]) == [other]
    assert not state.exists()


def test_pm_postgres_selects_workspace_forward_and_guest_service(tmp_path: Path) -> None:
    helper = load_helper()
    values = config(tmp_path)
    image = "docker.io/library/postgres:19beta3@sha256:" + "a" * 64
    values["pm_kernel"] = {
        "enabled": True, "workspace": "workspace1", "postgres_enabled": True,
        "postgres_image": image, "knowledge_postgres_enabled": True,
    }
    template = (ROOT / "private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl").read_text()
    template = (template.replace("{{ .dotfiles_ai.sandbox.cpus }}", "4")
                .replace("{{ .dotfiles_ai.sandbox.memory_gib }}", "8")
                .replace("{{ .dotfiles_ai.sandbox.disk_gib }}", "60"))

    helper.validate_config(values)
    selected = helper.render_workspace(values, values["workspaces"][0], template)
    other = helper.render_workspace(values, values["workspaces"][1], template)
    guest = tomllib.loads(helper.guest_config(values, values["workspaces"][0]))

    assert "hostPort: 55432" not in selected
    assert "hostPort: 55432" not in other
    assert guest["data"]["dotfiles_ai"]["pm_kernel"] == {
        "enabled": True, "workspace": "", "postgres_enabled": True,
        "postgres_image": image, "postgres_password_ref": "", "postgres_backup_dir": "",
        "jira_adapter": "fake", "jira_project": "", "jira_issue_types": [],
    }
    assert guest["data"]["dotfiles_ai"]["knowledge_store"] == {
        "enabled": True, "postgres_enabled": True,
    }


def test_configure_and_provision_pm_postgres_are_private(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["pm_kernel"].update({"enabled": True, "workspace": "workspace1", "postgres_enabled": True,
                                "postgres_image": "docker.io/library/postgres:19beta3@sha256:" + "a" * 64})
    calls = []

    def execute(argv, timeout=30, input_data=None):
        calls.append((argv, timeout, input_data))
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([{"name": "workspace1-sandbox", "status": "Running", "config": {}}])
        return ""

    monkeypatch.setattr(helper, "_instance_lock", lambda *_args: mock.MagicMock())
    helper.configure_pm_postgres(values, execute=execute, state_path=tmp_path / "pm-workspace")
    assert calls[2][0][:5] == ["limactl", "edit", "--yes", "--set", helper.pm_postgres_port_rule([])]

    calls.clear()
    password = b"a-private-password-with-32-bytes"
    helper.provision_pm_postgres(values, io.BytesIO(password + b"\n"), execute=execute)
    assert calls == [([
        "limactl", "shell", "workspace1-sandbox", "--", "podman", "secret", "create",
        "--replace", "pm-postgres-password", "-",
    ], 120, password)]


def test_pm_postgres_does_not_adopt_unowned_forward(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    values = config(tmp_path)
    values["pm_kernel"].update({"enabled": True, "workspace": "workspace1", "postgres_enabled": True,
                                "postgres_image": "docker.io/library/postgres:19beta3@sha256:" + "a" * 64})
    monkeypatch.setattr(helper, "_instance_lock", lambda *_args: mock.MagicMock())

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([{"name": "workspace1-sandbox", "status": "Running",
                                "config": {"portForwards": [helper.PM_POSTGRES_PORT_FORWARD]}}])
        return ""

    with pytest.raises(ValueError, match="no ownership state"):
        helper.configure_pm_postgres(values, execute=execute, state_path=tmp_path / "missing-state")
    values["pm_kernel"]["workspace"] = ""
    with pytest.raises(ValueError, match="ownership state is unavailable"):
        helper.configure_pm_postgres(values, remove=True, execute=execute,
                                     state_path=tmp_path / "missing-state")


def rendered_workspace(tmp_path: Path) -> tuple[str, Path]:
    helper = load_helper()
    values = config(tmp_path)
    template = (ROOT / "private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl").read_text()
    template = (template.replace("{{ .dotfiles_ai.sandbox.cpus }}", "4")
                .replace("{{ .dotfiles_ai.sandbox.memory_gib }}", "8")
                .replace("{{ .dotfiles_ai.sandbox.disk_gib }}", "60"))
    rendered = helper.render_workspace(values, values["workspaces"][1], template)
    path = tmp_path / "rendered.yaml"
    path.write_text(rendered)
    return rendered, path


def test_workspace_renderer_maps_access_and_protection(tmp_path: Path) -> None:
    rendered, _ = rendered_workspace(tmp_path)
    assert 'location: "' + str(tmp_path / "reference") + '"' in rendered
    assert 'mountPoint: "/workspace/reference"' in rendered
    assert "writable: true" in rendered
    assert '"protect_git_submodules":true' in rendered
    assert "@@" not in rendered


@pytest.mark.skipif(shutil.which("limactl") is None, reason="limactl is unavailable")
def test_workspace_renderer_passes_lima_validation(tmp_path: Path) -> None:
    _, path = rendered_workspace(tmp_path)
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
            assert kwargs["timeout"] == 120
            return json.dumps(history_page())
        if argv[:2] == ["dbsctrctl", "review-history"]:
            assert kwargs["timeout"] == 900
            return json.dumps(history_page())
        raise AssertionError(argv)

    result = helper.federated_review(
        config(tmp_path), 5, 0, execute=execute,
        excluded_session_id="session-current", excluded_message_id="message-current",
    )
    assert [source["source_id"] for source in result["sources"]] == ["host", "workspace1", "workspace2"]
    assert all(source["availability"] == "available" for source in result["sources"])
    assert len(result["manifest_digest"]) == 64
    assert result["source_state"] is None
    assert running == {"workspace1-sandbox": False, "workspace2-sandbox": True}
    assert ["limactl", "start", "workspace1-sandbox"] in calls
    assert ["limactl", "stop", "workspace1-sandbox"] in calls
    assert ["limactl", "stop", "workspace2-sandbox"] not in calls
    host = next(call for call in calls if call[:2] == ["dbsctrctl", "review-history"])
    guests = [call for call in calls if call[:2] == ["limactl", "shell"]]
    assert host[host.index("--excluded-session-id") + 1] == "session-current"
    assert host[host.index("--excluded-message-id") + 1] == "message-current"
    assert all("--excluded-session-id" not in call and "--excluded-message-id" not in call for call in guests)


def test_federation_collects_sources_concurrently_in_configured_order(tmp_path: Path) -> None:
    helper = load_helper()
    barrier = threading.Barrier(3, timeout=1)
    lock = threading.Lock()
    active = 0
    peak = 0

    def execute(argv, **kwargs):
        nonlocal active, peak
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        assert kwargs["timeout"] == (900 if argv[:2] == ["dbsctrctl", "review-history"] else 120)
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            barrier.wait()
            return json.dumps(history_page())
        finally:
            with lock:
                active -= 1

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert peak == 3
    assert [source["source_id"] for source in result["sources"]] == ["host", "workspace1", "workspace2"]
    assert all(source["availability"] == "available" for source in result["sources"])


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
    assert helper._valid_candidate({**candidate, "project_digest": "unavailable"})
    for key, value in (
        ("context", "/etc/passwd"),
        ("context", "person@example.com"),
        ("context", "password=private"),
        ("database_digest", "not-a-digest"),
        ("project_digest", "not-a-digest"),
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


def test_privacy_epochs_preserve_source_order(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        return json.dumps({"schema_version": 1, "privacy_epoch_digest": "a" * 64})

    result = helper.privacy_epochs(config(tmp_path), execute)
    assert [source["source_id"] for source in result["sources"]] == ["host", "workspace1", "workspace2"]
    assert all(source["availability"] == "available" for source in result["sources"])


def test_command_stops_oversized_output(tmp_path: Path, monkeypatch) -> None:
    helper = load_helper()
    monkeypatch.setattr(helper.os, "killpg", mock.Mock(side_effect=PermissionError))
    noisy = tmp_path / "noisy"
    noisy.write_text("#!/bin/sh\ndd if=/dev/zero bs=300000 count=1 2>/dev/null\nsleep 30\n")
    noisy.chmod(0o755)
    with pytest.raises(RuntimeError, match="output exceeded"):
        helper.command([str(noisy)])
    assert helper.os.killpg.called


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
    assert continuation[continuation.index("--capture-id") + 1] == "d" * 24


def test_federated_lens_summary_exhausts_captures_server_side(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        if "history-capture-latest" in argv:
            return json.dumps(capture_descriptor())
        if "history-capture" in argv:
            return json.dumps(lens_summary())
        return json.dumps({**history_page(), "limit": 25})

    result = helper.federated_lens_summary(
        config(tmp_path), "performance_cost", "exclude", execute=execute)
    assert result["telemetry"] == {
        "page_count": 3, "session_count": 3, "review_session_count": 0,
        "excluded_review_session_count": 0, "unattributed_session_count": 0,
        "source_count": 3,
    }
    assert [source["source_id"] for source in result["sources"]] == ["host", "workspace1", "workspace2"]
    assert result["sources"][1]["summary"]["evidence"][0]["session_id"] == "workspace1:session-1"
    assert len(result["manifest_digest"]) == 64
    stale = lens_summary()
    stale["capture_id"] = "f" * 24
    with pytest.raises(ValueError, match="invalid lens summary"):
        helper._validated_lens_summary(json.dumps(stale), "performance_cost", "exclude",
                                       history_page()["query"], "d" * 24)
    unsafe = lens_summary()
    unsafe["metrics"]["password"] = unsafe["metrics"].pop("cost_total")
    with pytest.raises(ValueError, match="invalid lens summary"):
        helper._validated_lens_summary(json.dumps(unsafe), "performance_cost", "exclude",
                                       history_page()["query"], "d" * 24)
    for mutation in (
        lambda value: value.update(lens="correctness_safety"),
        lambda value: value["categories"]["reviewed_status"].update(password=1),
        lambda value: [value["categories"][name].clear()
                       for name in ("cycle_state", "risk", "delivery_intent")],
        lambda value: value["evidence"][0].update(extra=1),
        lambda value: value["evidence"][0]["cycles"][0].update(extra=1),
    ):
        malformed = lens_summary()
        mutation(malformed)
        with pytest.raises(ValueError, match="invalid lens summary"):
            helper._validated_lens_summary(json.dumps(malformed), "performance_cost", "exclude",
                                           history_page()["query"], "d" * 24)


def test_federation_captures_once_then_pages_immutable_history(tmp_path: Path) -> None:
    helper = load_helper()
    calls = []

    def execute(argv, **_kwargs):
        calls.append(argv)
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        cursor = int(argv[argv.index("--cursor") + 1])
        return json.dumps({**history_page(), "cursor": cursor, "continuation": 5 if cursor == 0 else None})

    first = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert all(state["capture_id"] == "d" * 24 for state in first["source_state"])
    helper.federated_review(config(tmp_path), 5, 0, first["source_state"], execute=execute)
    history_calls = [call for call in calls if "review-history" in call]
    assert sum("--capture" in call for call in history_calls) == 3
    assert sum("--capture-id" in call for call in history_calls) == 3


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


def test_federation_rejects_changed_capture_identity(tmp_path: Path) -> None:
    helper = load_helper()

    def execute(argv, **_kwargs):
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Running"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        cursor = int(argv[argv.index("--cursor") + 1])
        return json.dumps({**history_page(), "cursor": cursor, "continuation": 5 if cursor == 0 else None,
                           "capture_id": ("e" if cursor else "d") * 24})

    first = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    second = helper.federated_review(config(tmp_path), 5, 0, first["source_state"], execute=execute)
    assert all(source["availability"] == "invalid_output" for source in second["sources"])
    assert second["source_state"] is None


def test_federation_does_not_start_or_stop_transitional_instance(tmp_path: Path) -> None:
    helper = load_helper()
    calls = []

    def execute(argv, **_kwargs):
        calls.append(argv)
        if argv[:2] == ["limactl", "list"]:
            return json.dumps([
                {"name": "workspace1-sandbox", "status": "Starting"},
                {"name": "workspace2-sandbox", "status": "Running"},
            ])
        return json.dumps(history_page())

    result = helper.federated_review(config(tmp_path), 5, 0, execute=execute)
    assert result["sources"][1]["availability"] == "invalid_output"
    assert not any(call[:2] in (["limactl", "start"], ["limactl", "stop"]) for call in calls)


def test_state_restoration_waits_for_lima_transition(monkeypatch) -> None:
    helper = load_helper()
    statuses = iter(["Starting", "Running"])
    calls = []

    def execute(argv, **_kwargs):
        calls.append(argv)
        return json.dumps({"name": "workspace1-sandbox", "status": next(statuses)})

    monkeypatch.setattr(helper.time, "sleep", lambda _seconds: None)
    helper._restore_instance_state(execute, "workspace1-sandbox", True)
    assert not any(call[:2] in (["limactl", "start"], ["limactl", "stop"]) for call in calls)


def test_instance_lifecycle_lock_serializes_and_rejects_symlinks(tmp_path: Path) -> None:
    helper = load_helper()
    root = tmp_path / "locks"
    first = helper._instance_lock(root, "workspace1-sandbox")
    attempting = threading.Event()
    acquired = threading.Event()

    def wait_for_lock():
        attempting.set()
        with helper._instance_lock(root, "workspace1-sandbox"):
            acquired.set()

    thread = threading.Thread(target=wait_for_lock)
    thread.start()
    assert attempting.wait(timeout=1)
    time.sleep(0.05)
    assert not acquired.is_set()
    first.close()
    thread.join(timeout=1)
    assert acquired.is_set()
    unsafe = tmp_path / "unsafe-locks"
    unsafe.symlink_to(root, target_is_directory=True)
    with pytest.raises(OSError):
        helper._instance_lock(unsafe, "workspace1-sandbox")


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

    values = config(tmp_path)
    values["lima_home"] = str(tmp_path)
    result = helper.status_report(values, execute=execute)
    assert result["host_free_bytes"] > 0
    assert result["workspaces"]["workspace1"]["running"] is True
    assert result["workspaces"]["workspace1"]["allocated_bytes"] > 0
    assert result["workspaces"]["workspace2"]["allocated_bytes"] is None

    values["lima_home"] = ""
    with mock.patch.dict(os.environ, {"LIMA_HOME": str(tmp_path)}, clear=True):
        fallback = helper.status_report(values, execute=execute)
    assert fallback["host_free_bytes"] > 0
    assert fallback["workspaces"] == result["workspaces"]


def test_general_controller_exposes_no_handoff_command() -> None:
    body = SCRIPT.read_text()
    assert 'add_parser("handoff")' not in body
    assert "launch_handoff" not in body
    assert '"render", "validate", "shell"' in body
    assert '"tailscale-enroll"' in body
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
    assert '["limactl", "shell", *preserve, workspace["instance"]' in body
    assert 'alias_args = sys.argv[1:] if argv is None else argv' in body
    assert 'argv = ["shell", matches[0], *(alias_args or ["herdr"])]' in body
    assert not (ROOT / "dot_local/bin/executable_lmsh").exists()
