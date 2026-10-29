#!/usr/bin/env python3
"""Read-only Supabase ledger diagnostic for interrupted or uncertain publication.

Never changes publication states and never contacts Meta. A 'publishing' row
may represent a process crash: flag for manual review, never retry POST.
"""
import os
from datetime import datetime, timezone
from scripts.presssport_recovery_triage import recovery_report

QUERY = """
SELECT state, reconciliation_required, updated_at, publication_key
FROM presssport_internal.publication_reservations
ORDER BY updated_at DESC
"""

def inspect_ledger(connect, database_url, *, now=None, stale_minutes=15):
    if not database_url:
        raise ValueError("database connection string required")
    if not isinstance(stale_minutes, int) or isinstance(stale_minutes, bool) or stale_minutes < 1:
        raise ValueError("invalid stale threshold")
    now = now or datetime.now(timezone.utc)
    connection = connect(database_url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("BEGIN READ ONLY")
            cursor.execute(QUERY)
            rows = cursor.fetchall()
            cursor.execute("ROLLBACK")
        counts = {}
        review = []
        for state, reconciliation_required, updated_at, publication_key in rows:
            counts[state] = counts.get(state, 0) + 1
            if updated_at is None or updated_at.tzinfo is None:
                raise RuntimeError("invalid ledger timestamp")
            age_seconds = (now - updated_at).total_seconds()
            stale_publishing = state == "publishing" and age_seconds >= stale_minutes * 60
            if state == "uncertain" or reconciliation_required or stale_publishing:
                review.append({
                    "publication_key": publication_key,
                    "state": state,
                    "reconciliation_required": bool(reconciliation_required),
                    "stale_publishing": stale_publishing,
                })
        return {"counts": counts, "review": review, "total": len(rows)}
    finally:
        connection.close()

def main():
    import psycopg
    result = inspect_ledger(psycopg.connect, os.environ.get("PRESSSPORT_DATABASE_URL"))
    print("LEDGER ROWS:", result["total"])
    for state, count in sorted(result["counts"].items()):
        print("STATE", state, count)
    print("REQUIRING MANUAL REVIEW:", len(result["review"]))
    for entry in result["review"]:
        # Avoid printing tokens, personal data or Meta IDs.
        print("REVIEW", entry["publication_key"], entry["state"],
              "stale=", entry["stale_publishing"])
    for decision in recovery_report(result["review"]):
        print("RECOVERY", decision["publication_key"], decision["action"], decision["reason"])
    print("READ ONLY: YES; META POST: NONE; AUTOMATIC RETRIES: NONE")

if __name__ == "__main__":
    main()
