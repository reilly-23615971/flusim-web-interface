# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the rest of the client application

# Imports
import logging
import streamlit as st
from functools import partial
from typing import Optional, Callable

# from typing import Optional, Union

# Logging
functionLog = logging.getLogger(__name__)
session = st.session_state

# Parameter Classes
'''
class Parameter:
    def __init__(self, key: str, scenarioID: int, paramName: str, defaultValue):
        self.key = key
        self.scenarioID = scenarioID
        self.fullKey = f"{key}_{scenarioID}"
        self.internalKey = f"_{key}_{scenarioID}"
        self.paramName = paramName
        self.defaultValue = defaultValue
        self._value = defaultValue

    @property
    def value(self):
        """Get the current value for this parameter"""
        return session.get(self.fullKey, self.defaultValue)

    def loadKey(self, noZeroDefault=False):
        """Update the value for this parameter's widget"""
        if noZeroDefault:
            session[self.internalKey] = session.get(self.fullKey, self.defaultValue)
        else:
            session[self.internalKey] = idGet(
                self.key, self.scenarioID, self.defaultValue
            )

    def saveKey(self):
        """Save the new value for this parameter set by its widget"""
        session[self.fullKey] = session.get(self.internalKey)
        if self.scenarioID != 0:
            session["scenarioSetParams"][self.scenarioID].append(self.key)

    def populateSchema(self, schema):
        """Populate a schema with this parameter's value"""
        setattr(schema, self.paramName, self.value)

    # TODO: Add error functionality


"""
Subclass for parameters that use sliders
"""


class SliderParam(Parameter):

    def __init__(
        self,
        key: str,
        scenarioID: int,
        paramName: str,
        defaultValue: Union[int, float],
        min: Union[int, float],
        max: Union[int, float],
        step: Union[int, float],
        title: str,
        format: Optional[str],
        help: Optional[str],
    ):
        super().__init__(key, scenarioID, paramName, defaultValue)
        self.loadKey
        self.widget = st.slider(
            title,
            min_value=min,
            max_value=max,
            value=defaultValue,
            step=step,
            format=format,
            key=self.internalKey,
            help=help,
            on_change=self.saveKey,
        )

'''


# Tools for error messages
# Error Colours: Text #BD4043, Background #FFE9E9
errorFormat = partial(st.error, icon=":material/error:")
# Warning Colours: Text #926C05, Background #FFFFEC
warnFormat = partial(st.warning, icon=":material/warning:")
# Use sRGB in the colour picker for the best display/code match


"""
Function to throw an error if a condition is met

Parameters:
    id: A string to identify this specific error.

    scenarioID: The integer representing the scenario this error applies to.

    condition: The criteria that must be fulfilled to throw the error, as a function.

    message: The text to display for the error message.

    isSevere: Set to True for red errors that prevent running the simulation.
"""


def paramError(
    id: str,
    scenarioID: int,
    condition: Callable[[], bool],
    message: str,
    isSevere=False,
):
    if condition():
        if isSevere:
            errorFormat(message)
            session["activeErrors"][scenarioID][id] = (message, True)
        else:
            warnFormat(message)
            session["activeErrors"][scenarioID][id] = (message, False)
    else:
        session["activeErrors"][scenarioID].pop(id, None)


"""
Function to throw either an error or a warning depending on certain conditions

Parameters:
    id: A string to identify this specific error.

    scenarioID: The integer representing the scenario this error applies to.

    errorCon: The criteria for a red, run-blocking error.

    warnCon: The criteria for a yellow, minor error.

    errorMessage: The text to display for the red error message.

    warnMessage: The text to display for the yellow error message.
"""


def dualError(
    id: str,
    scenarioID: int,
    errorCon: Callable[[], bool],
    warnCon: Callable[[], bool],
    errorMessage: str,
    warnMessage: str,
):
    if errorCon():
        errorFormat(errorMessage)
        session["activeErrors"][scenarioID][id] = (errorMessage, True)
    elif warnCon():
        warnFormat(warnMessage)
        session["activeErrors"][scenarioID][id] = (warnMessage, False)
    else:
        session["activeErrors"][scenarioID].pop(id, None)


