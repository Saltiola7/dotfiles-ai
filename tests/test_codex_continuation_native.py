"""Synthetic native-identity conformance; never live admission evidence."""

import copy
import json
import runpy
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[1] / "dot_local/bin/executable_codex-continuation"


@pytest.fixture
def api():
    return runpy.run_path(str(SOURCE), run_name="test_native_adapter")


@pytest.fixture
def records():
    return (
        {
            "hook_event_name": "PreToolUse",
            "session_id": "root-1",
            "turn_id": "turn-1",
            "tool_use_id": "call-1",
            "model": "model-1@default",
            "permission_mode": "bypassPermissions",
            "tool_input": {"command": "SECRET"},
            "transcript_path": "/SECRET",
        },
        {
            "id": "root-1",
            "sessionId": "root-1",
            "parentThreadId": None,
            "model": "model-1@default",
            "modelProvider": "openai",
        },
        {"id": "turn-1", "status": "interrupted"},
    )


def test_native_identity_is_exact_and_content_free(api, records):
    before = copy.deepcopy(records)
    assert api["validate_native_identity"](*records) == {
        "session_id": "root-1",
        "turn_id": "turn-1",
        "call_id": "call-1",
        "model_id": "model-1@default",
        "provider_id": "openai",
        "agent_id": "build",
    }
    assert records == before


@pytest.mark.parametrize(
    "index,key,value",
    [
        (0, "hook_event_name", "PostToolUse"),
        (0, "permission_mode", "plan"),
        (0, "permission_mode", "invented"),
        (0, "session_id", "other-root"),
        (0, "turn_id", "child-turn"),
        (0, "model", "other-model"),
        (0, "tool_use_id", ""),
        (0, "tool_use_id", "/SECRET"),
        (0, "tool_use_id", "a" * 257),
        (0, "tool_use_id", True),
        (1, "sessionId", "other-session"),
        (1, "parentThreadId", "parent-root"),
        (1, "modelProvider", "other-provider"),
        (1, "modelProvider", None),
        (2, "id", "older-turn"),
    ],
    ids=["post", "plan", "unknown-mode", "session", "child", "model", "empty-call",
         "path-call", "long-call", "boolean-call", "thread-session", "parent",
         "provider", "missing-provider", "old-turn"],
)
def test_contradictory_native_identity_refuses(api, records, index, key, value):
    records[index][key] = value
    with pytest.raises(api["NativeIdentityError"], match="^invalid_identity$"):
        api["validate_native_identity"](*records)


@pytest.mark.parametrize("index,key", [(0, "model"), (0, "permission_mode"),
                                     (1, "parentThreadId"), (1, "sessionId"), (2, "id")])
def test_missing_native_facts_are_not_inferred(api, records, index, key):
    del records[index][key]
    with pytest.raises(api["NativeIdentityError"], match="^invalid_identity$"):
        api["validate_native_identity"](*records)


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("value", [None, [], "SECRET", 1])
def test_wrong_wire_shapes_refuse_safely(api, records, index, value):
    values = list(records)
    values[index] = value
    with pytest.raises(api["NativeIdentityError"], match="^invalid_identity$"):
        api["validate_native_identity"](*values)


def test_same_session_child_cannot_become_primary(api, records):
    records[0]["turn_id"] = "child-turn"
    records[0]["agent_id"] = "build"
    with pytest.raises(api["NativeIdentityError"]):
        api["validate_native_identity"](*records)


def test_stored_execution_status_is_not_used_as_live_authority(api, records):
    validator = api["validate_native_identity"]
    expected = validator(*records)
    for status in ("completed", "failed", "inProgress", "interrupted"):
        records[2]["status"] = status
        assert validator(*records) == expected


