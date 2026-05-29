# Handover — May 29, 2026 Night2

## State
HMM-001 (XAUUSD D1) at Gate 4, passed 0–4. **Lookback RESOLVED → W=20 frozen.** Swept {10,20,40,60} out-of-fold via [gate4_window_sweep.py](research/models/hmm/gate4_window_sweep.py): AUC W10=0.479, W20=0.606, W40=0.659, W60=0.593. W40 best on point estimate but [gate4_window_bootstrap.py](research/models/hmm/gate4_window_bootstrap.py) (10k paired) gave ΔAUC=+0.053, 95%CI[−0.014,+0.119], p=0.063 — doesn't clear 95%, so per pre-set rule freeze W=20 (best early-warning t=+3.63, only +BSS, conservative for one-shot OOS). Results #19–27. Calibration decided: **Platt-adaptive** (Z=0.59 honest vs iso Z=4.27 under-warns — calibration > ranking for a risk filter). Multi-timeframe (W1/MN1 stacking, or down to H4/H1 + confluence) discussed and **PARKED as future HMM-002** — don't reopen Gate 4 before OOS.

## Next
1. **Freeze the full HMM-001 config**: window=20, cuts +0.85σ/−0.32σ, Gaussian emission, calibration=Platt-adaptive. Write it down as the locked spec.
2. **Count final n_trials and deflate** before OOS. Window question alone spent 5 (4 windows + bootstrap); add prior Gate-4 attempts. See [hmm001_open_variables.md](../.claude/projects/c--Users-User-Desktop-baysix-technologies/memory/hmm001_open_variables.md) item 6.
3. **Gate 6 — one-shot OOS** on sealed 2024-05-02+ data. Protocol rule 6: single shot, no peeking, no re-runs.

## Blockers
None. NIG emission (open-var #5) still untested but likely doesn't move the deliverable (calibration is a separate post-layer) — decide whether to skip before freezing.
