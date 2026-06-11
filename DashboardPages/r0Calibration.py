# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
import logging
from datetime import datetime
from threading import Event
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
    import streamlit_notify as stn  # type: ignore

# from streamlit_push_notifications import send_push, send_alert
from ClientResources.DownloadFunctions import createTemplate
from ClientResources.InterfaceFunctions import errorChecker
from ClientResources.ModelSchema import Parameters, communityOverride, overrideTemplate
from ClientResources.ParameterFunctions import loadKey, saveKey
from ClientResources.ServerFunctions import taskWrapper
from ClientResources.SharedResources import (
    calcCurrentProgress,
    calcErrorQueue,
    calcResultQueue,
    calcStatusQueue,
    calibCurrentProgress,
    calibErrorQueue,
    calibResultQueue,
    calibStatusQueue,
    communityPopulation,
    usePresetParams,
)

# Logging
r0Log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
calibrationInProgress = session.calibrationInProgress
calculationInProgress = session.calculationInProgress
calibCancelFlag = Event()
calcCancelFlag = Event()


@st.dialog("Calibrate $R_0$", width="large", icon=":material/partner_exchange:")
def calibrateR0Button() -> None:
    """
    Callback function for the Calibrate R0 button, opening a dialog window
    before performing the calibration.
    """
    # Disable button if it's taking a while to run
    calibPending = bool(session.get("confirmCalibrateButton"))

    # Get scenario to calculate
    scenarioID = session.get("rCalibrateScenario", 0)
    scenarioName = (
        "Baseline Scenario" if scenarioID == 0 else session[f"scenarioName{scenarioID}"]
    )
    targetR0 = session.get("targetR", 1.5)

    # Display any errors
    # TODO: Hide scenario errors that are copies of baseline errors
    severeErrorsFound = errorChecker(scenarioID, f"Errors in {scenarioName}")
    if severeErrorsFound:
        st.error(
            """
                The basic reproduction number cannot be calibrated due to the
                errors displayed above. Please correct these errors before
                calibrating $R_0$.
            """,
            icon=":material/error:",
        )
    else:
        # TODO: Estimate calibration runtime
        st.markdown(f"""
            Are you sure you want to calibrate the basic reproduction
            number to a value of {targetR0} for
            {"the baseline scenario" if scenarioID == 0 else scenarioName}?
        """)
        # TODO: Should precision be a parameter on the dashboard?
        st.info(
            f"""
Due to the iterative methods used to calibrate $R_0$, the basic reproduction
number achieved after calibration may differ from the target value ({targetR0})
by ±0.02.
        """,
            icon=":material/target:",
        )
        if st.button(
            "Confirm",
            key="confirmCalibrateButton",
            icon="spinner" if calibPending else None,
            disabled=calibPending,
        ):
            # Set params indicating model is simulating
            session.calibrationInProgress = True
            session.calibrationStartTime = datetime.now()
            calibCancelFlag.clear()

            # Get relevant settings from session
            showAdvanced = session.get("showAdvanced", False)
            useInterventions = session.get("rCalculateInterventionsToggle", False) if showAdvanced else False
            community = session.get("community", "newcastle")

            # Load JSON
            if usePresetParams:
                filename = f"default{"NoNPI" if useInterventions else ""}.json"
                with open(f"ClientResources/Templates/{filename}", "r") as f:
                    params = Parameters.model_validate_json(f.read())
            else:
                params = createTemplate(
                    scenarioID, includeInterventions=False, includeDashboard=False
                )
            schema = overrideTemplate(
                name=community, description=str(targetR0), parameters=params
            ).model_dump_json(indent=4, exclude_unset=True)
            # TODO: Just save ID instead of name?
            session.calibScenarioName = scenarioName
            session.calibSavedScenarioID = scenarioID

            # Prepare model call parameters
            statusParams = {
                "resultType": "json",
                "statusDecoder": {
                    "start": (0.01, "Initialising parameters..."),
                    "generatingToolbox": (0.02, "Preparing simulation engine..."),
                    "generatingConfig": (0.05, "Calibrating $R_0$..."),
                    "completed": (1.0, "$R_0$ calibrated!"),
                    "error": (-1.0, "Calibration halted due to error"),
                    "shutdown": (
                        -1.0,
                        "Server shut down before calibration could finish",
                    ),
                },
                "progress": calibCurrentProgress,
                "status": calibStatusQueue,
                "results": calibResultQueue,
                "error": calibErrorQueue,
            }

            # Clear the status queue
            calibCurrentProgress.append(0.0)
            calibStatusQueue.clear()
            calibStatusQueue.append("Connecting to server...")
            session["calibrationError"] = None

            # Make the model call
            session.calibrationInProgress = True
            taskWrapper(
                "R0 Calibration",
                "r0/calibrate",
                schema,
                calibCancelFlag,
                statusParams,
            )

            # Generate popup to let the user know it's pending
            stn.toast(
                "Calibrating $R_0$. Please wait...",
                icon=":material/partner_exchange:",
            )
            st.rerun()


