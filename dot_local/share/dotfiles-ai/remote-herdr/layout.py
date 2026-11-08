"""Pure, bounded structural adapters for Herdr TUI v3 and app documents.

No files, processes, environment, history, or credentials are read. All public
functions raise ValueError on unsupported/lossy input and return fresh JSON data.
Canonical pane numbering follows pane-list position, independently of BSP order.
Native pane numbers are sorted numerically when assigning canonical positions.
Shapes verified against herdrdev/herdr 2ecf19a (persist/snapshot.rs,
layout.rs) and herdrdev/herdr-app 93b097 (mirror.rs, layout.rs).
"""

import json
import math
import re
import shlex
from typing import NoReturn


MAX_BYTES = 1024 * 1024
MAX_SPACES = 256
MAX_TABS = 1024
MAX_PANES = 4096
MAX_DEPTH = 32
_SESSION = re.compile(r'ses_[A-Za-z0-9]+\Z')
_TERMINAL = re.compile(r't[0-9a-z]+\Z')


def _fail(message: str) -> NoReturn:
    # Never include untrusted values (which may contain credentials) in errors.
    raise ValueError(message)


def _string(value, limit=4096):
    if type(value) is not str or len(value) > limit or '\0' in value:
        _fail('invalid or overlong string')
    try:
        value.encode('utf-8')
    except UnicodeError:
        _fail('invalid Unicode string')
    return value


def _json_copy(value):
    """Bound the complete input, including fields that adapters intentionally omit.

    Incremental compact-JSON accounting avoids serializing an unbounded object.
    The generic nesting bound permits 32 BSP levels plus their JSON wrappers.
    Cycles are rejected by this bound without invoking arbitrary object methods.
    """
    remaining = MAX_BYTES

    def visit(item, depth):
        nonlocal remaining
        if depth > 100:
            _fail('JSON nesting exceeds limit')
        kind = type(item)
        if kind is dict or kind is list:
            remaining -= 2 + max(0, len(item) - 1)
            if kind is dict:
                remaining -= len(item)  # colons
            if remaining < 0:
                _fail('JSON exceeds 1 MiB')
            if kind is list:
                return [visit(child, depth + 1) for child in item]
            result = {}
            for key, child in item.items():
                _string(key)
                visit(key, depth + 1)
                result[key] = visit(child, depth + 1)
            return result
        if kind is str:
            _string(item)
        elif kind is float:
            if not math.isfinite(item):
                _fail('nonfinite JSON number')
        elif kind is int:
            if item.bit_length() > 64:
                _fail('JSON integer exceeds supported range')
        elif item is not None and kind is not bool:
            _fail('expected plain JSON data')
        remaining -= len(json.dumps(item, ensure_ascii=False, allow_nan=False).encode('utf-8'))
        if remaining < 0:
            _fail('JSON exceeds 1 MiB')
        return item

    return visit(value, 0)


def _object(value, keys=None):
    if type(value) is not dict or (keys is not None and set(value) != set(keys)):
        _fail('invalid object fields')
    return value


def _list(value, maximum):
    if type(value) is not list or len(value) > maximum:
        _fail('invalid or oversized list')
    return value


def _path(value):
    _string(value)
    if not value.startswith('/') or '..' in value.split('/'):
        _fail('directory must be absolute without parent traversal')
    return value


