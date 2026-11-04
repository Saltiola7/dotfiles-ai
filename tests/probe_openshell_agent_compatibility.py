"""Credential-free, source-selected client comparisons in the capped local guest."""
from __future__ import annotations

import hashlib
import json
import re

import probe_openshell_full_build as full
import probe_openshell_guest_build as build
import probe_openshell_guest_inventory as guest
import probe_openshell_storage_boot as boot
import probe_openshell_storage_create as create


OPERATIONS = ('agent-prepare', 'agent-test')
PROBES = ('codex-version', 'codex-help', 'codex-empty-login', 'codex-stdio',
          'opencode-version', 'opencode-help', 'opencode-rg')
MODES = ('unfiltered', 'upstream', 'patched')
CASES = tuple(f'{probe}-{mode}' for probe in PROBES for mode in MODES)
WORK = '/var/lib/dotfiles-ai-openshell-build/store/work'
FLAGS = {'session_enabled': False, 'full_runtime_qualified': False, 'compatibility_qualified': False}
RESERVE = 256 * 1024**2
VOICE_OMISSIONS_SHA256 = '478394bae952fff452aa79788abe07f3b2a44b1439c88b91da2919250cde7780'
STAGES = {
    'agent-prepare': (('agent-download', 'assets', True, 300), ('agent-prepare', 'assets', False, 300)),
    'agent-test': (('rust-verify', 'rust', False, 240), ('compiler-verify', 'compiler', False, 240),
                   ('source-verify', 'source', False, 120), ('agent-verify', 'assets', False, 180),
                   ('fixture-prepare', 'fixture-source', False, 240),
                   ('fixture-build', 'fixture-build', False, 240),
                   ('cases-prepare', 'cases', False, 60),
                   *((case, 'cases', False, 60 if case.startswith('codex-stdio-') else 30) for case in CASES),
                   ('agent-final', 'assets', False, 180), ('source-final', 'source', False, 120)),
}
ASSETS = {
    'codex': {'version': '0.164.0',
              'url': 'https://github.com/openai/codex/releases/download/rust-v0.164.0/codex-package-aarch64-unknown-linux-musl.tar.gz',
              'archive': 'codex-package-aarch64-unknown-linux-musl.tar.gz', 'bytes': 152400557,
              'sha256': '5918add6c7e9cf1e14a9af1b4c0f4bf1d24a43903faac26df5dc4c019ea91bd5',
              'expanded_limit': 1024**3},
    'opencode': {'version': '1.18.25',
                 'url': 'https://github.com/anomalyco/opencode/releases/download/v1.18.25/opencode-linux-arm64.tar.gz',
                 'archive': 'opencode-linux-arm64.tar.gz', 'bytes': 60345335,
                 'sha256': '35ef77897425e41b5183a2c21ac4fb1d4d944d82a94e3c920f57b5490af11ac5',
                 'expanded_limit': 512*1024**2},
}
FILE_SETS = {'codex': {'codex-package.json', 'bin/codex', 'bin/codex-code-mode-host', 'codex-resources/bwrap', 'codex-path/rg'},
             'opencode': {'opencode'}}
CODEX_METADATA = {'layoutVersion': 1, 'version': '0.164.0', 'target': 'aarch64-unknown-linux-musl',
                  'variant': 'codex', 'entrypoint': 'bin/codex', 'resourcesDir': 'codex-resources', 'pathDir': 'codex-path'}


def refuse(reason):
    raise build.Refusal('agent_' + reason)


def sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def integer(value, minimum=0, maximum=2**63-1):
    return type(value) is int and minimum <= value <= maximum


def manifest():
    value = create._json(build.read_source(build.FIXTURES/'agentcheck/manifest.json'))
    if (value != {'schema_version': 1, 'generation': 1, 'assets': ASSETS}
            or type(value['schema_version']) is not int or type(value['generation']) is not int):
        refuse('manifest')
    return value


