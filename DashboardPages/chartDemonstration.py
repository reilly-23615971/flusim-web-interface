# Flusim Web Interface Application
# Developed by Reilly Evans
# Page for displaying line graphs of infection over time

# Imports
import time
import logging
import altair as alt
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from ClientResources.SharedResources import usePresetData
from ClientResources.InterfaceFunctions import saveKey, loadKey
from ClientResources.VisualisationFunctions import (
    formatEpidemic, plotEpidemic
)

# Logging
graphLog = logging.getLogger(__name__)

# TODO: function to generate graph
def generateGraph():
    # Throw error if no data is present
    if not usePresetData and not (
        st.session_state.get('modelDataEpidemicDaily') is not None
    ): 
        raise FileNotFoundError((
            'No simulation epidemic data was available to plot; please '
            'run a simulation before attempting to generate a table.'
        ))
    
    scenarioNames = st.session_state.get(
        'DataScenarioNames', ['Baseline', 'Surged']
    )
    scenariosUsed = st.session_state.get('chartScenariosToUse', 'all')
    chartType = st.session_state.get('chartType', 'Cumulative')
    graphLog.info(f'''
        [generateGraph] Formatting epidemic data using the scenarios 
        {scenariosUsed} and the data type {chartType}
    ''')

    # Debug code for loading data in testing
    if usePresetData:
        # Set default session_state params
        st.session_state.DataCommunity = 'newcastle'
        # Load test data from file
        presetFilename = (
            './TestData/epidemicMedianCumulative.csv' 
            if chartType == 'Cumulative' 
            else './TestData/epidemicMedianDaily.csv'
        )
        with open(presetFilename, 'rb') as csv:
            epidemicData = formatEpidemic(
                csv.read(), scenarioNames, 
                cumulative = chartType == 'Cumulative'
            )
    # Load data from session_state
    else: 
        dataVarName = 'Cumulative' if chartType == 'Cumulative' else 'Daily'
        epidemicData = st.session_state.get(f'modelDataEpidemic{dataVarName}')
    
    chartData = plotEpidemic(
        epidemicData, cumulative = chartType == 'Cumulative', 
        includedScenarios = scenariosUsed
    )
    
    # Save the generated graph
    st.session_state.InfectionChartData = chartData
    st.session_state.ChartGenerated = True








st.title('Infection Over Time Graphs')

st.markdown('''
    Here you can generate line graphs plotting infection rates over 
    time for different scenarios in the most recently run simulation.
''')

# Check if there is data to tabulate
chartErrorContainer = st.container()
currentDataExists = not (st.session_state.get('modelDataEpidemicDaily') is None)
if not currentDataExists and not usePresetData: 
    chartErrorContainer.warning('''
        No simulation data has been generated. Click 
        :primary-badge[:material/motion_play: Run Simulation] in the 
        sidebar to run a simulation and obtain the data necessary to 
        generate a graph.
    ''', icon = ':material/science_off:')
if currentDataExists and st.session_state.simulationInProgress: 
    chartErrorContainer.warning('''
        Warning: A new simulation is currently in progress. Since the 
        data is not yet ready to process, attempting to create a graph 
        now will use the data from the previous simulation. Once the 
        in-progress simulation is complete, it will not be possible to 
        generate graphs with the previous simulation's data, though the 
        current graph will still be available to view and download 
        until you generate a new graph.
    ''', icon = ':material/av_timer:')


# TODO: Settings to configure the line graph ala table
graphSettings = st.expander('Graph Settings')
with graphSettings:
    st.markdown('''
        Use these parameters to configure how the line graph will be generated. 
        Hover your mouse over the :material/help: help icon next to a 
        setting's input field to show an explanation of what that setting 
        does. Hover your mouse over any buttons to show an explanation of 
        what that button does.  
    ''')

    loadKey(f'chartType', '', 'Cumulative', noZeroDefault = True)
    chartType = st.selectbox(
        'Chart Type', ['Cumulative', 'Daily Rate'], index = 0, 
        key = '_chartType', on_change = saveKey, args = (f'chartType', ''), 
        kwargs = {'notScenario': True}, 
        placeholder = 'Please select a data format', help = '''
            Select what kind of data should be displayed in the graph.

            ### Options:
            - Cumulative: the chart will plot the total number of 
            infections that have cumulatively occurred at each point of 
            the simulation.
            - Daily Rate: the chart will plot the number of infections 
            that occur in each day of the simulation.
        '''
    )

    # Scenario selection
    scenarioNames = st.session_state.get(
        'DataScenarioNames', ['Baseline', 'Surged']
    )
    if currentDataExists or usePresetData: 
        loadKey('chartScenariosToUse', '', scenarioNames, noZeroDefault = True)
        scenariosToUse = st.multiselect(
            'Scenarios to Include in Graph', scenarioNames, 
            default = scenarioNames, key = '_chartScenariosToUse', 
            on_change = saveKey, args = [f'chartScenariosToUse', ''], # type: ignore
            placeholder = 'Please select at least 1 scenario', 
            kwargs = {'notScenario': True}, help = '''
Select which scenarios should be included in the table. 
You may select as many scenarios as you wish, but you 
must select at least one. Each scenario will be plotted onto the graph 
as its own line, showing the infections over time for that scenario. 
            '''
        )
        if not scenariosToUse: chartErrorContainer.error('''
            Error: No scenarios have been included in the graph. If you 
            attempt to generate the graph now, it will be empty. Please 
            select at least one scenario to include with the 'Scenarios 
            to Use' setting.
        ''', icon = ':material/tab_unselected:')
    else: 
        st.info('''
            No simulation data has been generated, so there are 
            currently no scenarios to select. Click 
            :primary-badge[:material/motion_play: Run Simulation] in 
            the sidebar to run a simulation and obtain the data 
            necessary to generate a graph.
        ''', icon = ':material/tab_unselected:')
        scenariosToUse = None
    
    





