"""Migration 032 — Protocol 4.0 lean DB rebuild (BRC-only).

Nukes the 3.2/3.3 research.db and rebuilds it on the lean 4.0 schema (db_init),
porting ONLY the active idea (BRC-001 + its STRUCT-001 parent row) and the frozen
run-5 tester_zones ledger directly from the pre-4.0 backup. Everything else (71
ideas) stays in research/db/_backup/ — recoverable, not carried forward.

Sources from the BACKUP, not brc_seed.sql: the seed was a capture-before-nuke but is
incomplete (no step2_papers rows) — the backup is the complete truth.

Gate remap (3.2 → 4.0, decided 2026-06-22): BRC's old gates 0(literature)+1(rule) →
4.0 **G1 Premise = passed** (both rich answers preserved); old gate 2 has no separate
4.0 gate → BRC sits at **G2 Edge = open** (no IS ledger logged yet).

Run:  python research/migrations/032_rebuild_brc40.py
Idempotent: rebuilds from the backup each run (live DB renamed aside, not deleted).
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from research.code.infra import db_init

LIVE = REPO / "research" / "db" / "research.db"
BACKUP_DIR = REPO / "research" / "db" / "_backup"
KEEP_IDEA = "BRC-001"
PARENT_IDEA = "STRUCT-001"   # BRC builds on the STRUCT-001 primitive — keep the parent row
KEEP_ZONE_RUN = 5            # the frozen IS zone ledger (≈100k rows)


def _backup_path() -> Path:
    cands = sorted(BACKUP_DIR.glob("research_pre40_*.db"))
    if not cands:
        sys.exit(f"FATAL: no pre-4.0 backup in {BACKUP_DIR}")
    return cands[-1]


def _shared_cols(conn, table: str) -> list[str]:
    """Columns present in BOTH the live (new) schema and the attached backup —
    guards against column-order drift (idea_kind/output_type were appended by
    migration 026, so SELECT * would misalign)."""
    dest = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    src  = [r[1] for r in conn.execute(f"PRAGMA src.table_info({table})").fetchall()]
    srcset = set(src)
    return [c for c in dest if c in srcset]


def _copy(conn, table: str, where: str, cols: list[str] | None = None) -> int:
    cols = cols or _shared_cols(conn, table)
    collist = ", ".join(cols)
    conn.execute(
        f"INSERT INTO {table} ({collist}) SELECT {collist} FROM src.{table} WHERE {where}"
    )
    return conn.execute(f"SELECT changes()").fetchone()[0]


def rebuild():
    backup = _backup_path()
    print(f"backup source : {backup.name}")

    # 1) move the live DB aside (safety; we also have the backup) and build fresh.
    if LIVE.exists():
        aside = LIVE.with_suffix(".db.pre40_rebuild")
        if aside.exists():
            aside.unlink()
        LIVE.rename(aside)
        print(f"live DB moved aside -> {aside.name}")
    db_init.init()   # fresh lean 4.0 schema at LIVE

    conn = sqlite3.connect(LIVE)
    conn.execute("PRAGMA foreign_keys = OFF")   # bulk load order-independent
    conn.execute(f"ATTACH DATABASE '{backup.as_posix()}' AS src")

    # 2) ideas: STRUCT-001 parent (parent forced NULL — its own parent not carried),
    #    then BRC-001 (keeps parent_idea_id='STRUCT-001').
    icols = _shared_cols(conn, "step1_ideas")
    sel = ", ".join("NULL" if c == "parent_idea_id" else c for c in icols)
    conn.execute(
        f"INSERT INTO step1_ideas ({', '.join(icols)}) "
        f"SELECT {sel} FROM src.step1_ideas WHERE idea_id=?", (PARENT_IDEA,))
    n_struct = conn.execute("SELECT changes()").fetchone()[0]
    n_brc = _copy(conn, "step1_ideas", f"idea_id='{KEEP_IDEA}'")
    print(f"step1_ideas   : {n_struct} parent(STRUCT-001) + {n_brc} BRC-001")

    # 3) papers (preserve paper_id — log_agent references it).
    n_p = _copy(conn, "step2_papers", f"idea_id='{KEEP_IDEA}'")
    print(f"step2_papers  : {n_p}")

    # 4) GATE REMAP: old 0+1 -> G1 passed (merged answer); old 2 -> dropped; add G2 open.
    g = {r[0]: r for r in conn.execute(
        "SELECT gate_number, gate_answer, pass_criteria, answered_by, created_at, "
        "updated_at, answered_at FROM src.step3_gates WHERE idea_id=? ORDER BY gate_number",
        (KEEP_IDEA,))}
    a0 = g[0][1] if 0 in g else ""
    a1 = g[1][1] if 1 in g else ""
    merged = (f"{a1}\n\n--- LITERATURE / MATH (was Gate 0) ---\n{a0}").strip()
    g1_created = g.get(0, g.get(1))[4]
    g1_updated = g.get(1, g.get(0))[5]
    g1_answered = g.get(1, g.get(0))[6]
    conn.execute("""
        INSERT INTO step3_gates
            (idea_id, gate_number, attempt, gate_question, gate_answer, pass_criteria,
             status, answered_by, created_at, updated_at, answered_at)
        VALUES (?, 1, 1, ?, ?, ?, 'passed', 'human', ?, ?, ?)
    """, (KEEP_IDEA,
          "G1 Premise: idea + one simple rule + thesis + a linked research paper. "
          "Why should this edge exist?",
          merged,
          "Sensible mechanism + falsifiable thesis + >=1 step2_papers row.",
          g1_created, g1_updated, g1_answered))
    conn.execute("""
        INSERT INTO step3_gates
            (idea_id, gate_number, attempt, gate_question, pass_criteria, status,
             created_at, updated_at)
        VALUES (?, 2, 1, ?, ?, 'open', ?, ?)
    """, (KEEP_IDEA,
          "G2 Edge & Survival: build the rule, emit the IS net-of-cost ledger. "
          "Is the equity curve smooth and the drawdown acceptable?",
          "Curve eyeball + DD read on a logged NET result.",
          g1_updated, g1_updated))
    print("step3_gates   : G1 passed (old 0+1 merged) + G2 open  [old gate 2 dropped]")

    # 5) the ledgers (verbatim shared columns).
    for tbl in ("log_agent", "log_strategy", "log_tasks"):
        n = _copy(conn, tbl, f"idea_id='{KEEP_IDEA}'")
        print(f"{tbl:<14}: {n}")

    # 6) tester ledger: BRC runs (metadata) + run-5 zones (frozen IS) + any trades.
    n_runs = _copy(conn, "tester_runs", f"idea_id='{KEEP_IDEA}'")
    n_zones = _copy(conn, "tester_zones", f"run_id={KEEP_ZONE_RUN}")
    n_tr = _copy(conn, "tester_trades",
                 f"run_id IN (SELECT run_id FROM src.tester_runs WHERE idea_id='{KEEP_IDEA}')")
    print(f"tester_runs   : {n_runs}  | tester_zones(run {KEEP_ZONE_RUN}): {n_zones}  | tester_trades: {n_tr}")

    conn.commit()

    # 7) integrity.
    conn.execute("PRAGMA foreign_keys = ON")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    integ = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.execute("DETACH DATABASE src")
    conn.close()
    print(f"\nintegrity_check  : {integ}")
    print(f"foreign_key_check: {'OK (0 violations)' if not fk else fk}")
    if fk or integ != "ok":
        sys.exit("FATAL: integrity/FK check failed — live DB left as rebuilt for inspection.")
    print("\n4.0 rebuild complete.")


if __name__ == "__main__":
    rebuild()
