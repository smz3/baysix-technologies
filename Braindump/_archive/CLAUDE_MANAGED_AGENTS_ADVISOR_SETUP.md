# Claude Managed Agents & Advisor Tool Tutorial

## Overview

Anthropic released two powerful agent features:
1. **Claude Managed Agents** — pre-built agent harness in managed cloud infrastructure
2. **Advisor Tool** — pair a fast executor model with a smarter advisor for strategic guidance

This doc covers installation, usage, cost analysis, and free alternatives for sigma-brain.

---

## Part 1: Claude Managed Agents (Long-Running Agent Infrastructure)

### What It Is

A **managed, cloud-hosted agent runtime** where Claude runs autonomously with:
- File I/O (read, write, edit, glob, grep)
- Bash execution
- Web search and fetch
- MCP server connections
- Stateful sessions (multi-turn persistence)

No more building your own agent loop—Anthropic handles the infrastructure, tool sandboxing, and SSE streaming.

### Installation & Setup

#### 1. Authentication
```bash
# Install/upgrade Anthropic SDK
pip install -U anthropic

# Set your API key
export ANTHROPIC_API_KEY="sk-..."
```

#### 2. Create an Agent (one-time)

Define the agent's capabilities, system prompt, and tools:

```python
from anthropic import Anthropic

client = Anthropic(api_key="your_api_key")

# Define an agent (create once, reuse by ID)
agent_response = client.beta.agents.create(
    model="claude-opus-4-6",
    name="QuantResearchAgent",
    description="Autonomous quantitative research and backtesting agent",
    system_prompt="""You are a quantitative researcher for a hedge fund.
Your role:
1. Analyze trading strategies from PRDs and backtest specifications
2. Run backtests using local tools
3. Generate performance reports
4. Recommend alpha signals

Use your tools autonomously to fetch data, run analyses, and summarize findings.
""",
    tools=[
        {"type": "file_operations"},  # read, write, edit files
        {"type": "bash"},              # run shell commands
        {"type": "web_search"},        # search the web
        {"type": "mcp_server", "name": "qdrant_mcp"}  # custom MCP server
    ]
)

agent_id = agent_response.id
print(f"Agent created: {agent_id}")
```

#### 3. Create an Environment (container config)

Define pre-installed packages, network rules, mounted files:

```python
env_response = client.beta.environments.create(
    name="QuantEnv",
    docker_image="ubuntu:22.04",
    packages={
        "python": ["3.11"],
        "apt": ["wget", "curl"],
    },
    installed_packages=[
        "pandas==2.2.0",
        "numpy==1.24.0",
        "backtrader==1.9.94.123",  # your backtesting framework
        "requests",
        "anthropic"
    ],
    network_access=True  # allow outbound HTTP/HTTPS
)

env_id = env_response.id
```

#### 4. Start a Session (agent instance)

Create a session to run the agent on a specific task:

```python
session_response = client.beta.sessions.create(
    agent_id=agent_id,
    environment_id=env_id,
    task="Backtest the SAMTC Phase 13A strategy (OOS validation) on 2024-2025 data"
)

session_id = session_response.id
print(f"Session created: {session_id}")
```

#### 5. Stream Agent Output (async communication)

The agent runs autonomously; you stream events back:

```python
# Stream the agent's execution
with client.beta.sessions.stream(
    session_id=session_id,
    event_handler=lambda event: print(f"Event: {event.type} - {event.data}")
) as stream:
    for event in stream:
        if event.type == "tool_use":
            print(f"Tool: {event.name} | Input: {event.input}")
        elif event.type == "tool_result":
            print(f"Result: {event.content}")
        elif event.type == "message":
            print(f"Agent: {event.text}")
```

#### 6. Steer Mid-Execution (optional)

Send follow-up messages to guide the agent:

```python
# Agent found an issue; ask for deeper investigation
client.beta.sessions.send_message(
    session_id=session_id,
    content="The Sharpe ratio dropped in Q4 2024. Isolate the reason—is it drawdown duration or volatility spike?"
)
```

---

## Part 2: Advisor Tool (Faster Executor + Smarter Advisor)

### What It Is

A **cost-optimization pattern** where:
- A **fast, cheap model** (Haiku, Sonnet) executes most work
- A **powerful model** (Opus) is called mid-generation for strategic guidance
- Advisor reads the full transcript and returns advice; executor continues

**Use case:** You get Opus-quality output at ~Sonnet cost on long-horizon tasks.

### Setup & Usage

#### 1. Define the Advisor Tool

Add it to your tools array:

