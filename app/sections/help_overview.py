# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from utils import fetch_data, render_time_filter, filter_df_by_quarter, get_quarter_label, is_download_enabled, format_ticket_link_markdown, render_download_button


def load_data_years(selected_years):
    """Load data for yearly filter mode."""
    # Initialize a list to hold the monthly ticket counts for each year
    monthly_ticket_data = []
    yearly_ticket_counts = []
    all_dfs = {}

    for year in selected_years:
        # Fetch data for the year
        df = fetch_data(year, config['help_overview']['query_parameters']['query'], config['help_overview']['query_parameters']['fields'])
        
        if not df.empty:
            # Ensure the "Created" column is in datetime format
            df['Created'] = pd.to_datetime(df['Created'], format='%a %b %d %H:%M:%S %Y')
            
            # Extract month and year from the "Created" column
            df['Year'] = df['Created'].dt.year
            df['Month'] = df['Created'].dt.month
            
            # Store raw data for report
            all_dfs[year] = df.copy()
            
            # Group by Year and Month, then count the number of tickets
            monthly_counts = df.groupby(['Year', 'Month']).size().reset_index(name='Ticket Count')
            yearly_count = df['Year'].value_counts().reset_index(name='Ticket Count')
            yearly_count.columns = ['Year', 'Ticket Count']
            
            # Append to the list
            monthly_ticket_data.append(monthly_counts)
            yearly_ticket_counts.append(yearly_count)
    
    # Concatenate all years' data into a single DataFrame
    combined_monthly_df = pd.concat(monthly_ticket_data, ignore_index=True) if monthly_ticket_data else pd.DataFrame()
    combined_yearly_df = pd.concat(yearly_ticket_counts, ignore_index=True).groupby('Year').sum().reset_index() if yearly_ticket_counts else pd.DataFrame()
    
    return combined_monthly_df, combined_yearly_df, all_dfs


def load_data_quarters(quarter_periods):
    """Load data for quarter filter mode."""
    quarterly_ticket_data = []
    quarterly_totals = []
    all_dfs = {}
    
    # Group by year to minimize fetches
    years_needed = set(year for year, _ in quarter_periods)
    year_data_cache = {}
    
    for year in years_needed:
        df = fetch_data(year, config['help_overview']['query_parameters']['query'], config['help_overview']['query_parameters']['fields'])
        if not df.empty:
            df['Created'] = pd.to_datetime(df['Created'], format='%a %b %d %H:%M:%S %Y')
        year_data_cache[year] = df
    
    for year, quarter in quarter_periods:
        df = year_data_cache.get(year, pd.DataFrame())
        if not df.empty:
            df_quarter = filter_df_by_quarter(df, year, quarter)
            if not df_quarter.empty:
                label = get_quarter_label(year, quarter)
                df_quarter['Quarter'] = label
                df_quarter['Month'] = df_quarter['Created'].dt.month
                
                # Store raw data for report
                all_dfs[label] = df_quarter.copy()
                
                # Monthly counts within the quarter
                monthly_counts = df_quarter.groupby(['Quarter', 'Month']).size().reset_index(name='Ticket Count')
                quarterly_ticket_data.append(monthly_counts)
                
                # Total for the quarter
                quarterly_totals.append({
                    'Quarter': label,
                    'Ticket Count': len(df_quarter)
                })
    
    combined_monthly_df = pd.concat(quarterly_ticket_data, ignore_index=True) if quarterly_ticket_data else pd.DataFrame()
    combined_quarterly_df = pd.DataFrame(quarterly_totals) if quarterly_totals else pd.DataFrame()
    
    return combined_monthly_df, combined_quarterly_df, all_dfs


def generate_markdown_report(dfs_by_period, period_totals):
    """Generate a markdown report with ticket counts and links."""
    lines = []
    lines.append("# Help Queue Overview Report\n")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    for period in sorted(dfs_by_period.keys(), key=lambda x: str(x)):
        df = dfs_by_period[period]
        lines.append(f"## {period}\n")
        
        if df.empty:
            lines.append("No tickets for this period.\n")
            continue
        
        total = len(df)
        lines.append(f"**Total Tickets:** {total}\n")
        
        # Group by month
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        if 'Month' in df.columns:
            for month_num in sorted(df['Month'].unique()):
                month_df = df[df['Month'] == month_num]
                month_name = month_names[int(month_num) - 1]
                lines.append(f"### {month_name} ({len(month_df)} tickets)\n")
                
                # Get ticket IDs
                lower_cols = [col.lower() for col in df.columns]
                if "id" in lower_cols:
                    id_col = [col for col in df.columns if col.lower() == "id"][0]
                    for tid in month_df[id_col].tolist():
                        lines.append(f"- {format_ticket_link_markdown(tid)}")
                lines.append("")
        
        lines.append("")
    
    return "\n".join(lines)


def plot_monthly_tickets(data, selected_years):
    """Displays a bar chart of the number of tickets created per month for each selected year."""
    st.subheader("Number of Tickets Created Per Month Per Year")

    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_map = {i+1: month for i, month in enumerate(month_order)}

    # Create a pivot table to organize data
    pivot_table = data.pivot(index='Month', columns='Year', values='Ticket Count').fillna(0)
    pivot_table.index = pivot_table.index.map(month_map)
    pivot_table.index = pd.CategoricalIndex(pivot_table.index, categories=month_order, ordered=True)
    pivot_table = pivot_table.sort_index()

    # Convert the pivot table to Plotly-friendly format and plot using Plotly Express
    fig = px.bar(
        pivot_table.reset_index(), 
        x='Month', 
        y=pivot_table.columns, 
        barmode='group',
        labels={'value': 'Ticket Count'}, 
        title="Monthly Ticket Count by Year"
    )
    
    st.plotly_chart(fig)


