import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def values(
    enabled: bool = True,
    hermes_executable: str = "~/.local/bin/hermes",
    herdr_executable: str = "/opt/homebrew/bin/herdr",
    review_workdir: str = "/tmp/dotfiles-ai",
) -> dict:
    return {
        "dotfiles_ai": {
            "opencode": {
                "bedrock_region": "us-west-2",
                "bedrock_profile": "",
                "default_model": "openai/gpt-5.6-sol",
                "small_model": "openai/gpt-5.6-terra",
                "lmstudio_base_url": "http://127.0.0.1:1234/v1",
            },
            "herdr": {
                "theme": "catppuccin",
                "launchagent": True,
                "executable": herdr_executable,
            },
            "hermes": {
                "enabled": enabled,
                "executable": hermes_executable,
                "provider": "openai-codex",
                "model": "gpt-5.5",
                "review_workdir": review_workdir,
                "review_schedule": "0 9 * * *",
                "watchdog_schedule": "every 5m",
                "review_delivery": "local",
                "review_session_id": "ses_testreview",
                "workspace_label": "DBSCTR R&D",
                "github_account": "Saltiola7",
                "github_repository": "Saltiola7/dotfiles-ai",
                "update_weekday": 0,
                "update_hour": 4,
                "repositories": [
                    {"name": "dotfiles-ai", "path": "/tmp/dotfiles-ai"},
                    {"name": "seo-data-science", "path": "/tmp/seo-data-science"},
                ],
            },
            "onepassword": {
                "enabled": False,
                "account": "",
                "user_uuid": "",
                "keychain_service": "op-service-account-token",
            },
        }
    }


def chezmoi(*args: str, enabled: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(values(enabled)),
            *args,
        ],
        text=True,
        capture_output=True,
        check=True,
    )


def render_source(path: str, data: dict | None = None) -> str:
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(data or values()),
            "execute-template",
        ],
        input=(ROOT / path).read_text(),
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def test_hermes_targets_are_opt_in() -> None:
    enabled = set(chezmoi("managed").stdout.splitlines())
    disabled = set(chezmoi("managed", enabled=False).stdout.splitlines())
    targets = {
        ".hermes/skills/dbsctr-supervisor/SKILL.md",
        ".hermes/scripts/dbsctr-watchdog.py",
        ".local/bin/hermes-update",
        "Library/LaunchAgents/dev.dotfiles-ai.hermes-update.plist",
    }
    assert targets <= enabled
    assert not targets & disabled


def test_installer_is_noninteractive_and_not_curl_to_shell() -> None:
    installer = render_source("run_once_before_install-hermes.sh.tmpl")
    assert "https://hermes-agent.nousresearch.com/install.sh" in installer
    assert "--non-interactive" in installer
    assert "--skip-setup" in installer
    assert "--skip-browser" in installer
    assert "--no-skills" not in installer
    assert "curl -fsSL" in installer
    assert "| bash" not in installer
    assert 'mktemp "${TMPDIR:-/tmp}/hermes-install.XXXXXX"' in installer
    assert '"$HERMES" --version >/dev/null 2>&1 && exit 0' in installer


def test_supervisor_policy_is_allowlisted_and_pauses_for_discovery() -> None:
    skill = chezmoi(
        "cat", str(Path.home() / ".hermes/skills/dbsctr-supervisor/SKILL.md")
    ).stdout
    assert "Writable source: /tmp/dotfiles-ai" in skill
    assert "Herdr workspace label: DBSCTR R&D" in skill
    assert "GitHub account: Saltiola7" in skill
    assert "Global OpenCode history is review evidence, not a repository allowlist" in skill
    assert "Never use a heredoc, inline script, or shell" in skill
    assert "never call `skill_manage`" in skill
    assert "Cycle Record" in skill
    assert "pause" in skill.lower()
    assert "Discovery" in skill
    assert "merge" in skill.lower()
    assert "/compact" in skill
    assert "Never use `-s` for a scheduled worker" in skill
    assert "--prompt\n   /dbsctr-improve" in skill
    assert "dbsctrctl improvement-register" in skill
    assert "opencode -s <session> --agent build" in skill
    assert "three failures" in skill
    assert "explicit retry or abandonment" in skill
    assert "Do not guess from labels" in skill
    assert "Never invoke" in skill
    assert "dbsctrctl review-scan" in skill
    assert "managed OpenCode" in skill
    assert "`Build-GPT`" not in skill
    assert "dbsctr_review_complete" in skill
    assert "dbsctr_review_history_save" in skill
    assert "Never select `Allow always`" in skill
    assert "leave the tab open" in skill
    assert "Never merge or mark a pull request ready" in skill

    command = (ROOT / "private_dot_config/opencode/commands/dbsctr-improve.md").read_text()
    assert "one unreviewed global page" in command
    assert "dbsctr_improvement_claim" in command
    assert "at least 95% confident" in command
    assert "explicitly instruct you to proceed" in command
    assert "`draft_pr` DBSCTR cycle" in command


def test_configurator_reuses_saved_cron_id_and_fails_closed() -> None:
    script = render_source("run_onchange_after_configure-hermes.sh.tmpl")
    assert "herdr integration install opencode" in script
    assert "herdr integration install hermes" in script
    assert "hermes gateway install" in script
    assert 'hermes config set model.provider "openai-codex"' in script
    assert 'hermes config set model.default "gpt-5.5"' in script
    assert "hermes cron edit" in script
    assert "hermes cron create" in script
    assert "Created job:" in script
    assert "printf 'creating" in script
    assert "printf 'unknown" in script
    assert "refusing to create a duplicate" in script
    assert "hermes-review-cron-id" in script
    assert "hermes-watchdog-cron-id" in script
    assert '"every 5m"' in script
    assert '"dbsctr-watchdog.py"' in script
    assert "--skill dbsctr-supervisor" in script
    assert 'REVIEW_WORKDIR="/tmp/dotfiles-ai"' in script
    assert '--workdir "$REVIEW_WORKDIR"' in script

    disabled = subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(values(False)),
            "execute-template",
        ],
        input=(ROOT / "run_onchange_after_configure-hermes.sh.tmpl").read_text(),
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    assert 'cron remove "$job_id"' in disabled


