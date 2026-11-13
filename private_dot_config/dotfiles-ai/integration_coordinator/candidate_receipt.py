"""Credential-free PR identity metadata; native success is verified separately."""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from . import core as c
from .gitproof import GitObjects

ENV_FIELDS = (
    'GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
    'GITHUB_EVENT_NAME', 'GITHUB_JOB', 'GITHUB_WORKSPACE', 'RUNNER_TEMP',
    'DBSCTR_RECEIPT_SOURCE_HEAD', 'DBSCTR_RECEIPT_PR_NUMBER',
    'DBSCTR_RECEIPT_CONCERN', 'DBSCTR_RECEIPT_RESULT',
)


def _number(value: str) -> int:
    c._require(re.fullmatch(r'[1-9][0-9]{0,15}', value) is not None, 'receipt_number')
    result = int(value)
    c._integer(result)
    return result


def _directory(value: str) -> Path:
    c._require(0 < len(value) <= 4096 and not any(ord(ch) < 32 or ord(ch) == 127 for ch in value), 'receipt_directory')
    path = Path(value)
    c._require(path.is_absolute() and not path.is_symlink() and path.is_dir(), 'receipt_directory')
    return path.resolve(strict=True)


def collect(identity: Mapping[str, str], workspace: Path) -> dict[str, object]:
    repository, tested, source = identity['GITHUB_REPOSITORY'], identity['GITHUB_SHA'], identity['DBSCTR_RECEIPT_SOURCE_HEAD']
    c._repository(repository)
    c._oid(tested)
    c._oid(source)
    c._require(len(tested) == len(source) and identity['GITHUB_EVENT_NAME'] == 'pull_request', 'receipt_event')
    job, concern, result = identity['GITHUB_JOB'], identity['DBSCTR_RECEIPT_CONCERN'], identity['DBSCTR_RECEIPT_RESULT']
    c._require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,99}', job) is not None, 'receipt_job')
    c._require(0 < len(concern) <= 128 and all(32 <= ord(ch) < 127 for ch in concern), 'receipt_concern')
    c._require(result in {'success', 'failure', 'cancelled', 'skipped'}, 'receipt_result')
    run, attempt, pr = (_number(identity[name]) for name in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'DBSCTR_RECEIPT_PR_NUMBER'))
    objects = GitObjects(workspace)
    c._require(objects.read('rev-parse', '--verify', 'HEAD^{commit}') == tested, 'receipt_head')
    raw = objects._result(('cat-file', 'commit', tested))[1]
    # Git's object ID is an identity, not a new signature or execution attestation.
    framed = b'commit ' + str(len(raw)).encode('ascii') + b'\0' + raw
    computed = hashlib.new('sha1' if len(tested) == 40 else 'sha256', framed, usedforsecurity=False).hexdigest()
    c._require(computed == tested, 'receipt_object_identity')
    headers, separator, _ = raw.partition(b'\n\n')
    c._require(bool(separator), 'receipt_commit_headers')
    trees = [line[5:].decode('ascii') for line in headers.splitlines() if line.startswith(b'tree ')]
    parents = [line[7:].decode('ascii') for line in headers.splitlines() if line.startswith(b'parent ')]
    c._require(len(trees) == 1 and len(parents) == 2 and parents[1] == source, 'receipt_parents')
    for oid in (*trees, *parents):
        c._oid(oid)
        c._require(len(oid) == len(tested), 'mixed_oid_formats')
    return {'schema_version': 1, 'repository': repository, 'pr_number': pr, 'source_head': source,
        'tested_oid': tested, 'tree': trees[0], 'tested_parents': parents, 'base': parents[0],
        'run_id': run, 'attempt': attempt, 'event': 'pull_request', 'job': job,
        'concern': concern, 'result': result}


def write(identity: Mapping[str, str]) -> Path:
    workspace = _directory(identity['GITHUB_WORKSPACE'])
    temporary = _directory(identity['RUNNER_TEMP'])
    payload = c._canonical(collect(identity, workspace)) + b'\n'
    c._require(len(payload) <= 8192, 'receipt_size')
    directory = Path(tempfile.mkdtemp(prefix='dbsctr-ci-candidate-', dir=temporary))
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        owned = os.fstat(descriptor)
        c._require(stat.S_ISDIR(owned.st_mode) and owned.st_uid == os.getuid()
            and not owned.st_mode & 0o077, 'receipt_custody')
        fd = os.open('receipt.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=descriptor)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, c.Invalid):
        try:
            os.unlink('receipt.json', dir_fd=descriptor)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(descriptor)
    return directory / 'receipt.json'


def main() -> int:
    try:
        # Read an explicit allowlist only. Credentials and the event body are not
        # inputs and never appear in subprocesses, metadata or diagnostics.
        identity = {name: os.environ[name] for name in ENV_FIELDS}
        path = write(identity)
        print('receipt-path=' + str(path))
        return 0
    except (KeyError, UnicodeError, OSError, c.Invalid, c.Unavailable):
        print('candidate_receipt_unavailable', file=sys.stderr)
        return 1
