"""Internal adapter seam fixtures; never native identity or operator consent."""
import contextlib
import io
import json
import os
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dbsctr_continuation import cycle  # noqa: F401

SOURCE = Path(__file__).parents[1] / 'dot_local/bin/executable_dbsctrctl'


@pytest.fixture
def bridge(cycle, monkeypatch):
    for key, value in cycle.continuation_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(cycle.repo)
    module = runpy.run_path(str(SOURCE), run_name='codex_core_test')
    class Context:
        session_key = 'c' * 64
        session_id = 'codex-root'
        message_id = 'codex_receipt_fixture'
        repository_basis = cycle.repo.resolve()
        cycle_id = json.loads(cycle.record_path().read_text())["cycle_id"]
        home_id = 'a' * 64
        activation = {'schema_version': 1, 'provider_id': 'openai', 'model_id': 'fixture-model',
                      'agent_id': 'build', 'core_revision': '3.31', 'overlay_revision': 'neutral-2026-07-26'}
        approvals = []
        def verify_approval(self, request, binding, *, consume=True):
            if request.get('approval', {}).get('binding') != binding:
                raise module['ContinuationError']('approval_required')
            self.approvals.append(binding)
    actor = Context()
    def call(command='check', **changes):
        request = {'schema_version': 1, 'worktree': str(cycle.repo.resolve()), **changes}
        namespace = module['command_continuation'].__globals__
        monkeypatch.setattr(namespace['sys'], 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(request).encode())))
        output = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(output):
            try:
                module['command_continuation'](SimpleNamespace(command='continuation-'+command, request_json='-'),
                                               native_context=actor)
            except SystemExit as error:
                code = error.code
        return code, json.loads(output.getvalue())
    yield cycle, actor, call, module


def test_native_seam_preserves_record_and_uses_actual_home_identity(bridge):
    cycle, actor, call, _ = bridge
    original = cycle.record_path().read_bytes()
    code, check = call(action='enroll')
    assert code == 0 and check['reason'] == 'not_enrolled'
    approval = {'receipt_id': 'operator-receipt', 'binding': check['approval_binding']}
    assert call('enroll', approval=approval)[0] == 0
    code, attached = call('attach', mode='writer', generation=0)
    assert code == 0 and attached['generation'] == 1
    import sqlite3
    with sqlite3.connect(cycle.continuation_path) as connection:
        assert connection.execute('SELECT home_worktree_id FROM routes').fetchone()[0] == actor.home_id
    assert cycle.record_path().read_bytes() == original
    assert len(actor.approvals) >= 1


def test_native_seam_does_not_relax_generation_fencing(bridge):
    _, _, call, _ = bridge
    binding = call(action='enroll')[1]['approval_binding']
    assert call('enroll', approval={'receipt_id': 'receipt-1', 'binding': binding})[0] == 0
    assert call('attach', mode='writer', generation=0)[0] == 0
    code, result = call('admit', generation=0, call_id='call-1', operation_class='shell')
    assert code == 1 and result['reason'] == 'generation_changed'
    assert call('admit', generation=1, call_id='call-1', operation_class='shell')[0] == 0


def test_native_identity_fields_cannot_be_injected_through_request(bridge):
    _, _, call, _ = bridge
    code, result = call(session_id='forged')
    assert code == 1 and result['reason'] == 'invalid_identity'


def test_native_seam_refuses_wrong_selected_cycle(bridge):
    cycle, actor, call, _ = bridge
    actor.cycle_id = 'other-cycle'
    before = cycle.record_path().read_bytes()
    code, result = call()
    assert code == 1 and result['reason'] == 'invalid_target'
    assert cycle.record_path().read_bytes() == before


