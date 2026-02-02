import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sqlite3
from datetime import datetime
import os

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
        task1_completed INTEGER DEFAULT 0,
        task2_completed INTEGER DEFAULT 0,
        task3_completed INTEGER DEFAULT 0,
        task4_completed INTEGER DEFAULT 0,
        task5_completed INTEGER DEFAULT 0,
        wallet_address TEXT,
        joined_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

# Task configuration
TASKS = [
    {
        'id': 1,
        'name': 'Join Group',
        'description': 'Join our Telegram Group',
        'url': 'https://t.me/+UpEih_OErhA5YWZh',
        'button_text': '✅ Joined Group'
    },
    {
        'id': 2,
        'name': 'Join Channel',
        'description': 'Join our Telegram Channel',
        'url': 'https://t.me/+aCyF_M3PeV42OWIx',
        'button_text': '✅ Joined Channel'
    },
    {
        'id': 3,
        'name': 'Follow Twitter & Retweet',
        'description': 'Follow Twitter and retweet pinned post',
        'url': 'https://x.com/Freequencycoin',
        'button_text': '✅ Followed & Retweeted'
    },
    {
        'id': 4,
        'name': 'Tweet',
        'description': 'Tweet about Freequency',
        'url': 'https://x.com/compose/tweet',
        'button_text': '✅ Tweeted'
    },
    {
        'id': 5,
        'name': 'Visit Website',
        'description': 'Visit Frequency.com',
        'url': 'https://www.freequency.net/freequency-crypto.html',
        'button_text': '✅ Visited Website'
    }
]

