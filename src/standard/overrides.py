"""Per-repo threshold overrides (`[overrides.<rule>]` in standard.toml) and the effective limits."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

DEFAULT_RATIO = 1.0
# rule -> {key: (Limits field, integer-only)}
KNOWN: dict[str, dict[str, tuple[str, bool]]] = {
    "R2": {"file_lines": ("code_lines", True), "test_file_lines": ("test_lines", True)},
    "R3": {"function_lines": ("function_lines", True)},
    "R4": {"complexity": ("complexity", True)},
    "R6": {"test_code_ratio": ("test_code_ratio", False)},
}


class OverrideError(ValueError):
    """An `[overrides]` section is invalid."""


@dataclass(frozen=True)
class Limits:
    """Every threshold the checker (and the rendered ruff/ESLint configs) applies."""

    code_lines: int = 200  # R2
    test_lines: int = 300  # R2
    function_lines: int = 50  # R3
    complexity: int = 12  # R4
    test_code_ratio: float = DEFAULT_RATIO  # R6


@dataclass(frozen=True)
class Override:
    rule: str
    key: str
    value: float
    reason: str
    adr: str

    def describe(self) -> str:
        return f"override {self.rule} {self.key}={self.value:g} ({self.adr})"


def _number(rule: str, key: str, value: object, integer: bool) -> float:
    kind = "positive integer" if integer else "positive number"
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise OverrideError(f"overrides.{rule}.{key} must be a {kind}, got {value!r}")
    if integer and value != int(value):
        raise OverrideError(f"overrides.{rule}.{key} must be a {kind}, got {value!r}")
    return float(value)


def _text(rule: str, table: dict[str, object], field: str) -> str:
    value = table.get(field)
    if not isinstance(value, str) or not value.strip():
        raise OverrideError(f"overrides.{rule} needs a non-empty {field}")
    return value.strip()


def parse_overrides(section: object) -> tuple[Override, ...]:
    """Validate the `[overrides]` table; raises OverrideError on anything unknown or incomplete."""
    if section is None:
        return ()
    if not isinstance(section, dict):
        raise OverrideError("[overrides] must be a table of [overrides.<rule>] tables")
    out = []
    for rule, table in section.items():
        if rule not in KNOWN:
            raise OverrideError(f"overrides.{rule}: unknown rule (known: {', '.join(KNOWN)})")
        if not isinstance(table, dict):
            raise OverrideError(f"overrides.{rule} must be a table")
        reason, adr = _text(rule, table, "reason"), _text(rule, table, "adr")
        keys = [k for k in table if k not in {"reason", "adr"}]
        if not keys:
            raise OverrideError(f"overrides.{rule} sets no threshold (known: {', '.join(KNOWN[rule])})")
        for key in keys:
            if key not in KNOWN[rule]:
                raise OverrideError(f"overrides.{rule}.{key}: unknown key (known: {', '.join(KNOWN[rule])})")
            number = _number(rule, key, table[key], KNOWN[rule][key][1])
            out.append(Override(rule, key, int(number) if KNOWN[rule][key][1] else number, reason, adr))
    return tuple(out)


def effective_limits(overrides: tuple[Override, ...]) -> Limits:
    changes: dict[str, Any] = {KNOWN[i.rule][i.key][0]: i.value for i in overrides}
    limits = replace(Limits(), **changes)
    return limits


def missing_adrs(root: Path, overrides: tuple[Override, ...]) -> list[Override]:
    """Overrides whose ADR file does not exist in the repo."""
    return [item for item in overrides if not (root / item.adr).is_file()]
