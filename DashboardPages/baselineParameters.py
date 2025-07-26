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

# Logging
baselineLog = logging.getLogger(__name__)

# Initialise session variables
likelyLaterSessionParams = """
sessionParameters = {
    'vacAgeRowCount0': 0,
    'primaryDoseCount0': 2,
    'primWanedRowCount0': 0,
    'boostAgeRowCount0': 0, 
    'boosterRemainingAgeGroups0': list(dict.fromkeys(ageCategories))
}
for parameter, default in sessionParameters.items(): 
    st.session_state[parameter] = st.session_state.setdefault(
        parameter, default
    )
"""

# TODO: Bring back the age group set setup from vaccination/NPIs if 
# needed by other tabs





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

#TODO: Add more configurable parameters/tabs
#TODO: Consider having templates that load parameters for specific stuff
# Tab ideas: Environment? Health Outcome?

(
    basicTab, diseaseTab, environmentTab, 
    interventionTab, healthOutcomeTab, dynamicTab
) = st.tabs([
    'Initialisation', 'Disease', 'Community', 
    'Vaccination and NPIs', 'Health Outcome', 'Dynamic'
])


remainder = """
Still needs to be tabbed:
- Behaviour parameters
- Contact parameters
- Diagnosis delay
- Age-specific mortality
- Dynamic intervention

- Separate relaxation triggers?
"""

# Basic parameters
buildBasicTab(basicTab, 0, alertContainer)

# Disease parameters
buildDiseaseTab(diseaseTab, 0, alertContainer)

# Environment parameters
buildCommunityTab(environmentTab, 0, alertContainer)

# Vaccination and NPIs
buildVaccinationNPITab(interventionTab, 0, alertContainer)

#Debug
#st.header('DEBUG ZONE')
#st.write(st.session_state)