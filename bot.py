import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
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

# States for Edit Post Conversation
EDIT_SELECT, EDIT_TITLE, EDIT_DESCRIPTION, EDIT_LINK, EDIT_CONTENT = range(5)

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
        ["Add New Post", "View All Posts"],
        ["Manage Posts"]
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

    keyboard = []
    for post in posts:
        post_id, title, description, link, content, created_at = post
        keyboard.append([InlineKeyboardButton(title, callback_data=f"view_post_{post_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Welcome! Here are the latest blog posts ({len(posts)}). Click a title to read more:", reply_markup=reply_markup)

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

# --- Manage Posts Handlers ---

async def manage_posts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists posts with Edit/Delete buttons."""
    user_id = update.effective_user.id
    if not database.is_admin(user_id):
        await update.message.reply_text("You are not authorized to perform this action.")
        return

    posts = database.get_all_posts()
    if not posts:
        await update.message.reply_text("No posts to manage.")
        return

    await update.message.reply_text("Select a post to manage:")
    
    for post in posts:
        post_id, title, description, link, content, created_at = post
        keyboard = [
            [
                InlineKeyboardButton("Edit", callback_data=f"edit_{post_id}"),
                InlineKeyboardButton("Delete", callback_data=f"delete_{post_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"<b>{title}</b>\n{created_at}", reply_markup=reply_markup, parse_mode="HTML")

async def post_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles Edit, Delete, and View Post button clicks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("view_post_"):
        _, _, post_id = data.split('_')
        post_id = int(post_id)
        post = database.get_post(post_id)
        
        if not post:
            await query.edit_message_text("This post no longer exists.")
            return

        post_id, title, description, link, content, created_at = post
        message = (
            f"<b>{title}</b>\n\n"
            f"<i>{description}</i>\n\n"
            f"{content}\n\n"
            f"<a href='{link}'>Read More</a>\n"
            f"Date: {created_at}"
        )
        # Send as a new message so the menu stays
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="HTML")
        return

    action, post_id = data.split('_')
    post_id = int(post_id)

    if action == "delete":
        if database.delete_post(post_id):
            await query.edit_message_text(f"Post deleted successfully.")
        else:
            await query.edit_message_text("Failed to delete post.")
            
    elif action == "edit":
        # Start Edit Conversation manually? 
        # Since CallbackQueryHandler can't directly start a ConversationHandler entry point easily if it's not set up that way.
        # But we can trigger it if we set up the entry point to accept callback queries.
        # However, for simplicity, let's just tell the user what to do or use a different approach.
        # Actually, we can use context.user_data to store the post_id and then transition.
        # But `edit_post_start` needs to be triggered.
        # Let's try to make the ConversationHandler accept the callback query as entry point.
        pass # Handled by ConversationHandler entry points

# --- Edit Post Conversation ---

async def edit_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    _, post_id = data.split('_')
    context.user_data['edit_post_id'] = int(post_id)
    
    post = database.get_post(int(post_id))
    if not post:
        await query.edit_message_text("Post not found.")
        return ConversationHandler.END
        
    post_id, title, description, link, content, created_at = post
    
    await query.edit_message_text(
        f"Editing Post: <b>{title}</b>\n\n"
        "Please enter the new <b>Title</b> (or send . to keep current):",
        parse_mode="HTML"
    )
    return EDIT_TITLE

async def edit_received_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text != '.':
        context.user_data['edit_title'] = text
    else:
        # Fetch original if not changed? 
        # We need to fetch original again or store it. Let's fetch to be safe.
        post = database.get_post(context.user_data['edit_post_id'])
        context.user_data['edit_title'] = post[1]
        
    await update.message.reply_text("Enter new <b>Description</b> (or . to keep current):", parse_mode="HTML")
    return EDIT_DESCRIPTION

async def edit_received_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text != '.':
        context.user_data['edit_description'] = text
    else:
        post = database.get_post(context.user_data['edit_post_id'])
        context.user_data['edit_description'] = post[2]

    await update.message.reply_text("Enter new <b>Link</b> (or . to keep current):", parse_mode="HTML")
    return EDIT_LINK

async def edit_received_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text != '.':
        context.user_data['edit_link'] = text
    else:
        post = database.get_post(context.user_data['edit_post_id'])
        context.user_data['edit_link'] = post[3]

    await update.message.reply_text("Enter new <b>Content</b> (or . to keep current):", parse_mode="HTML")
    return EDIT_CONTENT

async def edit_received_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text != '.':
        context.user_data['edit_content'] = text
    else:
        post = database.get_post(context.user_data['edit_post_id'])
        context.user_data['edit_content'] = post[4]
        
    # Update DB
    database.update_post(
        context.user_data['edit_post_id'],
        context.user_data['edit_title'],
        context.user_data['edit_description'],
        context.user_data['edit_link'],
        context.user_data['edit_content']
    )
    
    await update.message.reply_text("Post updated successfully!")
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

    # Edit Post Conversation
    edit_post_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_post_start, pattern="^edit_")],
        states={
            EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_received_title)],
            EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_received_description)],
            EDIT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_received_link)],
            EDIT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_received_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(add_post_conv)
    application.add_handler(add_admin_conv)
    application.add_handler(edit_post_conv)
    
    application.add_handler(MessageHandler(filters.Regex("^Manage Posts$"), manage_posts_handler))
    application.add_handler(CallbackQueryHandler(post_action_callback, pattern="^delete_|^view_post_"))
    
    application.add_handler(MessageHandler(filters.Regex("^View All Posts$"), view_posts_handler))
    application.add_handler(CommandHandler("start", start))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
