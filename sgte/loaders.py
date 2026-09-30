"""JSON loaders for official Theme 2 starter files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from sgte.paths import DEEPLINKS_JSON, SIIS_RESPONSES_JSON, require_file


def load_json_file(path: Path) -> Any:
    require_file(path)
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


@dataclass(frozen=True)
class DeeplinkRecord:
    """One catalogue row from deeplinks.json, URI preserved exactly."""

    id: str
    deeplink: str
    description: str
    message: str
    originalType: Optional[str]
    control_type: Any
    qna_description: Optional[str]
    validation: Optional[Dict[str, Any]]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class SiisRecord:
    """One SIIS article from siis_responses.json."""

    id: str
    original_query: str
    title: str
    content: str
    siis_response: Mapping[str, Any]
    raw: Mapping[str, Any]


def _require_mapping(payload: Any, path: Path) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}, got {type(payload).__name__}")
    return payload


def load_deeplinks(path: Union[Path, None] = None) -> List[DeeplinkRecord]:
    path = path or DEEPLINKS_JSON
    payload = _require_mapping(load_json_file(path), path)
    rows = payload.get("deeplinks")
    if not isinstance(rows, list):
        raise ValueError(f"{path} is missing a 'deeplinks' array")
    records: List[DeeplinkRecord] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{path} deeplinks[{index}] is not an object")
        uri = row.get("deeplink")
        if not isinstance(uri, str) or not uri:
            raise ValueError(f"{path} deeplinks[{index}] is missing deeplink string")
        records.append(
            DeeplinkRecord(
                id=str(row.get("id", "")),
                deeplink=uri,  # verbatim; never rewrite masked URIs
                description=str(row.get("description") or ""),
                message=str(row.get("message") or ""),
                originalType=row.get("originalType"),
                control_type=row.get("control_type"),
                qna_description=row.get("qna_description"),
                validation=row.get("validation") if isinstance(row.get("validation"), dict) else None,
                raw=row,
            )
        )
    return records


def load_siis_responses(path: Union[Path, None] = None) -> List[SiisRecord]:
    path = path or SIIS_RESPONSES_JSON
    payload = _require_mapping(load_json_file(path), path)
    rows = payload.get("responses")
    if not isinstance(rows, list):
        raise ValueError(f"{path} is missing a 'responses' array")
    records: List[SiisRecord] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{path} responses[{index}] is not an object")
        nested = row.get("siis_response")
        if not isinstance(nested, dict):
            raise ValueError(f"{path} responses[{index}] is missing siis_response object")
        records.append(
            SiisRecord(
                id=str(row.get("id", "")),
                original_query=str(row.get("original_query") or ""),
                title=str(nested.get("title") or ""),
                content=str(nested.get("content") or ""),
                siis_response=nested,
                raw=row,
            )
        )
    return records
