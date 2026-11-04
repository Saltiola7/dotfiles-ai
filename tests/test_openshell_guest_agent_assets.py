"""Synthetic package admission; no agent execution, network or native VM proof."""
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tarfile
import time
from types import ModuleType
import urllib.request

import pytest


BASE = Path(__file__).parent/'fixtures/openshell_runtime'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def elf(*, machine=183, interpreter=None, needed=None):
    data = bytearray(1024)
    data[:16] = b'\x7fELF\x02\x01\x01'+bytes(9)
    count = 1 + bool(interpreter) + bool(needed)
    struct.pack_into('<HHIQQQIHHHHHH', data, 16, 3, machine, 1, 0, 64, 0, 0, 64, 56, count, 0, 0, 0)
    struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, 0, 0, 0, len(data), len(data), 4096)
    at = 120
    if interpreter:
        raw = interpreter.encode()+b'\0'; data[400:400+len(raw)] = raw
        struct.pack_into('<IIQQQQQQ', data, at, 3, 4, 400, 400, 0, len(raw), len(raw), 1); at += 56
    if needed:
        strings = b'\0'+needed.encode()+b'\0'; data[800:800+len(strings)] = strings
        for number, value in enumerate([(5, 800), (10, len(strings)), (1, 1), (0, 0)]):
            struct.pack_into('<qQ', data, 600+number*16, *value)
        struct.pack_into('<IIQQQQQQ', data, at, 2, 4, 600, 600, 0, 64, 64, 8)
    return bytes(data)


def archive(records, *, tail=b''):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT) as stream:
        for name, kind, raw, mode in records:
            member = tarfile.TarInfo(name); member.mode = mode
            if kind == 'directory': member.type = tarfile.DIRTYPE
            elif kind in {'symlink', 'hardlink'}:
                member.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE; member.linkname = raw.decode()
            elif kind == 'fifo': member.type = tarfile.FIFOTYPE
            else:
                member.size = len(raw)
                if kind == 'contiguous': member.type = tarfile.CONTTYPE
            stream.addfile(member, io.BytesIO(raw) if kind in {'file', 'contiguous'} else None)
    return gzip.compress(output.getvalue()+tail)


@pytest.fixture
def assets(tmp_path, monkeypatch):
    path = BASE/'guest_agent_assets.py'
    assert path.is_file(), 'agent asset helper absent: intended red'
    module = ModuleType('guest_agent_assets_test')
    exec(compile((BASE/'guest_harness.py').read_text()+'\n'+path.read_text(), str(path), 'exec'), module.__dict__)
    monkeypatch.setattr(module, 'WORK', tmp_path)
    monkeypatch.setattr(module, 'DEADLINE', time.monotonic()+60)
    contract = copy.deepcopy(module.agent_assets_contract)
    monkeypatch.setattr(module, 'agent_assets_contract', contract)
    metadata = module.agent_assets_codex_metadata
    records = {
        'codex': [(name, 'directory', b'', 0o755) for name in ('bin', 'codex-resources', 'codex-path')]
            + [('codex-package.json', 'file', json.dumps(metadata).encode(), 0o644)]
            + [(name, 'file', elf()+name.encode(), 0o755) for name in ('bin/codex', 'bin/codex-code-mode-host', 'codex-resources/bwrap', 'codex-path/rg')],
        'opencode': [('opencode', 'file', elf(interpreter='/lib/ld-linux-aarch64.so.1', needed='libc.so.6'), 0o755)],
    }
    omissions = json.loads((BASE/'agentcheck/voice-omissions.json').read_text())
    for name, item in omissions['entries'].items():
        raw = b'' if item['kind'] == 'directory' else ('omitted '+name).encode()
        item['bytes'] = len(raw)
        records['codex'].append((name, item['kind'], raw, item['mode']))
    inputs = tmp_path/'agent-assets-inputs-1'; inputs.mkdir(mode=0o700)
    for name, rows in records.items():
        raw = archive(rows); item = contract['assets'][name]
        item.update(bytes=len(raw), sha256=sha(raw), expanded_limit=65536 if name == 'codex' else 32768)
        (inputs/item['archive']).write_bytes(raw); (inputs/item['archive']).chmod(0o600)
    omissions['archive_sha256'] = contract['assets']['codex']['sha256']
    monkeypatch.setattr(module, 'agent_assets_voice_sha256', sha(json.dumps(omissions, sort_keys=True, separators=(',', ':')).encode()), raising=False)
    payload = {'agent_manifest': copy.deepcopy(contract), 'voice_omissions': omissions}
    monkeypatch.setattr(module.urllib.request, 'build_opener', lambda *args: pytest.fail('unexpected network'))
    return module, payload, records


