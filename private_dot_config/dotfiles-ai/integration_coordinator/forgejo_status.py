"""Read Forgejo v15 commit statuses for an exact object as native observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from urllib.parse import urlsplit

from . import core as c
from . import forgejo


NATIVE_STATES = frozenset({"pending", "success", "error", "failure", "warning"})


@dataclass(frozen=True, slots=True, repr=False)
class Status:
    id: int
    context: str
    state: str
    creator_id: int | None
    created_at: datetime | None
    diagnostic_url: str | None


def _context(value: object) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 512 or value != value.strip()
            or any(ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
                   for char in value)):
        raise c.Invalid("forgejo_status_context_invalid")
    return value


def _creator_id(creator: object) -> int:
    # Native Forgejo system users have reserved negative IDs.
    if type(creator) is not int or creator == 0 or not -3 <= creator <= c.MAX_INTEGER:
        raise c.Invalid("forgejo_status_creator_invalid")
    return creator


def _created_at(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,9})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", value
    ) is None:
        raise c.Invalid("forgejo_status_created_at_invalid")
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise c.Invalid("forgejo_status_created_at_invalid") from None


def _diagnostic_url(value: object, binding: forgejo.Binding) -> str | None:
    if (not isinstance(value, str) or not 1 <= len(value) <= 2048
            or not value.isascii() or any(ord(char) <= 32 or ord(char) == 127 for char in value)
            or any(char in value for char in "?#\\%")):
        return None
    url = binding.origin + value if value.startswith("/") and not value.startswith("//") else value
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    repo_path = f"/{binding.repository}"
    if (f"{parsed.scheme}://{parsed.netloc}" != binding.origin
            or not (parsed.path == repo_path or parsed.path.startswith(repo_path + "/"))
            or any(segment in {"", ".", ".."} for segment in parsed.path[1:].split("/"))
            or re.fullmatch(r"/[A-Za-z0-9._~/-]+", parsed.path) is None):
        return None
    return url


def _status(row: dict[str, object], binding: forgejo.Binding) -> Status:
    identifier, state = row.get("id"), row.get("status")
    if type(identifier) is not int or not 1 <= identifier <= c.MAX_INTEGER:
        raise c.Invalid("forgejo_status_id_invalid")
    if not isinstance(state, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", state) is None:
        raise c.Invalid("forgejo_status_state_invalid")
    creator = row.get("creator")
    return Status(
        identifier, _context(row.get("context")), state if state in NATIVE_STATES else "unknown",
        None if creator is None else _creator_id(forgejo._object(creator).get("id")),
        _created_at(row.get("created_at")),
        _diagnostic_url(row.get("target_url"), binding),
    )


def read_statuses(binding: forgejo.Binding, tested_oid: str, transport: forgejo.Transport) -> tuple[Status, ...]:
    """Return complete status history. These rows do not prove job execution."""
    forgejo._validate_binding(binding, transport)
    c._oid(tested_oid)
    endpoint = f"/api/v1/repos/{binding.repository}/statuses/{tested_oid}"
    statuses: dict[int, Status] = {}
    for row in forgejo._listing_rows(binding, transport, endpoint, {}):
        status = _status(row, binding)
        if status.id in statuses:
            raise c.Conflict("forgejo_page_repeated_status")
        statuses[status.id] = status
    return tuple(statuses.values())
