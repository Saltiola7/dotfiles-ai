import argparse
import hashlib
import io
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
DKSCTL = ROOT / "dot_local/bin/executable_dksctl"


def load_dksctl():
    loader = importlib.machinery.SourceFileLoader("dksctl_module", str(DKSCTL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, text=True,
                          capture_output=True).stdout.strip()


def render(path: str, *, enabled: bool = True, model_root: str = "/Volumes/ext/lmstudio") -> str:
    values = {
        "dotfiles_ai": {
            "state": {"root": "/Volumes/ext/state"},
            "knowledge_store": {
                "enabled": enabled,
                "model_root": model_root,
                "quality_model_root": "/Volumes/ext/state/models",
                "embedding_port": 11435,
                "embedding_dimensions": 4096,
                "embedding_context_tokens": 4096,
                "quality_services_enabled": True,
                "code_embedding_port": 11436,
                "reranker_port": 11437,
            },
        }
    }
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(values),
            "execute-template",
        ],
        input=(ROOT / path).read_text(),
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def test_knowledge_store_defaults_off_and_is_host_only() -> None:
    defaults = (ROOT / ".chezmoidata.toml").read_text()
    example = (ROOT / "config.example.toml").read_text()
    ignore = (ROOT / ".chezmoiignore").read_text()

    assert "[dotfiles_ai.knowledge_store]" in defaults
    assert "[data.dotfiles_ai.knowledge_store]" in example
    assert 'model_root = ""' in defaults
    assert "embedding_port = 11435" in defaults + example
    assert "embedding_dimensions = 4096" in defaults + example
    assert ".dotfiles_ai.knowledge_store.enabled" in ignore
    assert "dev.dotfiles-ai.dbsctr-embedding.plist" in ignore
    assert "install-dbsctr-embedding.sh" in ignore


def test_installer_pins_runtime_and_model_and_installs_atomically() -> None:
    source = (ROOT / "run_onchange_after_install-dbsctr-embedding.sh.tmpl").read_text()
    rendered = render("run_onchange_after_install-dbsctr-embedding.sh.tmpl")

    assert "llama-b10505-bin-macos-arm64.tar.gz" in source
    assert "d3383ae8c2a435a2ded122b243e971ca96b9bee6fde29a3b9889e85c8cf19176" in source
    assert "Qwen3-Embedding-8B-Q4_K_M.gguf" in source
    assert "69d0e58a13e463cd99a9b83e3f5fee7c10265fab" in source
    assert "3fcd3febec8b3fd64435204db75bf0dd73b91e8d0661e0331acfe7e7c3120b85" in source
    assert 'mktemp "${destination}.part.XXXXXX"' in source
    assert "shasum -a 256 -c" in source
    assert 'mv -f "$temporary" "$destination"' in source
    assert "download() (" in source
    assert "openssl rand -hex 32" in source
    assert 'chmod 0600 "$api_key"' in source
    assert "umask 077" in source
    assert "dbsctr-embedding-runtime-verify\" archive" in source
    assert "safe_mkdir" in source
    assert "/usr/bin/openssl" in rendered and "--identifier dev.dotfiles-ai.launch-sha256" in rendered
    assert "/usr/bin/codesign --verify --strict" in rendered
    assert 'chmod -R u=rX,go=rX "$runtime"' in rendered
    assert "/Volumes/ext/lmstudio" in rendered
    assert 'model="$model_root/dbsctr/qwen3-embedding-8b' in rendered
    assert "-hf" not in rendered


def test_wrapper_fails_closed_and_uses_explicit_embedding_semantics() -> None:
    source = (ROOT / "dot_local/bin/executable_dbsctr-embedding.tmpl").read_text()
    rendered = render("dot_local/bin/executable_dbsctr-embedding.tmpl")

    assert "d0878274b8d6bd3c8ea26a78eb66cd1ffd943d007c62b9dff31c8aa99922d713" in source
    assert "3fcd3febec8b3fd64435204db75bf0dd73b91e8d0661e0331acfe7e7c3120b85" in source
    assert "--embedding" in rendered
    assert "--pooling" in rendered and "last" in rendered
    assert "--embd-normalize" in rendered and "2" in rendered
    assert "--host" in rendered and "127.0.0.1" in rendered
    assert "--port" in rendered and "11435" in rendered
    assert "--api-key-file" in rendered
    assert "--offline" in rendered and "--metrics" in rendered and "--no-webui" in rendered
    assert "--log-disable" in rendered and "--no-cache-prompt" in rendered
    assert "--parallel 1" in rendered
    assert "curl" not in rendered.split('serve)')[1].split(';;', 1)[0]
    assert "launch-sha256" in rendered and "XPC_SERVICE_NAME" in rendered
    assert "runtime_archive" in rendered and "/usr/bin/shasum" not in rendered
    assert "dot(vectors[0], vectors[1]) < 0.9999" in rendered
    assert '! -L "$api_key"' in rendered and "^[0-9a-f]{64}$" in rendered
    assert 'base64 -A -in "$api_key"' in rendered
    assert "4096" in rendered


def test_manifest_and_launchagent_are_stable_and_private(tmp_path: Path) -> None:
    manifest = json.loads(render("private_dot_config/dotfiles-ai/knowledge/embedding-space.json.tmpl"))
    assert manifest["schema_version"] == 1
    assert manifest["embedding_space_id"].startswith("qwen3e8b-")
    assert manifest["model"]["revision"] == "69d0e58a13e463cd99a9b83e3f5fee7c10265fab"
    assert manifest["runtime"]["version"] == "b10505"
    assert manifest["contract"] == {
        "context_tokens": 4096,
        "dimensions": 4096,
        "normalization": "l2",
        "pooling": "last",
    }
    assert manifest["query"] == {
        "format": "Instruct: {instruction}\nQuery:{query}",
        "instruction": "Retrieve authoritative DBSCTR engineering evidence",
        "template_version": "dks-query-v1",
    }

    plist = render("private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-embedding.plist.tmpl")
    target = tmp_path / "embedding.plist"
    target.write_text(plist)
    subprocess.run(["plutil", "-lint", str(target)], check=True, capture_output=True)
    assert "dev.dotfiles-ai.dbsctr-embedding" in plist
    assert "state-root-exec" in plist and "dbsctr-embedding" in plist
    assert "RunAtLoad" in plist and "KeepAlive" in plist
    assert "127.0.0.1" not in plist  # Wrapper owns network arguments.


def test_quality_service_manifests_wrappers_and_launchagents_are_pinned(tmp_path: Path) -> None:
    code = json.loads(render("private_dot_config/dotfiles-ai/knowledge/code-embedding-space.json.tmpl"))
    reranker = json.loads(render("private_dot_config/dotfiles-ai/knowledge/reranker-space.json.tmpl"))
    assert code["contract"] == {"context_tokens": 32768, "dimensions": 3584,
                                "normalization": "l2", "pooling": "last"}
    assert code["runtime"]["server_sha256"] == \
        "eca763b9ea33ec611614d36a192353599fcf0a872d66d82c00e5764fdd5ea2f6"
    assert reranker["runtime"] == {"backend": "mps", "python": "3.12.11",
                                    "safetensors": "0.7.0", "tokenizers": "0.22.2",
                                    "torch": "2.9.1", "transformers": "5.5.0"}
    assert reranker["contract"] | {"template_sha256": None} == {
        "batch_size": 1, "context_tokens": 4096, "instruction":
        "Retrieve authoritative DBSCTR engineering evidence that answers the query",
        "logits_to_keep": 1, "max_mps_memory_gib": 20, "max_process_memory_gib": 24,
        "score": "binary_softmax_yes",
        "template_sha256": None, "truncation": "longest_first", "use_cache": False,
    }
    assert reranker["contract"]["template_sha256"] == \
        "c121f3f58991533a6cf1dd73429dc22a4bf0072b65b87b5ccfed274c7b55dde9"
    code_wrapper = render("dot_local/bin/executable_dbsctr-code-embedding.tmpl")
    assert "--pooling last" in code_wrapper and "--embd-normalize 2" in code_wrapper
    assert "--offline" in code_wrapper and "--no-webui" in code_wrapper and "--log-disable" in code_wrapper
    reranker_wrapper = render("dot_local/bin/executable_dbsctr-reranker.tmpl")
    compile(reranker_wrapper, "dbsctr-reranker", "exec")
    assert "local_files_only=True" in reranker_wrapper and "trust_remote_code=False" in reranker_wrapper
    assert "BATCH_SIZE = 1" in reranker_wrapper and "MAX_MPS_MEMORY_GIB = 20" in reranker_wrapper
    assert "MAX_PROCESS_MEMORY_GIB = 24" in reranker_wrapper
    assert "set_per_process_memory_fraction" in reranker_wrapper
    assert "use_cache=False, logits_to_keep=1" in reranker_wrapper
    assert "ThreadingHTTPServer((\"127.0.0.1\", PORT)" in reranker_wrapper
    assert "build_opener(NoRedirect)" in reranker_wrapper
    assert "build_opener(NoRedirect)" in render("dot_local/bin/executable_dbsctr-code-embedding.tmpl")
    graphify_wrapper = (ROOT / "dot_local/bin/executable_dbsctr-graphify").read_text()
    compile(graphify_wrapper, "dbsctr-graphify", "exec")
    assert "(deny network*)" in graphify_wrapper
    assert "71cb98287d1e526a8f8be9f60d10462de2df8c547bb1c5bfca2376e07a056be8" in graphify_wrapper
    models = json.loads((ROOT / "docs/specs/dbsctr_knowledge_store/DKS-003.models.json").read_text())
    assert models["graphify"]["runtime_sha256"] in graphify_wrapper
    assert models["graphify"]["producer_sha256"] == \
        hashlib.sha256(graphify_wrapper.encode()).hexdigest()
    assert "(deny default)" in graphify_wrapper and "(deny network*)" in graphify_wrapper
    installer = (ROOT / "run_onchange_after_install-dbsctr-quality-services.sh.tmpl").read_text()
    assert "graphify-sql-0.9.48-71cb9828" in installer
    assert 'candidate_root="$HOME/.config/dotfiles-ai/models' not in installer
    for name in ("code-embedding", "reranker"):
        plist = render(f"private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-{name}.plist.tmpl")
        target = tmp_path / f"{name}.plist"
        target.write_text(plist)
        subprocess.run(["plutil", "-lint", str(target)], check=True, capture_output=True)
    for name in ("code-embedding", "reranker"):
        manifest = json.loads(render(f"private_dot_config/dotfiles-ai/knowledge/{name}-space.json.tmpl"))
        assert manifest["service"]["artifact_root"] == "/Volumes/ext/state/models/dbsctr"


def test_loader_bootstraps_only_after_install_and_removes_only_owned_targets() -> None:
    source = (ROOT / "run_onchange_after_load-dbsctr-embedding.sh.tmpl").read_text()
    enabled = render("run_onchange_after_load-dbsctr-embedding.sh.tmpl")
    disabled = render("run_onchange_after_load-dbsctr-embedding.sh.tmpl", enabled=False)

    assert enabled.index('"$wrapper" verify') < enabled.index("launchctl bootstrap")
    assert enabled.index('prior service did not unload') < enabled.index("launchctl bootstrap")
    assert enabled.index("launchctl bootstrap") < enabled.index('"$wrapper" check')
    assert "dev.dotfiles-ai.dbsctr-embedding" in disabled
    assert 'launchctl bootout "$domain/$label"' in disabled
    assert disabled.index('launchctl print "$domain/$label"') < disabled.index('launchctl bootout "$domain/$label"')
    assert 'rm -f "$plist"' in disabled
    assert "rm -rf" not in source
    assert "Qwen3-Embedding" not in disabled
    assert "cleanup_candidate" in enabled and "trap cleanup_candidate ERR" in enabled
    assert "trap cleanup_signal INT TERM" in enabled


@pytest.mark.parametrize(
    "path",
    [
        "dot_local/bin/executable_dbsctr-embedding.tmpl",
        "run_onchange_after_install-dbsctr-embedding.sh.tmpl",
        "run_onchange_after_load-dbsctr-embedding.sh.tmpl",
    ],
)
def test_rendered_shell_is_valid(path: str) -> None:
    subprocess.run(["/bin/bash", "-n"], input=render(path), text=True, check=True)


def test_runtime_tree_verifier_detects_drift_and_unsafe_links(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "llama-server").write_bytes(b"server")
    (runtime / "lib.dylib").write_bytes(b"library")
    (runtime / "lib-current.dylib").symlink_to("lib.dylib")

    rows = [
        ("lib-current.dylib", "L", "lib.dylib"),
        ("lib.dylib", "F", hashlib.sha256(b"library").hexdigest()),
        ("llama-server", "F", hashlib.sha256(b"server").hexdigest()),
    ]
    digest = hashlib.sha256()
    for relative, kind, value in rows:
        digest.update(relative.encode() + b"\0" + kind.encode() + b"\0" + value.encode() + b"\n")
    verifier = ROOT / "dot_local/bin/executable_dbsctr-embedding-runtime-verify"
    subprocess.run(["python3", str(verifier), "tree", str(runtime), digest.hexdigest()], check=True)

    (runtime / "lib.dylib").write_bytes(b"changed")
    assert subprocess.run(["python3", str(verifier), "tree", str(runtime), digest.hexdigest()]).returncode != 0
    (runtime / "lib.dylib").write_bytes(b"library")
    (runtime / "unsafe").symlink_to("../outside")
    assert subprocess.run(["python3", str(verifier), "tree", str(runtime), digest.hexdigest()]).returncode != 0


