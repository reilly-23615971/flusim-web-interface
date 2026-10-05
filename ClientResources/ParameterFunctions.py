# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used for parameters and their relevant widgets

# Imports
from typing import Any, Callable, Optional

import pandas as pd
import streamlit as st

# Store st.session_state as variable for efficiency
session = st.session_state

# List of parameters that will be affected by changing cycle_count
# TODO: Add additional parameters or devise a way to automate their addition
TIME_PARAMS = [
    ("seedPeriod", "Infection Seeding Time Period"),
    ("schoolClosurePeriod", "School Closure Time Period"),
    ("withdrawalIncreasePeriod", "Withdrawal Increase Time Period"),
    ("reducedGroupPeriod", "Reduced Group Size Time Period"),
    ("bccPeriod", "BCC Reduction Time Period"),
]

# List of parameters that modify dynamic parameter forms when changed
DYNAMIC_PARAMS = {
    "seedPeriod": ("seedTimeForm", "Infection Seeding Rate"),
    "schoolClosurePeriod": ("closeTimeForm", "School Closure Compliance"),
    "bccPeriod": ("bccTimeForm", "Reduced Background Contact Count"),
}


# Widget Functions
def container_save(
    key: str,
    scenario_id: int = -1,
    containers: set[str] = set(),
    special_containers: dict[str, str] = {},
):
    """
    Wrapper for `save_key` that keeps specific containers open, used for
    advanced parameters and scenario names.

    Parameters:
        key (str): The string used to identify the widget.

        scenario_id (int): The integer representing the scenario the widget
            is part of. If this is negative, no ID will be added, allowing for
            parameters that are not associated with scenarios to be saved.

        containers (set of str): String used to identify each container to open.

        special_containers (dict of str): String used to identify containers
            that must be set to specific values (i.e. scenario tabs whose
            names change). Including `{id}` or `{value}` in one of the values
            for these will replace them with the value of `scenario_id` or the
            value of the widget that is being saved, respectively.
    """

    display_id = scenario_id if scenario_id >= 0 else ""
    save_key(key, scenario_id)
    for container in containers:
        session[container] = session.get(container)
    for container, value in special_containers.items():
        session[container] = value.format(
            id=display_id, value=session.get(f"{key}{display_id}")
        )


def save_key(
    key: str,
    scenario_id: int = -1,
    extra: Optional[str] = None,
    not_scenario=False,
    dataframe=False,
):
    """
    Function to save widget values into permanent `st.session_state` variables.

    Parameters:
        key (str): The string used to identify the widget.

        scenario_id (int): The integer representing the scenario the widget
            is part of. If this is negative, no ID will be added, allowing for
            parameters that are not associated with scenarios to be saved.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.

        not_scenario (bool): Set to `True` if the widget isn't a parameter for scenarios.

        dataframe (bool): Set to `True` if the widget is a dataframe that requires
            manual application of changes.
    """
    # TODO: See if dataframes can not reload after every change
    # TODO: See if scenario dataframes can adapt to baseline changes
    # (e.g. by having None/NA cells with the placeholder "Same as baseline")

    # Prevent invalid calls after deleting scenarios
    if scenario_id > session["scenario_count"]:
        return
    key_string = (
        f"{key}{scenario_id if scenario_id >= 0 else ""}{extra if extra else ""}"
    )
    if dataframe:
        # Load both data and changes
        current_data = session[key_string].copy()
        modified_data = session[f"_{key_string}"]

        # Row changes
        for row, edit in modified_data["edited_rows"].items():
            for column, new_value in edit.items():
                current_data.loc[row, column] = new_value

        # Row additions
        for new_row in modified_data["added_rows"]:
            current_data.loc[current_data.shape[0]] = new_row

        # Row removals
        current_data = current_data.drop(modified_data["deleted_rows"]).reset_index(
            drop=True
        )

        # Save the edited data
        session[key_string] = current_data
    else:
        session[key_string] = session.get(f"_{key_string}")

    # Add to scenario param lists if it's a scenario param (ID > 0)
    if not not_scenario and scenario_id > 0:
        if extra:
            session["scenario_extra_params"][scenario_id].add((key, extra))
        else:
            session["scenario_set_params"][scenario_id].add(key)


