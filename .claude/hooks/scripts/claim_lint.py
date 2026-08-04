#!/usr/bin/env python3
"""claim_lint — Loop A's executable guard (task 291).

Spec: docs/reference/grw_autonomous_workflow.md 1.2-1.4. Every claim carries a
provenance class (MEASURED / DERIVED / CITED / ASSUMED); RECALLED is banned.
Prose rules for this have now failed twice on the record (2026-08-03 audit,
2026-08-04 session), so the rule is executable or it is nothing.

TWO PLACEMENTS, because the failures live in two different places:

  Stop        -- lints `last_assistant_message`, the FINAL PROSE of the turn.
                 This is the load-bearing half. The three errors that reached
                 Syafiq on 2026-08-04 (fabricated attribution, a t-stat computed
                 off a non-independent n, a hypothesis stated as a decision)
                 were all prose. PreToolUse cannot see prose.
  PreToolUse  -- lints Write/Edit CONTENT (handovers, docs, plans) so a dead
                 path or a nonexistent table.column cannot reach disk.

HARD (blocks) -- only mechanically decidable things:
  1. DEAD_PATH   markdown link to a repo path that does not exist
  2. BAD_SCHEMA  table.column that research.db does not have
  3. STAT_NO_N   a t-stat / SE / p-value with no effective-n or independence
                 statement anywhere in the message

WARN (surfaces, does not block) -- judgement calls a regex should not arbitrate:
  4. ATTRIBUTION   second-person credit for a technical parameter
  5. UNADJUDICATED a strategy config called "decided" with no tester run cited
  6. ABSOLUTE      always / never / impossible with no DERIVED formula nearby

Loop guard: at most MAX_BLOCKS consecutive Stop blocks per session, then it
passes through with a note. A guard that can hang the session is worse than no
guard.

Escape hatch: CLAIM_LINT=off in the environment.
"""
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

MAX_BLOCKS = 2
REPO = Path(__file__).resolve().parents[3]
DB = REPO / "research" / "db" / "research.db"
STATE = Path(os.environ.get("TEMP", "/tmp")) / "claim_lint_blocks.json"

# ---------------------------------------------------------------- detectors

# t = +8.02 | t=-2.1 | t-stat of 3.4 | SE 0.0024 | ±se | p < 0.05 | z = 7.19
# EVERY alternative must bind to a NUMERAL. A bare `\bt-stat\b` fired on prose that
# merely discussed the concept ("the corrected t-stat, not the inflated one") — the
# check is about reporting a VALUE, not naming the statistic. Found by the guard
# blocking a handover reply, 2026-08-04.
STAT_RE = re.compile(
    r"(?:\bt\s*[=:]\s*[+-]?\d|\bt-stat\D{0,12}[+-]?\d|\bz\s*[=:]\s*[+-]?\d|"
    r"\bSE\s*[=:]?\s*\d|±\s*se\b|\bp\s*[<>=]\s*0?\.\d)",
    re.IGNORECASE,
)
# the words that make a t-stat honest
NEFF_RE = re.compile(
    r"(n_eff|n eff|effective n|effective sample|independen|overlap|"
    r"autocorrel|newey|block bootstrap|non-overlapping|de-?overlap)",
    re.IGNORECASE,
)
PROV_RE = re.compile(r"\b(MEASURED|DERIVED|CITED|ASSUMED)\b")
RESULT_ID_RE = re.compile(r"\bresult_id\s*\d+", re.IGNORECASE)

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
SCHEMA_RE = re.compile(r"\b([a-z][a-z0-9_]{2,})\.([a-z][a-z0-9_]{2,})\b")

ATTRIB_RE = re.compile(
    r"\byour\s+(?:[\w-]+\s+){0,2}"
    r"(stop|stops|sizing|risk|target|payoff|instinct|config|parameter|number|"
    r"fraction|threshold|barrier|floor|method)\b",
    re.IGNORECASE,
)
DECISION_RE = re.compile(
    r"\b(decided|the decision is|settled|locked in|final answer|"
    r"we will run|this is the config)\b", re.IGNORECASE,
)
TESTER_RE = re.compile(r"(tester|run_id|pass_id|backtest|\.set\b|OnTester)", re.IGNORECASE)
ABSOLUTE_RE = re.compile(
    r"\b(always|never survives|impossible|no strategy|cannot possibly|guaranteed)\b",
    re.IGNORECASE,
)

# extensions worth resolving; skip bare words that merely look like paths
PATHY = (".md", ".py", ".mq5", ".mqh", ".json", ".yaml", ".yml", ".db", ".csv", ".sql", ".txt")


def _tables() -> dict:
    """{table: {columns}} from the live DB. Empty dict if unavailable."""
    if not DB.exists():
        return {}
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
        out = {}
        for (t,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        ).fetchall():
            out[t] = {r[1] for r in con.execute(f"PRAGMA table_info('{t}')")}
        con.close()
        return out
    except Exception:
        return {}


