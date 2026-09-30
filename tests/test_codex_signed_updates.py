"""Synthetic update-policy tests; real native smoke is separate deployment evidence."""
import json
import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]

@pytest.fixture
def api():
    return runpy.run_path(str(ROOT / 'dot_local/bin/executable_codex-continuation'))


def test_legacy_runtime_keeps_exact_pin(api, monkeypatch):
    seen=[]
    monkeypatch.setitem(api['validate_native_executable'].__globals__, 'pinned_file', lambda v: seen.append(v))
    value={'path':'/legacy','sha256':'a'*64}
    assert api['validate_native_executable'](value) is None
    assert seen==[value]

@pytest.mark.parametrize('fault', ['policy','extra','digest','path','publisher','version','race'])
def test_signed_runtime_refuses_invalid_identity(api, tmp_path, monkeypatch, fault):
    ns=api['validate_native_executable'].__globals__
    binary=tmp_path/'codex';binary.write_bytes(b'one')
    value={'path':'/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex',
           'sha256':'a'*64,'verification':'openai-signed-v1'}
    if fault=='policy':value['verification']='trust-anything'
    if fault=='extra':value['extra']=True
    if fault=='digest':value['sha256']='wrong'
    if fault=='path':value['path']='/tmp/codex'
    monkeypatch.setitem(ns,'canonical_path',lambda *a,**k: binary)
    def run(argv, **kwargs):
        if fault=='publisher':raise subprocess.CalledProcessError(1,argv)
        if fault=='race':binary.write_bytes(b'changed')
        return subprocess.CompletedProcess(argv,0,b'codex-cli 0.159.0\n' if fault!='version' else b'garbage\n')
    monkeypatch.setattr(subprocess,'run',run)
    with pytest.raises((ValueError,api['NativeIdentityError'],subprocess.SubprocessError)):
        api['validate_native_executable'](value)


def test_signed_update_accepts_different_hash_and_records_actual(api,tmp_path,monkeypatch):
    ns=api['validate_native_executable'].__globals__;binary=tmp_path/'codex';binary.write_bytes(b'updated')
    monkeypatch.setitem(ns,'canonical_path',lambda *a,**k: binary)
    commands=[]
    def run(argv,**kwargs):
        commands.append(argv);return subprocess.CompletedProcess(argv,0,b'codex-cli 0.159.0\n')
    monkeypatch.setattr(subprocess,'run',run)
    result=api['validate_native_executable']({'path':'/Applications/ChatGPT.app/Contents/Resources/codex',
                                           'sha256':'a'*64,'verification':'openai-signed-v1'})
    assert result['sha256']!='a'*64 and result['version']=='0.159.0'
    assert commands[0][0]=='/usr/bin/codesign'
    assert '2DC432GLL2' in commands[0][3]


def test_only_exact_smoke_can_cross_update_gate(api):
    command=api['RUNTIME_SMOKE_COMMAND']
    assert api['is_runtime_smoke']({'command':command})
    for value in ({'command':command+'; touch file'}, {'command':command,'run_in_background':True},
                  {'command':command,'extra':True}, {'command':'echo arbitrary'}):
        assert not api['is_runtime_smoke'](value)

@pytest.fixture
def smoke_state(api,tmp_path):
    import contextlib,sqlite3
    from types import SimpleNamespace
    parent=tmp_path/'private';parent.mkdir(mode=0o700);(parent/'runtime').mkdir(mode=0o700)
    deployment={'conversation_id':'root','target':{'cycle_id':'business'}}
    runtime={'sha256':'c'*64,'version':'0.159.0'}
    receipt={'receipt_id':'d'*32,'tool':'shell','state':'completed','execution_started':True,
             'execution_finished':True,'deployment_digest':api['canonical_digest'](deployment),
             'identity':{'session_id':'root','call_id':'call'},'operation_id':'operation'}
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE operations(operation_id,cycle_id,state,completion_class,operation_class,session_key,message_id,call_id)')
    db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,?)',('operation','business','completed','native_completion','shell','actor','codex-'+receipt['receipt_id'],'call'))
    bridge=SimpleNamespace(repository_basis=tmp_path,cycle_id='business',session_key='actor',
                           core={'continuation_connection':lambda _:contextlib.nullcontext(db)})
    store=SimpleNamespace(read=lambda _:receipt)
    side={'receipt_id':receipt['receipt_id'],'deployment_digest':receipt['deployment_digest'],**runtime,'smoke':True}
    api['runtime_write'](parent/'runtime'/(receipt['receipt_id']+'.json'),side)
    api['runtime_write'](parent/'runtime'/(runtime['sha256']+'.proof.json'),{'receipt_id':receipt['receipt_id']})
    yield parent/'selected.json',deployment,store,bridge,runtime,receipt,db
    db.close()

