from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import os
import requests
import base64
import re
import logging
from pyzbar.pyzbar import decode
import cv2
BOT_TOKEN = "7604539261:AAGsgHZ1BMrLbsdi1NWazY8z2HtOSPSRd58"
API_KEY = "AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA"


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


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)


# Function to fetch bank data, only once per session
def fetch_bank_data(chat_id, context):

    url = f"https://oukpov.store/gtkn_project/public/api/list/bank?group_id={chat_id}"
    try:
        response = requests.post(url)
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            # Store the data in the user's context to avoid fetching it again
            context.user_data['bank_data'] = data
            # print('==========================>')
            return data
        else:
            logger.error(
                f"Failed to fetch bank data. Status Code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching bank data: {e}")
        return []


def checkPaySlips(amount_admin, group_id, message_id):
    # print(
    #     f'amount_admin : {amount_admin}\ngroup_id : {group_id}\nmessage_id : {message_id}')
    params = {

        "amount_admin": amount_admin,
        "group_id": group_id,
        "message_id": message_id - 1
    }
    try:
        response = requests.post(
            "https://oukpov.store/gtkn_project/public/api/check/status", params=params, json={})
        response.raise_for_status()  # Raises HTTPError for bad responses
        labels_field = response.json()
        return labels_field  # Return actual data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def calculateAmount(bank_id, bank_name, amount, name, currency, group_id, group_name, bot_id, qr_id, message_id):
    bank_id = int(bank_id)
    print(f'======> qr_id : {qr_id}')
    params = {
        "bank_name": bank_name,
        "bank_id": bank_id,
        "amount": amount,
        "name": name,
        "currency": currency,
        "group_id": group_id,
        "group_name": group_name,
        "bot_id": bot_id,
        "qr_id": qr_id,
        "message_id": message_id,
    }

    try:
        response = requests.post(
            f"https://oukpov.store/gtkn_project/public/api/calculate/amount/option1", params=params, json={})
        response.raise_for_status()  # Raises HTTPError for bad responses
        labels_field = response.json()
        return labels_field  # Return actual data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def generate_bank_options(data):
    if not data:  # Handle empty or None data
        logger.error("No data available to generate bank options.")
        return []
    # Convert the fetched data into the required format for BANK_OPTIONS
    bank_options = [(item['bank_name'], str(item['bank_id'])) for item in data]
    logger.info(f"Generated bank options: {bank_options}")
    return bank_options


# ========================= Handlers =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send a photo (Payslip) to continue.")
processed_files = set()


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_webhook()
    message = update.message
    user_id = message.from_user.id
    chat = message.chat
    text = message.text or ""
    chat_id = message.chat.id

    # === CASE 1: If message contains a phot
    if message.photo:
        photo = message.photo[-1]
        file_unique_id = photo.file_unique_id
        context.user_data['photo_file_id'] = photo.file_id
        context.user_data['message'] = message
        photo_message_id = message.message_id
        processed_files.add(file_unique_id)
        # await message.reply_text("🖼️ Received a photo.")
        await show_bank_options(update, context, message, photo, file_unique_id, photo_message_id)
        return
    # === CASE 2: If message is a reply and starts with '+'
    elif message.reply_to_message and text.startswith("+"):
        member = await context.bot.get_chat_member(chat.id, user_id)
        if member.status not in ['administrator', 'creator']:
            await message.reply_text("❌ Only admins can use this command.")
            return

        replied_msg_id = message.reply_to_message.message_id
        checkPaySlips(text, chat_id, replied_msg_id)
        # await message.reply_text(
        #     f"✅ Admin command accepted: {text}\n"
        #     f"📨 Target message ID: {replied_msg_id}"
        # )

        # Optionally process the amount
        # amount = int(text[1:])  # If needed
        return


