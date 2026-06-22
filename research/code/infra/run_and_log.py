"""run_and_log — the one sanctioned way to score a backtest (P1 task 58).

WHY THIS EXISTS
    Model scripts used to end by writing a summary.json + printing a VERDICT, then
    a human hand-called pipeline.log_result() / strategy_log.log_change() afterward.
    That seam is how the ORB saga happened: results existed un-logged or got the
    wrong verdict stamped on them. This harness removes the seam — a scored run
    emits its result AND logs it in one call, so a number can't exist in a handover
    without a result_id behind it (CLAUDE.md rule 11).

DESIGN (locked 2026-06-13, with Syafiq)
    1. FACT-ONLY auto-log.  The harness always writes the *fact* (the metrics) to
       step4_results. The *verdict* (log_change → log_strategy) is opt-in: pass
       verdict= only when a human has looked at WHY the number is what it is.
       verdict=None logs the fact and touches nothing in the lineage. This is the
       ORB lesson in one rule — never let code auto-stamp VALIDATED on a number.
    2. CLEAN-TREE gate.  A gate-scored result whose git_sha+code_path point at
       uncommitted code can't be reproduced, so a dirty tree is refused. Exploratory
       runs pass dirty_ok=True; the stored git_sha is then suffixed "-dirty" so the
       irreproducibility is on the record, not hidden.
    3. COMPENSATING-DELETE atomicity.  log_result and log_change commit to two
       different tables on two connections. If the verdict write fails after the
       result landed, the harness deletes the orphan result (pipeline.delete_result)
       and re-raises — so "result demanded a verdict but didn't get one" never
       persists. Chosen over a shared transaction to keep the two load-bearing
       core writers (rule 10) single-path.
    4. PER-IDEA CONTRACT.  Each idea family declares the metrics a result MUST carry
       (ORB → E_R + t_stat, HMM → AUC) and which one the verdict attaches to. A run
       missing a required metric is rejected before anything is written — the teeth
       that stop half-logged results.

THE RUNNER CONTRACT
    run_and_log(idea_id, runner, ...) calls runner() inside the guard. runner must
    return a normalized dict (a "RunResult"):
        {
          "stage": "OOS",            # IS | walkforward | montecarlo | OOS
          "period": "per_trade",     # per_trade | daily | annualised
          "cost_adjusted": 1,        # 0 raw | 1 net  — applies to every metric row
          "n_obs": 526,
          "data_start": "2024-05-02",
          "data_end":   "2026-06-01",
          "metrics": {"E_R": -0.0857, "t_stat": -1.67},   # the numbers
          "parameters": "{...}",     # optional — frozen knobs, json string
          "notes": "fork_a_ea_emulation full OOS",  # optional
        }
    Each entry in `metrics` becomes one step4_results row sharing the run-level
    stage/period/cost_adjusted/span. The harness fills git_sha + code_path itself.

USAGE (library — the main path; model scripts wrap their own run)
    from run_and_log import run_and_log
    out = run_and_log(
        "ORB-001", runner, gate_number=7,
        verdict="FALSIFIED", component="config", to_value="look-ahead",
        rationale="EA-faithful fills: E_R<0, t<2 across full OOS",
    )
    # out -> {"result_ids":[...], "primary_result_id":N, "log_id":M|None}

USAGE (CLI — introspection only; writing happens through the library)
    python research/code/run_and_log.py contracts     # list registered contracts
"""
from __future__ import annotations

import argparse
import inspect
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root for run-as-script
from research.code.gates import pipeline
from research.code.lineage import strategy_log

REPO = Path(__file__).resolve().parents[3]


# ── per-idea contracts ──────────────────────────────────────────────────────────
# required: metric keys a result of this family MUST carry (completeness guard).
# primary:  the metric the verdict (log_change.result_id) attaches to.
CONTRACTS: dict[str, dict] = {
    "ORB": {"required": ("E_R", "t_stat"), "primary": "E_R"},
    "HMM": {"required": ("AUC",),          "primary": "AUC"},
}


def _contract(idea_id: str) -> dict:
    family = idea_id.split("-")[0].upper()
    if family not in CONTRACTS:
        raise ValueError(
            f"no contract for family {family!r} (idea {idea_id!r}); "
            f"register one in CONTRACTS — known: {sorted(CONTRACTS)}")
    return CONTRACTS[family]


# ── provenance helpers ──────────────────────────────────────────────────────────
def _git_sha() -> str:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    if not sha:
        raise RuntimeError("could not read git HEAD sha")
    return sha


