from aiogram import Router, types, F
from aiogram.filters import CommandStart
from bot.keyboards.inline import (
    kb_welcome, kb_toko_utama, kb_syarat_ketentuan, 
    kb_pilih_tipe, kb_varian_basic
)

router = Router()

# Link foto banner lu (bisa dapet dari id foto di telegram)
BANNER_URL = "https://link-ke-foto-anime-boy-lu.jpg" 

@router.message(CommandStart())
async def start_cmd(message: types.Message):
    teks = (
        "── **Selamat Datang di Userbot Jiro** ──\n\n"
        "Halo, Z'fsto!\n"
        "Anda selangkah lebih dekat menuju Era Baru Promosi!\n\n"
        "Lupakan cara lama yang membuang waktu & tenaga. Bersama saya, promosi ke puluhan/ratusan grup ada dalam genggaman Anda..."
    )
    # Kirim pesan pakai foto (seperti Gambar 1)
    await message.answer_photo(
        photo=BANNER_URL, 
        caption=teks, 
        reply_markup=kb_welcome()
    )

@router.callback_query(F.data == "kembali_awal")
async def back_to_start(callback: types.CallbackQuery):
    # (Opsional) Hapus foto dan kembalikan ke teks awal jika ingin clean
    await callback.message.delete()
    await start_cmd(callback.message)

@router.callback_query(F.data == "menu_toko")
async def nav_toko(callback: types.CallbackQuery):
    teks = "🛍️ **MENU STORE & LAYANAN**\n\nSilakan pilih kategori produk yang ingin Anda akses di bawah ini:"
    await callback.message.edit_text(text=teks, reply_markup=kb_toko_utama())

@router.callback_query(F.data == "toko_beli_userbot")
async def nav_ketentuan(callback: types.CallbackQuery):
    teks = (
        "📜 **Kebijakan & Ketentuan Kami**\n\n"
        "🔸 Membeli berarti Anda menyetujui segala risiko!\n"
        "🔸 Garansi hanya berlaku untuk tipe tertentu.\n\n"
        "Jika Anda SETUJU, Tekan Tombol Di Bawah Ini."
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_syarat_ketentuan())

@router.callback_query(F.data == "toko_pilih_tipe")
async def nav_pilih_tipe(callback: types.CallbackQuery):
    teks = "📦 **PILIH TIPE LAYANAN**\n\nSilakan pilih paket yang sesuai dengan kebutuhan Anda di bawah ini:"
    await callback.message.edit_text(text=teks, reply_markup=kb_pilih_tipe())

@router.callback_query(F.data == "varian_basic")
async def nav_varian_basic(callback: types.CallbackQuery):
    teks = (
        "⭐ **PILIH TIPE LAYANAN BASIC**\n\n"
        "⚡ **Basic Hemat (Non-Garansi)**\n"
        "Rp 6.000 /bulan\n"
        "• Harga ekonomis\n• Tanpa Backup\n\n"
        "⚡ **Basic Sultan (Bergaransi)**\n"
        "Rp 10.000 /bulan\n"
        "• Fitur Full\n• Garansi login kembali"
    )
    await callback.message.edit_text(text=teks, reply_markup=kb_varian_basic())

@router.callback_query(F.data.startswith("checkout_"))
async def process_checkout(callback: types.CallbackQuery):
    paket = callback.data.split("_")[2] # ngambil kata 'hemat' atau 'sultan'
    teks = (
        f"✅ Anda memilih paket **Basic {paket.capitalize()}**.\n\n"
        "Langkah selanjutnya:\n"
        "1. Lakukan pembayaran manual via QRIS/DANA.\n"
        "2. Kirimkan bukti transfer ke Admin: @UsernameAdmin\n"
        "3. Admin akan memberikan **TOKEN AKTIVASI** kepada Anda.\n\n"
        "Jika sudah mendapat token, silakan klik tombol **Klaim Token** di menu utama."
    )
    await callback.message.edit_text(text=teks)