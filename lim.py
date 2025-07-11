import os
from dotenv import load_dotenv
from telegram import Update
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
    # Still keep language detection for potential future use
    lang = update.effective_user.language_code
    return 'en'  # Force English

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    messages = 'Hello! Send me a photo, I will save it and notify the owner.\n\nSend your transaction proof.'
    await update.message.reply_text(messages)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_file = await update.message.photo[-1].get_file()
    file_path = os.path.join(IMAGE_DIR, f'{photo_file.file_id}.jpg')
    await photo_file.download_to_drive(file_path)

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

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('reply', reply_command)],
        states={REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_reply)]},
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
