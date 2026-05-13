"""
settings.py - FSM atur jeda, masukin grup, atur pesan
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from bot.states.form import SettingsForm
from core.logger import logger

# Import fungsi database kita
from database.crud import update_session, add_target_group, get_sessions_by_user

router = Router()

# ==========================================
# 1. ATUR JEDA (Dari klik tombol Inline)
# ==========================================
@router.callback_query(F.data == "menu_jeda")
async def btn_atur_jeda(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.setting_delay)
    await callback.message.answer("⏱️ Berapa menit jeda antar pesan? (contoh: 10)")
    await callback.answer() # Hilangin loading di tombol

@router.message(SettingsForm.setting_delay)
async def process_delay(message: types.Message, state: FSMContext):
    try:
        delay = int(message.text)
        telegram_id = message.from_user.id
        
        # [Logika DB] Cari sesi Jaseb milik user ini
        sesi_user = get_sessions_by_user(telegram_id)
        if sesi_user:
            session_id = sesi_user[0]['id'] # Ambil akun pertama
            # Simpan ke DB!
            update_session(session_id, {"delay_promosi": delay})
            
            await message.answer(f"✅ Jeda berhasil diatur ke <b>{delay} menit</b>.", parse_mode="HTML")
        else:
            await message.answer("❌ Anda belum login akun Jaseb.")
            
        await state.clear()
    except ValueError:
        await message.answer("❌ Harus berupa angka. Coba masukkan lagi.")

# ==========================================
# 2. TAMBAH GRUP (Dari klik tombol Inline)
# ==========================================
@router.callback_query(F.data == "menu_grup")
async def btn_atur_grup(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.adding_group)
    await callback.message.answer("👥 Masukkan Username / ID Grup (contoh: @grupjualbeli atau -100123456):")
    await callback.answer()

@router.message(SettingsForm.adding_group)
async def process_group(message: types.Message, state: FSMContext):
    group_input = message.text
    telegram_id = message.from_user.id
    
    # [Logika DB] Simpan grup ke database
    sesi_user = get_sessions_by_user(telegram_id)
    if sesi_user:
        session_id = sesi_user[0]['id']
        
        # Biar aman, group_id diset 0 dulu (nanti Pyrogram yang ngeresolve username jadi ID)
        add_target_group(session_id, group_id=0, group_name=group_input)
        
        await message.answer(f"✅ Grup {group_input} berhasil dimasukkan ke daftar target!")
    else:
        await message.answer("❌ Anda belum login akun Jaseb.")
        
    await state.clear()

# ==========================================
# 3. ATUR PESAN (Support Forward & Media)
# ==========================================
@router.callback_query(F.data == "menu_pesan")
async def btn_atur_pesan(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.setting_message)
    await callback.message.answer("💬 Kirimkan pesan promosi Anda ke sini.\n\n<i>Bisa berupa teks biasa, foto dengan caption, atau <b>Forward pesan</b> dari channel Anda.</i>", parse_mode="HTML")
    await callback.answer()

@router.message(SettingsForm.setting_message)
async def process_message(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    
    # KUNCI ADVANCE: Kita gak simpan teksnya, tapi simpan ID pesannya!
    # Nanti Pyrogram tinggal meng-copy atau nge-forward pesan dari ID ini.
    pesan_id = message.message_id
    chat_id = message.chat.id
    format_penyimpanan = f"{chat_id}:{pesan_id}"
    
    sesi_user = get_sessions_by_user(telegram_id)
    if sesi_user:
        session_id = sesi_user[0]['id']
        # Simpan ke kolom pesan_promosi di tabel sessions
        update_session(session_id, {"pesan_promosi": format_penyimpanan})
        
        await message.answer("✅ Pesan promosi berhasil disimpan! Preview pesan:")
        # Kasih preview ke user biar yakin
        await message.copy_to(chat_id=message.chat.id)
    else:
        await message.answer("❌ Anda belum login akun Jaseb.")
        
    await state.clear()