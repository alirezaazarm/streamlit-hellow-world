from init import init_session_state, client
from threads_handling import sidebar_thread_management
from interface import main_chat_interface

def main():
    init_session_state()
    sidebar_thread_management()
    main_chat_interface()

if __name__ == "__main__":
    main()
