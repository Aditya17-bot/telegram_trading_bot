# =============================================================================
# setup_telegram.py — Run this ONCE to find your Telegram Chat ID.
# After running, copy the values into your local .env file.
# =============================================================================

import requests
import sys

print()
print("=" * 50)
print("  TELEGRAM SETUP HELPER")
print("=" * 50)
print()
print("Step 1: Open Telegram and message @BotFather")
print("Step 2: Send: /newbot")
print("Step 3: Follow the prompts, get your bot token")
print()

token = input("Paste your bot token here: ").strip()
if not token:
    print("No token entered. Exiting.")
    sys.exit(1)

print()
print("Now open Telegram and send ANY message to your new bot.")
input("Press Enter once you've messaged your bot...")

# Fetch updates to find chat ID
url = f"https://api.telegram.org/bot{token}/getUpdates"
try:
    resp = requests.get(url, timeout=10)
    data = resp.json()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

if not data.get("ok") or not data.get("result"):
    print()
    print("No messages found. Make sure you sent a message to your bot first.")
    print(f"Raw response: {data}")
    sys.exit(1)

update = data["result"][-1]
chat_id = update["message"]["chat"]["id"]
username = update["message"]["chat"].get("first_name", "User")

print()
print("=" * 50)
print(f"  Found! Hello, {username}!")
print(f"  Your Chat ID: {chat_id}")
print("=" * 50)
print()
print("Now add these to your local .env file:")
print(f"  TELEGRAM_BOT_TOKEN={token}")
print(f"  TELEGRAM_CHAT_ID={chat_id}")
print()

# Test it
confirm = input("Send a test message to confirm? (y/n): ").strip().lower()
if confirm == "y":
    test_url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(test_url, json={
        "chat_id": chat_id,
        "text": "✅ *PDH/PDL Scanner connected!* Your signals will arrive here.",
        "parse_mode": "Markdown"
    })
    print("Test message sent! Check your Telegram.")
