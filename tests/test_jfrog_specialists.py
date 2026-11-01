"""JFrog import completeness, narrow routing and inert deployment contracts."""
import json
import re
import subprocess
from pathlib import Path

from test_opencode_control_plane import ROOT

SKILLS = ROOT / 'dot_agents/skills'
NAMES = {'jfrog', 'jfrog-setup-package-managers', 'jfrog-package-curation',
         'jfrog-reference-architecture', 'jfrog-ai-catalog', 'jfrog-init',
         'jfrog-mcp-management'}
PIN = 'e555af53c3f5ead14fcafb009380e76d3ddf17d1'


def test_whole_jfrog_collection_has_one_reviewed_immutable_origin():
    inventory = json.loads((SKILLS / 'dbsctr/references/specialist-sources/sources.lock.json').read_text())
    records = {p['name']: p for p in inventory['packages'] if p['name'] in NAMES}
    assert records.keys() == NAMES
    for name, record in records.items():
        assert record['commit'] == PIN
        assert record['upstream_url'] == 'https://github.com/jfrog/jfrog-skills'
        assert record['upstream_path'] == 'skills/' + name
        assert record['license'] == 'Apache-2.0'
        assert 'references/upstream-workflow.md' in record['files']
        assert len((SKILLS / name / 'SKILL.md').read_bytes()) <= 6000


def test_jfrog_routing_uses_existing_platform_owner():
    router = (SKILLS / 'dbsctr/references/platform-specialists.md').read_text()
    for name in NAMES:
        assert '`' + name + '`' in router
    for module in ('python.md', 'cloud.md', 'shell.md'):
        assert 'jfrog-mcp-management' not in (SKILLS / 'dbsctr/modules' / module).read_text()
    qa = (SKILLS / 'qa/SKILL.md').read_text()
    assert 'configured JFrog Xray' in qa
    assert '`jfrog`' in qa


def test_upstream_helper_resources_parse_without_execution():
    roots = [SKILLS / name for name in NAMES]
    resources = [p for root in roots for p in root.rglob('*') if p.suffix in {'.mjs', '.sh'}]
    assert len(resources) == 40
    for path in resources:
        command = ['node', '--check', str(path)] if path.suffix == '.mjs' else ['/bin/bash', '-n', str(path)]
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode == 0, (path, result.stderr)


def test_node_helpers_retain_closed_local_dependencies():
    count = 0
    for name in NAMES:
        for source in (SKILLS / name).rglob('*.mjs'):
            for specifier in re.findall(r"(?m)^(?:import|export)\s+(?:[^;]+?\s+from\s+)?[\"']([^\"']+)", source.read_text()):
                if specifier.startswith('node:'):
                    continue
                assert specifier.startswith('.'), (source, specifier)
                target = (source.parent / specifier).resolve()
                assert target.is_relative_to(SKILLS.resolve()) and target.is_file(), (source, specifier)
                count += 1
    assert count == 58
