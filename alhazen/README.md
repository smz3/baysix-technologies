# Alhazen

A research lab, not a trading bot. Named for Ibn al-Haytham, who founded the scientific method by
building the instrument that let him be proven wrong.

**Status: pre-G1 exploration.** No idea row, no gate, no code, no market chosen. This folder is a
home for the thinking, not a build. It does not outrank the GRW mandate.

---

## Purpose

In markets, almost nobody can tell whether they got better — they can only tell whether they made
money. Those are not the same thing. Alhazen is built to close that gap first, and to trade second.

## Mission

Build systems that make better decisions under uncertainty, and the judge that proves they did.
Freeze the signal, vary the policy, score the gap between the decision taken and the best decision
available at the time. Live capital is the referee, not the objective.

## Vision

One person, running a desk's worth of coverage — hundreds of falsifiable claims a week, each
resolving itself on a clock without a human grading it, accumulating into a long, honest record of
decisions paired with what actually happened. The trading book is the receipt for that record, not
the product.

## Operating principles

1. **Grader before agent.** The environment decides what can be learned; the model is swappable.
2. **Decisions, not predictions.** Improvement is a better call on the same information.
3. **Forced flow, not forecast.** Hunt obligation, not opinion.
4. **Falsifiable or it does not ship.** Every claim carries its own disproof condition.
5. **Coverage is the edge.** Breadth of ideas graded, not depth of one idea.

---

## Layout

| Path | What | Tracked |
|---|---|---|
| `README.md` | This file — the identity statement. | yes |
| `docs/` | Notes and specs cleared for the public repo. | yes |
| `private/` | Charter, brainstorms, unshared drafts. | **no** — gitignored |
| `data/` | Recorded market tape, once it exists. | **no** — gitignored |

`private/charter.md` is the long form of this README plus the settled decisions and the open
questions. `private/2026-08-11_model_brainstorm.md` is the original argument trail.

## Boundaries

- **Separate from the rest of this repo.** The baysix codebase — `research.db`, the FOB state
  engine, the MQL5 systems — is explicitly not Alhazen's foundation. Sharing a git remote is
  convenience, not architecture.
- **No `research.db` rows.** Alhazen is pre-G1 by design; its backlog tasks carry `idea_id = NULL`.
  Same treatment as the futures and job-hunt work.
- **This repo is public.** Anything that should stay private goes in `private/`.
