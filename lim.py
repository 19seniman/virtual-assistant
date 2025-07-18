import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    JobQueue,
    CallbackQueryHandler
)
from telegram.error import Forbidden # Import Forbidden to handle blocked users

# Load environment variables from .env file
load_dotenv()

# Get bot token and owner ID from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")  # Must be in string format

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Main keyboard definition (will be stored in bot_data)
# This definition remains here for clarity, but the actual object used will be from bot_data
_main_menu_keyboard_definition = [
    ["/start"],
    ["/send_tx_hash"],
    ["/send_picture_proof"],
    ["/buy_testnet_faucet"],
    ["/script_access_on_github"]
]

# Define all messages in both Indonesian and English
MESSAGES = {
    "id": {
        "start_greeting": "Halo {user_name}! Silakan pilih bahasa Anda.",
        "welcome_menu": "Halo {user_name}! Silakan pilih opsi dari menu di bawah ini.",
        "tx_hash_prompt": "Silakan kirim bukti tx hash transaksi blockchain Anda\nContoh: tx hash : 0x123abc...",
        "picture_proof_prompt": "Silakan kirimkan bukti gambar.",
        "photo_received_owner": "⬆️ Gambar di atas dikirim oleh: {user_full_name} (ID: {user_id})",
        "photo_received_user": "Gambar Anda telah diterima dan diteruskan ke pemilik. Terima kasih!",
        "reply_from_owner": "📩 Balasan dari pemilik:\n\n{text}",
        "reply_sent_success": "✅ Balasan berhasil dikirim ke pengguna asli.",
        "reply_send_fail": "❌ Gagal mengirim balasan: {error}",
        "hash_received_owner": "⬆️ Pesan hash di atas dari: {user_full_name} (ID: {user_id})",
        "hash_received_user": "Pesan hash Anda telah diteruskan ke pemilik.",
        "unknown_text_forwarded_owner": "⬆️ Pesan di atas dari: {user_full_name} (ID: {user_id})",
        "unknown_text_forwarded_user": "Pesan Anda telah diteruskan ke pemilik. Terima kasih!",
        "purchase_details_prompt": "Silakan isi keterangan\n▫️Pilih Nomor atau nama Faucetnya :\n▫️Jumlah Pembelian :\n▫️Alamat Wallet kamu :\n▫️Metode Pembayaran :",
        "invalid_text_message": "Maaf, saya hanya bisa menerima gambar sebagai bukti transaksi, pesan dalam format 'tx hash : [hash Anda]', atau angka untuk pembelian faucet.\n\nSilakan gunakan menu di bawah ini.",
        "script_access_prompt": (
            "Silakan kirim 1.6 $Usdt atau $Usdc ke alamat ini: 0xf01fb9a6855f175d3f3e28e00fa617009c38ef59\n\n"
            "Dan kirimkan bukti transaksi dengan memilih menu /send_tx_hash dan menu /send_picture_proof."
        ),
        "faucet_list_message": (
            "🟢Ready Faucet :\n\n"
            "1. Monad Testnet 🔁 Rp. 1.200 | 0.074 $Usdt or $Usdc / 1\n"
            "2. ETH Sepolia 🔁 Rp. 4500 | 0.28 $Usdt or $Usdc / 1\n"
            "3. Somnia/stt Testnet 🔁 Rp. 450 | 0.031 $Usdt or $Usdc / 1\n"
            "4. Pharos Testnet 🔁 Rp. 600 | 0.037 $Usdt or $Usdc / 1\n"
            "5. Sui Testnet 🔁 Rp 350 | 0.021 $Usdt or $Usdc / 1\n"
            "6. 0G Testnet >> Coming soon..\n\n"
            "🛗 Payment Method\n"
            "⏺ Dana : 085275232733 | A/N : Hardianti\n"
            "⏺ Crypto : USDT & USDC | ➡️wallet address: 0xa138031dc7ea75c464364ed1a6d1cb3b510ff630\n\n"
            "Silakan pilih nomor 1,2,3,4,5,6... jika kamu ingin membeli."
        )
    },
    "en": {
        "start_greeting": "Hello {user_name}! Please select your language.",
        "welcome_menu": "Hello {user_name}! Please select an option from the menu below.",
        "tx_hash_prompt": "Please send your blockchain transaction hash proof\nExample: tx hash : 0x123abc...",
        "picture_proof_prompt": "Please send your picture proof.",
        "photo_received_owner": "⬆️ The photo above was sent by: {user_full_name} (ID: {user_id})",
        "photo_received_user": "Your photo has been received and forwarded to the owner. Thank you!",
        "reply_from_owner": "📩 Reply from owner:\n\n{text}",
        "reply_sent_success": "✅ Reply sent successfully to the original user.",
        "reply_send_fail": "❌ Failed to send reply: {error}",
        "hash_received_owner": "⬆️ The hash message above is from: {user_full_name} (ID: {user_id})",
        "hash_received_user": "Your hash message has been forwarded to the owner.",
        "unknown_text_forwarded_owner": "⬆️ The message above is from: {user_full_name} (ID: {user_id})",
        "unknown_text_forwarded_user": "Your message has been forwarded to the owner. Thank you!",
        "purchase_details_prompt": "Please fill in the details\n▫️Select Faucet Number or Name :\n▫️Purchase Quantity :\n▫️Your Wallet Address :\n▫️Payment Method :",
        "invalid_text_message": "Sorry, I can only accept images as transaction proof, messages in the format 'tx hash : [your hash]', or a number for faucet purchase.\n\nPlease use the menu below.",
        "script_access_prompt": (
            "Please send 1.6 $Usdt or $Usdc to this address: 0xf01fb9a6855f175d3f3e28e00fa617009c38ef59\n\n"
            "And send transaction proof by selecting the /send_tx_hash menu and the /send_picture_proof menu."
        ),
        "faucet_list_message": (
            "🟢Ready Faucet :\n\n"
            "1. Monad Testnet 🔁 Rp. 1.200 | 0.074 $Usdt or $Usdc / 1\n"
            "2. ETH Sepolia 🔁 Rp. 4500 | 0.28 $Usdt or $Usdc / 1\n"
            "3. Somnia/stt Testnet 🔁 Rp. 450 | 0.031 $Usdt or $Usdc / 1\n"
            "4. Pharos Testnet 🔁 Rp. 600 | 0.037 $Usdt or $Usdc / 1\n"
            "5. Sui Testnet 🔁 Rp 350 | 0.021 $Usdt or $Usdc / 1\n"
            "6. 0G Testnet >> Coming soon..\n\n"
            "🛗 Payment Method\n"
            "⏺ Dana : 085275232733 | A/N : Hardianti\n"
            "⏺ Crypto : USDT & USDC | ➡️wallet address: 0xa138031dc7ea75c464364ed1a6d1cb3b510ff630\n\n"
            "Please select number 1,2,3,4,5,6... if you wish to purchase."
        )
    }
}

