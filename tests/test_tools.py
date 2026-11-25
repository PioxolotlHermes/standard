import json
import tomllib
from pathlib import Path

import pytest

from standard.cli import main
from standard.sync import shipped_text
from tests.helpers import CONFIG, found, write_repo

FORMAT_ON = CONFIG + "\n[tool.standard]\nformat = true\n"
FULL = """[project]
name = "x"

[dependency-groups]
dev = ["ruff==0.17.5", "mypy==2.4.1"]

[tool.ruff]
extend = "ruff.standard.toml"

[tool.mypy]
strict = true
files = ["src"]
"""
ALL_OFF = {"ruff": False, "format": False, "mypy": False}


def tools(root: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, bool]:
    assert main(["tools", "--root", str(root), "--json"]) == 0
    result: dict[str, bool] = json.loads(capsys.readouterr().out)
    return result


@pytest.mark.parametrize(
    ("pyproject", "config", "expected"),
    [
        (FULL, FORMAT_ON, {"ruff": True, "format": True, "mypy": True}),
        (FULL, CONFIG, {"ruff": True, "format": False, "mypy": True}),
        (FULL.replace('"ruff==0.17.5", ', ""), FORMAT_ON, {"ruff": False, "format": False, "mypy": True}),
        (FULL.replace('extend = "ruff.standard.toml"', ""), FORMAT_ON, {"ruff": False, "format": False, "mypy": True}),
        (FULL.replace(', "mypy==2.4.1"', ""), FORMAT_ON, {"ruff": True, "format": True, "mypy": False}),
        (FULL.replace("strict = true", "strict = false"), FORMAT_ON, {"ruff": True, "format": True, "mypy": False}),
        (FULL.replace('files = ["src"]', ""), FORMAT_ON, {"ruff": True, "format": True, "mypy": False}),
        (FULL.replace('files = ["src"]', 'packages = ["x"]'), FORMAT_ON, {"ruff": True, "format": True, "mypy": True}),
    ],
)
def test_tool_adoption_detection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], pyproject: str, config: str, expected: dict[str, bool]
) -> None:
    """Defect: CI lints with a tool the repo has not adopted (red forever) or skips one it has (no enforcement)."""
    assert tools(write_repo(tmp_path, {"pyproject.toml": pyproject}, config), capsys) == expected


def test_no_pyproject_adopts_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Defect: a front-only repo gets python lint steps and fails on a missing pyproject.toml."""
    assert tools(write_repo(tmp_path, {}, FORMAT_ON), capsys) == ALL_OFF


def test_unadopted_format_is_baselinable_debt(tmp_path: Path) -> None:
    """Defect: an unformatted repo cannot reach 0 errors, or the debt stays invisible once the switch is flipped."""
    files = {"pyproject.toml": FULL, "ruff.standard.toml": shipped_text("ruff.standard.toml")}
    root = write_repo(tmp_path, files)
    assert "R8 pyproject.toml" in found(root)
    assert main(["baseline", "--root", str(root)]) == 0
    assert found(root) == set()
    (root / "standard.toml").write_text(FORMAT_ON, encoding="utf-8")
    assert "BASELINE pyproject.toml" in found(root)  # the stale entry: the ratchet keeps the adoption


def test_catalog_is_a_register_with_one_library_per_purpose() -> None:
    """Defect: a catalog entry without a purpose, or a second library for one purpose without a reason."""
    catalog = tomllib.loads(shipped_text("catalog.toml"))
    seen: dict[str, str] = {}
    for language, sections in catalog.items():
        for section, entries in sections.items():
            for name, entry in entries.items():
                purpose = entry.get("purpose", "")
                assert purpose, f"{language}.{section}.{name} has no purpose"
                first = seen.setdefault(f"{language}:{purpose}", name)
                assert first == name or entry.get("duplicate_of_ok"), f"{name} duplicates {first} ({purpose})"
    assert {"google-api-python-client", "google-auth", "openpyxl", "pillow"} <= set(catalog["python"]["runtime"])
