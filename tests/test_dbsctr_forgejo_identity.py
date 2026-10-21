"""Identity and Initiative boundaries for the bounded Forgejo local-only slice.

All origins, accounts and Git metadata are synthetic. These tests perform no
credential lookup, Git transport, repository mutation or lifecycle registration.
"""

import copy
import importlib.machinery
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "dot_local/bin/executable_dbsctrctl"
IDENTITY = {
    "provider": "forgejo",
    "origin": "https://forge.example.invalid",
    "repository": "example/project",
}


@pytest.fixture
def helper(monkeypatch):
    loader = importlib.machinery.SourceFileLoader("forgejo_identity_under_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Identity tests must not invoke credentials or transport")

    monkeypatch.setattr(module.subprocess, "run", forbidden)
    return module


def manifest(schema=2):
    repository = copy.deepcopy(IDENTITY) if schema == 2 else "example/project"
    return {
        "schema_version": schema,
        "id": "forgejo-identity",
        "title": "Identity-bound local validation",
        "state": "ready",
        "coordinator_repository": copy.deepcopy(repository),
        "statements": [{
            "id": "INT-001", "kind": "requirement", "text": "Validate the exact repository.",
            "disposition": "ready", "artifacts": ["docs/specs/test/README.md"],
        }],
        "contexts": [{
            "id": "test", "repository": copy.deepcopy(repository), "status": "ready", "depends_on": [],
        }],
        "slices": [{
            "id": "local", "context": "test", "state": "ready", "execution_owner": "build",
            "requirements": ["INT-001"], "depends_on": [],
            "artifacts": ["docs/specs/test/README.md"], "release_group": "local",
        }],
        "release_groups": [{"id": "local", "members": ["local"], "state": "ready"}],
    }


def write_manifest(root, value):
    path = root / "docs/initiatives/forgejo-identity/MANIFEST.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def mock_git_metadata(helper, monkeypatch, root, *, origin=None, dirty=None):
    """Supply committed-document metadata without creating or modifying a Git repo."""
    calls = []
    origin = origin or f"{IDENTITY['origin']}/{IDENTITY['repository']}.git"

    def git(_root, *args, **_kwargs):
        calls.append(args)
        if args[:2] == ("config", "--get-all"):
            return SimpleNamespace(stdout=origin + "\n", stderr="", returncode=0)
        if args[:2] == ("remote", "get-url"):
            return SimpleNamespace(stdout=origin + "\n", stderr="", returncode=0)
        if args[:2] == ("status", "--porcelain=v1"):
            path = args[-1]
            return SimpleNamespace(stdout=" M " + path if path == dirty else "", stderr="", returncode=0)
        if args[:1] == ("rev-parse",):
            return SimpleNamespace(stdout=("a" if args[-1] == "HEAD" else "b") * 40 + "\n",
                                   stderr="", returncode=0)
        if args[:2] == ("cat-file", "-e"):
            return SimpleNamespace(stdout="", stderr="", returncode=0)
        raise AssertionError(f"Unexpected Git operation in identity boundary: {args!r}")

    monkeypatch.setattr(helper, "git", git)
    monkeypatch.setattr(helper, "root_dir", lambda: root)
    return calls


def begin_args(helper, root, expected=None, **overrides):
    expected = copy.deepcopy(IDENTITY) if expected is None else expected
    args = helper.parser().parse_args([
        "begin", "--cycle-id", "identity-local", "--context", "test", "--risk", "critical",
        "--delivery-intent", "local", "--plan", str(root / "plan.json"), "--base-branch", "main",
        "--forge-provider", "forgejo", "--forge-origin", IDENTITY["origin"],
        "--forge-repository", IDENTITY["repository"], "--forge-account", "example-user",
        "--initiative-manifest", "docs/initiatives/forgejo-identity/MANIFEST.json",
        "--initiative-slice", "local", "--initiative-digest", "c" * 64,
        "--expected-plan-digest", "d" * 64,
        "--expected-repository-json", json.dumps(expected), "--preflight",
    ])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def selectors(**overrides):
    values = dict(
        delivery_intent="local", base_branch="main", github_account=None, github_repository=None,
        forge_provider="forgejo", forge_origin=IDENTITY["origin"],
        forge_repository=IDENTITY["repository"], forge_account="example-user",
    )
    return SimpleNamespace(**{**values, **overrides})


