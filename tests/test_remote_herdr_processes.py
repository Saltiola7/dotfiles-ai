"""Process-exit proof uses synthetic procfs trees, never host processes."""
import importlib.util
import errno
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parents[1]


def module():
    spec = importlib.util.spec_from_file_location('remote_herdr_processes',
        ROOT / 'dot_local/share/dotfiles-ai/remote-herdr/processes.py')
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def process(root, pid, argv, *, start=20, state='S'):
    path = root / str(pid)
    path.mkdir(exist_ok=True)
    (path / 'status').write_text('Name:\tfixture\nUid:\t' + '\t'.join([str(os.getuid())] * 4) + '\n')
    (path / 'cmdline').write_bytes(b'\0'.join(part.encode() for part in argv) + b'\0')
    fields = [state, *(['0'] * 18), str(start), '0', '0']
    (path / 'stat').write_text(f'{pid} (fixture (nested) name) ' + ' '.join(fields))
    return path


def test_scan_binds_exact_session_to_pid_and_start_time(tmp_path):
    core = module()
    process(tmp_path, 101, ['opencode', '--server', 'http://fixture', '--session', 'ses_saved'])
    process(tmp_path, 102, ['opencode', '--session=ses_other'])
    assert core.scan_sessions({'ses_saved'}, tmp_path) == [
        {'pid': 101, 'start_ticks': 20, 'session_id': 'ses_saved'}]


def test_source_exit_not_inferred_from_socket_or_changed_arguments(tmp_path):
    core = module()
    path = process(tmp_path, 101, ['opencode', '-s', 'ses_saved'])
    saved = core.scan_sessions({'ses_saved'}, tmp_path)
    (path / 'cmdline').write_bytes(b'bash\0')
    with pytest.raises(core.ProcessProofError):
        core.assert_absent({'ses_saved'}, saved, tmp_path)
    process(tmp_path, 101, ['bash'], start=21)
    core.assert_absent({'ses_saved'}, saved, tmp_path)


def test_new_duplicate_after_source_exit_still_blocks(tmp_path):
    core = module()
    process(tmp_path, 201, ['opencode', '--session', 'ses_saved'])
    with pytest.raises(core.ProcessProofError):
        core.assert_absent({'ses_saved'}, [], tmp_path)


def test_zombies_are_not_live_agents(tmp_path):
    core = module()
    process(tmp_path, 101, ['opencode', '--session', 'ses_saved'], state='Z')
    assert core.scan_sessions({'ses_saved'}, tmp_path) == []


def test_ambiguous_or_unreadable_candidate_refuses_without_private_output(tmp_path):
    core = module()
    path = process(tmp_path, 101, ['opencode', '--session', 'ses_saved', '-s', 'ses_other'])
    with pytest.raises(core.ProcessProofError) as captured:
        core.scan_sessions({'ses_saved'}, tmp_path)
    assert str(tmp_path) not in str(captured.value) and 'ses_saved' not in str(captured.value)
    (path / 'cmdline').write_bytes(b'opencode\0--session\0ses_saved\0')
    (path / 'stat').write_text('private malformed process data')
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)


def test_state_transition_does_not_change_identity(tmp_path, monkeypatch):
    core = module()
    path = process(tmp_path, 101, ['unapproved-agent', '-s', 'ses_saved'])
    original = core.identity
    calls = 0

    def identity(directory, pid):
        nonlocal calls
        calls += 1
        if calls == 2:
            (path / 'stat').write_text((path / 'stat').read_text().replace(') S ', ') R '))
        return original(directory, pid)

    monkeypatch.setattr(core, 'identity', identity)
    assert core.scan_sessions({'ses_saved'}, tmp_path)[0]['start_ticks'] == 20


def test_tick_transition_refuses(tmp_path, monkeypatch):
    core = module()
    process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    original = core.identity
    calls = 0

    def identity(directory, pid):
        nonlocal calls
        calls += 1
        state, ticks = original(directory, pid)
        return state, ticks + (calls == 2)

    monkeypatch.setattr(core, 'identity', identity)
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)


