import os
import base64
import requests
import threading
from flask import Flask, send_from_directory
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuration from environment (Railway-style)
API_KEY = os.getenv('AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA')
TELEGRAM_BOT_TOKEN = os.getenv(
    '7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s')
BASE_URL = os.getenv(
    'BASE_URL', 'https://gtkn.up.railway.app')  # <-- update this
SAVE_FOLDER = 'static/images'

# Create save folder if it doesn't exist
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Flask app for image hosting
flask_app = Flask(__name__)


@flask_app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(SAVE_FOLDER, filename)

# Telegram photo handler


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_list = update.message.photo
    for index, photo in enumerate(photo_list):
        file = await context.bot.get_file(photo.file_id)
        filename = f"{photo.file_unique_id}.jpg"
        file_path = os.path.join(SAVE_FOLDER, filename)
        await file.download_to_drive(file_path)

        # Generate image URL
        image_url = f"{BASE_URL}/images/{filename}"

        # ✅ Print to logs
        print(f"✅ Image URL saved: {image_url}")

        # ✅ Send image preview
        await update.message.reply_photo(photo=image_url)

        # Encode image to base64
        with open(file_path, 'rb') as image_file:
            content = base64.b64encode(image_file.read()).decode('utf-8')

        # Send to Google Vision
        response = requests.post(
            f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}",
            headers={'Content-Type': 'application/json'},
            json={
                "requests": [{
                    "image": {"content": content},
                    "features": [{"type": "TEXT_DETECTION"}]
                }]
            }
        )

        result = response.json()
        text = result['responses'][0].get(
            'fullTextAnnotation', {}).get('text', 'No text found.')

        # Send message with OCR result
        await update.message.reply_text(f"✅ Image saved:\n{image_url}\n\n📝 OCR Result:\n{text}")

# Telegram bot runner


def run_telegram_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

# Main runner


def main():
    port = int(os.environ.get("PORT", 3000))  # Railway sets PORT
    threading.Thread(target=lambda: flask_app.run(
        host='0.0.0.0', port=port, debug=False, use_reloader=False)).start()

    run_telegram_bot()


if __name__ == '__main__':
    main()
