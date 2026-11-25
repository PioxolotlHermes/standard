"""Which top-level modules does a TS/JS/Svelte file import (relative and `$lib/` specifiers)."""

import posixpath
import re

SPEC = re.compile(
    r"""(?:\b(?:import|export)\b[^'"`;]*?\bfrom\s*|\bimport\s*\(?\s*)['"]([^'"\n]+)['"]""",
)


def _resolve(spec: str, file_rel: str, roots: tuple[str, ...]) -> str | None:
    """Repo-relative path the specifier points to, or None when it is a package/unknown alias."""
    if spec.startswith("."):
        return posixpath.normpath(posixpath.join(posixpath.dirname(file_rel), spec))
    if spec.startswith("$lib/"):
        libs = [r for r in roots if posixpath.basename(r) == "lib"]
        return posixpath.join(libs[0], spec[5:]) if libs else None
    return None


def ts_targets(text: str, file_rel: str, roots: tuple[str, ...]) -> list[tuple[int, str, str]]:
    """(line, root, first path component below root) for each import that lands inside a package root."""
    found = []
    for match in SPEC.finditer(text):
        target = _resolve(match.group(1), file_rel, roots)
        if target is None:
            continue
        for root in roots:
            if target.startswith(root + "/"):
                line = text.count("\n", 0, match.start()) + 1
                found.append((line, root, target[len(root) + 1 :].split("/")[0]))
    return found
