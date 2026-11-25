"""R1: modular monolith - no imports between modules."""

from pathlib import PurePosixPath

from standard.config import Config
from standard.files import Source, parse_python
from standard.imports_py import python_targets
from standard.imports_ts import ts_targets
from standard.model import Violation

OPEN_SOURCES = {"root", "migrations", "top"}  # may import anything inside the app


def forbidden(src_role: str, src: str, tgt_role: str, tgt: str) -> str:
    """Reason why `src` may not import `tgt`, or an empty string when allowed."""
    if src == tgt or src_role in OPEN_SOURCES:
        return ""
    if tgt_role in {"root", "migrations"}:
        return f"{src} imports composition root {tgt}"
    if src_role == "shared":
        return "" if tgt_role == "shared" else f"shared module {src} imports app module {tgt}"
    if tgt_role == "shared":
        return ""
    if src_role == "core":
        return f"core module {src} imports {tgt} (core may import only shared modules)"
    return "" if tgt_role == "core" else f"module {src} imports module {tgt} (talk through ports in the root)"


def module_dirs(sources: list[Source], roots: tuple[str, ...]) -> dict[str, set[str]]:
    """Per root: names of its top-level directories that contain code."""
    dirs: dict[str, set[str]] = {root: set() for root in roots}
    for src in sources:
        for root in roots:
            if src.rel.startswith(root + "/") and src.rel.count("/", len(root) + 1) >= 1:
                dirs[root].add(src.rel[len(root) + 1 :].split("/")[0])
    return dirs


def _targets(src: Source, root: str, cfg: Config) -> list[tuple[int, str, str]]:
    """(line, root, target) for one file; empty when the file cannot be analysed."""
    below = PurePosixPath(src.rel).relative_to(root).parts
    if src.suffix == ".py":
        tree = parse_python(src)
        if tree is None:
            return []
        return [(line, root, tgt) for line, tgt in python_targets(tree, below, PurePosixPath(root).name)]
    return ts_targets(src.text, src.rel, cfg.roots)


def check_imports(sources: list[Source], cfg: Config) -> list[Violation]:
    known = module_dirs(sources, cfg.roots)
    out: list[Violation] = []
    for src in sources:
        root = next((r for r in cfg.roots if src.rel.startswith(r + "/")), None)
        if root is None:
            continue
        below = PurePosixPath(src.rel).relative_to(root).parts
        mine = below[0] if len(below) > 1 else ""
        role = cfg.role(mine) if mine else "top"
        for line, tgt_root, target in _targets(src, root, cfg):
            if target not in known.get(tgt_root, set()) or (tgt_root, target) == (root, mine):
                continue
            reason = forbidden(role, mine, cfg.role(target), target)
            if reason:
                out.append(Violation("R1", src.rel, line, reason, key=f"->{target}"))
    return out
