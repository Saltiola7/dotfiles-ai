"""Adapter v2 contracts use the real core and disposable native identities."""
import json
import sqlite3

import pytest
import test_opencode_continuation as legacy
import test_dbsctr_checkout_continuation as v2core

cycle = legacy.cycle
adapter = legacy.adapter


def run(adapter, script):
    result = legacy.bun(adapter, script)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_v2_capability_is_separate_from_enrollment_and_qualification(adapter):
    before = adapter.record_path().read_bytes()
    value = run(adapter, 'console.log(JSON.stringify(await control.preflight(context,root)));')
    assert value['adapter_revision'] == 'checkout-continuation-opencode-2'
    assert value['capabilities'] == {'protocol': 2, 'bind': True, 'recover': True, 'release': True}
    assert 'qualified' not in value and 'local_target' not in value
    assert not adapter.continuation_path.exists()
    assert adapter.record_path().read_bytes() == before


def test_v2_invalid_legacy_target_diagnostics_and_release(adapter):
    legacy.core.enroll(adapter)
    record = json.loads(adapter.record_path().read_text())
    (adapter.repo / '.git/dbsctr/worktrees' / record['worktree']['id'] / 'active').unlink()
    value = run(adapter, '''
for (const tool of ["dbsctr_inspect","dbsctr_audit","dbsctr_status"])
  await hooks["tool.execute.before"]({tool,sessionID:"owner",callID:"call-owner"},{args:{}});
const status=await control.diagnosticStatus(context);
const released=await control.release(context);
const after=await control.preflight(context);
console.log(JSON.stringify({status:JSON.parse(status),released,after}));
''')
    assert value['status']['checks']['target']['status'] == 'unavailable'
    assert value['released']['writer_relation'] == 'none'
    assert value['after']['next_action'] == 'select_target'
    assert 'local_target' not in value['released']


def test_v2_bind_attach_write_finish_and_release(adapter):
    value = run(adapter, '''
const asks=[];context.ask=async req=>asks.push(req.permission);
const bound=await control.bind(context,root);
const attached=await control.attach({...context,callID:"attach-call"},root,"writer");
const input={tool:"write",sessionID:"owner",callID:"call-owner"};
const args={filePath:root+"/candidate.txt",content:"candidate"};
await hooks["tool.execute.before"](input,{args});
await hooks["tool.execute.after"]({...input,args},{output:"written",metadata:{},title:""});
const released=await control.release({...context,callID:"release-call"});
console.log(JSON.stringify({bound,attached,released,asks,target:runtime.cycleTarget("owner","home")}));
''')
    assert value['bound']['binding_id']
    assert value['attached']['writer_relation'] == 'self'
    assert value['released']['generation'] > value['attached']['generation']
    assert value['asks'] == ['dbsctr_continuation_enroll']
    assert value['target'] == 'home'


def test_v2_legacy_uncertainty_requires_native_consent_before_release(adapter):
    legacy.core.enroll(adapter)
    op = legacy.core.call(adapter, 'admit', generation=1, call_id='uncertain', operation_class='file')
    legacy.core.call(adapter, 'finish', operation_id=op['operation_id'], outcome='uncertain')
    record = json.loads(adapter.record_path().read_text())
    (adapter.repo / '.git/dbsctr/worktrees' / record['worktree']['id'] / 'active').unlink()
    value = run(adapter, '''
const asks=[];context.ask=async req=>asks.push(req);
const recovered=await control.recover(context);
const released=await control.release({...context,callID:"release-call"});
console.log(JSON.stringify({recovered,released,asks}));
''')
    assert value['asks'][0]['permission'] == 'dbsctr_continuation_recover'
    assert json.loads(value['asks'][0]['patterns'][0])['action'] == 'recover'
    assert value['asks'][0]['metadata']['quiescenceRequired'] is True
    assert value['released']['writer_relation'] == 'none'