@pytest.mark.parametrize('fault',[None,'missing','uncertain','unfinished','deployment','session','hash','not_smoke',
                                  'core_missing','core_pending','quiescence','core_call','core_actor','core_cycle'])
def test_only_matched_normal_smoke_completion_qualifies(api,smoke_state,fault):
    path,d,store,b,r,value,db=smoke_state
    if fault=='missing':(path.parent/'runtime'/(r['sha256']+'.proof.json')).unlink()
    elif fault=='uncertain':value['state']='uncertain'
    elif fault=='unfinished':value['execution_finished']=False
    elif fault=='deployment':value['deployment_digest']='other'
    elif fault=='session':value['identity']['session_id']='other'
    elif fault=='hash':r['sha256']='a'*64
    elif fault=='not_smoke':
        p=path.parent/'runtime'/(value['receipt_id']+'.json');v=json.loads(p.read_text());v['smoke']=False;p.write_text(json.dumps(v))
    elif fault=='core_missing':db.execute('DELETE FROM operations')
    elif fault=='core_pending':db.execute("UPDATE operations SET state='running'")
    elif fault=='quiescence':db.execute("UPDATE operations SET completion_class='operator_quiescence'")
    elif fault=='core_call':db.execute("UPDATE operations SET call_id='other'")
    elif fault=='core_actor':db.execute("UPDATE operations SET session_key='other'")
    elif fault=='core_cycle':db.execute("UPDATE operations SET cycle_id='other'")
    if fault in ('missing','hash'):assert not api['runtime_smoke_ready'](path,d,store,b,r)
    elif fault:
        with pytest.raises(api['NativeIdentityError']):api['runtime_smoke_ready'](path,d,store,b,r)
    else:assert api['runtime_smoke_ready'](path,d,store,b,r)


def test_runtime_admission_refuses_update_during_dispatch(api,smoke_state):
    path,d,store,b,r,value,db=smoke_state
    r['sha256']='a'*64
    with pytest.raises(api['NativeIdentityError'],match='runtime_changed'):
        api['runtime_admission'](path,d,value,r)

@pytest.mark.parametrize('kind',['symlink','public','overwrite'])
def test_runtime_evidence_custody(api,tmp_path,kind):
    private=tmp_path/'runtime';private.mkdir(mode=0o700);p=private/'proof.json'
    if kind=='symlink':
        target=tmp_path/'target';target.write_text('{}');p.symlink_to(target)
        with pytest.raises((ValueError,api['NativeIdentityError'])):api['runtime_json'](p)
    elif kind=='public':
        p.write_text('{}');p.chmod(0o644)
        with pytest.raises(api['NativeIdentityError']):api['runtime_json'](p)
    else:
        api['runtime_write'](p,{'proof':'retained'})
        with pytest.raises(FileExistsError):api['runtime_write'](p,{'proof':'replacement'})
        assert api['runtime_json'](p)=={'proof':'retained'}


