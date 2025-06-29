# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import altair as alt
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

#******************************************************************
# Debug graph formatting
def formatMeanCaseCSV(filename, cumulative):
    formattedData = pd.read_csv(
        filename, header = 0, names = [
            'Days Since Start of Simulation', 'Constant Seeding', 'Surged Seeding'
        ]
    )
    valueLabel = 'Total Cases' if cumulative else 'Cases Per Day'
    return formattedData.round(3).melt(
        'Days Since Start of Simulation', var_name = 'Simulation', 
        value_name = valueLabel
    )

caseRate = 0.5
hospitalisationRate = 0.1
mortalityRate = 0.01
gpRate = 0.166666

def formatVaccineTable(filename):
    formattedData = pd.read_csv(filename, header = 0, index_col = 0)
    baselineName = list(formattedData.index)[0]
    infectionsTotal = formattedData['overall']
    infectionsDifference = formattedData['overall'] - formattedData.at[0, baselineName]

#******************************************************************

def formatInfectionData(data):
    # This function will eventually use additional parameters to 
    # determine how to format the pandas DataFrame
    # For now it just has preset formatting
    return data.round(3).melt(
        'Day', var_name = 'Simulation', value_name = 'Rate'
    )

st.title('Flusim Project Web Interface')

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



#******************************************************************
# Debug case plot
data1 = formatMeanCaseCSV('./meanCasePerDay.csv', False)
plot1 = alt.Chart(
    data1, title = 'Daily Cases Over Time'
).mark_line().encode(
    x = 'Days Since Start of Simulation:Q', y = 'Cases Per Day:Q', 
    color = 'Simulation:N'
)
st.altair_chart(plot1)

data2 = formatMeanCaseCSV('./cumulativeMean.csv', True)
plot2 = alt.Chart(
    data2, title = 'Total Cases Over Time'
).mark_line().encode(
    x = 'Days Since Start of Simulation:Q', y = 'Total Cases:Q', 
    color = 'Simulation:N'
)
st.altair_chart(plot2)

#******************************************************************