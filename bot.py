import logging
import os
import asyncio
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants - Fixed for Render disk storage
# Render mounts persistent storage at /opt/render/project/.render
DB_DIR = "/opt/render/project/.render"
DB_PATH = os.path.join(DB_DIR, "airdrop_bot.db")

# Create directory if it doesn't exist
try:
    os.makedirs(DB_DIR, exist_ok=True)
    logger.info(f"Database directory created/verified: {DB_DIR}")
except PermissionError:
    # Fallback to project directory if no permission for /opt/render/project/.render
    DB_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(DB_DIR, "airdrop_bot.db")
    logger.info(f"Using project directory for database: {DB_DIR}")

# Task configuration - UPDATED WEBSITE LINK
TASKS = [
    {
        'id': 1,
        'name': 'Join Group',
        'description': 'Join our Telegram Group',
        'url': 'https://t.me/+UpEih_OErhA5YWZh',
        'button_text': '✅ Joined Group',
        'verification_text': 'Click below after joining'
    },
    {
        'id': 2,
        'name': 'Join Channel',
        'description': 'Join our Telegram Channel',
        'url': 'https://t.me/+aCyF_M3PeV42OWIx',
        'button_text': '✅ Joined Channel',
        'verification_text': 'Click below after joining'
    },
    {
        'id': 3,
        'name': 'Follow Twitter & Retweet',
        'description': 'Follow Twitter and retweet pinned post',
        'url': 'https://x.com/Freequencycoin',
        'button_text': '✅ Followed & Retweeted',
        'verification_text': 'Click below after following & retweeting'
    },
    {
        'id': 4,
        'name': 'Tweet',
        'description': 'Tweet about Freequency',
        'url': 'https://x.com/compose/tweet',
        'button_text': '✅ Tweeted',
        'verification_text': 'Click below after tweeting'
    },
    {
        'id': 5,
        'name': 'Visit Website',
        'description': 'Visit Frequency.com',
        'url': 'https://freequency.net/crypto',  # UPDATED URL
        'button_text': '✅ Visited Website',
        'verification_text': 'Click below after visiting'
    }
]

ADMINS = ['@dallen32', '@joyouschrs']

