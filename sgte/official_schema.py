"""Import the official schema.py without copying or rewriting it."""

from __future__ import annotations

import importlib.util
import sys

from sgte.paths import SCHEMA_PY, require_file


def load_official_schema():
    path = require_file(SCHEMA_PY)
    name = "theme02_official_schema"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load official schema from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


schema = load_official_schema()

BaseDeeplink = schema.BaseDeeplink
Deeplink = schema.Deeplink
Condition = schema.Condition
ResultTypes = schema.ResultTypes
actionCategory = schema.actionCategory
ValidationDeepLink = schema.ValidationDeepLink
StepGroup = schema.StepGroup
Action = schema.Action
Goal = schema.Goal
ContextDeeplinkResponse = schema.ContextDeeplinkResponse
