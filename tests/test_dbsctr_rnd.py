import fcntl
import json
import os
import plistlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def values(enabled=True, review_workdir="/tmp/dotfiles-ai"):
    return {
        "dotfiles_ai": {
            "opencode": {
                "bedrock_region": "us-west-2", "bedrock_profile": "",
                "default_model": "openai/gpt-5.6-sol", "small_model": "openai/gpt-5.6-terra",
                "lmstudio_base_url": "http://127.0.0.1:1234/v1",
            },
            "herdr": {"theme": "catppuccin", "launchagent": True, "executable": "/mock/herdr"},
            "rnd": {
                "enabled": enabled, "review_workdir": review_workdir,
                "review_hour": 9, "review_minute": 15, "watchdog_interval_seconds": 300,
                "workspace_label": "DBSCTR R&D", "github_account": "test-user",
                "github_repository": "test-user/dotfiles-ai",
            },
            "onepassword": {"enabled": False, "account": "", "user_uuid": "", "keychain_service": "op"},
        }
    }


def chezmoi(*args, enabled=True):
    return subprocess.run([
        "chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
        "--override-data", json.dumps(values(enabled)), *args,
    ], text=True, capture_output=True, check=True)


def render(path, data=None):
    return subprocess.run([
        "chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
        "--override-data", json.dumps(data or values()), "execute-template",
    ], input=(ROOT / path).read_text(), text=True, capture_output=True, check=True).stdout


def test_rnd_schedule_is_machine_local_opt_in():
    enabled = set(chezmoi("managed").stdout.splitlines())
    disabled = set(chezmoi("managed", enabled=False).stdout.splitlines())
    jobs = {
        "Library/LaunchAgents/dev.dotfiles-ai.dbsctr-spawner.plist",
        "Library/LaunchAgents/dev.dotfiles-ai.dbsctr-watchdog.plist",
    }
    assert jobs <= enabled
    assert not jobs & disabled
    assert ".local/bin/dbsctr-rnd" in disabled
    assert not (ROOT / "dot_local/bin/executable_hermes-update").exists()
    assert not (ROOT / "private_Library/LaunchAgents/dev.dotfiles-ai.hermes-update.plist.tmpl").exists()


