"""Bounded native GitHub facts and fail-closed authority checks.

All I/O is injected.  Records, JSON claims and green workflow labels are not
native authority.  No constructor reads a credential or contacts GitHub.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import base64
import binascii
import datetime as dt
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
from typing import Protocol, TypeAlias, runtime_checkable
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from . import core as c
from . import runtime as r
from . import ci_mapping as m

MAX_JSON = 4 * 1024 * 1024
MAX_ARCHIVE = 70 * 1024 * 1024
MAX_MEMBER = 32 * 1024 * 1024
MAX_POPULATION = 4096


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise c.Invalid("native_object_invalid")
    return {key: item for key, item in value.items() if isinstance(key, str)}


def _array(value: object, limit: int = MAX_POPULATION) -> list[object]:
    if not isinstance(value, list) or len(value) > limit:
        raise c.Invalid("native_population_invalid")
    return list(value)


def _text(value: object, limit: int = 1024) -> str:
    if not isinstance(value, str) or not value or len(value) > limit or any(ord(ch) < 32 for ch in value):
        raise c.Invalid("native_text_invalid")
    return value


def _integer(value: object) -> int:
    if type(value) is not int or not 1 <= value <= c.MAX_INTEGER:
        raise c.Invalid("native_integer_invalid")
    return value


def _oid(value: object) -> str:
    text = _text(value, 64)
    if len(text) not in (40, 64) or re.fullmatch("[0-9a-f]+", text) is None or set(text) == {"0"}:
        raise c.Invalid("native_oid_invalid")
    return text


def _digest(value: object) -> str:
    text = _text(value, 64)
    if re.fullmatch("[0-9a-f]{64}", text) is None:
        raise c.Invalid("native_digest_invalid")
    return text


def _hash(value: object) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise c.Invalid("native_encoding_invalid") from error
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise c.Invalid("native_duplicate_key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> object:
    raise c.Invalid("native_nonfinite_number")


def decode_json(raw: bytes, limit: int = MAX_JSON) -> object:
    if type(raw) is not bytes or len(raw) > limit:
        raise c.Invalid("native_response_limit")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, OverflowError, RecursionError) as error:
        raise c.Invalid("native_json_invalid") from error


class ApiFailure(RuntimeError):
    """Only the HTTP status is retained; never a server body or credential."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__("native_api_rejected")


class Transport(Protocol):
    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object: ...
    def archive(self, path: str) -> bytes: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: object, fp: object, code: int, msg: str,
                         headers: object, newurl: str) -> None:
        return None


