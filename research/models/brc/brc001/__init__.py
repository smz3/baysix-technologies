"""
BRC-001 — Break · Retest · Continuation  (rebrand of the old "B2B").

A structural breakout/pullback continuation strategy, defined ONLY in observable,
testable price events (no "institutional / trapped trader" narrative):

    Break        -> a confirmed structural breakout  (STRUCT-001 rawbreakout)
    Retest       -> price pulls back and re-touches the broken level (L1)
    Continuation -> forward return past L1 in the break direction

Design rule: STRUCT-001 owns "Break" and is the SHARED primitive layer. BRC
*imports* struct (see _struct_on_path) — it never copies or forks the detector,
so there is exactly one source of truth for swings/breakouts.

Thesis under test (single-TF D1 atom first; no multi-TF russian-doll yet):
  H_base   : Break->Retest of L1 -> positive continuation, E[$/trade] > 0 net cost
  H_alt-1  : the retest reverts (fade-the-level / no memory)
  H_alt-2  : is the 2nd break load-bearing? (two-break zone vs single-break retest)

Modules:
  zones.py        -> two-barrier zone construction (L1/L2 geometry) on struct breaks
  retest.py       -> pullback re-touch detection (5-pointer P4)
  continuation.py -> forward-return labelling (5-pointer P5)
"""