def fake_native(tmp_path, mode="normal"):
    executable = tmp_path / "native"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json,sys,time\n"
        f"mode={mode!r}\n"
        "assert sys.argv[1:]==['app-server','--stdio']\n"
        "for line in sys.stdin:\n"
        " r=json.loads(line); method=r['method']\n"
        " if method=='initialized': continue\n"
        " if mode=='hang': time.sleep(10); continue\n"
        " if mode=='oversize': print('x'*2100000,flush=True); continue\n"
        " if mode=='duplicate': print('{\"id\":1,\"id\":1,\"result\":{}}',flush=True); continue\n"
        " if method=='initialize': value={}\n"
        " elif method=='thread/read':\n"
        "  assert r['params']=={'threadId':'root-1','includeTurns':False}\n"
        "  value={'thread':{'id':'root-1','sessionId':'root-1','parentThreadId':None,"
        "'model':'model-1@default','modelProvider':'openai','preview':'SECRET','turns':[]}}\n"
        " elif method=='thread/turns/list':\n"
        "  assert r['params']=={'threadId':'root-1','limit':1,'sortDirection':'desc','itemsView':'notLoaded'}\n"
        "  value={'data':[{'id':'turn-1','status':'interrupted','items':[],'itemsView':'notLoaded'}]}\n"
        " else: raise AssertionError('unapproved_method')\n"
        " print(json.dumps({'id':r['id'],'result':value}),flush=True)\n"
    )
    executable.chmod(0o700)
    return executable


def test_supported_native_reads_are_bounded_and_return_metadata_only(api, tmp_path, records):
    executable = fake_native(tmp_path)
    thread, turn = api["read_native_metadata"](executable, tmp_path, "root-1", timeout=2)
    assert "SECRET" not in json.dumps([thread, turn])
    assert set(thread) == {"id", "sessionId", "parentThreadId", "model", "modelProvider"}
    assert turn == {"id": "turn-1"}
    assert api["validate_native_identity"](records[0], thread, turn)["agent_id"] == "build"


@pytest.mark.parametrize("mode", ["hang", "oversize", "duplicate"])
def test_native_protocol_failure_is_sanitized(api, tmp_path, mode):
    executable = fake_native(tmp_path, mode)
    with pytest.raises(api["NativeIdentityError"], match="^native_unavailable$") as error:
        api["read_native_metadata"](executable, tmp_path, "root-1", timeout=0.3)
    assert error.value.__context__ is None


def test_invalid_thread_selector_never_starts_native_process(api, tmp_path):
    with pytest.raises(api["NativeIdentityError"], match="^invalid_identity$"):
        api["read_native_metadata"](tmp_path / "nonexistent", tmp_path, "../SECRET")


def test_receipt_store_absent_read_creates_nothing(api, tmp_path):
    path = tmp_path / "private"
    assert api["NativeReceiptStore"](path).read("a" * 32) is None
    assert not path.exists()


def test_receipt_lifecycle_is_exact_and_monotone(api, tmp_path, records):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    identity = api["validate_native_identity"](*records)
    receipt = store.issue(identity, "shell", "0" * 64, deployment_digest="d" * 64)
    issued = store.read(receipt)
    assert issued["state"] == "issued" and issued["identity"] == identity
    assert issued["operation_id"] is None
    store.activate(receipt, "operation-1")
    assert store.read(receipt)["state"] == "active"
    store.finish(receipt, "operation-1", "completed")
    assert store.read(receipt)["state"] == "completed"
    with pytest.raises(api["NativeIdentityError"], match="^receipt_state$"):
        store.activate(receipt, "operation-2")
    with pytest.raises(api["NativeIdentityError"], match="^receipt_state$"):
        store.finish(receipt, "operation-2", "completed")


def test_uncertain_receipt_is_not_relabelled_completed(api, tmp_path, records):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    receipt = store.issue(api["validate_native_identity"](*records), "file", "1" * 64, deployment_digest="d" * 64)
    store.activate(receipt, "operation-1")
    store.finish(receipt, "operation-1", "uncertain")
    with pytest.raises(api["NativeIdentityError"], match="^receipt_state$"):
        store.finish(receipt, "operation-1", "completed")


def test_repeated_native_call_cannot_issue_another_receipt(api, tmp_path, records):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    identity = api["validate_native_identity"](*records)
    store.issue(identity, "shell", "2" * 64, deployment_digest="d" * 64)
    with pytest.raises(api["NativeIdentityError"], match="^receipt_replayed$"):
        store.issue(identity, "shell", "2" * 64, deployment_digest="d" * 64)


