"""Repository-owned Python checks for the opt-in advisory runner."""

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import stat
import subprocess
import sys
import time

LIMIT = 1024 * 1024
UV = ["uv", "run", "--python", "3.14", "--frozen", "--group", "test"]
INSTRUCTIONS = [
    *UV, "pytest", "tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers",
    "tests/test_opencode_control_plane.py", "tests/test_dbsctr_lifecycle.py", "-q",
]
SWIFT = [*UV, "pytest", "tests/test_herdr_launchagent.py::test_herdr_host_swift_source_compiles_with_warnings_as_errors", "-q"]
PORTABLE = ["uv", "run", "--frozen", "--no-sync", "pytest", "tests/test_continuous_validation.py", "tests/test_continuous_validation_feedback.py", "tests/test_continuous_validation_dagger.py", "tests/test_continuous_validation_identity.py", "tests/test_continuous_validation_activation.py", "tests/test_dotfiles_validation_adapter.py", "-q"]


def _identity_module():
    source = Path(__file__).resolve().parents[1] / "private_dot_config/dotfiles-ai/continuous_validation/test_identity.py"
    spec = importlib.util.spec_from_file_location("dotfiles_test_identity", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _test_files(root):
    value = subprocess.run(["git", "ls-files", "-z", "--", "tests"], cwd=root,
                           capture_output=True, timeout=10, check=True)
    return [name.decode() for name in value.stdout.split(b"\0") if name.endswith(b".py")]


def _artifacts(log_path):
    log = Path(log_path)
    path = log.with_suffix(".artifacts")
    if (not log.is_absolute() or ".." in log.parts
            or any(parent.is_symlink() for parent in (log, *log.parents))):
        raise ValueError("invalid artifact directory")
    path.mkdir(mode=0o700, exist_ok=True)
    item = path.stat()
    if not stat.S_ISDIR(item.st_mode) or item.st_uid != os.getuid() or item.st_mode & 0o077:
        raise ValueError("invalid artifact directory")
    return path


def _syntax_log(path, failures):
    payload = json.dumps({"syntax_error_paths": failures}).encode()
    if len(payload) > LIMIT:
        raise ValueError("syntax diagnostic capacity")
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        item = os.fstat(stream.fileno())
        if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid()
                or item.st_nlink != 1 or item.st_mode & 0o077):
            raise ValueError("unsafe syntax log")
        stream.truncate(0)
        stream.write(payload)


def _with_identities(value, junit, root):
    if value["status"] not in {"passed", "failed"}:
        return value
    try:
        ids, receipt = _identity_module().collect_junit(junit, _test_files(root))
        if value["status"] == "passed" and receipt["outcomes"]["failed"] + receipt["outcomes"]["error"]:
            raise ValueError("inconsistent outcome")
    except (OSError, ValueError):
        return _result(value["check_id"], "unavailable", "test_identity_evidence_unavailable",
                       runtime=value.get("runtime", {}))
    return {**value, "runtime": {**value["runtime"], "test_identity": receipt}, "test_ids": ids}


def _config(config):
    if not isinstance(config, dict) or set(config) - {"dagger", "dagger_helper_argv"}:
        raise ValueError("unknown adapter configuration")
    pins = config.get("dagger", {})
    if not isinstance(pins, dict) or set(pins) - {"engine", "image", "python_version", "uv_version", "cli", "cli_sha256"}:
        raise ValueError("unknown Dagger configuration")
    if any(not isinstance(value, str) or not value or "\0" in value or len(value) > 4096 for value in pins.values()):
        raise ValueError("invalid Dagger configuration")
    if bool(pins.get("cli")) != bool(pins.get("cli_sha256")):
        raise ValueError("explicit CLI requires its binary checksum")
    if "cli" in pins and (not Path(pins["cli"]).is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", pins["cli_sha256"])):
        raise ValueError("invalid explicit CLI identity")
    argv = config.get("dagger_helper_argv", [])
    if not isinstance(argv, list) or len(argv) > 32 or any(not isinstance(value, str) or not value or "\0" in value for value in argv):
        raise ValueError("invalid helper argv")
    return config


def _architecture():
    return {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine().lower(), platform.machine().lower())


def _lane(os_name, config):
    root = Path(__file__).resolve().parents[1]
    locks = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
             for name in ("pyproject.toml", "uv.lock") if (root / name).is_file()}
    pins = config.get("dagger", {})
    return {"os": os_name, "architecture": _architecture(),
            "python": pins.get("python_version", "3.14") if os_name == "linux" else "3.14",
            "tools": {"uv": pins.get("uv_version", "identity unresolved")}, "dependencies": locks}


