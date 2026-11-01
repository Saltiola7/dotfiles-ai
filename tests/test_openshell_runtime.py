"""Admission and owned-process contracts; no VM, provider or runtime is started."""
from __future__ import annotations

import importlib.util
import ast
import builtins
from contextlib import redirect_stdout
import errno
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest


_SPEC = importlib.util.spec_from_file_location(
    "openshell_runtime_probe_under_test", Path(__file__).with_name("probe_openshell_runtime.py")
)
assert _SPEC is not None and _SPEC.loader is not None
probe = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = probe
_SPEC.loader.exec_module(probe)

DIGEST = "ab" * 32
RUN_NAME = "openshell-q-0123456789ab"


def selection_value(root: Path) -> dict:
    return {"schema_version": 1, "run_root": str(root), "lima_sha256": DIGEST}


def selection_bytes(root: Path, **changes) -> bytes:
    return json.dumps(selection_value(root) | changes).encode("utf-8")


def assert_safe_refusal(error: BaseException) -> None:
    # Refusal text is a bounded reason token, not an exception containing the
    # private path, malformed selector or raw child output.
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,63}", str(error))


@pytest.fixture
def owned_root(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / RUN_NAME
    root.mkdir(mode=0o700)
    for relative in ("fixture", "fixture/main", "fixture/task", "evidence", "lima"):
        (root / relative).mkdir(mode=0o700)
    marker = root / "owner.json"
    marker.write_text(json.dumps({"schema_version": 1, "run_id": root.name}), encoding="utf-8")
    marker.chmod(0o600)
    return root


def test_valid_selection_is_pure_and_preserves_exact_identity(tmp_path: Path, monkeypatch):
    root = tmp_path.resolve() / RUN_NAME
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("effect")
        raise AssertionError("selection parsing must not execute or create anything")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(os, "mkdir", forbidden)
    selected = probe.parse_selection(selection_bytes(root))
    assert selected == probe.Selection(root=root, lima_sha256=DIGEST)
    assert calls == []
    assert not root.exists()


@pytest.mark.parametrize("changes", [
    {"schema_version": True},
    {"schema_version": 1.0},
    {"schema_version": 0},
    {"schema_version": 2},
    {"schema_version": None},
    {"run_root": "relative/" + RUN_NAME},
    {"run_root": "/private/tmp/other/../" + RUN_NAME},
    {"run_root": "/private/tmp/./" + RUN_NAME},
    {"run_root": "/private/tmp//" + RUN_NAME},
    {"run_root": "/private/tmp/" + RUN_NAME + "/"},
    {"run_root": "/private/tmp/openshell-q-0123456789AB"},
    {"run_root": "/private/tmp/not-a-qualified-run"},
    {"run_root": "/private/tmp/" + RUN_NAME + "\x00private-marker"},
    {"run_root": None},
    {"run_root": ["/private/tmp/" + RUN_NAME]},
    {"lima_sha256": "AB" * 32},
    {"lima_sha256": "a" * 63},
    {"lima_sha256": "z" * 64},
    {"lima_sha256": 1},
    {"lima_sha256": None},
    {"command": "private-marker; unexpected-host-command"},
])
def test_invalid_selection_refuses_before_effects(tmp_path: Path, monkeypatch, changes):
    root = tmp_path.resolve() / RUN_NAME
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("effect")
        raise AssertionError("invalid selection reached an effect")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(os, "mkdir", forbidden)
    with pytest.raises(probe.Refusal) as caught:
        probe.parse_selection(selection_bytes(root, **changes))
    assert_safe_refusal(caught.value)
    assert calls == []
    assert not root.exists()


@pytest.mark.parametrize("raw", [
    b"[]", b"null", b"true", b"{}", b"{", b"\xffprivate-marker",
    b'{"schema_version":1,"schema_version":1}',
])
def test_malformed_or_incomplete_selection_is_sanitized(raw: bytes):
    with pytest.raises(probe.Refusal) as caught:
        probe.parse_selection(raw)
    assert_safe_refusal(caught.value)


@pytest.mark.parametrize("duplicate", ["schema_version", "run_root", "lima_sha256"])
def test_duplicate_fields_are_rejected_even_when_values_match(tmp_path: Path, duplicate):
    value = selection_value(tmp_path.resolve() / RUN_NAME)
    raw = json.dumps(value)[:-1] + "," + json.dumps(duplicate) + ":" + json.dumps(value[duplicate]) + "}"
    with pytest.raises(probe.Refusal) as caught:
        probe.parse_selection(raw.encode("utf-8"))
    assert_safe_refusal(caught.value)


def test_selection_byte_limit_has_exact_boundary(tmp_path: Path):
    root = tmp_path.resolve() / RUN_NAME
    raw = selection_bytes(root).ljust(64 * 1024, b" ")
    assert probe.parse_selection(raw).root == root
    with pytest.raises(probe.Refusal) as caught:
        probe.parse_selection(raw + b" ")
    assert_safe_refusal(caught.value)


def test_owner_controlled_layout_is_admitted_without_modification(owned_root: Path):
    sentinel = owned_root / "evidence" / "retained"
    sentinel.write_bytes(b"private retained observation")
    before = {str(p.relative_to(owned_root)): (p.stat().st_ino, p.stat().st_mode)
              for p in owned_root.rglob("*")}
    probe.validate_root(probe.Selection(owned_root, DIGEST))
    after = {str(p.relative_to(owned_root)): (p.stat().st_ino, p.stat().st_mode)
             for p in owned_root.rglob("*")}
    assert before == after
    assert sentinel.read_bytes() == b"private retained observation"


@pytest.mark.parametrize("relative", ["", "fixture", "fixture/main", "fixture/task", "evidence", "lima"])
def test_nonprivate_layout_is_refused_and_retained(owned_root: Path, relative):
    target = owned_root / relative
    target.chmod(0o755)
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(probe.Selection(owned_root, DIGEST))
    assert_safe_refusal(caught.value)
    assert target.is_dir()
    assert target.stat().st_mode & 0o777 == 0o755


@pytest.mark.parametrize("relative", ["fixture/main", "fixture/task", "evidence", "lima"])
def test_missing_layout_is_not_implicitly_created(owned_root: Path, relative):
    target = owned_root / relative
    target.rmdir()
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(probe.Selection(owned_root, DIGEST))
    assert_safe_refusal(caught.value)
    assert not target.exists()


@pytest.mark.parametrize("relative", ["fixture/main", "fixture/task", "evidence", "lima"])
def test_symlinked_layout_cannot_redirect_scope(owned_root: Path, tmp_path: Path, relative):
    outside = tmp_path.resolve() / "outside"
    outside.mkdir(mode=0o700)
    sentinel = outside / "keep"
    sentinel.write_bytes(b"unchanged")
    target = owned_root / relative
    target.rmdir()
    target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(probe.Selection(owned_root, DIGEST))
    assert_safe_refusal(caught.value)
    assert sentinel.read_bytes() == b"unchanged"
    assert target.is_symlink()


def test_symlinked_parent_is_refused(owned_root: Path, tmp_path: Path):
    parent_alias = tmp_path.resolve() / "parent-alias"
    parent_alias.symlink_to(owned_root.parent, target_is_directory=True)
    selected = probe.Selection(parent_alias / owned_root.name, DIGEST)
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(selected)
    assert_safe_refusal(caught.value)
    assert owned_root.is_dir()


def test_wrong_owner_is_refused(owned_root: Path, monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: owned_root.stat().st_uid + 1)
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(probe.Selection(owned_root, DIGEST))
    assert_safe_refusal(caught.value)


@pytest.mark.parametrize("marker_value", [
    {"schema_version": True, "run_id": RUN_NAME},
    {"schema_version": 2, "run_id": RUN_NAME},
    {"schema_version": 1, "run_id": "openshell-q-ffffffffffff"},
    {"schema_version": 1, "run_id": RUN_NAME, "adopt": True},
    {},
])
def test_mismatched_owner_marker_is_not_adopted(owned_root: Path, marker_value):
    marker = owned_root / "owner.json"
    marker.write_text(json.dumps(marker_value), encoding="utf-8")
    before = marker.read_bytes()
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(probe.Selection(owned_root, DIGEST))
    assert_safe_refusal(caught.value)
    assert marker.read_bytes() == before


def test_missing_owner_marker_is_not_created(owned_root: Path):
    marker = owned_root / "owner.json"
    marker.unlink()
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(probe.Selection(owned_root, DIGEST))
    assert_safe_refusal(caught.value)
    assert not marker.exists()


def test_owner_marker_alias_is_refused(owned_root: Path):
    marker = owned_root / "owner.json"
    retained = owned_root / "retained-owner.json"
    marker.rename(retained)
    marker.symlink_to(retained)
    with pytest.raises(probe.Refusal) as caught:
        probe.validate_root(probe.Selection(owned_root, DIGEST))
    assert_safe_refusal(caught.value)
    assert retained.is_file() and marker.is_symlink()


def test_command_preserves_exit_status_streams_and_argument_boundaries(tmp_path: Path):
    argument = "literal; $(unexpected-host-command) * ' \""
    script = "import sys; print(sys.argv[1]); print('diagnostic', file=sys.stderr); sys.exit(17)"
    result = probe.run_command([sys.executable, "-I", "-c", script, argument],
                               cwd=tmp_path, env={"PATH": "/usr/bin:/bin"})
    assert result.returncode == 17
    assert result.stdout == (argument + "\n").encode()
    assert result.stderr == b"diagnostic\n"


def test_command_uses_explicit_environment_only(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-parent-secret")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/private/unrelated-agent")
    script = "import json,os; print(json.dumps({k:os.environ.get(k) for k in ('OPENAI_API_KEY','SSH_AUTH_SOCK','QUALIFICATION_MARKER')}))"
    result = probe.run_command([sys.executable, "-I", "-c", script], cwd=tmp_path,
                               env={"PATH": "/usr/bin:/bin", "QUALIFICATION_MARKER": "synthetic"})
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "OPENAI_API_KEY": None, "SSH_AUTH_SOCK": None, "QUALIFICATION_MARKER": "synthetic"}


