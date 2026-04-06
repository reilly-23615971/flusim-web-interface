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
from aiohttp import (
    ClientConnectorError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
)
from streamlit_notify import toast  # type: ignore

from ClientResources.DownloadFunctions import createConfig
from ClientResources.InterfaceFunctions import errorChecker
from ClientResources.ParameterFunctions import idGet
from ClientResources.SharedResources import (
    AnalysisFile,
    ageTimeDict,
    ageWithTime,
    outcomeRateDefaults,
    outcomeRateVariables,
    resultQueue,
    saveJSON,
    serverUrl,
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
    # TODO: Contain in dropdown if too long
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
                f"""
                    Errors in {session[f'scenarioName{id}'] if id > 0 else 'Baseline'}
                """,
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
            oldMort = """session.PendingDataMortalityRates = {
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
            # TODO: Fix null getting added here when age tables are unchanged
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

            # Make the model call
            runModelWrapper(parameterJSON)

            # Generate popup to let the user know it's pending
            toast(
                "Sending a request to run the simulation. Please wait...",
                icon=":material/experiment:",
            )
            st.rerun()


async def runModel(parameterJSON: str):
    """
    Asynchronous function to send JSON model parameters to the server, awaiting a
    response containing the results of the simulation.

    Parameters:
        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.

    Returns:
        list: A list containing the byte data of the analysed CSV results.

        tuple: A string identifying what kind of error
            was encountered when running the model, alongside the error itself
            as an Exception subclass.
    """
    # TODO: Account for direct vs. indirect protection
    # (via extra asir filtered to vaccinated only)
    # TODO: Clean up this function so that errors are more easily read
    # and the returned types don't need as much checking
    # TODO: See if st.cache_data makes a difference here
    try:
        schema = json.loads(parameterJSON)

        # Send POST request to server with parameters
        functionLog.info(
            f"[runModel] Initialising session with base url {serverUrl}..."
        )
        # TODO: Adjust timeout as necessary (2 hours isn't normal)
        async with ClientSession(
            raise_for_status=False,
            base_url=serverUrl,
            timeout=ClientTimeout(total=7200),
        ) as session:
            functionLog.info("[runModel] Sending post request to run sim...")
            async with session.post("runModel", json=schema) as response:
                responseData = await response.read()
                if response.status == 422:
                    responseText = await response.text()
                    raise invalidSchemaError(
                        "The parameter schema did not comply with the Pydantic model",
                        responseText,
                    )
                response.raise_for_status()
            functionLog.info("[runModel] Response received! Returning data...")

        # Process without unzipping if there's only one analysis (unused currently)
        # if len(dataForms) == 1:
        # return [responseData]
        # Unzip data and format each analysis file
        with ZipFile(BytesIO(responseData)) as analyses:
            fileNames = analyses.namelist()
            # for file in fileNames:
            #     functionLog.info(f"File Data: {analyses.read(file).decode()}")
            if len(fileNames) == 0:
                functionLog.error("[runModel] Server returned no readable files")
                return "EmptyZipFile"
            try:
                processedData = [analyses.read(file) for file in fileNames]
            except ValueError as e:
                functionLog.error(f"[runModel] Server returned malformed files: {e}")
                return ("ValueError", e)
            except Exception as e:
                functionLog.error(
                    f"[runModel] Server returned unspecified malformed files: {e}"
                )
                return ("UncaughtFormatError", e)
        return processedData
    # Catch errors and return specific values to indicate them
    except ClientConnectorError as e:
        functionLog.error(f"[runModel] Couldn't connect to server: {e}")
        return ("ClientConnectorError", e)
    except ClientResponseError as e:
        functionLog.error(f"[runModel] Server returned status {e.status}: {e}")
        if e.status in {500, "500"}:
            return ("ClientResponseError500", e)
        else:
            return ("ClientResponseError", e)
    except invalidSchemaError as e:
        functionLog.error(f"[runModel] Parameter schema was invalid: {e}")
        return ("InvalidSchemaError", e)
    except Exception as e:
        functionLog.error(f"[runModel] Encountered {type(e).__name__}: {e}")
        return ("UncaughtError", e)


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
            # time.sleep(5)  # Debug for testing dashboard while running
            formattedData = asyncio.run(runModel(parameterJSON))
            if formattedData:
                resultQueue.put(formattedData)  # type: ignore
        except Exception as e:
            functionLog.info(f"[runner] Encountered {type(e).__name__}: {e}")
            functionLog.error(f"[runner] Encountered {type(e).__name__}: {e}")
            raise e

    session.simulationInProgress = True
    runModelThread = threading.Thread(target=threadRunner)
    runModelThread.start()
