# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to make requests to the server

# Imports
import asyncio
import json
import logging
from io import BytesIO
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

from resources.constants import SERVER_URL
from resources.types import RequestStatus

# Logging
server_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


async def start_task(route: str, parameter_json: str) -> str:
    """
    Async function to prompt the server to begin a task via a POST request.

    Parameters:
        route (str): The URL route to contact.

        parameter_json (str): A string containing the JSON to include in the
            server call.

    Returns:
        str: The ID used in future requests to obtain the task's status and
            results.

    Raises:
        ClientResponseError: If the server responds with an unsuccessful error
            code (4XX or 5XX).

        AssertionError: If the server responds with error code 422, i.e. if
            `parameter_json` is rejected by the server's validation model.
    """

    # Send POST request to server with parameters
    schema = json.loads(parameter_json)
    server_log.info(f"[start_task] Initialising session with base url {SERVER_URL}...")
    server_log.info(f"[start_task] Contacting {SERVER_URL}/{route}...")
    async with ClientSession(raise_for_status=False, base_url=SERVER_URL) as client:
        async with client.post(route, json=schema) as response:
            if response.status == 422:
                error_text = await response.text()
                # TODO: Unwrap Pydantic errors instead of making them AssertionErrors
                raise AssertionError(
                    "The provided parameters did not "
                    "comply with the required schema",
                    error_text,
                )
            response_data = await response.json()
            response.raise_for_status()
            task_id = response_data["task_id"]
        server_log.info(f"[start_task] Task ID: {task_id}")
        return task_id


async def wait_for_flag(flag: Event) -> None:
    """
    Async function to wait until the cancellation flag is set before
    progressing.

    Parameters:
        flag (Event): The flag to wait for.
    """
    while True:
        if flag.is_set():
            return
        await asyncio.sleep(0.25)


async def cancel_task(task_id: str):
    """
    Async function to cancel a running task.

    Parameters:
        task_id (str): The ID distinguishing this server task.
    """
    # Send DELETE request to server with parameters
    server_log.info(f"[cancel_task] Cancelling task {task_id}...")
    async with ClientSession(base_url=SERVER_URL) as client:
        async with client.delete(f"cancel/{task_id}"):
            server_log.info(f"[cancel_task] Task {task_id} successfully cancelled.")


@overload
async def get_task_results(
    route: str, task_id: str, result_type: Literal["zip"]
) -> list[bytes]: ...


@overload
async def get_task_results(
    route: str, task_id: str, result_type: Literal["json"]
) -> dict: ...


async def get_task_results(
    route: str, task_id: str, result_type: str
) -> list[bytes] | dict:
    """
    Async function to retrieve the results from a completed task.

    Parameters:
        route (str): The URL route to contact.

        task_id (str): The ID distinguishing this server task.

        result_type (str): A string indicating the format the results
            should be interpreted as.

    Returns:
        list or dict: If `result_type` is `zip`, returns a list of analysis
            files, unzipped and stored as byte data. If `result_type` is
            `json`, returns a dictionary representation of the JSON data.

    Raises:
        FileNotFoundError: If the server returns an empty zip file.

        JSONDecodeError: If the results cannot be decoded from JSON.

        ValueError: If `result_type` is not one of the accepted options or the
            results cannot be unzipped. Notes are used to distinguish these
            two error circumstances.

    """

    # Send POST request to server with parameters
    server_log.info(f"[get_task_results] Downloading results for task {task_id}...")
    async with ClientSession(base_url=SERVER_URL) as client:
        # Download the analysis files
        async with client.get(f"{route}/results/{task_id}") as response:
            file_data = await response.read()
            match result_type:
                case "zip":
                    # Unzip data and format each analysis file
                    with ZipFile(BytesIO(file_data)) as analyses:
                        file_names = analyses.namelist()
                        if len(file_names) == 0:
                            raise FileNotFoundError("Server returned no readable files")
                        try:
                            return [analyses.read(file) for file in file_names]
                        except ValueError as e:
                            e.add_note("zip")
                            raise e
                case "json":
                    return json.loads(file_data)
                case _:
                    raise ValueError("Unrecognised result type")