def _ratio(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 1:
        _fail('split ratio must be finite and strictly between zero and one')
    return float(value)


def _session(value):
    if not _SESSION.fullmatch(_string(value)):
        _fail('invalid OpenCode session identity')
    return value


def _index(value, upper):
    if type(value) is not int or not 0 <= value < upper:
        _fail('invalid pane reference')
    return value


def validate_plan(value):
    """Validate schema v1, return a defensive copy, never repair or prune input."""
    plan = _json_copy(value)
    _object(plan, ('schema_version', 'spaces'))
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        _fail('unsupported canonical schema version')
    sessions = set()
    pane_count = tab_count = 0
    for si, space in enumerate(_list(plan['spaces'], MAX_SPACES)):
        _object(space, ('name', 'directory', 'tabs'))
        _string(space['name'], 512)
        _path(space['directory'])
        for ti, tab in enumerate(_list(space['tabs'], MAX_TABS)):
            tab_count += 1
            if tab_count > MAX_TABS:
                _fail('too many tabs')
            _object(tab, ('name', 'root', 'panes'))
            _string(tab['name'], 512)
            panes = _list(tab['panes'], MAX_PANES)
            pane_count += len(panes)
            if not panes or pane_count > MAX_PANES:
                _fail('empty tab or too many panes')
            keys = set()
            for pi, pane in enumerate(panes):
                _object(pane, ('key', 'cwd', 'session_id'))
                if pane['key'] != f's{si}-t{ti}-p{pi}':
                    _fail('pane key does not match canonical position')
                keys.add(pane['key'])
                _path(pane['cwd'])
                if pane['session_id'] is not None:
                    session = _session(pane['session_id'])
                    if session in sessions:
                        _fail('duplicate OpenCode session identity')
                    sessions.add(session)
            referenced = set()

            def tree(node, depth):
                if depth > MAX_DEPTH:
                    _fail('BSP tree exceeds depth limit')
                _object(node)
                if set(node) == {'pane'}:
                    key = _string(node['pane'])
                    if key not in keys or key in referenced:
                        _fail('unknown or duplicate layout pane')
                    referenced.add(key)
                else:
                    _object(node, ('axis', 'ratio', 'children'))
                    if node['axis'] not in ('row', 'column'):
                        _fail('unsupported BSP axis')
                    node['ratio'] = _ratio(node['ratio'])
                    children = _list(node['children'], 2)
                    if len(children) != 2:
                        _fail('BSP splits require exactly two children')
                    for child in children:
                        tree(child, depth + 1)

            tree(tab['root'], 1)
            if referenced != keys:
                _fail('unreferenced panes')
    return plan


def _argv_session(value):
    if (type(value) is not list or len(value) != 3
            or value[:2] != ['opencode', '--session']):
        _fail('unsupported agent launch arguments')
    return _session(value[2])


def _native_session(pane):
    identities = []
    marked = False
    for field in ('agent_name', 'managed_agent_kind'):
        if pane.get(field) is not None:
            if pane[field] != 'opencode':
                _fail('unsupported agent identity')
            marked = True
    native = pane.get('agent_session')
    if native is not None:
        _object(native, ('source', 'agent', 'kind', 'value'))
        if (native['source'], native['agent'], native['kind']) != ('herdr:opencode', 'opencode', 'id'):
            _fail('unsupported native agent session')
        identities.append(_session(native['value']))
    argv = pane.get('launch_argv')
    if argv is not None:
        identities.append(_argv_session(argv))
    resume = pane.get('agent_resume')
    if resume is not None:
        _object(resume, ('source', 'agent', 'argv'))
        if (resume['source'], resume['agent']) != ('herdr:opencode', 'opencode'):
            _fail('unsupported native resume authority')
        identities.append(_argv_session(resume['argv']))
    if len(set(identities)) > 1:
        _fail('contradictory OpenCode session identities')
    if marked and not identities:
        _fail('agent has no explicit session identity')
    return identities[0] if identities else None


def _native_name(value):
    return '' if value is None else _string(value, 512)


def from_tui_snapshot(value):
    """Read TUI 0.9.5 snapshot v3; ignore non-layout metadata, never execute argv."""
    snapshot = _json_copy(value)
    _object(snapshot)
    if type(snapshot.get('version')) is not int or snapshot['version'] != 3:
        _fail('only TUI snapshot version 3 is supported')
    spaces = []
    tab_count = pane_count = 0
    seen_numbers = set()
    for si, workspace in enumerate(_list(snapshot.get('workspaces'), MAX_SPACES)):
        _object(workspace)
        space = {'name': _native_name(workspace.get('custom_name')),
                 'directory': _path(workspace.get('identity_cwd')), 'tabs': []}
        for ti, native_tab in enumerate(_list(workspace.get('tabs'), MAX_TABS)):
            tab_count += 1
            if tab_count > MAX_TABS:
                _fail('too many tabs')
            _object(native_tab)
            native_panes = _object(native_tab.get('panes'))
            pane_count += len(native_panes)
            if not native_panes or pane_count > MAX_PANES:
                _fail('empty tab or too many panes')
            for number in native_panes:
                if not re.fullmatch(r'0|[1-9][0-9]{0,9}', number) or int(number) > 0xffffffff:
                    _fail('invalid native pane number')
                if int(number) in seen_numbers:
                    _fail('duplicate global native pane number')
                seen_numbers.add(int(number))
            numbers = sorted(native_panes, key=int)
            mapping = {int(number): f's{si}-t{ti}-p{pi}' for pi, number in enumerate(numbers)}
            panes = []
            for number in numbers:
                pane = _object(native_panes[number])
                panes.append({'key': mapping[int(number)], 'cwd': _path(pane.get('cwd')),
                              'session_id': _native_session(pane)})

            def tree(node, depth):
                if depth > MAX_DEPTH:
                    _fail('BSP tree exceeds depth limit')
                _object(node)
                if set(node) == {'Pane'}:
                    number = node['Pane']
                    if type(number) is not int or number not in mapping:
                        _fail('unknown native layout pane')
                    return {'pane': mapping[number]}
                _object(node, ('Split',))
                split = _object(node['Split'], ('direction', 'ratio', 'first', 'second'))
                if split['direction'] not in ('Horizontal', 'Vertical'):
                    _fail('unsupported native split direction')
                return {'axis': 'row' if split['direction'] == 'Horizontal' else 'column',
                        'ratio': _ratio(split['ratio']), 'children': [
                            tree(split['first'], depth + 1), tree(split['second'], depth + 1)]}

            space['tabs'].append({'name': _native_name(native_tab.get('custom_name')),
                                  'root': tree(native_tab.get('layout'), 1), 'panes': panes})
        spaces.append(space)
    return validate_plan({'schema_version': 1, 'spaces': spaces})


def from_space_plan(value):
    """Read labelled ForkA plans. A space's first tab cwd is its directory.

    Old unlabelled tab-step arrays cannot preserve tab names and are refused.
    Splits target the last created pane; right/down preserve first/second order.
    Empty spaces lack a directory identity in this producer format and refuse.
    """
    source = _json_copy(value)
    spaces = []
    tab_count = pane_count = 0
    for si, native_space in enumerate(_list(source, MAX_SPACES)):
        _object(native_space)
        if native_space.get('missing') is not False:
            _fail('missing or unresolved space')
        if 'pruned' in native_space:
            if type(native_space['pruned']) is not int or native_space['pruned'] < 0:
                _fail('invalid pruned metadata')
        space = {'name': _string(native_space.get('label'), 512), 'directory': None, 'tabs': []}
        for ti, source_tab in enumerate(_list(native_space.get('tabs'), MAX_TABS)):
            tab_count += 1
            if tab_count > MAX_TABS:
                _fail('too many tabs')
            _object(source_tab, ('label', 'steps'))
            tab = {'name': _string(source_tab['label'], 512), 'root': None, 'panes': []}
            steps = _list(source_tab['steps'], MAX_PANES * 2)
            last_leaf = None
            for step in steps:
                _object(step)
                op = step.get('op')
                if op in ('tab', 'split'):
                    if op == 'tab':
                        _object(step, ('op', 'cwd'))
                        if tab['panes']:
                            _fail('tab step must be first and unique')
                    else:
                        _object(step, ('op', 'direction', 'ratio', 'cwd'))
                        if last_leaf is None or step['direction'] not in ('right', 'down'):
                            _fail('unsupported split or missing initial tab')
                    pane_count += 1
                    if pane_count > MAX_PANES:
                        _fail('too many panes')
                    key = f's{si}-t{ti}-p{len(tab["panes"])}'
                    cwd = _path(step['cwd'])
                    leaf: dict = {'pane': key}
                    tab['panes'].append({'key': key, 'cwd': cwd, 'session_id': None})
                    if op == 'tab':
                        tab['root'] = leaf
                        if space['directory'] is None:
                            space['directory'] = cwd
                    else:
                        if last_leaf is None:
                            _fail('unsupported split or missing initial tab')
                        old = dict(last_leaf)
                        last_leaf.clear()
                        last_leaf.update({'axis': 'row' if step['direction'] == 'right' else 'column',
                                          'ratio': _ratio(step['ratio']), 'children': [old, leaf]})
                    last_leaf = leaf
                elif op == 'resume':
                    _object(step, ('op', 'pane', 'command'))
                    index = _index(step['pane'], len(tab['panes']))
                    try:
                        argv = shlex.split(_string(step['command']), posix=True)
                    except ValueError:
                        _fail('invalid space-plan resume command')
                    session = _argv_session(argv)
                    if tab['panes'][index]['session_id'] is not None:
                        _fail('duplicate resume step')
                    tab['panes'][index]['session_id'] = session
                else:
                    _fail('unsupported space-plan step')
            space['tabs'].append(tab)
        if space['directory'] is None:
            _fail('space plan has no directory identity')
        spaces.append(space)
    return validate_plan({'schema_version': 1, 'spaces': spaces})


def to_tui_snapshot(plan):
    """Generate minimal complete v3 data, with neutral focus and no history."""
    plan = validate_plan(plan)
    workspaces = []
    next_number = 0
    for space in plan['spaces']:
        tabs = []
        for tab in space['tabs']:
            mapping = {pane['key']: next_number + pi for pi, pane in enumerate(tab['panes'])}
            next_number += len(tab['panes'])

            def tree(node):
                if 'pane' in node:
                    return {'Pane': mapping[node['pane']]}
                return {'Split': {'direction': 'Horizontal' if node['axis'] == 'row' else 'Vertical',
                                  'ratio': node['ratio'], 'first': tree(node['children'][0]),
                                  'second': tree(node['children'][1])}}

            panes = {}
            for pane in tab['panes']:
                native = {'cwd': pane['cwd']}
                session = pane['session_id']
                if session is not None:
                    native.update({'agent_name': 'opencode', 'managed_agent_kind': 'opencode',
                                   'agent_session': {'source': 'herdr:opencode', 'agent': 'opencode',
                                                     'kind': 'id', 'value': session},
                                   'launch_argv': ['opencode', '--session', session]})
                panes[str(mapping[pane['key']])] = native
            first = mapping[tab['panes'][0]['key']]
            tabs.append({'custom_name': tab['name'], 'layout': tree(tab['root']), 'panes': panes,
                         'zoomed': False, 'focused': first, 'root_pane': first})
        workspaces.append({'custom_name': space['name'], 'identity_cwd': space['directory'],
                           'public_pane_numbers': {}, 'tabs': tabs, 'active_tab': 0})
    return _json_copy({'version': 3, 'workspaces': workspaces,
                       'active': 0 if workspaces else None, 'selected': 0})


def to_app_document(plan, terminal_map):
    """Generate selected machine-local layout only, not private UI view state.

    terminal_map is an exact bijection from canonical pane keys to unqualified
    core addresses. Core terminal creation and document CAS/merge belong to the
    caller; a layout document itself carries neither cwd nor session identities.
    """
    plan = validate_plan(plan)
    mapping = _object(_json_copy(terminal_map))
    keys = {pane['key'] for space in plan['spaces'] for tab in space['tabs'] for pane in tab['panes']}
    if set(mapping) != keys:
        _fail('terminal map must cover exactly the selected panes')
    terminals = set()
    for terminal in mapping.values():
        if not _TERMINAL.fullmatch(_string(terminal)) or terminal in terminals:
            _fail('invalid or duplicate local core terminal address')
        terminals.add(terminal)
    spaces = []
    for si, space in enumerate(plan['spaces']):
        tabs = []
        for ti, tab in enumerate(space['tabs']):
            prefix = f's{si}-t{ti}'

            def tree(node, position):
                if 'pane' in node:
                    return {'id': node['pane'], 'type': 'block',
                            'content': {'terminal': mapping[node['pane']]}}
                children = [tree(child, position + str(i)) for i, child in enumerate(node['children'])]
                children[0]['size'] = {'weight': node['ratio']}
                children[1]['size'] = {'weight': 1.0 - node['ratio']}
                return {'id': f'{prefix}-n{position}', 'type': node['axis'], 'children': children}

            tabs.append({'id': prefix, 'name': tab['name'], 'root': tree(tab['root'], 'r')})
        spaces.append({'id': f's{si}', 'name': space['name'], 'folder': space['directory'], 'tabs': tabs})
    return _json_copy({'spaces': spaces})
