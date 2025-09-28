"""A minimal Telegram bot that talks to the Smart Bill Assistant API.

Usage:
  set TELEGRAM_BOT_TOKEN=<token>
  python scripts\smart_bill_bot.py

Commands:
  /bills - list bills and suggested actions
  /confirm <index> - confirm payment sandbox for bill index
  /archive <index> - archive bill
"""
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_BASE = os.environ.get("API_BASE", "http://localhost:8080")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Please set TELEGRAM_BOT_TOKEN environment variable")


def user_id_from_update(update: Update) -> str:
    # Use Telegram user id as a stable user identifier for demo
    return str(update.effective_user.id)


async def bills_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = user_id_from_update(update)
    res = requests.get(f"{API_BASE}/smart-bills/list", params={"user_id": uid})
    if res.status_code != 200:
        await update.message.reply_text("Error fetching bills")
        return
    data = res.json()
    bills = data.get("bills", [])
    if not bills:
        await update.message.reply_text("No bills found.")
        return
    msgs = []
    for i, entry in enumerate(bills):
        b = entry.get("bill", {})
        urgency = entry.get("urgency")
        msgs.append(f"#{i} Vendor: {b.get('vendor')} Amount: {b.get('amount')} Due: {b.get('due_date')} ({urgency})")
    msgs.append("Reply with /confirm <index> or /archive <index> to act (sandbox).")
    await update.message.reply_text("\n".join(msgs))


async def confirm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = user_id_from_update(update)
    if not context.args:
        await update.message.reply_text("Usage: /confirm <index>")
        return
    idx = int(context.args[0])
    # first ask for confirmation
    res = requests.post(f"{API_BASE}/smart-bills/action", json={"user_id": uid, "bill_index": idx, "action": "confirm-payment", "confirm": False})
    data = res.json()
    if data.get("status") == "confirm_required":
        await update.message.reply_text("Please confirm by sending /confirm_yes {index}")
        return
    # For demo, send confirm immediately
    res2 = requests.post(f"{API_BASE}/smart-bills/action", json={"user_id": uid, "bill_index": idx, "action": "confirm-payment", "confirm": True})
    await update.message.reply_text(res2.json().get("message", "Done"))


async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = user_id_from_update(update)
    if not context.args:
        await update.message.reply_text("Usage: /archive <index>")
        return
    idx = int(context.args[0])
    res = requests.post(f"{API_BASE}/smart-bills/action", json={"user_id": uid, "bill_index": idx, "action": "archive", "confirm": True})
    await update.message.reply_text(res.json().get("message", "Done"))


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("bills", bills_command))
    app.add_handler(CommandHandler("confirm", confirm_command))
    app.add_handler(CommandHandler("archive", archive_command))
    print("Starting Telegram bot...")
    app.run_polling()


if __name__ == "__main__":
    main()
