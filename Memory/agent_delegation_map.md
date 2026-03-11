# Agent Delegation Map
Last Updated: 2026-03-11

## Agent Roster

| Agent | File | Primary Domain | Context Window Impact |
|-------|------|---------------|----------------------|
| Chief of Staff | `CLAUDE.md` | Orchestration, synthesis | Main session |
| CIO | `.claude/agents/cio/AGENT.md` | Strategy, prioritization | Low (reads summaries) |
| Quant Researcher | `.claude/agents/quant-researcher/AGENT.md` | Research, hypothesis | Medium (reads papers) |
| Quant Developer | `.claude/agents/quant-developer/AGENT.md` | Code, backtests | High (reads full code) |
| Quant Trader | `.claude/agents/quant-trader/AGENT.md` | Signal monitoring | Low (reads logs only) |
| Risk Manager | `.claude/agents/risk-manager/AGENT.md` | Risk, drawdown, kill switch | Low (reads params + logs) |
| Memory Curator | `.claude/agents/memory-curator/AGENT.md` | Memory synthesis | Low (reads/writes memory) |

## Delegation Decision Tree

```
User Request
│
├── "What should we prioritize?" / "What's the strategy?"
│   └── → CIO
│
├── "Research...", "Why did...", "Analyze the data..."
│   └── → Quant Researcher
│       └── If needs new code → queue for Quant Developer
│
├── "Fix...", "Build...", "Run backtest...", "Implement..."
│   └── → Quant Developer
│       └── Risk check on any position/sizing change → Risk Manager first
│
├── "Check positions...", "Is the EA running...", "Status..."
│   └── → Quant Trader
│       └── If anomaly → escalate to Risk Manager
│
├── "What's our risk?", "Drawdown?", "Kill switch..."
│   └── → Risk Manager
│
├── "Remember this...", "Update memory...", "Save this insight..."
│   └── → Memory Curator
│
└── "Post to LinkedIn...", "Write a post..."
    └── → Use /push-linkedin skill
```

## Skills Registry

| Skill | Command | Delegates To | Location |
|-------|---------|--------------|----------|
| Run Backtest | `/run-backtest` | Quant Developer | `.claude/skills/run-backtest/` |
| Check MT5 Health | `/check-mt5-health` | Quant Trader | `.claude/skills/check-mt5-health/` |
| Update Memory | `/update-memory` | Memory Curator | `.claude/skills/update-memory/` |
| Push LinkedIn | `/push-linkedin` | (direct) | `.claude/skills/push-linkedin/` |

## OpenFang Integration (Future)
- When ready for 24/7 background agents, wire via: `Agents/hands_sandboxed/`
- Telegram alerts: OpenFang has 40 channel adapters ready
- Background crypto scanner: `Agents/hands_sandboxed/crypto_execution/`
