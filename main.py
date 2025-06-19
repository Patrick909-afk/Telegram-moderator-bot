from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from core.analyze import analyze_conflict

# 🔧 Настройки
TOKEN = "7703940481:AAE1yqM9r0iEXa0cPMHNp4-ipc_YafVTXiE"
OWNER_ID = 1609956648
MODERATORS = [1609956648]  # пока только ты, добавишь других позже

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Я — бот-судья. Отправьте текст спора, и я постараюсь определить, кто прав.")

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text

    # Проверка на спор между модераторами
    if any(str(uid) in text for uid in map(str, MODERATORS)):
        update.message.reply_text("⚠️ Спор с модератором или между модераторами не рассматривается.")
        return

    verdict = analyze_conflict(text)
    update.message.reply_text(f"📜 Вердикт:\n{verdict}")

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()