def voice_omissions(raw=None):
    if raw is None:
        raw = build.read_source(build.FIXTURES/'agentcheck/voice-omissions.json')
    value = create._json(raw)
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if (hashlib.sha256(canonical).hexdigest() != VOICE_OMISSIONS_SHA256
            or type(value) is not dict or set(value) != {'schema_version', 'archive_sha256', 'entries'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['archive_sha256'] != ASSETS['codex']['sha256']
            or type(value['entries']) is not dict or len(value['entries']) != 43):
        refuse('voice_omissions')
    return value


def load_bundle(parent):
    base = full.load_bundle(parent)
    files = {}; hashes = dict(base.source_hashes)
    for name, local in (('Cargo.toml', 'Cargo.toml'), ('Cargo.lock', 'Cargo.lock'), ('src/main.rs', 'main.rs')):
        raw = build.read_source(build.FIXTURES/'agentcheck'/local)
        if not 0 < len(raw) <= (10240 if name == 'src/main.rs' else 4096):
            refuse('fixture_bound')
        files[name] = raw.decode(); hashes['agentcheck/'+local] = hashlib.sha256(raw).hexdigest()
    selected = manifest()
    hashes['agentcheck/manifest.json'] = hashlib.sha256(build.read_source(build.FIXTURES/'agentcheck/manifest.json')).hexdigest()
    omission_raw = build.read_source(build.FIXTURES/'agentcheck/voice-omissions.json')
    omissions = voice_omissions(omission_raw)
    hashes['agentcheck/voice-omissions.json'] = hashlib.sha256(omission_raw).hexdigest()
    return build.Bundle(base.payload | {'agent_manifest': selected, 'fixture_files': files,
                                      'voice_omissions': omissions}, hashes)


def capture_sources(operation):
    if operation not in OPERATIONS:
        refuse('operation')
    standard = full.capture_sources('full-test')
    base = build.read_source(build.FIXTURES/'guest_harness.py').decode()
    def joined(*names):
        return base+'\n'+'\n'.join(build.read_source(build.FIXTURES/name).decode() for name in names)
    sources = standard | {
        'assets': joined('guest_agent_assets.py'),
        'fixture-source': joined('guest_full_source.py', 'guest_agent_build.py'),
        'fixture-build': joined('guest_cargo_artifact.py', 'guest_full_cargo.py', 'guest_agent_build.py'),
        'cases': joined('guest_cargo_artifact.py', 'guest_agent_runtime.py'),
    }
    return {key: sources[key] for key in dict.fromkeys(stage[1] for stage in STAGES[operation])}


def stage_payload(payload, stage, completed):
    if stage in {'rust-verify', 'compiler-verify', 'source-verify', 'source-final'}:
        return full.stage_payload(payload, stage)
    result = {} if stage.startswith('fixture-') else {'agent_manifest': payload.get('agent_manifest', {})}
    if stage.startswith('fixture-'):
        value = payload.get('full_manifest', {})
        result['full_manifest'] = {key: value[key] for key in ('schema_version', 'upstream_commit',
            'upstream_tree_sha1', 'experimental_version', 'source', 'cargo', 'limits') if key in value}
        if stage == 'fixture-build':
            result['agent_build_report'] = completed.get('fixture-prepare', {})
        else:
            result['fixture_files'] = payload.get('fixture_files', {})
    elif stage == 'cases-prepare' or stage in CASES:
        result['agent_build_report'] = completed.get('fixture-build', {})
        result['agent_assets_report'] = completed.get('agent-verify', {})
    elif stage in {'agent-download', 'agent-prepare', 'agent-verify', 'agent-final'}:
        result['voice_omissions'] = payload.get('voice_omissions', {})
    return result


def unit_source(source, payload, stage, seconds, completed):
    if stage in full.STAGE_BODIES:
        body = full.STAGE_BODIES[stage]
    elif stage in CASES:
        body = f'_result=agent_case(_stage_payload,{stage!r})\n'
    else:
        functions = {'agent-download': 'agent_assets_download', 'agent-prepare': 'agent_assets_prepare',
                     'agent-verify': 'agent_assets_verify', 'agent-final': 'agent_assets_verify',
                     'fixture-prepare': 'agent_build_prepare', 'fixture-build': 'agent_build_compile',
                     'cases-prepare': 'agent_cases_prepare'}
        if stage not in functions:
            refuse('stage')
        body = f'_result={functions[stage]}(_stage_payload)\n'
    validation = ("if not all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (1,2)):\n"
                  "    raise RuntimeError('harness_log_route')\n") if stage in CASES else 'validate_context()\n'
    unit = (source+'\n'+build.payload_source(stage_payload(payload, stage, completed))
            +f'\nDEADLINE=time.monotonic()+{seconds!r}\n'+validation+body
            +'\nremaining()\nprint(json.dumps(_result,sort_keys=True),flush=True)\n')
    if len(unit.encode()) > 65536:
        refuse('unit_bound')
    return unit


def stage_script(controller, runtime, inventory, source, payload, operation, stage, seconds, *, host_binding_sha256, completed=None):
    if operation not in OPERATIONS or not build._binding_digest(host_binding_sha256):
        refuse('operation')
    chosen = [item for item in STAGES[operation] if item[0] == stage]
    if len(chosen) != 1 or not integer(seconds, 90, 1600):
        refuse('stage')
    _, _, network, maximum = chosen[0]
    first = stage == STAGES[operation][0][0]
    threshold = (2*1024**3 if operation == 'agent-prepare' else 512*1024**2) if first else RESERVE
    unit = unit_source(source, payload, stage, min(maximum, seconds-70)-5, completed or {})
    case = stage if stage in CASES else None
    body = f'''
_operation_end=time.monotonic()+{seconds!r}
with mounted_store(deadline=_operation_end,host_binding_sha256={host_binding_sha256!r}):
    _before=build_inventory()
    if _before['store_available_bytes'] < {threshold!r}:
        raise RuntimeError('agent_capacity')
    _runtime=install_runtime(existing_only=True) if {first!r} else None
    _seconds=min({maximum!r},int(_operation_end-time.monotonic()-65))
    if _seconds<10:
        raise RuntimeError('agent_deadline')
    _observed=run_unit({unit!r},network={network!r},seconds=_seconds,agent_case={case!r})
    _result=json.loads(_observed['stdout'])
    _after=build_inventory()
    if _after['store_available_bytes'] < {RESERVE!r}:
        raise RuntimeError('agent_reserve')
print(json.dumps({{'status':'agent_stage_completed','operation':{operation!r},'stage':{stage!r},
    'result':_result,'runtime':_runtime,'inventory_before':_before,'inventory_after':_after,
    'unmounted_verified':True,'session_enabled':False,'full_runtime_qualified':False,
    'compatibility_qualified':False}}),flush=True)
'''
    return build._observed_script(controller+'\n'+(runtime if first else '')+'\n'+inventory, body)


def parse_stage(value, operation, stage):
    keys = {'status', 'operation', 'stage', 'result', 'runtime', 'inventory_before', 'inventory_after',
            'unmounted_verified', *FLAGS}
    first = stage == STAGES[operation][0][0]
    if (type(value) is not dict or set(value) != keys or value['status'] != 'agent_stage_completed'
            or value['operation'] != operation or value['stage'] != stage
            or any(value[key] is not False for key in FLAGS) or value['unmounted_verified'] is not True
            or type(value['result']) is not dict or (not first and value['runtime'] is not None)):
        refuse('stage_report')
    if first and (type(value['runtime']) is not dict or value['runtime'].get('status') != 'runtime_ready'
                  or value['runtime'].get('installed_bytes') != 945234):
        refuse('runtime_report')
    for key in ('inventory_before', 'inventory_after'):
        build.parse_inventory(value[key] | {'unmounted_verified': True})
    if value['inventory_after']['store_available_bytes'] < RESERVE:
        refuse('reserve')
    return value


def report_header(value, status, keys):
    if (type(value) is not dict or set(value) != {'schema_version', 'generation', 'status', *FLAGS, *keys}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or type(value['generation']) is not int or value['generation'] != 1 or value['status'] != status
            or any(value[key] is not False for key in FLAGS)):
        refuse('proof_header')


def parse_assets(value, downloaded=False):
    if downloaded:
        report_header(value, 'agent_assets_downloaded', {'archives'})
        if value['archives'] != {name: {key: item[key] for key in ('bytes', 'sha256')} for name, item in ASSETS.items()}:
            refuse('download_proof')
        return
    report_header(value, 'agent_assets_verified', {'prefixes', 'assets', 'codex_metadata'})
    if (value['prefixes'] != {name: WORK+'/agent-assets-1/'+name for name in ASSETS}
            or value['codex_metadata'] != CODEX_METADATA
            or type(value['codex_metadata'].get('layoutVersion')) is not int or type(value['assets']) is not dict
            or set(value['assets']) != set(ASSETS)):
        refuse('assets_proof')
    omission_layout = voice_omissions()['entries']
    for name, selected in ASSETS.items():
        item = value['assets'][name]
        if (type(item) is not dict or set(item) != {'version', 'archive_bytes', 'archive_sha256', 'expanded_bytes', 'files',
                                                  'package_scope', 'omitted_entries'}
                or item['version'] != selected['version'] or type(item['archive_bytes']) is not int
                or item['archive_bytes'] != selected['bytes']
                or item['archive_sha256'] != selected['sha256'] or not integer(item['expanded_bytes'], 1, selected['expanded_limit'])
                or type(item['files']) is not dict or set(item['files']) != FILE_SETS[name]):
            refuse('asset_identity')
        expected = omission_layout if name == 'codex' else {}
        scope = 'probe_subset_without_voice' if name == 'codex' else 'complete'
        omitted = item['omitted_entries']
        if item['package_scope'] != scope or type(omitted) is not dict or set(omitted) != set(expected):
            refuse('asset_omissions')
        for path, original in expected.items():
            entry = omitted[path]
            if (type(entry) is not dict or set(entry) != {'kind', 'bytes', 'mode', 'sha256'}
                    or type(entry['bytes']) is not int or type(entry['mode']) is not int
                    or any(entry[key] != original[key] for key in ('kind', 'bytes', 'mode'))
                    or (entry['sha256'] is not None if original['kind'] == 'directory' else not sha(entry['sha256']))):
                refuse('asset_omissions')
        if item['expanded_bytes'] + sum(entry['bytes'] for entry in omitted.values()) > selected['expanded_limit']:
            refuse('asset_expansion')
        for path, entry in item['files'].items():
            metadata = path == 'codex-package.json'
            if (type(entry) is not dict or set(entry) != {'bytes', 'sha256', 'mode', 'elf'}
                    or not integer(entry['bytes'], 1, selected['expanded_limit']) or not sha(entry['sha256'])
                    or type(entry['mode']) is not int or entry['mode'] != (0o400 if metadata else 0o500)):
                refuse('asset_file')
            elf = entry['elf']
            if metadata:
                if elf is not None: refuse('asset_elf')
            elif (type(elf) is not dict or set(elf) != {'machine', 'kind', 'interpreter', 'needed'}
                  or type(elf['machine']) is not int or elf['machine'] != 183
                  or type(elf['kind']) is not int or elf['kind'] not in (2, 3)
                  or elf['interpreter'] not in (None, '/lib/ld-linux-aarch64.so.1', '/lib/ld-musl-aarch64.so.1')
                  or type(elf['needed']) is not list or len(elf['needed']) > 64
                  or any(type(dep) is not str or dep in ('.', '..')
                         or not re.fullmatch('[A-Za-z0-9_.+-]{1,255}', dep) for dep in elf['needed'])
                  or len(set(elf['needed'])) != len(elf['needed'])):
                refuse('asset_elf')
        if sum(entry['bytes'] for entry in item['files'].values()) != item['expanded_bytes']:
            refuse('asset_expansion')


def parse_fixture(value, payload, built=False):
    keys = {'source_sha256'} | ({'binary_sha256', 'binary_bytes', 'binary_layout', 'static_arm64'} if built else set())
    report_header(value, 'agent_fixture_built' if built else 'agent_fixture_prepared', keys)
    expected = {name: hashlib.sha256(raw.encode()).hexdigest() for name, raw in payload['fixture_files'].items()}
    expected |= {'src/upstream_child_seccomp.rs': '14c06d0d2c33a56b9a075f469a16436b92cc101186ef19a00a4f1ab84871fa0f',
                 'src/patched_child_seccomp.rs': build.PATCHED_SHA}
    if value['source_sha256'] != expected: refuse('fixture_sources')
    if built:
        layout = value['binary_layout']
        if (not sha(value['binary_sha256']) or not integer(value['binary_bytes'], 1, 64*1024**2)
                or value['static_arm64'] is not True or type(layout) is not dict
                or set(layout) != {'link_count', 'companion'} or type(layout['link_count']) is not int
                or layout['link_count'] not in (1, 2)
                or (layout['link_count'] == 1 and layout['companion'] is not None)
                or (layout['link_count'] == 2 and (type(layout['companion']) is not str
                    or re.fullmatch('openshell_agent_filter_probe-[0-9a-f]{16}', layout['companion']) is None))):
            refuse('fixture_binary')


def parse_cases_prepared(value):
    report_header(value, 'agent_cases_prepared', {'cases', 'initial_sha256', 'case_state_bytes'})
    if (value['cases'] != list(CASES) or type(value['initial_sha256']) is not dict
            or value['initial_sha256'] != {
                'codex_config': '77b8b75c411e1232f4ddaa8f72551615000541dc3afc68b1614f62974acae68d',
                'opencode_gitignore': '2112e764c5bff9772492998e8ef894845f4208681f9a3a6d29fc6ff71ec2050e',
                'sentinel': '2e081162edc72aae46c42433abd114adc42868a47c86eb5acbb247f6ce826457'}
            or not integer(value['case_state_bytes'], 0, 128*1024**2)):
        refuse('case_preparation')


def parse_case(value, case, stages):
    keys = {'case', 'probe', 'mode', 'fixture_binary_sha256', 'executable_sha256', 'rg_sha256',
            'proof_records', 'observation', 'exit_code', 'signal', 'wrapper_returncode',
            'termination_requested', 'expectation_met', 'initialized', 'initialize_result', 'stdin_bytes',
            'stdout_bytes', 'stderr_bytes', 'stdout_tail', 'stderr_tail', 'case_state_bytes', 'python_nondumpable'}
    report_header(value, 'agent_case_observed', keys)
    probe, mode = case.rsplit('-', 1)
    if case not in CASES or (value['case'], value['probe'], value['mode']) != (case, probe, mode):
        refuse('case_identity')
    name = 'codex' if probe.startswith('codex-') else 'opencode'
    files = stages['agent-verify']['assets']
    selected = files[name]['files']['bin/codex' if name == 'codex' else 'opencode']['sha256']
    if (value['fixture_binary_sha256'] != stages['fixture-build']['binary_sha256']
            or value['executable_sha256'] != selected or value['rg_sha256'] != files['codex']['files']['codex-path/rg']['sha256']
            or value['python_nondumpable'] is not True or type(value['initialized']) is not bool
            or type(value['expectation_met']) is not bool or type(value['termination_requested']) is not bool
            or not integer(value['case_state_bytes'], 0, 128*1024**2)
            or not integer(value['stdin_bytes'], 0, 1024)
            or not all(integer(value[key], 0, 1024**2) for key in ('stdout_bytes', 'stderr_bytes'))
            or value['stdout_bytes'] + value['stderr_bytes'] > 1024**2
            or any(type(value[key]) is not str or len(value[key].encode()) > 8192 for key in ('stdout_tail', 'stderr_tail'))):
        refuse('case_metadata')
    for stream in ('stdout', 'stderr'):
        count, tail = value[stream+'_bytes'], value[stream+'_tail']
        if ((count == 0) != (tail == '') or (tail.isascii() and
                len(tail.encode()) != min(count, 8192))):
            refuse('case_output')
    # A controller timeout, malformed protocol or missing proof never becomes a
    # client compatibility finding. Preserve the native output and stop here.
    if (value['observation'] != 'exited' or value['termination_requested'] is not False
            or type(value['wrapper_returncode']) is not int or value['wrapper_returncode'] != 0):
        refuse('case_unexpected')
    records = value['proof_records']
    if (type(records) is not list or len(records) != 6
            or any(type(row) is not list or len(row) != 7 or any(not integer(cell, -2**31, 2**31-1) for cell in row) for row in records)
            or [row[0] for row in records] != [1, 2, 6, 3, 4, 5]):
        refuse('case_proof')
    parent, install, guard, kernel, execute, wait = [row[1:] for row in records]
    if (not integer(parent[0], 1, 2**31-1) or parent[2:4] != [1, 0]
            or not integer(parent[4], 1, 2**31-1) or parent[0] == parent[4] or parent[5] != 0
            or (parent[1] != 0 if mode == 'unfiltered' else not 1 <= parent[1] <= 4096)
            or install[0] != 0 or not integer(install[1], 1, 2**31-1)
            or install[1] in (parent[0], parent[4]) or install[2:] != [int(mode != 'unfiltered'), 0, 0, 0]
            or guard[0] not in (1, 13) or guard[1:] != [1, 7, 1, 0, 0]
            or kernel != [1 if mode == 'patched' else 0]*2+[0, 0, 0, 0]
            or execute != [0, install[1], 0, 0, 0, 0] or wait[2] not in (0, 1) or wait[3:] != [0, 0, 0]):
        refuse('case_proof')
    if wait[1] == 0 and 0 <= wait[0] <= 255:
        code, signal_number = wait[0], None
    elif wait[0] == -1 and 1 <= wait[1] <= 64:
        code, signal_number = None, wait[1]
    else:
        refuse('case_wait')
    if (value['exit_code'] != code or value['signal'] != signal_number
            or (code is not None and type(value['exit_code']) is not int)
            or (signal_number is not None and type(value['signal']) is not int)):
        refuse('case_wait')
    response = value['initialize_result']
    if value['initialized']:
        if (probe != 'codex-stdio' or value['stdout_bytes'] == 0 or type(response) is not dict
                or set(response) != {'userAgent', 'codexHome', 'platformFamily', 'platformOs'}
                or type(response['userAgent']) is not str or not 0 < len(response['userAgent'].encode()) <= 1024
                or response['codexHome'] != WORK+'/agent-cases-1/'+case+'/codex'
                or response['platformFamily'] != 'unix' or response['platformOs'] != 'linux'):
            refuse('case_initialize')
    elif response is not None:
        refuse('case_initialize')
    if probe != 'codex-stdio' and value['stdin_bytes'] != 0:
        refuse('case_input')
    output, error = value['stdout_tail'], value['stderr_tail']
    expected = False
    if signal_number is None:
        if probe == 'codex-empty-login':
            expected = code == 1 and value['stdout_bytes'] == 0 and value['stderr_bytes'] <= 8192 and error.strip() == 'Not logged in'
        elif code == 0:
            if probe == 'codex-version': expected = value['stdout_bytes'] <= 8192 and output.strip() == 'codex-cli 0.164.0'
            elif probe == 'opencode-version': expected = value['stdout_bytes'] <= 8192 and output.strip() == '1.18.25'
            elif probe == 'opencode-rg': expected = value['stdout_bytes'] == len('sentinel.txt\n') and output == 'sentinel.txt\n'
            elif probe.endswith('-help'): expected = value['stdout_bytes'] > 8192 or bool(output.strip())
            elif probe == 'codex-stdio': expected = value['initialized'] and value['stdin_bytes'] == 267
    if value['expectation_met'] is not expected:
        refuse('case_expectation')


def comparisons(stages):
    result = {}
    for probe in PROBES:
        for mode in ('unfiltered', 'upstream'):
            case = probe+'-'+mode
            if case in stages and stages[case]['expectation_met'] is not True:
                refuse('control_failed')
        last = probe+'-patched'
        if last in stages:
            if any(probe+'-'+mode not in stages for mode in MODES): refuse('comparison_order')
            result[probe] = 'selected_probe_compatible' if stages[last]['expectation_met'] else 'patch_incompatible'
    return result


def parse_stages(stages, operation, payload, *, complete=False):
    ordered = [stage[0] for stage in STAGES[operation]]
    if (type(stages) is not dict or not stages or list(stages) != ordered[:len(stages)]
            or (complete and len(stages) != len(ordered))):
        refuse('stage_order')
    if operation == 'agent-test':
        prefix = {key: stages[key] for key in ('rust-verify', 'compiler-verify', 'source-verify') if key in stages}
        if prefix: full.parse_stages(prefix, 'full-test', complete=False)
    for stage, result in stages.items():
        if stage == 'agent-download': parse_assets(result, downloaded=True)
        elif stage in {'agent-prepare', 'agent-verify', 'agent-final'}:
            parse_assets(result)
            if stage == 'agent-final' and result != stages['agent-verify']: refuse('assets_changed')
        elif stage in {'fixture-prepare', 'fixture-build'}: parse_fixture(result, payload, built=stage=='fixture-build')
        elif stage == 'cases-prepare': parse_cases_prepared(result)
        elif stage in CASES: parse_case(result, stage, stages)
        elif stage == 'source-final' and result != stages['source-verify']: refuse('source_changed')
    comparisons(stages)


def qualify(selection, operation):
    if operation not in OPERATIONS:
        refuse('operation')
    controller = build.read_source(build.FIXTURES/'guest_build_storage.py').decode()
    runtime = build.read_source(build.FIXTURES/'guest_runtime.py').decode()
    inventory = build.read_source(build.FIXTURES/'guest_build_inventory.py').decode()
    sources = capture_sources(operation)
    def inspect(selected, anchor, deadline):
        guest._inspect_guest(selected, anchor, deadline)
        binding = build.host_binding_sha256(selected, anchor)
        bundle = load_bundle(selected.storage.cache_path/'_tmp')
        stages = {}; programs = {}; before = after = runtime_result = None
        for stage, key, _, maximum in STAGES[operation]:
            seconds = min(maximum+100, 1600, int(create._remaining(deadline, 1700))-15)
            script = stage_script(controller, runtime, inventory, sources[key], bundle.payload, operation,
                                  stage, seconds, host_binding_sha256=binding, completed=stages)
            argv = [str(anchor.sources[0].identity.path), 'shell', '--tty=false', '--start=false',
                    '--workdir', '/', 'q', '--', '/usr/bin/sudo', '-n', '/usr/bin/python3', '-I', '-c', build.encode_program(script)]
            raw = create._command(selected, argv, deadline, 'guest_agent', seconds+30)
            observed = parse_stage(create._json(raw), operation, stage)
            stages[stage] = observed['result']; programs[stage] = hashlib.sha256(script.encode()).hexdigest()
            parse_stages(stages, operation, bundle.payload)
            if before is None:
                before = observed['inventory_before']; runtime_result = observed['runtime']
            after = observed['inventory_after']
        parse_stages(stages, operation, bundle.payload, complete=True)
        return {'status': 'agent_operation_completed', 'operation': operation, 'runtime': runtime_result,
                'stages': stages, 'inventory_before': before, 'inventory_after': after, 'unmounted_verified': True,
                'comparisons': comparisons(stages),
                **FLAGS, 'source_hashes': bundle.source_hashes | {key: hashlib.sha256(raw.encode()).hexdigest() for key, raw in sources.items()},
                'program_sha256': programs, 'controller_sha256': hashlib.sha256(controller.encode()).hexdigest()}
    lifecycle, result = boot._qualify_with_inspection(selection, inspect, qualification_seconds=1800)
    return build.BuildObservation(operation, lifecycle, result)
