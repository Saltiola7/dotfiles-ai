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


def kept_spawn_diagnostics(backend):
    """Counts only, shared by failed preparation and explicit-stop recovery."""
    pending = [t for t in backend._terminals() if t.get('state') == 'live'
               and t.get('keep') is True and t.get('pid') is None]
    label = '-count-' + str(len(pending))
    manifest = backend.store.read('manifest.json') or {}
    addresses = set((manifest.get('receipt') or {}).get('terminals', {}).values())
    label += '-mapped-' + str(sum(t.get('address') in addresses for t in pending))
    try:
        probe = load('kept_probe', '/opt/f07/kept-probe.py')
        registry = probe.private_registry(HOME / '.local/state/herdr-core/default/terminals.json')
        classes = [probe.classify(registry, t['address'], int(time.time() * 1000))['classification']
                   for t in pending]
        for kind in ('claimed-pending', 'eligible-pending-noholder', 'backoff-pending-noholder',
                     'spawned', 'not-kept-live', 'record-missing', 'schema-unsupported'):
            count = classes.count(kind)
            if count:
                label += '-' + kind + '-' + str(count)
    except Exception:
        label += '-private-state-unavailable'
    for reason in ('server_stop', 'host_shutdown', 'holder_lost', 'stopped_by_restart', 'spawn_pending'):
        count = sum(t.get('reason') == reason for t in pending)
        if count:
            label += '-' + reason.replace('_', '-') + '-' + str(count)
    try:
        log = backend._read(HOME / '.local/state/herdr-core/default/core.log', 2 * 1024 * 1024).decode('utf-8')
        for name, prefix in (
                ('holder', 'core: kept terminals waiting for a holder:'),
                ('shell', 'core: kept terminals waiting for a shell:')):
            label += '-' + name + '-errors-' + str(sum(line.startswith(prefix) for line in log.splitlines()))
        for name, text in (('missing', 'No such file or directory'),
                           ('denied', 'Permission denied'), ('resource', 'Resource temporarily unavailable'),
                           ('panic', 'panicked at'), ('failed', 'failed')):
            label += '-' + name + '-' + str(log.count(text))
    except Exception:
        label += '-log-unavailable'
    return label


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
                if check.endswith('-spawn-pending'):
                    label += kept_spawn_diagnostics(backend)
            elif phase in {'restore_pending', 'verify_pending'} and journal.get('target') == 'herdr-core':
                # Inspect only after a failed CLI. No retries, stop or relaunch.
                check = 'receipt'
                refusals = {
                    'core terminal ownership mismatch': 'terminal-ownership',
                    'core terminal session or directory mismatch': 'terminal-identity',
                    'core terminal not live or spawn pending': 'terminal-pending',
                    'core foreign or unsupported live program': 'unsupported-program',
                    'owned shell has foreign live program': 'shell-program',
                    'target contains unowned live agent': 'unowned-agent',
                    'core client directory proof unavailable': 'client-directory',
                    'session client executable or identity unsupported': 'client-argv',
                    'session client server unsupported': 'client-server',
                    'owned shell PID unavailable': 'shell-pid',
                }
                refusals.update(r1_refusal_labels())
                try:
                    from native import panes
                    backend = Native(HOME, store)
                    if receipt is None:
                        raise RuntimeError()
                    label += '-mapped-' + str(len(receipt['terminals']))
                    check = 'other-runtime'
                    backend._other_off('herdr-core')
                    check = 'receipt-terminal-proof'
                    for pane in panes(journal['plan']):
                        address = receipt['terminals'].get(pane['key'])
                        if address is not None:
                            backend._match_terminal(backend._terminal(address), pane, journal['txid'])
                    check = 'live-terminal-inventory'
                    backend._safe_live_terminals(journal['plan'], receipt)
                    check = 'current-observations-pass'
                except Exception as error:
                    if type(error).__name__ == 'NativeError':
                        check += '-' + refusals.get(str(error), 'unclassified-native-refusal')
                label += '-' + check
        raise CommandFailure('controller-' + label) from None


def r1_refusal_labels():
    """Exact source refusals only; never interpolate native error payloads."""
    return {
        'core repair guard binding changed': 'repair-binding',
        'core repair guard labels changed': 'repair-labels',
        'core repair guard pid changed': 'repair-pid',
        'core repair guard start-time changed': 'repair-start-time',
        'core repair guard argv changed': 'repair-argv',
        'core repair guard directory changed': 'repair-directory',
        'core repair guard state changed': 'repair-state',
        'core repair guard exit unproven': 'repair-exit',
        'core repair guard session changed': 'repair-session',
        'core repair guard document-version changed': 'repair-document-version',
        'core repair guard layout changed': 'repair-layout',
        'core repair guard identity invalid': 'repair-identity-invalid',
    }


def wait(check, seconds=120):
    global STEP
    deadline = time.monotonic() + seconds
    failure = None
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except CommandFailure as error:
            failure = (STEP, error.reason)
        except Exception:
            pass  # Observations only; never retry native mutations.
        time.sleep(1)
    if failure is not None:
        STEP, reason = failure
        raise CommandFailure(reason) from None
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
    session_id = next(p['session_id'] for s in plan['spaces'] for t in s['tabs']
                      for p in t['panes'] if p['session_id'] is not None)
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


def semantic_difference(actual, expected):
    """Return only fixed schema labels, never names, paths or session IDs."""
    if len(actual) != len(expected):
        return 'space-count'
    def tree(left, right):
        if set(left) != set(right):
            return 'tree-shape'
        for key, label in (('cwd', 'pane-directory'), ('session_id', 'pane-session'),
                           ('axis', 'split-axis'), ('ratio', 'split-ratio')):
            if left.get(key) != right.get(key):
                return label
        if 'children' in left:
            if len(left['children']) != len(right['children']):
                return 'child-count'
            for a, b in zip(left['children'], right['children']):
                result = tree(a, b)
                if result:
                    return result
        return None
    for left, right in zip(actual, expected):
        if left['name'] != right['name']:
            return 'space-name'
        if left['directory'] != right['directory']:
            return 'space-directory'
        if len(left['tabs']) != len(right['tabs']):
            return 'tab-count'
        for a, b in zip(left['tabs'], right['tabs']):
            if a['name'] != b['name']:
                return 'tab-name'
            result = tree(a['root'], b['root'])
            if result:
                return result
    return None


def observe(target, plan):
    global STEP
    STEP = 'observe-' + target + '-manifest'
    Store, Native = adapter()
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        manifest = store.read('manifest.json')
        require(manifest is not None and manifest['runtime'] == target)
        difference = semantic_difference(backend._semantic(manifest['plan']), backend._semantic(plan))
        if difference:
            raise CommandFailure('manifest-' + difference)
        STEP = 'observe-' + target + '-verify'
        try:
            backend.verify(target, manifest['plan'], manifest['receipt'])
        except Exception as error:
            if type(error).__name__ == 'NativeError' and str(error) in r1_refusal_labels():
                raise CommandFailure(r1_refusal_labels()[str(error)]) from None
            labels = {
                'core current restored layout differs': 'current-layout',
                'core current restored bindings differ': 'current-bindings',
                'core current inventory changed': 'current-inventory',
                'core current process identity changed': 'current-process',
                'core controller stop requires reconciliation': 'controller-stop-incomplete',
                'core controller stop process proof unavailable': 'controller-stop-pids',
                'core repair stop outcome inconsistent': 'repair-stop-inconsistent',
                'core created binding proof unavailable': 'created-binding',
                'core recovery foreign live program': 'foreign-program',
                'core recovery directory mismatch': 'directory-mismatch',
                'core recovery terminal not owned': 'ownership',
                'core terminal not live or spawn pending': 'terminal-pending',
                'session client coverage incomplete or duplicate': 'client-coverage',
                'native client exit ownership uncertain': 'exit-ownership',
                'native observation or mutation uncertain': 'native-uncertain',
            }
            label = labels.get(str(error), 'unclassified') if type(error).__name__ == 'NativeError' else 'observation'
            STEP += '-' + label
            if manifest.get('txid'):
                retained = store.read('receipt-' + manifest['txid'] + '.json')
                if retained:
                    pending = retained.get('pending')
                    if isinstance(pending, dict):
                        operations = {'server.start': 'start', 'terminal.kill': 'kill',
                                      'terminal.run': 'run', 'doc.set': 'cas'}
                        STEP += '-pending-' + operations.get(pending.get('operation'), 'unknown')
                    if retained.get('repairs'):
                        STEP += '-repairs'
            raise CommandFailure('verify-' + label) from None
        STEP = 'observe-' + target + '-capture'
        capture = backend.capture(target)
        STEP = 'observe-' + target + '-capture-fidelity'
        require(backend._semantic(capture['plan']) == backend._semantic(plan))
        STEP = 'observe-' + target + '-client-coverage'
        clients = backend._coverage(plan)
        expected_sessions = {p['session_id'] for s in plan['spaces'] for t in s['tabs']
                              for p in t['panes'] if p['session_id'] is not None}
        STEP = 'observe-' + target + '-client-session-set'
        require({client['session_id'] for client in clients} == expected_sessions)
        STEP = 'observe-' + target + '-client-session-count'
        require(len(clients) == len(expected_sessions))
        f01 = load('f01', '/opt/f01/verify-user.py')
        STEP = 'observe-' + target + '-shared-backend-ready'
        _, server = f01.ready()
        port = urlsplit(server).port
        require(port is not None)
        for client in clients:
            STEP = 'observe-' + target + '-client-argv'
            backend._client_argv(client['pid'], client['session_id'])
            STEP = 'observe-' + target + '-client-executable'
            require((Path('/proc') / str(client['pid']) / 'exe').resolve() == NATIVE)
            # Exact argv and a stored session alone do not prove attachment.
            # Reuse F01's native socket-owner proof against the shared backend.
            STEP = 'observe-' + target + '-client-connected'
            wait(lambda: f01.connected(client['pid'], port), seconds=30)
        for space in plan['spaces']:
            for tab in space['tabs']:
                for pane in tab['panes']:
                    if pane['session_id'] is None:
                        continue
                    STEP = 'observe-' + target + '-session-api'
                    data = api('get', '/api/session/' + pane['session_id'])['data']
                    STEP = 'observe-' + target + '-session-api-identity'
                    require(data['id'] == pane['session_id'])
                    STEP = 'observe-' + target + '-session-api-directory'
                    require(data['location']['directory'] == pane['cwd'])
        if target == 'herdr-core':
            STEP = 'observe-herdr-core-tui-inactive'
            require(unit('show', 'remote-herdr-tui.service', '-p', 'ActiveState', '--value') == 'inactive')
            transient_owners(backend, clients)
        else:
            require(unit('is-active', 'remote-herdr-tui.service') == 'active')
        return capture


