"""Loading `standard.toml`."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from standard.overrides import Limits, Override, OverrideError, effective_limits, parse_overrides


class ConfigError(Exception):
    """The configuration file is missing or malformed."""


@dataclass(frozen=True)
class Exemption:
    path: str
    rule: str
    reason: str


@dataclass(frozen=True)
class Config:
    roots: tuple[str, ...] = ()
    shared: frozenset[str] = frozenset()
    core: tuple[tuple[str, str], ...] = ()  # (module, adr path)
    root: frozenset[str] = frozenset()
    migrations: frozenset[str] = frozenset()
    texts: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()  # extra globs counted as tests (e.g. test-support dirs)
    front_dirs: tuple[str, ...] = ()
    exemptions: tuple[Exemption, ...] = ()
    format: bool = False  # [tool.standard] format = true: the repo is formatted, `ruff format --check` is enforced
    overrides: tuple[Override, ...] = ()  # [overrides.<rule>]: per-repo thresholds, each with reason + ADR

    @property
    def limits(self) -> Limits:
        return effective_limits(self.overrides)

    def role(self, module: str) -> str:
        """Role of a top-level module directory: shared, core, root, migrations or module."""
        if module in self.shared:
            return "shared"
        if module in {name for name, _ in self.core}:
            return "core"
        if module in self.root:
            return "root"
        if module in self.migrations:
            return "migrations"
        return "module"


def _strings(value: object) -> tuple[str, ...]:
    return tuple(str(item) for item in value) if isinstance(value, list) else ()


def _core(value: object) -> tuple[tuple[str, str], ...]:
    items = value if isinstance(value, list) else []
    return tuple((str(i.get("name", "")), str(i.get("adr", ""))) for i in items if isinstance(i, dict))


def parse_config(text: str) -> Config:
    """Parse the text of a standard.toml."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML: {exc}") from exc
    modules = data.get("modules", {})
    try:
        overrides = parse_overrides(data.get("overrides"))
    except OverrideError as exc:
        raise ConfigError(str(exc)) from exc
    exemptions = tuple(
        Exemption(str(e.get("path", "")), str(e.get("rule", "")), str(e.get("reason", "")).strip())
        for e in data.get("exceptions", [])
        if isinstance(e, dict)
    )
    return Config(
        roots=_strings(data.get("package", {}).get("roots")),
        shared=frozenset(_strings(modules.get("shared"))),
        core=_core(modules.get("core")),
        root=frozenset(_strings(modules.get("root"))),
        migrations=frozenset(_strings(modules.get("migrations"))),
        texts=_strings(data.get("texts", {}).get("globs")),
        tests=_strings(data.get("tests", {}).get("globs")),
        front_dirs=_strings(data.get("front", {}).get("dirs")),
        exemptions=exemptions,
        format=data.get("tool", {}).get("standard", {}).get("format") is True,
        overrides=overrides,
    )


def load_config(path: Path) -> Config:
    if not path.is_file():
        raise ConfigError(f"{path} not found (run `standard init`)")
    return parse_config(path.read_text(encoding="utf-8"))