def test_receipt_store_rejects_symlink_and_public_permissions(api, tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(private, target_is_directory=True)
    with pytest.raises(api["NativeIdentityError"], match="^storage_invalid$"):
        api["NativeReceiptStore"](link).initialize()
    private.chmod(0o755)
    with pytest.raises(api["NativeIdentityError"], match="^storage_invalid$"):
        api["NativeReceiptStore"](private).initialize()


def test_receipt_identifier_is_not_a_path(api, tmp_path):
    with pytest.raises(api["NativeIdentityError"], match="^invalid_identity$"):
        api["NativeReceiptStore"](tmp_path / "private").read("../SECRET")


def test_direct_transition_cannot_invent_terminal_state(api, tmp_path, records):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    receipt = store.issue(api["validate_native_identity"](*records), "shell", "1" * 64, deployment_digest="d" * 64)
    store.activate(receipt, "operation-1")
    with pytest.raises(api["NativeIdentityError"], match="^receipt_state$"):
        store.transition(receipt, "operation-1", "invented")
    assert store.read(receipt)["state"] == "active"


def test_corrupt_journal_input_is_sanitized(api, tmp_path, records):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    receipt = store.issue(api["validate_native_identity"](*records), "shell", "1" * 64, deployment_digest="d" * 64)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE receipts SET identity_json=?", ("SECRET",))
    with pytest.raises(api["NativeIdentityError"], match="^storage_invalid$") as error:
        store.read(receipt)
    assert "SECRET" not in str(error.value)
    assert error.value.__context__ is None


def test_hardlinked_journal_refuses_before_mutation(api, tmp_path):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    (tmp_path / "alias").hardlink_to(store.path)
    before = store.path.read_bytes()
    with pytest.raises(api["NativeIdentityError"], match="^storage_invalid$"):
        store.initialize()
    assert store.path.read_bytes() == before


def test_completed_receipt_read_does_not_rewrite_journal(api, tmp_path, records):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    receipt = store.issue(api["validate_native_identity"](*records), "file", "1" * 64, deployment_digest="d" * 64)
    before = store.path.read_bytes()
    stamp = store.path.stat().st_mtime_ns
    assert store.read(receipt)["state"] == "issued"
    assert store.path.read_bytes() == before and store.path.stat().st_mtime_ns == stamp


def qualify(command, *, raw=None):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        [sys.executable, str(SOURCE), "qualify", "--nonce", "a" * 32],
        input=json.dumps(payload).encode() if raw is None else raw,
        capture_output=True, timeout=5,
    )


def test_native_canary_denies_only_exact_prepared_command():
    marker = "codex-continuation-deny-" + "a" * 32
    result = qualify(marker)
    assert result.returncode == 0 and result.stderr == b""
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert json.loads(qualify("echo " + marker).stdout) == {}


def test_native_canary_rewrites_only_fixed_harmless_printf():
    result = qualify("printf 'codex-continuation-original-" + "a" * 32 + "\\n'")
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision == {
        "hookEventName": "PreToolUse", "permissionDecision": "allow",
        "updatedInput": {"command": "printf 'codex-continuation-rewritten-" + "a" * 32 + "\\n'"},
    }
    assert json.loads(qualify("echo ordinary").stdout) == {}


@pytest.mark.parametrize("raw", [b'{"tool_name":"Bash","tool_name":"SECRET"}', b'"SECRET"', b'x'*1048577],
                         ids=["duplicate", "scalar", "oversize"])
