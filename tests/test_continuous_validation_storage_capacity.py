"""Whole-selection storage admission and generation freshness contracts."""

import json
from pathlib import Path

import pytest

from test_continuous_validation import (
    comparison_observation, configured, private_json, request, runner, worktree,
)


def retained_records(state):
    return {path.name: path.read_bytes()
            for path in (state / "observations").glob("*.json")}


def seed_observations(state, count, *, offset=0):
    """Retain valid, independent prior evidence without executing fixture checks."""
    runner.private_dir(state)
    runner.private_dir(state / "observations")
    for number in range(offset, offset + count):
        value = comparison_observation(state, id=f"retained-{number}",
                                       request_id=f"retained-request-{number}")
        runner.validate_observation(value)
        private_json(state / "observations" / (value["id"] + ".json"), value)


def generation_records(state):
    return {path.name: path.read_bytes() for path in state.glob("current-*.json")}


def watch_executions(monkeypatch):
    calls = []
    original = runner.adapter_call

    def adapter_call(enrollment, action, payload, *args, **kwargs):
        if action == "execute":
            calls.append(payload["check"]["id"])
        return original(enrollment, action, payload, *args, **kwargs)

    monkeypatch.setattr(runner, "adapter_call", adapter_call)
    return calls


def assert_capacity_refusal(result):
    assert result["status"] == "unavailable"
    assert result["error_code"] == "observation_retention_limit"
    assert result["observations"] == []
    assert result["new_execution"] is False


def test_two_selected_checks_cannot_take_one_remaining_slot(configured, monkeypatch):
    path, value = configured
    state = Path(value["state_dir"])
    baseline = runner.run_request({**request(path), "request_id": "admitted-before-refusal"})
    assert len(baseline["observations"]) == 1
    seed_observations(state, 198)
    before = retained_records(state)
    current = generation_records(state)
    assert len(before) == 199 and current
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path, "checkpoint"), "request_id": "two-demand"})

    assert_capacity_refusal(result)
    assert executions == []
    assert retained_records(state) == before
    assert generation_records(state) == current


def test_one_eligible_edit_check_can_take_last_slot(configured, monkeypatch):
    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 199)
    before = retained_records(state)
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path), "request_id": "one-demand"})

    assert result["status"] == "pending"
    assert result["pending_checks"] == ["slow"]
    assert [item["check_id"] for item in result["observations"]] == ["quick"]
    assert executions == ["quick"]
    after = retained_records(state)
    assert len(after) == 200
    assert all(after[name] == contents for name, contents in before.items())


def select_checks(monkeypatch, checks, *, complete=True, cacheable=False):
    original = runner.adapter_call

    def adapter_call(enrollment, action, payload, *args, **kwargs):
        result = original(enrollment, action, payload, *args, **kwargs)
        if action == "select":
            return {**result, "checks": list(checks), "complete": complete}
        if action == "describe" and cacheable:
            result["checks"][0].update(cacheable=True, configuration={"hermetic": True})
        return result

    monkeypatch.setattr(runner, "adapter_call", adapter_call)


@pytest.mark.parametrize("count", [200, 201])
@pytest.mark.parametrize("selected", [[], ["slow"]])
def test_full_or_overfull_store_refuses_even_zero_observation_demand(
        configured, monkeypatch, count, selected):
    path, value = configured
    state = Path(value["state_dir"])
    baseline = runner.run_request({**request(path), "request_id": "baseline-full"})
    assert len(baseline["observations"]) == 1
    seed_observations(state, count - 1)
    before = retained_records(state)
    current = generation_records(state)
    select_checks(monkeypatch, selected)
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path), "request_id": "new-at-capacity"})

    assert_capacity_refusal(result)
    assert executions == []
    assert retained_records(state) == before
    assert generation_records(state) == current


@pytest.mark.parametrize("selected,complete,pending", [
    (["slow"], True, ["slow"]),
    ([], False, ["selection_incomplete"]),
])
def test_deferred_or_incomplete_selection_creates_no_synthetic_observation(
        configured, monkeypatch, selected, complete, pending):
    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 199)
    before = retained_records(state)
    select_checks(monkeypatch, selected, complete=complete)
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path), "request_id": "no-observation-demand"})

    assert result["status"] == "pending"
    assert result["observations"] == []
    assert result["pending_checks"] == pending
    assert executions == []
    assert retained_records(state) == before


