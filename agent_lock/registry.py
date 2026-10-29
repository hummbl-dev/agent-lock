"""Pluggable resolution registry for model pins and tool schemas.

The producer is a *resolver* plug-in away from full resolution: a `Resolver`
maps an unresolved model (alias/floating pin) to a concrete identity, and maps
a tool name to its JSON schema. `FileRegistry` is a deterministic, JSON-backed
implementation suitable for testing and air-gapped use.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class Resolver(Protocol):
    def resolve_model(self, name: str, provider: str | None, pin: str | None) -> dict[str, Any]:
        """Return a resolved model identity, or raise LookupError."""
        ...

    def resolve_tool_schema(self, name: str, version: str | None) -> dict[str, Any]:
        """Return a tool's JSON schema, or raise LookupError."""
        ...


class FileRegistry:
    """JSON-backed registry.

    Shape:
        {
          "models": {"<name>": {"provider": ..., "pin": "snapshot|weights", "identity": ...}},
          "tools":  {"<name>": {"schema": {...}}}
        }
    """

    def __init__(self, data: dict[str, Any]):
        self._models = data.get("models", {}) if isinstance(data, dict) else {}
        self._tools = data.get("tools", {}) if isinstance(data, dict) else {}

    @classmethod
    def load(cls, path: str | Path) -> "FileRegistry":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def resolve_model(self, name: str, provider: str | None = None, pin: str | None = None) -> dict[str, Any]:
        entry = self._models.get(name)
        if entry is None or not isinstance(entry, dict):
            raise LookupError(f"model {name!r} not in registry")
        resolved = dict(entry)
        resolved["name"] = name
        resolved.setdefault("pin", "snapshot")
        return resolved

    def resolve_tool_schema(self, name: str, version: str | None = None) -> dict[str, Any]:
        entry = self._tools.get(name)
        if entry is None or not isinstance(entry, dict) or "schema" not in entry:
            raise LookupError(f"tool {name!r} schema not in registry")
        return entry["schema"]
