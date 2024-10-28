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
max_companies = 1
for year in selected_years:
    df = fetch_data(year, config['customers_overview']['query_parameters']['query'], config['customers_overview']['query_parameters']['fields'])
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
        st.table(df_top)

        st.subheader("All Companies")
        st.table(pd.DataFrame(list(companies.items()), columns=["Company", "Tickets"]).sort_values(by="Company"))


