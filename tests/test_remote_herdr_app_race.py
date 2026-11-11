"""Synthetic connected-app repair ordering; never contacts a native runtime."""
import copy
import sqlite3

import pytest

from test_remote_herdr_native import (
    FakeCore, backend, manifest_for, native, plan, runtime_controller, synthetic_process, wrapper_argv,
)


class AppCore(FakeCore):
    def rpc(self, method, params):
        result = super().rpc(method, params)
        if method == 'terminal.kill':
            assert self.document is not None
            finished = {a for a, t in self.terminals.items() if t['state'] == 'finished'}
            def prune(node):
                if node.get('type') == 'block':
                    return None if (node.get('content') or {}).get('terminal') in finished else node
                if 'children' in node:
                    node['children'] = [p for n in node['children'] if (p := prune(n)) is not None]
                return node
            before = copy.deepcopy(self.document)
            # App-shaped trees are inspected independently of the adapter's rebind helper.
            for space in self.document['spaces']:
                retained = []
                for tab in space['tabs']:
                    root = prune(tab['root'])
                    if root is not None:
                        tab['root'] = root
                        retained.append(tab)
                space['tabs'] = retained
            if before != self.document:
                self.version += 1
        return result


def test_r3_connected_app_rebinds_before_old_shell_finishes(backend):
    core = AppCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    core.calls.clear()
    backend.restore_current()
    effects = [m for m, _ in core.calls if m in ('terminal.run', 'doc.set', 'terminal.kill')]
    assert effects == ['terminal.run', 'doc.set', 'terminal.kill']
    receipt = backend.store.read('manifest.json')['receipt']
    assert receipt['terminals'] == {'s0-t0-p0': 't2'}
    assert core.terminals['t2']['state'] == 'live'
    assert core.terminals['t1']['state'] == 'finished'
    assert receipt['pending'] is None and receipt['repairs'] == {}


def test_r4_restart_legacy_unbound_shells_and_stopped_closed_leaf(backend):
    core, retained = mixed_legacy(backend, controller_seed=True)
    # Resolve the R3 gone-run intent through its writer; the reported R4 state
    # has no pending effect, but still has the closed stopped repair in history.
    backend._reconcile_current_intent(copy.deepcopy(retained))
    core.restart()
    journal = backend.store.read('transaction.json')
    before = copy.deepcopy(core.document)
    core.calls.clear()
    runtime_controller.Controller(backend.store, backend).recover()
    final = backend.store.read('manifest.json')['receipt']
    assert len(final['bindings']) == 62
    assert final['pending'] is None and final['repairs'] == {}
    assert backend.store.read('transaction.json') == journal
    assert [tab['root']['id'] for tab in core.document['spaces'][0]['tabs']] == [
        tab['root']['id'] for tab in before['spaces'][0]['tabs']]
    assert all(core.terminals[f't{i}']['state'] == 'finished' for i in (1, 2, 3))
    assert len(backend.scan(native.sessions(final['plan']))) == 54
    for _ in range(2):
        core.restart()
        runtime_controller.Controller(backend.store, backend).recover()
        current = backend.store.read('manifest.json')['receipt']
        assert len(current['bindings']) == 62
        assert current['pending'] is None and current['repairs'] == {}
        assert len(backend.scan(native.sessions(current['plan']))) == 54


@pytest.mark.parametrize('lost,restart_again', [(False, False), (True, False), (False, True), (True, True)])
def test_r4_shell_hop_cas_intent_survives_interrupt_and_second_restart(backend, lost, restart_again):
    core, retained = mixed_legacy(backend, 6, 4, controller_seed=True)
    backend._reconcile_current_intent(copy.deepcopy(retained))
    core.restart()
    def interrupted(method, params):
        if method == 'doc.set' and not lost:
            raise native.NativeError('synthetic interruption')
        result = core.rpc(method, params)
        if method == 'doc.set' and lost:
            raise native.NativeError('synthetic interruption')
        return result
    backend.core = interrupted
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['retained_shell'] is True
    backend._binding_receipt(saved['plan'], saved, 'testtx', 2)
    backend.core = core.rpc
    if restart_again:
        core.restart()
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(final['bindings']) == 5
    assert len(backend.scan(native.sessions(final['plan']))) == 4


@pytest.mark.parametrize('change', ['owner', 'cwd', 'program', 'external', 'duplicate', 'old-pid', 'foreign-leaf'])
def test_r4_unbound_shell_negative_does_not_mutate_or_kill(backend, change):
    core, retained = mixed_legacy(backend, 6, 4, controller_seed=True)
    backend._reconcile_current_intent(copy.deepcopy(retained))
    # An old PID is a negative only when its captured boot still matches.
    # A different proven boot means the old identity really did exit.
    core.restart(same_boot=change == 'old-pid')
    repair = retained['repairs']['app-leaf-0']
    terminal = core.terminals[repair['created']]
    if change == 'owner':
        terminal['labels']['remote-herdr-owner'] = 'foreign'
    elif change == 'cwd':
        synthetic_process(backend, terminal['pid'], ['/bin/bash', '-l'], '/wrong')
    elif change == 'program':
        synthetic_process(backend, terminal['pid'], ['/bin/foreign'])
    elif change == 'external':
        synthetic_process(backend, 998, wrapper_argv(backend, repair['pane']['session_id']))
    elif change == 'duplicate':
        duplicate = copy.deepcopy(terminal)
        duplicate['address'] = 'duplicate'
        core.terminals['duplicate'] = duplicate
    elif change == 'old-pid':
        proof = repair['pids'][0]
        synthetic_process(backend, proof['pid'], ['/bin/bash', '-l'], ticks=proof['start_ticks'])
    else:
        core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] = 'foreign'
        core.version += 1
    core.calls.clear()
    saved = backend.store.read('receipt-testtx.json')
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('doc.set', 'terminal.run', 'terminal.kill') for m, _ in core.calls)
    assert backend.store.read('receipt-testtx.json') == saved


@pytest.mark.parametrize('operation,lost', [('terminal.kill', False), ('terminal.kill', True),
                                           ('server.stop', False), ('server.stop', True)])
