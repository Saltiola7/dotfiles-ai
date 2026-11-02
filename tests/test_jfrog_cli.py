"""Optional JFrog CLI ownership; all executable/download fixtures are synthetic."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import sys
import tomllib

import pytest

from test_portable_distribution import ROOT, data


SOURCE = ROOT / "run_onchange_after_install-jfrog-cli.sh.tmpl"
ASSETS = {
    ("darwin", "arm64"): ("mac-arm64", "0c576178e007a21f8b3df421e1c0bb735f4ed6461a78c3b97dd170c1e6ed911c"),
    ("darwin", "amd64"): ("mac-386", "83dd20eb3a9be26b101ae9253ecafd59822c33b24d50e56339c1214600452daa"),
    ("linux", "amd64"): ("linux-amd64", "8aaa3d46934e23a75c23a209780d95508199cddb5398b88e1c179cc86024a314"),
    ("linux", "arm64"): ("linux-arm64", "affa031c592fa4f587794dbfd7d4ed5e47c9b91ef15a494015a6fecc0a5bc43a"),
}


def render(*, enabled=True, platform="darwin", arch="arm64"):
    configured = data()
    configured["chezmoi"] = {"os": platform, "arch": arch}
    configured["dotfiles_ai"]["jfrog_cli"] = {"enabled": enabled}
    result = subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(configured), "execute-template"],
        input=SOURCE.read_text(), text=True, capture_output=True, check=True,
    )
    subprocess.run(["/bin/bash", "-n"], input=result.stdout, text=True, check=True)
    return result.stdout


def executable(path, content):
    path.write_text(content)
    path.chmod(0o755)
    return path


def candidate_content(log, version="2.129.0", exit_code=0, noisy=False):
    return f"#!{sys.executable}\n" + (
        "import json,os,pathlib,sys\n"
        f"log=pathlib.Path({str(log)!r})\n"
        "with log.open('a') as output:\n"
        " output.write(json.dumps({'args':sys.argv[1:],'env':dict(os.environ)})+'\\n')\n"
        "pathlib.Path(os.environ['HOME'],'probe-created').write_text('private')\n"
        + ("print('CANARY-'*10000)\n" if noisy else f"print('jf version {version}')\n")
        + f"sys.exit({exit_code})\n"
    )


@pytest.fixture
def sandbox(tmp_path):
    home, tools = tmp_path / "home", tmp_path / "tools"
    home.mkdir(mode=0o700)
    tools.mkdir(mode=0o700)
    (tools / "python3").symlink_to(sys.executable)
    cli_log, curl_log = tmp_path / "cli-calls", tmp_path / "curl-calls"
    candidate = tmp_path / "candidate"
    candidate.write_text(candidate_content(cli_log))
    exit_file = tmp_path / "curl-exit"
    exit_file.write_text("0")
    race_file = tmp_path / "create-race"
    executable(tools / "curl", f"#!{sys.executable}\n" +
               "import json,pathlib,sys\n"
               f"log=pathlib.Path({str(curl_log)!r})\n"
               "with log.open('a') as output: output.write(json.dumps(sys.argv[1:])+'\\n')\n"
               f"code=int(pathlib.Path({str(exit_file)!r}).read_text())\n"
               "if code: print('download-CANARY',file=sys.stderr); sys.exit(code)\n"
               "destination=pathlib.Path(sys.argv[sys.argv.index('--output')+1])\n"
               f"destination.write_bytes(pathlib.Path({str(candidate)!r}).read_bytes())\n"
               f"if pathlib.Path({str(race_file)!r}).exists():\n"
               f" pathlib.Path({str(home / '.local/bin/jf')!r}).write_text('foreign-race')\n")
    environment = {"HOME": str(home), "PATH": f"{tools}:/usr/bin:/bin",
                   "JFROG_CLI_HOME_DIR": str(home / "native-private"),
                   "JFROG_CLI_SERVER_ID": "CANARY-server", "JFROG_CLI_ENCRYPTION_KEY": "CANARY-key",
                   "JF_ACCESS_TOKEN": "CANARY-token", "JF_URL": "https://CANARY.invalid"}
    native = home / ".jfrog"
    native.mkdir(mode=0o700)
    (native / "jfrog-cli.conf.v6").write_text("private-CANARY")
    return {"home": home, "tools": tools, "candidate": candidate,
            "cli_log": cli_log, "curl_log": curl_log, "exit_file": exit_file,
            "race_file": race_file, "env": environment}


def run(script, sandbox):
    return subprocess.run(["/bin/bash"], input=script, text=True, capture_output=True,
                          env=sandbox["env"], timeout=20)


def synthetic_script(sandbox, **options):
    script = render(**options)
    digest = hashlib.sha256(sandbox["candidate"].read_bytes()).hexdigest()
    for _, expected in ASSETS.values():
        script = script.replace(expected, digest)
    return script


def test_cli_defaults_are_independent_and_off():
    defaults = tomllib.loads((ROOT / ".chezmoidata.toml").read_text())["dotfiles_ai"]
    assert defaults.get("jfrog_cli", {}).get("enabled") is False
    example = tomllib.loads((ROOT / "config.example.toml").read_text())["data"]["dotfiles_ai"]
    assert example["jfrog_cli"]["enabled"] is False


def test_disabled_cli_needs_no_tools_or_home():
    result = subprocess.run(["/bin/bash"], input=render(enabled=False), text=True,
                            capture_output=True, env={"PATH": "/not-present"}, timeout=5)
    assert result.returncode == 0 and result.stdout == result.stderr == ""


@pytest.mark.parametrize("platform,arch", ASSETS)
def test_each_supported_platform_downloads_only_its_pinned_asset(sandbox, platform, arch):
    script = render(platform=platform, arch=arch)
    for _, expected in ASSETS.values():
        assert expected in script
    result = run(synthetic_script(sandbox, platform=platform, arch=arch), sandbox)
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in sandbox["curl_log"].read_text().splitlines()]
    assert len(calls) == 1
    assert calls[0][0] == "-q"
    assert calls[0][-1] == (
        "https://releases.jfrog.io/artifactory/jfrog-cli/v2-jf/2.129.0/jfrog-cli-"
        + ASSETS[platform, arch][0] + "/jf"
    )
    target = sandbox["home"] / ".local/bin/jf"
    assert target.read_bytes() == sandbox["candidate"].read_bytes()
    assert target.stat().st_mode & 0o777 == 0o755
    assert target.stat().st_nlink == 1


@pytest.mark.parametrize("platform,arch", [("freebsd", "amd64"), ("linux", "386")])
def test_unsupported_platform_fails_before_creating_state(sandbox, platform, arch):
    result = run(render(platform=platform, arch=arch), sandbox)
    assert result.returncode != 0
    assert not (sandbox["home"] / ".local").exists()
    assert not sandbox["curl_log"].exists() and not sandbox["cli_log"].exists()


def test_repeat_apply_preserves_pinned_install_even_when_not_in_path(sandbox):
    script = synthetic_script(sandbox)
    for _ in range(2):
        result = run(script, sandbox)
        assert result.returncode == 0, result.stderr
    assert len(sandbox["curl_log"].read_text().splitlines()) == 1
    assert (sandbox["home"] / ".jfrog/jfrog-cli.conf.v6").read_text() == "private-CANARY"
    assert not (sandbox["home"] / "probe-created").exists()
    assert not list((sandbox["home"] / ".local/bin").glob(".jfrog-cli.*"))


@pytest.mark.parametrize("version", ["2.106.0", "2.140.3"])
def test_selected_existing_owner_and_symlink_are_preserved(sandbox, version):
    native = sandbox["home"] / "native-bin"
    native.mkdir(mode=0o700)
    real = executable(native / "owned-jf", candidate_content(sandbox["cli_log"], version))
    (native / "jf").symlink_to(real)
    before = real.read_bytes()
    sandbox["env"]["PATH"] = f"{native}:" + sandbox["env"]["PATH"]
    result = run(render(), sandbox)
    assert result.returncode == 0, result.stderr
    assert real.read_bytes() == before and (native / "jf").is_symlink()
    assert not sandbox["curl_log"].exists() and not (sandbox["home"] / ".local").exists()


def test_incompatible_existing_cli_is_retained_without_download(sandbox):
    native = sandbox["home"] / "native-bin"
    native.mkdir(mode=0o700)
    existing = executable(native / "jf", candidate_content(sandbox["cli_log"], "2.105.9"))
    before = existing.read_bytes()
    sandbox["env"]["PATH"] = f"{native}:" + sandbox["env"]["PATH"]
    result = run(render(), sandbox)
    assert result.returncode != 0 and existing.read_bytes() == before
    assert not sandbox["curl_log"].exists() and not (sandbox["home"] / ".local").exists()


@pytest.mark.parametrize("collision", ["file", "directory", "symlink", "ancestor-link", "writable-parent"])
def test_destination_collisions_are_never_overwritten_or_followed(sandbox, collision):
    parent = sandbox["home"] / ".local/bin"
    parent.mkdir(parents=True)
    target = parent / "jf"
    if collision == "file":
        target.write_text("foreign-bytes")
    elif collision == "directory":
        target.mkdir()
    elif collision == "symlink":
        target.symlink_to(parent / "missing")
    elif collision == "ancestor-link":
        parent.rmdir()
        other = sandbox["home"] / "other-bin"
        other.mkdir()
        parent.symlink_to(other, target_is_directory=True)
    else:
        parent.chmod(0o777)
    result = run(synthetic_script(sandbox), sandbox)
    assert result.returncode != 0
    assert not sandbox["curl_log"].exists() and not sandbox["cli_log"].exists()
    if collision == "file":
        assert target.read_text() == "foreign-bytes"
    elif collision in {"symlink", "ancestor-link"}:
        assert (target if collision == "symlink" else parent).is_symlink()


def test_checksum_failure_precedes_any_candidate_execution(sandbox):
    result = run(render(), sandbox)
    assert result.returncode != 0
    assert sandbox["curl_log"].exists() and not sandbox["cli_log"].exists()
    assert not (sandbox["home"] / ".local/bin/jf").exists()
    assert not list((sandbox["home"] / ".local/bin").glob(".jfrog-cli.*"))


def test_download_failure_retains_status_without_leaking_output(sandbox):
    sandbox["exit_file"].write_text("23")
    result = run(synthetic_script(sandbox), sandbox)
    assert result.returncode == 23
    assert "CANARY" not in result.stdout + result.stderr
    assert not sandbox["cli_log"].exists() and not (sandbox["home"] / ".local/bin/jf").exists()


@pytest.mark.parametrize("version,exit_code,noisy", [("2.128.0", 0, False), ("2.129.0", 17, False),
                                                     ("2.129.0", 0, True)])
def test_unqualified_candidate_is_not_published(sandbox, version, exit_code, noisy):
    sandbox["candidate"].write_text(candidate_content(sandbox["cli_log"], version, exit_code, noisy))
    result = run(synthetic_script(sandbox), sandbox)
    assert result.returncode != 0
    assert "CANARY" not in result.stdout + result.stderr
    assert not (sandbox["home"] / ".local/bin/jf").exists()


def test_probe_environment_cannot_load_native_credentials_or_plugins(sandbox):
    result = run(synthetic_script(sandbox), sandbox)
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in sandbox["cli_log"].read_text().splitlines()]
    assert calls and all(call["args"] == ["--version"] for call in calls)
    for call in calls:
        environment = call["env"]
        assert environment["HOME"] != str(sandbox["home"])
        assert environment["JFROG_CLI_HOME_DIR"] != sandbox["env"]["JFROG_CLI_HOME_DIR"]
        assert environment["JFROG_CLI_REPORT_USAGE"] == "false"
        assert environment["JFROG_CLI_AVOID_NEW_VERSION_WARNING"] == "true"
        assert environment["CI"] == "true"
        assert "CANARY" not in json.dumps(environment)
    assert (sandbox["home"] / ".jfrog/jfrog-cli.conf.v6").read_text() == "private-CANARY"


def test_late_destination_creation_cannot_be_replaced(sandbox):
    sandbox["race_file"].touch()
    result = run(synthetic_script(sandbox), sandbox)
    assert result.returncode != 0
    assert (sandbox["home"] / ".local/bin/jf").read_text() == "foreign-race"


def test_failed_existing_cli_probe_preserves_owner_without_secret_output(sandbox):
    native = sandbox["home"] / "native-bin"
    native.mkdir(mode=0o700)
    existing = executable(native / "jf", candidate_content(sandbox["cli_log"], exit_code=17, noisy=True))
    before = existing.read_bytes()
    sandbox["env"]["PATH"] = f"{native}:" + sandbox["env"]["PATH"]
    result = run(render(), sandbox)
    assert result.returncode != 0 and "CANARY" not in result.stdout + result.stderr
    assert existing.read_bytes() == before and not sandbox["curl_log"].exists()
    assert not (sandbox["home"] / "probe-created").exists()


def test_cancellation_reaps_download_and_cleans_only_its_staging(sandbox):
    ready = sandbox["home"].parent / "download-ready"
    executable(sandbox["tools"] / "curl", f"#!{sys.executable}\n" +
               "import pathlib,time\n" + f"pathlib.Path({str(ready)!r}).touch()\n" +
               "time.sleep(60)\n")
    child = subprocess.Popen(["/bin/bash"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=sandbox["env"])
    try:
        child.stdin.write(synthetic_script(sandbox))
        child.stdin.close()
        deadline = time.monotonic() + 5
        while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), "synthetic downloader was not started"
        child.terminate()
        assert child.wait(timeout=5) == 143
        assert not (sandbox["home"] / ".local/bin/jf").exists()
        assert not list((sandbox["home"] / ".local/bin").glob(".jfrog-cli.*"))
        assert (sandbox["home"] / ".jfrog/jfrog-cli.conf.v6").read_text() == "private-CANARY"
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        child.stdout.close()
        child.stderr.close()