@st.dialog("Cancel $R_0$ Calibration", width="large", icon=":material/stop_circle:")
def stopCalibrationButton():
    """
    Callback function for the Calibrate R0 button, opening a dialog window
    before cancelling the currently pending analysis.
    """

    # Disable button if it's taking a while to run
    cancelPending = bool(session.get("confirmCalibCancelButton"))

    st.warning(
        "Are you sure you want to stop calibrating $R_0$?",
        icon=":material/warning:",
    )

    if st.button(
        "Confirm",
        key="confirmCalibCancelButton",
        icon="spinner" if cancelPending else None,
        disabled=cancelPending,
    ):
        # Exit immediately if there's nothing to stop
        if not session.calibrationInProgress:
            stn.toast(
                "$R_0$ is not currently being calibrated; there's nothing to cancel.",
                icon=":material/stop:",
            )
            st.rerun()

        # Display as error on the progress bar
        session["calibrationError"] = (
            "Calibration cancelled",
            "The calibration was manually cancelled by the user.",
            "stop_circle",
            None,
        )
        calibCurrentProgress.append(-1.0)

        # Stop the runModel thread
        calibCancelFlag.set()
        session.calibrationInProgress = False
        session.showCalibProgress = True

        # Generate popup to let the user know it's cancelled
        stn.toast(
            "The calibration has been cancelled.",
            icon=":material/stop_circle:",
        )
        st.rerun()


@st.dialog("Calculate $R_0$", width="large", icon=":material/calculate:")
def calculateR0Button() -> None:
    """
    Callback function for the Calculate R0 button, opening a dialog window
    before running the calculation.
    """
    # Disable button if it's taking a while to run
    calcPending = bool(session.get("confirmCalculateButton"))

    # Get scenario to calculate
    scenarioID = session.get("rCalculateScenario", 0)
    scenarioName = (
        "Baseline Scenario" if scenarioID == 0 else session[f"scenarioName{scenarioID}"]
    )

    # Display any errors
    # TODO: Hide scenario errors that are copies of baseline errors
    severeErrorsFound = errorChecker(scenarioID, f"Errors in {scenarioName}")
    if severeErrorsFound:
        st.error(
            """
                The basic reproduction number cannot be calculated due to the
                errors displayed above. Please correct these errors before
                calculating $R_0$.
            """,
            icon=":material/error:",
        )
    else:
        # TODO: Estimate calculation runtime
        st.markdown(f"""
            Are you sure you want to calculate the basic reproduction number for
            {"the baseline scenario" if scenarioID == 0 else scenarioName}?
        """)
        if st.button(
            "Confirm",
            key="confirmCalculateButton",
            icon="spinner" if calcPending else None,
            disabled=calcPending,
        ):
            # Set params indicating model is simulating
            session.calculationInProgress = True
            session.calculationStartTime = datetime.now()
            calcCancelFlag.clear()

            # Get relevant settings from session
            showAdvanced = session.get("showAdvanced", False)
            useInterventions = session.get("rCalculateInterventionsToggle", False) if showAdvanced else False
            community = session.get("community", "newcastle")

            # Load JSON
            if usePresetParams:
                filename = f"default{"NoNPI" if useInterventions else ""}.json"
                with open(f"ClientResources/Templates/{filename}", "r") as f:
                    params = Parameters.model_validate_json(f.read())
            else:
                params = createTemplate(
                    scenarioID, includeInterventions=False, includeDashboard=False
                )
            schema = communityOverride(
                name=community, parameters=params
            ).model_dump_json(indent=4, exclude_unset=True)
            session.calcScenarioName = scenarioName

            # Prepare model call parameters
            statusParams = {
                "resultType": "json",
                "statusDecoder": {
                    "start": (0.01, "Initialising parameters..."),
                    "generatingToolbox": (0.02, "Preparing simulation engine..."),
                    "generatingConfig": (0.1, "Calculating $R_0$..."),
                    "completed": (1.0, "$R_0$ calculated!"),
                    "error": (-1.0, "Calculation halted due to error"),
                    "shutdown": (
                        -1.0,
                        "Server shut down before calculation could finish",
                    ),
                },
                "progress": calcCurrentProgress,
                "status": calcStatusQueue,
                "results": calcResultQueue,
                "error": calcErrorQueue,
            }

            # Clear the status queue
            calcCurrentProgress.append(0.0)
            calcStatusQueue.clear()
            calcStatusQueue.append("Connecting to server...")
            session["calculationError"] = None

            # Make the model call
            session.calculationInProgress = True
            taskWrapper(
                "R0 Calculation",
                "r0/calculate",
                schema,
                calcCancelFlag,
                statusParams,
            )

            # Generate popup to let the user know it's pending
            stn.toast(
                "Sending a request to calculate $R_0$. Please wait...",
                icon=":material/calculate:",
            )
            st.rerun()


