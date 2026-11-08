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


class QualificationSourceTests(unittest.TestCase):
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
                        "'--from-file'", "'--replace-target'", "'terminal.run'", "'doc.set'",
                        "'hc-serve-'", "'hc-hold-'", "'hc-shutdown-'", "'Transient'",
                        'signal.pidfd_send_signal(fd, signal.SIGTERM)',
                        "backend._coverage(plan) == before", "backend.stop('herdr-core', capture)",
                        "cli('restore')", "cli('recover')", "backend._pids_absent(before['clients'])",
                         "backend._client_argv(client['pid'], client['session_id'])",
                         "f01.connected(client['pid'], port)",
                        'backend._semantic', 'backend_pid() == pid', "'--version'",
                        "'remote-herdr-core', 'check'", "'ratio': 0.375",
                        'child.send_signal(signal.SIGSTOP)', 'require(interrupted)',
                        'require(refusal.returncode == 75)', "STEP = 'interrupted-switch-recovery'"):
            self.assertIn(witness, source)
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
