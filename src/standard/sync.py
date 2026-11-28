"""Shipped configs and `standard sync`."""

import json
from importlib import resources
from pathlib import Path, PurePosixPath

from standard.config import Config
from standard.overrides import Limits

TYPESCRIPT_PACKAGES = ("typescript", "typescript-eslint")


def shipped_text(name: str) -> str:
    return (resources.files("standard") / "configs" / name).read_text(encoding="utf-8")


def rendered_text(name: str, limits: Limits) -> str:
    """Shipped config with the repo's effective R2/R3/R4 limits (ruff and ESLint enforce them, not the checker)."""
    text = shipped_text(name)
    swaps = [
        ("max-complexity = 12", f"max-complexity = {limits.complexity}"),
        ("complexity: ['error', 12]", f"complexity: ['error', {limits.complexity}]"),
        ("max-lines': ['error', { max: 200,", f"max-lines': ['error', {{ max: {limits.code_lines},"),
        (
            "max-lines-per-function': ['error', { max: 50,",
            f"max-lines-per-function': ['error', {{ max: {limits.function_lines},",
        ),
        ("max-lines': ['error', { max: 300,", f"max-lines': ['error', {{ max: {limits.test_lines},"),
    ]
    for old, new in swaps:
        text = text.replace(old, new)
    return text


def eslint_variant(root: Path, front: str) -> str:
    """Shipped ESLint config for a front dir: the TypeScript one when package.json lists typescript, else plain JS."""
    try:
        data = json.loads((root / front / "package.json").read_text(encoding="utf-8"))
    except OSError, ValueError:
        return "eslint.standard.js"
    names = {name for key in ("dependencies", "devDependencies") for name in data.get(key, {})}
    return "eslint.standard.js" if names & set(TYPESCRIPT_PACKAGES) else "eslint.standard.plain.js"


def targets(root: Path, files: list[str], cfg: Config) -> dict[str, str]:
    """Repo-relative destination -> shipped file name."""
    out = {}
    for rel in files:
        path = PurePosixPath(rel)
        if path.name == "pyproject.toml":
            out[str(path.with_name("ruff.standard.toml"))] = "ruff.standard.toml"
    for front in cfg.front_dirs:
        out[f"{front}/eslint.standard.js"] = eslint_variant(root, front)
    return out


def ensure_gitignore(root: Path) -> bool:
    """Add `.security/` (scanner reports) to .gitignore so a clean `git status` stays clean; True when changed."""
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if any(line.strip().rstrip("/").lstrip("/") == ".security" for line in text.splitlines()):
        return False
    path.write_text(text + ("" if not text or text.endswith("\n") else "\n") + ".security/\n", encoding="utf-8")
    return True


def sync(root: Path, files: list[str], cfg: Config) -> list[str]:
    """Copy the shipped configs into the repo; returns the paths that changed."""
    changed = []
    for rel, name in sorted(targets(root, files, cfg).items()):
        dest, text = root / rel, rendered_text(name, cfg.limits)
        if not dest.is_file() or dest.read_text(encoding="utf-8") != text:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            changed.append(rel)
    if ensure_gitignore(root):
        changed.append(".gitignore")
    return changed
