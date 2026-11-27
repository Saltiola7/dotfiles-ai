"""Optional Dagger refuses a missing, unreachable or mismatched engine without retry or substitution."""

import asyncio
import json

import pytest

from test_continuous_validation_dagger import job, backend  # noqa: F401 - shared fixtures


def test_engine_free_request_is_unconfigured_before_any_probe(backend, job, monkeypatch):
    del job["check"]["configuration"]["engine"]
    monkeypatch.setattr(backend, "_probe_cli", lambda: pytest.fail("an unconfigured engine must fail first"))
    monkeypatch.setattr(backend, "_load_sdk", lambda: pytest.fail("an unconfigured engine must not load the SDK"))
    result = asyncio.run(backend.execute(job, enabled=True))
    assert (result["status"], result["diagnostic_codes"]) == ("unavailable", ["dagger_engine_unconfigured"])


def test_unreachable_engine_is_unavailable_after_one_attempt(backend, job, monkeypatch):
    attempts = []

    class Unreachable(Exception):
        pass

    async def pipeline(sdk, config, snapshot, log_path, timeout, executable):
        attempts.append(config["engine"])
        raise Unreachable("PRIVATE_ENGINE_DETAIL")

    monkeypatch.setattr(backend, "_probe_cli", lambda: ("/fixture/dagger", backend.DAGGER_VERSION))
    monkeypatch.setattr(backend, "_load_sdk", lambda: object())
    monkeypatch.setattr(backend, "_pipeline", pipeline)
    result = asyncio.run(backend.execute(job, enabled=True))
    assert (result["status"], result["diagnostic_codes"]) == ("unavailable", ["dagger_engine_unavailable"])
    assert attempts == ["unix:///tmp/fixture-dagger.sock"]
    assert "PRIVATE" not in json.dumps(result) and not backend._SESSION_LOCK.locked()


@pytest.mark.parametrize("version", ["0.21.9", "v0.21.10", "0.22.0", None])
def test_mismatched_cli_identity_stops_before_the_engine_is_contacted(backend, job, monkeypatch, version):
    monkeypatch.setattr(backend, "_probe_cli", lambda: ("/fixture/dagger", version))
    monkeypatch.setattr(backend, "_load_sdk", lambda: pytest.fail("a mismatched CLI must not load the SDK"))
    monkeypatch.setattr(backend, "_pipeline", lambda *args: pytest.fail("a mismatched CLI must not connect"))
    result = asyncio.run(backend.execute(job, enabled=True))
    assert (result["status"], result["diagnostic_codes"]) == ("unavailable", ["dagger_cli_version_mismatch"])
