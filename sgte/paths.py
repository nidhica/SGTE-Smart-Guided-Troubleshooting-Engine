"""Locate official Theme 2 starter-kit files without copying or mutating them."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Official Theme 2 student kit as shipped in this repository.
STUDENT_KIT = (
    REPO_ROOT
    / "participant-kit-all-themes (1)"
    / "participant-kit"
    / "Theme02_Input_Kit"
    / "student_kit"
)

SCHEMA_PY = STUDENT_KIT / "schema.py"
DEEPLINKS_JSON = STUDENT_KIT / "deeplinks.json"
SIIS_RESPONSES_JSON = STUDENT_KIT / "siis_responses.json"
SAMPLE_OUTPUT_JSON = STUDENT_KIT / "sample_output.json"
INPUT_TXT = STUDENT_KIT / "input.txt"


def require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Official file not found: {path}")
    return path
