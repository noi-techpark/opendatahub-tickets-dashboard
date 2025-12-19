# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later


import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from utils import fetch_data, render_time_filter, filter_df_by_quarter, get_quarter_label, is_download_enabled, format_ticket_link_markdown, render_download_button

# Constants
DEFAULT_START_YEAR = 2019
DATE_FORMAT = '%a %b %d %H:%M:%S %Y'
MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MONTH_MAP = {i+1: month for i, month in enumerate(MONTH_ORDER)}

# Fetch and process data for the selected years
def fetch_and_process_data_years(selected_years, config):
    monthly_ticket_data, owner_data_list, yearly_ticket_counts = [], [], []
    all_dfs = {}

    for year in selected_years:
        df = fetch_data_for_year(year, config)
        if not df.empty:
            df = process_year_data(df)
            all_dfs[year] = df.copy()
            owner_data_list.append(df[['Owner']].copy())
            monthly_ticket_data.append(calculate_monthly_ticket_counts(df))
            yearly_ticket_counts.append(calculate_yearly_ticket_counts(df))
    
    return (
        pd.concat(monthly_ticket_data, ignore_index=True) if monthly_ticket_data else pd.DataFrame(),
        pd.concat(yearly_ticket_counts, ignore_index=True).groupby('Year').sum().reset_index() if yearly_ticket_counts else pd.DataFrame(),
        pd.concat(owner_data_list, ignore_index=True) if owner_data_list else pd.DataFrame(),
        all_dfs
    )


# Fetch and process data for the selected quarters
def fetch_and_process_data_quarters(quarter_periods, config):
    monthly_ticket_data, owner_data_list, quarterly_ticket_counts = [], [], []
    all_dfs = {}
    
    # Group by year to minimize fetches
    years_needed = set(year for year, _ in quarter_periods)
    year_data_cache = {}
    
    for year in years_needed:
        df = fetch_data_for_year(year, config)
        year_data_cache[year] = df
    
    for year, quarter in quarter_periods:
        df = year_data_cache.get(year, pd.DataFrame())
        if not df.empty:
            df_quarter = filter_df_by_quarter(df, year, quarter)
            if not df_quarter.empty:
                df_quarter = df_quarter.copy()
                label = get_quarter_label(year, quarter)
                df_quarter['Period'] = label
                df_quarter['Month'] = df_quarter['Created'].dt.month
                
                all_dfs[label] = df_quarter.copy()
                owner_data_list.append(df_quarter[['Owner']].copy())
                
                # Monthly counts within the quarter
                monthly_counts = df_quarter.groupby(['Period', 'Month'], as_index=False).agg({'Created': 'size'})
                monthly_counts.columns = ['Period', 'Month', 'Ticket Count']
                monthly_ticket_data.append(monthly_counts)
                
                # Total for the quarter
                quarterly_ticket_counts.append({
                    'Period': label,
                    'Ticket Count': len(df_quarter)
                })
    
    return (
        pd.concat(monthly_ticket_data, ignore_index=True) if monthly_ticket_data else pd.DataFrame(),
        pd.DataFrame(quarterly_ticket_counts) if quarterly_ticket_counts else pd.DataFrame(),
        pd.concat(owner_data_list, ignore_index=True) if owner_data_list else pd.DataFrame(),
        all_dfs
    )


# Fetch data for a specific year
def fetch_data_for_year(year, config):
    query_params = config['idm_tickets']['query_parameters']
    df = fetch_data(year, query_params['query'], query_params['fields'])
    if not df.empty and 'Created' in df.columns:
        df['Created'] = pd.to_datetime(df['Created'], format=DATE_FORMAT, errors='coerce')
    return df

# Process year data: add 'Year' and 'Month' columns
def process_year_data(df):
    df['Year'] = df['Created'].dt.year.astype(int)
    df['Month'] = df['Created'].dt.month
    return df

# Calculate monthly ticket counts
def calculate_monthly_ticket_counts(df):
    monthly_counts = df.groupby(['Year', 'Month'], as_index=False).agg({'Created': 'size'})
    monthly_counts.columns = ['Year', 'Month', 'Ticket Count']
    return monthly_counts

