# Flusim Web Interface Application
# Developed by Reilly Evans
# Miscellaneous functions used by the client dashboard

# Imports
import re
from functools import partial
from typing import Any, Callable, Optional, cast

import numpy as np
import pandas as pd
import streamlit as st
from pydantic import BaseModel, ValidationError
from streamlit.delta_generator import DeltaGenerator

from ClientResources.ParameterFunctions import container_save, id_get
from ClientResources.Types import (
    AGE_GROUP_KEYS,
    AGE_GROUPS,
    AGE_KEY_CONVERTER,
    AgeGroup,
    AgeGroupKey,
    AgeWithTotal,
)

# Store st.session_state as variable for efficiency
session = st.session_state

# Tools for error messages
# Error Colours: Text #BD4043, Background #FFE9E9
error_format = partial(st.error, icon=":material/error:")
# Warning Colours: Text #926C05, Background #FFFFEC
warn_format = partial(st.warning, icon=":material/warning:")
# Use sRGB in the colour picker for the best display/code match


# Error functions
def param_error(
    label: str,
    scenario_id: int,
    condition: Callable[[], bool | np.bool],
    message: str,
    is_severe: bool = False,
):
    """
    Function to display an error message if a condition is met.

    Parameters:
        label (str): A string to identify this specific error.

        scenario_id (int): The integer representing the scenario this error applies to.

        condition (callable, returns bool): The criteria that must be fulfilled
            to display the error, formatted as a function that returns `True` when
            the criteria is met.

        message (str): The text to display for the error message.

        is_severe (bool): Set to `True` for red errors that prevent running
            the simulation if present.
    """
    # TODO: Allow errors to link to the affected parameter
    # (if anchor tags are/become possible)
    # TODO: Consider reworking errors so that you don't need to open
    # their tab to generate them
    if condition():
        if is_severe:
            error_format(message)
            session["active_errors"][scenario_id][label] = (message, True)
        else:
            warn_format(message)
            session["active_errors"][scenario_id][label] = (message, False)
    else:
        session["active_errors"][scenario_id].pop(label, None)


def dual_error(
    label: str,
    scenario_id: int,
    error_condition: Callable[[], bool],
    warn_condition: Callable[[], bool],
    error_message: str,
    warn_message: str,
):
    """
    Function to display an error message with two different severity levels
    if different conditions are met.

    Parameters:
        label (str): A string to identify this specific error.

        scenario_id (int): The integer representing the scenario this error applies to.

        error_condition (callable, returns bool): The criteria for a red,
            run-blocking error, formatted as a function that returns `True`
            when the criteria is met. This condition will override the
            condition in `warn_condition`.

        warn_condition (callable, returns bool): The criteria for a yellow,
            minor warning, formatted as a function that returns `True` when
            the criteria is met.

        error_message (str): The text to display for the red error message.

        warn_message (str): The text to display for the yellow error message.
    """
    if error_condition():
        error_format(error_message)
        session["active_errors"][scenario_id][label] = (error_message, True)
    elif warn_condition():
        warn_format(warn_message)
        session["active_errors"][scenario_id][label] = (warn_message, False)
    else:
        session["active_errors"][scenario_id].pop(label, None)


# @st.fragment(run_every=1)
def error_checker(scenario_id: int, name: str = "Errors in Current Scenario") -> bool:
    """
    Fragment to list errors from a specific scenario in a dropdown container.

    Parameters:
        scenario_id (int): The integer representing the scenario to pull errors from.

        name (str): The label of the dropdown container.

    Returns:
        bool: Returns `True` if at least one error was run-blocking and
            `False` otherwise.
    """
    # TODO: Consider removing the run_every parameter and defragmenting tabs
    severe_errors_found = False
    if session["active_errors"].get(scenario_id, False):
        with st.status(label=name, state="error"):
            for message, is_severe in session["active_errors"][scenario_id].values():
                if is_severe:
                    error_format(message)
                    severe_errors_found = True
                else:
                    warn_format(message)
    return severe_errors_found


