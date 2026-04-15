# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the rest of the client application

# Imports
import logging
import re
from functools import partial
from typing import Callable

import numpy as np
import streamlit as st

from ClientResources.ParameterFunctions import containerSave

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
    # since containers can be dynamically opened now
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


def dayCount(count: int | float):
    """
    Simple function to convert a number into a string describing a number of days.

    Parameters:
        count (int or float): The number of days to return.
    """
    return "1 Day" if count == 1 else f"{count:g} Days"


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

        scenarioID (int or ""): The integer representing the scenario the widget
            is naming. Defaults to `""`, allowing for parameters that are not
            associated with scenarios to be saved.

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
