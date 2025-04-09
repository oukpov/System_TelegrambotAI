import requests
import base64

API_KEY = 'AIzaSyAwuW-TTjKqYG7c-BSg_AquN37gv5Ia8OA'
IMAGE_PATH = 'image/bank_open1/bank_kl.jpg'
# IMAGE_PATH = 'image/bank_open1/bank_aba_150.jpg'


# Step 1: Read and encode image
with open(IMAGE_PATH, 'rb') as image_file:
    content = base64.b64encode(image_file.read()).decode('utf-8')

# Step 2: Call Vision API
endpoint_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
headers = {'Content-Type': 'application/json'}
body = {
    "requests": [{
        "image": {"content": content},
        "features": [{"type": "TEXT_DETECTION"}]
    }]
}

response = requests.post(endpoint_url, headers=headers, json=body)
full_text = response.json()['responses'][0].get(
    'textAnnotations', [{}])[0].get('description', '')
# print("🔍 Raw OCR output:\n", full_text)

# Step 3: Define function to extract fields by label blocks


def extract_fields_by_order(text):
    labels = [
        "Trx. ID", "From account", "Original amount",
        "Reference #", "Sender", "To account", "Transaction date"
    ]

    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

    # Step 1: Find where labels end
    label_indices = []
    for i, line in enumerate(lines):
        if any(label in line for label in labels):
            label_indices.append(i)

    if not label_indices:
        return {"error": "Labels not found"}

    # Step 2: Assume values come after the last label line
    value_start_index = label_indices[-1] + 1
    values = lines[value_start_index:]

    # Step 3: Group values line-by-line into expected fields
    field_data = {}
    field_values = []

    # Sometimes multi-line values exist (like sender names), so let's pad safely
    current_value = []
    for val in values:
        current_value.append(val)
        if len(field_values) < len(labels) - 1:
            field_values.append(' '.join(current_value).strip())
            current_value = []
    if current_value:
        field_values.append(' '.join(current_value).strip())

    # Map fields to values
    for i, label in enumerate(labels):
        field_data[label] = field_values[i] if i < len(
            field_values) else "Not found"

    return field_data


extracted = extract_fields_by_order(full_text)
print("\n🧾 Extracted Fields:")
for key in [
    "Trx. ID", "From account", "Original amount",
    "Reference #", "Sender", "To account", "Transaction date"
]:
    print(f"{key} : {extracted.get(key, 'Not found')}")
