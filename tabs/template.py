# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where parameter presets can be loaded

# Imports
import logging

import streamlit as st

from resources.download import (
    create_template,
    load_template,
    reset_scenario,
)
from resources.constants import TEMPLATES

# Logging
template_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.dialog("Load Scenario as Template", width="large", icon=":material/list_alt_add:")
def default_template_button(scenario_id: int, template_path: str, template_name: str):
    """
    Dialog wrapper to confirm replacing scenario parameters with template values.

    Parameters:
        scenario_id (int): The ID representing the scenario to replace the
            values of.

        template_path (str): The path to the JSON file holding the template
            parameter values.

        template_name (str): The name of the template.
    """
    # Disable button if it's taking a while to update parameters
    template_pending = bool(session.get("confirm_template_button"))

    st.markdown(
        """
Are you sure you want to replace the parameter values in the {name} with the
values from the "{template}" template? Note that this will not change the name
of the scenario.
        """.format(
            name=(
                "baseline scenario"
                if scenario_id == 0
                else f'scenario named "{session.scenario_names[scenario_id]}"'
            ),
            template=template_name,
        )
    )
    if scenario_id == 0 and session.get("scenario_count"):
        st.warning(
            body="""
Updating the baseline scenario's parameter values with a template may affect
unset parameters in other scenarios.
            """,
            icon=":material/dataset_linked:",
        )
    st.button(
        "Confirm",
        key="confirm_template_button",
        icon="spinner" if template_pending else None,
        disabled=template_pending,
    )
    if template_pending:
        load_template(scenario_id, template_path)


@st.dialog("Load Scenario as Template", width="large", icon=":material/list_alt_add:")
def scenario_template_button(current_scenario_id: int, new_scenario_id: int):
    """
    Dialog wrapper to confirm copying scenario parameters onto another scenario.

    Parameters:
        current_scenario_id (int): The ID representing the scenario to replace
            the values of.

        new_scenario_id (int): The ID representing the scenario to take the
            values from.
    """
    # Validate scenario ID
    if new_scenario_id == 0:
        template_log.error("""
[scenario_template_button] Tried to load baseline scenario as template;
use reset_scenario for that!
        """)
        st.rerun()
    if current_scenario_id == new_scenario_id:
        template_log.error(
            f"[scenario_template_button] Tried to load scenario {new_scenario_id} onto itself"
        )
        st.rerun()

    # Disable button if it's taking a while to update parameters
    template_pending = bool(session.get("confirm_template_button"))

    current_name = session.scenario_names[current_scenario_id]
    new_name = session.scenario_names[new_scenario_id]
    st.markdown(f"""
Are you sure you want to replace the parameter values in the
{"baseline scenario" if current_scenario_id == 0 else f'scenario named "{current_name}"'}
with the values from the
{"baseline scenario" if new_scenario_id == 0 else f'scenario named "{new_name}"'}?
Note that this will not change the names of either scenario.
    """)
    if current_scenario_id == 0:
        st.warning(
            body="""
Updating the baseline scenario's parameter values with a template may affect
unset parameters in other scenarios.
            """,
            icon=":material/dataset_linked:",
        )
    if st.button(
        "Confirm",
        key="confirm_template_button",
        icon="spinner" if template_pending else None,
        disabled=template_pending,
    ):
        template = create_template(new_scenario_id, include_dashboard=True)
        load_template(current_scenario_id, template)


@st.dialog(
    "Reset Scenario to Baseline Values",
    width="large",
    icon=":material/settings_backup_restore:",
)
def scenario_reset_button(scenario_id: int):
    """
    Dialog wrapper to confirm the resetting of a scenario to baseline values.

    Parameters:
        scenario_id (int): The ID representing the scenario to be reset.
    """
    # Validate scenario ID
    if scenario_id == 0:
        template_log.error(
            "[scenario_reset_button] Tried to reset baseline scenario to itself"
        )
        st.rerun()

    # Disable button if it's taking a while to update parameters
    template_pending = bool(session.get("confirm_template_button"))

    st.markdown(f"""
Are you sure you want to reset the parameter values in the scenario named
"{session.scenario_names[scenario_id]}" to the values from the baseline
scenario? Note that this will not change the scenario's name.
    """)
    if st.button(
        "Confirm",
        key="confirm_template_button",
        icon="spinner" if template_pending else None,
        disabled=template_pending,
    ):
        reset_scenario(scenario_id)
        st.rerun()


# @st.fragment
def build_template_tab(scenario_id: int):
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
This tab allows for presets representing existing infectious diseases or
scenarios to be loaded onto the dashboard.
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
    for template_name, (icon, template_path, description) in TEMPLATES.items():
        st.button(
            template_name,
            icon=f":material/{icon}:",
            on_click=default_template_button,
            args=[scenario_id, template_path, template_name],
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
            key="_scenario_template_button0",
            on_click=scenario_reset_button,
            args=[scenario_id],
            disabled=scenario_id == 0,
            help=(
                """
Resets the values of all parameters in the current scenario to match the values
set in the baseline scenario.
                """
                if scenario_id != 0
                else """
You cannot reset the baseline scenario back to itself. If you wish to reset all
parameters to the values they had when first opening the dashboard, load the
"Influenza" template.
                """
            ),
        )
        for template_id in range(1, scenario_count + 1):
            scenario_name = session.scenario_names[template_id]
            st.button(
                f"Load {scenario_name} as Template",
                icon=":material/list_alt_add:",
                key=f"_scenario_template_button{template_id}",
                on_click=scenario_template_button,
                args=[scenario_id, template_id],
                disabled=template_id == scenario_id,
                help=(
                    f"""
Set the parameter values in the current scenario to match the values set in the
scenario named {scenario_name}. Note that this will override all parameters
currently set for this scenario.
                """
                    if template_id != scenario_id
                    else """
A scenario cannot use its own parameters as a template.
                """
                ),
            )
