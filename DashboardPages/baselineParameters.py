# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging

import streamlit as st

from ClientResources.InterfaceFunctions import errorChecker
from ParameterTabs.communityParams import buildCommunityTab

# from streamlit_push_notifications import send_push, send_alert
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.dynamicParams import buildDynamicTab
from ParameterTabs.vaccinationNPIParams import buildVaccinationNPITab

# Logging
baselineLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Page Content

st.title("Baseline Parameters")

st.markdown(
    """
    This page allows for configuring the parameters that will be used
    as a baseline for the simulation.

    Select a tab to view or modify the parameters under that category.
    Hover your mouse over the :material/help: help icon next to a
    parameter's input field to show an explanation of what that
    parameter represents. Hover your mouse over any buttons to show an
    explanation of what that button does. After moving a slider, use
    the left and right arrow keys to fine-tune the parameter's value.

    All scenarios in the simulation will use the parameters on this
    page as a baseline; however, individual scenarios can have
    different values defined at the
    :grey-badge[:material/variable_add: Scenario Parameters]
    page, overwriting these base values.
"""
)

# Fragments to display errors and rerun on sim length change
errorChecker(0)


# TODO: Consider having a tab for templates that load parameters for
# specific stuff (e.g. influenza, NPI presets)
# TODO: Check studies for better parameter defaults/ranges
# TODO: Check parameters where slider is bad for selecting and either
# change scale or switch to number input

# Create tabs for each category of parameters
(diseaseTab, communityTab, interventionTab, dynamicTab) = st.tabs(
    [
        ":material/coronavirus: Disease",
        ":material/groups: Community",
        ":material/vaccines: Vaccination and NPIs",
        ":material/manage_history: Dynamic",
    ],
    on_change="rerun",
    key="paramTabs0",
)
# TODO: :material/pattern: for the template tab

if diseaseTab.open:
    with diseaseTab:
        buildDiseaseTab(0)
if communityTab.open:
    with communityTab:
        buildCommunityTab(0)
if interventionTab.open:
    with interventionTab:
        buildVaccinationNPITab(0)
if dynamicTab.open:
    with dynamicTab:
        buildDynamicTab(0)
