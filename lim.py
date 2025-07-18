import os
import logging
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

# Konfigurasi logging untuk menampilkan timestamp
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Memuat variabel lingkungan dari file .env
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID'))

# Direktori untuk menyimpan gambar yang diunduh
IMAGE_DIR = 'downloaded_images'
os.makedirs(IMAGE_DIR, exist_ok=True)

# Konstanta untuk ConversationHandler states
REPLY = 1

# Dictionary untuk menyimpan chat_id pengguna yang terakhir berinteraksi
# user_id -> chat_id
user_photo_senders = {}

# Set untuk melacak pengguna yang telah mengaktifkan menu (misalnya dengan mengirim foto)
user_has_menu = set()

# Fungsi untuk membuat keyboard menu
def get_menu_keyboard():
    keyboard = [
        [KeyboardButton("/start")],
        [KeyboardButton("Send your Tx Hash")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# Handler untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.message.chat_id
    # Selalu perbarui chat_id pengguna saat mereka memulai bot
    user_photo_senders[user.id] = chat_id
    
    # Pesan sambutan yang berbeda untuk pemilik dan pengguna biasa
    if user.id != OWNER_CHAT_ID:
        user_has_menu.add(user.id) # Aktifkan menu untuk pengguna biasa
        reply_markup = get_menu_keyboard()
        await update.message.reply_text(
            "Halo! Kirimkan saya foto sebagai bukti transaksi Anda, dan saya akan memberitahu pemilik. Menu diaktifkan! Gunakan tombol di bawah.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Halo pemilik! Anda bisa menggunakan /reply <user_id> untuk membalas pengguna."
        )

# Handler untuk pesan foto
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.message.chat_id

    # Jika pemilik bot mengirim foto saat dalam mode balasan,
    # lewati handler ini agar ConversationHandler yang menanganinya.
    if user.id == OWNER_CHAT_ID and context.user_data.get('reply_to_user_id') is not None:
        logger.info(f"Pemilik {user.id} mengirim foto saat dalam mode balasan. Melewatkan handle_photo.")
        return

    # Perbarui chat_id untuk pengguna yang mengirim foto
    user_photo_senders[user.id] = chat_id
    user_has_menu.add(user.id) # Mengirim foto mengaktifkan menu untuk pengguna

    photo_file = await update.message.photo[-1].get_file()
    file_path = os.path.join(IMAGE_DIR, f'{photo_file.file_id}.jpg')
    await photo_file.download_to_drive(file_path)

    caption = update.message.caption or "(Tidak ada deskripsi)"

    await update.message.reply_text('Foto diterima, pemilik akan segera menghubungi Anda.')

    # Kirim foto ke pemilik bot
    with open(file_path, 'rb') as photo:
        await context.bot.send_photo(
            chat_id=OWNER_CHAT_ID,
            photo=photo,
            caption=(
                f'📸 Foto baru dari @{user.username or user.first_name} (id: {user.id}).\n'
                f'Deskripsi: {caption}\n'
                f'File disimpan secara lokal.\n'
                f'Ketik /reply {user.id} untuk membalas.'
            )
        )
    
    # Pastikan menu ditampilkan jika bukan pemilik
    if user.id != OWNER_CHAT_ID:
        reply_markup = get_menu_keyboard()
        await update.message.reply_text("Menu diaktifkan! Gunakan tombol di bawah.", reply_markup=reply_markup)

# Handler untuk pesan teks (selain perintah)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    # Jika pemilik bot dalam mode balasan, pesan ini akan ditangani oleh send_reply
    # di ConversationHandler. Jadi, lewati pemrosesan teks normal untuk pemilik.
    if user.id == OWNER_CHAT_ID and context.user_data.get('reply_to_user_id') is not None:
        logger.info(f"Pemilik {user.id} mengirim teks saat dalam mode balasan. Melewatkan handle_text.")
        return

    # Untuk pesan teks lainnya (dari pengguna atau pemilik yang tidak dalam mode balasan),
    # perbarui chat_id pengguna agar selalu terbaru.
    user_photo_senders[user.id] = chat_id

    if text == "Send your Tx Hash":
        if user.id not in user_has_menu:
            await update.message.reply_text(
                "Silakan kirim foto terlebih dahulu untuk mengaktifkan menu."
            )
            return

        await update.message.reply_text(
            "Kirim Tx Hash Anda pada Transaksi Blockchain\nContoh: Tx Hash:0009ui777"
        )

    elif text.lower().startswith("tx hash:"):
        # Periksa apakah pengguna sudah pernah berinteraksi dengan bot (misalnya kirim foto/Tx Hash sebelumnya)
        if user.id not in user_photo_senders: 
            await update.message.reply_text(
                "Silakan kirim foto atau gunakan tombol 'Send your Tx Hash' terlebih dahulu untuk mengaktifkan interaksi."
            )
            return

        await update.message.reply_text("Tx Hash diterima, pemilik akan segera menghubungi Anda.")
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=(
                f"📢 Tx Hash baru dari @{user.username or user.first_name} (id: {user.id}):\n"
                f"{text}\n"
                f"Ketik /reply {user.id} untuk membalas."
            ),
        )

    else:
        await update.message.reply_text(
            "Saya tidak mengerti itu. Silakan gunakan menu atau kirim foto atau Tx Hash Anda."
        )

# Handler untuk perintah /reply (hanya untuk pemilik bot)
async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Pastikan hanya pemilik yang bisa menggunakan perintah ini
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("Anda tidak berwenang menggunakan perintah ini.")
        return ConversationHandler.END

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text('Silakan gunakan perintah dengan benar: /reply <user_id>')
        return ConversationHandler.END

    user_id = int(args[0])
    # Periksa apakah user_id target ada di user_photo_senders
    if user_id not in user_photo_senders:
        await update.message.reply_text('ID pengguna tidak ditemukan atau tidak lagi aktif (pengguna mungkin belum mengirim foto/Tx Hash atau bot baru saja dimulai ulang).')
        return ConversationHandler.END

    context.user_data['reply_to_user_id'] = user_id
    await update.message.reply_text(f'Anda sekarang membalas pengguna {user_id}. Kirim pesan balasan Anda (teks atau foto). Kirim /cancel untuk berhenti membalas.')
    return REPLY

# Handler untuk mengirim balasan dari pemilik ke pengguna
async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('reply_to_user_id')
    if user_id is None: # Seharusnya tidak terjadi jika alur benar, tapi untuk ketahanan
        await update.message.reply_text('Kesalahan: Tidak ada pengguna yang dipilih untuk dibalas. Silakan gunakan /reply <user_id> terlebih dahulu.')
        return ConversationHandler.END

    chat_id = user_photo_senders.get(user_id)
    if chat_id is None:
        logger.error(f"Gagal menemukan chat_id untuk user_id {user_id}. Pengguna mungkin telah memblokir bot atau chat_id hilang.")
        await update.message.reply_text('Gagal mengirim pesan: Chat pengguna tidak ditemukan atau pengguna mungkin telah memblokir bot.')
        # Akhiri percakapan jika chat_id hilang untuk mencegah kesalahan berulang
        context.user_data.pop('reply_to_user_id', None)
        return ConversationHandler.END

    try:
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            logger.info(f"Pemilik {update.effective_user.id} membalas dengan foto ke pengguna {user_id} (chat_id: {chat_id}).")
            await context.bot.send_photo(chat_id=chat_id, photo=photo_file.file_id, caption=update.message.caption)
        else:
            message_text = update.message.text
            logger.info(f"Pemilik {update.effective_user.id} membalas dengan teks ke pengguna {user_id} (chat_id: {chat_id}): '{message_text}'")
            await context.bot.send_message(chat_id=chat_id, text=f'Balasan dari pemilik: {message_text}')
        
        await update.message.reply_text('Pesan berhasil dikirim ke pengguna.')
        logger.info(f"Konfirmasi terkirim ke pemilik {update.effective_user.id}.")

    except Exception as e:
        logger.error(f"Gagal mengirim pesan ke pengguna {user_id} (chat_id: {chat_id}): {e}")
        await update.message.reply_text(f'Gagal mengirim pesan ke pengguna {user_id}. Error: {e}. Mereka mungkin telah memblokir bot atau chat tidak valid.')
    
    # Tetap dalam mode balasan untuk memungkinkan beberapa balasan
    return REPLY

# Handler untuk perintah /cancel (untuk keluar dari mode balasan)
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Pastikan hanya pemilik yang bisa menggunakan perintah ini saat dalam mode balasan
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("Anda tidak berwenang menggunakan perintah ini.")
        return ConversationHandler.END

    context.user_data.pop('reply_to_user_id', None)
    await update.message.reply_text('Sesi balasan dibatalkan. Gunakan /reply <user_id> untuk memulai lagi.')
    return ConversationHandler.END

# Fungsi utama untuk menjalankan bot
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Menambahkan handler perintah dan pesan
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    # handle_text hanya akan memproses teks non-perintah dari pengguna (atau pemilik yang tidak dalam mode balasan)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Konfigurasi ConversationHandler untuk fitur balasan
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('reply', reply_command)],
        states={
            REPLY: [
                # Tangani pesan teks dan foto dari pemilik saat dalam status REPLY
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, send_reply)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    logger.info("Bot mulai polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
