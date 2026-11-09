"""Linux same-user process identity/exit checks; never signal or inspect env."""
import errno
import os
from pathlib import Path
import re
import stat
import time

SESSION = re.compile(r'ses_[A-Za-z0-9]+\Z')
MAX_PROCESSES = 65536


class ProcessProofError(ValueError):
    """An observation gap blocks target activation, without private diagnostics."""


def _bounded(fd: int, limit: int) -> bytes:
    if type(limit) is not int or limit < 0:
        raise ProcessProofError('process observation bound invalid')
    chunks = []
    left = limit + 1
    while left:
        part = os.read(fd, min(left, 65536))
        if not part:
            break
        chunks.append(part)
        left -= len(part)
    value = b''.join(chunks)
    if len(value) > limit:
        raise ProcessProofError('process observation exceeds bound')
    return value


def read(path: Path, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ProcessProofError('process observation ownership unavailable')
        return _bounded(fd, limit)
    finally:
        os.close(fd)


def _task_directory(directory: Path) -> int:
    # Only a caller-selected proc root's literal PID child, never self or links.
    if not re.fullmatch(r'[1-9][0-9]{0,19}', directory.name):
        raise ProcessProofError('process directory unsafe')
    return os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)


def _check_task_file(fd: int, owners: set[int]) -> None:
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid not in owners
            or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        raise ProcessProofError('process observation ownership unavailable')


def _task_file(directory_fd: int, name: str, limit: int) -> bytes:
    """Scoped kernel files may be root-owned when the task is nondumpable."""
    directory_info = os.fstat(directory_fd)
    if not stat.S_ISDIR(directory_info.st_mode):
        raise ProcessProofError('process directory unsafe')
    owners = {0, os.getuid()}
    if name == 'status':
        owners.add(directory_info.st_uid)
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        _check_task_file(fd, owners)
        value = _bounded(fd, limit)
        _check_task_file(fd, owners)
        return value
    finally:
        os.close(fd)


def _task_uid_fd(directory_fd: int) -> int | None:
    raw = _task_file(directory_fd, 'status', 65536)
    lines = [line for line in raw.splitlines() if line.startswith(b'Uid:')]
    if len(lines) != 1:
        raise ProcessProofError('process ownership unavailable')
    values = lines[0][4:].split()
    if len(values) != 4 or any(not re.fullmatch(rb'[0-9]{1,10}', value) for value in values):
        raise ProcessProofError('process ownership unavailable')
    uids = [int(value) for value in values]
    if any(uid > 4294967295 for uid in uids):
        raise ProcessProofError('process ownership unavailable')
    ours = os.getuid()
    if all(uid == ours for uid in uids):
        return ours
    if ours not in uids:
        return None
    raise ProcessProofError('process ownership ambiguous')


def task_uid(directory: Path) -> int | None:
    """Prove all four kernel UIDs ours, or prove none ours; unknown is an error.

    directory is a literal PID child of the caller's known proc root (a fake
    root may be supplied by tests). Status contents never enter diagnostics.
    """
    fd = _task_directory(directory)
    try:
        return _task_uid_fd(fd)
    finally:
        os.close(fd)


def task_read(directory: Path, name: str, limit: int) -> bytes:
    """Read only stat/cmdline, bracketed by same-task kernel UID proofs."""
    if name not in {'stat', 'cmdline'}:
        raise ProcessProofError('process observation name invalid')
    fd = _task_directory(directory)
    try:
        if _task_uid_fd(fd) != os.getuid():
            raise ProcessProofError('process ownership changed')
        value = _task_file(fd, name, limit)
        if _task_uid_fd(fd) != os.getuid():
            raise ProcessProofError('process ownership changed')
        return value
    finally:
        os.close(fd)


def identity(directory: Path, pid: int) -> tuple[str, int]:
    if directory.name != str(pid):
        raise ProcessProofError('process identity unavailable')
    raw = task_read(directory, 'stat', 65536)
    try:
        prefix, rest = raw.rsplit(b')', 1)
        if not prefix.startswith(str(pid).encode() + b' ('):
            raise ValueError()
        fields = rest.split()
        state, ticks = fields[0].decode('ascii'), int(fields[19])
        if state not in {'R', 'S', 'D', 'Z', 'T', 't', 'X', 'I', 'P'} or ticks < 0:
            raise ValueError()
        return state, ticks
    except (ValueError, IndexError, UnicodeError):
        raise ProcessProofError('process identity unavailable') from None


