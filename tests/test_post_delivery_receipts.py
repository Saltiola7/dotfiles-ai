"""Post-delivery receipts for cycles completed at Final Push.

Real Git and the real helper; only the GitHub transport is synthetic, as in the
external completion tests. Identities are public examples. Nothing here
establishes production authentication, consent, CI or deployment acceptance.
"""

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import test_dbsctr_external_completion as external
from test_dbsctr_external_completion import NUMBER, cycle, snapshot


OWNER = "example-owner"
DEFERRED = ("deploy", "operate", "maintain_retire")
URL = f"https://github.com/{external.REPOSITORY}/pull/{NUMBER}"
PREDICATE = {"schema_version": 1, "id": "operate-green",
             "predicate": {"gate": "operate", "authority": "hosted-check", "result": "passed"}}


def real(*arguments, cwd):
    return subprocess.run(["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def git_input(*arguments, cwd, text):
    return subprocess.run(["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True,
                          input=text).stdout.strip()


@pytest.fixture
def delivered(cycle, monkeypatch, capsys):
    """A draft delivery that Final Push can complete with stubbed publication."""
    core = cycle.core
    cycle.primary = Path(cycle.fixture.temp.name) / "repo"
    cycle.capsys = capsys
    monkeypatch.setattr(core, "push_github_branch", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core, "link_improvement_pull_request", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core, "deliver_draft_pr", lambda *_args, **_kwargs: {
        "number": NUMBER, "url": URL, "draft": True, "state": "OPEN", "verified_at": core.now()})
    previous = core.git

    def git_at_transport(target, *arguments, **kwargs):
        if "--no-write-fetch-head" in arguments and "fetch" in arguments[:5]:
            # The fetch must run under the authenticated context; the offline one forbids transport.
            active = core.LOCAL_COMPLETION_GIT.get()
            assert active is not None and active.get("GIT_ALLOW_PROTOCOL") != ""
            assert active.get("GH_TOKEN") == "synthetic-token-never-print"
            # Only the GitHub URL differs: the simulated remote is this repository.
            assert external.ORIGIN in arguments and arguments[-1] == "+refs/heads/main:refs/heads/main", arguments
            served = [str(cycle.root) if value == external.ORIGIN else value for value in arguments]
            served[-1] = "+refs/remotes/origin/main:refs/heads/main"
            result = subprocess.run(["git", *served], cwd=target, env=active, capture_output=True, text=True)
            return subprocess.CompletedProcess(arguments, result.returncode, result.stdout, result.stderr)
        if arguments[0] == "ls-remote" and "--get-url" not in arguments:
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target, check=True,
                                  capture_output=True, text=True).stdout.strip()
            return subprocess.CompletedProcess(arguments, 0, stdout=f"{head}\t{arguments[-1]}\n", stderr="")
        return previous(target, *arguments, **kwargs)

    monkeypatch.setattr(core, "git", git_at_transport)
    native = external.NativeGitHub(core, cycle.root, cycle.base, "0" * 40, "0" * 40)
    monkeypatch.setattr(core, "github_environment", native.environment)
    monkeypatch.setattr(core, "github_json", native.json)
    cycle.native = native
    capsys.readouterr()
    return cycle


def evidence(ws, gate, *, paths=(), code=0, authority="fixture"):
    arguments = ["record-evidence", gate, "--authority", authority]
    for path in paths:
        arguments.extend(["--path", path])
    ws.core.command_record_evidence(ws.core.parser().parse_args([
        *arguments, "--", sys.executable, "-c", f"raise SystemExit({code})"]))


def approve(ws, gate, *, cycle_id="cycle-1", review=None):
    core = ws.core
    core.command_approve_exception(core.parser().parse_args([
        "approve-exception", "--kind", "deferred", "--owner", OWNER, "--rationale", "Needs the published result",
        "--review-condition", f"Check {gate} after publication", gate]))
    if review is not None:
        path = core.cycle_dir(ws.root) / "cycles" / f"{cycle_id}.json"
        record = json.loads(path.read_text())
        record["gates"][gate]["exception"]["review"] = review
        path.write_text(json.dumps(record))


def reviews(ws):
    for artifact, result in (("README", "unchanged"), ("BACKLOG", "unchanged"), ("CHANGELOG", "changed")):
        arguments = ["review-artifact", artifact, "--result", result, "--reason", "fixture review"]
        if result == "changed":
            arguments.extend(["--path", "docs/specs/test/CHANGELOG.md"])
        ws.core.command_review(ws.core.parser().parse_args(arguments))


def required_gates(ws, root=None):
    return [gate for gate in ws.core.GATES
            if ws.core.load(root or ws.root)[1]["gates"][gate]["applicability"] == "required"]


def prepare(ws, *, deferred=DEFERRED, review=None):
    """Gate evidence, one Gate Commit and artifact reviews; the cycle stays active."""
    core, root = ws.core, ws.root
    (root / "tracked.txt").write_text("Delivered fixture change\n")
    (root / "docs/specs/test/CHANGELOG.md").write_text("Delivered fixture change.\n")
    paths = ["tracked.txt", "docs/specs/test/CHANGELOG.md"]
    for gate in required_gates(ws):
        # A Gate Commit lists a gate only when its evidence carries the commit's paths.
        evidence(ws, gate, paths=() if gate in deferred else paths, code=1 if gate in deferred else 0)
        if gate in deferred:
            approve(ws, gate, review=(review or {}).get(gate))
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "fixture delivery", "--gates", *[gate for gate in required_gates(ws) if gate not in deferred],
        "--paths", *paths]))
    for gate in deferred:
        # Uncommitted failing evidence must sit at the head that Final Push pushes.
        evidence(ws, gate, code=1)
        approve(ws, gate, review=(review or {}).get(gate))
    reviews(ws)
    ws.head = real("rev-parse", "HEAD", cwd=ws.root)
    ws.tree = real("rev-parse", "HEAD^{tree}", cwd=ws.root)


def deliver(ws, **options):
    prepare(ws, **options)
    assert ws.invoke("final-push") == 0
    ws.capsys.readouterr()
    record = json.loads(ws.path.read_text())
    assert record["state"] == "completed" and "external_completion" not in record
    return record


