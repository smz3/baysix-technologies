# ORB-001 $50 Equity Simulator + Backlog Table — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove (or kill) whether a real $50 XAUUSD account can survive trading the validated ORB-001 London edge, and add a queryable `step6_backlog` table so research follow-ups stop getting lost.

**Architecture:** Two units. (1) `step6_backlog` table + `research/code/backlog.py` write/read layer + additive migration. (2) `research/models/orb/equity_sim.py` — converts each ORB trade's R-multiple into real dollars (`R × range_w × 100 × lot`), walks a $50 balance through the OOS slice under a % survival skip-filter, sweeps the cap, and emits a quantstats tearsheet + plotly equity curve + console verdict. Edge is already proven in R; this only tests survival — no gate re-runs.

**Tech Stack:** Python 3.13, pandas/numpy, sqlite3 (via existing `research/code/` layer), quantstats 0.0.81, plotly 6.5.0, pytest 9.0.2.

**Spec:** [2026-06-07-orb-equity-sim-and-backlog-design.md](../specs/2026-06-07-orb-equity-sim-and-backlog-design.md)

---

## File Structure

- Create: `research/code/backlog.py` — backlog write/read layer (mirrors `agent_log.py` patterns: MYT timestamps, `_conn()`, validation).
- Modify: `research/code/db_init.py` — add `step6_backlog` table + `open_backlog` view (CREATE … IF NOT EXISTS).
- Create: `research/migrations/012_create_backlog.py` — additive migration + seed rows.
- Create: `research/models/orb/equity_sim.py` — dollar sim, survival filter, cap sweep, outputs.
- Create: `research/tests/test_backlog.py` — round-trip + constraint tests.
- Create: `research/tests/test_equity_sim.py` — dollar-conversion + filter + ruin tests.
- Outputs (generated, gitignored): `research/outputs/orb001_equity_*.html`.

---

## Task 1: `step6_backlog` table + view in db_init

**Files:**
- Modify: `research/code/db_init.py` (inside the `executescript` block, after `step5_agent_log`)

- [ ] **Step 1: Add the table + view to the schema script**

In `research/code/db_init.py`, immediately after the `step5_agent_log` CREATE TABLE (before `DROP VIEW IF EXISTS idea_lifecycle;`), insert:

```sql
        CREATE TABLE IF NOT EXISTS step6_backlog (
            task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id     TEXT REFERENCES step1_ideas(idea_id),
            title       TEXT NOT NULL,
            detail      TEXT,
            kind        TEXT NOT NULL CHECK(kind IN
                          ('variant','sizing','filter','port','infra','data','cleanup')),
            priority    TEXT NOT NULL DEFAULT 'P2'
                          CHECK(priority IN ('P0','P1','P2')),
            status      TEXT NOT NULL DEFAULT 'open'
                          CHECK(status IN ('open','in_progress','done','dropped')),
            created_at  DATETIME NOT NULL,
            updated_at  DATETIME NOT NULL,
            resolved_at DATETIME,
            resolution  TEXT
        );

        DROP VIEW IF EXISTS open_backlog;
        CREATE VIEW open_backlog AS
        SELECT b.task_id, b.idea_id, i.name AS idea_name, b.title,
               b.kind, b.priority, b.status,
               CAST((julianday('now') - julianday(b.created_at)) AS INTEGER) AS age_days
        FROM step6_backlog b
        LEFT JOIN step1_ideas i ON i.idea_id = b.idea_id
        WHERE b.status IN ('open','in_progress')
        ORDER BY b.priority ASC, b.created_at ASC;
```

- [ ] **Step 2: Apply to the live DB (idempotent)**

Run: `python research/code/db_init.py`
Expected: `research.db ready -> ...` and no error. Existing tables/data untouched (all `IF NOT EXISTS`).

- [ ] **Step 3: Verify table exists**

Run: `python -c "import sqlite3; c=sqlite3.connect('research/db/research.db'); print([r[1] for r in c.execute('PRAGMA table_info(step6_backlog)')])"`
Expected: `['task_id', 'idea_id', 'title', 'detail', 'kind', 'priority', 'status', 'created_at', 'updated_at', 'resolved_at', 'resolution']`

- [ ] **Step 4: Commit**

```bash
git add research/code/db_init.py
git commit -m "feat(research): add step6_backlog table + open_backlog view"
```

