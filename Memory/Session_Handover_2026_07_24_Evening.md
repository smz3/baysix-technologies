# Handover — July 24, 2026 Evening

## State
- **Non-research session** — career/cash-flow strategy + public-repo hygiene. **Zero FOB runs; no new results logged.** DB result set unchanged (latest remains result_id 60).
- **Repo is now PUBLIC** (github.com/smz3/baysix-technologies, 585 tracked files).
- **Security audit: CLEAN.** No API keys/passwords/tokens in tracked content; no `.env`/`.pem`/`.key` ever committed (only `sigma-research/.env.example`); `.gitignore` airtight. The two `hooks-config*.json` hits are boolean toggles only.
- **Aspirational framing scrubbed + pushed** (commit `c02ddd9`, merge `00d670f`). Firm-name and pod-shop references now return zero hits on HEAD.
- **`Memory/` → `memory/` case-rename completed** in the same commit — GitHub no longer shows duplicate folders.
- **A GitHub web edit by Syafiq collided with the local scrub** (remote `b3ba06f` "Update CLAUDE.md with new project focus"). Merged, conflict resolved by hand, pushed.
- **EA untouched: still v1.41.0, git `54b2b97` lineage, clean tree.** [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5).
- **No README exists** — the single biggest gap now that the repo is public.
- Outreach sent: LinkedIn Premium InMail to Twistcode CEO Nurazam Malim re: joining Okane. Awaiting reply (memory: `twistcode_okane_outreach`).

## Next
1. **(task 272, P1)** Write the public-repo **README** — the recruiter-facing front door. Frame as *independent quant research with a falsification record*.
2. **(task 270, P1)** Entry-mechanic A/B at H4-CF3: `InpEntryMode` CF_MARKET vs CF_L1_LIMIT off the cf3 preset. **Unchanged and still the live research task** — carried untouched from 2026-07-10.
3. **(task 273, P2)** MQL5 freelance profile pitch — differentiated positioning, low-bid niches only.

## Blockers
- **Tasks 202, 260, 240, 245, 262 unchanged** — still no valid excursion measure (task 202 unblocks them).
- Headless tester still requires `terminal64.exe` closed ([[brc_headless_tester_fires]]).
- Task 272 (README) is not blocked; task 270 is not blocked by 202.

