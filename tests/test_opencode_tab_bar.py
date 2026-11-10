"""INT-083 uses disposable CLI config, never installed owner preferences."""
import json

import pytest

from test_opencode_v2_control_plane import project
from test_portable_distribution import data


def values(remote, mode):
    selected = data(state_root='', remote_user_environment=remote)
    selected['chezmoi'] = {'os': 'linux' if remote else 'darwin',
                          'arch': 'amd64' if remote else 'arm64'}
    selected['dotfiles_ai']['opencode']['tab_bar_mode'] = mode
    return selected


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('mode', ['off', 'on', 'auto', ''])
def test_tab_mode_owns_only_selected_key_and_reapply_is_stable(tmp_path, remote, mode):
    target = tmp_path / '.config/opencode/cli.json'
    target.parent.mkdir(parents=True)
    original = {'tabs': {'mode': 'on', 'scope': 'global', 'layout': 'vertical',
                         'indicators': 'numbers', 'enabled': True}, 'local': {'retain': [1, None]}}
    target.write_text(json.dumps(original))
    selected = values(remote, mode)
    result = project(tmp_path, 'cli.json', selected)
    assert result['tabs'] == {**original['tabs'], 'mode': mode or 'on'}
    assert result['local'] == original['local']
    assert project(tmp_path, 'cli.json', selected) == result
    assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('mode', ['unsupported', False, 0, [], {}])
def test_invalid_tab_mode_refuses_without_destination_write(tmp_path, remote, mode):
    target = tmp_path / '.config/opencode/cli.json'
    target.parent.mkdir(parents=True)
    original = '{"tabs":{"mode":"auto"},"local":"preserve"}\n'
    target.write_text(original)
    with pytest.raises(AssertionError):
        project(tmp_path, 'cli.json', values(remote, mode))
    assert target.read_text() == original


@pytest.mark.parametrize('tabs', [None, False, 'local', []])
def test_explicit_mode_rejects_non_object_tabs_without_overwrite(tmp_path, tabs):
    target = tmp_path / '.config/opencode/cli.json'
    target.parent.mkdir(parents=True)
    original = json.dumps({'tabs': tabs, 'local': [1]})
    target.write_text(original)
    with pytest.raises(AssertionError):
        project(tmp_path, 'cli.json', values(True, 'off'))
    assert target.read_text() == original


def test_empty_mode_leaves_tabs_absent_when_unconfigured(tmp_path):
    assert 'tabs' not in project(tmp_path, 'cli.json', values(True, ''))


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('mode', ['auto', 'on', 'off'])
def test_explicit_mode_creates_only_its_tab_key_when_unconfigured(tmp_path, remote, mode):
    assert project(tmp_path, 'cli.json', values(remote, mode))['tabs'] == {'mode': mode}