---

## Task 2: `backlog.py` code layer (TDD)

**Files:**
- Create: `research/code/backlog.py`
- Create: `research/tests/test_backlog.py`

- [ ] **Step 1: Write the failing tests**

Create `research/tests/test_backlog.py`:

```python
import sqlite3
from pathlib import Path

import pytest

from research.code import backlog, db_init


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "research.db"
    monkeypatch.setattr(db_init, "DB_PATH", db)
    monkeypatch.setattr(backlog, "DB_PATH", db)
    db_init.init()
    return db


def test_add_and_get(tmp_db):
    tid = backlog.add_task("Build X", kind="infra", detail="why", priority="P1")
    assert isinstance(tid, int)
    rows = backlog.get_backlog(status="open")
    assert len(rows) == 1
    assert rows[0]["title"] == "Build X"
    assert rows[0]["kind"] == "infra"
    assert rows[0]["priority"] == "P1"
    assert rows[0]["status"] == "open"


def test_update_and_resolve(tmp_db):
    tid = backlog.add_task("Task", kind="sizing")
    backlog.update_task(tid, status="in_progress", priority="P0")
    r = backlog.get_backlog(status="in_progress")[0]
    assert r["priority"] == "P0"
    backlog.resolve_task(tid, resolution="done it")
    assert backlog.get_backlog(status="open") == []
    done = backlog.get_backlog(status="done")[0]
    assert done["resolution"] == "done it"
    assert done["resolved_at"] is not None


def test_bad_kind_rejected(tmp_db):
    with pytest.raises(sqlite3.IntegrityError):
        backlog.add_task("Bad", kind="nonsense")


def test_filter_by_idea(tmp_db):
    backlog.add_task("A", kind="infra")
    backlog.add_task("B", kind="port", idea_id=None)
    rows = backlog.get_backlog(status="open", idea_id=None)
    assert len(rows) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest research/tests/test_backlog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.code.backlog'`

- [ ] **Step 3: Write `research/code/backlog.py`**

```python
"""
Backlog interface for research.db (step6_backlog).
Research/eng follow-ups that are NOT falsifiable ideas (ideas live in step1_ideas).
All writes go through here — no raw SQL elsewhere (CLAUDE.md rule 15).
"""
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"
MYT = timezone(timedelta(hours=8))

_VALID_KIND = ("variant", "sizing", "filter", "port", "infra", "data", "cleanup")
_VALID_PRIORITY = ("P0", "P1", "P2")
_VALID_STATUS = ("open", "in_progress", "done", "dropped")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def add_task(title: str, kind: str, detail: str = "", idea_id: str = None,
             priority: str = "P2") -> int:
    """Add a backlog task. Returns task_id."""
    if priority not in _VALID_PRIORITY:
        raise ValueError(f"priority must be one of {_VALID_PRIORITY}")
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO step6_backlog
                (idea_id, title, detail, kind, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
        """, (idea_id, title, detail, kind, priority, now, now))
        conn.commit()
        task_id = cur.lastrowid
    print(f"[backlog] task_id={task_id} [{kind}|{priority}] {title}")
    return task_id


def update_task(task_id: int, **fields) -> None:
    """Update status / priority / detail / title / kind. Bumps updated_at."""
    allowed = {"status", "priority", "detail", "title", "kind"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"cannot update {bad}; allowed: {allowed}")
    if "status" in fields and fields["status"] not in _VALID_STATUS:
        raise ValueError(f"status must be one of {_VALID_STATUS}")
    if "priority" in fields and fields["priority"] not in _VALID_PRIORITY:
        raise ValueError(f"priority must be one of {_VALID_PRIORITY}")
    sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
    vals = list(fields.values()) + [_now(), task_id]
    with _conn() as conn:
        conn.execute(f"UPDATE step6_backlog SET {sets} WHERE task_id=?", vals)
        conn.commit()


def resolve_task(task_id: int, resolution: str, status: str = "done") -> None:
    """Mark a task done/dropped with a resolution note."""
    if status not in ("done", "dropped"):
        raise ValueError("resolve status must be 'done' or 'dropped'")
    now = _now()
    with _conn() as conn:
        conn.execute("""
            UPDATE step6_backlog
            SET status=?, resolution=?, resolved_at=?, updated_at=?
            WHERE task_id=?
        """, (status, resolution, now, now, task_id))
        conn.commit()
    print(f"[backlog] task_id={task_id} -> {status}")


def get_backlog(status: str = "open", idea_id: str = "__any__") -> list[dict]:
    """Return backlog rows filtered by status (and optionally idea_id).
    Pass idea_id=None to match rows with NULL idea_id; omit to match any idea_id."""
    q = "SELECT * FROM step6_backlog WHERE status=?"
    params = [status]
    if idea_id != "__any__":
        if idea_id is None:
            q += " AND idea_id IS NULL"
        else:
            q += " AND idea_id=?"
            params.append(idea_id)
    q += " ORDER BY priority ASC, created_at ASC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
```

