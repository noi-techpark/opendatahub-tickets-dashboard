# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later


import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import holidays
from utils import fetch_data

# Constants for response time categories
RESPONSE_CATEGORIES = ["Within first hour", "Within first day", "Within first 2 days", "Within first week", "More than a week", "Not set"]
DATE_FORMAT = '%a %b %d %H:%M:%S %Y'
HOURS_IN_A_DAY = 24
HOURS_IN_A_WEEK = 7 * HOURS_IN_A_DAY

# Helper function to compute business hours (excluding weekends and Italian public holidays)
def compute_business_hours(start, end):
    # If either timestamp is missing, return NaN so that later we mark it as "Not set"
    if pd.isna(start) or pd.isna(end):
        return float('nan')
    if start >= end:
        return 0
    # Create a set of Italian holidays for all years in the interval
    years = list(range(start.year, end.year + 1))
    italian_holidays = holidays.Italy(years=years)
    
    total_minutes = 0
    # If both timestamps are on the same day
    if start.date() == end.date():
        if start.weekday() < 5 and start.date() not in italian_holidays:
            diff_minutes = (end - start).total_seconds() / 60
            total_minutes = diff_minutes
        return total_minutes / 60.0

    # Calculate minutes for the first day (from start time to midnight)
    first_day = start.date()
    if start.weekday() < 5 and first_day not in italian_holidays:
        end_of_day = datetime.datetime.combine(first_day + datetime.timedelta(days=1), datetime.time.min)
        diff_minutes = (end_of_day - start).total_seconds() / 60
        total_minutes += diff_minutes

    # Calculate minutes for the last day (from midnight to end time)
    last_day = end.date()
    if end.weekday() < 5 and last_day not in italian_holidays:
        start_of_day = datetime.datetime.combine(last_day, datetime.time.min)
        diff_minutes = (end - start_of_day).total_seconds() / 60
        total_minutes += diff_minutes

    # Sum full days in between
    day = start.date() + datetime.timedelta(days=1)
    while day < end.date():
        # If day is a weekday and not a holiday, add full day minutes
        if day.weekday() < 5 and day not in italian_holidays:
            total_minutes += 24 * 60
        day += datetime.timedelta(days=1)
    
    return total_minutes / 60.0

# Data processing function to calculate response time categories
def categorize_response_times(df, started_field="Started", created_field="Created"):
    # Parse datetime fields
    df[started_field] = pd.to_datetime(df[started_field], format=DATE_FORMAT, errors='coerce')
    df[created_field] = pd.to_datetime(df[created_field], format=DATE_FORMAT, errors='coerce')

    # Calculate response times in business hours (excluding weekends and Italian holidays)
    df['ResponseTime'] = df.apply(lambda row: compute_business_hours(row[created_field], row[started_field]), axis=1)

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
                category: (response_counts.get(category, 0) / response_counts.sum()) * 100
                for category in RESPONSE_CATEGORIES
            }
        }
        for year, response_counts in all_data.items()
    ]
    return stacked_data

# Helper function to generate Markdown report per year, per category listing Ticket IDs
def generate_markdown_report(dfs_by_year):
    lines = []
    for year in sorted(dfs_by_year.keys()):
        df = dfs_by_year[year]
        lines.append(f"## {year}\n")
        # Make a lowercase list of column names to allow case-insensitive search
        lower_cols = [col.lower() for col in df.columns]
        if "id" in lower_cols:
            # Get the original column name (in case the case is different)
            id_col = [col for col in df.columns if col.lower() == "id"][0]
        else:
            id_col = None

        for category in RESPONSE_CATEGORIES:
            lines.append(f"### {category}")
            if id_col is not None:
                ticket_ids = df.loc[df['ResponseCategory'] == category, id_col].tolist()
                if ticket_ids:
                    for tid in ticket_ids:
                        lines.append(f"- {tid}")
                else:
                    lines.append("- No tickets")
            else:
                lines.append("- Ticket ID column not found")
            lines.append("")  # Blank line for spacing
    return "\n".join(lines)

# Load configuration
config = st.session_state.config

st.title("Response Times")

# Text of this Page
st.markdown(config['response_time']['markdown_text']['additional_info'])

# Select years
current_year = datetime.datetime.now().year
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(2019, current_year + 1)), 
    default=[current_year-2, current_year-1, current_year]
)
selected_years.sort()

# Always use query_parameters_1
query_params = config['response_time']['query_parameters_1']

# Dictionaries to store data for plots and markdown report
all_data = {}
dfs_by_year = {}

data_columns = st.columns(len(selected_years))
for idx, year in enumerate(selected_years):
    df = fetch_and_process_data(year, query_params)
    dfs_by_year[year] = df  # Store full dataframe for the markdown download
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

# Generate markdown content and provide download button
if dfs_by_year:
    md_content = generate_markdown_report(dfs_by_year)
    st.download_button(
        label="Download Markdown Report",
        data=md_content,
        file_name="ticket_data.md",
        mime="text/markdown"
    )