"""
Fragment to display errors from a specific scenario in a dropdown

Parameters:
    id: The integer representing the scenario to pull errors from.

    name: The label of the dropdown.

Returns True if at least one error was run-blocking and False otherwise.
"""


@st.fragment(run_every=1)
def errorChecker(id: int, name: str = "Errors in Current Scenario"):
    if session["activeErrors"].get(id, False):
        with st.status(label=name, state="error"):
            severeErrorsFound = False
            for message, isSevere in session["activeErrors"][id].values():
                if isSevere:
                    errorFormat(message)
                    severeErrorsFound = True
                else:
                    warnFormat(message)
        return severeErrorsFound


"""
Function to save widget values into permanent session state vars

Parameters:
    key: The string used to identify the widget.

    scenarioID: The integer representing the scenario the widget is part of.

    extra: An additional part of the key used to distinguish variable-length forms.

    notScenario: Set to True if the widget isn't a parameter for scenarios.
"""


def saveKey(key: str, scenarioID: int, extra: Optional[str] = None, notScenario=False):
    keyString = f"{key}{scenarioID}{extra}" if extra else f"{key}{scenarioID}"
    session[keyString] = session.get(f"_{keyString}")
    if not notScenario and scenarioID != 0:
        if extra:
            session["scenarioSetParamsExtra"][scenarioID].append((key, extra))
        else:
            session["scenarioSetParams"][scenarioID].append(key)


"""
Function to update widgets with permanent session state vars

Parameters:
    key: The string used to identify the widget.

    scenarioID: The integer representing the scenario the widget is part of.

    default: the value to use if the widget is not present

    extra: An additional part of the key used to distinguish variable-length forms.

    noZeroDefault: Set to True if the widget shouldn't fall back on baseline values.
"""


def loadKey(
    key: str, scenarioID: int, default, extra: Optional[str] = "", noZeroDefault=False
):
    if noZeroDefault:
        session[f"_{key}{scenarioID}{extra}"] = session.get(
            f"{key}{scenarioID}{extra}", default
        )
    else:
        session[f"_{key}{scenarioID}{extra}"] = idGet(key, scenarioID, default, extra)


# TODO: Add proper docstrings
# ID-free save/load key functions for global engine parameters
def simpleSave(key: str):
    session[key] = session.get(f"_{key}")


def simpleLoad(key: str, default):
    session[f"_{key}"] = session.get(key, default)


timeParamList = ["seedPeriod"]  # TODO: Add the rest


# Function to update the ranges of time-based parameters
# TODO: Check if making initialisation params not scenario-based messes with this
def timeScaleChange():
    simpleSave("cycleCount")
    newLength = session["cycleCount"]
    for id in range(session["scenarioCount"] + 1):
        for key in timeParamList:
            fullKey = f"{key}{id}"
            if session.get(fullKey, None):
                session[fullKey] = (
                    min(session[fullKey][0], newLength),
                    min(session[fullKey][1], newLength),
                )
    session["rerunTime"] = True


# Function for rerunning the app when simulation length changes
@st.fragment(run_every=1)
def rerunTime():
    if session.get("rerunTime", None):
        session["rerunTime"] = False
        st.rerun(scope="app")


"""
Simple function to get a specific session state value with a specific
ID, checking ID 0 if the specified one doesn't exist before falling
back on a default

Parameters:
    key: The string component of the session state variable to get.

    scenarioID: The integer representing the scenario the value is part of.

    defaultValue: What to return if neither the specified key nor 0 give
    a value in session state.

    extra: An additional part of the key used to distinguish variable-length forms.
"""


def idGet(key: str, scenarioID: int, defaultValue, extra: Optional[str] = None):
    if not extra:
        return session.get(f"{key}{scenarioID}", session.get(f"{key}0", defaultValue))
    else:
        return session.get(
            f"{key}{scenarioID}{extra}",
            session.get(f"{key}0{extra}", defaultValue),
        )