def transient_owners(backend, clients):
    global STEP
    # Upstream 3965a46 platform/systemd.rs owns all three unit families.
    STEP = 'observe-herdr-core-transient-unit-list'
    units = json.loads(unit('list-units', '--all', '--output=json', '--no-pager', 'hc-*.service'))
    names = [item['unit'] for item in units]
    for prefix in ('hc-serve-', 'hc-hold-', 'hc-shutdown-'):
        matches = [name for name in names if name.startswith(prefix)]
        STEP = 'observe-herdr-core-transient-unit-families'
        require(matches)
        for name in matches:
            STEP = 'observe-herdr-core-transient-unit-property'
            require(unit('show', name, '-p', 'Transient', '--value') == 'yes')
    for client in clients:
        STEP = 'observe-herdr-core-client-cgroup'
        cgroup = (Path('/proc') / str(client['pid']) / 'cgroup').read_text()
        require('hc-hold-' in cgroup and '.service' in cgroup)
    STEP = 'observe-herdr-core-no-persistent-units'
    require(not list((HOME / '.config/systemd/user').glob('hc-*.service')))
    STEP = 'observe-herdr-core-exclusive-endpoint'
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
    STEP = 'switch-' + target + '-exit-proof'
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


def retained_shell_switch(plan, pid):
    """Produce the old adapter failure through real controller writes, then recover.

    Only legacy label emission/comparison is injected in this disposable process.
    Native core normalizes labels; no receipt, journal or manifest is hand-edited.
    The subsequent recover command loads the installed, unmodified adapter.
    """
    global STEP
    STEP = 'retained-shell-switch'
    Store, Native = adapter()
    from controller import Controller, ControllerError
    from native import NativeError
    first_pane = plan['spaces'][0]['tabs'][0]['panes'][0]
    require(first_pane['session_id'] is None)
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        labels = backend._labels
        match = backend._match_terminal
        def legacy_labels(txid, pane):
            value = labels(txid, pane)
            value['remote-herdr-session'] = pane['session_id'] or ''
            return value
        def legacy_match(terminal, pane, txid):
            if terminal.get('labels') != legacy_labels(txid, pane):
                raise NativeError('core terminal ownership mismatch')
            return match(terminal, pane, txid)
        backend._labels = legacy_labels
        backend._match_terminal = legacy_match
        backend.poll_seconds = 1.0
        try:
            Controller(store, backend).switch('herdr-core', replace_target=True, imported=plan)
        except ControllerError:
            pass
        else:
            raise CommandFailure('legacy-shell-failure-not-observed')
        journal = store.read('transaction.json')
        require(journal['phase'] == 'restore_pending' and backend.selected() == 'herdr-core')
        receipt = store.read('receipt-' + journal['txid'] + '.json')
        require(receipt['pending'] is None and set(receipt['terminals']) == {first_pane['key']})
        require(store.read('manifest.json') is None and not backend.endpoint_present('tui'))
        require(not backend.scan({p['session_id'] for s in plan['spaces'] for t in s['tabs']
                                  for p in t['panes'] if p['session_id']}))
        retained = receipt['terminals'][first_pane['key']]
        terminal = backend._terminal(retained)
        require(terminal['labels'] == {'remote-herdr-owner': journal['txid'],
                                       'remote-herdr-pane': first_pane['key']})
        wait(lambda: backend._shell_proof(backend._terminal(retained)) or True)
        addresses = {t['address'] for t in backend._terminals()}
        backup = receipt['backup']
    require(backend_pid() == pid)
    refusal = subprocess.run([str(BIN / 'remote-herdr'), 'restore'], cwd=HOME,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    require(refusal.returncode == 75)
    STEP = 'retained-shell-recover'
    cli('recover')
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        require(store.read('transaction.json')['phase'] == 'complete')
        manifest = store.read('manifest.json')
        require(manifest['receipt']['terminals'][first_pane['key']] == retained)
        require(store.read(backup) is not None)
        require(len({t['address'] for t in backend._terminals()} - addresses) == 3)
    observe('herdr-core', plan)
    require(backend_pid() == pid)
    print('F07: retained-shell-label-recovery-complete')


def expected_leaf_rebind(document, leaf, old, new):
    """Independent raw-tree expectation: change one scalar, preserve opaque data."""
    import copy
    expected = copy.deepcopy(document)
    matches = []
    def walk(node):
        if isinstance(node, dict):
            if node.get('id') == leaf and node.get('type') == 'block':
                require(node['content']['terminal'] == old)
                matches.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(expected)
    require(len(matches) == 1)
    matches[0]['content']['terminal'] = new
    return expected


def app_compatible_document(document):
    """Fixture-authored native app document, NOT actual Desktop UI producer evidence.

    Reuse tab IDs only across kinds; retain every original node, split and opaque
    field. The fixture's three current tabs need no new sessions or DB seeding.
    """
    import copy
    result = copy.deepcopy(document)
    tabs = [tab for space in result['spaces'] for tab in space['tabs']]
    require(len(tabs) == 3)
    node_ids = set()
    def walk(node):
        require(node['id'] not in node_ids)
        node_ids.add(node['id'])
        for child in node.get('children', []):
            walk(child)
    for tab in tabs:
        walk(tab['root'])
    require(len({tab['id'] for tab in tabs}) == 3)
    for tab in tabs:
        root = tab['root']
        if root['id'] == tab['id'] and root['type'] == 'row':
            require(len(root['children']) == 1)
            continue
        require(tab['id'] not in node_ids)
        tab['root'] = {'id': tab['id'], 'type': 'row', 'children': [root]}
        node_ids.add(tab['id'])
    return result


def native_app_labels(backend, address, *, changed=False):
    """Fixture-only public terminal.label; never extend production RPC authority.

    Provenance: herdrdev/herdr-core 3965a46caae095a3ead01de237fa13955e52b8c6,
    schema/hc.openrpc.json terminal.label: labels object<string>, terminal string,
    result Terminal. This simulates an app's labels on REAL core records, not a
    terminal.get overlay and not actual Desktop UI producer evidence.
    """
    global STEP
    import layout
    import protocol
    STEP = 'app-label-local-address'
    require(layout._TERMINAL.fullmatch(address) is not None)
    before = backend._terminal(address)
    labels = {'where': 'fixture app changed' if changed else 'fixture app',
              'herdr.seen': '2' if changed else '1',
              'herdr.space': 'fixture-space', 'herdr.tab': 'fixture-tab'}
    STEP = 'app-label-owned-endpoint'
    endpoint = backend._core_endpoint()
    # The adapter proves the existing endpoint and native version first. This
    # isolated transport sends ONLY hello and the pinned public label operation.
    require(backend.endpoint_present('herdr-core'))
    for parent in (endpoint.parent, *endpoint.parent.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0, os.getuid()}
                and (not info.st_mode & 0o022 or info.st_mode & stat.S_ISVTX))
    info = endpoint.lstat()
    require(stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o022)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
        peer.settimeout(30)
        peer.connect(str(endpoint))
        _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require(uid == os.getuid())
        pending = b''
        # Not a generic RPC helper: both messages and parameters are fixed here.
        for number, method, params in (
                (1, 'hello', {'framed': False}),
                (2, 'terminal.label', {'terminal': address, 'labels': labels})):
            outgoing = json.dumps({'jsonrpc': '2.0', 'id': number, 'method': method,
                                   'params': params}, allow_nan=False).encode() + b'\n'
            require(len(outgoing) <= protocol.MAX_MESSAGE)
            peer.sendall(outgoing)
            while b'\n' not in pending:
                part = peer.recv(min(65536, protocol.MAX_MESSAGE + 1 - len(pending)))
                require(bool(part))
                pending += part
                require(len(pending) <= protocol.MAX_MESSAGE)
            raw, pending = pending.split(b'\n', 1)
            answer = protocol.decode(raw)
            require(answer.get('jsonrpc') == '2.0' and type(answer.get('id')) is int
                    and answer['id'] == number and 'error' not in answer
                    and isinstance(answer.get('result'), dict))
            result = answer['result']
            if number == 1:
                STEP = 'app-label-protocol-version'
                require(result.get('version') == '0.1.18' and type(result.get('generation')) is int
                        and result['generation'] == 1 and result.get('framed') is False
                        and isinstance(result.get('methods'), list)
                        and 'terminal.label' in result['methods'])
            else:
                STEP = 'app-label-response-address'
                require(result['address'] == address)
    STEP = 'app-label-preserved-ownership'
    actual = backend._terminal(address)
    require(actual['labels'] == dict(before.get('labels', {}), **labels))
    return actual['labels']


