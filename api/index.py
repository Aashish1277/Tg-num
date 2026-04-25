import os
import requests
import telebot
from telebot import types
from flask import Flask, request

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 5714613336
API_KEY = "TVB_FULL_52F4672E"          # new API provider key
API_URL = f"https://techvishalboss.com/api/v1/lookup.php?key={API_KEY}&service=number&number="
CHANNEL_ID = "@TechTrovebyb44ner"
CHANNEL_URL = "https://t.me/TechTrovebyb44ner"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)
app = Flask(__name__)

session = requests.Session()

# --- HELPER FUNCTIONS ---

def check_sub(user_id):
    """Checks if the user is a member of the required channel."""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return True   # fallback to avoid lockout

# --- KEYBOARDS ---

def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔍 Start New Search", callback_data="start_search"))
    return markup

def force_join_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
    markup.add(types.InlineKeyboardButton("🔄 I Have Joined", callback_data="start_search"))
    return markup

def result_buttons():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔎 New Search", callback_data="start_search"),
        types.InlineKeyboardButton("🗑️ Clear Result", callback_data="delete_msg")
    )
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
        if not check_sub(call.from_user.id):
            bot.send_message(
                call.message.chat.id,
                f"⚠️ <b>Access Denied!</b>\n\nYou must join our channel to use this bot.",
                reply_markup=force_join_button()
            )
        else:
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
    # Force join check
    if not check_sub(message.from_user.id):
        bot.reply_to(
            message,
            "⚠️ <b>Access Denied!</b>\n\nPlease join the channel first to use the search feature.",
            reply_markup=force_join_button()
        )
        return

    number = message.text.strip()
    if len(number) < 10:
        bot.reply_to(message, "⚠️ <b>Invalid Input:</b> Please enter a valid 10-digit number.")
        return

    status = bot.send_message(message.chat.id, "<b>📡 Accessing Secure Database...</b>")

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = session.get(f"{API_URL}{number}", headers=headers, timeout=10)

        if response.status_code == 200:
            try:
                data = response.json()
            except:
                bot.edit_message_text("⚠️ <b>API Error:</b> The server returned an invalid response.",
                                      message.chat.id, status.message_id)
                return

            # Check new API status flag
            if not data.get("status"):
                bot.edit_message_text("❌ <b>Data Not Found:</b> No records found in our database.",
                                      message.chat.id, status.message_id)
                return

            results = data.get("results", {})
            if not results:
                bot.edit_message_text("❌ <b>Data Not Found:</b> No records found in our database.",
                                      message.chat.id, status.message_id)
                return

            final_response = ""
            # Limit to first 3 entries (just in case)
            for idx, (result_key, record) in enumerate(results.items()):
                if idx >= 3:
                    break

                name = str(record.get("name", "N/A")).title()
                phone = record.get("mobile", "N/A")
                alt_phone = record.get("alt_mobile", "N/A") or "N/A"
                father = str(record.get("father_name", "N/A")).title()
                email = record.get("email", "N/A")
                aadhar = record.get("aadhar_number", "N/A")
                operator = record.get("operator", "N/A")    # actually the circle name (e.g., MP)
                circle = record.get("state_circle", "N/A")  # network operator (e.g., AIRTEL)
                address = record.get("address", "N/A")

                final_response += (
                    f"— Result {idx+1} —\n"
                    f"👤 <b>Name:</b> <code>{name}</code>\n"
                    f"📞 <b>Phone:</b> <code>{phone}</code>\n"
                    f"📱 <b>Alt:</b> <code>{alt_phone}</code>\n"
                    f"👴 <b>Father:</b> <code>{father}</code>\n"
                    f"📧 <b>Email:</b> <code>{email}</code>\n"
                    f"🆔 <b>Aadhaar:</b> <code>{aadhar}</code>\n"
                    f"📡 <b>Operator:</b> <code>{circle}</code>\n"
                    f"📍 <b>Circle:</b> <code>{operator}</code>\n"
                    f"🏠 <b>Address:</b> <code>{address}</code>\n"
                    f"------------------------------\n\n"
                )

            bot.delete_message(message.chat.id, status.message_id)
            bot.send_message(message.chat.id, final_response, reply_markup=result_buttons())

            # Log to admin
            user = message.from_user
            username = f"@{user.username}" if user.username else "No Username"
            admin_log = (
                f"✅ <b>Search Successful</b>\n\n"
                f"🔢 <b>Number:</b> <code>{number}</code>\n"
                f"👤 <b>User:</b> {user.first_name}\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                f"🌐 <b>Username:</b> {username}"
            )
            try:
                bot.send_message(ADMIN_ID, admin_log)
            except:
                pass
        else:
            bot.edit_message_text("⚠️ <b>API Error:</b> Server busy or down.",
                                  message.chat.id, status.message_id)

    except requests.exceptions.Timeout:
        bot.edit_message_text("⏳ <b>Timeout:</b> Search took too long. Please try again.",
                              message.chat.id, status.message_id)
    except Exception as e:
        bot.edit_message_text("🚫 <b>System Error:</b> Please try again later.",
                              message.chat.id, status.message_id)

# --- VERCEL FLASK HANDLER ---

@app.route('/' + BOT_TOKEN if BOT_TOKEN else '/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    return "Bot is running perfectly.", 200

@app.route('/webhook', methods=['POST'])
def legacy_webhook():
    return webhook()

if __name__ == "__main__":
    app.run(debug=False)
