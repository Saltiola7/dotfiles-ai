import hashlib
import io
import importlib.machinery
import importlib.util
import json
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
                "embedding_port": 11435,
                "embedding_dimensions": 4096,
                "embedding_context_tokens": 4096,
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
    assert "build_graph" in source and 'channels["graph"]' in source
    assert "command_rebuild" in source and "rebuild identity mismatch" in source
    assert source.index("projected_identity(") < source.index("sync_statements(", source.index("def command_sync"))


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
    assert "same-base compatible" in baseline


def test_dks002_config_is_default_off_project_scoped_and_private() -> None:
    defaults = (ROOT / ".chezmoidata.toml").read_text()
    example = (ROOT / "config.example.toml").read_text()
    ignore = (ROOT / ".chezmoiignore").read_text()
    project = (ROOT / "private_dot_config/dotfiles-ai/knowledge/projects.json.tmpl").read_text()
    psql = (ROOT / "dot_local/bin/executable_dks-psql.tmpl").read_text()

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


def test_dks_project_config_renders_runtime_id_and_manifest_hash() -> None:
    values = {
        "chezmoi": {"homeDir": "/Users/test"},
        "dotfiles_ai": {
            "state": {"root": "/Volumes/state"},
            "knowledge_store": {
                "enabled": True, "postgres_enabled": True,
                "embedding_port": 11435, "embedding_dimensions": 4096,
                "embedding_context_tokens": 4096, "model_root": "/models",
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


def test_canonical_tickets_replace_context_backlogs_in_deployed_skills() -> None:
    discovery = (ROOT / "dot_agents/skills/discovery/SKILL.md").read_text()
    dbsctr = (ROOT / "dot_agents/skills/dbsctr/SKILL.md").read_text()
    assert "Every cycle reviews README, BACKLOG, and CHANGELOG" not in discovery
    assert "Every cycle reviews README, affected canonical tickets, and CHANGELOG" in discovery
    assert "update docs/backlog/changelog" not in dbsctr
    assert not list((ROOT / "docs/specs").glob("*/BACKLOG.md"))
