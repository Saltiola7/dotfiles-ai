from __future__ import annotations

import json
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


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    tmp_path.chmod(0o700)
    repo, tools = tmp_path / "repo", tmp_path / "tools"
    repo.mkdir()
    tools.mkdir()
    executable(
        tools / "python3",
        f'#!/bin/sh\n/usr/bin/env > .git/bootstrap-env.log\nexec "{sys.executable}" "$@"\n',
    )
    graph = repo / "graphify-out"
    (graph / "cache/ast/v0.9.50-s2").mkdir(parents=True)
    (graph / ".gitignore").write_text("/graph.json\n")
    (graph / "GRAPH_REPORT.md").write_text("# old\n")
    (graph / "cost.json").write_text("{}\n")
    (graph / "graph.json.dvc").write_text("old\n")
    (graph / "manifest.json").write_text('{"a.py":{"ast_hash":"warm"}}\n')
    (graph / "graph.json").write_text(
        '{"nodes":[{"id":"a"}],"links":[]}\n'
    )
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
           "AWS_PROFILE": "forbidden", "HTTPS_PROXY": "http://forbidden.invalid"}
    return repo, env


def adapter(repo: Path, env: dict[str, str], output: Path, mode: str = "check"):
    return run(
        ADAPTER, "--output-dir", output, cwd=repo,
        env={**env, "DBSCTR_GRAPHIFY_MODE": mode},
    )


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
