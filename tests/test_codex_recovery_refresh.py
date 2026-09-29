"""Synthetic recovery-refresh contract tests; never native qualification."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest


@pytest.fixture
def manager():
    return runpy.run_path(str(Path(__file__).parents[1] / 'dot_local/bin/executable_codex-requalify'))


@pytest.fixture
def pending():
    production = {'conversation_id': 'native-root', 'native_home': '/native',
                  'target': {'cycle_id': 'business'}}
    digest = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()
    actor = digest(['codex-desktop-1', '/native', 'native-root'])
    cycle = {'cycle_id': 'business', 'state': 'owned', 'generation': 5, 'writer': actor}
    operation = {'operation_id': 'operation', 'cycle_id': 'business', 'generation': 5,
                 'session_key': actor, 'operation_class': 'shell', 'state': 'running',
                 'message_id': 'codex-receipt', 'call_id': 'call', 'completion_class': None}
    receipt = {'receipt_id': 'receipt', 'operation_id': 'operation', 'session_id': 'native-root',
               'call_id': 'call', 'tool': 'shell', 'state': 'active',
               'deployment_digest': digest(production), 'execution_started': 0,
               'execution_finished': 0, 'identity_json': json.dumps({'session_id': 'native-root', 'call_id': 'call'})}
    return production, cycle, [operation], [receipt], [], digest


@pytest.mark.parametrize('fault', [None, 'started', 'finished', 'uncertain', 'extra_receipt',
    'extra_operation', 'foreign_writer', 'generation', 'message', 'call', 'session',
    'deployment', 'approved', 'prepared', 'operation_state', 'operation_class', 'completed',
    'cycle', 'identity', 'missing'])
def test_recovery_requires_one_exact_never_started_admission(manager, pending, fault):
    p, c, ops, receipts, approvals, digest = copy.deepcopy(pending)
    if fault == 'started': receipts[0]['execution_started'] = 1
    elif fault == 'finished': receipts[0]['execution_finished'] = 1
    elif fault == 'uncertain': receipts[0]['state'] = 'uncertain'
    elif fault == 'extra_receipt': receipts.append(dict(receipts[0]))
    elif fault == 'extra_operation': ops.append(dict(ops[0]))
    elif fault == 'foreign_writer': c['writer'] = 'foreign'
    elif fault == 'generation': ops[0]['generation'] = 4
    elif fault == 'message': ops[0]['message_id'] = 'other'
    elif fault == 'call': receipts[0]['call_id'] = 'other'
    elif fault == 'session': receipts[0]['session_id'] = 'other'
    elif fault == 'deployment': receipts[0]['deployment_digest'] = 'other'
    elif fault in ('approved', 'prepared'): approvals.append({'state': fault})
    elif fault == 'operation_state': ops[0]['state'] = 'uncertain'
    elif fault == 'operation_class': ops[0]['operation_class'] = 'file'
    elif fault == 'completed': ops[0]['completion_class'] = 'native'
    elif fault == 'cycle': ops[0]['cycle_id'] = 'other'
    elif fault == 'identity': receipts[0]['identity_json'] = json.dumps({'session_id': 'other', 'call_id': 'call'})
    elif fault == 'missing': receipts.clear()
    validate = manager['recovery_admission']
    if fault:
        with pytest.raises(ValueError): validate(p, c, ops, receipts, approvals, digest)
    else:
        assert validate(p, c, ops, receipts, approvals, digest) == {
            'cycle_id': 'business', 'generation': 5, 'operation_id': 'operation', 'receipt_id': 'receipt'}


class Terminal(io.StringIO):
    def isatty(self): return True


@pytest.mark.parametrize('fault', [None, 'agent', 'nonterminal', 'wrong', 'drift', 'replay'])
def test_recovery_approval_is_terminal_exact_and_one_use(manager, tmp_path, monkeypatch, fault):
    approval = manager['approve_recovery_refresh']
    for key in ('CODEX_THREAD_ID', 'OPENCODE_PID', 'OPENCODE_SESSION_ID'): monkeypatch.delenv(key, raising=False)
    if fault == 'agent': monkeypatch.setenv('CODEX_THREAD_ID', 'agent')
    plan = {'challenge': 'a'*32, 'snapshot': {'admission': {'cycle_id': 'business', 'generation': 5}},
            'hashes': {}, 'source_commit': 'b'*40}
    (tmp_path/'selection.after.json').write_text(json.dumps({'target':{}, 'producer':{}, 'core':{}, 'native_executable':{}}))
    calls = []
    def validate(*args):
        calls.append(1)
        if fault == 'drift' and len(calls) > 1: raise ValueError('production_state_drift')
        return plan, b'exact-plan'
    monkeypatch.setitem(approval.__globals__, 'validate_recovery_refresh', validate)
    if fault == 'replay': (tmp_path/'recovery.approved.json').write_text('{}')
    incoming = (io.StringIO if fault == 'nonterminal' else Terminal)(
        'wrong\n' if fault == 'wrong' else 'approve '+'a'*32+'\n')
    if fault:
        with pytest.raises((ValueError, FileExistsError)):
            approval(tmp_path, None, None, incoming, Terminal())
    else:
        approval(tmp_path, None, None, incoming, Terminal())
        recorded=json.loads((tmp_path/'recovery.approved.json').read_text())
        assert recorded == {'plan_sha256': hashlib.sha256(b'exact-plan').hexdigest(), 'challenge': 'a'*32}
        assert len(calls)==2


@pytest.mark.parametrize('fault', [None, 'current_generation', 'false_success', 'call', 'extra_pending'])
def test_snapshot_preserves_closed_history_but_refuses_unresolved_state(manager, pending, tmp_path, monkeypatch, fault):
    import contextlib
    import sqlite3
    p,c,ops,receipts,approvals,canonical=copy.deepcopy(pending)
    p['target'].update(worktree=str(tmp_path),common_git_dir=str(tmp_path))
    receipts[0]['deployment_digest']=canonical(p)
    c.update(locator_id='locator',worktree_id='worktree',record_digest='historical-enrollment-digest')
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    native=sqlite3.connect(':memory:');native.row_factory=sqlite3.Row
    def table(connection,name,row):
        connection.execute('CREATE TABLE '+name+' ('+','.join(row)+')')
        connection.execute('INSERT INTO '+name+' VALUES ('+','.join('?' for _ in row)+')',tuple(row.values()))
    table(db,'cycles',c);table(db,'operations',ops[0]);table(native,'receipts',receipts[0])
    native.execute('CREATE TABLE operator_approvals(state)')
    old=dict(ops[0],operation_id='old',generation=3,state='completed',completion_class='operator_quiescence',message_id='codex-old',call_id='old-call')
    if fault=='current_generation':old['generation']=5
    elif fault=='false_success':old['completion_class']='native'
    elif fault=='call':old['call_id']='different'
    elif fault=='extra_pending':old.update(state='running',completion_class=None)
    db.execute('INSERT INTO operations VALUES ('+','.join('?' for _ in old)+')',tuple(old.values()))
    historic=dict(receipts[0],receipt_id='old',operation_id='old',call_id='old-call',execution_started=1)
    native.execute('INSERT INTO receipts VALUES ('+','.join('?' for _ in historic)+')',tuple(historic.values()))
    (tmp_path/'cycles').mkdir();(tmp_path/'cycles/business.json').write_text(json.dumps({'cycle_id':'business','state':'active','worktree':{'id':'worktree'}}))
    (tmp_path/'native').mkdir();(tmp_path/'native/native.sqlite3').write_bytes(b'unchanged native history')
    (tmp_path/'core.sqlite3').write_bytes(b'unchanged core history')
    api={'IDENTIFIER':__import__('re').compile('[A-Za-z0-9-]+'),'unique_object':dict,
         'canonical_path':lambda v,**_:Path(v),'canonical_digest':canonical,
         'NativeReceiptStore':lambda _:SimpleNamespace(connection=lambda:contextlib.nullcontext(native))}
    core={'common_git_dir':lambda _:tmp_path,'cycle_dir':lambda _:tmp_path,'worktree_id':lambda _:'locator',
          'continuation_connection':lambda _:contextlib.nullcontext(db),'continuation_path':lambda _:tmp_path/'core.sqlite3'}
    monkeypatch.setitem(manager['recovery_snapshot'].__globals__,'git_read',lambda *args:b'git-evidence')
    before=list(native.execute('SELECT * FROM receipts'))
    try:
        if fault:
            with pytest.raises(ValueError):manager['recovery_snapshot'](tmp_path,p,api,core)
        else:
            snapshot=manager['recovery_snapshot'](tmp_path,p,api,core)
            assert snapshot['admission']['operation_id']=='operation'
        assert list(native.execute('SELECT * FROM receipts'))==before
    finally:db.close();native.close()


@pytest.fixture
def recovery_transaction(manager, tmp_path, monkeypatch):
    import contextlib
    directory=tmp_path/'transaction';directory.mkdir()
    selection=tmp_path/'selection';hooks=tmp_path/'hooks'
    selection.write_bytes(b'old selection');hooks.write_bytes(b'old hooks')
    files=[(selection,b'old selection',b'new selection','selection'),(hooks,b'old hooks',b'new hooks','hooks')]
    baseline={'admission':'pending'};plan={'challenge':'a'*32,'snapshot':baseline};raw=b'plan'
    api={'producer_lock':lambda _:contextlib.nullcontext(),'NativeReceiptStore':lambda _:None}
    def context(*args,**kwargs):return plan,raw,api,files,lambda:dict(baseline)
    monkeypatch.setitem(manager['apply_recovery_refresh'].__globals__,'recovery_plan_context',context)
    manager['json_new'](directory/'recovery.approved.json',{'plan_sha256':hashlib.sha256(raw).hexdigest(),'challenge':'a'*32})
    return directory,selection,hooks,plan,raw,api,files,baseline


def test_recovery_apply_consumes_once_and_exact_rollback(manager,recovery_transaction):
    d,selection,hooks,*_=recovery_transaction
    manager['apply_recovery_refresh'](d,d,None)
    assert selection.read_bytes()==b'new selection' and hooks.read_bytes()==b'new hooks'
    with pytest.raises(ValueError,match='consumed'):manager['apply_recovery_refresh'](d,d,None)
    manager['rollback_recovery_refresh'](d,d,None)
    assert selection.read_bytes()==b'old selection' and hooks.read_bytes()==b'old hooks'
    assert (d/'recovery.consumed.json').exists()


def test_recovery_apply_stops_on_snapshot_drift(manager,recovery_transaction,monkeypatch):
    d,selection,hooks,plan,raw,api,files,baseline=recovery_transaction
    calls=[]
    def snapshot():
        calls.append(1)
        return dict(baseline) if len(calls)==1 else {'changed':True}
    monkeypatch.setitem(manager['apply_recovery_refresh'].__globals__,'recovery_plan_context',
                        lambda *a,**k:(plan,raw,api,files,snapshot))
    with pytest.raises(ValueError,match='production_state_drift'):manager['apply_recovery_refresh'](d,d,None)
    assert selection.read_bytes()==b'new selection' and hooks.read_bytes()==b'old hooks'
    assert (d/'recovery.consumed.json').exists()
    assert not (d/'recovery.complete.json').exists()


def test_recovery_apply_refuses_approval_for_another_plan(manager,recovery_transaction):
    d,selection,hooks,*_=recovery_transaction
    (d/'recovery.approved.json').write_text('{}')
    with pytest.raises(ValueError,match='approval_required'):manager['apply_recovery_refresh'](d,d,None)
    assert selection.read_bytes()==b'old selection' and hooks.read_bytes()==b'old hooks'
    assert not (d/'recovery.consumed.json').exists()


def test_recovery_rollback_preserves_concurrent_hook_edit(manager,recovery_transaction):
    d,selection,hooks,*_=recovery_transaction
    manager['apply_recovery_refresh'](d,d,None)
    hooks.write_bytes(b'concurrent edit')
    with pytest.raises(ValueError,match='refresh_file_drift'):manager['rollback_recovery_refresh'](d,d,None)
    assert hooks.read_bytes()==b'concurrent edit' and selection.read_bytes()==b'new selection'


@pytest.fixture
def prepared_plan(manager,tmp_path,monkeypatch):
    import re
    directory=tmp_path/'deployment';directory.mkdir();lane=tmp_path/'lane';lane.mkdir()
    parent=tmp_path/'management';parent.mkdir();selected=parent/'qualification';selected.symlink_to(lane)
    home=tmp_path/'home';home.mkdir()
    production={'conversation_id':'root','conversation_home':'/conversation','native_home':str(home),
                'native_executable':{'path':'/native','sha256':'old'},'producer':{'path':'/old/producer','sha256':'p'},
                'core':{'path':'/old/core','sha256':'c'},'target':{'common_git_dir':'/business','cycle_id':'business'}}
    qualified=copy.deepcopy(production);qualified['target']['common_git_dir']='/fixture'
    qualified['native_executable']['sha256']='new'
    hooks={'hooks':{event:[{'matcher':matcher,'hooks':[{'type':'command','command':'python /old/producer hook --conversation root'}]}]
                   for event,matcher in [('PreToolUse','^(Bash|apply_patch|Edit|Write|mcp__.*)$'),('PostToolUse','^Bash$')]}}
    before=json.dumps(production).encode();hook_before=json.dumps(hooks).encode()
    after=json.dumps(manager['refresh_descriptor'](production,qualified,directory)).encode()
    hook_after=manager['fixture_hooks'](hook_before,production,directory/'executable_codex-continuation')
    raw={'selection.before.json':before,'selection.after.json':after,'hooks.before.json':hook_before,'hooks.after.json':hook_after}
    for n,v in raw.items():(directory/n).write_bytes(v)
    (parent/'selected.json').write_bytes(before);(home/'hooks.json').write_bytes(hook_before)
    (lane/'production.before.json').write_bytes(before);(lane/'hooks.before.json').write_bytes(hook_before)
    digest=manager['digest'];(lane/'restored.json').write_text(json.dumps({'production_sha256':digest(before),'hooks_sha256':digest(hook_before)}))
    (lane/'restore.complete.json').write_text(json.dumps({'after_sha256':digest(hook_before)}))
    plan={'schema_version':1,'kind':'never_started_recovery_refresh','challenge':'a'*32,'lane':str(lane),
          'directory':str(directory),'source_commit':'b'*40,'qualification_sha256':'proof','snapshot':{'state':'bound'},
          'hashes':{n:digest(v) for n,v in raw.items()}}
    (directory/'recovery.plan.json').write_text(json.dumps(plan))
    api={'canonical_path':lambda v,**k:Path(v),'private_path':lambda *a,**k:None,'unique_object':dict,
         'RECEIPT_ID':re.compile('[0-9a-f]{32}'),'load_deployment':lambda p:json.loads(p.read_text())}
    calls=[]
    def components(parent,selected,prod,commit):
        assert prod==production;calls.append(commit)
        return api,lane,qualified,{},'proof'
    scope=manager['recovery_plan_context'].__globals__
    monkeypatch.setitem(scope,'load_api',lambda _:api)
    monkeypatch.setitem(scope,'recovery_components',components)
    monkeypatch.setitem(scope,'recovery_snapshot',lambda *a:{'state':'bound'})
    monkeypatch.setitem(scope,'qualified_fixture',lambda *a:'proof')
    return directory,parent,selected,lane,home,plan,calls


@pytest.mark.parametrize('fault',[None,'selection','hooks','plan_hash','qualification','restoration','after_target','snapshot','consumed','unknown_kind','lane'])
def test_prepared_recovery_revalidates_every_bound_preimage(manager,prepared_plan,fault):
    d,parent,selected,lane,home,plan,calls=prepared_plan
    if fault=='selection':(parent/'selected.json').write_bytes(b'changed')
    elif fault=='hooks':(home/'hooks.json').write_bytes(b'changed')
    elif fault=='plan_hash':plan['hashes']['hooks.after.json']='wrong'
    elif fault=='qualification':plan['qualification_sha256']='wrong'
    elif fault=='restoration':(lane/'restored.json').unlink()
    elif fault=='after_target':
        path=d/'selection.after.json';value=json.loads(path.read_text());value['target']['cycle_id']='other';path.write_text(json.dumps(value));plan['hashes']['selection.after.json']=manager['digest'](path.read_bytes())
    elif fault=='snapshot':plan['snapshot']={'state':'other'}
    elif fault=='consumed':(d/'recovery.consumed.json').write_text('{}')
    elif fault=='unknown_kind':plan['kind']='force'
    elif fault=='lane':plan['lane']=str(lane/'other')
    (d/'recovery.plan.json').write_text(json.dumps(plan))
    if fault:
        with pytest.raises((ValueError,FileNotFoundError)):manager['validate_recovery_refresh'](d,parent,selected)
    else:
        assert manager['validate_recovery_refresh'](d,parent,selected)[0]==plan
        assert calls==['b'*40]
