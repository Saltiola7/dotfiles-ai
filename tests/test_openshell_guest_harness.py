"""Bounded, unprivileged artifact handling before native Linux qualification."""
from __future__ import annotations

import hashlib
import importlib.util
import io
from pathlib import Path
import struct
import sys
import tarfile
import json
import time

import pytest


@pytest.fixture(scope="module")
def builder():
    path = Path(__file__).parent / "fixtures/openshell_runtime/guest_harness.py"
    assert path.exists(), "guest harness absent: intended red evidence"
    spec = importlib.util.spec_from_file_location("guest_harness_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def archive(path, entries):
    with tarfile.open(path, "w:xz") as tar:
        for name, data, kind in entries:
            item = tarfile.TarInfo(name)
            if kind == "file":
                item.size = len(data)
                tar.addfile(item, io.BytesIO(data))
            else:
                item.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.FIFOTYPE
                item.linkname = data.decode()
                tar.addfile(item)


@pytest.mark.parametrize("kind", ["escape", "absolute", "symlink", "fifo", "budget"])
def test_archive_refuses_escapes_special_files_and_expansion(builder, tmp_path, kind):
    source = tmp_path / "input.tar.xz"
    entries = [("tool/bin/rustc", b"safe", "file")]
    if kind == "escape": entries.append(("../outside", b"x", "file"))
    elif kind == "absolute": entries.append(("/outside", b"x", "file"))
    elif kind == "symlink": entries.append(("tool/alias", b"../../outside", "symlink"))
    elif kind == "fifo": entries.append(("tool/fifo", b"", "fifo"))
    archive(source, entries)
    with pytest.raises(RuntimeError):
        builder.extract_archive(source, tmp_path / "output", "tool", maximum=3 if kind=="budget" else 1024)
    assert not (tmp_path / "outside").exists()


def test_archive_extracts_selected_root_only(builder, tmp_path):
    source = tmp_path / "input.tar.xz"
    archive(source, [("tool/bin/rustc", b"safe", "file")])
    output = tmp_path / "output"
    assert builder.extract_archive(source, output, "tool", maximum=1024) == 4
    assert (output / "tool/bin/rustc").read_bytes() == b"safe"


def elf(interpreter=False, machine=183):
    data = bytearray(120)
    data[:16] = b"\x7fELF\x02\x01\x01" + b"\0"*9
    struct.pack_into("<HHIQQQIHHHHHH", data, 16, 3, machine, 1, 0, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    struct.pack_into("<I", data, 64, 3 if interpreter else 1)
    return data


@pytest.mark.parametrize("kind", ["interpreter", "machine", "truncated"])
def test_static_arm64_probe_rejects_invalid_binary(builder, tmp_path, kind):
    data=elf(kind=="interpreter", 62 if kind=="machine" else 183)
    if kind=="truncated": data=data[:20]
    path=tmp_path/'binary';path.write_bytes(data)
    with pytest.raises(RuntimeError): builder.verify_static_arm64(path)


def test_static_arm64_probe_accepts_no_interpreter(builder, tmp_path):
    path=tmp_path/'binary';path.write_bytes(elf())
    assert builder.verify_static_arm64(path)==hashlib.sha256(path.read_bytes()).hexdigest()


def test_expired_command_never_spawns(builder, monkeypatch):
    monkeypatch.setattr(builder, "DEADLINE", 0)
    monkeypatch.setattr(builder.subprocess,"Popen",lambda *a,**k: pytest.fail("spawn after deadline"))
    with pytest.raises(RuntimeError,match="deadline"):
        builder.command(["/unused"])


@pytest.mark.parametrize('umask',[-2,0,0o022,0o077,True,False,None,'0066',0o066*1.0,-1.0])
def test_command_refuses_unselected_umask_before_spawn(builder,monkeypatch,umask):
    monkeypatch.setattr(builder,'DEADLINE',time.monotonic()+10)
    monkeypatch.setattr(builder.subprocess,'Popen',lambda *a,**k:pytest.fail('spawn with unselected umask'))
    with pytest.raises(RuntimeError,match='harness_command_umask'):
        builder.command(['/unused'],umask=umask)


def test_command_test_mask_changes_only_child_directory_traversal(builder,tmp_path,monkeypatch):
    monkeypatch.setattr(builder,'DEADLINE',time.monotonic()+30)
    script='''import json, stat, sys
from pathlib import Path
directory = Path(sys.argv[1])
directory.mkdir(mode=0o777)
file = directory / 'private-file'
file.write_bytes(b'permission probe')
print(json.dumps({'directory': stat.S_IMODE(directory.stat().st_mode),
                  'file': stat.S_IMODE(file.stat().st_mode)}))
'''
    def observe(name,**kwargs):
        output,error=builder.command([sys.executable,'-I','-c',script,str(tmp_path/name)],**kwargs)
        assert error==b''
        return json.loads(output)
    inherited=observe('before')
    assert observe('library-test',umask=0o066)=={'directory':0o711,'file':0o600}
    assert observe('after')==inherited
    assert observe('explicit-inherit',umask=-1)==inherited


def test_kernel_proof_requires_explicit_filtered_sentinel(builder, tmp_path, monkeypatch):
    source=tmp_path/'harness';source.mkdir()
    (source/'src/linux').mkdir(parents=True)
    files={'Cargo.lock':'locked','src/linux/child_seccomp.rs':'patched'}
    for name,data in files.items(): (source/name).write_text(data)
    binary=tmp_path/'target/release/test';binary.parent.mkdir(parents=True);binary.write_bytes(elf())
    calls=[]
    def command(argv,**kwargs):
        calls.append((argv,kwargs))
        if len(calls)==1:
            return json.dumps({'reason':'compiler-artifact','executable':str(binary)}).encode(),b''
        if len(calls)==2: return b'test result: ok. 5 passed; 0 failed\n',b''
        assert kwargs['environment']['OPENSHELL_CHILD_UNIX_DENIAL_PROBE']=='filtered'
        return (builder.SENTINEL+'\ntest result: ok. 1 passed; 0 failed\n').encode(),b''
    monkeypatch.setattr(builder,'WORK',tmp_path)
    monkeypatch.setattr(builder,'command',command)
    result=builder.execute_tests({'files':files})
    assert len(calls)==3 and result['kernel_only'] is True
    assert result['full_runtime_qualified'] is False


@pytest.mark.parametrize('kind',['short','oversize','digest','valid'])
def test_download_size_and_digest_bound_before_promotion(builder,tmp_path,monkeypatch,kind):
    downloads=tmp_path/'downloads';downloads.mkdir()
    name='cargo-1.95.0-aarch64-unknown-linux-musl.tar.xz'
    expected=b'verified'
    payload={'short':expected[:-1],'oversize':expected+b'x','digest':b'notright','valid':expected}[kind]
    class Response(io.BytesIO):
        url='https://static.rust-lang.org/dist/2026-04-16/'+name
    monkeypatch.setattr(builder,'WORK',tmp_path)
    monkeypatch.setattr(builder,'DEADLINE',time.monotonic()+10)
    monkeypatch.setattr(builder.urllib.request,'urlopen',lambda *a,**k:Response(payload))
    item={'archive':name,'url':Response.url,'bytes':len(expected),'sha256':hashlib.sha256(expected).hexdigest()}
    if kind=='valid':
        builder.download(item)
        assert (downloads/name).read_bytes()==expected
    else:
        with pytest.raises(RuntimeError,match='harness_download_'):
            builder.download(item)
        assert not (downloads/name).exists()
        assert len((downloads/name).with_suffix('.partial').read_bytes())<=len(expected)


@pytest.mark.parametrize('needed',[True,False])
def test_static_elf_rejects_shared_dependencies_even_without_interpreter(builder,tmp_path,needed):
    data=elf();data.extend(bytes(16))
    struct.pack_into('<IIQQQQQQ',data,64,2,0,120,0,0,16,16,8)
    struct.pack_into('<qQ',data,120,1 if needed else 0,1 if needed else 0)
    path=tmp_path/'binary';path.write_bytes(data)
    if needed:
        with pytest.raises(RuntimeError,match='dynamic'):
            builder.verify_static_arm64(path)
    else:
        assert builder.verify_static_arm64(path)==hashlib.sha256(data).hexdigest()


def test_unwind_generation_scopes_library_path_and_preserves_failed_prefix(builder,tmp_path,monkeypatch):
    failed=tmp_path/'toolchain';failed.mkdir();(failed/'evidence').write_text('retained')
    monkeypatch.setattr(builder,'WORK',tmp_path)
    env=builder.environment()
    assert env['RUSTC']==str(tmp_path/'toolchain-unwind-1/bin/rustc')
    assert env['LD_LIBRARY_PATH']==str(tmp_path/'toolchain-unwind-1/lib')
    assert 'LD_LIBRARY_PATH' not in builder.environment(rust=False)
    assert (failed/'evidence').read_text()=='retained'


def test_unwind_authentication_failure_precedes_rust_install(builder,tmp_path,monkeypatch):
    from types import SimpleNamespace
    failed=tmp_path/'toolchain';failed.mkdir();(failed/'evidence').write_text('retained')
    monkeypatch.setattr(builder,'WORK',tmp_path)
    monkeypatch.setattr(builder.os,'statvfs',lambda *a:SimpleNamespace(f_bavail=8*1024**3,f_frsize=1))
    def reject(prefix):
        assert prefix==tmp_path/'toolchain-unwind-1'
        raise RuntimeError('unwind_auth_failed')
    monkeypatch.setattr(builder,'unwind_install',reject,raising=False)
    monkeypatch.setattr(builder,'command',lambda *a,**k:pytest.fail('execute before library authentication'))
    with pytest.raises(RuntimeError,match='unwind_auth_failed'):
        builder.setup({'toolchain':{'artifacts':[]}})
    assert (failed/'evidence').read_text()=='retained'
    assert not (tmp_path/'toolchain-unwind-1').exists()


def test_explicit_resume_uses_fixed_fresh_target_and_no_network_steps(builder, monkeypatch, capsys):
    monkeypatch.setattr(builder,'validate_context',lambda:None)
    monkeypatch.setattr(builder,'resume',lambda payload:{'verified':True},raising=False)
    monkeypatch.setattr(builder,'download',lambda *a:pytest.fail('download on resume'))
    monkeypatch.setattr(builder,'setup',lambda *a:pytest.fail('install on resume'))
    monkeypatch.setattr(builder,'TARGET','target',raising=False)
    builder.stage('resume',{'toolchain':{'host':builder.HOST,'version':'1.95.0'}},60,resume_run=True)
    assert builder.environment()['CARGO_TARGET_DIR']==str(builder.WORK/'target/resume-1')
    assert json.loads(capsys.readouterr().out)['result']['verified'] is True
    with pytest.raises(RuntimeError):
        builder.stage('download',{},60,resume_run=True)
