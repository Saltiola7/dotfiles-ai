"""Legacy first-launch upgrades preserve native UI state, never owned edits."""
import hashlib
import json
from pathlib import Path
import tomllib

import pytest
from test_codex_distribution import load_projector, managed_source


def test_ubi_qualifies_the_projection_upgrade_boundary():
    root = Path(__file__).parents[1]
    workflow = (root / '.github/workflows/rhel-remote-user.yml').read_text()
    for path in ('dot_local/bin/executable_codex-project', 'run_onchange_after_project-codex.sh.tmpl',
                 'tests/test_codex_runtime_state.py'):
        assert f'"{path}"' in workflow
    assert 'Check legacy Codex projection upgrades' in workflow
    assert 'tests/test_codex_runtime_state.py -q' in workflow


def previous_projection(tmp_path, *, hooks_only=False):
    core = load_projector()
    source = managed_source(tmp_path)
    config = '[[hooks.Stop]]\ncommand = "managed-hook"\n' if hooks_only else (
        'model = "managed"\napproval_policy = "on-request"\n'
        '[[hooks.Stop]]\ncommand = "managed-hook"\n')
    (source / 'config.toml').write_text(config)
    target = tmp_path / 'state/codex'
    core.project(source, target)
    manifest = target / core.MANIFEST
    files = json.loads(manifest.read_text())['files']
    # This is the exact schema written by the b8043183 projector. No native
    # binary, credentials or historical Git/network access is needed.
    manifest.write_text(json.dumps({'schema_version': 1, 'files': files}))
    return core, source, target, config


@pytest.mark.parametrize('hooks_only', [False, True])
def test_legacy_first_launch_config_upgrades_without_reset(tmp_path, hooks_only):
    core, source, target, config = previous_projection(tmp_path, hooks_only=hooks_only)
    local = config + '\n[tui]\nscreen_reader_detection_done = true\n'
    (target / 'config.toml').write_text(local)
    (source / 'AGENTS.md').write_text('upgraded managed instructions\n')
    core.project(source, target)
    assert (target / 'config.toml').read_text() == local
    assert (target / 'AGENTS.md').read_text() == 'upgraded managed instructions\n'
    manifest = json.loads((target / core.MANIFEST).read_text())
    assert manifest['schema_version'] == 2
    assert len(manifest['config_owned_sha256']) == 64
    assert manifest['files']['config.toml'] == hashlib.sha256(local.encode()).hexdigest()
    backups = list((target / '.dotfiles-ai-config-backups').glob('*/config.toml'))
    assert len(backups) == 1 and backups[0].read_text() == local
    core.project(source, target)
    assert (target / 'config.toml').read_text() == local


def test_native_state_survives_later_managed_upgrade(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    (target / 'config.toml').write_text(config + '\n[tui]\nscreen_reader_detection_done = true\n')
    core.project(source, target)
    (target / 'config.toml').write_text((target / 'config.toml').read_text() +
        '\n[notice]\nhide_full_access_warning = true\n')
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    core.project(source, target)
    value = tomllib.loads((target / 'config.toml').read_text())
    assert value['model'] == 'updated'
    assert value['tui']['screen_reader_detection_done'] is True
    assert value['notice']['hide_full_access_warning'] is True
    core.project(source, target)
    assert tomllib.loads((target / 'config.toml').read_text()) == value


@pytest.mark.parametrize('version', [1, 2])
@pytest.mark.parametrize('edit', ['model', 'hooks', 'unknown', 'removed', 'malformed'])
def test_native_state_does_not_admit_owned_or_unknown_edits(tmp_path, version, edit):
    core, source, target, config = previous_projection(tmp_path)
    if version == 2:
        core.project(source, target)
    changed = config + '\n[tui]\nscreen_reader_detection_done = true\n'
    if edit == 'model':
        changed = changed.replace('model = "managed"', 'model = "edited"')
    elif edit == 'hooks':
        changed = changed.replace('managed-hook', 'edited-hook')
    elif edit == 'unknown':
        changed += '\n[projects.unreviewed]\ntrust_level = "trusted"\n'
    elif edit == 'removed':
        changed = changed.replace('approval_policy = "on-request"\n', '')
    else:
        changed += '\ninvalid = [\n'
    (target / 'config.toml').write_text(changed)
    before = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):
        core.project(source, target)
    assert {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()} == before


