"""Runs every rule and applies exceptions, the baseline and the diff guard."""

from pathlib import Path, PurePosixPath

from standard import baseline
from standard.config import Config, load_config
from standard.defect_rule import check_budget, check_defects
from standard.diff_guard import check_diff
from standard.files import list_files, load_sources
from standard.model import Report, Violation
from standard.r1_imports import check_imports
from standard.size_rules import check_file_sizes, check_function_sizes
from standard.text_rule import check_polish

CONFIG_FILE = "standard.toml"


def config_problems(root: Path, cfg: Config, name: str) -> list[Violation]:
    out = []
    for module, adr in cfg.core:
        if not adr or not (root / adr).exists():
            out.append(
                Violation(
                    "CONFIG", name, 0, f"core module {module} needs an existing ADR (adr = ...)", baselinable=False
                )
            )
    for item in cfg.exemptions:
        if not item.reason:
            msg = f"exception {item.rule} {item.path} has no reason"
            out.append(Violation("CONFIG", name, 0, msg, baselinable=False))
    return out


def _suppressed(violation: Violation, cfg: Config) -> bool:
    for item in cfg.exemptions:
        if item.reason and item.rule == violation.rule and PurePosixPath(violation.path).full_match(item.path):
            return True
    return False


def analyze(root: Path, cfg: Config, name: str = CONFIG_FILE) -> tuple[list[Violation], str]:
    """All violations after exceptions (before the baseline), plus the R6 budget line."""
    files = list_files(root)
    sources = load_sources(root, files)
    budget_violations, budget = check_budget(sources)
    found = (
        check_imports(sources, cfg)
        + check_file_sizes(sources)
        + check_function_sizes(sources)
        + check_polish(sources, cfg.texts)
        + check_defects(sources)
        + budget_violations
        + config_problems(root, cfg, name)
    )
    return [v for v in found if not _suppressed(v, cfg)], budget


def run_check(root: Path, config_path: Path | None = None, base: str | None = None) -> Report:
    config_path = config_path or root / CONFIG_FILE
    cfg = load_config(config_path)
    found, budget = analyze(root, cfg, config_path.name)
    errors, debt = baseline.apply(found, baseline.load(root))
    if base:
        inside = config_path.resolve().is_relative_to(root.resolve())
        rel = config_path.resolve().relative_to(root.resolve()).as_posix() if inside else None
        errors += check_diff(root, base, rel)
    errors.sort(key=lambda v: (v.rule, v.path, v.line))
    return Report(errors, debt, budget)
