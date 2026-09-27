"""Qualify a downloaded macOS Herdr pin in an isolated, named server."""
import hashlib
import contextlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tomllib


def main():
    binary = Path(sys.argv[1]).resolve(strict=True)
    pin = tomllib.loads((Path(__file__).parents[1] / ".chezmoidata.toml").read_text())["dotfiles_ai"]["herdr"]
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == pin["asset_sha256"]
    parent = Path(tempfile.gettempdir()) / "opencode"
    parent.mkdir(exist_ok=True)
    # macOS Unix socket paths have a small fixed limit; keep fixture names short.
    with tempfile.TemporaryDirectory(prefix="h", dir=parent) as directory:
        root = Path(directory)
        env = {"HOME": str(root), "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
               "SHELL": "/bin/bash", "TERM": "xterm-256color",
               "HERDR_CONFIG_PATH": str(root / "config.toml"),
               "XDG_CONFIG_HOME": str(root), "XDG_DATA_HOME": str(root / "data"),
               "XDG_STATE_HOME": str(root / "state"), "XDG_CACHE_HOME": str(root / "cache")}
        def run(*arguments):
            return subprocess.run([str(binary), *arguments], cwd=root, env=env,
                                  check=True, capture_output=True, text=True, timeout=10).stdout
        assert run("--version").strip() == "herdr " + pin["version"]
        session = "q"
        with (root / "server.log").open("w") as log:
            server = subprocess.Popen([str(binary), "--session", session, "server"],
                                      cwd=root, env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    try:
                        status = json.loads(run("--session", session, "status", "server", "--json"))
                        if status.get("running"):
                            break
                    except (subprocess.SubprocessError, json.JSONDecodeError):
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("isolated Herdr server did not start: " +
                                       (root / "server.log").read_text()[-4000:])
                assert status["version"] == pin["version"]
                assert status["protocol"] == pin["protocol"]
                assert status["compatible"] is True
                assert Path(status["socket"]).is_relative_to(root)
                assert status["session"] == session
                panes = json.loads(run("--session", session, "pane", "list"))
                assert isinstance(panes["result"]["panes"], list)
            finally:
                try:
                    with contextlib.suppress(subprocess.CalledProcessError):
                        run("--session", session, "server", "stop")
                finally:
                    if server.poll() is None:
                        server.terminate()
                    server.wait(timeout=10)
    print(json.dumps({"release": pin["version"], "protocol": pin["protocol"],
                      "checksum": "passed", "isolated_server": "passed"}))


if __name__ == "__main__":
    main()
