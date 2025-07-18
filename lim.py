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

# Main keyboard
main_menu_keyboard = [
    ["/start"],
    ["/send_tx_hash"],
    ["/send_picture_proof"]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds to the /start command from the user."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello {user_name}! Please select an option from the menu below.",
        reply_markup=main_menu_markup,
    )

# /send_tx_hash command
async def send_tx_hash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user to send a transaction hash."""
    await update.message.reply_text(
        "Please send your blockchain transaction hash proof\n"
        "Example: tx hash : 0x123abc..."
    )

# /send_picture_proof command
async def send_picture_proof_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user to send a picture proof."""
    await update.message.reply_text(
        "Please send your picture proof."
    )

# Handle photo
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages containing photos (transaction proofs)."""
    user = update.effective_user

    # Initialize user_map to store forwarded message_id to original user's chat_id mapping.
    context.bot_data.setdefault('user_map', {})

    # Forward the photo to the bot owner
    forwarded_message = await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=user.id,
        message_id=update.message.message_id,
    )
    logger.info(f"Photo from {user.full_name} (ID: {user.id}) forwarded to owner. Forwarded Message ID: {forwarded_message.message_id}")

    # Store the original user's ID with the forwarded message's ID as the key
    context.bot_data['user_map'][forwarded_message.message_id] = user.id

    # Inform the owner that the photo has been received
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"⬆️ The photo above was sent by: {user.full_name} (ID: {user.id})"
    )

    # Inform the user that the photo has been forwarded
    await update.message.reply_text(
        "Your photo has been received and forwarded to the owner. Thank you!",
        reply_markup=main_menu_markup
    )

# Handle text messages
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages, both from regular users and replies from the owner."""
    chat_id = update.message.chat_id
    text = update.message.text
    user = update.effective_user

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
                    text=f"📩 Reply from owner:\n\n{text}"
                )
                await update.message.reply_text("✅ Reply sent successfully to the original user.")
                logger.info(f"Successfully sent reply to user ID: {original_user_id}.")
            except Exception as e:
                logger.error(f"Failed to send reply to {original_user_id}: {e}")
                await update.message.reply_text(f"❌ Failed to send reply: {e}")
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
            logger.info(f"Hash message from {user.full_name} (ID: {user.id}) forwarded to owner. Forwarded Message ID: {forwarded_message.message_id}")
            # Store the original user's ID
            context.bot_data['user_map'][forwarded_message.message_id] = user.id

            # Inform the owner
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"⬆️ The hash message above is from: {user.full_name} (ID: {user.id})"
            )

            # Inform the user
            await update.message.reply_text(
                "Your hash message has been forwarded to the owner.",
                reply_markup=main_menu_markup
            )
        else:
            # Handle other text messages from users that are not hash messages or commands
            await update.message.reply_text(
                "Sorry, I can only accept images as transaction proof or messages in the format 'tx hash : [your hash]'.\n\n"
                "Please use the menu below.",
                reply_markup=main_menu_markup
            )

# Main function
def main() -> None:
    """Main function to run the bot."""
    if not BOT_TOKEN or not OWNER_ID:
        logger.error("BOT_TOKEN or OWNER_ID not found! Please ensure they are set in your .env file.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Initialize user_map in application.bot_data to persist across handlers
    application.bot_data['user_map'] = {}
    logger.info("user_map initialized.")

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_tx_hash", send_tx_hash_prompt))
    application.add_handler(CommandHandler("send_picture_proof", send_picture_proof_prompt))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    # Handle text messages that are not commands
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🤖 Bot is running...")
    # Start polling to receive updates
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
