import os
import base64
import requests
from flask import Flask, send_from_directory
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import threading

# Configuration
# Ensure you set this in Railway environment variables
API_KEY = os.getenv('AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA')
# Set this in Railway as well
TELEGRAM_BOT_TOKEN = os.getenv(
    '7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s')
BASE_URL = os.getenv(
    'BASE_URL', 'https://gtkn.up.railway.app')  # Railway domain
SAVE_FOLDER = 'static/images'

# Ensure save folder exists
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Flask app to serve images
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
        print(f"Image URL: {image_url}")

        # Encode image to base64 for Google Vision API
        with open(file_path, 'rb') as image_file:
            content = base64.b64encode(image_file.read()).decode('utf-8')

        # Send to Vision API
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

        # Reply to user with image URL and OCR text
        await update.message.reply_text(f"✅ Image saved:\n{image_url}\n\n📝 OCR Result:\n{text}")

# Telegram bot setup


def run_telegram_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

# Main runner


def main():
    port = int(os.environ.get("PORT", 3000))  # Railway sets PORT
    # Start Flask and Telegram bot together
    threading.Thread(target=lambda: flask_app.run(
        host='0.0.0.0', port=port, debug=False, use_reloader=False)).start()

    # Start Telegram bot
    run_telegram_bot()


if __name__ == '__main__':
    main()
