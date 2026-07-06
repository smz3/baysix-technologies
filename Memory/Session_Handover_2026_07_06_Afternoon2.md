# Handover — July 6, 2026 Afternoon2

## State
- **DISCUSS + one exploratory screen + one PROCESS FIX. No result logged (all mid, exploratory).**
- **Rule 16 SHIPPED** ([CLAUDE.md](../CLAUDE.md) rule 16 + memory [[mid-price-no-caveat-rule]], committed+pushed): mid-price is the discovery default, **NEVER caveat it** during logic work; cost enters ONCE at G2. Banned by Syafiq as recurring session-to-session friction.
- **"What is our CF edge?" answered honestly:** only **cf3** is net-positive on the MT5 tester (result_id 32 = +$304 / 373 trades, 8yr IS); cf0/cf2 lose. It is IS-only, thin, un-OOS'd, no t-stat stored (trades in Parquet post data-plane split).
- **cf3 survivorship screen run** (run_19, exploratory, mid) — geometry leans survivorship; not conclusive (proxy discredited). See ## Live-Threads. New task 242 opened.

## Next
1. **(task 242, P1)** cf3 survivorship decomposition: pull result_id-32 MT5 tester trades, split each winner's R into **pre-entry (banked before CF) vs post-entry (forward)** — settles edge-vs-survivorship on arbiter fills. Gates 238 + ML.
2. **Fork on 242:** real edge → task 238 (OOS crack of cf3·k0.5·RR2.0); survivorship → pivot entry thesis toward the CONTEXT router (horizon), not a CF trigger.
3. **(task 241, P1 — carried)** Sorter + smart-exit design session (horizon buckets + at-wall LOCATION detector + exit taxonomy E1–E4). DISCUSS-first.

## Blockers
- **None hard.** Task 242 is a data-pull + decomposition on existing tester output; no build. Which-VR selector (240) + bucket mapping (241) remain Syafiq's design calls.

## Why
- **Mid-caveat was banned because it recurred every session** — it lived only in-session, so each cold start re-derived the "careful, that's mid" caution and it *felt* like cost was gate-keeping the logic. Fix = codify in the two files loaded at startup (CLAUDE.md rule + MEMORY.md index) so it's settled permanently, per [[enforcement_code_not_prose]]. Mid-price cost-free IS the free logic playground; cost is the final exam at G2, an outcome not a hedge.
- **at-wall LOCATION detector proposal (task 241):** treat "at-wall" as a **continuous `room_R = dist(CMP→nearest opposing wall ahead) / dist(CMP→E1 stop)`**, not a boolean. Walls = existing opposing VR/PBO levels in the live chain (no new calc). Buckets (proposed, to be MEASURED not guessed): at-wall `< ~1 risk-unit` / mid `~1–2.5 risk-units` / open `≥ ~2.5 risk-units`. Does double duty: entry guard (don't open into a wall) + E4 TP trigger, and it **caps horizon** (a swing setup with a wall ~half a risk-unit ahead is really a scalp). Open call: opposing-walls-only vs also same-dir magnets.

## Ruled-Out
- **ML on FOB now = premature (do NOT start).** Binding constraint is sample size + no confirmed raw edge, not model power. No edge to condition on (cf3 un-OOS'd), ~low-hundreds H4 trades, near-coin-flip signal → overfit suicide. ML's legit role = CONTEXT/regime router + a *regularized logistic* enriching the analytic continuation-hazard curve, AFTER a deterministic OOS edge exists. Deep/Kronos = B2B zone-survival prior, do NOT cross into FOB.
- **Cost was NOT the ORB killer** (corrected on the record): ORB-001 died from **unsorted-tick look-ahead** (edge fake at zero cost, result_id 122 [[orb_unsorted_tick_lookahead]]); ORB-004 at Gate-3 robustness. Don't blame cost for ORB/BRC kills without checking the record — folded into rule 16.

## Live-Threads
- **cf3 survivorship screen (run_19, EXPLORATORY, mid — source [data/fob_payload/run_19/](../data/fob_payload/)):** two signals, neither conclusive:
  - **Geometry (trustworthy, pure arithmetic):** `pre_R` (PBO→CF travel ÷ risk-band) **rises monotonically with CF depth** — H4 median cf1≈2.0 → cf3≈2.3 → cf5≈2.7. You enter cf3 ~2.3 risk-units *deep into a move that already happened* = the survivorship setup.
  - **Forward proxy (DISCREDITED — do not trust sign):** `realized_r` **decays with depth** (all-TF: cf1 +0.109 → cf3 +0.089 → cf5 +0.029; H4 negative everywhere) → survivorship-consistent, BUT this is the k0-fixed-barrier mid proxy that contradicts the tester's cf3=+$304 (result_id 32). Shape only, never level. [data/fob_payload/run_19/](../data/fob_payload/) exploratory.
  - **Clean close is BLOCKED on `mfe_r/mae_r` = NULL** (task 202 never built) → hence task 242 decomposes the real MT5 fills instead.
- **cf3 candidate `L1·cf3·k0.5·RR2.0` (result_id 32) still un-OOS'd** — task 238 deliberately untouched until 242 confirms the edge is real (don't spend the hold-out on a possible mirage).
- **task 202 (mfe_r/mae_r excursion) is the clean-measurement unblock** — if 242's MT5 decomposition is fiddly, building 202 gives the cost-free forward measure to re-run the survivorship split properly.
