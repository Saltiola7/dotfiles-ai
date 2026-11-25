"""Repository-owned Python checks for the opt-in advisory runner."""

import argparse
import ast
import fnmatch
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
ROOT = Path(__file__).resolve().parents[1]
UV = ["uv", "run", "--python", "3.14", "--frozen", "--group", "test"]
INSTRUCTIONS = [
    *UV, "pytest", "tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers",
    "tests/test_opencode_control_plane.py", "tests/test_dbsctr_lifecycle.py", "-q",
]
PORTABLE = ["uv", "run", "--frozen", "--no-sync", "pytest", "tests/test_continuous_validation.py", "tests/test_continuous_validation_feedback.py", "tests/test_continuous_validation_dagger.py", "tests/test_continuous_validation_identity.py", "tests/test_continuous_validation_activation.py", "tests/test_dotfiles_validation_adapter.py", "-q"]
ADAPTER_TESTS = [*UV, "pytest", "tests/test_continuous_validation_dotfiles_adapter.py", "tests/test_dotfiles_validation_adapter.py", "-q"]
LIFECYCLE_TESTS = [*UV, "pytest", "tests/test_dbsctrctl.py", "tests/test_evidence_reuse.py", "-q"]
TRIGGERS = ("edit", "affected", "checkpoint", "manual")
BASES = ("affected", "broad", "full")
OWNERSHIP = "validation-ownership.json"
OWNERSHIP_DIGEST = "63c40ce2111c918b873dfde1f8edd2f8fcfa3cc92f440e310fa35e19268d8e07"
OWNERSHIP_FIELDS = {"schema_version", "components", "dependencies", "broad_check_ids"}
# Changed paths that select the broad set even when a later table maps them.
ALWAYS_BROAD = (".github/workflows/**", ".github/actions/**", "uv.lock", "pyproject.toml",
                "private_dot_config/dotfiles-ai/continuous_validation/dagger_runtime/pyproject.toml",
                "private_dot_config/dotfiles-ai/continuous_validation/dagger_runtime/uv.lock",
                "tests/ci_shard.py", "tests/fixtures/**", "tests/benchmarks/**")
MAX_PATHS = 16384


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


def _lane(python, config):
    root = Path(__file__).resolve().parents[1]
    locks = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
             for name in ("pyproject.toml", "uv.lock") if (root / name).is_file()}
    pins = config.get("dagger", {})
    return {"os": "linux", "architecture": _architecture(), "python": python,
            "tools": {"uv": pins.get("uv_version", "identity unresolved")}, "dependencies": locks}


def describe(config=None):
    config = _config(config or {})
    pins = config.get("dagger", {})
    native = _lane("3.14", config)
    checks = [
        ("dotfiles.syntax", "cheap", "native", {**native, "python": platform.python_version()}, 60, {"kind": "syntax"}),
        ("dotfiles.instructions", "cheap", "native", native, 180, {"argv": INSTRUCTIONS}),
        ("dotfiles.adapter", "cheap", "native", native, 600, {"argv": ADAPTER_TESTS}),
        ("dotfiles.lifecycle", "cheap", "native", native, 600, {"argv": LIFECYCLE_TESTS}),
        ("dotfiles.full", "expensive", "native", native, 2700, {"argv": [*UV, "pytest", "--maxfail=1"]}),
        ("dotfiles.portable", "expensive", "dagger", _lane(pins.get("python_version", "3.14"), config), 600, {"argv": PORTABLE}),
    ]
    return {"schema_version": 1, "adapter_id": "dotfiles.continuous-validation",
            "input_patterns": ["**", ".github/**", ".coveragerc*", ".chezmoi*"],
            "checks": [{"id": identity, "class": kind, "backend": backend, "lane": lane,
                        "timeout_seconds": timeout, "cacheable": False, "configuration": {
                            **settings, "test_identity": "not_applicable" if identity == "dotfiles.syntax" else "pytest-junit-v1"}}
                       for identity, kind, backend, lane, timeout, settings in checks]}


