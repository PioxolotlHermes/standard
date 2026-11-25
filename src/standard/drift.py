"""R8 (shared tooling) and R9 (library catalog) checks on manifests and config files."""

import tomllib
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from standard.config import Config
from standard.manifests import Dep, npm_deps, python_deps
from standard.model import Violation
from standard.sync import shipped_text, targets

ESLINT_CONFIGS = ("eslint.config.js", "eslint.config.mjs", "eslint.config.ts")


def _fixed(rule: str, path: str, message: str) -> Violation:
    return Violation(rule, path, 0, message, baselinable=False)


def _adoption(rule: str, path: str, message: str, key: str) -> Violation:
    """Tool not adopted yet (mypy strict, ruff extend, shared ESLint import): baselinable debt."""
    return Violation(rule, path, 0, message, key=key)


def _read(root: Path, rel: str) -> str | None:
    path = root / rel
    return path.read_text(encoding="utf-8") if path.is_file() else None


def check_shipped_copies(root: Path, files: list[str], cfg: Config) -> list[Violation]:
    out = []
    for rel, name in sorted(targets(files, cfg).items()):
        actual = _read(root, rel)
        if actual is None:
            out.append(_fixed("R8", rel, f"missing; run `standard sync` ({name})"))
        elif actual != shipped_text(name):
            out.append(_fixed("R8", rel, f"differs from the shipped {name}; run `standard sync`, never edit it"))
    return out


def check_pyproject(root: Path, files: list[str]) -> list[Violation]:
    out = []
    for rel in (f for f in files if PurePosixPath(f).name == "pyproject.toml"):
        try:
            data = tomllib.loads(_read(root, rel) or "")
        except tomllib.TOMLDecodeError:
            continue
        tool = data.get("tool", {})
        if tool.get("ruff", {}).get("extend") != "ruff.standard.toml":
            msg = '[tool.ruff] must set extend = "ruff.standard.toml"'
            out.append(_adoption("R8", rel, msg, "ruff-extend"))
        if tool.get("mypy", {}).get("strict") is not True:
            out.append(_adoption("R8", rel, "[tool.mypy] must set strict = true", "mypy-strict"))
    return out


def check_front_config(root: Path, cfg: Config) -> list[Violation]:
    out = []
    for front in cfg.front_dirs:
        texts = [_read(root, f"{front}/{name}") for name in ESLINT_CONFIGS]
        if not any(text and "eslint.standard" in text for text in texts):
            msg = "must import ./eslint.standard.js"
            out.append(_adoption("R8", f"{front}/eslint.config.js", msg, "eslint-standard"))
    return out


def _allowed(name: str, patterns: list[str]) -> bool:
    return any(fnmatchcase(name, p) for p in patterns)


def check_dependencies(root: Path, files: list[str]) -> list[Violation]:
    catalog = tomllib.loads(shipped_text("catalog.toml"))
    out = []
    for rel in files:
        kind = PurePosixPath(rel).name
        if kind not in {"pyproject.toml", "package.json"}:
            continue
        py, text = kind == "pyproject.toml", _read(root, rel) or ""
        deps = python_deps(text) if py else npm_deps(text)
        lists = catalog["python" if py else "npm"]
        for dep in deps:
            out += _dependency_violations(rel, dep, lists)
    return out


def _dependency_violations(rel: str, dep: Dep, lists: dict[str, list[str]]) -> list[Violation]:
    out = []
    pool = lists["runtime"] if dep.runtime else lists["runtime"] + lists["dev"]
    if not _allowed(dep.name, pool):
        msg = f"{dep.name} is not in the library catalog (catalog.toml); needs Piotrek's decision (tasks ask)"
        out.append(Violation("R9", rel, 0, msg, key=dep.name))
    if not dep.runtime and not dep.pinned:
        out.append(Violation("R8", rel, 0, f"dev tool {dep.name} must be pinned exactly", key=f"pin:{dep.name}"))
    return out


def check_drift(root: Path, files: list[str], cfg: Config) -> list[Violation]:
    return (
        check_shipped_copies(root, files, cfg)
        + check_pyproject(root, files)
        + check_front_config(root, cfg)
        + check_dependencies(root, files)
    )