# Database setup
def init_db():
    """Initialize SQLite database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            current_step INTEGER DEFAULT 1,
            task1_completed INTEGER DEFAULT 0,
            task2_completed INTEGER DEFAULT 0,
            task3_completed INTEGER DEFAULT 0,
            task4_completed INTEGER DEFAULT 0,
            task5_completed INTEGER DEFAULT 0,
            wallet_address TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create user_progress table for better tracking
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id INTEGER,
            completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        conn.commit()
        logger.info(f"Database initialized successfully at {DB_PATH}")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

def get_db_connection():
    """Get database connection with retry logic"""
    try:
        return sqlite3.connect(DB_PATH)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

class UserManager:
    """Manages user data and progress"""
    
    @staticmethod
    def get_or_create_user(user_id, username, first_name):
        """Get existing user or create new one"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user exists
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # Create new user
                cursor.execute('''
                INSERT INTO users (user_id, username, first_name, joined_at, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name))
                conn.commit()
                logger.info(f"New user created: {user_id} (@{username})")
            else:
                # Update last active
                cursor.execute('''
                UPDATE users SET last_active = CURRENT_TIMESTAMP, username = ?, first_name = ?
                WHERE user_id = ?
                ''', (username, first_name, user_id))
                conn.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_user_progress(user_id):
        """Get user's current progress"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT current_step, task1_completed, task2_completed, task3_completed, 
                   task4_completed, task5_completed, wallet_address
            FROM users WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'current_step': result[0],
                    'tasks_completed': [bool(result[i]) for i in range(1, 6)],
                    'wallet_address': result[6]
                }
            return None
        finally:
            conn.close()
    
    @staticmethod
    def update_user_step(user_id, step):
        """Update user's current step"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE users SET current_step = ?, last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
            ''', (step, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user step: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def mark_task_completed(user_id, task_num):
        """Mark a specific task as completed"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'''
            UPDATE users SET task{task_num}_completed = 1, last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
            ''', (user_id,))
            
            # Also update current_step to next task
            if task_num < 5:
                cursor.execute('''
                UPDATE users SET current_step = ? WHERE user_id = ? AND current_step = ?
                ''', (task_num + 1, user_id, task_num))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking task completed: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def reset_user_progress(user_id):
        """Reset user's progress"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE users SET 
                current_step = 1,
                task1_completed = 0,
                task2_completed = 0,
                task3_completed = 0,
                task4_completed = 0,
                task5_completed = 0,
                wallet_address = NULL,
                last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting user progress: {e}")
            return False
        finally:
            conn.close()

# Bot Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or "NoUsername"
    first_name = user.first_name or "User"
    
    logger.info(f"User {user_id} (@{username}) started the bot")
    
    # Register user
    UserManager.get_or_create_user(user_id, username, first_name)
    
    # Get user progress
    progress = UserManager.get_user_progress(user_id)
    current_step = progress['current_step'] if progress else 1
    
    # Welcome message
    welcome_text = """
🤖 *Welcome to Freequency Airdrop Bot* 🤖

💰 *Earn 100 FREQC tokens* by completing simple social tasks!

📋 *How it works:*
1. Complete tasks in order (one after another)
2. Each task must be verified before moving to next
3. After all tasks, contact admins with proof
4. Receive your 100 FREQC reward!

*Note:* Tasks must be completed sequentially. You cannot skip any task.

Click below to begin! 👇
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Start Tasks", callback_data="start_tasks")],
        [InlineKeyboardButton("📊 My Progress", callback_data="check_progress")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_task_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, task_number: int, user_id: int = None):
    """Display a specific task to user"""
    if not user_id:
        user_id = update.effective_user.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    if task_number > len(TASKS):
        await show_completion_screen(update, context, user_id)
        return
    
    task = TASKS[task_number - 1]
    progress = UserManager.get_user_progress(user_id)
    
    if not progress:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Please use /start to begin the airdrop."
        )
        return
    
    # Create progress summary
    completed_tasks = progress['tasks_completed']
    completed_count = sum(completed_tasks)
    total_tasks = len(TASKS)
    
    progress_text = "📊 *Your Progress:*\n"
    for i, t in enumerate(TASKS, 1):
        status = "✅" if completed_tasks[i-1] else "⭕"
        current = "📍" if i == task_number else ""
        progress_text += f"{current} {status} Task {i}: {t['name']}\n"
    
    progress_text += f"\n✅ Completed: {completed_count}/{total_tasks}"
    
    # Task message
    message = f"""
💰 *Task {task_number}: {task['name']}*

{task['description']}

{task['verification_text']}

{progress_text}

*Remember:* Complete this task first, then click verification button.
"""
    
    # Create buttons
    keyboard = [
        [InlineKeyboardButton("🔗 Open Link", url=task['url'])],
        [InlineKeyboardButton(task['button_text'], callback_data=f"verify_{task_number}")]
    ]
    
    # Navigation buttons
    nav_buttons = []
    if task_number > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"task_{task_number-1}"))
    
    if task_number < len(TASKS):
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"task_{task_number+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("🏁 Finish", callback_data="finish_all"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit message
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Error showing task screen: {e}")

async def show_completion_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Show completion screen after all tasks"""
    if not user_id:
        user_id = update.effective_user.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    user = update.effective_user
    username = user.username or "NoUsername"
    
    completion_message = f"""
🎉 *CONGRATULATIONS! ALL TASKS COMPLETED!* 🎉

✅ You have successfully completed all social tasks!

💰 *You qualify for:* **100 FREQC Tokens**

---

📋 *Next Steps:*

1. 📸 *Take Screenshots* of all completed tasks
2. 💼 *Prepare your wallet address* (ERC20/BEP20 compatible)
3. 📤 *Contact our admins* with the proof:

*Admins to Contact:*
{ADMINS[0]}
{ADMINS[1]}

*Send them this information:*
• Your Telegram: @{username}
• Screenshot proofs of all 5 tasks
• Your wallet address

---

⏳ *Verification Process:*
- Admins will verify your submissions
- Upon successful verification, tokens will be sent
- Processing time: 24-48 hours

*Thank you for participating in Freequency Airdrop!* 🚀
"""
    
    keyboard = [
        [InlineKeyboardButton("📤 Contact Admin 1", url=f"https://t.me/{ADMINS[0].replace('@', '')}")],
        [InlineKeyboardButton("📤 Contact Admin 2", url=f"https://t.me/{ADMINS[1].replace('@', '')}")],
        [InlineKeyboardButton("🔄 Restart Airdrop", callback_data="restart_airdrop")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=completion_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=completion_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error showing completion screen: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Button clicked by {user_id}: {data}")
    
    if data == "start_tasks":
        # Start from task 1
        UserManager.update_user_step(user_id, 1)
        await show_task_screen(update, context, 1, user_id)
    
    elif data == "check_progress":
        await progress_command(update, context)
    
    elif data.startswith("task_"):
        task_num = int(data.split("_")[1])
        UserManager.update_user_step(user_id, task_num)
        await show_task_screen(update, context, task_num, user_id)
    
    elif data.startswith("verify_"):
        task_num = int(data.split("_")[1])
        
        # Mark task as completed
        UserManager.mark_task_completed(user_id, task_num)
        
        # Show success message
        await query.edit_message_text(
            text=f"✅ *Task {task_num} Verified!*\n\nMoving to next task...",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(1)
        
        # Move to next task or show completion
        if task_num < len(TASKS):
            await show_task_screen(update, context, task_num + 1, user_id)
        else:
            await show_completion_screen(update, context, user_id)
    
    elif data == "finish_all":
        await show_completion_screen(update, context, user_id)
    
    elif data == "restart_airdrop":
        # Reset progress
        UserManager.reset_user_progress(user_id)
        
        await query.edit_message_text(
            text="🔄 *Progress Reset!* Starting from the beginning...",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(1)
        await show_task_screen(update, context, 1, user_id)

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /progress command"""
    user_id = update.effective_user.id
    progress = UserManager.get_user_progress(user_id)
    
    if not progress:
        await update.message.reply_text("Please use /start to begin the airdrop.")
        return
    
    completed_tasks = progress['tasks_completed']
    current_step = progress['current_step']
    completed_count = sum(completed_tasks)
    total_tasks = len(TASKS)
    
    # Create progress visualization
    progress_bar = ""
    for i in range(total_tasks):
        if completed_tasks[i]:
            progress_bar += "🟢"
        elif i + 1 == current_step:
            progress_bar += "🟡"
        else:
            progress_bar += "⚪"
    
    progress_text = f"""
📊 *Your Airdrop Progress*

{progress_bar}
✅ {completed_count}/{total_tasks} tasks completed

*Current Status:* {'🎉 All Tasks Completed!' if completed_count == total_tasks else f'Task {current_step} of {total_tasks}'}

📋 *Task Breakdown:*
"""
    
    for i, task in enumerate(TASKS, 1):
        status = "✅ Completed" if completed_tasks[i-1] else ("⏳ Current" if i == current_step else "📝 Pending")
        progress_text += f"{i}. {task['name']}: {status}\n"
    
    if completed_count == total_tasks:
        progress_text += f"\n🎉 *Ready to claim!*\nContact admins: {ADMINS[0]} or {ADMINS[1]}"
    else:
        current_task = TASKS[current_step-1]
        progress_text += f"\n👉 *Current Task:* {current_task['name']}"
    
    keyboard = []
    if completed_count < total_tasks:
        keyboard.append([InlineKeyboardButton("➡️ Continue Tasks", callback_data=f"task_{current_step}")])
    else:
        keyboard.append([InlineKeyboardButton("📤 Contact Admins", callback_data="finish_all")])
    
    keyboard.append([InlineKeyboardButton("🔄 Restart", callback_data="restart_airdrop")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.message:
            await update.message.reply_text(
                progress_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                progress_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in progress command: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🤖 *Freequency Airdrop Bot Help*

*Available Commands:*
/start - Start or resume the airdrop
/progress - Check your current progress
/help - Show this help message
/reset - Reset your progress (start over)

*How it works:*
1. Complete 5 social tasks in order
2. Each task must be verified before next
3. After all tasks, contact admins with proof
4. Receive 100 FREQC tokens

*Contact Admins for help:*
@dallen32 or @joyouschrs

Good luck! 🚀
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reset command"""
    user_id = update.effective_user.id
    
    UserManager.reset_user_progress(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🚀 Start Airdrop", callback_data="start_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔄 *Your progress has been reset!*\n\nClick below to start the airdrop from the beginning.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command (admin only)"""
    user = update.effective_user
    
    # Check if user is admin
    if f"@{user.username}" not in ADMINS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get statistics
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE task5_completed = 1')
        completed_users = cursor.fetchone()[0]
        
        # Today's stats
        cursor.execute('SELECT COUNT(*) FROM users WHERE date(joined_at) = date("now")')
        today_users = cursor.fetchone()[0]
        
        # Recent completions
        cursor.execute('''
        SELECT username, joined_at FROM users 
        WHERE task5_completed = 1 
        ORDER BY joined_at DESC 
        LIMIT 5
        ''')
        recent_completions = cursor.fetchall()
        
        stats_text = f"""
📊 *Admin Statistics*

👥 Total Users: {total_users}
✅ Completed All Tasks: {completed_users}
📅 New Users Today: {today_users}
📈 Completion Rate: {(completed_users/total_users*100 if total_users > 0 else 0):.1f}%

🏆 *Recent Completers:*
"""
        
        if recent_completions:
            for username, joined_at in recent_completions:
                stats_text += f"• @{username or 'NoUsername'} - {joined_at}\n"
        else:
            stats_text += "No completions yet\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text(f"Error getting statistics: {e}")
    finally:
        conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check if this looks like a wallet address
    if len(message_text) >= 20 and any(keyword in message_text for keyword in ['0x', 'bc1', '1', '3', 'addr']):
        # Save wallet address
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET wallet_address = ? WHERE user_id = ?', 
                      (message_text, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            "✅ *Wallet address saved!*\n\n"
            "Now please send your task completion screenshots to our admins:\n"
            f"{ADMINS[0]}\n{ADMINS[1]}",
            parse_mode='Markdown'
        )
    else:
        # Show current task
        progress = UserManager.get_user_progress(user_id)
        if progress:
            current_step = progress['current_step']
            if current_step <= len(TASKS):
                await show_task_screen(update, context, current_step, user_id)
            else:
                await show_completion_screen(update, context, user_id)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ An error occurred. Please try again or use /start"
            )
        except:
            pass

def main():
    """Main function to start the bot"""
    # Initialize database
    init_db()
    
    # Get bot token
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is not set!")
        logger.info("Please set the token: export TELEGRAM_BOT_TOKEN='your_token_here'")
        return
    
    logger.info("🤖 Starting Freequency Airdrop Bot...")
    logger.info(f"📊 Database path: {DB_PATH}")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    logger.info("🔄 Bot is now polling for updates...")
    application.run_polling(
        poll_interval=1.0,
        timeout=10,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