def test_native_hook_denies_business_until_rewritten_smoke_and_post_completion(api,tmp_path,monkeypatch,capsys):
    import base64,contextlib,shlex,sqlite3
    ns=api['native_hook_response'].__globals__
    private=tmp_path/'private';private.mkdir(mode=0o700);(private/'runtime').mkdir(mode=0o700)
    path=private/'selected.json';store=api['NativeReceiptStore'](private/'native');store.initialize()
    deployment={'conversation_id':'root','conversation_home':str(tmp_path),'native_home':str(tmp_path),
                'native_executable':{'verification':'openai-signed-v1','path':'/unused','sha256':'a'*64},
                'producer':{'path':'/unused'},'target':{'cycle_id':'business','worktree':str(tmp_path)}}
    runtime={'sha256':'c'*64,'version':'0.159.0'}
    coredb=sqlite3.connect(':memory:');coredb.row_factory=sqlite3.Row
    coredb.execute('CREATE TABLE operations(operation_id,cycle_id,state,completion_class,operation_class,session_key,message_id,call_id)')
    thread={'id':'root','sessionId':'root','parentThreadId':None,'model':'model','modelProvider':'openai'}
    hook={'hook_event_name':'PreToolUse','tool_name':'Bash','session_id':'root','turn_id':'turn',
          'tool_use_id':'call-business','model':'model','permission_mode':'bypassPermissions','cwd':str(tmp_path),
          'tool_input':{'command':'touch never'}}
    class Bridge:
        def __init__(self,d,identity,receipt,s):
            self.repository_basis=tmp_path;self.cycle_id='business';self.session_key='actor';self.identity=identity
            self.message_id='codex-'+receipt;self.deployment_digest=api['canonical_digest'](d)
            self.core={'continuation_connection':lambda _:contextlib.nullcontext(coredb)}
        def verify_operation(self,operation):pass
        def call(self,command,**fields):
            if command=='check':return {'ok':True,'state':'owned','writer_relation':'self','next_action':'none','generation':7}
            if command=='admit':
                op='operation-'+self.identity['call_id']
                coredb.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,?)',(op,'business','running',None,'shell','actor',self.message_id,self.identity['call_id']))
                return {'ok':True,'operation_id':op}
            if command=='finish':
                coredb.execute("UPDATE operations SET state='completed',completion_class='native_completion' WHERE operation_id=?",(fields['operation_id'],))
                return {'ok':True}
            raise AssertionError(command)
    for name,value in {'configured_deployment':lambda:(path,deployment),'configured_store':lambda _:store,
        'validate_native_executable':lambda _:dict(runtime),'read_native_metadata':lambda *a:(thread,{'id':'turn'}),
        'selection_closed':lambda *a:False,'load_core':lambda _: {},'CoreBridge':Bridge}.items():monkeypatch.setitem(ns,name,value)
    def invoke():return api['native_hook_response'](json.dumps(hook).encode(),'root')
    assert invoke()['hookSpecificOutput']['permissionDecision']=='deny'
    hook['tool_use_id']='call-control';hook['tool_input']['command']='codex-continuation control check'
    assert invoke()['hookSpecificOutput']['permissionDecision']=='allow'
    hook['tool_use_id']='call-smoke';hook['tool_input']['command']=api['RUNTIME_SMOKE_COMMAND']
    command=invoke()['hookSpecificOutput']['updatedInput']['command'];args=shlex.split(command)
    assert json.loads(base64.b64decode(args[-1]))['command']==api['RUNTIME_SMOKE_PAYLOAD']
    assert not list((private/'runtime').glob('*.proof.json'))
    assert api['dispatch_shell'](args[-3],args[-1])==0
    hook['hook_event_name']='PostToolUse';assert invoke()=={}
    assert len(list((private/'runtime').glob('*.proof.json')))==1
    hook['hook_event_name']='PreToolUse';hook['tool_use_id']='call-after';hook['tool_input']['command']='printf business'
    assert invoke()['hookSpecificOutput']['permissionDecision']=='allow'
    coredb.close()