> Note: `get_backlog(idea_id=None)` in the test matches the "any" default-less call — the test passes `idea_id=None` expecting all rows. Implementation: the sentinel `"__any__"` is the true default; the test's explicit `None` will hit the `IS NULL` branch, and both seeded rows have NULL idea_id, so it returns 2. ✔

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest research/tests/test_backlog.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add research/code/backlog.py research/tests/test_backlog.py
git commit -m "feat(research): backlog.py code layer + tests"
```

---

## Task 3: Migration 012 + seed the 6 follow-ups

**Files:**
- Create: `research/migrations/012_create_backlog.py`

- [ ] **Step 1: Write the migration (idempotent: ensures table, seeds only if empty)**

Create `research/migrations/012_create_backlog.py`:

```python
"""
Migration 012 — create step6_backlog (via db_init) and seed the initial follow-ups.
Additive + idempotent: re-running does not duplicate seeds (guards on empty table).

Run: python research/migrations/012_create_backlog.py
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
```

- [ ] **Step 2: Run the migration**

Run: `python research/migrations/012_create_backlog.py`
Expected: 6 `[backlog] task_id=…` lines then `seeded 6 backlog tasks.`

- [ ] **Step 3: Verify via the view**

Run: `python -c "import sqlite3; c=sqlite3.connect('research/db/research.db'); [print(r) for r in c.execute('SELECT task_id,kind,priority,title FROM open_backlog')]"`
Expected: 6 rows, P1s before P2s.

- [ ] **Step 4: Commit**

```bash
git add research/migrations/012_create_backlog.py
git commit -m "feat(research): migration 012 — seed backlog with 6 ORB follow-ups"
```

---

## Task 4: Equity simulator — dollar conversion core (TDD)

**Files:**
- Create: `research/models/orb/equity_sim.py`
- Create: `research/tests/test_equity_sim.py`

- [ ] **Step 1: Write the failing tests for the pure conversion**

Create `research/tests/test_equity_sim.py`:

```python
import pandas as pd
import pytest

from research.models.orb import equity_sim as es


def test_trade_pnl_usd_loss_min_lot():
    # -1R, range_w=$3, min lot 0.01 -> -$3.00 exactly (R * range_w * 100 * lot)
    assert es.trade_pnl_usd(R=-1.0, range_w=3.0, lot=0.01) == pytest.approx(-3.0)


def test_trade_pnl_usd_win_min_lot():
    # +3R, range_w=$3, min lot -> +$9.00
    assert es.trade_pnl_usd(R=3.0, range_w=3.0, lot=0.01) == pytest.approx(9.0)


def test_trade_pnl_scales_with_lot():
    assert es.trade_pnl_usd(R=1.0, range_w=5.0, lot=0.02) == pytest.approx(10.0)


def test_used_margin_tiny_at_high_leverage():
    # 0.01 lot at $3300, 1:3000 -> notional 3300, margin ~1.10
    assert es.used_margin_usd(entry_px=3300.0, lot=0.01, leverage=3000) == pytest.approx(1.10, abs=0.01)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest research/tests/test_equity_sim.py -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError: module … has no attribute 'trade_pnl_usd'`.

- [ ] **Step 3: Write the module header + pure helpers**

Create `research/models/orb/equity_sim.py`:

```python
"""
ORB-001 $50 dollar-equity simulator (survival test).

Edge is ALREADY proven in R-multiples (G0-G6). This converts each ORB trade's
R-multiple into REAL dollars on a $50 account and walks the balance through the
OOS slice under a survival skip-filter, to answer: can $50 survive this edge?

