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
import tomllib
import unittest

import pytest


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
                                            'unclassified-native-refusal')]:
        Backend.refusal = refusal
        ticks = iter([0, 0, 2])
        monkeypatch.setattr(namespace['time'], 'monotonic', lambda: next(ticks))
        monkeypatch.setattr(namespace['time'], 'sleep', lambda seconds: None)
        try:
            fixture['wait'](lambda: fixture['observe']('herdr-core', {}), seconds=1)
        except fixture['CommandFailure'] as error:
            assert error.reason == label
            assert namespace['STEP'] == 'observe-herdr-core-verify'
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
                    "pending.pop('identity')", 'original_receipt(receipt)',
                    'backend._terminal(address) != snapshot', 'result = copy.deepcopy(result)',
                    "Controller(store, backend).restore()", "cli('restore')",
                    'original_core(method, params)', 'kills == 0',
                    "pending['pids'] == shell_pids", "('identity' in pending) == lost_reply",
                    "backend._terminal(address)['state'] == 'live'",
                    "backend._pid_proofs([p['pid'] for p in shell_pids]) == shell_pids",
                    "backend._terminal(address)['state'] == 'finished'",
                    'backend._pids_absent(shell_pids)', "before['clients']", "before['pids']",
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
    assert body.index("pending.pop('identity')") < body.index('original_receipt(receipt)')
    assert body.index('original_receipt(receipt)') < body.index('churned = True')
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


@pytest.mark.parametrize('address', ['t7', 'ta', 't10'])
def test_r2_native_label_transport_is_fixed_bounded_and_preserves_ownership(monkeypatch, address):
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


class QualificationSourceTests(unittest.TestCase):
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
                        "cli('restore')", "cli('recover')", "backend._pids_absent(before['clients'])",
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
