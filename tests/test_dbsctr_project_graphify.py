from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

import pytest


ADAPTER = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctr-project-graphify"


def run(*args: str | Path, cwd: Path, env: dict[str, str] | None = None):
    return subprocess.run(
        [str(arg) for arg in args], cwd=cwd, env=env, text=True,
        capture_output=True, check=False, timeout=30,
    )


def git(repo: Path, *args: str) -> str:
    result = run("git", *args, cwd=repo)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_adapter_parses_with_platform_bash() -> None:
    result = run("/bin/bash", "-n", ADAPTER, cwd=ADAPTER.parent)
    assert result.returncode == 0, result.stderr


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    tmp_path.chmod(0o700)
    repo, tools = tmp_path / "repo", tmp_path / "tools"
    repo.mkdir()
    tools.mkdir()
    executable(
        tools / "python3",
        f'#!/bin/sh\ngit_dir=$(/usr/bin/git rev-parse --git-dir 2>/dev/null || printf .git)\n'
        f'/usr/bin/env > "$git_dir/bootstrap-env.log"\nexec "{sys.executable}" "$@"\n',
    )
    graph = repo / "graphify-out"
    (graph / "cache/ast/v0.9.50-s2").mkdir(parents=True)
    (graph / ".gitignore").write_text("/graph.json\n")
    (graph / "GRAPH_REPORT.md").write_text("# old\n")
    (graph / "cost.json").write_text("{}\n")
    graph_content = b'{"nodes":[{"id":"a"}],"links":[]}\n'
    (graph / "graph.json.dvc").write_text(
        "outs:\n"
        f"- md5: {hashlib.md5(graph_content, usedforsecurity=False).hexdigest()}\n"
        f"  size: {len(graph_content)}\n"
        "  hash: md5\n"
        "  path: graph.json\n"
    )
    (graph / "manifest.json").write_text('{"a.py":{"ast_hash":"warm"}}\n')
    (graph / "graph.json").write_bytes(graph_content)
    (graph / "cache/ast/v0.9.50-s2/warm.json").write_text('{"nodes":[]}\n')
    (repo / "a.py").write_text("value = 1\n")
    (repo / "outside.txt").write_text("clean\n")

    executable(
        tools / "graphify",
        """#!/bin/sh
set -eu
if [ "${1:-}" = --version ]; then
  [ ! -f VERSION_WARNING ] || printf 'warning before\\n' >&2
  printf 'graphify %s\\n' "$(cat VERSION 2>/dev/null || printf 0.9.50)"
  [ ! -f VERSION_WARNING_AFTER ] || printf 'warning after\\n' >&2
  exit 0
fi
git_dir=$(git rev-parse --git-dir)
printf '%s\\n' "$*" >> "$git_dir/graphify.log"
env | LC_ALL=C sort > "$git_dir/graphify.env"
[ ! -f FAIL_UPDATE ] || exit 41
[ ! -f SLOW_UPDATE ] || /bin/sleep 0.2
head=$(git rev-parse HEAD)
revision=$(printf '%s' "$head" | cut -c1-8)
[ ! -f STALE_REPORT ] || revision=deadbeef
[ ! -f NO_GRAPH_CHANGE ] || {
  printf 'No code-graph changes detected\\n'
  exit 0
}
[ ! -f TOPOLOGY_NO_CHANGE ] || {
  printf 'No code-graph topology changes detected; outputs left untouched.\\n'
  exit 0
}
[ ! -f NO_RELEVANT_CHANGE ] || {
  printf '[graphify watch] No relevant changes; graphify-out left untouched.\\n'
  exit 0
}
cat > graphify-out/GRAPH_REPORT.md <<EOF
# Graph Report
- Built from commit: \\`$revision\\`
EOF
[ ! -f MALFORMED_GRAPH ] || { printf 'bad\\n' > graphify-out/graph.json; exit 0; }
[ ! -f ZERO_GRAPH ] || { printf '{"nodes":[],"links":[]}\\n' > graphify-out/graph.json; exit 0; }
printf '{"nodes":[{"id":"a"}],"links":[]}\\n' > graphify-out/graph.json
printf '{}\\n' > graphify-out/cost.json
printf '{"a.py":{"ast_hash":"warm"},"b.py":{"ast_hash":"cold"}}\\n' > graphify-out/manifest.json
""",
    )
    executable(tools / "python", '#!/bin/sh\n[ ! -f MISSING_EXTRA ]\n')
    executable(
        tools / "uv",
        """#!/bin/sh
set -eu
git_dir=$(git rev-parse --git-dir)
printf '%s\\n' "$*" >> "$git_dir/uv.log"
case "$*" in
  "run --frozen --offline dvc checkout graphify-out/graph.json")
    [ ! -f FAIL_DVC_CHECKOUT ] || exit 43
    [ -f graphify-out/graph.json ] || printf '{"nodes":[{"id":"a"}],"links":[]}\\n' > graphify-out/graph.json ;;
  "run --frozen --offline dvc add graphify-out/graph.json")
    [ ! -f FAIL_DVC_ADD ] || exit 42
    printf 'new-pointer\\n' > graphify-out/graph.json.dvc
    git add graphify-out/graph.json.dvc
    [ ! -f WRITE_OUTSIDE ] || printf 'changed\\n' > outside.txt
    [ ! -f STAGE_OUTSIDE ] || { printf 'staged\\n' > outside.txt; git add outside.txt; } ;;
  *) exit 43 ;;
esac
""",
    )
    executable(
        tools / "env",
        '#!/bin/sh\ngit_dir=$(git rev-parse --git-dir)\n/usr/bin/env > "$git_dir/shadow-env.log"\n/usr/bin/env\n',
    )
    for name in ("dirname", "mkdir", "cp", "mktemp", "chmod", "rm", "mv"):
        executable(tools / name, "#!/bin/sh\nexit 97\n")
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture")
    env = {**os.environ, "PATH": f"{tools}:{os.environ['PATH']}",
           "DBSCTR_GRAPHIFY_VERSION": "0.9.50", "GEMINI_API_KEY": "forbidden",
           "AWS_PROFILE": "forbidden", "HTTPS_PROXY": "http://forbidden.invalid", "PYTHONHASHSEED": "1234"}
    return repo, env


