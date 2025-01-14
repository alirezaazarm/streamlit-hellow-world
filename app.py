import streamlit as st
from img_search import process_image
from drive import main as drive_main
import os
from openai import OpenAI
import json
from PIL import Image
import time
from assistant_functions import add_order_row
from datetime import datetime
import uuid

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state
def init_session_state():
    os.makedirs("./drive", exist_ok=True)  # Ensure ./drive/ exists
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None
    if "current_thread_name" not in st.session_state:
        st.session_state.current_thread_name = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "threads" not in st.session_state:
        st.session_state.threads = load_threads()

def load_threads():
    thread_file = "./drive/threads.json"
    if os.path.exists(thread_file):
        with open(thread_file, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_threads(threads):
    os.makedirs("./drive", exist_ok=True)
    thread_file = "./drive/threads.json"
    with open(thread_file, 'w') as f:
        json.dump(threads, f)

def load_messages(thread_id):
    os.makedirs("./drive", exist_ok=True)
    messages_file = f"./drive/messages_{thread_id}.json"
    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            return json.load(f)
    else:
        return []

def save_messages(thread_id, messages):
    os.makedirs("./drive", exist_ok=True)
    messages_file = f"./drive/messages_{thread_id}.json"
    with open(messages_file, 'w') as f:
        json.dump(messages, f)

def create_new_thread():
    thread_name = st.text_input("Enter the name for the new thread:")
    if st.button("Create"):
        if thread_name.strip() == "":
            st.warning("Please enter a valid thread name.")
        else:
            thread_id = str(uuid.uuid4())
            st.session_state.threads[thread_name] = thread_id
            save_threads(st.session_state.threads)
            save_messages(thread_id, [])
            st.session_state.current_thread_name = thread_name
            st.session_state.current_thread_id = thread_id
            st.session_state.messages = load_messages(thread_id)
            st.experimental_rerun()

def main_page():
    st.title("Image Search with CLIP & AI Chat")

    # Sidebar for thread selection
    st.sidebar.title("Threads")
    threads = st.session_state.threads
    thread_names = list(threads.keys())

    if thread_names:
        selected_thread = st.sidebar.selectbox("Select a thread", thread_names)
        st.session_state.current_thread_name = selected_thread
        st.session_state.current_thread_id = threads[selected_thread]
        st.session_state.messages = load_messages(st.session_state.current_thread_id)
    else:
        st.sidebar.info("No threads available. Create a new one.")

    if st.sidebar.button("Create New Thread"):
        create_new_thread()

    # Main content
    if st.session_state.current_thread_id:
        # Download required files
        st.header("Downloading Required Files")
        with st.spinner('Downloading files...'):
            try:
                drive_main()
                st.success("All required files are ready.")
            except Exception as e:
                st.error(f"Error in downloading files: {e}")
                st.stop()

        # Load orders from JSON file
        orders_file = f"./drive/orders_{st.session_state.current_thread_id}.json"
        if os.path.exists(orders_file):
            with open(orders_file, 'r') as f:
                orders = json.load(f)
        else:
            orders = []

        # Display orders
        st.header("Submitted Orders")
        if orders:
            st.dataframe(orders)
        else:
            st.write("No orders submitted yet.")

        # Image upload and processing
        st.header("Image Search")
        with st.expander("Upload and Search Image"):
            uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"], key="image_uploader")
            if uploaded_file:
                image = Image.open(uploaded_file).convert('RGB')
                st.image(image, caption='Uploaded Image.', use_container_width=True)
                # Process the image
                with st.spinner('Processing image...'):
                    logs = process_image(image, top_k=5)
                    st.text("Search Results:")
                    st.text(logs)
                # Append image search results to messages
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"Image search results: {logs}"
                })
                save_messages(st.session_state.current_thread_id, st.session_state.messages)

        # Chat with AI Assistant
        st.header("Chat with AI Assistant")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        # Chat input
        prompt = st.chat_input("Type your message here")
        if prompt:
            # Append user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Render user message in chat UI
            with st.chat_message("user"):
                st.write(prompt)
            # Send user message to the assistant
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=st.session_state.messages,
                max_tokens=100
            )
            assistant_response = response.choices[0].message.content
            # Append assistant's response to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_response
            })
            save_messages(st.session_state.current_thread_id, st.session_state.messages)
            # Render assistant's response in chat UI
            with st.chat_message("assistant"):
                st.write(assistant_response)
    else:
        st.info("Please select or create a thread to start.")

def main():
    init_session_state()
    main_page()

if __name__ == "__main__":
    main()