def blob(ws, text):
    return git_input("hash-object", "-w", "--stdin", cwd=ws.root, text=text)


def tree_with(ws, tree, replacements=(), additions=()):
    entries = real("ls-tree", tree, cwd=ws.root).splitlines()
    for name, text in replacements:
        entries = [f"100644 blob {blob(ws, text)}\t{name}" if entry.endswith("\t" + name) else entry
                   for entry in entries]
    return git_input("mktree", cwd=ws.root, text="\n".join(
        [*entries, *(f"100644 blob {blob(ws, text)}\t{name}" for name, text in additions)]) + "\n")


def edit(ws, text):
    """A substantive single-parent commit on the pull request branch after the delivered tip."""
    return real("commit-tree", tree_with(ws, ws.tree, replacements=[("tracked.txt", text)]), "-p", ws.head,
                "-m", "Later edit", cwd=ws.root)


def land(ws, *, pr_head=None, tree=None, parents=(None,)):
    """Place the simulated landing on the protected base and describe it natively."""
    ws.pr_head = ws.head if pr_head is None else pr_head
    tree = ws.tree if tree is None else tree
    ws.merge = real("commit-tree", tree, *[flag for parent in parents for flag in ("-p", ws.base if parent is None else parent)],
                    "-m", "External landing", cwd=ws.root)
    real("update-ref", "refs/remotes/origin/main", ws.merge, cwd=ws.root)
    ws.native.pull["head"]["sha"] = ws.pr_head
    ws.native.pull["merge_commit_sha"] = ws.merge
    return ws.merge


def advance_base(ws, *, conflict=False):
    """One later commit on the protected base, before the pull request lands."""
    tree = (tree_with(ws, f"{ws.base}^{{tree}}", replacements=[("tracked.txt", "Base change\n")]) if conflict
            else tree_with(ws, f"{ws.base}^{{tree}}", additions=[("later.txt", "Later base change\n")]))
    ws.new_base = real("commit-tree", tree, "-p", ws.base, "-m", "Later base commit", cwd=ws.root)
    return ws.new_base


def clean_merge_tree(ws, parent):
    merge_base = real("merge-base", ws.head, parent, cwd=ws.root)
    return real("merge-tree", "--write-tree", f"--merge-base={merge_base}", ws.head, parent, cwd=ws.root).splitlines()[0]


def take_in(ws, parent, *, tree=None):
    """One merge commit on the pull request branch that takes in `parent`."""
    ws.refresh_tree = clean_merge_tree(ws, parent) if tree is None else tree
    ws.pr_head = real("commit-tree", ws.refresh_tree, "-p", ws.head, "-p", parent, "-m", "Merge main into feature",
                      cwd=ws.root)
    return ws.pr_head


def refresh(ws, *, tree=None):
    """A base-only refresh that lands as an ordinary two-parent merge."""
    pr_head = take_in(ws, ws.new_base, tree=tree)
    return land(ws, pr_head=pr_head, tree=ws.refresh_tree, parents=(ws.new_base, pr_head))


def later_cycle(ws, monkeypatch, *, authority="hosted-check", code=0, finish=True, cycle_id="cycle-2"):
    """A second real cycle in its own checkout; its evidence is a later observation."""
    core, root = ws.core, ws.root
    worktree = Path(ws.fixture.temp.name) / f"{cycle_id}-worktree"
    real("worktree", "add", "-b", f"{cycle_id}-branch", str(worktree), "refs/remotes/origin/main", cwd=root)
    real("branch", "--set-upstream-to=origin/main", cwd=worktree)
    plan = ws.fixture.plan_path("draft_pr")
    with monkeypatch.context() as patch:
        patch.chdir(worktree)
        patch.setattr(core, "root_dir", lambda: worktree)
        core.command_start(core.parser().parse_args([
            "start", "--cycle-id", cycle_id, "--context", "test", "--risk", "routine", "--delivery-intent", "draft_pr",
            "--plan", str(plan), "--base-branch", "main", "--github-account", external.ACCOUNT,
            "--github-repository", external.REPOSITORY]))
        if not finish:
            ws.capsys.readouterr()
            return None
        (worktree / "tracked.txt").write_text("Later observation\n")
        (worktree / "docs/specs/test/CHANGELOG.md").write_text("Later observation.\n")
        paths = ["tracked.txt", "docs/specs/test/CHANGELOG.md"]

        def observe():
            # A Gate Commit lists a gate only when its evidence carries the commit's paths.
            evidence(ws, "operate", paths=() if code else paths, code=code, authority=authority)
            if code:
                approve(ws, "operate", cycle_id=cycle_id)

        for gate in required_gates(ws, worktree):
            if gate == "operate":
                observe()
            else:
                evidence(ws, gate, paths=paths)
        core.command_gate_commit(core.parser().parse_args([
            "gate-commit", "--message", "later observation",
            "--gates", *[gate for gate in required_gates(ws, worktree) if not (gate == "operate" and code)],
            "--paths", *paths]))
        if code:
            observe()
            # New evidence for operate invalidates the later gate; record it again at the final head.
            evidence(ws, "maintain_retire", paths=paths)
        reviews(ws)
        assert ws.invoke("final-push") == 0
        ws.capsys.readouterr()
    return json.loads((core.cycle_dir(worktree) / "cycles" / f"{cycle_id}.json").read_text())


def post(ws, *extra):
    return ["complete-external", "--post-delivery", "--cycle-id", "cycle-1", "--pr-number", str(NUMBER),
            "--expected-head", ws.pr_head, "--expected-merge", ws.merge, *extra]


def preview_argv(ws, argv):
    """A read-only preview: record, refs, index and pointer are byte-identical afterwards."""
    before = snapshot(ws)
    assert ws.invoke(*argv, "--preview") == 0, ws.capsys.readouterr().err
    report = json.loads(ws.capsys.readouterr().out)
    assert snapshot(ws) == before
    return report


def preview(ws, *extra):
    return preview_argv(ws, post(ws, *extra))


def append(ws, digest, *extra):
    """An approved append changes receipt custody only: record, refs, index and pointer stay as they were."""
    argv = post(ws, "--expected-receipt-digest", digest, "--approval", "agent-confirmed", *extra)
    before = snapshot(ws)
    assert ws.invoke(*argv) == 0, ws.capsys.readouterr().err
    assert snapshot(ws) == before
    return json.loads(ws.capsys.readouterr().out)