async def get_task_status(
    session: ClientSession,
    task_id: str,
    route: str,
    result_type: Literal["zip", "json"],
    status_decoder: dict[str, tuple[float, str]],
    request_queue: RequestStatus,
):
    """
    Async function to get status updates from the server via a websocket

    Parameters:
        session (ClientSession): The `aiohttp` session to open the websocket on.

        task_id (str): The ID distinguishing this server task.

        route (str): The URL route to contact for this task.

        result_type (str): A string indicating the format of the results.

        status_decoder (dict): A dictionary used to decode status messages
            returned by the server.

        request_queue (RequestStatus): An object bundling together lists and
            queues used to store the status and results of the task.

    Raises:
        RuntimeError: If the server returns the `error` status.

        PythonFinalisationError: If the server returns the `shutdown` status.

        WSMessageTypeError: If the websocket cannot be found.
    """
    async with session.ws_connect(f"/status/{task_id}") as ws:
        async for msg in ws:
            match msg.type:
                case WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    status = data.get("status")
                    server_log.info(
                        f"[get_task_status] Task {task_id} status: {status}"
                    )
                    progress, message = status_decoder[status]
                    # Prevent duplicate status messages
                    if message not in request_queue.tasks:
                        request_queue.progress.append(progress)
                        request_queue.tasks.append(message)
                    # End the websocket if certain statuses are returned
                    match status:
                        case "completed":
                            # Download the analysis files
                            results = await get_task_results(
                                route, task_id, result_type
                            )
                            request_queue.results.put(results)
                            return
                        case "error":
                            server_log.error(
                                "[get_task_status] Server encountered an "
                                f"error while running the task {task_id}"
                            )
                            raise RuntimeError(
                                "An error occurred while the server "
                                "was completing the request."
                            )
                        case "shutdown":
                            server_log.error(
                                "[get_task_status] Server shut down "
                                f"while running the task {task_id}"
                            )
                            raise PythonFinalizationError(
                                "The simulation server shut down "
                                "while attempting to complete the task."
                            )
                case WSMsgType.CLOSE:
                    if msg.data == 1008:
                        request_queue.tasks.append("Error: Server websocket not found")
                        raise WSMessageTypeError(
                            "Websocket with requested ID not found"
                        )
                    # TODO: Account for other reasons to close the websocket
                case WSMsgType.ERROR:
                    request_queue.tasks.append("Error: Server websocket had issues")
                    socket_error = ws.exception()
                    if socket_error is not None:
                        raise socket_error
                    else:
                        raise WSMessageTypeError(f"WebSocket error: {ws.exception()}")


async def monitor_task_websocket(
    route: str, task_id: str, cancel_flag: Event, status_params: dict
):
    """
    Async function to monitor the server websocket and cancel if requested

    Parameters:
        route (str): The URL route to contact for this task.

        task_id (str): The ID distinguishing this server task.

        cancel_flag (Event): The flag to indicate that the task should be
            cancelled.

        status_params (dict): A dictionary compiling the parameters used for
            monitoring the task, namely the status dictionary and the queues
            specific to this task.
    """

    async with ClientSession(base_url=SERVER_URL) as client:
        status_task = asyncio.create_task(
            get_task_status(
                client,
                task_id,
                route,
                result_type=status_params["result_type"],
                status_decoder=status_params["status_decoder"],
                request_queue=status_params["request_queue"],
            )
        )
        waiting_task = asyncio.create_task(wait_for_flag(cancel_flag))

        # Continue when either results are downloaded or cancel flag is set
        finished_task, incomplete_task = await asyncio.wait(
            [status_task, waiting_task], return_when=asyncio.FIRST_COMPLETED
        )
        for task in incomplete_task:
            task.cancel()

        # Cancel the sim if monitor was first
        if waiting_task in finished_task:
            # Cancel the simulation
            await cancel_task(task_id)
            return
        else:
            status_task.result()