# Global variable for the application instance (will be set in main)
application = None

def get_message(user_id: int, key: str, **kwargs) -> str:
    """Retrieves a message in the user's preferred language."""
    # Default to English if language not set or invalid
    user_lang = application.bot_data.get('user_languages', {}).get(user_id, 'en')
    
    # Fallback to English if the key is not found in the selected language
    message_template = MESSAGES.get(user_lang, MESSAGES['en']).get(key, MESSAGES['en'].get(key, f"Error: Message key '{key}' not found."))
    return message_template.format(**kwargs)


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Presents language selection or welcomes the user based on existing language preference."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Add user to the set of all users for scheduled messages
    context.bot_data.setdefault('all_users', set()).add(user_id)

    # Check if user already has a language preference
    if user_id in context.bot_data.get('user_languages', {}):
        await update.message.reply_text(
            get_message(user_id, "welcome_menu", user_name=user_name),
            reply_markup=context.bot_data['main_menu_markup'], # Access from bot_data
        )
    else:
        # Offer language selection
        keyboard = [
            [InlineKeyboardButton("Bahasa Indonesia", callback_data='lang_id')],
            [InlineKeyboardButton("English", callback_data='lang_en')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            get_message(user_id, "start_greeting", user_name=user_name), # Use a generic greeting for language selection
            reply_markup=reply_markup
        )

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses for language selection."""
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    await query.answer() # Acknowledge the callback query

    if query.data.startswith('lang_'):
        selected_lang = query.data.split('_')[1]
        context.bot_data.setdefault('user_languages', {})[user_id] = selected_lang
        logger.info(f"User {user_name} (ID: {user_id}) selected language: {selected_lang}")

        # Edit the message to remove the language selection buttons and show the welcome message
        await query.edit_message_text(
            text=get_message(user_id, "welcome_menu", user_name=user_name),
            reply_markup=context.bot_data['main_menu_markup'] # Access from bot_data
        )


# /send_tx_hash command
async def send_tx_hash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user to send a transaction hash."""
    user_id = update.effective_user.id
    context.bot_data.setdefault('all_users', set()).add(user_id)
    await update.message.reply_text(
        get_message(user_id, "tx_hash_prompt")
    )

# /send_picture_proof command
async def send_picture_proof_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user to send a picture proof."""
    user_id = update.effective_user.id
    context.bot_data.setdefault('all_users', set()).add(user_id)
    await update.message.reply_text(
        get_message(user_id, "picture_proof_prompt")
    )

# /buy_testnet_faucet command
async def buy_testnet_faucet_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays testnet faucet options and payment methods."""
    user_id = update.effective_user.id
    context.bot_data.setdefault('all_users', set()).add(user_id)
    await update.message.reply_text(get_message(user_id, "faucet_list_message"))

# /script_access_on_github command
async def script_access_on_github_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user for payment to gain script access on GitHub."""
    user_id = update.effective_user.id
    context.bot_data.setdefault('all_users', set()).add(user_id)
    await update.message.reply_text(get_message(user_id, "script_access_prompt"))


# Handle photo
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages containing photos (transaction proofs)."""
    user = update.effective_user
    user_id = user.id

    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(user_id)

    # Initialize user_map to store forwarded message_id to original user's chat_id mapping.
    context.bot_data.setdefault('user_map', {})

    # Forward the photo to the bot owner
    forwarded_message = await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=user_id,
        message_id=update.message.message_id,
    )
    logger.info(get_message(user_id, "photo_received_owner", user_full_name=user.full_name, user_id=user_id) + f" Forwarded Message ID: {forwarded_message.message_id}")

    # Store the original user's ID with the forwarded message's ID as the key
    context.bot_data['user_map'][forwarded_message.message_id] = user_id

    # Inform the owner that the photo has been received
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=get_message(user_id, "photo_received_owner", user_full_name=user.full_name, user_id=user_id)
    )

    # Inform the user that the photo has been forwarded
    await update.message.reply_text(
        get_message(user_id, "photo_received_user"),
        reply_markup=context.bot_data['main_menu_markup'] # Access from bot_data
    )

