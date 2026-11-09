"""INT-083/084 profile boundaries remain explicit and source-owned."""
from pathlib import Path


def test_profile_followup_contract_preserves_policy_and_argv_boundaries():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-profile-followups.md').read_text()
    for token in ('INT-083/084', 'critical-risk', 'tab_bar_mode', 'auto`, `on`, `off',
                  'default empty string', 'preserving other tab options',
                  'activation_binding', 'semantic_digest', 'legacy_policy_digest',
                  'bytes/inode remain unchanged', 'schema 2', 'single anchor transitively',
                  'complete effective policy', 'strict types', 'read-only',
                  'stop wrapper option parsing', 'known value-taking option',
                  'Bash 3.2', 'Fork A', 'RRW-007I', '## Visual Evidence', 'Text Equivalent'):
        assert token in text


def test_profile_completion_and_shared_storage_contracts_are_coherent():
    root = Path(__file__).parents[1] / 'docs/specs/dotfiles_ai_distribution'
    readme = (root / 'README.md').read_text()
    storage = (root / 'features/workflow-storage-policy.md').read_text()
    activation = (root / 'features/remote-worktree-activation.md').read_text()
    changelog = (root / 'CHANGELOG.md').read_text().split(
        '## 2026-11-09 — Remote profile follow-ups (RRW-007H)', 1)[1].split('\n## ', 1)[0]
    assert 'tab_bar_mode = "off"' in readme and 'validated legacy preimage' in readme
    assert 'activation_binding' in storage and 'schema 2' in storage
    assert 'preserve activation bytes' in changelog
    assert 'source-only revisions retain activation' in activation
    assert 'former manual fixture refresh workaround' in activation
    for token in ('606 tests', '4 explicitly selected', '91', '15', 'Fork A', '007I', 'never main'):
        assert token in changelog
