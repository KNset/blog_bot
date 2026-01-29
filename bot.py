import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import database

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = "8455626898:AAE559TsQ1JXsYJqNsEeLuLtuBzyeaHQuHk"
INITIAL_ADMIN_ID = 1278018722

# States for Add Post Conversation
TITLE, DESCRIPTION, LINK, CONTENT = range(4)

# States for Add Admin Conversation
NEW_ADMIN_ID = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the bot and shows options based on user role."""
    user = update.effective_user
    user_id = user.id
    
    if database.is_admin(user_id):
        await show_admin_menu(update, context)
    else:
        await show_user_menu(update, context)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    keyboard = [
        ["Add New Post", "View All Posts"]
    ]
    
    # Only the initial admin (Super Admin) can see the "Add New Admin" button
    if user_id == INITIAL_ADMIN_ID:
        keyboard.append(["Add New Admin"])
        
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome Admin! What would you like to do?",
        reply_markup=reply_markup
    )

async def show_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    posts = database.get_all_posts()
    if not posts:
        await update.message.reply_text("Welcome! There are no blog posts yet. Stay tuned!")
        return

    await update.message.reply_text(f"Welcome! Here are the latest blog posts ({len(posts)}):")
    for post in posts:
        title, description, link, content, created_at = post
        message = (
            f"<b>{title}</b>\n\n"
            f"<i>{description}</i>\n\n"
            f"{content}\n\n"
            f"<a href='{link}'>Read More</a>\n"
            f"Date: {created_at}"
        )
        await update.message.reply_html(message)

# --- Add Post Conversation ---

async def add_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not database.is_admin(user_id):
        await update.message.reply_text("You are not authorized to perform this action.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Let's create a new blog post.\n"
        "Please enter the <b>Title</b> of the post:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    return TITLE

async def received_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['post_title'] = update.message.text
    await update.message.reply_text("Got it. Now please enter the <b>Description</b> (short summary):", parse_mode="HTML")
    return DESCRIPTION

async def received_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['post_description'] = update.message.text
    await update.message.reply_text("Okay. Now please enter the <b>Link</b> to the full post/resource:", parse_mode="HTML")
    return LINK

async def received_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['post_link'] = update.message.text
    await update.message.reply_text("Almost done. Please enter the main <b>Content</b> or details for this post:", parse_mode="HTML")
    return CONTENT

async def received_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['post_content'] = update.message.text
    
    # Save to database
    database.add_post(
        context.user_data['post_title'],
        context.user_data['post_description'],
        context.user_data['post_link'],
        context.user_data['post_content']
    )
    
    await update.message.reply_text("Blog post created successfully!")
    await show_admin_menu(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    user_id = update.effective_user.id
    if database.is_admin(user_id):
        await show_admin_menu(update, context)
    else:
        await show_user_menu(update, context)
    return ConversationHandler.END

# --- Add Admin Conversation ---

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Check if user is the Super Admin
    if user_id != INITIAL_ADMIN_ID:
        await update.message.reply_text("You are not authorized to perform this action. Only the Super Admin can add new admins.")
        return ConversationHandler.END

    if not database.is_admin(user_id):
        await update.message.reply_text("You are not authorized to perform this action.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Please enter the <b>Telegram ID</b> of the new admin:\n"
        "(You can ask them to use @userinfobot to find their ID)",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    return NEW_ADMIN_ID

async def received_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_admin_id = int(update.message.text)
        if database.add_admin(new_admin_id):
            await update.message.reply_text(f"User {new_admin_id} has been added as an admin.")
        else:
            await update.message.reply_text("Failed to add admin. They might already be an admin.")
    except ValueError:
        await update.message.reply_text("Invalid ID. Please enter a numeric User ID.")
        return NEW_ADMIN_ID # Ask again

    await show_admin_menu(update, context)
    return ConversationHandler.END

# --- View Posts Handler (for Admin menu) ---
async def view_posts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_user_menu(update, context)
    # If admin, show menu again after listing posts so they don't get stuck
    if database.is_admin(update.effective_user.id):
        await show_admin_menu(update, context)


def main() -> None:
    """Run the bot."""
    # Initialize Database
    database.init_db(INITIAL_ADMIN_ID)
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add Post Conversation
    add_post_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Add New Post$"), add_post_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_description)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_link)],
            CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add Admin Conversation
    add_admin_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Add New Admin$"), add_admin_start)],
        states={
            NEW_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_admin_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(add_post_conv)
    application.add_handler(add_admin_conv)
    application.add_handler(MessageHandler(filters.Regex("^View All Posts$"), view_posts_handler))
    application.add_handler(CommandHandler("start", start))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
