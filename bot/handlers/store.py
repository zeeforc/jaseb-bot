from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from bot.keyboards.inline import (
    kb_welcome, kb_store_main, kb_syarat_ketentuan, 
    kb_pilih_tipe, kb_varian_basic, kb_varian_spesial, kb_lanjut_bayar
)
from aiogram.fsm.context import FSMContext
from bot.states.form import ClaimTokenState
from database.crud import verify_and_claim_token, check_session_exists
from bot.handlers.panel import get_panel_text
from bot.keyboards.inline import kb_panel_utama
from core.config import ADMIN_ID

router = Router()

# ==========================================
# 1. MENU UTAMA (/start)
# ==========================================
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    # --- 🔥 SATPAM DATABASE DI PINTU DEPAN 🔥 ---
    from database.crud import get_or_create_user
    username_tele = message.from_user.username or message.from_user.first_name
    get_or_create_user(message.from_user.id, username_tele)
    # ---------------------------------------------

    # CEK KE DATABASE: Apakah user ini udah pernah login?
    is_logged_in = check_session_exists(message.from_user.id)
    
    if is_logged_in:
        # JIKA SUDAH LOGIN -> Langsung lempar ke Panel Kontrol
        await message.answer(
            text=get_panel_text(message.from_user.id), 
            reply_markup=kb_panel_utama(), 
            parse_mode="HTML"
        )
    else:
        # JIKA BELUM LOGIN -> Tampilkan Menu Welcome, info ke keyboard kalau dia belum login (False)
        teks = (
            "── <b>Selamat Datang di Userbot Jiro</b> ──\n\n"
            f"Halo, <b>{message.from_user.first_name}</b>!\n"
            "Anda selangkah lebih dekat menuju Era Baru Promosi!\n\n"
            "Lupakan cara lama yang membuang waktu & tenaga. Bersama saya, promosi ke puluhan/ratusan grup ada dalam genggaman Anda, siap menerima pesan promosi secara otomatis, terjadwal, dan tanpa batas."
        )
        await message.answer(teks, reply_markup=kb_welcome(has_session=False), parse_mode="HTML")

# ==========================================
# PERINTAH /toko (Bisa dipanggil kapan aja)
# ==========================================
@router.message(Command("toko"))
async def cmd_toko(message: types.Message):
    is_logged_in = check_session_exists(message.from_user.id)
    teks = (
        "── <b>Toko & Layanan Userbot Jiro</b> ──\n\n"
        f"Halo, <b>{message.from_user.first_name}</b>!\n"
        "Silakan akses layanan toko, klaim token, atau perpanjang masa aktif Anda di sini."
    )
    # Kasih tau keyboard status login user yang sekarang
    await message.answer(text=teks, reply_markup=kb_welcome(has_session=is_logged_in), parse_mode="HTML")

# Tombol untuk kembali ke menu utama (Welcome) dari mana saja
@router.callback_query(F.data == "nav_main_menu")
async def back_to_main(callback: types.CallbackQuery):
    # Selalu cek status terbaru tiap kali user ngeklik tombol kembali
    is_logged_in = check_session_exists(callback.from_user.id)
    
    teks = (
        "── <b>Selamat Datang di Userbot Zoro</b> ──\n\n"
        f"Halo, <b>{callback.from_user.first_name}</b>!\n"
        "Anda selangkah lebih dekat menuju Era Baru Promosi!"
    )
    # Update tombol pakai status login terbaru
    await callback.message.edit_text(text=teks, reply_markup=kb_welcome(has_session=is_logged_in), parse_mode="HTML")

# ==========================================
# 2. MENU TOKO -> SYARAT KETENTUAN
# ==========================================
@router.callback_query(F.data == "store_main")
async def show_store_main(callback: types.CallbackQuery):
    teks = (
        "🛍️ <b>MENU STORE & LAYANAN</b>\n\n"
        "Silakan pilih kategori produk yang ingin Anda akses di bawah ini:"
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_store_main(), parse_mode="HTML")

@router.callback_query(F.data == "store_beli_userbot")
async def show_syarat(callback: types.CallbackQuery):
    teks = (
        "📜 <b>Kebijakan & Ketentuan Kami</b>\n\n"
        "🔸 Membeli berarti Anda menyetujui segala risiko!\n"
        "🔸 Panduan lengkap bisa langsung chat developer.\n"
        "🔸 Ketika terdeteksi melakukan hal ilegal (penipuan), langsung dibanned & dicabut akses userbotnya (No Refund).\n"
        "🔸 Garansi hanya berlaku untuk userbot tertentu.\n\n"
        "👉 <i>Jika Anda SETUJU, Tekan Tombol Di Bawah Ini.</i>"
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_syarat_ketentuan(), parse_mode="HTML")