def describe(config=None):
    config = _config(config or {})
    native = _lane("darwin", config)
    checks = [
        ("dotfiles.syntax", "cheap", "native", {**native, "python": platform.python_version()}, 60, {"kind": "syntax"}),
        ("dotfiles.instructions", "cheap", "native", native, 180, {"argv": INSTRUCTIONS}),
        ("dotfiles.full", "expensive", "native", native, 2700, {"argv": [*UV, "pytest", "--maxfail=1"]}),
        ("dotfiles.swift", "expensive", "native", native, 180, {"argv": SWIFT}),
        ("dotfiles.portable", "expensive", "dagger", _lane("linux", config), 600, {"argv": PORTABLE}),
    ]
    return {"schema_version": 1, "adapter_id": "dotfiles.continuous-validation",
            "input_patterns": ["**", ".github/**", ".coveragerc*", ".chezmoi*"],
            "checks": [{"id": identity, "class": kind, "backend": backend, "lane": lane,
                        "timeout_seconds": timeout, "cacheable": False, "configuration": {
                            **settings, "test_identity": "not_applicable" if identity == "dotfiles.syntax" else "pytest-junit-v1"}}
                       for identity, kind, backend, lane, timeout, settings in checks]}


def select(request):
    if (not isinstance(request, dict) or request.get("schema_version") != 1
            or set(request) - {"schema_version", "snapshot", "base", "trigger", "changed_paths", "config"}
            or request.get("trigger") not in {"edit", "checkpoint", "manual"}):
        raise ValueError("invalid selection request")
    _config(request.get("config", {}))
    checks = ["dotfiles.syntax", "dotfiles.instructions", "dotfiles.full"]
    if request["trigger"] in {"checkpoint", "manual"}:
        checks += ["dotfiles.swift", "dotfiles.portable"]
    return {"schema_version": 1, "checks": checks,
            "reason": "full_validation_at_checkpoint", "complete": request["trigger"] != "edit"}


def _result(identity, status, code=None, *, exit_code=None, runtime=None, tests=None):
    return {"schema_version": 1, "check_id": identity, "status": status, "exit_code": exit_code,
            "runtime": runtime or {}, "test_ids": tests or [], "diagnostic_codes": [code] if code else []}


def _snapshot(request):
    root = Path(request["snapshot"])
    if not root.is_absolute() or root.is_symlink() or not (root / ".git").is_dir():
        raise ValueError("immutable Git snapshot required")
    if (root / ".git/objects/info/alternates").exists():
        raise ValueError("self-contained Git required")
    result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root,
                            capture_output=True, text=True, timeout=10, check=True)
    if result.stdout.strip():
        raise ValueError("snapshot source differs from its commit")
    if not re.fullmatch(r"[0-9a-f]{40}", request["base"]):
        raise ValueError("pinned base required")
    subprocess.run(["git", "cat-file", "-e", request["base"] + "^{commit}"], cwd=root,
                   capture_output=True, timeout=10, check=True)
    return root


