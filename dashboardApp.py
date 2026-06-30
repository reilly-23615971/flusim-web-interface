# Flusim Web Interface Application
# Developed by Reilly Evans
# Main program of dashboard, defining pages & setting universal parameters


# Imports
import logging
import os
from datetime import datetime
from functools import partial
from typing import Any

import streamlit as st

# Reload streamlit_notify if it fails the first time
try:
    import streamlit_notify as stn
except ImportError:
    import importlib
    import time

    time.sleep(0.01)
    importlib.reload(importlib.import_module("streamlit_notify"))
    import streamlit_notify as stn

from ClientResources.InterfaceFunctions import timeString
from ClientResources.SharedResources import (
    calcCurrentProgress,
    calcErrorQueue,
    calcResultQueue,
    calibCurrentProgress,
    calibErrorQueue,
    calibResultQueue,
    simCurrentProgress,
    simErrorQueue,
    simResultQueue,
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
        designed by the UWA Infectious Disease Modelling Research Group.
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
    "calibrationInProgress": False,
    "calculationInProgress": False,
    "showSimProgress": False,
    "showCalibProgress": False,
    "showCalcProgress": False,
    "scenarioCount": 0,
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
r0Calculation = st.Page(
    "DashboardPages/r0Calibration.py",
    title="$R_0$ Calibration",
    icon=":material/partner_exchange:",
)
runSimulation = st.Page(
    "DashboardPages/runSimulations.py",
    title="Run Simulations",
    icon=":material/motion_play:",
)
infectionGraphs = st.Page(
    "DashboardPages/infectionCurves.py",
    title="Infection Curves",
    icon=":material/chart_data:",
)
healthTables = st.Page(
    "DashboardPages/healthBurdenTables.py",
    title="Health Burden Tables",
    icon=":material/table_chart_view:",
)

# TODO: Shorten section names, reduce font sizes or increase sidebar width
pages = {
    "Flusim Web Dashboard": [landingPage],
    "Parameter Configuration": [
        modelDescription,
        baselineParameters,
        scenarioParameters,
    ],
    "Conducting Experiments": [r0Calculation, runSimulation],
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
def updateData() -> None:
    """
    Fragment to regularly check if server results have been received yet.
    """
    resultsObtained = False
    # Simulation Results
    simHasResults, simHasError = not simResultQueue.empty(), not simErrorQueue.empty()
    if session.simulationInProgress and (simHasResults or simHasError):
        if simHasResults and not simHasError:
            # Reset pending simulation variables
            # TODO: Add a check to ensure visualisations can't use the new values
            # while this function is still processing the data
            simParams = session["pendingSimParams"]
            session.SimParams = simParams

            # Process data and ensure there is no formatting errors
            returnedData = simResultQueue.get()
            appLog.info(f"[updateData] Processing the following data:\n{returnedData}")

            # Remove any old session data that is no longer valid
            # TODO: Make more robust when number of returned values can vary more
            scenarioCount = len(simParams["Scenario Names"])
            dataForms = simParams["Analysis Formats"]
            if len(dataForms) < 4:
                session.pop("modelDataAsirVaccinated", None)

            # Format data
            formattedData = [formatData(d, f) for d, f in zip(returnedData, dataForms)]

            # Check for any errors in the data
            if any(len(data) == 0 for data in formattedData):
                simErrorQueue.put(
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
                simHasError = True
            elif any(
                form.tool == "epidemic"
                and len(data["Scenario"].value_counts()) != scenarioCount
                for data, form in zip(formattedData, dataForms)
            ):
                simErrorQueue.put(
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
                simHasError = True
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
        if simHasError:
            # Notify user of errors, but leave displaying them to runSimulations
            session["simulationError"] = simErrorQueue.get()
            simCurrentProgress.append(-1.0)
            notifyToast(
                """
Simulation encountered an error; see
:primary-badge[:material/motion_play: Run Simulations] for more.
                """,
                icon=":material/error:",
            )

        # Re-enable running new simulations and using their data
        session.simulationInProgress = False
        session.showSimProgress = True

        resultsObtained = True

    # R0 Calibration Results
    calibHasResults, calibHasError = (
        not calibResultQueue.empty(),
        not calibErrorQueue.empty(),
    )
    if session.calibrationInProgress and (calibHasResults or calibHasError):
        if calibHasResults and not calibHasError:
            # Get calculation results
            calibrationData: dict[str, Any] = calibResultQueue.get()
            appLog.info(
                f"[updateData] Obtained the following calibration data:\n{calibrationData}"
            )
            r0 = calibrationData["r0"]
            lowCI, highCI = calibrationData["interval"]
            beta = calibrationData["beta"]
            scenarioName = session.get("calibScenarioName")
            session["r0Calibration"] = r0
            session["r0CalibrationBeta"] = beta

            # session.calculationEndTime = datetime.now()
            # totalTime = session.calculationEndTime - session.calculationStartTime
            # formattedTime = timeString(totalTime.total_seconds())
            notifyToast(
                f"""
$R_0$ of {r0} for {scenarioName} achieved with transmission value of {beta}
                """,
                icon=":material/partner_exchange:",
            )
            appLog.info("[updateData] R0 calibration is complete.")
        if calibHasError:
            # Notify user of errors, but leave displaying them to runSimulations
            session["calibrationError"] = calibErrorQueue.get()
            calibCurrentProgress.append(-1.0)
            notifyToast(
                """
Error calibrating $R_0$; see
:primary-badge[:material/partner_exchange: $R_0$ Calibration] for more.
                """,
                icon=":material/error:",
            )

        # Re-enable running new simulations and using their data
        session.calibrationInProgress = False
        session.showCalibProgress = True

        resultsObtained = True

    # R0 Calculation Results
    calcHasResults, calcHasError = (
        not calcResultQueue.empty(),
        not calcErrorQueue.empty(),
    )
    if session.calculationInProgress and (calcHasResults or calcHasError):
        if calcHasResults and not calcHasError:
            # Get calculation results
            calculationData: dict[str, Any] = calcResultQueue.get()
            appLog.info(
                f"[updateData] Obtained the following calculation data:\n{calculationData}"
            )
            r0 = calculationData["r0"]
            lowCI, highCI = calculationData["interval"]
            scenarioName = session.get("calcScenarioName")
            session["r0Calculation"] = r0
            session["r0CalculationInterval"] = (lowCI, highCI)

            # session.calculationEndTime = datetime.now()
            # totalTime = session.calculationEndTime - session.calculationStartTime
            # formattedTime = timeString(totalTime.total_seconds())
            notifyToast(
                f"""
$R_0$ for {scenarioName} is {r0} with a 95% confidence interval of [{lowCI}, {highCI}]
                """,
                icon=":material/calculate:",
            )
            appLog.info("[updateData] R0 calculation is complete.")
        if calcHasError:
            # Notify user of errors, but leave displaying them to runSimulations
            session["calculationError"] = calcErrorQueue.get()
            calcCurrentProgress.append(-1.0)
            notifyToast(
                """
Error calculating $R_0$; see
:primary-badge[:material/partner_exchange: $R_0$ Calibration] for more.
                """,
                icon=":material/error:",
            )

        # Re-enable running new simulations and using their data
        session.calculationInProgress = False
        session.showCalcProgress = True

        resultsObtained = True

    # Rerun if results have been updated
    if resultsObtained:
        st.rerun()


updateData()