def test_command_limit_counts_both_streams_and_accepts_boundary(tmp_path: Path):
    script = "import os; os.write(1,b'a'*512); os.write(2,b'b'*512)"
    result = probe.run_command([sys.executable, "-I", "-c", script],
                               cwd=tmp_path, env={}, limit=1024)
    assert result.returncode == 0
    assert result.stdout == b"a" * 512 and result.stderr == b"b" * 512


@pytest.mark.parametrize("script", [
    "import os; os.write(1,b'x'*65536)",
    "import os; os.write(2,b'x'*65536)",
    "import os; os.write(1,b'x'*768); os.write(2,b'y'*768)",
])
def test_output_exhaustion_is_bounded_and_sanitized(tmp_path: Path, script):
    started = time.monotonic()
    with pytest.raises(probe.Refusal, match="^output_limit$"):
        probe.run_command([sys.executable, "-I", "-c", script],
                          cwd=tmp_path, env={}, timeout=2, limit=1024)
    assert time.monotonic() - started < 5


@pytest.mark.parametrize("parent_exits", [False, True])
def test_timeout_stops_owned_descendants_even_after_parent_exit(tmp_path: Path, parent_exits):
    marker = tmp_path / "descendant-survived"
    child = f"import time; from pathlib import Path; time.sleep(1.0); Path({str(marker)!r}).touch()"
    script = ("import subprocess,sys,time; "
              f"subprocess.Popen([sys.executable,'-I','-c',{child!r}]); "
              + ("sys.exit(0)" if parent_exits else "time.sleep(10)"))
    started = time.monotonic()
    with pytest.raises(probe.Refusal, match="^timeout$"):
        probe.run_command([sys.executable, "-I", "-c", script],
                          cwd=tmp_path, env={}, timeout=0.3)
    assert time.monotonic() - started < 5
    time.sleep(1.2)
    assert not marker.exists()


