# bot/keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb_welcome(has_session: bool = False) -> InlineKeyboardMarkup:
    """Gambar 1: Menu Utama /start (Dibuat Dinamis)"""
    
    # RAKIT BARIS PERTAMA SECARA DINAMIS
    baris_pertama = []
    
    if not has_session:
        # Kalau belum login, tampilin tombol Buat Userbot
        baris_pertama.append(InlineKeyboardButton(text="☄️ Buat Userbot", callback_data="buat_userbot"))
    else:
        # Kalau udah login, ganti jadi tombol balik ke Panel Kontrol
        baris_pertama.append(InlineKeyboardButton(text="🛠️ Ke Panel Kontrol", callback_data="nav_panel_utama"))
        
    # Tombol Toko selalu ada di sebelah kanannya
    baris_pertama.append(InlineKeyboardButton(text="🛒 Toko", callback_data="store_main"))

    return InlineKeyboardMarkup(inline_keyboard=[
        baris_pertama, # <-- Baris pertama yang udah dirakit otomatis
        [InlineKeyboardButton(text="🎫 Klaim Token", callback_data="klaim_token")],
        [
            InlineKeyboardButton(text="📑 Panduan Buat", callback_data="panduan_buat"),
            InlineKeyboardButton(text="♛ Fitur Unggulan", callback_data="fitur_unggulan")
        ],
        [InlineKeyboardButton(text="🎁 Coba Gratis", callback_data="coba_gratis")]
    ])

def kb_store_main() -> InlineKeyboardMarkup:
    """Gambar 2: Menu Toko Utama"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ Beli Userbot", callback_data="store_beli_userbot")],
        [InlineKeyboardButton(text="🗂️ Bulk Userbot", callback_data="store_bulk")],
        # [
        #     InlineKeyboardButton(text="🌐 Beli Username Grup", callback_data="store_grup"),
        #     InlineKeyboardButton(text="🤝 Beli Reseller", callback_data="store_reseller")
        # ],
        [InlineKeyboardButton(text="❌ Batal", callback_data="nav_main_menu")]
    ])

def kb_syarat_ketentuan() -> InlineKeyboardMarkup:
    """Gambar 3: Kebijakan & Ketentuan"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Setuju & Lanjutkan", callback_data="store_pilih_tipe")],
        [InlineKeyboardButton(text="❌ Tutup", callback_data="nav_main_menu")]
    ])

def kb_pilih_tipe() -> InlineKeyboardMarkup:
    """Gambar 4: Pilih Tipe Layanan"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 (Full Fitur) Basic", callback_data="store_tipe_basic"),
            InlineKeyboardButton(text="👑 (Full Fitur) Spesial", callback_data="store_tipe_spesial")
        ],
        # [
        #     InlineKeyboardButton(text="🎯 WTB Basic", callback_data="store_tipe_wtb_basic"),
        #     InlineKeyboardButton(text="🎯 WTB Spesial", callback_data="store_tipe_wtb_spesial")
        # ],
        [InlineKeyboardButton(text="🏠︎︎ Menu Utama", callback_data="nav_main_menu")]
    ])

def kb_varian_basic() -> InlineKeyboardMarkup:
    """Gambar 5: Varian Layanan Basic"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Basic Hemat (Rp 6.000)", callback_data="checkout_basic_hemat")],
        [InlineKeyboardButton(text="🟢 Basic Sultan (Rp 10.000)", callback_data="checkout_basic_sultan")],
        [InlineKeyboardButton(text="❌ Batal", callback_data="store_pilih_tipe")]
    ])

def kb_varian_spesial() -> InlineKeyboardMarkup:
    """Gambar 7: Varian Layanan Spesial"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Spesial Hemat (Rp 20.000)", callback_data="checkout_spesial_hemat")],
        [InlineKeyboardButton(text="🔵 Spesial Sultan (Rp 25.000)", callback_data="checkout_spesial_sultan")],
        [InlineKeyboardButton(text="❌ Batal", callback_data="store_pilih_tipe")]
    ])

def kb_lanjut_bayar() -> InlineKeyboardMarkup:
    """Gambar 6: Tombol Lanjut Bayar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Lanjut Pembayaran", callback_data="bayar_admin")],
        [InlineKeyboardButton(text="❌ Batal", callback_data="store_pilih_tipe")]
    ])
