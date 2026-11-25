"""R7: new rule suppressions, new exceptions and baseline growth need a decision (tasks ask)."""

import json
import re
import subprocess
import tomllib
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from standard.baseline import BASELINE_FILE
from standard.files import CODE_EXT, GIT
from standard.model import Violation

# Character classes keep these patterns from matching their own source line.
MARKERS = {
    "noq[a]": re.compile(r"\bnoq[a]\b"),
    "type: ignor[e]": re.compile(r"type:\s*ignor[e]"),
    "eslint-disabl[e]": re.compile(r"eslint-disabl[e]"),
    "ts-ignor[e]": re.compile(r"ts-ignor[e]"),
    "@ts-expect-erro[r]": re.compile(r"@ts-expect-erro[r]"),
    "pytest.mark.ski[p]": re.compile(r"pytest\.mark\.ski[p]"),
    ".ski[p](": re.compile(r"\.ski[p]\("),
    ".onl[y](": re.compile(r"\.onl[y]\("),
}
HUNK = re.compile(r"^@@ -\S+ \+(\d+)")
DECISION = "needs Piotrek's decision (tasks ask)"


class DiffError(Exception):
    """git could not produce the diff."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([GIT, "-C", str(root), *args], check=False, capture_output=True, text=True)


def added_lines(root: Path, base: str) -> Iterator[tuple[str, int, str]]:
    """(path, line number, text) for every line added since `base` (working tree included)."""
    proc = _git(root, "diff", "-U0", "--no-color", "--no-ext-diff", base, "--")
    if proc.returncode != 0:
        raise DiffError(f"git diff against {base} failed: {proc.stderr.strip()}")
    path, number = "", 0
    for line in proc.stdout.splitlines():
        hunk = HUNK.match(line)
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif hunk:
            number = int(hunk.group(1))
        elif line.startswith("+") and path:
            yield path, number, line[1:]
            number += 1


def _marker_violations(root: Path, base: str) -> list[Violation]:
    out = []
    for path, number, text in added_lines(root, base):
        if PurePosixPath(path).suffix not in CODE_EXT:
            continue
        for label, pattern in MARKERS.items():
            if pattern.search(text):
                out.append(Violation("R7", path, number, f"added `{label}`: {DECISION}", baselinable=False))
    return out


def _show(root: Path, base: str, rel: str) -> str | None:
    proc = _git(root, "show", f"{base}:{rel}")
    return proc.stdout if proc.returncode == 0 else None


def _exception_keys(text: str) -> set[tuple[str, str]]:
    items = tomllib.loads(text).get("exceptions", [])
    return {(str(i.get("path")), str(i.get("rule"))) for i in items}


def _exception_violations(root: Path, base: str, config_rel: str) -> list[Violation]:
    old, new = _show(root, base, config_rel), root / config_rel
    if old is None or not new.is_file():
        return []  # adoption commit: nothing to compare against
    added = _exception_keys(new.read_text(encoding="utf-8")) - _exception_keys(old)
    return [Violation("R7", config_rel, 0, f"new exception {r} {p}: {DECISION}", baselinable=False) for p, r in added]


def _baseline_rows(text: str) -> dict[tuple[str, str, str], int]:
    return {(e["rule"], e["path"], e["key"]): int(e["value"]) for e in json.loads(text)}


def _baseline_violations(root: Path, base: str) -> list[Violation]:
    old, new = _show(root, base, BASELINE_FILE), root / BASELINE_FILE
    if old is None or not new.is_file():
        return []
    before = _baseline_rows(old)
    grown = [k for k, v in _baseline_rows(new.read_text(encoding="utf-8")).items() if v > before.get(k, 0)]
    return [
        Violation("R7", BASELINE_FILE, 0, f"baseline grew for {r} {p}: {DECISION}", baselinable=False)
        for r, p, _ in grown
    ]


def check_diff(root: Path, base: str, config_rel: str | None) -> list[Violation]:
    try:
        out = _marker_violations(root, base)
    except DiffError as exc:
        return [Violation("R7", "(diff)", 0, str(exc), baselinable=False)]
    if config_rel:
        out += _exception_violations(root, base, config_rel)
    return out + _baseline_violations(root, base)