@pytest.mark.parametrize("count", [199, 200])
def test_cache_reuse_requires_its_own_observation_slot(configured, monkeypatch, count):
    path, value = configured
    state = Path(value["state_dir"])
    select_checks(monkeypatch, ["quick"], cacheable=True)
    first = runner.run_request({**request(path), "request_id": "cache-origin"})
    assert first["observations"][0]["cache_reused"] is False
    seed_observations(state, count - 1)
    before = retained_records(state)
    current = generation_records(state)
    caches = {p.name: p.read_bytes() for p in (state / "cache").glob("*.json")}
    assert len(caches) == 1
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path), "request_id": "cache-consumer"})

    assert executions == []
    assert {p.name: p.read_bytes() for p in (state / "cache").glob("*.json")} == caches
    if count == 200:
        assert_capacity_refusal(result)
        assert retained_records(state) == before
        assert generation_records(state) == current
    else:
        assert result["status"] == "passed"
        assert len(result["observations"]) == 1
        reused = result["observations"][0]
        assert reused["cache_reused"] is True
        assert reused["executed"] is False
        assert reused["id"] != first["observations"][0]["id"]
        assert reused["reused_from"] == first["observations"][0]["id"]
        assert len(retained_records(state)) == 200


@pytest.mark.parametrize("count", [197, 198])
def test_optional_review_counts_in_whole_selection_before_any_execution(
        configured, monkeypatch, count):
    from continuous_validation import feedback
    from test_continuous_validation_pr_agent_integration import (
        enable_review, install_review_double, review_module,
    )

    path, value = configured
    state = Path(value["state_dir"])
    reviews = []
    notifications = []
    install_review_double(monkeypatch, review_module(reviews))
    enable_review(path, value)
    monkeypatch.setattr(feedback, "deliver", lambda *args, **kwargs:
                        notifications.append(args) or {"status": "unavailable", "reason": "fixture"})
    seed_observations(state, count)
    before = retained_records(state)
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path, "checkpoint"), "request_id": "review-demand"})

    if count == 198:
        assert_capacity_refusal(result)
        assert executions == []
        assert reviews == []
        assert notifications == []
        assert retained_records(state) == before
        assert generation_records(state) == {}
    else:
        assert [item["check_id"] for item in result["observations"]] == [
            "quick", "slow", "pr-agent-review"]
        assert executions == ["quick", "slow"]
        assert len(reviews) == 1
        assert len(retained_records(state)) == 200


def test_completed_request_at_capacity_is_query_without_storage_changes(configured, monkeypatch):
    path, value = configured
    state = Path(value["state_dir"])
    payload = {**request(path), "request_id": "completed-at-capacity"}
    first = runner.run_request(payload)
    seed_observations(state, 199)
    assert len(retained_records(state)) == 200
    before = {str(p.relative_to(state)): p.read_bytes()
              for p in state.rglob("*") if p.is_file()}
    executions = watch_executions(monkeypatch)

    result = runner.run_request(payload)

    assert result["new_execution"] is False
    assert result["observations"] == first["observations"]
    assert executions == []
    assert {str(p.relative_to(state)): p.read_bytes()
            for p in state.rglob("*") if p.is_file()} == before