def test_r4_restart_after_interrupted_idle_stop(backend, operation, lost):
    # Stop itself is not an R3 repair: use the non-pruning core, whose native
    # records and document remain available after controller stop.
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    captured = backend.capture('herdr-core')
    rpc, command = core.rpc, core.command
    def interrupted_rpc(method, params):
        if operation == method and not lost:
            raise native.NativeError('synthetic interruption')
        result = rpc(method, params)
        if operation == method and lost:
            raise native.NativeError('synthetic interruption')
        return result
    def interrupted_command(argv, timeout=30):
        stopping = argv == ['herdr-core', 'server', 'stop', '--json']
        if operation == 'server.stop' and stopping and not lost:
            raise native.NativeError('synthetic interruption')
        result = command(argv, timeout)
        if operation == 'server.stop' and stopping and lost:
            raise native.NativeError('synthetic interruption')
        return result
    backend.core, backend.command = interrupted_rpc, interrupted_command
    with pytest.raises(native.NativeError):
        backend.stop('herdr-core', captured)
    assert backend.store.read('source-stop.json')['completed'] is False
    backend.core, backend.command = rpc, command
    core.restart()
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1
    assert backend.store.read('source-stop.json')['completed'] is True


def test_r4_idle_stop_published_none_checkpoint_recovers_after_boot(backend):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    captured = backend.capture('herdr-core')
    write = backend.store.write
    def checkpoint(name, value):
        write(name, value)
        if (name == 'source-stop.json' and value.get('completed') is False
                and value['pending'] is None and value['terminals']):
            raise native.NativeError('synthetic interruption at published checkpoint')
    backend.store.write = checkpoint
    with pytest.raises(native.NativeError):
        backend.stop('herdr-core', captured)
    backend.store.write = write
    stop = backend.store.read('source-stop.json')
    assert stop['pending'] is None and stop['completed'] is False
    core.restart()
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1
    assert backend.store.read('source-stop.json')['completed'] is True


@pytest.mark.parametrize('foreign', [False, True])
def test_r4_idle_stop_checkpoint_warm_original_client_continues_only_under_proof(backend, foreign):
    core = FakeCore(backend)
    value = plan()
    tab = copy.deepcopy(value['spaces'][0]['tabs'][0])
    tab['name'] = 'Second'
    tab['root']['pane'] = tab['panes'][0]['key'] = 's0-t1-p0'
    tab['panes'][0]['session_id'] = 'ses_second'
    value['spaces'][0]['tabs'].append(tab)
    with sqlite3.connect(backend.database_path()) as db:
        db.execute('INSERT INTO session VALUES (?, ?)', ('ses_second', '/work'))
    manifest_for(backend, core, value)
    backend.restore_current()
    capture = backend.capture('herdr-core')
    write = backend.store.write
    def checkpoint(name, value):
        write(name, value)
        if (name == 'source-stop.json' and value.get('completed') is False
                and value['pending'] is None and value['terminals']):
            raise native.NativeError('synthetic published checkpoint')
    backend.store.write = checkpoint
    with pytest.raises(native.NativeError):
        backend.stop('herdr-core', capture)
    backend.store.write = write
    core.restart(keep_processes=True)
    assert len(backend.scan({'ses_second'})) == 1
    if foreign:
        def drift(name, value):
            write(name, value)
            if name == 'source-stop.json' and value.get('pending') == {'operation': 'terminal.kill', 'terminal': 't2'}:
                synthetic_process(backend, core.terminals['t2']['pid'], ['/foreign'])
        backend.store.write = drift
    core.calls.clear()
    if foreign:
        with pytest.raises(native.NativeError):
            backend.restore_current()
        assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls)
        assert backend.store.read('source-stop.json')['completed'] is False
        assert core.terminals['t2']['state'] == 'live'
    else:
        backend.restore_current()
        final = backend.store.read('manifest.json')['receipt']
        assert final['pending'] is None and final['repairs'] == {}
        assert len(backend.scan({'ses_abc', 'ses_second'})) == 2
        assert [p['terminal'] for m, p in core.calls if m == 'terminal.kill'] == ['t2']
        assert core.terminals['t1']['state'] == core.terminals['t2']['state'] == 'finished'
        assert backend.store.read('source-stop.json')['completed'] is True


@pytest.mark.parametrize('boundary', ['run-reply', 'readiness'])
def test_r4_stopped_source_pending_run_returns_as_shell(backend, boundary):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    backend.stop('herdr-core', backend.capture('herdr-core'))
    core.active = True
    original_wait = backend._wait_created_core
    def lost_run(method, params):
        answer = core.rpc(method, params)
        if method == 'terminal.run' and boundary == 'run-reply':
            raise native.NativeError('synthetic interruption')
        return answer
    def readiness(*args):
        raise native.NativeError('synthetic interruption')
    backend.core = lost_run
    if boundary == 'readiness':
        backend._wait_created_core = readiness
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['operation'] == 'terminal.run'
    backend.core, backend._wait_created_core = core.rpc, original_wait
    core.restart()
    core.calls.clear()
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1
    assert [m for m, _ in core.calls if m in ('terminal.run', 'doc.set', 'terminal.kill')] == [
        'doc.set', 'terminal.run', 'doc.set', 'terminal.kill']


def test_r4_restart_after_completed_leaf_and_next_source_capture(backend):
    core = AppCore(backend)
    value = plan()
    tab = copy.deepcopy(value['spaces'][0]['tabs'][0])
    tab['name'] = 'Second'
    tab['root']['pane'] = tab['panes'][0]['key'] = 's0-t1-p0'
    tab['panes'][0]['session_id'] = 'ses_second'
    value['spaces'][0]['tabs'].append(tab)
    with sqlite3.connect(backend.database_path()) as db:
        db.execute('INSERT INTO session VALUES (?, ?)', ('ses_second', '/work'))
    manifest_for(backend, core, value)
    core.restart()
    publish = backend._receipt
    def interrupted(receipt):
        publish(receipt)
        repair = receipt.get('repairs', {}).get('s0-t1-p0', {})
        if (repair.get('source') and 's0-t0-p0' not in receipt['repairs']
                and receipt['pending'] is None):
            raise native.NativeError('synthetic interruption')
    backend._receipt = interrupted
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['terminals']['s0-t0-p0'] == 't3'
    old_source = saved['repairs']['s0-t1-p0']['pids']
    backend._receipt = publish
    core.restart()
    assert backend._pids_absent(old_source)
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(final['bindings']) == 2
    assert len(backend.scan({'ses_abc', 'ses_second'})) == 2


