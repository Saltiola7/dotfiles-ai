"""Preserved lifecycle delegation; tiny owners qualify routing, not the external component.

The first eight test functions retain the producer's helper-bound contracts.
Real component coherence and managed generation remain separate rollout evidence.
"""

from contextlib import contextmanager
import builtins
import importlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import test_dbsctrctl as lifecycle_harness
from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_dbsctrctl"


@pytest.fixture(autouse=True)
def isolated_owner_modules():
    """Restore every preexisting optional module and search path after each case."""
    def belongs(name):
        return name == "continuous_validation" or name.startswith("continuous_validation.")

    previous = {name: module for name, module in list(sys.modules.items()) if belongs(name)}
    previous_path = list(sys.path)
    for name in previous:
        sys.modules.pop(name, None)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        for name in list(sys.modules):
            if belongs(name):
                sys.modules.pop(name, None)
        sys.modules.update(previous)
        sys.path[:] = previous_path
        importlib.invalidate_caches()


@pytest.fixture
def core():
    loader = importlib.machinery.SourceFileLoader("validation_compat_fixture", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None, "Lifecycle helper must have an executable module spec"
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_new_registration_publishes_only_after_mutation_guard(core, monkeypatch):
    guarded = []
    seen = []

    @contextmanager
    def guard(*args):
        guarded.append(True)
        try:
            yield
        finally:
            guarded.pop()

    event = {"worktree": Path("/fixture"), "cycle": "cycle-new"}
    args = SimpleNamespace(
        command="begin", func=lambda _: {"validation_registration": event}
    )
    monkeypatch.setattr(
        core, "parser", lambda: SimpleNamespace(parse_args=lambda: args)
    )
    monkeypatch.setattr(core, "forgejo_internal_main", lambda _: False)
    monkeypatch.setattr(core, "local_dispatch_selection", lambda _: None)
    monkeypatch.setattr(core, "local_cli_mutation_guard", guard)
    monkeypatch.setattr(core, "continuation_guard", lambda _: None)
    monkeypatch.setattr(core, "workflow_operation_start", lambda _: None)
    monkeypatch.setattr(core, "workflow_operation_finish", lambda *a: None)
    monkeypatch.setattr(
        core,
        "optional_validation_registration",
        lambda value: seen.append((value, bool(guarded))),
    )
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "begin"])
    assert core.main() == 0
    assert seen == [(event, False)]
    args.func = lambda _: None  # Resume/preflight produce no registration marker.
    assert core.main() == 0
    assert len(seen) == 1


def test_missing_policy_never_imports_optional_owner_or_uses_git(
    core, tmp_path, monkeypatch
):
    monkeypatch.setattr(core.Path, "home", classmethod(lambda cls: tmp_path.resolve()))
    monkeypatch.setattr(
        core.subprocess, "run", lambda *a, **k: pytest.fail("disabled Git/process")
    )
    assert (
        core.managed_validation_action(
            "enroll", {"worktree": tmp_path, "cycle": "new"}
        )["status"]
        == "disabled"
    )
    monkeypatch.setattr(
        core, "root_dir", lambda: pytest.fail("disabled task Git lookup")
    )
    core.command_validation_checkpoint(
        SimpleNamespace(gate="contract", purpose="artifact", expected_test_id=[])
    )
    core.command_validation_opt_out(SimpleNamespace(on=True))
    assert not (tmp_path / ".local").exists()


def test_typed_readiness_parser_does_not_accept_commands(core):
    args = core.parser().parse_args(
        [
            "validation-checkpoint",
            "--gate",
            "contract",
            "--purpose",
            "red-proof",
            "--expected-test-id",
            "tests/test_x.py::test_x",
        ]
    )
    assert args.expected_test_id == ["tests/test_x.py::test_x"]
    with pytest.raises(SystemExit):
        core.parser().parse_args(
            ["validation-checkpoint", "--gate", "test", "--purpose", "shell:run"]
        )
    assert core.parser().parse_args(["validation-opt-out", "--on"]).on is True


