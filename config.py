# =============================================================================
# config.py — Settings. On Streamlit Cloud, secrets override these values.
# Telegram credentials are loaded from st.secrets (never hardcode them here).
# =============================================================================
import os

from dotenv import load_dotenv

load_dotenv()

# --- Try loading from Streamlit secrets first, fall back to env vars ---
def _get(key, default=""):
    try:
        import streamlit as st
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)

TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = _get("TELEGRAM_CHAT_ID")

# --- Capital & Risk ---
CAPITAL          = 5000
LEVERAGE         = 5
RISK_PER_TRADE   = 0.02
MAX_SIGNALS_PER_DAY = 2

# --- Strategy Parameters ---
STOP_LOSS_PCT      = 0.005
TARGET_RR          = 2.0
VOLUME_MULTIPLIER  = 1.5
PULLBACK_PCT       = 0.002
EMA_PERIOD         = 20

# --- Timing ---
SCAN_INTERVAL_SECONDS = 60
TRADE_START_TIME      = "09:30"
SIGNAL_CUTOFF_TIME    = "14:30"
MARKET_CLOSE_TIME     = "15:30"

# --- Nifty 50 ---
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
