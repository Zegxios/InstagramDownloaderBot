import os
import re
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN تنظیم نشده است")

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
            max_connection_attempts=2,
            quiet=True
        )
        
        # استخراج shortcode
        match = re.search(r'/(p|reel|tv)/([a-zA-Z0-9_-]+)/?', url)
        if not match:
            return None, "لینک نامعتبر"
        
        shortcode = match.group(2)
        
        # دریافت پست
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # چک خصوصی بودن
        if post.is_private:
            return None, "این صفحه خصوصی است"
        
        # دانلود
        L.download_post(post, target_dir=TEMP_DIR)
        
        # پیدا کردن فایل
        files = os.listdir(TEMP_DIR)
        
        for f in files:
            if shortcode in f:
                if f.endswith('.mp4'):
                    return os.path.join(TEMP_DIR, f), None
                elif f.endswith('.jpg'):
                    return os.path.join(TEMP_DIR, f), None
        
        return None, "فایل پیدا نشد"
            
    except Exception as e:
        return None, str(e)[:100]

def cleanup():
    for f in os.listdir(TEMP_DIR):
        try:
            os.remove(os.path.join(TEMP_DIR, f))
        except:
            pass

async def start(update, context):
    await update.message.reply_text("🎬 لینک اینستاگرام را بفرستید")

async def handle(update, context):
    url = update.message.text.strip()
    
    if not is_instagram_link(url):
        await update.message.reply_text("❌ لینک نامعتبر")
        return
    
    msg = await update.message.reply_text("⏳ در حال دریافت...")
    
    file_path, error = await download_instagram_content(url)
    
    if not file_path:
        await msg.edit_text(f"❌ {error}")
        return
    
    with open(file_path, 'rb') as f:
        if file_path.endswith('.mp4'):
            await update.message.reply_video(video=f, caption="✅ دانلود شد!")
        else:
            await update.message.reply_photo(photo=f, caption="✅ دانلود شد!")
    
    await msg.delete()
    cleanup()

async def help(update, context):
    await update.message.reply_text("لینک اینستاگرام بفرستید")

def main():
    print("🤖 Bot starting...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
