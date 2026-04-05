# =============================================================================
# config.py — All your settings. Edit this before running anything.
# No Kite API needed. No static IP needed. Just Python + internet.
# =============================================================================

# --- Telegram Bot ---
# Full setup guide is in README.md — takes about 2 minutes.
TELEGRAM_BOT_TOKEN = "8699283942:AAHSq_Po_gLBY_OqbsWI6eNe5LEWjh3n4k8"   # from @BotFather on Telegram
TELEGRAM_CHAT_ID   = "8064531676"     # your personal chat ID

# --- Capital & Risk ---
# Used only for the position size suggestion in the notification message.
CAPITAL          = 3000   # Your actual capital in rupees
LEVERAGE         = 5      # MIS intraday leverage on Zerodha
RISK_PER_TRADE   = 0.02   # Risk 2% of effective capital per trade

# --- How many signals to send per day ---
MAX_SIGNALS_PER_DAY = 2

# --- Strategy Parameters ---
STOP_LOSS_PCT      = 0.005   # 0.5% stop loss from entry price
TARGET_RR          = 2.0     # Risk:Reward — target = SL distance × this
VOLUME_MULTIPLIER  = 1.5     # Breakout candle volume must be > 1.5x 20-day average
PULLBACK_PCT       = 0.002   # Wait for 0.2% pullback after breakout before signalling
EMA_PERIOD         = 20      # EMA used for trend filter on bull breaks

# --- Timing ---
SCAN_INTERVAL_SECONDS = 60
TRADE_START_TIME      = "09:30"
SIGNAL_CUTOFF_TIME    = "14:30"  # Stop sending signals after this
MARKET_CLOSE_TIME     = "15:30"

# --- Nifty 50 symbols (NSE codes) ---
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

# --- Logging ---
LOG_FILE = "scanner.log"