class HttpTransport:
    """One fixed API origin; credential-free downloads use explicit signed URLs."""

    __slots__ = ("_token", "_timeout")

    def __init__(self, token: str, timeout: float = 30.0) -> None:
        if not token or not 0 < timeout <= 60:
            raise c.Invalid("native_transport_configuration")
        self._token = token
        self._timeout = timeout

    def __repr__(self) -> str:
        return "HttpTransport(<credential>)"

    def _request(self, method: str, path: str, body: dict[str, object] | None,
                 limit: int, *, artifact: bool = False) -> bytes:
        if method not in {"GET", "POST", "PATCH", "PUT"} or not (path.startswith("repos/") or path in {"graphql", "user"}):
            raise c.Invalid("native_route_invalid")
        if (any(part in {".", ".."} for part in path.split("/"))
                or any(ord(ch) < 32 or ch in (chr(92), "#") for ch in path) or "://" in path):
            raise c.Invalid("native_route_invalid")
        if artifact and re.fullmatch(r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/artifacts/[1-9][0-9]*/zip", path) is None:
            raise c.Invalid("native_archive_route_invalid")
        try:
            payload = None if body is None else json.dumps(body, separators=(",", ":"), allow_nan=False).encode()
        except (ValueError, TypeError, OverflowError, RecursionError) as error:
            raise c.Invalid("native_request_invalid") from error
        if payload is not None and len(payload) > MAX_JSON:
            raise c.Invalid("native_request_limit")
        request = urllib.request.Request("https://api.github.com/" + path, data=payload, method=method,
            headers={"Authorization": "Bearer " + self._token, "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "dbsctr-integration"})
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            try:
                response = opener.open(request, timeout=self._timeout)
            except urllib.error.HTTPError as redirect:
                if not 300 <= redirect.code < 400:
                    raise
                if not artifact or redirect.code not in {301, 302, 303, 307, 308}:
                    raise c.Unavailable("native_redirect_refused") from None
                location = redirect.headers.get("Location")
                if not isinstance(location, str) or len(location) > 8192:
                    raise c.Unavailable("native_redirect_refused") from None
                parsed = urllib.parse.urlsplit(location)
                host = parsed.hostname or ""
                if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
                        or parsed.port not in {None, 443} or parsed.fragment
                        or not (host.endswith(".blob.core.windows.net") or host.endswith(".githubusercontent.com"))):
                    raise c.Unavailable("native_redirect_refused") from None
                # Never copy API authorization, cookies, proxy credentials or any
                # server-supplied headers to the signed download destination.
                download = urllib.request.Request(location, method="GET", headers={"User-Agent": "dbsctr-integration"})
                try:
                    response = opener.open(download, timeout=self._timeout)
                except urllib.error.HTTPError as nested:
                    if 300 <= nested.code < 400:
                        raise c.Unavailable("native_redirect_refused") from None
                    raise
            with response:
                raw = response.read(limit + 1)
        except urllib.error.HTTPError as error:
            raise ApiFailure(error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            exception = c.Unavailable if method == "GET" else c.Ambiguous
            raise exception("native_api_unavailable") from None
        except ValueError:
            raise c.Unavailable("native_redirect_refused") from None
        if not isinstance(raw, bytes) or len(raw) > limit:
            raise c.Unavailable("native_response_limit")
        return raw

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        return decode_json(self._request(method, path, body, MAX_JSON))

    def archive(self, path: str) -> bytes:
        return self._request("GET", path, None, MAX_ARCHIVE, artifact=True)


@dataclass(frozen=True, slots=True)
class CheckRequirement:
    context: str
    app_id: int

    def __post_init__(self) -> None:
        _text(self.context, 256)
        _integer(self.app_id)


@dataclass(frozen=True, slots=True)
class TargetGuards:
    checks: tuple[CheckRequirement, ...]
    code_scanning: bool
    digest: str


def native_guard_digest(target_digest: str, control_digest: str) -> str:
    return _hash({"target": _digest(target_digest), "control": _digest(control_digest)})


@dataclass(frozen=True, slots=True)
class ControlActor:
    kind: str
    actor_id: int

    def __post_init__(self) -> None:
        if self.kind not in {"User", "Integration", "RepositoryRole"}:
            raise c.Invalid("control_actor_unsupported")
        _integer(self.actor_id)


@dataclass(frozen=True, slots=True)
class CheckBinding:
    context: str
    app_id: int
    workflow_id: int
    workflow_path: str
    event: str

    def __post_init__(self) -> None:
        CheckRequirement(self.context, self.app_id)
        _integer(self.workflow_id)
        if re.fullmatch(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml", self.workflow_path) is None:
            raise c.Invalid("native_workflow_invalid")
        if self.event not in {"pull_request", "push"}:
            raise c.Invalid("native_event_invalid")


def verify_target_policy(classic: object, rulesets: Sequence[object], *, review_exception: bool = False) -> TargetGuards:
    checks: set[CheckRequirement] = set()
    scanning = False
    if classic is not None:
        protection = _object(classic)
        status = protection.get("required_status_checks")
        if status is not None:
            value = _object(status)
            if value.get("strict") is not True or _object(protection.get("enforce_admins")).get("enabled") is not True:
                raise c.Unavailable("native_strict_guard_unavailable")
            for entry in _array(value.get("checks"), 512):
                item = _object(entry)
                checks.add(CheckRequirement(_text(item.get("context"), 256), _integer(item.get("app_id"))))
    safe = {"deletion", "non_fast_forward", "pull_request", "required_linear_history", "required_signatures", "creation", "update"}
    for raw in rulesets:
        ruleset = _object(raw)
        if ruleset.get("enforcement") != "active":
            raise c.Unavailable("native_rule_not_active")
        bypass = _text(ruleset.get("current_user_can_bypass"), 64)
        if bypass not in {"never", "always", "pull_requests_only"}:
            raise c.Unavailable("native_bypass_unknown")
        for entry in _array(ruleset.get("rules"), 128):
            rule = _object(entry)
            kind = _text(rule.get("type"), 128)
            params = _object(rule.get("parameters", {}))
            if kind in {"required_status_checks", "code_scanning"} and bypass != "never":
                raise c.Unavailable("native_ci_bypass_forbidden")
            if kind == "required_status_checks":
                if params.get("strict_required_status_checks_policy") is not True:
                    raise c.Unavailable("native_strict_guard_unavailable")
                for item in _array(params.get("required_status_checks"), 512):
                    check = _object(item)
                    checks.add(CheckRequirement(_text(check.get("context"), 256), _integer(check.get("integration_id"))))
            elif kind == "code_scanning":
                tools = _array(params.get("code_scanning_tools"), 16)
                if not tools or any(_object(tool).get("tool") != "CodeQL" for tool in tools):
                    raise c.Unavailable("native_scanner_unsupported")
                scanning = True
            elif kind == "pull_request":
                if bypass != "never" and not review_exception:
                    raise c.Unavailable("review_exception_not_enrolled")
            elif kind not in safe:
                raise c.Unavailable("native_policy_unsupported")
    if not checks:
        raise c.Unavailable("native_checks_absent")
    ordered = tuple(sorted(checks, key=lambda item: (item.context, item.app_id)))
    return TargetGuards(ordered, scanning, _hash({"classic": classic, "rulesets": list(rulesets)}))


def verify_control_policy(rulesets: Sequence[object], trusted_actors: tuple[ControlActor, ...], *,
                          admin_ids: tuple[int, ...] | None = None, classic: object = None) -> str:
    trusted = set(trusted_actors)
    integrity: set[str] = set()
    update = False
    if classic is not None:
        protection = _object(classic)
        linear = protection.get("required_linear_history")
        if linear is not None and _object(linear).get("enabled") is not False:
            raise c.Unavailable("control_linear_history_unsupported")
        if (_object(protection.get("enforce_admins")).get("enabled") is not True
                or _object(protection.get("allow_force_pushes")).get("enabled") is not False
                or _object(protection.get("allow_deletions")).get("enabled") is not False):
            raise c.Unavailable("control_integrity_unavailable")
        restriction = _object(protection.get("restrictions"))
        if _array(restriction.get("teams"), 128):
            raise c.Unavailable("control_team_expansion_unavailable")
        writers = tuple(ControlActor(kind, _integer(_object(actor).get("id")))
            for key, kind in (("users", "User"), ("apps", "Integration"))
            for actor in _array(restriction.get(key), 128))
        if not writers or any(writer not in trusted for writer in writers):
            raise c.Unavailable("control_writer_not_enrolled")
        if admin_ids is None or not admin_ids or any(ControlActor("User", uid) not in trusted for uid in admin_ids):
            raise c.Unavailable("control_writer_expansion_unavailable")
        integrity.update({"deletion", "non_fast_forward"}); update = True
    for raw in rulesets:
        value = _object(raw)
        if value.get("enforcement") != "active":
            raise c.Unavailable("control_rule_inactive")
        kinds = {_text(_object(rule).get("type"), 128) for rule in _array(value.get("rules"), 128)}
        if "required_linear_history" in kinds:
            raise c.Unavailable("control_linear_history_unsupported")
        actors = _array(value.get("bypass_actors"), 128)
        if not actors and value.get("current_user_can_bypass") == "never":
            integrity.update(kinds & {"deletion", "non_fast_forward"})
        if "update" in kinds:
            if value.get("current_user_can_bypass") != "always" or not actors:
                raise c.Unavailable("control_writer_unavailable")
            for actor in actors:
                item = _object(actor)
                if item.get("bypass_mode") != "always":
                    raise c.Unavailable("control_writer_unsupported")
                kind = _text(item.get("actor_type"), 64)
                actor_id = _integer(item.get("actor_id"))
                if kind == "RepositoryRole" and actor_id == 5:
                    if admin_ids is None or not admin_ids or any(ControlActor("User", uid) not in trusted for uid in admin_ids):
                        raise c.Unavailable("control_writer_expansion_unavailable")
                elif kind not in {"Integration", "User"} or ControlActor(kind, actor_id) not in trusted:
                    raise c.Unavailable("control_writer_not_enrolled")
            update = True
    if integrity != {"deletion", "non_fast_forward"} or not update:
        raise c.Unavailable("control_integrity_unavailable")
    return _hash({"rulesets": list(rulesets), "admin_ids": None if admin_ids is None else sorted(admin_ids), "classic": classic})


def verify_check(check_value: object, job_value: object, run_value: object, binding: CheckBinding, *,
                 head: str, tested_oid: str, pr_number: int, producer_digest: str) -> c.Evidence:
    _oid(head); _oid(tested_oid); _digest(producer_digest)
    check, job, run = _object(check_value), _object(job_value), _object(run_value)
    _integer(job.get("id"))
    check_id, run_id = _integer(check.get("id")), _integer(run.get("id"))
    check_url = _text(job.get("check_run_url"), 2048)
    if re.fullmatch(r"https://api\.github\.com/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/check-runs/" + str(check_id), check_url) is None:
        raise c.Unavailable("native_job_check_unbound")
    attempt = _integer(run.get("run_attempt"))
    for native_id in (job.get("run_id"), job.get("run_attempt"), run.get("workflow_id"),
                      _object(check.get("app")).get("id"), _object(check.get("check_suite")).get("id"), run.get("check_suite_id")):
        _integer(native_id)
    check_head, job_head = _oid(check.get("head_sha")), _oid(job.get("head_sha"))
    subjects = {head, tested_oid}
    if (check.get("name") != binding.context or job.get("name") != binding.context
            or _object(check.get("app")).get("id") != binding.app_id
            or job.get("run_id") != run_id or job.get("run_attempt") != attempt
            or run.get("workflow_id") != binding.workflow_id or run.get("path") != binding.workflow_path
            or run.get("event") != binding.event or run.get("head_sha") != head
            or check_head not in subjects or job_head not in subjects
            or _object(check.get("check_suite")).get("id") != run.get("check_suite_id")
            or any(value.get("status") != "completed" or value.get("conclusion") != "success" for value in (check, job, run))):
        raise c.Unavailable("native_check_unqualified")
    if binding.event == "pull_request" and not any(_object(item).get("number") == pr_number for item in _array(run.get("pull_requests"), 128)):
        raise c.Unavailable("native_pr_run_unbound")
    return c.Evidence("check", binding.app_id, check_id, attempt, tested_oid, producer_digest)


def _member(value: str) -> str:
    path = PurePosixPath(value)
    if (not path.parts or not value or len(value) > 256 or path.is_absolute() or "\\" in value
            or str(path) != value or any(part in {".", ".."} for part in path.parts)):
        raise c.Invalid("artifact_member_invalid")
    return value


def read_artifact(archive: bytes, metadata: object, *, run_id: int, repository_id: int,
                  source_head: str, member: str) -> dict[str, object]:
    _member(member); _oid(source_head); _integer(run_id); _integer(repository_id)
    item = _object(metadata)
    workflow = _object(item.get("workflow_run"))
    size = _integer(item.get("size_in_bytes"))
    if (item.get("expired") is not False or size > MAX_ARCHIVE or len(archive) > MAX_ARCHIVE
            or workflow.get("id") != run_id or workflow.get("repository_id") != repository_id
            or workflow.get("head_sha") != source_head
            or item.get("digest") != "sha256:" + hashlib.sha256(archive).hexdigest()):
        raise c.Unavailable("artifact_identity_unqualified")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            entries = zipped.infolist()
            if len(entries) > 2048 or len({entry.filename for entry in entries}) != len(entries):
                raise c.Invalid("artifact_population_invalid")
            found = [entry for entry in entries if entry.filename == member]
            if len(found) != 1 or found[0].file_size > MAX_MEMBER or found[0].flag_bits & 1 or (found[0].external_attr >> 16) & 0o170000 == 0o120000:
                raise c.Invalid("artifact_member_unqualified")
            raw = zipped.read(found[0])
    except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile) as error:
        raise c.Invalid("artifact_archive_invalid") from error
    return _object(decode_json(raw, MAX_MEMBER))


def _time(value: object) -> dt.datetime:
    try:
        instant = dt.datetime.fromisoformat(_text(value, 64).replace("Z", "+00:00"))
    except ValueError as error:
        raise c.Invalid("native_time_invalid") from error
    if instant.utcoffset() is None:
        raise c.Invalid("native_time_invalid")
    return instant


def verify_codeql(setup_value: object, analyses: Sequence[object], *, accepted_oids: tuple[str, ...],
                  accepted_refs: tuple[str, ...], attempt: int, started: dt.datetime, finished: dt.datetime) -> tuple[c.Evidence, ...]:
    _integer(attempt)
    if finished < started: raise c.Unavailable("codeql_attempt_interval_invalid")
    setup = _object(setup_value)
    if setup.get("state") != "configured":
        raise c.Unavailable("codeql_configuration_unavailable")
    changed = _time(setup.get("updated_at"))
    aliases = {"actions": "actions", "c-cpp": "c-cpp", "csharp": "csharp", "go": "go",
               "java": "java-kotlin", "kotlin": "java-kotlin", "java-kotlin": "java-kotlin",
               "javascript": "javascript-typescript", "typescript": "javascript-typescript",
               "javascript-typescript": "javascript-typescript", "python": "python", "ruby": "ruby",
               "rust": "rust", "swift": "swift"}
    expected: set[str] = set()
    for raw in _array(setup.get("languages"), 32):
        language = _text(raw, 64)
        if language not in aliases:
            raise c.Unavailable("codeql_language_unsupported")
        expected.add("/language:" + aliases[language])
    if not expected:
        raise c.Unavailable("codeql_categories_absent")
    latest: dict[str, tuple[dt.datetime, dict[str, object]]] = {}
    for raw in analyses:
        value = _object(raw)
        if value.get("commit_sha") not in accepted_oids or value.get("ref") not in accepted_refs:
            continue
        if _object(value.get("tool")).get("name") != "CodeQL":
            continue
        category = _text(value.get("category"), 256)
        if category not in expected:
            continue
        created = _time(value.get("created_at"))
        if category not in latest or created > latest[category][0]:
            latest[category] = (created, value)
        elif created == latest[category][0] and value != latest[category][1]:
            raise c.Unavailable("codeql_analysis_ambiguous")
    result: list[c.Evidence] = []
    for category in sorted(expected):
        if category not in latest:
            raise c.Unavailable("codeql_category_missing")
        created, value = latest[category]
        if created < changed or not started <= created <= finished or value.get("error") != "" or _integer(value.get("rules_count")) < 1:
            raise c.Unavailable("codeql_analysis_unqualified")
        result.append(c.Evidence("scan", 15368, _integer(value.get("id")), attempt,
                      _oid(value.get("commit_sha")), _hash({"setup": setup, "analysis": value})))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class Enrollment:
    repository: str
    repository_id: int
    default_branch: str
    control_branch: str
    root_oid: str
    policy_digest: str
    mutator_user_ids: tuple[int, ...] = ()
    mutator_app_ids: tuple[int, ...] = ()
    enabled: bool = False
    review_exception: bool = False
    native_guard_digest: str | None = None

    def __post_init__(self) -> None:
        c._repository(self.repository)
        if any(part in {".", ".."} for part in self.repository.split("/")):
            raise c.Invalid("native_repository_invalid")
        _integer(self.repository_id)
        c._branch(self.default_branch); c._branch(self.control_branch)
        _oid(self.root_oid); _digest(self.policy_digest)
        if self.native_guard_digest is not None: _digest(self.native_guard_digest)
        if self.control_branch in {self.default_branch, "main", "master"}:
            raise c.Invalid("control_target_collision")
        for values in (self.mutator_user_ids, self.mutator_app_ids):
            c._tuple(values, int, 128)
            for value in values: _integer(value)
            if len(set(values)) != len(values): raise c.Invalid("duplicate_mutator")
        if type(self.enabled) is not bool or type(self.review_exception) is not bool:
            raise c.Invalid("native_enrollment_invalid")


def parse_enrollment(value: object) -> Enrollment:
    data = _object(value)
    if set(data) - {"native_guard_digest"} != {"schema_version", "repository", "repository_id", "default_branch", "control_branch", "root_oid", "policy_digest", "mutator_user_ids", "mutator_app_ids", "enabled", "review_exception"} or data.get("schema_version") != 2 or type(data.get("schema_version")) is not int:
        raise c.Invalid("native_enrollment_fields")
    enabled, exception = data["enabled"], data["review_exception"]
    if type(enabled) is not bool or type(exception) is not bool:
        raise c.Invalid("native_enrollment_invalid")
    return Enrollment(_text(data["repository"], 201), _integer(data["repository_id"]),
        _text(data["default_branch"], 256), _text(data["control_branch"], 256), _oid(data["root_oid"]),
        _digest(data["policy_digest"]), tuple(_integer(item) for item in _array(data["mutator_user_ids"], 128)),
        tuple(_integer(item) for item in _array(data["mutator_app_ids"], 128)), enabled, exception,
        None if data.get("native_guard_digest") is None else _digest(data["native_guard_digest"]))


_FACTS = {"repository", "source_head", "tested_oid", "base", "tree", "run_id", "attempt", "run_id_text", "attempt_text", "event", "pr_number", "tested_parents"}


def _json_path(value: tuple[str, ...]) -> None:
    c._tuple(value, str, 16, 1)
    for part in value: _text(part, 256)


@dataclass(frozen=True, slots=True)
class IdentityField:
    path: tuple[str, ...]
    fact: str

    def __post_init__(self) -> None:
        _json_path(self.path)
        if self.fact not in _FACTS: raise c.Invalid("producer_fact_invalid")


@dataclass(frozen=True, slots=True)
class LiteralField:
    path: tuple[str, ...]
    value: object

    def __post_init__(self) -> None:
        _json_path(self.path)
        _hash(self.value)


@dataclass(frozen=True, slots=True)
class ReceiptBinding:
    artifact_name: str
    member: str
    fields: tuple[IdentityField, ...]
    literals: tuple[LiteralField, ...] = ()

    def __post_init__(self) -> None:
        _text(self.artifact_name, 256); _member(self.member)
        c._tuple(self.fields, IdentityField, 32, 1); c._tuple(self.literals, LiteralField, 32)
        facts = {value.fact for value in self.fields}
        if not ("tested_oid" in facts and facts & {"run_id", "run_id_text"} and facts & {"attempt", "attempt_text"}):
            raise c.Invalid("producer_identity_incomplete")
        paths = [item.path for item in (*self.fields, *self.literals)]
        if len(set(paths)) != len(paths): raise c.Invalid("producer_path_duplicate")
        remainder = self.artifact_name
        for token in ("{attempt}", "{head}", "{tested}", "{pr}"): remainder = remainder.replace(token, "")
        if "{" in remainder or "}" in remainder: raise c.Invalid("artifact_template_invalid")


@dataclass(frozen=True, slots=True)
class Producer:
    binding: CheckBinding
    workflow_digest: str
    receipt: ReceiptBinding | None = None

    def __post_init__(self) -> None:
        if type(self.binding) is not CheckBinding or self.receipt is not None and type(self.receipt) is not ReceiptBinding:
            raise c.Invalid("producer_binding_invalid")
        _digest(self.workflow_digest)


@dataclass(frozen=True, slots=True)
class CodeQLBinding:
    workflow_id: int
    app_id: int = 15368
    workflow_path: str = "dynamic/github-code-scanning/codeql"
    event: str = "dynamic"
    ref_templates: tuple[str, ...] = ("refs/pull/{pr}/merge",)

    def __post_init__(self) -> None:
        _integer(self.workflow_id); _integer(self.app_id)
        if self.workflow_path != "dynamic/github-code-scanning/codeql" or self.event != "dynamic":
            raise c.Invalid("codeql_producer_unsupported")
        c._tuple(self.ref_templates, str, 2, 1)
        if len(set(self.ref_templates)) != len(self.ref_templates) or any(value not in {"refs/pull/{pr}/merge", "refs/pull/{pr}/head"} for value in self.ref_templates):
            raise c.Invalid("codeql_ref_unsupported")


@dataclass(frozen=True, slots=True)
class CheckPlan:
    producers: tuple[Producer, ...]
    codeql: CodeQLBinding | None = None

    def __post_init__(self) -> None:
        c._tuple(self.producers, Producer, 480, 1)
        if self.codeql is not None and type(self.codeql) is not CodeQLBinding: raise c.Invalid("codeql_binding_invalid")
        contexts = [(value.binding.context, value.binding.app_id) for value in self.producers]
        if len(set(contexts)) != len(contexts): raise c.Invalid("producer_duplicate")
        if not any(value.receipt is not None for value in self.producers):
            raise c.Invalid("producer_receipt_missing")

    @property
    def digest(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True, slots=True)
class CheckPlanV2:
    producers: tuple[Producer, ...]
    applicability: m.MappingBinding
    codeql: CodeQLBinding | None = None

    def __post_init__(self) -> None:
        CheckPlan(self.producers, self.codeql)
        if type(self.applicability) is not m.MappingBinding:
            raise c.Invalid("check_plan_applicability")

    @property
    def digest(self) -> str:
        return _hash({"schema_version": 2, **asdict(self)})


NativeCheckPlan: TypeAlias = CheckPlan | CheckPlanV2


def check_plan_data(plan: NativeCheckPlan) -> dict[str, object]:
    if type(plan) not in {CheckPlan, CheckPlanV2}: raise c.Invalid("check_plan_type")
    return {"schema_version": 2 if type(plan) is CheckPlanV2 else 1, **asdict(plan)}


def parse_check_plan(value: object) -> NativeCheckPlan:
    data = _object(value)
    version = data.get("schema_version")
    expected = {"schema_version", "producers"} | ({"applicability"} if version == 2 else set())
    if set(data) - {"codeql"} != expected or type(version) is not int or version not in {1, 2}:
        raise c.Invalid("check_plan_fields")
    producers: list[Producer] = []
    for raw in _array(data["producers"], 512):
        producer = _object(raw)
        if set(producer) != {"binding", "workflow_digest", "receipt"}: raise c.Invalid("producer_fields")
        binding = _object(producer["binding"])
        if set(binding) != {"context", "app_id", "workflow_id", "workflow_path", "event"}: raise c.Invalid("check_binding_fields")
        receipt: ReceiptBinding | None = None
        if producer["receipt"] is not None:
            item = _object(producer["receipt"])
            if set(item) != {"artifact_name", "member", "fields", "literals"}: raise c.Invalid("receipt_binding_fields")
            fields: list[IdentityField] = []
            literals: list[LiteralField] = []
            for entry in _array(item["fields"], 32):
                field = _object(entry)
                if set(field) != {"path", "fact"}: raise c.Invalid("producer_field_fields")
                fields.append(IdentityField(tuple(_text(part, 256) for part in _array(field["path"], 16)), _text(field["fact"], 64)))
            for entry in _array(item["literals"], 32):
                literal = _object(entry)
                if set(literal) != {"path", "value"}: raise c.Invalid("producer_literal_fields")
                literals.append(LiteralField(tuple(_text(part, 256) for part in _array(literal["path"], 16)), literal["value"]))
            receipt = ReceiptBinding(_text(item["artifact_name"], 256), _text(item["member"], 256), tuple(fields), tuple(literals))
        producers.append(Producer(CheckBinding(_text(binding["context"], 256), _integer(binding["app_id"]),
            _integer(binding["workflow_id"]), _text(binding["workflow_path"], 256), _text(binding["event"], 64)),
            _digest(producer["workflow_digest"]), receipt))
    codeql: CodeQLBinding | None = None
    if data.get("codeql") is not None:
        value = _object(data["codeql"])
        if set(value) != {"workflow_id", "app_id", "workflow_path", "event", "ref_templates"}: raise c.Invalid("codeql_binding_fields")
        codeql = CodeQLBinding(_integer(value["workflow_id"]), _integer(value["app_id"]), _text(value["workflow_path"], 256),
            _text(value["event"], 64), tuple(_text(ref, 256) for ref in _array(value["ref_templates"], 2)))
    if version == 1:
        return CheckPlan(tuple(producers), codeql)
    binding = c._object(data["applicability"], "mapping_path mapping_digest")
    return CheckPlanV2(tuple(producers), m.MappingBinding(c._text(binding["mapping_path"]),
        c._text(binding["mapping_digest"])), codeql)


@dataclass(frozen=True, slots=True)
class PullFacts:
    number: int
    node_id: str
    head: str
    base: str
    head_ref: str
    base_ref: str
    merge_oid: str | None
    merged: bool
    merged_at: str | None
    known_conflict: bool = False


@dataclass(frozen=True, slots=True)
class GitCommit:
    oid: str
    tree: str
    parents: tuple[str, ...]


class ProofPort(Protocol):
    def prove_refresh(self, source: r.SourceSeries, head: str, base: str, /) -> r.Projection: ...
    def prove_delivery(self, source: r.SourceSeries, projection: r.Projection, merge_oid: str, /) -> tuple[c.CommitPair, ...]: ...
    def excludes_root(self, root: str, heads: tuple[str, ...], /) -> bool: ...


@runtime_checkable
class ScopeProofPort(Protocol):
    def candidate_scope(self, base: str, head: str, /) -> m.CandidateScope: ...


class FailedChecks(c.Unavailable):
    def __init__(self, failure_digest: str) -> None:
        self.failure_digest = _digest(failure_digest)
        super().__init__("native_checks_failed")


class SourceChanged(c.Unavailable):
    """Positive same-PR lifecycle fact, never a transport/identity inference.

    Only the unreserved scheduler may release affected work on this observation.
    An owned uncertain native mutation still requires its normal outcome proof.
    """
    def __init__(self, failure_digest: str) -> None:
        self.failure_digest = _digest(failure_digest)
        super().__init__("native_source_changed")


class NativeRejection(c.Conflict):
    def __init__(self, receipt_digest: str) -> None:
        self.receipt_digest = _digest(receipt_digest)
        super().__init__("native_mutation_rejected")


def verify_introduction(values: Sequence[object], repository: str, pr_number: int, merged_at: str) -> str:
    if len(values) != 1: raise c.Unavailable("native_introducing_pr_ambiguous")
    item = _object(values[0]); base = _object(item.get("base"))
    if (item.get("number") != pr_number or item.get("state") != "closed" or item.get("merged_at") != merged_at
            or item.get("html_url") != f"https://github.com/{repository}/pull/{pr_number}"
            or _object(base.get("repo")).get("full_name") != repository):
        raise c.Unavailable("native_introducing_pr_unbound")
    return _hash(item)


class GitHub:
    """Actual authority adapter; disabled enrollment never grants mutations."""

    def __init__(self, transport: Transport, enrollment: Enrollment, proof: ProofPort | None = None,
                 plan: NativeCheckPlan | None = None, *, policy_path: str | None = None) -> None:
        if policy_path is not None:
            if (not isinstance(policy_path, str) or not policy_path.endswith(".json")
                    or any(part in {".git", ".dbsctr"} for part in PurePosixPath(policy_path).parts)):
                raise c.Invalid("current_enrollment_path_invalid")
            _member(policy_path)
        self.policy_path = policy_path
        self.transport = transport
        self.enrollment = enrollment
        self.proof = proof
        self.plan = plan
        self._objects: dict[str, object] = {}

    def _path(self, path: str) -> str:
        return f"repos/{self.enrollment.repository}" + ("/" + path if path else "")

    def get(self, path: str) -> object:
        try:
            return self.transport.request("GET", self._path(path))
        except ApiFailure as error:
            raise c.Unavailable("native_read_unavailable") from error

    def _write(self, method: str, path: str, body: dict[str, object]) -> object:
        try:
            return self.transport.request(method, self._path(path), body)
        except ApiFailure as error:
            if error.status in {401, 403, 404, 409, 422}:
                raise NativeRejection(_hash({"method": method, "path": path, "status": error.status, "body_digest": _hash(body)})) from None
            raise c.Ambiguous("native_mutation_uncertain") from None

    def pages(self, path: str, key: str | None = None, *, limit: int = 4096) -> list[object]:
        result: list[object] = []
        total: int | None = None
        seen: set[int] = set()
        for page in range(1, (limit + 99) // 100 + 1):
            separator = "&" if "?" in path else "?"
            raw = self.get(f"{path}{separator}per_page=100&page={page}")
            if key is not None:
                value = _object(raw)
                count = value.get("total_count")
                if type(count) is not int or not 0 <= count <= limit: raise c.Unavailable("native_population_unavailable")
                if total is None: total = count
                if count != total: raise c.Unavailable("native_population_changed")
                entries = _array(value.get(key), 100)
            else:
                entries = _array(raw, 100)
            for item in entries:
                record = _object(item)
                if "id" in record:
                    native_id = _integer(record["id"])
                    if native_id in seen: raise c.Unavailable("native_population_duplicate")
                    seen.add(native_id)
                result.append(item)
            if len(result) > limit: raise c.Unavailable("native_population_unavailable")
            if len(entries) < 100:
                if total is not None and len(result) != total: raise c.Unavailable("native_population_incomplete")
                return result
            if total is not None and len(result) == total: return result
        raise c.Unavailable("native_population_unavailable")

    def _repository(self) -> dict[str, object]:
        value = _object(self.get(""))
        if (value.get("id") != self.enrollment.repository_id or value.get("full_name") != self.enrollment.repository
                or value.get("default_branch") != self.enrollment.default_branch):
            raise c.Unavailable("native_repository_changed")
        return value

    def ref(self, branch: str) -> str:
        c._branch(branch)
        value = _object(self.get("git/ref/heads/" + urllib.parse.quote(branch, safe="/")))
        item = _object(value.get("object"))
        if value.get("ref") != "refs/heads/" + branch or item.get("type") != "commit":
            raise c.Unavailable("native_ref_unbound")
        return _oid(item.get("sha"))

    def git_commit(self, oid: str) -> GitCommit:
        _oid(oid)
        cache_key = "commit:" + oid
        raw = self._objects.get(cache_key)
        if raw is None:
            raw = self.get("git/commits/" + oid); self._objects[cache_key] = raw
        value = _object(raw)
        if value.get("sha") != oid: raise c.Unavailable("native_commit_unbound")
        return GitCommit(oid, _oid(_object(value.get("tree")).get("sha")),
                         tuple(_oid(_object(parent).get("sha")) for parent in _array(value.get("parents"), 1025)))

    def git_tree(self, oid: str) -> list[dict[str, object]]:
        _oid(oid); key = "tree:" + oid
        raw = self._objects.get(key)
        if raw is None:
            raw = self.get("git/trees/" + oid); self._objects[key] = raw
        value = _object(raw)
        if value.get("sha") != oid or value.get("truncated") is not False:
            raise c.Unavailable("native_tree_incomplete")
        entries = [_object(entry) for entry in _array(value.get("tree"), 10000)]
        names = [_text(entry.get("path"), 256) for entry in entries]
        if len(set(names)) != len(names) or any("/" in name or name in {".", ".."} for name in names):
            raise c.Unavailable("native_tree_unsafe")
        for entry in entries: _oid(entry.get("sha"))
        return entries

    def _entry(self, head: str, path: str) -> dict[str, object] | None:
        parts = PurePosixPath(_member(path)).parts
        tree = self.git_commit(head).tree
        for index, part in enumerate(parts):
            entries = [entry for entry in self.git_tree(tree) if entry.get("path") == part]
            if not entries: return None
            if len(entries) != 1: raise c.Unavailable("native_tree_ambiguous")
            entry = entries[0]
            if index == len(parts) - 1: return entry
            if entry.get("type") != "tree" or entry.get("mode") != "040000":
                raise c.Unavailable("native_path_not_directory")
            tree = _oid(entry.get("sha"))
        raise c.Invalid("native_path_invalid")

    def file_at(self, head: str, path: str) -> bytes | None:
        entry = self._entry(head, path)
        if entry is None: return None
        if entry.get("type") != "blob" or entry.get("mode") not in {"100644", "100755"}:
            raise c.Unavailable("native_file_not_regular")
        sha = _oid(entry.get("sha")); key = "blob:" + sha
        raw = self._objects.get(key)
        if raw is None:
            raw = self.get("git/blobs/" + sha); self._objects[key] = raw
        value = _object(raw)
        size = value.get("size")
        if value.get("sha") != sha or value.get("encoding") != "base64" or type(size) is not int or not 0 <= size <= c.RECORD_LIMIT:
            raise c.Unavailable("native_blob_unqualified")
        content = value.get("content")
        if not isinstance(content, str) or len(content) > 2 * c.RECORD_LIMIT:
            raise c.Unavailable("native_blob_limit")
        try:
            decoded = base64.b64decode("".join(content.split()), validate=True)
        except (ValueError, binascii.Error) as error:
            raise c.Invalid("native_blob_invalid") from error
        if len(decoded) != size: raise c.Unavailable("native_blob_size_changed")
        return decoded

    def _proof(self) -> ProofPort:
        if self.proof is None: raise c.Unavailable("native_correspondence_unavailable")
        return self.proof

    def _ancestor(self, ancestor: str, descendant: str) -> bool:
        return not self._proof().excludes_root(ancestor, (descendant,))

    def _root(self, head: str) -> None:
        if self.git_commit(self.enrollment.root_oid).parents or not self._ancestor(self.enrollment.root_oid, head):
            raise c.Unavailable("control_root_unbound")
        if self._ancestor(self.enrollment.root_oid, self.ref(self.enrollment.default_branch)):
            raise c.Unavailable("control_root_not_orphan")

    def read_control(self, lookup_handles: tuple[str, ...] = ()) -> tuple[str, dict[str, bytes]]:
        c._tuple(lookup_handles, str, 32)
        for handle in lookup_handles: c._handle(handle)
        head = self.ref(self.enrollment.control_branch); self._root(head)
        prefix = "integration/v2/"
        target = self.file_at(head, prefix + "target.json")
        if target is None: raise c.Unavailable("control_state_missing")
        files = {prefix + "target.json": target}
        directory = self._entry(head, prefix + "tickets")
        ticket_handles: list[str] = []
        if directory is not None:
            if directory.get("type") != "tree": raise c.Unavailable("control_inventory_invalid")
            for entry in self.git_tree(_oid(directory.get("sha"))):
                name = _text(entry.get("path"), 256)
                if not name.endswith(".json"): raise c.Unavailable("control_inventory_invalid")
                handle = name[:-5]; c._handle(handle); ticket_handles.append(handle)
        if len(ticket_handles) > c.MAX_TICKETS: raise c.Unavailable("control_inventory_limit")
        obligations: set[str] = set()
        for handle in ticket_handles:
            path = prefix + "tickets/" + handle + ".json"
            payload = self.file_at(head, path)
            if payload is None: raise c.Unavailable("control_ticket_missing")
            files[path] = payload
            ticket = _object(decode_json(payload)); obligation = _text(ticket.get("obligation_handle"), 64)
            c._handle(obligation); obligations.add(obligation)
        for handle in lookup_handles:
            path = prefix + "archive/tickets/" + handle + ".json"
            payload = self.file_at(head, path)
            if payload is not None:
                files[path] = payload
                ticket = _object(_object(decode_json(payload)).get("ticket"))
                obligation = _text(ticket.get("obligation_handle"), 64); c._handle(obligation); obligations.add(obligation)
        for handle in obligations:
            path = prefix + "obligations/" + handle + ".json"
            payload = self.file_at(head, path)
            if payload is None: raise c.Unavailable("control_obligation_missing")
            files[path] = payload
            current = _text(_object(decode_json(payload)).get("current_ticket"), 64); c._handle(current)
            if current not in ticket_handles:
                archive_path = prefix + "archive/tickets/" + current + ".json"
                archive = self.file_at(head, archive_path)
                if archive is None: raise c.Unavailable("control_current_revision_missing")
                files[archive_path] = archive
        r.load_snapshot(files)
        return head, files

    def lookup_archive(self, handle: str, at_head: str | None = None) -> tuple[str, bytes | None]:
        c._handle(handle)
        head = self.ref(self.enrollment.control_branch) if at_head is None else _oid(at_head)
        self._root(head)
        return head, self.file_at(head, "integration/v2/archive/tickets/" + handle + ".json")

    def lookup_obligation(self, handle: str, at_head: str | None = None) -> tuple[str, bytes | None]:
        c._handle(handle)
        head = self.ref(self.enrollment.control_branch) if at_head is None else _oid(at_head)
        self._root(head)
        return head, self.file_at(head, "integration/v2/obligations/" + handle + ".json")

    def _rules(self, branch: str) -> list[object]:
        raw = self.pages("rules/branches/" + urllib.parse.quote(branch, safe=""), limit=512)
        identifiers = {_integer(_object(rule).get("ruleset_id")) for rule in raw}
        result: list[object] = []
        for identifier in sorted(identifiers):
            value = _object(self.get(f"rulesets/{identifier}"))
            if value.get("id") != identifier or value.get("enforcement") != "active":
                raise c.Unavailable("native_ruleset_changed")
            result.append(value)
        return result

    def _classic(self, branch: str) -> object:
        try:
            return self.transport.request("GET", self._path("branches/" + urllib.parse.quote(branch, safe="") + "/protection"))
        except ApiFailure as error:
            if error.status == 404: return None
            raise c.Unavailable("native_policy_unavailable") from error

    def observe_control(self) -> str:
        rules = self._rules(self.enrollment.control_branch)
        classic = self._classic(self.enrollment.control_branch)
        requires_admins = classic is not None or any(_object(actor).get("actor_type") == "RepositoryRole"
            for raw in rules for actor in _array(_object(raw).get("bypass_actors"), 128))
        admin_ids: tuple[int, ...] | None = None
        if requires_admins:
            collaborators = self.pages("collaborators?affiliation=all", limit=4096)
            admins: list[int] = []
            for raw in collaborators:
                user = _object(raw); permissions = _object(user.get("permissions"))
                if type(permissions.get("admin")) is not bool: raise c.Unavailable("control_writer_expansion_unavailable")
                if permissions["admin"] is True: admins.append(_integer(user.get("id")))
            admin_ids = tuple(sorted(admins))
        actors = tuple(ControlActor("User", uid) for uid in self.enrollment.mutator_user_ids) + tuple(
            ControlActor("Integration", app) for app in self.enrollment.mutator_app_ids)
        return verify_control_policy(rules, actors, admin_ids=admin_ids, classic=classic)

    def codeql_setup(self) -> object:
        try:
            return self.transport.request("GET", self._path("code-scanning/default-setup"))
        except ApiFailure as error:
            if error.status == 404: return None
            raise c.Unavailable("codeql_configuration_unavailable") from error

    def observe_policy(self) -> TargetGuards:
        self._repository(); control = self.observe_control()
        target = verify_target_policy(self._classic(self.enrollment.default_branch),
            self._rules(self.enrollment.default_branch), review_exception=self.enrollment.review_exception)
        setup = self.codeql_setup()
        if target.code_scanning and (setup is None or _object(setup).get("state") != "configured"):
            raise c.Unavailable("codeql_configuration_unavailable")
        fingerprint = native_guard_digest(_hash({"guards": target.digest, "codeql_setup": setup}), control)
        if self.enrollment.native_guard_digest is not None and fingerprint != self.enrollment.native_guard_digest:
            raise c.Unavailable("native_guard_drift")
        return TargetGuards(target.checks, target.code_scanning, fingerprint)

    def _current_enrollment(self) -> None:
        # Import the existing policy owner lazily, never a callback or module
        # named by provider data. No constructor/default-off path performs I/O.
        from .controller import parse_config, policy_identity
        if self.policy_path is None: raise c.Unavailable("current_enrollment_binding_missing")
        self._repository()
        current = self.ref(self.enrollment.default_branch)
        raw = self.file_at(current, self.policy_path)
        if raw is None: raise c.Unavailable("current_enrollment_missing")
        try:
            selected = parse_config(raw)
        except c.Invalid:
            raise c.Unavailable("current_enrollment_unqualified") from None
        if (not selected.enabled or selected.enrollment != self.enrollment or selected.check_plan != self.plan
                or policy_identity(selected) != self.enrollment.policy_digest):
            raise c.Unavailable("current_enrollment_revoked_or_changed")

    def _live(self) -> None:
        if not self.enrollment.enabled: raise c.Unavailable("coordinator_disabled")
        if self.enrollment.native_guard_digest is None: raise c.Unavailable("native_guard_pin_missing")
        if self.policy_path is None: raise c.Unavailable("current_enrollment_binding_missing")
        self._current_enrollment()

    def append(self, request: r.AppendRequest) -> str:
        self._live()
        if (request.control_branch != self.enrollment.control_branch or request.state.target.repository != self.enrollment.repository
                or request.state.target.root_oid != self.enrollment.root_oid or request.state.target.policy_digest != self.enrollment.policy_digest):
            raise c.Conflict("control_append_binding")
        self.observe_policy()
        if self.ref(self.enrollment.control_branch) != request.expected_head: raise c.Conflict("control_tip_changed")
        self._root(request.expected_head)
        if len(request.parents) > 1 and not self._proof().excludes_root(self.enrollment.root_oid, request.parents[1:]):
            raise c.Conflict("retention_contains_control_root")
        for parent in request.parents: self.git_commit(parent)
        before_records = {"integration/v2/target.json": r.encode(request.before.target)}
        before_records.update({"integration/v2/tickets/" + ticket.handle + ".json": r.encode(ticket) for ticket in request.before.tickets})
        before_records.update({"integration/v2/obligations/" + row.handle + ".json": r.encode(row) for row in request.before.obligations})
        before_records.update({"integration/v2/archive/tickets/" + row.ticket.handle + ".json": r.encode(row) for row in request.before.archives})
        for path, before_image in before_records.items():
            if self.file_at(request.expected_head, path) != before_image:
                raise c.Conflict("control_before_image_changed")
        old_tickets = {ticket.handle for ticket in request.before.tickets}
        old_obligations = {obligation.handle for obligation in request.before.obligations}
        for path, encoded in request.additions:
            raw = base64.b64decode(encoded, validate=True)
            existing = self.file_at(request.expected_head, path)
            if path.startswith("integration/v2/archive/tickets/") and existing is not None and existing != raw:
                raise c.Conflict("archive_immutable")
            if path.startswith("integration/v2/tickets/"):
                handle = path.rsplit("/", 1)[-1][:-5]
                if handle not in old_tickets and (existing is not None or self.file_at(request.expected_head, "integration/v2/archive/tickets/" + handle + ".json") is not None):
                    raise c.Conflict("ticket_handle_reused")
            if path.startswith("integration/v2/obligations/"):
                handle = path.rsplit("/", 1)[-1][:-5]
                if handle not in old_obligations and existing is not None: raise c.Conflict("obligation_handle_reused")
        if len(request.parents) == 1:
            try:
                result = _object(self.transport.request("POST", "graphql", {"query": "mutation($input:CreateCommitOnBranchInput!){createCommitOnBranch(input:$input){commit{oid} ref{target{oid}}}}", "variables": {"input": request.graphql()}}))
            except ApiFailure as error:
                if error.status in {401, 403, 404, 409, 422}: raise c.Conflict("control_append_rejected") from None
                raise c.Ambiguous("control_append_uncertain") from None
            if result.get("errors"):
                raise c.Ambiguous("control_append_uncertain")
            value = _object(_object(result.get("data")).get("createCommitOnBranch"))
            commit = _oid(_object(value.get("commit")).get("oid"))
            if _object(_object(value.get("ref")).get("target")).get("oid") != commit: raise c.Ambiguous("control_append_uncertain")
        else:
            entries: list[dict[str, object]] = []
            for path, encoded in request.additions:
                try: content = base64.b64decode(encoded, validate=True).decode("utf-8")
                except (UnicodeError, ValueError, binascii.Error) as error: raise c.Invalid("control_encoding_invalid") from error
                entries.append({"path": path, "mode": "100644", "type": "blob", "content": content})
            entries.extend({"path": path, "mode": "100644", "type": "blob", "sha": None} for path in request.deletions)
            tree = _object(self._write("POST", "git/trees", {"base_tree": self.git_commit(request.expected_head).tree, "tree": entries}))
            tree_oid = _oid(tree.get("sha"))
            created = _object(self._write("POST", "git/commits", {"message": "chore(integration): append retained state", "tree": tree_oid, "parents": list(request.parents)}))
            commit = _oid(created.get("sha"))
            if self.git_commit(commit).parents != request.parents or self.git_commit(commit).tree != tree_oid:
                raise c.Ambiguous("control_append_uncertain")
            self._write("PATCH", "git/refs/heads/" + urllib.parse.quote(request.control_branch, safe="/"), {"sha": commit, "force": False})
        observed = self.git_commit(commit)
        if observed.parents != request.parents or self.ref(request.control_branch) != commit:
            raise c.Ambiguous("control_append_uncertain")
        for path, encoded in request.additions:
            if self.file_at(commit, path) != base64.b64decode(encoded, validate=True): raise c.Ambiguous("control_append_uncertain")
        for path in request.deletions:
            if self.file_at(commit, path) is not None: raise c.Ambiguous("control_append_uncertain")
        return commit


    def observe_pr(self, number: int) -> PullFacts:
        _integer(number); self._repository()
        value = _object(self.get(f"pulls/{number}"))
        head, base = _object(value.get("head")), _object(value.get("base"))
        for side in (head, base):
            repo = _object(side.get("repo"))
            if repo.get("id") != self.enrollment.repository_id or repo.get("full_name") != self.enrollment.repository:
                raise c.Unavailable("native_pr_repository_unbound")
        head_ref, base_ref = _text(head.get("ref"), 256), _text(base.get("ref"), 256)
        c._branch(head_ref); c._branch(base_ref)
        merged, merged_at, draft = value.get("merged"), value.get("merged_at"), value.get("draft")
        node_id = _text(value.get("node_id"), 256)
        head_oid, base_oid = _oid(head.get("sha")), _oid(base.get("sha"))
        if (type(value.get("number")) is not int or value["number"] != number or type(merged) is not bool
                or type(draft) is not bool or base_ref != self.enrollment.default_branch
                or head_ref in {self.enrollment.default_branch, self.enrollment.control_branch, "main", "master"}):
            raise c.Unavailable("native_pr_target_unbound")
        state = value.get("state")
        if not merged and merged_at is None and (state == "closed" or state == "open" and draft):
            raise SourceChanged(_hash({"repository": self.enrollment.repository, "pr": number, "node_id": node_id,
                "head": head_oid, "base": base_oid, "head_ref": head_ref, "base_ref": base_ref,
                "state": state, "draft": draft, "merged": False}))
        if draft:
            raise c.Unavailable("native_pr_target_unbound")
        if merged:
            if state != "closed" or not isinstance(merged_at, str):
                raise c.Unavailable("native_merge_unbound")
            _time(merged_at)
        elif state != "open" or merged_at is not None or base_oid != self.ref(self.enrollment.default_branch):
            raise c.Unavailable("native_pr_base_moved")
        merge_oid = value.get("merge_commit_sha")
        return PullFacts(number, node_id, head_oid, base_oid, head_ref, base_ref,
                         None if merge_oid is None else _oid(merge_oid), merged, merged_at,
                         value.get("mergeable") is False and value.get("mergeable_state") == "dirty")

    def _interval(self, head: str, base: str, count: int) -> tuple[str, ...]:
        if not 1 <= count <= 1024: raise c.Unavailable("native_interval_limit")
        cursor = _oid(head); reverse: list[str] = []
        for _ in range(count):
            if cursor == base: raise c.Unavailable("native_interval_incomplete")
            commit = self.git_commit(cursor)
            if len(commit.parents) != 1: raise c.Unavailable("native_interval_not_linear")
            reverse.append(cursor); cursor = commit.parents[0]
        if cursor != base: raise c.Unavailable("native_interval_not_exact")
        return tuple(reversed(reverse))

    def projection(self, source: r.SourceSeries, head: str, base: str) -> r.Projection:
        if source.repository != self.enrollment.repository: raise c.Unavailable("native_source_repository_unbound")
        native = self.observe_pr(source.pr_number)
        if native.merged or native.head != head or native.base != base: raise c.Unavailable("native_projection_drift")
        comparison = _object(self.get(f"compare/{base}...{head}"))
        if _object(comparison.get("merge_base_commit")).get("sha") != base:
            raise c.Unavailable("native_projection_base_unbound")
        try:
            result = self._proof().prove_refresh(source, head, base)
        except c.Invalid as error:
            raise SourceChanged(_hash({"source": c.identity(source), "head": head, "base": base,
                "proof_refusal_digest": _hash({"reason": str(error)})})) from None
        interval = self._interval(head, base, len(source.entries))
        if (result.source_digest != c.identity(source) or result.head != head or result.base != base
                or tuple(pair.original for pair in result.mapping) != tuple(entry.oid for entry in source.entries)
                or tuple(pair.landed for pair in result.mapping) != interval):
            raise c.Unavailable("native_projection_proof_unbound")
        if self.observe_pr(source.pr_number) != native: raise c.Unavailable("native_projection_drift")
        return result

    def candidate(self, ticket: r.Ticket, generation: int, projection: r.Projection) -> r.Candidate:
        if self.plan is None: raise c.Unavailable("native_check_plan_missing")
        if projection.source_digest != c.identity(ticket.source): raise c.Unavailable("native_projection_source_unbound")
        native = self.observe_pr(ticket.source.pr_number)
        if native.merged or native.head != projection.head or native.base != projection.base or native.merge_oid is None:
            raise c.Unavailable("native_candidate_unavailable")
        tested = self.git_commit(native.merge_oid)
        if tested.parents != (native.base, native.head): raise c.Unavailable("native_candidate_parents_unbound")
        return r.Candidate(generation, c.identity(ticket.source), c.identity(projection), native.head, native.base,
            tested.oid, tested.parents, tested.tree, self.plan.digest, self.enrollment.policy_digest)

    def _candidate_facts(self, candidate: r.Candidate, number: int) -> PullFacts:
        native = self.observe_pr(number)
        if (native.merged or native.head != candidate.head or native.base != candidate.base
                or native.merge_oid != candidate.tested_oid or candidate.policy_digest != self.enrollment.policy_digest
                or self.plan is None or candidate.plan_digest != self.plan.digest):
            raise c.Unavailable("native_candidate_changed")
        tested = self.git_commit(candidate.tested_oid)
        if tested.tree != candidate.tree or tested.parents != candidate.tested_parents:
            raise c.Unavailable("native_candidate_changed")
        return native

    def _run_candidates(self, workflow_id: int, event: str, head: str, pr_number: int) -> list[dict[str, object]]:
        values = self.pages(f"actions/workflows/{workflow_id}/runs?head_sha={head}&event={event}", "workflow_runs", limit=1024)
        matches: list[dict[str, object]] = []
        for raw in values:
            run = _object(raw)
            if run.get("workflow_id") != workflow_id or run.get("event") != event or run.get("head_sha") != head:
                raise c.Unavailable("native_run_filter_unbound")
            if event == "pull_request" and not any(_object(pr).get("number") == pr_number for pr in _array(run.get("pull_requests"), 128)):
                continue
            matches.append(run)
        return matches

    def _run(self, workflow_id: int, event: str, head: str, pr_number: int) -> dict[str, object]:
        matches = self._run_candidates(workflow_id, event, head, pr_number)
        if not matches: raise c.Unavailable("native_run_missing")
        # Native run IDs increase on creation; a rerun retains its ID and is
        # subsequently read afresh to obtain its actual current attempt.
        selected = max(matches, key=lambda item: _integer(item.get("id")))
        run = _object(self.get("actions/runs/" + str(_integer(selected.get("id")))))
        if (run.get("id") != selected.get("id") or run.get("workflow_id") != workflow_id
                or run.get("event") != event or run.get("head_sha") != head):
            raise c.Unavailable("native_run_changed")
        repository = _object(run.get("repository"))
        if repository.get("id") != self.enrollment.repository_id or repository.get("full_name") != self.enrollment.repository:
            raise c.Unavailable("native_run_repository_unbound")
        _integer(run.get("run_attempt"))
        return run

    def _skipped_producer(self, producer: Producer, run: dict[str, object], candidate: r.Candidate, number: int) -> str:
        binding = producer.binding
        run_id, attempt = _integer(run.get("id")), _integer(run.get("run_attempt"))
        if run.get("path") != binding.workflow_path or run.get("status") != "completed":
            raise c.Unavailable("native_skipped_producer_unbound")
        jobs = self.pages(f"actions/runs/{run_id}/attempts/{attempt}/jobs", "jobs", limit=1024)
        found = [_object(job) for job in jobs if _object(job).get("name") == binding.context]
        if len(found) != 1: raise c.Unavailable("native_skipped_job_unbound")
        job = found[0]
        prefix = "https://api.github.com/" + self._path("check-runs/")
        url = _text(job.get("check_run_url"), 2048)
        if not url.startswith(prefix) or re.fullmatch(r"[1-9][0-9]*", url[len(prefix):]) is None:
            raise c.Unavailable("native_skipped_check_unbound")
        check = _object(self.get("check-runs/" + url[len(prefix):]))
        # Reuse the native identity verifier without representing a skip as a
        # passing Evidence. The false predicate and observed skip are both needed.
        success = {"status": "completed", "conclusion": "success"}
        verify_check({**check, **success}, {**job, **success}, {**run, **success}, binding,
            head=candidate.head, tested_oid=candidate.tested_oid, pr_number=number,
            producer_digest=_hash(asdict(producer)))
        if any(item.get("status") != "completed" or item.get("conclusion") != "skipped" for item in (job, check)):
            raise c.Unavailable("native_predicate_observation_conflict")
        return _hash({"producer": asdict(producer), "run": run, "job": job, "check": check})

    def _applicable_producers(self, candidate: r.Candidate, number: int, guards: TargetGuards
            ) -> tuple[tuple[Producer, ...], str | None, tuple[tuple[Producer, dict[str, object] | None, str | None], ...]]:
        if not isinstance(self.plan, CheckPlanV2):
            assert self.plan is not None
            return self.plan.producers, None, ()
        binding = self.plan.applicability
        raw = self.file_at(candidate.base, binding.mapping_path)
        if (raw is None or hashlib.sha256(raw).hexdigest() != binding.mapping_digest
                or self.file_at(candidate.tested_oid, binding.mapping_path) != raw):
            raise c.Unavailable("native_applicability_authority_changed")
        rules = m.parse_mapping(decode_json(raw))
        by_context = {(rule.context, rule.app_id): rule for rule in rules}
        registered = {(producer.binding.context, producer.binding.app_id) for producer in self.plan.producers}
        if not set(by_context) <= registered: raise c.Unavailable("native_applicability_producer_unbound")
        required = {(check.context, check.app_id) for check in guards.checks}
        if any(key in required and rule.predicates for key, rule in by_context.items()):
            raise c.Unavailable("native_required_check_conditional")
        proof = self._proof()
        if not isinstance(proof, ScopeProofPort): raise c.Unavailable("native_scope_proof_missing")
        try:
            scope = proof.candidate_scope(candidate.base, candidate.head)
        except c.Invalid:
            raise c.Unavailable("native_scope_unqualified") from None
        if type(scope) is not m.CandidateScope or scope.base != candidate.base or scope.head != candidate.head:
            raise c.Unavailable("native_scope_unbound")
        selected: list[Producer] = []
        decisions: list[object] = []
        fences: list[tuple[Producer, dict[str, object] | None, str | None]] = []
        for producer in self.plan.producers:
            check = producer.binding
            workflow = self.file_at(candidate.base, check.workflow_path)
            if (workflow is None or hashlib.sha256(workflow).hexdigest() != producer.workflow_digest
                    or self.file_at(candidate.tested_oid, check.workflow_path) != workflow):
                raise c.Unavailable("native_applicability_workflow_changed")
            rule = by_context.get((check.context, check.app_id))
            if rule is None or not rule.predicates:
                selected.append(producer)
                continue
            if check.event != "pull_request": raise c.Unavailable("native_applicability_event_unsupported")
            results: list[tuple[str, bool]] = []
            actor_run: dict[str, object] | None = None
            for predicate in rule.predicates:
                value = predicate.value
                if predicate.kind == "paths":
                    assert isinstance(value, tuple)
                    result = any(m.path_matches(pattern, path) for pattern in value for path in scope.paths)
                else:
                    assert isinstance(value, str)
                    if predicate.kind == "event":
                        result = check.event == value
                    elif predicate.kind == "target_branch":
                        result = self.enrollment.default_branch == value
                    else:
                        if actor_run is None:
                            actor_run = self._run(check.workflow_id, check.event, candidate.head, number)
                            if actor_run.get("path") != check.workflow_path:
                                raise c.Unavailable("native_actor_workflow_unbound")
                        actor = _object(actor_run.get("actor"))
                        _integer(actor.get("id"))
                        result = _text(actor.get("login"), 128).casefold() != value.casefold()
                results.append((predicate.kind, result))
            applies = all(result for _, result in results)
            skipped_digest: str | None = None
            if not applies:
                observed = self._run_candidates(check.workflow_id, check.event, candidate.head, number)
                if not observed:
                    fences.append((producer, None, None))
                elif all(kind in {"paths", "target_branch"} for kind, result in results if not result):
                    # Provider diff fallbacks may start a filtered workflow.
                    # An observed run must then qualify normally, never disappear.
                    applies = True
                else:
                    # The false actor decision and skip must use the same native
                    # snapshot. The final fence rejects any newer run/attempt.
                    if actor_run is None:
                        actor_run = self._run(check.workflow_id, check.event, candidate.head, number)
                    skipped_digest = self._skipped_producer(producer, actor_run, candidate, number)
            if actor_run is not None: fences.append((producer, actor_run, skipped_digest))
            if applies: selected.append(producer)
            decisions.append({"producer": asdict(producer), "rule": asdict(rule), "results": results,
                              "applicable": applies, "actor_run": actor_run, "skipped_proof": skipped_digest})
        if not selected: raise c.Unavailable("native_positive_producer_missing")
        digest = _hash({"kind": "native_applicability", "candidate": c.identity(candidate),
            "binding": asdict(binding), "scope": asdict(scope), "decisions": decisions})
        return tuple(selected), digest, tuple(fences)

    def _applicability_fences(self, candidate: r.Candidate, number: int,
            fences: tuple[tuple[Producer, dict[str, object] | None, str | None], ...]) -> None:
        for producer, observed, skipped_digest in fences:
            binding = producer.binding
            if observed is None:
                if self._run_candidates(binding.workflow_id, binding.event, candidate.head, number):
                    raise c.Unavailable("native_applicability_run_appeared")
            else:
                current = self._run(binding.workflow_id, binding.event, candidate.head, number)
                if _hash(current) != _hash(observed): raise c.Unavailable("native_applicability_attempt_changed")
                if skipped_digest is not None and self._skipped_producer(producer, current, candidate, number) != skipped_digest:
                    raise c.Unavailable("native_applicability_skip_changed")

    def _success(self, value: Mapping[str, object], *, kind: str) -> None:
        if value.get("status") != "completed": raise c.Unavailable("native_checks_pending")
        conclusion = _text(value.get("conclusion"), 64)
        if conclusion in {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}:
            raise FailedChecks(_hash({"kind": kind, "native": dict(value)}))
        if conclusion != "success": raise c.Unavailable("native_checks_unqualified")

    def _receipt(self, producer: Producer, run: dict[str, object], candidate: r.Candidate, number: int) -> str | None:
        binding = producer.receipt
        if binding is None: return None
        run_id, attempt = _integer(run.get("id")), _integer(run.get("run_attempt"))
        name = binding.artifact_name.format(attempt=attempt, head=candidate.head, tested=candidate.tested_oid, pr=number)
        values = self.pages(f"actions/runs/{run_id}/artifacts", "artifacts", limit=4096)
        found = [_object(item) for item in values if _object(item).get("name") == name]
        if len(found) != 1: raise c.Unavailable("native_receipt_missing_or_ambiguous")
        metadata = found[0]
        try:
            zipped = self.transport.archive(self._path("actions/artifacts/" + str(_integer(metadata.get("id"))) + "/zip"))
        except ApiFailure as error:
            raise c.Unavailable("native_receipt_unavailable") from error
        receipt = read_artifact(zipped, metadata, run_id=run_id, repository_id=self.enrollment.repository_id,
            source_head=candidate.head, member=binding.member)
        facts: dict[str, object] = {"repository": self.enrollment.repository, "source_head": candidate.head,
            "tested_oid": candidate.tested_oid, "base": candidate.base, "tree": candidate.tree,
            "run_id": run_id, "attempt": attempt, "run_id_text": str(run_id), "attempt_text": str(attempt), "event": run.get("event"),
            "pr_number": number, "tested_parents": candidate.tested_parents}
        def field(path: tuple[str, ...]) -> object:
            cursor: object = receipt
            for key in path:
                row = _object(cursor)
                if key not in row: raise c.Unavailable("native_receipt_field_missing")
                cursor = row[key]
            return cursor
        for expected in binding.fields:
            if _hash(field(expected.path)) != _hash(facts[expected.fact]): raise c.Unavailable("native_receipt_identity_unbound")
        for literal in binding.literals:
            if _hash(field(literal.path)) != _hash(literal.value): raise c.Unavailable("native_receipt_literal_unbound")
        return _hash({"metadata": metadata, "receipt": receipt, "producer": asdict(producer)})

    def _scan(self, candidate: r.Candidate, number: int, setup: object) -> tuple[c.Evidence, ...]:
        if self.plan is None or self.plan.codeql is None: raise c.Unavailable("codeql_producer_binding_missing")
        binding = self.plan.codeql
        run = self._run(binding.workflow_id, binding.event, candidate.head, number)
        if run.get("path") != binding.workflow_path: raise c.Unavailable("codeql_workflow_unbound")
        self._success(run, kind="codeql_run")
        run_id, attempt = _integer(run.get("id")), _integer(run.get("run_attempt"))
        jobs = self.pages(f"actions/runs/{run_id}/attempts/{attempt}/jobs", "jobs", limit=512)
        if not jobs: raise c.Unavailable("codeql_jobs_missing")
        for raw in jobs:
            job = _object(raw)
            if job.get("run_id") != run_id or job.get("run_attempt") != attempt or job.get("head_sha") not in {candidate.head, candidate.tested_oid}:
                raise c.Unavailable("codeql_job_unbound")
            check_url = _text(job.get("check_run_url"), 2048)
            prefix = "https://api.github.com/" + self._path("check-runs/")
            if not check_url.startswith(prefix) or re.fullmatch(r"[1-9][0-9]*", check_url[len(prefix):]) is None:
                raise c.Unavailable("codeql_check_unbound")
            check = _object(self.get("check-runs/" + check_url[len(prefix):]))
            if (check.get("id") != int(check_url[len(prefix):]) or check.get("name") != job.get("name")
                    or _object(check.get("app")).get("id") != binding.app_id
                    or check.get("head_sha") not in {candidate.head, candidate.tested_oid}
                    or _object(check.get("check_suite")).get("id") != run.get("check_suite_id")):
                raise c.Unavailable("codeql_check_unbound")
            self._success(job, kind="codeql_job"); self._success(check, kind="codeql_check")
        # Attempts have their own native start timestamp. Original created_at is
        # deliberately insufficient for an old run rerun hours or days later.
        started = _time(run.get("run_started_at")); finished = _time(run.get("updated_at"))
        refs = tuple(ref.format(pr=number) for ref in binding.ref_templates)
        by_id: dict[int, object] = {}
        for ref in refs:
            for raw in self.pages("code-scanning/analyses?tool_name=CodeQL&ref=" + urllib.parse.quote(ref, safe=""), limit=4096):
                value = _object(raw); analysis_id = _integer(value.get("id"))
                if analysis_id in by_id and by_id[analysis_id] != value: raise c.Unavailable("codeql_analysis_changed")
                by_id[analysis_id] = value
        analyses = list(by_id.values())
        evidence = verify_codeql(setup, analyses, accepted_oids=(candidate.head, candidate.tested_oid), accepted_refs=refs,
            attempt=attempt, started=started, finished=finished)
        current = _object(self.get(f"actions/runs/{run_id}"))
        if current.get("run_attempt") != attempt or current.get("status") != "completed" or current.get("conclusion") != "success":
            raise c.Unavailable("codeql_attempt_changed")
        return tuple(c.Evidence(item.kind, binding.app_id, item.native_id, attempt, item.subject_oid,
            _hash({"analysis": item.producer_digest, "run": run, "jobs": jobs, "binding": asdict(binding)})) for item in evidence)

    def qualify(self, candidate: r.Candidate, pr_number: int) -> c.Qualification:
        guards = self.observe_policy(); self._candidate_facts(candidate, pr_number)
        if self.plan is None: raise c.Unavailable("native_check_plan_missing")
        enrolled = {(producer.binding.context, producer.binding.app_id) for producer in self.plan.producers}
        if any((check.context, check.app_id) not in enrolled for check in guards.checks):
            raise c.Unavailable("native_required_producer_not_enrolled")
        producers, applicability_digest, applicability_fences = self._applicable_producers(candidate, pr_number, guards)
        checks: dict[int, dict[str, object]] = {}
        for head in dict.fromkeys((candidate.head, candidate.tested_oid)):
            for raw in self.pages(f"commits/{head}/check-runs?filter=latest", "check_runs", limit=1024):
                value = _object(raw); native_id = _integer(value.get("id"))
                if native_id in checks and checks[native_id] != value: raise c.Unavailable("native_check_changed")
                checks[native_id] = value
        runs: dict[tuple[int, str], dict[str, object]] = {}
        receipts: set[tuple[int, int]] = set()
        receiptless: list[tuple[int, int]] = []
        evidence: list[c.Evidence] = []
        for producer in producers:
            binding = producer.binding; key = (binding.workflow_id, binding.event)
            if key not in runs: runs[key] = self._run(*key, candidate.head, pr_number)
            run = runs[key]
            if run.get("path") != binding.workflow_path: raise c.Unavailable("native_workflow_unbound")
            workflow = self.file_at(candidate.tested_oid, binding.workflow_path)
            if workflow is None or hashlib.sha256(workflow).hexdigest() != producer.workflow_digest:
                raise c.Unavailable("native_workflow_source_changed")
            self._success(run, kind="workflow_run")
            run_id, attempt = _integer(run.get("id")), _integer(run.get("run_attempt"))
            jobs = self.pages(f"actions/runs/{run_id}/attempts/{attempt}/jobs", "jobs", limit=1024)
            found = [_object(job) for job in jobs if _object(job).get("name") == binding.context]
            if len(found) != 1: raise c.Unavailable("native_job_missing_or_ambiguous")
            job = found[0]
            url = _text(job.get("check_run_url"), 2048)
            prefix = "https://api.github.com/" + self._path("check-runs/")
            if not url.startswith(prefix) or re.fullmatch(r"[1-9][0-9]*", url[len(prefix):]) is None:
                raise c.Unavailable("native_job_check_unbound")
            check_id = int(url[len(prefix):]); check = checks.get(check_id)
            if check is None: raise c.Unavailable("native_check_missing")
            successful = {"status": "completed", "conclusion": "success"}
            # Bind native identities before deciding that a red label belongs to
            # this task. A foreign or old job is unavailable evidence, not repair.
            verify_check({**check, **successful}, {**job, **successful}, {**run, **successful}, binding,
                head=candidate.head, tested_oid=candidate.tested_oid, pr_number=pr_number, producer_digest=_hash(asdict(producer)))
            self._success(job, kind="job"); self._success(check, kind="check")
            receipt_digest = self._receipt(producer, run, candidate, pr_number)
            if receipt_digest is None: receiptless.append((run_id, attempt))
            else: receipts.add((run_id, attempt))
            producer_facts: dict[str, object] = {"producer": asdict(producer), "receipt": receipt_digest}
            if applicability_digest is not None: producer_facts["applicability"] = applicability_digest
            evidence.append(verify_check(check, job, run, binding, head=candidate.head, tested_oid=candidate.tested_oid,
                pr_number=pr_number, producer_digest=_hash(producer_facts)))
        if any(value not in receipts for value in receiptless): raise c.Unavailable("native_aggregate_candidate_unproven")
        setup = self.codeql_setup()
        if guards.code_scanning or setup is not None and _object(setup).get("state") == "configured":
            scans = self._scan(candidate, pr_number, setup)
            if applicability_digest is None:
                evidence.extend(scans)
            else:
                evidence.extend(c.Evidence(item.kind, item.app_id, item.native_id, item.attempt, item.subject_oid,
                    _hash({"native_producer": item.producer_digest, "applicability": applicability_digest})) for item in scans)
        for run in runs.values():
            current = _object(self.get("actions/runs/" + str(_integer(run.get("id")))))
            if current.get("run_attempt") != run.get("run_attempt") or current.get("status") != "completed" or current.get("conclusion") != "success":
                raise c.Unavailable("native_attempt_changed")
        self._candidate_facts(candidate, pr_number)
        self._applicability_fences(candidate, pr_number, applicability_fences)
        if self.observe_policy().digest != guards.digest: raise c.Unavailable("native_guard_drift")
        return c.Qualification(c.identity(candidate), candidate.plan_digest, candidate.policy_digest, guards.digest, tuple(evidence))

    def _approval_required(self) -> bool:
        review: list[dict[str, object]] = []
        classic = self._classic(self.enrollment.default_branch)
        if classic is not None:
            value = _object(classic).get("required_pull_request_reviews")
            if value is not None: review.append(_object(value))
        for raw in self._rules(self.enrollment.default_branch):
            for item in _array(_object(raw).get("rules"), 128):
                rule = _object(item)
                if rule.get("type") == "pull_request": review.append(_object(rule.get("parameters")))
        for rule in review:
            count = rule.get("required_approving_review_count")
            if type(count) is not int or not 0 <= count <= 100: raise c.Unavailable("native_review_policy_unavailable")
            if count > 0: return True
            for field in ("require_code_owner_review", "require_code_owner_reviews", "require_last_push_approval"):
                flag = rule.get(field, False)
                if type(flag) is not bool: raise c.Unavailable("native_review_policy_unavailable")
                if flag: return True
        return False

    def _review_bypass_capable(self) -> bool:
        classic = self._classic(self.enrollment.default_branch)
        if classic is not None:
            protection = _object(classic)
            reviews = protection.get("required_pull_request_reviews")
            if reviews is not None:
                if _object(protection.get("enforce_admins")).get("enabled") is not True:
                    return True
                allowances = _object(reviews).get("bypass_pull_request_allowances")
                if allowances is not None and any(_array(_object(allowances).get(key), 128) for key in ("users", "teams", "apps")):
                    # The classic API lacks an effective-viewer bypass field.
                    # Without a qualified identity expansion, any such allowance
                    # is conservatively unavailable for ordinary delivery.
                    return True
        for raw in self._rules(self.enrollment.default_branch):
            ruleset = _object(raw)
            if any(_object(rule).get("type") == "pull_request" for rule in _array(ruleset.get("rules"), 128)):
                if ruleset.get("current_user_can_bypass") != "never": return True
        return False

    def _delivery_authority(self, ticket: r.Ticket, candidate: r.Candidate) -> None:
        if ticket.delivery_mode == "admin":
            if not self.enrollment.review_exception: raise c.Unavailable("review_exception_not_enrolled")
            return
        approval_required = self._approval_required()
        if approval_required and self._review_bypass_capable():
            raise c.Unavailable("ordinary_review_guard_not_atomic")
        owner, name = self.enrollment.repository.split("/")
        try:
            raw = self.transport.request("POST", "graphql", {
                "query": "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){id headRefOid baseRefOid reviewDecision mergeStateStatus}}}",
                "variables": {"owner": owner, "name": name, "number": ticket.source.pr_number}})
        except ApiFailure as error:
            raise c.Unavailable("native_review_authority_unavailable") from error
        value = _object(raw)
        if value.get("errors"): raise c.Unavailable("native_review_authority_unavailable")
        review = _object(_object(_object(value.get("data")).get("repository")).get("pullRequest"))
        native = self.observe_pr(ticket.source.pr_number)
        if (review.get("id") != native.node_id or review.get("headRefOid") != candidate.head
                or review.get("baseRefOid") != candidate.base or review.get("mergeStateStatus") != "CLEAN"):
            raise c.Unavailable("ordinary_merge_native_requirements_unsatisfied")
        decision = review.get("reviewDecision")
        if decision != "APPROVED" and not (decision is None and not approval_required):
            raise c.Unavailable("ordinary_merge_review_unsatisfied")

    def _fence(self, ticket: r.Ticket, reservation: r.NativeReservation, *, mutation: bool) -> str:
        self._live(); self.observe_policy()
        head, files = self.read_control()
        state = r.load_snapshot(files)
        current = state.ticket(ticket.handle)
        target = state.target
        if (target.repository != self.enrollment.repository or target.default_branch != self.enrollment.default_branch
                or target.root_oid != self.enrollment.root_oid or target.policy_digest != self.enrollment.policy_digest
                or target.active != ticket.handle or target.generation != reservation.generation
                or c.identity(current) != c.identity(ticket) or current.reservation != reservation
                or mutation and reservation.uncertain):
            raise c.Conflict("native_reservation_fence_changed")
        retained = tuple(dict.fromkeys((ticket.source.head, ticket.current_head)))
        if not self._proof().excludes_root(self.enrollment.root_oid, retained):
            raise c.Conflict("retention_contains_control_root")
        if any(not self._ancestor(source, head) for source in retained):
            raise c.Unavailable("native_source_custody_missing")
        return head

    def _refresh_proof(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult:
        native = self.observe_pr(ticket.source.pr_number)
        if native.merged or native.head == reservation.expected_head:
            raise c.Ambiguous("native_refresh_outcome_uncertain")
        projection = self.projection(ticket.source, native.head, native.base)
        return r.RefreshResult(reservation.operation_id, reservation.invocation, reservation.subject_digest, projection,
            _hash({"operation": c.identity(reservation), "native": asdict(native), "projection": c.identity(projection)}))

    def refresh(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult:
        if reservation.uncertain: raise c.Ambiguous("native_prior_effect_unresolved")
        if reservation.kind != "refresh": raise c.Conflict("native_mutation_kind")
        try:
            if not ticket.guarded_refresh: raise c.Unavailable("guarded_refresh_not_authorized")
            self._fence(ticket, reservation, mutation=True)
            native = self.observe_pr(ticket.source.pr_number)
        except (c.Unavailable, c.Conflict, c.Invalid) as error:
            raise NativeRejection(_hash({"reservation": c.identity(reservation), "no_call": type(error).__name__})) from None
        if native.merged or native.head != reservation.expected_head or native.base != reservation.expected_base:
            raise NativeRejection(_hash({"reservation": c.identity(reservation), "reason": "native_refresh_guard_changed"}))
        # A native conflict is only a conservative refusal before any request.
        # It never resolves custody of an already-issued uncertain mutation.
        if native.known_conflict:
            raise NativeRejection(_hash({"reservation": c.identity(reservation),
                "reason": "native_conflict_no_call", "native": asdict(native)}))
        # Establish supported original/current correspondence before rewriting,
        # including unsafe attributes, empty phases and unsupported wrappers.
        # This is read-only proof; a refusal here definitively issued no call.
        try:
            prior_base = ticket.projection.base if ticket.projection is not None else ticket.source.base
            current = self._proof().prove_refresh(ticket.source, native.head, prior_base)
            if ticket.projection is not None and current != ticket.projection:
                raise c.Unavailable("native_current_projection_changed")
        except (c.Unavailable, c.Conflict, c.Invalid) as error:
            raise NativeRejection(_hash({"reservation": c.identity(reservation),
                                         "source_no_call": type(error).__name__})) from None
        variables: dict[str, object] = {"input": {"pullRequestId": native.node_id,
            "expectedHeadOid": reservation.expected_head, "updateMethod": "REBASE", "clientMutationId": reservation.operation_id}}
        try:
            result = _object(self.transport.request("POST", "graphql", {
                "query": "mutation($input:UpdatePullRequestBranchInput!){updatePullRequestBranch(input:$input){clientMutationId pullRequest{id headRefOid}}}",
                "variables": variables}))
        except ApiFailure as error:
            if error.status in {401, 403, 404, 409, 422}:
                raise NativeRejection(_hash({"reservation": c.identity(reservation), "status": error.status})) from None
            raise c.Ambiguous("native_refresh_outcome_uncertain") from None
        if result.get("errors"): raise c.Ambiguous("native_refresh_outcome_uncertain")
        payload = _object(_object(result.get("data")).get("updatePullRequestBranch"))
        pull = _object(payload.get("pullRequest"))
        if payload.get("clientMutationId") != reservation.operation_id or pull.get("id") != native.node_id:
            raise c.Ambiguous("native_refresh_outcome_uncertain")
        actual = _oid(pull.get("headRefOid"))
        proof = self._refresh_proof(ticket, reservation)
        if proof.projection.head != actual: raise c.Ambiguous("native_refresh_outcome_uncertain")
        self._fence(ticket, reservation, mutation=False)
        return proof

    def _delivery_proof(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
        candidate, projection = ticket.candidate, ticket.projection
        if candidate is None or projection is None: raise c.Conflict("native_delivery_candidate_missing")
        native = self.observe_pr(ticket.source.pr_number)
        if not native.merged or native.head != reservation.expected_head or native.merge_oid is None or native.merged_at is None:
            raise c.Ambiguous("native_merge_outcome_uncertain")
        if not self._ancestor(native.merge_oid, self.ref(self.enrollment.default_branch)):
            raise c.Unavailable("native_merge_not_on_default")
        mapping = self._proof().prove_delivery(ticket.source, projection, native.merge_oid)
        if tuple(pair.original for pair in mapping) != tuple(pair.landed for pair in projection.mapping):
            raise c.Unavailable("native_delivery_mapping_unbound")
        interval = self._interval(native.merge_oid, candidate.base, len(mapping))
        if tuple(pair.landed for pair in mapping) != interval:
            raise c.Unavailable("native_delivery_interval_unbound")
        introductions = tuple(verify_introduction(self.pages("commits/" + pair.landed + "/pulls", limit=100),
            self.enrollment.repository, ticket.source.pr_number, native.merged_at) for pair in mapping)
        if self.observe_pr(ticket.source.pr_number) != native:
            raise c.Unavailable("native_merge_observation_changed")
        return r.Delivery(reservation.operation_id, reservation.invocation, c.identity(candidate), c.identity(projection),
            ticket.source.pr_number, native.merge_oid, mapping,
            _hash({"reservation": c.identity(reservation), "native": asdict(native), "mapping": [asdict(pair) for pair in mapping], "introductions": introductions}))

    def merge(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.Delivery:
        if reservation.uncertain: raise c.Ambiguous("native_prior_effect_unresolved")
        if reservation.kind != "merge" or ticket.candidate is None: raise c.Conflict("native_mutation_kind")
        candidate = ticket.candidate
        try:
            self._fence(ticket, reservation, mutation=True)
            if candidate.head != reservation.expected_head or candidate.base != reservation.expected_base:
                raise c.Conflict("native_merge_reservation_unbound")
            if ticket.projection is None or self.projection(ticket.source, candidate.head, candidate.base) != ticket.projection:
                raise c.Unavailable("native_merge_projection_changed")
            # Native strict CI remains the atomic current-base guard during the
            # request; all local checks below are still before any mutation.
            self.qualify(candidate, ticket.source.pr_number)
            self._delivery_authority(ticket, candidate)
            self._fence(ticket, reservation, mutation=True)
            self._candidate_facts(candidate, ticket.source.pr_number)
        except (c.Unavailable, c.Conflict, c.Invalid) as error:
            raise NativeRejection(_hash({"reservation": c.identity(reservation), "no_call": type(error).__name__})) from None
        response = _object(self._write("PUT", f"pulls/{ticket.source.pr_number}/merge", {"sha": candidate.head, "merge_method": "rebase"}))
        if response.get("merged") is False:
            raise NativeRejection(_hash({"reservation": c.identity(reservation), "response": response}))
        if response.get("merged") is not True: raise c.Ambiguous("native_merge_outcome_uncertain")
        proof = self._delivery_proof(ticket, reservation)
        if response.get("sha") != proof.merge_oid: raise c.Ambiguous("native_merge_outcome_uncertain")
        self._fence(ticket, reservation, mutation=False)
        return proof

    def reconcile(self, ticket: r.Ticket, reservation: r.NativeReservation) -> r.RefreshResult | r.Delivery | r.NoEffect:
        self._fence(ticket, reservation, mutation=False)
        # Positive native proof is safe even if the initiating worker vanished.
        # No elapsed lease, unchanged ref, finished run, operator identity or
        # clientMutationId echo proves an uncertain server mutation did not occur.
        if reservation.kind == "refresh":
            return self._refresh_proof(ticket, reservation)
        return self._delivery_proof(ticket, reservation)
