"""Bounded complete JUnit identities; no test outcome grants gate authority."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import xml.etree.ElementTree as ET

PREFIX = "pytest-junit-sha256:"
MAX_CASES = 10000
MAX_XML = 4 * 1024 * 1024
MAX_RESPONSE = 1024 * 1024


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def not_applicable():
    return {"schema_version": 1, "kind": "not_applicable"}


class _NoDoctypeTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, public_id, system_id):
        raise ValueError("test_identity_artifact_unavailable")


def _document(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        item = os.fstat(stream.fileno())
        if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid()
                or item.st_nlink != 1 or item.st_size > MAX_XML):
            raise ValueError("test_identity_artifact_unavailable")
        raw = stream.read(MAX_XML + 1)
    if len(raw) > MAX_XML or b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        raise ValueError("test_identity_artifact_unavailable")
    try:
        document = ET.fromstring(raw, parser=ET.XMLParser(target=_NoDoctypeTreeBuilder()))
    except ET.ParseError:
        raise ValueError("test_identity_artifact_unavailable") from None
    if document.tag not in {"testsuite", "testsuites"}:
        raise ValueError("test_identity_artifact_unavailable")
    return document


def collect_junit(path, selected):
    """Represent every retained case exactly once, or return no partial receipt."""
    if (not isinstance(selected, list) or not selected
            or any(not isinstance(value, str) or not value.endswith(".py") for value in selected)
            or len(selected) != len(set(selected))):
        raise ValueError("test_identity_mapping_unavailable")
    modules = {value: value[:-3].replace("/", ".") for value in selected}
    identities, failed, logical_seen, encoded_seen = [], [], set(), set()
    outcomes = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for case in _document(Path(path)).iter("testcase"):
        if len(identities) >= MAX_CASES:
            raise ValueError("test_identity_capacity_unavailable")
        name, classname, file = case.get("name", ""), case.get("classname", ""), case.get("file", "")
        tags = [child.tag for child in case if child.tag in {"failure", "error", "skipped"}]
        if len(tags) > 1 or not name:
            raise ValueError("test_identity_mapping_unavailable")
        outcome = {"failure": "failed"}.get(tags[0], tags[0]) if tags else "passed"
        kind = "testcase"
        if not file:
            matches = [value for value, module in modules.items()
                       if classname == module or classname.startswith(module + ".")]
            if not classname and outcome == "skipped":
                matches = [value for value, module in modules.items() if name == module]
                kind = "module_skip"
            if len(matches) != 1:
                raise ValueError("test_identity_mapping_unavailable")
            file = matches[0]
        if file not in modules:
            raise ValueError("test_identity_mapping_unavailable")
        module = modules[file]
        if classname and classname != module and not classname.startswith(module + "."):
            raise ValueError("test_identity_mapping_unavailable")
        logical = {"version": 1, "kind": kind, "file": file, "classname": classname, "name": name}
        logical_digest = hashlib.sha256(canonical(logical)).hexdigest()
        if logical_digest in logical_seen:
            raise ValueError("test_identity_duplicate_unavailable")
        logical_seen.add(logical_digest)
        classes = classname[len(module):].strip(".").replace(".", "::") if classname else ""
        identity = "::".join(part for part in (file, classes, name) if part)
        if (len(identity) > 512 or not all(32 <= ord(char) < 127 for char in identity)
                or identity.startswith(PREFIX)):
            identity = PREFIX + logical_digest
        if identity in encoded_seen:
            raise ValueError("test_identity_duplicate_unavailable")
        encoded_seen.add(identity)
        identities.append(identity)
        outcomes[outcome] += 1
        if outcome in {"failed", "error"}:
            failed.append(identity)
    if not identities:
        raise ValueError("test_identity_empty_unavailable")
    identities.sort()
    receipt = {"schema_version": 1, "kind": "pytest-junit-v1",
               "encoding": "pytest-nodeid-or-sha256-v1", "scope": "completed", "complete": True,
               "case_count": len(identities), "reported_count": len(identities), "outcomes": outcomes,
               "opaque_count": sum(value.startswith(PREFIX) for value in identities), "omitted_count": 0,
               "ids_digest": hashlib.sha256(canonical(identities)).hexdigest(),
               "failed_test_ids": sorted(failed)}
    validate_receipt(receipt, identities)
    return identities, receipt


def validate_receipt(value, identities, declared=None):
    """Validate new evidence. Missing legacy evidence is handled by its reader."""
    if (not isinstance(value, dict) or not isinstance(identities, list)
            or type(value.get("schema_version")) is not int or value["schema_version"] != 1):
        raise ValueError("test_identity_receipt_invalid")
    if value.get("kind") == "not_applicable":
        if value != not_applicable() or identities or declared not in {None, "not_applicable"}:
            raise ValueError("test_identity_receipt_invalid")
        return value
    required = {"schema_version", "kind", "encoding", "scope", "complete", "case_count",
                "reported_count", "outcomes", "opaque_count", "omitted_count", "ids_digest", "failed_test_ids"}
    if (set(value) != required or value["kind"] != "pytest-junit-v1"
            or declared not in {None, "pytest-junit-v1"}
            or value["encoding"] != "pytest-nodeid-or-sha256-v1"
            or value["scope"] != "completed" or value["complete"] is not True):
        raise ValueError("test_identity_receipt_invalid")
    if (not isinstance(identities, list) or not 1 <= len(identities) <= MAX_CASES
            or any(not isinstance(item, str) or not 0 < len(item) <= 512
                   or not all(32 <= ord(char) < 127 for char in item)
                   or item.startswith(PREFIX) and re.fullmatch(re.escape(PREFIX) + r"[0-9a-f]{64}", item) is None
                   for item in identities)
            or identities != sorted(set(identities))):
        raise ValueError("test_identity_receipt_invalid")
    if any(type(value[name]) is not int or value[name] < 0
           for name in ("case_count", "reported_count", "opaque_count", "omitted_count")):
        raise ValueError("test_identity_receipt_invalid")
    outcomes = value["outcomes"]
    if (not isinstance(outcomes, dict) or set(outcomes) != {"passed", "failed", "error", "skipped"}
            or any(type(count) is not int or count < 0 for count in outcomes.values())
            or value["case_count"] != len(identities) or value["reported_count"] != len(identities)
            or sum(outcomes.values()) != len(identities) or value["omitted_count"] != 0
            or value["opaque_count"] != sum(item.startswith(PREFIX) for item in identities)
            or value["ids_digest"] != hashlib.sha256(canonical(identities)).hexdigest()):
        raise ValueError("test_identity_receipt_invalid")
    failed = value["failed_test_ids"]
    if (not isinstance(failed, list) or any(not isinstance(item, str) for item in failed)
            or failed != sorted(set(failed)) or not set(failed) <= set(identities)
            or len(failed) != outcomes["failed"] + outcomes["error"]):
        raise ValueError("test_identity_receipt_invalid")
    if len(canonical({"test_ids": identities, "test_identity": value})) > MAX_RESPONSE:
        raise ValueError("test_identity_capacity_unavailable")
    return value