def test_schema2_manifest_and_receipt_preserve_typed_authority(helper, tmp_path):
    path = write_manifest(tmp_path, manifest())
    value, _, contexts, _, _, digest = helper.read_initiative_manifest(path)
    assert value["coordinator_repository"] == IDENTITY
    assert contexts["test"]["repository"] == IDENTITY
    receipt = helper.initiative_receipt(path, "local")
    assert receipt["schema_version"] == 2
    assert receipt["coordinator_repository"] == IDENTITY
    assert receipt["repository"] == IDENTITY
    assert receipt["manifest_digest"] == digest
    assert receipt["execution_owner"] == "build"
    assert "account" not in json.dumps(receipt)
    assert "credential_source" not in json.dumps(receipt)


@pytest.mark.parametrize("field,value", [
    ("origin", "https://other.example.invalid"),
    ("origin", "https://forge.example.invalid:8443"),
    ("repository", "example/Project"),
])
def test_schema2_digest_binds_full_identity(helper, tmp_path, field, value):
    original = manifest()
    path = write_manifest(tmp_path, original)
    initial = helper.read_initiative_manifest(path)[-1]
    changed = copy.deepcopy(original)
    changed["contexts"][0]["repository"][field] = value
    assert helper.read_initiative_manifest(write_manifest(tmp_path, changed))[-1] != initial


def test_schema2_mixed_provider_homes_remain_distinct(helper, tmp_path):
    value = manifest()
    value["contexts"][0]["repository"] = {
        "provider": "github", "origin": "https://github.com", "repository": "example/project",
    }
    receipt = helper.initiative_receipt(write_manifest(tmp_path, value), "local")
    assert receipt["coordinator_repository"] == IDENTITY
    assert receipt["repository"]["provider"] == "github"
    assert receipt["repository"] != receipt["coordinator_repository"]


@pytest.mark.parametrize("change", [
    {"provider": "gitlab"}, {"origin": "http://forge.example.invalid"},
    {"origin": "https://user@forge.example.invalid"},
    {"origin": "https://forge.example.invalid/"},
    {"origin": "https://forge.example.invalid/subpath"},
    {"origin": "https://forge.example.invalid?other=1"},
    {"origin": "https://forge.example.invalid#other"},
    {"origin": "https://forge.example.invalid:0"},
    {"origin": "https://forge.example.invalid:65536"},
    {"origin": "https://forge.example.invalid\n"},
    {"repository": "example/../project"}, {"repository": "example/%2fproject"},
    {"repository": "example/project/extra"}, {"account": "example-user"},
    {"credential_source": "osxkeychain"},
])
def test_schema2_rejects_unsafe_or_private_identity_fields(helper, tmp_path, change):
    value = manifest()
    value["contexts"][0]["repository"].update(change)
    with pytest.raises(RuntimeError):
        helper.read_initiative_manifest(write_manifest(tmp_path, value))


@pytest.mark.parametrize("schema,repository", [(1, IDENTITY), (2, "example/project")])
def test_manifest_does_not_guess_identity_schema(helper, tmp_path, schema, repository):
    value = manifest(schema)
    value["contexts"][0]["repository"] = repository
    with pytest.raises(RuntimeError):
        helper.read_initiative_manifest(write_manifest(tmp_path, value))


def test_typed_identity_normalizes_origin_without_collapsing_ports(helper):
    identity = helper.typed_repository_identity({**IDENTITY, "origin": "https://FORGE.example.invalid:443"}, "target")
    assert identity == IDENTITY
    alternate = helper.typed_repository_identity({**IDENTITY, "origin": IDENTITY["origin"] + ":8443"}, "target")
    assert alternate["origin"] == IDENTITY["origin"] + ":8443"
    assert not helper.repository_equal(identity, alternate)


