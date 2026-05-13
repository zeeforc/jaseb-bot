# core/config.py
import os
from dotenv import load_dotenv

# Load file .env
load_dotenv()

# Kredensial Bot & Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
API_ID = int(os.getenv("API_ID", 0) if os.getenv("API_ID") else 0)
API_HASH = os.getenv("API_HASH")

# Kredensial Database
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Settingan Logger yang dicari sama logger.py lu
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Validasi sederhana
if not BOT_TOKEN or not API_ID or not API_HASH:
    print("⚠️ WARNING: Kredensial Telegram di .env belum lengkap!")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ WARNING: Kredensial Supabase di .env belum lengkap!")