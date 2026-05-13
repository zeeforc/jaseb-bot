import asyncio
import sys
from datetime import datetime, timezone # 🔥 Tambahan import buat ngecek waktu

# --- FIX UNTUK ERROR PYROGRAM DI PYTHON VERSI BARU ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
# -----------------------------------------------------

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.handlers import login, store, settings, admin, panel
from core.config import BOT_TOKEN
from core.logger import logger

# 🔥 Tambahan import untuk database dan worker
from database.crud import get_all_users, update_user_setting
from engine.worker import worker

# async def set_bot_commands(bot: Bot):
#     """Set bot commands menu"""
#     commands = [
#         BotCommand(command="start", description="Menu utama"),
#         BotCommand(command="cek", description="Cek masa aktif paket"),
#     ]
#     await bot.set_my_commands(commands)

# ==========================================
# 🔥 SATPAM AUTO-EXPIRED CHECKER
# ==========================================
async def auto_expired_checker():
    """Satpam yang patroli mengecek masa aktif paket tiap 1 jam"""
    # Tunggu 10 detik di awal biar database connect sempurna sebelum patroli
    await asyncio.sleep(10) 
    
    while True:
        try:
            logger.info("🕵️‍♂️ Memulai patroli pengecekan masa aktif user...")
            users = get_all_users()
            sekarang = datetime.now(timezone.utc)
            
            for user in users:
                user_id = user.get("telegram_id")
                paket = user.get("paket", "free")
                expired_str = user.get("expired_at")
                
                # Cek khusus user yang berlangganan (bukan free)
                if paket != "free" and expired_str:
                    try:
                        # Parsing string ISO 8601 dari Supabase
                        expired_date = datetime.fromisoformat(expired_str.replace("Z", "+00:00"))
                        
                        if sekarang > expired_date:
                            logger.info(f"🚨 WAKTU HABIS! User {user_id} paketnya kedaluwarsa.")
                            
                            # 1. Matikan mesin promosinya
                            await worker.stop_worker(user_id)
                            
                            # 2. Reset status di database
                            update_user_setting(user_id, "paket", "free")
                            update_user_setting(user_id, "expired_at", None)
                            
                            # (Opsional) Kasih notif ke user kalau sempet
                            
                    except Exception as date_err:
                        logger.error(f"✗ Gagal parsing tanggal user {user_id}: {date_err}")
                        
        except Exception as e:
            logger.error(f"✗ Error di auto_expired_checker: {e}")
            
        # Tidur selama 1 jam (3600 detik) sebelum keliling lagi
        await asyncio.sleep(3600)

# ==========================================

async def main():
    """Main entry point"""
    logger.info("🚀 Starting Jaseb Bot...")
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register routers
    dp.include_router(store.router)
    dp.include_router(login.router)
    dp.include_router(admin.router)
    dp.include_router(panel.router)
    dp.include_router(settings.router)
    
    # Set bot commands
    # await set_bot_commands(bot)
    
    logger.info("✓ Bot initialized")
    logger.info("✓ Handlers registered")
    
    # 🔥 PENTING: Jalankan satpam di background pakai create_task
    # Ini bikin Satpam jalan paralel tanpa nge-blokir fungsi start_polling
    checker_task = asyncio.create_task(auto_expired_checker())
    
    try:
        # Start polling
        logger.info("📡 Starting polling...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("⏸️ Bot stopped by user")
    finally:
        checker_task.cancel() # Matiin satpam kalau botnya dimatiin
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())