# Calculate yearly ticket counts
def calculate_yearly_ticket_counts(df):
    yearly_counts = df.groupby('Year', as_index=False).agg({'Created': 'size'})
    yearly_counts.columns = ['Year', 'Ticket Count']
    return yearly_counts

# Plot the distribution of ticket owners
def plot_owner_distribution(df):
    st.subheader("Owner Distribution")
    if df.empty or 'Owner' not in df.columns:
        st.error("The 'Owner' column is missing from the data.")
        return

    owner_counts = df['Owner'].value_counts().reset_index()
    owner_counts.columns = ['Owner', 'Ticket Count']
    fig = px.pie(owner_counts, hole=0.4, values='Ticket Count', names='Owner', title='Ticket Distribution by Owner')
    st.plotly_chart(fig)

# Plot the number of tickets created per month for each selected year
def plot_monthly_tickets_years(data, selected_years):
    st.subheader("Number of Tickets Created Per Month Per Year")
    pivot_table = prepare_monthly_pivot_table_years(data)
    
    # Convert the pivot table to Plotly-friendly format and plot using Plotly Express
    fig = px.bar(
        pivot_table.reset_index(), 
        x='Month', 
        y=pivot_table.columns.tolist(), 
        barmode='group',
        labels={'value': 'Ticket Count'}, 
        title="Monthly Ticket Count by Year"
    )
    
    st.plotly_chart(fig)


# Plot the number of tickets created per month for each selected quarter
def plot_monthly_tickets_quarters(data, quarter_periods):
    if data.empty:
        st.warning("No data available for the selected quarters.")
        return
    
    st.subheader("Number of Tickets Created Per Month Per Quarter")
    
    pivot_table = data.pivot(index='Month', columns='Period', values='Ticket Count').fillna(0)
    pivot_table.index = pivot_table.index.map(MONTH_MAP)
    pivot_table.index = pd.CategoricalIndex(pivot_table.index, categories=MONTH_ORDER, ordered=True)
    pivot_table = pivot_table.sort_index()
    
    fig = px.bar(
        pivot_table.reset_index(), 
        x='Month', 
        y=pivot_table.columns.tolist(), 
        barmode='group',
        labels={'value': 'Ticket Count'}, 
        title="Monthly Ticket Count by Quarter"
    )
    
    st.plotly_chart(fig)


# Prepare pivot table for monthly ticket data (years mode)
def prepare_monthly_pivot_table_years(data):
    pivot_table = data.pivot(index='Month', columns='Year', values='Ticket Count').fillna(0)
    pivot_table.index = pivot_table.index.map(MONTH_MAP)
    pivot_table.index = pd.CategoricalIndex(pivot_table.index, categories=MONTH_ORDER, ordered=True)
    return pivot_table.sort_index()

# Plot the total number of tickets per year
def plot_yearly_trend(data):
    if data.empty:
        return
    st.subheader("Total Number of Tickets Per Year")
    
    fig = px.bar(
        data, 
        x='Year', 
        y='Ticket Count', 
        labels={'Ticket Count': 'Total Tickets'}, 
        title='Total Tickets Per Year'
    )
    st.plotly_chart(fig)


# Plot the total number of tickets per quarter
def plot_quarterly_trend(data):
    if data.empty:
        return
    st.subheader("Total Number of Tickets Per Quarter")
    
    fig = px.bar(
        data, 
        x='Period', 
        y='Ticket Count', 
        labels={'Ticket Count': 'Total Tickets'}, 
        title='Total Tickets Per Quarter'
    )
    st.plotly_chart(fig)


# Display a heatmap-like table of monthly ticket counts per year/quarter with a black-and-white color scheme
def display_heatmap_table(data, mode='years'):
    if data.empty:
        return
    
    if mode == 'years':
        st.subheader("Heatmap of Monthly Ticket Counts Per Year")
        pivot_col = 'Year'
    else:
        st.subheader("Heatmap of Monthly Ticket Counts Per Quarter")
        pivot_col = 'Period'
    
    heatmap_data = prepare_heatmap_data(data, pivot_col)
    
    year_columns = heatmap_data.columns.drop('Month')
    if mode == 'years':
        heatmap_data[year_columns] = heatmap_data[year_columns].astype(int)

    # Sort the columns and ensure correct ordering
    heatmap_data = heatmap_data.set_index('Month').sort_index(axis=1)

    # Create a heatmap using Plotly
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns.astype(str),
        y=heatmap_data.index,
        colorscale='Greys',
        hoverongaps=False
    ))

    fig.update_layout(
        title='Monthly Ticket Count Heatmap',
        xaxis_title=pivot_col,
        yaxis_title='Month',
        xaxis=dict(
            tickmode='linear',
            dtick=1
        )
    )

    st.plotly_chart(fig)


