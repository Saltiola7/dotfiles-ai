"""Qualify real native tools against a scripted loopback provider, never a model."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        names = {item["function"]["name"] for item in request.get("tools", [])}
        completed = sum(item.get("role") == "tool" for item in request.get("messages", []))
        index = completed - self.server.offset
        if names and 0 <= index < len(self.server.steps):
            name, arguments = self.server.steps[index]
            if name not in names:
                self.server.missing.add(name)
                delta, reason = {"content": "Required fixture tool missing."}, "stop"
            else:
                delta = {"tool_calls": [{"index": 0, "id": f"call_{self.server.phase}_{index}",
                    "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]}
                reason = "tool_calls"
        else:
            delta, reason = {"content": "Fixture complete."}, "stop"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for part, finish in (({"role": "assistant"}, None), (delta, None), ({}, reason)):
            self.wfile.write(("data: " + json.dumps({"id": "fixture", "object": "chat.completion.chunk",
                "created": 1, "model": "mock", "choices": [{"index": 0, "delta": part,
                "finish_reason": finish}]}) + "\n\n").encode())
        self.wfile.write(b"data: [DONE]\n\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    layout = parser.add_mutually_exclusive_group(required=True)
    layout.add_argument("--source", type=Path)
    layout.add_argument("--installed-root", type=Path)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--sdk-modules", type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    installed = args.installed_root.resolve() if args.installed_root else None
    source = args.source.resolve() if args.source else None
    helper_source = installed / ".local/bin/dbsctrctl" if installed else source / "dot_local/bin/executable_dbsctrctl"
    control_source = installed / ".config/opencode" if installed else source / "private_dot_config/opencode"
    with tempfile.TemporaryDirectory(prefix="continuation-native-", dir=args.scratch) as temporary:
        root = Path(temporary).resolve()
        repo, registry, home, binaries = (root / name for name in ("repo", "registry", "home", "bin"))
        for path in (repo, registry, home, binaries):
            path.mkdir()
        profile = repo / "docs/specs/test/README.md"
        profile.parent.mkdir(parents=True)
        profile.write_text("Synthetic continuation fixture profile.\n")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "-qm", "fixture"], cwd=repo, check=True)
        cycle = registry / "cycle"
        subprocess.run(["git", "worktree", "add", "-qb", "dbsctr/test/probe", str(cycle)], cwd=repo, check=True)
        helper = binaries / "dbsctrctl"
        helper.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(helper_source))} \"$@\"\n")
        helper.chmod(0o700)
        staged = home / "config/opencode"
        for name in ("lib/dbsctr-runtime.ts", "lib/continuation.ts", "plugins/continuation.ts", "tools/dbsctr.ts"):
            destination = staged / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(control_source / name, destination)
        if args.sdk_modules:
            for package in ("@opencode-ai/plugin", "@opencode-ai/sdk", "zod"):
                destination = staged / "node_modules" / package
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(args.sdk_modules / package, destination)
            version = json.loads((args.sdk_modules / "@opencode-ai/plugin/package.json").read_text())["version"]
            dependencies = {"@opencode-ai/plugin": version}
            (staged / "package.json").write_text(json.dumps({"private": True, "dependencies": dependencies}))
            packages = {"": {"dependencies": dependencies}}
            for package in ("@opencode-ai/plugin", "@opencode-ai/sdk", "zod"):
                metadata = json.loads((staged / "node_modules" / package / "package.json").read_text())
                packages["node_modules/" + package] = {key: metadata[key] for key in ("version", "dependencies") if key in metadata}
            (staged / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "requires": True, "packages": packages}))
        plan = root / "plan.json"
        gates = ("domain", "behavior", "spec", "contract", "test_driven_implementation", "refactor",
                 "review_integrate", "release", "deploy", "operate", "maintain_retire")
        plan.write_text(json.dumps({"profile": "docs/specs/test/README.md", "gates": {
            gate: {"applicability": "required"} for gate in gates}}))
        server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        server.missing = set()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        config = {
            "$schema": "https://opencode.ai/config.json", "model": "probe/mock", "small_model": "probe/mock",
            "enabled_providers": ["probe"], "permission": "allow",
            "plugin": [(staged / "plugins/continuation.ts").as_uri()],
            "provider": {"probe": {"npm": "@ai-sdk/openai-compatible", "name": "Loopback fixture",
                "options": {"baseURL": f"http://127.0.0.1:{server.server_port}/v1", "apiKey": "fixture"},
                "models": {name: {"name": name, "limit": {"context": 32000, "output": 1000}}
                           for name in ("mock", "mock-two")}}},
        }
        env = {"HOME": str(home), "PATH": f"{binaries}:{os.environ['PATH']}",
               "XDG_CONFIG_HOME": str(home / "config"), "XDG_DATA_HOME": str(home / "data"),
               "XDG_STATE_HOME": str(home / "state"), "XDG_CACHE_HOME": str(home / "cache"),
               "DBSCTR_WORKTREE_ROOT": str(registry), "OPENCODE_CONFIG_CONTENT": json.dumps(config),
               "npm_config_offline": "true", "npm_config_audit": "false", "npm_config_fund": "false",
               "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1", "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
               "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_MODELS_FETCH": "1"}
        if args.sdk_modules:
            env["NODE_PATH"] = str(args.sdk_modules.resolve())
        subprocess.run([str(helper), "start", "--cycle-id", "native-probe", "--context", "test",
                        "--risk", "critical", "--delivery-intent", "local", "--plan", str(plan)],
                       cwd=cycle, env=env, check=True, capture_output=True)
        completion = root / "complete_fixture.py"
        completion.write_text(
            "import json\nfrom pathlib import Path\n"
            f"common = Path({str(repo / '.git/dbsctr')!r})\n"
            "path = common / 'cycles/native-probe.json'\n"
            "record = json.loads(path.read_text())\n"
            "record.update(state='completed', completed_at=record['created_at'])\n"
            "path.write_text(json.dumps(record))\n"
            "(common / 'worktrees' / record['worktree']['id'] / 'active').unlink()\n"
            "print('fixture delivery completed')\n")
        session, total = None, 0
        try:
            for phase, model in (("initial", "mock"), ("resume", "mock-two"), ("reader", "mock"),
                                 ("completion", "mock-two")):
                server.phase, server.offset = phase, 0 if phase == "reader" else total
                marker = f"{phase}.txt"
                server.steps = [
                    ("dbsctr_attach", {"worktree": str(cycle), "mode": "reader" if phase == "reader" else "writer"}),
                    ("write", {"filePath": str(repo / marker), "content": "fixture\n"}),
                    ("bash", {"command": "git status --short", "description": "Verify fixture cycle cwd"}),
                    ("dbsctr_preflight", {}),
                ]
                if phase == "reader":
                    server.steps.pop(2)
                elif phase == "completion":
                    server.steps = [
                        ("bash", {"command": shlex.join([sys.executable, str(completion)]),
                                  "description": "Complete disposable cycle and remove its active pointer"}),
                        ("dbsctr_preflight", {}),
                    ]
                command = [str(binary), "run", "--print-logs", "--log-level", "DEBUG", "--model", f"probe/{model}", "--agent", "build", "--format", "json"]
                if session and phase != "reader":
                    command += ["--session", session]
                process = subprocess.Popen([*command, "Run the synthetic qualification."], cwd=repo, env=env,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    stdout, stderr = process.communicate(timeout=120)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                    raise RuntimeError("native_probe_timeout") from None
                events = []
                for line in stdout.splitlines():
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        continue
                identifiers = {event["sessionID"] for event in events if "sessionID" in event}
                parts = [event["part"] for event in events if event.get("type") == "tool_use"]
                failures = [re.findall(r"continuation_[a-z_]+", str(part.get("state", {}).get("error", "")))
                            for part in parts if part.get("state", {}).get("status") != "completed"]
                summary = {"phase": phase, "exit": process.returncode, "tool_count": len(parts),
                           "tool_failures": failures, "missing_tools": sorted(server.missing),
                           "canonical_untouched": not (repo / marker).exists(),
                           "cycle_written": (cycle / marker).exists(), "one_session": len(identifiers) == 1,
                           "same_session": session is None or identifiers == {session}}
                print(json.dumps(summary), flush=True)
                if process.returncode != 0:
                    print("native_initialization_failed", flush=True)
                assert process.returncode == 0 and len(parts) == len(server.steps) and not server.missing, "native_tool_contract"
                if phase == "reader":
                    assert len(failures) == 1 and "continuation_writer_occupied" in failures[0], "native_reader_denial"
                    assert summary["canonical_untouched"] and not summary["cycle_written"], "native_reader_write"
                    assert summary["one_session"] and not summary["same_session"], "native_reader_identity"
                elif phase == "completion":
                    assert not failures and summary["same_session"], "native_completion_failure"
                    output = parts[0]["state"]["output"]
                    assert "fixture delivery completed" in output and "execution selection released" in output, "native_completion_output"
                    assert json.loads(parts[1]["state"]["output"])["next_action"] == "select_target", "native_route_release"
                else:
                    assert not failures, "native_tool_failure"
                    assert summary["canonical_untouched"] and summary["cycle_written"], "native_write_target"
                    assert summary["one_session"] and summary["same_session"], "native_session_identity"
                    session = next(iter(identifiers))
                    total += len(parts)
            print("passed")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
