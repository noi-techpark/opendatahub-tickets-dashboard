# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import streamlit as st
import yaml
import os
from dotenv import load_dotenv
from utils import login_request, logout_request
import plotly.io as pio

def load_config():
    # Determine the absolute path to config.yaml based on the current file's directory
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config = {}

    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        st.error(f"Configuration file not found at {config_path}.")
    except yaml.YAMLError:
        st.error("Error reading configuration file.")
    
    return config

# color scheme
BLACK_WHITE_GRAY_SCHEME = ['#000000', '#555555', '#808080', '#A9A9A9', '#D3D3D3', '#FFFFFF']

# Set the custom Plotly template globally
pio.templates["black_white_gray_template"] = pio.templates["plotly"]
pio.templates["black_white_gray_template"]['layout']['colorway'] = BLACK_WHITE_GRAY_SCHEME
pio.templates.default = "black_white_gray_template"

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

    # Load environment variables and config file
    load_dotenv()
    st.session_state.config = load_config()  # Store config in session state
    
    # Other setup as before
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

    queue = st.Page("sections/help_overview.py", title="Help Queue Overview", icon="", default=True)
    customer = st.Page("sections/customer_overview.py", title="Customer Overview", icon="")
    time = st.Page("sections/response_time.py", title="Response Times", icon="")
    domain = st.Page("sections/domains.py", title="Domains", icon="")
    idm = st.Page("sections/idm_tickets.py", title="IDM Tickets", icon="")
    requestors = st.Page("sections/requestors.py", title="Requestors", icon="")

    if st.session_state.logged_in:
        pg = st.navigation(
            {
                "Account": [logout_page],
                "Reports": [queue, domain, idm, time, requestors, customer]
            }
        )
    else:
        pg = st.navigation([login_page])
        
    pg.run()

if __name__ == "__main__":
    main()