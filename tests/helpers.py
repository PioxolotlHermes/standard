"""Test helpers: build a throwaway repo on disk and run the checker against it."""

import shutil
import subprocess
from pathlib import Path

from standard.engine import run_check

GIT = shutil.which("git") or "git"

CONFIG = """[package]
roots = ["src/pkg"]

[modules]
shared = ["common"]
core = [{ name = "people", adr = "docs/adr/0001-core.md" }]
root = ["web"]
migrations = ["migrations"]
"""


def write_repo(root: Path, files: dict[str, str], config: str = CONFIG) -> Path:
    """Write `files` (plus standard.toml and the core ADR) under `root`."""
    everything = {"standard.toml": config, "docs/adr/0001-core.md": "# core\n", **files}
    for rel, text in everything.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def found(root: Path, base: str | None = None) -> set[str]:
    """Return `RULE path` for every error the checker reports."""
    report = run_check(root, base=base)
    return {f"{v.rule} {v.path}" for v in report.errors}


def git(root: Path, *args: str) -> None:
    subprocess.run([GIT, "-C", str(root), *args], check=True, capture_output=True)


def git_init(root: Path) -> None:
    git(root, "init", "-q", "-b", "master")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    commit(root)


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "x", "--allow-empty")


def lines(n: int, line: str = "x = 1") -> str:
    return (line + "\n") * n
