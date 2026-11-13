"""Pure native applicability data and the shared segment matcher; no I/O."""
from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import re

from . import core as c


def path_matches(pattern: str, path: str) -> bool:
    """Segment DP preserves the existing diagnostic matcher's semantics."""
    pieces = path.split('/')
    positions = {0}
    for segment in pattern.split('/'):
        if segment == '**':
            positions = set(range(min(positions), len(pieces) + 1)) if positions else set()
        else:
            positions = {i + 1 for i in positions if i < len(pieces) and fnmatch.fnmatchcase(pieces[i], segment)}
    return len(pieces) in positions


def path_value(value: object) -> str:
    text = c._text(value)
    c._require(0 < len(text) <= 1024 and not text.startswith('/') and '\\' not in text
        and not any(ord(ch) < 32 or ord(ch) == 127 for ch in text)
        and all(part not in {'', '.', '..'} for part in text.split('/')), 'ci_path_invalid')
    return text


def pattern_value(value: object) -> str:
    text = path_value(value)
    c._require(re.fullmatch(r'[A-Za-z0-9_./* -]+', text) is not None
        and all('**' not in part or part == '**' for part in text.split('/')), 'ci_pattern_unsupported')
    return text


@dataclass(frozen=True, slots=True)
class MappingBinding:
    mapping_path: str
    mapping_digest: str

    def __post_init__(self) -> None:
        path_value(self.mapping_path)
        c._require(self.mapping_path.endswith('.json') and len(self.mapping_path) <= 256
            and not any(part in {'.git', '.dbsctr'} for part in self.mapping_path.split('/'))
            and not any(ch in self.mapping_path for ch in '*?[]'), 'ci_mapping_path')
        c._digest(self.mapping_digest)


@dataclass(frozen=True, slots=True)
class Predicate:
    kind: str
    value: str | tuple[str, ...]

    def __post_init__(self) -> None:
        c._require(isinstance(self.kind, str) and self.kind in {'event', 'target_branch', 'paths', 'actor_not'}, 'ci_predicate_kind')
        if self.kind == 'paths':
            c._tuple(self.value, str, 128, 1)
            assert isinstance(self.value, tuple)
            c._require(len(set(self.value)) == len(self.value), 'ci_pattern_duplicate')
            for pattern in self.value: pattern_value(pattern)
        else:
            c._require(type(self.value) is str, 'ci_predicate_value')
            assert isinstance(self.value, str)
            if self.kind == 'event':
                c._require(self.value in {'pull_request', 'push', 'workflow_dispatch', 'schedule'}, 'ci_event_unsupported')
            elif self.kind == 'target_branch':
                c._branch(self.value)
            else:
                c._require(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]{0,99}(?:\[bot\])?', self.value) is not None, 'ci_actor_invalid')


@dataclass(frozen=True, slots=True)
class Rule:
    context: str
    app_id: int
    predicates: tuple[Predicate, ...]

    def __post_init__(self) -> None:
        c._require(isinstance(self.context, str) and 0 < len(self.context) <= 256
            and all(32 <= ord(ch) < 127 for ch in self.context), 'ci_context_invalid')
        c._integer(self.app_id)
        c._tuple(self.predicates, Predicate, 32)
        c._require(len(set(self.predicates)) == len(self.predicates), 'ci_predicate_duplicate')


def parse_mapping(value: object) -> tuple[Rule, ...]:
    data = c._object(value, 'schema_version producers')
    c._require(c._int(data['schema_version']) == 1, 'ci_mapping_schema')
    result = []
    for raw in c._array(data['producers'], 480):
        row = c._object(raw, 'context app_id all')
        predicates = []
        for raw_predicate in c._array(row['all'], 32):
            predicate = c._object(raw_predicate, 'kind value')
            kind = c._text(predicate['kind'])
            checked = (tuple(c._text(item) for item in c._array(predicate['value'], 128))
                       if kind == 'paths' else c._text(predicate['value']))
            predicates.append(Predicate(kind, checked))
        result.append(Rule(c._text(row['context']), c._int(row['app_id']), tuple(predicates)))
    c._require(len({(rule.context, rule.app_id) for rule in result}) == len(result), 'ci_producer_duplicate')
    return tuple(result)


@dataclass(frozen=True, slots=True)
class CandidateScope:
    base: str
    head: str
    paths: tuple[str, ...]
    commit_count: int

    def __post_init__(self) -> None:
        c._oid(self.base)
        c._oid(self.head)
        c._require(len(self.base) == len(self.head), 'mixed_oid_formats')
        # Negative provider filtering is supported only when the complete Git
        # closure fits within its documented comparison limits.
        c._tuple(self.paths, str, 3000)
        c._integer(self.commit_count)
        c._require(self.commit_count < 1000, 'ci_scope_commit_limit')
        c._require(len(set(self.paths)) == len(self.paths) and tuple(sorted(self.paths)) == self.paths, 'ci_scope_paths')
        for path in self.paths: path_value(path)