def adopt_app_compatibility(plan):
    """Real native CAS and label effects; installed restore adopts without churn."""
    global STEP
    STEP = 'app-adoption-read-current'
    Store, Native = adapter()
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        manifest = store.read('manifest.json')
        clients = backend._coverage(plan)
        document, version = backend._document()
        STEP = 'app-adoption-three-tab-shape'
        document = app_compatible_document(document)
        labels = {address: native_app_labels(backend, address)
                  for address in manifest['receipt']['terminals'].values()}
        STEP = 'app-adoption-document-cas'
        backend.core('doc.set', {'name': 'herdr-app', 'value': document, 'version': version})
        baseline, _ = backend._document()
        addresses = {t['address'] for t in backend._terminals()}
    STEP = 'app-adoption-installed-restore'
    cli('restore')
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        STEP = 'app-adoption-raw-document'
        require(backend._document()[0] == baseline)
        STEP = 'app-adoption-client-identities'
        require(backend._coverage(plan) == clients)
        STEP = 'app-adoption-terminal-inventory'
        require({t['address'] for t in backend._terminals()} == addresses)
        STEP = 'app-adoption-terminal-labels'
        require(all(backend._terminal(address)['labels'] == value for address, value in labels.items()))


def finished_terminal_facts(terminal):
    # Public status/seen/title reports can still change after exit. Only stable
    # native completion and identity facts belong in the lost-reply assertion.
    return {key: terminal[key] for key in (
        'address', 'pid', 'labels', 'argv', 'cwd', 'state', 'finished_ms',
        'reason', 'exit_code', 'exitcode') if key in terminal}


def fresh_app_leaf_ids():
    """Public app CAS prevents old canonical pane history aliasing legacy labels."""
    Store, Native = adapter()
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        document, version = backend._document()
        def walk(node):
            if node['type'] == 'block':
                node['id'] = 'fixture-app-' + uuid.uuid4().hex
            for child in node.get('children', []):
                walk(child)
        for space in document['spaces']:
            for tab in space['tabs']:
                walk(tab['root'])
        backend.core('doc.set', {'name': 'herdr-app', 'value': document, 'version': version})
    cli('restore')


def legacy_repair_projection(original_projection, backend):
    """Small OLD admission serializer, before the original receipt writer only.

    Old releases had neither per-create generation labels nor source snapshots.
    Actual projection, identity guards, native effects and persistence stay native.
    """
    def project(*args):
        projected, bindings, labels, repairs = original_projection(*args)
        for leaf, repair in repairs.items():
            repair.pop('create_id', None)
            repair.pop('source', None)
            repair['labels'] = backend._labels(args[3]['txid'], {
                'key': leaf, 'session_id': repair['pane']['session_id']})
        return projected, bindings, labels, repairs
    return project


def fixture_references(document):
    """Independent leaf-only reader; never project through production layout."""
    references = {}
    def walk(node):
        if node['type'] == 'block':
            require(node['id'] not in references)
            references[node['id']] = node['content']['terminal']
        for child in node.get('children', []):
            walk(child)
    for space in document['spaces']:
        for tab in space['tabs']:
            walk(tab['root'])
    return references


def fixture_prune_finished(document, owned, finished):
    """App-like leaf removal, preserving opaque fields, IDs and remaining weights."""
    import copy
    result = copy.deepcopy(document)
    def prune(node):
        if node['type'] == 'block':
            return None if node['id'] in owned and node['content']['terminal'] in finished else node
        node['children'] = [kept for child in node['children']
                            if (kept := prune(child)) is not None]
        return node if node['children'] else None
    for space in result['spaces']:
        tabs = []
        for tab in space['tabs']:
            root = prune(tab['root'])
            if root is not None:
                tab['root'] = root
                tabs.append(tab)
        space['tabs'] = tabs
    result['spaces'] = [space for space in result['spaces'] if space['tabs']]
    return result


class FixtureAppClient:
    """Concurrent fixture protocol client, NOT the actual Desktop GUI.

    Only terminal.list/doc.get/doc.set via a dedicated Native.core are used.
    Baseline finished records are history, not events. Uncertain CAS/transport
    outcomes fail qualification: there is deliberately no mutation retry.
    """
    def __init__(self, core, owned):
        self.core = core
        self.owned = set(owned)
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self.failure = False
        self.events = {}
        self.live_seen = set()
        self.thread = threading.Thread(target=self._observe, daemon=True)

    def _states(self):
        result = self.core('terminal.list', {'all': True})['terminals']
        require(type(result) is list and len(result) <= 512)
        states = {t['address']: t['state'] for t in result}
        require(len(states) == len(result))
        return states

    def _observe(self):
        try:
            prior = self._states()
            with self.lock:
                self.live_seen.update(a for a, state in prior.items() if state == 'live')
            self.ready.set()
            pending = set()
            while not self.stop.wait(0.02):
                current = self._states()
                with self.lock:
                    self.live_seen.update(a for a, state in current.items() if state == 'live')
                pending.update(a for a, state in current.items()
                               if state == 'finished' and prior.get(a) == 'live')
                prior = current
                if not pending or not self.release.is_set():
                    continue
                answer = self.core('doc.get', {'name': 'herdr-app'})
                document, version = answer['value'], answer['version']
                require(type(version) is int and version > 0)
                with self.lock:
                    owned = set(self.owned)
                references = fixture_references(document)
                updated = fixture_prune_finished(document, owned, pending)
                if updated != document:
                    # One observed-version CAS. Even a refused CAS is not blindly
                    # replayed: the worker reports only a fixed failure label.
                    result = self.core('doc.set', {'name': 'herdr-app', 'value': updated,
                                                   'version': version})
                    require(type(result['version']) is int and result['version'] > version)
                with self.lock:
                    for address in pending:
                        self.events[address] = (references, {a for a, s in current.items() if s == 'live'})
                pending.clear()
        except Exception:
            # No unexpected error is swallowed, and no peer payload is printed.
            self.failure = True
            self.ready.set()

    def check(self):
        if self.failure:
            raise CommandFailure('app-client-observation-or-cas-failed')

    def seen(self, addresses):
        self.check()
        with self.lock:
            return addresses <= self.events.keys()

    def observed_live(self, address):
        self.check()
        with self.lock:
            return address in self.live_seen

    def __enter__(self):
        self.thread.start()
        try:
            require(self.ready.wait(30))
            self.check()
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join(35)
        if self.thread.is_alive():
            raise CommandFailure('app-client-join-deadline')
        self.check()


