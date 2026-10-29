import unittest

from agent_lock import FileRegistry, pin_issues, resolve, tool_issues, verify

REGISTRY = {
    "models": {
        "claude-opus-4-6": {"provider": "anthropic", "pin": "snapshot", "identity": "opus-4-6-20261028"},
    },
    "tools": {
        "gh": {"schema": {"type": "object", "properties": {"repo": {"type": "string"}}}},
    },
}


def _config() -> dict:
    return {
        "harness": "claude-code",
        "model": {"provider": "anthropic", "name": "claude-opus-4-6", "pin": "alias"},
        "tools": [{"name": "gh", "version": "2.60.0"}],
    }


class TestFileRegistry(unittest.TestCase):
    def test_resolve_model(self):
        r = FileRegistry(REGISTRY).resolve_model("claude-opus-4-6", "anthropic", "alias")
        self.assertEqual(r["pin"], "snapshot")
        self.assertIn("identity", r)

    def test_resolve_tool_schema(self):
        self.assertIn("properties", FileRegistry(REGISTRY).resolve_tool_schema("gh"))

    def test_unknown_model_raises(self):
        with self.assertRaises(LookupError):
            FileRegistry(REGISTRY).resolve_model("nope")

    def test_unknown_tool_raises(self):
        with self.assertRaises(LookupError):
            FileRegistry(REGISTRY).resolve_tool_schema("nope")


class TestResolve(unittest.TestCase):
    def test_resolve_pins_model_and_tool(self):
        doc = resolve(_config(), FileRegistry(REGISTRY), generated_by="test")
        self.assertEqual(doc["model"]["pin"], "snapshot")
        self.assertIn("schema_sha256", doc["tools"][0])
        self.assertTrue(verify(doc))
        self.assertEqual(pin_issues(doc), [])
        self.assertEqual(tool_issues(doc), [])

    def test_resolve_raises_on_unknown_model(self):
        cfg = _config()
        cfg["model"]["name"] = "unknown-model"
        with self.assertRaises(LookupError):
            resolve(cfg, FileRegistry(REGISTRY), generated_by="test")

    def test_resolve_leaves_unknown_tool_flagged(self):
        cfg = _config()
        cfg["tools"].append({"name": "mystery-tool", "version": "1.0"})
        doc = resolve(cfg, FileRegistry(REGISTRY), generated_by="test")
        self.assertTrue(any("mystery-tool" in e for e in tool_issues(doc)))


if __name__ == "__main__":
    unittest.main()
