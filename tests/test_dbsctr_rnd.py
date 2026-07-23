import concurrent.futures
import fcntl
import json
import os
import plistlib
import sqlite3
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
        "if [ \"$1\" = improvement-status ]; then printf '%s\\n' '{\"workers\":[]}'; "
        "else printf '{\"worker_id\":\"%s\",\"state\":\"reviewing\"}\\n' \"$3\"; fi\n"
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
    assert json.loads(completed.stdout)["worker_id"].startswith("dbsctr-")
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
    empty.write_text("#!/bin/sh\nprintf '[]\\n'\n")
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
    assert "hermes" not in example.lower()
    assert "Saltiola7" not in example
    retired = (ROOT / ".chezmoiremove").read_text()
    assert ".hermes/skills/dbsctr-supervisor/SKILL.md" in retired
    assert ".hermes/scripts/dbsctr-watchdog.py" in retired
