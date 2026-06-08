# Flusim Web Interface Application
# Developed by Reilly Evans
# Miscellaneous functions used by the client dashboard

# Imports
import logging
import re
from functools import partial
from typing import Any, Callable, Literal, cast

import numpy as np
import streamlit as st
from pydantic import ValidationError

from ClientResources.ParameterFunctions import containerSave
from ClientResources.SharedResources import ageWithTime, triggerConditions

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Tools for error messages
# Error Colours: Text #BD4043, Background #FFE9E9
errorFormat = partial(st.error, icon=":material/error:")
# Warning Colours: Text #926C05, Background #FFFFEC
warnFormat = partial(st.warning, icon=":material/warning:")
# Use sRGB in the colour picker for the best display/code match


# Error functions
def paramError(
    label: str,
    scenarioID: int,
    condition: Callable[[], bool | np.bool],
    message: str,
    isSevere=False,
):
    """
    Function to display an error message if a condition is met.

    Parameters:
        label (str): A string to identify this specific error.

        scenarioID (int): The integer representing the scenario this error applies to.

        condition (callable, returns bool): The criteria that must be fulfilled
            to display the error, formatted as a function that returns `True` when
            the criteria is met.

        message (str): The text to display for the error message.

        isSevere (bool): Set to `True` for red errors that prevent running
            the simulation if present.
    """
    # TODO: Allow errors to link to the affected parameter
    # (if anchor tags are/become possible)
    # TODO: Consider reworking errors so that you don't need to open
    # their tab to generate them
    if condition():
        if isSevere:
            errorFormat(message)
            session["activeErrors"][scenarioID][label] = (message, True)
        else:
            warnFormat(message)
            session["activeErrors"][scenarioID][label] = (message, False)
    else:
        session["activeErrors"][scenarioID].pop(label, None)


def dualError(
    label: str,
    scenarioID: int,
    errorCon: Callable[[], bool],
    warnCon: Callable[[], bool],
    errorMessage: str,
    warnMessage: str,
):
    """
    Function to display an error message with two different severity levels
    if different conditions are met.

    Parameters:
        label (str): A string to identify this specific error.

        scenarioID (int): The integer representing the scenario this error applies to.

        errorCon (callable, returns bool): The criteria for a red, run-blocking
            error, formatted as a function that returns `True` when the criteria
            is met. This condition will override the condition in `warnCon`.

        warnCon (callable, returns bool): The criteria for a yellow, minor warning,
            formatted as a function that returns `True` when the criteria is met.

        errorMessage (str): The text to display for the red error message.

        warnMessage (str): The text to display for the yellow error message.
    """
    if errorCon():
        errorFormat(errorMessage)
        session["activeErrors"][scenarioID][label] = (errorMessage, True)
    elif warnCon():
        warnFormat(warnMessage)
        session["activeErrors"][scenarioID][label] = (warnMessage, False)
    else:
        session["activeErrors"][scenarioID].pop(label, None)


@st.fragment(run_every=1)
def errorChecker(scenarioID: int, name: str = "Errors in Current Scenario"):
    """
    Fragment to list errors from a specific scenario in a dropdown container.

    Parameters:
        scenarioID (int): The integer representing the scenario to pull errors from.

        name (str): The label of the dropdown container.

    Returns:
        bool: Returns `True` if at least one error was run-blocking and
            `False` otherwise.
    """
    # TODO: Consider removing the run_every parameter and defragmenting tabs
    severeErrorsFound = False
    if session["activeErrors"].get(scenarioID, False):
        with st.status(label=name, state="error"):
            for message, isSevere in session["activeErrors"][scenarioID].values():
                if isSevere:
                    errorFormat(message)
                    severeErrorsFound = True
                else:
                    warnFormat(message)
    return severeErrorsFound


def validationErrorFormatting(e: ValidationError):
    """
    Function to convert ValidationErrors raised by Pydantic into user-readable
    error messages.

    Parameters:
        e (ValidationError): The error to unpack.
    """
    for error in e.errors():
        # TODO: Use Pydantic's method of subbing in custom messages
        # See https://pydantic.dev/docs/validation/latest/errors/errors/
        st.error(f"Error: {error["msg"]}", icon=":material/error:")


# Formatting functions
def plural(value: int | float):
    """
    Simple function to add "s" to words when a value is not 1.

    Parameters:
        value (int or float): The value to check.
    """
    return "" if value == 1 else "s"


def dayCount(count: int | float):
    """
    Simple function to convert a number into a string describing a number of days.

    Parameters:
        count (int or float): The number of days to return.
    """
    return "1 Day" if count == 1 else f"{count:g} Days"


def timeString(time: int | float) -> str:
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


def trigCast(x: str) -> Literal[
    "none",
    "timed",
    "per_school_cases",
    "community_cases",
    "community_rate",
    "per_primary_high_school_cases",
]:
    """
    Simple function to cast trigger strings into literals for validation.

    Parameters:
        x (str): The string to be cast.

    Returns:
        Literal: A literal with the same value as the string.
    """
    return cast(
        Literal[
            "none",
            "timed",
            "per_school_cases",
            "community_cases",
            "community_rate",
            "per_primary_high_school_cases",
        ],
        triggerConditions[x],
    )


