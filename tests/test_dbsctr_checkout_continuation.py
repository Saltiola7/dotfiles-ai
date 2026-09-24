"""Checkout-independent continuation regressions in disposable repositories."""
import json
import sqlite3
import uuid
import subprocess
from pathlib import Path

import test_dbsctr_continuation as legacy
import pytest

cycle = legacy.cycle


def v2(cycle, action='check', *, ok=True, **fields):
    request = {key: value for key, value in cycle.request.items() if key != 'worktree'}
    request.update(schema_version=2, action=action, **fields)
    result = legacy.fixtures.run(cycle.repo, 'continuation-v2', '--request-json', '-',
                                env=cycle.continuation_env, input_text=json.dumps(request), ok=ok)
    response = json.loads(result.stdout)
    assert response['ok'] is ok
    assert result.stderr == ''
    if action != 'resolve':
        assert str(cycle.repo) not in result.stdout
    return response


def v2_request(cycle, action, *, approved=False, **fields):
    preparation = {key: value for key, value in fields.items()
                   if key in {'worktree', 'mode', 'target_session_id', 'session_id', 'message_id'}}
    state = v2(cycle, for_action=action, **preparation)
    request = {'request_id': uuid.uuid4().hex, 'expected': state['expected'], **fields}
    if approved:
        request['approval'] = {'receipt_id': uuid.uuid4().hex, 'binding': state['expected']}
    return request


def bound_writer(cycle):
    target = {'worktree': str(cycle.repo)}
    v2(cycle, 'enroll', **v2_request(cycle, 'enroll', approved=True, **target))
    return v2(cycle, 'attach', **v2_request(cycle, 'attach', mode='writer', **target))


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_missing_historical_source_does_not_invalidate_live_cycle(cycle):
    """Keep home and execution valid while the distinct source branch changes."""
    source = Path(cycle.temp.name) / 'source'
    git(cycle.repo, 'worktree', 'add', '-b', 'launch-source', str(source))
    module = legacy.runpy.run_path(str(legacy.fixtures.SCRIPT))
    path = cycle.record_path()
    record = json.loads(path.read_text())
    record['source'] = {
        'id': module['worktree_id'](source), 'branch': 'launch-source',
        'locator': {'root': 'primary_worktree', 'path': '.'},
    }
    record['runtime'] = {'opencode': {
        'session_ids': ['owner'], 'path_root': 'cycle_worktree',
        'worktree': '.', 'directory': '.',
    }}
    module['sync_schema5_opencode'](record)
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    assert legacy.call(cycle)['ok']
    git(source, 'switch', '-c', 'ordinary-work')
    assert legacy.call(cycle)['ok']
    git(cycle.repo, 'worktree', 'remove', str(source))
    assert legacy.call(cycle)['ok']
    assert path.read_bytes() == before


def test_invalid_target_preserves_uncertain_work_but_blocks_recovery_binding(cycle):
    """Characterize the target-dependent recovery gap without waiving quiescence."""
    legacy.enroll(cycle)
    operation = legacy.call(cycle, 'admit', generation=1,
                            call_id='uncertain-before-target-loss', operation_class='file')
    legacy.call(cycle, 'finish', operation_id=operation['operation_id'], outcome='uncertain')
    record = json.loads(cycle.record_path().read_text())
    pointer = cycle.repo / '.git/dbsctr/worktrees' / record['worktree']['id'] / 'active'
    pointer.unlink()
    before = cycle.continuation_path.read_bytes()
    result = legacy.call(cycle, action='recover', ok=False)
    assert result['reason'] == 'invalid_target'
    assert result['approval_binding'] is None
    assert cycle.continuation_path.read_bytes() == before
    with sqlite3.connect(cycle.continuation_path) as db:
        assert db.execute('SELECT state FROM operations WHERE operation_id=?',
                          (operation['operation_id'],)).fetchone() == ('uncertain',)
        assert db.execute('SELECT state,generation FROM cycles WHERE cycle_id=?',
                          (record['cycle_id'],)).fetchone() == ('recovery_required', 1)


def test_v2_check_without_selection_creates_nothing(cycle):
    state = v2(cycle)
    assert state['next_action'] == 'select_target'
    assert state['cycle_id'] is None
    assert not cycle.continuation_path.exists()


