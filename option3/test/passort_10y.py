from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import logging
import re

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
    await update.message.reply_text("👋 Please send a photo to continue.")

# ========================= Handler: Photo Upload =========================


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_webhook()
    message = update.message

    if not message.photo:
        await message.reply_text("❌ No photo found in the message.")
        return

    photo = message.photo[-1]
    file_unique_id = photo.file_unique_id

    if file_unique_id in processed_files:
        logger.info(f"⚠️ Image already processed: {file_unique_id}")
        await message.reply_text("⚠️ This image has already been processed.")
        return

    context.user_data['message'] = message
    processed_files.add(file_unique_id)
    await checkFile(message, context)

# ========================= OCR and Processing =========================


async def checkFile(message, context: ContextTypes.DEFAULT_TYPE):
    chat_id = message.chat.id
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{photo.file_unique_id}.jpg"
    file_path = os.path.join(SAVE_FOLDER, filename)
    await file.download_to_drive(file_path)

    with open(file_path, 'rb') as image_file:
        content = base64.b64encode(image_file.read()).decode('utf-8')

    endpoint_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    body = {
        "requests": [{
            "image": {"content": content},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }

    response = requests.post(endpoint_url, headers=headers, json=body)
    response.raise_for_status()
    full_text = response.json()['responses'][0].get(
        'textAnnotations', [{}])[0].get('description', '')
    lines = full_text.strip().split('\n')

    def extract_field(pattern, fallback="N/A"):
        match = re.search(pattern, full_text, re.IGNORECASE)
        return match.group(1).strip() if match else fallback

    # Extract passport number prioritizing T-prefixed, fallback to regular
    travel_doc_match = re.search(r'T\d{7}', full_text)
    if travel_doc_match:
        passport_no = travel_doc_match.group(0)
        print(f'============> No.1 : {passport_no}')
    else:
        passport_no = extract_field(
            r'(?:លេខលិខិតឆ្លងដែន\s*/\s*Passport No\.?|Passport No\.?)[:\s]*([A-Z0-9]+)')
        print(f'============> No.2 : {passport_no}')

    # Allow surname extraction from Khmer and English label variants
    surname_pattern = r'(?:នាមត្រកូល\s*/\s*Sarname|នាមត្រកូល)[:\s\-]*([A-Z ]+)'
    surname = extract_field(surname_pattern)

    # Handle Given Names with variants including slash
    given_pattern = r'(?:Sugs/Given names|mugs/Given names|Given names)[:\s\-]*([A-Z ]+)'
    given_name = extract_field(given_pattern)

    nationality = extract_field(r'Nationality[:\s]*([A-Z ]+)')
    dob = extract_field(r'Date of birth[:\s]*([0-9]{2} \w{3} \d{4})')
    doi = extract_field(r'Date of issue[:\s]*([0-9]{2} \w{3} \d{4})')
    doe = extract_field(r'Date of expiry[:\s]*([0-9]{2} \w{3} \d{4})')
    place_of_birth = extract_field(r'Place of birth[:\s]*([A-Z ]+)')

    gender = next((line.strip()
                  for line in lines if line.strip() in ['M', 'F']), "N/A")
    height_match = re.search(r'(\d{2,3})\s?CM', full_text.upper())
    height = height_match.group(1) + " CM" if height_match else "N/A"

    mrz_1 = lines[-2] if len(lines) >= 2 else "N/A"
    mrz_2 = lines[-1] if len(lines) >= 1 else "N/A"

    khmer_name = extract_field(
        r'ឈ្មោះជាភាសាខ្មែរ[:\s]*Name ih Khmer[:\s]*(.*)')
    profession = extract_field(r'មុខរបរ[:\s]*Profession[:\s]*(.*)')

    response_text = (
        "✅ Done\n"
        f"🆔 No Card  :  {passport_no}\n"
        f"👤 Name  :   {surname},{given_name}\n"
        f"🚻 Gender  :  {gender}\n"
        f"📏 Height  :  {height}\n"
        f"🎂 Date of Birth : {dob}\n"
        f"🗓️ Date of Issue : {doi}\n"
        f"⌛️ Date of Expiry : {doe}\n"
        f"📍 Place of Birth : {place_of_birth}\n"
        f"🛂 MRZ\n{mrz_1}\n{mrz_2}"
    )

    if khmer_name != "N/A" and profession != "N/A":
        response_text += f"\n\nឈ្មោះជាភាសាខ្មែរ: {khmer_name}\nមុខរបរ: {profession}"

    await context.bot.send_message(chat_id=chat_id, text=response_text)

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

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot is running... Send a photo!")
    app.run_polling()
