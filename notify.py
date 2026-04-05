# =============================================================================
# notify.py — Sends Telegram messages when a signal fires.
# Also sends a morning summary and an end-of-day recap.
# =============================================================================

import requests
import logging
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CAPITAL, LEVERAGE, RISK_PER_TRADE

log = logging.getLogger(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def _send(text: str, parse_mode: str = "HTML") -> bool:
    """Core send function. Returns True if message delivered."""
    try:
        resp = requests.post(
            TELEGRAM_URL,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        else:
            log.warning(f"Telegram send failed: {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        log.error(f"Telegram error: {e}")
        return False


def calculate_qty(entry: float, sl: float) -> int:
    """How many shares to buy based on your capital settings."""
    effective = CAPITAL * LEVERAGE
    risk_amount = effective * RISK_PER_TRADE
    risk_per_share = abs(entry - sl)
    if risk_per_share <= 0:
        return 1
    qty = int(risk_amount / risk_per_share)
    # Don't let position exceed 80% of effective capital
    max_qty = int((effective * 0.8) / entry)
    return max(1, min(qty, max_qty))


def send_signal(signal) -> bool:
    """
    Sends a trade signal notification to your phone.
    Looks like:
    
    🟢 BUY SIGNAL — TATAMOTORS
    ━━━━━━━━━━━━━━━━━━━━
    Entry:      ₹924.50
    Stop Loss:  ₹919.90  (-0.5%)
    Target:     ₹933.60  (+1.0%)
    ...
    """
    is_buy = signal.direction == "BUY"
    emoji = "🟢" if is_buy else "🔴"
    direction_word = "BUY" if is_buy else "SELL SHORT"

    entry = signal.entry_price
    sl = signal.stop_loss
    target = signal.target

    sl_pct = abs(entry - sl) / entry * 100
    tgt_pct = abs(target - entry) / entry * 100
    qty = calculate_qty(entry, sl)
    position_value = qty * entry
    max_loss = qty * abs(entry - sl)
    max_gain = qty * abs(target - entry)

    # Time since signal generated
    now = datetime.now().strftime("%I:%M %p")

    msg = (
        f"{emoji} <b>{signal.direction} SIGNAL — {signal.symbol}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 <b>Time:</b> {now}\n"
        f"📍 <b>Entry:</b>      ₹{entry:,.2f}\n"
        f"🛑 <b>Stop Loss:</b>  ₹{sl:,.2f}  <i>(-{sl_pct:.1f}%)</i>\n"
        f"🎯 <b>Target:</b>     ₹{target:,.2f}  <i>(+{tgt_pct:.1f}%)</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Suggested qty:</b> {qty} shares\n"
        f"💰 <b>Position value:</b> ₹{position_value:,.0f}\n"
        f"📉 <b>Max loss:</b>  -₹{max_loss:,.0f}\n"
        f"📈 <b>Max gain:</b>  +₹{max_gain:,.0f}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>Why:</b> {signal.trigger_reason}\n"
        f"📊 PDH: ₹{signal.pdh:,.2f}  |  PDL: ₹{signal.pdl:,.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Place as <b>MIS Limit order</b> on Kite\n"
        f"Square off by <b>3:10 PM</b> manually if needed"
    )

    ok = _send(msg)
    if ok:
        log.info(f"Telegram signal sent for {signal.symbol}")
    return ok


def send_morning_summary(levels: dict) -> bool:
    """
    Sent at 9:15 AM. Shows today's key levels so you know what to watch.
    Lists top 10 stocks with the tightest PDH-PDL ranges (most likely to break).
    """
    # Sort by tightest range (% spread between PDH and PDL)
    ranked = sorted(
        levels.items(),
        key=lambda x: (x[1]["pdh"] - x[1]["pdl"]) / x[1]["pdc"] * 100
    )[:10]

    date_str = datetime.now().strftime("%d %b %Y, %A")
    lines = [
        f"☀️ <b>Good morning! PDH/PDL Scanner ready</b>",
        f"📅 {date_str}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Watching <b>{len(levels)}</b> Nifty 50 stocks",
        f"Signals start at <b>9:30 AM</b>, cutoff <b>2:30 PM</b>",
        f"",
        f"<b>Top 10 tightest ranges today:</b>",
        f"<i>(tighter range = easier breakout)</i>",
        f"",
    ]

    for sym, lvl in ranked:
        spread = (lvl["pdh"] - lvl["pdl"]) / lvl["pdc"] * 100
        lines.append(
            f"• <b>{sym}</b>  PDH: ₹{lvl['pdh']:,.1f}  PDL: ₹{lvl['pdl']:,.1f}  "
            f"<i>({spread:.1f}% range)</i>"
        )

    lines += [
        f"",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"I'll ping you the moment a signal fires 🔔",
    ]

    return _send("\n".join(lines))


def send_eod_recap(signals_sent: list) -> bool:
    """
    Sent at 3:15 PM. Quick end-of-day summary of all signals that fired.
    """
    date_str = datetime.now().strftime("%d %b")

    if not signals_sent:
        msg = (
            f"🌙 <b>EOD Recap — {date_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"No signals fired today.\n"
            f"Filters kept us out — that's discipline, not a loss. 💪\n"
            f"See you tomorrow!"
        )
    else:
        lines = [
            f"🌙 <b>EOD Recap — {date_str}</b>",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"Signals sent today: <b>{len(signals_sent)}</b>",
            f"",
        ]
        for i, s in enumerate(signals_sent, 1):
            lines.append(
                f"{i}. {s.direction} <b>{s.symbol}</b> @ ₹{s.entry_price:,.2f} "
                f"→ SL ₹{s.stop_loss:,.2f} / TGT ₹{s.target:,.2f}"
            )
        lines += [
            f"",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"⚠️ If you still have open positions, <b>square off NOW</b> before 3:20 PM",
            f"Zerodha auto-squares MIS at 3:20 PM (may get worse price).",
        ]
        msg = "\n".join(lines)

    return _send(msg)


def send_fake_breakout_alert(symbol: str, level: float, direction: str) -> bool:
    """Warns you if a stock faked out — so you don't chase it manually."""
    emoji = "⚠️"
    msg = (
        f"{emoji} <b>FAKE BREAKOUT — {symbol}</b>\n"
        f"Price broke {'above' if direction == 'up' else 'below'} "
        f"₹{level:,.2f} then reversed.\n"
        f"<i>Do NOT trade this stock today.</i>"
    )
    return _send(msg)


def send_heartbeat() -> bool:
    """Sent every hour so you know the script is still alive."""
    now = datetime.now().strftime("%I:%M %p")
    msg = f"💓 Scanner alive — {now} | No signals yet"
    return _send(msg)


def test_notification() -> bool:
    """Run this first to confirm Telegram is working before market hours."""
    msg = (
        f"✅ <b>PDH/PDL Scanner connected!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Your signal bot is set up correctly.\n"
        f"Capital: ₹{CAPITAL:,} × {LEVERAGE}× leverage = ₹{CAPITAL*LEVERAGE:,} effective\n"
        f"Signals will arrive here during market hours.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>This is a test message.</i>"
    )
    return _send(msg)