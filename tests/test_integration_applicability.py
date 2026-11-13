"""Conditional omission requires native candidate proof, never missing labels."""
from __future__ import annotations

from dataclasses import asdict, replace
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING, TypedDict

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'private_dot_config/dotfiles-ai'))
from integration_coordinator import core as c, github as g, controller as h
from test_integration_controller import config
from test_integration_github import QualifiedGitHub, check_plan, ready_candidate

if TYPE_CHECKING:
    from integration_coordinator import ci_mapping as m


def wire(version: int = 2) -> dict:
    value = {'schema_version': version, **json.loads(json.dumps(asdict(check_plan())))}
    if version == 2:
        value['applicability'] = {'mapping_path': '.github/dbsctr-checks.json', 'mapping_digest': '7' * 64}
    return value


def test_static_v1_plan_and_policy_identity_remain_exact():
    value = wire(1)
    expected = hashlib.sha256(json.dumps({key: value[key] for key in ('producers', 'codeql')},
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    plan = g.parse_check_plan(value)
    assert plan.digest == expected
    assert h.parse_config(json.dumps(h._config_data(config())).encode()) == config()


def test_v2_plan_roundtrips_without_changing_hosted_schema():
    value = wire()
    plan = g.parse_check_plan(value)
    assert plan.digest != g.parse_check_plan(wire(1)).digest
    proposed = replace(config(), check_plan=plan)
    assert proposed.enrollment is not None
    selected = replace(proposed, enrollment=replace(proposed.enrollment, policy_digest=h.policy_identity(proposed)))
    encoded = h._config_data(selected)
    assert encoded['schema_version'] == 2 and json.loads(json.dumps(encoded['check_plan'])) == value
    assert h.parse_config(json.dumps(encoded).encode()) == selected


@pytest.mark.parametrize('change', ['boolean_version', 'extra', 'missing', 'unsafe_path', 'bad_digest'])
def test_v2_plan_rejects_open_or_unbound_authority(change):
    value = wire()
    if change == 'boolean_version': value['schema_version'] = True
    elif change == 'extra': value['unreviewed'] = True
    elif change == 'missing': value.pop('applicability')
    elif change == 'unsafe_path': value['applicability']['mapping_path'] = '../escape.json'
    else: value['applicability']['mapping_digest'] = '0'
    with pytest.raises(c.Invalid): g.parse_check_plan(value)


class ScopeProof:
    def __init__(self, original: g.ProofPort, paths: tuple[str, ...]):
        self.original, self.paths = original, paths

    def prove_refresh(self, source, head, base):
        return self.original.prove_refresh(source, head, base)

    def prove_delivery(self, source, projection, merge_oid):
        return self.original.prove_delivery(source, projection, merge_oid)

    def excludes_root(self, root, heads):
        return self.original.excludes_root(root, heads)

    def candidate_scope(self, base: str, head: str) -> m.CandidateScope:
        from integration_coordinator import ci_mapping as m
        return m.CandidateScope(base, head, self.paths, 1)


class PredicateWire(TypedDict):
    kind: str
    value: str | list[str]


class MappingRow(TypedDict):
    context: str
    app_id: int
    all: list[PredicateWire]


class MappingWire(TypedDict):
    schema_version: int
    producers: list[MappingRow]


class ConditionalGitHub(QualifiedGitHub):
    def __init__(self, paths=('docs/usage.md',), predicate: PredicateWire | None = None):
        super().__init__()
        assert self.proof is not None
        self.original_proof = self.proof
        self.proof = ScopeProof(self.proof, paths)
        self.current: g.PullFacts = self.observe_pr(5)
        self.mapping: MappingWire = {'schema_version': 1, 'producers': [{'context': 'optional', 'app_id': 15368,
            'all': [predicate or {'kind': 'paths', 'value': ['service/**']}]}]}
        optional = copy.deepcopy(wire(1)['producers'][0])
        optional['binding'].update(context='optional', workflow_id=62, workflow_path='.github/workflows/optional.yml')
        optional['workflow_digest'] = hashlib.sha256(b'optional workflow').hexdigest()
        optional['receipt'] = None
        value = wire()
        value['producers'].append(optional)
        value['applicability']['mapping_digest'] = hashlib.sha256(self.mapping_bytes()).hexdigest()
        self.plan_wire = value
        self.plan = g.parse_check_plan(value)
        self.optional_runs = []
        self.optional_reads = 0
        self.actor_drift = False
        self.calls = []
        self.mapping_drift = False
        self.workflow_drift = False

    def mapping_bytes(self):
        return json.dumps(self.mapping, sort_keys=True).encode()

    def file_at(self, head, path):
        if path == '.github/dbsctr-checks.json':
            return b'{}' if self.mapping_drift and head != self.current.base else self.mapping_bytes()
        if path == '.github/workflows/optional.yml':
            return b'changed workflow' if self.workflow_drift else b'optional workflow'
        return super().file_at(head, path)

    def get(self, path):
        if path == 'actions/runs/72':
            self.optional_reads += 1
            value = dict(self.optional_runs[0])
            # Change the final fence after the predicate's original snapshot.
            if self.actor_drift and self.optional_reads > 1: value['run_attempt'] += 1
            return value
        if path == 'check-runs/82':
            value = copy.deepcopy(self.check)
            value.update(id=82, name='optional', conclusion='skipped', check_suite={'id': self.run['check_suite_id']})
            return value
        return super().get(path)

    def pages(self, path, key=None, *, limit=4096):
        self.calls.append(path)
        if path.startswith('actions/workflows/62/runs?'): return [dict(row) for row in self.optional_runs]
        if path == 'actions/runs/72/attempts/2/jobs':
            value = dict(self.job)
            value.update(id=889, name='optional', run_id=72, conclusion='skipped', check_run_url='https://api.github.com/repos/example/repo/check-runs/82')
            return [value]
        return super().pages(path, key, limit=limit)


def test_negative_path_proof_skips_only_conditional_producer_and_is_bound():
    first = ConditionalGitHub()
    candidate = ready_candidate(first)
    first.current = first.observe_pr(5)
    result = first.qualify(candidate, 5)
    assert len(result.evidence) == 1
    assert not any('actions/runs/72' in path for path in first.calls)
    other = ConditionalGitHub(paths=('docs/other.md',))
    other.current = other.observe_pr(5)
    other_result = other.qualify(ready_candidate(other), 5)
    assert result.evidence[0].producer_digest != other_result.evidence[0].producer_digest


@pytest.mark.parametrize('change', ['applicable_missing', 'mapping_drift', 'workflow_drift', 'required_condition', 'unknown_scope', 'actor_unproved'])
def test_no_negative_exemption_for_unproved_or_required_concern(change):
    api = ConditionalGitHub(paths=('service/code.py',) if change == 'applicable_missing' else ('docs/a.md',),
        predicate={'kind': 'actor_not', 'value': 'dependabot[bot]'} if change == 'actor_unproved' else None)
    api.current = api.observe_pr(5)
    if change == 'mapping_drift': api.mapping_drift = True
    if change == 'workflow_drift': api.workflow_drift = True
    if change == 'required_condition':
        api.mapping['producers'][0]['context'] = 'gate'
        api.plan_wire['applicability']['mapping_digest'] = hashlib.sha256(api.mapping_bytes()).hexdigest()
        api.plan = g.parse_check_plan(api.plan_wire)
    if change == 'unknown_scope': api.proof = api.original_proof
    with pytest.raises((c.Invalid, c.Unavailable)):
        api.qualify(ready_candidate(api), 5)


def optional_run(api, *, conclusion='skipped', actor='dependabot[bot]'):
    value = dict(api.run)
    value.update(id=72, workflow_id=62, path='.github/workflows/optional.yml',
        status='completed', conclusion=conclusion, actor={'id': 17, 'login': actor})
    return value


def test_observed_fallback_run_cannot_be_ignored_by_negative_paths():
    api = ConditionalGitHub()
    api.current = api.observe_pr(5)
    api.optional_runs = [optional_run(api, conclusion='failure')]
    with pytest.raises(g.FailedChecks): api.qualify(ready_candidate(api), 5)


def test_negative_actor_uses_native_causal_actor_and_fences_current_attempt():
    api = ConditionalGitHub(predicate={'kind': 'actor_not', 'value': 'Dependabot[bot]'})
    api.current = api.observe_pr(5)
    api.optional_runs = [optional_run(api)]
    result = api.qualify(ready_candidate(api), 5)
    assert len(result.evidence) == 1 and result.evidence[0].kind == 'check'
    api.optional_reads = 0
    api.actor_drift = True
    with pytest.raises(c.Unavailable, match='attempt_changed'):
        api.qualify(ready_candidate(api), 5)


def test_late_native_run_invalidates_negative_trigger_proof():
    class AppearingRun(ConditionalGitHub):
        def pages(self, path, key=None, *, limit=4096):
            if path.startswith('actions/workflows/62/runs?') and path in self.calls:
                self.optional_runs = [optional_run(self, conclusion='failure')]
            return super().pages(path, key, limit=limit)
    api = AppearingRun()
    api.current = api.observe_pr(5)
    with pytest.raises(c.Unavailable, match='run_appeared'):
        api.qualify(ready_candidate(api), 5)


def test_new_run_cannot_replace_the_actor_predicate_snapshot():
    class NewRun(ConditionalGitHub):
        def get(self, path):
            if path == 'actions/runs/73': return dict(self.optional_runs[-1])
            if path == 'check-runs/83':
                value = copy.deepcopy(self.check)
                value.update(id=83, name='optional', conclusion='skipped', check_suite={'id': 999})
                return value
            value = super().get(path)
            if path == 'actions/runs/72':
                newer = optional_run(self, actor='human-maintainer')
                newer.update(id=73, check_suite_id=999)
                self.optional_runs.append(newer)
            return value

        def pages(self, path, key=None, *, limit=4096):
            if path == 'actions/runs/73/attempts/2/jobs':
                value = dict(self.job)
                value.update(id=890, name='optional', run_id=73, conclusion='skipped',
                    check_run_url='https://api.github.com/repos/example/repo/check-runs/83')
                return [value]
            return super().pages(path, key, limit=limit)

    api = NewRun(predicate={'kind': 'actor_not', 'value': 'dependabot[bot]'})
    api.optional_runs = [optional_run(api)]
    with pytest.raises(c.Unavailable, match='attempt_changed'):
        api.qualify(ready_candidate(api), 5)


@pytest.mark.parametrize('predicate', [
    {'kind': 'unknown', 'value': 'x'}, {'kind': 'paths', 'value': ['!service/**']},
    {'kind': 'paths', 'value': ['service/[ab].py']}, {'kind': 'paths', 'value': ['../escape']},
    {'kind': 'paths', 'value': []}, {'kind': 'actor_not', 'value': ''},
    {'kind': 'event', 'value': 'pull_request', 'extra': True},
])
def test_mapping_predicates_are_closed_and_unsupported_patterns_never_exempt(predicate):
    from integration_coordinator import ci_mapping as m
    value = {'schema_version': 1, 'producers': [{'context': 'optional', 'app_id': 15368, 'all': [predicate]}]}
    with pytest.raises(c.Invalid): m.parse_mapping(value)


def test_duplicate_and_unbound_mapping_rows_refuse_qualification():
    for context in ('unknown', 'optional'):
        api = ConditionalGitHub()
        api.current = api.observe_pr(5)
        if context == 'unknown': api.mapping['producers'][0]['context'] = context
        else: api.mapping['producers'].append(copy.deepcopy(api.mapping['producers'][0]))
        api.plan_wire['applicability']['mapping_digest'] = hashlib.sha256(api.mapping_bytes()).hexdigest()
        api.plan = g.parse_check_plan(api.plan_wire)
        with pytest.raises((c.Invalid, c.Unavailable)): api.qualify(ready_candidate(api), 5)


def test_native_receipt_bindings_can_cover_pr_and_ordered_parents():
    assert g.IdentityField(('pr_number',), 'pr_number').fact == 'pr_number'
    assert g.IdentityField(('tested_parents',), 'tested_parents').fact == 'tested_parents'


from hypothesis import given, settings, strategies as st


@settings(max_examples=40)
@given(st.binary(min_size=32, max_size=32), st.text(alphabet='abcxyz012-_', min_size=1, max_size=24))
def test_conditional_plan_json_roundtrip_and_identity_are_stable(digest, filename):
    value = wire()
    value['applicability'] = {'mapping_path': '.github/' + filename + '.json', 'mapping_digest': digest.hex()}
    plan = g.parse_check_plan(value)
    reparsed = g.parse_check_plan(json.loads(json.dumps(g.check_plan_data(plan))))
    assert reparsed == plan and reparsed.digest == plan.digest