# Handle text messages
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages, both from regular users and replies from the owner."""
    chat_id = update.message.chat_id
    text = update.message.text
    user = update.effective_user
    user_id = user.id

    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(user_id)

    # Initialize user_map
    context.bot_data.setdefault('user_map', {})

    # --- Handle replies from the bot owner ---
    # If the message is from the OWNER_ID and is a reply to another message
    if str(chat_id) == OWNER_ID and update.message.reply_to_message:
        logger.info(f"Owner {user.full_name} (ID: {user.id}) replied to a message.")
        logger.info(f"Replied Message ID: {update.message.reply_to_message.message_id}")
        logger.info(f"Sender of Replied Message: {update.message.reply_to_message.from_user.full_name if update.message.reply_to_message.from_user else 'None'}")

        replied_msg_id = update.message.reply_to_message.message_id
        original_user_id = context.bot_data['user_map'].get(replied_msg_id)

        if original_user_id:
            try:
                # Send the reply to the original user
                await context.bot.send_message(
                    chat_id=original_user_id,
                    text=get_message(original_user_id, "reply_from_owner", text=text)
                )
                await update.message.reply_text(get_message(chat_id, "reply_sent_success"))
                logger.info(f"Successfully sent reply to user ID: {original_user_id}.")
            except Exception as e:
                logger.error(get_message(original_user_id, "reply_send_fail", error=e))
                await update.message.reply_text(get_message(chat_id, "reply_send_fail", error=e))
            return # Exit the function after handling the owner's reply

    # --- Handle messages from regular users ---
    # If the message is not from the owner (or not a reply from the owner)
    if str(chat_id) != OWNER_ID:
        # If the message contains "tx hash :"
        if "tx hash :" in text.lower():
            # Forward the hash message to the bot owner
            forwarded_message = await context.bot.forward_message(
                chat_id=OWNER_ID,
                from_chat_id=chat_id,
                message_id=update.message.message_id
            )
            logger.info(get_message(user_id, "hash_received_owner", user_full_name=user.full_name, user_id=user_id) + f" Forwarded Message ID: {forwarded_message.message_id}")
            # Store the original user's ID
            context.bot_data['user_map'][forwarded_message.message_id] = user_id

            # Inform the owner
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=get_message(user_id, "hash_received_owner", user_full_name=user.full_name, user_id=user.id)
            )

            # Inform the user
            await update.message.reply_text(
                get_message(user_id, "hash_received_user"),
                reply_markup=context.bot_data['main_menu_markup'] # Access from bot_data
            )
        # Check if the message is a digit (e.g., '1', '2', '3')
        elif text.isdigit():
            # Respond with the purchase detail prompt
            await update.message.reply_text(
                get_message(user_id, "purchase_details_prompt"),
                reply_markup=context.bot_data['main_menu_markup'] # Keep the menu visible
            )
        else:
            # If it's any other text message from the user, forward it to the owner
            forwarded_message = await context.bot.forward_message(
                chat_id=OWNER_ID,
                from_chat_id=chat_id,
                message_id=update.message.message_id
            )
            logger.info(get_message(user_id, "unknown_text_forwarded_owner", user_full_name=user.full_name, user_id=user.id) + f" Forwarded Message ID: {forwarded_message.message_id}")
            context.bot_data['user_map'][forwarded_message.message_id] = user_id

            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=get_message(user_id, "unknown_text_forwarded_owner", user_full_name=user.full_name, user_id=user.id)
            )
            await update.message.reply_text(
                get_message(user_id, "unknown_text_forwarded_user"),
                reply_markup=context.bot_data['main_menu_markup'] # Access from bot_data
            )

# Scheduled function to send faucet list
async def send_scheduled_faucet_list(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the faucet list message to all known users."""
    if 'all_users' in context.bot_data:
        for user_id in list(context.bot_data['all_users']): # Iterate over a copy to allow modification if users block
            try:
                await context.bot.send_message(chat_id=user_id, text=get_message(user_id, "faucet_list_message"))
                logger.info(f"Sent scheduled faucet list to user ID: {user_id}")
            except Forbidden:
                # User blocked the bot, remove them from the list
                context.bot_data['all_users'].remove(user_id)
                logger.warning(f"User ID: {user_id} blocked the bot. Removed from scheduled messages.")
            except Exception as e:
                logger.error(f"Failed to send scheduled faucet list to user ID: {user_id}: {e}")

