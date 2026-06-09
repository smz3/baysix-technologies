"""SessionStart briefing — prints the live research backlog + recent results so every
new agent sees what's open and what's already been tested, without relying on memory.
Wired into the SessionStart hook (.claude/settings.json). Read-only on research.db."""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DB = REPO / "research" / "db" / "research.db"
MEM = REPO / "memory"


def _latest_handover():
    files = sorted(MEM.glob("Session_Handover_*.md"))
    return files[-1].name if files else "(none yet)"


def main():
    print("=== BAYSIX SESSION START ===\n")
    print(f"Latest handover: memory/{_latest_handover()}   <- read this FIRST\n")

    if not DB.exists():
        print(f"(research.db not found at {DB})")
        return
    c = sqlite3.connect(str(DB))
    cur = c.cursor()

    print("--- OPEN BACKLOG (research.db -> open_backlog) ---")
    rows = cur.execute(
        "SELECT task_id, priority, kind, title FROM open_backlog "
        "ORDER BY priority, task_id").fetchall()
    if not rows:
        print("  (none open)")
    last_p = None
    for tid, prio, kind, title in rows:
        if prio != last_p:
            print(f" {prio}:")
            last_p = prio
        print(f"   {tid:>2} {kind:8s} {title}")

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

    print("\nBefore proposing work: check open_backlog (P1 first) + log_agent "
          "for the active idea (CLAUDE.md rule 16). Never re-surface resolved tasks.")
    c.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block a session on the brief
        print(f"(session_brief failed: {e})", file=sys.stderr)
