import os
import requests
import telebot
from telebot import types
from flask import Flask, request
import logging

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 5714613336
API_URL = "https://ayaanmods.site/number.php?key=annonymous&number="
CHANNEL_USERNAME = "@TechTrovebyb44ner" 
CHANNEL_URL = "https://t.me/TechTrovebyb44ner"

# Configure Logging
logging.basicConfig(level=logging.INFO)

# Initialize Bot - threaded=True helps handle multiple requests without blocking
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True)
app = Flask(__name__)

# Persistent session for connection pooling (Significant speed boost)
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0 Safari/537.36'})

# --- HELPER FUNCTIONS ---

def is_user_joined(user_id):
    """Checks if the user is a member of the required channel."""
    if user_id == ADMIN_ID: return True # Admin bypass
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Join check error: {e}")
        # If bot is not admin in channel, it returns False. 
        # Make sure bot is Admin in the channel!
        return False

# --- KEYBOARDS ---

def join_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="check_join"))
    return markup

def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔍 Start New Search", callback_data="start_search"))
    return markup

def result_buttons():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔎 New Search", callback_data="start_search"),
        types.InlineKeyboardButton("🗑️ Clear", callback_data="delete_msg")
    )
    return markup

# --- COMMANDS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    if not is_user_joined(message.from_user.id):
        bot.send_message(
            message.chat.id, 
            f"<b>❌ ACCESS DENIED</b>\n\nYou must join our channel to use this bot.", 
            reply_markup=join_markup()
        )
        return

    welcome_text = (
        "<b>🌟 PRO NUMBER FINDER 🌟</b>\n\n"
        "Send a 10-digit mobile number to get details."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# --- CALLBACKS ---

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "check_join":
        if is_user_joined(call.from_user.id):
            bot.edit_message_text("✅ Access Granted!", call.message.chat.id, call.message.message_id)
            welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "⚠️ You still haven't joined!", show_alert=True)

    elif call.data == "start_search":
        bot.send_message(call.message.chat.id, "<b>📥 Send the 10-digit mobile number:</b>")
        bot.answer_callback_query(call.id)
            
    elif call.data == "delete_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- CORE SEARCH LOGIC ---

@bot.message_handler(func=lambda message: message.text and message.text.isdigit())
def process_lookup(message):
    user_id = message.from_user.id
    number = message.text.strip()

    # 1. Force Join Check
    if not is_user_joined(user_id):
        bot.send_message(message.chat.id, "<b>⚠️ Join the channel first!</b>", reply_markup=join_markup())
        return

    # 2. Validation
    if len(number) != 10:
        bot.reply_to(message, "⚠️ <b>Error:</b> Please enter exactly 10 digits.")
        return

    # 3. Processing notification
    status_msg = bot.send_message(message.chat.id, "<b>📡 Searching Database...</b>")

    try:
        # Request with a strict timeout to prevent double-response bugs
        response = session.get(f"{API_URL}{number}", timeout=8)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("result"):
                final_response = "<b>✅ SEARCH RESULTS:</b>\n\n"
                # Showing up to 2 records to keep message length safe
                for record in data["result"][:2]:
                    final_response += (
                        f"👤 <b>Name:</b> <code>{str(record.get('name')).title()}</code>\n"
                        f"📞 <b>Phone:</b> <code>{record.get('mobile')}</code>\n"
                        f"👴 <b>Father:</b> <code>{str(record.get('father_name')).title()}</code>\n"
                        f"🆔 <b>CNIC/ID:</b> <code>{record.get('id')}</code>\n"
                        f"🏠 <b>Address:</b> <code>{record.get('address')}</code>\n"
                        f"--------------------------\n"
                    )
                
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_message(message.chat.id, final_response, reply_markup=result_buttons())
                
                # Admin Log
                log = f"🔎 <b>Search:</b> <code>{number}</code>\n👤 <b>By:</b> {message.from_user.first_name} ({user_id})"
                bot.send_message(ADMIN_ID, log)
            else:
                bot.edit_message_text("❌ <b>No records found.</b>", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("⚠️ <b>API Error:</b> Server is busy.", message.chat.id, status_msg.message_id)

    except requests.exceptions.ReadTimeout:
        bot.edit_message_text("⏳ <b>Timeout:</b> Server took too long to respond.", message.chat.id, status_msg.message_id)
    except Exception as e:
        logging.error(f"Search Error: {e}")
        bot.edit_message_text("🚫 <b>System Error.</b>", message.chat.id, status_msg.message_id)

# --- WEBHOOK HANDLING ---

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    # This prevents the webhook from hanging and causing double-responses
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # Replace 'YOUR_VERCEL_URL' with your actual deployment URL
    # bot.set_webhook(url='https://YOUR_VERCEL_URL/' + BOT_TOKEN)
    return "Bot is alive", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
