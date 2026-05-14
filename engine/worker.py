"""
worker.py - Background Task buat looping kirim pesan ke grup & fungsi fetch
"""
import asyncio
from core.logger import logger
from engine.manager import manager
from core.config import API_ID, API_HASH
from pyrogram import Client
from pyrogram.enums import ChatType


# ==========================================
# FUNGSI: TARIK SEMUA GRUP OTOMATIS
# ==========================================
async def fetch_all_groups_from_account(session_string: str) -> list:
    app = Client(
        name="temp_userbot",
        session_string=session_string,
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    
    grup_list = []
    try:
        await app.start()
        logger.info("✅ Userbot berhasil login untuk scan grup!")
        
        async for dialog in app.get_dialogs():
            if dialog.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                if dialog.chat.username:
                    grup_list.append(f"@{dialog.chat.username}")
                else:
                    grup_list.append(str(dialog.chat.id))
                    
        await app.stop()
        return grup_list
        
    except Exception as e:
        logger.error(f"✗ Gagal fetch grup: {e}")
        return []
# worker class
class MessageWorker:
    def __init__(self):
        self.tasks = {}  
        self.running = {}  
        self.putaran_ke = {} 
        self.last_sent_msgs = {}
        self.daily_counts = {}
        # self.LIMIT_HARIAN = 8
    
    async def send_messages_to_groups(self, user_id: int):
        """Mesin utama pengirim pesan promosi (Looping) dengan Manager"""
        from database.crud import get_user_data, get_target_groups, get_user_session
        from pyrogram.enums import ParseMode 
        from datetime import datetime, timedelta, timezone # Untuk hitung jam WIB

        # 1. AUTO-WAKE UP MANAGER 
        client = manager.get_client(user_id)
        if not client:
            logger.info(f"🔄 Membangunkan mesin user {user_id} ke Manager...")
            session_string = get_user_session(user_id)
            if not session_string:
                self.running[user_id] = False
                return
            
            client = manager.create_client(user_id, session_string)

        # PASTIKAN CLIENT TERHUBUNG SEBELUM LOOPING
        try:
            if not client.is_connected:
                await client.start()
        except Exception as e:
            if "already started" not in str(e): 
                logger.error(f"✗ Gagal start client di worker: {e}")
                self.running[user_id] = False
                return

        # Inisialisasi angka putaran (Mulai dari 1)
        if user_id not in self.putaran_ke:
            self.putaran_ke[user_id] = 1

        # 2. LOOPING UTAMA
        while self.running.get(user_id, False):
            try:
                user_data = get_user_data(user_id)
                groups = get_target_groups(user_id)
                
                if not groups:
                    self.running[user_id] = False
                    break

                pesan_teks = user_data.get("pesan_teks")
                pesan_forward = user_data.get("pesan_forward")
                watermark = user_data.get("custom_watermark", "")
                notif_username = user_data.get("notif_username")
                
                # --- 🔥 FITUR 2C: PENGECEKAN PAKET & LIMIT HARIAN ---
                paket_user = user_data.get("paket", "basic") # Default ke basic kalau kosong
                
                # Tentukan batas limit sesuai paketnya
                limit_harian = 100 if paket_user in ["sultan", "spesial"] else 50

                from datetime import datetime, timedelta, timezone
                tz_wib = timezone(timedelta(hours=7))
                hari_ini = datetime.now(tz_wib).strftime("%Y-%m-%d")
                
                # Reset counter jadi 0 kalau udah ganti hari
                if user_id not in self.daily_counts or self.daily_counts[user_id].get("date") != hari_ini:
                    self.daily_counts[user_id] = {"date": hari_ini, "count": 0}
                if pesan_teks == "None": pesan_teks = None
                if pesan_forward == "None": pesan_forward = None

                final_text = ""
                if pesan_teks:
                    final_text = f"{pesan_teks}\n\n{watermark}" if watermark else pesan_teks

                logger.info(f"🚀 Putaran {self.putaran_ke[user_id]} dimulai! Mengirim ke {len(groups)} grup...")

                # --- 🔥 VARIABEL PENGUMPUL DATA LAPORAN ---
                total_grup = len(groups)
                berhasil = 0
                gagal = 0
                gagal_list = []

                # 3. Mulai Blast ke Grup
                for group_id in groups:
                    if not self.running.get(user_id, False): break
                    
                    sukses_kirim = False
                    error_reason = ""
                    
                    try:
                        # --- 🔥 FITUR 2B: AUTO-DELETE PESAN LAMA ---
                        if user_id in self.last_sent_msgs and group_id in self.last_sent_msgs[user_id]:
                            old_msg_ids = self.last_sent_msgs[user_id][group_id]
                            if old_msg_ids:
                                try:
                                    # Hapus pesan putaran sebelumnya di grup ini
                                    await client.delete_messages(chat_id=group_id, message_ids=old_msg_ids)
                                except Exception:
                                    pass # Abaikan kalau gagal (misal admin matiin akses delete)
                                self.last_sent_msgs[user_id][group_id] = [] # Kosongkan setelah dihapus

                        # Siapkan list buat nyimpen ID pesan yang baru dikirim
                        new_msg_ids = []

                        # SKENARIO 1: USER PAKAI LINK FORWARD
                        if pesan_forward and "t.me/" in str(pesan_forward):
                            raw_url = str(pesan_forward).strip().split("?")[0] 
                            parts = raw_url.split("/")
                            
                            source_msg_id = int(parts[-1])
                            source_chat = parts[-2]
                            
                            if len(parts) >= 3 and parts[-3] == "c":
                                source_chat = int("-100" + str(source_chat))
                            elif not str(source_chat).startswith("@") and not str(source_chat).startswith("-100"):
                                source_chat = "@" + str(source_chat)
                                
                            terkirim = await client.forward_messages(
                                chat_id=group_id,
                                from_chat_id=source_chat,
                                message_ids=source_msg_id
                            )
                            new_msg_ids.append(terkirim.id)
                            
                            if watermark:
                                wm_msg = await client.send_message(group_id, f"<b>{watermark}</b>", parse_mode=ParseMode.HTML)
                                new_msg_ids.append(wm_msg.id)
                                
                            sukses_kirim = True
                            
                        # SKENARIO 2: USER PAKAI PESAN TEKS BISA
                        elif final_text:
                            terkirim = await client.send_message(
                                chat_id=group_id, 
                                text=final_text,
                                parse_mode=ParseMode.HTML, 
                                disable_web_page_preview=True 
                            )
                            new_msg_ids.append(terkirim.id)
                            sukses_kirim = True
                        else:
                            error_reason = "Pesan promosi belum diatur!"
                            
                        if sukses_kirim and new_msg_ids:
                            if user_id not in self.last_sent_msgs:
                                self.last_sent_msgs[user_id] = {}
                            self.last_sent_msgs[user_id][group_id] = new_msg_ids
                            
                    except Exception as e:
                        error_str = str(e)
                        if "CHAT_WRITE_FORBIDDEN" in error_str:
                            error_reason = "Tidak punya izin mengirim pesan (mute/ban)."
                        elif "PEER_ID_INVALID" in error_str or "USERNAME_INVALID" in error_str or "CHANNEL_PRIVATE" in error_str:
                            error_reason = "Grup tidak ditemukan atau ID salah."
                        else:
                            # Menyesuaikan dengan gaya raw error Telegram
                            if error_str.startswith("["):
                                error_reason = f"Telegram says: {error_str}"
                            elif error_str.startswith("Telegram says:"):
                                error_reason = error_str
                            else:
                                error_reason = f"Telegram says: [{type(e).__name__}] - {error_str}"

                    # --- 🔥 UPDATE STATISTIK LAPORAN SETELAH KIRIM ---
                    if sukses_kirim:
                        berhasil += 1
                        self.daily_counts[user_id]["count"] += 1
                        logger.info(f"✓ Sukses kirim ke {group_id}")
                    else:
                        gagal += 1
                        gagal_list.append(f"{gagal}. {group_id}\n   {error_reason}")
                        logger.error(f"✗ Gagal di grup {group_id}: {error_reason}")
                        
                    # Jeda antar grup
                    jeda = user_data.get("jeda_grup", 10)
                    await asyncio.sleep(jeda)

                # 4. 🔥 KIRIM LAPORAN NOTIFIKASI PM 🔥
                if self.running.get(user_id, False):
                    jeda_putaran = user_data.get("jeda_putaran", 5)
                    
                    # Hitung jam WIB untuk putaran selanjutnya
                    tz_wib = timezone(timedelta(hours=7))
                    waktu_lanjut = datetime.now(tz_wib) + timedelta(minutes=jeda_putaran)
                    waktu_str = waktu_lanjut.strftime("%H:%M:%S")

                    # Susun teks sesuai format gambar
                    if notif_username:
                        teks_laporan = (
                            "🚀 <b>Laporan Auto Promosi</b> 🚀\n\n"
                            f"• Putaran Ke: <b>{self.putaran_ke[user_id]}</b>\n"
                            f"• Total Grup: <b>{total_grup}</b>\n"
                            f"• ✅ Berhasil: <b>{berhasil}</b>\n"
                            f"• ❌ Gagal: <b>{gagal}</b>\n"
                        )
                        
                        if gagal_list:
                            # Max 40 grup di laporan biar pesan nggak kepanjangan (mencegah limit teks Telegram)
                            teks_laporan += "\n" + "\n".join(gagal_list[:40])
                            if len(gagal_list) > 40:
                                teks_laporan += f"\n... <i>dan {len(gagal_list)-40} grup lainnya.</i>"
                        
                        teks_laporan += f"\n\n⏳ <i>Putaran selanjutnya akan dimulai sekitar pukul {waktu_str} WIB</i>"

                        try:
                            await client.send_message(
                                chat_id=notif_username, 
                                text=teks_laporan, 
                                parse_mode=ParseMode.HTML, 
                                disable_web_page_preview=True
                            )
                            logger.info(f"✓ Laporan PM putaran {self.putaran_ke[user_id]} terkirim ke {notif_username}")
                        except Exception as e:
                            logger.error(f"✗ Gagal kirim laporan PM ke {notif_username}: {e}")

                    # Naikkan hitungan putaran buat sesi berikutnya
                    self.putaran_ke[user_id] += 1
                    # 5. Jeda Putaran (Cooldown)
                    logger.info(f"💤 Putaran selesai. Istirahat {jeda_putaran} menit...")
                    
                    # 🔥 FIX PROXY TIMEOUT: Putus koneksi sementara sebelum tidur panjang
                    if client.is_connected:
                        await client.stop()
                        
                    await asyncio.sleep(jeda_putaran * 60)
                    
                    # 🔥 Bangunkan dan konek ulang setelah istirahat selesai
                    if self.running.get(user_id, False):
                        logger.info("🔄 Menyambungkan ulang ke jaringan Proxy...")
                        await client.start()
                    # logger.info(f"💤 Putaran selesai. Istirahat {jeda_putaran} menit...")
                    # await manager.stop_client(user_id)
                    # await asyncio.sleep(jeda_putaran * 60)

            except Exception as e:
                logger.error(f"✗ Error fatal di worker: {e}")
                await asyncio.sleep(30)

    async def start_worker(self, user_id: int, *args, **kwargs):
        if self.running.get(user_id, False):
            logger.warning(f"Worker untuk user {user_id} sudah berjalan")
            return
        
        self.running[user_id] = True
        task = asyncio.create_task(self.send_messages_to_groups(user_id))
        self.tasks[user_id] = task
        logger.info(f"✓ Worker untuk user {user_id} dimulai")
    
    async def stop_worker(self, user_id: int):
        self.running[user_id] = False
        task = self.tasks.get(user_id)
        if task:
            task.cancel()
            del self.tasks[user_id]
            
        await manager.stop_client(user_id)
        logger.info(f"✓ Worker dan Mesin Pyrogram untuk user {user_id} dihentikan")

worker = MessageWorker()