```python
from anthropic import Anthropic

client = Anthropic()

tools = [
    {
        "type": "advisor_20260301",  # beta header required
        "name": "advisor",
        "model": "claude-opus-4-6",  # must be >= executor model
        "caching": {"type": "ephemeral", "ttl": "5m"},  # reuse advisor plan across calls
        "max_uses": 3  # cap advisor calls per request
    }
]
```

#### 2. Executor Model Calls Advisor Automatically

The executor (Sonnet) decides when to consult the advisor:

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-6",  # fast executor
    max_tokens=4096,
    betas=["advisor-tool-2026-03-01"],  # required beta header
    tools=tools,
    messages=[
        {
            "role": "user",
            "content": """Build a complete B2B zone detection system for MT5.
Requirements:
- Identify support/resistance clusters
- Measure zone strength (touches, time-at-level)
- Generate entry/exit signals
- Handle live market data updates

Provide a complete, production-ready implementation."""
        }
    ]
)

print(response.content)
```

#### 3. What Happens

1. Sonnet starts generating code
2. Sonnet realizes it needs a plan → calls advisor
3. Opus reads Sonnet's work so far, produces a strategic plan (400–700 tokens)
4. Sonnet resumes, informed by Opus's plan
5. Result streams back with both layers visible

**Response structure:**
```json
{
  "content": [
    {"type": "text", "text": "Let me ask the advisor for a strategic plan..."},
    {"type": "server_tool_use", "name": "advisor", "input": {}},
    {"type": "advisor_tool_result", "content": {"type": "advisor_result", "text": "Use a sliding-window approach with exponential weighting..."}},
    {"type": "text", "text": "Here's the implementation based on that guidance..."}
  ]
}
```

#### 4. Multi-Turn Conversation

Pass the full response (including advisor results) back on the next turn:

```python
messages = [
    {"role": "user", "content": "Build B2B zone detection..."},
    {"role": "assistant", "content": response.content},  # ← include advisor_tool_result
    {"role": "user", "content": "Now add live market update handling"}
]

response2 = client.beta.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    betas=["advisor-tool-2026-03-01"],
    tools=tools,  # ← must include advisor tool even on follow-ups
    messages=messages
)
```

---

## Part 3: Practical Integration for Sigma-Brain

### Use Case 1: Autonomous Backtest Runner (Managed Agents)

```python
# Run 24/7 backtests without you babysitting
session = client.beta.sessions.create(
    agent_id="sigma_backtest_agent",
    environment_id="quant_env",
    task="Run Test 13A (SAMTC OOS) on fresh 2025 data. Compare Sharpe/Payoff/Skew to baseline."
)

# Check status anytime
status = client.beta.sessions.retrieve(session.id)
print(f"Status: {status.status}")  # running, completed, failed
```

### Use Case 2: Code Generation with Advisor (Cost Optimization)

```python
# Generate production B2B logic at Sonnet cost + Opus quality
response = client.beta.messages.create(
    model="claude-sonnet-4-6",
    betas=["advisor-tool-2026-03-01"],
    tools=[{"type": "advisor_20260301", "name": "advisor", "model": "claude-opus-4-6"}],
    messages=[{
        "role": "user",
        "content": "Build a Cython-compiled B2B zone detector that handles 500 MT5 symbols in <2ms"
    }]
)
# Sonnet + Opus guidance saves ~40% vs Opus-only
```

### Use Case 3: Session-Based Research Pipeline

```python
# Long-running research task
env = client.beta.environments.create(
    name="ResearchEnv",
    installed_packages=["pandas", "numpy", "scipy", "scikit-learn", "matplotlib"]
)

session = client.beta.sessions.create(
    agent_id="sigma_research_agent",
    environment_id=env.id,
    task="Analyze correlation between NASA EONET risk events and crypto volatility spikes"
)

# Stream results in real-time
for event in client.beta.sessions.stream(session.id):
    if event.type == "message":
        print(f"Research finding: {event.text}")
```

---

## Part 4: Cost Analysis & Free Alternatives

### Anthropic Managed Agents Pricing

- Pay per **session minute** (~$0.10–0.50/min depending on model)
- Tool execution is free (Bash, file ops)
- MCP servers billed separately per call

**Monthly cost estimate:**
- 8hr/day backtesting: ~$180–240/mo
- Full-time agent loop: ~$500+/mo

### Advisor Tool Pricing

- Advisor sub-inference billed at **Opus rates** (~$15/MTok input, $60/MTok output)
- Executor output billed at **Sonnet rates** (~$3/MTok input, $15/MTok output)
- Typical advisor call: 1,400–1,800 tokens total
  - **Cost:** ~$0.02–0.03 per advisor call
  - **Savings:** Use Sonnet executor instead of Opus-only, save ~75% on non-advisor turns

**When to enable advisor caching:**
- 1–2 advisor calls per conversation: **disable** caching (cache write costs more than reads save)
- 3+ advisor calls per conversation: **enable** caching (reads save 90% after first call)

---

## FREE ALTERNATIVE: Local Agent Loop

Run agents **locally** on your machine using Gemma4-baysix (already running via Ollama) as the brain.

```python
#!/usr/bin/env python3
"""Local agent loop — zero cloud cost."""

