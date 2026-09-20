"""Native adapter boundary tests with actual helper and synthetic identity."""

import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest
import test_dbsctr_continuation as core

cycle = core.cycle
ROOT = Path(__file__).parents[1]
OC = ROOT / "private_dot_config/opencode"


@pytest.fixture
def adapter(cycle):
    binary = Path(cycle.temp.name) / "bin"
    binary.mkdir()
    executable = binary / "dbsctrctl"
    executable.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{core.fixtures.SCRIPT}" "$@"\n')
    executable.chmod(0o700)
    with sqlite3.connect(cycle.native_database) as db:
        db.execute("CREATE TABLE part (id TEXT PRIMARY KEY, session_id TEXT, message_id TEXT, data TEXT)")
        for name, session, message in (("call-owner", "owner", "owner-old"),
                                        ("call-reader", "reader", "reader-old"),
                                        ("call-plan", "plan", "plan-old"),
                                        ("call-child", "child", "child-old")):
            db.execute("INSERT INTO part VALUES (?,?,?,?)", (name, session, message,
                       json.dumps({"type": "tool", "callID": name, "tool": "write"})))
    cycle.adapter_env = {**cycle.continuation_env, "PATH": f"{binary}:{os.environ['PATH']}"}
    return cycle


def bun(adapter, script):
    prelude = f'''
import {{ Continuation }} from {json.dumps(str(OC / "plugins/continuation.ts"))};
import * as control from {json.dumps(str(OC / "lib/continuation.ts"))};
import * as runtime from {json.dumps(str(OC / "lib/dbsctr-runtime.ts"))};
const root={json.dumps(str(adapter.repo))};
const context={{worktree:root,directory:root,sessionID:"owner",messageID:"owner-old",callID:"call-owner"}};
const hooks=await Continuation({{worktree:root,directory:root}});
'''
    return subprocess.run([shutil.which("bun"), "-e", prelude + script], cwd=adapter.repo,
                          env=adapter.adapter_env, text=True, capture_output=True, timeout=30)


def test_adapter_preflight_does_not_enroll(adapter):
    result = bun(adapter, 'console.log(JSON.stringify(await control.preflight(context,root)));')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["reason"] == "not_enrolled"
    assert not adapter.continuation_path.exists()


def test_child_cannot_read_legacy_linked_worktree_outside_allocation_root(adapter):
    linked = Path(adapter.temp.name) / "legacy-linked"
    subprocess.run(["git", "worktree", "add", "-b", "legacy", str(linked)],
                   cwd=adapter.repo, check=True, capture_output=True)
    adapter.adapter_env["DBSCTR_WORKTREE_ROOT"] = str(Path(adapter.temp.name) / "new-allocation")
    result = bun(adapter, f'''
context.agentID="builder-openai";
await control.childRead(context,"read",{{filePath:root+"/tracked.txt"}});
try {{await control.childRead(context,"read",{{filePath:{json.dumps(str(linked / "tracked.txt"))}}})}}
catch(error) {{console.log(error.message)}};
''')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "continuation_child_external_read"


def test_adapter_enrollment_asks_exact_permission_and_restores_route(adapter):
    result = bun(adapter, '''
const approvals=[];
context.ask=async request=>approvals.push(request);
await control.attach(context,root,"writer");
await hooks["tool.execute.before"]({tool:"read",sessionID:"owner",callID:"call-owner"},{args:{filePath:root+"/tracked.txt"}});
console.log(JSON.stringify({approvals,target:runtime.cycleTarget("owner","wrong")}));
''')
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["target"] == str(adapter.repo.resolve())
    assert value["approvals"][0]["permission"] == "dbsctr_continuation_enroll"
    assert json.loads(value["approvals"][0]["patterns"][0])["action"] == "enroll"
    assert core.call(adapter)["writer_relation"] == "self"


def test_adapter_denied_enrollment_leaves_no_state(adapter):
    result = bun(adapter, '''
context.ask=async()=>{throw Error("denied")};
try {await control.attach(context,root,"writer")} catch(error) {console.log(error.message)};
''')
    assert result.returncode == 0, result.stderr
    assert "denied" in result.stdout
    assert not adapter.continuation_path.exists()


def test_adapter_readers_cannot_admit_writes(adapter):
    core.enroll(adapter)
    core.call(adapter, "attach", mode="reader", generation=1, session_id="reader", message_id="reader-old")
    result = bun(adapter, '''
try {await hooks["tool.execute.before"]({tool:"write",sessionID:"reader",callID:"call-reader"},{args:{filePath:root+"/tracked.txt"}})}
catch(error) {console.log(error.message)};
''')
    assert result.returncode == 0, result.stderr
    assert "writer_occupied" in result.stdout


