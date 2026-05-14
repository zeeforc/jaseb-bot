from database.connection import supabase
from core.logger import logger
from datetime import datetime, timedelta

db = supabase

# ===== USER OPERATIONS =====
def get_or_create_user(telegram_id: int, username: str):
    """Get user kalau ada, Create kalau belum ada (Upsert logic)"""
    try:
        # Cek user
        response = db.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if not response.data:
            # Create baru kalau kosong
            db.table("users").insert({
                "telegram_id": telegram_id,
                "username": username,
                "paket": "free"
            }).execute()
            logger.info(f"✓ User baru {telegram_id} terdaftar")
            return {"telegram_id": telegram_id, "username": username, "paket": "free"}
        return response.data[0]
    except Exception as e:
        logger.error(f"✗ Error di get_or_create_user: {e}")
        return None

def update_user(telegram_id: int, data: dict):
    """Update user data (misal: update paket premium)"""
    try:
        response = db.table("users").update(data).eq("telegram_id", telegram_id).execute()
        logger.info(f"✓ User {telegram_id} updated")
        return response.data
    except Exception as e:
        logger.error(f"✗ Error updating user: {e}")
        return None

# ===== SESSION OPERATIONS =====

def create_session(telegram_id: int, phone_number: str, string_session: str):
    """Create session untuk userbot"""
    try:
        response = db.table("sessions").insert({
            "telegram_id": telegram_id,
            "phone_number": phone_number,
            "session_string": string_session,
            "is_active": True
        }).execute()
        logger.info(f"✓ Session untuk user {telegram_id} created")
        return response.data
    except Exception as e:
        logger.error(f"✗ Error creating session: {e}")
        return None

def get_sessions_by_user(telegram_id: int):
    """Satu user bisa punya banyak akun jaseb/session"""
    try:
        response = db.table("sessions").select("*").eq("telegram_id", telegram_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"✗ Error getting session: {e}")
        return []

def update_session(session_id: str, data: dict):
    """Update settingan Jaseb (misal update pesan atau jeda)"""
    try:
        response = db.table("sessions").update(data).eq("id", session_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"✗ Error updating session: {e}")
        return None

def get_user_session(telegram_id: int):
    try:
        res = db.table("sessions").select("session_string").eq("telegram_id", telegram_id).execute()
        return res.data[0]["session_string"] if res.data else None
    except: return None

# ===== GRUP TARGET OPERATIONS =====

