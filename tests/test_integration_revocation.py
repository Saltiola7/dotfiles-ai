"""Missing revocation links differ from damaged existing authority custody."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import lifecycle as l


@pytest.fixture
def grant_store(tmp_path: Path) -> tuple[l.Custody, str]:
    common = tmp_path / "common"; common.mkdir()
    store = l.Custody(common)
    identity = store.write("grant", {"obligation_digest": "1" * 64, "record_digest": "2" * 64,
        "context": "fixture", "risk": "routine", "scope_digest": "3" * 64,
        "profile_blob": "4" * 40, "plan_digest": "5" * 64, "policy_digest": "6" * 64,
        "enrollment_digest": "7" * 64, "approval_digest": "8" * 64,
        "allowed_operations": ["submit", "repair", "accept_outcome"],
        "authorized_at": "2026-11-13T00:00:00Z"})
    return store, identity


def test_absent_revocation_link_is_unrevoked_without_creating_files(grant_store: tuple[l.Custody, str]) -> None:
    store, identity = grant_store
    before = set(store.directory.rglob("*"))
    assert not store.revoked(identity)
    assert set(store.directory.rglob("*")) == before


def test_complete_revocation_link_remains_revoked(grant_store: tuple[l.Custody, str]) -> None:
    store, identity = grant_store
    store.revoke(identity, "9" * 64, "2026-11-13T01:00:00Z")
    assert store.revoked(identity)


def test_dangling_existing_revocation_is_unavailable_not_unrevoked(grant_store: tuple[l.Custody, str]) -> None:
    store, identity = grant_store
    store.revoke(identity, "9" * 64, "2026-11-13T01:00:00Z")
    value = store.linked("revocation", identity)
    revocation = store.write("revocation", value)
    store.object_path(revocation).unlink()
    assert (store.directory / "links/revocation" / (identity + ".json")).is_file()
    with pytest.raises(FileNotFoundError): store.revoked(identity)


def test_corrupt_existing_revocation_link_refuses(grant_store: tuple[l.Custody, str]) -> None:
    store, identity = grant_store
    store.revoke(identity, "9" * 64, "2026-11-13T01:00:00Z")
    link = store.directory / "links/revocation" / (identity + ".json")
    link.write_bytes(b'{"digest":false}')
    with pytest.raises(ValueError): store.revoked(identity)
