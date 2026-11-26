"""Bind the explicit Linux backend while preserving historical recipe identities."""

from dataclasses import asdict

import pytest

from test_initiative_forgejo import fixture_document
from test_integration_forgejo_merge import Fixture
from integration_coordinator import initiative_service, lifecycle


@pytest.fixture
def recipe_input(tmp_path):
    common = {
        "authority_checkout": str(tmp_path.resolve()),
        "manifest_path": "docs/initiatives/fixture/MANIFEST.json",
        "writer_agent": "build",
        "slices": {
            "slice-a": {
                "branch": "fixture-a",
                "cycle_id": "FIXTURE-A",
                "context": "fixture",
                "risk": "critical",
                "plan_path": "docs/initiatives/fixture/A.plan.json",
                "plan_digest": "5" * 64,
            },
        },
    }

    def read(provider):
        git = tmp_path / f"recipe-{provider['schema_version']}.git"
        git.mkdir()
        custody = lifecycle.Custody(git)
        custody._write(custody.directory / "initiative-runtime.json", lifecycle.canonical({**common, **provider}))
        return initiative_service.read_recipe(custody)

    return common, read


@pytest.mark.parametrize("version", [1, 2])
def test_historical_backend_retains_canonical_recipe_digest(recipe_input, version):
    common, read = recipe_input
    provider = {"github_account": "test-user"} if version == 1 else {"forgejo": fixture_document(Fixture())}
    recipe = read({"schema_version": version, **provider})
    assert recipe.credential_source == "osxkeychain"
    assert recipe.digest == lifecycle.digest({
        **common,
        "schema_version": version,
        **(provider if version == 1 else {"forgejo": recipe.forgejo.digest}),
        "slices": [asdict(recipe.slice("slice-a"))],
    })


def test_linux_recipe_binds_backend_without_reidentifying_fixture(recipe_input):
    common, read = recipe_input
    provider = {"forgejo": fixture_document(Fixture())}
    keychain = read({"schema_version": 2, **provider})
    linux = read({"schema_version": 3, "credential_source": "systemd", **provider})
    assert linux.credential_source == "systemd"
    assert linux.forgejo == keychain.forgejo
    assert linux.forgejo.binding == keychain.forgejo.binding
    assert linux.forgejo.digest == keychain.forgejo.digest
    assert linux.digest != keychain.digest
    assert linux.digest == lifecycle.digest({
        **common,
        "schema_version": 3,
        "forgejo": keychain.forgejo.digest,
        "credential_source": "systemd",
        "slices": [asdict(linux.slice("slice-a"))],
    })
    binding = {
        "repository": linux.forgejo.repository,
        "target_ref": linux.forgejo.target_ref,
        "root_oid": linux.forgejo.root_oid,
        "policy_digest": linux.forgejo.plan.policy_digest,
        "enrollment_digest": linux.forgejo.digest,
        "controller_digest": "1" * 64,
        "writer_digest": "2" * 64,
        "qualification_digest": "3" * 64,
    }
    assert (
        initiative_service.bind_recipe(linux, binding)["qualification_digest"]
        != initiative_service.bind_recipe(keychain, binding)["qualification_digest"]
    )


@pytest.mark.parametrize(
    ("version", "extra"),
    [
        (1, {"credential_source": "systemd"}),
        (2, {"credential_source": "systemd"}),
        (3, {}),
        (3, {"credential_source": "osxkeychain"}),
        (3, {"credential_source": "file"}),
        (3, {"credential_source": {"type": "systemd"}}),
        (3, {"credential_source": "systemd", "credential_path": "/test/irrelevant"}),
        (3, {"credential_source": "systemd", "github_account": "test-user"}),
    ],
)
def test_credential_source_is_explicit_and_closed(recipe_input, version, extra):
    _, read = recipe_input
    provider = {"github_account": "test-user"} if version == 1 else {"forgejo": fixture_document(Fixture())}
    with pytest.raises(ValueError, match="initiative_recipe_"):
        read({"schema_version": version, **provider, **extra})


def test_only_linux_review_names_the_explicit_backend(recipe_input):
    _, read = recipe_input
    provider = {"forgejo": fixture_document(Fixture())}
    for version in (1, 2, 3):
        if version == 1:
            selected = {"github_account": "test-user"}
        elif version == 2:
            selected = provider
        else:
            selected = {**provider, "credential_source": "systemd"}
        recipe = read({"schema_version": version, **selected})
        preview = initiative_service.StartPreview(
            recipe, {"initiative_id": "fixture", "selected": ["slice-a"]}, {}, "1" * 64, "2" * 64,
        )
        if version == 3:
            assert preview.review["credential_source"] == "systemd"
        else:
            assert "credential_source" not in preview.review
