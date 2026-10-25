"""Behavioral contracts for the default-off local advisory runner."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from continuous_validation import runner


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, text=True,
                          capture_output=True).stdout.strip()


@pytest.fixture
def worktree(tmp_path):
    primary = tmp_path / "primary"
    primary.mkdir()
    git(primary, "init", "-b", "main")
    git(primary, "config", "user.name", "Fixture")
    git(primary, "config", "user.email", "fixture@invalid")
    git(primary, "config", "commit.gpgsign", "false")
    (primary / "source.py").write_text("value = 1\n")
    (primary / "removed.py").write_text("old = True\n")
    (primary / ".gitignore").write_text(".env\nignored/\n")
    git(primary, "add", ".")
    git(primary, "commit", "-m", "base")
    target = tmp_path / "task"
    git(primary, "worktree", "add", "-b", "task", str(target))
    return target


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


def test_disabled_runner_never_executes_adapter_or_creates_state(tmp_path):
    state = tmp_path / "absent"
    config = private_json(tmp_path / "enrollment.json", {
        "schema_version": 1, "enabled": False, "state_dir": str(state)})
    result = runner.run_request({"schema_version": 1, "enrollment": str(config),
                                 "trigger": "edit", "request_id": "disabled"})
    assert result["status"] == "disabled"
    assert not state.exists()


def test_unknown_fields_and_invalid_session_fail_closed():
    with pytest.raises(runner.ValidationError):
        runner.validate_enrollment({"schema_version": 1, "enabled": False,
                                    "automatic_enable_everywhere": True})


def test_dirty_snapshot_is_clean_git_and_preserves_original_checkout(worktree, tmp_path):
    before_head = git(worktree, "rev-parse", "HEAD")
    before_index = Path(git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index")).read_bytes()
    (worktree / "source.py").write_text("value = 2\n")
    (worktree / "removed.py").unlink()
    (worktree / "new.py").write_text("new = True\n")
    (worktree / ".env").write_text("PRIVATE_FIXTURE=do-not-copy\n")
    result = runner.capture_snapshot(worktree, ["**"], tmp_path / "state", before_head)
    snapshot = Path(result["path"])
    assert (snapshot / "source.py").read_text() == "value = 2\n"
    assert (snapshot / "new.py").exists()
    assert not (snapshot / "removed.py").exists()
    assert not (snapshot / ".env").exists()
    assert git(snapshot, "status", "--porcelain", "--untracked-files=no") == ""
    assert set(git(snapshot, "diff", "--name-only", result["base"] + "...HEAD").splitlines()) == {"new.py", "removed.py", "source.py"}
    assert git(worktree, "rev-parse", "HEAD") == before_head
    assert Path(git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index")).read_bytes() == before_index


def test_snapshot_content_identity_changes_with_source_and_modes(worktree, tmp_path):
    base = git(worktree, "rev-parse", "HEAD")
    first = runner.capture_snapshot(worktree, ["**"], tmp_path / "state", base)
    second = runner.capture_snapshot(worktree, ["**"], tmp_path / "state", base)
    assert first["id"] == second["id"]
    (worktree / "source.py").chmod(0o755)
    third = runner.capture_snapshot(worktree, ["**"], tmp_path / "state", base)
    assert third["id"] != first["id"]


def test_snapshot_refuses_escaping_symlink(worktree, tmp_path):
    private = tmp_path / "private"
    private.write_text("private fixture\n")
    (worktree / "escape.py").symlink_to(private)
    with pytest.raises(runner.ValidationError):
        runner.capture_snapshot(worktree, ["**"], tmp_path / "state", git(worktree, "rev-parse", "HEAD"))


ADAPTER = r'''import json,platform,sys,time
from pathlib import Path
request=json.load(sys.stdin)
config=request.get('config',{})
action=sys.argv[1]
def check(name,kind):
    return {'id':name,'class':kind,'backend':'native','lane':{'os':sys.platform,'architecture':platform.machine(),'python':platform.python_version(),'tools':{},'dependencies':{}},'timeout_seconds':3,'cacheable':False,'configuration':{}}
if action=='describe':
    value={'schema_version':1,'adapter_id':'fixture','input_patterns':['**'],'checks':[check('quick','cheap'),check('slow','expensive')]}
elif action=='select':
    value={'schema_version':1,'checks':['unknown'] if config.get('unknown') else ['quick','slow'],'reason':'fixture scope','complete':not config.get('incomplete',False)}
else:
    Path(request['log_path']).write_text('started\n')
    time.sleep(config.get('delay',0))
    failed='fail' in (Path(request['snapshot'])/'source.py').read_text()
    Path(request['log_path']).write_text('private fixture log\n')
    value={'schema_version':1,'check_id':request['check']['id'],'status':'failed' if failed else 'passed','exit_code':1 if failed else 0,'runtime':{'python':platform.python_version()},'test_ids':['fixture::case'],'diagnostic_codes':['assertion_failed'] if failed else []}
print(json.dumps(value))
'''


@pytest.fixture
def configured(worktree, tmp_path, monkeypatch):
    adapter = worktree / '.ci/adapter.py'
    adapter.parent.mkdir()
    adapter.write_text(ADAPTER)
    git(worktree, 'add', '.ci/adapter.py')
    git(worktree, 'commit', '-m', 'fixture adapter')
    value = {
        'schema_version': 1, 'enabled': True, 'mode': 'shadow',
        'worktree': str(worktree), 'adapter': '.ci/adapter.py',
        'adapter_digest': hashlib.sha256(adapter.read_bytes()).hexdigest(),
        'adapter_python': sys.executable, 'adapter_config': {},
        'repository_id': runner.repository_id(worktree),
        'session_id': str(uuid.uuid4()), 'cycle_id': 'fixture-cycle',
        'base': git(worktree, 'rev-parse', 'HEAD'), 'state_dir': str(tmp_path / 'state'),
    }
    path = private_json(tmp_path / 'enrollment.json', value)
    monkeypatch.setattr(runner, 'cycle_open', lambda _: True)
    monkeypatch.setattr(runner, 'budget_root', lambda: tmp_path / 'shared-admission')
    monkeypatch.setattr(runner, 'pressure', lambda _: False)
    return path, value


def request(path, trigger='edit'):
    return {'schema_version': 1, 'enrollment': str(path), 'trigger': trigger}


def test_edit_runs_cheap_checks_and_retains_heavy_requirement(configured):
    path, _ = configured
    result = runner.run_request(request(path))
    assert result['status'] == 'pending'
    assert result['pending_checks'] == ['slow']
    assert [(item['check_id'], item['status']) for item in result['observations']] == [('quick', 'passed')]
    assert result['observations'][0]['executed'] is True
    assert result['observations'][0]['cache_reused'] is False


def test_checkpoint_runs_both_owned_checks_and_preserves_private_evidence(configured):
    path, value = configured
    result = runner.run_request(request(path, 'checkpoint'))
    assert result['status'] == 'passed'
    assert result['pending_checks'] == []
    assert len(result['observations']) == 2
    for observation in result['observations']:
        artifact = Path(value['state_dir']) / 'observations' / (observation['id'] + '.json')
        assert json.loads(artifact.read_text())['snapshot_id'] == result['snapshot_id']
        assert artifact.stat().st_mode & 0o077 == 0


def test_closed_task_does_not_create_state_or_execute_adapter(configured, monkeypatch):
    path, value = configured
    monkeypatch.setattr(runner, 'cycle_open', lambda _: False)
    with pytest.raises(runner.ValidationError, match='enrolled_task_closed'):
        runner.run_request(request(path))
    assert not Path(value['state_dir']).exists()


def test_selection_cannot_claim_unknown_check_or_silently_complete(configured):
    path, value = configured
    private_json(path, {**value, 'adapter_config': {'unknown': True}})
    rejected = runner.run_request(request(path))
    assert rejected['status'] == 'unavailable'
    assert rejected['error_code'] == 'invalid_selection'
    private_json(path, {**value, 'adapter_config': {'incomplete': True}})
    result = runner.run_request(request(path, 'checkpoint'))
    assert result['status'] == 'pending'
    assert 'selection_incomplete' in result['pending_checks']


def test_adapter_change_requires_explicit_reenrollment(configured):
    path, value = configured
    adapter = Path(value['worktree']) / value['adapter']
    adapter.write_text(adapter.read_text() + '\n# new adapter\n')
    with pytest.raises(runner.ValidationError, match='adapter_identity_changed'):
        runner.run_request(request(path))


def test_current_failure_uses_structured_feedback_only(configured, monkeypatch):
    from continuous_validation import feedback
    path, value = configured
    (Path(value['worktree']) / 'source.py').write_text('fail = True\n')
    delivered = []
    def deliver(enrollment, observation, **kwargs):
        delivered.append((enrollment, observation, kwargs))
        return {'status': 'accepted'}
    monkeypatch.setattr(feedback, 'deliver', deliver)
    result = runner.run_request(request(path))
    assert result['status'] == 'failed'
    assert len(delivered) == 1
    assert delivered[0][1]['diagnostic_codes'] == ['assertion_failed']
    assert 'private fixture log' not in json.dumps(result)
    assert delivered[0][2]['current_snapshot_id'] == result['snapshot_id']


def test_stop_during_execution_interrupts_result_and_suppresses_feedback(configured, monkeypatch):
    import threading
    path, value = configured
    private_json(path, {**value, 'adapter_config': {'delay': 1.0}})
    def disable_started_execution():
        import time
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            logs = Path(value['state_dir']) / 'logs'
            if logs.exists() and any('started' in item.read_text() for item in logs.glob('*.log')):
                private_json(path, {**value, 'enabled': False})
                return
            time.sleep(0.02)
        raise AssertionError('fixture check never started')
    timer = threading.Thread(target=disable_started_execution)
    timer.start()
    try:
        result = runner.run_request(request(path))
    finally:
        timer.join(12)
    assert result['status'] == 'pending'
    assert result['observations'][0]['status'] == 'interrupted'
    assert 'feedback' not in result['observations'][0]


def test_budget_serializes_expensive_checks_across_processes(tmp_path):
    import multiprocessing
    context = multiprocessing.get_context('fork')
    shared = tmp_path / 'budget'
    queue = context.Queue()
    def worker(label):
        with runner.Budget(shared, 2, 1).slot('expensive', timeout=3):
            queue.put(('start', label, __import__('time').monotonic()))
            __import__('time').sleep(0.2)
            queue.put(('end', label, __import__('time').monotonic()))
    first = context.Process(target=worker, args=('first',))
    second = context.Process(target=worker, args=('second',))
    first.start()
    second.start()
    events = [queue.get(timeout=5) for _ in range(4)]
    first.join(5)
    second.join(5)
    assert first.exitcode == second.exitcode == 0
    assert [event[0] for event in sorted(events, key=lambda item: item[2])] == ['start', 'end', 'start', 'end']


def comparison_observation(tmp_path, **changes):
    return {
        'schema_version': 1, 'id': 'observation-one', 'request_id': 'request-one',
        'snapshot_id': 'a' * 64, 'generation': 1, 'check_id': 'quick',
        'lane': {'os': 'linux', 'architecture': 'arm64', 'python': '3.14',
                 'tools': {'uv': '0.9.2'}, 'dependencies': {'uv.lock': 'f' * 64}},
        'manifest_digest': 'b' * 64, 'selection_digest': 'c' * 64, 'cache_key': 'd' * 64,
        'status': 'passed', 'exit_code': 0,
        'runtime': {'os': 'linux', 'architecture': 'arm64', 'python': '3.14.4', 'tools': {'uv': '0.9.2'}},
        'test_ids': ['fixture::case'], 'diagnostic_codes': [], 'executed': True,
        'cache_reused': False, 'queue_seconds': 0.0, 'elapsed_seconds': 1.0,
        'execution_seconds': 1.0, 'at': '2026-10-24T00:00:00+00:00',
        'log_path': str(tmp_path / 'private.log'), 'advisory': True,
        'resource_metrics': 'unavailable', 'dagger_cache_metrics': 'unavailable', **changes,
    }


def compare_pair(tmp_path, left, right, *, distinct_samples=True):
    # Independent samples share modeled inputs, not immutable observation IDs.
    if distinct_samples:
        right = dict(right)
        if right.get('id') == 'observation-one':
            right['id'] = 'observation-two'
        if right.get('request_id') == 'request-one':
            right['request_id'] = 'request-two'
    paths = [private_json(tmp_path / 'left.json', left), private_json(tmp_path / 'right.json', right)]
    return runner.compare({'schema_version': 1, 'observations': [str(path) for path in paths]})


def test_compare_refuses_different_source_or_runtime(tmp_path):
    common = comparison_observation(tmp_path)
    result = compare_pair(tmp_path, common, {**common, 'lane': {**common['lane'], 'os': 'darwin'}})
    assert result['matched'] is False
    assert result['differences'] == ['lane']


def test_compare_rejects_sparse_json_instead_of_matching_missing_fields(tmp_path):
    with pytest.raises(runner.ValidationError):
        compare_pair(tmp_path, {'schema_version': 1}, {'schema_version': 1})


@pytest.mark.parametrize('changes,field', [
    ({'runtime': {'os': 'linux', 'architecture': 'arm64', 'python': '3.13.9', 'tools': {'uv': '0.9.2'}}}, 'runtime'),
    ({'cache_key': 'e' * 64}, 'cache_key'),
    ({'test_ids': ['fixture::different_case']}, 'test_ids'),
])
def test_compare_binds_actual_runtime_cache_and_selected_tests(tmp_path, changes, field):
    common = comparison_observation(tmp_path)
    result = compare_pair(tmp_path, common, {**common, **changes})
    assert result['matched'] is False
    assert field in result['differences']


@pytest.mark.parametrize('changes', [
    {'elapsed_seconds': -1.0}, {'elapsed_seconds': float('nan')},
    {'execution_seconds': float('inf')}, {'elapsed_seconds': True},
    {'executed': 1}, {'cache_reused': 1}, {'generation': True},
    {'cache_key': 'missing'}, {'unexpected': True}, {'status': {}},
    {'runtime': {'os': {}, 'architecture': 'arm64', 'python': '3.14.4'}},
])
def test_compare_rejects_malformed_controller_observations(tmp_path, changes):
    common = comparison_observation(tmp_path)
    with pytest.raises(runner.ValidationError):
        compare_pair(tmp_path, common, {**common, **changes})


@pytest.mark.parametrize('runtime', [{}, {'python': 'identity unresolved'},
    {'capability': 'dagger_backend_unavailable'}, {'adapter_python': '3.14.4', 'os': 'linux', 'architecture': 'arm64'},
    {'os': 'darwin', 'architecture': 'arm64', 'python': '3.14.4'}])
def test_compare_marks_unknown_runtime_unqualified_even_when_equal(tmp_path, runtime):
    observation = comparison_observation(tmp_path, runtime=runtime)
    result = compare_pair(tmp_path, observation, observation)
    assert result['matched'] is False
    assert result['qualified'] is False
    assert result['status'] == 'unqualified'


def test_compare_separates_outcomes_and_cache_measurements_from_input_identity(tmp_path):
    common = comparison_observation(tmp_path)
    left = {**common, 'runtime': {**common['runtime'], 'cache': 'miss', 'cache_metrics': {'hits': 0}}}
    right = {**common, 'status': 'failed', 'exit_code': 1,
        'runtime': {**common['runtime'], 'cache': 'hit', 'cache_metrics': {'hits': 3}},
        'elapsed_seconds': 0.5, 'execution_seconds': 0.5,
        'resource_metrics': {'cpu_seconds': 0.2}}
    result = compare_pair(tmp_path, left, right)
    assert result['matched'] is True
    assert result['qualified'] is True
    assert result['statuses'] == ['passed', 'failed']
    assert result['executed'] == [True, True]
    assert result['cache_reused'] == [False, False]
    assert result['metric_availability'][0]['resource_metrics'] == 'unavailable'
    assert result['metric_availability'][1]['resource_metrics'] == 'available'


def test_default_status_has_no_state_side_effect(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'dot_local/bin/executable_continuous-validation'),
                             'status', '--json'], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'schema_version': 1, 'status': 'disabled', 'enabled': False}


def test_repeated_request_id_does_not_execute_again(configured):
    path, value = configured
    payload = {**request(path), 'request_id': 'one-operation'}
    first = runner.run_request(payload)
    second = runner.run_request(payload)
    assert second['new_execution'] is False
    assert second['coalesced_with'] == 'one-operation'
    assert second['observations'][0]['id'] == first['observations'][0]['id']
    assert len(list((Path(value['state_dir']) / 'snapshots').iterdir())) == 1
    git(Path(value['worktree']), 'commit', '--allow-empty', '-m', 'different source commit')
    with pytest.raises(runner.ValidationError, match='request_source_changed'):
        runner.run_request(payload)
    (Path(value['worktree']) / 'source.py').write_text('changed = True\n')
    with pytest.raises(runner.ValidationError, match='request_source_changed'):
        runner.run_request(payload)


def test_snapshot_git_objects_are_self_contained(worktree, tmp_path):
    result = runner.capture_snapshot(worktree, ['**'], tmp_path / 'state', git(worktree, 'rev-parse', 'HEAD'))
    snapshot = Path(result['path'])
    assert not (snapshot / '.git/objects/info/alternates').exists()
    assert git(snapshot, 'cat-file', '-t', result['base']) == 'commit'
    assert git(snapshot, 'remote') == ''


def test_private_records_and_schema_refuse_unsafe_inputs(tmp_path):
    path = private_json(tmp_path / 'record.json', {'schema_version': 1, 'enabled': False})
    path.chmod(0o644)
    with pytest.raises(runner.ValidationError, match='unsafe_private_record'):
        runner.load_enrollment(path)
    with pytest.raises(runner.ValidationError, match='unsupported_schema'):
        runner.validate_enrollment({'schema_version': True, 'enabled': False})
    with pytest.raises(runner.ValidationError, match='non_json_value'):
        runner.canonical({'value': float('nan')})


def test_status_inspects_records_without_executing_checks(configured):
    path, value = configured
    assert not Path(value['state_dir']).exists()
    result = runner.inspect_status(path)
    assert result['status'] == 'enrolled'
    assert result['latest_observations'] == []
    assert not Path(value['state_dir']).exists()
    assert result['capabilities']['dagger_runtime'] == 'adapter_owned_not_probed'


def test_unknown_termination_keeps_admission_blocked(tmp_path):
    budget = runner.Budget(tmp_path / 'budget')
    with pytest.raises(runner.UncertainTermination):
        with budget.slot('cheap'):
            raise runner.UncertainTermination('termination_unconfirmed')
    index = runner.read_private(tmp_path / 'budget/index.json')
    assert index['entries'][0]['state'] == 'unknown'
    with pytest.raises(runner.ValidationError, match='admission_completion_unknown'):
        with budget.slot('cheap'):
            raise AssertionError('must not admit')


def test_interrupted_request_id_is_not_automatically_reexecuted(configured):
    path, value = configured
    payload = {**request(path), 'request_id': 'interrupted-operation'}
    runner.private_dir(Path(value['state_dir']))
    record = Path(value['state_dir']) / 'requests/interrupted-operation.json'
    private_json(record, {'schema_version': 1, 'request_digest': runner.digest(payload),
                         'enrollment_digest': runner.digest(runner.read_private(path))})
    result = runner.run_request(payload)
    assert result['status'] == 'unavailable'
    assert result['error_code'] == 'previous_execution_interrupted'
    assert result['new_execution'] is False
    assert not (Path(value['state_dir']) / 'snapshots').exists()


def test_filtered_git_history_omits_excluded_blobs_and_is_deterministic(worktree, tmp_path):
    (worktree / '.env').write_text('PRIVATE_HISTORY_TOKEN=never-export\n')
    git(worktree, 'add', '-f', '.env')
    git(worktree, 'commit', '-m', 'historical private file')
    base = git(worktree, 'rev-parse', 'HEAD')
    first = runner.capture_snapshot(worktree, ['**'], tmp_path / 'state', base)
    second = runner.capture_snapshot(worktree, ['**'], tmp_path / 'state', base)
    assert first['commit'] == second['commit']
    def git_bytes(result):
        root = Path(result['path']) / '.git'
        return {str(item.relative_to(root)): item.read_bytes() for item in root.rglob('*') if item.is_file()}
    assert git_bytes(first) == git_bytes(second)
    snapshot = Path(first['path'])
    names = git(snapshot, 'rev-list', '--objects', '--all')
    assert '.env' not in names
    assert first['original_base'] == base
    assert git(snapshot, 'status', '--porcelain', '--untracked-files=no') == ''


def test_filtered_history_preserves_three_dot_selection_and_refuses_hidden_changes(worktree, tmp_path):
    base = git(worktree, 'rev-parse', 'HEAD')
    (worktree / 'source.py').write_text('value = 4\n')
    git(worktree, 'add', 'source.py')
    git(worktree, 'commit', '-m', 'source change')
    result = runner.capture_snapshot(worktree, ['**'], tmp_path / 'state', base)
    assert git(Path(result['path']), 'diff', '--name-only', result['base'] + '...HEAD') == 'source.py'
    (worktree / '.env').write_text('PRIVATE_HISTORY_TOKEN=hidden-change\n')
    git(worktree, 'add', '-f', '.env')
    git(worktree, 'commit', '-m', 'excluded change')
    with pytest.raises(runner.ValidationError, match='excluded_changed_input'):
        runner.capture_snapshot(worktree, ['**'], tmp_path / 'other', base)


def test_explicit_qualified_feedback_enrollment_and_closed_receipt(configured, tmp_path, capsys):
    path, value = configured
    qualification = private_json(tmp_path / 'qualification.json', {
        'schema_version': 1, 'transport': 'codex-queue', 'codex_version': '0.163.0',
        'active_delivery': True, 'idle_wake': True})
    arguments = ['enroll', '--enable-shadow', '--worktree', value['worktree'],
                 '--adapter', value['adapter'], '--session-id', value['session_id'],
                 '--cycle-id', value['cycle_id'], '--base', value['base'],
                 '--state-dir', value['state_dir'], '--enrollment', str(path)]
    assert runner.main(arguments) == 0
    assert runner.read_private(path)['feedback_enabled'] is False
    assert runner.main([*arguments, '--feedback-qualification', str(qualification)]) == 0
    enabled = runner.load_enrollment(path)
    assert enabled['feedback_enabled'] is True
    assert enabled['feedback_qualification']['qualified'] is True
    assert enabled['feedback_qualification_receipt']['assertion'] == 'operator_supplied'
    private_json(qualification, {'schema_version': 1, 'transport': 'codex-queue',
        'codex_version': '0.163.0', 'active_delivery': True, 'idle_wake': False})
    assert runner.main([*arguments, '--feedback-qualification', str(qualification)]) == 2
    assert 'invalid_feedback_receipt' in capsys.readouterr().out


def test_filtered_history_keeps_diverged_merge_base_semantics(worktree, tmp_path):
    original = git(worktree, 'rev-parse', 'HEAD')
    (worktree / 'source.py').write_text('task = True\n')
    git(worktree, 'add', 'source.py')
    git(worktree, 'commit', '-m', 'task change')
    primary = worktree.parent / 'primary'
    (primary / 'main-only.py').write_text('main = True\n')
    git(primary, 'add', 'main-only.py')
    git(primary, 'commit', '-m', 'base advanced')
    base = git(primary, 'rev-parse', 'HEAD')
    expected = git(worktree, 'diff', '--name-only', base + '...HEAD')
    result = runner.capture_snapshot(worktree, ['**'], tmp_path / 'state', base)
    assert git(Path(result['path']), 'diff', '--name-only', result['base'] + '...HEAD') == expected == 'source.py'
    assert result['original_base'] == base != original


def test_historical_blob_bytes_share_the_source_limit(worktree, tmp_path, monkeypatch):
    (worktree / 'source.py').write_text('x' * 300)
    git(worktree, 'add', 'source.py')
    git(worktree, 'commit', '-m', 'large previous source')
    base = git(worktree, 'rev-parse', 'HEAD')
    (worktree / 'source.py').write_text('x = 1\n')
    git(worktree, 'add', 'source.py')
    git(worktree, 'commit', '-m', 'small current source')
    monkeypatch.setattr(runner, 'MAX_SOURCE', 128)
    with pytest.raises(runner.ValidationError, match='source_history_limit'):
        runner.capture_snapshot(worktree, ['**'], tmp_path / 'state', base)
    assert not list((tmp_path / 'state/snapshots').iterdir())


def test_inherited_git_redirection_cannot_retarget_snapshot_mutations(worktree, tmp_path, monkeypatch):
    base = git(worktree, 'rev-parse', 'HEAD')
    monkeypatch.setenv('GIT_DIR', str(tmp_path / 'not-the-enrolled-repository'))
    monkeypatch.setenv('GIT_INDEX_FILE', str(tmp_path / 'unrelated-index'))
    result = runner.capture_snapshot(worktree, ['**'], tmp_path / 'state', base)
    assert Path(result['path'], 'source.py').read_text() == 'value = 1\n'
    assert not (tmp_path / 'unrelated-index').exists()


def test_adapter_stderr_is_bounded_before_it_reaches_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'MAX_LOG', 1024)
    log = tmp_path / 'logs/stderr.log'
    with pytest.raises(runner.Interrupted, match='log_limit'):
        runner.process([sys.executable, '-c', "import sys;sys.stderr.write('x'*10000);print('{}')"],
                       {}, tmp_path, log, 3)
    assert log.stat().st_size <= 1024


def test_enroll_preserves_venv_python_and_its_prepared_dependencies(configured, tmp_path):
    import venv
    path, value = configured
    environment = tmp_path / 'prepared-runtime'
    venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
    executable = environment / 'bin/python'
    assert executable.is_symlink()
    purelib = Path(subprocess.run([str(executable), '-c',
        "import sysconfig;print(sysconfig.get_path('purelib'))"], check=True,
        capture_output=True, text=True).stdout.strip())
    (purelib / 'prepared_dependency.py').write_text('VALUE = "present-only-in-venv"\n')
    adapter = Path(value['worktree']) / value['adapter']
    adapter.write_text(ADAPTER.replace('request=json.load(sys.stdin)',
        'import prepared_dependency\nrequest=json.load(sys.stdin)').replace(
        "'runtime':{'python':platform.python_version()}",
        "'runtime':{'python':platform.python_version(),'prefix':sys.prefix,'dependency':prepared_dependency.VALUE}"))
    assert runner.main(['enroll', '--enable-shadow', '--worktree', value['worktree'],
        '--adapter', value['adapter'], '--python', str(executable),
        '--session-id', value['session_id'], '--cycle-id', value['cycle_id'],
        '--base', value['base'], '--state-dir', value['state_dir'],
        '--enrollment', str(path)]) == 0
    assert runner.read_private(path)['adapter_python'] == str(executable)
    result = runner.run_request(request(path, 'checkpoint'))
    assert result['status'] == 'passed'
    assert all(item['runtime']['prefix'] == str(environment) for item in result['observations'])
    assert all(item['runtime']['dependency'] == 'present-only-in-venv' for item in result['observations'])


@pytest.mark.parametrize('mutate_source', [False, True])
def test_declared_build_metadata_is_ignored_but_captured_source_remains_immutable(configured, mutate_source):
    path, value = configured
    adapter = Path(value['worktree']) / value['adapter']
    source = ADAPTER.replace("'input_patterns':['**']", "'input_patterns':['**','!build/fixture.egg-info/**']")
    source = source.replace("    time.sleep(config.get('delay',0))", """    metadata=Path(request['snapshot'])/'build/fixture.egg-info/PKG-INFO'
    metadata.parent.mkdir(parents=True,exist_ok=True)
    metadata.write_text('generated packaging metadata\\n')
    if config.get('mutate_source'):
        captured=Path(request['snapshot'])/'source.py'
        captured.chmod(0o644)
        captured.write_text('changed = True\\n')
    time.sleep(config.get('delay',0))""")
    adapter.write_text(source)
    private_json(path, {**value, 'adapter_digest': hashlib.sha256(source.encode()).hexdigest(),
                        'adapter_config': {'mutate_source': mutate_source}})
    result = runner.run_request(request(path, 'checkpoint'))
    if mutate_source:
        assert result['status'] == 'unavailable'
        assert all('snapshot_modified_by_check' in item['diagnostic_codes'] for item in result['observations'])
    else:
        assert result['status'] == 'passed'
        assert all(item['status'] == 'passed' for item in result['observations'])
    assert (Path(value['worktree']) / 'source.py').read_text() == 'value = 1\n'


def test_declared_excluded_history_never_travels_and_tracked_changes_refuse(worktree, tmp_path):
    metadata = worktree / 'build/fixture.egg-info/PKG-INFO'
    metadata.parent.mkdir(parents=True)
    metadata.write_text('PRIVATE_BUILD_METADATA=do-not-export\n')
    git(worktree, 'add', 'build')
    git(worktree, 'commit', '-m', 'existing generated metadata')
    base = git(worktree, 'rev-parse', 'HEAD')
    patterns = ['**', '!build/fixture.egg-info/**']
    result = runner.capture_snapshot(worktree, patterns, tmp_path / 'state', base)
    snapshot = Path(result['path'])
    assert not (snapshot / 'build/fixture.egg-info/PKG-INFO').exists()
    assert 'PKG-INFO' not in git(snapshot, 'rev-list', '--objects', '--all')
    before = runner.inventory(worktree, patterns, content=False)
    metadata.write_text('changed excluded tracked metadata\n')
    assert runner.inventory(worktree, patterns, content=False) == before
    with pytest.raises(runner.ValidationError, match='excluded_changed_input'):
        runner.capture_snapshot(worktree, patterns, tmp_path / 'dirty', base)
    git(worktree, 'add', 'build')
    git(worktree, 'commit', '-m', 'excluded metadata changed')
    with pytest.raises(runner.ValidationError, match='excluded_changed_input'):
        runner.capture_snapshot(worktree, patterns, tmp_path / 'committed', base)


@pytest.mark.parametrize('patterns', [['**', '!'], ['**', '!../escape'], ['**', '!/absolute'], ['!build/**']])
def test_input_exclusions_require_positive_and_safe_nonempty_relative_globs(worktree, tmp_path, patterns):
    with pytest.raises(runner.ValidationError):
        runner.capture_snapshot(worktree, patterns, tmp_path / 'state', git(worktree, 'rev-parse', 'HEAD'))


def test_abrupt_controller_exit_does_not_reclaim_recorded_running_lease(tmp_path):
    shared = tmp_path / 'budget'
    script = """import os,sys
