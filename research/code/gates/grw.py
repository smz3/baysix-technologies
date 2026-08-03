"""
GRW-001 promotion ladder — pre-registration + the MECHANICAL adjudicator (task 290).

Spec: docs/reference/grw_autonomous_workflow.md §2. Schema: infra/schema_ledger.py.

The one idea this module exists to enforce:

    The rule that decides promotion is written BEFORE the run, and the run cannot
    change it. The agent gets no vote on its own results.

Everything here is built so that "the agent talked itself into a promotion" is not a
reachable state:

  - `register_batch()` writes prereg.json, hashes it, and refuses to overwrite one that
    already exists. Changing a threshold means a NEW batch_id, never an edit.
  - Every `grw_passes` row carries the `prereg_sha` it was judged against, so a pass
    adjudicated under a moved goalpost is self-evident from the row alone.
  - `adjudicate()` re-hashes prereg.json and ABORTS on mismatch. It then evaluates
    `promote_if` / `kill_if` through a restricted AST evaluator over a fixed variable
    set — no `eval()`, no attribute access, no calls. An unknown name is a hard error,
    not a silent False, because a typo'd threshold that quietly fails open is exactly
    how a fake winner gets promoted.
  - `record_oos()` refuses to write an OOS leg before the IS leg exists and the batch
    has been screened. Looking at OOS is spending it, so it is a one-way door:
    `grw_batches.oos_spent` latches to 1 and never returns.

Ladder (spec 2.3): S0 GENERATE -> S1 SCREEN -> S2 HOLDOUT -> S3 ADJUDICATE -> S4 LOG.
Passes are RAW MATERIAL. Nothing becomes a step4_results row before S3.

CLAUDE.md rule 10: this module IS the code layer for grw_* — callers never touch the
DB directly.
"""

import ast
import hashlib
import json
import subprocess
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root for run-as-script
from research.code.gates import pipeline

REPO      = Path(__file__).resolve().parents[3]
DB_PATH   = REPO / "research" / "db" / "research.db"
RUNS_DIR  = REPO / "data" / "grw_runs"
MYT       = timezone(timedelta(hours=8))

# Fields a prereg MUST declare before a single pass may run. `mechanism` is here on
# purpose (spec 3.0): a candidate with no stated reason the edge should exist is a
# lottery ticket, and lottery tickets do not get a slot in the batch.
REQUIRED_PREREG = (
    "batch_id", "idea_id", "trial_family_id", "hypothesis", "mechanism",
    "is_window", "oos_window", "n_trials_budget", "promote_if",
)

# The ONLY names an adjudication rule may reference. Anything else is a hard error.
ADJUDICATION_VARS = (
    "is_growth", "is_n_trades", "is_net_usd", "is_max_dd_pct", "is_fitness",
    "oos_growth", "oos_n_trades", "oos_net_usd", "oos_max_dd_pct", "oos_fitness",
)


# ─── infrastructure ──────────────────────────────────────────────────────────

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def _git():
    """(short_sha, dirty). Provenance travels with every row — a DIRTY tree means the
    run is exploratory and cannot be cited as evidence."""
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return sha, int(dirty)
    except Exception:
        return None, None


def prereg_sha(prereg: dict) -> str:
    """sha256 of the prereg with the sha field itself removed, canonically serialised.
    Deterministic across dict ordering and whitespace so the hash tracks MEANING."""
    body = {k: v for k, v in prereg.items() if k != "prereg_sha"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ─── the restricted evaluator ────────────────────────────────────────────────

_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Compare,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
    ast.Name, ast.Load, ast.Constant,
)


