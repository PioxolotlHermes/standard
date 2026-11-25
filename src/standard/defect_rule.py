"""R6: only critical tests - every test states its `Defect:`; test lines stay within code lines."""

import ast
import re

from standard.files import Source, parse_python
from standard.model import Violation
from standard.size_rules import python_functions

CASE = re.compile(r"""^\s*(?:test|it)(?:\.(?:only|skip|fixme|fail|slow))?\s*\(\s*(?:['"`]([^'"`]*))?""")
JS_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs"}


def _python_cases(src: Source) -> list[Violation]:
    tree = parse_python(src)
    out = []
    for name, node in python_functions(tree) if tree else ():
        if node.name.startswith("test_") and "Defect:" not in (ast.get_docstring(node) or ""):
            msg = f'test {name} lacks a docstring with "Defect: <what it catches>"'
            out.append(Violation("R6", src.rel, node.lineno, msg, key=name))
    return out


def _js_cases(src: Source) -> list[Violation]:
    out = []
    for number, line in enumerate(src.lines):
        match = CASE.match(line)
        window = src.lines[max(0, number - 3) : number + 2]
        if match and not any("Defect:" in text for text in window):
            title = match.group(1) or "test"
            out.append(Violation("R6", src.rel, number + 1, f'test "{title}" lacks a // Defect: comment', key=title))
    return out


def check_defects(sources: list[Source]) -> list[Violation]:
    out: list[Violation] = []
    for src in sources:
        if not (src.is_test and src.counted):
            continue
        if src.suffix == ".py":
            out += _python_cases(src)
        elif src.suffix in JS_SUFFIXES:
            out += _js_cases(src)
    return out


def check_budget(sources: list[Source]) -> tuple[list[Violation], str]:
    """Test lines must not exceed code lines (hand-written, same exemptions as R2)."""
    tests = sum(len(s.lines) for s in sources if s.counted and s.is_test)
    code = sum(len(s.lines) for s in sources if s.counted and not s.is_test)
    ratio = tests / code if code else (0.0 if not tests else float("inf"))
    text = f"R6 budget: test lines {tests} / code lines {code} = {ratio:.2f} (max 1.00)"
    bad = [] if ratio <= 1.0 else [Violation("R6", "(repo)", 0, text, baselinable=False)]
    return bad, text
