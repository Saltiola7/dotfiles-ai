import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).parents[1]
OC = ROOT / "private_dot_config/opencode"


DATA = {
    "dotfiles_ai": {
        "opencode": {
            "bedrock_region": "us-west-2",
            "bedrock_profile": "test-profile",
            "default_model": "openai/gpt-5.6-sol",
            "small_model": "openai/gpt-5.6-terra",
            "lmstudio_base_url": "http://127.0.0.1:1234/v1",
        },
        "herdr": {
            "theme": "catppuccin",
            "launchagent": True,
            "executable": "/opt/homebrew/bin/herdr",
        },
        "onepassword": {
            "enabled": False,
            "account": "",
            "user_uuid": "",
            "keychain_service": "op-service-account-token",
        },
        "sandbox": {"workspaces": []},
    }
}


def text(path: str) -> str:
    return (ROOT / path).read_text()


def federated_digest(query, sources):
    identity = []
    for source in sources:
        item = {"source_id": source["source_id"], "availability": source["availability"]}
        if source["availability"] == "available":
            item.update({name: source["page"][name] for name in (
                "capture_id", "snapshot", "session_ceiling", "part_ceiling", "database_digest",
                "exclusion_digest", "limit", "cursor", "continuation", "digest",
            )})
        identity.append(item)
    return hashlib.sha256(json.dumps({"filters": query, "sources": identity}, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def rendered_config(env: dict[str, str] | None = None, data: dict | None = None) -> dict:
    result = subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(data or DATA),
            "cat", str(Path.home() / ".config/opencode/opencode.json"),
        ],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **(env or {})},
    )
    return json.loads(result.stdout)


def test_optional_local_repository_reference():
    assert "references" not in rendered_config()
    assert rendered_config()["permission"]["external_directory"] == "deny"
    configured = json.loads(json.dumps(DATA))
    configured["dotfiles_ai"]["sandbox"]["workspaces"] = [{
        "name": "workspace1", "instance": "workspace1-sandbox", "federate": True,
        "mounts": [{
            "host": "/workspace/reference", "guest": "/guest/reference", "writable": False,
            "protect_git_submodules": False, "reference_name": "project-reference",
            "reference_description": "Project reference.", "reference_subpath": "docs",
        }],
    }]
    rendered = rendered_config(data=configured)
    assert rendered["references"] == {
        "project-reference": {
            "path": "/workspace/reference/docs",
            "description": "Project reference.",
        }
    }
    assert list(rendered["permission"]["external_directory"].items()) == [
        ("*", "deny"),
        ("/workspace/reference/docs", "allow"),
        ("/workspace/reference/docs/**", "allow"),
    ]


def test_provider_and_primary_contracts():
    config = rendered_config()
    assert config["$schema"] == "https://opencode.ai/config.json"
    assert config["default_agent"] == "plan"
    assert not config["agent"].get("build", {}).get("disable", False)
    assert config["agent"]["plan"]["permission"]["edit"] == "deny"
    assert config["agent"]["plan"]["permission"]["bash"] == {
        "*": "ask",
        "dbsctrctl attach-runtime*": "deny",
        "*/dbsctrctl attach-runtime*": "deny",
        "env *dbsctrctl attach-runtime*": "deny",
        "command *dbsctrctl attach-runtime*": "deny",
        "dbsctrctl phase-span*": "deny",
        "*/dbsctrctl phase-span*": "deny",
        "env *dbsctrctl phase-span*": "deny",
        "command *dbsctrctl phase-span*": "deny",
        "dbsctrctl execution-benchmark*": "deny",
        "*/dbsctrctl execution-benchmark*": "deny",
        "env *dbsctrctl execution-benchmark*": "deny",
        "command *dbsctrctl execution-benchmark*": "deny",
        "dbsctrctl execution-dag*": "deny",
        "*/dbsctrctl execution-dag*": "deny",
        "env *dbsctrctl execution-dag*": "deny",
        "command *dbsctrctl execution-dag*": "deny",
        "acli *": "deny",
        "*/acli *": "deny",
        "env *acli *": "deny",
        "command *acli *": "deny",
        "acli jira auth status*": "allow",
        "acli jira workitem view *": "allow",
        "acli jira workitem search *": "allow",
        "acli jira workitem comment list *": "allow",
        "acli *&&*": "deny",
        "acli *;*": "deny",
        "acli *|*": "deny",
        "acli *>*": "deny",
        "acli *<*": "deny",
        "acli *$(*": "deny",
        "acli *`*": "deny",
    }
    assert "amazon-bedrock" in config["provider"]
    assert "lmstudio" in config["provider"]
    assert "headroom" not in config["provider"]
    assert "headroom-lmstudio" not in config["provider"]
    assert "gpt-5.6-sol-pro" not in config["provider"]["openai"]["models"]
    assert config["agent"]["plan"]["model"] == "openai/gpt-5.6-sol"
    assert config["agent"]["plan"]["variant"] == "medium"
    assert any(
        p == {"effect": "deny", "action": "provider.use", "resource": "anthropic"}
        for p in config["experimental"]["policies"]
    )


def test_context7_is_remote_optional_key_and_scout_only():
    anonymous = rendered_config({"CONTEXT7_API_KEY": ""})
    context7 = anonymous["mcp"]["context7"]
    assert context7 == {
        "type": "remote",
        "url": "https://mcp.context7.com/mcp",
        "enabled": True,
        "headers": {"CONTEXT7_API_KEY": "{env:CONTEXT7_API_KEY}"},
    }

    authenticated = rendered_config({"CONTEXT7_API_KEY": "test-context7-key"})
    assert authenticated["mcp"]["context7"] == context7
    assert "test-context7-key" not in text("private_dot_config/opencode/opencode.json.tmpl")
    assert authenticated["permission"]["context7_*"] == "deny"

    scouts = {"scout-openai.md", "scout-bedrock.md", "scout.md"}
    for agent in (OC / "agents").glob("*.md"):
        body = agent.read_text()
        if agent.name in scouts:
            assert "context7_*: allow" in body
        else:
            assert "context7_*: allow" not in body


def test_oauth_incompatible_pro_agents_are_absent():
    for name in ("plan-gpt-pro.md", "plan-gpt-pro-max.md", "build-gpt-pro.md"):
        assert not (OC / "agents" / name).exists()

    build = (OC / "agents/build-gpt.md").read_text()
    assert "model: openai/gpt-5.6-sol" in build
    assert "variant: medium" in build
    claude = (OC / "agents/build-claude.md").read_text()
    assert "model: amazon-bedrock/global.anthropic.claude-opus-5" in claude
    assert "variant: high" in claude
    assert "claude-opus-4-8" not in text("private_dot_config/opencode/opencode.json.tmpl")

    expected = {
        "explore-openai.md": ("openai/gpt-5.6-terra", "low"),
        "scout-openai.md": ("openai/gpt-5.6-terra", "medium"),
        "builder-openai.md": ("openai/gpt-5.6-terra", "medium"),
    }
    for name, (model, variant) in expected.items():
        body = (OC / "agents" / name).read_text()
        assert f"model: {model}" in body
        assert f"variant: {variant}" in body


def test_commands_inherit_current_agent():
    for name in ("dbsctr", "discovery", "qa", "dbsctr-review"):
        assert "\nagent:" not in (OC / f"commands/{name}.md").read_text()
    exact = {
        "dbsctr-gpt": ("build-gpt", "openai/gpt-5.6-sol"),
        "dbsctr-claude": ("build-claude", "amazon-bedrock/global.anthropic.claude-opus-5"),
    }
    for name, (agent, model) in exact.items():
        body = (OC / f"commands/{name}.md").read_text()
        assert f"agent: {agent}" in body
        assert f"model: {model}" in body


def test_provider_affine_task_permissions():
    expected = {
        "build-gpt.md": ("explore-openai", "scout-openai", "builder-openai"),
        "build-claude.md": ("explore-bedrock", "scout-bedrock", "builder-bedrock"),
    }
    for name, allowed in expected.items():
        body = (OC / "agents" / name).read_text()
        assert "\nname:" not in body
        assert '"*": deny' in body
        for agent in allowed:
            assert f"{agent}: allow" in body
    claude = (OC / "agents/build-claude.md").read_text()
    assert "explore-openai: allow" not in claude
    assert "scout-openai: allow" not in claude
    assert "builder-openai: allow" not in claude
    assert "exact runtime ID is\n`build-claude`" in claude
    assert "exact runtime ID is\n`build-gpt`" in (OC / "agents/build-gpt.md").read_text()


