# Flusim Web Interface Application
# Developed by Reilly Evans
# Main program of dashboard, defining pages & setting universal parameters


# Imports
import logging
import os
from datetime import datetime

import streamlit as st

from ClientResources.InterfaceFunctions import time_string
from ClientResources.Types import (
    R0_CALCULATION_STATUS,
    R0_CALIBRATION_STATUS,
    SIM_STATUS,
    SimParams,
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
        ### Additional Credits
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
sessionParameters = {
    "simulation_in_progress": False,
    "calibrationInProgress": False,
    "calculationInProgress": False,
    "showSimProgress": False,
    "showCalibProgress": False,
    "showCalcProgress": False,
    "scenario_count": 0,
    "scenario_names": ["Baseline Scenario"],
    "scenario_extra_params": {},
    "scenario_set_params": {},
    "active_errors": {0: {}},
}
for parameter, default in sessionParameters.items():
    session[parameter] = session.get(parameter, default)

# TODO: Load defaults from influenza template instead of hardcoding

# TODO: See if an extra cookie package like streamlit-cookie-controller
# can preserve parameters between refreshed pages

st.logo(image=":material/microbiology:")


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

# Initialise and run the application pages
flusimPages = st.navigation(pages)
flusimPages.run()

st.sidebar.link_button(
    "User Manual", "/app/static/UserManual.pdf", icon=":material/quick_reference:"
)


@st.fragment(run_every=1)
def update_data() -> None:
    """
    Fragment to regularly check if server results have been received yet.
    """
    resultsObtained = False
    # Simulation Results
    simHasResults, simHasError = (
        not SIM_STATUS.results.empty(),
        not SIM_STATUS.errors.empty(),
    )
    if session.simulation_in_progress and (simHasResults or simHasError):
        if simHasResults and not simHasError:
            # Reset pending simulation variables
            # TODO: Add a check to ensure visualisations can't use the new values
            # while this function is still processing the data
            current_params: SimParams = session["pending_sim_params"]
            session.sim_params = current_params

            # Process data and ensure there is no formatting errors
            returnedData = SIM_STATUS.results.get()
            appLog.info(f"[update_data] Processing the following data:\n{returnedData}")

            # Remove any old session data that is no longer valid
            # TODO: Make more robust when number of returned values can vary more
            scenario_count = len(current_params.scenario_names)
            dataForms = current_params.analysis_formats
            if len(dataForms) < 4:
                session.pop("modelDataAsirVaccinated", None)

            # Format data
            formattedData = [formatData(d, f) for d, f in zip(returnedData, dataForms)]

            # Check for any errors in the data
            if any(len(data) == 0 for data in formattedData):
                SIM_STATUS.errors.put(
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
                and len(data["Scenario"].value_counts()) != scenario_count
                for data, form in zip(formattedData, dataForms)
            ):
                SIM_STATUS.errors.put(
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
                formattedTime = time_string(totalTime.total_seconds())
                st.toast(
                    f"Simulation complete! Total duration: {formattedTime}",
                    icon=":material/check_circle:",
                    duration="infinite",
                )
                appLog.info("[update_data] Data processing is complete.")
                session.ChartGenerated = False
        if simHasError:
            # Notify user of errors, but leave displaying them to runSimulations
            session["simulationError"] = SIM_STATUS.errors.get()
            SIM_STATUS.progress.append(-1.0)
            st.toast(
                """
Simulation encountered an error; see
:primary-badge[:material/motion_play: Run Simulations] for more.
                """,
                icon=":material/error:",
                duration="infinite",
            )

        # Re-enable running new simulations and using their data
        session.simulation_in_progress = False
        session.showSimProgress = True

        resultsObtained = True

    # R0 Calibration Results
    calibHasResults, calibHasError = (
        not R0_CALIBRATION_STATUS.results.empty(),
        not R0_CALIBRATION_STATUS.results.empty(),
    )
    if session.calibrationInProgress and (calibHasResults or calibHasError):
        if calibHasResults and not calibHasError:
            # Get calculation results
            calibrationData = R0_CALIBRATION_STATUS.results.get()
            appLog.info(
                f"[update_data] Obtained the following calibration data:\n{calibrationData}"
            )
            if isinstance(calibrationData, dict):
                r0 = calibrationData["r0"]
                lowCI, highCI = calibrationData["interval"]
                beta = calibrationData["beta"]
                scenario_name = session.get("calib_scenario_name")
                session["r0Calibration"] = r0
                session["r0CalibrationBeta"] = beta

                # session.calculationEndTime = datetime.now()
                # totalTime = session.calculationEndTime - session.calculationStartTime
                # formattedTime = time_string(totalTime.total_seconds())

                st.toast(
                    f"""
                $R_0$ of {r0} for {scenario_name} achieved with transmission value of {beta}
                """,
                    icon=":material/partner_exchange:",
                    duration="infinite",
                )
                appLog.info("[update_data] R0 calibration is complete.")
            else:
                R0_CALIBRATION_STATUS.errors.put(
                    (
                        "Calibration results were incorrectly formatted",
                        """
The results of the $R_0$ calibration process were formatted incorrectly. This
is likely an error with the server; contact a developer to resolve the issue.
                    """,
                        "error",
                        None,
                    )
                )
                calibHasError = True
        if calibHasError:
            # Notify user of errors, but leave displaying them to runSimulations
            session["calibrationError"] = R0_CALIBRATION_STATUS.errors.get()
            R0_CALIBRATION_STATUS.progress.append(-1.0)
            st.toast(
                """
Error calibrating $R_0$; see
:primary-badge[:material/partner_exchange: $R_0$ Calibration] for more.
                """,
                icon=":material/error:",
                duration="infinite",
            )

        # Re-enable running new simulations and using their data
        session.calibrationInProgress = False
        session.showCalibProgress = True

        resultsObtained = True

    # R0 Calculation Results
    calcHasResults, calcHasError = (
        not R0_CALCULATION_STATUS.results.empty(),
        not R0_CALCULATION_STATUS.errors.empty(),
    )
    if session.calculationInProgress and (calcHasResults or calcHasError):
        if calcHasResults and not calcHasError:
            # Get calculation results
            calculationData = R0_CALCULATION_STATUS.results.get()
            appLog.info(
                f"[update_data] Obtained the following calculation data:\n{calculationData}"
            )
            if isinstance(calculationData, dict):
                r0 = calculationData["r0"]
                lowCI, highCI = calculationData["interval"]
                scenario_name = session.get("calcScenarioName")
                session["r0Calculation"] = r0
                session["r0CalculationInterval"] = (lowCI, highCI)

                # session.calculationEndTime = datetime.now()
                # totalTime = session.calculationEndTime - session.calculationStartTime
                # formattedTime = time_string(totalTime.total_seconds())
                st.toast(
                    f"""
    $R_0$ for {scenario_name} is {r0} with a 95% confidence interval of [{lowCI}, {highCI}]
                    """,
                    icon=":material/calculate:",
                )
                appLog.info("[update_data] R0 calculation is complete.")
            else:
                R0_CALCULATION_STATUS.errors.put(
                    (
                        "Calculation results were incorrectly formatted",
                        """
The results of the $R_0$ calculation process were formatted incorrectly. This
is likely an error with the server; contact a developer to resolve the issue.
                    """,
                        "error",
                        None,
                    )
                )
                calibHasError = True
        if calcHasError:
            # Notify user of errors, but leave displaying them to runSimulations
            session["calculationError"] = R0_CALCULATION_STATUS.errors.get()
            R0_CALCULATION_STATUS.progress.append(-1.0)
            st.toast(
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


update_data()
