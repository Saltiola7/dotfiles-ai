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

    @staticmethod
    def _checked_boot_id(value):
        if (type(value) is not str or not re.fullmatch(
                r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value)
                or uuid.UUID(value).int == 0):
            raise NativeError('native boot identity unavailable')
        return value

    def process_boot_id(self):
        """Bounded Linux boot evidence; tests replace this system-read seam."""
        try:
            fd = os.open(self.proc_root / 'sys/kernel/random/boot_id',
                         os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022:
                    raise NativeError('native boot identity unavailable')
                data = os.read(fd, 38)
                if os.read(fd, 1):
                    raise NativeError('native boot identity unavailable')
            finally:
                os.close(fd)
            if data.endswith(b'\n'):
                data = data[:-1]
            return self._checked_boot_id(data.decode('ascii'))
        except (OSError, UnicodeError, ValueError):
            raise NativeError('native boot identity unavailable') from None

    @staticmethod
    def _validate_pid_proofs(proofs, *, minimum=0, maximum=512):
        if (type(proofs) is not list or not minimum <= len(proofs) <= maximum
                or any(type(p) is not dict or set(p) not in ({'pid', 'start_ticks'}, {'pid', 'start_ticks', 'boot_id'})
                       or type(p['pid']) is not int or p['pid'] <= 1
                       or type(p['start_ticks']) is not int or p['start_ticks'] < 0 for p in proofs)):
            raise NativeError('native client PID proof invalid')
        for proof in proofs:
            if 'boot_id' in proof:
                Native._checked_boot_id(proof['boot_id'])
        if (len({p['pid'] for p in proofs}) != len(proofs)
                or len({p.get('boot_id') for p in proofs}) > 1):
            raise NativeError('native client PID proof invalid')

    def _pid_proofs(self, pids):
        boot_id = self._checked_boot_id(self.process_boot_id())
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
            result.append({'pid': pid, 'start_ticks': ticks, 'boot_id': boot_id})
        if self._checked_boot_id(self.process_boot_id()) != boot_id:
            raise NativeError('native boot identity changed')
        self._validate_pid_proofs(result)
        return result

    def _pids_absent(self, captured):
        self._validate_pid_proofs(captured)
        boot_id = self._checked_boot_id(self.process_boot_id())
        for item in captured:
            if 'boot_id' in item and item['boot_id'] != boot_id:
                continue
            directory = self.proc_root / str(item['pid'])
            try:
                info = directory.lstat()
                if not stat.S_ISDIR(info.st_mode) or processes.task_uid(directory) != os.getuid():
                    raise NativeError('native client exit ownership uncertain')
                state, ticks = processes.identity(directory, item['pid'])
                if state not in ('Z', 'X') and ticks == item['start_ticks']:
                    if self._checked_boot_id(self.process_boot_id()) != boot_id:
                        raise NativeError('native boot identity changed')
                    return False
            except (FileNotFoundError, ProcessLookupError):
                continue
        if self._checked_boot_id(self.process_boot_id()) != boot_id:
            raise NativeError('native boot identity changed')
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
        # Display labels belong to the app. Compare the complete ownership
        # namespace, including unknown keys, without altering private receipts.
        # Core 0.1.18 drops the legacy optional empty session label.
        if type(observed) is not dict or type(expected) is not dict:
            return False
        for labels in (observed, expected):
            if any(type(k) is not str or type(v) is not str for k, v in labels.items()):
                return False
            # Current-document adoption also records unowned app clients. An
            # ownership-labelled record, however, must have both required keys.
            if (any(k.startswith('remote-herdr-') for k in labels)
                    and any(not labels.get(k) for k in ('remote-herdr-owner', 'remote-herdr-pane'))):
                return False
        def canonical(labels):
            return {k: v for k, v in labels.items() if k.startswith('remote-herdr-')
                    and (k != 'remote-herdr-session' or v != '')}
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
            # A server.start wrapper may have just exposed a saved mutation.
            # Validate that intent's exact private form before reconciling it.
            self._binding_receipt(plan, receipt, manifest['txid'], manifest['schema_version'])
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
                expected = fields[pending['operation']]
                extended = ({'identity'}, {'identity', 'rebound'}, {'identity', 'rebound', 'retained_shell'}) if pending['operation'] == 'terminal.kill' else (
                    ({'leaf', 'replacement'}, {'leaf', 'replacement', 'retained_shell'})
                    if pending['operation'] == 'doc.set' else ())
                if set(pending) != expected and not any(set(pending) == expected | extra for extra in extended):
                    raise NativeError('current document mutation intent invalid')
                if 'identity' in pending:
                    self._validate_kill_identity(pending['identity'])
                if pending['operation'] == 'terminal.kill':
                    self._validate_pid_proofs(pending['pids'], minimum=1, maximum=2)
                if 'retained_shell' in pending and pending['retained_shell'] is not True:
                    raise NativeError('core repair guard replacement invalid')
                if 'rebound' in pending:
                    rebound = pending['rebound']
                    if (type(rebound) is not dict or set(rebound) != {'document', 'version', 'replacement'}
                            or type(rebound['version']) is not int or rebound['version'] <= receipt['doc_version']):
                        raise NativeError('core repair guard rebound invalid')
                    layout.project_app_document(rebound['document'], lambda leaf, address: None)
                    self._validate_replacement(rebound['replacement'])
                if 'replacement' in pending:
                    self._validate_replacement(pending['replacement'])
                    if (type(pending['leaf']) is not str or pending['leaf'] not in receipt.get('repairs', {})
                            or type(pending['version']) is not int or pending['version'] < 0):
                        raise NativeError('core repair guard binding changed')
                    layout.project_app_document(pending['document'], lambda leaf, address: None)
            repairs = receipt.get('repairs')
            if type(repairs) is not dict or set(repairs) - set(receipt['bindings'].values()):
                raise NativeError('current document repairs invalid')
            by_leaf = {receipt['bindings'][p['key']]: p for p in panes(plan)}
            for leaf, repair in repairs.items():
                base = {'terminal', 'pane', 'created', 'labels', 'stopped', 'pids'}
                if (type(repair) is not dict
                        or set(repair) not in (base, base | {'source'}, base | {'create_id'}, base | {'source', 'create_id'})
                        or ('create_id' in repair and (type(repair['create_id']) is not str
                            or not re.fullmatch(r'[0-9a-f]{32}', repair['create_id'])))
                        or type(repair['stopped']) is not bool or type(repair['pane']) is not dict
                        or set(repair['pane']) != {'key', 'cwd', 'session_id'}
                        or (repair['pane']['session_id'] is None and not repair['stopped'])
                        or any(repair['pane'][field] != by_leaf[leaf][field] for field in ('cwd', 'session_id'))
                        or repair['terminal'] != mapping[by_leaf[leaf]['key']]
                        or (repair['created'] is not None and (type(repair['created']) is not str
                            or not layout._TERMINAL.fullmatch(repair['created'])))
                        or repair['labels'] != self._repair_labels(txid, leaf, repair)):
                    raise NativeError('current document repair binding invalid')
                proofs = repair['pids']
                if proofs is not None:
                    self._validate_pid_proofs(proofs, minimum=1, maximum=2)
                if repair['stopped'] and proofs is None:
                    raise NativeError('current document repair stop proof unavailable')
                if repair['created'] is not None and not repair['stopped'] and 'source' not in repair:
                    raise NativeError('core repair guard source unavailable')
                if 'source' in repair:
                    self._validate_kill_identity(repair['source'])
                    if (proofs is None or repair['stopped']
                            or {p['pid'] for p in proofs} != {repair['source']['pid'], repair['source']['foreground_pid']}):
                        raise NativeError('core repair guard source invalid')

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
        live, proofs, actuals = {}, {}, {}
        source_guards = {}
        retained_shells = set()
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
                # A rebound address requires the durable CAS intent to be
                # reconciled first; never save old repair metadata over it.
                if address != repair['terminal']:
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
                labels[leaf] = repair['labels'] if address == repair.get('created') else previous[2]
                if repair.get('created'):
                    actual = lookup.get(repair['created'])
                    if actual is None or not self._same_labels(actual.get('labels'), repair['labels']):
                        raise NativeError('core created binding proof unavailable')
                    program = self._actual_core_program(actual)
                    if desired['session_id'] is not None and program == (None, desired['cwd']):
                        observed = self._document()
                        if observed[0] != document:
                            raise NativeError('core repair guard document-version changed')
                        repairs[leaf] = self._retained_source(receipt, leaf, lambda: self._same_document(observed))
                        self._replacement_proof(repair, retained_shell=True)
                        retained_shells.add(leaf)
                    elif program != (desired['session_id'], desired['cwd']):
                        raise NativeError('core created binding proof unavailable')
                    else:
                        observed = self._document()
                        if observed[0] != document:
                            raise NativeError('core repair guard document-version changed')
                        repairs[leaf] = self._retained_source(receipt, leaf, lambda: self._same_document(observed))
                elif not repair.get('stopped'):
                    actual = lookup[address]
                    if not self._same_labels(actual.get('labels'), previous[2]):
                        raise NativeError('core repair source ownership or program changed')
                    current_proofs = self._pid_proofs([actual['pid'], (actual.get('foreground') or actual)['pid']])
                    if 'source' in repair and current_proofs == repair['pids']:
                        observed = self._document()
                        if observed[0] != document:
                            raise NativeError('core repair guard document-version changed')
                        def guard_source(r=repair, key=previous[1]['key'], observation=observed):
                            intent = {'pane': key, 'terminal': r['terminal'], 'pids': r['pids'], 'identity': r['source']}
                            return self._old_shell_guard(receipt, intent, r, lambda: self._same_document(observation))
                        if guard_source() != 'live':
                            raise NativeError('core repair guard state changed')
                        source_guards[leaf] = guard_source
                    elif self._actual_core_program(actual) != (None, desired['cwd']):
                        raise NativeError('core repair source ownership or program changed')
                    live[leaf] = actual
                    actuals[leaf] = (None, desired['cwd'], self.process_argv((actual.get('foreground') or actual)['pid']))
                    proofs[leaf] = self._pid_proofs([actual['pid'], (actual.get('foreground') or actual)['pid']])
                    if 'source' in repair and repair['pids'] != proofs[leaf]:
                        old_boot = repair['pids'][0].get('boot_id')
                        changed_boot = old_boot is not None and old_boot != proofs[leaf][0]['boot_id']
                        if not changed_boot and {p['pid'] for p in repair['pids']} & {p['pid'] for p in proofs[leaf]}:
                            raise NativeError('core current process identity changed')
                        self._pids_absent_or_fail(repair['pids'])
                        # No create was admitted (pending effects reconcile
                        # before projection). Capture the rebooted owned shell
                        # as a new source/generation, never reuse the old PID.
                        repairs[leaf] = self._new_repair(receipt['txid'], leaf, address, desired)
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
                    repairs[leaf] = self._new_repair(receipt['txid'], leaf, address, desired,
                                                     stopped=True, pids=stopped[leaf][1])
                    labels[leaf] = layout._json_copy(previous[2])
                    return {'cwd': desired['cwd'], 'session_id': desired['session_id']}
                return None
            if previous and not self._same_labels(terminal.get('labels'), previous[2]):
                raise NativeError('core recovery terminal not owned')
            identity, cwd = self._actual_core_program(terminal, unknown=previous is None and not replaced)
            if identity is False:
                return None
            actuals[leaf] = (identity, cwd, self.process_argv((terminal.get('foreground') or terminal)['pid']))
            if previous:
                desired = previous[1]
                if cwd != desired['cwd']:
                    raise NativeError('core recovery directory mismatch')
                if identity is None and desired['session_id'] is not None:
                    repairs[leaf] = self._new_repair(receipt['txid'], leaf, address, desired)
                    identity = desired['session_id']
            labels[leaf] = layout._json_copy(terminal.get('labels', {}))
            live[leaf] = terminal
            proofs[leaf] = self._pid_proofs([terminal['pid'], (terminal.get('foreground') or terminal)['pid']])
            return {'cwd': cwd, 'session_id': identity}

        projected, bindings = layout.project_app_document(document, classify)
        present = {b['leaf'] for b in bindings.values()}
        for leaf in list(repairs):
            if leaf in present:
                continue
            repair = repairs[leaf]
            candidates = self._repair_candidates(terminals, repair)
            if repair['stopped'] and repair['created'] is None:
                self._pids_absent_or_fail(repair['pids'])
                candidates = [t for t in candidates if t.get('state') != 'finished']
            if (repair['created'] is not None or candidates
                    or self.scan({repair['pane']['session_id']} if repair['pane']['session_id'] else set())):
                raise NativeError('core closed repair ownership uncertain')
            del repairs[leaf]
        for repair in repairs.values():
            allowed = {repair['terminal'], repair.get('created')}
            if any(t['address'] not in allowed for t in self._repair_candidates(terminals, repair)):
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
            expected = 0 if repair and (not repair.get('created') or leaf in retained_shells) else 1
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
            current = self._terminal(terminal['address'])
            # Core reports titles/status/geometry asynchronously. Those are not
            # process identity. Foreground None -> the same PID's report is also
            # harmless; actual argv/cwd and PID/start-time remain authoritative.
            if (not self._same_labels(current.get('labels'), terminal.get('labels'))
                    or any(current.get(key) != terminal.get(key)
                           for key in ('address', 'state', 'pid', 'argv', 'cwd', 'keep'))
                    or (current.get('foreground') or current).get('pid')
                    != (terminal.get('foreground') or terminal).get('pid')):
                raise NativeError('core current inventory changed')
            if self._pid_proofs([p['pid'] for p in proofs[leaf]]) != proofs[leaf]:
                raise NativeError('core current process identity changed')
            if leaf in source_guards:
                # Full current source proof keeps actual cwd distinct from
                # launch cwd when the same PID's foreground report disappears.
                if source_guards[leaf]() != 'live':
                    raise NativeError('core current process identity changed')
            elif self._actual_core_program(current) != actuals[leaf][:2]:
                raise NativeError('core current process identity changed')
            if self.process_argv((current.get('foreground') or current)['pid']) != actuals[leaf][2]:
                raise NativeError('core current process identity changed')
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

    @staticmethod
    def _validate_kill_identity(identity):
        def argv(value):
            return (type(value) is list and 1 <= len(value) <= 256
                    and all(type(v) is str and len(v) <= 4096 and '\0' not in v for v in value))
        def directory(value):
            return type(value) is str and 0 < len(value) <= 4096 and '\0' not in value
        if (type(identity) is not dict
                or set(identity) != {'argv', 'cwd', 'launch', 'pid', 'foreground_pid'}
                or not argv(identity['argv']) or not directory(identity['cwd'])
                or any(type(identity[k]) is not int or identity[k] <= 1
                       for k in ('pid', 'foreground_pid'))
                or type(identity['launch']) is not dict
                or set(identity['launch']) != {'argv', 'cwd', 'keep'}
                or not argv(identity['launch']['argv'])
                or not directory(identity['launch']['cwd'])
                or (identity['launch']['keep'] is not None and type(identity['launch']['keep']) is not bool)):
            raise NativeError('core repair guard identity invalid')

    def _kill_identity(self, terminal):
        pid = (terminal.get('foreground') or terminal)['pid']
        identity = {'argv': self.process_argv(pid), 'cwd': self.process_cwd(pid),
                    'pid': terminal['pid'], 'foreground_pid': pid,
                    'launch': {k: terminal.get(k) for k in ('argv', 'cwd', 'keep')}}
        self._validate_kill_identity(identity)
        return identity

    def _kill_document_guard(self, receipt):
        document, version = self._document()
        if document != receipt['document']:
            raise NativeError('core repair guard layout changed')
        if version != receipt['doc_version']:
            raise NativeError('core repair guard document-version changed')

    def _current_kill_guard(self, receipt):
        """Re-observe only security facts, never terminal presentation or RPC ack."""
        self._kill_document_guard(receipt)
        pending = receipt['pending']
        key, leaf = pending['pane'], pending['leaf']
        repair = receipt['repairs'].get(leaf)
        if (repair is None or receipt['bindings'].get(key) != leaf
                or receipt['terminals'].get(key) != pending['terminal']
                or pending['terminal'] != repair['terminal'] or pending['pids'] != repair['pids']
                or not pending['pids'] or repair['created'] is not None):
            raise NativeError('core repair guard binding changed')
        references = {}
        def record(ref, address):
            references[ref] = address
            return None
        layout.project_app_document(receipt['document'], record)
        if references.get(leaf) != pending['terminal']:
            raise NativeError('core repair guard binding changed')
        return self._old_shell_guard(receipt, pending, repair, lambda: self._kill_document_guard(receipt))

    def _old_shell_guard(self, receipt, pending, repair, document_guard):
        """Shared process proof only; callers establish distinct binding authority."""
        key = pending['pane']
        terminal = self._terminal(pending['terminal'])
        self._validate_pid_proofs(pending['pids'], minimum=1, maximum=2)
        if terminal.get('state') == 'live':
            boot_id = self._checked_boot_id(self.process_boot_id())
            if any(p.get('boot_id') != boot_id for p in pending['pids']):
                raise NativeError('core repair guard boot identity changed')
        if terminal.get('address') != pending['terminal']:
            raise NativeError('core repair guard binding changed')
        if not self._same_labels(terminal.get('labels'), receipt['labels'][key]):
            raise NativeError('core repair guard labels changed')
        identity = pending.get('identity')
        if 'identity' in pending:
            self._validate_kill_identity(identity)
            if {identity['pid'], identity['foreground_pid']} != {p['pid'] for p in pending['pids']}:
                raise NativeError('core repair guard pid changed')
            if terminal.get('pid') != identity['pid']:
                raise NativeError('core repair guard pid changed')
            if terminal.get('argv') != identity['launch']['argv']:
                raise NativeError('core repair guard argv changed')
            if terminal.get('cwd') != identity['launch']['cwd']:
                raise NativeError('core repair guard directory changed')
            if terminal.get('keep') != identity['launch']['keep']:
                raise NativeError('core repair guard state changed')
        if terminal.get('state') == 'finished':
            try:
                self._pids_absent_or_fail(pending['pids'])
            except (NativeError, OSError, ValueError):
                raise NativeError('core repair guard exit unproven') from None
        elif terminal.get('state') == 'live':
            program = terminal.get('foreground') or terminal
            pids = [terminal.get('pid'), program.get('pid')]
            if (any(type(pid) is not int or pid <= 1 for pid in pids)
                    or set(pids) != {p['pid'] for p in pending['pids']}
                    or (identity is not None and (pids[0] != identity['pid']
                        or pids[1] != identity['foreground_pid']))):
                raise NativeError('core repair guard pid changed')
            try:
                proofs = self._pid_proofs(pids)
            except (NativeError, OSError, ValueError):
                raise NativeError('core repair guard start-time changed') from None
            if proofs != pending['pids']:
                raise NativeError('core repair guard start-time changed')
            argv = self.process_argv(pids[1])
            if (not argv or argv[0] not in ('/bin/bash', 'bash', '-bash')
                    or argv[1:] not in ([], ['-l'], ['--login'])
                    or (identity is not None and (argv != identity['argv']
                        or terminal.get('argv') != identity['launch']['argv']))):
                raise NativeError('core repair guard argv changed')
            cwd = self.process_cwd(pids[1])
            if (cwd != repair['pane']['cwd']
                    or (terminal.get('foreground') is not None and program.get('cwd') != cwd)
                    or (identity is not None and cwd != identity['cwd'])):
                raise NativeError('core repair guard directory changed')
            if self._pid_proofs(pids) != proofs:
                raise NativeError('core repair guard start-time changed')
        else:
            raise NativeError('core repair guard state changed')
        document_guard()
        if terminal['state'] == 'live':
            # The document RPC is another scheduling boundary. Recheck actual
            # process facts after it, without relying on cached foreground data.
            try:
                latest = self._pid_proofs(pids)
            except (NativeError, OSError, ValueError):
                raise NativeError('core repair guard start-time changed') from None
            if latest != proofs:
                raise NativeError('core repair guard start-time changed')
            if self.process_argv(pids[1]) != argv:
                raise NativeError('core repair guard argv changed')
            if self.process_cwd(pids[1]) != cwd:
                raise NativeError('core repair guard directory changed')
            if self._pid_proofs(pids) != latest:
                raise NativeError('core repair guard start-time changed')
        return terminal['state']

    @staticmethod
    def _validate_replacement(value):
        if type(value) is not dict or set(value) != {'identity', 'pids'}:
            raise NativeError('core repair guard replacement invalid')
        Native._validate_kill_identity(value['identity'])
        proofs = value['pids']
        Native._validate_pid_proofs(proofs, minimum=1, maximum=2)
        if {p['pid'] for p in proofs} != {value['identity']['pid'], value['identity']['foreground_pid']}:
            raise NativeError('core repair guard replacement invalid')

    def _repair_labels(self, txid, leaf, repair):
        labels = self._labels(txid, {'key': leaf, 'session_id': repair['pane']['session_id']})
        if 'create_id' in repair:
            labels['remote-herdr-repair'] = repair['create_id']
        return labels

    def _new_repair(self, txid, leaf, address, pane, *, stopped=False, pids=None):
        repair = {'terminal': address, 'pane': pane, 'created': None,
                  'stopped': stopped, 'pids': pids, 'create_id': uuid.uuid4().hex}
        repair['labels'] = self._repair_labels(txid, leaf, repair)
        return repair

    def _repair_candidates(self, terminals, repair):
        """Include finished and conflicting ownership records, not just matches.

        Finished prior generations are history, not an uncertain current create.
        Live related clients and finished current-generation records still refuse.
        Legacy repairs have no historical generation to infer and stay conservative.
        The original address has separate shell/exit proof, independent of labels.
        """
        expected = repair['labels']
        result = []
        for terminal in terminals:
            labels = terminal.get('labels')
            if type(labels) is not dict or any(type(k) is not str or type(v) is not str for k, v in labels.items()):
                raise NativeError('core repair guard labels changed')
            if terminal['address'] == repair['terminal']:
                continue
            same_pane = labels.get('remote-herdr-pane') == expected['remote-herdr-pane']
            related = (same_pane
                       or (terminal.get('state') != 'finished' and expected.get('remote-herdr-session')
                            and labels.get('remote-herdr-session') == expected['remote-herdr-session']))
            current = ('create_id' in repair and labels.get('remote-herdr-repair') == repair['create_id'])
            if (self._same_labels(labels, expected) or current
                    or (related and (terminal.get('state') != 'finished' or 'create_id' not in repair))):
                result.append(terminal)
        return result

    def _replacement_proof(self, repair, expected=None, *, retained_shell=False):
        matches = self._repair_candidates(self._terminals(), repair)
        if len(matches) != 1 or matches[0]['address'] != repair['created']:
            raise NativeError('core repair guard labels changed')
        terminal = matches[0]
        pane = repair['pane']
        if not self._same_labels(terminal.get('labels'), repair['labels']):
            raise NativeError('core repair guard labels changed')
        desired = None if retained_shell else pane['session_id']
        if self._actual_core_program(terminal) != (desired, pane['cwd']):
            raise NativeError('core repair guard argv changed')
        proof = {'identity': self._kill_identity(terminal),
                 'pids': self._pid_proofs([terminal['pid'], (terminal.get('foreground') or terminal)['pid']])}
        self._validate_replacement(proof)
        if expected is not None and proof != expected:
            raise NativeError('core repair guard replacement changed')
        found = self.scan({pane['session_id']} if pane['session_id'] else set())
        if (retained_shell and found) or (not retained_shell and pane['session_id']
                and (len(found) != 1 or found[0]['pid'] != proof['identity']['foreground_pid'])):
            raise NativeError('core repair guard session changed')
        return proof

    def _rebound_kill_guard(self, receipt):
        """R3 authority: replacement is bound/live, not R1 desired absence."""
        pending = receipt['pending']
        repair = receipt['repairs'][pending['leaf']]
        rebound = pending['rebound']
        expected = layout.rebind_app_document(receipt['document'],
            {pending['leaf']: (repair['terminal'], repair['created'])})
        if (rebound['document'] != expected or pending['identity'] != repair.get('source')
                or pending['pids'] != repair['pids'] or pending['terminal'] != repair['terminal']
                or receipt['bindings'].get(pending['pane']) != pending['leaf']):
            raise NativeError('core repair guard binding changed')
        def document_guard():
            if self._document() != (rebound['document'], rebound['version']):
                raise NativeError('core repair guard document-version changed')
        document_guard()
        retained = pending.get('retained_shell') is True
        self._replacement_proof(repair, rebound['replacement'], retained_shell=retained)
        state = self._old_shell_guard(receipt, pending, repair, document_guard)
        self._replacement_proof(repair, rebound['replacement'], retained_shell=retained)
        document_guard()
        if self._old_shell_guard(receipt, pending, repair, document_guard) != state:
            raise NativeError('core repair guard state changed')
        return state

    def _complete_rebound_kill(self, receipt):
        pending = receipt['pending']
        repair = receipt['repairs'][pending['leaf']]
        rebound = pending['rebound']
        if (pending.get('retained_shell') is not True and repair['pane']['session_id'] is not None
                and self._actual_core_program(self._terminal(repair['created'])) == (None, repair['pane']['cwd'])):
            expected = layout.rebind_app_document(receipt['document'],
                {pending['leaf']: (repair['terminal'], repair['created'])})
            if (rebound['document'] != expected or pending['identity'] != repair.get('source')
                    or pending['pids'] != repair['pids'] or pending['terminal'] != repair['terminal']
                    or receipt['bindings'].get(pending['pane']) != pending['leaf']):
                raise NativeError('core repair guard binding changed')
            self._same_document((rebound['document'], rebound['version']))
            self._publish_retained_shell_cas(receipt, pending['leaf'], prior=rebound['replacement'])
            self._accept_retained_shell_cas(receipt)
            return
        if self._rebound_kill_guard(receipt) == 'live':
            self.core('terminal.kill', {'terminal': pending['terminal']})
            self._wait(lambda: self._terminal(pending['terminal']).get('state') == 'finished'
                       and self._pids_absent(pending['pids']))
        self._rebound_kill_guard(receipt)
        self._finish_leaf_rebind(receipt, pending['leaf'], pending['rebound']['document'],
                                 pending['rebound']['version'])

    def _finish_leaf_rebind(self, receipt, leaf, document, version):
        repair = receipt['repairs'][leaf]
        key = next(k for k, value in receipt['bindings'].items() if value == leaf)
        receipt['terminals'][key] = repair['created']
        receipt['labels'][key] = repair['labels']
        receipt.update(document=document, doc_version=version, pending=None)
        del receipt['repairs'][leaf]
        self._receipt(receipt)

    def _accept_leaf_cas(self, receipt):
        pending = receipt['pending']
        if pending.get('retained_shell') is True:
            self._accept_retained_shell_cas(receipt)
            return
        leaf = pending['leaf']
        repair = receipt['repairs'][leaf]
        expected = layout.rebind_app_document(receipt['document'], {leaf: (repair['terminal'], repair['created'])})
        current, version = self._document()
        if (repair['pane']['session_id'] is not None
                and self._actual_core_program(self._terminal(repair['created'])) == (None, repair['pane']['cwd'])):
            if (pending['document'] != expected or pending['version'] != receipt['doc_version']
                    or not ((current, version) == (receipt['document'], pending['version'])
                            or (current == expected and version > pending['version']))):
                raise NativeError('uncertain document mutation unresolved')
            # The create succeeded, but its captured client exited. Preserve
            # the original CAS intent, then reclassify only its proven current
            # owned Bash under the same exact native pre/postimage facts.
            self._publish_retained_shell_cas(receipt, leaf, prior=pending['replacement'])
            self._accept_retained_shell_cas(receipt)
            return
        if (pending['document'] != expected or pending['version'] != receipt['doc_version']
                or current != expected or version <= pending['version']):
            raise NativeError('uncertain document mutation unresolved')
        self._replacement_proof(repair, pending['replacement'])
        if 'source' not in repair:
            if not repair['stopped']:
                raise NativeError('core repair guard source invalid')
            self._pids_absent_or_fail(repair['pids'])
            self._finish_leaf_rebind(receipt, leaf, current, version)
            return
        key = next(k for k, value in receipt['bindings'].items() if value == leaf)
        receipt['pending'] = {'operation': 'terminal.kill', 'pane': key, 'leaf': leaf,
                              'terminal': repair['terminal'], 'pids': repair['pids'],
                              'identity': repair['source'], 'rebound': {
                                  'document': current, 'version': version, 'replacement': pending['replacement']}}
        self._receipt(receipt)
        self._complete_rebound_kill(receipt)

    def _same_document(self, expected):
        if self._document() != expected:
            raise NativeError('core repair guard document-version changed')

    def _retained_source(self, receipt, leaf, document_guard):
        """Observe a distinct current source; no stale proof authorizes its kill.

        The caller backs up the original receipt and publishes the new source
        together with the shell-hop effect intent before any native mutation.
        """
        repair = layout._json_copy(receipt['repairs'][leaf])
        original = self._terminal(repair['terminal'])
        key = next(k for k, value in receipt['bindings'].items() if value == leaf)
        if repair['pids'] is None or not self._same_labels(original.get('labels'), receipt['labels'][key]):
            raise NativeError('core retained source exit unproven')
        if original.get('state') == 'finished':
            if 'source' in repair:
                pending = {'pane': key, 'terminal': repair['terminal'], 'pids': repair['pids'],
                           'identity': repair['source']}
                self._old_shell_guard(receipt, pending, repair, document_guard)
            else:
                self._pids_absent_or_fail(repair['pids'])
            repair['stopped'] = True
            repair.pop('source', None)
        elif original.get('state') == 'live':
            source = self._kill_identity(original)
            pids = self._pid_proofs([source['pid'], source['foreground_pid']])
            if repair.get('source') != source or repair['pids'] != pids:
                if self._actual_core_program(original) != (None, repair['pane']['cwd']):
                    raise NativeError('core repair guard argv changed')
                old_boot = repair['pids'][0].get('boot_id')
                changed_boot = old_boot is not None and old_boot != pids[0]['boot_id']
                if not changed_boot and {p['pid'] for p in pids} & {p['pid'] for p in repair['pids']}:
                    # Without cross-boot evidence, PID reuse/start-time drift
                    # is not authority to adopt a different process in place.
                    raise NativeError('core repair guard start-time changed')
                self._pids_absent_or_fail(repair['pids'])
                if 'source' in repair and source['launch'] != repair['source']['launch']:
                    raise NativeError('core repair guard source changed')
            repair.update(source=source, pids=pids, stopped=False)
            pending = {'pane': key, 'terminal': repair['terminal'], 'pids': pids, 'identity': source}
            self._old_shell_guard(receipt, pending, repair, document_guard)
        else:
            raise NativeError('core repair guard state changed')
        document_guard()
        return repair

    def _retained_shell_guard(self, receipt, leaf, expected=None):
        repair = receipt['repairs'][leaf]
        observed = self._document()
        current = self._retained_source(receipt, leaf, lambda: self._same_document(observed))
        if current != repair:
            raise NativeError('core repair guard source changed')
        return self._replacement_proof(repair, expected, retained_shell=True)

    def _publish_retained_shell_cas(self, receipt, leaf, *, prior=None):
        """Reconcile an existing create under exact CAS pre/postimage facts."""
        repair = receipt['repairs'][leaf]
        expected = layout.rebind_app_document(receipt['document'], {leaf: (repair['terminal'], repair['created'])})
        observed = self._document()
        if not (observed == (receipt['document'], receipt['doc_version'])
                or (prior is not None and observed[0] == expected and observed[1] > receipt['doc_version'])):
            raise NativeError('uncertain document mutation unresolved')
        proof = self._replacement_proof(repair, retained_shell=True)
        if prior is not None and proof != prior:
            self._pids_absent_or_fail(prior['pids'])
        source = self._retained_source(receipt, leaf, lambda: self._same_document(observed))
        self._replacement_proof(repair, proof, retained_shell=True)
        self._same_document(observed)
        receipt['adoption_backup'] = self._backup({'receipt': receipt})
        receipt['repairs'][leaf] = source
        receipt['pending'] = {'operation': 'doc.set', 'document': expected, 'version': receipt['doc_version'],
                              'leaf': leaf, 'replacement': proof, 'retained_shell': True}
        self._receipt(receipt)

    def _accept_retained_shell_cas(self, receipt):
        pending = receipt['pending']
        leaf = pending['leaf']
        repair = receipt['repairs'][leaf]
        expected = layout.rebind_app_document(receipt['document'], {leaf: (repair['terminal'], repair['created'])})
        if pending['document'] != expected or pending['version'] != receipt['doc_version']:
            raise NativeError('core pending document binding invalid')
        current, version = self._document()
        before = (current, version) == (receipt['document'], pending['version'])
        after = current == expected and version > pending['version']
        if not before and not after:
            raise NativeError('uncertain document mutation unresolved')
        proof = self._retained_shell_guard(receipt, leaf, pending['replacement'])
        if self._document() != (current, version):
            raise NativeError('core repair guard document-version changed')
        self._retained_shell_guard(receipt, leaf, proof)
        if before:
            # Exact native version plus preimage proves the CAS has not taken
            # effect. No terminal.run or kill is repeated by this reconciliation.
            self.core('doc.set', {'name': 'herdr-app', 'value': expected, 'version': version})
            current, version = self._document()
            if current != expected or version <= pending['version']:
                raise NativeError('uncertain document mutation unresolved')
            self._retained_shell_guard(receipt, leaf, proof)
            if self._document() != (current, version):
                raise NativeError('core repair guard document-version changed')
        if repair['stopped']:
            self._finish_leaf_rebind(receipt, leaf, current, version)
        else:
            key = next(k for k, value in receipt['bindings'].items() if value == leaf)
            receipt['pending'] = {'operation': 'terminal.kill', 'pane': key, 'leaf': leaf,
                                  'terminal': repair['terminal'], 'pids': repair['pids'],
                                  'identity': repair['source'], 'retained_shell': True,
                                  'rebound': {'document': current, 'version': version, 'replacement': proof}}
            self._receipt(receipt)
            self._complete_rebound_kill(receipt)

    def _bind_retained_shells(self, receipt, *, only_leaf=None):
        """Publish exact shell-hop intent before CAS; retain the old private proof."""
        for leaf, repair in list(receipt.get('repairs', {}).items()):
            if only_leaf is not None and leaf != only_leaf:
                continue
            if not repair['created'] or repair['pane']['session_id'] is None:
                continue
            terminal = self._terminal(repair['created'])
            if self._actual_core_program(terminal) != (None, repair['pane']['cwd']):
                continue
            self._current_effect_boundary(receipt)
            document, version = self._document()
            if (document, version) != (receipt['document'], receipt['doc_version']):
                raise NativeError('core repair guard document-version changed')
            # Only the owned original binding may be repaired. A user rebind or
            # closure is not authority to publish this unbound shell.
            updated = layout.rebind_app_document(document, {leaf: (repair['terminal'], repair['created'])})
            self._publish_retained_shell_cas(receipt, leaf)
            self._accept_retained_shell_cas(receipt)

    def _complete_current_kill(self, receipt):
        pending = receipt['pending']
        repair = receipt['repairs'][pending['leaf']]
        self._current_kill_guard(receipt)
        desired = repair['pane']['session_id']
        if self.scan({desired} if desired is not None else set()):
            raise NativeError('core repair guard session changed')
        # Inventory observation may itself race a terminal or document change.
        state = self._current_kill_guard(receipt)
        if state == 'live':
            self.core('terminal.kill', {'terminal': pending['terminal']})
            self._wait(lambda: self._terminal(pending['terminal']).get('state') == 'finished'
                       and self._pids_absent(pending['pids']))
        self._current_kill_guard(receipt)
        repair['stopped'] = True

    def _readmit_legacy_kill_source(self, receipt):
        """Retire boot-less kill *intent*, never assert its historical outcome.

        Matching legacy tokens are only an admission constraint. Current owned
        Bash is captured with fresh boot-bound proof and repaired replacement-
        first. The strict old kill guard remains unavailable to legacy proof.
        """
        pending = receipt['pending']
        if ('rebound' in pending or any('boot_id' in p for p in pending['pids'])
                or self._terminal(pending['terminal']).get('state') != 'live'):
            return False
        repair = receipt['repairs'][pending['leaf']]
        if repair['stopped']:
            return False
        terminal = self._terminal(pending['terminal'])
        pids = [terminal.get('pid'), (terminal.get('foreground') or terminal).get('pid')]
        if set(pids) != {p['pid'] for p in pending['pids']}:
            raise NativeError('core repair guard pid changed')
        proofs = self._pid_proofs(pids)
        if [{k: v for k, v in p.items() if k != 'boot_id'} for p in proofs] != pending['pids']:
            raise NativeError('core repair guard start-time changed')
        observed = layout._json_copy(receipt)
        observed['pending']['pids'] = proofs
        observed['repairs'][pending['leaf']]['pids'] = proofs
        if 'source' in repair:
            if 'identity' in pending and pending['identity'] != repair['source']:
                raise NativeError('core repair guard binding changed')
            observed['pending'].setdefault('identity', repair['source'])
        # This ephemeral current-proof view is observational only. In
        # particular it is never passed to a native kill or published as R1.
        self._current_kill_guard(observed)
        desired = {repair['pane']['session_id']} if repair['pane']['session_id'] else set()
        # A generation-less pre-create kill admits no run effect. Its finished
        # history is not a live creation; retain it and use a fresh generation.
        # Explicit current-generation records and every live candidate refuse.
        def creation_uncertain():
            return any(t.get('state') != 'finished' or 'create_id' in repair
                       for t in self._repair_candidates(self._terminals(), repair))
        if self.scan(desired) or creation_uncertain():
            raise NativeError('core repair guard session changed')
        self._db_sessions(receipt['plan'])
        fresh = self._new_repair(receipt['txid'], pending['leaf'], pending['terminal'], repair['pane'])
        fresh.update(pids=proofs, source=self._kill_identity(self._terminal(pending['terminal'])))
        if self.scan(desired) or creation_uncertain():
            raise NativeError('core repair guard session changed')
        self._current_kill_guard(observed)
        observed['pending']['identity'] = fresh['source']
        self._current_kill_guard(observed)
        receipt['adoption_backup'] = self._backup({'receipt': receipt})
        receipt['repairs'][pending['leaf']] = fresh
        receipt['pending'] = None
        self._receipt(receipt)
        return True

    def _reconcile_ready_source(self, receipt):
        """A kept exact client can outlive its original source shell process."""
        pending = receipt['pending']
        leaf = pending['leaf']
        repair = receipt['repairs'][leaf]
        expected = layout.rebind_app_document(receipt['document'], {leaf: (repair['terminal'], repair['created'])})
        observed = self._document()
        before = observed == (receipt['document'], receipt['doc_version'])
        if pending['operation'] == 'terminal.kill':
            rebound = pending['rebound']
            if (rebound['document'] != expected or pending['identity'] != repair.get('source')
                    or pending['pids'] != repair['pids'] or observed != (expected, rebound['version'])):
                raise NativeError('core repair guard binding changed')
            proof = rebound['replacement']
        else:
            if (pending['document'] != expected or pending['version'] != receipt['doc_version']
                    or not (before or (observed[0] == expected and observed[1] > pending['version']))):
                raise NativeError('uncertain document mutation unresolved')
            proof = pending['replacement']
        self._replacement_proof(repair, proof)
        source = self._retained_source(receipt, leaf, lambda: self._same_document(observed))
        if source == repair:
            return False
        self._replacement_proof(repair, proof)
        self._same_document(observed)
        receipt['adoption_backup'] = self._backup({'receipt': receipt})
        receipt['repairs'][leaf] = source
        if pending['operation'] == 'terminal.kill':
            if source['stopped']:
                self._finish_leaf_rebind(receipt, leaf, observed[0], observed[1])
                return True
            pending.update(identity=source['source'], pids=source['pids'])
            self._receipt(receipt)
            self._complete_rebound_kill(receipt)
        else:
            self._receipt(receipt)
            if before:
                key = next(k for k, value in receipt['bindings'].items() if value == leaf)
                self._source_before_rebind(receipt, key, leaf, source)
                self._replacement_proof(source, proof)
                self._source_before_rebind(receipt, key, leaf, source)
                self.core('doc.set', {'name': 'herdr-app', 'value': expected, 'version': observed[1]})
            self._accept_leaf_cas(receipt)
        return True

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
                         or (repair.get('stopped') is not True and 'source' not in repair)))):
                raise NativeError('core pending mutation binding invalid')
        if pending.get('retained_shell') is True:
            leaf = pending['leaf']
            repair = receipt['repairs'][leaf]
            expected = layout.rebind_app_document(receipt['document'],
                {leaf: (repair['terminal'], repair['created'])})
            if operation == 'terminal.kill':
                rebound = pending['rebound']
                if (rebound['document'] != expected or pending['identity'] != repair.get('source')
                        or pending['pids'] != repair['pids']):
                    raise NativeError('core repair guard binding changed')
                self._same_document((rebound['document'], rebound['version']))
                prior = rebound['replacement']
            else:
                if pending['document'] != expected or pending['version'] != receipt['doc_version']:
                    raise NativeError('core pending document binding invalid')
                prior = pending['replacement']
            self._publish_retained_shell_cas(receipt, leaf, prior=prior)
            self._accept_retained_shell_cas(receipt)
            return
        if ((operation == 'terminal.kill' and 'rebound' in pending)
                or (operation == 'doc.set' and 'leaf' in pending)):
            repair = receipt['repairs'][pending['leaf']]
            pane = repair['pane']
            if (pane['session_id'] is not None
                    and self._actual_core_program(self._terminal(repair['created'])) == (pane['session_id'], pane['cwd'])
                    and self._reconcile_ready_source(receipt)):
                return
        if operation == 'terminal.kill':
            if 'rebound' in pending:
                self._complete_rebound_kill(receipt)
                return
            if self._readmit_legacy_kill_source(receipt):
                return
            self._complete_current_kill(receipt)
        elif operation == 'terminal.run':
            document, version = self._document()
            terminals = self._terminals()
            repair = receipt['repairs'][pending['leaf']]
            matches = self._repair_candidates(terminals, repair)
            pane = repair['pane']
            references = {}
            def record_run(leaf, address):
                references[leaf] = address
                return None
            layout.project_app_document(document, record_run)
            if not matches and pending['leaf'] not in references:
                if (repair['created'] is not None
                        or any(self._same_labels(t.get('labels'), pending['labels']) for t in terminals)
                        or self.scan({pane['session_id']} if pane['session_id'] else set())
                        or self._closed_run_candidates(repair, pending['labels'])
                        or self.scan({pane['session_id']} if pane['session_id'] else set())
                        or self._document() != (document, version)):
                    raise NativeError('core closed repair ownership uncertain')
                # Keep the saved mapping coherent until projection removes the
                # closed leaf. No effect replay, no fabricated native address.
                receipt['pending'] = None
                self._receipt(receipt)
                return
            if references.get(pending['leaf']) != repair['terminal']:
                raise NativeError('core pending mutation binding invalid')
            if len(matches) != 1:
                raise NativeError('uncertain terminal creation unresolved')
            if matches[0].get('state') != 'live':
                raise NativeError('uncertain terminal creation unresolved')
            address = matches[0]['address']
            if repair['created'] not in (None, address):
                raise NativeError('uncertain created terminal identity changed')
            repair['created'] = address
            self._receipt(receipt)
            if (pane['session_id'] is not None
                    and self._actual_core_program(matches[0]) == (None, pane['cwd'])):
                self._current_effect_boundary(receipt)
                self._bind_retained_shells(receipt, only_leaf=pending['leaf'])
                return
            self._wait_created_core(address, pane, repair['labels'])
            self._replacement_proof(repair)
            if self._document() != (document, version):
                raise NativeError('core repair guard document-version changed')
            source = self._retained_source(receipt, pending['leaf'],
                lambda: self._same_document((document, version)))
            if source != repair:
                receipt['adoption_backup'] = self._backup({'receipt': receipt})
                receipt['repairs'][pending['leaf']] = source
                self._receipt(receipt)
        elif operation == 'doc.set':
            if 'leaf' in pending:
                self._accept_leaf_cas(receipt)
                return
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

    def _closed_run_candidates(self, repair, labels):
        # A second complete inventory is an observation boundary, not an atomic
        # absence claim. Ignore presentation/display churn, never ownership.
        terminals = self._terminals()
        return (self._repair_candidates(terminals, repair)
                or any(self._same_labels(t.get('labels'), labels) for t in terminals))

    def _continue_idle_core_stop(self, receipt, stop, backup, captured, active):
        """Finish only still-live *original* captured clients after a warm stop.

        Rebooted processes never qualify here: PID roles, start times, launch
        identity, actual program, ownership and raw document must all agree.
        """
        by_key = {p['key']: p for p in panes(receipt['plan'])}
        if active - set(receipt['terminals'].values()):
            raise NativeError('core controller stop ownership changed')
        def guard():
            self._same_document((backup['document'], backup['doc_version']))
            expected, remaining = [], []
            identities = {}
            for key, address in receipt['terminals'].items():
                old = captured[address]
                terminal = self._terminal(address)
                if (not self._same_labels(old.get('labels'), receipt['labels'][key])
                        or not self._same_labels(terminal.get('labels'), receipt['labels'][key])):
                    raise NativeError('core controller stop ownership changed')
                pids = {old['pid'], (old.get('foreground') or old)['pid']}
                proofs = [p for p in stop['pids'] if p['pid'] in pids]
                if terminal.get('state') == 'finished':
                    self._pids_absent_or_fail(proofs)
                    continue
                if (address not in active or terminal.get('state') != 'live'
                        or any(terminal.get(k) != old.get(k) for k in ('pid', 'argv', 'cwd', 'keep'))
                        or (terminal.get('foreground') or terminal).get('pid')
                        != (old.get('foreground') or old).get('pid')
                        or self._pid_proofs(pids) != proofs
                        or self._live_program(terminal) != (by_key[key]['session_id'], by_key[key]['cwd'])):
                    raise NativeError('core controller stop process proof unavailable')
                if by_key[key]['session_id'] is not None:
                    expected.append((by_key[key]['session_id'], (terminal.get('foreground') or terminal)['pid']))
                remaining.append((address, proofs))
                identities[address] = self._kill_identity(terminal)
            found = self.scan(sessions(receipt['plan']))
            if sorted((p['session_id'], p['pid']) for p in found) != sorted(expected):
                raise NativeError('core controller stop client inventory changed')
            self._same_document((backup['document'], backup['doc_version']))
            for address, proofs in remaining:
                identity = identities[address]
                if (self._pid_proofs([p['pid'] for p in proofs]) != proofs
                        or self.process_argv(identity['foreground_pid']) != identity['argv']
                        or self.process_cwd(identity['foreground_pid']) != identity['cwd']
                        or self._pid_proofs([p['pid'] for p in proofs]) != proofs):
                    raise NativeError('core controller stop process proof unavailable')
            return remaining
        remaining = guard()
        self._backup({'stop': stop})
        for address, proofs in remaining:
            if address not in stop['terminals']:
                stop['terminals'].append(address)
            stop['pending'] = {'operation': 'terminal.kill', 'terminal': address}
            self.store.write('source-stop.json', stop)
            if (address, proofs) not in guard():
                raise NativeError('core controller stop process proof unavailable')
            self.core('terminal.kill', {'terminal': address})
            self._wait(lambda: self._terminal(address).get('state') == 'finished' and self._pids_absent(proofs))
            stop['pending'] = None
            self.store.write('source-stop.json', stop)

    def _reconcile_idle_core_stop(self, receipt):
        """Observe interrupted ordinary stop after captured processes exited.

        Never replay an unproven stop or apply old PID proof to a rebooted shell.
        Only the exact saved document is admitted here; changed layouts remain
        uncertain. Completed records keep their existing projection semantics.
        """
        stop = self.store.read('source-stop.json')
        if (not stop or stop.get('runtime') != 'herdr-core'
                or stop.get('txid') != receipt['txid'] or stop.get('completed') is True):
            return
        if (set(stop) != {'runtime', 'backup', 'pending', 'txid', 'terminals', 'pids', 'completed'}
                or stop['completed'] is not False or type(stop['terminals']) is not list
                or any(type(a) is not str or not layout._TERMINAL.fullmatch(a) for a in stop['terminals'])
                or len(set(stop['terminals'])) != len(stop['terminals'])
                or type(stop['backup']) is not str or not re.fullmatch(r'backup-[0-9a-f]{32}\.json', stop['backup'])
                or type(stop['pids']) is not list):
            raise NativeError('core controller stop requires reconciliation')
        self._validate_pid_proofs(stop['pids'])
        pending = stop['pending']
        if ((pending is None and not stop['terminals']) or (pending is not None and pending != {'operation': 'server.stop'}
                and (type(pending) is not dict or set(pending) != {'operation', 'terminal'}
                     or pending['operation'] != 'terminal.kill' or pending['terminal'] not in stop['terminals']))):
            raise NativeError('core controller stop requires reconciliation')
        backup = self.store.read(stop['backup'])
        if (backup is None or set(backup) != {'document', 'doc_version', 'terminals'}
                or backup['document'] != receipt['document']
                or type(backup['doc_version']) is not int or backup['doc_version'] < 0
                or type(backup['terminals']) is not list
                or self._document() != (backup['document'], backup['doc_version'])):
            raise NativeError('core controller stop document changed')
        addresses = self._document_terminals(backup['document'])
        captured = {t['address']: t for t in backup['terminals']}
        active = {a for a in addresses if captured[a].get('state') == 'live'}
        expected_pids = {pid for a in active for pid in
                         (captured[a]['pid'], (captured[a].get('foreground') or captured[a])['pid'])}
        if (len(captured) != len(backup['terminals']) or set(stop['terminals']) - active
                or {p['pid'] for p in stop['pids']} != expected_pids):
            raise NativeError('core controller stop process proof unavailable')
        if not self._pids_absent(stop['pids']):
            self._continue_idle_core_stop(receipt, stop, backup, captured, active)
        self._pids_absent_or_fail(stop['pids'])
        if self.scan(sessions(receipt['plan'])):
            raise NativeError('core controller stop client exit unproven')
        programs = []
        by_key = {p['key']: p for p in panes(receipt['plan'])}
        for key, address in receipt['terminals'].items():
            terminal = self._terminal(address)
            if (not self._same_labels(captured[address].get('labels'), receipt['labels'][key])
                    or not self._same_labels(terminal.get('labels'), receipt['labels'][key])):
                raise NativeError('core controller stop ownership changed')
            if terminal.get('state') == 'live':
                if self._actual_core_program(terminal) != (None, by_key[key]['cwd']):
                    raise NativeError('core controller stop program changed')
                identity = self._kill_identity(terminal)
                proofs = self._pid_proofs([identity['pid'], identity['foreground_pid']])
                programs.append((address, key, identity, proofs))
            elif terminal.get('state') != 'finished':
                raise NativeError('core controller stop process proof unavailable')
            else:
                programs.append((address, key, None, None))
        # A published None checkpoint is real stop-writer output, not permission
        # to mark live captured clients stopped. Recheck every observed boundary.
        if self._document() != (backup['document'], backup['doc_version']):
            raise NativeError('core controller stop document changed')
        self._pids_absent_or_fail(stop['pids'])
        for address, key, identity, proofs in programs:
            terminal = self._terminal(address)
            if not self._same_labels(terminal.get('labels'), receipt['labels'][key]):
                raise NativeError('core controller stop ownership changed')
            if identity is None:
                if terminal.get('state') != 'finished':
                    raise NativeError('core controller stop process proof unavailable')
            elif (terminal.get('state') != 'live' or self._kill_identity(terminal) != identity
                    or self._pid_proofs([identity['pid'], identity['foreground_pid']]) != proofs):
                raise NativeError('core controller stop process proof unavailable')
        if self.scan(sessions(receipt['plan'])):
            raise NativeError('core controller stop client exit unproven')
        self._same_document((backup['document'], backup['doc_version']))
        self._backup({'stop': stop})
        stop.update(completed=True, pending=None)
        self.store.write('source-stop.json', stop)

    def _restore_document(self, manifest, plan, receipt):
        self._reconcile_idle_core_stop(receipt)
        document, version = self._document()
        if document is None:
            raise NativeError('current core document unavailable')
        projected, bindings, labels, repairs = self._current_projection(
            document, self._terminals(), plan, receipt)
        if any(leaf not in {b['leaf'] for b in bindings.values()} for leaf in repairs):
            raise NativeError('core repair leaf missing')
        if not receipt.get('current_document'):
            receipt['adoption_backup'] = self._backup({'manifest': manifest, 'receipt': receipt})
        elif receipt.get('repairs') != repairs:
            receipt['adoption_backup'] = self._backup({'receipt': receipt})
        receipt.update(current_document=True, plan=projected, document=document, doc_version=version,
                       terminals={k: b['terminal'] for k, b in bindings.items()},
                       bindings={k: b['leaf'] for k, b in bindings.items()},
                       labels={k: labels[b['leaf']] for k, b in bindings.items()}, repairs=repairs)
        self._receipt(receipt)
        prior_repairs = len(repairs)
        self._bind_retained_shells(receipt)
        if len(repairs) != prior_repairs:
            return self._restore_document(manifest, receipt['plan'], receipt)
        # Resolve already-created unbound clients before any later creation.
        ordered = sorted(receipt['bindings'].items(), key=lambda item: not bool(repairs.get(item[1], {}).get('created')))
        for key, leaf in ordered:
            repair = repairs.get(leaf)
            if repair is None:
                continue
            repair_sessions = ({repair['pane']['session_id']}
                               if repair['pane']['session_id'] is not None else set())
            terminal = self._terminal(repair['terminal'])
            if not repair.get('stopped') and 'source' not in repair:
                if (not self._same_labels(terminal.get('labels'), receipt['labels'][key])
                        or self._actual_core_program(terminal) != (None, repair['pane']['cwd'])):
                    raise NativeError('core repair source ownership or program changed')
                self._shell_proof(terminal)
                pids = [terminal['pid'], (terminal.get('foreground') or terminal)['pid']]
                repair['pids'] = self._pid_proofs(pids)
                repair['source'] = self._kill_identity(terminal)
                self._receipt(receipt)
            self._source_before_rebind(receipt, key, leaf, repair)
            if not repair.get('created'):
                self._current_effect_boundary(receipt)
                if (self.scan(repair_sessions)
                        or self._repair_candidates(self._terminals(), repair)):
                    raise NativeError('session client already running')
                receipt['pending'] = {'operation': 'terminal.run', 'pane': key, 'leaf': leaf,
                                      'labels': repair['labels']}
                self._receipt(receipt)
                self._source_before_rebind(receipt, key, leaf, repair)
                if (self.scan(repair_sessions)
                        or self._repair_candidates(self._terminals(), repair)):
                    raise NativeError('session client already running')
                self._current_effect_boundary(receipt)
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
                # Keep run intent through readiness; recovery observes, never replays.
                self._receipt(receipt)
                self._wait_created_core(repair['created'], pane, repair['labels'])
                receipt['pending'] = None
                self._receipt(receipt)
            replacement = self._replacement_proof(repair)
            self._source_before_rebind(receipt, key, leaf, repair)
            updated = layout.rebind_app_document(receipt['document'], {leaf: (repair['terminal'], repair['created'])})
            receipt['pending'] = {'operation': 'doc.set', 'document': updated, 'version': receipt['doc_version'],
                                  'leaf': leaf, 'replacement': replacement}
            self._receipt(receipt)
            self._source_before_rebind(receipt, key, leaf, repair)
            self._replacement_proof(repair, replacement)
            self._source_before_rebind(receipt, key, leaf, repair)
            answer = self.core('doc.set', {'name': 'herdr-app', 'value': updated, 'version': receipt['doc_version']})
            if type(answer.get('version')) is not int or answer['version'] <= receipt['doc_version']:
                raise NativeError('core document CAS outcome uncertain')
            self._accept_leaf_cas(receipt)
        self.verify('herdr-core', projected, receipt)
        self.store.write('manifest.json', {'schema_version': 2, 'runtime': 'herdr-core',
                         'plan': projected, 'receipt': receipt, 'txid': receipt['txid']})

    def _source_before_rebind(self, receipt, key, leaf, repair):
        self._current_effect_boundary(receipt)
        if repair['stopped']:
            self._pids_absent_or_fail(repair['pids'])
            if self._terminal(repair['terminal']).get('state') != 'finished':
                raise NativeError('core repair guard exit unproven')
            return
        pending = {'pane': key, 'leaf': leaf, 'terminal': repair['terminal'],
                   'pids': repair['pids'], 'identity': repair['source']}
        if self._old_shell_guard(receipt, pending, repair, lambda: self._current_effect_boundary(receipt)) != 'live':
            raise NativeError('core repair guard state changed')

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
                or any(not self._same_labels(labels[b['leaf']], receipt['labels'][k])
                       for k, b in bindings.items())):
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