def rejected_argv(ws, argv):
    before = snapshot(ws)
    assert ws.invoke(*argv) == 1
    output = ws.capsys.readouterr()
    assert "dbsctrctl:" in output.err and "Traceback" not in output.err
    assert "synthetic-token-never-print" not in output.out + output.err
    assert snapshot(ws) == before
    return output.err


def rejected(ws, *extra):
    return rejected_argv(ws, post(ws, *extra))


def receipt_names(ws):
    """Committed receipt files; an inert temporary file left by an interrupted writer is not one."""
    directory = ws.core.cycle_dir(ws.root) / "evidence" / "cycle-1" / "post-delivery"
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.iterdir() if not path.name.startswith("tmp"))


def stored(ws):
    argv = ["status", "--post-delivery", "--cycle-id", "cycle-1", "--json"]
    before = snapshot(ws)
    assert ws.invoke(*argv) == 0, ws.capsys.readouterr().err
    report = json.loads(ws.capsys.readouterr().out)
    assert snapshot(ws) == before
    assert receipt_names(ws) == [f"{item['sequence']:04d}-{item['digest']}.json" for item in report["receipts"]]
    return report


def condition(report, gate):
    return next(item for item in report["conditions"] if item["gate"] == gate)


def write_record(ws, change):
    record = json.loads(ws.path.read_text())
    change(record)
    ws.path.write_text(json.dumps(record))


@pytest.mark.parametrize("cycle", [None, "initiative"], indirect=True)
def test_preview_reports_the_recorded_delivery_and_an_unchanged_landing(delivered):
    record = deliver(delivered)
    land(delivered)
    report = preview(delivered)
    assert report["schema_version"] == 1 and report["mode"] == "preview" and report["recordable"] is True
    assert report["cycle_id"] == "cycle-1" and report["previous"] is None
    assert len(report["receipt_digest"]) == 64 and report["observed_at"]
    original = report["original"]
    assert original["record_sha256"] == hashlib.sha256(delivered.path.read_bytes()).hexdigest()
    assert original["completed_at"] == record["completed_at"]
    assert original["cycle_base"] == delivered.base
    assert original["recorded_commits"] == [entry["id"] for entry in record["commits"]]
    assert original["pull_request"] == {"number": NUMBER, "url": URL}
    assert original["base_branch"] == "main" and original["feature_branch"] == record["delivery"]["branch"]
    for gate in DEFERRED:
        assert original["gates"][gate] == {"result": "failed", "exception": {
            "kind": "deferred", "owner": OWNER, "approved_at": record["gates"][gate]["exception"]["approved_at"]}}
    assert original["gates"]["domain"] == {"result": "passed"} and "release" not in original["gates"]
    landing = report["landing"]
    assert landing["status"] == "verified" and landing["proof"] == "unchanged_head"
    assert landing["head"] == delivered.head and landing["merge"] == delivered.merge
    assert landing["merge_parent"] == delivered.base and "refresh" not in landing
    assert landing["target_branch"] == "main" and landing["target_head"] == delivered.merge
    assert landing["merged_at"] == external.MERGED_AT
    assert [item["gate"] for item in report["conditions"]] == list(DEFERRED)
    for item in report["conditions"]:
        assert item["kind"] == "judgment" and item["predicate"] is None and item["owner"] == OWNER
        assert item["condition"] == hashlib.sha256(item["review_condition"].encode()).hexdigest()
        assert item["disposition"] == "unverified" and item["reason"] == "evidence_required"
        assert item["evidence"] == [] and item["owner_decision"] is None
    assert receipt_names(delivered) == [] and stored(delivered)["receipts"] == []
    assert delivered.native.calls


@pytest.mark.parametrize("cycle", [None, "initiative"], indirect=True)
def test_append_records_one_private_receipt_and_an_identical_retry_returns_it(delivered):
    deliver(delivered)
    land(delivered)
    digest = preview(delivered)["receipt_digest"]
    original = delivered.path.read_bytes()
    assert "exact receipt digest" in rejected(delivered)
    assert "exact receipt digest" in rejected(delivered, "--approval", "agent-confirmed")
    assert "exact receipt digest" in rejected(delivered, "--expected-receipt-digest", digest)
    assert "plan changed" in rejected(
        delivered, "--expected-receipt-digest", "0" * 64, "--approval", "agent-confirmed")
    assert receipt_names(delivered) == []
    result = append(delivered, digest)
    assert result["mode"] == "recorded" and result["schema_version"] == 1
    assert result["kind"] == "post_delivery_receipt" and result["cycle_id"] == "cycle-1"
    assert result["sequence"] == 1 and result["previous"] is None and result["digest"] == digest
    assert result["approval"] == {"method": "agent_confirmed", "attribution": "caller_assertion"}
    assert result["landing"]["status"] == "verified" and result["recorded_at"] and result["observed_at"]
    assert result["original"]["record_sha256"] == hashlib.sha256(original).hexdigest()
    assert delivered.path.read_bytes() == original
    directory = delivered.core.cycle_dir(delivered.root) / "evidence" / "cycle-1" / "post-delivery"
    for path in (directory.parent, directory):
        assert stat.S_IMODE(path.stat().st_mode) == 0o700
    for path in directory.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600 and path.stat().st_nlink == 1
    again = append(delivered, digest)
    assert again.pop("mode") == "already_recorded"
    assert again == {key: value for key, value in result.items() if key != "mode"}
    assert len(receipt_names(delivered)) == 1
    report = stored(delivered)
    assert report["schema_version"] == 1 and report["cycle_id"] == "cycle-1" and report["mode"] == "stored_receipts"
    assert report["record_matches_latest"] is True and len(report["receipts"]) == 1
    assert report["latest"] == report["receipts"][0] and report["latest"]["record_matches"] is True
    assert report["latest"]["digest"] == digest and report["latest"]["sequence"] == 1
    assert report["latest"]["approval"] == result["approval"]
    assert report["latest"]["landing"]["status"] == "verified" and report["latest"]["landing"]["proof"] == "unchanged_head"
    assert report["latest"]["observed_at"] and report["latest"]["recorded_at"]
    assert [(item["gate"], item["disposition"]) for item in report["outstanding"]] == [
        (gate, "unverified") for gate in DEFERRED]
    # Stored receipts are read offline; status never repeats the native observation.
    delivered.native.calls.clear()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("stored status contacted GitHub")
    delivered.core.github_environment = forbidden
    assert stored(delivered)["latest"]["digest"] == digest and delivered.native.calls == []


