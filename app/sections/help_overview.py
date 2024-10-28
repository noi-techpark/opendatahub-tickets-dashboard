import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from utils import fetch_data

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

# Updated function to display a black-and-white heatmap
def display_heatmap_table(data):
    """Displays a heatmap-like table of monthly ticket counts per year using a black-and-white color scheme."""
    st.subheader("Heatmap of Monthly Ticket Counts Per Year")

    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_map = {i+1: month for i, month in enumerate(month_order)}

    # Create a pivot table to organize data
    heatmap_data = data.pivot_table(index='Month', columns='Year', values='Ticket Count', aggfunc='sum', fill_value=0)
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
        xaxis_title='Year',
        yaxis_title='Month'
    )

    st.plotly_chart(fig)

# Load the configuration
config = st.session_state.config

st.title("Help Queue Overview")

# Text of this Page
st.markdown(config['help_overview']['markdown_text']['additional_info'])

current_year = datetime.datetime.now().year
selected_years = st.multiselect(
    "Select Years", 
    options=list(range(2019, current_year+1)), 
    default=[current_year-2, current_year-1, current_year]
)
selected_years.sort()

# Load the data
combined_monthly_df, combined_yearly_df = load_data(selected_years)

# Plot the monthly data
plot_monthly_tickets(combined_monthly_df, selected_years)

# Display the heatmap-like table using black-and-white color scheme
display_heatmap_table(combined_monthly_df)

# Plot the yearly trend
plot_yearly_trend(combined_yearly_df)
