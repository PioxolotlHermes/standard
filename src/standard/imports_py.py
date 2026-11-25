"""Which top-level modules does a Python file import (absolute and relative imports resolved)."""

import ast


def _targets(node: ast.Import | ast.ImportFrom, pkg_parts: tuple[str, ...], pkg: str) -> list[str]:
    if isinstance(node, ast.Import):
        split = [a.name.split(".") for a in node.names]
        return [parts[1] for parts in split if parts[0] == pkg and len(parts) > 1]
    module = node.module.split(".") if node.module else []
    if node.level == 0:
        if not module or module[0] != pkg:
            return []
        rest = module[1:]
    else:
        up = node.level - 1
        if up > len(pkg_parts):
            return []
        rest = list(pkg_parts[: len(pkg_parts) - up]) + module
    return [rest[0]] if rest else [a.name for a in node.names]


def python_targets(tree: ast.Module, parts_in_root: tuple[str, ...], pkg: str) -> list[tuple[int, str]]:
    """(line, first path component below the package) for each import. `parts_in_root` = file path below root."""
    pkg_parts = parts_in_root[:-1]
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            found += [(node.lineno, target) for target in _targets(node, pkg_parts, pkg)]
    return found
