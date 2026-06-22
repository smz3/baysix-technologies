"""Launch a long-running command in a NEW PowerShell window (live output for Syafiq,
per CLAUDE.md rule 12) AND drop a completion SENTINEL so the agent can wait reliably.

WHY THIS EXISTS (2026-06-09): the old ad-hoc waiter polled for the output file's
mtime being "within 5s of now". The output is written once and never touched again,
so with a 10s poll the freshness window could never be caught -> the waiter hung to
its timeout and never notified. Never gate completion on a freshness window. Gate on
a sentinel's EXISTENCE, created fresh per run.

USAGE (agent):
    python research/code/run_tracked.py <name> -- <command...>
e.g.
    python research/code/run_tracked.py reentry -- python -X utf8 research/models/orb/reentry.py

Then wait on the sentinel (existence only):
    until [ -f research/outputs/_runs/<name>.done ]; do sleep 10; done

Pass a SCRIPT PATH (python -X utf8 path/to/script.py), not an inline `python -c "..."`
with shell metacharacters — quotes/semicolons get mangled joining argv back together.

The sentinel file contains the wrapped command's exit code (0 = success). A new
PowerShell window shows live output and stays open (-NoExit). Uses the inline
-Command launch pattern (no -File, no ExecutionPolicy override); single quotes in
the inner command are doubled for safe embedding."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUNS = REPO / "research" / "outputs" / "_runs"


def main() -> None:
    argv = sys.argv[1:]
    if "--" not in argv or argv.index("--") == 0:
        sys.exit("usage: run_tracked.py <name> -- <command...>")
    sep = argv.index("--")
    name = argv[0]
    command = argv[sep + 1:]
    if not command:
        sys.exit("no command after --")

    RUNS.mkdir(parents=True, exist_ok=True)
    sentinel = RUNS / f"{name}.done"
    if sentinel.exists():
        sentinel.unlink()                      # clear stale sentinel from a prior run

    # Inner PowerShell: cd repo, run command, then ALWAYS write the exit code to the
    # sentinel (try/finally) so the waiter is never left hanging on a crash.
    cmd = " ".join(command)
    inner = (f"Set-Location '{REPO}'; "
             f"try {{ {cmd}; $ec=$LASTEXITCODE; if($null -eq $ec){{$ec=0}} }} "
             f"catch {{ $ec=1 }} "
             f"finally {{ Set-Content -Path '{sentinel}' -Value $ec; "
             f"Write-Host \"`n[run_tracked] '{name}' done, exit=$ec\" }}")
    inner_escaped = inner.replace("'", "''")    # double single-quotes for embedding
    ps_command = (f"Start-Process powershell -ArgumentList "
                  f"'-NoExit','-Command','{inner_escaped}'")
    subprocess.run(["powershell.exe", "-Command", ps_command], check=True)
    print(f"[run_tracked] launched '{name}' in new window")
    print(f"[run_tracked] wait on:  {sentinel}")
    print(f"[run_tracked] agent:    until [ -f research/outputs/_runs/{name}.done ]; do sleep 10; done")


if __name__ == "__main__":
    main()