def references(raw: bytes) -> set[str]:
    try:
        argv = raw.rstrip(b'\0').decode('utf-8').split('\0')
    except UnicodeError:
        raise ProcessProofError('process arguments unavailable') from None
    result = set()
    for index, argument in enumerate(argv):
        if argument in {'--session', '-s'} and index + 1 < len(argv):
            result.add(argv[index + 1])
        elif argument.startswith('--session='):
            result.add(argument.partition('=')[2])
    return result


def scan_sessions(sessions: set[str], root: Path = Path('/proc')) -> list[dict]:
    """Identify exact CLI session references; missing references are not identity proof."""
    if any(not isinstance(value, str) or not SESSION.fullmatch(value) for value in sessions):
        raise ProcessProofError('invalid session identity set')
    deadline = time.monotonic() + 5.0
    for attempt in range(26):
        result = []
        try:
            with os.scandir(root) as entries:
                count = 0
                for entry in entries:
                    if not entry.name.isascii() or not entry.name.isdecimal():
                        continue
                    count += 1
                    if count > MAX_PROCESSES:
                        raise ProcessProofError('process inventory exceeds bound')
                    directory = root / entry.name
                    if not re.fullmatch(r'[1-9][0-9]{0,19}', entry.name):
                        raise ProcessProofError('process directory unsafe')
                    pid = int(entry.name)
                    info = entry.stat(follow_symlinks=False)
                    if not stat.S_ISDIR(info.st_mode):
                        raise ProcessProofError('process directory unsafe')
                    if task_uid(directory) is None:
                        continue
                    before = identity(directory, pid)
                    if before[0] in {'Z', 'X'}:
                        continue
                    refs = references(task_read(directory, 'cmdline', 1024 * 1024))
                    after = identity(directory, pid)
                    if before[1] != after[1]:
                        raise ProcessProofError('process session ownership ambiguous')
                    if after[0] in {'Z', 'X'}:
                        continue
                    relevant = refs & sessions
                    if not relevant:
                        continue
                    if pid == 1:
                        raise ProcessProofError('process identity unsupported')
                    if len(refs) != 1 or len(relevant) != 1:
                        raise ProcessProofError('process session ownership ambiguous')
                    result.append({'pid': pid, 'start_ticks': before[1], 'session_id': next(iter(relevant))})
            return sorted(result, key=lambda item: item['pid'])
        except OSError as error:
            # Discard the entire partial inventory, not just the vanished PID.
            remaining = deadline - time.monotonic()
            if error.errno in {errno.ENOENT, errno.ESRCH} and attempt < 25 and remaining > 0:
                time.sleep(min(0.2, remaining))
                continue
            raise ProcessProofError('process inventory unavailable') from None
    raise ProcessProofError('process inventory unavailable')


def assert_absent(sessions: set[str], captured: list[dict], root: Path = Path('/proc')) -> None:
    """Require captured identities gone AND no newly observed matching session."""
    if scan_sessions(sessions, root):
        raise ProcessProofError('source session still running')
    for item in captured:
        if (not isinstance(item, dict) or set(item) != {'pid', 'start_ticks', 'session_id'}
                or type(item['pid']) is not int or item['pid'] <= 1
                or type(item['start_ticks']) is not int or item['start_ticks'] < 0
                or item['session_id'] not in sessions):
            raise ProcessProofError('captured process identity invalid')
        try:
            directory = root / str(item['pid'])
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise ProcessProofError('process directory unsafe')
            if task_uid(directory) != os.getuid():
                raise ProcessProofError('process ownership changed')
            state, ticks = identity(directory, item['pid'])
            if state not in {'Z', 'X'} and ticks == item['start_ticks']:
                raise ProcessProofError('source process still running')
        except OSError as error:
            if error.errno in {errno.ENOENT, errno.ESRCH}:
                continue
            raise ProcessProofError('source process exit unavailable') from None