def test_v2_legacy_uncertain_invalid_target_recovery_then_release(cycle):
    legacy.enroll(cycle)
    op = legacy.call(cycle, 'admit', generation=1, call_id='lost', operation_class='file')
    legacy.call(cycle, 'finish', operation_id=op['operation_id'], outcome='uncertain')
    record = json.loads(cycle.record_path().read_text())
    (cycle.repo / '.git/dbsctr/worktrees' / record['worktree']['id'] / 'active').unlink()
    before = cycle.continuation_path.read_bytes()
    check = v2(cycle, for_action='recover')
    assert check['checks']['target']['status'] == 'unavailable'
    assert check['expected'] and check['generation'] == 1
    assert cycle.continuation_path.read_bytes() == before
    request = v2_request(cycle, 'recover', approved=True)
    recovered = v2(cycle, 'recover', **request)
    assert recovered['generation'] == 2 and recovered['writer_relation'] == 'none'
    assert v2(cycle, 'recover', **request)['replayed']
    v2(cycle, 'release', **v2_request(cycle, 'release'))
    assert v2(cycle)['next_action'] == 'select_target'
    with sqlite3.connect(cycle.continuation_path) as db:
        assert db.execute('SELECT completion_class FROM operations WHERE operation_id=?',
                          (op['operation_id'],)).fetchone() == ('operator_quiescence',)
        assert db.execute('SELECT count(*) FROM cycle_bindings').fetchone() == (0,)


def test_v2_bound_release_replay_preserves_new_same_cycle_selection(cycle):
    before = cycle.record_path().read_bytes()
    first = bound_writer(cycle)
    request = v2_request(cycle, 'release')
    released = v2(cycle, 'release', **request)
    assert released['generation'] == first['generation'] + 1
    second = v2(cycle, 'attach', **v2_request(cycle, 'attach', worktree=str(cycle.repo), mode='writer'))
    assert second['route_version'] > first['route_version']
    assert v2(cycle, 'release', **request)['replayed']
    assert v2(cycle)['writer_relation'] == 'self'
    assert v2(cycle)['route_version'] == second['route_version']
    assert cycle.record_path().read_bytes() == before
    assert legacy.call(cycle, ok=False)['reason'] == 'revision_incompatible'


def test_v2_branch_drift_denies_writes_but_allows_release(cycle):
    first = bound_writer(cycle)
    git(cycle.repo, 'switch', '-c', 'different')
    check = v2(cycle, for_action='release')
    assert check['binding_id'] == first['binding_id']
    assert check['checks']['target']['reason'] == 'branch_mismatch'
    assert v2(cycle, for_action='admit', ok=False)['reason'] == 'branch_mismatch'
    v2(cycle, 'release', **v2_request(cycle, 'release'))
    assert v2(cycle)['cycle_id'] is None


@pytest.mark.parametrize('session,message', [('plan', 'plan-old'), ('child', 'child-old'),
                                            ('owner', 'reader-old')])
def test_v2_release_requires_native_build_identity(cycle, session, message):
    legacy.enroll(cycle)
    request = v2_request(cycle, 'release')
    before = cycle.continuation_path.read_bytes()
    assert not v2(cycle, 'release', ok=False, session_id=session, message_id=message, **request)['ok']
    assert cycle.continuation_path.read_bytes() == before


def test_v2_enrollment_denial_and_idempotence(cycle):
    request = v2_request(cycle, 'enroll', approved=True, worktree=str(cycle.repo))
    bad = {**request, 'approval': {'receipt_id': 'denied', 'binding': {}}}
    assert v2(cycle, 'enroll', ok=False, **bad)['reason'] == 'approval_required'
    assert not cycle.continuation_path.exists()
    first = v2(cycle, 'enroll', **request)
    again = v2(cycle, 'enroll', **request)
    assert again['replayed'] and again['binding_id'] == first['binding_id']
    before = cycle.continuation_path.read_bytes()
    assert v2(cycle, 'enroll', ok=False, **{**request, 'message_id': 'owner-new'})['reason'] == 'invalid_state'
    assert cycle.continuation_path.read_bytes() == before


