"""Deterministic response validation against official schema.py and the deeplink catalogue."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from sgte.deeplink_repo import DeeplinkRepository
from sgte.official_schema import (
    Action,
    ContextDeeplinkResponse,
    Deeplink,
    Goal,
    ResultTypes,
    StepGroup,
    ValidationDeepLink,
    actionCategory,
)
from sgte.url_leak import scan_texts


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    response: Optional[ContextDeeplinkResponse] = None


def unwrap_response_payload(payload: Any) -> Any:
    """Accept official sample_output.json wrapping or a bare ContextDeeplinkResponse."""
    if not isinstance(payload, dict):
        return payload
    if "contexts" in payload:
        return {"contexts": payload["contexts"]}
    inner = payload.get("response")
    if isinstance(inner, dict) and "contexts" in inner:
        return {"contexts": inner["contexts"]}
    return payload


class ResponseValidator:
    def __init__(self, deeplinks: DeeplinkRepository):
        self.deeplinks = deeplinks

    def validate(self, payload: Any) -> ValidationResult:
        errors: List[str] = []
        body = unwrap_response_payload(payload)
        try:
            parsed = ContextDeeplinkResponse.model_validate(body)
        except ValidationError as exc:
            return ValidationResult(ok=False, errors=_pydantic_errors(exc))

        for gi, goal in enumerate(parsed.contexts):
            errors.extend(self._validate_goal(goal, f"contexts[{gi}]"))

        ok = not errors
        return ValidationResult(ok=ok, errors=errors, response=parsed)

    def _validate_goal(self, goal: Goal, loc: str) -> List[str]:
        errors: List[str] = []
        if not isinstance(goal.goal, str) or not goal.goal.strip():
            errors.append(f"{loc}.goal must be a non-empty string")
        if not isinstance(goal.title, str) or not goal.title.strip():
            errors.append(f"{loc}.title must be a non-empty string")
        if not isinstance(goal.actions, list):
            errors.append(f"{loc}.actions must be a list")
        if not isinstance(goal.score, (int, float)) or isinstance(goal.score, bool):
            errors.append(f"{loc}.score must be a number")

        errors.extend(scan_texts(((f"{loc}.goal", goal.goal), (f"{loc}.title", goal.title))))

        for ai, action in enumerate(goal.actions):
            errors.extend(self._validate_action(action, f"{loc}.actions[{ai}]"))
        return errors

    def _validate_action(self, action: Action, loc: str) -> List[str]:
        errors: List[str] = []
        if action.category is not None and not isinstance(action.category, actionCategory):
            errors.append(f"{loc}.category is not a valid actionCategory")

        category = action.category if action.category is not None else actionCategory.manual
        errors.extend(
            scan_texts(
                (
                    (f"{loc}.actionName", action.actionName),
                    (f"{loc}.description", action.description),
                )
            )
        )

        if not isinstance(action.stepGroups, list) or not action.stepGroups:
            errors.append(f"{loc}.stepGroups must be a non-empty list")
            return errors

        for si, group in enumerate(action.stepGroups):
            errors.extend(self._validate_step_group(group, category, f"{loc}.stepGroups[{si}]"))
        return errors

    def _validate_step_group(
        self, group: StepGroup, category: actionCategory, loc: str
    ) -> List[str]:
        errors: List[str] = []
        if not isinstance(group.steps, list) or not group.steps:
            errors.append(f"{loc}.steps must be a non-empty list of strings")
        else:
            for ti, step in enumerate(group.steps):
                if not isinstance(step, str) or not step.strip():
                    errors.append(f"{loc}.steps[{ti}] must be a non-empty string")
                errors.extend(scan_texts(((f"{loc}.steps[{ti}]", step),)))

        actionable = group.actionableDeeplink
        if category == actionCategory.manual and actionable is not None:
            errors.append(f"{loc}: manual actions must not contain actionableDeeplink")

        if actionable is not None:
            errors.extend(self._validate_actionable(actionable, f"{loc}.actionableDeeplink"))

        validation = group.validationDeeplink
        if validation is not None:
            errors.extend(self._validate_validation(validation, f"{loc}.validationDeeplink"))
        return errors

    def _validate_actionable(self, link: Deeplink, loc: str) -> List[str]:
        errors: List[str] = []
        uri = link.deeplink
        if not self.deeplinks.contains_actionable_uri(uri):
            errors.append(f"{loc}.deeplink is not in the official catalogue: {uri!r}")
        errors.extend(
            scan_texts(
                (
                    (f"{loc}.description", link.description),
                    (f"{loc}.message", link.message or ""),
                )
            )
        )
        return errors

    def _validate_validation(self, link: ValidationDeepLink, loc: str) -> List[str]:
        errors: List[str] = []
        if not link.deeplink:
            errors.append(f"{loc}.deeplink is required")
        elif not self.deeplinks.contains_validation_uri(link.deeplink):
            errors.append(
                f"{loc}.deeplink is not a catalogue validation URI: {link.deeplink!r}"
            )
        if not link.key:
            errors.append(f"{loc}.key is required")
        if link.resultType is not None and not isinstance(link.resultType, ResultTypes):
            errors.append(f"{loc}.resultType is not a valid ResultTypes value")
        return errors


def _pydantic_errors(exc: ValidationError) -> List[str]:
    messages: List[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        messages.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
    return messages or [str(exc)]