@pytest.mark.parametrize('lost', [False, True])
def test_r4_stopped_source_client_cas_reconciles_shell_after_restart(backend, lost):
    core = FakeCore(backend)
    manifest_for(backend, core)
    backend.restore_current()
    backend.stop('herdr-core', backend.capture('herdr-core'))
    core.active = True
    def interrupted(method, params):
        if method == 'doc.set' and not lost:
            raise native.NativeError('synthetic interruption')
        answer = core.rpc(method, params)
        if method == 'doc.set' and lost:
            raise native.NativeError('synthetic interruption')
        return answer
    backend.core = interrupted
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['operation'] == 'doc.set'
    assert 'retained_shell' not in saved['pending']
    backend.core = core.rpc
    core.restart()
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1


def test_r4_post_cas_old_kill_lost_reply_then_restart(backend):
    core = AppCore(backend)
    manifest_for(backend, core)
    core.restart()
    def interrupted(method, params):
        answer = core.rpc(method, params)
        if method == 'terminal.kill':
            raise native.NativeError('synthetic interruption')
        return answer
    backend.core = interrupted
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['operation'] == 'terminal.kill'
    assert 'rebound' in saved['pending']
    assert core.terminals['t1']['state'] == 'finished'
    backend.core = core.rpc
    core.restart()
    core.calls.clear()
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1
    assert [p['terminal'] for m, p in core.calls if m == 'terminal.kill'] == ['t2']
    assert core.document is not None
    assert core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] == 't3'


@pytest.mark.parametrize('boundary,lost', [('terminal.run', True), ('doc.set', False),
                                         ('doc.set', True), ('terminal.kill', False), ('readiness', False)])
def test_r4_two_live_shell_sources_converge_after_restart(backend, boundary, lost):
    core = AppCore(backend)
    manifest_for(backend, core)
    core.restart()
    def interrupted(method, params):
        if method == boundary and not lost:
            raise native.NativeError('synthetic interruption')
        answer = core.rpc(method, params)
        if method == boundary and lost:
            raise native.NativeError('synthetic interruption')
        return answer
    backend.core = interrupted
    wait = backend._wait_created_core
    if boundary == 'readiness':
        def unready(*args):
            raise native.NativeError('synthetic interruption')
        backend._wait_created_core = unready
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    backend.core = core.rpc
    backend._wait_created_core = wait
    core.restart()
    core.calls.clear()
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1
    assert core.terminals['t1']['state'] == core.terminals['t2']['state'] == 'finished'
    assert [p['terminal'] for m, p in core.calls if m == 'terminal.kill'] == ['t1', 't2']
    assert core.document is not None
    assert core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] == 't3'
    assert saved['pending'] is not None
    for _ in range(2):
        core.restart()
        backend.restore_current()
        assert len(backend.scan({'ses_abc'})) == 1
        current = backend.store.read('manifest.json')['receipt']
        assert current['pending'] is None and current['repairs'] == {}
        document, version = copy.deepcopy(core.document), core.version
        before = len(core.calls)
        core.restart(keep_processes=True)
        backend.restore_current()
        assert core.document == document and core.version == version
        assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('phase,lost', [('doc.set', False), ('doc.set', True),
                                      ('terminal.kill', False), ('terminal.kill', True),
                                      ('publish-hop', False), ('publish-cleanup', False)])
@pytest.mark.parametrize('restart_mode', ['cold', 'kept', 'same-boot-shells'])
def test_r4_dual_source_shell_hop_cleanup_interruptions(backend, phase, lost, restart_mode):
    core = AppCore(backend)
    manifest_for(backend, core)
    core.restart()
    def lost_original_run(method, params):
        answer = core.rpc(method, params)
        if method == 'terminal.run':
            raise native.NativeError('synthetic lost original run reply')
        return answer
    backend.core = lost_original_run
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core = core.rpc
    core.restart()
    publish = backend._receipt
    def fault(method, params):
        if method == phase and not lost:
            raise native.NativeError('synthetic shell-hop interruption')
        answer = core.rpc(method, params)
        if method == phase and lost:
            raise native.NativeError('synthetic shell-hop lost reply')
        return answer
    def persist(receipt):
        publish(receipt)
        pending = receipt.get('pending') or {}
        operation = {'publish-hop': 'doc.set', 'publish-cleanup': 'terminal.kill'}.get(phase)
        if pending.get('retained_shell') is True and pending.get('operation') == operation:
            raise native.NativeError('synthetic interruption after source-proof publication')
    backend.core, backend._receipt = fault, persist
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['retained_shell'] is True
    backend._binding_receipt(saved['plan'], saved, 'testtx', 2)
    assert backend.store.read(saved['adoption_backup']) is not None
    backend.core, backend._receipt = core.rpc, publish
    boot = backend.test_boot_id
    core.restart(keep_processes=restart_mode == 'kept', same_boot=restart_mode == 'same-boot-shells')
    assert (backend.test_boot_id == boot) == (restart_mode != 'cold')
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1
    assert core.terminals['t1']['state'] == core.terminals['t2']['state'] == 'finished'
    assert core.document is not None
    assert core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] == 't3'
    before = len(core.calls)
    backend.restore_current()
    assert not any(m in ('terminal.run', 'terminal.kill', 'doc.set') for m, _ in core.calls[before:])


@pytest.mark.parametrize('phase,lost', [('terminal.run', True), ('doc.set', False),
                                      ('doc.set', True), ('terminal.kill', False), ('readiness', False)])
def test_r4_restart_keeps_ready_exact_client_but_replaces_source_shell(backend, phase, lost):
    core = AppCore(backend)
    manifest_for(backend, core)
    core.restart()
    wait = backend._wait_created_core
    def fault(method, params):
        if method == phase and not lost:
            raise native.NativeError('synthetic interruption')
        answer = core.rpc(method, params)
        if method == phase and lost:
            raise native.NativeError('synthetic interruption')
        return answer
    def unready(*args):
        raise native.NativeError('synthetic readiness interruption')
    backend.core = fault
    if phase == 'readiness':
        backend._wait_created_core = unready
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core, backend._wait_created_core = core.rpc, wait
    client = copy.deepcopy(core.terminals['t2'])
    client_proof = backend._pid_proofs([client['pid']])
    core.restart(keep_addresses={'t2'})
    core.calls.clear()
    backend.restore_current()
    assert core.terminals['t2'] == client
    assert backend._pid_proofs([client['pid']]) == client_proof
    assert len(backend.scan({'ses_abc'})) == 1
    assert core.terminals['t1']['state'] == 'finished'
    assert not any(m == 'terminal.run' for m, _ in core.calls)
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert final['terminals'] == {'s0-t0-p0': 't2'}