def test_forked_requests_cannot_reserve_same_last_slot(configured):
    import multiprocessing

    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 199)
    before = retained_records(state)
    context = multiprocessing.get_context("fork")
    selected = context.Barrier(2)
    results = context.Queue()
    original = runner.adapter_call

    def worker(label):
        executions = []

        def adapter_call(enrollment, action, payload, *args, **kwargs):
            if action == "select":
                selected.wait(timeout=10)
                return {"schema_version": 1, "checks": ["quick"],
                        "reason": "one-slot contention fixture", "complete": True}
            if action == "execute":
                executions.append(payload["check"]["id"])
            return original(enrollment, action, payload, *args, **kwargs)

        runner.adapter_call = adapter_call
        try:
            result = runner.run_request({**request(path), "request_id": label})
            results.put((label, result, executions))
        except BaseException as error:
            results.put((label, {"fixture_error": repr(error)}, executions))
            raise

    processes = [context.Process(target=worker, args=(label,))
                 for label in ("contender-one", "contender-two")]
    try:
        for process in processes:
            process.start()
        outcomes = [results.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(timeout=5)
        assert all(process.exitcode == 0 for process in processes), outcomes
        assert all("fixture_error" not in result for _, result, _ in outcomes), outcomes
        assert sum(len(executions) for _, _, executions in outcomes) == 1
        assert sum(len(result["observations"]) for _, result, _ in outcomes) == 1
        refused = [result for _, result, _ in outcomes if not result["observations"]]
        assert len(refused) == 1
        assert refused[0]["status"] in {"unavailable", "interrupted"}
        assert refused[0]["error_code"] in {"observation_retention_limit", "superseded"}
        after = retained_records(state)
        assert len(after) == 200
        assert all(after[name] == contents for name, contents in before.items())
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)
        results.close()
        results.join_thread()


def test_stale_preparation_cannot_supersede_newer_admitted_request(configured):
    import multiprocessing

    path, value = configured
    state = Path(value["state_dir"])
    context = multiprocessing.get_context("fork")
    preparing = context.Event()
    release_preparation = context.Event()
    newer_executing = context.Event()
    release_newer = context.Event()
    results = context.Queue()
    original = runner.adapter_call

    def worker(label):
        executions = []

        def adapter_call(enrollment, action, payload, *args, **kwargs):
            if label == "older-preparation" and action == "describe":
                result = original(enrollment, action, payload, *args, **kwargs)
                preparing.set()
                assert release_preparation.wait(timeout=15), "old preparation not released"
                return result
            if action == "execute":
                executions.append(payload["check"]["id"])
                if label == "newer-admitted":
                    newer_executing.set()
                    assert release_newer.wait(timeout=15), "new execution not released"
            return original(enrollment, action, payload, *args, **kwargs)

        runner.adapter_call = adapter_call
        try:
            result = runner.run_request({**request(path), "request_id": label})
            results.put((label, result, executions))
        except BaseException as error:
            results.put((label, {"fixture_error": repr(error)}, executions))
            raise

    older = context.Process(target=worker, args=("older-preparation",))
    newer = context.Process(target=worker, args=("newer-admitted",))
    try:
        older.start()
        assert preparing.wait(timeout=10), "older request did not start preparation"
        newer.start()
        assert newer_executing.wait(timeout=10), "newer request was not admitted"
        admitted = generation_records(state)
        assert len(admitted) == 1
        assert json.loads(next(iter(admitted.values())))["request_id"] == "newer-admitted"
        release_preparation.set()
        old_label, old_result, old_executions = results.get(timeout=15)
        assert old_label == "older-preparation"
        assert old_result.get("status") == "interrupted", old_result
        assert old_result["error_code"] == "superseded"
        assert old_result["observations"] == []
        assert old_executions == []
        assert generation_records(state) == admitted
        release_newer.set()
        new_label, new_result, new_executions = results.get(timeout=15)
        assert new_label == "newer-admitted"
        assert new_result["status"] == "pending"
        assert new_executions == ["quick"]
        assert new_result["observations"][0]["status"] == "passed"
        assert generation_records(state) == admitted
        for process in (older, newer):
            process.join(timeout=5)
            assert process.exitcode == 0
    finally:
        release_preparation.set()
        release_newer.set()
        for process in (older, newer):
            if process.pid is not None:
                process.join(timeout=5)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
        results.close()
        results.join_thread()


