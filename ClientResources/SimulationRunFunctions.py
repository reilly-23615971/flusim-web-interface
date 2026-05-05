# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to make requests to the server for running the simulation

# Imports
import asyncio
import json
import logging
import threading
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import streamlit as st
from aiohttp import ClientConnectorError, ClientResponseError, ClientSession, WSMsgType

# Reload streamlit_notify if it fails the first time
try:
    import streamlit_notify as stn
except ImportError:
    import importlib
    import time

    time.sleep(0.01)
    importlib.reload(importlib.import_module("streamlit_notify"))
    import streamlit_notify as stn  # type: ignore

from ClientResources.DownloadFunctions import createConfig
from ClientResources.InterfaceFunctions import errorChecker, timeString
from ClientResources.ParameterFunctions import idGet
from ClientResources.SharedResources import (
    AnalysisFile,
    ageTimeDict,
    ageWithTime,
    currentProgress,
    errorQueue,
    resultQueue,
    saveJSON,
    serverUrl,
    splitPoint,
    statusQueue,
    usePresetParams,
)

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

cancelSimThread = threading.Event()


def runtimeEstimate(days: int, runs: int, scenarios: int) -> int:
    """
    Simple function estimating how long a simulation will take based on its
    length. This uses a linear function derived from testing at various lengths
    with default parameters (excluding immunity waning, which is as low as possible
    to ensure constant infections). The actual length of a given simulation is
    dependent on the number of infections, so this estimate is only a rough guess.

    Parameters:
        days (int): The number of days the simulation will run for.

        runs (int): The number of simulation runs that will be done for each scenario.

        scenarios (int): The number of scenarios defined in the simulation.

    Returns:
        int: The estimated number of seconds the simulation will run for.
    """
    return round((0.0948297101449275 * days - 2.977807971014478) * runs * scenarios)


def healthOutcomeStore(
    singleKey: str, ageKey: str, scenarioNames: list[str], useAges: bool = True
):
    """
    Function to format and store health burden outcome rates for a given set
    of scenarios.

    Parameters:
        singleKey (str): The `st.session_state` key for health burdens that
            are not age-specific.

        ageKey (str): The `st.session_state` key for health burdens that
            are age-specific.

        scenarioNames (list of str): The names of each scenario defined in
            the simulation.

        useAges (Boolean): Set to False to ignore age-specific health burdens
            and define each of their values to be the same baseline value.
    """
    # Required values for outcome rates
    icuKey, icuDefault, icuFormat = "icuRatio", 20.0, lambda x: x / 100
    deathKey, deathDefault, deathFormat = "deathRatio", 12.0, lambda x: x / 100000
    outcomeRates = {
        "Diagnosed Cases": ("caseRatio", 50.0, lambda x: x / 100),
        "GP Visits": ("gpRatio", 17.0, lambda x: x / 100),
        "Hospitalisations": ("hospitalRatio", 320.0, lambda x: x / 100000),
        "Deaths": (deathKey, deathDefault, deathFormat),
    }

    # Basic rates (not age-specific)
    singleRates = {}
    for outcome, (key, default, formatFunc) in outcomeRates.items():
        singleRates[outcome] = {
            scenario: formatFunc(idGet(key, i, default))
            for i, scenario in enumerate(scenarioNames)
        }

    # ICU (dependent on hospitalisation)
    singleRates["ICU Visits"] = {
        scenario: singleRates["Hospitalisations"][scenario]
        * icuFormat(idGet(icuKey, i, icuDefault))
        for i, scenario in enumerate(scenarioNames)
    }

    # Deaths (age-specific)
    """session.PendingDataMortalityRates = {
        scenarioNames[scenarioID]: {
            idGet("deathAgeGroup", scenarioID, None, f"-{rowID}"): deathFormat(
                idGet(deathKey, scenarioID, deathDefault, f"-{rowID}")
            )
            for rowID in range(idGet("deathRowCount", scenarioID, 0))
        }
        for scenarioID in range(scenarioCount + 1)
    }"""
    ageRates = {}
    for scenarioID, name in enumerate(scenarioNames):
        baseDeathRate = deathFormat(idGet(deathKey, scenarioID, deathDefault))
        if useAges:
            mortAgeForm = idGet(
                "mortAgeForm",
                scenarioID,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Mortality Rate": [baseDeathRate],
                    },
                ),
            ).copy()
            mortAgeForm["Mortality Rate"] = mortAgeForm["Mortality Rate"].apply(
                deathFormat
            )
            mortAgeDict = (
                mortAgeForm.dropna()
                .replace({"Age Group": ageTimeDict})
                .set_index("Age Group")["Mortality Rate"]
                .to_dict()
            )
        else:
            mortAgeDict = {}
        ageRates[name] = {age: baseDeathRate for age in ageWithTime} | mortAgeDict

    session[singleKey] = singleRates
    session[ageKey] = ageRates


