# =============================================================================
# scanner.py — The main script. Run this every morning, leave it running.
#
# What it does:
#   9:00 AM  → Sends morning summary to Telegram
#   9:30 AM  → Starts scanning all 50 stocks every 60 seconds
#   Signal!  → Sends Telegram notification instantly
#   2:30 PM  → Stops sending new signals
#   3:15 PM  → Sends EOD recap
#   3:30 PM  → Script exits
#
# How to run:
#   python scanner.py
# =============================================================================

import time
import logging
from datetime import datetime, time as dtime

import yfinance as yf
import pandas as pd

from config import (
    NIFTY50_SYMBOLS, SCAN_INTERVAL_SECONDS,
    TRADE_START_TIME, SIGNAL_CUTOFF_TIME, MARKET_CLOSE_TIME,
    MAX_SIGNALS_PER_DAY, EMA_PERIOD, VOLUME_MULTIPLIER, LOG_FILE
)
from data import fetch_previous_day_levels, save_levels, load_levels
from strategy import SignalEngine
from notify import (
    send_signal, send_morning_summary, send_eod_recap,
    send_fake_breakout_alert, send_heartbeat, test_notification
)

# =============================================================================
# Logging
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# =============================================================================
# Time helpers
# =============================================================================
def t(s: str) -> dtime:
    h, m = map(int, s.split(":"))
    return dtime(h, m)

def now_t() -> dtime:
    return datetime.now().time().replace(second=0, microsecond=0)

def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