@st.dialog("Cancel $R_0$ Calculation", width="large", icon=":material/stop_circle:")
def stopCalculationButton():
    """
    Callback function for the Calculate R0 button, opening a dialog window
    before cancelling the currently pending analysis.
    """
    # Disable button if it's taking a while to run
    cancelPending = bool(session.get("confirmCalcCancelButton"))

    st.warning(
        "Are you sure you want to stop calculating $R_0$?",
        icon=":material/warning:",
    )

    if st.button(
        "Confirm",
        key="confirmCalcCancelButton",
        icon="spinner" if cancelPending else None,
        disabled=cancelPending,
    ):
        # Exit immediately if there's nothing to stop
        if not session.calculationInProgress:
            stn.toast(
                "$R_0$ is not currently being calculated; there's nothing to cancel.",
                icon=":material/stop:",
            )
            st.rerun()

        # Display as error on the progress bar
        session["calculationError"] = (
            "Calculation cancelled",
            "The calculation was manually cancelled by the user.",
            "stop_circle",
            None,
        )
        calcCurrentProgress.append(-1.0)

        # Stop the runModel thread
        calcCancelFlag.set()
        session.calculationInProgress = False
        session.showCalcProgress = True

        # Generate popup to let the user know it's cancelled
        stn.toast(
            "The calculation has been cancelled.",
            icon=":material/stop_circle:",
        )
        st.rerun()


# Page Content

st.title("$R_0$ Calibration")

st.markdown("""
    This page is used to configure the experiment's parameters to match a desired
    basic reproduction number ($R_0$).
""")

# Global parameters
# Advanced parameters toggle
# TODO: Move advanced parameters to either the sidebar or a separate settings page
loadKey("showAdvanced", default=False, noZeroDefault=True)
showAdvanced = st.toggle(
    "Show Advanced Parameters",
    False,
    key="_showAdvanced",
    on_change=saveKey,
    args=["showAdvanced"],
    help="""
Toggle whether to include parameters that control more fine-grain aspects
of the simulation environment (such as waning vaccine immunity) when calibrating or calculating R0.
    """,
)

# Community Selection
st.markdown("""
    - The community selection determines the population, demographic distribution
    and other elements of the community that is simulated in the calculation, chosen
    from one of two Australian cities.
""")
loadKey("community", default="newcastle")
community = st.selectbox(
    "Simulated Community",
    communityPopulation.keys(),
    key="_community",
    format_func=lambda x: x.capitalize(),
    on_change=saveKey,
    args=["community"],
    help="""
The Australian city whose community data will be used as the
basis for the population and demographic distribution in the
calculation. Note that the data used for these communities comes
from 2011.

##### Options:
- Newcastle: A metropolitan area in New South Wales, Australia.
It has a population of 272407, the second-largest in the state,
and has a demographic distribution that more closely matches
that of Australia as a whole compared to Cairns.
- Cairns: A major city in Queensland, Australia. It has a
population of 140402 (as of 2011 when this data was collected)
and has a higher Indigenous population compared to Newcastle.
    """,
)
scenarioCount = session.get("scenarioCount", 0) + 1
scenarioNames = ["Baseline Scenario"] + [
    session[f"scenarioName{i}"] for i in range(1, scenarioCount)
]

# Calibration

st.header("Calibrate $R_0$")

st.markdown("""
    Select a scenario to calculate the transmission parameter value necessary
    to achieve a specific basic reproduction number.
""")

leftCalib, centerCalib, rightCalib = st.columns(3, vertical_alignment="center")


loadKey("targetR", default=1.5)
leftCalib.number_input(
    label="Target $R_0$",
    min_value=0.0,
    value=1.5,
    format="%0.8g",
    key="_targetR",
    on_change=saveKey,
    args=["targetR"],
    help="""
The desired basic reproduction number, i.e. the average number of new infections
a single infected individual will cause over the course of the infection's
lifespan. Calibrating $R_0$ will identify the experiment parameters needed to
simulate a disease with this basic reproduction number.
    """,
)

