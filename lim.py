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
    JobQueue # Import JobQueue explicitly
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

# Main keyboard
main_menu_keyboard = [
    ["/start"],
    ["/send_tx_hash"],
    ["/send_picture_proof"],
    ["/buy_testnet_faucet"],
    ["/script_access_on_github"] # Updated menu item name
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)

# Message content for the scheduled faucet list
FAUCET_LIST_MESSAGE = (
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


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds to the /start command from the user."""
    user_name = update.effective_user.first_name
    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(update.effective_user.id)
    logger.info(f"User {user_name} (ID: {update.effective_user.id}) started the bot and added to all_users.")

    await update.message.reply_text(
        f"Hello {user_name}! Please select an option from the menu below.",
        reply_markup=main_menu_markup,
    )

# /send_tx_hash command
async def send_tx_hash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user to send a transaction hash."""
    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(update.effective_user.id)
    await update.message.reply_text(
        "Please send your blockchain transaction hash proof\n"
        "Example: tx hash : 0x123abc..."
    )

# /send_picture_proof command
async def send_picture_proof_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user to send a picture proof."""
    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(update.effective_user.id)
    await update.message.reply_text(
        "Please send your picture proof."
    )

# /buy_testnet_faucet command
async def buy_testnet_faucet_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays testnet faucet options and payment methods."""
    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(update.effective_user.id)
    await update.message.reply_text(FAUCET_LIST_MESSAGE)

# /script_access_on_github command (renamed function)
async def script_access_on_github_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user for payment to gain script access on GitHub."""
    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(update.effective_user.id)
    message = (
        "Please send 1.6 $Usdt or $Usdc to this address: 0xf01fb9a6855f175d3f3e28e00fa617009c38ef59\n\n"
        "And send transaction proof by selecting the /send_tx_hash menu and the /send_picture_proof menu."
    )
    await update.message.reply_text(message)


# Handle photo
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages containing photos (transaction proofs)."""
    user = update.effective_user

    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(user.id)

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

    # Add user to the set of all users
    context.bot_data.setdefault('all_users', set()).add(user.id)

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
        # Check if the message is a digit (e.g., '1', '2', '3')
        elif text.isdigit():
            # Respond with the purchase detail prompt
            await update.message.reply_text(
                "Please fill in the details\n"
                "Select Faucet Number or Name: \n"
                "Purchase Quantity: \n"
                "Payment Method: ",
                reply_markup=main_menu_markup # Keep the menu visible
            )
        else:
            # If it's any other text message from the user, forward it to the owner
            forwarded_message = await context.bot.forward_message(
                chat_id=OWNER_ID,
                from_chat_id=chat_id,
                message_id=update.message.message_id
            )
            logger.info(f"General text message from {user.full_name} (ID: {user.id}) forwarded to owner. Forwarded Message ID: {forwarded_message.message_id}")
            context.bot_data['user_map'][forwarded_message.message_id] = user.id

            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"⬆️ The message above is from: {user.full_name} (ID: {user.id})"
            )
            await update.message.reply_text(
                "Your message has been forwarded to the owner. Thank you!",
                reply_markup=main_menu_markup
            )

# Scheduled function to send faucet list
async def send_scheduled_faucet_list(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the faucet list message to all known users."""
    if 'all_users' in context.bot_data:
        for user_id in list(context.bot_data['all_users']): # Iterate over a copy to allow modification if users block
            try:
                await context.bot.send_message(chat_id=user_id, text=FAUCET_LIST_MESSAGE)
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
    logger.info("user_map and all_users initialized.")

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_tx_hash", send_tx_hash_prompt))
    application.add_handler(CommandHandler("send_picture_proof", send_picture_proof_prompt))
    application.add_handler(CommandHandler("buy_testnet_faucet", buy_testnet_faucet_prompt))
    application.add_handler(CommandHandler("script_access_on_github", script_access_on_github_prompt)) # Updated handler registration
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
