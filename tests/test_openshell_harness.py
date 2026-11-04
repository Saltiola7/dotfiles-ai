"""Offline harness identity checks; no Rust compilation or Linux execution."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tomllib


ROOT = Path(__file__).parent / "fixtures/openshell_runtime/harness"
PATCHES = ROOT.parent / "patches"
COMMIT = "5d25211b25a8fc887e8d5c606d57d6ab22f1d76c"
PACKAGE = "dotfiles-ai-openshell-child-seccomp-proof"
VERSION = "0.1.7+dotfiles-ai.child-unix-deny.1"
REGISTRY = "registry+https://github.com/rust-lang/crates.io-index"
CRATES = {
    "bitflags": ("2.13.2", "3ded4057c258ba199e2d26386d3af3780957ecaee6c4ef4041c6b4b8b97c0b06"),
    "errno": ("0.3.14", "39cab71617ae0d63f51a36d69f866391735b51691dbda63cf6f96d042b63efeb"),
    "libc": ("0.2.189", "3eaf3ede3fee6db1a4c2ee091bf8a8b4dccdc6d17f656fb07896ee72867612f2"),
    "linux-raw-sys": ("0.12.1", "32a66949e030da00e8c7d4434b251670a91556f4144941d37452769c25d58a53"),
    "rustix": ("1.1.4", "b6fe4565b9518b83ef4f91bb47ce29620ca828bd32cb7e408f0062e9930ba190"),
    "socket2": ("0.6.3", "3a766e1110788c36f4fa1c2b71b387a7815aa65f88ce0229841826633d93723e"),
    "windows-link": ("0.2.1", "f0805222e57f7521d6a62e36fa9163bc891acd422f971defe97d64e70d0a4fe5"),
    "windows-sys": ("0.61.2", "ae137229bcbd6cdf0f7b80a31df61766145077ddf49416a728b02cb3921ff3fc"),
}
TOOLCHAIN = {
    "cargo": (11170304, "3ea32cd155faeefa3f7689d74a9e515641be5163cba1b331099943b79d8680d9"),
    "rustc": (103731264, "8d05ce001477dec7cfee8e778e15883a9b3a73a061d63e491f08429c3c2a5235"),
    "rust-std": (27119440, "f6710416ed9a7d5cf2a15efa761eb79a1deeb43f9961bbe05cc97bec4ef9064a"),
}


def manifest() -> dict:
    return json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


def test_source_identity_reuses_existing_patch_without_second_module():
    record = manifest()
    patch = json.loads((PATCHES / "source.json").read_text(encoding="utf-8"))
    assert record["schema_version"] == 1
    assert record["identity"] == PACKAGE + "-" + VERSION
    assert record["evidence_scope"] == "source-only; Linux kernel and full runtime unqualified"
    source = record["generated_source"]
    assert source["metadata"] == "../patches/source.json"
    assert source["upstream_commit"] == COMMIT == patch["upstream"]["commit"]
    assert source["preimage"] == "../patches/upstream/child_seccomp.rs"
    assert source["preimage_sha256"] == patch["upstream"]["source"]["sha256"]
    assert source["patch"] == "../patches/child-unix-sockets.patch"
    assert source["patch_sha256"] == patch["patch"]["sha256"]
    assert source["patched_sha256"] == patch["patch"]["patched_sha256"]
    assert source["patch_target"] == patch["patch"]["target"]
    assert source["destination"] == "src/linux/child_seccomp.rs"
    assert source["module"] == "linux::child_seccomp"
    assert source["license"] == "../patches/upstream/LICENSE"
    assert not (ROOT / source["destination"]).exists()


def test_declared_fixture_bytes_are_closed_and_bounded():
    records = manifest()["fixture_files"]
    assert [entry["path"] for entry in records] == ["Cargo.toml", "Cargo.lock", "src/lib.rs"]
    for entry in records:
        path = ROOT / entry["path"]
        assert not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == entry["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    files = sorted(path for path in ROOT.rglob("*") if path.is_file())
    assert [path.relative_to(ROOT).as_posix() for path in files] == [
        "Cargo.lock", "Cargo.toml", "README.md", "manifest.json", "src/lib.rs",
    ]
    assert sum(path.stat().st_size for path in files) < 64 * 1024


def test_manifest_declares_minimal_isolated_harness():
    cargo = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))
    assert cargo["package"] == {
        "name": PACKAGE, "version": VERSION, "edition": "2024",
        "rust-version": "1.95", "license": "Apache-2.0", "publish": False,
    }
    assert cargo["workspace"] == {"resolver": "2"}
    assert cargo["dependencies"] == {
        "libc": "=0.2.189",
        "rustix": {"version": "=1.1.4", "features": ["net"]},
        "socket2": {"version": "=0.6.3", "features": ["all"]},
    }
    assert cargo["lib"] == {"path": "src/lib.rs", "doctest": False}
    assert cargo["profile"]["release"] == {
        "debug": 0, "incremental": False, "lto": False,
    }
    assert set(cargo) == {"package", "workspace", "dependencies", "lib", "profile"}


def test_lock_is_exact_upstream_subset_with_only_documented_edge_changes():
    upstream = manifest()["upstream_lock"]
    assert upstream["commit"] == COMMIT
    assert upstream["git_blob"] == "7f0c1753f1ed4ce8c422004da54a33b9de4ff57f"
    assert upstream["url"] == f"https://github.com/NVIDIA/OpenShell/blob/{COMMIT}/Cargo.lock"
    originals = {entry["name"]: entry for entry in upstream["records"]}
    assert len(upstream["records"]) == len(originals) == len(CRATES)
    assert set(originals) == set(CRATES)
    lock = tomllib.loads((ROOT / "Cargo.lock").read_text(encoding="utf-8"))
    assert lock["version"] == 4
    packages = {entry["name"]: entry for entry in lock["package"]}
    assert len(lock["package"]) == len(packages) == len(CRATES) + 1
    assert packages.pop(PACKAGE) == {
        "name": PACKAGE, "version": VERSION, "dependencies": ["libc", "rustix", "socket2"],
    }
    for name, (version, checksum) in CRATES.items():
        original = originals[name]
        assert (original["version"], original["checksum"]) == (version, checksum)
        assert original["source"] == REGISTRY
        expected = dict(original)
        if name == "bitflags":
            assert expected.pop("dependencies") == ["serde_core"]
        elif "dependencies" in expected:
            expected["dependencies"] = [dependency.split()[0] for dependency in expected["dependencies"]]
        assert packages[name] == expected
        assert all(dependency in CRATES for dependency in expected.get("dependencies", []))
    assert set(packages) == set(CRATES)


def test_toolchain_metadata_pins_only_three_official_musl_host_archives():
    toolchain = manifest()["toolchain"]
    assert toolchain["version"] == "1.95.0"
    assert toolchain["host"] == "aarch64-unknown-linux-musl"
    assert toolchain["source_commit"] == "59807616e1fa2540724bfbac14d7976d7e4a3860"
    assert toolchain["channel_manifest"] == {
        "url": "https://static.rust-lang.org/dist/channel-rust-1.95.0.toml",
        "sha256": "821ff14e4c4a1cbe1e8915f35aff0a3fbbdf8d293ad48ab8f31e3b0440c581f9",
        "size_bytes": 848342, "date": "2026-04-16",
    }
    archives = toolchain["archives"]
    assert len(archives) == len(TOOLCHAIN)
    assert [entry["component"] for entry in archives] == list(TOOLCHAIN)
    for entry in archives:
        component = entry["component"]
        filename = f"{component}-1.95.0-aarch64-unknown-linux-musl.tar.xz"
        assert entry["filename"] == filename
        assert entry["url"] == f"https://static.rust-lang.org/dist/2026-04-16/{filename}"
        assert (entry["size_bytes"], entry["sha256"]) == TOOLCHAIN[component]
    assert sum(entry["size_bytes"] for entry in archives) == 142021008
    assert toolchain["payload_verification"] == "required-before-use; metadata-only here"


def test_build_contract_preserves_host_linking_and_isolated_test_sentinel():
    build = manifest()["build"]
    assert build["host"] == "aarch64-unknown-linux-musl"
    assert build["explicit_target"] is False
    assert build["linker_relative_path"] == "lib/rustlib/aarch64-unknown-linux-musl/bin/rust-lld"
    assert build["rustflags"] == [
        "-C", "linker={toolchain_prefix}/" + build["linker_relative_path"],
        "-C", "linker-flavor=ld.lld", "-C", "link-self-contained=yes",
    ]
    assert build["cargo_test_args"] == [
        "test", "--locked", "--offline", "--release", "--lib", "--", "--test-threads=1", "--nocapture",
    ]
    assert build["required_test"] == (
        "linux::child_seccomp::tests::filter_denies_unix_creation_only_in_workload_children"
    )
    assert build["required_stdout_sentinel"] == "openshell-child-unix-denial-checked"
    wrapper = (ROOT / "src/lib.rs").read_text(encoding="utf-8")
    assert '#[cfg(not(target_os = "linux"))]' in wrapper
    assert 'compile_error!("OpenShell child filter harness requires Linux")' in wrapper
    assert 'pub mod linux {\n    pub mod child_seccomp;\n}' in wrapper
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "not a full OpenShell runtime qualification" in readme
    assert "Cargo --locked validation remains pending" in readme


def test_offline_assembly_produces_exact_patched_module(tmp_path):
    record = manifest()
    source = record["generated_source"]
    original = (ROOT / source["preimage"]).read_bytes()
    patch = (ROOT / source["patch"]).read_bytes()
    assert hashlib.sha256(original).hexdigest() == source["preimage_sha256"]
    assert hashlib.sha256(patch).hexdigest() == source["patch_sha256"]
    preimage = tmp_path / "patch-stage" / source["patch_target"]
    preimage.parent.mkdir(parents=True)
    preimage.write_bytes(original)
    for options in (["--check", "--whitespace=error-all"], ["--whitespace=error-all"]):
        result = subprocess.run(
            ["/usr/bin/git", "apply", *options, "-"], cwd=tmp_path / "patch-stage",
            input=patch, capture_output=True, timeout=10, check=False,
        )
        assert result.returncode == 0, result.stderr.decode()
    patched = preimage.read_bytes()
    assert hashlib.sha256(patched).hexdigest() == source["patched_sha256"]
    assembly = tmp_path / "harness"
    for entry in record["fixture_files"]:
        destination = assembly / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / entry["path"], destination)
    module = assembly / source["destination"]
    module.parent.mkdir(parents=True)
    module.write_bytes(patched)
    assert module.read_bytes() == patched
    assert record["build"]["required_test"].encode() in patched
    assert record["build"]["required_stdout_sentinel"].encode() in patched
    assert patched.startswith(b"// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA")
    assert sorted(path.relative_to(assembly).as_posix() for path in assembly.rglob("*") if path.is_file()) == [
        "Cargo.lock", "Cargo.toml", "src/lib.rs", "src/linux/child_seccomp.rs",
    ]
