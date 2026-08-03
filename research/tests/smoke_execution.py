"""
Smoke test for execution.py / execution.db — runs against a TEMP DB (never touches
research/db/execution.db). Points EXECUTION_DB_PATH at a tempfile before importing
execution, then monkeypatches the three research.db-facing calls (get_idea,
tester.gate4_passed, strategy_log.get_live_config) so the test is fully isolated and
can drive both the blocked and happy paths deterministically.

Asserts the headline guardrails of the re-locked 12-table schema:
  - register_deployment REFUSES until research G4 (Live/FIDELITY) is passed
  - open FORWARD REFUSES until G4 passed
  - pass FORWARD REFUSES until d5_recon_results exist
  - FORWARD/live REFUSES until FORWARD/demo passed

Run: python research/tests/smoke_execution.py    (exit 0 = all assertions passed)
"""
import os
import sys
import sqlite3
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="exec_smoke_")) / "execution_test.db"
os.environ["EXECUTION_DB_PATH"] = str(_tmp)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import execution

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
_failures = []

# ── isolate the research.db reads (keep the smoke test self-contained) ──────────
_STATE = {"gate4": False}
execution.pipeline.get_idea = lambda idea_id: {"idea_id": idea_id} if idea_id.startswith("ORB-") else {}
execution.tester.gate4_passed = lambda idea_id: _STATE["gate4"]
execution.strategy_log.get_live_config = lambda idea_id: {"anchor": {"log_id": 99, "value": "09:00 UTC"}}


def check(label, cond):
    print(f"  [{PASS if cond else FAIL}] {label}")
    if not cond:
        _failures.append(label)


