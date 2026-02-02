import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
DB_NAME = "airdrop_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        current_step INTEGER DEFAULT 1,
        task1_completed BOOLEAN DEFAULT 0,
        task2_completed BOOLEAN DEFAULT 0,
        task3_completed BOOLEAN DEFAULT 0,
        task4_completed BOOLEAN DEFAULT 0,
        task5_completed BOOLEAN DEFAULT 0,
        wallet_address TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
    
    conn.commit()
    conn.close()

# Task configuration
TASKS = [
    {
        'id': 1,
        'name': 'Join Group',
        'description': 'Join our Telegram Group',
        'url': 'https://t.me/+UpEih_OErhA5YWZh',
        'button_text': '✅ Joined Group',
        'verification_text': 'Have you joined the Telegram group?'
    },
    {
        'id': 2,
        'name': 'Join Channel',
        'description': 'Join our Telegram Channel',
        'url': 'https://t.me/+aCyF_M3PeV42OWIx',
        'button_text': '✅ Joined Channel',
        'verification_text': 'Have you joined the Telegram channel?'
    },
    {
        'id': 3,
        'name': 'Follow Twitter & Retweet',
        'description': 'Follow Twitter and retweet pinned post',
        'url': 'https://x.com/Freequencycoin',
        'button_text': '✅ Followed & Retweeted',
        'verification_text': 'Have you followed and retweeted?'
    },
    {
        'id': 4,
        'name': 'Tweet',
        'description': 'Tweet about Freequency',
        'url': 'https://x.com/compose/tweet',
        'button_text': '✅ Tweeted',
        'verification_text': 'Have you tweeted about Freequency?'
    },
    {
        'id': 5,
        'name': 'Visit Website',
        'description': 'Visit Frequency.com',
        'url': 'https://www.freequency.net/freequency-crypto.html',
        'button_text': '✅ Visited Website',
        'verification_text': 'Have you visited the website?'
    }
]

ADMINS = ['@dallen32', '@joyouschrs']

class AirdropBot:
    def __init__(self):
        self.init_db()
        
    @staticmethod
    def init_db():
        init_db()
    
    @staticmethod
    def get_user_progress(user_id: int):
        """Get user progress from database"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT current_step, task1_completed, task2_completed, task3_completed, task4_completed, task5_completed, 
               username, wallet_address
        FROM users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'current_step': result[0],
                'tasks_completed': result[1:6],
                'username': result[6],
                'wallet_address': result[7]
            }
        return None
    
    @staticmethod
    def update_user_step(user_id: int, step: int):
        """Update user's current step"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET current_step = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', 
                      (step, user_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def mark_task_completed(user_id: int, task_num: int):
        """Mark a specific task as completed"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(f'UPDATE users SET task{task_num}_completed = 1, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', 
                      (user_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def register_user(user_id: int, username: str, first_name: str):
        """Register a new user"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, joined_at, last_active) 
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name))
        conn.commit()
        conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    
    # Register or update user
    AirdropBot.register_user(user_id, username, first_name)
    
    # Get user progress
    progress = AirdropBot.get_user_progress(user_id)
    if progress:
        current_step = progress['current_step']
    else:
        current_step = 1
        AirdropBot.update_user_step(user_id, current_step)
    
    # Send welcome message
    welcome_message = """
🚀 *Welcome to Freequency Airdrop Bot!* 🚀

💰 *Earn 100 FREQC tokens* by completing social tasks

📋 *How it works:*
1. Complete tasks in order
2. Each task must be verified before moving to next
3. After all tasks, contact admins with proof
4. Receive your reward!

Click the button below to start with Task 1!
"""
    
    keyboard = [
        [InlineKeyboardButton("🎯 Start Tasks", callback_data="start_tasks")],
        [InlineKeyboardButton("📊 Check Progress", callback_data="check_progress")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_number: int, user_id: int = None):
    """Show a specific task to the user"""
    if not user_id:
        user_id = update.effective_user.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    if task_number <= len(TASKS):
        task = TASKS[task_number - 1]
        
        # Get user progress
        progress = AirdropBot.get_user_progress(user_id)
        if not progress:
            await context.bot.send_message(
                chat_id=user_id,
                text="Please use /start to begin the airdrop."
            )
            return
        
        tasks_completed = progress['tasks_completed']
        
        # Create progress bar
        progress_text = "📊 *Your Progress:*\n"
        total_tasks = len(TASKS)
        completed_count = sum(tasks_completed)
        
        # Progress bar visualization
        progress_bar = "🟢" * completed_count + "⚪" * (total_tasks - completed_count)
        
        progress_text += f"{progress_bar}\n"
        progress_text += f"✅ {completed_count}/{total_tasks} tasks completed\n\n"
        
        for i, t in enumerate(TASKS, 1):
            status = "✅" if tasks_completed[i-1] else f"{i}."
            progress_text += f"{status} {t['name']}\n"
        
        # Task message
        message = f"""
💰 *Task {task_number}: {task['name']}*

{task['description']}

{task['verification_text']}

{progress_text}

*Note:* Complete this task and verify it before proceeding to the next.
        """
        
        # Create buttons
        keyboard = [
            [InlineKeyboardButton("🔗 Open Link", url=task['url'])],
            [InlineKeyboardButton(task['button_text'], callback_data=f"verify_{task_number}")]
        ]
        
        # Add navigation buttons
        nav_buttons = []
        if task_number > 1:
            nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"task_{task_number-1}"))
        
        if task_number < len(TASKS):
            nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"task_{task_number+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🏁 Finish", callback_data="all_done"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("📊 Progress", callback_data="check_progress")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send or edit message
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
    else:
        # All tasks completed
        await show_completion_message(update, context, user_id)

