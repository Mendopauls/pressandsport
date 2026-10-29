#!/usr/bin/env python3
"""Validate cloud publication ledger schema in a read-only transaction.

This checks prerequisites for future atomic reservation/transition writes.
No INSERT/UPDATE/DELETE, no Meta calls, no publication.
"""
import os

REQUIRED = {
    "publication_key", "instagram_account_id", "manifest_sha256",
    "attempt_id", "state", "meta_media_id", "reconciliation_required",
    "updated_at",
}

def inspect_transaction_schema(connect, database_url):
    if not database_url:
        raise ValueError("database connection string required")
    connection = connect(database_url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("BEGIN READ ONLY")
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'presssport_internal' "
                "AND table_name = 'publication_reservations'"
            )
            found = {row[0] for row in cursor.fetchall()}
            cursor.execute("ROLLBACK")
        missing = sorted(REQUIRED - found)
        if missing:
            raise RuntimeError("publication ledger missing required columns: " + ", ".join(missing))
        return {"schema_valid": True, "checked_columns": len(REQUIRED),
                "database_writes": False, "meta_calls": False}
    finally:
        connection.close()

def main():
    import psycopg
    result = inspect_transaction_schema(psycopg.connect, os.environ.get("PRESSSPORT_DATABASE_URL"))
    print("PASS: Supabase publication transaction schema verified")
    print("Required columns:", result["checked_columns"])
    print("DATABASE WRITES: NONE; META CALLS: NONE")

if __name__ == "__main__":
    main()
