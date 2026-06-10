"""
Smoke test for execution.py / execution.db — runs against a TEMP DB (never touches
research/db/execution.db). Points EXECUTION_DB_PATH at a tempfile before importing
execution, exercises the REGISTER → GATE path, and asserts the core guardrail:
pass_deploy_gate() MUST refuse until recon_results exist.

Run: python research/code/smoke_execution.py
Exit 0 = all assertions passed.
"""
import os
import sys
import tempfile
from pathlib import Path

# 1) isolate: temp DB BEFORE importing execution (DB path is read at call time, but
#    set it up front so nothing can touch the real file).
_tmp = Path(tempfile.mkdtemp(prefix="exec_smoke_")) / "execution_test.db"
os.environ["EXECUTION_DB_PATH"] = str(_tmp)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import execution

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
_failures = []


def check(label, cond):
    print(f"  [{PASS if cond else FAIL}] {label}")
    if not cond:
        _failures.append(label)


def main():
    print(f"=== execution.db smoke test (temp: {_tmp}) ===\n")

    # --- build schema ---
    execution.init_db()
    import sqlite3
    conn = sqlite3.connect(_tmp)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()}
    conn.close()
    expected = {"accounts", "deploy_strategies", "deploy_gates", "exec_signals",
                "exec_orders", "exec_fills", "exec_trades", "recon_results",
                "log_deploy", "log_incidents"}
    print("\n[schema]")
    check(f"all 10 tables created ({len(tables & expected)}/10)", expected <= tables)

    # --- REGISTER ---
    print("\n[register]")
    execution.register_account(
        "jm-live-01", venue="justmarkets", account_type="retail_highlev",
        mode="live", broker_login="12345678", initial_balance=50.0, leverage=500,
    )
    check("account jm-live-01 registered", bool(execution.get_account_rules("jm-live-01")))

    deploy_id = execution.register_deployment("ORB-001", "jm-live-01")
    dep = execution.get_deploy_config(deploy_id)
    check("deploy_id == 'ORB-001@jm-live-01'", deploy_id == "ORB-001@jm-live-01")
    check("magic_number == 1001 (readable map)", dep.get("magic_number") == 1001)
    check("stage defaults to D0", dep.get("stage") == "D0")
    check("status defaults to pending", dep.get("status") == "pending")
    check("config_snapshot captured from research.db", bool(dep.get("config_snapshot")))

    # --- soft-key validation should reject an unknown idea ---
    print("\n[soft-key validation]")
    try:
        execution.register_deployment("NOPE-999", "jm-live-01")
        check("unknown idea_id rejected", False)
    except ValueError:
        check("unknown idea_id rejected", True)

    # --- GATE + the guardrail (the headline assertion) ---
    print("\n[gate guardrail]")
    execution.open_deploy_gate(deploy_id, 0, pass_criteria="trade-list diff == 0; feed div < tol")
    try:
        execution.pass_deploy_gate(deploy_id, 0, gate_answer="looks fine")
        check("pass_deploy_gate BLOCKED with no recon_results", False)  # should not reach
    except ValueError as e:
        check("pass_deploy_gate BLOCKED with no recon_results", "no recon_results" in str(e))

    # log a recon result, then the same pass should succeed
    execution.log_recon_result(deploy_id, metric_key="trade_diff", metric_value=0.0,
                               n_obs=120, gate_number=0)
    try:
        execution.pass_deploy_gate(deploy_id, 0, gate_answer="trade diff 0, feed div 0.3px < 0.5px tol")
        check("pass_deploy_gate SUCCEEDS once recon exists", True)
    except ValueError:
        check("pass_deploy_gate SUCCEEDS once recon exists", False)

    gate = sqlite3.connect(_tmp).execute(
        "SELECT status FROM deploy_gates WHERE deploy_id=? AND gate_number=0", (deploy_id,)
    ).fetchone()
    check("D0 status == passed", gate and gate[0] == "passed")

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
        check("malformed meta rejected (extra/missing fields)", False)
    except Exception:
        check("malformed meta rejected (extra/missing fields)", True)

    # --- UNIQUE(account_id, magic_number) collision guard ---
    print("\n[constraints]")
    try:
        execution.register_deployment("ORB-001", "jm-live-01")  # same deploy_id + magic
        check("duplicate deployment rejected (PK/UNIQUE)", False)
    except sqlite3.IntegrityError:
        check("duplicate deployment rejected (PK/UNIQUE)", True)

    # --- verdict ---
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