def adapter(repo: Path, env: dict[str, str], output: Path, mode: str = "check"):
    return run(
        ADAPTER, "--output-dir", output, cwd=repo,
        env={**env, "DBSCTR_GRAPHIFY_MODE": mode},
    )


def test_adapter_runs_with_platform_bash(project, tmp_path: Path) -> None:
    repo, env = project
    result = run(
        "/bin/bash", ADAPTER, "--output-dir", tmp_path / "output", cwd=repo,
        env={**env, "DBSCTR_GRAPHIFY_MODE": "check"},
    )
    assert result.returncode == 0, result.stderr


def test_check_publishes_bounded_output_and_sanitizes_environment(
    project: tuple[Path, dict[str, str]], tmp_path: Path,
) -> None:
    repo, env = project
    output = tmp_path / "output"
    result = adapter(repo, env, output)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"cache_hits": 1, "cache_misses": 1}
    assert sorted(path.name for path in output.iterdir()) == [
        ".gitignore", "GRAPH_REPORT.md", "cost.json", "graph.json",
        "graph.json.dvc", "manifest.json",
    ]
    assert git(repo, "rev-parse", "HEAD") in (output / "GRAPH_REPORT.md").read_text()
    assert "PYTHONHASHSEED=0\n" in (repo / ".git/graphify.env").read_text()
    for log in ("graphify.env", "shadow-env.log", "bootstrap-env.log"):
        text = (repo / ".git" / log).read_text()
        assert "GEMINI_API_KEY=" not in text
        assert "AWS_PROFILE=" not in text
        assert "HTTPS_PROXY=" not in text


def test_check_uses_only_local_dvc(project, tmp_path: Path) -> None:
    repo, env = project
    (repo / "graphify-out/graph.json").unlink()
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode == 0, result.stderr
    assert (repo / ".git/uv.log").read_text().splitlines() == [
        "run --frozen --offline dvc checkout graphify-out/graph.json",
        "run --frozen --offline dvc add graphify-out/graph.json",
    ]


def test_check_restores_pointer_matched_primary_graph(project, tmp_path: Path) -> None:
    repo, env = project
    (repo / "FAIL_DVC_CHECKOUT").write_text("1\n")
    git(repo, "add", "FAIL_DVC_CHECKOUT")
    git(repo, "commit", "-qm", "missing local dvc")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", str(linked))
    result = adapter(linked, env, tmp_path / "output")
    assert result.returncode == 0, result.stderr
    assert (linked / ".git").is_file()