def test_a_clean_base_refresh_is_verified(delivered):
    deliver(delivered)
    advance_base(delivered)
    refresh(delivered)
    report = preview(delivered)
    assert report["landing"]["status"] == "verified" and report["landing"]["proof"] == "base_refresh"
    assert report["landing"]["head"] == delivered.pr_head and report["landing"]["merge"] == delivered.merge
    assert report["landing"]["refresh"] == {"base_parent": delivered.new_base}
    assert report["landing"]["target_head"] == delivered.merge and report["recordable"] is True


@pytest.mark.parametrize("change, reason", [
    ("extra-edit", "head_changed_beyond_base_refresh"),
    ("edited-tree", "refresh_changed_content"),
    ("not-pre-landing-base", "refresh_base_is_not_pre_landing_target"),
])
def test_changed_heads_without_a_clean_base_only_refresh_are_unverified(delivered, change, reason):
    deliver(delivered)
    advance_base(delivered)
    if change == "extra-edit":
        # This is also what an earlier cycle sees when a later cycle shares its pull request.
        land(delivered, pr_head=edit(delivered, "Later substantive edit\n"),
             tree=tree_with(delivered, delivered.tree, replacements=[("tracked.txt", "Later substantive edit\n")]))
    elif change == "edited-tree":
        refresh(delivered, tree=tree_with(delivered, clean_merge_tree(delivered, delivered.new_base),
                                          replacements=[("tracked.txt", "Resolved by hand\n")]))
    else:
        # Its second parent is reachable from the landing only through the pull request.
        pr_head = take_in(delivered, edit(delivered, "Not on the protected base\n"))
        land(delivered, pr_head=pr_head, tree=delivered.refresh_tree, parents=(None, pr_head))
    report = preview(delivered)
    assert report["landing"]["status"] == "unverified" and report["landing"]["proof"] is None
    assert report["landing"]["reason"] == reason and report["recordable"] is False
    assert report["landing"]["pull_request"] == {
        "state": "closed", "merged": True, "merged_at": external.MERGED_AT, "head": delivered.pr_head}
    assert "nothing to record" in rejected(
        delivered, "--expected-receipt-digest", report["receipt_digest"], "--approval", "agent-confirmed")
    assert receipt_names(delivered) == []


def test_a_squashed_clean_refresh_is_verified(delivered):
    deliver(delivered)
    advance_base(delivered)
    pr_head = take_in(delivered, delivered.new_base)
    # The protected base had already advanced when the squash landed.
    land(delivered, pr_head=pr_head, tree=delivered.refresh_tree, parents=(delivered.new_base,))
    report = preview(delivered)
    assert report["landing"]["status"] == "verified" and report["landing"]["proof"] == "base_refresh"
    assert report["landing"]["refresh"] == {"base_parent": delivered.new_base}


def test_a_refresh_that_resolved_a_conflict_by_hand_is_unverified(delivered):
    deliver(delivered)
    advance_base(delivered, conflict=True)
    resolved = tree_with(delivered, delivered.tree, replacements=[("tracked.txt", "Resolved by hand\n")])
    pr_head = real("commit-tree", resolved, "-p", delivered.head, "-p", delivered.new_base, "-m", "Merge main into feature",
                   cwd=delivered.root)
    land(delivered, pr_head=pr_head, tree=resolved, parents=(delivered.new_base, pr_head))
    report = preview(delivered)
    assert report["landing"]["status"] == "unverified" and report["recordable"] is False
    assert report["landing"]["reason"] == "refresh_is_not_a_clean_merge"


def test_a_pull_request_against_another_target_is_rejected(delivered):
    deliver(delivered)
    land(delivered)
    delivered.native.pull["base"]["ref"] = "release"
    assert "branch does not match" in rejected(delivered, "--preview")


def test_a_retained_source_that_cannot_be_proven_is_unavailable(delivered):
    deliver(delivered)
    land(delivered)
    write_record(delivered, lambda record: record["commits"][-1].update(id="1" * 40))
    report = preview(delivered)
    assert report["landing"]["status"] == "unavailable" and report["recordable"] is False
    assert report["landing"]["reason"] == "retained_source_unavailable"
    assert "nothing to record" in rejected(
        delivered, "--expected-receipt-digest", report["receipt_digest"], "--approval", "agent-confirmed")


def test_wrong_pull_request_or_stale_head_is_rejected(delivered):
    deliver(delivered)
    land(delivered)
    wrong = post(delivered)
    wrong[wrong.index("--pr-number") + 1] = str(NUMBER + 1)
    assert "does not match the request" in rejected_argv(delivered, wrong)
    wrong_merge = post(delivered, "--preview")
    wrong_merge[wrong_merge.index("--expected-merge") + 1] = delivered.base
    assert "pinned merged source" in rejected_argv(delivered, wrong_merge)
    land(delivered, pr_head=edit(delivered, "Later edit\n"))
    stale = post(delivered, "--preview")
    stale[stale.index("--expected-head") + 1] = delivered.head
    assert "not the current pull request head" in rejected_argv(delivered, stale)


def test_active_and_externally_completed_records_keep_their_own_routes(delivered, capsys):
    prepare(delivered)
    land(delivered)
    assert "require a completed cycle" in rejected(delivered, "--preview")
    assert delivered.invoke(*external.arguments(delivered)) == 0
    capsys.readouterr()
    assert "external completion receipt" in rejected(delivered, "--preview")


def test_unflagged_completion_is_unchanged_for_a_final_push_delivery(delivered):
    deliver(delivered)
    land(delivered)
    assert delivered.invoke("complete-external", "--cycle-id", "cycle-1", "--pr-number", str(NUMBER),
                            "--expected-head", delivered.pr_head, "--expected-merge", delivered.merge) == 1
    assert "already externally completed record" in delivered.capsys.readouterr().err


