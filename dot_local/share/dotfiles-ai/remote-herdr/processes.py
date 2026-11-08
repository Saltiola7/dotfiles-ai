"""Linux same-user process identity/exit checks; never signal or inspect env."""
import os
from pathlib import Path
import re
import stat

SESSION = re.compile(r'ses_[A-Za-z0-9]+\Z')
MAX_PROCESSES = 65536


class ProcessProofError(ValueError):
    """An observation gap blocks target activation, without private diagnostics."""


def read(path: Path, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ProcessProofError('process observation ownership unavailable')
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
    finally:
        os.close(fd)


def identity(directory: Path, pid: int) -> tuple[str, int]:
    raw = read(directory / 'stat', 65536)
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
    result = []
    try:
        with os.scandir(root) as entries:
            for index, entry in enumerate(entries):
                if index >= MAX_PROCESSES:
                    raise ProcessProofError('process inventory exceeds bound')
                if not entry.name.isascii() or not entry.name.isdecimal():
                    continue
                pid = int(entry.name)
                try:
                    info = entry.stat(follow_symlinks=False)
                    if not stat.S_ISDIR(info.st_mode):
                        raise ProcessProofError('process directory unsafe')
                    if info.st_uid != os.getuid():
                        continue
                    directory = root / entry.name
                    before = identity(directory, pid)
                    if before[0] in {'Z', 'X'}:
                        continue
                    refs = references(read(directory / 'cmdline', 1024 * 1024))
                    relevant = refs & sessions
                    if not relevant:
                        continue
                    if len(refs) != 1 or len(relevant) != 1 or before != identity(directory, pid):
                        raise ProcessProofError('process session ownership ambiguous')
                    result.append({'pid': pid, 'start_ticks': before[1], 'session_id': next(iter(relevant))})
                except FileNotFoundError:
                    # A disappearing process is no longer an activation owner.
                    continue
    except OSError:
        raise ProcessProofError('process inventory unavailable') from None
    return sorted(result, key=lambda item: item['pid'])


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
            if info.st_uid != os.getuid():
                continue
            state, ticks = identity(directory, item['pid'])
            if state not in {'Z', 'X'} and ticks == item['start_ticks']:
                raise ProcessProofError('source process still running')
        except FileNotFoundError:
            continue
        except OSError:
            raise ProcessProofError('source process exit unavailable') from None