async def show_bank_options(update: Update, context: ContextTypes.DEFAULT_TYPE, message, photo, file_unique_id, message_id):
    data = fetch_bank_data(update.message.chat.id, context)
    BANK_OPTIONS = generate_bank_options(data)

    file = await photo.get_file()
    img_path = f'/path/to/save/{file_unique_id}.jpg'
    os.makedirs(os.path.dirname(img_path), exist_ok=True)

    try:
        await file.download_to_drive(img_path)
        # Read the image for QR code detection
        image = cv2.imread(img_path)

        # Check if the image was loaded properly
        if image is None:
            raise ValueError(
                f"Image not found or cannot be opened: {img_path}")

            # Decode QR codes if present in the image
        qr_codes = decode(image)
        if qr_codes:
            for qr in qr_codes:
                qr_data = qr.data.decode('utf-8')
                logger.info(f"QR Code found: {qr_data}")
                # await message.reply_text(f"✅ QR Code found: {qr_data}")
            qr_RF = True
        else:
            logger.info("No QR Code found in the image.")
            qr_data = "N/A"
            qr_RF = False
            # await message.reply_text("❌ No QR Code found in the image.")

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        await message.reply_text("❌ An error occurred while processing the image.")
    if len(data) > 1:

        keyboard = [[InlineKeyboardButton(name, callback_data=code)]
                    for name, code in BANK_OPTIONS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "*Please choose a BANK*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:

        if data:  # Make sure it's not an empty list
            first_bank = data[0]
            await calculate(message, context, first_bank['bank_id'], first_bank['bank_name'], qr_data, qr_RF, update, message_id)
        else:
            await calculate(message, context, 1, "N/A", qr_data, qr_RF, update, message_id)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Try to get selected bank code from the button
    bank_code = query.data

    # Check if the message contains an image
    if 'message' not in context.user_data or not context.user_data['message'].photo:
        await query.message.reply_text("❗ No image found to process.")
        return

    message = context.user_data['message']
    photo = message.photo[-1]  # Highest resolution

    # Fetch bank list
    data = fetch_bank_data(message.chat.id, context)
    # print(f'---> bank data: {data}')

    # if data != []:
    # Get bank name from list
    bank_name = next((name for name, code in generate_bank_options(
        data) if code == bank_code), "Unknown")

    await query.edit_message_text(
        text=f"✅ *{bank_name}*",
        parse_mode="Markdown"
    )

    context.user_data['bank_code'] = bank_code
    context.user_data['bank_name'] = bank_name

    # Proceed with OCR + calculation
    await calculate(message, context, bank_code, bank_name)


def extract_field_thai(text, bank_name, bank_id, groupID, groupName, bot_id, qr_id, message_id):
    matches = re.findall(r'\b\d+\.\d{2}\b', text)

    # Convert appropriately
    def convert_amount(value):
        num = float(value)
        if num == 0:
            return None
        return int(num) if num.is_integer() else num

    # Get the first valid amount
    amount = next((convert_amount(m)
                  for m in matches if convert_amount(m) is not None), None)
    # print(amount)
    calculateAmount(bank_id, bank_name, amount,
                    "None", 'bat', groupID, groupName, bot_id, qr_id, message_id)


def extract_fields_Khmer(text, bank_name, bank_id, groupID, groupName, bot_id, message_id):
    amount_pattern = r'-?[\d,]+\.\d{2}\s*(KHR|USD)'
    named_line_pattern = r'^(?:Transfer to|Received from)\s+(.+)$'

    # Now support 4 formats
    date_patterns = [
        # Apr 15, 2025 01:56 PM
        r'([A-Za-z]{3,9} \d{1,2}, \d{4} \d{1,2}:\d{2} ?[APMapm]{2})',
        # 29-Apr-2025 07:10 AM
        r'(\d{1,2}-[A-Za-z]{3}-\d{4} \d{1,2}:\d{2} ?[APMapm]{2})',
        # 09-04-2025 | 20:35:52 PM
        r'(\d{2}-\d{2}-\d{4} *\| *\d{2}:\d{2}:\d{2} ?[APMapm]{2})',
        # 05:49:31 08/04/2025
        r'(\d{2}:\d{2}:\d{2} \d{2}/\d{2}/\d{4})',
        r'([A-Za-z]{3} \d{1,2}, \d{4} \| \d{1,2}:\d{2}[APMapm]{2})'
    ]

    name = None
    trx_date = None

    amount_match = re.search(amount_pattern, text)
    print(f'=================> amount_match : {amount_match}')

    if amount_match:
        amount_full = amount_match.group()
        amount_clean = amount_full.replace(',', '')
        currency = amount_match.group(1).lower()

        # Try to find name
        named_match = re.search(named_line_pattern, text, re.MULTILINE)
        if named_match:
            name = named_match.group(1).strip()
        else:
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if amount_full in line:
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if next_line:
                            name = next_line
                            break
                    break

        # Find matching date
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                trx_date = date_match.group(1).strip()
                trx_date = re.sub(r'\b(am|pm)\b', lambda m: m.group(
                    1).upper(), trx_date, flags=re.IGNORECASE)
                break

        # Final output
        calculateAmount(
            bank_id, bank_name,
            amount_clean, name,
            currency, groupID,
            groupName, bot_id, trx_date, message_id
        )

        print(f"✅ ==> Amount: {amount_clean}")
        print(f"✅ ==> Currency: {currency}")
        print(f"✅ ==> Name: {name if name else 'Not found'}")
        print(
            f"✅ ==> Trx. Date: {trx_date if trx_date else 'Not found in any format'}")

    else:
        print("❌ No valid amount found.")


# ========================= Photo Handler =========================
processed_files = set()


async def calculate(message, context: ContextTypes.DEFAULT_TYPE, bank_id, bank_name, qr_data, qr_RF, update: Update, message_id):
    # === Sender info ===
    sender = message.from_user
    chat_id = message.chat.id
    groupname = message.chat.title
    bankID = int(bank_id)
    bot_id = context.bot.id  # Use context.bot.id instead of message.bot.id

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

    # === Field Extraction ===
    if bankID == 1:
        extract_fields_Khmer(full_text, bank_name, bank_id,
                             chat_id, groupname, bot_id, message_id)
    else:
        if qr_RF == False:
            messageText = "❌ *Fake PaySlip*"
            await update.message.reply_text(
                text=f"*{messageText}*",
                parse_mode="Markdown"
            )
        else:
            messageText = "✅ *Processed*"
        # await update.message.reply_text(
        #     text=f"{messageText}\n🆔 *PaySlip No* : {qr_data}",
        #     parse_mode="Markdown"
        # )
            extract_field_thai(full_text, bank_name, bank_id,
                               chat_id, groupname, bot_id, qr_data, message_id)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # app.add_handler(MessageHandler(filters.ALL, photo_handler))
    # app.add_handler(CallbackQueryHandler(button_handler))  # keep this

    logger.info("🤖 Bot is running... Send a photo!")
    app.run_polling()


if __name__ == "__main__":
    main()
