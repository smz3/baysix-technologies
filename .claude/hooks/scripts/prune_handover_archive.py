"""Prune memory/_handover_archive/ — keep only the most recent N days of
archived handovers, delete the rest.

Companion to archive_handovers.py (the SessionStart sweep that *moves* old
handovers into the archive). This script *trims* that archive so it doesn't grow
without bound. "N days" is a calendar span anchored to the newest handover date
actually present in the archive (self-contained: the result is the same no matter
when you run it). Default span = 1 day.

Date comes from the filename (Session_Handover_YYYY_MM_DD_<slot>.md), never mtime
— git checkouts rewrite mtimes. Files that don't parse are left untouched.

Usage:
    python prune_handover_archive.py            # dry-run (default) — prints what WOULD go
    python prune_handover_archive.py --apply     # actually delete
    python prune_handover_archive.py --days 3    # keep newest 3 calendar days
    python prune_handover_archive.py --days 3 --apply

Deletes via `git rm` for tracked files (history is preserved — recoverable);
plain unlink for untracked. Never touches the live handover in memory/.
"""
import argparse
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ARCHIVE = REPO / "memory" / "_handover_archive"

# Session_Handover_YYYY_MM_DD_<slot>.md
_PAT = re.compile(r"^Session_Handover_(\d{4})_(\d{2})_(\d{2})_(.+)\.md$")


def _file_date(name):
    """-> date parsed from the filename, or None if it doesn't parse."""
    m = _PAT.match(name)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _delete(path):
    """git rm a tracked file (keeps history); fall back to unlink."""
    try:
        r = subprocess.run(
            ["git", "rm", "-q", "--", str(path)],
            cwd=str(REPO), capture_output=True, text=True)
        if r.returncode == 0:
            return
    except Exception:
        pass
    path.unlink(missing_ok=True)  # untracked file or git unavailable


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=1,
                    help="calendar days to keep, anchored to newest archived "
                         "handover (default 1 = keep only the newest day)")
    ap.add_argument("--apply", action="store_true",
                    help="actually delete (default is a dry-run preview)")
    args = ap.parse_args()

    if args.days < 1:
        print("--days must be >= 1", file=sys.stderr)
        return 2
    if not ARCHIVE.exists():
        print(f"(no archive at {ARCHIVE} — nothing to prune)")
        return 0

    dated = [(d, f) for f in ARCHIVE.glob("Session_Handover_*.md")
             if (d := _file_date(f.name)) is not None]
    if not dated:
        print("(no parseable handovers in archive — nothing to prune)")
        return 0

    newest = max(d for d, _ in dated)
    cutoff = newest - timedelta(days=args.days - 1)  # keep date >= cutoff
    to_delete = sorted((f for d, f in dated if d < cutoff), key=lambda f: f.name)
    kept = len(dated) - len(to_delete)

    print(f"archive: {len(dated)} handovers | newest day {newest} | "
          f"keeping {args.days} day(s) -> cutoff {cutoff} (keep >= cutoff)")
    if not to_delete:
        print(f"nothing to prune — all {kept} within window.")
        return 0

    verb = "DELETING" if args.apply else "would delete"
    print(f"{verb} {len(to_delete)} handover(s) older than {cutoff} "
          f"({kept} kept):")
    for f in to_delete:
        print(f"  - {f.name}")
        if args.apply:
            _delete(f)

    if not args.apply:
        print("\n(dry-run — re-run with --apply to delete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