import json
import subprocess
import sys
from pathlib import Path

def call_gemma4(prompt: str, system: str = "") -> str:
    """Call gemma4-baysix locally via Ollama."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    cmd = [
        "ollama", "run", "gemma4-baysix",
        json.dumps({"messages": messages, "temperature": 1.0, "top_p": 0.95})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()

class LocalAgent:
    """Agentic loop that runs locally."""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.history = []
    
    def run(self, task: str, max_iterations: int = 10):
        """Execute the task autonomously."""
        print(f"\n🤖 {self.name} starting: {task}\n")
        
        self.history.append({"role": "user", "content": task})
        
        for i in range(max_iterations):
            # Call Gemma4
            prompt = "\n".join([
                f"{m['role'].upper()}: {m['content'][:500]}" 
                for m in self.history
            ])
            response = call_gemma4(prompt, self.system_prompt)
            
            self.history.append({"role": "assistant", "content": response})
            
            # Parse tool calls (if agent decides to use bash, file ops, etc)
            if "<RUN_BASH>" in response:
                cmd = response.split("<RUN_BASH>")[1].split("</RUN_BASH>")[0]
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                self.history.append({
                    "role": "user", 
                    "content": f"Tool output:\n{result.stdout}\n{result.stderr}"
                })
                print(f"  [bash] {cmd[:60]}...")
            
            elif "<DONE>" in response:
                print(f"\n✅ Task complete:\n{response.split('<DONE>')[0]}")
                break
            
            else:
                print(f"  [turn {i}] {response[:200]}...")
        
        return self.history

# Usage
agent = LocalAgent(
    name="SigmaBacktestAgent",
    system_prompt="""You are a quantitative backtesting agent. 
Your tools:
- <RUN_BASH>command</RUN_BASH> to run Python, fetch data, etc
- Read/write files directly
- Analyze results and report metrics

When done, output <DONE> with final results."""
)

agent.run("Backtest SAMTC Phase 13A on 2024-2025 data. Report Sharpe, Payoff, Skew.")
```

**Cost:** $0 (runs on your machine, Ollama already installed)

**Pros:**
- Instant feedback (local latency ~5–10s per turn)
- Full control over Gemma4 parameters
- No rate limits
- No API keys exposed

**Cons:**
- Gemma4 slower than Opus (but good enough for backtesting orchestration)
- Can't run 24/7 (your machine has to stay on)

---

## FREE ALTERNATIVE: Deploy Gemma4 to VPS (~$5–10/month)

Host Gemma4 on a cheap cloud server (Render, Railway, Fly.io) and call it from anywhere.

### Step 1: Docker + Ollama Setup

```dockerfile
FROM ollama/ollama:latest

# Pre-load Gemma4
RUN ollama pull gemma4:31b

EXPOSE 11434

CMD ["ollama", "serve"]
```

### Step 2: Deploy to Render (Free Tier, then $5–10/mo)

```yaml
services:
  - type: web
    name: gemma4-api
    env: docker
    dockerfilePath: ./Dockerfile
    plan: starter  # $5/mo, keeps running
    envVars:
      - key: OLLAMA_HOST
        value: "0.0.0.0:11434"
```

**Deploy:**
```bash
git push render main  # auto-deploys
```

### Step 3: Call from Anywhere

```python
import requests

GEMMA4_URL = "https://gemma4-api.onrender.com"

def call_gemma4_cloud(prompt: str):
    response = requests.post(
        f"{GEMMA4_URL}/api/generate",
        json={
            "model": "gemma4:31b",
            "prompt": prompt,
            "stream": False,
            "temperature": 1.0,
            "top_p": 0.95
        }
    )
    return response.json()["response"]

# Same agent loop as before, but calls cloud Gemma4
result = call_gemma4_cloud("Run a backtest...")
```

**Cost:** ~$5–10/mo (Render starter or Railway free tier + paid if needed)

**Pros:**
- Always on
- Can run scheduled backtests 24/7
- Same agent loop code
- Much cheaper than Anthropic Managed Agents (~$180–500/mo)

---

## HYBRID APPROACH (Recommended for Sigma-Brain)

**Use Claude for planning, Gemma4 for execution.**

```python
from anthropic import Anthropic
import requests

claude = Anthropic()

def execute_with_gemma(task: str):
    """
    1. Claude plans the task (1 API call, ~$0.01)
    2. Gemma4 executes locally (free)
    3. Claude reviews results (1 API call, ~$0.01)
    """
    
    # Step 1: Claude creates execution plan
    plan = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"Create a step-by-step execution plan for: {task}"
        }]
    ).content[0].text
    
    # Step 2: Gemma4 executes the plan
    execution = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma4:31b", "prompt": f"Plan:\n{plan}\n\nExecute step by step."}
    ).json()["response"]
    
    # Step 3: Claude reviews & formats results
    review = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"Review and format these backtest results:\n{execution}"
        }]
    ).content[0].text
    
    return review

# Cost: ~$0.02 total (2 Claude turns) + $0 (Gemma4 local)
result = execute_with_gemma("Backtest SAMTC Phase 13A, report metrics")
```

**Cost:** ~$0.02 per task (only Claude for planning + review)

---

## Nightly Backtest Pipeline (Hybrid, Scheduled)

```python
#!/usr/bin/env python3
# nightly_backtest.py — run via `crontab -e`: 0 0 * * * python nightly_backtest.py

import subprocess
from anthropic import Anthropic

def main():
    # Plan: Claude (cheap)
    claude = Anthropic()
    plan = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": """Plan a nightly backtest of:
