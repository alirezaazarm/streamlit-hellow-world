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

def main():
    init_session_state()
    sidebar_thread_management()
    main_chat_interface()

if __name__ == "__main__":
    main()
