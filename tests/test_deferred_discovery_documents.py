"""Exact import and custody checks using synthetic Git repositories."""

import json

import pytest

from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture, git


MANIFEST = "docs/initiatives/test/MANIFEST.json"
CURRENT = "docs/specs/test/README.md"
LATER = "docs/specs/other/pointer.md"


def discovery(initiative, *, path=LATER, owner="slice-b", related=True, symlink=False):
    core, root, _, argv, _, plan = initiative
    base = git(root, "rev-parse", "HEAD").strip()
    value = json.loads((root / MANIFEST).read_bytes())
    first = value["slices"][0]
    first["deferred_documents"] = {
        "schema_version": 1, "documents": [{"path": path, "owner": owner}],
    }
    value["slices"].append({
        "id": "slice-b", "context": "test", "state": "captured",
        "requirements": ["INT-001"], "depends_on": ["slice-a"] if related else [],
        "artifacts": [path], "release_group": "release-a",
    })
    value["release_groups"][0]["members"].append("slice-b")
    (root / MANIFEST).write_text(json.dumps(value))
    (root / CURRENT).write_text("Current authority\n")
    if path != CURRENT:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        if symlink:
            (root / path).symlink_to("unrelated.md")
        else:
            (root / path).write_text("Later pointer\n")
    git(root, "add", "--", MANIFEST, CURRENT, path)
    git(root, "commit", "-m", "Mixed Discovery authority")
    args = core.parser().parse_args(argv)
    return core, root, args, core.read_plan(plan), base, value


def selection(core, root, args, plan, base, slice_id="slice-a"):
    receipt = core.initiative_receipt(root / MANIFEST, slice_id, root)
    receipt["manifest_path"] = MANIFEST
    return core.initiative_import_plan(root, root, receipt, plan, base, args)


@pytest.mark.parametrize("path", [LATER, "docs/specs/test/later.md"])
def test_exact_deferral_leaves_only_current_docs_in_import(initiative, path):
    core, root, args, plan, base, _ = discovery(initiative, path=path)
    approved = selection(core, root, args, plan, base)
    assert {item["path"] for item in approved["artifacts"]} == {MANIFEST, CURRENT}
    assert approved["deferred_documents"] == [{
        "path": path, "mode": "100644", "owner": "slice-b",
        "blob": git(root, "rev-parse", f"HEAD:{path}").strip(),
    }]
    assert path not in approved["receipt"]["artifacts"]
    (root / path).write_text("Changed later pointer\n")
    git(root, "commit", "-am", "Change deferred blob")
    changed = selection(core, root, args, plan, base)
    assert approved["artifacts"] == changed["artifacts"]
    assert approved["deferred_documents"] != changed["deferred_documents"]
    assert core.continuation_digest(approved) != core.continuation_digest(changed)


@pytest.mark.parametrize(("options", "error"), [
    ({"owner": "unknown"}, "later owning slice"),
    ({"related": False}, "later owning slice"),
    ({"path": CURRENT}, "overlaps"),
    ({"symlink": True}, "regular"),
    ({"path": "docs/specs/other/config.json"}, "Markdown"),
])
def test_invalid_deferral_refuses(initiative, options, error):
    core, root, args, plan, base, _ = discovery(initiative, **options)
    with pytest.raises(RuntimeError, match=error):
        selection(core, root, args, plan, base)


def test_registration_imports_only_current_authority(initiative, monkeypatch, capsys):
    core, source, _, _, base, _ = discovery(initiative)
    target = source.parent / "deferred-build"
    git(source, "worktree", "add", "-b", "deferred-build", str(target), base)
    git(target, "branch", "--set-upstream-to", "upstream/base")
    receipt = core.initiative_receipt(source / MANIFEST, "slice-a", source)
    _, _, _, argv, _, _ = initiative
    command = argv[:-2]
    command[command.index("--initiative-digest") + 1] = receipt["manifest_digest"]
    command += ["--initiative-source", str(source)]
    monkeypatch.chdir(target)
    core.command_begin(core.parser().parse_args([*command, "--preflight"]))
    preflight = json.loads(capsys.readouterr().out)
    assert preflight["plan"]["deferred_documents"][0]["path"] == LATER
    (source / LATER).write_text("Later pointer revised after preflight\n")
    git(source, "commit", "-am", "Change deferred authority after preflight")
    with pytest.raises(RuntimeError, match="launch plan changed"):
        core.command_begin(core.parser().parse_args([
            *command, "--expected-launch-digest", preflight["launch_digest"], "--approval", "agent-confirmed",
        ]))
    assert git(target, "rev-parse", "HEAD").strip() == base
    assert not (target / LATER).exists()
    core.command_begin(core.parser().parse_args([*command, "--preflight"]))
    preflight = json.loads(capsys.readouterr().out)
    core.command_begin(core.parser().parse_args([
        *command, "--expected-launch-digest", preflight["launch_digest"], "--approval", "agent-confirmed",
    ]))
    _, record = core.load(target)
    assert record["initiative"]["deferred_documents"] == preflight["plan"]["deferred_documents"]
    assert set(git(target, "diff", "--name-only", base, "HEAD").splitlines()) == {MANIFEST, CURRENT}
    assert not (target / LATER).exists()
    core.verify_discovery_import(target, record)
    with pytest.raises(RuntimeError, match="gate credit"):
        core.require_no_deferred_document_credit(record, ["./" + LATER])


def test_unclassified_document_is_not_silently_deferred(initiative):
    core, root, args, plan, base, _ = discovery(initiative)
    (root / LATER).with_name("unowned.md").write_text("Unclassified\n")
    git(root, "add", "--", str((root / LATER).with_name("unowned.md")))
    git(root, "commit", "-m", "Add unclassified source")
    with pytest.raises(RuntimeError, match="outside receipt artifacts"):
        selection(core, root, args, plan, base)


def test_full_source_privacy_check_includes_deferred_bytes(initiative, monkeypatch):
    core, root, args, plan, base, _ = discovery(initiative)
    monkeypatch.setattr(core, "publication_identifier_patterns", lambda: (("synthetic-private-marker",), ("unused-marker",)))
    (root / LATER).write_text("synthetic-private-marker\n")
    git(root, "commit", "-am", "Add synthetic privacy marker")
    with pytest.raises(RuntimeError, match="publication privacy"):
        selection(core, root, args, plan, base)


def test_later_owner_has_fresh_protected_base_conflict_check(initiative):
    core, root, args, plan, base, value = discovery(initiative)
    git(root, "worktree", "add", "--detach", str(root.parent / "protected"), base)
    protected = root.parent / "protected"
    (protected / LATER).parent.mkdir(parents=True, exist_ok=True)
    (protected / LATER).write_text("Independent protected change\n")
    git(protected, "add", "--", LATER)
    git(protected, "commit", "-m", "Advance protected document")
    value["slices"][0]["state"] = "delivered"
    value["slices"][1]["state"] = "ready"
    (root / MANIFEST).write_text(json.dumps(value))
    git(root, "commit", "-am", "Ready later owner")
    with pytest.raises(RuntimeError, match="conflicts with the protected base"):
        selection(core, root, args, plan, git(protected, "rev-parse", "HEAD").strip(), "slice-b")