def test_runtime_archive_verifier_rejects_escaping_members(tmp_path: Path) -> None:
    verifier = ROOT / "dot_local/bin/executable_dbsctr-embedding-runtime-verify"
    archive = tmp_path / "runtime.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        content = b"server"
        member = tarfile.TarInfo("llama-b10505/llama-server")
        member.size = len(content)
        stream.addfile(member, io.BytesIO(content))
    expected = hashlib.sha256(
        b"llama-server\0F\0" + hashlib.sha256(b"server").hexdigest().encode() + b"\n"
    ).hexdigest()
    subprocess.run(["python3", str(verifier), "archive", str(archive), expected], check=True)

    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo("../escape")
        member.size = 1
        stream.addfile(member, io.BytesIO(b"x"))
    assert subprocess.run(["python3", str(verifier), "archive", str(archive), expected]).returncode != 0


def test_loader_unloads_before_cleanup_and_unloads_failed_candidate(tmp_path: Path) -> None:
    home = tmp_path / "home"
    plist = home / "Library/LaunchAgents/dev.dotfiles-ai.dbsctr-embedding.plist"
    wrapper = home / ".local/bin/dbsctr-embedding"
    verifier = home / ".local/bin/dbsctr-embedding-runtime-verify"
    manifest = home / ".config/dotfiles-ai/knowledge/embedding-space.json"
    for parent in {plist.parent, wrapper.parent, manifest.parent}:
        parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(render("private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-embedding.plist.tmpl"))
    for path in (wrapper, verifier, manifest):
        path.write_text("owned")
    wrapper.chmod(0o755)

    state = tmp_path / "launch-state"
    state.touch()
    launchctl = tmp_path / "launchctl"
    launchctl.write_text(
        "#!/bin/bash\n"
        "case $1 in\n"
        "  print) [[ -e $FAKE_LAUNCH_STATE ]];;\n"
        "  bootout) rm -f \"$FAKE_LAUNCH_STATE\";;\n"
        "  bootstrap) touch \"$FAKE_LAUNCH_STATE\";;\n"
        "esac\n"
    )
    launchctl.chmod(0o755)
    env = {"HOME": str(home), "FAKE_LAUNCH_STATE": str(state), "PATH": "/usr/bin:/bin"}

    disabled = render("run_onchange_after_load-dbsctr-embedding.sh.tmpl", enabled=False)
    disabled = disabled.replace("/bin/launchctl", str(launchctl))
    subprocess.run(["/bin/bash"], input=disabled, text=True, env=env, check=True)
    assert not state.exists()
    assert not any(path.exists() for path in (plist, wrapper, verifier, manifest))

    plist.parent.mkdir(parents=True, exist_ok=True)
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(render("private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-embedding.plist.tmpl"))
    wrapper.write_text("#!/bin/bash\n[[ $1 == verify ]]\n")
    wrapper.chmod(0o755)
    manifest.write_text("owned")
    curl = tmp_path / "curl"
    curl.write_text("#!/bin/sh\nexit 0\n")
    curl.chmod(0o755)
    enabled = render("run_onchange_after_load-dbsctr-embedding.sh.tmpl")
    enabled = enabled.replace("/bin/launchctl", str(launchctl)).replace("/usr/bin/curl", str(curl))
    failed = subprocess.run(["/bin/bash"], input=enabled, text=True, env=env)
    assert failed.returncode != 0
    assert not state.exists()


@pytest.mark.parametrize(
    ("model_root", "message"),
    [
        ("relative/models", "absolute"),
        ("/Volumes/ext/../private", "dot-dot"),
        ("", "absolute"),
    ],
)
def test_enabled_render_rejects_unsafe_model_roots(model_root: str, message: str) -> None:
    with pytest.raises(subprocess.CalledProcessError) as error:
        render("run_onchange_after_install-dbsctr-embedding.sh.tmpl", model_root=model_root)
    assert message in error.value.stderr


def test_dks002_schema_is_scoped_exact_and_rerunnable() -> None:
    schema = (ROOT / "dot_local/share/dbsctr-knowledge/schema.sql").read_text()

    assert "CREATE EXTENSION IF NOT EXISTS vector" in schema
    assert "vector(4096)" in schema
    assert "USING hnsw" not in schema.lower() and "USING ivfflat" not in schema.lower()
    assert "FORCE ROW LEVEL SECURITY" in schema
    assert "current_setting('dks.project_id'" in schema
    assert "session_user" in schema and "project_roles" in schema
    assert "CREATE PROPERTY GRAPH" in schema and "GRAPH_TABLE" in schema
    assert "websearch_to_tsquery('english'" in schema
    assert "to_tsvector('english'" in schema
    assert "<#>" in schema
    assert "schema_migrations" in schema and "VALUES (1)" in schema
    assert "active_embedding_space_id" in schema
    assert "projects_active_revision_fk" in schema and "projects_active_run_fk" in schema
    assert "DROP VIEW IF EXISTS dks.one_hop_graph" in schema
    assert "security_invoker=true" in schema
    assert "SELECT rc.project_id, rc.revision_id, rc.path, r.blob_id" in schema
    assert "SELECT rc.project_id, rc.revision_id, rc.path, c.*" not in schema


def test_dks003_source_profile_is_default_deny_and_byte_exact() -> None:
    dks = load_dksctl()
    profile = json.loads((ROOT / "docs/specs/dbsctr_knowledge_store/DKS-003.source-profile.json").read_text())
    assert dks.accepted_source_path("dot_local/bin/executable_dksctl", profile)
    assert dks.accepted_source_path("tests/test_dbsctrctl.py", profile)
    assert dks.accepted_source_path("run_onchange_after_example.sh.tmpl", profile)
    assert not dks.accepted_source_path("private_dot_config/app/.env", profile)
    assert not dks.accepted_source_path("docs/_archive/old.md", profile)
    assert not dks.accepted_source_path("unknown/new.py", profile)
    assert not dks.accepted_source_path("dot_local/bin/unlisted", profile)
    deployed = json.loads((ROOT / "dot_local/share/dbsctr-knowledge/source-profile.json").read_text())
    assert deployed == profile


def test_dks003_schema_preserves_baseline_and_adds_versioned_quality_projection() -> None:
    schema = (ROOT / "dot_local/share/dbsctr-knowledge/schema.sql").read_text()
    assert "VALUES (1)" in schema and "VALUES (2)" in schema
    assert "authority_snapshots" in schema and "privacy_sequence" in schema
    assert "authority_records" in schema and "authority_chunks" in schema
    assert "vector(4096)" in schema and "vector(3584)" in schema
    assert "graph_imports" in schema and "imported_graph_nodes" in schema
    assert "imported_graph_edges" in schema and "ranking_policies" in schema
    assert "privacy_state" in schema
    policy_tables = schema.split("FOREACH relation_name IN ARRAY ARRAY[", 1)[1].split("] LOOP", 1)[0]
    for table in ("authority_snapshots", "privacy_state", "authority_records", "authority_chunks",
                  "authority_embeddings", "code_embeddings", "graph_imports", "imported_graph_nodes",
                  "imported_graph_edges", "imported_graph_node_chunks", "ranking_policies"):
        assert f"'{table}'" in policy_tables
    assert "ENABLE ROW LEVEL SECURITY" in schema and "FORCE ROW LEVEL SECURITY" in schema


def test_dks_source_v1_chunks_exact_nonoverlapping_lines() -> None:
    dks = load_dksctl()
    source = b"def one():\r\n    return 1\r\n\r\ndef two():\n    return 2\n"
    chunks = dks.chunk_source(source, "example.py", lambda value: len(value.encode()), token_limit=45)
    assert chunks
    assert chunks[0]["start_byte"] == 0
    assert chunks[-1]["end_byte"] == len(source)
    assert all(left["end_byte"] == right["start_byte"] for left, right in zip(chunks, chunks[1:]))
    assert all(chunk["body"].encode() == source[chunk["start_byte"]:chunk["end_byte"]] for chunk in chunks)
    assert chunks == dks.chunk_source(source, "example.py", lambda value: len(value.encode()), token_limit=45)


def test_dks_source_v1_tokenizer_calls_are_bounded() -> None:
    dks = load_dksctl()
    calls = 0

    def count(value: str) -> int:
        nonlocal calls
        calls += 1
        return len(value.encode())

    chunks = dks.chunk_source(b"x\n" * 256, "example.py", count, token_limit=100)
    assert chunks[-1]["end_byte"] == 512
    assert calls < 300


def test_dks_source_v1_resumes_at_oversized_line_end() -> None:
    dks = load_dksctl()
    source = b"a" * 45 + b"\n" + b"b" * 19 + b"\n"
    chunks = dks.chunk_source(source, "example.py", lambda value: len(value.encode()), token_limit=45)
    ends = [chunk["end_byte"] for chunk in chunks]
    assert 46 in ends
    assert not any(46 < end < len(source) for end in ends)


def test_dks_source_v1_prefers_blank_then_declaration_boundaries() -> None:
    dks = load_dksctl()
    count = lambda value: len(value.encode())
    blank = b"a" * 10 + b"\n\n" + b"b" * 10 + b"\n" + b"c" * 10 + b"\n"
    declaration = b"a" * 10 + b"\ndef item():\n" + b"b" * 10 + b"\n"
    assert dks.chunk_source(blank, "x.py", count, 48)[0]["end_byte"] == 12
    assert dks.chunk_source(declaration, "x.py", count, 48)[0]["end_byte"] == 11


def test_graphify_import_requires_exact_source_provenance() -> None:
    dks = load_dksctl()
    data = b"def answer():\n    return 42\n"
    content = hashlib.sha256(data).hexdigest()
    graph = {"nodes": [
        {"id": "answer", "label": "answer", "file_type": "code",
         "source_file": "example.py", "source_location": "L1", "_origin": "ast"},
        {"id": "external", "label": "Path", "source_file": "", "source_location": "",
         "_origin": "ast"},
    ], "edges": [{"source": "answer", "target": "external", "relation": "USES",
                   "confidence": "EXTRACTED", "source_file": "example.py",
                   "source_location": "L1", "_origin": "ast"},
                  {"source": "answer", "target": "missing", "relation": "CALLS",
                   "confidence": "INFERRED", "source_file": "example.py",
                   "source_location": "L1", "_origin": "ast"}], "hyperedges": [], "input_tokens": 0,
              "output_tokens": 0}
    validated = dks.validate_graphify_graph(
        graph, {"example.py": {"path": "example.py", "blob_id": "a" * 40, "data": data}},
        "b" * 40, "0.9.48", "c" * 64)
    assert validated["nodes"][0]["id"] == "answer"
    assert validated["excluded_external_nodes"] == 1 and validated["links"] == []
    assert validated["excluded_dangling_edges"] == 1
    assert validated["artifact_sha256"] == "c" * 64
    graph["nodes"][0]["source_location"] = "L3"
    with pytest.raises(ValueError, match="source location"):
        dks.validate_graphify_graph(
            graph, {"example.py": {"path": "example.py", "blob_id": "a" * 40, "data": data}},
            "b" * 40, "0.9.48", "c" * 64)
    graph["nodes"][0]["source_location"] = None
    with pytest.raises(ValueError, match="source location"):
        dks.validate_graphify_graph(
            graph, {"example.py": {"path": "example.py", "blob_id": "a" * 40, "data": data}},
            "b" * 40, "0.9.48", "c" * 64)


def test_graphify_locations_parse_each_document_once(monkeypatch) -> None:
    dks = load_dksctl()
    calls = 0
    source_lines = dks.source_lines

    def counted(data):
        nonlocal calls
        calls += 1
        return source_lines(data)

    monkeypatch.setattr(dks, "source_lines", counted)
    document = {"path": "example.py", "blob_id": "a" * 40, "data": b"one\ntwo\n"}
    assert dks.graphify_location(document, "L1")["start_byte"] == 0
    assert dks.graphify_location(document, "L2")["start_byte"] == 4
    assert calls == 1


