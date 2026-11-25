import re
from pathlib import Path

from standard.cli import main
from tests.helpers import found

REPO = Path(__file__).resolve().parents[1]
CHECKOUT_SHA = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"


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


def test_reusable_workflow_is_safe_and_pinned() -> None:
    """Defect: the shared workflow uses unpinned/third-party actions, a SIGPIPE-prone grep -q, or loses its inputs."""
    text = (REPO / ".github/workflows/standard.yml").read_text(encoding="utf-8")
    assert "workflow_call:" in text
    assert "inputs.ref" in text
    assert "--base" in text
    assert not re.search(r"\|\s*grep -q", text)
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert uses == [CHECKOUT_SHA]


def test_own_ci_enforces_the_standard_through_the_reusable_workflow() -> None:
    """Defect: this repo stops dogfooding the checker, so the standard rots unnoticed."""
    text = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "uses: ./.github/workflows/standard.yml" in text
    assert "ref: ${{ github.sha }}" in text


def test_agents_block_is_short_and_lists_every_rule() -> None:
    """Defect: the block pasted into every repo's AGENTS.md loses a rule or grows past its 10 lines."""
    text = (REPO / "templates/AGENTS-block.md").read_text(encoding="utf-8")
    assert len(text.strip().splitlines()) <= 10
    assert all(f"R{n}" in text for n in range(1, 10))
