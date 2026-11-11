"""Source-only native adapter tests: no native commands or real procfs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'dot_local/share/dotfiles-ai/remote-herdr'
sys.path.insert(0, str(SOURCE))
import controller as runtime_controller
spec = importlib.util.spec_from_file_location('remote_herdr_native', SOURCE / 'native.py')
assert spec is not None and spec.loader is not None
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Memory:
    def __init__(self):
        self.values = {}

    def read(self, name):
        return copy.deepcopy(self.values.get(name))

    def write(self, name, value):
        self.values[name] = copy.deepcopy(value)


@pytest.fixture
def backend(tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    (home / '.local/bin').mkdir(parents=True)
    (home / '.config/dotfiles-ai').mkdir(parents=True)
    pins = {'schema_version': 1, 'tui_version': '0.9.5', 'core_version': '0.1.18'}
    for name, key in [('herdr', 'tui'), ('herdr-core', 'core')]:
        path = home / '.local/bin' / name
        path.write_bytes(b'fake reviewed bytes')
        path.chmod(0o755)
        pins[key + '_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (home / '.config/dotfiles-ai/herdr-runtime.json').write_text(json.dumps(pins))
    config = home / '.config/dotfiles-ai/chezmoi.toml'
    config.write_text('sourceDir = "' + str(home / 'source') + '"\n'
                      '[data.dotfiles_ai.herdr]\nruntime = "tui" # retain\n'
                      '[data.other]\nsecret = "private"\n')
    (home / 'source').mkdir()
    b = native.Native(home, Memory())
    b.test_boot_id = '00000001-0000-4000-8000-000000000001'
    b.process_boot_id = lambda: b.test_boot_id
    b.proc_root = tmp_path / 'proc'
    b.proc_root.mkdir()
    b.run_root = tmp_path / 'run'
    b.run_root.mkdir()
    synthetic_process(b, 20, ['/bin/bash', '-l'])
    b.calls = []
    b.command = lambda argv, timeout=30: b.calls.append(argv) or {}
    b.database_path = lambda: b.home / '.local/share/opencode/opencode.db'
    b.endpoint_present = lambda runtime: False
    synthetic_db(b)
    return b


def synthetic_process(backend, pid, argv, cwd='/work', ticks=10):
    directory = backend.proc_root / str(pid)
    directory.mkdir(exist_ok=True)
    fields = ['S'] + ['0'] * 18 + [str(ticks)] + ['0'] * 10
    (directory / 'stat').write_text(f'{pid} (synthetic) ' + ' '.join(fields))
    (directory / 'status').write_text('Uid:\t' + '\t'.join([str(native.os.getuid())] * 4) + '\n')
    (directory / 'cmdline').write_bytes('\0'.join(argv).encode() + b'\0')
    (directory / 'cwd').unlink(missing_ok=True)
    (directory / 'cwd').symlink_to(cwd)


def synthetic_db(backend):
    path = backend.home / '.local/share/opencode/opencode.db'
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT)')
        db.execute('INSERT INTO session VALUES (?, ?)', ('ses_abc', '/work'))


@pytest.mark.parametrize('newline', [b'', b'\n'])
def test_r4_boot_reader_uses_only_bounded_synthetic_proc_file(backend, newline):
    path = backend.proc_root / 'sys/kernel/random/boot_id'
    path.parent.mkdir(parents=True)
    path.write_bytes(backend.test_boot_id.encode('ascii') + newline)
    path.chmod(0o600)
    assert native.Native.process_boot_id(backend) == backend.test_boot_id


@pytest.mark.parametrize('data', [b'', b'PRIVATE_VALUE', b'\xff', b'0' * 1000,
    b'00000000-0000-0000-0000-000000000000',
    b'ABCDEF01-0000-4000-8000-000000000001',
    b'00000001-0000-4000-8000-000000000001\n\n',
    b'00000001-0000-4000-8000-000000000001 extra'])
def test_r4_boot_reader_invalid_synthetic_bytes_are_value_free(backend, data):
    path = backend.proc_root / 'sys/kernel/random/boot_id'
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    path.chmod(0o600)
    with pytest.raises(native.NativeError, match='^native boot identity unavailable$'):
        native.Native.process_boot_id(backend)


@pytest.mark.parametrize('kind', ['missing', 'symlink', 'directory', 'writable'])
def test_r4_boot_reader_refuses_uncertain_synthetic_file(backend, kind):
    path = backend.proc_root / 'sys/kernel/random/boot_id'
    path.parent.mkdir(parents=True)
    if kind == 'symlink':
        target = path.parent / 'synthetic-target'
        target.write_text(backend.test_boot_id)
        path.symlink_to(target)
    elif kind == 'directory':
        path.mkdir()
    elif kind == 'writable':
        path.write_text(backend.test_boot_id)
        path.chmod(0o666)
    with pytest.raises(native.NativeError, match='^native boot identity unavailable$'):
        native.Native.process_boot_id(backend)


def test_r4_boot_proofs_preserve_exact_legacy_form_without_inventing_boot(backend):
    proof = backend._pid_proofs([20])[0]
    assert proof == {'pid': 20, 'start_ticks': 10, 'boot_id': backend.test_boot_id}
    legacy = {'pid': 20, 'start_ticks': 10}
    backend._validate_pid_proofs([legacy])
    assert not backend._pids_absent([legacy])
    backend.test_boot_id = '00000002-0000-4000-8000-000000000001'
    assert backend._pids_absent([proof])
    assert not backend._pids_absent([legacy])
    synthetic_process(backend, 20, ['/foreign'], ticks=10)
    assert not backend._pids_absent([legacy])
    assert legacy == {'pid': 20, 'start_ticks': 10}


@pytest.mark.parametrize('bad', ['null', 'uppercase', 'extra', 'duplicate', 'mixed-form', 'mixed-boot', 'bool-start'])
def test_r4_pid_proof_extensions_are_exact_and_coherent(backend, bad):
    proofs = backend._pid_proofs([20])
    proof = proofs[0]
    if bad == 'null':
        proof['boot_id'] = None
    elif bad == 'uppercase':
        proof['boot_id'] = 'ABCDEF01-0000-4000-8000-000000000001'
    elif bad == 'extra':
        proof['extra'] = True
    elif bad == 'duplicate':
        proofs.append(copy.deepcopy(proof))
    elif bad in ('mixed-form', 'mixed-boot'):
        other = {'pid': 21, 'start_ticks': 10}
        if bad == 'mixed-boot':
            other['boot_id'] = '00000002-0000-4000-8000-000000000001'
        proofs.append(other)
    else:
        proof['start_ticks'] = True
    with pytest.raises(native.NativeError):
        backend._validate_pid_proofs(proofs)
    with pytest.raises(native.NativeError):
        backend._pids_absent(proofs)


@pytest.mark.parametrize('unavailable', [None, '', 'PRIVATE_VALUE', 'ABCDEF01-0000-4000-8000-000000000001'])
def test_r4_unavailable_current_boot_never_establishes_exit(backend, unavailable, monkeypatch):
    proofs = backend._pid_proofs([20])
    backend.test_boot_id = unavailable
    def forbidden_pid_probe(*args):
        raise AssertionError('PID evidence inspected before boot validation')
    monkeypatch.setattr(native.processes, 'identity', forbidden_pid_probe)
    with pytest.raises(native.NativeError, match='^native boot identity unavailable$'):
        backend._pid_proofs([20])
    with pytest.raises(native.NativeError, match='^native boot identity unavailable$'):
        backend._pids_absent(proofs)


def test_r4_missing_boot_read_never_establishes_exit(backend):
    proofs = backend._pid_proofs([20])
    backend.process_boot_id = lambda: native.Native.process_boot_id(backend)
    with pytest.raises(native.NativeError, match='^native boot identity unavailable$'):
        backend._pids_absent(proofs)


@pytest.mark.parametrize('operation', ['capture', 'exit'])
def test_r4_boot_must_remain_stable_across_observation(backend, operation):
    proofs = backend._pid_proofs([20])
    values = iter(['00000002-0000-4000-8000-000000000001',
                   '00000003-0000-4000-8000-000000000001'])
    backend.process_boot_id = lambda: next(values)
    with pytest.raises(native.NativeError, match='^native boot identity changed$'):
        if operation == 'capture':
            backend._pid_proofs([20])
        else:
            backend._pids_absent(proofs)


@pytest.mark.parametrize('legacy_present', [False, True])
def test_current_native_session_v2_store_is_authoritative(backend, legacy_present):
    path = backend.home / '.local/share/opencode/opencode.db'
    with sqlite3.connect(path) as db:
        if not legacy_present:
            db.execute('DROP TABLE session')
        db.execute('CREATE TABLE session_v2 (id TEXT PRIMARY KEY, directory TEXT)')
        db.execute('INSERT INTO session_v2 VALUES (?, ?)', ('ses_abc', '/work'))
    backend._db_sessions(plan())
    with sqlite3.connect(path) as db:
        db.execute('UPDATE session_v2 SET directory = ?', ('/foreign',))
    # A matching old row cannot override the actual native v2 session location.
    with pytest.raises(native.NativeError, match='identity or directory'):
        backend._db_sessions(plan())


@pytest.mark.parametrize('name', ['opencode.db', 'opencode-v2.db', 'opencode-beta-2.db'])
def test_native_database_path_uses_channel_aware_read_only_resolver(backend, name):
    calls = []
    backend.command = lambda argv, timeout=30: calls.append(argv) or str(backend.home / '.local/share/opencode' / name) + '\n'
    path = native.Native.database_path(backend)
    assert path.name == name
    assert calls == [['opencode-native', 'debug', 'paths', 'db']]


@pytest.mark.parametrize('value', ['/outside/opencode.db', ':memory:', '/home/other/opencode.db', 'PRIVATE\0VALUE'])
def test_native_database_path_refuses_relocated_or_invalid_locations(backend, value):
    backend.command = lambda argv, timeout=30: value
    with pytest.raises(native.NativeError):
        native.Native.database_path(backend)


def wrapper_argv(backend, identity='ses_abc', server='http://127.0.0.1:4096', auto=True):
    # executable_opencode.tmpl:71,116-121: exec target, prepend server,
    # retain exact session constructor, append auto under HERDR_ENV (57-59).
    return [str(backend.home / '.opencode/bin/opencode'), '--server', server,
            '--session', identity] + (['--auto'] if auto else [])


def plan(session='ses_abc'):
    return {'schema_version': 1, 'spaces': [{'name': 'Space', 'directory': '/work', 'tabs': [
        {'name': 'Tab', 'root': {'pane': 's0-t0-p0'}, 'panes': [
            {'key': 's0-t0-p0', 'cwd': '/work', 'session_id': session}]}]}]}


def test_selection_preserves_other_bytes_and_restricts_apply(backend):
    config = backend.config_path
    before = config.read_text()
    backend.select('herdr-core')
    assert config.read_text() == before.replace('runtime = "tui"', 'runtime = "herdr-core"')
    assert backend.selected() == 'herdr-core'
    assert backend.calls[-1][-4:] == ['apply', '--include', 'files', str(backend.home / '.config/herdr/config.toml')]
    assert [Path(argv[0]).name for argv in backend.calls] == ['chezmoi']


def test_inline_selection_refuses_without_overwrite(backend):
    backend.config_path.write_text('[data.dotfiles_ai]\nherdr = {runtime = "tui"}\n')
    with pytest.raises(native.NativeError):
        backend.select('herdr-core')
    assert not backend.calls


def test_pin_drift_never_executes(backend):
    (backend.home / '.local/bin/herdr-core').write_bytes(b'drift')
    with pytest.raises(native.NativeError, match='binary'):
        backend.preflight('herdr-core')
    assert not backend.calls


def test_absent_core_probe_never_autostarts(backend):
    backend.preflight('herdr-core')
    assert not backend.calls


def test_core_preserves_only_the_protocol_fixed_label(backend, monkeypatch):
    def refused(*args):
        raise native.protocol.CoreProtocolError('core response refused or invalid')
    monkeypatch.setattr(native.protocol, 'request', refused)
    with pytest.raises(native.NativeError, match='^core protocol: core response refused or invalid$'):
        backend.core('server.status', {})
    assert not backend.calls


def test_api_snapshot_is_not_disk_schema(backend):
    with pytest.raises(native.NativeError):
        backend._api_inventory({'version': 3, 'workspaces': []})


def test_core_capture_preserves_identity_and_refuses_foreign_program(backend):
    p = plan(None)
    doc = native.layout.to_app_document(p, {'s0-t0-p0': 't1'})
    terminals = [{'address': 't1', 'cwd': '/work', 'argv': ['/bin/bash', '-l'],
                  'state': 'live', 'pid': 20, 'foreground': None, 'labels': {}}]
    assert backend._from_core(doc, terminals) == p
    terminals[0]['foreground'] = {'pid': 21, 'argv': ['/usr/bin/vim'], 'cwd': '/work'}
    with pytest.raises(native.NativeError, match='program'):
        backend._from_core(doc, terminals)


def test_core_cas_conflict_retains_receipt_and_backup(backend):
    p = plan(None)
    backend.selected = lambda: 'herdr-core'
    backend.core = lambda method, params: (_ for _ in ()).throw(native.NativeError('core outcome uncertain'))
    receipt = {'txid': 'a', 'runtime': 'herdr-core', 'document': None, 'doc_version': 0,
               'terminals': {'s0-t0-p0': 't1'}, 'pending': None}
    backend._terminal = lambda address: {'address': address, 'state': 'live', 'pid': 20,
                                       'cwd': '/work', 'argv': ['/bin/bash', '-l'],
                                       'foreground': None, 'labels': backend._labels('a', p['spaces'][0]['tabs'][0]['panes'][0])}
    backend._other_off = lambda target: None
    backend._document = lambda: (None, 0)
    backend._terminals = lambda: [backend._terminal('t1')]
    with pytest.raises(native.NativeError):
        backend.restore('herdr-core', p, 'a', receipt)
    saved = backend.store.read('receipt-a.json')
    assert saved['pending']['operation'] == 'doc.set'
    assert saved['terminals'] == {'s0-t0-p0': 't1'}


def test_duplicate_session_prevents_run(backend):
    backend.selected = lambda: 'herdr-core'
    backend.scan = lambda sessions: [{'pid': 99, 'start_ticks': 1, 'session_id': 'ses_abc'}]
    backend._other_off = lambda target: None
    backend._document = lambda: (None, 0)
    backend._terminals = lambda: []
    calls = []
    backend.core = lambda method, params: calls.append(method) or {}
    receipt = {'txid': 'a', 'runtime': 'herdr-core', 'document': None, 'doc_version': 0,
               'terminals': {}, 'pending': None}
    with pytest.raises(native.NativeError, match='client'):
        backend.restore('herdr-core', plan(), 'a', receipt)
    assert 'terminal.run' not in calls


def test_uncertain_run_not_retried(backend):
    backend.selected = lambda: 'herdr-core'
    backend._other_off = lambda target: None
    backend._document = lambda: (None, 0)
    backend._terminals = lambda: []
    calls = []

    def core(method, params):
        calls.append(method)
        raise native.NativeError('core outcome uncertain')

    backend.core = core
    receipt = {'txid': 'a', 'runtime': 'herdr-core', 'document': None, 'doc_version': 0,
               'terminals': {}, 'pending': None}
    with pytest.raises(native.NativeError):
        backend.restore('herdr-core', plan(None), 'a', receipt)
    assert calls == ['terminal.run']
    assert backend.store.read('receipt-a.json')['pending']['operation'] == 'terminal.run'


class FakeCore:
    """Only synthetic process files and dict mutations; no native runtime."""
    def __init__(self, backend):
        self.backend = backend
        self.document = None
        self.version = 0
        self.terminals = {}
        self.calls = []
        self.active = True
        backend.core = self.rpc
        backend.selected = lambda: 'herdr-core'
        backend.endpoint_present = lambda target: target == 'herdr-core' and self.active
        backend.command = self.command
        backend.poll_seconds = 0

    def command(self, argv, timeout=30):
        self.calls.append(('command', list(argv)))
        if argv == ['herdr-core', 'server', 'stop', '--json']:
            self.active = False
        elif argv == ['herdr-core', 'server', 'start', '--json']:
            self.active = True
        else:
            raise AssertionError('unexpected fake command')
        return {}

    def restart(self, *, keep_processes=False, keep_addresses=(), reuse_identities=False, same_boot=False):
        """Keep native records/labels, but replace every live process with Bash.

        Only this fake's synthetic proc tree is touched. Finished history stays
        finished; no old process survives the simulated core/VM restart.
        """
        if keep_processes:
            self.active = True
            return
        identities = {a: self.backend._pid_proofs([t['pid']])[0] for a, t in self.terminals.items()
                      if t['state'] == 'live'} if reuse_identities else {}
        retained_pids = {str(pid) for address in keep_addresses
                         for pid in (self.terminals[address]['pid'],
                                     (self.terminals[address].get('foreground') or self.terminals[address])['pid'])}
        for directory in self.backend.proc_root.iterdir():
            if directory.is_dir() and directory.name not in retained_pids:
                for entry in directory.iterdir():
                    entry.unlink()
                directory.rmdir()
        generation = getattr(self, 'restart_generation', 0) + 1
        self.restart_generation = generation
        if not keep_addresses and not same_boot:
            self.backend.test_boot_id = f'{generation + 1:08x}-0000-4000-8000-000000000001'
        for index, terminal in enumerate(self.terminals.values()):
            if terminal['state'] != 'live' or terminal['address'] in keep_addresses:
                continue
            pid = 10000 * generation + index + 100
            ticks = 100 + generation
            if reuse_identities:
                pid, ticks = identities[terminal['address']]['pid'], identities[terminal['address']]['start_ticks']
            synthetic_process(self.backend, pid, ['/bin/bash', '-l'], terminal['cwd'], ticks=ticks)
            terminal.update(pid=pid, foreground=None)
        self.active = True

    def rpc(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'server.status':
            return {}
        if method == 'doc.get':
            return {'value': copy.deepcopy(self.document), 'version': self.version}
        if method == 'doc.set':
            if params['version'] != self.version:
                raise native.NativeError('core conflict')
            self.document = copy.deepcopy(params['value'])
            self.version += 1
            return {'version': self.version}
        if method == 'terminal.list':
            return {'terminals': copy.deepcopy(list(self.terminals.values())), 'machines': [], 'hidden_finished': 0}
        if method == 'terminal.get':
            return copy.deepcopy(self.terminals[params['terminal']])
        if method == 'terminal.run':
            number = len(self.terminals) + 1
            address, pid = f't{number}', 30 + number
            live_argv = (wrapper_argv(self.backend, params['argv'][2])
                         if params['argv'][0].endswith('/opencode') else params['argv'])
            synthetic_process(self.backend, pid, live_argv, params['cwd'])
            terminal = {'address': address, 'pid': pid, 'state': 'live', 'foreground': None,
                         'argv': list(params['argv']), 'cwd': params['cwd'],
                         # Core 0.1.18 removes empty label values on creation.
                         'labels': {k: v for k, v in params['labels'].items() if v != ''}}
            self.terminals[address] = terminal
            return copy.deepcopy(terminal)
        if method == 'terminal.kill':
            terminal = self.terminals[params['terminal']]
            directory = self.backend.proc_root / str(terminal['pid'])
            for name in ('stat', 'cmdline', 'cwd', 'status'):
                (directory / name).unlink()
            directory.rmdir()
            terminal['state'] = 'finished'
            return copy.deepcopy(terminal)
        raise AssertionError('unexpected fake RPC')


def manifest_for(backend, core, p=None):
    p = p or plan()
    receipt = backend.prepare('herdr-core', p, 'testtx')
    receipt = backend.restore('herdr-core', p, 'testtx', receipt)
    backend.verify('herdr-core', p, receipt)
    manifest = {'schema_version': 1, 'runtime': 'herdr-core', 'plan': p,
                'receipt': receipt, 'txid': 'testtx'}
    backend.store.write('manifest.json', manifest)
    return manifest


def test_current_document_adopts_later_client_and_preserves_closed_raw_view(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    assert core.document is not None
    core.rpc('terminal.kill', {'terminal': 't1'})
    with sqlite3.connect(backend.database_path()) as db:
        db.execute('INSERT INTO session VALUES (?, ?)', ('ses_later', '/work'))
    later = core.rpc('terminal.run', {'argv': [str(backend.home / '.local/bin/opencode'), '--session', 'ses_later'],
                                    'cwd': '/work', 'labels': {}})
    tab = core.document['spaces'][0]['tabs'][0]
    old = tab['root']
    tab['root'] = {'id': 'split-new', 'type': 'row', 'opaque': [None], 'children': [
        old, {'id': 'later-leaf', 'type': 'block', 'content': {'terminal': later['address']}, 'size': {'weight': 2}}]}
    core.document['spaces'][0]['name'] = 'Renamed by user'
    core.document['metadata'] = {'preserve': True}
    core.version += 1
    before = copy.deepcopy(core.document)
    calls = len(core.calls)
    backend.restore_current()
    saved = backend.store.read('manifest.json')
    assert saved['schema_version'] == 2
    assert native.sessions(saved['plan']) == {'ses_later'}
    assert saved['receipt']['labels'] == {'s0-t0-p0': {}}
    assert core.document == before
    backend.restore_current()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set', 'command') for m, _ in core.calls[calls:])


def test_current_core_without_manifest_or_endpoint_is_quiet(backend):
    backend.selected = lambda: 'herdr-core'
    backend.restore_current()
    assert not backend.calls and backend.store.read('manifest.json') is None


def test_current_adoption_crash_before_manifest_recovers_durable_plan(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    assert core.document is not None
    core.document['spaces'][0]['tabs'][0]['name'] = 'Edited'
    core.version += 1
    write = backend.store.write
    def crash(name, value):
        if name == 'manifest.json' and value.get('schema_version') == 2:
            raise ValueError('synthetic crash')
        write(name, value)
    backend.store.write = crash
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.store.write = write
    before = len(core.calls)
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan']['spaces'][0]['tabs'][0]['name'] == 'Edited'
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('operation', ['terminal.kill', 'terminal.run', 'doc.set'])
def test_current_document_unknown_effect_reconciles_without_replaying(backend, operation):
    core = FakeCore(backend)
    manifest_for(backend, core)
    assert core.document is not None
    core.document['opaque'] = {'keep': True}
    core.version += 1
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    original = core.rpc
    def uncertain(method, params):
        result = original(method, params)
        if method == operation:
            raise native.NativeError('synthetic uncertain outcome')
        return result
    backend.core = uncertain
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core = original
    backend.restore_current()
    backend.restore_current()
    assert core.document['opaque'] == {'keep': True}
    assert sum(m == 'terminal.run' for m, _ in core.calls) == 2
    assert sum(m == 'terminal.kill' for m, _ in core.calls) == 1
    assert sum(m == 'doc.set' for m, _ in core.calls) == 2


def test_current_baseline_capture_accepts_user_metadata_without_killing_unknown_view(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    assert core.document is not None
    core.document['spaces'][0]['tabs'][0]['root']['size'] = {'weight': 1, 'default': None}
    core.document['opaque'] = 'keep'
    backend.restore_current()
    assert backend.capture('herdr-core')['plan'] == plan()


def test_current_capture_keeps_unrepresented_idle_shell_records(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'labels': {}})
    backend.restore_current()
    before = len(core.calls)
    assert backend.capture('herdr-core')['plan'] == plan()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('metadata', ['title', 'status', 'size', 'foreground-report'])
def test_current_inventory_proof_ignores_presentation_updates(backend, metadata):
    core = FakeCore(backend)
    manifest_for(backend, core)
    original = core.rpc
    def updating(method, params):
        result = original(method, params)
        if method == 'terminal.get':
            if metadata == 'title':
                result['title'] = 'Updated title'
            elif metadata == 'status':
                result.update(status={'state': 'idle'}, status_ms=42, turn=3, reported=True)
            elif metadata == 'size':
                result.update(cols=120, rows=40)
            else:
                result['foreground'] = {'pid': result['pid'], 'name': 'native',
                                        'argv': wrapper_argv(backend, 'ses_abc'), 'cwd': '/work'}
        return result
    backend.core = updating
    before = len(core.calls)
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan'] == plan()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('change', ['labels', 'pid', 'state', 'stored-argv', 'actual-argv',
                                    'cwd', 'start-ticks', 'foreground-pid', 'same-session-argv'])
def test_current_inventory_still_refuses_ownership_and_process_changes(backend, change):
    core = FakeCore(backend)
    manifest_for(backend, core)
    original = core.rpc
    def changed(method, params):
        result = original(method, params)
        if method == 'terminal.get':
            if change == 'labels':
                result['labels'] = {'foreign': 'owner'}
            elif change == 'pid':
                result['pid'] += 100
            elif change == 'state':
                result['state'] = 'finished'
            elif change == 'stored-argv':
                result['argv'] = ['/usr/bin/vim']
            elif change == 'actual-argv':
                synthetic_process(backend, result['pid'], wrapper_argv(backend, 'ses_other'))
            elif change == 'same-session-argv':
                synthetic_process(backend, result['pid'], wrapper_argv(backend, 'ses_abc', auto=False))
            elif change == 'cwd':
                synthetic_process(backend, result['pid'], wrapper_argv(backend, 'ses_abc'), cwd='/elsewhere')
            elif change == 'start-ticks':
                synthetic_process(backend, result['pid'], wrapper_argv(backend, 'ses_abc'), ticks=999)
            else:
                result['foreground'] = {'pid': 99, 'cwd': '/work', 'argv': wrapper_argv(backend, 'ses_abc')}
        return result
    backend.core = changed
    before = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('identity', ['ses_abc', None])
def test_current_controller_stopped_clients_are_not_user_closed_views(backend, identity):
    core = FakeCore(backend)
    manifest_for(backend, core, plan(identity))
    backend.restore_current()
    captured = backend.capture('herdr-core')
    backend.stop('herdr-core', captured)
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan'] == plan(identity)
    addresses = set(core.terminals)
    backend.restore_current()
    assert set(core.terminals) == addresses


@pytest.mark.parametrize('change', ['unfinished', 'missing-backup', 'changed-labels'])
def test_current_controller_stop_revival_requires_durable_proof(backend, change):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    backend.stop('herdr-core', backend.capture('herdr-core'))
    stop = backend.store.read('source-stop.json')
    if change == 'unfinished':
        stop['completed'] = False
        # R4 can observationally reconcile a genuine published checkpoint only
        # after *all* captured identities exited. Keep this negative unfinished
        # in fact, not merely by flipping a completed record's boolean.
        proof = stop['pids'][0]
        synthetic_process(backend, proof['pid'], wrapper_argv(backend), ticks=proof['start_ticks'])
    elif change == 'missing-backup':
        stop['backup'] = 'backup-unavailable.json'
    else:
        core.terminals['t1']['labels'] = {'foreign': 'owner'}
    backend.store.write('source-stop.json', stop)
    before = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


def test_current_unrelated_controller_stop_does_not_revive_user_finished_terminal(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    backend.stop('herdr-core', backend.capture('herdr-core'))
    stop = backend.store.read('source-stop.json')
    stop['txid'] = 'different-transaction'
    backend.store.write('source-stop.json', stop)
    before = len(core.calls)
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan']['spaces'] == []
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('identity', ['ses_abc', None])
@pytest.mark.parametrize('interruption', ['receipt', 'terminal.run'])
def test_controller_stopped_multi_pane_repairs_recover_durable_receipt(backend, identity, interruption):
    core = FakeCore(backend)
    original_plan = plan(identity)
    for index in (1, 2):
        extra = copy.deepcopy(original_plan['spaces'][0]['tabs'][0])
        key = f's0-t{index}-p0'
        extra['name'] = 'Extra ' + str(index)
        extra['root'] = {'pane': key}
        extra['panes'][0]['key'] = key
        extra['panes'][0]['session_id'] = 'ses_extra' + str(index)
        original_plan['spaces'][0]['tabs'].append(extra)
        with sqlite3.connect(backend.database_path()) as db:
            db.execute('INSERT INTO session VALUES (?, ?)', ('ses_extra' + str(index), '/work'))
    manifest_for(backend, core, original_plan)
    backend.restore_current()
    captured = backend.capture('herdr-core')
    assert len(captured['pids']) > 2
    backend.stop('herdr-core', captured)
    write = backend.store.write
    rpc = core.rpc
    failed = False
    def fail_write(name, value):
        nonlocal failed
        write(name, value)
        if interruption == 'receipt' and not failed and name == 'receipt-testtx.json' and value.get('repairs'):
            failed = True
            raise native.NativeError('synthetic crash after repair publication')
    def fail_rpc(method, params):
        nonlocal failed
        result = rpc(method, params)
        if interruption == 'terminal.run' and not failed and method == 'terminal.run':
            failed = True
            raise native.NativeError('synthetic lost stopped-client create reply')
        return result
    backend.store.write = fail_write
    backend.core = fail_rpc
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert failed
    backend.store.write = write
    backend.core = rpc
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan'] == original_plan
    assert len(core.terminals) == 6


@pytest.mark.parametrize('replace_finished_address', [False, True])
def test_current_owned_shell_can_adopt_a_later_exact_client(backend, replace_finished_address):
    core = FakeCore(backend)
    manifest_for(backend, core, plan(None))
    assert core.document is not None
    with sqlite3.connect(backend.database_path()) as db:
        db.execute('INSERT INTO session VALUES (?, ?)', ('ses_later', '/work'))
    if replace_finished_address:
        core.rpc('terminal.kill', {'terminal': 't1'})
        later = core.rpc('terminal.run', {'argv': [str(backend.home / '.local/bin/opencode'),
                        '--session', 'ses_later'], 'cwd': '/work', 'labels': {}})
        core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] = later['address']
        core.version += 1
    else:
        synthetic_process(backend, core.terminals['t1']['pid'], wrapper_argv(backend, 'ses_later'))
    before = len(core.calls)
    backend.restore_current()
    assert native.sessions(backend.store.read('manifest.json')['plan']) == {'ses_later'}
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


def test_current_repair_waits_for_observed_created_client_readiness(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    original = core.rpc
    observations = 0
    def delayed(method, params):
        nonlocal observations
        if method == 'terminal.get' and params['terminal'] == 't2':
            observations += 1
            if observations >= 2:
                core.terminals['t2']['pid'] = 32
        result = original(method, params)
        if method == 'terminal.run':
            core.terminals['t2']['pid'] = None
            result['pid'] = None
        return result
    backend.core = delayed
    def wait(check, *, seconds=None):
        for _ in range(4):
            if check():
                return
        raise native.NativeError('native readiness or stop proof unavailable')
    backend._wait = wait
    backend.restore_current()
    assert observations >= 2
    assert backend.store.read('manifest.json')['receipt']['terminals'] == {'s0-t0-p0': 't2'}
    assert sum(method == 'terminal.run' for method, _ in core.calls) == 2


def test_current_uncertain_cas_accepts_later_unrelated_desktop_serialization(backend):
    core = r1_shell(backend)
    original = core.rpc
    def uncertain(method, params):
        result = original(method, params)
        if method == 'doc.set':
            assert core.document is not None
            core.document['desktop-metadata'] = {'preserve': True}
            core.document['spaces'][0]['tabs'][0]['name'] = 'User rename after CAS'
            core.version += 1
            raise native.NativeError('synthetic lost CAS reply')
        return result
    backend.core = uncertain
    with pytest.raises(native.NativeError):
        backend.restore_current()
    # Retained R1/R2 batch-CAS intent: old shell was already proven stopped.
    receipt = backend.store.read('receipt-testtx.json')
    receipt['pending'].pop('leaf')
    receipt['pending'].pop('replacement')
    backend.store.write('receipt-testtx.json', receipt)
    backend.core = original
    before = len(core.calls)
    backend.restore_current()
    saved = backend.store.read('manifest.json')
    assert saved['plan']['spaces'][0]['tabs'][0]['name'] == 'User rename after CAS'
    assert core.document is not None
    assert core.document['desktop-metadata'] == {'preserve': True}
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


def test_uncertain_current_create_persists_observed_address_before_readiness_wait(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    original = core.rpc
    def uncertain(method, params):
        result = original(method, params)
        if method == 'terminal.run':
            raise native.NativeError('synthetic lost create reply')
        return result
    backend.core = uncertain
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core = original
    wait = backend._wait
    waits = 0
    def timeout(check, *, seconds=None):
        nonlocal waits
        waits += 1
        if waits == 1:
            assert check()  # Initial read-only kept-spawn observation is ready.
            return
        raise native.NativeError('native readiness or stop proof unavailable')
    backend._wait = timeout
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['operation'] == 'terminal.run'
    assert saved['repairs']['s0-t0-p0']['created'] == 't2'
    backend._wait = wait
    backend.restore_current()
    assert sum(m == 'terminal.run' for m, _ in core.calls) == 2


@pytest.mark.parametrize('returned_version', [None, 'unsupported', True, 0])
def test_current_cas_bad_acknowledgement_retains_reconcilable_intent(backend, returned_version):
    core = FakeCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    original = core.rpc
    def bad_reply(method, params):
        result = original(method, params)
        return {'version': returned_version} if method == 'doc.set' else result
    backend.core = bad_reply
    with pytest.raises(native.NativeError):
        backend.restore_current()
    receipt = backend.store.read('receipt-testtx.json')
    assert receipt['pending']['operation'] == 'doc.set'
    backend.core = original
    before = len(core.calls)
    backend.restore_current()
    assert backend.store.read('manifest.json')['receipt']['pending'] is None
    # R3 has not retired the old shell until the lost CAS result is proven.
    assert [m for m, _ in core.calls[before:] if m in ('terminal.run', 'terminal.kill', 'doc.set')] == ['terminal.kill']


def test_retained_published_64_pending_switch_adopts_three_without_resurrecting_four(backend):
    core = FakeCore(backend)
    leaves = [{'key': f's0-t0-p{i}', 'cwd': '/work',
               'session_id': None if i < 10 else f'ses_retained{i}'} for i in range(64)]
    def tree(items, native_tree=False):
        if len(items) == 1:
            return items[0] if native_tree else {'pane': items[0]['key']}
        half = len(items) // 2
        children = [tree(items[:half], native_tree), tree(items[half:], native_tree)]
        if native_tree:
            return {'id': 'branch-' + str(len(items)) + '-' + items[0]['id'], 'type': 'row', 'children': children}
        return {'axis': 'row', 'ratio': 0.5, 'children': children}
    value = {'schema_version': 1, 'spaces': [{'name': 'Original', 'directory': '/work', 'tabs': [
        {'name': 'Original tab', 'root': tree(leaves), 'panes': leaves}]}]}
    with sqlite3.connect(backend.database_path()) as db:
        db.executemany('INSERT INTO session VALUES (?, ?)',
                       [(p['session_id'], '/work') for p in leaves if p['session_id']])
        db.executemany('INSERT INTO session VALUES (?, ?)', [(f'ses_new{i}', '/work') for i in range(3)])
    manifest = manifest_for(backend, core, value)
    assert core.document is not None
    for address in ('t1', 't2', 't3', 't11'):
        core.rpc('terminal.kill', {'terminal': address})
    nodes = []
    def collect(node):
        if node['type'] == 'block':
            if node['content']['terminal'] not in ('t1', 't2', 't3', 't11'):
                nodes.append(copy.deepcopy(node))
        else:
            for child in node['children']:
                collect(child)
    collect(core.document['spaces'][0]['tabs'][0]['root'])
    for i in range(3):
        created = core.rpc('terminal.run', {'argv': [str(backend.home / '.local/bin/opencode'), '--session', f'ses_new{i}'],
                                           'cwd': '/work', 'labels': {}})
        nodes.insert(0, {'id': f'user-leaf-{i}', 'type': 'block', 'content': {'terminal': created['address']}})
    core.document['spaces'][0]['name'] = 'User renamed'
    core.document['spaces'][0]['tabs'][0]['root'] = tree(nodes, True)
    core.document['opaque'] = {'serde': [None, {'keep': True}]}
    core.version += 1
    before = copy.deepcopy(core.document)
    backend.store.write('transaction.json', {'schema_version': 1, 'txid': 'testtx', 'source': 'tui',
        'target': 'herdr-core', 'phase': 'restore_pending', 'plan': value, 'receipt': manifest['receipt']})
    calls = len(core.calls)
    runtime_controller.Controller(backend.store, backend).recover()
    saved = backend.store.read('manifest.json')
    assert saved['schema_version'] == 2 and saved['txid'] == 'testtx'
    assert len(native.panes(saved['plan'])) == 63 and len(native.sessions(saved['plan'])) == 56
    assert not {'t1', 't2', 't3', 't11'} & set(saved['receipt']['terminals'].values())
    assert all(core.terminals[a]['state'] == 'finished' for a in ('t1', 't2', 't3', 't11'))
    assert core.document == before and backend.store.read('transaction.json')['phase'] == 'complete'
    backend.restore_current()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set', 'command') for m, _ in core.calls[calls:])


@pytest.mark.parametrize('program', [['/usr/bin/vim'], ['opencode']])
def test_current_fresh_baseline_leaves_unowned_unknown_program_untouched(backend, program):
    core = FakeCore(backend)
    created = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'labels': {}})
    synthetic_process(backend, created['pid'], program)
    core.terminals[created['address']]['argv'] = program
    core.document = native.layout.to_app_document(plan(None), {'s0-t0-p0': created['address']})
    before = copy.deepcopy(core.document)
    calls = len(core.calls)
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan'] == {'schema_version': 1, 'spaces': []}
    assert core.document == before
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[calls:])


@pytest.mark.parametrize('proof', ['database-directory', 'actual-directory', 'duplicate'])
def test_current_later_client_adoption_refuses_bad_proofs_without_native_effect(backend, proof):
    core = FakeCore(backend)
    created = core.rpc('terminal.run', {'argv': [str(backend.home / '.local/bin/opencode'), '--session', 'ses_abc'],
                                      'cwd': '/work', 'labels': {}})
    core.document = native.layout.to_app_document(plan(), {'s0-t0-p0': created['address']})
    if proof == 'database-directory':
        with sqlite3.connect(backend.database_path()) as db:
            db.execute('UPDATE session SET directory = ?', ('/elsewhere',))
    elif proof == 'actual-directory':
        synthetic_process(backend, created['pid'], wrapper_argv(backend), cwd='/elsewhere')
    else:
        synthetic_process(backend, 90, wrapper_argv(backend))
    calls = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert backend.store.read('manifest.json') is None
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[calls:])


@pytest.mark.parametrize('boundary', ['kill-intent', 'run-intent', 'cas-intent', 'cas-conflict'])
def test_current_repair_races_preserve_user_edit_without_duplicate_creation(backend, boundary):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    assert core.document is not None
    core.document['opaque'] = 'before'
    core.version += 1
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    publish = backend._receipt
    operations = {'kill-intent': 'terminal.kill', 'run-intent': 'terminal.run', 'cas-intent': 'doc.set'}
    def race(receipt):
        publish(receipt)
        if boundary in operations and (receipt.get('pending') or {}).get('operation') == operations[boundary]:
            assert core.document is not None
            core.document['opaque'] = 'user-edit'
            core.version += 1
    backend._receipt = race
    rpc = core.rpc
    def conflict(method, params):
        if method == 'doc.set':
            assert core.document is not None
            core.document['opaque'] = 'user-edit'
            core.version += 1
        return rpc(method, params)
    if boundary == 'cas-conflict':
        backend.core = conflict
    calls = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert core.document['opaque'] == 'user-edit'
    backend._receipt = publish
    backend.core = rpc
    with pytest.raises(native.NativeError):
        backend.restore_current()
    # R3 creates and rebinds before publishing its old-shell kill intent.
    expected_runs = 0 if boundary == 'run-intent' else 1
    assert sum(m == 'terminal.run' for m, _ in core.calls[calls:]) == expected_runs
    assert not any(m == 'terminal.kill' for m, _ in core.calls[calls:])


def test_current_schema2_reboot_rebinds_owned_leaf_preserving_unowned_unknown_view(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    assert core.document is not None
    original = copy.deepcopy(core.document['spaces'][0]['tabs'][0]['root'])
    unknown = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'labels': {}})
    synthetic_process(backend, unknown['pid'], ['/usr/bin/vim'])
    core.terminals[unknown['address']]['argv'] = ['/usr/bin/vim']
    root = {'id': 'user-split', 'type': 'column', 'opaque': {'keep': None}, 'children': [
        {'id': 'unowned-view', 'type': 'block', 'content': {'terminal': unknown['address']}}, original]}
    core.document['spaces'][0]['tabs'][0]['root'] = root
    core.version += 1
    before = copy.deepcopy(core.document)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    core.active = False
    backend.restore_current()
    expected = native.layout.rebind_app_document(before, {'s0-t0-p0': ('t1', 't3')})
    assert core.document == expected
    assert core.terminals[unknown['address']]['state'] == 'live'
    assert core.terminals['t1']['state'] == 'finished'
    backend.restore_current()
    assert sum(m == 'terminal.run' for m, _ in core.calls) == 3


def test_current_resumed_repair_rechecks_saved_source_labels_before_kill(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    publish = backend._receipt
    def crash(receipt):
        publish(receipt)
        if receipt.get('repairs') and receipt.get('pending') is None:
            raise ValueError('synthetic crash after adopted baseline')
    backend._receipt = crash
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend._receipt = publish
    core.terminals['t1']['labels'] = {'foreign': 'changed'}
    calls = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set') for m, _ in core.calls[calls:])


def test_unpublished_full_v1_creation_still_uses_strict_migration_recovery(backend):
    core = FakeCore(backend)
    value = plan()
    receipt = backend.prepare('herdr-core', value, 'synthetic')
    cas = backend._cas
    backend._cas = lambda *args: (_ for _ in ()).throw(ValueError('synthetic crash before CAS intent'))
    with pytest.raises(native.NativeError):
        backend.restore('herdr-core', value, 'synthetic', receipt)
    backend._cas = cas
    saved = backend.store.read('receipt-synthetic.json')
    assert saved['terminals'] == {'s0-t0-p0': 't1'} and saved['pending'] is None
    assert saved['document'] is None and core.document is None
    backend.store.write('manifest.json', {'schema_version': 1, 'runtime': 'herdr-core',
                         'txid': 'synthetic', 'plan': value, 'receipt': saved})
    calls = len(core.calls)
    backend.restore_current()
    assert core.document == native.layout.to_app_document(value, saved['terminals'])
    assert not any(m == 'terminal.run' for m, _ in core.calls[calls:])


def test_published_partial_v1_receipt_does_not_resurrect_finished_view(backend):
    core = FakeCore(backend)
    manifest = manifest_for(backend, core)
    core.rpc('terminal.kill', {'terminal': 't1'})
    # Old recovery could persist removal from its binding map before crashing.
    receipt = manifest['receipt']
    receipt['terminals'] = {}
    backend._receipt(receipt)
    calls = len(core.calls)
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan'] == {'schema_version': 1, 'spaces': []}
    assert core.document == manifest['receipt']['document']
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[calls:])


def test_fresh_selected_live_core_adopts_exact_client_without_native_effect(backend):
    core = FakeCore(backend)
    created = core.rpc('terminal.run', {'argv': [str(backend.home / '.local/bin/opencode'), '--session', 'ses_abc'],
                                      'cwd': '/work', 'labels': {'user': 'retain'}})
    core.document = native.layout.to_app_document(plan(), {'s0-t0-p0': created['address']})
    calls = len(core.calls)
    backend.restore_current()
    saved = backend.store.read('manifest.json')
    assert saved['schema_version'] == 2 and saved['plan'] == plan()
    assert saved['receipt']['labels'] == {'s0-t0-p0': {'user': 'retain'}}
    assert backend.store.read(saved['receipt']['adoption_backup'])['manifest'] is None
    backend.restore_current()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set', 'command') for m, _ in core.calls[calls:])


def test_fresh_selected_live_core_without_document_is_quiet(backend):
    core = FakeCore(backend)
    backend.restore_current()
    assert backend.store.read('manifest.json') is None
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set', 'command') for m, _ in core.calls)


def test_current_repair_waits_for_actual_shell_pid_exit_not_only_finished_record(backend):
    core = r1_shell(backend)
    rpc = core.rpc
    def retained_process(method, params):
        if method == 'terminal.kill':
            core.calls.append((method, copy.deepcopy(params)))
            core.terminals[params['terminal']]['state'] = 'finished'
            return copy.deepcopy(core.terminals[params['terminal']])
        return rpc(method, params)
    backend.core = retained_process
    calls = len(core.calls)
    with pytest.raises(native.NativeError, match='proof'):
        backend.restore_current()
    assert backend.store.read('receipt-testtx.json')['pending']['operation'] == 'terminal.kill'
    with pytest.raises(native.NativeError, match='^core repair guard exit unproven$'):
        backend.restore_current()
    assert sum(m == 'terminal.kill' for m, _ in core.calls[calls:]) == 1
    assert not any(m in ('terminal.run', 'doc.set') for m, _ in core.calls[calls:])


@pytest.mark.parametrize('malformed', ['binding', 'labels', 'document', 'pending'])
def test_malformed_current_receipt_refuses_before_starting_stopped_core(backend, malformed):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    receipt = backend.store.read('receipt-testtx.json')
    if malformed == 'binding':
        receipt['bindings']['s0-t0-p0'] = 'missing-leaf'
    elif malformed == 'labels':
        receipt['labels']['s0-t0-p0'] = {'bad': None}
    elif malformed == 'document':
        receipt['document'] = {'spaces': 'invalid'}
    else:
        receipt['pending'] = {'operation': 'unknown'}
    backend.store.write('receipt-testtx.json', receipt)
    core.active = False
    calls = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set', 'command') for m, _ in core.calls[calls:])


def test_recover_retained_shell_receipt_completes_64_pane_switch(backend):
    core = FakeCore(backend)
    txid = 'shellfix'
    leaves = [{'key': 's0-t0-p' + str(i), 'cwd': '/work',
               'session_id': None if i < 10 else 'ses_hotfix' + str(i)} for i in range(64)]
    def tree(keys):
        if len(keys) == 1:
            return {'pane': keys[0]}
        half = len(keys) // 2
        return {'axis': 'row', 'ratio': 0.5, 'children': [tree(keys[:half]), tree(keys[half:])]}
    value = {'schema_version': 1, 'spaces': [{'name': 'Fixture', 'directory': '/work', 'tabs': [
        {'name': 'Mixed panes', 'root': tree([p['key'] for p in leaves]), 'panes': leaves}]}]}
    with sqlite3.connect(backend.database_path()) as db:
        db.executemany('INSERT INTO session VALUES (?, ?)',
                       [(p['session_id'], p['cwd']) for p in leaves if p['session_id']])
    receipt = backend.prepare('herdr-core', value, txid, replace_target=True)
    created = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work',
                       'labels': {'remote-herdr-owner': txid, 'remote-herdr-pane': leaves[0]['key']}})
    first = created['address']
    receipt['terminals'][leaves[0]['key']] = first
    backend._receipt(receipt)
    backend.store.write('transaction.json', {
        'schema_version': 1, 'txid': txid, 'source': 'tui', 'target': 'herdr-core',
        'phase': 'restore_pending', 'replace_target': True, 'capture': None,
        'plan': value, 'receipt': receipt})
    assert backend.store.read('manifest.json') is None and receipt['pending'] is None
    before = len(core.calls)
    runtime_controller.Controller(backend.store, backend).recover()
    journal = backend.store.read('transaction.json')
    assert journal['phase'] == 'complete' and journal['previous_manifest'] is None
    final = backend.store.read('manifest.json')
    assert final['receipt']['terminals'][leaves[0]['key']] == first
    assert len(final['receipt']['terminals']) == len(core.terminals) == 64
    assert sum(method == 'terminal.run' for method, _ in core.calls[before:]) == 63
    assert sum(method == 'doc.set' for method, _ in core.calls[before:]) == 1
    assert not any(method in ('terminal.kill', 'command') for method, _ in core.calls[before:])
    assert len(backend._coverage(value)) == 54
    assert backend.store.read(receipt['backup']) is not None
    before = len(core.calls)
    runtime_controller.Controller(backend.store, backend).recover()
    backend.restore_current()
    assert not any(method in ('terminal.run', 'terminal.kill', 'doc.set', 'command')
                   for method, _ in core.calls[before:])


@pytest.mark.parametrize('session', [None, 'ses_abc'])
def test_core_label_wire_contract_omits_empty_session_only_for_shells(backend, session):
    pane = plan(session)['spaces'][0]['tabs'][0]['panes'][0]
    labels = backend._labels('labelproof', pane)
    assert labels == {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': pane['key'],
                      **({'remote-herdr-session': session} if session else {})}


@pytest.mark.parametrize('labels', [
    {}, {'remote-herdr-pane': 's0-t0-p0'}, {'remote-herdr-owner': 'labelproof'},
    {'remote-herdr-owner': 'foreign', 'remote-herdr-pane': 's0-t0-p0'},
    {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 'other'},
    {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0', 'remote-herdr-session': 'ses_abc'},
    {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0', 'remote-herdr-unknown': ''},
])
def test_shell_empty_label_compatibility_does_not_weaken_other_labels(backend, labels):
    core = FakeCore(backend)
    terminal = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'labels': labels})
    # Keep even unknown empty keys in this malformed observation; do not discard
    # them while deciding ownership, regardless of core's creation behavior.
    terminal['labels'] = labels
    with pytest.raises(native.NativeError, match='ownership'):
        backend._match_terminal(terminal, plan(None)['spaces'][0]['tabs'][0]['panes'][0], 'labelproof')


@pytest.mark.parametrize('legacy_session_label', [False, True])
def test_shell_labels_accept_pinned_wire_and_legacy_empty_representation(backend, legacy_session_label):
    core = FakeCore(backend)
    terminal = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work',
                        'labels': {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0'}})
    if legacy_session_label:
        terminal['labels']['remote-herdr-session'] = ''
    backend._match_terminal(terminal, plan(None)['spaces'][0]['tabs'][0]['panes'][0], 'labelproof')


def test_legacy_pending_shell_creation_matches_normalized_core_labels(backend):
    core = FakeCore(backend)
    value = plan(None)
    receipt = backend.prepare('herdr-core', value, 'labelproof')
    labels = {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0', 'remote-herdr-session': ''}
    created = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'labels': labels})
    core.terminals[created['address']]['labels'].update(app_labels())
    receipt['pending'] = {'operation': 'terminal.run', 'pane': 's0-t0-p0', 'labels': labels}
    backend._receipt(receipt)
    backend.store.write('manifest.json', {'schema_version': 1, 'runtime': 'herdr-core',
                        'plan': value, 'receipt': receipt, 'txid': 'labelproof'})
    before = len(core.calls)
    backend.restore_current()
    assert backend.store.read('manifest.json')['receipt']['terminals'] == {'s0-t0-p0': created['address']}
    assert not any(method in ('terminal.run', 'terminal.kill') for method, _ in core.calls[before:])


@pytest.mark.parametrize('session_label', [None, '', 'ses_foreign'])
def test_agent_session_label_is_never_optional(backend, session_label):
    core = FakeCore(backend)
    labels = {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0'}
    if session_label is not None:
        labels['remote-herdr-session'] = session_label
    terminal = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'labels': labels})
    with pytest.raises(native.NativeError, match='ownership'):
        backend._match_terminal(terminal, plan()['spaces'][0]['tabs'][0]['panes'][0], 'labelproof')


@pytest.mark.parametrize('matches', [0, 2])
def test_legacy_pending_shell_creation_missing_or_duplicate_match_refuses(backend, matches):
    core = FakeCore(backend)
    value = plan(None)
    receipt = backend.prepare('herdr-core', value, 'labelproof')
    labels = {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0', 'remote-herdr-session': ''}
    for _ in range(matches):
        core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'labels': labels})
    receipt['pending'] = {'operation': 'terminal.run', 'pane': 's0-t0-p0', 'labels': labels}
    backend._receipt(receipt)
    backend.store.write('manifest.json', {'schema_version': 1, 'runtime': 'herdr-core',
                        'plan': value, 'receipt': receipt, 'txid': 'labelproof'})
    before = len(core.calls)
    with pytest.raises(native.NativeError, match='uncertain terminal creation unresolved'):
        backend.restore_current()
    assert not any(method in ('terminal.run', 'terminal.kill', 'doc.set') for method, _ in core.calls[before:])


@pytest.mark.parametrize('legacy_empty', [False, True])
def test_unrecorded_owned_shell_refuses_blind_duplicate_creation(backend, legacy_empty):
    core = FakeCore(backend)
    value = plan(None)
    receipt = backend.prepare('herdr-core', value, 'labelproof')
    terminal = core.rpc('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': '/work',
                        'labels': {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0'}})
    if legacy_empty:
        core.terminals[terminal['address']]['labels']['remote-herdr-session'] = ''
    core.terminals[terminal['address']]['labels'].update(app_labels())
    before = len(core.calls)
    with pytest.raises(native.NativeError, match='prior terminal creation requires recovery'):
        backend.restore('herdr-core', value, 'labelproof', receipt)
    assert not any(method in ('terminal.run', 'terminal.kill', 'doc.set') for method, _ in core.calls[before:])


def app_labels():
    return {'where': 'desktop', 'herdr.seen': '1', 'herdr.space': 'space',
            'herdr.tab': 'tab', 'another-display-key': ''}


@pytest.mark.parametrize('lost_reply', [False, True])
def test_r2_controller_recovers_retained_mixed_app_document(backend, tmp_path, lost_reply):
    with runtime_controller.Store(tmp_path / 'private-journal') as store:
        backend.store = store
        core = FakeCore(backend)
        value = plan()
        tabs = value['spaces'][0]['tabs']
        for i in (1, 2):
            tab = copy.deepcopy(tabs[0])
            key = f's0-t{i}-p0'
            tab.update(name=f'App tab {i}', root={'pane': key}, panes=[{
                'key': key, 'cwd': '/work', 'session_id': f'ses_app{i}'}])
            tabs.append(tab)
        with sqlite3.connect(backend.database_path()) as db:
            db.executemany('INSERT INTO session VALUES (?, ?)', [('ses_app1', '/work'), ('ses_app2', '/work')])
        manifest_for(backend, core, value)
        assert core.document is not None
        for tab in core.document['spaces'][0]['tabs']:
            tab['root'] = {'id': tab['id'], 'type': 'row', 'children': [tab['root']],
                           'opaque': {'keep': [None, True]}}
        core.document['metadata'] = {'app': 'untouched'}
        for terminal in core.terminals.values():
            terminal['labels'].update(app_labels())
        core.version += 1
        backend.restore_current()
        manifest = store.read('manifest.json')
        original = copy.deepcopy(core.document)
        live = {a: copy.deepcopy(t) for a, t in core.terminals.items() if a != 't2'}
        synthetic_process(backend, core.terminals['t2']['pid'], ['/bin/bash', '-l'])
        arm_legacy_kill(backend, core)
        store.write('transaction.json', {'schema_version': 1, 'txid': 'testtx', 'source': 'tui',
            'target': 'herdr-core', 'phase': 'restore_pending', 'plan': manifest['plan'],
            'receipt': manifest['receipt']})
        write = store.write
        if lost_reply:
            def rpc(method, params):
                result = core.rpc(method, params)
                if method == 'terminal.kill':
                    raise native.NativeError('synthetic interruption')
                return result
            backend.core = rpc
        else:
            def interrupt():
                raise native.NativeError('synthetic interruption')
            r1_on_intent(backend, interrupt)
        with pytest.raises(runtime_controller.ControllerError, match='recovery uncertain'):
            runtime_controller.Controller(store, backend).recover()
        assert store.read('transaction.json')['phase'] == 'restore_pending'
        assert store.read('receipt-testtx.json')['pending']['operation'] == 'terminal.kill'
        store.write = write
        def app_rpc(method, params):
            result = core.rpc(method, params)
            if method == 'terminal.run':
                core.terminals[result['address']]['labels'].update(app_labels())
                result['labels'].update(app_labels())
            return result
        backend.core = app_rpc
        for terminal in core.terminals.values():
            terminal['labels'].update({k: 'changed' for k in app_labels()})
        calls = len(core.calls)
        runtime_controller.Controller(store, backend).recover()
        final = store.read('manifest.json')
        assert store.read('transaction.json')['phase'] == 'complete'
        assert final['receipt']['pending'] is None and final['receipt']['repairs'] == {}
        assert len(core.terminals) == 4
        assert sum(m == 'terminal.run' for m, _ in core.calls[calls:]) == 1
        assert sum(m == 'terminal.kill' for m, _ in core.calls[calls:]) == (not lost_reply)
        assert not any(m == 'command' for m, _ in core.calls[calls:])
        expected = copy.deepcopy(original)
        expected['spaces'][0]['tabs'][1]['root']['children'][0]['content']['terminal'] = 't4'
        assert core.document == expected
        assert final['receipt']['bindings'] == manifest['receipt']['bindings']
        for address, terminal in live.items():
            assert core.terminals[address]['pid'] == terminal['pid']
            assert core.terminals[address]['state'] == 'live'
            assert backend.process_argv(terminal['pid']) == wrapper_argv(
                backend, terminal['labels']['remote-herdr-session'])
        assert len(backend._coverage(final['plan'])) == 3
        backend.restore_current()


@pytest.mark.parametrize('session', [None, 'ses_abc'])
def test_r2_label_namespace_is_exact_and_symmetric(backend, session):
    expected = backend._labels('labelproof', plan(session)['spaces'][0]['tabs'][0]['panes'][0])
    observed = {**expected, **app_labels()}
    assert backend._same_labels(observed, expected)
    assert backend._same_labels(expected, observed)
    assert backend._same_labels(observed, {**expected, 'where': 'changed'})
    if session is None:
        assert backend._same_labels(observed, {**expected, 'remote-herdr-session': ''})
    for key in expected:
        for changed in ('missing', 'changed', ''):
            bad = dict(observed)
            if changed == 'missing':
                bad.pop(key)
            else:
                bad[key] = changed
            assert not backend._same_labels(bad, expected)
            assert not backend._same_labels(expected, bad)
    for bad in ({**observed, 'remote-herdr-extra': 'x'},
                {**observed, 'where': None}, {**observed, 1: 'display'},
                {**observed, 'herdr.tab': []}, None, [], 'labels'):
        assert not backend._same_labels(bad, expected)
        assert not backend._same_labels(expected, bad)
    for bad in ({'remote-herdr-owner': '', 'remote-herdr-pane': 'pane'},
                {'remote-herdr-owner': 'owner', 'remote-herdr-pane': ''},
                {'remote-herdr-extra': 'x'}, {'where': None}):
        assert not backend._same_labels(bad, bad)


@pytest.mark.parametrize('boundary', ['inventory', 'verification', 'kill-intent'])
@pytest.mark.parametrize('change', ['added', 'changed', 'removed'])
def test_r2_display_churn_at_shared_guards(backend, boundary, change):
    core = r1_shell(backend) if boundary == 'kill-intent' else FakeCore(backend)
    if boundary != 'kill-intent':
        manifest_for(backend, core)
        backend.restore_current()
    terminal = core.terminals['t1']
    if change != 'added':
        terminal['labels'].update(app_labels())
    def churn():
        for key in app_labels():
            if change == 'removed':
                terminal['labels'].pop(key, None)
            else:
                terminal['labels'][key] = 'updated'
    if boundary == 'kill-intent':
        r1_on_intent(backend, churn)
    elif boundary == 'inventory':
        original = core.rpc
        def rpc(method, params):
            if method == 'terminal.get':
                churn()
            return original(method, params)
        backend.core = rpc
    else:
        saved = backend.store.read('manifest.json')
        saved['receipt']['labels']['s0-t0-p0'].update(app_labels())
        backend.store.write('manifest.json', saved)
        backend.store.write('receipt-testtx.json', saved['receipt'])
        churn()
    before = len(core.calls)
    if boundary == 'verification':
        saved = backend.store.read('manifest.json')
        receipt = copy.deepcopy(saved['receipt'])
        backend.verify('herdr-core', saved['plan'], receipt)
        assert receipt['labels'] == saved['receipt']['labels']
    backend.restore_current()
    assert backend.store.read('manifest.json')['schema_version'] == 2
    assert sum(m == 'terminal.kill' for m, _ in core.calls[before:]) == (boundary == 'kill-intent')


@pytest.mark.parametrize('family', ['match', 'receipt', 'ready', 'legacy-verify', 'current-verify', 'capture'])
@pytest.mark.parametrize('bad', [False, True])
def test_r2_app_labelled_caller_families_preserve_ownership_guards(backend, family, bad):
    core = FakeCore(backend)
    manifest = manifest_for(backend, core)
    if family == 'current-verify':
        backend.restore_current()
        manifest = backend.store.read('manifest.json')
    terminal = core.terminals['t1']
    terminal['labels'].update(app_labels())
    if bad:
        terminal['labels']['remote-herdr-unexpected'] = 'private'
    pane = manifest['plan']['spaces'][0]['tabs'][0]['panes'][0]
    def check():
        if family == 'match':
            backend._match_terminal(terminal, pane, 'testtx')
        elif family == 'receipt':
            backend._receipt_consistency(backend._terminals())
        elif family == 'ready':
            backend._wait_created_core('t1', pane, backend._labels('testtx', pane))
        elif family == 'capture':
            backend.capture('herdr-core')
        else:
            backend.verify('herdr-core', manifest['plan'], manifest['receipt'])
    before = len(core.calls)
    if bad:
        with pytest.raises(native.NativeError):
            check()
    else:
        check()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set', 'command') for m, _ in core.calls[before:])


@pytest.mark.parametrize('replacement', ['shell', 'foreign', 'pending'])
def test_prepare_observes_kept_spawn_before_proving_program(backend, replacement):
    core = FakeCore(backend)
    terminal: dict = {'address': 'kept', 'state': 'live', 'keep': True, 'pid': None,
                'argv': ['/bin/bash', '-l'], 'cwd': '/work', 'foreground': None, 'labels': {}}
    core.terminals['kept'] = terminal
    observations = []
    def wait(check, *, seconds=None):
        observations.append('pending')
        assert check() is False
        if replacement != 'pending':
            argv = ['/bin/bash', '-l'] if replacement == 'shell' else ['/usr/bin/vim']
            synthetic_process(backend, 81, argv)
            terminal.update(pid=81, argv=argv)
        if not check():
            raise native.NativeError('native readiness or stop proof unavailable')
        observations.append('ready')
    backend._wait = wait
    if replacement == 'shell':
        receipt = backend.prepare('herdr-core', plan(), 'kepttx')
        assert receipt['pending'] is None
        assert observations == ['pending', 'ready']
    else:
        with pytest.raises(native.NativeError):
            backend.prepare('herdr-core', plan(), 'kepttx')
    assert not any(method in {'terminal.run', 'terminal.kill', 'doc.set', 'command'}
                   for method, _ in core.calls)


def test_readiness_timeouts_identify_the_failed_boundary(backend):
    core = FakeCore(backend)
    receipt = backend.prepare('herdr-core', plan(), 'readytx')
    def timeout(check, *, seconds=None):
        raise native.NativeError('native readiness or stop proof unavailable')
    backend._wait = timeout
    with pytest.raises(native.NativeError, match='^core kept-terminal spawn readiness unavailable$'):
        backend._wait_core_spawns()
    with pytest.raises(native.NativeError, match='^restored runtime layout readiness unavailable$'):
        backend._wait_ready('herdr-core', plan(), receipt)
    with pytest.raises(native.NativeError, match='^core restored terminal readiness unavailable$'):
        backend.restore('herdr-core', plan(), 'readytx', receipt)
    assert sum(method == 'terminal.run' for method, _ in core.calls) == 1


@pytest.mark.parametrize('recovers', [True, False])
def test_kept_spawn_wait_covers_native_backoff_cap_and_remains_bounded(backend, monkeypatch, recovers):
    core = FakeCore(backend)
    backend.poll_seconds = 30.0
    clock = {'now': 0.0}
    monkeypatch.setattr(native.time, 'monotonic', lambda: clock['now'])
    def sleep(seconds):
        clock['now'] += seconds
    monkeypatch.setattr(native.time, 'sleep', sleep)
    def terminals():
        return [{'state': 'live', 'keep': True,
                 'pid': 81 if recovers and clock['now'] >= 60 else None}]
    backend._terminals = terminals
    if recovers:
        backend._wait_core_spawns()
        assert 60 <= clock['now'] < 61
    else:
        with pytest.raises(native.NativeError, match='kept-terminal spawn readiness unavailable'):
            backend._wait_core_spawns()
        assert 75 <= clock['now'] < 76
    assert backend.poll_seconds == 30.0
    assert not core.calls


def test_full_core_restore_direct_argv_and_idempotent_recovery(backend):
    core = FakeCore(backend)
    manifest = manifest_for(backend, core)
    runs = [params for method, params in core.calls if method == 'terminal.run']
    assert len(runs) == 1
    assert runs[0]['argv'] == [str(backend.home / '.local/bin/opencode'), '--session', 'ses_abc']
    assert runs[0]['labels'] == {'remote-herdr-owner': 'testtx', 'remote-herdr-pane': 's0-t0-p0',
                                'remote-herdr-session': 'ses_abc'}
    assert all(runs[0][key] for key in ('keep', 'no_parent', 'no_notify'))
    before = copy.deepcopy(core.terminals)
    backend.restore_current()
    backend.restore_current()
    assert core.terminals == before
    assert len([m for m, _ in core.calls if m == 'terminal.run']) == 1
    assert backend.store.read('manifest.json')['plan'] == manifest['plan']


@pytest.mark.parametrize('boundary', ['before_receipt', 'after_backup', 'start_observed'])
def test_prepare_crash_reconciles_without_terminal_creation(backend, boundary):
    core = FakeCore(backend)
    if boundary == 'after_backup':
        original = backend.prepare('herdr-core', plan(), 'crashtx')
    elif boundary == 'start_observed':
        backend.store.write('receipt-crashtx.json', {'runtime': 'herdr-core', 'txid': 'crashtx',
            'document': None, 'doc_version': 0, 'terminals': {}, 'pending': {'operation': 'server.start'}})
    recovered = backend.recover_prepared('herdr-core', plan(), 'crashtx')
    assert recovered['pending'] is None and recovered['terminals'] == {}
    assert backend.store.read(recovered['backup']) is not None
    assert not any(method in {'terminal.run', 'terminal.kill', 'doc.set'} for method, _ in core.calls)
    if boundary == 'after_backup':
        assert recovered['backup'] == original['backup']


def test_tui_crash_between_offline_write_and_start_can_recover(backend):
    backend.snapshot_path.parent.mkdir(parents=True)
    generated = native.layout.to_tui_snapshot(plan())
    backend.snapshot_path.write_text(json.dumps(generated))
    backend.snapshot_path.chmod(0o600)
    receipt = {'runtime': 'tui', 'txid': 'crashtx', 'document': None,
               'pending': {'operation': 'tui.write', 'document': generated}}
    calls = []
    def command(argv, timeout=30):
        calls.append(argv)
        return 'inactive\n' if 'show' in argv else {}
    backend.command = command
    backend._wait_ready = lambda target, value, saved: None
    recovered = backend.recover_tui(plan(), 'crashtx', receipt)
    assert recovered['pending'] is None and recovered['document'] == generated
    assert sum('start' in argv for argv in calls) == 1


def test_tui_uncertain_exec_waits_without_second_start(backend):
    receipt = {'runtime': 'tui', 'txid': 'crashtx', 'document': None,
               'pending': {'operation': 'tui.start'}}
    calls = []
    backend.command = lambda argv, timeout=30: calls.append(argv) or 'activating\n'
    backend._wait_ready = lambda *args: (_ for _ in ()).throw(native.NativeError('not ready'))
    with pytest.raises(native.NativeError):
        backend.recover_tui(plan(), 'crashtx', receipt)
    assert not any('start' in argv for argv in calls)


@pytest.mark.parametrize('change', [None, 'snapshot', 'surviving-client'])
def test_interrupted_boot_preserves_exact_native_snapshot(backend, change):
    backend.snapshot_path.parent.mkdir(parents=True)
    snapshot = native.layout.to_tui_snapshot(plan())
    snapshot['sidebar_width'] = 45
    backend.snapshot_path.write_text(json.dumps(snapshot, indent=2))
    backend.snapshot_path.chmod(0o600)
    before = backend.snapshot_path.read_bytes()
    receipt = {'runtime': 'tui', 'txid': 'boottx', 'document': copy.deepcopy(snapshot),
               'pending': {'operation': 'tui.start'}}
    if change == 'snapshot':
        snapshot['sidebar_width'] = 46
        backend.snapshot_path.write_text(json.dumps(snapshot))
    elif change == 'surviving-client':
        synthetic_process(backend, 88, wrapper_argv(backend))
    calls = []
    backend.command = lambda argv, timeout=30: calls.append(argv) or ('inactive\n' if 'show' in argv else {})
    backend._wait_ready = lambda *args: None
    def no_write(*args, **kwargs):
        raise AssertionError('boot recovery must preserve native snapshot bytes')
    backend._atomic = no_write
    if change:
        with pytest.raises(native.NativeError):
            backend.recover_tui(plan(), 'boottx', receipt, preserve_snapshot=True)
        assert not any('start' in argv for argv in calls)
    else:
        saved = backend.recover_tui(plan(), 'boottx', receipt, preserve_snapshot=True)
        assert saved['document'] == snapshot and saved['pending'] is None
        assert backend.snapshot_path.read_bytes() == before
        assert sum('start' in argv for argv in calls) == 1


@pytest.mark.parametrize('retain_original_argv', [False, True])
def test_owned_shell_recovery_retains_records_and_remaps(backend, retain_original_argv):
    core = FakeCore(backend)
    manifest_for(backend, core)
    terminal = core.terminals['t1']
    synthetic_process(backend, terminal['pid'], ['/bin/bash', '-l'])
    if not retain_original_argv:
        terminal['argv'] = ['/bin/bash', '-l']
    backend.restore_current()
    assert core.terminals['t1']['state'] == 'finished'
    assert core.terminals['t2']['argv'][-1] == 'ses_abc'
    receipt = backend.store.read('manifest.json')['receipt']
    assert receipt['terminals'] == {'s0-t0-p0': 't2'}
    assert core.document == native.layout.to_app_document(plan(), receipt['terminals'])
    assert len([m for m, _ in core.calls if m == 'terminal.kill']) == 1


def test_busy_owned_program_is_not_overwritten(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    terminal = core.terminals['t1']
    terminal['foreground'] = {'pid': 32, 'argv': ['/usr/bin/vim'], 'cwd': '/work'}
    synthetic_process(backend, 32, ['/usr/bin/vim'])
    before = len(core.calls)
    with pytest.raises(native.NativeError, match='program'):
        backend.restore_current()
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('change', ['argv', 'pid', 'document'])
def test_shell_recovery_rechecks_after_publishing_kill_intent(backend, change):
    core = FakeCore(backend)
    manifest_for(backend, core)
    terminal = core.terminals['t1']
    synthetic_process(backend, terminal['pid'], ['/bin/bash', '-l'])
    terminal['argv'] = ['/bin/bash', '-l']
    original = backend._receipt
    def persist(receipt):
        original(receipt)
        if (receipt.get('pending') or {}).get('operation') == 'terminal.kill':
            if change == 'argv':
                synthetic_process(backend, terminal['pid'], ['/usr/bin/vim'])
            elif change == 'pid':
                synthetic_process(backend, terminal['pid'], ['/bin/bash', '-l'], ticks=99)
            else:
                core.version += 1
    backend._receipt = persist
    before = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(method == 'terminal.kill' for method, _ in core.calls[before:])


def r1_shell(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    core.calls.clear()
    arm_legacy_kill(backend, core)
    return core


def arm_legacy_kill(backend, core):
    # Serialize the historical kill-first boundary explicitly. These regression
    # tests exercise retained R1 intents, not R3's deliberately changed ordering.
    restore = backend.restore_current
    def legacy_restore():
        backend.restore_current = restore
        manifest = backend.store.read('manifest.json')
        receipt = copy.deepcopy(manifest['receipt'])
        document, version = backend._document()
        projected, bindings, labels, repairs = backend._current_projection(
            document, backend._terminals(), manifest['plan'], receipt)
        for repair in repairs.values():
            repair.pop('create_id', None)
            repair['labels'].pop('remote-herdr-repair', None)
        receipt.update(current_document=True, plan=projected, document=document, doc_version=version,
                       bindings={k: b['leaf'] for k, b in bindings.items()},
                       labels={k: labels[b['leaf']] for k, b in bindings.items()}, repairs=repairs)
        key, binding = next((k, b) for k, b in bindings.items() if b['leaf'] in repairs)
        leaf = binding['leaf']
        terminal = core.terminals[binding['terminal']]
        proofs = backend._pid_proofs([terminal['pid'], (terminal.get('foreground') or terminal)['pid']])
        repairs[leaf]['pids'] = proofs
        receipt['pending'] = {'operation': 'terminal.kill', 'pane': key, 'leaf': leaf,
                              'terminal': terminal['address'], 'pids': proofs,
                              'identity': backend._kill_identity(terminal)}
        backend._receipt(receipt)
        restore()
    backend.restore_current = legacy_restore


def r1_on_intent(backend, action):
    write = backend.store.write
    def persist(name, value):
        write(name, value)
        if name == 'receipt-testtx.json' and (value.get('pending') or {}).get('operation') == 'terminal.kill':
            action()
    backend.store.write = persist
    return write


@pytest.mark.parametrize('field', ['title', 'status', 'records', 'turn', 'geometry', 'foreground'])
def test_r1_display_churn_after_kill_intent_is_not_identity(backend, field):
    core = r1_shell(backend)
    terminal = core.terminals['t1']
    value = ({'pid': terminal['pid'], 'argv': ['/bin/bash', '-l'], 'cwd': '/work'}
             if field == 'foreground' else {'async': 'PRIVATE_DISPLAY'})
    r1_on_intent(backend, lambda: terminal.update({field: value}))
    backend.restore_current()
    assert [m for m, _ in core.calls if m == 'terminal.kill'] == ['terminal.kill']
    assert backend.store.read('manifest.json')['schema_version'] == 2


@pytest.mark.parametrize('lost_reply', [False, True])
@pytest.mark.parametrize('legacy', [False, True])
@pytest.mark.parametrize('schema', [1, 2])
def test_r1_interrupted_kill_reconciles_original_observation(backend, lost_reply, legacy, schema):
    core = r1_shell(backend)
    write = backend.store.write
    if lost_reply:
        def rpc(method, params):
            result = core.rpc(method, params)
            if method == 'terminal.kill':
                raise native.NativeError('synthetic interruption')
            return result
        backend.core = rpc
    else:
        def interrupt():
            raise native.NativeError('synthetic interruption')
        r1_on_intent(backend, interrupt)
    with pytest.raises(native.NativeError, match='synthetic interruption'):
        backend.restore_current()
    backend.store.write = write
    backend.core = core.rpc
    saved = backend.store.read('receipt-testtx.json')
    if legacy:
        saved['pending'].pop('identity', None)
    # Exercise the old schema-2 pending-kill entry point as well as published v1.
    manifest = backend.store.read('manifest.json')
    if schema == 2:
        manifest.update(schema_version=2, plan=saved['plan'], receipt=saved)
    write('manifest.json', manifest)
    write('receipt-testtx.json', saved)
    backend.restore_current()
    assert len([m for m, _ in core.calls if m == 'terminal.kill']) == 1
    assert len([m for m, _ in core.calls if m == 'terminal.run']) == 1
    assert backend.store.read('receipt-testtx.json')['pending'] is None


@pytest.mark.parametrize('change,label', [
    ('labels', 'labels'), ('pid', 'pid'), ('start', 'start-time'),
    ('argv', 'argv'), ('foreign', 'argv'), ('cwd', 'directory'),
    ('foreground', 'pid'), ('launch', 'argv'), ('raw', 'layout'),
    ('version', 'document-version'), ('session', 'session'),
])
@pytest.mark.parametrize('resume', [False, True])
def test_r1_kill_identity_changes_refuse_with_literal_labels(backend, change, label, resume):
    core = r1_shell(backend)
    terminal = core.terminals['t1']
    def mutate():
        if change == 'labels':
            terminal['labels']['remote-herdr-owner'] = 'PRIVATE_CHANGED'
        elif change == 'pid':
            terminal['pid'] = 988
        elif change == 'start':
            synthetic_process(backend, terminal['pid'], ['/bin/bash', '-l'], ticks=999)
        elif change in ('argv', 'foreign'):
            synthetic_process(backend, terminal['pid'], ['/bin/bash', '--login'] if change == 'argv' else ['/PRIVATE_FOREIGN'])
        elif change == 'cwd':
            synthetic_process(backend, terminal['pid'], ['/bin/bash', '-l'], cwd='/PRIVATE_DIRECTORY')
        elif change == 'foreground':
            terminal['foreground'] = {'pid': 988, 'argv': ['/bin/bash'], 'cwd': '/work'}
        elif change == 'launch':
            terminal['argv'] = ['/PRIVATE_LAUNCH']
        elif change == 'raw':
            core.document['PRIVATE_RAW'] = 'PRIVATE_VALUE'
        elif change == 'version':
            core.version += 1
        else:
            synthetic_process(backend, 988, wrapper_argv(backend))
    if resume:
        def interrupt():
            raise native.NativeError('synthetic interruption')
        write = r1_on_intent(backend, interrupt)
        with pytest.raises(native.NativeError, match='synthetic interruption'):
            backend.restore_current()
        backend.store.write = write
        mutate()
    else:
        r1_on_intent(backend, mutate)
    with pytest.raises(native.NativeError) as error:
        backend.restore_current()
    assert str(error.value) == f'core repair guard {label} changed'
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set') for m, _ in core.calls)
    assert backend.store.read('receipt-testtx.json')['pending']['operation'] == 'terminal.kill'


@pytest.mark.parametrize('bad', [None, {}, {'extra': 'PRIVATE'}, 'PRIVATE', []])
def test_r1_malformed_identity_refuses_without_effect(backend, bad):
    core = r1_shell(backend)
    def interrupt():
        raise native.NativeError('synthetic interruption')
    write = r1_on_intent(backend, interrupt)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.store.write = write
    saved = backend.store.read('receipt-testtx.json')
    saved['pending']['identity'] = bad
    write('receipt-testtx.json', saved)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set') for m, _ in core.calls)
    assert backend.store.read('receipt-testtx.json')['pending'] == saved['pending']


@pytest.mark.parametrize('change', ['extra', 'nested-extra', 'oversized', 'bool-pid', 'wrong-role', 'wrong-proof'])
def test_r1_extended_intent_shape_and_binding_fail_closed(backend, change):
    core = r1_shell(backend)
    def interrupt():
        raise native.NativeError('synthetic interruption')
    write = r1_on_intent(backend, interrupt)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.store.write = write
    saved = backend.store.read('receipt-testtx.json')
    pending = saved['pending']
    if change == 'extra':
        pending['PRIVATE_EXTRA'] = True
    elif change == 'nested-extra':
        pending['identity']['launch']['PRIVATE_EXTRA'] = True
    elif change == 'oversized':
        pending['identity']['argv'] = ['/bin/bash'] + ['PRIVATE'] * 256
    elif change == 'bool-pid':
        pending['identity']['pid'] = True
    elif change == 'wrong-role':
        pending['identity']['foreground_pid'] = 988
    else:
        pending['pids'][0]['start_ticks'] += 1
    write('receipt-testtx.json', saved)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set') for m, _ in core.calls)
    assert backend.store.read('receipt-testtx.json')['pending'] == pending


@pytest.mark.parametrize('change', ['labels', 'raw', 'version', 'still-live-pid', 'launch', 'directory', 'pid', 'keep'])
def test_r1_finished_kill_rechecks_ownership_and_document_without_rekill(backend, change):
    core = r1_shell(backend)
    pid = core.terminals['t1']['pid']
    def rpc(method, params):
        result = core.rpc(method, params)
        if method == 'terminal.kill':
            raise native.NativeError('synthetic lost reply')
        return result
    backend.core = rpc
    with pytest.raises(native.NativeError, match='synthetic lost reply'):
        backend.restore_current()
    backend.core = core.rpc
    if change == 'labels':
        core.terminals['t1']['labels'] = {'PRIVATE': 'PRIVATE'}
    elif change == 'raw':
        core.document['PRIVATE'] = 'PRIVATE'
    elif change == 'version':
        core.version += 1
    elif change == 'still-live-pid':
        synthetic_process(backend, pid, ['/bin/bash', '-l'])
    elif change == 'launch':
        core.terminals['t1']['argv'] = ['/PRIVATE_CHANGED']
    elif change == 'directory':
        core.terminals['t1']['cwd'] = '/PRIVATE_CHANGED'
    elif change == 'pid':
        core.terminals['t1']['pid'] = 988
    else:
        core.terminals['t1']['keep'] = True
    with pytest.raises(native.NativeError) as error:
        backend.restore_current()
    assert 'PRIVATE' not in str(error.value)
    assert len([m for m, _ in core.calls if m == 'terminal.kill']) == 1
    assert not any(m in ('terminal.run', 'doc.set') for m, _ in core.calls)
    assert backend.store.read('receipt-testtx.json')['pending']['operation'] == 'terminal.kill'


def test_r1_legacy_intent_does_not_invent_historical_actual_argv(backend):
    core = r1_shell(backend)
    def interrupt():
        raise native.NativeError('synthetic interruption')
    write = r1_on_intent(backend, interrupt)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.store.write = write
    saved = backend.store.read('receipt-testtx.json')
    saved['pending'].pop('identity')
    write('receipt-testtx.json', saved)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '--login'])
    backend.restore_current()
    assert len([m for m, _ in core.calls if m == 'terminal.kill']) == 1


def test_r1_same_pid_foreground_report_removal_preserves_identity(backend):
    core = r1_shell(backend)
    terminal = core.terminals['t1']
    terminal['foreground'] = {'pid': terminal['pid'], 'argv': ['/bin/bash', '-l'], 'cwd': '/work'}
    r1_on_intent(backend, lambda: terminal.update(foreground=None))
    backend.restore_current()
    assert len([m for m, _ in core.calls if m == 'terminal.kill']) == 1


def test_r1_kept_shell_uses_actual_directory_not_the_original_launch_directory(backend):
    core = r1_shell(backend)
    terminal = core.terminals['t1']
    terminal['cwd'] = '/original-launch'
    terminal['foreground'] = {'pid': terminal['pid'], 'argv': ['/bin/bash', '-l'], 'cwd': '/work'}
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan'] == plan()
    assert len([m for m, _ in core.calls if m == 'terminal.kill']) == 1


@pytest.mark.parametrize('resume,legacy', [(False, False), (True, False), (True, True)])
def test_r1_foreground_report_can_disappear_with_a_different_launch_directory(backend, resume, legacy):
    core = r1_shell(backend)
    terminal = core.terminals['t1']
    terminal['cwd'] = '/original-launch'
    terminal['foreground'] = {'pid': terminal['pid'], 'argv': ['/bin/bash', '-l'], 'cwd': '/work'}
    if resume:
        def interrupt():
            raise native.NativeError('synthetic interruption')
        write = r1_on_intent(backend, interrupt)
        with pytest.raises(native.NativeError):
            backend.restore_current()
        backend.store.write = write
        if legacy:
            saved = backend.store.read('receipt-testtx.json')
            saved['pending'].pop('identity')
            write('receipt-testtx.json', saved)
        terminal['foreground'] = None
    else:
        r1_on_intent(backend, lambda: terminal.update(foreground=None))
    backend.restore_current()
    assert backend.store.read('manifest.json')['plan'] == plan()
    assert len([m for m, _ in core.calls if m == 'terminal.kill']) == 1


def test_r1_rechecks_actual_argv_after_final_document_observation(backend):
    core = r1_shell(backend)
    document = backend._document
    pending_observations = 0
    def changed_after_read():
        nonlocal pending_observations
        value = document()
        receipt = backend.store.read('receipt-testtx.json')
        if (receipt.get('pending') or {}).get('operation') == 'terminal.kill':
            pending_observations += 1
            if pending_observations == 2:
                synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '--login'])
        return value
    backend._document = changed_after_read
    with pytest.raises(native.NativeError, match='^core repair guard argv changed$'):
        backend.restore_current()
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set') for m, _ in core.calls)


@pytest.mark.parametrize('change', ['document', 'version', 'argv', 'labels'])
def test_r1_inventory_observation_is_followed_by_identity_and_document_guards(backend, change):
    core = r1_shell(backend)
    scan = backend.scan
    def racing_scan(wanted):
        result = scan(wanted)
        receipt = backend.store.read('receipt-testtx.json')
        if (receipt.get('pending') or {}).get('operation') == 'terminal.kill':
            if change == 'document':
                core.document['PRIVATE'] = 'PRIVATE'
            elif change == 'version':
                core.version += 1
            elif change == 'argv':
                synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '--login'])
            else:
                core.terminals['t1']['labels']['remote-herdr-PRIVATE'] = 'PRIVATE'
        return result
    backend.scan = racing_scan
    with pytest.raises(native.NativeError) as error:
        backend.restore_current()
    assert 'PRIVATE' not in str(error.value)
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set') for m, _ in core.calls)
    assert backend.store.read('receipt-testtx.json')['pending']['operation'] == 'terminal.kill'


def test_cas_edit_after_prepare_retains_private_backup(backend):
    core = FakeCore(backend)
    old = {'spaces': []}
    core.document = old
    receipt = backend.prepare('herdr-core', plan(), 'testtx', replace_target=True)
    core.document = {'spaces': [{'foreign': 'private'}]}
    core.version += 1
    with pytest.raises(native.NativeError, match='changed'):
        backend.restore('herdr-core', plan(), 'testtx', receipt)
    assert backend.store.read(receipt['backup'])['document'] == old
    assert not any(m == 'terminal.run' for m, _ in core.calls)


@pytest.mark.parametrize('rebooted_to_shell', [False, True])
def test_uncertain_create_discovered_by_labels_only_on_recovery(backend, rebooted_to_shell):
    core = FakeCore(backend)
    receipt = backend.prepare('herdr-core', plan(), 'testtx')
    original = core.rpc

    def uncertain(method, params):
        result = original(method, params)
        if method == 'terminal.run':
            raise native.NativeError('core outcome uncertain')
        return result

    backend.core = uncertain
    with pytest.raises(native.NativeError):
        backend.restore('herdr-core', plan(), 'testtx', receipt)
    assert len(core.terminals) == 1
    backend.store.write('manifest.json', {'schema_version': 1, 'runtime': 'herdr-core',
                                        'plan': plan(), 'receipt': receipt, 'txid': 'testtx'})
    backend.core = original
    core.terminals['t1']['labels'].update(app_labels())
    if rebooted_to_shell:
        core.active = False
        synthetic_process(backend, 31, ['/bin/bash', '-l'])
    backend.restore_current()
    address = 't2' if rebooted_to_shell else 't1'
    assert len(core.terminals) == (2 if rebooted_to_shell else 1)
    assert backend.store.read('manifest.json')['receipt']['terminals'] == {'s0-t0-p0': address}


def test_core_stop_proves_clients_gone_without_stopping_shared_service(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    captured = backend.capture('herdr-core')
    assert backend.stop('herdr-core', captured) == plan()
    assert not backend.scan({'ses_abc'})
    assert not core.active
    commands = [argv for method, argv in core.calls if method == 'command']
    assert commands == [['herdr-core', 'server', 'stop', '--json']]


def test_socket_absence_does_not_prove_source_client_exit(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    captured = backend.capture('herdr-core')

    def dont_kill(method, params):
        if method == 'terminal.kill':
            core.terminals['t1']['state'] = 'finished'
            return core.terminals['t1']
        return core.rpc(method, params)

    backend.core = dont_kill
    with pytest.raises(native.NativeError, match='proof'):
        backend.stop('herdr-core', captured)
    assert not core.active
    assert backend.scan({'ses_abc'})


def test_unknown_sqlite_schema_blocks_before_launch(backend):
    core = FakeCore(backend)
    path = backend.home / '.local/share/opencode/opencode.db'
    with sqlite3.connect(path) as db:
        db.execute('DROP TABLE session')
        db.execute('CREATE TABLE session (unknown TEXT)')
    with pytest.raises(native.NativeError, match='schema'):
        backend.prepare('herdr-core', plan(), 'testtx')
    assert not core.calls


def test_foreign_executable_cannot_impersonate_session_client(backend):
    synthetic_process(backend, 31, ['/usr/bin/vim', '--session', 'ses_abc'])
    with pytest.raises(native.NativeError, match='executable'):
        backend._coverage(plan())


def test_native_command_failure_is_private_once_and_env_is_sanitized(backend, monkeypatch):
    calls = []

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        raise RuntimeError('private native diagnostic and path')

    monkeypatch.setattr(native.subprocess, 'Popen', popen)
    with pytest.raises(native.NativeError) as error:
        native.Native.command(backend, ['herdr-core', 'server', 'start', '--json'])
    assert str(error.value) == 'native observation or mutation uncertain'
    assert len(calls) == 1
    env = calls[0][1]['env']
    assert 'HC_SESSION' not in env and 'HC_SOCKET' not in env
    assert set(env) <= {'HOME', 'PATH', 'LANG', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME',
                        'XDG_DATA_HOME', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS'}


class FakeTui:
    def __init__(self, backend, active=True):
        self.backend = backend
        self.snapshot_override: dict | None = None
        self.active = active
        self.saved = native.layout.to_tui_snapshot(plan())
        backend.snapshot_path.parent.mkdir(parents=True)
        backend.snapshot_path.write_text(json.dumps(self.saved))
        if active:
            synthetic_process(backend, 31, wrapper_argv(backend))
        backend.endpoint_present = lambda target: target == 'tui' and self.active
        backend.tui = self.rpc
        backend.command = self.command
        backend.poll_seconds = 0
        self.calls = []
        self.lose_save = False

    def snapshot(self):
        if self.snapshot_override is not None:
            return self.snapshot_override
        # Source-defined full wire example (not a recorded runtime response):
        # herdrdev/herdr@2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01
        # src/api/schema/{session,workspaces,tabs,panes,agents}.rs.
        # Required fields are present; omitted Option/empty-map/false fields
        # follow serde skip_serializing_if, not an invented minimal schema.
        identity = {'source': 'herdr:opencode', 'agent': 'opencode', 'kind': 'id', 'value': 'ses_abc'}
        return {'version': '0.9.5', 'protocol': 1,
                'focused_workspace_id': 'wid', 'focused_tab_id': 'tid', 'focused_pane_id': 'pid',
                'workspaces': [{'workspace_id': 'wid', 'number': 1, 'label': 'Space',
                                'focused': True, 'pane_count': 1, 'tab_count': 1,
                                'active_tab_id': 'tid', 'agent_status': 'idle'}],
                'tabs': [{'workspace_id': 'wid', 'tab_id': 'tid', 'number': 1, 'label': 'Tab',
                          'focused': True, 'pane_count': 1, 'agent_status': 'idle'}],
                'panes': [{'workspace_id': 'wid', 'tab_id': 'tid', 'pane_id': 'pid',
                           'terminal_id': 'term1', 'focused': True, 'cwd': '/work',
                           'foreground_cwd': '/work', 'agent': 'opencode',
                           'agent_status': 'idle', 'agent_session': identity, 'revision': 1}],
                'agents': [{'workspace_id': 'wid', 'tab_id': 'tid', 'pane_id': 'pid',
                            'terminal_id': 'term1', 'agent': 'opencode', 'agent_status': 'idle',
                            'focused': True, 'interactive_ready': True, 'state_change_seq': 1,
                            'cwd': '/work', 'foreground_cwd': '/work',
                            'agent_session': identity, 'revision': 1}],
                'layouts': [{'workspace_id': 'wid', 'tab_id': 'tid', 'zoomed': False,
                             'area': {'x': 0, 'y': 0, 'width': 120, 'height': 40},
                             'focused_pane_id': 'pid', 'panes': [{'pane_id': 'pid', 'focused': True,
                             'rect': {'x': 0, 'y': 0, 'width': 120, 'height': 40}}], 'splits': []}]}

    def rpc(self, method, params):
        if method == 'session.snapshot':
            return {'type': 'session_snapshot', 'snapshot': self.snapshot()}
        if method == 'layout.export':
            return {'type': 'layout_export', 'layout': {'workspace_id': 'wid', 'tab_id': 'tid',
                    'zoomed': False, 'focused_pane_id': 'pid',
                    'root': {'type': 'pane', 'pane_id': 'pid', 'cwd': '/work'}}}
        if method == 'pane.process_info':
            return {'type': 'pane_process_info', 'process_info': {'pane_id': 'pid', 'shell_pid': 20,
                    'foreground_process_group_id': 31, 'tty': '/dev/pts/1',
                    'foreground_processes': [{'pid': 31, 'name': 'opencode',
                                             'argv0': str(self.backend.home / '.opencode/bin/opencode'),
                                             'cwd': '/work'}]}}
        raise AssertionError('unexpected fake TUI RPC')

    def command(self, argv, timeout=30):
        self.calls.append(list(argv))
        if argv == ['herdr', 'session', 'stop', 'default', '--json']:
            self.active = False
            for pid in (20, 31):
                directory = self.backend.proc_root / str(pid)
                for name in ('stat', 'cmdline', 'cwd', 'status'):
                    (directory / name).unlink()
                directory.rmdir()
            saved = copy.deepcopy(self.saved)
            if self.lose_save:
                saved['workspaces'][0]['tabs'][0]['custom_name'] = 'lost original label'
            self.backend.snapshot_path.write_text(json.dumps(saved))
        elif argv == ['/usr/bin/systemctl', '--user', 'start', 'remote-herdr-tui.service']:
            self.active = True
            synthetic_process(self.backend, 31, wrapper_argv(self.backend))
        elif argv != ['/usr/bin/systemctl', '--user', 'stop', 'remote-herdr-tui.service']:
            raise AssertionError('unexpected fake TUI command')
        return {}


def test_tui_capture_observational_api_never_written_as_native_file(backend):
    tui = FakeTui(backend)
    before = backend.snapshot_path.read_bytes()
    captured = backend.capture('tui')
    assert captured['plan'] == plan()
    assert captured['api']['version'] == '0.9.5'
    assert backend.snapshot_path.read_bytes() == before
    assert backend.stop('tui', captured) == plan()
    assert json.loads(backend.snapshot_path.read_text())['version'] == 3
    assert not backend.scan({'ses_abc'})
    assert not any('opencode' in arg for argv in tui.calls for arg in argv)


def public_tui(backend, name=None, tab_name=None):
    tui = FakeTui(backend)
    space = tui.saved['workspaces'][0]
    space.update(id='synthetic', custom_name=name, public_tab_numbers=[3], public_pane_numbers={'0': 7})
    space['tabs'][0]['custom_name'] = tab_name
    backend.snapshot_path.write_text(json.dumps(tui.saved))
    api = tui.snapshot()
    api['workspaces'][0].update(workspace_id='synthetic', label='~' if name is None else name)
    api['tabs'][0].update(workspace_id='synthetic', tab_id='synthetic:t3', number=3,
                          label='1' if tab_name is None else tab_name)
    for key in ('panes', 'agents'):
        api[key][0].update(workspace_id='synthetic', tab_id='synthetic:t3', pane_id='synthetic:p7')
    tui.snapshot_override = api
    rpc = tui.rpc
    def public_rpc(method, params):
        result = rpc(method, params)
        if method == 'layout.export':
            result['layout'].update(workspace_id='synthetic', tab_id='synthetic:t3')
            result['layout']['root']['pane_id'] = 'synthetic:p7'
        elif method == 'pane.process_info':
            result['process_info']['pane_id'] = 'synthetic:p7'
        return result
    backend.tui = public_rpc
    return tui


@pytest.mark.parametrize('automatic', [False, True])
def test_legacy_tui_capture_uses_retained_backup_for_naming(backend, automatic):
    if automatic:
        public_tui(backend)
    else:
        FakeTui(backend)
    captured = backend.capture('tui')
    del captured['tui_names']
    assert backend.stop('tui', captured) == captured['plan']


@pytest.mark.parametrize('name,tab_name', [(None, None), ('', ''), (' ', ' '), ('~', '1'), ('1', '~')])
def test_tui_public_identity_preserves_nullable_and_explicit_names(backend, name, tab_name):
    tui = public_tui(backend, name, tab_name)
    before = backend.snapshot_path.read_bytes()
    captured = backend.capture('tui')
    assert captured['plan']['spaces'][0]['name'] == ('' if name is None else name)
    assert captured['plan']['spaces'][0]['tabs'][0]['name'] == ('' if tab_name is None else tab_name)
    assert captured['tui_names'] == [{'custom_name': name, 'tabs': [tab_name]}]
    assert backend.snapshot_path.read_bytes() == before
    assert backend.store.read(captured['backup'])['snapshot'] == tui.saved


@pytest.mark.parametrize('change', ['workspace', 'tab', 'pane', 'export-workspace', 'missing', 'tab-label'])
def test_tui_automatic_names_require_exact_persisted_identity(backend, change):
    tui = public_tui(backend)
    api = tui.snapshot_override
    assert api is not None
    if change == 'workspace': api['workspaces'][0]['workspace_id'] = 'stale'
    elif change == 'tab': api['tabs'][0]['tab_id'] = 'synthetic:t2'
    elif change == 'pane':
        api['panes'][0]['pane_id'] = api['agents'][0]['pane_id'] = 'synthetic:p8'
    elif change == 'tab-label': api['tabs'][0]['label'] = '3'
    elif change == 'missing':
        tui.saved['workspaces'][0].pop('id')
        backend.snapshot_path.write_text(json.dumps(tui.saved))
    else:
        rpc = backend.tui
        def stale(method, params):
            result = rpc(method, params)
            if method == 'layout.export': result['layout']['workspace_id'] = 'stale'
            return result
        backend.tui = stale
    with pytest.raises((native.NativeError, ValueError)):
        backend.capture('tui')
    assert not tui.calls


@pytest.mark.parametrize('boundary', ['before-stop', 'during-intent', 'poststop'])
@pytest.mark.parametrize('target', ['workspace', 'tab'])
def test_tui_null_to_explicit_empty_rename_refuses(backend, boundary, target):
    tui = public_tui(backend)
    captured = backend.capture('tui')
    def rename():
        item = tui.saved['workspaces'][0]
        if target == 'tab': item = item['tabs'][0]
        item['custom_name'] = ''
        backend.snapshot_path.write_text(json.dumps(tui.saved))
        assert tui.snapshot_override is not None
        tui.snapshot_override['workspaces' if target == 'workspace' else 'tabs'][0]['label'] = ''
    if boundary == 'before-stop': rename()
    elif boundary == 'during-intent':
        write = backend.store.write
        def persist(name, value):
            write(name, value)
            if name == 'source-stop.json' and value.get('pending') == {'operation': 'tui.stop'}: rename()
        backend.store.write = persist
    else:
        command = backend.command
        def stopped(argv, timeout=30):
            result = command(argv, timeout)
            if argv[:3] == ['herdr', 'session', 'stop']: rename()
            return result
        backend.command = stopped
    with pytest.raises(native.NativeError):
        backend.stop('tui', captured)
    if boundary != 'poststop': assert not tui.calls


def test_tui_legacy_explicit_names_keep_strict_fallback_and_optional_export_workspace(backend):
    tui = FakeTui(backend)
    rpc = backend.tui
    def legacy(method, params):
        result = rpc(method, params)
        if method == 'layout.export': result['layout'].pop('workspace_id')
        return result
    backend.tui = legacy
    assert backend.capture('tui')['plan'] == plan()
    api = tui.snapshot()
    api['workspaces'][0]['label'] = 'Space '
    tui.snapshot_override = api
    with pytest.raises(native.NativeError): backend.capture('tui')
    assert not tui.calls


def test_tui_automatic_name_never_falls_back_even_when_display_equals_empty(backend):
    tui = FakeTui(backend)
    tui.saved['workspaces'][0]['custom_name'] = None
    backend.snapshot_path.write_text(json.dumps(tui.saved))
    api = tui.snapshot()
    api['workspaces'][0]['label'] = ''
    tui.snapshot_override = api
    with pytest.raises(native.NativeError) as error: backend.capture('tui')
    assert str(error.value) == 'native observation or mutation uncertain'
    assert not tui.calls


@pytest.mark.parametrize('change', ['workspace-count', 'workspace-count-bool', 'automatic-label-type'])
def test_tui_public_binding_rejects_invalid_workspace_observation(backend, change):
    tui = public_tui(backend)
    api = tui.snapshot_override
    assert api is not None
    if change == 'automatic-label-type': api['workspaces'][0]['label'] = None
    else: api['workspaces'][0]['pane_count'] = True if change.endswith('bool') else 2
    with pytest.raises(native.NativeError): backend.capture('tui')
    assert not tui.calls


@pytest.mark.parametrize('change', [None, 'direction', 'ratio', 'order', 'cwd', 'session'])
def test_tui_public_binding_proves_ordered_topology_and_pane_identity(backend, change):
    tui = public_tui(backend)
    space = tui.saved['workspaces'][0]
    tab = space['tabs'][0]
    # Equal pane cwds make ordering proof depend on public identity, not cwd.
    tab['panes']['42'] = {'cwd': '/work'}
    space['public_pane_numbers']['42'] = 9
    tab['layout'] = {'Split': {'direction': 'Vertical', 'ratio': 0.3,
                              'first': {'Pane': 42}, 'second': {'Pane': 0}}}
    backend.snapshot_path.write_text(json.dumps(tui.saved))
    api = tui.snapshot_override
    assert api is not None
    api['workspaces'][0]['pane_count'] = api['tabs'][0]['pane_count'] = 2
    api['panes'].append({'workspace_id': 'synthetic', 'tab_id': 'synthetic:t3',
                         'pane_id': 'synthetic:p9', 'cwd': '/work'})
    root = {'type': 'split', 'direction': 'down', 'ratio': 0.3,
            'first': {'type': 'pane', 'pane_id': 'synthetic:p9'},
            'second': {'type': 'pane', 'pane_id': 'synthetic:p7'}}
    if change == 'direction': root['direction'] = 'right'
    elif change == 'ratio': root['ratio'] = 0.7
    elif change == 'order': root['first'], root['second'] = root['second'], root['first']
    elif change == 'cwd': api['panes'][1]['cwd'] = '/stale'
    elif change == 'session':
        for key in ('panes', 'agents'):
            api[key][0]['agent_session']['value'] = 'ses_Changed'
    rpc = backend.tui
    def split_rpc(method, params):
        result = rpc(method, params)
        if method == 'layout.export': result['layout']['root'] = copy.deepcopy(root)
        elif method == 'pane.process_info': result['process_info']['pane_id'] = params['pane_id']
        return result
    backend.tui = split_rpc
    if change is None:
        value, _, _ = backend._tui_live()
        assert value['spaces'][0]['tabs'][0]['root']['axis'] == 'column'
        assert value['spaces'][0]['tabs'][0]['panes'][0]['session_id'] is None
    else:
        with pytest.raises(native.NativeError):
            backend.capture('tui')
    assert not tui.calls


def test_tui_unnamed_tabs_display_position_not_public_number(backend):
    tui = public_tui(backend)
    space = tui.saved['workspaces'][0]
    space['public_tab_numbers'] = [1, 3]
    space['public_pane_numbers']['42'] = 9
    space['tabs'].append({'custom_name': None, 'root_pane': 42, 'layout': {'Pane': 42},
                          'panes': {'42': {'cwd': '/other'}}})
    backend.snapshot_path.write_text(json.dumps(tui.saved))
    api = tui.snapshot_override
    assert api is not None
    api['workspaces'][0].update(tab_count=2, pane_count=2)
    api['tabs'][0].update(tab_id='synthetic:t1', number=1)
    for key in ('panes', 'agents'): api[key][0]['tab_id'] = 'synthetic:t1'
    api['tabs'].append({'workspace_id': 'synthetic', 'tab_id': 'synthetic:t3',
                        'number': 3, 'label': '2', 'pane_count': 1})
    api['panes'].append({'workspace_id': 'synthetic', 'tab_id': 'synthetic:t3',
                         'pane_id': 'synthetic:p9', 'cwd': '/other'})
    rpc = backend.tui
    def tabs_rpc(method, params):
        result = rpc(method, params)
        if method == 'layout.export':
            result['layout']['tab_id'] = params['tab_id']
            if params['tab_id'] == 'synthetic:t3': result['layout']['root']['pane_id'] = 'synthetic:p9'
        elif method == 'pane.process_info': result['process_info']['pane_id'] = params['pane_id']
        return result
    backend.tui = tabs_rpc
    value, _, _ = backend._tui_live()
    assert [tab['name'] for tab in value['spaces'][0]['tabs']] == ['', '']
    api['tabs'][1]['label'] = '3'
    with pytest.raises(native.NativeError): backend._tui_live()


def test_tui_invalid_poststop_save_blocks_handoff(backend):
    tui = FakeTui(backend)
    captured = backend.capture('tui')
    tui.lose_save = True
    with pytest.raises(native.NativeError, match='saved layout'):
        backend.stop('tui', captured)
    assert backend.store.read(captured['backup'])['snapshot'] == tui.saved


@pytest.mark.parametrize('boundary', ['before-stop', 'during-intent'])
@pytest.mark.parametrize('change', ['foreign-program', 'reused-pid'])
def test_tui_stop_rechecks_actual_foreground_after_durable_intent(backend, boundary, change):
    tui = FakeTui(backend)
    value = plan()
    tab = value['spaces'][0]['tabs'][0]
    tab['panes'].append({'key': 's0-t0-p1', 'cwd': '/work', 'session_id': None})
    tab['root'] = {'axis': 'row', 'ratio': 0.5, 'children': [
        {'pane': 's0-t0-p0'}, {'pane': 's0-t0-p1'}]}
    synthetic_process(backend, 40, ['/bin/bash', '-l'])
    facts = [tui.rpc('pane.process_info', {})['process_info'],
             {'pane_id': 'plain', 'shell_pid': 40,
              'foreground_processes': [{'pid': 40, 'name': 'bash', 'cwd': '/work'}]}]
    backend._tui_live = lambda: (copy.deepcopy(value), {}, copy.deepcopy(facts))
    captured = backend.capture('tui')
    def mutate():
        argv = ['/usr/bin/vim'] if change == 'foreign-program' else ['/bin/bash', '-l']
        synthetic_process(backend, 40, argv, ticks=99 if change == 'reused-pid' else 10)
    if boundary == 'before-stop':
        mutate()
    else:
        publish = backend.store.write
        def write(name, document):
            publish(name, document)
            if name == 'source-stop.json' and document.get('pending') == {'operation': 'tui.stop'}:
                mutate()
        backend.store.write = write
    with pytest.raises(native.NativeError):
        backend.stop('tui', captured)
    assert not tui.calls


def test_tui_target_requires_backup_and_live_identity_readiness(backend):
    tui = FakeTui(backend, active=False)
    with pytest.raises(native.NativeError, match='approval'):
        backend.prepare('tui', plan(), 'testtx')
    receipt = backend.prepare('tui', plan(), 'testtx', replace_target=True)
    assert backend.store.read(receipt['backup'])['snapshot'] == tui.saved
    receipt = backend.restore('tui', plan(), 'testtx', receipt)
    backend.verify('tui', plan(), receipt)
    assert backend.snapshot_path.stat().st_mode & 0o777 == 0o600
    assert json.loads(backend.snapshot_path.read_text())['version'] == 3
    assert tui.calls == [['/usr/bin/systemctl', '--user', 'start', 'remote-herdr-tui.service']]


@pytest.mark.parametrize('change', ['duplicate_agent', 'foreign_agent', 'missing_identity'])
def test_tui_unknown_or_duplicate_agent_views_refuse_before_stop(backend, change):
    tui = FakeTui(backend)
    original = tui.snapshot()
    if change == 'duplicate_agent':
        original['agents'].append(copy.deepcopy(original['agents'][0]))
    elif change == 'foreign_agent':
        original['panes'][0]['agent'] = 'other-agent'
    else:
        original['panes'][0].pop('agent_session')
    tui.snapshot_override = original
    with pytest.raises(native.NativeError):
        backend.capture('tui')
    assert not tui.calls


@pytest.mark.parametrize('mode', [0o644, 0o700, 0o775, 0o4755])
def test_binary_mode_contract(backend, mode):
    (backend.home / '.local/bin/herdr-core').chmod(mode)
    with pytest.raises(native.NativeError, match='binary attributes'):
        backend.preflight('herdr-core')
    assert not backend.calls


def test_unknown_pin_fields_and_owned_document_edits_refuse(backend):
    pin_path = backend.home / '.config/dotfiles-ai/herdr-runtime.json'
    pins = json.loads(pin_path.read_text())
    pins['credentials'] = 'private'
    pin_path.write_text(json.dumps(pins))
    with pytest.raises(native.NativeError, match='pins'):
        backend.preflight('herdr-core')
    assert not backend.calls
    backend.store.write('owned-herdr-core.json', {'document': {'spaces': []}})
    with pytest.raises(native.NativeError, match='edits'):
        backend._owned_target('herdr-core', {'spaces': [{'foreign': 'private'}]}, True)


def test_core_layout_capture_preserves_labels_order_identity_and_binary_geometry(backend):
    core = FakeCore(backend)
    p = plan()
    tab = p['spaces'][0]['tabs'][0]
    tab['panes'].append({'key': 's0-t0-p1', 'cwd': '/other', 'session_id': None})
    tab['root'] = {'axis': 'column', 'ratio': 0.3,
                   'children': [{'pane': 's0-t0-p1'}, {'pane': 's0-t0-p0'}]}
    p['spaces'].append({'name': 'Second', 'directory': '/second', 'tabs': []})
    receipt = backend.prepare('herdr-core', p, 'testtx')
    receipt = backend.restore('herdr-core', p, 'testtx', receipt)
    captured = backend.capture('herdr-core')
    assert backend._semantic(captured['plan']) == backend._semantic(p)
    assert core.document is not None
    assert core.document['spaces'][0]['tabs'][0]['root']['children'][0]['content']['terminal'] == 't2'
    assert [s['name'] for s in core.document['spaces']] == ['Space', 'Second']
    root = core.document['spaces'][0]['tabs'][0]['root']
    root['type'] = 'stack'
    with pytest.raises(native.NativeError, match='unsupported'):
        backend.capture('herdr-core')


@pytest.mark.parametrize('effect_completed', [False, True])
def test_source_stop_uncertainty_is_persisted_and_not_blindly_retried(backend, effect_completed):
    core = FakeCore(backend)
    manifest_for(backend, core)
    captured = backend.capture('herdr-core')
    original = backend.core
    kills = []

    def uncertain(method, params):
        if method == 'terminal.kill':
            kills.append(method)
            if effect_completed:
                original(method, params)
            raise native.NativeError('core outcome uncertain')
        return original(method, params)

    backend.core = uncertain
    with pytest.raises(native.NativeError):
        backend.stop('herdr-core', captured)
    assert backend.store.read('source-stop.json')['pending']['operation'] == 'terminal.kill'
    with pytest.raises(native.NativeError, match='recovery'):
        backend.stop('herdr-core', captured)
    assert kills == ['terminal.kill']


def test_orphan_plain_shell_is_retained_when_source_stops(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    core.terminals['t9'] = {'address': 't9', 'pid': 20, 'state': 'live', 'foreground': None,
                            'cwd': '/work', 'argv': ['/bin/bash', '-l'], 'labels': {}}
    captured = backend.capture('herdr-core')
    backend.stop('herdr-core', captured)
    assert core.terminals['t9']['state'] == 'live'
    assert (backend.proc_root / '20/stat').exists()
    assert [params['terminal'] for method, params in core.calls if method == 'terminal.kill'] == ['t1']


def test_absent_selection_uses_compatibility_default(backend):
    backend.config_path.unlink()
    assert backend.selected() == 'tui'


@pytest.mark.parametrize('operation', ['capture', 'preflight', 'prepare'])
def test_core_stored_shell_actual_foreign_program_refused(backend, operation):
    core = FakeCore(backend)
    core.document = native.layout.to_app_document(plan(None), {'s0-t0-p0': 't1'})
    core.terminals['t1'] = {'address': 't1', 'pid': 20, 'state': 'live', 'foreground': None,
                            'cwd': '/work', 'argv': ['/bin/bash', '-l'], 'labels': {}}
    synthetic_process(backend, 20, ['/usr/bin/vim'])
    before = copy.deepcopy(core.terminals), copy.deepcopy(core.document)
    with pytest.raises(native.NativeError, match='foreign live program'):
        if operation == 'capture':
            backend.capture('herdr-core')
        elif operation == 'preflight':
            backend.preflight('herdr-core', replace_target=True)
        else:
            backend.prepare('herdr-core', plan(None), 'testtx', replace_target=True)
    assert (core.terminals, core.document) == before
    assert not any(m in ('terminal.kill', 'terminal.run', 'doc.set', 'command') for m, _ in core.calls)


@pytest.mark.parametrize('change', ['exec', 'reuse', 'metadata', 'gone'])
def test_core_shell_drift_after_capture_refuses_before_kill(backend, change):
    core = FakeCore(backend)
    manifest_for(backend, core, plan(None))
    captured = backend.capture('herdr-core')
    pid = core.terminals['t1']['pid']
    if change == 'exec':
        synthetic_process(backend, pid, ['/usr/bin/vim'])
    elif change == 'reuse':
        synthetic_process(backend, pid, ['/bin/bash', '-l'], ticks=11)
    elif change == 'metadata':
        core.terminals['t1']['pid'] = 20
    else:
        (backend.proc_root / str(pid) / 'cmdline').unlink()
    before = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.stop('herdr-core', captured)
    assert not any(m in ('terminal.kill', 'command') for m, _ in core.calls[before:])


def test_core_owned_user_rename_reconciled_without_overwriting_manifest(backend):
    core = FakeCore(backend)
    manifest = manifest_for(backend, core)
    assert isinstance(core.document, dict)
    core.document['spaces'][0]['name'] = 'User renamed'
    core.version += 1
    captured = backend.capture('herdr-core')
    expected = copy.deepcopy(core.document)
    final = backend.stop('herdr-core', captured)
    assert final['spaces'][0]['name'] == 'User renamed'
    assert backend.store.read('owned-herdr-core.json') == {'document': expected}
    assert backend.store.read('manifest.json') == manifest
    backend.prepare('herdr-core', final, 'returntx')
    assert isinstance(core.document, dict)
    core.document['spaces'][0]['name'] = 'Unexplained later edit'
    core.version += 1
    with pytest.raises(native.NativeError, match='edits'):
        backend.prepare('herdr-core', final, 'latertx', replace_target=True)


@pytest.mark.parametrize('source', ['tui', 'herdr-core'])
def test_reconcile_stopped_observes_without_replaying_or_advancing_intent(backend, source):
    if source == 'tui':
        fake = FakeTui(backend)
        backend.store.write('owned-tui.json', {'document': fake.saved})
    else:
        fake = FakeCore(backend)
        manifest_for(backend, fake)
    captured = backend.capture(source)
    with pytest.raises(native.NativeError, match='proof'):
        backend.reconcile_stopped(source, captured)
    backend.stop(source, captured)
    backend.store.write('source-stop.json', {'pending': {'operation': 'uncertain'}})
    backend.store.write('journal.json', {'sentinel': True})
    before = copy.deepcopy(fake.calls)
    assert backend.reconcile_stopped(source, captured) == captured['plan']
    assert fake.calls == before
    assert backend.store.read('source-stop.json') == {'pending': {'operation': 'uncertain'}}
    assert backend.store.read('journal.json') == {'sentinel': True}


def test_reconcile_unowned_core_does_not_adopt_document(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    captured = backend.capture('herdr-core')
    del backend.store.values['owned-herdr-core.json']
    backend.stop('herdr-core', captured)
    assert backend.store.read('owned-herdr-core.json') is None


@pytest.mark.parametrize('change', ['exec', 'reuse', 'version', 'metadata'])
def test_core_stop_rechecks_after_durable_kill_intent(backend, change):
    core = FakeCore(backend)
    manifest_for(backend, core, plan(None))
    captured = backend.capture('herdr-core')
    write = backend.store.write

    def drift_on_intent(name, value):
        write(name, value)
        if name != 'source-stop.json' or (value.get('pending') or {}).get('operation') != 'terminal.kill':
            return
        pid = core.terminals['t1']['pid']
        if change == 'exec':
            synthetic_process(backend, pid, ['/usr/bin/vim'])
        elif change == 'reuse':
            synthetic_process(backend, pid, ['/bin/bash', '-l'], ticks=11)
        elif change == 'version':
            core.version += 1
        else:
            core.terminals['t1']['argv'] = ['bash']

    backend.store.write = drift_on_intent
    before = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.stop('herdr-core', captured)
    assert not any(m in ('terminal.kill', 'command') for m, _ in core.calls[before:])


def test_absent_core_source_cannot_be_captured(backend):
    core = FakeCore(backend)
    core.active = False
    with pytest.raises(native.NativeError, match='endpoint'):
        backend.capture('herdr-core')
    assert not core.calls


@pytest.mark.parametrize('proof', ['pid', 'session'])
def test_reconcile_stopped_requires_process_and_exact_session_absence(backend, proof):
    core = FakeCore(backend)
    manifest_for(backend, core)
    captured = backend.capture('herdr-core')
    core.active = False
    if proof == 'session':
        pid = captured['pids'][0]['pid']
        directory = backend.proc_root / str(pid)
        for name in ('stat', 'cmdline', 'cwd', 'status'):
            (directory / name).unlink()
        directory.rmdir()
        synthetic_process(backend, 99, wrapper_argv(backend))
    before = copy.deepcopy(backend.store.values)
    with pytest.raises(native.NativeError):
        backend.reconcile_stopped('herdr-core', captured)
    assert backend.store.values == before


@pytest.mark.parametrize('server', ['http://127.0.0.1:4096', 'https://localhost:443', 'http://[::1]:4096'])
@pytest.mark.parametrize('auto', [False, True])
def test_wrapper_exec_contract_shared_by_core_and_process_proof(backend, server, auto):
    argv = wrapper_argv(backend, server=server, auto=auto)
    synthetic_process(backend, 31, argv)
    terminal = {'state': 'live', 'pid': 31, 'argv': argv, 'cwd': '/work'}
    assert backend._program(terminal) == ('ses_abc', '/work')
    assert backend._coverage(plan()) == [{'pid': 31, 'start_ticks': 10, 'session_id': 'ses_abc'}]
    with pytest.raises(native.NativeError, match='identity'):
        backend._client_argv(31, 'ses_other')


@pytest.mark.parametrize('server', ['http://external.example:4096', 'http://127.0.0.1',
    'http://127.0.0.1:0', 'http://127.0.0.1:65536', 'http://user@localhost:80',
    'http://localhost:80/path', 'http://localhost:80?x=1', 'http://localhost:80#x',
    'file://localhost:80', 'http://127.0.0.1.evil:80', 'http://localhost:80/'])
def test_wrapper_external_or_decorated_server_refused(backend, server):
    with pytest.raises(native.NativeError, match='server'):
        backend._session_argv(wrapper_argv(backend, server=server))


@pytest.mark.parametrize('tail', [
    ['--session', 'ses_abc', '--auto', '--auto'],
    ['--session', 'ses_abc', '--session', 'ses_other'],
    ['--auto', '--session', 'ses_abc'], ['--session=ses_abc'],
    ['--session', 'ses_abc', '--continue'], ['--session', 'ses_abc', '--model', 'foreign'],
    ['--session', 'ses_abc', '--server', 'http://localhost:80'],
    ['--session', 'ses_abc_suffix', '--unknown'], ['--session', 'invalid'],
])
def test_wrapper_unknown_duplicate_or_reordered_flags_refused(backend, tail):
    argv = wrapper_argv(backend)[:3] + tail
    with pytest.raises(native.NativeError):
        backend._session_argv(argv)


def test_wrapper_native_path_must_be_exact(backend):
    argv = wrapper_argv(backend)
    argv[0] = '/foreign/.opencode/bin/opencode'
    with pytest.raises(native.NativeError):
        backend._session_argv(argv)


def test_absent_core_preflight_defers_document_ownership_until_prepare(backend):
    core = FakeCore(backend)
    core.active = False
    core.document = {'spaces': [{'foreign': 'private'}]}
    backend.preflight('herdr-core')
    assert not core.calls
    with pytest.raises(native.NativeError, match='approval'):
        backend.prepare('herdr-core', plan(), 'testtx')
    assert not any(m in ('terminal.run', 'doc.set') for m, _ in core.calls)
    assert core.document == {'spaces': [{'foreign': 'private'}]}
    receipt = backend.prepare('herdr-core', plan(), 'approved', replace_target=True)
    assert backend.store.read(receipt['backup'])['document'] == core.document


@pytest.mark.parametrize(('direction', 'axis'), [('right', 'row'), ('down', 'column')])
@pytest.mark.parametrize('shell', [['/bin/bash', '-l'], ['/bin/sh']])
def test_pinned_api_split_direction_and_optional_process_argv(backend, direction, axis, shell):
    tui = FakeTui(backend)
    snapshot = tui.snapshot()
    snapshot['workspaces'][0]['pane_count'] = 2
    snapshot['tabs'][0]['pane_count'] = 2
    snapshot['panes'].append({'workspace_id': 'wid', 'tab_id': 'tid', 'pane_id': 'pid2',
        'terminal_id': 'term2', 'focused': False, 'cwd': '/work', 'agent_status': 'unknown', 'revision': 1})
    tui.snapshot_override = snapshot
    synthetic_process(backend, 40, shell)
    rpc = tui.rpc

    def split_rpc(method, params):
        if method == 'layout.export':
            result = rpc(method, params)
            result['layout']['root'] = {'type': 'split', 'direction': direction, 'ratio': 0.3,
                'first': {'type': 'pane', 'pane_id': 'pid', 'cwd': '/work'},
                'second': {'type': 'pane', 'pane_id': 'pid2', 'cwd': '/work'}}
            return result
        if method == 'pane.process_info' and params['pane_id'] == 'pid2':
            return {'type': 'pane_process_info', 'process_info': {'pane_id': 'pid2',
                'shell_pid': 40, 'foreground_process_group_id': 40, 'tty': '/dev/pts/2',
                'foreground_processes': [{'pid': 40, 'name': 'bash'}]}}
        return rpc(method, params)

    backend.tui = split_rpc
    captured = backend.capture('tui')
    root = captured['plan']['spaces'][0]['tabs'][0]['root']
    assert root['axis'] == axis and root['ratio'] == 0.3
    # API name alone cannot prove shell safety even when argv is absent.
    synthetic_process(backend, 40, ['/usr/bin/vim'])
    with pytest.raises(native.NativeError, match='unknown foreground'):
        backend.capture('tui')
    assert not tui.calls


@pytest.mark.parametrize(('argv', 'allowed'), [
    (['/bin/sh'], True),
    (['/bin/sh', '-c', 'printf must-not-run'], False),
    (['/bin/sh', '-l'], False),
    (['/bin/sh', '--login'], False),
    (['/bin/sh', '-i'], False),
    (['/bin/sh', ''], False),
    (['sh'], False),
    (['/usr/bin/sh'], False),
    (['/usr/bin/vim'], False),
])
def test_tui_default_posix_shell_requires_exact_argument_free_argv(backend, argv, allowed):
    synthetic_process(backend, 40, argv)
    facts = [{'shell_pid': 40, 'foreground_processes': [{'pid': 40, 'name': 'bash'}]}]
    if allowed:
        assert backend._tui_process_proofs(facts, []) == [
            {'pid': 40, 'start_ticks': 10, 'boot_id': backend.process_boot_id()}]
    else:
        with pytest.raises(native.NativeError, match='unknown foreground'):
            backend._tui_process_proofs(facts, [])
    assert not backend.calls