ADMINS = ['@dallen32', '@joyouschrs']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    # Initialize user in database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at) 
    VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, datetime.now()))
    
    cursor.execute('SELECT current_step FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_step = result[0] if result else 1
    
    conn.commit()
    conn.close()
    
    # Send welcome message with first task
    await show_task(update, context, current_step)

async def show_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_number: int):
    user_id = update.effective_user.id
    
    # Get user progress
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT task1_completed, task2_completed, task3_completed, task4_completed, task5_completed 
    FROM users WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return
    
    completed_tasks = result
    
    if task_number <= len(TASKS):
        task = TASKS[task_number - 1]
        
        # Create progress text
        progress_text = "📋 *Your Progress:*\n"
        for i, t in enumerate(TASKS, 1):
            status = "✅" if completed_tasks[i-1] else "⭕"
            progress_text += f"{status} Task {i}: {t['name']}\n"
        
        message = f"""
💰 *Complete social task to earn 100 FREQC*

*Current Task {task_number}: {task['name']}*
👉 {task['description']}

{progress_text}

*Note:* Complete this task before proceeding to the next. After all tasks, send screenshot and wallet address to admins.
        """
        
        keyboard = [
            [InlineKeyboardButton("🔗 Open Link", url=task['url'])],
            [InlineKeyboardButton(task['button_text'], callback_data=f"verify_{task_number}")]
        ]
        
        if task_number > 1:
            keyboard.append([InlineKeyboardButton("◀️ Previous Task", callback_data=f"prev_{task_number}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    else:
        # All tasks completed
        message = f"""
🎉 *Congratulations! All Tasks Completed!*

✅ You have successfully completed all social tasks.

📸 *Next Steps:*
1. Take screenshots of all completed tasks
2. Prepare your wallet address
3. Send proof to our admins:

*Admins to Contact:*
{ADMINS[0]}
{ADMINS[1]}

Send them:
• Your username: @{update.effective_user.username}
• Screenshot proofs
• Your wallet address

💰 You will receive 100 FREQC tokens after verification!
        """
        
        await update.callback_query.edit_message_text(
            text=message,
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if data.startswith("verify_"):
        task_num = int(data.split("_")[1])
        
        # Mark task as completed
        cursor.execute(f'''
        UPDATE users SET task{task_num}_completed = 1 
        WHERE user_id = ?
        ''', (user_id,))
        
        # Move to next task
        cursor.execute('''
        UPDATE users SET current_step = ? 
        WHERE user_id = ? AND current_step = ?
        ''', (task_num + 1, user_id, task_num))
        
        conn.commit()
        
        # Show next task or completion message
        if task_num < len(TASKS):
            await show_task(update, context, task_num + 1)
        else:
            await show_task(update, context, task_num + 1)  # This will show completion
    
    elif data.startswith("prev_"):
        task_num = int(data.split("_")[1])
        await show_task(update, context, task_num - 1)
    
    elif data.startswith("task_"):
        task_num = int(data.split("_")[1])
        await show_task(update, context, task_num)
    
    conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user wants to update wallet address
    message_text = update.message.text
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT current_step FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        current_step = result[0]
        
        # If all tasks completed and user sends wallet address
        if current_step > len(TASKS):
            # Check if message looks like a crypto wallet address
            if len(message_text) > 20 and any(char in message_text for char in ['0x', 'bc1', '1', '3']):
                cursor.execute('''
                UPDATE users SET wallet_address = ? WHERE user_id = ?
                ''', (message_text, user_id))
                
                conn.commit()
                
                await update.message.reply_text(
                    f"✅ Wallet address saved!\n\n"
                    f"Now please send your task completion screenshots to our admins:\n"
                    f"{ADMINS[0]}\n{ADMINS[1]}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"📸 Please send your task completion screenshots along with your wallet address to our admins:\n\n"
                    f"{ADMINS[0]}\n{ADMINS[1]}"
                )
        else:
            # User is still in tasks
            await show_task(update, context, current_step)
    
    conn.close()

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT current_step, task1_completed, task2_completed, task3_completed, task4_completed, task5_completed 
    FROM users WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        current_step, *completed_tasks = result
        
        progress_text = "📊 *Your Airdrop Progress*\n\n"
        total_tasks = len(TASKS)
        completed_count = sum(completed_tasks)
        
        progress_text += f"✅ Completed: {completed_count}/{total_tasks}\n\n"
        
        for i, task in enumerate(TASKS, 1):
            status = "✅" if completed_tasks[i-1] else "⭕"
            progress_text += f"{status} {task['name']}\n"
        
        if current_step <= len(TASKS):
            progress_text += f"\nCurrent Task: {current_step}. {TASKS[current_step-1]['name']}"
        else:
            progress_text += f"\n🎉 All tasks completed! Contact admins:\n{ADMINS[0]}\n{ADMINS[1]}"
        
        await update.message.reply_text(progress_text, parse_mode='Markdown')

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
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
    
    await update.message.reply_text("🔄 Your progress has been reset. Use /start to begin again.")
    await show_task(update, context, 1)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Check if user is admin
    if f"@{username}" not in ADMINS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get total users
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Get users who completed all tasks
    cursor.execute('''
    SELECT COUNT(*) FROM users 
    WHERE task1_completed = 1 
    AND task2_completed = 1 
    AND task3_completed = 1 
    AND task4_completed = 1 
    AND task5_completed = 1
    ''')
    completed_users = cursor.fetchone()[0]
    
    # Get recent users
    cursor.execute('''
    SELECT username, joined_at FROM users 
    ORDER BY joined_at DESC LIMIT 10
    ''')
    recent_users = cursor.fetchall()
    
    stats_text = f"""
📊 *Admin Statistics*

👥 Total Users: {total_users}
✅ Completed All Tasks: {completed_users}

📈 Completion Rate: {(completed_users/total_users*100 if total_users > 0 else 0):.1f}%

🆕 Recent Users:
"""
    
    for user in recent_users:
        username, joined_at = user
        stats_text += f"• @{username if username else 'N/A'} - {joined_at}\n"
    
    conn.close()
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

def main():
    # Initialize database
    init_db()
    
    # Get bot token from environment variable
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        print("Error: Please set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("progress", progress))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("🤖 Airdrop Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
