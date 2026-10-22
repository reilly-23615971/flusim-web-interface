# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where baseline parameter values can be set

# Imports
from typing import Optional

import streamlit as st
from streamlit.elements.lib.mutable_tab_container import TabContainer

from resources.download import upload_download_bar
from resources.interface import error_checker
from resources.parameter import container_save, load_key
from tabs.community import build_community_tab
from tabs.disease import build_disease_tab
from tabs.dynamic import build_dynamic_tab
from tabs.npi import build_npi_tab
from tabs.template import build_template_tab
from tabs.vaccination import build_vaccination_tab

# Store st.session_state as variable for efficiency
session = st.session_state


# Page Content

st.title("Baseline Parameters")

st.markdown("""
This page allows for configuring the parameters that will be used as a baseline
for the simulation.

Select a tab to view or modify the parameters under that category. Hover your
mouse over the :material/help: help icon next to a parameter's input field to
show an explanation of what that parameter represents. Hover your mouse over
any buttons to show an explanation of what that button does. After moving a
slider, use the left and right arrow keys to fine-tune the parameter's value.

All scenarios in the simulation will use the parameters on this page as a
baseline; however, individual scenarios can have different values defined at
the :grey-badge[:material/variable_add: Scenario Parameters] page, overwriting
these base values.
""")

# Buttons to upload simulation parameters
upload_download_bar()

# Fragment to display errors
# TODO: Errors aren't removed from here when fixed until page rerun
error_checker(0, "Errors in Baseline Scenario")

# Advanced parameters toggle
load_key("show_advanced", default=False, no_zero_default=True)
containers_to_open: set[str] = {"param_tabs0"}
show_advanced = st.toggle(
    "Show Advanced Parameters",
    False,
    key="_show_advanced",
    on_change=container_save,
    args=["show_advanced"],
    kwargs={"containers": containers_to_open},
    help="""
Toggle whether to display parameters that control more fine-grain aspects of
the simulation environment, such as age-specific NPI compliance or dynamic
parameter updates.
    """,
)

# Create tabs for each category of parameters
dynamic_tab: Optional[TabContainer] = None
if show_advanced:
    disease_tab, community_tab, vaccine_tab, npi_tab, dynamic_tab, template_tab = (
        st.tabs(
            [
                ":material/coronavirus: Pathogen",
                ":material/groups: Community",
                ":material/vaccines: Vaccination",
                ":material/medical_mask: NPIs",
                ":material/manage_history: Dynamic",
                ":material/list_alt: Templates",
            ],
            on_change="rerun",
            key="param_tabs0",
        )
    )
else:
    disease_tab, community_tab, vaccine_tab, npi_tab, template_tab = st.tabs(
        [
            ":material/coronavirus: Pathogen",
            ":material/groups: Community",
            ":material/vaccines: Vaccination",
            ":material/medical_mask: NPIs",
            ":material/list_alt: Templates",
        ],
        on_change="rerun",
        key="param_tabs0",
    )
if disease_tab.open:
    with disease_tab:
        build_disease_tab(0, show_advanced)
if community_tab.open:
    with community_tab:
        build_community_tab(0, show_advanced)
if vaccine_tab.open:
    with vaccine_tab:
        build_vaccination_tab(0, show_advanced)
if npi_tab.open:
    containers_to_open |= {
        "npi_container0",
        "school_closure_container0",
        "withdrawal_increase_container0",
        "reduced_workgroup_container0",
        "bcc_reduction_container0",
    }
    with npi_tab:
        build_npi_tab(0, show_advanced)
if dynamic_tab is not None and dynamic_tab.open:
    with dynamic_tab:
        build_dynamic_tab(0)
if template_tab.open:
    with template_tab:
        build_template_tab(0)
