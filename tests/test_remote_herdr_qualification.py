"""Source-only checks, never execute a runtime, login, systemctl or proc read.

These tests do not certify native behavior; the mandatory hosted job does that.
"""
import ast
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
        self.assertEqual(pins['opencode']['version'], '1.18.25')
        self.assertEqual(pins['herdr_core']['archive_sha256'],
                         '5b2f97cb4b2a9d7a6b2cc5942628203ed9fbb7cc0c2b4b09ad8a6f5648e246b7')
        self.assertEqual(pins['herdr_core']['binary_sha256'],
                         'baa9d208d6400556a6e379152455fe1301e0e1acdbc114ff60b79d64425179cf')
        for section, key in (('herdr', 'linux_amd64_asset_sha256'),
                             ('opencode', 'linux_amd64_asset_sha256')):
            self.assertRegex(pins[section][key], r'^[a-f0-9]{64}$')
        self.assertEqual(pins['herdr']['linux_amd64_asset_sha256'],
                         '14d9e8bc8b4a9e0118d77c32266f76d461f09b40342eb23752960bd89f59929d')
        self.assertEqual(pins['opencode']['linux_amd64_asset_sha256'],
                         '58a3729a6f3432dd6d2917fcc4a949788891a035818646ad480e12c947f56e78')
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
                        "'v2.session.create'", "'?mode=ro'", 'PRAGMA table_info(session)',
                        "'--from-file'", "'--replace-target'", "'terminal.run'", "'doc.set'",
                        "'hc-serve-'", "'hc-hold-'", "'hc-shutdown-'", "'Transient'",
                        'signal.pidfd_send_signal(fd, signal.SIGTERM)',
                        "backend._coverage(plan) == before", "backend.stop('herdr-core', capture)",
                        "cli('restore')", "cli('recover')", "backend._pids_absent(before['clients'])",
                        "backend._client_argv(client['pid'], client['session_id'])",
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

    def test_inflight_proof_uses_native_identity_and_durable_history(self):
        source = (FIXTURE / 'verify-user.py').read_text()
        for witness in ("Server(('127.0.0.1', 0), Handler)", 'ThreadingHTTPServer',
                        "self.path == '/v1/chat/completions'", "body['model'] == 'held'",
                        "body['stream'] is True", "self.headers.get('X-Session-Id') == fixture.session_id",
                        "self.headers.get('x-session-affinity')", 'length <= 1024 * 1024',
                        "'@ai-sdk/openai-compatible'", "'model': 'rrw007f/held'",
                        "'model': {'id': 'held', 'providerID': 'rrw007f'}",
                        "'id': message_id", "'delivery': 'steer', 'resume': True",
                        'provider.held.wait(120)', "switch('tui', plan, pid)",
                        'provider.release.set()', 'fixture.release.wait(360)',
                        'self.requests == 1', "'/api/session/active'", 'range(100)',
                        "'/history?limit=100&after='", "page['hasMore']",
                        "event['durable']['seq'] > after", "['data']['assistantMessageID']",
                        "typed(events, 'step.started') == starts", "typed(events, 'step.failed')",
                        "ends[0]['data']['finish'] == 'stop'", "typed(events, 'text.ended')",
                        "admissions[0]['durable']['seq'] == admitted['admittedSeq']",
                        "prompts[0]['data']['messageID'] == admitted['id']",
                        "'RRW007F-BEGIN:' + provider.nonce + ':END'",
                        'self.server.shutdown()', 'self.server.server_close()',
                        "print('F07: inflight-turn-preservation-complete')"):
            self.assertIn(witness, source)
        self.assertNotIn('/wait', source)
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
                  node.name in {'require', 'HeldProvider'})]
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
            self.assertEqual(config['providers']['rrw007f']['api'], {
                'type': 'aisdk', 'package': '@ai-sdk/openai-compatible',
                'url': 'http://127.0.0.1:' + str(provider.server.server_port) + '/v1'})
            self.assertNotRegex(json.dumps(config), r'apiKey|credential|authorization|integration|env')
            response = self.request(provider)
            self.assertEqual(response.status, 200)
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
