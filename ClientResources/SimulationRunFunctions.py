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
from streamlit_notify import toast  # type: ignore

from ClientResources.DownloadFunctions import createConfig
from ClientResources.InterfaceFunctions import errorChecker
from ClientResources.ParameterFunctions import idGet
from ClientResources.SharedResources import (
    AnalysisFile,
    ageTimeDict,
    ageWithTime,
    currentProgress,
    errorQueue,
    outcomeRateDefaults,
    outcomeRateVariables,
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


class invalidSchemaError(Exception):
    """
    Error class for getting full responses
    """

    # TODO: Flesh out docstrings
    def __init__(self, message, response):
        self.message = message
        self.response = response
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Full Response: {self.response})"


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
        st.markdown(
            f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate the baseline scenario.
    """
        )
    else:
        st.markdown(
            f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate each of the following {scenarioCount + 1} scenarios:
        """
        )
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
        # TODO: Ensure any visualisations show this chart warning
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
            # TODO: Display estimated simulation run time
        st.markdown(
            """
            Are you sure you want to begin running simulations with the
            selected parameters?
        """
        )
        if st.button(
            "Confirm",
            key="confirmRunButton",
            icon="spinner" if runPending else None,
            disabled=runPending,
        ):
            # Set params indicating model is simulating
            session.simulationInProgress = True
            session.simulationStartTime = datetime.now()

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

            session.PendingDataHealthOutcomeRates = {
                outcome: {
                    scenario: idGet(
                        outcomeRateVariables[outcome], i, outcomeRateDefaults[outcome]
                    )
                    for i, scenario in enumerate(scenarioNames)
                }
                for outcome in outcomeRateDefaults.keys()
            }
            """session.PendingDataMortalityRates = {
                scenarioNames[scenarioID]: {
                    idGet("deathAgeGroup", scenarioID, None, f"-{rowID}"): idGet(
                        "deathRatio",
                        scenarioID,
                        outcomeRateDefaults["Deaths"],
                        f"-{rowID}",
                    )
                    for rowID in range(idGet("deathRowCount", scenarioID, 0))
                }
                for scenarioID in range(scenarioCount + 1)
            }"""
            pendingDeaths = {
                scenarioID: idGet("deathRatio", scenarioID, 0.000115077)
                for scenarioID in range(scenarioCount + 1)
            }
            session.PendingDataMortalityRates = {
                scenarioNames[scenarioID]: {
                    age: pendingDeaths[scenarioID] for age in ageWithTime
                }
                | (
                    idGet(
                        "mortAgeForm",
                        scenarioID,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Mortality Rate": [pendingDeaths[scenarioID]],
                            },
                        ),
                    )
                    .dropna()
                    .replace({"Age Group": ageTimeDict})
                    .set_index("Age Group")["Mortality Rate"]
                    .to_dict()
                )
                for scenarioID in range(scenarioCount + 1)
            }

            # Clear the status queue
            currentProgress.append(0.0)
            statusQueue.clear()
            statusQueue.append("Connecting to server...")
            session["simulationError"] = None

            # Make the model call
            runModelWrapper(parameterJSON)

            # TODO: Remember streamlit_push_notifications

            # Generate popup to let the user know it's pending
            toast(
                "Sending a request to run the simulation. Please wait...",
                icon=":material/experiment:",
            )
            st.rerun()


async def runModelStart(parameterJSON: str) -> str:
    """
    Asynchronous function to prompt the server to begin running a simulation.

    Parameters:
        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.

    Returns:
        str: The ID used to obtain information on the simulation.
    """
    # TODO: Ensure wrapper handles errors

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


async def runModelStatus(simulationID: str, parameterJSON: str):
    """
    Async function to get status updates from the server via a websocket

    Parameters:
        simulationID (str): The ID distinguishing this simulation experiment.
    """
    # Generate progress using # of sims/analyses
    # TODO: Include client side processing like formatAsir in this progress
    schema = json.loads(parameterJSON)
    progressDict = {
        "generatingConfig": (0.02, "Initialising parameters..."),
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
    async with ClientSession(base_url=serverUrl) as session:
        async with session.ws_connect(f"/runModel/status/{simulationID}") as ws:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
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
                            functionLog.error(
                                f"[runModelStatus] Error getting {simulationID} status"
                            )
                            raise Exception("An error occurred in the simulation.")
                        case _:
                            progress, status = progressDict[simStatus]
                            currentProgress.append(progress)
                            # Prevent duplicate status messages
                            if status not in statusQueue:
                                statusQueue.append(status)
                elif msg.type == WSMsgType.ERROR:
                    statusQueue.append("Error: Server websocket had issues")
                    socketError = ws.exception()
                    if socketError is not None:
                        raise socketError
                    else:
                        raise RuntimeError(f"WebSocket error: {ws.exception()}")


async def runModelDownload(simulationID: str) -> list[bytes]:
    """
    Asynchronous function to download the results from a complete simulation.

    Parameters:
        simulationID (str): The ID distinguishing this simulation experiment.

    Returns:
        list: The analysis files, unzipped and stored as byte data.
    """
    # TODO: Ensure wrapper handles errors

    # Send POST request to server with parameters
    functionLog.info(
        f"[runModelDownload] Downloading analysis data for sim {simulationID}..."
    )
    async with ClientSession(base_url=serverUrl) as session:
        # Download the analysis files
        async with session.get(f"runModel/download/{simulationID}") as response:
            fileData = await response.read()
            # TODO: Account for server returning JSON when issues occur
            # Unzip data and format each analysis file
            with ZipFile(BytesIO(fileData)) as analyses:
                fileNames = analyses.namelist()
                # for file in fileNames:
                #     functionLog.info(f"File Data: {analyses.read(file).decode()}")
                if len(fileNames) == 0:
                    raise FileNotFoundError("Server returned no readable files")
                try:
                    return [analyses.read(file) for file in fileNames]
                except ValueError as e:
                    raise e


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
            asyncio.run(runModelStatus(simulationID, parameterJSON))

        # TODO: Tidy up the errors
        except Exception as e:
            formatError(e)

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
