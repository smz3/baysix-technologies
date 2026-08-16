"""
handover_lint.py — BLOCKING gate on the handover contract. Three checks:
  1. required sections present  (State/Next/Blockers + Why/Ruled-Out/Live-Threads — task 180)
  2. ## State is bullet-point form
  3. every result-shaped number cites a backing artifact (result_id or file on disk — task 50)

Why this exists
---------------
The ORB-001 saga started with a hand-typed "+67.4R / 56.5% win" pasted into a
handover with NO backing artifact (`git -S 67.4` found only the .md — the number
was a throwaway REPL print). CLAUDE.md rule 11 already required persistence but
had no teeth. This is the teeth.

What it flags (result-shaped numbers)
-------------------------------------
  R-multiples   +67.4R   -0.18R   0.45 R
  t-stats       t=10.74  t-stat 10.74  t 10.74
  win rates     56.5% win   13.6% win-rate
  $/trade       $7.62/trade   +$2/trade
  Sharpe        Sharpe 1.8   SR=1.8
  z-scores      z=+7.19

What clears a number (a valid citation in the SAME ## section)
--------------------------------------------------------------
  result_id     "result_id 121"  "result 121"  "#121"   (must exist in step4_results)
  artifact path "ReportTester-3.xlsx"  "outputs/foo.json"  "x.csv"  (must exist on disk)

Matching scope: SECTION. A number is OK if a valid citation appears anywhere
between the nearest "## " headers around it. Balanced — forces every claim-block
to carry a source without nagging on multi-number prose.

Fail-safe: a *blocking* gate that crashes would block ALL handovers. So any
internal/parse error fails OPEN (prints a warning, exit 0). Only a confirmed
uncited result-number blocks (exit 1).

Usage
-----
  python research/code/infra/handover_lint.py <handover.md> [<handover2.md> ...]
  exit 0 = clean (or failed-open);  exit 1 = blocked (uncited numbers found)
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).parents[3]
from research.code.infra.db_path import DB_PATH  # noqa: F401  (task 357: one canonical path)
# --- result-shaped number patterns -------------------------------------------
# Each entry: (label, compiled regex). Kept deliberately specific to avoid
# flagging dates ($50 capital, 2026-06-12, version numbers, task IDs).
NUMBER_PATTERNS = [
    # R-multiple: must be SIGNED or DECIMAL. A bare "1R"/"2R" is a risk-unit /
    # R:R ratio / trail distance (config, not a result) — deliberately excluded.
    ("R-multiple", re.compile(r"(?:[+\-−]\d+(?:\.\d+)?|\d+\.\d+)\s?R\b")),
    ("t-stat",     re.compile(r"\bt[\s=\-]?(?:stat\s*)?[+\-−]?\d+\.\d+")),
    # win-rate: number-then-"win"  OR  "win[-rate]"-then-number
    ("win-rate",   re.compile(r"(?:\d+(?:\.\d+)?\s?%\s?(?:win|win-?rate)"
                              r"|win[\s-]?(?:rate)?\s*[:=]?\s*\d+(?:\.\d+)?\s?%)", re.I)),
    ("$/trade",    re.compile(r"[+\-−]?\$\d+(?:\.\d+)?\s?/\s?(?:trade|t)\b", re.I)),
    ("Sharpe",     re.compile(r"\b(?:Sharpe|SR)[\s=:]+[+\-−]?\d+(?:\.\d+)?", re.I)),
    ("z-score",    re.compile(r"\bz[\s=]?[+\-−]?\d+\.\d+")),
]

# --- citation patterns -------------------------------------------------------
RESULT_ID_RE = re.compile(r"(?:result[_\s]?id|result|#)\s*(\d+)", re.I)
# artifact path: a token containing a path separator OR a known result extension
ARTIFACT_RE = re.compile(
    r"[\w./\\\-]+\.(?:xlsx|csv|json|parquet|png|html)\b", re.I
)


def _valid_result_ids() -> set[int]:
    """All result_ids that actually exist in step4_results. Empty set on any DB error (caller fails open)."""
    con = sqlite3.connect(DB_PATH)
    try:
        return {r[0] for r in con.execute("SELECT result_id FROM step4_results")}
    finally:
        con.close()


def _split_sections(text: str) -> list[tuple[int, str]]:
    """Split on '## ' (or deeper) markdown headers. Returns [(start_line_no, section_text), ...].
    Content before the first header is its own section."""
    lines = text.splitlines()
    sections: list[tuple[int, list[str]]] = [(1, [])]
    for i, line in enumerate(lines, start=1):
        if re.match(r"^#{2,}\s", line):
            sections.append((i, [line]))
        else:
            sections[-1][1].append(line)
    return [(ln, "\n".join(body)) for ln, body in sections]


def _citations_in(section: str, valid_ids: set[int]) -> bool:
    """True if the section carries at least one VALID citation (existing result_id or existing file)."""
    for m in RESULT_ID_RE.finditer(section):
        if int(m.group(1)) in valid_ids:
            return True
    for m in ARTIFACT_RE.finditer(section):
        token = m.group(0).replace("\\", "/").lstrip("./")
        # accept if the path exists relative to repo root, or basename matches anywhere sensible
        cand = REPO / token
        if cand.exists():
            return True
        # bare filename (e.g. ReportTester-3.xlsx) — accept if any match exists under repo
        base = Path(token).name
        if base != token:  # had dirs but didn't resolve — don't brute-force search
            continue
        # cheap basename probe in the usual artifact homes
        for home in ("", "mt5", "research/outputs", "research", "data"):
            if list((REPO / home).glob(base)) if (REPO / home).exists() else []:
                return True
    return False


# --- required-section contract (task 180) ------------------------------------
# Every handover must carry the HEAD (what-to-do, also in log_tasks) AND the
# NARRATIVE (why / dead-ends / loose threads — lives nowhere else). A narrative
# section can satisfy with an explicit "- None this session." but it must EXIST,
# so the author consciously decides each one instead of silently dropping it.
# Header text is matched tolerantly: "Ruled-Out" / "Ruled Out", "Live-Threads" /
# "Live Threads", any case.
REQUIRED_SECTIONS = [
    ("State",        re.compile(r"^#{2,}\s+State\b", re.I | re.M)),
    ("Next",         re.compile(r"^#{2,}\s+Next\b", re.I | re.M)),
    ("Blockers",     re.compile(r"^#{2,}\s+Blockers\b", re.I | re.M)),
    ("Why",          re.compile(r"^#{2,}\s+Why\b", re.I | re.M)),
    ("Ruled-Out",    re.compile(r"^#{2,}\s+Ruled[\s\-]?Out\b", re.I | re.M)),
    ("Live-Threads", re.compile(r"^#{2,}\s+Live[\s\-]?Threads\b", re.I | re.M)),
]


def _check_required_sections(text: str, path: Path) -> list[str]:
    """Every handover must carry all REQUIRED_SECTIONS. Missing ones block."""
    missing = [name for name, pat in REQUIRED_SECTIONS if not pat.search(text)]
    if missing:
        return [f"{path.name}  missing required section(s): {', '.join(missing)} "
                f"(narrative sections may say '- None this session.' but must exist — task 180)"]
    return []


def _check_state_bullets(text: str, path: Path) -> list[str]:
    """## State section must use bullet points (lines starting with - or *)."""
    in_state = False
    bullet_found = False
    prose_lines: list[int] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^##\s+State\b", line, re.I):
            in_state = True
            continue
        if in_state:
            if re.match(r"^#{2,}\s", line):
                break  # left the section
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("-", "*")):
                bullet_found = True
            else:
                prose_lines.append(i)
    if not in_state:
        return []  # no ## State section — skip
    if prose_lines and not bullet_found:
        return [f"{path.name}  ## State section must be bullet-point form (use - or *); prose found on lines {prose_lines[:3]}"]
    if prose_lines:
        return [f"{path.name}  ## State section has mixed prose+bullets; all lines must be bullet-point (lines {prose_lines[:3]})"]
    return []