loadKey("rCalibrateScenario", default=0)
centerCalib.selectbox(
    "Scenario to Calibrate",
    range(len(scenarioNames)),
    index=0,
    format_func=lambda x: scenarioNames[x],
    key="_rCalibrateScenario",
    on_change=saveKey,
    args=["rCalibrateScenario"],
    help="""
The scenario that the transmission parameters will be calculated for.
"Baseline Scenario" uses the parameters defined at the
:grey-badge[:material/variable_insert: Baseline Parameters] page. Scenarios
defined at the :grey-badge[:material/variable_add: Scenario Parameters] page
are listed by the names assigned to them.
    """,
)

if showAdvanced:
    loadKey("rCalibrateInterventionsToggle", default=False)
    rightCalib.toggle(
        "Include Vaccinations and NPIs",
        False,
        key="_rCalibrateInterventionsToggle",
        on_change=saveKey,
        args=["rCalibrateInterventionsToggle"],
        help="""
    Traditionally, the basic reproduction number is calculated without the influence
    of medical interventions such as vaccination, so they will be excluded from the
    simulation when calculating the parameters necessary to achieve a specific $R_0$.
    Set this toggle to `True` if you wish to match the basic reproduction number
    with interventions in place. 
        """,
    )

# Button to begin calculation
st.button(
    label=("Calibrating $R_0$..." if calculationInProgress else "Calibrate $R_0$"),
    on_click=calibrateR0Button,
    key="_rCalibrateButton",
    disabled=calibrationInProgress,
    type="primary",
    icon="spinner" if calibrationInProgress else ":material/partner_exchange:",
    help=(
        """
Send a request to the *Flusim* model server to run multiple simulations
with the specified parameters, then use the results of these simulations
to determine what transmission parameters achieve the desired $R_0$.
        """
        if not calibrationInProgress
        else """
$R_0$ is currently being calibrated; please wait for the process to complete.
        """
    ),
)


# Stop Simulation Button
if calibrationInProgress:
    st.button(
        label="Cancel $R_0$ Calibration",
        on_click=stopCalibrationButton,
        key="_stopCalib",
        type="primary",
        icon=":material/stop_circle:",
        help="Stop calibrating $R_0$.",
    )

calibResultsContainer = st.empty()

# TODO: Since buttons can't be made in fragments, find a more robust way
# to enusre this appearance is synchronised with the fragment
calibrationResults = session.get("r0Calibration")
idToUpdate = session.get("calibSavedScenarioID")
if calibrationResults is not None and idToUpdate is not None:
    scenarioName = session["calibScenarioName"]
    beta = session["r0CalibrationBeta"]
    def updateBeta():
        """
        Simple callback to update beta to match the calibrated value
        """
        session[f"beta{idToUpdate}"] = beta
        stn.toast(
            f"""
{"The baseline scenario" if idToUpdate == 0 else scenarioName}
now has a basic transmission parameter of {beta}.
            """,
            icon=":material/sync:",
        )

    st.button(
        f"Update Parameters in {scenarioName}",
        icon=":material/sync:",
        on_click=updateBeta,
        help=f"""
Update the value of the basic transmission parameter in
{"the baseline scenario" if idToUpdate == 0 else scenarioName}
to match the calibrated value above.
        """,
    )

# Calculation

st.header("Calculate $R_0$")

st.markdown("""
    Select a scenario to calculate the basic reproduction number obtained
    with its parameter settings.
""")

leftCalc, rightCalc = st.columns(2, vertical_alignment="center")

loadKey("rCalculateScenario", default=0)
leftCalc.selectbox(
    "Scenario to Calculate",
    range(len(scenarioNames)),
    index=0,
    format_func=lambda x: scenarioNames[x],
    key="_rCalculateScenario",
    on_change=saveKey,
    args=["rCalculateScenario"],
    help="""
The scenario that the basic reproduction number will be
calculated for. "Baseline Scenario" uses the parameters defined at the
:grey-badge[:material/variable_insert: Baseline Parameters] page. Scenarios
defined at the :grey-badge[:material/variable_add: Scenario Parameters] page
are listed by the names assigned to them.
    """,
)

if showAdvanced:
    loadKey("rCalculateInterventionsToggle", default=False)
    rightCalc.toggle(
        "Include Vaccinations and NPIs",
        False,
        key="_rCalculateInterventionsToggle",
        on_change=saveKey,
        args=["rCalculateInterventionsToggle"],
        help="""
    Traditionally, the basic reproduction number is calculated without the influence
    of medical interventions such as vaccination, so they will be excluded from the
    simulation when calculating the value of $R_0$. Set this toggle to `True` if you
    wish to calculate the basic reproduction number with interventions in place. 
        """,
    )