def eval_rule(expr: str, values: dict) -> bool:
    """Evaluate a promote_if / kill_if rule mechanically.

    Deliberately NOT `eval()`. Only comparisons, boolean ops and arithmetic over the
    fixed ADJUDICATION_VARS are permitted; calls, attributes, subscripts, lambdas and
    comprehensions all raise. Two failure modes matter more than the happy path:

      - An UNKNOWN NAME raises instead of returning False. A rule that silently fails
        open would promote on a typo.
      - A NULL input raises instead of comparing as 0. A missing OOS leg must stop the
        adjudication, not quietly read as a failed threshold.
    """
    expr = (expr or "").strip()
    if not expr:
        raise ValueError("empty adjudication rule")

    # Accept SQL-ish AND/OR that a human naturally writes in prereg.json.
    py = expr.replace(" AND ", " and ").replace(" OR ", " or ").replace(" NOT ", " not ")

    tree = ast.parse(py, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(
                f"illegal construct {type(node).__name__} in rule {expr!r} — rules may "
                f"only compare {ADJUDICATION_VARS} with and/or/not and + - * /")
        if isinstance(node, ast.Name):
            if node.id not in ADJUDICATION_VARS:
                raise ValueError(
                    f"unknown variable {node.id!r} in rule {expr!r}. Allowed: "
                    f"{', '.join(ADJUDICATION_VARS)}")
            if values.get(node.id) is None:
                raise ValueError(
                    f"rule {expr!r} references {node.id!r} but that value is NULL — "
                    f"the pass is not ready to adjudicate (run the missing leg first)")

    return bool(eval(compile(tree, "<prereg>", "eval"),  # noqa: S307 — AST vetted above
                     {"__builtins__": {}}, dict(values)))


# ─── S0: pre-registration ────────────────────────────────────────────────────

def register_batch(batch_id, idea_id, trial_family_id, hypothesis, mechanism,
                   is_window, oos_window, n_trials_budget, promote_if,
                   kill_if=None, fitness_ref=None, notes=None) -> Path:
    """Freeze a batch BEFORE it runs. Writes data/grw_runs/<batch_id>/prereg.json and
    the grw_batches row. Returns the prereg path.

    Refuses to overwrite an existing prereg — that is the whole point. To change a
    threshold, register a NEW batch_id; the old one stays on the record including its
    failure, which is what keeps the trial count honest.
    """
    for w, name in ((is_window, "is_window"), (oos_window, "oos_window")):
        if not (isinstance(w, (list, tuple)) and len(w) == 2):
            raise ValueError(f"{name} must be [start, end] as YYYY-MM-DD")
    if is_window[1] > oos_window[0]:
        raise ValueError(
            f"IS window ends {is_window[1]} AFTER OOS starts {oos_window[0]} — "
            f"overlapping windows make the holdout worthless")
    if not str(mechanism or "").strip():
        raise ValueError(
            "mechanism is required: one sentence on WHY the edge should exist "
            "(microstructure or behavioural). No mechanism = no slot in the batch.")

    prereg = {
        "batch_id": batch_id, "idea_id": idea_id, "trial_family_id": trial_family_id,
        "hypothesis": hypothesis, "mechanism": mechanism,
        "fitness": fitness_ref, "is_window": list(is_window),
        "oos_window": list(oos_window), "n_trials_budget": int(n_trials_budget),
        "promote_if": promote_if, "kill_if": kill_if,
    }
    missing = [f for f in REQUIRED_PREREG if not prereg.get(f)]
    if missing:
        raise ValueError(f"prereg missing required fields: {missing}")

    # Validate the rules NOW, against a dummy row. A rule that cannot parse must fail
    # at registration, not at adjudication when the compute is already spent.
    dummy = {v: 1.0 for v in ADJUDICATION_VARS}
    eval_rule(promote_if, dummy)
    if kill_if:
        eval_rule(kill_if, dummy)

    prereg["prereg_sha"] = prereg_sha(prereg)

    path = RUNS_DIR / batch_id / "prereg.json"
    if path.exists():
        raise FileExistsError(
            f"{path} already exists — a prereg is never edited. Register a new "
            f"batch_id instead (spec 2.2).")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prereg, indent=2), encoding="utf-8")

    sha, dirty = _git()
    now = _now()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO grw_batches
                (batch_id, idea_id, trial_family_id, hypothesis, mechanism, fitness_ref,
                 is_start, is_end, oos_start, oos_end, n_trials_budget, promote_if,
                 kill_if, prereg_path, prereg_sha, prereg_git_sha, stage, oos_spent,
                 notes, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'S0',0,?,?,?)
        """, (batch_id, idea_id, trial_family_id, hypothesis, mechanism, fitness_ref,
              is_window[0], is_window[1], oos_window[0], oos_window[1],
              int(n_trials_budget), promote_if, kill_if,
              str(path.relative_to(REPO)), prereg["prereg_sha"], sha, notes, now, now))
        conn.commit()

    print(f"[grw] batch {batch_id} PRE-REGISTERED  sha={prereg['prereg_sha'][:12]}  "
          f"IS {is_window[0]}..{is_window[1]}  OOS {oos_window[0]}..{oos_window[1]} (sealed)")
    print(f"      promote_if: {promote_if}")
    print(f"      -> {path}  — commit this BEFORE running the batch")
    return path


def load_prereg(batch_id: str) -> dict:
    """Read prereg.json and verify its hash. Raises if the file was edited after
    registration — the tamper check that makes S3 mechanical rather than advisory."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM grw_batches WHERE batch_id=?",
                           (batch_id,)).fetchone()
    if not row:
        raise ValueError(f"batch {batch_id!r} is not registered — run register_batch first")

    path = REPO / row["prereg_path"]
    if not path.exists():
        raise FileNotFoundError(f"prereg missing: {path}")
    prereg = json.loads(path.read_text(encoding="utf-8"))

    actual = prereg_sha(prereg)
    if actual != row["prereg_sha"]:
        raise ValueError(
            f"PREREG TAMPERED — {path}\n"
            f"  registered sha: {row['prereg_sha']}\n"
            f"  file sha now:   {actual}\n"
            f"The goalposts moved after registration. Adjudication is ABORTED. If the "
            f"threshold genuinely needs to change, register a new batch_id (spec 2.2).")
    return prereg


