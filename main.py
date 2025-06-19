import asyncio
from telegram import Update, User
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from core.analyze import analyze_conflict

TOKEN = "ТВОЙ_ТОКЕН"
OWNER_ID = 1609956648
MODERATORS = [1609956648]

# Активные споры: (user1_id, user2_id) -> [messages...]
active_disputes = {}
last_active = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я — бот-судья. Используй /spor @пользователь, чтобы начать спор.")

# /myid
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Твой ID: {update.effective_user.id}")

# /youid
async def youid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        await update.message.reply_text(f"ID пользователя: {uid}")
    else:
        await update.message.reply_text("Ответь на сообщение человека.")

# /spor
async def spor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответь на сообщение того, с кем хочешь начать спор.")
        return

    user1 = update.effective_user.id
    user2 = update.message.reply_to_message.from_user.id

    if user1 in MODERATORS and user2 in MODERATORS:
        await update.message.reply_text("⚠️ Спор между модераторами невозможен.")
        return

    key = tuple(sorted((user1, user2)))
    if key in active_disputes:
        await update.message.reply_text("Спор уже идёт.")
        return

    active_disputes[key] = []
    last_active[key] = asyncio.get_event_loop().time()
    await update.message.reply_text("✅ Спор начат. Пишите аргументы!")

# /log
async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user1 = update.effective_user.id
    for (u1, u2), messages in active_disputes.items():
        if user1 in (u1, u2):
            log_text = "\n".join(messages[-10:])
            await update.message.reply_text(f"📝 Последние сообщения:\n{log_text}")
            return
    await update.message.reply_text("Нет активного спора.")

# /mlog
async def mlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        return await update.message.reply_text("Нет доступа.")

    uid = None
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("Неверный ID.")

    if uid:
        for (u1, u2), messages in active_disputes.items():
            if uid in (u1, u2):
                log_text = "\n".join(messages[-10:])
                return await update.message.reply_text(f"📝 Лог спора:\n{log_text}")
        return await update.message.reply_text("Спор не найден.")
    await update.message.reply_text("Укажи ID или ответь на сообщение.")

# /end
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    for key in list(active_disputes.keys()):
        if uid in key:
            verdict = analyze_conflict("\n".join(active_disputes[key]))
            del active_disputes[key]
            del last_active[key]
            await update.message.reply_text(f"✅ Спор завершён.\n📜 Вердикт: {verdict}")
            return
    await update.message.reply_text("Нет активного спора.")

# /mend
async def mend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        return await update.message.reply_text("Нет доступа.")

    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        for key in list(active_disputes.keys()):
            if uid in key:
                del active_disputes[key]
                del last_active[key]
                return await update.message.reply_text("Спор принудительно завершён.")
    await update.message.reply_text("Укажи спор через ответ на сообщение.")

# /kick
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        return await update.message.reply_text("Нет доступа.")
    if update.message.reply_to_message:
        try:
            await update.message.chat.ban_member(update.message.reply_to_message.from_user.id)
            await update.message.reply_text("🚫 Пользователь исключён.")
        except:
            await update.message.reply_text("❌ Не удалось исключить.")
    else:
        await update.message.reply_text("Ответь на сообщение пользователя.")

# Принимаем все сообщения и логируем их
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    for key in active_disputes:
        if uid in key:
            active_disputes[key].append(f"{uid}: {update.message.text}")
            last_active[key] = asyncio.get_event_loop().time()
            break

# Проверка на неактивность
async def check_inactivity(app):
    while True:
        now = asyncio.get_event_loop().time()
        for key in list(last_active):
            if now - last_active[key] > 300:  # 5 минут
                del active_disputes[key]
                del last_active[key]
        await asyncio.sleep(60)

# Запуск
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("youid", youid))
    app.add_handler(CommandHandler("spor", spor))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CommandHandler("mlog", mlog))
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("mend", mend))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    app.create_task(check_inactivity(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())