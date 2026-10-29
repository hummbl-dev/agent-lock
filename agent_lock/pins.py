"""Model pin levels and resolution status.

A resolved configuration's model identity can be pinned at four levels:
  weights  — exact parameter tensor identity (e.g. a content hash)
  snapshot — a specific hosted snapshot/checkpoint
  alias    — a mutable named release (e.g. "latest", "opus-4-6")
  floating — no pin at all (whatever the harness resolves today)

Only `weights` and `snapshot` are fully resolved. `alias` and `floating`
require a registry lookup to resolve to a concrete identity, which this
package does not (yet) perform.
"""

from __future__ import annotations

from typing import Any

PIN_LEVELS = ("weights", "snapshot", "alias", "floating")
RESOLVED_PINS = {"weights", "snapshot"}


def valid_pin(pin: Any) -> bool:
    return pin in PIN_LEVELS


def is_resolved(pin: Any) -> bool:
    return pin in RESOLVED_PINS


def pin_issues(config: dict[str, Any]) -> list[str]:
    """Report problems with a config's model pin ([] = fully pinned)."""
    model = config.get("model", {}) if isinstance(config.get("model"), dict) else {}
    pin = model.get("pin")
    issues: list[str] = []
    if pin is None:
        issues.append("model.pin is missing")
    elif not valid_pin(pin):
        issues.append(f"model.pin {pin!r} not in {PIN_LEVELS}")
    elif not is_resolved(pin):
        issues.append(f"model.pin {pin!r} is unresolved (alias/floating); requires registry resolution")
    return issues


def tool_issues(config: dict[str, Any]) -> list[str]:
    """Report tools that lack a schema ([] = fully pinned)."""
    issues: list[str] = []
    for i, tool in enumerate(config.get("tools", [])):
        if not isinstance(tool, dict):
            issues.append(f"tool {i}: not an object")
            continue
        if "schema" not in tool:
            issues.append(f"tool {i} ({tool.get('name', '?')}): missing schema; needs registry resolution")
    return issues