@st.dialog("Run Simulation Experiment", width="large", icon=":material/motion_play:")
def runSimulationButton():
    """
    Callback function for the Run Simulation button, opening a dialog window
    before running the simulation itself.
    """
    # Disable button if it's taking a while to run
    runPending = bool(session.get("confirmRunButton"))

    # List scenarios
    scenarioCount = session.get("scenarioCount", 0)
    if scenarioCount == 0:
        st.markdown(f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate the baseline scenario.
    """)
    else:
        st.markdown(f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate each of the following {scenarioCount + 1} scenarios:
        """)
        with st.container() if scenarioCount < 10 else st.expander("Scenario Names"):
            st.markdown(
                "- Baseline\n"
                + "\n".join(
                    f"- {session[f'scenarioName{id}']}"
                    for id in range(1, scenarioCount + 1)
                )
            )

    # Display any errors
    # TODO: Hide scenario errors that are copies of baseline errors
    severeErrorsFound = False
    for id in range(scenarioCount + 1):
        severeErrorsFound = (
            errorChecker(
                id,
                f"Errors in {session[f'scenarioName{id}'] if id > 0 else 'Baseline'}",
            )
            or severeErrorsFound
        )
    if severeErrorsFound:
        st.error(
            """
                The simulation cannot be ran due to the errors displayed above.
                Please correct these errors before running the simulation.
            """,
            icon=":material/error:",
        )
    else:
        if session.get("ChartGenerated"):
            st.warning(
                """
Running a new simulation will result in future tables and graphs using
the new simulation's data. Please make sure to save any tables or graphs
you wish to keep with the current simulation data before running a new
simulation.
        """,
                icon=":material/bar_chart_off:",
            )

        # Get estimated simulation runtime
        cycleCount = session.get("cycleCount", 360)
        runCount = session.get("runCount", 24)
        estimatedTime = runtimeEstimate(cycleCount, runCount, scenarioCount + 1)
        st.metric(
            f"Estimated Time to Run Simulation Experiment",
            value=timeString(estimatedTime),
            border=True,
            help="""
This estimate is based on the length of each simulation run, the number of runs
per scenario and the number of scenarios you have defined. The actual duration
of the simulation experiment may differ from this estimate depending on other
simulation parameters, as well as whether or not the simulation server is
already busy with a different task.
            """,
        )
        st.markdown("""
            Are you sure you want to begin running simulations with the
            selected parameters?
        """)
        if st.button(
            "Confirm",
            key="confirmRunButton",
            icon="spinner" if runPending else None,
            disabled=runPending,
        ):
            # Set params indicating model is simulating
            session.simulationInProgress = True
            session.simulationStartTime = datetime.now()
            cancelSimThread.clear()

            # Create the final model JSON
            # Load debug parameters from file
            if usePresetParams:
                with open("ClientResources/defaultParams.guide.json", "r") as f:
                    parameterJSON = f.read()
                scenarioNames = [
                    "Baseline",
                    "School Closure",
                    "Case Isolation",
                    "Community Contact Reduction",
                ]

            # Create JSON for selected parameters
            else:
                parameterJSON = createConfig(scenarioCount + 1).model_dump_json(
                    indent=4, exclude_unset=True  # , exclude_defaults = True
                )
                if saveJSON:
                    with open("./savedJSON.json", "w") as file:
                        file.write(parameterJSON)
                scenarioNames = ["Baseline"] + [
                    session[f"scenarioName{i}"] for i in range(1, scenarioCount + 1)
                ]

            # Save current parameter values that'll be used for
            # visualisation when the user has potentially changed them
            useAdvanced = session.get("showAdvanced", False)
            schema = json.loads(parameterJSON)
            if "+vaccine" in schema.get("middle_joint"):
                session.PendingDataForms = [
                    AnalysisFile(
                        tool="epidemic", names=scenarioNames, useCumulative=True
                    ),
                    AnalysisFile(
                        tool="epidemic", names=scenarioNames, useCumulative=False
                    ),
                    AnalysisFile(tool="asir", names=scenarioNames),
                    AnalysisFile(tool="asir", names=scenarioNames, vaccinated=True),
                ]
            else:
                session.PendingDataForms = [
                    AnalysisFile(
                        tool="epidemic", names=scenarioNames, useCumulative=True
                    ),
                    AnalysisFile(
                        tool="epidemic", names=scenarioNames, useCumulative=False
                    ),
                    AnalysisFile(tool="asir", names=scenarioNames),
                ]
            session.PendingDataCommunity = session.get("community", "newcastle")
            session.PendingDataScenarioNames = scenarioNames
            session.PendingDataScenarioCount = scenarioCount
            session.PendingDataAsymptomatic = (
                [
                    [
                        1 - idGet("asymptomaticChild", scenarioID, 0.35),
                        1 - idGet("asymptomaticAdult", scenarioID, 0.35),
                    ]
                    for scenarioID in range(scenarioCount + 1)
                ]
                if useAdvanced
                else [
                    [1 - idGet("asymptomaticBoth", scenarioID, 0.35)] * 2
                    for scenarioID in range(scenarioCount + 1)
                ]
            )

            healthOutcomeStore(
                "PendingDataHealthOutcomeRates",
                "PendingDataMortalityRates",
                scenarioNames,
                useAges=useAdvanced,
            )

            # Clear the status queue
            currentProgress.append(0.0)
            statusQueue.clear()
            statusQueue.append("Connecting to server...")
            session["simulationError"] = None

            # Make the model call
            runModelWrapper(parameterJSON)

            # TODO: Remember streamlit_push_notifications

            # Generate popup to let the user know it's pending
            stn.toast(
                "Sending a request to run the simulation. Please wait...",
                icon=":material/experiment:",
            )
            st.rerun()