def test_builder_boundaries():
    for name in ("builder-openai.md", "builder-bedrock.md"):
        body = (OC / "agents" / name).read_text()
        assert "external_directory: deny" in body
        assert "task: deny" in body
        for command in (
            "git *", "gh *", "chezmoi apply*", "dvc push*", "npm publish*",
            "dbsctrctl review-complete*", "*/dbsctrctl review-complete*",
            "env *dbsctrctl review-complete*", "command *dbsctrctl review-complete*",
            *(form.format(command) for command in
              ("review-migrate", "review-backup", "review-restore", "review-prune", "review-forget")
              for form in ("dbsctrctl {}*", "*/dbsctrctl {}*", "env *dbsctrctl {}*", "command *dbsctrctl {}*")),
            "dbsctrctl improvement-*", "*/dbsctrctl improvement-*",
            "env *dbsctrctl improvement-*", "command *dbsctrctl improvement-*",
        ):
            assert f'"{command}": deny' in body


def test_only_build_primaries_can_begin_or_access_dbsctr_worktrees():
    config = rendered_config()
    worktrees = "~/.local/state/dbsctr/worktrees/**"
    local_config = "~/.config/dotfiles-ai/**"
    assert config["permission"]["dbsctr_begin"] == "deny"
    assert config["permission"]["dbsctr_attach"] == "deny"
    assert config["permission"]["dbsctr_phase_span"] == "deny"
    assert config["permission"]["dbsctr_execution_benchmark"] == "deny"
    assert config["permission"]["external_directory"] == "deny"
    assert "typed `dbsctr_execution_dag`" in (OC / "AGENTS.md").read_text()
    assert config["agent"]["build"]["permission"] == {
        "dbsctr_begin": "allow",
        "dbsctr_attach": "allow",
        "dbsctr_phase_span": "allow",
        "dbsctr_execution_benchmark": "allow",
        "dbsctr_execution_dag": "allow",
        "dbsctr_improvement_claim": "allow",
        "dbsctr_improvement_update": "allow",
        "dbsctr_provider_evaluation_save": "allow",
        "external_directory": {worktrees: "allow", local_config: "allow"},
    }

    build_primaries = {"build-gpt.md", "build-claude.md"}
    for agent in (OC / "agents").glob("*.md"):
        body = agent.read_text()
        if agent.name in build_primaries:
            assert "mode: primary" in body
            assert "dbsctr_begin: allow" in body
            assert "dbsctr_attach: allow" in body
            assert "dbsctr_phase_span: allow" in body
            assert "dbsctr_execution_benchmark: allow" in body
            assert "dbsctr_execution_dag: allow" in body
            assert f"external_directory:\n    {worktrees}: allow" in body
            assert f"    {local_config}: allow" in body
        else:
            assert "mode: subagent" in body
            assert "dbsctr_begin: allow" not in body
            assert "dbsctr_attach: allow" not in body
            assert "dbsctr_phase_span: allow" not in body
            assert "dbsctr_execution_benchmark: allow" not in body
            assert "dbsctr_execution_dag: allow" not in body
            assert worktrees not in body
            assert local_config not in body
    for name in ("builder-openai.md", "builder-bedrock.md"):
        assert "external_directory: deny" in (OC / "agents" / name).read_text()


def test_dbsctr_safe_git_permissions_and_reviewer():
    config = rendered_config()
    bash = config["permission"]["bash"]
    assert bash["dbsctrctl gate-commit*"] == "allow"
    assert bash["dbsctrctl final-push*"] == "allow"
    assert bash["dbsctrctl approve-exception*"] == "ask"
    assert bash["dbsctrctl record-dvc-push*"] == "ask"
    assert bash["dbsctrctl record-evidence*"] == "ask"
    for command in ("dbsctrctl attach-runtime*", "*/dbsctrctl attach-runtime*",
                    "env *dbsctrctl attach-runtime*", "command *dbsctrctl attach-runtime*"):
        assert bash[command] == "deny"
    for operation in ("phase-span", "execution-benchmark", "execution-dag"):
        for command in (f"dbsctrctl {operation}*", f"*/dbsctrctl {operation}*",
                        f"env *dbsctrctl {operation}*", f"command *dbsctrctl {operation}*"):
            assert bash[command] == "deny"
    assert bash["dbsctrctl review-complete*"] == "ask"
    assert bash["*/dbsctrctl review-complete*"] == "ask"
    assert bash["env *dbsctrctl review-complete*"] == "ask"
    assert bash["command *dbsctrctl review-complete*"] == "ask"
    for command in ("dbsctrctl review-history*", "*/dbsctrctl review-history*",
                    "env *dbsctrctl review-history*", "command *dbsctrctl review-history*"):
        assert bash[command] == "allow"
    for command in ("dbsctrctl review-history-save*", "*/dbsctrctl review-history-save*",
                     "env *dbsctrctl review-history-save*", "command *dbsctrctl review-history-save*"):
        assert bash[command] == "ask"
    for command in ("review-migrate", "review-backup", "review-restore", "review-prune", "review-forget",
                    "improvement-forget"):
        for form in ("dbsctrctl {}*", "*/dbsctrctl {}*", "env *dbsctrctl {}*", "command *dbsctrctl {}*"):
            assert bash[form.format(command)] == "ask"
    assert bash["*dbsctrctl improvement-forget*"] == "ask"
    assert bash["dbsctrctl cleanup*"] == "ask"
    assert bash["*limactl *"] == "deny"
    for command in (
        "herdr server stop*", "herdr config reset-keys*", "herdr worktree remove*",
        "herdr workspace close*", "herdr pane close*", "herdr tab close*",
        "herdr session stop*", "herdr session delete*",
    ):
        assert bash[command] == "ask"
    assert config["permission"]["dbsctr_status"] == "allow"
    assert config["permission"]["dbsctr_begin"] == "deny"
    assert config["permission"]["dbsctr_attach"] == "deny"
    assert config["permission"]["dbsctr_phase_span"] == "deny"
    assert config["permission"]["dbsctr_execution_benchmark"] == "deny"
    assert config["permission"]["dbsctr_execution_dag"] == "deny"
    assert config["permission"]["dbsctr_audit"] == "allow"
    assert config["permission"]["dbsctr_inspect"] == "allow"
    assert config["permission"]["dbsctr_review"] == "allow"
    assert config["permission"]["dbsctr_review_complete"] == "ask"
    assert config["permission"]["dbsctr_review_history"] == "allow"
    assert config["permission"]["dbsctr_review_history_save"] == "allow"
    assert config["permission"]["dbsctr_review_federated"] == "allow"
    assert bash["gh *"] == "ask"
    assert bash["gh issue list *"] == "allow"
    assert bash["gh pr list *"] == "allow"
    assert config["permission"]["dbsctr_vm_handoff"] == "ask"
    assert config["permission"]["dbsctr_improvement_status"] == "allow"
    assert config["permission"]["dbsctr_improvement_claim"] == "deny"
    assert config["permission"]["dbsctr_improvement_update"] == "deny"
    assert config["agent"]["plan"]["permission"]["dbsctr_begin"] == "deny"
    assert config["agent"]["plan"]["permission"]["dbsctr_attach"] == "deny"
    assert config["agent"]["plan"]["permission"]["dbsctr_phase_span"] == "deny"
    assert config["agent"]["plan"]["permission"]["dbsctr_vm_handoff"] == "deny"
    for command in (
        "git push --force*", "git push -f*", "git *push*--force*", "git push *+*",
        "git commit --no-verify*", "git commit -n*", "git *commit*--no-verify*",
    ):
        assert bash[command] == "deny"

    reviewer = (OC / "agents/reviewer-openai.md").read_text()
    assert "mode: subagent" in reviewer
    assert "model: openai/gpt-5.6-sol" in reviewer
    assert "edit: deny" in reviewer
    assert "task: deny" in reviewer
    assert "dbsctr_begin: deny" in reviewer
    assert "dbsctr_review_history_save: deny" in reviewer

    for name in ("build-gpt.md", "build-claude.md"):
        assert "dbsctr_begin: allow" in (OC / "agents" / name).read_text()
        assert "dbsctr_attach: allow" in (OC / "agents" / name).read_text()
        assert "dbsctr_phase_span: allow" in (OC / "agents" / name).read_text()
        assert "dbsctr_execution_benchmark: allow" in (OC / "agents" / name).read_text()
        assert "dbsctr_execution_dag: allow" in (OC / "agents" / name).read_text()
    for name in ("builder-openai.md", "builder-bedrock.md"):
        assert "dbsctr_begin: deny" in (OC / "agents" / name).read_text()
        assert "dbsctr_attach: deny" in (OC / "agents" / name).read_text()
        assert "dbsctr_phase_span: allow" not in (OC / "agents" / name).read_text()
        assert "dbsctr_execution_benchmark: allow" not in (OC / "agents" / name).read_text()
        assert "dbsctr_execution_dag: allow" not in (OC / "agents" / name).read_text()
        assert "dbsctr_review_complete: deny" in (OC / "agents" / name).read_text()
        assert "dbsctr_review_history_save: deny" in (OC / "agents" / name).read_text()
        assert "dbsctr_improvement_claim: deny" in (OC / "agents" / name).read_text()
        assert "dbsctr_improvement_update: deny" in (OC / "agents" / name).read_text()
    for name in ("reviewer-openai.md", "explore-openai.md", "explore-bedrock.md",
                 "scout-openai.md", "scout-bedrock.md", "scout.md"):
        assert "dbsctr_review_history_save: deny" in (OC / "agents" / name).read_text()


