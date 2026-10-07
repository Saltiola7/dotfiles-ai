"""Exercise stock config migration, shell scanning and permission evaluation.

OPENCODE_NATIVE_CORE selects the already installed @opencode/core package used
for qualification. No packages are installed. This tests native policy primitives,
not interactive approval UI, actor authentication or deployed configuration.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from test_opencode_control_plane import DATA, OC, ROOT, rendered_config


@pytest.mark.skipif(not os.environ.get("OPENCODE_NATIVE_CORE"), reason="native OpenCode core authority not selected")
@pytest.mark.parametrize("projected", [False, True])
def test_stock_permission_engine_respects_native_role_boundaries(tmp_path, projected):
    package = Path(os.environ["OPENCODE_NATIVE_CORE"]).resolve(strict=True)
    assert json.loads((package / "package.json").read_text())["version"] == "2.0.21"
    modules = {name: str(package / "dist" / path) for name, path in {
        "migration": "v1/config/migrate.js", "permission": "permission.js",
        "shell": "shell/parse.js", "markdown": "config/markdown.js",
    }.items()}
    effect = package.parent.parent / "effect/dist/index.js"
    cases = [
        ["build", "dbsctrctl begin --plan fixture.json", ["allow"]],
        ["plan", "dbsctrctl status --json", ["allow"]],
        ["plan", "dbsctrctl start --cycle-id fixture", ["deny"]],
        ["plan", "dbsctrctl record-evidence domain --authority fixture -- true", ["deny"]],
        ["plan", "dbsctr-rnd reserve", ["deny"]],
        ["plan", "wt list --format=json", ["allow"]],
        ["plan", "wt switch --create fixture", ["deny"]],
        ["build", "wt remove fixture", ["ask"]],
        ["build", "wt -C /tmp/fixture remove fixture", ["ask"]],
        ["build", "wt remove fixture --force", ["deny"]],
        ["build", "wt remove fixture --no-hooks", ["deny"]],
        ["build", "wt --config fixture.toml remove fixture", ["deny"]],
        ["build", "wt -C /tmp/fixture remove fixture --no-hooks", ["deny"]],
        ["plan", "wt list --config fixture.toml", ["deny"]],
        ["discovery-coordinator", "wt list --config fixture.toml", ["deny"]],
        ["build", "agent-worktree --override-busy -- codex", ["deny"]],
        ["build", "dbsctrctl knowledge-export", ["deny"]],
        ["discovery-coordinator", "dbsctrctl begin --plan fixture.json --preflight", ["allow"]],
        ["discovery-coordinator", "dbsctrctl set-gate domain --result passed", ["deny"]],
        ["builder-openai", "dbsctrctl begin --plan fixture.json", ["deny"]],
        ["builder-vertex", "dbsctr-rnd reserve", ["deny"]],
        ["builder-openai", "dksctl export", ["deny"]],
        ["reviewer-openai", "dbsctrctl status", ["deny"]],
        ["plan", "dbsctrctl status --json; dbsctrctl start --cycle-id fixture", ["allow", "deny"]],
    ]
    config = rendered_config()
    if projected:
        target = tmp_path / ".config/opencode/opencode.json"
        target.parent.mkdir(parents=True)
        target.write_text("{}\n")
        applied = subprocess.run(["chezmoi", "-S", str(ROOT), "-D", str(tmp_path),
                        "--config", "/dev/null", "--config-format", "toml",
                        "--override-data", json.dumps(DATA), "--cache", str(tmp_path / "cache"),
                        "--persistent-state", str(tmp_path / "state"), "apply", str(target)],
                       capture_output=True, text=True, timeout=30)
        assert applied.returncode == 0, applied.stderr
        config = json.loads(target.read_text())
    payload = {"config": config, "cases": cases,
               "agents": {path.stem: path.read_text() for path in (OC / "agents").glob("*.md")}}
    script = f'''
import {{ConfigMigrateV1}} from {json.dumps(modules['migration'])};
import {{Permission}} from {json.dumps(modules['permission'])};
import {{ShellParse}} from {json.dumps(modules['shell'])};
import {{ConfigMarkdown}} from {json.dumps(modules['markdown'])};
import {{Effect}} from {json.dumps(str(effect))};
import assert from "node:assert/strict";
const input=await new Response(Bun.stdin.stream()).json();
const config=ConfigMigrateV1.migrate(input.config);
const agents={{...config.agents}};
for (const [id, text] of Object.entries(input.agents)) {{
  const markdown=ConfigMarkdown.parseOption(text);
  assert(markdown);
  agents[id]=ConfigMigrateV1.migrateAgent({{...markdown.data,prompt:markdown.content}});
}}
for (const [id, command, expected] of input.cases) {{
  assert(agents[id]);
  const parsed=await Effect.runPromise(ShellParse.scan(command,"/bin/bash",process.cwd()));
  const actual=parsed.commands.map(item=>Permission.evaluate("shell",item.resource,
    config.permissions ?? [],agents[id].permissions ?? []).effect);
  assert.deepEqual(actual,expected,`native policy case: ${{id}} / ${{command}}`);
}}
console.log(JSON.stringify({{cases:input.cases.length,core:"2.0.21"}}));
'''
    environment = {"PATH": os.defpath, "HOME": str(tmp_path), "OPENCODE_TEST_HOME": str(tmp_path),
                   "XDG_CONFIG_HOME": str(tmp_path / "config"), "XDG_DATA_HOME": str(tmp_path / "data"),
                   "XDG_STATE_HOME": str(tmp_path / "state"), "XDG_CACHE_HOME": str(tmp_path / "cache")}
    result = subprocess.run([shutil.which("bun"), "-e", script], input=json.dumps(payload),
                            cwd=tmp_path, env=environment, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"cases": len(cases), "core": "2.0.21"}
