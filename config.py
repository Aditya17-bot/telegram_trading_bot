# =============================================================================
# config.py
# Reads credentials from Streamlit Cloud Secrets. No dotenv. No .env file.
#
# To set secrets on Streamlit Cloud:
#   Your app → ⋮ menu → Settings → Secrets → paste:
#
#   TELEGRAM_BOT_TOKEN = "your_token_here"
#   TELEGRAM_CHAT_ID = "your_chat_id_here"
# =============================================================================
import os
import streamlit as st

def _secret(key: str) -> str:
    """
    Read a secret safely.
    Priority: st.secrets → environment variable → empty string.
    Never crashes even if the key is missing.
    """
    try:
        val = st.secrets.get(key, "")
        if val:
            return str(val).strip()
    except Exception:
        pass
    return os.environ.get(key, "").strip()

# --- Telegram credentials (set these in Streamlit Cloud Secrets) ---
TELEGRAM_BOT_TOKEN = _secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = _secret("TELEGRAM_CHAT_ID")

# --- Capital & Risk ---
CAPITAL             = 5000
LEVERAGE            = 5
RISK_PER_TRADE      = 0.02
MAX_SIGNALS_PER_DAY = 2

# --- Strategy Parameters ---
STOP_LOSS_PCT      = 0.005
TARGET_RR          = 2.0
VOLUME_MULTIPLIER  = 1.5
PULLBACK_PCT       = 0.002
EMA_PERIOD         = 20

# --- Timing (IST) ---
SCAN_INTERVAL_SECONDS = 60
TRADE_START_TIME      = "09:30"
SIGNAL_CUTOFF_TIME    = "14:30"
MARKET_CLOSE_TIME     = "15:30"

# --- Nifty 50 symbols ---
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BAJFINANCE", "BHARTIARTL", "KOTAKBANK",
    "LT", "WIPRO", "HCLTECH", "ASIANPAINT", "MARUTI",
    "AXISBANK", "NTPC", "POWERGRID", "TITAN", "ULTRACEMCO",
    "SUNPHARMA", "TECHM", "ONGC", "JSWSTEEL", "TATAMOTORS",
    "TATASTEEL", "ADANIENT", "COALINDIA", "BAJAJFINSV", "DIVISLAB",
    "DRREDDY", "EICHERMOT", "NESTLEIND", "CIPLA", "HINDALCO",
    "INDUSINDBK", "GRASIM", "TATACONSUM", "BPCL", "HEROMOTOCO",
    "BRITANNIA", "APOLLOHOSP", "SHREECEM", "M&M", "SBILIFE",
    "HDFCLIFE", "BAJAJ-AUTO", "UPL", "ADANIPORTS", "ITC",
]

LOG_FILE = "scanner.log"