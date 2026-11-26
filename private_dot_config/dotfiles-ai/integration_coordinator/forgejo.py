"""Forgejo v15 pull requests over a caller-qualified, repository-bound transport."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
import re
from typing import Protocol
from urllib.parse import parse_qs, urlencode, urlsplit

from . import core as c


PAGE_SIZE = 50
MAX_PAGES = 100
MAX_LIST_ROWS = 4096


@dataclass(frozen=True, slots=True, repr=False)
class Binding:
    origin: str
    repository: str
    repository_id: int
    git_account: str
    api_account: str
    version: str = "15.0.10"


@dataclass(frozen=True, slots=True, repr=False)
class Publication:
    """Exact caller-approved refs, revisions and qualified instance draft prefixes."""

    binding: Binding
    source_ref: str
    target_ref: str
    head: str
    base: str
    title: str
    draft: bool
    draft_prefixes: tuple[str, ...]
    body: str = ""


@dataclass(frozen=True, slots=True, repr=False)
class Response:
    status: int
    value: object
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, repr=False)
class PullRequest:
    number: int
    url: str
    head: str
    base: str
    title: str
    draft: bool
    draft_prefix: str


class Transport(Protocol):
    """Supplies the verified identity, bounded JSON and native response headers."""

    @property
    def binding(self) -> Binding: ...

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> Response: ...


class UncertainPublication(c.Ambiguous):
    """The caller must retain the attempted write and resume with read-only recovery."""


def _title(value: object, limit: int = 255) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= limit
            or value != value.strip() or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        raise c.Invalid("forgejo_title_invalid")
    return value


def _draft_prefix(title: str, prefixes: tuple[str, ...]) -> str:
    matched = (title[:len(prefix)] for prefix in prefixes
               if title[:len(prefix)].casefold() == prefix.casefold())
    return max(matched, key=len, default="")


def _branch(ref: str) -> str:
    c._require(isinstance(ref, str) and ref.startswith("refs/heads/"), "forgejo_ref_invalid")
    branch = ref.removeprefix("refs/heads/")
    c._branch(branch)
    return branch


def _validate_binding(binding: Binding, transport: Transport | None = None) -> None:
    c._require(isinstance(binding, Binding), "forgejo_binding_invalid")
    c._repository(binding.repository)
    c._integer(binding.repository_id)
    if binding.version != "15.0.10" or (transport is not None and binding != transport.binding):
        raise c.Conflict("forgejo_binding_mismatch")
    c._require(isinstance(binding.origin, str) and re.fullmatch(
        r"https://[a-z0-9.-]+(?::[1-9][0-9]{0,4})?", binding.origin) is not None, "forgejo_origin_invalid")
    try:
        parsed = urlsplit(binding.origin)
        hostname, port = parsed.hostname, parsed.port
    except ValueError:
        raise c.Invalid("forgejo_origin_invalid") from None
    c._require(hostname is not None and len(hostname) <= 253 and port != 443 and all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in hostname.split(".")), "forgejo_origin_invalid")
    for account in (binding.git_account, binding.api_account):
        c._require(isinstance(account, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,126}", account)
                   is not None, "forgejo_account_invalid")


def _validate(intent: Publication, transport: Transport) -> None:
    _validate_binding(intent.binding, transport)
    if _branch(intent.source_ref) == _branch(intent.target_ref):
        raise c.Invalid("forgejo_refs_not_distinct")
    c._oids((intent.head, intent.base), 2, 2)
    c._require(type(intent.draft) is bool, "forgejo_readiness_invalid")
    c._tuple(intent.draft_prefixes, str, 16, minimum=1 if intent.draft else 0)
    for prefix in intent.draft_prefixes:
        _title(prefix, 64)
    _title(intent.title)
    if _draft_prefix(intent.title, intent.draft_prefixes):
        raise c.Invalid("forgejo_intended_title_has_draft_prefix")
    if intent.draft:
        _title(f"{intent.draft_prefixes[0]} {intent.title}")
    c._require(isinstance(intent.body, str) and len(intent.body) <= 65536 and "\0" not in intent.body,
               "forgejo_body_invalid")


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise c.Invalid("forgejo_response_invalid")
    return value


def _number(row: dict[str, object]) -> int:
    number = row.get("number")
    if type(number) is not int or not 1 <= number <= c.MAX_INTEGER:
        raise c.Invalid("forgejo_pull_number_invalid")
    return number


def _open(row: dict[str, object]) -> bool:
    state, merged = row.get("state"), row.get("merged")
    if state not in ("open", "closed") or type(merged) is not bool or (state == "open" and merged):
        raise c.Invalid("forgejo_pull_state_invalid")
    return state == "open"


def _same_repository(side: dict[str, object], binding: Binding) -> bool:
    repository = _object(side.get("repo"))
    identifier, name = repository.get("id"), repository.get("full_name")
    c._repository(name)
    c._integer(identifier)
    if (identifier == binding.repository_id) != (name == binding.repository):
        raise c.Conflict("forgejo_repository_identity_mismatch")
    return identifier == binding.repository_id


def _matches(row: dict[str, object], intent: Publication) -> bool:
    head, base = _object(row.get("head")), _object(row.get("base"))
    if not _same_repository(base, intent.binding):
        raise c.Conflict("forgejo_target_repository_mismatch")
    c._branch(head.get("ref"))
    c._branch(base.get("ref"))
    return (head["ref"] == _branch(intent.source_ref) and base["ref"] == _branch(intent.target_ref)
            and _same_repository(head, intent.binding))


def _get(transport: Transport, path: str) -> Response:
    try:
        response = transport.request("GET", path)
    except (OSError, c.Ambiguous):
        raise c.Unavailable("forgejo_read_unavailable") from None
    if not isinstance(response, Response) or type(response.status) is not int or response.status != 200:
        raise c.Unavailable("forgejo_read_unavailable")
    return response


def _header(response: Response, name: str) -> str | None:
    if not isinstance(response.headers, Mapping):
        raise c.Invalid("forgejo_page_headers_invalid")
    values = [value for key, value in response.headers.items() if isinstance(key, str) and key.lower() == name]
    if len(values) > 1 or any(not isinstance(value, str) or len(value) > 8192
                              or "\r" in value or "\n" in value for value in values):
        raise c.Invalid("forgejo_page_headers_invalid")
    return values[0] if values else None


def _page_links(link: str | None, origin: str, endpoint: str, page: int,
                filters: Mapping[str, str]) -> dict[str, int]:
    relations: dict[str, int] = {}
    if link is None:
        return relations
    expected = {"first": 1, "prev": page - 1, "next": page + 1}
    for part in link.split(","):
        match = re.fullmatch(r'\s*<([^<>\s]+)>\s*;\s*rel="(first|prev|next|last)"\s*', part)
        if match is None or match[2] in relations:
            raise c.Invalid("forgejo_pagination_link_invalid")
        url, relation = match.groups()
        try:
            parsed = urlsplit(url)
            query = parse_qs(parsed.query, strict_parsing=True, max_num_fields=len(filters) + 2)
        except ValueError:
            raise c.Invalid("forgejo_pagination_link_invalid") from None
        if (f"{parsed.scheme}://{parsed.netloc}" != origin or parsed.path != endpoint or parsed.fragment
                or set(query) != {*filters, "page", "limit"}
                or any(query[key] != [value] for key, value in filters.items())
                or len(query["page"]) != 1 or not re.fullmatch(r"[1-9][0-9]{0,2}", query["page"][0])
                or len(query["limit"]) != 1 or not re.fullmatch(r"[1-9][0-9]?", query["limit"][0])
                or int(query["limit"][0]) > PAGE_SIZE):
            raise c.Invalid("forgejo_pagination_link_invalid")
        destination = int(query["page"][0])
        if destination > MAX_PAGES or (relation in expected and destination != expected[relation]):
            raise c.Invalid("forgejo_pagination_link_invalid")
        relations[relation] = destination
    return relations


def _listing_rows(binding: Binding, transport: Transport, endpoint: str,
                  filters: Mapping[str, str]) -> Iterator[dict[str, object]]:
    """Read a bounded population; callers must exhaust the iterator before acting."""
    total = None
    last_page = None
    seen = 0
    for page in range(1, MAX_PAGES + 1):
        query = urlencode({**filters, "page": page, "limit": PAGE_SIZE})
        response = _get(transport, f"{endpoint}?{query}")
        count = _header(response, "x-total-count")
        if count is None or not re.fullmatch(r"(?:0|[1-9][0-9]{0,3})", count) or int(count) > MAX_LIST_ROWS:
            raise c.Invalid("forgejo_page_count_invalid")
        if total is not None and total != int(count):
            raise c.Conflict("forgejo_page_population_changed")
        total = int(count)
        values = response.value
        if (not isinstance(values, list) or len(values) > PAGE_SIZE
                or seen + len(values) > total or (not values and seen < total)):
            raise c.Invalid("forgejo_page_population_invalid")
        for value in values:
            yield _object(value)
        seen += len(values)
        links = _page_links(_header(response, "link"), binding.origin, endpoint, page, filters)
        has_next = "next" in links
        if "last" in links:
            if last_page is not None and links["last"] != last_page:
                raise c.Conflict("forgejo_page_population_changed")
            last_page = links["last"]
        if (has_next != (seen < total)
                or (last_page is not None and (page > last_page or has_next != (page < last_page)))):
            raise c.Conflict("forgejo_pagination_incomplete")
        if not has_next:
            return
    raise c.Conflict("forgejo_pagination_bound_exceeded")


def _endpoint(intent: Publication) -> str:
    return f"/api/v1/repos/{intent.binding.repository}/pulls"


def _lookup(intent: Publication, transport: Transport) -> int | None:
    seen: set[int] = set()
    matches: list[int] = []
    for row in _listing_rows(intent.binding, transport, _endpoint(intent), {"state": "all"}):
        number = _number(row)
        if number in seen:
            raise c.Conflict("forgejo_page_repeated_pull")
        seen.add(number)
        if _open(row) and _matches(row, intent):
            matches.append(number)
    if len(matches) > 1:
        raise c.Conflict("forgejo_open_pull_ambiguous")
    return matches[0] if matches else None


def _readback(intent: Publication, transport: Transport, number: int) -> PullRequest:
    row = _object(_get(transport, f"{_endpoint(intent)}/{number}").value)
    return _readback_row(intent, row, number)


def _readback_row(intent: Publication, row: dict[str, object], number: int) -> PullRequest:
    url = f"{intent.binding.origin}/{intent.binding.repository}/pulls/{number}"
    if _number(row) != number or not _open(row) or row.get("html_url") != url or not _matches(row, intent):
        raise c.Conflict("forgejo_pull_identity_mismatch")
    head, base = _object(row["head"]).get("sha"), _object(row["base"]).get("sha")
    if head != intent.head or base != intent.base:
        raise c.Conflict("forgejo_pull_revision_changed")
    title = _title(row.get("title"))
    prefix = _draft_prefix(title, intent.draft_prefixes)
    if row.get("draft") is not bool(prefix) or row["draft"] is not intent.draft:
        raise c.Conflict("forgejo_pull_readiness_mismatch")
    added = title[:-len(intent.title)]
    separator = added[len(prefix):]
    if (not added.startswith(prefix) or (separator and not prefix)
            or (separator and not separator.isspace()) or title != added + intent.title):
        raise c.Conflict("forgejo_pull_title_changed")
    return PullRequest(number, url, intent.head, intent.base, intent.title, intent.draft, added)


def recover_pull_request(intent: Publication, transport: Transport) -> PullRequest:
    """Read back an uncertain publication without issuing another mutation."""
    try:
        _validate(intent, transport)
        number = _lookup(intent, transport)
        if number is not None:
            return _readback(intent, transport, number)
    except (c.Invalid, c.Conflict, c.Unavailable, c.Ambiguous):
        pass
    raise UncertainPublication("forgejo_publication_unresolved") from None


def publish_pull_request(intent: Publication, transport: Transport,
                         *, before_create: Callable[[], None] | None = None) -> PullRequest:
    """Publish once or adopt an exact candidate. The caller owns the qualified feature ref."""
    _validate(intent, transport)
    number = _lookup(intent, transport)
    if number is not None:
        return _readback(intent, transport, number)
    title = f"{intent.draft_prefixes[0]} {intent.title}" if intent.draft else intent.title
    body = {"head": _branch(intent.source_ref), "base": _branch(intent.target_ref), "title": title, "body": intent.body}
    if before_create is not None:
        before_create()
    try:
        response = transport.request("POST", _endpoint(intent), body)
        if not isinstance(response, Response) or type(response.status) is not int or response.status != 201:
            raise UncertainPublication("forgejo_publication_unresolved")
        number = _number(_object(response.value))
    except (OSError, c.Invalid, c.Conflict, c.Unavailable, c.Ambiguous):
        return recover_pull_request(intent, transport)
    try:
        return _readback(intent, transport, number)
    except (c.Invalid, c.Conflict, c.Unavailable):
        raise UncertainPublication("forgejo_publication_unresolved") from None
