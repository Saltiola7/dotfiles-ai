"""Compose managed Initiative Start and Resume inside the private lifecycle owner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import json
from pathlib import Path, PurePosixPath
import re

from . import core, initiative_authority as authority, initiative_controller as controller, initiative_forgejo as forgejo_fixture
from . import lifecycle as l


@dataclass(frozen=True, slots=True)
class SliceRecipe:
    slice_id: str
    branch: str
    cycle_id: str
    context: str
    risk: str
    plan_path: str
    plan_digest: str


@dataclass(frozen=True, slots=True)
class RuntimeRecipe:
    authority_checkout: Path
    manifest_path: str
    github_account: str | None
    writer_agent: str
    slices: tuple[SliceRecipe, ...]
    forgejo: forgejo_fixture.Fixture | None = None

    def slice(self, identifier: str) -> SliceRecipe:
        for item in self.slices:
            if item.slice_id == identifier:
                return item
        raise ValueError("initiative_recipe_slice_unavailable")

    @property
    def digest(self) -> str:
        provider = ({"schema_version": 1, "github_account": self.github_account} if self.forgejo is None
                    else {"schema_version": 2, "forgejo": self.forgejo.digest})
        return l.digest({**provider, "authority_checkout": str(self.authority_checkout),
                         "manifest_path": self.manifest_path, "writer_agent": self.writer_agent,
                         "slices": [asdict(item) for item in self.slices]})


def _portable_path(value: object) -> str:
    text = l.text(value, 1024)
    path = PurePosixPath(text)
    if (path.as_posix() != text or not path.parts or path.parts[0] != "docs" or path.suffix != ".json"
            or ".." in path.parts or "\\" in text):
        raise ValueError("initiative_recipe_document_invalid")
    return text


def _identifier(value: object) -> str:
    text = l.text(value, 128)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", text) is None:
        raise ValueError("initiative_recipe_identifier_invalid")
    return text


def read_recipe(custody: l.Custody) -> RuntimeRecipe:
    """Read only the repository's fixed owner-only runtime recipe."""
    raw = custody._read(custody.directory / "initiative-runtime.json")
    value = l.object_value(json.loads(raw, object_pairs_hook=l.no_duplicates))
    version = value.get("schema_version")
    common = {"schema_version", "authority_checkout", "manifest_path", "writer_agent", "slices"}
    if type(version) is not int or version not in {1, 2} or set(value) != common | {
            "github_account" if version == 1 else "forgejo"}:
        raise ValueError("initiative_recipe_invalid")
    checkout = Path(l.text(value["authority_checkout"], 4096))
    if (not checkout.is_absolute() or checkout != checkout.resolve() or checkout.as_posix() != value["authority_checkout"]):
        raise ValueError("initiative_recipe_checkout_invalid")
    manifest = _portable_path(value["manifest_path"])
    if re.fullmatch(r"docs/initiatives/[a-z0-9][a-z0-9-]{0,127}/MANIFEST\.json", manifest) is None:
        raise ValueError("initiative_recipe_manifest_invalid")
    account = None
    fixture = None
    if version == 1:
        account = l.text(value["github_account"], 39)
        if re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", account) is None:
            raise ValueError("initiative_recipe_account_invalid")
    else:
        try:
            fixture = forgejo_fixture.parse_fixture(value["forgejo"])
        except (TypeError, ValueError, core.Invalid, core.Conflict):
            raise ValueError("initiative_recipe_forgejo_invalid") from None
    agent = l.text(value["writer_agent"], 64)
    if agent not in {"build", "build-gpt", "build-claude"}:
        raise ValueError("initiative_recipe_writer_invalid")
    raw_slices = l.object_value(value["slices"])
    if not 1 <= len(raw_slices) <= 256:
        raise ValueError("initiative_recipe_population_invalid")
    slices: list[SliceRecipe] = []
    for key, raw_slice in sorted(raw_slices.items()):
        item = l.object_value(raw_slice)
        if set(item) != {"branch", "cycle_id", "context", "risk", "plan_path", "plan_digest"}:
            raise ValueError("initiative_recipe_slice_invalid")
        branch = l.text(item["branch"])
        core._branch(branch)
        context = _identifier(item["context"])
        risk = l.text(item["risk"])
        if "." in context or branch in {"main", "master"} or risk not in {"routine", "elevated", "critical"}:
            raise ValueError("initiative_recipe_slice_invalid")
        slices.append(SliceRecipe(l.initiative_slice_id(key), branch, _identifier(item["cycle_id"]), context, risk,
                                  _portable_path(item["plan_path"]), l.hex_value(item["plan_digest"])))
    if len({item.branch for item in slices}) != len(slices) or len({item.cycle_id for item in slices}) != len(slices):
        raise ValueError("initiative_recipe_slice_duplicate")
    return RuntimeRecipe(checkout, manifest, account, agent, tuple(slices), fixture)