def load_key(
    key: str,
    scenario_id: int = -1,
    default=None,
    extra: Optional[str] = None,
    no_zero_default=False,
    dataframe=False,
):
    """
    Function to update widgets with permanent session state variables.

    Parameters:
        key (str): The string used to identify the widget.

        scenario_id (int): The integer representing the scenario the widget
            is part of. If this is negative, no ID will be added, allowing for
            parameters that are not associated with scenarios to be saved.

        default: The value to use if the widget is not present.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.

        no_zero_default (bool): Set to `True` if the widget shouldn't fall back
            on baseline values.

        dataframe (bool): Set to `True` for dataframe widgets that load
            their data differently.
    """

    key_string = (
        f"{key}{scenario_id if scenario_id >= 0 else ""}{extra if extra else ""}"
    )
    hidden_prefix = "_" if not dataframe else ""
    if no_zero_default or scenario_id < 0:
        session[f"{hidden_prefix}{key_string}"] = session.get(f"{key_string}", default)
    else:
        session[f"{hidden_prefix}{key_string}"] = (
            id_get(key, scenario_id, default, extra).copy()
            if dataframe
            else id_get(key, scenario_id, default, extra)
        )
    # Ensure dataframes are properly cleaned up even if never edited
    if dataframe and scenario_id > 0:
        if extra:
            session["scenario_extra_params"][scenario_id].add((key, extra))
        else:
            session["scenario_set_params"][scenario_id].add(key)


def time_scale_change():
    """
    Function to update the ranges of time-based parameters.
    """
    save_key("cycle_count")
    new_length = session["cycle_count"]
    changed_list = []
    for id in range(session["scenario_count"] + 1):
        for key, name in TIME_PARAMS:
            full_key = f"{key}{id}"
            old_value = session.get(full_key, None)
            if old_value is not None:
                if old_value[1] > new_length:
                    changed_list.append(name)
                session[full_key] = (
                    min(old_value[0], new_length),
                    min(old_value[1], new_length),
                )
    for param, (form, name) in DYNAMIC_PARAMS.items():
        dynamic_scale_change(param, form, name, 0, no_save=True)
    if changed_list:
        # TODO: Note which scenario these were present in
        st.toast(
            f"""
These parameters were above the new simulation length,
so they have been reduced:\n""" + "\n".join(f"- {name}" for name in changed_list),
            icon=":material/timer_arrow_down:",
            duration="infinite",
        )


def dynamic_scale_change(
    scale_key: str,
    form_key: str,
    param_name: str,
    scenario_id: int,
    condition: Optional[Callable[[], bool]] = None,
    no_save=False,
):
    """
    Function to update the ranges of dynamic parameters.

    Parameters:
        scale_key (str): The identifier used to distinguish the dynamic
            parameter being modified.

        form_key (str): The identifier used to distinguish the form
            whose ranges must be updated.

        param_name (str): The name of the parameter, to display in messages
            indicating that something has changed.

        scenario_id (int): The integer representing the scenario the widget
            is part of.

        condition (callable, returns bool, optional): A criteria that skips
            the range update if fulfilled, formatted as a function that
            returns `True` when the criteria is met.

        no_save (bool): Set to `True` if running this function from a different
            page where saving the widget value would instead set it to `None`.
    """

    if not no_save:
        save_key(scale_key, scenario_id)
    if condition is None or condition():
        has_changed = False
        new_min, new_max = id_get(scale_key, scenario_id, (1, 720))
        if scenario_id == 0:
            # Check all scenarios if the baseline was modified
            for id in range(session["scenario_count"] + 1):
                full_key = f"{form_key}{id}"
                scenario_min, scenario_max = id_get(scale_key, id, (new_min, new_max))
                form = session.get(full_key, None)
                if form is not None and not form.empty:
                    new_days = form["Day to Update Parameter"].clip(
                        lower=scenario_min, upper=scenario_max
                    )
                    if not new_days.equals(form["Day to Update Parameter"]):
                        has_changed = True
                    form["Day to Update Parameter"] = new_days
                    session[full_key] = form
        else:
            # Only update the relevant scenario
            full_key = f"{form_key}{scenario_id}"
            form = session.get(full_key, None)
            if form is not None and not form.empty:
                new_days = form["Day to Update Parameter"].clip(
                    lower=new_min, upper=new_max
                )
                if not new_days.equals(form["Day to Update Parameter"]):
                    has_changed = True
                form["Day to Update Parameter"] = new_days
                session[full_key] = form

        # Notify any changes
        if has_changed:
            st.toast(
                f"""
Some of the dynamic update points for {param_name} were outside
of the new period where {param_name.rsplit(' ', 1)[0]} is active.
They have been adjusted to fit the new period.
            """,
                icon=":material/timer_arrow_down:",
                duration="infinite",
            )