def test_native_canary_malformed_input_refuses_without_echoing(raw):
    result = qualify("ignored", raw=raw)
    assert result.returncode == 0 and result.stderr == b""
    assert b"SECRET" not in result.stdout
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.fixture
def deployment(tmp_path):
    import hashlib
    root = tmp_path.resolve()
    repo = root / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    private = root / 'private'
    private.mkdir(mode=0o700)
    binary = root / 'native'
    binary.write_bytes(b'native fixture')
    producer = root / 'producer'
    producer.write_bytes(b'producer fixture')
    native_home = root / 'native-home'
    native_home.mkdir()
    value = {
        'schema_version': 1, 'revision': 'codex-desktop-1',
        'conversation_id': 'root-1', 'conversation_home': str(root),
        'native_home': str(native_home),
        'native_executable': {'path': str(binary), 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()},
        'producer': {'path': str(producer), 'sha256': hashlib.sha256(producer.read_bytes()).hexdigest()},
        'core': {'path': str(producer), 'sha256': hashlib.sha256(producer.read_bytes()).hexdigest()},
        'target': {'worktree': str(repo), 'common_git_dir': str(repo / '.git'), 'cycle_id': 'CYCLE-1'},
    }
    path = private / 'deployment.json'
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path, value


def test_deployment_preserves_real_non_repository_home(api, deployment):
    path, value = deployment
    assert api['load_deployment'](path) == value


@pytest.mark.parametrize('mutation', ['version', 'revision', 'extra', 'missing', 'digest',
                                      'sibling', 'common', 'symlink', 'mode', 'directory-mode',
                                      'duplicate', 'oversize'])
def test_deployment_refuses_unbound_inputs(api, deployment, mutation):
    path, value = deployment
    if mutation == 'version': value['schema_version'] = True
    elif mutation == 'revision': value['revision'] = 'future'
    elif mutation == 'extra': value['authority'] = True
    elif mutation == 'missing': del value['conversation_id']
    elif mutation == 'digest': value['producer']['sha256'] = '0' * 64
    elif mutation == 'sibling':
        other = path.parent.parent / 'other'
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        value['target']['worktree'] = str(other)
    elif mutation == 'common': value['target']['common_git_dir'] = value['conversation_home']
    elif mutation == 'symlink':
        link = path.parent.parent / 'linked'
        link.symlink_to(value['native_home'])
        value['native_home'] = str(link)
    elif mutation == 'mode': path.chmod(0o644)
    elif mutation == 'directory-mode': path.parent.chmod(0o755)
    path.write_text(json.dumps(value))
    if mutation == 'duplicate': path.write_text('{"schema_version":1,' + path.read_text()[1:])
    if mutation == 'oversize': path.write_text(' ' * 16385)
    with pytest.raises(api['NativeIdentityError'], match='^deployment_invalid$') as caught:
        api['load_deployment'](path)
    assert caught.value.__context__ is None
    assert str(path) not in str(caught.value)


def test_deployment_discards_git_environment_overrides(api, deployment, monkeypatch):
    path, value = deployment
    monkeypatch.setenv('GIT_DIR', '/does-not-exist')
    monkeypatch.setenv('GIT_WORK_TREE', '/does-not-exist')
    assert api['load_deployment'](path) == value


@pytest.mark.parametrize('column,value', [('identity_json', 'SECRET'), ('tool', 'invented'),
                                        ('argument_digest', 'bad'), ('session_id', 'other')])
def test_transition_refuses_corrupt_receipt_before_mutation(api, tmp_path, records, column, value):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    receipt = store.issue(api['validate_native_identity'](*records), 'shell', '1' * 64, deployment_digest="d" * 64)
    with sqlite3.connect(store.path) as connection:
        connection.execute(f'UPDATE receipts SET {column}=?', (value,))
    before = store.path.read_bytes()
    with pytest.raises(api['NativeIdentityError'], match='^storage_invalid$'):
        store.activate(receipt, 'operation-1')
    assert store.path.read_bytes() == before


def test_storage_budget_counts_all_sqlite_files(api, tmp_path):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    for suffix in ('-wal', '-shm'):
        path = Path(str(store.path) + suffix)
        with path.open('wb') as stream:
            stream.truncate(17 * 1024 * 1024)
        path.chmod(0o600)
    with pytest.raises(api['NativeIdentityError'], match='^storage_invalid$'):
        store.read('a' * 32)