- SAMTC Phase 13A (OOS validation)
- Test 10C (governance baseline)
- New B2B zone detector

Return steps only, no preamble."""
        }]
    ).content[0].text
    
    # Execute: Gemma4 (free) + bash
    subprocess.run([
        "ollama", "run", "gemma4-baysix",
        f"Execute this plan:\n{plan}"
    ])
    
    # Review: Claude (cheap)
    with open("backtest_results.json") as f:
        results = f.read()
    
    review = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"Summarize these backtest results for the hedge fund:\n{results}"
        }]
    ).content[0].text
    
    print(review)
    # Send email, Slack, etc

if __name__ == "__main__":
    main()
```

**Cost per nightly backtest:** ~$0.02 (two Claude turns)  
**Cost per month:** ~$0.60 (30 backtests)  
**vs Managed Agents:** ~$250/mo

---

## Cost Comparison Table

| Option | Cost | Speed | Complexity | 24/7? |
|--------|------|-------|-----------|-------|
| **Local agent loop** | $0 | 5–10s/turn | Low | ❌ (machine on) |
| **Gemma4 on VPS** | $5–10/mo | 5–10s/turn | Medium | ✅ |
| **Claude Managed Agents** | $180–500/mo | 1–2s/turn | Low | ✅ |
| **Hybrid (Claude + Gemma4)** | $0.02/task | 2–5s/turn | Low | ✅ |

---

## Best Practices

### ✅ Managed Agents — Good For
- Backtesting pipelines (run 24/7, auto-retry on failures)
- Data ingestion (fetch FRED, NASA EONET, crypto feeds continuously)
- Report generation (daily Sharpe/Calmar/recovery summaries)
- Live trading signals (run strategy evaluation every hour)

### ✅ Advisor Tool — Good For
- Strategy coding (Sonnet + Opus guidance = production-quality code)
- Architecture decisions (executor proposes, advisor validates)
- Complex research (exploratory work, then ask Opus for synthesis)

### ✅ Hybrid Approach (LOCAL) — Good For
- Backtesting orchestration (Claude plans, Gemma4 executes)
- One-off research tasks
- Cost-sensitive workloads
- Development/prototyping

### ❌ Avoid
- Single-turn Q&A with advisor (no value in a plan for one answer)
- Real-time trading decisions (too slow; use cached signals instead)
- Managed Agents for sub-second latency (cloud infra has ~500ms overhead)

---

## References

- **Claude Managed Agents Docs:** https://platform.claude.com/docs/en/managed-agents/overview
- **Advisor Tool Docs:** https://platform.claude.com/docs/en/managed-agents/overview (scroll to Advisor Tool section)
- **Anthropic API Reference:** https://platform.claude.com/docs/en/api/beta/sessions
- **Beta Headers Required:**
  - Managed Agents: `managed-agents-2026-04-01`
  - Advisor Tool: `advisor-tool-2026-03-01`

---

## Implementation Checklist

### To Implement Later:
- [ ] Test local agent loop with Gemma4-baysix on your machine
- [ ] Deploy Gemma4 to Render/Railway for 24/7 availability
- [ ] Build hybrid pipeline: Claude planning + Gemma4 execution
- [ ] Set up nightly cron job for SAMTC/MT5 backtests
- [ ] Wire Advisor Tool into sigma-quant code generation workflows
- [ ] Compare costs: local vs hybrid vs Managed Agents for your actual workload
- [ ] Integrate results into sigma-quant dashboard

---

*Last Updated: 2026-04-11*
