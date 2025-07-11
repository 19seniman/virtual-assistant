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
    lang = update.effective_user.language_code
    return lang if lang in ['id', 'en'] else 'en'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_language(update)
    messages = {
        'id': 'Halo! Kirim gambar ke aku, nanti aku simpen dan owner bakal dapat notifikasi.\n\nKirim bukti transaksimu.',
        'en': 'Hello! Send me a photo, I will save it and notify the owner.\n\nSend your transaction proof.'
    }
    await update.message.reply_text(messages[lang])

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_language(update)
    photo_file = await update.message.photo[-1].get_file()
    file_path = os.path.join(IMAGE_DIR, f'{photo_file.file_id}.jpg')
    await photo_file.download_to_drive(file_path)

    user_photo_senders[user.id] = update.message.chat_id

    messages_user = {
        'id': 'Gambar diterima, owner akan segera menghubungi kamu.',
        'en': 'Photo received, the owner will contact you soon.'
    }
    await update.message.reply_text(messages_user[lang])

    messages_owner = (
        f'📸 New photo from @{user.username or user.first_name} (id: {user.id}).\n'
        f'File saved: {file_path}\n'
        f'Type /reply {user.id} to reply.'
    )
    await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=messages_owner)

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    lang = get_language(update)
    if len(args) != 1 or not args[0].isdigit():
        messages = {
            'id': 'Gunakan perintah dengan benar: /reply <user_id>',
            'en': 'Please use the command correctly: /reply <user_id>'
        }
        await update.message.reply_text(messages[lang])
        return ConversationHandler.END

    user_id = int(args[0])
    if user_id not in user_photo_senders:
        messages = {
            'id': 'User ID tidak ditemukan atau sudah tidak aktif.',
            'en': 'User ID not found or no longer active.'
        }
        await update.message.reply_text(messages[lang])
        return ConversationHandler.END

    context.user_data['reply_to_user_id'] = user_id
    messages = {
        'id': 'Kirim pesan balasan untuk user ini:',
        'en': 'Send your reply message to this user:'
    }
    await update.message.reply_text(messages[lang])
    return REPLY

async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('reply_to_user_id')
    if not user_id:
        await update.message.reply_text('Terjadi kesalahan, coba lagi.')
        return ConversationHandler.END

    message = update.message.text
    await context.bot.send_message(chat_id=user_photo_senders[user_id], text=f'Balasan dari owner: {message}')
    await update.message.reply_text('Pesan terkirim ke user.')
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_language(update)
    messages = {
        'id': 'Balasan dibatalkan.',
        'en': 'Reply cancelled.'
    }
    await update.message.reply_text(messages[lang])
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
