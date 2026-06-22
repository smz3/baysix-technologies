"""
Pipeline interface for research.db.
All writes go through here — no raw SQL elsewhere.

Idea functions:
  add_idea()          — insert a new idea (status=ideation)

Gate functions:
  open_gate()         — create a gate row (status=open)
  pass_gate()         — mark gate passed
  block_gate()        — mark gate blocked with reason
  kill_idea()         — kill idea at current gate

Result functions:
  log_result()        — log a metric to step4_results

Read functions:
  get_idea()          — fetch idea row
  get_gates()         — fetch all gates for an idea
  get_results()       — fetch all results for an idea
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parents[2] / "db" / "research.db"
MYT     = timezone(timedelta(hours=8))

GATE_QUESTIONS = {
    1: "Premise: idea + one simple rule + thesis + a linked paper. Why should this edge exist?",
    2: "Edge & Survival: does the IS net-of-cost ledger show a smooth curve and acceptable drawdown?",
    3: "Robustness: does the IS edge survive walk-forward + Monte Carlo?",
    4: "Live: does the MT5 tester / demo / live ledger match within tolerance?",
}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def _protocol():
    """Lazy handle on the protocol module (it imports pipeline at load, so a
    top-level import here would be circular)."""
    from research.code.gates import protocol
    return protocol


def _strategy_log():
    """Lazy handle on the strategy_log module (avoids any load-order coupling)."""
    from research.code.lineage import strategy_log
    return strategy_log


def _is_config_frozen(idea_id: str) -> bool:
    """IS settings are 'locked' once at least one component has a VALIDATED/ADOPTED
    row in the strategy lineage — i.e. strategy_log.get_live_config() is non-empty.
    CREATED/PROPOSED (born, unproven) does NOT count: you freeze a config by
    validating it at the IS gate (Gate 5), then go out-of-sample."""
    return bool(_strategy_log().get_live_config(idea_id))


def _require_frozen_config(idea_id: str, what: str, allow_unfrozen: bool) -> None:
    """Block an out-of-sample action unless the IS config is frozen. Escape hatch:
    allow_unfrozen=True downgrades to a warning (e.g. a primitive with no strategy
    config to validate). The freeze rule: exhaust + VALIDATE IS params before OOS."""
    if _is_config_frozen(idea_id):
        return
    msg = (f"{what} blocked: IS config for {idea_id} is NOT frozen "
           f"(no VALIDATED/ADOPTED component in strategy_log). Exhaust IS params "
           f"and log_change(verdict='VALIDATED'/'ADOPTED') the chosen config BEFORE "
           f"going out-of-sample. Override with allow_unfrozen=True only if there is "
           f"genuinely no config to validate.")
    if allow_unfrozen:
        print(f"[pipeline] WARNING — {msg}")
        return
    raise ValueError(msg)


# ── Idea functions ─────────────────────────────────────────────────────────────

def add_idea(
    idea_id: str,
    name: str,
    description: str,
    category: str,
    parent_idea_id: str | None = None,
) -> str:
    """Insert a new idea into step1_ideas at status='ideation'. Returns idea_id."""
    now = _now()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO step1_ideas
                (idea_id, name, description, category, parent_idea_id,
                 status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'ideation', ?, ?)
        """, (idea_id, name, description, category, parent_idea_id, now, now))
        conn.commit()
    print(f"[pipeline] idea added: {idea_id} ({category})")
    return idea_id


# ── Gate functions ─────────────────────────────────────────────────────────────

