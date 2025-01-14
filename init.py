from openai import OpenAI
import streamlit as st

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