@pytest.fixture
def pointer_fixture(owned_root: Path) -> tuple[Path, dict[str, str]]:
    """Native Git structure for local decisions, not Worktrunk/runtime proof."""
    controller = owned_root / "controller"
    controller.mkdir(mode=0o700)
    for name in ("config", "data", "state", "cache", "tmp"):
        (controller / name).mkdir(mode=0o700)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(controller),
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"}
    main, task = owned_root / "fixture/main", owned_root / "fixture/task"
    commands = (
        ["/usr/bin/git", "init", "--quiet", "--initial-branch=main", str(main)],
        ["/usr/bin/git", "-C", str(main), "-c", "user.name=Fixture",
         "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
         "commit", "--quiet", "--allow-empty", "-m", "Synthetic fixture"],
        ["/usr/bin/git", "-C", str(main), "worktree", "add", "--quiet", "--detach", str(task), "HEAD"],
    )
    for argv in commands:
        subprocess.run(argv, env=env, cwd=owned_root, check=True, capture_output=True, timeout=10)
    return owned_root, env


class PointerTransport:
    """Mock only guest transport; host identity/evidence checks remain real."""

    def __init__(self, root: Path, env: dict[str, str]):
        self.root = root
        self.env = env
        self.executions: list[tuple[str, str]] = []
        self.identity_calls = 0
        self.action = None
        self.identity_change_after_execution = None

    def identity(self, deadline: float) -> tuple:
        assert 0 < deadline - time.monotonic() <= 60
        self.identity_calls += 1
        if (self.identity_change_after_execution is not None
                and len(self.executions) >= self.identity_change_after_execution):
            return ("replacement-generation",)
        return ("same-qualified-generation",)

    def execute(self, program: str, deadline: float) -> dict:
        assert 0 < deadline - time.monotonic() <= 60
        # Parse constant enum input; never execute the guest program locally.
        assignment = next((node for node in ast.parse(program).body
                           if isinstance(node, ast.Assign)
                           and isinstance(node.targets[0], ast.Tuple)), None)
        if assignment is None:
            self.executions.append(("positive", ""))
            (self.root / "fixture/task" / probe._POSITIVE_NAME).write_bytes(probe._POSITIVE_BYTES)
            return {"schema_version": 1, "positive": "written"}
        operation, spelling = ast.literal_eval(assignment.value)
        self.executions.append((operation, spelling))
        result = {"schema_version": 1, "operation": operation, "spelling": spelling,
                  "outcome": "denied", "errno": 13}
        if self.action is not None:
            return self.action(operation, spelling, result)
        return result


def install_transport(monkeypatch, pointer_fixture) -> PointerTransport:
    root, env = pointer_fixture
    transport = PointerTransport(root, env)
    monkeypatch.setattr(probe, "_PointerController", lambda selection, deadline: transport)
    return transport


def test_pointer_success_cannot_claim_full_runtime_qualification(pointer_fixture, monkeypatch):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "passed" and result["reason"] is None
    assert result["runtime_qualification"] == "not_run"
    assert result["retained"] is True
    assert transport.executions[0] == ("positive", "")
    assert {op for op, spelling in transport.executions if spelling == ".git"} == {
        "write_open", "append", "truncate", "unlink", "rename", "replace", "hardlink"}
    evidence = list((root / "evidence").glob("pointer-*.json"))
    assert evidence
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in evidence)
    assert any(json.loads(path.read_text()) == result for path in evidence)
    assert str(root) not in json.dumps(result)


def test_pointer_write_permission_failure_stops_before_next_attempt(pointer_fixture, monkeypatch):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    pointer = root / "fixture/task/.git"
    before = pointer.read_bytes()
    transport.action = lambda operation, spelling, result: result | {"outcome": "succeeded", "errno": 0}
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "pointer_operation_allowed"
    assert result["retained"] is True and result["runtime_qualification"] == "not_run"
    assert transport.executions == [("positive", ""), ("write_open", ".git")]
    assert pointer.read_bytes() == before


@pytest.mark.parametrize("mutation", ["truncate", "unlink", "hardlink", "metadata"])
def test_host_observation_overrides_false_denial_and_retains_failed_fixture(
        pointer_fixture, monkeypatch, mutation):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    pointer = root / "fixture/task/.git"

    def violate(operation, spelling, result):
        if mutation == "truncate":
            pointer.write_bytes(b"private-untrusted-marker")
        elif mutation == "unlink":
            pointer.unlink()
        elif mutation == "hardlink":
            os.link(pointer, root / "fixture/task/retained-hardlink")
        else:
            (root / "fixture/main/.git/config").write_bytes(b"private-untrusted-marker")
        return result  # The workload claims denial despite the observed change.

    transport.action = violate
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert result["retained"] is True
    assert transport.executions == [("positive", ""), ("write_open", ".git")]
    assert "private-untrusted-marker" not in json.dumps(result)
    if mutation == "truncate":
        assert pointer.read_bytes() == b"private-untrusted-marker"
    elif mutation == "unlink":
        assert not pointer.exists()
    elif mutation == "hardlink":
        assert pointer.stat().st_nlink == 2
    else:
        assert (root / "fixture/main/.git/config").read_bytes() == b"private-untrusted-marker"


def test_changed_generation_cannot_pass_or_run_another_attempt(pointer_fixture, monkeypatch):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    transport.identity_change_after_execution = 2
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "sandbox_identity"
    assert result["runtime_qualification"] == "not_run" and result["retained"] is True
    assert transport.executions == [("positive", ""), ("write_open", ".git")]


