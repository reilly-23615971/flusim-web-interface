# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
import json
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

from ClientResources.DownloadFunctions import createConfig, uploadDownloadBar
from ClientResources.InterfaceFunctions import (
    errorChecker,
    healthOutcomeStore,
    timeString,
)
from ClientResources.ParameterFunctions import (
    idGet,
    loadKey,
    saveKey,
    timeScaleChange,
)
from ClientResources.ServerFunctions import taskWrapper
from ClientResources.SharedResources import (
    AnalysisFile,
    communityPopulation,
    presetJSONPath,
    saveJSON,
    simCurrentProgress,
    simErrorQueue,
    simResultQueue,
    simStatusQueue,
    splitPoint,
    usePresetParams,
)

# Logging
runSimLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
simulationInProgress = session.simulationInProgress
simCancelFlag = Event()


def simRuntimeEstimate(days: int, runs: int, scenarios: int) -> int:
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
        estimatedTime = simRuntimeEstimate(cycleCount, runCount, scenarioCount)
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
            simCancelFlag.clear()

            # Create the final model JSON
            # Load debug parameters from file
            if usePresetParams:
                with open(presetJSONPath, "r") as f:
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
            session.simulationInProgress = True
            taskWrapper(
                "Simulation Experiment",
                "runModel",
                parameterJSON,
                simCancelFlag,
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
        simCancelFlag.set()
        session.simulationInProgress = False
        session.showSimProgress = True

        # Generate popup to let the user know it's cancelled
        stn.toast(
            "The simulation has been cancelled.",
            icon=":material/stop_circle:",
        )
        st.rerun()


# Page Content

st.title("Run Simulations")

st.markdown("""
    This page lets you configure the simulation engine's settings and
    run the simulation experiment itself.
""")

# Global Engine Parameters
st.header("Simulation Engine Settings")

st.markdown("""
    These parameters control various universal elements of the simulation engine.
""")

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
Toggle whether to display parameters that control more fine-grain aspects
of the simulation environment, such as scaling population.
    """,
)

# Community Selection
st.markdown("""
    - The community selection determines the population, demographic distribution
    and other elements of the community that is simulated in the experiment, chosen
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
simulation. Note that the data used for these communities comes
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

st.markdown("""
    - The length of the simulation indicates how many days that each simulation
    run should last for. Note that individual simulation runs may end earlier if
    no infections occur in a given cycle.
""")
loadKey("cycleCount", default=360)
st.slider(
    "Length of Simulation (Days)",
    30,
    720,
    360,
    format="%f Day(s)",
    key="_cycleCount",
    on_change=timeScaleChange,
    help="""
The length of the time period that will be simulated, measured in days.

Note that if you lower this value, other time-based parameters
may have their values altered. For instance, if you go from 360
days to 120, a NPI set to end on Day 180 will be changed to end
on Day 120 instead.
    """,
)

st.markdown("""
    - The number of simulation runs decides how many times each scenario will be
    simulated. The results displayed on this dashboard are the median of the results
    obtained in each simulation run. Running each scenario multiple times utilises
    the model's stochasticity to generate reliable average values and reduce the
    likelihood of outliers.
""")
loadKey("runCount", default=24)
st.slider(
    "Number of Simulation Runs",
    min_value=16,
    max_value=64,
    value=24,
    key="_runCount",
    on_change=saveKey,
    args=["runCount"],
    help="""
How many times each scenario will be simulated. The results
of each individual simulation will be averaged together to
get the final results; higher values lead to longer
simulations but more accurate results.
    """,
)

if showAdvanced:
    st.markdown("""
        - The starting day of the week determines what day of the week it is on the
        first day of the experiment. Individuals in the simulation visit different
        locations on weekends, so this may affect the initial spread of the disease.
    """)
    loadKey("startDay", default="Random")
    st.radio(
        "Starting Day of the Week",
        (
            "Random",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ),
        index=0,
        horizontal=True,
        key="_startDay",
        on_change=saveKey,
        args=["startDay"],
        help="""
    The day of the week that the first day of the simulation will be. If this is "Random", the starting day will be chosen randomly for each simulation.
        """,
    )

    st.markdown("""
        - The scaling population will be used to adjust simulation results for populations larger than the simulated population. For instance, if you simulate Newcastle (whose population is 272,407) and set the scaling population to 544,814, all health burdens will be doubled to make them proportional to the new value.
    """)
    # TODO: Can this (and other big number inputs) use commas?
    loadKey("scalingPopulation", default=communityPopulation[community])
    st.number_input(
        "Scaling Population",
        min_value=1,
        value=communityPopulation[community],
        key=f"_scalingPopulation",
        on_change=saveKey,
        args=["scalingPopulation"],
        placeholder="Enter the size of the desired population",
        help="""
    The size of the population that all simulation results will be scaled to. The
    proportions of the data will not change, but all health burdens will be multiplied
    such that they reflect the values that would be obtained in a simulation whose
    population matches the scaling population.
            """,
    )

# Buttons to upload simulation parameters
# TODO: Move download popover so it doesn't interfere with the run sim dialog
uploadDownloadBar()

# Button to run the simulation
# TODO: Check if server is available and grey out button if not
st.button(
    label=(
        "Running simulations..."
        if simulationInProgress
        else "Run Simulation Experiment"
    ),
    on_click=runSimulationButton,
    key="_runSim",
    disabled=simulationInProgress,
    type="primary",
    icon="spinner" if simulationInProgress else ":material/motion_play:",
    help=(
        """
Send a request to the *Flusim* model server to run the model
with the specified parameters.
        """
        if not simulationInProgress
        else """
A simulation is already running; please wait for it to conclude
before running another one.
        """
    ),
)


@st.fragment(run_every=1)
def simulationProgressBar():
    """
    Fragment to generate a progress bar showing how far along the simulation is
    """
    # TODO: Display how long each step took
    try:
        progress = simCurrentProgress[0]
    except IndexError:
        progress = 0.0
    if progress < 0.0:
        # Display errors that have occurred alongside progress
        errorTitle, errorBody, errorIcon, errorObject = session.get(
            "simulationError",
            (
                "Error occurred when running simulation",
                "An unspecified error has occurred while running the simulation.",
                "error",
                None,
            ),
        )
        st.progress(1.0, f":red[:material/error:] {errorTitle}")
        simStatus = st.status(
            label="Experiment stopped due to error (click for more info)", state="error"
        )
        for newStatus in simStatusQueue:
            simStatus.write(newStatus)
        simStatus.error(f"Error: {errorBody}", icon=f":material/{errorIcon}:")
        if errorObject is not None:
            simStatus.exception(errorObject)
    else:
        st.progress(
            progress,
            simStatusQueue[-1] if simStatusQueue else "Initialising parameters...",
        )
        simStatus = st.status(
            "Experiment in progress..." if progress < 1.0 else "Experiment complete!",
            state="running" if progress < 1.0 else "complete",
        )
        for newStatus in simStatusQueue:
            simStatus.write(newStatus)


if simulationInProgress or session.showSimProgress:
    simulationProgressBar()

# Stop Simulation Button
if simulationInProgress:
    st.button(
        label="Cancel Simulation",
        on_click=stopSimulationButton,
        key="_stopSim",
        type="primary",
        icon=":material/stop_circle:",
        help="""
Cancel the currently running simulation, allowing you to immediately run a new
simulation with different parameters.
        """,
    )


# TODO: Debug
# st.header("DEBUG ZONE", anchor="test")
# st.write(session)
