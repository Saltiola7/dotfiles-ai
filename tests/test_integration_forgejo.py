"""Forgejo PR adapter acceptance using an entirely local scripted transport."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, forgejo


ORIGIN = "https://forge.example.invalid:8443"
REPOSITORY = "fixture/reference"
REPOSITORY_ID = 42
PULLS = "/api/v1/repos/fixture/reference/pulls"
HEAD = "a" * 40
BASE = "b" * 40
TITLE = "Keep this title"


@pytest.fixture
def publication():
    binding = forgejo.Binding(ORIGIN, REPOSITORY, REPOSITORY_ID, "git-actor", "api-actor")
    return forgejo.Publication(
        binding, "refs/heads/topic", "refs/heads/main", HEAD, BASE, TITLE,
        True, ("Hold:", "WIP:"), body="Review fixture changes.",
    )


def list_path(page=1):
    return f"{PULLS}?state=all&page={page}&limit=50"


def row(number=7, *, head=HEAD, base=BASE, state="open", merged=False, draft=True, title="Hold: " + TITLE):
    return {
        "number": number,
        "html_url": f"{ORIGIN}/{REPOSITORY}/pulls/{number}",
        "state": state,
        "merged": merged,
        "draft": draft,
        "title": title,
        "head": {"ref": "topic", "sha": head, "repo": {"id": REPOSITORY_ID, "full_name": REPOSITORY}},
        "base": {"ref": "main", "sha": base, "repo": {"id": REPOSITORY_ID, "full_name": REPOSITORY}},
    }


def page(rows, *, total=None, next_page=None):
    headers = {"X-Total-Count": str(len(rows) if total is None else total)}
    if next_page is not None:
        headers["Link"] = f'<{ORIGIN}{list_path(next_page)}>; rel="next"'
    return forgejo.Response(200, rows, headers)


class ScriptedTransport:
    def __init__(self, binding, *script):
        self.binding = binding
        self.script = list(script)
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        assert self.script, f"unexpected request to {path}"
        expected_method, expected_path, response = self.script.pop(0)
        assert (method, path) == (expected_method, expected_path)
        if isinstance(response, Exception):
            raise response
        return response


def assert_selected(result, *, number=7, title=TITLE, prefix="Hold: "):
    assert (result.number, result.url) == (number, f"{ORIGIN}/{REPOSITORY}/pulls/{number}")
    assert (result.head, result.base) == (HEAD, BASE)
    assert (result.title, result.draft, result.draft_prefix) == (title, bool(prefix), prefix)


@pytest.mark.parametrize("draft", [True, False])
def test_create_follows_native_title_representation_and_verifies_readback(publication, draft):
    publication = replace(publication, draft=draft)
    prefix = "Hold: " if draft else ""
    observed = row(draft=draft, title=prefix + TITLE)
    closed = row(3, state="closed", merged=True, draft=False, title=TITLE)
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([closed])),
        ("POST", PULLS, forgejo.Response(201, observed)),
        ("GET", f"{PULLS}/7", forgejo.Response(200, observed)),
    )
    result = forgejo.publish_pull_request(publication, transport)
    assert_selected(result, prefix=prefix)
    assert not transport.script
    assert transport.calls[1] == (
        "POST", PULLS, {"head": "topic", "base": "main", "title": prefix + TITLE, "body": publication.body},
    )


def test_reuse_reads_complete_clamped_pages_and_preserves_observed_prefix(publication):
    observed = row(title="hold: " + TITLE)
    closed = row(3, state="closed", merged=True, draft=False, title=TITLE)
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([closed], total=2, next_page=2)),
        ("GET", list_path(2), page([observed], total=2)),
        ("GET", f"{PULLS}/7", forgejo.Response(200, observed)),
    )
    assert_selected(forgejo.publish_pull_request(publication, transport), prefix="hold: ")
    assert not transport.script
    assert all(method == "GET" and body is None for method, _, body in transport.calls)


@pytest.mark.parametrize("problem", ["stale", "duplicate", "repeated", "missing_next", "changed_total"])
def test_incomplete_or_conflicting_listing_prevents_creation(publication, problem):
    first = row(3, state="closed")
    second = row()
    total = 2
    if problem == "stale":
        second = row(head="c" * 40)
    if problem == "duplicate":
        first = row(3)
    if problem == "repeated":
        second = first
    if problem == "changed_total":
        total = 3
    pages = [
        ("GET", list_path(), page([first], total=2, next_page=None if problem == "missing_next" else 2)),
        ("GET", list_path(2), page([second], total=total)),
    ]
    if problem == "stale":
        pages.append(("GET", f"{PULLS}/7", forgejo.Response(200, second)))
    transport = ScriptedTransport(publication.binding, *pages)
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert all(method == "GET" for method, _, _ in transport.calls)


def test_foreign_pagination_link_is_rejected_without_following_it(publication):
    foreign = "https://other.example.invalid" + list_path(2)
    response = forgejo.Response(200, [row(3, state="closed")], {
        "x-total-count": "2", "link": f'<{foreign}>; rel="next"',
    })
    transport = ScriptedTransport(publication.binding, ("GET", list_path(), response))
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert len(transport.calls) == 1


def test_missing_page_total_is_not_proof_that_no_open_pull_exists(publication):
    transport = ScriptedTransport(publication.binding, ("GET", list_path(), forgejo.Response(200, [])))
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert len(transport.calls) == 1


def test_zero_total_with_later_last_page_does_not_authorize_creation(publication):
    response = forgejo.Response(200, [], {
        "X-Total-Count": "0", "Link": f'<{ORIGIN}{list_path(2)}>; rel="last"',
    })
    transport = ScriptedTransport(publication.binding, ("GET", list_path(), response))
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert transport.calls == [("GET", list_path(), None)]


@pytest.mark.parametrize("field,value", [
    ("origin", "https://other.example.invalid"),
    ("repository", "fixture/other"),
    ("repository_id", 99),
    ("git_account", "different-git-actor"),
    ("api_account", "different-api-actor"),
    ("version", "16.0.0"),
])
def test_binding_mismatch_is_refused_before_transport(publication, field, value):
    transport = ScriptedTransport(replace(publication.binding, **{field: value}))
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert transport.calls == []


@pytest.mark.parametrize("problem", ["origin", "head", "base", "source_repo", "target_repo", "ref", "draft", "title"])
def test_adoption_requires_fresh_exact_readback(publication, problem):
    observed = row()
    changed = row()
    if problem == "origin":
        changed["html_url"] = "https://other.example.invalid/fixture/reference/pulls/7"
    elif problem == "head":
        changed = row(head="c" * 40)
    elif problem == "base":
        changed = row(base="d" * 40)
    elif problem == "source_repo":
        changed["head"]["repo"]["id"] = 99
    elif problem == "target_repo":
        changed["base"]["repo"]["full_name"] = "fixture/fork"
    elif problem == "ref":
        changed["head"]["ref"] = "different-topic"
    elif problem == "draft":
        changed = row(draft=False)
    else:
        changed = row(title="Hold: Edited elsewhere")
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([observed])),
        ("GET", f"{PULLS}/7", forgejo.Response(200, changed)),
    )
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert not transport.script


def test_ready_request_keeps_existing_draft_without_qualified_title_update(publication):
    publication = replace(publication, draft=False)
    observed = row()
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([observed])),
        ("GET", f"{PULLS}/7", forgejo.Response(200, observed)),
    )
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert all(method == "GET" for method, _, _ in transport.calls)


def test_ready_title_matching_qualified_draft_prefix_cannot_create_a_draft(publication):
    publication = replace(publication, draft=False, title="wip: " + TITLE)
    transport = ScriptedTransport(publication.binding, ("GET", list_path(), page([])))
    with pytest.raises((core.Invalid, core.Conflict)):
        forgejo.publish_pull_request(publication, transport)
    assert all(method == "GET" for method, _, _ in transport.calls)


@pytest.mark.parametrize("observed", [row(8), row(head="c" * 40)])
def test_success_status_cannot_substitute_for_exact_created_pull_readback(publication, observed):
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([])),
        ("POST", PULLS, forgejo.Response(201, row())),
        ("GET", f"{PULLS}/7", forgejo.Response(200, observed)),
    )
    with pytest.raises(forgejo.UncertainPublication):
        forgejo.publish_pull_request(publication, transport)
    assert not transport.script
    assert [method for method, _, _ in transport.calls] == ["GET", "POST", "GET"]


def test_ambiguous_readback_after_success_status_retains_unresolved_publication(publication):
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([])),
        ("POST", PULLS, forgejo.Response(201, row())),
        ("GET", f"{PULLS}/7", core.Ambiguous("fixture read unavailable")),
    )
    with pytest.raises(forgejo.UncertainPublication):
        forgejo.publish_pull_request(publication, transport)
    assert not transport.script
    assert [method for method, _, _ in transport.calls] == ["GET", "POST", "GET"]


@pytest.mark.parametrize("failure", [TimeoutError, OSError])
def test_lost_create_response_adopts_exact_observed_pull_without_retry(publication, failure):
    observed = row()
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([])),
        ("POST", PULLS, failure()),
        ("GET", list_path(), page([observed])),
        ("GET", f"{PULLS}/7", forgejo.Response(200, observed)),
    )
    assert_selected(forgejo.publish_pull_request(publication, transport))
    assert not transport.script
    assert [method for method, _, _ in transport.calls] == ["GET", "POST", "GET", "GET"]


@pytest.mark.parametrize("observation_unavailable", [False, True])
def test_unknown_create_remains_read_only_across_recovery(publication, observation_unavailable):
    observed = row()
    first_observation = TimeoutError() if observation_unavailable else page([])
    transport = ScriptedTransport(
        publication.binding,
        ("GET", list_path(), page([])),
        ("POST", PULLS, TimeoutError()),
        ("GET", list_path(), first_observation),
        ("GET", list_path(), first_observation),
        ("GET", list_path(), page([observed])),
        ("GET", f"{PULLS}/7", forgejo.Response(200, observed)),
    )
    with pytest.raises(forgejo.UncertainPublication):
        forgejo.publish_pull_request(publication, transport)
    with pytest.raises(forgejo.UncertainPublication):
        forgejo.recover_pull_request(publication, transport)
    assert_selected(forgejo.recover_pull_request(publication, transport))
    assert not transport.script
    assert [method for method, _, _ in transport.calls].count("POST") == 1