def replace_archive(assets, name, records, *, tail=b'', extra=b''):
    module, payload, _ = assets
    raw = archive(records, tail=tail)+extra
    item = module.agent_assets_contract['assets'][name]
    item.update(bytes=len(raw), sha256=sha(raw))
    payload['agent_manifest'] = copy.deepcopy(module.agent_assets_contract)
    if name == 'codex':
        payload['voice_omissions']['archive_sha256'] = item['sha256']
        module.agent_assets_voice_sha256 = sha(json.dumps(payload['voice_omissions'], sort_keys=True, separators=(',', ':')).encode())
    path = module.WORK/'agent-assets-inputs-1'/item['archive']; path.write_bytes(raw)
    return path


def test_manifest_pins_exact_public_assets(assets):
    module, _, _ = assets
    actual = json.loads((BASE/'agentcheck/manifest.json').read_text())
    assert set(actual) == {'schema_version', 'generation', 'assets'}
    assert actual['assets']['codex']['bytes'] == 152400557
    assert actual['assets']['codex']['sha256'] == '5918add6c7e9cf1e14a9af1b4c0f4bf1d24a43903faac26df5dc4c019ea91bd5'
    assert actual['assets']['opencode']['bytes'] == 60345335
    assert actual['assets']['opencode']['sha256'] == '35ef77897425e41b5183a2c21ac4fb1d4d944d82a94e3c920f57b5490af11ac5'
    assert [actual['assets'][key]['expanded_limit'] for key in ('codex', 'opencode')] == [1024**3, 512*1024**2]


def test_prepare_verify_same_closed_report_and_no_execution(assets, monkeypatch):
    module, payload, _ = assets
    monkeypatch.setattr(module, 'command', lambda *a, **k: pytest.fail('asset execution'))
    report = module.agent_assets_prepare(payload)
    root = module.WORK/'agent-assets-1'
    before = {p: module.agent_assets_identity(p.lstat()) for p in root.rglob('*')}
    assert report == module.agent_assets_verify(payload) == module.agent_assets_prepare(payload)
    assert before == {p: module.agent_assets_identity(p.lstat()) for p in root.rglob('*')}
    assert report['status'] == 'agent_assets_verified' and report['generation'] == 1
    assert all(report[key] is False for key in ('session_enabled', 'full_runtime_qualified', 'compatibility_qualified'))
    assert set(report['assets']['codex']['files']) == {'codex-package.json', 'bin/codex', 'bin/codex-code-mode-host', 'codex-resources/bwrap', 'codex-path/rg'}
    assert report['assets']['opencode']['files']['opencode']['elf'] == {
        'machine':183, 'kind':3, 'interpreter':'/lib/ld-linux-aarch64.so.1', 'needed':['libc.so.6']}
    assert report['codex_metadata'] == module.agent_assets_codex_metadata
    for name, entry in report['assets'].items():
        for path, item in entry['files'].items():
            selected = root/name/path
            assert item['sha256'] == sha(selected.read_bytes()) and item['bytes'] == selected.stat().st_size
            assert stat.S_IMODE(selected.stat().st_mode) == item['mode'] == (0o400 if path.endswith('.json') else 0o500)