def plot_quarterly_tickets(data, quarter_periods):
    """Displays a bar chart of the number of tickets created per month for each selected quarter."""
    if data.empty:
        st.warning("No data available for the selected quarters.")
        return
    
    st.subheader("Number of Tickets Created Per Month Per Quarter")

    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_map = {i+1: month for i, month in enumerate(month_order)}

    # Create a pivot table to organize data
    pivot_table = data.pivot(index='Month', columns='Quarter', values='Ticket Count').fillna(0)
    pivot_table.index = pivot_table.index.map(month_map)
    pivot_table.index = pd.CategoricalIndex(pivot_table.index, categories=month_order, ordered=True)
    pivot_table = pivot_table.sort_index()

    # Convert the pivot table to Plotly-friendly format and plot using Plotly Express
    fig = px.bar(
        pivot_table.reset_index(), 
        x='Month', 
        y=pivot_table.columns.tolist(), 
        barmode='group',
        labels={'value': 'Ticket Count'}, 
        title="Monthly Ticket Count by Quarter"
    )
    
    st.plotly_chart(fig)


def plot_yearly_trend(data):
    """Displays a bar chart of the total number of tickets per year."""
    st.subheader("Total Number of Tickets Per Year")
    
    # Create a bar chart using Plotly Express
    fig = px.bar(
        data, 
        x='Year', 
        y='Ticket Count', 
        labels={'Ticket Count': 'Total Tickets'}, 
        title='Total Tickets Per Year'
    )
    
    st.plotly_chart(fig)


def plot_quarterly_trend(data):
    """Displays a bar chart of the total number of tickets per quarter."""
    if data.empty:
        return
    
    st.subheader("Total Number of Tickets Per Quarter")
    
    # Create a bar chart using Plotly Express
    fig = px.bar(
        data, 
        x='Quarter', 
        y='Ticket Count', 
        labels={'Ticket Count': 'Total Tickets'}, 
        title='Total Tickets Per Quarter'
    )
    
    st.plotly_chart(fig)


# Updated function to display a black-and-white heatmap
def display_heatmap_table(data, mode='years'):
    """Displays a heatmap-like table of monthly ticket counts per year/quarter using a black-and-white color scheme."""
    if mode == 'years':
        st.subheader("Heatmap of Monthly Ticket Counts Per Year")
        pivot_col = 'Year'
    else:
        st.subheader("Heatmap of Monthly Ticket Counts Per Quarter")
        pivot_col = 'Quarter'

    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_map = {i+1: month for i, month in enumerate(month_order)}

    # Create a pivot table to organize data
    heatmap_data = data.pivot_table(index='Month', columns=pivot_col, values='Ticket Count', aggfunc='sum', fill_value=0)
    heatmap_data.index = heatmap_data.index.map(month_map)
    heatmap_data.index = pd.CategoricalIndex(heatmap_data.index, categories=month_order, ordered=True)
    heatmap_data = heatmap_data.sort_index()

    # Use the black-and-white 'Greys' color scale for the heatmap
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='Greys',  # Black-and-white color scale
        hoverongaps=False
    ))

    fig.update_layout(
        title='Monthly Ticket Count Heatmap',
        xaxis_title=pivot_col,
        yaxis_title='Month'
    )

    st.plotly_chart(fig)

# Load the configuration
config = st.session_state.config

st.title("Help Queue Overview")

# Text of this Page
st.markdown(config['help_overview']['markdown_text']['additional_info'])

# Use the unified time filter component
filter_mode, selected_periods = render_time_filter()

if filter_mode == 'years' and selected_periods:
    # Load the data for years
    combined_monthly_df, combined_yearly_df, all_dfs = load_data_years(selected_periods)

    # Plot the monthly data
    if not combined_monthly_df.empty:
        plot_monthly_tickets(combined_monthly_df, selected_periods)

        # Display the heatmap-like table using black-and-white color scheme
        display_heatmap_table(combined_monthly_df, mode='years')

    # Plot the yearly trend
    if not combined_yearly_df.empty:
        plot_yearly_trend(combined_yearly_df)
    
    # Download button
    if all_dfs:
        md_content = generate_markdown_report(all_dfs, combined_yearly_df)
        render_download_button(md_content, "help_queue_report.md", "Download Help Queue Report")

elif filter_mode == 'quarters' and selected_periods:
    # Load the data for quarters
    combined_monthly_df, combined_quarterly_df, all_dfs = load_data_quarters(selected_periods)

    # Plot the monthly data by quarter
    if not combined_monthly_df.empty:
        plot_quarterly_tickets(combined_monthly_df, selected_periods)
        
        # Display the heatmap-like table using black-and-white color scheme
        display_heatmap_table(combined_monthly_df, mode='quarters')

    # Plot the quarterly trend
    plot_quarterly_trend(combined_quarterly_df)
    
    # Download button
    if all_dfs:
        md_content = generate_markdown_report(all_dfs, combined_quarterly_df)
        render_download_button(md_content, "help_queue_report.md", "Download Help Queue Report")

else:
    st.warning("Please select at least one year or quarter.")
