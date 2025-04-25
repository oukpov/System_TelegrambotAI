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
import random
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
    no

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
        "underline": underline,
        "no": no
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Success:", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        print("❌ Request failed:", e)
        if e.response is not None:
            print("Response content:", e.response.text)
        return None


def labor_Conference(
    code_id,
    group_id,
    account_name,
    account_type,
    account_no,

):
    url = "https://oukpov.store/gtkn_project/public/api/add/Labor/conference"
    payload = {
        "card_ID": code_id,
        "group_id": group_id,
        "account_name": account_name,
        "account_type": account_type,
        "account_no": account_no,

    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
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

    if 'photo_list' not in context.user_data:
        context.user_data['photo_list'] = []

    if len(context.user_data['photo_list']) >= 3:
        await message.reply_text("⚠️ You can only upload up to 3 images.")
        return

    photo = message.photo[-1]
    file_unique_id = photo.file_unique_id

    # if file_unique_id in processed_files:
    #     await message.reply_text("⚠️ This image has already been uploaded.")
    #     return

    context.user_data['photo_list'].append(photo)
    processed_files.add(file_unique_id)

    if len(context.user_data['photo_list']) == 3:
        await process_images_by_index(context, message, context.user_data['photo_list'])
        context.user_data['photo_list'] = []


async def process_images_by_index(context, message, photo_list):
    for index, photo in enumerate(photo_list):
        file = await context.bot.get_file(photo.file_id)
        filename = f"{photo.file_unique_id}.jpg"
        file_path = os.path.join(SAVE_FOLDER, filename)
        await file.download_to_drive(file_path)

        with open(file_path, 'rb') as image_file:
            content = base64.b64encode(image_file.read()).decode('utf-8')

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
        full_text = result['responses'][0].get(
            'fullTextAnnotation', {}).get('text', '')

        def extract_field(pattern, fallback="N/A"):
            match = re.search(pattern, full_text, re.IGNORECASE)
            return match.group(1).strip() if match else fallback
        travel_doc_match = re.search(r'T\d{7}', full_text)
        match index:
            case 0:
                label = "Front"
                if travel_doc_match:
                    passport_no = travel_doc_match.group(0)
                    print(f'============> No.1 : {passport_no}')
                    await passort_method(message, full_text, context)
                else:
                    passport_no = extract_field(
                        r'(?:លេខលិខិតឆ្លងដែន\s*/\s*Passport No\.?|Passport No\.?)[:\s]*([A-Z0-9]+)')
                print(f'============> No.2 : {passport_no}')
                await passort_methodNo(message, full_text, context)
            case 1:
                # label = "Back"
                await labor_conference_Image(message, full_text, context, passport_no)
            case 2:
                label = "Extra"
            case _:
                label = f"Image {index + 1}"
        os.remove(file_path)


async def passort_method(message, full_text, context: ContextTypes.DEFAULT_TYPE):
    sender = message.from_user
    chat_id = message.chat.id
    groupname = message.chat.title

    lines = full_text.strip().split('\n')
    logger.info(f"📜 OCR Text:\n{full_text}")

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
                    'នាមខុល/Given names', 'Given name']
        for i, line in enumerate(lines):
            for variant in variants:
                if variant.lower() in line.lower():
                    match = re.search(
                        rf'{variant}[:\s\/\-]*([A-Z ]+)', line, re.IGNORECASE)
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
            r'ទិកៅនូលកង់ងងាត\s*/\s*Place of birth',
            r'Place of birth\s*/\s*ទិកៅនូលកង់ងងាត',
            r'Place of birth\|.*',
            r'Place of birth',
            r'ទិកៅនូលកង់ងងាត'
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

    dob_match = re.search(r'Date of birth\s*([0-9]{2} \w{3} \d{4})', full_text)
    doi_match = re.search(r'Date of issue\s*([0-9]{2} \w{3} \d{4})', full_text)
    doe_match = re.search(
        r'Date of expiry\s*([0-9]{2} \w{3} \d{4})', full_text)

    dob = format_date(dob_match.group(1)) if dob_match else "N/A"
    doi = format_date(doi_match.group(1)) if doi_match else "N/A"
    doe = format_date(doe_match.group(1)) if doe_match else "N/A"

    travel_doc_match = re.search(r'T\d{7}', full_text)
    travel_doc_no = travel_doc_match.group(0) if travel_doc_match else "N/A"

    mrz_1 = lines[-2] if len(lines) >= 2 else "N/A"
    mrz_2 = lines[-1] if len(lines) >= 1 else "N/A"

    information(
        surname, given_name, travel_doc_no, dob, doi, doe,
        height, place_of_birth, chat_id, groupname, gender, mrz_1 + mrz_2, 1
    )


