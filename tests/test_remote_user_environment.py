import json
import os
from pathlib import Path
import stat
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
COMMAND = ROOT / "dot_local/bin/executable_remote-user-foundation"


def _render(path: str) -> str:
    data = {
        "dotfiles_ai": {
            "remote_user_environment": {"enabled": True},
            "state": {"root": "/shared/state"},
            "codex": {"version": "0.151.0"},
            "opencode": {
                "version": "1.18.25",
                "vertex_project": "local-project",
                "vertex_location": "global",
                "vertex_credentials": "/shared/credentials.json",
                "vertex_account": "",
            },
            "herdr": {"host_enabled": False},
        }
    }
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(data),
            "execute-template",
        ],
        input=(ROOT / path).read_text(), text=True, capture_output=True, check=True,
    ).stdout


def test_remote_user_environment_has_distinct_pinned_assets() -> None:
    defaults = (ROOT / ".chezmoidata.toml").read_text()
    example = (ROOT / "config.example.toml").read_text()
    remote_example = (ROOT / "config.remote-user.example.toml").read_text()
    ignore = (ROOT / ".chezmoiignore").read_text()
    tools = (ROOT / "run_onchange_after_install-guest-development-tools.sh.tmpl").read_text()
    starship = (ROOT / "run_onchange_after_install-starship.sh.tmpl").read_text()
    atuin = (ROOT / "run_onchange_after_install-atuin.sh.tmpl").read_text()
    codex = (ROOT / "dot_local/bin/executable_codex-install.tmpl").read_text()
    opencode = (ROOT / "dot_local/bin/executable_opencode-install.tmpl").read_text()
    herdr = (ROOT / "run_onchange_after_install-00-remote-herdr.sh.tmpl").read_text()

    assert "[dotfiles_ai.remote_user_environment]" in defaults
    assert "[data.dotfiles_ai.remote_user_environment]" in example
    assert "[data.dotfiles_ai.remote_user_environment]" in remote_example
    assert 'enabled = true' in remote_example
    assert "role =" not in remote_example
    for forbidden in ("password =", "token =", "api_key =", "secret ="):
        assert forbidden not in remote_example.lower()
    assert "remote_user_environment.enabled" in ignore
    assert "remote_workspace.enabled" in ignore
    assert "docker-compose-linux-x86_64" in tools
    assert "dba9d98e1ba5bfe11d88c99b9bd32fc4a0624a30fafe68eea34d61a3e42fd372" in tools
    assert "op_linux_amd64_v2.39.0.zip" in tools
    assert "6fba7f376b6c6dec49f41b06408930a43ad064cce103c6a2ce5b3d0413a86434" in tools
    assert "google-cloud-cli-580.0.0-linux-x86_64.tar.gz" in tools
    assert "e580c04b45dfa2e537b8dc0cf7c828e46a65bc77ef61de69161e1f3a124d7480" in tools
    assert "asset=starship-x86_64-unknown-linux-musl.tar.gz" in starship
    assert "b7c232b0e8249d8e55a40beb79c5c43a7d370f3f9408bd215deb0170daeaadf3" in starship
    assert "asset=atuin-x86_64-unknown-linux-musl.tar.gz" in atuin
    assert "5772df4121174a9f0b71c17260727794fde22a71b5a3ee5ac07b227eebcbfa9a" in atuin
    assert "codex-x86_64-unknown-linux-musl" in codex
    assert '"$archive_binary"' in codex
    assert "605b4b183f22c645f5def63a5b7191767407fb66a6feaec4eaf10b5b7e0058f6" in defaults
    assert "opencode-linux-x64.tar.gz" in defaults
    assert "linux_amd64_asset_url" in opencode
    assert "58a3729a6f3432dd6d2917fcc4a949788891a035818646ad480e12c947f56e78" in defaults
    assert "herdr-linux-x86_64" in defaults
    assert "linux_amd64_asset_url" in herdr
    assert "976150a14d490c94b243ea2e1a7eb2dfb67f12e36b182db90936f6728e6aecf4" in defaults
    for source in (tools, starship, atuin, codex, opencode, herdr):
        assert "remote_user_environment.enabled" in source
        assert "uname -m" in source
    assert "DOTFILES_AI_SYSTEMCTL" in tools
    assert "install-00-remote-herdr.sh" in ignore
    assert "install-01-remote-opencode.sh" in ignore
    wrapper = (ROOT / "dot_local/bin/executable_opencode.tmpl").read_text()
    assert '{{ if eq .chezmoi.os "darwin" -}}\n    if [[ $session == 1 ]]' in wrapper


