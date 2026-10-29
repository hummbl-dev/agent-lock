import unittest

from agent_lock import lock, pin_issues, schema_sha256, valid_pin, is_resolved


def _config() -> dict:
    return {
        "harness": "claude-code",
        "model": {"provider": "anthropic", "name": "claude-opus-4-6", "pin": "snapshot"},
        "tools": [
            {"name": "gh", "version": "2.60.0", "schema": {"type": "object", "properties": {"repo": {"type": "string"}}}},
        ],
    }


class TestSchemaSha256(unittest.TestCase):
    def test_deterministic(self):
        s = {"type": "object", "properties": {"a": {"type": "string"}}}
        self.assertEqual(schema_sha256(s), schema_sha256(s))

    def test_key_order_irrelevant(self):
        a = {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "integer"}}}
        b = {"type": "object", "properties": {"b": {"type": "integer"}, "a": {"type": "string"}}}
        self.assertEqual(schema_sha256(a), schema_sha256(b))


class TestLock(unittest.TestCase):
    def test_lock_pins_tool_schema(self):
        doc = lock(_config(), generated_by="test")
        self.assertEqual(doc["tools"][0]["schema_sha256"], schema_sha256(_config()["tools"][0]["schema"]))

    def test_lock_overrides_stale_schema_sha256(self):
        cfg = _config()
        cfg["tools"][0]["schema_sha256"] = "deadbeef"
        doc = lock(cfg, generated_by="test")
        self.assertEqual(doc["tools"][0]["schema_sha256"], schema_sha256(cfg["tools"][0]["schema"]))

    def test_lock_verifies(self):
        from agent_lock import verify
        self.assertTrue(verify(lock(_config(), generated_by="test")))


class TestPins(unittest.TestCase):
    def test_valid_pin_levels(self):
        for p in ("weights", "snapshot", "alias", "floating"):
            self.assertTrue(valid_pin(p))
        self.assertFalse(valid_pin("nonsense"))

    def test_resolved(self):
        self.assertTrue(is_resolved("weights"))
        self.assertTrue(is_resolved("snapshot"))
        self.assertFalse(is_resolved("alias"))
        self.assertFalse(is_resolved("floating"))

    def test_pin_issues_clean_for_snapshot(self):
        self.assertEqual(pin_issues(_config()), [])

    def test_pin_issues_flags_floating(self):
        cfg = _config()
        cfg["model"]["pin"] = "floating"
        self.assertTrue(any("unresolved" in e for e in pin_issues(cfg)))

    def test_pin_issues_flags_missing(self):
        cfg = _config()
        del cfg["model"]["pin"]
        self.assertTrue(any("missing" in e for e in pin_issues(cfg)))


if __name__ == "__main__":
    unittest.main()
