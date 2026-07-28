#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run(["dbsctrctl", "cleanup", "--completed", "--all"], text=True)
raise SystemExit(result.returncode)
