"""Which Python lint tools a repo has adopted (drives the CI steps and the R8 adoption debt)."""

import tomllib
from pathlib import Path

from standard.manifests import python_deps

RUFF_CONFIG = "ruff.standard.toml"


def adoption(pyproject: str, format_on: bool) -> dict[str, bool]:
    """`ruff`, `format` and `mypy` adoption of one pyproject.toml; `format_on` is standard.toml's explicit switch."""
    try:
        data = tomllib.loads(pyproject)
    except tomllib.TOMLDecodeError:
        return {"ruff": False, "format": False, "mypy": False}
    dev = {dep.name for dep in python_deps(pyproject) if not dep.runtime}
    tool = data.get("tool", {})
    ruff = "ruff" in dev and tool.get("ruff", {}).get("extend") == RUFF_CONFIG
    mypy_cfg = tool.get("mypy", {})
    mypy = "mypy" in dev and mypy_cfg.get("strict") is True and bool(mypy_cfg.get("files") or mypy_cfg.get("packages"))
    return {"ruff": ruff, "format": ruff and format_on, "mypy": mypy}


def repo_adoption(root: Path, format_on: bool) -> dict[str, bool]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return {"ruff": False, "format": False, "mypy": False}
    return adoption(path.read_text(encoding="utf-8"), format_on)
