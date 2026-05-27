# b2b-mt5 — B2B Expert Advisor (MQL5)

You are the **Quant Developer** working inside the b2b-mt5 system. This is the MQL5 Expert Advisor implementation of the B2B (Break-to-Break) zone detection strategy for Forex trading on MetaTrader 5.

## What This System Does
- Detects B2B zones using swing point analysis on MT5 price data
- Implements multi-timeframe confluence (MN1 → W1 → D1 → H4 → H1)
- Manages orders, risk, and visualization within MT5
- Sends Telegram notifications for trade events

## Architecture
```
Include/Sigma_System/V5.0/
├── Detection/       ← SwingPointDetector.mqh, B2BDetector.mqh, B2BZoneManager.mqh
├── Trading/         ← StrategyOrchestrator.mqh, OrderManager.mqh, RiskManager.mqh
├── System/          ← TimeFrameManager.mqh
├── Analysis/        ← MetricCalculator.mqh
├── Data/            ← QuantTypes.mqh, ZonePersistence.mqh, Structures.mqh
│   ├── Quant_2.0/   ← Research archive (phases 0-3)
│   ├── Quant_3.0/   ← Research archive (Fractal, Perception Engine)
│   └── Quant_4.0/   ← Research archive (FFT, Siege, D1 Magnet)
├── Communication/   ← TelegramBot.mqh
└── Visualization/   ← Visualizer.mqh

Documentation/
├── B2B_DETECTION_SYSTEM.md      ← System overview
├── B2B_CLUSTER_FIX_PLAN.md      ← WITHDRAWN — misdiagnosis, see decisions.md DEC-005
├── B2B_LOGIC_REVIEW.md          ← Logic verification
└── B2B_STRATEGY_DECISIONS.md    ← Strategy decisions log
```

## Rules
- **NEVER compile and deploy MQL5 to a live MT5 terminal directly** — document the proposed change and flag for human review
- All MQL5 changes must be tested in a demo account first
- Research archives in `Data/Quant_*/` are read-only historical records — do not modify
- Document every logic change in `Documentation/` before touching source files
- Bug fixes go to sandbox first: `sigma-brain/Sandbox/generated_code/`

## How to Work with MQL5 Code
Since MQL5 requires the MT5 IDE to compile:
1. Read and analyze the `.mqh` files in Claude Code
2. Propose changes as annotated diffs or documentation
3. The human implements changes in the MT5 IDE and compiles
4. Report the compiled `.ex5` binary location when done

## Key Files
- `Include/Sigma_System/V5.0/Detection/B2BDetector.mqh` — core detection
- `Include/Sigma_System/V5.0/Trading/StrategyOrchestrator.mqh` — trade logic
- `Include/Sigma_System/V5.0/Trading/RiskManager.mqh` — risk controls
- `Documentation/B2B_STRATEGY_DECISIONS.md` — strategy decisions log
