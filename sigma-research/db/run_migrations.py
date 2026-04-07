"""
Run Supabase schema migrations.

Usage: python -m db.run_migrations
       python db/run_migrations.py

Applies all SQL in db/migrations/ to the Supabase project.
Uses the SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from .env.
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from db.supabase_client import SupabaseClient

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def run_migrations() -> None:
    client = SupabaseClient()

    if not client.is_available:
        print("ERROR: Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        return

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("No migration files found.")
        return

    print(f"Applying {len(migration_files)} migration(s) to {client._url}...")

    for migration_file in migration_files:
        sql = migration_file.read_text(encoding="utf-8")
        print(f"  -> {migration_file.name} ... ", end="", flush=True)
        try:
            client.client.postgrest.session.post(
                f"{client._url}/rest/v1/rpc/exec_sql",
                headers={
                    "apikey": client._key,
                    "Authorization": f"Bearer {client._key}",
                    "Content-Type": "application/json",
                },
                json={"sql": sql},
            )
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")


if __name__ == "__main__":
    run_migrations()
