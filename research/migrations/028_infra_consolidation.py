"""
Migration 028 — research-infra consolidation (LdP + Carver + AQR), task 96.

The single, one-shot schema migration that closes the wisdom-gathering phase
(META-001 dissects of López de Prado, Carver, AQR). Sequenced AFTER all three
authorities were dissected and BEFORE the code-wiring tasks (87–93) so the DB is
migrated exactly once. ADR:
  docs/specs/2026-06-15-research-infra-consolidation-ldp-carver-aqr.md

Two additive changes, both idempotent (no rebuild, no data loss):

1. NEW TABLE `trial_family` — the N_trials ledger. Closes the headline gap: our
   Gate-5 "DSR" silently runs as PSR because nothing supplies N + V[SR_n]
   (gate5_report.dsr() degrades to psr(sr_benchmark=0) when var_sr/n_trials are
   None). A family row records, per selection decision, how many configs were
   tried (n_configs = N) and the variance of their per-period Sharpes
   (var_sr = V[SR_n]). Scope is PER-IDEA — one family per sweep, never pooled
   across strategies. Each swept config logs a step4_results row tagged with the
   same trial_family_id; var_sr is computed from that family and cached here.

2. step4_results gains 3 columns:
   - config_hash : identifies each swept config (links a result row to its family
                   and lets the ledger count distinct trials / name the winner).
   - cost_bps    : AQR measure-don't-model — realized cost in bps (B-book
                   half-spread + IS-minus-MI slippage), not a borrowed impact model.
   - cost_basis  : 'measured' | 'modeled' — flags which discipline produced cost.

Run: python research/migrations/028_infra_consolidation.py
"""
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "research.db"
MYT = timezone(timedelta(hours=8))


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    now = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")

    # ── 1. trial_family ledger ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trial_family (
            family_id            TEXT PRIMARY KEY,
            idea_id              TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            description          TEXT,
            n_configs            INTEGER NOT NULL DEFAULT 0,
            var_sr               REAL,
            selected_config_hash TEXT,
            data_start           DATE,
            data_end             DATE,
            created_at           DATETIME NOT NULL,
            updated_at           DATETIME NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trial_family_idea
            ON trial_family(idea_id, created_at)
    """)

    # ── 2. step4_results additive columns ───────────────────────────────────
    cols = [r[1] for r in cur.execute("PRAGMA table_info(step4_results)")]
    adds = {
        "config_hash": "ALTER TABLE step4_results ADD COLUMN config_hash TEXT",
        "cost_bps":    "ALTER TABLE step4_results ADD COLUMN cost_bps REAL",
        # CHECK can't be added via ALTER on sqlite; enforce 'measured'|'modeled' in code layer.
        "cost_basis":  "ALTER TABLE step4_results ADD COLUMN cost_basis TEXT",
    }
    added = []
    for col, ddl in adds.items():
        if col not in cols:
            cur.execute(ddl)
            added.append(col)

    conn.commit()

    # ── verify ──────────────────────────────────────────────────────────────
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    new_cols = [r[1] for r in cur.execute("PRAGMA table_info(step4_results)")]
    print(f"  trial_family present       : {'trial_family' in tables}")
    print(f"  step4_results cols added   : {added or '(already present)'}")
    print(f"  config_hash/cost_bps/basis : "
          f"{all(c in new_cols for c in ('config_hash','cost_bps','cost_basis'))}")
    assert "trial_family" in tables
    assert all(c in new_cols for c in ("config_hash", "cost_bps", "cost_basis"))
    conn.close()
    print("migration 028 complete")


if __name__ == "__main__":
    main()
