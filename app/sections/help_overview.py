import streamlit as st
import pandas as pd
import yaml
import datetime
from utils import fetch_data

# Load configuration from the config.yaml file
def load_config(config_file="config.yaml"):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

def load_data(selected_years):
    # Initialize a list to hold the monthly ticket counts for each year
    monthly_ticket_data = []
    yearly_ticket_counts = []

    for year in selected_years:
        # Fetch data for the year
        df = fetch_data(year, config['help_overview']['query_parameters']['query'], config['help_overview']['query_parameters']['fields'])
        
        # Ensure the "Created" column is in datetime format
        df['Created'] = pd.to_datetime(df['Created'], format='%a %b %d %H:%M:%S %Y')
        
        # Extract month and year from the "Created" column
        df['Year'] = df['Created'].dt.year
        df['Month'] = df['Created'].dt.month
        
        # Group by Year and Month, then count the number of tickets
        monthly_counts = df.groupby(['Year', 'Month']).size().reset_index(name='Ticket Count')
        yearly_count = df['Year'].value_counts().reset_index(name='Ticket Count')
        yearly_count.columns = ['Year', 'Ticket Count']
        
        # Append to the list
        monthly_ticket_data.append(monthly_counts)
        yearly_ticket_counts.append(yearly_count)
    
    # Concatenate all years' data into a single DataFrame
    combined_monthly_df = pd.concat(monthly_ticket_data, ignore_index=True)
    combined_yearly_df = pd.concat(yearly_ticket_counts, ignore_index=True).groupby('Year').sum().reset_index()
    
    return combined_monthly_df, combined_yearly_df

import pandas as pd
import streamlit as st

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

    # Plot the data
    st.bar_chart(pivot_table)

def plot_yearly_trend(data):
    """Displays a bar chart of the total number of tickets per year."""
    st.subheader("Total Number of Tickets Per Year")
    
    # Set the 'Year' column as the index
    data = data.set_index('Year')

    # Plot the data
    st.bar_chart(data)

def display_heatmap_table(data):
    """Displays a heatmap-like table of monthly ticket counts per year."""
    st.subheader("Heatmap of Monthly Ticket Counts Per Year")

    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_map = {i+1: month for i, month in enumerate(month_order)}

    # Create a pivot table to organize data
    heatmap_data = data.pivot_table(index='Month', columns='Year', values='Ticket Count', aggfunc='sum', fill_value=0)
    heatmap_data.index = heatmap_data.index.map(month_map)
    heatmap_data.index = pd.CategoricalIndex(heatmap_data.index, categories=month_order, ordered=True)
    heatmap_data = heatmap_data.sort_index().reset_index()

    # Display the heatmap-like table
    st.dataframe(heatmap_data.style.background_gradient(cmap="YlGnBu", axis=None))




# Load the configuration
config = load_config()

st.title("Help Queue Overview")

current_year = datetime.datetime.now().year
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(2019, current_year+1)), 
    default=[current_year-2, current_year-1, current_year]
)
selected_years.sort()

# Text of this Page
st.markdown(config['help_overview']['markdown_text']['additional_info'])

# Load the data
combined_monthly_df, combined_yearly_df = load_data(selected_years)

# Plot the monthly data
plot_monthly_tickets(combined_monthly_df, selected_years)

# Display the heatmap-like table
display_heatmap_table(combined_monthly_df)

# Plot the yearly trend
plot_yearly_trend(combined_yearly_df)


