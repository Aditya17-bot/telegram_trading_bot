# =============================================================================
# app.py — Streamlit dashboard for PDH/PDL Signal Scanner
#
# Open on phone at: https://your-app-name.streamlit.app
# Tap "Start Scanner" → live updates every 60 seconds automatically
# =============================================================================

import time
import json
import traceback
from datetime import datetime, time as dtime

import streamlit as st
import pandas as pd

from config import (
    NIFTY50_SYMBOLS, SCAN_INTERVAL_SECONDS, CAPITAL, LEVERAGE,
    RISK_PER_TRADE, MAX_SIGNALS_PER_DAY, STOP_LOSS_PCT, TARGET_RR,
    VOLUME_MULTIPLIER, PULLBACK_PCT, EMA_PERIOD,
    TRADE_START_TIME, SIGNAL_CUTOFF_TIME, MARKET_CLOSE_TIME,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
)
from data import fetch_previous_day_levels
from strategy import SignalEngine
from notify import send_signal, send_morning_summary, send_eod_recap, test_notification

# =============================================================================
# Page config — mobile-friendly
# =============================================================================
st.set_page_config(
    page_title="PDH/PDL Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Compact mobile CSS
st.markdown("""
<style>
    .block-container { padding: 0.75rem 1rem 2rem; max-width: 900px; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.1rem !important; }
    h3 { font-size: 1rem !important; }
    .stMetric label { font-size: 0.75rem !important; }
    .stMetric [data-testid="metric-container"] { padding: 0.4rem 0.6rem; }
    div[data-testid="stStatusWidget"] { display: none; }
    .signal-card {
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
        border-left: 4px solid;
    }
    .buy-card  { background: #e8f5e9; border-color: #2e7d32; }
    .sell-card { background: #fce4ec; border-color: #c62828; }
    .status-dot { display: inline-block; width: 10px; height: 10px;
                  border-radius: 50%; margin-right: 6px; }
    .dot-green  { background: #4caf50; animation: pulse 1.5s infinite; }
    .dot-gray   { background: #9e9e9e; }
    .dot-orange { background: #ff9800; }
    @keyframes pulse {
        0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
    }
    .stock-row { font-size: 0.82rem; padding: 3px 0; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Session state initialisation — persists across reruns within one session
# =============================================================================
def init_state():
    defaults = {
        "running":          False,
        "levels":           {},
        "engine":           None,
        "signals":          [],        # list of Signal objects sent today
        "scan_count":       0,
        "last_scan_time":   None,
        "log":              [],        # list of (time_str, message) tuples
        "morning_sent":     False,
        "eod_sent":         False,
        "tg_ok":            None,      # None=unchecked, True/False
        "scan_error":       None,
        "quote_snapshot":   {},        # {symbol: {ltp, volume, state}}
        "next_scan_in":     0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =============================================================================
# Helpers
# =============================================================================
EFFECTIVE = CAPITAL * LEVERAGE

def t(s: str) -> dtime:
    h, m = map(int, s.split(":"))
    return dtime(h, m)

def now_t() -> dtime:
    return datetime.now().time().replace(second=0, microsecond=0)

def ist_now() -> str:
    return datetime.now().strftime("%H:%M:%S")

def ist_hm() -> str:
    return datetime.now().strftime("%H:%M")

def in_trading_window() -> bool:
    return t(TRADE_START_TIME) <= now_t() < t(SIGNAL_CUTOFF_TIME)

def past_cutoff() -> bool:
    return now_t() >= t(SIGNAL_CUTOFF_TIME)

def market_closed() -> bool:
    return now_t() >= t(MARKET_CLOSE_TIME)

def add_log(msg: str, level: str = "info"):
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌", "signal": "🔔"}
    icon = icons.get(level, "•")
    st.session_state.log.insert(0, (ist_now(), f"{icon} {msg}"))
    if len(st.session_state.log) > 100:
        st.session_state.log = st.session_state.log[:100]


# =============================================================================
# Live quote fetching
# =============================================================================
@st.cache_data(ttl=55)   # cache for 55s so rapid reruns don't re-fetch
def _fetch_quotes_cached(symbols_key: str, _ts: int):
    """Fetches 5m intraday candles for all symbols. Cached per minute."""
    import yfinance as yf
    symbols = NIFTY50_SYMBOLS
    yf_syms = [("M%26M.NS" if s == "M&M" else f"{s}.NS") for s in symbols]

    try:
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
        return {}, str(e)

    today = datetime.now().date()
    quotes = {}
    for i, sym in enumerate(symbols):
        try:
            df = raw[yf_syms[i]] if len(symbols) > 1 else raw
            df = df.dropna()
            df = df[df.index.date == today]
            if df.empty:
                continue
            last = df.iloc[-1]
            quotes[sym] = {
                "ltp":               round(float(last["Close"]), 2),
                "volume":            int(df["Volume"].sum()),
                "last_candle_volume": int(last["Volume"]),
                "high":              round(float(last["High"]), 2),
                "low":               round(float(last["Low"]), 2),
            }
        except Exception:
            continue
    return quotes, None


def get_quotes():
    # Use minute-level timestamp as cache key so we refetch every ~60s
    ts = int(time.time() // 60)
    return _fetch_quotes_cached("all", ts)


# =============================================================================
# One scan cycle
# =============================================================================
def do_scan():
    if not st.session_state.running:
        return
    if not st.session_state.engine:
        return

    quotes, err = get_quotes()

    if err:
        st.session_state.scan_error = err
        add_log(f"Quote fetch failed: {err}", "error")
        return

    st.session_state.scan_error = None
    st.session_state.scan_count += 1
    st.session_state.last_scan_time = ist_now()

    # Update quote snapshot for dashboard display
    snapshot = {}
    for sym, q in quotes.items():
        lvl = st.session_state.levels.get(sym, {})
        state = st.session_state.engine.trackers.get(sym)
        snapshot[sym] = {
            "ltp":    q["ltp"],
            "volume": q["volume"],
            "pdh":    lvl.get("pdh", 0),
            "pdl":    lvl.get("pdl", 0),
            "ema20":  lvl.get("ema20", 0),
            "state":  state.state if state else "idle",
            "dist_pdh_pct": round((q["ltp"] - lvl.get("pdh", q["ltp"])) / max(lvl.get("pdh", 1), 1) * 100, 2) if lvl else 0,
        }
    st.session_state.quote_snapshot = snapshot

    # Only generate signals during trading window and under limit
    if not in_trading_window():
        add_log(f"Scan #{st.session_state.scan_count} — outside trading window")
        return
    if len(st.session_state.signals) >= MAX_SIGNALS_PER_DAY:
        add_log(f"Scan #{st.session_state.scan_count} — max signals reached")
        return

    new_signals = st.session_state.engine.scan(quotes)

    for sig in new_signals:
        if len(st.session_state.signals) >= MAX_SIGNALS_PER_DAY:
            break
        ok = send_signal(sig)
        st.session_state.signals.append({
            "signal":    sig,
            "sent_ok":   ok,
            "sent_at":   ist_now(),
        })
        add_log(
            f"SIGNAL → {sig.direction} {sig.symbol} @ ₹{sig.entry_price} "
            f"| SL ₹{sig.stop_loss} | TGT ₹{sig.target}",
            "signal"
        )

    add_log(
        f"Scan #{st.session_state.scan_count} — {len(quotes)} stocks | "
        f"{len(new_signals)} new signal(s)"
    )


# =============================================================================
# Start / Stop actions
# =============================================================================
def start_scanner():
    add_log("Starting scanner...", "info")

    # Verify Telegram
    ok = test_notification()
    st.session_state.tg_ok = ok
    if not ok:
        add_log("Telegram test FAILED — check secrets", "error")
        return

    # Fetch levels
    with st.spinner("Fetching PDH/PDL levels for all 50 stocks..."):
        levels = fetch_previous_day_levels(NIFTY50_SYMBOLS)

    if not levels:
        add_log("Failed to fetch levels — check internet", "error")
        return

    st.session_state.levels = levels
    st.session_state.engine = SignalEngine(
        {s: levels[s] for s in NIFTY50_SYMBOLS if s in levels}
    )
    st.session_state.signals = []
    st.session_state.scan_count = 0
    st.session_state.log = []
    st.session_state.morning_sent = False
    st.session_state.eod_sent = False
    st.session_state.running = True

    # Morning summary
    send_morning_summary(levels)
    st.session_state.morning_sent = True
    add_log(f"Levels loaded for {len(levels)} stocks. Morning summary sent.", "success")


def stop_scanner():
    st.session_state.running = False
    if st.session_state.signals and not st.session_state.eod_sent:
        sigs = [s["signal"] for s in st.session_state.signals]
        send_eod_recap(sigs)
        st.session_state.eod_sent = True
    add_log("Scanner stopped.", "warning")


# =============================================================================
# UI — Header
# =============================================================================
col_title, col_status = st.columns([3, 1])
with col_title:
    st.title("📈 PDH/PDL Scanner")
    st.caption(f"Nifty 50 · {datetime.now().strftime('%d %b %Y')} · IST {ist_hm()}")

with col_status:
    if st.session_state.running:
        st.markdown(
            '<p style="text-align:right;margin-top:1.2rem">'
            '<span class="status-dot dot-green"></span>'
            '<b style="color:#2e7d32">LIVE</b></p>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<p style="text-align:right;margin-top:1.2rem">'
            '<span class="status-dot dot-gray"></span>'
            '<span style="color:#757575">STOPPED</span></p>',
            unsafe_allow_html=True
        )

# =============================================================================
# UI — Start / Stop button
# =============================================================================
btn_col, info_col = st.columns([1, 2])
with btn_col:
    if not st.session_state.running:
        if st.button("▶ Start Scanner", type="primary", use_container_width=True):
            start_scanner()
            st.rerun()
    else:
        if st.button("⏹ Stop Scanner", type="secondary", use_container_width=True):
            stop_scanner()
            st.rerun()

with info_col:
    if st.session_state.running and st.session_state.last_scan_time:
        st.caption(
            f"Last scan: {st.session_state.last_scan_time} · "
            f"Total scans: {st.session_state.scan_count} · "
            f"Signals: {len(st.session_state.signals)}/{MAX_SIGNALS_PER_DAY}"
        )
    elif not st.session_state.running:
        st.caption("Tap Start to begin. Signals arrive on Telegram automatically.")

st.divider()

# =============================================================================
# UI — Run scan cycle if active (this triggers on every rerun)
# =============================================================================
if st.session_state.running:
    # EOD check
    if market_closed() and not st.session_state.eod_sent:
        sigs = [s["signal"] for s in st.session_state.signals]
        send_eod_recap(sigs)
        st.session_state.eod_sent = True
        st.session_state.running = False
        add_log("Market closed. EOD recap sent.", "info")

    # Run scan
    if st.session_state.running:
        do_scan()

# =============================================================================
# UI — Key metrics row
# =============================================================================
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Capital", f"₹{CAPITAL:,}", f"5× = ₹{EFFECTIVE:,}")
with m2:
    st.metric("Signals today", f"{len(st.session_state.signals)}/{MAX_SIGNALS_PER_DAY}")
with m3:
    window_str = f"{TRADE_START_TIME}–{SIGNAL_CUTOFF_TIME}"
    in_win = in_trading_window() if st.session_state.running else False
    st.metric("Trading window", window_str, "ACTIVE" if in_win else "—")
with m4:
    levels_count = len(st.session_state.levels)
    st.metric("Stocks loaded", f"{levels_count}/50" if levels_count else "—")

st.divider()

# =============================================================================
# UI — Signal cards
# =============================================================================
st.subheader("🔔 Signals")

if not st.session_state.signals:
    st.info("No signals yet today. Watching all 50 stocks for breakouts.", icon="👀")
else:
    for item in reversed(st.session_state.signals):
        sig = item["signal"]
        is_buy = sig.direction == "BUY"
        card_class = "buy-card" if is_buy else "sell-card"
        emoji = "🟢" if is_buy else "🔴"
        sl_pct = abs(sig.entry_price - sig.stop_loss) / sig.entry_price * 100
        tgt_pct = abs(sig.target - sig.entry_price) / sig.entry_price * 100

        # Position size calc
        risk_amt = EFFECTIVE * RISK_PER_TRADE
        risk_per_share = abs(sig.entry_price - sig.stop_loss)
        qty = max(1, int(risk_amt / risk_per_share)) if risk_per_share > 0 else 1
        max_loss = qty * risk_per_share
        max_gain = qty * abs(sig.target - sig.entry_price)

        tg_status = "✅ Sent" if item["sent_ok"] else "❌ Failed"

        st.markdown(f"""
<div class="signal-card {card_class}">
  <b>{emoji} {sig.direction} — {sig.symbol}</b>
  &nbsp;&nbsp;<span style="font-size:0.8rem;color:#666">{item['sent_at']} · Telegram {tg_status}</span>
  <br>
  <table style="width:100%;margin-top:6px;font-size:0.88rem;border-collapse:collapse">
    <tr>
      <td><b>Entry</b></td><td>₹{sig.entry_price:,.2f}</td>
      <td><b>Stop Loss</b></td><td>₹{sig.stop_loss:,.2f} <span style="color:#c62828">(-{sl_pct:.1f}%)</span></td>
    </tr>
    <tr>
      <td><b>Target</b></td><td>₹{sig.target:,.2f} <span style="color:#2e7d32">(+{tgt_pct:.1f}%)</span></td>
      <td><b>Qty</b></td><td>{qty} shares</td>
    </tr>
    <tr>
      <td><b>Max loss</b></td><td style="color:#c62828">−₹{max_loss:,.0f}</td>
      <td><b>Max gain</b></td><td style="color:#2e7d32">+₹{max_gain:,.0f}</td>
    </tr>
  </table>
  <div style="margin-top:4px;font-size:0.8rem;color:#555">
    💡 {sig.trigger_reason} &nbsp;|&nbsp; PDH ₹{sig.pdh:,.2f} · PDL ₹{sig.pdl:,.2f}
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# =============================================================================
# UI — Live price table (all 50 stocks)
# =============================================================================
st.subheader("📊 Live Price Feed")

snap = st.session_state.quote_snapshot
if not snap:
    st.caption("Prices load after first scan.")
else:
    rows = []
    for sym, q in snap.items():
        ltp = q["ltp"]
        pdh = q["pdh"]
        pdl = q["pdl"]
        state = q["state"]

        # Distance from PDH/PDL
        dist_h = round((ltp - pdh) / pdh * 100, 2) if pdh else 0
        dist_l = round((ltp - pdl) / pdl * 100, 2) if pdl else 0

        # Status emoji
        state_map = {
            "idle":        "👀 Watching",
            "broken_up":   "⬆️ Broke PDH",
            "broken_down": "⬇️ Broke PDL",
            "done":        "✅ Done",
        }
        status = state_map.get(state, state)

        rows.append({
            "Symbol":    sym,
            "LTP":       f"₹{ltp:,.2f}",
            "PDH":       f"₹{pdh:,.2f}",
            "PDL":       f"₹{pdl:,.2f}",
            "vs PDH":    f"{dist_h:+.2f}%",
            "vs PDL":    f"{dist_l:+.2f}%",
            "Status":    status,
        })

    df = pd.DataFrame(rows)

    # Highlight rows with active breakout
    def highlight_row(row):
        if "Broke" in row["Status"]:
            return ["background-color: #fff9c4"] * len(row)
        elif "Done" in row["Status"]:
            return ["background-color: #e8f5e9"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(highlight_row, axis=1),
        use_container_width=True,
        height=420,
        hide_index=True,
    )

st.divider()

# =============================================================================
# UI — Activity log
# =============================================================================
st.subheader("📋 Activity Log")
if not st.session_state.log:
    st.caption("Log is empty.")
else:
    log_text = "\n".join(f"[{ts}] {msg}" for ts, msg in st.session_state.log[:30])
    st.code(log_text, language=None)

# =============================================================================
# UI — Settings expander (editable at runtime)
# =============================================================================
with st.expander("⚙️ Strategy Settings", expanded=False):
    sc1, sc2 = st.columns(2)
    with sc1:
        st.write(f"**Stop Loss:** {STOP_LOSS_PCT*100:.1f}%")
        st.write(f"**Target R:R:** {TARGET_RR}:1")
        st.write(f"**Volume filter:** {VOLUME_MULTIPLIER}×")
    with sc2:
        st.write(f"**Pullback:** {PULLBACK_PCT*100:.2f}%")
        st.write(f"**EMA period:** {EMA_PERIOD}")
        st.write(f"**Max signals/day:** {MAX_SIGNALS_PER_DAY}")
    st.caption("To change these, edit config.py and redeploy.")

    tg_col, _ = st.columns([1, 2])
    with tg_col:
        if st.button("Test Telegram", use_container_width=True):
            ok = test_notification()
            if ok:
                st.success("Telegram working ✅")
            else:
                st.error("Telegram failed ❌ — check secrets")

# =============================================================================
# Auto-refresh every 60 seconds while scanner is running
# =============================================================================
if st.session_state.running:
    time.sleep(SCAN_INTERVAL_SECONDS)
    st.rerun()