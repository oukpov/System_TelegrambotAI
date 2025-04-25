from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import logging
import re
from datetime import datetime
from telegram.ext import ContextTypes
import unicodedata
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


def convert_date(date_str):
    try:
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def information(
    first_name,
    last_name,
    card_id,
    date_of_birth,
    date_of_issue,
    date_of_expirey,
    hieght,
    place_of_birth,
    group_id,
    group_name,
    gender,
    underline,
):

    url = "https://oukpov.store/gtkn_project/public/api/optin3/add/data"

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "card_id": card_id,
        "date_of_birth": date_of_birth,
        "date_of_issue": date_of_issue,
        "date_of_expirey": date_of_expirey,
        "hieght": hieght,
        "place_of_birth": place_of_birth,
        "group_id": group_id,
        "group_name": group_name,
        "gender": gender,
        "underline": underline
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raises exception for 4xx/5xx errors
        print("✅ Success:", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        print("❌ Request failed:", e)
        if e.response is not None:
            print("Response content:", e.response.text)
        return None


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
    # if file_unique_id in processed_files:
    #     logger.info(f"⚠️ Image already processed: {file_unique_id}")
    #     await message.reply_text("⚠️ This payslip has already been processed.")
    #     return

    # Store image info
    context.user_data['photo_file_id'] = photo.file_id
    context.user_data['message'] = message
    processed_files.add(file_unique_id)

    # Continue to processing
    await checkFile(message, context)


def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except:
        return date_str


async def checkFile(message, context: ContextTypes.DEFAULT_TYPE):
    sender = message.from_user
    chat_id = message.chat.id
    groupname = message.chat.title

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

    try:
        response = requests.post(endpoint_url, headers=headers, json=body)
        response.raise_for_status()
        full_text = response.json()['responses'][0].get(
            'textAnnotations', [{}])[0].get('description', '')
        lines = full_text.strip().split('\n')
        logger.info(f"🧾 OCR Text:\n{full_text}")

        def extract_surname(lines, full_text):
            for i, line in enumerate(lines):
                if "នាមត្រកូល/Surname" in line:
                    match = re.search(r'Surname[:\s\-]*([A-Z ]{2,})', line)
                    if match:
                        return match.group(1).strip()
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if re.match(r'^[A-Z ]+$', next_line):
                            return next_line
            match = re.search(r'Surname[:\s\-]*([A-Z ]{2,})', full_text)
            if match:
                return match.group(1).strip()
            return ""

        def extract_given_name(lines, full_text, surname=None):
            variants = ['Given names', 'Sugs/Given names',
                        'នាមខ្លួន/Given names', 'Given name']
            for i, line in enumerate(lines):
                for variant in variants:
                    if variant.lower() in line.lower():
                        match = re.search(
                            rf'{variant}[:\s\/-]*([A-Z ]+)', line, re.IGNORECASE)
                        if match:
                            return match.group(1).strip()
                        if i + 1 < len(lines) and re.match(r'^[A-Z ]+$', lines[i + 1].strip()):
                            return lines[i + 1].strip()
            for l in lines:
                if "<<" in l and len(l) > 30:
                    parts = l.split("<<")
                    if len(parts) > 1:
                        return parts[1].replace("<", " ").strip()
            return ""

        def extract_place_of_birth(lines, full_text):
            keywords = [
                r'ទីកន្លែងកំណើត\s*/\s*Place of birth',
                r'Place of birth\s*/\s*ទីកន្លែងកំណើត',
                r'Place of birth\|ទីកន្លែងកំណើត',
                r'Place of birth',
                r'ទីកន្លែងកំណើត'
            ]
            for i, line in enumerate(lines):
                for keyword in keywords:
                    if re.search(keyword, line, re.IGNORECASE):
                        for j in range(i + 1, min(i + 4, len(lines))):
                            candidate = lines[j].strip().upper()
                            if candidate not in ['F', 'M'] and len(candidate) >= 5:
                                if re.match(r'^[A-ZÀ-ÿ ]+$', candidate):
                                    return candidate
            for pattern in keywords:
                match = re.search(
                    pattern + r'[:\s\-\/]{0,10}([A-ZÀ-ÿ ]{5,})', full_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return "N/A"

        def extract_gender(lines):
            for line in lines:
                if line.strip() in ['F', 'M']:
                    return line.strip()
            return ""

        surname = extract_surname(lines, full_text)
        given_name = extract_given_name(lines, full_text, surname=surname)
        place_of_birth = extract_place_of_birth(lines, full_text)
        gender = extract_gender(lines)

        height_match = re.search(r'(\d{2,3})\s?CM', full_text.upper())
        height = height_match.group(1) + " CM" if height_match else "N/A"

        dob_match = re.search(
            r'Date of birth\s*([0-9]{2} \w{3} \d{4})', full_text)
        doi_match = re.search(
            r'Date of issue\s*([0-9]{2} \w{3} \d{4})', full_text)
        doe_match = re.search(
            r'Date of expiry\s*([0-9]{2} \w{3} \d{4})', full_text)

        dob = format_date(dob_match.group(1)) if dob_match else "N/A"
        doi = format_date(doi_match.group(1)) if doi_match else "N/A"
        doe = format_date(doe_match.group(1)) if doe_match else "N/A"

        travel_doc_match = re.search(r'T\d{7}', full_text)
        travel_doc_no = travel_doc_match.group(
            0) if travel_doc_match else "N/A"

        mrz_1 = lines[-2] if len(lines) >= 2 else "N/A"
        mrz_2 = lines[-1] if len(lines) >= 1 else "N/A"

        # extracted = [
        #     f"Height: {height}",
        #     f"Surname: {surname}",
        #     f"Given Name: {given_name}",
        #     f"DOB: {dob}",
        #     f"DOI: {doi}",
        #     f"DOE: {doe}",
        #     f"Travel Doc: {travel_doc_no}",
        #     f"Place of Birth: {place_of_birth}",
        #     f"Gender: {gender}",
        #     f"MRZ1: {mrz_1}",
        #     f"MRZ2: {mrz_2}"
        # ]
        # await message.reply_text("📌 Extracted Info:\n" + "\n".join(extracted))

        # print(
        #     f'first_name : {surname}\n'
        #     f'last_name : {given_name}\n'
        #     f'card_id : {travel_doc_no}\n'
        #     f'date_of_birth : {dob}\n'
        #     f'date_of_issue : {doi}\n'
        #     f'date_of_expirey : {doe}\n'
        #     f'hieght : {height}\n'
        #     f'place_of_birth : {place_of_birth}\n'
        #     f'gender : {gender}\n'
        #     f'group_id : {chat_id}\n'
        #     f'group_name : {groupname}\n'
        # )
        information(
            surname, given_name, travel_doc_no, dob, doi, doe, height, place_of_birth, chat_id, groupname, gender, mrz_1 + mrz_2
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error with Google Vision API: {e}")
        await message.reply_text("❌ Failed to extract text from the image.")


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