def test_remote_agent_wrappers_force_per_user_state_and_adc() -> None:
    opencode = _render("dot_local/bin/executable_opencode.tmpl")
    codex = _render("dot_local/bin/executable_codex.tmpl")
    vertex = _render("dot_local/bin/executable_vertex-reauth.tmpl")
    config = json.loads(_render(".chezmoitemplates/opencode.json.tmpl"))

    assert 'export XDG_CONFIG_HOME="$HOME/.config"' in opencode
    assert 'export XDG_DATA_HOME="$HOME/.local/share"' in opencode
    assert 'export XDG_STATE_HOME="$HOME/.local/state"' in opencode
    assert 'export XDG_CACHE_HOME="$HOME/.cache"' in opencode
    assert "/shared/state" not in opencode + codex
    assert 'export CODEX_HOME="$HOME/.local/state/dotfiles-ai/codex"' in codex
    assert 'ADC="$HOME/.config/gcloud/application_default_credentials.json"' in vertex
    assert "/shared/credentials.json" not in vertex
    assert config["provider"]["google-vertex-anthropic"]["options"] == {
        "project": "local-project", "location": "global",
    }


@pytest.mark.parametrize("failed", [None, "opencode", "codex", "vertex-reauth", "op"])
def test_remote_agent_readiness_is_content_free(tmp_path: Path, failed: str | None) -> None:
    script = tmp_path / "remote-agent-readiness"
    script.write_text(_render("dot_local/bin/executable_remote-agent-readiness.tmpl"))
    script.chmod(0o755)
    (tmp_path / ".config/opencode").mkdir(parents=True)
    (tmp_path / ".config/opencode/opencode.json").write_text("{}\n")
    (tmp_path / ".local/state/dotfiles-ai/codex").mkdir(parents=True)
    (tmp_path / ".local/state/dotfiles-ai/codex/config.toml").write_text("\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    private = "private-account private-token private-path private-session private-content"
    commands = {
        "opencode": f'''#!/bin/bash
[[ $1 == --version ]] && {{ echo 1.18.25; exit; }}
[[ {failed!r} == opencode ]] && exit 1
echo "OpenAI {private}"
''',
        "codex": f'''#!/bin/bash
[[ $1 == --version ]] && {{ echo "codex-cli 0.151.0"; exit; }}
[[ {failed!r} == codex ]] && exit 1
echo "{private}"
''',
        "vertex-reauth": f'''#!/bin/bash
[[ {failed!r} == vertex-reauth ]] && exit 1
echo "{private}"
''',
        "op": f'''#!/bin/bash
[[ {failed!r} == op ]] && exit 1
echo "{private}"
''',
    }
    for name, source in commands.items():
        path = binary / name
        path.write_text(source)
        path.chmod(0o755)

    result = subprocess.run(
        [str(script)], text=True, capture_output=True,
        env={"HOME": str(tmp_path), "PATH": f"{binary}:/usr/bin:/bin"},
    )

    expected_state = "ready" if failed is None else "auth_pending"
    expected = {
        "codex": "failure" if failed == "codex" else "success",
        "onepassword": "failure" if failed == "op" else "success",
        "openai": "failure" if failed == "opencode" else "success",
        "state": expected_state,
        "vertex": "failure" if failed == "vertex-reauth" else "success",
    }
    assert json.loads(result.stdout) == expected
    assert result.returncode == (0 if failed is None else 1)
    assert result.stderr == ""
    assert not any(value in result.stdout for value in private.split())


def _commit(repository: Path, content: str) -> str:
    (repository / "managed.txt").write_text(content)
    subprocess.run(["git", "add", "managed.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-m", content], cwd=repository, check=True,
                   capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
        text=True, capture_output=True,
    ).stdout.strip()


def _foundation(tmp_path: Path, *arguments: str, fail: bool = False) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    source = tmp_path / "source"
    state = tmp_path / "state.json"
    config = tmp_path / "chezmoi.toml"
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    chezmoi = binary / "chezmoi"
    chezmoi.write_text(
        "#!/bin/sh\n"
        "case \" $* \" in\n"
        "  *' managed '*) printf '%s\\n' '.bashrc' '.config/opencode/opencode.json' ;;\n"
        "  *' apply '*) test \"${FAIL_APPLY:-0}\" != 1 ;;\n"
        "  *) exit 2 ;;\n"
        "esac\n"
    )
    chezmoi.chmod(0o755)
    environment = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{binary}:{os.environ['PATH']}",
        "DOTFILES_AI_SOURCE": str(source),
        "DOTFILES_AI_CONFIG": str(config),
        "DOTFILES_AI_FOUNDATION_STATE": str(state),
        "FAIL_APPLY": "1" if fail else "0",
    }
    return subprocess.run(
        [str(COMMAND), *arguments], text=True, capture_output=True,
        env=environment,
    )


