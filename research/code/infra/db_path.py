"""db_path — the ONE place the baysix.db location is decided (task 357).

THE BUG THIS FIXES (MEASURED 2026-08-16): every module built the path as
`Path(__file__).parents[2] / "db" / "research.db"`, i.e. relative to its own
file. A git worktree therefore resolved to the WORKTREE's own folder and got a
brand-new empty database. Syafiq's parallel-tab setup (MT5 / NinjaTrader /
admin, one worktree each) would have given three sessions three empty task
lists and three separate trial counts — which is the one number that has to be
shared for the research to stay honest.

Moving the file to db/baysix.db does NOT fix that on its own; a worktree has
its own root too. Only an ABSOLUTE path from the environment does.

RESOLUTION ORDER
  1. $BAYSIX_DB                       — set in .claude/settings.json `env`, an
                                        absolute path to the MAIN checkout, so
                                        every worktree resolves to the same file.
  2. BAYSIX_DB= in the repo-root .env — for plain shells that never load
                                        Claude Code's settings.
  3. <this repo>/db/baysix.db         — last resort. Correct in the main
                                        checkout, WRONG in a worktree, so it
                                        warns rather than failing silently.

Use `DB_PATH` for the module-level constant, or `db_path()` when a test needs
to re-read the environment after changing it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT = REPO / "db" / "baysix.db"
ENV_VAR = "BAYSIX_DB"


def _from_dotenv() -> str | None:
    """BAYSIX_DB out of the repo-root .env, without a dotenv dependency.

    Deliberately a 6-line parser: .env also holds API keys, and pulling in a
    loader that exports the whole file into os.environ would put those keys in
    the environment of every research script (CLAUDE.md rule 3).
    """
    f = REPO / ".env"
    if not f.exists():
        return None
    try:
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{ENV_VAR}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def db_path(warn: bool = True) -> Path:
    """Resolve the baysix.db path. See module docstring for the order."""
    raw = os.environ.get(ENV_VAR) or _from_dotenv()
    if raw:
        return Path(raw).expanduser()
    if warn and ".claude" in str(REPO).replace("\\", "/"):
        # a worktree lives under .claude/worktrees/ — the exact case the env
        # var exists to fix, so say so loudly instead of opening a blank DB
        print(
            f"[db_path] WARNING: {ENV_VAR} is unset and this looks like a git "
            f"worktree ({REPO}). Falling back to {DEFAULT}, which is a DIFFERENT "
            f"database from the main checkout. Set {ENV_VAR} before writing.",
            file=sys.stderr,
        )
    return DEFAULT


DB_PATH = db_path()