def test_graphify_import_sql_binds_identity_citations_and_completeness() -> None:
    dks = load_dksctl()
    graph = {"artifact_sha256": "a" * 64, "normalized_sha256": "b" * 64,
             "version": "0.9.48", "excluded_external_nodes": 2,
             "excluded_dangling_edges": 3,
              "nodes": [{"id": "one", "label": "one", "confidence": "EXTRACTED",
                         "source_location": {"path": "a.py", "start_byte": 0, "end_byte": 4}},
                        {"id": "two", "label": "two", "confidence": "EXTRACTED",
                         "source_location": {"path": "a.py", "start_byte": 4, "end_byte": 8}}],
              "links": [{"source": "one", "target": "two", "relation": "calls",
                         "confidence": "EXTRACTED",
                         "source_location": {"path": "a.py", "start_byte": 0, "end_byte": 4}},
                        {"source": "one", "target": "two", "relation": "calls",
                         "confidence": "EXTRACTED",
                         "source_location": {"path": "a.py", "start_byte": 4, "end_byte": 8}}]}
    sql = "\n".join(dks.graph_import_statements(
        "dotfiles-ai", "c" * 40, graph, "d" * 64, "e" * 64, "f" * 64))
    assert "b2cd36267456c166788c95be6e68574064a92a42" in sql
    assert "normalized_sha256" in sql and "source_profile_sha256" in sql
    assert "corpus_manifest_sha256" in sql
    assert "execution_receipt_sha256" in sql
    assert "Graphify projection completeness mismatch" in sql
    assert sql.index("projection completeness mismatch") < sql.index("SET state='active'")
    assert sql.index("DELETE FROM dks.imported_graph_edges") < \
        sql.index("DELETE FROM dks.imported_graph_nodes") < sql.index("DELETE FROM dks.graph_imports")
    assert "policy_id='dks-quality-v2'" in sql and "activation_id='dks-rrf-v1'" in sql
    edge_inserts = [item for item in dks.graph_import_statements(
        "dotfiles-ai", "c" * 40, graph, "d" * 64, "e" * 64, "f" * 64)
                    if item.startswith("INSERT INTO dks.imported_graph_edges")]
    assert len(edge_inserts) == 2 and edge_inserts[0] != edge_inserts[1]


def test_graphify_receipt_binds_runtime_corpus_and_artifact(tmp_path: Path) -> None:
    dks = load_dksctl()
    config_sha = dks.digest_json(dks.GRAPHIFY_CONFIG)
    receipt = {"schema_version": 1, "command_contract": "dks-graphify-code-v1",
               "package": "graphifyy[sql]", "extractor_version": "0.9.48",
               "extractor_revision": "b2cd36267456c166788c95be6e68574064a92a42",
               "python_version": "3.13.2", "runtime_sha256": dks.GRAPHIFY_RUNTIME_SHA256,
               "producer_sha256": dks.GRAPHIFY_PRODUCER_SHA256,
               "config_sha256": config_sha, "corpus_manifest_sha256": "b" * 64,
               "artifact_sha256": "c" * 64, "network_disabled": True,
               "raw_extraction_sha256": "d" * 64, "excluded_missing_locations": 2,
               "excluded_missing_location_ids_sha256": "e" * 64}
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt))
    path.chmod(0o600)
    assert dks.load_graphify_receipt(path, "c" * 64, "b" * 64) == \
        hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="identity mismatch"):
        dks.load_graphify_receipt(path, "d" * 64, "b" * 64)
    source = DKSCTL.read_text()
    import_command = source[source.index("def command_import_graph"):source.index("def load_benchmark_aggregate")]
    assert "producer_sha != GRAPHIFY_PRODUCER_SHA256" in import_command
    assert "producer_copy.write_bytes(producer_raw)" in import_command
    assert "subprocess.run([sys.executable, str(producer_copy)" in import_command


def test_knowledge_export_validation_and_authority_sql_are_atomic() -> None:
    dks = load_dksctl()
    text = '{"decision":"keep"}'
    record = {"type": "record", "schema_version": 1, "family": "review",
              "record_id": "a" * 64, "revision": hashlib.sha256(text.encode()).hexdigest(),
              "retention": "retained", "text": text}
    manifest = {"type": "manifest", "schema_version": 1, "privacy_sequence": 2,
                 "privacy_digest": "c" * 64,
                 "families": {name: "available" for name in dks.KNOWLEDGE_FAMILIES},
                 "record_count": 2}
    privacy = {"type": "privacy", "schema_version": 1, "family": "review",
               "record_id": "b" * 64, "reason": "forgotten", "timestamp": 1}
    lines = [dks.canonical_json(manifest), dks.canonical_json(privacy), dks.canonical_json(record)]
    terminal = {"type": "terminal", "schema_version": 1, "record_count": 2,
                "digest": hashlib.sha256("".join(line + "\n" for line in lines).encode()).hexdigest()}
    export = dks.parse_knowledge_export("\n".join([*lines, dks.canonical_json(terminal)]) + "\n")
    chunks = dks.authority_chunks(export["records"], lambda value: len(value.encode()), 1024)
    vectors = {chunk["chunk_id"]: [0.0] * 4095 + [1.0] for chunk in chunks}
    sql = "\n".join(dks.authority_sync_statements("dotfiles-ai", export, chunks, vectors,
                                                    "space", "d" * 64))
    assert sql.startswith("BEGIN;") and sql.rstrip().endswith("COMMIT;")
    assert "authority_snapshots" in sql and "authority_records" in sql
    assert "authority_chunks" in sql and "authority_embeddings" in sql
    assert sql.index("'staging'") < sql.index("SET state='active'")
    privacy_sql = "\n".join(dks.privacy_sync_statements("dotfiles-ai", export))
    assert privacy_sql.startswith("BEGIN;") and privacy_sql.rstrip().endswith("COMMIT;")
    assert "FOR UPDATE" in privacy_sql and "privacy identity rollback" in privacy_sql
    assert "DELETE FROM dks.authority_records" not in sql
    assert "DELETE FROM dks.authority_records" in privacy_sql
    assert "privacy_denies" in privacy_sql and "authority export contains denied identity" in sql
    assert "policy_id='dks-quality-v2'" in sql and "activation_id='dks-rrf-v1'" in sql
    assert "policy_id='dks-quality-v2'" in privacy_sql and "activation_id='dks-rrf-v1'" in privacy_sql
    assert privacy_sql.index("INSERT INTO dks.privacy_denies") < \
        privacy_sql.index("DELETE FROM dks.authority_records")
    assert privacy_sql.index("DELETE FROM dks.authority_records") < privacy_sql.index("COMMIT;")
    bad = dict(terminal, digest="0" * 64)
    with pytest.raises(ValueError, match="digest"):
        dks.parse_knowledge_export("\n".join([*lines, dks.canonical_json(bad)]) + "\n")
    tombstoned = dict(record, retention="tombstoned")
    tombstone_lines = [dks.canonical_json(manifest), dks.canonical_json(privacy),
                       dks.canonical_json(tombstoned)]
    tombstone_terminal = dict(
        terminal, digest=hashlib.sha256("".join(line + "\n" for line in tombstone_lines).encode()).hexdigest())
    with pytest.raises(ValueError, match="record"):
        dks.parse_knowledge_export(
            "\n".join([*tombstone_lines, dks.canonical_json(tombstone_terminal)]) + "\n")


def test_authority_chunk_identity_includes_family_and_record() -> None:
    dks = load_dksctl()
    records = [
        {"family": "review", "record_id": "a" * 64, "text": "identical"},
        {"family": "telemetry", "record_id": "b" * 64, "text": "identical"},
    ]
    chunks = dks.authority_chunks(records, lambda value: len(value.encode()), 1024)
    assert len(chunks) == 2
    assert chunks[0]["chunk_id"] != chunks[1]["chunk_id"]


def test_quality_ranking_pins_exact_and_falls_back_deterministically() -> None:
    dks = load_dksctl()
    channels = {"lexical": ["semantic", "exact"], "vector": ["semantic", "exact"],
                "exact": ["exact"]}
    metadata = {
        "exact": {"path": "docs/specs/example.md", "body": "release v3.27", "chunk_id": "exact"},
        "semantic": {"path": "docs/specs/other.md", "body": "related", "chunk_id": "semantic"},
    }
    baseline = dks.quality_rank(channels, metadata, "find v3.27", None, 10)
    reranked = dks.quality_rank(channels, metadata, "find v3.27", {"semantic": 0.99, "exact": 0.01}, 10)
    assert baseline[0]["id"] == "exact"
    assert reranked[0]["id"] == "exact"
    assert dks.quality_rank(channels, metadata, "ordinary query", None, 10) == \
        dks.quality_rank(channels, metadata, "ordinary query", None, 10)

    crowded = {"lexical": [f"lex-{index}" for index in range(50)],
               "vector": [f"vec-{index}" for index in range(50)], "exact": ["exact"]}
    assert dks.quality_candidates(crowded)[0]["id"] == "exact"


def test_quality_mutation_and_rollback_fail_closed() -> None:
    source = DKSCTL.read_text()
    sync_sql = source[source.index("def sync_statements"):source.index("def authority_sync_statements")]
    sync_code = source[source.index("def command_sync_code"):source.index("def command_sync_evidence")]
    activation = source[source.index("def command_activate_quality"):source.index("def command_benchmark_aggregate")]
    rollback = source[source.index("def command_rollback_quality"):source.index("def command_materialize")]
    assert "stored code embedding identity mismatch" in sync_code
    assert "ranking_fallback_statements(project_id)" in sync_sql
    assert "value_sha256<>" in sync_code and "value<>" in sync_code
    assert rollback.count("pg_try_advisory_lock") == 1
    assert "args.project + \":code\"" in rollback and "args.project + \":authority\"" in rollback
    assert "FOR UPDATE" in rollback and rollback.index("FOR UPDATE") < rollback.index("SET active=false")
    assert "args.project + \":authority\"" in activation and "projection_payload_sql" in activation
    for field in ("source_projection_sha256", "authority_snapshot_set_sha256",
                  "authority_projection_sha256",
                  "privacy_sequence", "privacy_digest"):
        assert field in activation
    assert "aggregate != verified_aggregate" in activation
    assert "validate_benchmark_approval" in activation
    query = source[source.index("def command_query"):source.index("def command_guarded_query")]
    assert query.count("c.body") >= 3
    assert 'rrf({name: channels[name] for name in ("lexical", "vector", "graph")}' in query
    assert 'if policy["policy_id"] == "dks-quality-v2"' in query
    assert 'choices=range(1, 21)' in source
    assert "pg_try_advisory_lock_shared" in query and "REPEATABLE READ READ ONLY" in query
    assert "session.execute(sql)" in query
    projection = source[source.index("def validate_quality_projection"):source.index("def projected_payload")]
    assert "expected_manifest = digest_json" in projection and "policy[\"manifest_sha256\"]" in projection


def test_stored_vector_digest_is_recomputed() -> None:
    dks = load_dksctl()
    vector = [1.0] + [0.0] * 4095
    value = dks.vector_value(vector)
    digest = hashlib.sha256(value.encode()).hexdigest()
    dks.validate_stored_vector(vector, value, digest)
    with pytest.raises(RuntimeError, match="identity"):
        dks.validate_stored_vector(vector, value, "0" * 64)


