"""Serialized, private switch journal. Unknown mutations are never replayed."""
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import uuid

import layout
import protocol


class ControllerError(ValueError):
    """Fixed-label diagnostics only; journals contain the private detail."""


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
            self._safe(os.fstat(self.fd))
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
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
                boot['receipt'] = self.backend.recover_tui(
                    boot['plan'], boot['receipt']['txid'], boot['receipt'], preserve_snapshot=True)
                boot['status'] = 'complete'
                self.store.write('boot.json', boot)
                return
            if not journal or journal.get('schema_version') != 1:
                raise ControllerError('switch journal unavailable')
            phase = journal['phase']
            if phase == 'complete':
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
                receipt = self.backend.recover_tui(journal['plan'], journal['txid'], receipt)
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

    def restore(self):
        journal = self.store.read('transaction.json')
        if journal and journal.get('phase') != 'complete':
            raise ControllerError('unfinished switch blocks automatic restore')
        if self.backend.selected() == 'herdr-core':
            self.backend.restore_current()
        else:
            if self.backend.endpoint_present('herdr-core'):
                raise ControllerError('unselected core remains active')
            manifest = self.store.read('manifest.json')
            if manifest is not None and manifest['runtime'] != 'tui':
                raise ControllerError('selection differs from owned manifest; switch required')
            if self.backend.endpoint_present('tui'):
                if manifest is not None:
                    self.backend.verify('tui', manifest['plan'], manifest['receipt'])
                return  # Never take over a healthy manually started default TUI.
            snapshot = self.backend._optional_snapshot()
            if snapshot is None:
                raise ControllerError('TUI boot requires an explicit saved layout')
            plan = layout.from_tui_snapshot(snapshot)
            if manifest and self.backend._semantic(plan) != self.backend._semantic(manifest['plan']):
                raise ControllerError('TUI boot snapshot differs from owned layout')
            boot = self.store.read('boot.json')
            if boot and boot.get('status') == 'start_pending':
                raise ControllerError('TUI boot startup uncertain; use recover')
            self.backend.absent(self.backend_sessions(plan), [])
            receipt = {'runtime': 'tui', 'txid': uuid.uuid4().hex, 'document': snapshot,
                       'pending': {'operation': 'tui.start'}}
            boot = {'schema_version': 1, 'runtime': 'tui', 'status': 'start_pending',
                    'plan': plan, 'receipt': receipt}
            self.store.write('boot.json', boot)
            self.backend.command(['/usr/bin/systemctl', '--user', 'start', 'remote-herdr-tui.service'])
            # Type=exec is not readiness. Keep ownership through live session and
            # topology proof so a switch cannot race an authorized delayed exec.
            self.backend._wait_ready('tui', plan, receipt)
            boot['status'] = 'complete'
            receipt['pending'] = None
            self.store.write('boot.json', boot)
