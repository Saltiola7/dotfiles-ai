"""Approved runtime boundaries remain explicit in the public feature contract."""
from pathlib import Path


def test_runtime_contract_keeps_approved_ownership_and_failure_boundaries():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    for required in (
        'INT-077', 'INT-079', 'critical', 'in-flight', 'upstream',
        'sole', 'transient', 'HC_SESSION', 'no automatic', 'hosted qualification',
        'private', 'CAS', 'PID/start-time', 'shell argv', 'label',
        'remote-herdr switch', '--replace-target', '--from-file', 'remote-herdr recover',
        'manifest.json', 'transaction.json', '30 seconds', 'Visual Evidence', 'Text Equivalent',
        'herdr-app', 'value.spaces', '/run/user/<uid>/herdr-core/default.sock',
    ):
        assert required.lower() in text.lower()
    assert 'No live deployment or merge is claimed' in text
    assert '24de7482f3c9ccc461b998ad17c63e1501ef1afa' in text


def test_runtime_completion_artifacts_keep_delivery_and_rollout_separate():
    root = Path(__file__).parents[1] / 'docs/specs/dotfiles_ai_distribution'
    readme = (root / 'README.md').read_text()
    changelog = (root / 'CHANGELOG.md').read_text()
    assert 'features/remote-herdr-runtime.md' in readme
    for token in ('--replace-target', 'shared backend', 'Fork A', '0.1.18'):
        assert token in readme
    entry = changelog.split('## 2026-11-08 — Selected remote Herdr runtime (RRW-007F)', 1)[1].split('\n## ', 1)[0]
    for token in ('24de7482', '19 hosted checks', 'Final Push', 'PR #297',
                  'No gate', 'bootstrap change', 'Fork A', '007B/007E/007F'):
        assert token in entry


def test_runtime_support_contract_retains_state_and_installer_authority():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    operations = text.split('## Operations and maintenance', 1)[1].split('## Visual Evidence', 1)[0]
    for token in ('remote-herdr selected', 'remote-herdr-core check', 'hc-serve-*',
                  'hc-hold-*', 'hc-shutdown-*', 'recover', 'owner inspection',
                  'Fork A', 'renewed checksum', 'retirement', 'No automatic cleanup'):
        assert token in operations
    assert '75 seconds' in text and '60-second backoff cap' in text
    assert 'Other ordinary\nreadiness waits remain 30 seconds' in text


def test_shell_label_hotfix_contract_preserves_retained_recovery_and_scope():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    section = text.split('### Plain-shell label compatibility (RRW-007F-R1)', 1)[1]
    for token in ('empty values', 'remote-herdr-owner', 'remote-herdr-pane',
                  'remote-herdr-session', 'extra labels still refuse', 'restore_pending',
                  'pending=None', 'remote-herdr recover', 'without repeating creation',
                  'operators must not manufacture one', 'does not implement INT-082'):
        assert token in section