@pytest.mark.parametrize("override", [
    {"schema_version": True},
    {"operation": "unrelated"},
    {"spelling": "unrelated"},
    {"outcome": "denied", "errno": 0},
    {"outcome": "denied", "errno": 2},
    {"outcome": "succeeded", "errno": 13},
    {"errno": True},
    {"unexpected": "private-untrusted-marker"},
])
def test_malformed_probe_output_cannot_authorize_a_pass(pointer_fixture, monkeypatch, override):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    transport.action = lambda operation, spelling, result: result | override
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "invalid_probe_output"
    assert result["retained"] is True and result["runtime_qualification"] == "not_run"
    assert transport.executions == [("positive", ""), ("write_open", ".git")]
    assert "private-untrusted-marker" not in json.dumps(result)


def test_probe_timeout_is_retained_without_followup(pointer_fixture, monkeypatch):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)

    def timeout(operation, spelling, result):
        raise probe.Refusal("timeout")

    transport.action = timeout
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "timeout"
    assert result["retained"] is True and result["runtime_qualification"] == "not_run"
    assert transport.executions == [("positive", ""), ("write_open", ".git")]


@pytest.mark.parametrize("violation", ["metadata_limit", "source_alias", "owner_mismatch"])
def test_unadmitted_fixture_never_reaches_workload_execution(pointer_fixture, monkeypatch, violation):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    if violation == "metadata_limit":
        with (root / "fixture/main/.git/oversized").open("wb") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
    elif violation == "source_alias":
        (root / "fixture/task/alias").symlink_to(root / "owner.json")
    else:
        (root / "owner.json").write_text('{"schema_version":1,"run_id":"wrong"}')
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["runtime_qualification"] == "not_run"
    assert transport.executions == []


@pytest.mark.parametrize("violation", ["full", "alias"])
def test_unavailable_evidence_storage_blocks_before_workload_effects(pointer_fixture, monkeypatch, violation):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    target = root / "evidence/previous.json"
    if violation == "full":
        with target.open("wb") as stream:
            stream.truncate(100 * 1024 * 1024)
        target.chmod(0o600)
    else:
        target.symlink_to(root / "owner.json")
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["runtime_qualification"] == "not_run"
    assert result["retained"] is False
    assert transport.executions == []
    assert target.exists()  # No pruning or repair to manufacture retention.


def test_retention_failure_cannot_hide_observed_boundary_failure(pointer_fixture, monkeypatch):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    original = probe._write_pointer_evidence
    pointer = root / "fixture/task/.git"

    def mutate_and_break_retention(operation, spelling, result):
        pointer.write_bytes(b"retained failure")
        monkeypatch.setattr(probe, "_write_pointer_evidence",
                            lambda root, report: (_ for _ in ()).throw(probe.Refusal("evidence_limit")))
        return result

    transport.action = mutate_and_break_retention
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["retained"] is False
    assert result["runtime_qualification"] == "not_run"
    assert pointer.read_bytes() == b"retained failure"
    assert transport.executions == [("positive", ""), ("write_open", ".git")]
    monkeypatch.setattr(probe, "_write_pointer_evidence", original)


@pytest.mark.parametrize("during", ["positive", "write_open"])
@pytest.mark.parametrize("failure", ["timeout", "invalid_probe_output", "os_error"])
def test_host_mutation_is_observed_even_when_execute_raises(
        pointer_fixture, monkeypatch, during, failure):
    root, _ = pointer_fixture
    transport = install_transport(monkeypatch, pointer_fixture)
    original_execute = transport.execute
    pointer = root / "fixture/task/.git"

    def interrupted(program, deadline):
        result = original_execute(program, deadline)
        if transport.executions[-1][0] == during:
            pointer.write_bytes(b"retained interrupted mutation")
            if failure == "os_error":
                raise OSError("private transport failure")
            raise probe.Refusal(failure)
        return result

    transport.execute = interrupted
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert result["retained"] is True and result["runtime_qualification"] == "not_run"
    assert pointer.read_bytes() == b"retained interrupted mutation"
    assert transport.executions == (
        [("positive", "")] if during == "positive"
        else [("positive", ""), ("write_open", ".git")])
    assert "private transport failure" not in json.dumps(result)
    assert any(json.loads(path.read_text()) == result
               for path in (root / "evidence").glob("pointer-*.json"))


def run_pointer_program_with_fake_os(operation: str, denied_at: str) -> tuple[dict, list[str]]:
    """Execute the fixed program with every filesystem call intercepted."""
    calls = []

    def lstat(path):
        assert path == "/work/.git"
        calls.append("lstat")
        if denied_at == "lstat":
            raise PermissionError(errno.EACCES, "private setup failure")
        return SimpleNamespace(st_mode=stat.S_IFREG | 0o600)

    def open_file(path, flags, mode=None):
        if operation == "replace":
            assert Path(path).parent == Path("/work")
            assert Path(path).name.startswith(".openshell-replace-")
        else:
            assert path == "/work/.git"
        calls.append("temporary_open" if operation == "replace" else "target_open")
        raise PermissionError(errno.EACCES, "private open failure")

    def forbidden(*args, **kwargs):
        raise AssertionError("a denied prerequisite must not reach another filesystem operation")

    fake_os = SimpleNamespace(lstat=lstat, open=open_file, close=forbidden, write=forbidden,
                              replace=forbidden, unlink=forbidden, rename=forbidden, link=forbidden,
                              path=SimpleNamespace(lexists=forbidden),
                              O_WRONLY=os.O_WRONLY, O_APPEND=os.O_APPEND, O_TRUNC=os.O_TRUNC,
                              O_CREAT=os.O_CREAT, O_EXCL=os.O_EXCL)
    modules = {"errno": errno, "json": json, "os": fake_os, "stat": stat}

    def isolated_import(name, *args, **kwargs):
        assert name in modules, "unexpected import must not reach the host"
        return modules[name]

    output = StringIO()
    namespace = {"__builtins__": vars(builtins) | {"__import__": isolated_import}}
    with redirect_stdout(output):
        exec(compile(probe._pointer_program(operation, ".git"), "<fixed-pointer-program>", "exec"), namespace)
    assert "private" not in output.getvalue()
    return json.loads(output.getvalue()), calls