@st.dialog("Cancel Simulation", width="large", icon=":material/stop_circle:")
def stopSimulationButton():
    """
    Callback function for the Cancel Simulation button, opening a dialog window
    before cancelling the currently pending simulation.
    """
    # Disable button if it's taking a while to run
    cancelPending = bool(session.get("confirmCancelButton"))

    st.warning(
        "Are you sure you want to cancel the currently running simulation?",
        icon=":material/warning:",
    )

    if st.button(
        "Confirm",
        key="confirmCancelButton",
        icon="spinner" if cancelPending else None,
        disabled=cancelPending,
    ):
        # Exit immediately if there's nothing to stop
        if not session.simulationInProgress:
            stn.toast(
                "No simulations are currently running; there's nothing to cancel.",
                icon=":material/stop:",
            )
            st.rerun()

        # Display as error on the progress bar
        session["simulationError"] = (
            "Simulation cancelled",
            "The simulation was manually cancelled by the user.",
            "stop_circle",
            None,
        )
        currentProgress.append(-1.0)

        # Stop the runModel thread
        cancelSimThread.set()
        session.simulationInProgress = False
        session.keepProgressBar = True

        # Generate popup to let the user know it's cancelled
        stn.toast(
            "The simulation has been cancelled.",
            icon=":material/stop_circle:",
        )
        st.rerun()


async def runModelStart(parameterJSON: str) -> str:
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
    functionLog.info(
        f"[runModelStart] Initialising session with base url {serverUrl}..."
    )
    async with ClientSession(raise_for_status=False, base_url=serverUrl) as session:
        async with session.post("runModel", json=schema) as response:
            responseData = await response.json()
            if response.status == 422:
                # TODO: Unwrap Pydantic errors instead of
                # making them AssertionErrors
                raise AssertionError(
                    """
The provided parameters did not comply with the simulation's model schema
                    """,
                    response.text(),
                )
            response.raise_for_status()
            simulationID = responseData["simulationID"]
        functionLog.info(f"[runModelStart] Sim ID: {simulationID}")
        return simulationID


async def runModelMonitor(simulationID: str):
    """
    Async function to wait until the cancellation flag is set before progressing

    Parameters:
        simulationID (str): The ID distinguishing this simulation experiment.
    """
    while True:
        if cancelSimThread.is_set():
            return simulationID
        await asyncio.sleep(0.25)


