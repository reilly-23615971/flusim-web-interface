# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
import json
import logging
from datetime import datetime
from threading import Event

import pandas as pd
import streamlit as st

from ClientResources.Constants import (
    LOG_PARAM_JSON,
    PRESET_JSON_PATH,
    PROGRESS_SPLIT_POINT,
    USE_PRESET_DATA,
    USE_PRESET_PARAMS,
)
from ClientResources.DownloadFunctions import (
    create_config,
    load_config,
    upload_download_bar,
)
from ClientResources.InterfaceFunctions import (
    error_checker,
    health_outcome_store,
    time_string,
)
from ClientResources.ParameterFunctions import (
    community_change,
    id_get,
    load_key,
    save_key,
    time_scale_change,
)
from ClientResources.ServerFunctions import task_wrapper
from ClientResources.Types import (
    COMMUNITIES,
    COMMUNITY_NAMES,
    SIM_STATUS,
    AnalysisFile,
    SimParams,
)

# Logging
runSimLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
simulation_in_progress = session.simulation_in_progress
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
    # TODO: The commented-out equation overestimates due to using
    # constant waning and no vaccination
    # return round((0.0948297101449275 * days - 2.977807971014478) * runs * scenarios)
    return round((0.02698311 * days - 2.977807971014478) * runs * scenarios)


