"""Hash-addressed agent configuration lockfiles.

Companion to the `acve` registry: acve validates and matches lockfiles, this
package produces them. A lockfile pins a resolved agent configuration
(harness + model + goals + tools + permissions + policy) to a deterministic
unit identity: `provenance.config_sha256`, the SHA-256 of the RFC 8785 (JCS)
canonicalization of the document with `provenance` excluded.

Ponytail: not a full RFC 8785 implementation. ECMAScript number serialization
is approximated by Python `repr`, which agrees for integers and common floats
but can diverge on edge cases (e.g. 1e21). The hash contract is the canonical
bytes, not this code; swap in a real JCS library if cross-implementation
identity is required.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def canonicalize(doc: dict[str, Any]) -> str:
    """Canonical JSON string of a document, minus `provenance`."""
    payload = {k: v for k, v in doc.items() if k != "provenance"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def config_sha256(doc: dict[str, Any]) -> str:
    """Compute the configuration unit hash for a document."""
    return hashlib.sha256(canonicalize(doc).encode("utf-8")).hexdigest()


def verify(doc: dict[str, Any]) -> bool:
    """True iff provenance.config_sha256 equals the computed hash."""
    claimed = doc.get("provenance", {}).get("config_sha256")
    return bool(claimed) and claimed == config_sha256(doc)


def schema_sha256(schema: dict[str, Any]) -> str:
    """SHA-256 of a tool's JSON schema (JCS canonicalization)."""
    return hashlib.sha256(
        json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def lock(
    config: dict[str, Any],
    *,
    generated_by: str,
    environment: str | None = None,
    generated_at: str | None = None,
    extra_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce a lockfile with tool schema pins.

    For every tool carrying a `schema`, sets `schema_sha256` to the canonical
    hash of that schema (overriding any stale value). Tools without a schema
    are left as-is — they need registry resolution, which is out of scope.
    Model pins are recorded, not resolved (see `pins.pin_issues`).
    """
    doc = copy.deepcopy(config)
    for tool in doc.get("tools", []):
        if isinstance(tool, dict) and "schema" in tool:
            tool["schema_sha256"] = schema_sha256(tool["schema"])
    return produce(
        doc,
        generated_by=generated_by,
        environment=environment,
        generated_at=generated_at,
        extra_provenance=extra_provenance,
    )


def produce(
    config: dict[str, Any],
    *,
    generated_by: str,
    environment: str | None = None,
    generated_at: str | None = None,
    extra_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce a lockfile from a resolved configuration.

    Returns a new document (input is not mutated) with a `provenance` block
    carrying `config_sha256` plus caller-supplied metadata. `config_sha256` is
    computed over the input with `provenance` excluded.
    """
    doc = copy.deepcopy(config)
    provenance: dict[str, Any] = {
        "config_sha256": config_sha256(config),
        "generated_by": generated_by,
        "generated_at": generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if environment is not None:
        provenance["environment"] = environment
    if extra_provenance:
        provenance.update(extra_provenance)
    doc["provenance"] = provenance
    return doc
