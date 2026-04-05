# PDH/PDL Signal Scanner + Telegram Notifier

No Kite API. No static IP. No automation risk.
You get a Telegram message → you place the order manually on your phone.

---

## What you'll receive on your phone

**Morning (9:15 AM):**
```
☀️ Good morning! PDH/PDL Scanner ready
📅 04 Apr 2025, Friday
━━━━━━━━━━━━━━━━━━━━
Watching 50 Nifty 50 stocks
Signals start at 9:30 AM, cutoff 2:30 PM

Top 10 tightest ranges today:
• TATAMOTORS  PDH: ₹924.5  PDL: ₹901.2  (2.5% range)
...
```

**When a signal fires:**
```
🟢 BUY SIGNAL — TATAMOTORS
━━━━━━━━━━━━━━━━━━━━
🕐 Time: 10:42 AM
📍 Entry:      ₹924.50
🛑 Stop Loss:  ₹919.90  (-0.5%)
🎯 Target:     ₹933.60  (+1.0%)
━━━━━━━━━━━━━━━━━━━━
📦 Suggested qty: 27 shares
💰 Position value: ₹24,961
📉 Max loss:  -₹500
📈 Max gain:  +₹247
━━━━━━━━━━━━━━━━━━━━
💡 Why: PDH ₹922.00 broken + pullback
⚠️ Place as MIS Limit order on Kite
Square off by 3:10 PM manually if needed
```

**End of day (3:15 PM):**
```
🌙 EOD Recap — 04 Apr
━━━━━━━━━━━━━━━━━━━━
Signals sent today: 2
1. BUY TATAMOTORS @ ₹924.50 → SL ₹919.90 / TGT ₹933.60
2. SELL SBIN @ ₹812.30 → SL ₹816.40 / TGT ₹804.10
⚠️ Square off all open positions before 3:20 PM
```

---

## One-time setup (do this once, ~10 minutes total)

### Step 1 — Install Python libraries
```bash
pip install -r requirements.txt
```

### Step 2 — Create your Telegram bot (2 minutes)

1. Open Telegram on your phone
2. Search for **@BotFather** and open it
3. Send: `/newbot`
4. It asks for a name — type anything, e.g. `My Trading Bot`
5. It asks for a username — type anything ending in `bot`, e.g. `mytrades_signal_bot`
6. BotFather gives you a token that looks like: `7412836901:AAHxxxxxxxxxxxxxxxxxxxxxxxx`
7. **Copy that token**

### Step 3 — Find your Chat ID (1 minute)
```bash
python setup_telegram.py
```
This script guides you through finding your Chat ID and tests the connection.

### Step 4 — Update config.py
Open `config.py` and fill in:
```python
TELEGRAM_BOT_TOKEN = "7412836901:AAHxxxxxxxxxxxxxxxxxxxxxxxx"
TELEGRAM_CHAT_ID   = "123456789"
CAPITAL            = 5000
```

### Step 5 — Prevent laptop from sleeping
So the script keeps running while you're away:

**Windows:**
- Settings → Power & Sleep → Sleep → set to "Never" (when plugged in)
- Or run: `powercfg /change standby-timeout-ac 0` in Command Prompt

**Mac:**
- System Settings → Battery → Prevent automatic sleeping when display is off
- Or run: `caffeinate -i python scanner.py` instead of `python scanner.py`

---

## Daily routine (2 minutes every morning)

```bash
# Run once at 9:00 AM
python data.py

# Then immediately run this (leave it running all day)
python scanner.py
```

That's it. Go about your day. Signals come to your phone.

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | Your settings — edit this first |
| `data.py` | Fetches PDH/PDL each morning (uses yfinance, free) |
| `strategy.py` | Signal detection logic |
| `notify.py` | Telegram message formatting and sending |
| `scanner.py` | Main loop — ties everything together |
| `setup_telegram.py` | One-time helper to find your Chat ID |

---

## How to place the trade on Kite app

When you get the notification:
1. Open **Kite** app
2. Search the stock name (e.g. TATAMOTORS)
3. Tap **Buy** (or **Sell** for short signals)
4. Order type: **Limit**
5. Product: **MIS** (this gives 5× leverage)
6. Price: enter the entry price from the notification
7. Quantity: enter the quantity from the notification
8. Tap **Buy** → confirm

Then set your stop loss:
1. Go to Positions tab
2. Tap the position → **Add SL**
3. Set trigger price = Stop Loss from the notification
4. Order type: SL-M (stop loss market)

**Remember: Square off by 3:10 PM.** If you forget, Zerodha auto-squares MIS at 3:20 PM — but you may get a worse price.

---

## Costs

| Item | Cost |
|------|------|
| Kite Connect API | ₹0 (not needed — using yfinance) |
| Telegram bot | ₹0 (completely free) |
| Python + libraries | ₹0 (all free) |
| **Total monthly cost** | **₹0** |

You only pay normal Zerodha brokerage when you place trades manually.

---

## Troubleshooting

**"No quotes received"**
→ yfinance sometimes has delays. Wait for the next scan (60 seconds).

**Telegram messages not arriving**
→ Make sure you messaged your bot at least once before running setup_telegram.py
→ Double-check token and chat ID in config.py — no extra spaces

**"No signals all day"**
→ Normal on low-volatility days. The filters are strict on purpose.
→ Try lowering VOLUME_MULTIPLIER to 1.2 in config.py

**Laptop went to sleep**
→ Check your power settings (see Step 5 above)
→ On Windows, use the free app "Caffeine" to prevent sleep