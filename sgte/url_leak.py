"""Detect web URL leakage in user-facing text. Structured bixby:// fields are out of scope."""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple

_HTTP = re.compile(r"https?://", re.IGNORECASE)
_WWW = re.compile(r"\bwww\.", re.IGNORECASE)
_MARKDOWN = re.compile(r"\[[^\]]*\]\([^)]+\)")
_WEB_SCHEME = re.compile(r"\b(?:ftp|mailto|file)://", re.IGNORECASE)
# Obvious host-style links (not Samsung masked bixby:// URIs).
_DOMAIN = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|edu|gov|io|co|kr|in|uk)\b",
    re.IGNORECASE,
)


def url_leak_reasons(text: str) -> List[str]:
    if not text:
        return []
    reasons: List[str] = []
    if _HTTP.search(text):
        reasons.append("http(s) URL")
    if _WWW.search(text):
        reasons.append("www. URL")
    if _MARKDOWN.search(text):
        reasons.append("markdown link")
    if _WEB_SCHEME.search(text):
        reasons.append("URI-style scheme")
    if _DOMAIN.search(text):
        reasons.append("domain-style link")
    return reasons


def scan_texts(labeled: Iterable[Tuple[str, str]]) -> List[str]:
    errors: List[str] = []
    for label, text in labeled:
        for reason in url_leak_reasons(text or ""):
            errors.append(f"URL leak ({reason}) in {label}")
    return errors
