"""Baseline ratchet: known debt may only shrink."""

import json
from pathlib import Path

from standard.model import Key, Violation

BASELINE_FILE = "standard-baseline.json"
SUMMED_RULES = {"R1", "R5", "R6"}  # count-like; size rules (R2, R3) use the maximum


def group(violations: list[Violation]) -> dict[Key, list[Violation]]:
    groups: dict[Key, list[Violation]] = {}
    for v in violations:
        if v.baselinable:
            groups.setdefault(v.group, []).append(v)
    return groups


def total(items: list[Violation]) -> int:
    values = [v.value for v in items]
    return sum(values) if items[0].rule in SUMMED_RULES else max(values)


def totals(violations: list[Violation]) -> dict[Key, int]:
    return {key: total(items) for key, items in group(violations).items()}


def load(root: Path) -> dict[Key, int]:
    path = root / BASELINE_FILE
    if not path.is_file():
        return {}
    return {(e["rule"], e["path"], e["key"]): int(e["value"]) for e in json.loads(path.read_text(encoding="utf-8"))}


def write(root: Path, entries: dict[Key, int]) -> None:
    rows = [{"rule": r, "path": p, "key": k, "value": v} for (r, p, k), v in sorted(entries.items())]
    (root / BASELINE_FILE).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def shrink(current: dict[Key, int], known: dict[Key, int]) -> dict[Key, int]:
    """Only entries that still fail, never above their recorded value; nothing new is added."""
    return {key: min(value, current[key]) for key, value in known.items() if key in current}


def apply(violations: list[Violation], known: dict[Key, int]) -> tuple[list[Violation], int]:
    """Split into (errors, debt count). Stale baseline entries become BASELINE errors."""
    errors = [v for v in violations if not v.baselinable]
    debt = 0
    groups = group(violations)
    for key, items in groups.items():
        allowed = known.get(key)
        if allowed is not None and total(items) <= allowed:
            debt += 1
        else:
            errors += items
    for (rule, path, entry_key), value in known.items():
        if (rule, path, entry_key) not in groups:
            msg = f"{rule} {entry_key or 'entry'} no longer fails (was {value}); run `standard baseline --shrink`"
            errors.append(Violation("BASELINE", path, 0, msg, baselinable=False))
    return errors, debt
