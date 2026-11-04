"""Offline synthetic qualification for the bounded full Cargo transaction."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tarfile
import time
from types import ModuleType

import pytest


BASE = Path(__file__).parent / 'fixtures/openshell_runtime'


@pytest.fixture
def full(tmp_path, monkeypatch):
    helper = BASE / 'guest_full_cargo.py'
    assert helper.is_file(), 'full Cargo helper absent: intended red'
    module = ModuleType('full_cargo_test')
    sys.modules[module.__name__] = module
    exec(compile((BASE/'guest_harness.py').read_text()+'\n'+helper.read_text(), str(helper), 'exec'), module.__dict__)
    monkeypatch.setattr(module, 'WORK', tmp_path)
    monkeypatch.setattr(module, 'DEADLINE', time.monotonic()+60)
    source = tmp_path/'full-source-1'; source.mkdir()
    (source/'.cargo').mkdir()
    (source/'.cargo/config.toml').write_bytes(module.FULL_SOURCE_CONFIG)
    (source/'Cargo.toml').write_text('[workspace]\nmembers = []\n')
    (source/'crates/openshell-sandbox/src/linux').mkdir(parents=True)
    (source/'crates/openshell-sandbox/src/linux/child_seccomp.rs').write_text('patch')
    for name in ('tmp', 'home', 'rustup', 'cache', 'full-c-wrappers-1'):
        (tmp_path/name).mkdir()
    for name in ('cc','as','ar'):
        target=tmp_path/'full-c-wrappers-1'/name; target.write_text('wrapper'); target.chmod(0o500)
    manifest=json.loads((BASE/'fullbuild/manifest.json').read_text())
    manifest['source']['external_packages']=1
    manifest['source']['local_packages']=1
    payload={'full_manifest':manifest,'patched_sha256':hashlib.sha256(b'patch').hexdigest()}
    return module, payload, source


def locked(full, checksum='1'*64, source='registry+https://github.com/rust-lang/crates.io-index'):
    module,payload,root=full
    raw=(f'version = 4\n[[package]]\nname = "openshell-sandbox"\nversion = "{module.FULL_VERSION}"\n'
         f'[[package]]\nname = "example"\nversion = "1.0.0"\nsource = "{source}"\nchecksum = "{checksum}"\n').encode()
    (root/'Cargo.lock').write_bytes(raw)
    payload['full_manifest']['source']['derived_lock_sha256']=hashlib.sha256(raw).hexdigest()
    return raw


def crate(full, *, entries=None):
    module,payload,source=full
    registry=module.WORK/'full-cargo-1/registry'
    index='index.crates.io-1949cf8c6b5b557f'
    cache=registry/'cache'/index; cache.mkdir(parents=True)
    extracted=registry/'src'/index/'example-1.0.0'; extracted.mkdir(parents=True)
    index_path=registry/'index'/index; index_path.mkdir(parents=True)
    (index_path/'config.json').write_text(json.dumps({'dl':'https://static.crates.io/crates','api':'https://crates.io'}))
    archive=cache/'example-1.0.0.crate'
    entries=entries or [('Cargo.toml',b'[package]\nname="example"\nversion="1.0.0"\n','file'),('src/lib.rs',b'pub fn x() {}','file')]
    with tarfile.open(archive,'w:gz') as tar:
        for name,data,kind in entries:
            item=tarfile.TarInfo('example-1.0.0/'+name)
            if kind=='file': item.size=len(data); tar.addfile(item,io.BytesIO(data))
            else: item.type=tarfile.SYMTYPE; item.linkname=data.decode(); tar.addfile(item)
            if kind=='file' and '..' not in Path(name).parts and not Path(name).is_absolute():
                path=extracted/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    (extracted/'.cargo-ok').write_text('{"v":1}')
    locked(full,hashlib.sha256(archive.read_bytes()).hexdigest())
    return archive,extracted


def elf(interpreter=None, needed=None, machine=183):
    count=1+(interpreter is not None)+(needed is not None)
    data=bytearray(512)
    data[:16]=b'\x7fELF\x02\x01\x01'+bytes(9)
    struct.pack_into('<HHIQQQIHHHHHH',data,16,3,machine,1,0,64,0,0,64,56,count,0,0,0)
    struct.pack_into('<IIQQQQQQ',data,64,1,5,0,0,0,512,512,4096)
    at=120
    if interpreter:
        value=interpreter.encode()+b'\0';data[300:300+len(value)]=value
        struct.pack_into('<IIQQQQQQ',data,at,3,4,300,300,0,len(value),len(value),1);at+=56
    if needed is not None:
        strings=b'\0'+needed.encode()+b'\0';data[400:400+len(strings)]=strings
        values=[(5,400),(10,len(strings)),(1,1),(0,0)]
        for i,value in enumerate(values):struct.pack_into('<qQ',data,336+16*i,*value)
        struct.pack_into('<IIQQQQQQ',data,at,2,4,336,336,0,64,64,8)
    return bytes(data)


def test_environment_preserves_rust_loader_and_scopes_all_c_compilers(full,monkeypatch):
    module,_,_=full
    monkeypatch.setenv('OPENAI_API_KEY','must-not-inherit')
    env=module.full_cargo_environment()
    assert env['CARGO_HOME']==str(module.WORK/'full-cargo-1')
    assert env['CARGO_TARGET_DIR']==str(module.WORK/'full-target-1')
    assert env['CARGO_CACHE_AUTO_CLEAN_FREQUENCY']=='never'
    assert env['CARGO_BUILD_JOBS']=='2' and env['CARGO_INCREMENTAL']=='0'
    assert env['CARGO_PROFILE_RELEASE_DEBUG']=='0'
    assert env['AWS_LC_SYS_USE_SYSTEM']==env['AWS_LC_SYS_CMAKE_BUILDER']=='0'
    assert env['CC']==env['CC_aarch64_unknown_linux_musl']==str(module.WORK/'full-c-wrappers-1/cc')
    assert env['AR']==env['AR_aarch64_unknown_linux_musl']==str(module.WORK/'full-c-wrappers-1/ar')
    assert env['LD_LIBRARY_PATH']==str(module.WORK/'toolchain-unwind-1/lib')
    assert env['GIT_DIR']=='/nonexistent'
    assert 'OPENAI_API_KEY' not in env


def test_only_authenticated_upstream_config_is_admitted(full):
    module,_,source=full
    assert hashlib.sha256(module.FULL_SOURCE_CONFIG).hexdigest()=='ea8ff3d493f65ec737ee9a98fc91080a6da42441e3fa5fddcba662b7bd27c175'
    module.full_cargo_configs()
    (source/'.cargo/config.toml').write_text('[source.crates-io]\nreplace-with="other"\n')
    with pytest.raises(RuntimeError,match='full_cargo_config'):module.full_cargo_configs()


@pytest.mark.parametrize('name',['config','config.toml','credentials','credentials.toml'])
def test_extra_home_configuration_refuses_without_reading(full,name):
    module,_,_=full
    home=module.WORK/'full-cargo-1';home.mkdir();(home/name).write_text('forbidden')
    with pytest.raises(RuntimeError,match='full_cargo_config'):module.full_cargo_configs()


def test_lock_records_bound_to_selected_hash_and_registry(full):
    module,payload,source=full
    locked(full)
    assert module.full_cargo_lock(payload)=={'example-1.0.0':'1'*64}
    (source/'Cargo.lock').write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='full_cargo_lock'):module.full_cargo_lock(payload)
    locked(full,source='git+https://example.invalid/repo')
    with pytest.raises(RuntimeError,match='full_cargo_lock'):module.full_cargo_lock(payload)


def test_valid_cache_matches_archive_and_extracted_files(full):
    module,payload,_=full
    archive,extracted=crate(full)
    result=module.full_cargo_cache(payload)
    assert result['crates']==1 and result['compressed_bytes']==archive.stat().st_size
    assert result['expanded_bytes']==sum(p.stat().st_size for p in extracted.rglob('*') if p.is_file() and p.name!='.cargo-ok')
    assert len(result['cache_sha256'])==64


def test_authenticated_crate_configs_are_bytes_not_ambient_configuration(full):
    module,payload,_=full
    crate(full,entries=[('.cargo/config.toml',b'[alias]\nexample="--version"\n','file'),
                        ('credentials.toml',b'# public synthetic fixture\n','file'),
                        ('config.toml',b'# package data, not Cargo home config\n','file')])
    assert module.full_cargo_cache(payload)['crates']==1


@pytest.mark.parametrize('corruption',['archive','file','extra','symlink','hardlink','credentials'])
def test_cache_corruption_and_unadmitted_state_refuse(full,corruption):
    module,payload,_=full
    archive,extracted=crate(full)
    if corruption=='archive':archive.write_bytes(archive.read_bytes()+b'x')
    elif corruption=='file':(extracted/'src/lib.rs').write_text('changed')
    elif corruption=='extra':(extracted/'extra').write_text('unexpected')
    elif corruption=='symlink':(extracted/'src/lib.rs').unlink();(extracted/'src/lib.rs').symlink_to('/etc/passwd')
    elif corruption=='hardlink':os.link(extracted/'src/lib.rs',extracted/'alias')
    else:(module.WORK/'full-cargo-1/credentials.toml').write_text('secret')
    with pytest.raises(RuntimeError,match='full_cargo_'):module.full_cargo_cache(payload)


@pytest.mark.parametrize('kind',['escape','symlink','budget'])
def test_authenticated_archive_still_obeys_path_type_and_expansion_bounds(full,monkeypatch,kind):
    module,payload,_=full
    entries=[('../escape',b'no','file')] if kind=='escape' else [('alias',b'../outside','symlink')] if kind=='symlink' else None
    crate(full,entries=entries)
    if kind=='budget':monkeypatch.setattr(module,'FULL_CRATE_EXPANDED_LIMIT',1)
    with pytest.raises(RuntimeError,match='full_cargo_'):module.full_cargo_cache(payload)


def test_fetch_fresh_home_locked_target_and_no_retry(full,monkeypatch):
    module,payload,source=full;locked(full);calls=[]
    def command(argv,**kwargs):calls.append((argv,kwargs));return b'',b''
    monkeypatch.setattr(module,'command',command)
    monkeypatch.setattr(module,'full_cargo_cache',lambda payload:{'crates':1,'compressed_bytes':10,'expanded_bytes':20,'cache_sha256':'a'*64})
    result=module.full_cargo_fetch(payload)
    assert result['status']=='full_cargo_fetched' and len(calls)==1
    assert calls[0][0][1:]==['fetch','--locked','--target',module.HOST]
    assert calls[0][1]['environment']['CARGO_NET_RETRY']=='0'
    assert result['session_enabled'] is False and result['full_runtime_qualified'] is False
    with pytest.raises(RuntimeError,match='full_cargo_retained'):module.full_cargo_fetch(payload)


def test_failed_fetch_preserves_created_home_and_is_not_retried(full,monkeypatch):
    module,payload,_=full;locked(full);calls=[]
    def fail(*args,**kwargs):calls.append(1);raise RuntimeError('network_failed')
    monkeypatch.setattr(module,'command',fail)
    with pytest.raises(RuntimeError,match='network_failed'):module.full_cargo_fetch(payload)
    assert len(calls)==1 and (module.WORK/'full-cargo-1').is_dir()


@pytest.mark.parametrize('interpreter,needed,accepted',[(None,None,True),('/lib/ld-linux-aarch64.so.1','libc.so.6',True),('/foreign/loader','libc.so.6',False),('/lib/ld-linux-aarch64.so.1','libevil.so',False)])
def test_protoc_elf_interpreter_and_dependency_allowlist(full,interpreter,needed,accepted):
    module,_,_=full;path=module.WORK/'protoc';path.write_bytes(elf(interpreter,needed));path.chmod(0o755)
    if accepted:
        result=module.full_protoc_elf(path)
        assert result['interpreter']==interpreter
        assert result['needed']==([] if needed is None else [needed])
    else:
        with pytest.raises(RuntimeError,match='full_cargo_protoc'):module.full_protoc_elf(path)


def test_test_executable_requires_exact_single_lib_target(full):
    module,_,_=full
    path=module.WORK/'full-target-1/release/deps/openshell_sandbox-0123abcd'
    path.parent.mkdir(parents=True);path.write_bytes(elf());path.chmod(0o755)
    line=f'  Executable unittests src/lib.rs ({path})\n'.encode()
    assert module.full_test_executable(line)==path
    for raw in (line+line,b'',line.replace(b'openshell_sandbox-',b'other-'),line.replace(b'src/lib.rs',b'src/main.rs')):
        with pytest.raises(RuntimeError,match='full_cargo_test_binary'):module.full_test_executable(raw)


def test_expired_transaction_refuses_before_process(full,monkeypatch):
    module,payload,_=full;locked(full)
    monkeypatch.setattr(module,'DEADLINE',0)
    monkeypatch.setattr(module,'command',lambda *a,**k:pytest.fail('spawn after deadline'))
    with pytest.raises(RuntimeError,match='deadline'):module.full_cargo_fetch(payload)


def test_helper_preserves_transport_bound():
    helper=BASE/'guest_full_cargo.py'
    assert helper.is_file(), 'full Cargo helper absent: intended red'
    assert helper.stat().st_size<=28*1024


def test_protoc_wrapper_keeps_exact_compiler_and_clears_rust_loader(full,monkeypatch):
    module,payload,_=full
    prefix=module.WORK/'full-cargo-1/registry/src/index.crates.io-1949cf8c6b5b557f/protoc-bin-vendored-linux-aarch_64-3.2.0'
    (prefix/'bin').mkdir(parents=True);(prefix/'include').mkdir()
    binary=prefix/'bin/protoc';binary.write_bytes(elf());binary.chmod(0o755)
    calls=[]
    def command(argv,**kwargs):
        calls.append((argv,kwargs));assert 'LD_LIBRARY_PATH' not in kwargs['environment']
        assert argv==[str(binary),'--version'];return b'libprotoc 31.1\n',b''
    monkeypatch.setattr(module,'command',command)
    result=module.full_protoc(payload)
    assert result['interpreter'] is None and result['needed']==[]
    wrapper=Path(result['wrapper'])
    assert stat.S_IMODE(wrapper.stat().st_mode)==0o500
    assert 'LD_LIBRARY_PATH' not in wrapper.read_text() and str(binary) in wrapper.read_text()
    assert len(calls)==1
    wrapper.chmod(0o700);wrapper.write_text('unexpected')
    with pytest.raises(RuntimeError,match='full_cargo_protoc_wrapper'):module.full_protoc(payload)
    assert wrapper.read_text()=='unexpected'


@pytest.mark.parametrize('failure',[None,'version','sentinel','lock','patch'])
def test_full_build_is_offline_and_requires_native_identity_and_sentinel(full,monkeypatch,failure):
    module,payload,source=full;locked(full)
    release=module.WORK/'full-target-1/release';(release/'deps').mkdir(parents=True)
    binary=release/'openshell-sandbox';binary.write_bytes(elf());binary.chmod(0o755)
    test=release/'deps/openshell_sandbox-0123456789abcdef';test.write_bytes(elf());test.chmod(0o755)
    monkeypatch.setattr(module,'full_protoc',lambda payload:{'wrapper':str(module.WORK/'full-protoc-1'),'include':str(module.WORK/'includes')})
    calls=[]
    def command(argv,**kwargs):
        calls.append((argv,kwargs))
        assert kwargs['environment']['CARGO_NET_OFFLINE']=='true'
        assert kwargs['environment']['PROTOC']==str(module.WORK/'full-protoc-1')
        if argv[1:2]==['build']:
            assert '--locked' in argv and '--offline' in argv and '--message-format=short' in argv
            assert '--target' not in argv
            return b'',b''
        if argv[1:2]==['--version']:
            return ('openshell-sandbox '+('0.1.7' if failure=='version' else module.FULL_VERSION)+'\n').encode(),b''
        if argv[1:2]==['test']:
            assert '--no-run' in argv and '--lib' in argv and '--offline' in argv
            assert '--target' not in argv
            return b'',f'  Executable unittests src/lib.rs ({test})\n'.encode()
        if '--exact' not in argv:return b'test result: ok. 10 passed; 0 failed; 0 ignored\n',b''
        assert kwargs['environment']['OPENSHELL_CHILD_UNIX_DENIAL_PROBE']=='filtered'
        if failure=='lock':(source/'Cargo.lock').write_text('modified')
        if failure=='patch':(source/'crates/openshell-sandbox/src/linux/child_seccomp.rs').write_text('modified')
        return (('' if failure=='sentinel' else module.SENTINEL+'\n')+'test result: ok. 1 passed; 0 failed; 0 ignored\n').encode(),b''
    monkeypatch.setattr(module,'command',command)
    if failure:
        with pytest.raises(RuntimeError,match='full_cargo_'):module.full_cargo_test(payload)
    else:
        result=module.full_cargo_test(payload)
        assert result['status']=='full_cargo_tested' and result['static_arm64'] is True
        assert result['session_enabled'] is False and result['full_runtime_qualified'] is False
        assert result['experimental_version']==module.FULL_VERSION
        assert module.SENTINEL in result['filtered_stdout'] and len(calls)==5
