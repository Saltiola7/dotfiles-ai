"""The shared metadata writer binds a real shallow checkout without credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest
from test_integration_gitproof import run, commit

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / '.github/actions/ci-candidate-receipt/write_receipt.py'


@pytest.fixture
def checkout(tmp_path):
    objects = tmp_path / 'objects.git'
    run(tmp_path, 'init', '--bare', '--template=', str(objects))
    base = commit(objects, {'a.txt': 'base'}, None, 'base')
    head = commit(objects, {'a.txt': 'feature'}, base, 'phase')
    tree = run(objects, 'rev-parse', head + '^{tree}')
    tested = run(objects, 'commit-tree', tree, '-p', base, '-p', head, data='Candidate\n')
    run(objects, 'update-ref', 'refs/heads/tested', tested)
    run(objects, 'symbolic-ref', 'HEAD', 'refs/heads/tested')
    work = tmp_path / 'workspace with spaces'
    run(tmp_path, 'clone', '--depth=1', objects.as_uri(), str(work))
    assert run(work, 'rev-parse', '--is-shallow-repository') == 'true'
    temporary = tmp_path / 'runner temp'; temporary.mkdir()
    env = {key: os.environ[key] for key in ('PATH', 'TMPDIR', 'LANG') if key in os.environ}
    env.update(GITHUB_REPOSITORY='example/repo', GITHUB_SHA=tested, GITHUB_RUN_ID='71',
        GITHUB_RUN_ATTEMPT='2', GITHUB_EVENT_NAME='pull_request', GITHUB_JOB='scan',
        GITHUB_WORKSPACE=str(work), RUNNER_TEMP=str(temporary),
        DBSCTR_RECEIPT_SOURCE_HEAD=head, DBSCTR_RECEIPT_PR_NUMBER='5',
        DBSCTR_RECEIPT_CONCERN='semgrep/ci', DBSCTR_RECEIPT_RESULT='success',
        GITHUB_TOKEN='fixture-secret-never-output', GIT_DIR='/does/not/exist')
    return work, temporary, env, base, head, tested, tree


def invoke(checkout, changes=None):
    work, _, env, *_ = checkout
    return subprocess.run([sys.executable, '-I', '-B', str(WRITER)], cwd=work,
        env={**env, **(changes or {})}, text=True, capture_output=True, timeout=15)


def test_shallow_receipt_matches_raw_parents_and_safe_native_identity(checkout):
    work, temporary, _, base, head, tested, tree = checkout
    before = sorted(path.name for path in temporary.iterdir())
    result = invoke(checkout)
    assert result.returncode == 0, result.stderr
    key, filename = result.stdout.strip().split('=', 1)
    assert key == 'receipt-path'
    path = Path(filename)
    assert path.name == 'receipt.json' and path.parent.parent == temporary
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    value = json.loads(path.read_text())
    assert value == {'schema_version': 1, 'repository': 'example/repo', 'pr_number': 5,
        'source_head': head, 'tested_oid': tested, 'tree': tree, 'tested_parents': [base, head],
        'base': base, 'run_id': 71, 'attempt': 2, 'event': 'pull_request', 'job': 'scan',
        'concern': 'semgrep/ci', 'result': 'success'}
    assert 'fixture-secret' not in result.stdout + result.stderr + path.read_text()
    assert len(list(temporary.iterdir())) == len(before) + 1
    assert run(work, 'rev-parse', '--is-shallow-repository') == 'true'


@pytest.mark.parametrize('changes', [
    {'GITHUB_SHA': 'f' * 40}, {'DBSCTR_RECEIPT_SOURCE_HEAD': 'e' * 40},
    {'GITHUB_EVENT_NAME': 'pull_request_target'}, {'GITHUB_RUN_ATTEMPT': 'false'},
    {'DBSCTR_RECEIPT_PR_NUMBER': '0'}, {'DBSCTR_RECEIPT_CONCERN': 'unsafe\noutput=x'},
    {'DBSCTR_RECEIPT_RESULT': 'neutral'}, {'GITHUB_REPOSITORY': '../other'},
])
def test_invalid_identity_fails_before_output_or_artifact_creation(checkout, changes):
    _, temporary, *_ = checkout
    result = invoke(checkout, changes)
    assert result.returncode != 0
    assert not result.stdout
    assert not list(temporary.iterdir())
    assert 'fixture-secret' not in result.stderr


def test_failure_receipt_never_turns_failure_into_success(checkout):
    result = invoke(checkout, {'DBSCTR_RECEIPT_RESULT': 'failure'})
    assert result.returncode == 0, result.stderr
    value = json.loads(Path(result.stdout.strip().split('=', 1)[1]).read_text())
    assert value['result'] == 'failure'


def test_action_has_no_credential_input_or_expression_in_shell_source():
    action = (WRITER.parent / 'action.yml').read_text()
    assert 'token:' not in action and 'checkout@' not in action and 'upload-artifact@' not in action
    shell_source = action.split('run:', 1)[1]
    assert '${{' not in shell_source
    assert 'python3 -I -B' in shell_source
    assert '"$GITHUB_ACTION_PATH/write_receipt.py"' in shell_source