@pytest.mark.parametrize('stage', ['initial', 'cmdline', 'final'])
@pytest.mark.parametrize('code', [errno.ENOENT, errno.ESRCH])
def test_disappearance_restarts_complete_inventory(tmp_path, monkeypatch, stage, code):
    core = module()
    process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    process(tmp_path, 102, ['agent', '-s', 'ses_saved'])
    original = core.task_read
    identities = 0
    failed = False
    visits = []

    def task_read(directory, name, limit):
        nonlocal identities, failed
        if directory.name == '101':
            visits.append(name)
            if name == 'stat':
                identities += 1
            target = (stage == 'initial' and identities == 1 and name == 'stat'
                      or stage == 'cmdline' and name == 'cmdline'
                      or stage == 'final' and identities == 2 and name == 'stat')
            if target and not failed:
                failed = True
                raise OSError(code, 'private fixture')
        return original(directory, name, limit)

    monkeypatch.setattr(core, 'task_read', task_read)
    assert [item['pid'] for item in core.scan_sessions({'ses_saved'}, tmp_path)] == [101, 102]
    assert failed and visits.count('stat') >= 3


def test_persistent_disappearance_refuses_after_three_attempts(tmp_path, monkeypatch):
    core = module()
    process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    calls = []

    def task_read(*args):
        calls.append(args)
        raise OSError(errno.ESRCH, 'private fixture')

    monkeypatch.setattr(core, 'task_read', task_read)
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)
    assert len(calls) == 3


def test_kernel_uid_not_inode_owner_proves_own_task(tmp_path, monkeypatch):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    original = core.os.fstat

    def root_metadata(fd):
        info = original(fd)
        return SimpleNamespace(st_mode=info.st_mode, st_uid=0)

    monkeypatch.setattr(core.os, 'fstat', root_metadata)
    assert core.task_uid(path) == os.getuid()
    assert core.scan_sessions({'ses_saved'}, tmp_path)[0]['pid'] == 101
    if os.getuid() != 0:
        with pytest.raises(core.ProcessProofError):
            core.read(path / 'cmdline', 1024)


def test_foreign_kernel_uid_skips_even_caller_owned_directory(tmp_path):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    foreign = os.getuid() + 1
    (path / 'status').write_text('Uid:\t' + '\t'.join([str(foreign)] * 4) + '\n')
    assert core.task_uid(path) is None
    assert core.scan_sessions({'ses_saved'}, tmp_path) == []
    with pytest.raises(core.ProcessProofError):
        core.task_read(path, 'cmdline', 1024)


@pytest.mark.parametrize('status', ['', 'Uid: 1 2 3', 'Uid: 1 2 3 x',
                                    'Uid: -1 -1 -1 -1', 'Uid: 1 2 3 4 5'])
def test_missing_or_malformed_uid_refuses(tmp_path, status):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    (path / 'status').write_text(status)
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)


def test_mixed_uid_and_unreadable_status_refuse(tmp_path, monkeypatch):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    (path / 'status').write_text(f'Uid: {os.getuid()} {os.getuid() + 1} 0 0\n')
    with pytest.raises(core.ProcessProofError):
        core.task_uid(path)
    original = core.os.open

    def unreadable(name, *args, **kwargs):
        if str(name) == 'status' or Path(name).name == 'status':
            raise PermissionError('private fixture')
        return original(name, *args, **kwargs)

    monkeypatch.setattr(core.os, 'open', unreadable)
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)


def test_captured_uid_change_is_not_absence(tmp_path):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    saved = core.scan_sessions({'ses_saved'}, tmp_path)
    foreign = os.getuid() + 1
    (path / 'status').write_text('Uid: ' + ' '.join([str(foreign)] * 4))
    with pytest.raises(core.ProcessProofError):
        core.assert_absent({'ses_saved'}, saved, tmp_path)


def test_matching_pid_one_refuses(tmp_path):
    core = module()
    process(tmp_path, 1, ['agent', '-s', 'ses_saved'])
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)


