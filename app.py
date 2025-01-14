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

# Initialize session state
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
    thread_file = "./drive/threads.json"
    os.makedirs(os.path.dirname(thread_file), exist_ok=True)
    with open(thread_file, 'w') as f:
        json.dump(threads, f)

def create_new_thread():
    thread_name = st.text_input("Enter the name for the new thread:")
    if st.button("Create Thread"):
        if thread_name.strip() == "":
            st.warning("Please enter a thread name.")
        else:
            try:
                thread = client.beta.threads.create()
                st.session_state.threads[thread_name] = thread.id
                save_threads(st.session_state.threads)
                st.session_state.current_thread_id = thread.id
                st.success(f"Thread '{thread_name}' created.")
                st.rerun()
            except Exception as e:
                st.error(f"Error creating thread: {e}")

def main_page():
    st.title("Image Search with CLIP & AI Chat")
    st.session_state.threads = load_threads()  # Reload threads

    # Sidebar for thread selection
    st.sidebar.title("Threads")
    threads_list = list(st.session_state.threads.keys())
    if threads_list:
        selected_thread_name = st.sidebar.selectbox("Select a thread", threads_list)
        selected_thread_id = st.session_state.threads[selected_thread_name]
        st.session_state.current_thread_id = selected_thread_id
    else:
        st.sidebar.info("No threads available. Create a new thread.")

    if st.sidebar.button("New Thread"):
        create_new_thread()

    # Check if a thread is selected
    if st.session_state.current_thread_id is None:
        st.warning("Please select or create a thread to continue.")
        return

    # Download required files
    st.header("Downloading Required Files")
    with st.spinner('Downloading files...'):
        try:
            drive_main()
            st.success("All required files are ready.")
        except Exception as e:
            st.error(f"Error in downloading files: {e}")
            st.stop()

    # Load orders for the current thread
    orders_file = f"./drive/orders_{st.session_state.current_thread_id}.json"
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
        uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"], key="image_uploader")
        
        if uploaded_file and st.session_state.current_image != uploaded_file:
            st.session_state.current_image = uploaded_file
            st.session_state.image_uploaded = False  # Reset the flag for new image
        
        if st.session_state.current_image and not st.session_state.image_uploaded:
            try:
                image = Image.open(st.session_state.current_image).convert('RGB')
                st.image(image, caption='Uploaded Image.', use_container_width=True)
                
                # Process the image
                with st.spinner('Processing image...'):
                    logs = process_image(image, top_k=5)
                    st.text("Search Results:")
                    st.text(logs)

                # Send results to the assistant only once
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
                        
                        # Fetch assistant's response
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
                                st.session_state.is_request_active = False  # Reset the flag
                            else:
                                st.warning("No response received from the assistant.")
                                st.session_state.is_request_active = False  # Reset the flag
                    except Exception as e:
                        st.error(f"Failed to send message or fetch response: {e}")
                        st.session_state.is_request_active = False  # Reset the flag
                    finally:
                        st.session_state.image_uploaded = True  # Mark image as processed
                else:
                    st.warning("A message is currently being processed. Please wait.")
            except Exception as e:
                st.error(f"Error processing image: {e}")
                
    # Chat with AI Assistant
    st.header("Chat with AI Assistant")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Check if a request is active
    if st.session_state.is_request_active:
        st.info("Please wait for the current request to complete before sending a new message.")
    else:
        # Chat input
        prompt = st.chat_input("Type your message here")
        
        if prompt:
            # Append user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Render user message in chat UI
            with st.chat_message("user"):
                st.write(prompt)
            # Send user message to the assistant
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
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.is_request_active = False  # Reset the flag
            finally:
                # Fetch assistant's response
                with st.spinner('Waiting for assistant...'):
                    messages = run_assistant(st.session_state.current_thread_id, st.secrets["ASSISTANT_ID"])
                    if messages and len(messages) > 0:
                        assistant_response = messages[0].content[0].text.value
                        # Append assistant's response to chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": assistant_response
                        })
                        # Render assistant's response in chat UI
                        with st.chat_message("assistant"):
                            st.write(assistant_response)
                        st.session_state.is_request_active = False  # Reset the flag
                    else:
                        st.warning("No response received from the assistant.")
                        st.session_state.is_request_active = False  # Reset the flag

def wait_for_runs_to_complete(thread_id):
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    for run in runs.data:
        if run.status in ["requires_action", "processing"]:
            # Wait until the active run is completed with exponential backoff
            max_attempts = 5
            for attempt in range(max_attempts):
                time.sleep(2**attempt)  # Exponential backoff
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run.status in ["completed", "failed"]:
                    break
            else:
                print(f"Run {run.id} still active after {max_attempts} attempts.")

def run_assistant(thread_id, assistant_id):
    # Check for existing active runs
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    for run in runs.data:
        if run.status in ["requires_action", "processing"]:
            # Wait until the active run is completed
            while run.status not in ["completed", "failed"]:
                time.sleep(2)  # Polling interval
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
    
    # Create a new run
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
                        file_path=f"./drive/orders_{thread_id}.json",
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
        else:
            print(f"Run status: {run.status}")
            time.sleep(2)  # Polling interval
    
    # Fetch messages after the run is completed
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data

def main():
    init_session_state()
    main_page()

if __name__ == "__main__":
    main()
