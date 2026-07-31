"""
Step 2 of the Telegram bridge build (docs/plans/2026-07-31_telegram_bridge_plan.md).
Minimal long-poll echo bot — proves the Telegram round-trip before wiring in Claude.
No chat_id allowlist yet: run this first, send the bot a message, and the console
will print your chat_id. Put that in .env as TELEGRAM_ALLOWED_CHAT_ID, then step 3
adds the allowlist check before any Claude wiring happens.
"""
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("echo_bot")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text
    log.info("chat_id=%s text=%r", chat_id, text)
    await update.message.reply_text(f"echo: {text}\n(your chat_id: {chat_id})")


def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    log.info("Bot starting (long-poll). Send it a message from Telegram now.")
    app.run_polling()


if __name__ == "__main__":
    main()