## Why
- **The session opened as a catch-up and became a cash-flow reckoning.** Syafiq is broke with no income. The honest call made and accepted: **FOB cannot pay him** — min-lot DD floor at a small account is structural ([[orb_dd_structural_floor]]) — so it was explicitly relieved of that job. FOB is *job evidence*, not income. That reframe is the session's real output.
- **Two funnels, deliberately separated:** (A) cash in weeks = MQL5 freelance; (B) job in months = applications + the Baysix research record. They had been fused, which made every FOB session feel like it should pay rent.
- **Market survey done (live, 2026-07-24), and the finding was the bid distribution, not the budget.** Generic MT5 EA jobs draw 40–82 bids; niche jobs (Sierra Chart ACSIL, NinjaTrader, XAUUSD-specific, Python-bridge) draw 9–29. Competing on "professional EA developer" is unwinnable; the differentiated pitch is the whole play. Marketplace reality: 50–200 USD/job until reviews accumulate — this **stabilises, it does not rescue**.
- **Jobs: Malaysia is thin and contaminated** (most "quant research" listings are market/consumer research — DKSH, IQVIA, Mintel; genuine finance names are JPMorgan/S&P Global/CFRA only). **Singapore is ~25× deeper** and remote-friendly. Their stated requirement — *"market microstructure, limit order books, high-frequency data"* — is exactly what FOB already is, just filed under the wrong name.
- **Loop vs graph engineering, researched:** loop = trigger → model picks next action → **verifier** → feedback; graph = specialist nodes + edges + shared state, for breadth. Verdict: Baysix already has 4/5 of the loop (MT5 tester = verifier, `run_tracked` sentinel = stop condition, CLAUDE.md = anchor, research.db = state). **The missing piece is the "no" being executable rather than prose** — pass/fail rules currently live in conversation. Named hazard: an auto-sweeping loop *is* multiplicity mining (task 271's exact concern).
- **Disclosure policy decided and logged** (`log_agent` call_id 98, human decision, FOB-001). Scrub the *framing*, keep the *parameters*: ~100 technical `$50` references (equity sims, min-lot DD floor, broker sizing YAML, EA lot inputs) were **retained deliberately** — they are real survival/sizing inputs, scrubbing them would break the analyses, and position-sizing realism reads as rigor to a quant reader.
- **History rewrite declined by Syafiq** — scrub-forward only. Old commits still contain the removed lines; accepted as low-risk.
- **Handovers stay tracked and public** — Syafiq chose per-line scrubbing over untracking the folder. **Consequence to carry: every future handover is world-readable at write time.** Write them factual, not personal.

## Ruled-Out
- **"Research firm publishing market outlook" — REJECTED before any build.** Unfalsifiable, crowded, n≈12 calls/year is unscoreable, and it reads as commentary rather than capability. The reframe that survived (not yet built): publish a *scored process* — dated hypothesis + explicit falsifier + horizon + auto-marked outcome. Parked, not dead.
- **Asking for a job in a LinkedIn connection request — dropped.** Connection notes cap at 300 chars and a cold transactional ask lowers accept rate. Moot in the end: Premium InMail was available and used.
- **Untracking the whole `Memory/` folder — considered and declined by Syafiq** (option was offered explicitly). Chose per-line scrubbing to preserve the visible research-process trail.
- **Git history rewrite / force-push — declined by Syafiq.** Do not re-propose unless he raises it.
- **Scrubbing technical `$50` references — actively argued against and not done.** Do not "finish the job" in a later session; this was a deliberate call, not an oversight.
- **Graph engineering as the next thing to build — rejected for now.** Baysix work is sequential and single-threaded; graph pays off on breadth (audits, sweeps). Loop-hardening comes first.

## Live-Threads
- **The Twistcode/Okane reply is the live external thread.** The wedge identified: their marketing claims 80–90% accuracy while their own product page says "at least 50% and above" — they are engineering-strong, trading-light. **When he replies, the "what exactly do you do?" moment is where the killed-strategy record speaks.** If he opens but doesn't reply in ~4–5 days, send a one-line nudge. Caveat held: ~6-person shop, may have no open req, and Okane may not be an active priority.
- **`verdict.py` — proposed, not built.** A pre-registered rule in → tester ledger → `PASS/FAIL/INCONCLUSIVE` + auto `log_result` + trial-count increment. This is the executable "no" that would harden the loop, and it would also discharge task 271's multiplicity concern mechanically. Not yet a task; Syafiq has not committed to it.
- **The "$50 rapid-scalp mandate" is now doubly stale** (carried since 2026-07-09, still unscoped) — and this session explicitly de-prioritised FOB as an income source, which weakens its original motivation. Someone should decide whether it is still wanted at all.
- **A ledger-filename audit is still overdue** (carried, unchanged): `InpExitOnCfInval`, `InpExitOnOppPbo`, `InpTrailStop`, `InpTrailActivateR/DistR`, `InpSessionFilter`, `InpDirFilterTf` are absent from ledger filenames — each an in-place-overwrite trap for the next A/B. Still not a task.
- **Doc landmines, still not fixed** (carried, unchanged): [storyline-alignment findings](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) §2 is void with no banner; [v0.2 entry-logic spec §6](../docs/specs/2026-07-02_fob_sequence_storyline_entry_logic_v0.2.md) points at retired `fob_trader.mq5`. **Now public** — these are visible to anyone reading the repo, which raises their priority.
- **GitHub web edits collide with local work.** This session lost a push to it. Either edit locally, or ping Claude to pull first.
- **The H4-CF3 case is unchanged and still thin** (carried): +$1.0349/tr at t +1.68, n=373 (result_id 55), mean carried by ~3 trades; 4 H4 cells tested with multiplicity never counted (task 271).
