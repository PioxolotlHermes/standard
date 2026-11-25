import json
from pathlib import Path

import pytest

from tests.helpers import CONFIG, commit, found, git_init, lines, write_repo

EXC = '\n[[exceptions]]\npath = "src/pkg/a/x.py"\nrule = "R2"\nreason = "because"\n'


@pytest.mark.parametrize(
    "marker",
    [
        "# no" + "qa",
        "# type: " + "ignore",
        "// eslint-" + "disable-next-line",
        "pytest.mark." + "skip",
        "it." + "only(",
    ],
)
def test_added_suppression_is_red_only_with_base(tmp_path: Path, marker: str) -> None:
    """Defect: a new rule suppression lands in a diff without Piotrek's decision."""
    root = write_repo(tmp_path, {"src/pkg/a/x.py": "x = 1\n"})
    git_init(root)
    (root / "src/pkg/a/x.py").write_text(f"x = 1  {marker}\n", encoding="utf-8")
    assert "R7 src/pkg/a/x.py" in found(root, base="HEAD")
    assert "R7 src/pkg/a/x.py" not in found(root)


def test_unchanged_suppression_is_not_flagged(tmp_path: Path) -> None:
    """Defect: R7 re-flags old suppressions on every commit, so the guard gets ignored."""
    root = write_repo(tmp_path, {"src/pkg/a/x.py": "x = 1  # no" + "qa\n"})
    git_init(root)
    (root / "src/pkg/a/y.py").write_text("y = 2\n", encoding="utf-8")
    assert found(root, base="HEAD") == set()


def test_new_exception_is_red(tmp_path: Path) -> None:
    """Defect: an exception is added to standard.toml to silence a rule without a decision."""
    root = write_repo(tmp_path, {"src/pkg/a/x.py": lines(201)})
    git_init(root)
    (root / "standard.toml").write_text(CONFIG + EXC, encoding="utf-8")
    assert "R7 standard.toml" in found(root, base="HEAD")


def test_baseline_growth_is_red(tmp_path: Path) -> None:
    """Defect: the baseline is regenerated to hide new debt."""
    root = write_repo(tmp_path, {"src/pkg/a/x.py": lines(201)})
    old = [{"rule": "R2", "path": "src/pkg/a/x.py", "key": "", "value": 201}]
    (root / "standard-baseline.json").write_text(json.dumps(old), encoding="utf-8")
    git_init(root)
    (root / "src/pkg/a/x.py").write_text(lines(250), encoding="utf-8")
    old[0]["value"] = 250
    (root / "standard-baseline.json").write_text(json.dumps(old), encoding="utf-8")
    commit(root)
    assert "R7 standard-baseline.json" in found(root, base="HEAD~1")