@pytest.mark.parametrize("case", ["duplicate", "misassociated"])
def test_primary_graph_fallback_rejects_malformed_pointer(project, tmp_path: Path, case: str) -> None:
    repo, env = project
    (repo / "FAIL_DVC_CHECKOUT").write_text("1\n")
    git(repo, "add", "FAIL_DVC_CHECKOUT")
    git(repo, "commit", "-qm", "missing local dvc")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", str(linked))
    pointer = linked / "graphify-out/graph.json.dvc"
    if case == "duplicate":
        pointer.write_text(pointer.read_text() + pointer.read_text())
    else:
        pointer.write_text(pointer.read_text().replace("path: graph.json", "path: other.json"))
    result = adapter(linked, env, tmp_path / "output")
    assert result.returncode != 0
    assert "invalid graph.json.dvc pointer" in result.stderr
    assert not (linked / ".git/graphify.log").exists()


@pytest.mark.parametrize("case", ["symlink", "writable"])
def test_primary_graph_fallback_rejects_unsafe_parent(project, tmp_path: Path, case: str) -> None:
    repo, env = project
    (repo / "FAIL_DVC_CHECKOUT").write_text("1\n")
    git(repo, "add", "FAIL_DVC_CHECKOUT")
    git(repo, "commit", "-qm", "missing local dvc")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", str(linked))
    graph = repo / "graphify-out"
    if case == "symlink":
        moved = tmp_path / "primary-graph"
        graph.rename(moved)
        graph.symlink_to(moved, target_is_directory=True)
    else:
        graph.chmod(0o777)
    result = adapter(linked, env, tmp_path / "output")
    assert result.returncode != 0
    assert "local DVC checkout failed" in result.stderr
    assert not (linked / ".git/graphify.log").exists()


@pytest.mark.parametrize("control", ["NO_GRAPH_CHANGE", "TOPOLOGY_NO_CHANGE", "NO_RELEVANT_CHANGE"])
@pytest.mark.parametrize("revision_length", [8, 40])
def test_no_change_normalizes_ancestor_report(project, tmp_path: Path, control: str, revision_length: int) -> None:
    repo, env = project
    prior = git(repo, "rev-parse", "HEAD")
    (repo / control).write_text("1\n")
    (repo / "graphify-out/GRAPH_REPORT.md").write_text(
        f"# Graph Report\n- Built from commit: `{prior[:revision_length]}`\n"
    )
    git(repo, "add", control, "graphify-out/GRAPH_REPORT.md")
    git(repo, "commit", "-qm", "topology unchanged")
    output = tmp_path / "output"
    result = adapter(repo, env, output)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "HEAD") in (output / "GRAPH_REPORT.md").read_text()


@pytest.mark.parametrize("control", ["NO_GRAPH_CHANGE", "TOPOLOGY_NO_CHANGE", "NO_RELEVANT_CHANGE"])
@pytest.mark.parametrize("case", ["malformed", "missing", "duplicate", "non_ancestor"])
def test_no_change_rejects_invalid_report_provenance(project, tmp_path: Path, control: str, case: str) -> None:
    repo, env = project
    revision = git(repo, "rev-parse", "HEAD")
    if case == "malformed":
        revision = "HEAD"
    elif case == "missing":
        revision = "0" * 40
    elif case == "non_ancestor":
        revision = git(repo, "commit-tree", git(repo, "rev-parse", "HEAD^{tree}"), "-m", "unrelated fixture")
    text = f"# Graph Report\n- Built from commit: `{revision}`\n"
    if case == "duplicate":
        text += f"- Built from commit: `{revision}`\n"
    (repo / "graphify-out/GRAPH_REPORT.md").write_text(text)
    (repo / control).write_text("1\n")
    output = tmp_path / "output"
    result = adapter(repo, env, output)
    assert result.returncode != 0
    assert not output.exists()
    assert not (repo / ".git/uv.log").exists()
    if case == "missing":
        assert "does not exist" in result.stderr
    elif case == "non_ancestor":
        assert "not an ancestor" in result.stderr