# Main function
def main() -> None:
    """Main function to run the bot."""
    global application # Declare application as global to be accessible by get_message

    if not BOT_TOKEN or not OWNER_ID:
        logger.error("BOT_TOKEN or OWNER_ID not found! Please ensure they are set in your .env file.")
        return

    # Create a JobQueue instance
    job_queue_instance = JobQueue()

    # Build the Application and pass the JobQueue instance to it
    application = Application.builder().token(BOT_TOKEN).job_queue(job_queue_instance).build()

    # Initialize user_map and all_users in application.bot_data to persist across handlers
    application.bot_data['user_map'] = {}
    application.bot_data['all_users'] = set() # Use a set to store unique user IDs
    application.bot_data['user_languages'] = {} # Store user language preferences
    # Store the main_menu_markup in bot_data for easy access
    application.bot_data['main_menu_markup'] = ReplyKeyboardMarkup(_main_menu_keyboard_definition, resize_keyboard=True, one_time_keyboard=False)
    logger.info("user_map, all_users, user_languages, and main_menu_markup initialized.")

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback_handler)) # Handler for inline button presses
    application.add_handler(CommandHandler("send_tx_hash", send_tx_hash_prompt))
    application.add_handler(CommandHandler("send_picture_proof", send_picture_proof_prompt))
    application.add_handler(CommandHandler("buy_testnet_faucet", buy_testnet_faucet_prompt))
    application.add_handler(CommandHandler("script_access_on_github", script_access_on_github_prompt))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    # Handle text messages that are not commands
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Get the JobQueue instance (which is now correctly set)
    job_queue = application.job_queue

    # Schedule the recurring message every 8 hours (28800 seconds)
    job_queue.run_repeating(send_scheduled_faucet_list, interval=28800, first=5) # first=5 to send first message 5 seconds after start
    logger.info("Scheduled faucet list message to run every 8 hours.")

    logger.info("🤖 Bot is running...")
    # Start polling to receive updates
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
