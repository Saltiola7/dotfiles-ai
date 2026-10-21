"""Isolated maintenance fixtures. No installed OpenCode or Herdr is executed."""
import copy
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'dot_local/bin/executable_opencode-maintenance.tmpl'


@pytest.fixture(scope='session')
def rendered_script(tmp_path_factory):
    from test_herdr_launchagent import _render_herdr_script
    from test_opencode_control_plane import DATA
    values = copy.deepcopy(DATA)
    values['dotfiles_ai']['state']['root'] = '/fixture/configured-state'
    rendered = _render_herdr_script('.local/bin/opencode-maintenance', values)
    target = tmp_path_factory.mktemp('maintenance-source') / 'opencode-maintenance'
    target.write_text(rendered)
    return target


@pytest.fixture
def module(rendered_script):
    return runpy.run_path(str(rendered_script))


@pytest.fixture
def state(tmp_path, monkeypatch):
    root = tmp_path / 'state'
    root.mkdir(mode=0o700)
    (root / '.dotfiles-ai-state').write_text('fixture\n')
    (root / '.dotfiles-ai-state').chmod(0o600)
    (root / 'herdr').mkdir(mode=0o700)
    monkeypatch.setenv('DOTFILES_AI_STATE_ROOT', str(root))
    monkeypatch.setenv('XDG_STATE_HOME', str(root / 'xdg/state'))
    return root


