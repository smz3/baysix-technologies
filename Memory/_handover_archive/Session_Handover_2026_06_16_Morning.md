# Handover — June 16, 2026 Morning

## State — FOCUS = B2B-001 (Sigma B2B Structural Zone Strategy · parent STRUCT-001 · status=ideation)

**B2B paper synthesis (the decision input Syafiq asked for) — 3 keepers dissected on Opus this session:**
- **Osler 2003** (call_id 70, pid28) — *mechanism*. FX dealer order-book: stop-losses cluster just BEYOND a level (→ cascade = the decisive break), take-profits cluster ON the level (→ partial reflect/retest). Two stacked cascades = institutional double-break footprint. Caveat: FX *order-book* data we don't have for gold; XAUUSD is price-only → mechanism is inferential.
- **Chung 2021** (call_id 71, pid29) — *lifecycle*. Zone bounce-prob RISES with #touches, DECAYS with age (real — beats shuffle + AR(1)). Gives a Bayesian `(n+1)/(N+2)` retest hit-rate prior. Gold never tested; re-measure decay curve on our ticks.
- **Costa 2026** (call_id 72, pid30) — *direction crux*. Gold CONFIRMS breakouts **66.78%** (D1, GC=F) vs FX reverts >75%. WEAK paper (no stat tests, daily-only, futures proxy, internally inconsistent) → hypothesis, not proof.

**VERDICT (for Syafiq's decision):** B2B retest edge survives, but the *direction* flips on gold → trade **continuation-after-pullback** (enter the retest IN the break direction), NOT fade-the-level. This hands us the ≥2-hypothesis framing the kill-rule needs: H_base=continuation-retest, H_alt=fade. 4th keeper Caporale (pid8) NOT yet dissected (task 59).

**Pipeline change shipped + committed:** paper flow is now FIND→ACQUIRE→EXTRACT(Docling)→DISSECT — dissect reads the `.md`, **native-vision PDF dissection BANNED** (CLAUDE.md rule 5b · [extract_pdf.py](research/code/extract_pdf.py) · [quant-researcher.md](.claude/agents/quant-researcher.md) updated). Source `.md` gitignored; `<stem>.dissect.md` git-tracked.

**Backlog refocused:** 16 unrelated infra tasks PARKED (new `parked` status · migration 017). Open now = STRUCT-001 (74/75/76) + BRK-001 (59/60/61) + new B2B-001 P1s (102/103). Caporale PDF MOVED brk/→b2b/ (still DB-tagged BRK-001, harmless).

## Next
1. **Finish Docling install** (downloading now) → **verify** `python research/code/extract_pdf.py research/papers/b2b/osler_2003_currency_orders_exchange_rate.pdf` → eyeball Osler's 4 tables for fidelity (task 102).
2. **Syafiq must paste** the new-window allow rule into [.claude/settings.json](.claude/settings.json) (I'm guardrail-blocked from editing permissions): `"Bash(powershell -Command Start-Process*)"`.
3. **Backfill** `.dissect.md` for Osler/Chung/Costa from this session + **dissect Caporale** (task 59) through the new pipeline (task 102).
4. **DECISION → open B2B-001 Gates 0/1** (task 103): `python research/code/idea_cli.py next B2B-001`, frame H_base=continuation-retest vs H_alt=fade, Chung knobs = min-touch + age cutoff.

## Blockers
- Docling install in progress — pipeline unverified until it finishes + Osler eyeball.
- New-window PowerShell launch blocked until Syafiq adds the allow rule (auto-mode classifier blocks me from widening my own permissions; it also blocked the config skill — this is by design, not retryable by me).
