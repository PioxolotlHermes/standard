import json
from pathlib import Path

from standard.cli import main
from tests.helpers import CONFIG, found, lines, write_repo

BIG = {"src/pkg/a/x.py": lines(201)}


def entry(value: int, path: str = "src/pkg/a/x.py") -> dict[str, object]:
    return {"rule": "R2", "path": path, "key": "", "value": value}


def baseline(root: Path, entries: list[dict[str, object]]) -> None:
    (root / "standard-baseline.json").write_text(json.dumps(entries), encoding="utf-8")


def test_baseline_accepts_listed_debt_only(tmp_path: Path) -> None:
    """Defect: the ratchet lets a new violation through, or rejects debt it already knows."""
    root = write_repo(tmp_path, {**BIG, "src/pkg/a/y.py": lines(201)})
    baseline(root, [entry(201)])
    assert found(root) == {"R2 src/pkg/a/y.py"}


def test_baseline_rejects_growth(tmp_path: Path) -> None:
    """Defect: a baselined file keeps growing because only its presence is checked."""
    root = write_repo(tmp_path, BIG)
    baseline(root, [entry(200)])
    assert found(root) == {"R2 src/pkg/a/x.py"}


def test_baseline_entry_that_no_longer_fails_is_an_error(tmp_path: Path) -> None:
    """Defect: paid-off debt stays in the baseline and can silently regress later."""
    root = write_repo(tmp_path, {"src/pkg/a/x.py": lines(10)})
    baseline(root, [entry(201)])
    assert found(root) == {"BASELINE src/pkg/a/x.py"}


def test_baseline_command_then_shrink(tmp_path: Path) -> None:
    """Defect: `baseline` writes entries that do not satisfy `check`, or --shrink adds new debt."""
    root = write_repo(tmp_path, BIG)
    assert main(["baseline", "--root", str(root)]) == 0
    assert found(root) == set()
    (root / "src/pkg/a/x.py").write_text(lines(150), encoding="utf-8")
    (root / "src/pkg/a/new.py").write_text(lines(250), encoding="utf-8")
    assert found(root) == {"BASELINE src/pkg/a/x.py", "R2 src/pkg/a/new.py"}
    assert main(["baseline", "--shrink", "--root", str(root)]) == 0
    assert json.loads((root / "standard-baseline.json").read_text()) == []
    assert found(root) == {"R2 src/pkg/a/new.py"}


def test_exception_needs_reason_and_suppresses(tmp_path: Path) -> None:
    """Defect: an exception without a reason is accepted, or a valid one does not suppress."""
    entry_toml = '\n[[exceptions]]\npath = "src/pkg/a/x.py"\nrule = "R2"\n'
    ok = write_repo(tmp_path / "ok", BIG, CONFIG + entry_toml + 'reason = "vendored file"\n')
    no_reason = write_repo(tmp_path / "no", BIG, CONFIG + entry_toml)
    assert found(ok) == set()
    assert "CONFIG standard.toml" in found(no_reason)
