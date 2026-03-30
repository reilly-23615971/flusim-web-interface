# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
import logging

import streamlit as st

# from streamlit_push_notifications import send_push, send_alert
from ClientResources.InterfaceFunctions import (
    dayCount,
    loadKey,
    saveKey,
    timeScaleChange,
)
from ClientResources.SharedResources import communityPopulation
from ClientResources.SimulationRunFunctions import runSimulationButton

# Logging
runSimLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Page Content

st.title("Run Simulations")

st.markdown(
    """
    This page lets you configure the simulation engine's settings and
    run the simulation experiment itself.
"""
)

# Global Engine Parameters
st.header("Simulation Engine Settings")

# Community Selection
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

# TODO: Notify users if parameters are changed when cycle count is adjusted
loadKey("cycleCount", default=360)
st.select_slider(
    "Length of Simulation (Days)",
    range(30, 721),
    360,
    format_func=dayCount,
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

loadKey("startDay", default="Monday")
st.select_slider(
    "Starting Day of the Week",
    ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    "Monday",
    key="_startDay",
    on_change=saveKey,
    args=["startDay"],
    help="""
        The day of the week that the first day of the
        simulation will be.
    """,
)

# Button to run the simulation
# TODO: Check if server is available and grey out button if not
# TODO: consider adding progress updates to the sidebar (time remaining,
# progress bars, server availability etc.)
st.button(
    label=(
        "Running simulations..."
        if session.simulationInProgress
        else "Run Simulation Experiment"
    ),
    on_click=runSimulationButton,
    key="_runSim",
    disabled=session.simulationInProgress,
    type="primary",
    icon=("spinner" if session.simulationInProgress else ":material/motion_play:"),
    help=(
        """
        Send a request to the *Flusim* model server to run the model
        with the specified parameters. Once the request has been made,
        you will be unable to run the model again until it completes,
        so make sure you have configured your parameters to appropriate
        values before clicking.
    """
        if not session.simulationInProgress
        else """
        A simulation is already running; please wait for it to conclude
        before running another one.
    """
    ),
)

# TODO: log of previous simulations/errors


# TODO: Debug
# st.header("DEBUG ZONE")
# st.write(session)
