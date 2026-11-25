"""Shipped configs and `standard sync`."""

from importlib import resources
from pathlib import Path, PurePosixPath

from standard.config import Config


def shipped_text(name: str) -> str:
    return (resources.files("standard") / "configs" / name).read_text(encoding="utf-8")


def targets(files: list[str], cfg: Config) -> dict[str, str]:
    """Repo-relative destination -> shipped file name."""
    out = {}
    for rel in files:
        path = PurePosixPath(rel)
        if path.name == "pyproject.toml":
            out[str(path.with_name("ruff.standard.toml"))] = "ruff.standard.toml"
    for front in cfg.front_dirs:
        out[f"{front}/eslint.standard.js"] = "eslint.standard.js"
    return out


def sync(root: Path, files: list[str], cfg: Config) -> list[str]:
    """Copy the shipped configs into the repo; returns the paths that changed."""
    changed = []
    for rel, name in sorted(targets(files, cfg).items()):
        dest, text = root / rel, shipped_text(name)
        if not dest.is_file() or dest.read_text(encoding="utf-8") != text:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            changed.append(rel)
    return changed