def test_dbsctr_tools_and_herdr_config_are_managed():
    tools = (OC / "tools/dbsctr.ts").read_text()
    assert 'export const status = tool({' in tools
    assert 'export const attach = tool({' in tools
    assert 'export const runtime_health = tool({' in tools
    assert 'export const begin = tool({' in tools
    assert 'export const audit = tool({' in tools
    assert 'export const inspect = tool({' in tools
    assert 'export const review = tool({' in tools
    assert 'export const review_complete = tool({' in tools
    assert 'export const review_history = tool({' in tools
    assert 'export const review_history_save = tool({' in tools
    assert 'export const review_federated = tool({' in tools
    assert 'export const vm_handoff = tool({' in tools
    assert 'export const history_capture = tool({' in tools
    assert 'export const history_telemetry = tool({' in tools
    assert 'export const benchmark = tool({' in tools
    assert 'export const improvement_status = tool({' in tools
    assert 'export const improvement_claim = tool({' in tools
    assert 'export const improvement_update = tool({' in tools
    assert 'export const phase_span = tool({' in tools
    assert 'export const execution_dag = tool({' in tools
    assert 'export const execution_benchmark = tool({' in tools
    assert "snapshot: tool.schema.number().int().min(0).optional()" in tools
    assert "snapshot: tool.schema.number().int().min(0)," in tools
    assert "snapshot: args.snapshot," in tools
    history_save = tools.split("export const review_history_save = tool({", 1)[1]
    assert "limit: tool.schema.number().int().min(1).max(100).optional()" in history_save
    assert "cursor: tool.schema.number().int().min(0).optional()" in history_save
    assert "limit: args.limit," in history_save
    assert "cursor: args.cursor," in history_save
    assert "default(false)" in tools
    runtime = (OC / "lib/dbsctr-runtime.ts").read_text()
    history_save_runtime = runtime.split("export async function reviewHistorySave", 1)[1]
    assert "limit?: number" in history_save_runtime
    assert "cursor?: number" in history_save_runtime
    assert '["dbsctrctl", "status", "--json"]' in runtime
    assert '["dbsctrctl", "audit", "--commit", commit, "--json"]' in runtime
    assert '"dbsctrctl", "inspect", "--commit"' in runtime
    assert '["dbsctrctl", "review-scan"' in runtime
    assert '"dbsctrctl", "review-complete"' in runtime
    assert '"dbsctrctl", "review-history"' in runtime
    assert '"dbsctrctl", "review-history-save"' in runtime
    assert '["sandbox-vm", "review"' in runtime
    assert 'sourceState?: {' in runtime
    assert 'argv.push("--excluded-session-id", excludedSessionID)' in runtime
    assert 'argv.push("--excluded-message-id", excludedMessageID)' in runtime
    assert '["sandbox-vm", "instance", report.target]' in runtime
    assert '["sandbox-vm", "build-workspace"]' in runtime
    assert '"herdr", "workspace", "create"' in runtime
    assert '"herdr", "agent", "start", "DBSCTR Handoff"' in runtime
    assert '"--kind", "opencode", "--pane", paneID' in runtime
    assert '"dbsctrctl", "history-capture"' in runtime
    assert '"dbsctrctl", "benchmark"' in runtime
    assert "timeoutMs: number | null = 30_000" in runtime
    assert "analyticsJSON(argv, cwd, null)" in runtime
    assert '"dbsctrctl", "improvement-status"' in runtime
    assert '"dbsctrctl", "improvement-claim"' in runtime
    assert '"dbsctrctl", "improvement-update"' in runtime
    assert '"dbsctrctl", "phase-span"' in runtime
    assert '"dbsctrctl", "execution-dag"' in runtime
    assert '"dbsctrctl", "execution-benchmark"' in runtime
    assert runtime.count('"--excluded-session-id"') == 5
    assert "context.sessionID" in tools
    assert "context.worktree, true" in tools
    assert '"herdr", "agent", "start", "opencode"' in runtime
    assert '"herdr", "pane", "current"' in runtime
    config = rendered_config()
    for permission in ("dbsctr_history_capture", "dbsctr_history_telemetry", "dbsctr_benchmark"):
        assert config["permission"][permission] == "allow"
    for agent in (OC / "agents").glob("*.md"):
        assert "dbsctr_vm_handoff: deny" in agent.read_text()
    herdr = text("private_dot_config/herdr/config.toml.tmpl")
    assert "pane_history = false" in herdr
    assert ".dotfiles_ai.herdr.theme" in herdr


