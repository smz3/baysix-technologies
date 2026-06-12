#!/usr/bin/env python
"""
context_watch.py  —  UserPromptSubmit hook.

Reads the REAL current context size from the session transcript (the API's own
token accounting, not an estimate) and emits a handover-prep banner once the
context crosses a threshold. Fires each threshold at most ONCE per session so it
nudges rather than nags.

Context size = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
of the most recent assistant turn (that sum is the full input the model re-read).

Thresholds (Syafiq, 2026-06-12):
  SOFT 100k  — "start wrapping up, prep a /handover soon"
  HARD 145k  — "wrap + /handover NOW" (auto-compact fires at 160k = 80% of 200k)

Safety: never blocks the prompt. Any error -> silent exit 0.
"""
import json
import sys
from pathlib import Path

SOFT = 100_000
HARD = 145_000
WINDOW = 200_000  # nominal context window, for the % readout

STATE_DIR = Path(__file__).resolve().parent.parent / "logs"
STATE_FILE = STATE_DIR / "context_watch_state.json"


def current_context_tokens(transcript_path: str) -> int | None:
    """Sum the input-side tokens of the latest assistant turn that has usage."""
    p = Path(transcript_path)
    if not p.exists():
        return None
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for ln in reversed(lines):
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        msg = obj.get("message") or {}
        usage = msg.get("usage")
        if not usage:
            continue
        return (
            int(usage.get("input_tokens", 0) or 0)
            + int(usage.get("cache_read_input_tokens", 0) or 0)
            + int(usage.get("cache_creation_input_tokens", 0) or 0)
        )
    return None


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # no input -> nothing to do
    session_id = payload.get("session_id", "unknown")
    transcript_path = payload.get("transcript_path", "")

    tokens = current_context_tokens(transcript_path)
    if tokens is None:
        return

    state = load_state()
    fired = set(state.get(session_id, []))

    level = None
    if tokens >= HARD and "hard" not in fired:
        level = "hard"
    elif tokens >= SOFT and "soft" not in fired:
        level = "soft"

    if level is None:
        return

    fired.add(level)
    state[session_id] = sorted(fired)
    save_state(state)

    pct = round(100 * tokens / WINDOW)
    k = round(tokens / 1000)
    if level == "soft":
        print(
            f"🔔 [CONTEXT WATCH] Session context ≈ {k}k tokens (~{pct}% of {WINDOW//1000}k). "
            f"SOFT threshold ({SOFT//1000}k) crossed. Tell Syafiq: we've left the sweet spot — "
            f"start wrapping the current thread and prep a /handover soon. Each further turn now "
            f"re-bills ~{k}k+ tokens against the session limit."
        )
    else:  # hard
        print(
            f"🚨 [CONTEXT WATCH] Session context ≈ {k}k tokens (~{pct}% of {WINDOW//1000}k). "
            f"HARD threshold ({HARD//1000}k) crossed — auto-compact fires at 160k. Tell Syafiq "
            f"PLAINLY: finish only what's in flight, then run /handover and start a FRESH session. "
            f"Pushing further degrades accuracy and burns the limit fast."
        )


if __name__ == "__main__":
    main()
