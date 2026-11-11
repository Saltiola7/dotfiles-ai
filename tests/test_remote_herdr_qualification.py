"""Source-only checks, never execute a runtime, login, systemctl or proc read.

These tests do not certify native behavior; the mandatory hosted job does that.
"""
import ast
import copy
import http.client
import json
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import sys
import tomllib
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/remote_herdr_systemd'
WORKFLOW = ROOT / '.github/workflows/remote-herdr-runtime.yml'


def test_fixture_failure_diagnostics_never_include_native_output(monkeypatch):
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    def failed(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout='PRIVATE-REGISTRATION', stderr=(
            'PRIVATE-CREDENTIAL\nchezmoi: install-04-remote-opencode-service.sh: exit status 75'))
    monkeypatch.setattr(subprocess, 'run', failed)
    try:
        fixture['run']('must-not-execute')
    except fixture['CommandFailure'] as error:
        assert error.reason == 'install-04-remote-opencode-service.sh-exit-75'
        assert 'PRIVATE' not in str(error)
    else:
        raise AssertionError('native failure must not pass')
    # Failed core-restore observation may classify only fixed labels, never raw
    # native payloads. This is an in-memory adapter, not a native process probe.
    monkeypatch.syspath_prepend(str(ROOT / 'dot_local/share/dotfiles-ai/remote-herdr'))
    class State:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, name):
            if name == 'transaction.json':
                return {'phase': 'restore_pending', 'target': 'herdr-core', 'txid': 'fixture',
                        'plan': {'spaces': [{'tabs': [{'panes': [{'key': 'p0'}]}]}]}}
            return {'pending': None, 'terminals': {'p0': 't1'}}
    error_type = type('NativeError', (ValueError,), {})
    class Backend:
        refusal = ''
        def __init__(self, *args): pass
        def _other_off(self, target): pass
        def _terminal(self, address): return {}
        def _match_terminal(self, *args): raise error_type(self.refusal)
        def _safe_live_terminals(self, *args):
            raise AssertionError('failed terminal proof must stop observations')
    monkeypatch.setitem(fixture['cli'].__globals__, 'adapter', lambda: (lambda root: State(), Backend))
    for refusal, label in [('core terminal ownership mismatch', 'terminal-ownership'),
                           ('PRIVATE-NATIVE-DETAIL', 'unclassified-native-refusal')]:
        Backend.refusal = refusal
        try:
            fixture['cli']('must-not-execute')
        except fixture['CommandFailure'] as error:
            assert error.reason == 'controller-restore_pending-mapped-1-receipt-terminal-proof-' + label
            assert 'PRIVATE' not in str(error)
        else:
            raise AssertionError('failed CLI must stay failed')


def test_r1_observe_refusal_is_fixed_and_survives_poll_deadline(monkeypatch):
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    namespace = fixture['observe'].__globals__
    error_type = type('NativeError', (ValueError,), {})
    class Store:
        def __init__(self, root): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, name):
            return {'runtime': 'herdr-core', 'plan': {}, 'receipt': {}}
    class Backend:
        refusal = ''
        def __init__(self, *args): pass
        def _semantic(self, plan): return []
        def verify(self, *args): raise error_type(self.refusal)
    monkeypatch.setitem(namespace, 'adapter', lambda: (Store, Backend))
    labels = fixture['r1_refusal_labels']()
    assert set(labels.values()) == {'repair-' + field for field in (
        'binding', 'labels', 'pid', 'start-time', 'argv', 'directory', 'state',
        'exit', 'session', 'document-version', 'layout', 'identity-invalid')}
    for refusal, label in [*labels.items(), ('PRIVATE-PATH-SESSION-PAYLOAD',
                                            'verify-unclassified')]:
        Backend.refusal = refusal
        ticks = iter([0, 0, 2])
        monkeypatch.setattr(namespace['time'], 'monotonic', lambda: next(ticks))
        monkeypatch.setattr(namespace['time'], 'sleep', lambda seconds: None)
        try:
            fixture['wait'](lambda: fixture['observe']('herdr-core', {}), seconds=1)
        except fixture['CommandFailure'] as error:
            assert error.reason == label
            expected_step = 'observe-herdr-core-verify'
            if label == 'verify-unclassified':
                expected_step += '-unclassified'
            assert namespace['STEP'] == expected_step
            assert 'PRIVATE' not in error.reason
        else:
            raise AssertionError('observation refusal must survive deadline')


def test_r1_expected_raw_document_changes_only_selected_scalar(monkeypatch):
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    monkeypatch.syspath_prepend(str(ROOT / 'dot_local/share/dotfiles-ai/remote-herdr'))
    import layout
    # Use the real producer and its canonical keys, not assumed positional IDs.
    plan = {'schema_version': 1, 'spaces': [{'name': 'Synthetic', 'directory': '/fixture',
        'tabs': [{'name': 'Views', 'panes': [
            {'key': 's0-t0-p0', 'cwd': '/fixture', 'session_id': 'ses_synthetic0'},
            {'key': 's0-t0-p1', 'cwd': '/fixture', 'session_id': 'ses_synthetic1'}],
            'root': {'axis': 'row', 'ratio': 0.4, 'children': [
                {'pane': 's0-t0-p0'}, {'pane': 's0-t0-p1'}]}}]}]}
    document = layout.to_app_document(plan, {'s0-t0-p0': 't1', 's0-t0-p1': 't2'})
    document['metadata'] = {'opaque': [None, {'id': 'unrelated', 'terminal': 't1'}]}
    root = document['spaces'][0]['tabs'][0]['root']
    root['children'][0]['content']['opaque'] = {'preserved': True}
    root['children'][0]['size'] = {'weight': 7}
    baseline = copy.deepcopy(document)
    expected = copy.deepcopy(document)
    leaf = root['children'][0]['id']
    expected['spaces'][0]['tabs'][0]['root']['children'][0]['content']['terminal'] = 't3'
    assert fixture['expected_leaf_rebind'](document, leaf, 't1', 't3') == expected
    assert document == baseline
    for selected, old in [('missing', 't1'), (leaf, 't2')]:
        try:
            fixture['expected_leaf_rebind'](document, selected, old, 't3')
        except RuntimeError:
            pass
        else:
            raise AssertionError('unproven binding must refuse')


def test_r1_poll_keeps_specific_step_after_later_generic_failure(monkeypatch):
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    namespace = fixture['wait'].__globals__
    ticks = iter([0, 0, 1, 3])
    monkeypatch.setattr(namespace['time'], 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(namespace['time'], 'sleep', lambda seconds: None)
    attempts = 0
    def observation():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            namespace['STEP'] = 'observe-herdr-core-verify'
            raise fixture['CommandFailure']('repair-start-time')
        namespace['STEP'] = 'observe-herdr-core-manifest'
        raise RuntimeError('PRIVATE')
    try:
        fixture['wait'](observation, seconds=2)
    except fixture['CommandFailure'] as error:
        assert error.reason == 'repair-start-time'
        assert namespace['STEP'] == 'observe-herdr-core-verify'
    else:
        raise AssertionError('last specific proof must remain visible')


def test_r1_finished_facts_ignore_display_but_keep_exit_identity():
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    terminal = {'address': 't1', 'pid': 31, 'labels': {'owned': 'synthetic'},
                'argv': ['/bin/bash'], 'cwd': '/fixture', 'state': 'finished',
                'finished_ms': 7, 'reason': 'killed', 'exit_code': 143, 'exitcode': 143,
                'status': 'old'}
    changed = dict(terminal, status='new', title='new', seen_ms=99)
    facts = fixture['finished_terminal_facts']
    assert facts(changed) == facts(terminal)
    for key in ('pid', 'labels', 'argv', 'cwd', 'state', 'finished_ms', 'reason', 'exit_code', 'exitcode'):
        assert facts(dict(terminal, **{key: None})) != facts(terminal)


def test_r1_fault_fixture_uses_native_keep_and_installed_restore_only():
    source = (FIXTURE / 'verify-user.py').read_text()
    tree = ast.parse(source)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    function = functions['kept_shell_kill_recovery']
    body = ast.get_source_segment(source, function)
    assert body is not None
    calls = [n for n in ast.walk(function) if isinstance(n, ast.Call)]
    assert not any(isinstance(n.func, ast.Attribute) and n.func.attr in {
        'write', 'write_text', 'write_bytes', 'execute'} for n in calls)
    assert not any(isinstance(n.func, ast.Name) and n.func.id == 'write' for n in calls)
    for witness in ("os.getuid() == 1000 and Path.home() == HOME", "backend.capture('herdr-core')",
                    "backend._coverage(plan)", "manifest['receipt']['bindings'][key]",
                    "manifest['receipt']['terminals'][key]", "client_pid != pid",
                    "backend._client_argv(client_pid, pane['session_id'])",
                    "'exe').resolve() == NATIVE", 'os.pidfd_open(client_pid)',
                    'backend._pid_proofs([client_pid]) == client_proof',
                    "backend.process_cwd(client_pid) == pane['cwd']",
                    "terminal.get('keep') is True",
                    'signal.pidfd_send_signal(fd, signal.SIGKILL)',
                    "backend._actual_core_program(current) != (None, pane['cwd'])",
                    'backend._pids_absent(client_proof)', 'backend._shell_proof(current)',
                    "pending.pop('identity')", 'original_receipt(legacy_pid_fields(receipt))',
                    'backend._terminal(address) != snapshot', 'result = copy.deepcopy(result)',
                    "Controller(store, backend).restore()", "cli('restore')",
                    'original_core(method, params)', 'kills == 0',
                    "legacy_pid_fields({'pending': {'pids': shell_pids}})", "('identity' in pending) == lost_reply",
                    "backend._terminal(address)['state'] == 'live'",
                    "backend._pid_proofs([p['pid'] for p in shell_pids]) == shell_pids",
                    "backend._terminal(address)['state'] == 'finished'",
                    'backend._pids_absent(shell_pids)', 'fixture_captured_client_proofs(backend, before)',
                    'backend._pids_absent(captured_client)', "before['pids']",
                    'fixture_before_legacy_repair_kill(backend, baseline, leaf, source, pane,',
                    'shell_pids, txid, key, legacy)', 'forwarded == 1', 'backend.core = original_core',
                    "manifest['txid'] == txid and manifest['plan'] == plan",
                    "receipt['pending'] is None and receipt['repairs'] == {}",
                    "- addresses == {replacement}", '== other_clients',
                    'expected_leaf_rebind(baseline, leaf, address, replacement)',
                    'backend._document()[0] == expected', '== final_addresses',
                    'finished_terminal_facts(backend._terminal(address)) == finished',
                    "observe('herdr-core', plan)", 'backend_pid() == pid',
                    'kept-shell-pending-kill-recovery-complete',
                    'kept-shell-observed-kill-recovery-complete'):
        assert witness in body
    assert body.count("cli('restore')") == 2
    assert "cli('recover')" not in body
    helper = ast.get_source_segment(source, functions['expected_leaf_rebind'])
    assert helper is not None and 'rebind_app_document' not in helper
    assert body.index("pending.pop('identity')") < body.index('original_receipt(legacy_pid_fields(receipt))')
    assert body.index('original_receipt(legacy_pid_fields(receipt))') < body.index('churned = True')
    assert body.index('fixture_before_legacy_repair_kill(') < body.index('forwarded += 1')
    assert body.index('forwarded += 1') < body.index('return original_core(method, params)')
    assert body.index('require(forwarded == 1)') < body.index("cli('restore')")
    prepare = ast.get_source_segment(source, functions['prepare_fixture'])
    assert prepare is not None
    assert (prepare.index('restart_and_recover(plan, pid)') <
            prepare.index('kept_shell_kill_recovery(plan, pid, lost_reply=False)') <
            prepare.index('kept_shell_kill_recovery(plan, pid, lost_reply=True)') <
            prepare.index("STEP = 'arm-core-boot'"))


def test_r2_app_document_preserves_nodes_metadata_and_semantics_without_aliases():
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    layout = runpy.run_path(str(ROOT / 'dot_local/share/dotfiles-ai/remote-herdr/layout.py'))
    plan = {'schema_version': 1, 'spaces': [{'name': 'Synthetic', 'directory': '/fixture',
        'tabs': [{'name': str(i), 'panes': [
            {'key': 's0-t' + str(i) + '-p0', 'cwd': '/fixture', 'session_id': 'ses_synthetic' + str(i)}],
            'root': {'pane': 's0-t' + str(i) + '-p0'}} for i in range(3)]}]}
    document = layout['to_app_document'](plan, {'s0-t' + str(i) + '-p0': 't' + str(i + 1)
                                              for i in range(3)})
    document['metadata'] = {'opaque': [None, {'value': 7}]}
    for tab in document['spaces'][0]['tabs']:
        tab['opaque'] = {'preserved': [1, 2]}
        tab['root']['size'] = {'weight': 7}
        tab['root']['content']['opaque'] = {'value': True}
    original = copy.deepcopy(document)
    result = fixture['app_compatible_document'](document)
    assert document == original
    ids = []
    for before, tab in zip(original['spaces'][0]['tabs'], result['spaces'][0]['tabs']):
        assert tab['root'] == {'id': tab['id'], 'type': 'row', 'children': [before['root']]}
        assert tab['opaque'] == before['opaque']
        ids.extend([tab['root']['id'], tab['root']['children'][0]['id']])
    assert len(ids) == len(set(ids)) == 6
    assert result['metadata'] == original['metadata']
    assert fixture['app_compatible_document'](result) == result
    classify = lambda leaf, address: {'cwd': '/fixture', 'session_id':
                                     'ses_synthetic' + str(int(address[1:]) - 1)}
    projected, _ = layout['project_app_document'](result, classify)
    assert projected == plan
    # Rebinding must still find precisely one block after cross-kind ID reuse.
    tab = result['spaces'][0]['tabs'][0]
    leaf = tab['root']['children'][0]['id']
    rebound = fixture['expected_leaf_rebind'](result, leaf, 't1', 't4')
    expected = copy.deepcopy(result)
    expected['spaces'][0]['tabs'][0]['root']['children'][0]['content']['terminal'] = 't4'
    assert rebound == expected
    rebound['metadata']['opaque'].append('independent')
    assert result['metadata'] == original['metadata']
    for case in ('node-alias', 'tab-alias', 'cross-tab-node', 'wrong-count'):
        invalid = copy.deepcopy(document)
        tabs = invalid['spaces'][0]['tabs']
        if case == 'node-alias':
            tabs[0]['root']['id'] = tabs[0]['id']
        elif case == 'tab-alias':
            tabs[1]['id'] = tabs[0]['id']
        elif case == 'cross-tab-node':
            tabs[1]['root']['id'] = tabs[0]['root']['id']
        else:
            tabs.pop()
        try:
            fixture['app_compatible_document'](invalid)
        except RuntimeError:
            pass
        else:
            raise AssertionError('ambiguous fixture identity must refuse')


def test_r2_native_label_transport_is_fixed_bounded_and_preserves_ownership(monkeypatch):
    for address in ('t7', 'ta', 't10'):
        check_r2_native_label_transport(monkeypatch, address)


def check_r2_native_label_transport(monkeypatch, address):
    # Synthetic wire only. No socket, native endpoint, proc or environment probe.
    from types import SimpleNamespace
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    namespace = fixture['native_app_labels'].__globals__
    monkeypatch.syspath_prepend(str(ROOT / 'dot_local/share/dotfiles-ai/remote-herdr'))
    import protocol
    import stat
    import struct
    methods = protocol.METHODS
    monkeypatch.setattr(namespace['os'], 'getuid', lambda: 1000)
    parent = SimpleNamespace(parents=(), lstat=lambda: SimpleNamespace(st_mode=stat.S_IFDIR | 0o700,
                                                                      st_uid=1000))
    class Endpoint:
        def __init__(self): self.parent = parent
        def lstat(self): return SimpleNamespace(st_mode=stat.S_IFSOCK | 0o600, st_uid=1000)
        def __str__(self): return '/synthetic/socket'
    class Backend:
        labels = {'remote-herdr-owner': 'synthetic', 'remote-herdr-pane': 'p0',
                  'remote-herdr-session': 'ses_synthetic'}
        def _core_endpoint(self): return Endpoint()
        def endpoint_present(self, target): return target == 'herdr-core'
        def _terminal(self, address): return {'address': address, 'labels': dict(self.labels)}
    backend = Backend()
    class Peer:
        compatible = True
        sent: list = []
        pending = b''
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def settimeout(self, timeout): assert timeout == 30
        def connect(self, endpoint): assert endpoint == '/synthetic/socket'
        def getsockopt(self, *args): return struct.pack('3i', 7, 1000, 1000)
        def sendall(self, raw):
            message = json.loads(raw)
            self.sent.append(message)
            if message['method'] == 'hello':
                assert message['params'] == {'framed': False}
                result = {'version': '0.1.18' if self.compatible else 'unsupported',
                          'generation': 1, 'framed': False, 'methods': ['terminal.label']}
            else:
                assert message['method'] == 'terminal.label'
                assert set(message['params']) == {'terminal', 'labels'}
                assert message['params']['terminal'] == address
                assert set(message['params']['labels']) == {'where', 'herdr.seen', 'herdr.space', 'herdr.tab'}
                backend.labels = dict(backend.labels, **message['params']['labels'])
                result = backend._terminal(address)
            self.pending = json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}).encode() + b'\n'
        def recv(self, size):
            assert 0 < size <= 65536
            part, self.pending = self.pending[:17], self.pending[17:]
            return part
    peer = Peer()
    # macOS need not expose Linux SO_PEERCRED; this is only a synthetic wire test.
    monkeypatch.setattr(namespace['socket'], 'SO_PEERCRED', 17, raising=False)
    monkeypatch.setattr(namespace['socket'], 'socket', lambda *args: peer)
    original = dict(backend.labels)
    for changed in (False, True):
        labels = fixture['native_app_labels'](backend, address, changed=changed)
        assert {key: labels[key] for key in original} == original
        assert labels['herdr.seen'] == ('2' if changed else '1')
    assert [message['method'] for message in peer.sent] == ['hello', 'terminal.label'] * 2
    assert protocol.METHODS == methods and 'terminal.label' not in methods
    peer.sent = []
    peer.compatible = False
    try:
        fixture['native_app_labels'](backend, address)
    except RuntimeError as error:
        assert not str(error)
    else:
        raise AssertionError('unsupported native version must refuse before labeling')
    assert [message['method'] for message in peer.sent] == ['hello']