def task_wrapper(
    task_name: str,
    route: str,
    parameter_json: str,
    cancel_flag: Event,
    status_params: dict,
):
    """
    Async wrapper function for server tasks, allowing HTTP requests to be made
    asynchronously without blocking Streamlit operations.

    Parameters:
        task_name (str): The name of the task being completed.

        route (str): The URL route to contact for this task.

        parameter_json (str): A string containing the JSON representation of
            the simulation experiment to run.

        cancel_flag (Event): The flag to indicate that the task should be
            cancelled.

        status_params (dict): A dictionary compiling the parameters used for
            monitoring the task, namely the status dictionary and the queues
            specific to this task.
    """

    def thread_runner():
        """
        Inner function to asynchronously call the server and await results,
        needed to avoid interrupting Streamlit UI functionality.
        """
        try:
            # Get task ID
            task_id = asyncio.run(start_task(route, parameter_json))

            # Open the websocket
            asyncio.run(
                monitor_task_websocket(route, task_id, cancel_flag, status_params)
            )

        except Exception as e:
            format_server_error(e, task_name, status_params["error"])
        finally:
            cancel_flag.clear()

    taskThread = Thread(target=thread_runner)
    taskThread.start()


def format_server_error(e: Exception, task_name: str, request_queue: RequestStatus):
    """
    Function to format error messages for display on the dashboard.

    Parameters:
        e (Exception): The exception to format.

        task_name (str): The name of the task being completed. Currently unused.

        request_queue (RequestStatus): An object containing the queue errors
            are logged to.
    """

    # Get error message based on error type
    # TODO: Use task name to modify error messages
    match e:
        case ClientConnectorError():
            short_description = "Couldn't connect to server"
            full_description = """
Could not connect to the simulation server. Please make sure you are connected
to the same network as the server, then try again.
            """
            error_icon = "link_off"
        case ClientResponseError():
            match e.status:
                # TODO: Make sure these errors only show up in the described cases
                # (or have even finer-grain distinguishing between them)
                case 404:
                    short_description = "Simulation ID not found"
                    full_description = """
The dashboard attempted to access a simulation using the wrong ID. Please
refresh the page or clear your browser cache and try again.
                    """
                case 500:
                    short_description = "Internal server error"
                    full_description = """
The simulation server had an internal error. Please try again later.
                    """
                case 503:
                    short_description = "Results not ready"
                    full_description = """
The dashboard attempted to obtain the results of the simulation before the
simulation was complete. Please try again later.
                    """
                case _:
                    short_description = f"Server returned status {e.status}"
                    full_description = """
An error occurred when attempting to contact the simulation server. Please
try again later.
                    """
            error_icon = "http"
        case AssertionError():
            short_description = "Server failed to validate parameters"
            full_description = """
The server encountered an error when attempting to validate the simulation
parameters. Please make sure that all parameters are set to the right values
before trying again.
            """
            error_icon = "schema"
        case WSMessageTypeError():
            short_description = "Websocket encountered an error"
            full_description = """
The websocket used to monitor the simulation server had an internal error.
Please check your network connection and try again.
            """
            error_icon = "plug_connect"
        # TODO: Account for other ValueErrors (e.g. bad result_type)
        case ValueError():
            short_description = "Error unzipping analysis files"
            full_description = """
The results generated by the server could not be extracted properly. Please
make sure your parameters do not possess any errors and try again.
            """
            error_icon = "folder_zip"
        case FileNotFoundError():
            short_description = "Server returned no readable files"
            full_description = """
The simulation server did not return any readable files. Ensure your
parameters do not result in a simulation where nobody is infected and try
again.
            """
            error_icon = "unknown_document"
        # TODO: Catch JSONDecodeError
        case PythonFinalizationError():
            short_description = "Server shut down while running simulation"
            full_description = """
The simulation server shut down while the simulation experiment was
running. Please try again later once the simulation server is restarted.
            """
            error_icon = "power_off"
        case _:
            short_description = "Error occurred when running simulation"
            full_description = """
An error occurred when attempting to run the simulation experiment. Please
try again later.
            """
            error_icon = "error"

    # Add to the queue
    server_log.error(f"[task_wrapper] {short_description}: {e}")
    request_queue.errors.put((short_description, full_description, error_icon, e))