def test_managed_gate_commit_routes_without_legacy_registry(
    core, tmp_path, monkeypatch
):
    monkeypatch.setattr(core.Path, "home", classmethod(lambda cls: tmp_path.resolve()))
    calls = []
    monkeypatch.setattr(
        core,
        "managed_validation_action",
        lambda action, event: calls.append((action, event)) or {"status": "queued"},
    )
    event = {
        "worktree": tmp_path,
        "cycle": "cycle-new",
        "head": "a" * 40,
        "gates": ["contract", "test_driven_implementation"],
    }
    core.optional_shadow_checkpoint(event)
    assert calls[0][0] == "checkpoint"
    assert calls[0][1]["purpose"] == "green-validation"
    assert (
        calls[0][1]["checkpoint_id"]
        == "gate-" + "a" * 40 + "-test_driven_implementation"
    )
    assert len(calls) == 1


def test_optional_registration_failure_preserves_native_result(
    core, monkeypatch, capsys
):
    monkeypatch.setattr(
        core,
        "managed_validation_action",
        lambda *a: (_ for _ in ()).throw(RuntimeError("private detail")),
    )
    core.optional_validation_registration(
        {"worktree": Path("/fixture"), "cycle": "new"}
    )
    assert (
        capsys.readouterr().err.strip()
        == "continuous_validation_enrollment_unavailable"
    )


def test_automatic_registration_declares_its_origin(core, monkeypatch):
    seen = []
    monkeypatch.setattr(
        core, "managed_validation_action", lambda action, event: seen.append(event)
    )
    event = {"worktree": Path("/fixture"), "cycle": "new"}
    core.optional_validation_registration(event)
    assert seen == [{**event, "automatic": True}]
    assert "automatic" not in event


def test_explicit_only_auto_registration_has_no_import_git_or_state(
    core, tmp_path, monkeypatch
):
    monkeypatch.setattr(core.Path, "home", classmethod(lambda cls: tmp_path.resolve()))
    path = tmp_path / ".config/dotfiles-ai/continuous-validation-policy.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"enabled": True, "enrollment": "explicit-only"}))
    path.chmod(0o600)
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == "continuous_validation.cli":
            pytest.fail("automatic enrollment imported optional owner")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(
        core.subprocess, "run", lambda *a, **k: pytest.fail("automatic Git/process")
    )
    assert (
        core.managed_validation_action(
            "enroll",
            {"worktree": tmp_path / "absent", "cycle": "new", "automatic": True},
        )["status"]
        == "disabled"
    )
    assert not (tmp_path / ".local").exists()


@pytest.mark.parametrize(
    "gates",
    [
        ["refactor", "test_driven_implementation"],
        ["test_driven_implementation", "refactor"],
    ],
)
def test_gate_commit_uses_canonical_broadest_gate_independent_of_argument_order(
    core, tmp_path, monkeypatch, gates
):
    calls = []
    monkeypatch.setattr(
        core,
        "managed_validation_action",
        lambda action, event: calls.append(event) or {"status": "queued"},
    )
    core.optional_shadow_checkpoint(
        {"worktree": tmp_path, "cycle": "new", "head": "a" * 40, "gates": gates}
    )
    assert calls[0]["gate"] == "refactor" and calls[0]["purpose"] == "regression"


def write_policy(home, value):
    path = home / ".config/dotfiles-ai/continuous-validation-policy.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    path.chmod(0o600)


@pytest.fixture
def owner_layout(core, tmp_path, monkeypatch):
    home = (tmp_path / "owned-home").resolve()
    home.mkdir()
    source = tmp_path / "source"
    helper = source / "dot_local/bin/dbsctrctl"
    helper.parent.mkdir(parents=True)
    helper.write_text("# Synthetic helper path for managed owner selection.\n")
    monkeypatch.setattr(core, "__file__", str(helper))
    monkeypatch.setattr(core.Path, "home", classmethod(lambda cls: home))
    write_policy(home, {"enabled": True, "enrollment": "allowlisted-new-tasks"})
    return {
        "home": home,
        "source": source / "private_dot_config/dotfiles-ai",
        "installed": home / ".config/dotfiles-ai",
    }


