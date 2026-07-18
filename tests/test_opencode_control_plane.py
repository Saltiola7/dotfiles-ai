import json
import os
import subprocess
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
    }
}


def text(path: str) -> str:
    return (ROOT / path).read_text()


def rendered_config(env: dict[str, str] | None = None) -> dict:
    result = subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(DATA),
            "cat", str(Path.home() / ".config/opencode/opencode.json"),
        ],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **(env or {})},
    )
    return json.loads(result.stdout)


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


def test_provider_affine_task_permissions():
    expected = {
        "build-gpt.md": ("explore-openai", "scout-openai", "builder-openai"),
        "build-claude.md": ("explore-bedrock", "scout-bedrock", "builder-bedrock"),
    }
    for name, allowed in expected.items():
        body = (OC / "agents" / name).read_text()
        assert '"*": deny' in body
        for agent in allowed:
            assert f"{agent}: allow" in body


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
    assert config["permission"]["external_directory"] == "deny"
    assert config["agent"]["build"]["permission"] == {
        "dbsctr_begin": "allow",
        "dbsctr_attach": "allow",
        "dbsctr_improvement_claim": "allow",
        "dbsctr_improvement_update": "allow",
        "external_directory": {worktrees: "allow", local_config: "allow"},
    }

    build_primaries = {"build-gpt.md", "build-claude.md"}
    for agent in (OC / "agents").glob("*.md"):
        body = agent.read_text()
        if agent.name in build_primaries:
            assert "mode: primary" in body
            assert "dbsctr_begin: allow" in body
            assert "dbsctr_attach: allow" in body
            assert f"external_directory:\n    {worktrees}: allow" in body
            assert f"    {local_config}: allow" in body
        else:
            assert "mode: subagent" in body
            assert "dbsctr_begin: allow" not in body
            assert "dbsctr_attach: allow" not in body
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
    for command in ("review-migrate", "review-backup", "review-restore", "review-prune", "review-forget"):
        for form in ("dbsctrctl {}*", "*/dbsctrctl {}*", "env *dbsctrctl {}*", "command *dbsctrctl {}*"):
            assert bash[form.format(command)] == "ask"
    assert bash["dbsctrctl cleanup*"] == "ask"
    for command in (
        "herdr server stop*", "herdr config reset-keys*", "herdr worktree remove*",
        "herdr workspace close*", "herdr pane close*", "herdr tab close*",
        "herdr session stop*", "herdr session delete*",
    ):
        assert bash[command] == "ask"
    assert config["permission"]["dbsctr_status"] == "allow"
    assert config["permission"]["dbsctr_begin"] == "deny"
    assert config["permission"]["dbsctr_attach"] == "deny"
    assert config["permission"]["dbsctr_audit"] == "allow"
    assert config["permission"]["dbsctr_inspect"] == "allow"
    assert config["permission"]["dbsctr_review"] == "allow"
    assert config["permission"]["dbsctr_review_complete"] == "ask"
    assert config["permission"]["dbsctr_review_history"] == "allow"
    assert config["permission"]["dbsctr_review_history_save"] == "allow"
    assert config["permission"]["dbsctr_improvement_status"] == "allow"
    assert config["permission"]["dbsctr_improvement_claim"] == "deny"
    assert config["permission"]["dbsctr_improvement_update"] == "deny"
    assert config["agent"]["plan"]["permission"]["dbsctr_begin"] == "deny"
    assert config["agent"]["plan"]["permission"]["dbsctr_attach"] == "deny"
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
    for name in ("builder-openai.md", "builder-bedrock.md"):
        assert "dbsctr_begin: deny" in (OC / "agents" / name).read_text()
        assert "dbsctr_attach: deny" in (OC / "agents" / name).read_text()
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
    assert 'export const begin = tool({' in tools
    assert 'export const audit = tool({' in tools
    assert 'export const inspect = tool({' in tools
    assert 'export const review = tool({' in tools
    assert 'export const review_complete = tool({' in tools
    assert 'export const review_history = tool({' in tools
    assert 'export const review_history_save = tool({' in tools
    assert 'export const improvement_status = tool({' in tools
    assert 'export const improvement_claim = tool({' in tools
    assert 'export const improvement_update = tool({' in tools
    assert "snapshot: tool.schema.number().int().min(0).optional()" in tools
    assert "snapshot: tool.schema.number().int().min(0)," in tools
    assert "snapshot: args.snapshot," in tools
    assert "default(false)" in tools
    runtime = (OC / "lib/dbsctr-runtime.ts").read_text()
    assert '["dbsctrctl", "status", "--json"]' in runtime
    assert '["dbsctrctl", "audit", "--commit", commit, "--json"]' in runtime
    assert '"dbsctrctl", "inspect", "--commit"' in runtime
    assert '["dbsctrctl", "review-scan"' in runtime
    assert '"dbsctrctl", "review-complete"' in runtime
    assert '"dbsctrctl", "review-history"' in runtime
    assert '"dbsctrctl", "review-history-save"' in runtime
    assert '"dbsctrctl", "improvement-status"' in runtime
    assert '"dbsctrctl", "improvement-claim"' in runtime
    assert '"dbsctrctl", "improvement-update"' in runtime
    assert runtime.count('"--excluded-session-id"') == 4
    assert "context.sessionID" in tools
    assert "context.worktree, true" in tools
    assert '"herdr", "agent", "start", "opencode"' in runtime
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
        "rubric": {"name": "history", "version": "1", "digest": "d" * 64}, "findings": [],
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
    ]


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
    ]


def test_removed_managed_integrations_are_absent():
    removed = (
        "dot_local/bin/executable_claude-personal",
        "dot_local/bin/executable_opencode-personal",
        "private_Library/LaunchAgents/ai.headroom.proxy.bedrock.plist",
        "private_Library/LaunchAgents/ai.headroom.proxy.lmstudio.plist",
        "docs/specs/opencode-personal.md",
        "docs/adr/ADR-001-omo-removal.md",
    )
    assert not [path for path in removed if (ROOT / path).exists()]
    assert not list((ROOT / "private_dot_config/meridian").glob("*"))
    assert not [line for line in text(".chezmoiremove").splitlines() if not line.startswith("#")]
