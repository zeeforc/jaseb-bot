"""
connection.py - Setup koneksi Supabase/DB
"""
from supabase import create_client, Client
from core.config import SUPABASE_URL, SUPABASE_KEY
from core.logger import logger

# Inisialisasi Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✓ Koneksi Supabase berhasil")
except Exception as e:
    logger.error(f"✗ Gagal koneksi Supabase: {e}")
    supabase = None

def get_connection():
    """Return Supabase connection"""
    return supabase