def test_dbsctr_tool_runtime_preserves_argv_and_opts_in_to_herdr(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    dbsctr_log = tmp_path / "dbsctr.log"
    dbsctr_calls = tmp_path / "dbsctr.calls"
    herdr_log = tmp_path / "herdr.log"
    cycle = tmp_path / "cycle"
    cycle.mkdir()
    dbsctr = bin_dir / "dbsctrctl"
    dbsctr.write_text(
        "#!/bin/sh\npwd > \"$DBSCTR_CWD\"\nprintf 'CALL\\n' >> \"$DBSCTR_CALLS\"\nprintf '<%s>\\n' \"$@\" > \"$DBSCTR_LOG\"\n"
        "[ \"$DBSCTR_MODE\" = fail ] && { printf 'boom\\n' >&2; exit 7; }\n"
        "[ \"$DBSCTR_MODE\" = malformed ] && { printf 'not-json\\n'; exit 0; }\n"
        "printf '{\"cycle_id\":\"x\",\"worktree\":\"%s\"}\\n' \"$CYCLE_PATH\"\n"
    )
    herdr = bin_dir / "herdr"
    herdr.write_text(
        "#!/bin/sh\nprintf 'CALL\\nCWD:%s\\n' \"$(pwd)\" >> \"$HERDR_LOG\"\n"
        "printf '<%s>\\n' \"$@\" >> \"$HERDR_LOG\"\n"
        "[ \"$HERDR_FAIL\" = 1 ] && { printf 'herdr-boom\\n' >&2; exit 9; }\n"
        "[ \"$HERDR_STRUCTURED\" = 1 ] && printf '{\"result\":{\"agent\":{\"terminal_id\":\"terminal-1\",\"agent_session\":{\"value\":\"session-launched\"}}}}\\n'\n"
        "exit 0\n"
    )
    dbsctr.chmod(0o755)
    herdr.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ beginCycle }} from {json.dumps(str(runtime))};'
        'console.log(JSON.stringify(await beginCycle({cycleId:"x;touch nope",context:"ctx",risk:"routine",'
        'deliveryIntent:"local",planPath:"/tmp/plan with spaces"},process.cwd(),'
        'process.argv[1] === "launch",process.env)));'
    )
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "DBSCTR_LOG": str(dbsctr_log),
        "DBSCTR_CWD": str(tmp_path / "dbsctr.cwd"),
        "DBSCTR_CALLS": str(dbsctr_calls),
        "HERDR_LOG": str(herdr_log),
        "HERDR_ENV": "1",
        "CYCLE_PATH": str(cycle),
    }
    no_launch = subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True,
                               capture_output=True, check=True)
    assert json.loads(no_launch.stdout)["herdr"] == "not_launched"
    assert not herdr_log.exists()
    assert (tmp_path / "dbsctr.cwd").read_text().strip() == str(ROOT)
    assert dbsctr_log.read_text().splitlines() == [
        "<begin>", "<--cycle-id>", "<x;touch nope>", "<--context>", "<ctx>",
        "<--risk>", "<routine>", "<--delivery-intent>", "<local>",
        "<--plan>", "</tmp/plan with spaces>",
    ]
    launched = subprocess.run(["bun", "-e", script, "launch"], cwd=ROOT, env=env, text=True,
                              capture_output=True, check=True)
    assert json.loads(launched.stdout)["herdr"] == "launched"
    assert herdr_log.read_text().splitlines() == [
        "CALL", f"CWD:{ROOT}", "<agent>", "<start>", "<opencode>", "<--cwd>",
        f"<{cycle}>", "<--no-focus>", "<-->", "<opencode>", f"<{cycle}>",
    ]
    structured = subprocess.run(["bun", "-e", script, "launch"], cwd=ROOT,
                                env={**env, "HERDR_STRUCTURED": "1"}, text=True,
                                capture_output=True, check=True)
    structured_result = json.loads(structured.stdout)
    assert structured_result["herdr_terminal_id"] == "terminal-1"
    assert structured_result["herdr_opencode_session_id"] == "session-launched"
    assert dbsctr_calls.read_text().splitlines() == ["CALL", "CALL", "CALL"]

    failed = subprocess.run(["bun", "-e", script], cwd=ROOT,
                            env={**env, "DBSCTR_MODE": "fail"}, text=True, capture_output=True)
    assert failed.returncode != 0 and "boom" in failed.stderr
    malformed = subprocess.run(["bun", "-e", script], cwd=ROOT,
                               env={**env, "DBSCTR_MODE": "malformed"}, text=True, capture_output=True)
    assert malformed.returncode != 0
    herdr_failed = subprocess.run(["bun", "-e", script, "launch"], cwd=ROOT,
                                  env={**env, "HERDR_FAIL": "1"}, text=True,
                                  capture_output=True, check=True)
    assert json.loads(herdr_failed.stdout)["herdr"].startswith("launch_failed:")


def test_dbsctr_inspect_runtime_preserves_argv(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "inspect.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text('#!/bin/sh\nprintf "<%s>\\n" "$@" > "$INSPECT_LOG"\nprintf "{}\\n"\n')
    helper.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ fixedCommitInspect }} from {json.dumps(str(runtime))};'
        'console.log(await fixedCommitInspect({action:"search",commit:"ref;touch nope",'
        'path:"docs/specs",query:"literal.* value",limit:7,cursor:2,excerpt:80},process.cwd()));'
    )
    subprocess.run(["bun", "-e", script], cwd=ROOT,
                   env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "INSPECT_LOG": str(log)},
                   text=True, capture_output=True, check=True)
    assert log.read_text().splitlines() == [
        "<inspect>", "<--commit>", "<ref;touch nope>", "<--action>", "<search>",
        "<--path>", "<docs/specs>", "<--query>", "<literal.* value>",
        "<--limit>", "<7>", "<--cursor>", "<2>", "<--excerpt>", "<80>", "<--json>",
    ]


def test_compact_analytics_adapters_bound_validate_and_preserve_argv(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "analytics.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text(
        '#!/bin/sh\nprintf "CALL\\n" >> "$ANALYTICS_LOG"\nprintf "<%s>\\n" "$@" >> "$ANALYTICS_LOG"\n'
        '[ "$DBSCTR_MODE" = oversized ] && { dd if=/dev/zero bs=300000 count=1 2>/dev/null | tr "\\000" x; exit 0; }\n'
        'case "$1" in\n'
        '  history-capture) printf "%s\\n" "$CAPTURE_JSON" ;;\n'
        '  review-history) printf "%s\\n" "$TELEMETRY_JSON" ;;\n'
        '  benchmark) printf "%s\\n" "$BENCHMARK_JSON" ;;\n'
        'esac\n'
    )
    helper.chmod(0o755)
    capture_id = "a" * 24
    benchmark_id = "b" * 24
    capture = {"schema_version": 1, "capture_id": capture_id, "query": {}, "snapshot": 1,
               "page_size": 100, "page_count": 1, "member_count": 1, "aggregates": {}}
    telemetry = {"schema_version": 1, "candidates": [{"telemetry": {
        "approval_count": "unavailable", "retry_count": "unavailable", "delegation_count": 1,
        "model_families": ["gpt"], "error_classes": {"tool_error": 0}, "token_total": 2,
        "cost_total": 0, "availability": {name: "available" for name in (
            "approval_count", "retry_count", "delegation_count", "model_families",
            "error_classes", "token_total", "cost_total")}, "attribution_status": "exact",
    }}, {"correlation_quality": "ambiguous"}], "limit": 7, "cursor": 2}
    benchmark = {"schema_version": 1, "benchmark_id": benchmark_id,
                 "definition": {"version": "v1", "metric": "tool_error_count", "direction": "lower"},
                 "inputs": {"baseline_capture_id": "c" * 24, "observation_capture_id": "d" * 24,
                            "merge_identity": "e" * 40, "merged_at": 1, "activation_status": "missing",
                            "activation_identity": None, "activated_at": None},
                 "windows": "unavailable", "result": {"classification": "insufficient",
                 "baseline_value": 1, "observation_value": 1, "delta": "unavailable",
                 "confounders": [], "unavailable_metrics": [], "association_only": True,
                 "reason": "activation_missing"}, "evaluated_at": 1}
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ historyCapture, historyTelemetry, benchmarkResult }} from {json.dumps(str(runtime))};'
        f'console.log(await historyCapture({{captureID:{json.dumps(capture_id)}}},process.cwd()));'
        'console.log(await historyTelemetry({limit:7,cursor:2},process.cwd(),"session;safe","message safe"));'
        f'console.log(await benchmarkResult({json.dumps(benchmark_id)},process.cwd()));'
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "ANALYTICS_LOG": str(log),
           "CAPTURE_JSON": json.dumps(capture), "TELEMETRY_JSON": json.dumps(telemetry),
           "BENCHMARK_JSON": json.dumps(benchmark)}
    result = subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True,
                            capture_output=True, check=True)
    outputs = [json.loads(line) for line in result.stdout.splitlines()]
    assert outputs[0] == capture and outputs[2] == benchmark
    normalized = outputs[1]["candidates"][0]["telemetry"]
    assert normalized["schema_version"] == 2
    for key, value in telemetry["candidates"][0]["telemetry"].items():
        if key == "availability":
            for metric, status in value.items():
                assert normalized[key][metric] == status
        else:
            assert normalized[key] == value
    legacy = outputs[1]["candidates"][1]["telemetry"]
    assert legacy["attribution_status"] == "ambiguous"
    assert set(legacy["availability"].values()) == {"unavailable"}
    assert log.read_text().splitlines() == [
        "CALL", "<history-capture>", "<--capture-id>", f"<{capture_id}>",
        "CALL", "<review-history>", "<--excluded-session-id>", "<session;safe>",
        "<--excluded-message-id>", "<message safe>", "<--limit>", "<7>", "<--cursor>", "<2>",
        "CALL", "<benchmark>", "<--benchmark-id>", f"<{benchmark_id}>",
    ]

    malformed = subprocess.run(
        ["bun", "-e", f'import {{ benchmarkResult }} from {json.dumps(str(runtime))};'
         f'await benchmarkResult({json.dumps(benchmark_id)},process.cwd());'],
        cwd=ROOT, env={**env, "BENCHMARK_JSON": "not-json"}, text=True, capture_output=True,
    )
    assert malformed.returncode != 0 and "malformed JSON" in malformed.stderr
    unsafe = {**benchmark, "definition": {**benchmark["definition"], "version": "/Users/private"}}
    rejected = subprocess.run(
        ["bun", "-e", f'import {{ benchmarkResult }} from {json.dumps(str(runtime))};'
         f'await benchmarkResult({json.dumps(benchmark_id)},process.cwd());'],
        cwd=ROOT, env={**env, "BENCHMARK_JSON": json.dumps(unsafe).replace("/", "\\u002f")},
        text=True, capture_output=True,
    )
    assert rejected.returncode != 0 and "unsafe content" in rejected.stderr
    oversized = subprocess.run(
        ["bun", "-e", f'import {{ benchmarkResult }} from {json.dumps(str(runtime))};'
         f'await benchmarkResult({json.dumps(benchmark_id)},process.cwd());'],
        cwd=ROOT, env={**env, "DBSCTR_MODE": "oversized"}, text=True, capture_output=True,
    )
    assert oversized.returncode != 0 and "exceeded bound" in oversized.stderr


