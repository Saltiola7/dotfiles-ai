"""Retained comparison admission without compiler, agent, provider, or VM calls."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path

import pytest

from test_openshell_guest_agent_build import build, retained, source  # noqa: F401
from test_openshell_guest_agent_runtime import runtime  # noqa: F401
from test_openshell_guest_full_cargo import elf


BASE = Path(__file__).parent / 'fixtures/openshell_runtime'


def append_resume(module):
    path = BASE / 'guest_agent_resume.py'
    assert path.is_file(), 'retained agent verifier absent: intended red'
    exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)


@pytest.fixture
def built(build, monkeypatch):
    module, work, _, payload = build
    prepared = module.agent_build_prepare(payload)
    exec(compile((BASE/'guest_cargo_artifact.py').read_text(), 'artifact', 'exec'), module.__dict__)
    append_resume(module)
    release = work/'full-target-1/release'
    (release/'deps').mkdir(parents=True)
    binary = release/'openshell-agent-filter-probe'
    binary.write_bytes(elf()); binary.chmod(0o500)
    report = {**prepared, 'status': 'agent_fixture_built',
              'binary_sha256': hashlib.sha256(elf()).hexdigest(), 'binary_bytes': len(elf()),
              'binary_layout': {'link_count': 1, 'companion': None}, 'static_arm64': True}
    verifier = module.verify_static_arm64

    def verify_descriptor(path):
        assert str(path).startswith('/proc/self/fd/')
        fd = int(path.name)

        class DescriptorPath:
            def open(self, mode):
                duplicate = os.dup(fd)
                os.lseek(duplicate, 0, os.SEEK_SET)
                return os.fdopen(duplicate, mode)

        return verifier(DescriptorPath())

    monkeypatch.setattr(module, 'verify_static_arm64', verify_descriptor)
    monkeypatch.setattr(module, 'command', lambda *a, **k: pytest.fail('resume executed a command'))
    return module, work, {'agent_build_report': report}, binary


@pytest.mark.parametrize('links', [1, 2])
def test_retained_fixture_verifies_exact_sources_binary_and_alias_without_execution(built, links):
    module, _, payload, binary = built
    if links == 2:
        companion = 'openshell_agent_filter_probe-0123456789abcdef'
        os.link(binary, binary.parent/'deps'/companion)
        payload['agent_build_report']['binary_layout'] = {'link_count': 2, 'companion': companion}
    before = deepcopy(payload)
    observed = module.agent_build_verify(payload)
    assert observed == {**payload['agent_build_report'], 'status': 'agent_fixture_verified'}
    assert payload == before
    assert binary.read_bytes() == elf()


@pytest.mark.parametrize('change', ['hash', 'size', 'layout', 'static', 'status', 'extra',
                                   'generation', 'schema', 'enabled', 'binary_size_type', 'link_type'])
def test_retained_fixture_rejects_changed_or_malformed_historical_identity(built, change):
    module, _, payload, _ = built
    report = payload['agent_build_report']
    if change == 'hash': report['binary_sha256'] = '0'*64
    elif change == 'size': report['binary_bytes'] += 1
    elif change == 'layout': report['binary_layout'] = {'link_count': 2, 'companion': 'openshell_agent_filter_probe-0123456789abcdef'}
    elif change == 'static': report['static_arm64'] = False
    elif change == 'status': report['status'] = 'agent_fixture_verified'
    elif change == 'extra': report['other'] = None
    elif change == 'generation': report['generation'] = True
    elif change == 'schema': report['schema_version'] = True
    elif change == 'enabled': report['session_enabled'] = 0
    elif change == 'binary_size_type': report['binary_bytes'] = float(report['binary_bytes'])
    else: report['binary_layout']['link_count'] = True
    with pytest.raises(RuntimeError): module.agent_build_verify(payload)


@pytest.mark.parametrize('change', ['source', 'source_extra', 'binary', 'binary_symlink', 'alias', 'retransmit'])
def test_retained_fixture_rejects_current_source_or_artifact_drift(built, change):
    module, work, payload, binary = built
    if change == 'source':
        path = work/'agent-fixture-1/src/main.rs'; path.chmod(0o600); path.write_text('changed')
    elif change == 'source_extra': (work/'agent-fixture-1/build.rs').write_text('extra')
    elif change == 'binary': binary.chmod(0o700); binary.write_bytes(b'changed'); binary.chmod(0o500)
    elif change == 'binary_symlink':
        raw = binary.read_bytes(); binary.unlink(); (work/'other').write_bytes(raw); binary.symlink_to(work/'other')
    elif change == 'alias': os.link(binary, binary.parent/'deps/unknown-alias')
    else: payload['fixture_files'] = {}
    with pytest.raises(RuntimeError): module.agent_build_verify(payload)


@pytest.mark.parametrize('body', [elf(interpreter='/lib/ld.so'), elf(needed='libc.so'), elf(machine=62)],
                         ids=['interpreter', 'dynamic_dependency', 'wrong_architecture'])
def test_historical_hash_match_does_not_replace_static_arm64_validation(built, body):
    module, _, payload, binary = built
    binary.chmod(0o700); binary.write_bytes(body); binary.chmod(0o500)
    payload['agent_build_report'].update(binary_sha256=hashlib.sha256(body).hexdigest(), binary_bytes=len(body))
    with pytest.raises(RuntimeError, match='harness_'): module.agent_build_verify(payload)


def test_source_changed_during_artifact_verification_is_rejected(built, monkeypatch):
    module, work, payload, _ = built
    original = module.verify_static_arm64

    def mutate(path):
        value = original(path)
        source_file = work/'agent-fixture-1/src/main.rs'
        source_file.chmod(0o600); source_file.write_text('changed after source admission')
        return value

    monkeypatch.setattr(module, 'verify_static_arm64', mutate)
    with pytest.raises(RuntimeError, match='agent_build_'): module.agent_build_verify(payload)


@pytest.fixture
def fresh(runtime, monkeypatch):
    exec(compile((BASE/'guest_cargo_artifact.py').read_text(), 'artifact', 'exec'), runtime.__dict__)
    append_resume(runtime)
    prepared = runtime.agent_cases_prepare({})
    monkeypatch.setattr(runtime, 'agent_cases_prepare', lambda *a: pytest.fail('resume recreated cases'))
    monkeypatch.setattr(runtime, 'agent_case', lambda *a: pytest.fail('resume launched an agent'))
    return runtime, prepared


def test_all_cases_verify_current_state_without_requiring_old_allocation(fresh, monkeypatch):
    module, prepared = fresh
    current = prepared['case_state_bytes'] + 4096
    monkeypatch.setattr(module, 'agent_state_bytes', lambda: current)
    observed = module.agent_cases_verify({})
    assert observed == {**prepared, 'status': 'agent_cases_verified', 'case_state_bytes': current}


@pytest.mark.parametrize('change', ['root_extra', 'root_missing', 'root_symlink', 'case_symlink',
                                   'case_file', 'root_mode', 'case_mode', 'config', 'state', 'sentinel'])
def test_resume_refuses_any_unselected_or_changed_case_entry(fresh, change):
    module, _ = fresh
    root = module.WORK/'agent-cases-1'; case = root/module.AGENT_CASES[0]
    if change == 'root_extra': (root/'unknown').mkdir()
    elif change == 'root_missing': case.rename(root/'unselected')
    elif change == 'root_symlink':
        root.rename(module.WORK/'old-cases'); root.symlink_to(module.WORK/'old-cases')
    elif change in ('case_symlink', 'case_file'):
        case.rename(module.WORK/'old-case')
        if change == 'case_symlink': case.symlink_to(module.WORK/'old-case')
        else: case.write_text('not a directory')
    elif change == 'root_mode': root.chmod(0o755)
    elif change == 'case_mode': (case/'home').chmod(0o755)
    elif change == 'config': (case/'codex/config.toml').write_text('changed')
    elif change == 'state': (case/'home/auth.json').write_text('synthetic state')
    else: (root/'opencode-rg-patched/workspace/sentinel.txt').write_text('changed')
    with pytest.raises(RuntimeError): module.agent_cases_verify({})


@pytest.mark.parametrize('check', ['agent_platform', 'agent_capacity', 'agent_state_bytes'])
def test_case_verification_propagates_platform_capacity_and_state_refusals(fresh, monkeypatch, check):
    module, _ = fresh

    def refuse():
        raise RuntimeError('synthetic admission refusal')

    monkeypatch.setattr(module, check, refuse)
    with pytest.raises(RuntimeError, match='synthetic admission refusal'): module.agent_cases_verify({})