@pytest.fixture
def native_call(records, deployment):
    hook, thread, turn = records
    hook.update(tool_name='Bash', cwd=deployment[1]['conversation_home'])
    hook['tool_input'] = {'command': 'printf ok', 'description': 'A harmless fixture', 'timeout': 1000}
    return hook, deployment[1], thread, turn


def test_native_call_envelope_retains_digests_not_command(api, native_call):
    import hashlib
    hook, deployment, _, _ = native_call
    value = api['validate_native_call'](*native_call)
    digest = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert value == {'identity': api['validate_native_identity'](hook, native_call[2], native_call[3]),
                     'deployment_digest': digest(deployment), 'tool': 'shell',
                     'argument_digest': digest(hook['tool_input'])}
    assert 'printf' not in json.dumps(value)


@pytest.mark.parametrize('mutation', ['other-session', 'other-home', 'file', 'background',
                                      'unknown-field', 'empty', 'large', 'boolean-timeout',
                                      'zero-timeout', 'large-description'])
def test_native_call_refuses_unqualified_transport(api, native_call, mutation):
    hook, deployment, _, _ = native_call
    if mutation == 'other-session': deployment['conversation_id'] = 'other'
    elif mutation == 'other-home': hook['cwd'] += '/sibling'
    elif mutation == 'file': hook['tool_name'] = 'Edit'
    elif mutation == 'background': hook['tool_input']['run_in_background'] = True
    elif mutation == 'unknown-field': hook['tool_input']['alternate_command'] = 'SECRET'
    elif mutation == 'empty': hook['tool_input']['command'] = ''
    elif mutation == 'large': hook['tool_input']['command'] = '\\' * 65536
    elif mutation == 'boolean-timeout': hook['tool_input']['timeout'] = True
    elif mutation == 'zero-timeout': hook['tool_input']['timeout'] = 0
    elif mutation == 'large-description': hook['tool_input']['description'] = 'a' * 4097
    with pytest.raises(api['NativeIdentityError'], match='^native_call_invalid$') as caught:
        api['validate_native_call'](*native_call)
    assert caught.value.__context__ is None


@pytest.fixture
def approval_binding():
    return {'action': 'recover', 'cycle_id': 'CYCLE-1', 'worktree_id': 'a' * 16,
            'generation': 3, 'state_digest': '1' * 64, 'record_digest': '2' * 64,
            'session_key': '3' * 64, 'activation_digest': '4' * 64,
            'target_session_id': None, 'mode': None}


def test_operator_challenge_requires_approval_and_consumes_once(api, tmp_path, approval_binding):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    challenge = store.prepare_approval(approval_binding, '5' * 64)
    with pytest.raises(api['NativeIdentityError'], match='^approval_required$'):
        store.consume_approval(challenge, approval_binding, '5' * 64)
    store.approve(challenge, approval_binding, '5' * 64)
    store.consume_approval(challenge, approval_binding, '5' * 64)
    with pytest.raises(api['NativeIdentityError'], match='^approval_required$'):
        store.consume_approval(challenge, approval_binding, '5' * 64)
    with pytest.raises(api['NativeIdentityError'], match='^approval_required$'):
        store.approve(challenge, approval_binding, '5' * 64)


@pytest.mark.parametrize('stage', ['approve', 'consume_approval'])
@pytest.mark.parametrize('changed', ['generation', 'state_digest', 'record_digest', 'activation_digest',
                                   'cycle_id', 'session_key', 'deployment'])
def test_operator_challenge_refuses_any_state_change(api, tmp_path, approval_binding, stage, changed):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    challenge = store.prepare_approval(approval_binding, '5' * 64)
    if stage == 'consume_approval': store.approve(challenge, approval_binding, '5' * 64)
    deployment_digest = '5' * 64
    if changed == 'deployment': deployment_digest = '6' * 64
    elif changed == 'generation': approval_binding[changed] += 1
    elif changed == 'cycle_id': approval_binding[changed] = 'CYCLE-2'
    else: approval_binding[changed] = '7' * 64
    before = store.path.read_bytes()
    with pytest.raises(api['NativeIdentityError'], match='^approval_required$'):
        getattr(store, stage)(challenge, approval_binding, deployment_digest)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize('key,value', [('action', 'handover'), ('generation', True),
                                      ('state_digest', 'bad'), ('target_session_id', 'other'),
                                      ('mode', 'writer')])
