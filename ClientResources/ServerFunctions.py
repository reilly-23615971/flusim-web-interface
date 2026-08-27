# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to make requests to the server

# Imports
import asyncio
import json
import logging
from collections import deque
from io import BytesIO
from queue import Queue
from threading import Event, Thread
from typing import Literal, overload
from zipfile import ZipFile

import streamlit as st
from aiohttp import (
    ClientConnectorError,
    ClientResponseError,
    ClientSession,
    WSMessageTypeError,
    WSMsgType,
)

from ClientResources.SharedResources import serverUrl

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


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
            if response.status == 422:
                errorText = await response.text()
                # TODO: Unwrap Pydantic errors instead of
                # making them AssertionErrors
                raise AssertionError(
                    "The provided parameters did not comply with the required schema",
                    errorText,
                )
            responseData = await response.json()
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
    async with session.ws_connect(f"/status/{taskID}") as ws:
        async for msg in ws:
            match msg.type:
                case WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    status = data.get("status")
                    functionLog.info(f"[taskStatus] Task {taskID} status: {status}")
                    progress, message = statuses[status]
                    # Prevent duplicate status messages
                    if message not in statusQueue:
                        progressValue.append(progress)
                        statusQueue.append(message)
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
                resultType=statusParams["resultType"],
                statuses=statusParams["statusDecoder"],
                progressValue=statusParams["progress"],
                statusQueue=statusParams["status"],
                resultQueue=statusParams["results"],
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
            formatError(e, taskName, statusParams["error"])
        finally:
            cancelFlag.clear()

    taskThread = Thread(target=threadRunner)
    taskThread.start()


def formatError(e: Exception, taskName: str, errorQueue: Queue):
    """
    Function to format error messages for display on the dashboard.

    Parameters:
        e (Exception): The exception to format.

        taskName (str): The name of the task being completed.

        errorQueue (Queue): The queue to add error details to.
    """

    # Get error message based on error type
    # TODO: Use task name to modify error messages
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