def test_benchmark_lineage_freezes_source_before_queries_and_judgments(monkeypatch) -> None:
    dks = load_dksctl()
    config = {"quality_benchmark_source_revision": "a" * 40,
              "quality_benchmark_query_approval_commit": "b" * 40,
              "quality_benchmark_judgment_freeze_commit": "c" * 40,
              "quality_benchmark_query_digest": "b" * 64,
              "quality_benchmark_protocol_digest": "f" * 64,
              "quality_benchmark_judgment_digest": "c" * 64}
    manifest = {"source_revision": "a" * 40, "query_approval_commit": "b" * 40,
                "judgment_freeze_commit": "c" * 40, "query_digest": "b" * 64,
                "protocol_digest": "f" * 64, "judgment_digest": "c" * 64}
    query_record = (b'[dotfiles_ai.knowledge_store]\nquality_benchmark_source_revision = "'
                    + b"a" * 40 + b'"\nquality_benchmark_query_digest = "' + b"b" * 64
                    + b'"\nquality_benchmark_protocol_digest = "' + b"f" * 64 + b'"\n')
    freeze_record = (b'[dotfiles_ai.knowledge_store]\nquality_benchmark_source_revision = "'
                     + b"a" * 40 + b'"\nquality_benchmark_query_approval_commit = "'
                     + b"b" * 40 + b'"\nquality_benchmark_query_digest = "' + b"b" * 64
                     + b'"\nquality_benchmark_protocol_digest = "' + b"f" * 64
                     + b'"\nquality_benchmark_judgment_digest = "' + b"c" * 64 + b'"\n')
    monkeypatch.setattr(dks.subprocess, "run", lambda *_args, **_kwargs:
                        subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(dks, "run_git", lambda _repo, _show, revision, **_kwargs:
                        query_record if revision.startswith("b") else freeze_record)
    dks.validate_benchmark_approval(config, {"repository": "/repo"}, manifest)
    manifest["query_digest"] = "e" * 64
    with pytest.raises(RuntimeError, match="lineage"):
        dks.validate_benchmark_approval(config, {"repository": "/repo"}, manifest)
    assert '"GIT_NO_REPLACE_OBJECTS": "1"' in DKSCTL.read_text()


def test_private_query_workbook_initializes_and_validates_without_leaking_text(tmp_path: Path) -> None:
    dks = load_dksctl()
    repository = tmp_path / "repository"
    repository.mkdir()
    private = tmp_path / "state" / "knowledge" / "private"
    private.mkdir(parents=True)
    private.chmod(0o700)
    project = {"repository": str(repository), "knowledge_state_root": str(tmp_path / "state")}
    args = argparse.Namespace(project="dotfiles-ai")

    initialized = dks.command_benchmark_author_init(args, {}, project)
    workbook = private / "benchmarks" / "DKS-005" / "queries.tsv"
    assert initialized["workbook"] == "DKS-005/queries.tsv"
    assert initialized["query_count"] == 100
    assert initialized["strata"] == {name: 20 for name in dks.BENCHMARK_QUERY_STRATA}
    assert workbook.stat().st_mode & 0o777 == 0o600
    assert workbook.parent.stat().st_mode & 0o777 == 0o700
    lines = workbook.read_text().splitlines()
    assert lines[0] == "query_id\tstratum\ttext"
    assert all(line.endswith("\t") for line in lines[1:])
    with pytest.raises(ValueError, match="already exists"):
        dks.command_benchmark_author_init(args, {}, project)

    completed = [lines[0], *(f"{line}human query {index}" for index, line in enumerate(lines[1:], 1))]
    workbook.write_text("\n".join(completed) + "\n")
    workbook.chmod(0o600)
    validated = dks.command_benchmark_author_validate(args, {}, project)
    identity = [line.split("\t", 2) for line in completed[1:]]
    assert validated == {
        "schema_version": 1,
        "project": "dotfiles-ai",
        "benchmark_id": "DKS-005",
        "source_revision": "0975428470e53282545676cbd3bf261a91aecb77",
        "query_count": 100,
        "strata": {name: 20 for name in dks.BENCHMARK_QUERY_STRATA},
        "query_digest": dks.digest_json(identity),
    }
    assert "human query" not in dks.canonical_json(validated)

    workbook.chmod(0o644)
    with pytest.raises(ValueError, match="unsafe benchmark workbook"):
        dks.command_benchmark_author_validate(args, {}, project)


def test_private_query_workbook_rejects_symlinks_and_unsafe_roots(tmp_path: Path) -> None:
    dks = load_dksctl()
    repository = tmp_path / "repository"
    repository.mkdir()
    private = tmp_path / "state" / "knowledge" / "private"
    private.mkdir(parents=True)
    private.chmod(0o700)
    project = {"repository": str(repository), "knowledge_state_root": str(tmp_path / "state")}
    args = argparse.Namespace(project="dotfiles-ai")

    previous_umask = os.umask(0o777)
    try:
        dks.command_benchmark_author_init(args, {}, project)
    finally:
        os.umask(previous_umask)
    benchmark = private / "benchmarks" / "DKS-005"
    workbook = benchmark / "queries.tsv"
    assert benchmark.stat().st_mode & 0o777 == 0o700
    assert workbook.stat().st_mode & 0o777 == 0o600

    workbook.unlink()
    target = private / "target.tsv"
    target.write_text("query_id\tstratum\ttext\n")
    target.chmod(0o600)
    workbook.symlink_to(target)
    with pytest.raises(ValueError, match="unsafe benchmark workbook"):
        dks.command_benchmark_author_validate(args, {}, project)

    benchmark.chmod(0o755)
    with pytest.raises(ValueError, match="private root is unsafe"):
        dks.command_benchmark_author_validate(args, {}, project)
    with pytest.raises(ValueError, match="private root is unsafe"):
        dks.command_benchmark_author_init(
            args, {}, {**project, "repository": str(tmp_path)})

    linked_state = tmp_path / "linked-state"
    linked_state.mkdir()
    (linked_state / "knowledge").symlink_to(tmp_path / "state" / "knowledge")
    with pytest.raises(ValueError, match="private root is unsafe"):
        dks.command_benchmark_author_init(
            args, {}, {**project, "knowledge_state_root": str(linked_state)})


def test_exact_tokens_and_channel_are_strict_and_deterministic() -> None:
    dks = load_dksctl()
    digest = "a" * 64
    query = f"find {digest} in `dot_local/bin/executable_dksctl` at v3.27"
    assert dks.exact_query_tokens(query) == [digest, "dot_local/bin/executable_dksctl", "v3.27"]
    assert dks.exact_query_tokens("`/absolute` `a//b` `a/../b` `a%2Fb` adjacentv3.27x") == []
    metadata = {
        "body-twice": {"body": f"{digest} {digest}"},
        "metadata": {"content_id": digest, "body": ""},
        "other": {"body": "unrelated"},
    }
    assert dks.exact_channel(metadata, digest) == ["metadata", "body-twice"]


def test_benchmark_aggregate_enforces_activation_thresholds(tmp_path: Path) -> None:
    dks = load_dksctl()
    passing = {"eligible": True, "relative_ndcg10": 0.05, "absolute_ndcg10": 0.06,
               "baseline_ndcg10": 0.5, "ci95_lower": 0.001,
               "max_stratum_regression": -0.02, "exact_citation_regressions": 0,
               "recall50_delta": 0.0, "deterministic_rank": True,
               "warm_p95_seconds": 30.0, "peak_memory_gib": 56.0,
               "memory_pressure": "normal", "swap_growth_bytes": 0}
    value = {"schema_version": 2, "manifest_sha256": "a" * 64, "query_count": 100,
             "strata": {f"s{index}": 20 for index in range(5)}, "judgment_depth": 50,
             "duplicate_fraction": 0.2, "quadratic_kappa": 0.7, "matrix_complete": True,
             "candidates": {"code": passing, "reranker": passing}}
    path = tmp_path / "benchmark.json"
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    loaded, digest = dks.load_benchmark_aggregate(path)
    assert loaded == value and digest == hashlib.sha256(path.read_bytes()).hexdigest()
    value["candidates"]["reranker"] = dict(passing, ci95_lower=0.0)
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="eligibility"):
        dks.load_benchmark_aggregate(path)


def test_silver_suite_is_frozen_grounded_and_not_human_evidence(tmp_path: Path, monkeypatch) -> None:
    dks = load_dksctl()
    quote = "The fixed baseline remains active until measured evidence passes."
    suite = {
        "schema_version": 1, "benchmark_id": "DKS-005", "protocol_version": "dks-silver-v1",
        "evidence_class": "silver", "source_revision": dks.DKS_005_SOURCE_REVISION,
        "generated_at": 1,
        "generator": {"provider": "openai", "model": "gpt-5.6-sol",
                      "prompt_sha256": "a" * 64, "evidence_sha256": "b" * 64},
        "reviewers": [
            {"provider": "openai", "model": "gpt-5.6-sol", "prompt_sha256": "c" * 64,
             "evidence_sha256": "d" * 64},
            {"provider": "openai", "model": "gpt-5.6-sol", "prompt_sha256": "e" * 64,
             "evidence_sha256": "f" * 64},
        ],
        "strata": {name: 20 for name in dks.BENCHMARK_QUERY_STRATA},
        "candidate_systems": ["baseline", "code", "reranker", "code_reranker"],
        "depths": [20, 50, 100], "trial_duration_seconds": 604800,
        "questions": [
            {"query_id": f"{stratum}-{index:03d}", "stratum": stratum,
             "text": f"Question {stratum} {index}?",
             "citations": [{"path": "docs/specs/example.md", "quote": quote, "grade": 3}]}
            for stratum in dks.BENCHMARK_QUERY_STRATA for index in range(1, 21)
        ],
    }
    suite["generator"]["evidence_sha256"] = dks.digest_json(suite["questions"])
    path = tmp_path / "silver.json"
    path.write_text(json.dumps(suite))
    monkeypatch.setattr(dks, "git_documents", lambda *_args, **_kwargs: [{
        "path": "docs/specs/example.md", "data": (quote + "\n").encode(), "blob_id": "a" * 40,
    }])
    loaded, digest = dks.load_silver_suite(path, {"repository": str(tmp_path), "remote": "origin"})
    assert loaded == suite
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()

    suite["evidence_class"] = "human"
    path.write_text(json.dumps(suite))
    with pytest.raises(ValueError, match="silver suite"):
        dks.load_silver_suite(path, {"repository": str(tmp_path), "remote": "origin"})


def test_committed_silver_suite_is_grounded_at_the_frozen_revision() -> None:
    dks = load_dksctl()
    profile = ROOT / "dot_local/share/dbsctr-knowledge/source-profile.json"
    project = {"repository": str(ROOT), "remote": "https://github.com/Saltiola7/dotfiles-ai",
               "source_profile_file": str(profile),
               "source_profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest()}
    suite = ROOT / "docs/specs/dbsctr_knowledge_store/benchmarks/DKS-005.silver.json"
    loaded, digest = dks.load_silver_suite(suite, project)
    assert loaded["evidence_class"] == "silver" and len(loaded["questions"]) == 100
    prompt_root = ROOT / "docs/specs/dbsctr_knowledge_store/benchmarks"
    assert loaded["generator"]["prompt_sha256"] == hashlib.sha256(
        (prompt_root / "DKS-005.generator-prompt.txt").read_bytes()).hexdigest()
    assert all(item["prompt_sha256"] == hashlib.sha256(
        (prompt_root / "DKS-005.review-prompt.txt").read_bytes()).hexdigest()
               for item in loaded["reviewers"])
    assert digest == "4478b0c250d5a454ed2ce2c6601d5a9e307cda5b7d957643ddff18d689cfb270"


def test_invalid_silver_trial_atomically_restores_baseline(monkeypatch) -> None:
    dks = load_dksctl()

    class Session:
        statements = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, sql):
            self.statements.append(sql)
            if "pg_try_advisory_lock" in sql:
                return ["t"]
            return []

    session = Session()
    monkeypatch.setattr(dks, "PsqlSession", lambda _config: session)
    monkeypatch.setattr(dks, "active_ranking_policy", lambda *_args, **_kwargs:
                        (_ for _ in ()).throw(RuntimeError("active silver trial expired")))
    result = dks.ensure_quality_policy({}, "dotfiles-ai")
    sql = "\n".join(session.statements)
    assert result == {"ranking_policy": "dks-rrf-v1", "state": "restored"}
    assert "FOR UPDATE" in sql
    assert "activation_id='dks-rrf-v1'" in sql
    assert sql.index("FOR UPDATE") < sql.index("SET active=false") < sql.index("COMMIT")


def test_failed_silver_query_rolls_back_and_retries_once(tmp_path: Path, monkeypatch) -> None:
    dks = load_dksctl()
    args = argparse.Namespace(project="dotfiles-ai", config="/config", text="query",
                              limit=10, commit=None)
    policy = {"policy_id": "dks-quality-v2", "evidence_class": "silver"}
    attempts = iter((subprocess.CompletedProcess([], 1, "", "failed"),
                     subprocess.CompletedProcess([], 0, json.dumps({"ranking_policy": "dks-rrf-v1"}), "")))
    rolled_back = []
    monkeypatch.setattr(dks, "ensure_quality_policy", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dks, "active_ranking_policy", lambda *_args, **_kwargs: policy)
    monkeypatch.setattr(dks, "run_psql", lambda *_args, **_kwargs: [json.dumps({
        "privacy_sequence": "1", "privacy_digest": "a" * 64})])
    monkeypatch.setattr(dks, "command_rollback_quality", lambda *_args, **_kwargs:
                        rolled_back.append(True))
    monkeypatch.setattr(dks.subprocess, "run", lambda *_args, **_kwargs: next(attempts))
    result = dks.command_guarded_query(args, {"dbsctrctl": "/bin/true"},
                                       {"knowledge_state_root": str(tmp_path)})
    assert result["ranking_policy"] == "dks-rrf-v1"
    assert rolled_back == [True]


def test_schema_six_records_trial_class_and_expiry() -> None:
    schema = (ROOT / "dot_local/share/dbsctr-knowledge/schema.sql").read_text()
    migration = (ROOT / "dot_local/bin/executable_dks-postgres-migrate.tmpl").read_text()
    source = DKSCTL.read_text()
    assert "evidence_class" in schema and "trial_expires_at" in schema
    no_force = schema.index("ranking_policies NO FORCE ROW LEVEL SECURITY")
    backfill = schema.index("UPDATE dks.ranking_policies SET evidence_class")
    force = schema.index("ranking_policies FORCE ROW LEVEL SECURITY", backfill)
    assert no_force < backfill < force
    assert "VALUES (6)" in migration and "version=6" in migration
    assert 'commands.add_parser("activate-silver-trial"' in source
    assert "604800" in source and "ensure_quality_policy" in source
    assert "silver trial reranker unavailable" in source


def test_expired_silver_policy_is_never_returned_as_active() -> None:
    dks = load_dksctl()
    policy = {
        "activation_id": "a" * 64, "policy_id": "dks-quality-v2",
        "manifest_sha256": "b" * 64, "benchmark_sha256": "c" * 64,
        "benchmark_aggregate_sha256": "d" * 64, "source_revision_id": "e" * 40,
        "source_projection_sha256": "f" * 64, "authority_snapshot_set_sha256": "1" * 64,
        "authority_projection_sha256": "2" * 64, "privacy_sequence": "3",
        "privacy_digest": "4" * 64, "current_source_revision": "e" * 40,
        "current_privacy_sequence": "3", "current_privacy_digest": "4" * 64,
        "code_embedding_space_id": None, "graph_artifact_sha256": "5" * 64,
        "reranker_manifest_sha256": "6" * 64, "evidence_class": "silver",
        "trial_expires_at": "100", "trial_expired": True,
    }

    class Session:
        def execute(self, _sql):
            return [json.dumps(policy)]

    with pytest.raises(RuntimeError, match="identity"):
        dks.active_ranking_policy({}, "dotfiles-ai", Session())
    policy["trial_expired"] = False
    assert dks.active_ranking_policy({}, "dotfiles-ai", Session())["evidence_class"] == "silver"