def fixture_idle_agents(backend, plan, keys, pid):
    """Signal only exact proven fixture UIs; native keep must supply actual Bash."""
    from native import panes
    manifest = backend.store.read('manifest.json')
    clients = backend._coverage(plan)
    proofs = {}
    for pane in panes(plan):
        key = pane['key']
        if key not in keys:
            continue
        client = next(c for c in clients if c['session_id'] == pane['session_id'])
        address = manifest['receipt']['terminals'][key]
        terminal = backend._terminal(address)
        require(terminal['keep'] is True and client['pid'] != pid)
        require((terminal.get('foreground') or terminal)['pid'] == client['pid'])
        require(backend._actual_core_program(terminal) == (pane['session_id'], pane['cwd']))
        backend._client_argv(client['pid'], pane['session_id'])
        require((Path('/proc') / str(client['pid']) / 'exe').resolve() == NATIVE)
        require(backend.process_cwd(client['pid']) == pane['cwd'])
        old = backend._pid_proofs([client['pid']])
        fd = os.pidfd_open(client['pid'])
        try:
            require(backend._pid_proofs([client['pid']]) == old)
            backend._client_argv(client['pid'], pane['session_id'])
            require((Path('/proc') / str(client['pid']) / 'exe').resolve() == NATIVE)
            require(backend.process_cwd(client['pid']) == pane['cwd'])
            signal.pidfd_send_signal(fd, signal.SIGKILL)
        finally:
            os.close(fd)
        def idle():
            current = backend._terminal(address)
            if not backend._pids_absent(old):
                return False
            if backend._actual_core_program(current) != (None, pane['cwd']):
                return False
            backend._shell_proof(current)
            return current
        shell = wait(idle)
        proofs[key] = {'client': old, 'shell': backend._pid_proofs([
            shell['pid'], (shell.get('foreground') or shell)['pid']])}
    require(set(proofs) == set(keys) and backend_pid() == pid)
    return proofs


def fixture_before_repair_kill(backend, baseline, leaf, source, pane, pids, txid, key):
    """Fixture-only synchronous ordering oracle, NOT actual Desktop GUI evidence.

    Read raw native facts and original durable intent immediately before forwarding
    kill. Never call the production rebound guard, mutate, retry, or reorder work.
    The polling app client alone establishes pruning, NOT mutation ordering.
    """
    old = source['address']
    document, version = backend._document()
    new = fixture_references(document).get(leaf)
    if new is None or new == old:
        raise CommandFailure('app-ordering-old-still-referenced')
    require(document == expected_leaf_rebind(baseline, leaf, old, new))
    receipt = backend.store.read('receipt-' + txid + '.json')
    pending = receipt['pending']
    repair = receipt['repairs'][leaf]
    require(pending['operation'] == 'terminal.kill' and pending['terminal'] == old
            and pending['leaf'] == leaf and pending['pane'] == key)
    require(receipt['bindings'][key] == leaf and receipt['terminals'][key] == old
            and repair['terminal'] == old and repair['created'] == new and repair['pane'] == pane)
    require(receipt['document'] == baseline and pending['rebound']['document'] == document
            and pending['rebound']['version'] == version and version > receipt['doc_version'])
    require(re.fullmatch(r'[0-9a-f]{32}', repair['create_id']) is not None)
    expected_labels = {'remote-herdr-owner': txid, 'remote-herdr-pane': leaf,
        'remote-herdr-session': pane['session_id'], 'remote-herdr-repair': repair['create_id']}
    require(repair['labels'] == expected_labels)
    def ownership(terminal):
        return {k: v for k, v in terminal['labels'].items() if k.startswith('remote-herdr-')}
    def identity(terminal):
        foreground = (terminal.get('foreground') or terminal)['pid']
        return {'pid': terminal['pid'], 'foreground_pid': foreground,
            'argv': backend.process_argv(foreground), 'cwd': backend.process_cwd(foreground),
            'launch': {k: terminal.get(k) for k in ('argv', 'cwd', 'keep')}}
    original = backend._terminal(old)
    require(original['state'] == 'live' and ownership(original) == ownership(source))
    require(all(original.get(k) == source.get(k) for k in ('pid', 'argv', 'cwd', 'keep')))
    require((original.get('foreground') or original)['pid'] == (source.get('foreground') or source)['pid'])
    require(backend._actual_core_program(original) == (None, pane['cwd']))
    require(backend._pid_proofs([p['pid'] for p in pids]) == pids)
    require(pending['pids'] == repair['pids'] == pids)
    require(pending['identity'] == repair['source'] == identity(original))
    replacement = backend._terminal(new)
    require(replacement['state'] == 'live' and ownership(replacement) == expected_labels)
    require(backend._actual_core_program(replacement) == (pane['session_id'], pane['cwd']))
    replacement_pids = backend._pid_proofs([
        replacement['pid'], (replacement.get('foreground') or replacement)['pid']])
    replacement_proof = {'identity': identity(replacement), 'pids': replacement_pids}
    require(pending['rebound']['replacement'] == replacement_proof)
    clients = backend.scan({pane['session_id']})
    require(len(clients) == 1 and clients[0]['pid'] == replacement_proof['identity']['foreground_pid'])
    # Recheck across observation boundaries, without claiming cross-RPC atomicity.
    require(backend._document() == (document, version))
    require(backend._pid_proofs([p['pid'] for p in pids]) == pids)
    require(backend._pid_proofs([p['pid'] for p in replacement_pids]) == replacement_pids)
    final_old, final_new = backend._terminal(old), backend._terminal(new)
    require(final_old['state'] == final_new['state'] == 'live')
    require(ownership(final_old) == ownership(source) and ownership(final_new) == expected_labels)
    require(backend._actual_core_program(final_old) == (None, pane['cwd']))
    require(backend._actual_core_program(final_new) == (pane['session_id'], pane['cwd']))
    require(identity(final_old) == pending['identity'])
    require(identity(final_new) == replacement_proof['identity'])
    require(backend.scan({pane['session_id']}) == clients)
    require(backend._document() == (document, version))
    return new


def fixture_app_canary(backend, app):
    """Positive control: a real Bash finish must cause a real native pane CAS."""
    import copy
    import layout
    document, version = backend._document()
    canary = backend.core('terminal.run', {'argv': ['/bin/bash', '-l'],
        'cwd': str(HOME), 'keep': True, 'no_parent': True, 'no_notify': True, 'wait': False})
    address = canary['address']
    require(layout._TERMINAL.fullmatch(address) is not None)
    def ready():
        terminal = backend._terminal(address)
        if backend._actual_core_program(terminal) != (None, str(HOME)):
            return False
        backend._shell_proof(terminal)
        return terminal
    terminal = wait(ready)
    proof = backend._pid_proofs([terminal['pid'], (terminal.get('foreground') or terminal)['pid']])
    leaf = 'fixture-canary-' + uuid.uuid4().hex
    updated = copy.deepcopy(document)
    updated['spaces'][0]['tabs'].append({'id': 'canary-tab-' + uuid.uuid4().hex,
        'name': 'Fixture event control', 'root': {'id': leaf, 'type': 'block',
                                               'content': {'terminal': address}}})
    with app.lock:
        app.owned.add(leaf)
    backend.core('doc.set', {'name': 'herdr-app', 'value': updated, 'version': version})
    # Ensure a newly observed live record precedes its finish (not snapshot prune).
    wait(lambda: app.observed_live(address), seconds=30)
    backend._shell_proof(backend._terminal(address))
    require(backend._pid_proofs([p['pid'] for p in proof]) == proof)
    # Negative control: the very same pre-forward oracle must reject kill-first,
    # before consulting R3 intent. Only this explicit canary bypasses that refusal.
    try:
        fixture_before_repair_kill(backend, updated, leaf, terminal,
            {'key': leaf, 'cwd': str(HOME), 'session_id': None}, proof, 'canary', leaf)
    except CommandFailure as error:
        require(error.reason == 'app-ordering-old-still-referenced')
    else:
        raise CommandFailure('app-ordering-negative-control-missed')
    backend.core('terminal.kill', {'terminal': address})
    wait(lambda: app.seen({address}), seconds=30)
    require(backend._pids_absent(proof) and backend._document()[0] == document)
    with app.lock:
        require(app.events[address][0].get(leaf) == address)


