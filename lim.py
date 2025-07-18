import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Muat variabel lingkungan dari file .env
load_dotenv()

# Ambil token bot dan ID pemilik dari environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")  # Harus dalam format string

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Keyboard utama
main_menu_keyboard = [
    ["/start"],
    ["/send_tx_hash"]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Halo {user_name}! Kirimkan saya gambar sebagai bukti transaksi Anda.\n\n"
        "Gunakan menu di bawah ini.",
        reply_markup=main_menu_markup,
    )

# /send_tx_hash command
async def send_tx_hash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Silakan kirim bukti tx hash on blockchain transaction\n"
        "Contoh: tx hash : 0x123abc..."
    )

# Tangani gambar
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    # Inisialisasi user_map jika belum ada
    context.bot_data.setdefault('user_map', {})

    # Teruskan gambar ke pemilik bot
    forwarded_message = await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=user.id,
        message_id=update.message.message_id,
    )

    # Simpan ID pengguna asal
    context.bot_data['user_map'][forwarded_message.message_id] = user.id

    # Informasi ke pemilik
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"⬆️ Gambar di atas dikirim oleh: {user.full_name} (ID: {user.id})"
    )

    # Informasi ke pengguna
    await update.message.reply_text(
        "Gambar Anda telah diterima dan diteruskan ke pemilik. Terima kasih!",
        reply_markup=main_menu_markup
    )

# Tangani pesan teks
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    text = update.message.text
    user = update.effective_user

    # Inisialisasi user_map
    context.bot_data.setdefault('user_map', {})

    # Jika pemilik bot membalas pesan yang diteruskan
    if str(chat_id) == OWNER_ID and update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        original_user_id = context.bot_data['user_map'].get(replied_msg_id)

        if original_user_id:
            try:
                await context.bot.send_message(
                    chat_id=original_user_id,
                    text=f"📩 Balasan dari pemilik:\n\n{text}"
                )
                await update.message.reply_text("✅ Balasan berhasil dikirim.")
                # Hapus dari map setelah dibalas
                del context.bot_data['user_map'][replied_msg_id]
            except Exception as e:
                logger.error(f"Gagal mengirim balasan ke {original_user_id}: {e}")
                await update.message.reply_text(f"❌ Gagal mengirim balasan: {e}")
            return
        else:
            await update.message.reply_text(
                "❌ Tidak dapat menemukan pengguna asli.\n"
                "Pastikan Anda membalas pesan gambar atau hash yang diteruskan, bukan teks konfirmasi."
            )
            return

    # Jika pengguna mengirimkan hash transaksi
    if "tx hash :" in text.lower():
        forwarded_message = await context.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=chat_id,
            message_id=update.message.message_id
        )
        context.bot_data['user_map'][forwarded_message.message_id] = user.id

        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"⬆️ Pesan hash di atas dari: {user.full_name} (ID: {user.id})"
        )

        await update.message.reply_text(
            "Pesan hash Anda telah diteruskan ke pemilik.",
            reply_markup=main_menu_markup
        )

# Fungsi utama
def main() -> None:
    if not BOT_TOKEN or not OWNER_ID:
        logger.error("BOT_TOKEN atau OWNER_ID tidak ditemukan! Periksa file .env Anda.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Inisialisasi user_map
    application.bot_data['user_map'] = {}

    # Daftarkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_tx_hash", send_tx_hash_prompt))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🤖 Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
