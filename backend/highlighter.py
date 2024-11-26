from PIL import Image, ImageDraw, ImageFont
import boto3
import json

# Set up AWS region and image path
aws_region = 'ap-south-1'
aws_access_key_id = 'xxxxxxxxxxxxx'
aws_secret_access_key = 'xxxxxxxxxxxxxxx'
image_file_location = 'german_citizenship.jpg'

# Initialize Textract client
textract_client = boto3.client('textract', region_name=aws_region,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key)

def analyze_document_with_coordinates(client, file_name):
    # Read the image file
    with open(file_name, 'rb') as document:
        image_bytes = document.read()

    # Call AWS Textract to analyze the document
    response = client.analyze_document(
        Document={'Bytes': image_bytes},
        FeatureTypes=['FORMS']
    )
    
    # Open the image to draw on
    image = Image.open(file_name)
    draw = ImageDraw.Draw(image)
    
    # Font for label
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font = ImageFont.load_default()
    
    # Initialize label counter and mapping dictionary
    label_counter = 1
    label_text_mapping = {}
    highlighted_boxes = []

    for block in response['Blocks']:
        # Only process blocks that contain detected text
        if block['BlockType'] in ['KEY_VALUE_SET', 'WORD'] and 'Text' in block:
            detected_text = block['Text']
            bounding_box = block['Geometry']['BoundingBox']
            
            # Calculate coordinates for the bounding box
            width, height = image.size
            left = bounding_box['Left'] * width
            top = bounding_box['Top'] * height
            right = left + (bounding_box['Width'] * width)
            bottom = top + (bounding_box['Height'] * height)
            
            # Store the coordinates of highlighted boxes
            highlighted_boxes.append((left, top, right, bottom))
            # Map label to detected text
            label_text_mapping[str(label_counter)] = detected_text
            label_counter += 1

    # Create a new image with additional space for labels
    label_area_height = 50 + (label_counter * 20)  # Extra height for labels
    new_image = Image.new('RGB', (image.width, image.height + label_area_height), (255, 255, 255))
    
    # Paste the original image onto the new image
    new_image.paste(image, (0, 0))

    # Draw highlighted boxes and labels on the original image portion
    for (left, top, right, bottom), label in zip(highlighted_boxes, label_text_mapping.keys()):
        draw.rectangle([(left, top), (right, bottom)], outline="red", width=2)

    # Draw labels below the original image
    draw = ImageDraw.Draw(new_image)
    for idx, (label, text) in enumerate(label_text_mapping.items()):
        draw.text((10, image.height + (idx * 20)), f"{label}: {text}", fill="blue", font=font)

    # Save the image with highlighted text and labels
    output_image_path = 'highlighted_with_labels.png'
    new_image.save(output_image_path)

    # Print the mapping of labels to detected text
    print("Label to Text Mapping:")
    for label, text in label_text_mapping.items():
        print(f"{label} = {text}")

    # Output as JSON
    json_output = json.dumps(label_text_mapping, indent=4)
    print("\nJSON Output:")
    print(json_output)

    # Extract specific fields
    output_data = {
        "First Name": label_text_mapping.get("33", ""),  # "ERIKA"
        "Last Name": label_text_mapping.get("29", ""),   # "MUSTERMANN"
        "Date of Birth": label_text_mapping.get("42", ""),  # "12.08.1983"
        "Nationality": label_text_mapping.get("43", ""),  # "DEUTSCH"
        "Place of Birth": label_text_mapping.get("49", ""),  # "BERLIN"
        "Date of Expiry": label_text_mapping.get("56", "")  # "01.08.2031"
    }
    
    print("\nExtracted Fields:")
    print(json.dumps(output_data, indent=4))  # Prints extracted fields as JSON

# Run the function
def main():
    analyze_document_with_coordinates(textract_client, image_file_location)

if __name__ == "__main__":
    main()