def _environment():
    allowed = {"PATH", "HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "UV_CACHE_DIR", "TMPDIR", "LANG", "LC_ALL", "SSL_CERT_FILE"}
    return {**{key: value for key, value in os.environ.items() if key in allowed},
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "UV_PYTHON_DOWNLOADS": "never",
            "PYTHONDONTWRITEBYTECODE": "1", "UV_NO_PROGRESS": "1"}


def _run(argv, root, log_path, timeout):
    log_path = Path(log_path)
    if not log_path.is_absolute() or log_path.is_symlink() or log_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("private external log required")
    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(log_path, os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as log:
        item = os.fstat(log.fileno())
        if not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid() or item.st_nlink != 1 or item.st_mode & 0o077:
            raise ValueError("aliased log rejected")
        log.truncate(0)
        process = subprocess.Popen(argv, cwd=root, env=_environment(), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline, size, ended = time.monotonic() + timeout, 0, None
        try:
            while selector.get_map():
                if time.monotonic() >= deadline:
                    process.kill()
                    return None, "check_timeout"
                if process.poll() is not None:
                    ended = ended or time.monotonic()
                    if time.monotonic() - ended > 1:
                        return None, "descendant_output_unclosed"
                for key, _ in selector.select(0.1):
                    block = os.read(key.fileobj.fileno(), 8192)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    remaining = LIMIT - size
                    log.write(block[:remaining])
                    size += len(block)
                    if size > LIMIT:
                        process.kill()
                        return None, "check_output_limit"
            return process.wait(timeout=max(0.1, deadline - time.monotonic())), None
        finally:
            selector.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            process.stdout.close()


def _syntax(root):
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, timeout=10, check=True)
    failed = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode()
        path = root / relative
        if not path.is_file() or path.suffix == ".tmpl" or relative.startswith(("tests/fixtures/", "docs/")):
            continue
        body = path.read_bytes()
        if path.suffix != ".py" and not (body.startswith(b"#!") and b"python" in body.split(b"\n", 1)[0]):
            continue
        try:
            ast.parse(body, filename=relative, feature_version=(3, 12))
        except (SyntaxError, ValueError, UnicodeError):
            failed.append(relative)
    return failed


def execute(request):
    identity = request.get("check", {}).get("id", "invalid") if isinstance(request, dict) else "invalid"
    try:
        if (not isinstance(request, dict) or request.get("schema_version") != 1
                or set(request) - {"schema_version", "snapshot", "base", "trigger", "check", "log_path", "config"}
                or request.get("trigger") not in {"edit", "checkpoint", "manual"}):
            raise ValueError("invalid execution request")
        config = _config(request.get("config", {}))
        check = next((item for item in describe(config)["checks"] if item["id"] == identity), None)
        if check is None or request.get("check") != check:
            raise ValueError("descriptor changed")
        if check["class"] == "expensive" and request["trigger"] == "edit":
            return _result(identity, "unavailable", "checkpoint_required")
        if check["backend"] == "dagger":
            pins, helper = config.get("dagger", {}), config.get("dagger_helper_argv", [])
            if not {"engine", "image", "python_version", "uv_version"} <= pins.keys() or not helper:
                return _result(identity, "unavailable", "dagger_runtime_unconfigured")
            root = _snapshot(request)
            artifacts = _artifacts(request["log_path"])
            payload = {**request, "log_path": str(artifacts / "dagger.log"), "check": {**check, "configuration": {
                **pins, "platform": "linux/" + check["lane"]["architecture"],
                "argv": [*PORTABLE, "--junitxml=.ci-select/junit.xml"], "groups": ["test"], "project_path": ".",
                "artifacts": [".ci-select/junit.xml"],
            }}}
            process = subprocess.run([*helper, "--enabled"], input=json.dumps(payload), capture_output=True,
                                     text=True, timeout=check["timeout_seconds"])
            if len(process.stdout) > LIMIT:
                return _result(identity, "unavailable", "dagger_helper_output_invalid")
            value = json.loads(process.stdout)
            if value.get("schema_version") != 1 or value.get("check_id") != identity or value.get("status") not in {"passed", "failed", "unavailable", "interrupted"}:
                raise ValueError("invalid helper result")
            return _with_identities(value, artifacts / ".ci-select/junit.xml", root)
        if platform.system() != "Darwin":
            return _result(identity, "unavailable", "native_macos_required")
        root = _snapshot(request)
        runtime = {"os": "darwin", "architecture": _architecture(), "python": platform.python_version(), "tools": {}}
        if identity == "dotfiles.syntax":
            failures = _syntax(root)
            _artifacts(request["log_path"])
            _syntax_log(request["log_path"], failures)
            runtime["test_identity"] = _identity_module().not_applicable()
            return _result(identity, "failed" if failures else "passed", "python_syntax_error" if failures else None,
                           exit_code=1 if failures else 0, runtime=runtime)
        if not shutil.which("uv") or not shutil.which("python3.14"):
            return _result(identity, "unavailable", "native_python_toolchain_unavailable")
        artifacts = _artifacts(request["log_path"])
        junit = artifacts / "junit.xml"
        code, error = _run([*check["configuration"]["argv"], "--junitxml=" + str(junit)],
                           root, request["log_path"], check["timeout_seconds"])
        interpreter = root / ".venv/bin/python"
        if interpreter.is_file():
            probe = subprocess.run([str(interpreter), "-c", "import platform; print(platform.python_version())"],
                                   cwd=root, env=_environment(), capture_output=True, text=True, timeout=5)
            if probe.returncode == 0 and re.fullmatch(r"3\.14\.[0-9]+", probe.stdout.strip()):
                runtime["python"] = probe.stdout.strip()
            elif not error:
                return _result(identity, "unavailable", "native_python_runtime_mismatch", runtime=runtime)
        if error:
            return _result(identity, "unavailable", error, runtime=runtime)
        if code < 0:
            return _result(identity, "unavailable", "native_process_crashed", exit_code=128-code, runtime=runtime)
        return _with_identities(_result(identity, "passed" if code == 0 else "failed", "pytest_failed" if code else None,
                                       exit_code=code, runtime=runtime), junit, root)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, json.JSONDecodeError, TypeError):
        return _result(identity, "unavailable", "adapter_execution_unavailable")


def main():
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in {"describe", "select", "execute"}:
            raise ValueError("action required")
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("input limit")
        request = json.loads(raw)
        if sys.argv[1] == "describe":
            if not isinstance(request, dict) or set(request) - {"schema_version", "config"} or request.get("schema_version") != 1:
                raise ValueError("invalid describe request")
            value = describe(request.get("config", {}))
        else:
            value = globals()[sys.argv[1]](request)
        print(json.dumps(value, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError):
        print(json.dumps({"schema_version": 1, "error": "adapter_protocol_invalid"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
