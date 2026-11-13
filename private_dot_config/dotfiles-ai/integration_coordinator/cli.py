"""Bounded offline codecs and explicitly selected qualified adapter entrypoints."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import subprocess
import sys
from typing import Sequence

from . import core


def _local_action(action: str, arguments: list[str]) -> int:
    """Select the paired lifecycle owner; never resolve a helper from task input."""
    location = Path(__file__).resolve()
    if location.parents[2].name == "private_dot_config":
        helper = location.parents[3] / "dot_local/bin/executable_dbsctrctl"
    else:
        package = Path.home() / ".config/dotfiles-ai/integration_coordinator"
        if location.parent != package:
            raise core.Unavailable("lifecycle_owner_unavailable")
        helper = Path.home() / ".local/bin/dbsctrctl"
    if not stat.S_ISREG(helper.lstat().st_mode):
        raise core.Unavailable("lifecycle_owner_unavailable")
    try:
        return subprocess.run([sys.executable, str(helper), "integration-" + action, *arguments],
                              stdin=subprocess.DEVNULL, timeout=300, check=False).returncode
    except (OSError, subprocess.TimeoutExpired):
        raise core.Unavailable("lifecycle_owner_unavailable") from None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dbsctr-integration")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate structure only; no native authority")
    validate.add_argument("--kind", required=True, choices=("source", "candidate", "ticket", "target"))
    status = commands.add_parser("status", help="offline Target by default; explicit remote obligation status")
    status.add_argument("--remote", action="store_true")
    status.add_argument("--cycle-id")
    for name in ("submit", "adopt", "reconcile", "operator-resume"):
        command = commands.add_parser(name, help="explicit enrolled lifecycle/native action")
        command.add_argument("--cycle-id")
        if name == "adopt":
            command.add_argument("--pr", type=int)
            command.add_argument("--integration-mode", default="inherit",
                                 choices=("inherit", "off", "draft_pr", "pr", "ordinary", "admin"))
        if name == "operator-resume":
            command.add_argument("--handle")
            command.add_argument("--expected-generation", type=int)
    advance = commands.add_parser("advance", help="trusted hosted wakeup; unavailable without explicit policy")
    advance.add_argument("--policy", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "advance" and args.policy is not None:
            from .controller import hosted_main
            return hosted_main(args.policy)
        if args.command == "status" and args.remote:
            if not args.cycle_id:
                core.unavailable_operation()
            return _local_action("status", ["--cycle-id", args.cycle_id])
        if args.command not in {"validate", "status"}:
            if not getattr(args, "cycle_id", None):
                core.unavailable_operation()
            arguments = ["--cycle-id", args.cycle_id]
            if args.command == "adopt":
                if type(args.pr) is not int or args.pr <= 0:
                    raise core.Invalid("adoption_pr_required")
                arguments.extend(("--pr", str(args.pr)))
                if args.integration_mode != "inherit":
                    arguments.extend(("--integration-mode", args.integration_mode))
            if args.command == "operator-resume":
                if not args.handle or type(args.expected_generation) is not int or args.expected_generation <= 0:
                    raise core.Invalid("operator_candidate_required")
                arguments.extend(("--handle", args.handle, "--expected-generation", str(args.expected_generation)))
            return _local_action(args.command, arguments)
        kind = "target" if args.command == "status" else args.kind
        limit = core.TARGET_LIMIT if kind == "target" else core.RECORD_LIMIT
        raw = sys.stdin.buffer.read(limit + 1)
        if len(raw) > limit:
            raise core.Invalid("record_limit")
        envelope: object = json.loads(raw)
        version = envelope.get("schema_version") if isinstance(envelope, dict) else None
        if type(version) is int and version == 2:
            from . import runtime
            value = runtime.decode(kind, raw)
        else:
            value = core.decode(kind, raw)
        if args.command == "status":
            if not isinstance(value, core.Target):
                from . import runtime
                if not isinstance(value, runtime.Target):
                    raise core.Invalid("target_required")
            result: dict[str, object] = {"status": "offline", "authority": "unverified",
                "queued": len(value.queue), "active": value.active is not None,
                "generation": value.generation}
        else:
            result = {"status": "valid", "authority": "structural_only",
                      "kind": kind, "sha256": core.identity(value)}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (core.Unavailable, ImportError):
        print("dbsctr-integration: live_adapters_unavailable", file=sys.stderr)
        return 78
    except core.Ambiguous:
        print("dbsctr-integration: native_outcome_uncertain", file=sys.stderr)
        return 75
    except core.Conflict:
        print("dbsctr-integration: input_or_generation_changed", file=sys.stderr)
        return 75
    except (core.Invalid, OSError, ValueError, RecursionError):
        print("dbsctr-integration: invalid_record", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
