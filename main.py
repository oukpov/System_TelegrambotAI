from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import logging
import re
from datetime import datetime
from telegram.ext import ContextTypes
from flask import Flask, send_from_directory, request
import threading


BOT_TOKEN = "7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s"
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"
BASE_URL = "https://gtkn.up.railway.app"
SAVE_FOLDER = 'image_option3'
# ========================= Logging Setup =========================
os.makedirs(SAVE_FOLDER, exist_ok=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================= Folder Setup =========================
flask_app = Flask(__name__)


@flask_app.route('/image_option3/<filename>')
def serve_image(filename):
    return send_from_directory(SAVE_FOLDER, filename)


processed_files = set()


def listBankDropdown(chat_id):
    params = {
        "group_id": str(chat_id)
    }
    try:
        # Use json=data in POST request to send JSON payload
        response = requests.post(
            "https://oukpov.store/gtkn_project/public/api/dropdown/list/banks",
            json=params  # Send data as JSON payload
        )
        response.raise_for_status()  # Raises HTTPError for bad responses
        data = response.json()
        print(f'listBankDropdown => {data}')
        return data  # Return actual data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
# Function to fetch bank data, only once per session


def checkMember(chat_id, groupName, botID, context):
    print(
        f'chat_id  : {chat_id}\ngroupName  : {groupName}\nbotID  : {botID}\n')
    url = f"https://oukpov.store/gtkn_project/public/api/check/members?group_id={chat_id}&group_name={groupName}&bot_id={botID}"
    try:
        response = requests.post(url)
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            context.user_data['member'] = data
            context.user_data['bank_id'] = data
            print(f'==> checkMember : {data}')
            return data
        else:
            logger.error(
                f"Failed to fetch bank data. Status Code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching bank data: {e}")
        return []


def convert_date(date_str):
    try:
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return date_str


async def checkMethod(card_id):
    url = f"https://oukpov.store/gtkn_project/public/api/checkPassort?card_id={card_id}"
    try:
        response = requests.post(url)
        response_json = response.json()
        # print(f'============> card_id : {card_id}')
        return response_json.get("key", False)
    except Exception as e:
        print(f"❌ Error checking passport: {e}")
        return False


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
    no,
    image_url1,
    image_blob,
    bot_id

):
    print(f'=======> 🌎 group_id : {group_id} & bot_id : {bot_id}')
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
        "group_id": str(group_id),
        "group_name": group_name,
        "gender": gender,
        "underline": underline,
        "no": no,
        "url_1": image_url1,
        "image_blob_1": image_blob,
        "bot_id": bot_id
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ No.1 Successfuly : ", response.json())
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
    image_url2,
    image_blob

):

    url = "https://oukpov.store/gtkn_project/public/api/add/Labor/conference"
    payload = {
        "card_ID": code_id,
        "group_id": str(group_id),
        "account_name": account_name,
        "account_type": account_type,
        "account_no": account_no,
        "url_2": image_url2,
        "image_blob_2": image_blob,


    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ No.2 : Successfuly", response.json())
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

# ========================= Handler: Photo Upload =========================


def generate_bank_options(data):
    if not data:  # Handle empty or None data
        logger.error("No data available to generate bank options.")
        return []
    # Convert the fetched data into the required format for BANK_OPTIONS
    bank_options = [(item['bank_name'], str(item['bank_name']))
                    for item in data]
    logger.info(f"Generated bank options: {bank_options}")
    return bank_options


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_webhook()
    message = update.message
    chat_id = message.chat.id
    bot_id = context.bot.id
    print(f'===> 🆔 : {chat_id}')

    if 'photo_list' not in context.user_data:
        context.user_data['photo_list'] = []
    elif len(context.user_data['photo_list']) >= 3:
        context.user_data['photo_list'] = []

    photo = message.photo[-1]
    context.user_data['photo_list'].append(photo)
    num_photos = len(context.user_data['photo_list'])
    option_bank = None
    BANK_OPTIONS = []
    # === Case 1 photo ===
    if num_photos == 1:
        # print('===> ✅ No.1 ***********')
        MEMBER = checkMember(chat_id, message.chat.title, bot_id, context)
        if not MEMBER:
            print('❌ Error: No data from checkMember')
            await message.reply_text("❌ Error retrieving member info.")
            return
        context.user_data['MEMBER_INFO'] = MEMBER[0]
        member_status = int(MEMBER[0].get("member", 0))
        option_bank = int(MEMBER[0].get("option_bank", 0))

        if member_status == 1:
            await message.reply_text("*👤 Welcome New Member ✅*\n  Please wait for Admin approval", parse_mode="Markdown")
            return
        elif option_bank == 1:
            await message.reply_text("*⚠️ Please wait for Admin approval*", parse_mode="Markdown")
            return
    # === Case 3 photos ===
    elif num_photos == 3:
        # print('===> ✅ No.2 ***********')
        MEMBER = context.user_data.get("MEMBER_INFO")
        if MEMBER:
            option_bank = int(MEMBER.get("option_bank", 0))

        if option_bank == 0:
            data1 = listBankDropdown(chat_id)
            BANK_OPTIONS = generate_bank_options(data1)

    # === Case 3 photos and process them ===

    MEMBER = context.user_data.get("MEMBER_INFO")
    if MEMBER:
        option_bank = int(MEMBER.get("option_bank", 0))

    if len(context.user_data['photo_list']) == 3 and option_bank == 0:
        # if len(context.user_data['photo_list']) == 3:
        # print(f'===> ✅ No.{num_photos}')
        await process_images_by_index(
            context, message, context.user_data['photo_list'], bot_id,
            update, BANK_OPTIONS, chat_id
        )
        # context.user_data['photo_list'] = []


async def process_images_by_index(context, message, photo_list, bot_id, update: Update, BANK_OPTIONS, chat_id):
    for index, photo in enumerate(photo_list):
        filename = f"{photo.file_unique_id}.jpg"
        file_path = os.path.join(SAVE_FOLDER, filename)

        telegram_file = await context.bot.get_file(photo.file_id)
        await telegram_file.download_to_drive(file_path)

        image_url = f"{BASE_URL}/image_option3/{filename}"

        with open(file_path, 'rb') as f:
            image_blob = f.read()
            encoded_image = base64.b64encode(image_blob).decode('utf-8')

        response = requests.post(
            f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}",
            headers={'Content-Type': 'application/json'},
            json={
                "requests": [{
                    "image": {"content": encoded_image},
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

        if index == 0:
            passport_no = travel_doc_match.group(0) if travel_doc_match else extract_field(
                r'(?:លេខលិខិតឆ្លងដែន\s*/\s*Passport No\.?|Passport No\.?)[:\s]*([A-Z0-9]+)'
            )
            check = await checkMethod(passport_no)

        print(f"passport_no : {passport_no} || check => {check}")

        if check is True:
            match index:
                case 0:
                    print(f'===> ✅ No.{index} ✅')
                    if travel_doc_match:
                        await passort_method(message, full_text, context, image_url, encoded_image, bot_id, chat_id)
                    else:
                        await passort_methodNo(message, full_text, context, image_url, encoded_image, bot_id, chat_id)
                case 1:
                    print(f'===> ✅ No.{index} ✅')
                    await labor_conference_Image(message, full_text, context, passport_no, image_url, encoded_image, chat_id)
                case 2:
                    print(f'===> ✅ No.{index} ✅')
                    # Save required data to context for button handler
                    context.user_data['chat_id'] = passport_no
                    context.user_data['passport_no'] = passport_no
                    context.user_data['image_url'] = image_url
                    context.user_data['encoded_image'] = encoded_image
                    context.user_data['bot_message'] = message
                    context.user_data['group_id'] = chat_id

                    keyboard = [[InlineKeyboardButton(name, callback_data=code)]
                                for name, code in BANK_OPTIONS]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await message.reply_text(
                        "*Please choose a BANK*",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
        else:
            if index == 0:
                await message.reply_text(f"⚠️ {passport_no} already exists or is invalid.")
        # os.remove(file_path)


async def bank_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bank_code = query.data
    context.user_data['selected_bank'] = bank_code
    passport_no = context.user_data.get('passport_no')
    image_url = context.user_data.get('image_url')
    encoded_image = context.user_data.get('encoded_image')
    message = context.user_data.get('bot_message')  # Saved from earlier
    chat_id = context.user_data.get('group_id')
    await query.edit_message_text(
        f"✅ You selected bank : *{bank_code}*",
        parse_mode="Markdown"
    )
    # print(f'==> passport_no : {passport_no}')
    # print(f'==> image_url : {image_url}')
    # print(f'==> encoded_image : {encoded_image}')
    # print(f'==> from_user : {message.from_user}')
    # print(f'==> bank_code : {bank_code}')
    # print(f'==> bot_id : {bot_id}')
    # print(f'==> messages : {messages.}')
    await calculate(message, context, passport_no,
                    image_url, encoded_image, bank_code, chat_id)


async def passort_method(message, full_text, context: ContextTypes.DEFAULT_TYPE, image_url1, image_blob, bot_id, chat_id):
    # sender = message.from_user

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
    # check = checkMethod()
    information(
        surname, given_name, travel_doc_no, dob, doi, doe,
        height, place_of_birth, chat_id, groupname, gender, mrz_1 +
        mrz_2, 1, image_url1, image_blob, bot_id
    )


async def passort_methodNo(message, full_text, context: ContextTypes.DEFAULT_TYPE, image_url1, image_blob, bot_id, chat_id):

    groupname = message.chat.title
    lines = full_text.strip().split('\n')

    def extract_field(pattern, fallback="N/A"):
        match = re.search(pattern, full_text, re.IGNORECASE)
        return match.group(1).strip() if match else fallback

    def format_date(date_str):
        try:
            return datetime.strptime(date_str.strip(), "%d %b %Y").strftime("%Y-%m-%d")
        except Exception:
            return date_str  # fallback if format fails

    def extract_multiline_date(label_pattern):
        for i, line in enumerate(lines):
            if re.search(label_pattern, line, re.IGNORECASE):
                if i + 1 < len(lines):
                    possible_date = lines[i + 1].strip()
                    try:
                        return format_date(possible_date)
                    except:
                        pass
        return "N/A"

    # Field extractions
    surname = extract_field(
        r'(?:នាមត្រកូល\s*/\s*Sarname|នាមត្រកូល)[:\s\-]*([A-Z ]+)')
    given_name = extract_field(
        r'(?:Sugs/Given names|mugs/Given names|Given names)[:\s\-]*([A-Z ]+)')
    passport_no = extract_field(
        r'(?:លេខលិខិតឆ្លងដែន\s*/\s*Passport No\.?|Passport No\.?)[:\s]*([A-Z0-9]+)')
    nationality = extract_field(r'(?:សញ្ញាតិ|Nationality)[:\s]*([A-Z ]+)')

    dob = extract_multiline_date(r'(?:ថ្ងៃខែឆ្នាំកំណើត|Date of birth)')
    doi = extract_multiline_date(r'(?:ថ្ងៃចេញ|Date of issue)')
    doe = extract_multiline_date(r'(?:ផុតកំណត់|Date of expiry)')
    place_of_birth = extract_field(
        r'(?:ទីកន្លែងកំណើត|Place of birth)[:\s]*([A-Z ]+)')

    gender = extract_field(r'(?:Sex|19/Sex)[\s:/\-]*([MF])')
    if gender == "N/A":
        gender = next((line.strip()
                      for line in lines if line.strip() in ['M', 'F']), "N/A")

    height_match = re.search(r'(\d{2,3})\s?CM', full_text.upper())
    height = height_match.group(1) + " CM" if height_match else "N/A"

    mrz_1 = lines[-2] if len(lines) >= 2 else "N/A"
    mrz_2 = lines[-1] if len(lines) >= 1 else "N/A"

    # Optional Khmer fields
    # khmer_name = extract_field(r'(?:ឈ្មោះជាភាសាខ្មែរ|Name in Khmer)[:\s]*(.*)')
    # profession = extract_field(r'(?:មុខរបរ|Profession)[:\s]*(.*)')

    # Save or forward data (call your internal method if needed)
    information(
        surname, given_name, passport_no, dob, doi, doe,
        height, place_of_birth, chat_id, groupname, gender, mrz_1 +
        mrz_2, 2, image_url1, image_blob, bot_id
    )


async def calculate(message, context: ContextTypes.DEFAULT_TYPE, passport_no, image_url3, image_blob, reply_markup, chat_id):
    # === Sender info ===

    # sender = message.from_user
    # username = sender.username or sender.first_name
    # user_id = sender.id
    # chat_id = message.chat.id
    # groupname = message.chat.title
    # bankID = int(bank_id)
    # print(f'chat_id => {chat_id}')
    # === Get and Save Photo ===
    photo = message.photo[-1]  # Highest resolution
    file = await context.bot.get_file(photo.file_id)
    filename = f"{photo.file_unique_id}.jpg"
    file_path = os.path.join(SAVE_FOLDER, filename)
    await file.download_to_drive(file_path)
    logger.info(f"📸 Photo saved to: {file_path}")

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
    try:
        response = requests.post(endpoint_url, headers=headers, json=body)
        response.raise_for_status()
        full_text = response.json()['responses'][0].get(
            'textAnnotations', [{}])[0].get('description', '')

        logger.info(f"🧾 OCR Text:\n{full_text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error with Google Vision API: {e}")
        return
    if 'USD' in full_text or 'KHR' in full_text:
        # print(f'No.1 ====>')
        extract_fields_Khmer(full_text, chat_id, 1,
                             passport_no, image_url3, image_blob, reply_markup)
    else:
        # print(f'No.2 ====>')
        extract_field_thai(full_text, chat_id, 2,
                           passport_no, image_url3, image_blob, reply_markup)


def extract_fields_Khmer(text, groupID, bank_id, passport_no, image_url3, image_blob, reply_markup):
    amount_pattern = r'-?[\d,]+\.\d{2}\s*(KHR|USD)'
    amount_match = re.search(amount_pattern, text)
    named_line_pattern = r'^(?:Transfer to|Received from)\s+(.+)$'

    # Init
    name = None

    if amount_match:
        amount_full = amount_match.group()
        amount_clean = amount_full.replace(',', '')
        currency = amount_match.group(1).lower()
        # print(f"✅ ==> First amount: {amount_clean}")
        # print(f"✅ ==> Currency: {currency}")

        # Try to find "Transfer to" or "Received from"
        named_match = re.search(named_line_pattern, text, re.MULTILINE)
        if named_match:
            name = named_match.group(1).strip()
        else:
            # Fallback: get the line after the amount
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if amount_full in line:
                    # Check next non-empty line
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if next_line:
                            name = next_line
                            break
                    break
        calculateAmount(amount_clean,
                        name, currency, groupID, bank_id, passport_no, image_url3, image_blob, reply_markup)
        if name:
            print(f"✅ ==> Name only: {name}")
        else:
            print("❌ No name found.")
    else:
        print("❌ No valid amount found.")


def extract_field_thai(text, groupID, bank_id, passport_no, image_url3, image_blob, reply_markup):
    normalized_text = re.sub(r'(?<=\d),(?=\d{3}\b)', '', text)

    # Find all decimal numbers
    matches = re.findall(r'\b\d+\.\d{2}\b', normalized_text)

    # Convert appropriately

    def convert_amount(value):
        num = float(value)
        if num == 0:
            return None
        return int(num) if num.is_integer() else num

    # Get the first valid amount
    amount = next((convert_amount(m)
                  for m in matches if convert_amount(m) is not None), None)
    # print(f'===> Th : {amount}')
    # print(amount)
    calculateAmount(amount,
                    "None", 'bat', groupID, bank_id, passport_no, image_url3, image_blob, reply_markup)


def calculateAmount(amount, name, currency, group_id, bank_id, passport_no, image_url3, image_blob, reply_markup):
    if bank_id == 1:
        url = "calculate/amount/kh/option3"
    else:
        url = "calculate/amount/th/option3"
    params = {
        "card_id": passport_no,
        "bank_id": bank_id,
        "amount": amount,
        "name": reply_markup,
        "currency": currency,
        "group_id":  str(group_id),
        "url_3": image_url3,
        "image_blob_3": image_blob
    }

    try:
        # Use json=data in POST request to send JSON payload
        response = requests.post(
            f"https://oukpov.store/gtkn_project/public/api/{url}",
            json=params  # Send data as JSON payload
        )
        response.raise_for_status()  # Raises HTTPError for bad responses
        labels_field = response.json()  # Parse JSON response
        return labels_field  # Return actual data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except:
        return date_str


async def labor_conference_Image(message, full_text, context: ContextTypes.DEFAULT_TYPE, card_id, image_url2, encoded_image, chat_id):
    # sender = message.from_user
    # username = sender.username or sender.first_name
    # user_id = sender.id
    # chat_id = message.chat.id

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
    # branch_match = re.search(r'สาขา[^\n\r]+', text)
    # branch = branch_match.group(
    #     0).strip() if branch_match else "❓ Not found"

    # === Reply back with extracted fields ===
    # reply_text = (
    #     f"👤 Name: {name}\n"
    #     f"🔢 Account No: {account_no}\n"
    #     f"📄 Account Type: {account_type}\n"
    #     f"🏬 Branch: {branch}"
    # )
    labor_Conference(card_id, chat_id, name,
                     account_type, account_no, image_url2, encoded_image)
    # await message.reply_text(reply_text)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    # app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(bank_button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    logger.info("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    threading.Thread(target=lambda: flask_app.run(
        debug=True, use_reloader=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))).start()
    main()
