# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# Cache configuration
CACHE_TTL_HOURS = 1  # Cache time-to-live in hours

def get_cache_key(year, query, fields):
    """Generate a unique cache key based on query parameters."""
    key_string = f"{year}_{query}_{fields}_{st.session_state.username}"
    return hashlib.md5(key_string.encode()).hexdigest()

def init_cache():
    """Initialize the cache in session state if not exists."""
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {}
    if 'cache_timestamps' not in st.session_state:
        st.session_state.cache_timestamps = {}

def is_cache_valid(cache_key):
    """Check if the cached data is still valid based on TTL."""
    if cache_key not in st.session_state.cache_timestamps:
        return False
    cache_time = st.session_state.cache_timestamps[cache_key]
    return datetime.now() - cache_time < timedelta(hours=CACHE_TTL_HOURS)

def get_cached_data(cache_key):
    """Retrieve data from cache if valid."""
    init_cache()
    if cache_key in st.session_state.data_cache and is_cache_valid(cache_key):
        return st.session_state.data_cache[cache_key].copy()
    return None

def set_cached_data(cache_key, df):
    """Store data in cache with timestamp."""
    init_cache()
    st.session_state.data_cache[cache_key] = df.copy()
    st.session_state.cache_timestamps[cache_key] = datetime.now()

def clear_cache():
    """Clear all cached data."""
    if 'data_cache' in st.session_state:
        st.session_state.data_cache = {}
    if 'cache_timestamps' in st.session_state:
        st.session_state.cache_timestamps = {}

def fetch_data(year, query, fields, use_cache=True):
    """Fetch data for a specific year with optional caching."""
    # Ensure 'Created' is always in the fields for quarterly filtering support
    if 'Created' not in fields:
        fields = f"{fields},Created"
    
    cache_key = get_cache_key(year, query, fields)
    
    # Check cache first
    if use_cache:
        cached_df = get_cached_data(cache_key)
        if cached_df is not None:
            print(f"Cache hit for year {year}")
            return cached_df
    
    # Construct the base URL and parameters
    url = f"{st.session_state.base_url}search/ticket?user={st.session_state.username}&pass={st.session_state.password}&fields={fields}"
    cookie_jar = st.session_state.cookie_jar

    # Add the Created condition to the query
    created_condition = f"( Created>'{year-1}-12-31'AND Created<'{year+1}-01-01' )"
    full_query = f"{query} AND {created_condition}"
    
    # Construct the final query URL
    full_url = f"{url}&query={full_query}"
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
    
    # Cache the result
    if use_cache and not df.empty:
        set_cached_data(cache_key, df)
    
    return df


def get_quarter_date_range(year, quarter):
    """Get the start and end dates for a specific quarter."""
    quarter_ranges = {
        1: (f"{year}-01-01", f"{year}-03-31"),
        2: (f"{year}-04-01", f"{year}-06-30"),
        3: (f"{year}-07-01", f"{year}-09-30"),
        4: (f"{year}-10-01", f"{year}-12-31"),
    }
    return quarter_ranges.get(quarter)


def filter_df_by_quarter(df, year, quarter, date_column='Created'):
    """Filter a DataFrame to only include data from a specific quarter."""
    if df.empty:
        return df
    
    # Check if the date column exists
    if date_column not in df.columns:
        return df.iloc[0:0].copy()  # Return empty DataFrame with same structure
    
    # Ensure the date column is in datetime format
    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column], format='%a %b %d %H:%M:%S %Y', errors='coerce')
    
    start_date, end_date = get_quarter_date_range(year, quarter)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date) + timedelta(days=1)  # Include the last day
    
    mask = (df[date_column] >= start_date) & (df[date_column] < end_date)
    return df[mask].copy()


def get_quarter_label(year, quarter):
    """Get a human-readable label for a quarter."""
    return f"Q{quarter} {year}"


def render_time_filter():
    """
    Render the time filter UI component with toggle between years and quarters.
    Returns a tuple of (filter_mode, selected_periods) where:
    - filter_mode is either 'years' or 'quarters'
    - selected_periods is either a list of years or a list of (year, quarter) tuples
    """
    import datetime as dt
    current_year = dt.datetime.now().year
    
    # Create tabs for switching between year and quarter filtering
    filter_tab = st.radio(
        "Filter by:",
        ["Years", "Quarters"],
        horizontal=True,
        key="time_filter_mode"
    )
    
    if filter_tab == "Years":
        selected_years = st.multiselect(
            "Select Years",
            options=list(range(2019, current_year + 1)),
            default=[current_year - 2, current_year - 1, current_year],
            key="year_filter"
        )
        selected_years.sort()
        return 'years', selected_years
    else:
        # Quarter filter mode
        col1, col2 = st.columns(2)
        
        with col1:
            selected_years_for_quarters = st.multiselect(
                "Select Years",
                options=list(range(2019, current_year + 1)),
                default=[current_year],
                key="quarter_year_filter"
            )
        
        with col2:
            selected_quarters = st.multiselect(
                "Select Quarters",
                options=[1, 2, 3, 4],
                default=[1, 2, 3, 4],
                format_func=lambda x: f"Q{x}",
                key="quarter_filter"
            )
        
        # Create list of (year, quarter) tuples
        quarter_periods = []
        for year in sorted(selected_years_for_quarters):
            for quarter in sorted(selected_quarters):
                # Only include quarters that have passed or are current
                if year < current_year or (year == current_year and quarter <= (dt.datetime.now().month - 1) // 3 + 1):
                    quarter_periods.append((year, quarter))
        
        return 'quarters', quarter_periods


def is_download_enabled():
    """Check if download functionality is enabled."""
    return st.session_state.get('download_enabled', False)


def get_ticket_url(ticket_id):
    """Generate a clickable URL for a ticket."""
    base_url = st.session_state.get('tickets_base_url', '')
    if base_url:
        # Extract just the numeric ID if it's in format like "ticket/12345"
        if '/' in str(ticket_id):
            ticket_id = str(ticket_id).split('/')[-1]
        return f"{base_url}?id={ticket_id}"
    return str(ticket_id)


def format_ticket_link_markdown(ticket_id):
    """Format a ticket ID as a clickable markdown link."""
    url = get_ticket_url(ticket_id)
    # Extract just the numeric ID for display
    display_id = str(ticket_id).split('/')[-1] if '/' in str(ticket_id) else str(ticket_id)
    return f"[{display_id}]({url})"


def render_download_button(content, filename, label="Download Markdown Report"):
    """Render a download button if downloads are enabled."""
    if is_download_enabled():
        st.download_button(
            label=label,
            data=content,
            file_name=filename,
            mime="text/markdown"
        )


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
