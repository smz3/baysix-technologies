"""044 — push the code layer's rules down into the schema (task 366, Syafiq 2026-08-16).

THE PROBLEM THIS SOLVES
Rule 10 says "writes via the code layer only", and the code layer does enforce real
rules: `log_result()` refuses without n_obs + git_sha, `open_run()` refuses an unknown
platform, `add_task()` refuses an unknown stream. But every one of those checks lives in
Python. A raw INSERT — or pandas `to_sql`, or a stray script — skips all of them, and the
row that lands LOOKS normal. That is the actual failure mode: not corruption, plausible
garbage that a later filter learns to trust.

A constraint in the schema holds no matter who opens the connection. That is why this
migration comes BEFORE the triggers (045): a trigger guards the door, a constraint guards
the data, and the second one is the one that cannot be argued with.

WHAT IS ADDED, AND WHY EACH ONE IS SAFE
Every constraint below mirrors a rule the code layer ALREADY enforces, and every one was
MEASURED against the live data first (2026-08-16, 71 results / 269 tasks / 2 runs):

  log_tasks.stream      CHECK IN (MT5, NinjaTrader, IBKR, Research, Ops)
                        mirrors backlog._VALID_STREAM. This is CLAUDE.md rule 17 in
                        executable form: a typo'd stream silently mints a new bucket, and
                        rule 5's "scope every search to the active system" then misses
                        rows without saying so. MEASURED: 3 distinct values, all legal.
  runs.platform         CHECK IN (MT5, NinjaTrader, IBKR) — mirrors runs._VALID_PLATFORM.
  runs.stage            CHECK IN (IS, OOS, WF, smoke) — mirrors runs._VALID_STAGE.
  step4_results.n_obs   NOT NULL — mirrors pipeline.log_result(). MEASURED: 0 NULLs / 71.
  step4_results.git_sha NOT NULL — same call, same measurement. 0 NULLs / 71.
  step4_results.run_id  REAL FOREIGN KEY -> runs(run_id).

WHY THE FK ONLY BECOMES POSSIBLE NOW
Migration 043 wanted this and could not have it: SQLite cannot ADD a column carrying a FK,
so 043 left the reference "enforced by the code layer" with a note saying so. A full table
rebuild CAN declare it, which is what this does. MEASURED: 0 orphans, so nothing is
dropped or invented. It stays NULLABLE — 63 of 71 rows predate the registry and will never
have a run, and inventing one is the mistake 043's docstring already ruled out.

WHAT IS DELIBERATELY *NOT* CONSTRAINED
  step1_ideas.status  — there is NO code-layer whitelist for it. `_update_idea_status()`
                        accepts any string, and writes 'ideation', 'gate_1'..'gate_4' and
                        'killed'. Adding a CHECK here would mean INVENTING the legal set
                        (does a G4 pass write 'live'? nobody has ruled), and a constraint
                        nobody decided is worse than none — it fails at 2am on a legal
                        write. Needs a ruling first; filed rather than guessed.
  log_strategy.event  — free text by design. MEASURED: 12 of the distinct values are full
                        sentences ("trail semantics floored at entry (task 267)").
  runs.n_trials       — stays nullable. Whether an unknown trial count should be a hard
                        refusal is task 365 and is Syafiq's call, not this migration's.

METHOD
The documented SQLite 12-step table rebuild (CREATE new / INSERT SELECT / DROP / RENAME),
because SQLite cannot ALTER a column to add NOT NULL or CHECK. Indexes are recreated
explicitly. The four views (idea_lifecycle, gate_pipeline, papers_queue, open_backlog)
survive untouched: they store SQL text and bind at query time, so a table dropped and
recreated under the same name leaves them valid — verified at the end regardless.

Run: python db/migrations/044_schema_constraints.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.infra.db_path import DB_PATH  # noqa: E402

# (name, new DDL, column list to copy, indexes to recreate)
REBUILDS = [
    (
        "log_tasks",
        """
        CREATE TABLE log_tasks (
            task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id     TEXT REFERENCES step1_ideas(idea_id),
            status      TEXT NOT NULL DEFAULT 'open'
                          CHECK(status IN ('open','in_progress','done','dropped','parked')),
            priority    TEXT NOT NULL DEFAULT 'P2'
                          CHECK(priority IN ('P0','P1','P2')),
            title       TEXT NOT NULL,
            detail      TEXT,
            kind        TEXT NOT NULL CHECK(kind IN
                          ('variant','sizing','filter','port','infra','data','cleanup')),
            created_at  DATETIME NOT NULL,
            updated_at  DATETIME NOT NULL,
            resolved_at DATETIME,
            resolution  TEXT,
            stream      TEXT NOT NULL DEFAULT 'Research'
                          CHECK(stream IN ('MT5','NinjaTrader','IBKR','Research','Ops'))
        )
        """,
        "task_id, idea_id, status, priority, title, detail, kind, created_at, "
        "updated_at, resolved_at, resolution, stream",
        [],
    ),
    (
        "runs",
        """
        CREATE TABLE runs (
            run_id          INTEGER PRIMARY KEY,
            platform        TEXT NOT NULL
                              CHECK(platform IN ('MT5','NinjaTrader','IBKR')),
            idea_id         TEXT,
            stage           TEXT NOT NULL
                              CHECK(stage IN ('IS','OOS','WF','smoke')),
            symbol          TEXT NOT NULL,
            version         TEXT,
            data_start      DATE,
            data_end        DATE,
            git_sha         TEXT NOT NULL,
            output_dir      TEXT,
            trial_family_id TEXT,
            n_trials        INTEGER,
            notes           TEXT,
            created_at      DATETIME NOT NULL,
            FOREIGN KEY (idea_id) REFERENCES step1_ideas(idea_id)
        )
        """,
        "run_id, platform, idea_id, stage, symbol, version, data_start, data_end, "
        "git_sha, output_dir, trial_family_id, n_trials, notes, created_at",
        [
            "CREATE INDEX idx_runs_platform ON runs(platform)",
            "CREATE INDEX idx_runs_idea ON runs(idea_id)",
            "CREATE INDEX idx_runs_family ON runs(trial_family_id)",
        ],
    ),
    (
        "step4_results",
        """
        CREATE TABLE step4_results (
            result_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id         TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number     INTEGER NOT NULL,
            stage           TEXT NOT NULL
                            CHECK(stage IN ('IS','walkforward','montecarlo','OOS')),
            metric_key      TEXT NOT NULL,
            metric_value    REAL NOT NULL,
            cost_adjusted   INTEGER NOT NULL DEFAULT 0
                            CHECK(cost_adjusted IN (0,1)),
            period          TEXT CHECK(period IN ('per_trade','daily','annualised')),
            n_obs           INTEGER NOT NULL,
            is_run          TEXT,
            instrument      TEXT NOT NULL DEFAULT 'XAUUSD',
            data_start      DATE,
            data_end        DATE,
            parameters      TEXT,
            git_sha         TEXT NOT NULL,
            data_hash       TEXT,
            seed            INTEGER,
            code_path       TEXT,
            notes           TEXT,
            logged_at       DATETIME NOT NULL,
            what_changed    TEXT,
            trial_family_id TEXT,
            n_trials        INTEGER,
            run_id          INTEGER REFERENCES runs(run_id)
        )
        """,
        "result_id, idea_id, gate_number, stage, metric_key, metric_value, "
        "cost_adjusted, period, n_obs, is_run, instrument, data_start, data_end, "
        "parameters, git_sha, data_hash, seed, code_path, notes, logged_at, "
        "what_changed, trial_family_id, n_trials, run_id",
        ["CREATE INDEX idx_results_run ON step4_results(run_id)"],
    ),
]

PRECHECKS = [
    ("log_tasks.stream illegal",
     "SELECT COUNT(*) FROM log_tasks WHERE stream NOT IN "
     "('MT5','NinjaTrader','IBKR','Research','Ops')"),
    ("runs.platform illegal",
     "SELECT COUNT(*) FROM runs WHERE platform NOT IN ('MT5','NinjaTrader','IBKR')"),
    ("runs.stage illegal",
     "SELECT COUNT(*) FROM runs WHERE stage NOT IN ('IS','OOS','WF','smoke')"),
    ("runs.git_sha NULL", "SELECT COUNT(*) FROM runs WHERE git_sha IS NULL"),
    ("step4_results.n_obs NULL",
     "SELECT COUNT(*) FROM step4_results WHERE n_obs IS NULL"),
    ("step4_results.git_sha NULL",
     "SELECT COUNT(*) FROM step4_results WHERE git_sha IS NULL"),
    ("step4_results.run_id orphans",
     "SELECT COUNT(*) FROM step4_results r WHERE r.run_id IS NOT NULL AND NOT EXISTS "
     "(SELECT 1 FROM runs u WHERE u.run_id = r.run_id)"),
]


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    already = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='log_tasks'"
    ).fetchone()
    if already and "CHECK(stream IN" in already["sql"]:
        print("ABORT: log_tasks.stream already has its CHECK — 044 has already run.")
        return 1

    # -- refuse to run if the live data would violate anything ---------------- #
    print("PRE-CHECKS (a constraint the data violates is a guess, not a rule):")
    violations = 0
    for label, sql in PRECHECKS:
        n = conn.execute(sql).fetchone()[0]
        print(f"  {'OK ' if n == 0 else 'BAD'} {label:38} {n}")
        violations += n
    if violations:
        print(f"\nABORT: {violations} row(s) would violate the new schema. Fix the DATA "
              f"or the CONSTRAINT first — never widen the rule to fit a bad row.")
        return 1

    counts_before = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t, *_ in REBUILDS
    }

    # The views must come down first. `ALTER TABLE ... RENAME` re-parses the WHOLE
    # schema, so a view still pointing at the just-dropped `log_tasks` aborts the
    # rebuild (MEASURED on the first run of this migration). They are pure SQL text
    # with no data, so dropping and restoring them verbatim costs nothing.
    views = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='view' AND sql IS NOT NULL"
    ).fetchall()
    print(f"\nviews to drop and restore: {[v['name'] for v in views]}")

    # -- the documented SQLite table rebuild ---------------------------------- #
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN")
    try:
        for v in views:
            conn.execute(f"DROP VIEW {v['name']}")

        for table, ddl, cols, indexes in REBUILDS:
            new = f"_new_{table}"
            conn.execute(ddl.replace(f"CREATE TABLE {table} (",
                                     f"CREATE TABLE {new} (", 1))
            conn.execute(f"INSERT INTO {new} ({cols}) SELECT {cols} FROM {table}")
            conn.execute(f"DROP TABLE {table}")
            # No other table references `_new_*`, so this rename cannot rewrite a
            # foreign key clause elsewhere in the schema.
            conn.execute(f"ALTER TABLE {new} RENAME TO {table}")
            for ix in indexes:
                conn.execute(ix)
            print(f"  rebuilt {table}")

        for v in views:
            conn.execute(v["sql"])
        print(f"  restored {len(views)} view(s)")

        bad_fks = conn.execute("PRAGMA foreign_key_check").fetchall()
        if bad_fks:
            raise RuntimeError(f"foreign_key_check failed: {bad_fks[:5]}")
        conn.execute("COMMIT")
    except Exception as exc:
        conn.execute("ROLLBACK")
        conn.execute("PRAGMA foreign_keys = ON")
        print(f"\nFAIL: rolled back, database unchanged -> {exc}")
        conn.close()
        return 1
    conn.execute("PRAGMA foreign_keys = ON")

    # -- verify ---------------------------------------------------------------- #
    print("\nVERIFY:")
    ok = True
    for table, *_ in REBUILDS:
        after = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        same = after == counts_before[table]
        ok &= same
        print(f"  {'OK ' if same else 'BAD'} {table:16} {counts_before[table]} -> {after}")

    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"  {'OK ' if integrity == 'ok' else 'BAD'} integrity_check      {integrity}")
    ok &= integrity == "ok"

    for v in ("idea_lifecycle", "gate_pipeline", "papers_queue", "open_backlog"):
        try:
            conn.execute(f"SELECT * FROM {v} LIMIT 1").fetchall()
            print(f"  OK  view {v} still resolves")
        except sqlite3.Error as exc:
            ok = False
            print(f"  BAD view {v} -> {exc}")

    conn.close()
    if not ok:
        print("\nFAIL: verification did not pass.")
        return 1
    print("\n044 applied. Next: python db/migrations/045_write_guard_triggers.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
