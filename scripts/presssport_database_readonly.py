#!/usr/bin/env python3
"""Read-only PostgreSQL connector for cloud publication preflight.

No database writes or Meta API calls. Requires a server-side connection string.
"""
import os

def inspect_publication_ledger(connect, database_url):
    if not database_url:
        raise ValueError("database connection string required")
    connection = connect(database_url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("BEGIN READ ONLY")
            cursor.execute("SELECT count(*) FROM presssport_internal.publication_reservations")
            row = cursor.fetchone()
            cursor.execute("ROLLBACK")
        if not row or not isinstance(row[0], int):
            raise RuntimeError("invalid ledger response")
        return {"ledger_accessible": True, "reservation_count": row[0],
                "publication_performed": False}
    finally:
        connection.close()

def main():
    import psycopg
    result = inspect_publication_ledger(psycopg.connect, os.environ.get("PRESSSPORT_DATABASE_URL"))
    print("PASS: private publication ledger accessible")
    print("Reservations:", result["reservation_count"])
    print("PUBLICATION: NOT PERFORMED")

if __name__ == "__main__":
    main()