def test_adapter_bash_environment_is_per_call_and_finishes(adapter):
    core.enroll(adapter)
    result = bun(adapter, '''
const input={tool:"bash",sessionID:"owner",callID:"call-owner"};
const args={command:"git status --short"};
await hooks["tool.execute.before"](input,{args});
const shell={env:{}};
await hooks["shell.env"]({cwd:root,sessionID:"owner",callID:"call-owner"},shell);
const inside=await runtime.withContinuationOperation(context,()=>runtime.run(["sh","-c","printf %s \\\"$DBSCTR_CONTINUATION_OPERATION\\\""],root));
const outside=await runtime.run(["sh","-c","printf %s \\\"$DBSCTR_CONTINUATION_OPERATION\\\""],root);
await hooks["tool.execute.after"]({...input,args},{metadata:{},output:"",title:""});
console.log(JSON.stringify({cwd:args.workdir,inside,outside,shell:shell.env.DBSCTR_CONTINUATION_OPERATION,global:process.env.DBSCTR_CONTINUATION_OPERATION??null}));
''')
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["cwd"] == str(adapter.repo.resolve())
    assert value["inside"] == value["shell"] and len(value["inside"]) == 32
    assert value["outside"] == ""
    assert value["global"] is None
    assert core.call(adapter)["next_action"] == "none"


@pytest.mark.parametrize("tool", ["unknown_mutator", "execute", "task", "mcp_write"])
def test_adapter_unqualified_mutators_fail_closed(adapter, tool):
    core.enroll(adapter)
    result = bun(adapter, f'''
try {{await hooks["tool.execute.before"]({{tool:{json.dumps(tool)},sessionID:"owner",callID:"call-owner"}},{{args:{{}}}})}}
catch(error) {{console.log(error.message)}};
''')
    assert result.returncode == 0, result.stderr
    assert "unqualified_tool" in result.stdout


def test_adapter_direct_shell_has_no_implicit_admission(adapter):
    core.enroll(adapter)
    result = bun(adapter, '''
try {await hooks["shell.env"]({cwd:root,sessionID:"owner",callID:"call-owner"},{env:{}})}
catch(error) {console.log(error.message)};
''')
    assert result.returncode == 0, result.stderr
    assert "unmediated_shell" in result.stdout


@pytest.mark.parametrize("name", ["../outside.txt", ".git/config", ".Git/config", "escape/file", "dangling"])
def test_adapter_rejects_escape_and_metadata_before_admission(adapter, name):
    core.enroll(adapter)
    (adapter.repo / "escape").symlink_to(Path(adapter.temp.name), target_is_directory=True)
    (adapter.repo / "dangling").symlink_to(Path(adapter.temp.name) / "missing-outside")
    result = bun(adapter, "const path=" + json.dumps(str(adapter.repo / name)) + ";" + '''
try {await hooks["tool.execute.before"]({tool:"write",sessionID:"owner",callID:"call-owner"},{args:{filePath:path}})}
catch(error) {console.log(error.message)};
''')
    assert result.returncode == 0, result.stderr
    assert "continuation_external_write" in result.stdout
    assert core.call(adapter)["next_action"] == "none"


def test_adapter_validates_every_patch_header_without_changing_content(adapter):
    core.enroll(adapter)
    patch = "*** Begin Patch\n*** Add File: new.txt\n+*** Update File: harmless-content\n*** End Patch\n"
    result = bun(adapter, f'''
const input={{tool:"apply_patch",sessionID:"owner",callID:"call-owner"}};
const args={{patchText:{json.dumps(patch)}}};
await hooks["tool.execute.before"](input,{{args}});
await hooks["tool.execute.after"]({{...input,args}},{{output:"",metadata:{{}},title:""}});
console.log(args.patchText);
''')
    assert result.returncode == 0, result.stderr
    assert f"*** Add File: {adapter.repo.resolve()}/new.txt" in result.stdout
    assert "+*** Update File: harmless-content" in result.stdout


def test_adapter_new_process_restores_route_and_does_not_borrow_environment(adapter):
    core.enroll(adapter)
    result = bun(adapter, '''
const input={tool:"read",sessionID:"owner",callID:"call-owner"};
await hooks["tool.execute.before"](input,{args:{filePath:root+"/tracked.txt"}});
runtime.rememberContinuationOperation({sessionID:"one",callID:"a"},"a".repeat(32));
runtime.rememberContinuationOperation({sessionID:"two",callID:"b"},"b".repeat(32));
const values=await Promise.all([
 runtime.withContinuationOperation({sessionID:"one",callID:"a"},async()=>{await Bun.sleep(10);return await runtime.run(["sh","-c","printf %s \\\"$DBSCTR_CONTINUATION_OPERATION\\\""],root)}),
 runtime.withContinuationOperation({sessionID:"two",callID:"b"},()=>runtime.run(["sh","-c","printf %s \\\"$DBSCTR_CONTINUATION_OPERATION\\\""],root)),
]);
console.log(JSON.stringify({target:runtime.cycleTarget("owner","wrong"),values}));
''')
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["target"] == str(adapter.repo.resolve())
    assert value["values"] == ["a" * 32, "b" * 32]