# Button to begin calculation
st.button(
    label=("Calculating $R_0$..." if calculationInProgress else "Calculate $R_0$"),
    on_click=calculateR0Button,
    key="_rCalculateButton",
    disabled=calculationInProgress,
    type="primary",
    icon="spinner" if calculationInProgress else ":material/calculate:",
    help=(
        """
Send a request to the *Flusim* model server to run multiple simulations
with the specified parameters, then use the results of these simulations
to estimate a value for $R_0$.
        """
        if not calculationInProgress
        else """
$R_0$ is currently being calculated; please wait for the process to complete.
        """
    ),
)

# TODO: Show Calib Results and dashboardApp additions

calcResultsContainer = st.empty()


@st.fragment(run_every=1)
def showR0Results():
    """
    Fragment to display any errors that occur when calculating R0
    """
    if session.showCalibProgress:
        try:
            progress = calibCurrentProgress[0]
        except IndexError:
            progress = 0.0
            # TODO: Use status to list the estimates that have occurred
            # already in lieu of a progress bar/estimated time
        if progress < 0.0:
            calibContents = calibResultsContainer.container()
            # Display errors that have occurred alongside progress
            errorTitle, errorBody, errorIcon, errorObject = session.get(
                "calibrationError",
                (
                    "Error occurred when calibrating $R_0$",
                    "An unspecified error has occurred while calibrating $R_0$.",
                    "error",
                    None,
                ),
            )
            calibContents.progress(1.0, f":red[:material/error:] {errorTitle}")
            simStatus = calibContents.status(
                label="Calibration stopped due to error (click for more info)",
                state="error",
            )
            simStatus.error(f"Error: {errorBody}", icon=f":material/{errorIcon}:")
            if errorObject is not None:
                simStatus.exception(errorObject)
        elif session.get("r0Calibration") is not None:
            # TODO: Save scenario ID and make descriptions sound natural
            calibContents = calibResultsContainer.container()
            scenarioName = session["calibScenarioName"]
            r0 = session["r0Calibration"]
            beta = session["r0CalibrationBeta"]
            calibContents.metric(
                f"Transmission Parameter Required for $R_0$ of {r0} in {scenarioName}",
                beta,
                border=True,
                help=f"""
The probability that the disease spreads to a new person when they interact with
an infected individual is $1 - \\exp{{(-\\beta}}$ (before accounting for other
factors such as age and location). If $\\beta$ is set to {beta} in the scenario
named {scenarioName}, the disease will have a basic reproduction number equal
to {r0}.
                """,
            )

    if session.showCalcProgress:
        try:
            progress = calcCurrentProgress[0]
        except IndexError:
            progress = 0.0
        if progress < 0.0:
            calcContents = calcResultsContainer.container()
            # Display errors that have occurred alongside progress
            errorTitle, errorBody, errorIcon, errorObject = session.get(
                "calculationError",
                (
                    "Error occurred when calculating $R_0$",
                    "An unspecified error has occurred while calculating $R_0$.",
                    "error",
                    None,
                ),
            )
            calcContents.progress(1.0, f":red[:material/error:] {errorTitle}")
            simStatus = calcContents.status(
                label="Calculation stopped due to error (click for more info)",
                state="error",
            )
            simStatus.error(f"Error: {errorBody}", icon=f":material/{errorIcon}:")
            if errorObject is not None:
                simStatus.exception(errorObject)
        elif session.get("r0Calculation") is not None:
            # TODO: Save scenario ID and make descriptions sound natural
            calcContents = calcResultsContainer.container()
            scenarioName = session["calcScenarioName"]
            r0 = session["r0Calculation"]
            lowCI, highCI = session["r0CalculationInterval"]
            calcContents.metric(
                f"Basic Reproduction Number ($R_0$) for {scenarioName}",
                r0,
                border=True,
                delta_description=f"95% Confidence Interval: [{lowCI}, {highCI}]",
                help=f"""
The basic reproduction number ($R_0$) is the average number of new infections that
will be caused by a single infected individual over the lifespan of their infection.
The scenario named {scenarioName} has an $R_0$ of {r0}.
                """,
            )


# Stop Simulation Button
if calculationInProgress:
    st.button(
        label="Cancel $R_0$ Calculation",
        on_click=stopCalculationButton,
        key="_stopCalc",
        type="primary",
        icon=":material/stop_circle:",
        help="Stop calculating $R_0$.",
    )


showR0Results()
