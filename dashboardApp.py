# Flusim Web Interface Application
# Developed by Reilly Evans
# Main page of dashboard, defining pages & setting universal parameters

# Imports
import logging
from datetime import datetime
import streamlit as st
import streamlit_notify as stn
from ClientResources.SharedResources import resultQueue



# Logging config
logging.basicConfig(
    filename = './interfaceAppLogs.txt', filemode = 'a', 
    format = '%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s', 
    datefmt = '%Y-%m-%d %H:%M:%S', level = logging.DEBUG
)

# Keep session state variables loaded
session = st.session_state

# Set environment variables for config
#os.environ['STREAMLIT_GLOBAL_DISABLE_WIDGET_STATE_DUPLICATION_WARNING'] = '1'



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
            'DashboardPages/scenarioParameters.py', 
            title = 'Scenario Parameter Configuration'
        ),
        st.Page(
            'DashboardPages/tableCreation.py', 
            title = 'Health Outcome Tables'
        )
    ]
}

# Initialise session variables used by this page
# Use current time (Unix) as session ID so that different simulations 
# aren't mixed up by the server
sessionParameters = {
    'modelData': None, 'simulationInProgress': False, 'scenarioCount': 0,
    'outcomeFieldCount': 1, 'sessionID': int(datetime.now().timestamp()),
    'scenarioSetParamsExtra': {1: [], 2: [], 3: [], 4: [], 5: []}, 
    'scenarioSetParams': {1: [], 2: [], 3: [], 4: [], 5: []}
}
for parameter, default in sessionParameters.items(): 
    session[parameter] = session.get(parameter, default)

# TODO: consider adding progress updates to the sidebar (time remaining,
# progress bars, server availability etc.)
parameterSidebar = st.sidebar
runModelButtonCode = """
runModelButton = parameterSidebar.button(
    'Run Simulation', on_click = runSimulationButton, key = 'sidebarRunModel'
)
"""
# Update toasts and the like
stn.notify(remove = False)

# Initialise and run the application pages
flusimPages = st.navigation(pages)
st.set_page_config(page_title = 'SMRG Flusim Web Dashboard', page_icon = '🦠')
flusimPages.run()



# Fragment to regularly check if model results have been received yet
@st.fragment(run_every = 1)
def updateData():
    if session.simulationInProgress and not resultQueue.empty():
        #TODO: Analyze model data to determine where to place in session
        processedData = resultQueue.get()
        for data, tag in processedData: session[f'modelData{tag}'] = data
        stn.toast('Simulation complete!', icon = ":material/check_circle:")
        session.simulationInProgress = False
updateData()