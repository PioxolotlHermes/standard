import json
from pathlib import Path

import pytest

from standard.cli import main
from standard.sync import shipped_text
from tests.helpers import CONFIG, found, write_repo

PYPROJECT = """[project]
name = "x"
dependencies = ["fastapi==1.0.0", "uvicorn[standard]==1.0.0"]

[dependency-groups]
dev = ["ruff==0.17.5", "types-pyyaml==6.0.0"]

[tool.ruff]
extend = "ruff.standard.toml"

[tool.mypy]
strict = true
"""
FRONT_CONFIG = CONFIG + '\n[front]\ndirs = ["front"]\n'


def repo(tmp_path: Path, **overrides: str | None) -> Path:
    files: dict[str, str | None] = {
        "pyproject.toml": PYPROJECT,
        "ruff.standard.toml": shipped_text("ruff.standard.toml"),
    }
    files.update(overrides)
    return write_repo(tmp_path, {k: v for k, v in files.items() if v is not None})


def test_clean_synced_repo_passes(tmp_path: Path) -> None:
    """Defect: the happy path reports false drift, which would block every repo."""
    assert found(repo(tmp_path)) == set()


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"ruff.standard.toml": None}, "R8 ruff.standard.toml"),
        ({"ruff.standard.toml": "line-length = 100\n"}, "R8 ruff.standard.toml"),
        ({"pyproject.toml": PYPROJECT.replace('extend = "ruff.standard.toml"', "")}, "R8 pyproject.toml"),
        ({"pyproject.toml": PYPROJECT.replace("strict = true", "strict = false")}, "R8 pyproject.toml"),
        ({"pyproject.toml": PYPROJECT.replace("ruff==0.17.5", "ruff>=0.17")}, "R8 pyproject.toml"),
    ],
)
def test_python_tooling_drift(tmp_path: Path, overrides: dict[str, str | None], expected: str) -> None:
    """Defect: a repo drifts from the shared ruff/mypy setup or floats its dev tools unnoticed."""
    assert expected in found(repo(tmp_path, **overrides))


def test_front_eslint_drift_and_npm_pins(tmp_path: Path) -> None:
    """Defect: the shared ESLint config is missing/stale in a front dir, or npm tools float (^1.0.0)."""
    package = json.dumps({"devDependencies": {"eslint": "^10.0.0", "vitest": "5.1.0"}})
    files = {"front/package.json": package, "front/eslint.config.js": "import './eslint.standard.js';\n"}
    root = write_repo(tmp_path, files, FRONT_CONFIG)
    errors = found(root)
    assert {"R8 front/eslint.standard.js", "R8 front/package.json"} <= errors
    (root / "front/eslint.standard.js").write_text(shipped_text("eslint.standard.js"), encoding="utf-8")
    (root / "front/package.json").write_text(json.dumps({"devDependencies": {"eslint": "10.14.0"}}), encoding="utf-8")
    assert found(root) == set()


def test_dependency_outside_catalog(tmp_path: Path) -> None:
    """Defect: an unvetted library (second HTTP client, ORM) enters a repo without a decision."""
    pyproject = PYPROJECT.replace('"fastapi==1.0.0"', '"fastapi==1.0.0", "requests==2.0.0"')
    package = json.dumps({"dependencies": {"left-pad": "1.0.0"}})
    root = write_repo(tmp_path, {"pyproject.toml": pyproject, "ruff.standard.toml": shipped_text("ruff.standard.toml")})
    (root / "package.json").write_text(package, encoding="utf-8")
    errors = found(root)
    assert {"R9 pyproject.toml", "R9 package.json"} <= errors
    exception = '\n[[exceptions]]\npath = "requests"\nrule = "R9"\nreason = "legacy client"\n'
    (root / "standard.toml").write_text(CONFIG + exception, encoding="utf-8")
    assert "R9 pyproject.toml" not in found(root)


def test_sync_makes_repo_clean(tmp_path: Path) -> None:
    """Defect: `standard sync` writes files that `standard check` then calls drift."""
    root = write_repo(tmp_path, {"pyproject.toml": PYPROJECT, "front/package.json": "{}"}, FRONT_CONFIG)
    (root / "front/eslint.config.js").write_text("import './eslint.standard.js';\n", encoding="utf-8")
    assert found(root) != set()
    assert main(["sync", "--root", str(root)]) == 0
    assert found(root) == set()


def test_build_time_npm_tools_are_dev_only(tmp_path: Path) -> None:
    """Defect: SvelteKit/Tailwind/adapter built at build time are rejected as runtime dependencies."""
    package = {
        "dependencies": {"svelte": "5.0.0"},
        "devDependencies": {
            "@sveltejs/kit": "2.0.0",
            "@sveltejs/adapter-static": "3.0.0",
            "@sveltejs/vite-plugin-svelte": "5.0.0",
            "@tailwindcss/vite": "4.0.0",
            "tailwindcss": "4.0.0",
        },
    }
    runtime = {**package, "dependencies": {"svelte": "5.0.0", "@sveltejs/kit": "2.0.0", "tailwindcss": "4.0.0"}}
    ok = write_repo(tmp_path / "ok", {"front/package.json": json.dumps(package)}, FRONT_CONFIG)
    bad = write_repo(tmp_path / "bad", {"front/package.json": json.dumps(runtime)}, FRONT_CONFIG)
    assert "R9 front/package.json" not in found(ok)
    assert "R9 front/package.json" in found(bad)
