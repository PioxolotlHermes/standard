from pathlib import Path

import pytest

from tests.helpers import CONFIG, found, lines, write_repo


@pytest.mark.parametrize(
    ("path", "text", "bad"),
    [
        ("src/pkg/a/x.py", lines(200), False),
        ("src/pkg/a/x.py", lines(201), True),
        ("tests/test_x.py", lines(300), False),
        ("tests/test_x.py", lines(301), True),
        ("front/src/lib/a/x.test.ts", lines(301, "const x = 1;"), True),
        ("src/pkg/migrations/versions/0001_x.py", lines(500), False),
        ("src/pkg/a/gen.py", "# generated\n" + lines(500), False),
        ("src/pkg/a/data.json", lines(500, "{}"), False),
    ],
)
def test_file_size_limits(tmp_path: Path, path: str, text: str, bad: bool) -> None:
    """Defect: oversized files slip through, or exempt files (migrations, generated, data) are flagged."""
    errors = found(write_repo(tmp_path, {path: text, "src/pkg/a/code.py": lines(400)}))
    assert (f"R2 {path}" in errors) is bad


@pytest.mark.parametrize(("body_lines", "decorator", "bad"), [(49, "", False), (50, "", True), (49, "@dec\n", False)])
def test_function_length(tmp_path: Path, body_lines: int, decorator: str, bad: bool) -> None:
    """Defect: a 51-line function passes, or decorators are counted towards the 50-line limit."""
    text = f"{decorator}def f() -> None:\n" + lines(body_lines, "    x = 1")
    errors = found(write_repo(tmp_path, {"src/pkg/a/x.py": text}))
    assert ("R3 src/pkg/a/x.py" in errors) is bad


def test_polish_letters_only_in_declared_texts(tmp_path: Path) -> None:
    """Defect: Polish identifiers/comments spread through the code; UI text files must stay allowed."""
    text = f"x = '{chr(0x105)}'\n"
    config = CONFIG + '\n[texts]\nglobs = ["src/pkg/i18n/pl*.py"]\n'
    files = {"src/pkg/a/x.py": text, "src/pkg/i18n/pl.py": text, "README.md": text}
    errors = found(write_repo(tmp_path, files, config))
    assert {e for e in errors if e.startswith("R5")} == {"R5 src/pkg/a/x.py"}
