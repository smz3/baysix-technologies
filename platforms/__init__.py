"""Per-platform code. One subpackage per trading platform (mt5, ninjatrader, ibkr).

Task 360 (2026-08-16) settled the split: the SHARED truth layer lives in
core (gates, lineage, the baysix.db ledger); each platform keeps its
own machinery here. Nothing under platforms/ may become a second home for
protocol, gate or trial-counting logic — duplicating that is what creates two
answers to "how much have we tested".
"""
