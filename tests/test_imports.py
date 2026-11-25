from pathlib import Path

import pytest

from tests.helpers import CONFIG, found, write_repo

MODULES = ("a", "b", "common", "people", "web", "migrations")


@pytest.mark.parametrize(
    ("module", "statement", "bad"),
    [
        ("a", "from pkg.b import y", True),
        ("a", "import pkg.b.deep", True),
        ("a", "from ..b import y", True),
        ("a", "from pkg.common import y", False),
        ("a", "from pkg.people import y", False),
        ("people", "from pkg.a import y", True),
        ("common", "from pkg.a import y", True),
        ("web", "from pkg.a import y", False),
        ("migrations", "from pkg.a import y", False),
        ("a", "from pkg.web import y", True),
        ("a", "import os", False),
    ],
)
def test_python_import_matrix(tmp_path: Path, module: str, statement: str, bad: bool) -> None:
    """Defect: a module imports a sibling module (or anything imports a root) and the build stays green."""
    files = {f"src/pkg/{m}/__init__.py": "" for m in MODULES}
    files[f"src/pkg/{module}/x.py"] = statement + "\n"
    errors = found(write_repo(tmp_path, files))
    assert (f"R1 src/pkg/{module}/x.py" in errors) is bad


@pytest.mark.parametrize(
    ("statement", "bad"),
    [
        ("import { y } from '../b/y';", True),
        ("import y from '$lib/b/y';", True),
        ("import {\n  y,\n} from '../b/y';", True),
        ("import { y } from '../common/y';", False),
        ("import { y } from './local';", False),
        ("import { y } from 'svelte';", False),
    ],
)
def test_front_import_matrix(tmp_path: Path, statement: str, bad: bool) -> None:
    """Defect: TS/Svelte imports bypass the module boundary because only Python was parsed."""
    config = CONFIG.replace('roots = ["src/pkg"]', 'roots = ["src/pkg", "front/src/lib"]')
    files = {f"front/src/lib/{m}/index.ts": "export const z = 1;\n" for m in ("a", "b", "common")}
    files["front/src/lib/a/x.svelte"] = f'<script lang="ts">\n{statement}\n</script>\n'
    errors = found(write_repo(tmp_path, files, config))
    assert ("R1 front/src/lib/a/x.svelte" in errors) is bad


def test_core_module_needs_existing_adr(tmp_path: Path) -> None:
    """Defect: a core module is declared without the ADR that justifies it."""
    root = write_repo(tmp_path, {"src/pkg/people/x.py": "x = 1\n"})
    (root / "docs/adr/0001-core.md").unlink()
    assert "CONFIG standard.toml" in found(root)
