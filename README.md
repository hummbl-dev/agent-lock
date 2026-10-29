# agent-lock

Producer for **hash-addressed agent configuration lockfiles** — the companion
to the [`acve`](https://github.com/hummbl-dev/acve) registry. acve *validates*
and *matches* lockfiles; this package *produces* them.

A lockfile pins a resolved agent configuration (harness + model + goals + tools
+ permissions + policy) to a deterministic unit identity:
`provenance.config_sha256`, the SHA-256 of the RFC 8785 (JCS) canonicalization
of the document with `provenance` excluded.

## Install / run

```bash
python -m agent_lock produce config.json -o agent-lock.json
python -m agent_lock verify agent-lock.json
python -m agent_lock hash config.json
```

Or `pip install .` to get the `agent-lock` console script. The `lock` API pins
tool `schema_sha256` values and records model pins; `pins.pin_issues` reports
what is still unresolved.

## Status

v0.1 — canonicalization, hashing, produce, verify, `lock` (tool schema pinning),
and model-pin validation. Real *resolution* (resolving model alias/floating
pins and tool schemas from registries) is the next gap to close.

## License

MIT.
