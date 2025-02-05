from assistant_functions import format_datetime
from datetime import datetime
from init import client
import streamlit as st
import json
import os


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

    # Check for duplicate names
    existing_names = [thread_info["name"].lower() for thread_info in threads.values()]
    if thread_name.lower() in existing_names:
        raise ValueError("A thread with this name already exists")

    thread = client.beta.threads.create(tool_resources={"file_search": {"vector_store_ids": [st.secrets["VECTORSTORE_ID "]] }} )
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
                try:
                    thread_id = create_new_thread(thread_name)
                    st.session_state.current_thread_id = thread_id
                    st.session_state.messages = []
                    st.success(f"Created new thread: {thread_name}")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            else:
                st.error("Please enter a thread name")

    # List existing threads
    threads = load_threads()
    st.sidebar.markdown("### Your Threads")

    # Custom CSS for thread buttons
    st.markdown("""
        <style>
        .thread-timestamp {
            font-size: 12px;
            color: #666;
            text-align: right;
            padding-top: 4px;
        }
        .thread-container {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
        }
        .thread-name {
            font-size: 16px;
            margin-bottom: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Sort threads by creation date (newest first)
    sorted_threads = sorted(
        threads.items(),
        key=lambda x: x[1]['created_at'],
        reverse=True
    )

    for thread_id, thread_info in sorted_threads:
        # Create a container for each thread
        with st.sidebar.container():
            # Use HTML for custom styling
            st.markdown(f"""
                <div class="thread-container" onclick="window.location.href='#{thread_id}'">
                    <div class="thread-name">{thread_info['name']}</div>
                    <div class="thread-timestamp">{format_datetime(thread_info['created_at'])}</div>
                </div>
            """, unsafe_allow_html=True)

            # Hidden button for functionality
            if st.button(
                thread_info['name'],
                key=thread_id,
                use_container_width=True,
                type="secondary"
            ):
                st.session_state.current_thread_id = thread_id
                st.session_state.messages = load_chat_history(thread_id)
                st.rerun()