def test_silver_evidence_recomputes_metrics_and_binds_resolved_citations(tmp_path: Path,
                                                                        monkeypatch) -> None:
    dks = load_dksctl()
    systems = ("baseline", "code", "reranker", "code_reranker")
    questions, queries, resolved, projected = [], [], {}, {}
    for offset in range(100):
        stratum = dks.BENCHMARK_QUERY_STRATA[offset // 20]
        query_id = f"{stratum}-{offset % 20 + 1:03d}"
        ids = [hashlib.sha256(f"{query_id}-{index}".encode()).hexdigest() for index in range(100)]
        citation = hashlib.sha256(f"citation-{query_id}".encode()).hexdigest()
        baseline = [*ids[1:], ids[0]]
        rankings = {"baseline": baseline, "code": ids, "reranker": baseline,
                    "code_reranker": ids}
        questions.append({"query_id": query_id, "stratum": stratum, "text": f"Question {offset}?",
                          "citations": [{"path": "README.md", "quote": "A sufficiently long quote.",
                                         "grade": 3}]})
        resolved[query_id] = {"judgments": {ids[0]: 3}, "expected_citations": [citation]}
        projected.update({item: citation for item in ids})
        queries.append({"query_id": query_id, "stratum": stratum, **resolved[query_id],
                        "rankings": rankings,
                        "citations": {name: [citation] for name in systems},
                        "runs_seconds": {name: [1.0, 1.0] for name in systems},
                        "repeat_rankings": {name: [ranking, ranking]
                                            for name, ranking in rankings.items()}})
    suite = {"source_revision": dks.DKS_005_SOURCE_REVISION,
             "strata": {name: 20 for name in dks.BENCHMARK_QUERY_STRATA},
             "questions": questions}
    identities = {name: "a" * 64 for name in (
        "source_profile_sha256", "source_projection_sha256", "authority_snapshot_set_sha256",
        "authority_projection_sha256", "privacy_digest", "graph_artifact_sha256",
        "general_embedding_manifest_sha256", "code_embedding_manifest_sha256",
        "reranker_manifest_sha256")}
    identities.update({"source_revision": dks.DKS_005_SOURCE_REVISION, "privacy_sequence": 1})
    resource = {"peak_memory_gib": 10.0, "memory_pressure": "normal", "swap_growth_bytes": 0}
    evidence = {"schema_version": 1, "evidence_class": "silver", "suite_sha256": "b" * 64,
                "execution_depth": 100, "reported_depths": [20, 50, 100],
                "identities": identities, "queries": queries,
                "resources": {"code": resource, "reranker": resource},
                "telemetry_samples": [
                    {"captured_at": 1.0, "memory_gib": 10.0, "memory_pressure": "normal",
                     "swap_used_bytes": 0},
                    {"captured_at": 2.0, "memory_gib": 10.0, "memory_pressure": "normal",
                     "swap_used_bytes": 0},
                ]}
    key = tmp_path / "key"
    key.write_text("f" * 64)
    key.chmod(0o600)
    config = {"embedding": {"api_key_file": str(key)}}
    evidence["receipt_hmac_sha256"] = dks.benchmark_receipt(config, evidence)
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    monkeypatch.setattr(dks, "resolve_silver_citations", lambda *_args, **_kwargs: resolved)
    monkeypatch.setattr(dks, "frozen_chunk_citations", lambda *_args, **_kwargs: projected)
    aggregate = dks.load_silver_evidence(path, suite, "b" * 64, config, "dotfiles-ai")
    assert aggregate["candidates"]["code"]["eligible"] is True
    assert aggregate["candidates"]["reranker"]["eligible"] is False

    valid = json.loads(json.dumps(evidence))
    evidence["receipt_hmac_sha256"] = "0" * 64
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="receipt"):
        dks.load_silver_evidence(path, suite, "b" * 64, config, "dotfiles-ai")

    evidence = json.loads(json.dumps(valid))
    evidence["queries"][0]["rankings"]["code"][0] = "0" * 64
    evidence["queries"][0]["repeat_rankings"]["code"] = [
        evidence["queries"][0]["rankings"]["code"]] * 2
    unsigned = {key: value for key, value in evidence.items() if key != "receipt_hmac_sha256"}
    evidence["receipt_hmac_sha256"] = dks.benchmark_receipt(config, unsigned)
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="query evidence"):
        dks.load_silver_evidence(path, suite, "b" * 64, config, "dotfiles-ai")

    evidence = json.loads(json.dumps(valid))
    evidence["telemetry_samples"][1]["captured_at"] = 20.0
    unsigned = {key: value for key, value in evidence.items() if key != "receipt_hmac_sha256"}
    evidence["receipt_hmac_sha256"] = dks.benchmark_receipt(config, unsigned)
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="telemetry"):
        dks.load_silver_evidence(path, suite, "b" * 64, config, "dotfiles-ai")

    evidence = json.loads(json.dumps(valid))
    evidence["queries"][0]["expected_citations"] = ["0" * 64]
    unsigned = {key: value for key, value in evidence.items() if key != "receipt_hmac_sha256"}
    evidence["receipt_hmac_sha256"] = dks.benchmark_receipt(config, unsigned)
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="query evidence"):
        dks.load_silver_evidence(path, suite, "b" * 64, config, "dotfiles-ai")


def test_silver_runner_uses_git_only_depth_100_cells() -> None:
    source = DKSCTL.read_text()
    query = source[source.index("def command_query_transaction"):source.index("def command_query(")]
    runner = source[source.index("def command_benchmark_silver_run"):source.index("def load_benchmark_aggregate")]
    assert "benchmark_system" in query and "'false' if benchmark" in query
    assert "rank <= {100 if benchmark else 20}" in query
    assert "quality_candidates(channels, max(50, args.limit))" not in query
    assert "quality_candidates(channels)" in query
    assert "600 if benchmark else 30" in query and "8 if benchmark else 50" in query
    assert 'systems = ("baseline", "code", "reranker", "code_reranker")' in runner
    assert "resolve_silver_citations" in runner and "limit=100" in runner
    assert "BenchmarkTelemetry" in runner and "receipt_hmac_sha256" in runner
    assert 'commands.add_parser("benchmark-silver-run"' in source


def test_silver_reranker_batches_offline_candidates(tmp_path: Path, monkeypatch) -> None:
    dks = load_dksctl()
    key = tmp_path / "key"
    key.write_text("a" * 64)
    key.chmod(0o600)
    manifest = {"model": {"revision": "22e683669bc0f0bd69640a1354a6d0aebcfeede5"},
                "contract": {"template_sha256": "b" * 64}, "reranker_id": "test"}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    batches = []

    class Opener:
        def open(self, request, timeout):
            documents = json.loads(request.data)["documents"]
            batches.append((len(documents), timeout))
            return io.BytesIO(json.dumps({
                "model": "reranker", "revision": manifest["model"]["revision"],
                "template_sha256": manifest["contract"]["template_sha256"],
                "truncation": "longest_first", "scores": [0.5] * len(documents),
            }).encode())

    monkeypatch.setattr(dks.urllib.request, "build_opener", lambda *_args: Opener())
    config = {"reranker": {"url": "http://127.0.0.1:11437", "model": "reranker",
                            "api_key_file": str(key), "manifest_file": str(manifest_path),
                            "manifest_sha256": manifest_sha}}
    candidates = [{"chunk_id": f"{offset:064x}", "body": str(offset)}
                  for offset in range(17)]
    scores, _ = dks.rerank(config, "query", candidates, manifest_sha, 600, 8)
    assert batches == [(8, 600), (8, 600), (1, 600)] and len(scores) == 17


def test_benchmark_v2_manifest_binds_complete_protocol(tmp_path: Path) -> None:
    dks = load_dksctl()
    hashes = {name: "a" * 64 for name in (
        "source_profile_sha256", "source_projection_sha256", "authority_snapshot_set_sha256",
        "authority_projection_sha256", "privacy_digest", "graph_artifact_sha256",
        "general_embedding_manifest_sha256", "code_embedding_manifest_sha256",
        "reranker_manifest_sha256", "query_digest", "judgment_digest", "result_digest",
        "seed_sha256")}
    manifest = {"schema_version": 2, "benchmark_id": "DKS-005", "protocol_version": "dks-benchmark-v2",
                "source_revision": "b" * 40, "query_approval_commit": "c" * 40,
                "judgment_freeze_commit": "d" * 40, "privacy_sequence": 0,
                "query_count": 100, "strata": {f"s{i}": 20 for i in range(5)},
                "depths": [20, 50, 100], "hardware": {"sku": "Mac", "os": "26",
                "power": "ac", "thermal": "nominal"}, "authored_at": 1,
                "assessor_protocol_version": "dks-assessor-v2",
                "candidate_systems": ["baseline", "code", "reranker", "code_reranker"],
                "prompts": {name: "e" * 64 for name in ("general", "code", "reranker")},
                "chunkers": ["dks-markdown-v1", "dks-source-v1", "dks-authority-v1"],
                "metrics": ["ndcg10", "recall50", "exact_citation", "latency", "memory"],
                "thresholds": {"relative_ndcg10": 0.05, "absolute_ndcg10_zero_baseline": 0.05,
                "ci95_lower": 0.0, "max_stratum_regression": -0.02,
                "warm_p95_seconds": 30.0, "peak_memory_gib": 56.0},
                "split": {"evaluation": "frozen", "training_queries": 0},
                "activation_order": ["baseline", "code", "reranker"],
                "telemetry_collector_sha256": "f" * 64, **hashes}
    manifest["protocol_digest"] = dks.digest_json(dks.benchmark_protocol_identity(manifest))
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    path.chmod(0o600)
    loaded, _ = dks.load_benchmark_manifest(path)
    assert loaded == manifest
    manifest["candidate_systems"] = ["baseline"]
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest"):
        dks.load_benchmark_manifest(path)


