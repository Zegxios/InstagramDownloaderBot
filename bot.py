import os
import re
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# خواندن توکن از متغیر محیطی
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده است!")

# پوشه ذخیره موقت
TEMP_DIR = "temp_downloads"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# تشخیص لینک اینستاگرام
def is_instagram_link(text):
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[a-zA-Z0-9_-]+/?.*)'
    return re.match(pattern, text)

# دانلود محتوا از اینستاگرام
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
        print(f"خطا در دانلود: {e}")
        return None, None

# پاک کردن فایل‌های موقت
def cleanup_temp_files():
    for f in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"خطا در پاک کردن: {e}")

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 به بات دانلودر اینستاگرام خوش آمدید!\n\n"
        "✅ لینک پست، ریلز یا ویدیوی اینستاگرام را برای من بفرستید.\n"
        "✅ محتوا را دانلود کرده و برایتان ارسال می‌کنم.\n\n"
        "⚠️ توجه: فقط صفحات عمومی قابل دانلود هستند."
    )

# دستور /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 راهنما:\n\n"
        "1. لینک اینستاگرام را کپی کنید.\n"
        "2. در همین چت برای من بفرستید.\n"
        "3. چند ثانیه صبر کنید تا دانلود و ارسال شود.\n\n"
        "مثال لینک معتبر:\n"
        "https://www.instagram.com/p/Cx123456789/"
    )

# پردازش لینک اینستاگرام
async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # بررسی معتبر بودن لینک
    if not is_instagram_link(url):
        await update.message.reply_text("❌ لینک معتبر اینستاگرام نیست.\nلینک باید از نوع /p، /reel یا /tv باشد.")
        return
    
    waiting_msg = await update.message.reply_text("⏳ در حال دریافت محتوا از اینستاگرام... لطفاً صبر کنید.")
    
    file_path, file_type = await download_instagram_content(url)
    
    if not file_path:
        await waiting_msg.edit_text("❌ خطا: محتوا یافت نشد.\nممکن است صفحه خصوصی باشد یا لینک نادرست است.")
        return
    
    try:
        with open(file_path, 'rb') as f:
            if file_type == 'video':
                await update.message.reply_video(video=f, caption="✅ دانلود با موفقیت انجام شد!")
            else:
                await update.message.reply_photo(photo=f, caption="✅ دانلود با موفقیت انجام شد!")
        
        await waiting_msg.delete()
        
    except Exception as e:
        await waiting_msg.edit_text(f"❌ خطا در ارسال فایل: {str(e)[:100]}")
    
    finally:
        cleanup_temp_files()

# تابع اصلی
def main():
    print("🤖 بات در حال راه‌اندازی...")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_link))
    
    print("✅ بات با موفقیت روشن شد! در حال انتظار برای پیام‌ها...")
    app.run_polling()

if __name__ == "__main__":
    main()