@pytest.mark.parametrize('fault',[None,'state_drift','candidate_drift','proof_drift','third_image'])
def test_policy_deployment_preserves_drift_and_has_exact_rollback(tmp_path,monkeypatch,fault):
    import contextlib,hashlib
    from types import SimpleNamespace
    manager=runpy.run_path(str(ROOT/'dot_local/bin/executable_codex-requalify'))
    ns=manager['deploy_signed_runtime'].__globals__
    parent=tmp_path/'private';parent.mkdir(mode=0o700);lane=tmp_path/'lane';lane.mkdir(mode=0o700)
    root=tmp_path/'source';(root/'dot_local/bin').mkdir(parents=True)
    for name in ('executable_codex-continuation','executable_dbsctrctl'):(root/'dot_local/bin'/name).write_bytes(name.encode())
    hooks=tmp_path/'hooks.json';hooks.write_bytes(b'old-hooks')
    production={'conversation_id':'root','native_home':str(tmp_path),'native_executable':{'path':'/native','sha256':'a'*64},
        'producer':{'path':'/old-producer','sha256':'b'*64},'core':{'path':'/old-core','sha256':'c'*64},'target':{'cycle_id':'business'}}
    before=json.dumps(production).encode();(parent/'selected.json').write_bytes(before)
    (lane/'selected.json').write_text(json.dumps(production));(lane/'restored.json').write_text('{}');(lane/'restore.complete.json').write_text('{}')
    selected=parent/'qualification';selected.symlink_to(lane)
    observed={'path':'/native','sha256':'d'*64,'version':'0.159.0'}
    checks={'candidate':0,'proof':0}
    def native(_):
        checks['candidate']+=1
        return {**observed,'sha256':'e'*64} if fault=='candidate_drift' and checks['candidate']>1 else dict(observed)
    def proof(*a):
        checks['proof']+=1
        return 'changed' if fault=='proof_drift' and checks['proof']>1 else 'proof'
    api={'unique_object':dict,'pinned_file':lambda _:None,'private_path':lambda *a,**kw:None,
         'load_core':lambda _: {},'validate_native_executable':native,'load_deployment':lambda p:json.loads(p.read_text()),
         'producer_lock':lambda _:contextlib.nullcontext(),'NativeReceiptStore':lambda _:None}
    monkeypatch.setitem(ns,'load_api',lambda _:api);monkeypatch.setitem(ns,'signed_runtime_source',lambda *a:root)
    monkeypatch.setitem(ns,'qualified_fixture',proof);monkeypatch.setitem(ns,'fixture_hooks',lambda *a:b'new-hooks')
    calls=[]
    def snapshot(*a):
        calls.append(1)
        if fault=='third_image' and len(calls)==3:hooks.write_bytes(b'concurrent-edit')
        return {'journal':'changed' if fault=='state_drift' and len(calls)==3 else 'original'}
    monkeypatch.setitem(ns,'production_snapshot',snapshot)
    monkeypatch.setitem(ns,'git_read',lambda *a:(_ for _ in ()).throw(subprocess.CalledProcessError(1,'git')))
    monkeypatch.setattr(Path,'home',lambda:SimpleNamespace(stat=lambda:SimpleNamespace(st_dev=-1)))
    directory=tmp_path/'deployment';args=SimpleNamespace(directory=directory,commit='e'*40)
    if fault:
        with pytest.raises(ValueError):manager['deploy_signed_runtime'](args,parent,selected)
        assert not (directory/'signed-runtime.complete.json').exists()
        if fault=='third_image':assert hooks.read_bytes()==b'concurrent-edit'
        elif fault=='state_drift':assert hooks.read_bytes()==b'old-hooks'
        else:assert (parent/'selected.json').read_bytes()==before and hooks.read_bytes()==b'old-hooks'
    else:
        manager['deploy_signed_runtime'](args,parent,selected)
        assert json.loads((parent/'selected.json').read_text())['native_executable']['verification']=='openai-signed-v1'
        assert (directory/'signed-runtime.complete.json').exists()
        manager['rollback_signed_runtime'](directory,parent)
        assert (parent/'selected.json').read_bytes()==before and hooks.read_bytes()==b'old-hooks'
    assert not list((parent/'runtime').glob('*.proof.json'))
