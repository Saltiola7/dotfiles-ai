"""Internal fail-fast probes for the credential-free OpenShell qualification.

This module is never installed. A probe result cannot qualify unperformed rows
of the runtime matrix. Preparation and retained-state retirement are separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class Refusal(Exception):
    """A stable, public-safe refusal reason without paths or command output."""


@dataclass(frozen=True)
class Selection:
    root: Path
    lima_sha256: str


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def parse_selection(raw: bytes) -> Selection:
    """Validate the closed private selection without executing commands."""
    raise NotImplementedError


def validate_root(selection: Selection) -> None:
    """Check private owner-controlled, alias-free prepared fixture ownership."""
    raise NotImplementedError


def run_command(argv: list[str], *, cwd: Path, env: dict[str, str],
                timeout: float = 60, limit: int = 1024 * 1024) -> CommandResult:
    """Bound owned child groups and both streams; retain nonzero exit status."""
    raise NotImplementedError


def pointer_probe(selection: Selection) -> dict:
    """Observe one fixed pointer-boundary experiment without claiming rollout."""
    raise NotImplementedError
