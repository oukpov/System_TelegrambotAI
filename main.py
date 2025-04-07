from mistralai import Mistral
import base64

API_KEY = "SapodE4wtaCwkTQMHWKvqJ50X4wwoGB1"


def encode_image(image_location):
    with open(image_location, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


client = Mistral(api_key=API_KEY)
image_path = 'bride.jpg'  # Ensure this is the correct path to your image file

base64image = encode_image(image_path)

ocr_response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{base64image}"
    }
)

print(ocr_response.pages[0].markdown)
