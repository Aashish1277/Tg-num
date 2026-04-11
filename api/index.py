import os
import requests
import telebot
from telebot import types
from flask import Flask, request

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 5714613336
API_URL = "https://ayaanmods.site/number.php?key=annonymous&number="

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# --- KEYBOARDS ---

def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔍 Start New Search", callback_data="start_search"))
    return markup

def result_buttons():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗑️ Clear Result", callback_data="delete_msg"))
    return markup

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, 
        "<b>🌟 PRO NUMBER FINDER 🌟</b>\n\nReady for unlimited searches. Click below:", 
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['admin'])
def admin_logs(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "📊 <b>Admin Note:</b> Session logs are cleared on every Vercel sleep. Check Vercel Dashboard for permanent logs.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "start_search":
        bot.send_message(call.message.chat.id, "<b>📥 INPUT NUMBER:</b>")
    elif call.data == "delete_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True)
def process_lookup(message):
    number = message.text.strip()

    if not number.isdigit() or len(number) < 10:
        bot.reply_to(message, "⚠️ Invalid number.")
        return

    # Notify Admin immediately (no delay)
    try:
        bot.send_message(ADMIN_ID, f"🔍 <b>Search:</b> <code>{number}</code> by <code>{message.from_user.id}</code>")
    except:
        pass

    status = bot.send_message(message.chat.id, "📡 <i>Searching Database...</i>")

    try:
        # TIMEOUT FIX: We set timeout to 8 seconds to prevent Telegram from retrying (double replies)
        response = requests.get(f"{API_URL}{number}", timeout=8)
        bot.delete_message(message.chat.id, status.message_id)

        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"]:
                for record in data["result"]:
                    res_msg = (
                        "<b>✨ RECORD FOUND ✨</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 <b>NAME:</b> <code>{record.get('name', 'N/A').upper()}</code>\n"
                        f"📞 <b>PHONE:</b> <code>{record.get('mobile', 'N/A')}</code>\n"
                        f"👴 <b>FATHER:</b> <code>{record.get('father_name', 'N/A').upper()}</code>\n"
                        f"🆔 <b>CNIC:</b> <code>{record.get('id', 'N/A')}</code>\n"
                        f"🏠 <b>ADDR:</b> <code>{record.get('address', 'N/A')}</code>\n"
                        "━━━━━━━━━━━━━━━━━━━━"
                    )
                    bot.send_message(message.chat.id, res_msg, reply_markup=result_buttons())
            else:
                bot.send_message(message.chat.id, "❌ No data found for this number.")
        else:
            bot.send_message(message.chat.id, "⚠️ API Server is down. Try later.")

    except requests.exceptions.Timeout:
        bot.delete_message(message.chat.id, status.message_id)
        bot.send_message(message.chat.id, "⏳ <b>Timeout:</b> Search took too long. Please try again.")
    except Exception as e:
        bot.send_message(message.chat.id, "🚫 <b>Error:</b> API Connection Failed.")

# --- WEBHOOK ROUTE ---

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    return "Bot is Active", 200