def test_identity_equality_preserves_provider_rules_and_host_boundary(helper):
    assert not helper.repository_equal(IDENTITY, {**IDENTITY, "origin": "https://other.example.invalid"})
    assert not helper.repository_equal(IDENTITY, {**IDENTITY, "repository": "example/Project"})
    github = {"provider": "github", "origin": "https://github.com", "repository": "example/project"}
    assert helper.repository_equal(github, {**github, "repository": "EXAMPLE/Project"})
    assert not helper.repository_equal(IDENTITY, github)


def test_schema2_receipt_binds_committed_coordinator_origin(helper, monkeypatch, tmp_path):
    path = write_manifest(tmp_path, manifest())
    calls = mock_git_metadata(helper, monkeypatch, tmp_path)
    receipt = helper.initiative_receipt(path, "local", tmp_path)
    assert receipt["schema_version"] == 2
    assert receipt["manifest_commit"] == "a" * 40
    assert receipt["manifest_blob"] == "b" * 40
    assert any(args[:2] == ("remote", "get-url") for args in calls)
    assert all(args[0] in {"remote", "config", "status", "rev-parse", "cat-file"} for args in calls)


@pytest.mark.parametrize("origin", [
    "https://other.example.invalid/example/project.git",
    "https://forge.example.invalid:8443/example/project.git",
    "https://forge.example.invalid/example/Project.git",
    "https://github.com/example/project.git",
])
def test_schema2_receipt_rejects_coordinator_aliases(helper, monkeypatch, tmp_path, origin):
    path = write_manifest(tmp_path, manifest())
    mock_git_metadata(helper, monkeypatch, tmp_path, origin=origin)
    with pytest.raises(RuntimeError, match="repository|identity|origin"):
        helper.initiative_receipt(path, "local", tmp_path)


def test_schema2_receipt_keeps_committed_clean_artifact_requirement(helper, monkeypatch, tmp_path):
    path = write_manifest(tmp_path, manifest())
    mock_git_metadata(helper, monkeypatch, tmp_path, dirty="docs/specs/test/README.md")
    with pytest.raises(RuntimeError, match="artifact.*committed.*clean"):
        helper.initiative_receipt(path, "local", tmp_path)


def test_local_selector_accepts_protected_ref_only_as_comparison_base(helper, monkeypatch, tmp_path):
    mock_git_metadata(helper, monkeypatch, tmp_path)
    args = selectors()
    helper.normalize_begin_delivery(tmp_path, args, "main")
    assert args.delivery_intent == "local"
    assert args.github_account is None
    assert args.github_repository is None


@pytest.mark.parametrize("missing", ["forge_provider", "forge_origin", "forge_repository", "forge_account"])
def test_local_selector_requires_complete_explicit_selection(helper, tmp_path, missing):
    with pytest.raises(RuntimeError, match="[Ff]orgejo|selector|selection"):
        helper.normalize_begin_delivery(tmp_path, selectors(**{missing: None}), "topic")


@pytest.mark.parametrize("override", [
    {"github_account": "example-github"}, {"github_repository": "example/project"},
    {"forge_provider": "gitlab"},
])
def test_local_selector_rejects_mixed_or_unknown_provider(helper, tmp_path, override):
    with pytest.raises(RuntimeError, match="[Ff]orgejo|provider|selector|selection|mix"):
        helper.normalize_begin_delivery(tmp_path, selectors(**override), "topic")


@pytest.mark.parametrize("intent", ["draft_pr", "merge", "release", "deploy"])
def test_local_selector_rejects_deferred_delivery_before_authentication(helper, tmp_path, intent):
    with pytest.raises(RuntimeError, match="[Ff]orgejo|local.only|local-only"):
        helper.normalize_begin_delivery(tmp_path, selectors(delivery_intent=intent), "topic")


def test_parser_separates_legacy_and_typed_expected_target(helper, tmp_path, capsys):
    args = begin_args(helper, tmp_path)
    assert args.expected_repository is None
    assert json.loads(args.expected_repository_json) == IDENTITY
    with pytest.raises(SystemExit) as error:
        helper.parser().parse_args([
            "begin", "--cycle-id", "mixed", "--context", "test", "--risk", "critical",
            "--delivery-intent", "local", "--plan", str(tmp_path / "plan.json"),
            "--expected-repository", "example/project", "--expected-repository-json", json.dumps(IDENTITY),
        ])
    assert error.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


