# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import streamlit as st
import pandas as pd
import plotly.express as px
from collections import defaultdict
import datetime
from utils import fetch_data, render_time_filter, filter_df_by_quarter, get_quarter_label, is_download_enabled, format_ticket_link_markdown, render_download_button


# Data processing functions
def process_companies_data(df, company_field="CF.{Company name}"):
    companies = defaultdict(int)
    for company in df[company_field].dropna():
        companies[company] += 1
    return companies

def prepare_top_companies(companies, top_n):
    return pd.DataFrame(
        sorted(companies.items(), key=lambda x: x[1], reverse=True)[:top_n],
        columns=["Company", "Tickets"]
    )

START_YEAR = 2018

def fetch_all_previous_companies(period_struct, filter_mode, config):
    query = config['customers_overview']['query_parameters']['query']
    fields = config['customers_overview']['query_parameters']['fields']
    previous_companies = set()
    
    if filter_mode == 'years':
        current_year = period_struct
        # Fetch for all previous years
        for year in range(START_YEAR, current_year):
            df = fetch_data(year, query, fields)
            if not df.empty:
                previous_companies.update(process_companies_data(df).keys())
                
    elif filter_mode == 'quarters':
        current_year, current_quarter = period_struct
        
        # 1. Fetch for all previous years
        for year in range(START_YEAR, current_year):
            df = fetch_data(year, query, fields)
            if not df.empty:
                previous_companies.update(process_companies_data(df).keys())
        
        # 2. Fetch for current year, previous quarters
        if current_quarter > 1:
            df = fetch_data(current_year, query, fields)
            if not df.empty and 'Created' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['Created']):
                     df['Created'] = pd.to_datetime(df['Created'], format='%a %b %d %H:%M:%S %Y', errors='coerce')
                
                # Filter for months before the current quarter
                # Q1: 1-3, Q2: 4-6, Q3: 7-9, Q4: 10-12
                # Start month of current quarter is (current_quarter - 1) * 3 + 1
                start_month_current = (current_quarter - 1) * 3 + 1
                df_prev = df[df['Created'].dt.month < start_month_current]
                previous_companies.update(process_companies_data(df_prev).keys())

    return previous_companies

# Helper function to generate Markdown report per year with all ticket IDs by company
def generate_markdown_report(dfs_by_period, company_field="CF.{Company name}"):
    lines = []
    lines.append("# Customer Overview Report\n")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    for period in sorted(dfs_by_period.keys(), key=lambda x: str(x)):
        df = dfs_by_period[period]
        lines.append(f"## {period}\n")
        if df.empty:
            lines.append("No data for this period.\n")
            continue
            
        if company_field not in df.columns:
            lines.append("Company field not found\n")
        else:
            # Group by company name
            groups = df.groupby(company_field)
            for company, group in sorted(groups, key=lambda x: x[0]):
                lines.append(f"### {company} ({len(group)} tickets)")
                # Check for ticket id column in a case-insensitive way
                lower_cols = [col.lower() for col in df.columns]
                if "id" in lower_cols:
                    id_col = [col for col in df.columns if col.lower() == "id"][0]
                    ticket_ids = group[id_col].tolist()
                    if ticket_ids:
                        for tid in ticket_ids:
                            lines.append(f"- {format_ticket_link_markdown(tid)}")
                    else:
                        lines.append("- No tickets")
                else:
                    lines.append("- Ticket ID column not found")
                lines.append("")  # blank line for spacing
    return "\n".join(lines)

# Load the configuration
config = st.session_state.config

st.title("Customer Overview")

# Text of this Page
st.markdown(config['customers_overview']['markdown_text']['additional_info'])

# Use the unified time filter component
filter_mode, selected_periods = render_time_filter()

# Fetch and process data
all_companies = {}
dfs_by_period = {}
max_companies = 1

if filter_mode == 'years' and selected_periods:
    for year in selected_periods:
        df = fetch_data(year, config['customers_overview']['query_parameters']['query'], config['customers_overview']['query_parameters']['fields'])
        dfs_by_period[year] = df.copy()
        companies = process_companies_data(df)
        all_companies[year] = companies
        max_companies = max(max_companies, len(companies))
    
    period_labels = selected_periods

elif filter_mode == 'quarters' and selected_periods:
    # Group by year to minimize fetches
    years_needed = set(year for year, _ in selected_periods)
    year_data_cache = {}
    
    for year in years_needed:
        df = fetch_data(year, config['customers_overview']['query_parameters']['query'], config['customers_overview']['query_parameters']['fields'])
        if not df.empty and 'Created' in df.columns:
            df['Created'] = pd.to_datetime(df['Created'], format='%a %b %d %H:%M:%S %Y', errors='coerce')
        year_data_cache[year] = df
    
    period_labels = []
    for year, quarter in selected_periods:
        label = get_quarter_label(year, quarter)
        period_labels.append(label)
        df = year_data_cache.get(year, pd.DataFrame())
        if not df.empty and 'Created' in df.columns:
            df_quarter = filter_df_by_quarter(df, year, quarter)
            dfs_by_period[label] = df_quarter.copy()
            companies = process_companies_data(df_quarter)
            all_companies[label] = companies
            max_companies = max(max_companies, len(companies))
        else:
            dfs_by_period[label] = pd.DataFrame()
            all_companies[label] = {}

else:
    st.warning("Please select at least one year or quarter.")
    st.stop()

if not all_companies:
    st.warning("No data available for the selected periods.")
    st.stop()

# User input for number of top companies to display
top_n = st.slider("Number of top companies to display", 1, max(max_companies, 1), 3)

# Display data for each selected period
data_columns = st.columns(len(period_labels))
for idx, period in enumerate(period_labels):
    with data_columns[idx]:
        st.subheader(f"{period}")

        companies = all_companies.get(period, {})
        total_tickets = sum(companies.values())
        total_companies = len(companies)

        # st.write(f"Tickets: **{total_tickets}**")
        st.write(f"Customer: **{total_companies}**")

        # Calculate new companies since ALL previous timeframes
        current_struct = selected_periods[idx]
        prev_companies_set = fetch_all_previous_companies(current_struct, filter_mode, config)
        current_companies_set = set(companies.keys())
        new_companies = current_companies_set - prev_companies_set
        st.write(f"New Customer: **{len(new_companies)}**")

        if companies:
            df_top = prepare_top_companies(companies, top_n)

            # Create a pie chart using Plotly
            fig = px.pie(df_top, values='Tickets', names='Company', title=f'Top {top_n} Companies in {period}')
            st.plotly_chart(fig)

            st.subheader("Top Companies")
            st.dataframe(df_top, hide_index=True)

            st.subheader("All Companies")
            all_companies_df = pd.DataFrame(list(companies.items()), columns=["Company", "Tickets"]).sort_values(by="Company")
            st.dataframe(all_companies_df, hide_index=True)
        else:
            st.write("No data available for this period.")

# Generate markdown content and provide download button
md_content = generate_markdown_report(dfs_by_period)
render_download_button(md_content, "customer_report.md", "Download Customer Report")