def test_operator_challenge_rejects_unsupported_binding(api, tmp_path, approval_binding, key, value):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    approval_binding[key] = value
    with pytest.raises(api['NativeIdentityError'], match='^approval_required$'):
        store.prepare_approval(approval_binding, '5' * 64)


def test_native_receipt_binds_full_deployment(api, tmp_path, records):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.initialize()
    receipt = store.issue(api["validate_native_identity"](*records), "shell", "1" * 64,
                          deployment_digest="d" * 64)
    assert store.read(receipt)["deployment_digest"] == "d" * 64
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE receipts SET deployment_digest='bad'")
    with pytest.raises(api["NativeIdentityError"], match="^storage_invalid$"):
        store.activate(receipt, "operation-1")


def test_approval_journal_refuses_prototype_version(api, tmp_path):
    store = api["NativeReceiptStore"](tmp_path / "private")
    store.directory.mkdir(mode=0o700)
    with sqlite3.connect(store.path) as connection:
        connection.executescript("CREATE TABLE metadata(version INTEGER); INSERT INTO metadata VALUES(1);")
    store.path.chmod(0o600)
    before = store.path.read_bytes()
    with pytest.raises(api["NativeIdentityError"], match="^storage_invalid$"):
        store.initialize()
    assert store.path.read_bytes() == before


@pytest.mark.parametrize('change', ['no-unique', 'column', 'trigger'])
def test_journal_version_cannot_hide_changed_schema(api, tmp_path, change):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    with sqlite3.connect(store.path) as connection:
        if change == 'trigger':
            connection.execute('CREATE TRIGGER extra AFTER INSERT ON receipts BEGIN DELETE FROM receipts; END')
        else:
            sql = connection.execute("SELECT sql FROM sqlite_master WHERE name='receipts'").fetchone()[0]
            connection.execute('DROP TABLE receipts')
            if change == 'no-unique': sql = sql.replace(',\n                        UNIQUE(session_id,turn_id,call_id)', '')
            else: sql = sql.replace('tool TEXT NOT NULL', 'tool BLOB NOT NULL')
            connection.execute(sql)
    before = store.path.read_bytes()
    with pytest.raises(api['NativeIdentityError'], match='^storage_invalid$'):
        store.initialize()
    assert store.path.read_bytes() == before


def test_prospective_database_limit_refuses_growth_before_commit(api, tmp_path, records):
    # Small capacity exercises identical page limit without a large fixture.
    api['NativeReceiptStore'].connection.__wrapped__.__globals__['MAX_DATABASE_BYTES'] = 32768
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    identity = api['validate_native_identity'](*records)
    last = None
    for index in range(100):
        identity['call_id'] = str(index) + 'x' * 240
        before = store.path.read_bytes()
        try:
            last = store.issue(identity, 'shell', '1' * 64, deployment_digest='d' * 64)
        except api['NativeIdentityError']:
            assert store.path.read_bytes() == before
            assert store.path.stat().st_size <= 32768
            assert last is not None and store.read(last)['state'] == 'issued'
            break
    else:
        pytest.fail('prospective capacity was never enforced')


def test_shell_execution_claim_is_single_use(api, tmp_path, records):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    receipt = store.issue(api['validate_native_identity'](*records), 'shell', '1' * 64,
                          deployment_digest='d' * 64)
    store.activate(receipt, 'operation-1')
    store.claim_execution(receipt, 'operation-1', '1' * 64, 'd' * 64)
    assert store.read(receipt)['execution_started'] is True
    assert store.read(receipt)['state'] == 'active'
    with pytest.raises(api['NativeIdentityError'], match='^receipt_state$'):
        store.claim_execution(receipt, 'operation-1', '1' * 64, 'd' * 64)


