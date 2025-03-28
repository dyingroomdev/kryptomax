from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import random
import requests
import time
import os

# === CONFIGURATION ===
BOT_TOKEN = "7415463958:AAFB-KIiUvnStRTKcqxnJTEpFonoWjl9FAA"
BLOCKCYPHER_TOKEN = "b4aa61c7eab349bcb23a897c9734b211"
BTC_ADDRESS_FILE = "btc_addresses.txt"
ETH_ADDRESS_FILE = "eth_addresses.txt"
PGP_KEY_FILE = "pgp.txt"
ADMIN_ID = 6190128347

# === Storage ===
user_states = {}
refund_addresses = {}
withdrawal_requests = {}
user_data = set()

# === Helper Functions ===
def get_pgp_key():
    try:
        with open(PGP_KEY_FILE, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"PGP key error: {e}")
        return "PGP key currently unavailable"

def generate_seed_phrase():
    with open("english.txt", "r") as f:
        words = f.read().splitlines()
    return " ".join(random.sample(words, 12))

def get_random_address(filename):
    try:
        with open(filename, "r") as f:
            addresses = [line.strip() for line in f if line.strip()]
        return random.choice(addresses) if addresses else None
    except:
        return None

def check_blockchain_for_tx(address, coin):
    url = f"https://api.blockcypher.com/v1/{'btc/main' if coin == 'btc' else 'eth/main'}/addrs/{address}/full?token={BLOCKCYPHER_TOKEN}"
    try:
        res = requests.get(url)
        data = res.json()
        if 'txs' in data:
            for tx in data['txs']:
                if tx.get('confirmations', 0) > 0:
                    value = tx['total'] / 1e8 if coin == 'btc' else tx['total'] / 1e18
                    return tx['hash'], value, tx['confirmations']
    except Exception as e:
        print("Blockchain check error:", e)
    return None, 0, 0

# === Command Handlers ===
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data.add(user_id)
    keyboard = [
        [InlineKeyboardButton("💰 Deposit BTC", callback_data='deposit_btc')],
        [InlineKeyboardButton("💰 Deposit ETH", callback_data='deposit_eth')],
        [InlineKeyboardButton("📜 Guide", callback_data='show_guide'),
         InlineKeyboardButton("🔐 PGP Key", callback_data='show_pgp')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome to KryptoMaxBot! Please select an option:", reply_markup=reply_markup)

def confirm(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_states:
        update.message.reply_text("Please start a session using /start.")
        return

    coin = user_states[user_id]["coin"]
    address = user_states[user_id]["address"]

    update.message.reply_text("⏳ Verifying your transaction on blockchain...")
    txid, value, conf = check_blockchain_for_tx(address, coin)

    if txid:
        update.message.reply_text(
            f"✅ Transaction detected!\n\n"
            f"*Amount:* {value:.6f} {coin.upper()}\n"
            f"*Confirmations:* {conf}\n"
            f"*TXID:* `{txid}`",
            parse_mode="Markdown"
        )
        update.message.reply_text("Please enter the *withdrawal address*:", parse_mode="Markdown")
        user_states[user_id]["awaiting_withdraw"] = True
    else:
        update.message.reply_text("❌ No confirmed transactions found. Try again later.")

def pgp_command(update: Update, context: CallbackContext):
    key = get_pgp_key()
    update.message.reply_text(
        f"🔐 *KryptoMax Official PGP Key*\n\n"
        f"```\n{key}\n```\n\n"
        f"Verify all official communications with this key.",
        parse_mode="Markdown"
    )

def guide(update: Update, context: CallbackContext):
    guide_text = """
📜 *KryptoMax Guide* 🚡

1. /start - Begin session
2. Choose deposit currency
3. Send crypto to provided address
4. /confirm - Verify transaction
5. Set withdrawal address
6. (Optional) Set refund address
7. Complete transaction

🔐 Verify PGP: /pgp
"""
    update.effective_message.reply_text(guide_text, parse_mode="Markdown")

# ... [Keep all your other existing functions unchanged] ...

# === Main Function ===
def main():
    # Verify required files exist
    required_files = [BTC_ADDRESS_FILE, ETH_ADDRESS_FILE, "english.txt", PGP_KEY_FILE]
    for file in required_files:
        if not os.path.exists(file):
            print(f"⚠️ Missing required file: {file}")

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("confirm", confirm))  # Now properly defined
    dp.add_handler(CommandHandler("pgp", pgp_command))
    dp.add_handler(CommandHandler("guide", guide))
    dp.add_handler(CommandHandler("admin", admin))

    # Other handlers
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    dp.add_handler(MessageHandler(Filters.regex("^(Users|Deposits|Withdrawals|Refunds)$"), admin_panel_handler))

    print("✅ Bot starting with all handlers registered")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
