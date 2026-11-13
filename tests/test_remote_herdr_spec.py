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
                  'operators must not manufacture one', 'does not implement INT-082',
                  "exactly `['/bin/sh']`", 'TUI-only compatibility',
                  'dea822039d71902ca7dc6dc5cc337a7d31514b31', 'both runtime boot phases'):
        assert token in section
    docs = root / 'docs/specs/dotfiles_ai_distribution'
    assert 'Plain-shell recovery accepts' in (docs / 'README.md').read_text()
    changelog = (docs / 'CHANGELOG.md').read_text().split('## 2026-11-08 — Recover retained plain-shell switches (RRW-007F-R1)', 1)[1].split('\n## ', 1)[0]
    for token in ('64 panes', '10 shells', '54 exact sessions', '63',
                  'Bootstrap and core 0.1.18 pin unchanged', 'draft PR', 'no live recovery'):
        assert token in changelog


def test_current_document_contract_keeps_adoption_and_mutation_boundaries():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    section = text.split('### Current-document restore and adoption (RRW-007G / INT-082)', 1)[1]
    for token in ('stable leaf ID', 'current document', 'restore_pending', 'never recreated',
                  'account-wide duplicate-client proofs', 'quiet no-op', 'Manifest schema 2',
                  'schema 1 remains', 'five seconds', 'partial inventories never pass',
                  'Native start/run/kill/doc.set effects are never retried', 'three later exact clients',
                  'one-based tab numbers', '007H', '007I'):
        assert token in section


def test_current_document_completion_artifacts_preserve_rollout_and_compatibility():
    root = Path(__file__).parents[1] / 'docs/specs/dotfiles_ai_distribution'
    readme = (root / 'README.md').read_text()
    for token in ('Manifest schema 2', 'quiet no-op', 'No new configuration keys',
                  'unresolved old mutation intents', 'RRW-007H', 'RRW-007I'):
        assert token in readme
    entry = (root / 'CHANGELOG.md').read_text().split(
        '## 2026-11-09 — Restore current desktop bindings (RRW-007G)', 1)[1].split('\n## ', 1)[0]
    for token in ('46a7347e', 'three later exact', 'same-journal', 'both runtime boots',
                  'No new keys/inputs', 'Fork A', 'no failed evidence is waived',
                  'Final Push', 'draft PR #299', 'never main'):
        assert token in entry


def test_kept_shell_kill_intent_contract_retains_identity_and_exit_guards():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    section = text.split('### Kept-shell kill-intent recovery (RRW-007G-R1 / INT-082)', 1)[1].split('\n### ', 1)[0]
    for token in ('presentation is not its process identity', 'same original owned idle shell',
                  'original captured processes absent', 'unchanged document/version',
                  'not blind mutation replay', 'single', 'identity', 'remain readable',
                  'never observed values', 'Unknown extra intent fields', 'No new CLI/configuration input',
                  'lost successful kill replies', 'both-boot', 'Fork A', '007H', '007I'):
        assert token in section


def test_r1_completion_artifacts_preserve_hotfix_and_rollout_boundaries():
    root = Path(__file__).parents[1] / 'docs/specs/dotfiles_ai_distribution'
    readme = (root / 'README.md').read_text()
    entry = (root / 'CHANGELOG.md').read_text().split(
        '## 2026-11-09 — Pending kept-shell recovery (RRW-007G-R1)', 1)[1].split('\n## ', 1)[0]
    for token in ('RRW-007G-R1', 'legacy intents', 'fixed field labels',
                  'Fork A', 'Bootstrap, binary pins and setup inputs are unchanged'):
        assert token in readme
    for token in ('INT-082', '719 tests', '55 subtests', 'Older adapters refuse',
                  'installed CLI', '60644736', 'never main', 'exact-head approval',
                  '007H', '007I', 'address-only'):
        assert token in entry


def test_r2_desktop_compatibility_contract_preserves_ownership_and_identity():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    section = text.split('### Desktop ownership and identity compatibility (RRW-007G-R2 / INT-082)', 1)[1].split('\n### ', 1)[0]
    for token in ('_same_labels', 'duplicate-creation', 'complete `remote-herdr-*`',
                  '`where`', '`herdr.seen`', '`herdr.space`', '`herdr.tab`',
                  'extra ownership keys', 'independently for spaces, tabs and all tree nodes',
                  'one-child row', 'branch', 'leaf', 'restore_pending', 'remote-herdr recover',
                  'without hand-editing journals', 'Already-live exact sessions stay live',
                  'actual app-producer evidence', 'both-boot', 'Fork A', '007H', '007I'):
        assert token in section


