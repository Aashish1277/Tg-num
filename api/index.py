import os
import requests
import telebot
from telebot import types
from flask import Flask, request

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 5714613336
API_URL = "https://ayaanmods.site/number.php?key=annonymous&number="

# Use threaded=False for Webhook environments like Vercel to prevent memory leaks
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)
app = Flask(__name__)

# Pre-define a session for faster API calls (keeps connection alive)
session = requests.Session()

# --- KEYBOARDS ---

def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔍 Start New Search", callback_data="start_search"))
    return markup

def result_buttons():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_new = types.InlineKeyboardButton("🔎 New Search", callback_data="start_search")
    btn_del = types.InlineKeyboardButton("🗑️ Clear Result", callback_data="delete_msg")
    markup.add(btn_new, btn_del)
    return markup

# --- COMMANDS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    welcome_text = (
        "<b>🌟 WELCOME TO PRO NUMBER FINDER 🌟</b>\n\n"
        "<i>The most advanced tool to find mobile registration details instantly.</i>\n\n"
        "<b>✅ High Accuracy</b>\n"
        "<b>✅ Fast Server Access</b>\n"
        "<b>✅ Unlimited Searches</b>\n\n"
        "Click the button below to begin your search."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# --- CALLBACKS ---

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "start_search":
        bot.send_message(call.message.chat.id, "<b>📥 INPUT NUMBER</b>\n\nPlease send the 10-digit mobile number:")
    elif call.data == "delete_msg":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass 
    bot.answer_callback_query(call.id)

# --- CORE SEARCH LOGIC ---

@bot.message_handler(func=lambda message: message.text and message.text.isdigit())
def process_lookup(message):
    number = message.text.strip()

    if len(number) < 10:
        bot.reply_to(message, "⚠️ <b>Invalid Input:</b> Please enter a valid 10-digit number.")
        return

    # 1. Send immediate feedback so user knows it's working
    status = bot.send_message(message.chat.id, "<b>📡 Accessing Secure Database...</b>")

    try:
        # 2. Optimized Request (shorter timeout to prevent Telegram retries)
        # We use 5 seconds because Telegram retries after ~5-10 seconds of no response
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = session.get(f"{API_URL}{number}", headers=headers, timeout=5)
        
        if response.status_code == 200:
            try:
                data = response.json()
            except:
                bot.edit_message_text("⚠️ <b>API Error:</b> Invalid data received from server.", message.chat.id, status.message_id)
                return
            
            if "result" in data and data["result"]:
                final_response = ""
                # Limit to first 3 results to prevent message length errors (Telegram limit 4096 chars)
                records = data["result"][:3] 
                
                for index, record in enumerate(records, start=1):
                    name = str(record.get("name", "N/A")).title()
                    phone = record.get("mobile", "N/A")
                    alt_phone = record.get("alternate", "N/A") or "N/A"
                    father = str(record.get("father_name", "N/A")).title()
                    circle = record.get("circle", "N/A")
                    id_num = record.get("id", "N/A")
                    address = record.get("address", "N/A")

                    final_response += (
                        f"— Result {index} —\n"
                        f"👤 <b>Name:</b> <code>{name}</code>\n"
                        f"📞 <b>Phone:</b> <code>{phone}</code>\n"
                        f"📱 <b>Alt:</b> <code>{alt_phone}</code>\n"
                        f"👴 <b>Father:</b> <code>{father}</code>\n"
                        f"🔴 <b>Circle:</b> <code>{circle}</code>\n"
                        f"🆔 <b>ID:</b> <code>{id_num}</code>\n"
                        f"🏠 <b>Address:</b> <code>{address}</code>\n"
                        f"------------------------------\n\n"
                    )
                
                bot.delete_message(message.chat.id, status.message_id)
                bot.send_message(message.chat.id, final_response, reply_markup=result_buttons())
                
                # Async-like Admin Log (Optional: ignore errors here to prioritize user speed)
                try:
                    bot.send_message(ADMIN_ID, f"✅ <b>Search</b>\nNum: <code>{number}</code>\nUser: <code>{message.from_user.id}</code>")
                except: pass
            
            else:
                bot.edit_message_text("❌ <b>Data Not Found:</b> No records found.", message.chat.id, status.message_id)
        else:
            bot.edit_message_text("⚠️ <b>Server Busy:</b> Try again in a moment.", message.chat.id, status.message_id)

    except requests.exceptions.Timeout:
        bot.edit_message_text("⏳ <b>Timeout:</b> Server is taking too long. Try again.", message.chat.id, status.message_id)
    except Exception as e:
        print(f"Error: {e}")
        bot.edit_message_text("🚫 <b>System Error:</b> Please try later.", message.chat.id, status.message_id)

# --- VERCEL / FLASK HANDLER ---

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        
        # This is crucial for Vercel: process the update then return 200 OK
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    return "Bot is running", 200

# To handle cases where Telegram sends updates to the wrong path
@app.route('/webhook', methods=['POST'])
def webhook_legacy():
    return webhook()
