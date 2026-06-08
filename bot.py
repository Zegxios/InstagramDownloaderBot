import os
import re
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده است!")

TEMP_DIR = "temp_downloads"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def is_instagram_link(text):
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[a-zA-Z0-9_-]+/?.*)'
    return re.match(pattern, text)

async def download_instagram_content(url):
    try:
        L = instaloader.Instaloader(
            dirname_pattern=TEMP_DIR,
            filename_pattern="{shortcode}",
            save_metadata=False,
            post_metadata_txt_pattern="",
            max_connection_attempts=3,
            quiet=True
        )
        
        post = instaloader.Post.from_url(url)
        L.download_post(post, target_dir=TEMP_DIR)
        
        shortcode = post.shortcode
        files = os.listdir(TEMP_DIR)
        
        video_file = None
        image_file = None
        
        for f in files:
            if shortcode in f:
                if f.endswith('.mp4'):
                    video_file = os.path.join(TEMP_DIR, f)
                elif f.endswith('.jpg') and not video_file:
                    image_file = os.path.join(TEMP_DIR, f)
        
        if video_file:
            return video_file, 'video'
        elif image_file:
            return image_file, 'image'
        else:
            return None, None
            
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def cleanup_temp_files():
    for f in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Cleanup error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 به بات دانلودر اینستاگرام خوش آمدید!\n\n"
        "✅ لینک اینستاگرام را بفرستید تا محتوا را دانلود کنم."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "لینک اینستاگرام را بفرستید.\n"
        "مثال: https://www.instagram.com/p/Cx123456789/"
    )

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not is_instagram_link(url):
        await update.message.reply_text("❌ لینک معتبر نیست.")
        return
    
    waiting_msg = await update.message.reply_text("⏳ در حال دریافت...")
    
    file_path, file_type = await download_instagram_content(url)
    
    if not file_path:
        await waiting_msg.edit_text("❌ خطا: محتوا یافت نشد.")
        return
    
    try:
        with open(file_path, 'rb') as f:
            if file_type == 'video':
                await update.message.reply_video(video=f, caption="✅ دانلود شد!")
            else:
                await update.message.reply_photo(photo=f, caption="✅ دانلود شد!")
        
        await waiting_msg.delete()
        
    except Exception as e:
        await waiting_msg.edit_text(f"❌ خطا: {str(e)[:100]}")
    
    finally:
        cleanup_temp_files()

def main():
    print("🤖 Bot starting...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_link))
    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()