def test_adapter_bridge_requires_real_companion_approval(cycle, monkeypatch):
    import hashlib
    import sqlite3
    for key, value in cycle.continuation_env.items(): monkeypatch.setenv(key, value)
    adapter_source = SOURCE.with_name('executable_codex-continuation')
    adapter = runpy.run_path(str(adapter_source), run_name='adapter_fixture')
    root = cycle.repo.resolve()
    identity = {'session_id': 'native-root', 'turn_id': 'native-turn', 'call_id': 'native-call',
                'model_id': 'fixture-model', 'provider_id': 'openai', 'agent_id': 'build'}
    deployment = {'conversation_id': 'native-root', 'conversation_home': str(root.parent),
                  'native_home': str(root.parent), 'producer': {'path': str(adapter_source)},
                  'core': {'path': str(SOURCE), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()},
                  'target': {'worktree': str(root), 'cycle_id': json.loads(cycle.record_path().read_text())['cycle_id']}}
    store = adapter['NativeReceiptStore'](root.parent / 'native-private')
    store.initialize()
    context = adapter['CoreBridge'](deployment, identity, 'a' * 32, store)
    checked = context.call('check', action='enroll')
    binding = checked['approval_binding']
    challenge = store.prepare_approval(binding, adapter['canonical_digest'](deployment))
    approval = {'receipt_id': challenge, 'binding': binding}
    assert context.call('enroll', approval=approval)['reason'] == 'approval_required'
    assert not cycle.continuation_path.exists()
    # Fixture-only operator transition. No native approval claimed.
    store.approve(challenge, binding, adapter['canonical_digest'](deployment))
    assert context.call('enroll', approval=approval)['ok'] is True
    assert context.call('attach', mode='writer', generation=0)['ok'] is True
    admitted = context.call('admit', generation=1, call_id='native-call', operation_class='shell')
    assert admitted['ok'] is True
    with sqlite3.connect(cycle.continuation_path) as db:
        assert db.execute('SELECT message_id FROM operations').fetchone()[0] == 'codex-' + 'a' * 32
    assert context.call('finish', operation_id=admitted['operation_id'], outcome='completed')['ok'] is True


def test_codex_companion_is_not_projected_as_opencode(bridge):
    import sqlite3
    cycle, actor, call, module = bridge
    binding = call(action='enroll')[1]['approval_binding']
    assert call('enroll', approval={'receipt_id': 'receipt', 'binding': binding})[0] == 0
    assert call('attach', mode='writer', generation=0)[0] == 0
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute("UPDATE activations SET activation=? WHERE kind='legacy'", (json.dumps(actor.activation, sort_keys=True),))
    result = module['continuation_runtime'](cycle.repo, actor.cycle_id)
    assert result['session_ids'] == []
    assert result['activation'] is None


