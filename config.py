import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

_gpt4_mini_raw = os.getenv("GPT4_MINI_API_KEYS", "pollinations_key_alpha_11a,pollinations_key_beta_11a,pollinations_key_gamma_11a,pollinations_key_delta_11a,pollinations_key_omega_11a,pollinations_key_sigma_11a")
GPT4_MINI_API_KEYS = [k.strip() for k in _gpt4_mini_raw.split(",") if k.strip()]

# Admin ID larini list<int> ko'rinishida olish
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
for aid in _admin_ids_raw.split(","):
    aid = aid.strip()
    if aid.isdigit() or (aid.startswith("-") and aid[1:].isdigit()):
        ADMIN_IDS.append(int(aid))

# Sinfdoshlar guruhining ID si
_group_id_raw = os.getenv("GROUP_CHAT_ID", "")
GROUP_CHAT_ID = int(_group_id_raw) if (_group_id_raw.lstrip("-").isdigit()) else 0

# Guruhda jimjitlik bo'lsa xabar yuborish intervali (soatlarda)
INACTIVITY_TIMEOUT_HOURS = float(os.getenv("INACTIVITY_TIMEOUT_HOURS", "4"))

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")
