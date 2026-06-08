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
            max_connection_attempts=3,
            quiet=True
        )
        
        # لاگین به اینستاگرام
        if INSTA_USERNAME and INSTA_PASSWORD:
            try:
                L.login(INSTA_USERNAME, INSTA_PASSWORD)
                print(f"✅ لاگین شد به {INSTA_USERNAME}")
            except Exception as e:
                error_detail = f"لاگین ناموفق: {str(e)[:100]}"
                print(error_detail)
                return None, None, error_detail
        
        # روش جدید دریافت پست
        try:
            # استخراج shortcode از لینک
            match = re.search(r'/(p|reel|tv)/([a-zA-Z0-9_-]+)/?', url)
            if not match:
                return None, None, "لینک معتبر نیست"
            
            shortcode = match.group(2)
            print(f"✅ shortcode: {shortcode}")
            
            # دریافت پست با shortcode
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            print(f"✅ پست پیدا شد: {post.shortcode}")
            
        except Exception as e:
            error_detail = f"پست پیدا نشد: {str(e)[:100]}"
            print(error_detail)
            return None, None, error_detail
        
        # دانلود
        try:
            L.download_post(post, target_dir=TEMP_DIR)
            print("✅ دانلود کامل شد")
        except Exception as e:
            error_detail = f"دانلود ناموفق: {str(e)[:100]}"
            print(error_detail)
            return None, None, error_detail
        
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
            return None, None, "فایل دانلود شده پیدا نشد"
            
    except Exception as e:
        error_detail = f"خطای عمومی: {str(e)[:200]}"
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
        "✅ لینک اینستاگرام را بفرستید تا محتوا را دانلود کنم.\n\n"
        "⚠️ توجه: فقط صفحات عمومی قابل دانلود هستند."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "لینک اینستاگرام را بفرستید.\n"
        "مثال: https://www.instagram.com/p/Cx123456789/\n\n"
        "پشتیبانی: پست‌ها و ریلز"
    )

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not is_instagram_link(url):
        await update.message.reply_text("❌ لینک معتبر اینستاگرام نیست.")
        return
    
    waiting_msg = await update.message.reply_text("⏳ در حال دریافت از اینستاگرام... (حداکثر 30 ثانیه)")
    
    file_path, file_type, error = await download_instagram_content(url)
    
    if not file_path:
        error_text = "❌ خطا: محتوا یافت نشد.\n\n"
        if error:
            error_text += f"📋 جزئیات خطا:\n`{error}`"
        else:
            error_text += "ممکن است:\n- صفحه خصوصی باشد\n- لینک نادرست باشد\n- اینستاگرام محدودیت ایجاد کرده باشد"
        
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
        await waiting_msg.edit_text(f"❌ خطا در ارسال: {str(e)[:100]}")
    
    finally:
        cleanup_temp_files()

def main():
    print("🤖 Bot starting...")
    if INSTA_USERNAME:
        print(f"✅ با اکانت اینستاگرام {INSTA_USERNAME} لاگین می‌شوم")
    else:
        print("⚠️ بدون لاگین (ممکن است محدودیت داشته باشد)")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_link))
    print("✅ Bot is running! منتظر پیام‌ها...")
    app.run_polling()

if __name__ == "__main__":
    main()