def app_connected_repair(plan, pid):
    """Installed Native/Controller with fixture-only pre-forward kill observation.

    Production restore owns all ordering and native effects. This synchronous
    read-only observer can refuse a bad order, never fix it or retry a mutation.
    CLI restore/recover subsequently prove uninstrumented idempotence.
    """
    global STEP
    from controller import Controller
    from native import panes
    Store, Native = adapter()
    STEP = 'app-connected-repair-admission'
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        pane = next(p for p in panes(plan) if p['session_id'] is not None)
        key = pane['key']
        before = backend._coverage(plan)
        other = [c for c in before if c['session_id'] != pane['session_id']]
        other_proofs = backend._pid_proofs([c['pid'] for c in other])
        proofs = fixture_idle_agents(backend, plan, {key}, pid)
        manifest = store.read('manifest.json')
        old = manifest['receipt']['terminals'][key]
        leaf = manifest['receipt']['bindings'][key]
        source = backend._terminal(old)
        baseline, _ = backend._document()
        app = FixtureAppClient(Native(HOME, store).core, fixture_references(baseline))
        app.__enter__()
        try:
            fixture_app_canary(backend, app)
            addresses = {t['address'] for t in backend._terminals()}
            original_core = backend.core
            forwarded = 0
            def observed_core(method, params):
                nonlocal forwarded
                if method == 'terminal.kill':
                    require(params == {'terminal': old} and forwarded == 0)
                    fixture_before_repair_kill(backend, baseline, leaf, source, pane,
                        proofs[key]['shell'], manifest['txid'], key)
                    forwarded += 1
                return original_core(method, params)
            STEP = 'app-connected-observed-controller-restore'
            backend.core = observed_core
            try:
                Controller(store, backend).restore()
                require(forwarded == 1)
            finally:
                backend.core = original_core
        except BaseException:
            app.__exit__()
            raise
    try:
        STEP = 'app-connected-post-restore-observation'
        wait(lambda: app.seen({old}), seconds=30)
        with Store(ROOT) as store:
            backend = Native(HOME, store)
            receipt = store.read('manifest.json')['receipt']
            new = receipt['terminals'][key]
            require(new != old and receipt['bindings'][key] == leaf)
            expected = expected_leaf_rebind(baseline, leaf, old, new)
            require(backend._document()[0] == expected)
            require(receipt['pending'] is None and receipt['repairs'] == {})
            require({t['address'] for t in backend._terminals()} - addresses == {new})
            require(backend._actual_core_program(backend._terminal(new)) == (pane['session_id'], pane['cwd']))
            require(re.fullmatch(r'[0-9a-f]{32}', backend._terminal(new)['labels']['remote-herdr-repair']) is not None)
            require(backend._pids_absent(proofs[key]['client']) and backend._pids_absent(proofs[key]['shell']))
            require([c for c in backend._coverage(plan) if c['session_id'] != pane['session_id']] == other)
            require(backend._pid_proofs([c['pid'] for c in other]) == other_proofs)
            with app.lock:
                refs, live = app.events[old]
                require(refs.get(leaf) == new and old not in refs.values() and new in live)
            final = {t['address'] for t in backend._terminals()}
        cli('restore')
        cli('recover')
        with Store(ROOT) as store:
            backend = Native(HOME, store)
            require(backend._document()[0] == expected)
            require({t['address'] for t in backend._terminals()} == final)
    finally:
        app.__exit__()
    observe('herdr-core', plan)
    require(backend_pid() == pid)
    print('F07: app-connected-repair-ordering-complete')


def legacy_mixed_admission(backend, plan, selected, *, before_last):
    """Bounded OLD serializer/kill-first fault adapter; original writers only.

    Admit all repairs from real projection, stop/create the first two with native
    guards and RPC, then persist the third run intent without executing that run.
    No clean receipt, journal or manifest is fabricated after publication.
    """
    import copy
    manifest = backend.store.read('manifest.json')
    receipt = copy.deepcopy(manifest['receipt'])
    document, version = backend._document()
    project = legacy_repair_projection(backend._current_projection, backend)
    projected, bindings, labels, repairs = project(document, backend._terminals(), plan, receipt)
    receipt.update(current_document=True, plan=projected, document=document, doc_version=version,
        terminals={k: b['terminal'] for k, b in bindings.items()},
        bindings={k: b['leaf'] for k, b in bindings.items()},
        labels={k: labels[b['leaf']] for k, b in bindings.items()}, repairs=repairs)
    original_receipt = backend._receipt
    original_receipt(receipt)
    for index, key in enumerate(selected):
        leaf = receipt['bindings'][key]
        repair = receipt['repairs'][leaf]
        require('create_id' not in repair and 'source' not in repair)
        if index == 2:
            before_last()
        terminal = backend._terminal(repair['terminal'])
        backend._shell_proof(terminal)
        repair['pids'] = backend._pid_proofs([terminal['pid'], (terminal.get('foreground') or terminal)['pid']])
        receipt['pending'] = {'operation': 'terminal.kill', 'pane': key, 'leaf': leaf,
            'terminal': repair['terminal'], 'pids': repair['pids'], 'identity': backend._kill_identity(terminal)}
        original_receipt(receipt)
        backend._complete_current_kill(receipt)  # Real stop and independent exit proof.
        receipt['pending'] = {'operation': 'terminal.run', 'pane': key, 'leaf': leaf,
                              'labels': repair['labels']}
        original_receipt(receipt)
        if index == 2:
            return receipt  # Real pre-run interruption, no third RPC was sent.
        pane = repair['pane']
        result = backend.core('terminal.run', {'argv': [str(BIN / 'opencode'), '--session', pane['session_id']],
            'cwd': pane['cwd'], 'labels': repair['labels'], 'keep': True,
            'no_parent': True, 'no_notify': True, 'wait': False})
        import layout
        require(layout._TERMINAL.fullmatch(result['address']) is not None)
        require(backend._same_labels(result.get('labels'), repair['labels']))
        repair['created'] = result['address']
        original_receipt(receipt)
        backend._wait_created_core(repair['created'], pane, repair['labels'])
        backend._replacement_proof(repair)
        receipt['pending'] = None
        original_receipt(receipt)
    raise CommandFailure('app-legacy-fault-admission-missing')