@pytest.mark.parametrize('phase', ['doc.set', 'terminal.kill'])
@pytest.mark.parametrize('bad', ['false', 'null', 'integer', 'extra', 'unwrapped-proof', 'start-bool'])
def test_r4_retained_shell_intents_have_exact_bounded_private_forms(backend, phase, bad):
    core = AppCore(backend)
    manifest_for(backend, core)
    core.restart()
    def lost_run(method, params):
        answer = core.rpc(method, params)
        if method == 'terminal.run':
            raise native.NativeError('synthetic lost run reply')
        return answer
    backend.core = lost_run
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core = core.rpc
    core.restart()
    publish = backend._receipt
    def checkpoint(receipt):
        publish(receipt)
        pending = receipt.get('pending') or {}
        if pending.get('retained_shell') is True and pending.get('operation') == phase:
            raise native.NativeError('synthetic durable intent checkpoint')
    backend._receipt = checkpoint
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    candidate = copy.deepcopy(saved)
    pending = candidate['pending']
    if bad in ('false', 'null', 'integer'):
        pending['retained_shell'] = {'false': False, 'null': None, 'integer': 1}[bad]
    elif bad == 'extra':
        pending['extra'] = True
    else:
        details = pending if phase == 'doc.set' else pending['rebound']
        if bad == 'unwrapped-proof':
            details['replacement'] = details['replacement']['identity']
        else:
            details['replacement']['pids'][0]['start_ticks'] = True
    before = len(core.calls)
    with pytest.raises(native.NativeError):
        backend._binding_receipt(candidate['plan'], candidate, 'testtx', 2)
    assert len(core.calls) == before
    assert backend.store.read('receipt-testtx.json') == saved


@pytest.mark.parametrize('phase', ['doc.set', 'terminal.kill'])
@pytest.mark.parametrize('legacy', [False, True])
def test_r4_retained_shell_restart_exact_pid_start_alias_requires_boot_proof(backend, phase, legacy):
    core = AppCore(backend)
    manifest_for(backend, core)
    core.restart()
    def lost_run(method, params):
        answer = core.rpc(method, params)
        if method == 'terminal.run':
            raise native.NativeError('synthetic lost run reply')
        return answer
    backend.core = lost_run
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core = core.rpc
    core.restart()
    publish = backend._receipt
    def checkpoint(receipt):
        pending = receipt.get('pending') or {}
        if pending.get('retained_shell') is True and pending.get('operation') == phase:
            if legacy:
                # Emulate a pre-boot-proof writer before publication, never
                # hand-edit an already-published receipt or journal.
                receipt = copy.deepcopy(receipt)
                repair = receipt['repairs'][pending['leaf']]
                for proof in repair['pids']:
                    proof.pop('boot_id', None)
                pending = receipt['pending']
                if phase == 'terminal.kill':
                    for proof in pending['pids']:
                        proof.pop('boot_id', None)
                details = pending if phase == 'doc.set' else pending['rebound']
                for proof in details['replacement']['pids']:
                    proof.pop('boot_id', None)
            publish(receipt)
            raise native.NativeError('synthetic durable shell checkpoint')
        publish(receipt)
    backend._receipt = checkpoint
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend._receipt = publish
    saved = backend.store.read('receipt-testtx.json')
    # All old processes really disappear in the fixture. The new boot happens
    # to reuse their PID/start tokens and restores both programs as owned Bash.
    core.restart(reuse_identities=True)
    core.calls.clear()
    if legacy:
        backend._binding_receipt(saved['plan'], saved, 'testtx', 2)
        with pytest.raises(native.NativeError):
            backend.restore_current()
        assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls)
        assert backend.store.read('receipt-testtx.json')['pending'] == saved['pending']
    else:
        def audit(method, params):
            if method == 'terminal.kill':
                intent = backend.store.read('receipt-testtx.json')['pending']
                assert all(p['boot_id'] == backend.process_boot_id() for p in intent['pids'])
            return core.rpc(method, params)
        backend.core = audit
        backend.restore_current()
        assert len(backend.scan({'ses_abc'})) == 1
        assert core.terminals['t1']['state'] == core.terminals['t2']['state'] == 'finished'
        final = backend.store.read('manifest.json')['receipt']
        assert final['pending'] is None and final['repairs'] == {}


def test_r4_legacy_two_field_stopped_proofs_recover_when_identity_is_absent(backend):
    publish = backend._receipt
    def legacy_writer(receipt):
        receipt = copy.deepcopy(receipt)
        for repair in receipt.get('repairs', {}).values():
            for proof in repair.get('pids') or []:
                proof.pop('boot_id', None)
        publish(receipt)
    backend._receipt = legacy_writer
    core, retained = mixed_legacy(backend, 6, 4, controller_seed=True)
    backend._reconcile_current_intent(copy.deepcopy(retained))
    backend._receipt = publish
    saved = backend.store.read('receipt-testtx.json')
    assert all(set(p) == {'pid', 'start_ticks'} for repair in saved['repairs'].values()
               for p in repair['pids'] or [])
    backend._binding_receipt(saved['plan'], saved, 'testtx', 2)
    core.restart()
    runtime_controller.Controller(backend.store, backend).recover()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(final['bindings']) == 5
    assert len(backend.scan(native.sessions(final['plan']))) == 4
    assert any(value.get('receipt', {}).get('repairs') == saved['repairs']
               for name, value in backend.store.values.items() if name.startswith('backup-'))


def test_r4_different_boot_pid_reuse_never_kills_unrelated_new_process(backend):
    core, retained = mixed_legacy(backend, 6, 4, controller_seed=True)
    backend._reconcile_current_intent(copy.deepcopy(retained))
    old = retained['repairs']['app-leaf-0']['pids'][0]
    core.restart()
    assert backend.test_boot_id != old['boot_id']
    synthetic_process(backend, old['pid'], ['/bin/bash', '-l'], '/unrelated', ticks=old['start_ticks'])
    before = backend._pid_proofs([old['pid']])
    backend.restore_current()
    assert backend._pid_proofs([old['pid']]) == before
    assert backend.process_cwd(old['pid']) == '/unrelated'
    assert backend.process_argv(old['pid']) == ['/bin/bash', '-l']
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}


