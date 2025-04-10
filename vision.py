from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import re
import logging

BOT_TOKEN = "7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s"
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Folder to save images
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)


def fetch_bank_data():
    # Replace with your actual API URL
    url = "http://127.0.0.1:8000/api/dropdown/list/bank"
    try:
        response = requests.post(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        if response.status_code == 200:
            data = response.json()  # Assuming the response is a list of dictionaries
            return data
        else:
            logger.error(
                f"Failed to fetch bank data. Status Code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching bank data: {e}")
        return []

# Generate BANK_OPTIONS dynamically from API data


def generate_bank_options(data):
    # Convert the fetched data into the required format for BANK_OPTIONS
    bank_options = [(item['bank_name'], str(item['code'])) for item in data]
    logger.info(f"Generated bank options: {bank_options}")
    return bank_options


# Fetch bank data and generate options dynamically
data = fetch_bank_data()
BANK_OPTIONS = generate_bank_options(data)
BANKS = {code: name for name, code in BANK_OPTIONS}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send a photo (Payslip) to continue.")

# Show bank options


async def show_bank_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=code)]
                for name, code in BANK_OPTIONS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("*Please choose a BANK*", reply_markup=reply_markup, parse_mode="Markdown")

# Photo handler triggers the options


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Save photo file info to context
    photo = update.message.photo[-1]
    file_id = photo.file_id
    context.user_data['photo_file_id'] = file_id  # Save file_id in context
    # Save full message in context
    context.user_data['message'] = update.message

    await show_bank_options(update, context)

# Handle bank button click


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    bank_code = query.data
    bank_name = BANKS.get(bank_code, "Unknown")

    # Process saved image
    if 'photo_file_id' in context.user_data and 'message' in context.user_data:
        # Save bank selection if needed
        context.user_data['bank_code'] = bank_code
        await calculate(context.user_data['message'], context)

        # Edit the original message to remove the inline keyboard and confirm the bank selection
        await query.edit_message_text(
            text=f"✅*{bank_name}*",
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text("❗ No image found to process.")


# ========================= Field Extractor =========================


def extract_fields_by_order(text):
    labels = [
        "Trx. ID", "From account", "Original amount",
        "Reference #",  "To account", "Transaction date"
        # "Trx. ID", "From account", "Original amount",
        # "Reference #", "Sender", "To account", "Transaction date"
    ]
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    label_indices = [i for i, line in enumerate(
        lines) if any(label in line for label in labels)]

    if not label_indices:
        return {"error": "Labels not found"}

    value_start_index = label_indices[-1] + 1
    values = lines[value_start_index:]

    field_data = {}
    field_values = []

    current_value = []
    for val in values:
        current_value.append(val)
        if len(field_values) < len(labels) - 1:
            field_values.append(' '.join(current_value).strip())
            current_value = []
    if current_value:
        field_values.append(' '.join(current_value).strip())

    for i, label in enumerate(labels):
        field_data[label] = field_values[i] if i < len(
            field_values) else "Not found"

    return field_data

# ========================= Photo Handler =========================


async def calculate(message, context: ContextTypes.DEFAULT_TYPE):
    # === Sender info ===
    sender = message.from_user
    username = sender.username or sender.first_name
    user_id = sender.id
    chat_id = message.chat.id

    # === Get and Save Photo ===
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{photo.file_id}.jpg"
    file_path = os.path.join(SAVE_FOLDER, filename)
    # await file.download_to_drive(file_path)
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
        response.raise_for_status()  # Raise an exception for HTTP errors
        full_text = response.json()['responses'][0].get(
            'textAnnotations', [{}])[0].get('description', '')
        logger.info(f"🧾 OCR Text:\n{full_text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error with Google Vision API: {e}")
        return

    # === Extract Fields ===
    extracted = extract_fields_by_order(full_text)

    message_text = '\n'.join([f"{key}: {extracted.get(key, 'Not found')}" for key in [
        "Trx. ID", "From account", "Original amount",
        "Reference #",  "To account", "Transaction date"
        #      "Trx. ID", "From account", "Original amount",
        # "Reference #", "Sender", "To account", "Transaction date"
    ]])

    # Respond to user
    print(f"====> {extracted.get('From account', '')}")

    response_message = f"{message_text}\n\n👤 From: {username}"
    await message.reply_text(response_message)

    # === Fetch and Process Price Data ===
    fetch_price_data(extracted.get("Original amount", ""), chat_id)

# ========================= Fetch Price Data =========================


def fetch_price_data(calculate_money, chat_id):
    url = "http://127.0.0.1:8000/api/calcuate/money/groups"
    params = {
        "calculate_money": calculate_money,
        "group_id": chat_id,
    }

    try:
        response = requests.post(url, params=params, json={})
        response.raise_for_status()
        data = response.json()
        amount = float(data.get("calculate_money", 0.0))
        count_slips = int(data.get("count_slips", 0))

        logger.info(f"Amount: {amount}")
        logger.info(f"Count Price: {count_slips}")

        return amount, count_slips

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data: {e}")
        return None, None

# ========================= Main =========================


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    main()
