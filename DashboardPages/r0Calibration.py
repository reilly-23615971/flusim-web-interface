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
from ClientResources.ModelSchema import Parameters, communityOverride
from ClientResources.ParameterFunctions import loadKey, saveKey
from ClientResources.ServerFunctions import taskWrapper
from ClientResources.SharedResources import (
    calcCurrentProgress,
    calcErrorQueue,
    calcResultQueue,
    calcStatusQueue,
    communityPopulation,
    usePresetParams,
)

# Logging
r0Log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
calculationInProgress = session.calculationInProgress
calcCancelFlag = Event()


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
            useInterventions = session.get("rCalculateInterventionsToggle", False)
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
                "Simulation Experiment",
                "runModel",
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

# TODO: Calibration

st.header("Calculate $R_0$")

st.markdown("""
    Select a scenario to calculate the basic reproduction number obtained
    with its parameter settings.
""")

leftCol, rightCol = st.columns(2, vertical_alignment="center")
scenarioCount = session.get("scenarioCount", 0) + 1
scenarioNames = ["Baseline Scenario"] + [
    session[f"scenarioName{i}"] for i in range(1, scenarioCount)
]

loadKey("rCalculateScenario", default=0)
indexToCalculate = leftCol.selectbox(
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
loadKey("rCalculateInterventionsToggle", default=False)
includeInterventions = rightCol.toggle(
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
# TODO: Either allow multiple unrelated server tasks or use different inProgress
# variables to indicate whether the calculation is running or
# another task is preventing it
st.button(
    label=("Running calculation..." if calculationInProgress else "Calculate $R_0$"),
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
A simulation is already running; please wait for it to conclude
before running another one.
        """
    ),
)


@st.fragment(run_every=1)
def showCalcResults():
    """
    Fragment to display any errors that occur when calculating R0
    """
    try:
        progress = calcCurrentProgress[0]
    except IndexError:
        progress = 0.0
    if progress < 0.0:
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
        st.progress(1.0, f":red[:material/error:] {errorTitle}")
        simStatus = st.status(
            label="Calculation stopped due to error (click for more info)",
            state="error",
        )
        simStatus.error(f"Error: {errorBody}", icon=f":material/{errorIcon}:")
        if errorObject is not None:
            simStatus.exception(errorObject)
    else:
        scenarioName = session["calcScenarioName"]
        r0 = session["r0Calculation"]
        lowCI, highCI = session["r0CalculationInterval"]
        st.metric(
            f"Basic Reproduction Number ($R_0$) for {scenarioName}",
            r0,
            delta_description=f"95% Confidence Interval: [{lowCI}, {highCI}]",
            help="""
The basic reproduction number is the average number of new infections that will
be caused by a single infected individual over the lifespan of their infection.
            """,
        )


if session.showCalcProgress:
    showCalcResults()

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
