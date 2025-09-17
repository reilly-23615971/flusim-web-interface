# Flusim Web Interface Application
# Developed by Reilly Evans
# Page for displaying line graphs of infection over time

# Imports
import logging
import altair as alt
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from dashboardApp import baselineParameters
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

st.title('Infection Over Time Graphs')

st.markdown('''
    Here you can generate line graphs plotting infection rates over 
    time for different scenarios in the most recently run simulation.
''')



# Get data and plot as a line graph
if not st.session_state.get('modelDataEpidemic'): 
    st.warning('''
        No simulation data has been generated. Click 
        :primary-badge[:material/motion_play: Run Simulation] in the 
        sidebar to run a simulation and obtain the data necessary to 
        generate a graph.
    ''', icon = ':material/science_off:')
    if st.button(
        'Go to Baseline Parameters', icon = ':material/variable_insert:'
    ): st.switch_page(baselineParameters)
else:
    data = st.session_state.modelDataEpidemic
    st.altair_chart(plotEpidemic(data, 'Cases'))



#******************************************************************
# Debug case plot
scenarios = ['Baseline', 'Surged']

with open('./TestData/epidemicMedianDaily.csv', 'rb') as csv:
    meanData = formatEpidemic(csv.read(), scenarios, 'Cases')

st.altair_chart(plotEpidemic(meanData, 'Cases'))


with open('./TestData/epidemicMedianCumulative.csv', 'rb') as csv:
    sumData = formatEpidemic(csv.read(), scenarios, 'Cases', True)

st.altair_chart(plotEpidemic(sumData, 'Cases', True))

#******************************************************************