@pytest.mark.parametrize("value", [{"nodes": [], "partial": True}, {"nodes": [], "error": "failed"}, []])
def test_legacy_incomplete_or_invalid_cache_is_not_a_hit(project, tmp_path: Path, value) -> None:
    repo, env = project
    (repo / "graphify-out/cache/ast/v0.9.50-s2/warm.json").write_text(json.dumps(value))
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"cache_hits": 0, "cache_misses": 2}


@pytest.fixture
def native_project(project, tmp_path: Path):
    raw = os.environ.get("DBSCTR_GRAPHIFY_NATIVE_TEST_EXECUTABLE")
    if not raw:
        pytest.skip("set DBSCTR_GRAPHIFY_NATIVE_TEST_EXECUTABLE to an already-qualified graphify 0.9.97 executable")
    cli = Path(raw)
    assert cli.is_absolute() and cli.is_file(), "native test executable must be an existing absolute path"
    cli = cli.resolve()
    python = cli.parent / "python"
    assert python.is_file(), "native Graphify interpreter must accompany executable"
    repo, original_env = project
    home, temporary = tmp_path / "native-home", tmp_path / "native-tmp"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    env = {"PATH": original_env["PATH"], "HOME": str(home), "TMPDIR": str(temporary),
           "LANG": "C.UTF-8", "LC_ALL": "C", "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
           "DBSCTR_GRAPHIFY_VERSION": "0.9.97"}
    version = run(cli, "--version", cwd=repo, env=env)
    assert version.returncode == 0 and version.stdout.strip() == "graphify 0.9.97", version.stderr
    tools = tmp_path / "tools"
    (tools / "graphify").unlink()
    (tools / "graphify").symlink_to(cli)
    (repo / "a.py").write_text("from b import double\n\ndef calculate(value):\n    return double(value)\n")
    (repo / "b.py").write_text("def double(value):\n    return value * 2\n")
    (repo / "alias.inc").write_text("def remapped(value):\n    return value + 1\n")
    (repo / ".graphifyrc").write_text("language.inc=python\n")
    git(repo, "add", "a.py", "b.py", "alias.inc", ".graphifyrc")
    git(repo, "commit", "-qm", "native code-only fixture")
    return repo, env, cli, python


@pytest.mark.parametrize("case", ["cold", "warm", "partial", "wrong_generation", "error", "no_change", "topology_no_change"])
def test_native_candidate_adapter_cache_and_provenance(native_project, tmp_path: Path, case: str) -> None:
    repo, env, cli, python = native_project
    graph = repo / "graphify-out"
    # Native manifest also stamps outside.txt, which has no AST extractor: always a miss.
    expected = {"cache_hits": 0, "cache_misses": 4}
    if case != "cold":
        prepared = run(cli, "update", ".", cwd=repo, env=env)
        (tmp_path / "native-prepare.stdout").write_text(prepared.stdout)
        (tmp_path / "native-prepare.stderr").write_text(prepared.stderr)
        assert prepared.returncode == 0, prepared.stderr
        expected = {"cache_hits": 3, "cache_misses": 1}
        key = run(python, "-I", "-B", "-c", """
from pathlib import Path
from graphify import cache
from graphify.rcfile import activate_language_overrides, cache_salt
root = Path.cwd()
activate_language_overrides(root)
path = root / 'alias.inc'
key = cache._salted_key(cache.file_hash(path, root), cache_salt(path))
print(cache.cache_dir(root) / (key + '.json'))
""", cwd=repo, env=env)
        assert key.returncode == 0, key.stderr
        entry = Path(key.stdout.strip())
        assert entry.is_file()
        assert entry.parent.name.startswith("v0.9.97-s29-g")
        manifest = json.loads((graph / "manifest.json").read_text())
        assert manifest["alias.inc"]["ast_hash"] != entry.stem
        if case in {"partial", "error"}:
            original = entry.read_bytes()
            (tmp_path / "native-cache-before.json").write_bytes(original)
            value = json.loads(original)
            value[case] = True if case == "partial" else "failed fixture extraction"
            entry.write_text(json.dumps(value))
            expected = {"cache_hits": 2, "cache_misses": 2}
        elif case == "wrong_generation":
            entry.parent.rename(entry.parent.with_name("v0.9.97-s28-gunqualified"))
            expected = {"cache_hits": 0, "cache_misses": 4}
        if case in {"warm", "partial", "wrong_generation"}:
            # Retain the state preimage but force actual native extraction, not its early no-change shortcut.
            state = graph / ".graphify_build_state.json"
            state.rename(state.with_suffix(".retained"))
        if case in {"no_change", "topology_no_change"}:
            if case == "no_change":
                (repo / ".gitignore").write_text("# fixture metadata only\n")
                changed = ".gitignore"
            else:
                with (repo / "a.py").open("a") as writer:
                    writer.write("\n# unchanged graph topology\n")
                changed = "a.py"
                expected = {"cache_hits": 2, "cache_misses": 2}
            git(repo, "add", changed)
            git(repo, "commit", "-qm", "native unchanged graph with new HEAD")
    output = tmp_path / "output"
    result = adapter(repo, env, output)
    (tmp_path / "native-adapter.stdout").write_text(result.stdout)
    (tmp_path / "native-adapter.stderr").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected
    assert {path.name for path in output.iterdir()} == {
        ".gitignore", "GRAPH_REPORT.md", "cost.json", "graph.json", "graph.json.dvc", "manifest.json",
    }
    assert (output / "cost.json").read_bytes() == b"{}\n", "preserve canonical cost baseline, never invent a receipt"
    report = (output / "GRAPH_REPORT.md").read_text()
    assert f"- Built from commit: `{git(repo, 'rev-parse', 'HEAD')}`\n" in report
    value = json.loads((output / "graph.json").read_text())
    assert value["nodes"] and value["links"]
    assert (repo / ".git/uv.log").read_text().splitlines() == [
        "run --frozen --offline dvc add graphify-out/graph.json",
    ]