def test_adapter_missing_helper_returns_bounded_preflight(adapter):
    (Path(adapter.temp.name) / "bin/dbsctrctl").write_text("#!/bin/sh\nexit 1\n")
    result = bun(adapter, 'console.log(JSON.stringify(await control.preflight(context,root)));')
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["reason"] == "capability_unavailable"
    assert value["next_action"] == "qualify_runtime"


def test_adapter_no_route_does_not_authorize_recorded_cycle_write(adapter):
    core.enroll(adapter)
    result = bun(adapter, '''
try {await hooks["tool.execute.before"]({tool:"write",sessionID:"reader",callID:"call-reader"},{args:{filePath:root+"/tracked.txt"}})}
catch(error) {console.log(error.message)};
''')
    assert result.returncode == 0, result.stderr
    assert "continuation_attachment_required" in result.stdout


def test_adapter_completion_after_pointer_removal_preserves_output_and_releases_route(adapter):
    core.enroll(adapter)
    result = bun(adapter, '''
import {readFile,writeFile,unlink} from "node:fs/promises";
const input={tool:"bash",sessionID:"owner",callID:"call-owner"};
const args={command:"fixture final push"};
await hooks["tool.execute.before"](input,{args});
const path=root+"/.git/dbsctr/cycles/cycle-1.json";
const record=JSON.parse(await readFile(path,"utf8"));
record.state="completed";record.completed_at=record.created_at;
await writeFile(path,JSON.stringify(record));
await unlink(root+"/.git/dbsctr/worktrees/"+record.worktree.id+"/active");
const output={metadata:{},output:"draft_pr verified; pushed fixture commits",title:""};
await hooks["tool.execute.after"]({...input,args},output);
const check=await control.preflight(context);
console.log(JSON.stringify({output:output.output,check,target:runtime.cycleTarget("owner","home")}));
''')
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["output"].startswith("draft_pr verified; pushed fixture commits")
    assert "execution selection released" in value["output"]
    assert value["check"]["next_action"] == "select_target"
    assert value["target"] == "home"


def test_adapter_storage_and_writer_recovery_have_distinct_approvals(adapter):
    core.enroll(adapter)
    core.interrupt_storage(adapter)
    result = bun(adapter, '''
const approvals=[];
context.ask=async value=>approvals.push(value.permission);
const result=await control.recover(context,root);
console.log(JSON.stringify({approvals,result}));
''')
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["approvals"] == ["dbsctr_continuation_storage_recover", "dbsctr_continuation_recover"]
    assert value["result"]["state"] == "reader_only"
    assert value["result"]["generation"] == 2


def test_adapter_denied_storage_recovery_stays_read_only(adapter):
    core.enroll(adapter)
    core.interrupt_storage(adapter)
    before = adapter.continuation_path.read_bytes()
    result = bun(adapter, '''
context.ask=async()=>{throw Error("denied")};
try {await control.recover(context,root)} catch(error) {console.log(error.message)};
''')
    assert result.returncode == 0, result.stderr
    assert "denied" in result.stdout
    assert adapter.continuation_path.read_bytes() == before


def test_adapter_children_keep_local_reads_but_cannot_write(adapter):
    core.enroll(adapter)
    result = bun(adapter, '''
await hooks["tool.execute.before"]({tool:"read",sessionID:"child",callID:"call-child"},{args:{filePath:root+"/tracked.txt"}});
try {await hooks["tool.execute.before"]({tool:"write",sessionID:"child",callID:"call-child"},{args:{filePath:root+"/tracked.txt"}})}
catch(error) {console.log(error.message)};
''')
    assert result.returncode == 0, result.stderr
    assert "continuation_invalid_identity" in result.stdout


def test_adapter_plan_reads_without_mutation_authority(adapter):
    core.enroll(adapter)
    result = bun(adapter, '''
await hooks["tool.execute.before"]({tool:"read",sessionID:"plan",callID:"call-plan"},{args:{filePath:root+"/tracked.txt"}});
console.log("read permitted");
''')
    assert result.returncode == 0, result.stderr
    assert "read permitted" in result.stdout
