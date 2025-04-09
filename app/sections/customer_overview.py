# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import streamlit as st
import pandas as pd
import plotly.express as px
from collections import defaultdict
import datetime
from utils import fetch_data


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

# Helper function to generate Markdown report per year with all ticket IDs by company
def generate_markdown_report(dfs_by_year, company_field="CF.{Company name}"):
    lines = []
    for year in sorted(dfs_by_year.keys()):
        df = dfs_by_year[year]
        lines.append(f"## {year}\n")
        if company_field not in df.columns:
            lines.append("Company field not found\n")
        else:
            # Group by company name
            groups = df.groupby(company_field)
            for company, group in groups:
                lines.append(f"### {company}")
                # Check for ticket id column in a case-insensitive way
                lower_cols = [col.lower() for col in df.columns]
                if "id" in lower_cols:
                    id_col = [col for col in df.columns if col.lower() == "id"][0]
                    ticket_ids = group[id_col].tolist()
                    if ticket_ids:
                        for tid in ticket_ids:
                            lines.append(f"- {tid}")
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

current_year = datetime.datetime.now().year
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(2019, current_year+1)), 
    default=[current_year-2, current_year-1, current_year]
)
selected_years.sort()

# Fetch and process data for each selected year
all_companies = {}
dfs_by_year = {}
max_companies = 1
for year in selected_years:
    df = fetch_data(year, config['customers_overview']['query_parameters']['query'], config['customers_overview']['query_parameters']['fields'])
    dfs_by_year[year] = df.copy()  # store full dataframe for the markdown download
    companies = process_companies_data(df)
    all_companies[year] = companies
    max_companies = max(max_companies, len(companies))

# User input for number of top companies to display
top_n = st.slider("Number of top companies to display", 1, max_companies, 3)

# Display data for each selected year
data_columns = st.columns(len(selected_years))
for idx, year in enumerate(selected_years):
    with data_columns[idx]:
        st.subheader(f"{year}")

        companies = all_companies[year]
        total_tickets = sum(companies.values())
        total_companies = len(companies)

        st.write(f"Tickets: **{total_tickets}**")
        st.write(f"Companies: **{total_companies}**")

        df_top = prepare_top_companies(companies, top_n)

        # Create a pie chart using Plotly
        fig = px.pie(df_top, values='Tickets', names='Company', title=f'Top {top_n} Companies in {year}')
        st.plotly_chart(fig)

        st.subheader("Top Companies")
        st.dataframe(df_top, hide_index=True)

        st.subheader("All Companies")
        all_companies_df = pd.DataFrame(list(companies.items()), columns=["Company", "Tickets"]).sort_values(by="Company")
        st.dataframe(all_companies_df, hide_index=True)

# Generate markdown content and provide download button
md_content = generate_markdown_report(dfs_by_year)
st.download_button(
    label="Download Markdown Report with Ticket IDs",
    data=md_content,
    file_name="ticket_ids_report.md",
    mime="text/markdown"
)