def test_r2_source_requires_real_native_labels_retained_recover_and_r1_guards():
    source = (FIXTURE / 'verify-user.py').read_text()
    functions = {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
    label = ast.get_source_segment(source, functions['native_app_labels'])
    assert label is not None
    for witness in ('3965a46caae095a3ead01de237fa13955e52b8c6', 'schema/hc.openrpc.json',
                    "(2, 'terminal.label', {'terminal': address, 'labels': labels})",
                    'protocol.MAX_MESSAGE', 'protocol.decode(raw)', 'socket.SO_PEERCRED',
                    "'herdr.seen'", "'herdr.space'", "'herdr.tab'", "'where'",
                    "actual['labels'] == dict(before.get('labels', {}), **labels)"):
        assert witness in label
    assert 'protocol.METHODS' not in source
    edited = ast.get_source_segment(source, functions['edited_document_recovery'])
    assert edited is not None
    for witness in ("Controller(store, backend).switch('herdr-core')",
                    "Controller(store, backend).recover()", "['phase'] == 'restore_pending'",
                    'app_compatible_document(edited)', 'native_app_labels(backend, address)',
                    "require(refusal.returncode == 75)", "cli('recover')",
                    'signal.pidfd_send_signal(fd, signal.SIGKILL)', 'backend._shell_proof(current)',
                    'backend._pids_absent(shell_proof)', '== other_clients',
                    'expected_leaf_rebind(baseline, repair_leaf, repair_address, replacement)',
                    '- addresses == {replacement}', 'write(EXPECTED, expected)'):
        assert witness in edited
    assert edited.index("cli('recover')") < edited.index("cli('restore')")
    r1 = ast.get_source_segment(source, functions['kept_shell_kill_recovery'])
    assert r1 is not None
    assert r1.index('adopt_app_compatibility(plan)') < r1.index("STEP = 'kept-shell-client-loss'")
    assert r1.index("receipt['pending']") < r1.index('native_app_labels(backend, address, changed=True)')
    prepare = ast.get_source_segment(source, functions['prepare_fixture'])
    assert prepare is not None
    assert prepare.index('kept_shell_kill_recovery(plan, pid, lost_reply=True)') < prepare.index(
        "print('F07: app-labels-and-tab-identities-recovery-complete')")
    assert 'NOT actual Desktop UI producer evidence' in source


class AppClientSourceTests(unittest.TestCase):
    """Synthetic documents and scripted core calls only; no native execution."""

    def setUp(self):
        self.fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
        self.document: dict = {'metadata': {'opaque': [None, {'terminal': 'ta'}]}, 'spaces': [
            {'id': 'alpha', 'opaque': True, 'tabs': [
                {'id': 'tab', 'name': 'Retain', 'root': {'id': 'row', 'type': 'row',
                    'size': {'weight': 7}, 'opaque': {'keep': True}, 'children': [
                        {'id': 'live', 'type': 'block', 'content': {'terminal': 't7', 'opaque': 3},
                         'size': {'weight': 2}},
                        {'id': 'historical', 'type': 'block', 'content': {'terminal': 'ta'}},
                        {'id': 'foreign', 'type': 'block', 'content': {'terminal': 't7'}}]}},
                {'id': 'empty-tab', 'root': {'id': 'column', 'type': 'column', 'children': [
                    {'id': 'closed-tab', 'type': 'block', 'content': {'terminal': 'tb'}}]}}]},
            {'id': 'beta', 'tabs': [{'id': 'last-tab', 'root': {
                'id': 'closed-space', 'type': 'block', 'content': {'terminal': 'tc'}}}]}]}

    def test_prune_preserves_opaque_fields_weights_ids_and_foreign_views(self):
        before = copy.deepcopy(self.document)
        owned = {'live', 'closed-tab', 'closed-space'}
        expected = copy.deepcopy(before)
        expected['spaces'].pop()
        expected['spaces'][0]['tabs'].pop()
        expected['spaces'][0]['tabs'][0]['root']['children'].pop(0)
        result = self.fixture['fixture_prune_finished'](before, owned, {'t7', 'tb', 'tc'})
        self.assertEqual(result, expected)
        self.assertEqual(before, self.document)
        refs = self.fixture['fixture_references'](result)
        self.assertEqual(refs, {'historical': 'ta', 'foreign': 't7'})
        self.assertEqual(self.fixture['fixture_prune_finished'](before, owned, {'tz'}), before)

    def test_empty_branches_are_dropped_without_collapsing_remaining_rows(self):
        result = self.fixture['fixture_prune_finished'](self.document, {'live'}, {'t7'})
        row = result['spaces'][0]['tabs'][0]['root']
        self.assertEqual(row['id'], 'row')
        self.assertEqual(row['size'], {'weight': 7})
        self.assertEqual(len(row['children']), 2)
        all_refs = self.fixture['fixture_references'](self.document)
        empty = self.fixture['fixture_prune_finished'](self.document, all_refs, set(all_refs.values()))
        self.assertEqual(empty, {'metadata': self.document['metadata'], 'spaces': []})

    def scripted_client(self, *, mutation_failure=False, observation_failure=False, paused=False):
        document = copy.deepcopy(self.document)
        calls = []
        inventories = iter([
            {'t7': 'live', 'ta': 'finished', 'tb': 'live', 'tc': 'live'},
            {'t7': 'finished', 'ta': 'finished', 'tb': 'live', 'tc': 'live'}])
        def core(method, params):
            calls.append((method, copy.deepcopy(params)))
            if observation_failure:
                raise ValueError('PRIVATE-NATIVE-PAYLOAD')
            if method == 'terminal.list':
                self.assertEqual(params, {'all': True})
                return {'terminals': [{'address': a, 'state': s} for a, s in next(inventories).items()]}
            if method == 'doc.get':
                self.assertEqual(params, {'name': 'herdr-app'})
                return {'version': 17, 'value': copy.deepcopy(document)}
            self.assertEqual(method, 'doc.set')
            self.assertEqual(params['version'], 17)
            self.assertEqual(params['name'], 'herdr-app')
            if mutation_failure:
                raise ValueError('PRIVATE-CAS-OUTCOME')
            return {'version': 18}
        client = self.fixture['FixtureAppClient'](core, {'live', 'historical'})
        class Stop:
            def __init__(self): self.calls = 0
            def wait(self, seconds):
                self.calls += 1
                return self.calls > 1
        client.stop = Stop()
        if paused:
            client.release.clear()
        client._observe()  # Scripted in this thread, no host services or sockets.
        return client, calls

    def test_observer_uses_live_finish_events_and_one_observed_version_cas(self):
        client, calls = self.scripted_client()
        client.check()
        self.assertTrue(client.seen({'t7'}))
        self.assertTrue(client.observed_live('t7'))
        self.assertEqual([m for m, _ in calls], ['terminal.list', 'terminal.list', 'doc.get', 'doc.set'])
        refs, live = client.events['t7']
        self.assertEqual(refs['live'], 't7')
        self.assertNotIn('t7', live)
        updated = calls[-1][1]['value']
        expected = copy.deepcopy(self.document)
        expected['spaces'][0]['tabs'][0]['root']['children'].pop(0)
        self.assertEqual(updated, expected)  # Preexisting finished 'ta' stays.
        self.assertNotIn('ta', client.events)

    def test_pause_prevents_document_write_and_unknown_failures_never_retry(self):
        paused, calls = self.scripted_client(paused=True)
        paused.check()
        self.assertEqual([m for m, _ in calls], ['terminal.list', 'terminal.list'])
        self.assertFalse(paused.events)
        for kwargs in ({'mutation_failure': True}, {'observation_failure': True}):
            with self.subTest(**kwargs):
                client, calls = self.scripted_client(**kwargs)
                with self.assertRaises(self.fixture['CommandFailure']) as caught:
                    client.check()
                self.assertEqual(caught.exception.reason, 'app-client-observation-or-cas-failed')
                self.assertNotIn('PRIVATE', str(caught.exception))
                self.assertLessEqual(sum(m == 'doc.set' for m, _ in calls), 1)
                self.assertFalse(client.events)

    def test_rebound_leaf_is_not_pruned_when_original_finishes(self):
        rebound = copy.deepcopy(self.document)
        rebound['spaces'][0]['tabs'][0]['root']['children'][0]['content']['terminal'] = 'tz'
        self.assertEqual(self.fixture['fixture_prune_finished'](rebound, {'live'}, {'t7'}), rebound)

    def test_legacy_serializer_is_pre_writer_small_and_does_not_modify_input(self):
        from types import SimpleNamespace
        repair = {'terminal': 't7', 'pane': {'session_id': 'ses_synthetic', 'cwd': '/fixture'},
                  'created': None, 'pids': None, 'stopped': False,
                  'source': {'private': 'not-published'}, 'create_id': 'a' * 32,
                  'labels': {'remote-herdr-repair': 'a' * 32}}
        old = copy.deepcopy(repair)
        original = lambda *args: ({'spaces': []}, {}, {}, {'uuid-leaf': copy.deepcopy(repair)})
        backend = SimpleNamespace(_labels=lambda txid, pane: {
            'remote-herdr-owner': txid, 'remote-herdr-pane': pane['key'],
            'remote-herdr-session': pane['session_id']})
        project = self.fixture['legacy_repair_projection'](original, backend)
        result = project({}, [], {}, {'txid': 'synthetic'})[3]['uuid-leaf']
        self.assertEqual(repair, old)
        self.assertNotIn('source', result)
        self.assertNotIn('create_id', result)
        self.assertEqual(result['labels'], {'remote-herdr-owner': 'synthetic',
            'remote-herdr-pane': 'uuid-leaf', 'remote-herdr-session': 'ses_synthetic'})
        for key in ('terminal', 'pane', 'created', 'pids', 'stopped'):
            self.assertEqual(result[key], repair[key])

    def test_legacy_mixed_fault_publishes_original_intents_before_effects_and_never_runs_third(self):
        from types import ModuleType, SimpleNamespace
        import sys
        keys = ['alpha', 'later', 'beta', 'remaining0', 'remaining1']
        repairs = {key: {'terminal': 't' + str(i + 1),
            'pane': {'key': key, 'session_id': 'ses_synthetic' + str(i), 'cwd': '/fixture'},
            'created': None, 'stopped': False, 'pids': None,
            'create_id': str(i) * 32, 'labels': {'remote-herdr-repair': str(i) * 32}}
            for i, key in enumerate(keys)}
        receipt = {'txid': 'synthetic', 'bindings': {k: k for k in keys},
                   'terminals': {k: r['terminal'] for k, r in repairs.items()}, 'repairs': {}, 'pending': None}
        manifest = {'plan': {'spaces': []}, 'receipt': copy.deepcopy(receipt)}
        terminals = {r['terminal']: {'address': r['terminal'], 'pid': 100 + i, 'state': 'live'}
                     for i, r in enumerate(repairs.values())}
        timeline = []
        published = []
        document = {'spaces': []}
        class Backend:
            store = SimpleNamespace(read=lambda name: copy.deepcopy(manifest))
            def _document(self): return copy.deepcopy(document), 9
            def _terminals(self): return copy.deepcopy(list(terminals.values()))
            def _current_projection(self, *args):
                return ({'spaces': []}, {k: {'leaf': k, 'terminal': r['terminal']} for k, r in repairs.items()},
                        {k: {'remote-herdr-owner': 'synthetic'} for k in keys}, copy.deepcopy(repairs))
            def _labels(self, txid, pane):
                return {'remote-herdr-owner': txid, 'remote-herdr-pane': pane['key'],
                        'remote-herdr-session': pane['session_id']}
            def _receipt(self, value):
                published.append(copy.deepcopy(value))
                pending = value['pending']
                timeline.append(('write', pending['operation'] if pending else None,
                                 pending.get('leaf') if pending else None))
            def _terminal(self, address): return copy.deepcopy(terminals[address])
            def _shell_proof(self, terminal):
                self_test.assertEqual(terminal['state'], 'live')
            def _pid_proofs(self, pids):
                return [{'pid': p, 'start_ticks': 1} for p in sorted(set(pids))]
            def _kill_identity(self, terminal): return {'synthetic-pid': terminal['pid']}
            def _complete_current_kill(self, value):
                self_test.assertEqual(published[-1], value)
                pending = value['pending']
                timeline.append(('kill', pending['leaf']))
                terminals[pending['terminal']]['state'] = 'finished'
                value['repairs'][pending['leaf']]['stopped'] = True
            def core(self, method, params):
                self_test.assertEqual(method, 'terminal.run')
                pending = published[-1]['pending']
                self_test.assertEqual(pending['operation'], method)
                self_test.assertEqual(params['labels'], pending['labels'])
                timeline.append(('run', pending['leaf']))
                address = 'ta' if pending['leaf'] == 'alpha' else 'tb'
                terminals[address] = {'address': address, 'labels': params['labels'], 'state': 'live'}
                return copy.deepcopy(terminals[address])
            def _same_labels(self, left, right): return left == right
            def _wait_created_core(self, address, pane, labels):
                self_test.assertEqual(published[-1]['pending']['operation'], 'terminal.run')
                timeline.append(('ready', address))
            def _replacement_proof(self, repair):
                self_test.assertEqual(terminals[repair['created']]['state'], 'live')
        self_test = self
        # Only the public address regex dependency is supplied; no native module
        # initialization, DB, filesystem, process, Store or socket is involved.
        previous = sys.modules.get('layout')
        dependency = ModuleType('layout')
        setattr(dependency, '_TERMINAL', re.compile(r't[0-9a-z]+'))
        sys.modules['layout'] = dependency
        try:
            admitted = self.fixture['legacy_mixed_admission'](Backend(), manifest['plan'], keys[:3],
                before_last=lambda: timeline.append(('barrier',)))
        finally:
            if previous is None:
                del sys.modules['layout']
            else:
                sys.modules['layout'] = previous
        self.assertEqual(published[-1], admitted)
        self.assertEqual(admitted['pending']['leaf'], 'beta')
        self.assertEqual(admitted['pending']['operation'], 'terminal.run')
        self.assertIsNone(admitted['repairs']['beta']['created'])
        self.assertEqual([event for event in timeline if event[0] == 'run'], [('run', 'alpha'), ('run', 'later')])
        self.assertEqual([event for event in timeline if event[0] == 'kill'],
                         [('kill', 'alpha'), ('kill', 'later'), ('kill', 'beta')])
        self.assertLess(timeline.index(('barrier',)), timeline.index(('kill', 'beta')))
        for key in keys:
            self.assertNotIn('create_id', admitted['repairs'][key])
            self.assertNotIn('source', admitted['repairs'][key])
        for key in keys[:3]:
            self.assertLess(timeline.index(('write', 'terminal.kill', key)), timeline.index(('kill', key)))
        for key in keys[:2]:
            self.assertLess(timeline.index(('write', 'terminal.run', key)), timeline.index(('run', key)))
        self.assertEqual(manifest['receipt'], receipt)  # No published input mutated.

    def test_app_worker_shutdown_is_owned_bounded_and_surfaces_failures(self):
        from types import SimpleNamespace
        client = self.fixture['FixtureAppClient'](lambda *args: {}, set())
        joined = []
        client.thread = SimpleNamespace(join=lambda seconds: joined.append(seconds), is_alive=lambda: False)
        client.__exit__()
        self.assertTrue(client.stop.is_set())
        self.assertEqual(joined, [35])
        client.thread.is_alive = lambda: True
        with self.assertRaises(self.fixture['CommandFailure']) as caught:
            client.__exit__()
        self.assertEqual(caught.exception.reason, 'app-client-join-deadline')
        client.thread.is_alive = lambda: False
        client.failure = True
        with self.assertRaises(self.fixture['CommandFailure']) as caught:
            client.__exit__()
        self.assertEqual(caught.exception.reason, 'app-client-observation-or-cas-failed')

    def ordering_backend(self):
        from types import SimpleNamespace
        baseline: dict = {'metadata': {'opaque': [None, 7]}, 'spaces': [{'id': 'space',
            'tabs': [{'id': 'tab', 'root': {'id': 'leaf', 'type': 'block',
                'size': {'weight': 3}, 'content': {'terminal': 'ta'}}}]}]}
        pane = {'key': 'pane', 'session_id': 'ses_synthetic', 'cwd': '/fixture'}
        source = {'address': 'ta', 'pid': 101, 'state': 'live', 'argv': ['/bin/bash', '-l'],
                  'cwd': '/fixture', 'keep': True, 'labels': {'remote-herdr-owner': 'synthetic',
                    'remote-herdr-pane': 'original-pane', 'remote-herdr-session': 'ses_synthetic'}}
        labels = {'remote-herdr-owner': 'synthetic', 'remote-herdr-pane': 'leaf',
                  'remote-herdr-session': 'ses_synthetic', 'remote-herdr-repair': 'a' * 32}
        new = dict(source, address='tb', pid=202, labels=labels,
                   argv=['/fixture/opencode', '--session', 'ses_synthetic'])
        document = copy.deepcopy(baseline)
        document['spaces'][0]['tabs'][0]['root']['content']['terminal'] = 'tb'
        boot_id = '11111111-2222-4333-8444-555555555555'
        def proof(pid): return [{'pid': pid, 'start_ticks': 17, 'boot_id': boot_id}]
        def identity(t):
            return {'pid': t['pid'], 'foreground_pid': t['pid'], 'argv': t['argv'], 'cwd': t['cwd'],
                    'launch': {k: t[k] for k in ('argv', 'cwd', 'keep')}}
        replacement = {'identity': identity(new), 'pids': proof(202)}
        receipt = {'document': copy.deepcopy(baseline), 'doc_version': 1,
            'bindings': {'pane': 'leaf'}, 'terminals': {'pane': 'ta'},
            'repairs': {'leaf': {'terminal': 'ta', 'created': 'tb', 'pane': pane, 'pids': proof(101),
                'source': identity(source), 'create_id': 'a' * 32, 'labels': copy.deepcopy(labels)}},
            'pending': {'operation': 'terminal.kill', 'terminal': 'ta', 'pane': 'pane', 'leaf': 'leaf',
                'identity': identity(source), 'pids': proof(101), 'rebound': {
                    'document': copy.deepcopy(document), 'version': 2, 'replacement': replacement}}}
        state: dict = {'document': document, 'version': 2, 'receipt': receipt,
            'terminals': {'ta': copy.deepcopy(source), 'tb': copy.deepcopy(new)},
            'clients': [{'pid': 202, 'session_id': 'ses_synthetic'}],
            'ticks': {101: 17, 202: 17}, 'cwd': {101: '/fixture', 202: '/fixture'}, 'reads': []}
        def read(name):
            self.assertEqual(name, 'receipt-synthetic.json')
            state['reads'].append(name)
            return copy.deepcopy(state['receipt'])
        def mutation(*args): raise AssertionError('ordering oracle must never mutate')
        backend = SimpleNamespace(
            store=SimpleNamespace(read=read, write=mutation), core=mutation,
            _document=lambda: (copy.deepcopy(state['document']), state['version']),
            _terminal=lambda address: copy.deepcopy(state['terminals'][address]),
            _pid_proofs=lambda pids: [{'pid': p, 'start_ticks': state['ticks'][p], 'boot_id': boot_id}
                                     for p in sorted(set(pids))],
            process_boot_id=lambda: boot_id,
            process_argv=lambda pid: copy.deepcopy(next(t['argv'] for t in state['terminals'].values()
                                                       if t['pid'] == pid)),
            process_cwd=lambda pid: state['cwd'][pid],
            _actual_core_program=lambda t: (None if t['address'] == 'ta' else 'ses_synthetic',
                                            state['cwd'][t['pid']]),
            scan=lambda sessions: copy.deepcopy(state['clients']))
        return (backend, baseline, 'leaf', source, pane, proof(101), 'synthetic', 'pane'), state

    def test_before_kill_oracle_accepts_live_exact_rebound_and_is_read_only(self):
        args, state = self.ordering_backend()
        before = copy.deepcopy(state)
        self.assertEqual(self.fixture['fixture_before_repair_kill'](*args), 'tb')
        self.assertEqual(state['reads'], ['receipt-synthetic.json'])
        state['reads'] = []
        self.assertEqual(state, before)

    def test_fast_kill_first_cannot_be_hidden_by_same_poll_cycle_run_and_cas(self):
        args, state = self.ordering_backend()
        # No thread, sleep or polling deadline: all proposed effects would run
        # back-to-back before the app observer's next sample. The FIRST effect
        # must instead refuse at its synchronous pre-forward boundary.
        state['document'] = copy.deepcopy(args[1])
        effects = []
        def kill_first_then_immediate_run_cas():
            self.fixture['fixture_before_repair_kill'](*args)
            effects.append('terminal.kill')
            effects.append('terminal.run')
            state['document']['spaces'][0]['tabs'][0]['root']['content']['terminal'] = 'tb'
            effects.append('doc.set')
        with self.assertRaises(self.fixture['CommandFailure']) as caught:
            kill_first_then_immediate_run_cas()
        self.assertEqual(caught.exception.reason, 'app-ordering-old-still-referenced')
        self.assertEqual(effects, [])
        self.assertEqual(state['reads'], [])  # Raw reference alone rejects canary/old intent.
        self.assertEqual(state['document'], args[1])

    def test_before_kill_oracle_refuses_changed_process_or_binding_facts(self):
        for case in ('stale-old-pid', 'old-cwd', 'new-cwd', 'duplicate-session', 'ref-old',
                     'finished-new', 'generation-label', 'replacement-proof', 'opaque-change',
                      'intent-version', 'old-label', 'old-boot', 'new-boot', 'invalid-boot', 'legacy-boot',
                      'nil-boot', 'uppercase-boot'):
            with self.subTest(case=case):
                args, state = self.ordering_backend()
                if case == 'stale-old-pid': state['ticks'][101] += 1
                elif case == 'old-cwd': state['cwd'][101] = '/foreign'
                elif case == 'new-cwd': state['cwd'][202] = '/foreign'
                elif case == 'duplicate-session': state['clients'].append({'pid': 303, 'session_id': 'ses_synthetic'})
                elif case == 'ref-old': state['document'] = copy.deepcopy(args[1])
                elif case == 'finished-new': state['terminals']['tb']['state'] = 'finished'
                elif case == 'generation-label': state['terminals']['tb']['labels']['remote-herdr-repair'] = 'b' * 32
                elif case == 'replacement-proof': state['receipt']['pending']['rebound']['replacement']['pids'][0]['start_ticks'] += 1
                elif case == 'opaque-change': state['document']['metadata']['opaque'].append('changed')
                elif case == 'intent-version': state['receipt']['pending']['rebound']['version'] += 1
                elif case == 'old-label': state['terminals']['ta']['labels']['remote-herdr-owner'] = 'foreign'
                elif case == 'old-boot': args[5][0]['boot_id'] = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
                elif case == 'new-boot': state['receipt']['pending']['rebound']['replacement']['pids'][0]['boot_id'] = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
                elif case == 'invalid-boot': args[0].process_boot_id = lambda: 'PRIVATE-invalid'
                elif case == 'legacy-boot': args[5][0].pop('boot_id')
                elif case == 'nil-boot': args[0].process_boot_id = lambda: '00000000-0000-0000-0000-000000000000'
                elif case == 'uppercase-boot': args[0].process_boot_id = lambda: 'AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE'
                with self.assertRaises((RuntimeError, self.fixture['CommandFailure'])):
                    self.fixture['fixture_before_repair_kill'](*args)

    def legacy_ordering_backend(self):
        args, state = self.ordering_backend()
        backend, baseline, leaf, source, pane, pids, txid, key = args
        old_pids = [{k: p[k] for k in ('pid', 'start_ticks')} for p in pids]
        legacy = {'txid': txid, 'document': copy.deepcopy(baseline), 'doc_version': 1,
            'pending': {'operation': 'terminal.kill', 'terminal': source['address'],
                        'pane': key, 'leaf': leaf, 'pids': copy.deepcopy(old_pids)},
            'repairs': {leaf: {'terminal': source['address'], 'pane': pane,
                'created': None, 'stopped': False, 'pids': copy.deepcopy(old_pids)}}}
        state['receipt']['adoption_backup'] = 'backup-synthetic.json'
        state['backup'] = {'receipt': copy.deepcopy(legacy)}
        read = backend.store.read
        backend.store.read = lambda name: (copy.deepcopy(state['backup'])
            if name == 'backup-synthetic.json' else read(name))
        return (*args, legacy), state

    def test_legacy_pre_kill_oracle_requires_fresh_ready_bound_replacement_and_whole_backup(self):
        args, state = self.legacy_ordering_backend()
        before = copy.deepcopy(state)
        self.assertEqual(self.fixture['fixture_before_legacy_repair_kill'](*args), 'tb')
        state['reads'] = []
        self.assertEqual(state, before)  # Read-only oracle; no old kill guard or effect.
        self.assertEqual(args[0].process_boot_id(), args[5][0]['boot_id'])
        self.assertNotIn('boot_id', args[-1]['pending']['pids'][0])

    def test_legacy_readmission_bad_facts_refuse_before_any_forwarded_effect(self):
        for case in ('owner', 'process', 'cwd', 'version', 'not-bound', 'not-ready',
                     'duplicate', 'wrong-backup', 'old-boot-authority', 'old-created',
                     'old-stopped', 'old-pid', 'old-rebound', 'old-version'):
            with self.subTest(case=case):
                args, state = self.legacy_ordering_backend()
                legacy = args[-1]
                if case == 'owner': state['terminals']['ta']['labels']['remote-herdr-owner'] = 'foreign'
                elif case == 'process': state['ticks'][101] += 1
                elif case == 'cwd': state['cwd'][101] = '/foreign'
                elif case == 'version': state['version'] += 1
                elif case == 'not-bound': state['document'] = copy.deepcopy(args[1])
                elif case == 'not-ready': state['terminals']['tb']['state'] = 'finished'
                elif case == 'duplicate': state['clients'].append({'pid': 303, 'session_id': 'ses_synthetic'})
                elif case == 'wrong-backup': state['backup']['receipt']['doc_version'] += 1
                elif case == 'old-boot-authority': legacy['pending']['pids'][0]['boot_id'] = args[5][0]['boot_id']
                elif case == 'old-created': legacy['repairs']['leaf']['created'] = 'tb'
                elif case == 'old-stopped': legacy['repairs']['leaf']['stopped'] = True
                elif case == 'old-pid': legacy['pending']['pids'][0]['start_ticks'] += 1
                elif case == 'old-rebound': legacy['pending']['rebound'] = {}
                elif case == 'old-version': legacy['doc_version'] += 1
                # Keep the original backup exact in every case except the explicit
                # corruption test, so semantic negatives test more than equality.
                if case != 'wrong-backup': state['backup'] = {'receipt': copy.deepcopy(legacy)}
                effects = []
                with self.assertRaises((RuntimeError, self.fixture['CommandFailure'])):
                    self.fixture['fixture_before_legacy_repair_kill'](*args)
                    effects.append('terminal.kill')
                self.assertEqual(effects, [])

    def test_native_case_boundaries_original_writers_and_both_new_markers(self):
        source = (FIXTURE / 'verify-user.py').read_text()
        tree = ast.parse(source)
        functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        bodies = {name: ast.get_source_segment(source, node) or '' for name, node in functions.items()}
        observer = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FixtureAppClient')
        observer_source = ast.get_source_segment(source, observer) or ''
        self.assertNotRegex(observer_source, r'\bStore\(|store\.(?:read|write)|terminal\.(?:kill|run)|server\.stop')
        for witness in ("'terminal.list'", "'doc.get'", "'doc.set'", "prior.get(a) == 'live'",
                        'self.thread.join(35)', 'self.stop.set()', 'self.check()', 'self.release.is_set()'):
            self.assertIn(witness, observer_source)
        for name in ('legacy_mixed_admission', 'kept_shell_kill_recovery',
                     'app_connected_repair', 'app_closed_pending_run_recovery'):
            body = bodies[name]
            self.assertNotRegex(body, r'store\.write\(|\.write_(?:text|bytes)\(')
        legacy = bodies['legacy_mixed_admission']
        for witness in ('legacy_repair_projection(', 'original_receipt = backend._receipt',
                        'original_receipt(receipt)', 'backend._complete_current_kill(receipt)',
                        "receipt['pending'] = {'operation': 'terminal.run'", "if index == 2:",
                        "backend.core('terminal.run'", 'backend._replacement_proof(repair)'):
            self.assertIn(witness, legacy)
        r1 = bodies['kept_shell_kill_recovery']
        self.assertIn('backend._current_projection = legacy_repair_projection(', r1)
        self.assertLess(r1.index("identity = repair.pop('source')"), r1.index('original_receipt(legacy_pid_fields(receipt))'))
        legacy_oracle = bodies['fixture_before_legacy_repair_kill']
        self.assertNotRegex(legacy_oracle,
            r'\b(?:core|write|_old_shell_guard|_current_kill_guard|_readmit_legacy_kill_source)\(')
        for witness in ('fixture_before_repair_kill(', "receipt['adoption_backup']", "{'receipt': legacy}",
                        "{'pid', 'start_ticks'}", "'create_id' not in repair",
                        "legacy['doc_version'] == receipt['doc_version']"):
            self.assertIn(witness, legacy_oracle)
        kept = bodies['fixture_idle_agents']
        for witness in ('os.pidfd_open(', 'signal.pidfd_send_signal(fd, signal.SIGKILL)',
                        'backend._client_argv(', 'backend.process_cwd(', '== NATIVE',
                        'backend._pid_proofs(', 'backend._shell_proof(current)', 'backend._pids_absent(old)'):
            self.assertIn(witness, kept)
        canary = bodies['fixture_app_canary']
        for witness in ("backend.core('terminal.run'", "backend.core('doc.set'", "backend.core('terminal.kill'",
                        'app.observed_live(address)', 'app.seen({address})', 'backend._document()[0] == document',
                        'backend._shell_proof(', 'backend._pid_proofs(', 'layout._TERMINAL.fullmatch(address)'):
            self.assertIn(witness, canary)
        self.assertLess(canary.index('fixture_before_repair_kill('), canary.index("backend.core('terminal.kill'"))
        self.assertIn("error.reason == 'app-ordering-old-still-referenced'", canary)
        oracle = bodies['fixture_before_repair_kill']
        self.assertNotRegex(oracle, r'\b(?:core|write|_rebound_kill_guard|_replacement_proof|_current_kill_guard)\(')
        for witness in ('fixture_references(document)', 'expected_leaf_rebind(baseline, leaf, old, new)',
                        "backend.store.read('receipt-' + txid + '.json')", "pending['rebound']['replacement']",
                        "repair['create_id']", "replacement['state'] == 'live'", 'backend.scan(',
                        'backend._pid_proofs(', "backend._actual_core_program(original) == (None, pane['cwd'])"):
            self.assertIn(witness, oracle)
        normal = bodies['app_connected_repair']
        for witness in ("cli('restore')", "cli('recover')", 'app.events[old]', 'new in live',
                        '== other_proofs', '== other', 'expected_leaf_rebind(', 'app.__exit__()',
                        'Controller(store, backend).restore()', 'backend.core = observed_core',
                        'backend.core = original_core', 'forwarded == 1', 'forwarded == 0',
                        'F07: app-connected-repair-ordering-complete'):
            self.assertIn(witness, normal)
        self.assertLess(normal.index('fixture_before_repair_kill('), normal.index('forwarded += 1'))
        self.assertLess(normal.index('forwarded += 1'), normal.index('return original_core(method, params)'))
        self.assertLess(normal.index('Controller(store, backend).restore()'), normal.index("cli('restore')"))
        retained = bodies['app_closed_pending_run_recovery']
        for witness in ("journal['phase'] == 'complete'", "store.read('transaction.json') == journal",
                        'fresh_app_leaf_ids()', 'fixture_idle_agents(', 'legacy_mixed_admission(',
                        'app.release.clear()', 'app.release.set()', 'active_app.seen({closed_address})',
                        "store.read('receipt-' + txid + '.json') == saved", "cli('recover')",
                        'fixture_prune_finished(', 'expected_leaf_rebind(', 'replacement == created[key]',
                        '== other_proofs', '== other_clients', "receipt['repairs'] == {}",
                        'backend._repair_candidates(', 'backend._same_labels(', 'backend._terminals()',
                        'not backend.scan({closed_session})', 'backend_pid() == pid',
                        'write(EXPECTED, expected_plan)', 'F07: app-closed-pending-run-recovery-complete'):
            self.assertIn(witness, retained)
        prepare = bodies['prepare_fixture']
        self.assertLess(prepare.index('kept_shell_kill_recovery(plan, pid, lost_reply=True)'),
                        prepare.index('app_connected_repair(plan, pid)'))
        self.assertLess(prepare.index('app_connected_repair(plan, pid)'),
                        prepare.index('plan = app_closed_pending_run_recovery(plan, pid)'))
        self.assertLess(prepare.index('plan = app_closed_pending_run_recovery(plan, pid)'),
                        prepare.index("STEP = 'arm-core-boot'"))


def test_observation_diagnostics_separate_coverage_and_native_ownership():
    source = (FIXTURE / 'verify-user.py').read_text()
    functions = {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
    observe = ast.get_source_segment(source, functions['observe'])
    owners = ast.get_source_segment(source, functions['transient_owners'])
    assert observe is not None and owners is not None
    for suffix in ('client-session-set', 'client-session-count', 'shared-backend-ready',
                   'client-argv', 'client-executable', 'client-connected', 'session-api',
                   'session-api-identity', 'session-api-directory'):
        assert "STEP = 'observe-' + target + '-" + suffix + "'" in observe
    for suffix in ('transient-unit-list', 'transient-unit-families', 'transient-unit-property',
                   'client-cgroup', 'no-persistent-units', 'exclusive-endpoint'):
        assert "STEP = 'observe-herdr-core-" + suffix + "'" in owners
    assert "wait(lambda: f01.connected(client['pid'], port), seconds=30)" in observe


class CapturedClientProofTests(unittest.TestCase):
    """Execute the REAL strict validator against synthetic captured facts only."""

    def setUp(self):
        self.fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
        module_path = str(ROOT / 'dot_local/share/dotfiles-ai/remote-herdr')
        sys.path.insert(0, module_path)
        try:
            from native import Native, NativeError
        finally:
            sys.path.remove(module_path)
        self.Native = Native
        self.NativeError = NativeError
        self.backend = object.__new__(Native)  # No constructor, env, home or proc reads.
        def forbidden(*args):
            raise AssertionError('must use captured facts, never collect after effects')
        self.enterContext(patch.object(self.backend, '_pid_proofs', forbidden))
        self.enterContext(patch.object(self.backend, 'process_boot_id', forbidden))
        self.boot = '11111111-2222-4333-8444-555555555555'
        self.capture: dict = {'clients': [
            {'pid': 101, 'start_ticks': 7, 'session_id': 'ses_synthetic0'},
            {'pid': 202, 'start_ticks': 9, 'session_id': 'ses_synthetic1'}],
            'pids': [{'pid': 303, 'start_ticks': 3, 'boot_id': self.boot},
                     {'pid': 202, 'start_ticks': 9, 'boot_id': self.boot},
                     {'pid': 101, 'start_ticks': 7, 'boot_id': self.boot}]}

    def test_red_regression_rich_client_rows_fail_real_absence_validator_before_proc(self):
        # The exact failed native call, not a permissive fake _pids_absent. It
        # must reject before process_boot_id (which is deliberately forbidden).
        with self.assertRaises(self.NativeError) as caught:
            self.backend._pids_absent(self.capture['clients'])
        self.assertEqual(str(caught.exception), 'native client PID proof invalid')

    def test_selected_original_proofs_pass_strict_absence_and_preserve_boot_and_input(self):
        before = copy.deepcopy(self.capture)
        selected = self.fixture['fixture_captured_client_proofs'](self.backend, self.capture)
        self.assertEqual(selected, self.capture['pids'][1:])
        self.assertEqual({p['pid'] for p in selected}, {101, 202})
        self.Native._validate_pid_proofs(selected)
        observed = []
        class AbsentProc:
            def __truediv__(self, pid):
                observed.append(int(pid))
                return self
            def lstat(self): raise FileNotFoundError()
        with patch.object(self.backend, 'proc_root', AbsentProc(), create=True):
            with patch.object(self.backend, 'process_boot_id', lambda: self.boot):
                self.assertTrue(self.backend._pids_absent(selected))
            self.assertEqual(observed, [202, 101])  # Shell 303 is not a session client.
            self.assertEqual(self.capture, before)
            # A different boot is evaluated by the actual native oracle, without
            # losing the original boot ID or consulting synthetic current PID paths.
            observed.clear()
            with patch.object(self.backend, 'process_boot_id', lambda: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'):
                self.assertTrue(self.backend._pids_absent(selected))
            self.assertFalse(observed)
        self.assertTrue(all(p['boot_id'] == self.boot for p in selected))
        selected[0]['start_ticks'] += 1
        self.assertEqual(self.capture, before)  # Selection does not alias receipt rows.

    def test_bad_capture_refuses_before_effects_without_filtering_unsafe_proofs(self):
        for case in ('missing-client-proof', 'duplicate-client', 'duplicate-proof',
                     'rich-proof', 'unsafe-proof-field', 'unsafe-client-field',
                     'missing-boot', 'invalid-boot', 'mixed-boots', 'changed-start',
                     'boolean-pid', 'invalid-client-shape'):
            with self.subTest(case=case):
                capture = copy.deepcopy(self.capture)
                if case == 'missing-client-proof': capture['pids'].pop()
                elif case == 'duplicate-client': capture['clients'].append(copy.deepcopy(capture['clients'][0]))
                elif case == 'duplicate-proof': capture['pids'].append(copy.deepcopy(capture['pids'][0]))
                elif case == 'rich-proof': capture['pids'][1] = copy.deepcopy(capture['clients'][1])
                elif case == 'unsafe-proof-field': capture['pids'][0]['unsafe'] = 'must-not-be-filtered'
                elif case == 'unsafe-client-field': capture['clients'][0]['unsafe'] = 'must-not-be-filtered'
                elif case == 'missing-boot':
                    for proof in capture['pids']: proof.pop('boot_id')
                elif case == 'invalid-boot': capture['pids'][0]['boot_id'] = 'invalid'
                elif case == 'mixed-boots': capture['pids'][0]['boot_id'] = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
                elif case == 'changed-start': capture['clients'][0]['start_ticks'] += 1
                elif case == 'boolean-pid': capture['clients'][0]['pid'] = True
                elif case == 'invalid-client-shape': capture['clients'][0] = 101
                effects = []
                with self.assertRaises((RuntimeError, self.NativeError)):
                    self.fixture['fixture_captured_client_proofs'](self.backend, capture)
                    effects.append('switch-or-kill')
                self.assertEqual(effects, [])

    def test_idle_shell_capture_has_empty_client_subset_but_keeps_valid_full_inventory(self):
        capture = copy.deepcopy(self.capture)
        capture['clients'] = []
        self.assertEqual(self.fixture['fixture_captured_client_proofs'](self.backend, capture), [])
        self.Native._validate_pid_proofs(capture['pids'])

    def test_all_three_native_call_sites_select_before_effects_and_keep_exit_assertions(self):
        source = (FIXTURE / 'verify-user.py').read_text()
        nodes = {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        bodies = {k: ast.get_source_segment(source, v) or '' for k, v in nodes.items()}
        switch = bodies['switch']
        self.assertLess(switch.index('fixture_captured_client_proofs(backend, before)'),
                        switch.index("cli('switch', target)"))
        self.assertIn('backend._pids_absent(client_proofs)', switch)
        kept = bodies['kept_shell_kill_recovery']
        self.assertLess(kept.index('fixture_captured_client_proofs(backend, before)'),
                        kept.index('signal.pidfd_send_signal(fd, signal.SIGKILL)'))
        self.assertLess(kept.index('require(len(captured_client) == 1)'),
                        kept.index('signal.pidfd_send_signal(fd, signal.SIGKILL)'))
        self.assertIn('backend._pids_absent(captured_client)', kept)
        edited = bodies['edited_document_recovery']
        self.assertLess(edited.index('fixture_captured_client_proofs(backend, source)'),
                        edited.index("Controller(store, backend).switch('herdr-core')"))
        self.assertIn('backend._pids_absent(source_client_proofs)', edited)
        # Bounded AST audit of every strict absence call: no rich clients or a
        # comprehension derived from rich clients may cross that boundary.
        for call in ast.walk(ast.parse(source)):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == '_pids_absent':
                for argument in call.args:
                    self.assertFalse(any(isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                                         and n.slice.value == 'clients' for n in ast.walk(argument)))


class RestartQualificationSourceTests(unittest.TestCase):
    """Scripted/source evidence only; none of these are native restart proofs."""

    def setUp(self):
        self.fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))

    def test_legacy_pid_serializer_strips_boot_before_writer_without_mutating_input(self):
        receipt = {'pending': {'operation': 'terminal.kill', 'pids': [
            {'pid': 101, 'start_ticks': 7, 'boot_id': '11111111-2222-4333-8444-555555555555'}]},
            'repairs': {'leaf': {'pids': [{'pid': 101, 'start_ticks': 7,
                                         'boot_id': '11111111-2222-4333-8444-555555555555'}]},
                        'later': {'pids': None}}, 'opaque': {'keep': True}}
        before = copy.deepcopy(receipt)
        old = self.fixture['legacy_pid_fields'](receipt)
        self.assertEqual(receipt, before)
        self.assertEqual(old['pending']['pids'], [{'pid': 101, 'start_ticks': 7}])
        self.assertEqual(old['repairs']['leaf']['pids'], old['pending']['pids'])
        self.assertIsNone(old['repairs']['later']['pids'])
        self.assertEqual(old['opaque'], receipt['opaque'])

    def test_restart_barrier_retains_logical_client_and_errors_are_not_suppressed(self):
        from types import SimpleNamespace
        client = self.fixture['FixtureAppClient'](lambda *args: {}, {'leaf'})
        client.events['old'] = ({'leaf': 'new'}, {'new'})
        client.live_seen.add('new')
        before = copy.deepcopy(client.events)
        joined = []
        client.thread = SimpleNamespace(join=lambda seconds: joined.append(seconds), is_alive=lambda: False)
        # Script only the acknowledged worker boundary: no thread or real RPC.
        def acknowledge(seconds):
            self.assertEqual(seconds, 30)
            self.assertTrue(client.restart_requested.is_set())
            self.assertFalse(client.restart_resume.is_set())
            client.restart_paused.set()
            return True
        client.restart_paused.wait = acknowledge
        client.pause_restart()
        core = lambda *args: {'synthetic': True}
        namespace = client.reconnect.__globals__
        old_wait = namespace['wait']
        def resume(check, seconds):
            self.assertEqual(seconds, 30)
            self.assertIs(client.core, core)
            self.assertFalse(client.restart_requested.is_set())
            self.assertTrue(client.restart_resume.is_set())
            client.restart_paused.clear()
            self.assertTrue(check())
        namespace['wait'] = resume
        try:
            client.reconnect(core)
        finally:
            namespace['wait'] = old_wait
        self.assertEqual(client.events, before)
        self.assertTrue(client.observed_live('new'))
        client.failure = True
        with self.assertRaises(self.fixture['CommandFailure']):
            client.pause_restart()
        client.failure = False
        client.restart_resume.clear()
        client.__exit__()
        self.assertEqual(joined, [35])
        self.assertTrue(client.restart_resume.is_set())

    def test_r4_restart_uses_existing_native_lifecycle_and_proves_exit_and_retention(self):
        source = (FIXTURE / 'verify-user.py').read_text()
        nodes = {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        bodies = {k: ast.get_source_segment(source, v) or '' for k, v in nodes.items()}
        identity = bodies['fixture_core_identity']
        for witness in ('socket.SO_PEERCRED', "(proc / 'exe').resolve() == BIN / 'herdr-core'",
                        "'hc-serve-'", 'backend._pid_proofs([core_pid])', 'core_pid != backend_pid()',
                        'os.getuid() == 1000 and Path.home() == HOME'):
            self.assertIn(witness, identity)
        restart = bodies['fixture_bootlike_core_restart']
        self.assertNotRegex(restart, r'store\.write\(|\.write_(?:text|bytes)\(|terminal\.(?:run|kill)|doc\.set')
        for witness in ("3965a46c", 'app.pause_restart()', 'fixture_core_identity(backend) == owner',
                        "backend.command(['herdr-core', 'server', 'stop', '--json'])",
                        "backend.command(['herdr-core', 'server', 'start', '--json'])",
                        'backend._pids_absent(owner)', 'backend._pids_absent(programs)',
                        'backend._pids_absent(stale)', "(None, previous['cwd'])", 'backend._shell_proof(current)',
                        "current['labels'] == previous['labels']", 'backend._document()[0] == document',
                        'app.reconnect(Native(HOME, backend.store).core)', 'backend_pid() == pid'):
            self.assertIn(witness, restart)
        self.assertLess(restart.index('app.pause_restart()'), restart.index("'server', 'stop'"))
        self.assertLess(restart.index('wait(retained'), restart.index('app.reconnect('))
        case = bodies['interrupted_restore_restart_recovery']
        self.assertNotRegex(case, r'store\.write\(|\.write_(?:text|bytes)\(')
        self.assertLess(case.index('original_receipt(receipt)'), case.index("raise NativeError('fixture partial"))
        for witness in ("receipt['pending'] is None", 'completed and created',
                        'backend._replacement_proof(repair)', 'Controller(store, backend).restore()',
                        "store.read('receipt-' + txid + '.json') == admitted", 'fixture_bootlike_core_restart(',
                        'for completed_restore in (False, True)', "cli('recover')", "cli('restore')",
                        "receipt['repairs'] == {}", 'expected_leaf_rebind(',
                        'set(fixture_references(expected)) == set(references)', '== set(receipt[\'terminals\'].values())',
                        'backend._pids_absent(stale)', 'backend._coverage(plan) == coverage',
                        "observe('herdr-core', plan)", 'app.__exit__()'):
            self.assertIn(witness, case)
        for marker in ('F07: interrupted-restore-restart-recovery-complete',
                       'F07: completed-restore-restart-recovery-complete'):
            self.assertEqual(source.count(marker), 1)
            self.assertLess(case.index('backend._coverage(plan) == coverage'), case.index(marker))
        prepare = bodies['prepare_fixture']
        self.assertLess(prepare.index('plan = app_closed_pending_run_recovery(plan, pid)'),
                        prepare.index('interrupted_restore_restart_recovery(plan, pid)'))
        self.assertLess(prepare.index('interrupted_restore_restart_recovery(plan, pid)'),
                        prepare.index("STEP = 'arm-core-boot'"))
        self.assertIn("wait(lambda: observe(target, plan), seconds=150)", bodies['boot'])


class QualificationSourceTests(unittest.TestCase):
    def test_boot_verify_diagnostics_keep_only_fixed_refusal_labels(self):
        fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
        observe = fixture['observe']
        error_type = type('NativeError', (ValueError,), {})
        class State:
            retained = None
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, name):
                if name.startswith('receipt-'):
                    return self.retained
                return {'runtime': 'herdr-core', 'plan': [], 'receipt': {}, 'txid': 'fixture'}
        class Backend:
            refusal = ''
            def __init__(self, *args): pass
            def _semantic(self, plan): return []
            def verify(self, *args): raise error_type(self.refusal)
        observe.__globals__['adapter'] = lambda: (lambda root: State(), Backend)
        for refusal, label in [('core current restored bindings differ', 'current-bindings'),
                               ('PRIVATE-RUNTIME-VALUE', 'unclassified')]:
            Backend.refusal = refusal
            with self.assertRaises(fixture['CommandFailure']) as caught:
                observe('herdr-core', [])
            self.assertEqual(caught.exception.reason, 'verify-' + label)
            self.assertEqual(observe.__globals__['STEP'], 'observe-herdr-core-verify-' + label)
            self.assertNotIn('PRIVATE', str(caught.exception))
        State.retained = {'pending': {'operation': 'PRIVATE-RUNTIME-OP'}, 'repairs': {'PRIVATE-LEAF': {}}}
        with self.assertRaises(fixture['CommandFailure']):
            observe('herdr-core', [])
        self.assertEqual(observe.__globals__['STEP'],
                         'observe-herdr-core-verify-unclassified-pending-unknown-repairs')

    def test_core_stop_failure_labels_are_fixed_and_cover_current_recovery(self):
        tree = ast.parse((FIXTURE / 'verify-user.py').read_text())
        restart = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'restart_and_recover')
        assignment = next(node for node in restart.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == 'labels'
                                  for target in node.targets))
        labels = ast.literal_eval(assignment.value)
        for message in ('core controller stop process proof unavailable',
                        'core repair binding changed', 'core current restored bindings differ',
                        'current document repair PID proof invalid'):
            self.assertRegex(labels[message], r'^[a-z-]+$')
        self.assertNotIn('PRIVATE-RUNTIME-VALUE', labels)
        self.assertEqual(labels.get('PRIVATE-RUNTIME-VALUE', 'unclassified'), 'unclassified')

    def test_semantic_failure_diagnostic_withholds_runtime_values(self):
        fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
        compare = fixture['semantic_difference']
        original = json.loads('''[{"name":"PRIVATE-SPACE", "directory":"/private/fixture", "tabs":[
            {"name":"PRIVATE-TAB", "root":{"axis":"row", "ratio":0.25, "children":[
                {"cwd":"/private/fixture", "session_id":"ses_private0"},
                {"cwd":"/private/fixture", "session_id":"ses_private1"}]}}]}]''')
        self.assertIsNone(compare(original, original))
        changes = [('name', 'space-name'), ('directory', 'space-directory')]
        for key, label in changes:
            changed = copy.deepcopy(original)
            changed[0][key] = 'PRIVATE-CHANGED'
            self.assertEqual(compare(changed, original), label)
        ratio_changed = copy.deepcopy(original)
        ratio_changed[0]['tabs'][0]['root']['ratio'] = 0.5
        self.assertEqual(compare(ratio_changed, original), 'split-ratio')
        session_changed = copy.deepcopy(original)
        session_changed[0]['tabs'][0]['root']['children'][1]['session_id'] = 'ses_private_changed'
        self.assertEqual(compare(session_changed, original), 'pane-session')

    def test_edited_fixture_expected_plan_has_canonical_keys_and_independent_geometry(self):
        fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
        tree = ast.parse((FIXTURE / 'verify-user.py').read_text())
        prepare = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'prepare_fixture')
        assignment = next(node for node in prepare.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == 'plan'
                                  for target in node.targets))
        # Evaluate only the fixture's literal plan with synthetic directories/IDs.
        plan = eval(compile(ast.Expression(assignment.value), '<fixture-plan>', 'eval'), {
            'directories': [Path('/fixture/alpha'), Path('/fixture/beta')],
            'sessions': ['ses_original0', 'ses_closed', 'ses_original2']})
        later = [{'key': 'later-' + str(i), 'cwd': '/fixture/alpha',
                  'session_id': 'ses_later' + str(i)} for i in range(3)]
        before = copy.deepcopy((plan, later))
        expected = fixture['edited_expected_plan'](plan, later)
        layout = runpy.run_path(str(ROOT / 'dot_local/share/dotfiles-ai/remote-herdr/layout.py'))
        self.assertEqual(layout['validate_plan'](expected), expected)
        self.assertEqual((plan, later), before)
        panes = [pane for space in expected['spaces'] for tab in space['tabs'] for pane in tab['panes']]
        self.assertEqual({pane['session_id'] for pane in panes}, {
            'ses_original0', 'ses_original2', 'ses_later0', 'ses_later1', 'ses_later2'})
        self.assertEqual(len(panes), 5)
        root = expected['spaces'][0]['tabs'][1]['root']
        self.assertEqual(root['ratio'], 0.25)
        self.assertEqual(root['children'][1]['ratio'], 0.4)

    def test_current_document_fixture_uses_real_transactions_and_installed_recovery(self):
        source = (FIXTURE / 'verify-user.py').read_text()
        tree = ast.parse(source)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'edited_document_recovery')
        writes = [node for node in ast.walk(function) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr == 'write']
        self.assertEqual(writes, [])  # No hand-written transaction/receipt/manifest.
        body = ast.get_source_segment(source, function)
        self.assertIsNotNone(body)
        assert body is not None
        for token in ("Controller(store, backend).switch('herdr-core')",
                      'Controller(store, backend).recover()', "cli('recover')", "cli('restore')",
                      "range(3)", "'--session', created['id']", "'terminal.kill'",
                      "backend._document()[0] == baseline", "backend.scan({closed_session})",
                      "store.read(receipt['adoption_backup'])", "['txid'] == txid",
                      'expected = edited_expected_plan(plan, later_panes)'):
            self.assertIn(token, body)
        prepare = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'prepare_fixture')
        steps = [call.func.id for call in ast.walk(prepare) if isinstance(call, ast.Call)
                 and isinstance(call.func, ast.Name)]
        self.assertLess(steps.index('inflight_switch'), steps.index('edited_document_recovery'))
        self.assertLess(steps.index('edited_document_recovery'), steps.index('restart_and_recover'))
        observe = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'observe')
        observation = ast.get_source_segment(source, observe)
        assert observation is not None
        self.assertNotIn('len(clients) == 3', observation)
        self.assertIn("{client['session_id'] for client in clients} == expected_sessions", observation)

    def test_copy_is_explicit_public_file_allowlist(self):
        allowed = {
            '.chezmoidata.toml', 'config.remote-user.example.toml',
            'dot_local/bin/executable_opencode.tmpl',
            'dot_local/bin/executable_opencode-install.tmpl',
            'dot_local/bin/executable_remote-herdr',
            'dot_local/bin/executable_remote-herdr-core',
            'dot_local/bin/executable_remote-user-bootstrap',
            'private_dot_config/herdr/config.toml.tmpl',
            'private_dot_config/dotfiles-ai/herdr-core.json.tmpl',
            'private_dot_config/dotfiles-ai/herdr-runtime.json.tmpl',
            'private_dot_config/systemd/user/opencode-shared.service',
            'tests/remote_opencode_systemd/verify-user.py',
            'tests/remote_herdr_systemd/boot-smoke.sh',
            'tests/remote_herdr_systemd/verify-user.py',
            'run_onchange_after_install-00-remote-herdr.sh.tmpl',
            'run_onchange_after_install-00z-remote-herdr-core.sh.tmpl',
            'run_onchange_after_install-01-remote-opencode.sh.tmpl',
            'run_after_install-04-remote-opencode-service.sh.tmpl',
            'run_after_install-05-remote-herdr-runtime.sh.tmpl',
        }
        allowed.update('dot_local/share/dotfiles-ai/remote-herdr/' + name + '.py'
                       for name in ('controller', 'native', 'layout', 'protocol', 'processes'))
        allowed.update('private_dot_config/systemd/user/' + name + '.tmpl'
                       for name in ('remote-herdr-tui.service', 'remote-herdr-restore.service',
                                     'remote-herdr-restore.timer'))
        allowed.update({'tests/remote_herdr_systemd/kept-probe.py',
                        'tests/remote_herdr_systemd/kept-probe.sh'})
        copied = set()
        for line in (FIXTURE / 'Containerfile').read_text().splitlines():
            if not line.startswith('COPY '):
                continue
            words = shlex.split(line)
            self.assertGreaterEqual(len(words), 3)
            for source in words[1:-1]:
                self.assertIn(source, allowed)
                self.assertTrue((ROOT / source).is_file())
                self.assertNotIn('*', source)
                copied.add(source)
        self.assertEqual(copied, allowed)

    def test_real_checksum_installers_and_version_identities(self):
        pins = tomllib.loads((ROOT / '.chezmoidata.toml').read_text())['dotfiles_ai']
        self.assertEqual(pins['herdr']['version'], '0.9.5')
        self.assertEqual(pins['herdr_core']['version'], '0.1.18')
        self.assertEqual(pins['herdr_core']['archive_sha256'],
                         '5b2f97cb4b2a9d7a6b2cc5942628203ed9fbb7cc0c2b4b09ad8a6f5648e246b7')
        self.assertEqual(pins['herdr_core']['binary_sha256'],
                         'baa9d208d6400556a6e379152455fe1301e0e1acdbc114ff60b79d64425179cf')
        for section, key in (('herdr', 'linux_amd64_asset_sha256'),):
            self.assertRegex(pins[section][key], r'^[a-f0-9]{64}$')
        self.assertEqual(pins['herdr']['linux_amd64_asset_sha256'],
                         '14d9e8bc8b4a9e0118d77c32266f76d461f09b40342eb23752960bd89f59929d')
        native_installer = (ROOT / 'dot_local/bin/executable_opencode-install.tmpl').read_text()
        self.assertIn('https://opencode.ai/v2/install', native_installer)
        fixture = (FIXTURE / 'verify-user.py').read_text()
        self.assertIn("write(HOME / 'qualified-opencode.json'", fixture)
        self.assertIn('hashlib.sha256(NATIVE.read_bytes())', fixture)
        self.assertNotIn("require('1.18.25' in", fixture)
        hook = (ROOT / 'run_onchange_after_install-00z-remote-herdr-core.sh.tmpl').read_text()
        self.assertIn('remote-herdr-core" install', hook)
        tui = (ROOT / 'run_onchange_after_install-00-remote-herdr.sh.tmpl').read_text()
        self.assertIn('sha256sum -c -', tui)

    def test_hosted_boot_job_is_required_and_isolated(self):
        workflow = WORKFLOW.read_text()
        self.assertIn('contents: read', workflow)
        self.assertIn('runs-on: ubuntu-latest', workflow)
        self.assertIn('--cgroupns=private', workflow)
        self.assertIn('--privileged', workflow)
        self.assertIn('--tmpfs /run --tmpfs /run/lock', workflow)
        self.assertIn('mount -o remount,rw /sys/fs/cgroup; exec /sbin/init', workflow)
        self.assertIn('persist-credentials: false', workflow)
        uses = re.findall(r'uses:\s*(\S+)', workflow)
        self.assertEqual(uses, ['actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1'])
        self.assertNotIn('continue-on-error:', workflow)
        self.assertNotIn('if:', workflow)
        self.assertNotIn('pull_request_target:', workflow)
        docker_run = workflow.split('docker run -d', 1)[1].split('docker exec', 1)[0]
        self.assertNotRegex(docker_run, r'--(?:volume|mount|network)|(?:^|\s)-[vp]\s')
        self.assertNotRegex(workflow, r'git push|gh pr|upload-artifact|secrets\.')
        stages = re.findall(r'boot-smoke.sh (prepare|verify-core|verify-tui)|docker (restart)', workflow)
        self.assertEqual([a or b for a, b in stages],
                         ['prepare', 'restart', 'verify-core', 'restart', 'verify-tui'])
        self.assertIn('test -f /var/lib/f07/qualified', workflow)
        self.assertIn('docker exec "$probe" bash /opt/f07/kept-probe.sh approved-disposable-container', workflow)
        self.assertLess(workflow.index('bash /opt/f07/kept-probe.sh'),
                        workflow.index('bash /opt/f07/boot-smoke.sh prepare'))
        for path in ('dot_local/bin/executable_opencode*',
                     'dot_local/share/dotfiles-ai/remote-herdr/**',
                     'private_dot_config/herdr/**',
                     'private_dot_config/systemd/user/remote-herdr*',
                     'private_dot_config/dotfiles-ai/herdr*.tmpl'):
            self.assertIn('"' + path + '"', workflow)

    def test_fixture_requires_native_evidence_not_mocks(self):
        source = (FIXTURE / 'verify-user.py').read_text()
        ast.parse(source)
        self.assertNotRegex(source, r'unittest.mock|monkeypatch|INSERT INTO|CREATE TABLE|fake.*binary')
        for witness in ("api('post', '/api/session'", "'location': {'directory'",
                        "'session.create'", "'?mode=ro'", 'PRAGMA table_info(session_v2)',
                        'replace_target=True, imported=plan', "'terminal.run'", "'doc.set'",
                        "'hc-serve-'", "'hc-hold-'", "'hc-shutdown-'", "'Transient'",
                        'signal.pidfd_send_signal(fd, signal.SIGTERM)',
                        "backend._coverage(plan) == before", "backend.stop('herdr-core', capture)",
                        "cli('restore')", "cli('recover')", 'backend._pids_absent(client_proofs)',
                        'fixture_captured_client_proofs(backend, before)',
                         "backend._client_argv(client['pid'], client['session_id'])",
                         "f01.connected(client['pid'], port)",
                        'backend._semantic', 'backend_pid() == pid', "'--version'",
                        "'remote-herdr-core', 'check'", "'ratio': 0.375",
                        'child.send_signal(signal.SIGSTOP)', 'require(interrupted)',
                        'require(refusal.returncode == 75)', "STEP = 'interrupted-switch-recovery'",
                        'retained-shell-label-recovery-complete',
                        "backend.absent(sessions(plan), capture['clients'])",
                        "receipt['pending'] is None", "store.read('manifest.json') is None",
                        "manifest['receipt']['terminals'][first_pane['key']] == retained"):
            self.assertIn(witness, source)
        retained = next(node for node in ast.parse(source).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'retained_shell_switch')
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr in {'write', 'write_text', 'write_bytes'}
                             for node in ast.walk(retained)))
        shell = (FIXTURE / 'boot-smoke.sh').read_text()
        for witness in ('env -i', 'loginctl enable-linger fixture', 'no_login',
                        'systemd-detect-virt --container',
                        '! -e /run/f07-core', '! -e /run/f07-tui', 'timeout 900', 'timeout 600'):
            self.assertIn(witness, shell)
        self.assertNotRegex(shell + source, r'journalctl|print\(.*(?:error|result|password|service\[)')
        self.assertNotIn('inflight-turn-not-qualified', shell)
        self.assertIn('native-layout-and-inflight-turn-qualification-complete', shell)

    def test_inflight_proof_uses_native_identity_and_projected_messages(self):
        source = (FIXTURE / 'verify-user.py').read_text()
        for witness in ("Server(('127.0.0.1', 0), Handler)", 'ThreadingHTTPServer',
                        "self.path == '/v1/chat/completions'", "body['model'] == 'held'",
                        "body['stream'] is True", "self.headers.get('X-Session-Id') == fixture.session_id",
                        "self.headers.get('x-session-affinity')", 'length <= 1024 * 1024',
                        "'@opencode/ai/providers/openai-compatible'", "'model': 'rrw007f/held'",
                        "'model': {'id': 'held', 'providerID': 'rrw007f'}",
                        "'id': message_id", "'delivery': 'steer', 'resume': True",
                        'provider.held.wait(120)', "switch('tui', plan, pid, during=held)",
                        'provider.release.set()', 'fixture.release.wait(360)',
                        'self.requests != 1', "'/api/session/active'",
                        "'/context'", "'/message/'", 'projected_turn(context(), admitted, original)',
                        "'text': provider.nonce", "admitted['payload']['text'] == provider.nonce",
                        'self.server.shutdown()', 'self.server.server_close()',
                        "print('F07: inflight-turn-preservation-complete')"):
            self.assertIn(witness, source)
        self.assertNotIn('/wait', source)
        self.assertNotIn('/history?', source)
        self.assertNotIn('/api/experimental/session/', source)
        self.assertNotIn('session.next.', source)
        self.assertNotIn("'prompt': {'text'", source)
        tree = ast.parse(source)
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        prepare = ast.get_source_segment(source, functions['prepare_fixture'])
        assert prepare is not None
        self.assertLess(prepare.index('provider.config()'), prepare.index("'apply'"))
        self.assertLess(prepare.index('inflight_switch(provider, plan, pid)'),
                        prepare.index('interrupted_switch(plan, pid)'))
        proof = ast.get_source_segment(source, functions['inflight_switch'])
        assert proof is not None
        self.assertEqual(proof.count("api('post'"), 1)  # Admission is never retried.
        self.assertLess(proof.index('held()\n'), proof.index("switch('tui'"))
        self.assertLess(proof.index("switch('tui'"), proof.index('provider.release.set()'))
        self.assertLess(proof.index('provider.release.set()'), proof.index("print('F07:"))
        calls = [node for node in ast.walk(functions['inflight_switch']) if isinstance(node, ast.Call)]
        validators = [node for node in calls if isinstance(node.func, ast.Name)
                      and node.func.id in {'projected_assistant', 'projected_turn'}]
        self.assertEqual(len(validators), 5)
        self.assertEqual(sum(any(key.arg == 'complete' and isinstance(key.value, ast.Constant)
                                 and key.value.value is True for key in node.keywords)
                             for node in validators), 2)