def test_unsupported_actions_never_capture_or_write(module, state, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail('refusal must never invoke capture or network')
    monkeypatch.setitem(module['main'].__globals__, 'prepare', forbidden)
    before = list(state.rglob('*'))
    for action in ('apply', 'recover'):
        assert module['main']([action]) == 75
        response = json.loads(capsys.readouterr().out)
        assert response['activation_allowed'] is False
        assert 'atomic_drain_unsupported' in response['blockers']
    assert list(state.rglob('*')) == before


@pytest.mark.parametrize('action', ['apply', 'recover', 'status'])
def test_cli_redacts_invalid_input(action, tmp_path, rendered_script):
    result = subprocess.run([sys.executable, str(rendered_script), action, '--force-secret'],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 2
    assert 'force-secret' not in result.stdout + result.stderr
    assert json.loads(result.stdout)['error'] == 'invalid_arguments'


def test_duplicate_json_and_budget(module):
    for value in (b'{"id":1,"id":2}', b'[' * 80 + b']' * 80, b'NaN'):
        with pytest.raises(ValueError):
            module['decode'](value)
    with pytest.raises(ValueError):
        module['decode'](b' ' * (module['MAX_BYTES'] + 1))


def test_missing_state_never_creates_fallback(module, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('DOTFILES_AI_STATE_ROOT', str(tmp_path / 'absent'))
    assert module['main'](['prepare', '--herdr-socket', '/absent']) == 75
    assert not (tmp_path / 'absent').exists()
    assert json.loads(capsys.readouterr().out)['error'] == 'state_or_inventory_unavailable'


def test_storage_no_overwrite_and_orphan_inspection(module, state, monkeypatch):
    with module['Store'](state, create=True) as store:
        first = module['empty_checkpoint'](None)
        store.publish(first)
        assert store.load()['generation'] == first['generation']
        with pytest.raises((ValueError, FileExistsError)):
            store.publish(first)
        second = module['empty_checkpoint'](first['generation'])
        replace = os.replace
        def interrupted(src, dst, **kwargs):
            if dst == 'latest.json':
                raise OSError('synthetic disk fault')
            return replace(src, dst, **kwargs)
        monkeypatch.setattr(os, 'replace', interrupted)
        with pytest.raises(OSError):
            store.publish(second)
        assert store.load()['generation'] == first['generation']
        assert store.load(second['generation']) == second
    files = list((state / 'herdr/opencode-maintenance').rglob('*.json'))
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in files)


@pytest.mark.parametrize('kind', ['symlink', 'fifo', 'public'])
def test_registration_private_regular_only(module, state, kind):
    target = state / 'registration.json'
    if kind == 'symlink':
        target.symlink_to(state / '.dotfiles-ai-state')
    elif kind == 'fifo':
        os.mkfifo(target, 0o600)
    else:
        target.write_text('{}')
        target.chmod(0o644)
    with pytest.raises((OSError, ValueError)):
        module['read_private'](target)


@pytest.mark.parametrize('url', ['http://example.com:42', 'http://127.0.0.1:42@evil.test',
    'http://localhost:42', 'file:///etc/passwd', 'http://127.0.0.1:42/path',
    'http://127.0.0.1:42?x=1', 'http://127.0.0.1:42#fragment', 'https://127.0.0.1:42'])
def test_registration_endpoint_rejection(module, url):
    with pytest.raises(ValueError):
        module['registration']({'id': 'native', 'pid': 10, 'version': '2.1.2',
                                'url': url, 'password': 'private-secret'})


def pane(pid=123, viewed='ses_child'):
    return {'pane_id': 'w1:p1', 'terminal_id': 't1', 'pid': pid,
            'owner_session_id': 'ses_root', 'launch_session_id': 'ses_old',
            'viewed_session_id': viewed, 'last_viewed_session_id': 'ses_child',
            'session_directory': '/fixture/repository', 'pane_cwd': '/fixture/shell',
            'client_version': '2.1.2', 'observer_incarnation': 'a' * 32,
            'provenance': 'observer', 'decision': 'verified', 'reasons': []}


def test_missing_and_replaced_observations_retain_previous(module):
    old = pane()
    for current in ([], [pane(pid=456)], [pane(viewed=None)]):
        entries = module['reconcile'](current, [old], True)
        assert entries[0]['decision'] == 'uncertain'
        assert entries[0]['previous']['viewed_session_id'] == 'ses_child'
    assert module['reconcile']([pane()], [old], False)[0]['decision'] == 'verified'


def test_duplicate_views_preserved(module):
    other = {**pane(), 'pane_id': 'w1:p2', 'terminal_id': 't2', 'pid': 456}
    assert len(module['reconcile']([pane(), other], [], True)) == 2


def test_checkpoint_unknown_schema_or_unsafe_generation(module, state):
    with module['Store'](state, create=True) as store:
        for generation in ('../escape', 'a' * 1000, 'a/b'):
            with pytest.raises(ValueError):
                store.load(generation)
        checkpoint = module['empty_checkpoint'](None)
        checkpoint['capabilities']['atomic_drain'] = 'supported'
        with pytest.raises(ValueError):
            store.publish(checkpoint)


def test_no_socket_no_herdr(module, state, monkeypatch, capsys):
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('must not start Herdr'))
    assert module['main'](['prepare', '--herdr-socket', str(state / 'missing.sock')]) == 75
    capsys.readouterr()


@pytest.fixture
def native(module, state, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    service_state = {'requests': [], 'pending': [], 'active': {}, 'fault': None}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            service_state['requests'].append((self.path, self.headers.get('Authorization')))
            if service_state.get('slow_headers'):
                import time
                try:
                    for char in b'HTTP/1.1 200 OK\r\nX-Slow: waiting\r\n\r\n':
                        self.connection.sendall(bytes([char]))
                        time.sleep(0.03)
                except OSError:
                    pass
                return
            if service_state['fault']:
                status, payload = service_state['fault']
                self.send_response(status)
                self.send_header('Location', 'http://127.0.0.1:1/private-secret')
                self.end_headers()
                self.wfile.write(payload)
                return
            endpoint = self.path.split('?')[0]
            if endpoint == '/api/info':
                data = {'pid': 77, 'version': '2.1.2'}
            elif endpoint == '/api/session/active':
                data = {'data': service_state['active']}
            elif endpoint == '/api/model':
                data = {'data': [{'id': 'fixture-model'}]}
            elif endpoint == '/api/session/ses_child':
                data = {'data': {'id': 'ses_child', 'location': {'directory': '/fixture/repository'}, 'title': 'private-secret'}}
            else:
                data = {'data': service_state['pending']}
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    registration_path = state / 'xdg/state/opencode/service.json'
    registration_path.parent.mkdir(parents=True, mode=0o700)
    registration_path.write_text(json.dumps({'id': 'fixture', 'pid': 77, 'version': '2.1.2',
        'url': f'http://127.0.0.1:{httpd.server_port}', 'password': 'private-secret'}))
    registration_path.chmod(0o600)
    service_state.update(path=registration_path)
    try:
        yield service_state
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(2)


@pytest.fixture
def backend(module, state):
    import threading
    # macOS limits UNIX paths to 104 bytes; pytest's nested fixture root is longer.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='maintenance-', dir='/private/tmp') as short:
        path = Path(short) / 'backend.sock'
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path))
        listener.listen()
        listener.settimeout(0.1)
        stop = threading.Event()
        snapshot = {'version': 'fixture', 'protocol': 22,
                    'focused_pane_id': 'w1:p1', 'panes': [{
                    'pane_id': 'w1:p1', 'terminal_id': 't1', 'cwd': '/fixture/shell',
                    'terminal_title': 'private-secret', 'agent': 'opencode',
                    'agent_session': {'agent': 'opencode', 'source': 'herdr:opencode',
                                      'kind': 'id', 'value': 'ses_root'}}]}
        observed = {'requests': [], 'snapshot': snapshot, 'pid': 123}
        def server():
            while not stop.is_set():
                try:
                    client, _ = listener.accept()
                except socket.timeout:
                    continue
                with client:
                    request = json.loads(client.recv(65536))
                    observed['requests'].append(request)
                    if request['method'] == 'session.snapshot':
                        result = {'type': 'session_snapshot', 'snapshot': snapshot}
                    else:
                        assert request['method'] == 'pane.process_info'
                        result = {'type': 'pane_process_info', 'process_info': {'foreground_processes': [{
                            'pid': observed['pid'], 'argv': ['opencode', '-s', 'ses_old', '--prompt', 'private-secret']}]}}
                    client.sendall((json.dumps({'id': request['id'], 'result': result}) + '\n').encode())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        folder = state / 'herdr/opencode-observers'
        folder.mkdir(mode=0o700)
        info = path.stat()
        record = {'schema_version': 1, 'socket': str(path), 'socket_device': info.st_dev,
            'socket_inode': info.st_ino, 'pane_id': 'w1:p1', 'pid': 123,
            'incarnation': 'a' * 32, 'captured_at': __import__('time').time_ns() // 1_000_000_000,
            'sequence': 1, 'client_version': '2.1.2', 'viewed_session_id': 'ses_child',
            'last_viewed_session_id': 'ses_child', 'session_directory': '/fixture/repository',
            'tabs': [{'session_id': 'ses_root', 'active': True}]}
        record_path = folder / module['observer_name'](str(path), 'w1:p1', 123, 'a' * 32)
        record_path.write_text(json.dumps(record))
        record_path.chmod(0o600)
        observed.update(path=path, record=record, record_path=record_path)
        try:
            yield observed
        finally:
            stop.set()
            thread.join(2)
            listener.close()