def lint(text: str) -> tuple[list, list]:
    """-> (hard_failures, warnings)"""
    hard, warn = [], []
    if not text or len(text) < 40:
        return hard, warn

    # 1. dead markdown paths
    for m in MD_LINK_RE.finditer(text):
        raw = m.group(1)
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        if not raw.lower().endswith(PATHY) and "/" not in raw:
            continue
        # strip leading ./ and ../ SEGMENTS only — lstrip("./") would eat the
        # dot in ".claude/..." and report a live path as dead (caught by this
        # linter blocking its own spec edit, 2026-08-04).
        raw_n = raw.replace("\\", "/")
        p = re.sub(r"^(?:\.{1,2}/)+", "", raw_n)
        cands = [REPO / p, REPO / raw_n, Path(raw_n)]
        if not any(c.exists() for c in cands):
            hard.append(f"DEAD_PATH  [{raw}] does not resolve under {REPO.name}/")

    # 2. schema claims
    tabs = _tables()
    if tabs:
        for m in SCHEMA_RE.finditer(text):
            t, c = m.group(1), m.group(2)
            if t in tabs and c not in tabs[t]:
                hard.append(
                    f"BAD_SCHEMA  {t}.{c} - '{t}' exists but has no column '{c}'. "
                    f"Verify with PRAGMA table_info('{t}') before asserting it."
                )

    # 3. a statistic without its effective n
    if STAT_RE.search(text) and not NEFF_RE.search(text):
        hard.append(
            "STAT_NO_N  A t-stat / SE / p-value is reported with no effective sample "
            "size or independence statement. Overlapping samples inflate t by "
            "sqrt(overlap) - this is the 2026-08-04 error (t=+8.02 -> +0.83). "
            "State n_eff and why, or drop the statistic."
        )

    # 4-6. warnings
    if ATTRIB_RE.search(text):
        warn.append(
            "ATTRIBUTION  Second-person credit for a technical parameter. Confirm "
            "Syafiq actually specified it - a DERIVED value must not be returned "
            "to him as CITED (2026-08-04: the 100-pip stop was never his)."
        )
    if DECISION_RE.search(text) and not TESTER_RE.search(text):
        warn.append(
            "UNADJUDICATED  Decision language with no tester run cited. The MT5 "
            "Strategy Tester on real ticks is the arbiter (CLAUDE.md rule 8/16); "
            "until it has run, this is a hypothesis, not a decision."
        )
    for m in ABSOLUTE_RE.finditer(text):
        lo, hi = max(0, m.start() - 260), min(len(text), m.end() + 260)
        if not PROV_RE.search(text[lo:hi]):
            warn.append(f"ABSOLUTE  '{m.group(0)}' with no MEASURED/DERIVED basis nearby.")
            break

    # message-level provenance floor for findings-shaped prose
    if STAT_RE.search(text) and not PROV_RE.search(text) and not RESULT_ID_RE.search(text):
        warn.append(
            "NO_PROVENANCE  Statistics reported with no MEASURED/DERIVED/CITED/"
            "ASSUMED tag and no result_id. RECALLED is banned (spec 1.2)."
        )
    return hard, warn


# ---------------------------------------------------------------- loop guard

def _blocks(sid: str) -> int:
    try:
        return json.loads(STATE.read_text()).get(sid, 0)
    except Exception:
        return 0


def _set_blocks(sid: str, n: int) -> None:
    try:
        d = json.loads(STATE.read_text()) if STATE.exists() else {}
    except Exception:
        d = {}
    d[sid] = n
    try:
        STATE.write_text(json.dumps(d)[:20000])
    except Exception:
        pass


# ---------------------------------------------------------------- entrypoints

def main() -> None:
    if os.environ.get("CLAIM_LINT", "").lower() in ("off", "0", "false"):
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    event = data.get("hook_event_name", "")
    sid = str(data.get("session_id", "-"))

    if event in ("Stop", "SubagentStop"):
        text = data.get("last_assistant_message") or ""
        hard, warn = lint(text)
        if hard and _blocks(sid) >= MAX_BLOCKS:
            print(
                "[claim_lint] "
                + f"{len(hard)} unresolved after {MAX_BLOCKS} attempts - passing through. "
                + " | ".join(hard),
                file=sys.stderr,
            )
            _set_blocks(sid, 0)
            sys.exit(0)
        if hard:
            _set_blocks(sid, _blocks(sid) + 1)
            msg = ["[claim_lint] BLOCKED - fix these before replying:"]
            msg += [f"  - {h}" for h in hard]
            msg += [f"  ~ {w}" for w in warn]
            print("\n".join(msg), file=sys.stderr)
            sys.exit(2)
        _set_blocks(sid, 0)
        if warn:
            # stderr alone is invisible on exit 0 — surface it as a systemMessage,
            # otherwise this is a prose rule again and prose rules have already failed twice.
            body = "[claim_lint] " + " | ".join(w.split("  ", 1)[0] for w in warn)
            print(json.dumps({"systemMessage": body + "\n" + "\n".join(f"  ~ {w}" for w in warn)}))
            print("[claim_lint] warnings:\n" + "\n".join(f"  ~ {w}" for w in warn),
                  file=sys.stderr)
        sys.exit(0)

    # PreToolUse: lint content headed for disk
    tool = data.get("tool_name", "")
    if tool in ("Write", "Edit"):
        ti = data.get("tool_input") or {}
        path = (ti.get("file_path") or "").replace("\\", "/")
        if path.lower().endswith((".md", ".json", ".yaml", ".yml")):
            body = ti.get("content") or ti.get("new_string") or ""
            hard, _ = lint(body)
            hard = [h for h in hard if not h.startswith("STAT_NO_N")]
            if hard:
                print(json.dumps({
                    "decision": "block",
                    "reason": "[claim_lint] " + " | ".join(hard),
                }))
                sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