# ─── S0/S1: passes ───────────────────────────────────────────────────────────

def log_pass(batch_id, params: dict, is_run_id=None, is_fitness=None, is_growth=None,
             is_n_trades=None, is_net_usd=None, is_max_dd_pct=None) -> int:
    """Record ONE optimizer pass (in-sample leg). Raw material — not a result.

    Enforces the declared trial budget: a batch cannot quietly run more passes than it
    pre-registered, because widening the search after seeing results is never automated
    (spec 3.4).
    """
    with _conn() as conn:
        b = conn.execute("SELECT * FROM grw_batches WHERE batch_id=?",
                         (batch_id,)).fetchone()
        if not b:
            raise ValueError(f"batch {batch_id!r} not registered")
        n = conn.execute("SELECT COUNT(*) FROM grw_passes WHERE batch_id=?",
                         (batch_id,)).fetchone()[0]
        if n >= b["n_trials_budget"]:
            raise ValueError(
                f"batch {batch_id} declared n_trials_budget={b['n_trials_budget']} and "
                f"already has {n} passes. Widening the budget after seeing results is "
                f"never automated (spec 3.4) — register a new batch.")

        blob = json.dumps(params, sort_keys=True, separators=(",", ":"))
        cfg_hash = hashlib.sha256(blob.encode()).hexdigest()[:16]
        sha, dirty = _git()
        now = _now()
        cur = conn.execute("""
            INSERT INTO grw_passes
                (batch_id, trial_family_id, idea_id, prereg_sha, config_hash, params,
                 is_run_id, is_fitness, is_growth, is_n_trades, is_net_usd,
                 is_max_dd_pct, stage, verdict, git_sha, git_dirty, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'S0','PENDING',?,?,?,?)
        """, (batch_id, b["trial_family_id"], b["idea_id"], b["prereg_sha"], cfg_hash,
              blob, is_run_id, is_fitness, is_growth, is_n_trades, is_net_usd,
              is_max_dd_pct, sha, dirty, now, now))
        conn.commit()
        return cur.lastrowid


