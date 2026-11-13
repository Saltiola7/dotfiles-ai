"""Bounded offline stdin interface. No adapter/configuration/credential loader."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import core


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dbsctr-integration")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate structure only; no native authority")
    validate.add_argument("--kind", required=True, choices=("source", "candidate", "ticket", "target"))
    commands.add_parser("status", help="inspect one offline Target, without verifying native state")
    for name in ("submit", "adopt", "advance", "reconcile", "operator-resume"):
        commands.add_parser(name, help="unavailable until separately qualified live adapters")
    args = parser.parse_args(argv)
    try:
        if args.command not in {"validate", "status"}:
            core.unavailable_operation()
        kind = "target" if args.command == "status" else args.kind
        limit = core.TARGET_LIMIT if kind == "target" else core.RECORD_LIMIT
        value = core.decode(kind, sys.stdin.buffer.read(limit + 1))
        if args.command == "status":
            assert isinstance(value, core.Target)
            result: dict[str, object] = {"status": "offline", "authority": "unverified",
                "queued": len(value.queue), "active": value.active is not None,
                "generation": value.generation}
        else:
            result = {"status": "valid", "authority": "structural_only",
                      "kind": kind, "sha256": core.identity(value)}
        print(json.dumps(result, sort_keys=True))
        return 0
    except core.Unavailable:
        print("dbsctr-integration: live_adapters_unavailable", file=sys.stderr)
        return 78
    except (core.Invalid, OSError, ValueError, RecursionError):
        print("dbsctr-integration: invalid_record", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
