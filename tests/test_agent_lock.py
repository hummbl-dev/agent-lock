import copy
import unittest

from agent_lock.core import canonicalize, config_sha256, produce, verify


def _config() -> dict:
    return {
        "harness": "claude-code",
        "model": {"provider": "anthropic", "name": "claude-opus-4-6", "pin": "snapshot"},
        "goals": ["review PR"],
        "tools": [{"name": "gh", "version": "2.60.0"}],
        "permissions": ["repo:read"],
        "policy": {"network": "none"},
    }


class TestCanonicalize(unittest.TestCase):
    def test_key_order_irrelevant(self):
        self.assertEqual(canonicalize({"b": 1, "a": 2}), canonicalize({"a": 2, "b": 1}))

    def test_provenance_excluded(self):
        doc = _config()
        h = config_sha256(doc)
        doc["provenance"] = {"config_sha256": "x", "generated_by": "test"}
        self.assertEqual(config_sha256(doc), h)


class TestHash(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(config_sha256(_config()), config_sha256(_config()))

    def test_sensitive_to_change(self):
        a = _config()
        b = copy.deepcopy(a)
        b["model"]["pin"] = "floating"
        self.assertNotEqual(config_sha256(a), config_sha256(b))


class TestProduceVerify(unittest.TestCase):
    def test_produce_adds_provenance_and_verifies(self):
        doc = produce(_config(), generated_by="test")
        self.assertIn("provenance", doc)
        self.assertTrue(verify(doc))

    def test_tamper_detected(self):
        doc = produce(_config(), generated_by="test")
        doc["model"]["pin"] = "floating"
        self.assertFalse(verify(doc))

    def test_produce_does_not_mutate_input(self):
        cfg = _config()
        produce(cfg, generated_by="test")
        self.assertNotIn("provenance", cfg)


if __name__ == "__main__":
    unittest.main()
