import os
from dotenv import load_dotenv
from aiogram import Bot
import logging

# Logging sozlash (xatolarni ko'rish uchun)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hozirgi papkani chop etish (debug)
print(f"DEBUG: Hozirgi ish papkasi: {os.getcwd()}")

# .env faylni yuklash (loyihaning ildiz papkasida bo'lishi kerak)
env_path = '.env'
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print(f"DEBUG: .env fayli topildi va yuklandi: {env_path}")
else:
    print(f"DEBUG: .env fayli topilmadi: {env_path}")

# BOT_TOKEN ni olish
BOT_TOKEN = os.getenv('8288388496:AAH-R65Pu1kUG5ZWxBZuh6F_LhLNRN_fpgc')
if not BOT_TOKEN:
    # Fallback: Hardcoded token (VAQTINCHALIK, xavfsiz emas!)
    BOT_TOKEN = '8288388496:AAH-R65Pu1kUG5ZWxBZuh6F_LhLNRN_fpgc'  # Sizning tokeningiz
    print("⚠️ OGOHLANTIRISH: .env dan BOT_TOKEN topilmadi! Hardcoded ishlatildi (xavfsiz emas). .env ni to'g'rilang.")
else:
    print(f"DEBUG: BOT_TOKEN yuklandi (qisman): {BOT_TOKEN[:20]}...")

# Botni ishga tushirish
try:
    bot = Bot(token=BOT_TOKEN)
    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")
    print("✅ Bot tayyor!")
except Exception as e:
    logger.error(f"❌ Bot ishga tushirishda xato: {e}")
    print(f"❌ Bot xatosi: {e}")
    raise

# Admin ID
ADMIN_ID = 1553336381

# Yuklamalar papkasi
UPLOADS_DIR = 'uploads'
os.makedirs(UPLOADS_DIR, exist_ok=True)
print(f"DEBUG: Uploads papkasi: {UPLOADS_DIR}")

# Database yo'li
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "reports.db")
print(f"DEBUG: DB yo'li: {DB_PATH}")

# Test: Bot ma'lumotlarini chop etish
print(f"✅ Konfiguratsiya yuklandi! ADMIN_ID: {ADMIN_ID}")