def _text(value, maximum=512):
    if (not isinstance(value, str) or not 1 <= len(value.encode()) <= maximum
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError("invalid_ownership_table")
    return value


def _pattern(value):
    """One owned-path pattern, with the rules of the lifecycle's CI-mapping reader."""
    parts = _text(value).split("/")
    if (any(part in ("", ".", "..", ".dbsctr") for part in parts)
            or any(character in value for character in "\\!{}[]")
            or any("**" in part and part != "**" for part in parts)):
        raise ValueError("invalid_ownership_table")
    return value


def _changed_paths(value):
    """Relative changed paths; pattern characters are never accepted as paths."""
    def valid(item):
        return (isinstance(item, str) and 0 < len(item.encode()) <= 512
                and not any(ord(character) < 32 or ord(character) == 127 for character in item)
                and not any(part in ("", ".", "..") for part in item.split("/"))
                and not any(character in item for character in "\\!{}[]*?"))
    if (not isinstance(value, list) or len(value) > MAX_PATHS or not all(valid(item) for item in value)
            or len(set(value)) != len(value)):
        raise ValueError("invalid_changed_paths")
    return value


def _matches(pattern, path):
    """Segment rules of the lifecycle's affected-CI reader; `**` spans directories."""
    pieces = path.split("/")
    positions = {0}
    for segment in pattern.split("/"):
        if segment == "**":
            positions = set(range(min(positions), len(pieces) + 1)) if positions else set()
        else:
            positions = {index + 1 for index in positions
                         if index < len(pieces) and fnmatch.fnmatchcase(pieces[index], segment)}
    return len(pieces) in positions


def _ownership():
    """The repository's one ownership table, bound to this adapter through its digest."""
    raw = Path(__file__).resolve().with_name(OWNERSHIP).read_bytes()
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != OWNERSHIP_DIGEST:
        raise ValueError("ownership_table_changed")
    table = json.loads(raw)
    known = {check["id"] for check in describe()["checks"]}
    try:
        components, edges = table["components"], table["dependencies"]
        identifiers = [component["id"] for component in components]
        valid = (set(table) == OWNERSHIP_FIELDS and table["schema_version"] == 1
                 and isinstance(components, list) and 1 <= len(components) <= 1024
                 and isinstance(edges, list) and len(set(identifiers)) == len(identifiers)
                 and set(table["broad_check_ids"]) <= set(known)
                 and all(set(component) == {"id", "owned_path_patterns", "check_ids"}
                         and component["id"] == _text(component["id"])
                         and len({(_pattern(pattern)) for pattern in component["owned_path_patterns"]})
                         == len(component["owned_path_patterns"]) and component["owned_path_patterns"]
                         and set(component["check_ids"]) <= set(known) for component in components)
                 and all(set(edge) == {"consumer", "dependency"} and edge["consumer"] in identifiers
                         and edge["dependency"] in identifiers for edge in edges))
    except (KeyError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise ValueError("invalid_ownership_table")
    return table


def selection(trigger, changed_paths):
    """One selection function of the trigger, the changed paths and the ownership table."""
    if not isinstance(trigger, str) or trigger not in TRIGGERS:
        raise ValueError("invalid_trigger")
    changed = _changed_paths(changed_paths)
    order = [check["id"] for check in describe()["checks"]]
    if trigger in {"checkpoint", "manual"}:
        return {"checks": order, "basis": "full", "complete": True}
    table = _ownership()
    owned, broad = set(), False
    for path in changed:
        owners = {component["id"] for component in table["components"]
                  if any(_matches(pattern, path) for pattern in component["owned_path_patterns"])}
        broad = broad or not owners or any(_matches(pattern, path) for pattern in ALWAYS_BROAD)
        owned |= owners
    consumers = {}
    for edge in table["dependencies"]:
        consumers.setdefault(edge["dependency"], set()).add(edge["consumer"])
    pending = list(owned)
    while pending:
        for consumer in consumers.get(pending.pop(), ()):
            if consumer not in owned:
                owned.add(consumer)
                pending.append(consumer)
    chosen = (set(table["broad_check_ids"]) if broad
              else {check for component in table["components"] if component["id"] in owned for check in component["check_ids"]})
    return {"checks": [check for check in order if check in chosen], "basis": "broad" if broad else "affected", "complete": False}


def select(request):
    if (not isinstance(request, dict) or request.get("schema_version") != 1
            or set(request) - {"schema_version", "snapshot", "base", "trigger", "changed_paths", "config"}
            or not isinstance(request.get("trigger"), str) or request["trigger"] not in TRIGGERS):
        raise ValueError("invalid selection request")
    _config(request.get("config", {}))
    chosen = selection(request["trigger"], request.get("changed_paths", []))
    reason = ("full_validation_at_checkpoint" if chosen["basis"] == "full"
              else "broad_fallback_for_unowned_change" if chosen["basis"] == "broad"
              else "affected_by_changed_paths")
    return {"schema_version": 1, **chosen, "reason": reason}


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


def _changed(root, base):
    """Changed paths of the mapped-base diff, exactly as the runner derives them."""
    result = subprocess.run(["git", "diff", "--name-only", "-z", base + "...HEAD"], cwd=root,
                            capture_output=True, timeout=30, check=True)
    return [name.decode() for name in result.stdout.split(b"\0") if name]


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


def _native(check, root, log_path):
    """Run one Linux-native check where the host provides its declared lane."""
    identity = check["id"]
    if platform.system().lower() != check["lane"]["os"]:
        return _result(identity, "unavailable", "native_lane_unavailable")
    runtime = {"os": check["lane"]["os"], "architecture": _architecture(), "python": platform.python_version(), "tools": {}}
    if identity == "dotfiles.syntax":
        failures = _syntax(root)
        _artifacts(log_path)
        _syntax_log(log_path, failures)
        runtime["test_identity"] = _identity_module().not_applicable()
        return _result(identity, "failed" if failures else "passed", "python_syntax_error" if failures else None,
                       exit_code=1 if failures else 0, runtime=runtime)
    if not shutil.which("uv") or not shutil.which("python3.14"):
        return _result(identity, "unavailable", "native_python_toolchain_unavailable")
    artifacts = _artifacts(log_path)
    junit = artifacts / "junit.xml"
    code, error = _run([*check["configuration"]["argv"], "--junitxml=" + str(junit)], root, log_path, check["timeout_seconds"])
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


def execute(request):
    identity = request.get("check", {}).get("id", "invalid") if isinstance(request, dict) else "invalid"
    try:
        if (not isinstance(request, dict) or request.get("schema_version") != 1
                or set(request) - {"schema_version", "snapshot", "base", "trigger", "check", "log_path", "config"}
                or not isinstance(request.get("trigger"), str) or request["trigger"] not in TRIGGERS):
            raise ValueError("invalid execution request")
        config = _config(request.get("config", {}))
        check = next((item for item in describe(config)["checks"] if item["id"] == identity), None)
        if check is None or request.get("check") != check:
            raise ValueError("descriptor changed")
        if check["class"] == "expensive" and request["trigger"] == "edit":
            return _result(identity, "unavailable", "checkpoint_required")
        pins, helper = config.get("dagger", {}), config.get("dagger_helper_argv", [])
        if check["backend"] == "dagger" and (not {"engine", "image", "python_version", "uv_version"} <= pins.keys() or not helper):
            return _result(identity, "unavailable", "dagger_runtime_unconfigured")
        root = _snapshot(request)
        if (request["trigger"] not in {"checkpoint", "manual"}
                and identity not in selection(request["trigger"], _changed(root, request["base"]))["checks"]):
            return _result(identity, "unavailable", "selection_mismatch")
        if check["backend"] == "dagger":
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
        return _native(check, root, request["log_path"])
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, json.JSONDecodeError, TypeError):
        return _result(identity, "unavailable", "adapter_execution_unavailable")


def _checkout(base, root):
    """A clean plain checkout at a base inside its own history; runs Git only."""
    def git(*arguments):
        return subprocess.run(["git", *arguments], cwd=root, capture_output=True, timeout=60)
    if not isinstance(base, str) or not base or len(base) > 512 or base.startswith("-") or any(ord(c) < 32 or ord(c) == 127 for c in base):
        raise ValueError("base_unknown")
    if not root.is_dir() or str(Path(git("rev-parse", "--show-toplevel").stdout.decode().strip()).resolve()) != str(root.resolve()):
        raise ValueError("checkout_required")
    if git("status", "--porcelain", "--untracked-files=all").stdout.strip():
        raise ValueError("checkout_dirty")
    resolved = git("rev-parse", "--verify", "--quiet", base + "^{commit}")
    if resolved.returncode:
        raise ValueError("base_unknown")
    resolved = resolved.stdout.decode().strip()
    if git("merge-base", "--is-ancestor", resolved, "HEAD").returncode:
        raise ValueError("base_not_in_history")
    return resolved, git("rev-parse", "HEAD").stdout.decode().strip(), _changed(root, resolved)


def plan(base, trigger="affected", *, root=None):
    """The selection and each selected command for a clean checkout; nothing is executed."""
    resolved, head, changed = _checkout(base, ROOT if root is None else root)
    chosen = selection(trigger, changed)
    return {"schema_version": 1, "kind": "dotfiles-validation-plan", "adapter_id": "dotfiles.continuous-validation",
            "base": resolved, "head": head, "trigger": trigger, "selection": chosen,
            "checks": [{"id": check["id"], "class": check["class"], "backend": check["backend"], "lane": check["lane"],
                        "argv": check["configuration"].get("argv")}
                       for check in describe()["checks"] if check["id"] in chosen["checks"]]}


def run(base, output, trigger="affected", *, root=None):
    """Execute the selected Linux-native checks in a clean checkout and write one result."""
    root = ROOT if root is None else root
    resolved, head, changed = _checkout(base, root)
    chosen = selection(trigger, changed)
    target = Path(output).absolute()
    if ".." in target.parts or target.is_symlink():
        raise ValueError("output_invalid")
    if target.resolve().is_relative_to(root.resolve()):
        raise ValueError("output_inside_checkout")
    if os.path.lexists(target):
        raise ValueError("output_exists")
    logs = target.parent / (target.name + ".logs")
    executed, skipped = [], []
    for check in describe()["checks"]:
        if check["id"] not in chosen["checks"]:
            continue
        if check["backend"] != "native":
            skipped.append({"id": check["id"], "reason": "dagger_lane"})
        elif check["class"] == "expensive" and trigger == "edit":
            skipped.append({"id": check["id"], "reason": "checkpoint_required"})
        else:
            executed.append(_native(check, root, logs / (check["id"] + ".log")))
    value = {"schema_version": 1, "kind": "dotfiles-validation-run", "adapter_id": "dotfiles.continuous-validation",
             "base": resolved, "head": head, "trigger": trigger, "selection": chosen,
             "executed": executed, "not_executed": skipped}
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
    statuses = {item["status"] for item in executed}
    return (1 if "failed" in statuses else 2 if statuses - {"passed"} else 0), value, target


def _command(argv):
    """`plan` and `run` serve a plain checkout; neither needs DBSCTR or an enrollment."""
    parser = argparse.ArgumentParser(prog="continuous_validation.py", add_help=False)
    parser.add_argument("action", choices=("plan", "run"))
    parser.add_argument("--base", required=True)
    parser.add_argument("--trigger", default="affected", choices=TRIGGERS)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.action == "plan":
            value = plan(args.base, args.trigger)
            if args.json:
                print(json.dumps(value, sort_keys=True))
            else:
                print("basis:", value["selection"]["basis"])
                for check in value["checks"]:
                    print("selected:", check["id"])
                    print("command:", " ".join(check["argv"]) if check["argv"] else "tracked-file Python syntax scan")
            return 0
        if not args.output:
            raise ValueError("arguments_invalid")
        code, value, target = run(args.base, args.output, args.trigger)
        print(json.dumps({**{name: value[name] for name in ("schema_version", "kind", "base", "head", "trigger", "selection")},
                          "output": str(target), "executed": [item["check_id"] for item in value["executed"]],
                          "not_executed": value["not_executed"]}, sort_keys=True))
        return code
    except SystemExit:
        code = "arguments_invalid"
    except ValueError as error:
        code = str(error) if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", str(error)) else "adapter_protocol_invalid"
    except (OSError, TypeError, KeyError, subprocess.SubprocessError):
        code = "adapter_protocol_invalid"
    print(json.dumps({"schema_version": 1, "error": code}))
    return 2


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in {"plan", "run"}:
        return _command(argv)
    try:
        if len(argv) != 2 or argv[1] not in {"describe", "select", "execute"}:
            raise ValueError("action required")
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("input limit")
        request = json.loads(raw)
        if argv[1] == "describe":
            if not isinstance(request, dict) or set(request) - {"schema_version", "config"} or request.get("schema_version") != 1:
                raise ValueError("invalid describe request")
            value = describe(request.get("config", {}))
        else:
            value = globals()[argv[1]](request)
        print(json.dumps(value, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError):
        print(json.dumps({"schema_version": 1, "error": "adapter_protocol_invalid"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
