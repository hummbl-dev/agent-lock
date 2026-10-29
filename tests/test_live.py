import json
import unittest
from unittest.mock import patch

from agent_lock import OllamaResolver, OpenRouterResolver, resolve, verify
from agent_lock.live import _DEFAULT_URL_TIMEOUT_SECONDS, _default_urlopen

OLLAMA_RESPONSE = {
    "models": [
        {"name": "qwen3:8b", "digest": "sha256:abcdef"},
        {"name": "llama3:latest", "digest": "sha256:123456"},
    ]
}

OPENROUTER_RESPONSE = {
    "data": [
        {"id": "anthropic/claude-opus-4-6"},
        {"id": "openai/gpt-5.5"},
    ]
}


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def read(self):
        return json.dumps(self._data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_urlopen(data):
    def f(url):
        return _FakeResp(data)

    return f


class TestOllamaResolver(unittest.TestCase):
    def test_resolve_model_snapshot(self):
        r = OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE))
        resolved = r.resolve_model("qwen3:8b")
        self.assertEqual(resolved["pin"], "snapshot")
        self.assertEqual(resolved["identity"], "sha256:abcdef")

    def test_missing_model_raises(self):
        r = OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE))
        with self.assertRaises(LookupError):
            r.resolve_model("nope")

    def test_no_tool_schemas(self):
        r = OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE))
        with self.assertRaises(LookupError):
            r.resolve_tool_schema("gh")

    def test_empty_digest_raises(self):
        for digest in ("", "   ", None):
            data = {"models": [{"name": "qwen3:8b", "digest": digest}]}
            r = OllamaResolver(urlopen=_fake_urlopen(data))
            with self.assertRaises(LookupError):
                r.resolve_model("qwen3:8b")

    def test_missing_digest_raises(self):
        data = {"models": [{"name": "qwen3:8b"}]}
        r = OllamaResolver(urlopen=_fake_urlopen(data))
        with self.assertRaises(LookupError):
            r.resolve_model("qwen3:8b")

    def test_requested_digest_matches(self):
        r = OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE))
        resolved = r.resolve_model("qwen3:8b", pin="sha256:abcdef")
        self.assertEqual(resolved["pin"], "snapshot")
        self.assertEqual(resolved["identity"], "sha256:abcdef")

    def test_requested_digest_mismatch_raises(self):
        r = OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE))
        with self.assertRaises(LookupError):
            r.resolve_model("qwen3:8b", pin="sha256:other")

    def test_unresolved_pin_upgrades_to_snapshot(self):
        r = OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE))
        for pin in ("floating", "alias", "snapshot"):
            resolved = r.resolve_model("qwen3:8b", pin=pin)
            self.assertEqual(resolved["pin"], "snapshot")
            self.assertEqual(resolved["identity"], "sha256:abcdef")

    def test_weights_pin_raises(self):
        r = OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE))
        with self.assertRaises(LookupError):
            r.resolve_model("qwen3:8b", pin="weights")


class TestOpenRouterResolver(unittest.TestCase):
    def test_resolve_model_alias(self):
        r = OpenRouterResolver(urlopen=_fake_urlopen(OPENROUTER_RESPONSE))
        resolved = r.resolve_model("openai/gpt-5.5")
        self.assertEqual(resolved["pin"], "alias")

    def test_missing_model_raises(self):
        r = OpenRouterResolver(urlopen=_fake_urlopen(OPENROUTER_RESPONSE))
        with self.assertRaises(LookupError):
            r.resolve_model("nope")

    def test_requested_id_matches(self):
        r = OpenRouterResolver(urlopen=_fake_urlopen(OPENROUTER_RESPONSE))
        resolved = r.resolve_model("openai/gpt-5.5", pin="openai/gpt-5.5")
        self.assertEqual(resolved["pin"], "alias")
        self.assertEqual(resolved["identity"], "openai/gpt-5.5")

    def test_snapshot_pin_raises(self):
        r = OpenRouterResolver(urlopen=_fake_urlopen(OPENROUTER_RESPONSE))
        with self.assertRaises(LookupError):
            r.resolve_model("openai/gpt-5.5", pin="snapshot")

    def test_other_pin_raises(self):
        r = OpenRouterResolver(urlopen=_fake_urlopen(OPENROUTER_RESPONSE))
        with self.assertRaises(LookupError):
            r.resolve_model("openai/gpt-5.5", pin="sha256:not-an-id")


class TestResolveWithLiveSource(unittest.TestCase):
    def test_resolve_ollama_model(self):
        config = {
            "harness": "ollama-cli",
            "model": {"name": "qwen3:8b", "pin": "floating"},
            "tools": [],
        }
        doc = resolve(config, OllamaResolver(urlopen=_fake_urlopen(OLLAMA_RESPONSE)), generated_by="test")
        self.assertEqual(doc["model"]["pin"], "snapshot")
        self.assertTrue(verify(doc))


class TestDefaultUrlOpen(unittest.TestCase):
    def test_timeout_is_passed(self):
        with patch("urllib.request.urlopen") as opener:
            opener.return_value = _FakeResp({})
            _default_urlopen("http://catalog.test/models")
        opener.assert_called_once_with(
            "http://catalog.test/models",
            timeout=_DEFAULT_URL_TIMEOUT_SECONDS,
        )


if __name__ == "__main__":
    unittest.main()
