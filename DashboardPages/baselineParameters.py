# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st
from ParameterTabs.basicParams import buildBasicTab
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.communityParams import buildCommunityTab
from ParameterTabs.vaccinationNPIParams import buildVaccinationNPITab
from ParameterTabs.dynamicParams import buildDynamicTab
from ClientResources.SimulationRunFunctions import runModelWrapper
from ClientResources.SharedResources import communityPopulation, clientUrl

# Logging
baselineLog = logging.getLogger(__name__)

# Callback for run simulation button
def runSimulationButton():
    st.session_state.simulationInProgress = True
    runModelWrapper()
    # TODO: Inform user if server doesn't respond





# Page Content
# TODO: Warn for nonsensical conditions like reduced BCC > regular BCC

st.title('Flusim Disease Model Web Dashboard')

st.markdown(f'''
    This page allows for configuring the parameters that will be used 
    as a baseline for the simulation.
            
    Select a tab to view or modify the parameters under that category. 
    Hover your mouse over the :material/help: help icon next to a 
    parameter's input field to show an explanation of what that 
    parameter represents. Hover your mouse over any buttons to show an 
    explanation of what that button does.
    
    All scenarios in the simulation will use the parameters on this 
    page as a baseline; however, individual scenarios can have 
    different values defined at the Scenario Parameter Configuration 
    page <a href="{clientUrl}scenarioParameters" target="_self">
    here</a>, overwriting these base values. The sole exception to this 
    is the Simulated Community parameter defined below, which applies 
    to all scenarios and cannot be overwritten.
''', unsafe_allow_html = True)

# Community Selection
multiCommunityCode = """
community = st.segmented_control(
    'Simulated Community', communityPopulation.keys(), 
    selection_mode = 'multi', default = 'newcastle', 
    format_func = lambda x: x.capitalize(), key = 'community', help = '''
                The Australian city whose community data will be used 
                as the basis for the population and demographic 
                distribution in the simulation. Note that the data used 
                for these communities comes from 2011.

                ##### Options:
                - Newcastle: A metropolitan area in New South Wales, 
                Australia. It has a population of 272407, the 
                second-largest in the state, and has a demographic 
                distribution that more closely matches that of 
                Australia as a whole compared to Cairns.
                - Cairns: A major city in Queensland, Australia. It has 
                a population of 140402 (as of 2011 when this data was 
                collected) and has a higher Indigenous population 
                compared to Newcastle.
            '''
)
"""
community = st.selectbox(
    'Simulated Community', communityPopulation.keys(), key = 'community', 
    format_func = lambda x: x.capitalize(), help = '''
        The Australian city whose community data will be used as the 
        basis for the population and demographic distribution in the 
        simulation. Note that the data used for these communities comes 
        from 2011.

        ##### Options:
        - Newcastle: A metropolitan area in New South Wales, Australia. 
        It has a population of 272407, the second-largest in the state, 
        and has a demographic distribution that more closely matches 
        that of Australia as a whole compared to Cairns.
        - Cairns: A major city in Queensland, Australia. It has a 
        population of 140402 (as of 2011 when this data was collected) 
        and has a higher Indigenous population compared to Newcastle.
    '''
)
# TODO: Consider displaying more comprehensive community info regarding 
# the one the user selects

# Button to run the model
# TODO: Check if server is available and grey out button if not
# TODO: Vary message depending on scenario presence, server 
# availability, errors, etc.
# TODO: Add 'are you sure' prompt when pressing button
st.markdown(f'''
    Press the button below to run the simulation. Remember that in 
    order to compare different parameter values, you should define 
    scenarios with different parameters <a href = 
    "{clientUrl}scenarioParameters" target = "_self">here</a>; 
    make sure these scenarios have been configured before running the 
    model.
''', unsafe_allow_html = True)

# TODO: Remove this message when there's no errors
st.markdown(f'''
    Currently, all parameters have been set to valid values. If any 
    errors are been detected with the parameters selected for the 
    simulation (both in this baseline scenario and in any scenarios 
    defined <a href = "{clientUrl}scenarioParameters" target = 
    "_self">here</a>), they will be described here.
''', unsafe_allow_html = True)
# Place to put warnings errors in the current parameter selection
alertContainer = st.container()

runModelButton = st.button(
    'Run Simulation', on_click = runSimulationButton
)

# TODO: Consider having a tab for templates that load parameters for 
# specific stuff (e.g. influenza, NPI presets)
# TODO: Check studies for better parameter defaults/ranges
# TODO: Check parameters where slider is bad for selecting and either 
# change scale or switch to number input

(
    basicTab, diseaseTab, communityTab, 
    interventionTab, dynamicTab
) = st.tabs([
    'Initialisation', 'Disease', 'Community', 
    'Vaccination and NPIs', 'Dynamic'
])

# Basic parameters
buildBasicTab(basicTab, 0, alertContainer)

# Disease parameters
buildDiseaseTab(diseaseTab, 0, alertContainer)

# Environment parameters
buildCommunityTab(communityTab, 0, alertContainer)

# Vaccination and NPIs
buildVaccinationNPITab(interventionTab, 0, alertContainer)

# Dynamic parameters
buildDynamicTab(dynamicTab, 0, alertContainer)

# TODO: Debug
#st.header('DEBUG ZONE')
#st.write(st.session_state)