def test_controller_failure_reports_only_known_journal_phase(monkeypatch):
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    class Store:
        def __init__(self, root):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, name):
            if name == 'transaction.json':
                return {'phase': 'restore_pending', 'txid': 'fixture', 'private': 'PRIVATE'}
            return {'pending': {'operation': 'terminal.run'}, 'private': 'PRIVATE'}
    def failed(*args, **kwargs):
        raise fixture['CommandFailure']('command-exit-75')
    monkeypatch.setitem(fixture['cli'].__globals__, 'adapter', lambda: (Store, None))
    monkeypatch.setitem(fixture['cli'].__globals__, 'run', failed)
    try:
        fixture['cli']('switch', 'herdr-core')
    except fixture['CommandFailure'] as error:
        assert error.reason == 'controller-restore_pending-terminal-run'
    else:
        raise AssertionError('failed switch must not pass')


def test_kept_spawn_diagnostics_expose_only_known_counts():
    fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
    class Backend:
        @property
        def store(self):
            return self
        def read(self, name):
            return {'receipt': {'terminals': {}}}
        def _terminals(self):
            return [{'state': 'live', 'keep': True, 'pid': None,
                     'reason': 'server_stop', 'argv': ['PRIVATE']}]
        def _read(self, path, bound):
            return b'core: kept terminals waiting for a holder: PRIVATE Permission denied\nPRIVATE\n'
    result = fixture['kept_spawn_diagnostics'](Backend())
    assert 'PRIVATE' not in result
    assert '-count-1-mapped-0' in result
    assert '-server-stop-1-holder-errors-1-shell-errors-0' in result
    assert '-missing-0-denied-1-resource-0' in result