def test_foundation_apply_retry_and_rollback_preserve_unrelated_state(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source, check=True)
    first = _commit(source, "first")
    second = _commit(source, "second")
    home = tmp_path / "home"
    home.mkdir()
    unrelated = home / "unrelated"
    unrelated.write_text("keep")

    result = _foundation(tmp_path, "apply", first)
    assert result.returncode == 0, result.stderr
    state_path = tmp_path / "state.json"
    state = json.loads(state_path.read_text())
    assert state == {
        "attempt": 1,
        "desired_revision": first,
        "managed_targets": [".bashrc", ".config/opencode/opencode.json"],
        "previous_managed_targets": [],
        "previous_revision": None,
        "revision": first,
        "schema_version": 1,
        "state": "foundation_ready",
    }
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600

    failed = _foundation(tmp_path, "apply", second, fail=True)
    assert failed.returncode != 0
    state = json.loads(state_path.read_text())
    assert state["state"] == "failed_retryable"
    assert state["revision"] == first
    assert state["desired_revision"] == second
    assert state["previous_revision"] is None
    assert state["previous_managed_targets"] == []
    assert state["attempt"] == 2

    changed = _foundation(tmp_path, "apply", first)
    assert changed.returncode != 0
    assert "retry must use the recorded foundation revision" in changed.stderr

    retried = _foundation(tmp_path, "retry")
    assert retried.returncode == 0, retried.stderr
    state = json.loads(state_path.read_text())
    assert state["state"] == "foundation_ready"
    assert state["revision"] == second
    assert state["previous_revision"] == first
    assert state["previous_managed_targets"] == [
        ".bashrc", ".config/opencode/opencode.json",
    ]
    assert state["attempt"] == 3

    rolled_back = _foundation(tmp_path, "rollback")
    assert rolled_back.returncode == 0, rolled_back.stderr
    state = json.loads(state_path.read_text())
    assert state["revision"] == first
    assert state["previous_revision"] == second
    assert state["managed_targets"] == state["previous_managed_targets"]
    assert state["attempt"] == 4
    assert unrelated.read_text() == "keep"

    status_result = _foundation(tmp_path, "status")
    assert status_result.returncode == 0
    assert json.loads(status_result.stdout) == state
