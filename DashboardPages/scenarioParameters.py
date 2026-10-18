# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where additional parameter sets can be added

# Imports
import logging
from typing import Optional

import streamlit as st
from streamlit.elements.lib.mutable_tab_container import TabContainer

from ClientResources.Constants import MAX_SCENARIOS
from ClientResources.DownloadFunctions import (
    add_scenario,
    delete_scenario,
    upload_download_bar,
)
from ClientResources.InterfaceFunctions import error_checker, load_name, save_name
from ClientResources.ParameterFunctions import container_save, load_key
from ParameterTabs.communityParams import build_community_tab
from ParameterTabs.diseaseParams import build_disease_tab
from ParameterTabs.dynamicParams import build_dynamic_tab
from ParameterTabs.npiParams import build_npi_tab
from ParameterTabs.templateParams import buildTemplateTab
from ParameterTabs.vaccinationParams import build_vaccination_tab

# Logging
scenarioLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Load scenario count early for efficiency
scenario_count = session.get("scenario_count", 0)


@st.dialog("Remove Scenario", width="large", icon=":material/delete:")
def delete_scenarioDialog(scenario_id: int):
    """
    Dialog function that removes a scenario from the dashboard if confirmed.

    Parameters:
        scenario_id (int): The ID representing the scenario to be deleted.
    """
    # Disable button if it's taking a while to delete
    deletePending = bool(session.get("confirmDeleteButton"))
    st.markdown(f"""
        Removing the "{session.scenario_names[scenario_id]}"
        scenario will erase any unique parameter values set for it. Are
        you sure you want to remove this scenario?
    """)
    # TODO: Note that deletion doesn't affect active simulations
    st.button(
        "Confirm",
        key="confirmDeleteButton",
        icon="spinner" if deletePending else None,
        disabled=deletePending,
    )
    if deletePending:
        delete_scenario(scenario_id, "scenarioTabs")
        st.rerun()


# Hack fix: Use st.empty to alter widget order when a scenario is added
# or removed, ensuring tabs are rendered properly when the number is modified
if session.get("tab_reloader"):
    st.empty()


# Page Content
st.title("Scenario Parameters")


st.markdown(f"""
    This page allows for configuring the parameters that will be used
    in different scenarios by the simulation. To allow for direct
    comparison of different parameter sets, you may define a series of
    scenarios in which different parameter values are used. Up to
    {MAX_SCENARIOS} additional scenarios plus the baseline can be run in
    a single simulation.

    Select a tab to view or modify the parameters under that category.
    Hover your mouse over the :material/help: help icon next to a
    parameter's input field to show an explanation of what that
    parameter represents. Hover your mouse over any buttons to show an
    explanation of what that button does. After moving a slider, use
    the left and right arrow keys to fine-tune the parameter's value.
""")

# Buttons to upload simulation parameters
upload_download_bar()

# Button to add another scenario
# TODO: Allow copying an existing scenario instead of starting from the baseline
st.button(
    label="Add Scenario",
    icon=":material/add:",
    type="primary",
    on_click=add_scenario,
    args=["scenarioTabs"],
    key=f"scenarioAdd{id}",
    disabled=not scenario_count < MAX_SCENARIOS,
    help=(
        """
Add another scenario to the simulation, where you can configure
different parameter values to use instead of the baseline values.
        """
        if scenario_count < MAX_SCENARIOS
        else f"""
To keep the number of scenarios manageable, no more than {MAX_SCENARIOS}
scenarios plus the baseline may be added to the simulation set at once.
    """
    ),
)

# Use tabs to separate scenarios
if scenario_count > 0:
    scenarioTabs = st.tabs(
        [f"**#{i}** {session.scenario_names[i]}" for i in range(1, scenario_count + 1)],
        key="scenarioTabs",
        on_change="rerun",
    )
    for index, tab in enumerate(scenarioTabs):
        scenario_id = index + 1
        with tab:
            if tab.open:
                st.header(f"Scenario #{scenario_id}")
                # Scenario name
                nameField = st.empty()
                nameError = st.container()
                load_name("scenario_name", scenario_id)
                scenario_name = nameField.text_input(
                    "Name of Scenario",
                    f"Scenario #{scenario_id}",
                    max_chars=50,
                    key=f"_scenario_name{scenario_id}",
                    autocomplete="off",
                    on_change=save_name,
                    args=["scenario_name", scenario_id, nameError],
                    kwargs={
                        "special_containers": {"scenarioTabs": "**#{id}** {value}"}
                    },
                    placeholder="Enter a name for this scenario",
                    help="""
The name to give to this scenario, which will display
in tables and graphs generated by the dashboard.
                    """,
                )
                # Parameters for this scenario
                st.subheader("Parameters")

                # Place to put warnings and errors in the current parameter selection
                error_checker(scenario_id, f"Errors in {scenario_name}")

                # Advanced parameters toggle
                load_key("show_advanced", default=False, no_zero_default=True)
                containersToOpen: set[str] = {
                    f"paramTabs{id}" for id in range(1, scenario_count + 1)
                }
                show_advanced = st.toggle(
                    "Show Advanced Parameters",
                    False,
                    key="_showAdvanced",
                    on_change=container_save,
                    args=["show_advanced"],
                    kwargs={"containers": containersToOpen},
                    help="""
                Toggle whether to display parameters that control more fine-grain
                aspects of the simulation environment, such as age-specific NPI
                compliance or dynamic parameter updates.
                    """,
                )

                # Create tabs for each category of parameters
                dynamicTab: Optional[TabContainer] = None
                if show_advanced:
                    (
                        diseaseTab,
                        communityTab,
                        vaccineTab,
                        npiTab,
                        dynamicTab,
                        templateTab,
                    ) = st.tabs(
                        [
                            ":material/coronavirus: Pathogen",
                            ":material/groups: Community",
                            ":material/vaccines: Vaccination",
                            ":material/medical_mask: NPIs",
                            ":material/manage_history: Dynamic",
                            ":material/list_alt: Templates",
                        ],
                        on_change="rerun",
                        key=f"paramTabs{scenario_id}",
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
                        key=f"paramTabs{scenario_id}",
                    )
                if diseaseTab.open:
                    with diseaseTab:
                        build_disease_tab(scenario_id, show_advanced)
                if communityTab.open:
                    with communityTab:
                        build_community_tab(scenario_id, show_advanced)
                if vaccineTab.open:
                    with vaccineTab:
                        build_vaccination_tab(scenario_id, show_advanced)
                if npiTab.open:
                    containersToOpen |= {
                        f"npi_container{scenario_id}",
                        f"school_closure_container{scenario_id}",
                        f"withdrawal_increase_container{scenario_id}",
                        f"reduced_workgroup_container{scenario_id}",
                        f"bcc_reduction_container{scenario_id}",
                    }
                    with npiTab:
                        build_npi_tab(scenario_id, show_advanced)
                if dynamicTab is not None and dynamicTab.open:
                    with dynamicTab:
                        build_dynamic_tab(scenario_id)
                if templateTab.open:
                    with templateTab:
                        buildTemplateTab(scenario_id)

                # Remove button
                st.button(
                    label="Remove Scenario",
                    icon=":material/delete:",
                    type="primary",
                    key=f"scenarioRemove{scenario_id}",
                    on_click=delete_scenarioDialog,
                    args=[scenario_id],
                    help="""
Remove this scenario from the simulation set, thus ensuring that it is not
ran when you run the simulation.
                    """,
                )
