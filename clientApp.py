# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import logging
import streamlit as st
from ClientResources.InterfaceFunctions import runModelWrapper
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
    datefmt = '%Y-%m-%d %H:%M:%S', level = logging.DEBUG
)

# Define application pages
# TODO: Determine ideal page layout/what goes where
st.set_page_config(page_title = 'SMRG Flusim Web Dashboard', page_icon = '🦠')
pages = {
    'SMRG Flusim Web Dashboard': [
        st.Page('pages/1_Model_Description.py', title = 'Model Description'),
        st.Page('pages/2_Chart_Demonstration.py', title = 'Chart Demonstration')
    ]
}

# Initialise session variables
sessionParameters = {'modelData': None, 'simulationInProgress': False}
for parameter, default in sessionParameters.items(): 
    st.session_state.setdefault(parameter, default)

# Start session monitoring function to ensure it's closed properly
#monitorSession()

# Define callbacks for model parameter widgets
def runSimulationButton():
    st.session_state.simulationInProgress = True
    runModelWrapper()



# Define model parameters to adjust in sidebar
# TODO: flesh out selectable options
# TODO: consider allowing for multiple selectable 'profiles' with 
# different parameters to run in parallel
# TODO: Check if server is available and grey out button if not
parameterSidebar = st.sidebar
beta = parameterSidebar.slider('Beta', 0.01, 10.0, 0.11, key = 'beta')
npi = parameterSidebar.selectbox('NPI Presets', ['None', 'Low', 'Medium', 'High'], key = 'npi')
runModelButton = parameterSidebar.button('Run Simulation', on_click = runSimulationButton)

# Initialise and run the application pages
flusimPages = st.navigation(pages)
flusimPages.run()



# Fragment to regularly check if model results have been received yet
@st.fragment(run_every = 1)
def updateData():
    if st.session_state.simulationInProgress and not resultQueue.empty():
        st.session_state.modelData = resultQueue.get()
        st.session_state.simulationInProgress = False
updateData()


# CORS middleware for deployment (comment out when testing)
if __name__ == '__main__': st.set_option('server.enableCORS', True)