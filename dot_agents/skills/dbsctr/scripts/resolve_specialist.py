"""Locate one permitted managed sibling; never search, install or execute it."""

import json
from pathlib import Path
import re
import sys


def resolve_specialist(name: str, *, script_path: Path | None = None) -> Path:
    """Follow the DBSCTR directory's physical location before selecting a sibling."""
    if not isinstance(name, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) is None:
        raise ValueError("invalid managed skill name")
    root = (script_path or Path(__file__)).resolve(strict=True).parent.parent
    entry = (root.parent / name / "SKILL.md").resolve(strict=True)
    if not entry.is_file():
        raise LookupError("managed entrypoint is not a regular file")
    with entry.open(encoding="utf-8") as stream:
        prefix = stream.read(8192)
    if not prefix.startswith("---\n") or "\n---\n" not in prefix[4:]:
        raise LookupError("managed metadata could not be verified")
    header = prefix[4:].split("\n---\n", 1)[0]
    names = re.findall(r"^name:[ \t]*(.*?)[ \t]*$", header, flags=re.MULTILINE)
    if len(names) != 1:
        raise LookupError("managed name could not be verified")
    declared = names[0]
    if len(declared) >= 2 and declared[0] == declared[-1] and declared[0] in "\"'":
        declared = declared[1:-1]
    if declared != name:
        raise LookupError("managed name does not match")
    return entry


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"status": "unavailable", "reason": "one-managed-name-required"}))
        return 64
    try:
        entry = resolve_specialist(sys.argv[1])
    except UnicodeError:
        print(json.dumps({"status": "unavailable", "reason": "physical-sibling-not-verified"}))
        return 2
    except ValueError:
        print(json.dumps({"status": "unavailable", "reason": "invalid-managed-name"}))
        return 64
    except (OSError, LookupError, RuntimeError):
        print(json.dumps({"status": "unavailable", "reason": "physical-sibling-not-verified"}))
        return 2
    print(json.dumps({"status": "available", "name": sys.argv[1], "path": str(entry)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
