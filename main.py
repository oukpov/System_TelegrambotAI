import os
import base64
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuration
API_KEY = os.getenv('AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA')
# Set this in Railway as well
TELEGRAM_BOT_TOKEN = os.getenv(
    '7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s')
BASE_URL = os.getenv(
    'BASE_URL', 'https://gtkn.up.railway.app')  # Railway domain
SAVE_FOLDER = 'static/images'

# Ensure save folder exists
os.makedirs(SAVE_FOLDER, exist_ok=True)

# FastAPI app
app = FastAPI()
PORT = os.getenv("PORT", 5000)  # Default to 5000 if PORT is not set


@app.get("/images/{filename}")
async def serve_image(filename: str):
    return FileResponse(os.path.join(SAVE_FOLDER, filename))


# Telegram photo handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Log the photo information
    print(f"Received photo: {update.message.photo}")
    photo_list = update.message.photo
    for index, photo in enumerate(photo_list):
        print(f"Processing photo {index}: {photo.file_id}")

        # Get the file from Telegram
        file = await context.bot.get_file(photo.file_id)
        filename = f"{photo.file_unique_id}.jpg"
        file_path = os.path.join(SAVE_FOLDER, filename)

        # Download the photo
        await file.download_to_drive(file_path)
        print(f"Image saved at {file_path}")

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
    print(f"Starting Telegram bot with token: {TELEGRAM_BOT_TOKEN}")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()


# Main runner
def main():
    # Ensure PORT is an integer
    port = int(PORT)  # Convert the PORT to an integer
    print(f"Starting FastAPI server on port {port}")

    # Start FastAPI with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)

    # Start Telegram bot (Note: This may need to be run in a separate thread or process)
    run_telegram_bot()


if __name__ == '__main__':
    main()