sys.path.insert(0,sys.argv[1])
from continuous_validation import runner
with runner.Budget(sys.argv[2],1,1).slot('cheap',timeout=3):
    os._exit(23)
"""
    exited = subprocess.run([sys.executable, '-c', script,
        str(ROOT / 'private_dot_config/dotfiles-ai'), str(shared)], timeout=5)
    assert exited.returncode == 23
    assert runner.read_private(shared / 'index.json')['entries'][0]['state'] == 'running'
    with pytest.raises(runner.ValidationError, match='admission_completion_unknown'):
        with runner.Budget(shared, 1, 1).slot('cheap', timeout=1):
            raise AssertionError('unconfirmed execution must keep its slot charged')
    assert runner.read_private(shared / 'index.json')['entries'][0]['state'] == 'running'


def test_abrupt_queued_exit_can_be_reclaimed_without_running_work(tmp_path):
    import time
    shared = tmp_path / 'budget'
    budget = runner.Budget(shared, 1, 1)
    script = """import sys
sys.path.insert(0,sys.argv[1])
from continuous_validation import runner
with runner.Budget(sys.argv[2],1,1).slot('cheap',timeout=10):
    raise AssertionError('parent still owns only slot')
"""
    with budget.slot('cheap', timeout=2):
        queued = subprocess.Popen([sys.executable, '-c', script,
            str(ROOT / 'private_dot_config/dotfiles-ai'), str(shared)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if any(item['state'] == 'queued' for item in runner.read_private(shared / 'index.json')['entries']):
                    break
                time.sleep(0.02)
            else:
                raise AssertionError('fixture did not queue')
            queued.kill()
            queued.wait(timeout=2)
        finally:
            if queued.poll() is None:
                queued.kill()
            queued.communicate(timeout=2)
    with budget.slot('cheap', timeout=1):
        assert len(runner.read_private(shared / 'index.json')['entries']) == 1
    assert runner.read_private(shared / 'index.json')['entries'] == []


@pytest.mark.parametrize('same_observation', [False, True])
def test_compare_never_counts_one_request_as_two_samples(tmp_path, same_observation):
    common = comparison_observation(tmp_path)
    right = {**common, 'id': common['id'] if same_observation else 'observation-two'}
    result = compare_pair(tmp_path, common, right, distinct_samples=False)
    assert result['matched'] is False
    assert result['status'] == 'unqualified'
    assert all('duplicate_sample' in reasons for reasons in result['qualification_reasons'])
