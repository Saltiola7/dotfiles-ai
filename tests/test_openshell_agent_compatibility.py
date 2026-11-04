"""Closed client comparison orchestration; these tests start no native worker."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def agent():
    path = Path(__file__).with_name("probe_openshell_agent_compatibility.py")
    assert path.exists(), "agent comparison orchestration absent: intended red"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("agent_comparison_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(path.parent))


@pytest.mark.parametrize("operation", ["activate", "agent", "agent-resume", "agent-prune", ""])
def test_unselected_agent_operation_refuses_before_boot(agent, monkeypatch, operation):
    monkeypatch.setattr(agent.boot, "_qualify_with_inspection", lambda *a, **k: pytest.fail("boot"))
    with pytest.raises(agent.build.Refusal):
        agent.qualify(None, operation)


def test_only_asset_download_has_network_and_each_case_has_own_stage(agent):
    assert agent.OPERATIONS == ("agent-prepare", "agent-test", "agent-inspect", "agent-test-resume")
    stages = agent.STAGES["agent-test"]
    assert len(stages) <= 30
    assert [s[0] for s in stages if s[0] in agent.CASES] == list(agent.CASES)
    assert len(agent.CASES) == 21
    assert all(not s[2] for s in stages)
    assert [s[0] for s in agent.STAGES["agent-prepare"] if s[2]] == ["agent-download"]


@pytest.mark.parametrize("operation,threshold", [("agent-prepare", 2 * 1024**3), ("agent-test", 512 * 1024**2)])
def test_agent_capacity_refuses_before_any_unit(agent, operation, threshold):
    @contextmanager
    def mounted_store(**kwargs):
        yield None
    namespace = {"time": time, "sys": sys, "json": json, "mounted_store": mounted_store,
                 "Refusal": agent.build.Refusal,
                 "run_unit": lambda *a, **k: pytest.fail("unit"),
                 "install_runtime": lambda **k: pytest.fail("runtime"),
                 "build_inventory": lambda: {"store_available_bytes": threshold - 1}}
    stage = agent.STAGES[operation][0][0]
    with pytest.raises(RuntimeError, match="agent_capacity"):
        exec(agent.stage_script("", "", "", "", {"toolchain": {}}, operation, stage, 400,
                                host_binding_sha256="d" * 64), namespace)


@pytest.mark.parametrize("operation", ["agent-prepare", "agent-test", "agent-inspect", "agent-test-resume"])
def test_public_runner_dispatches_agent_operations_without_legacy_boot(agent, monkeypatch, operation):
    import probe_openshell_agent_compatibility as canonical
    sentinel = object()
    monkeypatch.setattr(canonical, "qualify", lambda *a: sentinel)
    assert agent.build.qualify(None, operation) is sentinel


def case_fixture(agent, mode="patched", probe="codex-version"):
    output = {"codex-version":"codex-cli 0.164.0\n", "codex-help":"Codex CLI\nUsage: codex\n",
              "codex-empty-login":"", "codex-stdio":"", "opencode-version":"1.18.25\n",
              "opencode-help":"Usage: opencode\n", "opencode-rg":"sentinel.txt\n"}[probe]
    records = [[1,123,0 if mode == "unfiltered" else 80,1,0,122,0],
               [2,0,456,int(mode != "unfiltered"),0,0,0], [6,13,1,7,1,0,0],
               [3,1 if mode == "patched" else 0,1 if mode == "patched" else 0,0,0,0,0],
               [4,0,456,0,0,0,0], [5,0,0,0,0,0,0]]
    stages = {"fixture-build": {"binary_sha256": "a"*64},
              "agent-verify": {"assets": {"codex": {"files": {
                  "bin/codex": {"sha256": "b"*64}, "codex-path/rg": {"sha256": "c"*64}}},
                  "opencode":{"files":{"opencode":{"sha256":"d"*64}}}}}}
    value = {"schema_version":1,"generation":1,"status":"agent_case_observed",
             "case":probe+"-"+mode,"probe":probe,"mode":mode,"fixture_binary_sha256":"a"*64,
             "executable_sha256":("b" if probe.startswith("codex-") else "d")*64,
             "rg_sha256":"c"*64,"proof_records":records,
             "observation":"exited","exit_code":0,"signal":None,"wrapper_returncode":0,
             "termination_requested":False,"expectation_met":True,"initialized":False,
             "initialize_result":None,"stdin_bytes":0,"stdout_bytes":len(output),"stderr_bytes":0,
             "stdout_tail":output,"stderr_tail":"","case_state_bytes":256,"python_nondumpable":True,
             **agent.FLAGS}
    if probe == "codex-empty-login":
        value.update(exit_code=1,stderr_bytes=len("Not logged in\n"),stderr_tail="Not logged in\n")
        records[-1][1]=1
    if probe == "codex-stdio":
        response={"userAgent":"codex/0.164.0","codexHome":agent.WORK+"/agent-cases-1/"+value["case"]+"/codex",
                  "platformFamily":"unix","platformOs":"linux"}
        output=json.dumps({"id":1,"result":response})+"\n"
        value.update(initialized=True,initialize_result=response,stdin_bytes=267,
                     stdout_tail=output,stdout_bytes=len(output.encode()))
    return value, stages


def test_case_proof_accepts_completed_native_record_and_classifies_all_fixed_probes(agent):
    stages = {}
    for mode in agent.MODES:
        value, prior = case_fixture(agent, mode)
        stages.update(prior)
        if mode == "patched":
            value.update(exit_code=1, expectation_met=False, stdout_bytes=0, stdout_tail="")
            value["proof_records"][-1][1] = 1
        agent.parse_case(value, value["case"], stages)
        stages[value["case"]] = value
    assert agent.comparisons(stages) == {"codex-version":"patch_incompatible"}


@pytest.mark.parametrize("change", ["kernel", "parent", "child_pid", "exit", "mode", "extra", "fixture",
                                    "false_positive", "forged_signal", "oversize", "dumpable", "partial"])
def test_case_report_rejects_forged_positive_evidence(agent, change):
    value, stages = case_fixture(agent)
    if change == "kernel": value["proof_records"][3][1] = 0
    elif change == "parent": value["proof_records"][0][4] = 1
    elif change == "child_pid": value["proof_records"][4][2] = 555
    elif change == "exit": value["proof_records"][-1][1] = 1
    elif change == "mode": value["mode"] = "upstream"
    elif change == "extra": value["trusted"] = True
    elif change == "fixture": value["fixture_binary_sha256"] = "d"*64
    elif change == "false_positive": value["stdout_tail"] = "different"; value["stdout_bytes"] = 9
    elif change == "forged_signal": value["signal"] = 6
    elif change == "oversize": value["stdout_bytes"] = 1024**2+1
    elif change == "dumpable": value["python_nondumpable"] = False
    elif change == "partial": value["proof_records"].pop()
    with pytest.raises(agent.build.Refusal):
        agent.parse_case(value, "codex-version-patched", stages)


def assets_fixture(agent,downloaded=False):
    header={"schema_version":1,"generation":1,**agent.FLAGS}
    if downloaded:
        return header|{"status":"agent_assets_downloaded","archives":{
            name:{key:value[key] for key in ("bytes","sha256")} for name,value in agent.ASSETS.items()}}
    assets={}
    for name,selected in agent.ASSETS.items():
        files={}
        for path in agent.FILE_SETS[name]:
            metadata=path=="codex-package.json"
            files[path]={"bytes":20,"sha256":hashlib.sha256(path.encode()).hexdigest(),
                         "mode":0o400 if metadata else 0o500,
                         "elf":None if metadata else {"machine":183,"kind":3,"interpreter":None,"needed":[]}}
        omitted = json.loads((agent.build.FIXTURES/'agentcheck/voice-omissions.json').read_text())['entries'] if name == 'codex' else {}
        omitted = {path: {**entry, 'sha256': hashlib.sha256(path.encode()).hexdigest() if entry['kind'] == 'file' else None}
                   for path, entry in omitted.items()}
        assets[name]={"version":selected["version"],"archive_bytes":selected["bytes"],
                      "archive_sha256":selected["sha256"],"expanded_bytes":20*len(files),"files":files,
                      "package_scope": "probe_subset_without_voice" if name == 'codex' else 'complete',
                      "omitted_entries": omitted}
    return header|{"status":"agent_assets_verified","prefixes":{
        name:agent.WORK+"/agent-assets-1/"+name for name in agent.ASSETS},
        "assets":assets,"codex_metadata":dict(agent.CODEX_METADATA)}


def fixture_fixture(agent,built=False):
    payload={"fixture_files":{"Cargo.toml":"selected manifest","Cargo.lock":"selected lock","src/main.rs":"selected source"}}
    hashes={name:hashlib.sha256(raw.encode()).hexdigest() for name,raw in payload["fixture_files"].items()}
    hashes|={"src/upstream_child_seccomp.rs":"14c06d0d2c33a56b9a075f469a16436b92cc101186ef19a00a4f1ab84871fa0f",
             "src/patched_child_seccomp.rs":agent.build.PATCHED_SHA}
    value={"schema_version":1,"generation":1,"status":"agent_fixture_built" if built else "agent_fixture_prepared",
           "source_sha256":hashes,**agent.FLAGS}
    if built:value|={"binary_sha256":"a"*64,"binary_bytes":1024,"static_arm64":True,
                    "binary_layout":{"link_count":1,"companion":None}}
    return value,payload


def prepared_fixture(agent):
    return {"schema_version":1,"generation":1,"status":"agent_cases_prepared","cases":list(agent.CASES),
            "initial_sha256":{
                "codex_config":"77b8b75c411e1232f4ddaa8f72551615000541dc3afc68b1614f62974acae68d",
                "opencode_gitignore":"2112e764c5bff9772492998e8ef894845f4208681f9a3a6d29fc6ff71ec2050e",
                "sentinel":"2e081162edc72aae46c42433abd114adc42868a47c86eb5acbb247f6ce826457"},
            "case_state_bytes":4096,**agent.FLAGS}


@pytest.mark.parametrize("downloaded",[False,True])
def test_asset_proof_accepts_only_selected_complete_shape(agent,downloaded):
    agent.parse_assets(assets_fixture(agent,downloaded),downloaded=downloaded)


@pytest.mark.parametrize("change",["prefix","metadata","missing_file","extra_file","archive_hash","archive_size",
                                  "expansion","mode","file_hash","elf_machine","elf_kind","elf_extra","metadata_elf","enabled"])
def test_asset_proof_rejects_identity_and_layout_drift(agent,change):
    value=assets_fixture(agent);codex=value["assets"]["codex"];file=codex["files"]["bin/codex"]
    if change=="prefix":value["prefixes"]["codex"]="/foreign/codex"
    elif change=="metadata":value["codex_metadata"]["target"]="aarch64-apple-darwin"
    elif change=="missing_file":codex["files"].pop("codex-path/rg")
    elif change=="extra_file":codex["files"]["config"]=dict(file)
    elif change=="archive_hash":codex["archive_sha256"]="f"*64
    elif change=="archive_size":codex["archive_bytes"]-=1
    elif change=="expansion":codex["expanded_bytes"]+=1
    elif change=="mode":file["mode"]=0o700
    elif change=="file_hash":file["sha256"]="not-a-hash"
    elif change=="elf_machine":file["elf"]["machine"]=62
    elif change=="elf_kind":file["elf"]["kind"]=1
    elif change=="elf_extra":file["elf"]["verified"]=True
    elif change=="metadata_elf":codex["files"]["codex-package.json"]["elf"]={}
    else:value["compatibility_qualified"]=True
    with pytest.raises(agent.build.Refusal):agent.parse_assets(value)


@pytest.mark.parametrize("change",["missing","extra","hash","size","enabled"])
def test_download_report_binds_both_exact_archives(agent,change):
    value=assets_fixture(agent,True)
    if change=="missing":value["archives"].pop("codex")
    elif change=="extra":value["archives"]["other"]={}
    elif change=="hash":value["archives"]["opencode"]["sha256"]="e"*64
    elif change=="size":value["archives"]["codex"]["bytes"]+=1
    else:value["session_enabled"]=True
    with pytest.raises(agent.build.Refusal):agent.parse_assets(value,downloaded=True)


@pytest.mark.parametrize("built",[False,True])
def test_fixture_proof_binds_all_five_exact_source_files(agent,built):
    value,payload=fixture_fixture(agent,built)
    agent.parse_fixture(value,payload,built=built)
    value["source_sha256"]["src/main.rs"]="0"*64
    with pytest.raises(agent.build.Refusal,match="agent_fixture_sources"):
        agent.parse_fixture(value,payload,built=built)


@pytest.mark.parametrize("change",["upstream","patched","extra_source","dynamic","size","hash","layout","boolean_links","companion"])
def test_fixture_build_rejects_unselected_sources_or_artifact(agent,change):
    value,payload=fixture_fixture(agent,True)
    if change in ("upstream","patched"):value["source_sha256"]["src/"+change+"_child_seccomp.rs"]="f"*64
    elif change=="extra_source":value["source_sha256"]["src/other.rs"]="f"*64
    elif change=="dynamic":value["static_arm64"]=False
    elif change=="size":value["binary_bytes"]=64*1024**2+1
    elif change=="hash":value["binary_sha256"]="wrong"
    elif change=="layout":value["binary_layout"]["link_count"]=3
    elif change=="boolean_links":value["binary_layout"]["link_count"]=True
    else:value["binary_layout"]={"link_count":2,"companion":"../openshell_agent_filter_probe-0123456789abcdef"}
    with pytest.raises(agent.build.Refusal):agent.parse_fixture(value,payload,built=True)


@pytest.mark.parametrize("change",[None,"initial_hash","missing_hash","extra_case","case_order","size","boolean","enabled"])
def test_case_preparation_requires_exact_initial_bytes_and_fresh_matrix(agent,change):
    value=prepared_fixture(agent)
    if change is None:agent.parse_cases_prepared(value);return
    if change=="initial_hash":value["initial_sha256"]["codex_config"]="f"*64
    elif change=="missing_hash":value["initial_sha256"].pop("sentinel")
    elif change=="extra_case":value["cases"].append("codex-version-other")
    elif change=="case_order":value["cases"].reverse()
    elif change=="size":value["case_state_bytes"]=128*1024**2+1
    elif change=="boolean":value["case_state_bytes"]=False
    else:value["full_runtime_qualified"]=True
    with pytest.raises(agent.build.Refusal):agent.parse_cases_prepared(value)


@pytest.mark.parametrize("probe",["codex-version","codex-help","codex-empty-login","codex-stdio",
                                  "opencode-version","opencode-help","opencode-rg"])
@pytest.mark.parametrize("mode",["unfiltered","upstream","patched"])
def test_each_fixed_positive_predicate_is_reconstructed(agent,probe,mode):
    value,stages=case_fixture(agent,mode,probe)
    agent.parse_case(value,value["case"],stages)


@pytest.mark.parametrize("stdin_bytes",[0,1,266,268,True])
def test_stdio_positive_requires_exact_two_source_fixed_messages(agent,stdin_bytes):
    value,stages=case_fixture(agent,probe="codex-stdio")
    value["stdin_bytes"]=stdin_bytes
    with pytest.raises(agent.build.Refusal):agent.parse_case(value,value["case"],stages)


@pytest.mark.parametrize("change",["home","platform","useragent","extra","missing","nonstdio"])
def test_stdio_result_does_not_admit_another_home_or_unsolicited_identity(agent,change):
    value,stages=case_fixture(agent,probe="codex-stdio")
    if change=="home":value["initialize_result"]["codexHome"]="/ordinary/codex"
    elif change=="platform":value["initialize_result"]["platformOs"]="macos"
    elif change=="useragent":value["initialize_result"]["userAgent"]=""
    elif change=="extra":value["initialize_result"]["account"]="unselected"
    elif change=="missing":value["initialize_result"]=None
    else:value["case"]="codex-help-patched";value["probe"]="codex-help"
    with pytest.raises(agent.build.Refusal):agent.parse_case(value,value["case"],stages)


@pytest.mark.parametrize("observation",["timeout","output_limit","protocol_error","launch_error","filter_install_error","proof_error"])
def test_controller_or_proof_failure_never_becomes_negative_compatibility(agent,observation):
    value,stages=case_fixture(agent);value.update(observation=observation,expectation_met=False)
    with pytest.raises(agent.build.Refusal,match="agent_case_unexpected"):
        agent.parse_case(value,value["case"],stages)


def test_native_signal_can_be_recorded_but_controller_kill_cannot(agent):
    value,stages=case_fixture(agent);value.update(exit_code=None,signal=6,expectation_met=False)
    value["proof_records"][-1]=[5,-1,6,0,0,0,0]
    agent.parse_case(value,value["case"],stages)
    value["termination_requested"]=True
    with pytest.raises(agent.build.Refusal,match="agent_case_unexpected"):
        agent.parse_case(value,value["case"],stages)


@pytest.mark.parametrize("mode",["unfiltered","upstream"])
def test_failed_control_stops_its_comparison(agent,mode):
    stages={"codex-version-"+item:{"expectation_met":item!=mode} for item in agent.MODES}
    with pytest.raises(agent.build.Refusal,match="agent_control_failed"):agent.comparisons(stages)


def test_comparison_needs_both_controls_and_continues_independent_negative_results(agent):
    with pytest.raises(agent.build.Refusal,match="agent_comparison_order"):
        agent.comparisons({"codex-stdio-patched":{"expectation_met":False}})
    stages={probe+"-"+mode:{"expectation_met":mode!="patched" or probe=="opencode-version"}
            for probe in ("codex-stdio","opencode-version","opencode-rg") for mode in agent.MODES}
    assert agent.comparisons(stages)=={"codex-stdio":"patch_incompatible",
        "opencode-version":"selected_probe_compatible","opencode-rg":"patch_incompatible"}


@pytest.mark.parametrize("change", ["boolean_metadata", "loader", "parent_dep", "duplicate_dep"])
def test_asset_report_matches_guest_elf_and_metadata_constraints(agent, change):
    value = assets_fixture(agent)
    elf = value['assets']['codex']['files']['bin/codex']['elf']
    if change == 'boolean_metadata': value['codex_metadata']['layoutVersion'] = True
    elif change == 'loader': elf['interpreter'] = 'relative-loader'
    elif change == 'parent_dep': elf['needed'] = ['..']
    else: elf['needed'] = ['libc.so', 'libc.so']
    with pytest.raises(agent.build.Refusal): agent.parse_assets(value)


@pytest.mark.parametrize("probe", ['codex-version', 'codex-help', 'codex-stdio'])
def test_successful_output_cannot_claim_zero_received_bytes(agent, probe):
    value, stages = case_fixture(agent, probe=probe)
    value['stdout_bytes'] = 0
    with pytest.raises(agent.build.Refusal): agent.parse_case(value, value['case'], stages)


def test_actual_stage_compositions_fit_existing_caps(agent, tmp_path):
    payload = agent.load_bundle(tmp_path).payload
    prepared, _ = fixture_fixture(agent)
    prepared['source_sha256'].update({name:hashlib.sha256(raw.encode()).hexdigest()
                                    for name, raw in payload['fixture_files'].items()})
    built, _ = fixture_fixture(agent, True)
    built['source_sha256'] = prepared['source_sha256']
    completed = {'fixture-prepare':prepared, 'fixture-build':built, 'agent-verify':assets_fixture(agent)}
    payload['resume_history'] = {'fixture': built}
    agent.parse_fixture(prepared, payload)
    agent.parse_fixture(built, payload, built=True)
    controller = (agent.build.FIXTURES/'guest_build_storage.py').read_text()
    runtime = (agent.build.FIXTURES/'guest_runtime.py').read_text()
    inventory = (agent.build.FIXTURES/'guest_build_inventory.py').read_text()
    for operation in agent.OPERATIONS:
        selected = dict(completed)
        if operation == 'agent-test-resume':
            selected.pop('fixture-build')
            selected['fixture-verify'] = built | {'status': 'agent_fixture_verified'}
        sources = agent.capture_sources(operation)
        for stage, key, _, maximum in agent.STAGES[operation]:
            unit = agent.unit_source(sources[key], payload, stage, maximum-5, selected)
            compile(unit, '<agent-unit>', 'exec')
            if stage in agent.CASES:
                assert 'validate_context()\n_result=agent_case' not in unit
            script = agent.stage_script(controller, runtime, inventory, sources[key], payload,
                operation, stage, maximum+100, host_binding_sha256='d'*64, completed=selected)
            compile(script, '<agent-root>', 'exec')
            compile(agent.build.encode_program(script), '<agent-transport>', 'exec')


def test_descriptor_inspection_is_one_offline_fixed_case_without_agent_execution(agent):
    assert agent.STAGES['agent-inspect'] == (('agent-descriptors','cases',False,30),)
    source = agent.unit_source('', {}, 'agent-descriptors', 25, {})
    assert '_result=agent_descriptor_inspect()' in source
    assert 'agent_case(' not in source and 'validate_context()' not in source
    script = agent.stage_script('', '', '', '', {}, 'agent-inspect', 'agent-descriptors', 130,
                                host_binding_sha256='d'*64)
    assert "agent_case='codex-version-unfiltered'" in script


def test_descriptor_metadata_never_enables_a_session_or_accepts_changed_fd_state(agent):
    rows=[{'fd':fd,'errno':9,'mode':None,'rdev':None,'fd_flags':None,'status_flags':None} for fd in range(4)]
    value={'schema_version':1,'generation':1,'status':'agent_descriptors_observed',
           'before':rows,'after_validation':rows,'after_close':rows,'reserved_fd':0,
           'reserved_null':True,**agent.FLAGS}
    agent.parse_descriptors(value)
    value['reserved_null']=False
    with pytest.raises(agent.build.Refusal):agent.parse_descriptors(value)
    value['reserved_null']=True;value['after_close']=rows[:-1]
    with pytest.raises(agent.build.Refusal):agent.parse_descriptors(value)


def test_bundle_and_asset_stages_bind_exact_omission_source(agent, tmp_path):
    bundle = agent.load_bundle(tmp_path)
    raw = (agent.build.FIXTURES/'agentcheck/voice-omissions.json').read_bytes()
    expected = json.loads(raw)
    assert bundle.payload['voice_omissions'] == expected
    assert bundle.source_hashes['agentcheck/voice-omissions.json'] == hashlib.sha256(raw).hexdigest()
    assert hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == '478394bae952fff452aa79788abe07f3b2a44b1439c88b91da2919250cde7780'
    for stage in ('agent-download', 'agent-prepare', 'agent-verify', 'agent-final'):
        assert agent.stage_payload(bundle.payload, stage, {}) == {
            'agent_manifest': bundle.payload['agent_manifest'], 'voice_omissions': expected}
    for stage in ('fixture-prepare', 'fixture-build', 'cases-prepare', *agent.CASES):
        assert 'voice_omissions' not in agent.stage_payload(bundle.payload, stage, {})


@pytest.mark.parametrize('change', ['archive', 'path', 'bytes', 'mode', 'kind', 'boolean_schema', 'extra'])
def test_changed_omission_source_refuses_before_bundle_return(agent, monkeypatch, change):
    original = agent.build.read_source
    value = json.loads(original(agent.build.FIXTURES/'agentcheck/voice-omissions.json'))
    selected = next(name for name, entry in value['entries'].items() if entry['kind'] == 'file')
    if change == 'archive': value['archive_sha256'] = '0'*64
    elif change == 'path': value['entries']['../escape'] = value['entries'].pop(selected)
    elif change in ('bytes', 'mode'): value['entries'][selected][change] += 1
    elif change == 'kind': value['entries'][selected]['kind'] = 'link'
    elif change == 'boolean_schema': value['schema_version'] = True
    else: value['trusted'] = True
    def altered(path):
        return json.dumps(value).encode() if path.name == 'voice-omissions.json' else original(path)
    monkeypatch.setattr(agent.build, 'read_source', altered)
    with pytest.raises(agent.build.Refusal, match='agent_voice_omissions'): agent.voice_omissions()


@pytest.mark.parametrize('change', ['missing', 'extra', 'mode', 'bytes', 'kind', 'hash', 'file_null',
    'directory_hash', 'directory_false', 'boolean_mode', 'boolean_bytes', 'extra_field', 'scope',
    'opencode_omission', 'opencode_scope', 'combined_expansion'])
def test_asset_omission_proof_requires_exact_archive_layout(agent, change):
    value = assets_fixture(agent); codex = value['assets']['codex']; entries = codex['omitted_entries']
    selected = next(name for name, entry in entries.items() if entry['kind'] == 'file')
    directory = next(name for name, entry in entries.items() if entry['kind'] == 'directory')
    if change == 'missing': entries.pop(selected)
    elif change == 'extra': entries['codex-resources/voice/unknown'] = dict(entries[selected])
    elif change in ('mode', 'bytes'): entries[selected][change] += 1
    elif change == 'kind': entries[selected]['kind'] = 'link'
    elif change == 'hash': entries[selected]['sha256'] = 'unverified'
    elif change == 'file_null': entries[selected]['sha256'] = None
    elif change == 'directory_hash': entries[directory]['sha256'] = 'a'*64
    elif change == 'directory_false': entries[directory]['sha256'] = False
    elif change == 'boolean_mode': entries[selected]['mode'] = True
    elif change == 'boolean_bytes': entries[directory]['bytes'] = False
    elif change == 'extra_field': entries[selected]['trusted'] = True
    elif change == 'scope': codex['package_scope'] = 'complete'
    elif change == 'opencode_omission': value['assets']['opencode']['omitted_entries'] = {selected: entries[selected]}
    elif change == 'opencode_scope': value['assets']['opencode']['package_scope'] = 'probe_subset_without_voice'
    else:
        total = agent.ASSETS['codex']['expanded_limit']
        codex['files']['bin/codex']['bytes'] = total - 80
        codex['expanded_bytes'] = total
    with pytest.raises(agent.build.Refusal): agent.parse_assets(value)


def resume_history_fixture(agent, tmp_path, monkeypatch):
    from test_openshell_guest_build import inventory_report
    root = tmp_path.resolve() / 'run'
    directory = root / 'evidence/guest-build-agent-test-1'
    directory.mkdir(parents=True, mode=0o700)
    for path in (root, root/'evidence', directory): path.chmod(0o700)
    fixture, payload = fixture_fixture(agent, True)
    inventory = inventory_report(); inventory.pop('unmounted_verified')
    def outer(stage, result):
        return {'status':'agent_stage_completed','operation':'agent-test','stage':stage,
                'result':result,'runtime':None,'inventory_before':inventory,'inventory_after':inventory,
                'unmounted_verified':True,**agent.FLAGS}
    receipt = json.loads((agent.build.FIXTURES/'agentcheck/resume-receipt.json').read_bytes())
    objects = {
        'fixture': outer('fixture-build', fixture),
        'cases': outer('cases-prepare', prepared_fixture(agent)),
        'experiment': {'schema_version':1,'source_commit':receipt['source_commit'],
                       'source_sha256':{'tests/fixtures/openshell_runtime/agentcheck/'+local:
                            hashlib.sha256(payload['fixture_files'][name].encode()).hexdigest()
                            for name,local in [('Cargo.toml','Cargo.toml'),('Cargo.lock','Cargo.lock'),('src/main.rs','main.rs')]}},
        'stop': {'schema_version':1,'status':'refused','blockers':['guest_agent_failed'],
                 'vm_start_requested':True,'stop_requested':True,'stopped_verified':True,
                 'shutdown_uncertain':False,'session_enabled':False,'elapsed_seconds':75.0,
                 'diagnostic_bytes':1000,'diagnostic_commands_omitted':0},
        'failure': "_result=agent_case(_stage_payload,'codex-version-unfiltered')\nRuntimeError: agent_proof_fd_collision\nRefusal: unit_failed\n",
    }
    def publish():
        for key, value in objects.items():
            raw = value.encode() if type(value) is str else json.dumps(value).encode()
            path = directory/receipt['files'][key]['name']
            path.write_bytes(raw); path.chmod(0o600)
            receipt['files'][key].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    publish()
    monkeypatch.setattr(agent, 'resume_receipt', lambda: receipt)
    return root, directory, receipt, objects, payload, publish


def test_resume_receipt_is_source_pinned_and_bundle_records_it(agent, tmp_path):
    value = agent.resume_receipt()
    canonical = json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    assert hashlib.sha256(canonical).hexdigest() == '2c1e547f02e4e621fff711e3be327b347604896933712cf50e3df22583d1b4cc'
    bundle = agent.load_bundle(tmp_path)
    assert 'agentcheck/resume-receipt.json' in bundle.source_hashes


def test_resume_history_admits_only_current_fixture_and_preserves_old_reports(agent, tmp_path, monkeypatch):
    root, _, receipt, objects, payload, _ = resume_history_fixture(agent,tmp_path,monkeypatch)
    result = agent.load_resume_history(root,payload)
    assert result['fixture'] == objects['fixture']['result']
    assert result['cases'] == objects['cases']['result']
    assert result['source_commit'] == receipt['source_commit']
    assert result['files'] == receipt['files']


@pytest.mark.parametrize('change',['symlink','hardlink','public_file','public_directory','symlink_directory','hash','oversized','foreign_owner','swapped'])
def test_resume_history_rejects_path_or_file_admission_failure(agent,tmp_path,monkeypatch,change):
    root,directory,receipt,_,payload,_ = resume_history_fixture(agent,tmp_path,monkeypatch)
    path = directory/receipt['files']['fixture']['name']
    if change == 'symlink':
        saved=directory/'saved';path.rename(saved);path.symlink_to(saved)
    elif change == 'hardlink': os.link(path,directory/'alias')
    elif change == 'public_file': path.chmod(0o644)
    elif change == 'public_directory': directory.chmod(0o755)
    elif change == 'symlink_directory':
        saved=root/'saved';directory.rename(saved);directory.symlink_to(saved,target_is_directory=True)
    elif change == 'hash': path.write_bytes(b'x'*path.stat().st_size)
    elif change == 'oversized': path.write_bytes(path.read_bytes()+b'x')
    elif change == 'foreign_owner':
        uid=os.getuid();monkeypatch.setattr(agent.os,'getuid',lambda:uid+1)
    elif change == 'swapped':
        original=agent.os.read;done=False
        def swap(fd,count):
            nonlocal done
            raw=original(fd,count)
            if not done and os.fstat(fd).st_ino == path.stat().st_ino:
                done=True; saved=directory/'swap';saved.write_bytes(path.read_bytes());saved.chmod(0o600);saved.replace(path)
            return raw
        monkeypatch.setattr(agent.os,'read',swap)
    with pytest.raises(agent.build.Refusal): agent.load_resume_history(root,payload)


@pytest.mark.parametrize('change',['commit','source','current_source','running','uncertain','omitted','failure','fixture_stage','cases_stage','case_initial','binary','extra_stop'])
def test_resume_semantics_refuse_even_with_matching_fixture_checksums(agent,tmp_path,monkeypatch,change):
    root,_,_,objects,payload,publish=resume_history_fixture(agent,tmp_path,monkeypatch)
    if change=='commit':objects['experiment']['source_commit']='f'*40
    elif change=='source':objects['experiment']['source_sha256'][next(iter(objects['experiment']['source_sha256']))]='f'*64
    elif change=='current_source':payload['fixture_files']['src/main.rs']+='changed'
    elif change=='running':objects['stop']['stopped_verified']=False
    elif change=='uncertain':objects['stop']['shutdown_uncertain']=True
    elif change=='omitted':objects['stop']['diagnostic_commands_omitted']=1
    elif change=='failure':objects['failure']='RuntimeError: other_failure'
    elif change=='fixture_stage':objects['fixture']['stage']='fixture-prepare'
    elif change=='cases_stage':objects['cases']['operation']='agent-test-resume'
    elif change=='case_initial':objects['cases']['result']['initial_sha256']['sentinel']='f'*64
    elif change=='binary':objects['fixture']['result']['static_arm64']=False
    else:objects['stop']['unselected']=True
    publish()
    with pytest.raises(agent.build.Refusal):agent.load_resume_history(root,payload)


def test_resume_refuses_before_boot_or_bundle_side_effects(agent,tmp_path,monkeypatch):
    monkeypatch.setattr(agent,'load_bundle',lambda *a:pytest.fail('preboot bundle'))
    monkeypatch.setattr(agent.boot,'_qualify_with_inspection',lambda *a,**k:pytest.fail('boot'))
    selection=SimpleNamespace(storage=SimpleNamespace(run_root=tmp_path/'missing'))
    with pytest.raises(agent.build.Refusal):agent.qualify(selection,'agent-test-resume')


def test_resume_fixed_stages_verify_without_build_or_reinitialization(agent):
    stages=agent.STAGES['agent-test-resume']
    assert len(stages)==29 and all(not row[2] for row in stages)
    assert [row[0] for row in stages[:6]]==['rust-verify','compiler-verify','source-verify','agent-verify','fixture-verify','cases-verify']
    assert not {'fixture-prepare','fixture-build','cases-prepare'} & {row[0] for row in stages}
    built,payload=fixture_fixture(agent,True);payload['resume_history']={'fixture':built}
    assert agent.stage_payload(payload,'fixture-verify',{})=={'agent_build_report':built}
    assert agent.stage_payload(payload,'cases-verify',{})=={}
    for stage,call in [('fixture-verify','agent_build_verify'),('cases-verify','agent_cases_verify')]:
        unit=agent.unit_source('',payload,stage,50,{})
        assert f'_result={call}(_stage_payload)' in unit and 'validate_context()' not in unit
    verified=built|{'status':'agent_fixture_verified'}
    agent.parse_fixture(verified,payload,built=True,verified=True)
    agent.parse_cases_prepared(prepared_fixture(agent)|{'status':'agent_cases_verified'},verified=True)
    value,prior=case_fixture(agent)
    prior['fixture-verify']=prior.pop('fixture-build')
    agent.parse_case(value,value['case'],prior)
    prior['fixture-build']=prior['fixture-verify']
    with pytest.raises(agent.build.Refusal):agent.parse_case(value,value['case'],prior)
