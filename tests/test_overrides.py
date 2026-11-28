from pathlib import Path

import pytest

from standard.cli import main
from standard.config import ConfigError, parse_config
from standard.engine import run_check
from standard.sync import rendered_text
from tests.helpers import CONFIG, found, lines, write_repo

ADR = "docs/adr/0003-x.md"
OK = f'reason = "owner decision"\nadr = "{ADR}"\n'
CASE = 'def test_{}() -> None:\n    """Defect: the thing breaks."""\n' + lines(28, "    assert True")
TEST = "\n".join(CASE.format(n) for n in "abcd")  # 120 test lines against 100 code lines: ratio 1.2


def _repo(tmp: Path, body: str, files: dict[str, str] | None = None) -> Path:
    base = {ADR: "# adr\n", "src/pkg/a/x.py": lines(100), "tests/test_a.py": TEST}
    return write_repo(tmp, {**base, **(files or {})}, CONFIG + body)


@pytest.mark.parametrize(
    "body",
    [
        f"[overrides.R9]\nfoo = 1\n{OK}",
        f"[overrides.R6]\nbogus = 1\n{OK}",
        f'[overrides.R6]\ntest_code_ratio = 1.5\nadr = "{ADR}"\n',
        f'[overrides.R6]\ntest_code_ratio = 1.5\nreason = "  "\nadr = "{ADR}"\n',
        '[overrides.R6]\ntest_code_ratio = 1.5\nreason = "x"\n',
        f'[overrides.R6]\ntest_code_ratio = "1.5"\n{OK}',
        f"[overrides.R6]\ntest_code_ratio = 0\n{OK}",
        f"[overrides.R2]\nfile_lines = -5\n{OK}",
        f"[overrides.R2]\nfile_lines = 250.5\n{OK}",
        f"[overrides.R4]\ncomplexity = true\n{OK}",
        f"[overrides.R3]\n{OK}",
    ],
)
def test_invalid_override_is_a_config_error(body: str) -> None:
    """Defect: a typo or an unjustified override silently loosens the standard instead of failing."""
    with pytest.raises(ConfigError):
        parse_config(CONFIG + body)


def test_override_needs_existing_adr(tmp_path: Path) -> None:
    """Defect: an override cites an ADR that does not exist, so nobody recorded the owner's decision."""
    repo = _repo(tmp_path, f"[overrides.R6]\ntest_code_ratio = 1.5\n{OK}", {ADR: "x"})
    (repo / ADR).unlink()
    assert "CONFIG standard.toml" in found(repo)


def test_override_applies_and_is_visible(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Defect: an override is ignored, or it is applied without being shown on the run (hidden loosening)."""
    plain, over = _repo(tmp_path / "p", ""), _repo(tmp_path / "o", f"[overrides.R6]\ntest_code_ratio = 1.5\n{OK}")
    assert found(plain) == {"R6 (repo)"}  # default max 1.00 unchanged
    assert "(max 1.00)" in run_check(plain).budget
    assert "R6 (repo)" not in found(over)
    assert "(max 1.50)" in run_check(over).budget
    main(["check", "--root", str(over)])
    assert f"override R6 test_code_ratio=1.5 ({ADR})" in capsys.readouterr().out


def test_size_overrides_apply_and_default_stays(tmp_path: Path) -> None:
    """Defect: R2/R3 limits stay hard-coded, or an override leaks into repos that did not ask for it."""
    files = {"src/pkg/a/big.py": lines(250), "src/pkg/a/f.py": "def f() -> None:\n" + lines(60, "    x = 1")}
    body = f"[overrides.R2]\nfile_lines = 300\n{OK}\n[overrides.R3]\nfunction_lines = 80\n{OK}"
    default, relaxed = found(_repo(tmp_path / "d", "", files)), found(_repo(tmp_path / "r", body, files))
    assert {"R2 src/pkg/a/big.py", "R3 src/pkg/a/f.py"} <= default
    assert not {e for e in relaxed if e.split()[1].startswith("src/pkg/a/")}


def test_complexity_override_reaches_ruff_config() -> None:
    """Defect: R4 override accepted but ruff keeps enforcing 12, because ruff.standard.toml is a shipped copy."""
    cfg = parse_config(CONFIG + f"[overrides.R4]\ncomplexity = 15\n{OK}")
    assert "max-complexity = 15" in rendered_text("ruff.standard.toml", cfg.limits)
    assert "complexity: ['error', 15]" in rendered_text("eslint.standard.js", cfg.limits)
    assert "max-complexity = 12" in rendered_text("ruff.standard.toml", parse_config(CONFIG).limits)
