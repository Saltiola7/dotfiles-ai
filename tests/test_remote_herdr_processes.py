"""Process-exit proof uses synthetic procfs trees, never host processes."""
import importlib.util
from pathlib import Path

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