class ProjectedTurnTests(unittest.TestCase):
    """Synthetic projected messages, never native state or event-log payloads."""

    def setUp(self):
        fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
        self.validate = fixture['projected_turn']
        self.message = fixture['projected_assistant']
        self.admitted = {'id': 'msg_synthetic_user', 'payload': {'text': 'synthetic'}}
        self.user = {'id': self.admitted['id'], 'type': 'user', 'text': 'synthetic',
                     'time': {'created': 1}}
        self.assistant: dict = {'id': 'msg_synthetic_assistant', 'type': 'assistant',
                          'model': {'id': 'held', 'providerID': 'rrw007f'},
                          'time': {'created': 2}, 'content': []}

    def test_accepts_original_incomplete_and_completed_projection(self):
        self.assertEqual(self.validate([self.user, self.assistant], self.admitted), self.assistant)
        done = copy.deepcopy(self.assistant)
        done['time']['completed'] = 3
        done['finish'] = 'stop'
        done['content'] = [{'type': 'text', 'text': 'RRW007F-BEGIN:'},
                           {'type': 'text', 'text': 'synthetic:END'}]
        self.validate([self.user, done], self.admitted, self.assistant, complete=True)
        idle = {'id': 'msg_idle', 'type': 'idle', 'time': {'created': 4}, 'outcome': 'succeeded'}
        self.validate([self.user, done, idle], self.admitted, self.assistant, complete=True)
        for outcome in ('failed', 'interrupted'):
            with self.subTest(outcome=outcome), self.assertRaises(RuntimeError):
                self.validate([self.user, done, dict(idle, outcome=outcome)],
                              self.admitted, self.assistant, complete=True)

    def test_rejects_replacement_model_early_completion_and_errors(self):
        for case in ('id', 'created', 'model', 'provider', 'completed', 'finish', 'error', 'content'):
            changed = copy.deepcopy(self.assistant)
            if case == 'id':
                changed['id'] = 'msg_replacement'
            elif case in {'created', 'completed'}:
                changed['time'][case] = 99
            elif case in {'model', 'provider'}:
                changed['model']['id' if case == 'model' else 'providerID'] = 'wrong'
            elif case == 'error':
                changed['error'] = {'message': 'synthetic error'}
            elif case == 'content':
                changed['content'] = None
            else:
                changed['finish'] = 'stop'
            with self.subTest(case=case), self.assertRaises(RuntimeError):
                self.message(changed, self.assistant)

    def test_rejects_duplicate_missing_or_changed_user_and_assistant(self):
        wrong_id = dict(self.user, id='msg_wrong')
        wrong_text = dict(self.user, text='wrong')
        for context in ([self.user], [self.assistant], [self.user, self.user],
                        [self.assistant, self.assistant], [self.user, self.assistant, self.user],
                        [self.user, self.assistant, self.assistant],
                        [wrong_id, self.assistant], [wrong_text, self.assistant]):
            with self.subTest(count=len(context)), self.assertRaises(RuntimeError):
                self.validate(context, self.admitted, self.assistant)

    def test_projection_failure_reports_only_fixed_labels_and_counts(self):
        fixture = runpy.run_path(str(FIXTURE / 'verify-user.py'))
        with self.assertRaises(fixture['CommandFailure']) as captured:
            fixture['projected_turn']([dict(self.user, text='PRIVATE'), self.assistant], self.admitted)
        self.assertEqual(captured.exception.reason, 'projection-user-identity')
        with self.assertRaises(fixture['CommandFailure']) as captured:
            fixture['projected_turn']([self.user], self.admitted)
        self.assertEqual(captured.exception.reason, 'projection-count-users-1-assistants-0')
        changed = copy.deepcopy(self.assistant)
        changed['model']['variant'] = 'PRIVATE'
        with self.assertRaises(fixture['CommandFailure']) as captured:
            fixture['projected_assistant'](changed)
        self.assertEqual(captured.exception.reason,
                         'projection-model-variant')

    def test_accepts_native_default_variant_but_requires_unchanged_reference(self):
        original = copy.deepcopy(self.assistant)
        original['model']['variant'] = 'default'
        self.message(original)
        self.message(copy.deepcopy(original), original)
        with self.assertRaises(RuntimeError):
            self.message(self.assistant, original)
        with self.assertRaises(RuntimeError):
            self.message(original, self.assistant)
        changed = copy.deepcopy(original)
        changed['model']['unknown'] = 'PRIVATE'
        with self.assertRaises(RuntimeError):
            self.message(changed, original)

    def test_rejects_incomplete_wrong_finish_error_and_changed_final_text(self):
        for case in ('completed', 'finish', 'error', 'text'):
            done = copy.deepcopy(self.assistant)
            done['time']['completed'] = 3
            done['finish'] = 'stop'
            done['content'] = [{'type': 'text', 'text': 'RRW007F-BEGIN:synthetic:END'}]
            if case == 'completed':
                del done['time']['completed']
            elif case == 'finish':
                done['finish'] = 'length'
            elif case == 'error':
                done['error'] = {'message': 'synthetic error'}
            else:
                done['content'][0]['text'] += 'wrong'
            with self.subTest(case=case), self.assertRaises(RuntimeError):
                self.validate([self.user, done], self.admitted, self.assistant, complete=True)