def test_native_snapshot_counts_only_valid_sources_in_final_manifest(native_project, tmp_path: Path) -> None:
    repo, env, cli, python = native_project
    prepared = run(cli, "update", ".", cwd=repo, env=env)
    assert prepared.returncode == 0, prepared.stderr
    setup = run(python, "-I", "-B", "-c", """
import json
from pathlib import Path
from graphify import cache
from graphify.detect import _md5_file
root = Path.cwd()
manifest_path = root / 'graphify-out/manifest.json'
manifest = json.loads(manifest_path.read_text())
for name in ('outside.txt', '.aws/credentials.py', 'missing.py', '../outside.py', 'error.py', 'script.js', 'excluded.py'):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('def fixture(): pass\\n' if path.suffix == '.py' else 'fixture only\\n')
    cache.save_cached(path, {'nodes': [], 'edges': []}, root)
    manifest[name] = {'ast_hash': _md5_file(path)}
    if name == 'missing.py':
        path.unlink()
    elif name == 'error.py':
        entry = cache.cache_dir(root) / (cache.file_hash(path, root) + '.json')
        value = json.loads(entry.read_text())
        value['error'] = 'failed fixture extraction'
        entry.write_text(json.dumps(value))
(root / '.graphifyignore').write_text('excluded.py\\n')
del manifest['a.py']
manifest_path.write_text(json.dumps(manifest))
""", cwd=repo, env=env)
    assert setup.returncode == 0, setup.stderr
    tools = tmp_path / "tools"
    (tools / "graphify").unlink()
    executable(tools / "graphify", """#!/bin/sh
if [ "${1:-}" = --version ]; then printf 'graphify 0.9.97\\n'; exit 0; fi
printf '[graphify watch] No relevant changes; graphify-out left untouched.\\n'
""")
    executable(tools / "python", f'#!/bin/sh\nexec "{python}" "$@"\n')
    output = tmp_path / "output"
    result = adapter(repo, env, output)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"cache_hits": 2, "cache_misses": 7}


@pytest.mark.parametrize("case", ["unsafe_output", "unsafe_graph"])
def test_native_cache_waits_for_path_and_graph_guards(native_project, tmp_path: Path, case: str) -> None:
    repo, env, _, _ = native_project
    output = tmp_path / "output"
    if case == "unsafe_output":
        output.mkdir()
    else:
        (repo / "graphify-out/cache").chmod(0o777)
    before = {path.relative_to(repo): path.read_bytes() for path in (repo / "graphify-out").rglob("*") if path.is_file()}
    result = adapter(repo, env, output)
    assert result.returncode != 0
    after = {path.relative_to(repo): path.read_bytes() for path in (repo / "graphify-out").rglob("*") if path.is_file()}
    assert after == before