def bind_recipe(recipe: RuntimeRecipe, native_binding: dict) -> dict:
    """Bind the approved launch recipe without copying private paths into the grant."""
    binding = l.initiative_binding(native_binding)
    original = binding["qualification_digest"]
    binding["qualification_digest"] = l.digest({"schema_version": 1, "qualification_digest": original,
                                                "recipe_digest": recipe.digest})
    return binding


@dataclass(frozen=True, slots=True)
class StartPreview:
    recipe: RuntimeRecipe
    snapshot: dict
    proposal: dict
    approval_digest: str
    grant_digest: str

    @property
    def confirmation(self) -> str:
        return f"START {self.snapshot['initiative_id']} {self.approval_digest}"

    @property
    def review(self) -> dict:
        return {"schema_version": 1, "approval_digest": self.approval_digest, "grant_digest": self.grant_digest,
                "confirmation": self.confirmation, "scope": self.snapshot, "proposal": self.proposal,
                "recipe_digest": self.recipe.digest, "authority_checkout": str(self.recipe.authority_checkout),
                **({"github_account": self.recipe.github_account} if self.recipe.forgejo is None else
                   {"forgejo_fixture_digest": self.recipe.forgejo.digest}),
                "writer_agent": self.recipe.writer_agent,
                "slice_plans": [asdict(self.recipe.slice(identifier)) for identifier in self.snapshot["selected"]]}


def open_execution(custody: l.Custody, *, create: bool = False) -> controller.ExecutionStore:
    path = custody.directory / "initiative-execution.sqlite"
    anchor = custody.directory / "initiative-execution.json"
    try:
        recorded = custody._read(anchor)
    except FileNotFoundError:
        if not create:
            raise
        database = controller.ExecutionStore(path)
        info = path.lstat()
        custody._write(anchor, l.canonical({"schema_version": 1, "device": info.st_dev, "inode": info.st_ino}))
        return database
    database = controller.ExecutionStore(path, initialize=False)
    info = path.lstat()
    if recorded != l.canonical({"schema_version": 1, "device": info.st_dev, "inode": info.st_ino}):
        raise core.Unavailable("initiative_execution_journal_changed")
    return database