def open_gate(
    idea_id: str,
    gate_number: int,
    pass_criteria: str,
    attempt: int = 1,
    allow_unfrozen: bool = False,
) -> int:
    """Create a gate row at status=open. Returns gate_id.

    G3 (Robustness = walk-forward + OOS + Monte Carlo) is the freeze chokepoint:
    you cannot enter the out-of-sample phase until the IS config is frozen (a
    VALIDATED/ADOPTED component in strategy_log). allow_unfrozen=True downgrades
    it to a warning."""
    if gate_number not in range(1, 5):
        raise ValueError(f"gate_number must be 1–4, got {gate_number}")

    _check_gate_applicable(idea_id, gate_number)
    _check_previous_gate_passed(idea_id, gate_number)
    if gate_number == 3:
        _require_frozen_config(idea_id, "open_gate(3) [Robustness / OOS phase]", allow_unfrozen)

    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO step3_gates
                (idea_id, gate_number, attempt, gate_question, pass_criteria,
                 status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
        """, (idea_id, gate_number, attempt,
              GATE_QUESTIONS[gate_number], pass_criteria, now, now))
        conn.commit()
        gate_id = cur.lastrowid

    _update_idea_status(idea_id, f"gate_{gate_number}")
    print(f"[pipeline] {idea_id} gate {gate_number} attempt {attempt}: opened")
    return gate_id


# ── 4.0 gate walls ───────────────────────────────────────────────────────────
# Only two gates carry a code-enforced wall (the rest are human reads, per the
# simplicity-first protocol):
#   G1 Premise        → idea tagged (idea_kind + output_type) AND ≥1 linked paper.
#   G2 Edge+Survival  → ≥1 logged NET-of-cost result (step4_results cost_adjusted=1).
# G3 (robustness) and G4 (live) pass on human judgement of the WF/MC + parity reads.
def _enforce_gate_walls(idea_id: str, gate_number: int, gate_answer: str,
                        allow_incomplete: bool) -> None:
    if allow_incomplete:
        return
    if gate_number == 1:
        idea = get_idea(idea_id)
        if not idea.get("idea_kind") or not idea.get("output_type"):
            raise ValueError(
                f"Cannot pass G1 (Premise) for {idea_id}: idea_kind / output_type must "
                f"be tagged at G1 (pipeline.update_idea). 4.0 declares them here.")
        with _conn() as conn:
            n_papers = conn.execute(
                "SELECT COUNT(*) AS n FROM step2_papers WHERE idea_id=?", (idea_id,)
            ).fetchone()["n"]
        if not n_papers:
            raise ValueError(
                f"Cannot pass G1 (Premise) for {idea_id}: every idea must link ≥1 research "
                f"paper before leaving G1 (step2_papers is mandatory in 4.0). Run the paper "
                f"pipeline (FIND→ACQUIRE→EXTRACT→DISSECT) and agent_log.log_dissect_result().")
    if gate_number == 2:
        with _conn() as conn:
            n_net = conn.execute(
                "SELECT COUNT(*) AS n FROM step4_results "
                "WHERE idea_id=? AND cost_adjusted=1", (idea_id,)
            ).fetchone()["n"]
        if not n_net:
            raise ValueError(
                f"Cannot pass G2 (Edge & Survival) for {idea_id}: no NET-of-cost result "
                f"logged. Emit the IS ledger and log_result(cost_adjusted=1) first, or pass "
                f"allow_incomplete=True with a waiver reason in gate_answer.")


def pass_gate(
    idea_id: str,
    gate_number: int,
    gate_answer: str,
    answered_by: str = "human",
    attempt: int = 1,
    allow_incomplete: bool = False,
) -> None:
    """Mark a gate as passed.

    4.0 gate walls (see _enforce_gate_walls):
      G1 Premise       — idea tagged (idea_kind + output_type) AND ≥1 linked paper.
      G2 Edge+Survival — ≥1 logged NET-of-cost result (cost_adjusted=1).
      G3 / G4          — human reads (WF/MC robustness, live parity), no code wall.
    allow_incomplete=True bypasses the wall (log a waiver reason in gate_answer).
    """
    _enforce_gate_walls(idea_id, gate_number, gate_answer, allow_incomplete)
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE step3_gates
            SET status='passed', gate_answer=?, answered_by=?,
                updated_at=?, answered_at=?
            WHERE idea_id=? AND gate_number=? AND attempt=?
        """, (gate_answer, answered_by, now, now, idea_id, gate_number, attempt))
        if cur.rowcount == 0:
            raise ValueError(f"Gate not found: {idea_id} gate={gate_number} attempt={attempt}")
        conn.commit()
    print(f"[pipeline] {idea_id} gate {gate_number}: PASSED")