@pytest.mark.parametrize("name", ["graphify.py", "boto3.py", "tree_sitter_sql.py"])
def test_native_cache_imports_selected_runtime_not_project_modules(native_project, tmp_path: Path, name: str) -> None:
    repo, env, _, _ = native_project
    (repo / name).write_text("raise RuntimeError('project module must not be imported')\n")
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("case", ["malformed", "non_ancestor"])
def test_native_no_change_refuses_invalid_provenance(native_project, tmp_path: Path, case: str) -> None:
    repo, env, cli, _ = native_project
    prepared = run(cli, "update", ".", cwd=repo, env=env)
    assert prepared.returncode == 0, prepared.stderr
    revision = "HEAD" if case == "malformed" else git(
        repo, "commit-tree", git(repo, "rev-parse", "HEAD^{tree}"), "-m", "unrelated native fixture",
    )
    (repo / "graphify-out/GRAPH_REPORT.md").write_text(f"# Graph Report\n- Built from commit: `{revision}`\n")
    output = tmp_path / "output"
    result = adapter(repo, env, output)
    assert result.returncode != 0
    assert not output.exists()
    assert not (repo / ".git/uv.log").exists()
    assert ("not an ancestor" if case == "non_ancestor" else "identity is invalid") in result.stderr


def test_native_finalize_failure_restores_graph_and_index(native_project) -> None:
    repo, env, cli, _ = native_project
    prepared = run(cli, "update", ".", cwd=repo, env=env)
    assert prepared.returncode == 0, prepared.stderr
    (repo / "FAIL_DVC_ADD").write_text("1\n")
    git(repo, "add", "graphify-out", "FAIL_DVC_ADD")
    git(repo, "commit", "-qm", "native finalize baseline")
    graph = repo / "graphify-out"
    before = {path.relative_to(graph): path.read_bytes() for path in graph.rglob("*") if path.is_file()}
    index = repo / ".git/index"
    index_before = index.read_bytes()
    result = adapter(repo, env, graph, "finalize")
    assert result.returncode != 0
    assert "DVC metadata staging failed" in result.stderr
    assert {path.relative_to(graph): path.read_bytes() for path in graph.rglob("*") if path.is_file()} == before
    assert index.read_bytes() == index_before
    assert not git(repo, "status", "--porcelain=v1", "--", "graphify-out")


def test_finalize_requires_exact_clean_canonical_path(project) -> None:
    repo, env = project
    result = adapter(repo, env, repo / "graphify-out", "finalize")
    assert result.returncode == 0, result.stderr
    assert git(repo, "diff", "--cached", "--name-only") == "graphify-out/graph.json.dvc"


@pytest.mark.parametrize("control", ["FAIL_DVC_ADD", "MALFORMED_GRAPH", "STALE_REPORT"])
def test_finalize_failure_restores_graph_and_index(project, control: str) -> None:
    repo, env = project
    (repo / control).write_text("1\n")
    git(repo, "add", control)
    git(repo, "commit", "-qm", "finalize failure")
    graph = repo / "graphify-out"
    before = {path.relative_to(graph): path.read_bytes() for path in graph.rglob("*") if path.is_file()}
    result = adapter(repo, env, graph, "finalize")
    assert result.returncode != 0
    after = {path.relative_to(graph): path.read_bytes() for path in graph.rglob("*") if path.is_file()}
    assert after == before
    assert not git(repo, "diff", "--cached", "--name-only")
    assert not git(repo, "status", "--porcelain=v1", "--", "graphify-out")


@pytest.mark.parametrize("case", ["existing", "inside_repo", "symlink_parent"])
def test_check_rejects_unsafe_output(project, tmp_path: Path, case: str) -> None:
    repo, env = project
    output = tmp_path / "output"
    if case == "existing":
        output.mkdir()
    elif case == "inside_repo":
        output = repo / "output"
    else:
        real = tmp_path / "real"
        real.mkdir()
        parent = tmp_path / "link"
        parent.symlink_to(real, target_is_directory=True)
        output = parent / "output"
    result = adapter(repo, env, output)
    assert result.returncode != 0
    assert not (repo / ".git/graphify.log").exists()


