"""Compose managed Initiative Start and Resume inside the private lifecycle owner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path, PurePosixPath
import re
from typing import Literal

from . import core, initiative_authority as authority, initiative_controller as controller, initiative_forgejo as forgejo_fixture
from . import initiative_ci as ci, initiative_repair as repair, initiative_status as status
from . import lifecycle as l
from .initiative_evidence import Evidence


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
    credential_source: Literal["osxkeychain", "systemd"] = "osxkeychain"
    ci_policy: ci.Policy | None = None
    repair_policy: l.InitiativeRepairPolicy | None = None

    def slice(self, identifier: str) -> SliceRecipe:
        for item in self.slices:
            if item.slice_id == identifier:
                return item
        raise ValueError("initiative_recipe_slice_unavailable")

    @property
    def digest(self) -> str:
        if self.forgejo is None:
            provider = {"schema_version": 1, "github_account": self.github_account}
        elif self.credential_source == "systemd":
            provider = {"schema_version": 3, "forgejo": self.forgejo.digest, "credential_source": self.credential_source}
        else:
            provider = {"schema_version": 2, "forgejo": self.forgejo.digest}
        if self.ci_policy is not None:
            provider = {**provider, "schema_version": 4, "ci_policy": asdict(self.ci_policy),
                        "repair_policy": self.repair_policy}
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
    provider_fields = {1: {"github_account"}, 2: {"forgejo"}, 3: {"forgejo", "credential_source"}}
    telemetry = None
    repair_policy = None
    if type(version) is int and version == 4:
        recovery_fields = {"ci_policy", "repair_policy"}
        legacy_version = 1 if "github_account" in value else (3 if "credential_source" in value else 2)
        if set(value) != common | provider_fields[legacy_version] | recovery_fields:
            raise ValueError("initiative_recipe_invalid")
        telemetry = l.initiative_ci_policy(value["ci_policy"])
        if value["repair_policy"] is not None:
            repair_policy = l.initiative_repair_policy(value["repair_policy"])
        version = legacy_version
    elif type(version) is not int or version not in provider_fields or set(value) != common | provider_fields[version]:
        raise ValueError("initiative_recipe_invalid")
    credential_source: Literal["osxkeychain", "systemd"] = "osxkeychain"
    if version == 3:
        if value["credential_source"] != "systemd":
            raise ValueError("initiative_recipe_credential_source_invalid")
        credential_source = "systemd"
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
    return RuntimeRecipe(checkout, manifest, account, agent, tuple(slices), fixture, credential_source,
                         telemetry, repair_policy)


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
                **({"credential_source": self.recipe.credential_source} if self.recipe.credential_source == "systemd" else {}),
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


CIReader = Callable[[controller.Activation, controller.Admission, int], ci.Observation | None]


def read_status(custody: l.Custody, grant_digest: str, *, clock: Callable[[], str]) -> dict:
    proposal, snapshot = authority.read_grant(custody, grant_digest)
    view = Evidence(open_execution(custody)).snapshot(grant_digest)
    policy = ci.Policy(**proposal["ci_policy"]) if "ci_policy" in proposal else None
    return status.project(proposal, snapshot, view.executions, now=l.initiative_time(clock()),
                          repair_used=view.repair_used, verified_dependencies=view.verified_dependencies,
                          revoked=custody.optional_link("initiative_revocation", grant_digest) is not None,
                          ci=view.telemetry, policy=policy, reports=view.reports)


class InitiativeService:
    """One Start owner and one bounded Resume tick over the existing controller."""

    def __init__(self, custody: l.Custody, *, committed_scope: Callable[[RuntimeRecipe, tuple[str, ...]], dict],
                 live_binding: Callable[[RuntimeRecipe], dict], preflight: Callable[[RuntimeRecipe, str, str], controller.Launch],
                 prior_delivery: Callable[[RuntimeRecipe, controller.Approval, str, dict], bool],
                 writer: Callable[[controller.ExecutionStore], controller.Writer], provider: controller.Provider,
                 registration: controller.Registration | None, clock: Callable[[], str],
                 protected_tick: Callable[[RuntimeRecipe, controller.Activation], None] | None = None,
                 ci_reader: CIReader | None = None, repair_route: repair.Route | None = None) -> None:
        if protected_tick is not None and registration is None:
            raise core.Invalid("initiative_protected_registration_required")
        self.custody = custody
        self.committed_scope, self.live_binding, self.preflight, self.prior_delivery = (
            committed_scope, live_binding, preflight, prior_delivery
        )
        self.writer, self.provider, self.registration, self.clock = writer, provider, registration, clock
        self.protected_tick, self.ci_reader, self.repair_route = protected_tick, ci_reader, repair_route

    def _reviewed_repair(self, recipe: RuntimeRecipe, snapshot: dict, requested: tuple[str, ...]) -> l.InitiativeRepairPolicy | None:
        if requested == ("none",) or not requested and recipe.ci_policy is None:
            return None
        selected = requested or repair.CLASSES
        if len(selected) != len(set(selected)) or any(kind not in repair.CLASSES for kind in selected):
            raise ValueError("initiative_repair_selection_invalid")
        enrolled = recipe.repair_policy
        qualified = {} if self.repair_route is None else self.repair_route.qualifications(recipe, snapshot)
        enrolled_classes = {} if enrolled is None else enrolled["class_qualifications"]
        for kind in selected:
            if kind not in enrolled_classes or enrolled_classes[kind] != qualified.get(kind):
                raise ValueError(f"initiative_repair_capability_unavailable:{kind}")
        assert enrolled is not None
        return {"class_qualifications": {kind: enrolled_classes[kind] for kind in sorted(selected)},
                "writable_paths": {key: paths for key, paths in enrolled["writable_paths"].items()
                                   if repair.SOURCE in selected and key in snapshot["selected"]}}

    def _prepare(self, selected: tuple[str, ...], operator_id: str, approved_at: str, expires_at: str,
                 requested: tuple[str, ...] = ()) -> StartPreview:
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
        if recipe.ci_policy is not None and self.ci_reader is None:
            raise ValueError("initiative_ci_capability_unavailable")
        repair_policy = self._reviewed_repair(recipe, snapshot, requested)
        operations = ("launch", "admit", "merge") + (("repair",) if repair_policy is not None else ())
        proposal = authority.grant_proposal(snapshot, binding=binding, operator_id=operator_id,
                                            approved_at=approved_at, expires_at=expires_at,
                                            allowed_operations=operations, repair_limit=int(repair_policy is not None),
                                            ci_policy=recipe.ci_policy, repair_policy=repair_policy)
        grant_digest = l.digest({"schema_version": 1, "kind": "initiative_grant", "value": proposal})
        return StartPreview(recipe, snapshot, proposal, l.digest(proposal), grant_digest)

    def preview(self, selected: tuple[str, ...], *, operator_id: str, expires_at: str,
                repair_classes: tuple[str, ...] = ()) -> StartPreview:
        return self._prepare(selected, operator_id, self.clock(), expires_at, repair_classes)

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
            repair_policy = proposal.get("repair_policy")
            requested = ("none",) if repair_policy is None else tuple(repair_policy["class_qualifications"])
            fresh = self._prepare(tuple(preview.snapshot["selected"]), proposal["operator_id"],
                                  proposal["approved_at"], proposal["expires_at"], requested)
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

    def resume(self, grant_digest: str, *, wakeup: bool = False) -> controller.Report:
        proposal, _ = authority.read_grant(self.custody, grant_digest)
        store = open_execution(self.custody)
        evidence = Evidence(store)
        evidence.initialize()
        recipe = read_recipe(self.custody)

        def dependency(approval: controller.Approval, slice_id: str, scope: dict) -> bool:
            checked = self.prior_delivery(recipe, approval, slice_id, scope) is True
            return evidence.dependency(grant_digest, slice_id, checked)

        port = authority.CustodyAuthority(
            self.custody, current_binding=lambda: bind_recipe(read_recipe(self.custody), self.live_binding(recipe)),
            current_scope=lambda slice_id: self.committed_scope(recipe, (slice_id,)),
            plan=lambda slice_id: self.preflight(recipe, grant_digest, slice_id),
            prior_delivery=dependency, clock=self.clock,
        )
        runtime = controller.InitiativeController(store, port, self.writer(store), self.provider,
                                                  registration=self.registration)
        report = runtime.advance(grant_digest)
        if report.state in {"dispatched", "admitted", "uncertain"}:
            active = store.active(grant_digest)
            if (active is not None and active.activation.activation_id == report.activation_id
                    and (active.state == report.state or active.state == "admitted" and "ci_policy" in proposal)):
                report = self._advance_protected(recipe, proposal, evidence, active, report, wakeup)
        evidence.report(grant_digest, report)
        return report

    def _authorize_repair(self, activation: controller.Activation, request: repair.Request) -> None:
        recipe = read_recipe(self.custody)
        current = self.committed_scope(recipe, (activation.slice_id,))
        if self.repair_route is None or self.repair_route.qualifications(recipe, current).get(
                request.correction.kind) != request.qualification_digest:
            raise core.Unavailable("initiative_repair_capability_unavailable")
        if self.registration is None or self.registration.observed(activation) is None:
            raise core.Unavailable("initiative_repair_registration_unproved")
        authority.require_grant(
            self.custody, activation.grant_id, binding=bind_recipe(recipe, self.live_binding(recipe)),
            current=current, slice_id=activation.slice_id, operation="repair", now=self.clock(), repair_attempt=1,
            repair_class=request.correction.kind, repair_qualification_digest=request.qualification_digest,
            repair_paths=request.correction.writable_paths,
        )

    def _advance_protected(self, recipe: RuntimeRecipe, proposal: dict, evidence: Evidence,
                           active: controller.Execution, report: controller.Report, wakeup: bool) -> controller.Report:
        activation = active.activation
        telemetry = None
        try:
            if active.admission is not None and "ci_policy" in proposal:
                policy = ci.Policy(**proposal["ci_policy"])
                now = int(l.initiative_time(self.clock()).timestamp())
                previous = evidence.telemetry(activation.activation_id)
                recovery = repair.Recovery(self.custody, evidence, self.repair_route, self._authorize_repair)
                if previous is not None and not ci.due(previous, now, wakeup=wakeup):
                    previous_report = evidence.snapshot(activation.grant_id).reports.get(activation.slice_id)
                    return replace(previous_report or report, next_recheck_at=previous.next_recheck_at)
                observation = self._observe_ci(active, previous, now)
                if observation is not None:
                    telemetry = evidence.observe(activation, previous, ci.advance(previous, observation, policy))
                    observation = telemetry.observation
                repaired = recovery.advance(active, observation, proposal)
                if repaired is not None:
                    return replace(repaired, next_recheck_at=telemetry.next_recheck_at if telemetry else None)
                if telemetry is not None and telemetry.observation.state not in {"passed", "stale"}:
                    return replace(report, next_recheck_at=telemetry.next_recheck_at)
            if self.protected_tick is not None and report.state != "uncertain":
                self.protected_tick(recipe, activation)
        except (core.Unavailable, core.Conflict, core.Ambiguous, core.Invalid, OSError, ValueError) as error:
            reason = "initiative_protected_step_unverified"
            reason_code = str(error)
            if reason_code in {"initiative_material_changed", "initiative_repair_paths_unapproved",
                               "initiative_repair_correction_ambiguous"}:
                return replace(report, state="discovery_reopened", reason="initiative_execution_material_drift")
            if reason_code in {"initiative_grant_inactive", "initiative_grant_revoked", "initiative_qualification_changed",
                              "initiative_repair_capability_unavailable", "initiative_repair_qualification_changed"}:
                return replace(report, state="blocked", reason=reason_code)
            return replace(report, state="uncertain", reason=reason,
                           next_recheck_at=telemetry.next_recheck_at if telemetry else None)
        return replace(report, next_recheck_at=telemetry.next_recheck_at if telemetry else None)

    def _observe_ci(self, active: controller.Execution, previous: ci.Telemetry | None,
                    now: int) -> ci.Observation | None:
        assert active.admission is not None
        try:
            if self.ci_reader is not None:
                observation = self.ci_reader(active.activation, active.admission, now)
                if observation is not None:
                    return observation
        except (core.Unavailable, core.Conflict, core.Ambiguous, core.Invalid, OSError):
            return ci.unavailable(previous, now, "provider_read_unavailable")
        return None
