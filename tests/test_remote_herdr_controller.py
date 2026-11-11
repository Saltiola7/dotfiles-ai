"""Transaction ordering and private state; no real Herdr or user manager."""
import importlib.util
import json
from pathlib import Path
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
    def endpoint_present(self, target):
        return False

    def _optional_snapshot(self):
        import layout
        return layout.to_tui_snapshot(plan())

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

    def recover_tui(self, value, txid, receipt, *, preserve_snapshot=False):
        assert preserve_snapshot is True
        self.step('recover_boot')
        return {**receipt, 'pending': None}


def test_tui_boot_checks_absence_and_holds_lock_through_readiness(tmp_path):
    c = module()
    with c.Store(tmp_path / 'state') as store:
        backend = BootBackend(store)
        c.Controller(store, backend).restore()
        assert backend.events == ['absence', 'unit_start', 'ready']
        assert store.read('boot.json')['status'] == 'complete'


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
