# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later


import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from utils import fetch_data

# Constants for response time categories
RESPONSE_CATEGORIES = ["Within first hour", "Within first day", "Within first 2 days", "Within first week", "More than a week", "Not set"]
DATE_FORMAT = '%a %b %d %H:%M:%S %Y'
HOURS_IN_A_DAY = 24
HOURS_IN_A_WEEK = 7 * HOURS_IN_A_DAY

# Data processing function to calculate response time categories
def categorize_response_times(df, started_field="Started", created_field="Created"):
    # Parse datetime fields
    df[started_field] = pd.to_datetime(df[started_field], format=DATE_FORMAT, errors='coerce')
    df[created_field] = pd.to_datetime(df[created_field], format=DATE_FORMAT, errors='coerce')

    # Calculate response times in hours
    df['ResponseTime'] = (df[started_field] - df[created_field]).dt.total_seconds() / 3600.0

    # Categorize based on response time
    df['ResponseCategory'] = df['ResponseTime'].apply(lambda hours: categorize_time(hours))
    df['ResponseCategory'] = pd.Categorical(df['ResponseCategory'], categories=RESPONSE_CATEGORIES, ordered=True)

    return df

# Helper function to categorize response time
def categorize_time(hours):
    if pd.isna(hours):
        return "Not set"
    elif hours <= 1:
        return "Within first hour"
    elif hours <= HOURS_IN_A_DAY:
        return "Within first day"
    elif hours <= 2 * HOURS_IN_A_DAY:
        return "Within first 2 days"
    elif hours <= HOURS_IN_A_WEEK:
        return "Within first week"
    else:
        return "More than a week"

# Cache data fetch operation to avoid redundant requests
@st.cache_data
def fetch_and_process_data(year, query_params):
    df = fetch_data(year, query_params['query'], query_params['fields'])
    if not df.empty:
        df = categorize_response_times(df)
    return df

# Helper function for creating a pie chart
def create_pie_chart(df, year):
    response_counts = df['ResponseCategory'].value_counts().reindex(df['ResponseCategory'].cat.categories, fill_value=0)
    fig = px.pie(
        names=response_counts.index, 
        values=response_counts.values, 
        title=f"Response Time Distribution",
        category_orders={'names': df['ResponseCategory'].cat.categories.tolist()},
        hole=0.4
    )
    return fig

# Helper function for creating a stacked bar chart
def create_stacked_bar_chart(stacked_data):
    stacked_df = pd.DataFrame(stacked_data)
    melted_df = stacked_df.melt(id_vars='Year', var_name='Response Category', value_name='Percentage')

    # Filter categories for the bar chart
    filtered_df = melted_df[melted_df['Response Category'].isin(["Within first hour", "Within first day", "Within first 2 days"])]

    # Create stacked bar chart
    fig = px.bar(
        filtered_df, 
        x='Year', 
        y='Percentage', 
        color='Response Category', 
        title="Stacked Bar Chart of Response Times (%)",
        labels={'Percentage': 'Percentage of Responses (%)', 'Year': 'Year'},
        barmode='stack'
    )
    
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=stacked_df['Year'],
            ticktext=[str(int(year)) for year in stacked_df['Year']]
        )
    )
    return fig

# Prepare data for stacked bar chart
def prepare_stacked_data(all_data):
    stacked_data = [
        {
            "Year": year,
            **{
                category: (response_counts.get(category, 0) / total_responses) * 100
                for category, total_responses in zip(RESPONSE_CATEGORIES, [response_counts.sum()] * len(RESPONSE_CATEGORIES))
            }
        }
        for year, response_counts in all_data.items()
    ]
    return stacked_data


# Load configuration
config = st.session_state.config

st.title("Response Times")

# Text of this Page
st.markdown(config['response_time']['markdown_text']['additional_info'])

# Select years and query toggle
current_year = datetime.datetime.now().year
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(2019, current_year + 1)), 
    default=[current_year-2, current_year-1, current_year]
)
selected_years.sort()

use_query_2 = st.checkbox(config['response_time']['markdown_text']['text_button'])

# Determine query parameters
query_params_key = 'query_parameters_2' if use_query_2 else 'query_parameters_1'
query_params = config['response_time'][query_params_key]

# Fetch and display data
all_data = {}
data_columns = st.columns(len(selected_years))

for idx, year in enumerate(selected_years):
    df = fetch_and_process_data(year, query_params)
    with data_columns[idx]:
        st.subheader(f"{year}")
        if df.empty:
            st.write("No data available for this year.")
        else:
            all_data[year] = df['ResponseCategory'].value_counts().reindex(RESPONSE_CATEGORIES, fill_value=0)
            st.plotly_chart(create_pie_chart(df, year))

# Prepare and display stacked bar chart
if all_data:
    stacked_data = prepare_stacked_data(all_data)
    st.plotly_chart(create_stacked_bar_chart(stacked_data))

