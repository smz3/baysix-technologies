"""SessionStart / SessionEnd hook — routine snapshot of baysix.db (task 350).

Thin wrapper. All the logic lives in core/infra/db_snapshot.py so the same
routine is callable by hand (`python -m core.infra.db_snapshot pre_migration`).

Throttled to one snapshot every MIN_AGE_HOURS, so wiring it to BOTH session events
costs nothing: whichever fires first takes it, and a session that dies without a clean
end still gets covered by the next SessionStart.

Never fails a session. A backup routine that blocks work is a backup routine that gets
switched off, so every error is swallowed to stderr.

Usage: python -X utf8 .claude/hooks/scripts/db_snapshot_hook.py [reason]
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def main() -> int:
    reason = sys.argv[1] if len(sys.argv) > 1 else "session"
    try:
        from core.infra.db_snapshot import snapshot
        snapshot(reason)
    except Exception as e:  # noqa: BLE001 — see module docstring
        print(f"[db_snapshot] skipped: {type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