def test_profiler_adapters_preserve_structured_argv(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "profiler.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text(
        '#!/bin/sh\nprintf "CALL\\n" >> "$PROFILER_LOG"\nprintf "<%s>\\n" "$@" >> "$PROFILER_LOG"\nprintf "{}\\n"\n'
    )
    helper.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    benchmark_request = {"id": "fixture-v1", "commit": "a" * 40,
                         "path": "tests/fixtures/fixture.json", "blob": "b" * 40}
    script = (
        f'import {{ phaseSpan, validateExecutionDag, recordExecutionBenchmark }} from {json.dumps(str(runtime))};'
        'await phaseSpan({spanID:"read-a",event:"start",phase:"domain",operation:"read",'
        'dependencies:["root"],ownershipPaths:["docs/a"],attribution:"explicit"},process.cwd());'
        'await validateExecutionDag([{id:"read-a",depends_on:[],operation:"read",ownership_paths:["docs/a"]}],'
        '[],"benchmark",process.cwd());'
        f'await recordExecutionBenchmark({json.dumps(benchmark_request)},process.cwd());'
    )
    subprocess.run(
        ["bun", "-e", script], cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "PROFILER_LOG": str(log)},
        text=True, capture_output=True, check=True,
    )
    assert log.read_text().splitlines() == [
        "CALL", "<phase-span>", "<--span-id>", "<read-a>", "<--event>", "<start>",
        "<--phase>", "<domain>", "<--operation>", "<read>", "<--attribution>", "<explicit>",
        "<--dependency>", "<root>", "<--path>", "<docs/a>",
        "CALL", "<execution-dag>", "<--mode>", "<benchmark>", "<--dag-json>",
        '<{"nodes":[{"id":"read-a","depends_on":[],"operation":"read","ownership_paths":["docs/a"]}],"completed":[]}>',
        "CALL", "<execution-benchmark>", "<--fixture-id>", "<fixture-v1>",
        "<--fixture-commit>", f'<{"a" * 40}>', "<--fixture-path>", "<tests/fixtures/fixture.json>",
        "<--fixture-blob>", f'<{"b" * 40}>',
    ]


def test_dbsctr_review_runtime_preserves_optional_snapshot_argv(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "review.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text('#!/bin/sh\nprintf "<%s>\\n" "$@" > "$REVIEW_LOG"\nprintf "{}\\n"\n')
    helper.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ reviewScan }} from {json.dumps(str(runtime))};'
        'await reviewScan(7, 2, process.argv[1] === "snapshot" ? 123 : undefined, process.cwd());'
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "REVIEW_LOG": str(log)}
    subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    assert log.read_text().splitlines() == ["<review-scan>", "<--limit>", "<7>", "<--cursor>", "<2>"]
    subprocess.run(["bun", "-e", script, "snapshot"], cwd=ROOT, env=env,
                   text=True, capture_output=True, check=True)
    assert log.read_text().splitlines() == [
        "<review-scan>", "<--limit>", "<7>", "<--cursor>", "<2>", "<--snapshot>", "<123>",
    ]
    script = (
        f'import {{ reviewScan }} from {json.dumps(str(runtime))};'
        'await reviewScan(7, 2, undefined, process.cwd(), undefined, undefined, undefined, "active-tool");'
    )
    subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    assert log.read_text().splitlines() == [
        "<review-scan>", "<--limit>", "<7>", "<--cursor>", "<2>",
        "<--excluded-session-id>", "<active-tool>",
    ]


def test_dbsctr_review_adapters_pass_excluded_session_id(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "review-adapters.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text('#!/bin/sh\nprintf "CALL\\n" >> "$REVIEW_ADAPTERS_LOG"\nprintf "<%s>\\n" "$@" >> "$REVIEW_ADAPTERS_LOG"\nprintf "{}\\n"\n')
    helper.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    report = {
        "session_ids": ["included"], "cycle_ids": [], "scan_digest": "a" * 64,
        "snapshot": 1784073600000, "session_ceiling": 1, "part_ceiling": 1, "database_digest": "b" * 64,
        "limit": 1, "cursor": 0, "decision": "safe", "findings": [], "scorecards": [],
        "trends": [], "proposals": [], "caveats": [],
    }
    history = {
        "schema_version": 1, "cohort": ["included"], "query_digest": "c" * 64,
        "rubric": {"name": "history", "version": "1", "digest": "d" * 64},
        "snapshot": 1784073600000, "session_ceiling": 1, "part_ceiling": 1,
        "database_digest": "e" * 64, "limit": 1, "cursor": 100, "findings": [],
    }
    script = (
        f'import {{ reviewScan, reviewComplete, reviewHistory, reviewHistorySave }} from {json.dumps(str(runtime))};'
        f'const report={json.dumps(report)};const history={json.dumps(history)};'
        'await reviewScan(1,0,undefined,process.cwd(),undefined,undefined,undefined,"caller","message");'
        'await reviewComplete(report,process.cwd(),"caller","message");'
        'await reviewHistory({archiveOnly:true},process.cwd(),"caller","message");'
        'await reviewHistorySave(history,process.cwd(),"caller","message");'
    )
    subprocess.run(["bun", "-e", script], cwd=ROOT,
                   env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "REVIEW_ADAPTERS_LOG": str(log)},
                   text=True, capture_output=True, check=True)
    calls = [line for line in log.read_text().splitlines() if line != "CALL"]
    assert calls.count("<--excluded-session-id>") == 4
    assert calls.count("<caller>") == 4
    assert calls.count("<--excluded-message-id>") == 4
    assert calls.count("<message>") == 4
    payloads = [json.loads(line[1:-1]) for line in calls if line.startswith("<{\"")]
    saved_history = next(payload for payload in payloads if "cohort" in payload)
    assert saved_history["limit"] == 1
    assert saved_history["cursor"] == 100


def test_dbsctr_review_history_runtime_preserves_literal_argv(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "history.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text('#!/bin/sh\nprintf "<%s>\\n" "$@" > "$HISTORY_LOG"\nprintf "{}\\n"\n')
    helper.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ reviewHistory }} from {json.dumps(str(runtime))};'
        'await reviewHistory({context:"x;touch nope",reviewedStatus:"reviewed",limit:100,cursor:0},process.cwd());'
    )
    subprocess.run(["bun", "-e", script], cwd=ROOT,
                   env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "HISTORY_LOG": str(log)},
                   text=True, capture_output=True, check=True)
    assert log.read_text().splitlines() == [
        "<review-history>", "<--context>", "<x;touch nope>", "<--reviewed-status>", "<reviewed>",
        "<--limit>", "<100>", "<--cursor>", "<0>",
    ]


