"""Transaction ordering and private state; no real Herdr or user manager."""
import importlib.util
import json
from pathlib import Path
import struct
import sys

import pytest

SOURCE = Path(__file__).parents[1] / 'dot_local/share/dotfiles-ai/remote-herdr'
sys.path.insert(0, str(SOURCE))


def module():
    spec = importlib.util.spec_from_file_location('remote_herdr_controller', SOURCE / 'controller.py')
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def plan():
    return {'schema_version': 1, 'spaces': [{'name': 'Space', 'directory': '/work', 'tabs': [
        {'name': 'Tab', 'root': {'pane': 's0-t0-p0'}, 'panes': [
            {'key': 's0-t0-p0', 'cwd': '/work', 'session_id': 'ses_abc'}]}]}]}


class Backend:
    def __init__(self, store):
        self.store = store
        self.events = []
        self.choice = 'tui'
        self.failure = None

    def selected(self):
        return self.choice

    def endpoint_present(self, target):
        return True

    def step(self, name):
        self.events.append(name)
        if self.failure == name:
            raise ValueError('private native output')

    def preflight(self, target, replace_target=False):
        self.step('preflight')

    def capture(self, source):
        self.step('capture')
        return {'runtime': source, 'plan': plan(), 'clients': [], 'pids': []}

    def stop(self, source, captured):
        self.step('stop')
        return captured['plan']

    def prepare(self, target, value, txid, replace_target=False):
        self.step('prepare')
        receipt = {'txid': txid, 'runtime': target, 'pending': None}
        self.store.write('receipt-' + txid + '.json', receipt)
        return receipt

    def recover_prepared(self, target, value, txid, replace_target=False):
        self.step('recover_prepared')
        return {'txid': txid, 'runtime': target, 'pending': None}

    def select(self, target):
        self.step('select')
        self.choice = target

    def restore(self, target, value, txid, receipt):
        self.step('restore')
        return receipt

    def verify(self, target, value, receipt):
        self.step('verify')

    def restore_current(self):
        self.step('restore_current')