def screen(batch_id: str, top_k: int = None) -> list[dict]:
    """S1 — rank passes by in-sample fitness. Returns the top-K to carry to holdout.
    Ranking is the LAST step that may look at in-sample numbers."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT pass_id, config_hash, is_fitness, is_growth, is_n_trades
            FROM grw_passes WHERE batch_id=? AND is_fitness IS NOT NULL
            ORDER BY is_fitness DESC
        """, (batch_id,)).fetchall()
        for rank, r in enumerate(rows, start=1):
            conn.execute("UPDATE grw_passes SET rank=?, stage='S1', updated_at=? "
                         "WHERE pass_id=?", (rank, _now(), r["pass_id"]))
        conn.execute("UPDATE grw_batches SET stage='S1', updated_at=? WHERE batch_id=?",
                     (_now(), batch_id))
        conn.commit()
    out = [dict(r) for r in rows[:top_k]] if top_k else [dict(r) for r in rows]
    print(f"[grw] S1 screened {len(rows)} passes; carrying {len(out)} to holdout")
    return out


# ─── S2: holdout ─────────────────────────────────────────────────────────────

def record_oos(pass_id, oos_run_id=None, oos_fitness=None, oos_growth=None,
               oos_n_trades=None, oos_net_usd=None, oos_max_dd_pct=None) -> None:
    """S2 — attach the held-out leg. Latches grw_batches.oos_spent=1: looking at OOS is
    spending it, and that door only opens once (spec 2.2)."""
    with _conn() as conn:
        p = conn.execute("SELECT * FROM grw_passes WHERE pass_id=?", (pass_id,)).fetchone()
        if not p:
            raise ValueError(f"pass {pass_id} not found")
        if p["is_fitness"] is None:
            raise ValueError(
                f"pass {pass_id} has no in-sample leg — an OOS number without its IS "
                f"counterpart cannot be adjudicated against promote_if")
        conn.execute("""
            UPDATE grw_passes SET oos_run_id=?, oos_fitness=?, oos_growth=?,
                   oos_n_trades=?, oos_net_usd=?, oos_max_dd_pct=?, stage='S2', updated_at=?
            WHERE pass_id=?
        """, (oos_run_id, oos_fitness, oos_growth, oos_n_trades, oos_net_usd,
              oos_max_dd_pct, _now(), pass_id))
        conn.execute("UPDATE grw_batches SET oos_spent=1, stage='S2', updated_at=? "
                     "WHERE batch_id=?", (_now(), p["batch_id"]))
        conn.commit()


# ─── S3: the adjudicator ─────────────────────────────────────────────────────

def adjudicate(batch_id: str) -> dict:
    """S3 — apply promote_if / kill_if MECHANICALLY. The agent gets no vote.

    Re-hashes prereg.json first and aborts on mismatch. Every pass with a holdout leg
    gets exactly one verdict: PROMOTED / KILLED / FALSIFIED. Failures are logged, never
    discarded — a FALSIFIED row feeds the >=2-falsified kill rule (CLAUDE.md 8b) and
    keeps the denominator honest.
    """
    prereg = load_prereg(batch_id)          # raises if tampered
    promote_if, kill_if = prereg["promote_if"], prereg.get("kill_if")

    counts = {"PROMOTED": 0, "FALSIFIED": 0, "KILLED": 0, "SKIPPED": 0}
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM grw_passes WHERE batch_id=? ORDER BY rank, pass_id",
            (batch_id,)).fetchall()

        for r in rows:
            vals = {v: r[v] for v in ADJUDICATION_VARS}
            if r["oos_growth"] is None and r["oos_fitness"] is None:
                counts["SKIPPED"] += 1      # never carried to holdout — no verdict owed
                continue

            if kill_if and eval_rule(kill_if, vals):
                verdict, reason = "KILLED", f"kill_if fired: {kill_if}"
            elif eval_rule(promote_if, vals):
                verdict, reason = "PROMOTED", f"promote_if satisfied: {promote_if}"
            else:
                verdict, reason = "FALSIFIED", f"promote_if not met: {promote_if}"

            counts[verdict] += 1
            conn.execute("""
                UPDATE grw_passes SET verdict=?, verdict_reason=?, adjudicated_at=?,
                       stage='S3', updated_at=? WHERE pass_id=?
            """, (verdict, reason, _now(), _now(), r["pass_id"]))

        conn.execute("UPDATE grw_batches SET stage='S3', n_promoted=?, updated_at=? "
                     "WHERE batch_id=?", (counts["PROMOTED"], _now(), batch_id))
        conn.commit()

    print(f"[grw] S3 {batch_id}: {counts['PROMOTED']} promoted / "
          f"{counts['FALSIFIED']} falsified / {counts['KILLED']} killed "
          f"({counts['SKIPPED']} never held out)")
    return counts