@pytest.mark.parametrize('kind', ['digest', 'length', 'symlink', 'hardlink', 'unknown', 'deadline', 'manifest', 'bool'])
def test_input_contract_refuses_before_prefix_publication(assets, monkeypatch, kind):
    module, payload, _ = assets; inputs = module.WORK/'agent-assets-inputs-1'
    path = inputs/payload['agent_manifest']['assets']['codex']['archive']
    if kind == 'digest': path.write_bytes(b'x'*path.stat().st_size)
    elif kind == 'length': path.write_bytes(b'bad')
    elif kind == 'symlink': path.rename(inputs/'saved'); path.symlink_to(inputs/'saved')
    elif kind == 'hardlink': os.link(path, module.WORK/'alias')
    elif kind == 'unknown': (inputs/'unexpected').write_bytes(b'unknown')
    elif kind == 'deadline': monkeypatch.setattr(module, 'DEADLINE', 0)
    elif kind == 'manifest': payload['agent_manifest']['assets']['codex']['url'] = 'https://evil.example/asset'
    else: payload['agent_manifest']['schema_version'] = True
    with pytest.raises(RuntimeError): module.agent_assets_prepare(payload)
    assert not (module.WORK/'agent-assets-1').exists()


@pytest.mark.parametrize('kind', ['missing', 'unknown', 'duplicate', 'symlink', 'hardlink', 'fifo', 'contiguous', 'traversal', 'absolute', 'special_mode', 'no_exec', 'empty', 'expansion', 'trailing_tar', 'trailing_gzip'])
def test_authenticated_unsafe_archive_refuses_both_prefixes(assets, kind):
    module, payload, records = assets; rows = list(records['opencode']); tail = extra = b''
    if kind == 'missing': rows = []
    elif kind == 'unknown': rows += [('extra', 'file', b'x', 0o644)]
    elif kind == 'duplicate': rows += rows
    elif kind in {'symlink', 'hardlink', 'fifo'}: rows = [('opencode', kind, b'elsewhere', 0o755)]
    elif kind == 'contiguous': rows = [('opencode', kind, elf(), 0o755)]
    elif kind in {'traversal', 'absolute'}: rows = [('../opencode' if kind == 'traversal' else '/opencode', *rows[0][1:])]
    elif kind == 'special_mode': rows = [('opencode', 'file', elf(), 0o4755)]
    elif kind == 'no_exec': rows = [('opencode', 'file', elf(), 0o644)]
    elif kind == 'empty': rows = [('opencode', 'file', b'', 0o755)]
    elif kind == 'expansion': rows = [('opencode', 'file', b'x'*65536, 0o755)]
    elif kind == 'trailing_tar': tail = b'x'*512
    else: extra = gzip.compress(b'additional stream')
    replace_archive(assets, 'opencode', rows, tail=tail, extra=extra)
    with pytest.raises(RuntimeError): module.agent_assets_prepare(payload)
    assert not (module.WORK/'agent-assets-1').exists()


@pytest.mark.parametrize('kind', ['version', 'unknown', 'duplicate', 'bool', 'machine', 'loader', 'needed_escape', 'needed_parent', 'no_load', 'elf_truncated'])
def test_package_json_and_elf_preflight_precedes_any_write(assets, kind):
    module, payload, records = assets
    if kind in {'version', 'unknown', 'duplicate', 'bool'}:
        metadata = dict(module.agent_assets_codex_metadata)
        if kind == 'version': metadata['version'] = 'other'
        elif kind == 'unknown': metadata['extra'] = True
        elif kind == 'bool': metadata['layoutVersion'] = True
        raw = json.dumps(metadata).encode()
        if kind == 'duplicate': raw = raw[:-1]+b',"version":"0.164.0"}'
        rows = [(n, t, raw if n == 'codex-package.json' else b, m) for n,t,b,m in records['codex']]
        replace_archive(assets, 'codex', rows)
    else:
        no_load = bytearray(elf()); struct.pack_into('<I', no_load, 64, 4)
        raw = {'machine':elf(machine=62), 'loader':elf(interpreter='relative-loader'),
               'needed_escape':elf(needed='../lib.so'), 'needed_parent':elf(needed='..'),
               'no_load':bytes(no_load), 'elf_truncated':b'\x7fELF'}[kind]
        replace_archive(assets, 'opencode', [('opencode', 'file', raw, 0o755)])
    with pytest.raises(RuntimeError): module.agent_assets_prepare(payload)
    assert not (module.WORK/'agent-assets-1').exists()