def _git_dirty() -> bool:
    out = subprocess.run(["git", "status", "--porcelain"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    return bool(out)


def _rel(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path)


def _runner_path(runner) -> str:
    try:
        return _rel(inspect.getsourcefile(runner) or inspect.getfile(runner))
    except (TypeError, OSError):
        return "<unknown>"


def _validate_runresult(rr, required: tuple[str, ...]) -> None:
    if not isinstance(rr, dict):
        raise TypeError(f"runner must return a dict RunResult, got {type(rr).__name__}")
    for k in ("stage", "period", "cost_adjusted", "n_obs",
              "data_start", "data_end", "metrics"):
        if k not in rr:
            raise ValueError(f"RunResult missing required key {k!r}")
    metrics = rr["metrics"]
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("RunResult['metrics'] must be a non-empty dict")
    missing = [k for k in required if k not in metrics]
    if missing:
        raise ValueError(
            f"contract violation — metrics {missing} required but absent "
            f"(got {sorted(metrics)})")


# ── the harness ─────────────────────────────────────────────────────────────────
def run_and_log(
    idea_id: str,
    runner,
    *,
    gate_number: int,
    verdict: str | None = None,
    rationale: str = "",
    event: str | None = None,
    component: str | None = None,
    from_value: str | None = None,
    to_value: str | None = None,
    n_trials: int | None = None,
    trial_family_id: str | None = None,
    instrument: str = "XAUUSD",
    seed: int | None = None,
    decided_by: str = "human",
    dirty_ok: bool = False,
) -> dict:
    """Run a scored backtest and log it atomically. Returns
    {"result_ids", "primary_result_id", "log_id"}. See module docstring."""
    contract = _contract(idea_id)

    # (2) clean-tree gate — before we run anything expensive.
    dirty = _git_dirty()
    if dirty and not dirty_ok:
        raise SystemExit(
            "run_and_log: working tree is dirty — a gate-scored result must point at "
            "committed code to reproduce. Commit first, or pass dirty_ok=True for an "
            "exploratory run (git_sha will be marked '-dirty').")
    sha = _git_sha() + ("-dirty" if dirty else "")
    code_path = _runner_path(runner)

    # run the sim inside the guard, then check it satisfies the contract.
    rr = runner()
    _validate_runresult(rr, contract["required"])

    # (1)+(4) log the fact: one step4_results row per metric, primary first.
    primary = contract["primary"]
    keys = [primary] + [k for k in rr["metrics"] if k != primary]
    result_ids: list[int] = []
    try:
        for k in keys:
            rid = pipeline.log_result(
                idea_id=idea_id, gate_number=gate_number,
                stage=rr["stage"], metric_key=k, metric_value=rr["metrics"][k],
                cost_adjusted=rr["cost_adjusted"], period=rr["period"],
                n_obs=rr["n_obs"], data_start=rr["data_start"], data_end=rr["data_end"],
                git_sha=sha, code_path=code_path,
                n_trials=n_trials, trial_family_id=trial_family_id,
                instrument=instrument, parameters=rr.get("parameters"),
                seed=seed, notes=rr.get("notes"),
            )
            result_ids.append(rid)
        primary_rid = result_ids[0]

        # (1) verdict is opt-in and explicit — never auto-derived.
        log_id = None
        if verdict is not None:
            log_id = strategy_log.log_change(
                idea_id=idea_id, event=(event or verdict.lower()), verdict=verdict,
                component=component, from_value=from_value, to_value=to_value,
                rationale=rationale, result_id=primary_rid, git_sha=sha,
                decided_by=decided_by,
            )
    except Exception:
        # (3) compensating delete — never leave a result that demanded a verdict
        #     without one (or a partial set of metric rows).
        for rid in result_ids:
            try:
                pipeline.delete_result(rid)
            except Exception as ce:                       # noqa: BLE001
                print(f"[run_and_log] WARN: compensation failed for {rid}: {ce}")
        raise

    print(f"[run_and_log] {idea_id} gate={gate_number} logged "
          f"{len(result_ids)} metric(s) result_ids={result_ids}"
          + (f" verdict={verdict} log_id={log_id}" if verdict else " (fact-only)"))
    return {"result_ids": result_ids, "primary_result_id": primary_rid, "log_id": log_id}


# ── CLI (introspection only) ─────────────────────────────────────────────────────
def cmd_contracts() -> int:
    print("registered per-idea contracts (family -> required metrics | primary):")
    for fam, c in sorted(CONTRACTS.items()):
        req = ", ".join(c["required"])
        print(f"  {fam:<5} required=[{req}]  primary={c['primary']}")
    print("\nwriting happens through the library: from run_and_log import run_and_log")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("contracts", help="list registered per-idea contracts")
    args = ap.parse_args()
    return {"contracts": cmd_contracts}[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())