def test_inventory_bound_counts_only_numeric_entries(tmp_path, monkeypatch):
    core = module()
    monkeypatch.setattr(core, 'MAX_PROCESSES', 1)
    for name in ['cpuinfo', 'self', 'other']:
        (tmp_path / name).mkdir()
    process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    assert len(core.scan_sessions({'ses_saved'}, tmp_path)) == 1
    process(tmp_path, 102, ['agent'])
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)


@pytest.mark.parametrize('name', ['status', 'stat', 'cmdline'])
def test_symlink_and_writable_task_files_refuse(tmp_path, name):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    target = path / name
    target.chmod(0o664)
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)
    target.chmod(0o644)
    destination = tmp_path / 'private-fixture'
    target.rename(destination)
    target.symlink_to(destination)
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)


def test_task_directory_link_and_non_pid_names_refuse(tmp_path):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    (tmp_path / '102').symlink_to(path, target_is_directory=True)
    with pytest.raises(core.ProcessProofError):
        core.scan_sessions({'ses_saved'}, tmp_path)
    for directory in [tmp_path / 'self', tmp_path / '0', tmp_path / '01']:
        with pytest.raises(core.ProcessProofError):
            core.task_uid(directory)
    for name in ['status', '../status', '/stat', 'environ']:
        with pytest.raises(core.ProcessProofError):
            core.task_read(path, name, 1024)


def test_task_reads_and_status_are_bounded(tmp_path):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    with pytest.raises(core.ProcessProofError):
        core.task_read(path, 'cmdline', 1)
    with pytest.raises(core.ProcessProofError):
        core.read(path / 'cmdline', 1)
    (path / 'status').write_bytes(b'x' * 65537)
    with pytest.raises(core.ProcessProofError):
        core.task_uid(path)


def test_generic_read_still_refuses_foreign_owned_regular_file(tmp_path, monkeypatch):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    original = core.os.fstat

    def foreign_metadata(fd):
        info = original(fd)
        return SimpleNamespace(st_mode=info.st_mode, st_uid=os.getuid() + 1)

    monkeypatch.setattr(core.os, 'fstat', foreign_metadata)
    with pytest.raises(core.ProcessProofError):
        core.read(path / 'cmdline', 1024)


def test_uid_change_during_task_read_refuses(tmp_path, monkeypatch):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    original = core._task_file

    def changing(directory_fd, name, limit):
        value = original(directory_fd, name, limit)
        if name == 'cmdline':
            foreign = os.getuid() + 1
            (path / 'status').write_text('Uid: ' + ' '.join([str(foreign)] * 4))
        return value

    monkeypatch.setattr(core, '_task_file', changing)
    with pytest.raises(core.ProcessProofError):
        core.task_read(path, 'cmdline', 1024)


def test_final_zombie_is_not_captured(tmp_path, monkeypatch):
    core = module()
    process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    original = core.identity
    calls = 0

    def identity(directory, pid):
        nonlocal calls
        calls += 1
        state, ticks = original(directory, pid)
        return ('Z' if calls == 2 else state), ticks

    monkeypatch.setattr(core, 'identity', identity)
    assert core.scan_sessions({'ses_saved'}, tmp_path) == []


@pytest.mark.parametrize('code', [errno.ENOENT, errno.ESRCH])
def test_captured_kernel_disappearance_is_absence(tmp_path, monkeypatch, code):
    core = module()
    process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    captured = core.scan_sessions({'ses_saved'}, tmp_path)
    # Model a complete empty inventory followed by disappearance of captured PID.
    monkeypatch.setattr(core, 'scan_sessions', lambda sessions, root: [])

    def gone(directory, pid):
        raise OSError(code, 'private fixture')

    monkeypatch.setattr(core, 'identity', gone)
    core.assert_absent({'ses_saved'}, captured, tmp_path)


def test_duplicate_uid_fields_refuse(tmp_path):
    core = module()
    path = process(tmp_path, 101, ['agent', '-s', 'ses_saved'])
    status = path / 'status'
    status.write_text(status.read_text() * 2)
    with pytest.raises(core.ProcessProofError):
        core.task_uid(path)