def test_dbsctr_improvement_runtime_preserves_literal_argv(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "improvement.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text('#!/bin/sh\nprintf "CALL\\n" >> "$IMPROVEMENT_LOG"\nprintf "<%s>\\n" "$@" >> "$IMPROVEMENT_LOG"\nprintf "{}\\n"\n')
    helper.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ improvementClaim, improvementStatus, improvementUpdate }} from {json.dumps(str(runtime))};'
        'await improvementClaim("session-1","safe; literal",process.cwd());'
        'await improvementUpdate("session-1",{state:"implementing",cycleID:"cycle-1",paths:["a b","x;nope"]},process.cwd(),true);'
        'await improvementStatus("worker-1",process.cwd());'
    )
    subprocess.run(["bun", "-e", script], cwd=ROOT,
                   env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "IMPROVEMENT_LOG": str(log)},
                   text=True, capture_output=True, check=True)
    calls = log.read_text().splitlines()
    assert calls == [
        "CALL", "<improvement-claim>", "<--session-id>", "<session-1>",
        "<--summary>", "<safe; literal>",
        "CALL", "<improvement-update>", "<--session-id>", "<session-1>",
        "<--state>", "<implementing>", "<--cycle-id>", "<cycle-1>",
        "<--path>", "<a b>", "<--path>", "<x;nope>",
        "CALL", "<improvement-status>", "<--worker-id>", "<worker-1>",
    ]


def test_dbsctr_attach_runtime_preserves_structured_context(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "attach.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text('#!/bin/sh\nprintf "<%s>\\n" "$@" > "$ATTACH_LOG"\nprintf "{}\\n"\n')
    helper.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ attachRuntime }} from {json.dumps(str(runtime))};'
        'await attachRuntime(process.cwd(),{sessionID:"session-resumed",messageID:"message-resumed",directory:process.cwd(),worktree:process.cwd()});'
    )
    subprocess.run(["bun", "-e", script], cwd=ROOT,
                   env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "ATTACH_LOG": str(log)},
                   text=True, capture_output=True, check=True)
    assert log.read_text().splitlines() == [
        "<attach-runtime>", "<--opencode-session-id>", "<session-resumed>",
        "<--opencode-message-id>", "<message-resumed>",
        "<--opencode-directory>", f"<{ROOT}>", "<--opencode-worktree>", f"<{ROOT}>",
        "<--harness-activation-json>",
        '<{"schema_version":1,"core_revision":"3.29","overlays":{"build":"neutral-2026-07-26","build-gpt":"openai-2026-07-26","build-claude":"anthropic-2026-07-26"}}>',
    ]


def test_provider_evaluation_receipt_is_single_use(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    query = {"after": None, "archive_only": False, "before": None, "context": None,
             "cycle_id": None, "method_revision": None, "project_digest": None,
             "reviewed_status": None, "state": None}
    page = {"schema_version": 1, "capture_id": "c" * 24, "snapshot": 1,
            "session_ceiling": 1, "part_ceiling": 1, "database_digest": "d" * 64,
            "exclusion_digest": None, "limit": 25, "cursor": 0, "continuation": None,
            "candidates": [], "digest": "e" * 64, "query": query, "session_ids": []}
    identity = {"filters": query, "sources": [{"source_id": "host", "availability": "available",
                **{name: page[name] for name in ("capture_id", "snapshot", "session_ceiling", "part_ceiling",
                                                  "database_digest", "exclusion_digest", "limit", "cursor",
                                                  "continuation", "digest")}}]}
    manifest_digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    response = {"schema_version": 2, "sources": [{"source_id": "host", "availability": "available", "page": page}],
                "source_state": None, "manifest_digest": manifest_digest}
    privacy_log = tmp_path / "privacy.log"
    sandbox = bin_dir / "sandbox-vm"
    sandbox.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = privacy-epochs ]; then\n"
        "  digest=" + "f" * 64 + "\n"
        "  [ \"$PRIVACY_CHANGE\" = 1 ] && [ -s \"$PRIVACY_LOG\" ] && digest=" + "a" * 64 + "\n"
        "  printf 'x\\n' >> \"$PRIVACY_LOG\"\n"
        "  printf '{\"schema_version\":1,\"sources\":[{\"source_id\":\"host\",\"availability\":\"available\",\"privacy_epoch_digest\":\"%s\"}]}\\n' \"$digest\"\n"
        "  exit\n"
        "fi\n"
        f"printf '%s\\n' '{json.dumps(response, separators=(',', ':'))}'\n"
    )
    sandbox.chmod(0o755)
    helper = bin_dir / "dbsctrctl"
    helper.write_text(
        "#!/bin/sh\ncat >/dev/null\nprintf '%s\\n' "
        "'{\"schema_version\":1,\"status\":\"insufficient\",\"eligible_count\":0}'\n"
    )
    helper.chmod(0o755)
    config = tmp_path / "sandbox.json"
    config.write_text(json.dumps({"workspaces": []}))
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ reviewFederated, providerEvaluationSave }} from {json.dumps(str(runtime))};'
        f'const page=JSON.parse(await reviewFederated({{}},process.cwd(),undefined,undefined,'
        f'{{...process.env,OPENCODE_VM_CONFIG:{json.dumps(str(config))}}}));'
        'console.log(await providerEvaluationSave({manifestDigest:page.manifest_digest,'
        'rubric:{name:"provider-harness",version:"1",digest:"a".repeat(64)},findings:[],recommendations:[]},process.cwd()));'
        'try { await providerEvaluationSave({manifestDigest:page.manifest_digest,'
        'rubric:{name:"provider-harness",version:"1",digest:"a".repeat(64)},findings:[],recommendations:[]},process.cwd()); }'
        'catch (error) { console.log(error.message); }'
    )
    result = subprocess.run(["bun", "-e", script], cwd=ROOT,
                            env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                                 "PRIVACY_LOG": str(privacy_log)},
                            text=True, capture_output=True, check=True)
    assert result.stdout.splitlines() == [
        '{"schema_version":1,"status":"insufficient","eligible_count":0}',
        "terminal federated capture receipt is unavailable",
    ]
    assert privacy_log.read_text().splitlines() == ["x", "x"]

    privacy_log.unlink()
    changed_script = (
        f'import {{ reviewFederated, providerEvaluationSave }} from {json.dumps(str(runtime))};'
        f'const page=JSON.parse(await reviewFederated({{}},process.cwd(),undefined,undefined,'
        f'{{...process.env,OPENCODE_VM_CONFIG:{json.dumps(str(config))}}}));'
        'try { await providerEvaluationSave({manifestDigest:page.manifest_digest,'
        'rubric:{name:"provider-harness",version:"1",digest:"a".repeat(64)},findings:[],recommendations:[]},process.cwd()); }'
        'catch (error) { console.log(error.message); }'
    )
    changed = subprocess.run(["bun", "-e", changed_script], cwd=ROOT,
                             env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                                  "PRIVACY_LOG": str(privacy_log), "PRIVACY_CHANGE": "1"},
                             text=True, capture_output=True, check=True)
    assert changed.stdout.strip() == "terminal federated capture privacy epoch changed"


