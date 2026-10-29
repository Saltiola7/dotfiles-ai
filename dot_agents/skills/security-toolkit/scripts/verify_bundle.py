"""Verify reviewed skill bundles against the local lock, without network or execution.

Run only on a trusted source/deployment directory. This diagnoses drift; it is
not a sandbox, signature verifier, or safety scanner for hostile filesystems.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


def verify(skills_root: Path, lock: dict[str, Any]) -> list[str]:
    failures = []
    if skills_root.is_symlink() or not skills_root.is_dir():
        return ["skills root must be a real directory"]
    for package in lock["packages"]:
        name = package["name"]
        if "/" in name or name in ("", ".", ".."):
            return ["invalid package name"]
        root = skills_root / name
        if root.is_symlink() or not root.is_dir():
            failures.append(f"{name}: missing or linked bundle")
            continue
        expected = package["files"]
        for relative in expected:
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or str(path) != relative:
                return ["invalid lock path"]
        actual = {}
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                failures.append(f"{name}/{relative}: symbolic link")
            elif path.is_file():
                actual[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif not path.is_dir():
                failures.append(f"{name}/{relative}: unsupported file type")
        for relative in sorted(set(expected) | set(actual)):
            if expected.get(relative) != actual.get(relative):
                failures.append(f"{name}/{relative}: missing, unexpected or changed file")
    return failures


def main() -> int:
    toolkit = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=toolkit.parent)
    args = parser.parse_args()
    try:
        lock = json.loads((toolkit / "references/sources.lock.json").read_text())
        if lock["schema_version"] != 1:
            raise ValueError("unsupported lock schema")
        failures = verify(args.skills_root, lock)
    except (OSError, ValueError, KeyError, TypeError):
        print("Bundle verification failed: unreadable or invalid inventory")
        return 1
    if failures:
        print("Bundle verification failed:\n" + "\n".join(failures))
        return 1
    print(f"Verified {len(lock['packages'])} pinned bundles; no scan or target execution performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
