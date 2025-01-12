import streamlit as st
from img_search import process_image
from drive import main as drive_main
import os
from openai import OpenAI
import json
from datetime import datetime

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state
def init_session_state():
    if "username" not in st.session_state:
        st.session_state.username = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "orders" not in st.session_state:
        st.session_state.orders = []

def load_user_threads():
    thread_file = "./drive/user_threads.json"
    if os.path.exists(thread_file):
        with open(thread_file, 'r') as f:
            return json.load(f)
    return {}

def save_user_threads(user_threads):
    thread_file = "./drive/user_threads.json"
    os.makedirs(os.path.dirname(thread_file), exist_ok=True)
    with open(thread_file, 'w') as f:
        json.dump(user_threads, f)

def login_page():
    st.title("Image Search with CLIP & AI Chat")
    username = st.text_input("Enter your username:")
    
    if st.button("Start"):
        if username:
            st.session_state.username = username
            user_threads = load_user_threads()
            if username not in user_threads:
                thread = client.beta.threads.create()
                user_threads[username] = thread.id
                save_user_threads(user_threads)
            st.session_state.thread_id = user_threads[username]
            st.session_state.page = "main"
            st.rerun()
        else:
            st.error("Please enter a username")

def main_page():
    st.title(f"Welcome {st.session_state.username}")

    # Download required files
    st.text("Checking for required files...")
    try:
        drive_main()
        st.success("All required files are ready.")
    except Exception as e:
        st.error(f"Error in downloading files: {e}")
        st.stop()

    # Load orders from JSON file
    orders_file = "./drive/orders.json"
    if os.path.exists(orders_file):
        with open(orders_file, 'r') as f:
            st.session_state.orders = json.load(f)
    else:
        st.session_state.orders = []

    # Display orders
    st.subheader("Submitted Orders")
    if st.session_state.orders:
        st.table(st.session_state.orders)
    else:
        st.write("No orders submitted yet.")

    # Image upload and processing
    st.subheader("Image Search")
    if st.button("Share Image"):
        uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"], key="image_uploader")
        
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

                    # Debug statements
                    st.write(f"Debug: logs = {logs}")
                    st.write(f"Debug: thread_id = {st.session_state.thread_id}")
                    st.write(f"Debug: assistant_id = {st.secrets['ASSISTANT_ID']}")
                    
                    # Send results to the assistant
                    try:
                        client.beta.threads.messages.create(
                            thread_id=st.session_state.thread_id,
                            role="user",
                            content=f"Image search results:\n{logs}"
                        )
                        st.success("Message sent successfully!")
                    except Exception as e:
                        st.error(f"Error sending message: {e}")
                        
                    # Fetch assistant's response
                    messages = run_assistant(st.session_state.thread_id, st.secrets["ASSISTANT_ID"])
                    st.session_state.messages.extend([
                        {"role": "user", "content": "Image search results:\n" + logs},
                        {"role": "assistant", "content": messages[0].content[0].text.value}
                    ])
                    st.rerun()
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")
                st.error("Please make sure all required files are in the correct location")

    # Chat with AI Assistant
    st.subheader("Chat with AI Assistant")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    if "is_request_active" not in st.session_state:
        st.session_state.is_request_active = False
    # Chat input
    if prompt := st.chat_input("Send a message"):
        if not st.session_state.is_request_active:
            st.session_state.is_request_active = True
            try:
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=prompt
                )
                st.success("Message sent successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                st.session_state.is_request_active = False
        else:
            st.warning("A message is currently being processed. Please wait.")
        messages = run_assistant(st.session_state.thread_id, st.secrets["ASSISTANT_ID"])
        
        st.session_state.messages.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": messages[0].content[0].text.value}
        ])
        
        st.rerun()

def run_assistant(thread_id, assistant_id):
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run.status == "failed":
            return "Sorry, something went wrong. Please try again."
    
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data

def main():
    init_session_state()
    
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "main":
        main_page()

if __name__ == "__main__":
    main()