def test_dbsctr_runtime_health_is_advisory_and_normalized(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "herdr.log"
    herdr = bin_dir / "herdr"
    herdr.write_text(
        "#!/bin/sh\nprintf '<%s>\\n' \"$@\" > \"$HERDR_LOG\"\n"
        "[ \"$HERDR_MODE\" = fail ] && { printf 'private failure /Users/nope\\n' >&2; exit 9; }\n"
        "[ \"$HERDR_MODE\" = malformed ] && { printf 'not-json\\n'; exit 0; }\n"
        "[ \"$HERDR_MODE\" = missing ] && { printf '{\"result\":{\"pane\":null}}\\n'; exit 0; }\n"
        "[ \"$HERDR_MODE\" = timeout ] && exec sleep 5\n"
        "[ \"$HERDR_MODE\" = descendant ] && { sleep 5 & exit 0; }\n"
        "[ \"$HERDR_MODE\" = oversized ] && { dd if=/dev/zero bs=70000 count=1 2>/dev/null; exit 0; }\n"
        "[ \"$HERDR_MODE\" = combined ] && { dd if=/dev/zero bs=40000 count=1 2>/dev/null; dd if=/dev/zero bs=40000 count=1 2>/dev/null | cat >&2; exit 0; }\n"
        "printf '{\"result\":{\"pane\":{\"agent\":\"opencode\",\"agent_session\":{\"value\":\"%s\"},\"agent_status\":\"idle\",\"cwd\":\"%s\",\"pane_id\":\"w1:p2\",\"tab_id\":\"w1:t2\",\"workspace_id\":\"w1\",\"terminal_id\":\"term_1\"}}}\\n' \"${HERDR_SESSION:-session-1}\" \"$HERDR_CWD\"\n"
    )
    herdr.chmod(0o755)
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (
        f'import {{ runtimeHealth }} from {json.dumps(str(runtime))};'
        'console.log(JSON.stringify(await runtimeHealth(process.cwd(),{sessionID:"session-1",worktree:process.cwd()},process.env)));'
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "HERDR_LOG": str(log),
           "HERDR_CWD": str(ROOT), "HERDR_ENV": "1"}
    healthy = subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True,
                             capture_output=True, check=True)
    assert json.loads(healthy.stdout) == {
        "status": "healthy", "agent_status": "idle", "pane_id": "w1:p2",
        "tab_id": "w1:t2", "workspace_id": "w1", "terminal_id": "term_1",
    }
    assert log.read_text().splitlines() == ["<pane>", "<current>"]
    equivalent = tmp_path / "equivalent-worktree"
    equivalent.symlink_to(ROOT)
    same = subprocess.run(["bun", "-e", script], cwd=ROOT, env={**env, "HERDR_CWD": str(equivalent)},
                          text=True, capture_output=True, check=True)
    assert json.loads(same.stdout)["status"] == "healthy"
    for mode, expected in (("missing", "missing"), ("malformed", "ambiguous"), ("fail", "unavailable")):
        result = subprocess.run(["bun", "-e", script], cwd=ROOT, env={**env, "HERDR_MODE": mode},
                                text=True, capture_output=True, check=True)
        assert json.loads(result.stdout) == {"status": expected}
    for mode in ("timeout", "descendant", "oversized", "combined"):
        started = time.monotonic()
        result = subprocess.run(["bun", "-e", script], cwd=ROOT, env={**env, "HERDR_MODE": mode},
                                text=True, capture_output=True, check=True)
        assert json.loads(result.stdout) == {"status": "unavailable"}, mode
        assert time.monotonic() - started < 4
    mismatch = subprocess.run(["bun", "-e", script], cwd=ROOT,
                              env={**env, "HERDR_SESSION": "other-session"}, text=True,
                              capture_output=True, check=True)
    assert json.loads(mismatch.stdout) == {"status": "ambiguous"}
    unavailable = subprocess.run(["bun", "-e", script], cwd=ROOT,
                                 env={key: value for key, value in env.items() if key != "HERDR_ENV"},
                                 text=True, capture_output=True, check=True)
    assert json.loads(unavailable.stdout) == {"status": "unavailable"}


def test_dbsctr_runtime_health_tool_serializes_missing_cwd(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    herdr = bin_dir / "herdr"
    herdr.write_text("#!/bin/sh\nprintf '{\"result\":{\"pane\":{\"agent\":\"opencode\"}}}\\n'\n")
    herdr.chmod(0o755)
    tools = OC / "tools/dbsctr.ts"
    script = (f'import {{ runtime_health }} from {json.dumps(str(tools))};'
              'const value=await runtime_health.execute({},'
              '{worktree:process.cwd(),sessionID:"session-1"});console.log(value);')
    result = subprocess.run(
        ["bun", "-e", script], cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "HERDR_ENV": "1"},
        text=True, capture_output=True, check=True,
    )
    assert json.loads(result.stdout) == {"status": "ambiguous"}


def test_dbsctr_begin_runs_without_a_prompt(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    helper_log = tmp_path / "helper.log"
    helper = bin_dir / "dbsctrctl"
    helper.write_text("#!/bin/sh\nprintf '<%s>\\n' \"$@\" > \"$HELPER_LOG\"\nprintf '{\"worktree\":\"/tmp/cycle\"}\\n'\n")
    helper.chmod(0o755)
    tools = OC / "tools/dbsctr.ts"
    script = f'''import {{ begin }} from {json.dumps(str(tools))};
 const context = {{ worktree: process.cwd(), directory: process.cwd(), sessionID: "session-tool", messageID: "message-tool", ask: async () => {{
  throw new Error("unexpected prompt");
}} }};
try {{ console.log(await begin.execute({{cycleId:"x",context:"ctx",risk:"routine",deliveryIntent:"local",planPath:"/tmp/plan"}}, context)); }}
catch (error) {{ console.error(error.message); process.exit(1); }}'''
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "HELPER_LOG": str(helper_log)}
    result = subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True,
                            capture_output=True, check=True)
    assert helper_log.read_text().splitlines() == [
        "<begin>", "<--cycle-id>", "<x>", "<--context>", "<ctx>",
        "<--risk>", "<routine>", "<--delivery-intent>", "<local>",
        "<--plan>", "</tmp/plan>", "<--opencode-session-id>", "<session-tool>",
        "<--opencode-message-id>", "<message-tool>",
        "<--opencode-directory>", f"<{ROOT}>", "<--opencode-worktree>", f"<{ROOT}>",
        "<--harness-activation-json>",
        '<{"schema_version":1,"core_revision":"3.29","overlays":{"build":"neutral-2026-07-26","build-gpt":"openai-2026-07-26","build-claude":"anthropic-2026-07-26"}}>',
    ]


def test_vm_handoff_requires_typed_approval_and_preserves_argv(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    asks = tmp_path / "asks"
    opencode_vm = bin_dir / "sandbox-vm"
    opencode_vm.write_text(
        '#!/bin/sh\ncase "$1" in build-workspace) printf "workspace1\\n";; '
        'instance) printf "workspace1-sandbox\\n";; esac\n'
    )
    limactl = bin_dir / "limactl"
    limactl.write_text(
        '#!/bin/sh\nprintf "CALL\\n" >> "$VM_CALLS"\nprintf "<%s>\\n" "$@" >> "$VM_CALLS"\n'
        'case "$*" in *"printenv HOME"*) printf "/home/test.guest\\n";; '
        '*"workspace create"*) printf \'{"result":{"root_pane":{"pane_id":"w1:p1","workspace_id":"w1"}}}\\n\';; '
        '*) printf \'{"result":{"agent":{"pane_id":"w1:p1","tab_id":"w1:t1","workspace_id":"w1","agent_session":{"value":"session-vm"}}}}\\n\';; esac\n'
    )
    opencode_vm.chmod(0o755)
    limactl.chmod(0o755)
    tools = OC / "tools/dbsctr.ts"
    payload = {
        "workerId": "dbsctr-12345678",
        "proceed": True,
        "risk": "elevated",
        "summary": "Implement the approved sandbox change",
        "paths": ["dot_local/bin/executable_sandbox-vm"],
        "validation": ["pytest tests/test_lima_sandbox.py"],
    }
    script = f'''import {{ vm_handoff }} from {json.dumps(str(tools))};
const context={{worktree:process.cwd(),ask:async (value)=>{{await Bun.write(process.env.ASKS,JSON.stringify(value));}}}};
console.log(await vm_handoff.execute({json.dumps(payload)},context));'''
    result = subprocess.run(
        ["bun", "-e", script], cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "VM_CALLS": str(calls), "ASKS": str(asks)},
        text=True, capture_output=True, check=True,
    )
    assert json.loads(result.stdout)["session_id"] == "session-vm"
    assert json.loads(result.stdout)["target"] == "workspace1"
    assert json.loads(asks.read_text())["permission"] == "dbsctr_vm_handoff"
    assert json.loads(asks.read_text())["patterns"] == ["workspace1"]
    log = calls.read_text()
    assert "<herdr>" in log
    assert "<workspace>" in log
    assert "<--kind>" in log
    assert "<--pane>" in log
    assert "<--interactive>" in log
    limactl.write_text(
        '#!/bin/sh\nprintf "CALL\\n" >> "$VM_CALLS"\nprintf "<%s>\\n" "$@" >> "$VM_CALLS"\n'
        'case "$*" in *"printenv HOME"*) printf "/home/test.guest\\n";; '
        '*"workspace create"*) printf \'{"result":{"root_pane":{"pane_id":"w1:p1","workspace_id":"w1"}}}\\n\';; '
        '*) printf \'{"error":"launch failed"}\\n\';; esac\n'
    )
    missing_identity = subprocess.run(
        ["bun", "-e", script], cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "VM_CALLS": str(calls), "ASKS": str(asks)},
        text=True, capture_output=True,
    )
    assert missing_identity.returncode != 0
    assert "no launch identity" in missing_identity.stderr
    limactl.write_text(
        '#!/bin/sh\nprintf "CALL\\n" >> "$VM_CALLS"\nprintf "<%s>\\n" "$@" >> "$VM_CALLS"\n'
        'case "$*" in *"printenv HOME"*) printf "/home/test.guest\\n";; '
        '*"workspace create"*) printf \'{"result":{"root_pane":{"pane_id":"w1:p1","workspace_id":"w1"}}}\\n\';; '
        '*) printf \'{"result":{"agent":{"pane_id":"w2:p2","workspace_id":"w2"}}}\\n\';; esac\n'
    )
    mismatched_identity = subprocess.run(
        ["bun", "-e", script], cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "VM_CALLS": str(calls), "ASKS": str(asks)},
        text=True, capture_output=True,
    )
    assert mismatched_identity.returncode != 0
    assert "no launch identity" in mismatched_identity.stderr
    before = calls.read_text()
    for path in ("/etc/passwd", "a//b", "a/", "a\\b", "a\nb"):
        unsafe = {**payload, "paths": [path]}
        unsafe_script = f'''import {{ vm_handoff }} from {json.dumps(str(tools))};
const context={{worktree:process.cwd(),ask:async ()=>{{}}}};
await vm_handoff.execute({json.dumps(unsafe)},context);'''
        rejected = subprocess.run(
            ["bun", "-e", unsafe_script], cwd=ROOT,
            env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "VM_CALLS": str(calls)},
            text=True, capture_output=True,
        )
        assert rejected.returncode != 0
    for unsafe in (
        {**payload, "summary": "Contact dev@example.com"},
        {**payload, "summary": "password=hunter2"},
        {**payload, "validation": ["Bearer not-a-real-token"]},
        {**payload, "summary": "ghp_" + "a" * 36},
    ):
        unsafe_script = f'''import {{ vm_handoff }} from {json.dumps(str(tools))};
const context={{worktree:process.cwd(),ask:async ()=>{{}}}};
await vm_handoff.execute({json.dumps(unsafe)},context);'''
        rejected = subprocess.run(
            ["bun", "-e", unsafe_script], cwd=ROOT,
            env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "VM_CALLS": str(calls)},
            text=True, capture_output=True,
        )
        assert rejected.returncode != 0
    assert calls.read_text() == before


