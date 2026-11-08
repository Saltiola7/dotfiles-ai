"""Approved runtime boundaries remain explicit in the public feature contract."""
from pathlib import Path


def test_runtime_contract_keeps_approved_ownership_and_failure_boundaries():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    for required in (
        'INT-077', 'INT-079', 'critical', 'in-flight', 'upstream',
        'sole', 'transient', 'HC_SESSION', 'no automatic', 'native acceptance pending',
        'private', 'CAS', 'PID/start-time', 'shell argv', 'label',
        'remote-herdr switch', '--replace-target', '--from-file', 'remote-herdr recover',
        'manifest.json', 'transaction.json', '30 seconds', 'Visual Evidence', 'Text Equivalent',
    ):
        assert required.lower() in text.lower()
    assert 'No completion or native pass is claimed' in text
