import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, ChatMember, MessageEntity
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackContext
)
from core.analyze import analyze_conflict

TOKEN = os.environ.get("TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", 1609956648))  # Fallback на твой ID
MODERATORS = [OWNER_ID]  # Можно будет расширить
MAX_ACTIVE_DISPUTES = 5

# Структура для хранения споров
active_disputes = {}  # chat_id: {users, log, last_activity}
logging.basicConfig(level=logging.INFO)

# Авто-завершение спора по таймеру
async def monitor_disputes(app):
    while True:
        now = datetime.utcnow()
        for chat_id in list(active_disputes.keys()):
            last = active_disputes[chat_id]['last_activity']
            if now - last > timedelta(minutes=5):
                await app.bot.send_message(chat_id=chat_id, text="🕒 Спор закрыт по неактивности.")
                del active_disputes[chat_id]
        await asyncio.sleep(30)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👨‍⚖️ Бот Судья готов. Введите /spor @пользователь для начала спора.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Ваш ID: {update.effective_user.id}")

async def youid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await update.message.reply_text(f"🆔 ID этого пользователя: {target.id}")
    else:
        await update.message.reply_text("⚠️ Используйте в ответ на сообщение.")

async def spor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_disputes:
        await update.message.reply_text("⚠️ В этом чате уже идёт спор.")
        return
    if len(active_disputes) >= MAX_ACTIVE_DISPUTES:
        await update.message.reply_text("❌ Превышен лимит активных споров.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Используйте команду в ответ на сообщение оппонента.")
        return

    u1 = update.effective_user.id
    u2 = update.message.reply_to_message.from_user.id
    if u1 in MODERATORS and u2 in MODERATORS:
        await update.message.reply_text("⚠️ Споры между модераторами не разрешены.")
        return

    active_disputes[chat_id] = {
        'users': [u1, u2],
        'log': [],
        'last_activity': datetime.utcnow()
    }
    await update.message.reply_text("🧨 Спор начат! Пишите аргументы.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_disputes:
        active_disputes[chat_id]['log'].append(f"{update.effective_user.first_name}: {update.message.text}")
        active_disputes[chat_id]['last_activity'] = datetime.utcnow()

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in active_disputes:
        await update.message.reply_text("⚠️ В этом чате нет активного спора.")
        return
    users = active_disputes[chat_id]['users']
    if update.effective_user.id not in users:
        await update.message.reply_text("❌ Вы не участник этого спора.")
        return

    log = "\n".join(active_disputes[chat_id]['log'])
    verdict = analyze_conflict(log)
    await update.message.reply_text(f"📜 Вердикт:\n{verdict}")
    del active_disputes[chat_id]

async def mend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ Только владелец может завершать споры вручную.")
    chat_id = update.effective_chat.id
    if chat_id in active_disputes:
        del active_disputes[chat_id]
        await update.message.reply_text("✅ Спор принудительно завершён.")
    else:
        await update.message.reply_text("⚠️ Нет активного спора.")

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_disputes and update.effective_user.id in active_disputes[chat_id]['users']:
        log = "\n".join(active_disputes[chat_id]['log'])
        await update.message.reply_text(f"🗒️ Лог:\n{log}")
    else:
        await update.message.reply_text("⚠️ Лог доступен только участникам активного спора.")

async def mlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        return await update.message.reply_text("⛔ Только модераторы могут использовать эту команду.")
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("⚠️ Неверный формат ID.")
    else:
        return await update.message.reply_text("⚠️ Укажите ID или ответьте на сообщение.")

    for cid, info in active_disputes.items():
        if target_id in info['users']:
            log = "\n".join(info['log'])
            return await update.message.reply_text(f"🗒️ Лог спора с ID {target_id}:\n{log}")
    await update.message.reply_text("❌ Спор не найден.")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        return await update.message.reply_text("⛔ Только модераторы могут кикать.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Используйте в ответ на сообщение.")

    user_id = update.message.reply_to_message.from_user.id
    try:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
        await update.message.reply_text("✅ Пользователь удалён.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("youid", youid))
    app.add_handler(CommandHandler("spor", spor))
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("mend", mend))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CommandHandler("mlog", mlog))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(lambda c: monitor_disputes(app), interval=60)
    app.run_polling()

if __name__ == '__main__':
    main()