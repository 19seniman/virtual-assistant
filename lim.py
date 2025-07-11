import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID'))

IMAGE_DIR = 'downloaded_images'
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

REPLY = 1
user_photo_senders = {}

def get_language(update: Update):
    lang = update.message.from_user.language_code
    return lang if lang in ['id', 'en'] else 'en'

def start(update: Update, context: CallbackContext):
    lang = get_language(update)
    messages = {
        'id': 'Halo! Kirim gambar ke aku, nanti aku simpen dan owner bakal dapat notifikasi.',
        'en': 'Hello! Send me a photo, I will save it and notify the owner.'
    }
    update.message.reply_text(messages[lang])

def handle_photo(update: Update, context: CallbackContext):
    user = update.message.from_user
    lang = get_language(update)
    photo_file = update.message.photo[-1].get_file()
    file_path = os.path.join(IMAGE_DIR, f'{photo_file.file_id}.jpg')
    photo_file.download(file_path)

    user_photo_senders[user.id] = user.chat_id

    messages_user = {
        'id': 'Gambar diterima, owner akan segera menghubungi kamu.',
        'en': 'Photo received, the owner will contact you soon.'
    }
    update.message.reply_text(messages_user[lang])

    messages_owner = (
        f'📸 New photo from @{user.username or user.first_name} (id: {user.id}).\n'
        f'File saved: {file_path}\n'
        f'Type /reply {user.id} to reply.'
    )
    context.bot.send_message(chat_id=OWNER_CHAT_ID, text=messages_owner)

def reply_command(update: Update, context: CallbackContext):
    args = context.args
    lang = get_language(update)
    if len(args) != 1 or not args[0].isdigit():
        messages = {
            'id': 'Gunakan perintah dengan benar: /reply <user_id>',
            'en': 'Please use the command correctly: /reply <user_id>'
        }
        update.message.reply_text(messages[lang])
        return ConversationHandler.END

    user_id = int(args[0])
    if user_id not in user_photo_senders:
        messages = {
            'id': 'User ID tidak ditemukan atau sudah tidak aktif.',
            'en': 'User ID not found or no longer active.'
        }
        update.message.reply_text(messages[lang])
        return ConversationHandler.END

    context.user_data['reply_to_user_id'] = user_id
    messages = {
        'id': 'Kirim pesan balasan untuk user ini:',
        'en': 'Send your reply message to this user:'
    }
    update.message.reply_text(messages[lang])
    return REPLY

def send_reply(update: Update, context: CallbackContext):
    user_id = context.user_data.get('reply_to_user_id')
    if not user_id:
        update.message.reply_text('Terjadi kesalahan, coba lagi.')
        return ConversationHandler.END

    message = update.message.text
    context.bot.send_message(chat_id=user_photo_senders[user_id], text=f'Balasan dari owner: {message}')
    update.message.reply_text('Pesan terkirim ke user.')
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    lang = get_language(update)
    messages = {
        'id': 'Balasan dibatalkan.',
        'en': 'Reply cancelled.'
    }
    update.message.reply_text(messages[lang])
    return ConversationHandler.END

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('reply', reply_command)],
        states={REPLY: [MessageHandler(Filters.text & ~Filters.command, send_reply)]},
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
