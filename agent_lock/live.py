"""Adapters that map live hosted model-catalog APIs to the Resolver protocol.

These are the "live registry sources": instead of a static JSON file, they query
a running model catalog and map its response onto `resolve_model`. Network I/O is
injected (`urlopen`) so the adapters are testable without a live endpoint.
"""

from __future__ import annotations

import json
from typing import Any, Callable

UrlOpen = Callable[[str], Any]

# Seconds. A missing timeout lets a stalled catalog hang the resolver.
_DEFAULT_URL_TIMEOUT_SECONDS = 10.0

# Pin levels a live source may upgrade. `snapshot` and `weights` are requests
# for an identity this source must already be able to produce.
_OLLAMA_UNRESOLVED_PINS = frozenset({"floating", "alias"})
_OPENROUTER_UNRESOLVED_PINS = frozenset({"floating"})


def _default_urlopen(url: str) -> Any:
    import urllib.request

    return urllib.request.urlopen(url, timeout=_DEFAULT_URL_TIMEOUT_SECONDS)


def _require_identity(value: Any, *, model: str, source: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise LookupError(f"{source} model {model!r} has no identity")
    return value


def _check_requested_pin(
    requested: str | None,
    *,
    produced: str,
    identity: str,
    unresolved: frozenset[str],
) -> None:
    """Accept an omitted pin, an unresolved pin, the produced level, or the identity."""
    if requested is None or requested in unresolved or requested == produced or requested == identity:
        return
    raise LookupError(
        f"requested pin {requested!r} does not match {produced} identity {identity!r}"
    )


def _fetch_json(urlopen: UrlOpen, url: str) -> Any:
    with urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


class OllamaResolver:
    """Resolve models against a local Ollama server (`/api/tags`).

    An installed model's digest serves as its snapshot identity.
    """

    def __init__(self, base_url: str = "http://localhost:11434", urlopen: UrlOpen = _default_urlopen):
        self._base = base_url.rstrip("/")
        self._urlopen = urlopen

    def resolve_model(self, name: str, provider: str | None = None, pin: str | None = None) -> dict[str, Any]:
        """Resolve `name` to pin `snapshot`, identified by the Ollama digest.

        `pin` may be omitted, `floating`, `alias`, `snapshot`, or the digest
        itself. Any other request raises LookupError. A missing or blank
        digest raises LookupError.
        """
        data = _fetch_json(self._urlopen, f"{self._base}/api/tags")
        for model in data.get("models", []):
            if model.get("name") == name:
                identity = _require_identity(model.get("digest"), model=name, source="Ollama")
                _check_requested_pin(
                    pin,
                    produced="snapshot",
                    identity=identity,
                    unresolved=_OLLAMA_UNRESOLVED_PINS,
                )
                return {
                    "name": name,
                    "provider": "ollama",
                    "pin": "snapshot",
                    "identity": identity,
                }
        raise LookupError(f"model {name!r} not found in Ollama")

    def resolve_tool_schema(self, name: str, version: str | None = None) -> dict[str, Any]:
        raise LookupError("Ollama provides no tool schemas")


class OpenRouterResolver:
    """Resolve models against the OpenRouter public model list.

    OpenRouter model ids are mutable aliases, so they resolve to `pin=alias`.
    """

    URL = "https://openrouter.ai/api/v1/models"

    def __init__(self, urlopen: UrlOpen = _default_urlopen):
        self._urlopen = urlopen

    def resolve_model(self, name: str, provider: str | None = None, pin: str | None = None) -> dict[str, Any]:
        """Resolve `name` to pin `alias`, identified by the OpenRouter model id.

        `pin` may be omitted, `floating`, `alias`, or the model id. A request
        for `snapshot`, `weights`, or any other string raises LookupError.
        """
        data = _fetch_json(self._urlopen, self.URL)
        for model in data.get("data", []):
            if model.get("id") == name:
                identity = _require_identity(model.get("id"), model=name, source="OpenRouter")
                _check_requested_pin(
                    pin,
                    produced="alias",
                    identity=identity,
                    unresolved=_OPENROUTER_UNRESOLVED_PINS,
                )
                return {
                    "name": name,
                    "provider": "openrouter",
                    "pin": "alias",
                    "identity": identity,
                }
        raise LookupError(f"model {name!r} not found in OpenRouter")

    def resolve_tool_schema(self, name: str, version: str | None = None) -> dict[str, Any]:
        raise LookupError("OpenRouter provides no tool schemas")