# =============================================================================
# Live price fetching via yfinance (free, no Kite API needed)
# =============================================================================
def get_live_quotes(symbols: list, levels: dict) -> dict:
    """
    Fetches live price + today's volume for all symbols using yfinance.
    yfinance gives 1-minute delayed data for NSE — good enough for our strategy
    since we're looking for pullbacks, not millisecond entries.

    Also estimates the last-candle volume by comparing to the previous scan.
    """
    yf_syms = []
    for s in symbols:
        if s == "M&M":
            yf_syms.append("M%26M.NS")
        else:
            yf_syms.append(f"{s}.NS")

    try:
        # Download 2-day 5-minute data: gives us today's intraday candles
        raw = yf.download(
            tickers=yf_syms,
            period="2d",
            interval="5m",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        log.warning(f"Live quote fetch failed: {e}")
        return {}

    quotes = {}
    for i, symbol in enumerate(symbols):
        yf_sym = yf_syms[i]
        try:
            df = raw[yf_sym] if len(symbols) > 1 else raw
            df = df.dropna()
            # Keep only today's candles
            today = datetime.now().date()
            df = df[df.index.date == today]

            if df.empty:
                continue

            last_candle = df.iloc[-1]
            ltp = float(last_candle["Close"])
            total_volume = int(df["Volume"].sum())
            last_candle_volume = int(last_candle["Volume"])

            quotes[symbol] = {
                "ltp": ltp,
                "volume": total_volume,
                "last_candle_volume": last_candle_volume,
            }
        except Exception as e:
            log.debug(f"Quote parse failed for {symbol}: {e}")
            continue

    return quotes


# =============================================================================
# Main scanner loop
# =============================================================================
def run():
    log.info("=" * 60)
    log.info(f"PDH/PDL SIGNAL SCANNER — {datetime.now().strftime('%Y-%m-%d')}")
    log.info("=" * 60)

    # --- Step 1: Test Telegram first ---
    log.info("Testing Telegram connection...")
    if not test_notification():
        log.error(
            "Telegram test FAILED. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.py"
        )
        print("\n❌ Telegram not working. Fix config.py and try again.\n")
        return
    log.info("Telegram OK ✓")

    # --- Step 2: Fetch PDH/PDL levels ---
    try:
        levels = load_levels()
        log.info(f"Loaded cached levels for {len(levels)} stocks from levels.json")
    except FileNotFoundError:
        log.info("No cached levels — fetching now...")
        levels = fetch_previous_day_levels(NIFTY50_SYMBOLS)
        if not levels:
            log.error("Could not fetch levels. Check internet connection.")
            return
        save_levels(levels)

    active_symbols = [s for s in NIFTY50_SYMBOLS if s in levels]
    log.info(f"Watching {len(active_symbols)} stocks.")

    # --- Step 3: Send morning summary ---
    send_morning_summary(levels)

    # --- Step 4: Initialize signal engine ---
    engine = SignalEngine({s: levels[s] for s in active_symbols})

    # --- State ---
    signals_sent = []
    last_heartbeat_hour = -1
    eod_sent = False

    log.info(f"Waiting for trading window ({TRADE_START_TIME})...")

    # ==========================================================================
    # MAIN LOOP
    # ==========================================================================
    while True:
        current = now_t()

        # ---- Exit after market close ----
        if current >= t(MARKET_CLOSE_TIME):
            if not eod_sent:
                send_eod_recap(signals_sent)
                eod_sent = True
            log.info("Market closed. Scanner exiting. See you tomorrow!")
            break

        # ---- EOD recap at 3:15 PM ----
        if current >= t("15:15") and not eod_sent:
            send_eod_recap(signals_sent)
            eod_sent = True

        # ---- Outside trading window — just wait ----
        if current < t(TRADE_START_TIME):
            log.debug(f"[{now_str()}] Waiting for {TRADE_START_TIME}...")
            time.sleep(30)
            continue

        # ---- Past signal cutoff — no new signals ----
        past_cutoff = current >= t(SIGNAL_CUTOFF_TIME)
        if past_cutoff:
            log.debug(f"[{now_str()}] Past signal cutoff. Waiting for EOD.")
            time.sleep(60)
            continue

        # ---- Max signals reached for the day ----
        if len(signals_sent) >= MAX_SIGNALS_PER_DAY:
            log.debug(f"[{now_str()}] Max signals ({MAX_SIGNALS_PER_DAY}) reached for today.")
            time.sleep(60)
            continue

        # ---- Hourly heartbeat so you know script is alive ----
        current_hour = datetime.now().hour
        if current_hour != last_heartbeat_hour and current_hour >= 10:
            send_heartbeat()
            last_heartbeat_hour = current_hour

        # ---- SCAN ----
        try:
            quotes = get_live_quotes(active_symbols, levels)

            if not quotes:
                log.warning(f"[{now_str()}] No quotes received this scan.")
                time.sleep(SCAN_INTERVAL_SECONDS)
                continue

            new_signals = engine.scan(quotes)

            for signal in new_signals:
                if len(signals_sent) >= MAX_SIGNALS_PER_DAY:
                    break

                ok = send_signal(signal)
                if ok:
                    signals_sent.append(signal)
                    log.info(
                        f"SIGNAL SENT → {signal.direction} {signal.symbol} | "
                        f"Entry: {signal.entry_price} | SL: {signal.stop_loss} | "
                        f"Target: {signal.target}"
                    )
                else:
                    log.error(f"Failed to send signal for {signal.symbol}")

            log.info(
                f"[{now_str()}] Scan done | "
                f"Quotes: {len(quotes)} | "
                f"Signals today: {len(signals_sent)}/{MAX_SIGNALS_PER_DAY}"
            )

        except Exception as e:
            log.error(f"Scan error: {e}", exc_info=True)

        time.sleep(SCAN_INTERVAL_SECONDS)


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    print()
    print("=" * 55)
    print("  PDH/PDL SIGNAL SCANNER + TELEGRAM NOTIFIER")
    print("=" * 55)
    print()
    print("Make sure you have done these steps in config.py:")
    print("  1. Set TELEGRAM_BOT_TOKEN")
    print("  2. Set TELEGRAM_CHAT_ID")
    print("  3. Set CAPITAL to your actual capital")
    print()
    run()