#!/usr/bin/env python3
import subprocess
import sys

failed = False
for command in (["herdr-history-maintain"], ["dbsctrctl", "cleanup", "--completed", "--all"]):
    try:
        failed |= subprocess.run(command, text=True).returncode != 0
    except OSError as error:
        print(f"{command[0]}: {error}", file=sys.stderr)
        failed = True
raise SystemExit(failed)