def test_v2_explicit_bind_requires_recovered_legacy_writer(cycle):
    legacy.enroll(cycle)
    before = cycle.record_path().read_bytes()
    request = v2_request(cycle, 'bind', approved=True, worktree=str(cycle.repo))
    assert v2(cycle, 'bind', ok=False, **request)['reason'] == 'recovery_required'
    legacy.call(cycle, 'recover', generation=1, approval=legacy.approve(cycle, 'recover'))
    bound = v2(cycle, 'bind', **v2_request(cycle, 'bind', approved=True, worktree=str(cycle.repo)))
    assert bound['generation'] == 2 and bound['writer_relation'] == 'none'
    assert cycle.record_path().read_bytes() == before


def test_v2_admission_finish_and_legacy_lifecycle_guard(cycle):
    bound_writer(cycle)
    check = v2(cycle, for_action='admit')
    request = {'expected': check['expected'], 'call_id': 'native-call', 'operation_class': 'lifecycle'}
    op = v2(cycle, 'admit', **request)
    assert v2(cycle, 'admit', **request)['operation_id'] == op['operation_id']
    env = {**cycle.continuation_env, 'DBSCTR_CONTINUATION_OPERATION': op['operation_id']}
    legacy.fixtures.run(cycle.repo, 'set-gate', 'domain', '--result', 'pending', env=env)
    assert v2(cycle, 'release', ok=False, **v2_request(cycle, 'release'))['reason'] == 'operation_in_flight'
    v2(cycle, 'finish', operation_id=op['operation_id'], outcome='completed')
    assert legacy.fixtures.run(cycle.repo, 'set-gate', 'domain', '--result', 'pending', env=env, ok=False).returncode


def test_v2_stale_quiescence_approval_preserves_operations(cycle):
    legacy.enroll(cycle)
    request = v2_request(cycle, 'recover', approved=True)
    op = legacy.call(cycle, 'admit', generation=1, call_id='racing', operation_class='file')
    before = cycle.continuation_path.read_bytes()
    assert v2(cycle, 'recover', ok=False, **request)['reason'] == 'route_changed'
    assert cycle.continuation_path.read_bytes() == before
    legacy.call(cycle, 'finish', operation_id=op['operation_id'], outcome='completed')


def test_v2_custody_drift_blocks_writes_not_route_release(cycle):
    bound_writer(cycle)
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute('UPDATE worktree_bindings SET admin_ino=admin_ino+1')
    check = v2(cycle, for_action='release')
    assert check['checks']['target']['reason'] == 'registration_changed'
    assert v2(cycle, for_action='admit', ok=False)['reason'] == 'registration_changed'
    v2(cycle, 'release', **v2_request(cycle, 'release'))


def test_v2_reader_release_does_not_interrupt_other_writer(cycle):
    owner = bound_writer(cycle)
    op = v2(cycle, 'admit', expected=v2(cycle, for_action='admit')['expected'],
            call_id='owner-running', operation_class='file')
    identity = {'session_id': 'reader', 'message_id': 'reader-old'}
    check = v2(cycle, worktree=str(cycle.repo), for_action='attach', mode='reader', **identity)
    v2(cycle, 'attach', worktree=str(cycle.repo), mode='reader', request_id='reader-attach',
       expected=check['expected'], **identity)
    snapshot = v2(cycle, for_action='release', **identity)
    v2(cycle, 'release', request_id='reader-release', expected=snapshot['expected'], **identity)
    assert v2(cycle)['generation'] == owner['generation']
    assert v2(cycle)['writer_relation'] == 'self'
    v2(cycle, 'finish', operation_id=op['operation_id'], outcome='completed')


@pytest.mark.parametrize('expected', [None, [], {}, True, 'bad'])
def test_v2_malformed_snapshot_is_bounded_and_read_only(cycle, expected):
    legacy.enroll(cycle)
    before = cycle.continuation_path.read_bytes()
    assert v2(cycle, 'release', expected=expected, request_id='bad', ok=False)['reason'] == 'invalid_state'
    assert cycle.continuation_path.read_bytes() == before


def test_v2_resolve_keeps_path_on_local_interface_only(cycle):
    bound_writer(cycle)
    prepared = v2(cycle, for_action='resolve')
    assert prepared['local_target'] is None
    resolved = v2(cycle, 'resolve', expected=prepared['expected'])
    assert resolved['local_target']['path'] == str(cycle.repo.resolve())
    assert resolved['local_target']['binding_id'] == resolved['binding_id']


