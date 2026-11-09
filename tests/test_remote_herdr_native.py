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
    {'remote-herdr-owner': 'labelproof', 'remote-herdr-pane': 's0-t0-p0', 'foreign': ''},
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
    before = len(core.calls)
    with pytest.raises(native.NativeError, match='prior terminal creation requires recovery'):
        backend.restore('herdr-core', value, 'labelproof', receipt)
    assert not any(method in ('terminal.run', 'terminal.kill', 'doc.set') for method, _ in core.calls[before:])


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
        assert backend._tui_process_proofs(facts, []) == [{'pid': 40, 'start_ticks': 10}]
    else:
        with pytest.raises(native.NativeError, match='unknown foreground'):
            backend._tui_process_proofs(facts, [])
    assert not backend.calls