def test_benchmark_metrics_are_recomputed_from_frozen_evidence(tmp_path: Path) -> None:
    dks = load_dksctl()
    systems = ("baseline", "code", "reranker", "code_reranker")
    queries = []
    for index in range(100):
        ids = [f"chunk-{item}" for item in range(100)]
        code = list(ids)
        baseline = [*ids[1:], ids[0]]
        citation = hashlib.sha256(f"citation-{index}".encode()).hexdigest()
        rankings = {"baseline": baseline, "code": code,
                    "reranker": baseline, "code_reranker": code}
        warmups = {name: [1.0, 1.0, 1.0] for name in systems}
        runs = {name: [1.0] * 5 for name in systems}
        depths = {name: {str(depth): ranking[:depth] for depth in (20, 50, 100)}
                  for name, ranking in rankings.items()}
        depth_timings = {name: {str(depth): {
            "warmups": warmups[name] if depth == 100 else [1.0 + depth / 1000] * 3,
            "runs": runs[name] if depth == 100 else [1.0 + depth / 1000] * 5}
            for depth in (20, 50, 100)} for name in systems}
        queries.append({
            "query_id": f"query-{index}", "stratum": f"s{index % 5}", "text": f"query {index}",
            "judgments": {item: 3 if item == ids[0] else 0 for item in ids},
            "rankings": rankings, "expected_citations": [citation],
            "citations": {name: [citation] for name in systems},
            "depth_rankings": depths,
            "depth_timings": depth_timings,
            "execution_receipts": {name: {str(depth): {
                "run_id": f"query-{index}-{name}-{depth}",
                "ranking_sha256": dks.digest_json(depths[name][str(depth)]),
                "timings_sha256": dks.digest_json(depth_timings[name][str(depth)]),
                "telemetry_sha256": "b" * 64} for depth in (20, 50, 100)} for name in systems},
            "warmups_seconds": warmups,
            "runs_seconds": runs,
            "repeat_rankings": {"baseline": [baseline, baseline], "code": [code, code],
                                "reranker": [baseline, baseline], "code_reranker": [code, code]},
        })
    query_identity = [[item["query_id"], item["stratum"], item["text"]] for item in queries]
    duplicate = [{"original_assignment_id": f"original-{index}",
                  "duplicate_assignment_id": f"duplicate-{index}", "pair_id": f"pair-{index}",
                  "assessor_id": "assessor-a", "query_id": f"query-{index}",
                  "item_id": "chunk-0", "randomization_sha256": "f" * 64,
                  "first_grade": 3, "second_grade": 3}
                 for index in range(20)]
    judgment_identity = [[item["query_id"], sorted(item["judgments"].items()),
                          item["expected_citations"]] for item in queries]
    judgment_identity.append(["duplicates", duplicate])
    judgment_identity.append(["adjudications", []])
    resources = {name: {"peak_memory_gib": 10.0, "memory_pressure": "normal",
                        "swap_growth_bytes": 0, "hardware_sku": "Mac", "os_version": "26",
                        "power_state": "ac", "thermal_state": "nominal", "captured_at": 1,
                        "collector_sha256": "a" * 64}
                 for name in ("code", "reranker")}
    telemetry_receipts = {}
    run_manifests = {}
    for name, selected in (("code", {"baseline", "code"}),
                           ("reranker", {"reranker", "code_reranker"})):
        run_ids = sorted(receipt["run_id"] for query in queries
                         for system, receipts in query["execution_receipts"].items()
                         if system in selected for receipt in receipts.values())
        run_manifests[name] = {"collector_sha256": resources[name]["collector_sha256"],
                               "protocol_digest": "e" * 64, "run_ids": run_ids}
        resources[name]["run_manifest_sha256"] = dks.digest_json(run_manifests[name])
        receipt = {"collector_sha256": resources[name]["collector_sha256"],
                   "run_manifest_sha256": resources[name]["run_manifest_sha256"],
                   "run_ids": run_ids,
                   "samples": {key: resources[name][key] for key in (
                       "peak_memory_gib", "memory_pressure", "swap_growth_bytes", "hardware_sku",
                       "os_version", "power_state", "thermal_state", "captured_at")}}
        telemetry_receipts[name] = receipt
        resources[name]["raw_telemetry_sha256"] = dks.digest_json(receipt)
        for query in queries:
            for system in selected:
                for receipt_item in query["execution_receipts"][system].values():
                    receipt_item["telemetry_sha256"] = resources[name]["raw_telemetry_sha256"]
    result_identity = [[item["query_id"], item["rankings"], item["expected_citations"],
                        item["citations"], item["depth_rankings"],
                        item["depth_timings"],
                        item["execution_receipts"],
                        item["warmups_seconds"], item["runs_seconds"], item["repeat_rankings"]]
                       for item in queries]
    result_identity.append(["resources", resources])
    result_identity.append(["telemetry_receipts", telemetry_receipts])
    result_identity.append(["run_manifests", run_manifests])
    manifest = {"query_count": 100, "strata": {f"s{index}": 20 for index in range(5)},
                 "query_digest": dks.digest_json(query_identity),
                 "judgment_digest": dks.digest_json(judgment_identity),
                 "result_digest": dks.digest_json(result_identity), "seed_sha256": "d" * 64,
                 "hardware": {"sku": "Mac", "os": "26", "power": "ac", "thermal": "nominal"},
                 "telemetry_collector_sha256": "a" * 64, "protocol_digest": "e" * 64}
    evidence = {"schema_version": 2, "queries": queries, "duplicate_assessments": duplicate,
                "adjudications": [], "resources": resources,
                "telemetry_receipts": telemetry_receipts, "run_manifests": run_manifests}
    collector = tmp_path / "collector"
    collector.write_text("collector\n")
    collector.chmod(0o600)
    collector_sha = hashlib.sha256(collector.read_bytes()).hexdigest()
    manifest["telemetry_collector_sha256"] = collector_sha
    for name in resources:
        resources[name]["collector_sha256"] = collector_sha
        run_manifests[name]["collector_sha256"] = collector_sha
        resources[name]["run_manifest_sha256"] = dks.digest_json(run_manifests[name])
        telemetry_receipts[name]["collector_sha256"] = collector_sha
        telemetry_receipts[name]["run_manifest_sha256"] = resources[name]["run_manifest_sha256"]
        resources[name]["raw_telemetry_sha256"] = dks.digest_json(telemetry_receipts[name])
        for query in queries:
            for system in ({"baseline", "code"} if name == "code" else {"reranker", "code_reranker"}):
                for receipt in query["execution_receipts"][system].values():
                    receipt["telemetry_sha256"] = resources[name]["raw_telemetry_sha256"]
    result_identity = [[item["query_id"], item["rankings"], item["expected_citations"],
                        item["citations"], item["depth_rankings"], item["depth_timings"],
                        item["execution_receipts"], item["warmups_seconds"], item["runs_seconds"],
                        item["repeat_rankings"]] for item in queries]
    result_identity.extend([["resources", resources], ["telemetry_receipts", telemetry_receipts],
                            ["run_manifests", run_manifests]])
    manifest["result_digest"] = dks.digest_json(result_identity)
    collector_config = {"benchmark_collector_file": str(collector),
                        "benchmark_collector_sha256": collector_sha}
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    path.chmod(0o600)
    aggregate = dks.load_benchmark_evidence(path, manifest, "a" * 64, collector_config)
    assert aggregate["candidates"]["code"]["eligible"] is True
    assert aggregate["candidates"]["reranker"]["eligible"] is False
    assert aggregate["candidates"]["code"]["exact_citation_regressions"] == 0
    evidence["queries"][0]["citations"]["code"] = []
    evidence["queries"][1]["citations"]["baseline"] = []
    result_identity = [[item["query_id"], item["rankings"], item["expected_citations"],
                        item["citations"], item["depth_rankings"],
                        item["depth_timings"],
                        item["execution_receipts"],
                        item["warmups_seconds"], item["runs_seconds"], item["repeat_rankings"]]
                       for item in evidence["queries"]]
    result_identity.append(["resources", resources])
    result_identity.append(["telemetry_receipts", telemetry_receipts])
    result_identity.append(["run_manifests", run_manifests])
    manifest["result_digest"] = dks.digest_json(result_identity)
    path.write_text(json.dumps(evidence))
    citation_regression = dks.load_benchmark_evidence(path, manifest, "a" * 64, collector_config)
    assert citation_regression["candidates"]["code"]["exact_citation_regressions"] == 1
    assert citation_regression["candidates"]["code"]["eligible"] is False
    evidence["queries"][0]["citations"]["code"] = evidence["queries"][0]["expected_citations"]
    evidence["queries"][1]["citations"]["baseline"] = evidence["queries"][1]["expected_citations"]
    evidence["queries"][0]["repeat_rankings"]["code"][0] = baseline
    result_identity = [[item["query_id"], item["rankings"], item["expected_citations"],
                        item["citations"], item["depth_rankings"],
                        item["depth_timings"],
                        item["execution_receipts"],
                        item["warmups_seconds"], item["runs_seconds"], item["repeat_rankings"]]
                       for item in evidence["queries"]]
    result_identity.append(["resources", resources])
    result_identity.append(["telemetry_receipts", telemetry_receipts])
    result_identity.append(["run_manifests", run_manifests])
    manifest["result_digest"] = dks.digest_json(result_identity)
    path.write_text(json.dumps(evidence))
    nondeterministic = dks.load_benchmark_evidence(path, manifest, "a" * 64, collector_config)
    assert nondeterministic["candidates"]["code"]["deterministic_rank"] is False
    assert nondeterministic["candidates"]["code"]["eligible"] is False
    evidence["queries"][0]["text"] = "mutated"
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="manifest identity"):
        dks.load_benchmark_evidence(path, manifest, "a" * 64, collector_config)


def test_dksctl_normalizes_only_supported_repository_remotes() -> None:
    dks = load_dksctl()

    assert dks.normalize_remote("https://GitHub.com/Saltiola7/dotfiles-ai.git") == \
        "https://github.com/Saltiola7/dotfiles-ai"
    assert dks.normalize_remote("git@github.com:Saltiola7/dotfiles-ai.git") == \
        "https://github.com/Saltiola7/dotfiles-ai"
    with pytest.raises(ValueError):
        dks.normalize_remote("file:///tmp/repository")


def test_dksctl_reads_exact_git_blobs_not_dirty_worktree(tmp_path: Path) -> None:
    dks = load_dksctl()
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "remote", "add", "origin", "git@github.com:Saltiola7/dotfiles-ai.git")
    (tmp_path / "docs/specs/example").mkdir(parents=True)
    (tmp_path / "docs/tickets/context=example").mkdir(parents=True)
    (tmp_path / "docs/specs/_archive").mkdir(parents=True)
    (tmp_path / "docs/specs/example/README.md").write_bytes(b"# Spec\n\nBody\n")
    (tmp_path / "docs/tickets/context=example/EX-1.md").write_bytes(b"# Ticket\r\n\r\nWork\r\n")
    (tmp_path / "docs/specs/_archive/old.md").write_text("old\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "fixture")
    commit = git(tmp_path, "rev-parse", "HEAD")

    clean = dks.git_documents(tmp_path, commit, "https://github.com/Saltiola7/dotfiles-ai")
    (tmp_path / "docs/specs/example/README.md").write_text("dirty\n")
    dirty = dks.git_documents(tmp_path, commit, "https://github.com/Saltiola7/dotfiles-ai")

    assert clean == dirty
    assert [item["path"] for item in clean] == [
        "docs/specs/example/README.md",
        "docs/tickets/context=example/EX-1.md",
    ]
    assert clean[0]["data"] == b"# Spec\n\nBody\n"
    source = DKSCTL.read_text()
    assert '"GIT_NO_REPLACE_OBJECTS": "1"' in source
    assert '"ls-tree", "-rz", "--full-tree", "-r"' in source


def test_materialized_corpus_uses_only_exact_selected_blobs(tmp_path: Path) -> None:
    dks = load_dksctl()
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "remote", "add", "origin", "https://github.com/Saltiola7/dotfiles-ai")
    (repo / "src").mkdir()
    (repo / "src/accepted.py").write_text("committed = True\n")
    (repo / "secret.txt").write_text("excluded\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    commit = git(repo, "rev-parse", "HEAD")
    (repo / "src/accepted.py").write_text("dirty = True\n")
    profile_path = tmp_path / "source-profile.json"
    profile = {"schema_version": 1, "profile_id": "dks-source-profile-v1", "roots": ["src"],
               "root_files": [], "root_prefix_suffix": [], "suffixes": [".py"],
               "extensionless_paths": [], "excluded_components": [], "excluded_basenames": [],
               "excluded_suffixes": []}
    raw = canonical = dks.canonical_json(profile).encode()
    profile_path.write_bytes(raw)
    profile_path.chmod(0o600)
    output = tmp_path / "corpus"
    project = {"repository": str(repo), "remote": "https://github.com/Saltiola7/dotfiles-ai",
               "source_profile_file": str(profile_path),
               "source_profile_sha256": hashlib.sha256(raw).hexdigest()}
    result = dks.command_materialize(
        type("Args", (), {"output": str(output), "commit": commit, "project": "dotfiles-ai"})(),
        {}, project)
    assert result["documents"] == 1
    assert (output / "src/accepted.py").read_text() == "committed = True\n"
    assert not (output / "secret.txt").exists()
    assert json.loads((output / "dks-corpus.json").read_text())["commit"] == commit
    assert result["manifest_sha256"] == hashlib.sha256(
        (output / "dks-corpus.json").read_bytes()).hexdigest()


def test_dksctl_rejects_unsupported_git_modes_and_text(tmp_path: Path) -> None:
    dks = load_dksctl()
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "remote", "add", "origin", "https://github.com/Saltiola7/dotfiles-ai")
    (tmp_path / "docs/specs/example").mkdir(parents=True)
    (tmp_path / "docs/specs/example/link.md").symlink_to("target.md")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "symlink")
    with pytest.raises(ValueError, match="mode"):
        dks.git_documents(tmp_path, git(tmp_path, "rev-parse", "HEAD"),
                          "https://github.com/Saltiola7/dotfiles-ai")

    with pytest.raises(ValueError, match="UTF-8|BOM"):
        dks.validate_markdown(b"\xef\xbb\xbf# bad\n")
    with pytest.raises(ValueError, match="UTF-8|BOM"):
        dks.validate_markdown(b"\xff")


def test_dks_markdown_v1_preserves_ranges_fences_and_line_endings() -> None:
    dks = load_dksctl()
    source = (
        b"preamble\r\n\r\n# One\r\n\r\nFirst sentence. Second sentence!\r\n\r\n"
        b"```\r\n# not heading\r\n```\r\n\r\n## Two\r\n\r\nLast\r\n"
    )
    chunks = dks.chunk_markdown(source, lambda value: len(value.encode()), token_limit=64)

    assert chunks
    assert all(chunk["embedding_tokens"] <= 64 for chunk in chunks)
    assert all(source[chunk["start_byte"]:chunk["end_byte"]] == chunk["body_bytes"]
               for chunk in chunks)
    assert all(left["end_byte"] <= right["start_byte"] for left, right in zip(chunks, chunks[1:]))
    assert any("# not heading" in chunk["body"] for chunk in chunks)
    assert chunks[-1]["heading_path"] == ["One", "Two"]
    assert chunks == dks.chunk_markdown(source, lambda value: len(value.encode()), token_limit=64)


def test_dks_markdown_rejects_heading_context_over_budget() -> None:
    dks = load_dksctl()
    with pytest.raises(ValueError, match="heading"):
        dks.chunk_markdown(b"# Very long heading\n\nbody\n", lambda value: len(value), token_limit=8)


