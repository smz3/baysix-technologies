"""
Migration 013 — create step6_backlog (via db_init) and seed the initial follow-ups.
Additive + idempotent: re-running does not duplicate seeds (guards on empty table).

Run: python research/migrations/013_create_backlog.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import db_init, backlog
import sqlite3

SEEDS = [
    ("ORB equity sim — Mode B fixed-fractional / compounding sizing",
     "sizing", "P1", "ORB-001",
     "Risk a % of current equity, round to lot_step 0.01, compound. Compare equity curve vs Mode A (min-lot)."),
    ("ORB %/ATR survival filter — productionise the winning cap",
     "filter", "P1", "ORB-001",
     "Turn the swept survival cap into a reusable filter; ATR-relative variant alongside %-of-equity."),
    ("ORB-002 — NY-session ORB",
     "variant", "P1", "ORB-001",
     "Own idea, parent_idea_id=ORB-001. RE-ANSWER Gate 0 (NY-open fires into London afternoon, different liquidity regime). Inherit G1, quick G2, full re-run G3/5/6."),
    ("ORB-001 MQL5 port into Sigma EA (live XAUUSD)",
     "port", "P2", "ORB-001",
     "Port frozen London config (08:00 UTC anchor, N=5, 3R/1R, 21:00 flat) into Sigma EA after survival filter is set."),
    ("ORB-001 regime gate (Gate 4 attempt 2) — trend/session filter",
     "filter", "P2", "ORB-001",
     "Trade only when regime favours the 3R bet; addresses OOS regime-dependence flagged at G6."),
    ("Rename ORB-001 'London -> NY' to 'London' in step1_ideas",
     "cleanup", "P2", "ORB-001",
     "Current name 'Opening-Range Breakout (London -> NY) - XAUUSD' is misleading; only London validated. NY split to ORB-002."),
]


def main():
    db_init.init()  # ensures step6_backlog exists
    conn = sqlite3.connect(db_init.DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM step6_backlog").fetchone()[0]
    conn.close()
    if n > 0:
        print(f"step6_backlog already has {n} rows — skipping seed.")
        return
    for title, kind, priority, idea_id, detail in SEEDS:
        backlog.add_task(title, kind=kind, detail=detail, idea_id=idea_id, priority=priority)
    print(f"seeded {len(SEEDS)} backlog tasks.")


if __name__ == "__main__":
    main()