@pytest.mark.parametrize("control", ["VERSION_WARNING", "VERSION_WARNING_AFTER"])
def test_version_warnings_do_not_mask_exact_match(project, tmp_path: Path, control: str) -> None:
    repo, env = project
    (repo / control).write_text("1\n")
    git(repo, "add", control)
    git(repo, "commit", "-qm", "warning")
    assert adapter(repo, env, tmp_path / "output").returncode == 0


@pytest.mark.parametrize("control", ["VERSION", "MISSING_EXTRA"])
def test_runtime_mismatch_fails_before_mutation(project, tmp_path: Path, control: str) -> None:
    repo, env = project
    (repo / control).write_text("0.9.49\n")
    git(repo, "add", control)
    git(repo, "commit", "-qm", "mismatch")
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode != 0
    assert not (repo / ".git/graphify.log").exists()


@pytest.mark.parametrize("name", ["graph.json", "GRAPH_REPORT.md", "manifest.json", "cache"])
def test_existing_graph_symlink_fails_before_tools(project, tmp_path: Path, name: str) -> None:
    repo, env = project
    path = repo / "graphify-out" / name
    shutil.rmtree(path) if path.is_dir() else path.unlink()
    path.symlink_to(tmp_path / "outside", target_is_directory=name == "cache")
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode != 0
    assert not (repo / ".git/graphify.log").exists()
    assert not (repo / ".git/uv.log").exists()


def test_writable_graph_tree_fails_before_tools(project, tmp_path: Path) -> None:
    repo, env = project
    cache = repo / "graphify-out/cache"
    cache.chmod(0o777)
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode != 0
    assert "unsafe path" in result.stderr
    assert not (repo / ".git/graphify.log").exists()


def test_missing_local_dvc_fails_before_graphify(project, tmp_path: Path) -> None:
    repo, env = project
    (repo / "graphify-out/graph.json").unlink()
    (repo / "FAIL_DVC_CHECKOUT").write_text("1\n")
    git(repo, "add", "FAIL_DVC_CHECKOUT")
    git(repo, "commit", "-qm", "missing dvc")
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode != 0
    assert "local DVC checkout failed" in result.stderr
    assert not (repo / ".git/graphify.log").exists()


@pytest.mark.parametrize("control", ["MALFORMED_GRAPH", "ZERO_GRAPH"])
def test_invalid_graph_fails_before_dvc_add(project, tmp_path: Path, control: str) -> None:
    repo, env = project
    (repo / control).write_text("1\n")
    git(repo, "add", control)
    git(repo, "commit", "-qm", "invalid graph")
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode != 0
    assert not (repo / ".git/uv.log").exists()


@pytest.mark.parametrize("control", ["WRITE_OUTSIDE", "STAGE_OUTSIDE"])
def test_changes_outside_graph_output_are_rejected(project, tmp_path: Path, control: str) -> None:
    repo, env = project
    (repo / control).write_text("1\n")
    git(repo, "add", control)
    git(repo, "commit", "-qm", "outside")
    result = adapter(repo, env, tmp_path / "output")
    assert result.returncode != 0
    assert not (tmp_path / "output").exists()


def test_atomic_publication_preserves_racing_target(project, tmp_path: Path) -> None:
    repo, env = project
    (repo / "SLOW_UPDATE").write_text("1\n")
    git(repo, "add", "SLOW_UPDATE")
    git(repo, "commit", "-qm", "slow")
    output = tmp_path / "output"
    process = subprocess.Popen(
        [str(ADAPTER), "--output-dir", str(output)], cwd=repo,
        env={**env, "DBSCTR_GRAPHIFY_MODE": "check"}, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    for _ in range(100):
        if (repo / ".git/graphify.log").exists():
            break
        time.sleep(0.01)
    output.mkdir()
    (output / "owner").write_text("racer\n")
    stdout, _ = process.communicate(timeout=30)
    assert process.returncode != 0
    assert not stdout
    assert (output / "owner").read_text() == "racer\n"


def test_invocation_is_strict(project, tmp_path: Path) -> None:
    repo, env = project
    assert run(ADAPTER, "--output-dir", cwd=repo, env=env).returncode != 0
    assert run(ADAPTER, "--output-dir", tmp_path / "out", "extra", cwd=repo, env=env).returncode != 0
    assert run(ADAPTER, "--output-dir", tmp_path / "out", cwd=repo, env=env).returncode != 0
