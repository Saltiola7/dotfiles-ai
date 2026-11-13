"""Real Git-object correspondence; no forge, credentials or working source checkout."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from collections.abc import Mapping
from typing import IO

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core
from integration_coordinator.gitproof import GitMirror, GitObjects, ProofPort, prove_series
from integration_coordinator import runtime


@pytest.fixture
def objects(tmp_path: Path) -> Path:
    repo = tmp_path / "objects.git"
    run(repo.parent, "init", "--bare", "--template=", str(repo))
    return repo


def run(repo: Path, *args: str, data: str | None = None) -> str:
    env = {"PATH": os.environ["PATH"], "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Fixture",
           "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_AUTHOR_DATE": "1700000000 +0000",
           "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
           "GIT_COMMITTER_DATE": "1700000000 +0000"}
    return subprocess.run(["git", "-C", str(repo), *args], input=data, env=env,
                          text=True, capture_output=True, check=True).stdout.strip()


def commit(repo: Path, files: dict[str, str], parent: str | None, message: str) -> str:
    rows = []
    for name, content in sorted(files.items()):
        blob = run(repo, "hash-object", "-w", "--stdin", data=content)
        rows.append(f"100644 blob {blob}\t{name}\n")
    tree = run(repo, "mktree", data="".join(rows))
    return run(repo, "commit-tree", tree, *(["-p", parent] if parent else []), data=message + "\n")


def series(repo: Path) -> tuple[str, str, str, str, str, str]:
    root = commit(repo, {"a": "zero\n"}, None, "root")
    first = commit(repo, {"a": "one\n"}, root, "phase one")
    second = commit(repo, {"a": "one\n", "b": "two\n"}, first, "phase two")
    base = commit(repo, {"a": "zero\n", "c": "other\n"}, root, "other task")
    landed1 = commit(repo, {"a": "one\n", "c": "other\n"}, base, "phase one")
    landed2 = commit(repo, {"a": "one\n", "b": "two\n", "c": "other\n"}, landed1, "phase two")
    return root, first, second, base, landed1, landed2


def test_each_phase_replays_on_the_actual_new_base(objects: Path) -> None:
    root, first, second, base, one, two = series(objects)
    result = prove_series(GitObjects(objects), root, (first, second), two, base)
    assert result.base == base and result.head == two
    assert result.pairs == (core.CommitPair(first, one), core.CommitPair(second, two))
    assert result.tree == run(objects, "rev-parse", two + "^{tree}")


def test_final_tree_cannot_hide_changed_intermediate_phase(objects: Path) -> None:
    root, first, second, base, _, _ = series(objects)
    wrong = commit(objects, {"a": "zero\n", "b": "two\n", "c": "other\n"}, base, "phase one")
    final = commit(objects, {"a": "one\n", "b": "two\n", "c": "other\n"}, wrong, "phase two")
    with pytest.raises(core.Invalid):
        prove_series(GitObjects(objects), root, (first, second), final, base)


def test_message_or_missing_phase_is_not_correspondence(objects: Path) -> None:
    root, first, second, base, one, two = series(objects)
    wrong = commit(objects, {"a": "one\n", "b": "two\n", "c": "other\n"}, one, "different intent")
    for destination in (wrong, one):
        with pytest.raises(core.Invalid):
            prove_series(GitObjects(objects), root, (first, second), destination, base)
    assert two != wrong


def test_unknown_empty_commit_and_nonconsecutive_source_are_rejected(objects: Path) -> None:
    root, first, second, base, _, two = series(objects)
    empty = commit(objects, {"a": "one\n", "b": "two\n"}, second, "empty phase")
    for sources in ((second, first), (first, empty), (first, second, empty)):
        with pytest.raises(core.Invalid):
            prove_series(GitObjects(objects), root, sources, two, base)


def test_unsafe_attributes_and_local_driver_are_rejected(objects: Path) -> None:
    root, first, _, _, _, _ = series(objects)
    run(objects, "config", "merge.fixture.driver", "false")
    with pytest.raises(core.Invalid):
        prove_series(GitObjects(objects), root, (first,), first, root)
    run(objects, "config", "--unset", "merge.fixture.driver")
    poisoned = commit(objects, {"a": "one\n", ".gitattributes": "* merge=fixture\n"}, root, "phase")
    with pytest.raises(core.Invalid):
        prove_series(GitObjects(objects), root, (poisoned,), poisoned, root)


def test_control_root_ancestry_is_not_a_clock_or_name_check(objects: Path) -> None:
    root, first, _, _, _, _ = series(objects)
    unrelated = commit(objects, {"ledger": "genesis\n"}, None, "control genesis")
    reader = GitObjects(objects)
    assert reader.ancestor(root, first)
    assert not reader.ancestor(unrelated, first)
    assert reader.excludes_root(unrelated, (root, first))
    assert not reader.excludes_root(root, (first,))


def test_projection_and_delivery_ports_compose_without_relabeling_originals(objects: Path) -> None:
    root, first, second, base, one, two = series(objects)
    source = runtime.SourceSeries("example/repo", 1, root, second,
        (runtime.SourceEntry(first, "phase", ("domain",)),
         runtime.SourceEntry(second, "phase", ("contract",))), "a" * 64)
    requested: list[tuple[str, ...]] = []

    def supply(oids: tuple[str, ...]) -> GitObjects:
        requested.append(oids)
        return GitObjects(objects)

    port = ProofPort(supply)
    projection = port.prove_refresh(source, two, base)
    assert projection.mapping == (core.CommitPair(first, one), core.CommitPair(second, two))
    assert projection.source_digest == core.identity(source)
    landed1 = commit(objects, {"a": "one\n", "c": "other\n"}, base, "phase one")
    landed2 = commit(objects, {"a": "one\n", "b": "two\n", "c": "other\n"}, landed1, "phase two")
    mapping = port.prove_delivery(source, projection, landed2)
    assert mapping == (core.CommitPair(one, landed1), core.CommitPair(two, landed2))
    assert requested and all(len(set(ids)) == len(ids) for ids in requested)


def test_shallow_history_never_proves_control_root_exclusion(objects: Path) -> None:
    root, first, _, _, _, _ = series(objects)
    (objects / "shallow").write_text(first + "\n")
    with pytest.raises(core.Invalid):
        GitObjects(objects).excludes_root(root, (first,))


def test_mirror_credentials_stay_out_of_argv_and_inherited_git_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    original = subprocess.Popen
    arguments: list[list[str]] = []
    environments: list[dict[str, str]] = []

    def observed(args: list[str], *, env: Mapping[str, str], stdin: int,
                 stdout: IO[bytes], stderr: IO[bytes], start_new_session: bool) -> subprocess.Popen[bytes]:
        arguments.append(args)
        environments.append(dict(env))
        return original(args, env=env, stdin=stdin, stdout=stdout, stderr=stderr,
                        start_new_session=start_new_session)

    monkeypatch.setattr(subprocess, "Popen", observed)
    monkeypatch.setenv("GIT_TRACE_CURL", "1")
    monkeypatch.setenv("GIT_CURL_VERBOSE", "1")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "99")
    with GitMirror("example/repo", "fixture-credential") as mirror:
        mirror._run("version", authenticated=True)
        assert "fixture-credential" not in repr(mirror)
    assert len(arguments) == 1 and all("fixture-credential" not in arg for arg in arguments[0])
    assert "GIT_TRACE_CURL" not in environments[0] and "GIT_CURL_VERBOSE" not in environments[0]
    assert environments[0]["GIT_CONFIG_COUNT"] == "1"
    assert environments[0]["GIT_CONFIG_VALUE_0"].startswith("AUTHORIZATION: basic ")
