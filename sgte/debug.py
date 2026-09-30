"""Optional stderr debug trace. Never attached to the official JSON response."""

from __future__ import annotations

import sys
from typing import Iterable, List


def format_debug(blocks: Iterable[tuple[str, str]]) -> str:
    lines: List[str] = []
    for title, body in blocks:
        lines.append(title)
        lines.append("↓")
        lines.append(body.rstrip() or "(empty)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def emit_debug(text: str, enabled: bool) -> None:
    if enabled and text:
        sys.stderr.write(text)
        if not text.endswith("\n"):
            sys.stderr.write("\n")