def validation_error_formatting(e: ValidationError):
    """
    Function to convert ValidationErrors raised by Pydantic into user-readable
    error messages.

    Parameters:
        e (ValidationError): The error to unpack.
    """
    for error in e.errors():
        # TODO: Use Pydantic's method of subbing in custom messages
        # See https://pydantic.dev/docs/validation/latest/errors/errors/
        st.error(
            f"Error validating parameters: {error["msg"]}", icon=":material/error:"
        )


# Formatting functions
def plural(value: int | float) -> str:
    """
    Simple function to add "s" to words when a value is not 1.

    Parameters:
        value (int or float): The value to check.

    Returns:
        str: An empty string if `value` equals 1, or the string "s" otherwise.
    """
    return "" if value == 1 else "s"


def day_count(count: int | float) -> str:
    """
    Simple function to convert a number into a string describing a number of days.

    Parameters:
        count (int or float): The number of days to return.

    Returns:
        str: "1 Day" if `count` equals 1, or a string in the form "`count`
            Days" otherwise.
    """
    return "1 Day" if count == 1 else f"{count:g} Days"


def time_string(time: int | float) -> str:
    """
    Function to format a number of seconds in mm:ss (or h:mm:ss) format.

    Parameters:
        time (int or float): The number of seconds.

    Returns:
        str: The time as a string in either h:mm:ss or mm:ss format.
    """
    if time > 3600:
        return "{hours} hours, {minutes} minutes, {seconds} seconds".format(
            hours=int(time // 3600),
            minutes=str(int(time % 3600 // 60)).zfill(2),
            seconds=str(int(time % 60)).zfill(2),
        )
    else:
        return "{minutes} minutes, {seconds} seconds".format(
            minutes=int(time // 60),
            seconds=str(int(time % 60)).zfill(2),
        )


def health_outcome_store(
    scenario_names: list[str], use_ages: bool = True
) -> tuple[dict, dict]:
    """
    Function to format and store health burden outcome rates for a given set
    of scenarios.

    Parameters:
        scenario_names (list of str): The names of each scenario defined in
            the simulation.

        use_ages (Boolean): Set to False to ignore age-specific health burdens
            and define each of their values to be the same baseline value.

    Returns:
        tuple of dicts: A pair of dictionaries storing the global and age-specific
            health burden rates.
    """
    # Required values for outcome rates
    outcome_rates = {
        "Diagnosed Cases": ("case_ratio", 50.0, lambda x: x / 100),
        "GP Visits": ("gp_ratio", 17.0, lambda x: x / 100),
        "Hospitalisations": ("hospital_ratio", 320.0, lambda x: x / 100000),
        "Deaths": ("death_ratio", 12.0, lambda x: x / 100000),
    }

    # Basic rates
    single_rates = {}
    for outcome, (key, default, format_func) in outcome_rates.items():
        single_rates[outcome] = {
            name: format_func(id_get(key, scenario_id, default))
            for scenario_id, name in enumerate(scenario_names)
        }

    # ICU (dependent on hospitalisation)
    icu_multipliers = {
        name: id_get("icu_ratio", scenario_id, 20.0) / 100
        for scenario_id, name in enumerate(scenario_names)
    }
    single_rates["ICU Visits"] = {
        name: rate * icu_multipliers[name]
        for name, rate in single_rates["Hospitalisations"].items()
    }

    # Age-specific rates
    hospital_key, hospital_default, hospital_format = outcome_rates["Hospitalisations"]
    death_key, death_default, death_format = outcome_rates["Deaths"]
    age_rates = {}
    if use_ages:
        hospital_rates, icu_rates, death_rates = {}, {}, {}
        for scenario_id, name in enumerate(scenario_names):
            # Get previously-extracted base rates
            base_hospital_rate = single_rates["Hospitalisations"][name]
            base_death_rate = single_rates["Deaths"][name]
            base_icu_rate = icu_multipliers[name]
            # Format table with age-specific rates
            health_burden_age_form = (
                id_get(
                    "health_burden_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Hospitalisation Rate": [base_hospital_rate],
                            "Mortality Rate": [base_death_rate],
                        },
                    ),
                )
                .copy()
                .dropna()
                .replace({"Age Group": AGE_KEY_CONVERTER})
            )
            health_burden_age_form["Hospitalisation Rate"] = health_burden_age_form[
                "Hospitalisation Rate"
            ].apply(hospital_format)
            health_burden_age_form["Mortality Rate"] = health_burden_age_form[
                "Mortality Rate"
            ].apply(death_format)
            # Convert to dictionaries with base rate as default
            hospital_age_dict = (
                health_burden_age_form[["Age Group", "Hospitalisation Rate"]]
                .set_index("Age Group")["Hospitalisation Rate"]
                .to_dict()
            )
            hospital_rates[name] = {
                age: base_hospital_rate for age in AGE_GROUPS
            } | hospital_age_dict

            icu_age_dict = {
                age: rate * base_icu_rate for age, rate in hospital_age_dict.items()
            }
            icu_rates[name] = {
                age: base_hospital_rate * base_icu_rate for age in AGE_GROUPS
            } | icu_age_dict

            mort_age_dict = (
                health_burden_age_form[["Age Group", "Mortality Rate"]]
                .set_index("Age Group")["Mortality Rate"]
                .to_dict()
            )
            death_rates[name] = {
                age: base_death_rate for age in AGE_GROUPS
            } | mort_age_dict
        age_rates = {
            "Hospitalisations": hospital_rates,
            "ICU Visits": icu_rates,
            "Deaths": death_rates,
        }
    else:
        # Just set every age to the base rate
        # TODO: Avoid this unnecessary iteration and just check elsewhere
        # that there's no age-specific rates in use
        age_rates = {
            "Hospitalisations": {
                scenario: {
                    age: hospital_format(id_get(hospital_key, i, hospital_default))
                    for age in AGE_GROUPS
                }
                for i, scenario in enumerate(scenario_names)
            },
            "Deaths": {
                scenario: {
                    age: death_format(id_get(death_key, i, death_default))
                    for age in AGE_GROUPS
                }
                for i, scenario in enumerate(scenario_names)
            },
        }
        age_rates["ICU Visits"] = {
            name: {
                age: rate * icu_multipliers[name]
                for age, rate in age_rates["Hospitalisations"][name].items()
            }
            for name in scenario_names
        }

    return single_rates, age_rates


# Scenario name functions
def save_name(
    key: str,
    scenario_id: int,
    error_container: DeltaGenerator,
    special_containers: dict[str, str] = {},
):
    """
    Function to save scenario names into a list while stopping
        empty or duplicate names being saved.

    Parameters:
        key (str): The string used to identify the name-setting widget.

        scenario_id (int): The integer representing the scenario the widget
            is naming. Should not be 0 (the baseline scenario with a fixed name).

        error_container (DeltaGenerator): The Streamlit container in which to
            display the error message.

        special_containers (dict of str): String used to identify containers
            that must be set to specific values (i.e. scenario tabs whose
            names change). Including `{id}` or `{value}` in one of the values
            for these will replace them with the value of `scenario_id` or the
            value of the widget that is being saved, respectively.

    Raises:
        ValueError: If an ID less than 1 is passed.
    """
    if scenario_id <= 0:
        raise ValueError("id for save_name must be greater than 0")
    new_name = session.get(f"_{key}{scenario_id}")
    current_names = session.scenario_names
    if new_name == "":
        # TODO: Can be replaced with required keyword in Streamlit 1.65
        error_container.error(
            "Please enter a name.",
            icon=":material/remove_selection:",
        )
    elif new_name == current_names[0]:
        error_container.error(
            f"""
The name "{new_name}" is reserved for the scenario described at the
:grey-badge[:material/variable_insert: Baseline Parameters] page. Please enter
a different name.
            """,
            icon=":material/tab_close_inactive:",
        )
    elif new_name in current_names and new_name != current_names[scenario_id]:
        error_container.error(
            f"""
"{new_name}" is already the name of a different scenario. Please enter a
different name.
            """,
            icon=":material/tab_close_inactive:",
        )
    else:
        # Update saved names for r0
        if session.get("calib_saved_id") == scenario_id:
            session["calib_scenario_name"] = new_name

        session.scenario_names[scenario_id] = new_name
        for container, value in special_containers.items():
            session[container] = value.format(id=scenario_id, value=new_name)


def load_name(key: str, scenario_id: int = -1):
    """
    Function to update scenario names with permanent session state variables.

    Parameters:
        key (str): The string used to identify the name-setting widget.

        scenario_id (int): The integer representing the scenario the widget
            is part of.
    """
    key_string = f"{key}{scenario_id if scenario_id >= 0 else ""}"
    session[f"_{key_string}"] = session.scenario_names[scenario_id]


def unique_name(current_name: str, names: set[str]) -> str:
    """
    Function to add a suffix to a string to make it unique compared to a set.

    Parameters:
        current_name (str): The string to make unique.

        names (set of str): The other strings to compare with.

    Returns:
        str: A name that is different from all strings in `names`.
    """
    if current_name not in names:
        return current_name

    # Check if suffix is already present and increment if so
    match = re.match(r"^(.*?)(?: (\d+))?$", current_name)
    if match is not None:
        base, num = match.groups()
        n = int(num) if num else 2
    else:
        base = current_name
        n = 2

    candidate = f"{base} {n}"
    while candidate in names:
        n += 1
        candidate = f"{base} {n}"
    return candidate


# Age functions
def age_sort(age: tuple[AgeGroupKey, Any]) -> int:
    """
    Function to be used in `sorted()` for ordering age groups.

    Parameters:
        age (tuple with str): A tuple where the first item is the string
            representation of an age group.

    Returns:
        int: The numeric ordering index of the age group.
    """
    return AGE_GROUP_KEYS.index(age[0])


def age_sort_series(ages: pd.Series) -> pd.Series:
    """
    Function to be used in `pd.sort_values` for ordering age groups

    Parameters:
        age (Series): A Series containing string representations of age groups.

    Returns:
        Series: A Series containing the numeric ordering index of each age group.
    """
    return ages.map({age: index for index, age in enumerate(AGE_GROUP_KEYS)})


def age_display(option: str | int | float | bool) -> AgeGroup:
    """
    Function to be passed to format_func for displaying selectbox values

    Parameters:
        option (str): The string to be converted from key to display value.

    Returns:
        str: The display value corresponding to the selectbox option.
    """
    return AGE_KEY_CONVERTER[cast(AgeGroupKey, str(option))]


def age_range_string(lower: int | float, upper: int | float) -> str:
    """
    Simple function to format 2 numbers as an age range, accounting for
    unbound ends and rendering decimal values as months.

    Parameters:
        lower (int or float): The lower bound of the range.

        lower (int or float): The upper bound of the range.

    Returns:
        str: The string representation of the specified range.
    """
    if upper > 250:
        # Use a + for ranges large enough to be uncapped
        return f"{lower}+"
    elif (isinstance(lower, float) or isinstance(upper, float)) and upper < 9:
        # Use months if it's more readable that way
        return "{low}-{high} Months".format(
            low=round(lower * 12), high=round((upper if upper < 1 else upper - 1) * 12)
        )
    else:
        return f"{lower}-{upper - 1}"


def age_range_combiner(ages: list[AgeWithTotal]) -> str:
    """
    Function to convert a list of age brackets into a single string
    concisely listing them all.

    Parameters:
        ages (list of str): The age groups to combine.

    Returns:
        str: The string representation of the specified age groups.
    """
    # Immediate end conditions
    if len(ages) == 1:
        return (
            "All Ages" if ages[0] == "Total" else re.findall(r"\((.*?)\)", ages[0])[0]
        )
    if set(ages) == set(AGE_GROUPS):
        return "All Ages"

    # Dictionaries to get the starts/ends of each age bracket
    age_starts = {
        "Young Infant (0-6 Months)": 0,
        "Infant (7-24 Months)": 0.5,
        "Young Child (3-5 Years)": 3,
        "Child (6-12 Years)": 6,
        "Adolescent (13-17 Years)": 13,
        "Young Adult (18-24 Years)": 18,
        "Adult (25-44 Years)": 25,
        "Older Adult (45-64 Years)": 45,
        "Senior (65-79 Years)": 65,
        "Older Senior (80+ Years)": 80,
    }
    age_ends = {
        "Young Infant (0-6 Months)": 0.5,
        "Infant (7-24 Months)": 3,
        "Young Child (3-5 Years)": 6,
        "Child (6-12 Years)": 13,
        "Adolescent (13-17 Years)": 18,
        "Young Adult (18-24 Years)": 25,
        "Adult (25-44 Years)": 45,
        "Older Adult (45-64 Years)": 65,
        "Senior (65-79 Years)": 80,
        "Older Senior (80+ Years)": 999,
    }

    # Sort the ages
    ages = ages.copy()
    ages.sort(key=lambda x: age_starts[x])

    # Iteratively identify continuous age blocks and display as string
    current_start, current_end = age_starts[ages[0]], age_ends[ages[0]]
    current_string = ""
    for age in ages[1:]:
        if age_starts[age] == current_end:
            current_end = age_ends[age]
        else:
            current_string += f", {age_range_string(current_start, current_end)}"
            current_start, current_end = age_starts[age], age_ends[age]
    current_string += f", {age_range_string(current_start, current_end)}"
    current_string += " Years" if current_string[-6:] != "Months" else ""
    return current_string[2:]


# Miscellaneous functions
def schema_update(schema: BaseModel, param_group: str, new_params: BaseModel):
    """
    Function to update a parameter object with new schema values

    Parameters:
        schema (BaseModel): The Pydantic model holding the current parameters.

        param_group (str): The name of the group of parameters to be updated.

        new_params (BaseModel): The Pydantic model containing the new parameter
            values.
    """

    new_params_dict = new_params.model_dump(exclude_unset=True)
    if new_params_dict:
        if getattr(schema, param_group, None) is None:
            setattr(schema, param_group, new_params)
        else:
            new_schema = getattr(schema, param_group).model_copy(update=new_params_dict)
            setattr(schema, param_group, new_schema)


def schema_remove_baseline[Model: BaseModel](
    scenario: Model,
    baseline: Optional[Model],
    ignore: set[str] = set(),
    defaults: dict[str, Any] = {},
):
    """
    Function to remove any parameters from a scenario that are already represented in the baseline scenario.

    Parameters:
        scenario (BaseModel): The Pydantic model containing the scenario
            parameters to be removed.

        baseline (BaseModel): The object containing the baseline parameters to
            remove from the scenario object. The function will end immediately
            if this is `None`.

        ignore (set of str): A set specifying parameters that should
            never be removed from `scenario` even if they are present in `baseline`.

        defaults (dict): A dictionary specifying parameters that should
            default to a specific value if they are present in the `baseline` but
            missing in `scenario`.

    Raises:
        TypeError: If scenario and baseline are not part of the same object class.
    """

    if baseline is None:
        return
    if not (type(scenario) is type(baseline)):
        raise TypeError("scenario and baseline should be the same type")

    for param, value in vars(baseline).items():
        if param in defaults and getattr(scenario, param, None) is None:
            setattr(scenario, param, defaults[param])
        if getattr(scenario, param, float("nan")) == value and param not in ignore:
            delattr(scenario, param)


def background_colour() -> str:
    """
    Simple function to get the background colour of the current theme.

    Returns:
        str: The hex code representing the background colour as a string.
    """
    return "#0F1116" if st.context.theme.type == "dark" else "#FFFFFF"