# Button to generate the graph
st.button(
    label = 'Create Graph', icon = ':material/chart_data:', 
    key = 'generateGraph', type = 'primary', on_click = generateGraph, 
    disabled = (
        (not usePresetData and not currentDataExists) 
        or not scenariosToUse
    ), 
    help = '''
        Use the data from the last simulation to generate a graph 
        displaying the infections in the simulation, formatted using 
        the settings selected above.
    ''' if currentDataExists else '''
        No simulations have completed yet, so there is no data to plot.
    '''
)

# Display the graph itself
chartData = st.session_state.get('InfectionChartData')
if chartData is not None: 
    st.header('Infection Data Line Graph')
    st.altair_chart(chartData)

    # Button to download the CSV data used by the chart
    @st.fragment()
    def infectionDataDownload():
        chartTypeTag = 'Cumulative' if chartType == 'Cumulative' else 'Daily'
        dataToDownload = st.session_state.get(
            f'modelDataEpidemic{chartTypeTag}'
        )
        if dataToDownload is not None: 
            st.download_button(
                'Download Infection Data', dataToDownload.to_csv().encode('utf-8'), 
                f'FlusimInfectionData{chartTypeTag}_{time.strftime('%Y.%m.%d_%I.%M.%S%p')}.csv', 
                mime = 'text/csv', key = 'infectionDataDownload', 
                disabled = st.session_state.get('modelDataEpidemicDaily') == None,
                icon = ':material/download:', help = '''
                    Download the infection data from the most recent 
                    simulation (the data used by the above graph) as a CSV 
                    file. Note that all scenarios are included in the 
                    returned file, even if not all were selected for the 
                    graph.
                '''
            )
        elif usePresetData: 
            presetFilename = (
                './TestData/epidemicMedianCumulative.csv' 
                if chartType == 'Cumulative' 
                else './TestData/epidemicMedianDaily.csv'
            )
            with open(presetFilename, 'rb') as csv:
                epidemicData = formatEpidemic(
                    csv.read(), scenarioNames, 
                    cumulative = chartType == 'Cumulative'
                )
            st.download_button(
                'Download Infection Data', epidemicData.to_csv(index = False), 
                f'FlusimInfectionData{chartTypeTag}_{time.strftime('%Y.%m.%d_%I.%M.%S%p')}.csv', 
                mime = 'text/csv', key = 'infectionDataDownload', 
                disabled = (
                    not usePresetData 
                    and st.session_state.get('modelDataEpidemicDaily') == None
                ),
                icon = ':material/download:', help = '''
                    Download the infection data from the most recent 
                    simulation (the data used by the above graph) as a CSV 
                    file. Note that all scenarios are included in the 
                    returned file, even if not all were selected for the 
                    graph.
                '''
            )
        else: st.error('''
            Error: The data used by the graph was empty or could not be 
            accessed. Please try regenerating the graph or rerunning 
            the simulation to fix the issue.
        ''', icon = ':material/error:')
    infectionDataDownload()
    
    st.subheader('Using the Graph')
    st.markdown('''
        - Hover your mouse over a point on the graph to display a 
        tooltip, which lists the infection values for each scenario on 
        the corresponding day.
        - Click on a scenario name on the right to show only the line 
        for that scenario, blurring the others. Hold Shift and click on 
        another scenario name to toggle its visibility without 
        affecting the other lines.
                
        Hovering your mouse over the graph's top right corner will display two additional icons: 
        
        - Click the :material/fullscreen: fullscreen symbol to put the 
        table in fullscreen; click it again to return to viewing the 
        whole dashboard.
        - Click the :material/more_horiz: menu symbol to display a list 
        of additional options. With these options you can download the 
        graph as an image file or access the Vega source data for the 
        graph.
    ''')





debugPlots = """#******************************************************************
# Debug case plot
scenarios = ['Baseline', 'Surged']

with open('./TestData/epidemicMedianDaily.csv', 'rb') as csv:
    meanData = formatEpidemic(csv.read(), scenarios, 'Cases')

st.altair_chart(plotEpidemic(meanData, 'Cases'))


with open('./TestData/epidemicMedianCumulative.csv', 'rb') as csv:
    sumData = formatEpidemic(csv.read(), scenarios, 'Cases', True)

st.altair_chart(plotEpidemic(sumData, 'Cases', True))

#******************************************************************"""