class ApiSchemaTests(unittest.TestCase):
    """Minimal current wire schemas, deliberately indirect through local refs."""

    def spec(self):
        def obj(fields, required=()):
            return {'type': 'object', 'properties': fields, 'required': list(required)}
        def nullable(schema):
            return {'anyOf': [schema, {'type': 'null'}]}
        string = {'type': 'string'}
        location = obj({'directory': string}, ('directory',))
        model = obj({'id': string, 'providerID': string}, ('id', 'providerID'))
        info_fields = {'id': string, 'projectID': string, 'cost': {'type': 'number'},
                       'tokens': obj({}), 'time': obj({'created': string, 'updated': string},
                                                    ('created', 'updated')),
                       'location': {'$ref': '#/components/schemas/Location'}}
        info = obj(info_fields, info_fields)
        inbox_fields = {'id': string, 'sessionID': string, 'type': {'type': 'string', 'enum': ['user']},
                        'payload': obj({'text': string}, ('text',)), 'delivery': string, 'time': obj({})}
        schemas = {'Location': location, 'Model': model, 'Info': info,
                   'Inbox': obj(inbox_fields, inbox_fields)}

        def op(identifier, data, payload=None, session=True):
            operation = {'operationId': identifier, 'responses': {'200': {'content': {
                'application/json': {'schema': obj({'data': data}, ('data',))}}}}}
            if payload is not None:
                operation['requestBody'] = {'content': {'application/json': {'schema': payload}}}
            if session:
                operation['parameters'] = [{'name': 'sessionID', 'in': 'path', 'required': True,
                                            'schema': string}]
            return operation

        create = op('session.create', {'$ref': '#/components/schemas/Info'}, obj({
            **{key: string for key in ('id', 'parentID', 'title', 'agent', 'metadata', 'permissions')},
            'location': nullable({'$ref': '#/components/schemas/Location'}),
            'model': nullable({'$ref': '#/components/schemas/Model'})}), session=False)
        prompt = op('session.prompt', {'$ref': '#/components/schemas/Inbox'}, obj({
            'id': string, 'text': string, 'files': {'type': 'array'}, 'agents': {'type': 'array'},
            'delivery': nullable({'type': 'string', 'enum': ['steer', 'queue']}),
            'resume': nullable({'type': 'boolean'})}, ('text',)))
        active = op('session.active', {'type': 'object', 'additionalProperties': False,
                    'patternProperties': {'^ses': obj({
                        'type': {'type': 'string', 'enum': ['running']}}, ('type',))}}, session=False)
        for kind in ('user', 'assistant'):
            fields = {'id': string, 'time': obj({'created': {'type': 'number'}}, ('created',)),
                      'type': {'type': 'string', 'enum': [kind]}}
            fields.update({'text': string} if kind == 'user' else {
                'model': {'$ref': '#/components/schemas/Model'}, 'content': {'type': 'array'}})
            schemas[kind] = obj(fields, fields)
        schemas['Message'] = {'anyOf': [{'$ref': '#/components/schemas/' + kind}
                                        for kind in ('user', 'assistant')]}
        # The actual Info union also includes a nested Compaction union.
        schemas['Compaction'] = {'anyOf': [obj({
            'id': string, 'time': obj({'created': {'type': 'number'}}, ('created',)),
            'type': {'type': 'string', 'enum': ['compaction']}}, ('id', 'time', 'type'))]}
        schemas['Message']['anyOf'].append({'$ref': '#/components/schemas/Compaction'})
        message_ref = {'$ref': '#/components/schemas/Message'}
        context = op('session.context', {'type': 'array', 'items': message_ref})
        message = op('session.message.get', message_ref)
        message['parameters'].append({'name': 'messageID', 'in': 'path', 'required': True, 'schema': string})
        return {'components': {'schemas': schemas}, 'paths': {
            '/api/session': {'post': create},
            '/api/session/{sessionID}': {'get': op('session.get', {'$ref': '#/components/schemas/Info'})},
            '/api/session/{sessionID}/prompt': {'post': prompt},
            '/api/session/active': {'get': active},
            '/api/session/{sessionID}/context': {'get': context},
            '/api/session/{sessionID}/message/{messageID}': {'get': message}}}

    def test_accepts_resolved_current_wire_structure(self):
        runpy.run_path(str(FIXTURE / 'verify-user.py'))['validate_api_schema'](self.spec())

    def test_rejects_matching_operation_names_with_incompatible_structures(self):
        validate = runpy.run_path(str(FIXTURE / 'verify-user.py'))['validate_api_schema']
        original = self.spec()
        for case in ('operation', 'location', 'model', 'envelope', 'prompt', 'inbox', 'active',
                     'context-param', 'message-param', 'context-array', 'message-operation',
                     'cycle', 'user-text', 'assistant-model', 'assistant-content', 'message-time',
                     'missing-user', 'missing-assistant'):
            spec = copy.deepcopy(original)
            schemas = spec['components']['schemas']
            paths = spec['paths']
            create = paths['/api/session']['post']
            prompt = paths['/api/session/{sessionID}/prompt']['post']
            if case == 'operation':
                create['operationId'] = 'v2.session.create'
            elif case == 'location':
                schemas['Location']['properties']['directory'] = {'type': 'integer'}
            elif case == 'model':
                schemas['Model']['required'] = []
            elif case == 'envelope':
                del create['responses']['200']['content']['application/json']['schema']['properties']['data']
            elif case == 'prompt':
                fields = prompt['requestBody']['content']['application/json']['schema']['properties']
                fields['prompt'] = fields.pop('text')
            elif case == 'inbox':
                schemas['Inbox']['properties']['type']['enum'] = ['assistant']
            elif case == 'active':
                paths['/api/session/active']['get']['responses']['200']['content']['application/json'][
                    'schema']['properties']['data']['patternProperties']['^ses']['properties'][
                        'type']['enum'] = ['idle']
            elif case == 'context-param':
                paths['/api/session/{sessionID}/context']['get']['parameters'][0]['required'] = False
            elif case == 'message-param':
                paths['/api/session/{sessionID}/message/{messageID}']['get']['parameters'].pop()
            elif case == 'context-array':
                paths['/api/session/{sessionID}/context']['get']['responses']['200']['content'][
                    'application/json']['schema']['properties']['data']['type'] = 'object'
            elif case == 'message-operation':
                paths['/api/session/{sessionID}/message/{messageID}']['get']['operationId'] = 'wrong'
            elif case == 'cycle':
                schemas['Location'] = {'$ref': '#/components/schemas/Location'}
            elif case == 'user-text':
                schemas['user']['properties']['text'] = {'type': 'object'}
            elif case == 'assistant-model':
                schemas['assistant']['required'].remove('model')
            elif case == 'assistant-content':
                schemas['assistant']['properties']['content']['type'] = 'object'
            elif case == 'message-time':
                schemas['assistant']['properties']['time']['required'] = []
            elif case == 'missing-user':
                schemas['Message']['anyOf'].pop(0)
            elif case == 'missing-assistant':
                schemas['Message']['anyOf'].pop(1)
            with self.subTest(case=case), self.assertRaises((RuntimeError, KeyError)):
                validate(spec)


