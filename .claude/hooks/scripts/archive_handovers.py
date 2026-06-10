"""SessionStart handover sweep — keeps ONLY the single latest handover in
memory/ and moves every other one into memory/_handover_archive/.

Rule (revised 2026-06-10): each day produces several handovers
(Morning/Afternoon/Afternoon2/Evening/...). Keep just the most recent one for
easy tracking; archive the rest — including older same-day slots. "Most recent"
is ranked by (date, slot-of-day, slot-number, mtime): a robust slot order
(Morning < Noon < Afternoon < Evening < Night, with trailing digit as a minor
key), with file mtime as the final tiebreaker for unknown slot names. Wired into
the SessionStart hook (.claude/settings.json). Quiet on no-op; never blocks a
session."""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MEM = REPO / "memory"
ARCHIVE = MEM / "_handover_archive"

# Session_Handover_YYYY_MM_DD_<slot>.md
_PAT = re.compile(r"^Session_Handover_(\d{4})_(\d{2})_(\d{2})_(.+)\.md$")

# Chronological order of named slots within a day.
_SLOT_ORDER = {
    "morning": 1, "noon": 2, "midday": 2, "afternoon": 3,
    "evening": 4, "night": 5,
}


def _parsed(name):
    """-> (date, slot_rank, slot_num) or None if the name doesn't parse."""
    m = _PAT.match(name)
    if not m:
        return None
    try:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    slot = m.group(4)
    sm = re.match(r"^([A-Za-z]+?)(\d*)$", slot)
    base = sm.group(1).lower() if sm else slot.lower()
    num = int(sm.group(2)) if sm and sm.group(2) else 1
    rank = _SLOT_ORDER.get(base, 99)  # unknown slot -> ranks high; mtime breaks
    return (d, rank, num)


def _sort_key(f):
    """Total order over handovers; the max is the one we keep."""
    p = _parsed(f.name)
    if p is None:
        return None
    try:
        mtime = f.stat().st_mtime
    except OSError:
        mtime = 0.0
    return (*p, mtime)


def _move(src, dst):
    """git mv (keeps history clean); fall back to plain rename if git can't."""
    try:
        r = subprocess.run(
            ["git", "mv", str(src), str(dst)],
            cwd=str(REPO), capture_output=True, text=True)
        if r.returncode == 0:
            return True
    except Exception:
        pass
    src.rename(dst)  # untracked file or git unavailable
    return True


def main():
    if not MEM.exists():
        return
    ARCHIVE.mkdir(exist_ok=True)

    # Only parseable handovers are sortable; unparseable ones are left in place.
    candidates = [(k, f) for f in MEM.glob("Session_Handover_*.md")
                  if (k := _sort_key(f)) is not None]
    if not candidates:
        return  # nothing parseable -> nothing to sweep

    keeper = max(candidates, key=lambda kf: kf[0])[1]  # the single latest

    moved = []
    for _, f in sorted(candidates, key=lambda kf: kf[0]):
        if f == keeper:
            continue  # the latest handover stays in memory/
        dst = ARCHIVE / f.name
        if dst.exists():
            dst = ARCHIVE / f"{f.stem}_dup{f.suffix}"
        _move(f, dst)
        moved.append(f.name)

    if moved:
        print(f"[handover-sweep] kept {keeper.name}; archived "
              f"{len(moved)} older handover(s): " + ", ".join(moved))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block a session on the sweep
        print(f"(archive_handovers failed: {e})", file=sys.stderr)
