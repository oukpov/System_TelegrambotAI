import re
import mimetypes
import base64
import os
from mistralai import Mistral
from typing import Final
import asyncio
import http.client
import urllib.parse
import requests
import re

API_KEY = "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"
TOKEN: Final = '7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s'
BOT_USERNAME: Final = '@chatPlan_Test_bot'


# Initialize Mistral client
client = Mistral(api_key=API_KEY)


def stall_text_hosting(text):
    url = "http://127.0.0.1:8000/api/extract/image/text/option1?type_bank=1"

    # Extract values using regex
    def extract_field(label, text):
        pattern = rf"{label}\s+([^\n]+)"
        match = re.search(pattern, text)
        return match.group(1).strip() if match else "N/A"

    # # Sacombank
    # fields = [
    #     "Amount",
    #     "Transaction code",
    #     "Transaction hash",
    #     "Transaction date",
    #     "Source account",
    #     "Beneficiary account",
    #     "Beneficiary name",
    #     "Fee + Tax",
    #     "Total debit",
    #     "Content"
    # ]
   # ABA Bank
    fields = [
        "Original amount:",
        "Reference \#:",
        "Sender:",
        "To account:",
        "Transaction date:",

    ]
    # Build dictionary to send as listData
    listData = {field: extract_field(field, text) for field in fields}

    # Extract only Amount from listData
    # Default to "N/A" if not found
    amount = listData.get("Original amount:", "N/A")

    print(f"====> Amount to Send:\n{amount}")

    # Optional: send to Telegram
    # sendMessage("@grouptest2024", amount)

    try:
        # Sending only Amount to the API
        response = requests.post(
            url, json={"Amount": amount})
        response.raise_for_status()
        print("✅ Laravel request sent.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return None


def sendMessage(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"""
        {text}
        """
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Message sent to Telegram.")
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram send error: {e}")
        return None


def encode_image(image_path: str) -> str:
    """Encode image to base64 URL with MIME type detection."""
    try:
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            raise ValueError("❌ Unsupported image format")

        with open(image_path, 'rb') as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')

        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        print(f"Encoding error: {e}")
        return None


def extract_mrz(text: str) -> str:
    """Extract MRZ lines from OCR results (2-3 lines of 44 chars each)."""
    mrz_candidates = [
        line for line in text.split('\n')
        if len(line) >= 44 and all(c.isupper() or c in '<<$0123456789' for c in line)
    ]
    return '\n'.join(mrz_candidates[:3])  # Return max 3 MRZ lines


async def process_passport(image_path: str) -> str:
    """Process passport image and return MRZ data with debug prints."""
    print(f"\n=== Processing image: {image_path} ===")

    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return "❌ Image file not found"

    base64image = encode_image(image_path)
    if not base64image:
        print("❌ Failed to encode image")
        return "❌ Image encoding failed"

    print("✅ Image encoded successfully")

    try:
        print("⚡ Sending to OCR API...")
        response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "image_url", "image_url": base64image}
        )

        raw_text = response.pages[0].markdown
        # print("\n📄 RAW OCR OUTPUT:")
        print('===>'+raw_text)

        stall_text_hosting(raw_text)
        mrz_data = extract_mrz(raw_text)

        # print("\n🔍 EXTRACTED MRZ DATA:")
        # print(mrz_data if mrz_data else "No MRZ patterns found")

        return mrz_data if mrz_data else "⚠️ No MRZ data found in the image"
    except Exception as e:
        print(f"🔥 ERROR: {str(e)}")
        return f"🔴 OCR processing error: {str(e)}"

if __name__ == "__main__":
    print("\n=== MRZ EXTRACTION TEST ===")
    # test_image = "image/bank_open1/sacome_bank.jpg"
    test_image = "image/bank_open1/aba.jpg"
    result = asyncio.run(process_passport(test_image))

    # print("\n💎 FINAL RESULT:")
    # print(result)

    # Send to Telegram
# API_KEY = 'AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA'
# API_KEY = 'Key'
# BOT_USERNAME: Final = '@chatPlan_Test_bot'
# TOKEN: Final = '7669003420:AAGKhS6k8bTDxzNQR3_6cmnRPSkEgA8Xt0s'

# API_KEY = 'AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA'
# IMAGE_PATH = 'image/bank_open1/bank_kl.jpg'
# ///
# BOT_USERNAME: Final = '@chatPlan_Test_bot'
# TOKEN: Final = 'KEY'

# API_KEY = 'KEY'
