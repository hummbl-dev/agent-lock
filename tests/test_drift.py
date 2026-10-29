import json
import os
import tempfile
import unittest
from pathlib import Path

from agent_lock import CompositeResolver, FileRegistry, UrlRegistry, drift, lock, resolve

REGISTRY = {
    "models": {"claude-opus-4-6": {"provider": "anthropic", "pin": "snapshot", "identity": "i1"}},
    "tools": {"gh": {"schema": {"type": "object", "properties": {"repo": {"type": "string"}}}}},
}


def _config() -> dict:
    return {
        "harness": "claude-code",
        "model": {"provider": "anthropic", "name": "claude-opus-4-6", "pin": "snapshot", "identity": "i1"},
        "tools": [{"name": "gh", "version": "2.60.0", "schema": REGISTRY["tools"]["gh"]["schema"]}],
    }


class TestDrift(unittest.TestCase):
    def test_no_drift(self):
        lockfile = lock(_config(), generated_by="test")
        self.assertEqual(drift(lockfile, _config()), [])

    def test_tool_version_drift(self):
        lockfile = lock(_config(), generated_by="test")
        live = _config()
        live["tools"][0]["version"] = "2.99.0"
        self.assertTrue(any("version" in f for f in drift(lockfile, live)))

    def test_tool_schema_drift(self):
        lockfile = lock(_config(), generated_by="test")
        live = _config()
        live["tools"][0]["schema"] = {"type": "object", "properties": {"other": {"type": "integer"}}}
        self.assertTrue(any("schema hash" in f for f in drift(lockfile, live)))

    def test_model_pin_drift(self):
        lockfile = lock(_config(), generated_by="test")
        live = _config()
        live["model"]["pin"] = "alias"
        self.assertTrue(any("model pin" in f for f in drift(lockfile, live)))

    def test_new_tool_present_in_live(self):
        lockfile = lock(_config(), generated_by="test")
        live = _config()
        live["tools"].append({"name": "extra", "version": "1.0", "schema": {"type": "object"}})
        self.assertTrue(any("absent from lockfile" in f for f in drift(lockfile, live)))

    def test_drift_resolves_schema_from_resolver(self):
        lockfile = lock(_config(), generated_by="test")
        live = _config()
        del live["tools"][0]["schema"]  # schema-less; resolver fetches it
        self.assertEqual(drift(lockfile, live, resolver=FileRegistry(REGISTRY)), [])


class TestUrlRegistry(unittest.TestCase):
    def test_load_file_url(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "reg.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(REGISTRY, fh)
            reg = UrlRegistry.load(Path(path).as_uri())
            self.assertEqual(reg.resolve_model("claude-opus-4-6")["pin"], "snapshot")


class TestCompositeResolver(unittest.TestCase):
    def test_fallback(self):
        empty = FileRegistry({"models": {}, "tools": {}})
        full = FileRegistry(REGISTRY)
        comp = CompositeResolver([empty, full])
        self.assertEqual(comp.resolve_model("claude-opus-4-6")["pin"], "snapshot")

    def test_all_miss_raises(self):
        comp = CompositeResolver([FileRegistry({"models": {}, "tools": {}})])
        with self.assertRaises(LookupError):
            comp.resolve_model("nope")


if __name__ == "__main__":
    unittest.main()