@pytest.mark.parametrize('wrong', ['operation', 'argument', 'deployment', 'tool', 'state'])
def test_shell_execution_substitution_does_not_consume_claim(api, tmp_path, records, wrong):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    receipt = store.issue(api['validate_native_identity'](*records), 'file' if wrong == 'tool' else 'shell',
                          '1' * 64, deployment_digest='d' * 64)
    store.activate(receipt, 'operation-1')
    if wrong == 'state': store.finish(receipt, 'operation-1', 'uncertain')
    before = store.path.read_bytes()
    with pytest.raises(api['NativeIdentityError'], match='^receipt_state$'):
        store.claim_execution(receipt, 'operation-2' if wrong == 'operation' else 'operation-1',
                              '2' * 64 if wrong == 'argument' else '1' * 64,
                              'e' * 64 if wrong == 'deployment' else 'd' * 64)
    assert store.path.read_bytes() == before
    assert store.read(receipt)['execution_started'] is False


def test_observation_is_content_free_and_never_issues_receipt(api, native_call):
    hook, deployment, thread, turn = native_call
    hook['tool_input']['command'] = 'echo SECRET'
    result = api['native_observation'](hook, deployment, thread, turn)
    assert result['result'] == 'qualified'
    assert result['cwd_matches_home'] is True
    assert result['input_types'] == {'command': 'str', 'description': 'str', 'timeout': 'int'}
    assert result['unknown_input_fields'] == 0
    serialized = json.dumps(result)
    for secret in ['SECRET', 'root-1', deployment['conversation_home'], 'receipt_id', 'operation_id']:
        assert secret not in serialized


def test_observation_unknown_fields_do_not_echo_names(api, native_call):
    native_call[0]['tool_input']['SECRET'] = 'SECRET'
    result = api['native_observation'](*native_call)
    assert result['result'] == 'native_call_invalid'
    assert result['unknown_input_fields'] == 1
    assert 'SECRET' not in json.dumps(result)


def test_observation_storage_is_private_bounded_and_exclusive(api, tmp_path, native_call):
    private = tmp_path / 'observation-private'
    private.mkdir(mode=0o700)
    result = api['native_observation'](*native_call)
    api['store_observation'](private, result)
    directory = private / 'observations'
    files = list(directory.glob("*.json"))
    assert len(files) == 1 and files[0].stat().st_mode & 0o077 == 0
    assert json.loads(files[0].read_text()) == result
    with pytest.raises(api['NativeIdentityError'], match='^observation_unavailable$'):
        api['store_observation'](private, result)
    assert len(list(directory.glob("*.json"))) == 1


def test_inspection_canary_qualifies_without_writer_calls(api, native_call, deployment, monkeypatch):
    hook, _, thread, turn = native_call
    namespace = api['inspect_response'].__globals__
    monkeypatch.setitem(namespace, 'read_native_metadata', lambda *args: (thread, turn))
    def forbidden(*args, **kwargs): raise AssertionError('writer primitive called')
    monkeypatch.setitem(namespace, 'NativeReceiptStore', forbidden)
    hook['tool_input'] = {'command': 'codex-continuation-inspect-' + 'a' * 32}
    result = api['inspect_response'](json.dumps(hook).encode(), deployment[0], 'a' * 32)
    assert result == {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                     'updatedInput': {'command': "printf 'codex-continuation-inspected-" + 'a' * 32 + "\\n'"}}}
    assert not list(deployment[0].parent.glob('*.sqlite3'))


def test_inspection_plan_canary_is_denied(api, native_call, deployment, monkeypatch):
    hook, _, thread, turn = native_call
    monkeypatch.setitem(api['inspect_response'].__globals__, 'read_native_metadata', lambda *args: (thread, turn))
    hook['permission_mode'] = 'plan'
    hook['tool_input'] = {'command': 'codex-continuation-inspect-' + 'a' * 32}
    result = api['inspect_response'](json.dumps(hook).encode(), deployment[0], 'a' * 32)
    assert result['hookSpecificOutput']['permissionDecision'] == 'deny'


