# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st
#from streamlit_push_notifications import send_push, send_alert
from ParameterTabs.basicParams import buildBasicTab
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.communityParams import buildCommunityTab
from ParameterTabs.vaccinationNPIParams import buildVaccinationNPITab
from ParameterTabs.dynamicParams import buildDynamicTab
from ClientResources.InterfaceFunctions import saveKey, loadKey, checkErrors
from ClientResources.SimulationRunFunctions import runSimulationButton
from ClientResources.SharedResources import communityPopulation

# Logging
baselineLog = logging.getLogger(__name__)



# Page Content

st.title('Flusim Disease Model Web Dashboard')

st.markdown(f'''
    This page allows for configuring the parameters that will be used 
    as a baseline for the simulation.
    
    Select a tab to view or modify the parameters under that category. 
    Hover your mouse over the :material/help: help icon next to a 
    parameter's input field to show an explanation of what that 
    parameter represents. Hover your mouse over any buttons to show an 
    explanation of what that button does.
''')

# Community Selection
loadKey('community', '', 'newcastle')
community = st.selectbox(
    'Simulated Community', communityPopulation.keys(), key = '_community', 
    format_func = lambda x: x.capitalize(), 
    on_change = saveKey, args = ['community'],  # type: ignore
    help = '''
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

st.markdown(f'''
    All scenarios in the simulation will use the parameters on this 
    page as a baseline; however, individual scenarios can have 
    different values defined at the Scenario Parameter Configuration 
    page, overwriting these base values. The sole exception to this 
    is the Simulated Community parameter defined above, which applies 
    to all scenarios and cannot be overwritten.
''')
# TODO: Consider displaying more comprehensive community info regarding 
# the one the user selects

# Button to run the model
# TODO: Check if server is available and grey out button if not
# TODO: Vary message depending on scenario presence, server 
# availability, errors, etc.
# TODO: Add 'are you sure' prompt when pressing button
scenarioCount = st.session_state.get('scenarioCount', 0)
errors = [checkErrors(id) for id in range(scenarioCount + 1)]

# Place to put warnings and errors in the current parameter selection
if max((max(e) for e in errors)) == 0: st.markdown(f'''
    Currently, all parameters have been set to valid values; the 
    simulation should run as intended. If any errors are detected with 
    the parameters selected for the baseline scenario, they will be 
    described here.
''')
elif max(errors[0]) == 0: st.warning(f'''
    Currently, all parameters for the baseline scenario have been set 
    to valid values; however, there is at least 1 error present in the 
    scenarios defined at the Scenario Parameter Configuration page. 
    Please examine and correct these errors if necessary before running 
    the simulation. If any errors are detected with the parameters 
    selected for the baseline scenario, they will be described here.
''')
alertContainer = st.container()

runModelButton = st.button(
    'Run Simulation', key = 'baselineRunModel', on_click = runSimulationButton,
    disabled = st.session_state.simulationInProgress, help = '''
        Send a request to the *Flusim* model server to run the model 
        with the specified parameters. Once the request has been made, 
        you will be unable to run the model again until it completes, 
        so make sure you have configured your parameters to appropriate 
        values before clicking.
    ''' if not st.session_state.simulationInProgress else '''
        A simulation is already running; please wait for it to conclude 
        before running another one.
    '''
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
st.header('DEBUG ZONE')
st.write(st.session_state)