def write_owner(parent, status, *, broken=False):
    """A minimal real Python package exercises ownership routing only."""
    package = parent / "continuous_validation"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("")
    if broken:
        body = "import ci_validation_deliberately_absent_owner_dependency_4d8c\n"
    else:
        body = (
            "from pathlib import Path\n\n"
            "def managed_action(action, **fields):\n"
            "    Path(__file__).with_name('called').write_text(action)\n"
            f"    return {{'status': {status!r}, 'action': action, 'cycle': fields['cycle']}}\n"
        )
    (package / "cli.py").write_text(body)
    return package


@pytest.mark.parametrize("policy", [None, {"enabled": False}, {"enabled": True, "enrollment": "explicit-only"}])
def test_inert_policy_returns_before_any_optional_import_git_or_state(core, tmp_path, monkeypatch, policy):
    home = tmp_path.resolve()
    monkeypatch.setattr(core.Path, "home", classmethod(lambda cls: home))
    if policy is not None:
        write_policy(home, policy)
    original = builtins.__import__

    def guarded_import(name, *arguments, **keywords):
        if name == "continuous_validation" or name.startswith("continuous_validation."):
            pytest.fail("Inert policy imported its optional owner")
        return original(name, *arguments, **keywords)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(core.subprocess, "run", lambda *a, **k: pytest.fail("Inert policy accessed Git/processes"))
    result = core.managed_validation_action(
        "enroll", {"worktree": home / "absent", "cycle": "new", "automatic": True}
    )
    assert result == {"status": "disabled", "advisory": True}
    assert not (home / ".local").exists()
    assert not any(name == "continuous_validation" or name.startswith("continuous_validation.") for name in sys.modules)


@pytest.mark.parametrize("source_complete", [False, True])
def test_source_owner_requires_actual_managed_cli_file(core, owner_layout, source_complete):
    source = owner_layout["source"]
    installed = write_owner(owner_layout["installed"], "installed-selected")
    if source_complete:
        source_package = write_owner(source, "source-selected")
    else:
        source_package = source / "continuous_validation"
        source_package.mkdir(parents=True)
        (source_package / "__init__.py").write_text("")
        (source_package / "checkpoints.py").write_text("# Retained legacy checkpoint owner, without managed CLI.\n")
    result = core.managed_validation_action(
        "enroll", {"worktree": owner_layout["home"] / "task", "cycle": "new"}
    )
    assert result == {
        "status": "source-selected" if source_complete else "installed-selected",
        "action": "enroll", "cycle": "new",
    }
    selected, unselected = (source_package, installed) if source_complete else (installed, source_package)
    assert (selected / "called").read_text() == "enroll"
    assert not (unselected / "called").exists()


def test_cached_foreign_optional_module_is_rejected_without_switching_owner(core, owner_layout, tmp_path):
    selected = write_owner(owner_layout["source"], "selected")
    write_owner(owner_layout["installed"], "installed")
    foreign_root = tmp_path / "foreign"
    foreign = write_owner(foreign_root, "foreign")
    sys.path.insert(0, str(foreign_root))
    imported = importlib.import_module("continuous_validation.cli")
    with pytest.raises(RuntimeError, match="continuous_validation_owner_unavailable"):
        core.managed_validation_action("enroll", {"worktree": tmp_path, "cycle": "new"})
    assert sys.modules["continuous_validation.cli"] is imported
    assert not (foreign / "called").exists() and not (selected / "called").exists()


def test_broken_selected_owner_import_never_falls_back(core, owner_layout, tmp_path):
    write_owner(owner_layout["source"], "selected", broken=True)
    installed = write_owner(owner_layout["installed"], "fallback-must-not-run")
    with pytest.raises(RuntimeError) as raised:
        core.managed_validation_action("enroll", {"worktree": tmp_path, "cycle": "new"})
    assert str(raised.value) == "continuous_validation_owner_unavailable"
    assert not (installed / "called").exists()


