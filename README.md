# Baysix Technologies

**An autonomous research loop for systematic strategy discovery (currently XAUUSD/gold) — built to *falsify* trading ideas, not just showcase winners.**

![Python](https://img.shields.io/badge/Python-201%20files-3776AB?logo=python&logoColor=white)
![MQL5](https://img.shields.io/badge/MQL5-63%20files-1E88E5)
![SQLite](https://img.shields.io/badge/research.db-SQLite-003B57?logo=sqlite&logoColor=white)
![ArcticDB](https://img.shields.io/badge/tick%20store-511M%20ticks-2E7D32)

This is a working, single-operator quant-research program: a disciplined pipeline that turns published ideas into testable hypotheses, runs them against a tick-accurate market simulator, and **kills the ones that don't survive** — with the reasons recorded. The rare thing on display here isn't a profitable strategy; it's a documented record of *how ideas were killed*, which is the harder and scarcer skill.

---

## Why this repo is different: the falsification record

Most trading portfolios show only what worked. This one shows the graveyard, because in research the discipline to reject a false edge matters more than the luck of finding a real one.

| Idea | Status | Why |
|------|--------|-----|
| Opening-range breakout timing | ❌ **Killed** | An apparent edge turned out to be **look-ahead bias**: ticks weren't time-sorted, so "first breakout" was chosen with future information. On chronologically-sorted ticks, the edge vanished. |
| Support/resistance zone reaction | ⏸️ **Parked** | Entry-fade and entry-continuation produced statistically indistinguishable expectancy → **no directional edge**. Parked rather than force-fit. |
| Multi-timeframe breakout-reaction model | 🔬 **Active** | A cross-timeframe *reaction* model (not a win-rate classifier). Under validation on real ticks; treated as a research artifact, not a money machine. |

Every one of these decisions is logged in a SQLite research ledger (`research/db/research.db`) with the hypothesis, the net result, and the verdict — so the lineage of every idea is auditable, not anecdotal.

---

## How it works — a research loop with an honest "no"

The system is built around one principle: **a strategy is only as trustworthy as the verifier that can reject it.**

```
  Papers  ──▶  Hypothesis  ──▶  Backtest  ──▶  VERIFIER  ──▶  Verdict
 (ArXiv/    (tagged idea +   (real-tick MT5   (Strategy      (pass / kill,
  SSRN)      falsifier)       Strategy Tester)  Tester = the   logged to
                                                arbiter)       research.db)
```

- **Generate** — a paper-discovery pipeline (ArXiv/SSRN search → PDF acquire → Docling text-extraction → structured dissection) surfaces and distills relevant literature.
- **Validate** — ideas move through a staged protocol of gates (Premise → Edge & Survival → Robustness → Live), each gate code-enforced so an idea can't skip a step.
- **Verify** — the **MetaTrader 5 Strategy Tester on real dukascopy ticks (2016→2026)** is the ground-truth arbiter. A Python/SQL query is never accepted as a verdict — the look-ahead lesson above is *why*.
- **Record** — every result, gate, and kill is written through a typed data layer (never by hand), giving a tamper-resistant audit trail of the whole research history.

---

## Tech stack

- **Python** (201 files) — research engine, data layer, backtest orchestration, `pytest` suites.
- **MQL5** (63 files) — MetaTrader 5 Expert Advisors: a single causal tick-accumulator engine with EMIT (read-only oracle) / TRADE / STUDY modes, versioned with git-sha provenance stamped on init.
- **ArcticDB** — canonical tick store: **511M XAUUSD ticks (2016–2026), sorted + sealed** to eliminate look-ahead at the data layer.
- **SQLite** — two-database design: a research ledger (ideas, papers, gates, results, lineage) and a live-deployment twin.
- **Streamlit** — research dashboard for exploring runs and results.
- **Agentic workflow** — a CLI research agent (paper-find on one model, deep-dissect on another) with the operating protocol version-controlled as `CLAUDE.md`. Cross-session continuity is maintained through a structured **handover / memory file system**, so the agent resumes each session with full research state and prior decisions intact.

---

## Repo map — where to look

```
research/          ← the core. Python research engine, gates, DB layer, models, tests
  ├── code/          shared DB + IO layer (gates · lineage · io · infra)
  ├── models/        one folder per idea (active line + retired/archived lines)
  ├── db/            SQLite research + execution databases
  ├── dashboard/     Streamlit research dashboard
  └── tests/         pytest suites
mt5/               ← MQL5 Expert Advisors + Strategy Tester exports (the verifier)
b2b/               ← earlier zone-detection engine (Python + docs)
data/arctic/       ← 511M-tick ArcticDB store (read-only interface)
docs/              ← design specs, reference schemas, protocols
brokers/           ← venue cost models (spread/commission specs)
```

**Start in [`research/`](research/)** — that's the crown jewel.

---

## Skills demonstrated

- Time-series & market-microstructure research on high-frequency (tick) data
- Rigorous backtest validation — walk-forward / out-of-sample discipline, look-ahead & leakage avoidance, cost-aware net results
- Python engineering: modular packages, a typed database access layer, test coverage
- SQL schema design for a research/experiment ledger
- MQL5 systems programming: causal event-driven engine, deterministic tester fills, provenance/version control
- Reproducible research process with an auditable decision trail

---

## Status & honesty note

This is an **active, independent research program**, not a productized or profitable system. One research line is under active validation; two earlier lines are documented dead-ends — killed or parked on the record above, not deleted. The point of the repository is to demonstrate a **credible, falsifiable research process** — the ability to generate ideas, test them honestly against a tick-accurate simulator, and *reject* the ones that don't hold up. In a world where AI makes strategy *generation* nearly free, the scarce skill is *killing the fake ones*. That record is what this repo is.
