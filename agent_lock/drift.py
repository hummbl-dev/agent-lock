"""Detect when a live configuration has moved off its lockfile."""

from __future__ import annotations

from typing import Any

from .core import schema_sha256


def drift(lockfile: dict[str, Any], live_config: dict[str, Any], resolver: Any = None) -> list[str]:
    """Return drift findings ([] = live config still matches the lockfile).

    Reports:
      - tools present in the live config but absent from the lockfile
      - tool version changes
      - tool schema-hash changes (fetches the schema via `resolver` when the
        live config does not carry it inline)
      - model pin and identity changes
    """
    findings: list[str] = []
    locked_tools = {
        t["name"]: t for t in lockfile.get("tools", []) if isinstance(t, dict) and "name" in t
    }
    for t in live_config.get("tools", []):
        if not isinstance(t, dict) or "name" not in t:
            continue
        name = t["name"]
        locked = locked_tools.get(name)
        if locked is None:
            findings.append(f"tool {name!r}: present in live config, absent from lockfile")
            continue
        if t.get("version") != locked.get("version"):
            findings.append(f"tool {name!r}: version {locked.get('version')} -> {t.get('version')}")
        live_schema = t.get("schema")
        if live_schema is None and resolver is not None:
            try:
                live_schema = resolver.resolve_tool_schema(name, t.get("version"))
            except LookupError:
                pass
        if live_schema is not None:
            locked_sha = locked.get("schema_sha256")
            if locked_sha is not None and schema_sha256(live_schema) != locked_sha:
                findings.append(f"tool {name!r}: schema hash changed")

    live_model = live_config.get("model", {})
    locked_model = lockfile.get("model", {})
    if isinstance(live_model, dict) and isinstance(locked_model, dict):
        if locked_model.get("pin") != live_model.get("pin"):
            findings.append(f"model pin {locked_model.get('pin')} -> {live_model.get('pin')}")
        if locked_model.get("identity") and locked_model.get("identity") != live_model.get("identity"):
            findings.append(f"model identity {locked_model.get('identity')} -> {live_model.get('identity')}")
    return findings
