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
    if "is_request_active" not in st.session_state:
        st.session_state.is_request_active = False

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
    st.header("Downloading Required Files")
    with st.spinner('Downloading files...'):
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
    st.header("Submitted Orders")
    if st.session_state.orders:
        st.dataframe(st.session_state.orders)
    else:
        st.write("No orders submitted yet.")

    # Image upload and processing
    st.header("Image Search")
    with st.expander("Upload and Search Image"):
        if st.button("Share Image"):
            uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"], key="image_uploader")
            if uploaded_file:
                try:
                    # Save uploaded file
                    with open("uploaded_image.jpg", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success("Image uploaded successfully.")

                    # Process the image
                    with st.spinner('Processing image...'):
                        try:
                            logs, error = process_image("uploaded_image.jpg", top_k=5)
                            if error:
                                st.error(f"Error processing image: {error}")
                            else:
                                st.text("Search Results:")
                                st.text(logs)
                        except Exception as e:
                            st.error(f"Error processing image: {e}")
                    
                    # Send results to the assistant
                    try:
                        with st.spinner('Sending results to assistant...'):
                            client.beta.threads.messages.create(
                                thread_id=st.session_state.thread_id,
                                role="user",
                                content=f"Image search results: {logs}"
                            )
                            st.success("Results sent to assistant.")
                    except Exception as e:
                        st.error(f"Failed to send message to assistant: {e}")
                    
                    # Fetch assistant's response
                    with st.spinner('Waiting for assistant...'):
                        try:
                            messages = run_assistant(st.session_state.thread_id, st.secrets["ASSISTANT_ID"])
                            st.session_state.messages.extend([
                                {"role": "user", "content": "Image search results: " + logs},
                                {"role": "assistant", "content": messages[0].content[0].text.value}
                            ])
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to fetch assistant's response: {e}")
                except Exception as e:
                    st.error(f"Error processing image: {e}")

    # Chat with AI Assistant
    st.header("Chat with AI Assistant")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    prompt = st.chat_input("Type your message here")

    if prompt:
        if not st.session_state.is_request_active:
            st.session_state.is_request_active = True
            try:
                with st.spinner('Sending message...'):
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
            # Fetch assistant's response
            with st.spinner('Waiting for assistant...'):
                messages = run_assistant(st.session_state.thread_id, st.secrets["ASSISTANT_ID"])
                st.session_state.messages.extend([
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": messages[0].content[0].text.value}
                ])
                st.rerun()
        else:
            st.warning("A message is currently being processed. Please wait.")

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
