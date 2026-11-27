"""Verify the scoped wire and approval deadline for native Forgejo retries."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from test_initiative_forgejo import BASE, HEAD, TARGET, Fixture, custody, fixture_document
from test_integration_initiative_controller import digest
from integration_coordinator import core, initiative_ci as ci, initiative_controller as controller
from integration_coordinator import initiative_forgejo as auto, initiative_forgejo_bridge as module
from integration_coordinator import initiative_repair as repair, lifecycle


def expiry(seconds):
    return datetime.fromtimestamp(seconds, UTC).isoformat().replace("+00:00", "Z")


@pytest.fixture
def retry_bridge(custody, monkeypatch):
    program = b"# An inert owner; subprocess output is supplied by the test.\n"
    fixture = replace(auto.parse_fixture(fixture_document(Fixture())), bridge_digest=sha256(program).hexdigest())
    custody._write(custody.directory / "forgejo-fixture-provider.py", program)
    bridge = module.Bridge(custody, fixture)
    target = controller.Target(fixture.binding.origin, fixture.binding.repository, TARGET)
    approval = controller.Approval(digest(1), target, digest(2), digest(3), (controller.Slice("slice-a"),))
    launch = controller.Launch(digest(4), BASE, str(custody.common.parent), "LOCAL-A", "build")
    activation = controller.Activation.from_launch(approval, "slice-a", launch, managed=True)
    candidate = ci.Candidate(1, BASE, HEAD, HEAD, digest(5))
    failure = repair.Failure(digest(6), digest(7), candidate, digest(8), digest(9), digest(10), digest(11), 1)
    correction = repair.Correction(repair.INFRASTRUCTURE, digest(12))
    request = repair.Request(activation.grant_id, activation.activation_id, activation.slice_id,
                             failure, correction, digest(13))
    owner = SimpleNamespace(now=1000.25, read_seconds=0, response_seconds=0, calls=[], results={})
    read = custody._read

    def delayed_read(path):
        raw = read(path)
        owner.now += owner.read_seconds
        return raw

    def run(argv, *, input, timeout, stdout, cwd, **kwargs):
        call = json.loads(input)
        assert argv[1:3] == ["-I", "-B"]
        assert cwd == custody.directory
        assert kwargs["check"] is False
        owner.calls.append((call, timeout))
        owner.now += owner.response_seconds
        stdout.write(lifecycle.canonical({
            "schema_version": 1, "fixture_digest": fixture.digest,
            "result": owner.results.get(call["operation"]),
        }))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(custody, "_read", delayed_read)
    monkeypatch.setattr(module, "datetime", SimpleNamespace(now=lambda zone: datetime.fromtimestamp(owner.now, zone)))
    monkeypatch.setattr(module.subprocess, "run", run)
    return bridge, approval, activation, request, owner


def test_retry_operations_bind_exact_native_request_and_expiry(retry_bridge):
    bridge, _, activation, request, owner = retry_bridge
    owner.results.update(retry_qualification=request.qualification_digest,
                         retry_correction=request.correction.proof_digest,
                         retry_verify=True, retry_submit={"receipt_digest": digest(14)})
    expires_at = expiry(1300)

    assert bridge.retry_qualification() == request.qualification_digest
    assert bridge.retry_correction(activation, request.failure) == request.correction.proof_digest
    assert bridge.retry_verify(activation, request) is True
    assert bridge.retry_submit(activation, request, expires_at) == {"receipt_digest": digest(14)}
    owner.now = 1400
    assert bridge.retry_readback(activation, request) is None

    scope = {"activation_id": activation.activation_id, "grant_id": activation.grant_id, "slice_id": "slice-a"}
    fields = {**scope, "request": json.loads(lifecycle.canonical(asdict(request))),
              "request_digest": core.identity(request)}
    binding = {"schema_version": 1, "fixture_digest": bridge.fixture.digest, "binding": asdict(bridge.binding),
               "target_ref": bridge.fixture.target_ref}
    assert owner.calls == [
        ({**binding, "operation": operation, "request": payload}, 25)
        for operation, payload in (
            ("retry_qualification", {}),
            ("retry_correction", {**scope, "failure": asdict(request.failure)}),
            ("retry_verify", fields),
            ("retry_submit", {**fields, "expires_at": expires_at}),
            ("retry_readback", fields),
        )
    ]


def test_retry_submit_uses_only_approval_time_remaining_after_local_setup(retry_bridge):
    bridge, _, activation, request, owner = retry_bridge
    owner.read_seconds = 1.5

    assert bridge.retry_submit(activation, request, expiry(1004)) is None
    assert [timeout for _, timeout in owner.calls] == [2.25]


@pytest.mark.parametrize(("approval_expiry", "setup_seconds"), [(1000, 0), (1002, 1.75)])
def test_retry_submit_never_starts_when_approval_expired(retry_bridge, approval_expiry, setup_seconds):
    bridge, _, activation, request, owner = retry_bridge
    owner.read_seconds = setup_seconds

    with pytest.raises(core.Unavailable, match="bridge_approval_expired"):
        bridge.retry_submit(activation, request, expiry(approval_expiry))
    assert owner.calls == []


def test_retry_submit_cannot_use_reply_received_after_expiry(retry_bridge):
    bridge, _, activation, request, owner = retry_bridge
    owner.response_seconds = 1.75
    owner.results["retry_submit"] = {"receipt_digest": digest(14)}

    with pytest.raises(core.Unavailable, match="bridge_approval_expired"):
        bridge.retry_submit(activation, request, expiry(1002))
    assert [timeout for _, timeout in owner.calls] == [1.75]


def test_retry_scope_drift_or_wrong_repair_class_never_reaches_owner(retry_bridge):
    bridge, approval, activation, request, owner = retry_bridge
    elsewhere = replace(approval, target=replace(approval.target, repository="other/project"))
    wrong_target = controller.Activation.from_launch(elsewhere, activation.slice_id, activation.launch, managed=True)
    with pytest.raises(core.Conflict, match="retry_target_changed"):
        bridge.retry_correction(wrong_target, request.failure)
    for changed in (replace(request, activation_id=digest(40)), replace(request, grant_id=digest(41)),
                    replace(request, slice_id="slice-b"),
                    replace(request, correction=repair.Correction(repair.SOURCE, digest(42), ("src/main.py",)))):
        with pytest.raises(core.Conflict, match="retry_request_unbound"):
            bridge.retry_verify(activation, changed)
    assert owner.calls == []


def test_retry_verify_requires_actual_boolean_proof(retry_bridge):
    bridge, _, activation, request, owner = retry_bridge
    owner.results["retry_verify"] = False
    assert bridge.retry_verify(activation, request) is False
    owner.results["retry_verify"] = 1
    with pytest.raises(core.Invalid, match="retry_verification_unproved"):
        bridge.retry_verify(activation, request)
