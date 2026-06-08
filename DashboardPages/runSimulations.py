# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
import logging

import streamlit as st

# from streamlit_push_notifications import send_push, send_alert
from ClientResources.DownloadFunctions import uploadDownloadBar
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
runSimLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
simulationInProgress = session.simulationInProgress


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
containersToOpen: set[str] = {"paramTabs0"}
showAdvanced = st.toggle(
    "Show Advanced Parameters",
    False,
    key="_showAdvanced",
    on_change=containerSave,
    args=["showAdvanced"],
    kwargs={"containers": containersToOpen},
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
with the specified parameters. Once the request has been made,
you will be unable to run the model again until it completes,
so make sure you have configured your parameters to appropriate
values before clicking.
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
        progress = currentProgress[0]
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
        for newStatus in statusQueue:
            simStatus.write(newStatus)
        simStatus.error(f"Error: {errorBody}", icon=f":material/{errorIcon}:")
        if errorObject is not None:
            simStatus.exception(errorObject)
    else:
        st.progress(
            progress,
            statusQueue[-1] if statusQueue else "Initialising parameters...",
        )
        simStatus = st.status(
            "Experiment in progress..." if progress < 1.0 else "Experiment complete!",
            state="running" if progress < 1.0 else "complete",
        )
        for newStatus in statusQueue:
            simStatus.write(newStatus)


if simulationInProgress or session.keepProgressBar:
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
