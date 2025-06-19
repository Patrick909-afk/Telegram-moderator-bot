import logging
from telegram import Update, ChatMember, Message
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from core.analyze import analyze_conflict
from datetime import datetime, timedelta
import asyncio

# 🔧 Настройки
TOKEN = "ТВОЙ_ТОКЕН"
OWNER_ID = 1609956648
MODERATORS = [1609956648]

# 💬 Состояния
active_dispute = False
dispute_users = set()
dispute_log = []
last_activity = None
AUTO_CLOSE_SECONDS = 300

# ⚙️ Логгер
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 👥 Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я — бот-судья. Используй /spor @user, чтобы начать спор.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Твой ID: {update.effective_user.id}")

async def youid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        await update.message.reply_text(f"ID этого пользователя: {target_id}")
    else:
        await update.message.reply_text("Ответь на сообщение пользователя, чтобы узнать его ID.")

async def spor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_dispute, dispute_users, dispute_log, last_activity

    if active_dispute:
        await update.message.reply_text("Спор уже активен.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Ответь на сообщение пользователя, с кем хочешь начать спор.")
        return

    user1 = update.effective_user.id
    user2 = update.message.reply_to_message.from_user.id

    if user1 in MODERATORS and user2 in MODERATORS:
        await update.message.reply_text("⚠️ Споры между модераторами не рассматриваются.")
        return

    dispute_users = {user1, user2}
    active_dispute = True
    dispute_log = []
    last_activity = datetime.utcnow()

    await update.message.reply_text("⚖️ Спор начат. Отправляйте сообщения.")
    asyncio.create_task(check_dispute_timeout(context))

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_dispute, dispute_users, dispute_log
    if update.effective_user.id not in dispute_users:
        await update.message.reply_text("Ты не участвуешь в споре.")
        return

    await update.message.reply_text("Спор завершён.")
    dispute_users = set()
    dispute_log = []
    active_dispute = False

async def mend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        await update.message.reply_text("Только модератор может завершить спор.")
        return

    global active_dispute, dispute_users, dispute_log
    active_dispute = False
    dispute_users = set()
    dispute_log = []
    await update.message.reply_text("🛑 Спор модератором завершён.")

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in dispute_users:
        await update.message.reply_text("Ты не участвуешь в споре.")
        return

    if not dispute_log:
        await update.message.reply_text("Лог пуст.")
        return

    await update.message.reply_text("📜 Лог:\n" + "\n".join(dispute_log[-10:]))

async def mlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        await update.message.reply_text("Нет доступа.")
        return

    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except:
            await update.message.reply_text("Неверный ID.")
            return
    else:
        await update.message.reply_text("Укажи ID или ответь на сообщение.")
        return

    lines = [line for line in dispute_log if str(uid) in line]
    if not lines:
        await update.message.reply_text("Ничего не найдено.")
    else:
        await update.message.reply_text("📄 MLog:\n" + "\n".join(lines[-10:]))

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATORS:
        await update.message.reply_text("Ты не модератор.")
        return

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user.id
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target)
            await update.message.reply_text("✅ Успешно кикнут.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")
    else:
        await update.message.reply_text("Ответь на сообщение пользователя.")

# 📩 Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_activity

    if not active_dispute or update.effective_user.id not in dispute_users:
        return

    last_activity = datetime.utcnow()

    msg = f"[{update.effective_user.id}] {update.message.text}"
    dispute_log.append(msg)

    if any(str(uid) in update.message.text for uid in map(str, MODERATORS)):
        await update.message.reply_text("⚠️ Споры с модераторами не рассматриваются.")
        return

    verdict = analyze_conflict(update.message.text)
    await update.message.reply_text(f"📜 Вердикт:\n{verdict}")

# ⏳ Автозакрытие
async def check_dispute_timeout(context: ContextTypes.DEFAULT_TYPE):
    global last_activity, active_dispute
    while active_dispute:
        if datetime.utcnow() - last_activity > timedelta(seconds=AUTO_CLOSE_SECONDS):
            active_dispute = False
            await context.bot.send_message(chat_id=context.application.bot_data["chat_id"], text="⏱ Спор завершён по неактивности.")
            break
        await asyncio.sleep(30)

# 🚀 MAIN
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.bot_data["chat_id"] = OWNER_ID  # для автозавершения

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

    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())