"""Exact section authority over synthetic committed Markdown."""

import json

import pytest

from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture, git


def test_projection_preserves_only_selected_bytes(initiative):
    core, *_ = initiative
    first = b"<!-- dbsctr:begin first -->\r\nBody \r\n<!-- dbsctr:end first -->\r\n"
    second = b"<!-- dbsctr:begin second -->\nOther\n<!-- dbsctr:end second -->\n"
    selected = ("first", "second")
    before = core.initiative_section_projection(b"above\n" + first + b"gap\n" + second, selected)
    assert before == core.initiative_section_projection(first + second + b"below\n", selected)
    assert before != core.initiative_section_projection(
        first.replace(b"Body \r\n", b"Body\r\n") + second, selected)


@pytest.mark.parametrize("raw", [
    b"unmarked\n",
    b"<!-- dbsctr:begin first -->\n",
    b"<!-- dbsctr:begin First -->\n<!-- dbsctr:end First -->\n",
    b"<!-- dbsctr:begin first -->\n<!-- dbsctr:begin nested -->\n"
    b"<!-- dbsctr:end nested -->\n<!-- dbsctr:end first -->\n",
    b"<!-- dbsctr:begin first -->\n<!-- dbsctr:end first -->\n" * 2,
])
def test_invalid_selected_document_refuses(initiative, raw):
    core, *_ = initiative
    with pytest.raises(RuntimeError, match="section"):
        core.initiative_section_projection(raw, ("first",))


def test_committed_section_receipt_and_target_only_drift(initiative):
    core, root, *_ = initiative
    manifest = root / "docs/initiatives/test/MANIFEST.json"
    name = "docs/specs/test/shared.md"
    document = root / name
    section = "<!-- dbsctr:begin body -->\nApproved\n<!-- dbsctr:end body -->\n"
    document.write_text("Above\n" + section)
    value = json.loads(manifest.read_bytes())
    value["slices"][0]["section_artifacts"] = {
        "schema_version": 1, "documents": [{"path": name, "sections": ["body"]}],
    }
    manifest.write_text(json.dumps(value))
    git(root, "add", "--", name, str(manifest.relative_to(root)))
    git(root, "commit", "-m", "Select a shared section")
    prior = git(root, "rev-parse", "HEAD").strip()
    receipt = core.initiative_receipt(manifest, "slice-a", root)
    receipt["manifest_path"] = str(manifest.relative_to(root))
    record = {"initiative": receipt}
    assert receipt["section_authority"]["documents"][0]["path"] == name
    assert name in receipt["artifacts"]
    document.write_text(section + "Below\n")
    git(root, "add", "--", name)
    git(root, "commit", "-m", "Independent target text")
    target = git(root, "rev-parse", "HEAD").strip()
    core.require_initiative_section_tree(root, record, target, prior=prior, target=target)
    with pytest.raises(RuntimeError, match="out-of-scope"):
        core.require_initiative_section_tree(root, record, target, prior=prior)
    document.write_text(section.replace("Approved", "Changed"))
    git(root, "add", "--", name)
    git(root, "commit", "-m", "Change approved bytes")
    with pytest.raises(RuntimeError, match="authority changed"):
        core.require_initiative_section_tree(root, record, "HEAD")
    document.write_text(section)
    document.chmod(0o755)
    git(root, "add", "--chmod=+x", "--", name)
    git(root, "commit", "-m", "Change mode")
    with pytest.raises(RuntimeError, match="authority changed"):
        core.require_initiative_section_tree(root, record, "HEAD")
    value["statements"][0]["artifacts"].append(name)
    manifest.write_text(json.dumps(value))
    git(root, "add", "--", str(manifest.relative_to(root)))
    git(root, "commit", "-m", "Select whole document")
    whole = core.initiative_receipt(manifest, "slice-a", root)
    assert name in whole["artifacts"]
    assert "sections" not in whole["section_authority"]["documents"][0]
    git(root, "mv", "--", name, "docs/specs/test/renamed.md")
    git(root, "commit", "-m", "Rename selected document")
    with pytest.raises(RuntimeError, match="not a regular file"):
        core.require_initiative_section_tree(root, record, "HEAD")
