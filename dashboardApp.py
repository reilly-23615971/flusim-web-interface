# Flusim Web Interface Application
# Developed by Reilly Evans
# Main page of dashboard, defining pages & setting universal parameters

# Imports
import os
import logging
import streamlit as st
from ClientResources.SimulationRunFunctions import runModelWrapper
from ClientResources.InterfaceFunctions import preserveFormEntries
from ClientResources.SharedResources import resultQueue

#import time
#import atexit
#import numpy as np
#import pandas as pd
#from ClientResources.SharedResources import resultQueue, monitorSession



# Logging config
logging.basicConfig(
    filename = './interfaceAppLogs.txt', filemode = 'a', 
    format = '%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s', 
    datefmt = '%Y-%m-%d %H:%M:%S', level = logging.INFO
)

# Set environment variables for config
#os.environ['STREAMLIT_GLOBAL_DISABLE_WIDGET_STATE_DUPLICATION_WARNING'] = '1'

# Keep parameter values between pages
#preserveFormEntries()

# Define application pages
# TODO: Determine ideal page layout/what goes where
pages = {
    'SMRG Flusim Web Dashboard': [
        st.Page(
            'DashboardPages/modelDescription.py', 
            title = 'Model Description'
        ),
        st.Page(
            'DashboardPages/chartDemonstration.py', 
            title = 'Chart Demonstration'
        ),
        st.Page(
            'DashboardPages/baselineParameters.py', 
            title = 'Baseline Parameter Configuration'
        ),
        st.Page(
            'DashboardPages/parameterConfiguration.py', 
            title = 'Parameter Configuration'
        ),
        st.Page(
            'DashboardPages/tableCreation.py', 
            title = 'Health Outcome Tables'
        )
    ]
}

# Initialise session variables
sessionParameters = {
    'modelData': None, 'simulationInProgress': False, 
    'outcomeFieldCount': 1
}
for parameter, default in sessionParameters.items(): 
    st.session_state[parameter] = st.session_state.setdefault(
        parameter, default
    )

# Start session monitoring function to ensure it's closed properly
#monitorSession()

# Define callbacks for model parameter widgets
def runSimulationButton():
    st.session_state.simulationInProgress = True
    runModelWrapper()
    # TODO: Inform user if server doesn't respond



# Define model parameters to adjust in sidebar
# TODO: flesh out selectable options
# TODO: consider allowing for multiple selectable 'profiles' with 
# different parameters to run in parallel
# TODO: Check if server is available and grey out button if not
parameterSidebar = st.sidebar
modelParameters = parameterSidebar.form('modelParameters')
beta = modelParameters.slider('Beta', 0.01, 10.0, 0.11, key = 'beta')
npi = modelParameters.selectbox('NPI Presets', ['None', 'Low', 'Medium', 'High'], key = 'npi')

caseRatio = modelParameters.slider(
    'Diagnosed Case Ratio', 0.0, 1.0, 0.5, key = 'caseRatio'
)
hospitalRatio = modelParameters.slider(
    'Hospitalisation Rate', 0.0, 0.5, 0.25, key = 'hospitalRatio'
)
deathRatio = modelParameters.slider(
    'Mortality Rate', 0.0, 0.25, 0.05, key = 'deathRatio'
)
icuRatio = modelParameters.slider(
    'ICU Visit Ratio', 0.0, 0.5, 0.1, key = 'icuRatio'
)
gpRatio = modelParameters.slider(
    'GP Visit Rate', 0.0, 1.0, 0.333, key = 'gpRatio'
)

runModelButton = modelParameters.form_submit_button(
    'Run Simulation', on_click = runSimulationButton
)

# Initialise and run the application pages
flusimPages = st.navigation(pages)
st.set_page_config(page_title = 'SMRG Flusim Web Dashboard', page_icon = '🦠')
flusimPages.run()



# Fragment to regularly check if model results have been received yet
@st.fragment(run_every = 1)
def updateData():
    if st.session_state.simulationInProgress and not resultQueue.empty():
        st.session_state.modelData = resultQueue.get()
        st.session_state.simulationInProgress = False
updateData()