def test_invalid_selections_are_refused_before_any_native_read(delivered):
    deliver(delivered)
    land(delivered)
    for argv in (
        post(delivered, "--proof", "rebased_commits"),
        post(delivered, "--review-evidence", "operate"),
        post(delivered, "--review-evidence", "operate:abc:cycle-2"),
        post(delivered, "--owner-review", "operate:" + "f" * 64, "--review-evidence", "deploy:" + "f" * 64 + ":cycle-2:ev-1"),
    ):
        assert rejected_argv(delivered, argv)
    assert delivered.invoke("complete-external", "--post-delivery", "--cycle-id", "../escape", "--pr-number", "1",
                            "--expected-head", "a" * 40, "--expected-merge", "b" * 40) == 1
    assert delivered.invoke("complete-external", "--post-delivery", "--pr-number", str(NUMBER), "--expected-head", "a" * 40,
                            "--expected-merge", "b" * 40) == 1
    assert delivered.invoke("status", "--post-delivery", "--json") == 1
    assert delivered.invoke("status", "--post-delivery", "--cycle-id", "missing-cycle", "--json") == 1
    assert "dbsctrctl:" in delivered.capsys.readouterr().err
    assert delivered.native.calls == []


def test_a_judgment_condition_needs_its_named_owners_decision(delivered):
    deliver(delivered)
    land(delivered)
    operate = f"operate:{condition(preview(delivered), 'operate')['condition']}"
    assert "does not match a deferred condition" in rejected(
        delivered, "--owner-review", "operate:not-a-condition", "--preview")
    assert "does not match a deferred condition" in rejected(
        delivered, "--review-evidence", "operate:" + "f" * 64 + ":cycle-2:ev-1", "--preview")
    accepted = condition(preview(delivered, "--owner-review", operate), "operate")
    assert accepted["disposition"] == "owner_accepted" and accepted["reason"] is None and accepted["owner"] == OWNER
    assert accepted["owner_decision"] == {"method": "agent_reported", "attribution": "caller_assertion"}
    # Selecting one condition cannot hide the others.
    assert [item["disposition"] for item in preview(delivered, "--owner-review", operate)["conditions"]] == [
        "unverified", "owner_accepted", "unverified"]


def test_a_measurable_condition_is_verified_only_by_matching_later_evidence(delivered, monkeypatch):
    deliver(delivered, review={"operate": PREDICATE})
    source = later_cycle(delivered, monkeypatch)
    land(delivered)
    evidence_id = source["gates"]["operate"]["evidence"]
    selector = ("--review-evidence", f"operate:operate-green:{source['cycle_id']}:{evidence_id}")
    operate = condition(preview(delivered, *selector), "operate")
    assert operate["kind"] == "measurable" and operate["condition"] == "operate-green"
    assert operate["predicate"] == PREDICATE["predicate"]
    assert operate["disposition"] == "verified" and operate["reason"] is None
    (link,) = operate["evidence"]
    assert link == {"source_cycle": "cycle-2", "evidence_id": evidence_id, "gate": "operate", "authority": "hosted-check",
                    "result": "passed", "commit": source["commits"][-1]["id"], "started_at": link["started_at"],
                    "binding": "legacy", "coverage": [], "applicable": True, "reason": None}
    assert [item["disposition"] for item in preview(delivered, *selector)["conditions"]] == [
        "unverified", "verified", "unverified"]
    assert "does not match a deferred condition" in rejected(
        delivered, "--review-evidence", f"deploy:operate-green:cycle-2:{evidence_id}", "--preview")
    # A prose condition is never verified by evidence, however well it matches.
    write_record(delivered, lambda record: record["gates"]["operate"]["exception"].pop("review"))
    prose = f"operate:{hashlib.sha256(b'Check operate after publication').hexdigest()}"
    report = preview(delivered, "--review-evidence", f"{prose}:cycle-2:{evidence_id}")
    operate = condition(report, "operate")
    assert operate["disposition"] == "unverified" and operate["reason"] == "prose_condition_has_no_predicate"
    assert operate["evidence"][0]["applicable"] is True


def test_mismatched_or_unusable_later_evidence_never_verifies(delivered, monkeypatch):
    deliver(delivered, review={"operate": PREDICATE})
    mismatched = later_cycle(delivered, monkeypatch, authority="other-check")
    unknown = later_cycle(delivered, monkeypatch, code=1, cycle_id="cycle-3")
    later_cycle(delivered, monkeypatch, finish=False, cycle_id="cycle-4")
    land(delivered)
    selectors = ("--review-evidence", f"operate:operate-green:cycle-2:{mismatched['gates']['operate']['evidence']}",
                 "--review-evidence", f"operate:operate-green:cycle-3:{unknown['gates']['operate']['evidence']}")
    operate = condition(preview(delivered, *selectors), "operate")
    assert operate["disposition"] == "not_met" and operate["reason"] == "predicate_contradicted"
    assert [(link["source_cycle"], link["result"], link["applicable"], link["reason"]) for link in operate["evidence"]] == [
        ("cycle-2", "passed", False, "authority_mismatch"), ("cycle-3", "failed", True, None)]
    for selector, reason in ((f"operate:operate-green:missing:ev-1", "source_cycle_not_found"),
                             (f"operate:operate-green:cycle-4:ev-1", "source_cycle_not_completed"),
                             (f"operate:operate-green:cycle-2:ev-not-current", "evidence_is_not_current_for_gate")):
        operate = condition(preview(delivered, "--review-evidence", selector), "operate")
        assert operate["disposition"] == "unverified" and operate["evidence"][0]["reason"] == reason
    # Trusting one link does not settle the other deferred conditions.
    assert [item["disposition"] for item in preview(delivered, *selectors)["conditions"]] == [
        "unverified", "not_met", "unverified"]


