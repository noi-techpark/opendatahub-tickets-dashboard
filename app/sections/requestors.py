# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later


import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from utils import fetch_data

# Constants
DEFAULT_START_YEAR = 2019

# Cache data fetch operation to avoid redundant requests
@st.cache_data
def fetch_and_process_data(year, query_params):
    return fetch_data(year, query_params['query'], query_params['fields'])

# Function to create a bar chart for a categorical column
def create_bar_chart(df, column_name, title):
    count_series = df[column_name].value_counts()
    fig = px.bar(
        x=count_series.index, 
        y=count_series.values, 
        labels={'x': column_name, 'y': 'Count'}, 
        title=title
    )
    return fig

# Function to create a pie chart for a categorical column
def create_pie_chart(df, column_name, title, hole_size=0.4):
    count_series = df[column_name].value_counts()
    fig = px.pie(
        names=count_series.index, 
        values=count_series.values, 
        title=title,
        hole=hole_size
    )
    return fig

# Function to create a combined pie chart for multiple years
def create_combined_pie_chart(all_data, column_name, title, hole_size=0.4):
    combined_df = pd.concat(all_data, ignore_index=True)
    return create_pie_chart(combined_df, column_name, title, hole_size)

# Streamlit UI to display data and charts
def display_combined_view(all_data):
    st.markdown("## Combined Pie Charts for All Years")
    st.plotly_chart(create_combined_pie_chart(all_data, 'CF.{Type of requestor}', "Type of Requestor"))
    st.markdown(config['requestors']['markdown_text']['chart01'])
    st.plotly_chart(create_combined_pie_chart(all_data, 'CF.{Requestor use case}', "Requestor Use Case"))
    st.markdown(config['requestors']['markdown_text']['chart02'])
    st.plotly_chart(create_combined_pie_chart(all_data, 'CF.{Company type}', "Company Type"))
    st.markdown(config['requestors']['markdown_text']['chart03'])

def display_yearly_view(all_data, selected_years):
    st.markdown("## Yearly Pie Charts for Selected Years")

    # First display all "Type of Requestor" charts for each year
    st.markdown("### Type of Requestor")
    data_columns = st.columns(len(selected_years))
    for idx, year in enumerate(selected_years):
        df = all_data[idx]
        with data_columns[idx]:
            st.subheader(f"Year: {year}")
            if df.empty:
                st.write("No data available for this year.")
            else:
                st.plotly_chart(create_pie_chart(df, 'CF.{Type of requestor}', f"Type of Requestor"))

    # Display the markdown text for "Type of Requestor"
    st.markdown(config['requestors']['markdown_text']['chart01'])

    # Next display all "Requestor Use Case" charts for each year
    st.markdown("### Requestor Use Case")
    data_columns = st.columns(len(selected_years))
    for idx, year in enumerate(selected_years):
        df = all_data[idx]
        with data_columns[idx]:
            st.subheader(f"Year: {year}")
            if df.empty:
                st.write("No data available for this year.")
            else:
                st.plotly_chart(create_pie_chart(df, 'CF.{Requestor use case}', f"Requestor Use Case"))

    # Display the markdown text for "Requestor Use Case"
    st.markdown(config['requestors']['markdown_text']['chart02'])

    # Finally, display all "Company Type" charts for each year
    st.markdown("### Company Type")
    data_columns = st.columns(len(selected_years))
    for idx, year in enumerate(selected_years):
        df = all_data[idx]
        with data_columns[idx]:
            st.subheader(f"Year: {year}")
            if df.empty:
                st.write("No data available for this year.")
            else:
                st.plotly_chart(create_pie_chart(df, 'CF.{Company type}', f"Company Type"))

    # Display the markdown text for "Company Type"
    st.markdown(config['requestors']['markdown_text']['chart03'])


config = st.session_state.config

st.title("Requestors Overview")

# Text of this Page
st.markdown(config['requestors']['markdown_text']['additional_info'])

current_year = datetime.datetime.now().year

# Year selection widget
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(DEFAULT_START_YEAR, current_year + 1)), 
    default=[current_year - 2, current_year - 1, current_year]
)
selected_years.sort()

# Checkbox to select between two query parameters
use_alternate_query = st.checkbox(config['requestors']['markdown_text']['text_button'])

# Determine query parameters based on the checkbox
query_params_key = 'query_parameters_2' if use_alternate_query else 'query_parameters_1'
# Make a copy to avoid modifying the cached config
query_params = config['requestors'][query_params_key].copy()

# Fetch data for each selected year
# Temporary list to store fetched data before processing
fetched_data_list = [fetch_and_process_data(year, query_params) for year in selected_years]

processed_data_list = []
for df in fetched_data_list:
    if not df.empty and 'Queue' in df.columns:
        # Create the mask and add fields for rows where Queue is 'IDM'
        idm_mask = df['Queue'].astype(str).fillna('') == 'IDM'
        if 'CF.{Type of requestor}' in df.columns:
             df.loc[idm_mask, 'CF.{Type of requestor}'] = 'IDM'
        if 'CF.{Requestor use case}' in df.columns:
             df.loc[idm_mask, 'CF.{Requestor use case}'] = 'Data consumer'
        if 'CF.{Company type}' in df.columns:
             df.loc[idm_mask, 'CF.{Company type}'] = 'Publicly held'

    processed_data_list.append(df)

# Use the processed data list from now on
all_data = processed_data_list



# Toggle to switch between "Combined" and "Yearly" views
view_switch = st.radio("Select View:", ["Combined View", "Yearly View"])

# Display combined or yearly data based on the toggle
if view_switch == "Combined View":
    display_combined_view(all_data)
else:
    display_yearly_view(all_data, selected_years)