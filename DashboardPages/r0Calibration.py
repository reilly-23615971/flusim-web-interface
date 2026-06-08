# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
import json
import logging

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
from ClientResources.DownloadFunctions import uploadDownloadBar
from ClientResources.ModelSchema import communityOverride, modelGuideFile
from ClientResources.ParameterFunctions import (
    containerSave,
    loadKey,
    saveKey,
    timeScaleChange,
)
from ClientResources.SharedResources import (
    communityPopulation,
    currentProgress,
    statusQueue,
)
from ClientResources.SimulationRunFunctions import (
    runSimulationButton,
    stopSimulationButton,
)

# Logging
r0Log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
simulationInProgress = session.simulationInProgress


# Page Content

st.title("$R_0$ Calibration")

st.markdown("""
    This page is used to configure the experiment's parameters to match a desired
    basic reproduction number ($R_0$).
""")

st.header("TODO")


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
    defaultParams = createTemplate(0, includeInterventions=False, includeDashboard=False)

    # Save current parameter values that'll be used for
    # visualisation when the user has potentially changed them
    calibrationParams = communityOverride(
        name="newcastle", parameters=defaultParams
    )
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
