"""Explicit runtime selection and bounded failures, with offline native fixtures."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
WRAPPER = ROOT / "dot_local/bin/executable_managed-dvc"


def load(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(ROOT / "dot_local/bin" / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def provision_native_runtime(home):
    """Test-only import of a separately prepared disposable managed generation."""
    source = os.environ.get("MANAGED_DVC_TEST_HOME")
    if not source:
        pytest.skip("disposable managed DVC runtime not selected")
    source = Path(source) / ".config/dotfiles-ai/runtime/dvc"
    base = home / ".config/dotfiles-ai/runtime/dvc"
    base.mkdir(parents=True, exist_ok=True)
    lock = source / "requirements.txt"
    shutil.copyfile(lock, base / lock.name)
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    source_venv = source / "venvs" / digest
    target = base / "venvs" / digest
    (target / "bin").mkdir(parents=True)
    (target / "bin/python").symlink_to(source_venv / "bin/python")
    shutil.copyfile(source_venv / "pyvenv.cfg", target / "pyvenv.cfg")
    (target / "lib").symlink_to(source_venv / "lib", target_is_directory=True)
    (target / ".managed-lock-sha256").write_text(digest + "\n")


def call(home, *args, env=None, cwd=None, input_text=None):
    return subprocess.run([sys.executable, "-I", str(WRAPPER), *args],
                          env={**os.environ, "HOME": str(home), **(env or {})},
                          cwd=cwd, input=input_text, capture_output=True, text=True, timeout=30)


def test_missing_managed_runtime_never_uses_path_dvc(tmp_path):
    shadow = tmp_path / "bin"
    shadow.mkdir()
    sentinel = tmp_path / "invoked"
    (shadow / "dvc").write_text(f"#!/bin/sh\ntouch '{sentinel}'\n")
    (shadow / "dvc").chmod(0o755)
    result = call(tmp_path, "--version", env={"PATH": str(shadow)})
    assert result.returncode == 78
    assert result.stderr.strip() == "managed-dvc: managed_dvc_runtime_unavailable"
    assert not sentinel.exists()


def test_command_failure_is_not_classified_as_dirty_outputs(tmp_path, monkeypatch):
    module = load("executable_worktree-dvc-setup")
    def unavailable(*_):
        raise ValueError("dvc_command_failed")
    monkeypatch.setattr(module, "run", unavailable)
    with pytest.raises(ValueError, match="^dvc_command_failed$"):
        module.unchanged_outputs(tmp_path)


def test_absent_output_and_absent_cache_are_safe(tmp_path, monkeypatch):
    module = load("executable_worktree-dvc-setup")
    monkeypatch.setattr(module, "run", lambda *_: json.dumps({
        "uncommitted": {"deleted": ["result.txt"]}, "not_in_cache": ["result.txt"]}))
    module.unchanged_outputs(tmp_path)
    assert not (tmp_path / "result.txt").exists()


def test_setup_runtime_failure_is_sanitized(tmp_path, monkeypatch):
    module = load("executable_worktree-dvc-setup")
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a, 78, stdout="", stderr="managed-dvc: managed_dvc_backend_unavailable\nPRIVATE_SENTINEL"))
    with pytest.raises(ValueError) as error:
        module.run(["dvc", "--check-runtime"], tmp_path)
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert "dvc_command_failed" in str(error.value)


def test_backend_failure_precedes_cache_configuration(tmp_path, monkeypatch):
    module = load("executable_worktree-dvc-setup")
    metadata = tmp_path / ".dvc"
    metadata.mkdir()
    local = metadata / "config.local"
    local.write_bytes(b"[cache]\n type = reflink\n")
    def unavailable(argv, _):
        assert argv == ["dvc", "--check-runtime"]
        raise ValueError("managed_dvc_backend_unavailable")
    monkeypatch.setattr(module, "run", unavailable)
    with pytest.raises(ValueError, match="managed_dvc_backend_unavailable"):
        module.configure(tmp_path, tmp_path / "cache")
    assert local.read_bytes() == b"[cache]\n type = reflink\n"
    assert not (tmp_path / "cache").exists()


def test_registration_runs_the_paired_setup_check_with_inspection_env(tmp_path, monkeypatch):
    core = load("executable_dbsctrctl")
    (tmp_path / ".dvc").mkdir()
    monkeypatch.setattr(core, "primary_worktree", lambda _: tmp_path / "other")
    monkeypatch.setattr(core, "git_worktrees", lambda _: [{"worktree": str(tmp_path)}])
    monkeypatch.setattr(core, "branch", lambda _: "task")
    monkeypatch.setattr(core, "status_paths", lambda _: [])
    seen = []
    def run(argv, **kwargs):
        seen.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")
    monkeypatch.setattr(core.subprocess, "run", run)
    from types import SimpleNamespace
    args = SimpleNamespace(base_branch="main")
    with pytest.raises(RuntimeError, match="DVC registration requires"):
        core.require_native_checkout(tmp_path, args)
    assert seen[0][0][-1] == "--check"
    assert seen[0][0][1] == str(ROOT / "dot_local/bin/executable_worktree-dvc-setup")
    assert seen[0][1]["env"] is core.INSPECT_ENV


def test_backend_import_failure_has_only_fixed_diagnostic(tmp_path):
    wrapper = load("executable_managed-dvc")
    code = '''
import builtins, importlib.metadata
importlib.metadata.version = lambda name: {"dvc":"3.67.1", "dvc-data":"3.18.3", "dvc-gs":"3.1.0"}[name]
native = builtins.__import__
def importing(name, *args, **kwargs):
    if name == "dvc_gs":
        raise ImportError("PRIVATE_SENTINEL")
    return native(name, *args, **kwargs)
builtins.__import__ = importing
'''
    result = subprocess.run([sys.executable, "-I", "-c", code + wrapper.QUALIFY_AND_RUN, "--check-runtime"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 78
    assert result.stderr.strip() == "managed-dvc: managed_dvc_backend_unavailable"
    assert not result.stdout


@pytest.mark.parametrize("code,status,args", [
    ("raise ImportError('PRIVATE_SENTINEL')", 1, []),
    ("print('PRIVATE_SENTINEL'); sys.stderr.write('PRIVATE_SENTINEL'); sys.exit(2)", 2, []),
    ("os.write(1, b'PRIVATE_SENTINEL'); os.write(2, b'PRIVATE_SENTINEL'); sys.exit(3)", 3, []),
    ("raise ImportError('PRIVATE_SENTINEL')", 1, ["check-ignore", "--stdin"]),
])
def test_direct_command_failure_never_exposes_child_output(code, status, args):
    driver = f'''
import runpy, sys
wrapper = runpy.run_path({str(WRAPPER)!r})
main = wrapper["main"]
main.__globals__["runtime"] = lambda: sys.executable
main.__globals__["QUALIFY_AND_RUN"] = wrapper["QUALIFY_AND_RUN"].replace(repr(wrapper["DVC_PROGRAM"]), repr("import os, sys; " + {code!r}))
sys.argv = [sys.argv[0], *{args!r}]
sys.exit(main())
'''
    result = subprocess.run([sys.executable, "-I", "-c", driver],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == status
    assert not result.stdout
    assert result.stderr == "managed-dvc: dvc_command_failed\n"


def test_direct_success_preserves_stdout_and_bounds_dependency_stderr():
    code = "import os; os.write(1, b'{}\\n'); os.write(2, b'PRIVATE_SENTINEL')"
    driver = f'''
import runpy, sys
wrapper = runpy.run_path({str(WRAPPER)!r})
main = wrapper["main"]
main.__globals__["runtime"] = lambda: sys.executable
main.__globals__["QUALIFY_AND_RUN"] = wrapper["QUALIFY_AND_RUN"].replace(repr(wrapper["DVC_PROGRAM"]), repr({code!r}))
sys.exit(main())
'''
    result = subprocess.run([sys.executable, "-I", "-c", driver],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert result.stdout == "{}\n"
    assert result.stderr == "managed-dvc: dvc_command_warning\n"


def test_direct_command_keeps_the_wrapper_process_identity():
    driver = f'''
import runpy, sys
wrapper = runpy.run_path({str(WRAPPER)!r})
main = wrapper["main"]
main.__globals__["runtime"] = lambda: sys.executable
main.__globals__["QUALIFY_AND_RUN"] = "import os; print(os.getpid())"
sys.exit(main())
'''
    child = subprocess.Popen([sys.executable, "-I", "-c", driver],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = child.communicate(timeout=10)
    assert child.returncode == 0
    assert int(stdout.strip()) == child.pid
    assert not stderr


def test_removal_uses_managed_entry_with_inspection_environment(tmp_path, monkeypatch):
    core = load("executable_dbsctrctl")
    observed = []
    monkeypatch.setattr(core, "INSPECT_ENV", {"HOME": str(tmp_path), "PATH": "/project/bin"})
    class Child:
        returncode = 0
    def popen(argv, **kwargs):
        observed.append((argv, kwargs["env"]))
        return Child()
    monkeypatch.setattr(core.subprocess, "Popen", popen)
    monkeypatch.setattr(core, "preservation_output", lambda *a, **k: (b"{}", b""))
    assert core.removal_run(tmp_path, ["dvc", "data", "status", "--json"]) == "{}"
    argv, env = observed[0]
    assert argv[:3] == [sys.executable, "-I", str(WRAPPER)]
    assert argv[3:] == ["data", "status", "--json"]
    assert env["DVC_NO_ANALYTICS"] == "1"
    assert env["HOME"] == str(tmp_path)


@pytest.mark.parametrize("status,stderr,expected", [
    (78, b"managed-dvc: managed_dvc_backend_unavailable\n", "managed_dvc_backend_unavailable"),
    (78, b"PRIVATE_SENTINEL", "dvc_command_failed"),
    (78, b"managed-dvc: managed_dvc_backend_unavailable\nPRIVATE_SENTINEL", "dvc_command_failed"),
    (0, b"managed-dvc: dvc_command_warning\n", "dvc_command_failed"),
])
def test_removal_command_failure_is_typed_and_sanitized(tmp_path, monkeypatch, status, stderr, expected):
    core = load("executable_dbsctrctl")
    class Child:
        returncode = status
    monkeypatch.setattr(core.subprocess, "Popen", lambda *a, **k: Child())
    monkeypatch.setattr(core, "preservation_output", lambda *a, **k: (b"", stderr))
    with pytest.raises(core.DVCCommandUnavailable, match=f"^{expected}$"):
        core.removal_run(tmp_path, ["dvc", "data", "status", "--json"])


def test_real_runtime_ignores_shadow_and_python_overrides(tmp_path):
    provision_native_runtime(tmp_path)
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    for name in ("dvc", "dvc_gs", "dvc_data"):
        (shadow / f"{name}.py").write_text("raise RuntimeError('PRIVATE_SENTINEL')\n")
    result = call(tmp_path, "--check-runtime", env={"PYTHONPATH": str(shadow), "PATH": str(shadow)})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"dvc": "3.67.1", "dvc_data": "3.18.3", "dvc_gs": "3.1.0", "backend": "gs"}


def test_native_check_ignore_no_match_preserves_normal_exit(tmp_path):
    provision_native_runtime(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    initialized = call(tmp_path, "init", cwd=repo)
    assert initialized.returncode == 0, initialized.stderr
    result = call(tmp_path, "check-ignore", "--stdin", cwd=repo, input_text="")
    assert result.returncode == 1
    assert not result.stdout
    assert not result.stderr


def test_completed_native_installer_is_idempotent(tmp_path):
    provision_native_runtime(tmp_path)
    wrapper = tmp_path / ".local/bin/managed-dvc"
    wrapper.parent.mkdir(parents=True)
    shutil.copyfile(WRAPPER, wrapper)
    wrapper.chmod(0o755)
    from test_portable_distribution import chezmoi
    rendered = chezmoi("execute-template", template=(ROOT / "run_onchange_after_install-managed-dvc.sh.tmpl").read_text()).stdout
    script = tmp_path / "installer.sh"
    script.write_text(rendered)
    subprocess.run(["bash", "-n", str(script)], check=True)
    base = tmp_path / ".config/dotfiles-ai/runtime/dvc"
    before = {p: p.read_bytes() for p in base.rglob(".managed-lock-sha256")}
    result = subprocess.run(["bash", str(script)], env={**os.environ, "HOME": str(tmp_path), "UV_OFFLINE": "1"},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["backend"] == "gs"
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("problem", ["missing_marker", "wrong_marker", "unsafe_lock", "alias_generation"])
def test_incomplete_or_unsafe_runtime_is_not_executed(tmp_path, problem):
    base = tmp_path / ".config/dotfiles-ai/runtime/dvc"
    base.mkdir(parents=True)
    lock = base / "requirements.txt"
    lock.write_text("synthetic lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    generation = base / "venvs" / digest
    (generation / "bin").mkdir(parents=True)
    (generation / "bin/python").write_text("PRIVATE_SENTINEL")
    if problem != "missing_marker":
        (generation / ".managed-lock-sha256").write_text("wrong" if problem == "wrong_marker" else digest + "\n")
    if problem == "unsafe_lock":
        lock.chmod(0o666)
    if problem == "alias_generation":
        actual = base / "other"
        generation.rename(actual)
        generation.symlink_to(actual, target_is_directory=True)
    result = call(tmp_path, "--check-runtime")
    assert result.returncode == 78
    assert "managed_dvc_runtime_unavailable" in result.stderr
    assert "PRIVATE_SENTINEL" not in result.stderr