def test_r2_completion_artifacts_keep_live_recovery_separate():
    root = Path(__file__).parents[1] / 'docs/specs/dotfiles_ai_distribution'
    readme = (root / 'README.md').read_text()
    entry = (root / 'CHANGELOG.md').read_text().split(
        '## 2026-11-10 — Desktop ownership and ID compatibility (RRW-007G-R2)', 1)[1].split('\n## ', 1)[0]
    for token in ('RRW-007G-R2', 'remote-herdr-*', 'one-child row',
                  'restore_pending', 'remote-herdr recover', 'Fork A'):
        assert token in readme
    for token in ('INT-082', '775 tests', '55 subtests', 'terminal.label',
                  'genuine controller-written', 'actual Desktop UI', '13ae0c56',
                  'never main', 'exact-head merge approval', '007H', '007I'):
        assert token in entry


def test_r4_reboot_recovery_contract_keeps_current_process_and_closure_proofs():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    section = text.split('### Reboot-interrupted repair (RRW-007G-R4 / INT-082)', 1)[1].split('\n### ', 1)[0]
    for token in ('stored `created` address is an effect identity', 'fresh repair generation',
                  'unbound retained replacement', 'already bound', 'stopped repair whose stable leaf is gone',
                  'completed restore', '54 repairs', 'hand edits', 'PID reuse',
                  'core-only restart is not a full VM boot claim', 'gate-commit', 'RRW-007I'):
        assert token in section


def test_r4_delivery_artifacts_keep_boot_proofs_and_native_claims_bounded():
    root = Path(__file__).parents[1] / 'docs/specs/dotfiles_ai_distribution'
    readme = (root / 'README.md').read_text()
    entry = (root / 'CHANGELOG.md').read_text().split(
        '## 2026-11-11 — Reboot-interrupted repair (RRW-007G-R4)', 1)[1].split('\n## ', 1)[0]
    for token in ('RRW-007G-R4', 'Linux boot UUIDs', 'idle-stop checkpoints',
                  'not a full VM/Desktop GUI claim', 'No new inputs', 'Fork A'):
        assert token in readme
    for token in ('887 tests', '88 subtests', '38 stdlib', '`boot_id`',
                  '`retained_shell: true`', 'never a historical kill', 'never main',
                  'final merge', '007I', 'staged-deletion defect'):
        assert token in entry


def test_r3_app_connected_transition_keeps_replacement_live_before_retirement():
    root = Path(__file__).parents[1]
    text = (root / 'docs/specs/dotfiles_ai_distribution/features/remote-herdr-runtime.md').read_text()
    section = text.split('### App-connected repair ordering (RRW-007G-R3 / INT-082)', 1)[1].split('\n### ', 1)[0]
    for token in ('per-leaf create', 'verify, rebind, then retire', 'original shell remains live',
                  'document-version CAS', 'never the live', 'pre-create', 'CAS-uncertain',
                  'live **and finished**', 'resolve that', 'repair as closed',
                  'present leaf with no terminal match', 'already-created unbound replacements',
                  'Never', 'hand-edit journals', 'app-like client', 'both-boot',
                  '0ac1088028a1d3aca0cff09897bdce2ff3cb0829647a6bd885179af70715a8b3',
                  'Fork A', '007I'):
        assert token in section


def test_r3_completion_artifacts_keep_recovery_authority_and_provenance_exact():
    root = Path(__file__).parents[1] / 'docs/specs/dotfiles_ai_distribution'
    readme = (root / 'README.md').read_text()
    entry = (root / 'CHANGELOG.md').read_text().split(
        '## 2026-11-10 — App-connected restore ordering (RRW-007G-R3)', 1)[1].split('\n## ', 1)[0]
    for token in ('RRW-007G-R3', 'CAS-rebind', 'recover', 'complete switch journal',
                  'closed without replaying', 'Fork A', 'RRW-007I'):
        assert token in readme
    for token in ('#524', '924 tests', '68 subtests', 'generation', 'pre-kill oracle',
                  'Native/Controller', 'uninstrumented idempotence', 'Desktop GUI',
                  'never main', 'separate approval', '007I', '30a5b01b'):
        assert token in entry