@pytest.mark.parametrize('kind', ['content', 'missing', 'extra', 'symlink', 'hardlink', 'mode'])
def test_retained_prefix_drift_never_repaired(assets, kind):
    module, payload, _ = assets; module.agent_assets_prepare(payload)
    root = module.WORK/'agent-assets-1'; path = root/'opencode/opencode'
    if kind == 'content': path.chmod(0o600); path.write_bytes(b'changed'); path.chmod(0o500)
    elif kind == 'missing': path.unlink()
    elif kind == 'extra': (root/'unexpected').write_bytes(b'x')
    elif kind == 'symlink': path.unlink(); path.symlink_to(module.WORK/'missing')
    elif kind == 'hardlink': os.link(path, module.WORK/'alias')
    else: path.chmod(0o700)
    snapshot = sorted(str(p.relative_to(root)) for p in root.rglob('*'))
    for call in (module.agent_assets_prepare, module.agent_assets_verify):
        with pytest.raises(RuntimeError): call(payload)
    assert snapshot == sorted(str(p.relative_to(root)) for p in root.rglob('*'))


@pytest.mark.parametrize('kind', ['directory', 'dangling_symlink'])
def test_partial_or_alias_destination_refuses_without_adoption(assets, kind):
    module, payload, _ = assets; root = module.WORK/'agent-assets-1'
    if kind == 'directory': root.mkdir(mode=0o700)
    else: root.symlink_to(module.WORK/'absent')
    with pytest.raises(RuntimeError): module.agent_assets_prepare(payload)
    assert os.path.lexists(root)


@pytest.mark.parametrize('kind', ['valid', 'overflow', 'short', 'digest', 'status', 'interrupted'])
def test_download_is_bounded_exclusive_and_retains_failed_partial(assets, monkeypatch, kind):
    module, payload, _ = assets; item = payload['agent_manifest']['assets']['codex']
    path = module.WORK/'agent-assets-inputs-1'/item['archive']; raw = path.read_bytes(); path.unlink()
    if kind == 'overflow': raw += b'extra'
    elif kind == 'short': raw = raw[:-1]
    elif kind == 'digest': raw = b'x'*len(raw)
    class Response(io.BytesIO):
        status = 503 if kind == 'status' else 200
        url = 'https://release-assets.githubusercontent.com/fixed-public-asset'
        def read1(self, size):
            if kind == 'interrupted': raise OSError('public download interrupted')
            return self.read(min(size, 37))
    class Opener:
        def open(self, request, *, timeout):
            assert request.full_url == item['url'] and 0 < timeout <= 20
            assert not any(key.lower() in {'authorization', 'cookie'} for key in request.headers)
            return Response(raw)
    def opener(*handlers):
        assert any(isinstance(handler, urllib.request.ProxyHandler) and handler.proxies == {} for handler in handlers)
        return Opener()
    monkeypatch.setattr(module.urllib.request, 'build_opener', opener)
    if kind == 'valid':
        report = module.agent_assets_download(payload)
        assert report['status'] == 'agent_assets_downloaded' and path.read_bytes() == raw
        assert not path.with_name(path.name+'.partial').exists()
    else:
        with pytest.raises(RuntimeError): module.agent_assets_download(payload)
        assert not path.exists() and path.with_name(path.name+'.partial').is_file()
        with pytest.raises(RuntimeError): module.agent_assets_download(payload)
    assert not (module.WORK/'agent-assets-1').exists()


@pytest.mark.parametrize('url', ['http://release-assets.githubusercontent.com/a', 'https://evil.example/a', 'https://release-assets.githubusercontent.com.evil.example/a', 'https://user@release-assets.githubusercontent.com/a', 'https://release-assets.githubusercontent.com:444/a'])
def test_redirect_rejects_unselected_transport(assets, url):
    module, payload, _ = assets; item = payload['agent_manifest']['assets']['codex']
    handler = module.agent_assets_Redirect(item['url'])
    with pytest.raises(RuntimeError): handler.redirect_request(urllib.request.Request(item['url']), None, 302, '', {}, url)


def test_redirect_chain_is_bounded(assets):
    module, payload, _ = assets; original = payload['agent_manifest']['assets']['codex']['url']
    handler = module.agent_assets_Redirect(original); request = urllib.request.Request(original)
    for number in range(2):
        request = handler.redirect_request(request, None, 302, '', {}, f'https://release-assets.githubusercontent.com/{number}')
    with pytest.raises(RuntimeError): handler.redirect_request(request, None, 302, '', {}, 'https://release-assets.githubusercontent.com/third')


