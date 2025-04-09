from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os
import requests
import base64

# ========================= Config =========================

# Telegram bot token
BOT_TOKEN = "7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s"

# Google Vision API key
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"

# Folder to save images
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

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


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # === Sender info ===
    sender = message.from_user
    username = sender.username or sender.first_name
    user_id = sender.id
    chat_id = update.message.chat.id

    # === Chat info ===
    chat = message.chat
    chat_type = chat.type  # 'private', 'group', 'supergroup', or 'channel'
    group_title = chat.title if chat_type in ['group', 'supergroup'] else None
    group_id = chat.id

    print(f"👤 User: {username} ({user_id})")
    print(f"👤 chat_id: {chat_id})")
    print(f"💬 Chat type: {chat_type}")
    if group_title:
        print(f"👥 Group name: {group_title} (ID: {group_id})")

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

    # === Format result message ===
    message_text = '\n'.join([f"{key}: {extracted.get(key, 'Not found')}" for key in [
        "Trx. ID", "From account", "Original amount",
        "Reference #", "Sender", "To account", "Transaction date"
    ]])

    response_message = f"✅ Extracted Data:\n{message_text}\n\n👤 From: {username}\n💬 Chat type: {chat_type}"
    if group_title:
        response_message += f"\n👥 Group: {group_title}"

    # === Reply to User ===
    await message.reply_text(response_message)

# ========================= Main =========================


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    print("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    main()