@pytest.mark.parametrize("operation,denied_at,expected_calls", [
    ("write_open", "lstat", ["lstat"]),
    ("replace", "temporary_open", ["lstat", "temporary_open"]),
])
def test_guest_setup_denial_does_not_count_as_target_protection(operation, denied_at, expected_calls):
    result, calls = run_pointer_program_with_fake_os(operation, denied_at)
    assert calls == expected_calls
    assert result["outcome"] == "unavailable"
    assert result["operation"] == operation and result["spelling"] == ".git"


def test_guest_target_open_denial_is_observed_as_target_protection():
    result, calls = run_pointer_program_with_fake_os("write_open", "target_open")
    assert calls == ["lstat", "target_open"]
    assert result["outcome"] == "denied" and result["errno"] == errno.EACCES


def native_identity_fixture() -> tuple[object, dict]:
    """Use the real identity parser with fixed native JSON and no native calls."""
    controller = object.__new__(probe._PointerController)
    controller.sandbox_name = "q-0123456789ab"
    controller.prepared = {"sandbox_id": "ab123456-1234-4234-8234-123456789abc", "container_id": "cd" * 32}
    sandbox = {
        "id": controller.prepared["sandbox_id"], "name": controller.sandbox_name,
        "phase": "Ready", "restart_policy": "never", "restart_count": 0,
        "main_process_instance_id": "same-process", "main_process_started_at_ms": 1700000000000,
        "current_policy_version": 1,
        "configuration_admission": {"state": "accepted", "policy_hash": "ab" * 32,
                                    "policy_version": 1, "config_revision": 1, "provider_env_revision": 1},
    }
    container = [{
        "Id": controller.prepared["container_id"],
        "State": {"Running": True, "Paused": False, "Pid": 1234, "StartedAt": "2026-11-01T00:00:00Z"},
        "Config": {"Labels": {"openshell.managed": "true", "openshell.ai/isolation-role": "sandbox",
                              "openshell.ai/sandbox-id": controller.prepared["sandbox_id"]}},
    }]

    def guest(argv, deadline):
        assert deadline > time.monotonic()
        if argv == ["/usr/bin/openshell", "sandbox", "get", controller.sandbox_name, "-o", "json"]:
            payload = sandbox
        else:
            assert argv == ["/usr/bin/podman", "inspect", "--type", "container", controller.prepared["container_id"]]
            payload = container
        return probe.CommandResult(0, json.dumps(payload).encode(), b"")

    controller.guest = guest
    return controller, sandbox


@pytest.mark.parametrize("field", ["policy_hash", "policy_version", "config_revision", "provider_env_revision"])
def test_native_policy_change_with_same_process_stops_next_attempt(pointer_fixture, monkeypatch, field):
    root, _ = pointer_fixture
    native, sandbox = native_identity_fixture()
    transport = install_transport(monkeypatch, pointer_fixture)
    transport.identity = native.identity

    def change_policy(operation, spelling, result):
        admission = sandbox["configuration_admission"]
        admission[field] = "ef" * 32 if field == "policy_hash" else 2
        if field == "policy_version":
            sandbox["current_policy_version"] = 2
        return result

    transport.action = change_policy
    result = probe.pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["reason"] == "sandbox_identity"
    assert result["retained"] is True and result["runtime_qualification"] == "not_run"
    assert transport.executions == [("positive", ""), ("write_open", ".git")]


@pytest.mark.parametrize("violation", [
    "missing_admission", "pending", "policy_hash", "policy_version", "config_revision",
    "provider_env_revision", "current_policy_version", "version_mismatch",
])
def test_native_identity_rejects_unaccepted_or_malformed_policy(violation):
    controller, sandbox = native_identity_fixture()
    if violation == "missing_admission":
        del sandbox["configuration_admission"]
    elif violation == "pending":
        sandbox["configuration_admission"]["state"] = "pending"
    elif violation == "policy_hash":
        sandbox["configuration_admission"]["policy_hash"] = "AB" * 32
    elif violation == "current_policy_version":
        sandbox["current_policy_version"] = True
    elif violation == "version_mismatch":
        sandbox["current_policy_version"] = 2
    else:
        sandbox["configuration_admission"][violation] = True
    with pytest.raises(probe.Refusal, match="^sandbox_identity$"):
        controller.identity(time.monotonic() + 60)


GUARD_OPERATIONS = ("setflags_clear", "fssetxattr_clear", "xattr_set", "chmod")
# JSON errno values originate in the Linux workload, not the macOS controller.
GUEST_ERRNO = SimpleNamespace(EACCES=13, EPERM=1, EROFS=30, ENOTTY=25,
                             EOPNOTSUPP=95, ENOSYS=38, EINVAL=22)


@pytest.fixture
def guarded_pointer_fixture(pointer_fixture, monkeypatch):
    """Keep host file observations real except synthetic immutable flag values."""
    root, env = pointer_fixture
    pointer = root / "fixture/task/.git"
    info = pointer.stat()
    receipt = {"schema_version": 1, "device": info.st_dev, "inode": info.st_ino,
               "uid": info.st_uid, "link_count": info.st_nlink, "size": info.st_size,
               "mode": info.st_mode, "mtime_ns": info.st_mtime_ns, "original_flags": 0,
               "protected_flags": 2, "sha256": hashlib.sha256(pointer.read_bytes()).hexdigest()}
    path = root / "guard.json"
    path.write_text(json.dumps(receipt))
    path.chmod(0o600)
    observed = {"flags": 2, "reads": 0}
    native_fstat = os.fstat

    def with_synthetic_flags(fd):
        result = native_fstat(fd)
        if (result.st_dev, result.st_ino) != (info.st_dev, info.st_ino):
            return result
        observed["reads"] += 1
        fields = {name: getattr(result, name) for name in dir(result) if name.startswith("st_")}
        if observed["flags"] is None:
            fields.pop("st_flags", None)
        else:
            fields["st_flags"] = observed["flags"]
        return SimpleNamespace(**fields)

    monkeypatch.setattr(probe.os, "fstat", with_synthetic_flags)
    return root, env, receipt, observed