async def runModelStatus(session: ClientSession, simulationID: str, parameterJSON: str):
    """
    Async function to get status updates from the server via a websocket

    Parameters:
        session: The `aiohttp` session to open the websocket on.

        simulationID (str): The ID distinguishing this simulation experiment.

        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.
    """
    # Generate progress using # of sims/analyses
    # TODO: Include client side processing like formatAsir in this progress
    # TODO: Fake mid-simulation progress with estimated times
    schema = json.loads(parameterJSON)
    progressDict = {
        "start": (0.01, "Initialising parameters..."),
        "generatingConfig": (0.02, "Preparing simulation engine..."),
        "zippingAnalysis": (0.98, "Compiling results..."),
    }

    # Scenario status
    schemaSims = schema["simulation_sets"][0]["simulations"]
    scenarioCount = len(schemaSims)
    scenarioSegments = (splitPoint - 0.02) / scenarioCount
    progressDict |= {
        f"runningSim{i}": (
            scenarioSegments * i + 0.02,
            f'Running scenario "{sim["name"]}"...',
        )
        for i, sim in enumerate(schemaSims)
    }
    # Analysis status
    # Note that ASIR gets twice the progress length as epidemic
    if "+vaccine" in schema.get("middle_joint"):
        analysisSegments = (1 - splitPoint - 0.02) / 6
        progressDict |= {
            "toolboxAnalysis0": (
                splitPoint,
                "Extracting cumulative infections...",
            ),
            "toolboxAnalysis1": (
                analysisSegments + splitPoint,
                "Extracting daily infections...",
            ),
            "toolboxAnalysis2": (
                3 * analysisSegments + splitPoint,
                "Extracting age-based infections...",
            ),
            "toolboxAnalysis3": (
                5 * analysisSegments + splitPoint,
                "Extracting vaccine-based infections...",
            ),
        }
    else:
        analysisSegments = (1 - splitPoint - 0.02) / 4
        progressDict |= {
            "toolboxAnalysis0": (splitPoint, "Extracting cumulative infections..."),
            "toolboxAnalysis1": (
                analysisSegments + splitPoint,
                "Extracting daily infections...",
            ),
            "toolboxAnalysis2": (
                3 * analysisSegments + splitPoint,
                "Extracting age-based infections...",
            ),
        }
    async with session.ws_connect(f"/runModel/status/{simulationID}") as ws:
        async for msg in ws:
            match msg.type:
                case WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    simStatus = data.get("status")
                    functionLog.info(
                        f"[runModelStatus] Sim {simulationID} status: {simStatus}"
                    )
                    match simStatus:
                        case "completed":
                            # Download the analysis files
                            simData = await runModelDownload(simulationID)
                            resultQueue.put(simData)
                            currentProgress.append(1.0)
                            statusQueue.append("Simulation complete!")
                            return
                        case "error":
                            # TODO: Better error handling
                            statusQueue.append("Experiment halted due to error")
                            functionLog.error(f"""
[runModelStatus] Server encountered an error while running the simulation {simulationID}
                                """)
                            raise Exception("""
An error occurred while attempting to run the simulation.
                                """)
                        case _:
                            progress, status = progressDict[simStatus]
                            # Prevent duplicate status messages
                            if status not in statusQueue:
                                currentProgress.append(progress)
                                statusQueue.append(status)
                case WSMsgType.CLOSE:
                    if msg.data == 1008:
                        raise RuntimeError("Websocket with requested ID not found")
                case WSMsgType.ERROR:
                    statusQueue.append("Error: Server websocket had issues")
                    socketError = ws.exception()
                    if socketError is not None:
                        raise socketError
                    else:
                        raise RuntimeError(f"WebSocket error: {ws.exception()}")


async def runModelWebsocket(simulationID: str, parameterJSON: str):
    """
    Async function to monitor the server websocket and cancel if requested

    Parameters:
        simulationID (str): The ID distinguishing this simulation experiment.

        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.
    """
    async with ClientSession(base_url=serverUrl) as session:
        statusTask = asyncio.create_task(
            runModelStatus(session, simulationID, parameterJSON)
        )
        monitorTask = asyncio.create_task(runModelMonitor(simulationID))

        # Continue when either results are downloaded or monitor stops
        finishedTask, incompleteTask = await asyncio.wait(
            [statusTask, monitorTask], return_when=asyncio.FIRST_COMPLETED
        )
        for task in incompleteTask:
            task.cancel()

        # Cancel the sim if monitor was first
        if monitorTask in finishedTask:
            # Cancel the simulation
            await runModelCancel(simulationID)
            return
        else:
            statusTask.result()