def test_selected_source_without_package_init_rejects_before_any_owner_import(core, owner_layout, tmp_path):
    selected = owner_layout["source"] / "continuous_validation"
    selected.mkdir(parents=True)
    selected_marker = tmp_path / "selected-owner-imported"
    installed_marker = tmp_path / "installed-owner-imported"
    (selected / "cli.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(selected_marker)!r}).write_text('selected imported')\n"
        "def managed_action(*args, **kwargs):\n    return {'status': 'must-not-run'}\n"
    )
    installed = write_owner(owner_layout["installed"], "must-not-fall-back")
    installed_cli = installed / "cli.py"
    installed_cli.write_text(
        "from pathlib import Path\n"
        f"Path({str(installed_marker)!r}).write_text('installed imported')\n"
        + installed_cli.read_text()
    )
    with pytest.raises(RuntimeError, match="continuous_validation_owner_unavailable"):
        core.managed_validation_action("enroll", {"worktree": tmp_path, "cycle": "new"})
    assert not selected_marker.exists() and not installed_marker.exists()
    assert not (selected / "called").exists() and not (installed / "called").exists()


def test_optional_checkpoint_failure_preserves_formal_result_stdout_and_closed_locks(core, tmp_path, monkeypatch, capsys):
    """The formal handler seam succeeds; optional failure must not change its result."""
    monkeypatch.setattr(core.Path, "home", classmethod(lambda cls: tmp_path.resolve()))
    guarded = []
    committed = tmp_path / "formal-handler-result"
    commit = "a" * 40
    calls = []

    @contextmanager
    def guard(*arguments):
        guarded.append(True)
        try:
            yield
        finally:
            guarded.pop()

    def formal_commit(_):
        committed.write_text(commit)
        print(commit)
        return {"worktree": tmp_path, "cycle": "new", "head": commit, "gates": ["contract"]}

    def unavailable(action, event):
        assert committed.read_text() == commit and not guarded
        calls.append((action, event))
        raise RuntimeError("PRIVATE_OPTIONAL_DETAIL_" + "secret" * 1000)

    args = SimpleNamespace(command="gate-commit", func=formal_commit)
    monkeypatch.setattr(core, "parser", lambda: SimpleNamespace(parse_args=lambda: args))
    monkeypatch.setattr(core, "forgejo_internal_main", lambda _: False)
    monkeypatch.setattr(core, "local_dispatch_selection", lambda _: None)
    monkeypatch.setattr(core, "local_cli_mutation_guard", guard)
    monkeypatch.setattr(core, "continuation_guard", lambda _: None)
    monkeypatch.setattr(core, "workflow_operation_start", lambda _: None)
    monkeypatch.setattr(core, "workflow_operation_finish", lambda *a: None)
    monkeypatch.setattr(core, "managed_validation_action", unavailable)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "gate-commit"])
    assert core.main() == 0
    output = capsys.readouterr()
    assert output.out == commit + "\n"
    assert output.err == "continuous_validation_checkpoint_unavailable\n"
    assert committed.read_text() == commit and len(calls) == 1