def test_prepare_exact_child_and_readonly_protocol(module, state, native, backend):
    checkpoint = module['prepare'](state, backend['path'])
    assert checkpoint['complete'] is True
    row = checkpoint['panes'][0]
    assert (row['owner_session_id'], row['launch_session_id'], row['viewed_session_id']) == (
        'ses_root', 'ses_old', 'ses_child')
    assert row['pane_cwd'] != row['session_directory']
    assert row['decision'] == 'verified'
    assert len(backend['requests']) == 2
    assert 'private-secret' not in json.dumps(checkpoint)
    assert '/api/location/reload' not in [r[0] for r in native['requests']]
    assert all(r['method'] in ('session.snapshot', 'pane.process_info') for r in backend['requests'])
    assert checkpoint['capabilities'] == module['CAPABILITIES']


@pytest.mark.parametrize('fault', ['stale', 'future', 'pid', 'home', 'symlink', 'directory', 'schema'])
def test_observer_fault_preserves_last_verified(module, state, native, backend, fault):
    first = module['prepare'](state, backend['path'])
    record = backend['record']
    if fault == 'stale': record['captured_at'] -= 30
    if fault == 'future': record['captured_at'] += 30
    if fault == 'pid': backend['pid'] = 456
    if fault == 'home': record['viewed_session_id'] = None
    if fault == 'directory': record['session_directory'] = '/wrong/directory'
    if fault == 'schema': record['schema_version'] = 99
    backend['record_path'].write_text(json.dumps(record))
    if fault == 'symlink':
        backend['record_path'].unlink()
        backend['record_path'].symlink_to(native['path'])
    second = module['prepare'](state, backend['path'])
    assert second['parent'] == first['generation']
    assert second['complete'] is False
    assert second['panes'][0]['decision'] != 'verified'
    with module['Store'](state) as store:
        assert store.load(first['generation'])['panes'][0]['viewed_session_id'] == 'ses_child'


def test_pending_and_active_remain_blockers(module, state, native, backend):
    native['pending'] = [{'id': 'form1', 'question': 'private-secret'}]
    native['active'] = {'ses_unmapped': {'type': 'running'}}
    checkpoint = module['prepare'](state, backend['path'])
    assert 'active_work' in checkpoint['blockers']
    assert 'pending_interactions' in checkpoint['blockers']
    assert checkpoint['panes'][0]['decision'] == 'blocked'
    assert 'private-secret' not in json.dumps(checkpoint)