@pytest.mark.parametrize('phase', ['doc.set', 'terminal.kill'])
@pytest.mark.parametrize('unavailable', [None, 'PRIVATE_VALUE', 'missing'])
def test_r4_boot_read_failure_after_intent_never_mutates_native_state(backend, phase, unavailable):
    core = AppCore(backend)
    manifest_for(backend, core)
    core.restart()
    def lost_run(method, params):
        answer = core.rpc(method, params)
        if method == 'terminal.run':
            raise native.NativeError('synthetic lost run reply')
        return answer
    backend.core = lost_run
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core = core.rpc
    core.restart()
    publish, read_boot = backend._receipt, backend.process_boot_id
    valid_boot = backend.test_boot_id
    def unavailable_after_publish(receipt):
        publish(receipt)
        pending = receipt.get('pending') or {}
        if pending.get('retained_shell') is True and pending.get('operation') == phase:
            if unavailable == 'missing':
                backend.process_boot_id = lambda: native.Native.process_boot_id(backend)
            else:
                backend.test_boot_id = unavailable
    backend._receipt = unavailable_after_publish
    core.calls.clear()
    with pytest.raises(native.NativeError, match='^native boot identity unavailable$'):
        backend.restore_current()
    effects = [m for m, _ in core.calls if m in ('terminal.run', 'terminal.kill', 'doc.set')]
    assert effects == ([] if phase == 'doc.set' else ['doc.set'])
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['operation'] == phase and saved['pending']['retained_shell'] is True
    assert core.terminals['t1']['state'] == core.terminals['t2']['state'] == 'live'
    backend._receipt, backend.process_boot_id, backend.test_boot_id = publish, read_boot, valid_boot
    backend.restore_current()
    final = backend.store.read('manifest.json')['receipt']
    assert final['pending'] is None and final['repairs'] == {}
    assert len(backend.scan({'ses_abc'})) == 1


@pytest.mark.parametrize('change', ['version', 'foreign-leaf', 'labels', 'cwd', 'argv', 'start'])
def test_r4_shell_hop_rechecks_after_durable_intent(backend, change):
    core, retained = mixed_legacy(backend, 6, 4, controller_seed=True)
    backend._reconcile_current_intent(copy.deepcopy(retained))
    core.restart()
    publish = backend._receipt
    injected = False
    def persist(receipt):
        nonlocal injected
        publish(receipt)
        pending = receipt.get('pending') or {}
        if injected or pending.get('retained_shell') is not True:
            return
        injected = True
        shell = core.terminals[receipt['repairs'][pending['leaf']]['created']]
        if change == 'version':
            core.version += 1
        elif change == 'foreign-leaf':
            core.document['spaces'][0]['tabs'][-1]['root']['content']['terminal'] = 'foreign'
            core.version += 1
        elif change == 'labels':
            shell['labels']['remote-herdr-extra'] = 'unowned'
        else:
            synthetic_process(backend, shell['pid'], ['/foreign'] if change == 'argv' else ['/bin/bash', '-l'],
                              '/wrong' if change == 'cwd' else '/work', ticks=999 if change == 'start' else 101)
    backend._receipt = persist
    core.calls.clear()
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert injected
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls)
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['retained_shell'] is True
    backend._binding_receipt(saved['plan'], saved, 'testtx', 2)


@pytest.mark.parametrize('operation,lost', [
    ('terminal.run', False), ('terminal.run', True), ('doc.set', False), ('doc.set', True),
    ('terminal.kill', False), ('terminal.kill', True), ('readiness', False),
])
def test_r3_interruptions_preserve_proofs_without_replay(backend, operation, lost):
    core = AppCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    core.calls.clear()
    def interrupted(method, params):
        if method == operation and not lost:
            raise native.NativeError('synthetic interruption')
        result = core.rpc(method, params)
        if method == operation and lost:
            raise native.NativeError('synthetic interruption')
        return result
    backend.core = interrupted
    wait = backend._wait_created_core
    if operation == 'readiness':
        def unready(*args):
            raise native.NativeError('synthetic interruption')
        backend._wait_created_core = unready
    with pytest.raises(native.NativeError):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    backend._binding_receipt(saved['plan'], saved, 'testtx', 2)
    assert saved['pending'] is not None
    backend.core = core.rpc
    backend._wait_created_core = wait
    if operation in ('terminal.run', 'doc.set') and not lost:
        # Zero matches / unchanged preimage cannot prove an admitted effect failed.
        before = len(core.calls)
        with pytest.raises(native.NativeError):
            backend.restore_current()
        assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls[before:])
        assert backend.store.read('receipt-testtx.json')['pending'] == saved['pending']
        return
    backend.restore_current()
    assert [m for m, _ in core.calls if m in ('terminal.run', 'doc.set', 'terminal.kill')] == [
        'terminal.run', 'doc.set', 'terminal.kill']
    assert core.document is not None
    assert core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] == 't2'
    before = len(core.calls)
    backend.restore_current()
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls[before:])


def mixed_legacy(backend, count=63, repair_count=54, *, controller_seed=False):
    core = AppCore(backend)
    value = plan()
    tabs = value['spaces'][0]['tabs']
    tabs.clear()
    with sqlite3.connect(backend.database_path()) as db:
        for i in range(count):
            session = f'ses_mixed{i}' if i < repair_count + 1 else None
            if session:
                db.execute('INSERT INTO session VALUES (?, ?)', (session, '/work'))
            key = f's0-t{i}-p0'
            tabs.append({'name': f'Tab {i}', 'root': {'pane': key},
                         'panes': [{'key': key, 'cwd': '/work', 'session_id': session}]})
    if controller_seed:
        class SeedController(runtime_controller.Controller):
            def _journal(self, journal, phase):
                # Deterministic synthetic transaction identity; the original
                # controller remains the journal/manifest publication owner.
                journal['txid'] = 'testtx'
                super()._journal(journal, phase)
        backend.selected = lambda: 'tui'
        def select(target):
            backend.selected = lambda: target
        backend.select = select
        SeedController(backend.store, backend).switch('herdr-core', imported=value)
    else:
        manifest_for(backend, core, value)
    assert core.document is not None
    for i, tab in enumerate(core.document['spaces'][0]['tabs']):
        tab['root']['id'] = f'app-leaf-{i}'
        tab['opaque'] = {'preserve': [True, None, i]}
    core.version += 1
    backend.restore_current()
    manifest = backend.store.read('manifest.json')
    receipt = copy.deepcopy(manifest['receipt'])
    for i in range(repair_count):
        synthetic_process(backend, core.terminals[f't{i + 1}']['pid'], ['/bin/bash', '-l'])
    projected, bindings, labels, repairs = backend._current_projection(
        core.document, backend._terminals(), manifest['plan'], receipt)
    # Serialize the retained pre-generation R1/R2 repair form, not new R3 intents.
    for repair in repairs.values():
        repair.pop('create_id', None)
        repair['labels'].pop('remote-herdr-repair', None)
    receipt.update(plan=projected, repairs=repairs)
    receipt['adoption_backup'] = backend._backup({'manifest': manifest, 'receipt': receipt})
    for i in range(3):
        repair = repairs[f'app-leaf-{i}']
        terminal = core.terminals[repair['terminal']]
        repair['pids'] = backend._pid_proofs([terminal['pid']])
        FakeCore.rpc(core, 'terminal.kill', {'terminal': repair['terminal']})
        repair['stopped'] = True
        if i < 2:
            result = core.rpc('terminal.run', {'argv': [str(backend.home / '.local/bin/opencode'), '--session',
                                      repair['pane']['session_id']], 'cwd': '/work', 'labels': repair['labels']})
            repair['created'] = result['address']
    pending = repairs['app-leaf-2']
    receipt['pending'] = {'operation': 'terminal.run', 'pane': 's0-t2-p0', 'leaf': 'app-leaf-2',
                          'labels': pending['labels']}
    backend._receipt(receipt)
    if not controller_seed:
        backend.store.write('transaction.json', {'schema_version': 1, 'txid': 'testtx', 'source': 'tui',
            'target': 'herdr-core', 'phase': 'complete', 'plan': manifest['plan'], 'receipt': manifest['receipt'],
            'history': [{'phase': 'prepared', 'receipt': copy.deepcopy(manifest['receipt'])}, {'phase': 'complete'}]})
    del core.document['spaces'][0]['tabs'][2]
    core.version += 1
    core.calls.clear()
    return core, receipt