def test_dks_graph_identity_link_resolution_and_rrf_are_stable() -> None:
    dks = load_dksctl()
    node = dks.node_id("dotfiles-ai", "path", "docs/specs/a.md")
    edge = dks.edge_id("dotfiles-ai", "a" * 40, "links_to", node, node, 5, 12)
    assert node == dks.node_id("dotfiles-ai", "path", "docs/specs/a.md")
    assert edge == dks.edge_id("dotfiles-ai", "a" * 40, "links_to", node, node, 5, 12)
    assert dks.resolve_project_link("docs/specs/a.md", "../tickets/T-1.md#Outcome") == \
        ("docs/tickets/T-1.md", "Outcome")
    with pytest.raises(ValueError):
        dks.resolve_project_link("docs/specs/a.md", "../../../outside.md")

    ranked = dks.rrf({"lexical": ["b", "a"], "vector": ["a", "c"], "graph": ["c"]}, limit=3)
    assert [item["id"] for item in ranked] == ["a", "c", "b"]
    assert ranked[0]["ranks"] == {"lexical": 2, "vector": 1}

    data = b"---\nid: EX-1\ndepends_on:\n  - EX-0\nowns:\n  - docs/specs/a.md\n---\n# Outcome\n\n[Spec](../../specs/a.md)\n"
    documents = [{"path": "docs/tickets/context=example/EX-1.md", "blob_id": "a" * 40, "data": data},
                 {"path": "docs/specs/a.md", "blob_id": "b" * 40, "data": b"# Spec\n\nBody\n"}]
    chunks = []
    for document in documents:
        for chunk in dks.chunk_markdown(document["data"], lambda value: len(value), 1024):
            chunk.update(path=document["path"], blob_id=document["blob_id"])
            chunks.append(chunk)
    nodes, edges = dks.build_graph("dotfiles-ai", "c" * 40, documents, chunks)
    assert {edge["edge_type"] for edge in edges} >= {"contains", "depends_on", "owns", "links_to"}
    assert {node["kind"] for node in nodes} >= {"chunk", "heading", "path", "ticket"}
    assert all(edge["end_byte"] > edge["start_byte"] for edge in edges
               if edge["edge_type"] in {"depends_on", "owns"})


def test_dks_heading_identity_is_per_occurrence_not_per_chunk() -> None:
    dks = load_dksctl()
    target = b"# Same\n\none two three four five six seven eight nine ten\n"
    source = b"# Link\n\n[target](a.md#Same)\n"
    documents = [{"path": "docs/specs/a.md", "blob_id": "a" * 40, "data": target},
                 {"path": "docs/specs/b.md", "blob_id": "b" * 40, "data": source}]
    chunks = []
    for document in documents:
        for chunk in dks.chunk_markdown(document["data"], lambda value: len(value), 24):
            chunk.update(path=document["path"], blob_id=document["blob_id"])
            chunks.append(chunk)
    nodes, _ = dks.build_graph("dotfiles-ai", "c" * 40, documents, chunks)
    assert len([node for node in nodes if node["kind"] == "heading" and node["path"] == "docs/specs/a.md"]) == 1

    documents[0]["data"] = b"# Same\n\none\n\n# Same\n\ntwo\n"
    chunks = []
    for document in documents:
        for chunk in dks.chunk_markdown(document["data"], lambda value: len(value), 64):
            chunk.update(path=document["path"], blob_id=document["blob_id"])
            chunks.append(chunk)
    with pytest.raises(ValueError, match="not unique"):
        dks.build_graph("dotfiles-ai", "c" * 40, documents, chunks)


def test_dks_embedding_response_indexes_and_reused_vectors_are_validated(monkeypatch) -> None:
    dks = load_dksctl()
    vector = [1.0] + [0.0] * 4095
    monkeypatch.setattr(dks, "api_request", lambda *_: {
        "model": "qwen3-embedding-8b-q4km",
        "data": [{"index": 0, "embedding": vector}, {"index": 0, "embedding": vector}],
    })
    with pytest.raises(RuntimeError, match="indexes"):
        dks.embed({"embedding": {"model": "qwen3-embedding-8b-q4km"}}, ["one", "two"])
    with pytest.raises(RuntimeError, match="normalized"):
        dks.validate_vector([0.0] * 4096)


@pytest.mark.parametrize(("stderr", "message"), [
    ("op-session: Keychain item is missing or inaccessible.", "credential keychain unavailable"),
    ("op-session: Keychain OP_SERVICE_ACCOUNT_TOKEN is invalid", "credential rejected"),
    ("op-session: no valid session", "credential unavailable"),
    ("psql: connection to server failed", "unavailable"),
    ("ERROR: rejected statement containing private-value", "operation failed"),
])
def test_database_failures_expose_only_safe_categories(stderr: str, message: str) -> None:
    dks = load_dksctl()
    error = dks.database_failure(stderr)
    assert str(error) == f"knowledge database {message}"
    assert "private-value" not in str(error)


def test_lifecycle_failure_never_exposes_child_detail(monkeypatch, tmp_path: Path) -> None:
    dks = load_dksctl()
    project = {"knowledge_state_root": str(tmp_path), "repository": str(tmp_path)}
    monkeypatch.setattr(dks.subprocess, "run", lambda *_args, **_kwargs:
                        dks.subprocess.CompletedProcess([], 1, "", "dbsctrctl: store busy\n"))
    with pytest.raises(RuntimeError, match=r"knowledge-export failed$") as error:
        dks.lifecycle_output({"dbsctrctl": "/bin/false"}, project, "knowledge-export")
    assert "store busy" not in str(error.value)
    monkeypatch.setattr(dks.subprocess, "run", lambda *_args, **_kwargs:
                        (_ for _ in ()).throw(OSError("private/path")))
    with pytest.raises(RuntimeError, match=r"knowledge-export unavailable$") as error:
        dks.lifecycle_output({"dbsctrctl": "/bin/false"}, project, "knowledge-export")
    assert "private/path" not in str(error.value)
    with pytest.raises(ValueError, match="repository unavailable"):
        dks.lifecycle_output({"dbsctrctl": "/bin/false"},
                             {**project, "repository": str(tmp_path / "missing")},
                             "knowledge-export")


def test_dks_embedding_manifest_binds_space_model_endpoint_and_hash(tmp_path: Path) -> None:
    dks = load_dksctl()
    raw = render("private_dot_config/dotfiles-ai/knowledge/embedding-space.json.tmpl").encode()
    manifest = tmp_path / "embedding-space.json"
    manifest.write_bytes(raw)
    manifest.chmod(0o600)
    config = {"embedding": {
        "url": "http://127.0.0.1:11435",
        "manifest_file": str(manifest),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "space_id": "qwen3e8b-q4km-llamacpp-b10505-native4096-v1",
        "model": "qwen3-embedding-8b-q4km",
    }}
    dks.validate_embedding_config(config)
    config["embedding"]["manifest_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="identity"):
        dks.validate_embedding_config(config)


def test_dks_sync_locks_before_sources_and_validates_complete_graph_activation() -> None:
    source = DKSCTL.read_text()
    assert '"-qAt"' in source
    assert source.index("pg_try_advisory_lock") < source.index("documents = git_documents", source.index("def command_sync"))
    assert "expected_nodes" in source and "len(nodes)" in source
    assert "expected_edges" in source and "len(edges)" in source
    assert "projection completeness mismatch" in source
    assert "DELETE FROM dks.revision_chunks" in source
    assert "active_embedding_space_id" in source
    assert "DISTINCT ON (c.chunk_id)" in source
    assert "GRAPH_TABLE" in source
    assert "embedding space identity mismatch" in source
    assert "stored embedding identity mismatch" in source
    assert "vector_hashes[row[\"id\"]] = row[\"sha\"]" in source
    assert "build_graph" in source and 'channels["graph"]' in source
    assert "command_rebuild" in source and "rebuild identity mismatch" in source
    assert "{key: sorted(values) for key, values in rebuild_payload.items()}" in source
    command = source.index("def command_sync")
    assert source.index("projected = projected_payload", command) < source.index("sync_statements(", command)


def test_dksctl_cli_rejects_unscoped_or_unbounded_queries(tmp_path: Path) -> None:
    config = tmp_path / "projects.json"
    config.write_text(json.dumps({"projects": {}}))
    missing = subprocess.run(["python3", str(DKSCTL), "query", "--config", str(config),
                              "--text", "query"], text=True, capture_output=True)
    assert missing.returncode == 2
    assert "project" in missing.stderr.lower()
    assert "query" not in missing.stdout


def test_dks002_pgvector_image_and_migration_are_pinned_and_recoverable() -> None:
    containerfile = (ROOT / "dot_local/share/pm-kernel/Containerfile.pgvector").read_text()
    builder = (ROOT / "dot_local/bin/executable_pm-postgres-image-build").read_text()
    container = (ROOT / "private_dot_config/containers/systemd/pm-postgres.container.tmpl").read_text()
    guest_loader = (ROOT / "run_onchange_after_enable-pm-postgres.sh.tmpl").read_text()
    host_loader = (ROOT / "run_onchange_after_configure-pm-postgres.sh.tmpl").read_text()
    migrator = (ROOT / "dot_local/bin/executable_dks-postgres-migrate.tmpl").read_text()
    verifier = (ROOT / "dot_local/bin/executable_pm-postgres-image-verify").read_text()
    baseline = (ROOT / "dot_local/bin/executable_pm-postgres-baseline.tmpl").read_text()

    base_digest = "bfa69ac147240b42c3fc9005d8d173a8b0f07949c7d5c5bbc8985c17b011ec40"
    source_digest = "d076a3098010905fd60256649327809651f6288327db6413f0938305f62ea299"
    assert base_digest in containerfile and base_digest in builder
    assert "8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c" in builder
    assert source_digest in builder
    assert "postgresql-server-dev-19=19~beta3-1.pgdg13+1" in containerfile
    assert "make OPTFLAGS=\"\"" in containerfile
    assert "localhost/dotfiles-ai/postgres-pgvector:19beta3-0.8.6" in container
    assert "pm-postgres-image-build" in guest_loader
    assert "pm-postgres-image-verify" in guest_loader and "ExecStartPre" in container
    assert "image_id" in verifier and "0.8.6" in verifier
    assert "schema_migration" in baseline and "pm_state_preserved" in baseline
    assert host_loader.index("pm-postgres-backup") < host_loader.index('sandbox-vm" update')
    assert host_loader.index('baseline=$("$HOME/.local/bin/pm-postgres-baseline")') < \
        host_loader.index('"$HOME/.local/bin/pm-postgres-backup"')
    assert "existing inactive volume" in host_loader
    assert host_loader.index('sandbox-vm" update') < host_loader.index("dks-postgres-migrate")
    assert "\\getenv dks_password DKS_PASSWORD" in migrator
    assert "CREATE DATABASE dbsctr_knowledge" in migrator
    assert "dks_dotfiles_ai" in migrator
    assert "CREATEDB" in migrator and "CREATEROLE" in migrator
    assert "schema.sql" in migrator and "project_roles" in migrator
    assert "NOLOGIN" in migrator and "pg_terminate_backend" in migrator
    assert "DELETE ON dks.source_records" in migrator
    assert "DELETE ON dks.projects" not in migrator
    assert "SELECT ON PROPERTY GRAPH" in migrator
    assert "SELECT ON dks.schema_migrations" in migrator
    vectors = migrator.index("DO $vectors$")
    version = migrator.index("VALUES (4)")
    commit = migrator.index("COMMIT;", vectors)
    assert vectors < version < commit
    assert "policy_id='dks-quality-v2'" in migrator and "activation_id='dks-rrf-v1'" in migrator
    assert "same-base compatible" in baseline


def test_dks002_config_is_default_off_project_scoped_and_private() -> None:
    defaults = (ROOT / ".chezmoidata.toml").read_text()
    example = (ROOT / "config.example.toml").read_text()
    ignore = (ROOT / ".chezmoiignore").read_text()
    project = (ROOT / "private_dot_config/dotfiles-ai/knowledge/projects.json.tmpl").read_text()
    psql = (ROOT / "dot_local/bin/executable_dks-psql.tmpl").read_text()
    configure = (ROOT / "run_onchange_after_configure-pm-postgres.sh.tmpl").read_text()

    assert "postgres_enabled = false" in defaults
    assert "[dotfiles_ai.knowledge_store.projects]" in defaults
    assert "[data.dotfiles_ai.knowledge_store.projects.dotfiles_ai]" in example
    assert "postgres_password_ref" in example and "remote" in example
    assert "projects.json" in ignore and ".dotfiles_ai.knowledge_store.postgres_enabled" in ignore
    assert "embedding-api-key" in project and "embedding-space.json" in project
    assert '"manifest_file"' in project and '"model"' in project
    assert "postgres_password_ref" not in project
    assert "op read" in psql and "DBSCTR_KNOWLEDGE_PASSWORD" not in psql
    assert "127.0.0.1" in psql and "dbsctr_knowledge" in psql
    assert "/usr/bin/security find-generic-password" in psql
    assert "| /usr/bin/security add-generic-password" in configure
    assert '-w "$dks_password"' not in configure


def test_dks_project_config_renders_runtime_id_and_manifest_hash() -> None:
    values = {
        "chezmoi": {"homeDir": "/Users/test"},
        "dotfiles_ai": {
            "state": {"root": "/Volumes/state"},
            "knowledge_store": {
                "enabled": True, "postgres_enabled": True,
                "embedding_port": 11435, "embedding_dimensions": 4096,
                "embedding_context_tokens": 4096, "model_root": "/models",
                "quality_model_root": "/quality-models",
                "quality_services_enabled": True, "code_embedding_port": 11436,
                "reranker_port": 11437,
                "projects": {"dotfiles_ai": {
                    "repository": "/repo", "remote": "https://github.com/example/repo",
                }},
            },
        },
    }
    command = ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
               "--override-data", json.dumps(values), "execute-template"]
    project = json.loads(subprocess.run(command, input=(ROOT / "private_dot_config/dotfiles-ai/knowledge/projects.json.tmpl").read_text(),
                                        text=True, capture_output=True, check=True).stdout)
    manifest = subprocess.run(command, input=(ROOT / "private_dot_config/dotfiles-ai/knowledge/embedding-space.json.tmpl").read_text(),
                              text=True, capture_output=True, check=True).stdout.encode()
    assert set(project["projects"]) == {"dotfiles-ai"}
    assert project["embedding"]["manifest_sha256"] == hashlib.sha256(manifest).hexdigest()
    assert project["code_embedding"]["space_id"].startswith("nomic-code-")
    assert project["reranker"]["model"] == "qwen3-reranker-4b"