@pytest.mark.parametrize("enabled", [False, True])
def test_native_registration_and_durable_gate_commit_publish_only_after_locks(initiative, fixture, tmp_path, enabled):
    """Real fixture registration, evidence and Gate Commit; only the optional owner is tiny."""
    _, target, record_path, begin, _, _ = initiative
    assert isinstance(fixture, lifecycle_harness.DbsctrctlTest)
    original_home = os.environ.get("HOME")
    home = (tmp_path / "owned-native-home").resolve()
    home.mkdir()
    package = home / ".config/dotfiles-ai/continuous_validation"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "cli.py").write_text(r"""import json
import subprocess
import sys
from pathlib import Path

Path(__file__).with_name("imported").write_text("native optional owner imported")

def managed_action(action, **fields):
    root = Path(fields["worktree"])
    common = Path(subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        text=True, timeout=10).strip())
    probe = (
        "import fcntl,json,sys\n"
        "from pathlib import Path\n"
        "rows=[]\n"
        "for path in Path(sys.argv[1]).glob('evidence-*.lock'):\n"
        " with path.open('r+') as stream:\n"
        "  try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
        "  except BlockingIOError: raise SystemExit(74)\n"
        " rows.append(path.name)\n"
        "print(json.dumps(rows))\n"
    )
    locks = json.loads(subprocess.check_output(
        [sys.executable, "-c", probe, str(common / "dbsctr/locks")],
        text=True, timeout=10))
    record = json.loads((common / "dbsctr/cycles" / (fields["cycle"] + ".json")).read_text())
    assert record["cycle_id"] == fields["cycle"]
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                   text=True, timeout=10).strip()
    if action == "checkpoint":
        assert head == fields["head"] == record["commits"][-1]["id"]
        assert record["gates"]["domain"]["result"] == "passed"
    observation = {"action": action, "head": head, "gate": fields.get("gate"),
                   "purpose": fields.get("purpose"), "locks": locks,
                   "committed": [item["id"] for item in record["commits"]]}
    with Path(__file__).with_name("events.jsonl").open("a") as stream:
        stream.write(json.dumps(observation, sort_keys=True) + "\n")
    return {"status": "queued", "advisory": True}
""")
    if enabled:
        write_policy(home, {"enabled": True, "enrollment": "allowlisted-new-tasks"})
    bootstrap = tmp_path / "owned_home_bootstrap.py"
    bootstrap.write_text(
        "from pathlib import Path\n"
        f"Path.home = classmethod(lambda cls: Path({str(home)!r}))\n"
        "import runpy, sys\n"
        f"sys.argv = [{str(SCRIPT)!r}, *sys.argv[1:]]\n"
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
    )
    environment = lifecycle_harness.isolated_env()
    environment["PATH"] = str(Path(sys.executable).resolve().parent) + os.pathsep + environment["PATH"]
    environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "tests")))
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    transcript = []

    def successful_native(label, result):
        transcript.append({"operation": label, "returncode": result.returncode,
                           "stdout": result.stdout, "stderr": result.stderr})
        (tmp_path / "native-cli-results.json").write_text(json.dumps(transcript, indent=2))
        assert result.returncode == 0, result.stdout + result.stderr
        for marker in ("continuous_validation_enrollment_unavailable",
                       "continuous_validation_checkpoint_unavailable"):
            assert marker not in result.stderr, result.stderr

    result = lifecycle_harness.run(target, *begin, "--approval", "agent-confirmed",
                                   script=bootstrap, env=environment)
    successful_native("begin", result)
    assert "Approval: agent-confirmed (caller assertion)" in result.stderr
    assert json.loads(record_path.read_text())["initiative_approval"]["method"] == "agent_confirmed"
    events_path = package / "events.jsonl"
    if enabled:
        initial = [json.loads(line) for line in events_path.read_text().splitlines()]
        assert len(initial) == 1 and initial[0]["action"] == "enroll"
        assert any(name.startswith("evidence-registration-") for name in initial[0]["locks"])
    else:
        assert not events_path.exists() and not (package / "imported").exists()
    resumed = lifecycle_harness.run(target, *begin, "--resume-existing", script=bootstrap, env=environment)
    successful_native("resume", resumed)
    (target / "tracked.txt").write_text("native validated artifact\n")
    evidence = lifecycle_harness.run(
        target, "record-evidence", "domain", "--authority", "native-compatibility-test",
        "--path", "tracked.txt", "--", sys.executable, "-c",
        "from pathlib import Path; assert Path('tracked.txt').read_text() == 'native validated artifact\\n'",
        script=bootstrap, env=environment,
    )
    successful_native("record-evidence", evidence)
    if enabled:
        assert len(events_path.read_text().splitlines()) == 1
    committed = lifecycle_harness.run(
        target, "gate-commit", "--message", "Native optional routing proof", "--gates", "domain",
        "--paths", "tracked.txt", script=bootstrap, env=environment,
    )
    successful_native("gate-commit", committed)
    commit = committed.stdout.strip()
    assert len(commit) == 40
    record = json.loads(record_path.read_text())
    assert record["commits"][-1] == {"id": commit, "gates": ["domain"]}
    assert record["gates"]["domain"]["result"] == "passed"
    actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target,
                                          env=environment, text=True, timeout=10).strip()
    assert commit == actual_head
    if enabled:
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        assert [event["action"] for event in events] == ["enroll", "checkpoint"]
        assert events[1]["head"] == commit == events[1]["committed"][-1]
        assert events[1]["gate"] == "domain" and events[1]["purpose"] == "artifact"
        assert "evidence-local-mutation-cycle-1.lock" in events[1]["locks"]
    else:
        assert not events_path.exists() and not (package / "imported").exists()
    assert os.environ.get("HOME") == original_home
