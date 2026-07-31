# Telegram-to-Claude Bridge — Build Plan

Status: **DECISIONS LOCKED 2026-07-31, not built.** Written 2026-07-31 after a research pass (Agent tool, general-purpose, background). Section 7 open questions resolved same day (see below). No code exists yet — this is the spec the next session builds against.

---

## 1. Why (context for whoever picks this up)

Syafiq wants to message Claude directly from Telegram when away from his PC — not another MT5 trade-alert bot (he already has one, outbound-only, see below), but an actual two-way conversation with Claude Code running against this repo.

This sits inside a larger trajectory shift he's making (discussed same session, 2026-07-31):
- Move root [CLAUDE.md](../../CLAUDE.md) away from being FOB-locked — **done same session**: MT5/FOB workflow moved to [docs/reference/fob_mt5_playbook.md](../reference/fob_mt5_playbook.md) (commit `fb8ef6f`).
- Longer-term: IBKR TWS as an execution venue alongside/instead of MT5, and a "set a goal, Claude runs it end-to-end" autonomy model instead of Syafiq hand-specifying strategy mechanics (e.g. FOB PBO/VR/CF) every time. **Not scoped or committed to yet — flag, don't assume, next session.**
- This Telegram bridge is the first concrete infra piece of that shift: a way to reach Claude off-PC.

**Old telegram code audited, confirmed irrelevant:** `mt5/Include/Sigma_System/V5.0/Communication/TelegramBot.mqh` (ported from `SIGMA V3.2`, backup at `C:\Users\User\Desktop\backup\MQL5_18122025T3andOverlapDone`) is a stub in this repo, and the working V3.2 original is outbound-only (MQL5 `WebRequest` push of trade alerts, no inbound polling, no command handling implemented). Wrong shape for this — do not revive it as the basis for this bridge.

---

## 2. Architecture decision

**Use the Python Claude Agent SDK, `ClaudeSDKClient` (persistent, in-process session) — not repeated `claude -p` CLI subprocess calls.**

