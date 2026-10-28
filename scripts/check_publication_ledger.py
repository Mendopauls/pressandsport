#!/usr/bin/env python3
"""Read-only duplicate publication guard; no Meta calls or file writes."""
import argparse
import json
import sys
from pathlib import Path
from publication_ledger_state import duplicate_blockers

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="publishing/presssport-2026-10-28.json")
    parser.add_argument("--ledger", default="publishing/publication-ledger.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    problems = duplicate_blockers(manifest, ledger)
    if problems:
        for problem in problems:
            print("BLOCKED:", problem)
        return 1
    print("PASS: no matching entry in versioned publication ledger")
    print("NOTE: read-only check; not an atomic lock and not sufficient alone to prevent duplicates")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("BLOCKED: ledger or manifest invalid:", type(exc).__name__)
        sys.exit(1)