@pytest.mark.parametrize('count,repair_count', [(6, 4), (63, 54)])
def test_r3_legacy_mixed_gone_pending_run_rebinds_existing_clients_first(backend, count, repair_count):
    core, receipt = mixed_legacy(backend, count, repair_count)
    synthetic_process(backend, 9010, [str(backend.home / '.opencode/bin/opencode'), 'serve'], cwd='/backend', ticks=42)
    backend_proof = backend._pid_proofs([9010])
    backend_argv = backend.process_argv(9010)
    original = copy.deepcopy(core.document)
    untouched = {a: copy.deepcopy(t) for a, t in core.terminals.items()
                 if a in {f't{i + 1}' for i in range(repair_count, count)}}
    journal = backend.store.read('transaction.json')
    runtime_controller.Controller(backend.store, backend).recover()
    assert backend.store.read('transaction.json') == journal
    effects = [m for m, _ in core.calls if m in ('terminal.run', 'doc.set', 'terminal.kill')]
    assert effects[:2] == ['doc.set', 'doc.set']
    assert effects[2:] == ['terminal.run', 'doc.set', 'terminal.kill'] * (repair_count - 3)
    expected = copy.deepcopy(original)
    for i, tab in enumerate(expected['spaces'][0]['tabs']):
        leaf_index = int(tab['root']['id'].removeprefix('app-leaf-'))
        if leaf_index < repair_count:
            address = f't{count + 1 + leaf_index}' if leaf_index < 2 else f't{count + leaf_index}'
            tab['root']['content']['terminal'] = address
            assert core.terminals[address]['state'] == 'live'
    assert core.document == expected
    assert backend._pid_proofs([9010]) == backend_proof
    assert backend.process_argv(9010) == backend_argv
    assert backend.process_cwd(9010) == '/backend'
    for address, terminal in untouched.items():
        assert core.terminals[address] == terminal
    final = backend.store.read('manifest.json')
    assert len(final['receipt']['bindings']) == count - 1
    assert final['receipt']['pending'] is None and final['receipt']['repairs'] == {}
    assert backend.store.read(receipt['adoption_backup']) is not None
    before = len(core.calls)
    backend.restore_current()
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls[before:])


@pytest.mark.parametrize('owner', ['previous-transaction', 'testtx'])
def test_r3_legacy_finished_session_history_is_not_a_pending_create(backend, owner):
    core, receipt = mixed_legacy(backend, 6, 4)
    for index in range(3):
        historical = copy.deepcopy(core.terminals[f't{index + 1}'])
        address = f'th{index}'
        historical.update(address=address, state='finished', foreground=None,
            labels={'remote-herdr-owner': owner, 'remote-herdr-pane': f's0-t{index}-p0',
                    'remote-herdr-session': f'ses_mixed{index}'})
        core.terminals[address] = historical
    backend._reconcile_current_intent(receipt)
    assert receipt['pending'] is None
    for leaf in ('app-leaf-0', 'app-leaf-1'):
        backend._replacement_proof(receipt['repairs'][leaf])
    assert not any(method in ('terminal.run', 'terminal.kill', 'doc.set') for method, _ in core.calls)


def test_r3_rebound_stop_requires_process_exit_not_rpc_acknowledgement(backend):
    core = AppCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    core.calls.clear()
    def retained_process(method, params):
        if method == 'terminal.kill':
            core.calls.append((method, copy.deepcopy(params)))
            core.terminals[params['terminal']]['state'] = 'finished'
            return copy.deepcopy(core.terminals[params['terminal']])
        return core.rpc(method, params)
    backend.core = retained_process
    with pytest.raises(native.NativeError, match='proof'):
        backend.restore_current()
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['operation'] == 'terminal.kill'
    assert 'rebound' in saved['pending']
    backend._binding_receipt(saved['plan'], saved, 'testtx', 2)
    assert core.document is not None
    assert core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] == 't2'
    before = len(core.calls)
    with pytest.raises(native.NativeError, match='^core repair guard exit unproven$'):
        backend.restore_current()
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls[before:])


@pytest.mark.parametrize('conflict', ['present', 'live', 'finished', 'duplicate', 'external', 'conflicting-finished'])
def test_r3_closed_pending_run_negative_retains_intent(backend, conflict):
    core, receipt = mixed_legacy(backend, 6, 4)
    repair = receipt['repairs']['app-leaf-2']
    if conflict == 'present':
        tab = copy.deepcopy(receipt['document']['spaces'][0]['tabs'][2])
        core.document['spaces'][0]['tabs'].append(tab)
        core.version += 1
    elif conflict == 'external':
        synthetic_process(backend, 998, wrapper_argv(backend, repair['pane']['session_id']))
    else:
        for i in range(2 if conflict == 'duplicate' else 1):
            result = core.rpc('terminal.run', {'argv': [str(backend.home / '.local/bin/opencode'), '--session',
                                  repair['pane']['session_id']], 'cwd': '/work', 'labels': repair['labels']})
            if conflict.endswith('finished'):
                FakeCore.rpc(core, 'terminal.kill', {'terminal': result['address']})
            if conflict == 'conflicting-finished':
                core.terminals[result['address']]['labels']['remote-herdr-owner'] = 'conflicting'
    core.calls.clear()
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert backend.store.read('receipt-testtx.json')['pending'] == receipt['pending']
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls)