# Scenario name functions
def saveName(
    key: str,
    scenarioID: int,
    errorContainer,
    containers: set[str] = set(),
    specialContainers: dict[str, str] = {},
):
    """
    Wrapper for `containerSave` that stops empty or duplicate names being saved.

    Parameters:
        key (str): The string used to identify the name-setting widget.

        scenarioID (int): The integer representing the scenario the widget
            is naming.

        errorContainer: The container in which to display the error message.

        containers (set of str): String used to identify each container to open.

        specialContainers (dict of str): String used to identify containers
            that must be set to specific values (i.e. scenario tabs whose
            names change). Including `{id}` or `{value}` in one of the values
            for these will replace them with the value of `scenarioID` or the
            value of the widget that is being saved, respectively.
    """
    newName = session.get(f"_{key}{scenarioID}")
    scenarioCount = session.scenarioCount
    currentNames = {
        session.get(f"{key}{i}") for i in range(1, scenarioCount + 1) if i != scenarioID
    }
    if newName == "":
        errorContainer.error(
            """
            Please enter a name.
            """,
            icon=":material/remove_selection:",
        )
    elif newName in currentNames:
        errorContainer.error(
            """
            The selected name is already the name of a different scenario.
            Please enter a different name.
            """,
            icon=":material/tab_close_inactive:",
        )
    else:
        containerSave(key, scenarioID, containers, specialContainers)


def uniqueName(currentName: str, names: set[str]):
    """
    Function to add a suffix to a string to make it unique compared to a set

    Parameters:
        currentName (str): The string to make unique.

        names (set of str): The other strings to compare with.
    """
    if currentName not in names:
        return currentName

    # Check if suffix is already present and increment if so
    match = re.match(r"^(.*?)(?: (\d+))?$", currentName)
    if match is not None:
        base, num = match.groups()
        n = int(num) if num else 2
    else:
        base = currentName
        n = 2

    candidate = f"{base} {n}"
    while candidate in names:
        n += 1
        candidate = f"{base} {n}"
    return candidate


# Age functions
def ageSort(age: tuple[str, Any]) -> int:
    """
    Function to be used in `sorted()` for ordering age groups

    Parameters:
        age (tuple with str): A tuple where the first item is the string
            representation of an age group.

    Returns:
        int: The numeric ordering index of the age group.
    """
    return [
        "young_infant",
        "infant",
        "young_child",
        "child",
        "adolescent",
        "young_adult",
        "adult",
        "older_adult",
        "senior",
        "older_senior",
    ].index(age[0])


def ageRangeString(lower: int | float, upper: int | float) -> str:
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


def ageRangeCombiner(ages: list[str]) -> str:
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
    if set(ages) == set(ageWithTime):
        return "All Ages"

    # Dictionaries to get the starts/ends of each age bracket
    ageStarts = {
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
    ageEnds = {
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
    ageList = ages.copy()
    ageList.sort(key=lambda x: ageStarts[x])

    # Iteratively identify continuous age blocks and display as string
    currentStart, currentEnd = ageStarts[ageList[0]], ageEnds[ageList[0]]
    currentString = ""
    for age in ageList[1:]:
        if ageStarts[age] == currentEnd:
            currentEnd = ageEnds[age]
        else:
            currentString += f", {ageRangeString(currentStart, currentEnd)}"
            currentStart, currentEnd = ageStarts[age], ageEnds[age]
    currentString += f", {ageRangeString(currentStart, currentEnd)}"
    currentString += " Years" if currentString[-6:] != "Months" else ""
    return currentString[2:]


def ageCast(x: str) -> Literal[
    "young_infant",
    "infant",
    "young_child",
    "child",
    "adolescent",
    "young_adult",
    "adult",
    "older_adult",
    "senior",
    "older_senior",
]:
    """
    Simple function to cast age strings into literals for validation.

    Parameters:
        x (str): The string to be cast.

    Returns:
        Literal: A literal with the same value as the string.
    """
    return cast(
        Literal[
            "young_infant",
            "infant",
            "young_child",
            "child",
            "adolescent",
            "young_adult",
            "adult",
            "older_adult",
            "senior",
            "older_senior",
        ],
        x,
    )


# Miscellaneous functions
def schemaUpdate(schema: Any, paramGroup: str, newParams: Any):
    """
    Function to update a parameter object with new schema values

    Parameters:
        schema: The object holding the current parameters.

        paramGroup (str): The name of the group of parameters to be updated.

        newParams: The object containing the new parameter values.
    """
    newParamsDict = newParams.model_dump(exclude_unset=True)
    if newParamsDict:
        if getattr(schema, paramGroup, None) is None:
            setattr(schema, paramGroup, newParams)
        else:
            newSchema = getattr(schema, paramGroup).model_copy(update=newParamsDict)
            setattr(schema, paramGroup, newSchema)


def schemaRemoveBaseline(
    scenario: Any,
    baseline: Any,
    ignore: set[str] = set(),
    defaults: dict[str, Any] = {},
):
    """
    Function to remove any parameters from a scenario that are already represented in the baseline scenario.

    Parameters:
        scenario: The object containing the scenario parameters.

        baseline: The object containing the baseline parameters to remove from
            the scenario object.

        ignore (set of str): A set specifying parameters that should
            never be removed from `scenario` even if they are present in `baseline`.

        defaults (dict): A dictionary specifying parameters that should
            default to a specific value if they are present in the `baseline` but
            missing in `scenario`.

    Returns:
        Any: The scenario object, with any attributes shared with the baseline
            having been removed.

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


def backgroundColour() -> str:
    """
    Simple function to get the background colour of the current theme.

    Returns:
        str: The hex code representing the background colour as a string.
    """
    return "#0F1116" if st.context.theme.type == "dark" else "#FFFFFF"
