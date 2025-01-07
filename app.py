import streamlit as st
import os
from drive import main as drive_main
from img_search import process_image

# Ensure required files are downloaded
st.title("Image Search with CLIP")
st.write("An app to upload an image and view search logs.")

# Run drive.py to download necessary files
st.text("Checking for required files...")
try:
    drive_main()  # Call the main function in drive.py to handle downloading
    st.success("All required files are ready.")
except Exception as e:
    st.error(f"Error in downloading files: {e}")
    st.stop()

# Image uploader
uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # Save the uploaded image locally
    with open("uploaded_image.jpg", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("Image uploaded successfully.")

    # Call img_search.py to process the image
    st.text("Processing the uploaded image...")
    logs = process_image("uploaded_image.jpg")  # Assuming `process_image` is defined in img_search.py
    st.text("Processing logs:")
    st.text(logs)