@pytest.fixture
def native_bound(cycle, monkeypatch):
    import hashlib
    for key, value in cycle.continuation_env.items(): monkeypatch.setenv(key, value)
    root = cycle.repo.resolve()
    monkeypatch.chdir(root)
    adapter_source = SOURCE.with_name('executable_codex-continuation').resolve()
    module = runpy.run_path(str(SOURCE), run_name='native_guard_core')
    adapter = runpy.run_path(str(adapter_source), run_name='native_guard_adapter')
    private = Path(cycle.continuation_env['HOME']).resolve() / '.local/state/dbsctr/codex'
    private.mkdir(parents=True, mode=0o700)
    pin = lambda p: {'path': str(p.resolve()), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    descriptor = {'schema_version': 1, 'revision': 'codex-desktop-1', 'conversation_id': 'native-root',
                  'conversation_home': str(root.parent), 'native_home': str(root.parent),
                  'native_executable': pin(adapter_source), 'producer': pin(adapter_source), 'core': pin(SOURCE),
                  'target': {'worktree': str(root), 'common_git_dir': str(root / '.git'),
                             'cycle_id': json.loads(cycle.record_path().read_text())['cycle_id']}}
    path = private / 'selected.json'
    path.write_text(json.dumps(descriptor)); path.chmod(0o600)
    identity = {'session_id': 'native-root', 'turn_id': 'native-turn', 'call_id': 'native-call',
                'model_id': 'fixture-model', 'provider_id': 'openai', 'agent_id': 'build'}
    store = adapter['configured_store'](path); store.initialize()
    receipt = store.issue(identity, 'shell', '1' * 64, deployment_digest=adapter['canonical_digest'](descriptor))
    bridge = adapter['CoreBridge'](descriptor, identity, receipt, store)
    binding = bridge.call('check', action='enroll')['approval_binding']
    challenge = store.prepare_approval(binding, bridge.deployment_digest)
    store.approve(challenge, binding, bridge.deployment_digest)  # Synthetic fixture only.
    assert bridge.call('enroll', approval={'receipt_id': challenge, 'binding': binding})['ok']
    assert bridge.call('attach', mode='writer', generation=0)['ok']
    operation = bridge.call('admit', generation=1, call_id=identity['call_id'], operation_class='shell')['operation_id']
    store.activate(receipt, operation); store.claim_execution(receipt, operation, '1' * 64, bridge.deployment_digest)
    monkeypatch.setenv('DBSCTR_CONTINUATION_OPERATION', operation)
    return cycle, module, adapter, store, bridge, receipt, operation, path


def test_native_operation_guard_requires_validated_private_receipt(native_bound):
    _, module, _, _, bridge, _, operation, _ = native_bound
    bridge.verify_operation(operation)
    module['continuation_guard'](SimpleNamespace(command='review-artifact', cycle_id=bridge.cycle_id))


@pytest.mark.parametrize('change', ['deployment', 'receipt', 'generation', 'environment-only'])
def test_native_operation_guard_refuses_stale_or_fabricated_authority(native_bound, monkeypatch, change):
    import sqlite3
    cycle, module, _, store, bridge, receipt, operation, path = native_bound
    if change == 'deployment':
        value = json.loads(path.read_text()); value['conversation_id'] = 'other'; path.write_text(json.dumps(value))
    elif change == 'receipt': store.finish(receipt, operation, 'uncertain')
    elif change == 'generation':
        with sqlite3.connect(cycle.continuation_path) as db: db.execute('UPDATE cycles SET generation=generation+1')
    else: monkeypatch.setenv('DBSCTR_CONTINUATION_OPERATION', 'invented')
    with pytest.raises(RuntimeError):
        module['continuation_guard'](SimpleNamespace(command='review-artifact', cycle_id=bridge.cycle_id))


def fixture_hook(native_bound, monkeypatch, *, command='codex-continuation control check', call='next-call'):
    _, _, adapter, _, _, _, _, path = native_bound
    descriptor = json.loads(path.read_text())
    thread = {'id': 'native-root', 'sessionId': 'native-root', 'parentThreadId': None,
              'model': 'fixture-model', 'modelProvider': 'openai'}
    monkeypatch.setitem(adapter['native_hook_response'].__globals__, 'read_native_metadata',
                        lambda *args: (thread, {'id': 'native-turn'}))
    hook = {'hook_event_name': 'PreToolUse', 'session_id': 'native-root', 'turn_id': 'native-turn',
            'tool_use_id': call, 'model': 'fixture-model', 'permission_mode': 'bypassPermissions',
            'cwd': descriptor['conversation_home'], 'tool_name': 'Bash', 'tool_input': {'command': command}}
    return hook


def test_native_controls_remain_available_while_shell_is_pending(native_bound, monkeypatch):
    import shlex
    import subprocess
    cycle, _, adapter, _, _, _, _, _ = native_bound
    hook = fixture_hook(native_bound, monkeypatch)
    before = cycle.continuation_path.read_bytes()
    response = adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    command = response['hookSpecificOutput']['updatedInput']['command']
    result = subprocess.run(['/bin/bash', '-c', command], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['next_action'] == 'wait_for_completion'
    assert cycle.continuation_path.read_bytes() == before
    hook['tool_input']['command'] = 'printf not-admitted'
    hook['tool_use_id'] = 'other-call'
    refused = adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    assert refused['hookSpecificOutput']['permissionDecision'] == 'deny'


def test_native_post_closes_only_matching_operation(native_bound, monkeypatch):
    _, _, adapter, store, bridge, receipt, operation, _ = native_bound
    store.mark_execution_finished(receipt, operation)  # Synthetic foreground completion.
    hook = fixture_hook(native_bound, monkeypatch, call='native-call')
    hook['hook_event_name'] = 'PostToolUse'
    assert adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root') == {}
    assert store.read(receipt)['state'] == 'completed'
    assert bridge.call('check')['next_action'] == 'none'
    assert adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root') == {}


def test_native_dispatch_executes_once_in_selected_worktree(native_bound, monkeypatch):
    import base64
    cycle, _, adapter, store, _, _, _, _ = native_bound
    store.mark_execution_finished(native_bound[5], native_bound[6])
    post = fixture_hook(native_bound, monkeypatch, call='native-call')
    post['hook_event_name'] = 'PostToolUse'
    adapter['native_hook_response'](json.dumps(post).encode(), 'native-root')
    hook = fixture_hook(native_bound, monkeypatch, command='printf x >> execution.txt')
    result = adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    assert result['hookSpecificOutput']['permissionDecision'] == 'allow'
    value = store.find_call('native-root', 'native-turn', 'next-call')
    encoded = base64.b64encode(json.dumps(hook['tool_input']).encode()).decode()
    monkeypatch.chdir(cycle.repo.parent)
    assert adapter['dispatch_shell'](value['receipt_id'], encoded) == 0
    assert (cycle.repo / 'execution.txt').read_text() == 'x'
    assert not (cycle.repo.parent / 'execution.txt').exists()
    with pytest.raises(adapter['NativeIdentityError']): adapter['dispatch_shell'](value['receipt_id'], encoded)
    assert (cycle.repo / 'execution.txt').read_text() == 'x'
    assert store.read(value['receipt_id'])['state'] == 'active'


@pytest.mark.parametrize('suffix', ['', ' # ' + '\u00e9' * 12000], ids=['ascii', 'bounded-unicode'])
def test_native_rewritten_command_runs_through_real_cli(native_bound, monkeypatch, suffix):
    import subprocess
    cycle, _, adapter, store, _, _, _, _ = native_bound
    store.mark_execution_finished(native_bound[5], native_bound[6])
    post = fixture_hook(native_bound, monkeypatch, call='native-call')
    post['hook_event_name'] = 'PostToolUse'
    adapter['native_hook_response'](json.dumps(post).encode(), 'native-root')
    hook = fixture_hook(native_bound, monkeypatch, command='printf cli >> cli-result.txt' + suffix)
    response = adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    command = response['hookSpecificOutput']['updatedInput']['command']
    result = subprocess.run(['/bin/bash', '-c', command], cwd=cycle.repo.parent,
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert (cycle.repo / 'cli-result.txt').read_text() == 'cli'
    replay = subprocess.run(['/bin/bash', '-c', command], capture_output=True, timeout=10)
    assert replay.returncode != 0 and b'dispatch_refused' in replay.stderr
    assert (cycle.repo / 'cli-result.txt').read_text() == 'cli'
    assert store.find_call('native-root', 'native-turn', 'next-call')['state'] == 'active'


@pytest.mark.parametrize('change', ['none', 'transition', 'state', 'answer', 'noninteractive'])
def test_operator_confirmation_rechecks_exact_snapshot(native_bound, monkeypatch, change):
    import io
    cycle, _, adapter, store, bridge, _, _, _ = native_bound
    if change == 'transition':
        import sqlite3
        previous = {**bridge.activation, 'provider_id': 'google-vertex-anthropic', 'model_id': 'old-model'}
        with sqlite3.connect(cycle.continuation_path) as db:
            db.execute('UPDATE activations SET activation=? WHERE session_key=?',
                       (json.dumps(previous), bridge.session_key))
    hook = fixture_hook(native_bound, monkeypatch, command='codex-continuation control prepare recover')
    response = adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    import shlex
    state = json.loads(shlex.split(response['hookSpecificOutput']['updatedInput']['command'])[-1])
    challenge = state['operator_challenge']
    for name in ('CODEX_THREAD_ID', 'OPENCODE_PID', 'OPENCODE_SESSION_ID'):
        monkeypatch.delenv(name, raising=False)
    class Terminal(io.StringIO):
        def isatty(self): return change != 'noninteractive'
        def readline(self, *args):
            if change == 'state':
                bridge.call('finish', operation_id=native_bound[6], outcome='completed')
            return super().readline(*args)
    incoming = Terminal(('wrong' if change == 'answer' else 'approve ' + challenge) + '\n')
    outgoing = Terminal()
    if change in ('none', 'transition'):
        adapter['operator_approve'](challenge, incoming, outgoing)
        assert store.approval_details(challenge)['state'] == 'approved'
        assert 'quiescent' in outgoing.getvalue()
        displayed = json.loads(outgoing.getvalue().splitlines()[0])
        assert displayed['approval_summary']['proposed_activation']['provider_id'] == 'openai'
        assert displayed['approval_summary']['previous_activation']['model_id'] == (
            'old-model' if change == 'transition' else 'fixture-model')
        if change == 'transition':
            assert displayed['approval_summary']['previous_activation']['provider_id'] == 'google-vertex-anthropic'
            assert displayed['approval_summary']['writer_activation'] == previous
        assert displayed['approval_summary']['writer_key'] == bridge.session_key
        assert displayed['approval_summary']['writer_relation'] == 'self'
        assert displayed['approval_summary']['outstanding_operations'] == 1
    else:
        with pytest.raises(adapter['NativeIdentityError']):
            adapter['operator_approve'](challenge, incoming, outgoing)
        assert store.approval_details(challenge)['state'] == 'prepared'


def test_core_executes_verified_bytes_without_reopening_path(native_bound, monkeypatch, tmp_path):
    import hashlib
    _, _, adapter, store, bridge, receipt, _, path = native_bound
    descriptor = json.loads(path.read_text())
    copied = tmp_path / 'core.py'
    copied.write_bytes(SOURCE.read_bytes())
    descriptor['core'] = {'path': str(copied.resolve()), 'sha256': hashlib.sha256(copied.read_bytes()).hexdigest()}
    original = adapter['pinned_file']
    def replace_after_validation(value, **kwargs):
        result = original(value, **kwargs)
        if value['path'] == str(copied.resolve()):
            copied.write_text('raise AssertionError("unverified replacement executed")\n')
        return result
    monkeypatch.setitem(adapter['CoreBridge'].__init__.__globals__, 'pinned_file', replace_after_validation)
    verified = adapter['CoreBridge'](descriptor, bridge.identity, receipt, store)
    assert callable(verified.core['command_continuation'])


def test_native_post_without_wrapper_completion_is_uncertain(native_bound, monkeypatch):
    _, _, adapter, store, bridge, receipt, operation, _ = native_bound
    # This fixture has claimed execution but has not executed a foreground child.
    post = fixture_hook(native_bound, monkeypatch, call='native-call')
    post['hook_event_name'] = 'PostToolUse'
    assert adapter['native_hook_response'](json.dumps(post).encode(), 'native-root') == {}
    assert store.read(receipt)['state'] == 'uncertain'
    assert bridge.call('check')['state'] == 'recovery_required'


@pytest.mark.parametrize('after_mode', ['primary', 'plan', 'child', 'metadata-unavailable'])
def test_pointerless_finalization_releases_selection_only_after_matched_post(native_bound, monkeypatch, after_mode):
    cycle, _, adapter, store, bridge, receipt, operation, _ = native_bound
    record = json.loads(cycle.record_path().read_text())
    record.update(state='completed', completed_at=record['created_at'])
    cycle.record_path().write_text(json.dumps(record))
    (cycle.repo / '.git/dbsctr/worktrees' / record['worktree']['id'] / 'active').unlink()
    before = fixture_hook(native_bound, monkeypatch, command='printf ordinary', call='before-close')
    assert adapter['native_hook_response'](json.dumps(before).encode(), 'native-root')['hookSpecificOutput']['permissionDecision'] == 'deny'
    store.mark_execution_finished(receipt, operation)
    post = fixture_hook(native_bound, monkeypatch, call='native-call')
    post['hook_event_name'] = 'PostToolUse'
    assert adapter['native_hook_response'](json.dumps(post).encode(), 'native-root') == {}
    after = fixture_hook(native_bound, monkeypatch, command='printf ordinary', call='after-close')
    if after_mode == 'plan': after['permission_mode'] = 'plan'
    if after_mode == 'child': after['turn_id'] = 'child-turn'
    if after_mode == 'metadata-unavailable':
        def unavailable(*args): raise RuntimeError('unavailable')
        monkeypatch.setitem(adapter['native_hook_response'].__globals__, 'read_native_metadata', unavailable)
    assert adapter['native_hook_response'](json.dumps(after).encode(), 'native-root') == {}
    assert store.find_call('native-root', 'native-turn', 'after-close') is None
    assert bridge.selection_closed() is True


@pytest.mark.parametrize('termination', ['term', 'interrupt', 'resistant'])
def test_real_wrapper_interruption_cleans_owned_child_and_retains_uncertainty(native_bound, monkeypatch, termination):
    import shlex
    import signal
    import subprocess
    import sys
    import time
    cycle, _, adapter, store, bridge, receipt, operation, _ = native_bound
    store.mark_execution_finished(receipt, operation)
    post = fixture_hook(native_bound, monkeypatch, call='native-call')
    post['hook_event_name'] = 'PostToolUse'
    adapter['native_hook_response'](json.dumps(post).encode(), 'native-root')
    child_code = ('import os,signal,time; from pathlib import Path; '
                  + ('signal.signal(signal.SIGTERM,signal.SIG_IGN); ' if termination == 'resistant' else '')
                  + 'Path("child-pid").write_text(str(os.getpid())); time.sleep(30); '
                  'Path("late-write").write_text("should not run")')
    command = shlex.join([sys.executable, '-c', child_code])
    hook = fixture_hook(native_bound, monkeypatch, command=command)
    response = adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    wrapper = subprocess.Popen(shlex.split(response['hookSpecificOutput']['updatedInput']['command']),
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    child = group = None
    try:
        deadline = time.monotonic() + 5
        while not (cycle.repo / 'child-pid').exists() and time.monotonic() < deadline:
            time.sleep(.02)
        child = int((cycle.repo / 'child-pid').read_text())
        group = os.getpgid(child)
        assert group != os.getpgrp()
        wrapper.send_signal(signal.SIGINT if termination == 'interrupt' else signal.SIGTERM)
        wrapper.wait(timeout=5)
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            try: os.kill(child, 0)
            except ProcessLookupError: break
            time.sleep(.02)
        with pytest.raises(ProcessLookupError): os.kill(child, 0)
        value = store.find_call('native-root', 'native-turn', 'next-call')
        assert value['state'] == 'uncertain' and value['execution_finished'] is False, wrapper.stderr.read().decode()
        assert bridge.call('check')['state'] == 'recovery_required'
        assert not (cycle.repo / 'late-write').exists()
    finally:
        if wrapper.poll() is None:
            wrapper.kill(); wrapper.wait(timeout=5)
        wrapper.stderr.close()
        if group is not None:
            try: os.killpg(group, signal.SIGKILL)
            except ProcessLookupError: pass


def test_signal_during_spawn_retains_child_handle_before_cancellation(native_bound, monkeypatch):
    import base64
    import signal
    cycle, _, adapter, store, bridge, receipt, operation, _ = native_bound
    store.mark_execution_finished(receipt, operation)
    post = fixture_hook(native_bound, monkeypatch, call='native-call')
    post['hook_event_name'] = 'PostToolUse'
    adapter['native_hook_response'](json.dumps(post).encode(), 'native-root')
    hook = fixture_hook(native_bound, monkeypatch, command='exec sleep 30')
    adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    value = store.find_call('native-root', 'native-turn', 'next-call')
    namespace = adapter['dispatch_shell'].__globals__
    real_popen = namespace['subprocess'].Popen
    children = []
    def popen(arguments, **kwargs):
        child = real_popen(arguments, **kwargs)
        if arguments[0] == '/bin/bash':
            children.append(child)
            os.kill(os.getpid(), signal.SIGTERM)
        return child
    monkeypatch.setattr(namespace['subprocess'], 'Popen', popen)
    encoded = base64.b64encode(json.dumps(hook['tool_input']).encode()).decode()
    try:
        with pytest.raises(adapter['NativeIdentityError']):
            adapter['dispatch_shell'](value['receipt_id'], encoded)
        assert len(children) == 1
        assert children[0].poll() is not None, 'spawned child survived cancellation'
        with pytest.raises(ProcessLookupError): os.killpg(children[0].pid, 0)
        assert store.read(value['receipt_id'])['state'] == 'uncertain'
        assert bridge.call('check')['state'] == 'recovery_required'
    finally:
        for child in children:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait(timeout=5)


def test_cleanup_refusal_cannot_prevent_uncertainty_record(native_bound, monkeypatch):
    import base64
    cycle, _, adapter, store, bridge, receipt, operation, _ = native_bound
    store.mark_execution_finished(receipt, operation)
    post = fixture_hook(native_bound, monkeypatch, call='native-call')
    post['hook_event_name'] = 'PostToolUse'
    adapter['native_hook_response'](json.dumps(post).encode(), 'native-root')
    hook = fixture_hook(native_bound, monkeypatch, command='unused synthetic shell')
    adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    value = store.find_call('native-root', 'native-turn', 'next-call')
    namespace = adapter['dispatch_shell'].__globals__
    real_popen = namespace['subprocess'].Popen
    class Child:
        pid = 999999999
        def wait(self): return 0
        def poll(self): return 0
    def popen(arguments, **kwargs):
        return Child() if arguments[0] == '/bin/bash' else real_popen(arguments, **kwargs)
    real_killpg = os.killpg
    def killpg(group, signum):
        if group == Child.pid: raise PermissionError('synthetic owned-group refusal')
        return real_killpg(group, signum)
    monkeypatch.setattr(namespace['subprocess'], 'Popen', popen)
    monkeypatch.setattr(os, 'killpg', killpg)
    encoded = base64.b64encode(json.dumps(hook['tool_input']).encode()).decode()
    with pytest.raises(adapter['NativeIdentityError']):
        adapter['dispatch_shell'](value['receipt_id'], encoded)
    assert store.read(value['receipt_id'])['state'] == 'uncertain'
    assert bridge.call('check')['state'] == 'recovery_required'


@pytest.mark.parametrize('kind', ['plan', 'child', 'patch', 'mcp', 'background'])
def test_native_producer_refuses_unsupported_calls_without_state_change(native_bound, monkeypatch, kind):
    cycle, _, adapter, store, _, _, _, _ = native_bound
    hook = fixture_hook(native_bound, monkeypatch, command='printf forbidden')
    if kind == 'plan': hook['permission_mode'] = 'plan'
    elif kind == 'child': hook['turn_id'] = 'child-turn'
    elif kind == 'patch': hook['tool_name'] = 'apply_patch'
    elif kind == 'mcp': hook['tool_name'] = 'mcp__write'
    else: hook['tool_input']['run_in_background'] = True
    before = (cycle.continuation_path.read_bytes(), store.path.read_bytes())
    decision = adapter['native_hook_response'](json.dumps(hook).encode(), 'native-root')
    assert decision['hookSpecificOutput']['permissionDecision'] == 'deny'
    assert (cycle.continuation_path.read_bytes(), store.path.read_bytes()) == before


@pytest.mark.parametrize('kind', ['unfinished', 'wrong-record', 'missing-record', 'pending-operation'])
def test_selection_cannot_release_from_incomplete_or_inconsistent_evidence(native_bound, kind):
    import sqlite3
    cycle, _, _, _, bridge, _, _, _ = native_bound
    record_path = cycle.record_path()
    record = json.loads(record_path.read_text())
    record.update(state='completed', completed_at=record['created_at'])
    if kind == 'unfinished': record['state'] = 'active'
    if kind == 'wrong-record': record['cycle_id'] = 'OTHER'
    record_path.write_text(json.dumps(record))
    if kind == 'missing-record': record_path.unlink()
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute("UPDATE cycles SET state='closed',writer=NULL")
        if kind != 'pending-operation': db.execute("UPDATE operations SET state='completed'")
    with pytest.raises((Exception, SystemExit)):
        bridge.selection_closed()
