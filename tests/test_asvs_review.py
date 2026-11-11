"""ASVS reference fidelity, bounded loading and portable resource closure."""
import hashlib
import json
import re
from collections import Counter
from urllib.parse import unquote, urlsplit

from test_opencode_control_plane import ROOT

BUNDLE = ROOT / "dot_agents/skills/asvs-review"
STANDARD_COMMIT = "5cf9b032440be53ce345ab3c130fda46ba1ce7a2"
# Independently derived from all official 5.0/en chapter tables at this commit:
# sorted [requirement ID, integer level, exact requirement text], compact JSON.
STANDARD_SEMANTIC_SHA256 = "3d3def6aa57b918f6da23167969adc97ff303c18f0b923fe5c6034f2874919e1"
REQUIREMENT_ROW = re.compile(
    r"\|\s*\*\*(\d+\.\d+\.\d+)\*\*\s*\|\s*L([123])\s*\|\s*(.+?)\s*\|"
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")


def test_bundled_requirements_match_official_release():
    chapters = [BUNDLE / "reference" / f"V{number}.md" for number in range(1, 18)]
    assert set((BUNDLE / "reference").glob("V*.md")) == set(chapters)
    requirements: list[tuple[str, int, str]] = []
    for number, chapter in enumerate(chapters, 1):
        text = chapter.read_text()
        assert f"https://github.com/OWASP/ASVS/blob/{STANDARD_COMMIT}/5.0/en/" in text
        rows = [REQUIREMENT_ROW.fullmatch(line) for line in text.splitlines()]
        chapter_rows = [(row[1], int(row[2]), row[3]) for row in rows if row]
        assert chapter_rows
        assert all(row[0].split(".")[0] == str(number) for row in chapter_rows)
        requirements.extend(chapter_rows)
    assert len(requirements) == len({row[0] for row in requirements}) == 345
    assert Counter(row[1] for row in requirements) == {1: 70, 2: 183, 3: 92}
    requirements.sort(key=lambda row: tuple(map(int, row[0].split("."))))
    canonical = json.dumps(requirements, ensure_ascii=False, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == STANDARD_SEMANTIC_SHA256


def test_runtime_references_are_closed_and_progressively_reachable():
    root = BUNDLE.resolve()
    pending = [BUNDLE / "SKILL.md"]
    visited = set()
    while pending:
        document = pending.pop().resolve()
        if document in visited:
            continue
        assert document.is_relative_to(root), document
        assert document.is_file(), document
        visited.add(document)
        for destination in MARKDOWN_LINK.findall(document.read_text()):
            link = urlsplit(destination.strip("<>"))
            if link.scheme or link.netloc or not link.path:
                continue
            target = (document.parent / unquote(link.path)).resolve()
            assert target.is_relative_to(root), (document, destination)
            assert target.is_file(), (document, destination)
            if target.suffix == ".md":
                pending.append(target)
    expected = {BUNDLE / "references/workflow.md", BUNDLE / "reference/README.md"}
    expected.update(BUNDLE / "reference" / f"V{number}.md" for number in range(1, 18))
    assert {path.resolve() for path in expected} <= visited
    assert (BUNDLE / "SKILL.md").stat().st_size <= 6_000
    assert (BUNDLE / "references/workflow.md").stat().st_size <= 14_000


def test_complete_upstream_license_texts_are_preserved():
    expected = {
        "LICENSE.upstream": "b752c17f4ad5bd6d1598d782e19741b315f7276364f99b4016b2fabc3d93cb89",
        "LICENSE.asvs": "28a9529c7d0bb4dc51f4bf5c116a3d16ef247a052f7591466768ddf563fd1cf5",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest() == digest
