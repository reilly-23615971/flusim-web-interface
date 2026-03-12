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

from ClientResources.InterfaceFunctions import errorChecker, idGet
from ClientResources.ModelSchema import (
    Parameters,
    commandArgument,
    communityOverride,
    modelGuideFile,
    overrideParams,
    scenarioParameters,
    simulation,
    simulationSet,
)
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
from ClientResources.VisualisationFunctions import formatData
from ParameterTabs.communityParams import communitySchema

# from ParameterTabs.basicParams import basicSchema
from ParameterTabs.diseaseParams import diseaseSchema
from ParameterTabs.dynamicParams import dynamicSchema
from ParameterTabs.vaccinationNPIParams import vaccineSchema

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Error class for getting full responses
class invalidSchemaError(Exception):
    def __init__(self, message, response):
        self.message = message
        self.response = response
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Full Response: {self.response})"


def createConfig(scenarioCount: int):
    """
    Function to generate a JSON config file using the selected parameters

    Parameters:
        scenarioCount (int): The number of scenarios to define in the config.
    """
    # Set up schema objects
    scenarioParams = [Parameters() for _ in range(scenarioCount)]

    # Populate parameters with session_state values
    for id, scenario in enumerate(scenarioParams):
        # basicSchema(scenario, id)
        diseaseSchema(scenario, id)
        communitySchema(scenario, id)
        vaccineSchema(scenario, id)
        dynamicSchema(scenario, id)

    # Create config object with non-scenario parameters as overrides
    return modelGuideFile(
        name="Flusim Dashboard Simulation",
        description=str(session.sessionID),
        output_folder="./results/",
        middle_joint="-usingEpidemic",
        community_used=[session.get("community", "newcastle")],
        community_overrides=[
            communityOverride(
                name=session.get("community", "newcastle"),
                parameters=Parameters(
                    Command_Argument=commandArgument(
                        n_runs=session.get("runCount", 24),
                        n_cycles=session.get("cycleCount", 360) * 2,
                    ),
                    Scenario_Parameter=scenarioParameters(
                        start_day_of_week=(
                            "Sunday",
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                        ).index(session.get("startDay", "Monday"))
                    ),
                ),
            )
        ],
        shared_overrides=overrideParams(parameters=scenarioParams[0]),
        simulation_sets=[
            simulationSet(
                name="Dashboard Simulation Set",
                version=session.sessionID,
                simulations=[simulation(name="Baseline")]
                + [
                    simulation(
                        name=session[f"scenarioName{i}"],
                        override_setting=overrideParams(parameters=scenarioParams[i]),
                    )
                    for i in range(1, scenarioCount)
                ],
            )
        ],
    )


@st.dialog("Run Simulation Experiment", width="large", icon=":material/motion_play:")
def runSimulationButton():
    """
    Callback function for the Run Simulation button
    """
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
        severeErrorsFound = severeErrorsFound or errorChecker(
            id,
            f"""Errors in {
                session[f'scenarioName{id}'] if id > 0 else 'Baseline'
            }""",
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
        # TODO: Display estimated simulation run time
        # TODO: Make warning display for the chart one too
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
        st.markdown(
            """
            Are you sure you want to begin running simulations with the
            selected parameters?
        """
        )
        if st.button("Confirm"):
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
            session.PendingDataCommunity = session.get("community", "newcastle")
            session.PendingDataScenarioNames = scenarioNames
            session.PendingDataScenarioCount = scenarioCount
            session.PendingDataAsymptomatic = [
                [
                    1 - idGet("asymptomaticChild", scenarioID, 0.35),
                    1 - idGet("asymptomaticAdult", scenarioID, 0.35),
                ]
                for scenarioID in range(scenarioCount + 1)
            ]
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
                scenarioID: idGet("deathRatio", scenarioID, 0.00050034)
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
                    .replace({"Age Group": ageTimeDict})
                    .set_index("Age Group")["Mortality Rate"]
                    .to_dict()
                )
                for scenarioID in range(scenarioCount + 1)
            }

            # Make the model call
            runModelWrapper(scenarioNames, parameterJSON)

            # Generate popup to let the user know it's pending
            toast(
                "Sending a request to run the simulation. Please wait...",
                icon=":material/experiment:",
            )
            st.rerun()