async def runModelDownload(simulationID: str) -> list[bytes]:
    """
    Async function to download the results from a complete simulation.

    Parameters:
        simulationID (str): The ID distinguishing this simulation experiment.

    Returns:
        list: The analysis files, unzipped and stored as byte data.
    """
    # Send POST request to server with parameters
    functionLog.info(
        f"[runModelDownload] Downloading analysis data for sim {simulationID}..."
    )
    async with ClientSession(base_url=serverUrl) as session:
        # Download the analysis files
        async with session.get(f"runModel/download/{simulationID}") as response:
            fileData = await response.read()
            # Unzip data and format each analysis file
            with ZipFile(BytesIO(fileData)) as analyses:
                fileNames = analyses.namelist()
                if len(fileNames) == 0:
                    raise FileNotFoundError("Server returned no readable files")
                try:
                    return [analyses.read(file) for file in fileNames]
                except ValueError as e:
                    raise e


async def runModelCancel(simulationID: str):
    """
    Async function to cancel a running simulation.

    Parameters:
        simulationID (str): The ID distinguishing this simulation experiment.
    """

    # Send DELETE request to server with parameters
    functionLog.info(f"[runModelCancel] Cancelling sim {simulationID}...")
    async with ClientSession(base_url=serverUrl) as session:
        async with session.delete(f"runModel/cancel/{simulationID}"):
            functionLog.info(
                f"[runModelCancel] Sim {simulationID} successfully cancelled."
            )


def runModelWrapper(parameterJSON):
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
        try:
            # Get simulation ID
            simulationID = asyncio.run(runModelStart(parameterJSON))

            # Open the websocket
            asyncio.run(runModelWebsocket(simulationID, parameterJSON))

        except Exception as e:
            formatError(e)
        finally:
            cancelSimThread.clear()

    session.simulationInProgress = True
    runModelThread = threading.Thread(target=threadRunner)
    runModelThread.start()


def formatError(e: Exception):
    """
    Function to format error messages for display on the dashboard

    Parameters:
        e (Exception): The exception to format.
    """
    # Get error message based on error type
    match e:
        case ClientConnectorError():
            errorShort = "Couldn't connect to server"
            errorBody = """
Could not connect to the simulation server. Please make sure you are connected
to the same network as the server, then try again.
            """
            errorIcon = "link_off"
        case ClientResponseError():
            match e.status:
                # TODO: Make sure these errors only show up in the described cases
                # (or have even finer-grain distinguishing between them)
                case 404:
                    errorShort = "Simulation ID not found"
                    errorBody = """
The dashboard attempted to access a simulation using the wrong ID. Please
refresh the page or clear your browser cache and try again.
                    """
                case 500:
                    errorShort = "Internal server error"
                    errorBody = """
The simulation server had an internal error. Please try again later.
                    """
                case 503:
                    errorShort = "Results not ready"
                    errorBody = """
The dashboard attempted to obtain the results of the simulation before the
simulation was complete. Please try again later.
                    """
                case _:
                    errorShort = f"Server returned status {e.status}"
                    errorBody = """
An error occurred when attempting to contact the simulation server. Please
try again later.
                    """
            errorIcon = "http"
        case AssertionError():
            errorShort = "Server failed to validate parameters"
            errorBody = """
The server encountered an error when attempting to validate the simulation
parameters. Please make sure that all parameters are set to the right values
before trying again.
            """
            errorIcon = "schema"
        case RuntimeError():
            errorShort = "Websocket encountered an error"
            errorBody = """
The websocket used to monitor the simulation server had an internal error.
Please check your network connection and try again.
            """
            errorIcon = "plug_connect"
        case ValueError():
            errorShort = "Error unzipping analysis files"
            errorBody = """
The results generated by the server could not be extracted properly. Please
make sure your parameters do not possess any errors and try again.
            """
            errorIcon = "folder_zip"
        case FileNotFoundError():
            errorShort = "Server returned no readable files"
            errorBody = """
The simulation server did not return any readable files. Ensure your
parameters do not result in a simulation where nobody is infected and try again.
            """
            errorIcon = "unknown_document"
        case _:
            errorShort = "Error occurred when running simulation"
            errorBody = """
An error occurred when attempting to run the simulation experiment. Please
try again later.
            """
            errorIcon = "error"

    # Add to the queue
    functionLog.error(f"[runModel] {errorShort}: {e}")
    errorQueue.put((errorShort, errorBody, errorIcon, e))
