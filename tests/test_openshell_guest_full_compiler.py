"""Private C compiler source checks; never execute downloaded/native toolchains."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
import struct
from types import ModuleType

import pytest


@pytest.fixture
def compiler(tmp_path, monkeypatch):
    base = Path(__file__).parent/'fixtures/openshell_runtime'
    path = base/'guest_full_compiler.py'
    assert path.exists(), 'private compiler helper absent: intended red'
    module = ModuleType('full_compiler_fixture')
    source = '\n'.join((base/name).read_text() for name in ('guest_harness.py','guest_unwind.py','guest_full_compiler.py'))
    exec(compile(source,str(path),'exec'),module.__dict__)
    monkeypatch.setattr(module,'WORK',tmp_path)
    monkeypatch.setattr(module,'DEADLINE',time.monotonic()+30)
    module.fixture_payload = {'full_manifest':json.loads((base/'fullbuild/manifest.json').read_text())}
    return module


def package(compiler, entries=None, selected=3, **changes):
    item = dict(compiler.fixture_payload['full_manifest']['c_toolchain']['packages'][selected])
    raw = '\n'.join(f'{key} = {value}' for key,value in {
        'pkgname':item['pkgname'],'pkgver':item['pkgver'],'arch':item['arch'],'origin':item['origin'],
        'commit':item['source_commit'],'datahash':'a'*64,**changes}.items()).encode()+b'\n'
    raw += ''.join('depend = '+value+'\n' for value in item['dependencies_expected']).encode()
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as tar:
        members=[('.PKGINFO',raw,'file'),*(entries or [('lib/example',b'bytes','file')])]
        for name,body,kind in members:
            info=tarfile.TarInfo(name);info.mode=0o755 if name.endswith('/gcc') else 0o644
            if kind=='file':info.size=len(body);tar.addfile(info,io.BytesIO(body))
            else:
                info.type={'symlink':tarfile.SYMTYPE,'hardlink':tarfile.LNKTYPE,'fifo':tarfile.FIFOTYPE}[kind]
                info.linkname=body.decode();tar.addfile(info)
    return gzip.compress(stream.getvalue()),item


def test_fixed_manifest_rejects_changed_urls_or_selection(compiler):
    assert len(compiler.full_compiler_config(compiler.fixture_payload)['packages'])==15
    compiler.fixture_payload['full_manifest']['c_toolchain']['packages'][0]['url']='https://unknown.invalid/gcc.apk'
    with pytest.raises(RuntimeError,match='full_compiler_manifest'):
        compiler.full_compiler_config(compiler.fixture_payload)


@pytest.mark.parametrize('change',['pkgver','arch','origin','commit','pkgname'])
def test_signed_metadata_exact_identity(compiler,change):
    raw,item=package(compiler,**{change:'different'})
    with pytest.raises(RuntimeError,match='full_compiler_metadata'):
        compiler.full_compiler_parse(raw,item,{},1024**2)


@pytest.mark.parametrize('name,kind,body',[('../escape','file',b'x'),('/escape','file',b'x'),
    ('usr/a/../b','file',b'x'),('usr/fifo','fifo',b''),('usr/alias','symlink',b'/etc/passwd')])
def test_archive_rejects_escaping_or_special_paths(compiler,name,kind,body):
    raw,item=package(compiler,[(name,body,kind)])
    with pytest.raises(RuntimeError,match='full_compiler_'):
        compiler.full_compiler_parse(raw,item,{},1024**2)


def test_real_decompressed_stream_bound_includes_padding(compiler):
    raw,item=package(compiler)
    with pytest.raises(RuntimeError,match='full_compiler_expansion'):
        compiler.full_compiler_parse(raw,item,{},64)


def test_unused_ldd_absolute_link_is_omitted(compiler):
    raw,item=package(compiler,[('usr/bin/ldd',b'/lib/ld-musl-aarch64.so.1','symlink'),('lib/example',b'bytes','file')])
    entries,_=compiler.full_compiler_parse(raw,item,{},1024**2)
    assert 'usr/bin/ldd' not in entries and entries['lib/example'][2]==b'bytes'


def test_only_exact_signed_gcc_lto_link_is_relocated_inside_prefix(compiler):
    target='usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/liblto_plugin.so'
    name='usr/lib/bfd-plugins/liblto_plugin.so'
    raw,item=package(compiler,[(name,('//'+target).encode(),'symlink'),(target,b'authenticated plugin','file')],selected=0)
    entries,_=compiler.full_compiler_parse(raw,item,{},1024**2)
    assert entries[name][2]=='../../libexec/gcc/aarch64-alpine-linux-musl/14.2.0/liblto_plugin.so'
    result=compiler.full_compiler_graph(entries)
    assert result[target][0]=='file'
    entries[target]=('directory',0o700,None)
    with pytest.raises(RuntimeError,match='full_compiler_'):compiler.full_compiler_graph(entries)


@pytest.mark.parametrize('wrong',['single_slash','other_version','other_package'])
def test_lto_exception_cannot_admit_other_absolute_links(compiler,wrong):
    target='//usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/liblto_plugin.so'
    if wrong=='single_slash':target=target[1:]
    elif wrong=='other_version':target=target.replace('14.2.0','14.2.1')
    raw,item=package(compiler,[('usr/lib/bfd-plugins/liblto_plugin.so',target.encode(),'symlink')],selected=3 if wrong=='other_package' else 0)
    with pytest.raises(RuntimeError,match='full_compiler_link'):compiler.full_compiler_parse(raw,item,{},1024**2)


def test_normalized_dependency_requires_exact_selected_version(compiler):
    item=compiler.fixture_payload['full_manifest']['c_toolchain']['packages'][2]
    fields={'pkgname':[item['pkgname']],'pkgver':[item['pkgver']],'arch':['aarch64'],'origin':[item['origin']],
        'commit':[item['source_commit']],'datahash':['a'*64],'depend':['musl=1.2.5-r13']}
    compiler.full_compiler_metadata(fields,item,{'musl':'1.2.5-r13'})
    fields['depend']=['musl>=1.2.5-r13']
    with pytest.raises(RuntimeError,match='full_compiler_metadata'):
        compiler.full_compiler_metadata(fields,item,{'musl':'1.2.5-r13'})


def gcc_dependency_fields(compiler):
    item=compiler.fixture_payload['full_manifest']['c_toolchain']['packages'][0]
    fields={key:[item[key]] for key in ('pkgname','pkgver','arch','origin')}
    fields.update(commit=[item['source_commit']],datahash=['a'*64],depend=[
        'binutils','libgomp=14.2.0-r6','libatomic=14.2.0-r6','libgomp=14.2.0-r6',
        *item['dependencies_expected'][3:]])
    versions={record['pkgname']:record['pkgver'] for record in compiler.fixture_payload['full_manifest']['c_toolchain']['packages']}
    return item,fields,versions


def test_actual_gcc_identical_libgomp_declaration_has_one_dependency_meaning(compiler):
    item,fields,versions=gcc_dependency_fields(compiler)
    assert fields['depend'].count('libgomp=14.2.0-r6')==2
    compiler.full_compiler_metadata(fields,item,versions)


@pytest.mark.parametrize('conflict',['libgomp','libgomp=14.2.0-r5','libgomp>=14.2.0-r6'])
def test_conflicting_same_name_dependency_refuses_with_bounded_diagnostic(compiler,conflict):
    item,fields,versions=gcc_dependency_fields(compiler)
    fields['depend'][3]=conflict
    with pytest.raises(RuntimeError,match='full_compiler_metadata') as error:
        compiler.full_compiler_metadata(fields,item,versions)
    assert item['archive'] in str(error.value) and conflict in str(error.value)
    assert len(str(error.value))<600


def test_graph_resolves_internal_hardlinks_as_regular_copies(compiler):
    entries={'usr/bin/gcc':('file',0o500,b'body'),'usr/bin/cc':('hardlink',0o500,'usr/bin/gcc')}
    result=compiler.full_compiler_graph(entries)
    assert result['usr/bin/cc']==result['usr/bin/gcc']
    assert result['usr'][0]=='directory' and result['usr/bin'][0]=='directory'


@pytest.mark.parametrize('kind',['escape','cycle','child_of_link','missing'])
def test_graph_rejects_unknown_aliases(compiler,kind):
    entries={'usr/file':('file',0o400,b'x'),'usr/link':('symlink',0o777,'file')}
    if kind=='escape':entries['usr/link']=('symlink',0o777,'../../outside')
    elif kind=='cycle':entries['usr/link']=('symlink',0o777,'link')
    elif kind=='child_of_link':entries['usr/link/child']=('file',0o400,b'x')
    else:entries['usr/link']=('symlink',0o777,'missing')
    with pytest.raises(RuntimeError,match='full_compiler_'):compiler.full_compiler_graph(entries)


def test_publish_completes_only_exact_missing_entries_and_rejects_unknowns(compiler):
    root=compiler.WORK/'full-c-toolchain-1'
    entries=compiler.full_compiler_graph({'usr/a':('file',0o400,b'a'),'usr/b':('file',0o500,b'b')})
    compiler.full_compiler_publish(root,entries,create=True)
    original=(root/'usr/a').stat().st_ino
    (root/'usr/b').unlink()
    compiler.full_compiler_publish(root,entries,create=True)
    assert (root/'usr/a').stat().st_ino==original
    (root/'extra').write_text('unknown')
    with pytest.raises(RuntimeError,match='full_compiler_tree'):
        compiler.full_compiler_publish(root,entries,create=True)


def test_changed_existing_file_is_not_overwritten(compiler):
    root=compiler.WORK/'full-c-toolchain-1'
    entries=compiler.full_compiler_graph({'usr/a':('file',0o400,b'a')})
    compiler.full_compiler_publish(root,entries,create=True)
    (root/'usr/a').chmod(0o600);(root/'usr/a').write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='full_compiler_'):
        compiler.full_compiler_publish(root,entries,create=True)
    assert (root/'usr/a').read_bytes()==b'changed'


def test_authentication_failure_precedes_prefix_publication(compiler,monkeypatch):
    monkeypatch.setattr(compiler,'unwind_verify',lambda: (_ for _ in ()).throw(RuntimeError('signature failed')))
    with pytest.raises(RuntimeError,match='signature failed'):compiler.full_compiler_prepare(compiler.fixture_payload)
    assert not (compiler.WORK/'full-c-toolchain-1').exists()


def test_wrappers_use_scoped_fresh_environment_and_private_search_paths(compiler):
    wrappers=compiler.full_compiler_wrappers()
    assert set(wrappers)=={'cc','as','ar'}
    for raw in wrappers.values():
        assert b'/usr/bin/env -i' in raw and b'LD_LIBRARY_PATH=' in raw
        assert b'/full-c-toolchain-1/' in raw
        assert b'"$@"' in raw and b'export ' not in raw
    assert b'--sysroot=' in wrappers['cc'] and b'-nostdinc' in wrappers['cc']
    assert b'GCC_EXEC_PREFIX=' in wrappers['cc']


def test_probe_refuses_retained_partial_without_execution(compiler,monkeypatch):
    (compiler.WORK/'full-c-smoke-1').mkdir()
    monkeypatch.setattr(compiler,'full_compiler_verify',lambda payload:pytest.fail('verification/execution after partial'))
    with pytest.raises(RuntimeError,match='full_compiler_smoke_present'):
        compiler.full_compiler_probe(compiler.fixture_payload)


def test_source_size_no_entrypoint(compiler):
    path=Path(__file__).parent/'fixtures/openshell_runtime/guest_full_compiler.py'
    source=path.read_text()
    assert len(source.encode())<=30*1024 and '__main__' not in source


def gdb_entries():
    stems=['usr/lib/libcc1',
        'usr/lib/gcc/aarch64-alpine-linux-musl/14.2.0/plugin/libcc1plugin',
        'usr/lib/gcc/aarch64-alpine-linux-musl/14.2.0/plugin/libcp1plugin']
    entries={}
    for stem in stems:
        entries[stem+'.so.0.0.0']=('file',0o500,b'signed plugin '+stem.encode())
        entries[stem+'.so.0']=('symlink',0o777,Path(stem).name+'.so.0.0.0')
        entries[stem+'.so']=('symlink',0o777,Path(stem).name+'.so.0')
    return entries


def test_exact_gdb_subset_reports_signed_bytes_and_preserves_compiler(compiler):
    omitted=gdb_entries()
    kept={name:('file',0o500,b'required') for name in (
        'usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/cc1',
        'usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/collect2',
        'usr/lib/libstdc++.so.6','usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/liblto_plugin.so')}
    before=compiler.full_compiler_graph({**omitted,**kept})
    retained,proof=compiler.full_compiler_omit_gdb(before,omitted)
    assert set(proof)==set(omitted) and not set(omitted)&set(retained)
    assert set(omitted)<=set(before)
    assert all(retained[name]==value for name,value in kept.items())
    for name,(kind,_,raw) in omitted.items():
        assert proof[name]=={'kind':kind,'sha256':hashlib.sha256(raw if kind=='file' else raw.encode()).hexdigest()}


@pytest.mark.parametrize('failure',['missing','implementation_link','alias_file','cross_family','outside','retained_alias'])
def test_gdb_omission_refuses_partial_or_wrong_link_family(compiler,failure):
    selected=gdb_entries();entries=dict(selected)
    name='usr/lib/libcc1.so'
    if failure=='missing':selected.pop(name)
    elif failure=='implementation_link':selected['usr/lib/libcc1.so.0.0.0']=('symlink',0o777,'libcc1.so')
    elif failure=='alias_file':selected[name]=('file',0o500,b'not a signed alias')
    elif failure=='cross_family':selected[name]=('symlink',0o777,'gcc/aarch64-alpine-linux-musl/14.2.0/plugin/libcp1plugin.so.0.0.0')
    elif failure=='outside':selected[name]=('symlink',0o777,'../../outside')
    else:entries['usr/lib/retained.so']=('symlink',0o777,'libcc1.so')
    entries.update(selected)
    with pytest.raises(RuntimeError,match='full_compiler_'):
        compiler.full_compiler_omit_gdb(compiler.full_compiler_graph(entries),selected)


def test_retained_needed_dependency_cannot_use_omitted_gdb_library(compiler):
    gcc='usr/lib/gcc/aarch64-alpine-linux-musl/14.2.0'
    libexec='usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0'
    required=['usr/bin/gcc','usr/bin/as','usr/bin/ar','usr/bin/ld','lib/ld-musl-aarch64.so.1',
        libexec+'/cc1',libexec+'/collect2',gcc+'/include/stddef.h',gcc+'/libgcc.a',
        'usr/include/stdio.h','usr/lib/libc.a','usr/lib/crt1.o','usr/lib/crti.o','usr/lib/crtn.o']
    entries={name:('file',0o400,b'authenticated fixture') for name in required}
    raw,_=dynamic_elf();raw=bytearray(raw)
    dependency=b'libcc1.so.0\0';raw[513:513+len(dependency)]=dependency
    entries['usr/bin/gcc']=('file',0o500,bytes(raw))
    omitted=gdb_entries()
    retained,_=compiler.full_compiler_omit_gdb(compiler.full_compiler_graph({**entries,**omitted}),omitted)
    with pytest.raises(RuntimeError,match='full_compiler_missing_dependency:usr/bin/gcc:libcc1.so.0'):
        compiler.full_compiler_closure(retained)


@pytest.fixture
def signed_inputs(compiler,monkeypatch):
    cfg=json.loads(json.dumps(compiler.fixture_payload['full_manifest']['c_toolchain']))
    for item in cfg['packages']:item['bytes']=3
    root=compiler.WORK/'full-c-downloads-1';root.mkdir()
    for item in cfg['packages']:(root/item['archive']).write_bytes(b'apk')
    calls=[]
    monkeypatch.setattr(compiler,'full_compiler_config',lambda payload:cfg)
    monkeypatch.setattr(compiler,'unwind_verify',lambda:calls.append('bootstrap'))
    def command(argv,**kwargs):
        assert {'--no-network','--no-cache','verify','--keys-dir'}<=set(argv)
        assert 'LD_LIBRARY_PATH' not in kwargs['environment']
        calls.append('signature');return b'OK',b''
    monkeypatch.setattr(compiler,'command',command)
    def parse(raw,item,*args):
        assert calls==['bootstrap','signature']
        values={'usr/'+item['pkgname']:('file',0o400,b'authenticated')}
        if item['pkgname']=='gcc':values.update(gdb_entries())
        return values,32
    monkeypatch.setattr(compiler,'full_compiler_parse',parse)
    monkeypatch.setattr(compiler,'full_compiler_closure',lambda entries:None)
    return compiler,cfg,calls


def test_all_complete_apks_authenticated_before_any_member_parse(signed_inputs):
    module,cfg,calls=signed_inputs
    _,entries,hashes,expanded,omitted=module.full_compiler_inputs(module.fixture_payload)
    assert calls==['bootstrap','signature'] and len(hashes)==15 and expanded==15*32
    assert 'usr/gcc' in entries and all(value==hashlib.sha256(b'apk').hexdigest() for value in hashes.values())
    assert set(omitted)==set(gdb_entries()) and not set(omitted)&set(entries)


def test_gdb_entries_from_any_other_package_refuse(signed_inputs,monkeypatch):
    module,_,_=signed_inputs
    parse=module.full_compiler_parse
    def other_package(raw,item,*args):
        values,size=parse(raw,item,*args)
        if item['pkgname']=='musl':values.update(gdb_entries())
        return values,size
    monkeypatch.setattr(module,'full_compiler_parse',other_package)
    with pytest.raises(RuntimeError,match='full_compiler_gdb_package'):
        module.full_compiler_prepare(module.fixture_payload)
    assert not (module.WORK/'full-c-toolchain-1').exists()


def test_prepare_and_verify_bind_same_omission_report(signed_inputs):
    module,_,calls=signed_inputs
    prepared=module.full_compiler_prepare(module.fixture_payload)
    calls.clear()
    verified=module.full_compiler_verify(module.fixture_payload)
    assert set(prepared['omitted_gdb_entries'])==set(gdb_entries())
    assert prepared['omitted_gdb_entries']==verified['omitted_gdb_entries']


def test_signature_failure_blocks_all_package_extraction(signed_inputs,monkeypatch):
    module,_,_=signed_inputs
    monkeypatch.setattr(module,'command',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('APK signature rejected')))
    monkeypatch.setattr(module,'full_compiler_parse',lambda *a:pytest.fail('parsed unauthenticated APK'))
    with pytest.raises(RuntimeError,match='APK signature rejected'):module.full_compiler_prepare(module.fixture_payload)
    assert not (module.WORK/'full-c-toolchain-1').exists()


def test_unknown_retained_download_refuses(signed_inputs):
    module,_,_=signed_inputs
    (module.WORK/'full-c-downloads-1/unknown.apk').write_bytes(b'unknown')
    with pytest.raises(RuntimeError,match='full_compiler_download_retained'):
        module.full_compiler_inputs(module.fixture_payload)


def test_materialized_hardlink_copies_share_existing_expansion_budget(signed_inputs,monkeypatch):
    module,cfg,_=signed_inputs;cfg['expanded_limit']=500
    monkeypatch.setattr(module,'full_compiler_parse',lambda raw,item,*args:({'usr/'+item['pkgname']:('file',0o400,b'x'*100)},32))
    with pytest.raises(RuntimeError,match='full_compiler_expansion'):
        module.full_compiler_inputs(module.fixture_payload)


@pytest.mark.parametrize('case',['valid','short','oversize','redirect'])
def test_download_is_bounded_without_trusting_content_length(compiler,monkeypatch,case):
    item=dict(compiler.fixture_payload['full_manifest']['c_toolchain']['packages'][0],bytes=3)
    body={'short':b'ab','oversize':b'abcd'}.get(case,b'abc')
    class Response(io.BytesIO):
        status=200
        url='https://other.invalid' if case=='redirect' else item['url']
    class Opener:
        def open(self,*args,**kwargs):return Response(body)
    monkeypatch.setattr(compiler,'full_compiler_config',lambda payload:{'packages':[item],'compressed_bytes':3,'expanded_limit':32})
    monkeypatch.setattr(compiler.urllib.request,'build_opener',lambda *args:Opener())
    if case=='valid':
        report=compiler.full_compiler_download({})
        assert report['authenticated_packages']==0
        assert (compiler.WORK/'full-c-downloads-1'/item['archive']).read_bytes()==b'abc'
    else:
        with pytest.raises(RuntimeError,match='full_compiler_download_'):compiler.full_compiler_download({})
        assert not (compiler.WORK/'full-c-downloads-1'/item['archive']).exists()


def elf(kind=2,machine=183):
    data=bytearray(120 if kind!=1 else 64)
    data[:16]=b'\x7fELF\x02\x01\x01'+b'\0'*9
    struct.pack_into('<HHIQQQIHHHHHH',data,16,kind,machine,1,0,64 if kind!=1 else 0,0,0,64,56 if kind!=1 else 0,1 if kind!=1 else 0,0,0,0)
    if kind!=1:struct.pack_into('<IIQQQQQQ',data,64,1,5,0,0,0,len(data),len(data),4096)
    return bytes(data)


@pytest.mark.parametrize('kind',[1,2,3])
def test_elf_requires_arm64_even_for_objects(compiler,kind):
    assert compiler.full_compiler_elf(elf(kind))['kind']==kind
    with pytest.raises(RuntimeError,match='full_compiler_elf'):compiler.full_compiler_elf(elf(kind,machine=62))


def dynamic_elf(*, failure=None):
    table_size=1024**2+64
    table_at=512
    data=bytearray(table_at+table_size)
    data[:16]=b'\x7fELF\x02\x01\x01'+b'\0'*9
    count=3 if failure=='ambiguous' else 2
    struct.pack_into('<HHIQQQIHHHHHH',data,16,3,183,1,0,64,0,0,64,56,count,0,0,0)
    filesz=len(data)-1 if failure=='memory_only_tail' else len(data)
    struct.pack_into('<IIQQQQQQ',data,64,1,4,0,0,0,filesz,len(data),4096)
    struct.pack_into('<IIQQQQQQ',data,120,2,4,256,256,256,64,64,8)
    if failure=='ambiguous':
        struct.pack_into('<IIQQQQQQ',data,176,1,4,0,0,0,len(data),len(data),4096)
    declared_size=len(data)+1 if failure=='file_overflow' else table_size
    for index,(tag,value) in enumerate(((5,table_at),(10,declared_size),(1,1),(0,0))):
        struct.pack_into('<qQ',data,256+index*16,tag,value)
    dependency=b'\0libc.musl-aarch64.so.1\0'
    data[table_at:table_at+len(dependency)]=dependency
    return bytes(data),declared_size


def test_elf_large_string_table_uses_file_backed_load_extent(compiler):
    raw,_=dynamic_elf()
    assert compiler.full_compiler_elf(raw)['needed']==['libc.musl-aarch64.so.1']


@pytest.mark.parametrize('failure,mappings',[
    ('file_overflow',0),('memory_only_tail',0),('ambiguous',2),
])
def test_elf_string_table_requires_one_complete_file_mapping(compiler,failure,mappings):
    raw,length=dynamic_elf(failure=failure)
    member='usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/cc1'
    with pytest.raises(RuntimeError,match='full_compiler_elf') as error:
        compiler.full_compiler_elf(raw,member=member)
    assert member in str(error.value)
    assert f'mappings={mappings}' in str(error.value)
    assert f'bytes={length}' in str(error.value)


@pytest.mark.parametrize('tag',[15,29,0x6ffffefb,0x6ffffefc])
def test_elf_search_tags_report_value_but_never_allow_it(compiler,tag):
    raw,_=dynamic_elf()
    raw=bytearray(raw)
    struct.pack_into('<qQ',raw,288,tag,1)
    value=b'$ORIGIN/../lib'
    raw[513:513+len(value)+1]=value+b'\0'
    member='usr/libexec/gcc/aarch64-alpine-linux-musl/14.2.0/cc1'
    with pytest.raises(RuntimeError,match='full_compiler_elf_search_path') as error:
        compiler.full_compiler_elf(bytes(raw),member)
    assert member in str(error.value)
    assert f'tag={tag:#x}' in str(error.value)
    assert repr(value) in str(error.value)


@pytest.mark.parametrize('failure',['offset','unterminated','table'])
def test_elf_search_tag_invalid_string_remains_bounded_refusal(compiler,failure):
    raw,length=dynamic_elf(failure='file_overflow' if failure=='table' else None)
    raw=bytearray(raw)
    struct.pack_into('<qQ',raw,288,29,length+1 if failure=='offset' else 1)
    if failure=='unterminated':raw[513:513+300]=b'x'*300
    with pytest.raises(RuntimeError,match='full_compiler_elf') as error:
        compiler.full_compiler_elf(bytes(raw),'usr/bin/gcc')
    diagnostic=str(error.value)
    assert 'usr/bin/gcc' in diagnostic and 'tag=0x1d' in diagnostic
    assert 'invalid' in diagnostic or 'mappings=0' in diagnostic
    assert len(diagnostic)<550


@pytest.mark.parametrize('failure',[None,'query_escape','include_escape','link_escape','sentinel'])
def test_probe_requires_real_workflow_results_and_preserves_failure(compiler,monkeypatch,failure):
    prefix=compiler.WORK/'full-c-toolchain-1';(prefix/'usr/include').mkdir(parents=True)
    for name in ('cc1','as','ld','collect2','crt1.o','crti.o','crtn.o','libc.a','libgcc.a'):
        (prefix/name).write_bytes(b'authenticated fixture')
    report={'compiler_tree_sha256':'a'*64,'wrappers':{'cc':'/fixture/cc','ar':'/fixture/ar'}}
    monkeypatch.setattr(compiler,'full_compiler_verify',lambda payload:report)
    calls=[]
    def command(argv,**kwargs):
        calls.append(argv)
        assert 'LD_LIBRARY_PATH' not in kwargs['environment']
        if len(argv)==2 and argv[1].startswith('-print-'):
            path=Path('/usr/escape') if failure=='query_escape' else prefix/argv[1].split('=',1)[1]
            return (str(path)+'\n').encode(),b''
        if '-E' in argv:
            path='/usr/include' if failure=='include_escape' else str(prefix/'usr/include')
            return b'',('#include <...> search starts here:\n '+path+'\nEnd of search list.\n').encode()
        if '-c' in argv:
            Path(argv[-1]).write_bytes(elf(1));return b'',b''
        if argv[0]=='/fixture/ar':
            body=Path(argv[-1]).read_bytes()
            head=f'{"lib.o/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(body):<10}`\n'.encode()
            Path(argv[-2]).write_bytes(b'!<arch>\n'+head+body+(b'\n' if len(body)%2 else b''));return b'',b''
        if '-static' in argv:
            Path(argv[-1]).write_bytes(elf())
            return (('/usr/lib/foreign.a' if failure=='link_escape' else str(prefix/'libc.a'))+'\n').encode(),b''
        return (b'wrong\n' if failure=='sentinel' else b'openshell-private-c-static-checked\n'),b''
    monkeypatch.setattr(compiler,'command',command)
    if failure:
        with pytest.raises(RuntimeError,match='full_compiler_'):compiler.full_compiler_probe({})
        assert (compiler.WORK/'full-c-smoke-1/lib.c').exists()
    else:
        proof=compiler.full_compiler_probe({})
        assert proof['status']=='compiler_probed' and proof['static_arm64'] is True
        assert set(proof['smoke_sha256'])=={'lib.c','main.c','lib.o','libproof.a','proof'}
        assert any('-c' in argv for argv in calls) and any('-static' in argv for argv in calls)
