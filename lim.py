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
# Pastikan Anda memiliki file .env di direktori yang sama dengan script ini,
# berisi BOT_TOKEN dan OWNER_ID Anda.
# Contoh:
# BOT_TOKEN=YOUR_BOT_TOKEN_HERE
# OWNER_ID=YOUR_TELEGRAM_USER_ID_HERE
load_dotenv()

# Ambil token bot dan ID pemilik dari environment variables
# OWNER_ID adalah ID numerik Telegram Anda.
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") # Pastikan ini adalah string (misal: "123456789")

# Konfigurasi logging untuk melihat pesan informasi dan error
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Definisikan keyboard menu untuk pengguna
# Perbaikan: Mengubah nama perintah agar konsisten dengan handler
main_menu_keyboard = [
    ["/start"],
    ["/send_tx_hash"] # Nama perintah yang lebih standar
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)

# Fungsi untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan dan menampilkan keyboard menu."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Halo {user_name}! Kirimkan saya gambar sebagai bukti transaksi Anda.\n\n"
        "Menu diaktifkan! Gunakan tombol di bawah.",
        reply_markup=main_menu_markup,
    )

# Fungsi untuk perintah /send_tx_hash
async def send_tx_hash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Meminta pengguna untuk mengirimkan bukti tx hash."""
    await update.message.reply_text(
        "Silahkan kirim bukti tx hash on blockchain transaction\n"
        "contoh : tx hash : 0x123abc..."
    )

# Fungsi untuk menangani gambar yang dikirim pengguna
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Menerima gambar dari pengguna, meneruskannya ke pemilik bot,
    dan menyimpan mapping antara ID pesan yang diteruskan dengan ID pengguna asli.
    """
    user = update.effective_user
    
    # Meneruskan pesan gambar ke chat pemilik bot
    forwarded_message = await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=user.id,
        message_id=update.message.message_id,
    )
    
    # Menyimpan mapping: ID pesan yang diteruskan di chat pemilik -> ID pengguna asli
    # Ini penting agar bot tahu siapa yang mengirim pesan asli saat pemilik membalas.
    context.bot_data['user_map'][forwarded_message.message_id] = user.id
    
    # Mengirim pesan tambahan ke pemilik untuk mengidentifikasi pengirim gambar
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"⬆️ Gambar di atas dikirim oleh: {user.full_name} (ID: {user.id})"
    )

    # Memberi tahu pengguna bahwa gambar telah diterima
    await update.message.reply_text(
        "Gambar Anda telah diterima dan diteruskan. Terima kasih!",
        reply_markup=main_menu_markup
    )

# Fungsi untuk menangani semua pesan teks
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Menangani pesan teks:
    1. Jika pemilik membalas pesan yang diteruskan (gambar/hash), balasan akan dikirim ke pengguna asli.
    2. Jika pengguna mengirim pesan berisi "tx hash :", pesan akan diteruskan ke pemilik.
    """
    chat_id = update.message.chat_id
    text = update.message.text
    user = update.effective_user

    # KONDISI 1: Pesan adalah balasan dari PEMILIK BOT
    # Memeriksa apakah pengirim adalah pemilik bot DAN pesan adalah balasan (reply)
    if str(chat_id) == OWNER_ID and update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        
        # Mencari ID pengguna asli dari 'memori' bot (user_map)
        # 'user_map' menyimpan ID pesan yang diteruskan sebagai kunci dan ID pengguna asli sebagai nilai.
        original_user_id = context.bot_data['user_map'].get(replied_msg_id)
        
        if original_user_id:
            try:
                # Mengirim balasan dari pemilik ke pengguna asli
                await context.bot.send_message(
                    chat_id=original_user_id,
                    text=f"Pesan balasan dari pemilik:\n\n➡️ {text}"
                )
                await update.message.reply_text("✅ Balasan berhasil dikirim.")
                # Hapus mapping setelah berhasil dibalas untuk menghemat memori.
                # Perlu diingat: ini berarti pemilik hanya bisa membalas sekali per pesan yang diteruskan.
                del context.bot_data['user_map'][replied_msg_id]
            except Exception as e:
                logger.error(f"Gagal mengirim balasan ke {original_user_id}: {e}")
                await update.message.reply_text(f"Gagal mengirim balasan: {e}")
            return # Keluar dari fungsi setelah menangani balasan pemilik
        else:
            # Beri tahu pemilik jika mereka membalas pesan yang tidak terdaftar
            await update.message.reply_text(
                "❌ Gagal menemukan pengguna asli.\n\n"
                "Pastikan Anda membalas (reply) langsung ke **pesan gambar/hash** yang diteruskan "
                "dari pengguna, bukan pesan teks konfirmasi dari bot."
            )
            return # Keluar dari fungsi

    # KONDISI 2: Pesan dari PENGGUNA berisi "tx hash :"
    # Ini menangani pesan teks dari pengguna yang mengandung frasa tertentu.
    if "tx hash :" in text.lower():
        # Meneruskan pesan hash ke chat pemilik bot
        forwarded_message = await context.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=chat_id,
            message_id=update.message.message_id
        )
        # Menyimpan mapping untuk pesan hash juga
        context.bot_data['user_map'][forwarded_message.message_id] = user.id

        # Mengirim pesan tambahan ke pemilik untuk mengidentifikasi pengirim hash
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"⬆️ Pesan hash di atas dari: {user.full_name} (ID: {user.id})"
        )
        # Memberi tahu pengguna bahwa pesan hash telah diteruskan
        await update.message.reply_text(
            "Pesan hash Anda telah diteruskan ke pemilik.",
            reply_markup=main_menu_markup
        )
        return # Keluar dari fungsi

# Fungsi utama untuk menjalankan bot
def main() -> None:
    """Menjalankan bot Telegram."""
    if not BOT_TOKEN or not OWNER_ID:
        logger.error("BOT_TOKEN atau OWNER_ID tidak ditemukan! Pastikan file .env sudah benar.")
        return
        
    application = Application.builder().token(BOT_TOKEN).build()

    # Inisialisasi 'user_map' jika belum ada.
    # Ini akan menyimpan mapping ID pesan yang diteruskan ke ID pengguna asli.
    if 'user_map' not in application.bot_data:
        application.bot_data['user_map'] = {}

    # Daftarkan handler untuk berbagai jenis pesan
    application.add_handler(CommandHandler("start", start))
    # Perbaikan: Menggunakan nama perintah yang konsisten
    application.add_handler(CommandHandler("send_tx_hash", send_tx_hash_prompt))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    # Menangani semua pesan teks yang bukan perintah
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot sedang berjalan dengan kode final...")
    # Memulai polling untuk menerima update dari Telegram
    application.run_polling()

if __name__ == "__main__":
    main()