def setup_early_begin(helper, monkeypatch, root):
    path = write_manifest(root, manifest())
    receipt = helper.initiative_receipt(path, "local")
    mock_git_metadata(helper, monkeypatch, root)
    monkeypatch.setattr(helper, "require_native_checkout", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helper, "initiative_receipt", lambda *_args, **_kwargs: copy.deepcopy(receipt))
    return receipt


class ExpectedIdentityReached(Exception):
    """Stop before any cycle occupancy, plan, fetch or registration work."""


def stop_after_identity(*_args, **_kwargs):
    raise ExpectedIdentityReached


def test_begin_accepts_matching_typed_target_before_any_lifecycle_work(helper, monkeypatch, tmp_path):
    receipt = setup_early_begin(helper, monkeypatch, tmp_path)
    args = begin_args(helper, tmp_path, initiative_digest=receipt["manifest_digest"])
    monkeypatch.setattr(helper, "check_initiative_cycle_occupancy", stop_after_identity)
    with pytest.raises(ExpectedIdentityReached):
        helper.begin_registration(args)


@pytest.mark.parametrize("change", [
    {"origin": "https://other.example.invalid"},
    {"origin": IDENTITY["origin"] + ":8443"},
    {"repository": "example/Project"},
    {"provider": "github", "origin": "https://github.com"},
])
def test_begin_rejects_same_slug_wrong_expected_authority(helper, monkeypatch, tmp_path, change):
    receipt = setup_early_begin(helper, monkeypatch, tmp_path)
    args = begin_args(helper, tmp_path, {**IDENTITY, **change}, initiative_digest=receipt["manifest_digest"])
    monkeypatch.setattr(helper, "check_initiative_cycle_occupancy", stop_after_identity)
    with pytest.raises(RuntimeError, match="expected|target|identity|match|changed"):
        helper.begin_registration(args)


def test_schema1_digest_and_receipt_remain_legacy(helper, tmp_path):
    path = write_manifest(tmp_path, manifest(1))
    value, _, _, _, _, digest = helper.read_initiative_manifest(path)
    assert value["coordinator_repository"] == "example/project"
    assert digest == "9585cd2f01fd619f2a368cf9917d6f5d64de0f18faec09d7e7bb52d4ea87b8c0"
    receipt = helper.initiative_receipt(path, "local")
    assert receipt == {
        "schema_version": 1, "initiative_id": "forgejo-identity", "slice_id": "local",
        "manifest_digest": digest, "coordinator_repository": "example/project", "context": "test",
        "repository": "example/project", "requirements": ["INT-001"], "depends_on": [],
        "artifacts": ["docs/specs/test/README.md"], "release_group": "local", "execution_owner": "build",
    }


def test_legacy_github_origin_and_local_delivery_rules_unchanged(helper, tmp_path):
    assert helper.github_repository_from_url("git@github.com:example/project.git", "invalid") == "example/project"
    with pytest.raises(RuntimeError):
        helper.github_repository_from_url("https://forge.example.invalid/example/project.git", "invalid")
    args = SimpleNamespace(delivery_intent="local", base_branch="main", github_account=None, github_repository=None)
    helper.normalize_begin_delivery(tmp_path, args, "topic")
    assert args.delivery_intent == "local"
    with pytest.raises(RuntimeError, match="protected base branch"):
        helper.normalize_begin_delivery(tmp_path, args, "main")


def test_typed_github_nondefault_https_port_is_not_default_origin(helper):
    with pytest.raises(RuntimeError):
        helper.repository_identity_from_url("https://github.com:8443/example/project.git", "github")


def test_forgejo_receipt_rejects_rewritten_coordinator_endpoint(helper, monkeypatch, tmp_path):
    mock_git_metadata(helper, monkeypatch, tmp_path)
    metadata = helper.git

    def rewritten(root, *args, **kwargs):
        if args[:2] == ("config", "--get-all"):
            return SimpleNamespace(stdout="https://alias.example.invalid/example/project.git\n", returncode=0)
        return metadata(root, *args, **kwargs)

    monkeypatch.setattr(helper, "git", rewritten)
    with pytest.raises(RuntimeError):
        helper.require_repository_home(tmp_path, IDENTITY)