def test_v2_plan_does_not_request_mutating_consent(adapter):
    legacy.core.enroll(adapter)
    with sqlite3.connect(adapter.native_database) as db:
        db.execute("UPDATE session SET agent='plan' WHERE id='owner'")
    before = adapter.continuation_path.read_bytes()
    value = run(adapter, '''
const asks=[];context.ask=async req=>asks.push(req);
const failures=[];
for (const fn of [()=>control.bind(context,root),()=>control.recover(context),()=>control.release(context)]) {
  try {await fn();failures.push("unexpected success")} catch(error) {failures.push(error.message)}
}
console.log(JSON.stringify({asks,failures}));
''')
    assert not value['asks']
    assert all('switch_to_build' in error for error in value['failures'])
    assert adapter.continuation_path.read_bytes() == before


def test_v2_replayed_release_does_not_clear_newer_attachment(adapter):
    value = run(adapter, '''
context.ask=async()=>{};
await control.bind(context,root);
await control.attach({...context,callID:"first-attach"},root,"writer");
const releaseContext={...context,callID:"one-release"};
const first=await control.release(releaseContext);
const second=await control.attach({...context,callID:"second-attach"},root,"writer");
const replay=await control.release(releaseContext);
console.log(JSON.stringify({first,second,replay,target:runtime.cycleTarget("owner","home")}));
''')
    assert value['replay']['replayed']
    assert value['second']['route_version'] > value['first']['route_version']
    assert value['target'] == str(adapter.repo.resolve())


def test_v2_fixed_inspection_ignores_invalid_cached_target(adapter):
    legacy.core.enroll(adapter)
    record = json.loads(adapter.record_path().read_text())
    (adapter.repo / '.git/dbsctr/worktrees' / record['worktree']['id'] / 'active').unlink()
    value = run(adapter, '''
runtime.rememberCycleTarget("owner",root+"/missing-target");
await hooks["tool.execute.before"]({tool:"dbsctr_inspect",sessionID:"owner",callID:"call-owner"},{args:{}});
const cwd=await control.diagnosticRoot(context);
const result=JSON.parse(await runtime.fixedCommitInspect({action:"read",commit:"HEAD",path:"tracked.txt"},cwd));
console.log(JSON.stringify({cwd,result}));
''')
    assert value['cwd'] == str(adapter.repo)
    assert 'base' in json.dumps(value['result'])


def test_v2_bound_branch_drift_denies_write_but_preserves_release(adapter):
    v2core.bound_writer(adapter)
    v2core.git(adapter.repo, 'switch', '-c', 'changed')
    value = run(adapter, '''
let error="";
try {await hooks["tool.execute.before"]({tool:"write",sessionID:"owner",callID:"call-owner"},{args:{filePath:root+"/bad"}})}
catch(value) {error=value.message}
const released=await control.release(context);
console.log(JSON.stringify({error,released}));
''')
    assert value['error'] == 'continuation_branch_mismatch'
    assert value['released']['writer_relation'] == 'none'
    assert not (adapter.repo / 'bad').exists()


def test_v2_stale_approval_cannot_recover_changed_generation(adapter):
    legacy.core.enroll(adapter)
    value = run(adapter, '''
import {Database} from "bun:sqlite";
context.ask=async()=>{const db=new Database(root+"/.git/dbsctr/continuation/continuation.sqlite3");
  db.run("UPDATE cycles SET generation=generation+1");db.close()};
let error="";try {await control.recover(context)} catch(value) {error=value.message}
console.log(JSON.stringify({error}));
''')
    assert value['error'] == 'continuation_generation_changed'
    assert legacy.core.call(adapter)['writer_relation'] == 'self'


@pytest.mark.parametrize('change', [
    'value.extra="unknown"', 'value.generation=-1', 'value.writer_relation="assumed"',
    'value.checks.target={status:"available",reason:"secret"}',
    'value.local_target={path:root,binding_id:"a".repeat(32),registration_digest:"b".repeat(64)}',
])
def test_v2_response_validation_rejects_unsafe_projection(adapter, change):
    value = run(adapter, '''
const value=await control.requestV2(context,"check");
''' + change + ''';
let error="";try {control.validateV2(value,"check")} catch(value) {error=value.message}
console.log(JSON.stringify({error}));
''')
    assert value['error'] == 'continuation_invalid_response'


