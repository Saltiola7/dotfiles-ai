"""Closed client comparison orchestration; these tests start no native worker."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
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
    assert agent.OPERATIONS == ("agent-prepare", "agent-test")
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


@pytest.mark.parametrize("operation", ["agent-prepare", "agent-test"])
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
        assets[name]={"version":selected["version"],"archive_bytes":selected["bytes"],
                      "archive_sha256":selected["sha256"],"expanded_bytes":20*len(files),"files":files}
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
    agent.parse_fixture(prepared, payload)
    agent.parse_fixture(built, payload, built=True)
    controller = (agent.build.FIXTURES/'guest_build_storage.py').read_text()
    runtime = (agent.build.FIXTURES/'guest_runtime.py').read_text()
    inventory = (agent.build.FIXTURES/'guest_build_inventory.py').read_text()
    for operation in agent.OPERATIONS:
        sources = agent.capture_sources(operation)
        for stage, key, _, maximum in agent.STAGES[operation]:
            unit = agent.unit_source(sources[key], payload, stage, maximum-5, completed)
            compile(unit, '<agent-unit>', 'exec')
            if stage in agent.CASES:
                assert 'validate_context()\n_result=agent_case' not in unit
            script = agent.stage_script(controller, runtime, inventory, sources[key], payload,
                operation, stage, maximum+100, host_binding_sha256='d'*64, completed=completed)
            compile(script, '<agent-root>', 'exec')
            compile(agent.build.encode_program(script), '<agent-transport>', 'exec')
