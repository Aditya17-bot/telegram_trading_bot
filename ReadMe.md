# PDH/PDL Signal Scanner — Streamlit App

Open on your phone, tap Start, get Telegram alerts. No terminal needed.

---

## Deploy to Streamlit Cloud (one-time, ~10 minutes)

### Step 1 — Put the code on GitHub

1. Go to [github.com](https://github.com) → sign in or create free account
2. Click **New repository** → name it `pdh-scanner` → **Private** → Create
3. Upload all these files (drag and drop in the GitHub web UI):
   - `app.py`
   - `config.py`
   - `data.py`
   - `strategy.py`
   - `notify.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - **Do NOT upload** `.streamlit/secrets.toml` (keep that local only)

### Step 2 — Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **New app**
4. Repository: `your-username/pdh-scanner`
5. Branch: `main`
6. Main file path: `app.py`
7. Click **Deploy**

### Step 3 — Add your secrets

1. In Streamlit Cloud, open your app → click **⋮ (three dots)** → **Settings**
2. Click **Secrets** tab
3. Paste this (replace with your real values):

```toml
TELEGRAM_BOT_TOKEN = "7412836901:AAHxxxxxxxxxxxxxxxxxxxxxxxx"
TELEGRAM_CHAT_ID   = "123456789"
```

4. Click **Save** — app restarts automatically

### Step 4 — Open on your phone

Your app URL will be: `https://your-app-name.streamlit.app`

Bookmark it. Every morning, open it and tap **Start Scanner**.

---

## Daily routine

| Time | Action |
|------|--------|
| 9:00 AM | Open app URL on phone, tap **▶ Start Scanner** |
| 9:15 AM | Morning summary arrives on Telegram |
| 9:30 AM | Scanner starts watching for breakouts |
| Signal fires | Telegram notification → open Kite app → place MIS order |
| 3:10 PM | Square off open positions manually on Kite |
| 3:15 PM | EOD recap arrives on Telegram |

---

## What you see on the dashboard

- **Signal cards** — every signal with entry, SL, target, suggested qty
- **Live price table** — all 50 stocks with LTP, vs PDH/PDL %, and current state
- **Activity log** — timestamped record of every scan and event
- **Metrics bar** — capital, signals sent, trading window status

---

## How Streamlit Cloud keeps running

Streamlit Cloud keeps your app alive as long as someone has it open in a browser.
Since you open it in the morning and leave it open on your phone, it runs all day.

**Tip:** On iPhone/Android, add the URL to your home screen (Share → Add to Home Screen).
It opens fullscreen like an app.

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit dashboard — the only new file |
| `config.py` | Settings (reads secrets from Streamlit Cloud) |
| `strategy.py` | Signal detection logic (unchanged) |
| `data.py` | Fetches PDH/PDL via yfinance (unchanged) |
| `notify.py` | Telegram notifications (unchanged) |
| `requirements.txt` | Python dependencies |
| `.streamlit/config.toml` | UI theme settings |
| `.streamlit/secrets.toml` | Local secrets — **never upload to GitHub** |

---

## Cost

| Item | Cost |
|------|------|
| GitHub | ₹0 |
| Streamlit Cloud | ₹0 |
| Telegram bot | ₹0 |
| Kite API | ₹0 (not needed) |
| **Total** | **₹0/month** |