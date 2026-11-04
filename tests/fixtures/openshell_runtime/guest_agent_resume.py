"""Revalidate retained comparison inputs without creating or executing artifacts.

The host admits the historical receipt before boot. These checks independently
bind its identities to current files under the existing capped service policy.
"""


def agent_build_verify(payload):
    """Authenticate the retained source and held static fixture against its receipt."""
    report = payload.get('agent_build_report')
    prepared_keys = {'schema_version', 'generation', 'status', 'source_sha256',
                     'session_enabled', 'full_runtime_qualified', 'compatibility_qualified'}
    built_keys = prepared_keys | {'binary_sha256', 'binary_bytes', 'binary_layout', 'static_arm64'}
    if (type(report) is not dict or set(report) != built_keys or 'fixture_files' in payload
            or report['status'] != 'agent_fixture_built' or report['static_arm64'] is not True
            or type(report['binary_bytes']) is not int or not 0 < report['binary_bytes'] <= 64*1024**2
            or type(report['binary_sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', report['binary_sha256']) is None):
        agent_build_fail('resume_report')
    layout = report['binary_layout']
    if (type(layout) is not dict or set(layout) != {'link_count', 'companion'}
            or type(layout['link_count']) is not int or layout['link_count'] not in (1, 2)
            or (layout['link_count'] == 1 and layout['companion'] is not None)
            or (layout['link_count'] == 2 and (type(layout['companion']) is not str
                or re.fullmatch('openshell_agent_filter_probe-[0-9a-f]{16}', layout['companion']) is None))):
        agent_build_fail('resume_layout')
    prepared = {key: report[key] for key in prepared_keys}
    prepared['status'] = 'agent_fixture_prepared'
    selected = {'agent_build_report': prepared}
    files = agent_build_retained(selected)
    with full_cargo_runtime_artifact('agent-probe') as (fd, current_layout):
        size = os.fstat(fd).st_size
        value = full_cargo_runtime_digest(fd, 'agent-probe')
        if (size != report['binary_bytes'] or value != report['binary_sha256'] or current_layout != layout):
            agent_build_fail('resume_binary')
        if verify_static_arm64(Path(f'/proc/self/fd/{fd}')) != value:
            agent_build_fail('static_hash_changed')
        if full_cargo_runtime_digest(fd, 'agent-probe') != value:
            agent_build_fail('binary_changed')
        if agent_build_retained(selected) != files:
            agent_build_fail('source_changed')
    return dict(agent_build_report(files, 'agent_fixture_verified'), binary_sha256=value,
                binary_bytes=size, binary_layout=current_layout, static_arm64=True)


def agent_cases_verify(payload):
    """Require all selected cases to remain logically fresh; never reset state."""
    agent_platform(); agent_capacity()
    root = WORK/'agent-cases-1'
    before = agent_metadata(root, directory=True)
    if stat.S_IMODE(before.st_mode) != 0o700:
        raise RuntimeError('agent_cases_identity')
    identity = full_cargo_identity(before)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        if full_cargo_identity(os.fstat(fd)) != identity:
            raise RuntimeError('agent_cases_identity')
        expected = set(AGENT_CASES); found = set()
        with os.scandir(fd) as entries:
            for entry in entries:
                remaining()
                if (entry.name not in expected or entry.name in found
                        or not stat.S_ISDIR(entry.stat(follow_symlinks=False).st_mode)):
                    raise RuntimeError('agent_cases_entries')
                found.add(entry.name)
        if found != expected:
            raise RuntimeError('agent_cases_entries')
        for case in AGENT_CASES:
            remaining(); agent_fresh_case(case)
        state = agent_state_bytes(); agent_capacity()
        if (full_cargo_identity(os.fstat(fd)) != identity
                or full_cargo_identity(root.lstat()) != identity):
            raise RuntimeError('agent_cases_identity')
    finally:
        os.close(fd)
    return {'schema_version': 1, 'generation': 1, 'status': 'agent_cases_verified',
            'cases': list(AGENT_CASES), 'initial_sha256': {
                'codex_config': hashlib.sha256(AGENT_CODEX_CONFIG).hexdigest(),
                'opencode_gitignore': hashlib.sha256(AGENT_GITIGNORE).hexdigest(),
                'sentinel': hashlib.sha256(AGENT_SENTINEL).hexdigest()},
            'case_state_bytes': state, **AGENT_FLAGS}
