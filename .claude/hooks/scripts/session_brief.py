"""SessionStart briefing — prints the live research backlog + recent results so every
new agent sees what's open and what's already been tested, without relying on memory.
Wired into the SessionStart hook (.claude/settings.json). Read-only on baysix.db."""
import os
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DB = Path(os.environ.get("BAYSIX_DB") or (REPO / "db" / "baysix.db"))
MEM = REPO / "memory"


def _todays_handovers():
    """All of the current day's handovers, oldest -> newest.

    Parallel Claude tabs each write their own handover, so one day's context is
    split across several files; the day is the unit of read, not the last file.
    Ordering reuses archive_handovers._sort_key (slot-aware: Morning2 after
    Morning, Afternoon after Morning) — lexicographic sorting gets it wrong.
    """
    files = list(MEM.glob("Session_Handover_*.md"))
    if not files:
        return []
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from archive_handovers import _sort_key
        keyed = [(k, f) for f in files if (k := _sort_key(f)) is not None]
        if keyed:
            day = max(k[0] for k, _ in keyed)  # newest date present
            return [f.name for k, f in sorted(keyed) if k[0] == day]
    except Exception:
        pass
    return [f.name for f in sorted(files)]  # fallback: never block the brief


def main():
    print("=== BAYSIX SESSION START ===\n")
    hos = _todays_handovers()
    if not hos:
        print("Handovers: (none yet)\n")
    else:
        print(f"TODAY'S HANDOVERS ({len(hos)}) <- read ALL of these, in this "
              f"order, BEFORE anything else:")
        for i, name in enumerate(hos, 1):
            tail = "   <- most recent" if i == len(hos) else ""
            print(f"  {i}. memory/{name}{tail}")
        print("  (other tabs wrote these today; the last one is not the whole "
              "picture)\n")

    if not DB.exists():
        print(f"(research.db not found at {DB})")
        return
    c = sqlite3.connect(str(DB))
    cur = c.cursor()

    print("--- OPEN BACKLOG (baysix.db -> open_backlog) ---")
    # stream = which system owns the task (task 358). Shown so a session can scope
    # itself to one system on sight — CLAUDE.md rule 5.
    rows = cur.execute(
        "SELECT task_id, priority, stream, kind, title FROM open_backlog "
        "ORDER BY priority, task_id").fetchall()
    if not rows:
        print("  (none open)")
    last_p = None
    for tid, prio, stream, kind, title in rows:
        if prio != last_p:
            print(f" {prio}:")
            last_p = prio
        print(f"   {tid:>2} {stream:<11s} {kind:8s} {title}")

    print("\n--- RECENTLY RESOLVED (last 6) ---")
    done = cur.execute(
        "SELECT task_id, title FROM log_tasks WHERE status='done' "
        "ORDER BY resolved_at DESC LIMIT 6").fetchall()
    for tid, title in done:
        print(f"   {tid:>2} done  {title}")

    print("\n--- LATEST RESULTS (step4_results, last 5) ---")
    res = cur.execute(
        "SELECT idea_id, stage, metric_key, round(metric_value,4) "
        "FROM step4_results ORDER BY result_id DESC LIMIT 5").fetchall()
    for idea, stage, key, val in res:
        print(f"   {idea} {stage:4s} {key} = {val}")

    print("\n--- DB WRITE CONTRACT (core/ ONLY — never raw sqlite3) ---")
    print("  gate open/pass/block/kill -> pipeline.open_gate/pass_gate/block_gate/kill_idea")
    print("  metric result             -> pipeline.log_result()  (n_obs+git_sha required)")
    print("  strategy lineage event    -> strategy_log.log_change(component/from/to/verdict)")
    print("  QR find / dissect         -> agent_log.log_agent_call / log_dissect_result")
    print("  human arch/method call    -> agent_log.log_human_decision")
    print("  backlog task              -> backlog.add_task / resolve_task")
    print("  GATING: Protocol 4.0 = 4 gates (G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live).")
    print("          t-stat is REPORTED, never an auto-kill; OOS/WF persistence is the luck-test.")
    print("  KILL:   needs >=2 FALSIFIED hypotheses (rule 8b) — kill_idea blocks otherwise.")
    print("  DRIVER: python core/gates/idea_cli.py next <idea_id> -> the ONE next legal")
    print("          protocol action, computed from DB. Use it instead of recalling gates.")

    print("\nBefore proposing work: check open_backlog (P1 first) + log_agent "
          "for the active idea (CLAUDE.md rule 6). Never re-surface resolved tasks.")
    c.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block a session on the brief
        print(f"(session_brief failed: {e})", file=sys.stderr)