def test_archive_change_after_preflight_refuses_before_publication(assets, monkeypatch):
    module, payload, _ = assets; scan = module.agent_assets_scan
    path = module.WORK/'agent-assets-inputs-1'/payload['agent_manifest']['assets']['codex']['archive']
    def changed(fd, name, item, **kwargs):
        result = scan(fd, name, item, **kwargs)
        if name == 'opencode': path.write_bytes(b'x'*path.stat().st_size)
        return result
    monkeypatch.setattr(module, 'agent_assets_scan', changed)
    monkeypatch.setattr(module, 'agent_assets_mkdir', lambda *a: pytest.fail('published after archive changed'))
    with pytest.raises(RuntimeError, match='agent_assets_'): module.agent_assets_prepare(payload)


def test_download_report_rechecks_both_completed_archives(assets, monkeypatch):
    module, payload, _ = assets; download = module.agent_assets_download_one
    codex = payload['agent_manifest']['assets']['codex']; path = module.WORK/'agent-assets-inputs-1'/codex['archive']
    def changed(inputs, item):
        download(inputs, item)
        if item['version'] == '1.18.25': path.write_bytes(b'x'*path.stat().st_size)
    monkeypatch.setattr(module, 'agent_assets_download_one', changed)
    with pytest.raises(RuntimeError, match='agent_assets_'): module.agent_assets_download(payload)


@pytest.mark.parametrize('kind', ['unknown', 'duplicate', 'special_mode', 'long_name'])
def test_member_refusal_reports_only_bounded_archive_metadata(assets, kind):
    module, payload, records = assets
    rows = list(records['opencode']); index = 0
    if kind == 'unknown': rows = [('unexpected', 'file', b'private payload is never logged', 0o755)]
    elif kind == 'duplicate': rows += rows; index = 1
    elif kind == 'special_mode': rows = [('opencode', 'file', elf(), 0o4755)]
    else: rows = [('🌕'*300+'\n', 'file', b'private payload is never logged', 0o755)]
    replace_archive(assets, 'opencode', rows)
    with pytest.raises(RuntimeError, match='agent_assets_archive_member') as caught:
        module.agent_assets_prepare(payload)
    message = str(caught.value)
    detail = json.loads(message.split(':', 1)[1])
    assert set(detail) == {'asset', 'index', 'name_repr', 'type_repr', 'mode', 'duplicate', 'unknown', 'inventory'}
    assert detail['asset'] == 'opencode' and detail['index'] == index
    assert detail['name_repr'] == repr(rows[index][0])[:160]
    assert detail['type_repr'] == "b'0'" and detail['mode'] == oct(rows[index][3])
    assert detail['duplicate'] is (kind == 'duplicate')
    assert detail['unknown'] is (kind in ('unknown', 'long_name'))
    assert detail['inventory']['status'] == 'complete'
    assert len(detail['inventory']['entries']) == len(rows)
    assert len(detail['name_repr']) <= 160 and len(message.encode()) <= 24576
    assert '\n' not in message and 'private payload' not in message
    assert not (module.WORK/'agent-assets-1').exists()


@pytest.mark.parametrize('kind', ['complete', 'entry_limit', 'byte_limit'])
def test_refusal_header_inventory_is_bounded_and_never_extracts(assets, monkeypatch, kind):
    module, payload, _ = assets
    count = 162 if kind == 'entry_limit' else 30 if kind == 'byte_limit' else 5
    rows = [('unexpected-'+('🌕'*160 if kind == 'byte_limit' else '')+str(index), 'file', b'not extracted', 0o644)
            for index in range(count)]
    module.agent_assets_contract['assets']['opencode']['expanded_limit'] = 512*1024
    path = replace_archive(assets, 'opencode', rows)
    monkeypatch.setattr(module.tarfile.TarFile, 'extractfile', lambda *a, **k: pytest.fail('diagnostic extracted a member'))
    with module.agent_assets_hold(path, mode=0o600) as fd:
        with pytest.raises(RuntimeError, match='agent_assets_archive_member:') as caught:
            module.agent_assets_scan(fd, 'opencode', payload['agent_manifest']['assets']['opencode'])
    message = str(caught.value); detail = json.loads(message.split(':', 1)[1]); inventory = detail['inventory']
    assert detail['unknown'] is True and detail['index'] == 0 and detail['asset'] == 'opencode'
    assert len(message.encode()) <= 24576 and len(inventory['entries']) <= 160
    for index, item in enumerate(inventory['entries']):
        assert item == {'index': index, 'name_repr': repr(rows[index][0])[:160],
                        'type_repr': "b'0'", 'mode': '0o644', 'bytes': len(b'not extracted')}
    if kind == 'complete': assert inventory['status'] == 'complete' and len(inventory['entries']) == count
    else:
        assert inventory['status'] == 'limited' and inventory['error'] == kind
        assert len(inventory['entries']) < count
    assert not (module.WORK/'agent-assets-1').exists()