Why:
- `ClaudeSDKClient` holds one continuous conversation in the running Python process. CLAUDE.md/hooks/skills load once at session start, not on every Telegram message.
- Repeated `claude -p ...` subprocess calls are a cold session each time unless chained via `--continue`/`--resume`, and reload full project context (this repo's CLAUDE.md is not small) on every single message — real, avoidable cost.
- Docs: [Claude Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python), [Run Claude Code headless](https://code.claude.com/docs/en/headless).

Fallback if SDK proves awkward under Windows PowerShell: CLI subprocess with `--continue`/`--resume <session_id>` (session transcripts live under `~/.claude/projects/<project-path>/`). Simpler to reason about, matches his terminal-native habits, but pay the per-message context-reload cost.

---

## 3. Safety / permission design

**DECIDED 2026-07-31 — Syafiq explicitly chose full-run, no restriction, overriding the original recommendation below of a stricter phone profile.** Original reasoning (kept for the record, not followed): a phone text is a lower-trust input surface and there's no human physically present to click "allow" on a risky-action permission prompt over Telegram, so the safe default would have been read-only/plan mode with a hard block on Bash/Edit/Write/live-order tools. Syafiq's call: the phone session runs with the **same tool access as the interactive desktop session** — no separate restrictive `--settings` profile, no `--disallowedTools`.

Practical consequence to build against: since nothing is held back for manual approval, **any permission prompt the SDK would normally raise must auto-approve** (equivalent to `--dangerously-skip-permissions` / a permission profile that allows everything), because there is no one watching Telegram in real time to answer it. Build this deliberately, not as a default that happened to fall out of an unset config — the auto-approve behavior should be explicit in the bot's settings file so it's visible and auditable, not implicit.

Still non-negotiable regardless of the above:
- Bot token, and any secrets: `.env` only, gitignored, never printed/logged/committed. SDK/CLI can echo prompts/config in verbose or `stream-json` output modes — scrub before any logging.
- Telegram side: hard allowlist on `chat_id` — single-user bot, drop/ignore any other sender, no auth flow needed beyond that check.
- `/stop` kill-switch (Section 4) stays in v1 — it's the one safety control that still makes sense once permissions are unrestricted.

---

## 4. Telegram side

- Create bot via **@BotFather**, get bot token.
- **Long-polling**, not webhook — no public HTTPS endpoint/domain needed on a home PC, avoids ngrok/reverse-proxy complexity.
- Library: **`python-telegram-bot` v21.x** (actively maintained; simpler sync+async model than `aiogram` for a single-user bot at this scale — [comparison](https://piptrends.com/compare/python-telegram-bot-vs-aiogram)).
- Handle Telegram's 4096-char message cap — chunk long Claude replies.
- Use `send_chat_action` ("typing…") for feedback since Claude responses can take 10s+.
- Add a `/stop` command as a kill-switch Syafiq can hit from Telegram itself without PC access.

---

## 5. Hosting (Windows 10, this PC)

- **DECIDED 2026-07-31: v1 = PC-local, confirmed.** Plain Python process in a dedicated `Start-Process` PowerShell window — matches his existing long-running-command convention ([[feedback_long_run_terminal]]: never `run_in_background`, always a visible window), log-visible, manual restart on crash.
- **v2** (once proven stable): wrap as a **Windows service via NSSM** (Non-Sucking Service Manager) — auto-restart on crash, stdout/stderr redirected to log files, survives without an interactive login session ([NSSM scenarios](https://nssm.cc/scenarios)).
- **Accepted limitation for v1:** if the PC sleeps or is off, the bot stops responding — "away from PC" only means away-from-desk-but-PC-awake, not fully remote. Fixing that needs a cloud host, which then loses direct access to `research.db` / ArcticDB / the MT5 terminal (all Windows-desktop-resident) — **not recommended for v1**, revisit only if the desktop-tethered version proves genuinely limiting in practice.

---

## 6. Build sequence (for the implementing session)

1. BotFather → token → `.env`.
2. Minimal `python-telegram-bot` long-poll echo script, chat_id allowlist only — **prove the Telegram round-trip before touching Claude at all.**
3. Wire in `ClaudeSDKClient`: `cwd` = repo root, full/unrestricted permission profile with explicit auto-approve (Section 3 — deliberate, not default-fallthrough).
4. Message chunking for long replies.
5. Persist last session id to a small local file (not `.env`) so the bot can resume its Claude session after a process restart.
6. "Thinking…" typing indicator.
7. Run as `Start-Process` PowerShell window (v1 hosting).
8. `/stop` kill-switch command.
9. If stable after real use: promote to NSSM service (v2 hosting).

---

## 7. Open decisions — RESOLVED 2026-07-31

- **Hosting:** PC-local v1, confirmed. No 24/7-off-PC requirement.
- **Permission profile:** Full run, no restriction — same tool access as the desktop session, auto-approved (overrides the plan's original stricter-profile recommendation; see Section 3 for the record).
- **Repo location:** Inside `baysix-technologies` (not a new decoupled repo) — direct access to `research.db`/ArcticDB/MT5 terminal without a cross-repo cwd reference. Suggested home: a new top-level folder, e.g. `telegram_bridge/` (bot script, `.env`, session-id file), sibling to `mt5/`, `b2b/`, `research/`.

---

## 8. Risks / gotchas (from research pass)

- Cost/context per message avoided by persistent SDK client (Section 2) — this was the main reason to reject the naive `claude -p` per-message approach.
- Telegram long-polling stops if the PC sleeps (Section 5) — needs a "prevent sleep" power-setting note for Syafiq, or accept as v1 limitation.
- Background bash tasks spawned in headless/`-p` mode are killed ~5s after the result returns (irrelevant unless a Telegram-triggered Claude session tries to launch a long dev-server-style background task — should not happen under the restrictive profile anyway).
- Telegram Bot API rate limits are generous for single-user long-polling bots — not a practical constraint here.
- Sources: [Run Claude Code headless](https://code.claude.com/docs/en/headless) · [Claude Agent SDK Python](https://code.claude.com/docs/en/agent-sdk/python) · [Agent SDK permissions](https://platform.claude.com/docs/en/agent-sdk/permissions) · [Claude Code permission modes](https://claude-code-playbook.pages.dev/en/docs/level-2/permission-modes) · [python-telegram-bot vs aiogram](https://piptrends.com/compare/python-telegram-bot-vs-aiogram) · [NSSM scenarios](https://nssm.cc/scenarios)