Dollar math (JM XAUUSD.s, brokers/justmarkets.yaml):
  contract = 100 oz/lot, min lot 0.01, lot_step 0.01.
  pnl_usd = R * range_w * 100 * lot      (range_w = 1R in price $/oz)
  On min lot 0.01: pnl_usd = R * range_w  (a -1R loss costs range_w dollars).

Costs: spread already embedded in R as a win-rate drag (do NOT re-deduct);
swap $0 (swap-free + EOD-flat); commission $0 (Pro). Spread is the only cost.

    python research/models/orb/equity_sim.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

CONTRACT_OZ = 100.0
MIN_LOT = 0.01
LEVERAGE = 3000          # JM dynamic max for XAUUSD
STOPOUT_PCT = 20.0       # equity/used_margin*100 < 20 -> stop out


def trade_pnl_usd(R: float, range_w: float, lot: float = MIN_LOT) -> float:
    """Dollar P&L of one trade. range_w = 1R in price ($/oz)."""
    return R * range_w * CONTRACT_OZ * lot


def used_margin_usd(entry_px: float, lot: float = MIN_LOT,
                    leverage: int = LEVERAGE) -> float:
    """Margin to hold the position = notional / leverage."""
    notional = entry_px * CONTRACT_OZ * lot
    return notional / leverage
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest research/tests/test_equity_sim.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add research/models/orb/equity_sim.py research/tests/test_equity_sim.py
git commit -m "feat(research): ORB equity sim — dollar conversion core + tests"
```

---

## Task 5: Equity walk — survival filter + ruin detection (TDD)

**Files:**
- Modify: `research/models/orb/equity_sim.py`
- Modify: `research/tests/test_equity_sim.py`

- [ ] **Step 1: Add failing tests for the walk**

Append to `research/tests/test_equity_sim.py`:

```python
def _df(rows):
    # rows: list of (R, range_w, entry_px, date)
    return pd.DataFrame(
        [{"R": r, "range_w": w, "entry_px": p, "date": d} for r, w, p, d in rows]
    )


def test_walk_simple_growth():
    # two +3R wins, range_w=$1, min lot -> +$3 each -> $50 -> $56
    df = _df([(3.0, 1.0, 2000.0, "2024-05-02"), (3.0, 1.0, 2000.0, "2024-05-03")])
    out = es.simulate_equity(df, start=50.0)
    assert out["summary"]["terminal_equity"] == pytest.approx(56.0)
    assert out["summary"]["blew_up"] is False
    assert out["summary"]["n_taken"] == 2


def test_walk_ruin_on_loss_string():
    # range_w=$30, -1R each -> -$30/trade; $50 -> $20 -> blow up (can't take 3rd)
    df = _df([(-1.0, 30.0, 2000.0, f"2024-05-0{i}") for i in range(2, 6)])
    out = es.simulate_equity(df, start=50.0)
    assert out["summary"]["blew_up"] is True
    assert out["summary"]["terminal_equity"] < 50.0


