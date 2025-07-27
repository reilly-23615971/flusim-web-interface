# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st
from ParameterTabs.basicParams import buildBasicTab
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.communityParams import buildCommunityTab
from ParameterTabs.vaccinationNPIs import buildVaccinationNPITab
from ParameterTabs.dynamicParams import buildDynamicTab
from ClientResources.SimulationRunFunctions import runModelWrapper

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

st.markdown('''
    This page allows for configuring the parameters that will be used 
    as a baseline for the simulation. All scenarios that you run will 
    use these parameters unless the scenario explicitly overwrites them.
            
    Select a tab to view or modify the parameters under that category. 
    Hover your mouse over the :material/help: help icon next to a 
    parameter's input field to show an explanation of what that 
    parameter represents. Hover your mouse over any buttons to show an 
    explanation of what that button does.
''')

# Place to put warnings errors in the current parameter selection
alertContainer = st.container()

# Button to run the model
# TODO: Check if server is available and grey out button if not
# TODO: Vary message depending on scenario presence, server 
# availability, errors, etc.
# TODO: Add 'are you sure' prompt when pressing button
st.markdown('''
    Press the button below to run the simulation. Remember that in 
    order to compare different parameter values, you should define 
    scenarios with different parameters here [ADD LINK]; make sure 
    these scenarios have been configured before running the model.
''')
runModelButton = st.button(
    'Run Simulation', on_click = runSimulationButton
)

#TODO: Consider having a tab for templates that load parameters for 
# specific stuff (e.g. influenza, NPI presets)

(
    basicTab, diseaseTab, environmentTab, 
    interventionTab, dynamicTab
) = st.tabs([
    'Initialisation', 'Disease', 'Community', 
    'Vaccination and NPIs', 'Dynamic'
])


# TODO: Split up start and relaxation triggers in Vaccination/NPIs

# Basic parameters
buildBasicTab(basicTab, 0, alertContainer)

# Disease parameters
buildDiseaseTab(diseaseTab, 0, alertContainer)

# Environment parameters
buildCommunityTab(environmentTab, 0, alertContainer)

# Vaccination and NPIs
buildVaccinationNPITab(interventionTab, 0, alertContainer)

# Dynamic parameters
buildDynamicTab(dynamicTab, 0, alertContainer)

#Debug
#st.header('DEBUG ZONE')
#st.write(st.session_state)