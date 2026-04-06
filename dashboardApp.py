# Flusim Web Interface Application
# Developed by Reilly Evans
# Main page of dashboard, defining pages & setting universal parameters


# Imports
import logging
import os
from datetime import datetime
from functools import partial

import pandas as pd
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

from ClientResources.SharedResources import resultQueue, usePresetData, usePresetParams
from ClientResources.VisualisationFunctions import formatData

# Set this early to minimise the time spent with a different page title
st.set_page_config(
    page_title="Flusim Web Dashboard",
    page_icon=":material/microbiology:",
    layout="wide",
    menu_items={
        "About": """
        ## Flusim Web Dashboard
        This dashboard is designed to work with the *Flusim* model
        designed by the UWA Software Modelling Research Group.
        ##### Additional Credits
        Colour palette for scenarios created by Paul Tol
        https://sronpersonalpages.nl/~pault/
    """
    },
)

# Logging config
# TODO: Double-check that no logging loops are occurring
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
    "scenarioCount": 0,
    "sessionID": int(datetime.now().timestamp()),
    "scenarioSetParamsExtra": {},
    "scenarioSetParams": {},
    "activeErrors": {0: {}},
}
for parameter, default in sessionParameters.items():
    session[parameter] = session.get(parameter, default)

# Define partial function for toasts
notifyToast = partial(stn.toast, duration="infinite")


st.logo(":material/microbiology:")


# Define application pages
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
    "Flusim Web Dashboard": [modelDescription],
    "Parameter Configuration": [baselineParameters, scenarioParameters, runSimulation],
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


@st.fragment(run_every=1)
def updateData():
    """
    Fragment to regularly check if model results have been received yet.
    """
    # TODO: Rewrite this to be cleaner and more readable
    if session.simulationInProgress and not resultQueue.empty():
        returnedData = resultQueue.get()
        appLog.info(f"[updateData] Processing the following data:\n{returnedData}")
        os.write(1, "Simulation experiment call complete\n\n".encode())

        # Make pending data no longer pending
        pendingData = {
            "Forms",
            "Community",
            "ScenarioNames",
            "ScenarioCount",
            "Asymptomatic",
            "HealthOutcomeRates",
            "MortalityRates",
        }
        for name in pendingData:
            session[f"Data{name}"] = session.get(f"PendingData{name}")
        # TODO: Add a check to ensure visualisations can't use the new values
        # while this function is still processing the data

        # Check if the server returned an error instead of proper data
        if isinstance(returnedData, list):
            successes = 0
            scenarios = (
                4 if usePresetData or usePresetParams else session.DataScenarioCount + 1
            )
            # Remove any old session data that won't be overridden here
            # TODO: Make more robust when number of returned values can vary more
            dataForms = session.get("DataForms", [])
            if len(dataForms) < 4:
                session.pop("modelDataAsirVaccinated", None)
            for rawData, form in zip(returnedData, dataForms):
                # TODO: Consider creating vaccinated/unvaccinated asir dataframes
                # here rather than in generateAsir
                # TODO: Make better use of data forms
                # TODO: Consider leaving full errors to runSimulations and
                # simplifying the toasts to just no errors/errors
                data, tag = formatData(rawData, form)
                # Further error checking
                if len(data) == 0:
                    notifyToast(
                        body="""
                        :red-badge[Error]: No data was present on one
                        or more of the files received from the server.
                        Please make sure your parameters do not possess any
                        errors and try again.
                    """,
                        icon=":material/tab_unselected:",
                    )
                elif (
                    tag in {"EpidemicCumulative", "EpidemicDaily"}
                    and len(data["Scenario"].value_counts()) != scenarios
                ):
                    notifyToast(
                        body="""
                            :red-badge[Error]: One or more scenarios
                            were not run correctly by the simulation
                            server. Please ensure all scenarios do not
                            possess any errors and try again.
                        """,
                        icon=":material/donut_small:",
                    )

                else:
                    successes += 1
                    session[f"modelData{tag}"] = data

            # Tell the user what's happened
            session.simulationEndTime = datetime.now()
            totalTime = session.simulationEndTime - session.simulationStartTime
            seconds = str(totalTime.seconds % 60).zfill(2)
            timeString = f"{totalTime.seconds // 60}:{seconds}"
            if successes == len(dataForms):
                notifyToast(
                    f"Simulation complete! Total duration: {timeString}",
                    icon=":material/check_circle:",
                )
            elif successes > 0:
                notifyToast(
                    body=f"""
                Simulation complete, though some analyses had errors.
                Total duration: {timeString}
                    """,
                    icon=":material/flaky:",
                )
            appLog.info(
                f"""
                [updateData] Data processing is complete,
                with {scenarios - successes + 1} errors.
            """
            )
        else:
            appLog.error(
                "[updateData] Received data was atypical. Contents: "
                + str(returnedData)
            )

            # Show different toast messages for different errors
            if isinstance(returnedData, tuple):
                # Errors with exceptions attached
                errorType, e = returnedData
                if errorType == "ClientConnectorError":
                    notifyToast(
                        body="""
                            :red-badge[Error]: Could not connect to the
                            simulation server. Please make sure you are
                            connected to the same network as the server,
                            then try again.
                        """,
                        icon=":material/link_off:",
                    )
                elif errorType == "ClientResponseError500":
                    notifyToast(
                        body="""
                            :red-badge[Error]: The simulation server had an
                            internal error. Please try again later.
                        """,
                        icon=":material/error:",
                    )
                elif errorType == "ValueError":
                    notifyToast(
                        body="""
                            :red-badge[Error]: The data received from the
                            simulation server was incorrectly formatted. Please
                            make sure your parameters do not possess any errors
                            and try again.
                        """,
                        icon=":material/broken_image:",
                    )
                elif errorType == "InvalidSchemaError":
                    notifyToast(
                        body="""
                            :red-badge[Error]: The parameters sent to the
                            server do not match the required format. Please
                            check your parameters for errors and try again.
                        """,
                        icon=":material/schema:",
                    )
                    notifyToast(
                        f":red-badge[Response Body]: {e.response}",
                        icon=":material/breaking_news:",
                    )
                else:
                    notifyToast(
                        body="""
                            :red-badge[Error]: The simulation server
                            encountered an error. Please try again later.
                        """,
                        icon=":material/error:",
                    )
                notifyToast(
                    f":red-badge[Full Error Message]: {e}",
                    icon=":material/breaking_news:",
                )

            # Errors without exception messages to send
            elif isinstance(returnedData, pd.DataFrame):
                notifyToast(
                    body="""
                        :red-badge[Error]: The data was not processed
                        correctly. Please try again later.
                    """,
                    icon=":material/data_alert:",
                )
            elif returnedData == "EmptyZipFile":
                notifyToast(
                    body="""
                        :red-badge[Error]: The simulation server did not
                        return any readable files. Please make sure your
                        parameters do not possess any errors and try again.
                    """,
                    icon=":material/unknown_document:",
                )
            else:
                notifyToast(
                    body="""
                        :red-badge[Error]: An unknown error occurred. Please
                        try again later.
                    """,
                    icon=":material/error:",
                )

        # Re-enable running new simulations and using their data
        session.ChartGenerated = False
        session.simulationInProgress = False
        session.scenariosToUse = session.DataScenarioNames
        st.rerun()


updateData()
