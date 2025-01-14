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
    
    # Check for duplicate names
    existing_names = [thread_info["name"].lower() for thread_info in threads.values()]
    if thread_name.lower() in existing_names:
        raise ValueError("A thread with this name already exists")
    
    thread = client.beta.threads.create()
    threads[thread.id] = {
        "name": thread_name,
        "created_at": datetime.now().isoformat()
    }
    save_threads(threads)
    return thread.id

def format_datetime(iso_datetime):
    dt = datetime.fromisoformat(iso_datetime)
    return dt.strftime("%Y-%m-%d %H:%M")

def wait_for_runs_to_complete(thread_id):
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    for run in runs.data:
        if run.status in ["requires_action", "processing"]:
            max_attempts = 5
            for attempt in range(max_attempts):
                time.sleep(2**attempt)
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run.status in ["completed", "failed"]:
                    break
            else:
                print(f"Run {run.id} still active after {max_attempts} attempts.")

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
                    st.experimental_rerun()
                except ValueError as e:
                    st.error(str(e))
            else:
                st.error("Please enter a thread name")
    
    # List existing threads
    threads = load_threads()
    st.sidebar.markdown("### Your Threads")
    
    sorted_threads = sorted(
        threads.items(),
        key=lambda x: x[1]['created_at'],
        reverse=True
    )
    
    for thread_id, thread_info in sorted_threads:
        if st.sidebar.button(thread_info['name'], key=thread_id):
            st.session_state.current_thread_id = thread_id
            st.session_state.messages = load_chat_history(thread_id)
            st.experimental_rerun()


def verify_output_against_vector_store(client, vector_store_id, model_response):
    query = model_response
    try:
        search_results = client.beta.vector_stores.search(
            vector_store_id=vector_store_id,
            query=query,
            top_k=5
        )
        if search_results and "results" in search_results:
            matches = [result["document"]["content"] for result in search_results["results"]]
            return model_response in matches, matches
        return False, []
    except Exception as e:
        print(f"Error during verification: {e}")
        return False, []

def run_assistant(thread_id, assistant_id):
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    for run in runs.data:
        if run.status in ["requires_action", "processing"]:
            while run.status not in ["completed", "failed"]:
                time.sleep(2)
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
    
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        
        if run.status == "requires_action":
            required_actions = run.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []
            
            for tool_call in required_actions["tool_calls"]:
                func_name = tool_call['function']['name']
                arguments = json.loads(tool_call['function']['arguments'])
                
                if func_name == "add_order_row":
                    required_params = ['first_name', 'last_name', 'address', 'phone', 'product', 'price', 'how_many']
                    missing_params = [param for param in required_params if param not in arguments]
                    
                    if missing_params:
                        raise KeyError(f"Missing required parameters: {', '.join(missing_params)}")
                    
                    output_df = add_order_row(
                        file_path="./drive/orders.json",
                        first_name=arguments['first_name'],
                        last_name=arguments['last_name'],
                        address=arguments['address'],
                        phone=arguments['phone'],
                        product=arguments['product'],
                        price=arguments['price'],
                        how_many=arguments['how_many']
                    )
                    tool_outputs.append({
                        "tool_call_id": tool_call['id'],
                        "output": output_df.to_json(orient='records', force_ascii=False)
                    })
                else:
                    raise ValueError(f"Unknown function: {func_name}")
            
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        elif run.status == "completed":
            break
        elif run.status == "failed":
            raise Exception(f"Run failed: {run.last_error}")
        else:
            print(f"Run status: {run.status}")
            time.sleep(2)
    
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data

def main_chat_interface():
    st.title("Chat with AI Assistant")
    st.header("Chat Interface")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    if st.session_state.is_request_active:
        st.info("Please wait for the current request to complete.")
    else:
        prompt = st.chat_input("Type your message")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            st.session_state.is_request_active = True
            try:
                wait_for_runs_to_complete(st.session_state.current_thread_id)
                with st.spinner("Sending message..."):
                    client.beta.threads.messages.create(
                        thread_id=st.session_state.current_thread_id,
                        role="user",
                        content=prompt
                    )
                with st.spinner("Waiting for assistant..."):
                    messages = run_assistant(st.session_state.current_thread_id, st.secrets["ASSISTANT_ID"])
                    if messages:
                        assistant_response = messages[0].content[0].text.value
                        
                        verified, matches = verify_output_against_vector_store(
                            client=client,
                            vector_store_id=st.secrets["VECTOR_STORE_ID"],
                            model_response=assistant_response
                        )
                        
                        if verified:
                            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                            with st.chat_message("assistant"):
                                st.write(assistant_response)
                        else:
                            st.warning("The response could not be verified against the database.")
                            st.session_state.messages.append({"role": "assistant", "content": "I'm not sure about that. Let me double-check!"})
                        
                        save_chat_history(st.session_state.current_thread_id, st.session_state.messages)
                    else:
                        st.warning("No response received from the assistant.")
                st.session_state.is_request_active = False
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.is_request_active = False

def main():
    init_session_state()
    sidebar_thread_management()
    main_chat_interface()

if __name__ == "__main__":
    main()