def test_federated_runtime_rejects_duplicate_sources(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    manifest = json.dumps({
        "schema_version": 2,
        "sources": [
            {"source_id": "host", "availability": "complete"},
            {"source_id": "host", "availability": "complete"},
            {"source_id": "workspace2", "availability": "complete"},
        ],
        "source_state": None,
        "manifest_digest": "a" * 64,
    })
    helper = bin_dir / "sandbox-vm"
    helper.write_text(f"#!/bin/sh\ncat <<'EOF'\n{manifest}\nEOF\n")
    helper.chmod(0o755)
    sandbox_config = tmp_path / "sandbox.json"
    sandbox_config.write_text(json.dumps({"workspaces": [
        {"name": "workspace1", "federate": True}, {"name": "workspace2", "federate": True},
    ]}))
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = f'import {{ reviewFederated }} from {json.dumps(str(runtime))};await reviewFederated({{limit:5,cursor:0}},process.cwd());'
    result = subprocess.run(
        ["bun", "-e", script], cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
             "OPENCODE_VM_CONFIG": str(sandbox_config)},
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "invalid federation manifest" in result.stderr

def test_federated_runtime_validates_filters_and_manifest_digest(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sources = [
        {"source_id": source, "availability": "complete"}
        for source in ("host", "workspace1", "workspace2")
    ]
    query = {
        "after": None, "archive_only": False, "before": None, "context": "dotfiles_ai_distribution", "cycle_id": None,
        "method_revision": None, "project_digest": None, "reviewed_status": None, "state": None,
    }
    correct = federated_digest(query, sources)
    manifest = {"schema_version": 2, "sources": sources, "source_state": None, "manifest_digest": correct}
    helper = bin_dir / "sandbox-vm"
    helper.write_text(f"#!/bin/sh\nprintf '<%s>\\n' \"$@\" > \"$FEDERATED_LOG\"\nprintf '%s\\n' '{json.dumps(manifest)}'\n")
    helper.chmod(0o755)
    sandbox_config = tmp_path / "sandbox.json"
    sandbox_config.write_text(json.dumps({"workspaces": [
        {"name": "workspace1", "federate": True}, {"name": "workspace2", "federate": True},
    ]}))
    runtime = OC / "lib/dbsctr-runtime.ts"
    script = (f'import {{ reviewFederated }} from {json.dumps(str(runtime))};'
              'await reviewFederated({limit:5,context:"dotfiles_ai_distribution"},process.cwd());')
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FEDERATED_LOG": str(tmp_path / "args"),
           "OPENCODE_VM_CONFIG": str(sandbox_config)}
    subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    assert "<--context>\n<dotfiles_ai_distribution>" in (tmp_path / "args").read_text()
    helper.write_text(f"#!/bin/sh\nprintf '%s\\n' '{json.dumps({**manifest, 'manifest_digest': 'a' * 64})}'\n")
    result = subprocess.run(["bun", "-e", script], cwd=ROOT,
                            env=env,
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert "invalid federation manifest" in result.stderr

    swapped = [sources[0], sources[2], sources[1]]
    reordered = {"schema_version": 2, "sources": swapped, "source_state": None,
                 "manifest_digest": federated_digest(query, swapped)}
    helper.write_text(f"#!/bin/sh\nprintf '%s\\n' '{json.dumps(reordered)}'\n")
    result = subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert "invalid federation manifest" in result.stderr

    query_digest = hashlib.sha256(json.dumps(query, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    states = [{
        "source_id": source, "snapshot": 1, "session_ceiling": 1, "part_ceiling": 1,
        "database_digest": "b" * 64, "exclusion_digest": None, "query_digest": query_digest,
        "capture_id": "c" * 24, "continuation": 5 if source == "host" else None,
    } for source in ("host", "workspace1", "workspace2")]
    unavailable_sources = [
        {"source_id": "host", "availability": "missing_instance"},
        {"source_id": "workspace1", "availability": "complete"},
        {"source_id": "workspace2", "availability": "complete"},
    ]
    malicious = {
        "schema_version": 2,
        "sources": unavailable_sources,
        "source_state": states,
        "manifest_digest": federated_digest(query, unavailable_sources),
    }
    helper.write_text(f"#!/bin/sh\nprintf '%s\\n' '{json.dumps(malicious)}'\n")
    result = subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert "invalid federation manifest" in result.stderr


def test_autonomous_review_uses_full_capture_pages_without_resaving_cohorts():
    command = text("private_dot_config/opencode/commands/dbsctr-improve.md")
    assert "`dbsctr_review_federated` with `limit=100`" in command
    assert "Do not call\n   `dbsctr_review_history_save`" in command


def test_removed_managed_integrations_are_absent():
    removed = (
        "private_Library/LaunchAgents/ai.headroom.proxy.bedrock.plist",
        "private_Library/LaunchAgents/ai.headroom.proxy.lmstudio.plist",
        "docs/adr/ADR-001-omo-removal.md",
    )
    assert not [path for path in removed if (ROOT / path).exists()]
    assert not list((ROOT / "private_dot_config/meridian").glob("*"))
    assert {line for line in text(".chezmoiremove").splitlines() if line and not line.startswith("#")} == {
        ".hermes/skills/dbsctr-supervisor/SKILL.md",
        ".hermes/scripts/dbsctr-watchdog.py",
        ".local/bin/hermes-update",
        ".local/bin/opencode-vm",
            "Library/LaunchAgents/dev.dotfiles-ai.hermes-update.plist",
    }
