# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
import json
import logging
from datetime import datetime
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
from ClientResources.InterfaceFunctions import errorChecker, timeString
from ClientResources.ModelSchema import Parameters, communityOverride
from ClientResources.ParameterFunctions import (
    containerSave,
    loadKey,
    saveKey,
    timeScaleChange,
)
from ClientResources.SharedResources import (
    calcCurrentProgress,
    calcStatusQueue,
    communityPopulation,
    usePresetParams,
)
from ClientResources.SimulationRunFunctions import (
    runSimulationButton,
    stopSimulationButton,
)

# Logging
r0Log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
calculationInProgress = session.calculationInProgress


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


@st.dialog("Calculate $R_0$", width="large", icon=":material/calculate:")
def calculateR0Button():
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
            cancelCalcThread = threading.Event()

            # Get relevant settings from session
            useInterventions = session.get("rCalculateInterventionsToggle", False)
            community = session.get("community", "newcastle")

            # Load debug parameters from file
            if usePresetParams:
                filename = f"default{"NoNPI" if useInterventions else ""}.json"
                with open(f"ClientResources/Templates/{filename}", "r") as f:
                    params = Parameters.model_validate_json(f.read())
            else:
                params = createTemplate(
                    scenarioID, includeInterventions=False, includeDashboard=False
                )

            # Save current parameter values that'll be used for
            # visualisation when the user has potentially changed them
            schema = communityOverride(
                name=community, parameters=params
            ).model_dump_json(indent=4, exclude_unset=True)

            # Save current parameter values that'll be used for
            # visualisation when the user has potentially changed them
            calcParams: dict[str, Any] = {"Scenario": scenarioName}
            calcParams["Community"] = community
            calcParams["Interventions In Simulation"] = useInterventions

            session.pendingCalcParams = calcParams

            # TODO: Finish this once regular runSimulations is more genericised

            # Clear the status queue
            calcCurrentProgress.append(0.0)
            calcStatusQueue.clear()
            calcStatusQueue.append("Connecting to server...")
            session["simulationError"] = None

            # Make the model call
            # runModelWrapper(parameterJSON)

            # Generate popup to let the user know it's pending
            stn.toast(
                "Sending a request to calculate $R_0$. Please wait...",
                icon=":material/calculate:",
            )
            st.rerun()


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


# TODO: Below this point is placeholder test buttons and their functions
# Imports
import asyncio
import json
import logging
import threading

import streamlit as st
from aiohttp import ClientSession

# Reload streamlit_notify if it fails the first time
try:
    import streamlit_notify as stn
except ImportError:
    import importlib
    import time

    time.sleep(0.01)
    importlib.reload(importlib.import_module("streamlit_notify"))
    import streamlit_notify as stn  # type: ignore

from ClientResources.DownloadFunctions import createTemplate
from ClientResources.SharedResources import serverUrl


def testCalc():
    """
    Barebones test for R0 calculation.
    """
    # Load debug parameters from file
    defaultParams = createTemplate(
        0, includeInterventions=False, includeDashboard=False
    )

    # Save current parameter values that'll be used for
    # visualisation when the user has potentially changed them
    calibrationParams = communityOverride(name="newcastle", parameters=defaultParams)
    schema = calibrationParams.model_dump_json(indent=4, exclude_unset=True)

    # Make the model call
    testCalcWrapper(schema)

    # TODO: Remember streamlit_push_notifications

    # Generate popup to let the user know it's pending
    stn.toast(
        "Request sent.",
        icon=":material/experiment:",
    )


async def testCalcStart(parameterJSON: str):
    """
    Async function to prompt the server to begin running a simulation.

    Parameters:
        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.

    Returns:
        str: The ID used to obtain information on the simulation.
    """

    # Send POST request to server with parameters
    schema = json.loads(parameterJSON)
    async with ClientSession(raise_for_status=False, base_url=serverUrl) as session:
        async with session.post("r0/calculate", json=schema) as response:
            await response.json()


def testCalcWrapper(parameterJSON):
    """
    Async wrapper function for runModel, allowing HTTP requests to be made
    asynchronously without blocking Streamlit operations.

    Parameters:
        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.
    """

    # Inner function to asynchronously call the server and await results
    # Needed to avoid interrupting Streamlit UI functionality
    def threadRunner():
        """
        Inner function to asynchronously call the server and await results,
        needed to avoid interrupting Streamlit UI functionality.
        """
        asyncio.run(testCalcStart(parameterJSON))

    runModelThread = threading.Thread(target=threadRunner)
    runModelThread.start()


# Placeholder calculation button
st.button(
    label="Test $R_0$ Calculation",
    on_click=testCalc,
    key="_testcalc",
    type="primary",
)
