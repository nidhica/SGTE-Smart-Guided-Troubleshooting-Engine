"""Enable vs disable polarity for catalogue pairs. Never pick arbitrarily."""

from __future__ import annotations

import re
from typing import Optional

_ENABLE = re.compile(
    r"\b(enable|enabled|turn on|turns on|turned on|activate|activated|switch on|switching on|allow|allowed|show|unhide)\b",
    re.IGNORECASE,
)
_DISABLE = re.compile(
    r"\b(disable|disabled|turn off|turns off|turned off|deactivate|deactivated|switch off|switching off|block|blocked|hide|hidden)\b",
    re.IGNORECASE,
)

# Failure/report phrasing that contains "turn on" but is not an enable request.
_NEGATED_TURN_ON = re.compile(
    r"\b(?:"
    r"won'?t\s+turn(?:s|\s+ing)?\s+on|"
    r"will\s+not\s+turn(?:s|\s+ing)?\s+on|"
    r"doesn'?t\s+turn(?:s|\s+ing)?\s+on|"
    r"does\s+not\s+turn(?:s|\s+ing)?\s+on|"
    r"can'?t\s+turn(?:s|\s+ing)?\s+on|"
    r"cannot\s+turn(?:s|\s+ing)?\s+on|"
    r"unable\s+to\s+turn(?:s|\s+ing)?\s+on|"
    r"not\s+turning\s+on|"
    r"isn'?t\s+turning\s+on|"
    r"is\s+not\s+turning\s+on|"
    r"fails?\s+to\s+turn(?:s|\s+ing)?\s+on"
    r")\b",
    re.IGNORECASE,
)


def mask_negated_turn_on(text: str) -> str:
    """Remove negated/failure 'turn on' phrases before enable polarity matching."""
    return _NEGATED_TURN_ON.sub(" ", text or "")


def polarity(text: str) -> Optional[str]:
    """Return 'enable', 'disable', or None if the text does not commit."""
    # Scrub failure reports so "won't turn on" is not treated as enable.
    scrubbed = mask_negated_turn_on(text)
    en = bool(_ENABLE.search(scrubbed))
    dis = bool(_DISABLE.search(scrubbed))
    if en and not dis:
        return "enable"
    if dis and not en:
        return "disable"
    return None


def original_type_polarity(original_type: Optional[str]) -> Optional[str]:
    if original_type == "onURL":
        return "enable"
    if original_type == "offURL":
        return "disable"
    return None


def compatible(action_polarity: Optional[str], row_message: str, original_type: Optional[str]) -> bool:
    if action_polarity is None:
        return True
    row_p = polarity(row_message) or original_type_polarity(original_type)
    if row_p is None:
        return True
    return row_p == action_polarity
