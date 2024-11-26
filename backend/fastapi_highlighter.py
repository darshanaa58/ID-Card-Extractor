from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, ImageDraw, ImageFont
import boto3
import io
import os
import base64

# Initialize FastAPI app
app = FastAPI()

# AWS credentials and Textract client setup
aws_region = 'ap-south-1'
aws_access_key_id = 'xxxxxxxxxx'
aws_secret_access_key = 'xxxxxxxx'

textract_client = boto3.client(
    'textract',
    region_name=aws_region,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

# Ensure 'images' folder exists
os.makedirs("images", exist_ok=True)

def analyze_document_with_coordinates(client, image_bytes, original_image_path):
    # Call AWS Textract to analyze the document
    response = client.analyze_document(
        Document={'Bytes': image_bytes},
        FeatureTypes=['FORMS']
    )

    # Load the image from bytes
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    
    # Font setup for labels
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font = ImageFont.load_default()
    
    # Initialize label counter and mapping dictionary
    label_counter = 1
    label_text_mapping = {}

    # Highlight detected text and create label mappings
    for block in response['Blocks']:
        if block['BlockType'] in ['KEY_VALUE_SET', 'WORD'] and 'Text' in block:
            detected_text = block['Text']
            bounding_box = block['Geometry']['BoundingBox']
            
            # Calculate coordinates for bounding box
            width, height = image.size
            left = bounding_box['Left'] * width
            top = bounding_box['Top'] * height
            right = left + (bounding_box['Width'] * width)
            bottom = top + (bounding_box['Height'] * height)
            
            # Draw rectangle around detected text
            draw.rectangle([(left, top), (right, bottom)], outline="red", width=2)
            label_text_mapping[str(label_counter)] = detected_text
            label_counter += 1

    # Save the highlighted image with red borders
    highlighted_image_path = os.path.join("images", f"highlighted_{os.path.basename(original_image_path)}")
    image.save(highlighted_image_path)

    # Create a new image for labels
    num_columns = 3
    label_area_height = (len(label_text_mapping) // num_columns + 1) * 20 + 10  # Extra height for labels
    new_image = Image.new('RGB', (image.width, image.height + label_area_height), (255, 255, 255))
    
    # Paste the original highlighted image onto the new image
    new_image.paste(image, (0, 0))

    # Draw labels in three columns
    draw = ImageDraw.Draw(new_image)
    label_index = 0
    column_width = new_image.width // num_columns
    for idx, (label, text) in enumerate(label_text_mapping.items()):
        column = idx % num_columns
        row = idx // num_columns
        x = column * column_width + 10  # 10 pixels padding
        y = image.height + (row * 20) + 10  # 10 pixels padding from the image
        draw.text((x, y), f"{label}: {text}", fill="blue", font=font)

    # Convert highlighted image with red borders to base64
    buffered = io.BytesIO()
    new_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # Extract fields for specific keys
    output_data = {
        "First Name": label_text_mapping.get("33", ""),
        "Last Name": label_text_mapping.get("29", ""),
        "Date of Birth": label_text_mapping.get("42", ""),
        "Nationality": label_text_mapping.get("43", ""),
        "Place of Birth": label_text_mapping.get("49", ""),
        "Date of Expiry": label_text_mapping.get("56", "")
    }

    return {"extracted_data": output_data, "highlighted_image": img_str}

@app.post("/api/v1/upload_image")
async def upload_image(file: UploadFile = File(...)):
    # Check if the file is an image
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG images are supported.")
    
    # Read file contents
    image_bytes = await file.read()
    original_image_path = f"images/{file.filename}"

    # Save the original uploaded image
    with open(original_image_path, "wb") as f:
        f.write(image_bytes)

    try:
        # Analyze the image with Textract
        extracted_fields = analyze_document_with_coordinates(textract_client, image_bytes, original_image_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {e}")

    # Return extracted fields and highlighted image as JSON
    return JSONResponse(content=extracted_fields)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
