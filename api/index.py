import os
import requests
import telebot
from telebot import types
from flask import Flask, request

# --- BOT CONFIGURATION ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 5714613336
API_URL = "https://ayaanmods.site/number.php?key=annonymous&number="

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# --- IN-MEMORY DATABASE ---
# Note: Vercel resets these variables every few minutes of inactivity.
# For permanent data, you would need to connect a database (like MongoDB).
data_store = {
    "total_users": set(),
    "search_logs": []  # Stores last 50 searches
}

# --- KEYBOARDS ---

def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_search = types.InlineKeyboardButton("🔍 Start New Search", callback_data="start_search")
    btn_channel = types.InlineKeyboardButton("📢 Updates Channel", url="https://t.me/ayanmods")
    markup.add(btn_search, btn_channel)
    return markup

def result_buttons():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_new = types.InlineKeyboardButton("🔎 Search Again", callback_data="start_search")
    btn_del = types.InlineKeyboardButton("🗑️ Close Result", callback_data="delete_msg")
    markup.add(btn_new, btn_del)
    return markup

def back_btn():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_home"))
    return markup

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.from_user.id
    data_store["total_users"].add(user_id)
    
    welcome_text = (
        "<b>🌟 WELCOME TO PRO NUMBER FINDER 🌟</b>\n\n"
        "<i>The most advanced tool to find mobile registration details instantly.</i>\n\n"
        "<b>✅ Unlimited Searches Enabled</b>\n"
        "<b>✅ Fast Server Access</b>\n"
        "<b>✅ 1-Tap Copy Feature</b>\n\n"
        "Click the button below to begin your search."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is for the owner only.")
        return
    
    user_count = len(data_store["total_users"])
    logs = data_store["search_logs"][-15:] # Get last 15 searches
    
    log_text = ""
    for entry in logs:
        log_text += f"👤 <code>{entry['user']}</code> 🔍 <code>{entry['num']}</code>\n"
    
    if not log_text:
        log_text = "No recent searches found."

    admin_msg = (
        "<b>🛠️ ADMIN CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total Session Users:</b> {user_count}\n"
        f"📊 <b>Recent Search Logs:</b>\n\n{log_text}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(ADMIN_ID, admin_msg)

# --- CALLBACK HANDLERS ---

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "start_search":
        bot.send_message(
            call.message.chat.id,
            "<b>📥 INPUT NUMBER</b>\n\nPlease send the mobile number:\n\n<b>Example:</b> <code>7895134397</code>"
        )
    elif call.data == "back_home":
        bot.send_message(call.message.chat.id, "<b>🌟 MAIN MENU</b>", reply_markup=main_menu())
    elif call.data == "delete_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    bot.answer_callback_query(call.id)

# --- SEARCH LOGIC ---

@bot.message_handler(func=lambda message: True)
def process_lookup(message):
    number = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or user_id

    # Validation
    if not number.isdigit() or len(number) < 10:
        bot.reply_to(message, "⚠️ <b>Invalid Input:</b> Please enter a valid 10-digit number.")
        return

    # Add to logs for Admin
    data_store["search_logs"].append({"user": username, "num": number})
    data_store["total_users"].add(user_id)

    # Loading status
    status = bot.send_message(message.chat.id, "<b>📡 Searching Secure Database...</b>")

    try:
        response = requests.get(f"{API_URL}{number}", timeout=15)
        
        # We always send new messages (as requested)
        bot.delete_message(message.chat.id, status.message_id)
        
        if response.status_code == 200:
            data = response.json()
            
            if "result" in data and len(data["result"]) > 0:
                for record in data["result"]:
                    # Formatting each record professionally
                    res_msg = (
                        "<b>✨ REGISTRATION DETAILS FOUND ✨</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 <b>NAME:</b> <code>{record.get('name', 'N/A').upper()}</code>\n"
                        f"📞 <b>PHONE:</b> <code>{record.get('mobile', 'N/A')}</code>\n"
                        f"📱 <b>ALT:</b> <code>{record.get('alternate', 'N/A')}</code>\n"
                        f"👴 <b>FATHER:</b> <code>{record.get('father_name', 'N/A').upper()}</code>\n"
                        f"🆔 <b>CNIC/ID:</b> <code>{record.get('id', 'N/A')}</code>\n"
                        f"🔴 <b>CIRCLE:</b> <code>{record.get('circle', 'N/A')}</code>\n"
                        f"🏠 <b>ADDRESS:</b> <code>{record.get('address', 'N/A')}</code>\n"
                        "━━━━━━━━━━━━━━━━━━━━"
                    )
                    bot.send_message(message.chat.id, res_msg, reply_markup=result_buttons())
            else:
                bot.send_message(message.chat.id, "❌ <b>Data Not Found:</b> No records exist for this number.")
        else:
            bot.send_message(message.chat.id, "⚠️ <b>API Error:</b> Server is currently busy.")

    except Exception:
        bot.send_message(message.chat.id, "🚫 <b>System Error:</b> Connection to database failed.")

# --- VERCEL ENTRY POINT ---

@app.route('/webhook', methods=['POST'])
def get_update():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/')
def home():
    return "Bot is running online...", 200
