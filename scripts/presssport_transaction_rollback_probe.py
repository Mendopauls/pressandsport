#!/usr/bin/env python3
"""Test real Supabase reservation and CAS transaction semantics; ALWAYS roll back.

No Meta calls. No commit. Synthetic reservation key never references a real post.
"""
import os
import uuid

TABLE = "presssport_internal.publication_reservations"

def probe_transactions(connect, database_url):
    if not database_url:
        raise ValueError("database connection string required")
    marker = "cloud-probe-" + uuid.uuid4().hex
    attempt = str(uuid.uuid4())
    conn = connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '10000ms'")
            cur.execute("SET LOCAL lock_timeout = '3000ms'")
            cur.execute(
                f"INSERT INTO {TABLE} "
                "(publication_key, instagram_account_id, manifest_sha256, attempt_id) "
                "VALUES (%s,%s,%s,%s) RETURNING state",
                (marker, "synthetic-probe-not-an-account", "0"*64, attempt))
            if cur.fetchone()[0] != "reserved":
                raise RuntimeError("unexpected initial reservation state")
            cur.execute("SAVEPOINT duplicate_probe")
            duplicate_rejected = False
            try:
                cur.execute(
                    f"INSERT INTO {TABLE} "
                    "(publication_key, instagram_account_id, manifest_sha256, attempt_id) "
                    "VALUES (%s,%s,%s,%s)",
                    (marker, "synthetic-probe-not-an-account", "0"*64, str(uuid.uuid4())))
            except Exception as exc:
                # Only the PostgreSQL unique-violation error proves duplicate blocking.
                if getattr(exc, "sqlstate", None) != "23505":
                    raise
                duplicate_rejected = True
            finally:
                cur.execute("ROLLBACK TO SAVEPOINT duplicate_probe")
            if not duplicate_rejected:
                raise RuntimeError("duplicate reservation was not rejected")
            cur.execute(
                f"UPDATE {TABLE} SET state=%s, updated_at=now() "
                "WHERE publication_key=%s AND attempt_id=%s AND state=%s "
                "RETURNING state",
                ("publishing", marker, attempt, "reserved"))
            if cur.fetchone() != ("publishing",):
                raise RuntimeError("reserved-to-publishing transition failed")
            cur.execute(
                f"UPDATE {TABLE} SET state=%s "
                "WHERE publication_key=%s AND attempt_id=%s AND state=%s "
                "RETURNING state",
                ("published", marker, attempt, "reserved"))
            if cur.fetchone() is not None:
                raise RuntimeError("stale compare-and-swap transition unexpectedly succeeded")
        return {"duplicate_rejected": True, "cas_transition": True,
                "stale_transition_rejected": True, "committed": False}
    finally:
        # Never commit, even on errors.
        try:
            conn.rollback()
        finally:
            conn.close()

def main():
    import psycopg
    result = probe_transactions(psycopg.connect, os.environ.get("PRESSSPORT_DATABASE_URL"))
    if not all((result["duplicate_rejected"], result["cas_transition"],
                result["stale_transition_rejected"])):
        raise SystemExit("FAIL: transaction probe")
    print("PASS: duplicate key rejected")
    print("PASS: compare-and-swap state transition")
    print("PASS: stale transition rejected")
    print("PASS: entire synthetic transaction rolled back")
    print("META CALLS: NONE; PUBLISHED POSTS: NONE")

if __name__ == "__main__":
    main()
