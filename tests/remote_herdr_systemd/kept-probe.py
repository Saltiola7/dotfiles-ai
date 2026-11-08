#!/usr/bin/python3 -I
"""Disposable native-only reproduction, not RRW007F acceptance or a fix claim.

Schema provenance: https://github.com/herdrdev/herdr-core/tree/
3965a46caae095a3ead01de237fa13955e52b8c6/crates/herdr-core/src/
runtime.rs (startup/stop), terminals.rs (Registry/private holder), kept.rs
(claim-before-send, retry cap 60000ms). Claimed-pending supports that condition,
NOT proof that SPAWN was lost. Raw private records never leave memory.
"""
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import tomllib

HOME = Path('/home/fixture')
SOURCE = Path('/opt/f01/source')
BIN = HOME / '.local/bin'
STATE = HOME / '.local/state/herdr-core/default'
ENDPOINT = Path('/run/user/1000/herdr-core/default.sock')
REASONS = {'server_stop', 'host_shutdown', 'holder_lost', 'stopped_by_restart',
           'spawn_pending', 'signaled', 'exited', 'killed'}


def require(condition):
    if not condition:
        raise ValueError('invariant')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError('source-unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)


def private_registry(path):
    """Bounded no-symlink traversal; private native parent protects native 0644 files."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            require(info.st_uid in {0, os.getuid()}
                    and (not info.st_mode & 0o022 or info.st_mode & stat.S_ISVTX))
        info = os.fstat(fd)
        require(info.st_uid == os.getuid() and not info.st_mode & 0o077)
        child = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(child)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and info.st_nlink == 1 and not info.st_mode & 0o022)
            with os.fdopen(os.dup(child), 'rb') as stream:
                raw = stream.read(2 * 1024 * 1024 + 1)
            require(len(raw) <= 2 * 1024 * 1024)
            return json.loads(raw)
        finally:
            os.close(child)
    finally:
        os.close(fd)


def classify(registry, address, now_ms):
    """Persist only allowlisted labels, booleans and bounded numeric counters."""
    unsupported = {'classification': 'schema-unsupported'}
    if not isinstance(registry, dict) or not isinstance(registry.get('terminals'), dict):
        return unsupported
    records = list(registry['terminals'].values())
    if any(not isinstance(t, dict) for t in records):
        return unsupported
    matches = [t for t in records if t.get('address') == address]
    if not matches:
        return {'classification': 'record-missing'}
    if len(matches) != 1:
        return unsupported
    t = matches[0]
    if (not {'pid', 'state', 'reason', 'keep', 'restart_after_ms', 'restart_delay_ms'} <= t.keys()
            or t['state'] not in ('live', 'finished') or type(t['keep']) is not bool
            or t['reason'] is not None and (not isinstance(t['reason'], str) or t['reason'] not in REASONS)
            or t.get('holder') is not None and not isinstance(t['holder'], str)
            or t['pid'] is not None and (type(t['pid']) is not int or not 1 < t['pid'] <= 4294967295)
            or any(type(t[k]) is not int or not 0 <= t[k] < 2**64
                   for k in ('restart_after_ms', 'restart_delay_ms'))):
        return unsupported
    holder = t.get('holder') is not None  # serde omits None; public API omits this field entirely.
    live = t['state'] == 'live' and t['keep']
    label = ('spawned' if live and t['pid'] is not None else
             'claimed-pending' if live and holder else
             'eligible-pending-noholder' if live and t['restart_after_ms'] <= now_ms else
             'backoff-pending-noholder' if live else 'not-kept-live')
    return {'classification': label, 'holder_set': holder, 'pid_none': t['pid'] is None,
            'state_live': t['state'] == 'live', 'reason': t['reason'],
            'restart_after_ms': t['restart_after_ms'], 'restart_delay_ms': t['restart_delay_ms']}


def shell_argv(raw):
    if not raw.endswith(b'\0'):
        return False
    argv = raw[:-1].split(b'\0')
    return (argv[0] in {b'/bin/sh', b'sh', b'-sh', b'/bin/bash', b'bash', b'-bash'}
            and argv[1:] in ([], [b'-l'], [b'--login']))


def shell_proof(processes, pid, cwd, root=Path('/proc')):
    require(type(pid) is int and pid > 1)
    directory = root / str(pid)
    require(processes.task_uid(directory) == os.getuid())
    before = processes.identity(directory, pid)
    require(before[0] not in {'Z', 'X'})
    require(shell_argv(processes.task_read(directory, 'cmdline', 65536)))
    require(os.readlink(directory / 'cwd') == str(cwd))
    after = processes.identity(directory, pid)
    require(after[1] == before[1] and after[0] not in {'Z', 'X'})
    require(processes.task_uid(directory) == os.getuid())
    return {'pid': pid, 'start_ticks': before[1]}


def gone(processes, proof):
    try:
        state, ticks = processes.identity(Path('/proc') / str(proof['pid']), proof['pid'])
        return ticks != proof['start_ticks'] or state in {'Z', 'X'}
    except (FileNotFoundError, ProcessLookupError):
        return True


def wait(check, seconds):
    """Observation retries only; hard wall-clock budget includes blocked RPC reads."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        signal.setitimer(signal.ITIMER_REAL, min(2, deadline - time.monotonic()))
        try:
            result = check()
            if result:
                return result
        except Exception:
            pass
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        time.sleep(min(0.5, max(0, deadline - time.monotonic())))
    raise TimeoutError()


def run(*argv):
    result = subprocess.run([str(a) for a in argv], cwd=HOME, timeout=110,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    require(result.returncode == 0)


def main():
    os.umask(0o077)
    require(os.getuid() == 1000 and Path.home() == HOME and 'HC_SESSION' not in os.environ)
    status = {'complete': False, 'result': 'failed', 'phase': 'install',
              'rounds': [], 'lost_spawn_proven': False}
    # Exclusive output is a fresh-fixture guard; never overwrite previous evidence.
    output = HOME / 'kept-probe.json'
    write_private(output, status)
    try:
        pins = tomllib.loads((SOURCE / '.chezmoidata.toml').read_text())['dotfiles_ai']['herdr_core']
        require(set(pins) == {'version', 'archive_url', 'archive_sha256', 'binary_sha256'})
        require(pins['version'] == '0.1.18')
        config = HOME / '.config/dotfiles-ai'
        config.mkdir(parents=True, mode=0o700, exist_ok=True)
        write_private(config / 'herdr-core.json', pins)
        run(BIN / 'remote-herdr-core', 'install')
        run(BIN / 'remote-herdr-core', 'check')
        source = SOURCE / 'dot_local/share/dotfiles-ai/remote-herdr'
        protocol = load('kept_protocol', source / 'protocol.py')
        processes = load('kept_processes', source / 'processes.py')
        require(not STATE.exists() and not ENDPOINT.exists())
        require(not (HOME / '.config/herdr-core/config.toml').exists())
        cwd = HOME / 'kept-work'
        cwd.mkdir(mode=0o700)
        def rpc(method, params):
            return protocol.request(ENDPOINT, method, params)
        status['phase'] = 'initial-start'
        run(BIN / 'herdr-core', 'server', 'start', '--json')
        wait(lambda: rpc('server.status', {}), 30)
        status['phase'] = 'initial-shell'
        created = rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': str(cwd),
                      'keep': True, 'no_parent': True, 'no_notify': True, 'wait': False})
        address = created['address']
        require(isinstance(address, str))
        def ready():
            t = rpc('terminal.get', {'terminal': address})
            require(t['address'] == address and t['state'] == 'live' and t['keep'] is True)
            require(t['cwd'] == str(cwd))
            return shell_proof(processes, t['pid'], cwd)
        current = wait(ready, 75)
        for number in range(1, 4):
            item = {'round': number, 'old': current, 'recovered': False, 'classification': 'not-observed'}
            status['rounds'].append(item)
            status['phase'] = 'round-' + str(number) + '-stop'
            run(BIN / 'herdr-core', 'server', 'stop', '--json')
            wait(lambda: not ENDPOINT.exists() and gone(processes, current), 30)
            item['socket_off_old_identity_gone'] = True
            status['phase'] = 'round-' + str(number) + '-start'
            run(BIN / 'herdr-core', 'server', 'start', '--json')
            time.sleep(6)  # Do not accept startup before the native sweep window.
            try:
                current = wait(ready, 75)  # 60s upstream backoff cap plus margin.
                item.update(new=current, recovered=True, classification='spawned')
            except Exception:
                try:
                    item.update(classify(private_registry(STATE / 'terminals.json'),
                                         address, int(time.time() * 1000)))
                except Exception:
                    item['classification'] = 'private-observation-unavailable'
                print('kept-probe: ' + str(item['classification']))
                raise
            print('kept-probe: round-recovered-' + str(number))
        status.update(complete=True, result='stall-not-reproduced')
        print('kept-probe: stall-not-reproduced-rounds-3')
        print('kept-probe: complete')
        return 0
    except Exception:
        print('kept-probe: failed-' + status['phase'])
        return 1
    finally:
        # Only this fixture-owned output; no native records are rewritten.
        fd = os.open(output, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
        with os.fdopen(fd, 'w') as stream:
            json.dump(status, stream)


if __name__ == '__main__':
    def alarm(_signum, _frame):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, alarm)
    try:
        sys.exit(main())
    except Exception:
        print('kept-probe: precondition-failed')
        sys.exit(1)
