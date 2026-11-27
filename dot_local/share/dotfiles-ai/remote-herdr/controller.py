"""Serialized, private switch journal. Unknown mutations are never replayed."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

import layout
import protocol


class ControllerError(ValueError):
    """Fixed-label diagnostics only; journals contain the private detail."""


class ControllerBusy(ControllerError):
    def __init__(self, info):
        super().__init__('runtime state already owned')
        self.identity = info.st_dev, info.st_ino


class RecoveryContention(ControllerError):
    """Only the two fixed recover contention diagnostics are public."""


class TuiNotRestored(ControllerError):
    """A complete historical intent does not establish current readiness."""


class Store:
    """Single-user private JSON store held under one nonblocking advisory lock."""
    def __init__(self, root: Path):
        self.root = Path(root)
        self.fd = None

    def __enter__(self):
        try:
            if not self.root.is_absolute() or '..' in self.root.parts:
                raise ControllerError('runtime state path unsafe')
            for path in reversed((self.root, *self.root.parents)):
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    path.mkdir(mode=0o700)
                    info = path.lstat()
                if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, os.getuid()}
                        or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                    raise ControllerError('runtime state parent unsafe')
            info = self.root.lstat()
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ControllerError('runtime state directory must be private')
            self.fd = os.open(self.root / 'owner.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            info = os.fstat(self.fd)
            self._safe(info)
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ControllerBusy(info) from None
            return self
        except ControllerBusy:
            self.__exit__(None, None, None)
            raise
        except (OSError, ValueError):
            self.__exit__(None, None, None)
            raise ControllerError('runtime state unavailable or already owned') from None

    def __exit__(self, *args):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def _safe(self, info):
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size > protocol.MAX_MESSAGE):
            raise ControllerError('runtime state file unsafe')

    def _path(self, name):
        if self.fd is None or not isinstance(name, str) or not re.fullmatch(r'[a-z][A-Za-z0-9_-]{0,180}\.json', name):
            raise ControllerError('runtime state name or ownership invalid')
        return self.root / name

    def read(self, name):
        path = self._path(name)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return None
        except OSError:
            raise ControllerError('runtime state file unsafe') from None
        try:
            self._safe(os.fstat(fd))
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                return protocol.decode(stream.read(protocol.MAX_MESSAGE + 1))
        except (OSError, ValueError):
            raise ControllerError('runtime state invalid') from None
        finally:
            os.close(fd)

    def write(self, name, value):
        path = self._path(name)
        self.read(name)  # Existing unsafe entries are not overwritten.
        try:
            data = json.dumps(value, allow_nan=False).encode()
            protocol.decode(data)
        except (ValueError, TypeError, RecursionError):
            raise ControllerError('runtime state invalid or oversized') from None
        temporary = self.root / ('.write-' + uuid.uuid4().hex)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            raise ControllerError('runtime state publication uncertain') from None
        finally:
            temporary.unlink(missing_ok=True)


@contextmanager
def recovery_owner(store, background, report, *, limit=150, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + limit
    reported = False
    while True:
        if clock() >= deadline:
            raise RecoveryContention('Herdr recover did not run: state lock wait limit reached')
        try:
            store.__enter__()
            break
        except ControllerBusy as busy:
            remaining = deadline - clock()
            if remaining <= 0:
                raise RecoveryContention('Herdr recover did not run: state lock wait limit reached') from None
            try:
                proven = background(busy.identity, timeout=min(remaining, 3.0))
            except (ValueError, OSError):
                proven = False
            if clock() >= deadline:
                raise RecoveryContention('Herdr recover did not run: state lock wait limit reached') from None
            if not proven:
                # The owner might have finished between flock and observation.
                try:
                    store.__enter__()
                    break
                except ControllerBusy:
                    raise RecoveryContention(
                        'Herdr recover did not run: state held; background restore ownership not proven') from None
            if not reported:
                report('Herdr recover: waiting for the background restore to release the runtime state')
                reported = True
            sleep(max(0, min(1, deadline - clock())))
    try:
        yield store
    finally:
        store.__exit__(None, None, None)


class Controller:
    def __init__(self, store, backend):
        self.store = store
        self.backend = backend

    def _journal(self, journal, phase):
        journal['phase'] = phase
        self.store.write('transaction.json', journal)

    def _clear(self):
        boot = self.store.read('boot.json')
        if boot and boot.get('status') == 'start_pending':
            raise ControllerError('unfinished boot startup requires explicit recovery')
        prior = self.store.read('transaction.json')
        if prior:
            if prior.get('phase') != 'complete':
                raise ControllerError('unfinished switch requires explicit recovery')
            self.store.write('history-' + prior['txid'] + '.json', prior)

    def _manifest(self, journal, receipt):
        return {'schema_version': 2 if receipt.get('current_document') is True else 1,
                'runtime': journal['target'], 'plan': journal['plan'],
                'receipt': receipt, 'txid': journal['txid']}

    def _finish(self, journal, receipt):
        self._journal(journal, 'verify_pending')
        self.backend.verify(journal['target'], journal['plan'], receipt)
        self.store.write('manifest.json', self._manifest(journal, receipt))
        self._journal(journal, 'complete')

    def _activate(self, journal):
        self._journal(journal, 'select_pending')
        self.backend.select(journal['target'])
        self._journal(journal, 'restore_pending')
        receipt = self.backend.restore(journal['target'], journal['plan'], journal['txid'], journal['receipt'])
        journal['receipt'] = receipt
        self._finish(journal, receipt)

    def switch(self, target, replace_target=False, imported=None):
        try:
            if target not in {'tui', 'herdr-core'}:
                raise ControllerError('runtime selection invalid')
            self._clear()
            source = self.backend.selected()
            if source == target and imported is None:
                raise ControllerError('runtime already selected; use restore')
            self.backend.preflight(target, replace_target=replace_target)
            if imported is None:
                capture = self.backend.capture(source)
                plan = layout.validate_plan(capture['plan'])
            else:
                plan = layout.validate_plan(imported)
                # File import is not permission to abandon source clients.
                if self.backend.endpoint_present(source):
                    raise ControllerError('file import requires source runtime stopped')
                self.backend.absent({p['session_id'] for s in plan['spaces'] for t in s['tabs']
                                     for p in t['panes'] if p['session_id']}, [])
                capture = None
            journal = {'schema_version': 1, 'txid': uuid.uuid4().hex, 'source': source,
                       'target': target, 'replace_target': bool(replace_target),
                       'capture': capture, 'plan': plan, 'receipt': None}
            if capture is not None:
                self._journal(journal, 'stop_pending')
                journal['plan'] = layout.validate_plan(self.backend.stop(source, capture))
            self._journal(journal, 'prepare_pending')
            receipt = self.backend.prepare(target, journal['plan'], journal['txid'], replace_target=replace_target)
            journal['receipt'] = receipt
            self._journal(journal, 'prepared')
            self._activate(journal)
        except ControllerError:
            raise
        except Exception:
            raise ControllerError('switch incomplete; private journal retained; use recover') from None

    def recover(self):
        """Resume only after observational reconciliation; never repeat stop/run."""
        try:
            journal = self.store.read('transaction.json')
            boot = self.store.read('boot.json')
            if boot and boot.get('status') == 'start_pending':
                if journal and journal.get('phase') != 'complete':
                    raise ControllerError('conflicting retained startup and switch intents')
                receipt = self._recover_tui_edit(boot, boot['receipt'], booting=True)
                boot['receipt'] = self.backend.recover_tui(
                    boot['plan'], receipt['txid'], receipt, preserve_snapshot=True)
                self._complete_boot(boot)
                return
            if (journal is None and boot and boot.get('status') == 'complete'
                    and boot.get('schema_version') == 1 and boot.get('runtime') == 'tui'
                    and self.backend.selected() == 'tui' and not self.backend.endpoint_present('herdr-core')
                    and boot['receipt']['pending'] is None and boot['receipt']['runtime'] == 'tui'):
                self._recovered_tui()
                return
            if not journal or journal.get('schema_version') != 1:
                raise ControllerError('switch journal unavailable')
            phase = journal['phase']
            if phase == 'complete':
                if self.backend.selected() == 'herdr-core':
                    self.backend.restore_current()
                else:
                    self._recovered_tui()
                return
            if phase == 'stop_pending':
                capture = journal['capture']
                journal['plan'] = self.backend.reconcile_stopped(journal['source'], capture)
                # Source absence is established; do not replay its stop mutations.
                self._journal(journal, 'prepare_pending')
                receipt = self.backend.prepare(journal['target'], journal['plan'], journal['txid'],
                                               replace_target=journal['replace_target'])
                journal['receipt'] = receipt
                self._journal(journal, 'prepared')
                self._activate(journal)
                return
            if phase == 'prepare_pending':
                journal['receipt'] = self.backend.recover_prepared(
                    journal['target'], journal['plan'], journal['txid'], journal['replace_target'])
                self._journal(journal, 'prepared')
                self._activate(journal)
                return
            if phase in {'prepared', 'select_pending'}:
                self._activate(journal)
                return
            receipt = self.store.read('receipt-' + journal['txid'] + '.json') or journal['receipt']
            if phase not in {'restore_pending', 'verify_pending'} or receipt is None:
                raise ControllerError('switch recovery phase unsupported')
            if journal['target'] == 'herdr-core':
                if self.backend.selected() != 'herdr-core':
                    raise ControllerError('recovery selection changed')
                # restore_current reconciles each labeled uncertain effect before
                # any new mutation. Retain the previous manifest in the journal.
                journal.setdefault('previous_manifest', self.store.read('manifest.json'))
                self.store.write('transaction.json', journal)
                current = self.store.read('manifest.json')
                if not (current and current.get('schema_version') == 2
                        and current.get('txid') == journal['txid']):
                    self.store.write('manifest.json', self._manifest(journal, receipt))
                self.backend.restore_current()
                current = self.store.read('manifest.json')
                receipt = current['receipt']
                journal['plan'] = current['plan']
            else:
                # An adopted verify intent (and its plan) was published together.
                # Its earlier switch side-receipt can never regenerate an old plan.
                if (journal['receipt'] or {}).get('tui_lineage') is not None:
                    receipt = journal['receipt']
                receipt = self._recover_tui_edit(journal, receipt, booting=False)
                receipt = self.backend.recover_tui(journal['plan'], journal['txid'], receipt,
                                                   preserve_snapshot='tui_lineage' in receipt)
            journal['receipt'] = receipt
            self._finish(journal, receipt)
        except ControllerError:
            raise
        except Exception:
            raise ControllerError('recovery uncertain; private journal retained') from None

    @staticmethod
    def backend_sessions(plan):
        return {p['session_id'] for s in plan['spaces'] for t in s['tabs']
                for p in t['panes'] if p['session_id'] is not None}

    def _same_tui_plan(self, left, right):
        return (self.backend._semantic(left, native_ratios=True)
                == self.backend._semantic(right, native_ratios=True))

    def _recovered_tui(self):
        try:
            manifest = self.store.read('manifest.json')
            if manifest and manifest['runtime'] == 'tui':
                witness = self._tui_observation(manifest)
                if not (witness and witness['hold']) and self.backend.endpoint_present('tui'):
                    proof, disk, live = self.backend.tui_owner_view(manifest['plan'], witness)
                    if (not self._edited(manifest, disk, layout.from_tui_snapshot(disk)) and (
                            layout.tui_save_matches_view(disk, proof['view']) or (
                                all(b is None for b in layout.tui_public_identities(disk))
                                and disk == manifest['receipt']['document']
                                and self._same_tui_plan(live, manifest['plan'])))):
                        return
        except (OSError, ValueError, KeyError, TypeError):
            pass
        raise TuiNotRestored('Herdr recover did not complete: TUI state is held or not restored')

    @staticmethod
    def _lineage(manifest):
        return manifest['receipt'].get('tui_lineage', manifest['txid'])

    def _edited(self, manifest, snapshot, plan):
        previous = manifest['receipt'].get('document')
        if not self._same_tui_plan(plan, manifest['plan']):
            return True
        if previous is None:
            return False
        if layout.tui_names(previous) != layout.tui_names(snapshot):
            return True
        # A persisted public leaf must not silently become a different leaf
        # with identical cwd/session. Legacy generated documents lack IDs.
        bindings = layout.tui_public_identities(previous, stored_precision=True)
        return any(b is not None and b != current
                   for b, current in zip(bindings, layout.tui_public_identities(snapshot, stored_precision=True)))

    def _tui_observation(self, manifest):
        observed = self.store.read('tui-observation.json')
        if observed is not None and observed['lineage'] == self._lineage(manifest):
            return observed
        return None

    def _observe_tui(self, manifest):
        """First inhibit offline launch, then prove *all* panes in one observation.

        An interrupted/failed observation leaves the older manifest, receipt,
        snapshot and last witness intact. Even a byte-identical old save cannot
        launch while this hold is set. A subsequent live proof can clear it.
        """
        lineage = self._lineage(manifest)
        prior = self._tui_observation(manifest) or {'lineage': lineage}
        if not prior.get('hold'):
            self.store.write('tui-observation.json', {**prior, 'hold': True})
        witness, snapshot, live = self.backend.tui_owner_view(manifest['plan'], prior)
        plan = layout.from_tui_snapshot(snapshot)
        matched = layout.tui_save_matches_view(snapshot, witness['view'])
        # A migration writer has only explicit labels and no public identities.
        # It may confirm the exact already-owned document; it cannot prove an
        # edited save. The shutdown writer must join via its public IDs.
        legacy = (not matched and snapshot == manifest['receipt'].get('document')
                  and all(b is None for b in layout.tui_public_identities(snapshot))
                  and self._same_tui_plan(plan, live))
        observation = {'lineage': lineage, 'hold': False, **witness, 'legacy': legacy}
        if matched or legacy:
            observation['names'] = layout.tui_names(snapshot)
        if self.backend.snapshot_evidence()[1] != witness['file']:
            raise ControllerError('TUI snapshot changed during observation')
        self.store.write('tui-observation.json', observation)
        return snapshot, plan, matched or legacy

    def _adoption(self, manifest, receipt, snapshot, *, retained=None):
        backup = {'manifest': manifest}
        if retained is not None:
            backup['retained'] = retained
        return {**receipt, 'document': snapshot, 'adoption_backup': self.backend._backup(backup)}

    def _restore_live_tui(self, manifest):
        snapshot, plan, matched = self._observe_tui(manifest)
        if not matched or not self._edited(manifest, snapshot, plan):
            return
        receipt = self._adoption(manifest, {'runtime': 'tui', 'txid': uuid.uuid4().hex,
            'pending': None, 'tui_lineage': self._lineage(manifest)}, snapshot)
        self.backend._receipt(receipt)
        # Backup and private receipt publication take time. Re-prove the same
        # save and its clients before making a new manifest visible.
        current, _, matched = self._observe_tui(manifest)
        if not matched or current != snapshot:
            raise ControllerError('TUI changed before adoption')
        self.store.write('manifest.json', self._manifest(
            {'target': 'tui', 'plan': plan, 'txid': receipt['txid']}, receipt))

    def _recover_tui_edit(self, entry, receipt, *, booting):
        """Rebase only a known start, never a write/prepare intent. A retained
        boot or switch plan and its adopted receipt advance in a single write.
        """
        txid = receipt['txid'] if booting else entry['txid']
        if receipt.get('txid') != txid or receipt.get('runtime') != 'tui':
            raise ControllerError('TUI recovery identity mismatch')
        pending = receipt.get('pending')
        active = self.backend.endpoint_present('tui')
        if pending not in (None, {'operation': 'tui.start'}):
            if active:
                raise ControllerError('TUI write outcome conflicts with live endpoint')
            return receipt
        baseline = self._manifest({'target': 'tui', 'txid': txid, 'plan': entry['plan']}, receipt)
        witness = self._tui_observation(baseline)
        if active:
            document = receipt.get('document')
            if (self.backend.selected() != 'tui' or document is None
                    or not self._same_tui_plan(layout.from_tui_snapshot(document), entry['plan'])):
                raise ControllerError('TUI live endpoint not bound to retained start')
            snapshot, plan, matched = self._observe_tui(baseline)
            if not matched:
                raise ControllerError('TUI recovery awaits a matching native save')
            witness = self._tui_observation(baseline)
            file = witness['file']
        elif witness is not None:
            if (self.backend.selected() != 'tui' or self.backend.endpoint_present('herdr-core')
                    or not self.backend.tui_unit_stopped()):
                raise ControllerError('TUI shutdown not yet proven')
            snapshot = self.backend._optional_snapshot()
            file = self._check_witness(baseline, snapshot, witness, pending=True)
            plan = layout.from_tui_snapshot(snapshot)
            self.backend._db_sessions(plan)
            self.backend.absent(self.backend_sessions(plan), [])
        else:
            return receipt  # R8 reconciles its own offline write/start receipt.
        if (not self._edited(baseline, snapshot, plan) and snapshot == receipt['document']
                and file == receipt.get('start_file')):
            return receipt
        manifest = self.store.read('manifest.json')
        adopted = self._adoption(manifest, receipt, snapshot, retained=entry)
        adopted['tui_lineage'] = self._lineage(baseline)
        adopted['exit_pids'] = witness['pids']
        adopted['exit_run'] = witness['run']
        adopted['start_file'] = file
        entry.update(plan=plan, receipt=adopted)
        if booting:
            self.store.write('boot.json', entry)
        else:
            self._journal(entry, 'restore_pending')
        return adopted

    def _check_witness(self, manifest, snapshot, witness, *, pending=False):
        if witness['hold']:
            raise ControllerError('TUI shutdown save does not match latest live proof')
        current, file = self.backend.snapshot_evidence()
        replay = (pending and file == manifest['receipt'].get('start_file')
                  and snapshot == manifest['receipt']['document'] and witness['run'] == manifest['receipt'].get('exit_run'))
        if (snapshot != current or not layout.supported_tui_save(snapshot)
                or not replay and not self.backend.final_tui_file(witness['run'], file)):
            raise ControllerError('TUI shutdown save does not match latest live proof')
        # The final writer can close panes and change names, tab order or split
        # geometry after the last tick. Each remaining agent must still belong
        # to its independently proven pane in this run. An identity vanishing
        # from a retained pane could be an incomplete native save.
        previous = witness['clients']
        for space in layout.tui_public_identities(snapshot):
            if space is None:
                raise ControllerError('TUI shutdown public binding unavailable')
            for tab in space['tabs']:
                for pane, item in tab['panes'].items():
                    client = previous.get(pane)
                    if client is None and item['session_id'] is None:
                        continue
                    if (not client or client['run'] != witness['run'] or client['session_id'] != item['session_id']
                            or client['cwd'] != item['cwd']):
                        raise ControllerError('TUI shutdown session binding unavailable')
        if not self.backend._pids_absent([witness['run']]) or not self.backend._pids_absent(witness['pids']):
            raise ControllerError('TUI process exit not proven')
        return file

    def _complete_boot(self, boot):
        receipt = boot['receipt']
        if 'tui_lineage' in receipt:
            self._refresh_boot_witness(boot)
        receipt['pending'] = None
        if 'adoption_backup' in receipt or self.store.read('manifest.json') is None:
            self.store.write('manifest.json', self._manifest(
                {'target': 'tui', 'plan': boot['plan'], 'txid': receipt['txid']}, receipt))
        boot['status'] = 'complete'
        self.store.write('boot.json', boot)

    def _refresh_boot_witness(self, boot):
        """Do not carry exited PIDs from the preceding incarnation into a
        completed boot, including completion through interrupted-start recovery.
        """
        receipt = boot['receipt']
        if not self.backend.endpoint_present('tui'):
            raise ControllerError('TUI boot lost its live endpoint')
        baseline = self._manifest({'target': 'tui', 'plan': boot['plan'], 'txid': receipt['txid']}, receipt)
        disk, _, matched = self._observe_tui(baseline)
        if not matched or self._edited(baseline, disk, layout.from_tui_snapshot(disk)):
            raise ControllerError('TUI boot lost its verified layout')
        proof = self._tui_observation(baseline)
        receipt['ready_run'] = {key: proof[key] for key in ('run', 'pids', 'clients')}

    def restore(self):
        journal = self.store.read('transaction.json')
        if journal and journal.get('phase') != 'complete':
            raise ControllerError('unfinished switch blocks automatic restore')
        if self.backend.selected() == 'herdr-core':
            self.backend.restore_current()
            return
        if self.backend.endpoint_present('herdr-core'):
            raise ControllerError('unselected core remains active')
        manifest = self.store.read('manifest.json')
        if manifest is not None and manifest['runtime'] != 'tui':
            raise ControllerError('selection differs from owned manifest; switch required')
        boot = self.store.read('boot.json')
        if boot and boot.get('status') != 'complete':
            raise ControllerError('TUI boot startup uncertain; use recover')
        if boot and manifest is None:
            # Pre-K boot-only ownership: the previous authorized start is
            # evidence, not permission for any different offline snapshot.
            if (boot.get('runtime') != 'tui' or boot['receipt'].get('runtime') != 'tui'
                    or boot['receipt']['pending'] is not None):
                raise ControllerError('TUI completed boot receipt inconsistent')
            manifest = self._manifest({'target': 'tui', 'plan': boot['plan'],
                                       'txid': boot['receipt']['txid']}, boot['receipt'])
        if self.backend.endpoint_present('tui'):
            if manifest is not None:
                self._restore_live_tui(manifest)
            return  # Never take over a healthy manually started default TUI.
        self._boot_saved_tui(manifest, boot)

    def _boot_saved_tui(self, manifest, previous_boot):
        if not self.backend.tui_unit_stopped():
            raise ControllerError('TUI shutdown not yet proven')
        snapshot = self.backend._optional_snapshot()
        if snapshot is None or not layout.supported_tui_save(snapshot):
            raise ControllerError('TUI boot requires an explicit saved layout')
        plan = layout.from_tui_snapshot(snapshot)
        edited = manifest and self._edited(manifest, snapshot, plan)
        witness = manifest and self._tui_observation(manifest)
        receipt = {'runtime': 'tui', 'txid': uuid.uuid4().hex, 'document': snapshot,
                   'pending': {'operation': 'tui.start'}}
        receipt['tui_lineage'] = self._lineage(manifest) if manifest else receipt['txid']
        if witness is not None:
            authorized = self._check_witness(manifest, snapshot, witness)
            # Do not spend the same observed write on two distinct boot intents.
            prior = previous_boot and previous_boot['receipt']
            if (prior and prior.get('tui_lineage') == receipt['tui_lineage'] and 'start_file' in prior
                    and authorized['mtime_ns'] <= prior['start_file']['mtime_ns']):
                raise ControllerError('TUI shutdown save not newer than prior launch')
            receipt.update(start_file=authorized, exit_pids=witness['pids'])
            receipt['exit_run'] = witness['run']
        elif edited:
            raise ControllerError('TUI boot snapshot differs from owned layout without live proof')
        else:
            # Pre-K installations also kept an exact-file ownership marker.
            owned = self.store.read('owned-tui.json')
            if owned is not None:
                old = {'plan': layout.from_tui_snapshot(owned['document']), 'receipt': owned}
                if self._edited(old, snapshot, plan):
                    raise ControllerError('TUI owned records disagree without live proof')
        self.backend._db_sessions(plan)
        identities = self.backend_sessions(plan)
        self.backend.absent(identities, [])
        if edited:
            receipt = self._adoption(manifest, receipt, snapshot)
        self._check_tui_start_boundary(receipt)
        boot = {'schema_version': 1, 'runtime': 'tui', 'status': 'start_pending',
                'plan': plan, 'receipt': receipt}
        self.store.write('boot.json', boot)
        # Publication is a scheduling boundary; an unchanged socket alone
        # does not prove the captured processes exited or the file stayed put.
        self._check_tui_start_boundary(receipt)
        self.backend.absent(identities, [])
        self.backend.command(['/usr/bin/systemctl', '--user', 'start', 'remote-herdr-tui.service'])
        # Type=exec is not readiness. Keep ownership through live proof.
        self.backend._wait_ready('tui', plan, receipt)
        self._complete_boot(boot)

    def _check_tui_start_boundary(self, receipt):
        if (self.backend.selected() != 'tui' or not self.backend.tui_unit_stopped()
                or self.backend.endpoint_present('tui') or self.backend.endpoint_present('herdr-core')
                or self.backend._optional_snapshot() != receipt['document']
                or 'start_file' in receipt and self.backend.snapshot_evidence()[1] != receipt['start_file']
                or 'exit_run' in receipt and not self.backend._pids_absent([receipt['exit_run']])
                or 'exit_pids' in receipt and not self.backend._pids_absent(receipt['exit_pids'])):
            raise ControllerError('TUI boot observation changed')