def runModelProgress(
    scenario_names: list[str], use_vaccines: bool = False
) -> dict[str, tuple[float, str]]:
    """
    Function to generate the status dictionary used for the simulation progress bar.

    Parameters:
        scenario_names (list of str): The names of the scenarios in the simulation.

        use_vaccines (bool): Set to `True` to add an extra status point for
            vaccine-based infections.

    Returns:
        dict: A dictionary matching short status strings to tuples containing
            a float (the percentage of the progress bar to fill) and a string
            (the description of the step represented by this status)
    """
    # TODO: Include client side processing like format_asir in this progress
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
    scenarioSegments = (PROGRESS_SPLIT_POINT - 0.02) / len(scenario_names)
    progressDict |= {
        f"runningSim{i}": (
            scenarioSegments * i + 0.02,
            f'Running scenario "{name}"...',
        )
        for i, name in enumerate(scenario_names)
    }
    # Analysis status
    # Note that ASIR gets twice the progress length as epidemic
    if use_vaccines:
        analysisSegments = (1 - PROGRESS_SPLIT_POINT - 0.02) / 6
        progressDict |= {
            "toolboxAnalysis0": (
                PROGRESS_SPLIT_POINT,
                "Extracting cumulative infections...",
            ),
            "toolboxAnalysis1": (
                analysisSegments + PROGRESS_SPLIT_POINT,
                "Extracting daily infections...",
            ),
            "toolboxAnalysis2": (
                3 * analysisSegments + PROGRESS_SPLIT_POINT,
                "Extracting age-based infections...",
            ),
            "toolboxAnalysis3": (
                5 * analysisSegments + PROGRESS_SPLIT_POINT,
                "Extracting vaccine-based infections...",
            ),
        }
    else:
        analysisSegments = (1 - PROGRESS_SPLIT_POINT - 0.02) / 4
        progressDict |= {
            "toolboxAnalysis0": (
                PROGRESS_SPLIT_POINT,
                "Extracting cumulative infections...",
            ),
            "toolboxAnalysis1": (
                analysisSegments + PROGRESS_SPLIT_POINT,
                "Extracting daily infections...",
            ),
            "toolboxAnalysis2": (
                3 * analysisSegments + PROGRESS_SPLIT_POINT,
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
    scenario_count = session.get("scenario_count", 0) + 1
    scenario_names = session.scenario_names
    if scenario_count == 1:
        st.markdown(f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate the baseline scenario.
        """)
    else:
        st.markdown(f"""
With the current parameters, this modelling experiment will use the
"{session.get('community', 'newcastle').capitalize()}"
community data to simulate each of the following {scenario_count} scenarios:
        """)
        with st.container() if scenario_count < 11 else st.expander("Scenario Names"):
            st.markdown("\n".join(f"- {name}" for name in scenario_names))
    # Display any errors
    # TODO: Hide scenario errors that are copies of baseline errors
    severe_errors_found = False
    for scenario_id in range(scenario_count):
        severe_errors_found = (
            error_checker(scenario_id, f"Errors in {scenario_names[scenario_id]}")
            or severe_errors_found
        )
    if severe_errors_found:
        st.error(
            """
                The simulation cannot be ran due to the errors displayed above.
                Please correct these errors before running the simulation.
            """,
            icon=":material/error:",
        )
    else:
        if USE_PRESET_DATA:
            st.error(
                """
The debug settings of the dashboard are set such that visualisations use
preset data instead of server outputs. You will not be able to use the data
of any simulations you run unless this setting is disabled.
                """,
                icon=":material/bug_report:",
            )
        if USE_PRESET_PARAMS:
            st.warning(
                """
The debug settings of the dashboard are set such that simulations use
preset parameters instead of those set on the dashboard. Simulations
you run will not match the settings defined on the
:primary-badge[:material/variable_insert: Baseline Parameters] and
:primary-badge[:material/variable_add: Scenario Parameters] pages.
                """,
                icon=":material/bug_report:",
            )
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
        cycle_count = session.get("cycle_count", 360)
        run_count = session.get("run_count", 24)
        estimatedTime = simRuntimeEstimate(cycle_count, run_count, scenario_count)
        st.metric(
            f"Estimated Time to Run Simulation Experiment",
            value=time_string(estimatedTime),
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
        st.button(
            "Confirm",
            key="confirmRunButton",
            icon="spinner" if runPending else None,
            disabled=runPending,
        )

        if runPending:
            # Set params indicating model is simulating
            session.simulation_in_progress = True
            session.simulationStartTime = datetime.now()
            simCancelFlag.clear()

            # Create the final model JSON
            # Load debug parameters from file
            if USE_PRESET_PARAMS:
                with open(PRESET_JSON_PATH, "r") as f:
                    parameter_json = f.read()
                if load_config(parameter_json, loud=False):
                    return
                scenario_count = session.get("scenario_count", 0) + 1

            # Create JSON for selected parameters
            else:
                parameter_json = create_config(
                    scenario_count, include_dashboard=False
                ).model_dump_json(indent=4, exclude_unset=True)
                if LOG_PARAM_JSON:
                    with open("./savedJSON.json", "w") as file:
                        file.write(parameter_json)

            # Save current parameter values that'll be used for
            # visualisation when the user has potentially changed them
            scenario_names = session.scenario_names.copy()
            community = session.get("community", "newcastle")
            population = COMMUNITIES[community].population
            schema = json.loads(parameter_json)
            use_advanced = session.get("show_advanced", False)
            use_vaccines = "+vaccine" in schema.get("middle_joint")
            if use_vaccines:
                analysisFormats = [
                    AnalysisFile(
                        tool="epidemic", names=scenario_names, use_cumulative=True
                    ),
                    AnalysisFile(
                        tool="epidemic", names=scenario_names, use_cumulative=False
                    ),
                    AnalysisFile(tool="asir", names=scenario_names),
                    AnalysisFile(tool="asir", names=scenario_names, vaccinated=True),
                ]
            else:
                analysisFormats = [
                    AnalysisFile(
                        tool="epidemic", names=scenario_names, use_cumulative=True
                    ),
                    AnalysisFile(
                        tool="epidemic", names=scenario_names, use_cumulative=False
                    ),
                    AnalysisFile(tool="asir", names=scenario_names),
                ]

            scaling_factor = session.get("scaling_population", population) / population
            asymptomaticRates = (
                [
                    [
                        1 - id_get("asymptomatic_child", scenario_id, 0.35),
                        1 - id_get("asymptomatic_adult", scenario_id, 0.35),
                    ]
                    for scenario_id in range(scenario_count)
                ]
                if use_advanced
                else [
                    [1 - id_get("asymptomatic_adult", scenario_id, 0.35)] * 2
                    for scenario_id in range(scenario_count)
                ]
            )
            basicRates, age_rates = health_outcome_store(
                scenario_names,
                use_ages=use_advanced,
            )
            useWaning = use_advanced and any(
                id_get("naturalWaningToggle", scenario_id, False)
                or (
                    id_get("vaccineToggle", scenario_id, False)
                    and (
                        id_get("vaccineWaningToggle", scenario_id, False)
                        or id_get("boosterToggle", scenario_id, False)
                    )
                )
                for scenario_id in range(scenario_count)
            )

            session.pending_sim_params = SimParams(
                scenario_names=scenario_names,
                analysis_formats=analysisFormats,
                symptomatic_rates=asymptomaticRates,
                health_outcome_rates=basicRates,
                age_health_outcome_rates=age_rates,
                community=community,
                scaling_factor=scaling_factor,
                waning=useWaning,
            )

            # Prepare model call parameters
            status_params = {
                "result_type": "zip",
                "status_decoder": runModelProgress(scenario_names, use_vaccines),
                "request_queue": SIM_STATUS,
            }

            # Clear the status queue
            SIM_STATUS.progress.append(0.0)
            SIM_STATUS.tasks.clear()
            SIM_STATUS.tasks.append("Connecting to server...")
            session["simulationError"] = None

            # Make the model call
            session.simulation_in_progress = True
            task_wrapper(
                "Simulation Experiment",
                "runModel",
                parameter_json,
                simCancelFlag,
                status_params,
            )

            # TODO: Remember streamlit_push_notifications

            # Generate popup to let the user know it's pending
            st.toast(
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
    st.button(
        "Confirm",
        key="confirmCancelButton",
        icon="spinner" if cancelPending else None,
        disabled=cancelPending,
    )

    if cancelPending:
        # Exit immediately if there's nothing to stop
        if not session.simulation_in_progress:
            st.toast(
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
        SIM_STATUS.progress.append(-1.0)

        # Stop the runModel thread
        simCancelFlag.set()
        session.simulation_in_progress = False
        session.showSimProgress = True

        # Generate popup to let the user know it's cancelled
        st.toast(
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

# Buttons to upload simulation parameters
upload_download_bar()

# Advanced parameters toggle
# TODO: Move advanced parameters to either the sidebar or a separate settings page
load_key("show_advanced", default=False, no_zero_default=True)
show_advanced = st.toggle(
    "Show Advanced Parameters",
    False,
    key="_showAdvanced",
    on_change=save_key,
    args=["show_advanced"],
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
load_key("community", default="newcastle")
community = st.selectbox(
    "Simulated Community",
    COMMUNITY_NAMES,
    key="_community",
    format_func=lambda x: x.capitalize(),
    on_change=community_change,
    help="""
The Australian city whose community data will be used as the
basis for the population and demographic distribution in the
simulation. Note that the data used for these communities comes
from 2011.

### Options:
- Newcastle: A metropolitan area in New South Wales, Australia.
It has a population of 272,407 (as of 2011 when this data was
collected) and has a demographic distribution that more closely matches
that of Australia as a whole compared to the other communities.
- Cairns: A major city in Queensland, Australia. It has a population of
140,402 and has a higher Indigenous population compared to the other
communities.
- Albany: A major city in Western Australia. It has a population of
55,109 and has a higher proportion of older adults and seniors compared
to the other communities.
    """,
)

# Warn if patch parameters are set
scenario_count = session.get("scenario_count", 0) + 1
scenarios_with_patches = []
for i in range(scenario_count):
    current_patches = session.get(
        f"seeding_patch_form{i}", pd.DataFrame(columns=["Location"])
    )
    if current_patches["Location"].notna().any():
        scenarios_with_patches.append(session.scenario_names[i])
if show_advanced and scenarios_with_patches:
    reset_scenario_list = ", ".join(scenarios_with_patches)
    st.warning(
        f"""
        Warning: Location-specific seeding weights defined in some scenarios
        ({reset_scenario_list}) rely on locations that only exist in the
        currently selected community. Changing this community will reset the
        location-specific seeding weights for these scenarios.
        """,
        icon=":material/wrong_location:",
    )

st.markdown("""
    - The length of the simulation indicates how many days that each simulation
    run should last for. Note that individual simulation runs may end earlier if
    no infections occur in a given cycle.
""")
load_key("cycle_count", default=360)
st.slider(
    "Length of Simulation (Days)",
    30,
    720,
    360,
    format="%f Day(s)",
    key="_cycle_count",
    on_change=time_scale_change,
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
load_key("run_count", default=24)
st.slider(
    "Number of Simulation Runs",
    min_value=1,
    max_value=64,
    value=24,
    key="_runCount",
    on_change=save_key,
    args=["run_count"],
    help="""
How many times each scenario will be simulated. The results
of each individual simulation will be averaged together to
get the final results; higher values lead to longer
simulations but more accurate results.
    """,
)

if show_advanced:
    st.markdown("""
        - The starting day of the week determines what day of the week it is on the
        first day of the experiment. Individuals in the simulation visit different
        locations on weekends, so this may affect the initial spread of the disease.
    """)
    load_key("start_day", default="Random")
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
        on_change=save_key,
        args=["start_day"],
        help="""
    The day of the week that the first day of the simulation will be. If this is "Random", the starting day will be chosen randomly for each simulation.
        """,
    )

    st.markdown("""
        - The scaling population will be used to adjust simulation results for populations larger than the simulated population. For instance, if you simulate Newcastle (whose population is 272,407) and set the scaling population to 544,814, all health burdens will be doubled to make them proportional to the new value.
    """)
    default_population = COMMUNITIES[community if community else "newcastle"].population
    st.info(
        f"""
        The population used in the experiment for the current community
        ({community.capitalize() if community else "Newcastle"})
        is {default_population}.
        """,
        icon=":material/groups:",
    )
    load_key("scaling_population", default=default_population)
    st.number_input(
        "Scaling Population",
        min_value=1,
        value=default_population,
        key=f"_scalingPopulation",
        on_change=save_key,
        args=["scaling_population"],
        placeholder="Enter the size of the desired population",
        help="""
    The size of the population that all simulation results will be scaled to. The
    proportions of the data will not change, but all health burdens will be multiplied
    such that they reflect the values that would be obtained in a simulation whose
    population matches the scaling population.
            """,
    )

# Button to run the simulation
# TODO: Check if server is available and grey out button if not
st.button(
    label=(
        "Running simulations..."
        if simulation_in_progress
        else "Run Simulation Experiment"
    ),
    on_click=runSimulationButton,
    disabled=simulation_in_progress,
    type="primary",
    icon="spinner" if simulation_in_progress else ":material/motion_play:",
    help=(
        """
Send a request to the *Flusim* model server to run the model
with the specified parameters.
        """
        if not simulation_in_progress
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
    status_queue = SIM_STATUS.tasks
    try:
        progress = SIM_STATUS.progress[0]
    except IndexError:
        progress = 0.0
    if progress < 0.0:
        # Display errors that have occurred alongside progress
        errorTitle, errorBody, error_icon, errorObject = session.get(
            "simulationError",
            (
                "Error occurred when running simulation",
                "An unspecified error has occurred while running the simulation.",
                "error",
                None,
            ),
        )
        st.progress(1.0, f":red[:material/error:] {errorTitle}")
        # TODO: Different label for cancellation
        simStatus = st.status(
            label="Experiment stopped due to error (click for more info)", state="error"
        )
        for newStatus in status_queue:
            simStatus.write(newStatus)
        simStatus.error(f"Error: {errorBody}", icon=f":material/{error_icon}:")
        if errorObject is not None:
            simStatus.exception(errorObject)
    else:
        st.progress(
            progress,
            status_queue[-1] if status_queue else "Initialising parameters...",
        )
        simStatus = st.status(
            "Experiment in progress..." if progress < 1.0 else "Experiment complete!",
            state="running" if progress < 1.0 else "complete",
        )
        for newStatus in status_queue:
            simStatus.write(newStatus)


if simulation_in_progress or session.showSimProgress:
    simulationProgressBar()

# Stop Simulation Button
if simulation_in_progress:
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
