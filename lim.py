import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID'))

IMAGE_DIR = 'downloaded_images'
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

REPLY = 1
user_photo_senders = {}

def get_language(update: Update) -> str:
    return 'en'  # English only for now

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Send Photo")],
        [KeyboardButton("Help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    message = (
        "Welcome! Use the menu below or send me a photo directly.\n\n"
        "Send your transaction proof."
    )
    await update.message.reply_text(message, reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user = update.effective_user
    chat_id = update.message.chat_id

    if text == "send photo":
        # Save chat_id so owner can reply even if photo not sent yet
        user_photo_senders[user.id] = chat_id
        await update.message.reply_text("Please send your photo now.")
    elif text == "help":
        await update.message.reply_text("Just send me a photo as proof of your transaction, and the owner will get notified.")
    else:
        await update.message.reply_text("I didn't understand that. Please use the menu or send a photo.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_file = await update.message.photo[-1].get_file()
    file_path = os.path.join(IMAGE_DIR, f'{photo_file.file_id}.jpg')
    await photo_file.download_to_drive(file_path)

    # Update chat_id in case user sends photo after clicking "Send Photo"
    user_photo_senders[user.id] = update.message.chat_id

    await update.message.reply_text('Photo received, the owner will contact you soon.')

    with open(file_path, 'rb') as photo:
        await context.bot.send_photo(
            chat_id=OWNER_CHAT_ID,
            photo=photo,
            caption=(
                f'📸 New photo from @{user.username or user.first_name} (id: {user.id}).\n'
                f'File saved locally.\n'
                f'Type /reply {user.id} to reply.'
            )
        )

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text('Please use the command correctly: /reply <user_id>')
        return ConversationHandler.END

    user_id = int(args[0])
    if user_id not in user_photo_senders:
        await update.message.reply_text('User ID not found or no longer active.')
        return ConversationHandler.END

    context.user_data['reply_to_user_id'] = user_id
    await update.message.reply_text('Send your reply message to this user:')
    return REPLY

async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('reply_to_user_id')
    if not user_id:
        await update.message.reply_text('An error occurred, please try again.')
        return ConversationHandler.END

    message = update.message.text
    await context.bot.send_message(chat_id=user_photo_senders[user_id], text=f'Reply from owner: {message}')
    await update.message.reply_text('Message sent to user.')
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Reply cancelled.')
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('reply', reply_command)],
        states={REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_reply)]},
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
