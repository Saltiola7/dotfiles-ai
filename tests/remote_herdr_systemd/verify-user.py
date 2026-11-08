#!/usr/bin/env python3
"""Disposable native qualification. Loopback-only provider; no raw diagnostics.

OpenCode API provenance at v1.18.25 (not the legacy SDK /session route):
packages/cli/src/commands/handlers/api.ts and commands.ts: api --data, raw HTTP.
packages/protocol/src/groups/session.ts: POST /api/session, GET /api/session/:sessionID.
packages/schema/src/{location,session}.ts: location.directory, response.data.id.
Runtime OpenAPI is checked before the first mutation. Unsupported schemas fail;
the fixture never fabricates or migrates SQLite rows to satisfy the adapter.
"""
import importlib.util
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from pathlib import Path
import signal
import socket
import sqlite3
import stat
import struct
import subprocess
import sys
import threading
import time
import uuid


HOME = Path('/home/fixture')
SOURCE = HOME / '.local/share/chezmoi-dotfiles-ai'
CONFIG = HOME / '.config/dotfiles-ai/chezmoi.toml'
BIN = HOME / '.local/bin'
NATIVE = HOME / '.opencode/bin/opencode'
ROOT = HOME / '.local/state/dotfiles-ai/herdr-runtime'
EXPECTED = HOME / 'qualification.json'
STEP = 'initialization'


class CommandFailure(RuntimeError):
    def __init__(self, reason):
        self.reason = reason


def require(condition):
    if not condition:
        raise RuntimeError()


def run(*argv, timeout=90, env=None):
    # Never use check=True: CalledProcessError includes native argv/output.
    result = subprocess.run([str(a) for a in argv], capture_output=True, text=True,
                            cwd=HOME, env=env, timeout=timeout)
    if result.returncode != 0:
        # Literal program/hook names and numeric statuses only. Native text,
        # registration, provider messages and command arguments remain withheld.
        reason = 'command-exit-' + str(result.returncode)
        hooks = {'install-00-remote-herdr.sh', 'install-00z-remote-herdr-core.sh',
                 'install-01-remote-opencode.sh', 'install-04-remote-opencode-service.sh',
                 'install-05-remote-herdr-runtime.sh'}
        match = re.search(r'chezmoi: ([a-z0-9.-]+\.sh): exit status ([0-9]{1,3})', result.stderr)
        if match and match[1] in hooks:
            reason = match[1] + '-exit-' + match[2]
        raise CommandFailure(reason)
    if len(result.stdout) + len(result.stderr) > 2 * 1024 * 1024:
        raise CommandFailure('output-bound')
    return result.stdout.strip()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit(*args):
    return run('/usr/bin/systemctl', '--user', *args, timeout=30)


def cli(*args):
    return run(BIN / 'remote-herdr', *args, timeout=180)