def test_guard_snapshot_uses_open_file_identity_and_flags(guarded_pointer_fixture):
    root, _, receipt, observed = guarded_pointer_fixture
    actual = probe._guard_snapshot(root / "fixture/task/.git")
    expected = {key: value for key, value in receipt.items()
                if key not in {"schema_version", "original_flags", "protected_flags"}}
    expected["flags"] = 2
    assert actual == expected
    assert observed["reads"] > 0


@pytest.mark.parametrize("field", [
    "schema_version", "device", "inode", "uid", "link_count", "size", "mode",
    "mtime_ns", "original_flags", "protected_flags",
])
def test_boolean_guard_fields_refuse_before_native_calls(guarded_pointer_fixture, monkeypatch, field):
    root, _, receipt, _ = guarded_pointer_fixture
    receipt[field] = True
    (root / "guard.json").write_text(json.dumps(receipt))
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("native")
        raise AssertionError("invalid guard must refuse before native commands")

    monkeypatch.setattr(probe, "_PointerController", forbidden)
    monkeypatch.setattr(probe, "_host_git_fixture", forbidden)
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["runtime_qualification"] == "not_run"
    assert calls == []


@pytest.mark.parametrize("violation", [
    "unknown_field", "duplicate_field", "missing_field", "size_zero", "size_limit",
    "bad_hash", "wrong_hash", "wrong_inode", "wrong_uid", "hardlink_count",
    "directory_mode", "original_flags", "protected_flags", "unsafe_receipt", "receipt_alias",
    "missing_flags", "cleared_flags",
])
def test_invalid_or_unbound_guard_refuses_before_native_calls(guarded_pointer_fixture, monkeypatch, violation):
    root, _, receipt, observed = guarded_pointer_fixture
    path = root / "guard.json"
    changes = {"unknown_field": {"unexpected": "private marker"}, "size_zero": {"size": 0},
               "size_limit": {"size": 4097}, "bad_hash": {"sha256": "AB" * 32},
               "wrong_hash": {"sha256": "00" * 32}, "wrong_inode": {"inode": receipt["inode"] + 1},
               "wrong_uid": {"uid": receipt["uid"] + 1}, "hardlink_count": {"link_count": 2},
               "directory_mode": {"mode": stat.S_IFDIR | 0o700}, "original_flags": {"original_flags": 2},
               "protected_flags": {"protected_flags": 0}}
    receipt.update(changes.get(violation, {}))
    if violation == "missing_field":
        del receipt["mtime_ns"]
    raw = json.dumps(receipt)
    if violation == "duplicate_field":
        raw = raw[:-1] + ',"schema_version":1}'
    path.write_text(raw)
    if violation == "unsafe_receipt":
        path.chmod(0o644)
    elif violation == "receipt_alias":
        path.rename(root / "original-guard.json")
        path.symlink_to(root / "original-guard.json")
    elif violation == "missing_flags":
        observed["flags"] = None
    elif violation == "cleared_flags":
        observed["flags"] = 0
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("native")
        raise AssertionError("invalid guard must refuse before native commands")

    monkeypatch.setattr(probe, "_PointerController", forbidden)
    monkeypatch.setattr(probe, "_host_git_fixture", forbidden)
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable" and result["runtime_qualification"] == "not_run"
    assert calls == []
    assert "private marker" not in json.dumps(result)


def test_immutable_probe_checks_all_guards_before_pointer_operations(guarded_pointer_fixture, monkeypatch):
    root, env, _, observed = guarded_pointer_fixture
    transport = install_transport(monkeypatch, (root, env))
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "passed" and result["reason"] is None
    assert result["runtime_qualification"] == "not_run" and result["retained"] is True
    assert transport.executions[0] == ("positive", "")
    attempts = transport.executions[1:]
    first_pointer = next(index for index, (operation, _) in enumerate(attempts) if operation == "write_open")
    assert {operation for operation, _ in attempts[:first_pointer]} == set(GUARD_OPERATIONS)
    assert all(operation not in GUARD_OPERATIONS for operation, _ in attempts[first_pointer:])
    aliases = {spelling for operation, spelling in attempts if operation == "write_open"}
    assert {(operation, spelling) for operation, spelling in attempts[:first_pointer]} == {
        (operation, spelling) for operation in GUARD_OPERATIONS for spelling in aliases}
    assert observed["reads"] >= 2 * len(transport.executions)


@pytest.mark.parametrize("during", ["positive", "setflags_clear", "write_open"])
@pytest.mark.parametrize("failure", ["claimed_denial", "timeout"])
def test_immutable_guard_change_overrides_guest_result_or_exception(
        guarded_pointer_fixture, monkeypatch, during, failure):
    root, env, _, observed = guarded_pointer_fixture
    transport = install_transport(monkeypatch, (root, env))
    original_execute = transport.execute

    def lose_guard(program, deadline):
        result = original_execute(program, deadline)
        if transport.executions[-1][0] == during:
            observed["flags"] = 0
            if failure == "timeout":
                raise probe.Refusal("timeout")
        return result

    transport.execute = lose_guard
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "protected_state_changed"
    assert result["retained"] is True and result["runtime_qualification"] == "not_run"
    assert transport.executions[-1][0] == during
    assert sum(operation == during for operation, _ in transport.executions) == 1
    assert observed["flags"] == 0  # No repair that could manufacture a pass.


