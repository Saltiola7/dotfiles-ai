"""Disposable PTY proof; no inherited configuration or sockets."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import termios
import time
import uuid

binary = Path(sys.argv[1]).resolve(strict=True)
os.umask(0o077)
with tempfile.TemporaryDirectory(prefix="k.") as temp:
    root = Path(temp)
    data = root / "c" / sys.argv[2]
    data.mkdir(parents=True)
    for sub in ("h", "r", "t"):
        (root / sub).mkdir()
    config = data / "config.toml"
    config.write_text("onboarding = false\n[session]\nresume_agents_on_restore = false\n")
    api = root / "h.sock"
    client = root / "h-client.sock"
    snapshot = data / "session.json"
    receipt = data / "session-final-save.json"
    env = {
        "PATH": "/usr/bin:/bin", "TERM": "xterm-256color", "SHELL": "/bin/sh",
        "HOME": str(root / "h"), "XDG_RUNTIME_DIR": str(root / "r"),
        "XDG_CONFIG_HOME": str(data.parent), "HERDR_CONFIG_PATH": str(config),
        "HERDR_SOCKET_PATH": str(api), "TMPDIR": str(root / "t"),
    }
    owned = []

    def spawn(args, extra=None, **io):
        proc = subprocess.Popen([binary, *args], env=env | (extra or {}), cwd=root,
                                start_new_session=True, **io)
        owned.append(proc)
        return proc

    def ask(method, params=None):
        with socket.socket(socket.AF_UNIX) as conn:
            conn.settimeout(.25)
            conn.connect(str(api))
            conn.sendall(json.dumps({"id": "1", "method": method, "params": params or {}}).encode() + b"\n")
            value = json.loads(conn.makefile("rb").readline())
            assert "error" not in value, value.get("error")
            return value["result"]

    def panes():
        result = ask("session.snapshot")
        return result.get("snapshot", result)["panes"]

    def wait(action, predicate=bool, seconds=6):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            try:
                value = action()
                if predicate(value):
                    return value
            except OSError:
                pass
            if "master" in globals():
                while select.select([master], [], [], 0)[0]:
                    try:
                        if not os.read(master, 65536):
                            break
                    except OSError:
                        break
            time.sleep(.045)
        raise AssertionError(f"timeout waiting for {action.__name__}")

    def keys(data):
        for key in data:
            os.write(master, bytes([key]))
            time.sleep(.045)

    def t():
        tab = json.loads(snapshot.read_bytes())["workspaces"][0]["tabs"][0]
        return tab

    def stop(server):
        ask("server.stop")
        assert server.wait(timeout=6) == 0

    log = (root / "server.log").open("w+")
    try:
        invocation = uuid.uuid4().hex
        server = spawn(["server"], {"HERDR_PROOF_SAVE_INVOCATION": invocation},
                       stdout=log, stderr=log)
        wait(lambda: api.exists() and client.exists())
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 110, 0, 0))
        try:
            tui = spawn([], stdin=slave, stdout=slave, stderr=slave)
        finally:
            os.close(slave)
        wait(panes, lambda value: len(value) == 1)
        keys(b"\x02v")
        wait(panes, lambda value: len(value) == 2)
        keys(b"\x02-")
        before = wait(panes, lambda value: len(value) == 3)
        closing = next(p["pane_id"] for p in before if p["focused"])
        keys(b"\x02x")
        surviving = wait(panes, lambda value: len(value) == 2)
        assert closing not in {p["pane_id"] for p in surviving}
        for i, pane in enumerate(surviving):
            ask("pane.rename", {"pane_id": pane["pane_id"], "label": f"fixture-{i}"})
        unresized = wait(t, lambda v: len(v["panes"]) == 2 and
                         all(p.get("label") for p in v["panes"].values()))["layout"]["Split"]["ratio"]
        assert not receipt.exists()
        keys(b"\x02rhlh\r")
        keys(b"\x02q")
        wait(tui.poll, lambda status: status is not None)
        assert tui.returncode == 0 and server.poll() is None
        assert not receipt.exists(), "TUI quit is detach, not server shutdown"
        stop(server)
        saved = snapshot.read_bytes()
        proof = json.loads(receipt.read_bytes())
        assert proof["invocation"] == invocation and proof["version"] == 1
        assert proof["snapshot"] == "session.json" and receipt.stat().st_mode & 0o777 == 0o600
        digest = hashlib.sha256(saved).hexdigest()
        assert proof["sha256"] == digest
        assert len(t()["panes"]) == 2
        resized = t()["layout"]["Split"]["ratio"]
        assert abs(resized - unresized) > .001
        print("TUI split, close and resize; detach followed by graceful server stop: passed", flush=True)

        check = {"HERDR_PROOF_RESTORE_SHA256": digest}
        for args, msg in [
            (["server"], "session snapshot does not match the required digest"),
            (["server", "--handoff-import", str(root / "absent.sock"), "fixture"], "verified restore does not support handoff import"),
        ]:
            snapshot.write_bytes(saved + b"\n")
            events = subprocess.run([binary, *args], cwd=root, env=env | check,
                                    capture_output=True, timeout=6)
            assert events.returncode != 0 and msg.encode() in events.stderr, events.stderr[-1000:]
            assert not api.exists() and not client.exists()
            assert snapshot.read_bytes() == saved + b"\n"
        print("Byte-replacement and handoff import refused; no endpoints left behind", flush=True)

        snapshot.write_bytes(saved)
        restored = spawn(["server"], check, stdout=log, stderr=log)
        seen = wait(panes, lambda value: len(value) == 2)
        assert {p.get("label") for p in seen} == {"fixture-0", "fixture-1"}
        stop(restored)
        assert abs(t()["layout"]["Split"]["ratio"] - resized) < .001
        print("Verified restart retained the resize and did not revive the closed pane", flush=True)
    except Exception:
        log.flush()
        log.seek(0)
        print(log.read()[-2500:], flush=True)
        raise
    finally:
        for proc in reversed(owned):
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
        if "master" in globals():
            os.close(master)
        log.close()
