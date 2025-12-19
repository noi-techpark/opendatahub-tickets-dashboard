# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later


import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from utils import fetch_data, render_time_filter, filter_df_by_quarter, get_quarter_label, is_download_enabled, format_ticket_link_markdown, render_download_button

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


# Function to fetch and concatenate data for selected quarters
def fetch_data_for_quarters(quarter_periods, query_params):
    all_data = pd.DataFrame()
    
    # Group by year to minimize fetches
    years_needed = set(year for year, _ in quarter_periods)
    year_data_cache = {}
    
    for year in years_needed:
        df = fetch_data(year, query_params['query'], query_params['fields'])
        if not df.empty and 'Created' in df.columns:
            df['Created'] = pd.to_datetime(df['Created'], format=DATE_FORMAT, errors='coerce')
        year_data_cache[year] = df
    
    for year, quarter in quarter_periods:
        df = year_data_cache.get(year, pd.DataFrame())
        if not df.empty and 'Created' in df.columns:
            df_quarter = filter_df_by_quarter(df, year, quarter)
            if not df_quarter.empty:
                df_quarter = df_quarter.copy()
                df_quarter['Period'] = get_quarter_label(year, quarter)
                all_data = pd.concat([all_data, df_quarter], ignore_index=True)
    
    return all_data


# Function to process domain counts and calculate percentages
def calculate_domain_percentage(data, period_col, period_value):
    period_data = data[data[period_col] == period_value]
    domain_counts = period_data['Standardized_Domain'].value_counts().reset_index()
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
        title='Total Ticket Count per Domain (All Selected Periods)'
    )
    return fig

# Function to create period-specific percentage bar chart
def create_period_percentage_chart(domain_counts, period_label, max_percentage):
    fig = px.bar(
        domain_counts, 
        x='Domain', 
        y='Percentage',  
        color='Domain',  
        title=f'Percentage of Tickets per Domain in {period_label}'
    )
    fig.update_layout(
        xaxis_title=None, 
        showlegend=True, 
        xaxis=dict(showticklabels=False),
        yaxis_range=[0, max_percentage]  
    )
    return fig


def generate_domains_markdown_report(all_data, period_col, period_labels):
    """Generate a markdown report for domains."""
    lines = []
    lines.append("# Domains Overview Report\n")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    for period in period_labels:
        period_data = all_data[all_data[period_col] == period]
        lines.append(f"## {period}\n")
        
        if period_data.empty:
            lines.append("No data for this period.\n")
            continue
        
        lines.append(f"**Total Tickets:** {len(period_data)}\n")
        
        # Group by domain
        for domain in sorted(period_data['Standardized_Domain'].unique()):
            domain_df = period_data[period_data['Standardized_Domain'] == domain]
            lines.append(f"### {domain} ({len(domain_df)} tickets)")
            
            # Get ticket IDs
            lower_cols = [col.lower() for col in period_data.columns]
            if "id" in lower_cols:
                id_col = [col for col in period_data.columns if col.lower() == "id"][0]
                for tid in domain_df[id_col].tolist():
                    lines.append(f"- {format_ticket_link_markdown(tid)}")
            lines.append("")
        
        lines.append("")
    
    return "\n".join(lines)


# Load configuration
config = st.session_state.config

# Streamlit UI
st.title("Domains Overview")

# Text of this Page
st.markdown(config['domains']['markdown_text']['additional_info'])

# Use the unified time filter component
filter_mode, selected_periods = render_time_filter()

use_alternate_query = st.checkbox(config['domains']['markdown_text']['text_button'])
query_params_key = 'query_parameters_2' if use_alternate_query else 'query_parameters_1'
query_params = config['domains'][query_params_key]

# Fetch data based on filter mode
if filter_mode == 'years' and selected_periods:
    all_data = fetch_data_for_years(selected_periods, query_params)
    period_col = 'Year'
    period_labels = selected_periods
    
elif filter_mode == 'quarters' and selected_periods:
    all_data = fetch_data_for_quarters(selected_periods, query_params)
    period_col = 'Period'
    period_labels = [get_quarter_label(year, quarter) for year, quarter in selected_periods]
    
else:
    st.write("Please select at least one year or quarter.")
    st.stop()

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

    # Prepare columns for period-specific charts
    cols = st.columns(len(period_labels))

    # Calculate the global max percentage for uniform y-axis range
    max_percentage = 0
    valid_periods_for_max = []
    for period in period_labels:
        if not all_data[all_data[period_col] == period].empty:
            valid_periods_for_max.append(period)

    if valid_periods_for_max:
        max_percentage = max(
            calculate_domain_percentage(all_data, period_col, period)['Percentage'].max() for period in valid_periods_for_max
        )
    else:
        max_percentage = 100  # Default if no data exists for any selected period

    # Display period charts
    for idx, period in enumerate(period_labels):
        period_data = all_data[all_data[period_col] == period]
        if not period_data.empty:
            domain_counts_period = calculate_domain_percentage(all_data, period_col, period)
            if not domain_counts_period.empty:
                fig_period = create_period_percentage_chart(domain_counts_period, period, max_percentage)
                cols[idx].plotly_chart(fig_period)
            else:
                cols[idx].write(f"No domain data to display for {period}.")
        else:
            cols[idx].write(f"No data available for {period}.")
    
    # Generate markdown report
    md_content = generate_domains_markdown_report(all_data, period_col, period_labels)
    render_download_button(md_content, "domains_report.md", "Download Domains Report")

else:
    st.write("No data available for the selected periods.")