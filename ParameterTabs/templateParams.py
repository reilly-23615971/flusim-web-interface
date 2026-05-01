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
from ClientResources.SharedResources import templateDict

# Logging
templateLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.dialog("Load Scenario as Template", width="large", icon=":material/list_alt_add:")
def defaultTemplateButton(scenarioID: int, templatePath: str, templateName: str):
    """
    Dialog wrapper to confirm replacing scenario parameters with template values.

    Parameters:
        scenarioID (int): The ID representing the scenario to replace the values of.

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
                if scenarioID == 0
                else f'scenario named "{session[f"scenarioName{scenarioID}"]}"'
            ),
            template=templateName,
        )
    )
    if scenarioID == 0 and session.get("scenarioCount"):
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
        loadTemplate(scenarioID, templatePath)
        st.rerun()


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

    currentName = session[f"scenarioName{currentID}"]
    newName = session[f"scenarioName{newID}"]
    st.markdown(f"""
Are you sure you want to replace the parameter values in the
{"baseline scenario" if currentID == 0 else f'scenario named "{currentName}"'}
with the values from the
{"baseline scenario" if newID == 0 else f'scenario named "{newName}"'}?
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
        template = createTemplate(newID)
        loadTemplate(currentID, template)
        st.rerun()


@st.dialog(
    "Reset Scenario to Baseline Values",
    width="large",
    icon=":material/settings_backup_restore:",
)
def scenarioResetButton(scenarioID: int):
    """
    Dialog wrapper to confirm the resetting of a scenario to baseline values.

    Parameters:
        scenarioID (int): The ID representing the scenario to be reset.
    """
    # Validate scenario ID
    if scenarioID == 0:
        templateLog.error(
            "[scenarioResetButton] Tried to reset baseline scenario to itself"
        )
        st.rerun()

    # Disable button if it's taking a while to update parameters
    templatePending = bool(session.get("confirmTemplateButton"))

    st.markdown(f"""
Are you sure you want to reset the parameter values in the scenario named
"{session[f"scenarioName{scenarioID}"]}" to the values from the baseline
scenario? Note that this will not change the scenario's name.
        """)
    if st.button(
        "Confirm",
        key="confirmTemplateButton",
        icon="spinner" if templatePending else None,
        disabled=templatePending,
    ):
        resetScenario(scenarioID)
        st.rerun()


# @st.fragment
def buildTemplateTab(scenarioID: int):
    """
    Function to generate template loading buttons in a specified container
    with scenario differentiation.

    Parameters:
        scenarioID (int): An integer that will be used to differentiate the
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
    for templateName, (icon, templatePath, description) in templateDict.items():
        st.button(
            templateName,
            icon=f":material/{icon}:",
            key=f"_defaultTemplateButton{templateName}",
            on_click=defaultTemplateButton,
            args=[scenarioID, templatePath, templateName],
            help=description,
        )

    # Scenario Templates
    scenarioCount = session.get("scenarioCount", 0)
    if scenarioCount > 0:
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
            args=[scenarioID],
            disabled=scenarioID == 0,
            help=(
                """
Resets the values of all parameters in the current scenario to match the
values set in the baseline scenario.
                """
                if scenarioID != 0
                else """
You cannot reset the baseline scenario back to itself. If you wish to reset
all parameters to the values they had when first opening the dashboard, load
the "Influenza" template.
                """
            ),
        )
        for templateID in range(1, scenarioCount + 1):
            scenarioName = session[f"scenarioName{templateID}"]
            st.button(
                f"Load {scenarioName} as Template",
                icon=":material/list_alt_add:",
                key=f"_scenarioTemplateButton{templateID}",
                on_click=scenarioTemplateButton,
                args=[scenarioID, templateID],
                disabled=templateID == scenarioID,
                help=(
                    f"""
Set the parameter values in the current scenario to match the values set in the
scenario named {scenarioName}. Note that this will override all parameters
currently set for this scenario.
                """
                    if templateID != scenarioID
                    else """
A scenario cannot use its own parameters as a template.
                """
                ),
            )