def test_v2_release_transaction_rolls_back_when_receipt_fails(cycle):
    first = bound_writer(cycle)
    request = v2_request(cycle, 'release')
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute("CREATE TRIGGER interrupt_control BEFORE INSERT ON control_requests "
                   "BEGIN SELECT RAISE(ABORT,'injected interruption'); END")
    before = cycle.continuation_path.read_bytes()
    assert v2(cycle, 'release', ok=False, **request)['reason'] == 'invalid_state'
    assert cycle.continuation_path.read_bytes() == before
    state = v2(cycle)
    assert state['generation'] == first['generation']
    assert state['route_version'] == first['route_version']
    assert state['writer_relation'] == 'self'


def test_v2_partial_schema_is_not_treated_as_legacy(cycle):
    bound_writer(cycle)
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute('DROP TABLE control_requests')
    before = cycle.continuation_path.read_bytes()
    assert v2(cycle, ok=False)['reason'] == 'invalid_state'
    assert cycle.continuation_path.read_bytes() == before


def test_v2_stale_release_cannot_remove_new_selection(cycle):
    bound_writer(cycle)
    stale = v2_request(cycle, 'release')
    v2(cycle, 'attach', **v2_request(cycle, 'attach', worktree=str(cycle.repo), mode='writer'))
    before = cycle.continuation_path.read_bytes()
    assert v2(cycle, 'release', ok=False, **stale)['reason'] == 'route_changed'
    assert cycle.continuation_path.read_bytes() == before


def test_v2_completion_after_pointer_removal_releases_only_matching_route(cycle):
    bound_writer(cycle)
    operation = v2(cycle, 'admit', expected=v2(cycle, for_action='admit')['expected'],
                   call_id='final-push', operation_class='lifecycle')
    path = cycle.record_path()
    record = json.loads(path.read_text())
    record.update(state='completed', completed_at=record['created_at'])
    path.write_text(json.dumps(record))
    (cycle.repo / '.git/dbsctr/worktrees' / record['worktree']['id'] / 'active').unlink()
    assert v2(cycle, 'finish', operation_id=operation['operation_id'], outcome='completed')['state'] == 'closed'
    assert v2(cycle, 'finish', operation_id=operation['operation_id'], outcome='completed')['state'] == 'closed'
    assert v2(cycle)['cycle_id'] is None


def test_v2_finish_after_branch_drift_records_completion_without_admission(cycle):
    bound_writer(cycle)
    operation = v2(cycle, 'admit', expected=v2(cycle, for_action='admit')['expected'],
                   call_id='branch-changing-call', operation_class='shell')
    git(cycle.repo, 'switch', '-c', 'changed-by-call')
    assert v2(cycle, 'finish', operation_id=operation['operation_id'], outcome='completed')['ok']
    assert v2(cycle, for_action='admit', ok=False)['reason'] == 'branch_mismatch'


def test_v2_closed_cycle_cannot_be_rebound_or_attached(cycle):
    bound_writer(cycle)
    path = cycle.record_path()
    record = json.loads(path.read_text())
    record.update(state='completed', completed_at=record['created_at'])
    path.write_text(json.dumps(record))
    v2(cycle, 'recover', **v2_request(cycle, 'recover', approved=True))
    assert v2(cycle)['state'] == 'closed'
    attempt = v2_request(cycle, 'attach', worktree=str(cycle.repo), mode='writer')
    assert v2(cycle, 'attach', ok=False, **attempt)['reason'] == 'invalid_target'


def test_v2_missing_record_quiescence_does_not_create_replacement(cycle):
    legacy.enroll(cycle)
    path = cycle.record_path()
    path.unlink()
    recovered = v2(cycle, 'recover', **v2_request(cycle, 'recover', approved=True))
    assert recovered['writer_relation'] == 'none'
    assert not path.exists()
    v2(cycle, 'release', **v2_request(cycle, 'release'))
    assert not path.exists()


def test_v2_provider_transition_requires_exact_approval(cycle):
    bound_writer(cycle)
    fields = {'worktree': str(cycle.repo), 'mode': 'writer', 'message_id': 'owner-other'}
    request = v2_request(cycle, 'attach', **fields)
    assert v2(cycle, 'attach', ok=False, **request)['reason'] == 'provider_confirmation_required'
    approved = v2_request(cycle, 'attach', approved=True, **fields)
    assert v2(cycle, 'attach', **approved)['writer_relation'] == 'self'


