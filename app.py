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

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def init_session_state():
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "orders" not in st.session_state:
        st.session_state.orders = []
    if "is_request_active" not in st.session_state:
        st.session_state.is_request_active = False
    if "image_uploaded" not in st.session_state:
        st.session_state.image_uploaded = False
    if "current_image" not in st.session_state:
        st.session_state.current_image = None

def load_threads():
    thread_file = "./drive/threads.json"
    if os.path.exists(thread_file):
        with open(thread_file, 'r') as f:
            return json.load(f)
    return {}

def save_threads(threads):
    thread_file = "./drive/threads.json"
    os.makedirs(os.path.dirname(thread_file), exist_ok=True)
    with open(thread_file, 'w') as f:
        json.dump(threads, f)

def load_chat_history(thread_id):
    history_file = f"./drive/chat_history/{thread_id}.json"
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return json.load(f)
    return []

def save_chat_history(thread_id, messages):
    history_file = f"./drive/chat_history/{thread_id}.json"
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    with open(history_file, 'w') as f:
        json.dump(messages, f)

def create_new_thread(thread_name):
    threads = load_threads()
    thread = client.beta.threads.create()
    threads[thread.id] = {
        "name": thread_name,
        "created_at": datetime.now().isoformat()
    }
    save_threads(threads)
    return thread.id

def sidebar_thread_management():
    st.sidebar.title("Threads")
    
    # Create new thread
    with st.sidebar.expander("Create New Thread", expanded=False):
        thread_name = st.text_input("Thread Name")
        if st.button("Create Thread"):
            if thread_name:
                thread_id = create_new_thread(thread_name)
                st.session_state.current_thread_id = thread_id
                st.session_state.messages = []
                st.success(f"Created new thread: {thread_name}")
                st.rerun()
            else:
                st.error("Please enter a thread name")

    # List existing threads
    threads = load_threads()
    st.sidebar.markdown("### Your Threads")
    
    for thread_id, thread_info in threads.items():
        if st.sidebar.button(
            f"{thread_info['name']}",
            key=thread_id,
            use_container_width=True,
        ):
            st.session_state.current_thread_id = thread_id
            st.session_state.messages = load_chat_history(thread_id)
            st.rerun()

def main_chat_interface():
    st.title("Image Search with CLIP & AI Chat")

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

    # Display orders
    st.header("Submitted Orders")
    if st.session_state.orders:
        st.dataframe(st.session_state.orders)
    else:
        st.write("No orders submitted yet.")

    if st.session_state.current_thread_id:
        # Image upload and processing
        st.header("Image Search")
        with st.expander("Upload and Search Image"):
            uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"], key="image_uploader")
            
            if uploaded_file and st.session_state.current_image != uploaded_file:
                st.session_state.current_image = uploaded_file
                st.session_state.image_uploaded = False
            
            if st.session_state.current_image and not st.session_state.image_uploaded:
                try:
                    image = Image.open(st.session_state.current_image).convert('RGB')
                    st.image(image, caption='Uploaded Image.', use_container_width=True)
                    
                    with st.spinner('Processing image...'):
                        logs = process_image(image, top_k=5)
                        st.text("Search Results:")
                        st.text(logs)

                    if not st.session_state.is_request_active:
                        st.session_state.is_request_active = True
                        try:
                            wait_for_runs_to_complete(st.session_state.current_thread_id)
                            with st.spinner('Sending results to assistant...'):
                                client.beta.threads.messages.create(
                                    thread_id=st.session_state.current_thread_id,
                                    role="user",
                                    content=f"Image search results: {logs}"
                                )
                                st.success("Results sent to assistant.")
                            
                            with st.spinner('Waiting for assistant...'):
                                messages = run_assistant(st.session_state.current_thread_id, st.secrets["ASSISTANT_ID"])
                                if messages and len(messages) > 0:
                                    assistant_response = messages[0].content[0].text.value
                                    st.session_state.messages.append({
                                        "role": "user",
                                        "content": "Similarity search results by local model on uploaded image: " + logs
                                    })
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": assistant_response
                                    })
                                    save_chat_history(st.session_state.current_thread_id, st.session_state.messages)
                                    st.session_state.is_request_active = False
                                else:
                                    st.warning("No response received from the assistant.")
                                    st.session_state.is_request_active = False
                        except Exception as e:
                            st.error(f"Failed to send message or fetch response: {e}")
                            st.session_state.is_request_active = False
                        finally:
                            st.session_state.image_uploaded = True
                except Exception as e:
                    st.error(f"Error processing image: {e}")

        # Chat Interface
        st.header("Chat with AI Assistant")
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        if st.session_state.is_request_active:
            st.info("Please wait for the current request to complete before sending a new message.")
        else:
            prompt = st.chat_input("Type your message here")
            
            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                
                st.session_state.is_request_active = True
                try:
                    wait_for_runs_to_complete(st.session_state.current_thread_id)
                    with st.spinner('Sending message...'):
                        client.beta.threads.messages.create(
                            thread_id=st.session_state.current_thread_id,
                            role="user",
                            content=prompt
                        )
                        st.success("Message sent successfully!")

                    with st.spinner('Waiting for assistant...'):
                        messages = run_assistant(st.session_state.current_thread_id, st.secrets["ASSISTANT_ID"])
                        if messages and len(messages) > 0:
                            assistant_response = messages[0].content[0].text.value
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": assistant_response
                            })
                            save_chat_history(st.session_state.current_thread_id, st.session_state.messages)
                            with st.chat_message("assistant"):
                                st.write(assistant_response)
                            st.session_state.is_request_active = False
                        else:
                            st.warning("No response received from the assistant.")
                            st.session_state.is_request_active = False
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.is_request_active = False
    else:
        st.info("Please select a thread from the sidebar or create a new one to start chatting.")

def main():
    init_session_state()
    sidebar_thread_management()
    main_chat_interface()

if __name__ == "__main__":
    main()