def test_v2_missing_helper_never_falls_back_to_legacy_mutation(adapter):
    legacy.core.enroll(adapter)
    executable = legacy.Path(adapter.temp.name) / 'bin/dbsctrctl'
    marker = legacy.Path(adapter.temp.name) / 'legacy-called'
    executable.write_text(f'#!{legacy.sys.executable}\nimport sys\nfrom pathlib import Path\n'
                          f'if sys.argv[1] != "continuation-v2": Path({str(marker)!r}).touch()\n'
                          'print("{}")\nraise SystemExit(1)\n')
    value = run(adapter, '''
let error="";try {await control.attach(context,root)} catch(value) {error=value.message}
const state=await control.preflight(context);
console.log(JSON.stringify({error,state}));
''')
    assert value['state']['capabilities']['protocol'] is None
    assert value['error'] == 'continuation_invalid_response'
    assert not marker.exists()


def test_v2_admission_cannot_refresh_a_stale_writer_generation(adapter):
    v2core.bound_writer(adapter)
    value = run(adapter, '''
import {Database} from "bun:sqlite";
const state=await control.executionState(context);
const target=await control.executionTarget(context,state);
const db=new Database(root+"/.git/dbsctr/continuation/continuation.sqlite3");
db.run("UPDATE cycles SET generation=generation+1");db.close();
let error="";try {await control.admit(context,state,target,"file")} catch(value) {error=value.message}
console.log(JSON.stringify({error}));
''')
    assert value['error'] == 'continuation_route_changed'
    with sqlite3.connect(adapter.continuation_path) as db:
        assert db.execute("SELECT count(*) FROM operations WHERE state='running'").fetchone() == (0,)


def test_v2_plan_keeps_explicit_reads_and_known_status(adapter):
    v2core.bound_writer(adapter)
    with sqlite3.connect(adapter.native_database) as db:
        db.execute("UPDATE session SET agent='plan' WHERE id='owner'")
    before = adapter.continuation_path.read_bytes()
    value = run(adapter, '''
const args={filePath:root+"/tracked.txt"};
await hooks["tool.execute.before"]({tool:"read",sessionID:"owner",callID:"call-owner"},{args});
const state=JSON.parse(await control.diagnosticStatus(context));
console.log(JSON.stringify({state,args}));
''')
    assert value['state']['cycle_id'] == 'cycle-1'
    assert value['state']['next_action'] == 'switch_to_build'
    assert adapter.continuation_path.read_bytes() == before


@pytest.mark.parametrize('bound', [False, True])
def test_failed_file_event_preserves_native_error_without_writer_recovery(adapter, bound):
    if bound:
        v2core.bound_writer(adapter)
    else:
        legacy.core.enroll(adapter)
    value = run(adapter, '''
await hooks["tool.execute.before"]({tool:"write",sessionID:"owner",callID:"call-owner"},
  {args:{filePath:root+"/tracked.txt"}});
const part={type:"tool",tool:"write",sessionID:"owner",callID:"call-owner",
  state:{status:"error",time:{start:10,end:20}}};
const {Database}=await import("bun:sqlite");
const db=new Database(process.env.HOME+"/.local/share/opencode/opencode.db");
db.query("UPDATE part SET data=? WHERE id='call-owner'").run(JSON.stringify(part));db.close();
await hooks.event({event:{type:"message.part.updated",properties:{part}}});
console.log(JSON.stringify(await control.preflight(context)));
''')
    assert value['state'] == 'owned' and value['generation'] == 1
    with sqlite3.connect(adapter.continuation_path) as db:
        assert db.execute('SELECT state,completion_class FROM operations').fetchall() == [('completed', 'native_error')]


def test_failed_file_manual_finish_survives_restart_for_legacy_cycle(adapter):
    legacy.core.enroll(adapter)
    op = legacy.core.call(adapter, 'admit', generation=1, call_id='call-owner', operation_class='file')
    with sqlite3.connect(adapter.native_database) as db:
        db.execute("UPDATE part SET data=? WHERE id='call-owner'", (json.dumps({
            'type': 'tool', 'tool': 'write', 'callID': 'call-owner',
            'state': {'status': 'error', 'time': {'start': 10, 'end': 20}}}),))
    value = run(adapter, f'console.log(JSON.stringify(await control.finishFailedFile(context,{json.dumps(op["operation_id"])})));')
    assert value['completion_class'] == 'native_error' and value['generation'] == 1
