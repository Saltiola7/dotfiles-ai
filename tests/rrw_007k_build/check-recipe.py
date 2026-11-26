"""Check draft workflow and pinned recipe without running a hosted build."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml


root = Path(__file__).resolve().parents[2]
recipe = Path(__file__).resolve().parent
workflow = root / ".github/workflows/rrw-007k-herdr-build.yml"
plan = root / "docs/initiatives/rhel-remote-workspace/HERDR-BUILD.plan.json"
config = yaml.load(workflow.read_text(), Loader=yaml.BaseLoader)
assert set(config["on"]) == {"pull_request"}
assert config["permissions"] == {"contents": "read"}
jobs = config["jobs"]
assert set(jobs) == {"build", "qualify"}
assert all(job["runs-on"] == "ubuntu-24.04" for job in jobs.values())
assert jobs["build"]["strategy"]["matrix"]["replica"] == ["one", "two"]
assert jobs["qualify"]["needs"] == "build"
for job in jobs.values():
    assert int(job["timeout-minutes"]) > 0
    for step in job["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"[\w/-]+@[a-f0-9]{40}", step["uses"])
        if step.get("uses", "").startswith("actions/checkout@"):
            assert step["with"]["persist-credentials"] == "false"
        if step.get("uses", "").startswith("actions/upload-artifact@"):
            assert 1 <= int(step["with"]["retention-days"]) <= 7
assert json.loads(plan.read_text())["gates"]["release"]["applicability"] == "not_applicable"
build = (recipe / "build.sh").read_text()
patch_digest = hashlib.sha256((recipe / "native-proof.patch").read_bytes()).hexdigest()
assert build.count(patch_digest) == 2
assert "--network=none" in build and "--release --locked --offline" in build
assert "-C linker-flavor=ld" in build and "linker-flavor=gnu-lld" not in build
assert build.index("        /work/link-probe\n") < build.index("cargo build --release")
subprocess.run(["bash", "-n", recipe / "build.sh"], check=True)
for path in recipe.glob("*.py"):
    compile(path.read_bytes(), str(path), "exec")
