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
    if "image_uploaded" not in st.session_state:
        st.session_state.image_uploaded = False
    if "current_image" not in st.session_state:
        st.session_state.current_image = None

def load_user_credentials():
    cred_file = "./drive/user_credentials.json"
    if os.path.exists(cred_file):
        with open(cred_file, 'r') as f:
            return json.load(f)
    return {}

def save_user_credentials(creds):
    cred_file = "./drive/user_credentials.json"
    os.makedirs(os.path.dirname(cred_file), exist_ok=True)
    with open(cred_file, 'w') as f:
        json.dump(creds, f)

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
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        creds = load_user_credentials()
        if username in creds and creds[username] == password:
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
            st.error("Invalid username or password")
    
    st.write("Don't have an account? ", end="")
    if st.button("Sign Up"):
        st.session_state.page = "signup"
        st.rerun()
    
    st.write("Forgot password? ", end="")
    if st.button("Forgot Password"):
        st.session_state.page = "forgot_password"
        st.rerun()

def signup_page():
    st.title("Sign Up")
    username = st.text_input("Enter your username:")
    password = st.text_input("Enter your password:", type="password")
    confirm_password = st.text_input("Confirm your password:", type="password")
    
    if st.button("Sign Up"):
        creds = load_user_credentials()
        if username in creds:
            st.error("Username already exists. Please choose a different username.")
        else:
            if password == confirm_password:
                creds[username] = password
                save_user_credentials(creds)
                # Create a new thread ID for the user
                user_threads = load_user_threads()
                thread = client.beta.threads.create()
                user_threads[username] = thread.id
                save_user_threads(user_threads)
                st.success("Account created successfully. Please log in.")
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error("Passwords do not match. Please try again.")

def forgot_password_page():
    st.title("Forgot Password")
    username = st.text_input("Enter your username:")
    new_password = st.text_input("Enter your new password:", type="password")
    confirm_new_password = st.text_input("Confirm your new password:", type="password")
    
    if st.button("Reset Password"):
        creds = load_user_credentials()
        if username in creds:
            if new_password == confirm_new_password:
                creds[username] = new_password
                save_user_credentials(creds)
                st.success("Password reset successfully. Please log in with your new password.")
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error("New passwords do not match. Please try again.")
        else:
            st.error("Username not found. Please try again.")

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
        uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"], key="image_uploader")
        
        if uploaded_file and st.session_state.current_image != uploaded_file:
            st.session_state.current_image = uploaded_file
            st.session_state.image_uploaded = False  # Reset the flag for new image
        
        if st.session_state.current_image and not st.session_state.image_uploaded:
            try:
                image = Image.open(st.session_state.current_image).convert('RGB')
                st.image(image, caption='Uploaded Image.', use_column_width=True)
                
                # Process the image
                with st.spinner('Processing image...'):
                    logs = process_image(image, top_k=5)
                    st.text("Search Results:")
                    st.text(logs)

                # Send results to the assistant only once
                if not st.session_state.is_request_active:
                    st.session_state.is_request_active = True
                    try:
                        with st.spinner('Sending results to assistant...'):
                            client.beta.threads.messages.create(
                                thread_id=st.session_state.thread_id,
                                role="user",
                                content=f"Image search results: {logs}"
                            )
                            st.success("Results sent to assistant.")
                        
                        # Fetch assistant's response
                        with st.spinner('Waiting for assistant...'):
                            messages = run_assistant(st.session_state.thread_id, st.secrets["ASSISTANT_ID"])
                            if messages and len(messages) > 0:
                                assistant_response = messages[0].content[0].text.value
                                st.session_state.messages.extend([
                                    {"role": "user", "content": "Similarity search results by local model on uploaded image: " + logs},
                                    {"role": "assistant", "content": assistant_response}
                                ])
                            else:
                                st.warning("No response received from the assistant.")
                    except Exception as e:
                        st.error(f"Failed to send message or fetch response: {e}")
                    finally:
                        st.session_state.is_request_active = False
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
                if messages and len(messages) > 0:
                    assistant_response = messages[0].content[0].text.value
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                    st.rerun()
                else:
                    st.warning("No response received from the assistant.")

def run_assistant(thread_id, assistant_id):
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
            print("Function Calling...")
            required_actions = run.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []
            
            for tool_call in required_actions["tool_calls"]:
                func_name = tool_call['function']['name']
                arguments = json.loads(tool_call['function']['arguments'])
                
                if func_name == "add_order_row":
                    output_df = add_order_row(
                        file_path="./drive/orders.json",
                        first_name=arguments['first_name'],
                        last_name=arguments['last_name'],
                        address=arguments['address'],
                        phone=arguments['phone'],
                        product=arguments['product'],
                        price=arguments['price']
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
            time.sleep(2)
    
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data

def main():
    init_session_state()
    
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "signup":
        signup_page()
    elif st.session_state.page == "forgot_password":
        forgot_password_page()
    elif st.session_state.page == "main":
        main_page()

if __name__ == "__main__":
    main()