# TODO: Clean up this function so that errors are more easily read
# and the returned types don't need as much checking
async def runModel(scenarioNames: list[str], parameterJSON: str):
    """
    Asynchronous function to send JSON model parameters to the server, awaiting a
    response containing the results of the simulation

    Parameters:
        scenarioNames (list of str): A list of names to assign to each scenario.

        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.

    Returns:
        list: A list containing tuples for each analysis performed on the
            data. Each tuple contains the byte data of the analysed CSV
            results alongside a string to identify the type
            of analysis it represents.

        tuple: A string identifying what kind of error
            was encountered when running the model, alongside the error itself
            as an Exception subclass.
    """
    try:
        dataForms = [
            AnalysisFile(tool="epidemic", names=scenarioNames, useCumulative=True),
            AnalysisFile(tool="epidemic", names=scenarioNames, useCumulative=False),
            AnalysisFile(tool="asir", names=scenarioNames),
        ]

        # Send POST request to server with parameters
        functionLog.info(
            f"[runModel] Initialising session with base url {serverUrl}..."
        )
        async with ClientSession(
            raise_for_status=False,
            base_url=serverUrl,
            timeout=ClientTimeout(total=1800),
        ) as session:
            functionLog.info("[runModel] Sending post request...")
            async with session.post(
                "runModel", json=json.loads(parameterJSON)
            ) as response:
                responseData = await response.read()
                if response.status == 422:
                    responseText = await response.text()
                    raise invalidSchemaError(
                        "The parameter schema did not comply with the Pydantic model",
                        responseText,
                    )
                response.raise_for_status()
            functionLog.info("[runModel] Response received! Returning data...")

        # Convert CSV statistics into DataFrame(s)
        functionLog.info(
            f"[runModel] Preparing to process {len(dataForms)} analyses..."
        )
        # Process without unzipping if there's only one analysis
        if len(dataForms) == 1:
            return [formatData(responseData, dataForms[0])]
        # Unzip data and format each analysis file
        with ZipFile(BytesIO(responseData)) as analyses:
            fileNames = analyses.namelist()
            for file in fileNames:
                functionLog.info(f"File Data: {analyses.read(file).decode()}")
            if len(fileNames) == 0:
                functionLog.error("[runModel] Server returned no readable files")
                return "EmptyZipFile"

            try:
                processedData = [
                    formatData(analyses.read(file), dataForms[index])
                    for index, file in enumerate(fileNames)
                ]
            except ValueError as e:
                functionLog.error(f"[runModel] Server returned malformed files: {e}")
                return ("ValueError", e)
            except Exception as e:
                functionLog.error(
                    "[runModel] Server returned " f"unspecified malformed files: {e}"
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


def runModelWrapper(scenarioNames, parameterJSON):
    """
    Async wrapper function for runModel, allowing HTTP requests to be made
    asynchronously without blocking Streamlit operations

    Parameters:
        scenarioNames (list of str): A list of names to assign to each scenario.

        parameterJSON (str): A string containing the JSON representation of
            the simulation experiment to run.
    """

    # Inner function to asynchronously call the server and await results
    # Needed to avoid interrupting Streamlit UI functionality
    def threadRunner():
        """
        Inner function to asynchronously call the server and await results,
        needed to avoid interrupting Streamlit UI functionality
        """
        try:
            # time.sleep(5)  # Debug for testing dashboard while running
            formattedData = asyncio.run(runModel(scenarioNames, parameterJSON))
            if formattedData:
                resultQueue.put(formattedData)  # type: ignore
        except Exception as e:
            functionLog.info(f"[runner] Encountered {type(e).__name__}: {e}")
            functionLog.error(f"[runner] Encountered {type(e).__name__}: {e}")
            raise e

    session.simulationInProgress = True
    runModelThread = threading.Thread(target=threadRunner)
    runModelThread.start()
