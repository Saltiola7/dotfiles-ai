import json
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
                "review_delivery": "local",
                "review_tab": "dbsctr review",
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


def test_supervisor_policy_is_allowlisted_and_pauses_for_discovery() -> None:
    skill = chezmoi(
        "cat", str(Path.home() / ".hermes/skills/dbsctr-supervisor/SKILL.md")
    ).stdout
    assert "dotfiles-ai: /tmp/dotfiles-ai" in skill
    assert "seo-data-science: /tmp/seo-data-science" in skill
    assert "Never control a pane outside this allowlist" in skill
    assert "DBSCTR Cycle Record" in skill
    assert "pause" in skill.lower()
    assert "Discovery" in skill
    assert "merge" in skill.lower()
    assert "one historical cohort" in skill
    assert "/compact" in skill
    assert "absent, ambiguous" in skill
    assert "Never invoke" in skill
    assert "dbsctrctl review-scan" in skill
    assert "managed OpenCode" in skill


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
    assert ".local/state/dotfiles-ai/hermes-review-cron-id" in script
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
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    hermes.write_text(
        "#!/bin/bash\n"
        'printf "hermes %s\\n" "$*" >> "$COMMAND_LOG"\n'
        'if [[ "$1 $2" == "cron create" ]]; then printf "Created job: abcdef123456\\n"; fi\n'
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
    assert id_file.read_text() == "abcdef123456\n"

    second = subprocess.run(["bash"], input=rendered, env=env, text=True, capture_output=True)
    assert second.returncode == 0, second.stderr
    commands = log.read_text()
    assert commands.count("cron create") == 1
    assert "cron edit abcdef123456" in commands

    failed = subprocess.run(
        ["bash"], input=rendered, env={**env, "FAIL_EDIT": "1"},
        text=True, capture_output=True,
    )
    assert failed.returncode != 0
    assert "refusing to create a duplicate" in failed.stderr
    assert log.read_text().count("cron create") == 1


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


def test_example_documents_machine_local_hermes_settings() -> None:
    example = (ROOT / "config.example.toml").read_text()
    for term in (
        "[data.dotfiles_ai.hermes]", "review_schedule", "review_delivery",
        "provider", "openai-codex", "model", "gpt-5.5", "review_workdir", "review_tab",
        "update_weekday", "update_hour",
        "[[data.dotfiles_ai.hermes.repositories]]",
    ):
        assert term in example