def test_a_stale_runtime_binding_or_uncovered_requirement_cannot_verify(delivered, monkeypatch):
    """The binding payload and policy are served to this test on purpose: it checks the
    freshness and coverage rules, not custody, which the binding suites own."""
    core = delivered.core
    deliver(delivered, review={"operate": PREDICATE})
    source = later_cycle(delivered, monkeypatch)
    land(delivered)
    evidence_id = source["gates"]["operate"]["evidence"]
    path = core.cycle_dir(delivered.root) / "cycles" / "cycle-2.json"
    record = json.loads(path.read_text())
    record["evidence"]["bindings"] = {evidence_id: {"schema_version": 1, "sha256": "0" * 64}}
    path.write_text(json.dumps(record))
    payload = {"coverage": [{"id": "INT-001", "revision": "1"}], "runtime": None}
    monkeypatch.setattr(core, "load_evidence_binding", lambda *_args, **_kwargs: payload)
    policy = {"schema_version": 1,
              "requirements": {"INT-001": {"revision": "1", "depends_on": [], "gates": ["operate"]}},
              "gates": {"operate": {"runtime": {"max_age_seconds": 3600}}}}
    original = core.effective_evidence_policy
    monkeypatch.setattr(core, "effective_evidence_policy",
                        lambda record: policy if record.get("cycle_id") == "cycle-2" else original(record))
    selector = ("--review-evidence", f"operate:operate-green:cycle-2:{evidence_id}")
    payload["runtime"] = {"identity": {}, "validated_at": "2020-01-01T00:00:00Z"}
    operate = condition(preview(delivered, *selector), "operate")
    assert operate["disposition"] == "unverified" and operate["evidence"][0]["reason"] == "runtime_acceptance_stale"
    assert operate["evidence"][0]["binding"] == "bound" and operate["evidence"][0]["coverage"] == ["INT-001"]
    payload["runtime"] = {"identity": {}, "validated_at": core.now()}
    write_record(delivered, lambda record: record["gates"]["operate"]["exception"]["review"]["predicate"].update(
        requirement="INT-002"))
    operate = condition(preview(delivered, *selector), "operate")
    assert operate["disposition"] == "unverified" and operate["evidence"][0]["reason"] == "requirement_not_covered"
    write_record(delivered, lambda record: record["gates"]["operate"]["exception"]["review"]["predicate"].pop("requirement"))
    assert condition(preview(delivered, *selector), "operate")["disposition"] == "verified"


def test_a_second_observation_links_its_predecessor_and_a_moved_plan_needs_a_fresh_preview(delivered):
    deliver(delivered)
    land(delivered)
    first = preview(delivered)["receipt_digest"]
    # Same record content in different bytes: the receipt binds the exact bytes.
    write_record(delivered, lambda record: None)
    assert "plan changed" in rejected(delivered, "--expected-receipt-digest", first, "--approval", "agent-confirmed")
    first = preview(delivered)["receipt_digest"]
    append(delivered, first)
    report = stored(delivered)
    operate = f"operate:{condition(report['latest'], 'operate')['condition']}"
    assert len(report["outstanding"]) == 3 and len(report["receipts"]) == 1
    second = preview(delivered, "--owner-review", operate)
    assert second["previous"] == first
    # The observed target is part of the approved plan.
    later = real("commit-tree", f"{delivered.merge}^{{tree}}", "-p", delivered.merge, "-m", "Later target", cwd=delivered.root)
    real("update-ref", "refs/remotes/origin/main", later, cwd=delivered.root)
    assert "plan changed" in rejected(
        delivered, "--expected-receipt-digest", second["receipt_digest"], "--approval", "agent-confirmed")
    assert len(receipt_names(delivered)) == 1
    fresh = preview(delivered, "--owner-review", operate)
    assert fresh["previous"] == first and fresh["receipt_digest"] != second["receipt_digest"]
    result = append(delivered, fresh["receipt_digest"], "--owner-review", operate)
    assert result["sequence"] == 2 and result["previous"] == first and result["mode"] == "recorded"
    report = stored(delivered)
    assert [item["sequence"] for item in report["receipts"]] == [1, 2]
    assert [item["record_matches"] for item in report["receipts"]] == [True, True]
    assert report["previous"] == first and report["record_matches_latest"] is True
    assert [(item["gate"], item["disposition"]) for item in report["outstanding"]] == [
        ("deploy", "unverified"), ("maintain_retire", "unverified")]


def test_a_changed_record_is_reported_against_each_receipt(delivered):
    deliver(delivered)
    land(delivered)
    first = preview(delivered)["receipt_digest"]
    append(delivered, first)
    raw = delivered.path.read_bytes()
    delivered.path.write_bytes(raw + b"\n")
    report = stored(delivered)
    assert report["record_matches_latest"] is False and [item["record_matches"] for item in report["receipts"]] == [False]
    second = preview(delivered)
    assert second["receipt_digest"] != first and second["previous"] == first
    append(delivered, second["receipt_digest"])
    report = stored(delivered)
    assert [item["record_matches"] for item in report["receipts"]] == [False, True]
    assert report["record_matches_latest"] is True
    delivered.path.write_bytes(raw)
    assert [item["record_matches"] for item in stored(delivered)["receipts"]] == [True, False]


@pytest.mark.parametrize("cycle", [None, "initiative"], indirect=True)
def test_observation_runs_from_another_checkout_after_the_pointer_is_gone(delivered, monkeypatch):
    """The cycle's own checkout is not needed, even for an Initiative record bound to it."""
    deliver(delivered)
    land(delivered)
    primary = delivered.primary
    monkeypatch.chdir(primary)
    monkeypatch.setattr(delivered.core, "root_dir", lambda: primary)
    native = external.NativeGitHub(delivered.core, primary, delivered.base, delivered.head, delivered.merge)
    native.pull["head"]["ref"] = json.loads(delivered.path.read_text())["delivery"]["branch"]
    monkeypatch.setattr(delivered.core, "github_environment", native.environment)
    monkeypatch.setattr(delivered.core, "github_json", native.json)
    report = preview(delivered)
    assert report["landing"]["status"] == "verified" and report["recordable"] is True
    assert append(delivered, report["receipt_digest"])["sequence"] == 1
    assert [item["sequence"] for item in stored(delivered)["receipts"]] == [1]


