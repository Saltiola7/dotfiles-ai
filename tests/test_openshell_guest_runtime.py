"""Offline checks for the fixed Fedora musl prerequisite; no native RPM execution."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import ast
import sys

import pytest


@pytest.fixture
def runtime():
    base = Path(__file__).parent / "fixtures/openshell_runtime"
    path = base / "guest_runtime.py"
    assert path.is_file(), "Fixed musl runtime installer not implemented"
    module = ModuleType("guest_runtime_test")
    sys.modules[module.__name__] = module
    exec(compile((base / "guest_build_storage.py").read_text() + "\n" + path.read_text(), str(path), "exec"), module.__dict__)
    module.runtime_source = path.read_text()
    return module


def test_fixed_signed_two_package_set(runtime):
    packages = runtime.runtime_packages
    assert [(p["name"], p["bytes"], p["installed_bytes"]) for p in packages] == [
        ("musl-filesystem", 8360, 0), ("musl-libc", 472552, 945234)]
    assert [p["sha256"] for p in packages] == [
        "018341852575149323787e8ea4ef3f24abfb89940b57ae8c197cb0f5325a7bef",
        "01aeca38d800cf311eba92d7ef95941e21ac2bf938917f25d2aad82e7a82fedf"]
    assert runtime.runtime_fingerprint == "36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6"
    assert sum(p["bytes"] for p in packages) < 1024**2
    assert all(p["url"].startswith("https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/aarch64/os/Packages/m/") for p in packages)


def test_appended_source_has_no_entrypoint_or_future_import(runtime):
    tree = ast.parse(runtime.runtime_source)
    assert not any(isinstance(n, ast.ImportFrom) and n.module == "__future__" for n in tree.body)
    assert not any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) for n in tree.body)
    assert not any(isinstance(n, ast.If) for n in tree.body)
    assert len(runtime.runtime_source.encode()) < 20000
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            assert node.name == "install_runtime" or node.name.startswith("runtime_")


def test_requires_active_verified_mount_before_native_commands(runtime, monkeypatch):
    monkeypatch.setattr(runtime, "_command", lambda *a, **k: pytest.fail("native command before mount"))
    with pytest.raises(runtime.Refusal, match="store_not_mounted"):
        runtime.install_runtime()


def test_identity_exact_version_arch_epoch_and_size(runtime):
    package = runtime.runtime_packages[1]
    good = b"musl-libc\t0\t1.2.5\t6.fc44\taarch64\t945234\n"
    runtime.runtime_identity(good, package)
    for raw in [good.replace(b"6.fc44", b"7.fc44"), good.replace(b"aarch64", b"x86_64"), good + good, good.replace(b"945234", b"945235")]:
        with pytest.raises(runtime.Refusal, match="runtime_package_identity"):
            runtime.runtime_identity(raw, package)


def test_dependency_closure_exact_and_rejects_extra_or_duplicate(runtime):
    for package in runtime.runtime_packages:
        raw = "".join(f"{n}\t{f}\t{v}\n" for n, f, v in package["requires"]).encode()
        runtime.runtime_dependencies(raw, package)
        for bad in [raw + b"bash\t0\t\n", raw + raw, b""]:
            with pytest.raises(runtime.Refusal, match="runtime_dependencies"):
                runtime.runtime_dependencies(bad, package)


def test_file_metadata_exact_and_rejects_owner_path_mode_changes(runtime):
    package = runtime.runtime_packages[1]
    raw = "".join("\t".join(map(str, row)) + "\n" for row in package["files"]).encode()
    runtime.runtime_files(raw, package)
    for bad in [raw.replace(b"/etc/ld-musl", b"/opt/ld-musl"), raw.replace(b"\troot\t", b"\tnobody\t", 1), raw + raw, raw.replace(b"100755", b"104755", 1)]:
        with pytest.raises(runtime.Refusal, match="runtime_files"):
            runtime.runtime_files(bad, package)


@pytest.mark.parametrize("answer", [b"digests OK\n", b"digests signatures NOT OK\n", b"digests signatures OK\nextra\n", b"digests signatures NOKEY\n"])
def test_signature_requires_positive_digest_and_signature(runtime, monkeypatch, answer):
    path = Path("/private/frozen.rpm")
    monkeypatch.setattr(runtime, "runtime_command", lambda argv, **kw: {"stdout": str(path).encode() + b": " + answer, "stderr": b"", "returncode": 0})
    with pytest.raises(runtime.Refusal, match="runtime_signature"):
        runtime.runtime_signature(path)


def test_key_check_never_imports_key(runtime, monkeypatch):
    calls = []
    def command(argv, **kwargs):
        calls.append(argv)
        return {"stdout": b"", "stderr": b"", "returncode": 0}
    monkeypatch.setattr(runtime, "runtime_command", command)
    with pytest.raises(runtime.Refusal, match="runtime_signing_key"):
        runtime.runtime_key()
    assert calls == [["/usr/bin/rpmkeys", "--list", runtime.runtime_fingerprint]]


def test_partial_installed_set_refuses(runtime, monkeypatch):
    def command(argv, **kwargs):
        if argv[-1] == "musl-filesystem":
            return {"returncode": 0, "stdout": b"musl-filesystem\t0\t1.2.5\t6.fc44\taarch64\t0\n", "stderr": b""}
        return {"returncode": 1, "stdout": b"package musl-libc is not installed\n", "stderr": b""}
    monkeypatch.setattr(runtime, "runtime_command", command)
    with pytest.raises(runtime.Refusal, match="runtime_partial_install"):
        runtime.runtime_installed()


def test_database_error_is_not_package_absence(runtime, monkeypatch):
    monkeypatch.setattr(runtime, "runtime_command", lambda *a, **k: {"returncode": 1, "stdout": b"", "stderr": b"database error"})
    with pytest.raises(runtime.Refusal, match="runtime_package_query"):
        runtime.runtime_installed()


def test_download_requires_exact_length_digest_and_no_redirect(runtime, tmp_path, monkeypatch):
    import io
    import hashlib
    package = dict(runtime.runtime_packages[0], bytes=3, sha256=hashlib.sha256(b"abc").hexdigest())
    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Length": "3"}
        def geturl(self):
            return package["url"]
    monkeypatch.setattr(runtime, "runtime_open", lambda *a: Response(b"abc"))
    monkeypatch.setattr(runtime, "_remaining", lambda *a: 10)
    monkeypatch.setattr(runtime, "_work_end", 100.0)
    runtime.runtime_download(package, tmp_path / "good.rpm")
    assert (tmp_path / "good.rpm").read_bytes() == b"abc"
    monkeypatch.setattr(runtime, "runtime_open", lambda *a: Response(b"abcd"))
    with pytest.raises(runtime.Refusal, match="runtime_download"):
        runtime.runtime_download(package, tmp_path / "bad.rpm")
    assert (tmp_path / "bad.rpm.partial").is_file()
    monkeypatch.setattr(Response, "geturl", lambda self: "https://other.example/package")
    with pytest.raises(runtime.Refusal, match="runtime_download"):
        runtime.runtime_download(package, tmp_path / "redirect.rpm")


@pytest.fixture
def admitted(runtime, monkeypatch, tmp_path):
    runtime._active = SimpleNamespace(mount=tmp_path)
    runtime._work_end = 1000.0
    calls = []
    monkeypatch.setattr(runtime, "_remaining", lambda *a: 30)
    monkeypatch.setattr(runtime, "_verify", lambda *a: calls.append("verify"))
    monkeypatch.setattr(runtime, "runtime_key", lambda: calls.append("key"))
    monkeypatch.setattr(runtime, "runtime_system", lambda: calls.append("system"))
    monkeypatch.setattr(runtime, "runtime_cache", lambda: tmp_path)
    monkeypatch.setattr(runtime, "runtime_package", lambda p, d: d / (p["name"] + ".rpm"))
    monkeypatch.setattr(runtime, "runtime_free", lambda: 6 * 1024**3)
    monkeypatch.setattr(runtime, "runtime_installed", lambda: False)
    monkeypatch.setattr(runtime, "runtime_preexisting", lambda: calls.append("no_preexisting_files"))
    monkeypatch.setattr(runtime, "runtime_verify_installed", lambda: calls.append("installed_verified"))
    def command(argv, **kwargs):
        calls.append(argv)
        return {"returncode": 0, "stdout": b"", "stderr": b""}
    monkeypatch.setattr(runtime, "runtime_command", command)
    return runtime, calls


def test_transaction_dry_run_precedes_single_closed_install(admitted):
    runtime, calls = admitted
    result = runtime.install_runtime()
    transactions = [c for c in calls if isinstance(c, list)]
    assert len(transactions) == 2
    assert "--test" in transactions[0] and "--test" not in transactions[1]
    for argv in transactions:
        assert argv[0:2] == ["/usr/bin/rpm", "--install"]
        assert {"--noscripts", "--notriggers"} <= set(argv)
        assert not {"--nodeps", "--force", "--replacefiles", "--nosignature", "--nodigest", "--upgrade"} & set(argv)
    assert calls.index("installed_verified") > calls.index(transactions[1])
    assert calls.index("no_preexisting_files") < calls.index(transactions[0])
    assert result["status"] == "runtime_ready" and result["installed_bytes"] == 945234
    assert result["resumed"] is False


def test_failed_dependency_test_never_installs(admitted, monkeypatch):
    runtime, calls = admitted
    def command(argv, **kwargs):
        calls.append(argv)
        raise runtime.Refusal("native_command_failed")
    monkeypatch.setattr(runtime, "runtime_command", command)
    with pytest.raises(runtime.Refusal, match="native_command_failed"):
        runtime.install_runtime()
    assert len([c for c in calls if isinstance(c, list)]) == 1


def test_exact_installed_resume_verifies_without_transaction(admitted, monkeypatch):
    runtime, calls = admitted
    monkeypatch.setattr(runtime, "runtime_installed", lambda: True)
    result = runtime.install_runtime()
    assert result["resumed"] is True
    assert "installed_verified" in calls
    assert not any(isinstance(c, list) for c in calls)


def test_insufficient_root_reserve_refuses_before_install(admitted, monkeypatch):
    runtime, calls = admitted
    monkeypatch.setattr(runtime, "runtime_free", lambda: 4 * 1024**3)
    with pytest.raises(runtime.Refusal, match="runtime_root_reserve"):
        runtime.install_runtime()
    assert not any(isinstance(c, list) for c in calls)


def test_native_commands_share_work_deadline(runtime, monkeypatch):
    runtime._work_end = 42.0
    calls = []
    monkeypatch.setattr(runtime, "_command", lambda argv, deadline, **kw: calls.append((argv, deadline, kw)) or {"returncode": 0, "stdout": b"", "stderr": b""})
    runtime.runtime_command(["/usr/bin/rpm", "--version"])
    assert calls[0][1] == 42.0 and calls[0][2]["maximum"] <= 60


def test_download_total_deadline_handler_and_timer_collision(runtime, monkeypatch, tmp_path):
    with pytest.raises(runtime.Refusal, match="runtime_download_deadline"):
        runtime.runtime_download_expired(None, None)
    monkeypatch.setattr(runtime.signal, "getitimer", lambda *args: (2.0, 0.0))
    with pytest.raises(runtime.Refusal, match="runtime_download_timer_busy"):
        runtime.runtime_download(runtime.runtime_packages[0], tmp_path / "unwritten")
    assert list(tmp_path.iterdir()) == []


def test_cache_rejects_retained_partial_and_symlink(runtime, monkeypatch, tmp_path):
    runtime._active = SimpleNamespace(mount=tmp_path)
    monkeypatch.setattr(runtime, "_private", lambda *a, **k: None)
    directory = tmp_path / "runtime-rpms"
    directory.mkdir()
    (directory / "failed.rpm.partial").write_bytes(b"partial")
    with pytest.raises(runtime.Refusal, match="runtime_retained_download"):
        runtime.runtime_cache()
    (directory / "failed.rpm.partial").unlink()
    directory.rmdir()
    other = tmp_path / "other"
    other.mkdir()
    directory.symlink_to(other, target_is_directory=True)
    # The actual private identity validator must reject the alias before use.
    monkeypatch.undo()
    runtime._active = SimpleNamespace(mount=tmp_path)
    with pytest.raises(runtime.Refusal, match="resource_identity"):
        runtime.runtime_cache()


def test_unowned_existing_loader_cannot_be_replaced(runtime, tmp_path, monkeypatch):
    path = tmp_path / "loader"
    path.write_bytes(b"unowned")
    monkeypatch.setattr(runtime, "runtime_packages", ({"files": ((str(path), 7, "100755", "root", "root", "", ""),)},))
    with pytest.raises(runtime.Refusal, match="runtime_preexisting_files"):
        runtime.runtime_preexisting()


def test_failed_install_preserves_state_and_never_erases(admitted, monkeypatch):
    runtime, calls = admitted
    def command(argv, **kwargs):
        calls.append(argv)
        if "--test" not in argv:
            raise runtime.Refusal("native_command_failed")
        return {"returncode": 0, "stdout": b"", "stderr": b""}
    monkeypatch.setattr(runtime, "runtime_command", command)
    with pytest.raises(runtime.Refusal, match="native_command_failed"):
        runtime.install_runtime()
    transactions = [c for c in calls if isinstance(c, list)]
    assert len(transactions) == 2
    assert all("--install" in c and "--erase" not in c for c in transactions)
    assert "installed_verified" not in calls
