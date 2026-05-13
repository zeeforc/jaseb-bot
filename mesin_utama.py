import asyncio
import sys
import warnings

# --- BUNGKAM SURAT PERINGATAN (DEPRECATION WARNING) DARI PYTHON ---
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- FIX UNTUK ERROR PYROGRAM DI WINDOWS ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
# -----------------------------------------------------

from core.logger import logger
from database.crud import get_all_users

# 🔥 INI YANG TADI BIKIN ERROR, KATA "bot."-NYA UDAH GUA HAPUS
from engine.worker import worker 

async def scan_database():
    """Fungsi spesialis untuk memantau perintah dari Supabase"""
    logger.info("🤖 Mesin Utama (Pyrogram Worker) menyala dan siap memantau database...")
    
    # Jeda awal biar koneksi stabil
    await asyncio.sleep(5)
    
    while True:
        try:
            # 1. Ambil semua data user dari Supabase
            users = get_all_users()
            
            # Bikin daftar ID user yang "is_running" nya True di database
            db_running_users = []
            
            for user in users:
                user_id = user.get("telegram_id")
                is_running_db = user.get("is_running", False)
                
                if is_running_db:
                    db_running_users.append(user_id)
                    
                    # LOGIKA START: Di Database NYALA, tapi di memori Worker MATI
                    if not worker.running.get(user_id, False):
                        logger.info(f"⚡ Mendeteksi perintah START dari Panel untuk user {user_id}")
                        await worker.start_worker(user_id)
                        
            # LOGIKA STOP: Di memori Worker NYALA, tapi di Database MATI
            current_running_workers = list(worker.running.keys())
            for user_id in current_running_workers:
                if worker.running.get(user_id) and user_id not in db_running_users:
                    logger.info(f"🛑 Mendeteksi perintah STOP dari Panel untuk user {user_id}")
                    await worker.stop_worker(user_id)
                    
        except Exception as e:
            logger.error(f"✗ Error saat scanning database: {e}")
            
        # 2. Jeda 5 detik sebelum scan lagi
        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(scan_database())
    except KeyboardInterrupt:
        logger.info("⏸️ Mesin Utama dihentikan secara manual.")