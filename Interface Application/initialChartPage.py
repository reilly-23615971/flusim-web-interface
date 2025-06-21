# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import pandas as pd
import altair as alt
import streamlit as st

def formatInfectionData(data):
    # This function will eventually use additional parameters to 
    # determine how to format the pandas DataFrame
    # For now it just has preset formatting
    return data.round(3).melt(
        'Day', var_name = 'Simulation', value_name = 'Rate'
    )


# Create page


st.title('Model Results')

# Get data and plot as a line graph
if st.session_state.modelData is None: st.write((
    'No data loaded. Click "Run Simulation" on the sidebar '
    'to run a simulation and get some data to plot!'
))
else:
    data = formatInfectionData(st.session_state.modelData)
    plottedData = alt.Chart(
        data, title = 'Mean Daily Infection Rate Over Time'
    ).mark_line().encode(
        x = 'Day:Q', y = 'Rate:Q', 
        color = 'Simulation:N'
    )

    # Display the plot
    st.altair_chart(plottedData)