"""
Simple function to convert an integer into a string describing a number of days
"""


def dayCount(count: int):
    return "1 Day" if count == 1 else f"{count} Days"


"""
Function to update what parameters are selectable for different
parts of a form, to avoid duplicates

Parameters:
    groupSets: A dictionary with strings as keys and tuples containing
    two strings as values, representing the form sections where age
    groups need to be kept unique. The key strings are the Streamlit
    session state variables holding the groups that haven't been
    selected already. The first string of each value tuple is the
    variable holding the number of rows in the corresponding age
    selection form. The second string is the prefix used to identify
    variables holding the groups that have already been used.

    possibleValues: A tuple containing strings representing the
    possible values that can be selected in the form
"""


def getRemainingGroups(groupSets, possibleValues):
    for set, (rowCount, prefix) in groupSets.items():
        # Calculate age groups that haven't been used yet
        remainingGroups = dict.fromkeys(possibleValues)
        takenGroups = [session.get(f"{prefix}{i}") for i in range(session[rowCount])]
        for group in takenGroups:
            if group:
                remainingGroups.pop(group, None)
        # Save the new age groups
        session[set] = list(remainingGroups.keys())


"""
Function to add an additional row to a specific variable-length form

Parameters:
    rowCounter: A string representing the Streamlit session state
    variable storing the current number of rows in the form.

    forceSetParams: A dictionary of strings representing Streamlit
    state variables and values to assign to them. Used to preload
    widgets and keep drop-down selections up-to-date.
"""


def addFormRow(rowCounter, forceSetParams=None):
    session[rowCounter] += 1
    if forceSetParams:
        for var, value in forceSetParams.items():
            if value is not None:
                session[var] = value


"""
Function to remove a row from a specific variable-length form

Parameters:
    deletedRowIndex: An integer representing the index (first is 0) of
    the row that is to be deleted from the form.

    rowCounter: A string representing the Streamlit session state
    variable storing the current number of rows in the form.

    inputPrefixes: A set of strings representing the prefixes that
    denote the input widgets within the rows of the form.

    minRows: An integer representing the minimum number of rows the
    form can have.
"""


def deleteFormRow(deletedRowIndex, rowCounter, inputPrefixes, minRows=0):
    numberOfRows = session[rowCounter]
    # functionLog.info(f'Deleting row {deletedRowIndex} from the row
    # moderated by {rowCounter}; there\'s {numberOfRows} here, and
    # we\'re modifying the values ')
    # Make sure there's at least 1 row remaining
    if numberOfRows <= minRows:
        raise ValueError(
            (
                "Tried to delete a row from a form that "
                "already has the minimum number of rows."
            )
        )

    # Shift any rows below the deleted one up
    for row in range(deletedRowIndex, numberOfRows - 1):
        for input in inputPrefixes:
            session[f"{input}{row}"] = session[f"{input}{row+1}"]

    # Erase any lingering data
    for input in inputPrefixes:
        del session[f"{input}{numberOfRows - 1}"]
    session[rowCounter] -= 1


"""
Function to check if any errors are present in the parameters
"""


def checkErrors(id):
    return [
        session.get(error, 0)
        for error in (
            f"seedPeriodError{id}",
            f"seedDynamicError{id}",
            f"closeDynamicError{id}",
            f"bccDynamicError{id}",
            f"baseVacPropError{id}",
            f"ageVacPropError{id}",
            f"basePrimEfficacyError{id}",
            f"agePrimEfficacyError{id}",
            f"baseBoostEfficacyError{id}",
            f"ageBoostEfficacyError{id}",
            f"schoolTypeError{id}",
            f"adultWithdrawalError{id}",
            f"childWithdrawalError{id}",
            f"reducedGroupError{id}",
            f"bccError{id}",
            f"triggerRateError{id}",
            f"triggerTotalError{id}",
            f"vaccinePeriodError{id}",
            f"schoolClosurePeriodError{id}",
            f"withdrawalIncreasePeriodError{id}",
            f"reducedGroupPeriodError{id}",
            f"bccPeriodError{id}",
        )
    ]