def test_survival_filter_skips_oversized_risk():
    # range_w=$30 -> risk $30 = 60% of $50; cap 10% -> skip every trade
    df = _df([(3.0, 30.0, 2000.0, "2024-05-02")])
    out = es.simulate_equity(df, start=50.0, risk_cap_pct=10.0)
    assert out["summary"]["n_taken"] == 0
    assert out["summary"]["n_skipped"] == 1
    assert out["summary"]["terminal_equity"] == pytest.approx(50.0)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest research/tests/test_equity_sim.py -v`
Expected: FAIL — `AttributeError: … 'simulate_equity'`.

- [ ] **Step 3: Implement `simulate_equity`**

Append to `research/models/orb/equity_sim.py`:

```python
def simulate_equity(trades: pd.DataFrame, start: float = 50.0,
                    lot: float = MIN_LOT, risk_cap_pct: float | None = None,
                    leverage: int = LEVERAGE) -> dict:
    """
    Walk a dollar balance through trades in date order.

    risk_cap_pct: skip a trade if its $ risk (range_w * 100 * lot) exceeds this
                  % of CURRENT equity. None = take every affordable trade.
    Blow-up: equity can no longer fund the min-lot margin (or hits <= 0).

    Returns {"curve": DataFrame, "summary": dict}.
    """
    df = trades.sort_values("date").reset_index(drop=True)
    equity = start
    peak = start
    max_dd = 0.0
    n_taken = n_skipped = 0
    streak = worst_streak = 0
    blew_up = False
    curve = []

    for _, t in df.iterrows():
        risk_usd = abs(t["range_w"]) * CONTRACT_OZ * lot
        margin = used_margin_usd(t["entry_px"], lot, leverage)

        # ruin: cannot even open the minimum position
        if equity <= 0 or equity < margin:
            blew_up = True
            break

        # survival skip-filter
        if risk_cap_pct is not None and equity > 0 and (risk_usd / equity) * 100.0 > risk_cap_pct:
            n_skipped += 1
            curve.append({"date": t["date"], "equity": equity, "action": "skip"})
            continue

        pnl = trade_pnl_usd(t["R"], t["range_w"], lot)
        equity += pnl
        n_taken += 1
        streak = streak + 1 if pnl < 0 else 0
        worst_streak = max(worst_streak, streak)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
        curve.append({"date": t["date"], "equity": equity, "action": "trade"})

        if equity <= 0:
            blew_up = True
            break

    curve_df = pd.DataFrame(curve)
    summary = {
        "start_equity": start,
        "terminal_equity": equity,
        "return_pct": (equity / start - 1.0) * 100.0,
        "max_drawdown_pct": max_dd * 100.0,
        "worst_losing_streak": worst_streak,
        "n_taken": n_taken,
        "n_skipped": n_skipped,
        "blew_up": blew_up,
        "risk_cap_pct": risk_cap_pct,
    }
    return {"curve": curve_df, "summary": summary}
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest research/tests/test_equity_sim.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add research/models/orb/equity_sim.py research/tests/test_equity_sim.py
git commit -m "feat(research): ORB equity sim — walk + survival filter + ruin detection"
```

---

## Task 6: Cap sweep + outputs (tearsheet, plotly, console)

**Files:**
- Modify: `research/models/orb/equity_sim.py`

- [ ] **Step 1: Add the daily-returns helper test**

Append to `research/tests/test_equity_sim.py`:

```python
def test_daily_returns_from_curve():
    df = _df([(3.0, 1.0, 2000.0, "2024-05-02"), (-1.0, 1.0, 2000.0, "2024-05-03")])
    out = es.simulate_equity(df, start=50.0)
    rets = es.daily_returns(out["curve"], start=50.0)
    # day1: 50->53 (+6%), day2: 53->52 (-1.886%)
    assert rets.iloc[0] == pytest.approx(0.06, abs=1e-4)
    assert rets.iloc[1] == pytest.approx(-1.0 / 53.0, abs=1e-4)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest research/tests/test_equity_sim.py::test_daily_returns_from_curve -v`
Expected: FAIL — no `daily_returns`.

- [ ] **Step 3: Implement `daily_returns` + sweep + outputs + `main`**

Append to `research/models/orb/equity_sim.py`:

```python
def daily_returns(curve: pd.DataFrame, start: float) -> pd.Series:
    """Per-trade-day fractional returns from the equity curve (for quantstats)."""
    eq = curve[curve["action"] != "skip"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.set_index("date")["equity"]
    prev = eq.shift(1)
    prev.iloc[0] = start
    return (eq / prev - 1.0).rename("returns")


def load_oos_trades(n_minutes: int = 5, target_R: float = 3.0) -> pd.DataFrame:
    """Run the frozen ORB config on the sealed OOS slice -> trade DataFrame."""
    from research.models.orb.orb_backtest import run_backtest_multi
    months = [(y, m) for y in range(2024, 2027) for m in range(1, 13) if (y, m) >= (2024, 5)]
    runs = run_backtest_multi(months, n_list=[n_minutes], is_only=False,
                              spread_price=2.0 * 0.10, target_R=target_R, oos_only=True)
    return runs[n_minutes]


def sweep_caps(trades: pd.DataFrame, caps=(5.0, 10.0, 15.0, 20.0, None),
               start: float = 50.0) -> pd.DataFrame:
    """Run the sim across survival-cap settings; one summary row per cap."""
    rows = []
    for cap in caps:
        s = simulate_equity(trades, start=start, risk_cap_pct=cap)["summary"]
        rows.append(s)
    return pd.DataFrame(rows)


def write_outputs(curve: pd.DataFrame, start: float, out_dir: Path, tag: str) -> None:
    """quantstats tearsheet (HTML) + custom plotly equity/drawdown curve."""
    import plotly.graph_objects as go

    out_dir.mkdir(parents=True, exist_ok=True)
    rets = daily_returns(curve, start)

    try:
        import quantstats as qs
        qs.reports.html(rets, output=str(out_dir / f"orb001_equity_{tag}_tearsheet.html"),
                        title=f"ORB-001 $50 survival — {tag}")
    except Exception as e:  # quantstats can be brittle on tiny/edge series
        print(f"[warn] quantstats tearsheet skipped: {e}")

    eq = curve[curve["action"] != "skip"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    peak = eq["equity"].cummax()
    dd = (eq["equity"] - peak) / peak * 100.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq["date"], y=eq["equity"], name="Equity ($)", yaxis="y1"))
    fig.add_trace(go.Scatter(x=eq["date"], y=dd, name="Drawdown (%)", yaxis="y2",
                             line=dict(dash="dot")))
    fig.update_layout(
        title=f"ORB-001 $50 equity & drawdown — {tag}",
        yaxis=dict(title="Equity ($)"),
        yaxis2=dict(title="Drawdown (%)", overlaying="y", side="right"),
    )
    fig.write_html(str(out_dir / f"orb001_equity_{tag}_curve.html"))


