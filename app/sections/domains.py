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
DATE_FORMAT = '%a %b %d %H:%M:%S %Y'


# Function to standardize domain field by sorting its components
def standardize_domain(domain):
    if pd.isna(domain):
        return "Unknown Domain"  # Handle NaN values
    domain_parts = str(domain).split(',')
    domain_parts.sort()  # Sort domain components alphabetically
    return ','.join(domain_parts)

# Function to fetch and concatenate data for selected years
def fetch_data_for_years(selected_years, query_params):
    all_data = pd.DataFrame()  # Initialize an empty DataFrame to collect data from all selected years
    for year in selected_years:
        df = fetch_data(year, query_params['query'], query_params['fields'])
        if not df.empty:
            df['Year'] = year  # Add the year column to the data
            all_data = pd.concat([all_data, df], ignore_index=True)
    return all_data

# Function to process domain counts and calculate percentages
def calculate_domain_percentage(data, year):
    year_data = data[data['Year'] == year]
    domain_counts = year_data['Standardized_Domain'].value_counts().reset_index()
    domain_counts.columns = ['Domain', 'Count']
    total_tickets = domain_counts['Count'].sum()
    domain_counts['Percentage'] = (domain_counts['Count'] / total_tickets) * 100
    return domain_counts.sort_values(by='Domain')

# Function to create total bar chart of ticket counts per domain
def create_total_domain_chart(data):
    domain_counts = data['Standardized_Domain'].value_counts().reset_index()
    domain_counts.columns = ['Domain', 'Count']
    domain_counts = domain_counts.sort_values(by='Domain')
    fig = px.bar(
        domain_counts, 
        x='Count', 
        y='Domain', 
        orientation='h', 
        title='Total Ticket Count per Domain (All Selected Years)'
    )
    return fig

# Function to create year-specific percentage bar chart
def create_yearly_percentage_chart(domain_counts, year, max_percentage):
    fig = px.bar(
        domain_counts, 
        x='Domain', 
        y='Percentage',  
        color='Domain',  
        title=f'Percentage of Tickets per Domain in {year}'
    )
    fig.update_layout(
        xaxis_title=None, 
        showlegend=True, 
        xaxis=dict(showticklabels=False),
        yaxis_range=[0, max_percentage]  
    )
    return fig

# Load configuration
config = st.session_state.config

# Streamlit UI
st.title("Domains Overview")

# Text of this Page
st.markdown(config['domains']['markdown_text']['additional_info'])

current_year = datetime.datetime.now().year
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(DEFAULT_START_YEAR, current_year + 1)), 
    default=[current_year - 2, current_year - 1, current_year]
)
selected_years.sort()

use_alternate_query = st.checkbox(config['domains']['markdown_text']['text_button'])
query_params_key = 'query_parameters_2' if use_alternate_query else 'query_parameters_1'
query_params = config['domains'][query_params_key]

# Fetch data if years are selected
if selected_years:
    all_data = fetch_data_for_years(selected_years, query_params)

    if not all_data.empty:
        # Check if 'Queue' column exists, needed for the IDM->Tourism logic
        if 'Queue' not in all_data.columns:
            st.warning("The 'Queue' column is missing in the fetched data. Cannot apply IDM -> Tourism logic.")
            # Fallback: Apply standard domain logic without Queue check
            all_data['Standardized_Domain'] = all_data['CF.{OpenDataHub Domain}'].apply(standardize_domain)
        else:
            # Apply initial standardization based on the domain field
            all_data['Standardized_Domain'] = all_data['CF.{OpenDataHub Domain}'].apply(standardize_domain)
            # Override domain to 'Tourism' where Queue is 'IDM'
            # Ensure Queue column is treated as string and handle potential NaNs before comparison
            idm_mask = all_data['Queue'].astype(str).fillna('') == 'IDM'
            all_data.loc[idm_mask, 'Standardized_Domain'] = 'Tourism'


        # Display total domain chart
        st.plotly_chart(create_total_domain_chart(all_data))

        # Prepare columns for year-specific charts
        cols = st.columns(len(selected_years))

        # Calculate the global max percentage for uniform y-axis range
        # Handle potential case where a year might have no data after filtering/processing
        max_percentage = 0
        valid_years_for_max = []
        for year in selected_years:
             if not all_data[all_data['Year'] == year].empty:
                 valid_years_for_max.append(year)

        if valid_years_for_max:
             max_percentage = max(
                 calculate_domain_percentage(all_data, year)['Percentage'].max() for year in valid_years_for_max
             )
        else:
             max_percentage = 100 # Default if no data exists for any selected year

        # Display yearly charts
        for idx, year in enumerate(selected_years):
            year_data = all_data[all_data['Year'] == year]
            if not year_data.empty:
                domain_counts_year = calculate_domain_percentage(year_data, year) # Pass filtered data
                if not domain_counts_year.empty:
                    fig_year = create_yearly_percentage_chart(domain_counts_year, year, max_percentage)
                    cols[idx].plotly_chart(fig_year)
                else:
                    cols[idx].write(f"No domain data to display for {year}.")
            else:
                 cols[idx].write(f"No data available for {year}.")


    else:
        st.write("No data available for the selected years.")
else:
    st.write("Please select at least one year.")