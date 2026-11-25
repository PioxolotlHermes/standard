"""Discovering and classifying the files of a checked repo."""

import ast
import itertools
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CODE_EXT = frozenset({".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".svelte"})
SKIP_DIRS = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".svelte-kit", "build", "dist", ".mypy_cache"}
    | {".ruff_cache", ".pytest_cache", "test-results", "playwright-report", ".tox"}
)
GENERATED = ("# generated", "// generated")
GIT = shutil.which("git") or "git"


@dataclass(frozen=True)
class Source:
    rel: str
    text: str
    lines: tuple[str, ...]
    is_test: bool
    counted: bool  # hand-written: not generated and not an Alembic migration version

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.rel).suffix


def is_test_path(rel: str) -> bool:
    path = PurePosixPath(rel)
    name = path.name
    if "tests" in path.parts[:-1] or any(part.startswith("e2e") for part in path.parts[:-1]):
        return True
    if name.endswith((".test.ts", ".spec.ts", ".test.js", ".spec.js", ".test.tsx", ".spec.tsx")):
        return True
    return name.startswith("test_") and name.endswith(".py")


def _matches(rel: str, globs: tuple[str, ...]) -> bool:
    return any(PurePosixPath(rel).full_match(g) for g in globs)


def _is_migration(rel: str) -> bool:
    parts = PurePosixPath(rel).parts
    return any(a == "migrations" and b == "versions" for a, b in itertools.pairwise(parts))


def _git_files(root: Path) -> list[str] | None:
    cmd = [GIT, "-C", str(root), "rev-parse", "--show-toplevel"]
    top = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root.resolve():
        return None
    listing = subprocess.run(
        [GIT, "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [name for name in listing.stdout.split("\0") if name]


def _walk_files(root: Path) -> list[str]:
    found: list[str] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        found += [(Path(current) / n).relative_to(root).as_posix() for n in names]
    return found


def list_files(root: Path) -> list[str]:
    """Repo-relative posix paths of regular files (git view when root is a repo, else a directory walk)."""
    names = _git_files(root)
    if names is None:
        names = _walk_files(root)
    kept = [n for n in names if not SKIP_DIRS.intersection(PurePosixPath(n).parts[:-1])]
    kept = [n for n in kept if (root / n).is_file() and not (root / n).is_symlink()]
    return sorted(kept)


def load_sources(root: Path, files: list[str], test_globs: tuple[str, ...] = ()) -> list[Source]:
    sources = []
    for rel in files:
        if PurePosixPath(rel).suffix not in CODE_EXT:
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        lines = tuple(text.splitlines())
        generated = bool(lines) and lines[0].strip() in GENERATED
        counted = not generated and not _is_migration(rel)
        sources.append(Source(rel, text, lines, is_test_path(rel) or _matches(rel, test_globs), counted))
    return sources


def parse_python(source: Source) -> ast.Module | None:
    try:
        return ast.parse(source.text, filename=source.rel)
    except SyntaxError, ValueError:
        return None
