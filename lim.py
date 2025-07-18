import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

# Fungsi untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan dan menampilkan menu utama."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Halo {user_name}! Kirimkan saya gambar sebagai bukti transaksi Anda.\n\n"
        "Menu diaktifkan! Gunakan tombol di bawah.",
        reply_markup=main_menu_markup,
    )

# Fungsi untuk perintah /Send your Tx Hash
async def send_tx_hash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memberikan instruksi untuk mengirim tx hash."""
    await update.message.reply_text(
        "Silahkan kirim bukti tx hash on blockchain transaction\n"
        "contoh : tx hash : 0x123abc...",
        # Menghapus keyboard jika tidak ingin ditampilkan setelah perintah ini
        # reply_markup=ReplyKeyboardRemove()
    )

# Fungsi untuk menangani gambar yang dikirim pengguna
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Meneruskan gambar ke pemilik dan menyimpan data pengguna."""
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    # Simpan ID pengguna di user_data untuk membalas nanti
    # Forwarded message sudah berisi info pengirim asli, jadi ini cara alternatif
    context.user_data['original_user_id'] = user_id

    # Forward foto ke pemilik
    await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id,
    )
    
    # Beri tahu pemilik siapa pengirimnya
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"Gambar di atas dikirim oleh: {user_name} (ID: {user_id})"
    )

    # Konfirmasi ke pengguna dan tampilkan menu lagi
    await update.message.reply_text(
        "Gambar Anda telah diterima dan diteruskan. Terima kasih!",
        reply_markup=main_menu_markup
    )

# Fungsi untuk menangani semua pesan teks
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani balasan dari pemilik dan pesan tx hash dari pengguna."""
    chat_id = update.message.chat_id
    text = update.message.text
    user = update.effective_user

    # KONDISI 1: Pesan adalah balasan dari PEMILIK
    # Cek jika pengirim adalah pemilik dan pesan ini adalah balasan (reply)
    if str(chat_id) == OWNER_ID and update.message.reply_to_message:
        # Jika pemilik membalas pesan yang diteruskan (forwarded)
        if update.message.reply_to_message.forward_from:
            original_user_id = update.message.reply_to_message.forward_from.id
            await context.bot.send_message(
                chat_id=original_user_id,
                text=f"Pesan dari pemilik:\n\n{text}"
            )
            await update.message.reply_text("✅ Balasan berhasil dikirim.")
            return

    # KONDISI 2: Pesan dari PENGGUNA berisi "tx hash :"
    if "tx hash :" in text.lower():
        # Teruskan pesan ini ke pemilik
        await context.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=chat_id,
            message_id=update.message.message_id
        )
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"Pesan hash di atas dari: {user.full_name} (ID: {user.id})"
        )
        await update.message.reply_text(
            "Pesan hash Anda telah diteruskan ke pemilik.",
            reply_markup=main_menu_markup
        )
        return

# Fungsi utama untuk menjalankan bot
def main() -> None:
    """Jalankan bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN tidak ditemukan! Pastikan file .env sudah benar.")
        return
    if not OWNER_ID:
        logger.error("OWNER_ID tidak ditemukan! Pastikan file .env sudah benar.")
        return
        
    # Buat aplikasi bot
    application = Application.builder().token(BOT_TOKEN).build()

    # Daftarkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("Send_your_Tx_Hash", send_tx_hash_prompt))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Jalankan bot sampai dihentikan (misal: Ctrl+C)
    logger.info("Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