def test_unmaterialized_reservation_refuses_new_work_without_canceling_owner(configured):
    import multiprocessing

    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 199)
    before = retained_records(state)
    context = multiprocessing.get_context("fork")
    executing = context.Event()
    release = context.Event()
    results = context.Queue()
    original = runner.adapter_call

    def worker():
        def adapter_call(enrollment, action, payload, *args, **kwargs):
            if action == "execute":
                executing.set()
                assert release.wait(timeout=15), "reserved check not released"
            return original(enrollment, action, payload, *args, **kwargs)

        runner.adapter_call = adapter_call
        try:
            results.put(runner.run_request({**request(path), "request_id": "reservation-owner"}))
        except BaseException as error:
            results.put({"fixture_error": repr(error)})
            raise

    owner = context.Process(target=worker)
    try:
        owner.start()
        assert executing.wait(timeout=10), "first request did not execute"
        current = generation_records(state)
        assert retained_records(state) == before

        refused = runner.run_request({**request(path), "request_id": "one-more-slot"})

        assert_capacity_refusal(refused)
        assert generation_records(state) == current
        assert retained_records(state) == before
        release.set()
        completed = results.get(timeout=15)
        assert completed["status"] == "pending", completed
        assert completed["observations"][0]["status"] == "passed"
        assert len(retained_records(state)) == 200
        owner.join(timeout=5)
        assert owner.exitcode == 0
    finally:
        release.set()
        if owner.pid is not None:
            owner.join(timeout=5)
            if owner.is_alive():
                owner.terminate()
                owner.join(timeout=5)
        results.close()
        results.join_thread()


def test_compute_admission_deferral_still_consumes_observation_slot(configured, monkeypatch):
    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 199)
    select_checks(monkeypatch, ["slow"])
    private_json(path, {**value, "admission_timeout_seconds": 0.1})
    monkeypatch.setattr(runner, "pressure", lambda _: True)
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path, "checkpoint"), "request_id": "deferred-slot"})

    assert result["status"] == "pending"
    assert result["pending_checks"] == ["slow"]
    assert len(result["observations"]) == 1
    deferred = result["observations"][0]
    assert deferred["status"] == "pending"
    assert deferred["diagnostic_codes"] == ["admission_deferred"]
    assert deferred["executed"] is False
    assert deferred["cache_reused"] is False
    assert executions == []
    assert len(retained_records(state)) == 200
    assert_capacity_refusal(runner.run_request({
        **request(path, "checkpoint"), "request_id": "after-deferred-slot"}))


def crash_after_reservation(path, *, started=False):
    """Crash a real controller after admission, before its first check starts."""
    import multiprocessing
    import os

    context = multiprocessing.get_context("fork")

    def worker():
        original_start = runner.start_observation

        def crash_start(*args):
            if started:
                original_start(*args)
            os._exit(73)

        runner.start_observation = crash_start
        runner.run_request({**request(path), "request_id": "crashed-reservation-owner"})
        os._exit(74)

    process = context.Process(target=worker)
    try:
        process.start()
        process.join(timeout=10)
        assert process.exitcode == 73, "controller did not crash after reservation"
        return process.pid
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)


@pytest.mark.parametrize("invalid_state", [[], {}])
def test_malformed_reservation_state_is_structured_refusal(configured, monkeypatch, invalid_state):
    path, value = configured
    state = Path(value["state_dir"])
    crash_after_reservation(path)
    ledger = state / "retention.json"
    accounting = json.loads(ledger.read_bytes())
    assert len(accounting["entries"]) == 1
    accounting["entries"][0]["state"] = invalid_state
    private_json(ledger, accounting)
    before = ledger.read_bytes()
    current = generation_records(state)
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path), "request_id": "malformed-ledger-query"})

    assert result["status"] == "unavailable"
    assert result["error_code"] == "observation_reservation_invalid"
    assert result["observations"] == []
    assert result["new_execution"] is False
    assert executions == []
    assert ledger.read_bytes() == before
    assert generation_records(state) == current
    assert retained_records(state) == {}


