# Handover — June 25, 2026 Morning

## State
- **NEW: FOB-001 idea opened + MT5 detection foundation built/validated.** First Opposite Breakout; sibling of BRC under STRUCT-001 (paper_id 31 = Syafiq's FOB manual). G1 open. See [[fob001_foundation]].
- New `fob_system` namespace: [fob_types.mqh](mt5/Include/fob_system/fob_types.mqh) · [fob_sequence.mqh](mt5/Include/fob_system/fob_sequence.mqh) (cross-TF classifier) · [fob_csv.mqh](mt5/Include/fob_system/fob_csv.mqh) · [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh) · [fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5). Reuses STRUCT-001 `brc_swings`+`brc_breakouts`.
- **TF rule:** setup TF n → VR & CF = n−1; HRCF (high-risk CF) = n−2 (skip). Supersede: new break on TF n = new PBO, resets its VR/CF/HRCF. Colours PBO blue / VR purple / HRCF orange / CF green.
- **Works:** compiles 0 err (headless); deployed via fob_system junctions to JM terminal E7DB; smoke (XAUUSD.s May'26, open-prices) = 5930 events; MN1 PBO(BUY)→VR(W1 SELL)→CF(W1 BUY) chain hand-verified. Logged strategy_log log_id 68; task 153 in_progress.
- **Not yet done:** drawings never eyeballed (headless can't render). Syafiq wants adjustments to the visuals AND the visuals logic (specifics not yet given — session ended at context wall).
- House-cleaning: parked 6 stranded BRC tasks (126,129,130,133,141,144); dropped B2B/Sigma revival (149,150,151) + FOB-figures (152); task 135 headless tester FIXED ([[brc_headless_tester_fires]]).

## Next
1. **Eyeball FOB visuals** (task 154): visual-mode tester run — `fob_baysix` on M5 chart, `InpVisualize=true`, Visual Mode (NOT open-prices). Then get Syafiq's specific visual + visual-logic change requests and apply to [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh) (+ classifier if logic changes).
2. After visuals locked: validate FOB labels vs known manual examples; then build a Python ingester for `Common/Files/FOB/fob_events_*.csv` + the edge test (does VR+CF-conditioned continuation beat BRC's null?).

## Blockers
None. FOB foundation compiles + runs; the visual adjustments need Syafiq's specifics (deferred to fresh session — context wall hit).
