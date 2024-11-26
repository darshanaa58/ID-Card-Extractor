import streamlit as st
import requests
from PIL import Image
import io
import base64

# FastAPI backend URL
backend_url = "http://127.0.0.1:8000/api/v1/upload_image"

# Streamlit app title and instructions
st.title("Image Text Extraction App")
st.write("Upload an image to extract text fields.")

# File uploader for image upload
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

# Show the uploaded image
if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    # Send the image to the FastAPI backend for text extraction
    if st.button("Extract Text"):
        with st.spinner("Analyzing image..."):
            # Prepare the file for POST request
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "image/jpeg")}

            # Send the request to FastAPI
            response = requests.post(backend_url, files=files)

        # Check the response after the spinner
        if response.status_code == 200:
            extracted_data = response.json()
            st.write("### Extracted Data")
            st.json(extracted_data['extracted_data'])  # Display the extracted fields

            # Decode and display the highlighted image
            highlighted_image_data = extracted_data['highlighted_image']
            highlighted_image = Image.open(io.BytesIO(base64.b64decode(highlighted_image_data)))
            st.image(highlighted_image, caption="Highlighted Image", use_column_width=True)
        else:
            st.error(f"Failed to extract text. Status code: {response.status_code}")
            st.write(response.text)  # Display the backend error message for debugging