def block_gate(
    idea_id: str,
    gate_number: int,
    gate_answer: str,
    answered_by: str = "human",
    attempt: int = 1,
) -> None:
    """Mark a gate as blocked with a reason."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE step3_gates
            SET status='blocked', gate_answer=?, answered_by=?,
                updated_at=?, answered_at=?
            WHERE idea_id=? AND gate_number=? AND attempt=?
        """, (gate_answer, answered_by, now, now, idea_id, gate_number, attempt))
        if cur.rowcount == 0:
            raise ValueError(f"Gate not found: {idea_id} gate={gate_number} attempt={attempt}")
        conn.commit()
    print(f"[pipeline] {idea_id} gate {gate_number}: BLOCKED — {gate_answer[:80]}")


def _falsified_count(idea_id: str) -> int:
    """How many distinct hypotheses have been FALSIFIED for this idea (log_strategy)."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM log_strategy WHERE idea_id=? AND verdict='FALSIFIED'",
            (idea_id,),
        ).fetchone()
    return row[0] if row else 0


def kill_idea(
    idea_id: str,
    gate_number: int,
    kill_reason: str,
    answered_by: str = "human",
    attempt: int = 1,
    force: bool = False,
) -> None:
    """Kill an idea at a gate. Updates both gate row and idea row.

    Multi-hypothesis kill guard (CLAUDE.md rule 8b): refuses to kill unless >=2
    hypotheses have been FALSIFIED in log_strategy — the base/symmetric framing
    PLUS at least one directional/conditional variant. A single dead hypothesis
    is a REFRAME trigger, not a kill. Pass force=True ONLY for legitimate
    single-hypothesis kills (e.g. Gate 0 non-novelty, Gate 1 no testable spec) —
    and say why in kill_reason.
    """
    if not force:
        n = _falsified_count(idea_id)
        if n < 2:
            raise ValueError(
                f"kill_idea BLOCKED (rule 8b): {idea_id} has only {n} FALSIFIED "
                f"hypothesis(es) in log_strategy; >=2 required before kill. "
                f"A dead hypothesis is a reframe trigger, not a kill — test a "
                f"directional/conditional variant first. If this is a legitimate "
                f"single-hypothesis kill (Gate 0/1 non-novelty/no-spec), pass "
                f"force=True and justify in kill_reason."
            )
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            UPDATE step3_gates
            SET status='killed', gate_answer=?, answered_by=?,
                updated_at=?, answered_at=?
            WHERE idea_id=? AND gate_number=? AND attempt=?
        """, (kill_reason, answered_by, now, now, idea_id, gate_number, attempt))

        cur.execute("""
            UPDATE step1_ideas
            SET status='killed', kill_gate=?, kill_reason=?,
                killed_at=?, updated_at=?
            WHERE idea_id=?
        """, (gate_number, kill_reason, now, now, idea_id))

        conn.commit()
    print(f"[pipeline] {idea_id} gate {gate_number}: KILLED — {kill_reason[:80]}")


# ── Result logging ─────────────────────────────────────────────────────────────