@pytest.mark.parametrize("path", [
    "dot_local/bin/executable_dbsctr-code-embedding.tmpl",
    "run_onchange_after_install-dbsctr-quality-services.sh.tmpl",
    "run_onchange_after_load-dbsctr-code-embedding.sh.tmpl",
    "run_onchange_after_load-dbsctr-reranker.sh.tmpl",
])
def test_quality_service_rendered_shell_is_valid(path: str) -> None:
    subprocess.run(["/bin/bash", "-n"], input=render(path), text=True, check=True)


def test_code_embedding_sync_persists_bounded_batches() -> None:
    source = (ROOT / "dot_local/bin/executable_dksctl").read_text()
    sync_code = source.split("def command_sync_code", 1)[1].split("def lifecycle_output", 1)[0]
    assert 'for offset in range(0, len(rows), 8)' in sync_code
    assert "GROUP BY c.chunk_id,c.body" in sync_code
    assert 'missing = [row for row in batch' in sync_code
    assert 'session.execute("\\n".join(statements))' in sync_code


def test_reconcile_configuration_and_ref_are_bounded(tmp_path: Path) -> None:
    dks = load_dksctl()
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "remote", "add", "origin", "https://github.com/Saltiola7/dotfiles-ai")
    (repo / "README.md").write_text("fixture\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    commit = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/main", commit)
    config = {"reconcile": {"enabled": True, "interval_seconds": 900,
                             "timeout_seconds": 21600}}
    project = {"repository": str(repo), "remote": "https://github.com/Saltiola7/dotfiles-ai",
               "reconcile_ref": "refs/remotes/origin/main", "reconcile_fetch": False}

    settings = dks.reconcile_settings(config, project)
    assert dks.resolve_reconcile_commit(project, settings) == commit
    with pytest.raises(ValueError, match="ref"):
        dks.reconcile_settings(config, {**project, "reconcile_ref": "main"})
    with pytest.raises(ValueError, match="configuration"):
        dks.reconcile_settings({"reconcile": {**config["reconcile"], "interval_seconds": 1}}, project)


def test_reconcile_identity_freshness_and_delivery_contract() -> None:
    dks = load_dksctl()
    digest = "a" * 64
    export = {"manifest": {"privacy_sequence": 2, "privacy_digest": "b" * 64,
                            "families": {family: "available" for family in dks.KNOWLEDGE_FAMILIES}},
              "terminal": {"digest": digest}, "records": []}
    status = {"authority": {"privacy_sequence": "2", "privacy_digest": "b" * 64,
                             "manifests": [digest] * len(dks.KNOWLEDGE_FAMILIES)}}
    assert dks.authority_is_fresh(status, export)
    assert not dks.authority_is_fresh({**status, "authority": {**status["authority"],
                                       "privacy_sequence": "1"}}, export)
    current = {**export, "terminal": {"digest": "c" * 64},
               "records": [{"family": "cycle", "record_id": "new"}]}
    privacy = {"privacy_sequence": 2, "privacy_digest": "b" * 64}
    assert dks.authority_activation_safe(export, current, privacy, privacy)
    assert not dks.authority_activation_safe(
        export, {**current, "manifest": {**current["manifest"], "privacy_sequence": 3}},
        privacy, privacy)
    assert not dks.authority_activation_safe(export, current, privacy,
                                              {**privacy, "privacy_sequence": 3})

    plist = render("private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-knowledge-reconcile.plist.tmpl")
    subprocess.run(["plutil", "-lint", "--", "-"], input=plist, text=True, check=True)
    assert "StartInterval" in plist and "KeepAlive" not in plist
    assert "DOTFILES_AI_DKS_POSTGRES_KEYCHAIN" in plist
    source = DKSCTL.read_text()
    assert 'commands.add_parser("reconcile"' in source
    assert 'commands.add_parser("doctor"' in source
    assert 'LOCK_EX | fcntl.LOCK_NB' in source
    assert '"fetch", "--no-tags"' in source
    assert "authority_embeddings" in source and "DISTINCT ON (chunk_id)" in source
    psql = (ROOT / "dot_local/bin/executable_dks-psql.tmpl").read_text()
    assert "__op_timeout op read" in psql
    assert "dev.dotfiles-ai.dks-postgres" in psql


def test_reconcile_noop_disable_busy_and_failure_are_bounded(tmp_path: Path, monkeypatch) -> None:
    dks = load_dksctl()
    commit = "a" * 40
    space = "general-space"
    code_space = "code-space"
    config = {"reconcile": {"enabled": True, "interval_seconds": 900, "timeout_seconds": 60},
              "embedding": {"space_id": space, "manifest_sha256": "b" * 64},
              "code_embedding": {"space_id": code_space, "manifest_sha256": "c" * 64}}
    project = {"knowledge_state_root": str(tmp_path), "source_profile_sha256": "d" * 64,
               "reconcile_ref": "refs/remotes/origin/main", "reconcile_fetch": False}
    settings = dks.reconcile_settings(config, project)
    export = {"manifest": {"privacy_sequence": 0, "privacy_digest": "e" * 64,
                            "families": {family: "available" for family in dks.KNOWLEDGE_FAMILIES}},
              "terminal": {"digest": "f" * 64}, "records": []}
    status = {"active_revision": commit, "embedding_space": space, "embedding_manifest": "b" * 64,
              "code_chunks": 1, "code_embeddings": 1,
              "code_identity": {"embedding_space": code_space, "manifest_sha256": "c" * 64},
              "graphify": {"revision": commit, "source_profile_sha256": "d" * 64,
              "extractor_version": dks.GRAPHIFY_CONFIG["version"],
              "extractor_revision": dks.GRAPHIFY_EXTRACTOR_REVISION,
              "config_sha256": dks.digest_json(dks.GRAPHIFY_CONFIG)},
              "authority": {"privacy_sequence": "0", "privacy_digest": "e" * 64,
              "manifests": ["f" * 64] * len(dks.KNOWLEDGE_FAMILIES), "embedding_spaces": []}}
    monkeypatch.setattr(dks, "resolve_reconcile_commit", lambda *_args, **_kwargs: commit)
    monkeypatch.setattr(dks, "command_status", lambda *_args, **_kwargs: status)
    monkeypatch.setattr(dks, "lifecycle_output", lambda *_args, **_kwargs: "export")
    monkeypatch.setattr(dks, "parse_knowledge_export", lambda _raw: export)
    monkeypatch.setattr(dks, "git_is_fresh", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(dks, "graph_is_fresh", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(dks, "ensure_quality_policy", lambda *_args, **_kwargs:
                        {"ranking_policy": "dks-rrf-v1", "state": "active"})
    for name in ("command_sync", "command_sync_code", "command_import_graph", "command_sync_evidence"):
        monkeypatch.setattr(dks, name, lambda *_args, _name=name, **_kwargs:
                            pytest.fail(f"unexpected {_name}"))
    args = type("Args", (), {"project": "dotfiles-ai", "force": False})()
    result = dks.command_reconcile(args, config, project)
    assert [stage["state"] for stage in result["stages"]] == ["unchanged"] * 4

    disabled = {**config, "reconcile": {**config["reconcile"], "enabled": False}}
    assert dks.command_reconcile(args, disabled, project)["state"] == "disabled"

    handle = dks.open_reconcile_lock(project)
    dks.fcntl.flock(handle, dks.fcntl.LOCK_EX | dks.fcntl.LOCK_NB)
    try:
        assert dks.command_reconcile(args, config, project)["state"] == "busy"
    finally:
        handle.close()

    stale = {**status, "active_revision": "0" * 40}
    monkeypatch.setattr(dks, "command_status", lambda *_args, **_kwargs: stale)
    monkeypatch.setattr(dks, "git_is_fresh", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(dks, "command_sync", lambda *_args, **_kwargs:
                        (_ for _ in ()).throw(RuntimeError("injected")))
    with pytest.raises(RuntimeError, match="injected"):
        dks.command_reconcile(args, config, project)


def test_reconcile_lock_rejects_fifo(tmp_path: Path) -> None:
    dks = load_dksctl()
    directory = tmp_path / "knowledge/reconcile"
    directory.mkdir(parents=True)
    (directory / "dotfiles-ai.lock").unlink(missing_ok=True)
    import os
    os.mkfifo(directory / "dotfiles-ai.lock", 0o600)
    with pytest.raises(RuntimeError, match="unsafe"):
        dks.open_reconcile_lock({"knowledge_state_root": str(tmp_path)})


def test_git_and_graph_freshness_bind_complete_identities(tmp_path: Path) -> None:
    dks = load_dksctl()
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "remote", "add", "origin", "https://github.com/Saltiola7/dotfiles-ai")
    (repo / "src").mkdir()
    (repo / "src/example.py").write_text("value = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    commit = git(repo, "rev-parse", "HEAD")
    profile = {"schema_version": 1, "profile_id": "dks-source-profile-v1", "roots": ["src"],
               "root_files": [], "root_prefix_suffix": [], "suffixes": [".py"],
               "extensionless_paths": [], "excluded_components": [], "excluded_basenames": [],
               "excluded_suffixes": []}
    profile_path = tmp_path / "profile.json"
    profile_raw = dks.canonical_json(profile).encode()
    profile_path.write_bytes(profile_raw)
    profile_path.chmod(0o600)
    project = {"repository": str(repo), "remote": "https://github.com/Saltiola7/dotfiles-ai",
               "source_profile_file": str(profile_path),
               "source_profile_sha256": hashlib.sha256(profile_raw).hexdigest()}
    config = {"embedding": {"space_id": "space", "manifest_sha256": "a" * 64}}
    records_sha, chunkers = dks.expected_source_identity(project, commit)
    status = {"active_revision": commit, "embedding_space": "space",
              "embedding_manifest": "a" * 64, "source_records_sha256": records_sha,
              "chunkers": chunkers}
    assert dks.git_is_fresh(status, config, project, commit)
    assert not dks.git_is_fresh({**status, "source_records_sha256": "0" * 64}, config, project, commit)

    producer = tmp_path / "producer"
    producer.write_text("producer\n")
    dks.GRAPHIFY_PRODUCER_SHA256 = hashlib.sha256(producer.read_bytes()).hexdigest()
    graph = {"revision": commit, "source_profile_sha256": project["source_profile_sha256"],
             "extractor_version": dks.GRAPHIFY_CONFIG["version"],
             "extractor_revision": dks.GRAPHIFY_EXTRACTOR_REVISION,
             "config_sha256": dks.digest_json(dks.GRAPHIFY_CONFIG),
             "corpus_manifest_sha256": dks.expected_corpus_manifest_sha("dotfiles-ai", project, commit),
             "execution_receipt_sha256": "b" * 64, "runtime_sha256": dks.GRAPHIFY_RUNTIME_SHA256,
             "producer_sha256": dks.GRAPHIFY_PRODUCER_SHA256}
    assert dks.graph_is_fresh({"graphify": graph}, {"graphify_producer": str(producer)},
                              "dotfiles-ai", project, commit)
    assert not dks.graph_is_fresh({"graphify": {**graph, "runtime_sha256": "0" * 64}},
                                  {"graphify_producer": str(producer)}, "dotfiles-ai", project, commit)


def test_canonical_tickets_replace_context_backlogs_in_deployed_skills() -> None:
    discovery = (ROOT / "dot_agents/skills/discovery/SKILL.md").read_text()
    dbsctr = (ROOT / "dot_agents/skills/dbsctr/SKILL.md").read_text()
    assert "Every cycle reviews README, BACKLOG, and CHANGELOG" not in discovery
    assert "Every cycle reviews README, affected canonical tickets, and CHANGELOG" in discovery
    assert "update docs/backlog/changelog" not in dbsctr
    assert not list((ROOT / "docs/specs").glob("*/BACKLOG.md"))
