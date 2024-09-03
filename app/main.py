import streamlit as st
import os
from dotenv import load_dotenv
from utils import login_request, logout_request

def login():
    st.title("Login")
    
    if st.session_state.username:
        password = st.text_input("Password", type="password")
        
        if st.button("Log in"):
            response = login_request(st.session_state.base_url, st.session_state.username, password)
            
            if "200 Ok" in response.text:
                st.session_state.cookie_jar = response.cookies
                
                st.session_state.logged_in = True
                st.session_state.password = password
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        st.error("Username environment variable not set")


def logout():
    st.title("Logout")
    if st.button("Log out"):
        if st.session_state.logged_in:
            logout_request(st.session_state.base_url, st.session_state.cookie_jar)
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.password = ""
        st.session_state.cookie_jar = None
        st.rerun()

def main():

    st.set_page_config(layout="wide", page_icon="assets/NOI_OPENDATAHUB_NEW_BK_nospace-01.svg")

    # Variables
    load_dotenv()
    username_env = os.getenv("USERNAME_RT")
    base_url = os.getenv("BASE_URL")

    st.session_state.username = username_env if username_env else ""
    st.session_state.base_url = base_url if base_url else ""
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "password" not in st.session_state:
        st.session_state.password = ""


    # Define pages
    login_page = st.Page(login, title="Log in", icon="🔒")
    logout_page = st.Page(logout, title="Log out", icon="🔓")

    customer = st.Page("sections/customer_overview.py", title="Customer Overview", icon="", default=True)
    queue = st.Page("sections/help_overview.py", title="Help Queue Overview", icon="")
    # alerts = st.Page("reports/alerts.py", title="System alerts", icon="🚨")

    # search = st.Page("tools/search.py", title="Search", icon="🔍")
    # history = st.Page("tools/history.py", title="History", icon="📜")

    if st.session_state.logged_in:
        pg = st.navigation(
            {
                "Account": [logout_page],
                "Reports": [customer, queue]#, bugs, alerts],
                # "Tools": [search, history],
            }
        )
    else:
        pg = st.navigation([login_page])
        
    pg.run()

if __name__ == "__main__":
    main()