def test_store_private_atomic_and_no_unsafe_names(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        store.write('manifest.json', {'private': 'fixture'})
        assert store.read('manifest.json') == {'private': 'fixture'}
        assert (store.root.stat().st_mode & 0o777) == 0o700
        assert ((store.root / 'manifest.json').stat().st_mode & 0o777) == 0o600
        for name in ['../escape', '/escape', 'x/y.json', '.hidden', 'invalid']:
            with pytest.raises(c.ControllerError):
                store.write(name, {})


@pytest.mark.parametrize('selected', ['herdr-core', 'tui'])
def test_complete_journal_recover_only_dispatches_selected_core(tmp_path, selected):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        journal = {'schema_version': 1, 'phase': 'complete', 'history': {'retained': ['private']}}
        store.write('transaction.json', journal)
        before = (store.root / 'transaction.json').read_bytes()
        backend = Backend(store)
        backend.choice = selected
        if selected == 'tui':
            # No owned TUI manifest: a historical completed switch says nothing
            # about whether the selected TUI was in fact restored.
            with pytest.raises(c.ControllerError):
                c.Controller(store, backend).recover()
        else:
            c.Controller(store, backend).recover()
        assert backend.events == (['restore_current'] if selected == 'herdr-core' else [])
        assert (store.root / 'transaction.json').read_bytes() == before
        assert store.read('transaction.json') == journal


def test_store_refuses_links_duplicates_and_second_owner(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        with pytest.raises(c.ControllerError):
            with c.Store(store.root):
                pass
        target = tmp_path / 'outside'
        target.write_text('{}')
        (store.root / 'manifest.json').symlink_to(target)
        with pytest.raises(c.ControllerError):
            store.write('manifest.json', {})
        with pytest.raises(c.ControllerError):
            store.read('manifest.json')
        (store.root / 'duplicate.json').write_text('{"x":1,"x":2}')
        (store.root / 'duplicate.json').chmod(0o600)
        with pytest.raises(c.ControllerError):
            store.read('duplicate.json')


@pytest.mark.parametrize('outcome', ['release', 'timeout', 'other', 'unknown', 'handoff'])
def test_k_manual_recover_waits_only_for_proven_holder(tmp_path, outcome):
    c = module()
    owner = c.Store(tmp_path / 'state')
    clock, reports, probes = [0.0], [], []
    with owner:
        owner.write('transaction.json', {'private': 'retained'})
        original = (owner.root / 'transaction.json').read_bytes()
        info = (owner.root / 'owner.lock').stat()
        waiter = c.Store(owner.root)
        def background(identity, timeout):
            probes.append(identity)
            assert identity == (info.st_dev, info.st_ino)
            assert 0 < timeout <= 3 - clock[0]
            with pytest.raises(c.ControllerError):
                waiter.read('transaction.json')
            if outcome == 'unknown': raise OSError()
            return outcome != 'other' and not (outcome == 'handoff' and clock[0] > 0)
        def sleep(seconds):
            clock[0] += seconds
            if outcome == 'release':
                owner.__exit__(None, None, None)
        held = c.recovery_owner(waiter, background, reports.append, limit=3, clock=lambda: clock[0], sleep=sleep)
        if outcome == 'release':
            with held as store:
                assert store.read('transaction.json') == {'private': 'retained'}
                with pytest.raises(c.ControllerBusy):
                    with c.Store(owner.root):
                        pytest.fail()
        else:
            label = 'wait limit' if outcome == 'timeout' else 'not proven'
            with pytest.raises(c.RecoveryContention, match=label):
                with held:
                    pytest.fail()
        assert clock[0] == {'release': 1, 'timeout': 3, 'other': 0, 'unknown': 0, 'handoff': 1}[outcome]
        assert len(reports) == int(outcome not in ('other', 'unknown'))
        if reports:
            assert reports == ['Herdr recover: waiting for the background restore to release the runtime state']
        assert waiter.fd is None and probes
        assert (owner.root / 'transaction.json').read_bytes() == original


def test_k_unsafe_lock_is_not_recover_contention(tmp_path):
    c = module()
    root = tmp_path / 'state'
    root.mkdir(mode=0o700)
    (root / 'owner.lock').symlink_to(tmp_path / 'missing')
    with pytest.raises(c.ControllerError) as caught:
        with c.recovery_owner(c.Store(root), lambda *a, **kw: pytest.fail(), lambda *a: pytest.fail()):
            pytest.fail()
    assert not isinstance(caught.value, (c.ControllerBusy, c.RecoveryContention))


def test_k_wait_at_deadline_does_not_enter_even_when_holder_just_finished(tmp_path):
    c = module()
    owner = c.Store(tmp_path / 'state')
    ticks = [0.]
    with owner:
        def sleep(seconds):
            ticks[0] += seconds
            owner.__exit__(None, None, None)
        with pytest.raises(c.RecoveryContention, match='wait limit'):
            with c.recovery_owner(c.Store(owner.root), lambda *a, **kw: True, lambda _: None,
                                  limit=1, clock=lambda: ticks[0], sleep=sleep):
                pytest.fail()


def test_switch_orders_source_stop_before_target_mutations(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = Backend(store)
        c.Controller(store, backend).switch('herdr-core', replace_target=True)
        assert backend.events == ['preflight', 'capture', 'stop', 'prepare', 'select', 'restore', 'verify']
        manifest = store.read('manifest.json')
        assert manifest['runtime'] == 'herdr-core' and manifest['plan'] == plan()
        assert store.read('transaction.json')['phase'] == 'complete'


@pytest.mark.parametrize('failure', ['stop', 'prepare', 'select', 'restore', 'verify'])
def test_failed_switch_is_durable_and_cannot_be_replayed(tmp_path, failure):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = Backend(store)
        backend.failure = failure
        controller = c.Controller(store, backend)
        with pytest.raises(c.ControllerError) as captured:
            controller.switch('herdr-core')
        assert 'private native output' not in str(captured.value)
        assert store.read('transaction.json')['phase'] == failure + '_pending'
        events = list(backend.events)
        with pytest.raises(c.ControllerError):
            controller.switch('herdr-core')
        assert backend.events == events


def test_completed_history_retained_before_next_switch(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = Backend(store)
        controller = c.Controller(store, backend)
        controller.switch('herdr-core')
        first = store.read('transaction.json')
        controller.switch('tui')
        assert store.read('history-' + first['txid'] + '.json') == first


def test_import_requires_source_off_and_clients_absent(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = Backend(store)
        with pytest.raises(c.ControllerError):
            c.Controller(store, backend).switch('herdr-core', imported=plan())
        assert 'prepare' not in backend.events


def test_recovery_reconciles_prepare_without_replaying_it(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = Backend(store)
        backend.failure = 'prepare'
        controller = c.Controller(store, backend)
        with pytest.raises(c.ControllerError):
            controller.switch('herdr-core')
        backend.failure = None
        controller.recover()
        assert backend.events.count('prepare') == 1
        assert backend.events[-4:] == ['recover_prepared', 'select', 'restore', 'verify']
        assert store.read('transaction.json')['phase'] == 'complete'


def test_pending_switch_blocks_automatic_restore(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = Backend(store)
        backend.failure = 'stop'
        controller = c.Controller(store, backend)
        with pytest.raises(c.ControllerError):
            controller.switch('herdr-core')
        with pytest.raises(c.ControllerError, match='blocks automatic'):
            controller.restore()


def test_recovery_keeps_current_same_transaction_manifest_and_propagates_plan(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        current_plan = plan()
        current_plan['spaces'][0]['name'] = 'User renamed'
        receipt = {'runtime': 'herdr-core', 'txid': 'synthetic', 'pending': None, 'current_document': True}
        manifest = {'schema_version': 2, 'runtime': 'herdr-core', 'txid': 'synthetic',
                    'plan': current_plan, 'receipt': receipt}
        store.write('manifest.json', manifest)
        store.write('transaction.json', {'schema_version': 1, 'txid': 'synthetic', 'source': 'tui',
                    'target': 'herdr-core', 'phase': 'restore_pending', 'plan': plan(), 'receipt': receipt})
        class CurrentBackend(Backend):
            def restore_current(self):
                assert store.read('manifest.json') == manifest
            def verify(self, target, value, receipt):
                assert value == current_plan and receipt == manifest['receipt']
        backend = CurrentBackend(store)
        backend.choice = 'herdr-core'
        c.Controller(store, backend).recover()
        assert store.read('manifest.json') == manifest
        journal = store.read('transaction.json')
        assert journal['phase'] == 'complete' and journal['plan'] == current_plan


def test_store_large_state_refuses_without_replacing_prior_bytes(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        store.write('manifest.json', {'old': True})
        with pytest.raises(c.ControllerError):
            store.write('manifest.json', {'value': 'x' * (2 * 1024 * 1024)})
        assert store.read('manifest.json') == {'old': True}


class BootBackend(Backend):
    def __init__(self, store):
        super().__init__(store)
        self.active = False

    def endpoint_present(self, target):
        return target == 'tui' and self.active

    def _optional_snapshot(self):
        import layout
        return layout.to_tui_snapshot(plan())

    def tui_unit_stopped(self):
        return True

    def _db_sessions(self, value):
        assert value['spaces'][0]['tabs'][0]['panes'][0]['session_id'] == 'ses_abc'

    def snapshot_evidence(self):
        import hashlib
        snapshot = self._optional_snapshot()
        return snapshot, {'digest': hashlib.sha256(json.dumps(snapshot).encode()).hexdigest(), 'mtime_ns': 10}

    def tui_owner_view(self, value, prior):
        import layout
        return ({'view': [], 'pids': [], 'run': {'pid': 20, 'start_ticks': 11}, 'clients': {},
                 'file': self.snapshot_evidence()[1]}, self._optional_snapshot(),
                layout.from_tui_snapshot(self._optional_snapshot()))

    def _semantic(self, value, native_ratios=False):
        return value

    def absent(self, sessions, captured):
        self.step('absence')

    def command(self, argv):
        self.step('unit_start')

    def _wait_ready(self, target, value, receipt):
        assert self.store.read('boot.json')['status'] == 'start_pending'
        # The ownership lock remains held until native readiness, not just exec.
        c = module()
        with pytest.raises(c.ControllerError):
            with c.Store(self.store.root):
                pass
        self.step('ready')
        self.active = True

    def recover_tui(self, value, txid, receipt, *, preserve_snapshot=False):
        assert preserve_snapshot is True
        self.step('recover_boot')
        self.active = True
        return {**receipt, 'pending': None}


def test_tui_boot_checks_absence_and_holds_lock_through_readiness(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = BootBackend(store)
        c.Controller(store, backend).restore()
        assert backend.events == ['absence', 'absence', 'unit_start', 'ready']
        assert store.read('boot.json')['status'] == 'complete'
        assert store.read('boot.json')['receipt']['ready_run']['run'] == store.read('tui-observation.json')['run']


def test_tui_missing_socket_with_surviving_client_never_starts(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = BootBackend(store)
        backend.failure = 'absence'
        with pytest.raises(ValueError):
            c.Controller(store, backend).restore()
        assert backend.events == ['absence']
        assert store.read('boot.json') is None


def test_uncertain_boot_blocks_switch_even_without_source_endpoint(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = BootBackend(store)
        backend.failure = 'ready'
        controller = c.Controller(store, backend)
        with pytest.raises(ValueError):
            controller.restore()
        assert store.read('boot.json')['status'] == 'start_pending'
        with pytest.raises(c.ControllerError, match='boot startup'):
            controller.switch('herdr-core', imported=plan())
        assert 'preflight' not in backend.events


def test_boot_recovery_explicitly_preserves_native_snapshot(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = BootBackend(store)
        backend.failure = 'ready'
        controller = c.Controller(store, backend)
        with pytest.raises(ValueError):
            controller.restore()
        backend.failure = None
        controller.recover()
        assert backend.events[-1] == 'recover_boot'
        assert store.read('boot.json')['status'] == 'complete'


def split_at(planned):
    value = plan()
    tab = value['spaces'][0]['tabs'][0]
    tab['panes'].append({'key': 's0-t0-p1', 'cwd': '/work', 'session_id': None})
    tab['root'] = {'axis': 'row', 'ratio': planned,
                   'children': [{'pane': 's0-t0-p0'}, {'pane': 's0-t0-p1'}]}
    return value


def native_save(value, reported):
    """The saved session.json as the pinned TUI writes it (RRW-007G-R11).

    The native writer prints a 32-bit ratio as its shortest decimal, here
    0.5869565 for a plan ratio of 0.58695651. The two round to different
    6-decimal values.
    """
    import copy
    import layout
    saved = copy.deepcopy(layout.to_tui_snapshot(value))
    saved['workspaces'][0]['tabs'][0]['layout']['Split']['ratio'] = reported
    return saved


class NativeRatioBootBackend(BootBackend):
    """Boot backend with the real saved-snapshot reader and the real comparison."""

    def __init__(self, store, home, owned, reported):
        super().__init__(store)
        import native
        self.saved = native_save(owned, reported)
        self.adapter = native.Native(home, store)
        self.active = False

    def endpoint_present(self, target):
        return target == 'tui' and self.active

    def command(self, argv):
        super().command(argv)
        self.active = True

    def final_tui_file(self, run, file):
        return False

    def _optional_snapshot(self):
        return self.saved

    def _semantic(self, value, native_ratios=False):
        return self.adapter._semantic(value, native_ratios=native_ratios)


def native_ratio_boot_backend(store, owned, reported):
    return NativeRatioBootBackend(store, store.root.parent, owned, reported)


def owned_tui(store, plan_value):
    receipt = {'runtime': 'tui', 'txid': 'owned', 'pending': None}
    store.write('manifest.json', {'schema_version': 1, 'runtime': 'tui', 'txid': 'owned',
                                  'plan': plan_value, 'receipt': receipt})


def test_r11_tui_boot_accepts_the_native_form_of_an_owned_full_precision_ratio(tmp_path):
    c = module()
    owned = split_at(0.58695651)
    with c.Store(tmp_path / 'state') as store:
        owned_tui(store, owned)
        backend = native_ratio_boot_backend(store, owned, 0.5869565)
        c.Controller(store, backend).restore()
        assert backend.events == ['absence', 'absence', 'unit_start', 'ready']
        boot = store.read('boot.json')
        assert boot['status'] == 'complete'
        assert boot['plan']['spaces'][0]['tabs'][0]['root']['ratio'] == 0.5869565
        # A real edit of the saved ratio still refuses the boot and never starts the unit.
        backend = native_ratio_boot_backend(store, owned, 0.45)
        with pytest.raises(c.ControllerError, match='shutdown save does not match'):
            c.Controller(store, backend).restore()
        assert backend.events == []


def test_r11_tui_boot_refuses_a_ratio_that_differs_in_the_native_float(tmp_path):
    c = module()
    owned = split_at(0.58695651)
    # The adjacent lower 32-bit float rounds to the same 6 decimals.
    order = struct.unpack('I', struct.pack('f', 0.5869565))[0]
    reported = struct.unpack('f', struct.pack('I', order - 1))[0]
    assert reported != 0.5869565 and round(reported, 6) == round(0.5869565, 6)
    with c.Store(tmp_path / 'state') as store:
        owned_tui(store, owned)
        backend = native_ratio_boot_backend(store, owned, reported)
        with pytest.raises(c.ControllerError, match='differs from owned layout'):
            c.Controller(store, backend).restore()
        assert backend.events == [] and store.read('boot.json') is None
