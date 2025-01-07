import streamlit as st
import os
from drive import main as drive_main
from img_search import process_image

st.title("Image Search with CLIP")
st.write("An app to upload an image and view search logs.")

st.text("Checking for required files...")
try:
    drive_main()  
    st.success("All required files are ready.")
except Exception as e:
    st.error(f"Error in downloading files: {e}")
    st.stop()


uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    with open("uploaded_image.jpg", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("Image uploaded successfully.")

    st.text("Processing the uploaded image...")
    try:
        logs = process_image("uploaded_image.jpg", top_k=5)
        st.text("Search Results:")
        st.text(logs)
    except Exception as e:
        st.error(f"Error processing image: {e}")
        st.error("Make sure the pickle file and CSV file are in the correct location")
