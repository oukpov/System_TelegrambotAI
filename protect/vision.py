from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os
import requests
import base64

# Telegram bot token
BOT_TOKEN = "7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s"

# Google Vision API key
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"

# Folder to save images
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# ========================= OCR Field Extraction =========================


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


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    filename = f"{photo.file_id}.jpg"
    file_path = os.path.join(SAVE_FOLDER, filename)
    await file.download_to_drive(file_path)

    print(f"📸 Photo saved to: {file_path}")

    # STEP 1: Encode image to base64
    with open(file_path, 'rb') as image_file:
        content = base64.b64encode(image_file.read()).decode('utf-8')

    # STEP 2: Call Google Vision API
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

    # STEP 3: Extract fields
    extracted = extract_fields_by_order(full_text)
    print("\n🧾 Extracted Fields:")
    for key in [
        "Trx. ID", "From account", "Original amount",
        "Reference #", "Sender", "To account", "Transaction date"
    ]:
        print(f"{key} : {extracted.get(key, 'Not found')}")

    # Reply with extracted fields
    message = '\n'.join(
        [f"{key}: {extracted.get(key, 'Not found')}" for key in extracted])
    await update.message.reply_text("✅ Extracted Data:\n" + message)

# ========================= Main =========================


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    print("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    main()