@pytest.mark.parametrize("started", [False, True])
def test_crashed_controller_reservation_never_expires_or_frees_with_dead_pid(
        configured, monkeypatch, started):
    import os

    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 199)
    process_id = crash_after_reservation(path, started=started)
    with pytest.raises(ProcessLookupError):
        os.kill(process_id, 0)
    ledger = state / "retention.json"
    accounting = json.loads(ledger.read_bytes())
    assert len(accounting["entries"]) == 1
    assert accounting["entries"][0]["state"] == ("started" if started else "reserved")
    assert len(retained_records(state)) == 199
    os.utime(ledger, (946684800, 946684800))
    before = ledger.read_bytes()
    retained = retained_records(state)
    current = generation_records(state)
    intent = state / "requests" / "crashed-reservation-owner.json"
    original_intent = intent.read_bytes()
    executions = watch_executions(monkeypatch)

    for number in range(2):
        result = runner.run_request({**request(path), "request_id": f"after-controller-death-{number}"})
        assert_capacity_refusal(result)
        assert ledger.read_bytes() == before
        assert generation_records(state) == current
        assert retained_records(state) == retained
    replay = runner.run_request({**request(path), "request_id": "crashed-reservation-owner"})
    assert replay["status"] == "unavailable"
    assert replay["error_code"] == "previous_execution_interrupted"
    assert replay["new_execution"] is False
    assert replay["observations"] == []
    assert intent.read_bytes() == original_intent
    assert executions == []
    assert ledger.read_bytes() == before
    assert generation_records(state) == current


def crash_after_observation_publication(path, state):
    """Leave an exact durable observation while its started charge remains."""
    import multiprocessing
    import os

    context = multiprocessing.get_context("fork")

    def worker():
        original_write = runner.write_private

        def write_private(target, *args, **kwargs):
            result = original_write(target, *args, **kwargs)
            if Path(target).parent == state / "observations":
                os._exit(75)
            return result

        runner.write_private = write_private
        runner.run_request({**request(path), "request_id": "crashed-publication-owner"})
        os._exit(76)

    process = context.Process(target=worker)
    try:
        process.start()
        process.join(timeout=10)
        assert process.exitcode == 75, "controller did not crash after observation publication"
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)


def test_materialized_reserved_id_is_counted_once_after_publication_crash(configured, monkeypatch):
    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 198)
    crash_after_observation_publication(path, state)
    ledger = state / "retention.json"
    accounting = json.loads(ledger.read_bytes())
    assert len(accounting["entries"]) == 1
    entry = accounting["entries"][0]
    assert entry["state"] == "started"
    published = state / "observations" / (entry["id"] + ".json")
    durable = published.read_bytes()
    assert json.loads(durable)["executed"] is True
    assert len(retained_records(state)) == 199
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path), "request_id": "after-publication-crash"})

    assert result["status"] == "pending"
    assert len(result["observations"]) == 1
    assert result["observations"][0]["status"] == "passed"
    assert executions == ["quick"]
    assert len(retained_records(state)) == 200
    assert published.read_bytes() == durable
    assert json.loads(ledger.read_bytes())["entries"] == []
    replay = runner.run_request({**request(path), "request_id": "crashed-publication-owner"})
    assert replay["status"] == "unavailable"
    assert replay["error_code"] == "previous_execution_interrupted"
    assert replay["new_execution"] is False
    assert executions == ["quick"]
    assert published.read_bytes() == durable


def test_materialized_reservation_with_swapped_identity_remains_refused(configured, monkeypatch):
    path, value = configured
    state = Path(value["state_dir"])
    seed_observations(state, 198)
    crash_after_observation_publication(path, state)
    ledger = state / "retention.json"
    accounting = json.loads(ledger.read_bytes())
    entry = accounting["entries"][0]
    published = state / "observations" / (entry["id"] + ".json")
    observation = json.loads(published.read_bytes())
    observation["request_id"] = "swapped-publication-owner"
    runner.validate_observation(observation)
    private_json(published, observation)
    before = retained_records(state)
    original_ledger = ledger.read_bytes()
    current = generation_records(state)
    executions = watch_executions(monkeypatch)

    result = runner.run_request({**request(path), "request_id": "after-swapped-publication"})

    assert result["status"] == "unavailable"
    assert result["error_code"] == "observation_reservation_identity_changed"
    assert result["observations"] == []
    assert result["new_execution"] is False
    assert executions == []
    assert retained_records(state) == before
    assert ledger.read_bytes() == original_ledger
    assert generation_records(state) == current