def log_result(
    idea_id: str,
    gate_number: int,
    stage: str,
    metric_key: str,
    metric_value: float,
    cost_adjusted: int,
    period: str,
    n_obs: int,
    data_start: str,
    data_end: str,
    git_sha: str,
    code_path: str,
    is_run: str = None,
    what_changed: str = None,
    instrument: str = "XAUUSD",
    parameters: str = None,
    data_hash: str = None,
    seed: int = None,
    notes: str = None,
    allow_unfrozen: bool = False,
) -> int:
    """Log a metric result. Returns result_id.

    4.0 IS-discipline guards:
      - is_run is REQUIRED on IS/OOS rows → every IS experiment carries a run label
        (IS-01, IS-02…) so the degrees of freedom (shots taken before G3) stay
        visible. Just pass is_run='IS-01' (+ optional what_changed); the shot count
        is DISTINCT is_run over step4_results — no separate registry to pre-fill.
      - stage='OOS' is BLOCKED unless the IS config is frozen (see
        _require_frozen_config). allow_unfrozen=True downgrades it to a warning.
    """
    valid_stages  = ("IS", "walkforward", "montecarlo", "OOS")
    valid_periods = ("per_trade", "daily", "annualised")

    if stage not in valid_stages:
        raise ValueError(f"stage must be one of {valid_stages}")
    if period not in valid_periods:
        raise ValueError(f"period must be one of {valid_periods}")
    if cost_adjusted not in (0, 1):
        raise ValueError("cost_adjusted must be 0 (raw) or 1 (net)")
    if not git_sha:
        raise ValueError("git_sha is required — run `git rev-parse --short HEAD`")
    if not n_obs:
        raise ValueError("n_obs is required")
    if stage in ("IS", "OOS") and not is_run:
        raise ValueError(
            f"is_run is required for stage='{stage}' results — pass is_run='IS-01' "
            f"(IS-02…) so the shots taken before G3 are counted; an OOS row names the "
            f"IS run it validates.")
    if stage == "OOS":
        _require_frozen_config(idea_id, f"log_result(stage='OOS', {metric_key})",
                               allow_unfrozen)

    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO step4_results
                (idea_id, gate_number, stage, metric_key, metric_value,
                 cost_adjusted, period, n_obs, is_run, what_changed,
                 instrument, data_start, data_end, parameters,
                 git_sha, data_hash, seed, code_path, notes, logged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idea_id, gate_number, stage, metric_key, metric_value,
            cost_adjusted, period, n_obs, is_run, what_changed,
            instrument, data_start, data_end, parameters,
            git_sha, data_hash, seed, code_path, notes, now,
        ))
        conn.commit()
        result_id = cur.lastrowid

    label = "net" if cost_adjusted else "raw"
    print(f"[pipeline] {idea_id} gate={gate_number} {stage} {metric_key}={metric_value} [{label}|{period}]")
    return result_id


def get_is_runs(idea_id: str) -> list[dict]:
    """The distinct IS runs for an idea, oldest first — answers 'how many shots before
    G3?'. The deflator that replaced DSR/N_trials: one entry per is_run label seen on
    step4_results (no separate registry since migration 029 — the label lives on the
    result row, count = len of this list). `what_changed` is the first non-null seen
    for that label."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT is_run AS label,
                   MIN(logged_at)                       AS first_logged_at,
                   MAX(what_changed)                    AS what_changed,
                   COUNT(*)                             AS n_results
            FROM step4_results
            WHERE idea_id=? AND is_run IS NOT NULL
            GROUP BY is_run
            ORDER BY first_logged_at ASC
        """, (idea_id,)).fetchall()
    return [dict(r) for r in rows]


def delete_result(result_id: int) -> None:
    """Remove one step4_results row. Narrow purpose: the run_and_log harness calls
    this to compensate (roll back) an already-inserted result when the paired
    strategy_log.log_change() fails — so a result never lingers without its verdict
    when one was demanded. Not for hand-editing history."""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM step4_results WHERE result_id=?", (result_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"no step4_results row with result_id={result_id}")
    print(f"[pipeline] deleted result_id={result_id} (harness compensation)")


# ── Read functions ─────────────────────────────────────────────────────────────

def get_idea(idea_id: str) -> dict:
    """Return the idea row as a dict. Empty dict if not found."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM step1_ideas WHERE idea_id=?", (idea_id,))
        row = cur.fetchone()
        return dict(row) if row else {}


def get_gates(idea_id: str) -> list[dict]:
    """Return all gate rows for an idea, ordered by gate_number then attempt."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM step3_gates WHERE idea_id=? ORDER BY gate_number, attempt",
            (idea_id,)
        )
        return [dict(r) for r in cur.fetchall()]