def test_an_unrelated_active_cycle_does_not_block_and_a_held_lock_refuses(delivered, monkeypatch):
    deliver(delivered)
    later_cycle(delivered, monkeypatch, finish=False)
    land(delivered)
    digest = preview(delivered)["receipt_digest"]
    lock = delivered.core.evidence_lock(delivered.root, "cycle-1", timeout=1)
    lock.__enter__()
    try:
        assert "busy" in rejected(delivered, "--expected-receipt-digest", digest, "--approval", "agent-confirmed")
    finally:
        lock.__exit__(None, None, None)
    assert append(delivered, digest)["sequence"] == 1


def test_corrupt_or_unknown_receipt_custody_is_refused(delivered):
    deliver(delivered)
    land(delivered)
    append(delivered, preview(delivered)["receipt_digest"])
    (path,) = (delivered.core.cycle_dir(delivered.root) / "evidence" / "cycle-1" / "post-delivery").iterdir()
    raw = path.read_bytes()
    stray = path.parent / "stray.json"
    for change, restore in (
        (lambda: path.write_bytes(raw.replace(b'"verified"', b'"unverified"')), lambda: path.write_bytes(raw)),
        (lambda: path.write_bytes(raw.replace(b'"schema_version":1', b'"schema_version":2', 1)), lambda: path.write_bytes(raw)),
        (lambda: path.chmod(0o644), lambda: path.chmod(0o600)),
        (lambda: stray.write_text("{}"), lambda: stray.unlink()),
    ):
        change()
        assert "custody is invalid" in rejected_argv(
            delivered, ["status", "--post-delivery", "--cycle-id", "cycle-1", "--json"])
        restore()
    assert [item["sequence"] for item in stored(delivered)["receipts"]] == [1]


def removal_check(ws):
    """The removal check of a completed cycle exactly as the CLI reports it."""
    try:
        ws.invoke("workspace-remove-check")
        code = 0
    except SystemExit as error:
        code = error.code
    return code, ws.capsys.readouterr().out


def test_stored_receipts_grant_no_removal_eligibility_and_leave_plain_status_alone(delivered, monkeypatch):
    deliver(delivered)
    land(delivered)
    monkeypatch.setattr(delivered.core, "workspace_processes", lambda root: set())
    check = removal_check(delivered)
    assert check[0] == 1 and json.loads(check[1])["eligible"] is False
    assert delivered.invoke("status", "--json") == 0 and delivered.capsys.readouterr().out == "null\n"
    append(delivered, preview(delivered)["receipt_digest"])
    assert removal_check(delivered) == check
    assert delivered.invoke("status", "--json") == 0 and delivered.capsys.readouterr().out == "null\n"


@pytest.mark.parametrize("cycle", [None, "initiative"], indirect=True)
def test_review_options_are_refused_outside_the_post_delivery_mode(delivered):
    deliver(delivered)
    land(delivered)
    plain = ["complete-external", "--cycle-id", "cycle-1", "--pr-number", str(NUMBER),
             "--expected-head", delivered.pr_head, "--expected-merge", delivered.merge, "--preview"]
    for option in (["--review-evidence", "operate:abc:cycle-2:ev-1"], ["--owner-review", "operate:abc"],
                   ["--expected-receipt-digest", "0" * 64], ["--approval", "agent-confirmed"]):
        assert "require --post-delivery" in rejected_argv(delivered, [*plain, *option])
    assert "requires --post-delivery" in rejected_argv(delivered, ["status", "--cycle-id", "cycle-1", "--json"])
    assert "cannot be combined" in rejected(
        delivered, "--delivery-segment", f"{NUMBER}:{delivered.pr_head}:{delivered.merge}")


def test_verification_uses_the_remote_name_the_delivery_recorded(delivered):
    deliver(delivered)
    land(delivered)
    # The same repository reached through another remote name is still that repository.
    write_record(delivered, lambda record: record["delivery"].update(remote="github"))
    assert preview(delivered)["landing"]["status"] == "verified"
    write_record(delivered, lambda record: record["delivery"].update(remote="--upload-pack=touch"))
    assert "does not match the request" in rejected(delivered, "--preview")


def test_a_predicate_must_name_the_gate_that_holds_the_exception(delivered):
    elsewhere = {**PREDICATE, "predicate": {**PREDICATE["predicate"], "gate": "deploy"}}
    deliver(delivered, review={"operate": elsewhere})
    land(delivered)
    assert "unsupported deferred review declaration" in rejected(delivered, "--preview")


def test_an_unpassed_gate_without_a_valid_exception_is_refused(delivered):
    deliver(delivered)
    land(delivered)
    write_record(delivered, lambda record: record["gates"]["operate"]["exception"].pop("review_condition"))
    assert "without a valid approved exception" in rejected(delivered, "--preview")


def test_an_interrupted_write_leaves_the_chain_readable(delivered):
    deliver(delivered)
    land(delivered)
    first = preview(delivered)["receipt_digest"]
    append(delivered, first)
    directory = delivered.core.cycle_dir(delivered.root) / "evidence" / "cycle-1" / "post-delivery"
    # What tempfile.mkstemp leaves behind when the writer is killed before its link.
    descriptor, _ = tempfile.mkstemp(dir=directory)
    os.write(descriptor, b'{"schema_version": 1, "kind": "post_delivery_rec')
    os.close(descriptor)
    assert [item["sequence"] for item in stored(delivered)["receipts"]] == [1]
    assert append(delivered, first)["mode"] == "already_recorded"
    operate = f"operate:{condition(preview(delivered), 'operate')['condition']}"
    second = preview(delivered, "--owner-review", operate)
    assert second["previous"] == first
    assert append(delivered, second["receipt_digest"], "--owner-review", operate)["sequence"] == 2
    assert len(list(directory.iterdir())) == 3


