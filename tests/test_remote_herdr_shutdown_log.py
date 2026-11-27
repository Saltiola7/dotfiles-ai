"""Disposable 0.9.5 shutdown measurement. No native process at pytest import.

``measure`` requires an explicit executable hash and an empty private directory.
Only its foreground child can answer any RPC. No TUI client, shared service,
controller, installed configuration, authenticated session or default socket.
Never print the native log, snapshot, peer identities or application output.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import subprocess
import time
import uuid


def require(value, label):
    if not value:
        raise RuntimeError(label)


def measure(binary, expected_hash, root, *, fault=None):
    binary, root = Path(binary), Path(root)
    require(binary.is_absolute() and hashlib.sha256(binary.read_bytes()).hexdigest() == expected_hash,
            'native-build-mismatch')
    require(root.is_absolute() and not root.is_symlink() and not list(root.iterdir())
            and stat.S_IMODE(root.stat().st_mode) == 0o700 and root.stat().st_uid == os.getuid(),
            'fixture-root-not-empty-private')
    require(fault in (None, 'writer-failure', 'log-replaced', 'unclean-exit', 'save-replaced'), 'unknown-fault')
    env = {'LANG': 'C.UTF-8', 'TERM': 'xterm-256color', 'SHELL': '/bin/sh', 'RUST_LOG': 'debug'}
    for n, key in enumerate(('HOME', 'XDG_CONFIG_HOME', 'XDG_RUNTIME_DIR', 'XDG_DATA_HOME',
                             'XDG_STATE_HOME', 'XDG_CACHE_HOME', 'TMPDIR', 'PATH')):
        path = root / str(n)
        path.mkdir(mode=0o700)
        env[key] = str(path)
    config = Path(env['XDG_CONFIG_HOME']) / 'herdr'
    config.mkdir(mode=0o700)
    (config / 'config.toml').write_text('onboarding = false\n[update]\nversion_check = false\n'
                                        'manifest_check = false\n[session]\nresume_agents_on_restore = false\n')
    name = 'k' + uuid.uuid4().hex[:10]
    kwargs = dict(env=env, cwd=env['HOME'], stdin=subprocess.DEVNULL,
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, umask=0o077)
    child = subprocess.Popen([binary, '--session', name, 'server'], **kwargs, start_new_session=True)
    def wait(f):
        end = time.monotonic() + 8
        while time.monotonic() < end:
            value = f()
            if value: return value
            require(child.poll() is None, 'foreground-server-exited')
            time.sleep(.025)
        raise RuntimeError('fixture-observation-timeout')
    try:
        endpoint = wait(lambda: next((p for p in root.rglob('herdr.sock') if p.is_socket()), None))
        def rpc(method, params):
            require(child.poll() is None, 'foreground-server-exited')
            with socket.socket(socket.AF_UNIX) as peer:
                peer.settimeout(4)
                peer.connect(str(endpoint))
                pid, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                require((pid, uid) == (child.pid, os.getuid()), 'unexpected-fixture-server')
                key = uuid.uuid4().hex
                peer.sendall(json.dumps({'id': key, 'method': method, 'params': params}).encode() + b'\n')
                with peer.makefile('rb') as stream:
                    line = stream.readline(1048577)
            require(len(line) <= 1048576 and line.endswith(b'\n'), 'incomplete-native-response')
            result = json.loads(line)
            require(result.get('id') == key and 'error' not in result, 'fixture-rpc-refused-' + method)
            return result['result']
        def snapshot():
            return rpc('session.snapshot', {})['snapshot']
        created = rpc('workspace.create', {'cwd': env['HOME'], 'label': 'fixture', 'focus': True})
        wid = created['workspace']['workspace_id']
        def panes():
            return {p['pane_id'] for p in snapshot()['panes'] if p['workspace_id'] == wid}
        def add(target, direction):
            old = panes()
            rpc('pane.split', {'target_pane_id': target, 'direction': direction,
                               'cwd': env['HOME'], 'ratio': .5})
            new = panes() - old
            require(len(new) == 1, 'fixture-split-not-observed')
            return new.pop()
        first, = panes()
        second = add(first, 'right')
        third = add(second, 'down')
        tab, = [t['tab_id'] for t in snapshot()['tabs'] if t['workspace_id'] == wid]
        export = lambda: rpc('layout.export', {'tab_id': tab})['layout']['root']
        original = export()['ratio']
        # Establish an actual earlier autosave. It must not qualify as the
        # later synchronous write even with the same PID, role and output path.
        save = wait(lambda: next((p for p in root.rglob('session.json') if p.is_file()), None))
        def tab_of(document):
            return next(w['tabs'][0] for w in document['workspaces'] if w.get('id') == wid)
        def earlier_ready():
            try:
                return len(tab_of(json.loads(save.read_bytes()))['panes']) == 3
            except (StopIteration, KeyError, json.JSONDecodeError, FileNotFoundError):
                return False
        wait(earlier_ready)
        old = save.read_bytes()
        log_paths = [p for p in root.rglob('*.log') if p.is_file()]
        original_logs = {p: (p.stat().st_dev, p.stat().st_ino) for p in log_paths}
        writer_fds = set()
        for fd in (Path('/proc') / str(child.pid) / 'fd').iterdir():
            try:
                info = fd.stat()
            except FileNotFoundError:
                continue
            writer_fds.add((info.st_dev, info.st_ino))
        save_open = (save.stat().st_dev, save.stat().st_ino) in writer_fds
        rpc('pane.resize', {'pane_id': first, 'direction': 'right', 'amount': .125})
        resized = export()['ratio']
        require(resized != original and 0 < resized < 1, 'resize-did-not-change-ratio')
        rpc('pane.close', {'pane_id': third})
        require(panes() == {first, second}, 'close-not-observed')
        if fault == 'writer-failure':
            # Ordinary rename of the output cannot replace a directory.
            save.unlink(missing_ok=True)
            save.mkdir(mode=0o700)
        if fault == 'log-replaced':
            for p in log_paths:
                p.rename(p.with_suffix('.previous'))
                p.touch(mode=0o600)
        if fault == 'unclean-exit':
            child.kill()
        else:
            rpc('server.stop', {})
        status = child.wait(timeout=8)
        log_paths = [p for p in root.rglob('*.log') if p.is_file()]
        require(all(p.stat().st_size <= 2 * 1024 * 1024 for p in log_paths), 'fixture-log-too-large')
        logs = [p.read_bytes() for p in log_paths]
        if fault == 'save-replaced':
            later = save.with_suffix('.fixture')
            later.write_bytes(old)
            os.replace(later, save)
        raw = save.read_bytes() if save.is_file() else b''
        disk = tab_of(json.loads(raw)) if raw else None
        markers = (b'app.startup', b'completing server shutdown', b'persist.save',
                   b'headless server exiting', b'app.shutdown')
        observations = []
        for p, log in zip(log_paths, logs):
            lines = log.splitlines()
            begin = [i for i, line in enumerate(lines) if markers[1] in line]
            end = [i for i, line in enumerate(lines) if markers[3] in line]
            interval = lines[begin[0]+1:end[0]] if len(begin) == len(end) == 1 and begin[0] < end[0] else []
            saves = [line for line in interval if markers[2] in line]
            stamps = [re.search(rb'\b\d\d:\d\d:\d\d(?:\.(\d+))?', line) for line in saves]
            observations.append({
                'markers': [sum(m in line for line in lines) for m in markers],
                'interval_save_count': len(saves),
                'interval_save_error_count': sum(any(term in line.lower() for term in (
                    b'failed', b'error', b'warn')) for line in saves),
                'explicit_success': sum(b'session saved' in line for line in saves),
                'time_fraction_digits': [len((match[1] or b'')) if match else None for match in stamps],
                'log_open_at_last_edit': original_logs.get(p) in writer_fds,
                'role_file': {'herdr.log': 'general', 'herdr-server.log': 'server',
                              'herdr-client.log': 'client'}.get(p.name, 'other'),
                'single_link_owned_log': p.stat().st_nlink == 1 and p.stat().st_uid == os.getuid(),
                'snapshot_open_at_last_edit': save_open,
                # Names only, and only for a closed vocabulary of native log keys.
                'interval_save_key_names': sorted({key.decode() for line in saves for key in re.findall(
                    rb'\b([a-zA-Z_][a-zA-Z_0-9]*)=', line) if key in {
                        b'pid', b'bytes', b'workspaces', b'path', b'event', b'error', b'inode', b'session',
                        b'role', b'thread', b'thread_id', b'ts', b'time', b'timestamp', b'ts_ms', b'ts_ns',
                        b'subsystem', b'digest', b'sha256', b'generation', b'run_id', b'reason', b'source'}}),
                'integer_clock_field_shapes': sorted({(key.decode(), len(value)) for line in saves
                    for key, value in re.findall(rb'\b([a-z_]{1,40})=([0-9]{10,20})\b', line)}),
                'autosave_same_key_set': any(set(re.findall(rb'\b([a-zA-Z_][a-zA-Z_0-9]*)=', line))
                    == set(re.findall(rb'\b([a-zA-Z_][a-zA-Z_0-9]*)=', final)) for final in saves
                    for line in (lines[:begin[0]] if begin else []) if b'session saved' in line),
                'startup_pid_count': sum(b'pid=' + str(child.pid).encode() in line
                                         for line in lines if markers[0] in line),
                'shutdown_pid_count': sum(b'pid=' + str(child.pid).encode() in line
                                          for line in lines if markers[4] in line),
                'skip_or_handoff_count': sum(any(term in line.lower() for term in (
                    b'skip', b'checkpoint', b'handoff')) for line in interval),
                'includes_snapshot_hash': bool(raw and any(hashlib.sha256(raw).hexdigest().encode() in line
                                                          for line in saves)),
                'interval_pid_count': sum(str(child.pid).encode() in line for line in saves),
                'autosaves_before': sum(markers[2] in line for line in lines[:begin[0]]) if begin else 0,
            })
        return {'clean_exit': status == 0, 'edited_save': bool(disk and len(disk['panes']) == 2
                and disk['layout']['Split']['ratio'] == resized), 'earlier_save': raw == old,
                'rotation_or_loss': any(not p.exists() or (p.stat().st_dev, p.stat().st_ino) != ids
                                        for p, ids in original_logs.items()), 'streams': observations}
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=4)
