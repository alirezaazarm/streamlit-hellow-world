# app.py
import streamlit as st
from img_search import process_image
import os

st.title("Image Search with CLIP")
st.write("An app to upload an image and view search logs.")

# Add cache for better performance
@st.cache_resource
def initialize_app():
    return True

# Initialize the app
initialize_app()

uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        # Save uploaded file
        with open("uploaded_image.jpg", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("Image uploaded successfully.")

        # Process the image
        with st.spinner("Processing the uploaded image..."):
            logs = process_image("uploaded_image.jpg", top_k=5)
            st.text("Search Results:")
            st.text(logs)
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        st.error("Please make sure all required files are in the correct location")
