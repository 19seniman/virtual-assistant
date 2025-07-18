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

# Muat variabel dari file .env
load_dotenv()

# Ambil token dan ID pemilik dari environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

# Konfigurasi logging untuk melihat error
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Definisikan keyboard menu
main_menu_keyboard = [
    ["/start"],
    ["/Send your Tx Hash"]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)

# Fungsi untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Halo {user_name}! Kirimkan saya gambar sebagai bukti transaksi Anda.\n\n"
        "Menu diaktifkan! Gunakan tombol di bawah.",
        reply_markup=main_menu_markup,
    )

# Fungsi untuk perintah /Send your Tx Hash
async def send_tx_hash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Silahkan kirim bukti tx hash on blockchain transaction\n"
        "contoh : tx hash : 0x123abc..."
    )

# Fungsi untuk menangani gambar yang dikirim pengguna
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    forwarded_message = await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=user.id,
        message_id=update.message.message_id,
    )
    
    # Simpan mapping: ID pesan di chat pemilik -> ID pengguna asli
    context.bot_data['user_map'][forwarded_message.message_id] = user.id
    
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"⬆️ Gambar di atas dikirim oleh: {user.full_name} (ID: {user.id})"
    )

    await update.message.reply_text(
        "Gambar Anda telah diterima dan diteruskan. Terima kasih!",
        reply_markup=main_menu_markup
    )

# [DIPERBAIKI] Fungsi untuk menangani semua pesan teks
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    text = update.message.text
    user = update.effective_user

    # KONDISI 1: Pesan adalah balasan dari PEMILIK
    if str(chat_id) == OWNER_ID and update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        
        # Cari ID pengguna asli dari 'memori' bot
        original_user_id = context.bot_data['user_map'].get(replied_msg_id)
        
        if original_user_id:
            try:
                await context.bot.send_message(
                    chat_id=original_user_id,
                    text=f"Pesan balasan dari pemilik:\n\n➡️ {text}"
                )
                await update.message.reply_text("✅ Balasan berhasil dikirim.")
                # Hapus mapping setelah berhasil dibalas agar memori tidak penuh
                del context.bot_data['user_map'][replied_msg_id]
            except Exception as e:
                logger.error(f"Gagal mengirim balasan ke {original_user_id}: {e}")
                await update.message.reply_text(f"Gagal mengirim balasan: {e}")
            return
        else:
            # [BARU] Beri tahu pemilik jika mereka membalas pesan yang salah
            await update.message.reply_text(
                "❌ Gagal menemukan pengguna asli.\n\n"
                "Pastikan Anda membalas (reply) langsung ke **pesan gambar/hash** yang diteruskan, "
                "bukan pesan teks konfirmasi dari bot."
            )
            return

    # KONDISI 2: Pesan dari PENGGUNA berisi "tx hash :"
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
        return

# Fungsi utama untuk menjalankan bot
def main() -> None:
    if not BOT_TOKEN or not OWNER_ID:
        logger.error("BOT_TOKEN atau OWNER_ID tidak ditemukan! Pastikan file .env sudah benar.")
        return
        
    application = Application.builder().token(BOT_TOKEN).build()

    if 'user_map' not in application.bot_data:
        application.bot_data['user_map'] = {}

    # Daftarkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("Send_your_Tx_Hash", send_tx_hash_prompt))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot sedang berjalan dengan kode final...")
    application.run_polling()

if __name__ == "__main__":
    main()