# Prepare heatmap data
def prepare_heatmap_data(data, pivot_col='Year'):
    heatmap_data = data.pivot_table(index='Month', columns=pivot_col, values='Ticket Count', aggfunc='sum', fill_value=0)
    heatmap_data.index = heatmap_data.index.map(MONTH_MAP)
    heatmap_data.index = pd.CategoricalIndex(heatmap_data.index, categories=MONTH_ORDER, ordered=True)
    return heatmap_data.sort_index().reset_index()


def generate_idm_markdown_report(all_dfs):
    """Generate a markdown report for IDM tickets."""
    lines = []
    lines.append("# IDM Tickets Overview Report\n")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    for period in sorted(all_dfs.keys(), key=lambda x: str(x)):
        df = all_dfs[period]
        lines.append(f"## {period}\n")
        
        if df.empty:
            lines.append("No data for this period.\n")
            continue
        
        lines.append(f"**Total Tickets:** {len(df)}\n")
        
        # Group by owner
        if 'Owner' in df.columns:
            lines.append("### By Owner\n")
            for owner in sorted(df['Owner'].dropna().unique()):
                owner_df = df[df['Owner'] == owner]
                lines.append(f"#### {owner} ({len(owner_df)} tickets)")
                
                # Get ticket IDs
                lower_cols = [col.lower() for col in df.columns]
                if "id" in lower_cols:
                    id_col = [col for col in df.columns if col.lower() == "id"][0]
                    for tid in owner_df[id_col].tolist():
                        lines.append(f"- {format_ticket_link_markdown(tid)}")
                lines.append("")
        
        lines.append("")
    
    return "\n".join(lines)


# Load configuration
config = st.session_state.config

# Streamlit UI
st.title("IDM Tickets Overview")

# Text of this Page
st.markdown(config['idm_tickets']['markdown_text']['additional_info'])

# Use the unified time filter component
filter_mode, selected_periods = render_time_filter()

# Load and process the data
if filter_mode == 'years' and selected_periods:
    combined_monthly_df, combined_yearly_df, combined_owner_df, all_dfs = fetch_and_process_data_years(selected_periods, config)

    # Plot the owner distribution pie chart
    # plot_owner_distribution(combined_owner_df)

    # Plot the monthly ticket data
    if not combined_monthly_df.empty:
        plot_monthly_tickets_years(combined_monthly_df, selected_periods)

        # Display the heatmap-like table
        display_heatmap_table(combined_monthly_df, mode='years')

    # Plot the yearly trend
    plot_yearly_trend(combined_yearly_df)
    
    # Download button
    if all_dfs:
        md_content = generate_idm_markdown_report(all_dfs)
        render_download_button(md_content, "idm_tickets_report.md", "Download IDM Tickets Report")

elif filter_mode == 'quarters' and selected_periods:
    combined_monthly_df, combined_quarterly_df, combined_owner_df, all_dfs = fetch_and_process_data_quarters(selected_periods, config)

    # Plot the owner distribution pie chart
    # plot_owner_distribution(combined_owner_df)

    # Plot the monthly ticket data by quarter
    if not combined_monthly_df.empty:
        plot_monthly_tickets_quarters(combined_monthly_df, selected_periods)

        # Display the heatmap-like table
        display_heatmap_table(combined_monthly_df, mode='quarters')

    # Plot the quarterly trend
    plot_quarterly_trend(combined_quarterly_df)
    
    # Download button
    if all_dfs:
        md_content = generate_idm_markdown_report(all_dfs)
        render_download_button(md_content, "idm_tickets_report.md", "Download IDM Tickets Report")

else:
    st.write("Please select at least one year or quarter.")
