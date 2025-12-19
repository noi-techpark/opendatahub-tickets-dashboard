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

# Function to create a combined pie chart for multiple periods
def create_combined_pie_chart(all_data, column_name, title, hole_size=0.4):
    combined_df = pd.concat(all_data, ignore_index=True)
    return create_pie_chart(combined_df, column_name, title, hole_size)


# Apply IDM logic to dataframe
def apply_idm_logic(df):
    if not df.empty and 'Queue' in df.columns:
        # Create the mask and add fields for rows where Queue is 'IDM'
        idm_mask = df['Queue'].astype(str).fillna('') == 'IDM'
        if 'CF.{Type of requestor}' in df.columns:
            df.loc[idm_mask, 'CF.{Type of requestor}'] = 'IDM'
        if 'CF.{Requestor use case}' in df.columns:
            df.loc[idm_mask, 'CF.{Requestor use case}'] = 'Data consumer'
        if 'CF.{Company type}' in df.columns:
            df.loc[idm_mask, 'CF.{Company type}'] = 'Publicly held'
    return df


# Streamlit UI to display data and charts
def display_combined_view(all_data):
    st.markdown("## Combined Pie Charts for All Periods")
    st.plotly_chart(create_combined_pie_chart(all_data, 'CF.{Type of requestor}', "Type of Requestor"))
    st.markdown(config['requestors']['markdown_text']['chart01'])
    st.plotly_chart(create_combined_pie_chart(all_data, 'CF.{Requestor use case}', "Requestor Use Case"))
    st.markdown(config['requestors']['markdown_text']['chart02'])
    st.plotly_chart(create_combined_pie_chart(all_data, 'CF.{Company type}', "Company Type"))
    st.markdown(config['requestors']['markdown_text']['chart03'])


def display_period_view(all_data, period_labels):
    st.markdown("## Pie Charts for Selected Periods")

    # First display all "Type of Requestor" charts for each period
    st.markdown("### Type of Requestor")
    data_columns = st.columns(len(period_labels))
    for idx, period in enumerate(period_labels):
        df = all_data[idx]
        with data_columns[idx]:
            st.subheader(f"{period}")
            if df.empty:
                st.write("No data available for this period.")
            else:
                st.plotly_chart(create_pie_chart(df, 'CF.{Type of requestor}', f"Type of Requestor"))

    # Display the markdown text for "Type of Requestor"
    st.markdown(config['requestors']['markdown_text']['chart01'])

    # Next display all "Requestor Use Case" charts for each period
    st.markdown("### Requestor Use Case")
    data_columns = st.columns(len(period_labels))
    for idx, period in enumerate(period_labels):
        df = all_data[idx]
        with data_columns[idx]:
            st.subheader(f"{period}")
            if df.empty:
                st.write("No data available for this period.")
            else:
                st.plotly_chart(create_pie_chart(df, 'CF.{Requestor use case}', f"Requestor Use Case"))

    # Display the markdown text for "Requestor Use Case"
    st.markdown(config['requestors']['markdown_text']['chart02'])

    # Finally, display all "Company Type" charts for each period
    st.markdown("### Company Type")
    data_columns = st.columns(len(period_labels))
    for idx, period in enumerate(period_labels):
        df = all_data[idx]
        with data_columns[idx]:
            st.subheader(f"{period}")
            if df.empty:
                st.write("No data available for this period.")
            else:
                st.plotly_chart(create_pie_chart(df, 'CF.{Company type}', f"Company Type"))

    # Display the markdown text for "Company Type"
    st.markdown(config['requestors']['markdown_text']['chart03'])


config = st.session_state.config

st.title("Requestors Overview")

# Text of this Page
st.markdown(config['requestors']['markdown_text']['additional_info'])

# Use the unified time filter component
filter_mode, selected_periods = render_time_filter()

# Checkbox to select between two query parameters
use_alternate_query = st.checkbox(config['requestors']['markdown_text']['text_button'])

