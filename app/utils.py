import requests
import streamlit as st
import pandas as pd

def fetch_data(year, query, fields):
    url = f"{st.session_state.base_url}search/ticket?user={st.session_state.username}&pass={st.session_state.password}&query={query}>'{year-1}-12-31'AND Created<'{year+1}-01-01'&fields={fields}"
    cookie_jar = st.session_state.cookie_jar

    response = requests.post(url, cookies=cookie_jar)
    data = response.text.split('--')
    
    # Process the data into a structured DataFrame
    records = []
    for entry in data:
        record = {}
        for line in entry.strip().split("\n"):
            if ": " in line:
                key, value = line.split(": ", 1)
                record[key.strip()] = value.strip()
        if record:
            records.append(record)
    
    df = pd.DataFrame(records)
    return df



def login_request(base_url, username, password):
    url = f"{base_url}"
    data = {
        'user': username,
        'pass': password
    }
    
    return requests.post(url, data=data)

def logout_request(base_url, cookies):
    url = f"{base_url}logout"
    return requests.post(url, cookies=cookies)
