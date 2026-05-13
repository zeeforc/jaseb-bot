# bot/handlers/admin.py
import random
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.config import ADMIN_ID
from database.crud import create_token, get_all_users
from bot.states.form import AdminForm

router = Router()

def generate_random_string(length=8):
    """Generate random string tanpa karakter ambigu (O, 0, I, l, 1)"""
    characters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(random.choice(characters) for _ in range(length))

# ==========================================
# FITUR: GENERATE TOKEN PAKET
# ==========================================
@router.message(Command("gen_token"))
async def cmd_gen_token(message: types.Message):
    # 1. Cek apakah yang ngetik ini Admin atau bukan
    if message.from_user.id != ADMIN_ID:
        # Kacangin aja kalau bukan admin
        return

    # 2. Parsing Perintah (Format: /gen_token [paket] [durasi_hari])
    args = message.text.split()
    if len(args) != 3:
        teks_bantuan = (
            "❌ <b>Format Salah!</b>\n\n"
            "Gunakan: <code>/gen_token [paket] [durasi_hari]</code>\n\n"
            "<b>Daftar Kode Paket:</b>\n"
            "• <code>hemat</code> (Basic Hemat)\n"
            "• <code>sultan</code> (Basic Sultan)\n"
            "• <code>sp_hemat</code> (Spesial Hemat)\n"
            "• <code>sp_sultan</code> (Spesial Sultan)\n\n"
            "<b>Contoh:</b> <code>/gen_token sultan 30</code>"
        )
        await message.answer(teks_bantuan, parse_mode="HTML")
        return
    
    paket_input = args[1].lower()
    
    try:
        durasi = int(args[2])
    except ValueError:
        await message.answer("❌ Durasi hari harus berupa angka!")
        return

    # 3. Tentukan Prefix & Nama Paket DB
    prefix = "JSB"
    if paket_input == "hemat":
        kode_paket = "HMT"
        tipe_paket = "basic_hemat"
    elif paket_input == "sultan":
        kode_paket = "SLT"
        tipe_paket = "basic_sultan"
    elif paket_input == "sp_hemat":
        kode_paket = "SPH"
        tipe_paket = "spesial_hemat"
    elif paket_input == "sp_sultan":
        kode_paket = "SPS"
        tipe_paket = "spesial_sultan"
    else:
        await message.answer("❌ Paket tidak dikenal! Cek format /gen_token.")
        return
    
    # 4. Generate Token & Gabungkan Formatnya
    random_str = generate_random_string(8)
    token_final = f"{prefix}-{kode_paket}-{random_str}"

    # 5. Simpan ke Database
    sukses = create_token(token_final, tipe_paket, durasi)
    
    if sukses:
        teks_sukses = (
            "✅ <b>TOKEN BERHASIL DIBUAT!</b>\n\n"
            f"🎟️ <b>Token:</b> <code>{token_final}</code>\n"
            f"📦 <b>Paket:</b> {tipe_paket}\n"
            f"⏳ <b>Durasi:</b> {durasi} Hari\n\n"
            "<i>Klik token di atas untuk meng-copy, lalu berikan ke pembeli.</i>"
        )
        await message.answer(teks_sukses, parse_mode="HTML")
    else:
        await message.answer("❌ Gagal menyimpan token ke Database. Cek log terminal!")


# ==========================================
# FITUR 3A: BROADCAST PENGUMUMAN KE USER
# ==========================================

@router.message(Command("bc"), F.from_user.id == ADMIN_ID)
async def cmd_broadcast(message: types.Message, state: FSMContext):
    """Trigger awal untuk memulai mode broadcast"""
    teks = (
        "📢 <b>Mode Broadcast Admin</b> 📢\n\n"
        "Silakan kirim pesan yang ingin di-blast ke seluruh pelanggan JasebBot.\n"
        "<i>(Support pengiriman Teks, Foto, Video, atau Document)</i>\n\n"
        "👉 Ketik /batal untuk membatalkan."
    )
    await message.answer(teks, parse_mode="HTML")
    await state.set_state(AdminForm.broadcast_message)

@router.message(Command("batal"), F.from_user.id == ADMIN_ID)
async def cmd_batal_bc(message: types.Message, state: FSMContext):
    """Membatalkan mode broadcast"""
    await state.clear()
    await message.answer("❌ Broadcast dibatalkan.")

@router.message(AdminForm.broadcast_message, F.from_user.id == ADMIN_ID)
async def proses_broadcast(message: types.Message, state: FSMContext):
    """Mesin pengeksekusi pengiriman pesan massal ke user"""
    await state.clear() # Langsung matikan state biar aman
    
    # 1. Tarik semua data user dari Supabase
    users = get_all_users()
    if not users:
        await message.answer("❌ Database user masih kosong!")
        return
        
    await message.answer(f"⏳ <b>Memulai broadcast ke {len(users)} pengguna...</b>\nMohon tunggu, jangan spam command lain.", parse_mode="HTML")
    
    berhasil = 0
    gagal = 0
    
    # 2. Looping kirim pesan ke masing-masing user
    for user in users:
        user_id = user.get("telegram_id")
        if not user_id:
            continue
            
        try:
            # Pake fungsi copy_to biar bot bisa nerusin format persis kayak yang lu kirim (termasuk media)
            await message.copy_to(chat_id=user_id)
            berhasil += 1
            
            # 🔥 WAJIB ADA JEDA BIAR BOT LU GAK KENA LIMIT FLOOD TELEGRAM
            await asyncio.sleep(0.05) 
        except Exception:
            gagal += 1 # Biasanya gagal kalau user udah nge-block bot lu
            
    # 3. Laporan akhir ke lu
    laporan = (
        "✅ <b>BROADCAST SELESAI!</b>\n\n"
        f"🎯 Total Target: <b>{len(users)}</b>\n"
        f"🟢 Berhasil: <b>{berhasil}</b>\n"
        f"🔴 Gagal: <b>{gagal}</b> <i>(User blokir bot/ID salah)</i>"
    )
    await message.answer(laporan, parse_mode="HTML")