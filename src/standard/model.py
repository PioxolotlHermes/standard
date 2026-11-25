"""Shared result types."""

from dataclasses import dataclass, field

Key = tuple[str, str, str]  # (rule, path, key)


@dataclass(frozen=True)
class Violation:
    """One rule violation. `key`/`value` identify and size it for the baseline ratchet."""

    rule: str
    path: str
    line: int
    message: str
    key: str = ""
    value: int = 1
    baselinable: bool = True

    def format(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{self.rule} {where} {self.message}"

    @property
    def group(self) -> Key:
        return (self.rule, self.path, self.key)


@dataclass
class Report:
    """Outcome of one check run."""

    errors: list[Violation] = field(default_factory=list)
    debt: int = 0
    budget: str = ""