def app_closed_pending_run_recovery(plan, pid):
    """Real complete journal + mixed old receipts, delayed finish event and recover."""
    global STEP
    import copy
    from native import panes
    Store, Native = adapter()
    STEP = 'app-closed-pending-run-fresh-leaves'
    fresh_app_leaf_ids()
    values = list(panes(plan))
    require(len(values) == 5 and len(plan['spaces']) == 2)
    # Original alpha, first later view, beta sole leaf; later views 1/2 stay idle.
    selected = [plan['spaces'][0]['tabs'][0]['panes'][0]['key'],
                plan['spaces'][0]['tabs'][1]['panes'][0]['key'],
                plan['spaces'][1]['tabs'][0]['panes'][0]['key']]
    expected_plan = copy.deepcopy(plan)
    expected_plan['spaces'].pop()  # No canonical key renumbering: final space only.
    app = None
    try:
        with Store(ROOT) as store:
            backend = Native(HOME, store)
            journal = copy.deepcopy(store.read('transaction.json'))
            require(journal['phase'] == 'complete')
            manifest = store.read('manifest.json')
            require(manifest['txid'] == journal['txid'])
            txid = manifest['txid']
            proofs = fixture_idle_agents(backend, plan, {p['key'] for p in values}, pid)
            baseline, _ = backend._document()
            old_receipt = manifest['receipt']
            old = dict(old_receipt['terminals'])
            leaves = dict(old_receipt['bindings'])
            closed_key = selected[2]
            closed_leaf, closed_address = leaves[closed_key], old[closed_key]
            closed_session = next(p['session_id'] for p in values if p['key'] == closed_key)
            def before_last():
                nonlocal app
                # Initial finished records are excluded from this event observer.
                app = FixtureAppClient(Native(HOME, store).core, fixture_references(baseline))
                app.release.clear()  # Delayed app event, not a controller lock.
                app.__enter__()
                require(app.observed_live(closed_address))
            STEP = 'app-closed-pending-run-old-admission'
            admitted = legacy_mixed_admission(backend, plan, selected, before_last=before_last)
            pending = copy.deepcopy(admitted['pending'])
            require(pending['operation'] == 'terminal.run' and pending['leaf'] == closed_leaf)
            require(admitted['repairs'][closed_leaf]['created'] is None)
            saved = copy.deepcopy(store.read('receipt-' + txid + '.json'))
            require(saved == admitted and store.read('transaction.json') == journal)
            created = {key: saved['repairs'][leaves[key]]['created'] for key in selected[:2]}
            require(all(created.values()) and len(set(created.values())) == 2)
            for key in selected:
                require(backend._terminal(old[key])['state'] == 'finished')
                require(backend._pids_absent(proofs[key]['shell']))
            # Include finished records: zero matches is a real native observation,
            # not a terminal.get overlay or an unexecuted fake process record.
            require(not any(backend._same_labels(t.get('labels'), pending['labels'])
                            for t in backend._terminals()))
            require(not backend._repair_candidates(backend._terminals(), saved['repairs'][closed_leaf]))
            require(not backend.scan({closed_session}))
            addresses = {t['address'] for t in backend._terminals()}
            other_clients = backend.scan({p['session_id'] for p in values
                                          if p['key'] in selected[:2]})
            require(len(other_clients) == 2)
            other_proofs = backend._pid_proofs([c['pid'] for c in other_clients])
        if app is None:
            raise CommandFailure('app-client-not-started')
        active_app = app
        STEP = 'app-closed-pending-run-delayed-event'
        app.release.set()
        wait(lambda: active_app.seen({closed_address}), seconds=30)
        expected_document = fixture_prune_finished(baseline, {closed_leaf}, {closed_address})
        with Store(ROOT) as store:
            backend = Native(HOME, store)
            require(backend._document()[0] == expected_document)
            require(closed_leaf not in fixture_references(expected_document))
            require(store.read('receipt-' + txid + '.json') == saved)
            require(store.read('transaction.json') == journal)
            require(not any(backend._same_labels(t.get('labels'), pending['labels'])
                            for t in backend._terminals()))
        STEP = 'app-closed-pending-run-installed-recover'
        cli('recover')  # Complete journal must dispatch current-document restore.
        remaining_old = {old[p['key']] for p in values if p['key'] not in selected}
        wait(lambda: active_app.seen(remaining_old), seconds=30)
        with Store(ROOT) as store:
            backend = Native(HOME, store)
            require(store.read('transaction.json') == journal)
            manifest = store.read('manifest.json')
            receipt = manifest['receipt']
            require(manifest['txid'] == txid and manifest['plan'] == expected_plan)
            require(receipt['pending'] is None and receipt['repairs'] == {})
            require(backend._pid_proofs([c['pid'] for c in other_clients]) == other_proofs)
            require(backend.scan({c['session_id'] for c in other_clients}) == other_clients)
            for pane in panes(expected_plan):
                key = pane['key']
                replacement = receipt['terminals'][key]
                if key in created:
                    require(replacement == created[key])  # Existing unbound client reused.
                expected_document = expected_leaf_rebind(expected_document, leaves[key], old[key], replacement)
                require(backend._actual_core_program(backend._terminal(replacement)) == (pane['session_id'], pane['cwd']))
                if key not in selected:
                    with app.lock:
                        refs, live = app.events[old[key]]
                        require(refs.get(leaves[key]) == replacement and replacement in live)
                        # Earlier unbound creations were rebound before any new kill.
                        require(all(refs.get(leaves[k]) == v and v in live for k, v in created.items()))
            require(backend._document()[0] == expected_document)
            require(len({t['address'] for t in backend._terminals()} - addresses) == 2)
            for key, proof in proofs.items():
                require(backend._terminal(old[key])['state'] == 'finished')
                require(backend._pids_absent(proof['client']) and backend._pids_absent(proof['shell']))
            require(not backend.scan({closed_session}))
            require(closed_key not in receipt['terminals'])
            require(not any(backend._same_labels(t.get('labels'), pending['labels'])
                            for t in backend._terminals()))
            coverage = backend._coverage(expected_plan)
            final = {t['address'] for t in backend._terminals()}
        cli('restore')
        cli('recover')
        with Store(ROOT) as store:
            backend = Native(HOME, store)
            require(backend._document()[0] == expected_document)
            require({t['address'] for t in backend._terminals()} == final)
            require(backend._coverage(expected_plan) == coverage)
            require(not backend.scan({closed_session}))
    finally:
        if app is not None:
            app.__exit__()
    observe('herdr-core', expected_plan)
    require(backend_pid() == pid)
    write(EXPECTED, expected_plan)
    print('F07: app-closed-pending-run-recovery-complete')
    return expected_plan


def kept_shell_kill_recovery(plan, pid, *, lost_reply):
    """Two serial real-kept-Bash faults; installed restore owns all recovery.

    The first hook emulates the OLD serializer before its original private
    writer runs, then its whole-record comparison after durable publication.
    It is not a runtime hook installed in the CLI. Neither case writes a Store
    document outside the adapter's original writer or manufactures a capture.
    """
    global STEP
    import copy
    from controller import Controller, ControllerError
    from native import NativeError, panes
    require(os.getuid() == 1000 and Path.home() == HOME)
    Store, Native = adapter()
    adopt_app_compatibility(plan)
    fresh_app_leaf_ids()
    STEP = 'kept-shell-client-loss'
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        manifest = store.read('manifest.json')
        require(manifest['runtime'] == 'herdr-core' and manifest['plan'] == plan)
        txid = manifest['txid']
        pane = next(p for p in panes(manifest['plan']) if p['session_id'] is not None)
        key = pane['key']
        leaf = manifest['receipt']['bindings'][key]
        address = manifest['receipt']['terminals'][key]
        before = backend.capture('herdr-core')
        clients = backend._coverage(plan)
        client = next(c for c in clients if c['session_id'] == pane['session_id'])
        other_clients = [c for c in clients if c['session_id'] != pane['session_id']]
        client_pid = client['pid']
        terminal = backend._terminal(address)
        require(terminal.get('keep') is True)
        require((terminal.get('foreground') or terminal)['pid'] == client_pid)
        require(backend._actual_core_program(terminal) == (pane['session_id'], pane['cwd']))
        backend._client_argv(client_pid, pane['session_id'])
        require((Path('/proc') / str(client_pid) / 'exe').resolve() == NATIVE)
        require(backend.process_cwd(client_pid) == pane['cwd'] and client_pid != pid)
        client_proof = backend._pid_proofs([client_pid])  # Includes same-user/start-time proof.
        require(backend_pid() == pid)
        fd = os.pidfd_open(client_pid)
        try:
            require(backend._pid_proofs([client_pid]) == client_proof)
            backend._client_argv(client_pid, pane['session_id'])
            require((Path('/proc') / str(client_pid) / 'exe').resolve() == NATIVE)
            require(backend.process_cwd(client_pid) == pane['cwd'])
            # A UI can handle TERM and exit normally, which core correctly
            # treats as final. Force only this proven fixture client's signal
            # loss: pinned core keep replaces signaled programs with its shell.
            signal.pidfd_send_signal(fd, signal.SIGKILL)
        finally:
            os.close(fd)
        STEP = 'kept-shell-native-idle-bash'
        def kept_ready():
            current = backend._terminal(address)
            if not backend._pids_absent(client_proof):
                return False
            if backend._actual_core_program(current) != (None, pane['cwd']):
                return False
            backend._shell_proof(current)
            return current
        shell = wait(kept_ready)
        shell_pids = backend._pid_proofs([shell['pid'], (shell.get('foreground') or shell)['pid']])
        require(backend_pid() == pid)
        # Read the latest native document after keep's real UI reporting. The
        # admitted adapter restore must retain exactly this raw view/version.
        baseline, _ = backend._document()
        addresses = {t['address'] for t in backend._terminals()}
        original_core = backend.core
        original_receipt = backend._receipt
        backend._current_projection = legacy_repair_projection(backend._current_projection, backend)
        kills = 0
        churned = False
        def fault_core(method, params):
            nonlocal kills
            if method == 'terminal.kill':
                require(lost_reply and params == {'terminal': address} and kills == 0)
                kills += 1
                original_core(method, params)  # Actual successful native effect, once.
                raise NativeError('fixture successful kill reply lost')
            result = original_core(method, params)
            if churned and method == 'terminal.get' and params == {'terminal': address}:
                result = copy.deepcopy(result)
                result.update(title='fixture display churn', status={'fixture': True},
                              geometry={'rows': 31, 'cols': 97})
            return result
        def legacy_receipt(receipt):
            nonlocal churned
            repair = receipt.get('repairs', {}).get(leaf)
            if repair and 'source' in repair:
                # OLD kill-first admission, not a post-publication receipt edit.
                identity = repair.pop('source')
                receipt['pending'] = {'operation': 'terminal.kill', 'pane': key,
                                      'leaf': leaf, 'terminal': address,
                                      'pids': repair['pids'], 'identity': identity}
                pending = receipt['pending']
                require(pending['terminal'] == address and pending['leaf'] == leaf)
                snapshot = copy.deepcopy(backend._terminal(address))
                if not lost_reply:
                    pending.pop('identity')  # Old serializer version emulation, BEFORE writer.
                original_receipt(receipt)
                if lost_reply:
                    backend._complete_current_kill(receipt)
                    raise CommandFailure('kept-shell-kill-fault-missing')
                churned = True  # Display-only RPC-result overlay, not native mutation.
                require(backend._terminal(address) != snapshot)
                raise NativeError('core recovery process changed before shell stop')
            return original_receipt(receipt)
        backend.core = fault_core
        backend._receipt = legacy_receipt
        STEP = 'kept-shell-admitted-restore-interruption'
        try:
            Controller(store, backend).restore()
        except (NativeError, ControllerError) as error:
            require(str(error) == ('fixture successful kill reply lost' if lost_reply
                                  else 'core recovery process changed before shell stop'))
        else:
            raise CommandFailure('kept-shell-interruption-missing')
        require(kills == (1 if lost_reply else 0))
        # Drop all local faults before observing durable outcome, then close the
        # lock before invoking the unmodified installed CLI.
        backend = Native(HOME, store)
        receipt = store.read('receipt-' + txid + '.json')
        pending = receipt['pending']
        require(receipt['txid'] == txid and receipt['plan'] == plan)
        require(pending['operation'] == 'terminal.kill' and pending['terminal'] == address)
        require(pending['pids'] == shell_pids and set(receipt['repairs']) == {leaf})
        require(('identity' in pending) == lost_reply)
        require(receipt['document'] == baseline and receipt['bindings'][key] == leaf)
        # Actual public native label changes after intent publication; no mocked
        # terminal payload substitutes for app/ownership compatibility proof.
        native_app_labels(backend, address, changed=True)
        if lost_reply:
            wait(lambda: backend._terminal(address)['state'] == 'finished'
                 and backend._pids_absent(shell_pids))
            finished = finished_terminal_facts(backend._terminal(address))
        else:
            require(backend._terminal(address)['state'] == 'live')
            require(backend._pid_proofs([p['pid'] for p in shell_pids]) == shell_pids)
            backend._shell_proof(backend._terminal(address))
    STEP = 'kept-shell-installed-restore'
    cli('restore')
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        manifest = store.read('manifest.json')
        receipt = manifest['receipt']
        require(manifest['txid'] == txid and manifest['plan'] == plan)
        require(receipt['pending'] is None and receipt['repairs'] == {})
        replacement = receipt['terminals'][key]
        require(replacement != address and receipt['bindings'][key] == leaf)
        require({t['address'] for t in backend._terminals()} - addresses == {replacement})
        require(backend._terminal(address)['state'] == 'finished')
        require(backend._pids_absent(shell_pids) and backend._pids_absent(client_proof))
        require(backend._pids_absent([p for p in before['clients'] if p['pid'] == client_pid]))
        if lost_reply:
            require(finished_terminal_facts(backend._terminal(address)) == finished)
        expected = expected_leaf_rebind(baseline, leaf, address, replacement)
        require(backend._document()[0] == expected)
        coverage = backend._coverage(plan)
        require([c for c in coverage if c['session_id'] != pane['session_id']] == other_clients)
        for other in other_clients:
            require(backend._pid_proofs([other['pid']]) == [
                p for p in before['pids'] if p['pid'] == other['pid']])
        require(backend._actual_core_program(backend._terminal(replacement))
                == (pane['session_id'], pane['cwd']))
        final_addresses = {t['address'] for t in backend._terminals()}
    observe('herdr-core', plan)  # Exact unique client coverage, argv and real backend connection.
    require(backend_pid() == pid)
    cli('restore')
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        require({t['address'] for t in backend._terminals()} == final_addresses)
        require(backend._coverage(plan) == coverage and backend._document()[0] == expected)
        if lost_reply:
            require(finished_terminal_facts(backend._terminal(address)) == finished)
    require(backend_pid() == pid)
    if lost_reply:
        print('F07: kept-shell-observed-kill-recovery-complete')
    else:
        print('F07: kept-shell-pending-kill-recovery-complete')