def test_launchd_uses_native_daily_and_interval_schedules():
    spawner = chezmoi("cat", str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.dbsctr-spawner.plist")).stdout
    watchdog = chezmoi("cat", str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.dbsctr-watchdog.plist")).stdout
    assert "<key>Hour</key>\n        <integer>9</integer>" in spawner
    assert "<key>Minute</key>\n        <integer>15</integer>" in spawner
    assert "RunAtLoad" not in spawner
    assert "<key>StartInterval</key>\n    <integer>300</integer>" in watchdog
    assert "<key>RunAtLoad</key>\n    <true/>" in watchdog
    assert plistlib.loads(spawner.encode())["StartCalendarInterval"] == {"Hour": 9, "Minute": 15}
    assert plistlib.loads(watchdog.encode())["StartInterval"] == 300


def test_disabled_loader_removes_only_replacement_jobs():
    loader = render("run_onchange_after_load-dbsctr-rnd-launchagents.sh.tmpl", values(False))
    subprocess.run(["bash", "-n"], input=loader, text=True, check=True)
    assert "dev.dotfiles-ai.dbsctr-spawner" in loader
    assert "dev.dotfiles-ai.dbsctr-watchdog" in loader
    assert "bootout" in loader and "PlistBuddy" in loader
    assert 'bootout "$DOMAIN/dev.dotfiles-ai.hermes-update"' in loader
    assert "hermes-review-cron-id" in loader
    assert "hermes-watchdog-cron-id" in loader
    assert "hermes-watchdog.json" in loader
    assert '"$HOME/.local/bin/hermes" cron remove "$job_id"' in loader
    assert "^[0-9a-f]{12}$" in loader


def test_enabled_loader_is_valid_bash():
    subprocess.run(
        ["bash", "-n"], input=render("run_onchange_after_load-dbsctr-rnd-launchagents.sh.tmpl"),
        text=True, check=True,
    )


def test_spawn_creates_single_pane_worker_and_registers_exact_session(tmp_path):
    workdir = tmp_path / "source"
    workdir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    herdr = bin_dir / "herdr"
    dbsctrctl = bin_dir / "dbsctrctl"
    opencode = bin_dir / "opencode"
    herdr.write_text(
        "#!/bin/sh\n"
        "printf 'herdr %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "case \"$1 $2\" in\n"
        "  'workspace list') printf '%s\\n' '{\"result\":{\"workspaces\":[]}}';;\n"
        "  'workspace create') printf '%s\\n' '{\"result\":{\"workspace\":{\"workspace_id\":\"w7\"}}}';;\n"
        "  'tab create') printf '%s\\n' '{\"result\":{\"root_pane\":{\"tab_id\":\"w7:t0\",\"pane_id\":\"w7:p0\"},\"tab\":{\"tab_id\":\"w7:t0\"}}}';;\n"
        "  'agent start') printf '%s\\n' '{\"result\":{\"pane_id\":\"w7:p9\"}}';;\n"
        "  'pane move') printf '%s\\n' '{\"result\":{\"move_result\":{\"created_tab\":{\"tab_id\":\"w7:t9\"},\"previous_tab_id\":\"w7:t0\"}}}';;\n"
        "  'pane list') printf '%s\\n' '{\"result\":{\"panes\":[{\"tab_id\":\"w7:t0\",\"pane_id\":\"w7:p0\"},{\"tab_id\":\"w7:t9\",\"pane_id\":\"w7:p9\"}]}}';;\n"
        "  'pane process-info') printf '%s\\n' '{\"result\":{\"process_info\":{\"foreground_processes\":[{\"argv\":[\"opencode\",\"run\",\"--agent\",\"build\",\"--command\",\"dbsctr-improve\",\"--interactive\"]}]}}}';;\n"
        "  'agent list') printf '%s\\n' '{\"result\":{\"agents\":[{\"pane_id\":\"w7:p9\",\"agent_session\":{\"value\":\"ses_test\"},\"agent_status\":\"working\"}]}}';;\n"
        "  'tab close') printf '%s\\n' '{\"result\":{}}';;\n"
        "esac\n"
    )
    dbsctrctl.write_text(
        "#!/bin/sh\nprintf 'dbsctrctl %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "printf '%s\\n' '{\"worker_id\":\"registered\",\"state\":\"reviewing\"}'\n"
    )
    opencode.write_text(
        "#!/bin/sh\nif [ -f \"$SESSION_SEEN\" ]; then "
        f"printf '%s\\n' '[{{\"id\":\"ses_fallback\",\"directory\":\"{workdir}\"}}]'; "
        "else touch \"$SESSION_SEEN\"; printf '[]\\n'; fi\n"
    )
    herdr.chmod(0o755)
    dbsctrctl.chmod(0o755)
    opencode.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl", values(review_workdir=str(workdir))))
    env = {**os.environ, "HERDR": str(herdr), "DBSCTRCTL": str(dbsctrctl),
           "OPENCODE_BIN": str(opencode), "COMMAND_LOG": str(log),
           "SESSION_SEEN": str(tmp_path / "session-seen")}
    completed = subprocess.run(["python3", str(runner), "spawn"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout)["worker_id"] == "registered"
    commands = log.read_text()
    assert "opencode run --agent build --command dbsctr-improve --interactive" in commands
    assert "pane move w7:p9 --new-tab" in commands
    assert "tab close w7:t0" in commands
    assert "improvement-register" in commands
    assert "--session-id ses_test --workspace-id w7 --tab-id w7:t9 --pane-id w7:p9" in commands
    no_identity = herdr.read_text().replace(
        '{"pane_id":"w7:p9","agent_session":{"value":"ses_test"},"agent_status":"working"}',
        '{"pane_id":"w7:p9","agent_status":"working"}',
    )
    herdr.write_text(no_identity)
    Path(env["SESSION_SEEN"]).unlink(missing_ok=True)
    failed = bin_dir / "dbsctrctl-fail"
    failed.write_text("#!/bin/sh\nexit 1\n")
    failed.chmod(0o755)
    rejected = subprocess.run(
        ["python3", str(runner), "spawn"],
        env={**env, "DBSCTRCTL": str(failed)}, text=True, capture_output=True,
    )
    assert rejected.returncode != 0
    assert log.read_text().count("tab close w7:t9") == 1
    empty = bin_dir / "opencode-empty"
    empty.write_text("#!/bin/sh\nprintf '[]\\n'\n")
    empty.chmod(0o755)
    timed_out = subprocess.run(
        ["python3", str(runner), "spawn"],
        env={**env, "OPENCODE_BIN": str(empty), "DBSCTR_RND_SESSION_POLLS": "1"},
        text=True, capture_output=True,
    )
    assert timed_out.returncode != 0
    assert log.read_text().count("tab close w7:t9") == 2


def test_watchdog_leaves_live_discovery_worker_untouched(tmp_path):
    workdir = tmp_path / "source"
    workdir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    herdr = bin_dir / "herdr"
    dbsctrctl = bin_dir / "dbsctrctl"
    dbsctrctl.write_text(
        "#!/bin/sh\nprintf 'dbsctrctl %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "printf '%s\\n' '{\"workers\":[{\"worker_id\":\"worker-1\",\"session_id\":\"ses_1\",\"state\":\"discovery\",\"recovery_attempts\":0}]}'\n"
    )
    herdr.write_text(
        "#!/bin/sh\nprintf 'herdr %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "printf '%s\\n' '{\"result\":{\"agents\":[{\"agent_session\":{\"value\":\"ses_1\"},\"agent_status\":\"blocked\"}]}}'\n"
    )
    herdr.chmod(0o755)
    dbsctrctl.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl", values(review_workdir=str(workdir))))
    lock = tmp_path / "watchdog.lock"
    env = {**os.environ, "HERDR": str(herdr), "DBSCTRCTL": str(dbsctrctl),
           "COMMAND_LOG": str(log), "DBSCTR_RND_LOCK": str(lock)}
    completed = subprocess.run(["python3", str(runner), "watchdog"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout) == {"events": []}
    commands = log.read_text()
    assert "improvement-recover" not in commands
    assert "agent start" not in commands
    herdr.write_text(
        "#!/bin/sh\nprintf 'herdr %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "printf '%s\\n' '{\"result\":{\"agents\":[{\"agent_session\":{\"value\":\"ses_1\"},\"agent_status\":\"unknown\"}]}}'\n"
    )
    unknown = subprocess.run(["python3", str(runner), "watchdog"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(unknown.stdout)["events"][0]["status"] == "unknown"
    assert "improvement-update --worker-id worker-1 --state blocked" in log.read_text()
    with lock.open("a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        duplicate = subprocess.run(["python3", str(runner), "watchdog"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(duplicate.stdout)["status"] == "already_running"


def test_watchdog_recovers_only_missing_exact_session(tmp_path):
    workdir = tmp_path / "source"
    workdir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    marker = tmp_path / "started"
    herdr = bin_dir / "herdr"
    dbsctrctl = bin_dir / "dbsctrctl"
    dbsctrctl.write_text(
        "#!/bin/sh\nprintf 'dbsctrctl %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "if [ \"$1\" = improvement-status ]; then printf '%s\\n' "
        "'{\"workers\":[{\"worker_id\":\"worker-1\",\"session_id\":\"ses_1\",\"state\":\"reviewing\",\"recovery_attempts\":0}]}'; "
        "else printf '%s\\n' '{\"worker_id\":\"worker-1\",\"session_id\":\"ses_1\",\"state\":\"reviewing\",\"recovery_attempts\":0}'; fi\n"
    )
    herdr.write_text(
        "#!/bin/sh\nprintf 'herdr %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "case \"$1 $2\" in\n"
        "  'agent list') if [ -f \"$STARTED\" ]; then printf '%s\\n' '{\"result\":{\"agents\":[{\"pane_id\":\"w7:p9\",\"agent_session\":{\"value\":\"ses_1\"},\"agent_status\":\"working\"}]}}'; else printf '%s\\n' '{\"result\":{\"agents\":[]}}'; fi;;\n"
        "  'workspace list') printf '%s\\n' '{\"result\":{\"workspaces\":[{\"workspace_id\":\"w7\",\"label\":\"DBSCTR R&D\"}]}}';;\n"
        "  'tab create') printf '%s\\n' '{\"result\":{\"root_pane\":{\"tab_id\":\"w7:t0\",\"pane_id\":\"w7:p0\"},\"tab\":{\"tab_id\":\"w7:t0\"}}}';;\n"
        "  'agent start') touch \"$STARTED\"; printf '%s\\n' '{\"result\":{\"pane_id\":\"w7:p9\"}}';;\n"
        "  'pane move') printf '%s\\n' '{\"result\":{\"move_result\":{\"created_tab\":{\"tab_id\":\"w7:t9\"},\"previous_tab_id\":\"w7:t0\"}}}';;\n"
        "  'pane list') printf '%s\\n' '{\"result\":{\"panes\":[{\"tab_id\":\"w7:t0\",\"pane_id\":\"w7:p0\"},{\"tab_id\":\"w7:t9\",\"pane_id\":\"w7:p9\"}]}}';;\n"
        "  'tab close') printf '%s\\n' '{\"result\":{}}';;\n"
        "esac\n"
    )
    herdr.chmod(0o755)
    dbsctrctl.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl", values(review_workdir=str(workdir))))
    env = {**os.environ, "HERDR": str(herdr), "DBSCTRCTL": str(dbsctrctl),
           "COMMAND_LOG": str(log), "STARTED": str(marker),
           "DBSCTR_RND_LOCK": str(tmp_path / "watchdog.lock")}
    completed = subprocess.run(["python3", str(runner), "watchdog"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout)["events"][0]["status"] == "recovered"
    commands = log.read_text()
    assert "opencode -s ses_1 --agent build" in commands
    assert "improvement-update --worker-id worker-1 --state reviewing --workspace-id w7 --tab-id w7:t9 --pane-id w7:p9" in commands
    assert "improvement-recover --worker-id worker-1 --action success" in commands


def test_watchdog_adopts_only_exact_resumed_argv(tmp_path):
    workdir = tmp_path / "source"
    workdir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    dbsctrctl = bin_dir / "dbsctrctl"
    herdr = bin_dir / "herdr"
    dbsctrctl.write_text(
        "#!/bin/sh\nprintf 'dbsctrctl %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "printf '%s\\n' '{\"workers\":[{\"worker_id\":\"worker-1\",\"session_id\":\"ses_1\",\"state\":\"reviewing\",\"recovery_attempts\":0,\"workspace_id\":\"w7\",\"tab_id\":\"w7:t9\",\"pane_id\":\"w7:p9\"}]}'\n"
    )
    herdr.write_text(
        "#!/bin/sh\nprintf 'herdr %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "case \"$1 $2\" in\n"
        f"  'agent list') printf '%s\\n' '{{\"result\":{{\"agents\":[{{\"agent_status\":\"working\",\"cwd\":\"{workdir}\",\"workspace_id\":\"w7\",\"tab_id\":\"w7:t9\",\"pane_id\":\"w7:p9\"}}]}}}}';;\n"
        "  'pane list') printf '%s\\n' '{\"result\":{\"panes\":[{\"tab_id\":\"w7:t9\",\"pane_id\":\"w7:p9\"}]}}';;\n"
        "  'pane process-info') printf '%s\\n' '{\"result\":{\"process_info\":{\"foreground_processes\":[{\"argv\":[\"opencode\",\"-s\",\"ses_1\",\"--agent\",\"build\"]}]}}}';;\n"
        "esac\n"
    )
    herdr.chmod(0o755)
    dbsctrctl.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl", values(review_workdir=str(workdir))))
    env = {**os.environ, "HERDR": str(herdr), "DBSCTRCTL": str(dbsctrctl),
           "COMMAND_LOG": str(log), "DBSCTR_RND_LOCK": str(tmp_path / "watchdog.lock")}
    completed = subprocess.run(["python3", str(runner), "watchdog"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout) == {"events": []}
    assert "improvement-recover" not in log.read_text()
    exact = herdr.read_text()
    variants = (
        exact.replace('["opencode","-s","ses_1","--agent","build"]', '["opencode","-s","ses_1","--agent","plan"]'),
        exact.replace(str(workdir), "/tmp/unmanaged"),
        exact.replace(
            '[{"tab_id":"w7:t9","pane_id":"w7:p9"}]',
            '[{"tab_id":"w7:t9","pane_id":"w7:p9"},{"tab_id":"w7:t9","pane_id":"w7:p10"}]',
        ),
        exact.replace(
            '[{"argv":["opencode","-s","ses_1","--agent","build"]}]',
            '[{"argv":["opencode","-s","ses_1","--agent","build"]},{"argv":["opencode","-s","ses_1","--agent","build"]}]',
        ),
    )
    for index, variant in enumerate(variants):
        herdr.write_text(variant)
        ambiguous = subprocess.run(
            ["python3", str(runner), "watchdog"],
            env={**env, "DBSCTR_RND_LOCK": str(tmp_path / f"bad-{index}.lock")},
            text=True, capture_output=True, check=True,
        )
        assert json.loads(ambiguous.stdout)["events"][0]["status"] == "ambiguous"


def test_watchdog_records_human_pr_outcome(tmp_path):
    workdir = tmp_path / "source"
    workdir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    dbsctrctl = bin_dir / "dbsctrctl"
    herdr = bin_dir / "herdr"
    gh = bin_dir / "gh"
    dbsctrctl.write_text(
        "#!/bin/sh\nprintf 'dbsctrctl %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "if [ \"$1\" = improvement-status ]; then printf '%s\\n' "
        "'{\"workers\":[{\"worker_id\":\"worker-1\",\"session_id\":\"ses_1\",\"state\":\"draft_pr\",\"recovery_attempts\":0,\"pr_url\":\"https://github.com/test/repo/pull/1\"}]}'; "
        "else printf '%s\\n' '{\"worker_id\":\"worker-1\",\"state\":\"merged\",\"recovery_attempts\":0}'; fi\n"
    )
    herdr.write_text("#!/bin/sh\nprintf '%s\\n' '{\"result\":{\"agents\":[]}}'\n")
    gh.write_text(
        "#!/bin/sh\nprintf 'gh %s token=%s\\n' \"$*\" \"${GH_TOKEN:+set}\" >> \"$COMMAND_LOG\"\n"
        "if [ \"$1 $2\" = 'auth token' ]; then printf 'secret-token\\n'; "
        "else printf '%s\\n' '{\"state\":\"MERGED\",\"isDraft\":false}'; fi\n"
    )
    for executable in (dbsctrctl, herdr, gh):
        executable.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl", values(review_workdir=str(workdir))))
    env = {**os.environ, "HERDR": str(herdr), "DBSCTRCTL": str(dbsctrctl), "GH": str(gh),
           "COMMAND_LOG": str(log), "DBSCTR_RND_LOCK": str(tmp_path / "watchdog.lock")}
    completed = subprocess.run(["python3", str(runner), "watchdog"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout) == {"events": []}
    commands = log.read_text()
    assert "improvement-update --worker-id worker-1 --state merged" in commands
    assert "gh pr view" in commands and "token=set" in commands
    assert "secret-token" not in commands


def test_example_documents_only_neutral_rnd_settings():
    example = (ROOT / "config.example.toml").read_text()
    for term in ("[data.dotfiles_ai.rnd]", "enabled = false", "review_hour", "review_minute",
                 "watchdog_interval_seconds", "workspace_label", "github_account", "github_repository"):
        assert term in example
    assert "hermes" not in example.lower()
    assert "Saltiola7" not in example
    retired = (ROOT / ".chezmoiremove").read_text()
    assert ".hermes/skills/dbsctr-supervisor/SKILL.md" in retired
    assert ".hermes/scripts/dbsctr-watchdog.py" in retired