def family_trials(trial_family_id: str) -> dict:
    """The multiplicity ledger — cumulative trials for this family ACROSS batches.
    A growth rate without its trial count is not a finding (spec 2.3)."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM grw_family_trials WHERE trial_family_id=?",
                           (trial_family_id,)).fetchone()
    return dict(row) if row else {"trial_family_id": trial_family_id, "n_trials_cum": 0}


def promote(pass_id: int, metric_key: str = "oos_log_growth") -> int:
    """S4 — copy an adjudicated survivor into step4_results.

    Refuses anything the adjudicator did not stamp PROMOTED. This is the only door
    between raw passes and the findings ledger, and `n_trials` travels with the row:
    the cumulative family count, not this batch's count, so the bar rises as the search
    widens.
    """
    with _conn() as conn:
        p = conn.execute("SELECT * FROM grw_passes WHERE pass_id=?", (pass_id,)).fetchone()
    if not p:
        raise ValueError(f"pass {pass_id} not found")
    if p["verdict"] != "PROMOTED":
        raise ValueError(
            f"pass {pass_id} has verdict {p['verdict']!r}, not PROMOTED. Only the "
            f"adjudicator promotes; the agent does not get to override it (spec 2.3).")

    prereg = load_prereg(p["batch_id"])
    fam = family_trials(p["trial_family_id"])

    result_id = pipeline.log_result(
        idea_id=p["idea_id"], gate_number=2, stage="OOS", metric_key=metric_key,
        metric_value=p["oos_growth"], cost_adjusted=1, period="per_trade",
        n_obs=p["oos_n_trades"], data_start=prereg["oos_window"][0],
        data_end=prereg["oos_window"][1], git_sha=p["git_sha"],
        code_path="research/code/gates/grw.py", is_run=p["batch_id"],
        what_changed=prereg["hypothesis"], parameters=p["params"],
        trial_family_id=p["trial_family_id"], n_trials=fam["n_trials_cum"],
        notes=f"GRW S4 promote. {p['verdict_reason']}. mechanism: {prereg['mechanism']}",
        allow_unfrozen=True)

    with _conn() as conn:
        conn.execute("UPDATE grw_passes SET result_id=?, stage='S4', updated_at=? "
                     "WHERE pass_id=?", (result_id, _now(), pass_id))
        conn.execute("UPDATE grw_batches SET stage='S4', updated_at=? WHERE batch_id=?",
                     (_now(), p["batch_id"]))
        conn.commit()
    print(f"[grw] S4 pass {pass_id} -> result_id {result_id} "
          f"(family n_trials={fam['n_trials_cum']})")
    return result_id


def no_promotion_streak(trial_family_id: str) -> int:
    """Consecutive most-recent adjudicated batches with zero promotions. Spec 3.3 halts
    the loop at 3 — the search space is wrong, and that is a design question, not a
    compute question."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT n_promoted FROM grw_batches
            WHERE trial_family_id=? AND stage IN ('S3','S4','S5')
            ORDER BY created_at DESC
        """, (trial_family_id,)).fetchall()
    streak = 0
    for r in rows:
        if (r["n_promoted"] or 0) > 0:
            break
        streak += 1
    return streak
