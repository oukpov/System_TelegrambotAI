from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import re

BOT_TOKEN = "TOKEN"
API_KEY = "KEY"

BOT_TOKEN = "7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s"
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"
# Bank list (name, code)
BANK_OPTIONS = [
    ("ABA Bank", "1"),
    ("Sathapana Bank", "2"),
    ("Bride Bank", "3"),
    ("Wing Bank", "4"),
]
BANKS = {code: name for name, code in BANK_OPTIONS}

# Folder to save images
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send a photo (Payslip) to continue.")

# Show bank options


async def show_bank_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=code)]
                for name, code in BANK_OPTIONS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("*Please choose a BANK*", reply_markup=reply_markup,  parse_mode="Markdown")

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

    # await query.edit_message_text(
    #     text=f"🏦 *{bank_name}*\nPlease wait while we process your Payslip...",
    #     parse_mode="Markdown"
    # )

    # Process saved image
    if 'photo_file_id' in context.user_data and 'message' in context.user_data:
        # Save bank selection if needed
        context.user_data['bank_code'] = bank_code
        await calculate(context.user_data['message'], context)
    else:
        await query.message.reply_text("❗ No image found to process.")

# ========================= Field Extractor =========================


def extract_fields_by_order(text):
    labels = [
        "Trx. ID", "From account", "Original amount",
        "Reference #", "Sender", "To account", "Transaction date"
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

    # === Chat info ===
    chat = message.chat
    chat_type = chat.type  # 'private', 'group', 'supergroup', or 'channel'
    group_title = chat.title if chat_type in ['group', 'supergroup'] else None
    group_id = chat.id

    # === Get and Save Photo ===
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{photo.file_id}.jpg"
    file_path = os.path.join(SAVE_FOLDER, filename)
    await file.download_to_drive(file_path)
    print(f"📸 Photo saved to: {file_path}")

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

    response = requests.post(endpoint_url, headers=headers, json=body)
    full_text = response.json()['responses'][0].get(
        'textAnnotations', [{}])[0].get('description', '')

    print("\n🧾 OCR Text:\n", full_text)

    # === Extract Fields ===
    extracted = extract_fields_by_order(full_text)

    message_text = '\n'.join([f"{key}: {extracted.get(key, 'Not found')}" for key in [
        "Trx. ID", "From account", "Original amount",
        "Reference #", "Sender", "To account", "Transaction date"
    ]])
    raw_amount = extracted.get("Original amount", "")

    # Remove any currency prefix (USD, usd, U.S.D., etc.) and any commas or extra whitespace
    amount = re.sub(r'(?i)\bUSD\b[\s:]*', '',
                    raw_amount).replace(',', '').strip()

    # print(f'Amount: {amount}')

    # Respond to user
    response_message = f"✅ Extracted Data:\n{message_text}\n\n👤 From: {username}\n💬 Chat type: {chat_type}"
    if group_title:
        response_message += f"\n👥 Group: {group_title}"

    # === Reply to User ===
    await message.reply_text(response_message)
    # You can call your API here to save data or process further
    fetch_price_data(amount, chat_id)

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

        # Print or return values
        print("Amount:", amount)
        print("Count Price:", count_slips)

        return amount, count_slips

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None, None, None, None

# ========================= Main =========================


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    main()
