#!/usr/bin/env python3
"""style_lint — executable guard for the two GLOBAL CLAUDE.md directives.

Syafiq set both rules in the global CLAUDE.md months ago. They kept being
followed for a few turns and then quietly abandoned — most recently 2026-08-16,
when a task-360 answer came back at ~450 prose words across 8 sections with a
table, and Syafiq had to ask why the format rule was not being applied. That is
the third documented failure mode of a prose-only rule in this repo (see
claim_lint.py's docstring for the first two), so the rule becomes executable or
it is nothing.

THE TWO DIRECTIVES BEING ENFORCED
  1. DUMB MODE      "Always output explanation in Dumb Mode version. few bullet
                     points. the simpler the better."
  2. FIRST PRINCIPLE "Break a problem down to its most fundamental, undeniable
                     truths and reason up from there, rather than reasoning by
                     analogy or convention."

PLACEMENT: Stop only. These are properties of the FINAL PROSE of a turn, and
PreToolUse cannot see prose. Documents written to disk are deliberately NOT
linted — a handover or a spec is allowed to be long; a reply to Syafiq is not.

HARD (blocks) — only mechanically decidable things, same bar as claim_lint:
  1. WORDY        prose word count over MAX_WORDS
  2. LONG_SENT    one sentence over MAX_SENT, or a mean over MAX_MEAN
  3. WALL         a non-bullet paragraph over MAX_PARA words
  4. NO_GROUND    a recommendation/decision is stated and NOTHING in the message
                  is marked as a checked or measured fact. This is the first
                  principle in its only mechanically testable form: you may not
                  reason up if you never said what you are reasoning up FROM.

WARN (surfaces, does not block) — judgement calls a regex should not arbitrate:
  5. JARGON       a technical term used with no plain-English gloss near it
  6. BY_ANALOGY   "industry standard / best practice / typically" with no
                  foundational-truth marker nearby — reasoning by convention
  7. SECTIONS     more than MAX_HEADS headers; "few bullet points", not a report

OPT-OUT, three ways, because a guard that cannot be turned off gets turned off
permanently by deleting it:
  - env STYLE_LINT=off
  - Syafiq asks for depth in his own message ("in detail", "long version", ...)
  - MAX_BLOCKS consecutive blocks in a session, then it passes through with a
    note. A guard that can hang the session is worse than no guard.
"""
import json
import os
import re
import sys
from pathlib import Path

MAX_WORDS = 350      # prose words; the 2026-08-16 violation was ~450
MAX_SENT = 45        # words in any single sentence
MAX_MEAN = 25        # mean words per sentence
MAX_PARA = 90        # words in one non-bullet paragraph
MAX_HEADS = 6        # markdown/bold section headers
MIN_LINT = 60        # below this many words there is nothing to judge
MAX_BLOCKS = 2

STATE = Path(os.environ.get("TEMP", "/tmp")) / "style_lint_blocks.json"

# ---------------------------------------------------------------- stripping

