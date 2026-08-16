"""
backfill_dissect_md.py — persist a paper's stored DISSECT as the git-tracked
`<stem>.dissect.md` artifact.

WHY: the dissection narrative lives in research.db (step2_papers + the DISSECT
log_agent row). The pipeline (CLAUDE.md rule 5b) wants a human-readable, git-tracked
`<stem>.dissect.md` next to the PDF. This tool reconstructs that file FROM the DB —
text flows DB -> file and is never printed, so it never enters orchestrator context
(rule 9).

Path is derived from step2_papers.local_path (.pdf -> .dissect.md). Idempotent:
overwrites the .dissect.md (the DB is the source of truth).

Usage:
    python research/code/io/backfill_dissect_md.py 28 29 30      # specific paper_ids
    python research/code/io/backfill_dissect_md.py --idea B2B-001 # all dissected papers for an idea
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from research.code.infra.db_path import DB_PATH  # noqa: F401  (task 357: one canonical path)
def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_dissect_log(conn: sqlite3.Connection, paper_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT model, task_summary, output_summary, created_at
           FROM log_agent
           WHERE paper_id=? AND gear='DISSECT'
           ORDER BY call_id DESC LIMIT 1""",
        (paper_id,),
    ).fetchone()


def _render(paper: sqlite3.Row, log: sqlite3.Row | None) -> str:
    model = (log["model"] if log else None) or "unknown"
    when  = (log["created_at"] if log else None) or paper["dissected_at"] or ""
    parts = [
        f"# Dissection — {paper['title']}",
        "",
        f"- **Authors:** {paper['authors'] or 'n/a'}",
        f"- **Year:** {paper['year'] or 'n/a'}",
        f"- **paper_id:** {paper['paper_id']}  ·  **idea:** {paper['idea_id']}",
        f"- **Model:** {model}  ·  **Dissected:** {when}",
        f"- **Source:** {paper['source'] or 'n/a'}  ·  **DOI:** {paper['doi'] or 'n/a'}",
        "",
        "> Reconstructed from research.db (step2_papers + DISSECT log_agent) by "
        "backfill_dissect_md.py. The DB is the source of truth.",
        "",
    ]
    if log and (log["output_summary"] or "").strip():
        parts += ["## Summary", "", log["output_summary"].strip(), ""]
    parts += [
        "## Key Equations", "", (paper["key_equations"] or "_none recorded_").strip(), "",
        "## Empirical Findings", "", (paper["empirical_findings"] or "_none recorded_").strip(), "",
        "## Context Fit", "", (paper["context_fit"] or "_none recorded_").strip(), "",
        "## Limitations", "", (paper["limitations"] or "_none recorded_").strip(), "",
    ]
    return "\n".join(parts)


def _one(conn: sqlite3.Connection, paper_id: int) -> Path | None:
    paper = conn.execute(
        "SELECT * FROM step2_papers WHERE paper_id=?", (paper_id,)
    ).fetchone()
    if paper is None:
        print(f"[skip] paper_id={paper_id} not found")
        return None
    if not paper["dissected"]:
        print(f"[skip] paper_id={paper_id} not yet dissected")
        return None
    if not paper["local_path"]:
        print(f"[skip] paper_id={paper_id} has no local_path — run set_local_path first")
        return None

    out = Path(paper["local_path"]).with_suffix("")
    out = out.with_name(out.name + ".dissect.md")
    log = _latest_dissect_log(conn, paper_id)
    out.write_text(_render(paper, log), encoding="utf-8")
    print(f"[ok] wrote {out}  ({out.stat().st_size:,} bytes)")
    return out


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_ids", nargs="*", type=int)
    ap.add_argument("--idea")
    args = ap.parse_args(argv)

    with _conn() as conn:
        ids = list(args.paper_ids)
        if args.idea:
            ids += [
                r["paper_id"]
                for r in conn.execute(
                    "SELECT paper_id FROM step2_papers WHERE idea_id=? AND dissected=1 ORDER BY paper_id",
                    (args.idea,),
                )
            ]
        if not ids:
            sys.exit("no paper_ids given (pass ids or --idea)")
        for pid in dict.fromkeys(ids):  # dedupe, preserve order
            _one(conn, pid)


if __name__ == "__main__":
    main(sys.argv[1:])
