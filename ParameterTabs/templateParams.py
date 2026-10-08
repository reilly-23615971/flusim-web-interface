# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where parameter presets can be loaded

# Imports
import logging

import streamlit as st

from ClientResources.DownloadFunctions import (
    createTemplate,
    loadTemplate,
    resetScenario,
)
from ClientResources.Constants import TEMPLATES

# Logging
templateLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.dialog("Load Scenario as Template", width="large", icon=":material/list_alt_add:")
def defaultTemplateButton(scenario_id: int, templatePath: str, templateName: str):
    """
    Dialog wrapper to confirm replacing scenario parameters with template values.

    Parameters:
        scenario_id (int): The ID representing the scenario to replace the values of.

        templatePath (str): The path to the JSON file holding the template
            parameter values.

        templateName (str): The name of the template.
    """
    # Disable button if it's taking a while to update parameters
    templatePending = bool(session.get("confirmTemplateButton"))

    st.markdown(
        """
Are you sure you want to replace the parameter values in the {name}
with the values from the "{template}" template? Note that this will not
change the name of the scenario.
        """.format(
            name=(
                "baseline scenario"
                if scenario_id == 0
                else f'scenario named "{session[f"scenarioName{scenario_id}"]}"'
            ),
            template=templateName,
        )
    )
    if scenario_id == 0 and session.get("scenario_count"):
        st.warning(
            body="""
                Updating the baseline scenario's parameter values with a
                template may affect unset parameters in other scenarios.
            """,
            icon=":material/dataset_linked:",
        )
    if st.button(
        "Confirm",
        key="confirmTemplateButton",
        icon="spinner" if templatePending else None,
        disabled=templatePending,
    ):
        loadTemplate(scenario_id, templatePath)


@st.dialog("Load Scenario as Template", width="large", icon=":material/list_alt_add:")
def scenarioTemplateButton(currentID: int, newID: int):
    """
    Dialog wrapper to confirm copying scenario parameters onto another scenario.

    Parameters:
        currentID (int): The ID representing the scenario to replace the values of.

        newID (int): The ID representing the scenario to take the values from.
    """
    # Validate scenario ID
    if newID == 0:
        templateLog.error("""
[scenarioTemplateButton] Tried to load baseline scenario as template;
use resetScenario for that!
        """)
        st.rerun()
    if currentID == newID:
        templateLog.error(
            f"[scenarioTemplateButton] Tried to load scenario {newID} onto itself"
        )
        st.rerun()

    # Disable button if it's taking a while to update parameters
    templatePending = bool(session.get("confirmTemplateButton"))

    current_name = session[f"scenarioName{currentID}"]
    new_name = session[f"scenarioName{newID}"]
    st.markdown(f"""
Are you sure you want to replace the parameter values in the
{"baseline scenario" if currentID == 0 else f'scenario named "{current_name}"'}
with the values from the
{"baseline scenario" if newID == 0 else f'scenario named "{new_name}"'}?
Note that this will not change the names of either scenario.
    """)
    if currentID == 0:
        st.warning(
            body="""
                Updating the baseline scenario's parameter values with a
                template may affect unset parameters in other scenarios.
            """,
            icon=":material/dataset_linked:",
        )
    if st.button(
        "Confirm",
        key="confirmTemplateButton",
        icon="spinner" if templatePending else None,
        disabled=templatePending,
    ):
        template = createTemplate(newID, include_dashboard=True)
        loadTemplate(currentID, template)


@st.dialog(
    "Reset Scenario to Baseline Values",
    width="large",
    icon=":material/settings_backup_restore:",
)
def scenarioResetButton(scenario_id: int):
    """
    Dialog wrapper to confirm the resetting of a scenario to baseline values.

    Parameters:
        scenario_id (int): The ID representing the scenario to be reset.
    """
    # Validate scenario ID
    if scenario_id == 0:
        templateLog.error(
            "[scenarioResetButton] Tried to reset baseline scenario to itself"
        )
        st.rerun()

    # Disable button if it's taking a while to update parameters
    templatePending = bool(session.get("confirmTemplateButton"))

    st.markdown(f"""
Are you sure you want to reset the parameter values in the scenario named
"{session[f"scenarioName{scenario_id}"]}" to the values from the baseline
scenario? Note that this will not change the scenario's name.
    """)
    if st.button(
        "Confirm",
        key="confirmTemplateButton",
        icon="spinner" if templatePending else None,
        disabled=templatePending,
    ):
        resetScenario(scenario_id)
        st.rerun()


# @st.fragment
def buildTemplateTab(scenario_id: int):
    """
    Function to generate template loading buttons in a specified container
    with scenario differentiation.

    Parameters:
        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number
            to the Streamlit session state variables.
    """

    # Tab Content
    st.header("Parameter Templates")
    st.markdown("""
        This tab allows for presets representing existing infectious diseases
        or scenarios to be loaded onto the dashboard.
    """)

    # Disease Templates
    st.subheader(
        "Default Templates",
        help="""
The templates in this section use parameter settings that replicate a real-life
disease or situation.
        """,
    )
    # TODO: Load parameter defaults directly from flu template
    # rather than having them be hardcoded
    for templateName, (icon, templatePath, description) in TEMPLATES.items():
        st.button(
            templateName,
            icon=f":material/{icon}:",
            on_click=defaultTemplateButton,
            args=[scenario_id, templatePath, templateName],
            help=description,
        )

    # Scenario Templates
    scenario_count = session.get("scenario_count", 0)
    if scenario_count > 0:
        st.subheader(
            "Scenario Templates",
            help="""
The templates in this section use the parameter settings from one of the other
scenarios currently configured in the dashboard, allowing you to copy their
settings onto a different scenario.
            """,
        )
        st.button(
            "Reset to Baseline Scenario",
            icon=":material/settings_backup_restore:",
            key="_scenarioTemplateButton0",
            on_click=scenarioResetButton,
            args=[scenario_id],
            disabled=scenario_id == 0,
            help=(
                """
Resets the values of all parameters in the current scenario to match the
values set in the baseline scenario.
                """
                if scenario_id != 0
                else """
You cannot reset the baseline scenario back to itself. If you wish to reset
all parameters to the values they had when first opening the dashboard, load
the "Influenza" template.
                """
            ),
        )
        for templateID in range(1, scenario_count + 1):
            scenarioName = session[f"scenarioName{templateID}"]
            st.button(
                f"Load {scenarioName} as Template",
                icon=":material/list_alt_add:",
                key=f"_scenarioTemplateButton{templateID}",
                on_click=scenarioTemplateButton,
                args=[scenario_id, templateID],
                disabled=templateID == scenario_id,
                help=(
                    f"""
Set the parameter values in the current scenario to match the values set in the
scenario named {scenarioName}. Note that this will override all parameters
currently set for this scenario.
                """
                    if templateID != scenario_id
                    else """
A scenario cannot use its own parameters as a template.
                """
                ),
            )