def test_each_failed_evidence_check_reports_its_own_reason(delivered, monkeypatch):
    core = delivered.core
    real_policy = core.effective_evidence_policy
    deliver(delivered, review={"operate": PREDICATE})
    source = later_cycle(delivered, monkeypatch)
    land(delivered)
    evidence_id = source["gates"]["operate"]["evidence"]
    selector = ("--review-evidence", f"operate:operate-green:cycle-2:{evidence_id}")
    path = core.cycle_dir(delivered.root) / "cycles" / "cycle-2.json"
    original = path.read_text()
    renamed = json.loads(original)
    renamed["git"]["remote"]["name"] = "github"
    path.write_text(json.dumps(renamed))
    assert condition(preview(delivered, *selector), "operate")["disposition"] == "verified"

    def reason(change, policy=None):
        record = json.loads(original)
        change(record)
        path.write_text(json.dumps(record))
        monkeypatch.setattr(core, "effective_evidence_policy", real_policy if policy is None else (
            lambda stated: policy if stated.get("cycle_id") == "cycle-2" else real_policy(stated)))
        link = condition(preview(delivered, *selector), "operate")["evidence"][0]
        assert link["applicable"] is False
        return link["reason"]

    assert reason(lambda record: record["git"]["remote"].update(push_url="https://github.com/other/project.git")) == \
        "source_repository_differs"
    assert reason(lambda record: record["evidence"]["items"][evidence_id].update(
        started_at="2000-01-01T00:00:00Z")) == "evidence_predates_delivery"
    assert reason(lambda record: record["commits"][-1]["gates"].remove("operate")) == \
        "evidence_not_bound_to_source_delivery"
    assert reason(lambda record: record["evidence"]["items"][evidence_id].update(result="failed")) == \
        "evidence_or_binding_unavailable"
    declared = {"schema_version": 1, "requirements": {"INT-001": {"revision": "1", "depends_on": [], "gates": ["operate"]}},
                "gates": {"operate": {"runtime": {"max_age_seconds": 3600}}}}
    assert reason(lambda record: None, policy=declared) == "binding_unavailable"


def test_owner_review_cannot_override_a_contradicted_predicate(delivered, monkeypatch):
    deliver(delivered, review={"operate": PREDICATE})
    failed = later_cycle(delivered, monkeypatch, code=1)
    land(delivered)
    operate = condition(preview(delivered,
                                "--review-evidence", f"operate:operate-green:cycle-2:{failed['gates']['operate']['evidence']}",
                                "--owner-review", "operate:operate-green"), "operate")
    assert operate["disposition"] == "not_met" and operate["owner_decision"]["method"] == "agent_reported"
    # A measurable condition without evidence still awaits proof or its owner.
    operate = condition(preview(delivered, "--owner-review", "operate:operate-green"), "operate")
    assert operate["disposition"] == "owner_accepted" and operate["evidence"] == []


def test_an_unknown_landing_commit_is_reported_as_such(delivered):
    deliver(delivered)
    advance_base(delivered)
    refresh(delivered)
    argv = post(delivered)
    argv[argv.index("--expected-merge") + 1] = "1" * 40
    report = preview_argv(delivered, argv)
    assert report["landing"]["status"] == "unverified" and report["recordable"] is False
    assert report["landing"]["reason"] == "landing_commit_does_not_land_pull_head"


def test_a_refresh_that_resolved_a_criss_cross_merge_is_unverified(delivered):
    """Two merge bases: one forced candidate can look clean where Git's own merge conflicts."""
    deliver(delivered)

    def commit(tree, *parents, message):
        return real("commit-tree", tree, *[flag for parent in parents for flag in ("-p", parent)], "-m", message,
                    cwd=delivered.root)

    def with_file(tree, text):
        return tree_with(delivered, tree, additions=[("f.txt", text)])

    base_tree = f"{delivered.base}^{{tree}}"
    first = commit(with_file(base_tree, "first\n"), delivered.base, message="first base branch")
    second = commit(with_file(base_tree, "second\n"), delivered.base, message="second base branch")
    base_tip = commit(with_file(base_tree, "first second\n"), first, second, message="base merges its branches")
    # The delivery took each base branch in turn and kept the second one's content.
    taken = commit(with_file(delivered.tree, "first\n"), delivered.head, first, message="take in first")
    tip = commit(with_file(delivered.tree, "second\n"), taken, second, message="take in second")
    write_record(delivered, lambda record: record["commits"].extend(
        [{"id": taken, "gates": []}, {"id": tip, "gates": []}]))
    merge_bases = real("merge-base", "--all", tip, base_tip, cwd=delivered.root).split()
    assert sorted(merge_bases) == sorted([first, second])
    # The refresh keeps the base's content, which is what one forced merge base would also produce.
    refresh_head = commit(with_file(delivered.tree, "first second\n"), tip, base_tip, message="Merge main into feature")
    land(delivered, pr_head=refresh_head, tree=with_file(delivered.tree, "first second\n"),
         parents=(base_tip, refresh_head))
    report = preview(delivered)
    assert report["landing"]["status"] == "unverified" and report["recordable"] is False
    assert report["landing"]["reason"] == "refresh_is_not_a_clean_merge"


def test_a_missing_cycle_base_is_reported_not_mistaken_for_an_unreadable_base(delivered):
    deliver(delivered)
    land(delivered)
    write_record(delivered, lambda record: record["git"].update(head="1" * 40))
    report = preview(delivered)
    assert report["landing"]["status"] == "unavailable" and report["recordable"] is False
    assert report["landing"]["reason"] == "retained_source_unavailable"


def test_append_options_are_refused_on_a_preview(delivered):
    deliver(delivered)
    land(delivered)
    for option in (["--expected-receipt-digest", "0" * 64], ["--approval", "agent-confirmed"]):
        assert "not to a preview" in rejected_argv(delivered, post(delivered, "--preview", *option))


def test_a_hand_edited_receipt_with_a_recomputed_digest_is_refused(delivered):
    core = delivered.core
    deliver(delivered)
    land(delivered)
    append(delivered, preview(delivered)["receipt_digest"])
    (path,) = [item for item in (core.cycle_dir(delivered.root) / "evidence" / "cycle-1" / "post-delivery").iterdir()]
    value = json.loads(path.read_text())
    value["original"].pop("record_sha256")
    value["digest"] = core.continuation_digest({key: value[key] for key in core.POST_DELIVERY_CORE})
    # Someone with custody access who also knows the digest scheme: still a bounded refusal.
    path.write_text(core.amendment_bytes(value).decode())
    path.rename(path.with_name(f"0001-{value['digest']}.json"))
    assert "custody is invalid" in rejected_argv(
        delivered, ["status", "--post-delivery", "--cycle-id", "cycle-1", "--json"])