# Determine query parameters based on the checkbox
query_params_key = 'query_parameters_2' if use_alternate_query else 'query_parameters_1'
# Make a copy to avoid modifying the cached config
query_params = config['requestors'][query_params_key].copy()

# Fetch data based on filter mode
all_data = []
period_labels = []

if filter_mode == 'years' and selected_periods:
    period_labels = selected_periods
    
    for year in selected_periods:
        df = fetch_and_process_data(year, query_params)
        df = apply_idm_logic(df)
        all_data.append(df)

elif filter_mode == 'quarters' and selected_periods:
    # Group by year to minimize fetches
    years_needed = set(year for year, _ in selected_periods)
    year_data_cache = {}
    
    for year in years_needed:
        df = fetch_and_process_data(year, query_params)
        if not df.empty and 'Created' in df.columns:
            df['Created'] = pd.to_datetime(df['Created'], format=DATE_FORMAT, errors='coerce')
        year_data_cache[year] = df
    
    for year, quarter in selected_periods:
        label = get_quarter_label(year, quarter)
        period_labels.append(label)
        
        df = year_data_cache.get(year, pd.DataFrame())
        if not df.empty:
            df_quarter = filter_df_by_quarter(df, year, quarter)
            df_quarter = apply_idm_logic(df_quarter)
            all_data.append(df_quarter)
        else:
            all_data.append(pd.DataFrame())

else:
    st.warning("Please select at least one year or quarter.")
    st.stop()

if not all_data:
    st.warning("No data available for the selected periods.")
    st.stop()

# Toggle to switch between "Combined" and "Period" views
view_switch = st.radio("Select View:", ["Combined View", "Period View"])

# Display combined or period data based on the toggle
if view_switch == "Combined View":
    display_combined_view(all_data)
else:
    display_period_view(all_data, period_labels)

# Generate markdown report
def generate_requestors_markdown_report(all_data, period_labels):
    """Generate a markdown report for requestors."""
    lines = []
    lines.append("# Requestors Overview Report\n")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    for idx, period in enumerate(period_labels):
        df = all_data[idx] if idx < len(all_data) else pd.DataFrame()
        lines.append(f"## {period}\n")
        
        if df.empty:
            lines.append("No data for this period.\n")
            continue
        
        lines.append(f"**Total Tickets:** {len(df)}\n")
        
        # By Type of Requestor
        if 'CF.{Type of requestor}' in df.columns:
            lines.append("### By Type of Requestor\n")
            for req_type in sorted(df['CF.{Type of requestor}'].dropna().unique()):
                type_df = df[df['CF.{Type of requestor}'] == req_type]
                lines.append(f"#### {req_type} ({len(type_df)} tickets)")
                
                lower_cols = [col.lower() for col in df.columns]
                if "id" in lower_cols:
                    id_col = [col for col in df.columns if col.lower() == "id"][0]
                    for tid in type_df[id_col].tolist():
                        lines.append(f"- {format_ticket_link_markdown(tid)}")
                lines.append("")
        
        # By Use Case
        if 'CF.{Requestor use case}' in df.columns:
            lines.append("### By Requestor Use Case\n")
            for use_case in sorted(df['CF.{Requestor use case}'].dropna().unique()):
                case_df = df[df['CF.{Requestor use case}'] == use_case]
                lines.append(f"#### {use_case} ({len(case_df)} tickets)")
                
                lower_cols = [col.lower() for col in df.columns]
                if "id" in lower_cols:
                    id_col = [col for col in df.columns if col.lower() == "id"][0]
                    for tid in case_df[id_col].tolist():
                        lines.append(f"- {format_ticket_link_markdown(tid)}")
                lines.append("")
        
        lines.append("")
    
    return "\n".join(lines)

md_content = generate_requestors_markdown_report(all_data, period_labels)
render_download_button(md_content, "requestors_report.md", "Download Requestors Report")