async def show_completion_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Show completion message after all tasks"""
    if not user_id:
        user_id = update.effective_user.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    message = f"""
🎉 *CONGRATULATIONS!* 🎉

You have successfully completed all social tasks for the Freequency Airdrop!

💰 *You qualify for 100 FREQC tokens!*

📋 *Next Steps:*

1. 📸 *Take Screenshots* of all completed tasks
2. 💼 *Prepare your wallet address* (ERC20/BEP20 compatible)
3. 📤 *Contact our admins* with the following:

*Admins to Contact:*
{ADMINS[0]}
{ADMINS[1]}

*Send them this information:*
• Your Telegram: @{update.effective_user.username}
• Screenshot proofs of all tasks
• Your wallet address

⏳ *Verification Process:*
- Admins will verify your submissions
- Upon successful verification, tokens will be sent
- Processing time: 24-48 hours

Thank you for participating! 🚀
"""
    
    keyboard = [
        [InlineKeyboardButton("📤 Contact Admins", url=f"https://t.me/{ADMINS[0].replace('@', '')}")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "start_tasks":
        # Start from task 1
        AirdropBot.update_user_step(user_id, 1)
        await show_task(update, context, 1, user_id)
    
    elif data == "check_progress":
        await progress_command(update, context)
    
    elif data.startswith("task_"):
        task_num = int(data.split("_")[1])
        AirdropBot.update_user_step(user_id, task_num)
        await show_task(update, context, task_num, user_id)
    
    elif data.startswith("verify_"):
        task_num = int(data.split("_")[1])
        
        # Mark task as completed
        AirdropBot.mark_task_completed(user_id, task_num)
        
        # Move to next task if available
        if task_num < len(TASKS):
            next_task = task_num + 1
            AirdropBot.update_user_step(user_id, next_task)
            
            # Show success message
            await query.edit_message_text(
                text=f"✅ *Task {task_num} Verified Successfully!*\n\nMoving to Task {next_task}...",
                parse_mode='Markdown'
            )
            
            await asyncio.sleep(1)
            await show_task(update, context, next_task, user_id)
        else:
            # All tasks completed
            await query.edit_message_text(
                text="🎉 *All Tasks Completed Successfully!*",
                parse_mode='Markdown'
            )
            await asyncio.sleep(1)
            await show_completion_message(update, context, user_id)
    
    elif data == "all_done":
        await show_completion_message(update, context, user_id)
    
    elif data == "restart":
        # Reset user progress
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE users SET 
        current_step = 1,
        task1_completed = 0,
        task2_completed = 0,
        task3_completed = 0,
        task4_completed = 0,
        task5_completed = 0
        WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(
            text="🔄 *Progress Reset!* Starting from the beginning...",
            parse_mode='Markdown'
        )
        await asyncio.sleep(1)
        await show_task(update, context, 1, user_id)

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /progress command"""
    user_id = update.effective_user.id
    progress = AirdropBot.get_user_progress(user_id)
    
    if not progress:
        await update.message.reply_text("Please use /start to begin the airdrop.")
        return
    
    tasks_completed = progress['tasks_completed']
    current_step = progress['current_step']
    total_tasks = len(TASKS)
    completed_count = sum(tasks_completed)
    
    # Create detailed progress
    progress_text = f"""
📊 *Your Airdrop Progress*

🎯 *Current Status:* {'All Tasks Completed! 🎉' if completed_count == total_tasks else f'Task {current_step} of {total_tasks}'}

📈 *Completion:* {completed_count}/{total_tasks} tasks
{'⭐' * (completed_count if completed_count <= 5 else 5)}

📋 *Task Breakdown:*
"""
    
    for i, task in enumerate(TASKS, 1):
        status = "✅ Completed" if tasks_completed[i-1] else "⏳ Pending"
        progress_text += f"{i}. {task['name']}: {status}\n"
    
    if completed_count == total_tasks:
        progress_text += f"\n🎉 *All tasks completed!*\nContact admins: {ADMINS[0]} or {ADMINS[1]}"
    else:
        current_task = TASKS[current_step-1] if current_step <= total_tasks else None
        if current_task:
            progress_text += f"\n👉 *Current Task:* {current_task['name']}\n"
            progress_text += f"📝 *Description:* {current_task['description']}\n"
    
    keyboard = []
    if completed_count < total_tasks:
        keyboard.append([InlineKeyboardButton("➡️ Continue Tasks", callback_data=f"task_{current_step}")])
    else:
        keyboard.append([InlineKeyboardButton("📤 Contact Admins", url=f"https://t.me/{ADMINS[0].replace('@', '')}")])
    
    keyboard.append([InlineKeyboardButton("🔄 Restart", callback_data="restart")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command"""
    help_text = """
🤖 *Freequency Airdrop Bot Help*

*Available Commands:*
/start - Start or resume the airdrop
/progress - Check your current progress
/help - Show this help message
/reset - Reset your progress (start over)
/stats - Admin statistics (admin only)

*How it works:*
1. Complete 5 social tasks in order
2. Verify each task before proceeding
3. After all tasks, contact admins with proof
4. Receive 100 FREQC tokens

*Contact Admins:*
If you have any issues, contact:
@dallen32 or @joyouschrs

Good luck! 🚀
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /reset command"""
    user_id = update.effective_user.id
    
    # Reset user progress
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users SET 
    current_step = 1,
    task1_completed = 0,
    task2_completed = 0,
    task3_completed = 0,
    task4_completed = 0,
    task5_completed = 0
    WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("🎯 Start Tasks", callback_data="start_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔄 *Your progress has been reset successfully!*\n\nClick the button below to start from the beginning.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats command (admin only)"""
    user = update.effective_user
    
    # Check if user is admin
    if f"@{user.username}" not in ADMINS:
        await update.message.reply_text("❌ This command is for admins only.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE task5_completed = 1')
    completed_users = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT username, joined_at 
    FROM users 
    WHERE task5_completed = 1 
    ORDER BY joined_at DESC 
    LIMIT 10
    ''')
    recent_completed = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE date(joined_at) = date("now")')
    today_users = cursor.fetchone()[0]
    
    conn.close()
    
    # Format statistics
    stats_text = f"""
📊 *Admin Statistics*

👥 *Total Users:* {total_users}
✅ *Completed All Tasks:* {completed_users}
📈 *Completion Rate:* {(completed_users/total_users*100 if total_users > 0 else 0):.1f}%
📅 *New Users Today:* {today_users}

🏆 *Recent Completers:*
"""
    
    if recent_completed:
        for i, (username, joined_at) in enumerate(recent_completed, 1):
            stats_text += f"{i}. @{username or 'No username'} - {joined_at}\n"
    else:
        stats_text += "No users have completed all tasks yet.\n"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check if message might be a wallet address
    if len(message_text) >= 20 and any(keyword in message_text.lower() for keyword in ['0x', 'bc1', 'wallet', 'address']):
        # Save wallet address
        conn = sqlite3.connect(DB_NAME)
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
        # Check user progress and show current task
        progress = AirdropBot.get_user_progress(user_id)
        if progress:
            current_step = progress['current_step']
            if current_step <= len(TASKS):
                await show_task(update, context, current_step, user_id)
            else:
                await show_completion_message(update, context, user_id)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    # Initialize database
    AirdropBot.init_db()
    
    # Get bot token from environment variable
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    # Create application with persistence
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("🤖 Freequency Airdrop Bot is starting...")
    
    if os.getenv('RENDER'):
        # On Render, use webhook
        PORT = int(os.getenv('PORT', 8443))
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        
        if WEBHOOK_URL:
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
            )
        else:
            # Fallback to polling
            application.run_polling(allowed_updates=Update.ALL_TYPES)
    else:
        # Local development - use polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
