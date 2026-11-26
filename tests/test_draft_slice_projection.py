"""Exercise Discovery imports against fixed local Git objects."""
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "private_dot_config/dotfiles-ai"))
from integration_coordinator.draft_slice_projection import project_artifacts


@pytest.fixture
def repository(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-c", "user.name=Test", "-c",
                                        "user.email=test@example.org", *args],
                                       cwd=tmp_path, text=True).strip()

    git("init", "-q")
    docs = tmp_path / "docs/slice"
    docs.mkdir(parents=True)
    (docs / "stable.md").write_text("base document")
    git("add", "docs")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")

    def source(text):
        for name, body in {"input.md": text, "contract.md": "[stable](stable.md#body)",
                           "sibling.md": "other slice", "evidence.json": "{}"}.items():
            (docs / name).write_text(body)
        (docs / "alias.md").symlink_to("contract.md")
        git("add", "docs")
        git("commit", "-qm", "Discovery")
        head = git("rev-parse", "HEAD")
        (docs / "input.md").write_text("[dirty](sibling.md)")
        return head

    return tmp_path, git, base, source


def test_only_reachable_committed_documents(repository):
    root, git, base, source = repository
    head = source("[contract][c]\n\n[c]: contract.md\n[unused]: evidence.json\n"
                  "```\n[example](sibling.md)\n```\n")
    result = project_artifacts(root, base_head=base, source_commit=head, declared=["docs/slice/input.md"])
    paths = ["docs/slice/contract.md", "docs/slice/input.md"]
    assert result == [{"path": name, "blob": git("rev-parse", head + ":" + name),
                       "mode": "100644"} for name in paths]
    assert git("rev-parse", "HEAD") == head
    assert (root / paths[-1]).read_text() == "[dirty](sibling.md)"


@pytest.mark.parametrize("link", [
    "[missing](not-in-git.md)", "[alias](alias.md)", "[sibling](sibling.md)",
    "[unsafe](../../evidence.json)", "[missing][unbound]",
    "[contract][c]\n\n[c]: contract.md\n[C]: sibling.md",
])
def test_invalid_required_dependency_blocks_slice(repository, link):
    root, _, base, source = repository
    with pytest.raises(ValueError):
        project_artifacts(root, base_head=base, source_commit=source(link),
                          declared=["docs/slice/input.md"], forbidden=["docs/slice/sibling.md"])


def test_protected_change_to_dependency_blocks_projection(repository):
    root, git, base, source = repository
    head = source("[contract](contract.md)")
    git("checkout", "--detach", "-fq", base)
    (root / "docs/slice/contract.md").write_text("protected content")
    git("add", "docs")
    git("commit", "-qm", "protected")
    with pytest.raises(ValueError, match="conflicts"):
        project_artifacts(root, base_head=git("rev-parse", "HEAD"), source_commit=head,
                          declared=["docs/slice/input.md"])
