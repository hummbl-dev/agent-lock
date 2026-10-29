"""agent-lock CLI: produce and verify hash-addressed lockfiles.

    python -m agent_lock produce <config.json> [-o lock.json] [--generated-by X]
    python -m agent_lock verify <lockfile.json>
    python -m agent_lock hash <config.json>
"""

import argparse
import json
import sys
from pathlib import Path

from .core import config_sha256, produce, verify


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_produce(args) -> int:
    doc = produce(_load(args.config), generated_by=args.generated_by, environment=args.environment)
    text = json.dumps(doc, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_verify(args) -> int:
    doc = _load(args.lockfile)
    ok = verify(doc)
    print(f"{'VERIFIED' if ok else 'MISMATCH'}: {args.lockfile}")
    return 0 if ok else 1


def cmd_hash(args) -> int:
    print(config_sha256(_load(args.config)))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agent-lock", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("produce", help="produce a lockfile from a resolved config")
    p.add_argument("config")
    p.add_argument("-o", "--out")
    p.add_argument("--generated-by", default="agent-lock")
    p.add_argument("--environment")
    p.set_defaults(fn=cmd_produce)

    v = sub.add_parser("verify", help="verify provenance.config_sha256")
    v.add_argument("lockfile")
    v.set_defaults(fn=cmd_verify)

    h = sub.add_parser("hash", help="print config_sha256 for a config")
    h.add_argument("config")
    h.set_defaults(fn=cmd_hash)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