# ==========================================
# 3. PILIH TIPE LAYANAN & VARIAN
# ==========================================
@router.callback_query(F.data == "store_pilih_tipe")
async def show_pilih_tipe(callback: types.CallbackQuery):
    teks = (
        "📦 <b>PILIH TIPE LAYANAN</b>\n\n"
        "Silakan pilih paket yang sesuai dengan kebutuhan Anda di bawah ini."
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_pilih_tipe(), parse_mode="HTML")

@router.callback_query(F.data == "store_tipe_basic")
async def show_varian_basic(callback: types.CallbackQuery):
    teks = (
        "⭐ <b>PILIH TIPE LAYANAN BASIC</b>\n\n"
        "<i>Silakan pilih jenis layanan yang Anda inginkan. Perbedaan utama terletak pada garansi dan backup.</i>\n\n"
        "⚡ <b>Basic Hemat (Non-Garansi)</b>\n"
        "Rp 6.000 /bulan\n"
        "• Harga lebih ekonomis\n"
        "• Tanpa Token Backup\n"
        "• Resiko logout/banned tanggung sendiri\n\n"
        "⚡ <b>Basic Sultan (Bergaransi)</b>\n"
        "Rp 10.000 /bulan\n"
        "• Fitur Full + Token Backup\n"
        "• Garansi login kembali via token\n"
        "• Aman & Nyaman jangka panjang"
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_varian_basic(), parse_mode="HTML")

@router.callback_query(F.data == "store_tipe_spesial")
async def show_varian_spesial(callback: types.CallbackQuery):
    teks = (
        "🌟 <b>PILIH TIPE LAYANAN SPESIAL</b>\n\n"
        "<i>Perbedaan dengan Basic: Mendukung fitur premium seperti Forward Messages & Premium Emoji.</i>\n\n"
        "🔥 <b>Spesial Hemat (Non-Garansi)</b>\n"
        "Rp 20.000 /bulan\n"
        "• Support Media & Forward\n"
        "• Tanpa Token Backup\n\n"
        "🔥 <b>Spesial Sultan (Bergaransi)</b>\n"
        "Rp 25.000 /bulan\n"
        "• Fitur Full Premium + Token Backup\n"
        "• Garansi login kembali via token"
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_varian_spesial(), parse_mode="HTML")

# ==========================================
# 4. CHECKOUT & HUBUNGI ADMIN
# ==========================================
# Menangkap klik dari semua tombol yang awalnya "checkout_"
@router.callback_query(F.data.startswith("checkout_"))
async def show_checkout(callback: types.CallbackQuery):
    # Mengambil nama paket dari callback data (contoh: "checkout_basic_sultan")
    paket = callback.data.replace("checkout_", "").replace("_", " ").title()
    
    # Set harga otomatis berdasarkan paket
    harga = "Rp 6.000"
    if "Basic Sultan" in paket: harga = "Rp 10.000"
    elif "Spesial Hemat" in paket: harga = "Rp 20.000"
    elif "Spesial Sultan" in paket: harga = "Rp 25.000"

    teks = (
        f"📝 <b>RINGKASAN PESANAN</b>\n\n"
        f"📦 Paket: <b>{paket}</b>\n"
        f"💵 Harga: <b>{harga} / bulan</b>\n"
        f"🤖 Jumlah: 1 Userbot\n\n"
        "<i>Silakan klik Lanjut Pembayaran untuk mendapatkan instruksi transfer.</i>"
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_lanjut_bayar(), parse_mode="HTML")

@router.callback_query(F.data == "bayar_admin")
async def hubungi_admin(callback: types.CallbackQuery):
    teks = (
        "💳 <b>INSTRUKSI PEMBAYARAN</b>\n\n"
        "Silakan lakukan pembayaran manual ke Admin. Payment ke @zftpaymn support Qris dan TF Dana\n\n"
        "👤 <b>Kontak Admin:</b> @zoroaze\n\n"
        "1. Chat admin dan kirimkan bukti transfer.\n"
        "2. Admin akan memberikan <b>TOKEN AKTIVASI</b> (Contoh: JASEB-BASIC-XYZ).\n"
        "3. Kembali ke bot ini, klik menu <b>Klaim Token</b> untuk mengaktifkan paket Anda."
    )
    # Hapus tombol supaya user fokus chat admin
    await callback.message.edit_text(text=teks, parse_mode="HTML")

