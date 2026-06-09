# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to make requests to the server for running the simulation

# Imports
import asyncio
import json
import logging
from collections import deque
from datetime import datetime
from io import BytesIO
from queue import Queue
from threading import Event, Thread
from typing import Any, Literal, overload
from zipfile import ZipFile

import pandas as pd
import streamlit as st
from aiohttp import (
    ClientConnectorError,
    ClientResponseError,
    ClientSession,
    WSMessageTypeError,
    WSMsgType,
)

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
    communityPopulation,
    saveJSON,
    serverUrl,
    simCurrentProgress,
    simErrorQueue,
    simResultQueue,
    simStatusQueue,
    splitPoint,
    usePresetParams,
)

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

cancelSimThread = Event()


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
    # TODO: Remake estimates without constant waning
    # since it results in massive overestimates
    return round((0.0948297101449275 * days - 2.977807971014478) * runs * scenarios)


def healthOutcomeStore(
    scenarioNames: list[str], useAges: bool = True
) -> tuple[dict, dict]:
    """
    Function to format and store health burden outcome rates for a given set
    of scenarios.

    Parameters:
        scenarioNames (list of str): The names of each scenario defined in
            the simulation.

        useAges (Boolean): Set to False to ignore age-specific health burdens
            and define each of their values to be the same baseline value.

    Returns:
        tuple of dicts: A pair of dictionaries storing the global and age-specific
            health burden rates.
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
    """ageRates = {
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

    return singleRates, ageRates


def runModelProgress(
    scenarioNames: list[str], useVaccines: bool = False
) -> dict[str, tuple[float, str]]:
    """
    Function to generate the status dictionary used for the simulation progress bar.

    Parameters:
        scenarioNames (list of str): The names of the scenarios in the simulation.

        useVaccines (bool): Set to `True` to add an extra status point for
            vaccine-based infections.

    Returns:
        dict: A dictionary matching short status strings to tuples containing
            a float (the percentage of the progress bar to fill) and a string
            (the description of the step represented by this status)
    """
    # TODO: Include client side processing like formatAsir in this progress
    # TODO: Fake mid-simulation progress with estimated times
    progressDict = {
        "start": (0.01, "Initialising parameters..."),
        "generatingConfig": (0.02, "Preparing simulation engine..."),
        "zippingAnalysis": (0.98, "Compiling results..."),
        "completed": (1.0, "Simulation complete!"),
        "error": (-1.0, "Experiment halted due to error"),
        "shutdown": (-1.0, "Server shut down before experiment could finish"),
    }

    # Scenario status
    scenarioSegments = (splitPoint - 0.02) / len(scenarioNames)
    progressDict |= {
        f"runningSim{i}": (
            scenarioSegments * i + 0.02,
            f'Running scenario "{name}"...',
        )
        for i, name in enumerate(scenarioNames)
    }
    # Analysis status
    # Note that ASIR gets twice the progress length as epidemic
    if useVaccines:
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
    return progressDict


@st.dialog("Run Simulation Experiment", width="large", icon=":material/motion_play:")
def runSimulationButton() -> None:
    """
    Callback function for the Run Simulation button, opening a dialog window
    before running the simulation itself.
    """
    # Disable button if it's taking a while to run
    runPending = bool(session.get("confirmRunButton"))

    # List scenarios
    scenarioCount = session.get("scenarioCount", 0) + 1
    if scenarioCount == 1:
        st.markdown(f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate the baseline scenario.
        """)
    else:
        st.markdown(f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate each of the following {scenarioCount} scenarios:
        """)
        with st.container() if scenarioCount < 11 else st.expander("Scenario Names"):
            st.markdown(
                "- Baseline\n"
                + "\n".join(
                    f"- {session[f'scenarioName{id}']}"
                    for id in range(1, scenarioCount)
                )
            )

    # Display any errors
    # TODO: Hide scenario errors that are copies of baseline errors
    severeErrorsFound = False
    for id in range(scenarioCount):
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
        estimatedTime = runtimeEstimate(cycleCount, runCount, scenarioCount)
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
                parameterJSON = createConfig(
                    scenarioCount, includeDashboard=False
                ).model_dump_json(indent=4, exclude_unset=True)
                if saveJSON:
                    with open("./savedJSON.json", "w") as file:
                        file.write(parameterJSON)
                scenarioNames = ["Baseline"] + [
                    session[f"scenarioName{i}"] for i in range(1, scenarioCount)
                ]

            # Save current parameter values that'll be used for
            # visualisation when the user has potentially changed them
            simParams: dict[str, Any] = {"Scenario Names": scenarioNames}
            community = session.get("community", "newcastle")
            simParams["Community"] = community
            schema = json.loads(parameterJSON)
            useAdvanced = session.get("showAdvanced", False)
            useVaccines = "+vaccine" in schema.get("middle_joint")
            if useVaccines:
                simParams["Analysis Formats"] = [
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
                simParams["Analysis Formats"] = [
                    AnalysisFile(
                        tool="epidemic", names=scenarioNames, useCumulative=True
                    ),
                    AnalysisFile(
                        tool="epidemic", names=scenarioNames, useCumulative=False
                    ),
                    AnalysisFile(tool="asir", names=scenarioNames),
                ]

            simParams["Scaling Factor"] = (
                session.get("scalingPopulation", communityPopulation[community])
                / communityPopulation[community]
            )
            simParams["Asymptomatic Rates"] = (
                [
                    [
                        1 - idGet("asymptomaticChild", scenarioID, 0.35),
                        1 - idGet("asymptomaticAdult", scenarioID, 0.35),
                    ]
                    for scenarioID in range(scenarioCount)
                ]
                if useAdvanced
                else [
                    [1 - idGet("asymptomaticAdult", scenarioID, 0.35)] * 2
                    for scenarioID in range(scenarioCount)
                ]
            )
            healthOutcomeRates, mortalityRates = healthOutcomeStore(
                scenarioNames,
                useAges=useAdvanced,
            )
            simParams["Health Outcome Rates"] = healthOutcomeRates
            simParams["Age-Separated Health Outcome Rates"] = mortalityRates
            simParams["Waning In Simulation"] = useAdvanced and any(
                idGet("naturalWaningToggle", scenarioID, False)
                or (
                    idGet("vaccineToggle", scenarioID, False)
                    and (
                        idGet("vaccineWaningToggle", scenarioID, False)
                        or idGet("boosterToggle", scenarioID, False)
                    )
                )
                for scenarioID in range(scenarioCount)
            )

            session.pendingSimParams = simParams

            # Prepare model call parameters
            statusParams = {
                "resultType": "zip",
                "statusDecoder": runModelProgress(scenarioNames, useVaccines),
                "progress": simCurrentProgress,
                "status": simStatusQueue,
                "results": simResultQueue,
                "error": simErrorQueue,
            }

            # Clear the status queue
            simCurrentProgress.append(0.0)
            simStatusQueue.clear()
            simStatusQueue.append("Connecting to server...")
            session["simulationError"] = None

            # Make the model call
            # runModelWrapper(parameterJSON)
            session.simulationInProgress = True
            taskWrapper(
                "Simulation Experiment",
                "runModel",
                parameterJSON,
                cancelSimThread,
                statusParams,
            )

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
        simCurrentProgress.append(-1.0)

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


# Server contact functions


async def taskStart(route: str, parameterJSON: str) -> str:
    """
    Async function to prompt the server to begin a task via a POST request.

    Parameters:
        route (str): The URL route to contact.

        parameterJSON (str): A string containing the JSON to include in the server call.

    Returns:
        str: The ID used in future requests to obtain the task's status and results.

    Raises:
        ClientResponseError: If the server responds with an unsuccessful error
            code (4XX or 5XX).

        AssertionError: If the server responds with error code 422, i.e. if
            `parameterJSON` is rejected by the server's validation model.


    """

    # Send POST request to server with parameters
    schema = json.loads(parameterJSON)
    functionLog.info(f"[taskStart] Initialising session with base url {serverUrl}...")
    functionLog.info(f"[taskStart] Contacting {serverUrl}/{route}...")
    async with ClientSession(raise_for_status=False, base_url=serverUrl) as client:
        async with client.post(route, json=schema) as response:
            responseData = await response.json()
            if response.status == 422:
                # TODO: Unwrap Pydantic errors instead of
                # making them AssertionErrors
                raise AssertionError(
                    "The provided parameters did not comply with the required schema",
                    response.text(),
                )
            response.raise_for_status()
            taskID = responseData["taskID"]
        functionLog.info(f"[taskStart] Task ID: {taskID}")
        return taskID


async def taskMonitor(flag: Event) -> None:
    """
    Async function to wait until the cancellation flag is set before progressing.

    Parameters:
        flag (Event): The flag to wait for.
    """
    while True:
        if flag.is_set():
            return
        await asyncio.sleep(0.25)


async def taskCancel(taskID: str):
    """
    Async function to cancel a running task.

    Parameters:
        taskID (str): The ID distinguishing this server task.
    """
    # Send DELETE request to server with parameters
    functionLog.info(f"[taskCancel] Cancelling task {taskID}...")
    async with ClientSession(base_url=serverUrl) as client:
        async with client.delete(f"cancel/{taskID}"):
            functionLog.info(f"[taskCancel] Task {taskID} successfully cancelled.")


@overload
async def taskResults(
    route: str, taskID: str, resultType: Literal["zip"]
) -> list[bytes]: ...


@overload
async def taskResults(route: str, taskID: str, resultType: Literal["json"]) -> dict: ...


async def taskResults(route: str, taskID: str, resultType: str) -> list[bytes] | dict:
    """
    Async function to retrieve the results from a completed task.

    Parameters:
        route (str): The URL route to contact.

        taskID (str): The ID distinguishing this server task.

        resultType (str): A string indicating the format the results
            should be interpreted as.

    Returns:
        list or dict: If `resultType` is `zip`, returns a list of analysis files,
            unzipped and stored as byte data. If `resultType` is `json`, returns
            a dictionary representation of the JSON data.

    Raises:
        FileNotFoundError: If the server returns an empty zip file.

        JSONDecodeError: If the results cannot be decoded from JSON.

        ValueError: If `resultType` is not one of the accepted options or the
            results cannot be unzipped. Notes are used to distinguish these
            two error circumstances.

    """

    # Send POST request to server with parameters
    functionLog.info(f"[taskDownload] Downloading results for task {taskID}...")
    async with ClientSession(base_url=serverUrl) as client:
        # Download the analysis files
        async with client.get(f"{route}/results/{taskID}") as response:
            fileData = await response.read()
            match resultType:
                case "zip":
                    # Unzip data and format each analysis file
                    with ZipFile(BytesIO(fileData)) as analyses:
                        fileNames = analyses.namelist()
                        if len(fileNames) == 0:
                            raise FileNotFoundError("Server returned no readable files")
                        try:
                            return [analyses.read(file) for file in fileNames]
                        except ValueError as e:
                            e.add_note("zip")
                            raise e
                case "json":
                    return json.loads(fileData)
                case _:
                    raise ValueError("Unrecognised result type")


async def taskStatus(
    session: ClientSession,
    taskID: str,
    route: str,
    resultType: Literal["zip", "json"],
    statuses: dict[str, tuple[float, str]],
    progressValue: deque[float],
    statusQueue: list[str],
    resultQueue: Queue,
):
    """
    Async function to get status updates from the server via a websocket

    Parameters:
        session (ClientSession): The `aiohttp` session to open the websocket on.

        taskID (str): The ID distinguishing this server task.

        route (str): The URL route to contact for this task.

        resultType (str): A string indicating the format of the results.

        statuses (dict): A dictionary used to decode status messages
            returned by the server.

        progressValue (deque of float): A deque used to store the percentage
            of the task that has been completed.

        statusQueue (list of str): A list used to store the status messages
            noting the steps of the task that have been completed.

        resultQueue (Queue): A queue used to store the results of the task.

    Raises:
        RuntimeError: If the server returns the `error` status.

        PythonFinalisationError: If the server returns the `shutdown` status.

        WSMessageTypeError: If the websocket cannot be found.
    """

    # TODO: Finish genericising
    async with session.ws_connect(f"/status/{taskID}") as ws:
        async for msg in ws:
            match msg.type:
                case WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    status = data.get("status")
                    functionLog.info(f"[taskStatus] Task {taskID} status: {status}")
                    progress, message = statuses[status]
                    # Prevent duplicate status messages
                    if message not in simStatusQueue:
                        progressValue.append(progress)
                        statusQueue.append(status)
                    # End the websocket if certain statuses are returned
                    match status:
                        case "completed":
                            # Download the analysis files
                            results = await taskResults(route, taskID, resultType)
                            resultQueue.put(results)
                            return
                        case "error":
                            functionLog.error(f"""
[taskStatus] Server encountered an error while running the task {taskID}
                            """)
                            raise RuntimeError("""
An error occurred while the server was completing the request.
                            """)
                        case "shutdown":
                            functionLog.error(f"""
[taskStatus] Server shut down while running the task {taskID}
                            """)
                            raise PythonFinalizationError("""
The simulation server shut down while attempting to complete the task.
                            """)
                case WSMsgType.CLOSE:
                    if msg.data == 1008:
                        statusQueue.append("Error: Server websocket not found")
                        raise WSMessageTypeError(
                            "Websocket with requested ID not found"
                        )
                    # TODO: Account for other closures
                case WSMsgType.ERROR:
                    statusQueue.append("Error: Server websocket had issues")
                    socketError = ws.exception()
                    if socketError is not None:
                        raise socketError
                    else:
                        raise WSMessageTypeError(f"WebSocket error: {ws.exception()}")


async def taskWebsocket(route: str, taskID: str, cancelFlag: Event, statusParams: dict):
    """
    Async function to monitor the server websocket and cancel if requested

    Parameters:
        route (str): The URL route to contact for this task.

        taskID (str): The ID distinguishing this server task.

        cancelFlag (Event): The flag to indicate that the task should be cancelled.

        statusParams (dict): A dictionary compiling the parameters used for monitoring
            the task, namely the status dictionary and the queues specific
            to this task.
    """

    async with ClientSession(base_url=serverUrl) as client:
        statusTask = asyncio.create_task(
            taskStatus(
                client,
                taskID,
                route,
                statusParams["resultType"],
                statusParams["statusDecoder"],
                statusParams["progress"],
                statusParams["status"],
                statusParams["results"],
            )
        )
        monitorTask = asyncio.create_task(taskMonitor(cancelFlag))

        # Continue when either results are downloaded or monitor stops
        finishedTask, incompleteTask = await asyncio.wait(
            [statusTask, monitorTask], return_when=asyncio.FIRST_COMPLETED
        )
        for task in incompleteTask:
            task.cancel()

        # Cancel the sim if monitor was first
        if monitorTask in finishedTask:
            # Cancel the simulation
            await taskCancel(taskID)
            return
        else:
            statusTask.result()


def taskWrapper(
    taskName: str,
    route: str,
    parameterJSON: str,
    cancelFlag: Event,
    statusParams: dict,
):
    """
    Async wrapper function for server tasks, allowing HTTP requests to be made
    asynchronously without blocking Streamlit operations.

    Parameters:
        taskName (str): The name of the task being completed.

        route (str): The URL route to contact for this task.

        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.

        cancelFlag (Event): The flag to indicate that the task should be cancelled.

        statusParams (dict): A dictionary compiling the parameters used for monitoring
            the task, namely the status dictionary and the queues specific
            to this task.
    """

    def threadRunner():
        """
        Inner function to asynchronously call the server and await results,
        needed to avoid interrupting Streamlit UI functionality.
        """
        try:
            # Get task ID
            taskID = asyncio.run(taskStart(route, parameterJSON))

            # Open the websocket
            asyncio.run(taskWebsocket(route, taskID, cancelFlag, statusParams))

        except Exception as e:
            # TODO: Add taskName as parameter for formatError
            formatError(e, statusParams["error"])
        finally:
            cancelFlag.clear()

    taskThread = Thread(target=threadRunner)
    taskThread.start()


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
    async with session.ws_connect(f"/status/{simulationID}") as ws:
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
                            simData: list = await taskResults(
                                "runModel/download", simulationID, "zip"
                            )
                            simResultQueue.put(simData)
                            simCurrentProgress.append(1.0)
                            simStatusQueue.append("Simulation complete!")
                            return
                        case "error":
                            # TODO: Better error handling
                            simStatusQueue.append("Experiment halted due to error")
                            functionLog.error(f"""
[runModelStatus] Server encountered an error while running the simulation {simulationID}
                            """)
                            raise RuntimeError("""
An error occurred while attempting to run the simulation.
                            """)
                        case "shutdown":
                            simStatusQueue.append(
                                "Server shut down before experiment could finish"
                            )
                            functionLog.error(f"""
[runModelStatus] Server shut down while running the simulation {simulationID}
                            """)
                            raise PythonFinalizationError("""
The simulation server shut down while attempting to run the simulation.
                            """)
                        case _:
                            progress, status = progressDict[simStatus]
                            # Prevent duplicate status messages
                            if status not in simStatusQueue:
                                simCurrentProgress.append(progress)
                                simStatusQueue.append(status)
                case WSMsgType.CLOSE:
                    if msg.data == 1008:
                        raise WSMessageTypeError(
                            "Websocket with requested ID not found"
                        )
                case WSMsgType.ERROR:
                    simStatusQueue.append("Error: Server websocket had issues")
                    socketError = ws.exception()
                    if socketError is not None:
                        raise socketError
                    else:
                        raise WSMessageTypeError(f"WebSocket error: {ws.exception()}")


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
        monitorTask = asyncio.create_task(taskMonitor(cancelSimThread))

        # Continue when either results are downloaded or monitor stops
        finishedTask, incompleteTask = await asyncio.wait(
            [statusTask, monitorTask], return_when=asyncio.FIRST_COMPLETED
        )
        for task in incompleteTask:
            task.cancel()

        # Cancel the sim if monitor was first
        if monitorTask in finishedTask:
            # Cancel the simulation
            await taskCancel(simulationID)
            return
        else:
            statusTask.result()


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
            simulationID = asyncio.run(taskStart("runModel", parameterJSON))

            # Open the websocket
            asyncio.run(runModelWebsocket(simulationID, parameterJSON))

        except Exception as e:
            formatError(e, simErrorQueue)
        finally:
            cancelSimThread.clear()

    session.simulationInProgress = True
    runModelThread = Thread(target=threadRunner)
    runModelThread.start()


def formatError(e: Exception, errorQueue: Queue):
    """
    Function to format error messages for display on the dashboard.

    Parameters:
        e (Exception): The exception to format.

        errorQueue (Queue): The queue to add error details to.
    """
    # Get error message based on error type
    # TODO: Use task type (sim, r0 calc etc) to modify error messages
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
        case WSMessageTypeError():
            errorShort = "Websocket encountered an error"
            errorBody = """
The websocket used to monitor the simulation server had an internal error.
Please check your network connection and try again.
            """
            errorIcon = "plug_connect"
        # TODO: Account for other ValueErrors (e.g. bad resultType)
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
        # TODO: Catch JSONDecodeError
        case PythonFinalizationError():
            errorShort = "Server shut down while running simulation"
            errorBody = """
The simulation server shut down while the simulation experiment was
running. Please try again later once the simulation server is restarted.
            """
            errorIcon = "power_off"
        case _:
            errorShort = "Error occurred when running simulation"
            errorBody = """
An error occurred when attempting to run the simulation experiment. Please
try again later.
            """
            errorIcon = "error"

    # Add to the queue
    functionLog.error(f"[taskWrapper] {errorShort}: {e}")
    errorQueue.put((errorShort, errorBody, errorIcon, e))