@pytest.mark.parametrize('kind', ['io', 'deadline'])
def test_header_inventory_failure_preserves_original_refusal_without_exception_text(assets, monkeypatch, kind):
    module, payload, _ = assets
    path = replace_archive(assets, 'opencode', [('unexpected', 'file', b'body', 0o644)])
    gzip_reader = module.agent_assets_Gzip; calls = []
    def fail_second(fd, limit):
        calls.append(True)
        if len(calls) == 2:
            if kind == 'deadline': raise RuntimeError('harness_deadline')
            raise OSError('private exception contents must not be included')
        return gzip_reader(fd, limit)
    monkeypatch.setattr(module, 'agent_assets_Gzip', fail_second)
    with module.agent_assets_hold(path, mode=0o600) as fd:
        with pytest.raises(RuntimeError, match='agent_assets_archive_member:') as caught:
            module.agent_assets_scan(fd, 'opencode', payload['agent_manifest']['assets']['opencode'])
    message = str(caught.value); detail = json.loads(message.split(':', 1)[1])
    assert detail['unknown'] is True and detail['name_repr'] == "'unexpected'"
    assert detail['inventory']['status'] == 'incomplete'
    assert detail['inventory']['error'] == ('deadline' if kind == 'deadline' else 'io')
    assert 'private exception' not in message and not (module.WORK/'agent-assets-1').exists()


def test_source_module_bound_and_no_automatic_entrypoint():
    raw = (BASE/'guest_agent_assets.py').read_text()
    assert len(raw.encode()) <= 32*1024 and '__main__' not in raw


def test_voice_manifest_has_exact_authenticated_native_header_inventory():
    value = json.loads((BASE/'agentcheck/voice-omissions.json').read_text())
    assert sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()) == '478394bae952fff452aa79788abe07f3b2a44b1439c88b91da2919250cde7780'
    assert len(value['entries']) == 43
    assert sum(item['kind'] == 'directory' for item in value['entries'].values()) == 5
    assert sum(item['bytes'] for item in value['entries'].values()) == 55864949


def test_voice_subset_hashes_every_omission_and_never_publishes_it(assets, monkeypatch):
    module, payload, records = assets
    name = 'codex-resources/voice/NOTICE.md'
    records['codex'] = [(path, kind, b'x'*150000 if path == name else raw, mode)
                       for path, kind, raw, mode in records['codex']]
    payload['voice_omissions']['entries'][name]['bytes'] = 150000
    module.agent_assets_contract['assets']['codex']['expanded_limit'] = 256*1024
    replace_archive(assets, 'codex', records['codex'])
    original = module.tarfile.TarFile.extractfile; reads = []
    class BoundedReader:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def read(self, size=-1):
            assert 0 < size <= 65536
            reads.append(size)
            return self.stream.read(size)
    def extract(archive, member):
        stream = original(archive, member)
        return BoundedReader(stream) if member.name in payload['voice_omissions']['entries'] else stream
    monkeypatch.setattr(module.tarfile.TarFile, 'extractfile', extract)
    result = module.agent_assets_prepare(payload)
    assert reads and result == module.agent_assets_verify(payload)
    codex = result['assets']['codex']; opencode = result['assets']['opencode']
    assert codex['package_scope'] == 'probe_subset_without_voice'
    assert opencode['package_scope'] == 'complete' and opencode['omitted_entries'] == {}
    raw = {name: value for name, _, value, _ in records['codex']}
    assert codex['omitted_entries'] == {name: item | {'sha256': sha(raw[name]) if item['kind'] == 'file' else None}
        for name, item in payload['voice_omissions']['entries'].items()}
    assert codex['expanded_bytes'] == sum(item['bytes'] for item in codex['files'].values())
    assert not (module.WORK/'agent-assets-1/codex/codex-resources/voice').exists()


