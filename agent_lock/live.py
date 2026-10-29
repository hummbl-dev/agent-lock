"""Adapters that map live hosted model-catalog APIs to the Resolver protocol.

These are the "live registry sources": instead of a static JSON file, they query
a running model catalog and map its response onto `resolve_model`. Network I/O is
injected (`urlopen`) so the adapters are testable without a live endpoint.
"""

from __future__ import annotations

import json
from typing import Any, Callable

UrlOpen = Callable[[str], Any]


def _default_urlopen(url: str) -> Any:
    import urllib.request

    return urllib.request.urlopen(url)


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
        data = _fetch_json(self._urlopen, f"{self._base}/api/tags")
        for model in data.get("models", []):
            if model.get("name") == name:
                return {
                    "name": name,
                    "provider": "ollama",
                    "pin": "snapshot",
                    "identity": model.get("digest", ""),
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
        data = _fetch_json(self._urlopen, self.URL)
        for model in data.get("data", []):
            if model.get("id") == name:
                return {
                    "name": name,
                    "provider": "openrouter",
                    "pin": "alias",
                    "identity": model.get("id"),
                }
        raise LookupError(f"model {name!r} not found in OpenRouter")

    def resolve_tool_schema(self, name: str, version: str | None = None) -> dict[str, Any]:
        raise LookupError("OpenRouter provides no tool schemas")