def main():
    print(f"=== execution.db smoke test (temp: {_tmp}) ===\n")

    execution.init_db()
    conn = sqlite3.connect(_tmp)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()}
    conn.close()
    expected = {"d1_accounts", "d1_instruments", "d1_deployments", "d2_deploy_gates",
                "d3_signals", "d3_orders", "d3_fills", "d3_trades",
                "d4_equity_snapshots", "d5_recon_results", "log_deploy", "log_incidents"}
    print("[schema]")
    check(f"all 12 tables created ({len(tables & expected)}/12)", expected <= tables)

    # --- REGISTER account + instrument ---
    print("\n[register]")
    execution.register_account(
        "jm-demo-01", venue="mt5", broker="justmarkets",
        account_type="retail_highlev", mode="demo",
        broker_login="12345678", initial_balance=10000.0, leverage=500,
    )
    check("account jm-demo-01 registered", bool(execution.get_account_rules("jm-demo-01")))
    check("account venue == 'mt5' (protocol)", execution.get_account_rules("jm-demo-01")["venue"] == "mt5")
    check("account broker == 'justmarkets'", execution.get_account_rules("jm-demo-01")["broker"] == "justmarkets")

    execution.register_instrument(
        "XAUUSD.s", instrument_type="spot", tick_size=0.01, contract_size=100.0,
        display_name="Gold spot", base_asset="XAU", tick_value=1.0, min_lot=0.01, lot_step=0.01,
    )
    check("instrument XAUUSD.s registered", bool(execution.get_instrument("XAUUSD.s")))

    # --- G4 guardrail: deployment REFUSED until FIDELITY passed (headline) ---
    print("\n[G4 guardrail]")
    _STATE["gate4"] = False
    try:
        execution.register_deployment("ORB-001", "jm-demo-01", "XAUUSD.s")
        check("register_deployment BLOCKED until G4 passed", False)
    except ValueError as e:
        check("register_deployment BLOCKED until G4 passed", "G4" in str(e))

    # flip G4 -> passed, now it should succeed
    _STATE["gate4"] = True
    deploy_id = execution.register_deployment("ORB-001", "jm-demo-01", "XAUUSD.s")
    dep = execution.get_deploy_config(deploy_id)
    check("deploy_id == 'ORB-001@jm-demo-01'", deploy_id == "ORB-001@jm-demo-01")
    check("magic_number == 1001 (readable map)", dep.get("magic_number") == 1001)
    check("stage defaults to FORWARD", dep.get("stage") == "FORWARD")
    check("status defaults to pending", dep.get("status") == "pending")
    check("config_snapshot captured", bool(dep.get("config_snapshot")))

    # --- soft-key validation rejects unknown idea + unregistered instrument ---
    print("\n[validation]")
    try:
        execution.register_deployment("NOPE-999", "jm-demo-01", "XAUUSD.s")
        check("unknown idea_id rejected", False)
    except ValueError:
        check("unknown idea_id rejected", True)
    try:
        execution.register_deployment("ORB-002", "jm-demo-01", "NOPE.x")
        check("unregistered instrument rejected", False)
    except ValueError as e:
        check("unregistered instrument rejected", "instrument" in str(e))

    # --- FORWARD gate + guardrails ---
    print("\n[FORWARD gate]")
    gate_id = execution.open_deploy_gate(deploy_id, pass_criteria="slip<median tol; live E[R] in IS CI", sub_stage="demo")
    check("FORWARD/demo gate opened", isinstance(gate_id, int))

    try:
        execution.pass_deploy_gate(deploy_id, gate_answer="looks fine", sub_stage="demo")
        check("pass FORWARD/demo BLOCKED with no recon", False)
    except ValueError as e:
        check("pass FORWARD/demo BLOCKED with no recon", "no d5_recon_results" in str(e))

    execution.log_recon_result(deploy_id, metric_key="slippage_median_px", metric_value=0.4,
                               n_obs=40, gate_id=gate_id)
    execution.pass_deploy_gate(deploy_id, gate_answer="slip 0.4px ok; E[R] in CI", sub_stage="demo")
    demo_status = sqlite3.connect(_tmp).execute(
        "SELECT status FROM d2_deploy_gates WHERE gate_id=?", (gate_id,)
    ).fetchone()
    check("FORWARD/demo status == passed", demo_status and demo_status[0] == "passed")

    # --- live sub_stage needs demo passed (we just passed demo, so a fresh deploy tests the block) ---
    print("\n[demo-before-live]")
    _STATE["gate4"] = True
    execution.register_account("jm-demo-02", venue="mt5", broker="justmarkets",
                               account_type="retail_highlev", mode="demo")
    d2 = execution.register_deployment("ORB-002", "jm-demo-02", "XAUUSD.s")
    execution.open_deploy_gate(d2, pass_criteria="x", sub_stage="live")
    execution.log_recon_result(d2, metric_key="x", metric_value=1.0, n_obs=1)
    try:
        execution.pass_deploy_gate(d2, gate_answer="skip demo", sub_stage="live")
        check("FORWARD/live BLOCKED until demo passed", False)
    except ValueError as e:
        check("FORWARD/live BLOCKED until demo passed", "demo" in str(e))

    # --- meta Pydantic validation on a signal ---
    print("\n[meta validation]")
    sig = execution.log_signal(
        deploy_id, direction="long", signal_ts="2026-06-11 09:00:00",
        session_date="2026-06-11", intended_entry_px=2350.0, intended_stop_px=2345.0,
        expected_R=2.0, meta={"or_high": 2350.0, "or_low": 2345.0, "range_w": 5.0, "anchor": "09:00 UTC"},
    )
    check("valid ORB meta accepted", isinstance(sig, int))
    try:
        execution.log_signal(deploy_id, direction="long", signal_ts="2026-06-11 09:00:00",
                             session_date="2026-06-11", meta={"bogus_field": 1})
        check("malformed meta rejected", False)
    except Exception:
        check("malformed meta rejected", True)

    # --- equity snapshot (STATE layer) ---
    print("\n[state]")
    snap = execution.log_equity_snapshot("jm-demo-01", snapshot_ts="2026-06-11 09:05:00",
                                         equity=10050.0, balance=10000.0, open_pnl=50.0)
    check("equity snapshot logged", isinstance(snap, int))

    # --- log_incident needs a scope ---
    print("\n[incidents]")
    try:
        execution.log_incident(severity="warn", kind="heartbeat_gap", detail="no scope")
        check("log_incident requires deploy_id or account_id", False)
    except ValueError:
        check("log_incident requires deploy_id or account_id", True)
    inc = execution.log_incident(severity="warn", kind="prop_rule_breach",
                                 detail="daily loss near limit", account_id="jm-demo-01")
    check("account-level incident logged", isinstance(inc, int))

    # --- UNIQUE(account_id, magic_number) collision guard ---
    print("\n[constraints]")
    try:
        execution.register_deployment("ORB-001", "jm-demo-01", "XAUUSD.s")  # same deploy_id + magic
        check("duplicate deployment rejected (PK/UNIQUE)", False)
    except sqlite3.IntegrityError:
        check("duplicate deployment rejected (PK/UNIQUE)", True)

    print()
    if _failures:
        print(f"=== SMOKE FAILED: {len(_failures)} assertion(s) ===")
        for f in _failures:
            print(f"   - {f}")
        sys.exit(1)
    print("=== SMOKE PASSED — execution.db build verified ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
