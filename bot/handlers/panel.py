# bot/handlers/panel.py
from aiogram.exceptions import TelegramBadRequest
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import (
    kb_panel_utama, kb_mulai_promosi, kb_fitur_premium,
    kb_atur_pesan, kb_atur_grup, kb_tambah_grup,
    kb_atur_jeda, kb_base_reply, kb_notif
)
from bot.states.form import PanelForm
from database.crud import update_user_setting, get_user_data
from aiogram.types import LinkPreviewOptions
from database.crud import (
    update_user_setting, get_user_data, 
    add_target_group, get_target_groups, 
    delete_target_group, delete_all_target_groups
)
from database.crud import get_user_session, add_target_group
from engine.worker import fetch_all_groups_from_account, worker
from datetime import datetime
from aiogram.filters import Command
router = Router()

def get_panel_text(user_id: int) -> str:
    """Fungsi helper untuk nampilin teks status panel kontrol dengan data AKTUAL dari Database"""
    # 1. Tarik data aktual user dari database
    user_data = get_user_data(user_id) or {}
    
    # 2. Cek Status Mesin Promosi (Berjalan atau Berhenti)
    is_running = user_data.get("is_running", False)
    status_promosi = "✅ Aktif" if is_running else "❌ Nonaktif"
    
    # 3. Cek Status Base Reply (Resepsionis)
    is_reply_active = user_data.get("base_reply_active", False)
    status_reply = "✅ Aktif" if is_reply_active else "❌ Nonaktif"
    
    # 4. Ambil Info Paket & Format biar rapi (contoh: "basic_sultan" -> "Basic Sultan")
    paket_raw = user_data.get("paket", "free")
    paket_rapi = str(paket_raw).replace("_", " ").title()
    
    # 5. Ambil Info Expired
    expired_raw = user_data.get("expired_at")
    if expired_raw:
        # Data dari Supabase formatnya panjang "2026-06-04T18:08:51...", kita potong ambil tanggalnya aja
        expired_rapi = str(expired_raw)[:10] 
    else:
        expired_rapi = "Selamanya (No Limit)" if paket_raw == "free" else "Belum Diatur"

    return (
        "🚀 <b>Panel Kontrol Auto Promosi</b> 🚀\n\n"
        f"⭐ <b>Auto Promosi:</b> {status_promosi}\n"
        f"💬 <b>WTB Reply:</b> {status_reply}\n"
        "🛡 <b>PM Permit:</b> ✅ Aktif\n"
        f"🆔 <b>ID Userbot:</b> <code>{user_id}</code>\n"
        f"💎 <b>Paket:</b> <b>{paket_rapi}</b>\n"
        f"⏳ <b>Kedaluwarsa:</b> {expired_rapi}\n\n"
        "🔔 <b>Ads:</b> JASEB TERBAIK HANYA DI @Zft'Store"
    )

# --- NAVIGASI KEMBALI KE MENU UTAMA PANEL ---
@router.callback_query(F.data == "nav_panel_utama")
async def nav_main_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear() # Bersihin memori input kalau user neken tombol kembali
    teks = get_panel_text(callback.from_user.id)
    await callback.message.edit_text(text=teks, reply_markup=kb_panel_utama(), parse_mode="HTML")

# --- NAVIGASI MENU UTAMA ---
# ==========================================
# HELPER & HANDLER: PANEL STATUS PROMOSI
# ==========================================
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_promosi_ui(user_id: int):
    """Pabrik UI Tunggal: Menjamin Teks dan Tombol 100% Sinkron"""
    user_data = get_user_data(user_id) or {}
    grup_list = get_target_groups(user_id) or []
    
    # 🔥 NORMALISASI MUTLAK (Penghancur Jebakan "False" = True)
    raw_status = user_data.get("is_running", False)
    if isinstance(raw_status, str):
        is_running = raw_status.lower() in ['true', '1', 'yes', 't']
    else:
        is_running = bool(raw_status)
        
    # 1. RAKIT TEKS & TOMBOL DARI SATU VARIABEL (is_running)
    status_ikon = "✅ BERJALAN" if is_running else "❌ BERHENTI"
    teks_tombol = "⏹️ Stop Promosi" if is_running else "▶️ Mulai Promosi"
    
    jeda_grup = user_data.get("jeda_grup", 0)
    jeda_putaran = user_data.get("jeda_putaran", 0)
    
    teks_ui = (
        "▶️ <b>Status Promosi</b>\n\n"
        f"Status: <b>{status_ikon}</b>\n"
        f"Target Grup: <b>{len(grup_list)} grup</b>\n"
        f"Jeda Grup: {jeda_grup} detik\n"
        f"Jeda Putaran: {jeda_putaran} menit\n\n"
        "<i>Pastikan semua amunisi siap sebelum klik Start!</i>"
    )
    
    kb_ui = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=teks_tombol, callback_data="toggle_promosi")],
        [InlineKeyboardButton(text="🏠 Menu Utama", callback_data="nav_panel_utama")]
    ])
    
    return teks_ui, kb_ui, is_running

