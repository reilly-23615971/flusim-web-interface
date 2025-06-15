# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import pandas as pd
import altair as alt
import streamlit as st

def getInfectionData():
    # This function will eventually contact the server running the
    # Flusim model in order to get data with the desired parameters
    # For now it just pulls from one CSV file
    if st.session_state.modelData:
        meanInfectionsPerDay = st.session_state.modelData.round(3).melt(
            'Day', var_name = 'Simulation', 
            value_name = 'Rate'
        )
        return meanInfectionsPerDay
    else: return -1


# Create page


st.title('Model Results')

# Get data and plot as a line graph
data = getInfectionData()
if data == -1: st.write((
    'No data loaded. Click "Run Model" on the sidebar '
    'to run a simulation and get some data to plot!'
))
else:
    plottedData = alt.Chart(
        data, title = 'Mean Daily Infection Rate Over Time'
    ).mark_line().encode(
        x = 'Day:Q', y = 'Rate:Q', 
        color = 'Simulation:N'
    )

    # Display the plot
    st.altair_chart(plottedData)