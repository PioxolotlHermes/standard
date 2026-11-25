from pathlib import Path

from tests.helpers import found, lines, write_repo

PY_OK = 'def test_a() -> None:\n    """Defect: the thing breaks."""\n    assert True\n'
PY_BAD = 'def test_a() -> None:\n    """Just a test."""\n    assert True\n'
CODE = {"src/pkg/a/x.py": lines(30)}


def test_pytest_function_needs_defect_docstring(tmp_path: Path) -> None:
    """Defect: tests without a stated defect pile up (R6 is what keeps the suite critical-only)."""
    bad = write_repo(tmp_path / "bad", {**CODE, "tests/test_a.py": PY_BAD})
    good = write_repo(tmp_path / "good", {**CODE, "tests/test_a.py": PY_OK})
    assert "R6 tests/test_a.py" in found(bad)
    assert "R6 tests/test_a.py" not in found(good)


def test_vitest_case_needs_defect_comment(tmp_path: Path) -> None:
    """Defect: vitest/Playwright cases escape R6 because only pytest was inspected."""
    bad = "test('x', () => {\n  expect(1).toBe(1);\n});\n"
    good = "// Defect: x breaks.\n" + bad
    errors_bad = found(write_repo(tmp_path / "bad", {**CODE, "front/a.test.ts": bad}))
    errors_good = found(write_repo(tmp_path / "good", {**CODE, "front/a.test.ts": good}))
    assert "R6 front/a.test.ts" in errors_bad
    assert "R6 front/a.test.ts" not in errors_good


def test_test_budget_cannot_exceed_code(tmp_path: Path) -> None:
    """Defect: the suite outgrows the code it guards (R6 budget above 1.0)."""
    over = write_repo(tmp_path / "over", {"src/pkg/a/x.py": "x = 1\n", "tests/test_a.py": PY_OK})
    under = write_repo(tmp_path / "under", {**CODE, "tests/test_a.py": PY_OK})
    assert "R6 (repo)" in found(over)
    assert "R6 (repo)" not in found(under)