@pytest.mark.parametrize('operation', ['download', 'prepare', 'verify'])
@pytest.mark.parametrize('kind', ['missing', 'digest', 'schema_bool', 'archive', 'unknown'])
def test_voice_selection_refuses_before_any_effect(assets, monkeypatch, operation, kind):
    module, payload, _ = assets
    if kind == 'missing': del payload['voice_omissions']
    elif kind == 'digest': payload['voice_omissions']['entries']['codex-resources/voice']['mode'] = 0o700
    elif kind == 'schema_bool': payload['voice_omissions']['schema_version'] = True
    elif kind == 'archive': payload['voice_omissions']['archive_sha256'] = '0'*64
    else: payload['voice_omissions']['extra'] = True
    monkeypatch.setattr(module, 'agent_assets_inputs', lambda **kw: pytest.fail('input access before omission selection'))
    with pytest.raises(RuntimeError, match='agent_assets_voice_selection'):
        getattr(module, 'agent_assets_'+operation)(payload)


@pytest.mark.parametrize('kind', ['missing', 'unknown', 'mode', 'size', 'symlink', 'hardlink', 'fifo', 'contiguous', 'directory_file', 'duplicate'])
def test_voice_headers_are_exact_and_not_a_prefix_allowance(assets, kind):
    module, payload, records = assets; rows = list(records['codex'])
    name = 'codex-resources/voice/NOTICE.md'
    at = next(index for index, row in enumerate(rows) if row[0] == name)
    path, _, raw, mode = rows[at]
    if kind == 'missing': rows.pop(at)
    elif kind == 'unknown': rows.append(('codex-resources/voice/unselected', 'file', b'ignored?', 0o644))
    elif kind == 'mode': rows[at] = (path, 'file', raw, 0o600)
    elif kind == 'size': rows[at] = (path, 'file', raw+b'x', mode)
    elif kind == 'duplicate': rows.append(rows[at])
    elif kind == 'directory_file':
        at = next(index for index, row in enumerate(rows) if row[0] == 'codex-resources/voice')
        rows[at] = ('codex-resources/voice', 'file', b'', 0o755)
    else: rows[at] = (path, kind, raw, mode)
    replace_archive(assets, 'codex', rows)
    with pytest.raises(RuntimeError, match='agent_assets_'): module.agent_assets_prepare(payload)
    assert not (module.WORK/'agent-assets-1').exists()


def test_voice_bytes_share_the_original_expansion_limit(assets):
    module, payload, records = assets
    rows = [(name, kind, b'x'*70000 if name == 'codex-resources/voice/NOTICE.md' else raw, mode)
            for name, kind, raw, mode in records['codex']]
    payload['voice_omissions']['entries']['codex-resources/voice/NOTICE.md']['bytes'] = 70000
    replace_archive(assets, 'codex', rows)
    with pytest.raises(RuntimeError, match='agent_assets_'): module.agent_assets_prepare(payload)
    assert not (module.WORK/'agent-assets-1').exists()


def test_voice_second_pass_compares_hashes_before_success(assets, monkeypatch):
    module, payload, _ = assets
    original = module.tarfile.TarFile.extractfile; visits = []
    def extract(archive, member):
        stream = original(archive, member)
        if member.name == 'codex-resources/voice/NOTICE.md':
            visits.append(True)
            if len(visits) == 2:
                raw = stream.read(); stream.close()
                return io.BytesIO(b'!' + raw[1:])
        return stream
    monkeypatch.setattr(module.tarfile.TarFile, 'extractfile', extract)
    with pytest.raises(RuntimeError, match='agent_assets_archive_changed'):
        module.agent_assets_prepare(payload)
    assert len(visits) == 2
    assert not (module.WORK/'agent-assets-1/codex/codex-resources/voice').exists()
