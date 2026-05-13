# bot/handlers/login.py
import re
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.states.form import LoginForm
from engine.manager import manager
from database.crud import create_session

router = Router()

# ==========================================
# 1. TRIGGER LOGIN DARI TOMBOL
# ==========================================
# Menangkap klik tombol "Buat Userbot" dari menu utama
@router.callback_query(F.data == "buat_userbot")
async def btn_buat_userbot(callback: types.CallbackQuery, state: FSMContext):
    teks = (
        "📱 <b>Login Akun Jaseb</b>\n\n"
        "Masukkan nomor telepon Telegram Anda dengan awalan kode negara.\n"
        "(contoh: <code>+6281234567890</code>)\n\n"
        "<i>Ketik /start untuk membatalkan proses ini.</i>"
    )
    await callback.message.edit_text(text=teks, parse_mode="HTML")
    await state.set_state(LoginForm.asking_phone)

# (Opsional) Tetap pertahankan perintah /login buat jaga-jaga
@router.message(Command("login"))
async def cmd_login(message: types.Message, state: FSMContext):
    teks = (
        "📱 <b>Login Akun Jaseb</b>\n\n"
        "Masukkan nomor telepon Telegram Anda dengan awalan kode negara.\n"
        "(contoh: <code>+6281234567890</code>)\n\n"
        "<i>Ketik /start untuk membatalkan.</i>"
    )
    await message.answer(text=teks, parse_mode="HTML")
    await state.set_state(LoginForm.asking_phone)

# ==========================================
# 2. PROSES MEMINTA OTP
# ==========================================
@router.message(LoginForm.asking_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    
    if phone.startswith("/start"):
        await state.clear()
        await message.answer("❌ Proses login dibatalkan. Ketik /start untuk kembali ke menu.")
        return

    # Validasi format nomor telepon sederhana
    if not phone.startswith("+") or not phone[1:].isdigit():
        await message.answer("❌ Format nomor salah! Pastikan menggunakan awalan +, contoh: +6281234567890")
        return

    # Kasih loading message
    loading_msg = await message.answer("⏳ Sedang meminta kode OTP dari Telegram...")

    # Panggil fungsi request OTP dari manager.py
    sukses = await manager.request_otp(message.from_user.id, phone)

    if sukses:
        # Simpan nomor telepon di memory FSM sementara
        await state.update_data(phone=phone)
        
        teks_otp = (
            f"✅ <b>Kode OTP telah dikirim ke {phone} via Telegram.</b>\n\n"
            "⚠️ <b>PENTING (ANTI-BANNED):</b>\n"
            "Ketik kode dengan spasi atau huruf di depannya agar akun tidak terdeteksi bot!\n"
            "<i>Contoh jika kode 12345: ketik <code>1 2 3 4 5</code> atau <code>OTP 12345</code></i>\n\n"
            "Silakan masukkan kode OTP Anda:"
        )
        await loading_msg.edit_text(teks_otp, parse_mode="HTML")
        await state.set_state(LoginForm.asking_otp)
    else:
        await loading_msg.edit_text("❌ Gagal meminta OTP. Pastikan nomor benar dan tidak sedang terkena limit Telegram.")
        await state.clear()

# ==========================================
# 3. VERIFIKASI OTP & SIMPAN KE DATABASE
# ==========================================
@router.message(LoginForm.asking_otp)
async def process_otp(message: types.Message, state: FSMContext):
    raw_otp = message.text.strip()
    
    if raw_otp.startswith("/start"):
        await state.clear()
        await message.answer("❌ Proses login dibatalkan.")
        return

    # Bersihkan input OTP user dari spasi dan huruf (mengambil angkanya saja)
    clean_otp = re.sub(r'\D', '', raw_otp)

    if not clean_otp:
        await message.answer("❌ Harap masukkan angka OTP yang valid!")
        return

    user_data = await state.get_data()
    phone = user_data.get("phone")

    loading_msg = await message.answer("⏳ Memverifikasi OTP dan membuat sesi...")

    # Panggil fungsi verify OTP di manager.py untuk mendapatkan String Session
    string_session = await manager.verify_otp(message.from_user.id, clean_otp)

    if string_session:
            # --- 🔥 SATPAM DATABASE TAMBAHAN 🔥 ---
            # Pastikan user terdaftar di tabel 'users' sebelum nyimpen session
            from database.crud import get_or_create_user
            
            # Kita ambil username telegram-nya (kalo ga punya, pake nama depannya aja)
            username_tele = message.from_user.username or message.from_user.first_name
            get_or_create_user(message.from_user.id, username_tele)
            # ----------------------------------------

            # Baru deh Simpan ke Database
            simpan_db = create_session(message.from_user.id, phone, string_session)
            
            if simpan_db:
                from bot.handlers.panel import get_panel_text
                from bot.keyboards.inline import kb_panel_utama
                
                await loading_msg.edit_text(
                    text=get_panel_text(message.from_user.id), 
                    reply_markup=kb_panel_utama(), 
                    parse_mode="HTML"
                )
            else:
                await loading_msg.edit_text("❌ Login Telegram sukses, tapi gagal menyimpan ke Database. Hubungi Admin.")
            
            await state.clear()