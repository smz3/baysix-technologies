#!/usr/bin/env python
"""Baysix agent-safe commit+push — serialised across parallel agent harnesses.

WHY THIS EXISTS
---------------
Several agent harnesses (Claude Code, grokbot, hermes) run against ONE shared
working copy on this PC. The repo's standing rule is "auto commit + push at
natural completion points". Done with the obvious `git add -A`, that rule is a
collision generator:

  * `git add -A` from agent A stages agent B's half-finished edits, so B's
    unfinished work lands in A's commit under A's message.
  * Two agents running `git commit` at the same moment fight over
    `.git/index.lock` and one of them dies mid-write.
  * Two `git push` calls race the same branch; the loser is rejected.

This wrapper removes all three:

  1. EXCLUSIVE LOCK — only one agent may be inside the commit+push critical
     section at a time. Others wait (they do not fail fast); a lock older than
     --stale-secs is treated as abandoned and broken.
  2. EXPLICIT PATHS ONLY — you must name what you are committing. There is no
     "-A" / "--all" / "." escape hatch; passing one is a hard error.
  3. PATHSPEC-LIMITED COMMIT — `git commit -- <paths>` commits exactly those
     paths even if some other agent left unrelated entries sitting in the
     shared index. Their staging is neither committed nor destroyed.

USAGE
-----
    python .claude/hooks/git/agent_commit.py \
        -m "fix(fob): correct CF band width" \
        --agent claude-code \
        research/models/fob/foo.py docs/specs/bar.md

    # commit only, leave the push for later
    ... --no-push

Exit codes: 0 ok · 1 usage/refusal · 2 lock timeout · 3 git command failed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Names that would sweep in files the caller never inspected. Refused outright.
BANNED_PATHSPECS = {"-A", "--all", "-a", ".", "*", ":/", "./"}

LOCK_NAME = "baysix-agent.lock"
TOKEN_ENV = "BAYSIX_GIT_LOCK_TOKEN"


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(out.stdout.strip())


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        sys.stderr.write(f"[agent-commit] git {' '.join(args)} failed:\n{proc.stderr}")
        sys.exit(3)
    return proc


# --------------------------------------------------------------------------
# lock
# --------------------------------------------------------------------------
def acquire(lock_path: Path, agent: str, token: str, timeout: int, stale: int) -> None:
    """Block until we own `lock_path`, or exit(2) after `timeout` seconds.

    The lock is a plain file created with O_EXCL — atomic on Windows and POSIX
    alike, so two agents can never both believe they hold it. Staleness is
    judged by age only (a PID liveness check is not portable enough to trust on
    Windows), which is safe here because the critical section is a few seconds.
    """
    deadline = time.time() + timeout
    announced = False
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as fh:
                json.dump(
                    {"agent": agent, "pid": os.getpid(), "token": token, "ts": time.time()},
                    fh,
                )
            return
        except FileExistsError:
            holder = read_lock(lock_path)
            age = time.time() - holder.get("ts", 0)
            if age > stale:
                sys.stderr.write(
                    f"[agent-commit] breaking stale lock from "
                    f"{holder.get('agent', '?')} (age {age:.0f}s > {stale}s)\n"
                )
                lock_path.unlink(missing_ok=True)
                continue
            if not announced:
                sys.stderr.write(
                    f"[agent-commit] waiting — '{holder.get('agent', '?')}' "
                    f"is committing (held {age:.0f}s)\n"
                )
                announced = True
            if time.time() > deadline:
                sys.stderr.write(
                    f"[agent-commit] TIMEOUT after {timeout}s waiting for "
                    f"{holder.get('agent', '?')}. Nothing was committed.\n"
                )
                sys.exit(2)
            time.sleep(1.0)


def read_lock(lock_path: Path) -> dict:
    try:
        return json.loads(lock_path.read_text())
    except (OSError, ValueError):
        # Unreadable lock = mid-write or corrupt; treat as ancient so it can be broken.
        return {"agent": "unknown", "ts": 0.0}


def release(lock_path: Path, token: str) -> None:
    """Drop the lock, but only if it is still ours (never steal a successor's)."""
    if lock_path.exists() and read_lock(lock_path).get("token") == token:
        lock_path.unlink(missing_ok=True)


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Serialised, path-scoped commit+push.")
    ap.add_argument("-m", "--message", required=True, help="commit message")
    ap.add_argument("--agent", default=os.environ.get("BAYSIX_AGENT", "unknown"),
                    help="which harness is committing (shown to whoever waits)")
    ap.add_argument("--no-push", action="store_true", help="commit only")
    ap.add_argument("--timeout", type=int, default=300, help="seconds to wait for the lock")
    ap.add_argument("--stale-secs", type=int, default=900,
                    help="a lock older than this is considered abandoned")
    ap.add_argument("paths", nargs="+", help="explicit files/dirs to commit")

    def refuse(bad: list[str]) -> None:
        sys.stderr.write(
            f"[agent-commit] REFUSED: {bad} sweeps in other agents' in-flight edits.\n"
            f"                Name the files you actually changed.\n"
        )
        sys.exit(1)

    # Scan raw argv BEFORE parsing: argparse would reject "-A"/"--all" as unknown
    # options and die with a bare usage dump, which reads like a typo rather than
    # a deliberate refusal.
    if raw_bad := [a for a in sys.argv[1:] if a in BANNED_PATHSPECS]:
        refuse(raw_bad)

    args = ap.parse_args()

    if path_bad := [p for p in args.paths if p in BANNED_PATHSPECS]:
        refuse(path_bad)

    root = repo_root()
    lock_path = root / ".git" / LOCK_NAME
    token = f"{os.getpid()}-{time.time_ns()}"

    acquire(lock_path, args.agent, token, args.timeout, args.stale_secs)
    try:
        # The pre-commit hook reads this to tell "lock held by me" from
        # "lock held by a different agent" (which means an interleaved commit).
        os.environ[TOKEN_ENV] = token

        git("add", "--", *args.paths, cwd=root)

        # Pathspec-limited: commits these paths only, even if the shared index
        # holds unrelated entries another agent staged.
        staged = git("diff", "--cached", "--name-only", "--", *args.paths, cwd=root)
        if not staged.stdout.strip():
            print("[agent-commit] nothing to commit for the given paths.")
            return

        print("[agent-commit] committing:\n  " + "\n  ".join(staged.stdout.split()))
        git("commit", "-m", args.message, "--", *args.paths, cwd=root)

        if args.no_push:
            print("[agent-commit] committed (push skipped).")
            return

        branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=root).stdout.strip()
        push = git("push", "origin", branch, cwd=root, check=False)
        if push.returncode != 0:
            sys.stderr.write(
                f"[agent-commit] COMMIT OK, PUSH REJECTED on {branch}:\n{push.stderr}\n"
                f"                The commit is safe locally. Resolve by hand — this\n"
                f"                wrapper will not rebase a working tree that other\n"
                f"                agents are actively editing.\n"
            )
            sys.exit(3)
        print(f"[agent-commit] pushed to origin/{branch}.")
    finally:
        release(lock_path, token)


if __name__ == "__main__":
    main()
