"""Install or report pinned local tools; never scan, authenticate or register integrations."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from typing import Any, Literal, TypedDict


class ReleaseAsset(TypedDict):
    name: str
    url: str
    bytes: int
    sha256: str


class ToolSpec(TypedDict, total=False):
    name: str
    version: str
    kind: Literal["binary", "python"]
    asset: ReleaseAsset
    binary_sha256: str
    archive_member: str
    license_file: str
    license_sha256: str
    requirements: str
    requirements_sha256: str
    python: str

DATA = Path(__file__).resolve().parents[1] / "references/runtime"
DEFAULT_ROOT = Path.home() / ".config/dotfiles-ai/runtime/security"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_profile() -> dict[str, Any]:
    profile = json.loads((DATA / "tools.lock.json").read_text())
    if not isinstance(profile, dict) or profile["schema_version"] != 1 or any(x["enabled"] for x in profile["subscription_integrations"].values()):
        raise ValueError("unsupported or enabled subscription profile")
    return profile


def check_platform() -> None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("local runtime installation is qualified only for Apple Silicon macOS")
    if tuple(map(int, platform.mac_ver()[0].split(".")[:2])) < (13, 0):
        raise ValueError("local runtime installation requires macOS 13 or later")


def validate_directory(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError("runtime and cache roots must be absolute")
    for parent in reversed([path, *path.parents]):
        if not parent.exists() and not parent.is_symlink():
            continue
        item = parent.lstat()
        trusted_temporary = item.st_uid == 0 and bool(item.st_mode & stat.S_ISVTX)
        if (not stat.S_ISDIR(item.st_mode) or item.st_uid not in (0, os.getuid())
                or item.st_mode & 0o022 and not trusted_temporary):
            raise ValueError("unsafe runtime directory or ancestor")


def real_directory(path: Path) -> None:
    validate_directory(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    validate_directory(path)


def regular_file(path: Path) -> None:
    item = path.lstat()
    if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid()
            or item.st_mode & 0o022 or item.st_nlink != 1):
        raise ValueError("unsafe runtime file")


def inventory(root: Path) -> dict[str, dict[str, str | int]]:
    result = {}
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        if name == "installed.json":
            continue
        item = path.lstat()
        if stat.S_ISLNK(item.st_mode):
            # uv's Python links are recorded, never silently followed or changed.
            result[name] = {"link": os.readlink(path)}
        elif stat.S_ISREG(item.st_mode):
            regular_file(path)
            result[name] = {"sha256": digest(path), "mode": stat.S_IMODE(item.st_mode)}
        elif stat.S_ISDIR(item.st_mode):
            validate_directory(path)
            result[name] = {"directory_mode": stat.S_IMODE(item.st_mode), "owner": item.st_uid}
        else:
            raise ValueError("unsupported runtime entry")
    return result


def secure_uv_lock(path: Path) -> None:
    item = path.lstat()
    if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid()
            or item.st_nlink != 1 or item.st_size != 0):
        raise ValueError("unexpected uv environment lock")
    # uv creates its own empty environment lock with 0666; keep this private.
    path.chmod(0o600)


def preflight(tool: ToolSpec) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z-]+", tool["name"]) or not re.fullmatch(r"[0-9.]+", tool["version"]):
        raise ValueError("unsafe tool identity")
    if tool["kind"] == "binary" and tool["name"] in ("gitleaks", "osv-scanner"):
        asset = tool["asset"]
        expected = "https://github.com/" + ("gitleaks/gitleaks" if tool["name"] == "gitleaks" else "google/osv-scanner") + "/releases/download/"
        if (not asset["url"].startswith(expected) or Path(asset["name"]).name != asset["name"]
                or not 0 < asset["bytes"] <= 100 * 1024 * 1024):
            raise ValueError("release does not match reviewed vendor")
        for key in (asset["sha256"], tool["binary_sha256"], tool["license_sha256"]):
            if not re.fullmatch(r"[0-9a-f]{64}", key):
                raise ValueError("invalid release digest")
        license_path = DATA / tool["license_file"]
        if license_path.parent != DATA:
            raise ValueError("invalid license path")
        regular_file(license_path)
        if digest(license_path) != tool["license_sha256"]:
            raise ValueError("upstream license drift")
        return {}
    if tool["kind"] == "python" and tool["name"] == "semgrep":
        requirements = DATA / tool["requirements"]
        if requirements.parent != DATA:
            raise ValueError("invalid Python lock path")
        regular_file(requirements)
        if digest(requirements) != tool["requirements_sha256"]:
            raise ValueError("Python runtime lock drift")
        uv = shutil.which("uv")
        if not uv:
            raise ValueError("existing uv is required")
        env = {key: value for key, value in os.environ.items() if not key.startswith(("UV_", "PIP_"))}
        selected = subprocess.run([uv, "--no-config", "python", "find", "--system", "--no-python-downloads", tool["python"]],
                                  env=env, check=True, text=True, capture_output=True).stdout.strip()
        return {"uv": uv, "python": selected, "env": env}
    raise ValueError("unsupported tool kind")


def check_archive(archive: Path, member_name: str) -> bytes:
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError("unsafe release archive member")
        selected = bundle.getmember(member_name)
        if not selected.isfile() or selected.size > 100 * 1024 * 1024:
            raise ValueError("unexpected release binary")
        return bundle.extractfile(selected).read()


def binary_path(tool: ToolSpec, generation: Path) -> Path:
    return generation / ("venv/bin/semgrep" if tool["kind"] == "python" else tool["name"])


def smoke(tool: ToolSpec, generation: Path) -> None:
    executable = binary_path(tool, generation)
    with tempfile.TemporaryDirectory(prefix="security-tool-version-") as temporary:
        env = {"PATH": str(executable.parent) + ":/opt/homebrew/bin:/usr/bin:/bin", "HOME": temporary,
               "TMPDIR": temporary, "LANG": "C", "PYTHONDONTWRITEBYTECODE": "1", "SEMGREP_ENABLE_VERSION_CHECK": "0",
               "SEMGREP_SEND_METRICS": "off", "SEMGREP_SETTINGS_FILE": temporary + "/settings.yaml",
               "SEMGREP_LOG_FILE": temporary + "/semgrep.log", "SEMGREP_VERSION_CACHE_PATH": temporary + "/version"}
        flags = ["version"] if tool["name"] == "gitleaks" else ["--version"]
        if tool["name"] == "semgrep":
            flags += ["--disable-version-check", "--metrics=off"]
        result = subprocess.run([str(executable), *flags], env=env, cwd=temporary, capture_output=True, text=True, timeout=30)
        if result.returncode or not re.search(r"(?<![0-9.])" + re.escape(tool["version"]) + r"(?![0-9.])", result.stdout + result.stderr):
            raise ValueError(tool["name"] + ": version qualification failed")


def generation_for(tool: ToolSpec, root: Path) -> Path:
    identity = tool.get("requirements_sha256", tool.get("binary_sha256"))
    return root / tool["name"] / (tool["version"] + "-" + identity[:12])


def verify_generation(tool: ToolSpec, generation: Path) -> None:
    validate_directory(generation)
    marker = generation / "installed.json"
    if not marker.exists() and not marker.is_symlink():
        raise ValueError(tool["name"] + ": incomplete generation requires explicit recovery")
    regular_file(marker)
    record = json.loads(marker.read_text())
    if not isinstance(record, dict):
        raise ValueError("invalid installed record")
    executable = binary_path(tool, generation)
    regular_file(executable)
    if (record.get("tool") != tool or digest(executable) != record.get("entrypoint_sha256")
            or inventory(generation) != record.get("files")):
        raise ValueError(tool["name"] + ": installed generation drift")
    if tool["kind"] == "binary" and record["entrypoint_sha256"] != tool["binary_sha256"]:
        raise ValueError(tool["name"] + ": binary checksum mismatch")


def install(tool: ToolSpec, root: Path, cache: Path) -> None:
    prerequisites = preflight(tool)
    real_directory(root)
    real_directory(root / tool["name"])
    generation = generation_for(tool, root)
    if generation.exists() or generation.is_symlink():
        if generation.is_symlink():
            raise ValueError("linked tool generation")
        verify_generation(tool, generation)
        smoke(tool, generation)
        print(tool["name"], tool["version"], "already installed and qualified")
        return
    # Failed/incomplete generations are retained rather than overwritten or removed.
    if tool["kind"] == "binary":
        asset = tool["asset"]
        real_directory(cache)
        download = cache / asset["name"]
        if not download.exists() and not download.is_symlink():
            with tempfile.NamedTemporaryFile(prefix="release-", dir=cache, delete=False) as temporary:
                partial = Path(temporary.name)
            subprocess.run(["/usr/bin/curl", "--fail", "--location", "--silent", "--show-error",
                            "--proto", "=https", "--tlsv1.2", "--max-filesize", str(asset["bytes"]),
                            "--output", str(partial), asset["url"]], check=True, timeout=120)
            regular_file(partial)
            if digest(partial) != asset["sha256"] or partial.stat().st_size != asset["bytes"]:
                raise ValueError(tool["name"] + ": release checksum/size mismatch")
            partial.rename(download)
        regular_file(download)
        if digest(download) != asset["sha256"] or download.stat().st_size != asset["bytes"]:
            raise ValueError(tool["name"] + ": release checksum/size mismatch")
        generation.mkdir(mode=0o700)
        binary = binary_path(tool, generation)
        binary.write_bytes(check_archive(download, tool["archive_member"]) if "archive_member" in tool else download.read_bytes())
        if digest(binary) != tool["binary_sha256"]:
            raise ValueError(tool["name"] + ": binary checksum mismatch")
        binary.chmod(0o755)
        license_path = DATA / tool["license_file"]
        if digest(license_path) != tool["license_sha256"]:
            raise ValueError("upstream license drift")
        shutil.copyfile(license_path, generation / "LICENSE.upstream")
    elif tool["kind"] == "python" and tool["name"] == "semgrep":
        requirements = DATA / tool["requirements"]
        uv, selected, env = prerequisites["uv"], prerequisites["python"], prerequisites["env"]
        env["UV_CACHE_DIR"] = str(root / "cache/uv")
        generation.mkdir(mode=0o700)
        subprocess.run([uv, "--no-config", "venv", "--no-python-downloads", "--python", selected, str(generation / "venv")], env=env, check=True)
        subprocess.run([uv, "--no-config", "pip", "sync", "--no-python-downloads", "--python", str(generation / "venv/bin/python"),
                        "--require-hashes", "--only-binary", ":all:", "--link-mode", "copy", "--index-url", "https://pypi.org/simple", str(requirements)], env=env, check=True)
    else:
        raise ValueError("unsupported tool kind")
    if tool["kind"] == "python":
        secure_uv_lock(generation / "venv/.lock")
    smoke(tool, generation)
    marker = {"tool": tool, "entrypoint_sha256": digest(binary_path(tool, generation)), "qualification": "version_only_no_scan", "files": inventory(generation)}
    (generation / "installed.json").write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    print(tool["name"], tool["version"], "installed; version smoke passed; no scan")


def status(profile: dict[str, Any], root: Path, run_smoke: bool = False) -> dict[str, Any]:
    tools = []
    for tool in profile["tools"]:
        generation = generation_for(tool, root)
        state = "missing"
        if generation.exists() or generation.is_symlink():
            try:
                if generation.is_symlink():
                    raise ValueError("linked generation")
                verify_generation(tool, generation)
                if run_smoke:
                    smoke(tool, generation)
                state = "installed_version_qualified" if run_smoke else "installed_record_verified"
            except (ValueError, OSError, subprocess.SubprocessError):
                state = "drift_or_unqualified"
        tools.append({"name": tool["name"], "version": tool["version"], "state": state,
                      "entrypoint": str(binary_path(tool, generation)) if state.startswith("installed_") else None})
    return {"tools": tools, "subscription_integrations": profile["subscription_integrations"],
            "osv_database": profile["osv_database"], "audit_performed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "install"])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--smoke", action="store_true", help="only sanitized version probes, never scans")
    args = parser.parse_args()
    try:
        profile = load_profile()
        if args.action == "install":
            check_platform()
            for tool in profile["tools"]:
                install(tool, args.root, args.cache or args.root / "cache/downloads")
        else:
            result = status(profile, args.root, args.smoke)
            print(json.dumps(result, indent=2, sort_keys=True))
            if args.smoke and any(t["state"] != "installed_version_qualified" for t in result["tools"]):
                return 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, tarfile.TarError) as error:
        print("Local tooling setup failed:", str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
