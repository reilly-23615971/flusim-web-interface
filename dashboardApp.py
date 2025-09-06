# Flusim Web Interface Application
# Developed by Reilly Evans
# Main page of dashboard, defining pages & setting universal parameters

# Imports
import logging
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import streamlit_notify as stn
from ClientResources.SharedResources import resultQueue

# Set this early to minimise the time spent with a different page title
# TODO: Populate About section
st.set_page_config(
    page_title = 'SMRG Flusim Web Dashboard', 
    page_icon = ':material/microbiology:',
    menu_items = {'About': '[TODO]'}
)



# Logging config
# Note that watchdog will kick logfiles into the gigabyte range if it's 
# set to Debug due to treating the log itself as a file to track
logging.basicConfig(
    filename = './interfaceAppLogs.txt', filemode = 'a', 
    format = '%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s', 
    datefmt = '%Y-%m-%d %H:%M:%S', level = logging.INFO
)

appLog = logging.getLogger(__name__)

# Load session state as variable for easy access
session = st.session_state

# Set environment variables for config
#os.environ['STREAMLIT_GLOBAL_DISABLE_WIDGET_STATE_DUPLICATION_WARNING'] = '1'



# Define application pages
# TODO: Confirm ideal page layout/what goes where
pages = {
    'SMRG Flusim Web Dashboard': [
        st.Page(
            'DashboardPages/modelDescription.py', 
            title = 'Model Description', icon = ':material/description:'
        ),
        st.Page(
            'DashboardPages/baselineParameters.py', 
            title = 'Baseline Parameters', 
            icon = ':material/variable_insert:'
        ),
        st.Page(
            'DashboardPages/scenarioParameters.py', 
            title = 'Scenario Parameters', 
            icon = ':material/variable_add:'
        ),
        st.Page(
            'DashboardPages/chartDemonstration.py', 
            title = 'Chart Demonstration', icon = ':material/chart_data:'
        ),
        st.Page(
            'DashboardPages/tableCreation.py', 
            title = 'Health Outcome Tables', 
            icon = ':material/table_chart_view:'
        )
    ]
}

# Initialise session variables used globally by the dashboard
# Use current time (Unix) as session ID so that different simulations 
# aren't mixed up by the server
sessionParameters = {
    'simulationInProgress': False, 'scenarioCount': 0,
    'sessionID': int(datetime.now().timestamp()),
    'scenarioSetParamsExtra': {1: [], 2: [], 3: [], 4: [], 5: []}, 
    'scenarioSetParams': {1: [], 2: [], 3: [], 4: [], 5: []}
}
for parameter, default in sessionParameters.items(): 
    session[parameter] = session.get(parameter, default)

# Display toasts
stn.notify(remove = True)

# Initialise and run the application pages
flusimPages = st.navigation(pages)
flusimPages.run()

# TODO: consider adding progress updates to the sidebar (time remaining,
# progress bars, server availability etc.)
# parameterSidebar = st.sidebar


# Fragment to regularly check if model results have been received yet
@st.fragment(run_every = 1)
def updateData():
    if session.simulationInProgress and not resultQueue.empty():
        processedData = resultQueue.get()
        appLog.info(
            f'[updateData] Processing the following data:\n{processedData}'
        )

        # Check if the server returned an error instead of proper data
        if isinstance(processedData, list):
            successes = 0
            scenarios = session.scenarioCount
            for data, tag in processedData: 
                # Further error checking
                if len(processedData) == 0: stn.toast(
                    f'''
                    :red-badge[Error]: No data was present on one 
                    or more of the files received from the server. 
                    Please make sure your parameters do not possess any 
                    errors and try again.
                ''', icon = ':material/tab_unselected:')
                elif tag == 'epidemic' and len(
                    data['Scenario'].value_counts()
                ) <= scenarios: 
                    stn.toast(f'''
                        :red-badge[Error]: One or more scenarios 
                        were not run correctly by the simulation 
                        server. Please ensure all scenarios do not 
                        possess any errors and try again.
                    ''', icon = ':material/donut_small:')
                else: 
                    successes += 1
                    session[f'modelData{tag}'] = data
            
            # Update parameters
            session.simulationEndTime = datetime.now().timestamp()
            totalTime = timedelta(
                session.simulationEndTime - session.simulationStartTime
            )
            if successes == scenarios + 1: stn.toast(
                f'Simulation complete! Total duration: {totalTime}', 
                icon = ":material/check_circle:"
            )
            elif successes > 0: stn.toast(f'''
                Simulation complete :yellow-background[(though some 
                analyses had errors)]. Total duration: {totalTime}
            ''', icon = ":material/check_circle_unread:")
            appLog.info(f'''
                [updateData] Data processing is complete, 
                with {scenarios - successes + 1} errors.
            ''')
        else:
            appLog.error(
                '[updateData] Received data was atypical. Contents: ' 
                + str(processedData)
            )

            # Show different toast messages for different errors
            if isinstance(processedData, tuple):
                # Errors with exceptions attached
                errorType, e = processedData
                if errorType == 'ClientConnectorError': stn.toast(f'''
                    :red-badge[Error]: Could not connect to the 
                    simulation server. Please make sure you are 
                    connected to the same network as the server, then 
                    try again.
                ''', icon = ':material/link_off:')
                elif errorType == 'ClientResponseError500': stn.toast(f'''
                    :red-badge[Error]: Simulation server had an 
                    internal error. Please try again later.
                ''', icon = ':material/error:')
                elif errorType == 'ValueError': stn.toast(f'''
                    :red-badge[Error]: The data received from the 
                    simulation server was incorrectly formatted. Please 
                    make sure your parameters do not possess any errors 
                    and try again.
                ''', icon = ':material/broken_image:')  
                else: stn.toast(f'''
                    :red-badge[Error]: The simulation server 
                    encountered an error. Please try again later.
                ''', icon = ':material/error:')
                stn.toast(f':red-badge[Full Error Message]: {e}')
            
            # Errors without exception messages to send
            elif isinstance(processedData, pd.DataFrame): stn.toast(f'''
                :red-badge[Error]: The data was not processed 
                correctly. Please try again later.
            ''', icon = ':material/data_alert:')
            elif processedData == 'EmptyZipFile': stn.toast(f'''
                :red-badge[Error]: The simulation server did not 
                return any readable files. Please make sure your 
                parameters do not possess any errors and try again.
            ''', icon = ':material/unknown_document:')
            else: stn.toast(f'''
                :red-badge[Error]: An unknown error occurred. Please 
                try again later.
            ''', icon = ':material/error:')
                
        # Make pending data no longer pending
        pendingData = {
            'Community', 'ScenarioNames', 'ScenarioCount', 
            'HealthOutcomeRates', 'MortalityRates'
        }
        for name in pendingData: 
            session[f'Data{name}'] = session.get(f'PendingData{name}')
        session.scenariosToUse = session.DataScenarioNames

        # Re-enable running new simulations and using their data
        session.ChartGenerated = False
        session.simulationInProgress = False
        st.rerun()
updateData()