class InitiativeService:
    """One Start owner and one bounded Resume tick over the existing controller."""

    def __init__(self, custody: l.Custody, *, committed_scope: Callable[[RuntimeRecipe, tuple[str, ...]], dict],
                 live_binding: Callable[[RuntimeRecipe], dict], preflight: Callable[[RuntimeRecipe, str, str], controller.Launch],
                 prior_delivery: Callable[[RuntimeRecipe, controller.Approval, str, dict], bool],
                 writer: Callable[[controller.ExecutionStore], controller.Writer], provider: controller.Provider,
                 registration: controller.Registration | None, clock: Callable[[], str],
                 protected_tick: Callable[[RuntimeRecipe, controller.Activation], None] | None = None) -> None:
        if protected_tick is not None and registration is None:
            raise core.Invalid("initiative_protected_registration_required")
        self.custody = custody
        self.committed_scope, self.live_binding, self.preflight, self.prior_delivery = (
            committed_scope, live_binding, preflight, prior_delivery
        )
        self.writer, self.provider, self.registration, self.clock = writer, provider, registration, clock
        self.protected_tick = protected_tick

    def _prepare(self, selected: tuple[str, ...], operator_id: str, approved_at: str, expires_at: str) -> StartPreview:
        recipe = read_recipe(self.custody)
        chosen = [recipe.slice(identifier) for identifier in selected]
        snapshot = self.committed_scope(recipe, selected)
        if snapshot["manifest_path"] != recipe.manifest_path or snapshot["selected"] != list(selected):
            raise ValueError("initiative_recipe_scope_changed")
        binding = bind_recipe(recipe, self.live_binding(recipe))
        fixture = recipe.forgejo
        repository = binding["repository"]
        target_matches = (repository["provider"] == "github" if fixture is None else
                          (repository, binding["target_ref"], binding["root_oid"], binding["policy_digest"],
                           binding["enrollment_digest"]) ==
                          (fixture.repository, fixture.target_ref, fixture.root_oid, fixture.plan.policy_digest,
                           fixture.digest))
        if not target_matches or any("refs/heads/" + item.branch == binding["target_ref"] for item in chosen):
            raise ValueError("initiative_recipe_target_invalid")
        proposal = authority.grant_proposal(snapshot, binding=binding, operator_id=operator_id,
                                            approved_at=approved_at, expires_at=expires_at,
                                            allowed_operations=("launch", "admit", "merge"), repair_limit=0)
        grant_digest = l.digest({"schema_version": 1, "kind": "initiative_grant", "value": proposal})
        return StartPreview(recipe, snapshot, proposal, l.digest(proposal), grant_digest)

    def preview(self, selected: tuple[str, ...], *, operator_id: str, expires_at: str) -> StartPreview:
        return self._prepare(selected, operator_id, self.clock(), expires_at)

    def confirm(self, preview: StartPreview, input_line: str) -> str:
        """Accept the exact operator line, then revalidate before recording the grant."""
        if input_line != preview.confirmation:
            raise ValueError("initiative_confirmation_refused")
        proposal = preview.proposal
        lock = l.digest({"kind": "initiative-journal-initialization"})
        with authority.initiative_effect_lock(self.custody, lock):
            now = l.initiative_time(self.clock())
            if not l.initiative_time(proposal["approved_at"]) <= now < l.initiative_time(proposal["expires_at"]):
                raise ValueError("initiative_confirmation_inactive")
            fresh = self._prepare(tuple(preview.snapshot["selected"]), proposal["operator_id"],
                                  proposal["approved_at"], proposal["expires_at"])
            if fresh != preview:
                raise ValueError("initiative_confirmation_changed")
            if l.initiative_time(self.clock()) >= l.initiative_time(proposal["expires_at"]):
                raise ValueError("initiative_confirmation_inactive")
            open_execution(self.custody, create=True)
            identity = authority.store_grant(self.custody, fresh.snapshot, fresh.proposal,
                                             expected_approval_digest=fresh.approval_digest)
            if identity != fresh.grant_digest:
                raise core.Conflict("initiative_grant_identity_changed")
            return identity

    def resume(self, grant_digest: str) -> controller.Report:
        authority.read_grant(self.custody, grant_digest)
        store = open_execution(self.custody)
        recipe = read_recipe(self.custody)
        port = authority.CustodyAuthority(
            self.custody, current_binding=lambda: bind_recipe(read_recipe(self.custody), self.live_binding(recipe)),
            current_scope=lambda slice_id: self.committed_scope(recipe, (slice_id,)),
            plan=lambda slice_id: self.preflight(recipe, grant_digest, slice_id),
            prior_delivery=lambda approval, slice_id, scope: self.prior_delivery(recipe, approval, slice_id, scope),
            clock=self.clock,
        )
        runtime = controller.InitiativeController(store, port, self.writer(store), self.provider,
                                                  registration=self.registration)
        report = runtime.advance(grant_digest)
        if self.protected_tick is not None and report.state in {"dispatched", "admitted"}:
            active = store.active(grant_digest)
            if active is not None and (active.state, active.activation.activation_id) == (report.state, report.activation_id):
                try:
                    self.protected_tick(recipe, active.activation)
                except (core.Unavailable, core.Conflict, core.Ambiguous, core.Invalid, OSError):
                    return controller.Report("uncertain", report.slice_id, report.activation_id,
                                             "initiative_protected_step_unverified")
        return report
