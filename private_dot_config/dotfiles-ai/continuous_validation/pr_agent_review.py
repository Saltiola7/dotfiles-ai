"""Controller-owned preparation for explicitly enabled private PR-Agent reviews.

Repository adapters receive neither provider settings nor credentials. This
module prepares one captured patch and validates one private review; it does
not install software, start an engine, authenticate, or accept gate evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import subprocess
import tempfile
import time

CHECK_ID = "pr-agent-review"
STRATEGY = "pr-agent-review-v1"
RELEASE = "0.49.0"
SOURCE_COMMIT = "efdde4afe14aa401a3889012c7f3e9ef3081a430"
IMAGE = "pragent/pr-agent:0.49.0@sha256:10a8893d5e081be1a5ae825843d9fc14f8e8d59d8a4f61d67c1775415156079f"
PLATFORM_IMAGES = {
    "linux/arm64": "sha256:72bf20078583aadb63f4cdb6cf350668d6f622a79ed00cba2d30643ec802d4a4",
    "linux/amd64": "sha256:e47e1108778407cd85882cd035f9217f69daae08c8a826617ccb2eb2373b4071",
}
MAX_FILES = 32
MAX_PATCH = 256 * 1024
MAX_ARTIFACT = 1024 * 1024
MAX_CONFIG = 64 * 1024
TIMEOUT = 300
_CONFIG_FIELDS = {"schema_version", "provider", "model", "project", "location", "adc_file",
                  "source_patterns", "real_inference_enabled", "dagger"}
_DAGGER_FIELDS = {"platform", "engine", "cli", "cli_sha256", "sdk_python"}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _fail(code="pr_agent_configuration_invalid"):
    raise ValueError(code)


def _text(value, maximum=4096):
    return (isinstance(value, str) and 0 < len(value) <= maximum
            and all(ord(char) >= 32 and ord(char) != 127 for char in value))


def _absolute(value):
    return _text(value) and Path(value).is_absolute() and ".." not in Path(value).parts


def _relative(value):
    if not _text(value) or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and path.as_posix() == value and not any(part in {"", ".", ".."} for part in path.parts)


def _unique(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            _fail("pr_agent_artifact_invalid")
        result[name] = value
    return result


def _read_private(path, limit, code):
    from . import runner
    try:
        path = runner.no_alias(Path(path))
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            item = os.fstat(stream.fileno())
            if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid() or item.st_nlink != 1
                    or item.st_mode & 0o077 or item.st_size > limit):
                _fail(code)
            data = stream.read(limit + 1)
        if len(data) > limit:
            _fail(code)
        return data
    except (OSError, runner.ValidationError):
        _fail(code)


def validate_config(value):
    """Validate private configuration without reading credentials or probing tools."""
    from .dagger_backend import _local_engine
    if not isinstance(value, dict) or set(value) != _CONFIG_FIELDS:
        _fail()
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["provider"] != "vertex" or type(value["real_inference_enabled"]) is not bool
            or not isinstance(value["model"], str)
            or re.fullmatch(r"vertex_ai/(?:claude|gemini)-[A-Za-z0-9._@-]{1,160}", value["model"]) is None
            or not isinstance(value["project"], str)
            or re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", value["project"]) is None
            or not isinstance(value["location"], str)
            or re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value["location"]) is None
            or not _absolute(value["adc_file"])):
        _fail()
    patterns = value["source_patterns"]
    if (not isinstance(patterns, list) or not 1 <= len(patterns) <= 32
            or any(not _relative(item) or item.startswith("!") for item in patterns)
            or len(set(patterns)) != len(patterns)):
        _fail()
    config = value["dagger"]
    if (not isinstance(config, dict) or set(config) != _DAGGER_FIELDS
            or not isinstance(config["platform"], str) or config["platform"] not in PLATFORM_IMAGES
            or not _local_engine(config["engine"])
            or not _absolute(config["cli"]) or not _absolute(config["sdk_python"])
            or not isinstance(config["cli_sha256"], str) or _HEX.fullmatch(config["cli_sha256"]) is None):
        _fail()
    try:
        encoded = _canonical(value)
    except (ValueError, TypeError):
        _fail()
    if len(encoded) > MAX_CONFIG:
        _fail()
    return json.loads(encoded)


def load_config(path):
    """Read only the explicitly selected private controller configuration."""
    from . import runner
    try:
        runner.outside_git(Path(path).parent)
        value = json.loads(_read_private(path, MAX_CONFIG, "pr_agent_configuration_invalid"), object_pairs_hook=_unique)
        return validate_config(value)
    except (OSError, ValueError, runner.ValidationError, UnicodeError):
        _fail()


def descriptor(config):
    config = validate_config(config)
    platform = config["dagger"]["platform"]
    wrappers = {}
    for name in ("pr_agent_review.py", "pr_agent_backend.py", "pr_agent_worker.py"):
        path = Path(__file__).with_name(name)
        try:
            item = path.lstat()
            if not stat.S_ISREG(item.st_mode) or item.st_size > MAX_ARTIFACT:
                _fail("pr_agent_wrapper_unavailable")
            wrappers[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            _fail("pr_agent_wrapper_unavailable")
    return {"id": CHECK_ID, "class": "expensive", "backend": "dagger", "timeout_seconds": TIMEOUT,
            "cacheable": False,
            "lane": {"os": "linux", "architecture": platform.split("/")[1], "python": "3.14.9",
                     "tools": {"dagger": "0.21.10", "pr-agent-release": RELEASE},
                     "dependencies": {"image": PLATFORM_IMAGES[platform], "source": SOURCE_COMMIT,
                                      "wrappers": wrappers}},
            "configuration": {"strategy": STRATEGY, "test_identity": "not_applicable",
                              "config_digest": hashlib.sha256(_canonical(config)).hexdigest()}}


def _environment(home=None):
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    if home is not None:
        environment.update({"HOME": str(home), "XDG_CONFIG_HOME": str(home / "config"),
                            "XDG_DATA_HOME": str(home / "data"), "XDG_CACHE_HOME": str(home / "cache"),
                            "PYTHONPATH": str(Path(__file__).resolve().parent.parent)})
    return environment


def _capture(argv, payload, cwd, *, timeout, limit, cancel, environment, code, descendants=True,
             accepted_returncodes=(0,), completed=False):
    """Bound a trusted subprocess and retain uncertain descendant termination."""
    from . import runner
    child = None
    selector = selectors.DefaultSelector()
    output = bytearray()
    stderr_count = 0
    start = time.monotonic()
    try:
        child = subprocess.Popen(argv, cwd=cwd, env=environment, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            os.setpriority(os.PRIO_PROCESS, child.pid, 10)
        except (AttributeError, OSError):
            pass
        pending = payload or b""
        position = 0
        os.set_blocking(child.stdin.fileno(), False)
        selector.register(child.stdin, selectors.EVENT_WRITE, "input")
        selector.register(child.stdout, selectors.EVENT_READ, "output")
        selector.register(child.stderr, selectors.EVENT_READ, "error")
        while selector.get_map() or child.poll() is None:
            if cancel():
                raise runner.Interrupted("superseded")
            if time.monotonic() - start >= timeout:
                raise runner.Interrupted("pr_agent_execution_timeout")
            for key, _ in selector.select(0.1):
                if key.data == "input":
                    try:
                        position += os.write(key.fileobj.fileno(), pending[position:position + 65536])
                    except BrokenPipeError:
                        position = len(pending)
                    if position == len(pending):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                else:
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                    elif key.data == "output":
                        output.extend(data)
                        if len(output) > limit:
                            _fail(code)
                    else:
                        stderr_count += len(data)
                        if stderr_count > 256 * 1024:
                            _fail(code)
            if child.poll() is not None and not selector.get_map():
                break
        if child.returncode not in accepted_returncodes:
            _fail(code)
        if completed:
            return subprocess.CompletedProcess(argv, child.returncode, bytes(output))
        return bytes(output)
    except OSError:
        _fail(code)
    finally:
        selector.close()
        if child is not None:
            uncertain = False
            for sig, wait in ((signal.SIGTERM, 0.5), (signal.SIGKILL, 2)):
                try:
                    if descendants:
                        os.killpg(child.pid, sig)
                    elif child.poll() is None:
                        # These Git commands cannot execute external helpers:
                        # selected history, diff and attributes come from the
                        # filtered capture, with textconv/ext-diff disabled.
                        child.send_signal(sig)
                except ProcessLookupError:
                    pass
                except OSError:
                    uncertain = True
                try:
                    child.wait(timeout=wait)
                except subprocess.TimeoutExpired:
                    if sig == signal.SIGKILL:
                        uncertain = True
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream and not stream.closed:
                    stream.close()
            if uncertain:
                raise runner.UncertainTermination("termination_unconfirmed")


def _git(root, args, limit, code):
    return _capture(["git", "--literal-pathspecs", "-C", str(root), *args], None, root, timeout=30, limit=limit,
                    cancel=lambda: False, environment=_environment(), code=code, descendants=False)


def build_patch(snapshot, config, destination):
    """Build a patch solely from filtered immutable snapshot Git objects."""
    from . import runner
    config = validate_config(config)
    if (not isinstance(snapshot, dict) or not isinstance(snapshot.get("id"), str)
            or _HEX.fullmatch(snapshot["id"]) is None
            or any(not isinstance(snapshot.get(name), str) or _OBJECT.fullmatch(snapshot[name]) is None
                   for name in ("base", "commit")) or not isinstance(snapshot.get("files"), dict)):
        _fail("pr_agent_snapshot_invalid")
    try:
        root = runner.no_alias(Path(snapshot["path"]))
        if not root.is_dir() or not (root / ".git").is_dir():
            _fail("pr_agent_snapshot_invalid")
        head = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"], 256, "pr_agent_snapshot_invalid").decode().strip()
        if head != snapshot["commit"] or runner.inventory(root, ["**"]) != snapshot["files"]:
            _fail("pr_agent_snapshot_invalid")
        if (_git(root, ["rev-parse", "--verify", "refs/heads/base^{commit}"], 256,
                 "pr_agent_snapshot_invalid").decode().strip() != snapshot["base"]
                or _git(root, ["diff", "--no-ext-diff", "--no-textconv", "--name-only", snapshot["commit"], "--"],
                        256 * 1024, "pr_agent_snapshot_invalid")):
            _fail("pr_agent_snapshot_invalid")
        raw = _git(root, ["diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--name-only", "-z",
                          snapshot["base"], snapshot["commit"], "--"], 256 * 1024, "pr_agent_snapshot_invalid")
        paths = [item.decode("utf-8") for item in raw.split(b"\0") if item]
        if any(not _relative(name) or not runner.selected_name(name, ["**"]) for name in paths):
            _fail("pr_agent_snapshot_invalid")
        if not paths:
            _fail("pr_agent_empty_diff")
        if len(paths) > MAX_FILES:
            _fail("pr_agent_patch_limit")
        if any(not runner.matches(name, config["source_patterns"]) for name in paths):
            _fail("pr_agent_source_scope_denied")
        for revision in (snapshot["base"], snapshot["commit"]):
            tree = _git(root, ["ls-tree", "-r", "-z", revision, "--", *paths],
                        256 * 1024, "pr_agent_snapshot_invalid")
            for entry in tree.split(b"\0"):
                if entry:
                    header, _ = entry.split(b"\t", 1)
                    mode, kind, _ = header.split()
                    if mode not in {b"100644", b"100755"} or kind != b"blob":
                        _fail("pr_agent_source_kind_unsupported")
        counts = _git(root, ["diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--numstat", "-z",
                             snapshot["base"], snapshot["commit"], "--", *paths], 256 * 1024, "pr_agent_snapshot_invalid")
        if any(line.split(b"\t", 2)[:2] == [b"-", b"-"] for line in counts.split(b"\0") if line):
            _fail("pr_agent_binary_input")
        patch = _git(root, ["diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--full-index", "--no-color",
                            "--src-prefix=a/", "--dst-prefix=b/", snapshot["base"], snapshot["commit"], "--", *paths],
                     MAX_PATCH, "pr_agent_patch_limit")
        if len(patch) > MAX_PATCH or not patch:
            _fail("pr_agent_patch_limit")
        patch.decode("utf-8")
        destination = runner.no_alias(Path(destination))
        runner.private_dir(destination.parent)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(patch)
        return {"patch_sha256": hashlib.sha256(patch).hexdigest(), "paths": paths,
                "snapshot_id": snapshot["id"], "original_base": snapshot.get("original_base", snapshot["base"])}
    except runner.UncertainTermination:
        raise
    except (OSError, UnicodeError, KeyError, runner.ValidationError):
        _fail("pr_agent_snapshot_invalid")


def validate_artifacts(log_path, paths):
    """Bind new review evidence; legacy artifact lists are not digest authority."""
    folder = Path(log_path).with_suffix(".artifacts")
    try:
        markdown = _read_private(folder / "review.md", MAX_ARTIFACT, "pr_agent_artifact_invalid")
        if not markdown.strip():
            _fail("pr_agent_artifact_invalid")
        markdown.decode("utf-8")
        data = json.loads(_read_private(folder / "review.json", MAX_ARTIFACT, "pr_agent_artifact_invalid"),
                          object_pairs_hook=_unique, parse_constant=lambda _: _fail("pr_agent_artifact_invalid"))
        if (not isinstance(data, dict) or set(data) != {"review", "usage", "coverage"}
                or not isinstance(data["review"], dict) or not data["review"] or not isinstance(data["usage"], dict)):
            _fail("pr_agent_artifact_invalid")
        usage = data["usage"]
        if usage and (set(usage) != {"prompt_tokens", "completion_tokens", "total_tokens"}
                      or any(type(n) is not int or n < 0 for n in usage.values())
                      or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]):
            _fail("pr_agent_artifact_invalid")
        coverage = data["coverage"]
        if not isinstance(coverage, dict) or set(coverage) != {"files_not_reviewed", "files_partially_reviewed"}:
            _fail("pr_agent_artifact_invalid")
        selected = set(paths)
        for values in coverage.values():
            if (not isinstance(values, list) or len(values) > MAX_FILES or any(not _relative(name) for name in values)
                    or len(set(values)) != len(values) or not set(values) <= selected):
                _fail("pr_agent_artifact_invalid")
        if set(coverage["files_not_reviewed"]) & set(coverage["files_partially_reviewed"]):
            _fail("pr_agent_artifact_invalid")
        return {"schema_version": 1, "kind": "pr-agent-review", "event": "review_completed",
                "coverage_disposition": "partial" if any(coverage.values()) else "complete",
                "artifact_locator": str(folder / "review.md"), "artifact_sha256": hashlib.sha256(markdown).hexdigest()}
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, TypeError):
        _fail("pr_agent_artifact_invalid")


def _result(code, status="unavailable", *, runtime=None, exit_code=None):
    return {"schema_version": 1, "check_id": CHECK_ID, "status": status, "exit_code": exit_code,
            "runtime": runtime or {}, "test_ids": [], "diagnostic_codes": [code] if code else []}


def _backend(request, config, log_path, cancel, timeout):
    from . import runner
    if config.get("real_inference_enabled") is not True:
        _fail("pr_agent_inference_not_activated")
    executable = Path(config["dagger"]["sdk_python"])
    if not executable.is_file() or not os.access(executable, os.X_OK):
        _fail("pr_agent_sdk_unavailable")
    runner.outside_git(executable.parent)
    with tempfile.TemporaryDirectory(prefix="pr-agent-runtime-", dir=log_path.parent) as directory:
        home = Path(directory)
        home.chmod(0o700)
        completed = _capture([str(executable), "-m", "continuous_validation.pr_agent_backend", "--enabled"],
                       _canonical(request), home,
                       timeout=timeout, limit=MAX_ARTIFACT, cancel=cancel, environment=_environment(home),
                       code="pr_agent_backend_unavailable", accepted_returncodes=(0, 2), completed=True)
    try:
        result = json.loads(completed.stdout, object_pairs_hook=_unique,
                            parse_constant=lambda _: _fail("pr_agent_backend_invalid"))
        fields = {"schema_version", "check_id", "status", "exit_code", "runtime", "test_ids", "diagnostic_codes"}
        if (not isinstance(result, dict) or set(result) != fields
                or type(result["schema_version"]) is not int or result["schema_version"] != 1
                or result["check_id"] != CHECK_ID or result["status"] not in {"passed", "failed", "unavailable", "interrupted"}
                or type(completed.returncode) is not int or completed.returncode not in {0, 2}
                or (completed.returncode == 0) != (result["status"] == "passed")
                or result["status"] == "passed" and (type(result["exit_code"]) is not int or result["exit_code"] != 0)):
            _fail("pr_agent_backend_invalid")
        return result
    except (ValueError, TypeError, AttributeError, RecursionError, UnicodeError):
        _fail("pr_agent_backend_invalid")


def execute(enrollment, snapshot, log_path, cancel=None):
    """Execute only explicit real-review activation under the caller's admission."""
    from . import runner, test_identity
    if enrollment.get("enabled") is not True or enrollment.get("reviews_enabled") is not True:
        return _result("pr_agent_review_disabled")
    try:
        config = validate_config(enrollment.get("review_config"))
        if config["real_inference_enabled"] is not True:
            return _result("pr_agent_inference_not_activated")
        cancel = cancel or (lambda: False)
        if cancel():
            raise runner.Interrupted("superseded")
        started = time.monotonic()
        log_path = runner.no_alias(Path(log_path))
        runner.private_dir(log_path.parent)
        inputs = runner.private_dir(log_path.with_suffix(".inputs"))
        patch = inputs / "changes.diff"
        prepared = build_patch(snapshot, config, patch)
        result = _backend({"schema_version": 1, "check": descriptor(config), "log_path": str(log_path),
                           "patch_path": str(patch), "config": config}, config, log_path, cancel,
                          max(0.001, TIMEOUT - (time.monotonic() - started)))
        if (not isinstance(result, dict) or set(result) != {"schema_version", "check_id", "status", "exit_code", "runtime", "test_ids", "diagnostic_codes"}
                or type(result["schema_version"]) is not int or result["schema_version"] != 1
                or result["check_id"] != CHECK_ID or result["status"] not in {"passed", "failed", "unavailable", "interrupted"}
                or not isinstance(result["runtime"], dict) or result["test_ids"] != []
                or not isinstance(result["diagnostic_codes"], list) or len(result["diagnostic_codes"]) > 16
                or any(not isinstance(c, str) or re.fullmatch(r"(?:pr_agent|dagger)_[a-z0-9_]{1,110}|shadow_disabled", c) is None
                       for c in result["diagnostic_codes"])
                or result["exit_code"] is not None and (type(result["exit_code"]) is not int or not 0 <= result["exit_code"] <= 255)):
            _fail("pr_agent_backend_invalid")
        if result["status"] == "passed":
            if result["exit_code"] != 0 or result["runtime"].get("artifacts") != ["review.md", "review.json"]:
                _fail("pr_agent_backend_invalid")
            result["runtime"]["advisory_review"] = validate_artifacts(log_path, prepared["paths"])
            result["runtime"]["test_identity"] = test_identity.not_applicable()
        else:
            result["runtime"].pop("advisory_review", None)
        result["runtime"]["patch_sha256"] = prepared["patch_sha256"]
        result["runtime"]["review_config_digest"] = hashlib.sha256(_canonical(config)).hexdigest()
        return result
    except (runner.Interrupted, runner.UncertainTermination):
        raise
    except runner.ValidationError as error:
        return _result(str(error) if re.fullmatch(r"pr_agent_[a-z0-9_]+", str(error)) else "pr_agent_input_unavailable")
    except ValueError as error:
        code = str(error)
        return _result(code if re.fullmatch(r"pr_agent_[a-z0-9_]+", code) else "pr_agent_input_unavailable")
    except OSError:
        return _result("pr_agent_input_unavailable")
