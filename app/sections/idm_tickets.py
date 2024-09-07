import streamlit as st
import pandas as pd
import yaml
import datetime
import plotly.express as px
import plotly.graph_objects as go
from utils import fetch_data

# Constants
DEFAULT_START_YEAR = 2019
DATE_FORMAT = '%a %b %d %H:%M:%S %Y'
MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MONTH_MAP = {i+1: month for i, month in enumerate(MONTH_ORDER)}

# Load configuration from the config.yaml file
def load_config(config_file="config.yaml"):
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

# Fetch and process data for the selected years
def fetch_and_process_data(selected_years, config):
    monthly_ticket_data, owner_data_list, yearly_ticket_counts = [], [], []

    for year in selected_years:
        df = fetch_data_for_year(year, config)
        if not df.empty:
            df = process_year_data(df)
            owner_data_list.append(df[['Owner']].copy())
            monthly_ticket_data.append(calculate_monthly_ticket_counts(df))
            yearly_ticket_counts.append(calculate_yearly_ticket_counts(df))
    
    return (
        pd.concat(monthly_ticket_data, ignore_index=True),
        pd.concat(yearly_ticket_counts, ignore_index=True).groupby('Year').sum().reset_index(),
        pd.concat(owner_data_list, ignore_index=True)
    )

# Fetch data for a specific year
def fetch_data_for_year(year, config):
    query_params = config['idm_tickets']['query_parameters']
    df = fetch_data(year, query_params['query'], query_params['fields'])
    df['Created'] = pd.to_datetime(df['Created'], format=DATE_FORMAT)
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
    if 'Owner' not in df.columns:
        st.error("The 'Owner' column is missing from the data.")
        return

    owner_counts = df['Owner'].value_counts().reset_index()
    owner_counts.columns = ['Owner', 'Ticket Count']
    fig = px.pie(owner_counts, hole=0.4, values='Ticket Count', names='Owner', title='Ticket Distribution by Owner')
    st.plotly_chart(fig)

# Plot the number of tickets created per month for each selected year
def plot_monthly_tickets(data, selected_years):
    st.subheader("Number of Tickets Created Per Month Per Year")
    pivot_table = prepare_monthly_pivot_table(data)
    
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

# Prepare pivot table for monthly ticket data
def prepare_monthly_pivot_table(data):
    pivot_table = data.pivot(index='Month', columns='Year', values='Ticket Count').fillna(0)
    pivot_table.index = pivot_table.index.map(MONTH_MAP)
    pivot_table.index = pd.CategoricalIndex(pivot_table.index, categories=MONTH_ORDER, ordered=True)
    return pivot_table.sort_index()

# Plot the total number of tickets per year
def plot_yearly_trend(data):
    st.subheader("Total Number of Tickets Per Year")
    data['Year'] = data['Year'].astype(int)
    fig = px.bar(data, x='Ticket Count', y='Year', orientation='h', title="Total Tickets per Year")
    fig.update_layout(
        yaxis=dict(tickmode='linear', tick0=0, dtick=1)
    )
    st.plotly_chart(fig)

# Display a heatmap-like table of monthly ticket counts per year with a black-and-white color scheme
def display_heatmap_table(data, color_scheme='bw'):
    st.subheader("Heatmap of Monthly Ticket Counts Per Year")
    
    heatmap_data = prepare_heatmap_data(data)
    
    year_columns = heatmap_data.columns.drop('Month')
    heatmap_data[year_columns] = heatmap_data[year_columns].astype(int)

    # Sort the year columns and ensure correct year ordering
    heatmap_data = heatmap_data.set_index('Month').sort_index(axis=1)

    # Define color scales
    colorscale = 'Greys'

    # Create a heatmap using Plotly
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns.astype(str),
        y=heatmap_data.index,
        colorscale=colorscale,
        hoverongaps=False
    ))

    fig.update_layout(
        title='Monthly Ticket Count Heatmap',
        xaxis_title='Year',
        yaxis_title='Month',
        xaxis=dict(
            tickmode='linear',
            dtick=1
        )
    )

    st.plotly_chart(fig)




# Prepare heatmap data
def prepare_heatmap_data(data):
    heatmap_data = data.pivot_table(index='Month', columns='Year', values='Ticket Count', aggfunc='sum', fill_value=0)
    heatmap_data.index = heatmap_data.index.map(MONTH_MAP)
    heatmap_data.index = pd.CategoricalIndex(heatmap_data.index, categories=MONTH_ORDER, ordered=True)
    return heatmap_data.sort_index().reset_index()

# Load configuration
config = load_config()

# Streamlit UI
st.title("IDM Tickets Overview")

# Text of this Page
st.markdown(config['idm_tickets']['markdown_text']['additional_info'])

current_year = datetime.datetime.now().year
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(DEFAULT_START_YEAR, current_year + 1)), 
    default=[current_year - 2, current_year - 1, current_year]
)
selected_years.sort()

# Load and process the data
if selected_years:
    combined_monthly_df, combined_yearly_df, combined_owner_df = fetch_and_process_data(selected_years, config)

    # Plot the owner distribution pie chart
    plot_owner_distribution(combined_owner_df)

    # Plot the monthly ticket data
    plot_monthly_tickets(combined_monthly_df, selected_years)

    # Display the heatmap-like table
    display_heatmap_table(combined_monthly_df)

    # Plot the yearly trend
    plot_yearly_trend(combined_yearly_df)
else:
    st.write("Please select at least one year.")
