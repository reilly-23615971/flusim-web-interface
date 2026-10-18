# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where baseline parameter values can be set

# Imports
import logging
from typing import Optional

import streamlit as st
from streamlit.elements.lib.mutable_tab_container import TabContainer

from ClientResources.DownloadFunctions import upload_download_bar
from ClientResources.InterfaceFunctions import error_checker
from ClientResources.ParameterFunctions import container_save, load_key
from ParameterTabs.communityParams import build_community_tab
from ParameterTabs.diseaseParams import build_disease_tab
from ParameterTabs.dynamicParams import build_dynamic_tab
from ParameterTabs.npiParams import build_npi_tab
from ParameterTabs.templateParams import build_template_tab
from ParameterTabs.vaccinationParams import build_vaccination_tab

# from streamlit_push_notifications import send_push, send_alert


# Logging
baselineLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Page Content

st.title("Baseline Parameters")

st.markdown("""
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
""")

# Buttons to upload simulation parameters
upload_download_bar()

# Fragment to display errors
# TODO: Errors aren't removed from here when fixed until page rerun
error_checker(0, "Errors in Baseline Scenario")

# Advanced parameters toggle
load_key("show_advanced", default=False, no_zero_default=True)
containersToOpen: set[str] = {"paramTabs0"}
show_advanced = st.toggle(
    "Show Advanced Parameters",
    False,
    key="_show_advanced",
    on_change=container_save,
    args=["show_advanced"],
    kwargs={"containers": containersToOpen},
    help="""
Toggle whether to display parameters that control more fine-grain aspects
of the simulation environment, such as age-specific NPI compliance or
dynamic parameter updates.
    """,
)

# Create tabs for each category of parameters
dynamicTab: Optional[TabContainer] = None
if show_advanced:
    diseaseTab, communityTab, vaccineTab, npiTab, dynamicTab, templateTab = st.tabs(
        [
            ":material/coronavirus: Pathogen",
            ":material/groups: Community",
            ":material/vaccines: Vaccination",
            ":material/medical_mask: NPIs",
            ":material/manage_history: Dynamic",
            ":material/list_alt: Templates",
        ],
        on_change="rerun",
        key="paramTabs0",
    )
else:
    diseaseTab, communityTab, vaccineTab, npiTab, templateTab = st.tabs(
        [
            ":material/coronavirus: Pathogen",
            ":material/groups: Community",
            ":material/vaccines: Vaccination",
            ":material/medical_mask: NPIs",
            ":material/list_alt: Templates",
        ],
        on_change="rerun",
        key="paramTabs0",
    )
if diseaseTab.open:
    with diseaseTab:
        build_disease_tab(0, show_advanced)
if communityTab.open:
    with communityTab:
        build_community_tab(0, show_advanced)
if vaccineTab.open:
    with vaccineTab:
        build_vaccination_tab(0, show_advanced)
if npiTab.open:
    containersToOpen |= {
        "npi_container0",
        "school_closure_container0",
        "withdrawal_increase_container0",
        "reduced_workgroup_container0",
        "bcc_reduction_container0",
    }
    with npiTab:
        build_npi_tab(0, show_advanced)
if dynamicTab is not None and dynamicTab.open:
    with dynamicTab:
        build_dynamic_tab(0)
if templateTab.open:
    with templateTab:
        build_template_tab(0)