# ==========================================
# 5. SISTEM KLAIM TOKEN (FSM)
# ==========================================

@router.callback_query(F.data == "klaim_token")
async def ask_for_token(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "🔑 <b>KLAIM TOKEN AKTIVASI</b>\n\n"
        "Silakan ketik atau <i>paste</i> Token yang Anda dapatkan dari Admin di sini:\n\n"
        "<i>(Ketik /start jika ingin membatalkan)</i>"
    )
    # Kirim pesan baru (nggak di-edit) biar kelihatan riwayatnya
    await callback.message.answer(text=teks, parse_mode="HTML")
    
    # Nyalakan mode "Merekam Input Token"
    await state.set_state(ClaimTokenState.waiting_for_token)
    await callback.answer() # Hilangin loading di tombol

@router.message(ClaimTokenState.waiting_for_token)
async def process_claim_token(message: types.Message, state: FSMContext):
    token_input = message.text.strip() # Bersihin spasi kalau user nggak sengaja kepencet spasi
    
    # Cek user nge-cancel atau nggak
    if token_input.startswith("/start"):
        await state.clear()
        await cmd_start(message)
        return
        
    # Panggil fungsi Database yang barusan kita bikin
    sukses, pesan_kembalian = verify_and_claim_token(message.from_user.id, token_input)
    
    if sukses:
        paket_rapi = pesan_kembalian.replace("_", " ").title() # Ubah "basic_sultan" jadi "Basic Sultan"
        teks_sukses = (
            "🎉 <b>KLAIM TOKEN BERHASIL!</b>\n\n"
            f"Selamat! Paket akun Anda sekarang telah di-upgrade menjadi <b>{paket_rapi}</b>.\n\n"
            "👉 Silakan klik tombol <b>🚀 Buat Userbot</b> di menu /start untuk menghubungkan nomor Telegram Anda dan memulai promosi otomatis!"
        )
        await message.answer(teks_sukses, parse_mode="HTML")
        
        # Matikan mode FSM karena udah berhasil
        await state.clear()
    else:
        # Kalau token salah, biarkan state tetap nyala biar user bisa coba ngetik lagi
        teks_gagal = (
            f"❌ <b>KLAIM GAGAL</b>\n\n"
            f"Alasan: {pesan_kembalian}\n\n"
            "Silakan periksa kembali Token Anda dan ketik ulang, atau ketik /start untuk membatalkan."
        )
        await message.answer(teks_gagal, parse_mode="HTML")

# ==========================================
# FITUR ADMIN: BROADCAST PENGUMUMAN
# ==========================================

@router.message(Command("broadcast"))
async def admin_broadcast(message: types.Message):
    # Validasi: Cuma Admin yang boleh pakai perintah ini!
    if message.from_user.id != ADMIN_ID:
        return

    # Ambil teks setelah kata "/broadcast"
    teks_pesan = message.text.replace("/broadcast", "").strip()
    
    if not teks_pesan:
        await message.answer("❌ Format salah!\nCara pakai: <code>/broadcast Halo semua, server sedang maintenance!</code>", parse_mode="HTML")
        return

    from database.crud import get_all_users
    semua_user = get_all_users()
    
    if not semua_user:
        await message.answer("❌ Gagal mengambil data user.")
        return

    await message.answer(f"⏳ <b>Memulai Broadcast ke {len(semua_user)} user...</b>", parse_mode="HTML")
    
    sukses = 0
    for user in semua_user:
        target_id = user.get("telegram_id")
        try:
            # Kasih header otomatis biar user tau ini dari lu
            pesan_final = f"📢 <b>PENGUMUMAN ADMIN</b> 📢\n\n{teks_pesan}"
            await message.bot.send_message(chat_id=target_id, text=pesan_final, parse_mode="HTML")
            sukses += 1
        except Exception:
            pass # Cuekin aja kalau gagal (misal user udah nge-blokir bot)
            
    await message.answer(f"✅ <b>Broadcast Selesai!</b>\nBerhasil terkirim ke {sukses} user.", parse_mode="HTML")