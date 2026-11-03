"""Private, local Prefect orchestration for an explicitly configured Obsidian lab.

The trusted lab exporter owns schemas. This adapter owns immutable capture,
atomic generation publication, serialized refresh, recovery, and supervision.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
from dataclasses import dataclass, field
from typing import Iterator
from urllib.parse import urlsplit
from urllib.request import urlopen
import uuid


class SafeFailure(RuntimeError):
    """An operational category safe to expose in orchestration metadata."""


class Busy(SafeFailure):
    pass


@dataclass(frozen=True)
class Config:
    lab_root: Path
    vault_path: Path
    state_root: Path
    python: Path
    obsidian_cli: Path
    vault_name: str
    api_url: str
    reports: dict[str, int]
    poll_seconds: float = 1
    quiet_seconds: float = 2
    retry_seconds: float = 15

    @property
    def exporter_path(self) -> Path:
        preserved = self.lab_root / "workbench_source.py"
        return preserved if preserved.exists() else self.lab_root / "workbench.py"

    @classmethod
    def from_dict(cls, value: dict) -> Config:
        try:
            data = dict(value)
            for name in ("lab_root", "vault_path", "state_root", "python", "obsidian_cli"):
                path = Path(data[name])
                if not path.is_absolute():
                    raise ValueError
                data[name] = path.resolve() if name in {"lab_root", "vault_path", "state_root"} else path.absolute()
            address = urlsplit(data["api_url"])
            if (address.scheme != "http" or address.hostname != "127.0.0.1"
                    or not address.port or address.path != "/api"
                    or address.username or address.password or address.query or address.fragment):
                raise ValueError
            if not re.fullmatch(r"[\w .-]{1,100}", data["vault_name"]):
                raise ValueError
            reports = data["reports"]
            if not isinstance(reports, dict) or not reports:
                raise ValueError
            for name, blocks in reports.items():
                path = Path(name)
                if (path.is_absolute() or ".." in path.parts or path.suffix != ".md"
                        or path.parts[0] in {"Records", "Knowledge", ".obsidian"}
                        or type(blocks) is not int or blocks < 1):
                    raise ValueError
            for name in ("poll_seconds", "quiet_seconds", "retry_seconds"):
                number = data.get(name, cls.__dataclass_fields__[name].default)
                if type(number) not in (int, float) or not 0 < number <= 3600:
                    raise ValueError
            config = cls(**data)
            vault, lab, state = (p.resolve() for p in
                                  (config.vault_path, config.lab_root, config.state_root))
            if not vault.is_relative_to(lab) or vault == lab:
                raise ValueError
            if state.is_relative_to(vault) or vault.is_relative_to(state):
                raise ValueError
            return config
        except (ValueError, TypeError, KeyError, IndexError):
            raise SafeFailure("invalid_config") from None

    @classmethod
    def load(cls, path: Path) -> Config:
        try:
            return cls.from_dict(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            raise SafeFailure("invalid_config") from None


@dataclass(frozen=True)
class Snapshot:
    digest: str
    files: dict[str, bytes] = field(repr=False)
    link_targets: frozenset[str] = field(default_factory=frozenset, repr=False)


def private_root(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def atomic_json(path: Path, value: dict) -> None:
    private_root(path.parent)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            os.chmod(temporary, 0o600)
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (OSError, ValueError):
        raise SafeFailure("invalid_checkpoint") from None


@contextlib.contextmanager
def process_lock(path: Path) -> Iterator[None]:
    import fcntl

    private_root(path.parent)
    with path.open("a") as handle:
        os.chmod(path, 0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Busy("busy") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def capture(config: Config) -> Snapshot:
    """Capture canonical bytes, rejecting absent roots and all source symlinks."""
    files: dict[str, bytes] = {}
    def unavailable(error: OSError) -> None:
        raise SafeFailure("source_unavailable") from None

    try:
        for name in ("Records", "Knowledge"):
            root = config.vault_path / name
            if not root.is_dir() or root.is_symlink():
                raise SafeFailure("source_unavailable")
            for directory, folders, names in os.walk(root, followlinks=False, onerror=unavailable):
                parent = Path(directory)
                if any((parent / child).is_symlink() for child in folders):
                    raise SafeFailure("source_symlink")
                for child in sorted(names):
                    path = parent / child
                    if path.suffix != ".md":
                        continue
                    if path.is_symlink():
                        raise SafeFailure("source_symlink")
                    files[path.relative_to(config.vault_path).as_posix()] = path.read_bytes()
        hasher = hashlib.sha256()
        link_targets = set()
        for name, content in sorted(files.items()):
            hasher.update(name.encode() + b"\0" + hashlib.sha256(content).digest())
            for link in re.findall(r"\[\[([^\]]+)\]\]", content.decode("utf-8", errors="replace")):
                target = link.partition("|")[0].split("#", 1)[0].replace("\\", "")
                if not target:
                    continue
                path = Path(target if Path(target).suffix else target + ".md")
                if path.is_absolute() or ".." in path.parts:
                    continue
                if (config.vault_path / path).is_file():
                    link_targets.add(path.as_posix())
        hasher.update(json.dumps(sorted(link_targets)).encode())
        hasher.update(config.exporter_path.read_bytes())
        hasher.update(Path(__file__).read_bytes())
        hasher.update(json.dumps({"reports": config.reports, "vault": str(config.vault_path),
                                  "vault_name": config.vault_name, "cli": str(config.obsidian_cli)},
                                 sort_keys=True).encode())
        source = config.lab_root / ".source/linear/snapshot.json"
        if source.exists():
            hasher.update(source.read_bytes())
        return Snapshot(hasher.hexdigest(), files, frozenset(link_targets))
    except OSError:
        raise SafeFailure("source_unavailable") from None


def build_generation(config: Config, snapshot: Snapshot, occurrence: str) -> dict:
    """Run the existing exporter only against private immutable captured files."""
    generations = config.lab_root / "data/generations"
    private_root(generations)
    if not re.fullmatch(r"[0-9a-f]{32}", occurrence):
        raise SafeFailure("invalid_occurrence")
    generation = generations / occurrence
    generation.mkdir(mode=0o700)
    private_root(config.state_root)
    try:
        with tempfile.TemporaryDirectory(prefix="capture-", dir=config.state_root) as temporary:
            vault = Path(temporary) / "vault"
            for name in ("Records", "Knowledge"):
                (vault / name).mkdir(parents=True)
            for name, content in snapshot.files.items():
                destination = vault / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            module = types.ModuleType("_trusted_workbench")
            module.__file__ = str(config.exporter_path)
            # Compile trusted exporter bytes directly: Python's timestamp-based
            # bytecode cache must not defeat the code fingerprint on fast saves.
            exec(compile(config.exporter_path.read_bytes(), str(config.exporter_path), "exec"), module.__dict__)
            if hasattr(module, "_rows"):
                original_rows = module._rows

                def captured_rows(vault_root: Path):
                    rows = original_rows(vault_root)
                    for link in rows.get("note_links", []):
                        link["target_exists"] = link["target_path"] in snapshot.link_targets
                    return rows

                # The exporter must see captured existence, not the absence of
                # uncopied binaries inside its temporary input directory.
                module._rows = captured_rows
            try:
                findings = module.validate_vault(vault)
                if findings:
                    raise SafeFailure("invalid_source")
                counts = module.export_projection(vault, generation)
            except ValueError:
                raise SafeFailure("invalid_source") from None
            shutil.move(str(vault / "Data"), str(generation / "Data"))
            if (not (generation / "knowledge.duckdb").is_file()
                    or set(counts) != set(module.TABLES)
                    or any(type(n) is not int or n < 0 for n in counts.values())):
                raise SafeFailure("incomplete_generation")
            for table in module.TABLES:
                for kind, suffix in (("parquet", "parquet"), ("json", "json")):
                    if not (generation / f"Data/{kind}/{table}.{suffix}").is_file():
                        raise SafeFailure("incomplete_generation")
        # Re-reading the live inputs also catches writes during the initial capture.
        if capture(config).digest != snapshot.digest:
            raise SafeFailure("superseded")
        outputs = {path.relative_to(generation).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in generation.rglob("*") if path.is_file()}
        manifest = {"occurrence": occurrence, "digest": snapshot.digest,
                    "counts": counts, "path": str(generation), "created_at": time.time(), "outputs": outputs}
        atomic_json(generation / "manifest.json", manifest)
        return manifest
    except Exception as error:
        shutil.rmtree(generation, ignore_errors=True)
        if isinstance(error, SafeFailure):
            raise
        raise SafeFailure("build_failed") from None


def _link(target: str, destination: Path) -> None:
    temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex)
    try:
        temporary.symlink_to(target)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def current_manifest(config: Config) -> dict:
    pointer = config.lab_root / "data/current"
    if not pointer.is_symlink():
        return {}
    target = pointer.resolve()
    if target.parent != (config.lab_root / "data/generations").resolve():
        raise SafeFailure("invalid_generation_pointer")
    manifest = read_json(target / "manifest.json")
    if not manifest or manifest.get("path") != str(target):
        raise SafeFailure("invalid_generation_manifest")
    return manifest


def publish_generation(config: Config, manifest: dict) -> None:
    """Switch every stable serving path through one atomic current pointer."""
    generation = Path(manifest["path"])
    expected = config.lab_root / "data/generations" / manifest["occurrence"]
    if generation != expected or read_json(generation / "manifest.json") != manifest:
        raise SafeFailure("invalid_generation_manifest")
    for name, digest in manifest.get("outputs", {}).items():
        path = generation / name
        if (Path(name).is_absolute() or ".." in Path(name).parts or not path.is_file()
                or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise SafeFailure("incomplete_generation")
    if capture(config).digest != manifest["digest"]:
        raise SafeFailure("superseded")
    data = config.lab_root / "data"
    # Set the valid target before migrating stable links: interrupted first
    # installation must never leave a newly created link targeting nothing.
    _link(os.path.relpath(generation, data), data / "current")
    ensure_serving_links(config)


def ensure_serving_links(config: Config) -> None:
    """Finish or repair the one-time migration before any UI acknowledgement."""
    # The first migration preserves original artifacts. Subsequent publications
    # replace only the single current symlink; both stable serving links persist.
    data = config.lab_root / "data"
    recovery = data / "initial-recovery"
    private_root(recovery)
    for path, backup, target in (
        (config.vault_path / "Data", recovery / "Data", os.path.relpath(data / "current/Data", config.vault_path)),
        (data / "knowledge.duckdb", recovery / "knowledge.duckdb", "current/knowledge.duckdb"),
    ):
        if path.is_symlink():
            if os.readlink(path) != target:
                raise SafeFailure("unexpected_serving_link")
        elif path.exists():
            if backup.exists():
                raise SafeFailure("unexpected_serving_files")
            path.rename(backup)
            try:
                _link(target, path)
            except Exception:
                backup.rename(path)
                raise
        else:
            _link(target, path)


def _evaluate(config: Config, expression: str):
    """Never expose CLI output: the plugin logs SQL and possibly record content."""
    try:
        result = subprocess.run(
            [str(config.obsidian_cli), "vault=" + config.vault_name, "eval", "code=" + expression],
            capture_output=True, text=True, timeout=90, check=True,
        )
        values = re.findall(r"^=> (.*)$", result.stdout, re.M)
        if not values:
            raise ValueError
        return json.loads(values[-1])
    except (subprocess.SubprocessError, OSError, ValueError):
        raise SafeFailure("obsidian_unavailable") from None


def refresh(config: Config) -> None:
    """Reset only an already running Obsidian, verifying the selected vault."""
    for name in config.reports:
        path = config.vault_path / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(config.vault_path.resolve()):
            raise SafeFailure("invalid_report")
    alive = subprocess.run(["/usr/bin/pgrep", "-x", "Obsidian"], capture_output=True, timeout=5)
    if alive.returncode:
        raise SafeFailure("obsidian_closed")
    expression = """(async()=>{
      if(app.vault.adapter.getBasePath()!==VAULT) return JSON.stringify({error:'wrong_vault'});
      const p=app.plugins.plugins['duckdb-motherduck'];
      const c=app.commands.commands['duckdb-motherduck:reset-connection'];
      if(!p?.api||!c?.callback) return JSON.stringify({error:'plugin_unavailable'});
      await c.callback();
      const results=[];
      for(const [path,expected] of Object.entries(REPORTS)){
        const message=await p.api.refreshFile(path);
        const m=/^Refreshed (\\d+) block\\(s\\), (\\d+) error\\(s\\) in /.exec(message);
        results.push({ok:!!m&&Number(m[1])===expected&&Number(m[2])===0});
      }
      return JSON.stringify({ok:results.every(x=>x.ok),reports:results.length});
    })()""".replace("VAULT", json.dumps(str(config.vault_path.resolve()))).replace("REPORTS", json.dumps(config.reports))
    result = _evaluate(config, expression)
    if not isinstance(result, dict) or result.get("ok") is not True or result.get("reports") != len(config.reports):
        raise SafeFailure("refresh_failed")


def checkpoint(config: Config, **changes) -> dict:
    state = read_json(config.state_root / "checkpoint.json")
    state.update(changes, updated_at=time.time())
    atomic_json(config.state_root / "checkpoint.json", state)
    return state


def event(config: Config, state: dict) -> None:
    path = config.state_root / "events.json"
    history = read_json(path).get("events", [])
    history.append({k: state[k] for k in ("state", "digest", "occurrence", "error", "updated_at") if k in state})
    atomic_json(path, {"events": history[-200:]})


def reconcile(config: Config) -> dict:
    """Recover from the published manifest before deciding whether to rebuild."""
    private_root(config.state_root)
    with process_lock(config.state_root / "publisher.lock"):
        try:
            manifest = current_manifest(config)
            if manifest:
                ensure_serving_links(config)
            snapshot = capture(config)
            state = read_json(config.state_root / "checkpoint.json")
            if manifest.get("digest") != snapshot.digest:
                occurrence = uuid.uuid4().hex
                checkpoint(config, state="building", digest=snapshot.digest, occurrence=occurrence, error=None)
                manifest = build_generation(config, snapshot, occurrence)
                publish_generation(config, manifest)
                state = checkpoint(config, state="refresh_pending", occurrence=occurrence,
                                   digest=snapshot.digest, counts=manifest["counts"], error=None)
            if state.get("refreshed_occurrence") != manifest["occurrence"]:
                checkpoint(config, state="refresh_pending", occurrence=manifest["occurrence"],
                           digest=manifest["digest"], counts=manifest["counts"], error=None)
                refresh(config)
                state = checkpoint(config, state="current", occurrence=manifest["occurrence"],
                                   digest=manifest["digest"], counts=manifest["counts"],
                                   refreshed_occurrence=manifest["occurrence"], error=None)
            else:
                state = checkpoint(config, state="current", occurrence=manifest["occurrence"],
                                   digest=manifest["digest"], counts=manifest["counts"], error=None)
            cleanup_generations(config)
        except SafeFailure as error:
            state = checkpoint(config, state="error", error=str(error))
        except Exception:
            state = checkpoint(config, state="error", error="operation_failed")
        event(config, state)
        return state


def cleanup_generations(config: Config) -> None:
    current = current_manifest(config)
    root = config.lab_root / "data/generations"
    complete = []
    for path in root.iterdir():
        if re.fullmatch(r"[0-9a-f]{32}", path.name) and path.is_dir() and not path.is_symlink():
            manifest = read_json(path / "manifest.json")
            if manifest:
                complete.append((manifest.get("created_at", 0), path))
            else:
                shutil.rmtree(path)
    retained = {Path(current["path"])}
    for _, path in sorted(complete, reverse=True):
        if path not in retained and len(retained) < 2:
            retained.add(path)
    for _, path in complete:
        if path not in retained:
            shutil.rmtree(path)


def isolated_environment(config: Config) -> dict[str, str]:
    environment = {k: v for k, v in os.environ.items() if not k.startswith("PREFECT_")}
    prefect_home = config.state_root / "prefect"
    private_root(prefect_home)
    environment.update({
        "PREFECT_HOME": str(prefect_home), "PREFECT_PROFILES_PATH": str(prefect_home / "profiles.toml"),
        "PREFECT_SERVER_DATABASE_CONNECTION_URL": "sqlite+aiosqlite:///" + str(prefect_home / "prefect.db"),
        "PREFECT_API_URL": config.api_url, "PREFECT_SERVER_EPHEMERAL_ENABLED": "false",
        "PREFECT_SERVER_ANALYTICS_ENABLED": "false", "PREFECT_LOGGING_LOG_PRINTS": "false",
        "PREFECT_RESULTS_PERSIST_BY_DEFAULT": "false", "PREFECT_API_ENABLE_HTTP2": "false",
        "PYTHONUNBUFFERED": "1",
    })
    return environment


def runtime_directory(config: Config) -> Path:
    """Prefect reads dotenv and TOML from cwd, even with an explicit API URL."""
    directory = config.state_root / "runtime"
    private_root(directory)
    if any((directory / name).exists() for name in (".env", "prefect.toml", "pyproject.toml")):
        raise SafeFailure("unexpected_runtime_settings")
    return directory


def run_flow(config: Config) -> dict:
    # CLI sets environment before this lazy import. Parameters and exceptions
    # contain no note bytes, paths, SQL, raw validation output, or CLI output.
    from prefect import flow

    @flow(name="obsidian-vault-refresh", persist_result=False, log_prints=False)
    def pipeline() -> dict:
        state = reconcile(config)
        if state.get("state") != "current":
            raise SafeFailure(state.get("error", "refresh_pending")) from None
        return {key: state[key] for key in ("state", "digest", "occurrence", "counts")}

    try:
        return pipeline()
    except Exception:
        # Prefect receives only sanitized failures from pipeline. Transport
        # errors are handled by the outer watcher with bounded retries.
        # A failure before the flow body (API/auth/version availability) must
        # also be visible locally; otherwise a watcher can appear silently idle.
        state = read_json(config.state_root / "checkpoint.json")
        if state.get("state") not in {"error", "building", "refresh_pending"}:
            checkpoint(config, state="error", error="prefect_run_unavailable")
    state = read_json(config.state_root / "checkpoint.json")
    return state if state.get("state") == "error" else {"state": "error", "error": "flow_failed"}


def healthy(config: Config) -> bool:
    try:
        with urlopen(config.api_url + "/health", timeout=3) as response:
            return response.status == 200
    except OSError:
        return False


def bound_logs(config: Config) -> None:
    """Bound private launchd logs without moving files held open by launchd."""
    for path in log_root(config).glob("*.log"):
        if path.stat().st_size > 5 * 1024 * 1024:
            with path.open("r+b") as handle:
                handle.seek(-512 * 1024, os.SEEK_END)
                tail = handle.read()
                handle.seek(0)
                handle.write(tail)
                handle.truncate()


def watch(config: Config) -> None:
    with process_lock(config.state_root / "watcher.lock"):
        observed, changed_at, attempted, last_attempt = None, 0.0, None, 0.0
        while True:
            now = time.monotonic()
            try:
                bound_logs(config)
                digest = capture(config).digest
                if digest != observed:
                    observed, changed_at = digest, now
                state = read_json(config.state_root / "checkpoint.json")
                current = current_manifest(config)
                needed = (state.get("state") != "current" or current.get("digest") != digest or
                          state.get("refreshed_occurrence") != current.get("occurrence"))
                invalid = state.get("digest") == digest and state.get("error") in {"invalid_source", "source_symlink"}
                due = attempted != digest or (not invalid and now - last_attempt >= config.retry_seconds)
                if needed and due and now - changed_at >= config.quiet_seconds and healthy(config):
                    attempted, last_attempt = digest, now
                    run_flow(config)
            except SafeFailure as error:
                # Do not acknowledge a missing external volume as empty data.
                state = checkpoint(config, state="error", error=str(error))
            except Exception:
                checkpoint(config, state="error", error="watcher_retry")
            time.sleep(config.poll_seconds)


FACADE = '''"""Read APIs from the preserved exporter; persistent builds use safe orchestration."""
from pathlib import Path
import json
import subprocess
import sys
from workbench_source import *

def export_projection(vault_root, output_root):
    root = Path(__file__).resolve().parent
    if Path(vault_root).resolve() != (root / "sample-vault").resolve() or Path(output_root).resolve() != (root / "data").resolve():
        raise ValueError("Configured automation owns only its selected vault and output")
    command = [sys.executable, str(root / "scripts/auto_refresh.py"), "--config", str(root / ".automation/config.json"), "run"]
    result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=180)
    return json.loads(result.stdout)["counts"]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "build"])
    args = parser.parse_args()
    if args.command == "check":
        errors = validate_vault(LAB_ROOT / "sample-vault")
        print(json.dumps({"valid": not errors, "findings": errors}, indent=2))
        raise SystemExit(bool(errors))
    print(json.dumps(export_projection(LAB_ROOT / "sample-vault", LAB_ROOT / "data"), indent=2))
'''


def install_facade(config: Config) -> None:
    # Compatibility facade is intentionally restricted to the lab's original
    # public paths. Other adapters can use run/watch directly without migration.
    if config.vault_path.resolve() != (config.lab_root / "sample-vault").resolve():
        raise SafeFailure("facade_requires_sample_vault")
    original = config.lab_root / "workbench.py"
    preserved = config.lab_root / "workbench_source.py"
    if not preserved.exists():
        preserved.write_bytes(original.read_bytes())
    elif original.read_text() != FACADE:
        raise SafeFailure("exporter_drift")
    original.write_text(FACADE)


def agent_labels(config: Config) -> list[str]:
    identity = hashlib.sha256(str(config.state_root).encode()).hexdigest()[:10]
    return [f"dev.dotfiles-ai.obsidian-{identity}-server", f"dev.dotfiles-ai.obsidian-{identity}-watcher"]


def log_root(config: Config) -> Path:
    identity = hashlib.sha256(str(config.state_root).encode()).hexdigest()[:10]
    return Path.home() / "Library/Logs/obsidian-workbench" / identity


def install(config: Config, config_path: Path) -> None:
    if sys.platform != "darwin":
        raise SafeFailure("macos_required")
    os.umask(0o077)
    private_root(config.state_root)
    logs = log_root(config)
    private_root(logs)
    install_facade(config)
    agents = Path.home() / "Library/LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    environment = isolated_environment(config)
    # launchd does not inherit the invoking shell. Supply only explicit runtime
    # settings, never unrelated environment variables or credentials.
    environment = {k: v for k, v in environment.items() if k.startswith("PREFECT_") or k == "PYTHONUNBUFFERED"}
    environment.update({"PATH": "/opt/homebrew/bin:/usr/bin:/bin", "HOME": str(Path.home())})
    commands = [
        [str(config.python), str(Path(__file__).resolve()), "--config", str(config_path.resolve()), "server"],
        [str(config.python), str(Path(__file__).resolve()), "--config", str(config_path.resolve()), "watch"],
    ]
    for label, command in zip(agent_labels(config), commands, strict=True):
        path = agents / (label + ".plist")
        contents = {"Label": label, "ProgramArguments": command,
                    # launchd itself cannot open files on all external mounts.
                    # The user process enters its clean runtime before SDK import.
                    "WorkingDirectory": str(Path.home()), "EnvironmentVariables": environment,
                    "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 15,
                    "LimitLoadToSessionType": "Aqua", "ProcessType": "Background",
                    "StandardOutPath": str(logs / (label + ".out.log")),
                    "StandardErrorPath": str(logs / (label + ".err.log"))}
        path.write_bytes(plistlib.dumps(contents))
        path.chmod(0o600)
        for stream in (contents["StandardOutPath"], contents["StandardErrorPath"]):
            Path(stream).touch(mode=0o600, exist_ok=True)
            Path(stream).chmod(0o600)
        subprocess.run(["/bin/launchctl", "bootout", f"gui/{os.getuid()}/{label}"], capture_output=True)
        # bootout can return while the old job is still being removed.
        for attempt in range(20):
            result = subprocess.run(["/bin/launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)], capture_output=True)
            if not result.returncode:
                break
            time.sleep(0.25)
        else:
            raise SafeFailure("launchagent_install_failed")


def uninstall(config: Config) -> None:
    for label in agent_labels(config):
        subprocess.run(["/bin/launchctl", "bootout", f"gui/{os.getuid()}/{label}"], capture_output=True)
        (Path.home() / "Library/LaunchAgents" / (label + ".plist")).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("command", choices=("run", "watch", "status", "install", "uninstall", "server"))
    args = parser.parse_args()
    args.config = args.config.resolve()
    os.umask(0o077)
    try:
        config = Config.load(args.config)
        for key in list(os.environ):
            if key.startswith("PREFECT_"):
                del os.environ[key]
        os.environ.update(isolated_environment(config))
        os.chdir(runtime_directory(config))
        if args.command == "server":
            command = [str(config.python), "-m", "prefect", "server", "start", "--host", "127.0.0.1",
                       "--port", str(urlsplit(config.api_url).port)]
            os.execve(config.python, command, isolated_environment(config))
        elif args.command == "watch":
            watch(config)
        elif args.command == "run":
            if not healthy(config):
                raise SafeFailure("prefect_unavailable")
            result = run_flow(config)
            print(json.dumps(result))
            return 0 if result.get("state") == "current" else 1
        elif args.command == "status":
            result = read_json(config.state_root / "checkpoint.json")
            result["api_healthy"] = healthy(config)
            print(json.dumps(result, indent=2))
        elif args.command == "install":
            install(config, args.config)
        elif args.command == "uninstall":
            uninstall(config)
        return 0
    except SafeFailure as error:
        print(json.dumps({"state": "error", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
