import os

def load_env(file_path=".env"):
    """Simple manual .env loader as python-dotenv might not be installed"""
    if not os.path.exists(file_path):
        return
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

# Load environment variables
load_env()

# Mode: DEMO atau LIVE
ACCOUNT_MODE = os.getenv("ACCOUNT_MODE", "DEMO").upper()

if ACCOUNT_MODE == "LIVE":
    MT5_LOGIN = int(os.getenv("MT5_LIVE_LOGIN", 0))
    MT5_PASSWORD = os.getenv("MT5_LIVE_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_LIVE_SERVER", "")
else:
    MT5_LOGIN = int(os.getenv("MT5_DEMO_LOGIN", 0))
    MT5_PASSWORD = os.getenv("MT5_DEMO_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_DEMO_SERVER", "")

# Trading Settings
SYMBOL = os.getenv("SYMBOL", "XAUUSD.m")
MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", 123456))
DEFAULT_LOT = float(os.getenv("DEFAULT_LOT", 0.01))

# Engine Logic
RATING_THRESHOLD = float(os.getenv("RATING_THRESHOLD", 0.70))
STOP_LOSS_PIPS = int(os.getenv("STOP_LOSS_PIPS", 800))
TAKE_PROFIT_PIPS = int(os.getenv("TAKE_PROFIT_PIPS", 800))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", 60))
MAX_TRADES = int(os.getenv("MAX_TRADES", 1))
MIN_MARGIN_LEVEL = float(os.getenv("MIN_MARGIN_LEVEL", 300.0))
HARD_TP_USD = float(os.getenv("HARD_TP_USD", 15.0))
EMERGENCY_SL_USD = float(os.getenv("EMERGENCY_SL_USD", -8.0))
MAX_CONSEC_LOSSES = int(os.getenv("MAX_CONSEC_LOSSES", 4))

# Database
DB_FILE = os.getenv("DB_FILE", "data/trading_data.db")

# Risk Management
MAX_DAILY_LOSS_USD = float(os.getenv("MAX_DAILY_LOSS_USD", -50.0)) # Stop if daily loss hits -$50
TRAILING_STOP_PIPS = int(os.getenv("TRAILING_STOP_PIPS", 250)) # Follow profit by 250 pips
BREAK_EVEN_PIPS = int(os.getenv("BREAK_EVEN_PIPS", 300)) # Move to BE after 300 pips profit

# AI Model & Mode
AI_MODE = os.getenv("AI_MODE", "LOCAL").upper() # LOCAL atau CLOUD
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "qwen2.5:7b")
AI_URL = os.getenv("AI_URL", "http://127.0.0.1:11434/api/generate")