@pytest.mark.parametrize('status,payload', [(302, b'private-secret'), (503, b'private-secret'),
    (200, b'{"id":1,"id":2}'), (200, b'x' * (2 * 1024 * 1024 + 1))])
def test_service_fault_preserves_history_and_redacts(module, state, native, backend, status, payload):
    first = module['prepare'](state, backend['path'])
    native['fault'] = status, payload
    second = module['prepare'](state, backend['path'])
    assert second['parent'] == first['generation'] and not second['complete']
    assert second['service'] is None
    assert 'private-secret' not in json.dumps(second)


def test_proxy_ignored_and_registration_drift_refuses(module, native, monkeypatch):
    for key in ('http_proxy', 'HTTP_PROXY', 'all_proxy', 'ALL_PROXY', 'HTTPS_PROXY'):
        monkeypatch.setenv(key, 'http://127.0.0.1:1')
    service = module['Service'](native['path'])
    service.finish()
    native['path'].write_text(native['path'].read_text().replace('private-secret', 'changed-secret'))
    with pytest.raises(ValueError):
        service.finish()
    with pytest.raises(ValueError):
        service.get('/api/location/reload')


def test_status_reads_without_capture_and_preserves_bytes(module, state, native, backend, capsys):
    checkpoint = module['prepare'](state, backend['path'])
    requests = len(native['requests']), len(backend['requests'])
    before = {str(p): p.read_bytes() for p in (state / 'herdr/opencode-maintenance').iterdir()}
    for action in ('status', 'apply', 'recover'):
        assert module['main']([action, '--generation', checkpoint['generation']]) == (0 if action == 'status' else 75)
        capsys.readouterr()
    assert requests == (len(native['requests']), len(backend['requests']))
    assert before == {str(p): p.read_bytes() for p in (state / 'herdr/opencode-maintenance').iterdir()}


def test_registration_identical_replacement_is_drift(module, native):
    service = module['Service'](native['path'])
    replacement = native['path'].with_suffix('.replacement')
    replacement.write_bytes(native['path'].read_bytes())
    replacement.chmod(0o600)
    replacement.replace(native['path'])
    with pytest.raises(ValueError):
        service.finish()


def test_checkpoint_requires_existing_parent(module, state):
    with module['Store'](state, create=True) as store:
        with pytest.raises((OSError, ValueError)):
            store.publish(module['empty_checkpoint']('f' * 32))


def test_preparation_lock_serializes_writers(module, state):
    import fcntl
    import threading
    with module['Store'](state, create=True) as store:
        with module['locked'](store.fd, 'prepare.lock'):
            fd = os.open('prepare.lock', os.O_RDWR, dir_fd=store.fd)
            try:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(fd)


def test_large_inventory_and_duplicate_views(module, state, native, backend, monkeypatch):
    original = copy.deepcopy(backend['snapshot']['panes'][0])
    backend['snapshot']['panes'] = [{**original, 'pane_id': f'w1:p{i}', 'terminal_id': f't{i}'} for i in range(200)]
    for i in range(200):
        record = {**backend['record'], 'pane_id': f'w1:p{i}'}
        path = backend['record_path'].parent / module['observer_name'](str(backend['path']), f'w1:p{i}', 123, 'a' * 32)
        path.write_text(json.dumps(record))
        path.chmod(0o600)
    # Native metadata is identical for these views; no repeated full session enumeration.
    checkpoint = module['prepare'](state, backend['path'])
    assert len(checkpoint['panes']) == 200
    assert all(row['viewed_session_id'] == 'ses_child' for row in checkpoint['panes'])
    assert len(backend['requests']) == 201
    assert 'private-secret' not in json.dumps(checkpoint)


def test_disconnected_backend_retains_uncertain_generation(module, state, native, backend):
    first = module['prepare'](state, backend['path'])
    backend['path'].unlink()
    second = module['prepare'](state, backend['path'])
    assert not second['complete']
    assert second['parent'] == first['generation']
    assert second['panes'][0]['decision'] == 'uncertain'
    assert second['panes'][0]['previous']['viewed_session_id'] == 'ses_child'


def test_overlapping_incarnations_refuse_selection(module, state, native, backend):
    record = {**backend['record'], 'incarnation': 'b' * 32}
    path = backend['record_path'].parent / module['observer_name'](str(backend['path']), 'w1:p1', 123, 'b' * 32)
    path.write_text(json.dumps(record))
    path.chmod(0o600)
    checkpoint = module['prepare'](state, backend['path'])
    assert checkpoint['panes'][0]['decision'] == 'uncertain'
    assert len(list(path.parent.glob('*.json'))) == 2


