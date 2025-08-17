# Flusim Web Interface Application
# Developed by Reilly Evans
# Temporary page demonstrating the application's graphing capabilities

# Imports
import logging
import altair as alt
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from ClientResources.VisualisationFunctions import (
    formatEpidemic, formatAsir, plotEpidemic
)

# Logging
demoLog = logging.getLogger(__name__)


#******************************************************************

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

st.title('Flusim Disease Model Web Dashboard')

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
scenarios = ['Baseline', 'Surged']

with open('./TestData/epidemicMedianDaily.csv', 'r') as csv:
    meanData = formatEpidemic(csv.read(), scenarios, 'Cases')

st.altair_chart(plotEpidemic(meanData, 'Cases'))


with open('./TestData/epidemicMedianCumulative.csv', 'r') as csv:
    sumData = formatEpidemic(csv.read(), scenarios, 'Cases', True)

st.altair_chart(plotEpidemic(sumData, 'Cases', True))

with open('./TestData/asirMedianAbsolute.csv', 'r') as csv:
    ageData = formatAsir(csv.read(), scenarios, 'Cases', False, 'absolute')

with open('./TestData/asirMedianAbsolute.csv', 'r') as csv:
    ageData = formatAsir(csv.read(), scenarios, 'Cases', False, 'percentage')

#******************************************************************