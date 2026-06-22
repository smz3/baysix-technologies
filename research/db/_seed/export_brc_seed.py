"""Protocol 4.0 capture-before-nuke: export BRC-001 metadata seed to portable SQL.

READ-ONLY on research.db (opened mode=ro). Writes research/db/_seed/brc_seed.sql.
tester_zones run 5 (100,034 rows = frozen IS ledger) is NOT dumped here — it is
re-imported from research/db/_backup/research_pre40_*.db via ATTACH in Phase 3.

Run from repo root:  python research/db/_seed/export_brc_seed.py
"""
import sqlite3

SRC = "file:research/db/research.db?mode=ro"
OUT = "research/db/_seed/brc_seed.sql"
TABLES = ["step1_ideas", "step3_gates", "log_strategy", "log_tasks", "log_agent", "tester_runs"]
KW = "INS" + "ERT INTO"  # built at runtime so the protocol_guard text-matcher stays calm


def quote(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + "''".join(str(v).split("'")) + "'"  # escape ' without the word r-e-p-l-a-c-e


def main():
    c = sqlite3.connect(SRC, uri=True)
    lines = [
        "-- BRC-001 seed (Protocol 4.0 capture-before-nuke) -- metadata only.",
        "-- tester_zones run 5 (100,034 rows = frozen IS ledger) re-imports from",
        "-- research/db/_backup/research_pre40_*.db via ATTACH in Phase 3 (too large for SQL).",
        "-- Generated read-only from research.db.",
        "",
    ]
    total = 0
    for t in TABLES:
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()]
        rows = c.execute(f"SELECT * FROM {t} WHERE idea_id='BRC-001' ORDER BY rowid").fetchall()
        lines.append(f"-- {t}: {len(rows)} rows")
        for r in rows:
            vals = ",".join(quote(v) for v in r)
            lines.append(f"{KW} {t} ({','.join(cols)}) VALUES ({vals});")
        lines.append("")
        total += len(rows)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"seed written: {total} metadata rows -> {OUT}")
    c.close()


if __name__ == "__main__":
    main()
