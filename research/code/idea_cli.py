"""Thin read-only CLI over the research/code/ getters — replaces the ad-hoc DB
queries Claude used to type by hand before briefing the QR agent / coding a model.

Three subcommands, each maps to a CLAUDE.md rule:
    prebrief  <idea_id>   rule 6  — idea + prior agent calls + open tasks (pre-brief check)
    gatecheck <idea_id>   rule 8  — gate table + hard PASS/BLOCK on Gates 0 & 1
    next      <idea_id>            — the ONE next legal protocol action, computed from DB state
    status    <idea_id>            — one snapshot: status + live config + spec + latest results + tasks

MAINTAINABILITY (the point of keeping it thin): this file holds NO schema or
workflow logic of its own. It only calls pipeline/strategy_log/backlog/agent_log
getters and renders what they return. When the workflow or DB shape changes, the
code-layer getters change and this CLI follows for free. The only thing to touch
here is display formatting. Text-heavy columns (rule 9) are auto-truncated by
key name, so adding a new long column never risks dumping it into context.

USAGE:
    python research/code/idea_cli.py prebrief ORB-001
    python research/code/idea_cli.py gatecheck HMM-001
    python research/code/idea_cli.py status ORB-002
"""
from __future__ import annotations

import argparse
import sys

import agent_log
import backlog
import pipeline
import protocol
import strategy_log

# rule 9 — never render these in full; truncate hard.
_TEXT_HEAVY = {
    "key_equations", "empirical_findings", "context_fit", "limitations",
    "gate_answer", "output_summary", "task_summary", "rationale", "detail",
    "notes", "description",
}
_TRUNC = 100


def _val(key: str, v) -> str:
    s = "" if v is None else str(v).replace("\n", " ")
    if key in _TEXT_HEAVY and len(s) > _TRUNC:
        return s[:_TRUNC] + "..."
    return s


def _row(d: dict, keys=None) -> str:
    keys = keys or list(d.keys())
    return " · ".join(f"{k}={_val(k, d.get(k))}" for k in keys if k in d)


def _hdr(t: str) -> None:
    print(f"\n-- {t} " + "-" * max(0, 60 - len(t)))


def cmd_prebrief(idea_id: str) -> int:
    idea = pipeline.get_idea(idea_id)
    if not idea:
        print(f"no idea {idea_id!r}")
        return 1
    _hdr(f"IDEA {idea_id}")
    print(_row(idea))

    calls = agent_log.get_agent_calls(idea_id)
    _hdr(f"PRIOR AGENT CALLS ({len(calls)})")
    for c in calls:
        print("  " + _row(c, ["call_id", "gate_number", "gear", "model",
                              "source", "task_summary", "created_at"]))

    tasks = backlog.get_backlog(status="open", idea_id=idea_id)
    _hdr(f"OPEN TASKS ({len(tasks)})")
    for t in tasks:
        print("  " + _row(t, ["task_id", "kind", "title", "detail"]))
    print("\n(rule 6 satisfied — don't re-surface anything above)")
    return 0


def cmd_gatecheck(idea_id: str) -> int:
    gates = pipeline.get_gates(idea_id)
    if not gates:
        print(f"{idea_id}: NO gates opened — BLOCK (open & pass 0,1 first)")
        return 1
    _hdr(f"GATES {idea_id}")
    by_num = {}
    for g in gates:
        n = g.get("gate_number")
        by_num[n] = g.get("status")
        print("  " + _row(g, ["gate_number", "gate_name", "status", "updated_at"]))
    ok = by_num.get(0) == "passed" and by_num.get(1) == "passed"
    verdict = "PASS — clear to write model code" if ok else \
        "BLOCK — Gates 0 & 1 must be 'passed' before any model code (rule 8)"
    print(f"\n{verdict}")
    return 0 if ok else 2


def cmd_next(idea_id: str) -> int:
    d = protocol.next_step(idea_id)
    if d.get("error"):
        print(d["error"])
        return 1
    _hdr(f"PROTOCOL {idea_id}")
    print(f"  status    : {d['status']}")
    print(f"  idea_kind : {d['idea_kind']}")
    print(f"  gates     : {d['gates']}   (P=passed o=open X=blocked K=killed -=none)")
    print(f"  applies   : {d['applies']}   (gates this idea_kind must clear)")
    print(f"  sig_test  : {d['sig_test']}   (Gate-5 test, resolved from output_type)")
    print(f"  falsified : {d['falsified']}")
    print(f"\n  NEXT  -> {d['next']}")
    print(f"  WHY   -> {d['why']}")
    for w in d.get("warnings", []):
        print(f"  ⚠️  {w}")
    return 0


def cmd_status(idea_id: str) -> int:
    idea = pipeline.get_idea(idea_id)
    if not idea:
        print(f"no idea {idea_id!r}")
        return 1
    _hdr(f"STATUS {idea_id}")
    print(_row(idea, ["idea_id", "title", "status", "asset_class", "updated_at"]))

    for label, fn in (("LIVE CONFIG", strategy_log.get_live_config),
                      ("SPEC", strategy_log.get_spec)):
        _hdr(label)
        try:
            d = fn(idea_id)
            print(_row(d) if d else "  (none)")
        except Exception as e:
            print(f"  (none — {e})")

    res = pipeline.get_results(idea_id)
    _hdr(f"LATEST RESULTS ({len(res)}, showing 5)")
    for r in res[:5]:
        print("  " + _row(r, ["result_id", "metric_name", "metric_value",
                              "verdict", "created_at"]))

    tasks = backlog.get_backlog(status="open", idea_id=idea_id)
    _hdr(f"OPEN TASKS ({len(tasks)})")
    for t in tasks:
        print("  " + _row(t, ["task_id", "kind", "title"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prebrief", "gatecheck", "next", "status"):
        p = sub.add_parser(name)
        p.add_argument("idea_id")
    args = ap.parse_args()
    return {"prebrief": cmd_prebrief, "gatecheck": cmd_gatecheck,
            "next": cmd_next, "status": cmd_status}[args.cmd](args.idea_id)


if __name__ == "__main__":
    sys.exit(main())
