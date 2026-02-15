"""
Run migration SQL against Supabase via the PostgREST rpc or direct HTTP.
Uses the Supabase Management API's SQL endpoint.

Usage:
    python -m scripts.run_migration
"""

import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

MIGRATION_FILE = os.path.join(
    os.path.dirname(__file__), "..", "supabase", "migrations", "001_initial_schema.sql"
)


def run_sql(sql: str) -> dict:
    """Execute SQL via Supabase's pg_net / REST SQL endpoint."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    # Try the rpc approach first (requires a helper function)
    # Fall back to executing statements one by one via postgrest
    response = httpx.post(url, json={"query": sql}, headers=headers, timeout=60)
    return {"status": response.status_code, "body": response.text}


def split_statements(sql: str) -> list[str]:
    """Split SQL into individual statements, handling multi-line statements."""
    statements = []
    current = []

    for line in sql.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []

    # Handle $$ delimited functions
    if current:
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)

    return statements


def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    if not os.path.exists(MIGRATION_FILE):
        print(f"Error: Migration file not found: {MIGRATION_FILE}")
        sys.exit(1)

    with open(MIGRATION_FILE, "r") as f:
        full_sql = f.read()

    print(f"Running migration against {SUPABASE_URL}")
    print(f"Migration file: {MIGRATION_FILE}")
    print(f"SQL length: {len(full_sql):,} characters")
    print()

    # Try executing the full SQL at once via the exec_sql rpc
    result = run_sql(full_sql)

    if result["status"] == 200:
        print("Migration executed successfully!")
    elif result["status"] == 404:
        print("exec_sql RPC not found. You need to run the migration manually.")
        print()
        print("Option 1: Supabase Dashboard SQL Editor")
        print("  1. Go to https://supabase.com/dashboard/project/qdhmhpmhbtlncncpnptq/sql")
        print("  2. Paste the contents of:")
        print(f"     {os.path.abspath(MIGRATION_FILE)}")
        print("  3. Click 'Run'")
        print()
        print("Option 2: Use psql directly")
        print("  psql 'postgresql://postgres:[PASSWORD]@db.qdhmhpmhbtlncncpnptq.supabase.co:5432/postgres' -f supabase/migrations/001_initial_schema.sql")
    else:
        print(f"Migration failed with status {result['status']}")
        print(f"Response: {result['body'][:500]}")
        print()
        print("Please run the migration manually via the Supabase SQL Editor:")
        print(f"  https://supabase.com/dashboard/project/qdhmhpmhbtlncncpnptq/sql")


if __name__ == "__main__":
    main()
