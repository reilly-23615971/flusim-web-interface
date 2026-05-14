# Flusim Web Interface Application
# Developed by Reilly Evans
# Main program of dashboard, defining pages & setting universal parameters


# Imports
import logging
import os
from datetime import datetime
from functools import partial

import streamlit as st

# Reload streamlit_notify if it fails the first time
try:
    import streamlit_notify as stn
except ImportError:
    import importlib
    import time

    time.sleep(0.01)
    importlib.reload(importlib.import_module("streamlit_notify"))
    import streamlit_notify as stn  # type: ignore

from ClientResources.InterfaceFunctions import timeString
from ClientResources.SharedResources import (
    currentProgress,
    errorQueue,
    resultQueue,
    usePresetData,
    usePresetParams,
)
from ClientResources.VisualisationFunctions import formatData

# Set this early to minimise the time spent with a different page title
st.set_page_config(
    page_title="Flusim Web Dashboard",
    page_icon=":material/microbiology:",
    layout="wide",
    menu_items={"About": """
        ## Flusim Web Dashboard
        This dashboard is designed to work with the *Flusim* model
        designed by the UWA Software Modelling Research Group.
        ##### Additional Credits
        Colour palette for scenarios created by Paul Tol
        https://sronpersonalpages.nl/~pault/
    """},
)

# Logging config
os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    filename="Logs/interfaceAppLogs.txt",
    filemode="a",
    format="%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

appLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Initialise session variables used globally by the dashboard
# Use current time (Unix) as session ID so that different simulations
# aren't mixed up by the server
sessionParameters = {
    "simulationInProgress": False,
    "keepProgressBar": False,
    "scenarioCount": 0,
    "sessionID": int(datetime.now().timestamp()),
    "scenarioSetParamsExtra": {},
    "scenarioSetParams": {},
    "activeErrors": {0: {}},
}
for parameter, default in sessionParameters.items():
    session[parameter] = session.get(parameter, default)

# TODO: Load defaults from influenza template instead of hardcoding

# TODO: See if an extra cookie package like streamlit-cookie-controller
# can preserve parameters between refreshed pages

# Define partial function for toasts
notifyToast = partial(stn.toast, duration="infinite")


st.logo(":material/microbiology:")


# Define application pages
# TODO: Limit nested containers since apparently they might cause page blanking
landingPage = st.Page(
    "DashboardPages/landingPage.py",
    title="Main Page",
    icon=":material/home:",
)
modelDescription = st.Page(
    "DashboardPages/modelDescription.py",
    title="Model Description",
    icon=":material/description:",
)
baselineParameters = st.Page(
    "DashboardPages/baselineParameters.py",
    title="Baseline Parameters",
    icon=":material/variable_insert:",
)
scenarioParameters = st.Page(
    "DashboardPages/scenarioParameters.py",
    title="Scenario Parameters",
    icon=":material/variable_add:",
)
runSimulation = st.Page(
    "DashboardPages/runSimulations.py",
    title="Run Simulations",
    icon=":material/motion_play:",
)
infectionGraphs = st.Page(
    "DashboardPages/infectionOverTimeGraphs.py",
    title="Infection Graphs",
    icon=":material/chart_data:",
)
healthTables = st.Page(
    "DashboardPages/healthBurdenTables.py",
    title="Health Burden Tables",
    icon=":material/table_chart_view:",
)

pages = {
    "Flusim Web Dashboard": [landingPage],
    "Parameter Configuration": [
        modelDescription,
        baselineParameters,
        scenarioParameters,
    ],
    "Conducting Experiments": [runSimulation],
    "Results Visualisation": [infectionGraphs, healthTables],
}

# Display toasts
stn.notify(remove=True)

# Initialise and run the application pages
flusimPages = st.navigation(pages)
flusimPages.run()

st.sidebar.link_button(
    "User Manual", "/app/static/UserManual.pdf", icon=":material/quick_reference:"
)


# TODO: Fix the "fragment no longer exists" issues
@st.fragment(run_every=1)
def updateData():
    """
    Fragment to regularly check if model results have been received yet.
    """
    hasResults, hasError = not resultQueue.empty(), not errorQueue.empty()
    if session.simulationInProgress and (hasResults or hasError):
        if hasResults and not hasError:
            # Reset pending simulation variables
            pendingData = {
                "Forms",
                "Community",
                "ScenarioNames",
                "ScenarioCount",
                "Asymptomatic",
                "HealthOutcomeRates",
                "MortalityRates",
                "HasWaning",
            }
            # TODO: Add a check to ensure visualisations can't use the new values
            # while this function is still processing the data
            for name in pendingData:
                session[f"Data{name}"] = session.get(f"PendingData{name}")

            # Process data and ensure there is no formatting errors
            returnedData = resultQueue.get()
            appLog.info(f"[updateData] Processing the following data:\n{returnedData}")

            # Remove any old session data that is no longer valid
            # TODO: Make more robust when number of returned values can vary more
            scenarioCount = (
                4 if usePresetData or usePresetParams else session.DataScenarioCount + 1
            )
            dataForms = session.get("DataForms", [])
            if len(dataForms) < 4:
                session.pop("modelDataAsirVaccinated", None)

            # Format data
            # TODO: Consider creating vaccinated/unvaccinated asir dataframes
            # here rather than in generateAsir
            formattedData = [formatData(d, f) for d, f in zip(returnedData, dataForms)]

            # Check for any errors in the data
            if any(len(data) == 0 for data in formattedData):
                errorQueue.put(
                    (
                        "Simulation results were empty",
                        """
No data was present on one or more of the files received from the server.
Please make sure your parameters do not possess any errors and try again.
                    """,
                        "tab_unselected",
                        None,
                    )
                )
                hasError = True
            elif any(
                form.tool == "epidemic"
                and len(data["Scenario"].value_counts()) != scenarioCount
                for data, form in zip(formattedData, dataForms)
            ):
                errorQueue.put(
                    (
                        "Some scenarios were not run properly",
                        """
One or more scenarios were not run correctly by the simulation server. Please
ensure all scenarios do not possess any errors and try again.
                    """,
                        "donut_small",
                        None,
                    )
                )
                hasError = True
            else:
                # Save the data to st.session_state
                for data, form in zip(formattedData, dataForms):
                    session[f"modelData{form.dataTag}"] = data

                # Tell the user what's happened
                session.simulationEndTime = datetime.now()
                totalTime = session.simulationEndTime - session.simulationStartTime
                formattedTime = timeString(totalTime.total_seconds())
                notifyToast(
                    f"Simulation complete! Total duration: {formattedTime}",
                    icon=":material/check_circle:",
                )
                appLog.info("[updateData] Data processing is complete.")
                session.ChartGenerated = False
        if hasError:
            # Notify user of errors, but leave displaying them to runSimulations
            session["simulationError"] = errorQueue.get()
            currentProgress.append(-1.0)
            notifyToast(
                """
Simulation encountered an error; see
:primary-badge[:material/motion_play: Run Simulations] for more.
                """,
                icon=":material/error:",
            )

        # Re-enable running new simulations and using their data
        session.simulationInProgress = False
        session.keepProgressBar = True
        st.rerun()


updateData()