def id_get(key: str, scenario_id: int, default_value, extra: Optional[str] = None):
    """
    Simple function to get a specific session state value with a specific
    ID, checking ID 0 if the specified one doesn't exist before falling
    back on a default.

    Parameters:
        key (str): The string component of the session state variable to get.

        scenario_id (int): The integer representing the scenario the value is part of.

        default_value: The value to return if neither the specified key nor the
            baseline have values in `st.session_state`.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.
    """
    if not extra:
        return session.get(f"{key}{scenario_id}", session.get(f"{key}0", default_value))
    else:
        return session.get(
            f"{key}{scenario_id}{extra}",
            session.get(f"{key}0{extra}", default_value),
        )


# Variable-Length Form Functions
def has_duplicates(df: pd.DataFrame, column: str = "Age Group"):
    """
    Simple function to check if there are duplicates in a given dataframe row.

    Parameters:
        df (DataFrame): The dataframe to check.

        column (str): The column to check.
    """
    return len(set(df[column])) != len(df[column])


def replace_table_na(df: pd.DataFrame, column_dict: dict[str, Any]) -> pd.DataFrame:
    """
    Function to fill NA values in specific dataframe columns, accounting for
    values that don't work with pandas' built-in `fillna` function like the empty list.

    Parameters:
        df (DataFrame): The dataframe to modify.

        column_dict (dict with str keys): A dictionary containing column names
            and the value to replace NA values with.

    Returns:
        Dataframe: The dataframe with NA values replaced as needed.
    """
    new_table = df.copy()
    for column, value in column_dict.items():
        if column in new_table.columns:
            for row in new_table.loc[new_table[column].isnull(), column].index:
                new_table.at[row, column] = value
    return new_table


# Schema loading functions
def update_param_from_schema(
    key: str,
    value: Any,
    scenario_id: int,
    extra: Optional[str] = None,
):
    """
    Wrapper function to ensure scenario parameters loaded from a schema are
    added to sets for deletion

    Parameters:
        key (str): The string used to identify the parameter.

        value (any): The new value from the schema.

        scenario_id (int): The integer representing the scenario the parameter
            is part of.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.
    """
    session[f"{key}{scenario_id}{extra if extra else ""}"] = value
    if scenario_id:
        if extra:
            session["scenario_extra_params"][scenario_id].add((key, extra))
        else:
            session["scenario_set_params"][scenario_id].add(key)


def update_table_from_schema(
    key: str,
    new_table: pd.DataFrame,
    scenario_id: int,
    default_table: pd.DataFrame,
    extra: Optional[str] = None,
):
    """
    Function to update tables in the dashboard using one constructed from a
    schema, accounting for the default table style.

    Parameters:
        key (str): The string used to identify the table.

        new_table (DataFrame): The new table data from the schema.

        scenario_id (int): The integer representing the scenario the table is part of.

        default_table (DataFrame): The table to load if neither `new_table` nor
            the baseline scenario have any data to utilise.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.
    """
    session[f"{key}{scenario_id}{extra if extra else ""}"] = (
        default_table if new_table.empty else new_table.reset_index(drop=True)
    )
    # Add to scenario parameters for ease of deletion
    if scenario_id:
        if extra:
            session["scenario_extra_params"][scenario_id].add((key, extra))
        else:
            session["scenario_set_params"][scenario_id].add(key)