def edited_expected_plan(plan, later_panes):
    """Independent canonical expectation, not a projection of the actual doc."""
    import copy
    expected = copy.deepcopy(plan)
    alpha = expected['spaces'][0]
    alpha['name'] = 'Desktop renamed alpha'
    retained_tab = alpha['tabs'][1]
    retained_tab['panes'] = retained_tab['panes'][:1]
    retained_tab['panes'][0]['key'] = 's0-t0-p0'
    retained_tab['root'] = {'pane': 's0-t0-p0'}
    later_panes = copy.deepcopy(later_panes)
    for index, pane in enumerate(later_panes):
        pane['key'] = 's0-t1-p' + str(index)
    alpha['tabs'] = [retained_tab, {'name': '2', 'panes': later_panes, 'root': {
        'axis': 'row', 'ratio': 0.25, 'children': [{'pane': 's0-t1-p0'}, {
            'axis': 'column', 'ratio': 0.4,
            'children': [{'pane': 's0-t1-p1'}, {'pane': 's0-t1-p2'}]}]}}]
    return expected


def edited_document_recovery(plan, pid):
    """Interrupt after actual effects, never fabricate journals or receipts."""
    global STEP
    import copy
    from controller import Controller, ControllerError
    from native import NativeError
    Store, Native = adapter()
    STEP = 'edited-document-retain-switch'
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        source = backend.capture('tui')
        restore = backend.restore
        def interrupted_restore(*args, **kwargs):
            restore(*args, **kwargs)
            raise NativeError('fixture interruption after target restore')
        backend.restore = interrupted_restore
        try:
            Controller(store, backend).switch('herdr-core')
        except ControllerError:
            pass
        else:
            raise CommandFailure('edited-switch-interruption-missing')
        require(store.read('transaction.json')['phase'] == 'restore_pending')
        require(backend._pids_absent(source['pids']) and backend._pids_absent(source['clients']))
        # Retain the manifest through genuine recovery writes, interrupted before
        # journal completion. Only this disposable adapter instance is faulted.
        backend = Native(HOME, store)
        restore_current = backend.restore_current
        def interrupted_recovery():
            restore_current()
            raise NativeError('fixture interruption after manifest publication')
        backend.restore_current = interrupted_recovery
        try:
            Controller(store, backend).recover()
        except ControllerError:
            pass
        else:
            raise CommandFailure('edited-recovery-interruption-missing')
        journal = store.read('transaction.json')
        txid = journal['txid']
        require(journal['phase'] == 'restore_pending')
        require(store.read('manifest.json')['txid'] == txid)
        backend = Native(HOME, store)
        document, version = backend._document()
        require(document is not None)
        edited = copy.deepcopy(document)
        shell_tab, agent_tab = edited['spaces'][0]['tabs']
        shell_address = shell_tab['root']['content']['terminal']
        closed_agent = agent_tab['root']['children'][1]['content']['terminal']
        closed_session = plan['spaces'][0]['tabs'][1]['panes'][1]['session_id']
        STEP = 'edited-document-close-views'
        backend.core('terminal.kill', {'terminal': shell_address})
        backend.core('terminal.kill', {'terminal': closed_agent})
        agent_tab['root'] = agent_tab['root']['children'][0]
        edited['spaces'][0]['tabs'] = [agent_tab]
        edited['spaces'][0]['name'] = 'Desktop renamed alpha'
        edited['metadata'] = {'fixture': 'preserve', 'nested': [None, {'value': 7}]}
        later_panes = []
        later_leaves: list[dict] = []
        STEP = 'edited-document-create-later-clients'
        cwd = plan['spaces'][0]['directory']
        for index in range(3):
            created = api('post', '/api/session', {'location': {'directory': cwd},
                          'title': 'Later exact fixture ' + str(index)})['data']
            require(created['location']['directory'] == cwd)
            terminal = backend.core('terminal.run', {
                'argv': [str(BIN / 'opencode'), '--session', created['id']], 'cwd': cwd,
                'keep': True, 'no_parent': True, 'no_notify': True, 'wait': False})
            address = terminal['address']
            wait(lambda: backend._actual_core_program(backend._terminal(address)) == (created['id'], cwd))
            key = 'later-' + str(index)
            later_panes.append({'key': key, 'cwd': cwd, 'session_id': created['id']})
            later_leaves.append({'id': key, 'type': 'block', 'content': {'terminal': address},
                                 'size': {'weight': index + 1}})
        # Build expected semantics independently of the adoption implementation.
        edited['spaces'][0]['tabs'].append({'id': 'later-tab', 'name': '2', 'root': {
            'id': 'later-row', 'type': 'row', 'children': [later_leaves[0], {
                'id': 'later-column', 'type': 'column', 'size': {'weight': 3},
                'children': later_leaves[1:]}]}})
        expected = edited_expected_plan(plan, later_panes)
        # Three existing tabs, including the later nested split, get app-style
        # one-child rows. Fixture-authored structure is not Desktop UI evidence.
        edited = app_compatible_document(edited)
        repair_leaf = agent_tab['root']['id']
        repair_address = agent_tab['root']['content']['terminal']
        live_addresses = [repair_address, *[leaf['content']['terminal'] for leaf in later_leaves],
                          edited['spaces'][1]['tabs'][0]['root']['children'][0]['content']['terminal']]
        app_labels = {address: native_app_labels(backend, address) for address in live_addresses}
        STEP = 'edited-document-publish-desktop-cas'
        backend.core('doc.set', {'name': 'herdr-app', 'value': edited, 'version': version})
        baseline, _ = backend._document()  # Native serialization is authoritative.
        addresses = {t['address'] for t in backend._terminals()}
        # A genuine retained switch, manifest and mixed live/repair population.
        # No direct journal/receipt writes: kill only our proven exact client;
        # core's keep machinery must supply its real idle Bash before recover.
        repair_session = expected['spaces'][0]['tabs'][0]['panes'][0]['session_id']
        clients = backend._coverage(expected)
        client = next(c for c in clients if c['session_id'] == repair_session)
        other_clients = [c for c in clients if c['session_id'] != repair_session]
        other_proofs = backend._pid_proofs([c['pid'] for c in other_clients])
        client_proof = backend._pid_proofs([client['pid']])
        backend._client_argv(client['pid'], repair_session)
        require((Path('/proc') / str(client['pid']) / 'exe').resolve() == NATIVE)
        require(client['pid'] != pid and backend.process_cwd(client['pid']) == cwd)
        fd = os.pidfd_open(client['pid'])
        try:
            require(backend._pid_proofs([client['pid']]) == client_proof)
            signal.pidfd_send_signal(fd, signal.SIGKILL)
        finally:
            os.close(fd)
        def idle_repair():
            current = backend._terminal(repair_address)
            if not backend._pids_absent(client_proof):
                return False
            if backend._actual_core_program(current) != (None, cwd):
                return False
            backend._shell_proof(current)
            return current
        shell = wait(idle_repair)
        shell_proof = backend._pid_proofs([shell['pid'], (shell.get('foreground') or shell)['pid']])
        # Native keep reporting may update view data; retain its latest raw view.
        baseline, _ = backend._document()
        require(store.read('transaction.json')['phase'] == 'restore_pending')
    refusal = subprocess.run([str(BIN / 'remote-herdr'), 'restore'], cwd=HOME,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    require(refusal.returncode == 75)
    STEP = 'edited-document-installed-recovery'
    cli('recover')
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        require(store.read('transaction.json')['phase'] == 'complete')
        require(store.read('transaction.json')['txid'] == txid)
        require(store.read('manifest.json')['schema_version'] == 2)
        receipt = store.read('manifest.json')['receipt']
        replacement = receipt['terminals']['s0-t0-p0']
        require(replacement != repair_address)
        baseline = expected_leaf_rebind(baseline, repair_leaf, repair_address, replacement)
        require(backend._document()[0] == baseline)
        require({t['address'] for t in backend._terminals()} - addresses == {replacement})
        addresses.add(replacement)
        require(backend._terminal(repair_address)['state'] == 'finished')
        require(backend._pids_absent(shell_proof) and backend._pids_absent(client_proof))
        require([c for c in backend._coverage(expected) if c['session_id'] != repair_session] == other_clients)
        require(backend._pid_proofs([c['pid'] for c in other_clients]) == other_proofs)
        require(all(backend._terminal(address)['labels'] == labels
                    for address, labels in app_labels.items()))
        require(not backend.scan({closed_session}))
        require(store.read(receipt['adoption_backup']) is not None)
    observe('herdr-core', expected)
    cli('restore')
    cli('recover')
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        require(backend._document()[0] == baseline)
        require({t['address'] for t in backend._terminals()} == addresses)
        require(not backend.scan({closed_session}))
    require(backend_pid() == pid)
    write(EXPECTED, expected)
    print('F07: current-document-adoption-recovery-complete')
    return expected


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
            {'name': 'Plain shell', 'panes': [
                {'key': 's0-t0-p0', 'cwd': str(directories[0]), 'session_id': None}],
             'root': {'pane': 's0-t0-p0'}},
            {'name': 'Review split', 'panes': [
                {'key': 's0-t1-p0', 'cwd': str(directories[0]), 'session_id': sessions[0]},
                {'key': 's0-t1-p1', 'cwd': str(directories[0]), 'session_id': sessions[1]}],
             'root': {'axis': 'row', 'ratio': 0.375,
                       'children': [{'pane': 's0-t1-p0'}, {'pane': 's0-t1-p1'}]}}]},
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
    retained_shell_switch(plan, pid)
    observe('herdr-core', plan)
    with Store(ROOT) as store:
        backend = Native(HOME, store)
        backups = [store.read(path.name) for path in ROOT.glob('backup-*.json')]
        require(any(value.get('document') == document and
                    address in {t['address'] for t in value.get('terminals', [])} for value in backups))
        require(address in {t['address'] for t in backend._terminals()})
    require(backend_pid() == pid)
    inflight_switch(provider, plan, pid)
    plan = edited_document_recovery(plan, pid)
    interrupted_switch(plan, pid)
    switch('herdr-core', plan, pid)
    restart_and_recover(plan, pid)
    kept_shell_kill_recovery(plan, pid, lost_reply=False)
    kept_shell_kill_recovery(plan, pid, lost_reply=True)
    print('F07: app-labels-and-tab-identities-recovery-complete')
    app_connected_repair(plan, pid)
    plan = app_closed_pending_run_recovery(plan, pid)
    STEP = 'arm-core-boot'
    require(unit('is-enabled', 'remote-herdr-restore.timer') == 'enabled')
    unit('start', 'remote-herdr-restore.timer')


