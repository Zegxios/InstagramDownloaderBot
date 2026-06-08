import os
import re
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
INSTA_USERNAME = os.environ.get("INSTA_USERNAME")
INSTA_PASSWORD = os.environ.get("INSTA_PASSWORD")

if not TOKEN:
    raise ValueError("BOT_TOKEN تنظیم نشده است")

TEMP_DIR = "temp_downloads"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def is_instagram_link(text):
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[a-zA-Z0-9_-]+/?.*)'
    return re.match(pattern, text)

async def download_instagram_content(url):
    error_detail = None
    try:
        L = instaloader.Instaloader(
            dirname_pattern=TEMP_DIR,
            filename_pattern="{shortcode}",
            save_metadata=False,
            post_metadata_txt_pattern="",
            max_connection_attempts=2,
            quiet=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        # روش جدید لاگین با save session
        if INSTA_USERNAME and INSTA_PASSWORD:
            try:
                # لاگین با session file
                session_file = f"{INSTA_USERNAME}_session"
                if os.path.exists(session_file):
                    L.load_session_from_file(INSTA_USERNAME, session_file)
                    print(f"✅ سشن بارگذاری شد برای {INSTA_USERNAME}")
                else:
                    L.login(INSTA_USERNAME, INSTA_PASSWORD)
                    L.save_session_to_file(session_file)
                    print(f"✅ لاگین شد و سشن ذخیره شد برای {INSTA_USERNAME}")
            except Exception as e:
                error_detail = f"لاگین ناموفق: {str(e)[:100]}"
                print(error_detail)
                # ادامه بدون لاگین
                pass
        
        # استخراج shortcode از لینک
        match = re.search(r'/(p|reel|tv)/([a-zA-Z0-9_-]+)/?', url)
        if not match:
            return None, None, "لینک معتبر نیست"
        
        shortcode = match.group(2)
        print(f"✅ shortcode: {shortcode}")
        
        # دریافت پست
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print(f"✅ پست پیدا شد: {post.shortcode}")
        
        # دانلود
        L.download_post(post, target_dir=TEMP_DIR)
        print("✅ دانلود کامل شد")
        
        # پیدا کردن فایل
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
            return video_file, 'video', None
        elif image_file:
            return image_file, 'image', None
        else:
            return None, None, "فایل پیدا نشد"
            
    except Exception as e:
        error_detail = f"خطا: {str(e)[:200]}"
        print(error_detail)
        return None, None, error_detail

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
        "✅ لینک اینستاگرام را بفرستید.\n"
        "✅ پشتیبانی: پست و ریلز\n\n"
        "⚠️ فقط صفحات عمومی"
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
    
    file_path, file_type, error = await download_instagram_content(url)
    
    if not file_path:
        error_text = "❌ خطا\n\n"
        if error:
            error_text += f"`{error[:150]}`"
        else:
            error_text += "صفحه خصوصی یا لینک نامعتبر"
        
        await waiting_msg.edit_text(error_text, parse_mode='Markdown')
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
    if INSTA_USERNAME:
        print(f"📱 اکانت اینستاگرام: {INSTA_USERNAME}")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_link))
    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