def lint_file(path: Path, valid_ids: set[int]) -> list[str]:
    """Return a list of violation strings for one handover file. Empty = clean."""
    text = path.read_text(encoding="utf-8", errors="replace")
    violations: list[str] = _check_required_sections(text, path)
    violations += _check_state_bullets(text, path)
    for start_ln, section in _split_sections(text):
        # find result-shaped numbers in this section
        hits: list[tuple[str, str]] = []
        for label, pat in NUMBER_PATTERNS:
            for m in pat.finditer(section):
                hits.append((label, m.group(0).strip()))
        if not hits:
            continue
        if _citations_in(section, valid_ids):
            continue
        # section has numbers but no valid citation -> violations
        header = section.splitlines()[0].strip() if section.strip() else "(preamble)"
        uniq = sorted({f"{lbl}:{val}" for lbl, val in hits})
        violations.append(
            f"{path.name}  section '{header[:50]}' (line {start_ln}): "
            f"{len(uniq)} uncited number(s) -> {', '.join(uniq)}"
        )
    return violations


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv]
    paths = [p for p in paths if p.suffix.lower() == ".md" and p.exists()]
    if not paths:
        print("handover_lint: no handover .md files to check — skipping.")
        return 0

    try:
        valid_ids = _valid_result_ids()
    except Exception as e:  # noqa: BLE001 — fail OPEN, never block on infra error
        print(f"handover_lint: WARN could not read step4_results ({e}) — failing open.")
        return 0

    all_violations: list[str] = []
    for p in paths:
        try:
            all_violations += lint_file(p, valid_ids)
        except Exception as e:  # noqa: BLE001 — fail OPEN per-file
            print(f"handover_lint: WARN could not parse {p.name} ({e}) — failing open.")

    if not all_violations:
        print(f"handover_lint: OK — {len(paths)} file(s) clean, every result-number cited.")
        return 0

    print("=" * 72)
    print("handover_lint: BLOCKED — handover contract violation(s).")
    print("Fixes: (a) add any missing section (narrative may say '- None this session.');")
    print("       (b) make ## State bullet-point form;")
    print("       (c) cite each result-number with a step4_results result_id or an")
    print("           on-disk artifact path (ReportTester-*.xlsx, outputs/**/*.json|csv).")
    print("-" * 72)
    for v in all_violations:
        print("  " + v)
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
