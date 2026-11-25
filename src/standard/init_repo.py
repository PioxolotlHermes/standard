"""`standard init`: skeleton for a new repo."""

from importlib import resources
from pathlib import Path

from standard.baseline import BASELINE_FILE
from standard.config import ConfigError, parse_config
from standard.engine import CONFIG_FILE
from standard.files import list_files
from standard.sync import sync

DEFAULT_ROOT = 'roots = ["src/example"]'


def detect_packages(root: Path) -> list[str]:
    src = root / "src"
    found = sorted(p.name for p in src.iterdir() if p.is_dir() and any(p.rglob("*.py"))) if src.is_dir() else []
    return [f"src/{name}" for name in found] or ["src"]


def render_config(packages: list[str], fronts: list[str]) -> str:
    text = (resources.files("standard") / "templates" / "standard.toml").read_text(encoding="utf-8")
    text = text.replace(DEFAULT_ROOT, "roots = [" + ", ".join(f'"{p}"' for p in packages) + "]")
    return text.replace("dirs = []", "dirs = [" + ", ".join(f'"{f}"' for f in fronts) + "]")


def init_repo(root: Path, packages: list[str], fronts: list[str]) -> list[str]:
    """Write standard.toml, an empty baseline and the synced configs; returns the files written."""
    target = root / CONFIG_FILE
    if target.exists():
        raise ConfigError(f"{target} already exists; init only creates new repos")
    text = render_config(packages or detect_packages(root), fronts)
    target.write_text(text, encoding="utf-8")
    (root / BASELINE_FILE).write_text("[]\n", encoding="utf-8")
    written = [CONFIG_FILE, BASELINE_FILE]
    return written + sync(root, list_files(root), parse_config(text))