def test_configurator_creates_then_edits_exact_cron_id(tmp_path: Path) -> None:
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    hermes = home / ".local/bin/hermes"
    herdr = bin_dir / "herdr"
    hermes.parent.mkdir(parents=True)
    scripts = home / ".hermes/scripts"
    scripts.mkdir(parents=True)
    (scripts / "dbsctr-watchdog.py").write_text("# test\n")
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    hermes.write_text(
        "#!/bin/bash\n"
        'printf "hermes %s\\n" "$*" >> "$COMMAND_LOG"\n'
        'if [[ "$1 $2" == "cron create" && "$*" == *watchdog* ]]; then printf "Created job: fedcba654321\\n";\n'
        'elif [[ "$1 $2" == "cron create" ]]; then printf "Created job: abcdef123456\\n"; fi\n'
        'if [[ "$1 $2" == "cron edit" && -n "${FAIL_EDIT:-}" ]]; then exit 1; fi\n'
    )
    herdr.write_text('#!/bin/bash\nprintf "herdr %s\\n" "$*" >> "$COMMAND_LOG"\n')
    hermes.chmod(0o755)
    herdr.chmod(0o755)
    rendered = render_source(
        "run_onchange_after_configure-hermes.sh.tmpl",
        values(
            hermes_executable=str(hermes), herdr_executable=str(herdr),
            review_workdir=str(tmp_path),
        ),
    )
    env = {"HOME": str(home), "COMMAND_LOG": str(log), "PATH": "/usr/bin:/bin"}

    first = subprocess.run(["bash"], input=rendered, env=env, text=True, capture_output=True)
    assert first.returncode == 0, first.stderr
    id_file = home / ".local/state/dotfiles-ai/hermes-review-cron-id"
    watchdog_id_file = home / ".local/state/dotfiles-ai/hermes-watchdog-cron-id"
    assert id_file.read_text() == "abcdef123456\n"
    assert watchdog_id_file.read_text() == "fedcba654321\n"

    second = subprocess.run(["bash"], input=rendered, env=env, text=True, capture_output=True)
    assert second.returncode == 0, second.stderr
    commands = log.read_text()
    assert commands.count("cron create") == 2
    assert "cron edit abcdef123456" in commands
    assert "cron edit fedcba654321" in commands

    failed = subprocess.run(
        ["bash"], input=rendered, env={**env, "FAIL_EDIT": "1"},
        text=True, capture_output=True,
    )
    assert failed.returncode != 0
    assert "refusing to create a duplicate" in failed.stderr
    assert log.read_text().count("cron create") == 2


def test_updater_tracks_latest_with_backup_and_health_check() -> None:
    updater = chezmoi("cat", str(Path.home() / ".local/bin/hermes-update")).stdout
    assert "hermes update --backup --yes" in updater
    assert "hermes doctor" in updater
    assert "hermes gateway status" in updater

    plist = chezmoi(
        "cat", str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.hermes-update.plist")
    ).stdout
    assert "dev.dotfiles-ai.hermes-update" in plist
    assert "<key>Weekday</key>\n        <integer>0</integer>" in plist
    assert "<key>Hour</key>\n        <integer>4</integer>" in plist


def test_watchdog_wakes_only_on_changed_actionable_worker_state(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    dbsctrctl = bin_dir / "dbsctrctl"
    herdr = bin_dir / "herdr"
    dbsctrctl.write_text(
        "#!/bin/sh\nprintf '%s\\n' '{\"workers\":[{\"worker_id\":\"worker-1\",\"session_id\":\"session-1\",\"state\":\"discovery\"}]}'\n"
    )
    herdr.write_text(
        "#!/bin/sh\nprintf '%s\\n' '{\"result\":{\"agents\":[{\"agent_session\":{\"value\":\"session-1\"},\"agent_status\":\"blocked\"}]}}'\n"
    )
    dbsctrctl.chmod(0o755)
    herdr.chmod(0o755)
    script = render_source("private_dot_hermes/private_scripts/executable_dbsctr-watchdog.py.tmpl")
    state = tmp_path / "watchdog.json"
    env = {**os.environ, "DBSCTRCTL": str(dbsctrctl), "HERDR": str(herdr),
           "DBSCTR_WATCHDOG_STATE": str(state)}
    first = subprocess.run(["python3"], input=script, env=env, text=True, capture_output=True, check=True)
    assert json.loads(first.stdout)["wakeAgent"] is True
    repeated = subprocess.run(["python3"], input=script, env=env, text=True, capture_output=True, check=True)
    assert json.loads(repeated.stdout) == {"wakeAgent": False}
    assert state.stat().st_mode & 0o777 == 0o600


def test_example_documents_machine_local_hermes_settings() -> None:
    example = (ROOT / "config.example.toml").read_text()
    for term in (
        "[data.dotfiles_ai.hermes]", "review_schedule", "review_delivery",
        "provider", "openai-codex", "model", "gpt-5.5", "review_workdir",
        "watchdog_schedule", "workspace_label", "github_account", "github_repository",
        "update_weekday", "update_hour",
        "[[data.dotfiles_ai.hermes.repositories]]",
    ):
        assert term in example
