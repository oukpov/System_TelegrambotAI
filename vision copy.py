from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import re
import logging
import hashlib
BOT_TOKEN = "7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s"
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Folder to save images
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)


def fetch_bank_data(chatID):
    print(f'Chat ID : {chatID}')
    url = "https://oukpov.store/gtkn_project/public/api/list/bank"
    try:
        response = requests.post(url)
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            logger.error(
                f"Failed to fetch bank data. Status Code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching bank data: {e}")
        return []


def calculateAmount(bank_id, bank_name, amount, name, currency, group_id, group_name):
    bank_id = int(bank_id)
    if bank_id == 1:
        url = "calculate/amount"
    else:
        url = "calculate/amount/thailand"
        print(f'======> ({bank_id}) : 2')

    params = {
        "bank_name": bank_name,
        "bank_id": bank_id,
        "amount": amount,
        "name": name,
        "currency": currency,
        "group_id": group_id,
        "group_name": group_name
    }

    try:
        response = requests.post(
            f"https://oukpov.store/gtkn_project/public/api/{url}", params=params, json={})
        response.raise_for_status()  # Raises HTTPError for bad responses
        labels_field = response.json()
        # print(f"====> {labels_field}")
        return labels_field  # Return actual data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def generate_bank_options(data):
    # Convert the fetched data into the required format for BANK_OPTIONS
    bank_options = [(item['bank_name'], str(item['bank_id'])) for item in data]
    logger.info(f"Generated bank options: {bank_options}")
    return bank_options


# Fetch bank data and generate options dynamically
data = None
BANK_OPTIONS = generate_bank_options(data)
BANKS = {code: name for name, code in BANK_OPTIONS}
# data = fetch_bank_data()
# BANK_OPTIONS = generate_bank_options(data)
# BANKS = {code: name for name, code in BANK_OPTIONS}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send a photo (Payslip) to continue.")

# Show bank options


async def show_bank_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=code)]
                for name, code in BANK_OPTIONS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("*Please choose a BANK*", reply_markup=reply_markup, parse_mode="Markdown")

# Photo handler triggers the options


processed_files = set()  # Define this globally at the top of your script


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    photo = message.photo[-1]
    file_unique_id = photo.file_unique_id

    # === Check if this image has already been processed
    if file_unique_id in processed_files:
        logger.info(f"⚠️ Image already processed: {file_unique_id}")
        await message.reply_text("⚠️ This Payslips has already been processed.")
        return

    # Otherwise, store info and continue
    context.user_data['photo_file_id'] = photo.file_id
    context.user_data['message'] = message

    await show_bank_options(update, context)  # Show the buttons


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    bank_code = query.data
    bank_name = BANKS.get(bank_code, "Unknown")

    # Check if message and photo exist
    if 'message' not in context.user_data or not context.user_data['message'].photo:
        await query.message.reply_text("❗ No image found to process.")
        return

    message = context.user_data['message']
    photo = message.photo[-1]  # Highest resolution
    print(f'message : {message.chat.id}')
    data = fetch_bank_data(message.chat.id)
    # Check for duplicate processing
    if photo.file_unique_id in processed_files:
        logger.info(
            f"⚠️ OCR already extracted for this image: {photo.file_unique_id}")
        await query.edit_message_text(
            text="⚠️ This PlaySlips has already been processed.",
            parse_mode="Markdown"
        )
        return
    else:
        processed_files.add(photo.file_unique_id)

    # Confirm bank selection
    await query.edit_message_text(
        text=f"✅ *{bank_name}*",
        parse_mode="Markdown"
    )

    # Save selected bank
    context.user_data['bank_code'] = bank_code
    context.user_data['bank_name'] = bank_name

    # Call calculate function
    await calculate(message, context, bank_code, bank_name)


# ========================= Field Extractor =========================

def extract_field_thai(text, bank_name, bank_id, groupID, groupName):
    matches = re.findall(r'\b\d+\.\d{2}\b', text)

    # Convert appropriately
    def convert_amount(value):
        num = float(value)
        if num == 0:
            return None
        return int(num) if num.is_integer() else num

    # Get the first valid amount
    amount = next((convert_amount(m)
                  for m in matches if convert_amount(m) is not None), None)
    # print(amount)
    calculateAmount(bank_id, bank_name, amount,
                    "None", 'bat', groupID, groupName)


def extract_fields_Khmer(text, bank_name, bank_id, groupID, groupName):
    amount_pattern = r'-?[\d,]+\.\d{2}\s*(KHR|USD)'
    amount_match = re.search(amount_pattern, text)

    # Regex to find named transfer line
    named_line_pattern = r'^(?:Transfer to|Received from)\s+(.+)$'

    # Init
    name = None

    if amount_match:
        amount_full = amount_match.group()
        amount_clean = amount_full.replace(',', '')
        currency = amount_match.group(1).lower()
        # print(f"✅ ==> First amount: {amount_clean}")
        # print(f"✅ ==> Currency: {currency}")

        # Try to find "Transfer to" or "Received from"
        named_match = re.search(named_line_pattern, text, re.MULTILINE)
        if named_match:
            name = named_match.group(1).strip()
        else:
            # Fallback: get the line after the amount
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if amount_full in line:
                    # Check next non-empty line
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if next_line:
                            name = next_line
                            break
                    break
        calculateAmount(bank_id, bank_name,  amount_clean,
                        name, currency, groupID, groupName)
        if name:
            print(f"✅ ==> Name only: {name}")
        else:
            print("❌ No name found.")
    else:
        print("❌ No valid amount found.")

# ========================= Photo Handler =========================


processed_files = set()


async def calculate(message, context: ContextTypes.DEFAULT_TYPE, bank_id, bank_name):
    # === Sender info ===
    sender = message.from_user
    username = sender.username or sender.first_name
    user_id = sender.id
    chat_id = message.chat.id
    groupname = message.chat.title
    bankID = int(bank_id)

    # === Get and Save Photo ===
    photo = message.photo[-1]  # Highest resolution
    file = await context.bot.get_file(photo.file_id)
    filename = f"{photo.file_unique_id}.jpg"
    file_path = os.path.join(SAVE_FOLDER, filename)
    await file.download_to_drive(file_path)
    logger.info(f"📸 Photo saved to: {file_path}")

    # === Encode image to base64 ===
    with open(file_path, 'rb') as image_file:
        content = base64.b64encode(image_file.read()).decode('utf-8')

    # === Google Vision API Call ===
    endpoint_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    body = {
        "requests": [{
            "image": {"content": content},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }
    try:
        response = requests.post(endpoint_url, headers=headers, json=body)
        response.raise_for_status()
        full_text = response.json()['responses'][0].get(
            'textAnnotations', [{}])[0].get('description', '')

        logger.info(f"🧾 OCR Text:\n{full_text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error with Google Vision API: {e}")
        return

    # === Field Extraction ===
    if bankID == 1:
        extract_fields_Khmer(full_text, bank_name, bank_id, chat_id, groupname)
    else:
        extract_field_thai(full_text, bank_name, bank_id, chat_id, groupname)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(button_handler))  # keep this

    logger.info("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    main()
