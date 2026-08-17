# Baysix Technologies

**Research infrastructure for systematic trading — built to *falsify* trading ideas, not just showcase winners.**

[![Project Status: Suspended](https://www.repostatus.org/badges/latest/suspended.svg)](https://www.repostatus.org/#suspended)
![Python](https://img.shields.io/badge/Python-223%20files-3776AB?logo=python&logoColor=white)
![MQL5](https://img.shields.io/badge/MQL5-63%20files-1E88E5)
![SQLite](https://img.shields.io/badge/ledger-baysix.db-003B57?logo=sqlite&logoColor=white)
![ArcticDB](https://img.shields.io/badge/tick%20store-XAUUSD%202016--2026-2E7D32)

> ### 📦 Status: paused — August 2026
>
> **This repository is a completed research record, not an actively developed system.**
> It is preserved as-is because the falsification history below is the deliverable.
>
> Active development has moved to a successor project that rebuilds the
> strategy-generation layer from scratch. What is here — the tick-data layer, the MQL5
> verifier, the gated protocol, and the record of what was killed and why — remains
> accurate and readable.
>
> Issues and PRs are not being monitored. Read it as a portfolio of research process.

This is a working, single-operator quant-research program: a disciplined pipeline that turns published ideas into testable hypotheses, runs them against a tick-accurate market simulator, and **kills the ones that don't survive** — with the reasons recorded. The rare thing on display here isn't a profitable strategy; it's a documented record of *how ideas were killed*, which is the harder and scarcer skill.

---

## Why this repo is different: the falsification record

Most trading portfolios show only what worked. This one shows the graveyard, because in research the discipline to reject a false edge matters more than the luck of finding a real one.

| Idea | Status | Why |
|------|--------|-----|
| Opening-range breakout timing | ❌ **Killed** | An apparent edge turned out to be **look-ahead bias**: ticks weren't time-sorted, so "first breakout" was chosen with future information. On chronologically-sorted ticks, the edge vanished. |
| Support/resistance zone reaction | ⏸️ **Parked** | Entry-fade and entry-continuation produced statistically indistinguishable expectancy → **no directional edge**. Parked rather than force-fit. |
| Break-retest continuation (BRC-001) | ⏸️ **Parked at Gate 2** | Premise gate passed on three dissected papers; the edge-and-survival gate was never answered. Machinery archived, evidence retained. |
| Multi-timeframe breakout-reaction (FOB-001) | ⏸️ **Parked at Gate 1** | A cross-timeframe *reaction* model, not a win-rate classifier. Substantial engineering exists; the premise gate is still formally unanswered, so it is parked rather than claimed. |

Every one of these decisions is logged in a SQLite research ledger (`db/baysix.db`) with the hypothesis, the net result, and the verdict — so the lineage of every idea is auditable, not anecdotal. The ledger currently holds **4 ideas, 5 dissected papers, 71 logged results and 87 lineage events**.

The ledger file itself is deliberately untracked (it is derived and rebuildable); the code that writes it, and the migrations that define its schema, are both here.

---

## How it works — a research loop with an honest "no"

The system is built around one principle: **a strategy is only as trustworthy as the verifier that can reject it.**

```
  Papers  ──▶  Hypothesis  ──▶  Backtest  ──▶  VERIFIER  ──▶  Verdict
 (ArXiv/    (tagged idea +   (real-tick MT5   (Strategy      (pass / kill,
  SSRN)      falsifier)       Strategy Tester)  Tester = the   logged to
                                                arbiter)       baysix.db)
```

- **Generate** — a paper-discovery pipeline (ArXiv/SSRN search → PDF acquire → Docling text-extraction → structured dissection) surfaces and distills relevant literature.
- **Validate** — ideas move through a 4-gate protocol (Premise → Edge & Survival → Robustness → Live), each gate code-enforced so an idea can't skip a step. A kill requires **two falsified hypotheses**, never a single bad t-stat.
- **Verify** — the **MetaTrader 5 Strategy Tester on real dukascopy ticks** is the ground-truth arbiter. A Python/SQL query is never accepted as a verdict — the look-ahead lesson above is *why*.
- **Record** — every result, gate, and kill is written through a typed data layer, enforced at the database by triggers that reject any write from an unarmed connection. The audit trail cannot be edited by hand.

---

## Tech stack

- **Python** (223 files tracked; 105 in the live tree, the rest archived on purpose) — research engine, data layer, backtest orchestration, `pytest` suites.
- **MQL5** (63 files) — MetaTrader 5 Expert Advisors: a single causal tick-accumulator engine with EMIT (read-only oracle) / TRADE / STUDY modes, versioned with git-sha provenance stamped on init.
- **ArcticDB** — canonical XAUUSD tick store (2016–2026), sorted + sealed to eliminate look-ahead at the data layer. Local-only; not in the repo.
- **SQLite** — one canonical ledger (`db/baysix.db`) covering ideas, papers, gates, results and lineage, defined by versioned migrations under `db/migrations/`.
- **Agentic workflow** — a CLI research agent (paper-find on one model, deep-dissect on another) with the operating protocol version-controlled as `CLAUDE.md`. Cross-session continuity runs through a structured handover system, so the agent resumes with prior decisions intact.

---

## Repo map — where to look

```
core/              ← the spine. Everything that runs.
  ├── gates/         4-gate protocol engine + idea_cli driver
  ├── lineage/       idea / result / agent-call / backlog ledgers
  ├── io/            tick store, paper fetch, PDF extraction, tester harness
  ├── infra/         DB guard, snapshots, output-path registry, provenance
  └── tests/         pytest suites
db/                ← baysix.db (untracked) + versioned migrations
platforms/         ← execution venues
  ├── mt5/           MQL5 Expert Advisors + Strategy Tester exports (the verifier) — the only
  │                  venue that ever produced a logged result
  ├── ninjatrader/   NT8 futures seam — reserved, never implemented
  └── ibkr/          IB gateway connection probes
research/          ← evidence only. Nothing here executes.
  ├── papers/        dissected literature
  ├── models/        archived idea lines, kept greppable and out of the live path
  └── brokers/       venue cost models (spread/commission specs)
docs/              ← design specs, plans, protocol notes
```

**Start in [`core/`](core/)** — that's the crown jewel. `research/` is the evidence room; archived model lines under `research/models/_archive/` keep their original imports deliberately broken so they can never be silently resurrected.

---

## Skills demonstrated

- Time-series & market-microstructure research on high-frequency (tick) data
- Rigorous backtest validation — walk-forward / out-of-sample discipline, look-ahead & leakage avoidance, cost-aware net results
- Python engineering: modular packages, a typed database access layer, test coverage
- SQL schema design for a research/experiment ledger, with integrity enforced by triggers rather than convention
- MQL5 systems programming: causal event-driven engine, deterministic tester fills, provenance/version control
- Reproducible research process with an auditable decision trail

---

## Status & honesty note

This was an **independent research program**, never a productized or profitable system, and it is now paused. No idea cleared Gate 2. Two earlier lines are documented dead-ends — killed or parked on the record above rather than quietly deleted.

The strategy-generation layer was torn down in August 2026 after review found it had never produced a measured result: ~2,300 lines of well-formed contracts, ledgers and adjudicators with no engine attached. That teardown is itself on the record, and the decision to rebuild rather than patch it is why this repository is paused rather than extended.

What did work is still here and still true: a sealed tick store, a causal MQL5 verifier, a gated protocol that an idea cannot skip a step in, and a ledger whose integrity is enforced by database triggers rather than good intentions.

The point of the repository is to demonstrate a **credible, falsifiable research process** — the ability to generate ideas, test them honestly against a tick-accurate simulator, and *reject* the ones that don't hold up. In a world where AI makes strategy *generation* nearly free, the scarce skill is *killing the fake ones*. That record is what this repo is, and it does not expire because development moved elsewhere.
