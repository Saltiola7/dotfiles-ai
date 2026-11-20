"""Prove the existing shared service, then exec one authenticated client."""
import fcntl
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit


def admit(deadline: float) -> int:
    root = "/run/user/" + str(os.getuid())
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(directory)
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise ValueError("unsafe TUI admission directory")
        fd = os.open("dotfiles-ai-herdr-start.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                     0o600, dir_fd=directory)
    finally:
        os.close(directory)
    try:
        metadata = os.fstat(fd)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_mode & 0o077 or metadata.st_nlink != 1 or metadata.st_size > 64):
            raise ValueError("unsafe TUI admission record")
        while time.monotonic() < deadline:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                time.sleep(0.2)
                continue
            prior = os.pread(fd, 64, 0)
            now = time.monotonic()
            stamp = float(prior) if prior else 0
            if not math.isfinite(stamp) or not 0 <= stamp <= now:
                raise ValueError("invalid TUI admission timestamp")
            delay = stamp + 2.5 - now
            if delay > 0:
                fcntl.flock(fd, fcntl.LOCK_UN)
                time.sleep(delay)
                continue
            return fd  # Closed by exec; not inherited by the native client.
        raise TimeoutError("TUI admission expired")
    except BaseException:
        os.close(fd)
        raise


def main() -> int:
    target = sys.argv[1]
    environment = os.environ.copy()
    pace = environment.get("DOTFILES_AI_HERDR_PACE") == "1" and sys.platform == "linux"
    deadline = time.monotonic() + 280

    def read(*args: str) -> str:
        return subprocess.check_output([target, *args], env=environment, text=True,
                                       stderr=subprocess.DEVNULL,
                                       timeout=min(10, max(0.001, deadline - time.monotonic()))).strip()

    admission = None
    try:
        admission = admit(deadline) if pace else None
        server = read("service", "status")
        url = urlsplit(server)
        if url.scheme not in {"http", "https"} or url.hostname not in {"127.0.0.1", "localhost", "::1"} or not url.port:
            raise ValueError("shared service unavailable")
        registration = Path(read("debug", "paths", "state")) / "service.json"
        with os.fdopen(os.open(registration, os.O_RDONLY | os.O_NOFOLLOW)) as stream:
            metadata = os.fstat(stream.fileno())
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or metadata.st_mode & 0o077 or metadata.st_size > 65536):
                raise ValueError("unsafe native service registration")
            service = json.load(stream)
        if (service.get("url") != server or type(service.get("pid")) is not int
                or not isinstance(service.get("password"), str) or not service["password"]):
            raise ValueError("invalid native service registration")
        # Keep credentials in the child environment, never argv or output.
        environment["OPENCODE_PASSWORD"] = service["password"]
        info = json.loads(read("api", "--server", server, "get", "/api/info"))
        version = read("--version").removeprefix("opencode v")
        if info.get("version") != version or info.get("pid") != service["pid"]:
            raise ValueError("shared service version mismatch")
        arguments = sys.argv[3:]
        index = int(sys.argv[2])
        arguments[index:index] = ["--server", server]
        if admission is not None:
            if time.monotonic() >= deadline:
                raise TimeoutError("TUI admission expired")
            stamp = str(time.monotonic()).encode("ascii")
            os.ftruncate(admission, 0)
            os.pwrite(admission, stamp, 0)
        # An explicit authenticated endpoint cannot replace the shared service.
        os.execvpe(target, [target, *arguments], environment)
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        print("OpenCode start blocked: shared service unavailable or version mismatch; "
              "use a coordinated opencode service start/restart, or explicit --standalone/--server.",
              file=sys.stderr)
        return 75
    finally:
        if admission is not None:
            os.close(admission)


if __name__ == "__main__":
    sys.exit(main())
