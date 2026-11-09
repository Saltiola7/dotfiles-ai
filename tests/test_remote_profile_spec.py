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