CODE_RE = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]+`", re.DOTALL)
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
HEAD_RE = re.compile(r"^\s*(?:#{1,6}\s+\S|\*\*[^*\n]{3,60}\*\*\s*$)", re.MULTILINE)


def _prose(text: str) -> str:
    """Text with code, tables and link targets removed.

    Code and tables are not prose — a quoted command or a two-column table is
    the SIMPLE way to say something, so counting them as verbosity would push
    the reply back toward paragraphs, which is the opposite of the directive.
    """
    t = CODE_RE.sub(" ", text)
    t = TABLE_RE.sub(" ", t)
    return LINK_RE.sub(r"\1", t)


def _words(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][\w'-]*", s))


def _sentences(s: str) -> list:
    """Sentence-ish units. A LINE BREAK ends a unit, same as a full stop.

    Bullets do not carry terminal punctuation, so splitting on [.!?] alone
    welded a whole bullet list into one enormous 'sentence' and LONG_SENT fired
    on it. MEASURED 2026-08-16: this guard blocked the very reply announcing
    this guard, on a list whose longest bullet was six words.
    """
    parts = re.split(r"(?<=[.!?])\s+|\n+", s)
    return [p.strip() for p in parts if _words(p) >= 3]


# ---------------------------------------------------------------- detectors

# a claim that something SHOULD happen
RECO_RE = re.compile(
    r"\b(I recommend|my recommendation|we should|you should|I'd (?:go|pick)|"
    r"the (?:right|correct|best) (?:call|answer|move|approach)|let's|"
    r"the fix is|the answer is|I'd suggest|I suggest)\b",
    re.IGNORECASE,
)
# something asserted as CHECKED, not remembered
GROUND_RE = re.compile(
    r"\b(MEASURED|DERIVED|CITED|ASSUMED|I checked|I read|I verified|verified|"
    r"confirmed|measured|does not exist|doesn't exist|zero rows|0 rows|"
    r"on disk|returns|grep|log_id|result_id|task \d+|line \d+)\b",
    re.IGNORECASE,
)
# reasoning by convention instead of from fundamentals
ANALOGY_RE = re.compile(
    r"\b(industry standard|best practice|standard approach|common practice|"
    r"typically|usually|conventionally|most people|everyone (?:does|uses)|"
    r"the normal way|as is customary)\b",
    re.IGNORECASE,
)
FIRST_PRIN_RE = re.compile(
    r"\b(first principle|from scratch|fundamental|undeniable|what we know|"
    r"the physics|by definition|reason up|blank page|ground truth)\b",
    re.IGNORECASE,
)
# terms that mean nothing to someone with zero background
JARGON = (
    "denominator", "multiplicity", "idempotent", "orthogonal", "canonical",
    "deterministic", "provenance", "heuristic", "stochastic", "monotonic",
    "marginal", "posterior", "autocorrelation", "contention", "throughput",
    "atomic", "schema", "DDL", "FK", "WAL", "spine", "ledger", "registry",
    "lease", "namespace", "topology", "invariant", "cardinality",
)
JARGON_RE = re.compile(r"\b(" + "|".join(JARGON) + r")\b", re.IGNORECASE)
# a gloss: an equals sign, a dash-explainer, or an explicit definition phrase
GLOSS_RE = re.compile(r"(=|—|--|\bmeans\b|\bi\.e\.\b|\bthat is\b|\bin other words\b|\()")

# Syafiq explicitly asking for depth
DEPTH_RE = re.compile(
    r"\b(in detail|long version|full (?:explanation|version|detail)|verbose|"
    r"deep dive|no dumb mode|explain fully|walk me through|write the (?:doc|spec))\b",
    re.IGNORECASE,
)


def lint(text: str) -> tuple[list, list]:
    """-> (hard_failures, warnings)"""
    hard, warn = [], []
    prose = _prose(text or "")
    n = _words(prose)
    if n < MIN_LINT:
        return hard, warn

    # 1. total length
    if n > MAX_WORDS:
        hard.append(
            f"WORDY  {n} prose words (limit {MAX_WORDS}). Global CLAUDE.md: "
            f"'few bullet points, the simpler the better'. Cut to the decision "
            f"and the reason for it."
        )

    # 2. sentence length
    sents = _sentences(prose)
    if sents:
        longest = max(sents, key=_words)
        if _words(longest) > MAX_SENT:
            hard.append(
                f"LONG_SENT  a {_words(longest)}-word sentence (limit {MAX_SENT}): "
                f"\"{longest[:70]}...\" Split it."
            )
        mean = sum(_words(s) for s in sents) / len(sents)
        if mean > MAX_MEAN:
            hard.append(
                f"LONG_SENT  mean sentence {mean:.0f} words (limit {MAX_MEAN}). "
                f"Short sentences ARE the dumb-mode format."
            )

    # 3. wall of text
    for para in re.split(r"\n\s*\n", prose):
        if BULLET_RE.search(para) or HEAD_RE.search(para):
            continue
        if _words(para) > MAX_PARA:
            hard.append(
                f"WALL  a {_words(para)}-word paragraph (limit {MAX_PARA}). "
                f"Bullets, not paragraphs."
            )
            break

    # 4. first principle, in its only testable form
    if RECO_RE.search(prose) and not GROUND_RE.search(text):
        hard.append(
            "NO_GROUND  A recommendation is made and nothing in the message is "
            "marked as checked or measured. First principle: state the "
            "undeniable facts you reasoned UP from, or do not recommend."
        )

    # 5-7. warnings
    for m in JARGON_RE.finditer(prose):
        lo, hi = m.end(), min(len(prose), m.end() + 90)
        if not GLOSS_RE.search(prose[lo:hi]):
            warn.append(
                f"JARGON  '{m.group(0)}' used with no plain-English gloss after it. "
                f"Zero background is the assumption."
            )
            break
    if ANALOGY_RE.search(prose) and not FIRST_PRIN_RE.search(prose):
        m = ANALOGY_RE.search(prose)
        warn.append(
            f"BY_ANALOGY  '{m.group(0)}' with no foundational-truth basis nearby. "
            f"Global CLAUDE.md bans reasoning by analogy or convention."
        )
    heads = len(HEAD_RE.findall(text))
    if heads > MAX_HEADS:
        warn.append(f"SECTIONS  {heads} headers (limit {MAX_HEADS}). This is a reply, not a report.")
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


def _last_user_text(transcript_path: str) -> str:
    """Syafiq's most recent real message, or '' if it cannot be read.

    Tool results arrive with role 'user' too, so a row only counts when it
    carries actual text. Any failure returns '' and the lint proceeds — an
    unreadable transcript must not silently disable the guard.
    """
    try:
        p = Path(transcript_path)
        if not p.exists():
            return ""
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return ""
    for r in reversed(rows):
        msg = r.get("message") or {}
        if msg.get("role") != "user":
            continue
        c = msg.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            txt = " ".join(b.get("text", "") for b in c
                           if isinstance(b, dict) and b.get("type") == "text")
            if txt.strip():
                return txt
    return ""


# ---------------------------------------------------------------- entrypoint

def main() -> None:
    if os.environ.get("STYLE_LINT", "").lower() in ("off", "0", "false"):
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("hook_event_name", "") not in ("Stop", "SubagentStop"):
        sys.exit(0)

    sid = str(data.get("session_id", "-"))
    text = data.get("last_assistant_message") or ""

    # Syafiq asked for depth -> the directive is waived by him, not by me
    if DEPTH_RE.search(_last_user_text(data.get("transcript_path", ""))):
        sys.exit(0)

    hard, warn = lint(text)

    if hard and _blocks(sid) >= MAX_BLOCKS:
        print(f"[style_lint] {len(hard)} unresolved after {MAX_BLOCKS} attempts - "
              "passing through. " + " | ".join(hard), file=sys.stderr)
        _set_blocks(sid, 0)
        sys.exit(0)

    if hard:
        _set_blocks(sid, _blocks(sid) + 1)
        msg = ["[style_lint] BLOCKED - rewrite in Dumb Mode before replying:"]
        msg += [f"  - {h}" for h in hard]
        msg += [f"  ~ {w}" for w in warn]
        print("\n".join(msg), file=sys.stderr)
        sys.exit(2)

    _set_blocks(sid, 0)
    if warn:
        body = "[style_lint] " + " | ".join(w.split("  ", 1)[0] for w in warn)
        print(json.dumps({"systemMessage": body + "\n" + "\n".join(f"  ~ {w}" for w in warn)}))
        print("[style_lint] warnings:\n" + "\n".join(f"  ~ {w}" for w in warn), file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
