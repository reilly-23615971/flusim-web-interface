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
r0Log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
simulationInProgress = session.simulationInProgress


# Page Content

st.title("$R_0$ Configuration")

st.markdown("""
    This page is used to configure the experiment's parameters to match a desired
    basic reproduction number ($R_0$).
""")

st.header("TODO")
