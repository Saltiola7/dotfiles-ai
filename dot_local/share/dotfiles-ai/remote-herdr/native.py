"""Bounded, fail-closed adapters for the reviewed default Herdr runtimes.

No transaction journal or lock lives here: the caller must serialize selection,
switch and recovery. Native effects have injectable command/core/tui seams. Store
objects are private JSON objects; mutation intent is durable before each effect.
Native observations are not release/qualification evidence.
"""
from contextlib import closing
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import socket
import sqlite3
import stat
import struct
import subprocess
import time
import tomllib
from typing import Protocol
from urllib.parse import urlsplit
import uuid

import layout
import processes
import protocol


LIMIT = 2 * 1024 * 1024
RUNTIMES = {'tui', 'herdr-core'}


class NativeError(ValueError):
    """Fixed-label error; native text and command arguments never escape."""


class Store(Protocol):
    def read(self, name: str) -> dict | None: ...
    def write(self, name: str, value: dict) -> None: ...


def bounded(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except NativeError:
            raise
        except protocol.CoreProtocolError as error:
            # Protocol errors contain only source-literal labels, never peer
            # message text. Preserve that distinction for private diagnostics.
            raise NativeError('core protocol: ' + str(error)) from None
        except Exception:
            raise NativeError('native observation or mutation uncertain') from None
    return call


def panes(plan):
    return [p for s in plan['spaces'] for t in s['tabs'] for p in t['panes']]


def sessions(plan):
    return {p['session_id'] for p in panes(plan) if p['session_id'] is not None}


def runtime(value):
    if value not in RUNTIMES:
        raise NativeError('runtime selection invalid')
    return value


def checked_plan(value):
    try:
        return layout.validate_plan(value)
    except Exception:
        raise NativeError('canonical plan invalid') from None


class Native:
    def __init__(self, home: Path, store: Store):
        # Never consult HOME, HC_SESSION, credentials, or the caller's environment.
        self.home = Path(home)
        if not self.home.is_absolute() or '..' in self.home.parts:
            raise NativeError('home boundary invalid')
        self.store = store
        self.proc_root = Path('/proc')
        self.config_path = self.home / '.config/dotfiles-ai/chezmoi.toml'
        self.snapshot_path = self.home / '.config/herdr/session.json'
        self.tui_endpoint = self.home / '.config/herdr/herdr.sock'
        self.run_root = Path(f'/run/user/{os.getuid()}')
        self.poll_seconds = 30.0

    def _parents(self, path):
        if not path.is_relative_to(self.home):
            raise NativeError('file outside home boundary')
        current = path.parent
        while True:
            info = current.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o022):
                raise NativeError('private file parent unsafe')
            if current == self.home:
                break
            current = current.parent

    def _read(self, path, limit=LIMIT):
        self._parents(path)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or info.st_size > limit or info.st_mode & 0o022):
                raise NativeError('private file unsafe or oversized')
            data = b''
            while len(data) <= limit:
                part = os.read(fd, min(65536, limit + 1 - len(data)))
                if not part:
                    return data
                data += part
            raise NativeError('private file oversized')
        finally:
            os.close(fd)

    def _json(self, path):
        return protocol.decode(self._read(path))

    def _optional_snapshot(self):
        try:
            return self._json(self.snapshot_path)
        except FileNotFoundError:
            return None

    def _atomic(self, path, data, mode=0o600):
        self._parents(path)
        if path.is_symlink():
            raise NativeError('private file unsafe')
        if path.exists():
            self._read(path)
        temporary = path.with_name('.remote-herdr-' + uuid.uuid4().hex)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    def _backup(self, value):
        name = 'backup-' + uuid.uuid4().hex + '.json'
        self.store.write(name, layout._json_copy(value))
        return name

    def _receipt(self, receipt):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', receipt['txid']):
            raise NativeError('transaction identity invalid')
        self.store.write('receipt-' + receipt['txid'] + '.json', layout._json_copy(receipt))

    def _pins(self):
        pins = self._json(self.home / '.config/dotfiles-ai/herdr-runtime.json')
        if (set(pins) != {'schema_version', 'tui_version', 'tui_sha256', 'core_version', 'core_sha256'}
                or type(pins['schema_version']) is not int or pins['schema_version'] != 1
                or pins['tui_version'] != '0.9.5' or pins['core_version'] != '0.1.18'
                or any(not isinstance(pins[k], str) or not re.fullmatch('[0-9a-f]{64}', pins[k])
                       for k in ('tui_sha256', 'core_sha256'))):
            raise NativeError('managed binary pins invalid')
        return pins

    def _binary(self, target):
        pins = self._pins()
        name, key = ('herdr', 'tui_sha256') if target == 'tui' else ('herdr-core', 'core_sha256')
        path = self.home / '.local/bin' / name
        self._parents(path)
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o755):
            raise NativeError('native binary attributes invalid')
        # Binaries are larger than structured state but still bounded.
        data = self._read(path, 256 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != pins[key]:
            raise NativeError('native binary integrity mismatch')
        return path

    @bounded
    def command(self, argv, timeout=30):
        """One command, bounded output/time, no inherited environment or shell."""
        argv = list(argv)
        if not argv or any(type(a) is not str or '\0' in a for a in argv):
            raise NativeError('native command invalid')
        if argv[0] in ('herdr', 'herdr-core'):
            argv[0] = str(self._binary('tui' if argv[0] == 'herdr' else 'herdr-core'))
        elif argv == ['opencode-native', 'debug', 'paths', 'db']:
            # Read-only native path resolver, not service discovery/start. Native
            # v2 installation/update ownership remains with the foundation.
            executable = self.home / '.opencode/bin/opencode'
            self._parents(executable)
            info = executable.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or info.st_mode & 0o022 or not info.st_mode & 0o100):
                raise NativeError('native OpenCode executable unsafe')
            argv[0] = str(executable)
        elif argv[0] not in ('/usr/bin/systemctl', str(self.home / '.local/bin/chezmoi')):
            raise NativeError('native command not authorized')
        env = {'HOME': str(self.home), 'PATH': str(self.home / '.local/bin') + ':/usr/bin:/bin',
               'XDG_CONFIG_HOME': str(self.home / '.config'),
               'XDG_STATE_HOME': str(self.home / '.local/state'),
               'XDG_DATA_HOME': str(self.home / '.local/share'), 'LANG': 'C.UTF-8'}
        if self.run_root.is_dir():
            env['XDG_RUNTIME_DIR'] = str(self.run_root)
            env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=' + str(self.run_root / 'bus')
        deadline = time.monotonic() + timeout
        with subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, close_fds=True) as child:
            output = bytearray()
            if child.stdout is None or child.stderr is None:
                raise NativeError('native command pipes unavailable')
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ, True)
                selector.register(child.stderr, selectors.EVENT_READ, False)
                total = 0
                try:
                    while selector.get_map():
                        left = deadline - time.monotonic()
                        if left <= 0:
                            raise NativeError('native command outcome uncertain')
                        for key, _ in selector.select(left):
                            part = os.read(key.fd, 65536)
                            if not part:
                                selector.unregister(key.fileobj)
                                continue
                            total += len(part)
                            if total > LIMIT:
                                raise NativeError('native command output exceeds bound')
                            if key.data:
                                output.extend(part)
                    if child.wait(timeout=max(0.001, deadline - time.monotonic())) != 0:
                        raise NativeError('native command outcome uncertain')
                finally:
                    if child.poll() is None:
                        # Only our CLI child, never a native holder/client/backend PID.
                        child.kill()
                        child.wait()
        if not output.strip():
            return {}
        try:
            return protocol.decode(bytes(output))
        except ValueError:
            return bytes(output).decode('utf-8')

    def _core_endpoint(self):
        config = self.home / '.config/herdr-core/config.toml'
        if config.exists():
            value = tomllib.loads(self._read(config).decode())
            if value.get('socket') is not None:
                raise NativeError('relocated core endpoint unsupported')
        if self.run_root.is_dir():
            return self.run_root / 'herdr-core/default.sock'
        return self.home / '.local/state/herdr-core/default/default.sock'

    @bounded
    def endpoint_present(self, target):
        path = self.tui_endpoint if runtime(target) == 'tui' else self._core_endpoint()
        try:
            info = path.lstat()
        except FileNotFoundError:
            return False
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise NativeError('native endpoint unsafe')
        return True

    @bounded
    def core(self, method, params):
        self._binary('herdr-core')
        return protocol.request(self._core_endpoint(), method, params)

    @bounded
    def tui(self, method, params):
        """Pinned TUI raw JSON-line API (not core JSON-RPC, no auto-start)."""
        self._binary('tui')
        if method not in {'session.snapshot', 'layout.export', 'pane.process_info'}:
            raise NativeError('TUI request not authorized')
        self._parents(self.tui_endpoint)
        info = self.tui_endpoint.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise NativeError('TUI endpoint unsafe')
        if not hasattr(socket, 'SO_PEERCRED'):
            raise NativeError('TUI peer identity unavailable')
        request_id = 'remote-herdr-' + uuid.uuid4().hex
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(30)
            peer.connect(str(self.tui_endpoint))
            _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                raise NativeError('TUI peer identity mismatch')
            # Request flattens a method enum tagged with method/content=params.
            payload = {'id': request_id, 'method': method, 'params': params}
            peer.sendall(json.dumps(payload).encode() + b'\n')
            data = b''
            while b'\n' not in data:
                part = peer.recv(min(65536, LIMIT + 1 - len(data)))
                if not part or len(data) + len(part) > LIMIT:
                    raise NativeError('TUI response unavailable or oversized')
                data += part
        answer = protocol.decode(data.split(b'\n', 1)[0])
        if answer.get('id') != request_id or 'error' in answer or type(answer.get('result')) is not dict:
            raise NativeError('TUI response refused or invalid')
        return answer['result']

    def scan(self, identities):
        return processes.scan_sessions(identities, self.proc_root)

    def absent(self, identities, captured):
        processes.assert_absent(identities, captured, self.proc_root)

    def _coverage(self, plan):
        expected = sessions(plan)
        found = self.scan(expected)
        if any(sum(item['session_id'] == identity for item in found) != 1 for identity in expected):
            raise NativeError('session client coverage incomplete or duplicate')
        for item in found:
            self._client_argv(item['pid'], item['session_id'])
            # The process seam proves exact ID; cwd must independently agree.
            wanted = next(p['cwd'] for p in panes(plan) if p['session_id'] == item['session_id'])
            if self.process_cwd(item['pid']) != wanted:
                raise NativeError('session client directory mismatch')
        return found

    def process_cwd(self, pid):
        return os.readlink(self.proc_root / str(pid) / 'cwd')

    def process_argv(self, pid):
        raw = processes.task_read(self.proc_root / str(pid), 'cmdline', LIMIT)
        # Remove the terminator, not trailing empty arguments: exact argv is proof.
        return raw.removesuffix(b'\0').decode('utf-8').split('\0')

    def _client_argv(self, pid, identity):
        if self._session_argv(self.process_argv(pid)) != identity:
            raise NativeError('session client executable or identity unsupported')

    def _session_argv(self, argv):
        """Only the constructor and executable_opencode.tmpl's exec expansion.

        The wrapper prepends --server and appends --auto under HERDR_ENV.
        This is not a general OpenCode CLI parser: reordered/duplicate/unknown
        flags and external or decorated endpoints deliberately remain blocked.
        """
        if type(argv) is not list or not argv or any(type(a) is not str for a in argv):
            raise NativeError('session client executable or identity unsupported')
        if argv[0] in ('opencode', str(self.home / '.local/bin/opencode')):
            tail = argv[1:]
        elif argv[0] == str(self.home / '.opencode/bin/opencode'):
            if len(argv) not in (5, 6) or argv[1] != '--server':
                raise NativeError('session client executable or identity unsupported')
            try:
                url = urlsplit(argv[2])
                if (url.scheme not in ('http', 'https')
                        or url.hostname not in ('127.0.0.1', 'localhost', '::1')
                        or not url.port or url.username is not None or url.password is not None
                        or url.path or url.query or url.fragment
                        or argv[2] != f'{url.scheme}://{url.netloc}'):
                    raise ValueError
            except ValueError:
                raise NativeError('session client server unsupported') from None
            tail = argv[3:]
        else:
            raise NativeError('session client executable or identity unsupported')
        if (len(tail) not in (2, 3) or tail[0] != '--session'
                or not processes.SESSION.fullmatch(tail[1])
                or (len(tail) == 3 and tail[2] != '--auto')):
            raise NativeError('session client executable or identity unsupported')
        return tail[1]

    def _shell_proof(self, terminal):
        """A recovered owned shell must really be a shell, not stored old argv."""
        program = terminal.get('foreground') or terminal
        pid = program.get('pid')
        if type(pid) is not int or pid <= 1:
            raise NativeError('owned shell PID unavailable')
        argv = self.process_argv(pid)
        if not argv or argv[0] not in ('/bin/bash', 'bash', '-bash') or argv[1:] not in ([], ['-l'], ['--login']):
            raise NativeError('owned shell has foreign live program')
        if self.process_cwd(pid) != program.get('cwd'):
            raise NativeError('owned shell directory proof unavailable')

    @bounded
    def database_path(self):
        value = self.command(['opencode-native', 'debug', 'paths', 'db'])
        if not isinstance(value, str) or '\0' in value:
            raise NativeError('OpenCode database path unavailable')
        path = Path(value.strip())
        if (path.parent != self.home / '.local/share/opencode'
                or not re.fullmatch(r'opencode(?:-[A-Za-z0-9._-]+)?\.db', path.name)):
            raise NativeError('OpenCode database location unsupported')
        return path

    def _db_sessions(self, plan):
        """Supported OpenCode SQLite identity/directory contract, read-only only."""
        if not sessions(plan):
            return
        path = self.database_path()
        # Missing store is not positive evidence of a resumable session.
        self._parents(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise NativeError('OpenCode session store unsafe')
        try:
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
                db.execute('PRAGMA query_only = ON')
                db.set_progress_handler(lambda: 1, 100000)
                # Native v2.2.6 uses session_v2. Never satisfy a current session
                # proof from a stale legacy row when both tables coexist.
                tables = {row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('session_v2', 'session')")}
                table = 'session_v2' if 'session_v2' in tables else 'session'
                columns = {row[1] for row in db.execute('PRAGMA table_info(' + table + ')')}
                if not {'id', 'directory'} <= columns:
                    raise NativeError('OpenCode session schema unsupported')
                for pane in panes(plan):
                    if pane['session_id'] is not None:
                        rows = db.execute('SELECT id, directory FROM ' + table + ' WHERE id = ? AND length(directory) <= 4096 LIMIT 2',
                                          (pane['session_id'],)).fetchall()
                        if rows != [(pane['session_id'], pane['cwd'])]:
                            raise NativeError('OpenCode session identity or directory unavailable')
        except sqlite3.Error:
            raise NativeError('OpenCode session store unavailable or unsupported') from None

    @bounded
    def selected(self):
        try:
            config = tomllib.loads(self._read(self.config_path).decode())
        except FileNotFoundError:
            return 'tui'
        return runtime(config.get('data', {}).get('dotfiles_ai', {}).get('herdr', {}).get('runtime', 'tui'))

    @bounded
    def select(self, target):
        runtime(target)
        original = self._read(self.config_path).decode('utf-8')
        before = tomllib.loads(original)
        lines = original.splitlines(keepends=True)
        section = None
        assignments = []
        end = len(lines)
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('['):
                if section is not None and end == len(lines):
                    end = index
                if re.fullmatch(r'\[data\.dotfiles_ai\.herdr\]\s*(?:#.*)?', stripped):
                    if section is not None:
                        raise NativeError('selection TOML ambiguous')
                    section = index
                    end = len(lines)
            elif section is not None and end == len(lines) and re.match(r'\s*runtime\s*=', line):
                assignments.append(index)
        old = before.get('data', {}).get('dotfiles_ai', {}).get('herdr', {})
        if type(old) is not dict or len(assignments) > 1 or (old and section is None):
            raise NativeError('selection TOML unsupported inline or ambiguous structure')
        if assignments:
            index = assignments[0]
            match = re.fullmatch(r'(\s*runtime\s*=\s*)([\'"])(tui|herdr-core)\2([ \t]*(?:#[^\r\n]*)?)(\r?\n)?', lines[index])
            if not match:
                raise NativeError('selection TOML scalar unsupported')
            lines[index] = match[1] + match[2] + target + match[2] + match[4] + (match[5] or '')
        elif section is not None:
            lines.insert(section + 1, 'runtime = ' + json.dumps(target) + '\n')
        else:
            # Avoid trying to reinterpret quoted/dotted/inline parent declarations.
            if 'herdr' in before.get('data', {}).get('dotfiles_ai', {}):
                raise NativeError('selection TOML unsupported structure')
            lines.append(('' if original.endswith('\n') else '\n') +
                         '[data.dotfiles_ai.herdr]\nruntime = ' + json.dumps(target) + '\n')
        updated = ''.join(lines)
        expected = tomllib.loads(original)
        expected.setdefault('data', {}).setdefault('dotfiles_ai', {}).setdefault('herdr', {})['runtime'] = target
        if tomllib.loads(updated) != expected:
            raise NativeError('selection TOML changed unrelated values')
        source = before.get('sourceDir')
        if before.get('hooks'):
            raise NativeError('chezmoi apply hooks unsupported')
        if type(source) is not str:
            raise NativeError('chezmoi source directory unavailable')
        source_path = Path(source)
        if not source_path.is_absolute() or not source_path.is_relative_to(self.home) or '..' in source_path.parts:
            raise NativeError('chezmoi source directory unsafe')
        self._parents(source_path / 'boundary')
        self._atomic(self.config_path, updated.encode())
        self.command([str(self.home / '.local/bin/chezmoi'), '--config', str(self.config_path),
                      '--source', str(source_path), 'apply', '--include', 'files',
                      str(self.home / '.config/herdr/config.toml')])

    def _document(self):
        answer = self.core('doc.get', {'name': 'herdr-app'})
        # Pinned DocGetResult wraps a nullable value, with version zero initially.
        if answer is None:
            return None, 0
        if (type(answer) is not dict or set(answer) != {'version', 'value'}
                or type(answer['version']) is not int or answer['version'] < 0):
            raise NativeError('core document schema unsupported')
        return layout._json_copy(answer['value']), answer['version']

    def _terminals(self):
        value = self.core('terminal.list', {'all': True})
        result = value.get('terminals')
        if type(result) is not list or len(result) > layout.MAX_PANES:
            raise NativeError('core terminal inventory invalid')
        addresses = [item.get('address') for item in result]
        if len(set(addresses)) != len(addresses):
            raise NativeError('core terminal inventory ambiguous')
        return layout._json_copy(result)

    def _terminal(self, address):
        result = self.core('terminal.get', {'terminal': address})
        if result.get('address') != address:
            raise NativeError('core terminal identity mismatch')
        return result

    def _wait_core_spawns(self):
        """A listening core can still be spawning its kept replacement shells."""
        def ready():
            return not any(t.get('state') == 'live' and t.get('keep') is True
                           and t.get('pid') is None for t in self._terminals())
        # Observations only: never restart a core, run a terminal or retry a
        # mutation because the kept-terminal PID is not available yet.
        try:
            # Upstream keep backoff caps at 60 seconds; leave a margin for the
            # sweep and one-second recovery loop. Ordinary readiness stays 30s.
            self._wait(ready, seconds=75.0)
        except NativeError as error:
            if str(error) == 'native readiness or stop proof unavailable':
                raise NativeError('core kept-terminal spawn readiness unavailable') from None
            raise

    def _program(self, terminal):
        if terminal.get('state') != 'live' or type(terminal.get('pid')) is not int or terminal['pid'] <= 1:
            raise NativeError('core terminal not live or spawn pending')
        foreground = terminal.get('foreground')
        program = foreground if foreground is not None else terminal
        if type(program.get('pid')) is not int or program['pid'] <= 1:
            raise NativeError('core foreground process identity unavailable')
        argv = program.get('argv')
        if type(argv) is not list or not argv or any(type(a) is not str for a in argv):
            raise NativeError('core program identity unavailable')
        executable = argv[0]
        cwd = program.get('cwd')
        if executable in ('/bin/bash', 'bash', '-bash') and argv[1:] in ([], ['-l'], ['--login']):
            return None, cwd
        try:
            return self._session_argv(argv), cwd
        except NativeError:
            raise NativeError('core foreign or unsupported live program') from None

    def _live_program(self, terminal):
        """Prove native metadata against the actual same-owner live process."""
        identity, cwd = self._program(terminal)
        program = terminal.get('foreground') or terminal
        self._pid_proofs([terminal['pid'], program['pid']])
        if identity is None:
            self._shell_proof(terminal)
        else:
            self._client_argv(program['pid'], identity)
            if self.process_cwd(program['pid']) != cwd:
                raise NativeError('core client directory proof unavailable')
        return identity, cwd

    def _from_core(self, document, terminals):
        manifest = self.store.read('manifest.json')
        if manifest is not None and manifest.get('schema_version') == 2:
            previous = checked_plan(manifest['plan'])
            receipt = manifest['receipt']
            self._binding_receipt(previous, receipt, manifest['txid'], 2)
            plan, bindings, _, repairs = self._current_projection(document, terminals, previous, receipt)
            represented = {b['terminal'] for b in bindings.values()}
            if repairs or any(t.get('state') == 'live' and t['address'] not in represented
                              and self._actual_core_program(t)[0] is not None for t in terminals):
                raise NativeError('core source contains unrestorable live content')
            return plan
        if document is None:
            document = {'spaces': []}
        if type(document) is not dict or set(document) != {'spaces'}:
            raise NativeError('core app document structure unsupported')
        lookup = {item['address']: item for item in terminals}
        seen = set()
        spaces = []
        for si, native_space in enumerate(document['spaces']):
            if set(native_space) != {'id', 'name', 'folder', 'tabs'}:
                raise NativeError('core space structure unsupported')
            space = {'name': native_space['name'], 'directory': native_space['folder'], 'tabs': []}
            for ti, native_tab in enumerate(native_space['tabs']):
                if set(native_tab) != {'id', 'name', 'root'}:
                    raise NativeError('core tab structure unsupported')
                tab_panes = []
                tab = {'name': native_tab['name'], 'panes': tab_panes, 'root': None}

                def tree(node, depth=1):
                    if depth > layout.MAX_DEPTH or type(node) is not dict:
                        raise NativeError('core tree unsupported')
                    if set(node) - {'id', 'type', 'size', 'content', 'children'}:
                        raise NativeError('core node modifiers unsupported')
                    if 'size' in node and (type(node['size']) is not dict or set(node['size']) != {'weight'}):
                        raise NativeError('core node size modifiers unsupported')
                    if node.get('type') == 'block':
                        if 'children' in node or set(node.get('content', {})) != {'terminal'}:
                            raise NativeError('core block unsupported')
                        address = node['content']['terminal']
                        if address in seen or address not in lookup:
                            raise NativeError('core duplicate or missing terminal view')
                        seen.add(address)
                        identity, cwd = self._live_program(lookup[address])
                        key = f's{si}-t{ti}-p{len(tab_panes)}'
                        tab_panes.append({'key': key, 'cwd': cwd, 'session_id': identity})
                        return {'pane': key}
                    if node.get('type') not in ('row', 'column') or 'content' in node:
                        raise NativeError('core layout node unsupported')
                    children = node.get('children')
                    if type(children) is not list or len(children) not in (1, 2):
                        raise NativeError('core nonbinary layout unsupported')
                    if len(children) == 1:
                        return tree(children[0], depth + 1)
                    weights = [child.get('size', {}).get('weight', 1.0) for child in children]
                    if any(type(w) not in (int, float) or not 0 < w < float('inf') for w in weights):
                        raise NativeError('core layout weights unsupported')
                    return {'axis': node['type'], 'ratio': weights[0] / sum(weights),
                            'children': [tree(child, depth + 1) for child in children]}

                tab['root'] = tree(native_tab['root'])
                space['tabs'].append(tab)
            spaces.append(space)
        # A live agent hidden outside the selected document is not safe to ignore.
        for terminal in terminals:
            if terminal.get('state') == 'live' and terminal['address'] not in seen:
                if self._live_program(terminal)[0] is not None:
                    raise NativeError('core unrepresented live agent')
        return checked_plan({'schema_version': 1, 'spaces': spaces})

    def _document_terminals(self, document):
        result = set()
        def tree(node):
            if node['type'] == 'block':
                result.add(node['content']['terminal'])
            else:
                for child in node['children']:
                    tree(child)
        if document is not None:
            for space in document['spaces']:
                for tab in space['tabs']:
                    tree(tab['root'])
        return result

    def _receipt_consistency(self, terminals):
        manifest = self.store.read('manifest.json')
        if manifest is None or manifest.get('runtime') != 'herdr-core':
            return
        if manifest.get('schema_version') not in (1, 2):
            raise NativeError('core source manifest unsupported')
        previous = checked_plan(manifest['plan'])
        receipt = manifest['receipt']
        if manifest['schema_version'] == 2:
            self._binding_receipt(previous, receipt, manifest['txid'], 2)
        recorded = {receipt['terminals'][p['key']]: p for p in panes(previous)}
        for terminal in terminals:
            if terminal['address'] not in recorded or terminal.get('state') != 'live':
                continue
            pane = recorded[terminal['address']]
            labels = (receipt['labels'][pane['key']] if manifest['schema_version'] == 2
                      else self._labels(manifest['txid'], pane))
            program = self._actual_core_program(terminal) if manifest['schema_version'] == 2 else self._program(terminal)
            if (not self._same_labels(terminal.get('labels'), labels)
                    or program != (pane['session_id'], pane['cwd'])):
                raise NativeError('core source identity contradicts owned receipt')

    def _owned_target(self, target, value, replace_target):
        owned = self.store.read('owned-' + target + '.json')
        if owned is not None:
            if owned.get('document') != value:
                raise NativeError('target has unexplained native edits')
        elif value not in (None, {'spaces': []}) and not replace_target:
            raise NativeError('target replacement requires explicit approval')

    @bounded
    def preflight(self, target, replace_target=False):
        runtime(target)
        self._binary(target)
        self.selected()
        if target == 'tui':
            if self.endpoint_present(target):
                raise NativeError('target TUI already active')
            snapshot = self._optional_snapshot()
            if snapshot is not None:
                checked_plan(layout.from_tui_snapshot(snapshot))
                self._owned_target(target, snapshot, replace_target)
        elif self.endpoint_present(target):
            self.core('server.status', {})
            document, _ = self._document()
            terminals = self._terminals()
            for terminal in terminals:
                if terminal.get('state') == 'live' and self._live_program(terminal)[0] is not None:
                    raise NativeError('target already has live session clients')
            self._owned_target(target, document, replace_target)
        # An absent core cannot be queried without starting it. Persisted doc
        # ownership is checked in prepare after explicit server.start, before
        # terminal.run or doc.set; preflight is not replacement authorization.

    def _other_off(self, target):
        other = 'tui' if target == 'herdr-core' else 'herdr-core'
        if self.endpoint_present(other):
            raise NativeError('other runtime endpoint still present')

    def _source_other_safe(self, source):
        # Initial desktop adoption may already have a running core containing
        # only plain shells. Do not start it here, and never allow agent clients
        # there while capturing/stopping TUI. prepare still enforces replacement
        # authority and retains the old document/terminal records privately.
        if source == 'tui' and self.endpoint_present('herdr-core'):
            for terminal in self._terminals():
                if terminal.get('state') != 'finished':
                    if self._live_program(terminal)[0] is not None:
                        raise NativeError('other runtime has live agent clients')
                    self._shell_proof(terminal)
        elif source == 'herdr-core':
            self._other_off(source)

    def _wait(self, check, *, seconds=None):
        deadline = time.monotonic() + (self.poll_seconds if seconds is None else seconds)
        while True:
            if check():
                return
            if time.monotonic() >= deadline:
                raise NativeError('native readiness or stop proof unavailable')
            time.sleep(0.1)

    def _api_inventory(self, snapshot):
        if snapshot.get('version') != '0.9.5' or type(snapshot.get('protocol')) is not int:
            raise NativeError('TUI API snapshot schema incompatible')
        for key, maximum in [('workspaces', layout.MAX_SPACES), ('tabs', layout.MAX_TABS),
                             ('panes', layout.MAX_PANES), ('agents', layout.MAX_PANES),
                             ('layouts', layout.MAX_TABS)]:
            if type(snapshot.get(key)) is not list or len(snapshot[key]) > maximum:
                raise NativeError('TUI API inventory invalid')
        result = []
        seen_panes = set()
        seen_tabs = set()
        seen_spaces = set()
        for space in snapshot['workspaces']:
            wid = space['workspace_id']
            if wid in seen_spaces:
                raise NativeError('TUI duplicate workspace')
            seen_spaces.add(wid)
            item = {'name': space['label'], 'tabs': []}
            for tab in [t for t in snapshot['tabs'] if t['workspace_id'] == wid]:
                tid = tab['tab_id']
                if tid in seen_tabs:
                    raise NativeError('TUI duplicate tab')
                seen_tabs.add(tid)
                native_panes = [p for p in snapshot['panes'] if p['tab_id'] == tid and p['workspace_id'] == wid]
                agents = [a for a in snapshot['agents'] if a['tab_id'] == tid and a['workspace_id'] == wid]
                mapped = {}
                for pane in native_panes:
                    pid = pane['pane_id']
                    if pid in seen_panes or pane.get('restore_error'):
                        raise NativeError('TUI duplicate or failed pane')
                    seen_panes.add(pid)
                    agent = pane.get('agent')
                    native_identity = pane.get('agent_session')
                    if pane.get('display_agent') is not None and agent is None:
                        raise NativeError('TUI unauthoritative agent identity')
                    if agent not in (None, 'opencode') or (agent is not None and native_identity is None):
                        raise NativeError('TUI unsupported or unknown agent')
                    identity = layout._native_session({'agent_name': agent, 'agent_session': native_identity})
                    views = [a for a in agents if a['pane_id'] == pid]
                    if len(views) > 1:
                        raise NativeError('TUI duplicate agent views')
                    if identity is not None:
                        if (len(views) != 1 or views[0].get('agent_session') != native_identity
                                or views[0].get('agent') != 'opencode' or views[0].get('launch_pending')):
                            raise NativeError('TUI agent identity not live')
                    elif views and (views[0].get('agent') is not None or views[0].get('agent_session') is not None):
                        raise NativeError('TUI inconsistent agent view')
                    mapped[pid] = {'cwd': pane.get('foreground_cwd') or pane.get('cwd'), 'session_id': identity}
                if len(mapped) != tab['pane_count']:
                    raise NativeError('TUI pane inventory incomplete')
                if any(a['pane_id'] not in mapped for a in agents):
                    raise NativeError('TUI unrepresented agent view')
                item['tabs'].append({'name': tab['label'], 'id': tid, 'panes': mapped})
            if len(item['tabs']) != space['tab_count']:
                raise NativeError('TUI tab inventory incomplete')
            result.append(item)
        if len(seen_panes) != len(snapshot['panes']) or len(seen_tabs) != len(snapshot['tabs']):
            raise NativeError('TUI orphaned inventory')
        for view in snapshot['agents']:
            matches = [p for p in snapshot['panes'] if
                       (p['workspace_id'], p['tab_id'], p['pane_id']) ==
                       (view['workspace_id'], view['tab_id'], view['pane_id'])]
            if len(matches) != 1:
                raise NativeError('TUI orphaned agent view')
        return result

    def _tui_live(self):
        response = self.tui('session.snapshot', {})
        if response.get('type') != 'session_snapshot':
            raise NativeError('TUI snapshot response invalid')
        snapshot = layout._json_copy(response['snapshot'])
        inventory = self._api_inventory(snapshot)
        # API has no workspace identity_cwd. Retain it from the private native
        # snapshot; refuse missing/stale workspace identity instead of guessing.
        disk = self._optional_snapshot()
        if disk is None:
            raise NativeError('TUI workspace directory proof unavailable')
        old = layout.from_tui_snapshot(disk)
        identities = layout.tui_public_identities(disk)
        names = layout.tui_names(disk)
        if len(old['spaces']) != len(inventory):
            raise NativeError('TUI workspace directory proof stale')
        spaces = []
        process_info = []
        for si, space in enumerate(inventory):
            previous = old['spaces'][si]
            binding = identities[si]
            native_space = snapshot['workspaces'][si]
            layout._string(space['name'], 512)
            if binding is not None and native_space['workspace_id'] != binding['id']:
                raise NativeError('TUI persisted workspace identity stale')
            if binding is not None and (
                    type(native_space.get('pane_count')) is not int
                    or type(native_space.get('tab_count')) is not int
                    or native_space['pane_count'] != sum(len(t['panes']) for t in binding['tabs'])):
                raise NativeError('TUI persisted workspace pane count stale')
            if names[si]['custom_name'] is not None and space['name'] != previous['name']:
                raise NativeError('TUI workspace directory proof ambiguous')
            if len(space['tabs']) != len(previous['tabs']):
                raise NativeError('TUI persisted tab inventory stale')
            canonical = {'name': previous['name'], 'directory': previous['directory'], 'tabs': []}
            for ti, tab in enumerate(space['tabs']):
                expected = binding['tabs'][ti] if binding is not None else None
                name = names[si]['tabs'][ti]
                if tab['name'] != (str(ti + 1) if name is None else name):
                    raise NativeError('TUI persisted tab name stale')
                if expected is not None:
                    api_tab = next(t for t in snapshot['tabs'] if t['tab_id'] == tab['id'])
                    if (tab['id'] != expected['id'] or type(api_tab.get('number')) is not int
                            or type(api_tab.get('pane_count')) is not int
                            or api_tab['number'] != expected['number'] or tab['panes'] != expected['panes']):
                        raise NativeError('TUI persisted public identity stale')
                exported = self.tui('layout.export', {'tab_id': tab['id']})
                if exported.get('type') != 'layout_export' or exported['layout']['tab_id'] != tab['id']:
                    raise NativeError('TUI layout export incompatible')
                if binding is not None and exported['layout'].get('workspace_id') != binding['id']:
                    raise NativeError('TUI layout workspace identity stale')
                tab_panes = []
                used = set()
                public_keys = {}

                def tree(node, depth=1):
                    if depth > layout.MAX_DEPTH or type(node) is not dict:
                        raise NativeError('TUI layout unsupported')
                    if node.get('type') == 'pane':
                        pid = node.get('pane_id')
                        if pid not in tab['panes'] or pid in used:
                            raise NativeError('TUI layout pane coverage incomplete')
                        used.add(pid)
                        key = f's{si}-t{ti}-p{len(tab_panes)}'
                        public_keys[key] = pid
                        tab_panes.append({'key': key, **tab['panes'][pid]})
                        facts = self.tui('pane.process_info', {'pane_id': pid})
                        if facts.get('type') != 'pane_process_info':
                            raise NativeError('TUI process proof unavailable')
                        info = facts['process_info']
                        if info.get('pane_id') != pid or type(info.get('shell_pid')) is not int:
                            raise NativeError('TUI process coverage incomplete')
                        process_info.append(info)
                        return {'pane': key}
                    # Pinned schema/common.rs SplitDirection (snake_case).
                    if node.get('type') != 'split' or node.get('direction') not in ('right', 'down'):
                        raise NativeError('TUI layout split unsupported')
                    return {'axis': 'row' if node['direction'] == 'right' else 'column',
                            'ratio': node['ratio'], 'children': [tree(node['first'], depth + 1), tree(node['second'], depth + 1)]}

                root = tree(exported['layout']['root'])
                if used != set(tab['panes']):
                    raise NativeError('TUI layout pane coverage incomplete')
                def public_tree(node):
                    if 'pane' in node:
                        return {'pane': public_keys[node['pane']]}
                    return {'axis': node['axis'], 'ratio': layout._ratio(node['ratio']),
                            'children': [public_tree(child) for child in node['children']]}
                if expected is not None and public_tree(root) != expected['root']:
                    raise NativeError('TUI persisted topology stale')
                canonical['tabs'].append({'name': previous['tabs'][ti]['name'], 'root': root, 'panes': tab_panes})
            spaces.append(canonical)
        plan = checked_plan({'schema_version': 1, 'spaces': spaces})
        return plan, snapshot, process_info

    def _pid_proofs(self, pids):
        result = []
        for pid in sorted(set(pids)):
            if type(pid) is not int or pid <= 1:
                raise NativeError('native client PID invalid')
            directory = self.proc_root / str(pid)
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or processes.task_uid(directory) != os.getuid():
                raise NativeError('native client ownership unavailable')
            state, ticks = processes.identity(directory, pid)
            if state in ('Z', 'X'):
                raise NativeError('native client already exited')
            result.append({'pid': pid, 'start_ticks': ticks})
        return result

    def _pids_absent(self, captured):
        for item in captured:
            directory = self.proc_root / str(item['pid'])
            try:
                info = directory.lstat()
                if not stat.S_ISDIR(info.st_mode) or processes.task_uid(directory) != os.getuid():
                    raise NativeError('native client exit ownership uncertain')
                state, ticks = processes.identity(directory, item['pid'])
                if state not in ('Z', 'X') and ticks == item['start_ticks']:
                    return False
            except (FileNotFoundError, ProcessLookupError):
                continue
        return True

    def _tui_process_proofs(self, facts, clients):
        foreground = [p for fact in facts for p in fact.get('foreground_processes', [])]
        known = {p['pid'] for p in clients}
        for proc in foreground:
            # Optional API argv is not proof of the actual foreground program.
            argv = self.process_argv(proc['pid'])
            is_shell = argv and argv[0] in ('/bin/bash', 'bash', '-bash') and argv[1:] in ([], ['-l'], ['--login'])
            # Pinned TUI defaults to /bin/sh when exec-tui leaves SHELL unset.
            # Admit only its idle argv; never sh -c, flags or arbitrary aliases.
            is_shell = is_shell or argv == ['/bin/sh']
            if proc['pid'] not in known and not is_shell:
                raise NativeError('TUI unknown foreground process')
        if any(client['pid'] not in {p['pid'] for p in foreground} for client in clients):
            raise NativeError('TUI session process coverage incomplete')
        return self._pid_proofs([f['shell_pid'] for f in facts] + [p['pid'] for p in foreground])

    def _captured_tui_names(self, capture):
        if 'tui_names' in capture:
            return capture['tui_names']
        # Pre-007G captures retain the authoritative native file in their backup.
        backup = self.store.read(capture['backup'])
        if backup is None:
            raise NativeError('TUI captured naming provenance unavailable')
        return layout.tui_names(backup['snapshot'])

    @bounded
    def capture(self, source):
        runtime(source)
        self._binary(source)
        self._source_other_safe(source)
        if not self.endpoint_present(source):
            raise NativeError('source endpoint unavailable')
        if source == 'tui':
            plan, api, facts = self._tui_live()
            clients = self._coverage(plan)
            proofs = self._tui_process_proofs(facts, clients)
            snapshot = self._optional_snapshot()
            value = {'plan': plan, 'api': api, 'clients': clients, 'pids': proofs,
                     'tui_names': layout.tui_names(snapshot),
                     'backup': self._backup({'snapshot': snapshot})}
        else:
            document, version = self._document()
            terminals = self._terminals()
            self._receipt_consistency(terminals)
            plan = self._from_core(document, terminals)
            clients = self._coverage(plan)
            addresses = self._document_terminals(document)
            active = [item for item in terminals if item['address'] in addresses and item.get('state') == 'live']
            represented = {item['pid'] for item in active if item.get('state') == 'live'}
            represented |= {item['foreground']['pid'] for item in active if item.get('foreground')}
            if any(client['pid'] not in represented for client in clients):
                raise NativeError('core session process coverage incomplete')
            value = {'plan': plan, 'clients': clients, 'pids': self._pid_proofs(represented),
                     'document': document, 'doc_version': version, 'terminals': terminals,
                     'stop_terminals': sorted(addresses),
                     'backup': self._backup({'document': document, 'doc_version': version, 'terminals': terminals})}
        self._db_sessions(plan)
        value['runtime'] = source
        return value

    def _semantic(self, plan):
        """Compare topology/labels/identities independent of native pane numbering."""
        result = []
        for space in checked_plan(plan)['spaces']:
            tabs = []
            for tab in space['tabs']:
                lookup = {p['key']: p for p in tab['panes']}

                def tree(node):
                    if 'pane' in node:
                        p = lookup[node['pane']]
                        return {'cwd': p['cwd'], 'session_id': p['session_id']}
                    return {'axis': node['axis'], 'ratio': round(node['ratio'], 6),
                            'children': [tree(c) for c in node['children']]}

                tabs.append({'name': tab['name'], 'root': tree(tab['root'])})
            result.append({'name': space['name'], 'directory': space['directory'], 'tabs': tabs})
        return result

    @bounded
    def stop(self, source, capture):
        runtime(source)
        if capture.get('runtime') != source:
            raise NativeError('source capture runtime mismatch')
        plan = checked_plan(capture['plan'])
        previous_stop = self.store.read('source-stop.json')
        if previous_stop and previous_stop.get('backup') == capture['backup'] and previous_stop.get('pending'):
            raise NativeError('source stop outcome requires explicit recovery')
        self._source_other_safe(source)
        if self._coverage(plan) != capture['clients']:
            raise NativeError('source client inventory changed after capture')
        stop_record = {'runtime': source, 'backup': capture['backup'], 'pending': None}
        manifest = self.store.read('manifest.json')
        if source == 'herdr-core' and manifest and manifest.get('schema_version') == 2:
            stop_record.update(txid=manifest['txid'], terminals=[], pids=capture['pids'], completed=False)

        def intent(operation, **fields):
            stop_record['pending'] = {'operation': operation, **fields}
            self.store.write('source-stop.json', stop_record)

        def observed():
            stop_record['pending'] = None
            self.store.write('source-stop.json', stop_record)

        if source == 'tui':
            live, _, _ = self._tui_live()
            if (self._semantic(live) != self._semantic(plan)
                    or layout.tui_names(self._optional_snapshot()) != self._captured_tui_names(capture)):
                raise NativeError('TUI source changed after capture')
            # Stop both managed and manually started default TUI without ever
            # touching the independent F01 OpenCode user service.
            intent('tui.stop')
            # Durable intent is a scheduling boundary. Re-observe actual programs
            # and PID identities immediately before the destructive native stop.
            live, _, facts = self._tui_live()
            if (self._semantic(live) != self._semantic(plan)
                    or layout.tui_names(self._optional_snapshot()) != self._captured_tui_names(capture)):
                raise NativeError('TUI source changed after capture')
            clients = self._coverage(live)
            if clients != capture['clients'] or self._tui_process_proofs(facts, clients) != capture['pids']:
                raise NativeError('TUI source process inventory changed after capture')
            self.command(['herdr', 'session', 'stop', 'default', '--json'], timeout=25)
            # The CLI's success alone is not an observation of process exit.
            self._wait(lambda: not self.endpoint_present(source) and self._pids_absent(capture['pids']))
            observed()
            intent('tui.unit.stop')
            self.command(['/usr/bin/systemctl', '--user', 'stop', 'remote-herdr-tui.service'])
            observed()
        else:
            document, version = self._document()
            if document != capture['document'] or version != capture['doc_version']:
                raise NativeError('core source document changed after capture')
            live = self._from_core(document, self._terminals())
            if self._semantic(live) != self._semantic(plan):
                raise NativeError('core source program changed after capture')
            if self._pid_proofs([p['pid'] for p in capture['pids']]) != capture['pids']:
                raise NativeError('core source PID changed after capture')
            for terminal in capture['terminals']:
                if terminal['address'] not in capture['stop_terminals']:
                    continue
                if terminal.get('state') == 'live':
                    if 'terminals' in stop_record:
                        assert isinstance(stop_record['terminals'], list)
                        stop_record['terminals'].append(terminal['address'])
                    intent('terminal.kill', terminal=terminal['address'])
                    # Recheck after durable intent, immediately before each kill.
                    # Earlier kills may have changed other terminals/processes.
                    current, current_version = self._document()
                    if current != capture['document'] or current_version != capture['doc_version']:
                        raise NativeError('core source document changed after capture')
                    actual = self._terminal(terminal['address'])
                    if actual != terminal:
                        raise NativeError('core source terminal changed after capture')
                    self._live_program(actual)
                    pids = {actual['pid']}
                    if actual.get('foreground'):
                        pids.add(actual['foreground']['pid'])
                    expected = [p for p in capture['pids'] if p['pid'] in pids]
                    if self._pid_proofs(pids) != expected:
                        raise NativeError('core source PID changed after capture')
                    self.core('terminal.kill', {'terminal': terminal['address']})
                    self._wait(lambda: self._terminal(terminal['address']).get('state') == 'finished')
                    observed()
            intent('server.stop')
            self.command(['herdr-core', 'server', 'stop', '--json'])

        def stopped():
            if self.endpoint_present(source) or not self._pids_absent(capture['pids']):
                return False
            self.absent(sessions(plan), capture['clients'])
            return True

        self._wait(stopped)
        if 'completed' in stop_record:
            stop_record['completed'] = True
        observed()
        return self.reconcile_stopped(source, capture)

    @bounded
    def reconcile_stopped(self, source, capture):
        """Return the captured plan after observational stop reconciliation.

        Caller owns serialization and journal advancement. Never replay native
        stop effects or change manifest/journal/stop intent. Require endpoint off,
        captured process identities gone and exact sessions absent. Reconcile only
        an already-owned native document; retain TUI post-stop snapshot backup.
        """
        runtime(source)
        if capture.get('runtime') != source:
            raise NativeError('source capture runtime mismatch')
        plan = checked_plan(capture['plan'])
        if self.endpoint_present(source) or not self._pids_absent(capture['pids']):
            raise NativeError('source stop proof unavailable')
        self.absent(sessions(plan), capture['clients'])
        if source == 'tui':
            snapshot = self._json(self.snapshot_path)
            final = layout.from_tui_snapshot(snapshot)
            if (self._semantic(final) != self._semantic(plan)
                    or layout.tui_names(snapshot) != self._captured_tui_names(capture)):
                raise NativeError('TUI saved layout differs from live capture')
            self._backup({'snapshot': snapshot})
            if self.store.read('owned-tui.json') is not None:
                self.store.write('owned-tui.json', {'document': snapshot})
            return final
        if self.store.read('owned-herdr-core.json') is not None:
            self.store.write('owned-herdr-core.json', {'document': layout._json_copy(capture['document'])})
        return plan

    @bounded
    def prepare(self, target, plan, txid, replace_target=False):
        runtime(target)
        plan = checked_plan(plan)
        self._binary(target)
        self._other_off(target)
        self.absent(sessions(plan), [])
        self._db_sessions(plan)
        receipt = {'runtime': target, 'txid': txid, 'document': None, 'doc_version': 0,
                   'terminals': {}, 'pending': None}
        self._receipt(receipt)
        if target == 'herdr-core':
            if not self.endpoint_present(target):
                receipt['pending'] = {'operation': 'server.start'}
                self._receipt(receipt)
                self.command(['herdr-core', 'server', 'start', '--json'])
                self._wait(lambda: self.endpoint_present(target))
                receipt['pending'] = None
                self._receipt(receipt)
            self.core('server.status', {})
            self._wait_core_spawns()
            document, version = self._document()
            terminals = self._terminals()
            for terminal in terminals:
                if terminal.get('state') == 'live' and self._live_program(terminal)[0] is not None:
                    raise NativeError('target already has live session clients')
            self._owned_target(target, document, replace_target)
            receipt.update({'document': document, 'doc_version': version,
                            'backup': self._backup({'document': document, 'doc_version': version, 'terminals': terminals})})
        else:
            if self.endpoint_present(target):
                raise NativeError('target TUI already active')
            snapshot = self._optional_snapshot()
            self._owned_target(target, snapshot, replace_target)
            receipt.update({'document': snapshot, 'backup': self._backup({'snapshot': snapshot})})
        self._receipt(receipt)
        return receipt

    def _labels(self, txid, pane):
        labels = {'remote-herdr-owner': txid, 'remote-herdr-pane': pane['key']}
        if pane['session_id'] is not None:
            labels['remote-herdr-session'] = pane['session_id']
        return labels

    @staticmethod
    def _same_labels(observed, expected):
        # Core 0.1.18 drops empty values. Normalize only the legacy optional
        # session label; never forgive missing owner/pane or unrelated labels.
        if type(observed) is not dict or type(expected) is not dict:
            return False
        def canonical(labels):
            return {k: v for k, v in labels.items() if k != 'remote-herdr-session' or v != ''}
        return canonical(observed) == canonical(expected)

    @bounded
    def recover_prepared(self, target, plan, txid, replace_target=False):
        """Reconcile prepare's read/backup/start-only effects, never terminal.run."""
        runtime(target)
        plan = checked_plan(plan)
        self._other_off(target)
        self.absent(sessions(plan), [])
        receipt = self.store.read('receipt-' + txid + '.json')
        if receipt is None:
            # prepare's first action persists this receipt, before native effects.
            return self.prepare(target, plan, txid, replace_target)
        if (receipt.get('runtime') != target or receipt.get('txid') != txid
                or receipt.get('terminals') != {}):
            raise NativeError('preparation receipt inconsistent')
        pending = receipt.get('pending')
        if pending:
            if target != 'herdr-core' or pending != {'operation': 'server.start'}:
                raise NativeError('preparation mutation unsupported')
            # A disconnected start may still be in flight. Observe it, never
            # launch a second start based only on missing socket/client evidence.
            self._wait(lambda: self.endpoint_present(target))
            self.core('server.status', {})
        if 'backup' in receipt:
            if self.store.read(receipt['backup']) is None:
                raise NativeError('preparation backup unavailable')
            if target == 'herdr-core':
                self._wait_core_spawns()
                document, version = self._document()
                if document != receipt['document'] or version != receipt['doc_version']:
                    raise NativeError('prepared target changed')
                for terminal in self._terminals():
                    if terminal.get('state') == 'live':
                        if self._program(terminal)[0] is not None:
                            raise NativeError('prepared target contains live agent')
                        self._shell_proof(terminal)
            elif self._optional_snapshot() != receipt['document'] or self.endpoint_present(target):
                raise NativeError('prepared TUI target changed')
            self._owned_target(target, receipt['document'], replace_target)
            receipt['pending'] = None
            self._receipt(receipt)
            return receipt
        # No target writes or terminal starts occur during prepare. With native
        # start observed, recapture/backup is safe; prior backup files are retained.
        return self.prepare(target, plan, txid, replace_target)

    @bounded
    def recover_tui(self, plan, txid, receipt, *, preserve_snapshot=False):
        """Reconcile offline write/start using exact bytes and unit ownership."""
        plan = checked_plan(plan)
        if receipt.get('runtime') != 'tui' or receipt.get('txid') != txid or self.selected() != 'tui':
            raise NativeError('TUI recovery identity mismatch')
        self._other_off('tui')
        if self.endpoint_present('tui'):
            self.verify('tui', plan, receipt)
            receipt['pending'] = None
            self._receipt(receipt)
            return receipt
        pending = receipt.get('pending')
        if pending and pending.get('operation') not in {'tui.write', 'tui.start'}:
            raise NativeError('TUI pending mutation unsupported')
        state = self.command(['/usr/bin/systemctl', '--user', 'show', 'remote-herdr-tui.service',
                              '--property=ActiveState', '--value'])
        if not isinstance(state, str) or state.strip() not in {'inactive', 'failed'}:
            # Type=exec can still be starting after its CLI acknowledgement.
            self._wait_ready('tui', plan, receipt)
            receipt['pending'] = None
            self._receipt(receipt)
            return receipt
        self.absent(sessions(plan), [])
        generated = layout.to_tui_snapshot(plan)
        current = self._optional_snapshot()
        if preserve_snapshot:
            if (current != receipt['document'] or current is None
                    or self._semantic(layout.from_tui_snapshot(current)) != self._semantic(plan)):
                raise NativeError('TUI boot snapshot has unexplained edits')
            # Boot observes a saved native snapshot, not a switch-generated file.
            # Supported focus/default/history fields and original bytes stay intact.
            generated = current
        elif current != generated:
            if current != receipt['document'] or pending and pending.get('operation') == 'tui.start':
                raise NativeError('TUI recovery snapshot has unexplained edits')
            receipt['pending'] = {'operation': 'tui.write', 'document': generated}
            self._receipt(receipt)
            self._atomic(self.snapshot_path, json.dumps(generated).encode())
        receipt['document'] = generated
        receipt['pending'] = {'operation': 'tui.start'}
        self._receipt(receipt)
        self.command(['/usr/bin/systemctl', '--user', 'start', 'remote-herdr-tui.service'])
        self._wait_ready('tui', plan, receipt)
        receipt['pending'] = None
        self._receipt(receipt)
        return receipt

    def _match_terminal(self, terminal, pane, txid):
        if not self._same_labels(terminal.get('labels'), self._labels(txid, pane)):
            raise NativeError('core terminal ownership mismatch')
        identity, cwd = self._program(terminal)
        if (identity, cwd) != (pane['session_id'], pane['cwd']):
            raise NativeError('core terminal session or directory mismatch')
        if identity is not None:
            pid = (terminal.get('foreground') or terminal)['pid']
            self._client_argv(pid, identity)
        else:
            self._shell_proof(terminal)

    def _safe_live_terminals(self, plan, receipt):
        assigned = {address: key for key, address in receipt['terminals'].items()}
        by_key = {p['key']: p for p in panes(plan)}
        for terminal in self._terminals():
            if terminal.get('state') == 'finished':
                continue
            address = terminal['address']
            if address in assigned:
                self._match_terminal(terminal, by_key[assigned[address]], receipt['txid'])
            elif self._live_program(terminal)[0] is not None:
                raise NativeError('target contains unowned live agent')

    def _cas(self, plan, receipt):
        expected = layout.to_app_document(plan, receipt['terminals'])
        current, version = self._document()
        if current == expected:
            receipt.update({'document': expected, 'doc_version': version, 'pending': None})
            self._receipt(receipt)
            return
        if current != receipt['document'] or version != receipt['doc_version']:
            raise NativeError('core document CAS conflict')
        receipt['pending'] = {'operation': 'doc.set', 'document': expected, 'version': version}
        self._receipt(receipt)
        result = self.core('doc.set', {'name': 'herdr-app', 'value': expected, 'version': version})
        if type(result.get('version')) is not int or result['version'] <= version:
            raise NativeError('core document CAS outcome uncertain')
        receipt.update({'document': expected, 'doc_version': result['version'], 'pending': None})
        self._receipt(receipt)

    @bounded
    def restore(self, target, plan, txid, receipt):
        runtime(target)
        plan = checked_plan(plan)
        receipt = layout._json_copy(receipt)
        if receipt.get('runtime') != target or receipt.get('txid') != txid:
            raise NativeError('restore receipt identity mismatch')
        self._other_off(target)
        if self.selected() != target:
            raise NativeError('restore target not selected')
        self._db_sessions(plan)
        if target == 'tui':
            self.absent(sessions(plan), [])
            if self.endpoint_present(target):
                raise NativeError('TUI restore requires offline target')
            if receipt.get('pending'):
                raise NativeError('TUI prior mutation requires explicit recovery')
            if self._optional_snapshot() != receipt['document']:
                raise NativeError('TUI target changed after backup')
            generated = layout.to_tui_snapshot(plan)
            receipt['pending'] = {'operation': 'tui.write', 'document': generated}
            self._receipt(receipt)
            self.snapshot_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._atomic(self.snapshot_path, json.dumps(generated).encode())
            receipt['document'] = generated
            receipt['pending'] = {'operation': 'tui.start'}
            self._receipt(receipt)
            self.command(['/usr/bin/systemctl', '--user', 'start', 'remote-herdr-tui.service'])
            self._wait(lambda: self.endpoint_present(target))
            self._wait_ready(target, plan, receipt)
            receipt['pending'] = None
            self._receipt(receipt)
            return receipt
        if receipt.get('pending') is not None:
            raise NativeError('core prior mutation requires explicit recovery')
        current, version = self._document()
        if current != receipt['document'] or version != receipt['doc_version']:
            raise NativeError('core target changed after backup')
        for pane in panes(plan):
            key = pane['key']
            if key in receipt['terminals']:
                self._match_terminal(self._terminal(receipt['terminals'][key]), pane, txid)
                continue
            if pane['session_id'] is not None and self.scan({pane['session_id']}):
                raise NativeError('session client already running')
            self._safe_live_terminals(plan, receipt)
            labels = self._labels(txid, pane)
            # Existing owner labels without a recorded address imply an uncertain
            # earlier create, not permission for a blind duplicate create.
            if any(self._same_labels(t.get('labels'), labels) and t.get('state') != 'finished' for t in self._terminals()):
                raise NativeError('core prior terminal creation requires recovery')
            receipt['pending'] = {'operation': 'terminal.run', 'pane': key, 'labels': labels}
            self._receipt(receipt)
            argv = [str(self.home / '.local/bin/opencode'), '--session', pane['session_id']] if pane['session_id'] else ['/bin/bash', '-l']
            created = self.core('terminal.run', {'argv': argv, 'cwd': pane['cwd'], 'labels': labels,
                                                'keep': True, 'no_parent': True, 'no_notify': True, 'wait': False})
            address = created.get('address')
            if not isinstance(address, str) or not re.fullmatch(r't[0-9a-z]+', address):
                raise NativeError('core terminal creation outcome uncertain')
            receipt['terminals'][key] = address
            receipt['pending'] = None
            self._receipt(receipt)
            def terminal_ready():
                try:
                    self._match_terminal(self._terminal(address), pane, txid)
                    return True
                except (NativeError, ValueError, OSError):
                    return False
            try:
                self._wait(terminal_ready)
            except NativeError as error:
                if str(error) == 'native readiness or stop proof unavailable':
                    raise NativeError('core restored terminal readiness unavailable') from None
                raise
        self._cas(plan, receipt)
        self._wait_ready(target, plan, receipt)
        return receipt

    def _wait_ready(self, target, plan, receipt):
        # Only observational readiness is retried, never a native mutation.
        def ready():
            try:
                self.verify(target, plan, receipt)
                return True
            except NativeError:
                return False
        try:
            self._wait(ready)
        except NativeError as error:
            if str(error) == 'native readiness or stop proof unavailable':
                raise NativeError('restored runtime layout readiness unavailable') from None
            raise

    @bounded
    def verify(self, target, plan, receipt):
        runtime(target)
        plan = checked_plan(plan)
        self._other_off(target)
        if self.selected() != target or not self.endpoint_present(target):
            raise NativeError('selected runtime readiness unavailable')
        if target == 'herdr-core':
            document, version = self._document()
            if receipt.get('current_document') is True:
                self._verify_current(plan, receipt, document, version)
                self.store.write('owned-' + target + '.json', {'document': document})
                return
            expected = layout.to_app_document(plan, receipt['terminals'])
            if document != expected:
                raise NativeError('core restored layout differs')
            for pane in panes(plan):
                self._match_terminal(self._terminal(receipt['terminals'][pane['key']]), pane, receipt['txid'])
            self._safe_live_terminals(plan, receipt)
            receipt.update({'document': document, 'doc_version': version})
        else:
            live, _, _ = self._tui_live()
            if self._semantic(live) != self._semantic(plan):
                raise NativeError('TUI restored layout differs')
        self._coverage(plan)
        self._db_sessions(plan)
        owned = receipt['document']
        self.store.write('owned-' + target + '.json', {'document': owned})

    @bounded
    def restore_current(self):
        """Reconcile current desktop ownership, or resume unpublished migration."""
        manifest = self.store.read('manifest.json')
        if self.selected() != 'herdr-core':
            raise NativeError('core recovery runtime not selected')
        self._other_off('herdr-core')
        if manifest is None and not self.endpoint_present('herdr-core'):
            return
        self._binary('herdr-core')
        if manifest is None:
            self._wait_core_spawns()
            document, version = self._document()
            if document is None:
                return
            txid = uuid.uuid4().hex
            receipt = {'runtime': 'herdr-core', 'txid': txid, 'document': document,
                       'doc_version': version, 'terminals': {}, 'pending': None}
            self._restore_document(None, {'schema_version': 1, 'spaces': []}, receipt)
            return
        if (type(manifest) is not dict
                or set(manifest) != {'schema_version', 'runtime', 'plan', 'receipt', 'txid'}
                or type(manifest['schema_version']) is not int or manifest['schema_version'] not in (1, 2)
                or manifest['runtime'] != 'herdr-core'
                or type(manifest['txid']) is not str
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', manifest['txid'])):
            raise NativeError('runtime manifest unavailable or unsupported')
        plan = checked_plan(manifest['plan'])
        receipt = self.store.read('receipt-' + manifest['txid'] + '.json') or manifest['receipt']
        receipt = layout._json_copy(receipt)
        if type(receipt) is dict and receipt.get('current_document') is True:
            # The receipt is durable before manifest publication and may contain
            # an adopted plan newer than either the manifest or switch journal.
            plan = checked_plan(receipt.get('plan'))
        self._binding_receipt(plan, receipt, manifest['txid'], manifest['schema_version'])
        if not self.endpoint_present('herdr-core'):
            if receipt.get('pending') and receipt['pending'].get('operation') == 'server.start':
                raise NativeError('core start outcome remains uncertain')
            previous = receipt.get('pending')
            receipt['pending'] = {'operation': 'server.start', 'previous': previous}
            self._receipt(receipt)
            self.command(['herdr-core', 'server', 'start', '--json'])
            self._wait(lambda: self.endpoint_present('herdr-core'))
            receipt['pending'] = previous
            self._receipt(receipt)
        if receipt.get('pending') and receipt['pending'].get('operation') == 'server.start':
            self.core('server.status', {})
            receipt['pending'] = receipt['pending'].get('previous')
            self._receipt(receipt)
        self._wait_core_spawns()
        if receipt.get('current_document') is True:
            self._reconcile_current_intent(receipt)
            self._restore_document(manifest, receipt['plan'], receipt)
            return
        # Only an unpublished partial v1 migration keeps whole-plan authority.
        if receipt.get('pending') or not self._published_migration_document(plan, receipt):
            self._restore_migration_current()
            return
        self._restore_document(manifest, plan, receipt)

    def _published_migration_document(self, plan, receipt):
        """Recognize v1's exact published target, not merely a full create map.

        Old recovery may already have removed a finished binding from its map.
        Conversely every create can be recorded before the first document CAS.
        Neither case changes whether whole-plan migration authority still applies.
        """
        references = {}
        def record(leaf, address):
            references[leaf] = address
            return None
        try:
            layout.project_app_document(receipt['document'], record)
            if any(references.get(key) != address for key, address in receipt['terminals'].items()):
                return False
            return layout.to_app_document(plan, references) == receipt['document']
        except ValueError:
            return False

    def _binding_receipt(self, plan, receipt, txid, schema):
        if (type(receipt) is not dict or receipt.get('runtime') != 'herdr-core'
                or receipt.get('txid') != txid or type(receipt.get('terminals')) is not dict
                or 'pending' not in receipt or 'document' not in receipt
                or type(receipt.get('doc_version')) is not int or receipt['doc_version'] < 0):
            raise NativeError('core recovery receipt identity mismatch')
        keys = {p['key'] for p in panes(plan)}
        mapping = receipt['terminals']
        if (set(mapping) - keys or any(type(a) is not str or not layout._TERMINAL.fullmatch(a)
                                      for a in mapping.values())
                or len(set(mapping.values())) != len(mapping)):
            raise NativeError('core recovery bindings invalid')
        pending = receipt['pending']
        if pending is not None:
            if type(pending) is not dict or pending.get('operation') not in {
                    'server.start', 'terminal.run', 'terminal.kill', 'doc.set'}:
                raise NativeError('core pending mutation unsupported')
        if schema == 2 or receipt.get('current_document') is True:
            if (receipt.get('current_document') is not True or checked_plan(receipt.get('plan')) != plan
                    or set(mapping) != keys or type(receipt.get('bindings')) is not dict
                    or set(receipt['bindings']) != keys or type(receipt.get('labels')) is not dict
                    or set(receipt['labels']) != keys
                    or len(set(receipt['bindings'].values())) != len(keys)):
                raise NativeError('current document receipt invalid')
            for key in keys:
                leaf = receipt['bindings'][key]
                labels = receipt['labels'][key]
                if (type(leaf) is not str or not leaf or len(leaf) > 512 or type(labels) is not dict
                        or any(type(k) is not str or type(v) is not str for k, v in labels.items())):
                    raise NativeError('current document binding invalid')
            observed = {}
            def record(leaf, address):
                observed[leaf] = address
                return None
            layout.project_app_document(receipt['document'], record)
            if any(observed.get(receipt['bindings'][key]) != address for key, address in mapping.items()):
                raise NativeError('current document saved binding differs')
            if pending is not None:
                fields = {'terminal.kill': {'operation', 'pane', 'leaf', 'terminal', 'pids'},
                          'terminal.run': {'operation', 'pane', 'leaf', 'labels'},
                          'doc.set': {'operation', 'document', 'version'},
                          'server.start': {'operation', 'previous'}}
                if set(pending) != fields[pending['operation']]:
                    raise NativeError('current document mutation intent invalid')
            repairs = receipt.get('repairs')
            if type(repairs) is not dict or set(repairs) - set(receipt['bindings'].values()):
                raise NativeError('current document repairs invalid')
            by_leaf = {receipt['bindings'][p['key']]: p for p in panes(plan)}
            for leaf, repair in repairs.items():
                if (type(repair) is not dict
                        or set(repair) != {'terminal', 'pane', 'created', 'labels', 'stopped', 'pids'}
                        or type(repair['stopped']) is not bool or type(repair['pane']) is not dict
                        or set(repair['pane']) != {'key', 'cwd', 'session_id'}
                        or (repair['pane']['session_id'] is None and not repair['stopped'])
                        or any(repair['pane'][field] != by_leaf[leaf][field] for field in ('cwd', 'session_id'))
                        or repair['terminal'] != mapping[by_leaf[leaf]['key']]
                        or (repair['created'] is not None and (type(repair['created']) is not str
                            or not layout._TERMINAL.fullmatch(repair['created'])))
                        or repair['labels'] != self._labels(txid, {'key': leaf,
                                                       'session_id': repair['pane']['session_id']})):
                    raise NativeError('current document repair binding invalid')
                proofs = repair['pids']
                if proofs is not None and (type(proofs) is not list or not 1 <= len(proofs) <= 2
                        or any(type(p) is not dict or set(p) != {'pid', 'start_ticks'}
                               or type(p['pid']) is not int or p['pid'] <= 1
                               or type(p['start_ticks']) is not int or p['start_ticks'] < 0 for p in proofs)):
                    raise NativeError('current document repair PID proof invalid')
                if repair['stopped'] and proofs is None:
                    raise NativeError('current document repair stop proof unavailable')

    def _actual_core_program(self, terminal, *, unknown=False):
        """Actual process proof, independent of retained launch argv after keep."""
        if terminal.get('state') != 'live':
            raise NativeError('core terminal not live or spawn pending')
        program = terminal.get('foreground') or terminal
        pids = [terminal.get('pid'), program.get('pid')]
        before = self._pid_proofs(pids)
        argv = self.process_argv(program['pid'])
        cwd = self.process_cwd(program['pid'])
        if cwd != program.get('cwd'):
            raise NativeError('core recovery directory mismatch')
        if argv and argv[0] in ('/bin/bash', 'bash', '-bash'):
            self._shell_proof(terminal)
            identity = None
        else:
            try:
                identity = self._session_argv(argv)
            except NativeError:
                if not unknown:
                    raise NativeError('core recovery foreign live program') from None
                identity = False
        if self._pid_proofs(pids) != before:
            raise NativeError('core process identity changed')
        return identity, cwd

    def _current_projection(self, document, terminals, plan, receipt):
        lookup = {t['address']: t for t in terminals}
        old = {p['key']: p for p in panes(plan)}
        known = {receipt.get('bindings', {}).get(k, k): (receipt['terminals'][k], p,
                 receipt.get('labels', {}).get(k, self._labels(receipt['txid'], p)))
                 for k, p in old.items() if k in receipt['terminals']}
        labels, repairs = {}, layout._json_copy(receipt.get('repairs', {}))
        live, proofs = {}, {}
        stop = self.store.read('source-stop.json')
        stopped = {}
        if (stop and stop.get('runtime') == 'herdr-core' and stop.get('txid') == receipt['txid']):
            if stop.get('completed') is not True or stop.get('pending') is not None:
                raise NativeError('core controller stop requires reconciliation')
            backup = self.store.read(stop['backup'])
            if backup is None:
                raise NativeError('core controller stop backup unavailable')
            prior_addresses = {}
            def collect(leaf, address):
                prior_addresses[leaf] = address
                return None
            layout.project_app_document(backup['document'], collect)
            self._pids_absent_or_fail(stop['pids'])
            captured = {t['address']: t for t in backup['terminals']}
            for leaf, address in prior_addresses.items():
                if address not in stop['terminals']:
                    continue
                terminal = captured[address]
                pids = {terminal['pid'], (terminal.get('foreground') or terminal)['pid']}
                captured_proofs = [p for p in stop['pids'] if p['pid'] in pids]
                if {p['pid'] for p in captured_proofs} != pids:
                    raise NativeError('core controller stop process proof unavailable')
                stopped[leaf] = (address, captured_proofs)

        def classify(leaf, address):
            previous = known.get(leaf)
            replaced = False
            repair = repairs.get(leaf)
            if repair:
                if previous is None:
                    raise NativeError('core repair binding unavailable')
                if address not in (repair['terminal'], repair.get('created')):
                    raise NativeError('core repair binding changed')
                desired = repair['pane']
                if repair.get('stopped'):
                    self._pids_absent_or_fail(repair['pids'])
                    if lookup[repair['terminal']].get('state') != 'finished':
                        raise NativeError('core repair stop outcome inconsistent')
                if (not repair.get('stopped') and not repair.get('created')
                        and lookup[address].get('state') == 'finished'):
                    # A user closed the view before our durable stop intent.
                    # This is a tombstone, not authority to resurrect a client.
                    repairs.pop(leaf)
                    return None
                labels[leaf] = repair['labels'] if repair.get('created') else previous[2]
                if repair.get('created'):
                    actual = lookup.get(repair['created'])
                    if (actual is None or not self._same_labels(actual.get('labels'), repair['labels'])
                            or self._actual_core_program(actual) != (desired['session_id'], desired['cwd'])):
                        raise NativeError('core created binding proof unavailable')
                elif not repair.get('stopped'):
                    actual = lookup[address]
                    if (not self._same_labels(actual.get('labels'), previous[2])
                            or self._actual_core_program(actual) != (None, desired['cwd'])):
                        raise NativeError('core repair source ownership or program changed')
                    live[leaf] = actual
                    proofs[leaf] = self._pid_proofs([actual['pid'], (actual.get('foreground') or actual)['pid']])
                return {'cwd': desired['cwd'], 'session_id': desired['session_id']}
            if previous and previous[0] != address:
                old_terminal = lookup.get(previous[0])
                if old_terminal is None or old_terminal.get('state') != 'finished':
                    raise NativeError('core owned leaf terminal changed')
                # A closed terminal is not the current leaf's program. Prove
                # its replacement afresh; never carry over the retired session.
                previous = None
                replaced = True
            terminal = lookup.get(address)
            if terminal is None:
                raise NativeError('core referenced terminal unavailable')
            if terminal.get('state') == 'finished':
                if previous and leaf in stopped and stopped[leaf][0] == address:
                    if not self._same_labels(terminal.get('labels'), previous[2]):
                        raise NativeError('core recovery terminal not owned')
                    desired = previous[1]
                    repairs[leaf] = {'terminal': address, 'pane': desired, 'created': None,
                                     'stopped': True, 'pids': stopped[leaf][1],
                                     'labels': self._labels(receipt['txid'], {'key': leaf, **{
                                         k: desired[k] for k in ('cwd', 'session_id')}})}
                    labels[leaf] = layout._json_copy(previous[2])
                    return {'cwd': desired['cwd'], 'session_id': desired['session_id']}
                return None
            if previous and not self._same_labels(terminal.get('labels'), previous[2]):
                raise NativeError('core recovery terminal not owned')
            identity, cwd = self._actual_core_program(terminal, unknown=previous is None and not replaced)
            if identity is False:
                return None
            if previous:
                desired = previous[1]
                if cwd != desired['cwd']:
                    raise NativeError('core recovery directory mismatch')
                if identity is None and desired['session_id'] is not None:
                    repairs[leaf] = {'terminal': address, 'pane': desired, 'created': None,
                                     'stopped': False, 'pids': None,
                                     'labels': self._labels(receipt['txid'], {'key': leaf, **{
                                         k: desired[k] for k in ('cwd', 'session_id')}})}
                    identity = desired['session_id']
            labels[leaf] = layout._json_copy(terminal.get('labels', {}))
            live[leaf] = terminal
            proofs[leaf] = self._pid_proofs([terminal['pid'], (terminal.get('foreground') or terminal)['pid']])
            return {'cwd': cwd, 'session_id': identity}

        projected, bindings = layout.project_app_document(document, classify)
        for repair in repairs.values():
            allowed = {repair['terminal'], repair.get('created')}
            if any(t.get('state') == 'live' and t['address'] not in allowed
                   and self._same_labels(t.get('labels'), repair['labels']) for t in terminals):
                raise NativeError('prior terminal creation requires recovery')
        # Reconcile the entire desired session inventory once, before any effect.
        found = self.scan(sessions(projected))
        for pane in panes(projected):
            leaf = bindings[pane['key']]['leaf']
            identity = pane['session_id']
            if identity is None:
                continue
            matches = [p for p in found if p['session_id'] == identity]
            repair = repairs.get(leaf)
            expected = 0 if repair and not repair.get('created') else 1
            if len(matches) != expected:
                raise NativeError('session client coverage incomplete or duplicate')
            if matches:
                terminal = lookup[repair['created']] if repair else live[leaf]
                pid = (terminal.get('foreground') or terminal)['pid']
                if matches[0]['pid'] != pid or self.process_cwd(pid) != pane['cwd']:
                    raise NativeError('session client directory or PID mismatch')
                self._client_argv(pid, identity)
        self._db_sessions(projected)
        # Recheck actual programs and start times across the inventory boundary.
        for leaf, terminal in live.items():
            if self._terminal(terminal['address']) != terminal:
                raise NativeError('core current inventory changed')
            if self._pid_proofs([p['pid'] for p in proofs[leaf]]) != proofs[leaf]:
                raise NativeError('core current process identity changed')
            self._actual_core_program(terminal)
        return projected, bindings, labels, repairs

    def _wait_created_core(self, address, pane, labels):
        def ready():
            try:
                terminal = self._terminal(address)
                return (self._same_labels(terminal.get('labels'), labels)
                        and self._actual_core_program(terminal) == (pane['session_id'], pane['cwd']))
            except (NativeError, ValueError, OSError):
                return False
        self._wait(ready)

    def _reconcile_current_intent(self, receipt):
        pending = receipt.get('pending')
        if pending is None:
            return
        operation = pending.get('operation')
        if operation in ('terminal.kill', 'terminal.run'):
            leaf = pending.get('leaf')
            repair = receipt['repairs'].get(leaf)
            if (repair is None or receipt['bindings'].get(pending.get('pane')) != leaf
                    or (operation == 'terminal.kill' and (pending.get('terminal') != repair['terminal']
                        or pending.get('pids') != repair['pids']))
                    or (operation == 'terminal.run' and (pending.get('labels') != repair['labels']
                        or repair.get('stopped') is not True))):
                raise NativeError('core pending mutation binding invalid')
        if operation == 'terminal.kill':
            if self._terminal(pending['terminal']).get('state') != 'finished':
                raise NativeError('uncertain owned shell stop unresolved')
            self._pids_absent_or_fail(pending['pids'])
            receipt['repairs'][pending['leaf']]['stopped'] = True
        elif operation == 'terminal.run':
            matches = [t for t in self._terminals() if self._same_labels(t.get('labels'), pending['labels'])
                       and t.get('state') != 'finished']
            repair = receipt['repairs'][pending['leaf']]
            pane = repair['pane']
            if len(matches) != 1:
                raise NativeError('uncertain terminal creation unresolved')
            address = matches[0]['address']
            if repair['created'] not in (None, address):
                raise NativeError('uncertain created terminal identity changed')
            repair['created'] = address
            self._receipt(receipt)
            self._wait_created_core(address, pane, repair['labels'])
        elif operation == 'doc.set':
            expected = layout.rebind_app_document(receipt['document'],
                {leaf: (repair['terminal'], repair['created']) for leaf, repair in receipt['repairs'].items()})
            if pending.get('document') != expected or pending.get('version') != receipt['doc_version']:
                raise NativeError('core pending document binding invalid')
            current, version = self._document()
            observed = {}
            def record(leaf, address):
                observed[leaf] = address
                return None
            layout.project_app_document(current, record)
            if (version <= pending['version'] or any(
                    observed.get(leaf) != repair['created'] for leaf, repair in receipt['repairs'].items())):
                raise NativeError('uncertain document mutation unresolved')
            # A desktop serialization/rename may follow the successful CAS.
            # Keep the acknowledged proposal internally consistent through a
            # crash; the next projection adopts the actual current document.
            receipt.update(document=pending['document'], doc_version=pending['version'] + 1)
            for key, leaf in receipt['bindings'].items():
                repair = receipt['repairs'].get(leaf)
                if repair:
                    receipt['terminals'][key] = repair['created']
                    receipt['labels'][key] = repair['labels']
            receipt['repairs'] = {}
        else:
            raise NativeError('core pending mutation unsupported')
        receipt['pending'] = None
        self._receipt(receipt)

    def _restore_document(self, manifest, plan, receipt):
        document, version = self._document()
        if document is None:
            raise NativeError('current core document unavailable')
        projected, bindings, labels, repairs = self._current_projection(
            document, self._terminals(), plan, receipt)
        if any(leaf not in {b['leaf'] for b in bindings.values()} for leaf in repairs):
            raise NativeError('core repair leaf missing')
        if not receipt.get('current_document'):
            receipt['adoption_backup'] = self._backup({'manifest': manifest, 'receipt': receipt})
        receipt.update(current_document=True, plan=projected, document=document, doc_version=version,
                       terminals={k: b['terminal'] for k, b in bindings.items()},
                       bindings={k: b['leaf'] for k, b in bindings.items()},
                       labels={k: labels[b['leaf']] for k, b in bindings.items()}, repairs=repairs)
        self._receipt(receipt)
        for key, leaf in receipt['bindings'].items():
            repair = repairs.get(leaf)
            if repair is None or repair.get('created'):
                continue
            repair_sessions = ({repair['pane']['session_id']}
                               if repair['pane']['session_id'] is not None else set())
            terminal = self._terminal(repair['terminal'])
            if terminal.get('state') != 'finished':
                if (not self._same_labels(terminal.get('labels'), receipt['labels'][key])
                        or self._actual_core_program(terminal) != (None, repair['pane']['cwd'])):
                    raise NativeError('core repair source ownership or program changed')
                self._shell_proof(terminal)
                pids = [terminal['pid'], (terminal.get('foreground') or terminal)['pid']]
                proofs = self._pid_proofs(pids)
                repair['pids'] = proofs
                receipt['pending'] = {'operation': 'terminal.kill', 'pane': key, 'leaf': leaf,
                                      'terminal': repair['terminal'], 'pids': proofs}
                self._receipt(receipt)
                self._current_effect_boundary(receipt)
                observed = self._terminal(repair['terminal'])
                if observed != terminal or self._pid_proofs(pids) != proofs:
                    raise NativeError('core recovery process changed before shell stop')
                self._shell_proof(observed)
                if self.scan(repair_sessions):
                    raise NativeError('session client already running')
                self.core('terminal.kill', {'terminal': repair['terminal']})
                self._wait(lambda: self._terminal(repair['terminal']).get('state') == 'finished'
                           and self._pids_absent(proofs))
                receipt['pending'] = None
                repair['stopped'] = True
                self._receipt(receipt)
            elif not repair.get('stopped'):
                raise NativeError('core repair terminal closed before shell stop')
            self._current_effect_boundary(receipt)
            if (self.scan(repair_sessions)
                    or any(t.get('state') == 'live' and self._same_labels(t.get('labels'), repair['labels'])
                           for t in self._terminals())):
                raise NativeError('session client already running')
            receipt['pending'] = {'operation': 'terminal.run', 'pane': key, 'leaf': leaf,
                                  'labels': repair['labels']}
            self._receipt(receipt)
            self._current_effect_boundary(receipt)
            if (self.scan(repair_sessions)
                    or any(t.get('state') == 'live' and self._same_labels(t.get('labels'), repair['labels'])
                           for t in self._terminals())):
                raise NativeError('session client already running')
            pane = repair['pane']
            argv = ([str(self.home / '.local/bin/opencode'), '--session', pane['session_id']]
                    if pane['session_id'] is not None else ['/bin/bash', '-l'])
            result = self.core('terminal.run', {'argv': argv, 'cwd': pane['cwd'],
                                'labels': repair['labels'], 'keep': True, 'no_parent': True,
                                'no_notify': True, 'wait': False})
            if (not self._same_labels(result.get('labels'), repair['labels'])
                    or type(result.get('address')) is not str or not layout._TERMINAL.fullmatch(result['address'])):
                raise NativeError('core created terminal ownership unavailable')
            repair['created'] = result['address']
            receipt['pending'] = None
            self._receipt(receipt)
            self._wait_created_core(repair['created'], pane, repair['labels'])
        if repairs:
            # Prove every created client before publishing its address.
            self._current_projection(document, self._terminals(), projected, receipt)
            replacements = {leaf: (r['terminal'], r['created']) for leaf, r in repairs.items()}
            updated = layout.rebind_app_document(document, replacements)
            receipt['pending'] = {'operation': 'doc.set', 'document': updated, 'version': version}
            self._receipt(receipt)
            self._current_effect_boundary(receipt)
            answer = self.core('doc.set', {'name': 'herdr-app', 'value': updated, 'version': version})
            if type(answer.get('version')) is not int or answer['version'] <= version:
                raise NativeError('core document CAS outcome uncertain')
            receipt.update(document=updated, doc_version=answer['version'])
            for key, leaf in receipt['bindings'].items():
                if leaf in repairs:
                    receipt['terminals'][key] = repairs[leaf]['created']
                    receipt['labels'][key] = repairs[leaf]['labels']
            receipt.update(pending=None, repairs={})
            self._receipt(receipt)
        self.verify('herdr-core', projected, receipt)
        self.store.write('manifest.json', {'schema_version': 2, 'runtime': 'herdr-core',
                         'plan': projected, 'receipt': receipt, 'txid': receipt['txid']})

    def _current_effect_boundary(self, receipt):
        document, version = self._document()
        if document != receipt['document'] or version != receipt['doc_version']:
            raise NativeError('core recovery document changed before mutation')

    def _verify_current(self, plan, receipt, document, version):
        self._binding_receipt(plan, receipt, receipt['txid'], 2)
        if receipt.get('pending') or receipt.get('repairs') or document != receipt['document']:
            raise NativeError('core current restored layout differs')
        projected, bindings, labels, repairs = self._current_projection(
            document, self._terminals(), plan, receipt)
        if (projected != plan or repairs
                or {k: b['leaf'] for k, b in bindings.items()} != receipt['bindings']
                or {k: b['terminal'] for k, b in bindings.items()} != receipt['terminals']
                or {k: labels[b['leaf']] for k, b in bindings.items()} != receipt['labels']):
            raise NativeError('core current restored bindings differ')
        receipt['doc_version'] = version

    def _restore_migration_current(self):
        """Explicit, idempotent core recovery. Never infer ownership from a shell."""
        manifest = self.store.read('manifest.json')
        if (type(manifest) is not dict or set(manifest) != {'schema_version', 'runtime', 'plan', 'receipt', 'txid'}
                or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1):
            raise NativeError('runtime manifest unavailable or unsupported')
        target = runtime(manifest['runtime'])
        if target != 'herdr-core' or self.selected() != target:
            raise NativeError('core recovery runtime not selected')
        self._binary(target)
        self._other_off(target)
        plan = checked_plan(manifest['plan'])
        txid = manifest['txid']
        receipt = self.store.read('receipt-' + txid + '.json') or manifest['receipt']
        receipt = layout._json_copy(receipt)
        if receipt.get('runtime') != target or receipt.get('txid') != txid:
            raise NativeError('core recovery receipt identity mismatch')
        self._db_sessions(plan)
        if not self.endpoint_present(target):
            # Core restart preserves existing programs. Start only the native
            # supervisor, then inspect; never treat restart as client absence.
            if receipt.get('pending') and receipt['pending'].get('operation') == 'server.start':
                raise NativeError('core start outcome remains uncertain')
            prior_pending = receipt.get('pending')
            receipt['pending'] = {'operation': 'server.start', 'previous': prior_pending}
            self._receipt(receipt)
            self.command(['herdr-core', 'server', 'start', '--json'])
            self._wait(lambda: self.endpoint_present(target))
            receipt['pending'] = prior_pending
            self._receipt(receipt)
        pending = receipt.get('pending')
        if pending and pending.get('operation') == 'server.start':
            self.core('server.status', {})
            receipt['pending'] = pending.get('previous')
            self._receipt(receipt)
            pending = receipt['pending']
        self._wait_core_spawns()
        if pending:
            operation = pending.get('operation')
            if operation == 'terminal.run':
                matches = [t for t in self._terminals()
                           if self._same_labels(t.get('labels'), pending['labels']) and t.get('state') != 'finished']
                if len(matches) != 1:
                    raise NativeError('uncertain terminal creation unresolved')
                pane = next(p for p in panes(plan) if p['key'] == pending['pane'])
                terminal = matches[0]
                if not self._same_labels(terminal.get('labels'), self._labels(txid, pane)):
                    raise NativeError('uncertain terminal ownership unresolved')
                identity, cwd = self._program(terminal)
                if cwd != pane['cwd'] or identity not in (None, pane['session_id']):
                    raise NativeError('uncertain terminal identity unresolved')
                pid = (terminal.get('foreground') or terminal)['pid']
                actual = self.process_argv(pid)
                if identity is None or actual and actual[0] in ('/bin/bash', 'bash', '-bash'):
                    self._shell_proof(terminal)
                else:
                    self._client_argv(pid, identity)
                receipt['terminals'][pane['key']] = matches[0]['address']
                receipt['pending'] = None
                self._receipt(receipt)
            elif operation == 'doc.set':
                current, version = self._document()
                if current != pending['document']:
                    raise NativeError('uncertain document mutation unresolved')
                receipt.update({'document': current, 'doc_version': version, 'pending': None})
                self._receipt(receipt)
            elif operation == 'terminal.kill':
                terminal = self._terminal(pending['terminal'])
                if terminal.get('state') != 'finished':
                    raise NativeError('uncertain owned shell stop unresolved')
                self._pids_absent_or_fail(pending['pids'])
                receipt['terminals'].pop(pending['pane'], None)
                receipt['pending'] = None
                self._receipt(receipt)
            else:
                raise NativeError('core pending mutation unsupported')
        current, version = self._document()
        if current != receipt['document']:
            raise NativeError('core recovery document has unexplained edits')
        receipt['doc_version'] = version
        for pane in panes(plan):
            address = receipt['terminals'].get(pane['key'])
            if address is None:
                continue
            terminal = self._terminal(address)
            if not self._same_labels(terminal.get('labels'), self._labels(txid, pane)):
                raise NativeError('core recovery terminal not owned')
            if terminal.get('state') == 'finished':
                if pane['session_id'] and self.scan({pane['session_id']}):
                    raise NativeError('session client still running')
                receipt['terminals'].pop(pane['key'])
                self._receipt(receipt)
                continue
            identity, cwd = self._program(terminal)
            if cwd != pane['cwd']:
                raise NativeError('core recovery directory mismatch')
            if identity is not None:
                # keep can retain original launch argv while the recovered live
                # program is a shell. Do not mistake persisted argv for liveness.
                pid = (terminal.get('foreground') or terminal)['pid']
                actual = self.process_argv(pid)
                if actual and actual[0] in ('/bin/bash', 'bash', '-bash'):
                    self._shell_proof(terminal)
                    identity = None
                else:
                    self._client_argv(pid, identity)
            if identity == pane['session_id']:
                if identity is not None:
                    found = self.scan({identity})
                    if len(found) != 1:
                        raise NativeError('session client coverage incomplete or duplicate')
                continue
            if identity is not None or pane['session_id'] is None:
                raise NativeError('core recovery foreign program')
            self._shell_proof(terminal)
            if self.scan({pane['session_id']}):
                raise NativeError('session client already running')
            pids = [terminal['pid']]
            if terminal.get('foreground'):
                pids.append(terminal['foreground']['pid'])
            proofs = self._pid_proofs(pids)
            receipt['pending'] = {'operation': 'terminal.kill', 'pane': pane['key'],
                                  'terminal': address, 'pids': proofs}
            self._receipt(receipt)
            # Durable intent publication is a scheduling/crash boundary. Recheck
            # actual ownership immediately before killing the recovered shell.
            observed, observed_version = self._document()
            if observed != receipt['document'] or observed_version != receipt['doc_version']:
                raise NativeError('core recovery document changed before shell stop')
            actual = self._terminal(address)
            if actual != terminal or self._pid_proofs(pids) != proofs:
                raise NativeError('core recovery process changed before shell stop')
            self._shell_proof(actual)
            self.core('terminal.kill', {'terminal': address})
            self._wait(lambda: self._terminal(address).get('state') == 'finished' and self._pids_absent(proofs))
            receipt['terminals'].pop(pane['key'])
            receipt['pending'] = None
            self._receipt(receipt)
        self._receipt(receipt)
        receipt = self.restore(target, plan, txid, receipt)
        self.verify(target, plan, receipt)
        manifest['receipt'] = receipt
        self.store.write('manifest.json', manifest)

    def _pids_absent_or_fail(self, proofs):
        if not self._pids_absent(proofs):
            raise NativeError('owned shell still running')
