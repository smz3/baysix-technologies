"""
Telegram-to-Claude bridge (docs/plans/2026-07-31_telegram_bridge_plan.md, step 3+).

One persistent ClaudeSDKClient session for the life of this process, reused across
every Telegram message (avoids paying CLAUDE.md/hooks/skills load cost per message).
Session id is persisted to session_id.txt so a process restart can resume the same
conversation instead of starting cold.

Permission model: DECIDED 2026-07-31 by Syafiq — full run, no restriction
(bypassPermissions). No human is watching Telegram in real time to approve a
prompt, so this is a deliberate, explicit choice, not a default fallthrough.
See docs/plans/2026-07-31_telegram_bridge_plan.md Section 3 for the record.

Single-user: only TELEGRAM_ALLOWED_CHAT_ID is served. /stop is the kill-switch.
"""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSION_ID_FILE = Path(__file__).resolve().parent / "session_id.txt"
TELEGRAM_MAX_LEN = 4096

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_ID = int(os.environ["TELEGRAM_ALLOWED_CHAT_ID"])

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bridge")

claude: ClaudeSDKClient | None = None
claude_lock = asyncio.Lock()


def _load_resume_id() -> str | None:
    if SESSION_ID_FILE.exists():
        sid = SESSION_ID_FILE.read_text().strip()
        return sid or None
    return None


def _save_resume_id(session_id: str) -> None:
    SESSION_ID_FILE.write_text(session_id)


async def get_claude() -> ClaudeSDKClient:
    global claude
    if claude is None:
        options = ClaudeAgentOptions(
            cwd=str(REPO_ROOT),
            permission_mode="bypassPermissions",
            resume=_load_resume_id(),
        )
        claude = ClaudeSDKClient(options=options)
        await claude.connect()
        log.info("Claude session connected (cwd=%s)", REPO_ROOT)
    return claude


def chunk_text(text: str, size: int = TELEGRAM_MAX_LEN) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id != ALLOWED_CHAT_ID:
        log.warning("Ignoring message from unauthorized chat_id=%s", chat_id)
        return

    text = update.message.text
    log.info("-> %r", text)

    async with claude_lock:
        client = await get_claude()
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await client.query(text)

        reply_parts: list[str] = []
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        reply_parts.append(block.text)
            elif isinstance(message, ResultMessage):
                if message.session_id:
                    _save_resume_id(message.session_id)

    reply = "".join(reply_parts).strip() or "(no text response)"
    log.info("<- %d chars", len(reply))
    for chunk in chunk_text(reply):
        await update.message.reply_text(chunk)


async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id != ALLOWED_CHAT_ID:
        return
    await update.message.reply_text("Stopping bridge.")
    log.info("Kill-switch received from chat_id=%s", chat_id)
    context.application.stop_running()


def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("stop", handle_stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Bridge starting (long-poll, chat_id=%s).", ALLOWED_CHAT_ID)
    app.run_polling()


if __name__ == "__main__":
    main()
