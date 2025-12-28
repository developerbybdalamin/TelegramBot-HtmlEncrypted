import os
import base64
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread
import time

# Flask app for Render.com
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is running!", 200

@app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Bot Configuration
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN environment variable")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Loading animation function
async def show_loading_animation(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str = "Processing your HTML file..."):
    """Show loading animation with dots"""
    loading_messages = [
        f"⏳ {message_text}",
        f"⏳ {message_text}.",
        f"⏳ {message_text}..",
        f"⏳ {message_text}..."
    ]
    
    loading_message = None
    for i in range(8):  # Run animation for 8 cycles
        msg_text = loading_messages[i % 4]
        if loading_message:
            try:
                await loading_message.edit_text(msg_text)
            except:
                loading_message = await update.message.reply_text(msg_text)
        else:
            loading_message = await update.message.reply_text(msg_text)
        await asyncio.sleep(0.5)
    
    return loading_message

# Encryption function
def encrypt_html(content: str) -> str:
    """Encrypt HTML content using _d0 + _d23 + base64"""
    # Encode to base64
    base64_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    # Add prefixes
    encrypted = f"_d0_d23{base64_encoded}"
    
    return encrypted

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    welcome_text = """
    🤖 **HTML File Encryptor Bot**
    
    Welcome! I can encrypt your HTML files.
    
    **How to use:**
    1. Send me any HTML file (.html or .htm)
    2. I'll encrypt it using special encryption
    3. You'll get back the encrypted HTML file
    
    **Encryption Method:**
    `_d0 + _d23 + base64`
    
    Just send me an HTML file to get started!
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = """
    **📖 Help Guide**
    
    **Commands:**
    /start - Start the bot
    /help - Show this help message
    /about - About this bot
    
    **To encrypt HTML:**
    Simply send me any HTML file (with .html or .htm extension)
    
    **Encryption Process:**
    1. You send HTML file
    2. I show loading animation
    3. Encrypt using: `_d0 + _d23 + base64`
    4. Return encrypted HTML file
    
    **Note:** Maximum file size: 20MB
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show about information."""
    about_text = """
    **🔒 HTML File Encryptor Bot**
    
    **Version:** 1.0
    **Developer:** Your Name
    
    **Features:**
    • HTML file encryption
    • Loading animation
    • Fast processing
    • Secure encryption
    
    **Encryption:** _d0 + _d23 + base64
    
    Hosted on Render.com
    """
    await update.message.reply_text(about_text, parse_mode='Markdown')

# Handle HTML files
async def handle_html_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming HTML files."""
    try:
        # Check if message contains document
        if not update.message.document:
            await update.message.reply_text("Please send an HTML file (.html or .htm)")
            return
        
        document = update.message.document
        
        # Check file extension
        file_name = document.file_name.lower()
        if not (file_name.endswith('.html') or file_name.endswith('.htm')):
            await update.message.reply_text("❌ Please send only HTML files (.html or .htm extension)")
            return
        
        # Show loading animation
        loading_msg = await show_loading_animation(update, context, "Encrypting HTML file...")
        
        # Download the file
        file = await document.get_file()
        file_path = f"temp_{document.file_id}.html"
        await file.download_to_drive(file_path)
        
        # Read and encrypt the file
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Encrypt the content
        encrypted_content = encrypt_html(html_content)
        
        # Create encrypted file
        encrypted_filename = f"encrypted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(encrypted_filename, 'w', encoding='utf-8') as f:
            f.write(encrypted_content)
        
        # Send encrypted file back
        with open(encrypted_filename, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"encrypted_{document.file_name}",
                caption=f"✅ **Encrypted HTML File**\n\n📁 Original: {document.file_name}\n🔐 Method: _d0 + _d23 + base64\n\nDownload and use as needed!"
            )
        
        # Clean up
        if loading_msg:
            await loading_msg.delete()
        
        os.remove(file_path)
        os.remove(encrypted_filename)
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Handle text messages
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    text = update.message.text
    
    if not text.startswith('/'):
        await update.message.reply_text(
            "📁 Please send me an HTML file to encrypt!\n"
            "Use /help for instructions."
        )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    # Create Flask thread for Render.com
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    
    # Handle documents (HTML files)
    application.add_handler(MessageHandler(
        filters.Document.ALL, 
        handle_html_file
    ))
    
    # Handle text messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text
    ))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()