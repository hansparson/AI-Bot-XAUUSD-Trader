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

# PRO Strategy Settings
PRO_MODE = os.getenv("PRO_MODE", "TRUE").upper() == "TRUE"
ATR_PERIOD = int(os.getenv("ATR_PERIOD", 14))
ATR_SL_MULT = float(os.getenv("ATR_SL_MULT", 1.5))
ATR_TP_MULT = float(os.getenv("ATR_TP_MULT", 2.5))
ATR_BE_MULT = float(os.getenv("ATR_BE_MULT", 1.0))
ATR_TRAIL_MULT = float(os.getenv("ATR_TRAIL_MULT", 1.5))

# Session & News Filter
USE_SESSION_FILTER_PRO = os.getenv("USE_SESSION_FILTER_PRO", "TRUE").upper() == "TRUE"
USE_NEWS_FILTER_PRO = os.getenv("USE_NEWS_FILTER_PRO", "TRUE").upper() == "TRUE"
DYNAMIC_AI_THRESHOLD = os.getenv("DYNAMIC_AI_THRESHOLD", "TRUE").upper() == "TRUE"

# Institutional / Risk Manager Settings
MAX_SPREAD_POINTS = int(os.getenv("MAX_SPREAD_POINTS", 300))
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", 5))
ENSEMBLE_AI = os.getenv("ENSEMBLE_AI", "TRUE").upper() == "TRUE"
WEIGHT_TECH = float(os.getenv("WEIGHT_TECH", 0.5))
WEIGHT_OLLAMA = float(os.getenv("WEIGHT_OLLAMA", 0.25))
WEIGHT_GEMINI = float(os.getenv("WEIGHT_GEMINI", 0.25))
EQUITY_DD_THRESHOLD = float(os.getenv("EQUITY_DD_THRESHOLD", 12.0))
# Cooldown between trades (seconds)
TRADE_COOLDOWN = int(os.getenv("TRADE_COOLDOWN", 1800)) 

# Database
DB_FILE = os.getenv("DB_FILE", "data/trading_data.db")

# Risk Management
MAX_DAILY_LOSS_USD = float(os.getenv("MAX_DAILY_LOSS_USD", -50.0)) # Stop if daily loss hits -$50
TRAILING_STOP_PIPS = int(os.getenv("TRAILING_STOP_PIPS", 250)) # Follow profit by 250 pips
BREAK_EVEN_PIPS = int(os.getenv("BREAK_EVEN_PIPS", 300)) # Move to BE after 300 pips profit

# AI Model & Mode
AI_MODE = os.getenv("AI_MODE", "CLOUD").upper() # LOCAL atau CLOUD
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CLOUD_MODEL = os.getenv("CLOUD_MODEL", "gemini-1.5-flash")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5:7b")
AI_URL = os.getenv("AI_URL", "http://127.0.0.1:11434/api/generate")
