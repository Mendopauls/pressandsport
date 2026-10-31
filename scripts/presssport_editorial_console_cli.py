"""Private operator-only CLI for Press & Sport Cloud multichannel drafts.

Runs locally, needs psycopg and PRESSSPORT_DATABASE_URL in operator environment.
This tool CANNOT publish. Never run from a publicly exposed web process.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from scripts.presssport_multichannel_queue import insert_draft, move_state, list_queue

def parser():
    p = argparse.ArgumentParser(description="Press & Sport editorial console (no publishing)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    add = sub.add_parser("draft")
    for key in ("post-key", "kind", "account-id", "caption", "images-json"):
        add.add_argument("--" + key, required=True)
    move = sub.add_parser("transition")
    for key in ("post-key", "from-state", "to-state"):
        move.add_argument("--" + key, required=True)
    move.add_argument("--planned-at", help="ISO-8601 timezone-aware timestamp")
    return p

def run(args, connection):
    if args.command == "list":
        return list_queue(connection)
    if args.command == "draft":
        urls = json.loads(args.images_json)
        return insert_draft(connection, post_key=args.post_key, kind=args.kind,
                            account_id=args.account_id, caption=args.caption,
                            image_urls=urls)
    if args.command == "transition":
        planned_at = datetime.fromisoformat(args.planned_at) if args.planned_at else None
        return move_state(connection, post_key=args.post_key,
                          from_state=args.from_state, to_state=args.to_state,
                          operator="Paolo Savio", planned_at=planned_at)
    raise ValueError("unknown command")

def main(argv=None):
    args = parser().parse_args(argv)
    dsn = os.environ.get("PRESSSPORT_DATABASE_URL")
    if not dsn:
        raise SystemExit("PRESSSPORT_DATABASE_URL missing; no database accessed")
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Install psycopg in your isolated operator environment") from exc
    # Operators must have legitimate access to the internal database role.
    # The database itself enforces RLS and immutable editorial states.
    with psycopg.connect(dsn, connect_timeout=8) as conn:
        result = run(args, conn)
        conn.commit()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0

if __name__ == "__main__":
    sys.exit(main())
