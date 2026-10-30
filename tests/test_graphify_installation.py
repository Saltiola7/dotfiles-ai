"""One native global owner; fixture tools never touch an installed runtime."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from test_portable_distribution import ROOT, data


SOURCE = ROOT / "run_onchange_after_install-graphify.sh.tmpl"


def render(path=SOURCE, system="darwin", arch="arm64"):
    configured = data()
    configured["chezmoi"] = {"os": system, "arch": arch}
    return subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(configured), "execute-template"],
        input=path.read_text(), text=True, capture_output=True, check=True,
    ).stdout


def executable(path, body):
    path.write_text(f"#!{sys.executable}\n" + body)
    path.chmod(0o755)


@pytest.fixture
def installation(tmp_path):
    home, tools, caller = (tmp_path / name for name in ("home", "tools", "caller"))
    for path in (home, tools, caller):
        path.mkdir()
    runtime = home / ".local/share/uv/tools/graphifyy"
    seed = tmp_path / "seed"
    (seed / "bin").mkdir(parents=True)
    package = seed / "package"
    references = package / "skills/opencode/references"
    references.mkdir(parents=True)
    (package / "skill-opencode.md").write_text("# /graphify\nFixture packaged skill.\n")
    (references / "query.md").write_text("Fixture query reference.\n")
    (seed / "version").write_text("0.9.50")
    (seed / "uv-receipt.toml").write_text(
        '[tool]\nrequirements = [{name = "graphifyy"}]\nentrypoints = ['
        f'{{name = "graphify", install-path = {json.dumps(str(tools / "graphify"))}}}]\n'
    )
    executable(seed / "bin/python", '''import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
if (root / "missing-extra").exists():
    sys.exit(1)
print(json.dumps({"version": (root / "version").read_text(), "prefix": str(root),
                  "package": str(root / "package")}))
''')
    executable(seed / "bin/graphify", '''import os, shutil, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
assert "GEMINI_API_KEY" not in os.environ
if (root / "broken-cli").exists():
    sys.exit(1)
version = (root / "version").read_text()
if sys.argv[1:] == ["--version"]:
    print("warning: old installed skill", file=sys.stderr)
    print("graphify " + version)
    sys.exit(0)
assert sys.argv[1:] == ["install", "--platform", "opencode"]
if (root / "escape-target").exists():
    Path((root / "escape-target").read_text()).write_text("unapproved side effect")
destination = Path.home() / ".config/opencode/skills/graphify"
destination.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / "package/skill-opencode.md", destination / "SKILL.md")
shutil.copytree(root / "package/skills/opencode/references", destination / "references", dirs_exist_ok=True)
(destination / ".graphify_version").write_text("invalid" if (root / "bad-skill").exists() else version)
plugin = Path.cwd() / ".opencode/plugins/graphify.js"
plugin.parent.mkdir(parents=True, exist_ok=True)
plugin.write_text("fixture project side effect")
''')
    executable(tools / "uv", f'''import json, shutil, sys
from pathlib import Path
home, tools, runtime, seed = map(Path, {list(map(str, (home, tools, runtime, seed)))!r})
args = sys.argv[1:]
if args == ["tool", "dir"]:
    print(runtime.parent)
elif args == ["tool", "dir", "--bin"]:
    print(tools)
elif args[:2] == ["python", "find"]:
    if (runtime / "missing-python").exists():
        sys.exit(1)
    print({sys.executable!r})
elif args[:2] == ["tool", "install"]:
    with (home / "install.jsonl").open("a") as handle:
        handle.write(json.dumps(args) + "\\n")
    shutil.copytree(seed, runtime)
    (runtime / "version").write_text(next(value.split("==")[1] for value in args if value.startswith("graphifyy==")))
    (tools / "graphify").symlink_to(runtime / "bin/graphify")
else:
    sys.exit(2)
''')
    (tools / "python3").symlink_to(sys.executable)
    env = {**os.environ, "HOME": str(home), "PATH": f"{tools}:/usr/bin:/bin",
           "GEMINI_API_KEY": "must-not-be-forwarded", "TMPDIR": str(tmp_path)}
    return home, tools, caller, runtime, seed, env


def install(fixture):
    home, tools, caller, runtime, seed, env = fixture
    return subprocess.run(["/bin/bash"], input=render(), cwd=caller, env=env,
                          text=True, capture_output=True, timeout=20)


def retain(fixture, version="0.9.50"):
    home, tools, caller, runtime, seed, env = fixture
    shutil.copytree(seed, runtime)
    (runtime / "version").write_text(version)
    (tools / "graphify").symlink_to(runtime / "bin/graphify")


def bundle(path):
    return {file.relative_to(path).as_posix(): file.read_bytes()
            for file in path.rglob("*") if file.is_file()}


def test_missing_bootstrap_preserves_recipe_and_reapplies(installation):
    home, tools, caller, runtime, seed, env = installation
    result = install(installation)
    assert result.returncode == 0, result.stderr
    command, = [json.loads(line) for line in (home / "install.jsonl").read_text().splitlines()]
    for required in ("graphifyy==0.9.97", "anthropic[vertex]", "boto3", "tree-sitter-hcl",
                     "tree-sitter-language-pack==0.11.0", "tree-sitter-sql", "--no-python-downloads"):
        assert required in command
    assert not {"--force", "--upgrade", "--reinstall"}.intersection(command)
    destination = home / ".config/opencode/skills/graphify"
    before = bundle(destination)
    assert before[".graphify_version"].strip() == b"0.9.97"
    assert "references/query.md" in before
    assert not (caller / ".opencode").exists()
    assert not (home / ".opencode").exists()
    assert install(installation).returncode == 0
    assert bundle(destination) == before
    assert len((home / "install.jsonl").read_text().splitlines()) == 1


@pytest.mark.parametrize("version", ["0.9.50", "0.10.0"])
def test_healthy_existing_runtime_and_dependencies_are_not_replaced(installation, version):
    home, tools, caller, runtime, seed, env = installation
    retain(installation, version)
    before = bundle(runtime)
    result = install(installation)
    assert result.returncode == 0, result.stderr
    assert bundle(runtime) == before
    assert not (home / "install.jsonl").exists()
    assert (home / ".config/opencode/skills/graphify/.graphify_version").read_text().strip() == version


@pytest.mark.parametrize("failure", ["missing-extra", "broken-cli", "bad-skill", "orphan", "missing-uv", "missing-python"])
def test_failed_admission_keeps_existing_skill_and_does_not_install(installation, failure):
    home, tools, caller, runtime, seed, env = installation
    retain(installation)
    destination = home / ".config/opencode/skills/graphify"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text("Retain this preimage.\n")
    before = bundle(destination)
    if failure == "orphan":
        (tools / "graphify").unlink()
    elif failure == "missing-uv":
        (tools / "uv").unlink()
    else:
        (runtime / failure).touch()
    result = install(installation)
    assert result.returncode != 0
    assert bundle(destination) == before
    assert not (home / "install.jsonl").exists()
    assert not (caller / ".opencode").exists()


def test_refresh_preserves_complete_prior_skill_outside_discovery(installation):
    home, tools, caller, runtime, seed, env = installation
    retain(installation)
    destination = home / ".config/opencode/skills/graphify"
    destination.mkdir(parents=True)
    old = b"Prior skill customization.\n"
    (destination / "SKILL.md").write_bytes(old)
    result = install(installation)
    assert result.returncode == 0, result.stderr
    assert (destination / "SKILL.md").read_bytes() != old
    preimages = [path for path in (home / ".config/opencode").rglob("SKILL.md")
                 if path != destination / "SKILL.md"]
    assert any(path.read_bytes() == old for path in preimages)
    assert not any(path.is_relative_to(home / ".config/opencode/skills") for path in preimages)


@pytest.mark.parametrize("conflict", ["second-cli", "skill-symlink", "foreign-receipt"])
def test_conflicting_ownership_is_not_reconciled_implicitly(installation, conflict):
    home, tools, caller, runtime, seed, env = installation
    retain(installation)
    if conflict == "second-cli":
        other = caller / "tools"
        other.mkdir()
        executable(other / "graphify", "raise SystemExit(0)\n")
        env["PATH"] += ":" + str(other)
    elif conflict == "skill-symlink":
        destination = home / ".config/opencode/skills/graphify"
        destination.parent.mkdir(parents=True)
        destination.symlink_to(caller, target_is_directory=True)
    else:
        (runtime / "uv-receipt.toml").write_text(
            '[tool]\nrequirements = [{name = "graphifyy"}]\n'
            'entrypoints = [{name = "graphify", install-path = "/unrelated/graphify"}]\n')
    before = bundle(home)
    result = install(installation)
    assert result.returncode != 0
    assert bundle(home) == before
    assert not (home / "install.jsonl").exists()


def test_native_skill_installer_cannot_write_outside_private_scratch(installation):
    home, tools, caller, runtime, seed, env = installation
    retain(installation)
    target = caller / "unapproved"
    (runtime / "escape-target").write_text(str(target))
    assert install(installation).returncode != 0
    assert not target.exists()
    assert not (home / ".config/opencode/skills/graphify").exists()


def test_installer_driver_does_not_import_caller_modules(installation):
    home, tools, caller, runtime, seed, env = installation
    retain(installation)
    (caller / "json.py").write_text("raise RuntimeError('caller module must not be imported')\n")
    result = install(installation)
    assert result.returncode == 0, result.stderr
    assert (home / ".config/opencode/skills/graphify/SKILL.md").is_file()


@pytest.mark.skipif(not os.environ.get("GRAPHIFY_NATIVE_TEST_EXECUTABLE"),
                    reason="already-qualified native Graphify runtime not selected")
def test_native_runtime_refreshes_only_isolated_skill(installation):
    home, tools, caller, runtime, seed, env = installation
    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(["git", "init", "-q", str(caller)], env=git_env, check=True)
    subprocess.run(["git", "-C", str(caller), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.com", "-c", "commit.gpgsign=false",
                    "commit", "--allow-empty", "-qm", "fixture"], env=git_env, check=True)
    native = Path(os.environ["GRAPHIFY_NATIVE_TEST_EXECUTABLE"]).resolve(strict=True)
    uv = shutil.which("uv")
    assert uv
    (tools / "uv").unlink()
    (tools / "uv").symlink_to(uv)
    (tools / "graphify").symlink_to(native)
    env.update(UV_TOOL_DIR=str(home / "empty-uv-tools"), UV_TOOL_BIN_DIR=str(tools),
               UV_CACHE_DIR=str(home / "uv-cache"))
    result = install(installation)
    assert result.returncode == 0, result.stderr
    destination = home / ".config/opencode/skills/graphify"
    before = bundle(destination)
    assert before[".graphify_version"].strip()
    assert "SKILL.md" in before and any(name.startswith("references/") for name in before)
    assert not (caller / ".opencode").exists()
    assert not (home / ".opencode").exists()
    assert install(installation).returncode == 0
    assert bundle(destination) == before
    assert not (home / "empty-uv-tools").exists(), "retained native runtime was not an install request"
    binary = os.environ.get("OPENCODE_NATIVE_TEST_EXECUTABLE")
    if binary:
        import pwd
        system_sources = [Path("/Library/Application Support/opencode"),
                          Path("/Library/Managed Preferences/ai.opencode.managed.plist"),
                          Path("/Library/Managed Preferences") / pwd.getpwuid(os.getuid()).pw_name /
                          "ai.opencode.managed.plist"]
        assert not any(path.exists() for path in system_sources), "system policy needs separate fixture qualification"
        native_env = {"PATH": os.defpath, "HOME": str(home), "OPENCODE_TEST_HOME": str(home),
                      "TERM": "dumb", "NO_COLOR": "1"}
        for key, suffix in {"XDG_CONFIG_HOME": ".config", "OPENCODE_CONFIG_DIR": ".config/opencode",
                            "XDG_DATA_HOME": "data", "XDG_STATE_HOME": "state",
                            "XDG_CACHE_HOME": "cache", "TMPDIR": "tmp"}.items():
            path = home / suffix
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            native_env[key] = str(path)
        (home / ".config/opencode/opencode.json").write_text(json.dumps(
            {"update": "disable", "plugins": [], "mcp": {"servers": {}}}))
        profile = ('(version 1) (allow default) (deny network*) '
                   '(allow network-inbound (local ip "localhost:*")) '
                   '(allow network-outbound (remote ip "localhost:*"))')
        import secrets
        import selectors
        import time
        from urllib.parse import urlsplit

        # One-shot standalone API exits before asynchronous skill plugins activate.
        # Keep one fixture-only, in-memory server until readiness; never use a live service.
        native_env.update(OPENCODE_PASSWORD=secrets.token_urlsafe(32), OPENCODE_DB=":memory:",
                          OPENCODE_DISABLE_MODELS_FETCH="1")
        child = subprocess.Popen(
            ["/usr/bin/sandbox-exec", "-p", profile, binary, "serve", "--stdio",
             "--hostname", "127.0.0.1", "--port", "0"], cwd=caller, env=native_env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                assert selector.select(15), "private native server did not become ready"
                url = json.loads(child.stdout.readline())["url"]
            address = urlsplit(url)
            assert address.scheme == "http" and address.hostname == "127.0.0.1" and address.port

            def api(*arguments):
                result = subprocess.run(
                    ["/usr/bin/sandbox-exec", "-p", profile, binary, "api", "--server", url, *arguments],
                    cwd=caller, env=native_env, capture_output=True, text=True, timeout=10,
                )
                assert result.returncode == 0, "private native API request failed"
                return json.loads(result.stdout)

            info = api("get", "/api/info")
            assert info["pid"] == child.pid, "response was not from the owned fixture child"
            deadline = time.monotonic() + 30
            while True:
                plugins = api("plugin.list", "--param", f"location[directory]={caller}")["data"]
                states = {item["id"]: item["state"]["status"] for item in plugins if "id" in item}
                selected = [states.get(name) for name in ("opencode.skill", "opencode.config.skill")]
                assert "failed" not in selected, "private skill plugin activation failed"
                if selected == ["active", "active"]:
                    break
                assert time.monotonic() < deadline, "private skill registry readiness timed out"
                time.sleep(.1)
            skills = api("skill.list", "--param", f"location[directory]={caller}")["data"]
            assert any(item["id"] == "graphify" for item in skills)
        finally:
            child.stdin.close()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()  # Only this still-owned fixture process, never another consumer.
                child.wait(timeout=5)
            child.stdout.close()


@pytest.mark.parametrize("system,arch", [("linux", "arm64"), ("linux", "amd64"), ("darwin", "amd64")])
def test_excluded_platform_does_not_probe_or_install(system, arch):
    result = subprocess.run(["/bin/bash"], input=render(system=system, arch=arch),
                            env={"PATH": "/unavailable"}, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "install-graphify.sh" in render(ROOT / ".chezmoiignore", system, arch).splitlines()