def get_results(idea_id: str) -> list[dict]:
    """Return all result rows for an idea, ordered by gate_number then logged_at."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM step4_results WHERE idea_id=? ORDER BY gate_number, logged_at",
            (idea_id,)
        )
        return [dict(r) for r in cur.fetchall()]


def get_lifecycle() -> list[dict]:
    """Return the idea_lifecycle view — one row per idea."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM idea_lifecycle ORDER BY idea_id")
        return [dict(r) for r in cur.fetchall()]


IDEA_KINDS = {"strategy", "primitive", "overlay", "classifier"}
OUTPUT_TYPES = {"pnl_stream", "classifier_score", "primitive_output"}


def update_idea(idea_id: str, **fields) -> None:
    """Update descriptive idea fields (name / description / category / parent_idea_id /
    idea_kind / output_type). Bumps updated_at. Status changes go through the gate/kill
    functions, not here. idea_kind + output_type drive Protocol 3.2 gate-variant +
    significance-test selection (docs/specs/2026-06-15-research-protocol-3.2-generic-gating.md)."""
    allowed = {"name", "description", "category", "parent_idea_id",
               "idea_kind", "output_type"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"cannot update {bad}; allowed: {allowed}")
    if "idea_kind" in fields and fields["idea_kind"] not in IDEA_KINDS:
        raise ValueError(f"idea_kind must be one of {IDEA_KINDS}")
    if "output_type" in fields and fields["output_type"] not in OUTPUT_TYPES:
        raise ValueError(f"output_type must be one of {OUTPUT_TYPES}")
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
    vals = list(fields.values()) + [_now(), idea_id]
    with _conn() as conn:
        conn.execute(f"UPDATE step1_ideas SET {sets} WHERE idea_id=?", vals)
        conn.commit()


# ── Internal helpers ───────────────────────────────────────────────────────────

def _check_gate_applicable(idea_id: str, gate_number: int) -> None:
    """Protocol 3.2: refuse to open a gate that does not apply to the idea_kind
    (e.g. Gate 3 on a `primitive`). Untagged ideas get the full ladder (back-compat).
    docs/specs/2026-06-15-research-protocol-3.2-generic-gating.md."""
    protocol = _protocol()  # lazy: avoid the protocol<->pipeline import cycle at load
    kind = get_idea(idea_id).get("idea_kind")
    gates = protocol.applicable_gates(kind)
    if gate_number not in gates:
        raise ValueError(
            f"Cannot open gate {gate_number}: not applicable to idea_kind={kind!r} "
            f"(applicable gates: {sorted(gates)}). Protocol 3.2 legal skip."
        )


def _check_previous_gate_passed(idea_id: str, gate_number: int) -> None:
    """Raise if the previous APPLICABLE gate is not passed. Protocol 3.2: an
    idea_kind may legally skip gates (primitive skips 3-6), so the predecessor is
    the highest applicable gate below this one, not literally N-1."""
    protocol = _protocol()  # lazy: avoid the protocol<->pipeline import cycle at load
    gates = protocol.applicable_gates(get_idea(idea_id).get("idea_kind"))
    prev = max((g for g in gates if g < gate_number), default=None)
    if prev is None:
        return  # this is the first applicable gate (G1)
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT status FROM step3_gates
            WHERE idea_id=? AND gate_number=?
            ORDER BY attempt DESC LIMIT 1
        """, (idea_id, prev))
        row = cur.fetchone()
        if not row or row["status"] != "passed":
            raise ValueError(
                f"Cannot open gate {gate_number}: previous applicable gate {prev} is not passed"
            )


def _update_idea_status(idea_id: str, new_status: str) -> None:
    now = _now()
    with _conn() as conn:
        conn.execute(
            "UPDATE step1_ideas SET status=?, updated_at=? WHERE idea_id=?",
            (new_status, now, idea_id)
        )
        conn.commit()