def wait(check, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except Exception:
            pass  # Observations only; never retry native mutations.
        time.sleep(1)
    raise RuntimeError()


def write(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)


class HeldProvider:
    """One bounded ChatCompletions stream, owned only by prepare's lifetime.

    v1.18.25 core/session/runner/model.ts selects the native compatible-chat
    transport for @ai-sdk/openai-compatible; this does not run an npm package.
    No credential or environment integration is configured or consulted here.
    """

    def __init__(self):
        self.nonce = 'rrw007f_' + uuid.uuid4().hex
        self.session_id = None
        self.held = threading.Event()
        self.release = threading.Event()
        self.done = threading.Event()
        self.lock = threading.Lock()
        self.requests = 0
        self.failed = False  # Sanitized thread failure: never retain request/error text.

    def __enter__(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def do_GET(self):
                with fixture.lock:
                    fixture.failed = True
                self.send_error(404)

            def do_POST(self):
                try:
                    with fixture.lock:
                        fixture.requests += 1
                        require(fixture.requests == 1)
                    require(self.path == '/v1/chat/completions')
                    require(self.headers.get('Transfer-Encoding') is None)
                    length = int(self.headers.get('Content-Length', '0'))
                    require(0 < length <= 1024 * 1024)
                    raw = self.rfile.read(length)
                    require(len(raw) == length)
                    body = json.loads(raw)
                    require(body['model'] == 'held' and body['stream'] is True)
                    require(fixture.session_id is not None)
                    require(self.headers.get('X-Session-Id') == fixture.session_id)
                    require(bool(self.headers.get('x-session-affinity')))
                    require(any(message.get('role') == 'user' and
                                (message.get('content') == fixture.nonce or
                                 any(part.get('type') == 'text' and part.get('text') == fixture.nonce
                                     for part in message.get('content', []) if isinstance(part, dict)))
                                for message in body['messages']))
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Connection', 'close')
                    self.end_headers()

                    def chunk(content, finish=None, usage=None):
                        value = {'id': 'chatcmpl-rrw007f', 'object': 'chat.completion.chunk',
                                 'created': 0, 'model': 'held',
                                 'choices': [{'index': 0, 'delta': {'content': content},
                                              'finish_reason': finish}], 'usage': usage}
                        self.wfile.write(('data: ' + json.dumps(value) + '\n\n').encode())
                        self.wfile.flush()

                    chunk('RRW007F-BEGIN:')
                    fixture.held.set()  # Explicit barrier after the original stream flush.
                    require(fixture.release.wait(360))
                    chunk(fixture.nonce + ':END')
                    chunk('', 'stop', {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2})
                    self.wfile.write(b'data: [DONE]\n\n')
                    self.wfile.flush()
                except Exception:
                    with fixture.lock:
                        fixture.failed = True
                finally:
                    self.close_connection = True
                    fixture.done.set()

        class Server(ThreadingHTTPServer):
            daemon_threads = False

            def handle_error(self, request, client_address):
                with fixture.lock:
                    fixture.failed = True

        self.server = Server(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()  # Joins only fixture-owned, bounded HTTP workers.
        self.thread.join(timeout=10)
        require(not self.thread.is_alive())

    def check(self):
        with self.lock:
            require(not self.failed and self.requests == 1)

    def config(self):
        return {'model': 'rrw007f/held', 'autoupdate': False, 'share': 'disabled',
                'snapshots': False, 'providers': {'rrw007f': {
                    'name': 'RRW007F loopback fixture',
                    'api': {'type': 'aisdk', 'package': '@ai-sdk/openai-compatible',
                            'url': 'http://127.0.0.1:' + str(self.server.server_port) + '/v1'},
                    'models': {'held': {'name': 'Held fixture',
                                       'capabilities': {'tools': False, 'input': ['text'], 'output': ['text']},
                                       'limit': {'context': 100000, 'output': 1024}}}}}}


def history(session_id):
    # Public v1.18.25 protocol/groups/session.ts and schema/{event,session-event}.ts.
    events = []
    after = 0
    for _ in range(100):
        page = api('get', '/api/session/' + session_id + '/history?limit=100&after=' + str(after))
        for event in page['data']:
            require(event['data']['sessionID'] == session_id)
            require(event['durable']['aggregateID'] == session_id)
            require(event['durable']['seq'] > after)
            after = event['durable']['seq']
            events.append(event)
        if not page['hasMore']:
            return events
        require(page['data'])
    raise RuntimeError()


def inflight_switch(provider, plan, pid):
    global STEP
    STEP = 'inflight-turn-admission'
    session_id = plan['spaces'][0]['tabs'][0]['panes'][0]['session_id']
    provider.session_id = session_id
    message_id = 'msg_' + provider.nonce
    admitted = api('post', '/api/session/' + session_id + '/prompt', {
        'id': message_id, 'prompt': {'text': provider.nonce}, 'delivery': 'steer', 'resume': True})['data']
    require(admitted['id'] == message_id and admitted['sessionID'] == session_id)
    require(provider.held.wait(120))
    provider.check()

    def typed(events, kind):
        return [event for event in events if event['type'] == 'session.next.' + kind]

    def running():
        return api('get', '/api/session/active')['data'].get(session_id) == {'type': 'running'}

    def started():
        events = history(session_id)
        return typed(events, 'step.started')

    starts = wait(started)
    require(len(starts) == 1)
    assistant_id = starts[0]['data']['assistantMessageID']

    def held():
        provider.check()
        require(not provider.release.is_set() and not provider.done.is_set())
        require(backend_pid() == pid and running())
        events = history(session_id)
        require(typed(events, 'step.started') == starts)
        require(not typed(events, 'step.ended') and not typed(events, 'step.failed'))

    STEP = 'inflight-turn-before-switch'
    held()
    switch('tui', plan, pid)  # Existing proof checks old client PIDs absent, same sessions restored.
    STEP = 'inflight-turn-after-switch'
    held()
    provider.release.set()  # Complete the original connection, never submit another prompt.
    STEP = 'inflight-turn-settlement'
    require(provider.done.wait(30))
    provider.check()

    def settled():
        events = history(session_id)
        if not typed(events, 'step.ended') or session_id in api('get', '/api/session/active')['data']:
            return None
        return events

    events = wait(settled)
    require(typed(events, 'step.started') == starts)
    ends = typed(events, 'step.ended')
    require(len(ends) == 1 and ends[0]['data']['assistantMessageID'] == assistant_id)
    require(ends[0]['data']['finish'] == 'stop' and not typed(events, 'step.failed'))
    texts = typed(events, 'text.ended')
    require(len(texts) == 1 and texts[0]['data']['assistantMessageID'] == assistant_id)
    require(texts[0]['data']['text'] == 'RRW007F-BEGIN:' + provider.nonce + ':END')
    admissions = typed(events, 'prompt.admitted')
    require(len(admissions) == 1 and admissions[0]['data']['messageID'] == admitted['id'])
    require(admissions[0]['durable']['seq'] == admitted['admittedSeq'])
    prompts = typed(events, 'prompted')
    require(len(prompts) == 1 and prompts[0]['data']['messageID'] == admitted['id'])
    require(admissions[0]['data']['prompt']['text'] == provider.nonce)
    require(prompts[0]['data']['prompt']['text'] == provider.nonce)
    require(backend_pid() == pid)
    provider.check()
    print('F07: inflight-turn-preservation-complete')


def api(method, path, body=None):
    # Registration/password stays in private memory and the subprocess environment.
    registration = HOME / '.local/state/opencode/service.json'
    metadata = registration.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()
            and not metadata.st_mode & 0o077)
    service = json.loads(registration.read_text())
    env = dict(os.environ, OPENCODE_PASSWORD=service['password'])
    args = [NATIVE, 'api', '--server', service['url'], method, path]
    if body is not None:
        args += ['--data', json.dumps(body)]
    return json.loads(run(*args, env=env, timeout=30))


def adapter():
    sys.path.insert(0, str(HOME / '.local/share/dotfiles-ai/remote-herdr'))
    from controller import Store
    from native import Native
    return Store, Native


def observe(target, plan):
    Store, Native = adapter()
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        manifest = store.read('manifest.json')
        require(manifest is not None and manifest['runtime'] == target)
        require(backend._semantic(manifest['plan']) == backend._semantic(plan))
        backend.verify(target, manifest['plan'], manifest['receipt'])
        capture = backend.capture(target)
        require(backend._semantic(capture['plan']) == backend._semantic(plan))
        clients = backend._coverage(plan)
        require(len(clients) == 3)
        for client in clients:
            backend._client_argv(client['pid'], client['session_id'])
            require((Path('/proc') / str(client['pid']) / 'exe').resolve() == NATIVE)
        for space in plan['spaces']:
            for tab in space['tabs']:
                for pane in tab['panes']:
                    data = api('get', '/api/session/' + pane['session_id'])['data']
                    require(data['id'] == pane['session_id'])
                    require(data['location']['directory'] == pane['cwd'])
        if target == 'herdr-core':
            require(unit('show', 'remote-herdr-tui.service', '-p', 'ActiveState', '--value') == 'inactive')
            transient_owners(backend, clients)
        else:
            require(unit('is-active', 'remote-herdr-tui.service') == 'active')
        return capture


def transient_owners(backend, clients):
    # Upstream 3965a46 platform/systemd.rs owns all three unit families.
    units = json.loads(unit('list-units', '--all', '--output=json', '--no-pager', 'hc-*.service'))
    names = [item['unit'] for item in units]
    for prefix in ('hc-serve-', 'hc-hold-', 'hc-shutdown-'):
        matches = [name for name in names if name.startswith(prefix)]
        require(matches)
        for name in matches:
            require(unit('show', name, '-p', 'Transient', '--value') == 'yes')
    for client in clients:
        cgroup = (Path('/proc') / str(client['pid']) / 'cgroup').read_text()
        require('hc-hold-' in cgroup and '.service' in cgroup)
    require(not list((HOME / '.config/systemd/user').glob('hc-*.service')))
    require(backend.endpoint_present('herdr-core') and not backend.endpoint_present('tui'))


def backend_pid():
    f01 = load('f01', '/opt/f01/verify-user.py')
    return f01.ready()[0]  # Real authenticated API identity + owner + listener proof.


def switch(target, plan, pid):
    global STEP
    STEP = 'switch-' + target
    Store, Native = adapter()
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        before = backend.capture(backend.selected())
    cli('switch', target)
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        journal = store.read('transaction.json')
        require(journal['phase'] == 'complete')
        require(backend._pids_absent(before['pids']))
        # New clients for the same sessions may now exist; old PID/start times may not.
        require(backend._pids_absent(before['clients']))
        require(store.read(journal['capture']['backup']) is not None)
    observe(target, plan)
    require(backend_pid() == pid)


def interrupted_switch(plan, pid):
    """Kill only our CLI after its real journal admits target startup.

No fabricated journal or native fault hook: target startup may still complete.
Recovery must observe that outcome and not blindly launch another client.
"""
    global STEP
    STEP = 'interrupted-switch'
    Store, Native = adapter()
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        before = backend.capture('herdr-core')
        old_txid = store.read('transaction.json')['txid']
    child = subprocess.Popen([str(BIN / 'remote-herdr'), 'switch', 'tui'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=HOME)
    interrupted = False
    try:
        deadline = time.monotonic() + 120
        while child.poll() is None and time.monotonic() < deadline:
            journal = json.loads((ROOT / 'transaction.json').read_text())
            if journal['txid'] != old_txid and journal['phase'] in {'restore_pending', 'verify_pending'}:
                child.send_signal(signal.SIGSTOP)
                paused = json.loads((ROOT / 'transaction.json').read_text())
                require(paused['phase'] in {'restore_pending', 'verify_pending'})
                require(backend._pids_absent(before['pids']))
                child.kill()
                child.wait(timeout=5)
                interrupted = True
                break
            time.sleep(0.01)
        require(interrupted)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
    STEP = 'interrupted-switch-recovery'
    # Automatic restore must refuse this unfinished real transaction.
    refusal = subprocess.run([str(BIN / 'remote-herdr'), 'restore'], cwd=HOME,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    require(refusal.returncode == 75)
    cli('recover')
    observe('tui', plan)
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        require(store.read('transaction.json')['phase'] == 'complete')
        require(backend._pids_absent(before['pids']))
    require(backend_pid() == pid)


def prepare():
    with HeldProvider() as provider:
        prepare_fixture(provider)


def prepare_fixture(provider):
    global STEP
    STEP = 'install-bootstrap-config'
    bootstrap = load('bootstrap', '/opt/f01/bootstrap.py')
    bootstrap.prepare_config()
    STEP = 'install-chezmoi'
    bootstrap.install_chezmoi()
    # Only the allowlisted partial source is applied. No foundation/cloud tools.
    opencode_config = HOME / '.config/opencode'
    opencode_config.mkdir(mode=0o700)
    write(opencode_config / 'opencode.json', provider.config())
    STEP = 'install-apply'
    run(BIN / 'chezmoi', '-c', CONFIG, '-S', SOURCE, 'apply', timeout=600)
    # Pause only the disposable timer during serial fixture manipulation.
    STEP = 'pause-restore-timer'
    unit('stop', 'remote-herdr-restore.timer', 'remote-herdr-restore.service')
    STEP = 'load-installed-adapter'
    Store, Native = adapter()
    STEP = 'open-private-store'
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        STEP = 'probe-default-tui'
        if backend.endpoint_present('tui'):
            run(BIN / 'herdr', 'session', 'stop', 'default', '--json')
        unit('stop', 'remote-herdr-tui.service')
        require(not backend.endpoint_present('tui'))
        STEP = 'verify-tui-binary'
        backend._binary('tui')
        STEP = 'verify-core-binary'
        backend._binary('herdr-core')
    STEP = 'verify-installed-core'
    run(BIN / 'remote-herdr-core', 'check')
    STEP = 'verify-opencode-version'
    version = run(NATIVE, '--version')
    require(re.fullmatch(r'opencode v2\.[0-9]+\.[0-9]+', version) is not None)
    # F01 deliberately delegates updates to the native v2 installer. The old
    # source asset defaults are not a Linux remote runtime pin. Bind this proof
    # to the observed version and bytes, then enforce the runtime API schema.
    write(HOME / 'qualified-opencode.json', {'version': version,
          'binary_sha256': hashlib.sha256(NATIVE.read_bytes()).hexdigest()})
    print('F07: ' + version + '; binary-sha256=' + hashlib.sha256(NATIVE.read_bytes()).hexdigest())
    STEP = 'verify-shared-backend'
    pid = backend_pid()
    STEP = 'session-api-schema'
    spec = api('get', '/openapi.json')
    create = spec['paths']['/api/session']['post']
    require(create['operationId'] == 'v2.session.create')
    require('/api/session/{sessionID}' in spec['paths'])
    directories = [HOME / 'project alpha', HOME / 'project beta']
    for directory in directories:
        directory.mkdir(mode=0o700)
    sessions = []
    for directory in (directories[0], directories[0], directories[1]):
        created = api('post', '/api/session', {'location': {'directory': str(directory)},
                                             'model': {'id': 'held', 'providerID': 'rrw007f'}})['data']
        require(created['location']['directory'] == str(directory))
        sessions.append(created['id'])
    require(len(set(sessions)) == 3)
    plan = {'schema_version': 1, 'spaces': [
        {'name': 'Alpha space', 'directory': str(directories[0]), 'tabs': [
            {'name': 'Review split', 'panes': [
                {'key': 's0-t0-p0', 'cwd': str(directories[0]), 'session_id': sessions[0]},
                {'key': 's0-t0-p1', 'cwd': str(directories[0]), 'session_id': sessions[1]}],
             'root': {'axis': 'row', 'ratio': 0.375,
                      'children': [{'pane': 's0-t0-p0'}, {'pane': 's0-t0-p1'}]}}]},
        {'name': 'Beta space', 'directory': str(directories[1]), 'tabs': [
            {'name': 'Exact saved agent', 'panes': [
                {'key': 's1-t0-p0', 'cwd': str(directories[1]), 'session_id': sessions[2]}],
             'root': {'pane': 's1-t0-p0'}}]}]}
    write(EXPECTED, plan)
    STEP = 'native-sqlite-contract'
    # Observe the actual adapter-required store; do not create/fill a missing DB.
    database = HOME / '.local/share/opencode/opencode.db'
    require(database.is_file())
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only = ON')
        require({'id', 'directory'} <= {row[1] for row in db.execute('PRAGMA table_info(session)')})
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        backend._db_sessions(plan)
        require(not backend.scan(set(sessions)))
        STEP = 'plain-shell-adoption'
        backend.command(['herdr-core', 'server', 'start', '--json'])
        wait(lambda: backend.endpoint_present('herdr-core'))
        shell = backend.core('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': str(directories[0]),
                                             'keep': True, 'no_parent': True, 'no_notify': True, 'wait': False})
        address = shell['address']
        def shell_ready():
            backend._live_program(backend._terminal(address))
            return True
        wait(shell_ready)
        import layout
        plain = {'schema_version': 1, 'spaces': [{'name': 'Desktop shell', 'directory': str(directories[0]),
                 'tabs': [{'name': 'Original shell', 'panes': [{'key': 's0-t0-p0', 'cwd': str(directories[0]),
                           'session_id': None}], 'root': {'pane': 's0-t0-p0'}}]}]}
        document = layout.to_app_document(plain, {'s0-t0-p0': address})
        _, version = backend._document()
        backend.core('doc.set', {'name': 'herdr-app', 'value': document, 'version': version})
    cli('switch', 'herdr-core', '--from-file', EXPECTED, '--replace-target')
    observe('herdr-core', plan)
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        backups = [store.read(path.name) for path in ROOT.glob('backup-*.json')]
        require(any(value.get('document') == document and
                    address in {t['address'] for t in value.get('terminals', [])} for value in backups))
        require(address in {t['address'] for t in backend._terminals()})
    require(backend_pid() == pid)
    inflight_switch(provider, plan, pid)
    switch('herdr-core', plan, pid)
    interrupted_switch(plan, pid)
    switch('herdr-core', plan, pid)
    restart_and_recover(plan, pid)
    STEP = 'arm-core-boot'
    require(unit('is-enabled', 'remote-herdr-restore.timer') == 'enabled')
    unit('start', 'remote-herdr-restore.timer')


def restart_and_recover(plan, pid):
    global STEP
    Store, Native = adapter()
    STEP = 'core-preserving-restart'
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        before = backend._coverage(plan)
        # Peer credentials identify the real owned core, not an invented status PID.
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.connect(str(backend._core_endpoint()))
            core_pid, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require(uid == os.getuid())
        proc = Path('/proc') / str(core_pid)
        require((proc / 'exe').resolve() == BIN / 'herdr-core')
        require('hc-serve-' in (proc / 'cgroup').read_text())
        fd = os.pidfd_open(core_pid)
        try:
            signal.pidfd_send_signal(fd, signal.SIGTERM)
        finally:
            os.close(fd)
        wait(lambda: not backend.endpoint_present('herdr-core'))
    cli('restore')
    observe('herdr-core', plan)
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        require(backend._coverage(plan) == before)
        STEP = 'core-explicit-stop'
        capture = backend.capture('herdr-core')
        # Explicit native stop kills programs, unlike SIGTERM above.
        backend.stop('herdr-core', capture)
        backend.absent(set(p['session_id'] for s in plan['spaces'] for t in s['tabs'] for p in t['panes']), capture['clients'])
        require(backend._pids_absent(capture['pids']))
    STEP = 'core-shell-recovery'
    cli('restore')
    observe('herdr-core', plan)
    cli('recover')  # A completed transaction must be observational/idempotent.
    observe('herdr-core', plan)
    require(backend_pid() == pid)


def boot(target):
    global STEP
    STEP = 'boot-' + target
    plan = json.loads(EXPECTED.read_text())
    # No apply/start/restore before these observations: timer must do the work.
    pid = backend_pid()
    wait(lambda: observe(target, plan), seconds=150)
    require(unit('is-enabled', 'remote-herdr-restore.timer') == 'enabled')
    unit('stop', 'remote-herdr-restore.timer', 'remote-herdr-restore.service')
    if target == 'herdr-core':
        switch('tui', plan, pid)
        unit('start', 'remote-herdr-restore.timer')
    else:
        switch('herdr-core', plan, pid)
        switch('tui', plan, pid)
        run(BIN / 'remote-herdr-core', 'check')
        Store, Native = adapter()
        with Store(ROOT) as store:
            backend = Native(HOME, store)
            backend._binary('tui')
            backend._binary('herdr-core')


if __name__ == '__main__':
    try:
        os.umask(0o077)
        require(os.getuid() == 1000 and Path.home() == HOME)
        require(len(sys.argv) == 2)
        stages = {'prepare': prepare, 'verify-core': lambda: boot('herdr-core'),
                  'verify-tui': lambda: boot('tui')}
        stages[sys.argv[1]]()
        print('F07: stage-complete')
    except Exception as error:
        # STEP comes only from literal fixture labels, never exception/native text.
        suffix = '-' + error.reason if isinstance(error, CommandFailure) else '-invariant'
        if isinstance(error, (ImportError, AttributeError, TypeError, KeyError, OSError, UnicodeError)):
            suffix = '-unsupported-interface'
        print('F07: failed-' + STEP + suffix, file=sys.stderr)
        sys.exit(1)
