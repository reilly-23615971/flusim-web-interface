# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st

# from streamlit_push_notifications import send_push, send_alert
from ParameterTabs.basicParams import buildBasicTab, rerunTime
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.communityParams import buildCommunityTab
from ParameterTabs.vaccinationNPIParams import buildVaccinationNPITab
from ParameterTabs.dynamicParams import buildDynamicTab
from ClientResources.InterfaceFunctions import saveKey, loadKey, errorChecker
from ClientResources.SharedResources import communityPopulation

# Logging
baselineLog = logging.getLogger(__name__)

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
    page, overwriting these base values. The sole exception to this
    is the Simulated Community parameter defined below, which applies
    to all scenarios and cannot be overwritten.
"""
)

# Community Selection
# TODO: Fix key errors here (axe loadKey outright?)
loadKey("community", "", "newcastle")
community = st.selectbox(
    "Simulated Community",
    communityPopulation.keys(),
    key="_community",
    format_func=lambda x: x.capitalize(),
    on_change=saveKey,
    args=["community", ""],  # type: ignore
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

# Fragments to display errors and rerun on sim length change
rerunTime()
errorChecker(0)


# TODO: Consider having a tab for templates that load parameters for
# specific stuff (e.g. influenza, NPI presets)
# TODO: Check studies for better parameter defaults/ranges
# TODO: Check parameters where slider is bad for selecting and either
# change scale or switch to number input

# Create tabs for each category of parameters
(basicTab, diseaseTab, communityTab, interventionTab, dynamicTab) = st.tabs(
    [
        ":material/start: Initialisation",
        ":material/coronavirus: Disease",
        ":material/groups: Community",
        ":material/vaccines: Vaccination and NPIs",
        ":material/manage_history: Dynamic",
    ]
)
# :material/pattern: for the template tab
# Basic parameters
with basicTab:
    buildBasicTab(0)

# Disease parameters
with diseaseTab:
    buildDiseaseTab(0)

# Environment parameters
with communityTab:
    buildCommunityTab(0)

# Vaccination and NPIs
with interventionTab:
    buildVaccinationNPITab(0)

# Dynamic parameters
with dynamicTab:
    buildDynamicTab(0)

# TODO: Debug
st.header("DEBUG ZONE")
st.write(st.session_state)