def restart_and_recover(plan, pid):
    global STEP
    from native import sessions
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
        backend.absent(sessions(plan), capture['clients'])
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
        'core kept-terminal spawn readiness unavailable': 'kept-spawn-readiness',
        'core restored terminal readiness unavailable': 'client-readiness',
        'restored runtime layout readiness unavailable': 'layout-readiness',
        'core recovery process changed before shell stop': 'process-changed',
        'core recovery document changed before shell stop': 'document-changed-before-stop',
        'native observation or mutation uncertain': 'native-uncertain',
        'core controller stop requires reconciliation': 'controller-stop-incomplete',
        'core controller stop backup unavailable': 'controller-stop-backup',
        'core controller stop process proof unavailable': 'controller-stop-pids',
        'core process identity changed': 'actual-process-changed',
        'core referenced terminal unavailable': 'referenced-terminal-missing',
        'core repair binding unavailable': 'repair-binding-missing',
        'core repair binding changed': 'repair-binding-changed',
        'core repair stop outcome inconsistent': 'repair-stop-inconsistent',
        'core created binding proof unavailable': 'created-binding-proof',
        'core repair source ownership or program changed': 'repair-source-changed',
        'core owned leaf terminal changed': 'owned-leaf-changed',
        'prior terminal creation requires recovery': 'current-prior-create',
        'session client coverage incomplete or duplicate': 'client-coverage',
        'session client directory or PID mismatch': 'client-directory-or-pid',
        'core current inventory changed': 'current-inventory-changed',
        'core current process identity changed': 'current-process-changed',
        'core repair leaf missing': 'repair-leaf-missing',
        'core repair terminal closed before shell stop': 'repair-closed-before-stop',
        'core created terminal ownership unavailable': 'created-terminal-ownership',
        'core recovery document changed before mutation': 'document-changed-before-mutation',
        'core current restored layout differs': 'current-layout-differs',
        'core current restored bindings differ': 'current-bindings-differ',
        'current document receipt invalid': 'current-receipt-invalid',
        'current document saved binding differs': 'saved-binding-differs',
        'current document repair binding invalid': 'repair-binding-invalid',
        'current document repair PID proof invalid': 'repair-pids-invalid',
        'current document repair stop proof unavailable': 'repair-stop-proof',
    }
    labels.update(r1_refusal_labels())
    try:
        with Store(ROOT) as store:
            Controller(store, Native(HOME, store)).restore()
    except Exception as error:
        label = labels.get(str(error), 'unclassified') if type(error).__name__ == 'NativeError' else 'controller'
        if label == 'kept-spawn-readiness':
            with Store(ROOT) as store:
                backend = Native(HOME, store)
                label += kept_spawn_diagnostics(backend)
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
            'TUI unknown foreground process': 'tui-unknown-foreground',
            'TUI session process coverage incomplete': 'tui-session-coverage',
            'TUI restored layout differs': 'tui-layout-differs',
            'TUI duplicate or failed pane': 'tui-duplicate-or-failed-pane',
            'TUI workspace directory proof ambiguous': 'tui-workspace-ambiguous',
            'session client coverage incomplete or duplicate': 'session-client-coverage',
        }
        protocol_labels.update(r1_refusal_labels())
        if type(error).__name__ == 'NativeError' and str(error) in protocol_labels:
            suffix = '-' + protocol_labels[str(error)]
        print('F07: failed-' + STEP + suffix, file=sys.stderr)
        sys.exit(1)
