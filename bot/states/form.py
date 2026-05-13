"""
form.py - FSM (Finite State Machine) untuk input user
"""
from aiogram.fsm.state import State, StatesGroup

class LoginForm(StatesGroup):
    """Login FSM States"""
    asking_phone = State()
    asking_otp = State()

class ClaimTokenState(StatesGroup):
    """Klaim Token FSM State"""
    waiting_for_token = State()

# === STATE BAWAAN LU YANG LAMA (BIAR GA ERROR) ===
class SettingsForm(StatesGroup):
    """Settings FSM States"""
    setting_delay = State()
    adding_group = State()
    setting_message = State()

# === TAMBAHAN BARU: FSM UNTUK PANEL KONTROL ===
class PanelForm(StatesGroup):
    """FSM untuk menyimpan input settingan bot"""
    # Atur Pesan
    setting_pesan_teks = State()
    setting_pesan_forward = State()
    
    # Atur Grup
    adding_group_manual = State()
    deleting_group = State()
    
    # Atur Jeda
    setting_jeda_grup = State()
    setting_jeda_putaran = State()
    
    # Fitur Premium
    setting_watermark = State()
    
    # Notif
    setting_notif_user = State()
    
    # Base Reply
    adding_base_reply = State()

    # Proxy
    setting_proxy = State()

class AdminForm(StatesGroup):
    broadcast_message = State()