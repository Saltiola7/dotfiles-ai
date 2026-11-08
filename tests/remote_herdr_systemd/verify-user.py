#!/usr/bin/env python3
"""Disposable native qualification. Loopback-only provider; no raw diagnostics.

OpenCode v2.2.6 source provenance: anomalyco/opencode commit
dc2ffcf8bf26f9e669b6aa22b95f50e12be15e06 (not the legacy SDK /session route):
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
from urllib.parse import urlsplit


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
    try:
        return run(BIN / 'remote-herdr', *args, timeout=180)
    except CommandFailure:
        # Inspect only the failed fixture transaction, never replay its effects.
        # Phase and pending operations are restricted to source-defined labels.
        Store, Native = adapter()
        with Store(ROOT) as store:
            journal = store.read('transaction.json') or {}
            phase = journal.get('phase')
            phases = {'stop_pending', 'prepare_pending', 'prepared', 'select_pending',
                      'restore_pending', 'verify_pending', 'complete'}
            label = phase if phase in phases else 'before-journal'
            receipt = (store.read('receipt-' + journal['txid'] + '.json')
                       if phase in phases and journal.get('txid') else None)
            operation = ((receipt or {}).get('pending') or {}).get('operation')
            if operation in {'server.start', 'terminal.run', 'terminal.kill', 'doc.set',
                             'tui.write', 'tui.start'}:
                label += '-' + operation.replace('.', '-')
            if phase == 'prepare_pending' and journal.get('target') == 'herdr-core':
                # Mirror observations only, not prepare's start/backup effects.
                check = 'receipt'
                try:
                    backend = Native(HOME, store)
                    require(receipt is not None)
                    check = 'core-endpoint'
                    require(backend.endpoint_present('herdr-core'))
                    check = 'core-document-read'
                    document, _ = backend._document()
                    check = 'core-document-owned'
                    backend._owned_target('herdr-core', document, journal['replace_target'])
                    check = 'core-terminal-inventory'
                    terminals = backend._terminals()
                    for terminal in terminals:
                        if terminal.get('state') == 'live':
                            check = 'core-live-program'
                            if type(terminal.get('pid')) is not int:
                                check += '-spawn-pending'
                            else:
                                program = terminal.get('foreground') or terminal
                                argv = program.get('argv') or []
                                if argv and argv[0] in ('/bin/sh', 'sh', '-sh'):
                                    check += '-posix-shell'
                                elif argv and argv[0] in ('/bin/bash', 'bash', '-bash'):
                                    check += '-bash'
                            identity, _ = backend._live_program(terminal)
                            check = 'core-live-client-absence'
                            require(identity is None)
                    check = 'observations-now-pass'
                except Exception:
                    pass  # Keep only the literal failed observation label.
                label += '-' + check
        raise CommandFailure('controller-' + label) from None


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

    schema/config/provider.ts and ai/providers/openai-compatible.ts select the
    bundled compatible-chat transport; this does not run an npm package.
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
        self.failure_label = 'io'

    def __enter__(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
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
                def expected(condition, label):
                    if not condition:
                        with fixture.lock:
                            fixture.failure_label = label
                        raise RuntimeError()
                try:
                    with fixture.lock:
                        fixture.requests += 1
                        unique = fixture.requests == 1
                    expected(unique, 'duplicate-request')
                    expected(self.path == '/v1/chat/completions', 'route')
                    expected(self.headers.get('Transfer-Encoding') is None, 'transfer-encoding')
                    length = int(self.headers.get('Content-Length', '0'))
                    expected(0 < length <= 1024 * 1024, 'content-length')
                    raw = self.rfile.read(length)
                    require(len(raw) == length)
                    body = json.loads(raw)
                    expected(body['model'] == 'held' and body['stream'] is True, 'model-stream')
                    expected(fixture.session_id is not None, 'session-not-set')
                    expected(self.headers.get('X-Session-Id') == fixture.session_id, 'session-header')
                    expected(bool(self.headers.get('x-session-affinity')), 'affinity-header')
                    expected(any(message.get('role') == 'user' and
                                (message.get('content') == fixture.nonce or
                                 any(part.get('type') == 'text' and part.get('text') == fixture.nonce
                                     for part in message.get('content', []) if isinstance(part, dict)))
                                for message in body['messages']), 'prompt-content')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Transfer-Encoding', 'chunked')
                    self.send_header('Connection', 'close')
                    self.end_headers()

                    def send_sse(data):
                        wire = ('data: ' + data + '\n\n').encode()
                        self.wfile.write(format(len(wire), 'x').encode() + b'\r\n' + wire + b'\r\n')
                        self.wfile.flush()

                    def chunk(content, finish=None, usage=None):
                        value = {'id': 'chatcmpl-rrw007f', 'object': 'chat.completion.chunk',
                                 'created': 0, 'model': 'held',
                                 'choices': [{'index': 0, 'delta': {'content': content},
                                              'finish_reason': finish}], 'usage': usage}
                        send_sse(json.dumps(value))

                    chunk('RRW007F-BEGIN:')
                    fixture.held.set()  # Explicit barrier after the original stream flush.
                    require(fixture.release.wait(360))
                    chunk(fixture.nonce + ':END')
                    chunk('', 'stop', {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2})
                    send_sse('[DONE]')
                    self.wfile.write(b'0\r\n\r\n')
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
            if self.failed:
                raise CommandFailure('provider-' + self.failure_label)
            if self.requests != 1:
                raise CommandFailure('provider-request-count-' + str(self.requests))

    def config(self):
        return {'model': 'rrw007f/held', 'update': 'disable', 'share': 'disabled',
                'snapshots': False, 'providers': {'rrw007f': {
                    'name': 'RRW007F loopback fixture',
                    'package': '@opencode/ai/providers/openai-compatible',
                    'settings': {'baseURL': 'http://127.0.0.1:' + str(self.server.server_port) + '/v1'},
                    'models': {'held': {'name': 'Held fixture',
                                       'capabilities': {'tools': False, 'input': ['text'], 'output': ['text']},
                                       'limit': {'context': 100000, 'output': 1024}}}}}}


def projected_assistant(message, original=None, *, complete=False, nonce=''):
    """Private in-memory projection assertions; failures disclose no payload."""
    def check(condition, label):
        if not condition:
            raise CommandFailure('projection-' + label)
    check(message['type'] == 'assistant' and bool(message['id']), 'assistant-identity')
    check(isinstance(message['model'], dict), 'model-shape')
    check(message['model'].get('id') == 'held', 'model-id')
    check(message['model'].get('providerID') == 'rrw007f', 'model-provider')
    # Model.Ref permits a variant; native clients select the explicit default.
    # Pinned model-resolver.ts withVariant treats "default" as the base model.
    model = message['model']
    check(set(model) <= {'id', 'providerID', 'variant'}, 'model-fields')
    check('variant' not in model or model['variant'] == 'default', 'model-variant')
    check(message['time']['created'] is not None and message.get('error') is None, 'created-or-error')
    check(isinstance(message['content'], list), 'content')
    if original is not None:
        require(message['id'] == original['id'])
        require(message['time']['created'] == original['time']['created'])
        check(message['model'] == original['model'], 'model-changed')
    if complete:
        require(message['time'].get('completed') is not None and message.get('finish') == 'stop')
        require(''.join(part['text'] for part in message['content'] if part['type'] == 'text')
                == 'RRW007F-BEGIN:' + nonce + ':END')
    else:
        check(message['time'].get('completed') is None and message.get('finish') is None, 'completed-early')
    return message


def projected_turn(context, admitted, original=None, *, complete=False):
    # Pinned source projector.ts InboxDelivered inserts id: input.id (the inboxID).
    # Step.Started creates the assistant projection. These persisted message rows
    # do not require Bus.configured's optional payload-log persistence (off by
    # default in v2.2.6); no claim is made about retained event payloads.
    users = [message for message in context if message['type'] == 'user']
    assistants = [message for message in context if message['type'] == 'assistant']
    if len(users) != 1 or len(assistants) != 1:
        raise CommandFailure('projection-count-users-' + str(len(users)) + '-assistants-' + str(len(assistants)))
    if users[0]['id'] != admitted['id'] or users[0]['text'] != admitted['payload']['text']:
        raise CommandFailure('projection-user-identity')
    require(users[0]['time']['created'] is not None)
    for message in context:
        if message['type'] == 'idle':
            if not (complete and message['outcome'] == 'succeeded' and message.get('error') is None):
                raise CommandFailure('projection-unexpected-idle')
    return projected_assistant(assistants[0], original, complete=complete, nonce=admitted['payload']['text'])


def inflight_switch(provider, plan, pid):
    global STEP
    STEP = 'inflight-turn-admission'
    session_id = plan['spaces'][0]['tabs'][0]['panes'][0]['session_id']
    provider.session_id = session_id
    message_id = 'msg_' + provider.nonce
    admitted = api('post', '/api/session/' + session_id + '/prompt', {
        'id': message_id, 'text': provider.nonce, 'delivery': 'steer', 'resume': True})['data']
    require(admitted['id'] == message_id and admitted['sessionID'] == session_id)
    require(admitted['type'] == 'user' and admitted['delivery'] == 'steer')
    require(admitted['payload']['text'] == provider.nonce)
    STEP = 'inflight-model-request'
    if not provider.held.wait(120):
        provider.check()
        raise CommandFailure('provider-hold-not-observed')
    provider.check()

    def running():
        return api('get', '/api/session/active')['data'].get(session_id) == {'type': 'running'}

    def context():
        return api('get', '/api/session/' + session_id + '/context')['data']

    projection_failure = 'projection-not-observed'
    def started():
        nonlocal projection_failure
        try:
            return projected_turn(context(), admitted)
        except CommandFailure as error:
            projection_failure = error.reason
            return None

    STEP = 'inflight-start-projection'
    try:
        original = wait(started)
    except RuntimeError:
        provider.check()
        raise CommandFailure(projection_failure) from None
    message_path = '/api/session/' + session_id + '/message/' + original['id']

    def held():
        provider.check()
        require(not provider.release.is_set() and not provider.done.is_set())
        require(backend_pid() == pid and running())
        projected_assistant(api('get', message_path)['data'], original)
        projected_turn(context(), admitted, original)

    STEP = 'inflight-turn-before-switch'
    held()
    # switch() observes source shutdown and target TCP clients before returning;
    # this callback also checks the original projection between those phases.
    switch('tui', plan, pid, during=held)
    STEP = 'inflight-turn-after-switch'
    held()
    provider.release.set()  # Complete the original connection, never submit another prompt.
    STEP = 'inflight-turn-settlement'
    require(provider.done.wait(30))
    provider.check()

    def settled():
        message = api('get', message_path)['data']
        if message['time'].get('completed') is None or session_id in api('get', '/api/session/active')['data']:
            return None
        return message

    projected_assistant(wait(settled), original, complete=True, nonce=provider.nonce)
    projected_turn(context(), admitted, original, complete=True)
    require(backend_pid() == pid)
    provider.check()
    print('F07: inflight-turn-preservation-complete')


def registration():
    registration = HOME / '.local/state/opencode/service.json'
    metadata = registration.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()
            and not metadata.st_mode & 0o077)
    return json.loads(registration.read_text())


def api(method, path, body=None):
    # Registration/password stays in private memory and the subprocess environment.
    service = registration()
    env = dict(os.environ, OPENCODE_PASSWORD=service['password'])
    args = [NATIVE, 'api', '--server', service['url'], method, path]
    if body is not None:
        args += ['--data', json.dumps(body)]
    return json.loads(run(*args, env=env, timeout=30))


def validate_api_schema(spec):
    """Resolve local refs and require the actual wire structures, not just labels."""
    def resolve(schema):
        seen = set()
        for _ in range(100):
            if '$ref' in schema:
                ref = schema['$ref']
                require(ref.startswith('#/') and ref not in seen)
                seen.add(ref)
                schema = spec
                for key in ref[2:].split('/'):
                    schema = schema[key.replace('~1', '/').replace('~0', '~')]
                continue
            if 'anyOf' in schema:
                nonnull = [item for item in schema['anyOf'] if item.get('type') != 'null']
                if len(nonnull) == 1:
                    schema = nonnull[0]
                    continue
            return schema
        raise RuntimeError()

    def properties(schema, fields, required=()):
        schema = resolve(schema)
        require(schema['type'] == 'object')
        require(set(fields) <= schema['properties'].keys())
        require(set(required) <= set(schema.get('required', [])))
        return schema['properties']

    def string(schema):
        require(resolve(schema)['type'] == 'string')

    def operation(path, method, identifier):
        op = spec['paths'][path][method]
        require(op['operationId'] == identifier)
        params = [resolve(p) for p in spec['paths'][path].get('parameters', []) + op.get('parameters', [])]
        for name in ('sessionID', 'messageID'):
            if '{' + name + '}' in path:
                require(any(p['name'] == name and p['in'] == 'path' and p['required'] is True
                            and resolve(p['schema'])['type'] == 'string' for p in params))
        return op

    def body(op):
        return resolve(op['requestBody'])['content']['application/json']['schema']

    def response(op):
        schema = resolve(op['responses']['200'])['content']['application/json']['schema']
        return properties(schema, {'data'}, {'data'})['data']

    create = operation('/api/session', 'post', 'session.create')
    fields = properties(body(create), {'id', 'parentID', 'title', 'agent', 'model', 'location',
                                       'metadata', 'permissions'})
    require(not resolve(body(create)).get('required'))
    string(properties(fields['location'], {'directory'}, {'directory'})['directory'])
    model = properties(fields['model'], {'id', 'providerID'}, {'id', 'providerID'})
    string(model['id'])
    string(model['providerID'])
    for op in (create, operation('/api/session/{sessionID}', 'get', 'session.get')):
        info = properties(response(op), {'id', 'projectID', 'cost', 'tokens', 'time', 'location'},
                          {'id', 'projectID', 'cost', 'tokens', 'time', 'location'})
        string(info['id'])
        string(properties(info['location'], {'directory'}, {'directory'})['directory'])
        properties(info['time'], {'created', 'updated'}, {'created', 'updated'})
    prompt = operation('/api/session/{sessionID}/prompt', 'post', 'session.prompt')
    fields = properties(body(prompt), {'id', 'text', 'files', 'agents', 'delivery', 'resume'}, {'text'})
    require('prompt' not in fields)
    string(fields['text'])
    require(resolve(fields['resume'])['type'] == 'boolean')
    require(set(resolve(fields['delivery'])['enum']) == {'steer', 'queue'})
    inbox = properties(response(prompt), {'id', 'sessionID', 'type', 'payload', 'delivery', 'time'},
                       {'id', 'sessionID', 'type', 'payload', 'delivery', 'time'})
    string(inbox['id'])
    string(inbox['sessionID'])
    require(resolve(inbox['type']).get('enum') == ['user'] or resolve(inbox['type']).get('const') == 'user')
    string(properties(inbox['payload'], {'text'}, {'text'})['text'])
    active = resolve(response(operation('/api/session/active', 'get', 'session.active')))
    require(active['type'] == 'object')
    require(active['additionalProperties'] is False)
    status = properties(active['patternProperties']['^ses'], {'type'}, {'type'})
    require(resolve(status['type']).get('enum') == ['running'] or
            resolve(status['type']).get('const') == 'running')
    def message_info(schema):
        def members(schema):
            schema = resolve(schema)
            if 'anyOf' in schema:
                return [leaf for item in schema['anyOf'] for leaf in members(item)]
            return [schema]

        variants = {}
        require('anyOf' in resolve(schema))
        for item in members(schema):
            fields = properties(item, {'id', 'time', 'type'}, {'id', 'time', 'type'})
            tag = resolve(fields['type'])
            kind = tag.get('const') or tag['enum'][0]
            variants[kind] = item
        for kind in ('user', 'assistant'):
            required = {'id', 'time', 'type'} | ({'text'} if kind == 'user' else {'model', 'content'})
            fields = properties(variants[kind], required, required)
            string(fields['id'])
            properties(fields['time'], {'created'}, {'created'})
            if kind == 'user':
                string(fields['text'])
            else:
                model = properties(fields['model'], {'id', 'providerID'}, {'id', 'providerID'})
                string(model['id'])
                string(model['providerID'])
                require(resolve(fields['content'])['type'] == 'array')

    context = resolve(response(operation('/api/session/{sessionID}/context', 'get', 'session.context')))
    require(context['type'] == 'array')
    message_info(context['items'])
    message_info(response(operation('/api/session/{sessionID}/message/{messageID}', 'get', 'session.message.get')))


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
        f01 = load('f01', '/opt/f01/verify-user.py')
        _, server = f01.ready()
        port = urlsplit(server).port
        require(port is not None)
        for client in clients:
            backend._client_argv(client['pid'], client['session_id'])
            require((Path('/proc') / str(client['pid']) / 'exe').resolve() == NATIVE)
            # Exact argv and a stored session alone do not prove attachment.
            # Reuse F01's native socket-owner proof against the shared backend.
            wait(lambda: f01.connected(client['pid'], port), seconds=30)
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


def switch(target, plan, pid, during=None):
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
    if during is not None:
        during()
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
    validate_api_schema(spec)
    directories = [HOME / 'project alpha', HOME / 'project beta']
    for directory in directories:
        directory.mkdir(mode=0o700)
    sessions = []
    for directory in (directories[0], directories[0], directories[1]):
        created = api('post', '/api/session', {'location': {'directory': str(directory)},
                                              'title': 'RRW007F fixture ' + str(len(sessions)),
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
    STEP = 'native-database-resolution'
    # Observe the actual adapter-required store; do not create/fill a missing DB.
    with Store(ROOT) as store:
        database = Native(HOME, store).database_path()
    STEP = 'native-database-file'
    require(database.is_file())
    STEP = 'native-database-schema'
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only = ON')
        require({'id', 'directory'} <= {row[1] for row in db.execute('PRAGMA table_info(session_v2)')})
    STEP = 'native-database-session-proof'
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        backend._db_sessions(plan)
        STEP = 'initial-session-client-absence'
        import processes
        try:
            initial_clients = backend.scan(set(sessions))
        except processes.ProcessProofError as error:
            labels = {
                'process observation ownership unavailable': 'process-read-ownership',
                'process observation exceeds bound': 'process-read-bound',
                'process identity unavailable': 'process-identity',
                'process arguments unavailable': 'process-arguments',
                'process directory unsafe': 'process-directory',
                'process inventory unavailable': 'process-inventory',
                'process inventory exceeds bound': 'process-inventory-bound',
                'process session ownership ambiguous': 'process-ambiguous',
            }
            raise CommandFailure(labels.get(str(error), 'process-proof-unavailable')) from None
        if initial_clients:
            raise CommandFailure('unexpected-client-count-' + str(len(initial_clients)))
        STEP = 'core-start'
        backend.command(['herdr-core', 'server', 'start', '--json'])
        STEP = 'core-endpoint'
        wait(lambda: backend.endpoint_present('herdr-core'))
        STEP = 'core-plain-terminal-create'
        shell = backend.core('terminal.run', {'argv': ['/bin/bash', '-l'], 'cwd': str(directories[0]),
                                             'keep': True, 'no_parent': True, 'no_notify': True, 'wait': False})
        address = shell['address']
        def shell_ready():
            backend._live_program(backend._terminal(address))
            return True
        STEP = 'core-plain-terminal-readiness'
        wait(shell_ready)
        import layout
        plain = {'schema_version': 1, 'spaces': [{'name': 'Desktop shell', 'directory': str(directories[0]),
                 'tabs': [{'name': 'Original shell', 'panes': [{'key': 's0-t0-p0', 'cwd': str(directories[0]),
                           'session_id': None}], 'root': {'pane': 's0-t0-p0'}}]}]}
        document = layout.to_app_document(plain, {'s0-t0-p0': address})
        STEP = 'core-initial-document'
        _, version = backend._document()
        backend.core('doc.set', {'name': 'herdr-app', 'value': document, 'version': version})
    STEP = 'core-file-import'
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
    # Use the installed controller directly for this phase so fixed native
    # refusal labels survive the CLI's deliberately generic failure boundary.
    # Native effects and locking are unchanged; never retry a failed restore.
    from controller import Controller
    labels = {
        'core recovery document has unexplained edits': 'document-changed',
        'core recovery terminal not owned': 'terminal-not-owned',
        'core recovery directory mismatch': 'directory-mismatch',
        'core recovery foreign program': 'foreign-program',
        'core foreign or unsupported live program': 'unsupported-live-program',
        'owned shell has foreign live program': 'shell-program-mismatch',
        'core target changed after backup': 'target-changed',
        'core prior terminal creation requires recovery': 'prior-create',
        'session client already running': 'client-already-running',
        'native readiness or stop proof unavailable': 'readiness',
        'core recovery process changed before shell stop': 'process-changed',
        'core recovery document changed before shell stop': 'document-changed-before-stop',
    }
    try:
        with Store(ROOT) as store:
            Controller(store, Native(HOME, store)).restore()
    except Exception as error:
        label = labels.get(str(error), 'unclassified') if type(error).__name__ == 'NativeError' else 'controller'
        raise CommandFailure('core-recovery-' + label) from None
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
        protocol_labels = {
            'core protocol: core endpoint unsafe': 'core-endpoint-unsafe',
            'core protocol: core endpoint unavailable or outcome uncertain': 'core-endpoint-unavailable',
            'core protocol: core peer identity unavailable': 'core-peer-unavailable',
            'core protocol: core peer identity mismatch': 'core-peer-mismatch',
            'core protocol: core version or protocol incompatible': 'core-protocol-incompatible',
            'core protocol: core response refused or invalid': 'core-response-refused',
            'core protocol: core request outcome uncertain': 'core-outcome-uncertain',
            'core protocol: core structured response invalid': 'core-response-invalid',
        }
        if type(error).__name__ == 'NativeError' and str(error) in protocol_labels:
            suffix = '-' + protocol_labels[str(error)]
        print('F07: failed-' + STEP + suffix, file=sys.stderr)
        sys.exit(1)