# ==========================================
# KEYBOARD PANEL KONTROL USERBOT
# ==========================================

def kb_panel_utama() -> InlineKeyboardMarkup:
    """Menu Utama Panel Kontrol"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Mulai Promosi", callback_data="panel_mulai"),
         InlineKeyboardButton(text="💎 Fitur Premium", callback_data="panel_premium")],
        [InlineKeyboardButton(text="📝 Atur Pesan", callback_data="panel_pesan"),
         InlineKeyboardButton(text="👥 Atur Grup", callback_data="panel_grup"),
         InlineKeyboardButton(text="⏱️ Atur Jeda", callback_data="panel_jeda")],
        [InlineKeyboardButton(text="💬 Auto Reply", callback_data="panel_reply"),
         InlineKeyboardButton(text="🔔 Notif Laporan", callback_data="panel_notif")],
        [InlineKeyboardButton(text="📓 Panduan Pakai", callback_data="panel_panduan")]
    ])

def kb_mulai_promosi() -> InlineKeyboardMarkup:
    """Tombol di menu Mulai Promosi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏸️ Stop Promosi", callback_data="act_stop_promosi")],
        [InlineKeyboardButton(text="🏠︎ Menu Utama", callback_data="nav_panel_utama")]
    ])

def kb_fitur_premium() -> InlineKeyboardMarkup:
    """Tombol di menu Fitur Premium"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Broadcast PM", callback_data="prem_broadcast"),
         InlineKeyboardButton(text="©️ Custom Watermark", callback_data="prem_watermark")],
        [InlineKeyboardButton(text="🌐 Atur Proxy (Anti-Banned)", callback_data="prem_proxy")],
        [InlineKeyboardButton(text="🏠︎ Menu Utama", callback_data="nav_panel_utama")]
    ])

def kb_atur_pesan() -> InlineKeyboardMarkup:
    """Tombol di menu Atur Pesan"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Pesan Teks/Media", callback_data="pesan_teks")],
        [InlineKeyboardButton(text="↪️ Pesan Forward", callback_data="pesan_forward")],
        [InlineKeyboardButton(text="👀 Lihat Pesan", callback_data="pesan_lihat")],
        [InlineKeyboardButton(text="🏠︎ Menu Utama", callback_data="nav_panel_utama")]
    ])

def kb_atur_grup() -> InlineKeyboardMarkup:
    """Tombol di menu Atur Grup"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Tambah Grup", callback_data="grup_tambah"),
         InlineKeyboardButton(text="🗑️ Hapus Grup", callback_data="grup_hapus")],
        [InlineKeyboardButton(text="📋 Daftar Grup", callback_data="grup_daftar")],
        [InlineKeyboardButton(text="🏠︎ Menu Utama", callback_data="nav_panel_utama")]
    ])

def kb_tambah_grup() -> InlineKeyboardMarkup:
    """Tombol Sub-menu Tambah Grup"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Tambah Manual", callback_data="grup_tambah_manual")],
        [InlineKeyboardButton(text="🌐 Tambah Semua Grup", callback_data="grup_tambah_semua")],
        [InlineKeyboardButton(text="🔙 Kembali", callback_data="panel_grup")]
    ])

def kb_atur_jeda() -> InlineKeyboardMarkup:
    """Tombol di menu Atur Jeda"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Jeda Antar Grup", callback_data="jeda_grup")],
        [InlineKeyboardButton(text="🔄 Jeda Antar Putaran", callback_data="jeda_putaran")],
        [InlineKeyboardButton(text="🏠︎ Menu Utama", callback_data="nav_panel_utama")]
    ])

def kb_base_reply() -> InlineKeyboardMarkup:
    """Tombol di menu Base Reply"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 Aktifkan/Nonaktifkan Reply", callback_data="reply_toggle")],
        [InlineKeyboardButton(text="➕ Tambah Reply", callback_data="reply_tambah"),
         InlineKeyboardButton(text="🗑️ Hapus Reply", callback_data="reply_hapus")],
        [InlineKeyboardButton(text="🏠︎ Menu Utama", callback_data="nav_panel_utama")]
    ])

def kb_notif() -> InlineKeyboardMarkup:
    """Tombol di menu Notif"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Username Penerima", callback_data="notif_username")],
        [InlineKeyboardButton(text="🏠︎ Menu Utama", callback_data="nav_panel_utama")]
    ])