class LoopbackProviderTests(unittest.TestCase):
    """Synthetic local HTTP only: no native code, fixture HOME or host state."""

    def provider(self):
        tree = ast.parse((FIXTURE / 'verify-user.py').read_text())
        # Compile only the isolated provider and its stdlib imports, not fixture setup.
        nodes: list[ast.stmt] = [node for node in tree.body if
                 (isinstance(node, ast.Import) and all(alias.name in {'json', 'threading', 'uuid'}
                                                       for alias in node.names)) or
                 (isinstance(node, ast.ImportFrom) and node.module == 'http.server') or
                 (isinstance(node, (ast.FunctionDef, ast.ClassDef)) and
                   node.name in {'require', 'CommandFailure', 'HeldProvider'})]
        namespace = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<loopback-provider>', 'exec'), namespace)
        return namespace['HeldProvider']()

    def request(self, provider, *, path='/v1/chat/completions', session='ses_synthetic', body=None):
        connection = http.client.HTTPConnection('127.0.0.1', provider.server.server_port, timeout=5)
        self.addCleanup(connection.close)
        payload = {'model': 'held', 'stream': True,
                   'messages': [{'role': 'user', 'content': provider.nonce}]} if body is None else body
        connection.request('POST', path, json.dumps(payload),
                           {'Content-Type': 'application/json', 'X-Session-Id': session,
                            'x-session-affinity': 'ses_synthetic'})
        return connection.getresponse()

    def test_stream_is_held_until_explicit_release_then_completes_once(self):
        with self.provider() as provider:
            provider.session_id = 'ses_synthetic'
            config = provider.config()
            self.assertEqual(set(config['providers']), {'rrw007f'})
            self.assertEqual(config['update'], 'disable')
            self.assertEqual(config['providers']['rrw007f']['package'],
                             '@opencode/ai/providers/openai-compatible')
            self.assertEqual(config['providers']['rrw007f']['settings'], {
                'baseURL': 'http://127.0.0.1:' + str(provider.server.server_port) + '/v1'})
            self.assertNotRegex(json.dumps(config), r'apiKey|credential|authorization|integration|env')
            response = self.request(provider)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.version, 11)
            self.assertEqual(response.getheader('Transfer-Encoding'), 'chunked')
            self.assertEqual(response.getheader('Content-Type'), 'text/event-stream')
            first = json.loads(response.readline().decode().removeprefix('data: '))
            self.assertEqual(first['choices'][0]['delta']['content'], 'RRW007F-BEGIN:')
            self.assertTrue(provider.held.wait(5))
            self.assertFalse(provider.done.is_set())
            self.assertFalse(provider.release.is_set())
            provider.check()
            provider.release.set()
            tail = response.read().decode()
            self.assertIn(provider.nonce + ':END', tail)
            self.assertIn('"finish_reason": "stop"', tail)
            self.assertIn('"total_tokens": 2', tail)
            self.assertTrue(tail.endswith('data: [DONE]\n\n'))
            self.assertTrue(provider.done.wait(5))
            provider.check()
        self.assertFalse(provider.thread.is_alive())

    def test_rejects_bad_path_model_nonce_session_and_nonstreaming(self):
        for case in ('path', 'model', 'nonce', 'session', 'stream'):
            with self.subTest(case=case), self.provider() as provider:
                provider.session_id = 'ses_synthetic'
                body = {'model': 'held', 'stream': True,
                        'messages': [{'role': 'user', 'content': provider.nonce}]}
                if case in {'model', 'stream'}:
                    body[case] = 'wrong'
                if case == 'nonce':
                    body['messages'][0]['content'] = 'wrong'
                with self.assertRaises((http.client.HTTPException, OSError)):
                    self.request(provider, path='/wrong' if case == 'path' else '/v1/chat/completions',
                                 session='wrong' if case == 'session' else 'ses_synthetic', body=body)
                self.assertTrue(provider.done.wait(5))
                self.assertTrue(provider.failed)
                self.assertFalse(provider.held.is_set())
                with self.assertRaises(RuntimeError):
                    provider.check()

    def test_cleanup_releases_held_worker_and_duplicate_request_fails(self):
        with self.provider() as provider:
            provider.session_id = 'ses_synthetic'
            response = self.request(provider)
            self.assertTrue(provider.held.wait(5))
            with self.assertRaises((http.client.HTTPException, OSError)):
                self.request(provider)
            self.assertEqual(provider.requests, 2)
            with self.assertRaises(RuntimeError):
                provider.check()
        self.assertFalse(provider.thread.is_alive())
        self.assertIn('data: [DONE]', response.read().decode())


if __name__ == '__main__':
    unittest.main()