async def passort_methodNo(message, full_text, context: ContextTypes.DEFAULT_TYPE):
    chat_id = message.chat.id
    groupname = message.chat.title
    lines = full_text.strip().split('\n')
    logger.info(f"📜 OCR Text []:\n{full_text}")

    def extract_field(pattern, fallback="N/A"):
        match = re.search(pattern, full_text, re.IGNORECASE)
        return match.group(1).strip() if match else fallback

    def format_date(date_str):
        try:
            return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
        except Exception:
            return date_str  # fallback to original if format fails

    surname = extract_field(
        r'(?:នាមត្រកូល\s*/\s*Sarname|នាមត្រកូល)[:\s\-]*([A-Z ]+)')
    given_name = extract_field(
        r'(?:Sugs/Given names|mugs/Given names|Given names)[:\s\-]*([A-Z ]+)')

    passport_no = extract_field(
        r'(?:លេខលិខិតឆ្លងដែន\s*/\s*Passport No\.?|Passport No\.?)[:\s]*([A-Z0-9]+)')
    nationality = extract_field(r'Nationality[:\s]*([A-Z ]+)')

    dob_raw = extract_field(r'Date of birth[:\s]*([0-9]{2} \w{3} \d{4})')
    dob = format_date(dob_raw)

    doi_raw = extract_field(r'Date of issue[:\s]*([0-9]{2} \w{3} \d{4})')
    doi = format_date(doi_raw)

    doe_raw = extract_field(r'Date of expiry[:\s]*([0-9]{2} \w{3} \d{4})')
    doe = format_date(doe_raw)

    place_of_birth = extract_field(r'Place of birth[:\s]*([A-Z ]+)')

    gender = next((line.strip()
                  for line in lines if line.strip() in ['M', 'F']), "N/A")
    height_match = re.search(r'(\d{2,3})\s?CM', full_text.upper())
    height = height_match.group(1) + " CM" if height_match else "N/A"

    mrz_1 = lines[-2] if len(lines) >= 2 else "N/A"
    mrz_2 = lines[-1] if len(lines) >= 1 else "N/A"

    # khmer_name = extract_field(
    #     r'ឈ្មោះជាភាសាខ្មែរ[:\s]*Name ih Khmer[:\s]*(.*)')
    # profession = extract_field(r'មុខរបរ[:\s]*Profession[:\s]*(.*)')
    information(
        surname, given_name, passport_no, dob, doi, doe,
        height, place_of_birth, chat_id, groupname, gender, mrz_1 + mrz_2, 2
    )
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
    await context.bot.send_message(chat_id=chat_id, text=response_text)


def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except:
        return date_str


async def labor_conference_Image(message, full_text, context: ContextTypes.DEFAULT_TYPE, card_id):
    sender = message.from_user
    # username = sender.username or sender.first_name
    # user_id = sender.id
    chat_id = message.chat.id

    logger.info(f"🧾 OCR Text:\n{full_text}")
    # await message.reply_text(f"🧾 Extracted Text:\n{full_text}")
    # === Normalize and Extract Fields ===
    text = full_text.strip()

    # 1. Extract Account Name (MISTER or MRS.)
    name_match = re.search(r'\b(?:MISTER|MRS\.)\s+[A-Z\s]+\b', text)
    name = name_match.group(0).strip() if name_match else "❓ Not found"

    # 2. Extract Account Number
    acc_no_match = re.search(r'\b\d{3}-\d{6}-\d\b', text)
    account_no = acc_no_match.group(0) if acc_no_match else "❓ Not found"

    # 3. Extract Account Type (English only)
    account_type_match = re.search(
        r'Non Passbook Savings Account', text, re.IGNORECASE)
    account_type = account_type_match.group(
        0).strip() if account_type_match else "❓ Not found"

    # 4. Extract Branch (สาขา...)
    branch_match = re.search(r'สาขา[^\n\r]+', text)
    branch = branch_match.group(
        0).strip() if branch_match else "❓ Not found"

    # === Reply back with extracted fields ===
    # reply_text = (
    #     f"👤 Name: {name}\n"
    #     f"🔢 Account No: {account_no}\n"
    #     f"📄 Account Type: {account_type}\n"
    #     f"🏬 Branch: {branch}"
    # )
    labor_Conference(card_id, chat_id, name, account_type, account_no)
    # await message.reply_text(reply_text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'message' not in context.user_data or not context.user_data['message'].photo:
        await query.message.reply_text("❗ No image found to process.")
        return

    message = context.user_data['message']
    await passort_method(message, context)


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
