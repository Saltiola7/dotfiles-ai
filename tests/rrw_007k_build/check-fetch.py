"""Exercise the bounded download contract without network access."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

script = Path(__file__).with_name("fetch-zig.sh").resolve()
body = b"abcdef"
digest = hashlib.sha256(body).hexdigest()
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    curl = root / "curl"
    curl.write_text("""#!/bin/bash
set -eu
while (($#)); do
  case "$1" in
    --continue-at) offset=$2; shift ;;
    --output) output=$2; shift ;;
  esac
  shift
done
printf '%s\\n' "$offset" >> "$CALLS"
case "$MODE:$offset" in
  *:0) printf abc >> "$output"; exit 28 ;;
  resume:3) printf def >> "$output" ;;
  corrupt:3) printf XYZ >> "$output" ;;
  no-range:3) exit 33 ;;
  exhausted:3) exit 28 ;;
  *) exit 99 ;;
esac
""")
    curl.chmod(0o700)
    for mode, result, offsets in (
        ("resume", 0, ["0", "3"]),
        ("corrupt", 1, ["0", "3"]),
        ("no-range", 33, ["0", "3"]),
        ("exhausted", 1, ["0", "3", "3", "3", "3"]),
    ):
        output = root / mode
        calls = root / f"{mode}.calls"
        process = subprocess.run(
            ["bash", script, output, "https://fixture.invalid/zig", "6", digest],
            env={**os.environ, "PATH": f"{root}:/usr/bin:/bin", "MODE": mode, "CALLS": str(calls)},
            capture_output=True,
            timeout=10,
        )
        assert process.returncode == result, (mode, process.stderr)
        assert calls.read_text().splitlines() == offsets
        assert not list(root.glob(f"{mode}.part.*"))
        if result == 0:
            assert output.read_bytes() == body
        else:
            assert not output.exists()
