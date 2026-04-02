# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the rest of the client application

# Imports
import logging
from functools import partial
from typing import Callable

import numpy as np
import streamlit as st

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


# TODO: Allow errors to link to the affected parameter
# since containers can be dynamically opened now
def paramError(
    label: str,
    scenarioID: int,
    condition: Callable[[], bool | np.bool],
    message: str,
    isSevere=False,
):
    """
    Function to throw an error if a condition is met

    Parameters:
        label (str): A string to identify this specific error.

        scenarioID (int): The integer representing the scenario this error applies to.

        condition (callable, returns bool): The criteria that must be fulfilled
            to throw the error, formatted as a function that returns True when
            the criteria is met.

        message (str): The text to display for the error message.

        isSevere (bool): Set to True for red errors that prevent running the simulation.
    """
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
    Function to throw either an error or a warning depending on certain conditions

    Parameters:
        label (str): A string to identify this specific error.

        scenarioID (int): The integer representing the scenario this error applies to.

        errorCon (callable, returns bool): The criteria for a red, run-blocking
            error, formatted as a function that returns True when the criteria is met.

        warnCon (callable, returns bool): The criteria for a yellow, minor error,
            formatted as a function that returns True when the criteria is met.

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
    Fragment to display errors from a specific scenario in a dropdown

    Parameters:
        scenarioID (int): The integer representing the scenario to pull errors from.

        name (str): The label of the dropdown.

    Returns:
        bool: Returns True if at least one error was run-blocking and False otherwise.


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
    Simple function to convert an integer into a string describing a number of days

    Parameters:
        count (in or float): The number of days to return.
    """
    return "1 Day" if count == 1 else f"{count} Days"
