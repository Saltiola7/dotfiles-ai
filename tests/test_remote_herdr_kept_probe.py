"""Pure fixtures only: no native core, systemctl, network or live /proc access."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError('source-unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load('kept_probe_test', ROOT / 'tests/remote_herdr_systemd/kept-probe.py')
processes = load('kept_processes_test', ROOT / 'dot_local/share/dotfiles-ai/remote-herdr/processes.py')


def registry(**changes):
    terminal = {'address': 't1', 'pid': None, 'keep': True, 'state': 'live',
                'reason': 'server_stop', 'restart_after_ms': 1500, 'restart_delay_ms': 1500}
    terminal.update(changes)
    return {'next_id': 2, 'holder': None, 'terminals': {'1': terminal}}


class ClassificationTests(unittest.TestCase):
    def classify(self, **changes):
        return probe.classify(registry(**changes), 't1', 2000)

    def test_eligible_none_and_serde_omitted_holder(self):
        omitted = self.classify()
        self.assertEqual(omitted, self.classify(holder=None))
        self.assertEqual(omitted['classification'], 'eligible-pending-noholder')
        self.assertFalse(omitted['holder_set'])

    def test_claimed_is_condition_not_lost_spawn_proof(self):
        result = self.classify(holder='PRIVATE-HOLDER', argv=['PRIVATE'], cwd='PRIVATE', env={'secret': 'PRIVATE'})
        self.assertEqual(result['classification'], 'claimed-pending')
        self.assertTrue(result['pid_none'])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('lost_spawn_proven', result)

    def test_spawned_backoff_finished_and_missing(self):
        self.assertEqual(self.classify(pid=123, holder='private')['classification'], 'spawned')
        self.assertEqual(self.classify(restart_after_ms=3000)['classification'], 'backoff-pending-noholder')
        self.assertEqual(self.classify(state='finished')['classification'], 'not-kept-live')
        self.assertEqual(probe.classify(registry(), 't2', 2000)['classification'], 'record-missing')

    def test_schema_unsupported_is_fail_closed(self):
        for value in ({}, [], {'terminals': []}, {'terminals': {'1': []}}):
            self.assertEqual(probe.classify(value, 't1', 0)['classification'], 'schema-unsupported')
        for changes in ({'pid': True}, {'pid': 1}, {'pid': -1}, {'keep': 1}, {'state': []},
                        {'reason': 'PRIVATE'}, {'reason': {}}, {'holder': 4},
                        {'restart_delay_ms': -1}, {'restart_after_ms': True}):
            with self.subTest(changes=changes):
                self.assertEqual(self.classify(**changes)['classification'], 'schema-unsupported')
        value = registry()
        del value['terminals']['1']['restart_delay_ms']
        self.assertEqual(probe.classify(value, 't1', 0)['classification'], 'schema-unsupported')
        value = registry()
        value['terminals']['2'] = value['terminals']['1'].copy()
        self.assertEqual(probe.classify(value, 't1', 0)['classification'], 'schema-unsupported')


class PrivateReadTests(unittest.TestCase):
    def test_bootstrap_explicitly_owns_intermediate_local_directory(self):
        script = (ROOT / 'tests/remote_herdr_systemd/kept-probe.sh').read_text()
        self.assertIn('install -d -o fixture -g fixture -m 0700 '
                      '/home/fixture/.local /home/fixture/.local/bin', script)

    def test_private_read_and_symlink_mode_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            parent.chmod(0o700)
            target = parent / 'terminals.json'
            probe.write_private(target, registry())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(probe.private_registry(target), registry())
            with self.assertRaises(FileExistsError):
                probe.write_private(target, {})
            link = parent / 'link'
            link.symlink_to(target)
            with self.assertRaises(OSError):
                probe.private_registry(link)
            directory_link = parent / 'directory-link'
            directory_link.symlink_to(parent, target_is_directory=True)
            with self.assertRaises(OSError):
                probe.private_registry(directory_link / target.name)
            target.chmod(0o666)
            with self.assertRaises(ValueError):
                probe.private_registry(target)
            target.chmod(0o600)
            target.write_bytes(b'x' * (2 * 1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                probe.private_registry(target)


class ShellIdentityTests(unittest.TestCase):
    def test_only_shell_and_optional_login_flag(self):
        for raw in (b'/bin/sh\0', b'/bin/bash\0-l\0', b'-bash\0', b'sh\0--login\0'):
            self.assertTrue(probe.shell_argv(raw))
        for raw in (b'', b'/bin/sh', b'/bin/sh\0-c\0true\0', b'python\0',
                    b'/bin/bash\0-l\0-c\0true\0', b'/bin/bash\0\0'):
            self.assertFalse(probe.shell_argv(raw))

    def test_fake_proc_production_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / '123'
            directory.mkdir()
            uid = os.getuid()
            (directory / 'status').write_text('Uid:\t' + '\t'.join([str(uid)] * 4) + '\n')
            fields = ['S'] + ['0'] * 18 + ['4242']
            (directory / 'stat').write_text('123 (shell with ) space) ' + ' '.join(fields))
            (directory / 'cmdline').write_bytes(b'/bin/sh\0')
            (directory / 'cwd').symlink_to(root, target_is_directory=True)
            self.assertEqual(probe.shell_proof(processes, 123, root, root),
                             {'pid': 123, 'start_ticks': 4242})
            with self.assertRaises(ValueError):
                probe.shell_proof(processes, 123, root / 'wrong', root)
            (directory / 'cmdline').write_bytes(b'/bin/sh\0-c\0true\0')
            with self.assertRaises(ValueError):
                probe.shell_proof(processes, 123, root, root)
            (directory / 'cmdline').write_bytes(b'/bin/sh\0')
            with patch.object(processes, 'identity', side_effect=[('S', 4242), ('S', 4243)]):
                with self.assertRaises(ValueError):
                    probe.shell_proof(processes, 123, root, root)
            with patch.object(processes, 'task_uid', return_value=None):
                with self.assertRaises(ValueError):
                    probe.shell_proof(processes, 123, root, root)


if __name__ == '__main__':
    unittest.main()
