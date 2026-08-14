"""factory.db — the ledger, and the ONLY place its DDL is written.

Two lessons from the MT5 side are baked in rather than re-learned:

*   **One DDL home.** Over there the `tester_runs` DDL was duplicated between the
    initialiser and the writer, and the two drifted: a from-scratch rebuild would
    have silently dropped columns that live data depended on. Here the schema is
    one dict in one module, and everything imports it.

*   **WAL, not rollback journaling.** The driver writes on a timer while a brief or
    a dashboard reads. Under `journal_mode=delete` that is a `database is locked`
    waiting to happen.

## What this module refuses to do

`spend_oos()` latches `batches.oos_spent` to 1 and there is no code path back.
Looking at the holdout IS spending it — not as a policy, as a fact about what the
number then means — so the latch is a one-way door and a second holdout run
against the same batch raises.

All writes go through the functions here. Callers never open a cursor: timestamps,
provenance and constraints are exactly what gets skipped when they do.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from factory.adjudicate import Verdict as RuleVerdict
from factory.objective import BarrierOutcome
from factory.prereg import Prereg
from factory.provenance import Claim
from factory.spec import StrategySpec
from factory.venue import AgreementReport, RunResult, Window

__all__ = ["Ledger", "LedgerError", "SCHEMA", "DEFAULT_DB"]

DEFAULT_DB = Path(__file__).resolve().parents[1] / "db" / "factory.db"


class LedgerError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
#  the schema — one home, no duplicates
# --------------------------------------------------------------------------- #

SCHEMA: dict[str, str] = {
    "batches": """
        CREATE TABLE IF NOT EXISTS batches (
            batch_id          TEXT PRIMARY KEY,
            prereg_sha        TEXT NOT NULL,
            family            TEXT NOT NULL,
            instrument        TEXT NOT NULL,
            hypothesis        TEXT NOT NULL,
            mechanism         TEXT NOT NULL,
            objective_ref     TEXT NOT NULL,
            is_start          TEXT NOT NULL,
            is_end            TEXT NOT NULL,
            oos_start         TEXT NOT NULL,
            oos_end           TEXT NOT NULL,
            n_trials_budget   INTEGER NOT NULL,
            promote_if        TEXT NOT NULL,
            kill_if           TEXT,
            venue_search      TEXT NOT NULL,
            venue_arbiter     TEXT,
            oos_spent         INTEGER NOT NULL DEFAULT 0,
            screened          INTEGER NOT NULL DEFAULT 0,
            status            TEXT NOT NULL DEFAULT 'OPEN',
            git_sha           TEXT,
            git_dirty         INTEGER,
            registered_at     TEXT NOT NULL,
            created_at        TEXT NOT NULL
        )
    """,
    "candidates": """
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id      TEXT NOT NULL REFERENCES batches(batch_id),
            config_hash   TEXT NOT NULL,
            spec_json     TEXT NOT NULL,
            mechanism     TEXT NOT NULL,
            rank          INTEGER,
            created_at    TEXT NOT NULL,
            UNIQUE (batch_id, config_hash)
        )
    """,
    # One row per execution. A run IS one episode, i.e. ONE Bernoulli draw — the
    # probability lives at aggregate level, never here.
    "runs": """
        CREATE TABLE IF NOT EXISTS runs (
            run_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id       INTEGER NOT NULL REFERENCES candidates(candidate_id),
            batch_id           TEXT NOT NULL REFERENCES batches(batch_id),
            venue              TEXT NOT NULL,
            venue_role         TEXT NOT NULL,
            leg                TEXT NOT NULL CHECK (leg IN ('IS','OOS')),
            window_start       TEXT NOT NULL,
            window_end         TEXT NOT NULL,
            data_ref           TEXT NOT NULL,
            objective_ref      TEXT NOT NULL,
            verdict            TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','CENSORED')),
            fitness            REAL NOT NULL,
            n_trades           INTEGER NOT NULL,
            net_usd            REAL NOT NULL,
            days_traded        INTEGER,
            best_day_profit    REAL,
            effective_target   REAL,
            floor_at_end       REAL,
            peak_equity        REAL,
            trough_equity      REAL,
            resolved_at        TEXT,
            detail             TEXT,
            meta_json          TEXT,
            git_sha            TEXT,
            git_dirty          INTEGER,
            created_at         TEXT NOT NULL
        )
    """,
    "trades": """
        CREATE TABLE IF NOT EXISTS trades (
            trade_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL REFERENCES runs(run_id),
            entry_ts    TEXT NOT NULL,
            exit_ts     TEXT NOT NULL,
            direction   INTEGER NOT NULL,
            qty         REAL NOT NULL,
            entry_px    REAL NOT NULL,
            exit_px     REAL NOT NULL,
            gross_usd   REAL NOT NULL,
            cost_usd    REAL NOT NULL
        )
    """,
    # Cross-engine agreement. A divergence HALTS the batch; it is recorded here so
    # the halt is explicable a month later.
    "agreements": """
        CREATE TABLE IF NOT EXISTS agreements (
            agreement_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id    INTEGER NOT NULL REFERENCES candidates(candidate_id),
            search_run_id   INTEGER NOT NULL REFERENCES runs(run_id),
            arbiter_run_id  INTEGER NOT NULL REFERENCES runs(run_id),
            agree           INTEGER NOT NULL,
            lines_json      TEXT NOT NULL,
            created_at      TEXT NOT NULL
        )
    """,
    # Every verdict carries the prereg_sha it was judged against, so a decision
    # reached under a moved goalpost is self-evident from the row alone.
    "verdicts": """
        CREATE TABLE IF NOT EXISTS verdicts (
            verdict_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id      TEXT NOT NULL REFERENCES batches(batch_id),
            candidate_id  INTEGER NOT NULL REFERENCES candidates(candidate_id),
            prereg_sha    TEXT NOT NULL,
            ruling        TEXT NOT NULL CHECK (ruling IN ('PROMOTE','FALSIFIED','NO_ACTION')),
            promote_rule  TEXT NOT NULL,
            kill_rule     TEXT,
            inputs_json   TEXT NOT NULL,
            n_trials      INTEGER NOT NULL,
            detail        TEXT,
            created_at    TEXT NOT NULL,
            UNIQUE (batch_id, candidate_id)
        )
    """,
    "claims": """
        CREATE TABLE IF NOT EXISTS claims (
            claim_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            scope       TEXT NOT NULL,
            scope_id    TEXT,
            name        TEXT NOT NULL,
            value       TEXT NOT NULL,
            unit        TEXT,
            provenance  TEXT NOT NULL CHECK (provenance IN ('MEASURED','DERIVED','CITED','ASSUMED')),
            source      TEXT NOT NULL,
            claimed_at  TEXT NOT NULL
        )
    """,
    "data_integrity": """
        CREATE TABLE IF NOT EXISTS data_integrity (
            check_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset     TEXT NOT NULL,
            symbol      TEXT NOT NULL,
            check_name  TEXT NOT NULL,
            passed      INTEGER NOT NULL,
            observed    TEXT,
            detail      TEXT,
            created_at  TEXT NOT NULL
        )
    """,
    # Append-only. What the loop did, in order, so a morning brief is reconstructed
    # from the record rather than from anybody's memory of the night.
    "events": """
        CREATE TABLE IF NOT EXISTS events (
            event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id    TEXT,
            stage       TEXT NOT NULL,
            actor       TEXT NOT NULL,
            action      TEXT NOT NULL,
            detail      TEXT,
            created_at  TEXT NOT NULL
        )
    """,
}

INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS ix_runs_candidate ON runs (candidate_id, leg)",
    "CREATE INDEX IF NOT EXISTS ix_runs_batch ON runs (batch_id, leg)",
    "CREATE INDEX IF NOT EXISTS ix_trades_run ON trades (run_id)",
    "CREATE INDEX IF NOT EXISTS ix_cand_batch ON candidates (batch_id)",
    "CREATE INDEX IF NOT EXISTS ix_events_batch ON events (batch_id, event_id)",
)

VIEWS: dict[str, str] = {
    # Cumulative trials per family across batches. The bar should rise as the
    # search widens, and a rule can only reference n_trials if something counts it.
    "family_trials": """
        CREATE VIEW IF NOT EXISTS family_trials AS
        SELECT b.family,
               COUNT(DISTINCT c.candidate_id) AS n_candidates,
               COUNT(DISTINCT b.batch_id)     AS n_batches,
               SUM(b.n_trials_budget)         AS budgeted_trials
        FROM batches b
        LEFT JOIN candidates c ON c.batch_id = b.batch_id
        GROUP BY b.family
    """,
    # Drives the "three consecutive batches with no promotion" hard stop: at that
    # point the search space is wrong, which is a design question, not a compute one.
    "batch_scoreboard": """
        CREATE VIEW IF NOT EXISTS batch_scoreboard AS
        SELECT b.batch_id, b.family, b.status, b.oos_spent, b.registered_at,
               COUNT(DISTINCT c.candidate_id) AS n_candidates,
               SUM(CASE WHEN v.ruling = 'PROMOTE'   THEN 1 ELSE 0 END) AS n_promoted,
               SUM(CASE WHEN v.ruling = 'FALSIFIED' THEN 1 ELSE 0 END) AS n_falsified
        FROM batches b
        LEFT JOIN candidates c ON c.batch_id = b.batch_id
        LEFT JOIN verdicts  v ON v.candidate_id = c.candidate_id
        GROUP BY b.batch_id
    """,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(repo: Path) -> tuple[str | None, int | None]:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip())
        return sha, int(dirty)
    except Exception:
        return None, None


class Ledger:
    """The write layer. Nothing else opens a cursor on factory.db."""

    def __init__(self, path: str | Path = DEFAULT_DB, *, repo: Path | None = None):
        self.path = Path(path)
        self.repo = repo or self.path.resolve().parents[1]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # -- plumbing ----------------------------------------------------------- #

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            for ddl in SCHEMA.values():
                conn.execute(ddl)
            for ddl in INDEXES:
                conn.execute(ddl)
            for ddl in VIEWS.values():
                conn.execute(ddl)

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Read-only escape hatch. Writes must use the named methods."""
        stripped = sql.lstrip().upper()
        if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
            raise LedgerError("query() is read-only; use the write methods")
        with self._conn() as conn:
            return conn.execute(sql, params).fetchall()

    # -- writes ------------------------------------------------------------- #

    def record_batch(self, pre: Prereg) -> str:
        """S0. Persist a pre-registration that has already been written to disk."""
        pre.verify()
        p = pre.payload
        with self._conn() as conn:
            exists = conn.execute(
                "SELECT prereg_sha FROM batches WHERE batch_id = ?", (pre.batch_id,)
            ).fetchone()
            if exists:
                if exists["prereg_sha"] != pre.sha:
                    raise LedgerError(
                        f"batch {pre.batch_id} is already on the record under a "
                        f"DIFFERENT pre-registration ({exists['prereg_sha'][:12]} vs "
                        f"{pre.sha[:12]}). Register a new batch_id."
                    )
                return pre.batch_id
            conn.execute(
                """INSERT INTO batches (batch_id, prereg_sha, family, instrument,
                       hypothesis, mechanism, objective_ref, is_start, is_end,
                       oos_start, oos_end, n_trials_budget, promote_if, kill_if,
                       venue_search, venue_arbiter, git_sha, git_dirty,
                       registered_at, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    p["batch_id"], pre.sha, p["family"], p["instrument"],
                    p["hypothesis"], p["mechanism"], p["objective_ref"],
                    p["is_window"][0], p["is_window"][1],
                    p["oos_window"][0], p["oos_window"][1],
                    p["n_trials_budget"], p["promote_if"], p.get("kill_if"),
                    p.get("venue_search", "pyoracle"), p.get("venue_arbiter"),
                    p.get("git_sha"), p.get("git_dirty"),
                    p["registered_at"], _now(),
                ),
            )
        self.log_event(pre.batch_id, "S0", "prereg", "registered", pre.sha[:12])
        return pre.batch_id

    def add_candidate(self, batch_id: str, spec: StrategySpec) -> int:
        """S0. A candidate may only be added while the batch is still within budget."""
        with self._conn() as conn:
            batch = conn.execute(
                "SELECT n_trials_budget, oos_spent FROM batches WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if batch is None:
                raise LedgerError(f"no such batch {batch_id!r}; register it first")
            if batch["oos_spent"]:
                raise LedgerError(
                    f"batch {batch_id} has already spent its holdout. Adding a "
                    f"candidate now would let the search widen after seeing the "
                    f"answer, which is the definition of the thing prereg prevents."
                )
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM candidates WHERE batch_id = ?", (batch_id,)
            ).fetchone()["n"]
            if n >= batch["n_trials_budget"]:
                raise LedgerError(
                    f"batch {batch_id} budgeted {batch['n_trials_budget']} trials and "
                    f"already has {n}. Widening a budget after registration is not a "
                    f"setting change; register a new batch."
                )
            cur = conn.execute(
                """INSERT INTO candidates (batch_id, config_hash, spec_json,
                                           mechanism, created_at)
                   VALUES (?,?,?,?,?)""",
                (batch_id, spec.config_hash, spec.to_json(), spec.mechanism, _now()),
            )
            return int(cur.lastrowid)

    def log_run(
        self,
        candidate_id: int,
        batch_id: str,
        result: RunResult,
        *,
        venue_role: str,
        leg: str,
        window: Window,
        data_ref: str,
    ) -> int:
        """S1/S2/S3. One row per episode. Trades land alongside it."""
        if leg not in {"IS", "OOS"}:
            raise LedgerError(f"leg must be IS or OOS, got {leg!r}")
        if leg == "OOS" and not self.is_oos_spent(batch_id):
            raise LedgerError(
                f"batch {batch_id}: an OOS run was logged without spend_oos() first. "
                f"The latch exists so that looking is recorded as spending."
            )

        o: BarrierOutcome = result.outcome
        sha, dirty = _git(self.repo)
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO runs (candidate_id, batch_id, venue, venue_role, leg,
                       window_start, window_end, data_ref, objective_ref, verdict,
                       fitness, n_trades, net_usd, days_traded, best_day_profit,
                       effective_target, floor_at_end, peak_equity, trough_equity,
                       resolved_at, detail, meta_json, git_sha, git_dirty, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    candidate_id, batch_id, result.handle.venue, venue_role, leg,
                    window.start.isoformat(), window.end.isoformat(), data_ref,
                    result.objective_fingerprint, o.verdict.value, o.fitness,
                    result.n_trades, result.net_usd, o.days_traded, o.best_day_profit,
                    o.effective_target, o.floor_at_end, o.peak_equity, o.trough_equity,
                    o.resolved_at.isoformat() if o.resolved_at else None, o.detail,
                    json.dumps(result.meta, default=str), sha, dirty, _now(),
                ),
            )
            run_id = int(cur.lastrowid)
            conn.executemany(
                """INSERT INTO trades (run_id, entry_ts, exit_ts, direction, qty,
                                       entry_px, exit_px, gross_usd, cost_usd)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    (run_id, t.entry_ts.isoformat(), t.exit_ts.isoformat(),
                     t.direction, t.qty, t.entry_px, t.exit_px, t.gross_usd, t.cost_usd)
                    for t in result.trades
                ],
            )
        return run_id

    def log_agreement(
        self, candidate_id: int, search_run_id: int, arbiter_run_id: int,
        report: AgreementReport,
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO agreements (candidate_id, search_run_id, arbiter_run_id,
                                           agree, lines_json, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (candidate_id, search_run_id, arbiter_run_id, int(report.agree),
                 json.dumps([list(l) for l in report.lines], default=str), _now()),
            )
            return int(cur.lastrowid)

    def spend_oos(self, batch_id: str) -> None:
        """S3. The one-way door. Latches and never returns.

        Raises if called twice, because a second holdout run against the same batch
        is a second look at data that was only ever good for one.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT oos_spent, screened FROM batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
            if row is None:
                raise LedgerError(f"no such batch {batch_id!r}")
            if row["oos_spent"]:
                raise LedgerError(
                    f"batch {batch_id} has already spent its holdout. There is no "
                    f"second look: re-testing on the same OOS window turns it into "
                    f"in-sample data with extra steps."
                )
            if not row["screened"]:
                raise LedgerError(
                    f"batch {batch_id} has not been screened. Spending the holdout "
                    f"before ranking in-sample means the holdout chose the winner."
                )
            conn.execute(
                "UPDATE batches SET oos_spent = 1 WHERE batch_id = ?", (batch_id,)
            )
        self.log_event(batch_id, "S3", "ledger", "oos_spent", "one-way door latched")

    def mark_screened(self, batch_id: str, ranks: dict[int, int]) -> None:
        """S1. Record the in-sample ranking, then close screening."""
        with self._conn() as conn:
            for candidate_id, rank in ranks.items():
                conn.execute(
                    "UPDATE candidates SET rank = ? WHERE candidate_id = ?",
                    (rank, candidate_id),
                )
            conn.execute("UPDATE batches SET screened = 1 WHERE batch_id = ?", (batch_id,))
        self.log_event(batch_id, "S1", "ledger", "screened", f"{len(ranks)} ranked")

    def log_verdict(
        self, batch_id: str, candidate_id: int, verdict: RuleVerdict, *, n_trials: int
    ) -> int:
        """S4. Verdicts are written by the adjudicator and are not editable."""
        with self._conn() as conn:
            batch = conn.execute(
                "SELECT prereg_sha FROM batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
            if batch is None:
                raise LedgerError(f"no such batch {batch_id!r}")
            existing = conn.execute(
                "SELECT ruling FROM verdicts WHERE batch_id = ? AND candidate_id = ?",
                (batch_id, candidate_id),
            ).fetchone()
            if existing:
                raise LedgerError(
                    f"candidate {candidate_id} in {batch_id} is already adjudicated as "
                    f"{existing['ruling']}. A verdict is not revisited; register a new "
                    f"batch if the bar was wrong."
                )
            cur = conn.execute(
                """INSERT INTO verdicts (batch_id, candidate_id, prereg_sha, ruling,
                       promote_rule, kill_rule, inputs_json, n_trials, detail, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (batch_id, candidate_id, batch["prereg_sha"], verdict.ruling.value,
                 verdict.promote_rule, verdict.kill_rule,
                 json.dumps(dict(verdict.inputs_used), default=str),
                 n_trials, verdict.detail, _now()),
            )
            return int(cur.lastrowid)

    def log_claim(self, claim: Claim, *, scope: str, scope_id: str | None = None) -> int:
        row = claim.to_row()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO claims (scope, scope_id, name, value, unit,
                                       provenance, source, claimed_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (scope, scope_id, row["name"], str(row["value"]), row["unit"],
                 row["provenance"], row["source"], row["claimed_at"]),
            )
            return int(cur.lastrowid)

    def log_integrity(
        self, dataset: str, symbol: str, check_name: str, passed: bool,
        observed: str = "", detail: str = "",
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO data_integrity (dataset, symbol, check_name, passed,
                                               observed, detail, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (dataset, symbol, check_name, int(passed), observed, detail, _now()),
            )
            return int(cur.lastrowid)

    def log_event(
        self, batch_id: str | None, stage: str, actor: str, action: str, detail: str = ""
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO events (batch_id, stage, actor, action, detail, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (batch_id, stage, actor, action, detail, _now()),
            )
            return int(cur.lastrowid)

    # -- reads used by the driver ------------------------------------------- #

    def is_oos_spent(self, batch_id: str) -> bool:
        rows = self.query("SELECT oos_spent FROM batches WHERE batch_id = ?", (batch_id,))
        if not rows:
            raise LedgerError(f"no such batch {batch_id!r}")
        return bool(rows[0]["oos_spent"])

    def candidates(self, batch_id: str) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM candidates WHERE batch_id = ? ORDER BY rank IS NULL, rank",
            (batch_id,),
        )

    def runs(self, candidate_id: int, leg: str | None = None) -> list[sqlite3.Row]:
        if leg:
            return self.query(
                "SELECT * FROM runs WHERE candidate_id = ? AND leg = ? ORDER BY run_id",
                (candidate_id, leg),
            )
        return self.query(
            "SELECT * FROM runs WHERE candidate_id = ? ORDER BY run_id", (candidate_id,)
        )

    def consecutive_batches_without_promotion(self, family: str) -> int:
        """Three of these is a hard stop: the search space is wrong, and that is a
        design question rather than a compute one."""
        rows = self.query(
            """SELECT n_promoted FROM batch_scoreboard
               WHERE family = ? AND status != 'OPEN'
               ORDER BY registered_at DESC""",
            (family,),
        )
        streak = 0
        for r in rows:
            if (r["n_promoted"] or 0) > 0:
                break
            streak += 1
        return streak
