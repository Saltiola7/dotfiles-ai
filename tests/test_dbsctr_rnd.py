import concurrent.futures
import fcntl
import json
import os
import plistlib
import sqlite3
import subprocess
import sys
from pathlib import Path



ROOT = Path(__file__).parents[1]


def values(enabled=True, review_workdir="/tmp/dotfiles-ai", backend="native", roots=None):
    return {
        "dotfiles_ai": {
            "opencode": {
                "vertex_project": "", "vertex_location": "global", "vertex_credentials": "",
                "default_model": "openai/gpt-5.6-sol", "small_model": "openai/gpt-5.6-terra",
                "lmstudio_base_url": "http://127.0.0.1:1234/v1",
            },
            "herdr": {"theme": "catppuccin", "launchagent": True, "executable": "/mock/herdr"},
            "hermes": {"enabled": enabled, "executable": "~/.local/bin/hermes", "profile": "system",
                       "provider": "openai-codex", "backlog_roots": roots or [],
                       "project_profiles": False},
            "rnd": {
                "enabled": enabled, "backend": backend, "review_workdir": review_workdir,
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
    assert "gateway stop" in loader
    assert "hermes-review-cron-id" not in loader


def test_enabled_loader_is_valid_bash():
    subprocess.run(
        ["bash", "-n"], input=render("run_onchange_after_load-dbsctr-rnd-launchagents.sh.tmpl"),
        text=True, check=True,
    )


def test_hermes_backend_retires_native_jobs_only_after_health_contract():
    loader = render("run_onchange_after_load-dbsctr-rnd-launchagents.sh.tmpl",
                    values(backend="hermes"))
    subprocess.run(["bash", "-n"], input=loader, text=True, check=True)
    assert "gateway status" in loader
    assert "launchctl print" in loader and "state = running" in loader
    assert "*-cron-id" in loader
    assert "remove_job dev.dotfiles-ai.dbsctr-spawner" in loader
    assert loader.index("gateway status") < loader.index("launchctl bootstrap")


def test_hermes_templates_are_profile_local_and_valid_bash():
    installer = render("run_onchange_before_install-hermes.sh.tmpl")
    configure = render("run_onchange_after_configure-hermes.sh.tmpl")
    project_data = values()
    project_data["dotfiles_ai"]["hermes"]["project_profiles"] = True
    project_configure = render("run_onchange_after_configure-hermes.sh.tmpl", project_data)
    catalog = (ROOT / "private_dot_hermes/private_managed/private_scripts/executable_dbsctr-catalog.py.tmpl").read_text()
    subprocess.run(["bash", "-n"], input=installer, text=True, check=True)
    subprocess.run(["bash", "-n"], input=configure, text=True, check=True)
    assert "sha256sum -c -" in installer and "shasum -a 256 -c -" in installer
    assert 'hermes_agent-0.19.0-py3-none-any.whl' in installer
    assert 'UV_TOOL_DIR="$HOME/.local/share/uv/tools"' in installer
    assert 'UV_PYTHON_INSTALL_DIR="$HOME/.local/share/uv/python"' in installer
    assert 'uv python install 3.13.2' in installer
    assert 'uv tool install --force --python 3.13.2 "$wheel"' in installer
    assert '"$target" != /Volumes/*' in installer
    assert '"$runtime" != /Volumes/*' in installer
    assert 'retire_job "$state/catalog-cron-id" "dotfiles-ai project catalog"' in configure
    assert 'retire_job "$state/refinement-cron-id" "dotfiles-ai context refinement"' in project_configure
    assert '${HERMES#\\~/}' in installer
    assert 'profiles/$PROFILE' in configure
    assert 'managed_home="$HERMES_HOME/managed"' in configure
    assert '$HOME/.hermes/managed' not in configure
    assert "terminal.home_mode profile" in configure
    assert "config set model.default openai-codex/gpt-5.6-sol" in configure
    assert "config get model.provider" in configure
    assert "config get model.default" in configure
    assert "gateway install --force" in configure
    assert "state-root-exec" in configure and "plistlib" in configure
    assert 'payload.pop("WorkingDirectory", None)' in configure
    assert 'payload["StandardOutPath"]' in configure and 'payload["StandardErrorPath"]' in configure
    assert "launchctl bootout" in configure and "launchctl bootstrap" in configure
    assert "/usr/bin/shlock -p $$" in configure and "flock -n 9" in configure
    assert 'rm -f "$lock"' in configure
    assert "cron list --all" in configure and "prune_duplicate_jobs" in configure
    assert "cron remove \"$duplicate\"" in configure
    assert "launchctl print" in configure and "state = running" in configure
    assert '"config", "get", "model.provider"' in catalog
    assert '"config", "get", "model.default"' in catalog
    assert 'MANAGED_HOME / "skills/dbsctr-supervisor/SKILL.md"' in catalog
    assert '"gateway", "install", "--force", "--no-start-now"' in catalog
    assert 'payload.pop("WorkingDirectory", None)' in catalog
    assert '"state = running" in status.stdout' in catalog
    maintenance = (ROOT / "private_dot_hermes/private_managed/private_scripts/executable_dbsctr-maintain.py").read_text()
    assert '["herdr-history-maintain"]' in maintenance
    assert '["dbsctrctl", "cleanup", "--completed", "--all"]' in maintenance
    assert "cron pause" in configure and "cutover-ready" in configure


def test_hermes_mode_transition_retires_every_obsolete_job(tmp_path):
    configure = render("run_onchange_after_configure-hermes.sh.tmpl")
    helper = configure[configure.index("retire_job() {"):configure.index("\n\nretire_job ", configure.index("retire_job() {"))]
    hermes = tmp_path / "hermes"
    log = tmp_path / "calls"
    hermes.write_text("""#!/bin/bash
if [[ "$*" == *"cron list --all" ]]; then
    printf 'aaaaaaaaaaaa [active]\\n  Name:      obsolete\\nbbbbbbbbbbbb [active]\\n  Name:      obsolete\\n'
else
    printf '%s\\n' "$*" >> "$FAKE_HERMES_LOG"
fi
""")
    hermes.chmod(0o755)
    state = tmp_path / "state"
    state.mkdir()
    id_file = state / "obsolete-cron-id"
    id_file.write_text("aaaaaaaaaaaa\n")
    script = f'''set -euo pipefail
HERMES={hermes}
PROFILE=system
state={state}
{helper}
retire_job "$state/obsolete-cron-id" obsolete
'''
    subprocess.run(["bash"], input=script, text=True, check=True,
                   env={**os.environ, "FAKE_HERMES_LOG": str(log)})
    calls = log.read_text()
    assert "cron pause aaaaaaaaaaaa" in calls and "cron remove aaaaaaaaaaaa" in calls
    assert "cron pause bbbbbbbbbbbb" in calls and "cron remove bbbbbbbbbbbb" in calls
    assert not id_file.exists()


def test_supervisor_uses_argparse_safe_direct_launch_command():
    skill = render(
        "private_dot_hermes/private_managed/private_skills/private_dbsctr-supervisor/SKILL.md.tmpl"
    )
    assert (
        "dbsctr-rnd --reservation RESERVATION --worker-id WORKER_ID "
        "--repository-id REPOSITORY_ID launch"
    ) in skill
    assert "dbsctr-rnd --reservation RESERVATION --reason prelaunch_failed release" in skill
    assert "Repeatedly run `dbsctr-rnd reserve` until a no-op" in skill
    catalog = render("private_dot_hermes/private_managed/private_scripts/executable_dbsctr-catalog.py.tmpl")
    compile(catalog, "dbsctr-catalog.py", "exec")
    assert "HERMES_KANBAN_HOME" in catalog and "repository_id" in catalog
    linux_ignores = (ROOT / ".chezmoiignore").read_text().split(
        '{{ if eq .chezmoi.os "linux" }}', 1
    )[1]
    assert ".local/bin/dbsctr-rnd" not in linux_ignores
    assert ".hermes/managed" not in linux_ignores


def test_herdr_history_archives_once_daily_and_prunes_older_than_30_days(tmp_path):
    source = tmp_path / "session-history.json"
    archive = tmp_path / "archive"
    source.write_text('{"pane":"private"}\n')
    archive.mkdir(mode=0o700)
    (archive / "2026-06-01.json").write_text("old\n")
    (archive / "2026-07-01.json").write_text("boundary\n")
    script = ROOT / "dot_local/bin/executable_herdr-history-maintain"
    env = {
        **os.environ,
        "HERDR_HISTORY_SOURCE": str(source),
        "HERDR_HISTORY_ARCHIVE": str(archive),
        "HERDR_HISTORY_NOW": "2026-07-31T03:00:00+00:00",
    }
    result = subprocess.run([sys.executable, script], env=env, text=True, capture_output=True, check=True)
    report = json.loads(result.stdout)
    assert report == {"archived": True, "path": "2026-07-31.json", "pruned": 1}
    assert not (archive / "2026-06-01.json").exists()
    assert (archive / "2026-07-01.json").exists()
    snapshot = archive / "2026-07-31.json"
    assert snapshot.read_text() == source.read_text()
    assert snapshot.stat().st_mode & 0o777 == 0o600


def test_herdr_history_rejects_symlink_source(tmp_path):
    target = tmp_path / "target.json"
    target.write_text("{}\n")
    source = tmp_path / "session-history.json"
    source.symlink_to(target)
    result = subprocess.run(
        [sys.executable, ROOT / "dot_local/bin/executable_herdr-history-maintain"],
        env={**os.environ, "HERDR_HISTORY_SOURCE": str(source),
             "HERDR_HISTORY_ARCHIVE": str(tmp_path / "archive")},
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "source is unsafe" in result.stderr


def test_runner_bounds_dependency_commands(tmp_path):
    script = tmp_path / "dbsctr-rnd"
    script.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl"))
    script.chmod(0o755)
    sleeper = tmp_path / "dbsctrctl"
    sleeper.write_text("#!/bin/sh\nsleep 1\n")
    sleeper.chmod(0o755)
    result = subprocess.run(
        [str(script), "watchdog"], text=True, capture_output=True, timeout=2,
        env={**os.environ, "DBSCTRCTL": str(sleeper), "DBSCTR_RND_COMMAND_TIMEOUT": "0.05",
             "DBSCTR_RND_LOCK": str(tmp_path / "watchdog.lock"),
             "DBSCTR_RND_STATE": str(tmp_path / "state.sqlite3")},
    )
    assert result.returncode != 0
    assert "timed out" in result.stderr


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
        "if [ \"$1\" = improvement-status ]; then printf '%s\\n' '{\"workers\":[]}'; "
        "else printf '{\"worker_id\":\"%s\",\"session_id\":\"%s\",\"state\":\"reviewing\"}\\n' \"$3\" \"$5\"; fi\n"
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
    assert 'DBSCTR_RND_SESSION_POLLS", "240"' in runner.read_text()
    env = {**os.environ, "HERDR": str(herdr), "DBSCTRCTL": str(dbsctrctl),
           "OPENCODE_BIN": str(opencode), "COMMAND_LOG": str(log),
           "SESSION_SEEN": str(tmp_path / "session-seen"),
           "DBSCTR_RND_STATE": str(tmp_path / "scheduler.sqlite3")}
    completed = subprocess.run(["python3", str(runner), "spawn"], env=env, text=True, capture_output=True, check=True)
    worker_id = json.loads(completed.stdout)["worker_id"]
    assert worker_id.startswith("dbsctr-")
    commands = log.read_text()
    assert "opencode run --agent build --command dbsctr-improve --interactive" in commands
    assert "--env DBSCTR_RND_WORKER_ID=dbsctr-" in commands
    assert "pane move w7:p9 --new-tab" in commands
    assert "tab close w7:t0" in commands
    assert "improvement-register" in commands
    assert "--session-id ses_test --workspace-id w7 --tab-id w7:t9 --pane-id w7:p9" in commands
    connection = sqlite3.connect(env["DBSCTR_RND_STATE"])
    assert connection.execute("select worker_id from spawn_reservations").fetchone() == (worker_id,)
    connection.close()
    no_identity = herdr.read_text().replace(
        '{"pane_id":"w7:p9","agent_session":{"value":"ses_test"},"agent_status":"working"}',
        '{"pane_id":"w7:p9","agent_status":"working"}',
    )
    herdr.write_text(no_identity)
    Path(env["SESSION_SEEN"]).unlink(missing_ok=True)
    failed = bin_dir / "dbsctrctl-fail"
    failed.write_text(
        "#!/bin/sh\n[ \"$1\" = improvement-status ] && { printf '%s\\n' '{\"workers\":[]}'; exit 0; }\nexit 1\n"
    )
    failed.chmod(0o755)
    rejected = subprocess.run(
        ["python3", str(runner), "spawn"],
        env={**env, "DBSCTRCTL": str(failed),
             "DBSCTR_RND_STATE": str(tmp_path / "failed-scheduler.sqlite3")},
        text=True, capture_output=True,
    )
    assert rejected.returncode != 0
    assert log.read_text().count("tab close w7:t9") == 1
    empty = bin_dir / "opencode-empty"
    empty.write_text("#!/bin/sh\nexit 0\n")
    empty.chmod(0o755)
    timed_out = subprocess.run(
        ["python3", str(runner), "spawn"],
        env={**env, "OPENCODE_BIN": str(empty), "DBSCTR_RND_SESSION_POLLS": "1",
             "DBSCTR_RND_STATE": str(tmp_path / "timeout-scheduler.sqlite3")},
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
    unknown = subprocess.run(["python3", str(runner), "watchdog"], env=env, text=True, capture_output=True)
    assert unknown.returncode != 0
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
    assert f"opencode --mini {workdir} -s ses_1 --agent build --no-replay" in commands
    assert "improvement-update --worker-id worker-1 --state reviewing --workspace-id w7 --tab-id w7:t9 --pane-id w7:p9" in commands
    assert "improvement-recover --worker-id worker-1 --action success" in commands


def test_watchdog_exits_nonzero_for_degraded_worker(tmp_path):
    workdir = tmp_path / "source"
    workdir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    dbsctrctl = bin_dir / "dbsctrctl"
    herdr = bin_dir / "herdr"
    dbsctrctl.write_text(
        "#!/bin/sh\nprintf '%s\\n' "
        "'{\"workers\":[{\"worker_id\":\"worker-1\",\"session_id\":\"ses_1\","
        "\"state\":\"blocked\",\"recovery_attempts\":3}]}'\n"
    )
    herdr.write_text(
        "#!/bin/sh\nprintf '%s\\n' "
        "'{\"result\":{\"agents\":[{\"agent_session\":{\"value\":\"ses_1\"},"
        "\"agent_status\":\"blocked\"}]}}'\n"
    )
    herdr.chmod(0o755)
    dbsctrctl.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl", values(review_workdir=str(workdir))))
    completed = subprocess.run(
        ["python3", str(runner), "watchdog"],
        env={**os.environ, "HERDR": str(herdr), "DBSCTRCTL": str(dbsctrctl),
             "DBSCTR_RND_LOCK": str(tmp_path / "watchdog.lock")},
        text=True, capture_output=True,
    )
    assert completed.returncode != 0
    assert json.loads(completed.stdout) == {"events": [{"worker_id": "worker-1", "status": "blocked"}]}


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
    herdr.write_text((
        "#!/bin/sh\nprintf 'herdr %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "case \"$1 $2\" in\n"
        f"  'agent list') printf '%s\\n' '{{\"result\":{{\"agents\":[{{\"agent_status\":\"working\",\"cwd\":\"{workdir}\",\"workspace_id\":\"w7\",\"tab_id\":\"w7:t9\",\"pane_id\":\"w7:p9\"}}]}}}}';;\n"
        "  'pane list') printf '%s\\n' '{\"result\":{\"panes\":[{\"tab_id\":\"w7:t9\",\"pane_id\":\"w7:p9\"}]}}';;\n"
        "  'pane process-info') printf '%s\\n' '{\"result\":{\"process_info\":{\"foreground_processes\":[{\"argv\":[\"opencode\",\"--mini\",\"__WORKDIR__\",\"-s\",\"ses_1\",\"--agent\",\"build\",\"--no-replay\"]}]}}}';;\n"
        "esac\n"
    ).replace("__WORKDIR__", str(workdir)))
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
        exact.replace('["opencode","--mini","' + str(workdir) + '","-s","ses_1","--agent","build","--no-replay"]', '["opencode","--mini","' + str(workdir) + '","-s","ses_1","--agent","plan","--no-replay"]'),
        exact.replace(str(workdir), "/tmp/unmanaged"),
        exact.replace(
            '[{"tab_id":"w7:t9","pane_id":"w7:p9"}]',
            '[{"tab_id":"w7:t9","pane_id":"w7:p9"},{"tab_id":"w7:t9","pane_id":"w7:p10"}]',
        ),
        exact.replace(
            '[{"argv":["opencode","--mini","' + str(workdir) + '","-s","ses_1","--agent","build","--no-replay"]}]',
            '[{"argv":["opencode","--mini","' + str(workdir) + '","-s","ses_1","--agent","build","--no-replay"]},{"argv":["opencode","--mini","' + str(workdir) + '","-s","ses_1","--agent","build","--no-replay"]}]',
        ),
    )
    for index, variant in enumerate(variants):
        herdr.write_text(variant)
        ambiguous = subprocess.run(
            ["python3", str(runner), "watchdog"],
            env={**env, "DBSCTR_RND_LOCK": str(tmp_path / f"bad-{index}.lock")},
            text=True, capture_output=True,
        )
        assert ambiguous.returncode != 0
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
        "else printf '%s\\n' '{\"state\":\"MERGED\",\"isDraft\":false,\"mergeCommit\":{\"oid\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}}'; fi\n"
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


def load_runner(tmp_path, monkeypatch, name):
    state = tmp_path / f"{name}.sqlite3"
    monkeypatch.setenv("DBSCTR_RND_STATE", str(state))
    monkeypatch.setenv("DBSCTR_RND_LOCK", str(tmp_path / f"{name}.lock"))
    monkeypatch.setenv("DBSCTR_RND_RECEIPTS", str(tmp_path / f"{name}-receipts"))
    source = render("dot_local/bin/executable_dbsctr-rnd.tmpl")
    namespace = {"__name__": f"dbsctr_rnd_{name}"}
    exec(source.split("\nparser = argparse.ArgumentParser()", 1)[0], namespace)
    return namespace, state


def test_scheduler_caps_workers_halts_and_requires_reset(tmp_path, monkeypatch, capsys):
    runner, state = load_runner(tmp_path, monkeypatch, "safety")
    workers = [{"worker_id": f"worker-{index}", "state": "reviewing"} for index in range(2)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        reservations = list(pool.map(lambda _: runner["reserve_spawn"](workers, 100), range(2)))
    assert sorted(reason for _, reason in reservations) == ["reserved", "worker_cap"]
    reservation = next(value for value, reason in reservations if reason == "reserved")
    runner["release_reservation"](reservation)
    assert state.stat().st_mode & 0o777 == 0o600
    assert state.parent.stat().st_mode & 0o777 == 0o700

    connection = runner["state_connection"]()
    connection.execute("BEGIN IMMEDIATE")
    runner["sync_worker_outcomes"](connection, [
        {"worker_id": "attempt-blocked", "state": "blocked"},
        {"worker_id": "attempt-abandoned", "state": "abandoned"},
        {"worker_id": "attempt-reverted", "state": "blocked"},
    ], 200)
    connection.commit()
    connection.close()
    assert runner["reserve_spawn"]([], 201) == (None, "halted")
    runner["reset_schedule"]()
    assert json.loads(capsys.readouterr().out) == {"status": "reset"}
    resumed, reason = runner["reserve_spawn"]([], 201)
    assert reason == "reserved"
    runner["release_reservation"](resumed)
    connection = sqlite3.connect(state)
    assert connection.execute("select count(*) from outcome_events where kind='failed'").fetchone() == (3,)
    assert connection.execute("select halt_reason from scheduler_state").fetchone() == (None,)
    connection.execute("update scheduler_meta set value='broken' where key='schema_version'")
    connection.commit()
    connection.close()
    try:
        runner["state_connection"]()
    except RuntimeError as error:
        assert "unsupported schema" in str(error)
    else:
        raise AssertionError("malformed scheduler state was accepted")
    connection = sqlite3.connect(state)
    assert connection.execute("select halt_reason from scheduler_state").fetchone() == ("malformed_state",)
    connection.close()

    malformed, malformed_state = load_runner(tmp_path, monkeypatch, "malformed-event")
    connection = malformed["state_connection"]()
    identifier = malformed["event_id"]("bad-attempt", "failed", "", "")
    connection.execute(
        "insert into outcome_events values (?,?,?,?,?,?,?,?,?,?,?,?)",
        (identifier, "bad-attempt", "failed", "improved", "blocked", 1,
         None, None, None, None, None, json.dumps("unavailable")))
    connection.commit()
    connection.close()
    try:
        malformed["state_connection"]()
    except RuntimeError as error:
        assert "malformed" in str(error)
    else:
        raise AssertionError("semantically malformed outcome was accepted")
    connection = sqlite3.connect(malformed_state)
    assert connection.execute("select halt_reason from scheduler_state").fetchone() == ("malformed_state",)
    connection.close()


def test_failed_reservation_does_not_consume_cadence(tmp_path, monkeypatch):
    runner, state = load_runner(tmp_path, monkeypatch, "reservation")
    reservation, reason = runner["reserve_spawn"]([], 100)
    assert reason == "reserved"
    try:
        runner["complete_reservation"](reservation, "worker-unclaimed", 100)
    except RuntimeError as error:
        assert "unclaimed" in str(error)
    else:
        raise AssertionError("unclaimed reservation was completed")
    connection = sqlite3.connect(state)
    assert connection.execute("select next_eligible_at from scheduler_state").fetchone() == (0,)
    connection.close()
    runner["release_reservation"](reservation)

    crashed, reason = runner["reserve_spawn"]([], 200)
    assert reason == "reserved"
    reclaimed, reason = runner["reserve_spawn"]([], 200 + runner["RESERVATION_LEASE_SECONDS"] + 1)
    assert reason == "reserved" and reclaimed != crashed
    runner["release_reservation"](reclaimed)
    retried, reason = runner["reserve_spawn"]([], 101)
    assert reason == "reserved"
    runner["claim_reservation"](retried, "worker-1", 101)
    runner["complete_reservation"](retried, "worker-1", 101)
    connection = sqlite3.connect(state)
    assert connection.execute("select next_eligible_at from scheduler_state").fetchone() == (0,)
    assert connection.execute("select worker_id from lens_attempts").fetchone() == ("worker-1",)
    connection.close()
    reclaimed, reason = runner["reserve_spawn"](
        [], 101 + runner["RESERVATION_LEASE_SECONDS"] + 1)
    assert reason == "reserved"
    runner["release_reservation"](reclaimed)


def test_lens_governance_migrates_and_applies_adaptive_cadence(tmp_path, monkeypatch):
    runner, state = load_runner(tmp_path, monkeypatch, "lens-governance")
    connection = runner["state_connection"]()
    connection.execute("update scheduler_state set cadence='daily',next_eligible_at=123")
    runner["append_event"](connection, "preserved-attempt", "failed", "blocked", 10)
    connection.execute("drop table lens_passes")
    connection.execute("drop table lens_attempts")
    connection.execute("drop table lens_state")
    connection.execute("update scheduler_meta set value='1' where key='schema_version'")
    connection.commit()
    connection.close()
    connection = runner["state_connection"]()
    assert connection.execute("select value from scheduler_meta where key='schema_version'").fetchone() == ("7",)
    assert connection.execute("select cadence,no_yield_count from lens_state").fetchone() == ("daily", 0)
    assert connection.execute("select cadence,next_eligible_at from scheduler_state").fetchone() == ("daily", 123)
    assert connection.execute(
        "select attempt_id,kind,reason from outcome_events where attempt_id='preserved-attempt'"
    ).fetchone() == ("preserved-attempt", "failed", "blocked")
    connection.close()

    start = 1_704_067_200
    connection = runner["state_connection"]()
    plan = runner["lens_plan"](connection, start)
    connection.commit()
    connection.close()
    assert plan["capture_day"] == "2024-01-01" and plan["due"]
    assert [item["name"] for item in plan["lenses"]] == list(runner["LEGACY_LENSES"])
    assert all(item["version"] == 1 for item in plan["lenses"])

    runner["command"] = lambda _argv, **_kwargs: {
        "workers": [{"worker_id": current_worker, "state": current_state}]}

    def record(now, outcome, number):
        nonlocal current_worker, current_state
        current_worker = f"worker-{number}"
        current_state = "claimed" if outcome == "yield" else "reviewing"
        reservation, reason = runner["reserve_spawn"]([], now)
        assert reason == "reserved"
        runner["claim_reservation"](reservation, current_worker, now)
        runner["complete_reservation"](reservation, current_worker, now)
        day = runner["capture_day_at"](now)
        return runner["lens_result"](current_worker, day, f"{number:064x}", outcome, now)

    current_worker = ""
    current_state = "reviewing"
    now = start
    for number in range(1, 4):
        result = record(now, "no_yield", number)
        now = result["next_eligible_at"]
    assert result["cadence"] == "weekly" and result["no_yield_count"] == 0
    for number in range(4, 8):
        result = record(now, "no_yield", number)
        now = result["next_eligible_at"]
    assert result["cadence"] == "monthly" and result["no_yield_count"] == 0
    result = record(now, "yield", 8)
    assert result["cadence"] == "daily" and result["no_yield_count"] == 0
    runner["command"] = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("idempotent replay queried worker state"))
    assert runner["lens_result"](
        current_worker, result["capture_day"], result["manifest_digest"],
        "yield", now + 86400) == result
    try:
        runner["lens_result"](current_worker, result["capture_day"], "f" * 64, "yield", now + 86400)
    except RuntimeError as error:
        assert "conflicts" in str(error)
    else:
        raise AssertionError("conflicting lens result was accepted")

    connection = runner["state_connection"]()
    connection.execute(
        "update lens_state set cadence='monthly',no_yield_count=2,quarter='2024-Q1',next_eligible_at=?",
        (2_000_000_000,))
    reset = runner["lens_plan"](connection, 1_712_275_200)
    connection.commit()
    connection.close()
    assert reset["quarter"] == "2024-Q2" and reset["cadence"] == "daily" and reset["due"]

    migrated, migrated_state = load_runner(tmp_path, monkeypatch, "parallel-v3-migration")
    connection = migrated["state_connection"]()
    connection.execute("drop table parallel_lens_passes")
    connection.execute("""create table parallel_lens_passes (
        worker_id text primary key, lens_name text not null, capture_day text not null,
        manifest_digest text not null, outcome text not null, recorded_at integer not null,
        cadence text not null, no_yield_count integer not null, quarter text not null,
        next_eligible_at integer not null, page_count integer not null,
        session_count integer not null, review_session_count integer not null,
        excluded_review_session_count integer not null, source_count integer not null
    ) without rowid""")
    connection.execute("update scheduler_meta set value='3' where key='schema_version'")
    connection.execute("alter table parallel_lens_attempts drop column session_id")
    connection.execute("insert into spawn_reservations values ('reservation-old',1,'worker-old')")
    connection.execute("insert into parallel_lens_attempts values "
                       "('reservation-old','correctness_safety','worker-old','2024-01-01','daily',0,'2024-Q1')")
    connection.commit()
    connection.close()
    connection = migrated["state_connection"]()
    assert connection.execute("select value from scheduler_meta where key='schema_version'").fetchone() == ("7",)
    columns = {row[1] for row in connection.execute("pragma table_info(parallel_lens_passes)")}
    assert {"unattributed_session_count", "opportunity_id", "session_id"} <= columns
    assert connection.execute("select count(*) from parallel_lens_attempts").fetchone() == (0,)
    assert connection.execute(
        "select count(*) from spawn_reservations where reservation_id='reservation-old'"
    ).fetchone() == (0,)
    connection.close()


def test_lens_governance_prevents_duplicate_daily_pass(tmp_path, monkeypatch):
    runner, _ = load_runner(tmp_path, monkeypatch, "lens-duplicate")
    now = 1_704_067_200
    reservation, reason = runner["reserve_spawn"]([], now)
    assert reason == "reserved"
    runner["claim_reservation"](reservation, "worker-1", now)
    runner["complete_reservation"](reservation, "worker-1", now)
    assert runner["reserve_parallel_lens"]([], now) == (None, None, "legacy_attempt_active")
    assert runner["reserve_spawn"]([], now) == (None, "cadence_not_due")
    connection = runner["state_connection"]()
    assert runner["lens_plan"](connection, now, "worker-1")["due"]
    recovered = runner["lens_plan"](connection, now + 86400, "worker-1")
    assert recovered["due"] and recovered["capture_day"] == "2024-01-01"
    connection.close()
    assert runner["reserve_spawn"](
        [{"worker_id": "worker-1", "state": "reviewing"}], now + 86400
    ) == (None, "cadence_not_due")
    runner["command"] = lambda _argv, **_kwargs: {"workers": []}
    try:
        runner["lens_result"]("worker-1", "2024-01-01", "a" * 64, "yield", now)
    except RuntimeError as error:
        assert "required state" in str(error)
    else:
        raise AssertionError("missing worker was accepted")
    runner["command"] = lambda _argv, **_kwargs: {
        "workers": [{"worker_id": "worker-1", "state": "blocked"}]}
    try:
        runner["lens_result"]("worker-1", "2024-01-01", "a" * 64, "no_yield", now)
    except RuntimeError as error:
        assert "required state" in str(error)
    else:
        raise AssertionError("blocked worker was accepted")
    runner["command"] = lambda _argv, **_kwargs: {
        "workers": [{"worker_id": "worker-1", "state": "reviewing"}]}
    late = runner["lens_result"](
        "worker-1", "2024-01-01", "a" * 64, "no_yield", now + 86400)
    assert late["capture_day"] == "2024-01-01" and late["no_yield_count"] == 1


def test_parallel_lenses_isolate_review_sessions_and_record_telemetry(tmp_path, monkeypatch):
    runner, state = load_runner(tmp_path, monkeypatch, "parallel-lenses")
    assert runner["LENSES"] == (
        "correctness_safety", "reliability_recovery", "performance_cost",
        "operator_experience", "architecture_rnd_meta", "review_session_governance",
    )
    now = 1_704_067_200
    attempts = {}
    for expected in runner["LENSES"]:
        reservation, lens, reason = runner["reserve_parallel_lens"]([], now)
        assert (lens, reason) == (expected, "reserved")
        worker = f"worker-{len(attempts)}"
        runner["claim_reservation"](reservation, worker, now)
        runner["complete_reservation"](reservation, worker, session_id=f"session-{len(attempts)}")
        runner["complete_reservation"](reservation, worker, session_id=f"session-{len(attempts)}")
        attempts[lens] = (reservation, worker)
    assert runner["reserve_parallel_lens"]([], now) == (None, None, "no_lens_due")

    states = {worker: "reviewing" for _, worker in attempts.values()}
    opportunities = {}
    runner["command"] = lambda argv, **_kwargs: {
        "workers": [{"worker_id": argv[-1], "state": states[argv[-1]],
                     "session_id": f"session-{argv[-1].removeprefix('worker-')}",
                     "opportunity_id": opportunities.get(argv[-1])}],
    }
    ordinary = attempts["correctness_safety"][1]
    review = attempts[runner["REVIEW_SESSION_LENS"]][1]
    base = {"page_count": 7, "session_count": 10, "review_session_count": 0,
            "excluded_review_session_count": 2, "unattributed_session_count": 0,
            "source_count": 3}
    runner["RECEIPTS"].mkdir(mode=0o700)

    def write_receipt(digest, scope, telemetry):
        path = runner["RECEIPTS"] / f"{digest}.{scope}.json"
        path.write_text(json.dumps({"schema_version": 1, "manifest_digest": digest,
                                    "scope": scope, "telemetry": telemetry}))
        path.chmod(0o600)

    write_receipt("a" * 64, "exclude", base)
    try:
        runner["parallel_lens_result"](
            ordinary, "2024-01-01", "a" * 64, "no_yield",
            {**base, "review_session_count": 1}, now)
    except RuntimeError as error:
        assert "capture receipt" in str(error)
    else:
        raise AssertionError("ordinary lens accepted review-session evidence")
    try:
        runner["parallel_lens_result"](
            ordinary, "2024-01-01", "a" * 64, "no_yield",
            {**base, "unattributed_session_count": 1}, now)
    except RuntimeError as error:
        assert "inconsistent" in str(error)
    else:
        raise AssertionError("unattributed lens evidence was accepted")
    ordinary_result = runner["parallel_lens_result"](
        ordinary, "2024-01-01", "a" * 64, "no_yield", base, now)
    assert ordinary_result["next_eligible_at"] == now + 86400

    review_metrics = {"page_count": 7, "session_count": 2, "review_session_count": 2,
                      "excluded_review_session_count": 0, "unattributed_session_count": 0,
                      "source_count": 3}
    write_receipt("b" * 64, "only", review_metrics)
    try:
        runner["parallel_lens_result"](
            review, "2024-01-01", "b" * 64, "no_yield",
            {**review_metrics, "review_session_count": 3}, now)
    except RuntimeError as error:
        assert "inconsistent" in str(error)
    else:
        raise AssertionError("inconsistent lens counters were accepted")
    review_result = runner["parallel_lens_result"](
        review, "2024-01-01", "b" * 64, "no_yield", review_metrics, now)
    assert review_result["lens"] == "review_session_governance"
    yielded = attempts["reliability_recovery"][1]
    states[yielded] = "claimed"
    opportunities[yielded] = "c" * 64
    write_receipt("d" * 64, "exclude", base)
    runner["parallel_lens_result"](yielded, "2024-01-01", "d" * 64, "yield", base, now)
    connection = sqlite3.connect(state)
    assert connection.execute(
        "select review_session_count,excluded_review_session_count,source_count "
        "from parallel_lens_passes where worker_id=?", (review,)).fetchone() == (2, 0, 3)
    assert connection.execute(
        "select session_id,opportunity_id from parallel_lens_passes where worker_id=?", (yielded,)
    ).fetchone() == (f"session-{yielded.removeprefix('worker-')}", "c" * 64)
    connection.close()

    reused = attempts["performance_cost"][1]
    states[reused] = "claimed"
    opportunities[reused] = "e" * 64
    original_command = runner["command"]
    runner["command"] = lambda argv, **kwargs: {
        "workers": [{**original_command(argv, **kwargs)["workers"][0], "session_id": "session-reused"}],
    }
    try:
        runner["complete_reservation"](
            attempts["performance_cost"][0], reused, session_id="session-reused")
    except RuntimeError as error:
        assert "incarnation changed" in str(error)
    else:
        raise AssertionError("completion rebound a pending lens attempt")
    write_receipt("f" * 64, "exclude", base)
    try:
        runner["parallel_lens_result"](reused, "2024-01-01", "f" * 64, "yield", base, now)
    except RuntimeError as error:
        assert "incarnation changed" in str(error)
    else:
        raise AssertionError("reused worker inherited a pending lens attempt")

    for lens, (reservation, _worker) in attempts.items():
        if lens not in {"correctness_safety", "reliability_recovery", runner["REVIEW_SESSION_LENS"]}:
            runner["release_reservation"](reservation)


def test_parallel_lenses_reclaim_absent_expired_worker(tmp_path, monkeypatch):
    runner, state = load_runner(tmp_path, monkeypatch, "parallel-stale-worker")
    now = 1_704_067_200
    reservation, lens, _ = runner["reserve_parallel_lens"]([], now)
    runner["claim_reservation"](reservation, "worker-stale", now)
    runner["complete_reservation"](reservation, "worker-stale", session_id="session-stale")

    replacement, replacement_lens, reason = runner["reserve_parallel_lens"](
        [], now + runner["RESERVATION_LEASE_SECONDS"] + 1
    )

    assert reason == "reserved" and replacement_lens == lens and replacement != reservation
    connection = sqlite3.connect(state)
    assert connection.execute(
        "select count(*) from spawn_reservations where reservation_id=?", (reservation,)
    ).fetchone() == (0,)
    connection.close()


def test_scheduler_health_records_reserve_and_release_outcomes(tmp_path, monkeypatch):
    runner, state = load_runner(tmp_path, monkeypatch, "scheduler-health")
    now = 1_704_067_200
    reservation, lens, reason = runner["reserve_parallel_lens"]([], now)
    assert reason == "reserved"
    runner["release_reservation"](reservation, "prelaunch_failed")
    health = runner["scheduler_health"]()
    assert health == {
        "schema_version": 1, "state_schema_version": 7, "lens_count": 6,
        "reserve_count": 1, "last_reserve_at": now,
        "last_reserve_status": "reserved", "last_lens": lens,
        "release_count": 1, "last_release_at": health["last_release_at"],
        "last_release_reason": "prelaunch_failed", "active_attempt_count": 0,
        "pass_count": 0,
    }
    connection = sqlite3.connect(state)
    connection.execute("update scheduler_activity set last_reserve_status='bad status'")
    connection.commit()
    connection.close()
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "activity is malformed" in str(error)
    else:
        raise AssertionError("malformed scheduler health was accepted")
    connection = sqlite3.connect(state)
    connection.execute("update scheduler_activity set last_reserve_status='reserved'")
    connection.execute("update scheduler_meta set value='5' where key='schema_version'")
    connection.commit()
    connection.close()
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "unsupported schema" in str(error)
    else:
        raise AssertionError("old scheduler health schema was accepted")
    connection = sqlite3.connect(state)
    connection.execute("update scheduler_meta set value='7' where key='schema_version'")
    connection.execute("pragma foreign_keys=off")
    connection.execute("insert into parallel_lens_attempts values "
                       "('missing','correctness_safety',NULL,'2024-01-01','daily',0,'2024-Q1',NULL)")
    connection.commit()
    connection.close()
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "foreign-key check failed" in str(error)
    else:
        raise AssertionError("invalid scheduler health foreign key was accepted")
    connection = sqlite3.connect(state)
    connection.execute("delete from parallel_lens_attempts where reservation_id='missing'")
    connection.execute("insert into spawn_reservations values ('invalid-domain',1,NULL)")
    connection.execute("insert into parallel_lens_attempts values "
                       "('invalid-domain','unsupported_lens',NULL,'2024-01-01','daily',0,'2024-Q1',NULL)")
    connection.commit()
    connection.close()
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "attempt is malformed" in str(error)
    else:
        raise AssertionError("domain-invalid scheduler health state was accepted")
    connection = sqlite3.connect(state)
    connection.execute("delete from spawn_reservations where reservation_id='invalid-domain'")
    connection.commit()
    connection.close()
    state.chmod(0o644)
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "path is unsafe" in str(error)
    else:
        raise AssertionError("unsafe scheduler health mode was accepted")
    state.chmod(0o600)
    state.parent.chmod(0o755)
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "path is unsafe" in str(error)
    else:
        raise AssertionError("unsafe scheduler health parent mode was accepted")
    state.parent.chmod(0o700)
    real_state = state.with_suffix(".real")
    state.rename(real_state)
    state.symlink_to(real_state)
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "path is unsafe" in str(error)
    else:
        raise AssertionError("symlinked scheduler health was accepted")
    state.unlink()
    try:
        runner["scheduler_health"]()
    except RuntimeError as error:
        assert "path is unsafe" in str(error)
    else:
        raise AssertionError("missing scheduler health state was accepted")

    corrupt_runner, corrupt_state = load_runner(tmp_path, monkeypatch, "scheduler-health-corrupt")
    corrupt_state.write_bytes(b"not a sqlite database")
    corrupt_state.chmod(0o600)
    try:
        corrupt_runner["scheduler_health"]()
    except RuntimeError as error:
        assert "integrity check failed" in str(error)
    else:
        raise AssertionError("corrupt scheduler health state was accepted")


def test_parallel_completion_binds_exactly_one_concurrent_session(tmp_path, monkeypatch):
    runner, state = load_runner(tmp_path, monkeypatch, "parallel-completion-race")
    now = 1_704_067_200
    reservation, _lens, reason = runner["reserve_parallel_lens"]([], now)
    assert reason == "reserved"
    runner["claim_reservation"](reservation, "worker-race", now)

    def complete(session_id):
        try:
            runner["complete_reservation"](reservation, "worker-race", session_id=session_id)
            return session_id
        except RuntimeError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(complete, ("session-a", "session-b")))
    winners = [result for result in results if result]
    assert len(winners) == 1
    connection = sqlite3.connect(state)
    assert connection.execute(
        "select session_id from parallel_lens_attempts where reservation_id=?", (reservation,)
    ).fetchone() == (winners[0],)
    connection.close()

def test_watchdog_leaves_waiting_priority_claims_queued(tmp_path, monkeypatch, capsys):
    runner, _ = load_runner(tmp_path, monkeypatch, "waiting-priority")
    worker = {"worker_id": "worker-1", "session_id": "session-1", "state": "claimed",
              "priority": "P0", "recovery_attempts": 0}

    def execute(argv, **_kwargs):
        if argv[0] == runner["DBSCTRCTL"]:
            return {"workers": [worker]}
        if argv[:3] == [runner["HERDR"], "agent", "list"]:
            raise AssertionError("Herdr queried for waiting-only workers")
        raise AssertionError(argv)

    runner["command"] = execute
    runner["launch"] = lambda *_args: (_ for _ in ()).throw(AssertionError("worker recovered"))
    for priority in ("P2", "P3"):
        worker["priority"] = priority
        assert runner["watchdog"]() == 0
        assert json.loads(capsys.readouterr().out) == {
            "events": [{"worker_id": "worker-1", "status": "waiting_priority"}]}


def test_canonical_backlog_discovery_is_root_bounded(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    repo = root / "project"
    context = repo / "docs/specs/example"
    context.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (context / "BACKLOG.md").write_text(
        "# Backlog\n\n## Active\n\n"
        "| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
        "| X-1 | Refine \\| work | high | pending | - | code | docs | no | needed | S | test |\n\n"
        "## Completed\n\n| id | outcome | completed | commit |\n|---|---|---|---|\n"
    )
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "docs/specs/example/BACKLOG.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "backlog"], cwd=repo, check=True, capture_output=True)
    source = render("dot_local/bin/executable_dbsctr-rnd.tmpl",
                    values(review_workdir=str(repo), roots=[str(root)]))
    namespace = {"__name__": "dbsctr_rnd_backlogs"}
    exec(source.split("\nparser = argparse.ArgumentParser()", 1)[0], namespace)
    namespace["PMCTL"] = str(ROOT / "dot_local/bin/executable_pmctl")
    subprocess.run(["python3", namespace["PMCTL"], "migrate-backlogs", "--root", str(repo),
                    "--apply", "--json"], check=True, capture_output=True, text=True)
    discovered = namespace["canonical_backlogs"]()
    assert len(discovered["backlogs"]) == 1
    assert discovered["backlogs"][0]["id"] == "X-1"
    assert discovered["backlogs"][0]["title"] == "Refine | work"
    assert len(discovered["backlogs"][0]["idempotency_key"]) == 64
    repository = namespace["backlog_repositories"]()["repositories"][0]
    assert repository["profile"].startswith("project-")
    assert len(repository["profile"]) <= 64

    ticket = next((repo / "docs/tickets/context=example").glob("*.md"))
    valid = ticket.read_text()
    ticket.write_text(valid.replace("state: \"intake\"", "state: \"unknown\""))
    try:
        namespace["canonical_backlogs"]()
    except RuntimeError as error:
        assert "failed" in str(error)
    else:
        raise AssertionError("malformed ticket was accepted")
    ticket.write_text(valid)

    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "docs/tickets/context=escape").symlink_to(outside, target_is_directory=True)
    try:
        namespace["canonical_backlogs"]()
    except RuntimeError as error:
        assert "failed" in str(error)
    else:
        raise AssertionError("backlog symlink escape was accepted")


def test_direct_launch_registers_only_its_exact_native_session(tmp_path, monkeypatch, capsys):
    runner, _ = load_runner(tmp_path, monkeypatch, "direct-launch")
    repository = tmp_path / "project"
    repository.mkdir()
    now = int(runner["time"].time())
    reservation, reason = runner["reserve_spawn"]([], now)
    assert reason == "reserved"
    calls = []
    sessions = iter((set(), {"ses_exact"}))

    class Process:
        def __init__(self, argv, **kwargs):
            calls.append(argv)
            assert not any(key.startswith("OPENCODE") for key in kwargs["env"])
            assert kwargs["env"]["PWD"] == str(repository)
            kwargs["stdout"].write('{"sessionID":"ses_exact"}\n')
            kwargs["stdout"].flush()

        def poll(self):
            return None

        def terminate(self):
            raise AssertionError("registered process was terminated")

    runner["canonical_backlogs"] = lambda: {"backlogs": [{
        "repository_id": "repo-1", "repository": str(repository),
    }]}
    runner["session_ids"] = lambda _repository: next(sessions)
    monkeypatch.setattr(runner["subprocess"], "Popen", Process)
    runner["command"] = lambda argv, **_kwargs: {
        "worker_id": argv[argv.index("--worker-id") + 1],
        "session_id": argv[argv.index("--session-id") + 1],
    }
    runner["launch_action"](reservation, "worker-1", "repo-1")
    output = json.loads(capsys.readouterr().out)
    assert output == {"session_id": "ses_exact", "status": "started", "worker_id": "worker-1"}
    assert calls == [["opencode", "run", "--agent", "build", "--command", "dbsctr-improve",
                      "--format", "json"]]


def test_direct_launch_rejects_expired_reservation_before_process_start(tmp_path, monkeypatch):
    runner, _ = load_runner(tmp_path, monkeypatch, "expired-direct-launch")
    repository = tmp_path / "project"
    repository.mkdir()
    reservation, reason = runner["reserve_spawn"]([], 100)
    assert reason == "reserved"
    runner["canonical_backlogs"] = lambda: {"backlogs": [{
        "repository_id": "repo-1", "repository": str(repository),
    }]}
    monkeypatch.setattr(runner["time"], "time", lambda: 100 + runner["RESERVATION_LEASE_SECONDS"] + 1)
    monkeypatch.setattr(
        runner["subprocess"], "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("process started")),
    )

    try:
        runner["launch_action"](reservation, "worker-1", "repo-1")
    except RuntimeError as error:
        assert "expired" in str(error)
    else:
        raise AssertionError("expired reservation was accepted")


def test_direct_launch_reaps_process_when_reservation_cleanup_fails(tmp_path, monkeypatch):
    runner, _ = load_runner(tmp_path, monkeypatch, "cleanup-direct-launch")
    repository = tmp_path / "project"
    repository.mkdir()
    reservation, reason = runner["reserve_spawn"]([], int(runner["time"].time()))
    assert reason == "reserved"
    events = []

    class Process:
        pid = 123

        def __init__(self, *_args, **_kwargs):
            pass

        def poll(self):
            return None

        def wait(self, timeout):
            events.append(("wait", timeout))
            return 0

    runner["canonical_backlogs"] = lambda: {"backlogs": [{
        "repository_id": "repo-1", "repository": str(repository),
    }]}
    calls = 0

    def sessions(_repository):
        nonlocal calls
        calls += 1
        if calls == 1:
            return set()
        raise RuntimeError("session lookup failed")

    def release(_reservation, *_args):
        events.append(("release", None))
        raise RuntimeError("reservation cleanup failed")

    runner["session_ids"] = sessions
    runner["release_reservation"] = release
    monkeypatch.setattr(runner["subprocess"], "Popen", Process)
    def killpg(pid, sig):
        events.append(("kill", (pid, sig)))
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr(runner["os"], "killpg", killpg)

    try:
        runner["launch_action"](reservation, "worker-1", "repo-1")
    except ExceptionGroup as error:
        assert [str(item) for item in error.exceptions] == [
            "session lookup failed", "reservation cleanup failed",
        ]
    else:
        raise AssertionError("combined launch and cleanup failure was not reported")
    assert events == [
        ("kill", (123, runner["signal"].SIGTERM)), ("wait", 5),
        ("kill", (123, 0)), ("wait", 5), ("release", None),
    ]


def test_direct_launch_kills_group_after_leader_exits(tmp_path, monkeypatch):
    runner, _ = load_runner(tmp_path, monkeypatch, "exited-leader-direct-launch")
    repository = tmp_path / "project"
    repository.mkdir()
    reservation, reason = runner["reserve_spawn"]([], int(runner["time"].time()))
    assert reason == "reserved"
    signals = []

    class Process:
        pid = 456

        def __init__(self, *_args, **_kwargs):
            pass

        def poll(self):
            return 0

        def wait(self, timeout):
            assert timeout == 5
            return 0

    runner["canonical_backlogs"] = lambda: {"backlogs": [{
        "repository_id": "repo-1", "repository": str(repository),
    }]}
    calls = 0

    def sessions(_repository):
        nonlocal calls
        calls += 1
        if calls == 1:
            return set()
        raise RuntimeError("session lookup failed")

    runner["session_ids"] = sessions
    monkeypatch.setattr(runner["subprocess"], "Popen", Process)
    monkeypatch.setattr(runner["os"], "killpg", lambda pid, sig: signals.append((pid, sig)))

    try:
        runner["launch_action"](reservation, "worker-1", "repo-1")
    except RuntimeError as error:
        assert str(error) == "session lookup failed"
    else:
        raise AssertionError("failed launch was accepted")
    assert signals == [
        (456, runner["signal"].SIGTERM), (456, 0), (456, runner["signal"].SIGKILL),
    ]


def test_installed_opencode_supports_pure_session_json():
    completed = subprocess.run(
        ["opencode", "session", "list", "--pure", "--format", "json", "-n", "1"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    assert completed.stdout == "" or isinstance(json.loads(completed.stdout), list)


def test_direct_launch_e2e_uses_pure_session_cli_and_cleans_failed_preflight(tmp_path):
    repository = tmp_path / "project"
    backlog = repository / "docs/specs/example/BACKLOG.md"
    backlog.parent.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", repository], check=True)
    backlog.write_text(
        "# Backlog\n\n## Active\n\n"
        "| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
        "| X-1 | Exercise launch | high | pending | - | runner | sessions | no | regression | S | e2e |\n\n"
        "## Completed\n\n| id | outcome | completed | commit |\n|---|---|---|---|\n"
    )
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    subprocess.run(["git", "add", "docs/specs/example/BACKLOG.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-m", "backlog"], cwd=repository, check=True, capture_output=True)
    subprocess.run(["python3", str(ROOT / "dot_local/bin/executable_pmctl"),
                    "migrate-backlogs", "--root", str(repository), "--apply", "--json"],
                   check=True, capture_output=True, text=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    command_log = tmp_path / "commands.log"
    session_marker = tmp_path / "session-created"
    pid_file = tmp_path / "worker.pid"
    opencode = bin_dir / "opencode"
    opencode.write_text(
        "#!/bin/sh\n"
        "printf 'opencode %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "if [ \"$1 $2\" = 'session list' ]; then\n"
        "  case \" $* \" in *' --pure '*) ;; *) exit 0;; esac\n"
        "  [ \"${SESSION_LIST_MODE:-valid}\" = invalid ] && { printf 'not-json\\n'; exit 0; }\n"
        "  if [ -f \"$SESSION_MARKER\" ]; then\n"
        f"    printf '%s\\n' '[{{\"id\":\"ses_e2e\",\"directory\":\"{repository}\"}}]'\n"
        "  else printf '%s\\n' '[]'; fi\n"
        "elif [ \"$1\" = run ]; then\n"
        "  touch \"$SESSION_MARKER\"\n"
        "  printf '%s\\n' \"$$\" > \"$PID_FILE\"\n"
        "  printf '%s\\n' '{\"sessionID\":\"ses_e2e\"}'\n"
        "  sleep 30\n"
        "fi\n"
    )
    dbsctrctl = bin_dir / "dbsctrctl"
    dbsctrctl.write_text(
        "#!/bin/sh\n"
        "printf 'dbsctrctl %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        "if [ \"$1\" = improvement-status ]; then printf '%s\\n' '{\"workers\":[]}'; exit 0; fi\n"
        "worker= session=\n"
        "while [ $# -gt 0 ]; do\n"
        "  case \"$1\" in --worker-id) worker=$2; shift 2;; --session-id) session=$2; shift 2;; *) shift;; esac\n"
        "done\n"
        "[ \"${REGISTER_MODE:-valid}\" = invalid ] && worker=wrong-worker\n"
        "printf '{\"worker_id\":\"%s\",\"session_id\":\"%s\",\"state\":\"reviewing\"}\\n' \"$worker\" \"$session\"\n"
    )
    opencode.chmod(0o755)
    dbsctrctl.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render(
        "dot_local/bin/executable_dbsctr-rnd.tmpl",
        values(review_workdir=str(repository), roots=[str(repository)]),
    ))
    runner.chmod(0o755)
    state = tmp_path / "scheduler.sqlite3"
    env = {
        **os.environ,
        "COMMAND_LOG": str(command_log),
        "DBSCTRCTL": str(dbsctrctl),
        "DBSCTR_RND_STATE": str(state),
        "OPENCODE_BIN": str(opencode),
        "PMCTL": str(ROOT / "dot_local/bin/executable_pmctl"),
        "PID_FILE": str(pid_file),
        "SESSION_MARKER": str(session_marker),
    }

    reserved = json.loads(subprocess.run(
        [str(runner), "reserve"], env=env, text=True, capture_output=True, check=True,
    ).stdout)
    repository_id = json.loads(subprocess.run(
        [str(runner), "repositories"], env=env, text=True, capture_output=True, check=True,
    ).stdout)["repositories"][0]["repository_id"]
    launched = subprocess.run([
        str(runner), "--reservation", reserved["reservation"],
        "--worker-id", reserved["worker_id"], "--repository-id", repository_id, "launch",
    ], env=env, text=True, capture_output=True, check=True)
    assert json.loads(launched.stdout) == {
        "session_id": "ses_e2e", "status": "started", "worker_id": reserved["worker_id"],
    }
    commands = command_log.read_text()
    assert "opencode session list --pure --format json -n 100" in commands
    assert f"improvement-register --worker-id {reserved['worker_id']} --session-id ses_e2e" in commands
    successful_pid = int(pid_file.read_text())
    os.kill(successful_pid, 0)
    os.killpg(successful_pid, 15)

    failed_state = tmp_path / "failed.sqlite3"
    failed_env = {**env, "DBSCTR_RND_STATE": str(failed_state), "SESSION_LIST_MODE": "invalid"}
    failed_reservation = json.loads(subprocess.run(
        [str(runner), "reserve"], env=failed_env, text=True, capture_output=True, check=True,
    ).stdout)
    failed = subprocess.run([
        str(runner), "--reservation", failed_reservation["reservation"],
        "--worker-id", failed_reservation["worker_id"], "--repository-id", repository_id, "launch",
    ], env=failed_env, text=True, capture_output=True)
    assert failed.returncode != 0
    assert "returned invalid JSON" in failed.stderr
    connection = sqlite3.connect(failed_state)
    assert connection.execute("select count(*) from spawn_reservations").fetchone() == (0,)
    assert connection.execute("select count(*) from lens_attempts").fetchone() == (0,)
    connection.close()

    setup_failure_dir = tmp_path / "setup-failure"
    setup_failure_dir.mkdir()
    setup_state = setup_failure_dir / "scheduler.sqlite3"
    setup_env = {**env, "DBSCTR_RND_STATE": str(setup_state)}
    setup_reservation = json.loads(subprocess.run(
        [str(runner), "reserve"], env=setup_env, text=True, capture_output=True, check=True,
    ).stdout)
    (setup_failure_dir / "launches").write_text("not a directory")
    setup_failed = subprocess.run([
        str(runner), "--reservation", setup_reservation["reservation"],
        "--worker-id", setup_reservation["worker_id"], "--repository-id", repository_id, "launch",
    ], env=setup_env, text=True, capture_output=True)
    assert setup_failed.returncode != 0
    connection = sqlite3.connect(setup_state)
    assert connection.execute("select count(*) from spawn_reservations").fetchone() == (0,)
    assert connection.execute("select count(*) from lens_attempts").fetchone() == (0,)
    connection.close()

    session_marker.unlink()
    failed_state = tmp_path / "failed-after-start.sqlite3"
    failed_env = {**env, "DBSCTR_RND_STATE": str(failed_state), "REGISTER_MODE": "invalid"}
    failed_reservation = json.loads(subprocess.run(
        [str(runner), "reserve"], env=failed_env, text=True, capture_output=True, check=True,
    ).stdout)
    failed = subprocess.run([
        str(runner), "--reservation", failed_reservation["reservation"],
        "--worker-id", failed_reservation["worker_id"], "--repository-id", repository_id, "launch",
    ], env=failed_env, text=True, capture_output=True)
    assert failed.returncode != 0
    failed_pid = int(pid_file.read_text())
    try:
        os.kill(failed_pid, 0)
    except ProcessLookupError:
        pass
    else:
        raise AssertionError("failed direct-launch process was not reaped")
    connection = sqlite3.connect(failed_state)
    assert connection.execute("select count(*) from spawn_reservations").fetchone() == (0,)
    assert connection.execute("select count(*) from lens_attempts").fetchone() == (0,)
    connection.close()


def test_effects_finalize_once_and_drive_monthly_cadence(tmp_path, monkeypatch, capsys):
    runner, state = load_runner(tmp_path, monkeypatch, "effects")
    activation = 1_000_000

    def report(identifier, merge_identity, classification, version="errors-v1",
               metric="tool_error_count", observation=1):
        return {
            "benchmark_id": identifier,
            "definition": {"version": version, "metric": metric, "direction": "lower"},
            "inputs": {"merge_identity": merge_identity, "activation_status": "verified",
                       "activation_identity": f"activation-{identifier}", "activated_at": activation},
            "result": {"classification": classification, "observation_value": observation},
            "evaluated_at": activation + 30 * 86400 * 1000,
        }

    connection = runner["state_connection"]()
    connection.execute("BEGIN IMMEDIATE")
    for attempt, identity in (("attempt-1", "a" * 40), ("attempt-2", "b" * 40)):
        runner["append_event"](connection, attempt, "merged", "merged", 100,
                               merge_identity=identity)
        request = {"attempt_id": attempt, "benchmark_id": f"benchmark-{attempt[-1]}"}
        benchmark = report(request["benchmark_id"], identity, "improved")
        first = runner["finalize_effect"](connection, request, benchmark, 100)
        assert runner["finalize_effect"](connection, request, benchmark, 101) == first
        conflicting = report(request["benchmark_id"], identity, "neutral")
        try:
            runner["finalize_effect"](connection, request, conflicting, 102)
        except RuntimeError as error:
            assert "conflicts" in str(error)
        else:
            raise AssertionError("finalized effect was rewritten")
    cadence, changed, counts, cost = runner["evaluate_month"](connection, 100)
    assert (cadence, changed, counts["improved"], counts["pending"], cost) == (
        "twice_weekly", True, 2, 0, "unavailable")
    connection.commit()

    later = 100 + runner["MONTH_SECONDS"]
    runner["append_event"](connection, "attempt-pending", "merged", "merged", later,
                           merge_identity="c" * 40)
    incomplete = report("benchmark-incomplete", "c" * 40, "insufficient")
    incomplete["evaluated_at"] = activation + 1000
    try:
        runner["finalize_effect"](
            connection, {"attempt_id": "attempt-pending", "benchmark_id": "benchmark-incomplete"},
            incomplete, later)
    except RuntimeError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("incomplete benchmark was finalized")
    runner["append_event"](connection, "attempt-regressed", "merged", "merged", later,
                           merge_identity="d" * 40)
    runner["finalize_effect"](
        connection, {"attempt_id": "attempt-regressed", "benchmark_id": "benchmark-regressed"},
        report("benchmark-regressed", "d" * 40, "regressed"), later)
    runner["append_event"](connection, "attempt-insufficient", "merged", "merged", later,
                           merge_identity="e" * 40)
    runner["finalize_effect"](
        connection, {"attempt_id": "attempt-insufficient", "benchmark_id": "benchmark-insufficient"},
        report("benchmark-insufficient", "e" * 40, "insufficient"), later)
    cadence, changed, counts, _ = runner["evaluate_month"](connection, later)
    assert cadence == "weekly" and changed
    assert counts["regressed"] == 1 and counts["insufficient"] == 1 and counts["pending"] == 1
    connection.commit()

    latest = later + runner["MONTH_SECONDS"]
    runner["append_event"](connection, "attempt-cost", "merged", "merged", latest,
                           merge_identity="f" * 40)
    runner["finalize_effect"](
        connection, {"attempt_id": "attempt-cost", "benchmark_id": "benchmark-cost"},
        report("benchmark-cost", "f" * 40, "improved", "cost-v1", "cost_total", 5), latest)
    cadence, changed, counts, cost = runner["evaluate_month"](connection, latest)
    connection.commit()
    connection.close()
    assert cadence == "weekly" and not changed and counts["improved"] == 1 and cost == 5

    connection = sqlite3.connect(state)
    assert connection.execute(
        "select count(*) from outcome_events where attempt_id='attempt-1' and kind='effect_finalized'"
    ).fetchone() == (1,)
    connection.close()
    runner["command"] = lambda argv: {"workers": []}
    runner["analytics"](latest + 1, True)
    summary = json.loads(capsys.readouterr().out)
    assert summary["cadence"] == "weekly" and summary["cost_total"] == "unavailable"


def test_analytics_cli_has_bounded_human_and_json_output(tmp_path):
    helper = tmp_path / "dbsctrctl"
    helper.write_text(
        "#!/bin/sh\nprintf '%s\\n' "
        "'{\"workers\":[{\"worker_id\":\"attempt-reverted\",\"state\":\"merged\"}]}'\n"
    )
    helper.chmod(0o755)
    runner = tmp_path / "dbsctr-rnd"
    runner.write_text(render("dot_local/bin/executable_dbsctr-rnd.tmpl"))
    state = tmp_path / "scheduler.sqlite3"
    env = {**os.environ, "DBSCTRCTL": str(helper), "DBSCTR_RND_STATE": str(state),
           "DBSCTR_RND_LOCK": str(tmp_path / "scheduler.lock")}
    structured = subprocess.run(
        ["python3", str(runner), "analytics", "--json", "--failure-json",
         json.dumps({"attempt_id": "attempt-reverted", "reason": "reverted"})],
        env=env, text=True, capture_output=True, check=True)
    structured_result = json.loads(structured.stdout)
    assert structured_result["cadence"] == "weekly" and structured_result["counts"]["failed"] == 1
    human = subprocess.run(
        ["python3", str(runner), "analytics"],
        env=env, text=True, capture_output=True, check=True)
    assert human.stdout.startswith("cadence=weekly") and len(human.stdout.encode()) < 1024
    reset = subprocess.run(
        ["python3", str(runner), "reset-schedule"], env=env,
        text=True, capture_output=True, check=True)
    assert json.loads(reset.stdout) == {"status": "reset"}


def test_example_documents_only_neutral_rnd_settings():
    example = (ROOT / "config.example.toml").read_text()
    for term in ("[data.dotfiles_ai.rnd]", "enabled = false", "review_hour", "review_minute",
                 "watchdog_interval_seconds", "workspace_label", "github_account", "github_repository"):
        assert term in example
    for term in ("[data.dotfiles_ai.hermes]", 'provider = "openai-codex"',
                 'backend = "native"', "backlog_roots"):
        assert term in example
    assert 'github_account = "your-account"' in example
    retired = (ROOT / ".chezmoiremove").read_text()
    assert ".hermes/skills/dbsctr-supervisor/SKILL.md" in retired
    assert ".hermes/scripts/dbsctr-watchdog.py" in retired
    assert (ROOT / "private_dot_hermes/private_managed/private_skills/private_dbsctr-supervisor/SKILL.md.tmpl").exists()