def test_status_rejects_broken_or_cyclic_ancestry(module, state):
    with module['Store'](state, create=True) as store:
        first = module['empty_checkpoint'](None)
        store.publish(first)
        second = module['empty_checkpoint'](first['generation'])
        store.publish(second)
        path = state / 'herdr/opencode-maintenance' / (first['generation'] + '.json')
        path.unlink()
        with pytest.raises(FileNotFoundError):
            store.load()
        first['parent'] = second['generation']
        path.write_text(json.dumps(first))
        path.chmod(0o600)
        with pytest.raises(ValueError):
            store.load()


def test_total_deadline_cannot_be_swallowed_as_partial_inventory(module, state, backend, monkeypatch):
    def expired(*args):
        raise module['DeadlineExpired']()
    monkeypatch.setitem(module['prepare'].__globals__, 'herdr', expired)
    with pytest.raises(module['DeadlineExpired']):
        module['prepare'](state, backend['path'])
    assert not (state / 'herdr/opencode-maintenance/latest.json').exists()


def test_layout_geometry_preserved_without_titles(module):
    rect = {'x': 0, 'y': 0, 'width': 100, 'height': 40}
    layout = {'workspace_id': 'w1', 'tab_id': 'tab1', 'zoomed': False, 'area': rect,
              'focused_pane_id': 'w1:p1', 'panes': [{'pane_id': 'w1:p1', 'focused': True, 'rect': rect}],
              'splits': [{'id': 's1', 'direction': 'right', 'ratio': 0.5, 'rect': rect}]}
    snapshot = {'layouts': [layout], 'terminal_title': 'private-secret'}
    assert module['sanitize_layout'](snapshot) == {'layouts': [layout]}
    layout['panes'][0]['rect'] = {**rect, 'width': -1}
    with pytest.raises(ValueError):
        module['sanitize_layout'](snapshot)


@pytest.mark.parametrize('bad', [None, [], 'invalid', 7])
def test_malformed_process_records_fail_boundedly(module, state, backend, bad):
    with pytest.raises(ValueError):
        module['observation'](state, str(backend['path']), backend['snapshot']['panes'][0], [bad])


def test_capacity_refusal_preserves_readable_latest(module, state):
    with module['Store'](state, create=True) as store:
        parent = None
        for _ in range(256):
            checkpoint = module['empty_checkpoint'](parent)
            store.write(checkpoint['generation'] + '.json', checkpoint, immutable=True)
            parent = checkpoint['generation']
        store.write('latest.json', {'generation': parent})
        assert store.load()['generation'] == parent
        with pytest.raises(ValueError):
            store.publish(module['empty_checkpoint'](parent))
        assert store.load()['generation'] == parent


def test_configured_root_is_rendered(module):
    assert module['CONFIGURED_STATE_ROOT'] == '/fixture/configured-state'


def test_registration_access_time_is_not_identity_drift(module, native):
    service = module['Service'](native['path'])
    info = native['path'].stat()
    os.utime(native['path'], ns=(info.st_atime_ns + 1_000_000_000, info.st_mtime_ns))
    service.finish()


def test_old_client_version_is_explicit_blocker(module, state, native, backend):
    backend['record']['client_version'] = '2.0.31'
    backend['record_path'].write_text(json.dumps(backend['record']))
    checkpoint = module['prepare'](state, backend['path'])
    assert 'client_version_mismatch' in checkpoint['blockers']
    assert checkpoint['panes'][0]['decision'] == 'blocked'
    assert not checkpoint['complete']


def test_total_cli_deadline_bounds_slow_headers(rendered_script, state, native, backend):
    native['slow_headers'] = True
    source = """import runpy, signal, sys
scope = runpy.run_path(sys.argv[1])
signal.signal(signal.SIGALRM, scope['expire'])
signal.setitimer(signal.ITIMER_REAL, 0.3)
raise SystemExit(scope['main'](['prepare', '--herdr-socket', sys.argv[2]]))
"""
    result = subprocess.run([sys.executable, '-c', source, str(rendered_script), str(backend['path'])],
                            text=True, capture_output=True, timeout=3)
    assert result.returncode == 75
    assert json.loads(result.stdout)['error'] == 'state_or_inventory_unavailable'
    assert not (state / 'herdr/opencode-maintenance/latest.json').exists()
    assert 'private-secret' not in result.stdout + result.stderr