def test_inspection_different_conversation_creates_nothing(api, native_call, deployment):
    hook = native_call[0]
    hook['session_id'] = 'other'
    assert api['inspect_response'](json.dumps(hook).encode(), deployment[0], 'a' * 32) == {}
    assert not (deployment[0].parent / 'observations').exists()


@pytest.mark.parametrize('failure', ['descriptor', 'capacity'])
def test_inspection_failures_never_block_ordinary_calls(api, native_call, deployment, monkeypatch, failure):
    hook, _, thread, turn = native_call
    namespace = api['inspect_response'].__globals__
    monkeypatch.setitem(namespace, 'read_native_metadata', lambda *args: (thread, turn))
    def refuse(*args): raise api['NativeIdentityError']('observation_unavailable')
    monkeypatch.setitem(namespace, 'load_deployment' if failure == 'descriptor' else 'store_observation', refuse)
    hook['tool_input'] = {'command': 'printf ordinary'}
    assert api['inspect_response'](json.dumps(hook).encode(), deployment[0], 'a' * 32) == {}
    hook['tool_input']['command'] = 'codex-continuation-inspect-' + 'a' * 32
    assert api['inspect_response'](json.dumps(hook).encode(), deployment[0], 'a' * 32)['hookSpecificOutput']['permissionDecision'] == 'deny'


@pytest.mark.parametrize('failure', ['duplicate', 'full', 'native', 'other-task-stale'])
def test_inspection_ordinary_failure_matrix(api, native_call, deployment, monkeypatch, failure):
    hook, _, thread, turn = native_call
    namespace = api['inspect_response'].__globals__
    monkeypatch.setitem(namespace, 'read_native_metadata', lambda *args: (thread, turn))
    raw = json.dumps(hook).encode()
    if failure == 'duplicate':
        assert api['inspect_response'](raw, deployment[0], 'a' * 32) == {}
    elif failure == 'full':
        value = api['native_observation'](*native_call)
        for index in range(128):
            api['store_observation'](deployment[0].parent, {**value, 'call_digest': f'{index:064x}'})
    elif failure == 'native':
        def unavailable(*args): raise api['NativeIdentityError']('native_unavailable')
        monkeypatch.setitem(namespace, 'read_native_metadata', unavailable)
    else:
        hook['session_id'] = 'other-task'
        raw = json.dumps(hook).encode()
        deployment[0].write_text('invalid')
    assert api['inspect_response'](raw, deployment[0], 'a' * 32) == {}


def test_approval_details_are_validated_and_read_only(api, tmp_path, approval_binding):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    challenge = store.prepare_approval(approval_binding, 'd' * 64)
    before = store.path.read_bytes()
    assert store.approval_details(challenge) == {'binding': approval_binding, 'deployment_digest': 'd' * 64, 'state': 'prepared'}
    assert store.path.read_bytes() == before
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE operator_approvals SET binding_json='SECRET'")
    with pytest.raises(api['NativeIdentityError'], match='^storage_invalid$') as caught:
        store.approval_details(challenge)
    assert caught.value.__context__ is None


def test_native_receipt_lookup_matches_exact_call(api, tmp_path, records):
    store = api['NativeReceiptStore'](tmp_path / 'private')
    store.initialize()
    identity = api['validate_native_identity'](*records)
    receipt = store.issue(identity, 'shell', '1' * 64, deployment_digest='d' * 64)
    assert store.find_call('root-1', 'turn-1', 'call-1')['receipt_id'] == receipt
    assert store.find_call('root-1', 'other-turn', 'call-1') is None


@pytest.mark.parametrize('command,expected', [
    ('codex-continuation control check', ('check', None)),
    ('codex-continuation control attach', ('attach', None)),
    ('codex-continuation control prepare recover', ('prepare', 'recover')),
    ('codex-continuation control apply ' + 'a' * 32, ('apply', 'a' * 32)),
    ('printf hello', None),
    ('codex-continuation control check; printf extra', None),
])
def test_control_parser_is_exact(api, command, expected):
    assert api['parse_control'](command) == expected


def test_operator_approval_command_is_not_native_control(api):
    assert api['parse_control']('codex-continuation approve ' + 'a' * 32) == ('operator_only', None)
