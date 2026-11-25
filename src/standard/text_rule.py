"""R5: code is in English - Polish letters only in declared UI text files."""

import re
from pathlib import PurePosixPath

from standard.files import Source
from standard.model import Violation

# Polish diacritics written as escapes so this file itself stays ASCII.
POLISH = re.compile(
    "[\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c\u0104\u0106\u0118\u0141\u0143\u00d3\u015a\u0179\u017b]"
)


def allowed(rel: str, globs: tuple[str, ...]) -> bool:
    return any(PurePosixPath(rel).full_match(pattern) for pattern in globs)


def check_polish(sources: list[Source], globs: tuple[str, ...]) -> list[Violation]:
    out = []
    for src in sources:
        if not src.counted or allowed(src.rel, globs):
            continue
        hits = [n for n, line in enumerate(src.lines, 1) if POLISH.search(line)]
        if hits:
            msg = f"Polish letters on {len(hits)} line(s); code is English (UI texts: declare in [texts])"
            out.append(Violation("R5", src.rel, hits[0], msg, value=len(hits)))
    return out