def test_v2_handover_drains_then_fences(cycle):
    bound_writer(cycle)
    op = v2(cycle, 'admit', expected=v2(cycle, for_action='admit')['expected'],
            call_id='drain-me', operation_class='file')
    transfer = v2_request(cycle, 'handover', approved=True, target_session_id='reader')
    assert v2(cycle, 'handover', **transfer)['state'] == 'draining'
    v2(cycle, 'finish', operation_id=op['operation_id'], outcome='completed')
    result = v2(cycle, 'handover', **v2_request(cycle, 'handover', approved=True, target_session_id='reader'))
    assert result['generation'] == 2 and result['writer_relation'] == 'other'
    request = v2_request(cycle, 'attach', worktree=str(cycle.repo), mode='writer',
                         session_id='reader', message_id='reader-old')
    assert v2(cycle, 'attach', **request)['writer_relation'] == 'self'


def test_v2_second_cycle_cannot_orphan_writer_and_detached_bindings_stay_distinct(cycle):
    first = bound_writer(cycle)
    linked = Path(cycle.temp.name) / 'second'
    git(cycle.repo, 'worktree', 'add', '-b', 'second', str(linked))
    legacy.fixtures.run(linked, 'start', '--cycle-id', 'cycle-2', '--context', 'test',
                        '--risk', 'routine', '--delivery-intent', 'local',
                        '--plan', str(cycle.plan_path()), '--base-branch', 'main')
    v2(cycle, 'enroll', **v2_request(cycle, 'enroll', approved=True, worktree=str(linked)))
    attempt = v2_request(cycle, 'attach', worktree=str(linked), mode='writer')
    assert v2(cycle, 'attach', ok=False, **attempt)['reason'] == 'writer_occupied'
    identity = {'session_id': 'reader', 'message_id': 'reader-old'}
    second = v2(cycle, 'attach', **v2_request(cycle, 'attach', worktree=str(linked), mode='writer', **identity))
    assert first['binding_id'] != second['binding_id']
    git(cycle.repo, 'switch', '--detach')
    git(linked, 'switch', '--detach')
    assert v2(cycle)['binding_id'] == first['binding_id']
    assert v2(cycle, **identity)['binding_id'] == second['binding_id']
    assert v2(cycle)['checks']['target']['reason'] == 'branch_mismatch'


def test_v2_foreign_clone_never_selects_or_recovers_route(cycle):
    bound_writer(cycle)
    outsider = Path(cycle.temp.name) / 'outsider'
    git(cycle.repo, 'clone', '--quiet', str(cycle.repo), str(outsider))
    before = cycle.continuation_path.read_bytes()
    result = v2(cycle, worktree=str(outsider), for_action='recover', ok=False)
    assert result['reason'] == 'repository_mismatch'
    assert cycle.continuation_path.read_bytes() == before


def test_v2_corrupt_receipt_never_echoes_private_content(cycle):
    bound_writer(cycle)
    request = v2_request(cycle, 'release')
    v2(cycle, 'release', **request)
    with sqlite3.connect(cycle.continuation_path) as db:
        row = db.execute('SELECT response FROM control_requests WHERE request_id=?', (request['request_id'],)).fetchone()
        value = json.loads(row[0])
        value['reason'] = str(cycle.repo)
        db.execute('UPDATE control_requests SET response=? WHERE request_id=?', (json.dumps(value), request['request_id']))
    assert v2(cycle, 'release', ok=False, **request)['reason'] == 'invalid_state'


def test_v2_release_closes_terminal_record_restored_after_recovery(cycle):
    legacy.enroll(cycle)
    path = cycle.record_path()
    record = json.loads(path.read_text())
    path.unlink()
    v2(cycle, 'recover', **v2_request(cycle, 'recover', approved=True))
    record.update(state='completed', completed_at=record['created_at'])
    path.write_text(json.dumps(record))
    result = v2(cycle, 'release', **v2_request(cycle, 'release'))
    assert result['state'] == 'closed' and result['writer_relation'] == 'none'
