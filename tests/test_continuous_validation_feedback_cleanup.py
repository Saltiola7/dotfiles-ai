"""Deterministic cleanup contracts; no subprocess, signals or session commands.

The real module is exercised with deterministic process stubs.
"""
import errno
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "private_dot_config/dotfiles-ai/continuous_validation/feedback.py"
SPEC = importlib.util.spec_from_file_location("cleanup_feedback", SOURCE)
feedback = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feedback)

class Pipe:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.closed = False

    def fileno(self):
        return self.descriptor

    def close(self):
        self.closed = True


class Child:
    pid = 12345  # Synthetic only: os.killpg is always stubbed.

    def __init__(self, wait_error):
        self.stdout = Pipe(30)
        self.stderr = Pipe(31)
        self.wait_error = wait_error
        self.waits = []

    def wait(self, *, timeout):
        self.waits.append(timeout)
        if self.wait_error is not None:
            raise self.wait_error
        return -9


class Selector:
    def __init__(self):
        self.registered = {}
        self.closed = False

    def register(self, stream, events, name):
        self.registered[stream] = SimpleNamespace(fileobj=stream, data=name)

    def unregister(self, stream):
        del self.registered[stream]

    def get_map(self):
        return self.registered

    def select(self, timeout):
        return [(next(iter(self.registered.values())), None)]

    def close(self):
        self.closed = True


class CleanupContract(unittest.TestCase):
    def check_cleanup(self, *, kill_error=None, wait_error=None, expected):
        child = Child(wait_error)
        selector = Selector()
        reads = []

        def read(descriptor, count):
            self.assertEqual(descriptor, child.stdout.fileno())
            self.assertGreater(count, 0)
            value = (b"x" * 8192)[:count]
            reads.append(len(value))
            return value

        with (patch.object(feedback.subprocess, "Popen", return_value=child) as popen,
              patch.object(feedback.selectors, "DefaultSelector", return_value=selector),
              patch.object(feedback.os, "set_blocking") as set_blocking,
              patch.object(feedback.os, "read", side_effect=read),
              patch.object(feedback.os, "killpg", side_effect=kill_error) as killpg):
            caught = None
            try:
                feedback._native_command(["synthetic-command-never-executed"], cwd=ROOT,
                    capture_output=True, text=True, timeout=10, env={})
            except BaseException as error:
                caught = error
            self.assertEqual(child.waits, [1], "cleanup must always attempt bounded reaping")
            self.assertIs(type(caught), subprocess.SubprocessError)
            self.assertEqual(str(caught), expected)
            killpg.assert_called_once_with(child.pid, feedback.signal.SIGKILL)
            self.assertEqual(popen.call_args.kwargs["env"], {})
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertGreater(sum(reads), 64 * 1024)
        self.assertTrue(selector.closed)
        self.assertTrue(child.stdout.closed and child.stderr.closed)

    def test_permission_denied_still_reaps_and_reports_uncertainty(self):
        self.check_cleanup(kill_error=PermissionError(errno.EPERM, "synthetic"),
                           expected="native_termination_unconfirmed")

    def test_permission_denied_and_wait_timeout_remain_uncertain(self):
        self.check_cleanup(kill_error=PermissionError(errno.EPERM, "synthetic"),
                           wait_error=subprocess.TimeoutExpired("synthetic", 1),
                           expected="native_termination_unconfirmed")

    def test_other_signal_error_still_reaps_and_reports_uncertainty(self):
        self.check_cleanup(kill_error=OSError(errno.EIO, "synthetic"),
                           expected="native_termination_unconfirmed")

    def test_wait_oserror_is_normalized(self):
        self.check_cleanup(wait_error=OSError(errno.ECHILD, "synthetic"),
                           expected="native_termination_unconfirmed")

    def test_wait_timeout_is_uncertain(self):
        self.check_cleanup(wait_error=subprocess.TimeoutExpired("synthetic", 1),
                           expected="native_termination_unconfirmed")

    def test_successful_cleanup_preserves_output_limit(self):
        self.check_cleanup(expected="native_output_limit")

    def test_absent_group_and_reaped_child_preserve_output_limit(self):
        self.check_cleanup(kill_error=ProcessLookupError(errno.ESRCH, "synthetic"),
                           expected="native_output_limit")

    def test_absent_group_does_not_waive_wait_timeout(self):
        self.check_cleanup(kill_error=ProcessLookupError(errno.ESRCH, "synthetic"),
                           wait_error=subprocess.TimeoutExpired("synthetic", 1),
                           expected="native_termination_unconfirmed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