def main() -> None:
    out_dir = Path(__file__).resolve().parents[3] / "research" / "outputs"
    print("=" * 84)
    print("ORB-001 $50 EQUITY SIMULATOR — OOS survival (min-lot, Mode A)")
    print("=" * 84)
    trades = load_oos_trades()
    print(f"OOS trades: {len(trades)}  ({trades['date'].min()} -> {trades['date'].max()})\n")

    sweep = sweep_caps(trades)
    cols = ["risk_cap_pct", "terminal_equity", "return_pct", "max_drawdown_pct",
            "worst_losing_streak", "n_taken", "n_skipped", "blew_up"]
    print(sweep[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # write outputs for the no-cap baseline + best surviving cap
    base = simulate_equity(trades, start=50.0, risk_cap_pct=None)
    write_outputs(base["curve"], 50.0, out_dir, tag="nocap")
    survivors = sweep[~sweep["blew_up"]].sort_values("terminal_equity", ascending=False)
    if len(survivors):
        best_cap = survivors.iloc[0]["risk_cap_pct"]
        best = simulate_equity(trades, start=50.0, risk_cap_pct=best_cap)
        write_outputs(best["curve"], 50.0, out_dir, tag=f"cap{best_cap:g}")
        print(f"\nBest surviving cap: {best_cap}%  -> terminal ${best['summary']['terminal_equity']:,.2f}")
    else:
        print("\nNo cap setting survived — $50 cannot trade this edge at min-lot.")
    print(f"\noutputs -> {out_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the unit test**

Run: `python -m pytest research/tests/test_equity_sim.py -v`
Expected: 8 passed.

- [ ] **Step 5: Run the full sim in a visible window (rule 8 / 17 — long run)**

Run (PowerShell):
```powershell
Start-Process powershell -ArgumentList '-NoExit','-Command','cd ''c:\Users\User\Desktop\baysix-technologies''; python research/models/orb/equity_sim.py'
```
Expected: a sweep table (one row per cap), a "best surviving cap" or "no cap survived" line, and two HTML files in `research/outputs/`. **Sanity-check before logging:** terminal equity finite, n_taken+n_skipped == len(trades) per row, blew_up boolean sensible.

- [ ] **Step 6: Commit**

```bash
git add research/models/orb/equity_sim.py research/tests/test_equity_sim.py
git commit -m "feat(research): ORB equity sim — cap sweep + quantstats/plotly outputs"
```

---

## Task 7: Log survival result to DB

**Files:**
- (No new file — a one-off logging call using the verified numbers from Task 6's run.)

- [ ] **Step 1: Capture the run's headline numbers**

From the Task 6 sweep output, note for the **no-cap baseline** and the **best surviving cap**: `terminal_equity`, `max_drawdown_pct`, `blew_up`, `n_taken`. Get the commit sha:

Run: `git rev-parse --short HEAD`

- [ ] **Step 2: Log to step4_results + log the human decision (fill the real numbers in)**

Run (replace ALLCAPS with the verified values from Step 1):
```bash
python -c "import sys; sys.path.insert(0,'.'); from research.code import pipeline, agent_log; \
rid = pipeline.log_result(idea_id='ORB-001', gate_number=6, stage='OOS', \
  metric_key='terminal_equity_usd_nocap_minlot', metric_value=TERMINAL_NOCAP, cost_adjusted=1, \
  period='daily', n_obs=N_TAKEN, data_start='2024-05-02', data_end='2026-05-18', \
  git_sha='SHA', code_path='research/models/orb/equity_sim.py', \
  notes='$50 start, min-lot 0.01, Mode A no-cap. max_dd=MAXDD%, blew_up=BLEWUP. Spread already in R.'); \
agent_log.log_agent_call(idea_id='ORB-001', gate_number=6, gear='VALIDATE', model='opus', \
  task_summary='ORB-001 \$50 OOS survival sim (Mode A min-lot + cap sweep)', \
  output_summary='Best surviving cap=CAP%% -> terminal \$BESTTERM (no-cap \$TERMINAL_NOCAP, blew_up=BLEWUP). Survival verdict: VERDICT.', \
  result_id=rid)"
```
Expected: `[pipeline] ORB-001 gate=6 OOS …` and `[agent_log] call_id=…`.

- [ ] **Step 3: Verify the rows landed**

Run: `python -c "import sqlite3; c=sqlite3.connect('research/db/research.db'); print(c.execute('SELECT metric_key,metric_value FROM step4_results WHERE idea_id=\"ORB-001\" ORDER BY result_id DESC LIMIT 1').fetchone())"`
Expected: the terminal-equity row you just logged.

- [ ] **Step 4: Mark the equity-sim follow-up done; commit + push**

```bash
python -c "import sys; sys.path.insert(0,'.'); from research.code import backlog; \
[backlog.resolve_task(t['task_id'], 'Mode A done: $50 OOS survival sim built + run + logged') \
 for t in backlog.get_backlog('open','ORB-001') if t['title'].startswith('ORB equity sim — Mode B')==False and 'Mode A' in t['title']]" 2>/dev/null; \
git add -A && git commit -m "feat(research): ORB-001 \$50 survival result logged to step4_results" && git push
```
> Note: there is no "Mode A" backlog row (Mode A is this session's deliverable, not a backlog item) — the equity sim itself was the session goal. Skip the resolve loop if it matches nothing; just commit + push. Mode B remains open in the backlog.

---

## Self-Review

**Spec coverage:**
- Equity sim location/input/dollar-math → Tasks 4–5. ✔
- Spread-in-R / margin-not-the-wall → encoded in `simulate_equity` (no spread deduction) + `used_margin_usd` check. ✔
- Mode A (min-lot + %/ATR survival skip-filter, cap sweep) → Tasks 5–6. ✔
- Mode B → seeded as backlog row (Task 3), not built. ✔
- Outputs (quantstats + plotly + console verdict) → Task 6. ✔
- DB log of result → Task 7. ✔
- step6_backlog table + code layer + migration + 6 seeds → Tasks 1–3. ✔
- ORB-002 lineage / Gate-0 re-answer note → captured in seed detail (Task 3). ✔

**Placeholder scan:** Task 7 intentionally uses ALLCAPS tokens — these are *runtime values* the engineer fills from the verified sim run (cannot be known at plan-time); every code step that defines behavior shows complete code. No "TBD/handle edge cases" placeholders. ✔

**Type consistency:** `trade_pnl_usd(R, range_w, lot)`, `used_margin_usd(entry_px, lot, leverage)`, `simulate_equity(...) -> {"curve","summary"}`, `daily_returns(curve, start)`, `sweep_caps`, `write_outputs`, `load_oos_trades`, `main` — names consistent across Tasks 4–7. Summary dict keys used in Task 6/7 (`terminal_equity`, `max_drawdown_pct`, `blew_up`, `n_taken`, `risk_cap_pct`) match those defined in Task 5. ✔

**ATR-relative cap note:** the spec mentions a parallel ATR-relative cap; this plan implements the %-of-equity cap and seeds the ATR variant into the backlog ("ORB %/ATR survival filter — productionise"). Flagged so it's a conscious deferral, not a gap.