def test_legacy_unknown_baseline_is_not_guessed(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    (target / 'config.toml').write_text(config + '\n[tui]\nscreen_reader_detection_done = true\n')
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    with pytest.raises(ValueError, match='managed target changed'):
        core.project(source, target)


def test_interrupted_native_state_upgrade_recovers(tmp_path, monkeypatch):
    core, source, target, config = previous_projection(tmp_path)
    (target / 'config.toml').write_text(config + '\n[tui]\nscreen_reader_detection_done = true\n')
    (source / 'AGENTS.md').write_text('upgraded instructions\n')
    publish = core.publish_entry
    def interrupt(*args):
        publish(*args)
        raise RuntimeError('interrupted')
    monkeypatch.setattr(core, 'publish_entry', interrupt)
    with pytest.raises(RuntimeError, match='interrupted'):
        core.project(source, target)
    monkeypatch.setattr(core, 'publish_entry', publish)
    core.project(source, target)
    assert tomllib.loads((target / 'config.toml').read_text())['tui']['screen_reader_detection_done'] is True
    assert json.loads((target / core.MANIFEST).read_text())['schema_version'] == 2
    assert not (target / core.JOURNAL).exists()


def test_unchanged_legacy_projection_can_upgrade_managed_values(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    core.project(source, target)
    assert tomllib.loads((target / 'config.toml').read_text())['model'] == 'updated'
    assert json.loads((target / core.MANIFEST).read_text())['schema_version'] == 2


def test_version_two_uses_prior_not_incoming_owned_fingerprint(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    core.project(source, target)
    changed = config.replace('"managed"', '"updated"')
    (source / 'config.toml').write_text(changed)
    (target / 'config.toml').write_text(changed + '\n[tui]\nscreen_reader_detection_done = true\n')
    with pytest.raises(ValueError, match='managed target changed'):
        core.project(source, target)


def test_native_state_round_trips_on_managed_change(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    runtime = '\n[tui]\nstatus_line = ["model", "cwd"]\ntheme = "téšt"\n' + (
        '[tui.keymap]\n"ctrl+x" = { action = "line\\nnext", enabled = true }\n')
    (target / 'config.toml').write_text(config + runtime)
    core.project(source, target)
    expected = tomllib.loads((target / 'config.toml').read_text())['tui']
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    core.project(source, target)
    assert tomllib.loads((target / 'config.toml').read_text())['tui'] == expected
    # Mutable native state remains native-owned after a successful merge.
    (target / 'config.toml').write_text((target / 'config.toml').read_text().replace('téšt', 'other'))
    core.project(source, target)
    assert tomllib.loads((target / 'config.toml').read_text())['tui']['theme'] == 'other'


@pytest.mark.parametrize('runtime', ['tui = false\n', '[tui]\ntheme = 1979-05-27\n'])
def test_invalid_native_state_is_refused(tmp_path, runtime):
    core, source, target, config = previous_projection(tmp_path)
    # Scalars must be at the root, before any hook array-of-table headers.
    (target / 'config.toml').write_text(runtime + '\n' + config)
    with pytest.raises(ValueError):
        core.project(source, target)


def test_source_cannot_claim_reserved_native_tables(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    (source / 'config.toml').write_text(config + '\n[tui]\ntheme = "source-owned"\n')
    with pytest.raises(ValueError, match='native config tables'):
        core.project(source, target)


def test_other_managed_edits_block_native_adoption_before_preimages(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    (target / 'config.toml').write_text(config + '\n[tui]\nscreen_reader_detection_done = true\n')
    (target / 'AGENTS.md').write_text('unreviewed instructions\n')
    with pytest.raises(ValueError, match='managed target changed'):
        core.project(source, target)
    assert not (target / '.dotfiles-ai-config-backups').exists()
    assert not (target / core.JOURNAL).exists()


@pytest.mark.parametrize('fault', ['mode', 'hardlink', 'oversized'])
def test_native_adoption_keeps_private_file_guards(tmp_path, monkeypatch, fault):
    core, source, target, config = previous_projection(tmp_path)
    path = target / 'config.toml'
    path.write_text(config + '\n[tui]\nscreen_reader_detection_done = true\n')
    if fault == 'mode':
        path.chmod(0o644)
    elif fault == 'hardlink':
        (target / 'linked-config').hardlink_to(path)
    else:
        # Leave source/manifest admission under the original limit; bound only
        # the target reader to exercise its oversized-file rejection.
        original = core.private_config
        def bounded_config(path):
            monkeypatch.setattr(core, 'MAX_FILE_SIZE', len(config))
            return original(path)
        monkeypatch.setattr(core, 'private_config', bounded_config)
    with pytest.raises(ValueError, match='unsafe managed target'):
        core.project(source, target)


@pytest.mark.parametrize('version', [True, 3])
def test_manifest_version_validation_remains_strict(tmp_path, version):
    core, source, target, _ = previous_projection(tmp_path)
    path = target / core.MANIFEST
    metadata = json.loads(path.read_text())
    metadata['schema_version'] = version
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='invalid ownership manifest'):
        core.project(source, target)


def test_legacy_pending_transaction_remains_recoverable(tmp_path, monkeypatch):
    core, source, target, _ = previous_projection(tmp_path)
    (source / 'AGENTS.md').write_text('new instructions\n')
    publish = core.publish_entry
    def interrupt(*args):
        publish(*args)
        raise RuntimeError('interrupted')
    monkeypatch.setattr(core, 'publish_entry', interrupt)
    with pytest.raises(RuntimeError):
        core.project(source, target)
    journal = target / core.JOURNAL
    metadata = json.loads(journal.read_text())
    metadata['schema_version'] = 1
    metadata.pop('config_owned_sha256')
    journal.write_text(json.dumps(metadata))
    monkeypatch.setattr(core, 'publish_entry', publish)
    core.project(source, target)
    assert (target / 'AGENTS.md').read_text() == 'new instructions\n'
    assert json.loads((target / core.MANIFEST).read_text())['schema_version'] == 2


def test_drift_preimage_precedes_managed_update(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    core.project(source, target)
    before = config + '\n[tui]\nscreen_reader_detection_done = true\n'
    (target / 'config.toml').write_text(before)
    manifest_before = (target / core.MANIFEST).read_bytes()
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    core.project(source, target)
    backups = list((target / '.dotfiles-ai-config-backups').iterdir())
    assert len(backups) == 1
    assert (backups[0] / 'config.toml').read_text() == before
    assert (backups[0] / core.MANIFEST).read_bytes() == manifest_before


def test_native_escaped_controls_survive_managed_update(tmp_path):
    core, source, target, config = previous_projection(tmp_path)
    (target / 'config.toml').write_text(config + '\n[tui]\n"\\u007f" = "\\u007f"\n')
    core.project(source, target)
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    core.project(source, target)
    assert tomllib.loads((target / 'config.toml').read_text())['tui']['\x7f'] == '\x7f'


@pytest.mark.parametrize('fault', ['fingerprint', 'coverage'])
def test_invalid_journal_is_rejected_before_publication(tmp_path, monkeypatch, fault):
    core, source, target, config = previous_projection(tmp_path)
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    def interrupt(*args):
        raise RuntimeError('before publication')
    monkeypatch.setattr(core, 'publish_entry', interrupt)
    with pytest.raises(RuntimeError):
        core.project(source, target)
    monkeypatch.undo()
    journal = target / core.JOURNAL
    metadata = json.loads(journal.read_text())
    if fault == 'fingerprint':
        metadata['config_owned_sha256'] = '0' * 64
    else:
        metadata['manifest']['agents/extra.toml'] = '0' * 64
    journal.write_text(json.dumps(metadata))
    before = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):
        core.recover(target)
    assert {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()} == before


@pytest.mark.parametrize('interleave', ['preflight', 'publication'])
def test_recovery_detects_intervening_native_config_write(tmp_path, monkeypatch, interleave):
    core, source, target, config = previous_projection(tmp_path)
    (source / 'config.toml').write_text(config.replace('"managed"', '"updated"'))
    publish = core.publish_entry
    def stop(*args):
        raise RuntimeError('before publication')
    monkeypatch.setattr(core, 'publish_entry', stop)
    with pytest.raises(RuntimeError):
        core.project(source, target)
    monkeypatch.undo()
    native = '\n[tui]\nscreen_reader_detection_done = true\n'
    wrote = False
    if interleave == 'preflight':
        recovery_digest = core.recovery_digest
        def interleaved_digest(path):
            nonlocal wrote
            if path == target / 'AGENTS.md' and not wrote:
                (target / 'config.toml').write_text(config + native)
                wrote = True
            return recovery_digest(path)
        monkeypatch.setattr(core, 'recovery_digest', interleaved_digest)
    else:
        def interleaved_publish(staged, current):
            nonlocal wrote
            publish(staged, current)
            if current == target / 'config.toml':
                current.write_text(current.read_text() + native)
                wrote = True
        monkeypatch.setattr(core, 'publish_entry', interleaved_publish)
    with pytest.raises(ValueError):
        core.recover(target)
    assert wrote
    assert (target / 'config.toml').read_text().endswith(native)
    assert (target / core.JOURNAL).exists()
