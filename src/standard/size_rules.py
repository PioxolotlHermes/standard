"""R2 (file size) and R3 (Python function size). R4/TS function size belong to ruff/ESLint (R8)."""

import ast
from collections.abc import Iterator

from standard.files import Source, parse_python
from standard.model import Violation

CODE_LIMIT = 200
TEST_LIMIT = 300
FUNCTION_LIMIT = 50


def check_file_sizes(sources: list[Source]) -> list[Violation]:
    out = []
    for src in sources:
        limit = TEST_LIMIT if src.is_test else CODE_LIMIT
        if src.counted and len(src.lines) > limit:
            msg = f"{len(src.lines)} lines (limit {limit}); split the file, never raise the limit"
            out.append(Violation("R2", src.rel, limit + 1, msg, value=len(src.lines)))
    return out


def python_functions(tree: ast.Module) -> Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Every function with its dotted qualified name (classes and enclosing functions included)."""
    stack: list[tuple[str, ast.AST]] = [("", tree)]
    while stack:
        prefix, parent = stack.pop()
        for node in ast.iter_child_nodes(parent):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                name = prefix + node.name
                if not isinstance(node, ast.ClassDef):
                    yield name, node
                stack.append((name + ".", node))
            else:
                stack.append((prefix, node))


def check_function_sizes(sources: list[Source]) -> list[Violation]:
    out = []
    for src in sources:
        tree = parse_python(src) if src.suffix == ".py" and src.counted else None
        for name, node in python_functions(tree) if tree else ():
            size = (node.end_lineno or node.lineno) - node.lineno + 1
            if size > FUNCTION_LIMIT:
                msg = f"function {name} has {size} lines (limit {FUNCTION_LIMIT}); split it"
                out.append(Violation("R3", src.rel, node.lineno, msg, key=name, value=size))
    return out