def add_target_group(session_id: str, group_id: int, group_name: str):
    """Nambahin grup ke spesifik sesi bot Jaseb"""
    try:
        response = db.table("target_groups").insert({
            "session_id": session_id,
            "group_id": group_id,
            "group_name": group_name
        }).execute()
        logger.info(f"✓ Group {group_name} added to session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"✗ Error adding group: {e}")
        return None

def get_target_groups(session_id: str):
    """Get semua grup yang jadi target dari satu akun jaseb"""
    try:
        response = db.table("target_groups").select("*").eq("session_id", session_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"✗ Error getting groups: {e}")
        return []

def delete_target_group(group_id: int, session_id: str):
    """Delete spesifik grup dari akun jaseb"""
    try:
        db.table("target_groups").delete().match({"group_id": group_id, "session_id": session_id}).execute()
        logger.info(f"✓ Group {group_id} deleted")
        return True
    except Exception as e:
        logger.error(f"✗ Error deleting group: {e}")
        return False

def create_token(token: str, tipe_paket: str, durasi_hari: int):
    """Admin: Insert token baru ke tabel tokens"""
    try:
        response = db.table("tokens").insert({
            "token": token,
            "tipe_paket": tipe_paket,
            "durasi_hari": durasi_hari,
            "is_used": False
        }).execute()
        logger.info(f"✓ Token {token} berhasil dibuat di DB")
        return True
    except Exception as e:
        logger.error(f"✗ Error creating token: {e}")
        return False

def verify_and_claim_token(telegram_id: int, token_input: str) -> tuple[bool, str]:
    """Cek token, kalau valid langsung update paket user dengan logika Akumulasi"""
    try:
        # 1. Cari token di database
        res = db.table("tokens").select("*").eq("token", token_input).eq("is_used", False).execute()
        
        # Kalau token nggak ada atau udah kepakai
        if not res.data:
            return False, "Token tidak valid, salah ketik, atau sudah digunakan."
        
        token_data = res.data[0]
        tipe_paket = token_data["tipe_paket"]
        durasi_hari = token_data["durasi_hari"]

        # 2. Tarik data user untuk ngecek sisa waktu mereka saat ini
        user_resp = db.table("users").select("*").eq("telegram_id", telegram_id).execute()
        sekarang = datetime.now()

        if user_resp.data:
            user_data = user_resp.data[0]
            paket_lama = user_data.get("paket")
            expired_lama_str = user_data.get("expired_at")

            # Ubah teks expired dari Supabase jadi format Waktu Python
            if expired_lama_str:
                try:
                    clean_date_str = str(expired_lama_str).split('+')[0].split('.')[0]
                    expired_lama = datetime.fromisoformat(clean_date_str)
                except Exception:
                    expired_lama = sekarang
            else:
                expired_lama = sekarang

            # --- 🔥 LOGIKA AKUMULASI DURASI (BISNIS MODE) 🔥 ---
            if paket_lama == tipe_paket and expired_lama > sekarang:
                # Skenario 1: Paket SAMA dan MASIH AKTIF -> Sisa hari ditambahkan!
                new_expired = expired_lama + timedelta(days=durasi_hari)
            else:
                # Skenario 2: Paket BEDA (Upgrade) ATAU Sudah Mati -> Dihitung dari 0 hari ini!
                new_expired = sekarang + timedelta(days=durasi_hari)
        else:
            # Skenario 3: User sama sekali belum ada di database
            new_expired = sekarang + timedelta(days=durasi_hari)

        # 3. Hanguskan Token (Update is_used jadi True)
        db.table("tokens").update({
            "is_used": True,
            "used_by": telegram_id
        }).eq("token", token_input).execute()

        # 4. Update Paket User & Expired Date
        db.table("users").update({
            "paket": tipe_paket,
            "expired_at": new_expired.isoformat() # Supabase butuh format ISO
        }).eq("telegram_id", telegram_id).execute()

        logger.info(f"✓ User {telegram_id} sukses klaim token {token_input}. Expired baru: {new_expired}")
        return True, tipe_paket

    except Exception as e:
        logger.error(f"✗ Error saat claim token: {e}")
        return False, "Terjadi kesalahan pada server database."

def update_user_setting(telegram_id: int, kolom: str, value: any) -> bool:
    """Fungsi universal untuk update settingan di tabel users"""
    try:
        db.table("users").update({
            kolom: value
        }).eq("telegram_id", telegram_id).execute()
        
        logger.info(f"✓ Setting '{kolom}' untuk user {telegram_id} diupdate menjadi: {value}")
        return True
    except Exception as e:
        logger.error(f"✗ Error update setting {kolom}: {e}")
        return False

def check_session_exists(telegram_id: int) -> bool:
    """Mengecek apakah user sudah login (punya session) di database"""
    try:
        response = db.table("sessions").select("*").eq("telegram_id", telegram_id).execute()
        # Kalau datanya ada, return True. Kalau kosong, return False.
        return len(response.data) > 0 
    except Exception as e:
        logger.error(f"✗ Error ngecek session: {e}")
        return False
    
def get_user_data(telegram_id: int):
    """Ambil semua data user dari tabel users"""
    try:
        res = db.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"✗ Error get user data: {e}")
        return None

def add_target_group(telegram_id: int, target: str) -> bool:
    """Tambah grup ke database, cegah duplikat"""
    try:
        # Bersihkan spasi
        target = target.strip()
        # Cek apakah grup ini sudah ada sebelumnya
        cek = db.table("target_groups").select("*").eq("telegram_id", telegram_id).eq("target", target).execute()
        if cek.data:
            return True # Kalau udah ada, anggap aja sukses (skip)
            
        # Kalau belum ada, insert baru
        db.table("target_groups").insert({
            "telegram_id": telegram_id,
            "target": target
        }).execute()
        return True
    except Exception as e:
        logger.error(f"✗ Error add target group: {e}")
        return False

def get_target_groups(telegram_id: int) -> list:
    """Ambil semua daftar grup milik user"""
    try:
        res = db.table("target_groups").select("target").eq("telegram_id", telegram_id).execute()
        return [item["target"] for item in res.data]
    except Exception as e:
        logger.error(f"✗ Error get target groups: {e}")
        return []

def delete_target_group(telegram_id: int, target: str) -> bool:
    """Hapus satu grup spesifik"""
    try:
        target = target.strip()
        db.table("target_groups").delete().eq("telegram_id", telegram_id).eq("target", target).execute()
        return True
    except Exception as e:
        return False

def delete_all_target_groups(telegram_id: int) -> bool:
    """Hapus semua grup sekaligus"""
    try:
        db.table("target_groups").delete().eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        return False

def get_all_users():
    try:
        response = supabase.table("users").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"✗ Error get_all_users: {e}")
        return []

def get_all_transactions():
    """Tarik semua riwayat transaksi yang sudah LUNAS untuk laporan admin"""
    try:
        # Kita ambil yang statusnya PAID (Lunas) dan diurutkan dari yang terbaru
        response = db.table("transactions").select("*").eq("status", "PAID").order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"✗ Error get_all_transactions: {e}")
        return []