def test_complete_journal_recover_entry_point_reaches_native_repair(backend):
    core, receipt = mixed_legacy(backend, 6, 4)
    runtime_controller.Controller(backend.store, backend).recover()
    assert backend.store.read('manifest.json')['receipt']['pending'] is None
    assert backend.store.read('manifest.json')['receipt']['repairs'] == {}
    assert backend.store.read('receipt-testtx.json')['repairs'] == {}


def test_r3_three_repairs_same_canonical_leaf_keep_finished_history(backend):
    core = AppCore(backend)
    manifest_for(backend, core)
    labels = []
    for cycle in range(3):
        old = f't{cycle + 1}'
        synthetic_process(backend, core.terminals[old]['pid'], ['/bin/bash', '-l'])
        core.calls.clear()
        backend.restore_current()
        effects = [m for m, _ in core.calls if m in ('terminal.run', 'doc.set', 'terminal.kill')]
        assert effects == ['terminal.run', 'doc.set', 'terminal.kill']
        replacement = core.terminals[f't{cycle + 2}']
        labels.append(replacement['labels'])
        assert replacement['state'] == 'live'
        assert len(backend.scan({'ses_abc'})) == 1
        assert all(core.terminals[f't{i + 1}']['state'] == 'finished' for i in range(cycle + 1))
        assert core.document is not None
        assert core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] == replacement['address']
    assert len({label['remote-herdr-repair'] for label in labels}) == 3


@pytest.mark.parametrize('change', ['display', 'live', 'finished', 'version', 'external'])
def test_r3_closed_run_rechecks_relevant_absence_not_terminal_presentation(backend, change):
    core, receipt = mixed_legacy(backend, 6, 4)
    inventory = backend._terminals
    polls = 0
    def observe():
        nonlocal polls
        polls += 1
        if polls == 2:
            unrelated = core.terminals['t6']
            unrelated.update(title='changed', status={'async': True}, records=[{'turn': 1}])
            unrelated['labels'].update({'where': 'changed', 'herdr.seen': 'later'})
            if change in ('live', 'finished'):
                repair = receipt['repairs']['app-leaf-2']
                terminal = copy.deepcopy(unrelated)
                terminal.update(address='appeared', labels=repair['labels'], state=change)
                core.terminals['appeared'] = terminal
            elif change == 'version':
                core.version += 1
            elif change == 'external':
                session = receipt['repairs']['app-leaf-2']['pane']['session_id']
                synthetic_process(backend, 998, wrapper_argv(backend, session))
        return inventory()
    backend._terminals = observe
    if change == 'display':
        backend._reconcile_current_intent(copy.deepcopy(receipt))
        backend.restore_current()
        assert backend.store.read('manifest.json')['receipt']['pending'] is None
    else:
        with pytest.raises(native.NativeError):
            backend._reconcile_current_intent(copy.deepcopy(receipt))
        assert backend.store.read('receipt-testtx.json')['pending'] == receipt['pending']
        assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls)


@pytest.mark.parametrize('boundary', ['doc.set', 'terminal.kill'])
@pytest.mark.parametrize('change', [
    'old-labels', 'old-pid', 'old-start', 'old-argv', 'old-cwd', 'old-launch',
    'new-labels', 'new-pid', 'new-start', 'new-argv', 'new-cwd',
    'version', 'foreign-reference', 'duplicate-live', 'duplicate-finished',
])
def test_r3_security_drift_never_kills_original_or_replacement(backend, boundary, change):
    core = AppCore(backend)
    manifest_for(backend, core)
    assert core.document is not None
    core.document['spaces'][0]['tabs'][0]['root']['id'] = 'app-leaf'
    core.version += 1
    backend.restore_current()
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    core.calls.clear()
    publish = backend._receipt
    mutated = False
    def persist(receipt):
        nonlocal mutated
        publish(receipt)
        if mutated or (receipt.get('pending') or {}).get('operation') != boundary:
            return
        mutated = True
        target = core.terminals['t1' if change.startswith('old-') else 't2']
        if change.endswith('labels'):
            target['labels']['remote-herdr-extra'] = 'PRIVATE_VALUE'
        elif change.endswith('-pid'):
            target['pid'] = 998
        elif change.endswith('-start'):
            argv = ['/bin/bash', '-l'] if change.startswith('old-') else wrapper_argv(backend)
            synthetic_process(backend, target['pid'], argv, ticks=999)
        elif change.endswith('-argv'):
            synthetic_process(backend, target['pid'], ['/PRIVATE_FOREIGN'])
        elif change.endswith('-cwd'):
            argv = ['/bin/bash', '-l'] if change.startswith('old-') else wrapper_argv(backend)
            synthetic_process(backend, target['pid'], argv, cwd='/PRIVATE_DIRECTORY')
        elif change == 'old-launch':
            target['argv'] = ['/PRIVATE_LAUNCH']
        elif change == 'version':
            core.version += 1
        elif change == 'foreign-reference':
            assert core.document is not None
            core.document['spaces'][0]['tabs'][0]['root']['content']['terminal'] = 'foreign'
            core.version += 1
        else:
            terminal = copy.deepcopy(core.terminals['t2'])
            terminal['address'] = 'duplicate'
            if change.endswith('finished'):
                terminal['state'] = 'finished'
            core.terminals['duplicate'] = terminal
    backend._receipt = persist
    with pytest.raises(native.NativeError) as error:
        backend.restore_current()
    assert 'PRIVATE' not in str(error.value)
    assert mutated
    effects = [m for m, _ in core.calls if m in ('terminal.run', 'doc.set', 'terminal.kill')]
    assert effects == (['terminal.run'] if boundary == 'doc.set' else ['terminal.run', 'doc.set'])
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['operation'] == boundary
    backend._binding_receipt(saved['plan'], saved, 'testtx', 2)
    backend._receipt = publish
    before = len(core.calls)
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls[before:])


