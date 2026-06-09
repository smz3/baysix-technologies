"""SessionStart handover sweep — moves any handover older than today into
memory/_handover_archive/ so memory/ only ever holds the current day's handovers.

Rule (confirmed 2026-06-09): keep every Session_Handover dated *today*; git mv
anything older to the archive. Preserves same-day narrative (Morning/Afternoon/...)
while keeping memory/ from accumulating. Wired into the SessionStart hook
(.claude/settings.json). Quiet on no-op; never blocks a session."""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MEM = REPO / "memory"
ARCHIVE = MEM / "_handover_archive"

# Session_Handover_YYYY_MM_DD_<slot>.md
_PAT = re.compile(r"^Session_Handover_(\d{4})_(\d{2})_(\d{2})_.+\.md$")


def _file_date(name):
    m = _PAT.match(name)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


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
    today = date.today()

    moved = []
    for f in sorted(MEM.glob("Session_Handover_*.md")):
        d = _file_date(f.name)
        if d is None or d >= today:
            continue  # unparseable -> leave in place (safe); today's -> keep
        dst = ARCHIVE / f.name
        if dst.exists():
            dst = ARCHIVE / f"{f.stem}_dup{f.suffix}"
        _move(f, dst)
        moved.append(f.name)

    if moved:
        print(f"[handover-sweep] archived {len(moved)} older handover(s): "
              + ", ".join(moved))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block a session on the sweep
        print(f"(archive_handovers failed: {e})", file=sys.stderr)
