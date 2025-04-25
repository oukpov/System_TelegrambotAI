from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import logging

# ========================= Configuration =========================

BOT_TOKEN = "7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s"
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"

# ========================= Logging Setup =========================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================= Folder Setup =========================

SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Track processed images to avoid reprocessing
processed_files = set()


# ========================= Webhook Cleanup =========================

def delete_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logger.info("Webhook deleted successfully.")
        else:
            logger.warning(f"Failed to delete webhook: {response.text}")
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Exception while deleting webhook: {e}")
        return None


# ========================= Command: /start =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Please send a photo (Payslip) to continue.")


# ========================= Handler: Photo Upload =========================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_webhook()
    message = update.message

    if not message.photo:
        await message.reply_text("❌ No photo found in the message.")
        return

    photo = message.photo[-1]
    file_unique_id = photo.file_unique_id

    # Check if image already processed
    if file_unique_id in processed_files:
        logger.info(f"⚠️ Image already processed: {file_unique_id}")
        await message.reply_text("⚠️ This payslip has already been processed.")
        return

    # Store image info
    context.user_data['photo_file_id'] = photo.file_id
    context.user_data['message'] = message
    processed_files.add(file_unique_id)

    # Continue to processing
    await checkFile(message, context)


# ========================= OCR and Processing =========================

async def checkFile(message, context: ContextTypes.DEFAULT_TYPE):
    sender = message.from_user
    username = sender.username or sender.first_name
    user_id = sender.id
    chat_id = message.chat.id

    # Get highest quality image
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{photo.file_unique_id}.jpg"
    file_path = os.path.join(SAVE_FOLDER, filename)
    await file.download_to_drive(file_path)
    logger.info(f"📸 Photo saved to: {file_path}")

    # Encode image as base64
    with open(file_path, 'rb') as image_file:
        content = base64.b64encode(image_file.read()).decode('utf-8')

    # Send to Google Vision
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
        await message.reply_text(f"🧾 Extracted Text:\n{full_text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error with Google Vision API: {e}")
        await message.reply_text("❌ Failed to extract text from the image.")


# ========================= (Optional) Button Handler =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'message' not in context.user_data or not context.user_data['message'].photo:
        await query.message.reply_text("❗ No image found to process.")
        return

    message = context.user_data['message']
    await checkFile(message, context)


# ========================= Main Entry =========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    # Optional if using buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    main()
