from pathlib import Path

from standard.cli import main
from tests.helpers import found

REPO = Path(__file__).resolve().parents[1]


def test_init_creates_a_repo_that_passes_check(tmp_path: Path) -> None:
    """Defect: a new repo starts red (or without the baseline/configs) so enforcement is skipped from commit one."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (tmp_path / "src/x").mkdir(parents=True)
    (tmp_path / "src/x/__init__.py").write_text("", encoding="utf-8")
    assert main(["init", "--root", str(tmp_path), "--front", "front"]) == 0
    for name in ("standard.toml", "standard-baseline.json", "ruff.standard.toml", "front/eslint.standard.js"):
        assert (tmp_path / name).is_file(), name
    assert 'roots = ["src/x"]' in (tmp_path / "standard.toml").read_text(encoding="utf-8")
    drift = {e for e in found(tmp_path) if not e.startswith("R8 pyproject.toml")}
    assert drift == {"R8 front/eslint.config.js"}  # the repo still has to wire pyproject and eslint itself


def test_init_refuses_to_overwrite(tmp_path: Path) -> None:
    """Defect: re-running init wipes a repo's reviewed standard.toml."""
    (tmp_path / "standard.toml").write_text("# mine\n", encoding="utf-8")
    assert main(["init", "--root", str(tmp_path)]) == 2
    assert (tmp_path / "standard.toml").read_text(encoding="utf-8") == "# mine\n"


def test_woodpecker_step_template_runs_lint_only_for_adopted_tools() -> None:
    """Defect: the shared CI step lints with tools a repo has not adopted, so atlas and the monorepo stay red."""
    text = (REPO / "templates/woodpecker-standard-step.yaml").read_text(encoding="utf-8")
    assert "standard tools --json" in text
    assert "--base" in text
    for tool, command in (("ruff", "ruff check ."), ("format", "ruff format --check ."), ("mypy", "mypy")):
        assert f"if flag {tool}; then uv run {command}; fi" in text, tool


def test_woodpecker_step_template_gets_the_pr_target_branch_from_the_clone() -> None:
    """Defect: on pull_request the diff guard has no origin/<target> (the step has no netrc), so it checks nothing."""
    text = (REPO / "templates/woodpecker-standard-step.yaml").read_text(encoding="utf-8")
    assert "fetch-target-branch: true" in text
    assert "depth: 0" in text


def test_own_ci_dogfoods_the_checker() -> None:
    """Defect: this repo stops dogfooding the checker, so the standard rots unnoticed."""
    text = (REPO / ".woodpecker.yaml").read_text(encoding="utf-8")
    assert "standard check --base" in text
    assert "fetch-target-branch: true" in text


def test_agents_block_is_short_and_lists_every_rule() -> None:
    """Defect: the block pasted into every repo's AGENTS.md loses a rule or grows past its 10 lines."""
    text = (REPO / "templates/AGENTS-block.md").read_text(encoding="utf-8")
    assert len(text.strip().splitlines()) <= 10
    assert all(f"R{n}" in text for n in range(1, 10))