def test_successful_guard_syscall_with_unchanged_host_guard_is_distinct(
        guarded_pointer_fixture, monkeypatch):
    root, env, _, _ = guarded_pointer_fixture
    transport = install_transport(monkeypatch, (root, env))
    transport.action = lambda operation, spelling, result: (
        result | {"outcome": "succeeded", "errno": 0} if operation in GUARD_OPERATIONS else result)
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    checks = [check for check in result["checks"] if check.get("operation") in GUARD_OPERATIONS]
    assert result["status"] == "passed" and result["runtime_qualification"] == "not_run"
    assert checks and all(check["status"] == "succeeded_guard_intact" for check in checks)
    assert any(operation == "write_open" for operation, _ in transport.executions)


def test_immutable_guard_does_not_excuse_successful_pointer_write_open(guarded_pointer_fixture, monkeypatch):
    root, env, _, _ = guarded_pointer_fixture
    transport = install_transport(monkeypatch, (root, env))
    transport.action = lambda operation, spelling, result: (
        result | {"outcome": "succeeded", "errno": 0} if operation == "write_open" else result)
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "failed" and result["reason"] == "pointer_operation_allowed"
    assert transport.executions[-1] == ("write_open", ".git")


@pytest.mark.parametrize("operation,error_number", [
    ("chmod", errno.ENOTTY), ("setflags_clear", errno.EINVAL),
    ("fssetxattr_clear", errno.EINVAL), ("xattr_set", errno.EINVAL),
    # Controller-native errno numbers cannot widen the Linux guest allowlist.
    ("fssetxattr_clear", 102), ("xattr_set", 78),
])
def test_unexpected_unsupported_guard_result_cannot_authorize_pass(
        guarded_pointer_fixture, monkeypatch, operation, error_number):
    root, env, _, _ = guarded_pointer_fixture
    transport = install_transport(monkeypatch, (root, env))
    transport.action = lambda current, spelling, result: (
        result | {"outcome": "unsupported", "errno": error_number} if current == operation else result)
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    assert result["status"] == "unavailable"
    assert result["runtime_qualification"] == "not_run"
    assert transport.executions[-1][0] == operation


@pytest.mark.parametrize("operation,error_number", [
    ("setflags_clear", GUEST_ERRNO.ENOTTY), ("fssetxattr_clear", GUEST_ERRNO.EOPNOTSUPP),
    ("xattr_set", GUEST_ERRNO.ENOSYS),
])
def test_supported_classification_of_unavailable_guest_interfaces_is_explicit(
        guarded_pointer_fixture, monkeypatch, operation, error_number):
    root, env, _, _ = guarded_pointer_fixture
    transport = install_transport(monkeypatch, (root, env))
    transport.action = lambda current, spelling, result: (
        result | {"outcome": "unsupported", "errno": error_number} if current == operation else result)
    result = probe.immutable_pointer_probe(probe.Selection(root, DIGEST))
    checks = [check for check in result["checks"] if check.get("operation") == operation]
    assert checks and all(check["status"] == "unsupported" for check in checks)
    assert result["runtime_qualification"] == "not_run"


@pytest.mark.parametrize("mode", ["pointer", "immutable-pointer"])
def test_cli_routes_selected_probe_without_changing_default(owned_root, monkeypatch, capsys, mode):
    selected = owned_root / "selection.json"
    selected.write_bytes(selection_bytes(owned_root))
    selected.chmod(0o600)
    calls = []

    def report(name):
        def run(selection):
            assert selection.root == owned_root
            calls.append(name)
            return {"status": "passed", "probe": name, "runtime_qualification": "not_run"}
        return run

    monkeypatch.setattr(probe, "pointer_probe", report("pointer"))
    monkeypatch.setattr(probe, "immutable_pointer_probe", report("immutable-pointer"), raising=False)
    args = ["probe_openshell_runtime.py", "--selection", str(selected)]
    if mode == "immutable-pointer":
        args.extend(["--probe", mode])
    monkeypatch.setattr(sys, "argv", args)
    assert probe.main() == 0
    assert calls == [mode]
    assert json.loads(capsys.readouterr().out)["probe"] == mode


def run_guard_program_with_fake_interfaces(operation: str, failure_at=None, error_number=GUEST_ERRNO.EPERM):
    """Observe fixed guest arguments without reaching any real filesystem call."""
    calls = []

    def attempt(name):
        calls.append(name)
        if failure_at == name:
            raise OSError(error_number, "private synthetic interface error")

    def lstat(path):
        assert path == "/work/.git"
        attempt("lstat")
        return SimpleNamespace(st_mode=stat.S_IFREG | 0o600)

    def open_file(path, flags):
        assert path == "/work/.git"
        assert flags == os.O_RDONLY | os.O_NOFOLLOW
        attempt("open")
        return 17

    def close(fd):
        assert fd == 17
        calls.append("close")

    def ioctl(fd, request, payload):
        assert fd == 17
        expected = {"setflags_clear": (0x40086602, bytes(8)),
                    "fssetxattr_clear": (0x401C5820, bytes(28))}
        assert (request, payload) == expected[operation]
        attempt(operation)

    def setxattr(path, name, value, *, follow_symlinks):
        assert path == "/work/.git" and name == "user.openshell_qualification" and value == b"probe"
        assert follow_symlinks is False
        attempt("xattr_set")

    def chmod(path, mode, *, follow_symlinks):
        assert path == "/work/.git" and mode == 0o600 and follow_symlinks is False
        attempt("chmod")

    fake_os = SimpleNamespace(lstat=lstat, open=open_file, close=close, setxattr=setxattr, chmod=chmod,
                              O_RDONLY=os.O_RDONLY, O_NOFOLLOW=os.O_NOFOLLOW)
    modules = {"errno": GUEST_ERRNO, "fcntl": SimpleNamespace(ioctl=ioctl), "json": json,
               "os": fake_os, "stat": stat}

    def isolated_import(name, *args, **kwargs):
        assert name in modules, "unexpected import must not reach the host"
        return modules[name]

    namespace = {"__builtins__": vars(builtins) | {"__import__": isolated_import}}
    output = StringIO()
    with redirect_stdout(output):
        exec(compile(probe._guard_program(operation, ".git"), "<fixed-guard-program>", "exec"), namespace)
    assert "private" not in output.getvalue()
    return json.loads(output.getvalue()), calls


