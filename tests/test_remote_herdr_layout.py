"""Pure layout contracts; all identities and directories here are synthetic."""
import copy
import importlib.util
import json
from pathlib import Path
import random

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'dot_local/share/dotfiles-ai/remote-herdr/layout.py'


@pytest.fixture
def layout():
    spec = importlib.util.spec_from_file_location('remote_herdr_layout', SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plan():
    return {'schema_version': 1, 'spaces': [{
        'name': 'work α', 'directory': '/synthetic/project', 'tabs': [{
            'name': 'review', 'root': {
                'axis': 'row', 'ratio': 0.3, 'children': [
                    {'pane': 's0-t0-p0'}, {'axis': 'column', 'ratio': 0.7,
                     'children': [{'pane': 's0-t0-p1'}, {'pane': 's0-t0-p2'}]}]},
            'panes': [{'key': f's0-t0-p{i}', 'cwd': f'/synthetic/p{i}',
                       'session_id': f'ses_Test{i}' if i != 1 else None} for i in range(3)]
        }]}]}


def test_current_app_projection_and_rebind_preserve_opaque_document(layout):
    document = layout.to_app_document(plan(), {f's0-t0-p{i}': f't{i + 1}' for i in range(3)})
    document['opaque'] = {'token': ['synthetic', None]}
    root = document['spaces'][0]['tabs'][0]['root']
    root['custom'] = {'keep': True}
    root['children'][0]['content']['serde_default'] = None
    before = copy.deepcopy(document)
    projected, bindings = layout.project_app_document(
        document, lambda leaf, address: None if address == 't2' else
        {'cwd': '/synthetic/project', 'session_id': 'ses_Test' + address[1:]})
    assert len(projected['spaces'][0]['tabs'][0]['panes']) == 2
    assert bindings == {'s0-t0-p0': {'leaf': 's0-t0-p0', 'terminal': 't1'},
                        's0-t0-p1': {'leaf': 's0-t0-p2', 'terminal': 't3'}}
    changed = layout.rebind_app_document(document, {'s0-t0-p2': ('t3', 't4')})
    expected = copy.deepcopy(before)
    expected['spaces'][0]['tabs'][0]['root']['children'][1]['children'][1]['content']['terminal'] = 't4'
    assert changed == expected and document == before
    with pytest.raises(ValueError):
        layout.rebind_app_document(document, {'s0-t0-p2': ('t9', 't4')})


@pytest.mark.parametrize('malformed', ['duplicate-leaf', 'duplicate-terminal', 'remote-address',
                                      'machine', 'bad-weight', 'bad-axis', 'missing-id'])
def test_current_app_projection_refuses_ambiguous_or_remote_structure(layout, malformed):
    document = layout.to_app_document(plan(), {f's0-t0-p{i}': f't{i + 1}' for i in range(3)})
    root = document['spaces'][0]['tabs'][0]['root']
    first, last = root['children'][0], root['children'][1]['children'][1]
    if malformed == 'duplicate-leaf':
        last['id'] = first['id']
    elif malformed == 'duplicate-terminal':
        last['content']['terminal'] = first['content']['terminal']
    elif malformed == 'remote-address':
        last['content']['terminal'] = 'machine/t3'
    elif malformed == 'machine':
        last['content']['machine'] = 'remote'
    elif malformed == 'bad-weight':
        first['size']['weight'] = 0
    elif malformed == 'bad-axis':
        root['type'] = 'unknown'
    else:
        first.pop('id')
    with pytest.raises(ValueError):
        layout.project_app_document(document, lambda leaf, address: None)


def test_current_projection_prunes_only_private_empty_tabs_spaces_and_singletons(layout):
    document = layout.to_app_document(plan(), {f's0-t0-p{i}': f't{i + 1}' for i in range(3)})
    before = copy.deepcopy(document)
    projected, bindings = layout.project_app_document(document, lambda leaf, address:
        {'cwd': '/synthetic/project', 'session_id': None} if address == 't3' else None)
    assert projected['spaces'][0]['tabs'][0]['root'] == {'pane': 's0-t0-p0'}
    assert bindings['s0-t0-p0']['leaf'] == 's0-t0-p2'
    assert layout.project_app_document(document, lambda leaf, address: None) == (
        {'schema_version': 1, 'spaces': []}, {})
    assert document == before


def test_roundtrip_geometry_identity_names_and_order(layout):
    value = plan()
    value['spaces'].append({'name': '', 'directory': '/synthetic/other', 'tabs': []})
    value['spaces'][0]['tabs'].append({
        'name': '', 'root': {'pane': 's0-t1-p0'},
        'panes': [{'key': 's0-t1-p0', 'cwd': '/synthetic/empty', 'session_id': None}]})
    snapshot = layout.to_tui_snapshot(value)
    assert snapshot['version'] == 3
    tab = snapshot['workspaces'][0]['tabs'][0]
    assert tab['layout']['Split']['direction'] == 'Horizontal'
    assert tab['layout']['Split']['second']['Split']['direction'] == 'Vertical'
    assert tab['panes']['0']['agent_session'] == {
        'source': 'herdr:opencode', 'agent': 'opencode', 'kind': 'id', 'value': 'ses_Test0'}
    assert tab['panes']['0']['launch_argv'] == ['opencode', '--session', 'ses_Test0']
    assert layout.from_tui_snapshot(json.loads(json.dumps(snapshot))) == value
    assert layout.validate_plan(value) == value
    clone = layout.validate_plan(value)
    clone['spaces'][0]['tabs'][0]['panes'][0]['cwd'] = '/changed'
    assert value['spaces'][0]['tabs'][0]['panes'][0]['cwd'] == '/synthetic/p0'


def test_native_arbitrary_ids_and_no_custom_names(layout):
    native = layout.to_tui_snapshot(plan())
    tab = native['workspaces'][0]['tabs'][0]
    tab['panes'] = {'42': tab['panes']['0'], '8': tab['panes']['1'], '91': tab['panes']['2']}
    tab['layout'] = {'Split': {'direction': 'Horizontal', 'ratio': 0.3,
                              'first': {'Pane': 42}, 'second': {'Split': {
                                  'direction': 'Vertical', 'ratio': 0.7,
                                  'first': {'Pane': 8}, 'second': {'Pane': 91}}}}}
    tab.pop('custom_name')
    native['workspaces'][0]['custom_name'] = None
    result = layout.from_tui_snapshot(native)
    assert result['spaces'][0]['name'] == ''
    assert result['spaces'][0]['tabs'][0]['name'] == ''
    assert layout.from_tui_snapshot(layout.to_tui_snapshot(result)) == result


def test_app_native_document_weights_and_exact_mapping(layout):
    mapping = {f's0-t0-p{i}': f't{i + 1}' for i in range(3)}
    doc = layout.to_app_document(plan(), mapping)
    assert set(doc) == {'spaces'}
    space = doc['spaces'][0]
    assert space['name'] == 'work α' and space['folder'] == '/synthetic/project'
    root = space['tabs'][0]['root']
    assert root['type'] == 'row'
    assert root['children'][0]['size'] == {'weight': 0.3}
    assert root['children'][1]['size'] == {'weight': 0.7}
    assert root['children'][0]['content'] == {'terminal': 't1'}
    assert root['children'][1]['type'] == 'column'
    assert doc == layout.to_app_document(plan(), mapping)
    for invalid in [{}, {**mapping, 'extra': 't9'}, {**mapping, 's0-t0-p1': 't1'},
                    {**mapping, 's0-t0-p1': 'machine/t2'}, {**mapping, 's0-t0-p1': 'tA'}]:
        with pytest.raises(ValueError):
            layout.to_app_document(plan(), invalid)


def space_plan():
    return [{'label': 'space', 'missing': False, 'pruned': 9, 'tabs': [{
        'label': 'exact', 'steps': [
            {'op': 'tab', 'cwd': '/synthetic'},
            {'op': 'split', 'direction': 'right', 'ratio': 0.3, 'cwd': '/synthetic/right'},
            {'op': 'split', 'direction': 'down', 'ratio': 0.6, 'cwd': '/synthetic/down'},
            {'op': 'resume', 'pane': 2, 'command': 'opencode --session ses_Example'}]}]}]


def test_labelled_spaceplan_last_pane_chain(layout):
    result = layout.from_space_plan(space_plan())
    space = result['spaces'][0]
    assert space['directory'] == '/synthetic'
    assert space['name'] == 'space' and space['tabs'][0]['name'] == 'exact'
    tab = space['tabs'][0]
    assert tab['root']['axis'] == 'row'
    assert tab['root']['children'][1]['axis'] == 'column'
    assert tab['panes'][2]['session_id'] == 'ses_Example'
    assert len(tab['panes']) == 3  # pruned is metadata, not a request


@pytest.mark.parametrize('command', [
    'opencode --session ses_A; touch /x', 'env opencode --session ses_A',
    'opencode --session ses_A && echo x', 'opencode --session $(x)',
    'opencode --session ses_A --session ses_B', 'opencode --session ses_A\necho x',
    'opencode --session', 'other --session ses_A', 'opencode --session ses_a_b'])
def test_spaceplan_command_refusal(layout, command):
    value = space_plan()
    value[0]['tabs'][0]['steps'][-1]['command'] = command
    with pytest.raises(ValueError):
        layout.from_space_plan(value)


@pytest.mark.parametrize('change', ['legacy', 'missing', 'unknown', 'left', 'no_tab', 'bad_pane'])
def test_spaceplan_lossy_or_unknown_refused(layout, change):
    value = space_plan()
    tab = value[0]['tabs'][0]
    if change == 'legacy':
        value[0]['tabs'] = [tab['steps']]
    elif change == 'missing':
        value[0]['missing'] = True
    elif change == 'unknown':
        tab['steps'].append({'op': 'exec', 'command': 'anything'})
    elif change == 'left':
        tab['steps'][1]['direction'] = 'left'
    elif change == 'no_tab':
        tab['steps'].pop(0)
    else:
        tab['steps'][-1]['pane'] = -1
    with pytest.raises(ValueError):
        layout.from_space_plan(value)


@pytest.mark.parametrize('change', [
    'version', 'bool_version', 'relative', 'dotdot', 'null', 'long_name',
    'duplicate_session', 'bad_session', 'missing_ref', 'duplicate_ref', 'extra_pane',
    'wrong_key', 'unknown_field', 'bad_axis', 'nan', 'zero', 'one', 'bool_ratio',
    'three_children', 'empty_tab', 'cycle', 'too_many_spaces', 'too_many_tabs'])
def test_invalid_canonical_refused(layout, change):
    value = plan()
    space = value['spaces'][0]
    tab = space['tabs'][0]
    if change == 'version': value['schema_version'] = 2
    elif change == 'bool_version': value['schema_version'] = True
    elif change == 'relative': space['directory'] = 'relative'
    elif change == 'dotdot': tab['panes'][0]['cwd'] = '/a/../b'
    elif change == 'null': space['name'] = 'a\0b'
    elif change == 'long_name': space['name'] = 'x' * 513
    elif change == 'duplicate_session': tab['panes'][1]['session_id'] = 'ses_Test0'
    elif change == 'bad_session': tab['panes'][1]['session_id'] = 'ses_bad-id'
    elif change == 'missing_ref': tab['root']['children'][0]['pane'] = 'missing'
    elif change == 'duplicate_ref': tab['root']['children'][1] = {'pane': 's0-t0-p0'}
    elif change == 'extra_pane': tab['panes'].append({'key': 's0-t0-p3', 'cwd': '/x', 'session_id': None})
    elif change == 'wrong_key': tab['panes'][0]['key'] = 'foreign'
    elif change == 'unknown_field': value['credentials'] = 'never carried'
    elif change == 'bad_axis': tab['root']['axis'] = 'horizontal'
    elif change in ('nan', 'zero', 'one', 'bool_ratio'):
        tab['root']['ratio'] = {'nan': float('nan'), 'zero': 0, 'one': 1, 'bool_ratio': True}[change]
    elif change == 'three_children': tab['root']['children'].append({'pane': 's0-t0-p0'})
    elif change == 'empty_tab': tab['panes'] = []
    elif change == 'cycle': tab['root']['children'][0] = tab['root']
    elif change == 'too_many_spaces': value['spaces'] = [copy.deepcopy(space) for _ in range(257)]
    else: space['tabs'] = [copy.deepcopy(tab) for _ in range(1025)]
    with pytest.raises(ValueError):
        layout.validate_plan(value)


@pytest.mark.parametrize('field,value', [
    ('agent_name', 'claude'), ('managed_agent_kind', 'pi'),
    ('agent_session', {'source': 'herdr:pi', 'agent': 'pi', 'kind': 'id', 'value': 'ses_Test0'}),
    ('launch_argv', ['opencode', '--session', 'ses_Contradiction']),
    ('launch_argv', ['sh', '-c', 'opencode --session ses_Test0']),
    ('agent_resume', {'source': 'herdr:opencode', 'agent': 'opencode', 'argv': ['dangerous']}),
])
def test_native_agent_ambiguity_refused(layout, field, value):
    native = layout.to_tui_snapshot(plan())
    native['workspaces'][0]['tabs'][0]['panes']['0'][field] = value
    with pytest.raises(ValueError):
        layout.from_tui_snapshot(native)


def test_native_argv_only_identity_and_no_invention_or_history(layout):
    native = layout.to_tui_snapshot(plan())
    pane = native['workspaces'][0]['tabs'][0]['panes']['0']
    pane.pop('agent_session')
    pane['history'] = {'ansi': 'not exported'}
    native['credentials'] = 'not exported either'
    assert layout.from_tui_snapshot(native) == plan()
    pane['launch_argv'] = ['opencode']
    with pytest.raises(ValueError):
        layout.from_tui_snapshot(native)


def test_json_budget_and_deep_input_refused(layout):
    native = layout.to_tui_snapshot(plan())
    native['ignored'] = ['x' * 4096] * 257
    with pytest.raises(ValueError):
        layout.from_tui_snapshot(native)
    value = plan()
    tree = value['spaces'][0]['tabs'][0]['root']
    for _ in range(33):
        tree = {'axis': 'row', 'ratio': 0.5, 'children': [tree, {'pane': 's0-t0-p0'}]}
    value['spaces'][0]['tabs'][0]['root'] = tree
    with pytest.raises(ValueError):
        layout.validate_plan(value)


@pytest.mark.parametrize('axis', ['row', 'column'])
@pytest.mark.parametrize('ratio', [0.001, 0.125, 0.5, 0.875, 0.999])
def test_roundtrip_ratio_domain(layout, axis, ratio):
    value = plan()
    root = value['spaces'][0]['tabs'][0]['root']
    root['axis'], root['ratio'] = axis, ratio
    # Pane numbering and BSP order are independent.
    root['children'].reverse()
    assert layout.from_tui_snapshot(layout.to_tui_snapshot(value)) == value


def single_tab(si=0, ti=0):
    key = f's{si}-t{ti}-p0'
    return {'name': '', 'root': {'pane': key},
            'panes': [{'key': key, 'cwd': '/synthetic', 'session_id': None}]}


def balanced_plan(count):
    panes = [{'key': f's0-t0-p{i}', 'cwd': '/s', 'session_id': None} for i in range(count)]

    def tree(start, stop):
        if stop - start == 1:
            return {'pane': panes[start]['key']}
        middle = (start + stop) // 2
        return {'axis': 'row', 'ratio': 0.5,
                'children': [tree(start, middle), tree(middle, stop)]}

    return {'schema_version': 1, 'spaces': [{'name': '', 'directory': '/s', 'tabs': [{
        'name': '', 'root': tree(0, count), 'panes': panes}]}]}


def test_global_native_numbers_and_session_uniqueness(layout):
    value = plan()
    value['spaces'].append({'name': 'second', 'directory': '/synthetic/second',
                            'tabs': [single_tab(1)]})
    native = layout.to_tui_snapshot(value)
    numbers = [number for space in native['workspaces'] for tab in space['tabs']
               for number in tab['panes']]
    assert len(numbers) == len(set(numbers))
    assert layout.from_tui_snapshot(native) == value
    second_tab = native['workspaces'][1]['tabs'][0]
    second_pane = next(iter(second_tab['panes'].values()))
    second_tab['panes'] = {'0': second_pane}
    second_tab['layout'] = {'Pane': 0}
    with pytest.raises(ValueError):
        layout.from_tui_snapshot(native)
    value['spaces'][1]['tabs'][0]['panes'][0]['session_id'] = 'ses_Test0'
    with pytest.raises(ValueError):
        layout.validate_plan(value)


@pytest.mark.parametrize('count', [1, 4096])
def test_pane_count_boundary(layout, count):
    value = balanced_plan(count)
    assert layout.from_tui_snapshot(layout.to_tui_snapshot(value)) == value


def test_excess_pane_count(layout):
    with pytest.raises(ValueError):
        layout.validate_plan(balanced_plan(4097))


def test_space_and_tab_count_boundaries(layout):
    spaces = [{'name': '', 'directory': '/s', 'tabs': []} for _ in range(256)]
    assert layout.validate_plan({'schema_version': 1, 'spaces': spaces})['spaces'] == spaces
    value = {'schema_version': 1, 'spaces': [{
        'name': '', 'directory': '/s', 'tabs': [single_tab(0, ti) for ti in range(1024)]}]}
    assert layout.from_tui_snapshot(layout.to_tui_snapshot(value)) == value


def test_exact_depth_boundary(layout):
    value = balanced_plan(1)
    tab = value['spaces'][0]['tabs'][0]
    for pi in range(1, 32):
        key = f's0-t0-p{pi}'
        tab['panes'].append({'key': key, 'cwd': '/s', 'session_id': None})
        tab['root'] = {'axis': 'row', 'ratio': 0.5,
                       'children': [tab['root'], {'pane': key}]}
    assert layout.from_tui_snapshot(layout.to_tui_snapshot(value)) == value
    tab['root'] = {'axis': 'column', 'ratio': 0.5,
                   'children': [tab['root'], {'pane': 's0-t0-p0'}]}
    with pytest.raises(ValueError):
        layout.validate_plan(value)


def test_deterministic_generated_bsp_domain(layout):
    # Generated properties without a new dependency or on-disk example database.
    for seed in range(100):
        rng = random.Random(seed)
        value = balanced_plan(rng.randrange(1, 40))
        tab = value['spaces'][0]['tabs'][0]
        leaves = [{'pane': pane['key']} for pane in tab['panes']]
        rng.shuffle(leaves)
        while len(leaves) > 1:
            index = rng.randrange(len(leaves) - 1)
            leaves[index:index + 2] = [{
                'axis': rng.choice(['row', 'column']), 'ratio': rng.uniform(0.01, 0.99),
                'children': leaves[index:index + 2]}]
        tab['root'] = leaves[0]
        for pi, pane in enumerate(tab['panes']):
            pane['session_id'] = f'ses_Seed{seed}Pane{pi}' if rng.randrange(2) else None
        before = copy.deepcopy(value)
        native = layout.to_tui_snapshot(value)
        assert layout.from_tui_snapshot(native) == before
        mapping = {pane['key']: f't{pi}' for pi, pane in enumerate(tab['panes'])}
        document = layout.to_app_document(value, mapping)
        assert value == before

        def check(canonical, app):
            if 'pane' in canonical:
                assert app['content'] == {'terminal': mapping[canonical['pane']]}
                return
            assert app['type'] == canonical['axis']
            first, second = app['children']
            assert first['size']['weight'] == canonical['ratio']
            assert second['size']['weight'] == 1 - canonical['ratio']
            for child, app_child in zip(canonical['children'], app['children']):
                check(child, app_child)

        check(tab['root'], document['spaces'][0]['tabs'][0]['root'])


@pytest.mark.parametrize('value', [None, [], True, 1, 'text', {'schema_version': 1},
                                  {'schema_version': 1, 'spaces': {}}])
def test_nonplans_fail_with_valueerror(layout, value):
    with pytest.raises(ValueError):
        layout.validate_plan(value)


def test_empty_selection(layout):
    value = {'schema_version': 1, 'spaces': []}
    assert layout.from_tui_snapshot(layout.to_tui_snapshot(value)) == value
    assert layout.from_space_plan([]) == value
    assert layout.to_app_document(value, {}) == {'spaces': []}


@pytest.mark.parametrize('number,encoded', [(0, '0'), (1, '1'), (31, 'Z'), (32, '0'), (33, '11'), (1024, 'Z0')])
def test_tui_public_number_encoding(layout, number, encoded):
    assert layout.encode_public_number(number) == encoded


def test_tui_nullable_naming_provenance_is_not_canonical_schema(layout):
    snapshot = layout.to_tui_snapshot(plan())
    space = snapshot['workspaces'][0]
    space['custom_name'] = None
    space['tabs'][0]['custom_name'] = ''
    assert layout.tui_names(snapshot) == [{'custom_name': None, 'tabs': ['']}]
    space['custom_name'] = ''
    assert layout.tui_names(snapshot) == [{'custom_name': '', 'tabs': ['']}]


def identity_snapshot(layout):
    snapshot = layout.to_tui_snapshot(plan())
    space = snapshot['workspaces'][0]
    space.update(id='synthetic', custom_name=None, public_tab_numbers=[3],
                 public_pane_numbers={'0': 9, '1': 2, '2': 33})
    return snapshot


def test_tui_public_binding_uses_mapping_not_internal_numbers(layout):
    snapshot = identity_snapshot(layout)
    binding = layout.tui_public_identities(snapshot)[0]
    assert binding['id'] == 'synthetic'
    tab = binding['tabs'][0]
    assert tab['id'] == 'synthetic:t3'
    assert tab['root']['children'][0] == {'pane': 'synthetic:p9'}
    assert set(tab['panes']) == {'synthetic:p9', 'synthetic:p2', 'synthetic:p11'}
    assert tab['panes']['synthetic:p9']['session_id'] == 'ses_Test0'
    assert snapshot == identity_snapshot(layout)


@pytest.mark.parametrize('change', ['missing-workspace', 'missing-tabs', 'missing-pane', 'extra-pane',
                                  'duplicate-pane', 'bool-pane', 'bad-root', 'bad-tab-number'])
def test_tui_public_mapping_refuses_lossy_identity(layout, change):
    snapshot = identity_snapshot(layout)
    space = snapshot['workspaces'][0]
    if change == 'missing-workspace': space.pop('id')
    elif change == 'missing-tabs': space['public_tab_numbers'] = []
    elif change == 'missing-pane': space['public_pane_numbers'].pop('1')
    elif change == 'extra-pane': space['public_pane_numbers']['99'] = 99
    elif change == 'duplicate-pane': space['public_pane_numbers']['1'] = 9
    elif change == 'bool-pane': space['public_pane_numbers']['1'] = True
    elif change == 'bad-root': space['tabs'][0]['root_pane'] = 99
    else: space['public_tab_numbers'] = [True]
    with pytest.raises(ValueError) as error:
        layout.tui_public_identities(snapshot)
    assert 'synthetic' not in str(error.value) and 'ses_Test' not in str(error.value)


@pytest.mark.parametrize('value', ['x' * 4097, '\ud800', {'not': 'a string'}])
def test_invalid_strings(layout, value):
    canonical = plan()
    canonical['spaces'][0]['tabs'][0]['panes'][0]['cwd'] = value
    with pytest.raises(ValueError):
        layout.validate_plan(canonical)


def test_native_version_unknown_layout_and_duplicate_leaves(layout):
    for change in ['version', 'direction', 'duplicate', 'unreferenced', 'bad_id']:
        native = layout.to_tui_snapshot(plan())
        tab = native['workspaces'][0]['tabs'][0]
        if change == 'version': native['version'] = 2
        elif change == 'direction': tab['layout']['Split']['direction'] = 'Diagonal'
        elif change == 'duplicate': tab['layout']['Split']['first'] = {'Pane': 1}
        elif change == 'unreferenced': tab['layout'] = {'Pane': 0}
        else: tab['panes']['00'] = tab['panes'].pop('0')
        with pytest.raises(ValueError):
            layout.from_tui_snapshot(native)
