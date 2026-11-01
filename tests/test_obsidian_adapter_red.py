"""Regression: unattended input capture requires both canonical roots."""
import importlib.util
from pathlib import Path
import pytest


def test_missing_roots_cannot_become_empty_projection(tmp_path):
    source = Path(__file__).parents[1] / 'dot_local/share/pm-kernel/obsidian_workbench.py'
    assert source.is_file(), 'Missing safe automation adapter'
    spec = importlib.util.spec_from_file_location('obsidian_adapter_red', source)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    lab = tmp_path / 'lab'; lab.mkdir()
    (lab / 'workbench.py').write_text('')
    vault = lab / 'vault'; vault.mkdir(); (vault / 'Records').mkdir()
    config = module.Config.from_dict(dict(lab_root=str(lab),vault_path=str(vault),state_root=str(tmp_path/'state'),python='/usr/bin/python3',obsidian_cli='/bin/true',vault_name='test',api_url='http://127.0.0.1:4202/api',reports={'Views/Test.md':1}))
    with pytest.raises(module.SafeFailure, match='source_unavailable'):
        module.capture(config)