@pytest.mark.parametrize('phase,malformed', [
    ('doc.set', 'extra'), ('doc.set', 'replacement-extra'), ('doc.set', 'replacement-pid'),
    ('doc.set', 'bool-version'), ('doc.set', 'source-extra'), ('doc.set', 'source-oversized'),
    ('doc.set', 'missing-source'), ('terminal.kill', 'extra'), ('terminal.kill', 'rebound-extra'),
    ('terminal.kill', 'replacement-extra'), ('terminal.kill', 'replacement-pid'),
    ('terminal.kill', 'bool-version'),
    ('doc.set', 'create-id-null'), ('doc.set', 'create-id-bool'), ('doc.set', 'create-id-uppercase'),
    ('doc.set', 'create-id-oversized'), ('doc.set', 'create-label-missing'), ('doc.set', 'create-label-mismatch'),
])
def test_r3_extended_private_forms_are_exact_and_bounded(backend, phase, malformed):
    core = AppCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    write = backend.store.write
    def interrupt(name, value):
        write(name, value)
        if name == 'receipt-testtx.json' and (value.get('pending') or {}).get('operation') == phase:
            raise native.NativeError('synthetic interruption')
    backend.store.write = interrupt
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.store.write = write
    saved = backend.store.read('receipt-testtx.json')
    pending = saved['pending']
    repair = saved['repairs']['s0-t0-p0']
    details = pending if phase == 'doc.set' else pending['rebound']
    if malformed == 'extra':
        pending['extra'] = True
    elif malformed == 'rebound-extra':
        details['extra'] = True
    elif malformed == 'replacement-extra':
        details['replacement']['extra'] = True
    elif malformed == 'replacement-pid':
        details['replacement']['pids'][0]['pid'] = True
    elif malformed == 'bool-version':
        details['version'] = True
    elif malformed == 'source-extra':
        repair['source']['extra'] = True
    elif malformed == 'source-oversized':
        repair['source']['argv'] = ['/bin/bash'] + ['x'] * 256
    elif malformed.startswith('create-id-'):
        repair['create_id'] = {'null': None, 'bool': True, 'uppercase': 'A' * 32,
                               'oversized': 'a' * 33}[malformed.removeprefix('create-id-')]
    elif malformed == 'create-label-missing':
        del repair['labels']['remote-herdr-repair']
    elif malformed == 'create-label-mismatch':
        repair['labels']['remote-herdr-repair'] = '0' * 32
    else:
        del repair['source']
    write('receipt-testtx.json', saved)
    core.calls.clear()
    with pytest.raises(native.NativeError):
        backend.restore_current()
    assert backend.store.read('receipt-testtx.json') == saved
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill', 'command') for m, _ in core.calls)


@pytest.mark.parametrize('candidate', ['finished-history', 'finished-current', 'live-foreign', 'finished-current-conflict'])
def test_r3_generation_admission_distinguishes_history_from_current_effect(backend, candidate):
    core = AppCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    core.calls.clear()
    publish = backend._receipt
    injected = False
    def persist(receipt):
        nonlocal injected
        publish(receipt)
        pending = receipt.get('pending') or {}
        if injected or pending.get('operation') != 'terminal.run':
            return
        injected = True
        labels = copy.deepcopy(pending['labels'])
        if candidate in ('finished-history', 'live-foreign'):
            labels['remote-herdr-repair'] = '0' * 32 if labels['remote-herdr-repair'] != '0' * 32 else '1' * 32
        elif candidate == 'finished-current-conflict':
            labels['remote-herdr-owner'] = 'conflicting-owner'
        terminal = copy.deepcopy(core.terminals['t1'])
        terminal.update(address='historical', pid=998, labels=labels,
                        state='live' if candidate == 'live-foreign' else 'finished')
        core.terminals['historical'] = terminal
        if candidate == 'live-foreign':
            synthetic_process(backend, 998, wrapper_argv(backend))
    backend._receipt = persist
    if candidate == 'finished-history':
        backend.restore_current()
        assert len(backend.scan({'ses_abc'})) == 1
        assert [m for m, _ in core.calls if m in ('terminal.run', 'doc.set', 'terminal.kill')] == [
            'terminal.run', 'doc.set', 'terminal.kill']
    else:
        with pytest.raises(native.NativeError):
            backend.restore_current()
        assert backend.store.read('receipt-testtx.json')['pending']['operation'] == 'terminal.run'
        assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls)


@pytest.mark.parametrize('candidate', ['none', 'finished-history', 'finished-current', 'live-current',
                                        'duplicate-current', 'finished-current-conflict'])
def test_r3_gone_new_generation_run_preserves_current_generation_uncertainty(backend, candidate):
    core = AppCore(backend)
    manifest_for(backend, core)
    synthetic_process(backend, core.terminals['t1']['pid'], ['/bin/bash', '-l'])
    def before_run(method, params):
        if method == 'terminal.run':
            raise native.NativeError('synthetic interruption')
        return core.rpc(method, params)
    backend.core = before_run
    with pytest.raises(native.NativeError):
        backend.restore_current()
    backend.core = core.rpc
    saved = backend.store.read('receipt-testtx.json')
    assert saved['pending']['labels']['remote-herdr-repair'] == saved['repairs']['s0-t0-p0']['create_id']
    assert core.document is not None
    core.document['spaces'][0]['tabs'].clear()
    core.version += 1
    if candidate != 'none':
        for i in range(2 if candidate == 'duplicate-current' else 1):
            labels = copy.deepcopy(saved['pending']['labels'])
            if candidate == 'finished-history':
                labels.pop('remote-herdr-repair')
            elif candidate == 'finished-current-conflict':
                labels['remote-herdr-owner'] = 'changed'
            terminal = copy.deepcopy(core.terminals['t1'])
            terminal.update(address=f'candidate{i}', labels=labels, pid=998 + i,
                            state='live' if candidate == 'live-current' else 'finished')
            core.terminals[terminal['address']] = terminal
            if terminal['state'] == 'live':
                synthetic_process(backend, terminal['pid'], wrapper_argv(backend))
    core.calls.clear()
    if candidate in ('none', 'finished-history'):
        backend.restore_current()
        final = backend.store.read('manifest.json')['receipt']
        assert final['pending'] is None and final['repairs'] == {} and final['bindings'] == {}
        assert core.terminals['t1']['state'] == 'live'
    else:
        with pytest.raises(native.NativeError):
            backend.restore_current()
        assert backend.store.read('receipt-testtx.json')['pending'] == saved['pending']
    assert not any(m in ('terminal.run', 'doc.set', 'terminal.kill') for m, _ in core.calls)
