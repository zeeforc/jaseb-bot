"""
manager.py - Start/Stop Pyrogram client & Sistem Login OTP
"""
from pyrogram import Client
from core.config import API_ID, API_HASH
from core.logger import logger

import time
from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.enums import ParseMode
from database.crud import get_user_data
# 🔥 Cache Memory buat Anti-Spam Auto Reply
replied_cache = {}

async def auto_reply_handler(client, message):
    """Resepsionis yang nangkap PM masuk dan balas otomatis"""
    # 1. Validasi: Pastikan ini PM, dan bukan dari diri sendiri/bot lain
    if getattr(message.chat, "type", None) != "private" and str(getattr(message.chat, "type", "")) != "ChatType.PRIVATE":
        return
    if not getattr(message, "from_user", None) or message.from_user.is_self or message.from_user.is_bot:
        return
        
    # User_id dari pemilik userbot
    owner_id = client.me.id
    sender_id = message.from_user.id
    
    # 2. Sistem Cooldown (Anti-Spam 1 Jam)
    sekarang = time.time()
    if owner_id not in replied_cache:
        replied_cache[owner_id] = {}
        
    if sender_id in replied_cache[owner_id]:
        waktu_terakhir = replied_cache[owner_id][sender_id]
        if sekarang - waktu_terakhir < 3600: # 3600 detik = 1 jam
            return # Cuekin kalau belum 1 jam biar pembeli ga risih
            
    # 3. Cek Database: Apakah Base Reply Aktif?
    user_data = get_user_data(owner_id)
    if not user_data:
        return
        
    is_active = user_data.get("base_reply_active", False)
    reply_text = user_data.get("base_reply_text")
    
    # 4. Eksekusi Balasan!
    if is_active and reply_text:
        try:
            await message.reply_text(reply_text, parse_mode=ParseMode.HTML)
            # Simpan waktu balasan ke memori
            replied_cache[owner_id][sender_id] = sekarang
        except Exception as e:
            pass

class UserBotManager:
    """Manage Pyrogram client instances"""
    
    def __init__(self):
        self.clients = {}  # Klien yang udah aktif berjalan (running background)
        self.temp_clients = {}  # Klien sementara untuk proses login OTP
    
    # ===== SISTEM LOGIN OTP =====
    
    async def request_otp(self, telegram_id: int, phone_number: str) -> bool:
        """Request OTP ke Telegram server"""
        try:
            client = Client(
                name=f"temp_{telegram_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                in_memory=True 
            )
            await client.connect()
            sent_code = await client.send_code(phone_number)
            
            # Simpan data auth sementara
            self.temp_clients[telegram_id] = {
                "client": client,
                "phone_code_hash": sent_code.phone_code_hash,
                "phone": phone_number
            }
            logger.info(f"✓ OTP requested for {phone_number}")
            return True
        except Exception as e:
            logger.error(f"✗ Error requesting OTP: {e}")
            return False

    async def verify_otp(self, telegram_id: int, otp_code: str) -> str:
        """Verify OTP dan kembalikan String Session"""
        try:
            data = self.temp_clients.get(telegram_id)
            if not data:
                return None
                
            client = data["client"]
            await client.sign_in(data["phone"], data["phone_code_hash"], otp_code)
            
            # Berhasil login! Ekstrak string session
            string_session = await client.export_session_string()
            
            await client.disconnect()
            del self.temp_clients[telegram_id]
            
            logger.info(f"✓ String Session generated for {telegram_id}")
            return string_session
        except Exception as e:
            logger.error(f"✗ Error verifying OTP: {e}")
            if telegram_id in self.temp_clients:
                await self.temp_clients[telegram_id]["client"].disconnect()
                del self.temp_clients[telegram_id]
            return None

    # ===== MANAJEMEN KLIEN AKTIF =====
    
    def create_client(self, user_id: int, string_session: str) -> Client:
        """Create new Pyrogram client dengan dukungan PROXY"""
        try:
            from database.crud import get_user_data
            user_data = get_user_data(user_id) or {}
            
            # 1. Siapkan variabel config Proxy
            proxy_config = None
            
            # 2. Tarik data dari Supabase
            p_host = user_data.get("proxy_host")
            p_port = user_data.get("proxy_port")
            p_user = user_data.get("proxy_user")
            p_pass = user_data.get("proxy_pass")

            # 3. Rakit config-nya jika IP dan Port tersedia
            if p_host and p_port:
                proxy_config = {
                    "scheme": "socks5", # Sangat disarankan pakai SOCKS5 untuk Telegram
                    "hostname": p_host,
                    "port": int(p_port),
                    "username": p_user if p_user else None,
                    "password": p_pass if p_pass else None
                }
                logger.info(f"🌐 User {user_id} menggunakan Proxy: {p_host}")

            # 4. Suntikkan proxy_config ke dalam Client
            client = Client(
                name=f"jaseb_{user_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=string_session,
                proxy=proxy_config, # 🔥 PROXY BERAKSI DI SINI
                in_memory=True 
            )
            
            client.panel_user_id = user_id
            
            # Pastikan handler Base Reply lu tetep nyantol
            # HAPUS BARIS IMPORT DARI WORKER KARENA FUNGSINYA UDAH ADA DI ATAS FILE INI
            from pyrogram.handlers import MessageHandler
            from pyrogram import filters
            client.add_handler(MessageHandler(auto_reply_handler, filters.private))
            
            self.clients[user_id] = client
            return client
            
        except Exception as e:
            logger.error(f"✗ Error creating Pyrogram client: {e}")
            return None
            
    async def start_client(self, user_id: int):
        """Start Pyrogram client"""
        try:
            client = self.clients.get(user_id)
            if client:
                await client.start()
                logger.info(f"✓ Pyrogram client untuk user {user_id} started")
                return True
        except Exception as e:
            logger.error(f"✗ Error starting client: {e}")
        return False
    
    # Di dalam class UserBotManager di engine/manager.py
    async def stop_client(self, user_id: int):
        """Stop Pyrogram client dengan aman"""
        try:
            client = self.clients.get(user_id)
            if client:
                # Cek dulu apakah klien beneran lagi connect sebelum di-stop
                if client.is_connected:
                    await client.stop()
                    logger.info(f"✓ Pyrogram client untuk user {user_id} stopped dengan aman")
                del self.clients[user_id]
                return True
        except Exception as e:
            # Abaikan error 'Connection already closed'
            if "Connection already closed" not in str(e):
                logger.error(f"✗ Error stopping client: {e}")
            # Tetap hapus dari dictionary
            if user_id in self.clients:
                del self.clients[user_id]
        return False
    
    def get_client(self, user_id: int) -> Client:
        """Get client by user_id"""
        return self.clients.get(user_id)

# Global instance
manager = UserBotManager()