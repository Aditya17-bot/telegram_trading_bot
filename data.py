# =============================================================================
# data.py — Fetches previous day High/Low and volume averages for all 50 stocks
# Uses yfinance (free) so you don't need the paid ₹500/month Kite data plan.
# Run this once at ~9:00 AM before markets open.
# =============================================================================

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
import json
import os
from config import NIFTY50_SYMBOLS, EMA_PERIOD, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# yfinance uses ".NS" suffix for NSE stocks
def to_yf_symbol(symbol: str) -> str:
    # M&M needs special handling
    if symbol == "M&M":
        return "M%26M.NS"
    return f"{symbol}.NS"

def fetch_previous_day_levels(symbols: list) -> dict:
    """
    Fetches for each stock:
    - PDH: Previous Day High
    - PDL: Previous Day Low  
    - PDC: Previous Day Close
    - avg_volume: 20-day average volume (for the volume filter)
    - ema20: Current 20-period EMA on daily timeframe

    Returns a dict keyed by symbol.
    """
    log.info(f"Fetching data for {len(symbols)} stocks...")
    levels = {}

    # Fetch in bulk using yfinance download for speed
    yf_symbols = [to_yf_symbol(s) for s in symbols]

    try:
        # Download 30 days of daily OHLCV data — enough for EMA + volume avg
        raw = yf.download(
            tickers=yf_symbols,
            period="30d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        log.error(f"yfinance bulk download failed: {e}")
        return {}

    for symbol in symbols:
        yf_sym = to_yf_symbol(symbol)
        try:
            # Handle single vs multi ticker response format
            if len(symbols) == 1:
                df = raw
            else:
                df = raw[yf_sym]

            df = df.dropna()

            if len(df) < 2:
                log.warning(f"{symbol}: Not enough data (got {len(df)} rows)")
                continue

            # Previous day = second-to-last row (last row = today pre-market or latest)
            # If market hasn't opened yet today, last row IS previous day
            prev = df.iloc[-1]
            if datetime.now().hour < 9:
                prev = df.iloc[-1]
            else:
                prev = df.iloc[-2]

            pdh = float(prev["High"])
            pdl = float(prev["Low"])
            pdc = float(prev["Close"])

            # 20-day average volume
            avg_vol = float(df["Volume"].tail(20).mean())

            # 20-period EMA on close prices
            closes = df["Close"].tail(EMA_PERIOD + 5)
            ema20 = float(closes.ewm(span=EMA_PERIOD, adjust=False).mean().iloc[-1])

            levels[symbol] = {
                "pdh": round(pdh, 2),
                "pdl": round(pdl, 2),
                "pdc": round(pdc, 2),
                "avg_volume": round(avg_vol),
                "ema20": round(ema20, 2),
                "fetched_at": datetime.now().isoformat(),
            }

            log.info(
                f"{symbol:15s} PDH={pdh:.2f}  PDL={pdl:.2f}  "
                f"AvgVol={avg_vol:,.0f}  EMA20={ema20:.2f}"
            )

        except Exception as e:
            log.warning(f"{symbol}: Failed to parse data — {e}")
            continue

    log.info(f"Successfully fetched levels for {len(levels)}/{len(symbols)} stocks.")
    return levels


def save_levels(levels: dict, path: str = "levels.json"):
    """Save fetched levels to disk so trader.py can read them."""
    with open(path, "w") as f:
        json.dump(levels, f, indent=2)
    log.info(f"Levels saved to {path}")


def load_levels(path: str = "levels.json") -> dict:
    """Load levels from disk."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Run data.py first.")
    with open(path) as f:
        return json.load(f)


def fetch_intraday_data(symbol: str, interval: str = "5m") -> pd.DataFrame:
    """
    Fetch today's intraday OHLCV data for a symbol.
    Used by strategy.py to calculate live volume vs avg volume.
    interval: "1m", "5m", "15m"
    """
    try:
        df = yf.download(
            tickers=to_yf_symbol(symbol),
            period="1d",
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        return df.dropna()
    except Exception as e:
        log.warning(f"Intraday fetch failed for {symbol}: {e}")
        return pd.DataFrame()


# =============================================================================
# Run this file directly each morning: python data.py
# =============================================================================
if __name__ == "__main__":
    from config import NIFTY50_SYMBOLS
    log.info("=" * 60)
    log.info("PDH/PDL DATA FETCH — " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)

    levels = fetch_previous_day_levels(NIFTY50_SYMBOLS)

    if not levels:
        log.error("No data fetched. Check your internet connection.")
    else:
        save_levels(levels)
        log.info(f"\nDone. {len(levels)} stocks ready for trading today.")
        log.info("Now run: python trader.py")