# ==========================================
# FITUR 3B: CEK MASA AKTIF & STATUS PAKET
# ==========================================
@router.message(Command("cek", "status"))
async def cmd_cek_status(message: types.Message):
    """Fitur ngecek sisa masa aktif langganan user"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id) or {}
    
    # 1. Ambil Nama Paket & Limit Harian (Dinamis sesuai logika lu kemaren)
    paket_raw = user_data.get("paket", "free")
    paket_rapi = str(paket_raw).replace("_", " ").title()
    limit_harian = 100 if "sultan" in str(paket_raw).lower() else 50
    
    # 2. Ambil dan Hitung Sisa Waktu Kedaluwarsa
    expired_raw = user_data.get("expired_at")
    
    if expired_raw:
        try:
            # Format Supabase: 2026-06-04T18:08:51.123456
            # Kita potong bagian timezone/fractional biar gampang dihitung
            clean_date_str = str(expired_raw).split('+')[0].split('.')[0]
            exp_date = datetime.fromisoformat(clean_date_str)
            sekarang = datetime.now()
            
            # Hitung selisih harinya
            sisa_waktu = exp_date - sekarang
            sisa_hari = sisa_waktu.days
            
            if sisa_hari < 0:
                status_waktu = "🔴 KEDALUWARSA"
                sisa_hari = 0
            else:
                status_waktu = f"🟢 AKTIF ({sisa_hari} Hari Lagi)"
                
            expired_str = exp_date.strftime("%d %B %Y, %H:%M WIB")
        except Exception as e:
            # Fallback kalau format tanggalnya ada yang aneh
            expired_str = str(expired_raw)[:10]
            status_waktu = "🟢 AKTIF"
    else:
        expired_str = "Selamanya (No Limit)" if paket_raw == "free" else "Belum Diatur"
        status_waktu = "🟢 AKTIF"

    # 3. Rakit Pesan Balasan yang Rapi & Mewah
    teks = (
        "🛡️ <b>STATUS AKUN JASEB BOT</b> 🛡️\n\n"
        f"👤 <b>ID:</b> <code>{user_id}</code>\n"
        f"💎 <b>Paket:</b> {paket_rapi}\n"
        f"⚡ <b>Batas Kirim:</b> {limit_harian} Pesan/Hari\n\n"
        f"📅 <b>Masa Aktif:</b> {expired_str}\n"
        f"📌 <b>Status:</b> {status_waktu}\n\n"
        "<i>Untuk memperpanjang masa aktif, silakan ke menu /toko atau hubungi Admin.</i>"
    )
    
    await message.answer(teks, parse_mode="HTML")

@router.callback_query(F.data == "panel_mulai")
async def nav_mulai_promosi(callback: types.CallbackQuery):
    """Nampilin menu Start dengan UI yang udah disatukan"""
    user_id = callback.from_user.id
    
    # Langsung minta UI dari Pabrik
    teks_baru, kb_baru, _ = build_promosi_ui(user_id)
    
    await callback.message.edit_text(text=teks_baru, reply_markup=kb_baru, parse_mode="HTML")

@router.callback_query(F.data == "toggle_promosi")
async def control_worker(callback: types.CallbackQuery):
    """Tombol Sakti Start/Stop Mesin Userbot"""
    user_id = callback.from_user.id
    
    # 1. Cek status UI sekarang, lalu siapkan kebalikannya
    _, _, is_running_sekarang = build_promosi_ui(user_id)
    status_baru = not is_running_sekarang 
    
    # 2. Validasi amunisi kalau mau ngegas
    if status_baru: 
        user_data = get_user_data(user_id) or {}
        pesan = user_data.get("pesan_teks") or user_data.get("pesan_forward")
        grup_list = get_target_groups(user_id)
        if not pesan or not grup_list:
            await callback.answer("❌ Gagal! Pesan atau Target Grup belum diatur.", show_alert=True)
            return
            
    # 3. UPDATE DATABASE
    update_user_setting(user_id, "is_running", status_baru)
    
    # 4. TARIK UI BARU SETELAH DATABASE BERUBAH
    teks_baru, kb_baru, _ = build_promosi_ui(user_id)
    
    try:
        await callback.message.edit_text(text=teks_baru, reply_markup=kb_baru, parse_mode="HTML")
        teks_notif = "▶️ Mesin Dinyalakan!" if status_baru else "⏹️ Mesin Dimatikan!"
        await callback.answer(teks_notif)
    except Exception:
        await callback.answer("Sedang memproses...", show_alert=False)

# Kodingan di bawahnya biarkan lanjut ke @router.callback_query(F.data == "panel_premium")

@router.callback_query(F.data == "panel_premium")
async def nav_fitur_premium(callback: types.CallbackQuery):
    teks = "💎 <b>Menu Fitur Tambahan:</b>\n\nSilakan pilih fitur premium yang ingin Anda gunakan."
    await callback.message.edit_text(text=teks, reply_markup=kb_fitur_premium(), parse_mode="HTML")

@router.callback_query(F.data == "panel_pesan")
async def nav_atur_pesan(callback: types.CallbackQuery):
    teks = "📝 <b>Pengaturan Pesan Promosi:</b>\n\nAtur pesan yang akan dikirimkan oleh bot ke target grup Anda."
    await callback.message.edit_text(text=teks, reply_markup=kb_atur_pesan(), parse_mode="HTML")

@router.callback_query(F.data == "panel_grup")
async def nav_atur_grup(callback: types.CallbackQuery):
    teks = "👥 <b>Pengaturan Target Grup:</b>\n\nKelola daftar target grup yang akan menjadi tujuan promosi Anda."
    await callback.message.edit_text(text=teks, reply_markup=kb_atur_grup(), parse_mode="HTML")

@router.callback_query(F.data == "grup_tambah")
async def nav_tambah_grup(callback: types.CallbackQuery):
    teks = "➕ <b>Pilih Metode Penambahan Grup:</b>\n\nSilakan pilih bagaimana Anda ingin menambahkan target grup."
    await callback.message.edit_text(text=teks, reply_markup=kb_tambah_grup(), parse_mode="HTML")

@router.callback_query(F.data == "panel_jeda")
async def nav_atur_jeda(callback: types.CallbackQuery):
    teks = "⏱️ <b>Pengaturan Interval Waktu:</b>\n\nAtur waktu jeda antar pengiriman pesan agar akun terhindar dari limit Telegram."
    await callback.message.edit_text(text=teks, reply_markup=kb_atur_jeda(), parse_mode="HTML")

@router.callback_query(F.data == "panel_reply")
async def nav_base_reply(callback: types.CallbackQuery):
    teks = (
        "💬 <b>AUTO WTB REPLY CONFIGURATION</b> ⚡️\n\n"
        "Cara Kerja: Bot akan otomatis merespons pesan ke orang yang chat Anda.\n\n"
        "Status System: 🔴 OFFLINE\n"
        "Status Timer: Tidak ada timer aktif"
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_base_reply(), parse_mode="HTML")

@router.callback_query(F.data == "panel_notif")
async def nav_notif(callback: types.CallbackQuery):
    teks = "🔔 <b>Pengaturan Notifikasi:</b>\n\nMasukkan username Telegram yang akan menerima laporan hasil Auto Promosi secara otomatis."
    await callback.message.edit_text(text=teks, reply_markup=kb_notif(), parse_mode="HTML")

@router.callback_query(F.data == "panel_panduan")
async def nav_panduan(callback: types.CallbackQuery):
    teks = (
        "📚 <b>Panduan Penggunaan Userbot:</b>\n\n"
        "1. Pastikan Anda sudah mengatur <b>Pesan Promosi</b>.\n"
        "2. Tambahkan <b>Target Grup</b> (otomatis/manual).\n"
        "3. Atur <b>Jeda</b> agar aman dari banned (disarankan jeda antar grup >30 detik).\n"
        "4. Kembali ke menu utama dan klik <b>Mulai Promosi</b>.\n\n"
        "<i>Bot akan tetap berjalan otomatis di latar belakang tanpa henti.</i>"
    )
    # Bikin tombol "Menu Utama" dadakan khusus untuk panduan
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb_back = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Menu Utama", callback_data="nav_panel_utama")]
    ])
    await callback.message.edit_text(text=teks, reply_markup=kb_back, parse_mode="HTML")

# ==========================================
# FASE 3: SISTEM INPUT - ATUR JEDA
# ==========================================

# 1. Trigger saat user ngeklik tombol "Jeda Antar Grup"
@router.callback_query(F.data == "jeda_grup")
async def ask_jeda_grup(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "⏳ <b>Atur Jeda Antar Grup</b>\n\n"
        "Masukkan angka jeda dalam hitungan <b>detik</b>.\n"
        "<i>(Contoh: ketik <code>10</code> untuk jeda 10 detik antar grup).</i>\n\n"
        "👉 Silakan ketik angkanya di bawah ini:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.setting_jeda_grup) # Nyalakan mode memori

# 2. Penangkap saat user ngetik angkanya
@router.message(PanelForm.setting_jeda_grup)
async def save_jeda_grup(message: types.Message, state: FSMContext):
    jeda_input = message.text.strip()
    
    # Validasi: Pastikan user ngetik angka, bukan huruf
    if not jeda_input.isdigit():
        await message.answer("❌ Format salah! Harap ketik angka saja (contoh: 10).")
        return
        
    # Simpan ke Database
    sukses = update_user_setting(message.from_user.id, "jeda_grup", int(jeda_input))
    
    if sukses:
        teks_sukses = f"✅ <b>Jeda Antar Grup</b> berhasil disimpan: <b>{jeda_input} detik</b>!"
        await message.answer(teks_sukses, reply_markup=kb_atur_jeda(), parse_mode="HTML")
        await state.clear() # Matikan mode memori
    else:
        await message.answer("❌ Gagal menyimpan ke database. Hubungi Admin.")

# 3. Trigger saat user ngeklik tombol "Jeda Antar Putaran"
@router.callback_query(F.data == "jeda_putaran")
async def ask_jeda_putaran(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "🔄 <b>Atur Jeda Antar Putaran</b>\n\n"
        "Masukkan angka jeda dalam hitungan <b>menit</b>.\n"
        "<i>(Contoh: ketik <code>5</code> untuk istirahat 5 menit setelah selesai 1 putaran).</i>\n\n"
        "👉 Silakan ketik angkanya di bawah ini:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.setting_jeda_putaran)

# 4. Penangkap saat user ngetik angkanya
@router.message(PanelForm.setting_jeda_putaran)
async def save_jeda_putaran(message: types.Message, state: FSMContext):
    jeda_input = message.text.strip()
    
    if not jeda_input.isdigit():
        await message.answer("❌ Format salah! Harap ketik angka saja (contoh: 5).")
        return
        
    sukses = update_user_setting(message.from_user.id, "jeda_putaran", int(jeda_input))
    
    if sukses:
        teks_sukses = f"✅ <b>Jeda Antar Putaran</b> berhasil disimpan: <b>{jeda_input} menit</b>!"
        await message.answer(teks_sukses, reply_markup=kb_atur_jeda(), parse_mode="HTML")
        await state.clear()
    else:
        await message.answer("❌ Gagal menyimpan ke database.")

# logic pesan teks biasa
# 1. Trigger saat user ngeklik tombol "Pesan Teks/Media"
@router.callback_query(F.data == "pesan_teks")
async def ask_pesan_teks(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "📝 <b>Atur Pesan Teks</b>\n\n"
        "Silakan tempel (paste) atau ketik pesan promosi Anda di sini.\n"
        "<i>(Format tebal/miring/link bawaan Telegram akan otomatis tersimpan)</i>\n\n"
        "👉 Kirim pesan Anda sekarang:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.setting_pesan_teks)

# 2. Penangkap saat user ngirim teks promosinya
@router.message(PanelForm.setting_pesan_teks)
async def save_pesan_teks(message: types.Message, state: FSMContext):
    pesan_input = message.html_text 
    
    if not pesan_input:
        await message.answer("❌ Harap kirimkan pesan berbentuk teks!")
        return

    # KUNCI: Simpan pesan teks, dan KOSONGKAN pesan forward
    sukses_simpan = update_user_setting(message.from_user.id, "pesan_teks", pesan_input)
    update_user_setting(message.from_user.id, "pesan_forward", None) # Menghapus pesan lama
    
    if sukses_simpan:
        await message.answer("✅ <b>Pesan Promosi Teks berhasil disimpan!</b>\n<i>(Pesan mode Forward otomatis dinonaktifkan)</i>", reply_markup=kb_atur_pesan(), parse_mode="HTML")
        await state.clear()
    else:
        await message.answer("❌ Gagal menyimpan pesan ke database.")

# 3. Trigger saat user ngeklik tombol "Lihat Pesan" (UPDATE V2 - FULL MESSAGE)
@router.callback_query(F.data == "pesan_lihat")
async def lihat_pesan_tersimpan(callback: types.CallbackQuery):
    user_data = get_user_data(callback.from_user.id)
    
    if not user_data:
        await callback.answer("Gagal mengambil data.", show_alert=True)
        return

    pesan_teks = user_data.get("pesan_teks")
    pesan_forward = user_data.get("pesan_forward")
    
    if not pesan_teks and not pesan_forward:
        teks = "❌ <b>Belum Ada Pesan!</b>\n\nAnda belum mengatur pesan promosi apapun."
        await callback.message.edit_text(text=teks, reply_markup=kb_atur_pesan(), parse_mode="HTML")
        return

    # Hapus bubble menu saat ini biar rapi dan nggak numpuk
    await callback.message.delete()
    
    # Kirim Header
    await callback.message.answer("👀 <b>Pesan Promosi Anda Saat Ini:</b>", parse_mode="HTML")
    
    # 1. Tampilkan pesan teks (jika ada)
    if pesan_teks:
        await callback.message.answer(f"📝 <b>Pesan Teks:</b>\n\n{pesan_teks}", parse_mode="HTML")
    
    # 2. Tampilkan pesan forward secara FULL (jika ada)
    if pesan_forward:
        if pesan_forward.startswith("msg_id:"):
            # JIKA USER MENGGUNAKAN FITUR FORWARD PESAN MANUAL
            msg_id = int(pesan_forward.split(":")[1])
            try:
                await callback.message.bot.copy_message(
                    chat_id=callback.from_user.id,
                    from_chat_id=callback.from_user.id,
                    message_id=msg_id
                )
            except Exception as e:
                await callback.message.answer("❌ <i>Gagal memuat wujud pesan forward. Mungkin pesan aslinya sudah terhapus dari obrolan ini.</i>", parse_mode="HTML")
        
        else:
            # 🔥 FIX: JIKA USER MENGGUNAKAN LINK (KITA PAKSA BOT FORWARD WUJUD ASLINYA)
            try:
                # Bedah link t.me/username/123 buat ngambil ID Channel dan ID Pesan
                raw_url = str(pesan_forward).strip().split("?")[0]
                parts = raw_url.split("/")
                
                source_msg_id = int(parts[-1])
                source_chat = parts[-2]
                
                # Format penulisan ID Channel
                if len(parts) >= 3 and parts[-3] == "c":
                    source_chat = int("-100" + str(source_chat))
                elif not str(source_chat).startswith("@") and not str(source_chat).startswith("-100"):
                    source_chat = "@" + str(source_chat)
                    
                # Bot langsung mem-forward wujud asli pesan dari channel ke layar panel user
                await callback.bot.forward_message(
                    chat_id=callback.from_user.id,
                    from_chat_id=source_chat,
                    message_id=source_msg_id
                )
                
            except Exception as e:
                # Fallback: Kalau bot gagal narik (misal karena channelnya Private dan Bot lu bukan admin/member di sana)
                await callback.message.answer(
                    text=f"↪️ <b>Pesan Forward (Link):</b>\n{pesan_forward}\n\n<i>⚠️ Bot panel tidak bisa menampilkan wujud asli karena channel di-private. Jangan khawatir, mesin Userbot akan tetap bisa mengirimnya nanti!</i>",
                    link_preview_options=LinkPreviewOptions(is_disabled=False),
                    parse_mode="HTML"
                )
            
    # 3. Munculkan kembali tombol navigasinya di paling bawah
    await callback.message.answer(
        text="<i>Pilih menu di bawah untuk mengubah pesan:</i>",
        reply_markup=kb_atur_pesan(),
        parse_mode="HTML"
    )
# logic pesan forward

# 1. Trigger saat user ngeklik tombol "Pesan Forward"
@router.callback_query(F.data == "pesan_forward")
async def ask_pesan_forward(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "↪️ <b>Atur Pesan Forward</b>\n\n"
        "Anda bisa menggunakan 2 cara:\n"
        "1. <b>Kirim Link Pesan:</b> (Contoh: <code>https://t.me/usernamechannel/123</code>)\n"
        "2. <b>Forward Pesan:</b> Langsung <i>forward</i> (teruskan) pesan dari grup/channel lain ke bot ini.\n\n"
        "👉 Silakan kirim Link atau Forward pesannya sekarang:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.setting_pesan_forward)

# 2. Penangkap saat user ngirim link / nge-forward pesan
@router.message(PanelForm.setting_pesan_forward)
async def save_pesan_forward(message: types.Message, state: FSMContext):
    data_to_save = ""
    
    # Deteksi apakah user ngirim Link atau nge-Forward pesan
    if message.text and "t.me/" in message.text:
        data_to_save = message.text.strip()
        tipe = "Link Pesan"
    else:
        data_to_save = f"msg_id:{message.message_id}"
        tipe = "ID Pesan Forward"

    # KUNCI: Simpan pesan forward, dan KOSONGKAN pesan teks
    sukses_simpan = update_user_setting(message.from_user.id, "pesan_forward", data_to_save)
    update_user_setting(message.from_user.id, "pesan_teks", None) # Menghapus pesan lama
    
    if sukses_simpan:
        teks_sukses = f"✅ <b>Pesan Forward berhasil disimpan!</b>\n(Tipe: {tipe})\n<i>(Pesan mode Teks otomatis dinonaktifkan)</i>"
        await message.answer(teks_sukses, reply_markup=kb_atur_pesan(), parse_mode="HTML")
        await state.clear()
    else:
        await message.answer("❌ Gagal menyimpan pesan ke database.")

# ==========================================
# FASE 3: SISTEM INPUT - ATUR TARGET GRUP
# ==========================================

# 1. TAMBAH GRUP MANUAL
@router.callback_query(F.data == "grup_tambah_manual")
async def ask_tambah_manual(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "✍️ <b>Tambah Grup Manual</b>\n\n"
        "Silakan kirimkan <i>username</i> grup target Anda.\n"
        "Contoh: <code>@grubjblokal</code>\n\n"
        "<i>(Anda juga bisa mengirimkan banyak grup sekaligus, pisahkan dengan koma atau baris baru)</i>\n\n"
        "👉 Kirim username grup sekarang:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.adding_group_manual)

@router.message(PanelForm.adding_group_manual)
async def save_grup_manual(message: types.Message, state: FSMContext):
    input_text = message.text
    
    # Kita pisahkan teks pakai koma atau baris baru, jadi user bisa masukin banyak sekaligus
    import re
    grup_list = re.split(r'[,\n]+', input_text)
    
    sukses_count = 0
    for grup in grup_list:
        grup = grup.strip()
        if grup.startswith("@") or "t.me/" in grup or grup.startswith("-100"): # Validasi sederhana
            if add_target_group(message.from_user.id, grup):
                sukses_count += 1
                
    if sukses_count > 0:
        await message.answer(f"✅ <b>Berhasil menyimpan {sukses_count} grup!</b>", reply_markup=kb_atur_grup(), parse_mode="HTML")
    else:
        await message.answer("❌ Tidak ada grup valid yang ditambahkan. Pastikan pakai awalan @ (contoh: @grupku).")
    await state.clear()

# 2. DAFTAR GRUP
@router.callback_query(F.data == "grup_daftar")
async def lihat_daftar_grup(callback: types.CallbackQuery):
    grup_list = get_target_groups(callback.from_user.id)
    
    if not grup_list:
        teks = "❌ <b>Belum Ada Grup Target!</b>\n\nAnda belum menambahkan grup manapun."
    else:
        teks = f"📋 <b>Daftar Target Grup Anda ({len(grup_list)} Grup):</b>\n\n"
        for i, grup in enumerate(grup_list, 1):
            teks += f"{i}. {grup}\n"
            
    await callback.message.edit_text(text=teks, reply_markup=kb_atur_grup(), parse_mode="HTML", disable_web_page_preview=True)

# 3. HAPUS GRUP
@router.callback_query(F.data == "grup_hapus")
async def ask_hapus_grup(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "🗑️ <b>Hapus Target Grup</b>\n\n"
        "Ketik <i>username</i> grup yang ingin dihapus (contoh: <code>@grubjblokal</code>).\n\n"
        "Atau, ketik kata <b>HAPUS SEMUA</b> untuk mengosongkan seluruh daftar grup Anda.\n\n"
        "👉 Kirim balasan Anda sekarang:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.deleting_group)

@router.message(PanelForm.deleting_group)
async def proses_hapus_grup(message: types.Message, state: FSMContext):
    input_text = message.text.strip()
    
    if input_text.upper() == "HAPUS SEMUA":
        if delete_all_target_groups(message.from_user.id):
            await message.answer("✅ <b>SELURUH GRUP BERHASIL DIHAPUS!</b>", reply_markup=kb_atur_grup(), parse_mode="HTML")
        else:
            await message.answer("❌ Gagal menghapus grup.")
    else:
        if delete_target_group(message.from_user.id, input_text):
            await message.answer(f"✅ Grup <b>{input_text}</b> berhasil dihapus dari daftar!", reply_markup=kb_atur_grup(), parse_mode="HTML")
        else:
            await message.answer("❌ Gagal menghapus grup.")
            
    await state.clear()

# ==========================================
# FASE 3: SISTEM INPUT - BASE REPLY
# ==========================================

# 1. Tambah Pesan Reply
@router.callback_query(F.data == "reply_tambah")
async def ask_tambah_reply(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "💬 <b>Tambah Pesan Base Reply</b>\n\n"
        "Pesan ini akan dikirim otomatis jika ada seseorang yang mengirim pesan ke akun (userbot) Anda.\n\n"
        "👉 Kirim pesan Auto Reply Anda sekarang:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.adding_base_reply)

@router.message(PanelForm.adding_base_reply)
async def save_base_reply(message: types.Message, state: FSMContext):
    pesan_input = message.html_text
    if update_user_setting(message.from_user.id, "base_reply_text", pesan_input):
        await message.answer("✅ <b>Pesan Auto Reply berhasil disimpan!</b>\nJangan lupa klik 'Aktifkan Reply' di menu sebelumnya.", reply_markup=kb_base_reply(), parse_mode="HTML")
    else:
        await message.answer("❌ Gagal menyimpan pesan reply.")
    await state.clear()

# 2. Hapus Pesan Reply
@router.callback_query(F.data == "reply_hapus")
async def hapus_base_reply(callback: types.CallbackQuery):
    update_user_setting(callback.from_user.id, "base_reply_text", None)
    update_user_setting(callback.from_user.id, "base_reply_active", False) # Otomatis matiin fiturnya
    await callback.answer("🗑️ Pesan Base Reply berhasil dihapus!", show_alert=True)

# 3. Toggle On/Off Base Reply
@router.callback_query(F.data == "reply_toggle")
async def toggle_base_reply(callback: types.CallbackQuery):
    user_data = get_user_data(callback.from_user.id)
    
    # Cek apakah user udah bikin pesan reply-nya atau belum
    if not user_data or not user_data.get("base_reply_text"):
        await callback.answer("❌ Anda belum menambahkan pesan Base Reply! Silakan tambah pesan dulu.", show_alert=True)
        return
        
    # Balikkan status (kalau False jadi True, kalau True jadi False)
    current_status = user_data.get("base_reply_active", False)
    new_status = not current_status
    
    update_user_setting(callback.from_user.id, "base_reply_active", new_status)
    status_text = "AKTIF ✅" if new_status else "NONAKTIF ❌"
    
    await callback.message.edit_text(f"🔄 <b>Status Base Reply sekarang: {status_text}</b>", reply_markup=kb_base_reply(), parse_mode="HTML")


# ==========================================
# FASE 3: SISTEM INPUT - FITUR PREMIUM & NOTIF
# ==========================================

# 1. Custom Watermark
@router.callback_query(F.data == "prem_watermark")
async def ask_watermark(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "©️ <b>Atur Custom Watermark</b>\n\n"
        "Watermark akan disematkan di bagian paling bawah pada setiap pesan promosi Anda.\n"
        "<i>(Contoh: 🌟 Trusted by JasebJiro)</i>\n\n"
        "👉 Kirim teks watermark Anda:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.setting_watermark)

@router.message(PanelForm.setting_watermark)
async def save_watermark(message: types.Message, state: FSMContext):
    if update_user_setting(message.from_user.id, "custom_watermark", message.html_text):
        await message.answer("✅ <b>Custom Watermark berhasil disimpan!</b>", reply_markup=kb_fitur_premium(), parse_mode="HTML")
    else:
        await message.answer("❌ Gagal menyimpan watermark.")
    await state.clear()

# 2. Notif Username
@router.callback_query(F.data == "notif_username")
async def ask_notif_username(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "🔔 <b>Atur Penerima Laporan</b>\n\n"
        "Masukkan username Telegram (menggunakan @) yang akan menerima pesan laporan putaran bot.\n"
        "<i>(Contoh: @akunutama_jiro)</i>\n\n"
        "👉 Kirim username penerima laporan:"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.setting_notif_user)

@router.message(PanelForm.setting_notif_user)
async def save_notif_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith("@"):
        await message.answer("❌ Format salah! Harap gunakan awalan @ (contoh: @username_anda).")
        return
        
    if update_user_setting(message.from_user.id, "notif_username", username):
        await message.answer(f"✅ <b>Penerima Laporan diatur ke: {username}</b>", reply_markup=kb_notif(), parse_mode="HTML")
    else:
        await message.answer("❌ Gagal menyimpan username notifikasi.")
    await state.clear()

@router.callback_query(F.data == "grup_tambah_semua")
async def proses_tambah_semua_grup(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    await callback.message.edit_text("⏳ <b>Sedang memindai akun Anda...</b>", parse_mode="HTML")
    
    # Ambil session string dari database
    # Di crud.py lu, pastikan ada fungsi get_user_session atau sejenisnya
    session_string = get_user_session(user_id) 
    
    if not session_string:
        await callback.message.edit_text("❌ Session tidak ditemukan. Silakan login ulang.")
        return
        
    daftar_grup = await fetch_all_groups_from_account(session_string)
    
    sukses_count = 0
    for grup in daftar_grup:
        # Menggunakan fungsi add_target_group dari crud.py lu
        if add_target_group(user_id, grup):
            sukses_count += 1
            
    await callback.message.edit_text(
        f"✅ Berhasil menarik <b>{sukses_count}</b> grup!",
        reply_markup=kb_atur_grup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "prem_proxy")
async def ask_proxy(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "🌐 <b>Pengaturan Proxy SOCKS5 (Anti-Banned)</b>\n\n"
        "Gunakan proxy untuk menyembunyikan IP asli bot Anda.\n\n"
        "👉 <b>Format Pengisian:</b>\n"
        "<code>IP:PORT:USERNAME:PASSWORD</code>\n\n"
        "<i>Contoh: 192.168.1.1:8080:zoro:rahasia123</i>\n"
        "(Jika proxy Anda tanpa username/password, cukup ketik <code>IP:PORT</code>)\n\n"
        "🗑 Ketik <b>HAPUS</b> untuk mematikan proxy."
    )
    # Note: Pastikan lu nambahin tombol callback_data="prem_proxy" di file inline.py lu ya!
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(PanelForm.setting_proxy)

@router.message(PanelForm.setting_proxy)
async def save_proxy(message: types.Message, state: FSMContext):
    text_input = message.text.strip()
    user_id = message.from_user.id
    
    # 1. Fitur Hapus Proxy
    if text_input.upper() == "HAPUS":
        update_user_setting(user_id, "proxy_host", None)
        update_user_setting(user_id, "proxy_port", None)
        update_user_setting(user_id, "proxy_user", None)
        update_user_setting(user_id, "proxy_pass", None)
        await message.answer("✅ <b>Proxy berhasil dihapus!</b> Bot akan kembali menggunakan IP Default Server.", parse_mode="HTML")
        await state.clear()
        return

    # 2. Fitur Simpan Proxy
    parts = text_input.split(":")
    if len(parts) < 2:
        await message.answer("❌ Format salah! Gunakan format IP:PORT atau IP:PORT:USER:PASS")
        return

    host = parts[0]
    port = parts[1]
    user = parts[2] if len(parts) > 2 else None
    password = parts[3] if len(parts) > 3 else None

    if not port.isdigit():
        await message.answer("❌ Port harus berupa angka!")
        return

    # Simpan ke Supabase
    update_user_setting(user_id, "proxy_host", host)
    update_user_setting(user_id, "proxy_port", int(port))
    update_user_setting(user_id, "proxy_user", user)
    update_user_setting(user_id, "proxy_pass", password)

    teks_sukses = f"✅ <b>Proxy Berhasil Disimpan!</b>\n🌐 IP: <code>{host}</code>\n🔌 Port: <code>{port}</code>\n\n<i>Proxy akan aktif saat Anda me-restart mesin promosi.</i>"
    await message.answer(teks_sukses, parse_mode="HTML")
    await state.clear()@router.callback_query(F.data == "panel_mulai")
async def nav_mulai_promosi(callback: types.CallbackQuery):
    """Nampilin menu Start dengan tombol Pintar"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id) or {}
    
    # 🔥 PENGAMAN TIPE DATA (Biar gak salah baca True/False dari Supabase)
    is_running = user_data.get("is_running", False)
    if isinstance(is_running, str):
        is_running = is_running.lower() == 'true'
    
    teks = get_status_promosi_text(user_id)
    
    # Cek status buat nentuin teks tombol
    teks_tombol = "⏹️ Stop Promosi" if is_running else "▶️ Mulai Promosi"
    
    kb_pintar = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=teks_tombol, callback_data="toggle_promosi")],
        [InlineKeyboardButton(text="🏠 Menu Utama", callback_data="nav_panel_utama")]
    ])
    
    await callback.message.edit_text(text=teks, reply_markup=kb_pintar, parse_mode="HTML")