@pytest.mark.parametrize("operation", GUARD_OPERATIONS)
def test_guard_program_uses_only_fixed_target_arguments_and_closes_descriptors(operation):
    result, calls = run_guard_program_with_fake_interfaces(operation)
    assert result == {"schema_version": 1, "operation": operation, "spelling": ".git",
                      "outcome": "succeeded", "errno": 0}
    assert calls == (["lstat", "open", operation, "close"]
                     if operation in {"setflags_clear", "fssetxattr_clear"} else ["lstat", operation])


@pytest.mark.parametrize("operation,failure_at", [
    *((operation, "lstat") for operation in GUARD_OPERATIONS),
    ("setflags_clear", "open"), ("fssetxattr_clear", "open"),
])
def test_guard_program_does_not_count_failed_setup_as_target_denial(operation, failure_at):
    result, calls = run_guard_program_with_fake_interfaces(operation, failure_at)
    assert result["outcome"] == "unavailable"
    assert operation not in calls
    assert "close" not in calls


@pytest.mark.parametrize("operation,error_number,expected", [
    *((operation, error_number, "denied") for operation in GUARD_OPERATIONS
      for error_number in (GUEST_ERRNO.EACCES, GUEST_ERRNO.EPERM, GUEST_ERRNO.EROFS)),
    *((operation, error_number, "unsupported") for operation in GUARD_OPERATIONS if operation != "chmod"
      for error_number in (GUEST_ERRNO.ENOTTY, GUEST_ERRNO.EOPNOTSUPP, GUEST_ERRNO.ENOSYS)),
    *(("chmod", error_number, "unavailable") for error_number in (GUEST_ERRNO.ENOTTY, GUEST_ERRNO.EOPNOTSUPP, GUEST_ERRNO.ENOSYS)),
    *((operation, GUEST_ERRNO.EINVAL, "unavailable") for operation in GUARD_OPERATIONS),
])
def test_guard_program_classifies_only_expected_target_errors(operation, error_number, expected):
    result, calls = run_guard_program_with_fake_interfaces(operation, operation, error_number)
    assert result["outcome"] == expected and result["errno"] == error_number
    assert calls.count(operation) == 1
    if operation in {"setflags_clear", "fssetxattr_clear"}:
        assert calls[-1] == "close"


@pytest.mark.parametrize("operation,spelling", [
    ("arbitrary", ".git"), ("chmod", "../.git"), ("setflags_clear", ".git;private"),
])
def test_guard_program_refuses_unreviewed_operation_or_path(operation, spelling):
    with pytest.raises(probe.Refusal, match="^invalid_probe$"):
        probe._guard_program(operation, spelling)


def test_replacement_attempts_reach_each_case_alias_with_retained_temporary_files():
    """A case-insensitive share must not confuse retained probe outputs."""
    pointer_bytes = b"gitdir: /host/synthetic/.git/worktrees/task\n"
    files = {"/work/.git": pointer_bytes}
    descriptors = {}
    target_attempts = []
    temporary_paths = []

    def lstat(path):
        assert path.casefold() == "/work/.git"
        return SimpleNamespace(st_mode=stat.S_IFREG | 0o600)

    def open_file(path, flags, mode):
        assert Path(path).parent == Path("/work")
        assert Path(path).name.startswith(".openshell-replace-")
        assert flags == os.O_WRONLY | os.O_CREAT | os.O_EXCL and mode == 0o600
        key = path.casefold()
        if key in files:
            raise FileExistsError(errno.EEXIST, "retained temporary path already exists")
        files[key] = b""
        fd = len(files) + 10
        descriptors[fd] = key
        temporary_paths.append(path)
        return fd

    def write(fd, content):
        files[descriptors[fd]] += content
        return len(content)

    def close(fd):
        del descriptors[fd]

    def replace(source, target):
        assert files[source.casefold()] == b"probe"
        assert target.casefold() == "/work/.git"
        target_attempts.append(target)
        raise PermissionError(errno.EACCES, "protected target denied")

    fake_os = SimpleNamespace(lstat=lstat, open=open_file, write=write, close=close, replace=replace,
                              O_WRONLY=os.O_WRONLY, O_CREAT=os.O_CREAT, O_EXCL=os.O_EXCL)
    modules = {"errno": errno, "json": json, "os": fake_os, "stat": stat}

    def isolated_import(name, *args, **kwargs):
        assert name in modules, "unexpected import must not reach the host"
        return modules[name]

    results = []
    spellings = (".git", ".GIT", ".GiT")
    for spelling in spellings:
        namespace = {"__builtins__": vars(builtins) | {"__import__": isolated_import}}
        output = StringIO()
        with redirect_stdout(output):
            exec(compile(probe._pointer_program("replace", spelling), "<fixed-pointer-program>", "exec"), namespace)
        results.append(json.loads(output.getvalue()))
    assert target_attempts == ["/work/" + spelling for spelling in spellings]
    assert all(result["outcome"] == "denied" and result["errno"] == errno.EACCES for result in results)
    assert len({path.casefold() for path in temporary_paths}) == len(spellings)
    assert files["/work/.git"] == pointer_bytes
    assert len(files) == 1 + len(spellings)  # Retain each temporary file for evidence.
    assert descriptors == {}
