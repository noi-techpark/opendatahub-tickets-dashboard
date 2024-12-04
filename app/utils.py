# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import requests
import streamlit as st
import pandas as pd

def fetch_data(year, query, fields):
    # Construct the base URL and parameters
    url = f"{st.session_state.base_url}search/ticket?user={st.session_state.username}&pass={st.session_state.password}&fields={fields}"
    cookie_jar = st.session_state.cookie_jar

    # Add the Created condition to the query
    created_condition = f"( Created>'{year-1}-12-31'AND Created<'{year+1}-01-01' )"
    query = f"{query} AND {created_condition}"
    
    # Construct the final query URL
    full_url = f"{url}&query={query}"
    print(f"Querying URL: {full_url}")
    
    # Make the POST request
    response = requests.post(full_url, cookies=cookie_jar)
    print(response.text)
    
    # Process the response text into a structured DataFrame
    data = response.text.split('--')
    records = []
    for entry in data:
        record = {}
        for line in entry.strip().split("\n"):
            if ": " in line:
                key, value = line.split(": ", 1)
                record[key.strip()] = value.strip()
        if record:
            records.append(record)
    
    # Convert records to a DataFrame
    df = pd.DataFrame(records)
    print(df)
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
