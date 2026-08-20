import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


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
    assert "openssl rand -hex 32" in source
    assert 'chmod 0600 "$api_key"' in source
    assert "umask 077" in source
    assert "dbsctr-embedding-runtime-verify\" archive" in source
    assert "safe_mkdir" in source
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
